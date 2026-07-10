from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from openinfra.application.ports import (
    AuditRepository,
    NetworkConfigBaselinePage,
    NetworkConfigComplianceRepository,
    NetworkConfigObservationPage,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.network_config_compliance import (
    NetworkConfigBaseline,
    NetworkConfigBaselineStatus,
    NetworkConfigComplianceReport,
    NetworkConfigComplianceStatus,
    NetworkConfigObservation,
)
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class UpsertNetworkConfigBaselineCommand:
    tenant_id: str
    actor: str
    admin_token: str
    code: str
    device_object_key: str
    platform: str
    expected_config: object
    ignored_paths: tuple[str, ...]
    critical_paths: tuple[str, ...]
    owner: str
    justification: str


@dataclass(frozen=True, slots=True)
class RetireNetworkConfigBaselineCommand:
    tenant_id: str
    actor: str
    admin_token: str
    baseline_id: str


@dataclass(frozen=True, slots=True)
class ListNetworkConfigBaselinesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class SubmitNetworkConfigObservationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    idempotency_key: str
    source: str
    collector: str
    device_object_key: str
    platform: str
    observed_config: object
    observed_at: str | datetime


@dataclass(frozen=True, slots=True)
class ListNetworkConfigObservationsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    device_object_key: str | None = None
    platform: str | None = None
    observed_before: str | datetime | None = None


@dataclass(frozen=True, slots=True)
class AssessNetworkConfigComplianceCommand:
    tenant_id: str
    admin_token: str
    actor: str = "api"
    baseline_code: str | None = None
    as_of: str | datetime | None = None
    status: str | None = None
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class NetworkConfigComplianceReportPage:
    items: tuple[NetworkConfigComplianceReport, ...]
    next_cursor: str | None
    as_of: datetime

    def as_dict(self) -> dict[str, object]:
        summary = {
            status.value: sum(1 for item in self.items if item.status is status)
            for status in NetworkConfigComplianceStatus
        }
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
            "as_of": self.as_of.isoformat(),
            "summary": {"total": len(self.items), **summary},
        }


