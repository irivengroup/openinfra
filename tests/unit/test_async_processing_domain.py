from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.async_processing import (
    ArtifactReference,
    AsyncJob,
    LeasedWorkState,
    OutboxEvent,
    WorkerSpecialization,
    WorkStatus,
)
from openinfra.domain.common import ConflictError, TenantId, ValidationError


def artifact() -> ArtifactReference:
    return ArtifactReference.create(
        object_key="default/async-payload/aa/" + "a" * 64 + ".json",
        sha256="a" * 64,
        size_bytes=2,
        media_type="application/json",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_lease_fencing_retry_dead_letter_and_replay() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = LeasedWorkState.initial(2, now)
    first = state.claim("reporting-01", 10, now)
    assert first.status is WorkStatus.LEASED
    assert first.lease_token == 1
    with pytest.raises(ConflictError, match="stale"):
        first.complete("reporting-02", 1, now + timedelta(seconds=1))
    retry = first.fail("reporting-01", 1, "temporary", 0, now + timedelta(seconds=1))
    assert retry.status is WorkStatus.RETRY_WAIT
    second = retry.claim("reporting-02", 10, now + timedelta(seconds=1))
    dead = second.fail("reporting-02", 2, "permanent", 0, now + timedelta(seconds=2))
    assert dead.status is WorkStatus.DEAD_LETTER
    replayed = dead.replay(now + timedelta(seconds=3))
    assert replayed.status is WorkStatus.QUEUED
    assert replayed.attempt_count == 0
    assert replayed.lease_token == 2


def test_expired_final_lease_moves_to_dead_letter() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    leased = LeasedWorkState.initial(1, now).claim("reporting-01", 5, now)
    dead = leased.expire_final_lease(now + timedelta(seconds=5))
    assert dead.status is WorkStatus.DEAD_LETTER
    assert dead.last_error == "lease expired after final attempt"


def test_job_and_outbox_invariants() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    job = AsyncJob.create(
        tenant_id=TenantId.from_value("default"),
        specialization=WorkerSpecialization.REPORTING,
        operation="reporting.async-queue-health",
        idempotency_key="request-001",
        payload_artifact=artifact(),
        max_attempts=3,
        requested_by="tester",
        now=now,
    )
    claimed = job.claim("reporting-01", 30, now)
    result = ArtifactReference.create(
        object_key="default/async-result/bb/" + "b" * 64 + ".json",
        sha256="b" * 64,
        size_bytes=2,
        media_type="application/json",
        created_at=now,
    )
    completed = claimed.complete("reporting-01", 1, result, now + timedelta(seconds=1))
    completed.assert_persistence_transition_from(claimed)
    assert completed.result_artifact == result

    event = OutboxEvent.create(
        tenant_id=TenantId.from_value("default"),
        aggregate_type="async-job",
        aggregate_id=job.id.value,
        event_name="async.job.submitted",
        idempotency_key="event-001",
        payload={"job_id": job.id.value},
        now=now,
    )
    published = event.claim("outbox-01", 30, now).mark_published(
        "outbox-01", 1, now + timedelta(seconds=1)
    )
    assert published.as_dict()["published"] is True


def test_invalid_artifact_and_oversized_outbox_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ArtifactReference.create(
            object_key="../escape",
            sha256="x",
            size_bytes=-1,
            media_type="bad",
        )
    with pytest.raises(ValidationError, match="64 KiB"):
        OutboxEvent.create(
            tenant_id=TenantId.from_value("default"),
            aggregate_type="async-job",
            aggregate_id="id",
            event_name="async.job.submitted",
            idempotency_key="event-large",
            payload={"data": "x" * 70_000},
        )


def test_enum_and_rule_validation_contracts() -> None:
    from openinfra.domain.async_processing import AsyncProcessingRules

    assert WorkStatus.from_value("RETRY_WAIT") is WorkStatus.RETRY_WAIT
    assert WorkerSpecialization.from_value("REPORTING") is WorkerSpecialization.REPORTING
    for invalid, expected in (("bad", "status"), ("", "status")):
        with pytest.raises(ValidationError, match=expected):
            WorkStatus.from_value(invalid)
    with pytest.raises(ValidationError, match="specialization"):
        WorkerSpecialization.from_value("unknown")

    validators = (
        (AsyncProcessingRules.normalize_max_attempts, 0, "max_attempts"),
        (AsyncProcessingRules.normalize_lease_seconds, 4, "lease_seconds"),
        (AsyncProcessingRules.normalize_retry_delay, -1, "retry delay"),
        (AsyncProcessingRules.normalize_worker_id, "x", "worker id"),
        (AsyncProcessingRules.normalize_idempotency_key, "short", "idempotency"),
        (AsyncProcessingRules.normalize_operation, "?", "operation"),
        (AsyncProcessingRules.normalize_actor, "", "actor"),
        (AsyncProcessingRules.normalize_error, "  ", "error"),
    )
    for validator, value, message in validators:
        with pytest.raises(ValidationError, match=message):
            validator(value)
    with pytest.raises(ValidationError, match="timezone-aware"):
        AsyncProcessingRules.normalize_datetime(datetime(2026, 1, 1), "timestamp")
    assert AsyncProcessingRules.normalize_optional_datetime(None, "optional") is None
    assert AsyncProcessingRules.parse_optional_datetime(None) is None
    parsed = AsyncProcessingRules.parse_optional_datetime("2026-01-01T00:00:00+00:00")
    assert parsed == datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"object_key": "/absolute"}, "object key"),
        ({"sha256": "z" * 64}, "sha256"),
        ({"size_bytes": 10 * 1024 * 1024 * 1024 + 1}, "size"),
        ({"media_type": "invalid"}, "media type"),
        ({"created_at": datetime(2026, 1, 1)}, "timezone-aware"),
    ],
)
def test_artifact_reference_validates_each_invariant(overrides, message: str) -> None:
    values = {
        "object_key": "default/async-result/aa/" + "a" * 64 + ".json",
        "sha256": "a" * 64,
        "size_bytes": 2,
        "media_type": "application/json",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    values.update(overrides)
    with pytest.raises(ValidationError, match=message):
        ArtifactReference.create(**values)


def test_artifact_reference_round_trip() -> None:
    original = artifact()
    assert ArtifactReference.from_dict(original.as_dict()) == original


def test_artifact_reference_locator_payload_is_stable_and_backward_compatible() -> None:
    original = artifact()

    locator = original.as_locator_dict()
    restored = ArtifactReference.from_dict(locator)

    assert locator == {
        "object_key": original.object_key,
        "sha256": original.sha256,
        "size_bytes": original.size_bytes,
        "media_type": original.media_type,
    }
    assert restored.object_key == original.object_key
    assert restored.sha256 == original.sha256
    assert restored.size_bytes == original.size_bytes
    assert restored.media_type == original.media_type


def test_leased_state_validates_restore_and_transition_edges() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValidationError, match="attempt count"):
        LeasedWorkState.restore(
            max_attempts=2,
            attempt_count=3,
            status=WorkStatus.QUEUED,
            lease_owner=None,
            lease_token=0,
            leased_until=None,
            next_attempt_at=now,
            last_error=None,
            completed_at=None,
        )
    with pytest.raises(ValidationError, match="token"):
        LeasedWorkState.restore(
            max_attempts=2,
            attempt_count=0,
            status=WorkStatus.QUEUED,
            lease_owner=None,
            lease_token=-1,
            leased_until=None,
            next_attempt_at=now,
            last_error=None,
            completed_at=None,
        )

    invalid_states = (
        {
            "status": WorkStatus.LEASED,
            "attempt_count": 0,
            "lease_owner": None,
            "leased_until": None,
            "next_attempt_at": None,
            "last_error": None,
            "completed_at": None,
        },
        {
            "status": WorkStatus.QUEUED,
            "attempt_count": 0,
            "lease_owner": "worker-01",
            "leased_until": now,
            "next_attempt_at": now,
            "last_error": None,
            "completed_at": None,
        },
        {
            "status": WorkStatus.QUEUED,
            "attempt_count": 0,
            "lease_owner": None,
            "leased_until": None,
            "next_attempt_at": None,
            "last_error": None,
            "completed_at": None,
        },
        {
            "status": WorkStatus.LEASED,
            "attempt_count": 1,
            "lease_owner": "worker-01",
            "leased_until": now,
            "next_attempt_at": now,
            "last_error": None,
            "completed_at": None,
        },
        {
            "status": WorkStatus.RETRY_WAIT,
            "attempt_count": 1,
            "lease_owner": None,
            "leased_until": None,
            "next_attempt_at": now,
            "last_error": None,
            "completed_at": None,
        },
        {
            "status": WorkStatus.DEAD_LETTER,
            "attempt_count": 1,
            "lease_owner": None,
            "leased_until": None,
            "next_attempt_at": None,
            "last_error": "failed",
            "completed_at": None,
        },
        {
            "status": WorkStatus.COMPLETED,
            "attempt_count": 1,
            "lease_owner": None,
            "leased_until": None,
            "next_attempt_at": None,
            "last_error": None,
            "completed_at": None,
        },
        {
            "status": WorkStatus.QUEUED,
            "attempt_count": 0,
            "lease_owner": None,
            "leased_until": None,
            "next_attempt_at": now,
            "last_error": None,
            "completed_at": now,
        },
    )
    for values in invalid_states:
        with pytest.raises(ValidationError):
            LeasedWorkState.restore(max_attempts=2, lease_token=0, **values)

    initial = LeasedWorkState.initial(2, now)
    with pytest.raises(ConflictError, match="not claimable"):
        initial.claim("worker-01", 5, now).claim("worker-02", 5, now)
    leased = initial.claim("worker-01", 5, now)
    renewed = leased.renew("worker-01", 1, 10, now + timedelta(seconds=1))
    assert renewed.leased_until == now + timedelta(seconds=11)
    with pytest.raises(ConflictError, match="expired"):
        leased.renew("worker-01", 1, 5, now + timedelta(seconds=5))
    with pytest.raises(ConflictError, match="not leased"):
        initial.complete("worker-01", 0, now)
    with pytest.raises(ConflictError, match="stale"):
        leased.complete("worker-02", 1, now + timedelta(seconds=1))
    with pytest.raises(ConflictError, match="only leased"):
        initial.expire_final_lease(now)
    with pytest.raises(ConflictError, match="not expired"):
        leased.expire_final_lease(now)
    with pytest.raises(ConflictError, match="retry attempts"):
        leased.expire_final_lease(now + timedelta(seconds=5))
    with pytest.raises(ConflictError, match="only dead-letter"):
        initial.replay(now)

    assert initial.as_dict() == LeasedWorkState.from_dict(initial.as_dict()).as_dict()
    initial.assert_transition_from(initial)
    with pytest.raises(ConflictError, match="max_attempts"):
        LeasedWorkState.initial(3, now).assert_transition_from(initial)
    with pytest.raises(ConflictError, match="fencing token"):
        LeasedWorkState.restore(
            max_attempts=2,
            attempt_count=1,
            status=WorkStatus.LEASED,
            lease_owner="worker-01",
            lease_token=0,
            leased_until=now + timedelta(seconds=10),
            next_attempt_at=None,
            last_error=None,
            completed_at=None,
        ).assert_transition_from(leased)


