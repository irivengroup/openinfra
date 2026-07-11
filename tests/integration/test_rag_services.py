from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.rag_services import (
    AskRagCommand,
    CreateRagJobCommand,
    DeactivateRagDocumentCommand,
    GetRagAnswerCommand,
    GetRagArtifactCommand,
    GetRagDocumentCommand,
    ListRagDocumentsCommand,
    RunRagJobCommand,
    UpsertRagDocumentCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError, NotFoundError, ValidationError


def _app(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    admin = "a" * 40
    viewer = "v" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "rag-admin", ("admin",), admin)
    )
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "rag-viewer", ("viewer",), viewer)
    )
    return app, admin, viewer


def test_rag_permission_filter_citations_audit_versioning_and_deactivation(tmp_path: Path) -> None:
    app, admin, viewer = _app(tmp_path)
    public = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            admin,
            "runbook",
            "postgresql-ha",
            "PostgreSQL haute disponibilité",
            "OpenInfra utilise PostgreSQL avec réplication et bascule contrôlée.",
            ("rag.read",),
            ("database",),
            {"owner": "platform"},
        )
    )
    restricted = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            admin,
            "policy",
            "audit-secret",
            "Politique audit restreinte",
            "Le mot clé ultrasecret ne doit jamais être révélé aux viewers.",
            ("audit.read",),
        )
    )
    assert (
        app.rag_service.get_document(
            GetRagDocumentCommand("default", admin, restricted.id.value)
        ).id
        == restricted.id
    )
    with pytest.raises(NotFoundError):
        app.rag_service.get_document(GetRagDocumentCommand("default", viewer, restricted.id.value))

    visible = app.rag_service.list_documents(ListRagDocumentsCommand("default", viewer))
    assert [item.id for item in visible.items] == [public.id]
    answer = app.rag_service.ask(
        AskRagCommand("default", viewer, "Quelle base de données utilise OpenInfra ?")
    )
    assert answer.status.value == "answered"
    assert answer.citations and answer.citations[0].document_id == public.id.value
    assert "PostgreSQL" in answer.answer
    hidden = app.rag_service.ask(
        AskRagCommand("default", viewer, "Quel document contient ultrasecret ?")
    )
    assert hidden.status.value == "insufficient-context"
    assert hidden.citations == ()
    assert (
        app.rag_service.get_answer(
            GetRagAnswerCommand("default", viewer, answer.id.value)
        ).question_hash
        == answer.question_hash
    )

    revised = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            admin,
            "runbook",
            "postgresql-ha",
            "PostgreSQL haute disponibilité",
            "OpenInfra utilise PostgreSQL avec réplication synchrone et bascule contrôlée.",
            ("rag.read",),
            ("database",),
            {"owner": "platform"},
        )
    )
    assert revised.version == 2 and revised.id != public.id
    assert (
        app.rag_service.deactivate_document(
            DeactivateRagDocumentCommand("default", admin, revised.id.value)
        ).active
        is False
    )

    audit_payload = json.dumps(app.store.data["audit_events"], sort_keys=True)
    assert answer.question not in audit_payload
    assert answer.question_hash in audit_payload


def test_rag_resumable_jobs_idempotency_exports_and_error_paths(tmp_path: Path) -> None:
    app, admin, _viewer = _app(tmp_path)
    import_payload = {
        "documents": [
            {
                "source_type": "documentation",
                "source_ref": "doc-1",
                "title": "Documentation 1",
                "content": "Documentation OpenInfra sur le réseau et les VLAN.",
                "required_permissions": ["rag.read"],
            },
            {
                "source_type": "documentation",
                "source_ref": "doc-2",
                "title": "Documentation 2",
                "content": "Documentation OpenInfra sur les racks et les sites.",
                "required_permissions": ["rag.read"],
            },
        ]
    }
    command = CreateRagJobCommand(
        "default", admin, "document-import", "import-batch-001", import_payload, 1
    )
    job = app.rag_service.create_job(command)
    assert app.rag_service.create_job(command).id == job.id
    first = app.rag_service.run_job(RunRagJobCommand("default", admin, job.id.value))
    assert first.status.value == "queued" and first.processed_count == 1
    completed = app.rag_service.run_job(RunRagJobCommand("default", admin, job.id.value))
    assert completed.status.value == "completed"

    answer = app.rag_service.ask(
        AskRagCommand("default", admin, "Quels documents parlent réseau ?")
    )
    export = app.rag_service.create_job(
        CreateRagJobCommand(
            "default",
            admin,
            "answer-export",
            "export-answers-001",
            {"format": "json", "answer_ids": [answer.id.value]},
        )
    )
    exported = app.rag_service.run_job(RunRagJobCommand("default", admin, export.id.value))
    assert exported.status.value == "completed"
    artifact = app.rag_service.get_artifact(
        GetRagArtifactCommand("default", admin, exported.id.value)
    )
    assert artifact.content_type == "application/json"
    assert answer.id.value.encode() in artifact.content

    with pytest.raises(ConflictError):
        app.rag_service.create_job(
            CreateRagJobCommand(
                "default",
                admin,
                "answer-export",
                "export-answers-001",
                {"format": "csv", "answer_ids": []},
            )
        )
    with pytest.raises(ValidationError, match="json or csv"):
        app.rag_service.create_job(
            CreateRagJobCommand("default", admin, "answer-export", "bad-export", {"format": "xlsx"})
        )
