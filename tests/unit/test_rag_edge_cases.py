from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.rag import (
    RagAnswer,
    RagAnswerPage,
    RagAnswerStatus,
    RagArtifact,
    RagChunk,
    RagCitation,
    RagDocument,
    RagDocumentPage,
    RagJobKind,
    RagJobPage,
    RagJobStatus,
    RagSourceType,
    RagSyncResult,
    RagTextProcessor,
    RagTransferJob,
    RagValidator,
)


def _document() -> RagDocument:
    return RagDocument.create(
        TenantId.from_value("default"),
        "documentation",
        "edge-runbook",
        "Edge runbook",
        "OpenInfra utilise PostgreSQL pour la persistance.\n\nLe réseau utilise des VLAN.",
        ("rag.read",),
        ("edge",),
        {"owner": "qa"},
        "https://example.invalid/runbook",
    )


def test_rag_validator_and_text_processor_cover_all_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    assert RagSourceType.from_value("DOCUMENTATION") is RagSourceType.DOCUMENTATION
    assert RagJobKind.from_value("ANSWER_EXPORT") is RagJobKind.ANSWER_EXPORT
    with pytest.raises(ValidationError, match="source type"):
        RagSourceType.from_value("unsupported")
    with pytest.raises(ValidationError, match="job kind"):
        RagJobKind.from_value("unsupported")

    assert RagValidator.optional_text(None, "optional") is None
    assert RagValidator.optional_text("   ", "optional") is None
    assert RagValidator.optional_text(" value ", "optional") == "value"
    with pytest.raises(ValidationError, match="1 to 4"):
        RagValidator.text("", "short", 4)
    with pytest.raises(ValidationError, match="safe characters"):
        RagValidator.key("unsafe key!", "key")
    with pytest.raises(ValidationError, match="SHA-256"):
        RagValidator.sha256("not-a-digest")

    assert RagValidator.uri(None) is None
    assert RagValidator.uri(" ") is None
    for value, message in (
        ("https://example.invalid/path with space", "invalid"),
        ("https:///missing-host", "requires a host"),
        ("urn:", "requires a path"),
        ("ftp://example.invalid/file", "must use"),
    ):
        with pytest.raises(ValidationError, match=message):
            RagValidator.uri(value)

    for value in ("", "\x00invalid"):
        with pytest.raises(ValidationError, match="content"):
            RagValidator.content(value)
    with pytest.raises(ValidationError, match="1048576"):
        RagValidator.content("a" * 1_048_577)
    with pytest.raises(ValidationError, match="3 to 2000"):
        RagValidator.question("no")
    with pytest.raises(ValidationError, match="at least one permission"):
        RagValidator.permissions(())
    monkeypatch.setattr(
        RagValidator, "_PERMISSIONS", frozenset(f"permission.{i}" for i in range(33))
    )
    with pytest.raises(ValidationError, match="more than 32"):
        RagValidator.permissions(tuple(f"permission.{i}" for i in range(33)))

    with pytest.raises(ValidationError, match="JSON object"):
        RagValidator.json_object([], "metadata")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="serializable"):
        RagValidator.json_object({"value": object()}, "metadata")
    with pytest.raises(ValidationError, match="exceeds"):
        RagValidator.json_object({"value": "x" * 100}, "metadata", maximum_bytes=10)
    assert RagValidator.json_object({"values": (1, 2)}, "metadata") == {"values": [1, 2]}

    with pytest.raises(ValidationError, match="timezone-aware"):
        RagValidator.aware_datetime(datetime(2026, 7, 11), "created_at")
    for value in ("invalid", Decimal("NaN"), Decimal("-0.1")):
        with pytest.raises(ValidationError, match="score"):
            RagValidator.score(value)
    with pytest.raises(ValidationError, match="between 0 and 1"):
        RagValidator.confidence("1.1")

    with pytest.raises(ValidationError, match="parameters"):
        RagTextProcessor.chunk("valid content", maximum=100)
    long_paragraph = "A" * 700
    chunks = RagTextProcessor.chunk(
        f"prefix\n\n{long_paragraph}\n\nsuffix", maximum=256, overlap=16
    )
    assert len(chunks) >= 4
    buffered = RagTextProcessor.chunk(
        ("first " * 30) + "\n\n" + ("second " * 25), maximum=256, overlap=12
    )
    assert len(buffered) == 2
    assert buffered[1].startswith(buffered[0][-12:].strip())
    assert RagTextProcessor.excerpt("short text", 20) == "short text"
    assert RagTextProcessor.excerpt("word " * 30, 24).endswith("…")


