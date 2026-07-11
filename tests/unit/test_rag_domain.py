from __future__ import annotations

from decimal import Decimal

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.rag import (
    RagAnswer,
    RagAnswerStatus,
    RagCitation,
    RagDocument,
    RagJobKind,
    RagTextProcessor,
    RagTransferJob,
    RagValidator,
)


def _document() -> RagDocument:
    return RagDocument.create(
        TenantId.from_value("default"),
        "documentation",
        "runbook-openinfra",
        "Runbook OpenInfra",
        "OpenInfra utilise PostgreSQL.\n\nLe service web expose une API gouvernée.",
        ("rag.read",),
        ("production",),
        {"owner": "platform"},
        "https://example.invalid/runbook",
    )


def test_rag_document_chunking_citations_and_answer_invariants() -> None:
    document = _document()
    assert document.chunks
    assert RagTextProcessor.terms("Quelle base utilise OpenInfra ?") >= ("base", "openinfra")
    citation = RagCitation.create(document, document.chunks[0], Decimal("3.5"))
    answer = RagAnswer.create(
        document.tenant_id,
        "Quelle base utilise OpenInfra ?",
        "OpenInfra utilise PostgreSQL [1].",
        RagAnswerStatus.ANSWERED,
        Decimal("0.8"),
        (citation,),
    )
    assert answer.citations == (citation,)
    with pytest.raises(ValidationError, match="requires at least one citation"):
        RagAnswer.create(
            document.tenant_id,
            "Quelle base utilise OpenInfra ?",
            "Réponse sans source.",
            RagAnswerStatus.ANSWERED,
            Decimal("0.2"),
            (),
        )


def test_rag_validator_rejects_secrets_unknown_permissions_and_invalid_uri() -> None:
    with pytest.raises(ValidationError, match="sensitive key"):
        RagValidator.json_object({"nested": {"api_token": "forbidden"}}, "metadata")
    with pytest.raises(ValidationError, match="unsupported RAG permission"):
        RagValidator.permissions(("unknown.permission",))
    with pytest.raises(ValidationError, match="must use"):
        RagValidator.uri("javascript:alert(1)")


def test_rag_document_versioning_deactivation_and_restore_guards() -> None:
    document = _document()
    assert document.deactivate().active is False
    with pytest.raises(ValidationError, match="checksum"):
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
            "0" * 64,
            True,
            document.chunks,
            document.indexed_at,
        )


def test_rag_transfer_job_progress_and_failure_guards() -> None:
    job = RagTransferJob.create(
        TenantId.from_value("default"),
        RagJobKind.DOCUMENT_IMPORT.value,
        "import-2026-07-11",
        {"documents": [{"source_ref": "a"}]},
        1,
        1,
    )
    running = job.start()
    assert running.advance(1).status.value == "completed"
    assert running.fail("invalid document").status.value == "failed"
    with pytest.raises(ValidationError, match="cannot move backwards"):
        running.advance(-1)
