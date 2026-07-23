from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from openinfra.application.ipam_services import (
    IpamDdiService,
    PreviewDdiReservationCommand,
)
from openinfra.application.ports import (
    AuditRepository,
    DdiExecutionRepository,
    DdiExecutor,
    TransactionManager,
)
from openinfra.domain.common import AuditEvent, TenantId, ValidationError
from openinfra.domain.ddi_sync import (
    DdiExecutionJournal,
    DdiExecutionStatus,
    DdiMutationOutcome,
    DdiProviderMutationError,
)
from openinfra.domain.ipam import DdiProvider


@dataclass(frozen=True, slots=True)
class SyncDdiReservationCommand:
    tenant_id: str
    actor: str
    vrf: str
    reservation_idempotency_key: str
    execution_idempotency_key: str
    providers: tuple[str, ...] = ("all",)
    dns_zone: str | None = None
    reverse_dns_zone: str | None = None
    mac_address: str | None = None
    ttl: int = 300
    resume: bool = False


class IpamDdiSynchronizationService:
    def __init__(
        self,
        preview_service: IpamDdiService,
        execution_repository: DdiExecutionRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        executors: tuple[DdiExecutor, ...],
    ) -> None:
        self._preview_service = preview_service
        self._execution_repository = execution_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._executors = {executor.provider: executor for executor in executors}

    def synchronize(self, command: SyncDdiReservationCommand) -> DdiExecutionJournal:
        preview = self._preview_service.preview_reservation(
            PreviewDdiReservationCommand(
                tenant_id=command.tenant_id,
                actor=command.actor,
                vrf=command.vrf,
                idempotency_key=command.reservation_idempotency_key,
                providers=command.providers,
                dns_zone=command.dns_zone,
                mac_address=command.mac_address,
                ttl=command.ttl,
                dry_run=False,
                reverse_dns_zone=command.reverse_dns_zone,
            )
        )
        if not preview.safe_to_apply:
            raise ValidationError("DDI synchronization is blocked by preview divergences")
        missing = sorted(
            provider.value for provider in preview.providers if provider not in self._executors
        )
        if missing:
            raise ValidationError(f"DDI executors unavailable: {', '.join(missing)}")
        fingerprint = self._fingerprint(command, preview.as_dict())
        journal = self._initialize(command, preview.providers, fingerprint)
        if journal.terminal:
            return journal
        if journal.status is DdiExecutionStatus.RUNNING and journal.receipts and not command.resume:
            return journal
        if journal.status is DdiExecutionStatus.COMPENSATING:
            if not command.resume:
                return journal
            return self._compensate(journal, command.actor)
        if journal.status is DdiExecutionStatus.PENDING:
            journal = self._persist(journal.start())
        if journal.status is not DdiExecutionStatus.RUNNING:
            raise ValidationError("DDI execution cannot continue from its current state")

        changes = preview.changes
        completed = len(journal.receipts)
        if completed > len(changes):
            return self._persist(
                journal.compensation_failed("DDI journal contains more receipts than planned changes")
            )
        for index, change in enumerate(changes[completed:], start=completed + 1):
            executor = self._executors[change.provider]
            try:
                receipt = executor.apply(index, change)
            except DdiProviderMutationError as exc:
                if exc.receipt is not None:
                    journal = self._persist(journal.record_receipt(exc.receipt))
                return self._handle_failure(journal, str(exc), command.actor, exc.outcome_unknown)
            except Exception as exc:
                return self._handle_failure(journal, str(exc), command.actor, False)
            journal = self._persist(journal.record_receipt(receipt))

        journal = self._persist(journal.succeed())
        self._audit_terminal(journal, command.actor)
        return journal

    def get_execution(
        self, tenant_id: str, execution_idempotency_key: str
    ) -> DdiExecutionJournal | None:
        normalized_tenant = TenantId.from_value(tenant_id)
        with self._transaction_manager.begin() as unit_of_work:
            journal = self._execution_repository.find_by_idempotency_key(
                normalized_tenant, execution_idempotency_key
            )
            unit_of_work.commit()
        return journal

    def _initialize(
        self,
        command: SyncDdiReservationCommand,
        providers: tuple[DdiProvider, ...],
        fingerprint: str,
    ) -> DdiExecutionJournal:
        tenant_id = TenantId.from_value(command.tenant_id)
        with self._transaction_manager.begin() as unit_of_work:
            self._execution_repository.acquire_execution_lock(
                tenant_id, command.execution_idempotency_key
            )
            existing = self._execution_repository.find_by_idempotency_key(
                tenant_id, command.execution_idempotency_key
            )
            if existing is not None:
                existing.ensure_same_request(fingerprint)
                unit_of_work.commit()
                return existing
            journal = DdiExecutionJournal.create(
                tenant_id=tenant_id,
                vrf_name=command.vrf,
                reservation_idempotency_key=command.reservation_idempotency_key,
                execution_idempotency_key=command.execution_idempotency_key,
                request_fingerprint=fingerprint,
                providers=providers,
            ).start()
            self._execution_repository.save(journal)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.ddi.sync.started",
                    target_type="ipam_ddi_execution",
                    target_id=journal.id.value,
                    metadata={
                        "vrf": journal.vrf_name.value,
                        "execution_idempotency_key": journal.execution_idempotency_key,
                        "reservation_idempotency_key": journal.reservation_idempotency_key,
                        "providers": [provider.value for provider in providers],
                    },
                )
            )
            unit_of_work.commit()
        return journal

    def _handle_failure(
        self,
        journal: DdiExecutionJournal,
        error_message: str,
        actor: str,
        outcome_unknown: bool,
    ) -> DdiExecutionJournal:
        has_effects = any(
            receipt.outcome in {DdiMutationOutcome.APPLIED, DdiMutationOutcome.UNKNOWN}
            for receipt in journal.receipts
        )
        if not has_effects:
            failed = self._persist(
                journal.fail_without_effect(
                    error_message,
                    reconciliation_required=outcome_unknown,
                )
            )
            self._audit_terminal(failed, actor)
            return failed
        compensating = self._persist(journal.begin_compensation(error_message))
        return self._compensate(compensating, actor)

    def _compensate(self, journal: DdiExecutionJournal, actor: str) -> DdiExecutionJournal:
        current = journal
        for receipt in reversed(current.receipts):
            if receipt.compensated:
                continue
            if receipt.outcome is DdiMutationOutcome.NOT_APPLIED:
                continue
            executor = self._executors.get(receipt.provider)
            if executor is None:
                failed = self._persist(
                    current.compensation_failed(
                        f"DDI executor unavailable during compensation: {receipt.provider.value}"
                    )
                )
                self._audit_terminal(failed, actor)
                return failed
            try:
                reference = executor.compensate(receipt)
            except Exception as exc:
                failed = self._persist(
                    current.compensation_failed(
                        f"DDI compensation failed for {receipt.provider.value}: {exc}"
                    )
                )
                self._audit_terminal(failed, actor)
                return failed
            current = self._persist(
                current.mark_receipt_compensated(receipt.sequence, reference)
            )
        finished = self._persist(current.compensated())
        self._audit_terminal(finished, actor)
        return finished

    def _persist(self, journal: DdiExecutionJournal) -> DdiExecutionJournal:
        with self._transaction_manager.begin() as unit_of_work:
            self._execution_repository.acquire_execution_lock(
                journal.tenant_id, journal.execution_idempotency_key
            )
            current = self._execution_repository.find_by_idempotency_key(
                journal.tenant_id, journal.execution_idempotency_key
            )
            if current is None:
                raise ValidationError("DDI execution journal disappeared during synchronization")
            if current.id != journal.id:
                raise ValidationError("DDI execution journal identity changed unexpectedly")
            current.ensure_same_request(journal.request_fingerprint)
            self._execution_repository.save(journal)
            unit_of_work.commit()
        return journal

    def _audit_terminal(self, journal: DdiExecutionJournal, actor: str) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=journal.tenant_id,
                    actor=actor,
                    action=f"ipam.ddi.sync.{journal.status.value}",
                    target_type="ipam_ddi_execution",
                    target_id=journal.id.value,
                    metadata={
                        "vrf": journal.vrf_name.value,
                        "execution_idempotency_key": journal.execution_idempotency_key,
                        "reservation_idempotency_key": journal.reservation_idempotency_key,
                        "providers": [provider.value for provider in journal.providers],
                        "receipt_count": len(journal.receipts),
                        "reconciliation_required": journal.reconciliation_required,
                    },
                )
            )
            unit_of_work.commit()

    @staticmethod
    def _fingerprint(
        command: SyncDdiReservationCommand, preview_payload: dict[str, object]
    ) -> str:
        payload = {
            "tenant_id": command.tenant_id.strip().lower(),
            "vrf": command.vrf.strip().lower(),
            "reservation_idempotency_key": command.reservation_idempotency_key.strip(),
            "providers": list(preview_payload.get("providers", [])),
            "dns_zone": (command.dns_zone or "").strip().lower().rstrip("."),
            "reverse_dns_zone": (command.reverse_dns_zone or "")
            .strip()
            .lower()
            .rstrip("."),
            "mac_address": (command.mac_address or "").strip().lower(),
            "ttl": int(command.ttl),
            "changes": preview_payload.get("changes", []),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
