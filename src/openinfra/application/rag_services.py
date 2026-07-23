from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from openinfra.application.ports import (
    AuditRepository,
    RagGeneratorPort,
    RagRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.application.source_of_truth_services import ListSourceObjectsCommand
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    DomainEvent,
    NotFoundError,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.domain.rag import (
    RagAnswer,
    RagAnswerPage,
    RagAnswerStatus,
    RagArtifact,
    RagCitation,
    RagDocument,
    RagDocumentPage,
    RagJobKind,
    RagJobPage,
    RagJobStatus,
    RagSyncResult,
    RagTextProcessor,
    RagTransferJob,
    RagValidator,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class UpsertRagDocumentCommand:
    tenant_id: str
    admin_token: str
    source_type: str
    source_ref: str
    title: str
    content: str
    required_permissions: tuple[str, ...] = (Permission.RAG_READ.value,)
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None
    source_uri: str | None = None
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetRagDocumentCommand:
    tenant_id: str
    admin_token: str
    document_id: str


@dataclass(frozen=True, slots=True)
class ListRagDocumentsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    source_type: str | None = None
    active: bool | None = None


@dataclass(frozen=True, slots=True)
class DeactivateRagDocumentCommand:
    tenant_id: str
    admin_token: str
    document_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class SyncRsotRagCommand:
    tenant_id: str
    admin_token: str
    actor: str | None = None
    max_objects: int = 5_000
    deactivate_missing: bool = False


@dataclass(frozen=True, slots=True)
class AskRagCommand:
    tenant_id: str
    admin_token: str
    question: str
    limit: int = 6
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetRagAnswerCommand:
    tenant_id: str
    admin_token: str
    answer_id: str


@dataclass(frozen=True, slots=True)
class ListRagAnswersCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class CreateRagJobCommand:
    tenant_id: str
    admin_token: str
    kind: str
    idempotency_key: str
    payload: dict[str, Any]
    batch_size: int = 100
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class RunRagJobCommand:
    tenant_id: str
    admin_token: str
    job_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetRagJobCommand:
    tenant_id: str
    admin_token: str
    job_id: str


@dataclass(frozen=True, slots=True)
class ListRagJobsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class GetRagArtifactCommand:
    tenant_id: str
    admin_token: str
    job_id: str


class RagService:
    _MAX_QUERY_CITATIONS = 10
    _MAX_RSOT_OBJECTS = 10_000

    def __init__(
        self,
        repository: RagRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        source_of_truth_service: Any,
        generator: RagGeneratorPort,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._source_of_truth_service = source_of_truth_service
        self._generator = generator

    def upsert_document(self, command: UpsertRagDocumentCommand) -> RagDocument:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_WRITE
        )
        return self._upsert_document(
            tenant_id,
            principal,
            command.source_type,
            command.source_ref,
            command.title,
            command.content,
            command.required_permissions,
            command.tags,
            command.metadata or {},
            command.source_uri,
            command.actor,
        )

    def get_document(self, command: GetRagDocumentCommand) -> RagDocument:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_READ
        )
        document = self._repository.get_document(tenant_id, command.document_id)
        if document is None or not self._can_read(document, principal):
            raise NotFoundError("RAG document not found")
        return document

    def list_documents(self, command: ListRagDocumentsCommand) -> RagDocumentPage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_READ
        )
        requested = Pagination.from_values(command.limit, command.cursor)
        page = self._repository.list_documents(
            tenant_id,
            Pagination.from_values(
                min(500, max(requested.limit * 5, requested.limit)),
                command.cursor,
            ),
            command.source_type,
            command.active,
        )
        visible = tuple(item for item in page.items if self._can_read(item, principal))
        return RagDocumentPage(visible[: requested.limit], page.next_cursor)

    def deactivate_document(self, command: DeactivateRagDocumentCommand) -> RagDocument:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_WRITE
        )
        document = self._repository.get_document(tenant_id, command.document_id)
        if document is None:
            raise NotFoundError("RAG document not found")
        deactivated = document.deactivate()
        self._save_document_with_audit(
            deactivated,
            command.actor or principal.subject,
            "rag.document.deactivated",
            {"source_type": deactivated.source_type.value, "source_ref": deactivated.source_ref},
        )
        return deactivated

    def sync_rsot(self, command: SyncRsotRagCommand) -> RagSyncResult:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_IMPORT
        )
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.RSOT_READ)
        )
        maximum = int(command.max_objects)
        if not 1 <= maximum <= self._MAX_RSOT_OBJECTS:
            raise ValidationError(
                "RAG RSOT synchronization max_objects must be between 1 and "
                f"{self._MAX_RSOT_OBJECTS}"
            )
        imported = 0
        updated = 0
        unchanged = 0
        seen: set[str] = set()
        cursor: str | None = None
        while imported + updated + unchanged < maximum:
            remaining = maximum - imported - updated - unchanged
            page = self._source_of_truth_service.list_objects(
                ListSourceObjectsCommand(
                    tenant_id=tenant_id.value,
                    admin_token=command.admin_token,
                    limit=min(500, remaining),
                    cursor=cursor,
                )
            )
            for source_object in page.items:
                row = source_object.as_dict()
                source_ref = str(row["key"])
                seen.add(source_ref)
                existing = self._repository.find_active_document(tenant_id, "rsot", source_ref)
                result = self._upsert_document(
                    tenant_id,
                    principal,
                    "rsot",
                    source_ref,
                    str(row["display_name"]),
                    json.dumps(row, sort_keys=True, ensure_ascii=False, indent=2),
                    (Permission.RSOT_READ.value,),
                    tuple(str(item) for item in row.get("tags", [])),
                    {
                        "kind": row.get("kind"),
                        "resource_category": row.get("resource_category"),
                        "resource_type": row.get("resource_type"),
                        "source": row.get("source"),
                        "rsot_version": row.get("version"),
                    },
                    f"openinfra:rsot/{source_ref}",
                    command.actor,
                )
                if existing is None:
                    imported += 1
                elif result.id == existing.id:
                    unchanged += 1
                else:
                    updated += 1
            cursor = page.next_cursor
            if cursor is None or not page.items:
                break
        deactivated = 0
        if command.deactivate_missing and cursor is None:
            deactivated = self._deactivate_missing_rsot(tenant_id, principal, seen, command.actor)
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or principal.subject,
                    "rag.rsot.synchronized",
                    "rag_index",
                    tenant_id.value,
                    {
                        "imported": imported,
                        "updated": updated,
                        "unchanged": unchanged,
                        "deactivated": deactivated,
                    },
                )
            )
            unit_of_work.commit()
        return RagSyncResult(imported, updated, unchanged, deactivated)

    def ask(self, command: AskRagCommand) -> RagAnswer:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_QUERY
        )
        question = RagValidator.question(command.question)
        if not RagTextProcessor.terms(question):
            raise ValidationError("RAG question must contain at least one searchable term")
        limit = int(command.limit)
        if not 1 <= limit <= self._MAX_QUERY_CITATIONS:
            raise ValidationError(
                f"RAG citation limit must be between 1 and {self._MAX_QUERY_CITATIONS}"
            )
        search = self._repository.search(
            tenant_id,
            question,
            frozenset(permission.value for permission in principal.permissions),
            limit,
        )
        citations = tuple(
            RagCitation.create(item.document, item.chunk, item.score)
            for item in search.candidates[:limit]
            if item.score > 0
        )
        if citations:
            status = RagAnswerStatus.ANSWERED
            confidence = self._confidence(citations)
        else:
            status = RagAnswerStatus.INSUFFICIENT_CONTEXT
            confidence = Decimal("0")
        answer_text = self._generator.generate(question, citations)
        answer = RagAnswer.create(
            tenant_id,
            question,
            answer_text,
            status,
            confidence,
            citations,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_answer(answer)
            event = DomainEvent.create(
                tenant_id,
                answer.id,
                "rag.query.completed",
                {
                    "answer_id": answer.id.value,
                    "question_hash": answer.question_hash,
                    "status": answer.status.value,
                    "citation_count": len(answer.citations),
                    "confidence": str(answer.confidence),
                    "source_object_count": len(answer.source_object_citations()),
                    "source_data_mutation_performed": False,
                    "change_validation_required": True,
                },
            )
            self._repository.append_event(event)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or principal.subject,
                    "rag.query.completed",
                    "rag_answer",
                    answer.id.value,
                    {
                        "question_hash": answer.question_hash,
                        "question_length": len(question),
                        "citation_count": len(answer.citations),
                        "status": answer.status.value,
                        "confidence": str(answer.confidence),
                        "source_object_count": len(answer.source_object_citations()),
                        "source_data_mutation_performed": False,
                        "change_validation_required": True,
                        "permission_filtered_documents": search.filtered_document_count,
                    },
                )
            )
            unit_of_work.commit()
        return answer

    def get_answer(self, command: GetRagAnswerCommand) -> RagAnswer:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.RAG_READ)
        answer = self._repository.get_answer(tenant_id, command.answer_id)
        if answer is None:
            raise NotFoundError("RAG answer not found")
        return answer

    def list_answers(self, command: ListRagAnswersCommand) -> RagAnswerPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.RAG_READ)
        return self._repository.list_answers(
            tenant_id, Pagination.from_values(command.limit, command.cursor)
        )

    def create_job(self, command: CreateRagJobCommand) -> RagTransferJob:
        kind = RagJobKind.from_value(command.kind)
        permission = (
            Permission.RAG_IMPORT if kind is RagJobKind.DOCUMENT_IMPORT else Permission.RAG_EXPORT
        )
        tenant_id, principal = self._authorize(command.tenant_id, command.admin_token, permission)
        payload, total = self._validate_job_payload(kind, command.payload)
        candidate = RagTransferJob.create(
            tenant_id,
            kind.value,
            command.idempotency_key,
            payload,
            total,
            command.batch_size,
        )
        existing = self._repository.find_job_by_idempotency_key(
            tenant_id, candidate.idempotency_key
        )
        if existing is not None:
            if existing.input_digest == candidate.input_digest and existing.kind is candidate.kind:
                return existing
            raise ConflictError("RAG job idempotency key already exists with another payload")
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_job(candidate)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    candidate.id,
                    "rag.job.created",
                    {
                        "kind": candidate.kind.value,
                        "total_count": candidate.total_count,
                        "input_digest": candidate.input_digest,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or principal.subject,
                    "rag.job.created",
                    "rag_job",
                    candidate.id.value,
                    {
                        "kind": candidate.kind.value,
                        "total_count": candidate.total_count,
                    },
                )
            )
            unit_of_work.commit()
        return candidate

    def run_job(self, command: RunRagJobCommand) -> RagTransferJob:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_READ
        )
        job = self._repository.get_job(tenant_id, command.job_id)
        if job is None:
            raise NotFoundError("RAG job not found")
        required = (
            Permission.RAG_IMPORT
            if job.kind is RagJobKind.DOCUMENT_IMPORT
            else Permission.RAG_EXPORT
        )
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, required)
        )
        if job.status is RagJobStatus.COMPLETED:
            return job
        running = job.start()
        self._repository.save_job(running)
        try:
            completed = (
                self._run_import_job(running, principal, command.actor)
                if running.kind is RagJobKind.DOCUMENT_IMPORT
                else self._run_export_job(running)
            )
        except Exception as exc:
            failed = running.fail(str(exc))
            self._save_job_result(failed, principal, command.actor, "rag.job.failed")
            raise
        self._save_job_result(completed, principal, command.actor, "rag.job.progressed")
        return completed

    def get_job(self, command: GetRagJobCommand) -> RagTransferJob:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.RAG_READ)
        job = self._repository.get_job(tenant_id, command.job_id)
        if job is None:
            raise NotFoundError("RAG job not found")
        return job

    def list_jobs(self, command: ListRagJobsCommand) -> RagJobPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.RAG_READ)
        return self._repository.list_jobs(
            tenant_id, Pagination.from_values(command.limit, command.cursor)
        )

    def get_artifact(self, command: GetRagArtifactCommand) -> RagArtifact:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.RAG_EXPORT
        )
        job = self._repository.get_job(tenant_id, command.job_id)
        if job is None:
            raise NotFoundError("RAG job not found")
        if job.kind is not RagJobKind.ANSWER_EXPORT or job.status is not RagJobStatus.COMPLETED:
            raise ValidationError("RAG export artifact is not available")
        artifact = self._repository.get_artifact(tenant_id, job.id.value)
        if artifact is None:
            raise NotFoundError("RAG export artifact not found")
        return artifact

    def _upsert_document(
        self,
        tenant_id: TenantId,
        principal: AuthenticatedPrincipal,
        source_type: str,
        source_ref: str,
        title: str,
        content: str,
        required_permissions: tuple[str, ...],
        tags: tuple[str, ...],
        metadata: dict[str, Any],
        source_uri: str | None,
        actor: str | None,
    ) -> RagDocument:
        existing = self._repository.find_active_document(tenant_id, source_type, source_ref)
        version = 1 if existing is None else existing.version + 1
        candidate = RagDocument.create(
            tenant_id,
            source_type,
            source_ref,
            title,
            content,
            required_permissions,
            tags,
            metadata,
            source_uri,
            version,
        )
        if existing is not None and self._same_document(existing, candidate):
            return existing
        with self._transaction_manager.begin() as unit_of_work:
            if existing is not None:
                self._repository.save_document(existing.deactivate())
            self._repository.save_document(candidate)
            event = DomainEvent.create(
                tenant_id,
                candidate.id,
                "rag.document.indexed",
                {
                    "source_type": candidate.source_type.value,
                    "source_ref": candidate.source_ref,
                    "version": candidate.version,
                    "checksum": candidate.checksum,
                    "chunk_count": len(candidate.chunks),
                },
            )
            self._repository.append_event(event)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    actor or principal.subject,
                    "rag.document.indexed",
                    "rag_document",
                    candidate.id.value,
                    event.payload,
                )
            )
            unit_of_work.commit()
        return candidate

    def _deactivate_missing_rsot(
        self,
        tenant_id: TenantId,
        principal: AuthenticatedPrincipal,
        seen: set[str],
        actor: str | None,
    ) -> int:
        cursor: str | None = None
        deactivated = 0
        while True:
            page = self._repository.list_documents(
                tenant_id,
                Pagination.from_values(500, cursor),
                source_type="rsot",
                active=True,
            )
            for document in page.items:
                if document.source_ref not in seen:
                    self._save_document_with_audit(
                        document.deactivate(),
                        actor or principal.subject,
                        "rag.document.deactivated",
                        {"reason": "missing-from-rsot"},
                    )
                    deactivated += 1
            cursor = page.next_cursor
            if cursor is None:
                return deactivated

    def _save_document_with_audit(
        self,
        document: RagDocument,
        actor: str,
        action: str,
        metadata: dict[str, Any],
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_document(document)
            self._repository.append_event(
                DomainEvent.create(document.tenant_id, document.id, action, metadata)
            )
            self._audit_repository.append(
                AuditEvent.record(
                    document.tenant_id,
                    actor,
                    action,
                    "rag_document",
                    document.id.value,
                    metadata,
                )
            )
            unit_of_work.commit()

    def _run_import_job(
        self,
        job: RagTransferJob,
        principal: AuthenticatedPrincipal,
        actor: str | None,
    ) -> RagTransferJob:
        raw_documents = job.payload.get("documents")
        if not isinstance(raw_documents, list):
            raise ValidationError("RAG document import job requires a documents array")
        end = min(job.processed_count + job.batch_size, job.total_count)
        for raw in raw_documents[job.processed_count : end]:
            if not isinstance(raw, dict):
                raise ValidationError("RAG import document must be a JSON object")
            self._upsert_document(
                job.tenant_id,
                principal,
                str(raw.get("source_type", "documentation")),
                str(raw.get("source_ref", "")),
                str(raw.get("title", "")),
                str(raw.get("content", "")),
                tuple(str(item) for item in raw.get("required_permissions", ["rag.read"])),
                tuple(str(item) for item in raw.get("tags", [])),
                self._mapping(raw.get("metadata", {}), "RAG import metadata"),
                None if raw.get("source_uri") is None else str(raw["source_uri"]),
                actor,
            )
        return job.advance(end)

    def _run_export_job(self, job: RagTransferJob) -> RagTransferJob:
        raw_ids = job.payload.get("answer_ids", [])
        if not isinstance(raw_ids, list):
            raise ValidationError("RAG export answer_ids must be an array")
        answers: list[RagAnswer] = []
        if raw_ids:
            for answer_id in raw_ids:
                answer = self._repository.get_answer(job.tenant_id, str(answer_id))
                if answer is None:
                    raise NotFoundError(f"RAG answer not found: {answer_id}")
                answers.append(answer)
        else:
            cursor: str | None = None
            while len(answers) < 10_000:
                page = self._repository.list_answers(
                    job.tenant_id, Pagination.from_values(500, cursor)
                )
                answers.extend(page.items)
                cursor = page.next_cursor
                if cursor is None:
                    break
        export_format = str(job.payload.get("format", "json")).strip().lower()
        artifact = self._render_answers(answers, export_format, job.id.value)
        self._repository.save_artifact(job.tenant_id, job.id.value, artifact)
        return job.advance(job.total_count)

    def _save_job_result(
        self,
        job: RagTransferJob,
        principal: AuthenticatedPrincipal,
        actor: str | None,
        event_name: str,
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_job(job)
            self._repository.append_event(
                DomainEvent.create(
                    job.tenant_id,
                    job.id,
                    event_name,
                    {
                        "kind": job.kind.value,
                        "status": job.status.value,
                        "processed_count": job.processed_count,
                        "total_count": job.total_count,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    job.tenant_id,
                    actor or principal.subject,
                    event_name,
                    "rag_job",
                    job.id.value,
                    {
                        "kind": job.kind.value,
                        "status": job.status.value,
                        "processed_count": job.processed_count,
                        "total_count": job.total_count,
                    },
                )
            )
            unit_of_work.commit()

    @staticmethod
    def _render_answers(answers: list[RagAnswer], export_format: str, job_id: str) -> RagArtifact:
        if export_format == "json":
            content = json.dumps(
                {"answers": [item.as_dict() for item in answers]},
                sort_keys=True,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            return RagArtifact.create(
                f"openinfra-rag-answers-{job_id}.json", "application/json", content
            )
        if export_format == "csv":
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "answer_id",
                    "question_hash",
                    "status",
                    "confidence",
                    "question",
                    "answer",
                    "citation_count",
                    "generated_at",
                ]
            )
            for item in answers:
                writer.writerow(
                    [
                        item.id.value,
                        item.question_hash,
                        item.status.value,
                        str(item.confidence),
                        item.question,
                        item.answer,
                        len(item.citations),
                        item.generated_at.isoformat(),
                    ]
                )
            return RagArtifact.create(
                f"openinfra-rag-answers-{job_id}.csv",
                "text/csv; charset=utf-8",
                stream.getvalue().encode("utf-8"),
            )
        raise ValidationError("RAG export format must be json or csv")

    @staticmethod
    def _validate_job_payload(
        kind: RagJobKind, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        normalized = RagValidator.json_object(payload, "RAG job payload", maximum_bytes=5_242_880)
        if kind is RagJobKind.DOCUMENT_IMPORT:
            documents = normalized.get("documents")
            if not isinstance(documents, list) or not 1 <= len(documents) <= 10_000:
                raise ValidationError("RAG import job requires 1 to 10000 documents")
            if any(not isinstance(item, dict) for item in documents):
                raise ValidationError("RAG import documents must be JSON objects")
            return normalized, len(documents)
        export_format = str(normalized.get("format", "json")).strip().lower()
        if export_format not in {"json", "csv"}:
            raise ValidationError("RAG export format must be json or csv")
        answer_ids = normalized.get("answer_ids", [])
        if not isinstance(answer_ids, list) or len(answer_ids) > 10_000:
            raise ValidationError("RAG export answer_ids must be an array of at most 10000 items")
        normalized["format"] = export_format
        normalized["answer_ids"] = [str(item) for item in answer_ids]
        return normalized, 1

    @staticmethod
    def _mapping(value: object, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def _same_document(left: RagDocument, right: RagDocument) -> bool:
        return (
            left.source_type is right.source_type
            and left.source_ref == right.source_ref
            and left.source_uri == right.source_uri
            and left.title == right.title
            and left.content == right.content
            and left.required_permissions == right.required_permissions
            and left.tags == right.tags
            and left.metadata == right.metadata
        )

    @staticmethod
    def _can_read(document: RagDocument, principal: AuthenticatedPrincipal) -> bool:
        permissions = {permission.value for permission in principal.permissions}
        return set(document.required_permissions).issubset(permissions)

    @staticmethod
    def _confidence(citations: tuple[RagCitation, ...]) -> Decimal:
        top = citations[0].score
        density = min(Decimal("0.25"), Decimal(len(citations)) * Decimal("0.04"))
        confidence = (top / (top + Decimal("2"))) + density
        return min(Decimal("0.99"), confidence.quantize(Decimal("0.0001")))

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized.value, token, permission)
        )
        return normalized, principal
