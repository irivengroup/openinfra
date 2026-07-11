from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.field_operations import (
    ChecklistResult,
    EvidencePhase,
    EvidenceStatus,
    FieldChecklistItem,
    FieldEvidence,
    FieldOperationSheet,
    FieldOperationStatus,
    FieldPhysicalLocation,
    FieldRules,
    FieldSafetyWarning,
    FieldTargetType,
    InterventionLock,
    OfflinePackageStatus,
    OfflineSyncPackage,
)


def _location() -> FieldPhysicalLocation:
    return FieldPhysicalLocation.create(
        site="PAR1",
        building="BAT-A",
        floor="L01",
        room="MMR1",
        row="A",
        column="01",
        zone="Z1",
        rack="R01",
        rack_face="front",
        u_position=12,
        x=1.0,
        y=2.0,
        z=3.0,
    )


def _sheet() -> FieldOperationSheet:
    return FieldOperationSheet.create(
        tenant_id=TenantId.from_value("default"),
        target_type="equipment",
        target_id="PAR-SRV-001",
        title="Remplacement alimentation",
        purpose="Remplacer le bloc d'alimentation défectueux.",
        owner="ops.owner",
        operator="field.operator",
        location=_location(),
        source_object_key="device/PAR-SRV-001",
        warnings=(),
        actor="pytest.actor",
    )


def _evidence(sheet: FieldOperationSheet, phase: str) -> FieldEvidence:
    return FieldEvidence.create(
        tenant_id=sheet.tenant_id,
        sheet_id=sheet.id,
        phase=phase,
        media_type="image/png",
        filename=f"{phase}.png",
        content_base64=base64.b64encode(f"evidence-{phase}".encode()).decode(),
        caption=f"Preuve {phase}",
        actor="field.operator",
    )


def test_physical_location_validates_and_exposes_human_path() -> None:
    location = _location()

    assert location.human_path() == (
        "PAR1 / BAT-A / L01 / MMR1 / A/01 / Z1 / R01/front/U12 / XYZ:1.00/2.00/3.00"
    )
    assert location.as_dict()["human_path"] == location.human_path()

    with pytest.raises(ValidationError):
        FieldPhysicalLocation.create(
            site="PAR1",
            building="BAT-A",
            room="MMR1",
            row="A",
            column="01",
            x=1.0,
        )


def test_sheet_requires_checklist_and_validated_before_after_evidence() -> None:
    sheet = _sheet()
    assert sheet.verify_qr(sheet.qr_payload) is True
    assert sheet.verify_qr(f"{sheet.qr_payload}x") is False

    started = sheet.start("field.operator")
    assert started.status is FieldOperationStatus.IN_PROGRESS
    with pytest.raises(ValidationError, match="checklist"):
        started.complete("field.operator", ())

    completed_checklist = started
    for item in started.checklist:
        completed_checklist = completed_checklist.record_checklist(
            item.id.value,
            "passed",
            "Contrôle réalisé",
            "field.operator",
        )
    before = _evidence(sheet, "before").validate("field.supervisor")
    after = _evidence(sheet, "after").validate("field.supervisor")
    completed = completed_checklist.complete("field.operator", (before, after))

    assert completed.status is FieldOperationStatus.COMPLETED
    assert completed.completed_at is not None


def test_evidence_is_bounded_hashed_and_immutable_by_restore_contract() -> None:
    sheet = _sheet()
    evidence = _evidence(sheet, "before")

    assert evidence.phase is EvidencePhase.BEFORE
    assert evidence.status is EvidenceStatus.ATTACHED
    assert evidence.size_bytes == len(b"evidence-before")
    assert "content_base64" not in evidence.as_dict()
    assert evidence.as_dict(include_content=True)["content_base64"] == evidence.content_base64
    assert evidence.validate("field.supervisor").status is EvidenceStatus.VALIDATED

    with pytest.raises(ValidationError, match="checksum"):
        FieldEvidence.restore(
            id=evidence.id,
            tenant_id=evidence.tenant_id,
            sheet_id=evidence.sheet_id,
            phase=evidence.phase.value,
            media_type=evidence.media_type,
            filename=evidence.filename,
            content_base64=evidence.content_base64,
            content_sha256="0" * 64,
            size_bytes=evidence.size_bytes,
            caption=evidence.caption,
            status=evidence.status.value,
            attached_by=evidence.attached_by,
            attached_at=evidence.attached_at,
            validated_by=evidence.validated_by,
            validated_at=evidence.validated_at,
        )

    with pytest.raises(ValidationError, match="2 MiB"):
        FieldEvidence.create(
            tenant_id=sheet.tenant_id,
            sheet_id=sheet.id,
            phase="before",
            media_type="image/png",
            filename="oversize.png",
            content_base64=base64.b64encode(b"x" * (2 * 1024 * 1024 + 1)).decode(),
            caption="Preuve trop volumineuse",
            actor="field.operator",
        )


