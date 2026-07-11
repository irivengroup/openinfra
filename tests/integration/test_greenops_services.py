from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.greenops_services import (
    CreateCarbonFactorCommand,
    CreateMeasurementSourceCommand,
    ExportSustainabilityReportCommand,
    GenerateSustainabilityReportCommand,
    GetGreenOpsPolicyCommand,
    GetSustainabilityReportCommand,
    IngestEnergyMeasurementCommand,
    ListCapacityForecastsCommand,
    ListCarbonFactorsCommand,
    ListConsolidationCandidatesCommand,
    ListEnergyAnomaliesCommand,
    ListEnergyMeasurementsCommand,
    ListGreenScoresCommand,
    ListMeasurementSourcesCommand,
    ListSustainabilityReportsCommand,
    UpsertGreenOpsPolicyCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import NotFoundError, ValidationError


def _application(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "g" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "greenops-admin", ("admin",), token)
    )
    return app, token


def _configure(app, token: str) -> None:
    service = app.greenops_service
    service.create_source(
        CreateMeasurementSourceCommand(
            "default", token, "pytest", "dcim-meter", "DCIM meter", "dcim", "facilities"
        )
    )
    service.create_carbon_factor(
        CreateCarbonFactorCommand(
            "default",
            token,
            "pytest",
            "fr-2026",
            "fr",
            "50",
            "RTE",
            date(2026, 1, 1),
            date(2026, 12, 31),
            "https://example.invalid/rte/fr-2026",
        )
    )
    service.upsert_policy(
        UpsertGreenOpsPolicyCommand(
            "default", token, "pytest", "par-01", "1.4", "0.20", "EUR", "fr-2026"
        )
    )


def _ingest(
    app,
    token: str,
    key: str,
    start: datetime,
    energy: str,
    *,
    scope: str = "site",
    scope_key: str = "par-01",
    utilization: str | None = None,
    capacity: str | None = None,
    kind: str = "observed",
) -> None:
    app.greenops_service.ingest_measurement(
        IngestEnergyMeasurementCommand(
            "default",
            token,
            "pytest",
            key,
            "dcim-meter",
            kind,
            scope,
            scope_key,
            "par-01",
            start,
            start + timedelta(days=1),
            energy,
            utilization_percent=utilization,
            energy_capacity_percent=capacity,
            metadata={"collector": "pytest"},
        )
    )


