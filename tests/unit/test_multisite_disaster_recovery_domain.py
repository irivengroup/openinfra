from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.multisite import (
    DisasterRecoveryDrillStatus,
    DisasterRecoveryReplicationMode,
    MultisiteDisasterRecoveryDrill,
    MultisiteDisasterRecoveryPlan,
)


def _plan() -> MultisiteDisasterRecoveryPlan:
    return MultisiteDisasterRecoveryPlan.create(
        TenantId.from_value("default"),
        "Paris to London",
        "PAR1",
        "LON1",
        "async",
        300,
        1800,
        86400,
        "pytest",
        datetime(2026, 7, 11, 8, tzinfo=UTC),
    )


def test_dr_plan_lifecycle_restore_and_serialization() -> None:
    plan = _plan()
    assert plan.replication_mode is DisasterRecoveryReplicationMode.ASYNCHRONOUS
    assert plan.as_dict()["primary_site_code"] == "PAR1"

    revised = plan.revise(
        name="Paris to London critical",
        replication_mode="sync",
        rpo_seconds=60,
        rto_seconds=600,
        max_backup_age_seconds=3600,
        configured_by="dr-admin",
        now=datetime(2026, 7, 11, 9, tzinfo=UTC),
    )
    assert revised.id == plan.id
    assert revised.created_at == plan.created_at
    assert revised.replication_mode is DisasterRecoveryReplicationMode.SYNCHRONOUS

    disabled = revised.disable("dr-admin", datetime(2026, 7, 11, 10, tzinfo=UTC))
    assert disabled.active is False and disabled.disabled_at is not None
    assert disabled.disable("dr-admin") == disabled
    restored = MultisiteDisasterRecoveryPlan.restore(
        id=disabled.id,
        tenant_id=disabled.tenant_id,
        name=disabled.name,
        primary_site_code=disabled.primary_site_code,
        recovery_site_code=disabled.recovery_site_code,
        replication_mode=disabled.replication_mode,
        rpo_seconds=disabled.rpo_seconds,
        rto_seconds=disabled.rto_seconds,
        max_backup_age_seconds=disabled.max_backup_age_seconds,
        active=disabled.active,
        configured_by=disabled.configured_by,
        created_at=disabled.created_at,
        updated_at=disabled.updated_at,
        disabled_at=disabled.disabled_at,
    )
    assert restored == disabled


def test_dr_plan_validation_guards() -> None:
    tenant = TenantId.from_value("default")
    arguments = (tenant, "Valid plan", "PAR1", "LON1", "async", 300, 1800, 86400, "pytest")
    with pytest.raises(ValidationError, match="3 to 128"):
        MultisiteDisasterRecoveryPlan.create(
            tenant, "x", "PAR1", "LON1", "async", 300, 1800, 86400, "pytest"
        )
    with pytest.raises(ValidationError, match="different"):
        MultisiteDisasterRecoveryPlan.create(
            tenant, "Valid plan", "PAR1", "PAR1", "async", 300, 1800, 86400, "pytest"
        )
    with pytest.raises(ValidationError, match="replication mode"):
        MultisiteDisasterRecoveryPlan.create(*arguments[:4], "streaming", *arguments[5:])
    with pytest.raises(ValidationError, match="RPO"):
        MultisiteDisasterRecoveryPlan.create(*arguments[:5], 0, *arguments[6:])
    with pytest.raises(ValidationError, match="RTO"):
        MultisiteDisasterRecoveryPlan.create(*arguments[:6], 0, *arguments[7:])
    with pytest.raises(ValidationError, match="maximum backup age"):
        MultisiteDisasterRecoveryPlan.create(*arguments[:7], 30, *arguments[8:])
    with pytest.raises(ValidationError, match="active state"):
        MultisiteDisasterRecoveryPlan.restore(
            id=EntityId.new(),
            tenant_id=tenant,
            name="Valid plan",
            primary_site_code="PAR1",
            recovery_site_code="LON1",
            replication_mode="async",
            rpo_seconds=300,
            rto_seconds=1800,
            max_backup_age_seconds=86400,
            active=False,
            configured_by="pytest",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            disabled_at=None,
        )


