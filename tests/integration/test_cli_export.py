from __future__ import annotations

import json
import zipfile
from pathlib import Path

from openinfra.interfaces.cli import OpenInfraCLI


def _bootstrap(data: Path, token: str) -> None:
    assert (
        OpenInfraCLI().run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--subject",
                "export-cli",
                "--role",
                "itrm:operator",
                "--token",
                token,
            ]
        )
        == 0
    )


def _upsert(data: Path, token: str, key: str) -> None:
    assert (
        OpenInfraCLI().run(
            [
                "itrm",
                "upsert-object",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--key",
                key,
                "--kind",
                "device",
                "--display-name",
                "CLI Export",
                "--attributes-json",
                '{"serial":"CLI"}',
                "--tag",
                "prod",
                "--source",
                "cli_export",
            ]
        )
        == 0
    )


def test_cli_export_request_run_report_and_artifact(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "f" * 40
    output = tmp_path / "export.json"
    _bootstrap(data, token)
    capsys.readouterr()
    _upsert(data, token, "device/cli-export-1")
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "export",
                "request",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--format",
                "json",
                "--kind",
                "device",
                "--tag",
                "prod",
            ]
        )
        == 0
    )
    queued = json.loads(capsys.readouterr().out)
    assert queued["status"] == "queued"

    assert (
        OpenInfraCLI().run(
            [
                "export",
                "run",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--job-id",
                queued["job_id"],
            ]
        )
        == 0
    )
    completed = json.loads(capsys.readouterr().out)
    assert completed["status"] == "completed"
    assert completed["artifact"]["signature_algorithm"] == "hmac-sha256"

    assert (
        OpenInfraCLI().run(
            [
                "export",
                "report",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--job-id",
                queued["job_id"],
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["total_rows"] == 1

    assert (
        OpenInfraCLI().run(
            [
                "export",
                "artifact",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--job-id",
                queued["job_id"],
                "--output",
                str(output),
            ]
        )
        == 0
    )
    artifact_result = json.loads(capsys.readouterr().out)
    assert artifact_result["content_size_bytes"] == output.stat().st_size
    assert json.loads(output.read_text(encoding="utf-8"))[0]["key"] == "device/cli-export-1"


def test_cli_export_xlsx_artifact(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state-xlsx.json"
    token = "g" * 40
    output = tmp_path / "export.xlsx"
    _bootstrap(data, token)
    capsys.readouterr()
    _upsert(data, token, "device/cli-export-xlsx")
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "export",
                "request",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--format",
                "xlsx",
            ]
        )
        == 0
    )
    queued = json.loads(capsys.readouterr().out)
    assert (
        OpenInfraCLI().run(
            [
                "export",
                "run",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--job-id",
                queued["job_id"],
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        OpenInfraCLI().run(
            [
                "export",
                "artifact",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--job-id",
                queued["job_id"],
                "--output",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()
    with zipfile.ZipFile(output) as workbook:
        assert "xl/workbook.xml" in workbook.namelist()