def test_rag_entities_restore_state_and_serialization_guards() -> None:
    document = _document()
    chunk = document.chunks[0]
    with pytest.raises(ValidationError, match="ordinal"):
        RagChunk.create(document.id, -1, "invalid")
    with pytest.raises(ValidationError, match="checksum"):
        RagChunk.restore(
            chunk.id,
            chunk.document_id,
            chunk.ordinal,
            chunk.content,
            "0" * 64,
            chunk.terms,
        )
    with pytest.raises(ValidationError, match="ordinal"):
        RagChunk.restore(
            chunk.id,
            chunk.document_id,
            -1,
            chunk.content,
            chunk.checksum,
            chunk.terms,
        )
    assert (
        RagChunk.restore(
            chunk.id,
            chunk.document_id,
            chunk.ordinal,
            chunk.content,
            chunk.checksum,
            chunk.terms,
        ).as_dict()["checksum"]
        == chunk.checksum
    )

    with pytest.raises(ValidationError, match="version"):
        RagDocument.create(
            document.tenant_id,
            "documentation",
            "invalid-version",
            "Invalid",
            "valid content",
            ("rag.read",),
            version=0,
        )
    with pytest.raises(ValidationError, match="version"):
        RagDocument.restore(
            document.id,
            document.tenant_id,
            document.source_type.value,
            document.source_ref,
            document.source_uri,
            document.title,
            document.content,
            document.required_permissions,
            document.tags,
            document.metadata,
            0,
            document.checksum,
            True,
            document.chunks,
            document.indexed_at,
        )
    foreign = RagChunk.create(EntityId.new(), 0, "foreign chunk")
    with pytest.raises(ValidationError, match="another document"):
        RagDocument.restore(
            document.id,
            document.tenant_id,
            document.source_type.value,
            document.source_ref,
            document.source_uri,
            document.title,
            document.content,
            document.required_permissions,
            document.tags,
            document.metadata,
            document.version,
            document.checksum,
            True,
            (foreign,),
            document.indexed_at,
        )
    restored = RagDocument.restore(
        document.id,
        document.tenant_id,
        document.source_type.value,
        document.source_ref,
        document.source_uri,
        document.title,
        document.content,
        document.required_permissions,
        document.tags,
        document.metadata,
        document.version,
        document.checksum,
        False,
        document.chunks,
        document.indexed_at,
    )
    assert restored.identity_key == "documentation:edge-runbook"
    assert restored.deactivate() is restored
    assert restored.as_dict()["active"] is False

    citation = RagCitation.create(document, chunk, Decimal("2.5"))
    restored_citation = RagCitation.restore(
        citation.document_id,
        citation.chunk_id,
        citation.source_type,
        citation.source_ref,
        citation.source_uri,
        citation.title,
        citation.excerpt,
        citation.score,
    )
    assert restored_citation.as_dict()["score"] == "2.5000"

    with pytest.raises(ValidationError, match="insufficient-context"):
        RagAnswer.create(
            document.tenant_id,
            "Question valide ?",
            "Réponse invalide.",
            RagAnswerStatus.INSUFFICIENT_CONTEXT,
            Decimal("0"),
            (citation,),
        )
    answer = RagAnswer.create(
        document.tenant_id,
        "Question valide ?",
        "Réponse citée [1].",
        RagAnswerStatus.ANSWERED,
        Decimal("0.8"),
        (citation,),
    )
    with pytest.raises(ValidationError, match="hash"):
        RagAnswer.restore(
            answer.id,
            answer.tenant_id,
            answer.question,
            "0" * 64,
            answer.answer,
            answer.status.value,
            answer.confidence,
            answer.citations,
            answer.retrieval_model,
            answer.generated_at,
        )
    for status, citations, message in (
        ("unsupported", answer.citations, "status"),
        ("answered", (), "requires"),
        ("insufficient-context", answer.citations, "cannot contain"),
    ):
        with pytest.raises(ValidationError, match=message):
            RagAnswer.restore(
                answer.id,
                answer.tenant_id,
                answer.question,
                answer.question_hash,
                answer.answer,
                status,
                answer.confidence,
                citations,
                answer.retrieval_model,
                answer.generated_at,
            )
    assert RagAnswer.restore(
        answer.id,
        answer.tenant_id,
        answer.question,
        answer.question_hash,
        answer.answer,
        answer.status.value,
        answer.confidence,
        answer.citations,
        answer.retrieval_model,
        answer.generated_at,
    ).as_dict()["citations"]


def test_rag_job_pages_sync_and_artifact_guards() -> None:
    tenant_id = TenantId.from_value("default")
    for total, batch, message in ((-1, 1, "negative"), (1, 0, "between 1 and 500")):
        with pytest.raises(ValidationError, match=message):
            RagTransferJob.create(tenant_id, "document-import", "edge-job", {}, total, batch)
    job = RagTransferJob.create(
        tenant_id,
        "answer-export",
        "edge-export",
        {"format": "json", "answer_ids": []},
        1,
        1,
    )
    for digest, status, processed, total, batch, message in (
        ("0" * 64, "queued", 0, 1, 1, "digest"),
        (job.input_digest, "unknown", 0, 1, 1, "status"),
        (job.input_digest, "queued", 2, 1, 1, "progress"),
        (job.input_digest, "queued", 0, 1, 0, "batch size"),
    ):
        with pytest.raises(ValidationError, match=message):
            RagTransferJob.restore(
                job.id,
                job.tenant_id,
                job.kind.value,
                status,
                job.idempotency_key,
                digest,
                job.payload,
                processed,
                total,
                batch,
                None,
                job.created_at,
                job.updated_at,
            )
    restored = RagTransferJob.restore(
        job.id,
        job.tenant_id,
        job.kind.value,
        job.status.value,
        job.idempotency_key,
        job.input_digest,
        job.payload,
        job.processed_count,
        job.total_count,
        job.batch_size,
        None,
        job.created_at,
        job.updated_at,
    )
    completed = restored.start().advance(1)
    assert completed.start() is completed
    assert completed.as_dict()["status"] == RagJobStatus.COMPLETED.value

    assert RagDocumentPage((), "1").as_dict() == {"items": [], "next_cursor": "1"}
    assert RagAnswerPage((), None).as_dict() == {"items": [], "next_cursor": None}
    assert RagJobPage((completed,), None).as_dict()["items"][0]["status"] == "completed"
    assert RagSyncResult(1, 2, 3, 4).as_dict()["deactivated"] == 4
    with pytest.raises(ValidationError, match="cannot be empty"):
        RagArtifact.create("empty.json", "application/json", b"")
    artifact = RagArtifact.create("result.json", "application/json", b"{}")
    assert artifact.sha256 == hashlib.sha256(b"{}").hexdigest()
