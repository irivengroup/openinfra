from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import ConflictError, EntityId, TenantId, ValidationError


class WorkStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RETRY_WAIT = "retry-wait"
    COMPLETED = "completed"
    DEAD_LETTER = "dead-letter"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("asynchronous work status is invalid") from exc


class WorkerSpecialization(StrEnum):
    REPORTING = "reporting"
    IMPORTS = "imports"
    GRAPH = "graph"
    RAG = "rag"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("worker specialization is invalid") from exc


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    object_key: str
    sha256: str
    size_bytes: int
    media_type: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        object_key: str,
        sha256: str,
        size_bytes: int,
        media_type: str,
        created_at: datetime | None = None,
    ) -> Self:
        normalized_key = object_key.strip()
        if (
            not 3 <= len(normalized_key) <= 512
            or normalized_key.startswith("/")
            or ".." in normalized_key.split("/")
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", normalized_key)
        ):
            raise ValidationError("artifact object key is invalid")
        normalized_hash = sha256.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized_hash):
            raise ValidationError("artifact sha256 must be a SHA-256 hex digest")
        normalized_size = int(size_bytes)
        if not 0 <= normalized_size <= 10 * 1024 * 1024 * 1024:
            raise ValidationError("artifact size must be between 0 and 10 GiB")
        normalized_media_type = media_type.strip().lower()
        if not re.fullmatch(
            r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}",
            normalized_media_type,
        ):
            raise ValidationError("artifact media type is invalid")
        timestamp = created_at or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(timestamp, "artifact created_at")
        return cls(
            object_key=normalized_key,
            sha256=normalized_hash,
            size_bytes=normalized_size,
            media_type=normalized_media_type,
            created_at=timestamp.astimezone(UTC),
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        return cls.create(
            object_key=str(value["object_key"]),
            sha256=str(value["sha256"]),
            size_bytes=int(str(value["size_bytes"])),
            media_type=str(value["media_type"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "object_key": self.object_key,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class LeasedWorkState:
    max_attempts: int
    attempt_count: int
    status: WorkStatus
    lease_owner: str | None
    lease_token: int
    leased_until: datetime | None
    next_attempt_at: datetime | None
    last_error: str | None
    completed_at: datetime | None

    @classmethod
    def initial(cls, max_attempts: int, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(timestamp, "work state timestamp")
        return cls.restore(
            max_attempts=max_attempts,
            attempt_count=0,
            status=WorkStatus.QUEUED,
            lease_owner=None,
            lease_token=0,
            leased_until=None,
            next_attempt_at=timestamp,
            last_error=None,
            completed_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        max_attempts: int,
        attempt_count: int,
        status: WorkStatus,
        lease_owner: str | None,
        lease_token: int,
        leased_until: datetime | None,
        next_attempt_at: datetime | None,
        last_error: str | None,
        completed_at: datetime | None,
    ) -> Self:
        normalized_max = AsyncProcessingRules.normalize_max_attempts(max_attempts)
        normalized_attempt = int(attempt_count)
        if not 0 <= normalized_attempt <= normalized_max:
            raise ValidationError("asynchronous work attempt count is invalid")
        normalized_token = int(lease_token)
        if normalized_token < 0:
            raise ValidationError("asynchronous work lease token cannot be negative")
        normalized_owner = (
            None if lease_owner is None else AsyncProcessingRules.normalize_worker_id(lease_owner)
        )
        normalized_error = (
            None if last_error is None else AsyncProcessingRules.normalize_error(last_error)
        )
        normalized_lease = AsyncProcessingRules.normalize_optional_datetime(
            leased_until, "leased_until"
        )
        normalized_next = AsyncProcessingRules.normalize_optional_datetime(
            next_attempt_at, "next_attempt_at"
        )
        normalized_completed = AsyncProcessingRules.normalize_optional_datetime(
            completed_at, "completed_at"
        )
        cls._validate_state(
            max_attempts=normalized_max,
            attempt_count=normalized_attempt,
            status=status,
            lease_owner=normalized_owner,
            leased_until=normalized_lease,
            next_attempt_at=normalized_next,
            last_error=normalized_error,
            completed_at=normalized_completed,
        )
        return cls(
            max_attempts=normalized_max,
            attempt_count=normalized_attempt,
            status=status,
            lease_owner=normalized_owner,
            lease_token=normalized_token,
            leased_until=normalized_lease,
            next_attempt_at=normalized_next,
            last_error=normalized_error,
            completed_at=normalized_completed,
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        return cls.restore(
            max_attempts=int(str(value["max_attempts"])),
            attempt_count=int(str(value["attempt_count"])),
            status=WorkStatus.from_value(str(value["status"])),
            lease_owner=None if value.get("lease_owner") is None else str(value["lease_owner"]),
            lease_token=int(str(value.get("lease_token", 0))),
            leased_until=AsyncProcessingRules.parse_optional_datetime(value.get("leased_until")),
            next_attempt_at=AsyncProcessingRules.parse_optional_datetime(
                value.get("next_attempt_at")
            ),
            last_error=None if value.get("last_error") is None else str(value["last_error"]),
            completed_at=AsyncProcessingRules.parse_optional_datetime(value.get("completed_at")),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "max_attempts": self.max_attempts,
            "attempt_count": self.attempt_count,
            "status": self.status.value,
            "lease_owner": self.lease_owner,
            "lease_token": self.lease_token,
            "leased_until": None if self.leased_until is None else self.leased_until.isoformat(),
            "next_attempt_at": (
                None if self.next_attempt_at is None else self.next_attempt_at.isoformat()
            ),
            "last_error": self.last_error,
            "completed_at": None if self.completed_at is None else self.completed_at.isoformat(),
        }

    def is_claimable(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(current, "claim timestamp")
        if self.status is WorkStatus.QUEUED:
            return True
        if self.status is WorkStatus.RETRY_WAIT:
            return self.next_attempt_at is not None and self.next_attempt_at <= current
        return (
            self.status is WorkStatus.LEASED
            and self.leased_until is not None
            and self.leased_until <= current
            and self.attempt_count < self.max_attempts
        )

    def claim(self, worker_id: str, lease_seconds: int, now: datetime | None = None) -> Self:
        current = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(current, "claim timestamp")
        if not self.is_claimable(current):
            raise ConflictError("asynchronous work item is not claimable")
        if self.attempt_count >= self.max_attempts:
            raise ConflictError("asynchronous work item exhausted its attempts")
        duration = AsyncProcessingRules.normalize_lease_seconds(lease_seconds)
        return self.restore(
            max_attempts=self.max_attempts,
            attempt_count=self.attempt_count + 1,
            status=WorkStatus.LEASED,
            lease_owner=AsyncProcessingRules.normalize_worker_id(worker_id),
            lease_token=self.lease_token + 1,
            leased_until=current + timedelta(seconds=duration),
            next_attempt_at=None,
            last_error=self.last_error,
            completed_at=None,
        )

    def renew(
        self,
        worker_id: str,
        lease_token: int,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        current = now or datetime.now(UTC)
        self.assert_active_lease(worker_id, lease_token, current)
        return self.restore(
            max_attempts=self.max_attempts,
            attempt_count=self.attempt_count,
            status=WorkStatus.LEASED,
            lease_owner=self.lease_owner,
            lease_token=self.lease_token,
            leased_until=current
            + timedelta(seconds=AsyncProcessingRules.normalize_lease_seconds(lease_seconds)),
            next_attempt_at=None,
            last_error=self.last_error,
            completed_at=None,
        )

    def complete(
        self,
        worker_id: str,
        lease_token: int,
        now: datetime | None = None,
    ) -> Self:
        current = now or datetime.now(UTC)
        self.assert_active_lease(worker_id, lease_token, current)
        return self.restore(
            max_attempts=self.max_attempts,
            attempt_count=self.attempt_count,
            status=WorkStatus.COMPLETED,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=None,
            last_error=None,
            completed_at=current,
        )

    def fail(
        self,
        worker_id: str,
        lease_token: int,
        error: str,
        retry_delay_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        current = now or datetime.now(UTC)
        self.assert_active_lease(worker_id, lease_token, current)
        terminal = self.attempt_count >= self.max_attempts
        return self.restore(
            max_attempts=self.max_attempts,
            attempt_count=self.attempt_count,
            status=WorkStatus.DEAD_LETTER if terminal else WorkStatus.RETRY_WAIT,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=(
                None
                if terminal
                else current
                + timedelta(seconds=AsyncProcessingRules.normalize_retry_delay(retry_delay_seconds))
            ),
            last_error=AsyncProcessingRules.normalize_error(error),
            completed_at=None,
        )

    def expire_final_lease(self, now: datetime | None = None) -> Self:
        current = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(current, "lease expiry timestamp")
        if self.status is not WorkStatus.LEASED:
            raise ConflictError("only leased work can expire into dead-letter")
        if self.leased_until is None or self.leased_until > current:
            raise ConflictError("asynchronous work lease has not expired")
        if self.attempt_count < self.max_attempts:
            raise ConflictError("asynchronous work still has retry attempts")
        return self.restore(
            max_attempts=self.max_attempts,
            attempt_count=self.attempt_count,
            status=WorkStatus.DEAD_LETTER,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=None,
            last_error="lease expired after final attempt",
            completed_at=None,
        )

    def replay(self, now: datetime | None = None) -> Self:
        if self.status is not WorkStatus.DEAD_LETTER:
            raise ConflictError("only dead-letter work can be replayed")
        current = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(current, "replay timestamp")
        return self.restore(
            max_attempts=self.max_attempts,
            attempt_count=0,
            status=WorkStatus.QUEUED,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=current,
            last_error=self.last_error,
            completed_at=None,
        )

    def assert_active_lease(self, worker_id: str, lease_token: int, now: datetime) -> None:
        AsyncProcessingRules.validate_aware(now, "lease assertion timestamp")
        if self.status is not WorkStatus.LEASED:
            raise ConflictError("asynchronous work item is not leased")
        if (
            self.lease_owner != AsyncProcessingRules.normalize_worker_id(worker_id)
            or self.lease_token != lease_token
        ):
            raise ConflictError("asynchronous work lease fencing token is stale")
        if self.leased_until is None or self.leased_until <= now:
            raise ConflictError("asynchronous work lease has expired")

    def assert_transition_from(self, previous: Self) -> None:
        if self == previous:
            return
        if self.max_attempts != previous.max_attempts:
            raise ConflictError("asynchronous work max_attempts is immutable")
        if self.lease_token < previous.lease_token:
            raise ConflictError("asynchronous work lease fencing token is stale")
        claim_transition = (
            self.status is WorkStatus.LEASED
            and self.lease_token == previous.lease_token + 1
            and self.attempt_count == previous.attempt_count + 1
            and self.lease_owner is not None
            and self.leased_until is not None
            and previous.status
            in {
                WorkStatus.QUEUED,
                WorkStatus.RETRY_WAIT,
                WorkStatus.LEASED,
            }
        )
        if claim_transition:
            if (
                previous.status is WorkStatus.LEASED
                and previous.leased_until is not None
                and self.leased_until is not None
                and self.leased_until <= previous.leased_until
            ):
                raise ConflictError("asynchronous work replacement lease is stale")
            return
        if previous.status is WorkStatus.LEASED:
            same_fencing_token = (
                self.lease_token == previous.lease_token
                and self.attempt_count == previous.attempt_count
            )
            if same_fencing_token and self.status is WorkStatus.LEASED:
                if (
                    self.lease_owner != previous.lease_owner
                    or previous.leased_until is None
                    or self.leased_until is None
                    or self.leased_until < previous.leased_until
                ):
                    raise ConflictError("asynchronous work lease renewal is stale")
                return
            if (
                same_fencing_token
                and self.lease_owner is None
                and self.status
                in {
                    WorkStatus.RETRY_WAIT,
                    WorkStatus.COMPLETED,
                    WorkStatus.DEAD_LETTER,
                }
            ):
                return
        if (
            previous.status is WorkStatus.DEAD_LETTER
            and self.status is WorkStatus.QUEUED
            and self.lease_token == previous.lease_token
            and self.attempt_count == 0
        ):
            return
        raise ConflictError("asynchronous work state transition conflicts with persisted state")

    @staticmethod
    def _validate_state(
        *,
        max_attempts: int,
        attempt_count: int,
        status: WorkStatus,
        lease_owner: str | None,
        leased_until: datetime | None,
        next_attempt_at: datetime | None,
        last_error: str | None,
        completed_at: datetime | None,
    ) -> None:
        if status is WorkStatus.LEASED:
            if lease_owner is None or leased_until is None or attempt_count < 1:
                raise ValidationError("leased work requires owner, expiry and attempt")
        elif lease_owner is not None or leased_until is not None:
            raise ValidationError("non-leased work cannot retain lease metadata")
        if status in {WorkStatus.QUEUED, WorkStatus.RETRY_WAIT}:
            if next_attempt_at is None:
                raise ValidationError("queued work requires next_attempt_at")
        elif next_attempt_at is not None:
            raise ValidationError("leased or terminal work cannot retain next_attempt_at")
        if status is WorkStatus.RETRY_WAIT and last_error is None:
            raise ValidationError("retrying work requires an error")
        if status is WorkStatus.DEAD_LETTER and (
            last_error is None or attempt_count != max_attempts
        ):
            raise ValidationError("dead-letter work requires exhausted attempts and error")
        if status is WorkStatus.COMPLETED and completed_at is None:
            raise ValidationError("completed work requires a completion timestamp")
        if status is not WorkStatus.COMPLETED and completed_at is not None:
            raise ValidationError("non-completed work cannot retain completion metadata")


@dataclass(frozen=True, slots=True)
class AsyncJob:
    id: EntityId
    tenant_id: TenantId
    specialization: WorkerSpecialization
    operation: str
    idempotency_key: str
    payload_artifact: ArtifactReference
    result_artifact: ArtifactReference | None
    requested_by: str
    state: LeasedWorkState
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        specialization: WorkerSpecialization,
        operation: str,
        idempotency_key: str,
        payload_artifact: ArtifactReference,
        max_attempts: int,
        requested_by: str,
        job_id: EntityId | None = None,
        now: datetime | None = None,
    ) -> Self:
        timestamp = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(timestamp, "async job timestamp")
        return cls.restore(
            job_id=job_id or EntityId.new(),
            tenant_id=tenant_id,
            specialization=specialization,
            operation=operation,
            idempotency_key=idempotency_key,
            payload_artifact=payload_artifact,
            result_artifact=None,
            requested_by=requested_by,
            state=LeasedWorkState.initial(max_attempts, timestamp),
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def restore(
        cls,
        *,
        job_id: EntityId,
        tenant_id: TenantId,
        specialization: WorkerSpecialization,
        operation: str,
        idempotency_key: str,
        payload_artifact: ArtifactReference,
        result_artifact: ArtifactReference | None,
        requested_by: str,
        state: LeasedWorkState,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        normalized_operation = AsyncProcessingRules.normalize_operation(operation)
        normalized_key = AsyncProcessingRules.normalize_idempotency_key(idempotency_key)
        normalized_actor = AsyncProcessingRules.normalize_actor(requested_by)
        created = AsyncProcessingRules.normalize_datetime(created_at, "async job created_at")
        updated = AsyncProcessingRules.normalize_datetime(updated_at, "async job updated_at")
        if updated < created:
            raise ValidationError("async job updated_at cannot precede created_at")
        if state.status is WorkStatus.COMPLETED and result_artifact is None:
            raise ValidationError("completed async job requires a result artifact")
        if state.status is not WorkStatus.COMPLETED and result_artifact is not None:
            raise ValidationError("non-completed async job cannot retain a result artifact")
        return cls(
            id=job_id,
            tenant_id=tenant_id,
            specialization=specialization,
            operation=normalized_operation,
            idempotency_key=normalized_key,
            payload_artifact=payload_artifact,
            result_artifact=result_artifact,
            requested_by=normalized_actor,
            state=state,
            created_at=created,
            updated_at=updated,
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        payload = value["payload_artifact"]
        result = value.get("result_artifact")
        if not isinstance(payload, dict) or (result is not None and not isinstance(result, dict)):
            raise ValidationError("async job artifact metadata is invalid")
        return cls.restore(
            job_id=EntityId.from_value(str(value.get("job_id", value.get("id")))),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            specialization=WorkerSpecialization.from_value(str(value["specialization"])),
            operation=str(value["operation"]),
            idempotency_key=str(value["idempotency_key"]),
            payload_artifact=ArtifactReference.from_dict(payload),
            result_artifact=(None if result is None else ArtifactReference.from_dict(result)),
            requested_by=str(value["requested_by"]),
            state=LeasedWorkState.from_dict(value),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
        )

    def claim(self, worker_id: str, lease_seconds: int, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.claim(worker_id, lease_seconds, timestamp), None, timestamp)

    def renew(
        self,
        worker_id: str,
        lease_token: int,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(
            self.state.renew(worker_id, lease_token, lease_seconds, timestamp), None, timestamp
        )

    def complete(
        self,
        worker_id: str,
        lease_token: int,
        result_artifact: ArtifactReference,
        now: datetime | None = None,
    ) -> Self:
        if self.state.status is WorkStatus.COMPLETED:
            if self.result_artifact == result_artifact:
                return self
            raise ConflictError("async job completion conflicts with stored artifact")
        timestamp = now or datetime.now(UTC)
        return self._replace(
            self.state.complete(worker_id, lease_token, timestamp), result_artifact, timestamp
        )

    def fail(
        self,
        worker_id: str,
        lease_token: int,
        error: str,
        retry_delay_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(
            self.state.fail(worker_id, lease_token, error, retry_delay_seconds, timestamp),
            None,
            timestamp,
        )

    def expire_final_lease(self, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.expire_final_lease(timestamp), None, timestamp)

    def replay(self, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.replay(timestamp), None, timestamp)

    def assert_persistence_transition_from(self, previous: Self) -> None:
        if (
            self.id,
            self.tenant_id,
            self.specialization,
            self.operation,
            self.idempotency_key,
            self.payload_artifact,
            self.requested_by,
            self.created_at,
        ) != (
            previous.id,
            previous.tenant_id,
            previous.specialization,
            previous.operation,
            previous.idempotency_key,
            previous.payload_artifact,
            previous.requested_by,
            previous.created_at,
        ):
            raise ConflictError("async job immutable attributes cannot change")
        if self.updated_at < previous.updated_at:
            raise ConflictError("async job update is stale")
        self.state.assert_transition_from(previous.state)

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.id.value,
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "specialization": self.specialization.value,
            "operation": self.operation,
            "idempotency_key": self.idempotency_key,
            "payload_artifact": self.payload_artifact.as_dict(),
            "result_artifact": (
                None if self.result_artifact is None else self.result_artifact.as_dict()
            ),
            "requested_by": self.requested_by,
            **self.state.as_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def _replace(
        self,
        state: LeasedWorkState,
        result_artifact: ArtifactReference | None,
        updated_at: datetime,
    ) -> Self:
        return self.restore(
            job_id=self.id,
            tenant_id=self.tenant_id,
            specialization=self.specialization,
            operation=self.operation,
            idempotency_key=self.idempotency_key,
            payload_artifact=self.payload_artifact,
            result_artifact=result_artifact,
            requested_by=self.requested_by,
            state=state,
            created_at=self.created_at,
            updated_at=updated_at,
        )


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: EntityId
    tenant_id: TenantId
    aggregate_type: str
    aggregate_id: str
    event_name: str
    idempotency_key: str
    payload: dict[str, Any]
    state: LeasedWorkState
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        aggregate_type: str,
        aggregate_id: str,
        event_name: str,
        idempotency_key: str,
        payload: dict[str, Any],
        max_attempts: int = 10,
        event_id: EntityId | None = None,
        now: datetime | None = None,
    ) -> Self:
        timestamp = now or datetime.now(UTC)
        AsyncProcessingRules.validate_aware(timestamp, "outbox event timestamp")
        return cls.restore(
            event_id=event_id or EntityId.new(),
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_name=event_name,
            idempotency_key=idempotency_key,
            payload=payload,
            state=LeasedWorkState.initial(max_attempts, timestamp),
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def restore(
        cls,
        *,
        event_id: EntityId,
        tenant_id: TenantId,
        aggregate_type: str,
        aggregate_id: str,
        event_name: str,
        idempotency_key: str,
        payload: dict[str, Any],
        state: LeasedWorkState,
        created_at: datetime,
        updated_at: datetime,
    ) -> Self:
        normalized_aggregate_type = aggregate_type.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,63}", normalized_aggregate_type):
            raise ValidationError("outbox aggregate type is invalid")
        normalized_aggregate_id = aggregate_id.strip()
        if not 1 <= len(normalized_aggregate_id) <= 255:
            raise ValidationError("outbox aggregate id is invalid")
        normalized_event = event_name.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,120}", normalized_event):
            raise ValidationError("outbox event name is invalid")
        normalized_key = AsyncProcessingRules.normalize_idempotency_key(idempotency_key)
        try:
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValidationError("outbox payload must be JSON serializable") from exc
        if len(serialized.encode("utf-8")) > 65_536:
            raise ValidationError("outbox payload must not exceed 64 KiB")
        created = AsyncProcessingRules.normalize_datetime(created_at, "outbox created_at")
        updated = AsyncProcessingRules.normalize_datetime(updated_at, "outbox updated_at")
        if updated < created:
            raise ValidationError("outbox updated_at cannot precede created_at")
        return cls(
            id=event_id,
            tenant_id=tenant_id,
            aggregate_type=normalized_aggregate_type,
            aggregate_id=normalized_aggregate_id,
            event_name=normalized_event,
            idempotency_key=normalized_key,
            payload=dict(payload),
            state=state,
            created_at=created,
            updated_at=updated,
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        payload = value["payload"]
        if not isinstance(payload, dict):
            raise ValidationError("outbox payload must be an object")
        return cls.restore(
            event_id=EntityId.from_value(str(value.get("event_id", value.get("id")))),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            aggregate_type=str(value["aggregate_type"]),
            aggregate_id=str(value["aggregate_id"]),
            event_name=str(value["event_name"]),
            idempotency_key=str(value["idempotency_key"]),
            payload=dict(payload),
            state=LeasedWorkState.from_dict(value),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
        )

    def claim(self, worker_id: str, lease_seconds: int, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.claim(worker_id, lease_seconds, timestamp), timestamp)

    def renew(
        self,
        worker_id: str,
        lease_token: int,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(
            self.state.renew(worker_id, lease_token, lease_seconds, timestamp), timestamp
        )

    def mark_published(
        self,
        worker_id: str,
        lease_token: int,
        now: datetime | None = None,
    ) -> Self:
        if self.state.status is WorkStatus.COMPLETED:
            return self
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.complete(worker_id, lease_token, timestamp), timestamp)

    def fail(
        self,
        worker_id: str,
        lease_token: int,
        error: str,
        retry_delay_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(
            self.state.fail(worker_id, lease_token, error, retry_delay_seconds, timestamp),
            timestamp,
        )

    def expire_final_lease(self, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.expire_final_lease(timestamp), timestamp)

    def replay(self, now: datetime | None = None) -> Self:
        timestamp = now or datetime.now(UTC)
        return self._replace(self.state.replay(timestamp), timestamp)

    def assert_persistence_transition_from(self, previous: Self) -> None:
        if (
            self.id,
            self.tenant_id,
            self.aggregate_type,
            self.aggregate_id,
            self.event_name,
            self.idempotency_key,
            self.payload,
            self.created_at,
        ) != (
            previous.id,
            previous.tenant_id,
            previous.aggregate_type,
            previous.aggregate_id,
            previous.event_name,
            previous.idempotency_key,
            previous.payload,
            previous.created_at,
        ):
            raise ConflictError("outbox event immutable attributes cannot change")
        if self.updated_at < previous.updated_at:
            raise ConflictError("outbox event update is stale")
        self.state.assert_transition_from(previous.state)

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.id.value,
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "event_name": self.event_name,
            "idempotency_key": self.idempotency_key,
            "payload": self.payload,
            "published": self.state.status is WorkStatus.COMPLETED,
            **self.state.as_dict(),
            "published_at": (
                None
                if self.state.status is not WorkStatus.COMPLETED
                else self.state.completed_at.isoformat()
                if self.state.completed_at
                else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def _replace(self, state: LeasedWorkState, updated_at: datetime) -> Self:
        return self.restore(
            event_id=self.id,
            tenant_id=self.tenant_id,
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            event_name=self.event_name,
            idempotency_key=self.idempotency_key,
            payload=self.payload,
            state=state,
            created_at=self.created_at,
            updated_at=updated_at,
        )


class AsyncProcessingRules:
    @staticmethod
    def normalize_max_attempts(value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 20:
            raise ValidationError("asynchronous work max_attempts must be between 1 and 20")
        return normalized

    @staticmethod
    def normalize_lease_seconds(value: int) -> int:
        normalized = int(value)
        if not 5 <= normalized <= 3600:
            raise ValidationError("asynchronous work lease_seconds must be between 5 and 3600")
        return normalized

    @staticmethod
    def normalize_retry_delay(value: int) -> int:
        normalized = int(value)
        if not 0 <= normalized <= 86_400:
            raise ValidationError("asynchronous work retry delay must be between 0 and 86400")
        return normalized

    @staticmethod
    def normalize_worker_id(value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{2,127}", normalized):
            raise ValidationError("worker id must use 3 to 128 safe characters")
        return normalized

    @staticmethod
    def normalize_idempotency_key(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}", normalized):
            raise ValidationError("idempotency key must use 8 to 128 safe characters")
        return normalized

    @staticmethod
    def normalize_operation(value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,120}", normalized):
            raise ValidationError("asynchronous operation is invalid")
        return normalized

    @staticmethod
    def normalize_actor(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 128:
            raise ValidationError("asynchronous actor must contain 1 to 128 characters")
        return normalized

    @staticmethod
    def normalize_error(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValidationError("asynchronous failure error is mandatory")
        return normalized[:2048]

    @staticmethod
    def validate_aware(value: datetime, label: str) -> None:
        if value.tzinfo is None:
            raise ValidationError(label + " must be timezone-aware")

    @classmethod
    def normalize_datetime(cls, value: datetime, label: str) -> datetime:
        cls.validate_aware(value, label)
        return value.astimezone(UTC)

    @classmethod
    def normalize_optional_datetime(cls, value: datetime | None, label: str) -> datetime | None:
        return None if value is None else cls.normalize_datetime(value, label)

    @staticmethod
    def parse_optional_datetime(value: object) -> datetime | None:
        return None if value is None else datetime.fromisoformat(str(value))
