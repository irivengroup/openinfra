from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import ConflictError, EntityId, TenantId, ValidationError
from openinfra.domain.discovery import DiscoveryScope
from openinfra.domain.discovery_jobs import DiscoveryJob, DiscoveryJobStatus


def _job(now: datetime | None = None, max_attempts: int = 2) -> DiscoveryJob:
    created = now or datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    return DiscoveryJob.create(
        tenant_id=TenantId.from_value("default"),
        collector_id=EntityId.from_value("11111111-1111-4111-8111-111111111111"),
        requested_scope=DiscoveryScope.from_value("site/par1"),
        job_type="ssh-inventory",
        target="srv-app-01",
        idempotency_key="job/par1/srv-app-01/0001",
        max_attempts=max_attempts,
        requested_by="pytest",
        created_at=created,
    )


def test_discovery_job_reclaims_expired_lease_with_fencing_token() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    job = _job(now)
    first = job.claim(worker_id="worker-a", lease_seconds=30, now=now)

    assert first.status is DiscoveryJobStatus.LEASED
    assert first.attempt_count == 1
    assert first.lease_token == 1
    assert first.is_claimable(first.collector_id, now + timedelta(seconds=31)) is True

    second = first.claim(
        worker_id="worker-b",
        lease_seconds=30,
        now=now + timedelta(seconds=31),
    )

    assert second.lease_owner == "worker-b"
    assert second.attempt_count == 2
    assert second.lease_token == 2
    with pytest.raises(ConflictError, match="fencing token"):
        second.complete(
            worker_id="worker-a",
            lease_token=1,
            result_hash="a" * 64,
            now=now + timedelta(seconds=32),
        )


def test_discovery_job_retries_then_moves_to_dead_letter_and_replays() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    first_claim = _job(now).claim(worker_id="worker-a", lease_seconds=30, now=now)
    retrying = first_claim.fail(
        worker_id="worker-a",
        lease_token=1,
        error="temporary timeout",
        retry_delay_seconds=10,
        now=now + timedelta(seconds=1),
    )
    assert retrying.status is DiscoveryJobStatus.RETRY_WAIT
    assert retrying.is_claimable(retrying.collector_id, now + timedelta(seconds=10)) is False

    second_claim = retrying.claim(
        worker_id="worker-b",
        lease_seconds=30,
        now=now + timedelta(seconds=11),
    )
    dead_letter = second_claim.fail(
        worker_id="worker-b",
        lease_token=2,
        error="permanent failure",
        retry_delay_seconds=10,
        now=now + timedelta(seconds=12),
    )

    assert dead_letter.status is DiscoveryJobStatus.DEAD_LETTER
    assert dead_letter.next_attempt_at is None
    replayed = dead_letter.replay(now=now + timedelta(seconds=20))
    assert replayed.status is DiscoveryJobStatus.QUEUED
    assert replayed.attempt_count == 0
    assert replayed.lease_token == 2


def test_discovery_job_completion_is_idempotent_and_rejects_conflicting_result() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    claimed = _job(now).claim(worker_id="worker-a", lease_seconds=30, now=now)
    completed = claimed.complete(
        worker_id="worker-a",
        lease_token=1,
        result_hash="b" * 64,
        now=now + timedelta(seconds=1),
    )

    assert (
        completed.complete(
            worker_id="worker-a",
            lease_token=1,
            result_hash="b" * 64,
            now=now + timedelta(seconds=2),
        )
        is completed
    )
    with pytest.raises(ConflictError, match="conflicts"):
        completed.complete(
            worker_id="worker-a",
            lease_token=1,
            result_hash="c" * 64,
            now=now + timedelta(seconds=2),
        )


def test_discovery_job_validates_bounds_and_serialization() -> None:
    job = _job()
    assert DiscoveryJob.from_dict(job.as_dict()) == job

    with pytest.raises(ValidationError, match="max_attempts"):
        _job(max_attempts=0)
    with pytest.raises(ValidationError, match="lease_seconds"):
        job.claim(worker_id="worker-a", lease_seconds=1)
    with pytest.raises(ValidationError, match="SHA-256"):
        job.claim(worker_id="worker-a", lease_seconds=5).complete(
            worker_id="worker-a", lease_token=1, result_hash="invalid"
        )


def test_discovery_job_expired_final_lease_moves_to_dead_letter() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    leased = _job(now, max_attempts=1).claim(worker_id="worker-a", lease_seconds=5, now=now)

    dead_letter = leased.dead_letter_expired_final_lease(now=now + timedelta(seconds=6))

    assert dead_letter.status is DiscoveryJobStatus.DEAD_LETTER
    assert dead_letter.attempt_count == 1
    assert dead_letter.lease_token == 1
    assert dead_letter.lease_owner is None
    assert dead_letter.last_error == "lease expired after final attempt"
    dead_letter.assert_persistence_transition_from(leased)


