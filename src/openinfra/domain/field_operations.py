from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Self

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError


class FieldTargetType(StrEnum):
    EQUIPMENT = "equipment"
    RACK = "rack"
    CABLE = "cable"
    POWER_DEVICE = "power-device"
    CERTIFICATE = "certificate"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"pdu": cls.POWER_DEVICE.value, "power_device": cls.POWER_DEVICE.value}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("field target type is unsupported") from exc


class FieldOperationStatus(StrEnum):
    READY = "ready"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChecklistPhase(StrEnum):
    BEFORE = "before"
    AFTER = "after"


class ChecklistResult(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not-applicable"


class EvidencePhase(StrEnum):
    BEFORE = "before"
    AFTER = "after"


class EvidenceStatus(StrEnum):
    ATTACHED = "attached"
    VALIDATED = "validated"


class OfflinePackageStatus(StrEnum):
    READY = "ready"
    SYNCHRONIZED = "synchronized"
    REVOKED = "revoked"


class InterventionLockStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"


@dataclass(frozen=True, slots=True)
class FieldPhysicalLocation:
    site: str
    building: str
    room: str
    row: str
    column: str
    floor: str | None = None
    zone: str | None = None
    rack: str | None = None
    rack_face: str | None = None
    u_position: int | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None

    @classmethod
    def create(
        cls,
        *,
        site: str,
        building: str,
        room: str,
        row: str,
        column: str,
        floor: str | None = None,
        zone: str | None = None,
        rack: str | None = None,
        rack_face: str | None = None,
        u_position: int | None = None,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ) -> Self:
        required = {
            "site": cls._code(site, "site"),
            "building": cls._code(building, "building"),
            "room": cls._code(room, "room"),
            "row": cls._code(row, "row"),
            "column": cls._code(column, "column"),
        }
        coords = cls._coordinates(x, y, z)
        normalized_u = None if u_position is None else int(u_position)
        if normalized_u is not None and not 1 <= normalized_u <= 60:
            raise ValidationError("field location U position must be between 1 and 60")
        return cls(
            **required,
            floor=cls._optional_code(floor, "floor"),
            zone=cls._optional_code(zone, "zone"),
            rack=cls._optional_code(rack, "rack"),
            rack_face=cls._optional_token(rack_face, "rack face", 16),
            u_position=normalized_u,
            x=coords[0],
            y=coords[1],
            z=coords[2],
        )

    @staticmethod
    def _code(value: str, label: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{0,63}", normalized):
            raise ValidationError(f"field location {label} is invalid")
        return normalized

    @classmethod
    def _optional_code(cls, value: str | None, label: str) -> str | None:
        if value is None or not value.strip():
            return None
        return cls._code(value, label)

    @staticmethod
    def _optional_token(value: str | None, label: str, maximum: int) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(rf"[a-z0-9][a-z0-9.-]{{0,{maximum - 1}}}", normalized):
            raise ValidationError(f"field location {label} is invalid")
        return normalized

    @staticmethod
    def _coordinates(
        x: float | None, y: float | None, z: float | None
    ) -> tuple[float | None, float | None, float | None]:
        if x is None and y is None and z is None:
            return None, None, None
        if x is None or y is None or z is None:
            raise ValidationError("field location coordinates require x, y and z together")
        normalized = (float(x), float(y), float(z))
        if min(normalized) < 0:
            raise ValidationError("field location coordinates cannot be negative")
        return normalized

    def human_path(self) -> str:
        parts = [self.site, self.building]
        if self.floor:
            parts.append(self.floor)
        parts.extend((self.room, f"{self.row}/{self.column}"))
        if self.zone:
            parts.append(self.zone)
        if self.rack:
            rack = self.rack
            if self.rack_face:
                rack += f"/{self.rack_face}"
            if self.u_position is not None:
                rack += f"/U{self.u_position}"
            parts.append(rack)
        if self.x is not None and self.y is not None and self.z is not None:
            parts.append(f"XYZ:{self.x:.2f}/{self.y:.2f}/{self.z:.2f}")
        return " / ".join(parts)

    def as_dict(self) -> dict[str, object]:
        return {
            "site": self.site,
            "building": self.building,
            "floor": self.floor,
            "room": self.room,
            "row": self.row,
            "column": self.column,
            "zone": self.zone,
            "rack": self.rack,
            "rack_face": self.rack_face,
            "u_position": self.u_position,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "human_path": self.human_path(),
        }


@dataclass(frozen=True, slots=True)
class FieldSafetyWarning:
    code: str
    severity: Severity
    message: str
    source: str

    @classmethod
    def create(cls, code: str, severity: str, message: str, source: str) -> Self:
        normalized_code = code.strip().upper().replace("-", "_")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", normalized_code):
            raise ValidationError("field safety warning code is invalid")
        try:
            normalized_severity = Severity(severity.strip().lower())
        except ValueError as exc:
            raise ValidationError("field safety warning severity is invalid") from exc
        normalized_message = " ".join(message.strip().split())
        normalized_source = source.strip().lower().replace("_", "-")
        if not 5 <= len(normalized_message) <= 1000:
            raise ValidationError("field safety warning message must contain 5 to 1000 characters")
        if not re.fullmatch(r"[a-z][a-z0-9.-]{1,63}", normalized_source):
            raise ValidationError("field safety warning source is invalid")
        return cls(normalized_code, normalized_severity, normalized_message, normalized_source)

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class FieldChecklistItem:
    id: EntityId
    phase: ChecklistPhase
    order: int
    title: str
    instruction: str
    required: bool
    result: ChecklistResult
    operator_note: str | None
    verified_by: str | None
    verified_at: datetime | None

    @classmethod
    def create(
        cls,
        phase: str,
        order: int,
        title: str,
        instruction: str,
        required: bool = True,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            phase=phase,
            order=order,
            title=title,
            instruction=instruction,
            required=required,
            result=ChecklistResult.PENDING.value,
            operator_note=None,
            verified_by=None,
            verified_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        phase: str,
        order: int,
        title: str,
        instruction: str,
        required: bool,
        result: str,
        operator_note: str | None,
        verified_by: str | None,
        verified_at: datetime | None,
    ) -> Self:
        try:
            normalized_phase = ChecklistPhase(phase.strip().lower())
            normalized_result = ChecklistResult(result.strip().lower())
        except ValueError as exc:
            raise ValidationError("field checklist phase or result is invalid") from exc
        normalized_order = int(order)
        if not 1 <= normalized_order <= 100:
            raise ValidationError("field checklist order must be between 1 and 100")
        normalized_title = FieldRules.text(title, "field checklist title", 2, 120)
        normalized_instruction = FieldRules.text(
            instruction, "field checklist instruction", 5, 1000
        )
        note = FieldRules.optional_text(operator_note, "field checklist note", 1000)
        actor = FieldRules.optional_actor(verified_by)
        timestamp = FieldRules.optional_datetime(verified_at, "field checklist verified_at")
        if normalized_result is ChecklistResult.PENDING:
            actor = None
            timestamp = None
        elif actor is None or timestamp is None:
            raise ValidationError("completed checklist item requires operator and timestamp")
        return cls(
            id=id,
            phase=normalized_phase,
            order=normalized_order,
            title=normalized_title,
            instruction=normalized_instruction,
            required=bool(required),
            result=normalized_result,
            operator_note=note,
            verified_by=actor,
            verified_at=timestamp,
        )

    def record(self, result: str, operator_note: str | None, actor: str) -> Self:
        normalized_result = ChecklistResult(result.strip().lower())
        if normalized_result is ChecklistResult.PENDING:
            raise ValidationError("field checklist result cannot be reset to pending")
        return self.restore(
            id=self.id,
            phase=self.phase.value,
            order=self.order,
            title=self.title,
            instruction=self.instruction,
            required=self.required,
            result=normalized_result.value,
            operator_note=operator_note,
            verified_by=actor,
            verified_at=datetime.now(UTC),
        )

    def accepted(self) -> bool:
        return self.result in (ChecklistResult.PASSED, ChecklistResult.NOT_APPLICABLE)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "phase": self.phase.value,
            "order": self.order,
            "title": self.title,
            "instruction": self.instruction,
            "required": self.required,
            "result": self.result.value,
            "operator_note": self.operator_note,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


@dataclass(frozen=True, slots=True)
class FieldOperationSheet:
    id: EntityId
    tenant_id: TenantId
    target_type: FieldTargetType
    target_id: str
    title: str
    purpose: str
    owner: str
    operator: str
    location: FieldPhysicalLocation
    source_object_key: str | None
    qr_payload: str
    barcode: str
    checklist: tuple[FieldChecklistItem, ...]
    warnings: tuple[FieldSafetyWarning, ...]
    status: FieldOperationStatus
    version: int
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        target_type: str,
        target_id: str,
        title: str,
        purpose: str,
        owner: str,
        operator: str,
        location: FieldPhysicalLocation,
        source_object_key: str | None,
        warnings: tuple[FieldSafetyWarning, ...],
        actor: str,
    ) -> Self:
        now = datetime.now(UTC)
        identifier = EntityId.new()
        normalized_target_type = FieldTargetType.from_value(target_type)
        normalized_target_id = FieldRules.reference(target_id, "field target id")
        qr_payload = FieldRules.qr_payload(
            tenant_id, identifier, normalized_target_type, normalized_target_id
        )
        return cls.restore(
            id=identifier,
            tenant_id=tenant_id,
            target_type=normalized_target_type.value,
            target_id=normalized_target_id,
            title=title,
            purpose=purpose,
            owner=owner,
            operator=operator,
            location=location,
            source_object_key=source_object_key,
            qr_payload=qr_payload,
            barcode=FieldRules.barcode(normalized_target_type, normalized_target_id),
            checklist=FieldChecklistFactory.default(),
            warnings=warnings,
            status=FieldOperationStatus.READY.value,
            version=1,
            created_by=actor,
            created_at=now,
            updated_by=actor,
            updated_at=now,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        target_type: str,
        target_id: str,
        title: str,
        purpose: str,
        owner: str,
        operator: str,
        location: FieldPhysicalLocation,
        source_object_key: str | None,
        qr_payload: str,
        barcode: str,
        checklist: tuple[FieldChecklistItem, ...],
        warnings: tuple[FieldSafetyWarning, ...],
        status: str,
        version: int,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
        started_at: datetime | None,
        completed_at: datetime | None,
        cancelled_at: datetime | None,
    ) -> Self:
        normalized_target_type = FieldTargetType.from_value(target_type)
        try:
            normalized_status = FieldOperationStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("field operation status is invalid") from exc
        normalized_version = int(version)
        if normalized_version < 1:
            raise ValidationError("field operation version must be positive")
        normalized_checklist = tuple(sorted(checklist, key=lambda item: (item.phase, item.order)))
        if not normalized_checklist:
            raise ValidationError("field operation checklist cannot be empty")
        return cls(
            id=id,
            tenant_id=tenant_id,
            target_type=normalized_target_type,
            target_id=FieldRules.reference(target_id, "field target id"),
            title=FieldRules.text(title, "field operation title", 3, 200),
            purpose=FieldRules.text(purpose, "field operation purpose", 5, 2000),
            owner=FieldRules.actor(owner),
            operator=FieldRules.actor(operator),
            location=location,
            source_object_key=FieldRules.optional_reference(
                source_object_key, "field source object key"
            ),
            qr_payload=FieldRules.qr(qr_payload),
            barcode=FieldRules.barcode_value(barcode),
            checklist=normalized_checklist,
            warnings=tuple(warnings),
            status=normalized_status,
            version=normalized_version,
            created_by=FieldRules.actor(created_by),
            created_at=FieldRules.normalize_datetime(created_at, "field operation created_at"),
            updated_by=FieldRules.actor(updated_by),
            updated_at=FieldRules.normalize_datetime(updated_at, "field operation updated_at"),
            started_at=FieldRules.optional_datetime(started_at, "field operation started_at"),
            completed_at=FieldRules.optional_datetime(completed_at, "field operation completed_at"),
            cancelled_at=FieldRules.optional_datetime(cancelled_at, "field operation cancelled_at"),
        )

    def start(self, actor: str) -> Self:
        if self.status is not FieldOperationStatus.READY:
            raise ValidationError("only a ready field operation can be started")
        now = datetime.now(UTC)
        return replace(
            self,
            status=FieldOperationStatus.IN_PROGRESS,
            version=self.version + 1,
            updated_by=FieldRules.actor(actor),
            updated_at=now,
            started_at=now,
        )

    def record_checklist(
        self, item_id: str, result: str, operator_note: str | None, actor: str
    ) -> Self:
        if self.status not in (FieldOperationStatus.READY, FieldOperationStatus.IN_PROGRESS):
            raise ValidationError("field checklist cannot be changed in the current state")
        normalized_id = EntityId.from_value(item_id)
        found = False
        items: list[FieldChecklistItem] = []
        for item in self.checklist:
            if item.id == normalized_id:
                items.append(item.record(result, operator_note, actor))
                found = True
            else:
                items.append(item)
        if not found:
            raise ValidationError("field checklist item does not exist")
        return replace(
            self,
            checklist=tuple(items),
            version=self.version + 1,
            updated_by=FieldRules.actor(actor),
            updated_at=datetime.now(UTC),
        )

    def complete(self, actor: str, evidence: tuple[FieldEvidence, ...]) -> Self:
        if self.status is not FieldOperationStatus.IN_PROGRESS:
            raise ValidationError("only an in-progress field operation can be completed")
        incomplete = [
            item.title for item in self.checklist if item.required and not item.accepted()
        ]
        if incomplete:
            raise ValidationError(
                "required field checklist items are incomplete: " + ", ".join(incomplete)
            )
        validated_phases = {
            item.phase for item in evidence if item.status is EvidenceStatus.VALIDATED
        }
        if (
            EvidencePhase.BEFORE not in validated_phases
            or EvidencePhase.AFTER not in validated_phases
        ):
            raise ValidationError("validated before and after evidence are required")
        now = datetime.now(UTC)
        return replace(
            self,
            status=FieldOperationStatus.COMPLETED,
            version=self.version + 1,
            updated_by=FieldRules.actor(actor),
            updated_at=now,
            completed_at=now,
        )

    def cancel(self, actor: str) -> Self:
        if self.status in (FieldOperationStatus.COMPLETED, FieldOperationStatus.CANCELLED):
            raise ValidationError("field operation is already closed")
        now = datetime.now(UTC)
        return replace(
            self,
            status=FieldOperationStatus.CANCELLED,
            version=self.version + 1,
            updated_by=FieldRules.actor(actor),
            updated_at=now,
            cancelled_at=now,
        )

    def verify_qr(self, payload: str) -> bool:
        submitted = hashlib.sha256(payload.strip().encode()).digest()
        expected = hashlib.sha256(self.qr_payload.encode()).digest()
        return hmac.compare_digest(submitted, expected)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "target_type": self.target_type.value,
            "target_id": self.target_id,
            "title": self.title,
            "purpose": self.purpose,
            "owner": self.owner,
            "operator": self.operator,
            "location": self.location.as_dict(),
            "source_object_key": self.source_object_key,
            "qr_payload": self.qr_payload,
            "barcode": self.barcode,
            "checklist": [item.as_dict() for item in self.checklist],
            "warnings": [item.as_dict() for item in self.warnings],
            "status": self.status.value,
            "version": self.version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }


