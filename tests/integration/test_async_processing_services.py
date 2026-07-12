from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from openinfra.application.async_processing_services import (
    AsyncProcessingService,
    ClaimAsyncJobCommand,
    ClaimOutboxEventCommand,
    CompleteAsyncJobCommand,
    FailAsyncJobCommand,
    FailOutboxEventCommand,
    GetAsyncArtifactCommand,
    GetAsyncJobCommand,
    GetAsyncQueueMetricsCommand,
    GetOutboxEventCommand,
    ListAsyncJobsCommand,
    ListOutboxEventsCommand,
    OutboxDispatcher,
    PublishOutboxEventCommand,
    RenewAsyncJobLeaseCommand,
    RenewOutboxLeaseCommand,
    ReplayAsyncJobCommand,
    ReplayOutboxEventCommand,
    SubmitAsyncJobCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.async_processing import (
    AsyncJob,
    OutboxEvent,
    WorkerSpecialization,
    WorkStatus,
)
from openinfra.domain.common import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.infrastructure.async_processing import FileOutboxPublisher


def build_app(tmp_path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "async-admin-token-0123456789abcdef"
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "async-admin", ("admin",), token)
    )
    return app, token


def submit(app, token, *, key="health-001", max_attempts=3):
    return app.async_processing_service.submit_job(
        SubmitAsyncJobCommand(
            "default",
            token,
            "pytest",
            "reporting",
            "reporting.async-queue-health",
            key,
            {"scope": "all"},
            max_attempts,
        )
    )


def test_all_repository_reads_run_inside_a_unit_of_work(tmp_path) -> None:
    app, token = build_app(tmp_path)
    state = {"active": False}
    delegate = app.transaction_manager

    class GuardedUnitOfWork:
        def __init__(self) -> None:
            self._delegate = delegate.begin()

        def __enter__(self):
            self._delegate.__enter__()
            state["active"] = True
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            try:
                self._delegate.__exit__(exc_type, exc, traceback)
            finally:
                state["active"] = False

        def commit(self) -> None:
            self._delegate.commit()

        def rollback(self) -> None:
            self._delegate.rollback()

    class GuardedTransactionManager:
        @staticmethod
        def begin():
            return GuardedUnitOfWork()

    repository = app.async_processing_repository
    for method_name in (
        "lock_job_idempotency",
        "find_job_by_idempotency_key",
        "get_job",
        "list_jobs",
        "get_outbox_event",
        "list_outbox_events",
        "queue_metrics",
    ):
        original = getattr(repository, method_name)

        def guarded(*args, _original=original, _name=method_name, **kwargs):
            assert state["active"], f"{_name} called outside unit of work"
            return _original(*args, **kwargs)

        setattr(repository, method_name, guarded)

    service = AsyncProcessingService(
        repository,
        app.artifact_store,
        app.audit_repository,
        GuardedTransactionManager(),
        app.security_service,
    )
    job = service.submit_job(
        SubmitAsyncJobCommand(
            "default",
            token,
            "pytest",
            "reporting",
            "reporting.async-queue-health",
            "uow-0001",
            {"scope": "all"},
        )
    )
    assert service.get_job(GetAsyncJobCommand("default", token, job.id.value)) == job
    assert service.list_jobs(ListAsyncJobsCommand("default", token)).items == (job,)
    assert service.get_artifact(
        GetAsyncArtifactCommand("default", token, job.id.value, "payload")
    ).content
    events = service.list_outbox_events(ListOutboxEventsCommand("default", token))
    assert (
        service.get_outbox_event(GetOutboxEventCommand("default", token, events.items[0].id.value))
        == events.items[0]
    )
    assert service.queue_metrics(GetAsyncQueueMetricsCommand("default", token))["jobs"]


def test_concurrent_submissions_share_one_job_and_one_outbox_event(tmp_path) -> None:
    app, token = build_app(tmp_path)

    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = tuple(executor.map(lambda _: submit(app, token, key="concurrent-001"), range(24)))

    assert len({job.id.value for job in jobs}) == 1
    page = app.async_processing_service.list_jobs(ListAsyncJobsCommand("default", token))
    events = app.async_processing_service.list_outbox_events(
        ListOutboxEventsCommand("default", token)
    )
    assert len(page.items) == 1
    assert len(events.items) == 1
    assert events.items[0].aggregate_id == page.items[0].id.value


def test_submit_is_idempotent_and_creates_atomic_outbox(tmp_path) -> None:
    app, token = build_app(tmp_path)
    first = submit(app, token)
    second = submit(app, token)
    assert second.id == first.id
    events = app.async_processing_service.list_outbox_events(
        ListOutboxEventsCommand("default", token)
    )
    assert len(events.items) == 1
    assert events.items[0].aggregate_id == first.id.value
    with pytest.raises(ConflictError, match="idempotency"):
        app.async_processing_service.submit_job(
            SubmitAsyncJobCommand(
                "default",
                token,
                "pytest",
                "reporting",
                "reporting.async-queue-health",
                "health-001",
                {"scope": "different"},
            )
        )


