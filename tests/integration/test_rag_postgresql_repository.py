from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import DomainEvent, EntityId, Pagination, TenantId, ValidationError
from openinfra.domain.rag import (
    RagAnswer,
    RagAnswerStatus,
    RagArtifact,
    RagCitation,
    RagDocument,
    RagTransferJob,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLRagRepository,
    PostgreSQLSessionRegistry,
)


def _repository() -> PostgreSQLRagRepository:
    connection = FakeConnection()
    return PostgreSQLRagRepository(
        PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=lambda _dsn, _profile: connection,
            )
        )
    )


def _objects() -> dict[str, object]:
    tenant = TenantId.from_value("default")
    document = RagDocument.create(
        tenant,
        "runbook",
        "postgresql-ha",
        "PostgreSQL HA",
        "OpenInfra utilise PostgreSQL avec réplication contrôlée.",
        ("rag.read",),
        ("database",),
        {"owner": "platform"},
        "https://example.invalid/runbook",
    )
    citation = RagCitation.create(document, document.chunks[0], Decimal("4.0"))
    answer = RagAnswer.create(
        tenant,
        "Quelle base utilise OpenInfra ?",
        "OpenInfra utilise PostgreSQL [1].",
        RagAnswerStatus.ANSWERED,
        Decimal("0.8"),
        (citation,),
    )
    job = RagTransferJob.create(
        tenant,
        "answer-export",
        "pg-export-001",
        {"format": "json", "answer_ids": [answer.id.value]},
        1,
        100,
    )
    artifact = RagArtifact.create("answers.json", "application/json", b'{"answers":[]}')
    event = DomainEvent(
        EntityId.new(), tenant, document.id, "rag.document.indexed", {}, datetime.now(UTC)
    )
    return {
        "tenant": tenant,
        "document": document,
        "answer": answer,
        "job": job,
        "artifact": artifact,
        "event": event,
    }


def test_rag_postgresql_writes_are_parameterized_and_cover_outbox(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    values = _objects()
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    repo.save_document(values["document"])  # type: ignore[arg-type]
    repo.save_answer(values["answer"])  # type: ignore[arg-type]
    repo.save_job(values["job"])  # type: ignore[arg-type]
    repo.save_artifact(
        values["tenant"],
        values["job"].id.value,
        values["artifact"],  # type: ignore[union-attr,arg-type]
    )
    repo.append_event(values["event"])  # type: ignore[arg-type]
    joined = "\n".join(query for query, _params in statements)
    for table in (
        "rag_documents",
        "rag_chunks",
        "rag_answers",
        "rag_jobs",
        "rag_artifacts",
        "rag_event_outbox",
    ):
        assert table in joined
    assert all("%(tenant_id)s" in query for query, _params in statements)


def test_rag_postgresql_reads_search_pagination_artifact_and_guards(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    values = _objects()
    tenant = values["tenant"]
    document = values["document"]
    answer = values["answer"]
    job = values["job"]
    artifact = values["artifact"]
    assert isinstance(tenant, TenantId)
    assert isinstance(document, RagDocument)
    assert isinstance(answer, RagAnswer)
    assert isinstance(job, RagTransferJob)
    assert isinstance(artifact, RagArtifact)

    rows = iter(
        [
            {"payload": json.dumps(document.as_dict())},
            {"payload": json.dumps(document.as_dict())},
            {"payload": json.dumps(answer.as_dict())},
            {"payload": json.dumps(job.as_dict())},
            {"payload": json.dumps(job.as_dict())},
            {
                "filename": artifact.filename,
                "content_type": artifact.content_type,
                "content": memoryview(artifact.content),
                "sha256": artifact.sha256,
            },
            None,
        ]
    )
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))
    assert repo.get_document(tenant, document.id.value) == document
    assert repo.find_active_document(tenant, "runbook", "postgresql-ha") == document
    assert repo.get_answer(tenant, answer.id.value) == answer
    assert repo.get_job(tenant, job.id.value) == job
    assert repo.find_job_by_idempotency_key(tenant, job.idempotency_key) == job
    assert repo.get_artifact(tenant, job.id.value) == artifact
    assert repo.get_document(tenant, document.id.value) is None

    calls: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        calls.append((" ".join(query.split()), dict(params)))
        if "FROM rag_chunks c" in query:
            return [
                {
                    "document_payload": json.dumps(document.as_dict()),
                    "chunk_payload": json.dumps(document.chunks[0].as_dict()),
                    "rank": Decimal("0.75"),
                }
            ]
        return [
            {"payload": json.dumps(document.as_dict())},
            {"payload": json.dumps(document.as_dict())},
        ]

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: {"total": 2})
    page = repo.list_documents(tenant, Pagination(limit=1), "runbook", True)
    assert page.items == (document,) and page.next_cursor == "1"
    search = repo.search(tenant, "PostgreSQL OpenInfra", frozenset({"rag.read"}), 5)
    assert search.candidates[0].document == document
    assert search.filtered_document_count == 2
    assert any("required_permissions" in query for query, _params in calls)

    monkeypatch.setattr(
        repo,
        "_fetch_one",
        lambda _query, _params: {
            "filename": artifact.filename,
            "content_type": artifact.content_type,
            "content": "invalid",
            "sha256": artifact.sha256,
        },
    )
    with pytest.raises(ValidationError, match="content is invalid"):
        repo.get_artifact(tenant, job.id.value)
    with pytest.raises(ValueError, match="unsupported RAG pagination"):
        repo._page("rag_documents", tenant, Pagination(limit=1), "id")
