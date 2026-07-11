from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.multisite_services import (
    GenerateMultisiteReportCommand,
    GetMultisiteReportCommand,
    ListAccessibleSitesCommand,
    ListMultisiteReportsCommand,
    ListSiteAccessCommand,
    RevokeSiteAccessCommand,
    UpsertSiteAccessCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import AccessDeniedError, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import Site
from openinfra.domain.multisite import SiteAccessGrant


def _application(tmp_path: Path, *, edition: str = "pro"):
    state = tmp_path / f"state-{edition}.json"
    app = ApplicationFactory().create_json_application(state, seed=True, edition=edition)
    admin = "a" * 40
    viewer = "v" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "multisite-admin", ("admin",), admin)
    )
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "site.viewer", ("multisite:reader",), viewer)
    )
    with app.transaction_manager.begin() as unit_of_work:
        app.dcim_repository.add_site(
            Site.create(
                TenantId.from_value("default"),
                "LON1",
                "London 1",
                "GB",
                "London",
                "England",
                "1 Datacenter Way",
                "E1 1AA",
                "lon1@example.invalid",
                "+442000000001",
            )
        )
        unit_of_work.commit()
    return state, app, admin, viewer


def test_multisite_site_scoped_rbac_reports_audit_and_persistence(tmp_path: Path) -> None:
    state, app, admin, viewer = _application(tmp_path)
    grant = app.multisite_service.upsert_site_access(
        UpsertSiteAccessCommand("default", admin, "SITE.VIEWER", "par1", "viewer")
    )
    assert grant.subject == "site.viewer" and grant.site_code == "PAR1"

    viewer_sites = app.multisite_service.list_accessible_sites(
        ListAccessibleSitesCommand("default", viewer)
    )
    assert [item["site_code"] for item in viewer_sites] == ["PAR1"]
    admin_sites = app.multisite_service.list_accessible_sites(
        ListAccessibleSitesCommand("default", admin)
    )
    assert [item["site_code"] for item in admin_sites] == ["LON1", "PAR1"]

    report = app.multisite_service.generate_report(
        GenerateMultisiteReportCommand("default", viewer, ("par1",))
    )
    assert report.requested_subject == "site.viewer"
    assert report.totals == {
        "sites": 1,
        "buildings": 1,
        "floors": 1,
        "rooms": 1,
        "racks": 1,
        "equipment": 0,
    }
    assert (
        app.multisite_service.get_report(
            GetMultisiteReportCommand("default", viewer, report.id.value)
        ).id
        == report.id
    )
    assert app.multisite_service.list_reports(
        ListMultisiteReportsCommand("default", viewer)
    ).items == (report,)
    assert app.multisite_service.list_site_access(
        ListSiteAccessCommand("default", admin, subject="site.viewer")
    ).items == (grant,)

    with pytest.raises(AccessDeniedError, match="unauthorized site"):
        app.multisite_service.generate_report(
            GenerateMultisiteReportCommand("default", viewer, ("PAR1", "LON1"))
        )
    with pytest.raises(AccessDeniedError, match="another subject"):
        app.multisite_service.generate_report(
            GenerateMultisiteReportCommand("default", viewer, ("PAR1",), subject="multisite-admin")
        )
    with pytest.raises(AccessDeniedError, match="another subject"):
        app.multisite_service.list_accessible_sites(
            ListAccessibleSitesCommand("default", viewer, subject="multisite-admin")
        )
    with pytest.raises(NotFoundError, match="DCIM site"):
        app.multisite_service.upsert_site_access(
            UpsertSiteAccessCommand("default", admin, "site.viewer", "MAD1", "viewer")
        )
    with pytest.raises(NotFoundError, match="multisite report"):
        app.multisite_service.get_report(
            GetMultisiteReportCommand("default", viewer, "00000000-0000-4000-8000-000000000001")
        )

    admin_report = app.multisite_service.generate_report(
        GenerateMultisiteReportCommand("default", admin, ("PAR1",))
    )
    with pytest.raises(AccessDeniedError, match="outside the principal"):
        app.multisite_service.get_report(
            GetMultisiteReportCommand("default", viewer, admin_report.id.value)
        )

    reopened = ApplicationFactory().create_json_application(state, seed=False, edition="pro")
    assert (
        reopened.multisite_repository.find_grant(
            TenantId.from_value("default"), "site.viewer", "PAR1"
        )
        is not None
    )
    assert (
        reopened.multisite_repository.get_report(TenantId.from_value("default"), report.id.value)
        is not None
    )
    assert any(
        event["action"] == "multisite.report.generated"
        for event in reopened.store.data["audit_events"]
    )

    revoked = app.multisite_service.revoke_site_access(
        RevokeSiteAccessCommand("default", admin, "site.viewer", "PAR1")
    )
    assert revoked.active is False
    assert (
        app.multisite_service.list_site_access(ListSiteAccessCommand("default", admin)).items == ()
    )
    with pytest.raises(NotFoundError, match="grant"):
        app.multisite_service.revoke_site_access(
            RevokeSiteAccessCommand("default", admin, "unknown.subject", "PAR1")
        )


def test_multisite_is_available_in_pro_and_enterprise_but_not_lite(tmp_path: Path) -> None:
    _state, pro, pro_admin, _viewer = _application(tmp_path / "pro", edition="pro")
    assert pro.multisite_service.list_accessible_sites(
        ListAccessibleSitesCommand("default", pro_admin)
    )

    lite = ApplicationFactory().create_json_application(
        tmp_path / "lite.json", seed=True, edition="lite"
    )
    lite_admin = "l" * 40
    lite.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "lite-admin", ("admin",), lite_admin)
    )
    with pytest.raises(ValidationError, match="centralized_multisite"):
        lite.multisite_service.list_accessible_sites(
            ListAccessibleSitesCommand("default", lite_admin)
        )


def test_multisite_access_scope_reads_all_repository_pages(tmp_path: Path) -> None:
    _state, app, _admin, viewer = _application(tmp_path)
    tenant_id = TenantId.from_value("default")
    with app.transaction_manager.begin() as unit_of_work:
        for index in range(501):
            site_code = f"S{index:03d}"
            app.dcim_repository.add_site(
                Site.create(
                    tenant_id,
                    site_code,
                    f"Site {index}",
                    "FR",
                    "Paris",
                    "Ile-de-France",
                    f"{index + 1} Datacenter Way",
                    "75001",
                    f"site-{index}@example.invalid",
                    f"+331{index:08d}",
                )
            )
            app.multisite_repository.save_grant(
                SiteAccessGrant.create(tenant_id, "site.viewer", site_code, "viewer", "pytest")
            )
        unit_of_work.commit()

    accessible = app.multisite_service.list_accessible_sites(
        ListAccessibleSitesCommand("default", viewer)
    )
    assert len(accessible) == 501
    assert accessible[0]["site_code"] == "S000"
    assert accessible[-1]["site_code"] == "S500"
