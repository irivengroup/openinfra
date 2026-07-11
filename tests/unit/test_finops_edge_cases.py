from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.finops import (
    AllocationDimension,
    CostAllocation,
    CostAllocationRule,
    CostAnomaly,
    CostCategory,
    CostImportJob,
    CostRecord,
    FinancialPeriod,
    FinOpsBudget,
    FinOpsForecast,
    FinOpsReport,
    FinOpsReportKind,
    FinOpsReportLine,
    FinOpsValueValidator,
)
from openinfra.infrastructure.finops_mapper import FinOpsRecordMapper


def _raw_record() -> dict[str, object]:
    return {
        "external_id": "edge-001",
        "category": "cloud",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "currency": "EUR",
        "amount": "10",
    }


def test_finops_validators_cover_rejection_boundaries() -> None:
    invalid_calls = (
        lambda: CostCategory.from_value("invalid"),
        lambda: AllocationDimension.from_value("invalid"),
        lambda: FinOpsReportKind.from_value("invalid"),
        lambda: FinOpsValueValidator.text("", "name", 1, 2),
        lambda: FinOpsValueValidator.token("?bad", "token"),
        lambda: FinOpsValueValidator.idempotency_key("short"),
        lambda: FinOpsValueValidator.currency("EU"),
        lambda: FinOpsValueValidator.amount("1000000000000000000"),
        lambda: FinOpsValueValidator.positive_amount("0"),
        lambda: FinOpsValueValidator.percentage("invalid"),
        lambda: FinOpsValueValidator.percentage("101"),
        lambda: FinOpsValueValidator.date_range(date(2026, 2, 1), date(2026, 1, 1)),
        lambda: FinOpsValueValidator.selector_key("tag:?"),
        lambda: FinOpsValueValidator.selector_key("unknown"),
        lambda: FinOpsValueValidator.json_object([], "metadata"),  # type: ignore[arg-type]
        lambda: FinOpsValueValidator.json_object({"value": object()}, "metadata"),
        lambda: FinOpsValueValidator.json_object({"value": "x" * 140_000}, "metadata"),
        lambda: FinOpsValueValidator.records(()),
        lambda: FinOpsValueValidator.records(tuple({"id": i} for i in range(10_001))),
    )
    for call in invalid_calls:
        with pytest.raises(ValidationError):
            call()

    assert FinOpsValueValidator.optional_text(None, "optional") is None
    assert FinOpsValueValidator.optional_token("", "optional") is None
    assert FinOpsValueValidator.optional_datetime(None, "optional") is None
    assert FinOpsValueValidator.json_object(
        {"items": ({"safe": "value"},), "numeric_key": {1: "ok"}}, "metadata"
    )["items"] == ({"safe": "value"},)