@dataclass(frozen=True, slots=True)
class FieldEvidence:
    id: EntityId
    tenant_id: TenantId
    sheet_id: EntityId
    phase: EvidencePhase
    media_type: str
    filename: str
    content_base64: str
    content_sha256: str
    size_bytes: int
    caption: str
    status: EvidenceStatus
    attached_by: str
    attached_at: datetime
    validated_by: str | None
    validated_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        sheet_id: EntityId,
        phase: str,
        media_type: str,
        filename: str,
        content_base64: str,
        caption: str,
        actor: str,
    ) -> Self:
        try:
            normalized_phase = EvidencePhase(phase.strip().lower())
        except ValueError as exc:
            raise ValidationError("field evidence phase must be before or after") from exc
        normalized_media = media_type.strip().lower()
        if normalized_media not in ("image/jpeg", "image/png", "image/webp", "application/pdf"):
            raise ValidationError("field evidence media type is unsupported")
        normalized_filename = FieldRules.filename(filename)
        normalized_content, decoded = FieldRules.base64_content(content_base64)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            sheet_id=sheet_id,
            phase=normalized_phase,
            media_type=normalized_media,
            filename=normalized_filename,
            content_base64=normalized_content,
            content_sha256=hashlib.sha256(decoded).hexdigest(),
            size_bytes=len(decoded),
            caption=FieldRules.text(caption, "field evidence caption", 2, 500),
            status=EvidenceStatus.ATTACHED,
            attached_by=FieldRules.actor(actor),
            attached_at=datetime.now(UTC),
            validated_by=None,
            validated_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        sheet_id: EntityId,
        phase: str,
        media_type: str,
        filename: str,
        content_base64: str,
        content_sha256: str,
        size_bytes: int,
        caption: str,
        status: str,
        attached_by: str,
        attached_at: datetime,
        validated_by: str | None,
        validated_at: datetime | None,
    ) -> Self:
        evidence = cls.create(
            tenant_id=tenant_id,
            sheet_id=sheet_id,
            phase=phase,
            media_type=media_type,
            filename=filename,
            content_base64=content_base64,
            caption=caption,
            actor=attached_by,
        )
        try:
            normalized_status = EvidenceStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("field evidence status is invalid") from exc
        if evidence.content_sha256 != content_sha256.strip().lower():
            raise ValidationError("field evidence checksum mismatch")
        if evidence.size_bytes != int(size_bytes):
            raise ValidationError("field evidence size mismatch")
        return replace(
            evidence,
            id=id,
            status=normalized_status,
            attached_at=FieldRules.normalize_datetime(attached_at, "field evidence attached_at"),
            validated_by=FieldRules.optional_actor(validated_by),
            validated_at=FieldRules.optional_datetime(validated_at, "field evidence validated_at"),
        )

    def validate(self, actor: str) -> Self:
        if self.status is EvidenceStatus.VALIDATED:
            return self
        now = datetime.now(UTC)
        return replace(
            self,
            status=EvidenceStatus.VALIDATED,
            validated_by=FieldRules.actor(actor),
            validated_at=now,
        )

    def as_dict(self, include_content: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "sheet_id": self.sheet_id.value,
            "phase": self.phase.value,
            "media_type": self.media_type,
            "filename": self.filename,
            "content_sha256": self.content_sha256,
            "size_bytes": self.size_bytes,
            "caption": self.caption,
            "status": self.status.value,
            "attached_by": self.attached_by,
            "attached_at": self.attached_at.isoformat(),
            "validated_by": self.validated_by,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
        }
        if include_content:
            payload["content_base64"] = self.content_base64
        return payload


