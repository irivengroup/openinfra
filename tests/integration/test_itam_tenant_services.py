from __future__ import annotations

import json

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.itam_services import (
    CreateItamTenantCommand,
    DeleteItamTenantCommand,
    ListItamTenantsCommand,
    UpdateItamTenantCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError, ValidationError
from openinfra.interfaces.cli import OpenInfraCLI


def _admin_token(app: object) -> str:
    token = "ten_" + "b" * 40
    app.security_service.bootstrap_token(  # type: ignore[attr-defined]
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="itam-tenant-admin",
            roles=("admin",),
            token=token,
        )
    )
    return token


def test_itam_tenant_crud_default_and_auto_selection(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    initial = app.itam_support_service.list_tenants(
        ListItamTenantsCommand("default", token)
    ).as_dict()
    assert initial["auto_selected_tenant_id"] == "default"
    assert initial["default_tenant_id"] == "default"

    tenant = app.itam_support_service.create_tenant(
        CreateItamTenantCommand(
            tenant_id="production",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Production",
            is_default=True,
            description="Tenant production",
        )
    )
    assert tenant.as_dict()["is_default"] is True

    catalog = app.itam_support_service.list_tenants(
        ListItamTenantsCommand("default", token)
    ).as_dict()
    assert catalog["default_tenant_id"] == "production"
    assert catalog["auto_selected_tenant_id"] is None

    updated = app.itam_support_service.update_tenant(
        UpdateItamTenantCommand(
            tenant_id="production",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Production IT",
            is_default=False,
        )
    ).as_dict()
    assert updated["name"] == "Production IT"
    assert updated["is_default"] is False

    retired = app.itam_support_service.delete_tenant(
        DeleteItamTenantCommand(
            tenant_id="production",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
        )
    ).as_dict()
    assert retired["status"] == "retired"
    assert retired["selectable"] is False

    active = app.itam_support_service.list_tenants(
        ListItamTenantsCommand("default", token)
    ).as_dict()
    assert [item["tenant_id"] for item in active["items"]] == ["default"]


def test_itam_tenant_conflicts_and_default_guard(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    command = CreateItamTenantCommand(
        tenant_id="sandbox",
        scope_tenant_id="default",
        actor="pytest",
        admin_token=token,
        name="Sandbox",
    )
    app.itam_support_service.create_tenant(command)
    with pytest.raises(ConflictError):
        app.itam_support_service.create_tenant(command)

    with pytest.raises(ValidationError, match="active ITAM tenant"):
        app.itam_support_service.create_tenant(
            CreateItamTenantCommand(
                tenant_id="retired-default",
                scope_tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Bad default",
                status="retired",
                is_default=True,
            )
        )


def test_itam_tenant_cli_crud_and_default(tmp_path, capsys) -> None:
    data = tmp_path / "cli-tenants.json"
    token = "c" * 40
    bootstrap_code = OpenInfraCLI().run(
        [
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "itam-cli-admin",
            "--role",
            "admin",
            "--token",
            token,
        ]
    )
    capsys.readouterr()

    create_code = OpenInfraCLI().run(
        [
            "itam",
            "tenant-create",
            "--data",
            str(data),
            "--tenant",
            "ops",
            "--scope-tenant",
            "default",
            "--admin-token",
            token,
            "--name",
            "Operations",
            "--default",
        ]
    )
    created = json.loads(capsys.readouterr().out)

    list_code = OpenInfraCLI().run(
        [
            "itam",
            "tenants",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
        ]
    )
    catalog = json.loads(capsys.readouterr().out)

    assert bootstrap_code == 0
    assert create_code == 0
    assert list_code == 0
    assert created["tenant_id"] == "ops"
    assert catalog["default_tenant_id"] == "ops"
