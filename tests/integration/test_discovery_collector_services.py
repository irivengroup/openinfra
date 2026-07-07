from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
    DisableCollectorCommand,
    EnrollDiscoveryProxyCommand,
    HeartbeatCollectorCommand,
    ListCollectorsCommand,
    RegisterCollectorCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import TenantId, ValidationError

FINGERPRINT = "c" * 64


def _application(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "d" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="test",
            subject="sec-admin",
            roles=("security:admin",),
            token=token,
        )
    )
    return app, token


def test_collector_registry_heartbeat_and_job_authorization(tmp_path: Path) -> None:
    app, token = _application(tmp_path)

    vault_ref = "vault://" + "openinfra/discovery/snmp/par1"
    collector = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="SNMP collector PAR1",
            kind="snmp",
            certificate_fingerprint=FINGERPRINT,
            scopes=("site/par1", "vrf/default"),
            version="1.0.0",
            vault_secret_ref=vault_ref,
            endpoint_url="https://collector-par1.example.tld/agent",
        )
    )

    refreshed = app.discovery_service.heartbeat(
        HeartbeatCollectorCommand(
            tenant_id="default",
            collector_id=collector.id.value,
            certificate_fingerprint=FINGERPRINT,
            version="1.0.1",
            status="ok",
        )
    )
    authorized = app.discovery_service.authorize_job(
        AuthorizeDiscoveryJobCommand(
            tenant_id="default",
            collector_id=collector.id.value,
            certificate_fingerprint=FINGERPRINT,
            requested_scope="site/par1",
            job_type="snmp-scan",
            target="par1-core-01",
        )
    )

    assert refreshed.last_seen_version == "1.0.1"
    assert authorized.authorized is True
    assert authorized.reasons == ()


def test_enterprise_proxy_enrollment_requires_proxy_kind_and_persists_collector(
    tmp_path: Path,
) -> None:
    app, token = _application(tmp_path)

    enrolled = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Paris site proxy",
            kind="site-proxy",
            certificate_fingerprint="3" * 64,
            scopes=("site/par1", "network/core"),
            version="0.29.35",
            endpoint_url="https://proxy-par1.example.tld/agent",
            vault_secret_ref="vault://" + "openinfra/discovery/proxy/par1",
        )
    )

    stored = app.discovery_repository.get_collector(
        TenantId.from_value("default"), enrolled.id.value
    )
    assert stored is not None
    assert enrolled.kind.value == "site-proxy"
    assert enrolled.endpoint_url == "https://proxy-par1.example.tld/agent"
    assert [scope.value for scope in enrolled.scopes] == ["site/par1", "network/core"]


def test_proxy_enrollment_rejects_non_proxy_collector_kind(tmp_path: Path) -> None:
    app, token = _application(tmp_path)

    with pytest.raises(ValidationError, match="proxy enrollment kind"):
        app.discovery_service.enroll_proxy(
            EnrollDiscoveryProxyCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="SNMP collector",
                kind="snmp",
                certificate_fingerprint="4" * 64,
                scopes=("site/par1",),
                version="0.29.35",
                endpoint_url="https://collector.example.tld/agent",
            )
        )


def test_disabled_collector_is_not_authorized_for_new_jobs(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    collector = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="SSH collector PAR1",
            kind="ssh",
            certificate_fingerprint=FINGERPRINT,
            scopes=("site/par1",),
            version="1.0.0",
        )
    )

    disabled = app.discovery_service.disable_collector(
        DisableCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            collector_id=collector.id.value,
            reason="collector certificate rotated",
        )
    )
    decision = app.discovery_service.authorize_job(
        AuthorizeDiscoveryJobCommand(
            tenant_id="default",
            collector_id=collector.id.value,
            certificate_fingerprint=FINGERPRINT,
            requested_scope="site/par1",
            job_type="ssh-inventory",
            target="server01",
        )
    )

    assert disabled.status.value == "disabled"
    assert decision.authorized is False
    assert decision.reasons == ("collector_not_active",)


def test_collector_list_hides_inactive_by_default(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    collector = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Cloud collector",
            kind="cloud",
            certificate_fingerprint=FINGERPRINT,
            scopes=("cloud/aws/prod",),
            version="2026.7",
        )
    )
    app.discovery_service.disable_collector(
        DisableCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            collector_id=collector.id.value,
            reason="disabled for test",
        )
    )

    active_page = app.discovery_service.list_collectors(
        ListCollectorsCommand("default", token, include_inactive=False)
    )
    all_page = app.discovery_service.list_collectors(
        ListCollectorsCommand("default", token, include_inactive=True)
    )

    assert active_page.items == ()
    assert len(all_page.items) == 1


def test_json_discovery_repository_missing_and_cursor_paths(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    assert app.discovery_repository.get_collector(TenantId.from_value("default"), "missing") is None
    first = app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Generic collector 1",
            kind="generic",
            certificate_fingerprint="1" * 64,
            scopes=("site/a",),
            version="1.0.0",
        )
    )
    app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Generic collector 2",
            kind="generic",
            certificate_fingerprint="2" * 64,
            scopes=("site/b",),
            version="1.0.0",
        )
    )

    first_page = app.discovery_service.list_collectors(
        ListCollectorsCommand("default", token, limit=1, include_inactive=True)
    )
    second_page = app.discovery_service.list_collectors(
        ListCollectorsCommand(
            "default", token, limit=1, cursor=first_page.next_cursor, include_inactive=True
        )
    )

    assert first_page.items[0].id == first.id
    assert len(second_page.items) == 1
