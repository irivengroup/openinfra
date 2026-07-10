from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    ClaimDiscoveryJobCommand,
    CompleteDiscoveryJobCommand,
    FailDiscoveryJobCommand,
    GetDiscoveryJobCommand,
    ListDiscoveryJobsCommand,
    RegisterCollectorCommand,
    ReplayDiscoveryDeadLetterJobCommand,
    SubmitDiscoveryJobCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError, EntityId, TenantId, ValidationError
from openinfra.domain.discovery import DiscoveryScope
from openinfra.domain.discovery_jobs import DiscoveryJob, DiscoveryJobStatus

FINGERPRINT = "a" * 64


def _application(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="discovery-admin",
            roles=("security:admin",),
            token=token,
        )
    )
    collector = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Resilient collector",
            kind="ssh",
            certificate_fingerprint=FINGERPRINT,
            scopes=("site/par1",),
            version="0.29.83",
        )
    )
    return app, token, collector


def test_discovery_job_service_retry_dlq_replay_and_completion(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    command = SubmitDiscoveryJobCommand(
        tenant_id="default",
        actor="pytest",
        admin_token=token,
        collector_id=collector.id.value,
        requested_scope="site/par1",
        job_type="ssh-inventory",
        target="srv-app-01",
        idempotency_key="job/par1/srv-app-01/0001",
        max_attempts=2,
    )
    submitted = app.discovery_service.submit_job(command)
    duplicate = app.discovery_service.submit_job(command)
    assert duplicate.id == submitted.id

    first = app.discovery_service.claim_job(
        ClaimDiscoveryJobCommand(
            "default", collector.id.value, FINGERPRINT, "worker-a", lease_seconds=60
        )
    )
    assert first is not None
    retrying = app.discovery_service.fail_job(
        FailDiscoveryJobCommand(
            "default",
            collector.id.value,
            FINGERPRINT,
            first.id.value,
            "worker-a",
            first.lease_token,
            "temporary timeout",
            retry_delay_seconds=0,
        )
    )
    assert retrying.status is DiscoveryJobStatus.RETRY_WAIT

    second = app.discovery_service.claim_job(
        ClaimDiscoveryJobCommand(
            "default", collector.id.value, FINGERPRINT, "worker-b", lease_seconds=60
        )
    )
    assert second is not None
    dead_letter = app.discovery_service.fail_job(
        FailDiscoveryJobCommand(
            "default",
            collector.id.value,
            FINGERPRINT,
            second.id.value,
            "worker-b",
            second.lease_token,
            "permanent failure",
            retry_delay_seconds=0,
        )
    )
    assert dead_letter.status is DiscoveryJobStatus.DEAD_LETTER

    replayed = app.discovery_service.replay_dead_letter_job(
        ReplayDiscoveryDeadLetterJobCommand("default", "pytest", token, dead_letter.id.value)
    )
    third = app.discovery_service.claim_job(
        ClaimDiscoveryJobCommand(
            "default", collector.id.value, FINGERPRINT, "worker-c", lease_seconds=60
        )
    )
    assert third is not None
    assert third.id == replayed.id
    completed = app.discovery_service.complete_job(
        CompleteDiscoveryJobCommand(
            "default",
            collector.id.value,
            FINGERPRINT,
            third.id.value,
            "worker-c",
            third.lease_token,
            "d" * 64,
        )
    )

    assert completed.status is DiscoveryJobStatus.COMPLETED
    assert (
        app.discovery_service.get_job(GetDiscoveryJobCommand("default", token, completed.id.value))
        == completed
    )
    assert (
        len(
            app.discovery_service.list_jobs(
                ListDiscoveryJobsCommand("default", token, status="completed")
            ).items
        )
        == 1
    )
    actions = [event.action for event in app.audit_repository.list_events()]
    assert "discovery.job.dead-lettered" in actions
    assert "discovery.job.replayed" in actions
    assert "discovery.job.completed" in actions


def test_json_repository_reclaims_crashed_worker_without_job_loss(tmp_path: Path) -> None:
    app, _, collector = _application(tmp_path)
    tenant_id = TenantId.from_value("default")
    start = datetime.now(UTC) - timedelta(minutes=1)
    job = DiscoveryJob.create(
        tenant_id=tenant_id,
        collector_id=collector.id,
        requested_scope=DiscoveryScope.from_value("site/par1"),
        job_type="ssh-inventory",
        target="srv-db-01",
        idempotency_key="job/par1/srv-db-01/0001",
        max_attempts=3,
        requested_by="pytest",
        created_at=start,
    )
    app.discovery_repository.save_job(job)
    first_result = app.discovery_repository.claim_next_job(
        tenant_id,
        collector.id,
        "worker-crashed",
        5,
        start + timedelta(seconds=1),
    )
    first = first_result.job
    assert first is not None
    recovered_result = app.discovery_repository.claim_next_job(
        tenant_id,
        collector.id,
        "worker-recovery",
        30,
        start + timedelta(seconds=10),
    )
    recovered = recovered_result.job

    assert recovered is not None
    assert recovered.id == job.id
    assert recovered.lease_token == 2
    assert recovered.attempt_count == 2
    assert recovered.lease_owner == "worker-recovery"
    with pytest.raises(ConflictError, match="fencing token"):
        recovered.complete(
            worker_id="worker-crashed",
            lease_token=1,
            result_hash="e" * 64,
            now=start + timedelta(seconds=11),
        )


def test_discovery_job_rejects_wrong_collector_identity(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    app.discovery_service.submit_job(
        SubmitDiscoveryJobCommand(
            "default",
            "pytest",
            token,
            collector.id.value,
            "site/par1",
            "ssh-inventory",
            "srv-app-02",
            "job/par1/srv-app-02/0001",
        )
    )

    with pytest.raises(Exception, match="authentication rejected"):
        app.discovery_service.claim_job(
            ClaimDiscoveryJobCommand("default", collector.id.value, "f" * 64, "worker-a", 60)
        )

    assert (
        app.discovery_repository.get_job(TenantId.from_value("default"), str(EntityId.new().value))
        is None
    )


def test_json_repository_claims_jobs_once_under_concurrency(tmp_path: Path) -> None:
    app, _, collector = _application(tmp_path)
    tenant_id = TenantId.from_value("default")
    created_at = datetime.now(UTC)
    expected_ids: set[str] = set()
    for index in range(24):
        job = DiscoveryJob.create(
            tenant_id=tenant_id,
            collector_id=collector.id,
            requested_scope=DiscoveryScope.from_value("site/par1"),
            job_type="ssh-inventory",
            target=f"srv-{index:03d}",
            idempotency_key=f"concurrent-job-{index:03d}",
            max_attempts=3,
            requested_by="pytest",
            created_at=created_at,
        )
        expected_ids.add(job.id.value)
        app.discovery_repository.save_job(job)

    def claim_all(worker_index: int) -> list[str]:
        claimed_ids: list[str] = []
        while True:
            result = app.discovery_repository.claim_next_job(
                tenant_id,
                collector.id,
                f"worker-{worker_index}",
                60,
                created_at + timedelta(seconds=1),
            )
            if result.job is None:
                return claimed_ids
            claimed_ids.append(result.job.id.value)

    with ThreadPoolExecutor(max_workers=8) as executor:
        batches = list(executor.map(claim_all, range(8)))

    claimed_ids = [job_id for batch in batches for job_id in batch]
    assert len(claimed_ids) == 24
    assert len(set(claimed_ids)) == 24
    assert set(claimed_ids) == expected_ids


def test_expired_final_attempt_moves_to_dlq_and_is_audited(tmp_path: Path) -> None:
    app, _, collector = _application(tmp_path)
    tenant_id = TenantId.from_value("default")
    start = datetime.now(UTC) - timedelta(minutes=2)
    job = DiscoveryJob.create(
        tenant_id=tenant_id,
        collector_id=collector.id,
        requested_scope=DiscoveryScope.from_value("site/par1"),
        job_type="ssh-inventory",
        target="srv-final-crash",
        idempotency_key="final-crash-job-0001",
        max_attempts=1,
        requested_by="pytest",
        created_at=start,
    )
    app.discovery_repository.save_job(job)
    first = app.discovery_repository.claim_next_job(
        tenant_id, collector.id, "worker-final", 5, start + timedelta(seconds=1)
    ).job
    assert first is not None

    claimed = app.discovery_service.claim_job(
        ClaimDiscoveryJobCommand(
            "default", collector.id.value, FINGERPRINT, "worker-recovery", lease_seconds=60
        )
    )

    assert claimed is None
    persisted = app.discovery_repository.get_job(tenant_id, job.id.value)
    assert persisted is not None
    assert persisted.status is DiscoveryJobStatus.DEAD_LETTER
    assert persisted.last_error == "lease expired after final attempt"
    events = [
        event
        for event in app.audit_repository.list_events()
        if event.target_id == job.id.value and event.action == "discovery.job.dead-lettered"
    ]
    assert len(events) == 1
    assert events[0].metadata["reason"] == "lease_expired_after_final_attempt"


def test_json_repository_rejects_competing_terminal_updates_with_same_fencing_token(
    tmp_path: Path,
) -> None:
    app, _, collector = _application(tmp_path)
    tenant_id = TenantId.from_value("default")
    start = datetime.now(UTC)
    job = DiscoveryJob.create(
        tenant_id=tenant_id,
        collector_id=collector.id,
        requested_scope=DiscoveryScope.from_value("site/par1"),
        job_type="ssh-inventory",
        target="srv-race",
        idempotency_key="terminal-race-job-0001",
        max_attempts=2,
        requested_by="pytest",
        created_at=start,
    )
    app.discovery_repository.save_job(job)
    leased = app.discovery_repository.claim_next_job(
        tenant_id, collector.id, "worker-race", 60, start + timedelta(seconds=1)
    ).job
    assert leased is not None
    completed = leased.complete(
        worker_id="worker-race",
        lease_token=leased.lease_token,
        result_hash="b" * 64,
        now=start + timedelta(seconds=2),
    )
    retrying = leased.fail(
        worker_id="worker-race",
        lease_token=leased.lease_token,
        error="late competing failure",
        retry_delay_seconds=30,
        now=start + timedelta(seconds=3),
    )

    app.discovery_repository.save_job(completed)
    with pytest.raises(ConflictError, match="state transition"):
        app.discovery_repository.save_job(retrying)


def test_discovery_job_submission_is_idempotent_under_concurrency(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    command = SubmitDiscoveryJobCommand(
        tenant_id="default",
        actor="pytest",
        admin_token=token,
        collector_id=collector.id.value,
        requested_scope="site/par1",
        job_type="ssh-inventory",
        target="srv-idempotent",
        idempotency_key="concurrent-submission-0001",
        max_attempts=3,
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = tuple(executor.map(lambda _: app.discovery_service.submit_job(command), range(16)))

    assert len({job.id.value for job in jobs}) == 1
    persisted = app.discovery_service.list_jobs(ListDiscoveryJobsCommand("default", token)).items
    assert len(persisted) == 1
    submitted_events = [
        event
        for event in app.audit_repository.list_events()
        if event.action == "discovery.job.submitted"
    ]
    assert len(submitted_events) == 1


def test_discovery_job_service_negative_contracts(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    unknown_collector = EntityId.new().value
    with pytest.raises(ValidationError, match="submission rejected"):
        app.discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                "default",
                "pytest",
                token,
                unknown_collector,
                "site/par1",
                "ssh-inventory",
                "srv-unknown",
                "unknown-collector-job-0001",
            )
        )

    original = SubmitDiscoveryJobCommand(
        "default",
        "pytest",
        token,
        collector.id.value,
        "site/par1",
        "ssh-inventory",
        "srv-original",
        "conflicting-job-key-0001",
    )
    app.discovery_service.submit_job(original)
    with pytest.raises(ValidationError, match="idempotency key conflicts"):
        app.discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                "default",
                "pytest",
                token,
                collector.id.value,
                "site/par1",
                "ssh-inventory",
                "srv-different",
                "conflicting-job-key-0001",
            )
        )

    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.get_job(
            GetDiscoveryJobCommand("default", token, EntityId.new().value)
        )
    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.replay_dead_letter_job(
            ReplayDiscoveryDeadLetterJobCommand("default", "pytest", token, EntityId.new().value)
        )


def test_discovery_job_completion_is_idempotent_through_service(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    submitted = app.discovery_service.submit_job(
        SubmitDiscoveryJobCommand(
            "default",
            "pytest",
            token,
            collector.id.value,
            "site/par1",
            "ssh-inventory",
            "srv-idempotent-completion",
            "idempotent-completion-job-0001",
        )
    )
    claimed = app.discovery_service.claim_job(
        ClaimDiscoveryJobCommand(
            "default", collector.id.value, FINGERPRINT, "worker-idempotent", 60
        )
    )
    assert claimed is not None and claimed.id == submitted.id
    command = CompleteDiscoveryJobCommand(
        "default",
        collector.id.value,
        FINGERPRINT,
        claimed.id.value,
        "worker-idempotent",
        claimed.lease_token,
        "f" * 64,
    )
    first = app.discovery_service.complete_job(command)
    second = app.discovery_service.complete_job(command)
    assert second == first


def test_discovery_worker_rejects_wrong_collector_and_scope(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    second_fingerprint = "b" * 64
    second = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Second collector",
            kind="ssh",
            certificate_fingerprint=second_fingerprint,
            scopes=("site/par1",),
            version="0.29.83",
        )
    )
    submitted = app.discovery_service.submit_job(
        SubmitDiscoveryJobCommand(
            "default",
            "pytest",
            token,
            collector.id.value,
            "site/par1",
            "ssh-inventory",
            "srv-owned",
            "collector-owner-job-0001",
        )
    )
    with pytest.raises(ValidationError, match="assigned to another collector"):
        app.discovery_service.complete_job(
            CompleteDiscoveryJobCommand(
                "default",
                second.id.value,
                second_fingerprint,
                submitted.id.value,
                "worker-second",
                1,
                "a" * 64,
            )
        )

    out_of_scope = DiscoveryJob.create(
        tenant_id=TenantId.from_value("default"),
        collector_id=collector.id,
        requested_scope=DiscoveryScope.from_value("site/lon1"),
        job_type="ssh-inventory",
        target="srv-out-of-scope",
        idempotency_key="out-of-scope-job-0001",
        max_attempts=2,
        requested_by="pytest",
    )
    app.discovery_repository.save_job(out_of_scope)
    with pytest.raises(ValidationError, match="worker operation rejected"):
        app.discovery_service.complete_job(
            CompleteDiscoveryJobCommand(
                "default",
                collector.id.value,
                FINGERPRINT,
                out_of_scope.id.value,
                "worker-a",
                1,
                "a" * 64,
            )
        )


def test_discovery_submission_recovers_from_concurrent_insert_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, token, collector = _application(tmp_path)
    captured: dict[str, DiscoveryJob] = {}

    def conflict_after_candidate(job: DiscoveryJob) -> None:
        captured["job"] = job
        raise ConflictError("simulated concurrent insert")

    monkeypatch.setattr(app.discovery_repository, "save_job", conflict_after_candidate)
    monkeypatch.setattr(
        app.discovery_service,
        "_find_job_by_idempotency_key",
        lambda tenant_id, key: captured.get("job"),
    )
    command = SubmitDiscoveryJobCommand(
        "default",
        "pytest",
        token,
        collector.id.value,
        "site/par1",
        "ssh-inventory",
        "srv-race-recovery",
        "race-recovery-job-0001",
    )

    recovered = app.discovery_service.submit_job(command)
    assert recovered == captured["job"]


def test_discovery_submission_rejects_conflicting_concurrent_insert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, token, collector = _application(tmp_path)
    captured: dict[str, DiscoveryJob] = {}

    def conflict_after_candidate(job: DiscoveryJob) -> None:
        captured["job"] = job
        raise ConflictError("simulated concurrent insert")

    monkeypatch.setattr(app.discovery_repository, "save_job", conflict_after_candidate)
    monkeypatch.setattr(
        app.discovery_service,
        "_find_job_by_idempotency_key",
        lambda tenant_id, key: replace(captured["job"], target="srv-conflict"),
    )
    with pytest.raises(ValidationError, match="idempotency key conflicts"):
        app.discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                "default",
                "pytest",
                token,
                collector.id.value,
                "site/par1",
                "ssh-inventory",
                "srv-race-conflict",
                "race-conflict-job-0001",
            )
        )