def test_discovery_job_expired_lease_preserves_remaining_retry_attempts() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    leased = _job(now, max_attempts=2).claim(worker_id="worker-a", lease_seconds=5, now=now)

    with pytest.raises(ConflictError, match="still has retry attempts"):
        leased.dead_letter_expired_final_lease(now=now + timedelta(seconds=6))


def test_discovery_job_persistence_rejects_competing_terminal_transition() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    leased = _job(now).claim(worker_id="worker-a", lease_seconds=30, now=now)
    completed = leased.complete(
        worker_id="worker-a",
        lease_token=1,
        result_hash="d" * 64,
        now=now + timedelta(seconds=1),
    )
    retrying = leased.fail(
        worker_id="worker-a",
        lease_token=1,
        error="competing result",
        retry_delay_seconds=10,
        now=now + timedelta(seconds=2),
    )

    completed.assert_persistence_transition_from(leased)
    with pytest.raises(ConflictError, match="state transition"):
        retrying.assert_persistence_transition_from(completed)


def test_discovery_job_persistence_rejects_stale_lease_renewal() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    leased = _job(now).claim(worker_id="worker-a", lease_seconds=30, now=now)
    renewed = leased.renew_lease(
        worker_id="worker-a",
        lease_token=1,
        lease_seconds=60,
        now=now + timedelta(seconds=1),
    )

    renewed.assert_persistence_transition_from(leased)
    with pytest.raises(ConflictError, match="update is stale"):
        leased.assert_persistence_transition_from(renewed)


def test_discovery_job_rejects_invalid_status_and_chronology() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match="status is invalid"):
        DiscoveryJobStatus.from_value("unknown")
    with pytest.raises(ValidationError, match="updated_at cannot precede"):
        DiscoveryJob.create(
            tenant_id=TenantId.from_value("default"),
            collector_id=EntityId.from_value("11111111-1111-4111-8111-111111111111"),
            requested_scope=DiscoveryScope.from_value("site/par1"),
            job_type="ssh-inventory",
            target="srv-app-01",
            idempotency_key="chronology-job-0001",
            max_attempts=2,
            requested_by="pytest",
            created_at=now,
            updated_at=now - timedelta(seconds=1),
        )


def test_discovery_job_restore_rejects_invalid_persisted_states() -> None:
    base = _job()
    payload = base.as_dict()

    invalid_cases = (
        ({"attempt_count": 3}, "attempt_count is invalid"),
        ({"lease_token": -1}, "lease_token cannot be negative"),
        (
            {"updated_at": (base.created_at - timedelta(seconds=1)).isoformat()},
            "updated_at cannot precede",
        ),
        (
            {
                "status": "leased",
                "attempt_count": 1,
                "lease_owner": None,
                "leased_until": (base.created_at + timedelta(seconds=30)).isoformat(),
                "next_attempt_at": None,
            },
            "requires owner, expiry and attempt",
        ),
        (
            {
                "status": "queued",
                "lease_owner": "worker-a",
                "leased_until": (base.created_at + timedelta(seconds=30)).isoformat(),
            },
            "cannot retain lease metadata",
        ),
        ({"next_attempt_at": None}, "requires next_attempt_at"),
        (
            {
                "status": "leased",
                "attempt_count": 1,
                "lease_owner": "worker-a",
                "leased_until": (base.created_at + timedelta(seconds=30)).isoformat(),
                "next_attempt_at": base.created_at.isoformat(),
            },
            "cannot have next_attempt_at",
        ),
        (
            {"status": "retry-wait", "last_error": None},
            "retrying discovery job requires last_error",
        ),
        (
            {
                "status": "dead-letter",
                "attempt_count": 1,
                "next_attempt_at": None,
                "last_error": "failed",
            },
            "requires exhausted attempts and error",
        ),
        (
            {"status": "completed", "next_attempt_at": None},
            "requires result hash and timestamp",
        ),
        (
            {
                "result_hash": "a" * 64,
                "completed_at": base.created_at.isoformat(),
            },
            "cannot retain completion metadata",
        ),
    )
    for overrides, message in invalid_cases:
        candidate = dict(payload)
        candidate.update(overrides)
        with pytest.raises(ValidationError, match=message):
            DiscoveryJob.from_dict(candidate)