def test_reporting_worker_externalizes_result_and_dispatcher_is_idempotent(tmp_path) -> None:
    app, token = build_app(tmp_path)
    job = submit(app, token)
    completed = app.reporting_worker.run_once(
        tenant_id="default", admin_token=token, worker_id="reporting-01"
    )
    assert completed is not None
    assert completed.id == job.id
    assert completed.state.status is WorkStatus.COMPLETED
    artifact = app.async_processing_service.get_artifact(
        GetAsyncArtifactCommand("default", token, job.id.value, "result")
    )
    report = json.loads(artifact.content)
    assert report["operation"] == "reporting.async-queue-health"
    assert report["queues"]["jobs"]["leased"] == 1

    sink = tmp_path / "events"
    dispatcher = OutboxDispatcher(app.async_processing_service, FileOutboxPublisher(sink))
    published = []
    while True:
        event = dispatcher.run_once(tenant_id="default", admin_token=token, worker_id="outbox-01")
        if event is None:
            break
        published.append(event)
    assert len(published) == 2
    assert all(event.state.status is WorkStatus.COMPLETED for event in published)
    assert len(list((sink / "default").glob("*.json"))) == 2
    assert (
        dispatcher.run_once(tenant_id="default", admin_token=token, worker_id="outbox-01") is None
    )


def test_fencing_retry_dead_letter_replay_and_restart_recovery(tmp_path) -> None:
    app, token = build_app(tmp_path)
    job = submit(app, token, max_attempts=1)
    claimed = app.async_processing_service.claim_job(
        ClaimAsyncJobCommand("default", token, "worker", "reporting", "reporting-01", 5)
    )
    assert claimed is not None
    with pytest.raises(ConflictError, match="stale"):
        app.async_processing_service.fail_job(
            FailAsyncJobCommand(
                "default",
                token,
                "worker",
                job.id.value,
                "reporting-01",
                claimed.state.lease_token + 1,
                "stale",
                0,
            )
        )

    stored = app.async_processing_repository.get_job(job.tenant_id, job.id.value)
    assert stored is not None and stored.state.leased_until is not None
    expired = stored._replace(
        stored.state.restore(
            max_attempts=1,
            attempt_count=1,
            status=WorkStatus.LEASED,
            lease_owner="reporting-01",
            lease_token=stored.state.lease_token,
            leased_until=datetime.now(UTC) - timedelta(seconds=1),
            next_attempt_at=None,
            last_error=None,
            completed_at=None,
        ),
        None,
        datetime.now(UTC),
    )
    with app.transaction_manager.begin() as unit:
        key = f"{job.tenant_id.value}:{job.id.value}"
        app.store.data["async_jobs"][key] = expired.as_dict()
        app.store.mark_dirty()
        unit.commit()

    restarted = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    assert (
        restarted.async_processing_service.claim_job(
            ClaimAsyncJobCommand("default", token, "worker", "reporting", "reporting-02", 5)
        )
        is None
    )
    dead = restarted.async_processing_repository.get_job(job.tenant_id, job.id.value)
    assert dead is not None and dead.state.status is WorkStatus.DEAD_LETTER
    replayed = restarted.async_processing_service.replay_job(
        ReplayAsyncJobCommand("default", token, "admin", job.id.value)
    )
    assert replayed.state.status is WorkStatus.QUEUED


def test_async_roles_enforce_least_privilege(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    tokens = {
        "reader": "r" * 40,
        "operator": "o" * 40,
        "worker": "w" * 40,
        "admin": "a" * 40,
    }
    for role, token in tokens.items():
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", f"async-{role}", (f"async:{role}",), token)
        )

    assert (
        app.async_processing_service.list_jobs(
            ListAsyncJobsCommand("default", tokens["reader"])
        ).items
        == ()
    )
    with pytest.raises(AccessDeniedError):
        submit(app, tokens["reader"], key="reader-denied")

    job = submit(app, tokens["operator"], key="operator-allowed")
    with pytest.raises(AccessDeniedError):
        app.async_processing_service.claim_job(
            ClaimAsyncJobCommand(
                "default", tokens["operator"], "operator", "reporting", "worker-01", 5
            )
        )

    claimed = app.async_processing_service.claim_job(
        ClaimAsyncJobCommand("default", tokens["worker"], "worker", "reporting", "worker-01", 5)
    )
    assert claimed is not None and claimed.id == job.id
    failed = app.async_processing_service.fail_job(
        FailAsyncJobCommand(
            "default",
            tokens["worker"],
            "worker",
            job.id.value,
            "worker-01",
            claimed.state.lease_token,
            "forced failure",
            0,
        )
    )
    assert failed.state.status is WorkStatus.RETRY_WAIT
    with pytest.raises(AccessDeniedError):
        app.async_processing_service.replay_job(
            ReplayAsyncJobCommand("default", tokens["worker"], "worker", job.id.value)
        )


