from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from openinfra.application.ports import (
    AuditRepository,
    CostAllocationRulePage,
    CostAnomalyPage,
    CostImportJobPage,
    CostRecordPage,
    FinancialPeriodPage,
    FinOpsBudgetPage,
    FinOpsForecastPage,
    FinOpsReportPage,
    FinOpsRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    DomainEvent,
    EntityId,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.finops import (
    AllocationDimension,
    CostAllocation,
    CostAllocationRule,
    CostAnomaly,
    CostCategory,
    CostImportJob,
    CostQualityStatus,
    CostRecord,
    FinancialPeriod,
    FinancialPeriodStatus,
    FinOpsBudget,
    FinOpsForecast,
    FinOpsImportJobStatus,
    FinOpsReport,
    FinOpsReportKind,
    FinOpsReportLine,
    FinOpsValueValidator,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class CreateCostAllocationRuleCommand:
    tenant_id: str
    admin_token: str
    actor: str
    name: str
    priority: int
    dimension: str
    selector_key: str
    percentage: str
    category: str | None = None
    source: str | None = None
    fixed_target: str | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class ListCostAllocationRulesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    active_only: bool = False


@dataclass(frozen=True, slots=True)
class SubmitCostImportJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    idempotency_key: str
    source: str
    records: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class GetCostImportJobCommand:
    tenant_id: str
    admin_token: str
    job_id: str
    include_records: bool = False


@dataclass(frozen=True, slots=True)
class ListCostImportJobsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class RunCostImportJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    job_id: str


@dataclass(frozen=True, slots=True)
class CancelCostImportJobCommand:
    tenant_id: str
    admin_token: str
    actor: str
    job_id: str


@dataclass(frozen=True, slots=True)
class ListCostRecordsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    currency: str | None = None
    category: str | None = None
    source: str | None = None
    quality_status: str | None = None


@dataclass(frozen=True, slots=True)
class UpsertFinOpsBudgetCommand:
    tenant_id: str
    admin_token: str
    actor: str
    dimension: str
    target: str
    period_start: date
    period_end: date
    currency: str
    amount: str
    warning_threshold_percent: str
    owner: str


@dataclass(frozen=True, slots=True)
class ListFinOpsBudgetsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    dimension: str | None = None
    target: str | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class CloseFinancialPeriodCommand:
    tenant_id: str
    admin_token: str
    actor: str
    period_start: date
    period_end: date
    currency: str


@dataclass(frozen=True, slots=True)
class ListFinancialPeriodsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class GenerateFinOpsReportCommand:
    tenant_id: str
    admin_token: str
    actor: str
    kind: str
    period_start: date
    period_end: date
    group_by: str
    currency: str
    chargeback_markup_percent: str = "0"


@dataclass(frozen=True, slots=True)
class GetFinOpsReportCommand:
    tenant_id: str
    admin_token: str
    report_id: str


@dataclass(frozen=True, slots=True)
class ListFinOpsReportsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    kind: str | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class ExportFinOpsReportCommand:
    tenant_id: str
    admin_token: str
    report_id: str
    format: str = "json"


@dataclass(frozen=True, slots=True)
class ListCostAnomaliesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    severity: str | None = None


@dataclass(frozen=True, slots=True)
class ListFinOpsForecastsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    dimension: str | None = None
    target: str | None = None


@dataclass(frozen=True, slots=True)
class FinOpsReportExport:
    filename: str
    content_type: str
    content: bytes


class CostAllocationEngine:
    @classmethod
    def allocate(
        cls,
        tenant_id: TenantId,
        amount: Decimal,
        category: CostCategory,
        source: str,
        metadata: dict[str, Any],
        rules: tuple[CostAllocationRule, ...],
    ) -> tuple[CostAllocation, ...]:
        remaining = amount
        allocations: list[CostAllocation] = []
        for rule in sorted(rules, key=lambda item: (item.priority, item.id.value)):
            if remaining <= 0 or not rule.matches(category, source):
                continue
            target = rule.resolve_target(metadata, tenant_id)
            if target is None:
                continue
            requested = (amount * rule.percentage / Decimal("100")).quantize(
                FinOpsValueValidator._MONEY_QUANTUM
            )
            allocated = min(remaining, requested)
            if allocated <= 0:
                continue
            actual_percentage = (allocated / amount * Decimal("100")).quantize(
                FinOpsValueValidator._PERCENT_QUANTUM
            )
            allocations.append(
                CostAllocation.create(
                    rule.dimension.value,
                    target,
                    actual_percentage,
                    allocated,
                    rule.id,
                )
            )
            remaining = (remaining - allocated).quantize(FinOpsValueValidator._MONEY_QUANTUM)
        if remaining > 0:
            percentage = (remaining / amount * Decimal("100")).quantize(
                FinOpsValueValidator._PERCENT_QUANTUM
            )
            allocations.append(
                CostAllocation.create(
                    AllocationDimension.UNALLOCATED.value,
                    "financial-quality/unallocated",
                    percentage,
                    remaining,
                )
            )
        return tuple(allocations)


class FinOpsService:
    _MAX_ANALYTIC_RECORDS = 100_000
    _PAGE_SIZE = 500

    def __init__(
        self,
        repository: FinOpsRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def create_allocation_rule(
        self, command: CreateCostAllocationRuleCommand
    ) -> CostAllocationRule:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_WRITE
        )
        rule = CostAllocationRule.create(
            tenant_id=tenant_id,
            name=command.name,
            priority=command.priority,
            dimension=command.dimension,
            selector_key=command.selector_key,
            percentage=command.percentage,
            category=command.category,
            source=command.source,
            fixed_target=command.fixed_target,
            active=command.active,
        )
        self._save_with_audit(
            rule.id,
            tenant_id,
            command.actor or principal.subject,
            "finops.allocation-rule.created",
            "finops_allocation_rule",
            rule.as_dict(),
            lambda: self._repository.save_allocation_rule(rule),
        )
        return rule

    def list_allocation_rules(
        self, command: ListCostAllocationRulesCommand
    ) -> CostAllocationRulePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_allocation_rules(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.active_only,
        )

    def submit_import_job(self, command: SubmitCostImportJobCommand) -> CostImportJob:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_IMPORT
        )
        existing = self._repository.find_import_job_by_idempotency_key(
            tenant_id, command.idempotency_key
        )
        if existing is not None:
            candidate = CostImportJob.create(
                tenant_id, command.idempotency_key, command.source, command.records
            )
            if existing.payload_sha256 != candidate.payload_sha256:
                raise ValidationError(
                    "finops import idempotency key is already bound to another payload"
                )
            return existing
        job = CostImportJob.create(
            tenant_id, command.idempotency_key, command.source, command.records
        )
        self._save_with_audit(
            job.id,
            tenant_id,
            command.actor or principal.subject,
            "finops.import.queued",
            "finops_import_job",
            job.as_dict(include_records=False),
            lambda: self._repository.save_import_job(job),
            event_payload={
                "job_id": job.id.value,
                "record_count": len(job.records),
                "payload_sha256": job.payload_sha256,
            },
        )
        return job

    def get_import_job(self, command: GetCostImportJobCommand) -> dict[str, object]:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        job = self._required_import_job(tenant_id, command.job_id)
        return job.as_dict(include_records=command.include_records)

    def list_import_jobs(self, command: ListCostImportJobsCommand) -> CostImportJobPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_import_jobs(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.status,
        )

    def run_import_job(self, command: RunCostImportJobCommand) -> CostImportJob:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_IMPORT
        )
        current = self._required_import_job(tenant_id, command.job_id)
        if current.status is FinOpsImportJobStatus.COMPLETED:
            return current
        running = current.started()
        self._save_job_transition(
            current,
            running,
            command.actor or principal.subject,
            "finops.import.started",
        )
        try:
            completed = self._process_import_job(running)
        except Exception as exc:
            failed = running.failed(str(exc))
            self._save_job_transition(
                running,
                failed,
                command.actor or principal.subject,
                "finops.import.failed",
                Severity.ERROR,
            )
            raise
        self._save_job_transition(
            running,
            completed,
            command.actor or principal.subject,
            "finops.import.completed",
        )
        return completed

    def cancel_import_job(self, command: CancelCostImportJobCommand) -> CostImportJob:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_IMPORT
        )
        current = self._required_import_job(tenant_id, command.job_id)
        cancelled = current.cancelled()
        if cancelled is current:
            return current
        self._save_job_transition(
            current,
            cancelled,
            command.actor or principal.subject,
            "finops.import.cancelled",
        )
        return cancelled

    def list_cost_records(self, command: ListCostRecordsCommand) -> CostRecordPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        if command.period_start is None and command.period_end is None and command.limit > 100:
            raise ValidationError(
                "unfiltered finops cost record queries are limited to 100 entries"
            )
        return self._repository.list_cost_records(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.period_start,
            command.period_end,
            command.currency,
            command.category,
            command.source,
            command.quality_status,
        )

    def upsert_budget(self, command: UpsertFinOpsBudgetCommand) -> FinOpsBudget:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_WRITE
        )
        existing = self._repository.find_budget(
            tenant_id,
            command.dimension,
            command.target,
            command.period_start,
            command.period_end,
            command.currency,
        )
        budget = (
            FinOpsBudget.create(
                tenant_id,
                command.dimension,
                command.target,
                command.period_start,
                command.period_end,
                command.currency,
                command.amount,
                command.warning_threshold_percent,
                command.owner,
            )
            if existing is None
            else existing.revised(command.amount, command.warning_threshold_percent, command.owner)
        )
        self._save_with_audit(
            budget.id,
            tenant_id,
            command.actor or principal.subject,
            "finops.budget.upserted",
            "finops_budget",
            {
                "old_state": None if existing is None else existing.as_dict(),
                "new_state": budget.as_dict(),
            },
            lambda: self._repository.save_budget(budget),
        )
        return budget

    def list_budgets(self, command: ListFinOpsBudgetsCommand) -> FinOpsBudgetPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_budgets(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.dimension,
            command.target,
            command.currency,
        )

    def close_period(self, command: CloseFinancialPeriodCommand) -> FinancialPeriod:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_ADMIN
        )
        records = self._all_records(
            tenant_id, command.period_start, command.period_end, command.currency
        )
        digest = self._records_digest(records)
        current = self._repository.find_period(
            tenant_id, command.period_start, command.period_end, command.currency
        ) or FinancialPeriod.create(
            tenant_id, command.period_start, command.period_end, command.currency
        )
        closed = current.closed(command.actor or principal.subject, digest)
        self._save_with_audit(
            closed.id,
            tenant_id,
            command.actor or principal.subject,
            "finops.period.closed",
            "finops_financial_period",
            {"old_state": current.as_dict(), "new_state": closed.as_dict()},
            lambda: self._repository.save_period(closed),
            event_payload={
                "period_id": closed.id.value,
                "currency": closed.currency,
                "source_digest": digest,
                "record_count": len(records),
            },
        )
        return closed

    def list_periods(self, command: ListFinancialPeriodsCommand) -> FinancialPeriodPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_periods(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.status,
        )

    def generate_report(self, command: GenerateFinOpsReportCommand) -> FinOpsReport:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_WRITE
        )
        report_kind = FinOpsReportKind.from_value(command.kind)
        dimension = AllocationDimension.from_value(command.group_by)
        if dimension is AllocationDimension.UNALLOCATED:
            raise ValidationError("finops reports cannot group solely by unallocated dimension")
        markup = FinOpsValueValidator.percentage(
            command.chargeback_markup_percent, "chargeback markup", allow_zero=True
        )
        if report_kind is FinOpsReportKind.SHOWBACK and markup != 0:
            raise ValidationError("showback reports cannot apply a chargeback markup")
        records = self._all_records(
            tenant_id, command.period_start, command.period_end, command.currency
        )
        period = self._repository.find_period(
            tenant_id, command.period_start, command.period_end, command.currency
        )
        input_digest = self._records_digest(records)
        if (
            period is not None
            and period.status is FinancialPeriodStatus.CLOSED
            and period.source_digest != input_digest
        ):
            raise ValidationError("closed financial period data no longer matches its digest")
        report, forecasts = self._build_report(
            tenant_id,
            report_kind,
            dimension,
            command.period_start,
            command.period_end,
            command.currency,
            markup,
            records,
            period is not None and period.status is FinancialPeriodStatus.CLOSED,
            input_digest,
        )
        if report.closed_period:
            existing = self._repository.find_report_by_reproducibility_key(
                tenant_id, report.reproducibility_key()
            )
            if existing is not None:
                return existing
        actor = command.actor or principal.subject
        with self._transaction_manager.begin() as unit_of_work:
            for forecast in forecasts:
                self._repository.save_forecast(forecast)
            self._repository.save_report(report)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    report.id,
                    "finops.report.generated",
                    {
                        "report_id": report.id.value,
                        "kind": report.kind.value,
                        "total_amount": str(report.total_amount),
                        "currency": report.currency,
                        "quality_score_percent": str(report.quality_score_percent),
                        "production_billing_mutation": False,
                    },
                )
            )
            for line in report.lines:
                if line.budget_amount is not None and line.variance_amount is not None:
                    budget = self._repository.find_budget(
                        tenant_id,
                        dimension.value,
                        line.target,
                        command.period_start,
                        command.period_end,
                        command.currency,
                    )
                    if budget is not None and line.amount >= (
                        budget.amount * budget.warning_threshold_percent / Decimal("100")
                    ):
                        self._repository.append_event(
                            DomainEvent.create(
                                tenant_id,
                                budget.id,
                                "budget.threshold.crossed",
                                {
                                    "budget_id": budget.id.value,
                                    "target": line.target,
                                    "actual_amount": str(line.amount),
                                    "budget_amount": str(budget.amount),
                                },
                            )
                        )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    actor,
                    "finops.report.generated",
                    "finops_report",
                    report.id.value,
                    metadata={
                        "report": report.as_dict(),
                        "source": "finops-analytics",
                        "production_billing_mutation": False,
                    },
                )
            )
            unit_of_work.commit()
        return report

    def get_report(self, command: GetFinOpsReportCommand) -> FinOpsReport:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        report = self._repository.get_report(tenant_id, command.report_id)
        if report is None:
            raise NotFoundError("finops report does not exist")
        return report

    def list_reports(self, command: ListFinOpsReportsCommand) -> FinOpsReportPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_reports(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.kind,
            command.currency,
        )

    def export_report(self, command: ExportFinOpsReportCommand) -> FinOpsReportExport:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_EXPORT
        )
        report = self._repository.get_report(tenant_id, command.report_id)
        if report is None:
            raise NotFoundError("finops report does not exist")
        normalized_format = command.format.strip().lower()
        if normalized_format == "json":
            content = json.dumps(
                report.as_dict(), sort_keys=True, ensure_ascii=False, indent=2
            ).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        elif normalized_format == "csv":
            output = io.StringIO(newline="")
            writer = csv.DictWriter(
                output,
                fieldnames=(
                    "target",
                    "amount",
                    "record_count",
                    "budget_amount",
                    "variance_amount",
                    "variance_percent",
                    "forecast_amount",
                    "anomaly_count",
                ),
            )
            writer.writeheader()
            for line in report.lines:
                writer.writerow(line.as_dict())
            content = output.getvalue().encode("utf-8")
            content_type = "text/csv; charset=utf-8"
        else:
            raise ValidationError("finops report export format must be json or csv")
        return FinOpsReportExport(
            filename=f"finops-{report.kind.value}-{report.id.value}.{normalized_format}",
            content_type=content_type,
            content=content,
        )

    def list_anomalies(self, command: ListCostAnomaliesCommand) -> CostAnomalyPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_anomalies(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.severity,
        )

    def list_forecasts(self, command: ListFinOpsForecastsCommand) -> FinOpsForecastPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FINOPS_READ
        )
        return self._repository.list_forecasts(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.dimension,
            command.target,
        )

    def _process_import_job(self, job: CostImportJob) -> CostImportJob:
        rules = self._all_rules(job.tenant_id)
        imported_count = 0
        duplicate_count = 0
        anomaly_count = 0
        unallocated_count = 0
        for payload in job.records:
            idempotency_key = str(
                payload.get("idempotency_key")
                or f"{job.idempotency_key}:{payload.get('external_id', '')}"
            )
            existing = self._repository.find_cost_record_by_idempotency_key(
                job.tenant_id, idempotency_key
            )
            if existing is not None:
                duplicate_count += 1
                continue
            record = self._record_from_payload(job, payload, rules, idempotency_key)
            anomalies = self._detect_anomalies(record)
            with self._transaction_manager.begin() as unit_of_work:
                self._repository.save_cost_record(record)
                self._repository.append_event(
                    DomainEvent.create(
                        job.tenant_id,
                        record.id,
                        "cost.record.imported",
                        {
                            "record_id": record.id.value,
                            "import_job_id": job.id.value,
                            "category": record.category.value,
                            "source": record.source,
                            "amount": str(record.amount),
                            "currency": record.currency,
                        },
                    )
                )
                self._repository.append_event(
                    DomainEvent.create(
                        job.tenant_id,
                        record.id,
                        "cost.allocation.recomputed",
                        {
                            "record_id": record.id.value,
                            "allocation_count": len(record.allocations),
                            "quality_status": record.quality_status.value,
                        },
                    )
                )
                for anomaly in anomalies:
                    self._repository.save_anomaly(anomaly)
                    self._repository.append_event(
                        DomainEvent.create(
                            job.tenant_id,
                            anomaly.id,
                            "cost.anomaly.detected",
                            anomaly.as_dict(),
                        )
                    )
                unit_of_work.commit()
            imported_count += 1
            anomaly_count += len(anomalies)
            if record.quality_status is not CostQualityStatus.ALLOCATED:
                unallocated_count += 1
        return job.completed(
            imported_count,
            duplicate_count,
            anomaly_count,
            unallocated_count,
        )

    def _record_from_payload(
        self,
        job: CostImportJob,
        payload: dict[str, Any],
        rules: tuple[CostAllocationRule, ...],
        idempotency_key: str,
    ) -> CostRecord:
        external_id = str(payload.get("external_id", ""))
        category = CostCategory.from_value(str(payload.get("category", "")))
        source = FinOpsValueValidator.token(
            str(payload.get("source") or job.source), "cost source", 128
        )
        period_start = self._parse_date(payload.get("period_start"), "period_start")
        period_end = self._parse_date(payload.get("period_end"), "period_end")
        currency = FinOpsValueValidator.currency(str(payload.get("currency", "")))
        amount = FinOpsValueValidator.positive_amount(payload.get("amount", ""), "cost amount")
        owner = str(payload.get("owner", ""))
        metadata = dict(payload.get("metadata") or {})
        for key in (
            "asset_key",
            "application_key",
            "service_key",
            "cost_center",
            "environment",
            "dependency_key",
            "tags",
        ):
            if key in payload and key not in metadata:
                metadata[key] = payload[key]
        metadata.setdefault("owner", owner)
        metadata.setdefault("tenant", job.tenant_id.value)
        period = self._repository.find_period(job.tenant_id, period_start, period_end, currency)
        if period is not None and period.status is FinancialPeriodStatus.CLOSED:
            raise ValidationError("cannot import cost records into a closed financial period")
        allocations = CostAllocationEngine.allocate(
            job.tenant_id, amount, category, source, metadata, rules
        )
        return CostRecord.create(
            tenant_id=job.tenant_id,
            external_id=external_id,
            idempotency_key=idempotency_key,
            category=category.value,
            source=source,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            amount=amount,
            owner=owner,
            allocation_method=str(payload.get("allocation_method") or "rule-based"),
            metadata=metadata,
            allocations=allocations,
            import_job_id=job.id,
        )

    def _detect_anomalies(self, record: CostRecord) -> tuple[CostAnomaly, ...]:
        anomalies: list[CostAnomaly] = []
        unallocated = sum(
            (
                item.amount
                for item in record.allocations
                if item.dimension is AllocationDimension.UNALLOCATED
            ),
            Decimal("0"),
        )
        if unallocated > 0:
            unallocated_percent = min(
                Decimal("100"),
                (unallocated / record.amount * Decimal("100")).quantize(
                    FinOpsValueValidator._PERCENT_QUANTUM
                ),
            )
            anomalies.append(
                CostAnomaly.create(
                    record.tenant_id,
                    record.id,
                    "unallocated-cost",
                    Severity.WARNING,
                    "Une partie du coût reste dans le bucket de qualité financière non attribué.",
                    unallocated_percent,
                )
            )
        previous_page = self._repository.list_cost_records(
            record.tenant_id,
            Pagination.from_values(100),
            None,
            record.period_start - timedelta(days=1),
            record.currency,
            record.category.value,
            record.source,
            None,
        )
        previous = [item.amount for item in previous_page.items if item.id != record.id]
        if len(previous) >= 2:
            average = sum(previous, Decimal("0")) / Decimal(len(previous))
            if average > 0 and record.amount >= average * Decimal("1.5"):
                deviation = min(
                    Decimal("100"),
                    ((record.amount - average) / average * Decimal("100")).quantize(
                        FinOpsValueValidator._PERCENT_QUANTUM
                    ),
                )
                anomalies.append(
                    CostAnomaly.create(
                        record.tenant_id,
                        record.id,
                        "cost-spike",
                        Severity.ERROR
                        if record.amount >= average * Decimal("2")
                        else Severity.WARNING,
                        "Le coût dépasse significativement la moyenne historique comparable.",
                        deviation,
                    )
                )
        return tuple(anomalies)

    def _build_report(
        self,
        tenant_id: TenantId,
        kind: FinOpsReportKind,
        dimension: AllocationDimension,
        period_start: date,
        period_end: date,
        currency: str,
        markup: Decimal,
        records: tuple[CostRecord, ...],
        closed_period: bool,
        input_digest: str,
    ) -> tuple[FinOpsReport, tuple[FinOpsForecast, ...]]:
        grouped: dict[str, Decimal] = {}
        record_ids: dict[str, set[str]] = {}
        unallocated = Decimal("0")
        for record in records:
            allocations = self._allocations_for_dimension(record, dimension)
            for target, amount in allocations:
                grouped[target] = grouped.get(target, Decimal("0")) + amount
                record_ids.setdefault(target, set()).add(record.id.value)
                if target == "financial-quality/unallocated":
                    unallocated += amount
        factor = (
            Decimal("1") + markup / Decimal("100")
            if kind is FinOpsReportKind.CHARGEBACK
            else Decimal("1")
        )
        budgets = self._all_budgets(tenant_id, dimension, currency)
        budget_by_target = {
            item.target: item
            for item in budgets
            if item.period_start == period_start and item.period_end == period_end
        }
        anomalies = self._all_anomalies(tenant_id)
        anomaly_by_record: dict[str, int] = {}
        for anomaly in anomalies:
            anomaly_by_record[anomaly.record_id.value] = (
                anomaly_by_record.get(anomaly.record_id.value, 0) + 1
            )
        forecasts = self._build_forecasts(
            tenant_id,
            dimension,
            period_start,
            period_end,
            currency,
            grouped,
            input_digest,
        )
        forecast_by_target = {item.target: item for item in forecasts}
        lines = tuple(
            FinOpsReportLine.create(
                target=target,
                amount=(amount * factor).quantize(FinOpsValueValidator._MONEY_QUANTUM),
                record_count=len(record_ids.get(target, set())),
                budget_amount=(
                    None if target not in budget_by_target else budget_by_target[target].amount
                ),
                forecast_amount=(
                    None
                    if target not in forecast_by_target
                    else forecast_by_target[target].expected_amount
                ),
                anomaly_count=sum(
                    anomaly_by_record.get(record_id, 0)
                    for record_id in record_ids.get(target, set())
                ),
            )
            for target, amount in sorted(grouped.items())
        )
        total = sum((item.amount for item in lines), Decimal("0"))
        return (
            FinOpsReport.create(
                tenant_id=tenant_id,
                kind=kind.value,
                period_start=period_start,
                period_end=period_end,
                group_by=dimension.value,
                currency=currency,
                total_amount=total,
                unallocated_amount=(unallocated * factor).quantize(
                    FinOpsValueValidator._MONEY_QUANTUM
                ),
                chargeback_markup_percent=markup,
                lines=lines,
                input_digest=input_digest,
                closed_period=closed_period,
            ),
            forecasts,
        )

    def _build_forecasts(
        self,
        tenant_id: TenantId,
        dimension: AllocationDimension,
        period_start: date,
        period_end: date,
        currency: str,
        current_grouped: dict[str, Decimal],
        input_digest: str,
    ) -> tuple[FinOpsForecast, ...]:
        history_start = period_start - timedelta(days=366)
        history = self._all_records(
            tenant_id, history_start, period_start - timedelta(days=1), currency
        )
        by_target_month: dict[str, dict[str, Decimal]] = {}
        for record in history:
            month = record.period_start.strftime("%Y-%m")
            for target, amount in self._allocations_for_dimension(record, dimension):
                by_target_month.setdefault(target, {})[month] = (
                    by_target_month.setdefault(target, {}).get(month, Decimal("0")) + amount
                )
        targets = sorted(set(current_grouped) | set(by_target_month))
        forecasts: list[FinOpsForecast] = []
        for target in targets:
            monthly = by_target_month.get(target, {})
            if monthly:
                basis = min(12, len(monthly))
                selected = [monthly[key] for key in sorted(monthly)[-basis:]]
                expected = (sum(selected, Decimal("0")) / Decimal(basis)).quantize(
                    FinOpsValueValidator._MONEY_QUANTUM
                )
                confidence = min(Decimal("95"), Decimal("40") + Decimal(basis) * Decimal("5"))
            else:
                basis = 1
                expected = current_grouped.get(target, Decimal("0"))
                confidence = Decimal("25")
            forecasts.append(
                FinOpsForecast.create(
                    tenant_id=tenant_id,
                    dimension=dimension.value,
                    target=target,
                    period_start=period_start,
                    period_end=period_end,
                    currency=currency,
                    expected_amount=expected,
                    basis_period_count=basis,
                    confidence_percent=confidence,
                    input_digest=input_digest,
                )
            )
        return tuple(forecasts)

    def _allocations_for_dimension(
        self, record: CostRecord, dimension: AllocationDimension
    ) -> tuple[tuple[str, Decimal], ...]:
        if dimension is AllocationDimension.TENANT:
            return ((record.tenant_id.value, record.amount),)
        matching = tuple(
            (item.target, item.amount) for item in record.allocations if item.dimension is dimension
        )
        if matching:
            allocated = sum((amount for _, amount in matching), Decimal("0"))
            if allocated < record.amount:
                return (*matching, ("financial-quality/unallocated", record.amount - allocated))
            return matching
        metadata_keys = {
            AllocationDimension.ASSET: "asset_key",
            AllocationDimension.APPLICATION: "application_key",
            AllocationDimension.BUSINESS_SERVICE: "service_key",
            AllocationDimension.OWNER: "owner",
            AllocationDimension.COST_CENTER: "cost_center",
            AllocationDimension.ENVIRONMENT: "environment",
            AllocationDimension.DEPENDENCY: "dependency_key",
        }
        if dimension is AllocationDimension.TAG:
            tags = record.metadata.get("tags")
            if isinstance(tags, dict) and tags:
                key = sorted(str(item) for item in tags)[0]
                target = f"{key}:{tags[key]}"
                return ((FinOpsValueValidator.token(target, "cost tag", 192), record.amount),)
        metadata_key = metadata_keys.get(dimension)
        value = None if metadata_key is None else record.metadata.get(metadata_key)
        if value is not None and str(value).strip():
            return (
                (
                    FinOpsValueValidator.token(str(value), "finops report target", 192),
                    record.amount,
                ),
            )
        return (("financial-quality/unallocated", record.amount),)

    def _all_rules(self, tenant_id: TenantId) -> tuple[CostAllocationRule, ...]:
        items: list[CostAllocationRule] = []
        cursor: str | None = None
        while True:
            page = self._repository.list_allocation_rules(
                tenant_id, Pagination.from_values(self._PAGE_SIZE, cursor), active_only=True
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor

    def _all_records(
        self,
        tenant_id: TenantId,
        period_start: date,
        period_end: date,
        currency: str,
    ) -> tuple[CostRecord, ...]:
        FinOpsValueValidator.date_range(period_start, period_end)
        normalized_currency = FinOpsValueValidator.currency(currency)
        items: list[CostRecord] = []
        cursor: str | None = None
        while len(items) < self._MAX_ANALYTIC_RECORDS:
            page = self._repository.list_cost_records(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_ANALYTIC_RECORDS - len(items)), cursor
                ),
                period_start,
                period_end,
                normalized_currency,
                None,
                None,
                None,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor
        if cursor is not None:
            raise ValidationError("finops analytic query exceeds 100000 records")
        return tuple(items)

    def _all_budgets(
        self, tenant_id: TenantId, dimension: AllocationDimension, currency: str
    ) -> tuple[FinOpsBudget, ...]:
        items: list[FinOpsBudget] = []
        cursor: str | None = None
        while True:
            page = self._repository.list_budgets(
                tenant_id,
                Pagination.from_values(self._PAGE_SIZE, cursor),
                dimension.value,
                None,
                currency,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor

    def _all_anomalies(self, tenant_id: TenantId) -> tuple[CostAnomaly, ...]:
        items: list[CostAnomaly] = []
        cursor: str | None = None
        while True:
            page = self._repository.list_anomalies(
                tenant_id, Pagination.from_values(self._PAGE_SIZE, cursor), None
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor

    def _save_job_transition(
        self,
        old: CostImportJob,
        new: CostImportJob,
        actor: str,
        event_name: str,
        severity: Severity = Severity.INFO,
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_import_job(new)
            self._repository.append_event(
                DomainEvent.create(
                    new.tenant_id,
                    new.id,
                    event_name,
                    {
                        "job_id": new.id.value,
                        "old_status": old.status.value,
                        "new_status": new.status.value,
                        "imported_count": new.imported_count,
                        "duplicate_count": new.duplicate_count,
                        "anomaly_count": new.anomaly_count,
                        "unallocated_count": new.unallocated_count,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    new.tenant_id,
                    actor,
                    event_name,
                    "finops_import_job",
                    new.id.value,
                    metadata={"old_state": old.as_dict(), "new_state": new.as_dict()},
                    severity=severity,
                )
            )
            unit_of_work.commit()

    def _save_with_audit(
        self,
        aggregate_id: EntityId,
        tenant_id: TenantId,
        actor: str,
        event_name: str,
        target_type: str,
        metadata: dict[str, object],
        saver: Any,
        event_payload: dict[str, object] | None = None,
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            saver()
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    aggregate_id,
                    event_name,
                    dict(event_payload or metadata),
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    actor,
                    event_name,
                    target_type,
                    aggregate_id.value,
                    metadata=dict(metadata),
                )
            )
            unit_of_work.commit()

    def _required_import_job(self, tenant_id: TenantId, job_id: str) -> CostImportJob:
        job = self._repository.get_import_job(tenant_id, job_id)
        if job is None:
            raise NotFoundError("finops import job does not exist")
        return job

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized_tenant = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized_tenant.value, token, permission)
        )
        return normalized_tenant, principal

    @staticmethod
    def _parse_date(value: object, label: str) -> date:
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError(f"{label} must use ISO-8601 YYYY-MM-DD") from exc

    @staticmethod
    def _records_digest(records: tuple[CostRecord, ...]) -> str:
        payload = [item.as_dict() for item in sorted(records, key=lambda item: item.id.value)]
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
