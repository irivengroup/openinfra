from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.source_governance import (
    SourceConflictStrategy,
    SourceGovernanceEvaluator,
    SourceGovernanceRule,
)
from openinfra.domain.source_of_truth import SourceObjectKind, SourceSystem


def test_governance_rule_disabled_and_staleness_paths() -> None:
    rule = SourceGovernanceRule.create(
        tenant_id=TenantId.from_value("default"),
        name="freshness-rule",
        object_kind=None,
        attribute_path="*",
        authoritative_source="cmdb",
        priority=5,
        freshness_seconds=120,
        conflict_strategy="reject",
    )
    old_observation = datetime.now(UTC) - timedelta(minutes=10)
    disabled = rule.disabled()

    assert rule.applies_to(SourceObjectKind.DEVICE, "owner.team") is True
    assert rule.is_authoritative(SourceSystem.from_value("cmdb")) is True
    assert rule.is_stale(old_observation) is True
    assert disabled.active is False
    assert disabled.as_dict()["object_kind"] == "*"


def test_governance_validation_rejects_bad_bounds_and_naive_dates() -> None:
    with pytest.raises(ValidationError):
        SourceGovernanceRule.create(
            TenantId.from_value("default"),
            "bad-priority",
            "device",
            "serial",
            "cmdb",
            -1,
            None,
            "reject",
        )
    with pytest.raises(ValidationError):
        SourceGovernanceRule.restore(
            EntityId.new(),
            TenantId.from_value("default"),
            "naive-date",
            "device",
            "serial",
            "cmdb",
            1,
            None,
            "reject",
            True,
            datetime(2026, 1, 1),
        )


def test_accept_with_audit_conflict_keeps_evaluation_accepted() -> None:
    rule = SourceGovernanceRule.create(
        TenantId.from_value("default"),
        "audit-only",
        "device",
        "serial",
        "cmdb",
        1,
        None,
        SourceConflictStrategy.ACCEPT_WITH_AUDIT.value,
    )
    evaluation = SourceGovernanceEvaluator().evaluate(
        rule.tenant_id,
        SourceObjectKind.DEVICE,
        SourceSystem.from_value("manual"),
        {"serial": "A"},
        {"serial": "B"},
        (rule,),
    )

    assert evaluation.accepted is True
    assert evaluation.as_dict()["conflicts"][0]["strategy"] == "accept_with_audit"
