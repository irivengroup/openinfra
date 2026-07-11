from __future__ import annotations

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
    GetRagJobCommand,
    ListRagAnswersCommand,
    ListRagDocumentsCommand,
    ListRagJobsCommand,
    RagService,
    RunRagJobCommand,
    SyncRsotRagCommand,
    UpsertRagDocumentCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import NotFoundError, TenantId, ValidationError
from openinfra.domain.rag import RagTransferJob


def _app(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "e" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "rag-edge-admin", ("admin",), token)
    )
    return app, token


def test_rag_sync_rsot_idempotency_updates_and_deactivates_missing(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    stale = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            token,
            "rsot",
            "device/stale",
            "Stale device",
            "Objet RSOT obsolète conservé uniquement pour tester la désactivation.",
            ("rsot.read",),
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/srv-rag-001",
            kind="device",
            display_name="RAG server",
            attributes_json='{"site":"PAR1"}',
            tags=("production",),
            source="manual",
        )
    )

    result = app.rag_service.sync_rsot(SyncRsotRagCommand("default", token, "pytest", 10, True))
    assert result.imported == 1
    assert result.deactivated == 1
    assert (
        app.rag_repository.get_document(TenantId.from_value("default"), stale.id.value).active
        is False
    )

    unchanged = app.rag_service.sync_rsot(SyncRsotRagCommand("default", token, "pytest", 10, True))
    assert unchanged.unchanged == 1
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/srv-rag-001",
            kind="device",
            display_name="RAG server updated",
            attributes_json='{"site":"PAR2"}',
            tags=("production", "critical"),
            source="manual",
        )
    )
    updated = app.rag_service.sync_rsot(SyncRsotRagCommand("default", token, max_objects=10))
    assert updated.updated == 1

    with pytest.raises(ValidationError, match="max_objects"):
        app.rag_service.sync_rsot(SyncRsotRagCommand("default", token, max_objects=0))


def test_rag_service_missing_resources_filters_and_query_guards(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    document = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            token,
            "documentation",
            "same-document",
            "Same document",
            "Contenu identique pour vérifier une indexation idempotente.",
        )
    )
    same = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            token,
            "documentation",
            "same-document",
            "Same document",
            "Contenu identique pour vérifier une indexation idempotente.",
        )
    )
    assert same.id == document.id
    assert app.rag_service.list_documents(
        ListRagDocumentsCommand("default", token, source_type="documentation", active=True)
    ).items
    assert app.rag_service.list_answers(ListRagAnswersCommand("default", token)).items == ()
    assert app.rag_service.list_jobs(ListRagJobsCommand("default", token)).items == ()

    for operation in (
        lambda: app.rag_service.get_document(GetRagDocumentCommand("default", token, "0" * 32)),
        lambda: app.rag_service.deactivate_document(
            DeactivateRagDocumentCommand("default", token, "0" * 32)
        ),
        lambda: app.rag_service.get_answer(GetRagAnswerCommand("default", token, "0" * 32)),
        lambda: app.rag_service.get_job(GetRagJobCommand("default", token, "0" * 32)),
        lambda: app.rag_service.run_job(RunRagJobCommand("default", token, "0" * 32)),
        lambda: app.rag_service.get_artifact(GetRagArtifactCommand("default", token, "0" * 32)),
    ):
        with pytest.raises(NotFoundError):
            operation()

    with pytest.raises(ValidationError, match="searchable term"):
        app.rag_service.ask(AskRagCommand("default", token, "the and with"))
    with pytest.raises(ValidationError, match="citation limit"):
        app.rag_service.ask(AskRagCommand("default", token, "Question valide", limit=0))


