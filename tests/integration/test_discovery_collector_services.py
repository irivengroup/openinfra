from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
    BuildLocalDiscoveryPlanCommand,
    DisableCollectorCommand,
    EnrollDiscoveryProxyCommand,
    HeartbeatCollectorCommand,
    ListCollectorsCommand,
    RegisterCollectorCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import TenantId, ValidationError

FINGERPRINT = "c" * 64
LOCAL_VAULT_REF = "vault://" + "openinfra/discovery/local/par1"


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
            version="0.29.36",
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
                version="0.29.36",
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


def test_local_discovery_plan_lite_without_agent_or_rsot_mutation(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="lite")
    token = "e" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="test",
            subject="sec-admin",
            roles=("security:admin",),
            token=token,
        )
    )

    plan = app.discovery_service.build_local_discovery_plan(
        BuildLocalDiscoveryPlanCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Discovery PAR1",
            scope="site/par1",
            protocol="ssh",
            targets=("srv-app-01", "srv-app-02"),
            credential_secret_ref=LOCAL_VAULT_REF,
            max_concurrency=2,
            rate_limit_per_minute=60,
        )
    )

    payload = plan.as_dict()
    assert payload["edition"] == "lite"
    assert payload["dry_run"] is True
    assert payload["agent_required"] is False
    assert payload["network_scan_executed"] is False
    assert payload["rsot_write_enabled"] is False
    assert payload["targets_count"] == 2
    assert len(app.audit_repository.list_events()) >= 1


def test_local_discovery_plan_rejects_enterprise_runtime(tmp_path: Path) -> None:
    app, token = _application(tmp_path)

    with pytest.raises(ValidationError, match="lite and pro"):
        app.discovery_service.build_local_discovery_plan(
            BuildLocalDiscoveryPlanCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Discovery PAR1",
                scope="site/par1",
                protocol="snmp",
                targets=("10.20.30.10",),
                credential_secret_ref=LOCAL_VAULT_REF,
            )
        )


def test_discovery_protocol_profile_lifecycle_and_local_plan_binding(tmp_path: Path) -> None:
    from openinfra.application.discovery_services import (
        CreateDiscoveryProtocolProfileCommand,
        DisableDiscoveryProtocolProfileCommand,
        GetDiscoveryProtocolProfileCommand,
        ListDiscoveryProtocolProfilesCommand,
        UpdateDiscoveryProtocolProfileCommand,
    )

    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="pro")
    token = "p" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="test",
            subject="sec-admin",
            roles=("security:admin",),
            token=token,
        )
    )

    profile = app.discovery_service.create_protocol_profile(
        CreateDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="SNMPv3 PAR1",
            protocol="snmp",
            scope="site/par1",
            credential_secret_ref="vault://" + "openinfra/discovery/snmp/par1",
            max_concurrency=8,
            rate_limit_per_minute=240,
        )
    )
    updated = app.discovery_service.update_protocol_profile(
        UpdateDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            profile_id=profile.id.value,
            rate_limit_per_minute=180,
        )
    )
    loaded = app.discovery_service.get_protocol_profile(
        GetDiscoveryProtocolProfileCommand("default", token, profile.id.value)
    )
    page = app.discovery_service.list_protocol_profiles(
        ListDiscoveryProtocolProfilesCommand("default", token)
    )
    plan = app.discovery_service.build_local_discovery_plan(
        BuildLocalDiscoveryPlanCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Discovery PAR1 SNMP",
            scope="site/par1",
            protocol="snmp",
            targets=("10.20.30.10",),
            credential_secret_ref="vault://" + "openinfra/discovery/unused",
            max_concurrency=1,
            rate_limit_per_minute=1,
            protocol_profile_id=profile.id.value,
        )
    )
    disabled = app.discovery_service.disable_protocol_profile(
        DisableDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            profile_id=profile.id.value,
            reason="secret rotation",
        )
    )
    active_page = app.discovery_service.list_protocol_profiles(
        ListDiscoveryProtocolProfilesCommand("default", token)
    )
    all_page = app.discovery_service.list_protocol_profiles(
        ListDiscoveryProtocolProfilesCommand("default", token, include_inactive=True)
    )

    assert updated.rate_limit_per_minute == 180
    assert loaded.as_public_dict()["credential_secret_ref"] == "vault://***"
    assert page.items[0].id == profile.id
    assert plan.protocol_profile_id == profile.id.value
    assert plan.max_concurrency == 8
    assert plan.rate_limit_per_minute == 180
    assert plan.jobs[0].protocol_profile_id == profile.id.value
    assert disabled.status.value == "disabled"
    assert active_page.items == ()
    assert len(all_page.items) == 1