def test_job_roundtrip_idempotent_completion_and_persistence_guards() -> None:
    from dataclasses import replace

    now = datetime(2026, 1, 1, tzinfo=UTC)
    job = AsyncJob.create(
        tenant_id=TenantId.from_value("default"),
        specialization=WorkerSpecialization.REPORTING,
        operation="reporting.async-queue-health",
        idempotency_key="request-002",
        payload_artifact=artifact(),
        max_attempts=2,
        requested_by="tester",
        now=now,
    )
    assert AsyncJob.from_dict(job.as_dict()) == job
    with pytest.raises(ValidationError, match="artifact metadata"):
        AsyncJob.from_dict({**job.as_dict(), "payload_artifact": "invalid"})
    with pytest.raises(ValidationError, match="precede"):
        AsyncJob.restore(
            job_id=job.id,
            tenant_id=job.tenant_id,
            specialization=job.specialization,
            operation=job.operation,
            idempotency_key=job.idempotency_key,
            payload_artifact=job.payload_artifact,
            result_artifact=None,
            requested_by=job.requested_by,
            state=job.state,
            created_at=now,
            updated_at=now - timedelta(seconds=1),
        )
    with pytest.raises(ValidationError, match="non-completed"):
        AsyncJob.restore(
            job_id=job.id,
            tenant_id=job.tenant_id,
            specialization=job.specialization,
            operation=job.operation,
            idempotency_key=job.idempotency_key,
            payload_artifact=job.payload_artifact,
            result_artifact=artifact(),
            requested_by=job.requested_by,
            state=job.state,
            created_at=now,
            updated_at=now,
        )

    result = ArtifactReference.create(
        object_key="default/async-result/bb/" + "b" * 64 + ".json",
        sha256="b" * 64,
        size_bytes=2,
        media_type="application/json",
        created_at=now,
    )
    completed = job.claim("worker-01", 5, now).complete(
        "worker-01", 1, result, now + timedelta(seconds=1)
    )
    assert completed.complete("worker-01", 1, result, now + timedelta(seconds=2)) == completed
    with pytest.raises(ConflictError, match="completion conflicts"):
        completed.complete("worker-01", 1, artifact(), now + timedelta(seconds=2))
    with pytest.raises(ConflictError, match="immutable"):
        replace(completed, requested_by="other").assert_persistence_transition_from(completed)
    with pytest.raises(ConflictError, match="stale"):
        replace(completed, updated_at=now).assert_persistence_transition_from(completed)


