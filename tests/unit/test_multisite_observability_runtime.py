from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    EnrollDiscoveryProxyCommand,
    HeartbeatCollectorCommand,
)
from openinfra.application.multisite_services import ConfigureRegionalDiscoveryRouteCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ValidationError
from openinfra.infrastructure.multisite_observability import MultisiteOperationalMetricsProvider
from openinfra.infrastructure.observability import OpenInfraTelemetry


def _application_with_route(tmp_path: Path):
    app = ApplicationFactory().create_json_application(
        tmp_path / "multisite-observability.json", seed=True, edition="enterprise"
    )
    token = "m" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "multisite-observability", ("admin",), token)
    )
    scopes = (
        "region/eu-west/site/par1/vrf/prod",
        "region/eu-west/site/par1/vrf/management",
    )
    collector = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Paris regional proxy",
            kind="network-proxy",
            certificate_fingerprint="a" * 64,
            scopes=scopes,
            version="0.32.12",
            endpoint_url="https://par1-agent.example.invalid:8443",
        )
    )
    app.multisite_service.configure_regional_discovery_route(
        ConfigureRegionalDiscoveryRouteCommand(
            "default", token, "eu-west", "par1", "prod", collector.id.value
        )
    )
    app.multisite_service.configure_regional_discovery_route(
        ConfigureRegionalDiscoveryRouteCommand(
            "default", token, "eu-west", "par1", "management", collector.id.value
        )
    )
    return app, collector


def test_multisite_metrics_provider_aggregates_real_collector_heartbeats(tmp_path: Path) -> None:
    app, collector = _application_with_route(tmp_path)
    refreshed = app.discovery_service.heartbeat(
        HeartbeatCollectorCommand("default", collector.id.value, "a" * 64, "0.32.12", "ok")
    )
    assert refreshed.last_heartbeat_at is not None
    provider = MultisiteOperationalMetricsProvider(
        app.multisite_repository,
        app.discovery_repository,
        tenant_id="default",
        agent_stale_after_seconds=120,
        clock=lambda: refreshed.last_heartbeat_at + timedelta(seconds=30),
    )

    payload = provider()

    assert payload["tenant_scope"] == "default"
    assert payload["agent_stale_after_seconds"] == 120
    assert payload["sites"] == [
        {
            "region": "EU-WEST",
            "site": "PAR1",
            "agent_lag_seconds": 30.0,
            "collectors_total": 1,
            "collectors_healthy": 1,
            "collectors_degraded": 0,
            "collectors_maintenance": 0,
            "collectors_stale": 0,
            "healthy": True,
        }
    ]


def test_multisite_metrics_provider_marks_stale_and_validates_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, collector = _application_with_route(tmp_path)
    refreshed = app.discovery_service.heartbeat(
        HeartbeatCollectorCommand("default", collector.id.value, "a" * 64, "0.32.12", "degraded")
    )
    assert refreshed.last_heartbeat_at is not None
    provider = MultisiteOperationalMetricsProvider(
        app.multisite_repository,
        app.discovery_repository,
        tenant_id="default",
        agent_stale_after_seconds=60,
        clock=lambda: refreshed.last_heartbeat_at + timedelta(seconds=61),
    )
    site = provider()["sites"][0]
    assert isinstance(site, dict)
    assert site["collectors_stale"] == 1
    assert site["healthy"] is False

    monkeypatch.setenv("OPENINFRA_MULTISITE_AGENT_STALE_AFTER_SECONDS", "invalid")
    with pytest.raises(ValidationError, match="must be an integer"):
        MultisiteOperationalMetricsProvider.from_environment(
            app.multisite_repository, app.discovery_repository
        )
    with pytest.raises(ValidationError, match="between 10 and 86400"):
        MultisiteOperationalMetricsProvider(
            app.multisite_repository,
            app.discovery_repository,
            agent_stale_after_seconds=1,
        )


def test_prometheus_exports_bounded_multisite_agent_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    telemetry = OpenInfraTelemetry(
        service_name="openinfra-api",
        edition="enterprise",
        environment="test",
        multisite_metrics_provider=lambda: {
            "sites": [
                {
                    "region": "EU-WEST",
                    "site": "PAR1",
                    "agent_lag_seconds": 12.5,
                    "collectors_healthy": 2,
                    "collectors_degraded": 0,
                    "collectors_maintenance": 1,
                    "collectors_stale": 0,
                    "healthy": False,
                },
                {"region": "unsafe label", "site": "PAR1", "agent_lag_seconds": 1},
            ]
        },
    )

    metrics = telemetry.render_prometheus().decode("utf-8")

    assert 'openinfra_multisite_agent_lag_seconds{region="EU-WEST",site="PAR1"} 12.5' in metrics
    assert 'openinfra_multisite_agent_health{region="EU-WEST",site="PAR1"} 0.0' in metrics
    assert (
        'openinfra_multisite_agent_collectors{region="EU-WEST",site="PAR1",state="maintenance"} 1.0'
        in metrics
    )
    assert "unsafe label" not in metrics
    telemetry.close()
