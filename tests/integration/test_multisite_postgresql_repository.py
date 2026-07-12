from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import EntityId, Pagination, TenantId, ValidationError
from openinfra.domain.multisite import (
    MultisitePortfolioReport,
    RegionalDiscoveryRoute,
    SiteAccessGrant,
    SitePortfolioEntry,
)
from openinfra.infrastructure.cursor_pagination import CursorField
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLMultisiteRepository,
    PostgreSQLSessionRegistry,
)


def _repository() -> PostgreSQLMultisiteRepository:
    return PostgreSQLMultisiteRepository(
        PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=lambda _dsn, _profile: FakeConnection(),
            )
        )
    )


def _objects() -> tuple[TenantId, SiteAccessGrant, MultisitePortfolioReport]:
    tenant = TenantId.from_value("default")
    grant = SiteAccessGrant.create(
        tenant,
        "postgres.user",
        "PAR1",
        "operator",
        "pytest",
        datetime(2026, 7, 11, 8, tzinfo=UTC),
    )
    report = MultisitePortfolioReport.create(
        tenant,
        "postgres.user",
        "pytest",
        (SitePortfolioEntry("PAR1", "Paris 1", "FR", "Paris", "active", 1, 1, 1, 1, 0),),
        datetime(2026, 7, 11, 9, tzinfo=UTC),
    )
    return tenant, grant, report


def test_multisite_postgresql_writes_are_parameterized(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    _tenant, grant, report = _objects()
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    repo.save_grant(grant)
    repo.save_report(report)
    assert "INSERT INTO multisite_site_access_grants" in statements[0][0]
    assert "INSERT INTO multisite_reports" in statements[1][0]
    assert statements[0][1]["subject"] == "postgres.user"
    assert statements[1][1]["requested_subject"] == "postgres.user"
    assert all("%(tenant_id)s" in statement for statement, _params in statements)


def test_multisite_postgresql_reads_filters_pagination_and_guards(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    tenant, grant, report = _objects()
    rows = iter(
        [
            {"payload": json.dumps(grant.as_dict())},
            {"payload": json.dumps(report.as_dict())},
            None,
        ]
    )
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))
    assert repo.find_grant(tenant, "POSTGRES.USER", "par1") == grant
    assert repo.get_report(tenant, report.id.value) == report
    assert repo.find_grant(tenant, "postgres.user", "PAR1") is None

    calls: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        calls.append((" ".join(query.split()), dict(params)))
        payload = grant.as_dict() if "site_access" in query else report.as_dict()
        return [{"payload": json.dumps(payload)}, {"payload": json.dumps(payload)}]

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    grants = repo.list_grants(
        tenant, Pagination(limit=1), subject="postgres.user", site_code="par1", active_only=True
    )
    reports = repo.list_reports(tenant, Pagination(limit=1), requested_subject="POSTGRES.USER")
    assert grants.items == (grant,) and grants.next_cursor == "1"
    assert reports.items == (report,) and reports.next_cursor == "1"
    assert "active = TRUE" in calls[0][0]
    assert calls[1][1]["requested_subject"] == "postgres.user"

    with pytest.raises(ValueError, match="unsupported multisite pagination"):
        repo._page("multisite_reports", tenant, Pagination(limit=1), "", {}, "id")
    with pytest.raises(ValidationError, match="signing secret"):
        repo._keyset_page(
            Pagination.from_values(10, "invalid.cursor"),
            scope="multisite.reports",
            tenant_id=tenant,
            filters={},
            fields=(CursorField("id"),),
        )
    first_page = repo._keyset_page(
        Pagination.from_values(10),
        scope="multisite.reports",
        tenant_id=tenant,
        filters={},
        fields=(CursorField("id"),),
    )
    legacy_page = repo._keyset_page(
        Pagination.from_values(10, "25"),
        scope="multisite.reports",
        tenant_id=tenant,
        filters={},
        fields=(CursorField("id"),),
    )
    assert first_page.where_sql == "" and first_page.offset_sql == ""
    assert legacy_page.parameters["legacy_offset"] == 25
    with pytest.raises(ValidationError, match="sites payload"):
        repo._report({**report.as_dict(), "sites": "invalid"})
    with pytest.raises(ValidationError, match="JSON object"):
        repo._json_mapping([])


