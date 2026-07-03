from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import AuditEvent, Pagination, Severity, TenantId, ValidationError


class AuditExportFormat(StrEnum):
    JSON = "json"
    JSONL = "jsonl"


@dataclass(frozen=True, slots=True)
class AuditEventFilter:
    tenant_id: TenantId
    pagination: Pagination
    actor: str | None = None
    action: str | None = None
    target_type: str | None = None
    severity: Severity | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        pagination: Pagination,
        actor: str | None = None,
        action: str | None = None,
        target_type: str | None = None,
        severity: str | Severity | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> Self:
        normalized_actor = cls._optional_safe_text(actor, "actor")
        normalized_action = cls._optional_safe_text(action, "action")
        normalized_target_type = cls._optional_safe_text(target_type, "target type")
        normalized_severity = cls._normalize_severity(severity)
        normalized_from = cls._normalize_optional_datetime(created_from, "created_from")
        normalized_to = cls._normalize_optional_datetime(created_to, "created_to")
        if (
            normalized_from is not None
            and normalized_to is not None
            and normalized_from > normalized_to
        ):
            raise ValidationError("audit created_from cannot be greater than created_to")
        return cls(
            tenant_id=tenant_id,
            pagination=pagination,
            actor=normalized_actor,
            action=normalized_action,
            target_type=normalized_target_type,
            severity=normalized_severity,
            created_from=normalized_from,
            created_to=normalized_to,
        )

    @classmethod
    def _optional_safe_text(cls, value: str | None, label: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValidationError("audit " + label + " filter cannot be blank")
        return normalized

    @classmethod
    def _normalize_severity(cls, value: str | Severity | None) -> Severity | None:
        if value is None:
            return None
        return value if isinstance(value, Severity) else Severity(str(value).strip().lower())

    @classmethod
    def _normalize_optional_datetime(
        cls,
        value: datetime | None,
        label: str,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValidationError("audit " + label + " must be timezone-aware")
        return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AuditEventRecord:
    event: AuditEvent
    previous_hash: str
    record_hash: str

    @classmethod
    def create(cls, event: AuditEvent, previous_hash: str) -> Self:
        normalized_previous = AuditIntegrityHasher.normalize_hash(previous_hash, "previous_hash")
        record_hash = AuditIntegrityHasher().compute_event_hash(event, normalized_previous)
        return cls(event=event, previous_hash=normalized_previous, record_hash=record_hash)

    @classmethod
    def restore(cls, event: AuditEvent, previous_hash: str, record_hash: str) -> Self:
        normalized_previous = AuditIntegrityHasher.normalize_hash(previous_hash, "previous_hash")
        normalized_hash = AuditIntegrityHasher.normalize_hash(record_hash, "record_hash")
        return cls(event=event, previous_hash=normalized_previous, record_hash=normalized_hash)

    def verifies(self) -> bool:
        expected = AuditIntegrityHasher().compute_event_hash(self.event, self.previous_hash)
        return expected == self.record_hash

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.event.id.value,
            "tenant_id": self.event.tenant_id.value,
            "actor": self.event.actor,
            "action": self.event.action,
            "target_type": self.event.target_type,
            "target_id": self.event.target_id,
            "severity": self.event.severity.value,
            "created_at": self.event.created_at.isoformat(),
            "metadata": self.event.metadata,
            "previous_hash": self.previous_hash,
            "record_hash": self.record_hash,
            "integrity_valid": self.verifies(),
        }


@dataclass(frozen=True, slots=True)
class AuditEventPage:
    items: tuple[AuditEventRecord, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class AuditIntegrityReport:
    tenant_id: TenantId
    checked: int
    valid: bool
    broken_record_id: str | None
    head_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "checked": self.checked,
            "valid": self.valid,
            "broken_record_id": self.broken_record_id,
            "head_hash": self.head_hash,
        }


@dataclass(frozen=True, slots=True)
class AuditExportBundle:
    tenant_id: TenantId
    format: AuditExportFormat
    content_type: str
    payload: str
    count: int
    head_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "format": self.format.value,
            "content_type": self.content_type,
            "payload": self.payload,
            "count": self.count,
            "head_hash": self.head_hash,
        }


class AuditIntegrityHasher:
    GENESIS_HASH = "0" * 64

    @classmethod
    def normalize_hash(cls, value: str, label: str) -> str:
        normalized = value.strip().lower()
        has_invalid_character = any(character not in "0123456789abcdef" for character in normalized)
        if len(normalized) != 64 or has_invalid_character:
            raise ValidationError(label + " must be a sha256 hex digest")
        return normalized

    def compute_event_hash(self, event: AuditEvent, previous_hash: str) -> str:
        payload = {
            "id": event.id.value,
            "tenant_id": event.tenant_id.value,
            "actor": event.actor,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "severity": event.severity.value,
            "created_at": event.created_at.astimezone(UTC).isoformat(),
            "metadata": event.metadata,
            "previous_hash": self.normalize_hash(previous_hash, "previous_hash"),
        }
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
