from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import EntityId, TenantId, ValidationError


class SourceObjectKind(StrEnum):
    GENERIC = "generic"
    DEVICE = "device"
    INTERFACE = "interface"
    SERVICE = "service"
    APPLICATION = "application"


class SourceObjectStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class SourceObjectKey:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:@/-]{1,126}[a-z0-9]", normalized):
            raise ValidationError("source object key must use 3 to 128 safe characters")
        if ".." in normalized or "//" in normalized:
            raise ValidationError("source object key cannot contain unsafe path-like segments")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class SourceTag:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,63}", normalized):
            raise ValidationError("tag must use 1 to 64 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class SourceSystem:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized):
            raise ValidationError("source system must use 2 to 64 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class RelationType:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized):
            raise ValidationError("relation type must use 2 to 64 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class SourceOfTruthObject:
    id: EntityId
    tenant_id: TenantId
    key: SourceObjectKey
    kind: SourceObjectKind
    display_name: str
    attributes: dict[str, Any]
    tags: tuple[SourceTag, ...]
    source: SourceSystem
    version: int
    status: SourceObjectStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, Any] | None,
        tags: tuple[str, ...],
        source: str,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            key=key,
            kind=kind,
            display_name=display_name,
            attributes=attributes or {},
            tags=tags,
            source=source,
            version=1,
            status=SourceObjectStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, Any],
        tags: tuple[str, ...],
        source: str,
        version: int,
        status: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        normalized_name = " ".join(display_name.strip().split())
        if not 1 <= len(normalized_name) <= 255:
            raise ValidationError("source object display name must contain 1 to 255 characters")
        cls._validate_attributes(attributes)
        normalized_version = int(version)
        if normalized_version < 1:
            raise ValidationError("source object version must be positive")
        normalized_created_at = cls._normalize_datetime(created_at, "created_at")
        normalized_updated_at = cls._normalize_datetime(updated_at, "updated_at")
        if normalized_updated_at < normalized_created_at:
            raise ValidationError("source object updated_at cannot be before created_at")
        return cls(
            id=id,
            tenant_id=tenant_id,
            key=SourceObjectKey.from_value(key),
            kind=SourceObjectKind(str(kind).strip().lower()),
            display_name=normalized_name,
            attributes=dict(attributes),
            tags=tuple(
                sorted({SourceTag.from_value(tag) for tag in tags}, key=lambda item: item.value)
            ),
            source=SourceSystem.from_value(source),
            version=normalized_version,
            status=SourceObjectStatus(str(status).strip().lower()),
            created_at=normalized_created_at,
            updated_at=normalized_updated_at,
        )

    @classmethod
    def _validate_attributes(cls, attributes: dict[str, Any]) -> None:
        if not isinstance(attributes, dict):
            raise ValidationError("source object attributes must be a JSON object")
        encoded = json.dumps(attributes, sort_keys=True)
        if len(encoded.encode("utf-8")) > 65_536:
            raise ValidationError("source object attributes exceed 64 KiB")
        for key in attributes:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", str(key)):
                raise ValidationError("source object attribute keys must be safe")

    @classmethod
    def _normalize_datetime(cls, value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(field_name + " must be timezone-aware")
        return value.astimezone(UTC)

    def revise(
        self,
        display_name: str | None,
        attributes: dict[str, Any] | None,
        tags: tuple[str, ...] | None,
        source: str | None,
        status: str | None = None,
    ) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            key=self.key.value,
            kind=self.kind.value,
            display_name=self.display_name if display_name is None else display_name,
            attributes=self.attributes if attributes is None else attributes,
            tags=tuple(tag.value for tag in self.tags) if tags is None else tags,
            source=self.source.value if source is None else source,
            version=self.version + 1,
            status=self.status.value if status is None else status,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "key": self.key.value,
            "kind": self.kind.value,
            "display_name": self.display_name,
            "attributes": self.attributes,
            "tags": [tag.value for tag in self.tags],
            "source": self.source.value,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SourceObjectSnapshot:
    id: EntityId
    tenant_id: TenantId
    object_key: SourceObjectKey
    object_id: EntityId
    version: int
    payload: dict[str, Any]
    changed_by: str
    changed_at: datetime

    @classmethod
    def create(cls, source_object: SourceOfTruthObject, changed_by: str) -> Self:
        actor = changed_by.strip()
        if not actor:
            raise ValidationError("snapshot actor is mandatory")
        return cls(
            id=EntityId.new(),
            tenant_id=source_object.tenant_id,
            object_key=source_object.key,
            object_id=source_object.id,
            version=source_object.version,
            payload=source_object.as_dict(),
            changed_by=actor,
            changed_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        object_key: str,
        object_id: EntityId,
        version: int,
        payload: dict[str, Any],
        changed_by: str,
        changed_at: datetime,
    ) -> Self:
        actor = changed_by.strip()
        if not actor:
            raise ValidationError("snapshot actor is mandatory")
        if int(version) < 1:
            raise ValidationError("snapshot version must be positive")
        SourceOfTruthObject._validate_attributes(payload)
        return cls(
            id=id,
            tenant_id=tenant_id,
            object_key=SourceObjectKey.from_value(object_key),
            object_id=object_id,
            version=int(version),
            payload=dict(payload),
            changed_by=actor,
            changed_at=SourceOfTruthObject._normalize_datetime(changed_at, "changed_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "object_key": self.object_key.value,
            "object_id": self.object_id.value,
            "version": self.version,
            "payload": self.payload,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SourceRelation:
    id: EntityId
    tenant_id: TenantId
    relation_type: RelationType
    source_key: SourceObjectKey
    target_key: SourceObjectKey
    provenance: SourceSystem
    valid_from: datetime
    valid_to: datetime | None
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        relation_type: str,
        source_key: str,
        target_key: str,
        provenance: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            relation_type=relation_type,
            source_key=source_key,
            target_key=target_key,
            provenance=provenance,
            valid_from=valid_from or now,
            valid_to=valid_to,
            active=True,
            created_at=now,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        relation_type: str,
        source_key: str,
        target_key: str,
        provenance: str,
        valid_from: datetime,
        valid_to: datetime | None,
        active: bool,
        created_at: datetime,
    ) -> Self:
        normalized_valid_from = SourceOfTruthObject._normalize_datetime(valid_from, "valid_from")
        normalized_valid_to = (
            SourceOfTruthObject._normalize_datetime(valid_to, "valid_to")
            if valid_to is not None
            else None
        )
        if normalized_valid_to is not None and normalized_valid_to <= normalized_valid_from:
            raise ValidationError("relation valid_to must be after valid_from")
        source = SourceObjectKey.from_value(source_key)
        target = SourceObjectKey.from_value(target_key)
        if source == target:
            raise ValidationError("a source relation cannot target the same object")
        return cls(
            id=id,
            tenant_id=tenant_id,
            relation_type=RelationType.from_value(relation_type),
            source_key=source,
            target_key=target,
            provenance=SourceSystem.from_value(provenance),
            valid_from=normalized_valid_from,
            valid_to=normalized_valid_to,
            active=bool(active),
            created_at=SourceOfTruthObject._normalize_datetime(created_at, "created_at"),
        )

    def is_valid_at(self, at: datetime) -> bool:
        normalized = SourceOfTruthObject._normalize_datetime(at, "as_of")
        return (
            self.active
            and self.valid_from <= normalized
            and (self.valid_to is None or normalized < self.valid_to)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "relation_type": self.relation_type.value,
            "source_key": self.source_key.value,
            "target_key": self.target_key.value,
            "provenance": self.provenance.value,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SourceObjectPage:
    items: tuple[SourceOfTruthObject, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class SourceRelationPage:
    items: tuple[SourceRelation, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }
