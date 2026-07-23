from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Self, cast
from urllib.parse import urlparse

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.security import Permission


class RagSourceType(StrEnum):
    RSOT = "rsot"
    RUNBOOK = "runbook"
    POLICY = "policy"
    DOCUMENTATION = "documentation"
    OTHER = "other"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("RAG source type is unsupported") from exc


class RagAnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_CONTEXT = "insufficient-context"


class RagJobKind(StrEnum):
    DOCUMENT_IMPORT = "document-import"
    ANSWER_EXPORT = "answer-export"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("RAG job kind is unsupported") from exc


class RagJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RagValidator:
    _SAFE_KEY = re.compile(r"[a-z0-9][a-z0-9_.:@/+~-]{0,255}")
    _SHA256 = re.compile(r"[a-f0-9]{64}")
    _SENSITIVE_KEY = re.compile(
        r"(?:^|[_\-.])(password|passwd|pwd|secret|token|credential|api[_-]?key|private[_-]?key)(?:$|[_\-.])",
        re.IGNORECASE,
    )
    _PERMISSIONS = frozenset(item.value for item in Permission)

    @classmethod
    def text(cls, value: str, label: str, maximum: int = 512) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain 1 to {maximum} characters")
        return normalized

    @classmethod
    def optional_text(cls, value: str | None, label: str, maximum: int = 512) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.text(value, label, maximum)

    @classmethod
    def key(cls, value: str, label: str, maximum: int = 256) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if len(normalized) > maximum or not cls._SAFE_KEY.fullmatch(normalized):
            raise ValidationError(f"{label} must use 1 to {maximum} safe characters")
        return normalized

    @classmethod
    def sha256(cls, value: str, label: str = "sha256") -> str:
        normalized = value.strip().lower()
        if not cls._SHA256.fullmatch(normalized):
            raise ValidationError(f"{label} must be a SHA-256 hexadecimal digest")
        return normalized

    @classmethod
    def uri(cls, value: str | None, label: str = "URI") -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if len(normalized) > 2048 or any(char.isspace() for char in normalized):
            raise ValidationError(f"{label} is invalid")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"https", "http", "file", "urn", "openinfra"}:
            raise ValidationError(f"{label} must use https, http, file, urn or openinfra")
        if parsed.scheme in {"https", "http"} and not parsed.netloc:
            raise ValidationError(f"{label} requires a host")
        if parsed.scheme in {"file", "urn", "openinfra"} and not parsed.path:
            raise ValidationError(f"{label} requires a path")
        return normalized

    @classmethod
    def content(cls, value: str) -> str:
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        encoded = normalized.encode("utf-8")
        if not normalized or len(encoded) > 1_048_576:
            raise ValidationError("RAG document content must contain 1 to 1048576 UTF-8 bytes")
        if "\x00" in normalized:
            raise ValidationError("RAG document content cannot contain NUL characters")
        return normalized

    @classmethod
    def question(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 3 <= len(normalized) <= 2_000:
            raise ValidationError("RAG question must contain 3 to 2000 characters")
        return normalized

    @classmethod
    def permissions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted({value.strip().lower() for value in values if value.strip()}))
        if not normalized:
            raise ValidationError("RAG document requires at least one permission")
        if len(normalized) > 32:
            raise ValidationError("RAG document cannot require more than 32 permissions")
        unknown = [value for value in normalized if value not in cls._PERMISSIONS]
        if unknown:
            raise ValidationError(f"unsupported RAG permission: {unknown[0]}")
        return normalized

    @classmethod
    def tags(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({cls.key(value, "RAG tag", 64) for value in values if value.strip()}))

    @classmethod
    def json_object(
        cls, value: dict[str, Any], label: str, maximum_bytes: int = 262_144
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        normalized = cast(dict[str, Any], cls._sanitize(value, label, "$"))
        try:
            encoded = json.dumps(
                normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{label} must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > maximum_bytes:
            raise ValidationError(f"{label} exceeds {maximum_bytes} bytes")
        return normalized

    @classmethod
    def _sanitize(cls, value: Any, label: str, path: str) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key, item in value.items():
                key = str(raw_key)
                if cls._SENSITIVE_KEY.search(key):
                    raise ValidationError(f"{label} contains a sensitive key at {path}.{key}")
                result[key] = cls._sanitize(item, label, f"{path}.{key}")
            return result
        if isinstance(value, (list, tuple)):
            return [
                cls._sanitize(item, label, f"{path}[{index}]") for index, item in enumerate(value)
            ]
        return value

    @staticmethod
    def digest(payload: object) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def aware_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def score(value: Decimal | str | int | float) -> Decimal:
        try:
            normalized = Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("RAG score must be a finite decimal") from exc
        if not normalized.is_finite() or normalized < 0:
            raise ValidationError("RAG score must be non-negative")
        return normalized

    @staticmethod
    def confidence(value: Decimal | str | int | float) -> Decimal:
        normalized = RagValidator.score(value)
        if normalized > 1:
            raise ValidationError("RAG confidence must be between 0 and 1")
        return normalized


class RagTextProcessor:
    _WORD = re.compile(r"[a-z0-9][a-z0-9_.:/+-]{1,63}")
    _STOP_WORDS = frozenset(
        {
            "avec",
            "dans",
            "des",
            "est",
            "les",
            "pour",
            "quel",
            "quelle",
            "quels",
            "quelles",
            "sur",
            "une",
            "the",
            "and",
            "for",
            "from",
            "what",
            "which",
            "with",
            "this",
            "that",
        }
    )

    @classmethod
    def normalize(cls, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.lower())
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    @classmethod
    def terms(cls, value: str) -> tuple[str, ...]:
        normalized = cls.normalize(value)
        return tuple(
            sorted(
                {
                    match.group(0)
                    for match in cls._WORD.finditer(normalized)
                    if match.group(0) not in cls._STOP_WORDS
                }
            )
        )

    @classmethod
    def chunk(cls, content: str, maximum: int = 1_200, overlap: int = 160) -> tuple[str, ...]:
        normalized = RagValidator.content(content)
        if maximum < 256 or overlap < 0 or overlap >= maximum:
            raise ValidationError("RAG chunking parameters are invalid")
        paragraphs = [item.strip() for item in re.split(r"\n{2,}", normalized) if item.strip()]
        chunks: list[str] = []
        buffer = ""
        for paragraph in paragraphs:
            if len(paragraph) > maximum:
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                start = 0
                while start < len(paragraph):
                    end = min(start + maximum, len(paragraph))
                    candidate = paragraph[start:end].strip()
                    if candidate:
                        chunks.append(candidate)
                    if end == len(paragraph):
                        break
                    start = end - overlap
                continue
            candidate = paragraph if not buffer else f"{buffer}\n\n{paragraph}"
            if len(candidate) <= maximum:
                buffer = candidate
            else:
                chunks.append(buffer)
                prefix = buffer[-overlap:].strip() if overlap else ""
                buffer = f"{prefix}\n\n{paragraph}".strip()
        if buffer:
            chunks.append(buffer)
        return tuple(chunks or (normalized,))

    @classmethod
    def excerpt(cls, value: str, maximum: int = 600) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= maximum:
            return normalized
        clipped = normalized[: maximum - 1].rsplit(" ", 1)[0].rstrip()
        return f"{clipped}…"


@dataclass(frozen=True, slots=True)
class RagChunk:
    id: EntityId
    document_id: EntityId
    ordinal: int
    content: str
    checksum: str
    terms: tuple[str, ...]

    @classmethod
    def create(cls, document_id: EntityId, ordinal: int, content: str) -> Self:
        if ordinal < 0:
            raise ValidationError("RAG chunk ordinal cannot be negative")
        normalized = RagValidator.content(content)
        checksum = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return cls(
            EntityId.new(),
            document_id,
            ordinal,
            normalized,
            checksum,
            RagTextProcessor.terms(normalized),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        document_id: EntityId,
        ordinal: int,
        content: str,
        checksum: str,
        terms: tuple[str, ...],
    ) -> Self:
        normalized = RagValidator.content(content)
        expected = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if RagValidator.sha256(checksum, "RAG chunk checksum") != expected:
            raise ValidationError("RAG chunk checksum does not match content")
        if ordinal < 0:
            raise ValidationError("RAG chunk ordinal cannot be negative")
        normalized_terms = tuple(sorted({RagValidator.key(item, "RAG term", 64) for item in terms}))
        return cls(id, document_id, ordinal, normalized, expected, normalized_terms)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "document_id": self.document_id.value,
            "ordinal": self.ordinal,
            "content": self.content,
            "checksum": self.checksum,
            "terms": list(self.terms),
        }


@dataclass(frozen=True, slots=True)
class RagDocument:
    id: EntityId
    tenant_id: TenantId
    source_type: RagSourceType
    source_ref: str
    source_uri: str | None
    title: str
    content: str
    required_permissions: tuple[str, ...]
    tags: tuple[str, ...]
    metadata: dict[str, Any]
    version: int
    checksum: str
    active: bool
    chunks: tuple[RagChunk, ...]
    indexed_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        source_type: str,
        source_ref: str,
        title: str,
        content: str,
        required_permissions: tuple[str, ...],
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        source_uri: str | None = None,
        version: int = 1,
    ) -> Self:
        if version < 1:
            raise ValidationError("RAG document version must be positive")
        normalized_content = RagValidator.content(content)
        document_id = EntityId.new()
        chunks = tuple(
            RagChunk.create(document_id, index, chunk)
            for index, chunk in enumerate(RagTextProcessor.chunk(normalized_content))
        )
        return cls(
            document_id,
            tenant_id,
            RagSourceType.from_value(source_type),
            RagValidator.text(source_ref, "RAG source reference", 512),
            RagValidator.uri(source_uri, "RAG source URI"),
            RagValidator.text(title, "RAG document title", 512),
            normalized_content,
            RagValidator.permissions(required_permissions),
            RagValidator.tags(tags),
            RagValidator.json_object(metadata or {}, "RAG document metadata"),
            version,
            hashlib.sha256(normalized_content.encode("utf-8")).hexdigest(),
            True,
            chunks,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        source_type: str,
        source_ref: str,
        source_uri: str | None,
        title: str,
        content: str,
        required_permissions: tuple[str, ...],
        tags: tuple[str, ...],
        metadata: dict[str, Any],
        version: int,
        checksum: str,
        active: bool,
        chunks: tuple[RagChunk, ...],
        indexed_at: datetime,
    ) -> Self:
        normalized_content = RagValidator.content(content)
        expected = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        if RagValidator.sha256(checksum, "RAG document checksum") != expected:
            raise ValidationError("RAG document checksum does not match content")
        if version < 1:
            raise ValidationError("RAG document version must be positive")
        if any(chunk.document_id != id for chunk in chunks):
            raise ValidationError("RAG chunk references another document")
        return cls(
            id,
            tenant_id,
            RagSourceType.from_value(source_type),
            RagValidator.text(source_ref, "RAG source reference", 512),
            RagValidator.uri(source_uri, "RAG source URI"),
            RagValidator.text(title, "RAG document title", 512),
            normalized_content,
            RagValidator.permissions(required_permissions),
            RagValidator.tags(tags),
            RagValidator.json_object(metadata, "RAG document metadata"),
            version,
            expected,
            bool(active),
            chunks,
            RagValidator.aware_datetime(indexed_at, "indexed_at"),
        )

    @property
    def identity_key(self) -> str:
        return f"{self.source_type.value}:{self.source_ref.lower()}"

    def deactivate(self) -> Self:
        if not self.active:
            return self
        return replace(self, active=False, indexed_at=datetime.now(UTC))

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
            "source_uri": self.source_uri,
            "title": self.title,
            "content": self.content,
            "required_permissions": list(self.required_permissions),
            "tags": list(self.tags),
            "metadata": self.metadata,
            "version": self.version,
            "checksum": self.checksum,
            "active": self.active,
            "chunks": [chunk.as_dict() for chunk in self.chunks],
            "indexed_at": self.indexed_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RagCitation:
    document_id: str
    chunk_id: str
    source_type: str
    source_ref: str
    source_uri: str | None
    title: str
    excerpt: str
    score: Decimal

    @classmethod
    def create(cls, document: RagDocument, chunk: RagChunk, score: Decimal | float) -> Self:
        return cls(
            document.id.value,
            chunk.id.value,
            document.source_type.value,
            document.source_ref,
            document.source_uri,
            document.title,
            RagTextProcessor.excerpt(chunk.content),
            RagValidator.score(score),
        )

    @classmethod
    def restore(
        cls,
        document_id: str,
        chunk_id: str,
        source_type: str,
        source_ref: str,
        source_uri: str | None,
        title: str,
        excerpt: str,
        score: Decimal | str | float,
    ) -> Self:
        return cls(
            EntityId.from_value(document_id).value,
            EntityId.from_value(chunk_id).value,
            RagSourceType.from_value(source_type).value,
            RagValidator.text(source_ref, "RAG source reference", 512),
            RagValidator.uri(source_uri, "RAG source URI"),
            RagValidator.text(title, "RAG citation title", 512),
            RagValidator.text(excerpt, "RAG citation excerpt", 600),
            RagValidator.score(score),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "source_uri": self.source_uri,
            "title": self.title,
            "excerpt": self.excerpt,
            "score": str(self.score),
        }


