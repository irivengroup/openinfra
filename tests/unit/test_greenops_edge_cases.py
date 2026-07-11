from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.greenops import (
    CapacityDimension,
    CapacityForecast,
    CarbonEstimate,
    CarbonFactor,
    ConsolidationAction,
    ConsolidationCandidate,
    EnergyAnomaly,
    EnergyMeasurement,
    EnergyScope,
    GreenOpsPolicy,
    GreenOpsValidator,
    GreenScore,
    MeasurementKind,
    MeasurementSource,
    SustainabilityReport,
)
from openinfra.infrastructure.greenops_mapper import GreenOpsRecordMapper


def _tenant() -> TenantId:
    return TenantId.from_value("default")


def _now() -> datetime:
    return datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda: MeasurementKind.from_value("computed"), "observed or estimated"),
        (lambda: CapacityDimension.from_value("cpu"), "unsupported"),
        (lambda: GreenOpsValidator.text("", "name"), "1 to"),
        (lambda: GreenOpsValidator.token("bad value", "token"), "safe characters"),
        (lambda: GreenOpsValidator.idempotency_key("short"), "8 to 192"),
        (lambda: GreenOpsValidator.decimal("not-a-number", "value"), "finite decimal"),
        (lambda: GreenOpsValidator.decimal("NaN", "value"), "non-negative"),
        (lambda: GreenOpsValidator.decimal("-1", "value"), "non-negative"),
        (
            lambda: GreenOpsValidator.decimal("0", "value", positive=True),
            "strictly positive",
        ),
        (
            lambda: GreenOpsValidator.decimal("1000000000000000000", "value"),
            "supported range",
        ),
        (lambda: GreenOpsValidator.aware_datetime(datetime(2026, 1, 1), "date"), "timezone"),
        (
            lambda: GreenOpsValidator.time_range(_now(), _now() + timedelta(days=3661)),
            "ten years",
        ),
        (
            lambda: GreenOpsValidator.date_range(date(2026, 2, 1), date(2026, 1, 1)),
            "must not precede",
        ),
        (
            lambda: GreenOpsValidator.date_range(date(2020, 1, 1), date(2031, 1, 2)),
            "ten years",
        ),
        (
            lambda: GreenOpsValidator.json_object([], "metadata"),  # type: ignore[arg-type]
            "JSON object",
        ),
        (
            lambda: GreenOpsValidator.json_object({"value": object()}, "metadata"),
            "JSON serializable",
        ),
        (
            lambda: GreenOpsValidator.json_object({"value": "x" * 131_073}, "metadata"),
            "128 KiB",
        ),
    ],
)
def test_greenops_validation_error_paths(operation, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        operation()


def test_greenops_validator_optional_and_nested_sequence_paths() -> None:
    assert GreenOpsValidator.optional_text(None, "value") is None
    assert GreenOpsValidator.optional_text("   ", "value") is None
    assert GreenOpsValidator.json_object({"items": ({"label": "ok"}, 2)}, "metadata") == {
        "items": [{"label": "ok"}, 2]
    }
    assert len(GreenOpsValidator.digest({"b": 2, "a": 1})) == 64


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: CarbonFactor.create(
                _tenant(),
                "fr-2026",
                "fr",
                "50",
                "RTE",
                date(2026, 1, 1),
                date(2026, 12, 31),
                "http://example.invalid/factor",
            ),
            "must use HTTPS",
        ),
        (
            lambda: GreenOpsPolicy.create(_tenant(), "par-01", "0.9", "0.2", "EUR", "fr-2026"),
            "between 1 and 5",
        ),
        (
            lambda: GreenOpsPolicy.create(
                _tenant(),
                "par-01",
                "1.4",
                "0.2",
                "EUR",
                "fr-2026",
                warning_capacity_percent="95",
                critical_capacity_percent="90",
            ),
            "lower than critical",
        ),
        (
            lambda: GreenOpsPolicy.create(_tenant(), "par-01", "1.4", "0.2", "EURO", "fr-2026"),
            "ISO-4217",
        ),
        (
            lambda: GreenOpsPolicy.create(
                _tenant(),
                "par-01",
                "1.4",
                "0.2",
                "EUR",
                "fr-2026",
                minimum_samples=1,
            ),
            "between 2 and 120",
        ),
        (
            lambda: EnergyMeasurement.create(
                _tenant(),
                "greenops-invalid-energy-0001",
                "meter",
                "observed",
                "site",
                "par-01",
                "par-01",
                _now(),
                _now() + timedelta(hours=1),
                "10",
                it_energy_kwh="10",
                facility_energy_kwh="9",
            ),
            "cannot be lower",
        ),
        (
            lambda: CapacityForecast.create(
                _tenant(),
                "par-01",
                EnergyScope.SITE,
                "par-01",
                CapacityDimension.ENERGY,
                Decimal("80"),
                Decimal("1"),
                None,
                Decimal("90"),
                3,
                "invalid",
            ),
            "SHA-256",
        ),
        (
            lambda: ConsolidationCandidate.create(
                _tenant(),
                "par-01",
                EnergyScope.ASSET,
                "server-001",
                ConsolidationAction.CONSOLIDATE,
                "Underutilized asset",
                Decimal("100"),
                Decimal("10"),
                Severity.WARNING,
                "invalid",
            ),
            "SHA-256",
        ),
    ],
)
def test_greenops_domain_rejects_invalid_business_values(factory, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        factory()


def test_greenops_restore_roundtrips_and_human_approval_guard() -> None:
    tenant = _tenant()
    now = _now()
    digest = "a" * 64
    source = MeasurementSource.create(tenant, "meter", "Meter", "dcim", "Facilities")
    factor = CarbonFactor.create(
        tenant,
        "fr-2026",
        "fr",
        "50",
        "RTE",
        date(2026, 1, 1),
        date(2026, 12, 31),
        "https://example.invalid/factor",
    )
    policy = GreenOpsPolicy.create(tenant, "par-01", "1.4", "0.2", "EUR", factor.code)
    measurement = EnergyMeasurement.create(
        tenant,
        "greenops-roundtrip-0001",
        source.code,
        "observed",
        "rack",
        "rack-a01",
        "par-01",
        now,
        now + timedelta(hours=1),
        "12",
        application_key="billing",
        it_energy_kwh="10",
        facility_energy_kwh="12",
        cooling_capacity_percent="50",
        space_capacity_percent="60",
        weight_capacity_percent="70",
        metadata={"labels": ["dcim", "meter"]},
    )
    anomaly = EnergyAnomaly.create(
        tenant,
        "par-01",
        EnergyScope.RACK,
        "rack-a01",
        "energy-spike",
        Severity.WARNING,
        Decimal("12"),
        Decimal("8"),
        "Energy increase",
    )
    forecast = CapacityForecast.create(
        tenant,
        "par-01",
        EnergyScope.RACK,
        "rack-a01",
        CapacityDimension.ENERGY,
        Decimal("80"),
        Decimal("1"),
        date(2026, 8, 1),
        Decimal("90"),
        3,
        digest,
    )
    candidate = ConsolidationCandidate.create(
        tenant,
        "par-01",
        EnergyScope.ASSET,
        "server-001",
        ConsolidationAction.CONSOLIDATE,
        "Underutilized asset",
        Decimal("100"),
        Decimal("5"),
        Severity.WARNING,
        digest,
    )
    score = GreenScore.create(
        tenant,
        "site:par-01",
        Decimal("80"),
        Decimal("75"),
        Decimal("85"),
        Decimal("90"),
        date(2026, 7, 1),
        date(2026, 7, 31),
    )
    estimate = CarbonEstimate(
        Decimal("12"),
        Decimal("0.6"),
        factor.code,
        factor.grams_co2e_per_kwh,
        factor.source_name,
        factor.source_uri,
        factor.period_start,
        factor.period_end,
        "rack:rack-a01",
    )
    report = SustainabilityReport.create(
        tenant,
        "par-01",
        "rack:rack-a01",
        date(2026, 7, 1),
        date(2026, 7, 31),
        Decimal("12"),
        Decimal("10"),
        Decimal("12"),
        Decimal("1.2"),
        "measured",
        Decimal("2.4"),
        "EUR",
        estimate,
        score,
        1,
        1,
        0,
        (anomaly.id.value,),
        (forecast.id.value,),
        (candidate.id.value,),
        ("observed",),
        digest,
    )

    assert GreenOpsRecordMapper.source(source.as_dict()).id == source.id
    assert GreenOpsRecordMapper.factor(factor.as_dict()).id == factor.id
    assert GreenOpsRecordMapper.policy(policy.as_dict()).id == policy.id
    assert GreenOpsRecordMapper.measurement(measurement.as_dict()).input_digest()
    assert GreenOpsRecordMapper.anomaly(anomaly.as_dict()).id == anomaly.id
    assert GreenOpsRecordMapper.forecast(forecast.as_dict()).projected_saturation_at == date(
        2026, 8, 1
    )
    assert GreenOpsRecordMapper.candidate(candidate.as_dict()).requires_human_approval is True
    assert GreenOpsRecordMapper.score(score.as_dict()).id == score.id
    restored_report = GreenOpsRecordMapper.report(report.as_dict())
    assert restored_report.reproducibility_key() == report.reproducibility_key()

    invalid_candidate = candidate.as_dict()
    invalid_candidate["requires_human_approval"] = False
    with pytest.raises(ValidationError, match="human approval"):
        GreenOpsRecordMapper.candidate(invalid_candidate)


@pytest.mark.parametrize(
    ("payload", "method", "message"),
    [
        ({"created_at": "invalid"}, "_datetime", "invalid GreenOps datetime"),
        ({"period_start": "invalid"}, "_date", "invalid GreenOps date"),
        ({"metadata": []}, "_mapping", "JSON object"),
    ],
)
def test_greenops_mapper_rejects_invalid_scalar_payloads(
    payload: dict[str, object], method: str, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        if method == "_datetime":
            GreenOpsRecordMapper._datetime(payload["created_at"], "created_at")
        elif method == "_date":
            GreenOpsRecordMapper._date(payload["period_start"], "period_start")
        else:
            GreenOpsRecordMapper._mapping(payload["metadata"], "metadata")


def test_greenops_report_and_candidate_restore_validation_paths() -> None:
    tenant = _tenant()
    score = GreenScore.create(
        tenant,
        "site:par-01",
        Decimal("80"),
        Decimal("80"),
        Decimal("80"),
        Decimal("80"),
        date(2026, 7, 1),
        date(2026, 7, 31),
    )
    estimate = CarbonEstimate(
        Decimal("1"),
        Decimal("0.05"),
        "fr-2026",
        Decimal("50"),
        "RTE",
        None,
        date(2026, 1, 1),
        date(2026, 12, 31),
        "site:par-01",
    )
    common = {
        "tenant_id": tenant,
        "site_code": "par-01",
        "scope": "site:par-01",
        "period_start": date(2026, 7, 1),
        "period_end": date(2026, 7, 31),
        "total_energy_kwh": Decimal("1"),
        "it_energy_kwh": Decimal("1"),
        "facility_energy_kwh": Decimal("1"),
        "pue": Decimal("1"),
        "pue_source": "measured",
        "energy_cost": Decimal("0.2"),
        "carbon_estimate": estimate,
        "green_score": score,
        "measurement_count": 1,
        "observed_measurement_count": 1,
        "estimated_measurement_count": 0,
        "anomaly_ids": (),
        "forecast_ids": (),
        "candidate_ids": (),
        "assumptions": (),
    }
    with pytest.raises(ValidationError, match="input digest"):
        SustainabilityReport.create(currency="EUR", input_digest="bad", **common)
    with pytest.raises(ValidationError, match="ISO-4217"):
        SustainabilityReport.create(currency="EURO", input_digest="a" * 64, **common)

    with pytest.raises(ValidationError, match="human approval"):
        ConsolidationCandidate.restore(
            EntityId.new(),
            tenant,
            "par-01",
            "asset",
            "server-001",
            "consolidate",
            "Underutilized asset",
            "100",
            "5",
            "warning",
            False,
            "a" * 64,
            _now(),
        )
