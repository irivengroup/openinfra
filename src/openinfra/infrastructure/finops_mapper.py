from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Any

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.finops import (
    CostAllocation,
    CostAllocationRule,
    CostAnomaly,
    CostImportJob,
    CostRecord,
    FinancialPeriod,
    FinOpsBudget,
    FinOpsForecast,
    FinOpsReport,
    FinOpsReportLine,
)


class FinOpsRecordMapper:
    @classmethod
    def allocation_rule(cls, value: Mapping[str, Any]) -> CostAllocationRule:
        return CostAllocationRule.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            name=str(value["name"]),
            priority=int(value["priority"]),
            category=cls._optional_text(value.get("category")),
            source=cls._optional_text(value.get("source")),
            dimension=str(value["dimension"]),
            selector_key=str(value["selector_key"]),
            fixed_target=cls._optional_text(value.get("fixed_target")),
            percentage=str(value["percentage"]),
            active=bool(value.get("active", True)),
            created_at=cls._datetime(value["created_at"]),
            updated_at=cls._datetime(value["updated_at"]),
            version=int(value["version"]),
        )

    @classmethod
    def allocation(cls, value: Mapping[str, Any]) -> CostAllocation:
        rule_id = value.get("rule_id")
        return CostAllocation.create(
            dimension=str(value["dimension"]),
            target=str(value["target"]),
            percentage=str(value["percentage"]),
            amount=str(value["amount"]),
            rule_id=None if rule_id in (None, "") else EntityId.from_value(str(rule_id)),
        )

    @classmethod
    def cost_record(cls, value: Mapping[str, Any]) -> CostRecord:
        return CostRecord.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            external_id=str(value["external_id"]),
            idempotency_key=str(value["idempotency_key"]),
            category=str(value["category"]),
            source=str(value["source"]),
            period_start=cls._date(value["period_start"]),
            period_end=cls._date(value["period_end"]),
            currency=str(value["currency"]),
            amount=str(value["amount"]),
            owner=str(value["owner"]),
            allocation_method=str(value["allocation_method"]),
            metadata=cls._mapping(value.get("metadata")),
            allocations=tuple(
                cls.allocation(item) for item in cls._mapping_list(value.get("allocations"))
            ),
            imported_at=cls._datetime(value["imported_at"]),
            import_job_id=EntityId.from_value(str(value["import_job_id"])),
        )

    @classmethod
    def import_job(cls, value: Mapping[str, Any]) -> CostImportJob:
        return CostImportJob.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            idempotency_key=str(value["idempotency_key"]),
            source=str(value["source"]),
            records=tuple(dict(item) for item in cls._mapping_list(value.get("records"))),
            payload_sha256=str(value["payload_sha256"]),
            status=str(value["status"]),
            submitted_at=cls._datetime(value["submitted_at"]),
            started_at=cls._optional_datetime(value.get("started_at")),
            completed_at=cls._optional_datetime(value.get("completed_at")),
            failure_reason=cls._optional_text(value.get("failure_reason")),
            imported_count=int(value.get("imported_count", 0)),
            duplicate_count=int(value.get("duplicate_count", 0)),
            anomaly_count=int(value.get("anomaly_count", 0)),
            unallocated_count=int(value.get("unallocated_count", 0)),
            version=int(value["version"]),
        )

    @classmethod
    def period(cls, value: Mapping[str, Any]) -> FinancialPeriod:
        return FinancialPeriod.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            period_start=cls._date(value["period_start"]),
            period_end=cls._date(value["period_end"]),
            currency=str(value["currency"]),
            status=str(value["status"]),
            closed_at=cls._optional_datetime(value.get("closed_at")),
            closed_by=cls._optional_text(value.get("closed_by")),
            source_digest=cls._optional_text(value.get("source_digest")),
            created_at=cls._datetime(value["created_at"]),
        )

    @classmethod
    def budget(cls, value: Mapping[str, Any]) -> FinOpsBudget:
        return FinOpsBudget.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            dimension=str(value["dimension"]),
            target=str(value["target"]),
            period_start=cls._date(value["period_start"]),
            period_end=cls._date(value["period_end"]),
            currency=str(value["currency"]),
            amount=str(value["amount"]),
            warning_threshold_percent=str(value["warning_threshold_percent"]),
            owner=str(value["owner"]),
            created_at=cls._datetime(value["created_at"]),
            updated_at=cls._datetime(value["updated_at"]),
            version=int(value["version"]),
        )

    @classmethod
    def anomaly(cls, value: Mapping[str, Any]) -> CostAnomaly:
        return CostAnomaly.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            record_id=EntityId.from_value(str(value["record_id"])),
            code=str(value["code"]),
            severity=str(value["severity"]),
            message=str(value["message"]),
            deviation_percent=str(value["deviation_percent"]),
            detected_at=cls._datetime(value["detected_at"]),
        )

    @classmethod
    def forecast(cls, value: Mapping[str, Any]) -> FinOpsForecast:
        return FinOpsForecast.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            dimension=str(value["dimension"]),
            target=str(value["target"]),
            period_start=cls._date(value["period_start"]),
            period_end=cls._date(value["period_end"]),
            currency=str(value["currency"]),
            expected_amount=str(value["expected_amount"]),
            basis_period_count=int(value["basis_period_count"]),
            confidence_percent=str(value["confidence_percent"]),
            input_digest=str(value["input_digest"]),
            generated_at=cls._datetime(value["generated_at"]),
        )

    @classmethod
    def report_line(cls, value: Mapping[str, Any]) -> FinOpsReportLine:
        return FinOpsReportLine.create(
            target=str(value["target"]),
            amount=str(value["amount"]),
            record_count=int(value["record_count"]),
            budget_amount=cls._optional_decimal_text(value.get("budget_amount")),
            forecast_amount=cls._optional_decimal_text(value.get("forecast_amount")),
            anomaly_count=int(value.get("anomaly_count", 0)),
        )

    @classmethod
    def report(cls, value: Mapping[str, Any]) -> FinOpsReport:
        return FinOpsReport.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            kind=str(value["kind"]),
            period_start=cls._date(value["period_start"]),
            period_end=cls._date(value["period_end"]),
            group_by=str(value["group_by"]),
            currency=str(value["currency"]),
            total_amount=str(value["total_amount"]),
            unallocated_amount=str(value["unallocated_amount"]),
            chargeback_markup_percent=str(value["chargeback_markup_percent"]),
            lines=tuple(cls.report_line(item) for item in cls._mapping_list(value.get("lines"))),
            input_digest=str(value["input_digest"]),
            closed_period=bool(value.get("closed_period", False)),
            generated_at=cls._datetime(value["generated_at"]),
        )

    @staticmethod
    def _date(value: object) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError("finops record date is invalid") from exc

    @staticmethod
    def _datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError("finops record datetime is invalid") from exc
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @classmethod
    def _optional_datetime(cls, value: object) -> datetime | None:
        return None if value in (None, "") else cls._datetime(value)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return None if value in (None, "") else str(value)

    @staticmethod
    def _optional_decimal_text(value: object) -> str | None:
        return None if value in (None, "") else str(value)

    @staticmethod
    def _mapping(value: object) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValidationError("finops record JSON object is invalid")
        return {str(key): item for key, item in value.items()}

    @classmethod
    def _mapping_list(cls, value: object) -> list[Mapping[str, Any]]:
        if value is None:
            return []
        if not isinstance(value, list | tuple):
            raise ValidationError("finops record JSON array is invalid")
        result: list[Mapping[str, Any]] = []
        for item in value:
            if not isinstance(item, Mapping):
                raise ValidationError("finops record object array is invalid")
            result.append(item)
        return result
