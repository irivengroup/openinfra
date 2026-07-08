from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import (
    Code,
    EntityId,
    LifecycleStatus,
    Name,
    TenantId,
    ValidationError,
)


class SupportContractStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PLANNED = "planned"
    TERMINATED = "terminated"


class WarrantyCoverageStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PLANNED = "planned"


class AssetCoverageState(StrEnum):
    MANUFACTURER_ACTIVE = "manufacturer_active"
    MANUFACTURER_PLANNED = "manufacturer_planned"
    THIRD_PARTY_ONLY = "third_party_only"
    EXPIRED = "expired"


class SoftwareLicenseMetric(StrEnum):
    DEVICE = "device"
    USER = "user"
    CORE = "core"
    SOCKET = "socket"
    INSTANCE = "instance"
    SUBSCRIPTION = "subscription"


class SoftwareLicenseStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PLANNED = "planned"
    TERMINATED = "terminated"


class SoftwareLicenseComplianceState(StrEnum):
    COMPLIANT = "compliant"
    OVER_ASSIGNED = "over_assigned"
    EXPIRED = "expired"
    PLANNED = "planned"


class ItamOrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class ItamOrganization:
    id: TenantId
    legal_name: Name
    display_name: Name
    status: ItamOrganizationStatus
    registration_number: str
    tax_identifier: str
    country_code: str
    city: str
    address: str
    contact_email: str
    support_contact: str
    description: str | None
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        organization_id: str | TenantId,
        legal_name: str,
        actor: str,
        display_name: str | None = None,
        status: str = "active",
        registration_number: str = "N/A",
        tax_identifier: str = "N/A",
        country_code: str = "FR",
        city: str = "Non renseigné",
        address: str = "Non renseigné",
        contact_email: str = "contact@example.invalid",
        support_contact: str = "support@example.invalid",
        description: str | None = None,
    ) -> Self:
        identifier = (
            organization_id
            if isinstance(organization_id, TenantId)
            else TenantId.from_value(organization_id)
        )
        now = datetime.now(UTC)
        return cls.restore(
            organization_id=identifier,
            legal_name=legal_name,
            display_name=display_name or legal_name,
            status=status,
            registration_number=registration_number,
            tax_identifier=tax_identifier,
            country_code=country_code,
            city=city,
            address=address,
            contact_email=contact_email,
            support_contact=support_contact,
            description=description,
            created_by=actor,
            created_at=now,
            updated_by=actor,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        organization_id: str | TenantId,
        legal_name: str,
        display_name: str,
        status: str,
        registration_number: str,
        tax_identifier: str,
        country_code: str,
        city: str,
        address: str,
        contact_email: str,
        support_contact: str,
        description: str | None,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
    ) -> Self:
        identifier = (
            organization_id
            if isinstance(organization_id, TenantId)
            else TenantId.from_value(organization_id)
        )
        try:
            status_value = ItamOrganizationStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError(
                "ITAM organization status must be active, suspended or retired"
            ) from exc
        normalized_country = country_code.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", normalized_country):
            raise ValidationError(
                "ITAM organization country code must use ISO 3166-1 alpha-2 format"
            )
        return cls(
            id=identifier,
            legal_name=Name.from_value(legal_name, "ITAM organization legal name"),
            display_name=Name.from_value(display_name, "ITAM organization display name"),
            status=status_value,
            registration_number=ItamValidation.normalized_required_text(
                registration_number, "ITAM organization registration number", 128
            ),
            tax_identifier=ItamValidation.normalized_required_text(
                tax_identifier, "ITAM organization tax identifier", 128
            ),
            country_code=normalized_country,
            city=ItamValidation.normalized_required_text(city, "ITAM organization city", 128),
            address=ItamValidation.normalized_required_text(
                address, "ITAM organization address", 512
            ),
            contact_email=ItamValidation.normalized_email(
                contact_email, "ITAM organization contact email"
            ),
            support_contact=ItamValidation.normalized_required_text(
                support_contact, "ITAM organization support contact", 255
            ),
            description=ItamValidation.normalized_optional_text(
                description, "ITAM organization description", 1024
            ),
            created_by=ItamValidation.normalized_actor(created_by),
            created_at=ItamValidation.normalized_datetime(
                created_at, "ITAM organization creation date"
            ),
            updated_by=ItamValidation.normalized_actor(updated_by),
            updated_at=ItamValidation.normalized_datetime(
                updated_at, "ITAM organization update date"
            ),
        )

    def update(
        self,
        *,
        actor: str,
        legal_name: str | None = None,
        display_name: str | None = None,
        status: str | None = None,
        registration_number: str | None = None,
        tax_identifier: str | None = None,
        country_code: str | None = None,
        city: str | None = None,
        address: str | None = None,
        contact_email: str | None = None,
        support_contact: str | None = None,
        description: str | None = None,
    ) -> Self:
        return self.restore(
            organization_id=self.id,
            legal_name=self.legal_name.value if legal_name is None else legal_name,
            display_name=self.display_name.value if display_name is None else display_name,
            status=self.status.value if status is None else status,
            registration_number=(
                self.registration_number if registration_number is None else registration_number
            ),
            tax_identifier=self.tax_identifier if tax_identifier is None else tax_identifier,
            country_code=self.country_code if country_code is None else country_code,
            city=self.city if city is None else city,
            address=self.address if address is None else address,
            contact_email=self.contact_email if contact_email is None else contact_email,
            support_contact=self.support_contact if support_contact is None else support_contact,
            description=self.description if description is None else description,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def retire(self, actor: str) -> Self:
        return self.update(actor=actor, status=ItamOrganizationStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status == ItamOrganizationStatus.ACTIVE

    def as_dict(self) -> dict[str, object]:
        return {
            "organization_id": self.id.value,
            "legal_name": self.legal_name.value,
            "display_name": self.display_name.value,
            "status": self.status.value,
            "registration_number": self.registration_number,
            "tax_identifier": self.tax_identifier,
            "country_code": self.country_code,
            "city": self.city,
            "address": self.address,
            "contact_email": self.contact_email,
            "support_contact": self.support_contact,
            "description": self.description,
            "selectable": self.selectable(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ItamOrganizationCatalog:
    items: tuple[ItamOrganization, ...]
    default_organization_id: str | None
    auto_selected_organization_id: str | None

    @classmethod
    def from_items(cls, items: tuple[ItamOrganization, ...]) -> Self:
        active = tuple(item for item in items if item.selectable())
        auto_selected = active[0].id.value if len(active) == 1 else None
        default = "default" if any(item.id.value == "default" for item in active) else auto_selected
        return cls(
            items=items,
            default_organization_id=default,
            auto_selected_organization_id=auto_selected,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "default_organization_id": self.default_organization_id,
            "auto_selected_organization_id": self.auto_selected_organization_id,
        }


class ItamTenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class ItamTenant:
    id: TenantId
    organization_id: TenantId
    name: Name
    status: ItamTenantStatus
    is_default: bool
    description: str | None
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: str | TenantId,
        name: str,
        actor: str,
        organization_id: str | TenantId = "default",
        status: str = "active",
        is_default: bool = False,
        description: str | None = None,
    ) -> Self:
        identifier = (
            tenant_id if isinstance(tenant_id, TenantId) else TenantId.from_value(tenant_id)
        )
        now = datetime.now(UTC)
        return cls.restore(
            tenant_id=identifier,
            organization_id=organization_id,
            name=name,
            status=status,
            is_default=is_default,
            description=description,
            created_by=actor,
            created_at=now,
            updated_by=actor,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        tenant_id: str | TenantId,
        name: str,
        status: str,
        is_default: bool,
        description: str | None,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
        organization_id: str | TenantId = "default",
    ) -> Self:
        identifier = (
            tenant_id if isinstance(tenant_id, TenantId) else TenantId.from_value(tenant_id)
        )
        organization_identifier = (
            organization_id
            if isinstance(organization_id, TenantId)
            else TenantId.from_value(organization_id)
        )
        try:
            status_value = ItamTenantStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError(
                "ITAM tenant status must be active, suspended or retired"
            ) from exc
        return cls(
            id=identifier,
            organization_id=organization_identifier,
            name=Name.from_value(name, "ITAM tenant name"),
            status=status_value,
            is_default=bool(is_default),
            description=ItamValidation.normalized_optional_text(
                description, "ITAM tenant description", 1024
            ),
            created_by=ItamValidation.normalized_actor(created_by),
            created_at=ItamValidation.normalized_datetime(created_at, "ITAM tenant creation date"),
            updated_by=ItamValidation.normalized_actor(updated_by),
            updated_at=ItamValidation.normalized_datetime(updated_at, "ITAM tenant update date"),
        )

    def update(
        self,
        *,
        actor: str,
        name: str | None = None,
        status: str | None = None,
        is_default: bool | None = None,
        description: str | None = None,
    ) -> Self:
        return self.restore(
            tenant_id=self.id,
            organization_id=self.organization_id,
            name=self.name.value if name is None else name,
            status=self.status.value if status is None else status,
            is_default=self.is_default if is_default is None else is_default,
            description=self.description if description is None else description,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def retire(self, actor: str) -> Self:
        return self.update(actor=actor, status=ItamTenantStatus.RETIRED.value, is_default=False)

    def selectable(self) -> bool:
        return self.status == ItamTenantStatus.ACTIVE

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.id.value,
            "organization_id": self.organization_id.value,
            "name": self.name.value,
            "status": self.status.value,
            "is_default": self.is_default,
            "description": self.description,
            "selectable": self.selectable(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ItamTenantCatalog:
    items: tuple[ItamTenant, ...]
    default_tenant_id: str | None
    auto_selected_tenant_id: str | None

    @classmethod
    def from_items(cls, items: tuple[ItamTenant, ...]) -> Self:
        active = tuple(item for item in items if item.selectable())
        explicit_default = next((item.id.value for item in active if item.is_default), None)
        auto_selected = active[0].id.value if len(active) == 1 else None
        return cls(
            items=items,
            default_tenant_id=explicit_default or auto_selected,
            auto_selected_tenant_id=auto_selected,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "default_tenant_id": self.default_tenant_id,
            "auto_selected_tenant_id": self.auto_selected_tenant_id,
        }


@dataclass(frozen=True, slots=True)
class Asset:
    id: EntityId
    tenant_id: TenantId
    asset_tag: Code
    name: Name
    lifecycle_status: LifecycleStatus
    owner: str | None
    purchase_date: date | None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        asset_tag: str,
        name: str,
        lifecycle_status: LifecycleStatus = LifecycleStatus.PLANNED,
        owner: str | None = None,
        purchase_date: date | None = None,
    ) -> Self:
        normalized_owner = " ".join(owner.strip().split()) if owner else None
        if normalized_owner == "":
            raise ValidationError("asset owner cannot be blank")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            asset_tag=Code.from_value(asset_tag, "asset tag"),
            name=Name.from_value(name, "asset name"),
            lifecycle_status=lifecycle_status,
            owner=normalized_owner,
            purchase_date=purchase_date,
        )


@dataclass(frozen=True, slots=True)
class ManufacturerWarranty:
    manufacturer: str
    warranty_reference: str
    warranty_level: str
    warranty_start: date
    warranty_end: date
    support_reference: str
    support_level: str
    support_contact: str

    @classmethod
    def create(
        cls,
        manufacturer: str,
        warranty_reference: str,
        warranty_level: str,
        warranty_start: date,
        warranty_end: date,
        support_reference: str,
        support_level: str,
        support_contact: str,
    ) -> Self:
        if warranty_end < warranty_start:
            raise ValidationError("manufacturer warranty end date cannot be before start date")
        return cls(
            manufacturer=ItamValidation.normalized_text(
                manufacturer, "manufacturer", max_length=128
            ),
            warranty_reference=ItamValidation.normalized_code_text(
                warranty_reference, "manufacturer warranty reference"
            ),
            warranty_level=ItamValidation.normalized_text(
                warranty_level, "manufacturer warranty level", max_length=128
            ),
            warranty_start=warranty_start,
            warranty_end=warranty_end,
            support_reference=ItamValidation.normalized_code_text(
                support_reference, "manufacturer support reference"
            ),
            support_level=ItamValidation.normalized_text(
                support_level, "manufacturer support level", max_length=128
            ),
            support_contact=ItamValidation.normalized_contact(
                support_contact, "manufacturer support contact"
            ),
        )

    @classmethod
    def restore(
        cls,
        manufacturer: str,
        warranty_reference: str,
        warranty_level: str,
        warranty_start: date,
        warranty_end: date,
        support_reference: str,
        support_level: str,
        support_contact: str,
    ) -> Self:
        return cls.create(
            manufacturer=manufacturer,
            warranty_reference=warranty_reference,
            warranty_level=warranty_level,
            warranty_start=warranty_start,
            warranty_end=warranty_end,
            support_reference=support_reference,
            support_level=support_level,
            support_contact=support_contact,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "manufacturer": self.manufacturer,
            "warranty_reference": self.warranty_reference,
            "warranty_level": self.warranty_level,
            "warranty_start": self.warranty_start.isoformat(),
            "warranty_end": self.warranty_end.isoformat(),
            "support_reference": self.support_reference,
            "support_level": self.support_level,
            "support_contact": self.support_contact,
        }


@dataclass(frozen=True, slots=True)
class ThirdPartySupportContract:
    id: EntityId
    provider: str
    contract_reference: str
    support_level: str
    support_start: date
    support_end: date
    support_contact: str
    status: SupportContractStatus
    notes: str | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        provider: str,
        contract_reference: str,
        support_level: str,
        support_start: date,
        support_end: date,
        support_contact: str,
        status: str = "active",
        notes: str | None = None,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            provider=provider,
            contract_reference=contract_reference,
            support_level=support_level,
            support_start=support_start,
            support_end=support_end,
            support_contact=support_contact,
            status=status,
            notes=notes,
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        provider: str,
        contract_reference: str,
        support_level: str,
        support_start: date,
        support_end: date,
        support_contact: str,
        status: str,
        notes: str | None,
        created_at: datetime,
    ) -> Self:
        if support_end < support_start:
            raise ValidationError("third-party support end date cannot be before start date")
        normalized_notes = ItamValidation.normalized_optional_text(
            notes, "third-party support notes", 1024
        )
        return cls(
            id=id,
            provider=ItamValidation.normalized_text(
                provider, "third-party support provider", max_length=128
            ),
            contract_reference=ItamValidation.normalized_code_text(
                contract_reference, "third-party support contract reference"
            ),
            support_level=ItamValidation.normalized_text(
                support_level, "third-party support level", max_length=128
            ),
            support_start=support_start,
            support_end=support_end,
            support_contact=ItamValidation.normalized_contact(
                support_contact, "third-party support contact"
            ),
            status=SupportContractStatus(status.strip().lower()),
            notes=normalized_notes,
            created_at=ItamValidation.normalized_datetime(
                created_at, "third-party support creation date"
            ),
        )

    def same_business_key(self, other: ThirdPartySupportContract) -> bool:
        return self.provider.lower() == other.provider.lower() and (
            self.contract_reference.upper() == other.contract_reference.upper()
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "provider": self.provider,
            "contract_reference": self.contract_reference,
            "support_level": self.support_level,
            "support_start": self.support_start.isoformat(),
            "support_end": self.support_end.isoformat(),
            "support_contact": self.support_contact,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class PhysicalAssetSupportProfile:
    id: EntityId
    tenant_id: TenantId
    asset_tag: Code
    manufacturer_warranty: ManufacturerWarranty
    third_party_contracts: tuple[ThirdPartySupportContract, ...]
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        asset_tag: str,
        manufacturer_warranty: ManufacturerWarranty,
        actor: str,
    ) -> Self:
        normalized_actor = ItamValidation.normalized_actor(actor)
        now = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            asset_tag=Code.from_value(asset_tag, "asset tag"),
            manufacturer_warranty=manufacturer_warranty,
            third_party_contracts=(),
            created_by=normalized_actor,
            created_at=now,
            updated_by=normalized_actor,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        asset_tag: str,
        manufacturer_warranty: ManufacturerWarranty,
        third_party_contracts: tuple[ThirdPartySupportContract, ...],
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
    ) -> Self:
        ordered_contracts = tuple(
            sorted(
                third_party_contracts,
                key=lambda item: (item.provider.lower(), item.contract_reference),
            )
        )
        return cls(
            id=id,
            tenant_id=tenant_id,
            asset_tag=Code.from_value(asset_tag, "asset tag"),
            manufacturer_warranty=manufacturer_warranty,
            third_party_contracts=ordered_contracts,
            created_by=ItamValidation.normalized_actor(created_by),
            created_at=ItamValidation.normalized_datetime(created_at, "profile creation date"),
            updated_by=ItamValidation.normalized_actor(updated_by),
            updated_at=ItamValidation.normalized_datetime(updated_at, "profile update date"),
        )

    def with_third_party_contract(
        self,
        contract: ThirdPartySupportContract,
        actor: str,
    ) -> PhysicalAssetSupportProfile:
        if any(existing.same_business_key(contract) for existing in self.third_party_contracts):
            raise ValidationError("third-party support contract already exists for this asset")
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            asset_tag=self.asset_tag.value,
            manufacturer_warranty=self.manufacturer_warranty,
            third_party_contracts=(*self.third_party_contracts, contract),
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "asset_tag": self.asset_tag.value,
            "manufacturer_warranty": self.manufacturer_warranty.as_dict(),
            "third_party_contracts": [item.as_dict() for item in self.third_party_contracts],
            "complete": self.is_complete(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }

    def is_complete(self) -> bool:
        return bool(
            self.manufacturer_warranty.manufacturer
            and self.manufacturer_warranty.warranty_reference
            and self.manufacturer_warranty.support_reference
            and self.manufacturer_warranty.support_contact
        )


@dataclass(frozen=True, slots=True)
class PhysicalAssetSupportCoverageReport:
    tenant_id: TenantId
    asset_tag: Code
    as_of: date
    manufacturer: str
    manufacturer_warranty_reference: str
    manufacturer_support_reference: str
    warranty_status: WarrantyCoverageStatus
    warranty_days_remaining: int
    warranty_expired: bool
    third_party_active_count: int
    third_party_planned_count: int
    third_party_expired_count: int
    coverage_state: AssetCoverageState

    @classmethod
    def from_profile(cls, profile: PhysicalAssetSupportProfile, as_of: date) -> Self:
        warranty = profile.manufacturer_warranty
        warranty_status = cls._period_status(warranty.warranty_start, warranty.warranty_end, as_of)
        active_count = 0
        planned_count = 0
        expired_count = 0
        for contract in profile.third_party_contracts:
            if (
                contract.status == SupportContractStatus.ACTIVE
                and contract.support_start <= as_of <= contract.support_end
            ):
                active_count += 1
            elif contract.status == SupportContractStatus.PLANNED or contract.support_start > as_of:
                planned_count += 1
            else:
                expired_count += 1
        if warranty_status == WarrantyCoverageStatus.ACTIVE:
            coverage_state = AssetCoverageState.MANUFACTURER_ACTIVE
        elif warranty_status == WarrantyCoverageStatus.PLANNED:
            coverage_state = AssetCoverageState.MANUFACTURER_PLANNED
        elif active_count > 0:
            coverage_state = AssetCoverageState.THIRD_PARTY_ONLY
        else:
            coverage_state = AssetCoverageState.EXPIRED
        return cls(
            tenant_id=profile.tenant_id,
            asset_tag=profile.asset_tag,
            as_of=as_of,
            manufacturer=warranty.manufacturer,
            manufacturer_warranty_reference=warranty.warranty_reference,
            manufacturer_support_reference=warranty.support_reference,
            warranty_status=warranty_status,
            warranty_days_remaining=(warranty.warranty_end - as_of).days,
            warranty_expired=warranty_status == WarrantyCoverageStatus.EXPIRED,
            third_party_active_count=active_count,
            third_party_planned_count=planned_count,
            third_party_expired_count=expired_count,
            coverage_state=coverage_state,
        )

    @staticmethod
    def _period_status(start: date, end: date, as_of: date) -> WarrantyCoverageStatus:
        if as_of < start:
            return WarrantyCoverageStatus.PLANNED
        if as_of > end:
            return WarrantyCoverageStatus.EXPIRED
        return WarrantyCoverageStatus.ACTIVE

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "asset_tag": self.asset_tag.value,
            "as_of": self.as_of.isoformat(),
            "manufacturer": self.manufacturer,
            "manufacturer_warranty_reference": self.manufacturer_warranty_reference,
            "manufacturer_support_reference": self.manufacturer_support_reference,
            "warranty_status": self.warranty_status.value,
            "warranty_days_remaining": self.warranty_days_remaining,
            "warranty_expired": self.warranty_expired,
            "third_party_active_count": self.third_party_active_count,
            "third_party_planned_count": self.third_party_planned_count,
            "third_party_expired_count": self.third_party_expired_count,
            "coverage_state": self.coverage_state.value,
        }


