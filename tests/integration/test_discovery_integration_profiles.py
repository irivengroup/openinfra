from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    CreateDiscoveryIntegrationProfileCommand,
    DisableDiscoveryIntegrationProfileCommand,
    GetDiscoveryIntegrationProfileCommand,
    ListDiscoveryIntegrationProfilesCommand,
    UpdateDiscoveryIntegrationProfileCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import TenantId, ValidationError

VCENTER_VAULT_REF = "vault://" + "openinfra/discovery/vcenter/par1"
PROXMOX_VAULT_REF = "vault://" + "openinfra/discovery/proxmox/par1"


def _application(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "i" * 40
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


def test_discovery_integration_profile_service_lifecycle(tmp_path: Path) -> None:
    app, token = _application(tmp_path)

    created = app.discovery_service.create_integration_profile(
        CreateDiscoveryIntegrationProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="vCenter PAR1",
            kind="vmware",
            scope="site/par1",
            endpoint_url="https://vcenter.par1.example.local/sdk",
            credential_secret_ref=VCENTER_VAULT_REF,
            max_concurrency=8,
            rate_limit_per_minute=240,
        )
    )
    updated = app.discovery_service.update_integration_profile(
        UpdateDiscoveryIntegrationProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            profile_id=created.id.value,
            rate_limit_per_minute=180,
        )
    )
    fetched = app.discovery_service.get_integration_profile(
        GetDiscoveryIntegrationProfileCommand("default", token, created.id.value)
    )
    active_page = app.discovery_service.list_integration_profiles(
        ListDiscoveryIntegrationProfilesCommand("default", token)
    )
    disabled = app.discovery_service.disable_integration_profile(
        DisableDiscoveryIntegrationProfileCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            profile_id=created.id.value,
            reason="secret rotated",
        )
    )
    hidden_page = app.discovery_service.list_integration_profiles(
        ListDiscoveryIntegrationProfilesCommand("default", token)
    )
    all_page = app.discovery_service.list_integration_profiles(
        ListDiscoveryIntegrationProfilesCommand("default", token, include_inactive=True)
    )
    stored = app.discovery_repository.get_integration_profile(
        TenantId.from_value("default"), created.id.value
    )

    assert created.as_public_dict()["credential_secret_ref"] == "vault://***"
    assert created.connector_family == "virtualization"
    assert updated.rate_limit_per_minute == 180
    assert fetched.id == created.id
    assert len(active_page.items) == 1
    assert disabled.status.value == "disabled"
    assert hidden_page.items == ()
    assert len(all_page.items) == 1
    assert stored is not None


def test_discovery_integration_profile_rejects_insecure_configuration(tmp_path: Path) -> None:
    app, token = _application(tmp_path)

    with pytest.raises(ValidationError, match="https"):
        app.discovery_service.create_integration_profile(
            CreateDiscoveryIntegrationProfileCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Proxmox PAR1",
                kind="proxmox",
                scope="site/par1",
                endpoint_url="http://proxmox.example.local",
                credential_secret_ref=PROXMOX_VAULT_REF,
            )
        )
    with pytest.raises(ValidationError, match="not registered"):
        app.discovery_service.get_integration_profile(
            GetDiscoveryIntegrationProfileCommand("default", token, "missing")
        )