@dataclass(frozen=True, slots=True)
class InterventionLock:
    id: EntityId
    tenant_id: TenantId
    sheet_id: EntityId
    target_type: FieldTargetType
    target_id: str
    idempotency_key: str
    owner: str
    status: InterventionLockStatus
    acquired_at: datetime
    expires_at: datetime
    released_at: datetime | None
    released_by: str | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        sheet_id: EntityId,
        target_type: str,
        target_id: str,
        idempotency_key: str,
        owner: str,
        ttl_seconds: int,
    ) -> Self:
        ttl = int(ttl_seconds)
        if not 60 <= ttl <= 86_400:
            raise ValidationError("intervention lock ttl must be between 60 and 86400 seconds")
        acquired_at = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            sheet_id=sheet_id,
            target_type=FieldTargetType.from_value(target_type),
            target_id=FieldRules.reference(target_id, "field target id"),
            idempotency_key=FieldRules.idempotency_key(idempotency_key),
            owner=FieldRules.actor(owner),
            status=InterventionLockStatus.ACTIVE,
            acquired_at=acquired_at,
            expires_at=acquired_at + timedelta(seconds=ttl),
            released_at=None,
            released_by=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        sheet_id: EntityId,
        target_type: str,
        target_id: str,
        idempotency_key: str,
        owner: str,
        status: str,
        acquired_at: datetime,
        expires_at: datetime,
        released_at: datetime | None,
        released_by: str | None,
    ) -> Self:
        try:
            normalized_status = InterventionLockStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("intervention lock status is invalid") from exc
        acquired = FieldRules.normalize_datetime(acquired_at, "intervention lock acquired_at")
        expires = FieldRules.normalize_datetime(expires_at, "intervention lock expires_at")
        if expires <= acquired:
            raise ValidationError("intervention lock expiration must be after acquisition")
        normalized_released_at = FieldRules.optional_datetime(
            released_at, "intervention lock released_at"
        )
        normalized_released_by = FieldRules.optional_actor(released_by)
        if normalized_status is InterventionLockStatus.RELEASED and (
            normalized_released_at is None or normalized_released_by is None
        ):
            raise ValidationError("released intervention lock requires actor and timestamp")
        return cls(
            id=id,
            tenant_id=tenant_id,
            sheet_id=sheet_id,
            target_type=FieldTargetType.from_value(target_type),
            target_id=FieldRules.reference(target_id, "field target id"),
            idempotency_key=FieldRules.idempotency_key(idempotency_key),
            owner=FieldRules.actor(owner),
            status=normalized_status,
            acquired_at=acquired,
            expires_at=expires,
            released_at=normalized_released_at,
            released_by=normalized_released_by,
        )

    def active(self, now: datetime | None = None) -> bool:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        return self.status is InterventionLockStatus.ACTIVE and self.expires_at > current

    def release(self, actor: str) -> Self:
        if self.status is InterventionLockStatus.RELEASED:
            return self
        return replace(
            self,
            status=InterventionLockStatus.RELEASED,
            released_at=datetime.now(UTC),
            released_by=FieldRules.actor(actor),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "sheet_id": self.sheet_id.value,
            "target_type": self.target_type.value,
            "target_id": self.target_id,
            "idempotency_key": self.idempotency_key,
            "owner": self.owner,
            "status": self.status.value,
            "active": self.active(),
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "released_by": self.released_by,
        }