def test_dr_drill_pass_failure_restore_and_guards() -> None:
    plan = _plan()
    passed = MultisiteDisasterRecoveryDrill.execute_site_loss(
        plan,
        replication_lag_seconds=120,
        backup_age_seconds=3600,
        measured_rto_seconds=900,
        restore_verified=True,
        recovery_available=True,
        vip_reachable=True,
        operator_confirmed=True,
        executed_by="pytest",
        now=datetime(2026, 7, 11, 11, tzinfo=UTC),
    )
    assert passed.status is DisasterRecoveryDrillStatus.PASSED
    assert passed.failure_reasons == ()
    assert passed.measured_rpo_seconds == 120

    failed = MultisiteDisasterRecoveryDrill.execute_site_loss(
        plan,
        replication_lag_seconds=301,
        backup_age_seconds=86401,
        measured_rto_seconds=1801,
        restore_verified=False,
        recovery_available=False,
        vip_reachable=False,
        operator_confirmed=False,
        executed_by="pytest",
    )
    assert failed.status is DisasterRecoveryDrillStatus.FAILED
    assert set(failed.failure_reasons) == {
        "operator-confirmation-missing",
        "recovery-site-unavailable",
        "restore-not-verified",
        "service-endpoint-unreachable",
        "rpo-exceeded",
        "backup-too-old",
        "rto-exceeded",
    }
    restored = MultisiteDisasterRecoveryDrill.restore(
        id=failed.id,
        tenant_id=failed.tenant_id,
        plan_id=failed.plan_id,
        scenario=failed.scenario,
        unavailable_site_code=failed.unavailable_site_code,
        recovery_site_code=failed.recovery_site_code,
        replication_lag_seconds=failed.replication_lag_seconds,
        backup_age_seconds=failed.backup_age_seconds,
        measured_rto_seconds=failed.measured_rto_seconds,
        restore_verified=failed.restore_verified,
        recovery_available=failed.recovery_available,
        vip_reachable=failed.vip_reachable,
        operator_confirmed=failed.operator_confirmed,
        status=failed.status,
        failure_reasons=failed.failure_reasons,
        executed_by=failed.executed_by,
        executed_at=failed.executed_at,
    )
    assert restored == failed

    with pytest.raises(ValidationError, match="non-negative"):
        MultisiteDisasterRecoveryDrill.execute_site_loss(
            plan,
            replication_lag_seconds=-1,
            backup_age_seconds=0,
            measured_rto_seconds=0,
            restore_verified=True,
            recovery_available=True,
            vip_reachable=True,
            operator_confirmed=True,
            executed_by="pytest",
        )
    with pytest.raises(ValidationError, match="active plan"):
        MultisiteDisasterRecoveryDrill.execute_site_loss(
            plan.disable("pytest"),
            replication_lag_seconds=0,
            backup_age_seconds=0,
            measured_rto_seconds=0,
            restore_verified=True,
            recovery_available=True,
            vip_reachable=True,
            operator_confirmed=True,
            executed_by="pytest",
        )
    with pytest.raises(ValidationError, match="unsupported DR drill scenario"):
        MultisiteDisasterRecoveryDrill.restore(
            id=EntityId.new(),
            tenant_id=plan.tenant_id,
            plan_id=plan.id,
            scenario="regional-network-loss",
            unavailable_site_code="PAR1",
            recovery_site_code="LON1",
            replication_lag_seconds=0,
            backup_age_seconds=0,
            measured_rto_seconds=0,
            restore_verified=True,
            recovery_available=True,
            vip_reachable=True,
            operator_confirmed=True,
            status="passed",
            failure_reasons=(),
            executed_by="pytest",
            executed_at=datetime.now(UTC),
        )
    with pytest.raises(ValidationError, match="passed or failed"):
        MultisiteDisasterRecoveryDrill.restore(
            id=EntityId.new(),
            tenant_id=plan.tenant_id,
            plan_id=plan.id,
            scenario="primary-site-loss",
            unavailable_site_code="PAR1",
            recovery_site_code="LON1",
            replication_lag_seconds=0,
            backup_age_seconds=0,
            measured_rto_seconds=0,
            restore_verified=True,
            recovery_available=True,
            vip_reachable=True,
            operator_confirmed=True,
            status="unknown",
            failure_reasons=(),
            executed_by="pytest",
            executed_at=datetime.now(UTC),
        )
    with pytest.raises(ValidationError, match="status and failure"):
        MultisiteDisasterRecoveryDrill.restore(
            id=EntityId.new(),
            tenant_id=plan.tenant_id,
            plan_id=plan.id,
            scenario="primary-site-loss",
            unavailable_site_code="PAR1",
            recovery_site_code="LON1",
            replication_lag_seconds=0,
            backup_age_seconds=0,
            measured_rto_seconds=0,
            restore_verified=True,
            recovery_available=True,
            vip_reachable=True,
            operator_confirmed=True,
            status="passed",
            failure_reasons=("unexpected",),
            executed_by="pytest",
            executed_at=datetime.now(UTC),
        )
