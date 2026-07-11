from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from openinfra.application.finops_services import CostAllocationEngine
from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.finops import (
    AllocationDimension,
    CostAllocation,
    CostAllocationRule,
    CostCategory,
    CostImportJob,
    FinancialPeriod,
    FinOpsBudget,
    FinOpsReport,
    FinOpsReportLine,
    FinOpsValueValidator,
)


def test_finops_value_validation_rejects_invalid_financial_and_sensitive_values() -> None:
    assert FinOpsValueValidator.amount("12.3456789") == Decimal("12.345679")
    assert FinOpsValueValidator.currency("eur") == "EUR"
    assert FinOpsValueValidator.selector_key("tag:Product") == "tag:product"
    assert FinOpsValueValidator.date_range(date(2026, 1, 1), date(2026, 1, 31))

    for value in ("NaN", "Infinity", "-1"):
        with pytest.raises(ValidationError):
            FinOpsValueValidator.amount(value)
    with pytest.raises(ValidationError, match="sensitive key"):
        FinOpsValueValidator.json_object(
            {"provider": {"credentials": [{"api_key": "must-not-be-stored"}]}},
            "billing metadata",
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        FinOpsValueValidator.aware_datetime(datetime(2026, 1, 1), "created_at")
    with pytest.raises(ValidationError, match="ten years"):
        FinOpsValueValidator.date_range(date(2010, 1, 1), date(2026, 1, 1))


def test_allocation_rules_and_engine_are_deterministic_and_preserve_totals() -> None:
    tenant = TenantId.from_value("default")
    app_rule = CostAllocationRule.create(
        tenant,
        "Application allocation",
        10,
        "application",
        "application_key",
        "70",
        category="cloud",
    )
    cost_center_rule = CostAllocationRule.create(
        tenant,
        "Cost center allocation",
        20,
        "cost-center",
        "cost_center",
        "30",
        source="aws-cur",
    )
    allocations = CostAllocationEngine.allocate(
        tenant,
        Decimal("100"),
        CostCategory.CLOUD,
        "aws-cur",
        {"application_key": "erp", "cost_center": "cc-001"},
        (cost_center_rule, app_rule),
    )
    assert [(item.dimension.value, item.target, item.amount) for item in allocations] == [
        ("application", "erp", Decimal("70.000000")),
        ("cost-center", "cc-001", Decimal("30.000000")),
    ]
    assert sum((item.amount for item in allocations), Decimal("0")) == Decimal("100")

    fallback = CostAllocationEngine.allocate(
        tenant, Decimal("50"), CostCategory.SAAS, "vendor", {}, (app_rule,)
    )
    assert fallback[0].dimension is AllocationDimension.UNALLOCATED
    assert fallback[0].target == "financial-quality/unallocated"
    assert fallback[0].amount == Decimal("50.000000")
    assert app_rule.revised("Application allocation v2", 5, "60", False).version == 2


def test_import_period_budget_and_report_lifecycle_invariants() -> None:
    tenant = TenantId.from_value("default")
    job = CostImportJob.create(
        tenant,
        "finops-domain-0001",
        "aws-cur",
        (
            {
                "external_id": "line-1",
                "category": "cloud",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "currency": "EUR",
                "amount": "100",
            },
        ),
    )
    running = job.started()
    assert running.started() is running
    completed = running.completed(1, 0, 0, 0)
    assert completed.completed_at is not None
    assert completed.cancelled() is completed
    with pytest.raises(ValidationError):
        job.completed(2, 0, 0, 0)

    period = FinancialPeriod.create(tenant, date(2026, 6, 1), date(2026, 6, 30), "EUR")
    closed = period.closed("finance.team", "a" * 64)
    assert closed.closed("finance.team", "a" * 64) is closed
    with pytest.raises(ValidationError, match="source digest cannot change"):
        closed.closed("finance.team", "b" * 64)

    budget = FinOpsBudget.create(
        tenant,
        "application",
        "erp",
        date(2026, 6, 1),
        date(2026, 6, 30),
        "EUR",
        "90",
        "80",
        "finance.team",
    )
    revised = budget.revised("120", "85", "finance.lead")
    assert revised.version == 2
    assert revised.amount == Decimal("120.000000")

    line = FinOpsReportLine.create("erp", "110", 2, "100", "105", 1)
    assert line.variance_amount == Decimal("10.000000")
    assert line.variance_percent == Decimal("10.0000")
    report = FinOpsReport.create(
        tenant,
        "showback",
        date(2026, 6, 1),
        date(2026, 6, 30),
        "application",
        "EUR",
        "110",
        "10",
        "0",
        (line,),
        "c" * 64,
        False,
    )
    closed_report = FinOpsReport.restore(
        report.id,
        report.tenant_id,
        report.kind.value,
        report.period_start,
        report.period_end,
        report.group_by.value,
        report.currency,
        report.total_amount,
        report.unallocated_amount,
        report.chargeback_markup_percent,
        report.lines,
        report.input_digest,
        True,
        report.generated_at + timedelta(seconds=1),
    )
    assert report.quality_score_percent == Decimal("90.9091")
    assert report.reproducibility_key() != closed_report.reproducibility_key()


def test_domain_restore_rejects_cross_field_inconsistencies() -> None:
    tenant = TenantId.from_value("default")
    now = datetime.now(UTC)
    with pytest.raises(ValidationError, match="priority"):
        CostAllocationRule.restore(
            EntityId.new(),
            tenant,
            "Invalid priority",
            0,
            None,
            None,
            "application",
            "application_key",
            None,
            "100",
            True,
            now,
            now,
            1,
        )
    with pytest.raises(ValidationError, match="unallocated"):
        CostAllocationRule.create(tenant, "Invalid dimension", 1, "unallocated", "tenant", "100")
    with pytest.raises(ValidationError, match="cannot exceed"):
        FinOpsReport.create(
            tenant,
            "showback",
            date(2026, 1, 1),
            date(2026, 1, 31),
            "tenant",
            "EUR",
            "10",
            "11",
            "0",
            (),
            "d" * 64,
            False,
        )
    allocation = CostAllocation.create("unallocated", "ignored", "100", "10")
    assert allocation.target == "financial-quality/unallocated"
