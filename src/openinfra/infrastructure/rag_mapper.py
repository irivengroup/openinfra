from __future__ import annotations

from datetime import datetime
from typing import Any

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.rag import (
    RagAnswer,
    RagChunk,
    RagCitation,
    RagDocument,
    RagTransferJob,
)


class RagRecordMapper:
    @staticmethod
    def _datetime(value: object, field: str) -> datetime:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError(f"invalid RAG datetime: {field}") from exc

    @staticmethod
    def _mapping(value: object, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{field} must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @classmethod
    def chunk(cls, value: dict[str, Any]) -> RagChunk:
        return RagChunk.restore(
            EntityId.from_value(str(value["id"])),
            EntityId.from_value(str(value["document_id"])),
            int(value["ordinal"]),
            str(value["content"]),
            str(value["checksum"]),
            tuple(str(item) for item in value.get("terms", [])),
        )

    @classmethod
    def document(cls, value: dict[str, Any]) -> RagDocument:
        raw_chunks = value.get("chunks")
        if not isinstance(raw_chunks, list):
            raise ValidationError("RAG chunks must be an array")
        return RagDocument.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["source_type"]),
            str(value["source_ref"]),
            None if value.get("source_uri") is None else str(value["source_uri"]),
            str(value["title"]),
            str(value["content"]),
            tuple(str(item) for item in value.get("required_permissions", [])),
            tuple(str(item) for item in value.get("tags", [])),
            cls._mapping(value.get("metadata", {}), "RAG metadata"),
            int(value["version"]),
            str(value["checksum"]),
            bool(value["active"]),
            tuple(cls.chunk(cls._mapping(item, "RAG chunk")) for item in raw_chunks),
            cls._datetime(value["indexed_at"], "indexed_at"),
        )

    @classmethod
    def citation(cls, value: dict[str, Any]) -> RagCitation:
        return RagCitation.restore(
            str(value["document_id"]),
            str(value["chunk_id"]),
            str(value["source_type"]),
            str(value["source_ref"]),
            None if value.get("source_uri") is None else str(value["source_uri"]),
            str(value["title"]),
            str(value["excerpt"]),
            str(value["score"]),
        )

    @classmethod
    def answer(cls, value: dict[str, Any]) -> RagAnswer:
        raw_citations = value.get("citations")
        if not isinstance(raw_citations, list):
            raise ValidationError("RAG citations must be an array")
        return RagAnswer.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["question"]),
            str(value["question_hash"]),
            str(value["answer"]),
            str(value["status"]),
            str(value["confidence"]),
            tuple(cls.citation(cls._mapping(item, "RAG citation")) for item in raw_citations),
            str(value["retrieval_model"]),
            cls._datetime(value["generated_at"], "generated_at"),
        )

    @classmethod
    def job(cls, value: dict[str, Any]) -> RagTransferJob:
        return RagTransferJob.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["kind"]),
            str(value["status"]),
            str(value["idempotency_key"]),
            str(value["input_digest"]),
            cls._mapping(value.get("payload", {}), "RAG job payload"),
            int(value["processed_count"]),
            int(value["total_count"]),
            int(value["batch_size"]),
            None if value.get("error") is None else str(value["error"]),
            cls._datetime(value["created_at"], "created_at"),
            cls._datetime(value["updated_at"], "updated_at"),
        )
