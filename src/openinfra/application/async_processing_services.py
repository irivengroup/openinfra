from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from openinfra.application.ports import (
    ArtifactStore,
    AsyncJobPage,
    AsyncProcessingRepository,
    AuditRepository,
    OutboxEventPage,
    OutboxPublisher,
    RuntimeTelemetry,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.application.telemetry import NullRuntimeTelemetry
from openinfra.domain.async_processing import (
    ArtifactReference,
    AsyncJob,
    OutboxEvent,
    WorkerSpecialization,
    WorkStatus,
)
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class SubmitAsyncJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    specialization: str
    operation: str
    idempotency_key: str
    payload: dict[str, Any]
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class StoreAsyncArtifactCommand:
    tenant_id: str
    admin_token: str
    actor: str
    purpose: str
    content: bytes
    media_type: str


@dataclass(frozen=True, slots=True)
class GetAsyncJobCommand:
    tenant_id: str
    admin_token: str
    job_id: str


@dataclass(frozen=True, slots=True)
class ListAsyncJobsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None
    specialization: str | None = None


@dataclass(frozen=True, slots=True)
class ClaimAsyncJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    specialization: str
    worker_id: str
    lease_seconds: int = 60


@dataclass(frozen=True, slots=True)
class RenewAsyncJobLeaseCommand:
    tenant_id: str
    admin_token: str
    actor: str
    job_id: str
    worker_id: str
    lease_token: int
    lease_seconds: int = 60


@dataclass(frozen=True, slots=True)
class CompleteAsyncJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    job_id: str
    worker_id: str
    lease_token: int
    result: bytes
    media_type: str = "application/json"


@dataclass(frozen=True, slots=True)
class FailAsyncJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    job_id: str
    worker_id: str
    lease_token: int
    error: str
    retry_delay_seconds: int = 30


@dataclass(frozen=True, slots=True)
class ReplayAsyncJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    job_id: str


@dataclass(frozen=True, slots=True)
class GetAsyncArtifactCommand:
    tenant_id: str
    admin_token: str
    job_id: str
    kind: str = "result"


@dataclass(frozen=True, slots=True)
class ListOutboxEventsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class GetOutboxEventCommand:
    tenant_id: str
    admin_token: str
    event_id: str


@dataclass(frozen=True, slots=True)
class ClaimOutboxEventCommand:
    tenant_id: str
    admin_token: str
    actor: str
    worker_id: str
    lease_seconds: int = 60


@dataclass(frozen=True, slots=True)
class RenewOutboxLeaseCommand:
    tenant_id: str
    admin_token: str
    actor: str
    event_id: str
    worker_id: str
    lease_token: int
    lease_seconds: int = 60


@dataclass(frozen=True, slots=True)
class PublishOutboxEventCommand:
    tenant_id: str
    admin_token: str
    actor: str
    event_id: str
    worker_id: str
    lease_token: int


@dataclass(frozen=True, slots=True)
class FailOutboxEventCommand:
    tenant_id: str
    admin_token: str
    actor: str
    event_id: str
    worker_id: str
    lease_token: int
    error: str
    retry_delay_seconds: int = 30


@dataclass(frozen=True, slots=True)
class ReplayOutboxEventCommand:
    tenant_id: str
    admin_token: str
    actor: str
    event_id: str


@dataclass(frozen=True, slots=True)
class GetAsyncQueueMetricsCommand:
    tenant_id: str
    admin_token: str


@dataclass(frozen=True, slots=True)
class ArtifactContent:
    reference: ArtifactReference
    content: bytes


class AsyncProcessingService:
    def __init__(
        self,
        repository: AsyncProcessingRepository,
        artifact_store: ArtifactStore,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._artifact_store = artifact_store
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def submit_job(self, command: SubmitAsyncJobCommand) -> AsyncJob:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_SUBMIT
        )
        specialization = WorkerSpecialization.from_value(command.specialization)
        self._validate_supported_operation(specialization, command.operation)
        payload = self._canonical_json(command.payload)
        payload_artifact = self._artifact_store.write(
            tenant_id, "async-payload", payload, "application/json"
        )
        with self._transaction_manager.begin() as unit:
            self._repository.lock_job_idempotency(tenant_id, command.idempotency_key)
            existing = self._repository.find_job_by_idempotency_key(
                tenant_id, command.idempotency_key
            )
            if existing is not None:
                if (
                    existing.specialization is specialization
                    and existing.operation == command.operation.strip().lower()
                    and existing.payload_artifact.sha256 == payload_artifact.sha256
                ):
                    unit.commit()
                    return existing
                raise ConflictError("async job idempotency key conflicts with existing request")
            job = AsyncJob.create(
                tenant_id=tenant_id,
                specialization=specialization,
                operation=command.operation,
                idempotency_key=command.idempotency_key,
                payload_artifact=payload_artifact,
                max_attempts=command.max_attempts,
                requested_by=actor,
            )
            self._repository.save_job(job)
            self._repository.save_outbox_event(
                self._job_event(job, "async.job.submitted", "submitted")
            )
            self._audit(
                tenant_id,
                actor,
                "async.job.submitted",
                "async-job",
                job.id.value,
                {
                    "specialization": job.specialization.value,
                    "operation": job.operation,
                    "payload_sha256": job.payload_artifact.sha256,
                },
            )
            unit.commit()
        return job

    def store_artifact(self, command: StoreAsyncArtifactCommand) -> ArtifactReference:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_SUBMIT
        )
        artifact = self._artifact_store.write(
            tenant_id, command.purpose, command.content, command.media_type
        )
        with self._transaction_manager.begin() as unit:
            self._audit(
                tenant_id,
                actor,
                "async.artifact.stored",
                "async-artifact",
                artifact.sha256,
                {
                    "purpose": command.purpose,
                    "object_key": artifact.object_key,
                    "media_type": artifact.media_type,
                    "size_bytes": artifact.size_bytes,
                },
            )
            unit.commit()
        return artifact

    def get_job(self, command: GetAsyncJobCommand) -> AsyncJob:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, "reader", Permission.ASYNC_READ
        )
        with self._transaction_manager.begin() as unit:
            job = self._require_job(tenant_id, command.job_id)
            unit.commit()
        return job

    def list_jobs(self, command: ListAsyncJobsCommand) -> AsyncJobPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, "reader", Permission.ASYNC_READ
        )
        status = None if command.status is None else WorkStatus.from_value(command.status)
        specialization = (
            None
            if command.specialization is None
            else WorkerSpecialization.from_value(command.specialization)
        )
        with self._transaction_manager.begin() as unit:
            page = self._repository.list_jobs(
                tenant_id,
                Pagination.from_values(command.limit, command.cursor),
                status,
                specialization,
            )
            unit.commit()
        return page

    def claim_job(self, command: ClaimAsyncJobCommand) -> AsyncJob | None:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        specialization = WorkerSpecialization.from_value(command.specialization)
        with self._transaction_manager.begin() as unit:
            job = self._repository.claim_next_job(
                tenant_id,
                specialization,
                command.worker_id,
                command.lease_seconds,
                datetime.now(UTC),
            )
            if job is not None:
                self._audit(
                    tenant_id,
                    actor,
                    "async.job.claimed",
                    "async-job",
                    job.id.value,
                    {
                        "worker_id": command.worker_id,
                        "lease_token": job.state.lease_token,
                        "attempt_count": job.state.attempt_count,
                    },
                )
            unit.commit()
        return job

    def renew_job_lease(self, command: RenewAsyncJobLeaseCommand) -> AsyncJob:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_job(tenant_id, command.job_id)
            renewed = current.renew(
                command.worker_id,
                command.lease_token,
                command.lease_seconds,
            )
            self._repository.save_job(renewed)
            self._audit(
                tenant_id,
                actor,
                "async.job.lease-renewed",
                "async-job",
                renewed.id.value,
                {"worker_id": command.worker_id, "lease_token": command.lease_token},
            )
            unit.commit()
        return renewed

    def complete_job(self, command: CompleteAsyncJobCommand) -> AsyncJob:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        artifact = self._artifact_store.write(
            tenant_id, "async-result", command.result, command.media_type
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_job(tenant_id, command.job_id)
            completed = current.complete(
                command.worker_id,
                command.lease_token,
                artifact,
            )
            self._repository.save_job(completed)
            self._repository.save_outbox_event(
                self._job_event(completed, "async.job.completed", "completed")
            )
            self._audit(
                tenant_id,
                actor,
                "async.job.completed",
                "async-job",
                completed.id.value,
                {
                    "worker_id": command.worker_id,
                    "lease_token": command.lease_token,
                    "result_sha256": artifact.sha256,
                    "result_size_bytes": artifact.size_bytes,
                },
            )
            unit.commit()
        return completed

    def fail_job(self, command: FailAsyncJobCommand) -> AsyncJob:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_job(tenant_id, command.job_id)
            failed = current.fail(
                command.worker_id,
                command.lease_token,
                command.error,
                command.retry_delay_seconds,
            )
            self._repository.save_job(failed)
            event_name = (
                "async.job.dead-lettered"
                if failed.state.status is WorkStatus.DEAD_LETTER
                else "async.job.retry-scheduled"
            )
            self._repository.save_outbox_event(
                self._job_event(failed, event_name, failed.state.status.value)
            )
            self._audit(
                tenant_id,
                actor,
                event_name,
                "async-job",
                failed.id.value,
                {
                    "worker_id": command.worker_id,
                    "lease_token": command.lease_token,
                    "attempt_count": failed.state.attempt_count,
                    "error": failed.state.last_error,
                },
                (
                    Severity.ERROR
                    if failed.state.status is WorkStatus.DEAD_LETTER
                    else Severity.WARNING
                ),
            )
            unit.commit()
        return failed

    def replay_job(self, command: ReplayAsyncJobCommand) -> AsyncJob:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_ADMIN
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_job(tenant_id, command.job_id)
            replayed = current.replay()
            self._repository.save_job(replayed)
            self._repository.save_outbox_event(
                self._job_event(replayed, "async.job.replayed", "replayed")
            )
            self._audit(
                tenant_id,
                actor,
                "async.job.replayed",
                "async-job",
                replayed.id.value,
                {"lease_token": replayed.state.lease_token},
            )
            unit.commit()
        return replayed

    def get_artifact(self, command: GetAsyncArtifactCommand) -> ArtifactContent:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, "reader", Permission.ASYNC_READ
        )
        with self._transaction_manager.begin() as unit:
            job = self._require_job(tenant_id, command.job_id)
            unit.commit()
        kind = command.kind.strip().lower()
        if kind == "payload":
            reference = job.payload_artifact
        elif kind == "result":
            if job.result_artifact is None:
                raise NotFoundError("async job result artifact is not available")
            reference = job.result_artifact
        else:
            raise ValidationError("artifact kind must be payload or result")
        return ArtifactContent(reference, self._artifact_store.read(tenant_id, reference))

    def list_outbox_events(self, command: ListOutboxEventsCommand) -> OutboxEventPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, "reader", Permission.ASYNC_READ
        )
        status = None if command.status is None else WorkStatus.from_value(command.status)
        with self._transaction_manager.begin() as unit:
            page = self._repository.list_outbox_events(
                tenant_id, Pagination.from_values(command.limit, command.cursor), status
            )
            unit.commit()
        return page

    def get_outbox_event(self, command: GetOutboxEventCommand) -> OutboxEvent:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, "reader", Permission.ASYNC_READ
        )
        with self._transaction_manager.begin() as unit:
            event = self._require_outbox_event(tenant_id, command.event_id)
            unit.commit()
        return event

    def claim_outbox_event(self, command: ClaimOutboxEventCommand) -> OutboxEvent | None:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        with self._transaction_manager.begin() as unit:
            event = self._repository.claim_next_outbox_event(
                tenant_id, command.worker_id, command.lease_seconds, datetime.now(UTC)
            )
            if event is not None:
                self._audit(
                    tenant_id,
                    actor,
                    "async.outbox.claimed",
                    "outbox-event",
                    event.id.value,
                    {
                        "worker_id": command.worker_id,
                        "lease_token": event.state.lease_token,
                    },
                )
            unit.commit()
        return event

    def renew_outbox_lease(self, command: RenewOutboxLeaseCommand) -> OutboxEvent:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_outbox_event(tenant_id, command.event_id)
            renewed = current.renew(command.worker_id, command.lease_token, command.lease_seconds)
            self._repository.save_outbox_event(renewed)
            self._audit(
                tenant_id,
                actor,
                "async.outbox.lease-renewed",
                "outbox-event",
                renewed.id.value,
                {"worker_id": command.worker_id, "lease_token": command.lease_token},
            )
            unit.commit()
        return renewed

    def mark_outbox_published(self, command: PublishOutboxEventCommand) -> OutboxEvent:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_outbox_event(tenant_id, command.event_id)
            published = current.mark_published(command.worker_id, command.lease_token)
            self._repository.save_outbox_event(published)
            self._audit(
                tenant_id,
                actor,
                "async.outbox.published",
                "outbox-event",
                published.id.value,
                {
                    "worker_id": command.worker_id,
                    "lease_token": command.lease_token,
                    "event_name": published.event_name,
                },
            )
            unit.commit()
        return published

    def fail_outbox_event(self, command: FailOutboxEventCommand) -> OutboxEvent:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_WORKER
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_outbox_event(tenant_id, command.event_id)
            failed = current.fail(
                command.worker_id,
                command.lease_token,
                command.error,
                command.retry_delay_seconds,
            )
            self._repository.save_outbox_event(failed)
            self._audit(
                tenant_id,
                actor,
                "async.outbox.dead-lettered"
                if failed.state.status is WorkStatus.DEAD_LETTER
                else "async.outbox.retry-scheduled",
                "outbox-event",
                failed.id.value,
                {
                    "worker_id": command.worker_id,
                    "lease_token": command.lease_token,
                    "error": failed.state.last_error,
                },
                (
                    Severity.ERROR
                    if failed.state.status is WorkStatus.DEAD_LETTER
                    else Severity.WARNING
                ),
            )
            unit.commit()
        return failed

    def replay_outbox_event(self, command: ReplayOutboxEventCommand) -> OutboxEvent:
        tenant_id, actor = self._authorize(
            command.tenant_id, command.admin_token, command.actor, Permission.ASYNC_ADMIN
        )
        with self._transaction_manager.begin() as unit:
            current = self._require_outbox_event(tenant_id, command.event_id)
            replayed = current.replay()
            self._repository.save_outbox_event(replayed)
            self._audit(
                tenant_id,
                actor,
                "async.outbox.replayed",
                "outbox-event",
                replayed.id.value,
                {"lease_token": replayed.state.lease_token},
            )
            unit.commit()
        return replayed

    def queue_metrics(self, command: GetAsyncQueueMetricsCommand) -> dict[str, object]:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, "reader", Permission.ASYNC_READ
        )
        with self._transaction_manager.begin() as unit:
            metrics = self._repository.queue_metrics(tenant_id)
            unit.commit()
        return metrics

    def _authorize(
        self,
        tenant_value: str,
        token: str,
        actor: str,
        permission: Permission,
    ) -> tuple[TenantId, str]:
        tenant_id = TenantId.from_value(tenant_value)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, token, permission)
        )
        normalized_actor = (
            principal.subject if actor.strip() in {"", "api", "cli", "reader"} else actor
        )
        return tenant_id, normalized_actor

    def _require_job(self, tenant_id: TenantId, job_id: str) -> AsyncJob:
        job = self._repository.get_job(tenant_id, job_id)
        if job is None:
            raise NotFoundError("async job not found")
        return job

    def _require_outbox_event(self, tenant_id: TenantId, event_id: str) -> OutboxEvent:
        event = self._repository.get_outbox_event(tenant_id, event_id)
        if event is None:
            raise NotFoundError("outbox event not found")
        return event

    def _job_event(
        self,
        job: AsyncJob,
        event_name: str,
        transition: str,
    ) -> OutboxEvent:
        result = None if job.result_artifact is None else job.result_artifact.as_dict()
        return OutboxEvent.create(
            tenant_id=job.tenant_id,
            aggregate_type="async-job",
            aggregate_id=job.id.value,
            event_name=event_name,
            idempotency_key=(
                f"job:{job.id.value}:{transition}:{job.state.lease_token}:{job.state.attempt_count}"
            ),
            payload={
                "job_id": job.id.value,
                "specialization": job.specialization.value,
                "operation": job.operation,
                "status": job.state.status.value,
                "attempt_count": job.state.attempt_count,
                "lease_token": job.state.lease_token,
                "payload_artifact": job.payload_artifact.as_dict(),
                "result_artifact": result,
            },
        )

    def _audit(
        self,
        tenant_id: TenantId,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, Any],
        severity: Severity = Severity.INFO,
    ) -> None:
        self._audit_repository.append(
            AuditEvent.record(
                tenant_id,
                actor,
                action,
                target_type,
                target_id,
                metadata,
                severity,
            )
        )

    @staticmethod
    def _canonical_json(payload: dict[str, Any]) -> bytes:
        try:
            return json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValidationError("async job payload must be JSON serializable") from exc

    @staticmethod
    def _validate_supported_operation(specialization: WorkerSpecialization, operation: str) -> None:
        normalized = operation.strip().lower()
        supported = {
            WorkerSpecialization.REPORTING: {"reporting.async-queue-health"},
            WorkerSpecialization.IMPORTS: {"imports.dataset", "imports.bulk-dataset"},
            WorkerSpecialization.GRAPH: {
                "graph.traverse",
                "graph.impact",
                "graph.path",
                "graph.spof",
                "graph.export",
            },
            WorkerSpecialization.RAG: {
                "rag.sync-rsot",
                "rag.document-import",
                "rag.answer-export",
            },
        }
        if normalized not in supported[specialization]:
            raise ValidationError(
                f"operation {normalized or '<empty>'} is not supported by {specialization.value}"
            )


