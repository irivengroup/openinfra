from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Self

from openinfra.domain.common import Code, EntityId, LifecycleStatus, Name, TenantId, ValidationError


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
