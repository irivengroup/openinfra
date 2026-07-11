from __future__ import annotations

from decimal import Decimal

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.rag import (
    RagAnswer,
    RagAnswerStatus,
    RagCitation,
    RagDocument,
    RagTransferJob,
)
from openinfra.infrastructure.rag_generator import DeterministicRagGenerator
from openinfra.infrastructure.rag_mapper import RagRecordMapper


def _citation(excerpt: str, ordinal: int = 1) -> RagCitation:
    return RagCitation(
        document_id=f"{ordinal:032x}",
        chunk_id=f"{ordinal + 10:032x}",
        source_type="documentation",
        source_ref=f"doc-{ordinal}",
        source_uri=None,
        title=f"Document {ordinal}",
        excerpt=excerpt,
        score=Decimal("2.0"),
    )


def test_deterministic_generator_handles_empty_duplicates_and_five_source_limit() -> None:
    generator = DeterministicRagGenerator()
    assert "Aucune source" in generator.generate("question", ())
    assert "ne permet pas" in generator.generate("question", (_citation(""),))

    duplicated = generator.generate(
        "postgresql",
        (_citation("PostgreSQL est utilisé."), _citation("PostgreSQL est utilisé.", 2)),
    )
    assert duplicated.count("PostgreSQL est utilisé") == 1

    citations = tuple(
        _citation(f"Source distincte {index} PostgreSQL.", index) for index in range(1, 8)
    )
    generated = generator.generate("PostgreSQL", citations)
    assert generated.count("\n-") == 5
    assert "[5]" in generated
    assert "[6]" not in generated


def test_rag_mapper_round_trips_and_rejects_invalid_shapes() -> None:
    document = RagDocument.create(
        tenant_id=TenantId.from_value("default"),
        source_type="documentation",
        source_ref="mapper",
        title="Mapper",
        content="Mapper round trip content.",
        required_permissions=("rag.read",),
    )
    mapped_document = RagRecordMapper.document(document.as_dict())
    assert mapped_document.id == document.id

    citation = RagCitation.create(document, document.chunks[0], Decimal("1"))
    answer = RagAnswer.create(
        document.tenant_id,
        "What is mapped?",
        "The document is mapped [1].",
        RagAnswerStatus.ANSWERED,
        Decimal("0.5"),
        (citation,),
    )
    assert RagRecordMapper.answer(answer.as_dict()).id == answer.id

    job = RagTransferJob.create(
        document.tenant_id,
        "answer-export",
        "mapper-export",
        {"format": "json", "answer_ids": []},
        1,
    )
    assert RagRecordMapper.job(job.as_dict()).id == job.id

    invalid_datetime = document.as_dict()
    invalid_datetime["indexed_at"] = "not-a-date"
    with pytest.raises(ValidationError, match="invalid RAG datetime"):
        RagRecordMapper.document(invalid_datetime)

    invalid_metadata = document.as_dict()
    invalid_metadata["metadata"] = []
    with pytest.raises(ValidationError, match="JSON object"):
        RagRecordMapper.document(invalid_metadata)

    invalid_chunks = document.as_dict()
    invalid_chunks["chunks"] = {}
    with pytest.raises(ValidationError, match="chunks must be an array"):
        RagRecordMapper.document(invalid_chunks)

    invalid_citations = answer.as_dict()
    invalid_citations["citations"] = {}
    with pytest.raises(ValidationError, match="citations must be an array"):
        RagRecordMapper.answer(invalid_citations)
