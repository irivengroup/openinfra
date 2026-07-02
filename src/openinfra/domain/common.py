from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self


class OpenInfraError(Exception):
    """Base error for controlled OpenInfra failures."""


class ValidationError(OpenInfraError):
    """Raised when a value violates domain invariants."""


class ConflictError(OpenInfraError):
    """Raised when an operation conflicts with existing state."""


class NotFoundError(OpenInfraError):
    """Raised when an entity cannot be found."""


class AccessDeniedError(OpenInfraError):
    """Raised when an operation is not authorized."""


class LifecycleStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class EntityId:
    value: str

    @classmethod
    def new(cls) -> Self:
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip()
        if not normalized:
            raise ValidationError("entity id cannot be empty")
        try:
            uuid.UUID(normalized)
        except ValueError as exc:
            raise ValidationError(f"invalid entity id: {value}") from exc
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class TenantId:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,62}[a-z0-9]", normalized):
            raise ValidationError("tenant id must be 3 to 64 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class Code:
    value: str

    @classmethod
    def from_value(cls, value: str, label: str = "code") -> Self:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{0,63}", normalized):
            raise ValidationError(f"{label} must use 1 to 64 safe uppercase characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class Name:
    value: str

    @classmethod
    def from_value(cls, value: str, label: str = "name") -> Self:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 255:
            raise ValidationError(f"{label} must contain 1 to 255 characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class Coordinates3D:
    x: float
    y: float
    z: float

    @classmethod
    def from_values(cls, x: float | None, y: float | None, z: float | None) -> Self | None:
        if x is None and y is None and z is None:
            return None
        if x is None or y is None or z is None:
            raise ValidationError("coordinates require x, y and z together")
        if min(x, y, z) < 0:
            raise ValidationError("coordinates cannot be negative")
        return cls(x=x, y=y, z=z)

    def as_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int
    cursor: str | None = None

    @classmethod
    def from_values(cls, limit: int, cursor: str | None = None) -> Self:
        if not 1 <= limit <= 500:
            raise ValidationError("pagination limit must be between 1 and 500")
        normalized_cursor = cursor.strip() if cursor else None
        if normalized_cursor == "":
            raise ValidationError("cursor cannot be blank")
        return cls(limit=limit, cursor=normalized_cursor)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    id: EntityId
    tenant_id: TenantId
    aggregate_id: EntityId
    name: str
    payload: dict[str, Any]
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        aggregate_id: EntityId,
        name: str,
        payload: dict[str, Any],
    ) -> Self:
        event_name = name.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,120}", event_name):
            raise ValidationError("domain event name is invalid")
        json.dumps(payload, sort_keys=True)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            aggregate_id=aggregate_id,
            name=event_name,
            payload=payload,
            occurred_at=datetime.now(UTC),
        )


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: EntityId
    tenant_id: TenantId
    actor: str
    action: str
    target_type: str
    target_id: str
    severity: Severity
    created_at: datetime
    metadata: dict[str, Any]

    @classmethod
    def record(
        cls,
        tenant_id: TenantId,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, Any] | None = None,
        severity: Severity = Severity.INFO,
    ) -> Self:
        normalized_actor = actor.strip()
        normalized_action = action.strip().lower()
        normalized_target_type = target_type.strip().lower()
        normalized_target_id = target_id.strip()
        if not normalized_actor:
            raise ValidationError("audit actor is mandatory")
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,120}", normalized_action):
            raise ValidationError("audit action is invalid")
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,120}", normalized_target_type):
            raise ValidationError("audit target type is invalid")
        if not normalized_target_id:
            raise ValidationError("audit target id is mandatory")
        safe_metadata = metadata or {}
        json.dumps(safe_metadata, sort_keys=True)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            actor=normalized_actor,
            action=normalized_action,
            target_type=normalized_target_type,
            target_id=normalized_target_id,
            severity=severity,
            created_at=datetime.now(UTC),
            metadata=safe_metadata,
        )