def test_outbox_roundtrip_lifecycle_and_persistence_guards() -> None:
    from dataclasses import replace

    now = datetime(2026, 1, 1, tzinfo=UTC)
    tenant = TenantId.from_value("default")
    event = OutboxEvent.create(
        tenant_id=tenant,
        aggregate_type="async-job",
        aggregate_id="job-001",
        event_name="async.job.submitted",
        idempotency_key="event-002",
        payload={"job_id": "job-001"},
        max_attempts=2,
        now=now,
    )
    assert OutboxEvent.from_dict(event.as_dict()) == event
    with pytest.raises(ValidationError, match="object"):
        OutboxEvent.from_dict({**event.as_dict(), "payload": "invalid"})
    invalid = (
        {"aggregate_type": "?"},
        {"aggregate_id": ""},
        {"event_name": "?"},
        {"payload": {"bad": object()}},
        {"updated_at": now - timedelta(seconds=1)},
    )
    for override in invalid:
        values = {
            "event_id": event.id,
            "tenant_id": tenant,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "event_name": event.event_name,
            "idempotency_key": event.idempotency_key,
            "payload": event.payload,
            "state": event.state,
            "created_at": now,
            "updated_at": now,
        }
        values.update(override)
        with pytest.raises(ValidationError):
            OutboxEvent.restore(**values)

    leased = event.claim("outbox-01", 5, now)
    renewed = leased.renew("outbox-01", 1, 10, now + timedelta(seconds=1))
    retry = renewed.fail("outbox-01", 1, "temporary", 0, now + timedelta(seconds=2))
    leased_again = retry.claim("outbox-02", 5, now + timedelta(seconds=2))
    dead = leased_again.fail("outbox-02", 2, "permanent", 0, now + timedelta(seconds=3))
    replayed = dead.replay(now + timedelta(seconds=4))
    assert replayed.state.status is WorkStatus.QUEUED
    published = replayed.claim("outbox-03", 5, now + timedelta(seconds=4)).mark_published(
        "outbox-03", 3, now + timedelta(seconds=5)
    )
    assert published.mark_published("outbox-03", 3, now + timedelta(seconds=6)) == published

    final_lease = OutboxEvent.create(
        tenant_id=tenant,
        aggregate_type="async-job",
        aggregate_id="job-002",
        event_name="async.job.submitted",
        idempotency_key="event-003",
        payload={},
        max_attempts=1,
        now=now,
    ).claim("outbox-01", 5, now)
    assert (
        final_lease.expire_final_lease(now + timedelta(seconds=5)).state.status
        is WorkStatus.DEAD_LETTER
    )
    with pytest.raises(ConflictError, match="immutable"):
        replace(event, event_name="async.job.changed").assert_persistence_transition_from(event)
    with pytest.raises(ConflictError, match="stale"):
        replace(renewed, updated_at=now).assert_persistence_transition_from(renewed)


