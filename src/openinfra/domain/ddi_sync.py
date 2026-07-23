from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import EntityId, Name, OpenInfraError, TenantId, ValidationError
from openinfra.domain.ipam import DdiChange, DdiProvider


class DdiExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    COMPENSATION_FAILED = "compensation_failed"

    @classmethod
    def from_value(cls, value: str) -> Self:
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("DDI execution status is invalid") from exc


class DdiMutationOutcome(StrEnum):
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    UNKNOWN = "unknown"

    @classmethod
    def from_value(cls, value: str) -> Self:
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("DDI mutation outcome is invalid") from exc


class DdiProviderMutationError(OpenInfraError):
    def __init__(
        self,
        message: str,
        *,
        outcome_unknown: bool = False,
        receipt: DdiMutationReceipt | None = None,
    ) -> None:
        super().__init__(message)
        self.outcome_unknown = bool(outcome_unknown)
        self.receipt = receipt


@dataclass(frozen=True, slots=True)
class DdiMutationReceipt:
    sequence: int
    provider: DdiProvider
    change: DdiChange
    rollback_change: DdiChange
    provider_reference: str
    outcome: DdiMutationOutcome
    compensated: bool
    compensation_reference: str | None
    recorded_at: datetime

    @classmethod
    def create(
        cls,
        sequence: int,
        change: DdiChange,
        rollback_change: DdiChange,
        provider_reference: str,
        outcome: str | DdiMutationOutcome = DdiMutationOutcome.APPLIED,
        recorded_at: datetime | None = None,
    ) -> Self:
        if sequence < 1:
            raise ValidationError("DDI receipt sequence must be positive")
        normalized_reference = " ".join(provider_reference.strip().split())
        if not normalized_reference:
            raise ValidationError("DDI receipt provider reference is mandatory")
        if rollback_change.provider is not change.provider:
            raise ValidationError("DDI rollback provider must match applied provider")
        normalized_outcome = (
            outcome
            if isinstance(outcome, DdiMutationOutcome)
            else DdiMutationOutcome.from_value(outcome)
        )
        timestamp = cls._normalize_datetime(recorded_at or datetime.now(UTC))
        return cls(
            sequence=sequence,
            provider=change.provider,
            change=change,
            rollback_change=rollback_change,
            provider_reference=normalized_reference,
            outcome=normalized_outcome,
            compensated=False,
            compensation_reference=None,
            recorded_at=timestamp,
        )

    @classmethod
    def restore(cls, payload: dict[str, object]) -> Self:
        change = cls._change_from_dict(cls._mapping(payload.get("change"), "change"))
        rollback = cls._change_from_dict(
            cls._mapping(payload.get("rollback_change"), "rollback_change")
        )
        receipt = cls.create(
            sequence=int(payload["sequence"]),
            change=change,
            rollback_change=rollback,
            provider_reference=str(payload["provider_reference"]),
            outcome=str(payload["outcome"]),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
        )
        compensated = bool(payload.get("compensated", False))
        reference = payload.get("compensation_reference")
        if compensated:
            return receipt.mark_compensated(str(reference or "restored-compensation"))
        if reference is not None:
            raise ValidationError("uncompensated DDI receipt cannot have compensation reference")
        return receipt

    def mark_compensated(self, provider_reference: str) -> Self:
        normalized_reference = " ".join(provider_reference.strip().split())
        if not normalized_reference:
            raise ValidationError("DDI compensation reference is mandatory")
        return replace(
            self,
            compensated=True,
            compensation_reference=normalized_reference,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "provider": self.provider.value,
            "change": self.change.as_dict(),
            "rollback_change": self.rollback_change.as_dict(),
            "provider_reference": self.provider_reference,
            "outcome": self.outcome.value,
            "compensated": self.compensated,
            "compensation_reference": self.compensation_reference,
            "recorded_at": self.recorded_at.isoformat(),
        }

    @staticmethod
    def _mapping(value: object, field_name: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValidationError(f"DDI receipt {field_name} must be an object")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def _change_from_dict(payload: dict[str, object]) -> DdiChange:
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValidationError("DDI change metadata must be an object")
        return DdiChange.create(
            provider=str(payload["provider"]),
            action=str(payload["action"]),
            record_kind=str(payload["record_kind"]),
            name=str(payload["name"]),
            value=str(payload["value"]),
            ttl=int(payload.get("ttl", 300)),
            metadata={str(key): value for key, value in metadata.items()},
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValidationError("DDI receipt datetime must be timezone-aware")
        return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class DdiExecutionJournal:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    reservation_idempotency_key: str
    execution_idempotency_key: str
    request_fingerprint: str
    providers: tuple[DdiProvider, ...]
    status: DdiExecutionStatus
    receipts: tuple[DdiMutationReceipt, ...]
    error_message: str | None
    reconciliation_required: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        reservation_idempotency_key: str,
        execution_idempotency_key: str,
        request_fingerprint: str,
        providers: tuple[DdiProvider, ...],
        now: datetime | None = None,
    ) -> Self:
        reservation_key = cls._normalize_key(
            reservation_idempotency_key, "reservation idempotency key"
        )
        execution_key = cls._normalize_key(
            execution_idempotency_key, "execution idempotency key"
        )
        fingerprint = request_fingerprint.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValidationError("DDI request fingerprint must be a SHA-256 hex digest")
        normalized_providers = tuple(dict.fromkeys(providers))
        if not normalized_providers:
            raise ValidationError("DDI execution requires at least one provider")
        timestamp = cls._normalize_datetime(now or datetime.now(UTC))
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            reservation_idempotency_key=reservation_key,
            execution_idempotency_key=execution_key,
            request_fingerprint=fingerprint,
            providers=normalized_providers,
            status=DdiExecutionStatus.PENDING,
            receipts=(),
            error_message=None,
            reconciliation_required=False,
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def restore(cls, payload: dict[str, object]) -> Self:
        providers_raw = payload.get("providers")
        receipts_raw = payload.get("receipts")
        if not isinstance(providers_raw, list) or not isinstance(receipts_raw, list):
            raise ValidationError("DDI execution providers and receipts must be arrays")
        instance = cls(
            id=EntityId.from_value(str(payload["id"])),
            tenant_id=TenantId.from_value(str(payload["tenant_id"])),
            vrf_name=Name.from_value(str(payload["vrf"]), "vrf name"),
            reservation_idempotency_key=cls._normalize_key(
                str(payload["reservation_idempotency_key"]),
                "reservation idempotency key",
            ),
            execution_idempotency_key=cls._normalize_key(
                str(payload["execution_idempotency_key"]),
                "execution idempotency key",
            ),
            request_fingerprint=str(payload["request_fingerprint"]).strip().lower(),
            providers=tuple(DdiProvider.from_value(str(value)) for value in providers_raw),
            status=DdiExecutionStatus.from_value(str(payload["status"])),
            receipts=tuple(
                DdiMutationReceipt.restore(dict(value))
                for value in receipts_raw
                if isinstance(value, dict)
            ),
            error_message=(
                " ".join(str(payload["error_message"]).strip().split())
                if payload.get("error_message")
                else None
            ),
            reconciliation_required=bool(payload.get("reconciliation_required", False)),
            created_at=cls._normalize_datetime(
                datetime.fromisoformat(str(payload["created_at"]))
            ),
            updated_at=cls._normalize_datetime(
                datetime.fromisoformat(str(payload["updated_at"]))
            ),
        )
        instance._validate_invariants()
        return instance

    @property
    def terminal(self) -> bool:
        return self.status in {
            DdiExecutionStatus.SUCCEEDED,
            DdiExecutionStatus.FAILED,
            DdiExecutionStatus.COMPENSATED,
            DdiExecutionStatus.COMPENSATION_FAILED,
        }

    def ensure_same_request(self, fingerprint: str) -> None:
        if self.request_fingerprint != fingerprint.strip().lower():
            raise ValidationError(
                "DDI execution idempotency key is already bound to a different request"
            )

    def start(self, now: datetime | None = None) -> Self:
        if self.status not in {DdiExecutionStatus.PENDING, DdiExecutionStatus.RUNNING}:
            raise ValidationError("DDI execution cannot start from its current state")
        return self._transition(DdiExecutionStatus.RUNNING, now=now)

    def record_receipt(
        self, receipt: DdiMutationReceipt, now: datetime | None = None
    ) -> Self:
        if self.status is not DdiExecutionStatus.RUNNING:
            raise ValidationError("DDI receipt can only be recorded while execution is running")
        expected = len(self.receipts) + 1
        if receipt.sequence != expected:
            raise ValidationError(f"DDI receipt sequence must be {expected}")
        if receipt.provider not in self.providers:
            raise ValidationError("DDI receipt provider is not part of the execution request")
        reconciliation = self.reconciliation_required or (
            receipt.outcome is DdiMutationOutcome.UNKNOWN
        )
        return replace(
            self,
            receipts=(*self.receipts, receipt),
            reconciliation_required=reconciliation,
            updated_at=self._timestamp(now),
        )

    def succeed(self, now: datetime | None = None) -> Self:
        if self.status is not DdiExecutionStatus.RUNNING:
            raise ValidationError("DDI execution can only succeed while running")
        if not self.receipts or any(
            receipt.outcome is not DdiMutationOutcome.APPLIED for receipt in self.receipts
        ):
            raise ValidationError("DDI execution cannot succeed without applied receipts")
        if self.reconciliation_required:
            raise ValidationError("DDI execution requiring reconciliation cannot succeed")
        return self._transition(DdiExecutionStatus.SUCCEEDED, now=now)

    def begin_compensation(self, error_message: str, now: datetime | None = None) -> Self:
        if self.status is not DdiExecutionStatus.RUNNING:
            raise ValidationError("DDI compensation can only start from running state")
        return self._transition(
            DdiExecutionStatus.COMPENSATING,
            error_message=error_message,
            now=now,
        )

    def mark_receipt_compensated(
        self, sequence: int, provider_reference: str, now: datetime | None = None
    ) -> Self:
        if self.status is not DdiExecutionStatus.COMPENSATING:
            raise ValidationError("DDI receipt can only be compensated while compensating")
        updated: list[DdiMutationReceipt] = []
        found = False
        for receipt in self.receipts:
            if receipt.sequence == sequence:
                updated.append(receipt.mark_compensated(provider_reference))
                found = True
            else:
                updated.append(receipt)
        if not found:
            raise ValidationError("DDI receipt to compensate was not found")
        return replace(self, receipts=tuple(updated), updated_at=self._timestamp(now))

    def compensated(self, now: datetime | None = None) -> Self:
        if self.status is not DdiExecutionStatus.COMPENSATING:
            raise ValidationError("DDI execution can only finish compensation while compensating")
        applied = [
            receipt
            for receipt in self.receipts
            if receipt.outcome is DdiMutationOutcome.APPLIED
        ]
        if any(not receipt.compensated for receipt in applied):
            raise ValidationError("DDI execution has uncompensated applied effects")
        if self.reconciliation_required:
            return self.compensation_failed(
                self.error_message or "DDI provider outcome requires reconciliation",
                now=now,
            )
        return self._transition(DdiExecutionStatus.COMPENSATED, now=now)

    def fail_without_effect(
        self, error_message: str, *, reconciliation_required: bool = False, now: datetime | None = None
    ) -> Self:
        if self.status not in {DdiExecutionStatus.PENDING, DdiExecutionStatus.RUNNING}:
            raise ValidationError("DDI execution cannot fail from its current state")
        return self._transition(
            DdiExecutionStatus.FAILED,
            error_message=error_message,
            reconciliation_required=reconciliation_required,
            now=now,
        )

    def compensation_failed(self, error_message: str, now: datetime | None = None) -> Self:
        if self.status not in {
            DdiExecutionStatus.RUNNING,
            DdiExecutionStatus.COMPENSATING,
        }:
            raise ValidationError("DDI compensation failure has invalid source state")
        return self._transition(
            DdiExecutionStatus.COMPENSATION_FAILED,
            error_message=error_message,
            reconciliation_required=True,
            now=now,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "vrf": self.vrf_name.value,
            "reservation_idempotency_key": self.reservation_idempotency_key,
            "execution_idempotency_key": self.execution_idempotency_key,
            "request_fingerprint": self.request_fingerprint,
            "providers": [provider.value for provider in self.providers],
            "status": self.status.value,
            "terminal": self.terminal,
            "receipts": [receipt.as_dict() for receipt in self.receipts],
            "receipt_count": len(self.receipts),
            "error_message": self.error_message,
            "reconciliation_required": self.reconciliation_required,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def _transition(
        self,
        status: DdiExecutionStatus,
        *,
        error_message: str | None = None,
        reconciliation_required: bool | None = None,
        now: datetime | None = None,
    ) -> Self:
        normalized_error = (
            " ".join(error_message.strip().split()) if error_message and error_message.strip() else None
        )
        updated = replace(
            self,
            status=status,
            error_message=normalized_error if error_message is not None else self.error_message,
            reconciliation_required=(
                self.reconciliation_required
                if reconciliation_required is None
                else bool(reconciliation_required)
            ),
            updated_at=self._timestamp(now),
        )
        updated._validate_invariants()
        return updated

    def _validate_invariants(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_fingerprint):
            raise ValidationError("DDI request fingerprint must be a SHA-256 hex digest")
        if not self.providers:
            raise ValidationError("DDI execution requires at least one provider")
        if self.updated_at < self.created_at:
            raise ValidationError("DDI execution update time cannot precede creation time")
        if self.status is DdiExecutionStatus.SUCCEEDED:
            if not self.receipts or self.reconciliation_required:
                raise ValidationError("successful DDI execution invariants are not satisfied")
            if any(
                receipt.outcome is not DdiMutationOutcome.APPLIED for receipt in self.receipts
            ):
                raise ValidationError("successful DDI execution contains a non-applied receipt")
        if self.status is DdiExecutionStatus.COMPENSATED:
            applied = [
                receipt
                for receipt in self.receipts
                if receipt.outcome is DdiMutationOutcome.APPLIED
            ]
            if any(not receipt.compensated for receipt in applied):
                raise ValidationError("compensated DDI execution has uncompensated effects")
            if self.reconciliation_required:
                raise ValidationError("compensated DDI execution cannot require reconciliation")
        if self.status is DdiExecutionStatus.COMPENSATION_FAILED and not self.reconciliation_required:
            raise ValidationError("failed DDI compensation must require reconciliation")

    @classmethod
    def _normalize_key(cls, value: str, field_name: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}", normalized):
            raise ValidationError(f"DDI {field_name} must use 3 to 128 safe characters")
        return normalized

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValidationError("DDI execution datetime must be timezone-aware")
        return value.astimezone(UTC)

    def _timestamp(self, value: datetime | None) -> datetime:
        timestamp = self._normalize_datetime(value or datetime.now(UTC))
        if timestamp < self.updated_at:
            raise ValidationError("DDI execution timestamp cannot move backwards")
        return timestamp