def test_discovery_submission_propagates_unresolved_repository_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, token, collector = _application(tmp_path)

    def conflict(_job: DiscoveryJob) -> None:
        raise ConflictError("unresolved conflict")

    monkeypatch.setattr(app.discovery_repository, "save_job", conflict)
    monkeypatch.setattr(
        app.discovery_service,
        "_find_job_by_idempotency_key",
        lambda tenant_id, key: None,
    )
    with pytest.raises(ConflictError, match="unresolved conflict"):
        app.discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                "default",
                "pytest",
                token,
                collector.id.value,
                "site/par1",
                "ssh-inventory",
                "srv-unresolved",
                "unresolved-conflict-job-0001",
            )
        )


def test_discovery_submission_propagates_conflict_before_candidate_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, token, collector = _application(tmp_path)

    def collector_conflict(_tenant_id: TenantId, _collector_id: str):
        raise ConflictError("collector lookup conflict")

    monkeypatch.setattr(app.discovery_repository, "get_collector", collector_conflict)
    with pytest.raises(ConflictError, match="collector lookup conflict"):
        app.discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                "default",
                "pytest",
                token,
                collector.id.value,
                "site/par1",
                "ssh-inventory",
                "srv-no-candidate",
                "no-candidate-job-0001",
            )
        )


