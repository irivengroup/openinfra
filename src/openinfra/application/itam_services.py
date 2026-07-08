from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from openinfra.application.ports import AuditRepository, ItamSupportRepository, TransactionManager
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, ConflictError, NotFoundError, TenantId, ValidationError
from openinfra.domain.itam import (
    ManufacturerWarranty,
    PhysicalAssetSupportProfile,
    PhysicalAssetSupportCoverageReport,
    SoftwareLicenseComplianceReport,
    SoftwareLicenseEntitlement,
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


@dataclass(frozen=True, slots=True)
class GetAssetSupportCoverageReportCommand:
    tenant_id: str
    admin_token: str
    asset_tag: str
    as_of: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterSoftwareLicenseCommand:
    tenant_id: str
    actor: str
    admin_token: str
    product_name: str
    vendor: str
    license_reference: str
    metric: str
    purchased_quantity: int
    assigned_quantity: int
    entitlement_start: str
    entitlement_end: str
    contract_reference: str | None = None
    version: str | None = None
    status: str = "active"
    owner: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateSoftwareLicenseAssignmentCommand:
    tenant_id: str
    actor: str
    admin_token: str
    license_reference: str
    assigned_quantity: int
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class GetSoftwareLicenseCommand:
    tenant_id: str
    admin_token: str
    license_reference: str


@dataclass(frozen=True, slots=True)
class GetSoftwareLicenseComplianceCommand:
    tenant_id: str
    admin_token: str
    license_reference: str
    as_of: str | None = None


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


    def get_support_coverage_report(
        self, command: GetAssetSupportCoverageReportCommand
    ) -> PhysicalAssetSupportCoverageReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_READ)
        )
        profile = self._repository.find_support_profile(tenant_id, command.asset_tag)
        if profile is None:
            raise NotFoundError("asset support profile not found")
        as_of = (
            ItamDateParser.parse_date(command.as_of, "asset support coverage date")
            if command.as_of is not None
            else datetime.now(UTC).date()
        )
        return PhysicalAssetSupportCoverageReport.from_profile(profile, as_of)


    def register_software_license(
        self, command: RegisterSoftwareLicenseCommand
    ) -> SoftwareLicenseEntitlement:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_WRITE)
        )
        license_ = SoftwareLicenseEntitlement.create(
            tenant_id=tenant_id,
            product_name=command.product_name,
            vendor=command.vendor,
            license_reference=command.license_reference,
            metric=command.metric,
            purchased_quantity=int(command.purchased_quantity),
            assigned_quantity=int(command.assigned_quantity),
            entitlement_start=ItamDateParser.parse_date(command.entitlement_start, "software entitlement start"),
            entitlement_end=ItamDateParser.parse_date(command.entitlement_end, "software entitlement end"),
            actor=command.actor,
            contract_reference=command.contract_reference,
            version=command.version,
            status=command.status,
            owner=command.owner,
            notes=command.notes,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_software_license(tenant_id, license_.license_reference.value)
            action = "itam.software_license.update" if existing is not None else "itam.software_license.register"
            if existing is not None and existing.id != license_.id:
                license_ = SoftwareLicenseEntitlement.restore(
                    id=existing.id,
                    tenant_id=license_.tenant_id,
                    product_name=license_.product_name.value,
                    vendor=license_.vendor,
                    license_reference=license_.license_reference.value,
                    contract_reference=license_.contract_reference,
                    metric=license_.metric.value,
                    purchased_quantity=license_.purchased_quantity,
                    assigned_quantity=license_.assigned_quantity,
                    entitlement_start=license_.entitlement_start,
                    entitlement_end=license_.entitlement_end,
                    status=license_.status.value,
                    owner=license_.owner,
                    version=license_.version,
                    notes=license_.notes,
                    created_by=existing.created_by,
                    created_at=existing.created_at,
                    updated_by=command.actor,
                    updated_at=datetime.now(UTC),
                )
            self._repository.save_software_license(license_)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action=action,
                    target_type="software_license",
                    target_id=license_.license_reference.value,
                    metadata={
                        "license_reference": license_.license_reference.value,
                        "product_name": license_.product_name.value,
                        "vendor": license_.vendor,
                        "metric": license_.metric.value,
                        "purchased_quantity": license_.purchased_quantity,
                        "assigned_quantity": license_.assigned_quantity,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return license_

    def update_software_license_assignment(
        self, command: UpdateSoftwareLicenseAssignmentCommand
    ) -> SoftwareLicenseEntitlement:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_WRITE)
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_software_license(tenant_id, command.license_reference)
            if existing is None:
                raise NotFoundError("software license entitlement not found")
            updated = existing.with_assignment(
                assigned_quantity=int(command.assigned_quantity),
                actor=command.actor,
                notes=command.notes,
            )
            self._repository.save_software_license(updated)
            report = SoftwareLicenseComplianceReport.from_license(updated, datetime.now(UTC).date())
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itam.software_license.assignment.update",
                    target_type="software_license",
                    target_id=updated.license_reference.value,
                    metadata={
                        "license_reference": updated.license_reference.value,
                        "assigned_quantity": updated.assigned_quantity,
                        "available_quantity": updated.available_quantity(),
                        "compliance_state": report.compliance_state.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def get_software_license(self, command: GetSoftwareLicenseCommand) -> SoftwareLicenseEntitlement:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_READ)
        )
        license_ = self._repository.find_software_license(tenant_id, command.license_reference)
        if license_ is None:
            raise NotFoundError("software license entitlement not found")
        return license_

    def get_software_license_compliance(
        self, command: GetSoftwareLicenseComplianceCommand
    ) -> SoftwareLicenseComplianceReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_READ)
        )
        license_ = self._repository.find_software_license(tenant_id, command.license_reference)
        if license_ is None:
            raise NotFoundError("software license entitlement not found")
        as_of = (
            ItamDateParser.parse_date(command.as_of, "software license compliance date")
            if command.as_of is not None
            else datetime.now(UTC).date()
        )
        return SoftwareLicenseComplianceReport.from_license(license_, as_of)