def test_service_covers_lease_completion_artifact_and_not_found_contracts(tmp_path) -> None:
    app, token = build_app(tmp_path)
    job = submit(app, token, key="service-lifecycle-001")

    with pytest.raises(NotFoundError, match="result artifact"):
        app.async_processing_service.get_artifact(
            GetAsyncArtifactCommand("default", token, job.id.value, "result")
        )
    with pytest.raises(ValidationError, match="payload or result"):
        app.async_processing_service.get_artifact(
            GetAsyncArtifactCommand("default", token, job.id.value, "invalid")
        )
    with pytest.raises(NotFoundError, match="job"):
        app.async_processing_service.get_job(GetAsyncJobCommand("default", token, "missing-job"))
    with pytest.raises(NotFoundError, match="outbox"):
        app.async_processing_service.get_outbox_event(
            GetOutboxEventCommand("default", token, "missing-event")
        )

    claimed = app.async_processing_service.claim_job(
        ClaimAsyncJobCommand("default", token, "worker", "reporting", "worker-01", 10)
    )
    assert claimed is not None
    renewed = app.async_processing_service.renew_job_lease(
        RenewAsyncJobLeaseCommand(
            "default",
            token,
            "worker",
            job.id.value,
            "worker-01",
            claimed.state.lease_token,
            30,
        )
    )
    completed = app.async_processing_service.complete_job(
        CompleteAsyncJobCommand(
            "default",
            token,
            "worker",
            job.id.value,
            "worker-01",
            renewed.state.lease_token,
            b'{"ok":true}',
        )
    )
    assert completed.state.status is WorkStatus.COMPLETED
    assert (
        app.async_processing_service.get_artifact(
            GetAsyncArtifactCommand("default", token, job.id.value, "result")
        ).content
        == b'{"ok":true}'
    )


def test_service_outbox_retry_dead_letter_replay_and_publish(tmp_path) -> None:
    app, token = build_app(tmp_path)
    submit(app, token, key="outbox-lifecycle-001")
    claimed = app.async_processing_service.claim_outbox_event(
        ClaimOutboxEventCommand("default", token, "worker", "outbox-01", 10)
    )
    assert claimed is not None
    renewed = app.async_processing_service.renew_outbox_lease(
        RenewOutboxLeaseCommand(
            "default",
            token,
            "worker",
            claimed.id.value,
            "outbox-01",
            claimed.state.lease_token,
            30,
        )
    )
    retry = app.async_processing_service.fail_outbox_event(
        FailOutboxEventCommand(
            "default",
            token,
            "worker",
            renewed.id.value,
            "outbox-01",
            renewed.state.lease_token,
            "temporary",
            0,
        )
    )
    assert retry.state.status is WorkStatus.RETRY_WAIT
    claimed_again = app.async_processing_service.claim_outbox_event(
        ClaimOutboxEventCommand("default", token, "worker", "outbox-02", 10)
    )
    assert claimed_again is not None
    published = app.async_processing_service.mark_outbox_published(
        PublishOutboxEventCommand(
            "default",
            token,
            "worker",
            claimed_again.id.value,
            "outbox-02",
            claimed_again.state.lease_token,
        )
    )
    assert published.state.status is WorkStatus.COMPLETED

    dead_job = submit(app, token, key="outbox-dead-001", max_attempts=1)
    event = next(
        item
        for item in app.async_processing_service.list_outbox_events(
            ListOutboxEventsCommand("default", token)
        ).items
        if item.aggregate_id == dead_job.id.value
    )
    event_claimed = app.async_processing_service.claim_outbox_event(
        ClaimOutboxEventCommand("default", token, "worker", "outbox-03", 10)
    )
    assert event_claimed is not None and event_claimed.id == event.id
    dead = app.async_processing_service.fail_outbox_event(
        FailOutboxEventCommand(
            "default",
            token,
            "worker",
            event.id.value,
            "outbox-03",
            event_claimed.state.lease_token,
            "permanent",
            0,
        )
    )
    assert dead.state.status is WorkStatus.RETRY_WAIT or dead.state.status is WorkStatus.DEAD_LETTER
    # Outbox events use their own bounded retry policy; force exhaustion deterministically.
    current = dead
    while current.state.status is not WorkStatus.DEAD_LETTER:
        current = app.async_processing_service.claim_outbox_event(
            ClaimOutboxEventCommand("default", token, "worker", "outbox-03", 10)
        )
        assert current is not None
        current = app.async_processing_service.fail_outbox_event(
            FailOutboxEventCommand(
                "default",
                token,
                "worker",
                current.id.value,
                "outbox-03",
                current.state.lease_token,
                "permanent",
                0,
            )
        )
    replayed = app.async_processing_service.replay_outbox_event(
        ReplayOutboxEventCommand("default", token, "admin", current.id.value)
    )
    assert replayed.state.status is WorkStatus.QUEUED