def test_finops_rule_record_and_job_edge_invariants() -> None:
    tenant = TenantId.from_value("default")
    now = datetime.now(UTC)
    tenant_rule = CostAllocationRule.create(tenant, "Tenant rule", 1, "tenant", "tenant", "100")
    assert tenant_rule.fixed_target == "default"
    assert tenant_rule.resolve_target({}, tenant) == "default"

    fixed = CostAllocationRule.create(
        tenant, "Fixed rule", 2, "application", "application_key", "100", fixed_target="erp"
    )
    assert fixed.resolve_target({}, tenant) == "erp"
    tag = CostAllocationRule.create(tenant, "Tag rule", 3, "tag", "tag:product", "100")
    assert tag.resolve_target({}, tenant) is None
    assert tag.resolve_target({"tags": []}, tenant) is None
    assert tag.resolve_target({"tags": {"product": "openinfra"}}, tenant) == "openinfra"

    with pytest.raises(ValidationError, match="version"):
        CostAllocationRule.restore(
            EntityId.new(),
            tenant,
            "Rule",
            1,
            None,
            None,
            "tenant",
            "tenant",
            None,
            "100",
            True,
            now,
            now,
            0,
        )
    with pytest.raises(ValidationError, match="precede"):
        CostAllocationRule.restore(
            EntityId.new(),
            tenant,
            "Rule",
            1,
            None,
            None,
            "tenant",
            "tenant",
            None,
            "100",
            True,
            now,
            now - timedelta(seconds=1),
            1,
        )

    job_id = EntityId.new()
    allocated = CostAllocation.create("application", "erp", "50", "5")
    unallocated = CostAllocation.create("unallocated", "ignored", "50", "5")
    partial = CostRecord.create(
        tenant,
        "edge-001",
        "finops-edge-record-0001",
        "cloud",
        "aws",
        date(2026, 1, 1),
        date(2026, 1, 31),
        "EUR",
        "10",
        "platform.team",
        "rule-based",
        {},
        (allocated, unallocated),
        job_id,
    )
    assert partial.quality_status.value == "partial"

    invalid_record_calls = (
        lambda: CostRecord.create(
            tenant,
            "edge-002",
            "finops-edge-record-0002",
            "cloud",
            "aws",
            date(2026, 1, 1),
            date(2026, 1, 31),
            "EUR",
            "10",
            "platform.team",
            "rule-based",
            {},
            (),
            job_id,
        ),
        lambda: CostRecord.create(
            tenant,
            "edge-003",
            "finops-edge-record-0003",
            "cloud",
            "aws",
            date(2026, 1, 1),
            date(2026, 1, 31),
            "EUR",
            "10",
            "platform.team",
            "rule-based",
            {},
            (CostAllocation.create("application", "erp", "100", "9"),),
            job_id,
        ),
        lambda: CostRecord.create(
            tenant,
            "edge-004",
            "finops-edge-record-0004",
            "cloud",
            "aws",
            date(2026, 1, 1),
            date(2026, 1, 31),
            "EUR",
            "10",
            "platform.team",
            "rule-based",
            {},
            (
                CostAllocation.create("application", "erp", "60", "5"),
                CostAllocation.create("tenant", "default", "60", "5"),
            ),
            job_id,
        ),
    )
    for call in invalid_record_calls:
        with pytest.raises(ValidationError):
            call()

    job = CostImportJob.create(tenant, "finops-edge-job-0001", "aws", (_raw_record(),))
    base = job.as_dict(include_records=True)
    restore_kwargs = {
        "id": job.id,
        "tenant_id": tenant,
        "idempotency_key": job.idempotency_key,
        "source": job.source,
        "records": job.records,
        "payload_sha256": job.payload_sha256,
        "status": job.status.value,
        "submitted_at": job.submitted_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "failure_reason": job.failure_reason,
        "imported_count": job.imported_count,
        "duplicate_count": job.duplicate_count,
        "anomaly_count": job.anomaly_count,
        "unallocated_count": job.unallocated_count,
        "version": job.version,
    }
    assert base["records"]
    invalid_job_values = (
        {"payload_sha256": "0" * 64},
        {"status": "unknown"},
        {"imported_count": -1},
        {"version": 0},
        {"started_at": job.submitted_at - timedelta(seconds=1)},
        {
            "status": "completed",
            "started_at": job.submitted_at,
            "completed_at": job.submitted_at - timedelta(seconds=1),
        },
    )
    for update in invalid_job_values:
        with pytest.raises(ValidationError):
            CostImportJob.restore(**(restore_kwargs | update))

    failed = job.started().failed("provider unavailable")
    assert failed.status.value == "failed"
    with pytest.raises(ValidationError, match="cannot be started"):
        job.cancelled().started()


