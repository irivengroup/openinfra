from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from openinfra.application.ports import AuditRepository, ItamSupportRepository, TransactionManager
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    TenantId,
    ValidationError,
)
from openinfra.domain.itam import (
    ItamDateParser,
    ItamOrganization,
    ItamOrganizationCatalog,
    ItamOrganizationStatus,
    ItamPartner,
    ItamPartnerCatalog,
    ItamPartnerKind,
    ItamPartnerStatus,
    ItamTenant,
    ItamTenantCatalog,
    ItamTenantStatus,
    ManufacturerWarranty,
    PhysicalAssetSupportCoverageReport,
    PhysicalAssetSupportProfile,
    SoftwareLicenseComplianceReport,
    SoftwareLicenseEntitlement,
    ThirdPartySupportContract,
)
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class CreateItamOrganizationCommand:
    organization_id: str
    actor: str
    admin_token: str
    legal_name: str
    scope_tenant_id: str = "default"
    display_name: str | None = None
    status: str = "active"
    registration_number: str = "N/A"
    tax_identifier: str = "N/A"
    country_code: str = "FR"
    city: str = "Non renseigné"
    address: str = "Non renseigné"
    contact_email: str = "contact@example.invalid"
    support_contact: str = "support@example.invalid"
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateItamOrganizationCommand:
    organization_id: str
    actor: str
    admin_token: str
    scope_tenant_id: str = "default"
    legal_name: str | None = None
    display_name: str | None = None
    status: str | None = None
    registration_number: str | None = None
    tax_identifier: str | None = None
    country_code: str | None = None
    city: str | None = None
    address: str | None = None
    contact_email: str | None = None
    support_contact: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteItamOrganizationCommand:
    organization_id: str
    actor: str
    admin_token: str
    scope_tenant_id: str = "default"


@dataclass(frozen=True, slots=True)
class GetItamOrganizationCommand:
    organization_id: str
    admin_token: str
    scope_tenant_id: str = "default"


@dataclass(frozen=True, slots=True)
class ListItamOrganizationsCommand:
    tenant_id: str
    admin_token: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class CreateItamPartnerCommand:
    organization_id: str
    partner_id: str
    kind: str
    actor: str
    admin_token: str
    legal_name: str
    scope_tenant_id: str = "default"
    display_name: str | None = None
    status: str = "active"
    registration_number: str = "N/A"
    tax_identifier: str = "N/A"
    country_code: str = "FR"
    city: str = "Non renseigné"
    address: str = "Non renseigné"
    contact_email: str = "contact@example.invalid"
    phone: str = "+33000000000"
    support_contact: str = "support@example.invalid"
    website: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateItamPartnerCommand:
    organization_id: str
    partner_id: str
    actor: str
    admin_token: str
    scope_tenant_id: str = "default"
    kind: str | None = None
    legal_name: str | None = None
    display_name: str | None = None
    status: str | None = None
    registration_number: str | None = None
    tax_identifier: str | None = None
    country_code: str | None = None
    city: str | None = None
    address: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    support_contact: str | None = None
    website: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteItamPartnerCommand:
    organization_id: str
    partner_id: str
    actor: str
    admin_token: str
    scope_tenant_id: str = "default"


@dataclass(frozen=True, slots=True)
class GetItamPartnerCommand:
    organization_id: str
    partner_id: str
    admin_token: str
    scope_tenant_id: str = "default"


@dataclass(frozen=True, slots=True)
class ListItamPartnersCommand:
    tenant_id: str
    admin_token: str
    organization_id: str | None = None
    kind: str | None = None
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class CreateItamTenantCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    scope_tenant_id: str = "default"
    organization_id: str = "default"
    status: str = "active"
    is_default: bool = False
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateItamTenantCommand:
    tenant_id: str
    actor: str
    admin_token: str
    scope_tenant_id: str = "default"
    organization_id: str | None = None
    name: str | None = None
    status: str | None = None
    is_default: bool | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteItamTenantCommand:
    tenant_id: str
    actor: str
    admin_token: str
    scope_tenant_id: str = "default"


@dataclass(frozen=True, slots=True)
class GetItamTenantCommand:
    tenant_id: str
    admin_token: str


