from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import ValidationError
from openinfra.interfaces.cli import OpenInfraCLI


def test_simulation_cli_create_run_list_and_report(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "s" * 40
    application = ApplicationFactory().create_json_application(state)
    application.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "simulation-admin", ("admin",), token)
    )
    application.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            "default",
            "pytest",
            token,
            "server:cli-001",
            "server",
            "Serveur CLI 001",
            json.dumps({"site": "par1", "rack": "r01", "power_watts": 500}),
            ("production",),
            "pytest",
        )
    )
    changes_file = tmp_path / "changes.json"
    changes_file.write_text(
        json.dumps(
            [
                {
                    "kind": "equipment-move",
                    "target_key": "server:cli-001",
                    "before": {"site": "par1"},
                    "after": {"site": "par2", "rack": "r20", "power_watts": 400},
                    "assumptions": ["La capacité du rack cible est réservée"],
                }
            ]
        ),
        encoding="utf-8",
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "simulation",
                "create",
                *common,
                "--name",
                "Migration CLI",
                "--description",
                "Simulation complète depuis la ligne de commande OpenInfra.",
                "--owner",
                "architecture.team",
                "--idempotency-key",
                "simulation-cli-0001",
                "--changes-file",
                str(changes_file),
                "--site",
                "par1",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    scenario_id = str(created["id"])

    assert cli.run(["simulation", "run", *common, "--scenario-id", scenario_id]) == 0
    report = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    report_id = str(report["id"])
    assert report["production_mutation"] is False
    assert report["execution_order"] is False

    assert cli.run(["simulation", "get", *common, "--scenario-id", scenario_id]) == 0
    fetched = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert fetched["status"] == "completed"

    assert cli.run(["simulation", "list", *common, "--status", "completed"]) == 0
    listed = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert [item["id"] for item in listed["items"]] == [scenario_id]

    assert cli.run(["simulation", "report", *common, "--report-id", report_id]) == 0
    fetched_report = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert fetched_report["id"] == report_id

    assert cli.run(["simulation", "reports", *common, "--scenario-id", scenario_id]) == 0
    reports = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert [item["id"] for item in reports["items"]] == [report_id]

    outage_file = tmp_path / "outage.json"
    outage_file.write_text(
        json.dumps([{"kind": "equipment-outage", "target_key": "server:cli-001"}]),
        encoding="utf-8",
    )
    assert (
        cli.run(
            [
                "simulation",
                "create",
                *common,
                "--name",
                "Coupure CLI",
                "--description",
                "Simulation de coupure pour comparer deux rapports CLI.",
                "--owner",
                "architecture.team",
                "--idempotency-key",
                "simulation-cli-0002",
                "--changes-file",
                str(outage_file),
            ]
        )
        == 0
    )
    outage_scenario_id = str(json.loads(capsys.readouterr().out)["id"])  # type: ignore[attr-defined]
    assert cli.run(["simulation", "run", *common, "--scenario-id", outage_scenario_id]) == 0
    outage_report_id = str(json.loads(capsys.readouterr().out)["id"])  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "simulation",
                "compare",
                *common,
                "--left-report-id",
                report_id,
                "--right-report-id",
                outage_report_id,
            ]
        )
        == 0
    )
    comparison = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert comparison["left_report_id"] == report_id
    assert cli.run(["simulation", "comparisons", *common]) == 0
    comparisons = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert comparisons["items"][0]["id"] == comparison["id"]

    assert (
        cli.run(
            [
                "simulation",
                "create",
                *common,
                "--name",
                "Annulation CLI",
                "--description",
                "Simulation brouillon destinée à valider l'annulation CLI.",
                "--owner",
                "architecture.team",
                "--idempotency-key",
                "simulation-cli-0003",
                "--changes-file",
                str(outage_file),
            ]
        )
        == 0
    )
    cancelled_id = str(json.loads(capsys.readouterr().out)["id"])  # type: ignore[attr-defined]
    assert cli.run(["simulation", "cancel", *common, "--scenario-id", cancelled_id]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "cancelled"  # type: ignore[attr-defined]


def test_simulation_cli_rejects_invalid_changes_file(tmp_path: Path, capsys: object) -> None:
    changes_file = tmp_path / "changes.json"
    changes_file.write_text('{"kind":"equipment-outage"}', encoding="utf-8")
    result = OpenInfraCLI().run(
        [
            "simulation",
            "create",
            "--data",
            str(tmp_path / "state.json"),
            "--tenant",
            "default",
            "--admin-token",
            "x" * 40,
            "--name",
            "Invalid",
            "--description",
            "Ce scénario doit être refusé avant sa création.",
            "--owner",
            "architecture.team",
            "--idempotency-key",
            "simulation-cli-invalid-0001",
            "--changes-file",
            str(changes_file),
        ]
    )
    assert result == 2
    assert "non-empty JSON array" in capsys.readouterr().err  # type: ignore[attr-defined]


def test_simulation_cli_rejects_unreadable_malformed_and_non_object_files(tmp_path: Path) -> None:
    cli = OpenInfraCLI()
    with pytest.raises(ValidationError, match="cannot read simulation changes file"):
        cli._read_simulation_changes(tmp_path / "missing.json")

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[", encoding="utf-8")
    with pytest.raises(ValidationError, match="invalid JSON"):
        cli._read_simulation_changes(malformed)

    non_object = tmp_path / "non-object.json"
    non_object.write_text('["invalid"]', encoding="utf-8")
    with pytest.raises(ValidationError, match="index 0"):
        cli._read_simulation_changes(non_object)