def test_multisite_postgresql_regional_routes_are_parameterized_and_mapped(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    tenant = TenantId.from_value("default")
    route = RegionalDiscoveryRoute.create(
        tenant,
        "EU-WEST",
        "PAR1",
        "PROD",
        EntityId.new(),
        "pytest",
        datetime(2026, 7, 11, 10, tzinfo=UTC),
    )
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    repo.save_regional_route(route)
    assert "INSERT INTO multisite_regional_discovery_routes" in statements[0][0]
    assert statements[0][1]["collector_id"] == route.collector_id.value

    rows = iter(
        [
            {"payload": json.dumps(route.as_dict())},
            {"payload": json.dumps(route.as_dict())},
        ]
    )
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))
    assert repo.get_regional_route(tenant, route.id.value) == route
    assert repo.find_regional_route(tenant, "eu-west", "par1", "prod") == route

    calls: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        calls.append((" ".join(query.split()), dict(params)))
        return [
            {"payload": json.dumps(route.as_dict())},
            {"payload": json.dumps(route.as_dict())},
        ]

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    page = repo.list_regional_routes(
        tenant,
        Pagination(limit=1),
        region_code="eu-west",
        site_code="par1",
        active_only=True,
    )
    assert page.items == (route,) and page.next_cursor == "1"
    assert "active = TRUE" in calls[0][0]
    assert calls[0][1]["region_code"] == "EU-WEST"


def test_multisite_postgresql_disaster_recovery_is_parameterized_and_mapped(
    monkeypatch: MonkeyPatch,
) -> None:
    from openinfra.domain.multisite import (
        MultisiteDisasterRecoveryDrill,
        MultisiteDisasterRecoveryPlan,
    )

    repo = _repository()
    tenant = TenantId.from_value("default")
    plan = MultisiteDisasterRecoveryPlan.create(
        tenant,
        "Paris to London",
        "PAR1",
        "LON1",
        "async",
        300,
        1800,
        86400,
        "pytest",
        datetime(2026, 7, 11, 12, tzinfo=UTC),
    )
    drill = MultisiteDisasterRecoveryDrill.execute_site_loss(
        plan,
        replication_lag_seconds=30,
        backup_age_seconds=3600,
        measured_rto_seconds=600,
        restore_verified=True,
        recovery_available=True,
        vip_reachable=True,
        operator_confirmed=True,
        executed_by="pytest",
        now=datetime(2026, 7, 11, 13, tzinfo=UTC),
    )
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    repo.save_dr_plan(plan)
    repo.save_dr_drill(drill)
    assert "INSERT INTO multisite_dr_plans" in statements[0][0]
    assert "id = EXCLUDED.id" not in statements[0][0]
    assert "INSERT INTO multisite_dr_drills" in statements[1][0]
    assert "ON CONFLICT (tenant_id, id) DO NOTHING" in statements[1][0]
    assert statements[0][1]["primary_site_code"] == "PAR1"
    assert statements[1][1]["status"] == "passed"

    rows = iter(
        [
            {"payload": json.dumps(plan.as_dict())},
            {"payload": json.dumps(plan.as_dict())},
            {"payload": json.dumps(drill.as_dict())},
        ]
    )
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))
    assert repo.get_dr_plan(tenant, plan.id.value) == plan
    assert repo.find_dr_plan_by_sites(tenant, "par1", "lon1") == plan
    assert repo.get_dr_drill(tenant, drill.id.value) == drill

    calls: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        calls.append((" ".join(query.split()), dict(params)))
        payload = drill.as_dict() if "dr_drills" in query else plan.as_dict()
        return [{"payload": json.dumps(payload)}, {"payload": json.dumps(payload)}]

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    plans = repo.list_dr_plans(tenant, Pagination(limit=1), active_only=True)
    drills = repo.list_dr_drills(
        tenant, Pagination(limit=1), plan_id=plan.id.value, status="passed"
    )
    assert plans.items == (plan,) and plans.next_cursor == "1"
    assert drills.items == (drill,) and drills.next_cursor == "1"
    assert "active = TRUE" in calls[0][0]
    assert calls[1][1]["status"] == "passed"
    with pytest.raises(ValidationError, match="passed or failed"):
        repo.list_dr_drills(tenant, Pagination(limit=1), status="invalid")
    with pytest.raises(ValidationError, match="failure reasons payload"):
        repo._dr_drill({**drill.as_dict(), "failure_reasons": "invalid"})