@dataclass(frozen=True, slots=True)
class SoftwareLicenseEntitlement:
    id: EntityId
    tenant_id: TenantId
    product_name: Name
    vendor: str
    version: str | None
    license_reference: Code
    contract_reference: str | None
    metric: SoftwareLicenseMetric
    purchased_quantity: int
    assigned_quantity: int
    entitlement_start: date
    entitlement_end: date
    status: SoftwareLicenseStatus
    owner: str | None
    notes: str | None
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        product_name: str,
        vendor: str,
        license_reference: str,
        metric: str,
        purchased_quantity: int,
        assigned_quantity: int,
        entitlement_start: date,
        entitlement_end: date,
        actor: str,
        contract_reference: str | None = None,
        version: str | None = None,
        status: str = "active",
        owner: str | None = None,
        notes: str | None = None,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            product_name=product_name,
            vendor=vendor,
            license_reference=license_reference,
            contract_reference=contract_reference,
            metric=metric,
            purchased_quantity=purchased_quantity,
            assigned_quantity=assigned_quantity,
            entitlement_start=entitlement_start,
            entitlement_end=entitlement_end,
            status=status,
            owner=owner,
            version=version,
            notes=notes,
            created_by=actor,
            created_at=datetime.now(UTC),
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        product_name: str,
        vendor: str,
        license_reference: str,
        contract_reference: str | None,
        metric: str,
        purchased_quantity: int,
        assigned_quantity: int,
        entitlement_start: date,
        entitlement_end: date,
        status: str,
        owner: str | None,
        version: str | None,
        notes: str | None,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
    ) -> Self:
        if entitlement_end < entitlement_start:
            raise ValidationError(
                "software license entitlement end date cannot be before start date"
            )
        if purchased_quantity < 1:
            raise ValidationError("software license purchased quantity must be greater than zero")
        if assigned_quantity < 0:
            raise ValidationError("software license assigned quantity cannot be negative")
        try:
            metric_value = SoftwareLicenseMetric(metric.strip().lower())
        except ValueError as exc:
            raise ValidationError("unsupported software license metric") from exc
        try:
            status_value = SoftwareLicenseStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("unsupported software license status") from exc
        return cls(
            id=id,
            tenant_id=tenant_id,
            product_name=Name.from_value(product_name, "software product name"),
            vendor=ItamValidation.normalized_text(
                vendor, "software license vendor", max_length=128
            ),
            version=ItamValidation.normalized_optional_text(version, "software version", 64),
            license_reference=Code.from_value(license_reference, "software license reference"),
            contract_reference=ItamValidation.normalized_optional_code_text(
                contract_reference, "software contract reference"
            ),
            metric=metric_value,
            purchased_quantity=purchased_quantity,
            assigned_quantity=assigned_quantity,
            entitlement_start=entitlement_start,
            entitlement_end=entitlement_end,
            status=status_value,
            owner=ItamValidation.normalized_optional_text(owner, "software license owner", 128),
            notes=ItamValidation.normalized_optional_text(notes, "software license notes", 1024),
            created_by=ItamValidation.normalized_actor(created_by),
            created_at=ItamValidation.normalized_datetime(
                created_at, "software license creation date"
            ),
            updated_by=ItamValidation.normalized_actor(updated_by),
            updated_at=ItamValidation.normalized_datetime(
                updated_at, "software license update date"
            ),
        )

    def with_assignment(
        self,
        assigned_quantity: int,
        actor: str,
        notes: str | None = None,
    ) -> SoftwareLicenseEntitlement:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            product_name=self.product_name.value,
            vendor=self.vendor,
            license_reference=self.license_reference.value,
            contract_reference=self.contract_reference,
            metric=self.metric.value,
            purchased_quantity=self.purchased_quantity,
            assigned_quantity=assigned_quantity,
            entitlement_start=self.entitlement_start,
            entitlement_end=self.entitlement_end,
            status=self.status.value,
            owner=self.owner,
            version=self.version,
            notes=self.notes if notes is None else notes,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "product_name": self.product_name.value,
            "vendor": self.vendor,
            "version": self.version,
            "license_reference": self.license_reference.value,
            "contract_reference": self.contract_reference,
            "metric": self.metric.value,
            "purchased_quantity": self.purchased_quantity,
            "assigned_quantity": self.assigned_quantity,
            "available_quantity": self.available_quantity(),
            "entitlement_start": self.entitlement_start.isoformat(),
            "entitlement_end": self.entitlement_end.isoformat(),
            "status": self.status.value,
            "owner": self.owner,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }

    def available_quantity(self) -> int:
        return self.purchased_quantity - self.assigned_quantity


