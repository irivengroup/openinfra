from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Self

from openinfra.domain.common import ConflictError, EntityId, TenantId, ValidationError
from openinfra.domain.discovery import DiscoveryJobAuthorization, DiscoveryScope


class DiscoveryJobStatus(StrEnum):
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
            raise ValidationError("discovery job status is invalid") from exc


@dataclass(frozen=True, slots=True)
class DiscoveryJob:
    id: EntityId
    tenant_id: TenantId
    collector_id: EntityId
    requested_scope: DiscoveryScope
    job_type: str
    target: str
    idempotency_key: str
    max_attempts: int
    attempt_count: int
    status: DiscoveryJobStatus
    lease_owner: str | None
    lease_token: int
    leased_until: datetime | None
    next_attempt_at: datetime | None
    last_error: str | None
    result_hash: str | None
    requested_by: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        collector_id: EntityId,
        requested_scope: DiscoveryScope,
        job_type: str,
        target: str,
        idempotency_key: str,
        max_attempts: int,
        requested_by: str,
        job_id: EntityId | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> Self:
        now = created_at or datetime.now(UTC)
        updated = updated_at or now
        cls._validate_aware(now, "created_at")
        cls._validate_aware(updated, "updated_at")
        if updated < now:
            raise ValidationError("discovery job updated_at cannot precede created_at")
        normalized_job_type = DiscoveryJobAuthorization._normalize_job_type(job_type)
        normalized_target = DiscoveryJobAuthorization._normalize_target(target)
        normalized_key = cls._normalize_idempotency_key(idempotency_key)
        normalized_actor = cls._normalize_actor(requested_by)
        normalized_max_attempts = cls._normalize_max_attempts(max_attempts)
        return cls(
            id=job_id or EntityId.new(),
            tenant_id=tenant_id,
            collector_id=collector_id,
            requested_scope=requested_scope,
            job_type=normalized_job_type,
            target=normalized_target,
            idempotency_key=normalized_key,
            max_attempts=normalized_max_attempts,
            attempt_count=0,
            status=DiscoveryJobStatus.QUEUED,
            lease_owner=None,
            lease_token=0,
            leased_until=None,
            next_attempt_at=now.astimezone(UTC),
            last_error=None,
            result_hash=None,
            requested_by=normalized_actor,
            created_at=now.astimezone(UTC),
            updated_at=updated.astimezone(UTC),
            completed_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        tenant_id: TenantId,
        collector_id: EntityId,
        requested_scope: DiscoveryScope,
        job_type: str,
        target: str,
        idempotency_key: str,
        max_attempts: int,
        attempt_count: int,
        status: DiscoveryJobStatus,
        lease_owner: str | None,
        lease_token: int,
        leased_until: datetime | None,
        next_attempt_at: datetime | None,
        last_error: str | None,
        result_hash: str | None,
        requested_by: str,
        job_id: EntityId,
        created_at: datetime,
        updated_at: datetime,
        completed_at: datetime | None,
    ) -> Self:
        normalized_job_type = DiscoveryJobAuthorization._normalize_job_type(job_type)
        normalized_target = DiscoveryJobAuthorization._normalize_target(target)
        normalized_key = cls._normalize_idempotency_key(idempotency_key)
        normalized_actor = cls._normalize_actor(requested_by)
        normalized_max_attempts = cls._normalize_max_attempts(max_attempts)
        if not 0 <= attempt_count <= normalized_max_attempts:
            raise ValidationError("discovery job attempt_count is invalid")
        if lease_token < 0:
            raise ValidationError("discovery job lease_token cannot be negative")
        cls._validate_aware(created_at, "created_at")
        cls._validate_aware(updated_at, "updated_at")
        if updated_at < created_at:
            raise ValidationError("discovery job updated_at cannot precede created_at")
        for field_name, value in (
            ("leased_until", leased_until),
            ("next_attempt_at", next_attempt_at),
            ("completed_at", completed_at),
        ):
            if value is not None:
                cls._validate_aware(value, field_name)
        normalized_owner = None if lease_owner is None else cls._normalize_worker_id(lease_owner)
        normalized_error = cls._normalize_optional_error(last_error)
        normalized_result = cls._normalize_optional_hash(result_hash)
        cls._validate_state(
            status=status,
            attempt_count=attempt_count,
            max_attempts=normalized_max_attempts,
            lease_owner=normalized_owner,
            leased_until=leased_until,
            next_attempt_at=next_attempt_at,
            last_error=normalized_error,
            result_hash=normalized_result,
            completed_at=completed_at,
        )
        return cls(
            id=job_id,
            tenant_id=tenant_id,
            collector_id=collector_id,
            requested_scope=requested_scope,
            job_type=normalized_job_type,
            target=normalized_target,
            idempotency_key=normalized_key,
            max_attempts=normalized_max_attempts,
            attempt_count=attempt_count,
            status=status,
            lease_owner=normalized_owner,
            lease_token=lease_token,
            leased_until=None if leased_until is None else leased_until.astimezone(UTC),
            next_attempt_at=(None if next_attempt_at is None else next_attempt_at.astimezone(UTC)),
            last_error=normalized_error,
            result_hash=normalized_result,
            requested_by=normalized_actor,
            created_at=created_at.astimezone(UTC),
            updated_at=updated_at.astimezone(UTC),
            completed_at=None if completed_at is None else completed_at.astimezone(UTC),
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        return cls.restore(
            job_id=EntityId.from_value(str(value.get("id", value.get("job_id")))),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            collector_id=EntityId.from_value(str(value["collector_id"])),
            requested_scope=DiscoveryScope.from_value(str(value["requested_scope"])),
            job_type=str(value["job_type"]),
            target=str(value["target"]),
            idempotency_key=str(value["idempotency_key"]),
            max_attempts=int(str(value["max_attempts"])),
            attempt_count=int(str(value["attempt_count"])),
            status=DiscoveryJobStatus.from_value(str(value["status"])),
            lease_owner=None if value.get("lease_owner") is None else str(value["lease_owner"]),
            lease_token=int(str(value.get("lease_token", 0))),
            leased_until=cls._parse_optional_datetime(value.get("leased_until")),
            next_attempt_at=cls._parse_optional_datetime(value.get("next_attempt_at")),
            last_error=None if value.get("last_error") is None else str(value["last_error"]),
            result_hash=None if value.get("result_hash") is None else str(value["result_hash"]),
            requested_by=str(value["requested_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
            completed_at=cls._parse_optional_datetime(value.get("completed_at")),
        )

    def is_claimable(self, collector_id: EntityId, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        self._validate_aware(current, "now")
        if collector_id != self.collector_id:
            return False
        if self.status is DiscoveryJobStatus.QUEUED:
            return True
        if self.status is DiscoveryJobStatus.RETRY_WAIT:
            return self.next_attempt_at is not None and self.next_attempt_at <= current
        return (
            self.status is DiscoveryJobStatus.LEASED
            and self.leased_until is not None
            and self.leased_until <= current
        )

    def claim(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        current = now or datetime.now(UTC)
        self._validate_aware(current, "now")
        if not self.is_claimable(self.collector_id, current):
            raise ConflictError("discovery job is not claimable")
        if self.attempt_count >= self.max_attempts:
            raise ConflictError("discovery job exhausted its attempts")
        owner = self._normalize_worker_id(worker_id)
        duration = self._normalize_lease_seconds(lease_seconds)
        return self._replace(
            status=DiscoveryJobStatus.LEASED,
            attempt_count=self.attempt_count + 1,
            lease_owner=owner,
            lease_token=self.lease_token + 1,
            leased_until=current + timedelta(seconds=duration),
            next_attempt_at=None,
            last_error=self.last_error,
            result_hash=None,
            completed_at=None,
            now=current,
        )

    def renew_lease(
        self,
        *,
        worker_id: str,
        lease_token: int,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        current = now or datetime.now(UTC)
        self._assert_active_lease(worker_id, lease_token, current)
        duration = self._normalize_lease_seconds(lease_seconds)
        return self._replace(
            status=DiscoveryJobStatus.LEASED,
            attempt_count=self.attempt_count,
            lease_owner=self.lease_owner,
            lease_token=self.lease_token,
            leased_until=current + timedelta(seconds=duration),
            next_attempt_at=None,
            last_error=self.last_error,
            result_hash=None,
            completed_at=None,
            now=current,
        )

    def complete(
        self,
        *,
        worker_id: str,
        lease_token: int,
        result_hash: str,
        now: datetime | None = None,
    ) -> Self:
        normalized_hash = self._normalize_hash(result_hash)
        if self.status is DiscoveryJobStatus.COMPLETED:
            if self.result_hash == normalized_hash:
                return self
            raise ConflictError("discovery job completion result conflicts with stored result")
        current = now or datetime.now(UTC)
        self._assert_active_lease(worker_id, lease_token, current)
        return self._replace(
            status=DiscoveryJobStatus.COMPLETED,
            attempt_count=self.attempt_count,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=None,
            last_error=None,
            result_hash=normalized_hash,
            completed_at=current,
            now=current,
        )

    def fail(
        self,
        *,
        worker_id: str,
        lease_token: int,
        error: str,
        retry_delay_seconds: int,
        now: datetime | None = None,
    ) -> Self:
        current = now or datetime.now(UTC)
        self._assert_active_lease(worker_id, lease_token, current)
        normalized_error = self._normalize_error(error)
        delay = self._normalize_retry_delay(retry_delay_seconds)
        terminal = self.attempt_count >= self.max_attempts
        return self._replace(
            status=(DiscoveryJobStatus.DEAD_LETTER if terminal else DiscoveryJobStatus.RETRY_WAIT),
            attempt_count=self.attempt_count,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=None if terminal else current + timedelta(seconds=delay),
            last_error=normalized_error,
            result_hash=None,
            completed_at=None,
            now=current,
        )

    def dead_letter_expired_final_lease(self, *, now: datetime | None = None) -> Self:
        current = now or datetime.now(UTC)
        self._validate_aware(current, "now")
        if self.status is not DiscoveryJobStatus.LEASED:
            raise ConflictError("only leased discovery jobs can expire into dead-letter")
        if self.leased_until is None or self.leased_until > current:
            raise ConflictError("discovery job lease has not expired")
        if self.attempt_count < self.max_attempts:
            raise ConflictError("discovery job still has retry attempts")
        return self._replace(
            status=DiscoveryJobStatus.DEAD_LETTER,
            attempt_count=self.attempt_count,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=None,
            last_error="lease expired after final attempt",
            result_hash=None,
            completed_at=None,
            now=current,
        )

    def assert_persistence_transition_from(self, previous: Self) -> None:
        immutable_current = (
            self.id,
            self.tenant_id,
            self.collector_id,
            self.requested_scope,
            self.job_type,
            self.target,
            self.idempotency_key,
            self.max_attempts,
            self.requested_by,
            self.created_at,
        )
        immutable_previous = (
            previous.id,
            previous.tenant_id,
            previous.collector_id,
            previous.requested_scope,
            previous.job_type,
            previous.target,
            previous.idempotency_key,
            previous.max_attempts,
            previous.requested_by,
            previous.created_at,
        )
        if immutable_current != immutable_previous:
            raise ConflictError("discovery job immutable attributes cannot change")
        if self == previous:
            return
        if self.updated_at < previous.updated_at:
            raise ConflictError("discovery job update is stale")
        if self.lease_token < previous.lease_token:
            raise ConflictError("discovery job lease fencing token is stale")
        if (
            previous.status is DiscoveryJobStatus.LEASED
            and self.lease_token == previous.lease_token
            and self.attempt_count == previous.attempt_count
        ):
            if self.status is DiscoveryJobStatus.LEASED:
                if self.lease_owner != previous.lease_owner:
                    raise ConflictError("discovery job lease owner cannot change without a claim")
                if (
                    previous.leased_until is None
                    or self.leased_until is None
                    or self.leased_until < previous.leased_until
                ):
                    raise ConflictError("discovery job lease renewal is stale")
                return
            if self.status in {
                DiscoveryJobStatus.RETRY_WAIT,
                DiscoveryJobStatus.COMPLETED,
                DiscoveryJobStatus.DEAD_LETTER,
            }:
                return
        if (
            previous.status is DiscoveryJobStatus.DEAD_LETTER
            and self.status is DiscoveryJobStatus.QUEUED
            and self.lease_token == previous.lease_token
            and self.attempt_count == 0
        ):
            return
        raise ConflictError("discovery job state transition conflicts with persisted state")

    def replay(self, *, now: datetime | None = None) -> Self:
        if self.status is not DiscoveryJobStatus.DEAD_LETTER:
            raise ConflictError("only dead-letter discovery jobs can be replayed")
        current = now or datetime.now(UTC)
        self._validate_aware(current, "now")
        return self._replace(
            status=DiscoveryJobStatus.QUEUED,
            attempt_count=0,
            lease_owner=None,
            lease_token=self.lease_token,
            leased_until=None,
            next_attempt_at=current,
            last_error=self.last_error,
            result_hash=None,
            completed_at=None,
            now=current,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.id.value,
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "collector_id": self.collector_id.value,
            "requested_scope": self.requested_scope.value,
            "job_type": self.job_type,
            "target": self.target,
            "idempotency_key": self.idempotency_key,
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
            "result_hash": self.result_hash,
            "requested_by": self.requested_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": None if self.completed_at is None else self.completed_at.isoformat(),
        }

    def _assert_active_lease(self, worker_id: str, lease_token: int, now: datetime) -> None:
        self._validate_aware(now, "now")
        owner = self._normalize_worker_id(worker_id)
        if self.status is not DiscoveryJobStatus.LEASED:
            raise ConflictError("discovery job is not leased")
        if self.lease_owner != owner or self.lease_token != lease_token:
            raise ConflictError("discovery job lease fencing token is stale")
        if self.leased_until is None or self.leased_until <= now:
            raise ConflictError("discovery job lease has expired")

    def _replace(
        self,
        *,
        status: DiscoveryJobStatus,
        attempt_count: int,
        lease_owner: str | None,
        lease_token: int,
        leased_until: datetime | None,
        next_attempt_at: datetime | None,
        last_error: str | None,
        result_hash: str | None,
        completed_at: datetime | None,
        now: datetime,
    ) -> Self:
        return self.restore(
            tenant_id=self.tenant_id,
            collector_id=self.collector_id,
            requested_scope=self.requested_scope,
            job_type=self.job_type,
            target=self.target,
            idempotency_key=self.idempotency_key,
            max_attempts=self.max_attempts,
            attempt_count=attempt_count,
            status=status,
            lease_owner=lease_owner,
            lease_token=lease_token,
            leased_until=leased_until,
            next_attempt_at=next_attempt_at,
            last_error=last_error,
            result_hash=result_hash,
            requested_by=self.requested_by,
            job_id=self.id,
            created_at=self.created_at,
            updated_at=now,
            completed_at=completed_at,
        )

    @staticmethod
    def _normalize_idempotency_key(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}", normalized):
            raise ValidationError("discovery job idempotency key must use 8 to 128 safe characters")
        return normalized

    @staticmethod
    def _normalize_actor(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 128:
            raise ValidationError("discovery job actor must contain 1 to 128 characters")
        return normalized

    @staticmethod
    def _normalize_worker_id(value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{2,127}", normalized):
            raise ValidationError("discovery worker id must use 3 to 128 safe characters")
        return normalized

    @staticmethod
    def _normalize_max_attempts(value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 20:
            raise ValidationError("discovery job max_attempts must be between 1 and 20")
        return normalized

    @staticmethod
    def _normalize_lease_seconds(value: int) -> int:
        normalized = int(value)
        if not 5 <= normalized <= 3600:
            raise ValidationError("discovery job lease_seconds must be between 5 and 3600")
        return normalized

    @staticmethod
    def _normalize_retry_delay(value: int) -> int:
        normalized = int(value)
        if not 0 <= normalized <= 86_400:
            raise ValidationError("discovery job retry delay must be between 0 and 86400")
        return normalized

    @staticmethod
    def _normalize_error(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValidationError("discovery job failure error is mandatory")
        return normalized[:1024]

    @classmethod
    def _normalize_optional_error(cls, value: str | None) -> str | None:
        return None if value is None else cls._normalize_error(value)

    @staticmethod
    def _normalize_hash(value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValidationError("discovery job result hash must be a SHA-256 hex digest")
        return normalized

    @classmethod
    def _normalize_optional_hash(cls, value: str | None) -> str | None:
        return None if value is None else cls._normalize_hash(value)

    @staticmethod
    def _validate_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None:
            raise ValidationError(f"discovery job {field_name} must be timezone-aware")

    @staticmethod
    def _parse_optional_datetime(value: object) -> datetime | None:
        return None if value is None else datetime.fromisoformat(str(value))

    @staticmethod
    def _validate_state(
        *,
        status: DiscoveryJobStatus,
        attempt_count: int,
        max_attempts: int,
        lease_owner: str | None,
        leased_until: datetime | None,
        next_attempt_at: datetime | None,
        last_error: str | None,
        result_hash: str | None,
        completed_at: datetime | None,
    ) -> None:
        if status is DiscoveryJobStatus.LEASED:
            if lease_owner is None or leased_until is None or attempt_count < 1:
                raise ValidationError("leased discovery job requires owner, expiry and attempt")
        elif lease_owner is not None or leased_until is not None:
            raise ValidationError("non-leased discovery job cannot retain lease metadata")
        if status in {DiscoveryJobStatus.QUEUED, DiscoveryJobStatus.RETRY_WAIT}:
            if next_attempt_at is None:
                raise ValidationError("queued discovery job requires next_attempt_at")
        elif next_attempt_at is not None:
            raise ValidationError("terminal or leased discovery job cannot have next_attempt_at")
        if status is DiscoveryJobStatus.RETRY_WAIT and last_error is None:
            raise ValidationError("retrying discovery job requires last_error")
        if status is DiscoveryJobStatus.DEAD_LETTER and (
            last_error is None or attempt_count != max_attempts
        ):
            raise ValidationError("dead-letter discovery job requires exhausted attempts and error")
        if status is DiscoveryJobStatus.COMPLETED:
            if result_hash is None or completed_at is None:
                raise ValidationError("completed discovery job requires result hash and timestamp")
        elif result_hash is not None or completed_at is not None:
            raise ValidationError("non-completed discovery job cannot retain completion metadata")
