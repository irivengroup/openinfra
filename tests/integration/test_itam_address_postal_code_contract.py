from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.itam_services import (
    CreateItamOrganizationCommand,
    CreateItamPartnerCommand,
    DeleteItamOrganizationCommand,
    DeleteItamPartnerCommand,
    GetItamOrganizationCommand,
    GetItamPartnerCommand,
    ListItamOrganizationsCommand,
    ListItamPartnersCommand,
    UpdateItamOrganizationCommand,
    UpdateItamPartnerCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ValidationError
from openinfra.domain.itam import ItamOrganization, ItamPartner
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _post_json(url: str, payload: dict[str, object], token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_itam_organization_partner_postal_code_domain_validation() -> None:
    organization = ItamOrganization.create(
        organization_id="org-postal",
        legal_name="Postal Organization SAS",
        actor="pytest",
        registration_number="REG-POSTAL",
        tax_identifier="TAX-POSTAL",
        country_code="fr",
        city=" Paris ",
        postal_code=" 75008 ",
        address="1 avenue Postal",
        contact_email="contact-postal@example.invalid",
        phone="+33123456789",
        support_contact="support-postal@example.invalid",
    )
    partner = ItamPartner.create(
        partner_id="partner-postal",
        organization_id=organization.id,
        kind="manufacturer",
        legal_name="Postal Partner SAS",
        actor="pytest",
        registration_number="REG-PARTNER",
        tax_identifier="TAX-PARTNER",
        country_code="fr",
        city="Paris",
        postal_code="75009",
        address="2 avenue Postal",
        contact_email="contact-partner@example.invalid",
        phone="+33123456780",
        support_contact="support-partner@example.invalid",
        website="https://partner.example.invalid",
    )

    assert organization.postal_code == "75008"
    assert organization.as_dict()["postal_code"] == "75008"
    assert partner.postal_code == "75009"
    assert partner.as_dict()["postal_code"] == "75009"

    with pytest.raises(ValidationError, match="organization status"):
        ItamOrganization.restore(
            organization_id="org-bad-status",
            legal_name="Bad Status",
            display_name="Bad Status",
            status="unknown",
            registration_number="REG",
            tax_identifier="TAX",
            country_code="FR",
            city="Paris",
            postal_code="75000",
            address="1 rue Test",
            contact_email="contact@example.invalid",
            phone="+33123456789",
            support_contact="support@example.invalid",
            description=None,
            created_by="pytest",
            created_at=organization.created_at,
            updated_by="pytest",
            updated_at=organization.updated_at,
        )
    with pytest.raises(ValidationError, match="country code"):
        organization.update(actor="pytest", country_code="FRA")
    with pytest.raises(ValidationError, match="postal code"):
        organization.update(actor="pytest", postal_code="")
    with pytest.raises(ValidationError, match="partner kind"):
        partner.update(actor="pytest", kind="integrator")
    with pytest.raises(ValidationError, match="partner status"):
        partner.update(actor="pytest", status="disabled")
    with pytest.raises(ValidationError, match="country code"):
        partner.update(actor="pytest", country_code="France")
    with pytest.raises(ValidationError, match="business phone"):
        partner.update(actor="pytest", phone="bad")
    with pytest.raises(ValidationError, match="http:// or https://"):
        partner.update(actor="pytest", website="ftp://partner.example.invalid")


def test_itam_organization_partner_postal_code_service_cli_and_http(tmp_path: Path, capsys) -> None:
    state = tmp_path / "postal-state.json"
    token = "p" * 40
    app = ApplicationFactory().create_json_application(state, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="postal-admin",
            roles=("admin",),
            token=token,
        )
    )
    service = app.itam_support_service

    organization = service.create_organization(
        CreateItamOrganizationCommand(
            organization_id="postal-org",
            actor="pytest",
            admin_token=token,
            legal_name="Postal Org SAS",
            display_name="Postal Org",
            registration_number="REG-ORG",
            tax_identifier="TAX-ORG",
            country_code="FR",
            city="Paris",
            postal_code="75010",
            address="10 rue Organisation",
            contact_email="contact-org@example.invalid",
            phone="+33100000000",
            support_contact="support-org@example.invalid",
        )
    )
    updated_organization = service.update_organization(
        UpdateItamOrganizationCommand(
            organization_id="postal-org",
            actor="pytest",
            admin_token=token,
            postal_code="75011",
            address="11 rue Organisation",
            phone="+33100000011",
        )
    )
    listed_organizations = service.list_organizations(
        ListItamOrganizationsCommand("default", token, include_retired=True)
    )
    loaded_organization = service.get_organization(GetItamOrganizationCommand("postal-org", token))
    partner = service.create_partner(
        CreateItamPartnerCommand(
            organization_id="postal-org",
            partner_id="postal-partner",
            kind="software_publisher",
            actor="pytest",
            admin_token=token,
            legal_name="Postal Partner SAS",
            display_name="Postal Partner",
            registration_number="REG-PARTNER",
            tax_identifier="TAX-PARTNER",
            country_code="FR",
            city="Paris",
            postal_code="75012",
            address="12 rue Partenaire",
            contact_email="contact-partner@example.invalid",
            phone="+33100000012",
            support_contact="support-partner@example.invalid",
            website="https://partner.example.invalid",
        )
    )
    updated_partner = service.update_partner(
        UpdateItamPartnerCommand(
            organization_id="postal-org",
            partner_id="postal-partner",
            actor="pytest",
            admin_token=token,
            postal_code="75013",
            phone="+33100000013",
        )
    )
    loaded_partner = service.get_partner(
        GetItamPartnerCommand("postal-org", "postal-partner", token)
    )
    listed_partners = service.list_partners(
        ListItamPartnersCommand(
            "default", token, organization_id="postal-org", include_retired=True
        )
    )
    retired_partner = service.delete_partner(
        DeleteItamPartnerCommand("postal-org", "postal-partner", "pytest", token)
    )
    retired_organization = service.delete_organization(
        DeleteItamOrganizationCommand("postal-org", "pytest", token)
    )

    assert organization.postal_code == "75010"
    assert updated_organization.postal_code == "75011"
    assert loaded_organization.postal_code == "75011"
    assert listed_organizations.as_dict()["items"][0]["postal_code"]
    assert partner.postal_code == "75012"
    assert updated_partner.postal_code == "75013"
    assert loaded_partner.postal_code == "75013"
    assert listed_partners.as_dict()["items"][0]["postal_code"] == "75013"
    assert retired_partner.status.value == "retired"
    assert retired_organization.status.value == "retired"

    assert (
        OpenInfraCLI().run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--subject",
                "cli-postal",
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
                str(state),
                "--organization",
                "cli-org",
                "--admin-token",
                token,
                "--legal-name",
                "CLI Org SAS",
                "--display-name",
                "CLI Org",
                "--registration-number",
                "REG-CLI",
                "--tax-identifier",
                "TAX-CLI",
                "--country-code",
                "FR",
                "--city",
                "Paris",
                "--postal-code",
                "75100",
                "--address",
                "100 rue CLI",
                "--contact-email",
                "cli-org@example.invalid",
                "--phone",
                "+33100100100",
                "--support-contact",
                "support-cli-org@example.invalid",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["postal_code"] == "75100"
    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organization",
                "--data",
                str(state),
                "--organization",
                "cli-org",
                "--tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["postal_code"] == "75100"
    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "organization-update",
                "--data",
                str(state),
                "--organization",
                "cli-org",
                "--admin-token",
                token,
                "--postal-code",
                "75101",
                "--phone",
                "+33100100101",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["postal_code"] == "75101"
    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner-create",
                "--data",
                str(state),
                "--organization",
                "cli-org",
                "--partner",
                "cli-partner",
                "--kind",
                "manufacturer",
                "--admin-token",
                token,
                "--legal-name",
                "CLI Partner SAS",
                "--display-name",
                "CLI Partner",
                "--registration-number",
                "REG-CLI-PARTNER",
                "--tax-identifier",
                "TAX-CLI-PARTNER",
                "--country-code",
                "FR",
                "--city",
                "Paris",
                "--postal-code",
                "75102",
                "--address",
                "102 rue CLI",
                "--contact-email",
                "cli-partner@example.invalid",
                "--phone",
                "+33100100102",
                "--support-contact",
                "support-cli-partner@example.invalid",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["postal_code"] == "75102"
    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner",
                "--data",
                str(state),
                "--organization",
                "cli-org",
                "--partner",
                "cli-partner",
                "--tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["postal_code"] == "75102"
    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner-update",
                "--data",
                str(state),
                "--organization",
                "cli-org",
                "--partner",
                "cli-partner",
                "--admin-token",
                token,
                "--postal-code",
                "75103",
                "--phone",
                "+33100100103",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["postal_code"] == "75103"
    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner-delete",
                "--data",
                str(state),
                "--organization",
                "cli-org",
                "--partner",
                "cli-partner",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "retired"

    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        http_org = _post_json(
            base + "/api/v1/itam/organization/create",
            {
                "organization_id": "http-org",
                "legal_name": "HTTP Org SAS",
                "display_name": "HTTP Org",
                "registration_number": "REG-HTTP",
                "tax_identifier": "TAX-HTTP",
                "country_code": "FR",
                "city": "Paris",
                "postal_code": "75200",
                "address": "200 rue HTTP",
                "contact_email": "http-org@example.invalid",
                "phone": "+33100200200",
                "support_contact": "support-http-org@example.invalid",
            },
            token,
        )
        assert http_org["postal_code"] == "75200"
        http_org_update = _post_json(
            base + "/api/v1/itam/organization/update",
            {"organization_id": "http-org", "postal_code": "75201", "phone": "+33100200201"},
            token,
        )
        assert http_org_update["postal_code"] == "75201"
        loaded_http_org = _get_json(
            base + "/api/v1/itam/organization?tenant_id=default&organization_id=http-org",
            token,
        )
        assert loaded_http_org["postal_code"] == "75201"
        http_partner = _post_json(
            base + "/api/v1/itam/partner/create",
            {
                "organization_id": "http-org",
                "partner_id": "http-partner",
                "kind": "third_party_support",
                "legal_name": "HTTP Partner SAS",
                "display_name": "HTTP Partner",
                "registration_number": "REG-HTTP-PARTNER",
                "tax_identifier": "TAX-HTTP-PARTNER",
                "country_code": "FR",
                "city": "Paris",
                "postal_code": "75202",
                "address": "202 rue HTTP",
                "contact_email": "http-partner@example.invalid",
                "phone": "+33100200202",
                "support_contact": "support-http-partner@example.invalid",
            },
            token,
        )
        assert http_partner["postal_code"] == "75202"
        http_partner_update = _post_json(
            base + "/api/v1/itam/partner/update",
            {
                "organization_id": "http-org",
                "partner_id": "http-partner",
                "postal_code": "75203",
                "phone": "+33100200203",
            },
            token,
        )
        assert http_partner_update["postal_code"] == "75203"
        loaded_http_partner = _get_json(
            base
            + "/api/v1/itam/partner?tenant_id=default&organization_id=http-org&partner_id=http-partner",
            token,
        )
        assert loaded_http_partner["postal_code"] == "75203"
        deleted_http_partner = _post_json(
            base + "/api/v1/itam/partner/delete",
            {"organization_id": "http-org", "partner_id": "http-partner"},
            token,
        )
        deleted_http_org = _post_json(
            base + "/api/v1/itam/organization/delete",
            {"organization_id": "http-org"},
            token,
        )
        assert deleted_http_partner["status"] == "retired"
        assert deleted_http_org["status"] == "retired"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