class ReportingWorker:
    def __init__(
        self,
        service: AsyncProcessingService,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self._service = service
        self._telemetry = telemetry or NullRuntimeTelemetry()

    def run_once(
        self,
        *,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
        lease_seconds: int = 60,
        retry_delay_seconds: int = 30,
    ) -> AsyncJob | None:
        started_at = time.perf_counter()
        outcome = "failed"
        self._telemetry.worker_started(WorkerSpecialization.REPORTING.value)
        try:
            claimed = self._service.claim_job(
                ClaimAsyncJobCommand(
                    tenant_id,
                    admin_token,
                    worker_id,
                    WorkerSpecialization.REPORTING.value,
                    worker_id,
                    lease_seconds,
                )
            )
            if claimed is None:
                outcome = "idle"
                return None
            try:
                payload_artifact = self._service.get_artifact(
                    GetAsyncArtifactCommand(tenant_id, admin_token, claimed.id.value, "payload")
                )
                payload = json.loads(payload_artifact.content.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValidationError("reporting job payload must be a JSON object")
                if claimed.operation != "reporting.async-queue-health":
                    raise ValidationError("reporting worker does not support this operation")
                report = {
                    "schema_version": "1.0",
                    "generated_at": datetime.now(UTC).isoformat(),
                    "tenant_id": tenant_id,
                    "job_id": claimed.id.value,
                    "operation": claimed.operation,
                    "request": payload,
                    "queues": self._service.queue_metrics(
                        GetAsyncQueueMetricsCommand(tenant_id, admin_token)
                    ),
                }
                result = json.dumps(
                    report, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
                completed = self._service.complete_job(
                    CompleteAsyncJobCommand(
                        tenant_id,
                        admin_token,
                        worker_id,
                        claimed.id.value,
                        worker_id,
                        claimed.state.lease_token,
                        result,
                    )
                )
                outcome = "completed"
                return completed
            except Exception as exc:
                failed = self._service.fail_job(
                    FailAsyncJobCommand(
                        tenant_id,
                        admin_token,
                        worker_id,
                        claimed.id.value,
                        worker_id,
                        claimed.state.lease_token,
                        str(exc),
                        retry_delay_seconds,
                    )
                )
                outcome = (
                    "dead-letter" if failed.state.status is WorkStatus.DEAD_LETTER else "retry"
                )
                return failed
        finally:
            self._telemetry.worker_finished(
                WorkerSpecialization.REPORTING.value,
                outcome,
                max(0.0, time.perf_counter() - started_at),
            )


class OutboxDispatcher:
    def __init__(
        self,
        service: AsyncProcessingService,
        publisher: OutboxPublisher,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self._service = service
        self._publisher = publisher
        self._telemetry = telemetry or NullRuntimeTelemetry()

    def run_once(
        self,
        *,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
        lease_seconds: int = 60,
        retry_delay_seconds: int = 30,
    ) -> OutboxEvent | None:
        started_at = time.perf_counter()
        outcome = "failed"
        try:
            claimed = self._service.claim_outbox_event(
                ClaimOutboxEventCommand(
                    tenant_id,
                    admin_token,
                    worker_id,
                    worker_id,
                    lease_seconds,
                )
            )
            if claimed is None:
                outcome = "idle"
                return None
            try:
                self._publisher.publish(claimed)
                published = self._service.mark_outbox_published(
                    PublishOutboxEventCommand(
                        tenant_id,
                        admin_token,
                        worker_id,
                        claimed.id.value,
                        worker_id,
                        claimed.state.lease_token,
                    )
                )
                outcome = "published"
                return published
            except Exception as exc:
                failed = self._service.fail_outbox_event(
                    FailOutboxEventCommand(
                        tenant_id,
                        admin_token,
                        worker_id,
                        claimed.id.value,
                        worker_id,
                        claimed.state.lease_token,
                        str(exc),
                        retry_delay_seconds,
                    )
                )
                outcome = (
                    "dead-letter" if failed.state.status is WorkStatus.DEAD_LETTER else "retry"
                )
                return failed
        finally:
            self._telemetry.outbox_dispatch_finished(
                outcome, max(0.0, time.perf_counter() - started_at)
            )
