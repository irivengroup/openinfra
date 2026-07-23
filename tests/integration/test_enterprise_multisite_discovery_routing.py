from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    DisableCollectorCommand,
    EnrollDiscoveryProxyCommand,
    RegisterCollectorCommand,
)
from openinfra.application.multisite_services import (
    ConfigureRegionalDiscoveryRouteCommand,
    DisableRegionalDiscoveryRouteCommand,
    GetRegionalDiscoveryRouteCommand,
    ListRegionalDiscoveryRoutesCommand,
    RouteRegionalDiscoveryJobCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import (
    AccessDeniedError,
    EntityId,
    NotFoundError,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import Site


def _enterprise_application(tmp_path: Path):
    state = tmp_path / "enterprise-routing.json"
    app = ApplicationFactory().create_json_application(state, seed=True, edition="enterprise")
    token = "e" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "enterprise-admin", ("admin",), token)
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
    scope = "region/eu-west/site/lon1/vrf/prod"
    collector = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="EU West regional proxy",
            kind="network-proxy",
            certificate_fingerprint="b" * 64,
            scopes=(scope,),
            version="0.29.103",
            endpoint_url="https://regional-agent.example.invalid:8443",
        )
    )
    return state, app, token, collector


def test_enterprise_regional_route_dispatch_persistence_and_audit(tmp_path: Path) -> None:
    state, app, token, collector = _enterprise_application(tmp_path)
    route = app.multisite_service.configure_regional_discovery_route(
        ConfigureRegionalDiscoveryRouteCommand(
            "default", token, "eu-west", "lon1", "prod", collector.id.value
        )
    )
    assert route.discovery_scope == "region/eu-west/site/lon1/vrf/prod"
    assert (
        app.multisite_service.get_regional_discovery_route(
            GetRegionalDiscoveryRouteCommand("default", token, route.id.value)
        )
        == route
    )
    page = app.multisite_service.list_regional_discovery_routes(
        ListRegionalDiscoveryRoutesCommand("default", token, region_code="EU-WEST")
    )
    assert page.items == (route,)

    dispatch = app.multisite_service.route_regional_discovery_job(
        RouteRegionalDiscoveryJobCommand(
            tenant_id="default",
            admin_token=token,
            region_code="EU-WEST",
            site_code="LON1",
            vrf_code="PROD",
            job_type="network-inventory",
            target="10.20.0.0/24",
            idempotency_key="regional-lon1-prod-0001",
        )
    )
    assert dispatch.route == route
    assert dispatch.job.collector_id == collector.id
    assert dispatch.job.requested_scope.value == route.discovery_scope

    same_dispatch = app.multisite_service.route_regional_discovery_job(
        RouteRegionalDiscoveryJobCommand(
            "default",
            token,
            "EU-WEST",
            "LON1",
            "PROD",
            "network-inventory",
            "10.20.0.0/24",
            "regional-lon1-prod-0001",
        )
    )
    assert same_dispatch.job.id == dispatch.job.id

    reopened = ApplicationFactory().create_json_application(state, seed=False, edition="enterprise")
    persisted = reopened.multisite_repository.find_regional_route(
        TenantId.from_value("default"), "EU-WEST", "LON1", "PROD"
    )
    assert persisted == route
    assert any(
        event["action"] == "multisite.regional_discovery.routed"
        for event in reopened.store.data["audit_events"]
    )

    disabled = app.multisite_service.disable_regional_discovery_route(
        DisableRegionalDiscoveryRouteCommand("default", token, route.id.value)
    )
    assert disabled.active is False
    assert (
        app.multisite_service.list_regional_discovery_routes(
            ListRegionalDiscoveryRoutesCommand("default", token)
        ).items
        == ()
    )
    with pytest.raises(NotFoundError, match="active regional discovery route"):
        app.multisite_service.route_regional_discovery_job(
            RouteRegionalDiscoveryJobCommand(
                "default",
                token,
                "EU-WEST",
                "LON1",
                "PROD",
                "network-inventory",
                "10.20.0.0/24",
                "regional-lon1-prod-0002",
            )
        )


