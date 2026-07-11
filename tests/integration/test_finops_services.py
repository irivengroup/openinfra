from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.finops_services import (
    CancelCostImportJobCommand,
    CloseFinancialPeriodCommand,
    CreateCostAllocationRuleCommand,
    ExportFinOpsReportCommand,
    GenerateFinOpsReportCommand,
    GetCostImportJobCommand,
    GetFinOpsReportCommand,
    ListCostAllocationRulesCommand,
    ListCostAnomaliesCommand,
    ListCostImportJobsCommand,
    ListCostRecordsCommand,
    ListFinancialPeriodsCommand,
    ListFinOpsBudgetsCommand,
    ListFinOpsForecastsCommand,
    ListFinOpsReportsCommand,
    RunCostImportJobCommand,
    SubmitCostImportJobCommand,
    UpsertFinOpsBudgetCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import NotFoundError, ValidationError

PERIOD_START = date(2026, 6, 1)
PERIOD_END = date(2026, 6, 30)


def _application(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "f" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "finops-admin", ("admin",), token)
    )
    return app, token


def _records() -> tuple[dict[str, object], ...]:
    return (
        {
            "external_id": "aws-001",
            "idempotency_key": "cost-record-aws-0001",
            "category": "cloud",
            "source": "aws-cur",
            "period_start": PERIOD_START.isoformat(),
            "period_end": PERIOD_END.isoformat(),
            "currency": "EUR",
            "amount": "100",
            "owner": "platform.team",
            "metadata": {
                "application_key": "erp",
                "service_key": "billing",
                "cost_center": "cc-001",
                "environment": "production",
                "tags": {"product": "erp"},
            },
        },
        {
            "external_id": "saas-001",
            "idempotency_key": "cost-record-saas-0001",
            "category": "saas",
            "source": "vendor-invoice",
            "period_start": PERIOD_START.isoformat(),
            "period_end": PERIOD_END.isoformat(),
            "currency": "EUR",
            "amount": "50",
            "owner": "business.team",
            "metadata": {"service_key": "crm"},
        },
    )