def test_intervention_lock_is_idempotent_to_release_and_expires() -> None:
    sheet = _sheet()
    lock = InterventionLock.create(
        tenant_id=sheet.tenant_id,
        sheet_id=sheet.id,
        target_type=sheet.target_type.value,
        target_id=sheet.target_id,
        idempotency_key="field-lock-0001",
        owner="field.operator",
        ttl_seconds=60,
    )

    assert lock.active() is True
    assert lock.active(lock.expires_at + timedelta(seconds=1)) is False
    released = lock.release("field.operator")
    assert released.active() is False
    assert released.release("field.operator") == released


def test_offline_package_checksum_expiry_and_sync_are_enforced() -> None:
    sheet = _sheet()
    package = OfflineSyncPackage.create(
        tenant_id=sheet.tenant_id,
        sheet=sheet,
        evidence=(),
        idempotency_key="offline-package-0001",
        ttl_seconds=300,
        actor="field.operator",
    )

    with pytest.raises(ValidationError, match="checksum"):
        package.synchronize("0" * 64, "field.operator")

    synchronized = package.synchronize(package.payload_sha256, "field.operator")
    assert synchronized.status is OfflinePackageStatus.SYNCHRONIZED
    assert synchronized.synchronize(package.payload_sha256, "field.operator") == synchronized

    expired = OfflineSyncPackage.restore(
        id=package.id,
        tenant_id=package.tenant_id,
        sheet_id=package.sheet_id,
        idempotency_key=package.idempotency_key,
        authorized_site=package.authorized_site,
        payload=package.payload,
        payload_sha256=package.payload_sha256,
        status=package.status.value,
        created_by=package.created_by,
        created_at=datetime.now(UTC) - timedelta(hours=2),
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        synchronized_by=None,
        synchronized_at=None,
        client_payload_sha256=None,
    )
    with pytest.raises(ValidationError, match="expired"):
        expired.synchronize(expired.payload_sha256, "field.operator")


def test_field_operation_domain_rejects_invalid_enums_locations_and_warnings() -> None:
    with pytest.raises(ValidationError, match="target type"):
        FieldTargetType.from_value("unsupported")
    with pytest.raises(ValidationError, match="U position"):
        FieldPhysicalLocation.create(
            site="PAR1", building="BAT-A", room="MMR1", row="A", column="01", u_position=61
        )
    with pytest.raises(ValidationError, match="site"):
        FieldPhysicalLocation.create(
            site="bad value", building="BAT-A", room="MMR1", row="A", column="01"
        )
    with pytest.raises(ValidationError, match="rack face"):
        FieldPhysicalLocation.create(
            site="PAR1",
            building="BAT-A",
            room="MMR1",
            row="A",
            column="01",
            rack_face="bad face!",
        )
    with pytest.raises(ValidationError, match="negative"):
        FieldPhysicalLocation.create(
            site="PAR1",
            building="BAT-A",
            room="MMR1",
            row="A",
            column="01",
            x=-1,
            y=0,
            z=0,
        )

    invalid_warnings = (
        ("x", "warning", "message valide", "field", "code"),
        ("VALID_CODE", "unknown", "message valide", "field", "severity"),
        ("VALID_CODE", "warning", "bad", "field", "message"),
        ("VALID_CODE", "warning", "message valide", "!", "source"),
    )
    for code, severity, message, source, expected in invalid_warnings:
        with pytest.raises(ValidationError, match=expected):
            FieldSafetyWarning.create(code, severity, message, source)