def test_regional_route_rejects_wrong_collector_site_and_edition(tmp_path: Path) -> None:
    _state, app, token, collector = _enterprise_application(tmp_path / "enterprise")
    with pytest.raises(NotFoundError, match="DCIM site"):
        app.multisite_service.configure_regional_discovery_route(
            ConfigureRegionalDiscoveryRouteCommand(
                "default", token, "eu-west", "MAD1", "prod", collector.id.value
            )
        )

    invalid_collector = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            "default",
            "pytest",
            token,
            "Site-only proxy",
            "site-proxy",
            "c" * 64,
            ("region/eu-west/site/lon1/vrf/prod",),
            "0.29.103",
            "https://site-agent.example.invalid:8443",
        )
    )
    with pytest.raises(AccessDeniedError, match="regional proxy"):
        app.multisite_service.configure_regional_discovery_route(
            ConfigureRegionalDiscoveryRouteCommand(
                "default", token, "eu-west", "LON1", "prod", invalid_collector.id.value
            )
        )

    route = app.multisite_service.configure_regional_discovery_route(
        ConfigureRegionalDiscoveryRouteCommand(
            "default", token, "eu-west", "LON1", "prod", collector.id.value
        )
    )
    app.discovery_service.disable_collector(
        DisableCollectorCommand("default", "pytest", token, collector.id.value, "maintenance")
    )
    with pytest.raises(AccessDeniedError, match="not active"):
        app.multisite_service.route_regional_discovery_job(
            RouteRegionalDiscoveryJobCommand(
                "default",
                token,
                route.region_code,
                route.site_code,
                route.vrf_code,
                "network-inventory",
                "10.20.0.0/24",
                "regional-disabled-collector",
            )
        )

    pro = ApplicationFactory().create_json_application(
        tmp_path / "pro.json", seed=True, edition="pro"
    )
    pro_token = "p" * 40
    pro.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "pro-admin", ("admin",), pro_token)
    )
    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        pro.multisite_service.list_regional_discovery_routes(
            ListRegionalDiscoveryRoutesCommand("default", pro_token)
        )


def test_regional_route_rejects_missing_route_collector_endpoint_and_scope(tmp_path: Path) -> None:
    _state, app, token, _collector = _enterprise_application(tmp_path)

    missing_route_id = EntityId.new().value
    with pytest.raises(NotFoundError, match="regional discovery route"):
        app.multisite_service.get_regional_discovery_route(
            GetRegionalDiscoveryRouteCommand("default", token, missing_route_id)
        )
    with pytest.raises(NotFoundError, match="regional discovery route"):
        app.multisite_service.disable_regional_discovery_route(
            DisableRegionalDiscoveryRouteCommand("default", token, missing_route_id)
        )
    with pytest.raises(NotFoundError, match="regional discovery collector"):
        app.multisite_service.configure_regional_discovery_route(
            ConfigureRegionalDiscoveryRouteCommand(
                "default", token, "eu-west", "LON1", "prod", EntityId.new().value
            )
        )

    no_endpoint = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            "default",
            "pytest",
            token,
            "Proxy without endpoint",
            "network-proxy",
            "d" * 64,
            ("region/eu-west/site/lon1/vrf/prod",),
            "0.29.103",
        )
    )
    with pytest.raises(AccessDeniedError, match="HTTPS endpoint"):
        app.multisite_service.configure_regional_discovery_route(
            ConfigureRegionalDiscoveryRouteCommand(
                "default", token, "eu-west", "LON1", "prod", no_endpoint.id.value
            )
        )

    out_of_scope = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            "default",
            "pytest",
            token,
            "Out-of-scope proxy",
            "datacenter-proxy",
            "f" * 64,
            ("region/eu-west/site/lon1/vrf/management",),
            "0.29.103",
            "https://regional-agent.example.invalid:8443",
        )
    )
    with pytest.raises(AccessDeniedError, match="does not authorize route scope"):
        app.multisite_service.configure_regional_discovery_route(
            ConfigureRegionalDiscoveryRouteCommand(
                "default", token, "eu-west", "LON1", "prod", out_of_scope.id.value
            )
        )