def test_finops_end_to_end_showback_chargeback_close_and_events(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    service = app.finops_service
    for name, priority, dimension, selector, percentage in (
        ("Application 80", 10, "application", "application_key", "80"),
        ("Cost center 20", 20, "cost-center", "cost_center", "20"),
    ):
        service.create_allocation_rule(
            CreateCostAllocationRuleCommand(
                "default", token, "pytest", name, priority, dimension, selector, percentage
            )
        )
    assert (
        len(service.list_allocation_rules(ListCostAllocationRulesCommand("default", token)).items)
        == 2
    )

    command = SubmitCostImportJobCommand(
        "default", token, "pytest", "finops-import-0001", "billing-connector", _records()
    )
    job = service.submit_import_job(command)
    assert service.submit_import_job(command).id == job.id
    with pytest.raises(ValidationError, match="another payload"):
        service.submit_import_job(
            SubmitCostImportJobCommand(
                "default",
                token,
                "pytest",
                "finops-import-0001",
                "billing-connector",
                ({**_records()[0], "amount": "999"},),
            )
        )

    completed = service.run_import_job(
        RunCostImportJobCommand("default", token, "pytest", job.id.value)
    )
    assert completed.imported_count == 2
    assert completed.unallocated_count == 1
    assert (
        service.run_import_job(RunCostImportJobCommand("default", token, "pytest", job.id.value)).id
        == completed.id
    )
    assert (
        len(
            service.get_import_job(GetCostImportJobCommand("default", token, job.id.value, True))[
                "records"
            ]
        )
        == 2
    )
    assert service.list_import_jobs(
        ListCostImportJobsCommand("default", token, status="completed")
    ).items

    records = service.list_cost_records(
        ListCostRecordsCommand(
            "default",
            token,
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            currency="EUR",
        )
    ).items
    assert len(records) == 2
    assert sum((record.amount for record in records), Decimal("0")) == Decimal("150.000000")
    assert any(record.quality_status.value == "unallocated" for record in records)
    with pytest.raises(ValidationError, match="limited to 100"):
        service.list_cost_records(ListCostRecordsCommand("default", token, limit=101))

    budget = service.upsert_budget(
        UpsertFinOpsBudgetCommand(
            "default",
            token,
            "pytest",
            "application",
            "erp",
            PERIOD_START,
            PERIOD_END,
            "EUR",
            "75",
            "80",
            "finance.team",
        )
    )
    revised = service.upsert_budget(
        UpsertFinOpsBudgetCommand(
            "default",
            token,
            "pytest",
            "application",
            "erp",
            PERIOD_START,
            PERIOD_END,
            "EUR",
            "80",
            "85",
            "finance.lead",
        )
    )
    assert revised.id == budget.id and revised.version == 2
    assert service.list_budgets(
        ListFinOpsBudgetsCommand("default", token, dimension="application", currency="EUR")
    ).items

    showback = service.generate_report(
        GenerateFinOpsReportCommand(
            "default", token, "pytest", "showback", PERIOD_START, PERIOD_END, "application", "EUR"
        )
    )
    assert showback.total_amount == Decimal("150.000000")
    assert showback.as_dict()["production_billing_mutation"] is False
    assert {line.target for line in showback.lines} == {
        "erp",
        "financial-quality/unallocated",
    }
    assert (
        service.get_report(GetFinOpsReportCommand("default", token, showback.id.value)).id
        == showback.id
    )
    assert service.list_reports(
        ListFinOpsReportsCommand("default", token, kind="showback", currency="EUR")
    ).items

    chargeback = service.generate_report(
        GenerateFinOpsReportCommand(
            "default",
            token,
            "pytest",
            "chargeback",
            PERIOD_START,
            PERIOD_END,
            "tenant",
            "EUR",
            "10",
        )
    )
    assert chargeback.total_amount == Decimal("165.000000")
    assert chargeback.as_dict()["production_billing_mutation"] is False
    with pytest.raises(ValidationError, match="showback"):
        service.generate_report(
            GenerateFinOpsReportCommand(
                "default",
                token,
                "pytest",
                "showback",
                PERIOD_START,
                PERIOD_END,
                "tenant",
                "EUR",
                "1",
            )
        )

    json_export = service.export_report(
        ExportFinOpsReportCommand("default", token, showback.id.value, "json")
    )
    csv_export = service.export_report(
        ExportFinOpsReportCommand("default", token, showback.id.value, "csv")
    )
    assert json.loads(json_export.content)["id"] == showback.id.value
    assert b"target,amount" in csv_export.content
    with pytest.raises(ValidationError, match="json or csv"):
        service.export_report(ExportFinOpsReportCommand("default", token, showback.id.value, "xml"))

    assert service.list_anomalies(ListCostAnomaliesCommand("default", token)).items
    assert service.list_forecasts(
        ListFinOpsForecastsCommand("default", token, dimension="application")
    ).items

    closed = service.close_period(
        CloseFinancialPeriodCommand("default", token, "pytest", PERIOD_START, PERIOD_END, "EUR")
    )
    assert closed.status.value == "closed"
    assert service.list_periods(
        ListFinancialPeriodsCommand("default", token, status="closed")
    ).items
    closed_report = service.generate_report(
        GenerateFinOpsReportCommand(
            "default", token, "pytest", "showback", PERIOD_START, PERIOD_END, "application", "EUR"
        )
    )
    assert closed_report.closed_period is True
    repeated = service.generate_report(
        GenerateFinOpsReportCommand(
            "default", token, "pytest", "showback", PERIOD_START, PERIOD_END, "application", "EUR"
        )
    )
    assert repeated.id == closed_report.id
    assert closed_report.reproducibility_key() != showback.reproducibility_key()

    late_job = service.submit_import_job(
        SubmitCostImportJobCommand(
            "default",
            token,
            "pytest",
            "finops-import-closed-0002",
            "billing-connector",
            ({**_records()[0], "idempotency_key": "late-record-0001"},),
        )
    )
    with pytest.raises(ValidationError, match="closed financial period"):
        service.run_import_job(
            RunCostImportJobCommand("default", token, "pytest", late_job.id.value)
        )
    assert (
        service.get_import_job(GetCostImportJobCommand("default", token, late_job.id.value))[
            "status"
        ]
        == "failed"
    )

    outbox_names = {value["name"] for value in app.store.data["finops_event_outbox"].values()}
    assert {
        "cost.record.imported",
        "cost.allocation.recomputed",
        "cost.anomaly.detected",
        "budget.threshold.crossed",
    }.issubset(outbox_names)
    assert any(
        event.action == "finops.report.generated" for event in app.audit_repository.list_events()
    )


def test_finops_cancel_not_found_tenant_isolation_and_sensitive_metadata(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    service = app.finops_service
    queued = service.submit_import_job(
        SubmitCostImportJobCommand(
            "default", token, "pytest", "finops-cancel-0001", "billing", (_records()[0],)
        )
    )
    cancelled = service.cancel_import_job(
        CancelCostImportJobCommand("default", token, "pytest", queued.id.value)
    )
    assert cancelled.status.value == "cancelled"
    assert (
        service.cancel_import_job(
            CancelCostImportJobCommand("default", token, "pytest", queued.id.value)
        ).id
        == cancelled.id
    )
    with pytest.raises(NotFoundError):
        service.get_report(
            GetFinOpsReportCommand("default", token, "00000000-0000-4000-8000-000000000001")
        )
    with pytest.raises(ValidationError, match="sensitive key"):
        service.submit_import_job(
            SubmitCostImportJobCommand(
                "default",
                token,
                "pytest",
                "finops-secret-0001",
                "billing",
                ({**_records()[0], "metadata": {"api_token": "forbidden"}},),
            )
        )


def test_finops_historical_analysis_tag_grouping_duplicates_and_errors(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    service = app.finops_service

    periods = (
        (date(2026, 1, 1), date(2026, 1, 31), "100", "hist-record-jan-0001"),
        (date(2026, 2, 1), date(2026, 2, 28), "100", "hist-record-feb-0001"),
        (date(2026, 3, 1), date(2026, 3, 31), "250", "hist-record-mar-0001"),
    )
    for index, (period_start, period_end, amount, record_key) in enumerate(periods, start=1):
        record = {
            "external_id": f"aws-history-{index:02d}",
            "idempotency_key": record_key,
            "category": "cloud",
            "source": "aws-cur",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "currency": "EUR",
            "amount": amount,
            "owner": "platform.team",
            "metadata": {
                "owner": "platform.team",
                "tags": {"product": "openinfra"},
            },
        }
        job = service.submit_import_job(
            SubmitCostImportJobCommand(
                "default",
                token,
                "pytest",
                f"finops-history-import-{index:04d}",
                "aws-cur",
                (record,),
            )
        )
        completed = service.run_import_job(
            RunCostImportJobCommand("default", token, "pytest", job.id.value)
        )
        assert completed.imported_count == 1

    anomalies = service.list_anomalies(
        ListCostAnomaliesCommand("default", token, severity="error")
    ).items
    assert any(item.code == "cost-spike" for item in anomalies)

    tag_report = service.generate_report(
        GenerateFinOpsReportCommand(
            "default",
            token,
            "pytest",
            "showback",
            date(2026, 3, 1),
            date(2026, 3, 31),
            "tag",
            "EUR",
        )
    )
    assert [(line.target, line.amount) for line in tag_report.lines] == [
        ("product:openinfra", Decimal("250.000000"))
    ]
    tag_forecasts = service.list_forecasts(
        ListFinOpsForecastsCommand("default", token, dimension="tag", target="product:openinfra")
    ).items
    assert len(tag_forecasts) == 1
    assert tag_forecasts[0].expected_amount == Decimal("100.000000")
    assert tag_forecasts[0].basis_period_count == 2

    owner_report = service.generate_report(
        GenerateFinOpsReportCommand(
            "default",
            token,
            "pytest",
            "showback",
            date(2026, 3, 1),
            date(2026, 3, 31),
            "owner",
            "EUR",
        )
    )
    assert owner_report.lines[0].target == "platform.team"

    duplicate_record = {
        "external_id": "aws-history-duplicate",
        "idempotency_key": "hist-record-mar-0001",
        "category": "cloud",
        "source": "aws-cur",
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
        "currency": "EUR",
        "amount": "250",
        "owner": "platform.team",
        "metadata": {"tags": {"product": "openinfra"}},
    }
    duplicate_job = service.submit_import_job(
        SubmitCostImportJobCommand(
            "default",
            token,
            "pytest",
            "finops-history-duplicate-0001",
            "aws-cur",
            (duplicate_record,),
        )
    )
    duplicate_completed = service.run_import_job(
        RunCostImportJobCommand("default", token, "pytest", duplicate_job.id.value)
    )
    assert duplicate_completed.imported_count == 0
    assert duplicate_completed.duplicate_count == 1

    with pytest.raises(ValidationError, match="cannot group solely"):
        service.generate_report(
            GenerateFinOpsReportCommand(
                "default",
                token,
                "pytest",
                "showback",
                date(2026, 3, 1),
                date(2026, 3, 31),
                "unallocated",
                "EUR",
            )
        )
    missing_id = "00000000-0000-4000-8000-000000000002"
    with pytest.raises(NotFoundError, match="report"):
        service.export_report(ExportFinOpsReportCommand("default", token, missing_id, "json"))
    with pytest.raises(NotFoundError, match="import job"):
        service.run_import_job(RunCostImportJobCommand("default", token, "pytest", missing_id))

    invalid_job = service.submit_import_job(
        SubmitCostImportJobCommand(
            "default",
            token,
            "pytest",
            "finops-invalid-date-0001",
            "aws-cur",
            (
                {
                    **duplicate_record,
                    "idempotency_key": "hist-invalid-date-0001",
                    "period_start": "2026-99-01",
                },
            ),
        )
    )
    with pytest.raises(ValidationError, match="ISO-8601"):
        service.run_import_job(
            RunCostImportJobCommand("default", token, "pytest", invalid_job.id.value)
        )
    assert service._parse_date(date(2026, 3, 1), "period start") == date(2026, 3, 1)