def test_finops_period_budget_anomaly_forecast_and_report_boundaries() -> None:
    tenant = TenantId.from_value("default")
    now = datetime.now(UTC)
    period = FinancialPeriod.create(tenant, date(2026, 1, 1), date(2026, 1, 31), "EUR")
    with pytest.raises(ValidationError):
        FinancialPeriod.restore(
            period.id,
            tenant,
            period.period_start,
            period.period_end,
            "EUR",
            "invalid",
            None,
            None,
            None,
            now,
        )
    with pytest.raises(ValidationError):
        FinancialPeriod.restore(
            period.id,
            tenant,
            period.period_start,
            period.period_end,
            "EUR",
            "closed",
            None,
            None,
            None,
            now,
        )
    with pytest.raises(ValidationError):
        period.closed("finance.team", "invalid")

    budget = FinOpsBudget.create(
        tenant,
        "application",
        "erp",
        date(2026, 1, 1),
        date(2026, 1, 31),
        "EUR",
        "100",
        "80",
        "finance.team",
    )
    with pytest.raises(ValidationError):
        FinOpsBudget.restore(
            budget.id,
            tenant,
            "application",
            "erp",
            budget.period_start,
            budget.period_end,
            "EUR",
            "100",
            "80",
            "finance.team",
            now,
            now,
            0,
        )
    with pytest.raises(ValidationError):
        FinOpsBudget.restore(
            budget.id,
            tenant,
            "application",
            "erp",
            budget.period_start,
            budget.period_end,
            "EUR",
            "100",
            "80",
            "finance.team",
            now,
            now - timedelta(seconds=1),
            1,
        )

    anomaly = CostAnomaly.create(
        tenant, EntityId.new(), "cost-spike", Severity.WARNING, "Cost spike detected", "50"
    )
    assert anomaly.as_dict()["severity"] == "warning"
    with pytest.raises(ValidationError):
        CostAnomaly.restore(
            anomaly.id,
            tenant,
            anomaly.record_id,
            "cost-spike",
            "invalid",
            "Cost spike detected",
            "50",
            now,
        )

    forecast = FinOpsForecast.create(
        tenant,
        "application",
        "erp",
        date(2026, 2, 1),
        date(2026, 2, 28),
        "EUR",
        "100",
        3,
        "75",
        "a" * 64,
    )
    assert forecast.as_dict()["basis_period_count"] == 3
    for periods, digest in ((0, "a" * 64), (37, "a" * 64), (1, "invalid")):
        with pytest.raises(ValidationError):
            FinOpsForecast.restore(
                forecast.id,
                tenant,
                "application",
                "erp",
                forecast.period_start,
                forecast.period_end,
                "EUR",
                "100",
                periods,
                "75",
                digest,
                now,
            )

    with pytest.raises(ValidationError, match="counters"):
        FinOpsReportLine.create("erp", "10", -1, None, None, 0)
    with pytest.raises(ValidationError, match="SHA-256"):
        FinOpsReport.create(
            tenant,
            "showback",
            date(2026, 1, 1),
            date(2026, 1, 31),
            "application",
            "EUR",
            "10",
            "0",
            "0",
            (),
            "invalid",
            False,
        )


def test_finops_mapper_helper_boundaries() -> None:
    now = datetime.now(UTC)
    assert FinOpsRecordMapper._date(now) == now.date()
    assert FinOpsRecordMapper._date(now.date()) == now.date()
    assert FinOpsRecordMapper._datetime(now) == now
    assert FinOpsRecordMapper._datetime("2026-01-01T00:00:00Z").tzinfo is not None
    assert FinOpsRecordMapper._optional_datetime("") is None
    assert FinOpsRecordMapper._optional_text("") is None
    assert FinOpsRecordMapper._optional_decimal_text(None) is None
    assert FinOpsRecordMapper._mapping(None) == {}
    assert FinOpsRecordMapper._mapping_list(None) == []

    for call in (
        lambda: FinOpsRecordMapper._date("invalid"),
        lambda: FinOpsRecordMapper._datetime("invalid"),
        lambda: FinOpsRecordMapper._mapping([]),
        lambda: FinOpsRecordMapper._mapping_list({}),
        lambda: FinOpsRecordMapper._mapping_list(["invalid"]),
    ):
        with pytest.raises(ValidationError):
            call()
