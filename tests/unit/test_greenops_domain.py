from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.greenops import (
    CapacityDimension,
    CarbonFactor,
    ConsolidationAction,
    EnergyMeasurement,
    EnergyScope,
    GreenOpsPolicy,
    GreenOpsValidator,
    MeasurementKind,
    MeasurementSource,
)


def test_greenops_value_objects_validate_and_normalize() -> None:
    tenant = TenantId.from_value("default")
    source = MeasurementSource.create(
        tenant, "dcim-meter-01", "Main meter", "dcim", "facilities.team"
    )
    assert source.code == "dcim-meter-01"
    assert source.active is True
    factor = CarbonFactor.create(
        tenant,
        "FR-RTE-2026",
        "FR",
        "42.75",
        "RTE",
        date(2026, 1, 1),
        date(2026, 12, 31),
        "https://example.invalid/factors/fr-2026",
    )
    assert factor.grams_co2e_per_kwh == Decimal("42.750000")
    policy = GreenOpsPolicy.create(
        tenant,
        "PAR-01",
        "1.35",
        "0.21",
        "EUR",
        factor.code,
        "20",
        "80",
        "90",
        3,
    )
    assert policy.default_pue == Decimal("1.350000")
    assert EnergyScope.from_value("equipment") is EnergyScope.ASSET
    assert MeasurementKind.from_value("observed") is MeasurementKind.OBSERVED
    assert CapacityDimension.from_value("thermal") is CapacityDimension.COOLING
    assert ConsolidationAction.CONSOLIDATE.value == "consolidate"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"api_token": "secret"}, "sensitive key"),
        ({"nested": {"private-key": "secret"}}, "sensitive key"),
    ],
)
def test_greenops_metadata_rejects_sensitive_keys(payload: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        GreenOpsValidator.json_object(payload, "metadata")


def test_energy_measurement_distinguishes_observed_and_estimated_values() -> None:
    tenant = TenantId.from_value("default")
    start = datetime(2026, 7, 1, tzinfo=UTC)
    observed = EnergyMeasurement.create(
        tenant,
        "greenops-observed-0001",
        "dcim-meter-01",
        "observed",
        "rack",
        "rack-a01",
        "par-01",
        start,
        start + timedelta(hours=1),
        "12.5",
        it_energy_kwh="10",
        facility_energy_kwh="12.5",
        utilization_percent="18",
        energy_capacity_percent="72",
        metadata={"meter": "rack-a"},
    )
    estimated = EnergyMeasurement.create(
        tenant,
        "greenops-estimated-0001",
        "dcim-meter-01",
        "estimated",
        "asset",
        "server-001",
        "par-01",
        start,
        start + timedelta(hours=1),
        "1.5",
        utilization_percent="12",
        metadata={"method": "rated-power"},
    )
    assert observed.kind is MeasurementKind.OBSERVED
    assert observed.capacity_values()[CapacityDimension.ENERGY] == Decimal("72.0000")
    assert estimated.kind is MeasurementKind.ESTIMATED
    assert estimated.as_dict()["metadata"] == {"method": "rated-power"}


def test_greenops_invalid_ranges_and_values_are_rejected() -> None:
    tenant = TenantId.from_value("default")
    start = datetime(2026, 7, 1, tzinfo=UTC)
    with pytest.raises(ValidationError, match="after period_start"):
        EnergyMeasurement.create(
            tenant,
            "greenops-invalid-0001",
            "meter",
            "observed",
            "site",
            "par-01",
            "par-01",
            start,
            start,
            "1",
        )
    with pytest.raises(ValidationError, match="between 0 and 100"):
        EnergyMeasurement.create(
            tenant,
            "greenops-invalid-0002",
            "meter",
            "observed",
            "site",
            "par-01",
            "par-01",
            start,
            start + timedelta(hours=1),
            "1",
            utilization_percent="101",
        )
    with pytest.raises(ValidationError, match="unsupported"):
        EnergyScope.from_value("planet")
