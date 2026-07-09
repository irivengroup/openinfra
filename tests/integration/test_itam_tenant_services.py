from __future__ import annotations

import json

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.itam_services import (
    CreateItamOrganizationCommand,
    CreateItamPartnerCommand,
    CreateItamTenantCommand,
    DeleteItamOrganizationCommand,
    DeleteItamPartnerCommand,
    DeleteItamTenantCommand,
    GetItamPartnerCommand,
    ListItamOrganizationsCommand,
    ListItamPartnersCommand,
    ListItamTenantsCommand,
    UpdateItamPartnerCommand,
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


def test_itam_organization_identity_filters_tenants_and_retire_cascades(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    organization = app.itam_support_service.create_organization(
        CreateItamOrganizationCommand(
            organization_id="orange",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            legal_name="Orange SA",
            display_name="Orange",
            registration_number="RCS PARIS 380 129 866",
            tax_identifier="FR89380129866",
            country_code="FR",
            city="Paris",
            address="111 Quai du Président Roosevelt",
            contact_email="contact@orange.example",
            support_contact="support@orange.example",
        )
    )
    tenant = app.itam_support_service.create_tenant(
        CreateItamTenantCommand(
            tenant_id="dsi",
            organization_id="orange",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="DSI",
        )
    )

    organizations = app.itam_support_service.list_organizations(
        ListItamOrganizationsCommand("default", token)
    ).as_dict()
    tenants = app.itam_support_service.list_tenants(
        ListItamTenantsCommand("default", token)
    ).as_dict()

    assert organization.as_dict()["organization_id"] == "orange"
    assert tenant.as_dict()["organization_id"] == "orange"
    assert any(item["organization_id"] == "orange" for item in organizations["items"])
    assert any(
        item["tenant_id"] == "dsi" and item["organization_id"] == "orange"
        for item in tenants["items"]
    )

    retired = app.itam_support_service.delete_organization(
        DeleteItamOrganizationCommand(
            organization_id="orange",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
        )
    )
    retired_tenants = app.itam_support_service.list_tenants(
        ListItamTenantsCommand("default", token, include_retired=True)
    ).as_dict()["items"]
    retired_tenant = next(item for item in retired_tenants if item["tenant_id"] == "dsi")

    assert retired.as_dict()["status"] == "retired"
    assert retired_tenant["status"] == "retired"
    assert retired_tenant["selectable"] is False


def test_itam_organization_cli_crud(tmp_path, capsys) -> None:
    data = tmp_path / "cli-orgs.json"
    token = "o" * 40
    assert (
        OpenInfraCLI().run(
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
        == 0
    )
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organization-create",
                "--data",
                str(data),
                "--organization",
                "orange",
                "--scope-tenant",
                "default",
                "--admin-token",
                token,
                "--legal-name",
                "Orange SA",
                "--display-name",
                "Orange",
                "--registration-number",
                "RCS PARIS 380 129 866",
                "--tax-identifier",
                "FR89380129866",
                "--country-code",
                "FR",
                "--city",
                "Paris",
                "--address",
                "111 Quai du Président Roosevelt",
                "--contact-email",
                "contact@orange.example",
                "--support-contact",
                "support@orange.example",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["organization_id"] == "orange"

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "tenant-create",
                "--data",
                str(data),
                "--tenant",
                "dsi",
                "--organization",
                "orange",
                "--scope-tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "DSI",
            ]
        )
        == 0
    )
    tenant = json.loads(capsys.readouterr().out)
    assert tenant["organization_id"] == "orange"

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organizations",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    organizations = json.loads(capsys.readouterr().out)
    assert any(item["organization_id"] == "orange" for item in organizations["items"])

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organization",
                "--data",
                str(data),
                "--organization",
                "orange",
                "--tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    loaded = json.loads(capsys.readouterr().out)
    assert loaded["legal_name"] == "Orange SA"

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organization-update",
                "--data",
                str(data),
                "--organization",
                "orange",
                "--scope-tenant",
                "default",
                "--admin-token",
                token,
                "--legal-name",
                "Orange France SA",
                "--support-contact",
                "soc@example.invalid",
            ]
        )
        == 0
    )
    updated = json.loads(capsys.readouterr().out)
    assert updated["legal_name"] == "Orange France SA"

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organization-delete",
                "--data",
                str(data),
                "--organization",
                "orange",
                "--scope-tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    retired = json.loads(capsys.readouterr().out)
    assert retired["status"] == "retired"


