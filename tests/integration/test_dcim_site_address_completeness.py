from __future__ import annotations

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import CreateDcimSiteCommand, UpdateDcimSiteCommand
from openinfra.application.itam_services import (
    CreateItamOrganizationCommand,
    UpdateItamOrganizationCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand


def test_dcim_site_keeps_complete_address(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)

    created = app.dcim_topology_service.create_site(
        CreateDcimSiteCommand(
            tenant_id="default",
            actor="pytest",
            code="par2",
            name="Paris 2",
            country="fr",
            city="Paris",
            region="IDF",
            street_address="111 Quai du Président Roosevelt",
            postal_code="92130",
            contact_email="site-par2@example.net",
            phone="+33123456789",
        )
    )

    assert created["country"] == "FR"
    assert created["street_address"] == "111 Quai du Président Roosevelt"
    assert created["postal_code"] == "92130"
    assert created["contact_email"] == "site-par2@example.net"
    assert created["phone"] == "+33123456789"

    updated = app.dcim_topology_service.update_site(
        UpdateDcimSiteCommand(
            tenant_id="default",
            actor="pytest",
            code="PAR2",
            postal_code="75015",
            phone="+33111111111",
        )
    )

    assert updated["street_address"] == "111 Quai du Président Roosevelt"
    assert updated["postal_code"] == "75015"
    assert updated["phone"] == "+33111111111"


def test_itam_organization_keeps_phone(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "a" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="admin",
            roles=("admin",),
            token=token,
        )
    )

    created = app.itam_support_service.create_organization(
        CreateItamOrganizationCommand(
            organization_id="orange",
            actor="pytest",
            admin_token=token,
            legal_name="Orange SA",
            registration_number="RCS PARIS 380 129 866",
            tax_identifier="FR89380129866",
            country_code="fr",
            city="Paris",
            address="111 Quai du Président Roosevelt",
            contact_email="contact@orange.example",
            phone="+33123456789",
            support_contact="support@orange.example",
        )
    )

    assert created.country_code == "FR"
    assert created.phone == "+33123456789"

    updated = app.itam_support_service.update_organization(
        UpdateItamOrganizationCommand(
            organization_id="orange",
            actor="pytest",
            admin_token=token,
            phone="+33111111111",
        )
    )

    assert updated.phone == "+33111111111"