@dataclass(frozen=True, slots=True)
class OfflineSyncPackage:
    id: EntityId
    tenant_id: TenantId
    sheet_id: EntityId
    idempotency_key: str
    authorized_site: str
    payload: dict[str, object]
    payload_sha256: str
    status: OfflinePackageStatus
    created_by: str
    created_at: datetime
    expires_at: datetime
    synchronized_by: str | None
    synchronized_at: datetime | None
    client_payload_sha256: str | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        sheet: FieldOperationSheet,
        evidence: tuple[FieldEvidence, ...],
        idempotency_key: str,
        ttl_seconds: int,
        actor: str,
    ) -> Self:
        ttl = int(ttl_seconds)
        if not 300 <= ttl <= 604_800:
            raise ValidationError("offline package ttl must be between 300 and 604800 seconds")
        payload = {
            "schema_version": 1,
            "sheet": sheet.as_dict(),
            "evidence": [item.as_dict(include_content=False) for item in evidence],
            "authorized_scope": {"tenant_id": tenant_id.value, "site": sheet.location.site},
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        now = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            sheet_id=sheet.id,
            idempotency_key=FieldRules.idempotency_key(idempotency_key),
            authorized_site=sheet.location.site,
            payload=payload,
            payload_sha256=hashlib.sha256(serialized).hexdigest(),
            status=OfflinePackageStatus.READY,
            created_by=FieldRules.actor(actor),
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            synchronized_by=None,
            synchronized_at=None,
            client_payload_sha256=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        sheet_id: EntityId,
        idempotency_key: str,
        authorized_site: str,
        payload: dict[str, object],
        payload_sha256: str,
        status: str,
        created_by: str,
        created_at: datetime,
        expires_at: datetime,
        synchronized_by: str | None,
        synchronized_at: datetime | None,
        client_payload_sha256: str | None,
    ) -> Self:
        try:
            normalized_status = OfflinePackageStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("offline package status is invalid") from exc
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        normalized_hash = FieldRules.sha256(payload_sha256, "offline package payload hash")
        if hashlib.sha256(serialized).hexdigest() != normalized_hash:
            raise ValidationError("offline package payload checksum mismatch")
        created = FieldRules.normalize_datetime(created_at, "offline package created_at")
        expires = FieldRules.normalize_datetime(expires_at, "offline package expires_at")
        if expires <= created:
            raise ValidationError("offline package expiration must be after creation")
        return cls(
            id=id,
            tenant_id=tenant_id,
            sheet_id=sheet_id,
            idempotency_key=FieldRules.idempotency_key(idempotency_key),
            authorized_site=FieldPhysicalLocation._code(authorized_site, "site"),
            payload=payload,
            payload_sha256=normalized_hash,
            status=normalized_status,
            created_by=FieldRules.actor(created_by),
            created_at=created,
            expires_at=expires,
            synchronized_by=FieldRules.optional_actor(synchronized_by),
            synchronized_at=FieldRules.optional_datetime(
                synchronized_at, "offline package synchronized_at"
            ),
            client_payload_sha256=(
                None
                if client_payload_sha256 is None
                else FieldRules.sha256(client_payload_sha256, "offline package client payload hash")
            ),
        )

    def expired(self, now: datetime | None = None) -> bool:
        return self.expires_at <= (now or datetime.now(UTC)).astimezone(UTC)

    def synchronize(self, client_payload_sha256: str, actor: str) -> Self:
        if self.status is OfflinePackageStatus.REVOKED:
            raise ValidationError("offline package is revoked")
        if self.expired():
            raise ValidationError("offline package is expired")
        normalized_hash = FieldRules.sha256(client_payload_sha256, "offline package client hash")
        if normalized_hash != self.payload_sha256:
            raise ValidationError("offline package checksum mismatch")
        if self.status is OfflinePackageStatus.SYNCHRONIZED:
            return self
        now = datetime.now(UTC)
        return replace(
            self,
            status=OfflinePackageStatus.SYNCHRONIZED,
            synchronized_by=FieldRules.actor(actor),
            synchronized_at=now,
            client_payload_sha256=normalized_hash,
        )

    def as_dict(self, include_payload: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "sheet_id": self.sheet_id.value,
            "idempotency_key": self.idempotency_key,
            "authorized_site": self.authorized_site,
            "payload_sha256": self.payload_sha256,
            "status": self.status.value,
            "expired": self.expired(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "synchronized_by": self.synchronized_by,
            "synchronized_at": self.synchronized_at.isoformat() if self.synchronized_at else None,
            "client_payload_sha256": self.client_payload_sha256,
        }
        if include_payload:
            result["payload"] = self.payload
        return result


class FieldChecklistFactory:
    @classmethod
    def default(cls) -> tuple[FieldChecklistItem, ...]:
        definitions = (
            ("before", 1, "Vérifier le QR", "Scanner le QR et confirmer la cible physique.", True),
            (
                "before",
                2,
                "Lire les avertissements",
                "Lire les impacts, flux, alimentation et SPOF avant manipulation.",
                True,
            ),
            (
                "before",
                3,
                "Photographier avant",
                "Joindre une preuve visuelle avant intervention.",
                True,
            ),
            (
                "before",
                4,
                "Sécuriser la zone",
                "Confirmer l'absence de risque immédiat pour les personnes et équipements.",
                True,
            ),
            (
                "after",
                1,
                "Contrôler la cible",
                "Vérifier l'état final et la cohérence de la localisation.",
                True,
            ),
            (
                "after",
                2,
                "Photographier après",
                "Joindre une preuve visuelle après intervention.",
                True,
            ),
            (
                "after",
                3,
                "Rétablir le service",
                "Confirmer le rétablissement attendu ou documenter l'exception.",
                True,
            ),
            (
                "after",
                4,
                "Libérer le verrou",
                "Libérer le verrou logique d'intervention.",
                True,
            ),
        )
        return tuple(FieldChecklistItem.create(*definition) for definition in definitions)


class FieldRules:
    _MAX_EVIDENCE_BYTES = 2 * 1024 * 1024

    @staticmethod
    def text(value: str, label: str, minimum: int, maximum: int) -> str:
        normalized = " ".join(value.strip().split())
        if not minimum <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain {minimum} to {maximum} characters")
        return normalized

    @classmethod
    def optional_text(cls, value: str | None, label: str, maximum: int) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.text(value, label, 1, maximum)

    @staticmethod
    def actor(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@:-]{1,127}", normalized):
            raise ValidationError("field actor must use 2 to 128 safe characters")
        return normalized

    @classmethod
    def optional_actor(cls, value: str | None) -> str | None:
        return None if value is None or not value.strip() else cls.actor(value)

    @staticmethod
    def reference(value: str, label: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/@-]{0,255}", normalized):
            raise ValidationError(f"{label} is invalid")
        return normalized

    @classmethod
    def optional_reference(cls, value: str | None, label: str) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.reference(value, label)

    @staticmethod
    def idempotency_key(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}", normalized):
            raise ValidationError("field idempotency key must use 8 to 128 safe characters")
        return normalized

    @staticmethod
    def normalize_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def optional_datetime(cls, value: datetime | None, label: str) -> datetime | None:
        return None if value is None else cls.normalize_datetime(value, label)

    @staticmethod
    def sha256(value: str, label: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValidationError(f"{label} must be a SHA-256 hexadecimal digest")
        return normalized

    @staticmethod
    def filename(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,199}", normalized):
            raise ValidationError("field evidence filename is invalid")
        if ".." in normalized or "/" in normalized or "\\" in normalized:
            raise ValidationError("field evidence filename contains a forbidden path")
        return normalized

    @classmethod
    def base64_content(cls, value: str) -> tuple[str, bytes]:
        normalized = "".join(value.strip().split())
        try:
            decoded = base64.b64decode(normalized, validate=True)
        except ValueError as exc:
            raise ValidationError("field evidence content must be valid base64") from exc
        if not 1 <= len(decoded) <= cls._MAX_EVIDENCE_BYTES:
            raise ValidationError("field evidence must contain 1 byte to 2 MiB")
        return base64.b64encode(decoded).decode("ascii"), decoded

    @staticmethod
    def qr_payload(
        tenant_id: TenantId,
        sheet_id: EntityId,
        target_type: FieldTargetType,
        target_id: str,
    ) -> str:
        core = f"OIF1|{tenant_id.value}|{sheet_id.value}|{target_type.value}|{target_id}"
        checksum = hashlib.sha256(core.encode()).hexdigest()[:16]
        payload = f"{core}|{checksum}"
        if len(payload.encode()) > 500:
            raise ValidationError("field QR payload exceeds supported capacity")
        return payload

    @staticmethod
    def qr(value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("OIF1|") or len(normalized.encode()) > 500:
            raise ValidationError("field QR payload is invalid")
        parts = normalized.split("|")
        if len(parts) != 6:
            raise ValidationError("field QR payload is invalid")
        core = "|".join(parts[:5])
        expected = hashlib.sha256(core.encode()).hexdigest()[:16]
        if parts[5] != expected:
            raise ValidationError("field QR payload checksum is invalid")
        return normalized

    @staticmethod
    def barcode(target_type: FieldTargetType, target_id: str) -> str:
        digest = hashlib.sha256(f"{target_type.value}:{target_id}".encode()).hexdigest()[:16]
        prefix = target_type.value.upper().replace("-", "")[:6]
        return f"OI-{prefix}-{digest.upper()}"

    @staticmethod
    def barcode_value(value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"OI-[A-Z0-9]{3,6}-[A-F0-9]{16}", normalized):
            raise ValidationError("field barcode is invalid")
        return normalized
