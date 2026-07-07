from __future__ import annotations

from datetime import date

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.itam import (
    ManufacturerWarranty,
    PhysicalAssetSupportProfile,
    ThirdPartySupportContract,
)


def test_manufacturer_warranty_requires_valid_period_and_support_reference() -> None:
    warranty = ManufacturerWarranty.create(
        manufacturer="Dell",
        warranty_reference="war-123",
        warranty_level="ProSupport Plus",
        warranty_start=date(2026, 1, 1),
        warranty_end=date(2028, 1, 1),
        support_reference="sup-123",
        support_level="24x7",
        support_contact="support@example.invalid",
    )

    assert warranty.as_dict()["warranty_reference"] == "WAR-123"
    assert warranty.as_dict()["support_reference"] == "SUP-123"

    with pytest.raises(ValidationError, match="end date cannot be before"):
        ManufacturerWarranty.create(
            manufacturer="Dell",
            warranty_reference="war-123",
            warranty_level="ProSupport Plus",
            warranty_start=date(2028, 1, 1),
            warranty_end=date(2026, 1, 1),
            support_reference="sup-123",
            support_level="24x7",
            support_contact="support@example.invalid",
        )


def test_third_party_support_does_not_replace_manufacturer_support() -> None:
    warranty = ManufacturerWarranty.create(
        manufacturer="HPE",
        warranty_reference="hpe-war-01",
        warranty_level="Foundation Care",
        warranty_start=date(2026, 1, 1),
        warranty_end=date(2029, 1, 1),
        support_reference="hpe-sup-01",
        support_level="NBD",
        support_contact="hpe-support@example.invalid",
    )
    profile = PhysicalAssetSupportProfile.create(
        tenant_id=TenantId.from_value("default"),
        asset_tag="srv-001",
        manufacturer_warranty=warranty,
        actor="pytest",
    )
    contract = ThirdPartySupportContract.create(
        provider="MaintCo",
        contract_reference="maint-001",
        support_level="24x7 onsite",
        support_start=date(2026, 2, 1),
        support_end=date(2027, 2, 1),
        support_contact="noc@maintco.example.invalid",
    )

    updated = profile.with_third_party_contract(contract, "pytest")

    assert updated.manufacturer_warranty == warranty
    assert len(updated.third_party_contracts) == 1
    with pytest.raises(ValidationError, match="already exists"):
        updated.with_third_party_contract(contract, "pytest")