def test_itam_partner_registry_crud_and_accreditation_scope(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    app.itam_support_service.create_organization(
        CreateItamOrganizationCommand(
            organization_id="orange",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            legal_name="Orange SA",
            display_name="Orange",
            registration_number="RCS PARIS 380 129 866",
            tax_identifier="FR89380129866",
            country_code="FR",
            city="Paris",
            address="111 Quai du Président Roosevelt",
            contact_email="contact@orange.example",
            support_contact="support@orange.example",
        )
    )

    partner = app.itam_support_service.create_partner(
        CreateItamPartnerCommand(
            organization_id="orange",
            partner_id="dell",
            kind="manufacturer",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            legal_name="Dell Technologies France SAS",
            display_name="Dell Technologies",
            registration_number="REG-DELL-FR",
            tax_identifier="TAX-DELL-FR",
            country_code="FR",
            city="Paris",
            address="2 rue du Fournisseur",
            contact_email="account@dell.example",
            phone="+33123456789",
            support_contact="support@dell.example",
            website="https://www.dell.example",
        )
    )
    assert partner.as_dict()["organization_id"] == "orange"
    assert partner.as_dict()["kind"] == "manufacturer"
    assert partner.as_dict()["selectable"] is True

    catalog = app.itam_support_service.list_partners(
        ListItamPartnersCommand("default", token, organization_id="orange", kind="manufacturer")
    ).as_dict()
    assert [item["partner_id"] for item in catalog["items"]] == ["dell"]

    updated = app.itam_support_service.update_partner(
        UpdateItamPartnerCommand(
            organization_id="orange",
            partner_id="dell",
            scope_tenant_id="default",
            actor="pytest",
            admin_token=token,
            status="suspended",
            phone="+33987654321",
        )
    ).as_dict()
    assert updated["status"] == "suspended"
    assert updated["selectable"] is False

    loaded = app.itam_support_service.get_partner(
        GetItamPartnerCommand(
            organization_id="orange",
            partner_id="dell",
            admin_token=token,
            scope_tenant_id="default",
        )
    ).as_dict()
    assert loaded["phone"] == "+33987654321"

    retired = app.itam_support_service.delete_partner(
        DeleteItamPartnerCommand(
            organization_id="orange",
            partner_id="dell",
            actor="pytest",
            admin_token=token,
            scope_tenant_id="default",
        )
    ).as_dict()
    assert retired["status"] == "retired"


def test_itam_partner_cli_crud(tmp_path, capsys) -> None:
    data = tmp_path / "cli-partners.json"
    token = "p" * 40
    assert (
        OpenInfraCLI().run(
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
        == 0
    )
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner-create",
                "--data",
                str(data),
                "--organization",
                "default",
                "--partner",
                "publisher",
                "--kind",
                "software_publisher",
                "--admin-token",
                token,
                "--legal-name",
                "Publisher SAS",
                "--registration-number",
                "REG-PUBLISHER",
                "--tax-identifier",
                "TAX-PUBLISHER",
                "--country-code",
                "FR",
                "--city",
                "Paris",
                "--address",
                "3 rue Logiciel",
                "--contact-email",
                "contact@publisher.example",
                "--phone",
                "+33111111111",
                "--support-contact",
                "support@publisher.example",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["partner_id"] == "publisher"

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partners",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--organization",
                "default",
                "--kind",
                "software_publisher",
            ]
        )
        == 0
    )
    catalog = json.loads(capsys.readouterr().out)
    assert [item["partner_id"] for item in catalog["items"]] == ["publisher"]

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner-delete",
                "--data",
                str(data),
                "--organization",
                "default",
                "--partner",
                "publisher",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    retired = json.loads(capsys.readouterr().out)
    assert retired["status"] == "retired"
