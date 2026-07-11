from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.multisite import (
    MultisitePortfolioReport,
    SiteAccessGrant,
    SiteAccessLevel,
    SitePortfolioEntry,
)


def _entry(code: str = "PAR1") -> SitePortfolioEntry:
    return SitePortfolioEntry(code, f"Site {code}", "FR", "Paris", "active", 1, 1, 1, 1, 2)


def test_site_access_grant_lifecycle_and_serialization() -> None:
    tenant = TenantId.from_value("default")
    granted_at = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)
    grant = SiteAccessGrant.create(
        tenant, "Operator.Example", "par1", SiteAccessLevel.VIEWER, "pytest", granted_at
    )
    assert grant.subject == "operator.example"
    assert grant.site_code == "PAR1"
    assert grant.allows("viewer") is True
    assert grant.allows("operator") is False

    revised = grant.revise("operator", "security-admin", datetime(2026, 7, 11, 9, 0, tzinfo=UTC))
    assert revised.id == grant.id
    assert revised.allows(SiteAccessLevel.OPERATOR) is True
    revoked = revised.revoke("security-admin", datetime(2026, 7, 11, 10, 0, tzinfo=UTC))
    assert revoked.active is False and revoked.revoked_at is not None
    assert revoked.revoke("security-admin") == revoked
    assert revoked.as_dict()["access_level"] == "operator"

    restored = SiteAccessGrant.restore(
        id=EntityId.from_value(revoked.id.value),
        tenant_id=tenant,
        subject=revoked.subject,
        site_code=revoked.site_code,
        access_level=revoked.access_level,
        active=False,
        granted_by=revoked.granted_by,
        created_at=revoked.created_at,
        updated_at=revoked.updated_at,
        revoked_at=revoked.revoked_at,
    )
    assert restored == revoked


def test_multisite_domain_validation_guards() -> None:
    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError, match="viewer, operator or admin"):
        SiteAccessLevel.from_value("owner")
    with pytest.raises(ValidationError, match="subject"):
        SiteAccessGrant.create(tenant, "x", "PAR1", "viewer", "pytest")
    with pytest.raises(ValidationError, match="revocation date"):
        SiteAccessGrant.restore(
            id=EntityId.new(),
            tenant_id=tenant,
            subject="valid.subject",
            site_code="PAR1",
            access_level="viewer",
            active=False,
            granted_by="pytest",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            revoked_at=None,
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        SiteAccessGrant.create(
            tenant,
            "valid.subject",
            "PAR1",
            "viewer",
            "pytest",
            datetime(2026, 7, 11),
        )
    with pytest.raises(ValidationError, match="actor"):
        SiteAccessGrant.create(tenant, "valid.subject", "PAR1", "viewer", "")
    with pytest.raises(ValidationError, match="active site access grant"):
        SiteAccessGrant.restore(
            id=EntityId.new(),
            tenant_id=tenant,
            subject="valid.subject",
            site_code="PAR1",
            access_level="viewer",
            active=True,
            granted_by="pytest",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            revoked_at=datetime.now(UTC),
        )


def test_multisite_report_totals_order_restore_and_guards() -> None:
    tenant = TenantId.from_value("default")
    report = MultisitePortfolioReport.create(
        tenant,
        "report.viewer",
        "pytest",
        (_entry("LON1"), _entry("PAR1")),
        datetime(2026, 7, 11, 8, 0, tzinfo=UTC),
    )
    assert [item.site_code for item in report.sites] == ["LON1", "PAR1"]
    assert report.totals == {
        "sites": 2,
        "buildings": 2,
        "floors": 2,
        "rooms": 2,
        "racks": 2,
        "equipment": 4,
    }
    restored = MultisitePortfolioReport.restore(
        id=report.id,
        tenant_id=tenant,
        requested_subject=report.requested_subject,
        generated_by=report.generated_by,
        generated_at=report.generated_at,
        sites=report.sites,
    )
    assert restored.as_dict() == report.as_dict()
    with pytest.raises(ValidationError, match="at least one"):
        MultisitePortfolioReport.create(tenant, "report.viewer", "pytest", ())
    with pytest.raises(ValidationError, match="duplicate"):
        MultisitePortfolioReport.create(
            tenant, "report.viewer", "pytest", (_entry("PAR1"), _entry("PAR1"))
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        MultisitePortfolioReport.create(
            tenant,
            "report.viewer",
            "pytest",
            (_entry("PAR1"),),
            datetime(2026, 7, 11),
        )
    with pytest.raises(ValidationError, match="more than 500"):
        MultisitePortfolioReport.create(
            tenant,
            "report.viewer",
            "pytest",
            tuple(_entry(f"S{index:03d}") for index in range(501)),
        )


def test_regional_discovery_route_lifecycle_scope_and_guards() -> None:
    from openinfra.domain.multisite import RegionalDiscoveryRoute

    tenant = TenantId.from_value("default")
    created_at = datetime(2026, 7, 11, 9, 0, tzinfo=UTC)
    collector_id = EntityId.new()
    route = RegionalDiscoveryRoute.create(
        tenant,
        "eu-west",
        "par1",
        "prod",
        collector_id,
        "multisite-admin",
        created_at,
    )
    assert route.discovery_scope == "region/eu-west/site/par1/vrf/prod"
    assert route.matches("EU-WEST", "PAR1", "PROD") is True
    assert route.matches("EU-WEST", "LON1", "PROD") is False

    reassigned = route.reassign(
        EntityId.new(), "routing-admin", datetime(2026, 7, 11, 10, 0, tzinfo=UTC)
    )
    assert reassigned.id == route.id
    assert reassigned.collector_id != route.collector_id
    disabled = reassigned.disable("routing-admin", datetime(2026, 7, 11, 11, 0, tzinfo=UTC))
    assert disabled.active is False and disabled.disabled_at is not None
    assert disabled.disable("routing-admin") == disabled

    restored = RegionalDiscoveryRoute.restore(
        id=disabled.id,
        tenant_id=disabled.tenant_id,
        region_code=disabled.region_code,
        site_code=disabled.site_code,
        vrf_code=disabled.vrf_code,
        collector_id=disabled.collector_id,
        discovery_scope=disabled.discovery_scope,
        active=False,
        configured_by=disabled.configured_by,
        created_at=disabled.created_at,
        updated_at=disabled.updated_at,
        disabled_at=disabled.disabled_at,
    )
    assert restored.as_dict() == disabled.as_dict()

    with pytest.raises(ValidationError, match="scope is inconsistent"):
        RegionalDiscoveryRoute.restore(
            id=route.id,
            tenant_id=tenant,
            region_code="EU-WEST",
            site_code="PAR1",
            vrf_code="PROD",
            collector_id=collector_id,
            discovery_scope="region/eu/site/par1/vrf/prod",
            active=True,
            configured_by="pytest",
            created_at=created_at,
            updated_at=created_at,
        )
    with pytest.raises(ValidationError, match="active state is inconsistent"):
        RegionalDiscoveryRoute.restore(
            id=route.id,
            tenant_id=tenant,
            region_code="EU-WEST",
            site_code="PAR1",
            vrf_code="PROD",
            collector_id=collector_id,
            discovery_scope=route.discovery_scope,
            active=False,
            configured_by="pytest",
            created_at=created_at,
            updated_at=created_at,
        )