def test_field_checklist_and_sheet_restore_validation_edges() -> None:
    item = FieldChecklistItem.create("before", 1, "Titre", "Instruction complète")
    with pytest.raises(ValidationError, match="phase or result"):
        FieldChecklistItem.restore(
            id=item.id,
            phase="invalid",
            order=1,
            title=item.title,
            instruction=item.instruction,
            required=True,
            result="pending",
            operator_note=None,
            verified_by=None,
            verified_at=None,
        )
    with pytest.raises(ValidationError, match="order"):
        FieldChecklistItem.restore(
            id=item.id,
            phase="before",
            order=0,
            title=item.title,
            instruction=item.instruction,
            required=True,
            result="pending",
            operator_note=None,
            verified_by=None,
            verified_at=None,
        )
    with pytest.raises(ValidationError, match="operator and timestamp"):
        FieldChecklistItem.restore(
            id=item.id,
            phase="before",
            order=1,
            title=item.title,
            instruction=item.instruction,
            required=True,
            result="passed",
            operator_note=None,
            verified_by=None,
            verified_at=None,
        )
    with pytest.raises(ValidationError, match="pending"):
        item.record(ChecklistResult.PENDING.value, None, "field.operator")

    sheet = _sheet()
    kwargs = {
        "id": sheet.id,
        "tenant_id": sheet.tenant_id,
        "target_type": sheet.target_type.value,
        "target_id": sheet.target_id,
        "title": sheet.title,
        "purpose": sheet.purpose,
        "owner": sheet.owner,
        "operator": sheet.operator,
        "location": sheet.location,
        "source_object_key": sheet.source_object_key,
        "qr_payload": sheet.qr_payload,
        "barcode": sheet.barcode,
        "checklist": sheet.checklist,
        "warnings": sheet.warnings,
        "status": sheet.status.value,
        "version": sheet.version,
        "created_by": sheet.created_by,
        "created_at": sheet.created_at,
        "updated_by": sheet.updated_by,
        "updated_at": sheet.updated_at,
        "started_at": sheet.started_at,
        "completed_at": sheet.completed_at,
        "cancelled_at": sheet.cancelled_at,
    }
    for changes, expected in (
        ({"status": "invalid"}, "status"),
        ({"version": 0}, "version"),
        ({"checklist": ()}, "checklist"),
    ):
        with pytest.raises(ValidationError, match=expected):
            FieldOperationSheet.restore(**(kwargs | changes))  # type: ignore[arg-type]

    started = sheet.start("field.operator")
    with pytest.raises(ValidationError, match="ready"):
        started.start("field.operator")
    with pytest.raises(ValidationError, match="does not exist"):
        started.record_checklist(EntityId.new().value, "passed", None, "field.operator")
    with pytest.raises(ValidationError, match="before and after"):
        completed_checklist = started
        for checklist_item in started.checklist:
            completed_checklist = completed_checklist.record_checklist(
                checklist_item.id.value, "passed", None, "field.operator"
            )
        completed_checklist.complete("field.operator", ())
    cancelled = sheet.cancel("field.operator")
    with pytest.raises(ValidationError, match="already closed"):
        cancelled.cancel("field.operator")


