from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import (
    DomainEvent,
    EntityId,
    OpenInfraError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
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
    GreenScore,
    MeasurementSource,
    SustainabilityReport,
)
from openinfra.infrastructure.cursor_pagination import CursorField
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLGreenOpsRepository,
    PostgreSQLSessionRegistry,
)


def _repository() -> PostgreSQLGreenOpsRepository:
    connection = FakeConnection()
    return PostgreSQLGreenOpsRepository(
        PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=lambda _dsn, _profile: connection,
            )
        )
    )


def _objects() -> dict[str, object]:
    tenant = TenantId.from_value("default")
    now = datetime(2026, 7, 11, 12, tzinfo=UTC)
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
        "greenops-postgresql-0001",
        source.code,
        "observed",
        "rack",
        "rack-a01",
        "par-01",
        now,
        now + timedelta(hours=1),
        "12",
        it_energy_kwh="10",
        facility_energy_kwh="12",
        utilization_percent="10",
        energy_capacity_percent="80",
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
    event = DomainEvent(
        EntityId.new(),
        tenant,
        report.id,
        "green.report.generated",
        {"report_id": report.id.value},
        now,
    )
    return {
        "tenant": tenant,
        "source": source,
        "factor": factor,
        "policy": policy,
        "measurement": measurement,
        "anomaly": anomaly,
        "forecast": forecast,
        "candidate": candidate,
        "score": score,
        "report": report,
        "event": event,
    }


def _patch_writes(
    monkeypatch: MonkeyPatch, repo: PostgreSQLGreenOpsRepository
) -> list[tuple[str, dict[str, object]]]:
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    return statements


def test_greenops_postgresql_save_methods_and_outbox(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    values = _objects()
    statements = _patch_writes(monkeypatch, repo)

    repo.save_source(values["source"])  # type: ignore[arg-type]
    repo.save_policy(values["policy"])  # type: ignore[arg-type]
    repo.save_carbon_factor(values["factor"])  # type: ignore[arg-type]
    repo.save_anomaly(values["anomaly"])  # type: ignore[arg-type]
    repo.save_forecast(values["forecast"])  # type: ignore[arg-type]
    repo.save_candidate(values["candidate"])  # type: ignore[arg-type]
    repo.save_score(values["score"])  # type: ignore[arg-type]
    repo.save_report(values["report"])  # type: ignore[arg-type]
    repo.append_event(values["event"])  # type: ignore[arg-type]

    joined = "\n".join(query for query, _params in statements)
    assert "greenops_measurement_sources" in joined
    assert "greenops_policies" in joined
    assert "greenops_carbon_factors" in joined
    assert "greenops_anomalies" in joined
    assert "greenops_forecasts" in joined
    assert "greenops_consolidation_candidates" in joined
    assert "greenops_scores" in joined
    assert "greenops_reports" in joined
    assert "greenops_event_outbox" in joined


def test_greenops_postgresql_measurement_idempotency_paths(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    values = _objects()
    measurement = values["measurement"]
    assert isinstance(measurement, EnergyMeasurement)
    statements = _patch_writes(monkeypatch, repo)

    payload = json.dumps(measurement.as_dict(), sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        repo,
        "_fetch_one",
        lambda _query, _params: {
            "measurement_id": measurement.id.value,
            "payload_digest": digest,
        },
    )
    repo.save_measurement(measurement)
    assert any("greenops_energy_measurements" in query for query, _params in statements)

    responses: list[dict[str, object] | None] = [None, None]
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: responses.pop(0))
    with pytest.raises(OpenInfraError, match="could not be verified"):
        repo.save_measurement(measurement)

    responses = [
        None,
        {"measurement_id": measurement.id.value, "payload_digest": "b" * 64},
    ]
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: responses.pop(0))
    with pytest.raises(ValidationError, match="another payload"):
        repo.save_measurement(measurement)

    responses = [
        None,
        {"measurement_id": EntityId.new().value, "payload_digest": digest},
    ]
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: responses.pop(0))
    with pytest.raises(ValidationError, match="committed or in progress"):
        repo.save_measurement(measurement)