def test_completed_job_requires_result_and_replacement_lease_must_advance() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    tenant = TenantId.from_value("default")
    queued = AsyncJob.create(
        tenant_id=tenant,
        specialization=WorkerSpecialization.REPORTING,
        operation="reporting.async-queue-health",
        idempotency_key="replacement-lease-001",
        payload_artifact=artifact(),
        max_attempts=3,
        requested_by="tester",
        now=now,
    )
    leased = queued.state.claim("worker-01", 30, now)
    completed_state = leased.complete("worker-01", leased.lease_token, now + timedelta(seconds=1))
    with pytest.raises(ValidationError, match="requires a result"):
        AsyncJob.restore(
            job_id=queued.id,
            tenant_id=tenant,
            specialization=queued.specialization,
            operation=queued.operation,
            idempotency_key=queued.idempotency_key,
            payload_artifact=queued.payload_artifact,
            result_artifact=None,
            requested_by=queued.requested_by,
            state=completed_state,
            created_at=now,
            updated_at=now + timedelta(seconds=1),
        )

    stale_replacement = LeasedWorkState.restore(
        max_attempts=3,
        attempt_count=leased.attempt_count + 1,
        status=WorkStatus.LEASED,
        lease_owner="worker-02",
        lease_token=leased.lease_token + 1,
        leased_until=leased.leased_until,
        next_attempt_at=None,
        last_error=None,
        completed_at=None,
    )
    with pytest.raises(ConflictError, match="replacement lease is stale"):
        stale_replacement.assert_transition_from(leased)
