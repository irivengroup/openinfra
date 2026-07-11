from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ValidationError
from openinfra.interfaces.cli import OpenInfraCLI


def _record(external_id: str, month: str = "06") -> dict[str, object]:
    return {
        "external_id": external_id,
        "category": "cloud",
        "source": "azure-cost",
        "period_start": f"2026-{month}-01",
        "period_end": f"2026-{month}-30" if month == "06" else f"2026-{month}-31",
        "currency": "EUR",
        "amount": "240.00",
        "owner": "platform.team",
        "application_key": "openinfra",
        "service_key": "asset-management",
        "cost_center": "cc-200",
        "environment": "production",
        "metadata": {"provider": "azure", "subscription": "sub-001"},
    }


def test_finops_cli_complete_cycle(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "c" * 40
    app = ApplicationFactory().create_json_application(state)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "finops-admin", ("admin",), token)
    )
    records_file = tmp_path / "costs.json"
    records_file.write_text(json.dumps([_record("azure-2026-06-001")]), encoding="utf-8")
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "finops",
                "rule-create",
                *common,
                "--actor",
                "pytest",
                "--name",
                "Application allocation",
                "--priority",
                "10",
                "--dimension",
                "application",
                "--selector-key",
                "application_key",
                "--percentage",
                "100",
                "--category",
                "cloud",
                "--source",
                "azure-cost",
            ]
        )
        == 0
    )
    rule = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert rule["active"] is True

    assert cli.run(["finops", "rules", *common, "--active-only"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "finops",
                "import-submit",
                *common,
                "--actor",
                "pytest",
                "--idempotency-key",
                "finops-cli-import-0001",
                "--source",
                "azure-cost",
                "--records-file",
                str(records_file),
            ]
        )
        == 0
    )
    queued = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    job_id = str(queued["id"])

    assert cli.run(["finops", "import-get", *common, "--job-id", job_id, "--include-records"]) == 0
    assert len(json.loads(capsys.readouterr().out)["records"]) == 1  # type: ignore[attr-defined]

    assert cli.run(["finops", "import-run", *common, "--job-id", job_id]) == 0
    completed = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert completed["status"] == "completed"

    assert cli.run(["finops", "imports", *common, "--status", "completed"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == job_id  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "finops",
                "costs",
                *common,
                "--period-start",
                "2026-06-01",
                "--period-end",
                "2026-06-30",
                "--currency",
                "EUR",
                "--category",
                "cloud",
                "--source",
                "azure-cost",
                "--quality-status",
                "allocated",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["items"][0]["amount"] == "240.000000"  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "finops",
                "budget-upsert",
                *common,
                "--actor",
                "pytest",
                "--dimension",
                "application",
                "--target",
                "openinfra",
                "--period-start",
                "2026-06-01",
                "--period-end",
                "2026-06-30",
                "--currency",
                "EUR",
                "--amount",
                "200",
                "--warning-threshold-percent",
                "80",
                "--owner",
                "finops.team",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["version"] == 1  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "finops",
                "budgets",
                *common,
                "--dimension",
                "application",
                "--target",
                "openinfra",
                "--currency",
                "EUR",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["items"][0]["target"] == "openinfra"  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "finops",
                "report-generate",
                *common,
                "--actor",
                "pytest",
                "--kind",
                "chargeback",
                "--period-start",
                "2026-06-01",
                "--period-end",
                "2026-06-30",
                "--group-by",
                "application",
                "--currency",
                "EUR",
                "--chargeback-markup-percent",
                "10",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    report_id = str(report["id"])
    assert report["production_billing_mutation"] is False
    assert report["total_amount"] == "264.000000"

    assert cli.run(["finops", "report", *common, "--report-id", report_id]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == report_id  # type: ignore[attr-defined]

    assert cli.run(["finops", "reports", *common, "--kind", "chargeback"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == report_id  # type: ignore[attr-defined]

    json_output = tmp_path / "report.json"
    csv_output = tmp_path / "report.csv"
    assert (
        cli.run(
            [
                "finops",
                "report-export",
                *common,
                "--report-id",
                report_id,
                "--format",
                "json",
                "--output",
                str(json_output),
            ]
        )
        == 0
    )
    assert json.loads(json_output.read_text(encoding="utf-8"))["id"] == report_id
    assert (
        cli.run(
            [
                "finops",
                "report-export",
                *common,
                "--report-id",
                report_id,
                "--format",
                "csv",
                "--output",
                str(csv_output),
            ]
        )
        == 0
    )
    assert "target,amount" in csv_output.read_text(encoding="utf-8")

    assert cli.run(["finops", "anomalies", *common]) == 0
    assert isinstance(json.loads(capsys.readouterr().out)["items"], list)  # type: ignore[attr-defined]
    assert cli.run(["finops", "forecasts", *common, "--dimension", "application"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["target"] == "openinfra"  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "finops",
                "period-close",
                *common,
                "--actor",
                "pytest",
                "--period-start",
                "2026-06-01",
                "--period-end",
                "2026-06-30",
                "--currency",
                "EUR",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "closed"  # type: ignore[attr-defined]
    assert cli.run(["finops", "periods", *common, "--status", "closed"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["status"] == "closed"  # type: ignore[attr-defined]

    records_file.write_text(json.dumps([_record("azure-2026-07-001", "07")]), encoding="utf-8")
    assert (
        cli.run(
            [
                "finops",
                "import-submit",
                *common,
                "--idempotency-key",
                "finops-cli-import-0002",
                "--source",
                "azure-cost",
                "--records-file",
                str(records_file),
            ]
        )
        == 0
    )
    cancel_job_id = str(json.loads(capsys.readouterr().out)["id"])  # type: ignore[attr-defined]
    assert cli.run(["finops", "import-cancel", *common, "--job-id", cancel_job_id]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "cancelled"  # type: ignore[attr-defined]


def test_finops_cli_rejects_invalid_record_files(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="cannot read FinOps records file"):
        OpenInfraCLI._read_finops_records(tmp_path / "missing.json")

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[", encoding="utf-8")
    with pytest.raises(ValidationError, match="invalid JSON"):
        OpenInfraCLI._read_finops_records(malformed)

    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(ValidationError, match="non-empty JSON array"):
        OpenInfraCLI._read_finops_records(empty)

    invalid = tmp_path / "invalid.json"
    invalid.write_text('["invalid"]', encoding="utf-8")
    with pytest.raises(ValidationError, match="each FinOps record"):
        OpenInfraCLI._read_finops_records(invalid)