def test_evidence_lock_offline_restore_and_field_rules_validation_edges() -> None:
    sheet = _sheet()
    evidence = _evidence(sheet, "before")
    evidence_kwargs = {
        "id": evidence.id,
        "tenant_id": evidence.tenant_id,
        "sheet_id": evidence.sheet_id,
        "phase": evidence.phase.value,
        "media_type": evidence.media_type,
        "filename": evidence.filename,
        "content_base64": evidence.content_base64,
        "content_sha256": evidence.content_sha256,
        "size_bytes": evidence.size_bytes,
        "caption": evidence.caption,
        "status": evidence.status.value,
        "attached_by": evidence.attached_by,
        "attached_at": evidence.attached_at,
        "validated_by": evidence.validated_by,
        "validated_at": evidence.validated_at,
    }
    with pytest.raises(ValidationError, match="status"):
        FieldEvidence.restore(**(evidence_kwargs | {"status": "invalid"}))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="size"):
        FieldEvidence.restore(**(evidence_kwargs | {"size_bytes": evidence.size_bytes + 1}))  # type: ignore[arg-type]
    validated = evidence.validate("field.supervisor")
    assert validated.validate("field.supervisor") is validated

    with pytest.raises(ValidationError, match="ttl"):
        InterventionLock.create(
            tenant_id=sheet.tenant_id,
            sheet_id=sheet.id,
            target_type=sheet.target_type.value,
            target_id=sheet.target_id,
            idempotency_key="lock-key-0001",
            owner="field.operator",
            ttl_seconds=1,
        )
    now = datetime.now(UTC)
    lock_restore = {
        "id": EntityId.new(),
        "tenant_id": sheet.tenant_id,
        "sheet_id": sheet.id,
        "target_type": sheet.target_type.value,
        "target_id": sheet.target_id,
        "idempotency_key": "lock-key-0001",
        "owner": "field.operator",
        "status": "active",
        "acquired_at": now,
        "expires_at": now + timedelta(minutes=5),
        "released_at": None,
        "released_by": None,
    }
    for changes, expected in (
        ({"status": "invalid"}, "status"),
        ({"expires_at": now}, "expiration"),
        ({"status": "released"}, "actor and timestamp"),
    ):
        with pytest.raises(ValidationError, match=expected):
            InterventionLock.restore(**(lock_restore | changes))  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="ttl"):
        OfflineSyncPackage.create(
            tenant_id=sheet.tenant_id,
            sheet=sheet,
            evidence=(),
            idempotency_key="offline-key-0001",
            ttl_seconds=1,
            actor="field.operator",
        )
    package = OfflineSyncPackage.create(
        tenant_id=sheet.tenant_id,
        sheet=sheet,
        evidence=(),
        idempotency_key="offline-key-0001",
        ttl_seconds=300,
        actor="field.operator",
    )
    package_restore = {
        "id": package.id,
        "tenant_id": package.tenant_id,
        "sheet_id": package.sheet_id,
        "idempotency_key": package.idempotency_key,
        "authorized_site": package.authorized_site,
        "payload": package.payload,
        "payload_sha256": package.payload_sha256,
        "status": package.status.value,
        "created_by": package.created_by,
        "created_at": package.created_at,
        "expires_at": package.expires_at,
        "synchronized_by": None,
        "synchronized_at": None,
        "client_payload_sha256": None,
    }
    for changes, expected in (
        ({"status": "invalid"}, "status"),
        ({"payload_sha256": "0" * 64}, "checksum"),
        ({"expires_at": package.created_at}, "expiration"),
    ):
        with pytest.raises(ValidationError, match=expected):
            OfflineSyncPackage.restore(**(package_restore | changes))  # type: ignore[arg-type]
    revoked = OfflineSyncPackage.restore(**(package_restore | {"status": "revoked"}))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="revoked"):
        revoked.synchronize(revoked.payload_sha256, "field.operator")

    invalid_calls = (
        lambda: FieldRules.text("x", "text", 2, 3),
        lambda: FieldRules.actor("!"),
        lambda: FieldRules.reference("!", "reference"),
        lambda: FieldRules.idempotency_key("short"),
        lambda: FieldRules.normalize_datetime(datetime.now(), "timestamp"),
        lambda: FieldRules.sha256("bad", "digest"),
        lambda: FieldRules.filename("!bad"),
        lambda: FieldRules.filename("safe..name"),
        lambda: FieldRules.base64_content("%%%"),
        lambda: FieldRules.base64_content(""),
        lambda: FieldRules.qr_payload(sheet.tenant_id, sheet.id, sheet.target_type, "x" * 600),
        lambda: FieldRules.qr("bad"),
        lambda: FieldRules.qr("OIF1|too|few"),
        lambda: FieldRules.qr("OIF1|default|id|equipment|target|deadbeefdeadbeef"),
        lambda: FieldRules.barcode_value("bad"),
    )
    for invalid_call in invalid_calls:
        with pytest.raises(ValidationError):
            invalid_call()