def test_rag_jobs_failure_resume_exports_and_artifact_guards(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            token,
            "documentation",
            "export-source",
            "Export source",
            "OpenInfra exporte des réponses RAG avec leurs citations.",
        )
    )
    answer = app.rag_service.ask(AskRagCommand("default", token, "Que fait OpenInfra ?"))

    export = app.rag_service.create_job(
        CreateRagJobCommand("default", token, "answer-export", "all-answers", {"format": "json"})
    )
    with pytest.raises(ValidationError, match="not available"):
        app.rag_service.get_artifact(GetRagArtifactCommand("default", token, export.id.value))
    completed = app.rag_service.run_job(RunRagJobCommand("default", token, export.id.value))
    assert completed.status.value == "completed"
    assert (
        app.rag_service.run_job(RunRagJobCommand("default", token, export.id.value)).id
        == completed.id
    )
    assert (
        answer.id.value.encode()
        in app.rag_service.get_artifact(
            GetRagArtifactCommand("default", token, export.id.value)
        ).content
    )
    assert (
        app.rag_service.get_job(GetRagJobCommand("default", token, export.id.value)).status.value
        == "completed"
    )
    assert app.rag_service.list_jobs(ListRagJobsCommand("default", token)).items

    missing_answer = app.rag_service.create_job(
        CreateRagJobCommand(
            "default",
            token,
            "answer-export",
            "missing-answer",
            {"format": "json", "answer_ids": ["0" * 32]},
        )
    )
    with pytest.raises(NotFoundError, match="answer not found"):
        app.rag_service.run_job(RunRagJobCommand("default", token, missing_answer.id.value))
    assert (
        app.rag_service.get_job(
            GetRagJobCommand("default", token, missing_answer.id.value)
        ).status.value
        == "failed"
    )

    invalid_metadata = app.rag_service.create_job(
        CreateRagJobCommand(
            "default",
            token,
            "document-import",
            "invalid-metadata",
            {
                "documents": [
                    {
                        "source_ref": "invalid",
                        "title": "Invalid",
                        "content": "Invalid metadata import",
                        "metadata": [],
                    }
                ]
            },
        )
    )
    with pytest.raises(ValidationError, match="JSON object"):
        app.rag_service.run_job(RunRagJobCommand("default", token, invalid_metadata.id.value))

    malformed = RagTransferJob.create(
        TenantId.from_value("default"),
        "document-import",
        "malformed-array",
        {"documents": "not-an-array"},
        1,
    )
    app.rag_repository.save_job(malformed)
    with pytest.raises(ValidationError, match="documents array"):
        app.rag_service.run_job(RunRagJobCommand("default", token, malformed.id.value))

    malformed_item = RagTransferJob.create(
        TenantId.from_value("default"),
        "document-import",
        "malformed-item",
        {"documents": ["not-an-object"]},
        1,
    )
    app.rag_repository.save_job(malformed_item)
    with pytest.raises(ValidationError, match="JSON object"):
        app.rag_service.run_job(RunRagJobCommand("default", token, malformed_item.id.value))

    malformed_ids = RagTransferJob.create(
        TenantId.from_value("default"),
        "answer-export",
        "malformed-ids",
        {"format": "json", "answer_ids": "not-an-array"},
        1,
    )
    app.rag_repository.save_job(malformed_ids)
    with pytest.raises(ValidationError, match="answer_ids"):
        app.rag_service.run_job(RunRagJobCommand("default", token, malformed_ids.id.value))

    completed_without_artifact = (
        RagTransferJob.create(
            TenantId.from_value("default"),
            "answer-export",
            "artifact-missing",
            {"format": "json", "answer_ids": []},
            1,
        )
        .start()
        .advance(1)
    )
    app.rag_repository.save_job(completed_without_artifact)
    with pytest.raises(NotFoundError, match="artifact not found"):
        app.rag_service.get_artifact(
            GetRagArtifactCommand("default", token, completed_without_artifact.id.value)
        )

    for payload, message in (
        ({}, "1 to 10000"),
        ({"documents": ["invalid"]}, "JSON objects"),
    ):
        with pytest.raises(ValidationError, match=message):
            app.rag_service.create_job(
                CreateRagJobCommand("default", token, "document-import", f"bad-{message}", payload)
            )
    with pytest.raises(ValidationError, match="array of at most"):
        app.rag_service.create_job(
            CreateRagJobCommand(
                "default", token, "answer-export", "bad-answer-ids", {"answer_ids": "bad"}
            )
        )
    with pytest.raises(ValidationError, match="json or csv"):
        RagService._render_answers([], "xml", "job")
    with pytest.raises(ValidationError, match="JSON object"):
        RagService._mapping([], "mapping")


def test_json_rag_repository_rejects_corruption_and_bad_cursors(tmp_path: Path) -> None:
    from openinfra.domain.common import Pagination
    from openinfra.domain.rag import RagArtifact

    app, token = _app(tmp_path)
    document = app.rag_service.upsert_document(
        UpsertRagDocumentCommand(
            "default",
            token,
            "documentation",
            "repository-edge",
            "Repository edge",
            "Document de test pour les branches du dépôt JSON RAG.",
        )
    )
    app.rag_service.deactivate_document(
        DeactivateRagDocumentCommand("default", token, document.id.value)
    )
    search = app.rag_repository.search(
        TenantId.from_value("default"), "Document test", frozenset({"rag.read"}), 5
    )
    assert search.candidates == ()

    for cursor, message in (("invalid", "numeric offset"), ("-1", "positive")):
        with pytest.raises(ValidationError, match=message):
            app.rag_repository.list_documents(
                TenantId.from_value("default"), Pagination.from_values(10, cursor)
            )

    tenant_id = TenantId.from_value("default")
    job_id = "f" * 32
    artifact = RagArtifact.create("artifact.json", "application/json", b"{}")
    app.rag_repository.save_artifact(tenant_id, job_id, artifact)
    key = f"default:{job_id}"
    app.store.data["rag_artifacts"][key]["content"] = "%%%"
    with pytest.raises(ValidationError, match="stored RAG artifact is invalid"):
        app.rag_repository.get_artifact(tenant_id, job_id)

    app.rag_repository.save_artifact(tenant_id, job_id, artifact)
    app.store.data["rag_artifacts"][key]["sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="checksum"):
        app.rag_repository.get_artifact(tenant_id, job_id)