def test_workers_convert_processing_and_publication_failures_to_retries(tmp_path) -> None:
    app, token = build_app(tmp_path)
    submit(app, token, key="worker-failure-001")

    original_read = app.artifact_store.read

    def invalid_payload(*_args):
        return b"[]"

    app.artifact_store.read = invalid_payload
    failed_job = app.reporting_worker.run_once(
        tenant_id="default", admin_token=token, worker_id="reporting-failure"
    )
    app.artifact_store.read = original_read
    assert failed_job is not None and failed_job.state.status is WorkStatus.RETRY_WAIT

    class FailingPublisher:
        @staticmethod
        def publish(_event) -> None:
            raise RuntimeError("broker unavailable")

    dispatcher = OutboxDispatcher(app.async_processing_service, FailingPublisher())
    failed_event = dispatcher.run_once(
        tenant_id="default", admin_token=token, worker_id="outbox-failure"
    )
    assert failed_event is not None and failed_event.state.status is WorkStatus.RETRY_WAIT


def test_submission_rejects_unsupported_and_non_serializable_payloads(tmp_path) -> None:
    app, token = build_app(tmp_path)
    with pytest.raises(ValidationError, match="not supported"):
        app.async_processing_service.submit_job(
            SubmitAsyncJobCommand(
                "default",
                token,
                "pytest",
                "reporting",
                "reporting.unknown",
                "unsupported-001",
                {},
            )
        )
    with pytest.raises(ValidationError, match="JSON serializable"):
        app.async_processing_service.submit_job(
            SubmitAsyncJobCommand(
                "default",
                token,
                "pytest",
                "reporting",
                "reporting.async-queue-health",
                "nonserial-001",
                {"invalid": object()},
            )
        )


def test_json_async_repository_idempotent_saves_expiry_and_pagination_guards(tmp_path) -> None:
    app, token = build_app(tmp_path)
    job = submit(app, token, key="repository-guard-001")
    repository = app.async_processing_repository

    repository.save_job(job)
    with pytest.raises(ValidationError, match="idempotency key"):
        repository.lock_job_idempotency(TenantId.from_value("default"), "  ")
    with pytest.raises(ValidationError, match="cursor"):
        repository.list_jobs(
            TenantId.from_value("default"),
            Pagination.from_values(10, "missing-cursor"),
        )

    duplicate = AsyncJob.create(
        tenant_id=job.tenant_id,
        specialization=WorkerSpecialization.REPORTING,
        operation=job.operation,
        idempotency_key=job.idempotency_key,
        payload_artifact=job.payload_artifact,
        max_attempts=3,
        requested_by="pytest",
    )
    with pytest.raises(ConflictError, match="idempotency"):
        repository.save_job(duplicate)

    events = app.async_processing_service.list_outbox_events(
        ListOutboxEventsCommand("default", token)
    ).items
    repository.save_outbox_event(events[0])
    with app.transaction_manager.begin() as unit:
        app.store.data["outbox_events"].clear()
        app.store.mark_dirty()
        unit.commit()

    now = datetime.now(UTC)
    expiring = OutboxEvent.create(
        tenant_id=TenantId.from_value("default"),
        aggregate_type="async-job",
        aggregate_id="expired-job",
        event_name="async.job.submitted",
        idempotency_key="expired-event-001",
        payload={"job_id": "expired-job"},
        max_attempts=1,
        now=now,
    ).claim("expired-worker", 5, now)
    repository.save_outbox_event(expiring)
    claimed = repository.claim_next_outbox_event(
        TenantId.from_value("default"),
        "next-worker",
        5,
        now + timedelta(seconds=5),
    )
    # Older queued events may be claimed first; the exhausted event must still be dead-lettered.
    stored = repository.get_outbox_event(TenantId.from_value("default"), expiring.id.value)
    assert stored is not None and stored.state.status is WorkStatus.DEAD_LETTER
    assert claimed is None or claimed.id != expiring.id


def test_reporting_worker_returns_none_when_queue_is_empty(tmp_path) -> None:
    app, token = build_app(tmp_path)
    assert (
        app.reporting_worker.run_once(
            tenant_id="default", admin_token=token, worker_id="empty-worker"
        )
        is None
    )