@dataclass(frozen=True, slots=True)
class RagAnswer:
    id: EntityId
    tenant_id: TenantId
    question: str
    question_hash: str
    answer: str
    status: RagAnswerStatus
    confidence: Decimal
    citations: tuple[RagCitation, ...]
    retrieval_model: str
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        question: str,
        answer: str,
        status: RagAnswerStatus,
        confidence: Decimal | float,
        citations: tuple[RagCitation, ...],
        retrieval_model: str = "openinfra-extractive-rag-v1",
    ) -> Self:
        normalized_question = RagValidator.question(question)
        normalized_answer = RagValidator.text(answer, "RAG answer", 12_000)
        if status is RagAnswerStatus.ANSWERED and not citations:
            raise ValidationError("answered RAG response requires at least one citation")
        if status is RagAnswerStatus.INSUFFICIENT_CONTEXT and citations:
            raise ValidationError("insufficient-context response cannot contain citations")
        return cls(
            EntityId.new(),
            tenant_id,
            normalized_question,
            hashlib.sha256(normalized_question.encode("utf-8")).hexdigest(),
            normalized_answer,
            status,
            RagValidator.confidence(confidence),
            citations,
            RagValidator.key(retrieval_model, "RAG retrieval model", 128),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        question: str,
        question_hash: str,
        answer: str,
        status: str,
        confidence: Decimal | str | float,
        citations: tuple[RagCitation, ...],
        retrieval_model: str,
        generated_at: datetime,
    ) -> Self:
        normalized_question = RagValidator.question(question)
        expected = hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()
        if RagValidator.sha256(question_hash, "RAG question hash") != expected:
            raise ValidationError("RAG question hash does not match question")
        try:
            normalized_status = RagAnswerStatus(status.strip().lower().replace("_", "-"))
        except ValueError as exc:
            raise ValidationError("RAG answer status is unsupported") from exc
        if normalized_status is RagAnswerStatus.ANSWERED and not citations:
            raise ValidationError("answered RAG response requires at least one citation")
        if normalized_status is RagAnswerStatus.INSUFFICIENT_CONTEXT and citations:
            raise ValidationError("insufficient-context response cannot contain citations")
        return cls(
            id,
            tenant_id,
            normalized_question,
            expected,
            RagValidator.text(answer, "RAG answer", 12_000),
            normalized_status,
            RagValidator.confidence(confidence),
            citations,
            RagValidator.key(retrieval_model, "RAG retrieval model", 128),
            RagValidator.aware_datetime(generated_at, "generated_at"),
        )

    def source_object_citations(self) -> tuple[dict[str, object], ...]:
        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for citation in self.citations:
            if citation.source_type != RagSourceType.RSOT.value or citation.source_ref in seen:
                continue
            seen.add(citation.source_ref)
            result.append(
                {
                    "object_key": citation.source_ref,
                    "source_uri": citation.source_uri,
                    "title": citation.title,
                    "document_id": citation.document_id,
                    "chunk_id": citation.chunk_id,
                    "score": str(citation.score),
                }
            )
        return tuple(result)

    @staticmethod
    def governance() -> dict[str, object]:
        return {
            "mode": "read-only",
            "source_data_mutation_performed": False,
            "change_validation_required": True,
            "execution_capabilities": [],
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "question": self.question,
            "question_hash": self.question_hash,
            "answer": self.answer,
            "status": self.status.value,
            "confidence": str(self.confidence),
            "citations": [citation.as_dict() for citation in self.citations],
            "source_objects": list(self.source_object_citations()),
            "governance": self.governance(),
            "retrieval_model": self.retrieval_model,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RagTransferJob:
    id: EntityId
    tenant_id: TenantId
    kind: RagJobKind
    status: RagJobStatus
    idempotency_key: str
    input_digest: str
    payload: dict[str, Any]
    processed_count: int
    total_count: int
    batch_size: int
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        kind: str,
        idempotency_key: str,
        payload: dict[str, Any],
        total_count: int,
        batch_size: int = 100,
    ) -> Self:
        if total_count < 0:
            raise ValidationError("RAG job total count cannot be negative")
        if not 1 <= batch_size <= 500:
            raise ValidationError("RAG job batch size must be between 1 and 500")
        normalized_payload = RagValidator.json_object(
            payload, "RAG job payload", maximum_bytes=5_242_880
        )
        now = datetime.now(UTC)
        return cls(
            EntityId.new(),
            tenant_id,
            RagJobKind.from_value(kind),
            RagJobStatus.QUEUED,
            RagValidator.key(idempotency_key, "RAG idempotency key", 128),
            RagValidator.digest(normalized_payload),
            normalized_payload,
            0,
            total_count,
            batch_size,
            None,
            now,
            now,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        kind: str,
        status: str,
        idempotency_key: str,
        input_digest: str,
        payload: dict[str, Any],
        processed_count: int,
        total_count: int,
        batch_size: int,
        error: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        normalized_payload = RagValidator.json_object(
            payload, "RAG job payload", maximum_bytes=5_242_880
        )
        if RagValidator.sha256(input_digest, "RAG job input digest") != RagValidator.digest(
            normalized_payload
        ):
            raise ValidationError("RAG job input digest does not match payload")
        try:
            normalized_status = RagJobStatus(status.strip().lower().replace("_", "-"))
        except ValueError as exc:
            raise ValidationError("RAG job status is unsupported") from exc
        if total_count < 0 or not 0 <= processed_count <= total_count:
            raise ValidationError("RAG job progress is invalid")
        if not 1 <= batch_size <= 500:
            raise ValidationError("RAG job batch size must be between 1 and 500")
        return cls(
            id,
            tenant_id,
            RagJobKind.from_value(kind),
            normalized_status,
            RagValidator.key(idempotency_key, "RAG idempotency key", 128),
            RagValidator.sha256(input_digest, "RAG job input digest"),
            normalized_payload,
            processed_count,
            total_count,
            batch_size,
            RagValidator.optional_text(error, "RAG job error", 2_000),
            RagValidator.aware_datetime(created_at, "created_at"),
            RagValidator.aware_datetime(updated_at, "updated_at"),
        )

    def start(self) -> Self:
        if self.status is RagJobStatus.COMPLETED:
            return self
        return replace(self, status=RagJobStatus.RUNNING, error=None, updated_at=datetime.now(UTC))

    def advance(self, processed_count: int) -> Self:
        if not self.processed_count <= processed_count <= self.total_count:
            raise ValidationError("RAG job progress cannot move backwards or exceed total")
        status = (
            RagJobStatus.COMPLETED if processed_count == self.total_count else RagJobStatus.QUEUED
        )
        return replace(
            self,
            status=status,
            processed_count=processed_count,
            error=None,
            updated_at=datetime.now(UTC),
        )

    def fail(self, error: str) -> Self:
        return replace(
            self,
            status=RagJobStatus.FAILED,
            error=RagValidator.text(error, "RAG job error", 2_000),
            updated_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "kind": self.kind.value,
            "status": self.status.value,
            "idempotency_key": self.idempotency_key,
            "input_digest": self.input_digest,
            "payload": self.payload,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "batch_size": self.batch_size,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RagSearchCandidate:
    document: RagDocument
    chunk: RagChunk
    score: Decimal


@dataclass(frozen=True, slots=True)
class RagSearchResult:
    candidates: tuple[RagSearchCandidate, ...]
    filtered_document_count: int


@dataclass(frozen=True, slots=True)
class RagDocumentPage:
    items: tuple[RagDocument, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class RagAnswerPage:
    items: tuple[RagAnswer, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class RagJobPage:
    items: tuple[RagTransferJob, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class RagSyncResult:
    imported: int
    updated: int
    unchanged: int
    deactivated: int

    def as_dict(self) -> dict[str, object]:
        return {
            "imported": self.imported,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "deactivated": self.deactivated,
        }


@dataclass(frozen=True, slots=True)
class RagArtifact:
    filename: str
    content_type: str
    content: bytes
    sha256: str

    @classmethod
    def create(cls, filename: str, content_type: str, content: bytes) -> Self:
        if not content:
            raise ValidationError("RAG artifact cannot be empty")
        return cls(
            RagValidator.text(filename, "RAG artifact filename", 255),
            RagValidator.text(content_type, "RAG artifact content type", 255),
            bytes(content),
            hashlib.sha256(content).hexdigest(),
        )