def test_greenops_end_to_end_reports_forecasts_anomalies_and_exports(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    _configure(app, token)
    service = app.greenops_service
    assert service.list_sources(ListMeasurementSourcesCommand("default", token)).items
    assert service.list_carbon_factors(ListCarbonFactorsCommand("default", token)).items
    assert (
        service.get_policy(GetGreenOpsPolicyCommand("default", token, "par-01")).currency == "EUR"
    )

    start = datetime(2026, 7, 1, tzinfo=UTC)
    for index, (energy, capacity) in enumerate((("100", "40"), ("110", "60"), ("250", "85"))):
        _ingest(
            app,
            token,
            f"greenops-site-{index:04d}",
            start + timedelta(days=index),
            energy,
            capacity=capacity,
        )
    for index, utilization in enumerate(("15", "12", "10")):
        _ingest(
            app,
            token,
            f"greenops-asset-{index:04d}",
            start + timedelta(days=index),
            "10",
            scope="asset",
            scope_key="server-001",
            utilization=utilization,
            capacity="20",
            kind="estimated" if index == 0 else "observed",
        )

    report = service.generate_report(
        GenerateSustainabilityReportCommand(
            "default", token, "pytest", "par-01", date(2026, 7, 1), date(2026, 7, 3)
        )
    )
    assert report.pue == Decimal("1.400000")
    assert report.pue_source == "policy-estimate"
    assert report.carbon_estimate.factor_source == "RTE"
    assert report.carbon_estimate.factor_period_start == date(2026, 1, 1)
    assert report.as_dict()["production_mutation"] is False
    assert report.assumptions
    assert (
        service.generate_report(
            GenerateSustainabilityReportCommand(
                "default", token, "pytest", "par-01", date(2026, 7, 1), date(2026, 7, 3)
            )
        ).id
        == report.id
    )
    assert (
        service.get_report(GetSustainabilityReportCommand("default", token, report.id.value)).id
        == report.id
    )
    assert service.list_reports(ListSustainabilityReportsCommand("default", token)).items
    assert service.list_anomalies(ListEnergyAnomaliesCommand("default", token)).items
    assert service.list_forecasts(ListCapacityForecastsCommand("default", token)).items
    candidates = service.list_candidates(
        ListConsolidationCandidatesCommand("default", token, site_code="par-01")
    ).items
    assert candidates and all(item.requires_human_approval for item in candidates)
    assert service.list_scores(ListGreenScoresCommand("default", token)).items
    assert (
        len(service.list_measurements(ListEnergyMeasurementsCommand("default", token)).items) == 6
    )

    json_export = service.export_report(
        ExportSustainabilityReportCommand("default", token, report.id.value, "json")
    )
    csv_export = service.export_report(
        ExportSustainabilityReportCommand("default", token, report.id.value, "csv")
    )
    assert json.loads(json_export.content)["id"] == report.id.value
    assert b"kilograms_co2e" in csv_export.content
    with pytest.raises(ValidationError, match="json or csv"):
        service.export_report(
            ExportSustainabilityReportCommand("default", token, report.id.value, "xlsx")
        )

    event_names = {value["name"] for value in app.store.data["greenops_event_outbox"].values()}
    assert {
        "green.energy.anomaly.detected",
        "green.capacity.forecast.updated",
        "green.report.generated",
    }.issubset(event_names)
    assert any(
        event.action == "green.report.generated" for event in app.audit_repository.list_events()
    )


def test_greenops_idempotency_security_and_missing_dependencies(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    service = app.greenops_service
    source_command = CreateMeasurementSourceCommand(
        "default", token, "pytest", "meter", "Meter", "manual", "facilities"
    )
    source = service.create_source(source_command)
    assert service.create_source(source_command).id == source.id
    with pytest.raises(ValidationError, match="already exists"):
        service.create_source(
            CreateMeasurementSourceCommand(
                "default", token, "pytest", "meter", "Other", "manual", "facilities"
            )
        )
    start = datetime(2026, 7, 1, tzinfo=UTC)
    command = IngestEnergyMeasurementCommand(
        "default",
        token,
        "pytest",
        "greenops-idempotent-0001",
        "meter",
        "observed",
        "site",
        "par-01",
        "par-01",
        start,
        start + timedelta(hours=1),
        "10",
    )
    measurement = service.ingest_measurement(command)
    assert service.ingest_measurement(command).id == measurement.id
    with pytest.raises(ValidationError, match="another payload"):
        service.ingest_measurement(replace(command, energy_kwh="11"))
    with pytest.raises(ValidationError, match="source is missing"):
        service.ingest_measurement(
            replace(command, idempotency_key="greenops-idempotent-0002", source_code="missing")
        )
    with pytest.raises(ValidationError, match="policy must be configured"):
        service.generate_report(
            GenerateSustainabilityReportCommand(
                "default", token, "pytest", "par-01", date(2026, 7, 1), date(2026, 7, 1)
            )
        )
    with pytest.raises(NotFoundError):
        service.get_report(GetSustainabilityReportCommand("default", token, "0" * 32))


def test_greenops_measured_pue_and_empty_analytic_branches(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    _configure(app, token)
    service = app.greenops_service

    with pytest.raises(NotFoundError, match="policy does not exist"):
        service.get_policy(GetGreenOpsPolicyCommand("default", token, "missing"))
    with pytest.raises(ValidationError, match="no GreenOps measurements"):
        service.generate_report(
            GenerateSustainabilityReportCommand(
                "default", token, "pytest", "par-01", date(2026, 7, 1), date(2026, 7, 1)
            )
        )
    with pytest.raises(NotFoundError, match="report does not exist"):
        service.export_report(ExportSustainabilityReportCommand("default", token, "0" * 32, "json"))

    start = datetime(2026, 7, 1, tzinfo=UTC)
    service.ingest_measurement(
        IngestEnergyMeasurementCommand(
            "default",
            token,
            "pytest",
            "greenops-measured-pue-0001",
            "dcim-meter",
            "observed",
            "asset",
            "server-001",
            "par-01",
            start,
            start + timedelta(hours=1),
            "12",
            it_energy_kwh="10",
            facility_energy_kwh="12",
            utilization_percent="90",
            energy_capacity_percent="80",
        )
    )
    report = service.generate_report(
        GenerateSustainabilityReportCommand(
            "default",
            token,
            "pytest",
            "par-01",
            date(2026, 7, 1),
            date(2026, 7, 1),
            "asset",
            "server-001",
        )
    )

    assert report.pue == Decimal("1.200000")
    assert report.pue_source == "measured"
    assert report.anomaly_ids == ()
    assert report.forecast_ids == ()
    assert report.candidate_ids == ()
