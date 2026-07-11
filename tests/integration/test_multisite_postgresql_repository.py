from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import Pagination, TenantId, ValidationError
from openinfra.domain.multisite import MultisitePortfolioReport, SiteAccessGrant, SitePortfolioEntry
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
    with pytest.raises(ValidationError, match="numeric offset"):
        repo._offset("invalid")
    with pytest.raises(ValidationError, match="positive"):
        repo._offset("-1")
    with pytest.raises(ValidationError, match="sites payload"):
        repo._report({**report.as_dict(), "sites": "invalid"})
    with pytest.raises(ValidationError, match="JSON object"):
        repo._json_mapping([])