@dataclass(frozen=True, slots=True)
class SoftwareLicenseComplianceReport:
    tenant_id: TenantId
    license_reference: Code
    product_name: Name
    vendor: str
    as_of: date
    metric: SoftwareLicenseMetric
    purchased_quantity: int
    assigned_quantity: int
    available_quantity: int
    utilization_percent: float
    entitlement_status: SoftwareLicenseStatus
    compliance_state: SoftwareLicenseComplianceState
    days_until_expiration: int
    contract_reference: str | None

    @classmethod
    def from_license(cls, license_: SoftwareLicenseEntitlement, as_of: date) -> Self:
        if as_of < license_.entitlement_start or license_.status == SoftwareLicenseStatus.PLANNED:
            compliance_state = SoftwareLicenseComplianceState.PLANNED
        elif as_of > license_.entitlement_end or license_.status in {
            SoftwareLicenseStatus.EXPIRED,
            SoftwareLicenseStatus.TERMINATED,
        }:
            compliance_state = SoftwareLicenseComplianceState.EXPIRED
        elif license_.assigned_quantity > license_.purchased_quantity:
            compliance_state = SoftwareLicenseComplianceState.OVER_ASSIGNED
        else:
            compliance_state = SoftwareLicenseComplianceState.COMPLIANT
        utilization = round((license_.assigned_quantity / license_.purchased_quantity) * 100, 2)
        return cls(
            tenant_id=license_.tenant_id,
            license_reference=license_.license_reference,
            product_name=license_.product_name,
            vendor=license_.vendor,
            as_of=as_of,
            metric=license_.metric,
            purchased_quantity=license_.purchased_quantity,
            assigned_quantity=license_.assigned_quantity,
            available_quantity=license_.available_quantity(),
            utilization_percent=utilization,
            entitlement_status=license_.status,
            compliance_state=compliance_state,
            days_until_expiration=(license_.entitlement_end - as_of).days,
            contract_reference=license_.contract_reference,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "license_reference": self.license_reference.value,
            "product_name": self.product_name.value,
            "vendor": self.vendor,
            "as_of": self.as_of.isoformat(),
            "metric": self.metric.value,
            "purchased_quantity": self.purchased_quantity,
            "assigned_quantity": self.assigned_quantity,
            "available_quantity": self.available_quantity,
            "utilization_percent": self.utilization_percent,
            "entitlement_status": self.entitlement_status.value,
            "compliance_state": self.compliance_state.value,
            "days_until_expiration": self.days_until_expiration,
            "contract_reference": self.contract_reference,
        }