@dataclass(frozen=True, slots=True)
class ListItamTenantsCommand:
    tenant_id: str
    admin_token: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class RegisterManufacturerSupportCommand:
    tenant_id: str
    actor: str
    admin_token: str
    asset_tag: str
    manufacturer: str
    manufacturer_partner_id: str
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
    provider_partner_id: str
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
    vendor_partner_id: str
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

    def create_organization(self, command: CreateItamOrganizationCommand) -> ItamOrganization:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        organization = ItamOrganization.create(
            organization_id=command.organization_id,
            legal_name=command.legal_name,
            display_name=command.display_name,
            actor=command.actor,
            status=command.status,
            registration_number=command.registration_number,
            tax_identifier=command.tax_identifier,
            country_code=command.country_code,
            city=command.city,
            address=command.address,
            contact_email=command.contact_email,
            support_contact=command.support_contact,
            description=command.description,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_organization(organization.id.value)
            if existing is not None and existing.status != ItamOrganizationStatus.RETIRED:
                raise ConflictError("ITAM organization already exists")
            self._repository.save_organization(organization)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=scope_tenant_id,
                    actor=principal.subject,
                    action="itam.organization.create",
                    target_type="itam_organization",
                    target_id=organization.id.value,
                    metadata={
                        "organization_id": organization.id.value,
                        "legal_name": organization.legal_name.value,
                        "status": organization.status.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return organization

    def update_organization(self, command: UpdateItamOrganizationCommand) -> ItamOrganization:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_organization(command.organization_id)
            if existing is None:
                raise NotFoundError("ITAM organization not found")
            updated = existing.update(
                actor=command.actor,
                legal_name=command.legal_name,
                display_name=command.display_name,
                status=command.status,
                registration_number=command.registration_number,
                tax_identifier=command.tax_identifier,
                country_code=command.country_code,
                city=command.city,
                address=command.address,
                contact_email=command.contact_email,
                support_contact=command.support_contact,
                description=command.description,
            )
            self._repository.save_organization(updated)
            if updated.status == ItamOrganizationStatus.RETIRED:
                self._retire_organization_tenants(updated.id.value, command.actor)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=scope_tenant_id,
                    actor=principal.subject,
                    action="itam.organization.update",
                    target_type="itam_organization",
                    target_id=updated.id.value,
                    metadata={
                        "organization_id": updated.id.value,
                        "legal_name": updated.legal_name.value,
                        "status": updated.status.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def delete_organization(self, command: DeleteItamOrganizationCommand) -> ItamOrganization:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_organization(command.organization_id)
            if existing is None:
                raise NotFoundError("ITAM organization not found")
            retired = existing.retire(command.actor)
            self._repository.save_organization(retired)
            self._retire_organization_tenants(retired.id.value, command.actor)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=scope_tenant_id,
                    actor=principal.subject,
                    action="itam.organization.retire",
                    target_type="itam_organization",
                    target_id=retired.id.value,
                    metadata={
                        "organization_id": retired.id.value,
                        "legal_name": retired.legal_name.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return retired

    def get_organization(self, command: GetItamOrganizationCommand) -> ItamOrganization:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_READ
            )
        )
        organization = self._repository.find_organization(command.organization_id)
        if organization is None:
            raise NotFoundError("ITAM organization not found")
        return organization

    def list_organizations(self, command: ListItamOrganizationsCommand) -> ItamOrganizationCatalog:
        scope_tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_READ
            )
        )
        organizations = self._repository.list_organizations(command.include_retired)
        return ItamOrganizationCatalog.from_items(organizations)

    def create_partner(self, command: CreateItamPartnerCommand) -> ItamPartner:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        organization = self._require_active_organization(command.organization_id)
        partner = ItamPartner.create(
            partner_id=command.partner_id,
            organization_id=organization.id,
            kind=command.kind,
            legal_name=command.legal_name,
            actor=command.actor,
            display_name=command.display_name,
            status=command.status,
            registration_number=command.registration_number,
            tax_identifier=command.tax_identifier,
            country_code=command.country_code,
            city=command.city,
            address=command.address,
            contact_email=command.contact_email,
            phone=command.phone,
            support_contact=command.support_contact,
            website=command.website,
            description=command.description,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_partner(organization.id.value, partner.id.value)
            if existing is not None and existing.status != ItamPartnerStatus.RETIRED:
                raise ConflictError("ITAM partner already exists for this organization")
            self._repository.save_partner(partner)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=scope_tenant_id,
                    actor=principal.subject,
                    action="itam.partner.create",
                    target_type="itam_partner",
                    target_id=f"{partner.organization_id.value}:{partner.id.value}",
                    metadata={
                        "organization_id": partner.organization_id.value,
                        "partner_id": partner.id.value,
                        "kind": partner.kind.value,
                        "status": partner.status.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return partner

    def update_partner(self, command: UpdateItamPartnerCommand) -> ItamPartner:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        organization = self._require_active_organization(command.organization_id)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_partner(organization.id.value, command.partner_id)
            if existing is None:
                raise NotFoundError("ITAM partner not found")
            updated = existing.update(
                actor=command.actor,
                kind=command.kind,
                legal_name=command.legal_name,
                display_name=command.display_name,
                status=command.status,
                registration_number=command.registration_number,
                tax_identifier=command.tax_identifier,
                country_code=command.country_code,
                city=command.city,
                address=command.address,
                contact_email=command.contact_email,
                phone=command.phone,
                support_contact=command.support_contact,
                website=command.website,
                description=command.description,
            )
            self._repository.save_partner(updated)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=scope_tenant_id,
                    actor=principal.subject,
                    action="itam.partner.update",
                    target_type="itam_partner",
                    target_id=f"{updated.organization_id.value}:{updated.id.value}",
                    metadata={
                        "organization_id": updated.organization_id.value,
                        "partner_id": updated.id.value,
                        "kind": updated.kind.value,
                        "status": updated.status.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def delete_partner(self, command: DeleteItamPartnerCommand) -> ItamPartner:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        organization = self._require_active_organization(command.organization_id)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_partner(organization.id.value, command.partner_id)
            if existing is None:
                raise NotFoundError("ITAM partner not found")
            retired = existing.retire(command.actor)
            self._repository.save_partner(retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=scope_tenant_id,
                    actor=principal.subject,
                    action="itam.partner.retire",
                    target_type="itam_partner",
                    target_id=f"{retired.organization_id.value}:{retired.id.value}",
                    metadata={
                        "organization_id": retired.organization_id.value,
                        "partner_id": retired.id.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return retired

    def get_partner(self, command: GetItamPartnerCommand) -> ItamPartner:
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_READ
            )
        )
        partner = self._repository.find_partner(command.organization_id, command.partner_id)
        if partner is None:
            raise NotFoundError("ITAM partner not found")
        return partner

    def list_partners(self, command: ListItamPartnersCommand) -> ItamPartnerCatalog:
        scope_tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_READ
            )
        )
        if command.organization_id is not None:
            self._require_active_organization(command.organization_id)
        partners = self._repository.list_partners(command.organization_id, command.include_retired)
        if command.kind is not None:
            try:
                kind = ItamPartnerKind(command.kind.strip().lower())
            except ValueError as exc:
                raise ValidationError("unsupported ITAM partner kind") from exc
            partners = tuple(item for item in partners if item.kind == kind)
        return ItamPartnerCatalog.from_items(partners)

    def _require_active_partner(
        self, organization_id: str, partner_id: str, expected_kind: ItamPartnerKind
    ) -> ItamPartner:
        organization = self._require_active_organization(organization_id)
        partner = self._repository.find_partner(organization.id.value, partner_id)
        if partner is None or not partner.supports_kind(expected_kind):
            raise ValidationError(
                f"an active accredited ITAM partner of kind {expected_kind.value} is required"
            )
        return partner

    def _organization_for_tenant(self, tenant_id: TenantId) -> ItamOrganization:
        tenant = self._require_active_tenant(tenant_id)
        return self._require_active_organization(tenant.organization_id.value)

    def _ensure_default_organization(self) -> ItamOrganization:
        existing = self._repository.find_organization("default")
        if existing is not None:
            return existing
        organization = ItamOrganization.create(
            organization_id="default",
            legal_name="Default Organization",
            display_name="Default",
            actor="system",
            registration_number="N/A",
            tax_identifier="N/A",
            country_code="FR",
            city="Non renseigné",
            address="Non renseigné",
            contact_email="contact@example.invalid",
            support_contact="support@example.invalid",
            description="Compatibility organization for single-tenant installations.",
        )
        self._repository.save_organization(organization)
        return organization

    def _require_active_organization(self, organization_id: str) -> ItamOrganization:
        if organization_id == "default":
            return self._ensure_default_organization()
        organization = self._repository.find_organization(organization_id)
        if organization is None or not organization.selectable():
            raise ValidationError("an active ITAM organization is required")
        return organization

    def _materialize_implicit_tenant_for_organization(
        self, tenant_id: TenantId
    ) -> ItamTenant | None:
        organization = self._repository.find_organization(tenant_id.value)
        if organization is None or not organization.selectable():
            return None
        tenant = ItamTenant.create(
            tenant_id=tenant_id,
            organization_id=organization.id,
            name=organization.display_name.value,
            actor="system",
            description="Implicit ITAM tenant materialized from its organization.",
        )
        self._repository.save_tenant(tenant)
        return tenant

    def _require_active_tenant(self, tenant_id: TenantId) -> ItamTenant:
        if tenant_id.value == "default":
            self._ensure_default_organization()
        tenant = self._repository.find_tenant(tenant_id)
        if tenant is None:
            tenant = self._materialize_implicit_tenant_for_organization(tenant_id)
        if tenant is None or not tenant.selectable():
            raise ValidationError(
                "an active ITAM tenant attached to an active organization is required"
            )
        organization = self._require_active_organization(tenant.organization_id.value)
        if organization.id != tenant.organization_id:
            raise ValidationError("ITAM tenant organization reference is inconsistent")
        return tenant

    def _retire_organization_tenants(self, organization_id: str, actor: str) -> None:
        for tenant in self._repository.list_tenants(include_retired=True):
            if (
                tenant.organization_id.value == organization_id
                and tenant.status != ItamTenantStatus.RETIRED
            ):
                self._repository.save_tenant(tenant.retire(actor))

    def create_tenant(self, command: CreateItamTenantCommand) -> ItamTenant:
        tenant_id = TenantId.from_value(command.tenant_id)
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        organization = self._require_active_organization(command.organization_id)
        tenant = ItamTenant.create(
            tenant_id=tenant_id,
            organization_id=organization.id,
            name=command.name,
            actor=command.actor,
            status=command.status,
            is_default=command.is_default,
            description=command.description,
        )
        if tenant.is_default and not tenant.selectable():
            raise ValidationError("only an active ITAM tenant can be the default")
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_tenant(tenant.id)
            if existing is not None and existing.status != ItamTenantStatus.RETIRED:
                raise ConflictError("ITAM tenant already exists")
            if tenant.is_default:
                self._repository.clear_default_tenant(except_tenant_id=tenant.id)
            self._repository.save_tenant(tenant)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant.id,
                    actor=principal.subject,
                    action="itam.tenant.create",
                    target_type="itam_tenant",
                    target_id=tenant.id.value,
                    metadata={
                        "tenant_id": tenant.id.value,
                        "organization_id": tenant.organization_id.value,
                        "name": tenant.name.value,
                        "status": tenant.status.value,
                        "is_default": tenant.is_default,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return tenant

    def update_tenant(self, command: UpdateItamTenantCommand) -> ItamTenant:
        tenant_id = TenantId.from_value(command.tenant_id)
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_tenant(tenant_id)
            if existing is None:
                raise NotFoundError("ITAM tenant not found")
            organization_id = existing.organization_id
            if command.organization_id is not None:
                organization_id = self._require_active_organization(command.organization_id).id
            updated = ItamTenant.restore(
                tenant_id=existing.id,
                organization_id=organization_id,
                name=existing.name.value if command.name is None else command.name,
                status=existing.status.value if command.status is None else command.status,
                is_default=existing.is_default
                if command.is_default is None
                else command.is_default,
                description=existing.description
                if command.description is None
                else command.description,
                created_by=existing.created_by,
                created_at=existing.created_at,
                updated_by=command.actor,
                updated_at=datetime.now(UTC),
            )
            if updated.is_default and not updated.selectable():
                raise ValidationError("only an active ITAM tenant can be the default")
            if updated.is_default:
                self._repository.clear_default_tenant(except_tenant_id=updated.id)
            self._repository.save_tenant(updated)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itam.tenant.update",
                    target_type="itam_tenant",
                    target_id=updated.id.value,
                    metadata={
                        "tenant_id": updated.id.value,
                        "organization_id": updated.organization_id.value,
                        "name": updated.name.value,
                        "status": updated.status.value,
                        "is_default": updated.is_default,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def delete_tenant(self, command: DeleteItamTenantCommand) -> ItamTenant:
        tenant_id = TenantId.from_value(command.tenant_id)
        scope_tenant_id = TenantId.from_value(command.scope_tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_WRITE
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_tenant(tenant_id)
            if existing is None:
                raise NotFoundError("ITAM tenant not found")
            retired = existing.retire(command.actor)
            self._repository.save_tenant(retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itam.tenant.retire",
                    target_type="itam_tenant",
                    target_id=retired.id.value,
                    metadata={
                        "tenant_id": retired.id.value,
                        "name": retired.name.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return retired

    def get_tenant(self, command: GetItamTenantCommand) -> ItamTenant:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_READ)
        )
        tenant = self._repository.find_tenant(tenant_id)
        if tenant is None:
            raise NotFoundError("ITAM tenant not found")
        return tenant

    def list_tenants(self, command: ListItamTenantsCommand) -> ItamTenantCatalog:
        scope_tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                scope_tenant_id.value, command.admin_token, Permission.ITAM_READ
            )
        )
        self._ensure_default_organization()
        tenants = self._repository.list_tenants(command.include_retired)
        return ItamTenantCatalog.from_items(tenants)

    def register_manufacturer_support(
        self, command: RegisterManufacturerSupportCommand
    ) -> PhysicalAssetSupportProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_WRITE)
        )
        organization = self._organization_for_tenant(tenant_id)
        manufacturer_partner = self._require_active_partner(
            organization.id.value, command.manufacturer_partner_id, ItamPartnerKind.MANUFACTURER
        )
        warranty = ManufacturerWarranty.create(
            manufacturer=manufacturer_partner.display_name.value,
            manufacturer_partner_id=manufacturer_partner.id.value,
            warranty_reference=command.warranty_reference,
            warranty_level=command.warranty_level,
            warranty_start=ItamDateParser.parse_date(
                command.warranty_start, "manufacturer warranty start"
            ),
            warranty_end=ItamDateParser.parse_date(
                command.warranty_end, "manufacturer warranty end"
            ),
            support_reference=command.support_reference,
            support_level=command.support_level,
            support_contact=command.support_contact,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_support_profile(tenant_id, command.asset_tag)
            if existing is not None:
                if existing.manufacturer_warranty != warranty:
                    raise ConflictError(
                        "manufacturer warranty/support is immutable; "
                        "add third-party support separately"
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
        organization = self._organization_for_tenant(tenant_id)
        provider_partner = self._require_active_partner(
            organization.id.value, command.provider_partner_id, ItamPartnerKind.THIRD_PARTY_SUPPORT
        )
        contract = ThirdPartySupportContract.create(
            provider=provider_partner.display_name.value,
            provider_partner_id=provider_partner.id.value,
            contract_reference=command.contract_reference,
            support_level=command.support_level,
            support_start=ItamDateParser.parse_date(
                command.support_start, "third-party support start"
            ),
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
                        "manufacturer_support_reference": (
                            profile.manufacturer_warranty.support_reference
                        ),
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
        self._require_active_tenant(tenant_id)
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
        self._require_active_tenant(tenant_id)
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
        organization = self._organization_for_tenant(tenant_id)
        vendor_partner = self._require_active_partner(
            organization.id.value, command.vendor_partner_id, ItamPartnerKind.SOFTWARE_PUBLISHER
        )
        license_ = SoftwareLicenseEntitlement.create(
            tenant_id=tenant_id,
            product_name=command.product_name,
            vendor=vendor_partner.display_name.value,
            vendor_partner_id=vendor_partner.id.value,
            license_reference=command.license_reference,
            metric=command.metric,
            purchased_quantity=int(command.purchased_quantity),
            assigned_quantity=int(command.assigned_quantity),
            entitlement_start=ItamDateParser.parse_date(
                command.entitlement_start, "software entitlement start"
            ),
            entitlement_end=ItamDateParser.parse_date(
                command.entitlement_end, "software entitlement end"
            ),
            actor=command.actor,
            contract_reference=command.contract_reference,
            version=command.version,
            status=command.status,
            owner=command.owner,
            notes=command.notes,
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_software_license(
                tenant_id, license_.license_reference.value
            )
            action = (
                "itam.software_license.update"
                if existing is not None
                else "itam.software_license.register"
            )
            if existing is not None and existing.id != license_.id:
                license_ = SoftwareLicenseEntitlement.restore(
                    id=existing.id,
                    tenant_id=license_.tenant_id,
                    product_name=license_.product_name.value,
                    vendor=license_.vendor,
                    vendor_partner_id=license_.vendor_partner_id,
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
            self._require_active_tenant(tenant_id)
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

    def get_software_license(
        self, command: GetSoftwareLicenseCommand
    ) -> SoftwareLicenseEntitlement:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITAM_READ)
        )
        self._require_active_tenant(tenant_id)
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
        self._require_active_tenant(tenant_id)
        license_ = self._repository.find_software_license(tenant_id, command.license_reference)
        if license_ is None:
            raise NotFoundError("software license entitlement not found")
        as_of = (
            ItamDateParser.parse_date(command.as_of, "software license compliance date")
            if command.as_of is not None
            else datetime.now(UTC).date()
        )
        return SoftwareLicenseComplianceReport.from_license(license_, as_of)
