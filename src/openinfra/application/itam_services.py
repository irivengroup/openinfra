from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.ports import AuditRepository, ItamSupportRepository, TransactionManager
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, ConflictError, NotFoundError, TenantId, ValidationError
from openinfra.domain.itam import (
    ManufacturerWarranty,
    PhysicalAssetSupportProfile,
    ThirdPartySupportContract,
    ItamDateParser,
)
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class RegisterManufacturerSupportCommand:
    tenant_id: str
    actor: str
    admin_token: str
    asset_tag: str
    manufacturer: str
    warranty_reference: str
    warranty_level: str
    warranty_start: str
    warranty_end: str
    support_reference: str
    support_level: str
    support_contact: str


@dataclass(frozen=True, slots=True)
class AddThirdPartySupportCommand:
    tenant_id: str
    actor: str
    admin_token: str
    asset_tag: str
    provider: str
    contract_reference: str
    support_level: str
    support_start: str
    support_end: str
    support_contact: str
    status: str = "active"
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class GetAssetSupportProfileCommand:
    tenant_id: str
    admin_token: str
    asset_tag: str


class ItamSupportService:
    def __init__(
        self,
        repository: ItamSupportRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def register_manufacturer_support(
        self, command: RegisterManufacturerSupportCommand
    ) -> PhysicalAssetSupportProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_WRITE)
        )
        warranty = ManufacturerWarranty.create(
            manufacturer=command.manufacturer,
            warranty_reference=command.warranty_reference,
            warranty_level=command.warranty_level,
            warranty_start=ItamDateParser.parse_date(command.warranty_start, "manufacturer warranty start"),
            warranty_end=ItamDateParser.parse_date(command.warranty_end, "manufacturer warranty end"),
            support_reference=command.support_reference,
            support_level=command.support_level,
            support_contact=command.support_contact,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_support_profile(tenant_id, command.asset_tag)
            if existing is not None:
                if existing.manufacturer_warranty != warranty:
                    raise ConflictError(
                        "manufacturer warranty/support is immutable; add third-party support separately"
                    )
                profile = existing
                action = "itam.support.manufacturer.confirm"
            else:
                profile = PhysicalAssetSupportProfile.create(
                    tenant_id=tenant_id,
                    asset_tag=command.asset_tag,
                    manufacturer_warranty=warranty,
                    actor=command.actor,
                )
                self._repository.save_support_profile(profile)
                action = "itam.support.manufacturer.register"
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action=action,
                    target_type="asset_support_profile",
                    target_id=profile.asset_tag.value,
                    metadata={
                        "asset_tag": profile.asset_tag.value,
                        "manufacturer": profile.manufacturer_warranty.manufacturer,
                        "warranty_reference": profile.manufacturer_warranty.warranty_reference,
                        "support_reference": profile.manufacturer_warranty.support_reference,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return profile

    def add_third_party_support(
        self, command: AddThirdPartySupportCommand
    ) -> PhysicalAssetSupportProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_WRITE)
        )
        contract = ThirdPartySupportContract.create(
            provider=command.provider,
            contract_reference=command.contract_reference,
            support_level=command.support_level,
            support_start=ItamDateParser.parse_date(command.support_start, "third-party support start"),
            support_end=ItamDateParser.parse_date(command.support_end, "third-party support end"),
            support_contact=command.support_contact,
            status=command.status,
            notes=command.notes,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_support_profile(tenant_id, command.asset_tag)
            if existing is None:
                raise NotFoundError(
                    "manufacturer warranty/support must be registered before third-party support"
                )
            profile = existing.with_third_party_contract(contract, command.actor)
            if profile.manufacturer_warranty != existing.manufacturer_warranty:
                raise ValidationError("third-party support cannot modify manufacturer support")
            self._repository.save_support_profile(profile)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itam.support.third_party.add",
                    target_type="asset_support_profile",
                    target_id=profile.asset_tag.value,
                    metadata={
                        "asset_tag": profile.asset_tag.value,
                        "provider": contract.provider,
                        "contract_reference": contract.contract_reference,
                        "manufacturer_support_reference": profile.manufacturer_warranty.support_reference,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return profile

    def get_support_profile(
        self, command: GetAssetSupportProfileCommand
    ) -> PhysicalAssetSupportProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_READ)
        )
        profile = self._repository.find_support_profile(tenant_id, command.asset_tag)
        if profile is None:
            raise NotFoundError("asset support profile not found")
        return profile