class ItamDateParser:
    @staticmethod
    def parse_date(value: str | date, field_name: str) -> date:
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValidationError(f"{field_name} must use ISO date format YYYY-MM-DD") from exc


class ItamValidation:
    @staticmethod
    def normalized_text(value: str, field_name: str, max_length: int) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= max_length:
            raise ValidationError(f"{field_name} must contain 1 to {max_length} characters")
        return normalized

    @staticmethod
    def normalized_required_text(value: str, field_name: str, max_length: int) -> str:
        return ItamValidation.normalized_text(value, field_name, max_length)

    @staticmethod
    def normalized_email(value: str, field_name: str) -> str:
        normalized = " ".join(value.strip().split()).lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValidationError(f"{field_name} must be a valid email address")
        if len(normalized) > 255:
            raise ValidationError(f"{field_name} must contain at most 255 characters")
        return normalized

    @staticmethod
    def normalized_optional_text(value: str | None, field_name: str, max_length: int) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            return None
        if len(normalized) > max_length:
            raise ValidationError(f"{field_name} must contain at most {max_length} characters")
        return normalized

    @staticmethod
    def normalized_code_text(value: str, field_name: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:/#-]{0,127}", normalized):
            raise ValidationError(f"{field_name} must use 1 to 128 safe reference characters")
        return normalized

    @staticmethod
    def normalized_optional_code_text(value: str | None, field_name: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            return None
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:/#-]{0,127}", normalized):
            raise ValidationError(f"{field_name} must use 1 to 128 safe reference characters")
        return normalized

    @staticmethod
    def normalized_contact(value: str, field_name: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 3 <= len(normalized) <= 255:
            raise ValidationError(f"{field_name} must contain 3 to 255 characters")
        return normalized

    @staticmethod
    def normalized_actor(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValidationError("asset support actor is mandatory")
        return normalized

    @staticmethod
    def normalized_datetime(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{field_name} must be timezone-aware")
        return value.astimezone(UTC)
