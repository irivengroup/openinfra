from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI


def test_greenops_cli_complete_cycle(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "g" * 40
    app = ApplicationFactory().create_json_application(state)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "greenops-admin", ("admin",), token)
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "greenops",
                "source-create",
                *common,
                "--actor",
                "pytest",
                "--code",
                "meter-01",
                "--name",
                "Meter 01",
                "--source-type",
                "dcim",
                "--owner",
                "facilities",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["code"] == "meter-01"  # type: ignore[attr-defined]
    assert cli.run(["greenops", "sources", *common, "--active-only"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "greenops",
                "factor-create",
                *common,
                "--actor",
                "pytest",
                "--code",
                "fr-2026",
                "--region",
                "fr",
                "--grams-co2e-per-kwh",
                "50",
                "--source-name",
                "RTE",
                "--source-uri",
                "https://example.invalid/rte",
                "--period-start",
                "2026-01-01",
                "--period-end",
                "2026-12-31",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["source_name"] == "RTE"  # type: ignore[attr-defined]
    assert cli.run(["greenops", "factors", *common, "--code", "fr-2026"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "greenops",
                "policy-upsert",
                *common,
                "--actor",
                "pytest",
                "--site-code",
                "par-01",
                "--default-pue",
                "1.4",
                "--energy-cost-per-kwh",
                "0.20",
                "--currency",
                "EUR",
                "--carbon-factor-code",
                "fr-2026",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["currency"] == "EUR"  # type: ignore[attr-defined]
    assert cli.run(["greenops", "policy-get", *common, "--site-code", "par-01"]) == 0
    assert json.loads(capsys.readouterr().out)["site_code"] == "par-01"  # type: ignore[attr-defined]

    for index, energy in enumerate(("100", "110", "250"), start=1):
        assert (
            cli.run(
                [
                    "greenops",
                    "measurement-ingest",
                    *common,
                    "--actor",
                    "pytest",
                    "--idempotency-key",
                    f"greenops-cli-000{index}",
                    "--source-code",
                    "meter-01",
                    "--kind",
                    "observed",
                    "--scope",
                    "site",
                    "--scope-key",
                    "par-01",
                    "--site-code",
                    "par-01",
                    "--period-start",
                    f"2026-07-0{index}T00:00:00+00:00",
                    "--period-end",
                    f"2026-07-0{index + 1}T00:00:00+00:00",
                    "--energy-kwh",
                    energy,
                    "--energy-capacity-percent",
                    str(35 + index * 20),
                ]
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["source_code"] == "meter-01"  # type: ignore[attr-defined]

    assert cli.run(["greenops", "measurements", *common, "--site-code", "par-01"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 3  # type: ignore[attr-defined]
    assert (
        cli.run(
            [
                "greenops",
                "report-generate",
                *common,
                "--actor",
                "pytest",
                "--site-code",
                "par-01",
                "--period-start",
                "2026-07-01",
                "--period-end",
                "2026-07-03",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    report_id = str(report["id"])
    assert report["production_mutation"] is False

    assert cli.run(["greenops", "report", *common, "--report-id", report_id]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == report_id  # type: ignore[attr-defined]
    assert cli.run(["greenops", "reports", *common, "--site-code", "par-01"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == report_id  # type: ignore[attr-defined]

    output = tmp_path / "greenops-report.csv"
    assert (
        cli.run(
            [
                "greenops",
                "report-export",
                *common,
                "--report-id",
                report_id,
                "--format",
                "csv",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert "kilograms_co2e" in output.read_text(encoding="utf-8")
    capsys.readouterr()  # type: ignore[attr-defined]

    for command in ("anomalies", "forecasts", "candidates", "scores"):
        assert cli.run(["greenops", command, *common, "--site-code", "par-01"]) == 0
        assert isinstance(json.loads(capsys.readouterr().out)["items"], list)  # type: ignore[attr-defined]
