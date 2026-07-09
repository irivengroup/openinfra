from __future__ import annotations

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.itam_services import (
    AddThirdPartySupportCommand,
    CreateItamPartnerCommand,
    GetAssetSupportCoverageReportCommand,
    GetAssetSupportProfileCommand,
    RegisterManufacturerSupportCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError, NotFoundError


def _admin_token(app: object) -> str:
    token = "itam_" + "a" * 40
    app.security_service.bootstrap_token(  # type: ignore[attr-defined]
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="itam-admin",
            roles=("admin",),
            token=token,
        )
    )
    return token


def _create_partner(app: object, token: str, partner_id: str, kind: str, display_name: str) -> None:
    app.itam_support_service.create_partner(  # type: ignore[attr-defined]
        CreateItamPartnerCommand(
            organization_id="default",
            partner_id=partner_id,
            kind=kind,
            actor="pytest",
            admin_token=token,
            scope_tenant_id="default",
            legal_name=f"{display_name} SAS",
            display_name=display_name,
            registration_number=f"REG-{partner_id.upper()}",
            tax_identifier=f"TAX-{partner_id.upper()}",
            country_code="FR",
            city="Paris",
            address="1 rue du Test",
            contact_email=f"contact-{partner_id}@example.invalid",
            phone="+33123456789",
            support_contact=f"support-{partner_id}@example.invalid",
        )
    )


def test_asset_support_profile_separates_manufacturer_and_third_party(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    _create_partner(app, token, "dell", "manufacturer", "Dell")
    _create_partner(app, token, "thirdsupport", "third_party_support", "ThirdSupport")

    profile = app.itam_support_service.register_manufacturer_support(
        RegisterManufacturerSupportCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            asset_tag="srv-001",
            manufacturer="Dell",
            manufacturer_partner_id="dell",
            warranty_reference="war-001",
            warranty_level="ProSupport Plus",
            warranty_start="2026-01-01",
            warranty_end="2029-01-01",
            support_reference="sup-001",
            support_level="24x7",
            support_contact="support@example.invalid",
        )
    )
    assert profile.as_dict()["complete"] is True

    updated = app.itam_support_service.add_third_party_support(
        AddThirdPartySupportCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            asset_tag="srv-001",
            provider="ThirdSupport",
            provider_partner_id="thirdsupport",
            contract_reference="tp-001",
            support_level="4h onsite",
            support_start="2026-02-01",
            support_end="2027-02-01",
            support_contact="noc@example.invalid",
            notes="Datacenter support overlay",
        )
    )

    payload = updated.as_dict()
    assert payload["manufacturer_warranty"]["support_reference"] == "SUP-001"
    assert payload["third_party_contracts"][0]["contract_reference"] == "TP-001"
    assert payload["third_party_contracts"][0]["provider"] == "ThirdSupport"

    reloaded = app.itam_support_service.get_support_profile(
        GetAssetSupportProfileCommand("default", token, "srv-001")
    )
    assert reloaded.as_dict() == updated.as_dict()

    coverage = app.itam_support_service.get_support_coverage_report(
        GetAssetSupportCoverageReportCommand("default", token, "srv-001", as_of="2026-07-01")
    ).as_dict()
    assert coverage["coverage_state"] == "manufacturer_active"
    assert coverage["warranty_days_remaining"] > 800
    assert coverage["third_party_active_count"] == 1


def test_manufacturer_support_is_immutable_and_third_party_requires_profile(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    _create_partner(app, token, "dell", "manufacturer", "Dell")
    _create_partner(app, token, "thirdsupport", "third_party_support", "ThirdSupport")

    with pytest.raises(NotFoundError, match="manufacturer warranty/support"):
        app.itam_support_service.add_third_party_support(
            AddThirdPartySupportCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                asset_tag="missing",
                provider="ThirdSupport",
                provider_partner_id="thirdsupport",
                contract_reference="tp-001",
                support_level="4h onsite",
                support_start="2026-02-01",
                support_end="2027-02-01",
                support_contact="noc@example.invalid",
            )
        )

    command = RegisterManufacturerSupportCommand(
        tenant_id="default",
        actor="pytest",
        admin_token=token,
        asset_tag="srv-immut",
        manufacturer="Dell",
        manufacturer_partner_id="dell",
        warranty_reference="war-001",
        warranty_level="ProSupport",
        warranty_start="2026-01-01",
        warranty_end="2029-01-01",
        support_reference="sup-001",
        support_level="24x7",
        support_contact="support@example.invalid",
    )
    app.itam_support_service.register_manufacturer_support(command)
    with pytest.raises(ConflictError, match="immutable"):
        app.itam_support_service.register_manufacturer_support(
            RegisterManufacturerSupportCommand(
                tenant_id=command.tenant_id,
                actor=command.actor,
                admin_token=command.admin_token,
                asset_tag=command.asset_tag,
                manufacturer=command.manufacturer,
                manufacturer_partner_id="dell",
                warranty_reference=command.warranty_reference,
                warranty_level=command.warranty_level,
                warranty_start=command.warranty_start,
                warranty_end=command.warranty_end,
                support_reference="sup-002",
                support_level=command.support_level,
                support_contact=command.support_contact,
            )
        )
