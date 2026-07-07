from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import Code, EntityId, LifecycleStatus, Name, TenantId, ValidationError


class SupportContractStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PLANNED = "planned"
    TERMINATED = "terminated"


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
            manufacturer=ItamValidation.normalized_text(manufacturer, "manufacturer", max_length=128),
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
            support_contact=ItamValidation.normalized_contact(support_contact, "manufacturer support contact"),
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
        normalized_notes = ItamValidation.normalized_optional_text(notes, "third-party support notes", 1024)
        return cls(
            id=id,
            provider=ItamValidation.normalized_text(provider, "third-party support provider", max_length=128),
            contract_reference=ItamValidation.normalized_code_text(
                contract_reference, "third-party support contract reference"
            ),
            support_level=ItamValidation.normalized_text(
                support_level, "third-party support level", max_length=128
            ),
            support_start=support_start,
            support_end=support_end,
            support_contact=ItamValidation.normalized_contact(support_contact, "third-party support contact"),
            status=SupportContractStatus(status.strip().lower()),
            notes=normalized_notes,
            created_at=ItamValidation.normalized_datetime(created_at, "third-party support creation date"),
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
            sorted(third_party_contracts, key=lambda item: (item.provider.lower(), item.contract_reference))
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
    def normalized_optional_text(
        value: str | None, field_name: str, max_length: int
    ) -> str | None:
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
