from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI


def test_rag_cli_document_query_job_and_artifact(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "r" * 40
    app = ApplicationFactory().create_json_application(state, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "rag-admin", ("admin",), token)
    )
    document = tmp_path / "runbook.txt"
    document.write_text(
        "OpenInfra utilise PostgreSQL et des migrations versionnées.", encoding="utf-8"
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "rag",
                "document-upsert",
                *common,
                "--source-type",
                "runbook",
                "--source-ref",
                "postgresql",
                "--title",
                "Runbook PostgreSQL",
                "--file",
                str(document),
                "--required-permission",
                "rag.read",
            ]
        )
        == 0
    )
    indexed = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert indexed["source_ref"] == "postgresql"

    assert cli.run(["rag", "ask", *common, "--question", "Quelle base utilise OpenInfra ?"]) == 0
    answer = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert answer["citations"]

    payload = tmp_path / "job.json"
    payload.write_text(
        json.dumps({"format": "json", "answer_ids": [answer["id"]]}), encoding="utf-8"
    )
    assert (
        cli.run(
            [
                "rag",
                "job-create",
                *common,
                "--kind",
                "answer-export",
                "--idempotency-key",
                "cli-export-001",
                "--payload-file",
                str(payload),
            ]
        )
        == 0
    )
    job = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert cli.run(["rag", "job-run", *common, "--job-id", job["id"]]) == 0
    capsys.readouterr()  # type: ignore[attr-defined]
    output = tmp_path / "answers.json"
    assert (
        cli.run(["rag", "artifact", *common, "--job-id", job["id"], "--output", str(output)]) == 0
    )
    assert answer["id"] in output.read_text(encoding="utf-8")