def test_discovery_idempotency_lookup_uses_transaction_boundary(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    submitted = app.discovery_service.submit_job(
        SubmitDiscoveryJobCommand(
            "default",
            "pytest",
            token,
            collector.id.value,
            "site/par1",
            "ssh-inventory",
            "srv-lookup",
            "lookup-job-key-0001",
        )
    )
    found = app.discovery_service._find_job_by_idempotency_key(
        TenantId.from_value("default"), submitted.idempotency_key
    )
    assert found == submitted


def test_discovery_job_limited_runtime_checks_feature_and_quota(tmp_path: Path) -> None:
    app, token, collector = _application(tmp_path)
    calls: list[str] = []

    class AllowingLimitedRuntimeGuard:
        limited_runtime = True

        def require_feature(self, *_args: object) -> None:
            calls.append("feature")

        def require_quota(self, *_args: object) -> None:
            calls.append("quota")

    app.discovery_service._edition_guard = AllowingLimitedRuntimeGuard()
    app.discovery_service.submit_job(
        SubmitDiscoveryJobCommand(
            "default",
            "pytest",
            token,
            collector.id.value,
            "site/par1",
            "ssh-inventory",
            "srv-limited-runtime",
            "limited-runtime-job-0001",
        )
    )
    app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Limited runtime collector",
            kind="ssh",
            certificate_fingerprint="c" * 64,
            scopes=("site/par1",),
            version="0.29.83",
        )
    )

    assert calls.count("feature") == 2
    assert calls.count("quota") == 1