def test_greenops_postgresql_reads_lists_filters_and_pagination(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    values = _objects()
    tenant = values["tenant"]
    assert isinstance(tenant, TenantId)
    source = values["source"]
    policy = values["policy"]
    factor = values["factor"]
    measurement = values["measurement"]
    anomaly = values["anomaly"]
    forecast = values["forecast"]
    candidate = values["candidate"]
    score = values["score"]
    report = values["report"]
    assert isinstance(source, MeasurementSource)
    assert isinstance(policy, GreenOpsPolicy)
    assert isinstance(factor, CarbonFactor)
    assert isinstance(measurement, EnergyMeasurement)
    assert isinstance(anomaly, EnergyAnomaly)
    assert isinstance(forecast, CapacityForecast)
    assert isinstance(candidate, ConsolidationCandidate)
    assert isinstance(score, GreenScore)
    assert isinstance(report, SustainabilityReport)

    single_rows: list[dict[str, object] | None] = [
        {"payload": json.dumps(source.as_dict())},
        None,
        {"payload": policy.as_dict()},
        None,
        {"payload": measurement.as_dict()},
        None,
        {"payload": report.as_dict()},
        None,
        {"payload": report.as_dict()},
        None,
    ]
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: single_rows.pop(0))
    assert repo.find_source(tenant, "METER") is not None
    assert repo.find_source(tenant, "missing") is None
    assert repo.get_policy(tenant, "PAR_01") is not None
    assert repo.get_policy(tenant, "missing") is None
    assert repo.find_measurement_by_idempotency_key(tenant, measurement.idempotency_key) is not None
    assert repo.find_measurement_by_idempotency_key(tenant, "missing") is None
    assert repo.get_report(tenant, report.id.value) is not None
    assert repo.get_report(tenant, EntityId.new().value) is None
    assert repo.find_report_by_reproducibility_key(tenant, report.reproducibility_key()) is not None
    assert repo.find_report_by_reproducibility_key(tenant, "missing") is None

    payloads: list[dict[str, object]] = [
        source.as_dict(),
        factor.as_dict(),
        measurement.as_dict(),
        anomaly.as_dict(),
        forecast.as_dict(),
        candidate.as_dict(),
        score.as_dict(),
        report.as_dict(),
    ]
    monkeypatch.setattr(
        repo,
        "_fetch_all",
        lambda _query, _params: [{"payload": item} for item in payloads[:2]],
    )
    assert repo.list_sources(tenant, Pagination.from_values(1), active_only=True).next_cursor == "1"

    def one_payload(query: str, _params: dict[str, object]) -> list[dict[str, object]]:
        table_match = {
            "greenops_carbon_factors": factor.as_dict(),
            "greenops_energy_measurements": measurement.as_dict(),
            "greenops_anomalies": anomaly.as_dict(),
            "greenops_forecasts": forecast.as_dict(),
            "greenops_consolidation_candidates": candidate.as_dict(),
            "greenops_scores": score.as_dict(),
            "greenops_reports": report.as_dict(),
        }
        normalized = " ".join(query.split())
        for table_name, payload in table_match.items():
            if table_name in normalized:
                return [{"payload": payload}]
        return []

    monkeypatch.setattr(repo, "_fetch_all", one_payload)
    assert repo.list_carbon_factors(tenant, Pagination.from_values(10), "FR_2026", "FR").items
    assert repo.list_measurements(
        tenant,
        Pagination.from_values(10),
        datetime(2026, 7, 1, tzinfo=UTC),
        datetime(2026, 7, 31, tzinfo=UTC),
        "PAR_01",
        "RACK",
        "RACK_A01",
        "OBSERVED",
    ).items
    assert repo.list_anomalies(tenant, Pagination.from_values(10), "WARNING", "PAR_01").items
    assert repo.list_forecasts(tenant, Pagination.from_values(10), "PAR_01", "ENERGY").items
    assert repo.list_candidates(tenant, Pagination.from_values(10), "PAR_01", "WARNING").items
    assert repo.list_scores(tenant, Pagination.from_values(10), "SITE:PAR-01").items
    assert repo.list_reports(tenant, Pagination.from_values(10), "PAR_01", "RACK").items


def test_greenops_postgresql_internal_guards(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    tenant = TenantId.from_value("default")
    _patch_writes(monkeypatch, repo)

    with pytest.raises(ValueError, match="unsupported GreenOps payload"):
        repo._upsert_payload("users", tenant, EntityId.new().value, {}, {})
    with pytest.raises(ValueError, match="unsupported GreenOps pagination"):
        repo._payload_page("users", tenant, Pagination.from_values(10), "", {}, "id")
    with pytest.raises(ValidationError, match="signing secret"):
        repo._keyset_page(
            Pagination.from_values(10, "invalid.cursor"),
            scope="greenops.reports",
            tenant_id=tenant,
            filters={},
            fields=(CursorField("id"),),
        )
    with pytest.raises(ValidationError, match="JSON object"):
        repo._json_mapping("[]")

    first_page = repo._keyset_page(
        Pagination.from_values(10),
        scope="greenops.reports",
        tenant_id=tenant,
        filters={},
        fields=(CursorField("id"),),
    )
    legacy_page = repo._keyset_page(
        Pagination.from_values(10, "25"),
        scope="greenops.reports",
        tenant_id=tenant,
        filters={},
        fields=(CursorField("id"),),
    )
    assert first_page.where_sql == "" and first_page.offset_sql == ""
    assert legacy_page.offset_sql == " OFFSET %(legacy_offset)s"
    assert legacy_page.parameters["legacy_offset"] == 25
    assert repo._optional_filters({"site_code": "par-01", "scope": None}) == (
        "AND site_code = %(site_code)s",
        {"site_code": "par-01"},
    )
    assert repo._json_mapping('{"site_code":"par-01"}') == {"site_code": "par-01"}
