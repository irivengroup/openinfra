from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import LocateEquipmentCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI


def test_dcim_field_operation_cli_generate_get_and_list(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "c" * 40
    application = ApplicationFactory().create_json_application(state)
    application.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "field-admin", ("admin",), token)
    )
    application.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="CLI-SRV-001",
            equipment_name="Serveur CLI terrain",
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

    cli = OpenInfraCLI()
    assert (
        cli.run(
            [
                "dcim",
                "field-sheet-generate",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--target-type",
                "equipment",
                "--target-id",
                "CLI-SRV-001",
                "--title",
                "Intervention CLI",
                "--purpose",
                "Valider le parcours terrain depuis la CLI.",
                "--owner",
                "ops.owner",
                "--operator",
                "field.operator",
            ]
        )
        == 0
    )
    generated = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    sheet_id = generated["id"]

    assert (
        cli.run(
            [
                "dcim",
                "field-sheet-get",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--sheet-id",
                sheet_id,
            ]
        )
        == 0
    )
    fetched = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert fetched["id"] == sheet_id

    assert (
        cli.run(
            [
                "dcim",
                "field-sheet-list",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--site",
                "PAR1",
            ]
        )
        == 0
    )
    listed = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert [item["id"] for item in listed["items"]] == [sheet_id]


def test_dcim_field_operation_cli_full_workflow(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state-full.json"
    token = "d" * 40
    application = ApplicationFactory().create_json_application(state)
    application.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "field-admin", ("admin",), token)
    )
    application.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="CLI-SRV-FULL",
            equipment_name="Serveur CLI terrain complet",
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
    cli = OpenInfraCLI()

    def run_json(arguments: list[str]) -> dict[str, object]:
        assert cli.run(arguments) == 0
        return json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]

    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]
    generated = run_json(
        [
            "dcim",
            "field-sheet-generate",
            *common,
            "--target-type",
            "equipment",
            "--target-id",
            "CLI-SRV-FULL",
            "--title",
            "Intervention CLI complète",
            "--purpose",
            "Valider toutes les commandes du parcours terrain depuis la CLI.",
            "--owner",
            "ops.owner",
            "--operator",
            "field.operator",
        ]
    )
    sheet_id = str(generated["id"])

    qr_file = tmp_path / "field-qr.txt"
    qr_file.write_text(str(generated["qr_payload"]), encoding="utf-8")
    verified = run_json(
        [
            "dcim",
            "field-qr-verify",
            *common,
            "--sheet-id",
            sheet_id,
            "--payload-file",
            str(qr_file),
        ]
    )
    assert verified["verified"] is True

    lock = run_json(
        [
            "dcim",
            "field-lock-acquire",
            *common,
            "--sheet-id",
            sheet_id,
            "--idempotency-key",
            "cli-field-lock-full-0001",
            "--ttl-seconds",
            "3600",
        ]
    )
    assert lock["active"] is True

    started = run_json(["dcim", "field-start", *common, "--sheet-id", sheet_id])
    assert started["status"] == "in-progress"
    for checklist_item in started["checklist"]:  # type: ignore[union-attr]
        checked = run_json(
            [
                "dcim",
                "field-checklist-record",
                *common,
                "--sheet-id",
                sheet_id,
                "--item-id",
                str(checklist_item["id"]),
                "--result",
                "passed",
                "--operator-note",
                "Contrôle CLI validé",
            ]
        )
        assert checked["id"] == sheet_id

    evidence_ids: list[str] = []
    for phase in ("before", "after"):
        evidence_file = tmp_path / f"{phase}.png"
        evidence_file.write_bytes(f"cli-evidence-{phase}".encode())
        attached = run_json(
            [
                "dcim",
                "field-evidence-attach",
                *common,
                "--sheet-id",
                sheet_id,
                "--phase",
                phase,
                "--media-type",
                "image/png",
                "--file",
                str(evidence_file),
                "--caption",
                f"Photo {phase}",
            ]
        )
        evidence_id = str(attached["id"])
        evidence_ids.append(evidence_id)
        validated = run_json(
            [
                "dcim",
                "field-evidence-validate",
                *common,
                "--evidence-id",
                evidence_id,
            ]
        )
        assert validated["status"] == "validated"

    evidence_page = run_json(["dcim", "field-evidence-list", *common, "--sheet-id", sheet_id])
    assert {item["id"] for item in evidence_page["items"]} == set(evidence_ids)  # type: ignore[union-attr]

    package = run_json(
        [
            "dcim",
            "field-offline-create",
            *common,
            "--sheet-id",
            sheet_id,
            "--idempotency-key",
            "cli-offline-full-0001",
            "--ttl-seconds",
            "86400",
        ]
    )
    package_id = str(package["id"])
    package_sha256 = str(package["payload_sha256"])
    assert package["payload"]

    packages = run_json(
        [
            "dcim",
            "field-offline-list",
            *common,
            "--sheet-id",
            sheet_id,
            "--limit",
            "10",
        ]
    )
    assert [item["id"] for item in packages["items"]] == [package_id]  # type: ignore[union-attr]

    package_without_payload = run_json(
        [
            "dcim",
            "field-offline-get",
            *common,
            "--package-id",
            package_id,
            "--no-include-payload",
        ]
    )
    assert "payload" not in package_without_payload

    synchronized = run_json(
        [
            "dcim",
            "field-offline-sync",
            *common,
            "--package-id",
            package_id,
            "--payload-sha256",
            package_sha256,
        ]
    )
    assert synchronized["status"] == "synchronized"

    completed = run_json(["dcim", "field-complete", *common, "--sheet-id", sheet_id])
    assert completed["status"] == "completed"

    generated_cancel = run_json(
        [
            "dcim",
            "field-sheet-generate",
            *common,
            "--target-type",
            "equipment",
            "--target-id",
            "CLI-SRV-FULL",
            "--title",
            "Intervention CLI annulée",
            "--purpose",
            "Valider la commande d'annulation et la libération explicite.",
            "--owner",
            "ops.owner",
            "--operator",
            "field.operator",
        ]
    )
    cancel_sheet_id = str(generated_cancel["id"])
    cancel_lock = run_json(
        [
            "dcim",
            "field-lock-acquire",
            *common,
            "--sheet-id",
            cancel_sheet_id,
            "--idempotency-key",
            "cli-field-cancel-lock-0001",
        ]
    )
    released = run_json(
        [
            "dcim",
            "field-lock-release",
            *common,
            "--lock-id",
            str(cancel_lock["id"]),
        ]
    )
    assert released["active"] is False
    cancelled = run_json(["dcim", "field-cancel", *common, "--sheet-id", cancel_sheet_id])
    assert cancelled["status"] == "cancelled"