def test_local_discovery_rejects_mismatched_protocol_profile(tmp_path: Path) -> None:
    from openinfra.application.discovery_services import CreateDiscoveryProtocolProfileCommand

    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="lite")
    token = "q" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="test",
            subject="sec-admin",
            roles=("security:admin",),
            token=token,
        )
    )
    profile = app.discovery_service.create_protocol_profile(
        CreateDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="SSH PAR1",
            protocol="ssh",
            scope="site/par1",
            credential_secret_ref="vault://" + "openinfra/discovery/ssh/par1",
        )
    )

    with pytest.raises(ValidationError, match="protocol must match"):
        app.discovery_service.build_local_discovery_plan(
            BuildLocalDiscoveryPlanCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Discovery mismatch",
                scope="site/par1",
                protocol="snmp",
                targets=("srv-app-01",),
                credential_secret_ref="vault://" + "openinfra/discovery/local/par1",
                protocol_profile_id=profile.id.value,
            )
        )


def test_protocol_profile_rejection_and_pagination_paths(tmp_path: Path) -> None:
    from openinfra.application.discovery_services import (
        CreateDiscoveryProtocolProfileCommand,
        DisableDiscoveryProtocolProfileCommand,
        GetDiscoveryProtocolProfileCommand,
        ListDiscoveryProtocolProfilesCommand,
        UpdateDiscoveryProtocolProfileCommand,
    )

    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="pro")
    token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="test",
            subject="sec-admin",
            roles=("security:admin",),
            token=token,
        )
    )

    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.get_protocol_profile(
            GetDiscoveryProtocolProfileCommand("default", token, "missing")
        )
    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.update_protocol_profile(
            UpdateDiscoveryProtocolProfileCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                profile_id="missing",
                name="SSH missing",
            )
        )
    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.disable_protocol_profile(
            DisableDiscoveryProtocolProfileCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                profile_id="missing",
                reason="missing profile",
            )
        )
    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.build_local_discovery_plan(
            BuildLocalDiscoveryPlanCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Discovery missing profile",
                scope="site/par1",
                protocol="ssh",
                targets=("srv-app-01",),
                credential_secret_ref="vault://" + "openinfra/discovery/local/par1",
                protocol_profile_id="missing",
            )
        )

    first = app.discovery_service.create_protocol_profile(
        CreateDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="SSH PAR1",
            protocol="ssh",
            scope="site/par1",
            credential_secret_ref="vault://" + "openinfra/discovery/ssh/par1",
        )
    )
    second = app.discovery_service.create_protocol_profile(
        CreateDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="WinRM PAR2",
            protocol="winrm",
            scope="site/par2",
            credential_secret_ref="vault://" + "openinfra/discovery/winrm/par2",
        )
    )

    first_page = app.discovery_service.list_protocol_profiles(
        ListDiscoveryProtocolProfilesCommand("default", token, limit=1, include_inactive=True)
    )
    second_page = app.discovery_service.list_protocol_profiles(
        ListDiscoveryProtocolProfilesCommand(
            "default", token, limit=1, cursor=first_page.next_cursor, include_inactive=True
        )
    )

    assert first_page.items == (first,)
    assert second_page.items == (second,)

    disabled = app.discovery_service.disable_protocol_profile(
        DisableDiscoveryProtocolProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            profile_id=first.id.value,
            reason="security rotation",
        )
    )
    assert disabled.disabled_reason == "security rotation"

    with pytest.raises(ValidationError, match="must be active"):
        app.discovery_service.build_local_discovery_plan(
            BuildLocalDiscoveryPlanCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Discovery disabled profile",
                scope="site/par1",
                protocol="ssh",
                targets=("srv-app-01",),
                credential_secret_ref="vault://" + "openinfra/discovery/local/par1",
                protocol_profile_id=first.id.value,
            )
        )
    with pytest.raises(ValidationError, match="scope must match"):
        app.discovery_service.build_local_discovery_plan(
            BuildLocalDiscoveryPlanCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Discovery scope mismatch",
                scope="site/par1",
                protocol="winrm",
                targets=("srv-app-02",),
                credential_secret_ref="vault://" + "openinfra/discovery/local/par2",
                protocol_profile_id=second.id.value,
            )
        )