def test_discovery_job_claim_and_lease_guards_cover_negative_paths() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    job = _job(now)
    other_collector = EntityId.from_value("22222222-2222-4222-8222-222222222222")
    assert job.is_claimable(other_collector, now) is False

    completed = job.claim(worker_id="worker-a", lease_seconds=5, now=now).complete(
        worker_id="worker-a",
        lease_token=1,
        result_hash="a" * 64,
        now=now + timedelta(seconds=1),
    )
    with pytest.raises(ConflictError, match="not claimable"):
        completed.claim(worker_id="worker-b", lease_seconds=5, now=now + timedelta(seconds=2))
    with pytest.raises(ConflictError, match="not leased"):
        job.complete(
            worker_id="worker-a",
            lease_token=0,
            result_hash="b" * 64,
            now=now,
        )

    expired = job.claim(worker_id="worker-a", lease_seconds=5, now=now)
    with pytest.raises(ConflictError, match="lease has expired"):
        expired.complete(
            worker_id="worker-a",
            lease_token=1,
            result_hash="b" * 64,
            now=now + timedelta(seconds=6),
        )

    exhausted = DiscoveryJob.restore(
        tenant_id=job.tenant_id,
        collector_id=job.collector_id,
        requested_scope=job.requested_scope,
        job_type=job.job_type,
        target=job.target,
        idempotency_key=job.idempotency_key,
        max_attempts=2,
        attempt_count=2,
        status=DiscoveryJobStatus.QUEUED,
        lease_owner=None,
        lease_token=2,
        leased_until=None,
        next_attempt_at=now,
        last_error=None,
        result_hash=None,
        requested_by=job.requested_by,
        job_id=job.id,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    with pytest.raises(ConflictError, match="exhausted its attempts"):
        exhausted.claim(worker_id="worker-a", lease_seconds=5, now=now)


def test_discovery_job_expiry_replay_and_input_guards() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    queued = _job(now)
    with pytest.raises(ConflictError, match="only leased"):
        queued.dead_letter_expired_final_lease(now=now)
    leased = queued.claim(worker_id="worker-a", lease_seconds=30, now=now)
    with pytest.raises(ConflictError, match="has not expired"):
        leased.dead_letter_expired_final_lease(now=now + timedelta(seconds=1))
    with pytest.raises(ConflictError, match="only dead-letter"):
        queued.replay(now=now)

    invalid_creations = (
        ({"idempotency_key": "bad"}, "idempotency key"),
        ({"requested_by": ""}, "actor"),
    )
    for overrides, message in invalid_creations:
        values = {
            "tenant_id": queued.tenant_id,
            "collector_id": queued.collector_id,
            "requested_scope": queued.requested_scope,
            "job_type": queued.job_type,
            "target": queued.target,
            "idempotency_key": "valid-job-key-0001",
            "max_attempts": 2,
            "requested_by": "pytest",
            "created_at": now,
        }
        values.update(overrides)
        with pytest.raises(ValidationError, match=message):
            DiscoveryJob.create(**values)

    with pytest.raises(ValidationError, match="worker id"):
        queued.claim(worker_id="x", lease_seconds=5, now=now)
    with pytest.raises(ValidationError, match="retry delay"):
        leased.fail(
            worker_id="worker-a",
            lease_token=1,
            error="failure",
            retry_delay_seconds=86_401,
            now=now + timedelta(seconds=1),
        )
    with pytest.raises(ValidationError, match="error is mandatory"):
        leased.fail(
            worker_id="worker-a",
            lease_token=1,
            error=" ",
            retry_delay_seconds=0,
            now=now + timedelta(seconds=1),
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        queued.is_claimable(queued.collector_id, datetime(2026, 7, 10, 8, 0))


def test_discovery_job_persistence_transition_guards_all_conflicts() -> None:
    now = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
    queued = _job(now)
    queued.assert_persistence_transition_from(queued)
    with pytest.raises(ConflictError, match="immutable attributes"):
        replace(queued, target="srv-other").assert_persistence_transition_from(queued)

    leased = queued.claim(worker_id="worker-a", lease_seconds=30, now=now)
    with pytest.raises(ConflictError, match="fencing token is stale"):
        replace(
            leased,
            lease_token=0,
            updated_at=now + timedelta(seconds=1),
        ).assert_persistence_transition_from(leased)
    with pytest.raises(ConflictError, match="lease owner cannot change"):
        replace(
            leased,
            lease_owner="worker-b",
            updated_at=now + timedelta(seconds=1),
        ).assert_persistence_transition_from(leased)
    with pytest.raises(ConflictError, match="lease renewal is stale"):
        replace(
            leased,
            leased_until=leased.leased_until - timedelta(seconds=1),
            updated_at=now + timedelta(seconds=1),
        ).assert_persistence_transition_from(leased)
