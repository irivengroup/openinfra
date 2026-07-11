from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.greenops import (
    CapacityForecast,
    CarbonEstimate,
    CarbonFactor,
    ConsolidationCandidate,
    EnergyAnomaly,
    EnergyMeasurement,
    GreenOpsPolicy,
    GreenScore,
    MeasurementSource,
    SustainabilityReport,
)


class GreenOpsRecordMapper:
    @staticmethod
    def _datetime(value: object, field: str) -> datetime:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError(f"invalid GreenOps datetime: {field}") from exc

    @staticmethod
    def _date(value: object, field: str) -> date:
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError(f"invalid GreenOps date: {field}") from exc

    @staticmethod
    def _mapping(value: object, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{field} must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @classmethod
    def source(cls, value: dict[str, Any]) -> MeasurementSource:
        return MeasurementSource.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["code"]),
            str(value["name"]),
            str(value["source_type"]),
            str(value["owner"]),
            bool(value["active"]),
            cls._datetime(value["created_at"], "created_at"),
        )

    @classmethod
    def factor(cls, value: dict[str, Any]) -> CarbonFactor:
        return CarbonFactor.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["code"]),
            str(value["region"]),
            str(value["grams_co2e_per_kwh"]),
            str(value["source_name"]),
            None if value.get("source_uri") is None else str(value["source_uri"]),
            cls._date(value["period_start"], "period_start"),
            cls._date(value["period_end"], "period_end"),
            cls._datetime(value["created_at"], "created_at"),
        )

    @classmethod
    def policy(cls, value: dict[str, Any]) -> GreenOpsPolicy:
        return GreenOpsPolicy.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["site_code"]),
            str(value["default_pue"]),
            str(value["energy_cost_per_kwh"]),
            str(value["currency"]),
            str(value["carbon_factor_code"]),
            str(value["underutilized_percent"]),
            str(value["warning_capacity_percent"]),
            str(value["critical_capacity_percent"]),
            int(value["minimum_samples"]),
            cls._datetime(value["updated_at"], "updated_at"),
        )

    @classmethod
    def measurement(cls, value: dict[str, Any]) -> EnergyMeasurement:
        def optional(key: str) -> str | None:
            return None if value.get(key) is None else str(value[key])

        return EnergyMeasurement.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["idempotency_key"]),
            str(value["source_code"]),
            str(value["kind"]),
            str(value["scope"]),
            str(value["scope_key"]),
            str(value["site_code"]),
            optional("application_key"),
            cls._datetime(value["period_start"], "period_start"),
            cls._datetime(value["period_end"], "period_end"),
            str(value["energy_kwh"]),
            optional("it_energy_kwh"),
            optional("facility_energy_kwh"),
            optional("utilization_percent"),
            optional("energy_capacity_percent"),
            optional("cooling_capacity_percent"),
            optional("space_capacity_percent"),
            optional("weight_capacity_percent"),
            cls._mapping(value.get("metadata", {}), "measurement metadata"),
            cls._datetime(value["recorded_at"], "recorded_at"),
        )

    @classmethod
    def anomaly(cls, value: dict[str, Any]) -> EnergyAnomaly:
        return EnergyAnomaly.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["site_code"]),
            str(value["scope"]),
            str(value["scope_key"]),
            str(value["kind"]),
            str(value["severity"]),
            str(value["observed_value"]),
            str(value["baseline_value"]),
            str(value["description"]),
            cls._datetime(value["detected_at"], "detected_at"),
        )

    @classmethod
    def forecast(cls, value: dict[str, Any]) -> CapacityForecast:
        projected = value.get("projected_saturation_at")
        return CapacityForecast.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["site_code"]),
            str(value["scope"]),
            str(value["scope_key"]),
            str(value["dimension"]),
            str(value["current_percent"]),
            str(value["daily_growth_percent"]),
            None if projected is None else cls._date(projected, "projected_saturation_at"),
            str(value["confidence_percent"]),
            int(value["sample_count"]),
            str(value["source_digest"]),
            cls._datetime(value["generated_at"], "generated_at"),
        )

    @classmethod
    def candidate(cls, value: dict[str, Any]) -> ConsolidationCandidate:
        return ConsolidationCandidate.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["site_code"]),
            str(value["scope"]),
            str(value["scope_key"]),
            str(value["action"]),
            str(value["rationale"]),
            str(value["estimated_annual_energy_saving_kwh"]),
            str(value["estimated_annual_carbon_saving_kg"]),
            str(value["risk_level"]),
            bool(value["requires_human_approval"]),
            str(value["source_digest"]),
            cls._datetime(value["generated_at"], "generated_at"),
        )

    @classmethod
    def score(cls, value: dict[str, Any]) -> GreenScore:
        return GreenScore.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["scope"]),
            str(value["score"]),
            str(value["pue_component"]),
            str(value["capacity_component"]),
            str(value["data_quality_component"]),
            cls._date(value["period_start"], "period_start"),
            cls._date(value["period_end"], "period_end"),
            cls._datetime(value["generated_at"], "generated_at"),
        )

    @classmethod
    def report(cls, value: dict[str, Any]) -> SustainabilityReport:
        carbon = cls._mapping(value["carbon_estimate"], "carbon estimate")
        score = cls._mapping(value["green_score"], "green score")
        estimate = CarbonEstimate(
            energy_kwh=Decimal(str(carbon["energy_kwh"])),
            kilograms_co2e=Decimal(str(carbon["kilograms_co2e"])),
            factor_code=str(carbon["factor_code"]),
            factor_grams_co2e_per_kwh=Decimal(str(carbon["factor_grams_co2e_per_kwh"])),
            factor_source=str(carbon["factor_source"]),
            factor_source_uri=None
            if carbon.get("factor_source_uri") is None
            else str(carbon["factor_source_uri"]),
            factor_period_start=cls._date(carbon["factor_period_start"], "factor_period_start"),
            factor_period_end=cls._date(carbon["factor_period_end"], "factor_period_end"),
            scope=str(carbon["scope"]),
        )
        green_score = cls.score(score)
        return SustainabilityReport.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["site_code"]),
            str(value["scope"]),
            cls._date(value["period_start"], "period_start"),
            cls._date(value["period_end"], "period_end"),
            str(value["total_energy_kwh"]),
            str(value["it_energy_kwh"]),
            str(value["facility_energy_kwh"]),
            str(value["pue"]),
            str(value["pue_source"]),
            str(value["energy_cost"]),
            str(value["currency"]),
            estimate,
            green_score,
            int(value["measurement_count"]),
            int(value["observed_measurement_count"]),
            int(value["estimated_measurement_count"]),
            tuple(str(item) for item in value.get("anomaly_ids", [])),
            tuple(str(item) for item in value.get("forecast_ids", [])),
            tuple(str(item) for item in value.get("candidate_ids", [])),
            tuple(str(item) for item in value.get("assumptions", [])),
            str(value["input_digest"]),
            cls._datetime(value["generated_at"], "generated_at"),
        )
