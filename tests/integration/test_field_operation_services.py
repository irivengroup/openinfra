from __future__ import annotations

import base64
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import LocateEquipmentCommand
from openinfra.application.field_operation_services import (
    AcquireInterventionLockCommand,
    AttachFieldEvidenceCommand,
    CompleteFieldOperationCommand,
    CreateOfflineSyncPackageCommand,
    GenerateFieldOperationSheetCommand,
    GetFieldOperationSheetCommand,
    ListFieldOperationSheetsCommand,
    RecordFieldChecklistCommand,
    ReleaseInterventionLockCommand,
    StartFieldOperationCommand,
    SynchronizeOfflinePackageCommand,
    ValidateFieldEvidenceCommand,
    VerifyFieldQrCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError
from openinfra.domain.field_operations import FieldOperationStatus, OfflinePackageStatus


def _application(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "f" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "field-admin", ("admin",), token)
    )
    app.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="PAR-SRV-001",
            equipment_name="Serveur terrain",
            site="PAR1",
            building="BAT-A",
            floor="F01",
            room="MMR1",
            zone=None,
            row="B",
            column="12",
            rack="R42",
            u_position=12,
            rack_face="front",
            u_height=2,
            x=12.0,
            y=4.0,
            z=0.0,
        )
    )
    return app, token


def test_field_operation_workflow_is_locked_audited_and_offline_capable(
    tmp_path: Path,
) -> None:
    app, token = _application(tmp_path)
    service = app.field_operation_service
    sheet = service.generate_sheet(
        GenerateFieldOperationSheetCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            target_type="equipment",
            target_id="PAR-SRV-001",
            title="Remplacement alimentation",
            purpose="Remplacer le bloc d'alimentation et contrôler le service.",
            owner="ops.owner",
            operator="field.operator",
        )
    )

    assert sheet.location.human_path().startswith("PAR1 / BAT-A / F01 / MMR1")
    assert {warning.code for warning in sheet.warnings} == {
        "POWER_PATH_UNDOCUMENTED",
        "RSOT_LINK_MISSING",
    }
    verified = service.verify_qr(
        VerifyFieldQrCommand("default", token, sheet.id.value, sheet.qr_payload)
    )
    assert verified["verified"] is True

    lock = service.acquire_lock(
        AcquireInterventionLockCommand(
            "default",
            "pytest",
            token,
            sheet.id.value,
            "field-lock-0001",
            3600,
        )
    )
    assert (
        service.acquire_lock(
            AcquireInterventionLockCommand(
                "default", "pytest", token, sheet.id.value, "field-lock-0001", 3600
            )
        )
        == lock
    )

    started = service.start(StartFieldOperationCommand("default", "pytest", token, sheet.id.value))
    assert started.status is FieldOperationStatus.IN_PROGRESS

    current = started
    for item in started.checklist:
        current = service.record_checklist(
            RecordFieldChecklistCommand(
                "default",
                "pytest",
                token,
                sheet.id.value,
                item.id.value,
                "passed",
                "Contrôle terrain validé",
            )
        )

    evidence = []
    for phase in ("before", "after"):
        attached = service.attach_evidence(
            AttachFieldEvidenceCommand(
                "default",
                "pytest",
                token,
                sheet.id.value,
                phase,
                "image/png",
                f"{phase}.png",
                base64.b64encode(f"evidence-{phase}".encode()).decode(),
                f"Photo {phase}",
            )
        )
        evidence.append(
            service.validate_evidence(
                ValidateFieldEvidenceCommand("default", "pytest", token, attached.id.value)
            )
        )

    package = service.create_offline_package(
        CreateOfflineSyncPackageCommand(
            "default",
            "pytest",
            token,
            sheet.id.value,
            "offline-package-0001",
            86400,
        )
    )
    synchronized = service.synchronize_offline_package(
        SynchronizeOfflinePackageCommand(
            "default", "pytest", token, package.id.value, package.payload_sha256
        )
    )
    completed = service.complete(
        CompleteFieldOperationCommand("default", "pytest", token, sheet.id.value)
    )

    assert synchronized.status is OfflinePackageStatus.SYNCHRONIZED
    assert completed.status is FieldOperationStatus.COMPLETED
    assert (
        len(service.list_evidence(GetFieldOperationSheetCommand("default", token, sheet.id.value)))
        == 2
    )
    page = service.list_sheets(ListFieldOperationSheetsCommand("default", token, limit=10))
    assert [item.id for item in page.items] == [sheet.id]
    outbox_names = {item["name"] for item in app.store.data["field_event_outbox"].values()}
    assert {
        "field.sheet.generated",
        "field.operation.locked",
        "field.operation.started",
        "field.checklist.recorded",
        "field.evidence.attached",
        "field.evidence.validated",
        "field.offline.package.created",
        "field.offline.sync.completed",
        "field.operation.completed",
    }.issubset(outbox_names)
    actions = {item["action"] for item in app.store.data["audit_events"]}
    assert {
        "field.sheet.generated",
        "field.operation.locked",
        "field.evidence.attached",
        "field.operation.completed",
        "field.offline.sync.completed",
    }.issubset(actions)


def test_completion_requires_an_active_matching_lock(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    service = app.field_operation_service
    sheet = service.generate_sheet(
        GenerateFieldOperationSheetCommand(
            "default",
            "pytest",
            token,
            "equipment",
            "PAR-SRV-001",
            "Contrôle terrain",
            "Contrôler la cible avant maintenance.",
            "ops.owner",
            "field.operator",
        )
    )
    lock = service.acquire_lock(
        AcquireInterventionLockCommand(
            "default", "pytest", token, sheet.id.value, "field-lock-0002", 3600
        )
    )
    started = service.start(StartFieldOperationCommand("default", "pytest", token, sheet.id.value))
    assert started.status is FieldOperationStatus.IN_PROGRESS
    service.release_lock(ReleaseInterventionLockCommand("default", "pytest", token, lock.id.value))

    with pytest.raises(ConflictError, match="lock"):
        service.complete(CompleteFieldOperationCommand("default", "pytest", token, sheet.id.value))