class NetworkConfigComplianceService:
    def __init__(
        self,
        repository: NetworkConfigComplianceRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def upsert_baseline(self, command: UpsertNetworkConfigBaselineCommand) -> NetworkConfigBaseline:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.NETWORK_CONFIG_WRITE
        )
        actor = self._actor(command.actor, subject)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_baseline_by_code(tenant_id, command.code)
            if existing is None:
                baseline = NetworkConfigBaseline.create(
                    tenant_id=tenant_id,
                    code=command.code,
                    device_object_key=command.device_object_key,
                    platform=command.platform,
                    expected_config=self._config(command.expected_config),
                    ignored_paths=command.ignored_paths,
                    critical_paths=command.critical_paths,
                    owner=command.owner,
                    justification=command.justification,
                    actor=actor,
                )
                action = "network_config.baseline.create"
            else:
                if existing.device_object_key != command.device_object_key.strip():
                    raise ConflictError("network configuration baseline device cannot be changed")
                baseline = existing.revise(
                    platform=command.platform,
                    expected_config=self._config(command.expected_config),
                    ignored_paths=command.ignored_paths,
                    critical_paths=command.critical_paths,
                    owner=command.owner,
                    justification=command.justification,
                    actor=actor,
                )
                action = "network_config.baseline.update"
            self._repository.save_baseline(baseline)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action=action,
                    target_type="network_config_baseline",
                    target_id=baseline.id.value,
                    metadata={
                        "code": baseline.code,
                        "device_object_key": baseline.device_object_key,
                        "platform": baseline.platform,
                        "version": baseline.version,
                    },
                )
            )
            unit_of_work.commit()
        return baseline

    def retire_baseline(self, command: RetireNetworkConfigBaselineCommand) -> NetworkConfigBaseline:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.NETWORK_CONFIG_WRITE
        )
        actor = self._actor(command.actor, subject)
        with self._transaction_manager.begin() as unit_of_work:
            baseline = self._repository.get_baseline(tenant_id, command.baseline_id)
            if baseline is None:
                raise NotFoundError("network configuration baseline not found")
            retired = baseline.retire(actor)
            self._repository.save_baseline(retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="network_config.baseline.retire",
                    target_type="network_config_baseline",
                    target_id=retired.id.value,
                    metadata={"code": retired.code, "version": retired.version},
                )
            )
            unit_of_work.commit()
        return retired

    def list_baselines(
        self, command: ListNetworkConfigBaselinesCommand
    ) -> NetworkConfigBaselinePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.NETWORK_CONFIG_READ
        )
        return self._repository.list_baselines(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            include_retired=command.include_retired,
        )

    def submit_observation(
        self, command: SubmitNetworkConfigObservationCommand
    ) -> NetworkConfigObservation:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.NETWORK_CONFIG_WRITE
        )
        actor = self._actor(command.actor, subject)
        observation = NetworkConfigObservation.create(
            tenant_id=tenant_id,
            idempotency_key=command.idempotency_key,
            source=command.source,
            collector=command.collector,
            device_object_key=command.device_object_key,
            platform=command.platform,
            observed_config=self._config(command.observed_config),
            observed_at=self._required_datetime(command.observed_at, "observed_at"),
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_observation_by_idempotency_key(
                tenant_id, observation.idempotency_key
            )
            if existing is not None:
                if existing.fingerprint != observation.fingerprint:
                    raise ConflictError(
                        "network configuration observation idempotency key already exists "
                        "with a different payload"
                    )
                unit_of_work.commit()
                return existing
            self._repository.save_observation(observation)
            persisted = self._repository.find_observation_by_idempotency_key(
                tenant_id, observation.idempotency_key
            )
            if persisted is None or persisted.fingerprint != observation.fingerprint:
                raise ConflictError("network configuration observation could not be persisted")
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="network_config.observation.ingest",
                    target_type="network_config_observation",
                    target_id=persisted.id.value,
                    metadata={
                        "source": persisted.source.value,
                        "collector": persisted.collector,
                        "device_object_key": persisted.device_object_key,
                        "platform": persisted.platform,
                    },
                )
            )
            unit_of_work.commit()
        return persisted

    def list_observations(
        self, command: ListNetworkConfigObservationsCommand
    ) -> NetworkConfigObservationPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.NETWORK_CONFIG_READ
        )
        source_platform = None if command.platform is None else command.platform.strip().lower()
        return self._repository.list_observations(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            device_object_key=command.device_object_key,
            platform=source_platform,
            observed_before=self._datetime(command.observed_before),
        )

    def assess(
        self, command: AssessNetworkConfigComplianceCommand
    ) -> NetworkConfigComplianceReportPage:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.NETWORK_CONFIG_READ
        )
        as_of = self._datetime(command.as_of) or datetime.now(UTC)
        status_filter = self._status(command.status)
        pagination = Pagination.from_values(command.limit, command.cursor)
        baselines: tuple[NetworkConfigBaseline, ...]
        if command.baseline_code:
            baseline = self._repository.find_baseline_by_code(tenant_id, command.baseline_code)
            baselines = () if baseline is None else (baseline,)
            next_cursor = None
        else:
            page = self._repository.list_baselines(tenant_id, pagination, include_retired=False)
            baselines, next_cursor = page.items, page.next_cursor
        reports: list[NetworkConfigComplianceReport] = []
        for baseline in baselines:
            if baseline.status is NetworkConfigBaselineStatus.RETIRED:
                continue
            observations = self._repository.list_observations(
                tenant_id,
                Pagination.from_values(1),
                device_object_key=baseline.device_object_key,
                platform=baseline.platform,
                observed_before=as_of,
            )
            report = NetworkConfigComplianceReport.evaluate(
                baseline, observations.items[0] if observations.items else None
            )
            if status_filter is None or report.status is status_filter:
                reports.append(report)
        actor = self._actor(command.actor, subject)
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="network_config.compliance.assess",
                    target_type="network_config_compliance",
                    target_id=command.baseline_code or "all",
                    severity=(
                        Severity.WARNING
                        if any(
                            r.status is not NetworkConfigComplianceStatus.COMPLIANT for r in reports
                        )
                        else Severity.INFO
                    ),
                    metadata={
                        "as_of": as_of.isoformat(),
                        "reports": len(reports),
                        "status_filter": None if status_filter is None else status_filter.value,
                    },
                )
            )
            unit_of_work.commit()
        return NetworkConfigComplianceReportPage(tuple(reports), next_cursor, as_of)

    def _authorize(self, tenant: str, token: str, permission: Permission) -> tuple[TenantId, str]:
        tenant_id = TenantId.from_value(tenant)
        authentication = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, token, permission)
        )
        return tenant_id, authentication.subject

    @staticmethod
    def _actor(actor: str, subject: str) -> str:
        return " ".join(actor.strip().split()) or subject

    @staticmethod
    def _config(value: object) -> object:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValidationError("network configuration must be valid JSON") from exc
        return value

    @staticmethod
    def _datetime(value: str | datetime | None) -> datetime | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError("datetime value must use ISO-8601 syntax") from exc
        if parsed.tzinfo is None:
            raise ValidationError("datetime value must be timezone-aware")
        return parsed.astimezone(UTC)

    @classmethod
    def _required_datetime(cls, value: str | datetime, label: str) -> datetime:
        parsed = cls._datetime(value)
        if parsed is None:
            raise ValidationError(label + " is mandatory")
        return parsed

    @staticmethod
    def _status(value: str | None) -> NetworkConfigComplianceStatus | None:
        if value is None or value.strip() == "":
            return None
        try:
            return NetworkConfigComplianceStatus(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("network configuration compliance status is unsupported") from exc
