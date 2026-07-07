from __future__ import annotations

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.itam_services import (
    AddThirdPartySupportCommand,
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


def test_asset_support_profile_separates_manufacturer_and_third_party(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    profile = app.itam_support_service.register_manufacturer_support(
        RegisterManufacturerSupportCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            asset_tag="srv-001",
            manufacturer="Dell",
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


def test_manufacturer_support_is_immutable_and_third_party_requires_profile(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    with pytest.raises(NotFoundError, match="manufacturer warranty/support"):
        app.itam_support_service.add_third_party_support(
            AddThirdPartySupportCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                asset_tag="missing",
                provider="ThirdSupport",
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
                warranty_reference=command.warranty_reference,
                warranty_level=command.warranty_level,
                warranty_start=command.warranty_start,
                warranty_end=command.warranty_end,
                support_reference="sup-002",
                support_level=command.support_level,
                support_contact=command.support_contact,
            )
        )
