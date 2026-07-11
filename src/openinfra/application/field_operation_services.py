from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.access_policy_services import AccessPolicyService
from openinfra.application.dependency_graph_services import (
    AnalyzeDependencyImpactCommand,
    AnalyzeDependencySpofCommand,
    DependencyGraphService,
)
from openinfra.application.ports import (
    AuditRepository,
    CertificateInventoryRepository,
    DcimRepository,
    FieldOperationRepository,
    FieldOperationSheetPage,
    FlowMatrixRepository,
    OfflineSyncPackagePage,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    DomainEvent,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import (
    DcimPortEndpoint,
    DcimPortOwnerType,
    Equipment,
    EquipmentLocation,
    PowerFeedSide,
    Rack,
)
from openinfra.domain.field_operations import (
    FieldEvidence,
    FieldOperationSheet,
    FieldPhysicalLocation,
    FieldSafetyWarning,
    FieldTargetType,
    InterventionLock,
    OfflineSyncPackage,
)
from openinfra.domain.flow_matrix import FlowSelectorKind
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class GenerateFieldOperationSheetCommand:
    tenant_id: str
    actor: str
    admin_token: str
    target_type: str
    target_id: str
    title: str
    purpose: str
    owner: str
    operator: str
    source_object_key: str | None = None
    site: str | None = None
    building: str | None = None
    room: str | None = None
    location_target_type: str | None = None
    location_target_id: str | None = None


@dataclass(frozen=True, slots=True)
class GetFieldOperationSheetCommand:
    tenant_id: str
    admin_token: str
    sheet_id: str


@dataclass(frozen=True, slots=True)
class ListFieldOperationSheetsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None
    target_type: str | None = None
    site: str | None = None


@dataclass(frozen=True, slots=True)
class StartFieldOperationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str


@dataclass(frozen=True, slots=True)
class RecordFieldChecklistCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str
    item_id: str
    result: str
    operator_note: str | None = None


@dataclass(frozen=True, slots=True)
class AttachFieldEvidenceCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str
    phase: str
    media_type: str
    filename: str
    content_base64: str
    caption: str


@dataclass(frozen=True, slots=True)
class ValidateFieldEvidenceCommand:
    tenant_id: str
    actor: str
    admin_token: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class CompleteFieldOperationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str


@dataclass(frozen=True, slots=True)
class CancelFieldOperationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str


@dataclass(frozen=True, slots=True)
class VerifyFieldQrCommand:
    tenant_id: str
    admin_token: str
    sheet_id: str
    payload: str


@dataclass(frozen=True, slots=True)
class AcquireInterventionLockCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str
    idempotency_key: str
    ttl_seconds: int = 3600


@dataclass(frozen=True, slots=True)
class ReleaseInterventionLockCommand:
    tenant_id: str
    actor: str
    admin_token: str
    lock_id: str


@dataclass(frozen=True, slots=True)
class CreateOfflineSyncPackageCommand:
    tenant_id: str
    actor: str
    admin_token: str
    sheet_id: str
    idempotency_key: str
    ttl_seconds: int = 86400


@dataclass(frozen=True, slots=True)
class GetOfflineSyncPackageCommand:
    tenant_id: str
    admin_token: str
    package_id: str
    include_payload: bool = True


@dataclass(frozen=True, slots=True)
class ListOfflineSyncPackagesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    sheet_id: str | None = None


@dataclass(frozen=True, slots=True)
class SynchronizeOfflinePackageCommand:
    tenant_id: str
    actor: str
    admin_token: str
    package_id: str
    payload_sha256: str


class FieldLocationResolver:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        certificate_repository: CertificateInventoryRepository,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._certificate_repository = certificate_repository

    def resolve(
        self,
        tenant_id: TenantId,
        command: GenerateFieldOperationSheetCommand,
    ) -> FieldPhysicalLocation:
        target_type = FieldTargetType.from_value(command.target_type)
        if target_type is FieldTargetType.CERTIFICATE:
            certificate = self._certificate_repository.get_certificate_by_fingerprint(
                tenant_id, command.target_id
            ) or self._certificate_repository.get_certificate(tenant_id, command.target_id)
            if certificate is None:
                raise NotFoundError("certificate does not exist")
            if not command.location_target_type or not command.location_target_id:
                raise ValidationError(
                    "certificate field operation requires a physical location target"
                )
            target_type = FieldTargetType.from_value(command.location_target_type)
            if target_type is FieldTargetType.CERTIFICATE:
                raise ValidationError("certificate cannot be used as its own physical location")
            target_id = command.location_target_id
        else:
            target_id = command.target_id
        if target_type is FieldTargetType.EQUIPMENT:
            equipment = self._dcim_repository.find_equipment(tenant_id, target_id)
            if equipment is None:
                raise NotFoundError("equipment does not exist")
            return self._from_equipment(equipment)
        if target_type is FieldTargetType.RACK:
            rack = self._rack(tenant_id, command.site, command.building, command.room, target_id)
            return self._from_rack(rack)
        if target_type is FieldTargetType.POWER_DEVICE:
            device = self._dcim_repository.find_power_device(tenant_id, target_id)
            if device is None:
                raise NotFoundError("power device does not exist")
            if device.rack_code is None:
                raise ValidationError("power device has no rack location")
            rack = self._rack(
                tenant_id,
                device.site_code.value,
                device.building_code.value,
                device.room_code.value,
                device.rack_code.value,
            )
            return self._from_rack(rack)
        if target_type is FieldTargetType.CABLE:
            cable = self._dcim_repository.find_dcim_cable(tenant_id, target_id)
            if cable is None:
                raise NotFoundError("DCIM cable does not exist")
            for endpoint in (cable.a_endpoint, cable.b_endpoint):
                location = self._from_endpoint(tenant_id, endpoint)
                if location is not None:
                    return location
            raise ValidationError("DCIM cable endpoints have no complete physical location")
        raise ValidationError("unsupported physical location target")

    def _from_endpoint(
        self, tenant_id: TenantId, endpoint: DcimPortEndpoint
    ) -> FieldPhysicalLocation | None:
        owner_type = endpoint.owner_type
        owner_code = endpoint.owner_code.value
        if owner_type is DcimPortOwnerType.EQUIPMENT:
            equipment = self._dcim_repository.find_equipment(tenant_id, owner_code)
            return None if equipment is None else self._from_equipment(equipment)
        port = self._dcim_repository.find_dcim_port(tenant_id, endpoint)
        if port is None:
            return None
        for rack in self._dcim_repository.list_racks_in_room(
            tenant_id,
            port.site_code.value,
            port.building_code.value,
            port.room_code.value,
        ):
            panel = self._dcim_repository.find_patch_panel(
                tenant_id,
                port.site_code.value,
                port.building_code.value,
                port.room_code.value,
                rack.code.value,
                owner_code,
            )
            if panel is None:
                continue
            base = self._from_rack(rack)
            return FieldPhysicalLocation.create(
                site=base.site,
                building=base.building,
                floor=base.floor,
                room=base.room,
                row=base.row,
                column=base.column,
                zone=base.zone,
                rack=base.rack,
                rack_face=panel.rack_face.value,
                u_position=panel.u_position,
                x=base.x,
                y=base.y,
                z=base.z,
            )
        return None

    def _rack(
        self,
        tenant_id: TenantId,
        site: str | None,
        building: str | None,
        room: str | None,
        rack_code: str,
    ) -> Rack:
        if not site or not building or not room:
            raise ValidationError("rack location requires site, building and room")
        rack = self._dcim_repository.find_rack(tenant_id, site, building, room, rack_code)
        if rack is None:
            raise NotFoundError("rack does not exist")
        return rack

    @staticmethod
    def _from_equipment(equipment: Equipment) -> FieldPhysicalLocation:
        location = equipment.location
        return FieldLocationResolver._from_location(location)

    @staticmethod
    def _from_location(location: EquipmentLocation) -> FieldPhysicalLocation:
        coordinates = location.coordinates
        return FieldPhysicalLocation.create(
            site=location.site_code.value,
            building=location.building_code.value,
            floor=location.floor_code.value if location.floor_code else None,
            room=location.room_code.value,
            row=location.row,
            column=location.column,
            zone=location.zone_code.value if location.zone_code else None,
            rack=location.rack_code.value if location.rack_code else None,
            rack_face=location.rack_face.value if location.rack_face else None,
            u_position=location.u_position,
            x=coordinates.x if coordinates else None,
            y=coordinates.y if coordinates else None,
            z=coordinates.z if coordinates else None,
        )

    @staticmethod
    def _from_rack(rack: Rack) -> FieldPhysicalLocation:
        coordinates = rack.coordinates
        return FieldPhysicalLocation.create(
            site=rack.site_code.value,
            building=rack.building_code.value,
            floor=rack.floor_code.value if rack.floor_code else None,
            room=rack.room_code.value,
            row=rack.row,
            column=rack.column,
            zone=rack.zone_code.value if rack.zone_code else None,
            rack=rack.code.value,
            x=coordinates.x if coordinates else None,
            y=coordinates.y if coordinates else None,
            z=coordinates.z if coordinates else None,
        )


class FieldSafetyAssessmentService:
    def __init__(
        self,
        graph_service: DependencyGraphService,
        flow_repository: FlowMatrixRepository,
        dcim_repository: DcimRepository,
    ) -> None:
        self._graph_service = graph_service
        self._flow_repository = flow_repository
        self._dcim_repository = dcim_repository

    def assess(
        self,
        tenant_id: TenantId,
        admin_token: str,
        source_object_key: str | None,
        location: FieldPhysicalLocation,
    ) -> tuple[FieldSafetyWarning, ...]:
        warnings: list[FieldSafetyWarning] = []
        self._assess_power(tenant_id, location, warnings)
        if source_object_key is None or not source_object_key.strip():
            warnings.append(
                FieldSafetyWarning.create(
                    "RSOT_LINK_MISSING",
                    Severity.WARNING.value,
                    (
                        "Aucun objet RSOT n'est associé; les impacts et flux "
                        "ne peuvent pas être évalués."
                    ),
                    "field",
                )
            )
            return tuple(warnings)
        impact = self._graph_service.impact(
            AnalyzeDependencyImpactCommand(
                tenant_id=tenant_id.value,
                admin_token=admin_token,
                root_key=source_object_key,
                max_depth=4,
                max_nodes=1000,
            )
        )
        if impact.impacted_nodes:
            warnings.append(
                FieldSafetyWarning.create(
                    "DEPENDENCY_IMPACT",
                    Severity.CRITICAL.value if impact.direct_count else Severity.WARNING.value,
                    (
                        f"La cible impacte {len(impact.impacted_nodes)} objet(s), "
                        f"dont {impact.direct_count} directement."
                    ),
                    "graph",
                )
            )
        if impact.truncated:
            warnings.append(
                FieldSafetyWarning.create(
                    "DEPENDENCY_ANALYSIS_TRUNCATED",
                    Severity.WARNING.value,
                    (
                        "L'analyse de dépendances est tronquée; le périmètre réel "
                        "peut être plus large."
                    ),
                    "graph",
                )
            )
        spof = self._graph_service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id=tenant_id.value,
                admin_token=admin_token,
                root_key=source_object_key,
                max_depth=6,
                max_nodes=2000,
                limit=10,
            )
        )
        if spof.total_spof_count:
            warnings.append(
                FieldSafetyWarning.create(
                    "SPOF_PRESENT",
                    Severity.CRITICAL.value,
                    (
                        f"Le périmètre contient {spof.total_spof_count} point(s) "
                        "unique(s) de défaillance."
                    ),
                    "graph",
                )
            )
        declarations = self._flow_repository.list_declarations(
            tenant_id,
            Pagination.from_values(500),
            include_retired=False,
        )
        related = 0
        for declaration in declarations.items:
            selectors = (declaration.source_selector, declaration.destination_selector)
            if any(
                selector.kind is FlowSelectorKind.OBJECT
                and selector.value == source_object_key.strip()
                for selector in selectors
            ):
                related += 1
        if related:
            warnings.append(
                FieldSafetyWarning.create(
                    "DECLARED_FLOWS",
                    Severity.WARNING.value,
                    (
                        f"La cible participe à {related} flux déclaré(s); vérifier "
                        "les dépendances réseau avant coupure."
                    ),
                    "flow",
                )
            )
        if declarations.next_cursor is not None:
            warnings.append(
                FieldSafetyWarning.create(
                    "FLOW_ANALYSIS_TRUNCATED",
                    Severity.WARNING.value,
                    "L'analyse des flux est bornée aux 500 premières déclarations actives.",
                    "flow",
                )
            )
        return tuple(warnings)

    def _assess_power(
        self,
        tenant_id: TenantId,
        location: FieldPhysicalLocation,
        warnings: list[FieldSafetyWarning],
    ) -> None:
        if location.rack is None:
            return
        circuits = self._dcim_repository.list_power_circuits_for_rack(
            tenant_id,
            location.site,
            location.building,
            location.room,
            location.rack,
        )
        active_sides = {circuit.side for circuit in circuits}
        if not circuits:
            warnings.append(
                FieldSafetyWarning.create(
                    "POWER_PATH_UNDOCUMENTED",
                    Severity.WARNING.value,
                    "Aucun circuit électrique n'est documenté pour ce rack.",
                    "dcim-power",
                )
            )
        elif not {PowerFeedSide.A, PowerFeedSide.B}.issubset(active_sides):
            warnings.append(
                FieldSafetyWarning.create(
                    "POWER_REDUNDANCY_MISSING",
                    Severity.CRITICAL.value,
                    "Le rack ne dispose pas de chemins électriques actifs redondants A et B.",
                    "dcim-power",
                )
            )


class FieldOperationService:
    def __init__(
        self,
        repository: FieldOperationRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        access_policy_service: AccessPolicyService,
        location_resolver: FieldLocationResolver,
        safety_assessment: FieldSafetyAssessmentService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._access_policy_service = access_policy_service
        self._location_resolver = location_resolver
        self._safety_assessment = safety_assessment

    def generate_sheet(self, command: GenerateFieldOperationSheetCommand) -> FieldOperationSheet:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        location = self._location_resolver.resolve(tenant_id, command)
        self._authorize_context(principal, Permission.FIELD_WRITE, location.site)
        warnings = self._safety_assessment.assess(
            tenant_id, command.admin_token, command.source_object_key, location
        )
        sheet = FieldOperationSheet.create(
            tenant_id=tenant_id,
            target_type=command.target_type,
            target_id=command.target_id,
            title=command.title,
            purpose=command.purpose,
            owner=command.owner,
            operator=command.operator,
            location=location,
            source_object_key=command.source_object_key,
            warnings=warnings,
            actor=principal.subject,
        )
        self._persist_sheet(sheet, principal.subject, "field.sheet.generated", command.actor)
        return sheet

    def get_sheet(self, command: GetFieldOperationSheetCommand) -> FieldOperationSheet:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_READ
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_READ, sheet.location.site)
        self._audit_read(tenant_id, principal.subject, "field.sheet.read", sheet.id.value)
        return sheet

    def list_sheets(self, command: ListFieldOperationSheetsCommand) -> FieldOperationSheetPage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_READ
        )
        if command.site:
            self._authorize_context(principal, Permission.FIELD_READ, command.site)
        page = self._repository.list_sheets(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.status,
            command.target_type,
            command.site,
        )
        visible = tuple(
            item
            for item in page.items
            if self._access_policy_service.is_allowed(
                principal,
                AccessRequestContext.create(
                    tenant_id, Permission.FIELD_READ, item.location.site, None
                ),
            )
        )
        return FieldOperationSheetPage(visible, page.next_cursor)

    def start(self, command: StartFieldOperationCommand) -> FieldOperationSheet:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        active_lock = self._repository.find_active_lock(
            tenant_id, sheet.target_type.value, sheet.target_id
        )
        if active_lock is None or active_lock.sheet_id != sheet.id:
            raise ConflictError("an active intervention lock is required before starting")
        updated = sheet.start(principal.subject)
        self._persist_sheet(updated, principal.subject, "field.operation.started", command.actor)
        return updated

    def record_checklist(self, command: RecordFieldChecklistCommand) -> FieldOperationSheet:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        updated = sheet.record_checklist(
            command.item_id, command.result, command.operator_note, principal.subject
        )
        self._persist_sheet(updated, principal.subject, "field.checklist.recorded", command.actor)
        return updated

    def attach_evidence(self, command: AttachFieldEvidenceCommand) -> FieldEvidence:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        evidence = FieldEvidence.create(
            tenant_id=tenant_id,
            sheet_id=sheet.id,
            phase=command.phase,
            media_type=command.media_type,
            filename=command.filename,
            content_base64=command.content_base64,
            caption=command.caption,
            actor=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_evidence(evidence)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    evidence.id,
                    "field.evidence.attached",
                    {
                        "sheet_id": sheet.id.value,
                        "phase": evidence.phase.value,
                        "content_sha256": evidence.content_sha256,
                        "size_bytes": evidence.size_bytes,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.evidence.attached",
                    "field_evidence",
                    evidence.id.value,
                    {
                        "sheet_id": sheet.id.value,
                        "phase": evidence.phase.value,
                        "content_sha256": evidence.content_sha256,
                        "size_bytes": evidence.size_bytes,
                        "requested_by": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return evidence

    def validate_evidence(self, command: ValidateFieldEvidenceCommand) -> FieldEvidence:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        evidence = self._repository.get_evidence(tenant_id, command.evidence_id)
        if evidence is None:
            raise NotFoundError("field evidence does not exist")
        sheet = self._required_sheet(tenant_id, evidence.sheet_id.value)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        updated = evidence.validate(principal.subject)
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_evidence(updated)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    updated.id,
                    "field.evidence.validated",
                    {
                        "sheet_id": sheet.id.value,
                        "content_sha256": updated.content_sha256,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.evidence.validated",
                    "field_evidence",
                    updated.id.value,
                    {
                        "sheet_id": sheet.id.value,
                        "content_sha256": updated.content_sha256,
                        "requested_by": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def list_evidence(self, command: GetFieldOperationSheetCommand) -> tuple[FieldEvidence, ...]:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_READ
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_READ, sheet.location.site)
        return self._repository.list_evidence(tenant_id, sheet.id.value)

    def complete(self, command: CompleteFieldOperationCommand) -> FieldOperationSheet:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        lock = self._repository.find_active_lock(
            tenant_id, sheet.target_type.value, sheet.target_id
        )
        if lock is None or lock.sheet_id != sheet.id:
            raise ConflictError("active intervention lock is missing or expired")
        evidence = self._repository.list_evidence(tenant_id, sheet.id.value)
        updated = sheet.complete(principal.subject, evidence)
        released = lock.release(principal.subject)
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_sheet(updated)
            self._repository.save_lock(released)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    updated.id,
                    "field.operation.completed",
                    {
                        "target_type": updated.target_type.value,
                        "target_id": updated.target_id,
                        "evidence_count": len(evidence),
                        "version": updated.version,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.operation.completed",
                    "field_operation_sheet",
                    sheet.id.value,
                    {
                        "target_type": sheet.target_type.value,
                        "target_id": sheet.target_id,
                        "evidence_count": len(evidence),
                        "requested_by": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def cancel(self, command: CancelFieldOperationCommand) -> FieldOperationSheet:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        updated = sheet.cancel(principal.subject)
        lock = self._repository.find_active_lock(
            tenant_id, sheet.target_type.value, sheet.target_id
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_sheet(updated)
            if lock is not None:
                self._repository.save_lock(lock.release(principal.subject))
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    updated.id,
                    "field.operation.cancelled",
                    {
                        "target_type": updated.target_type.value,
                        "target_id": updated.target_id,
                        "version": updated.version,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.operation.cancelled",
                    "field_operation_sheet",
                    sheet.id.value,
                    {"requested_by": command.actor},
                )
            )
            unit_of_work.commit()
        return updated

    def verify_qr(self, command: VerifyFieldQrCommand) -> dict[str, object]:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_READ
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_READ, sheet.location.site)
        verified = sheet.verify_qr(command.payload)
        self._audit_read(
            tenant_id,
            principal.subject,
            "field.qr.verified" if verified else "field.qr.rejected",
            sheet.id.value,
        )
        if not verified:
            raise ValidationError("field QR payload does not match the operation sheet")
        return {
            "tenant_id": tenant_id.value,
            "sheet_id": sheet.id.value,
            "target_type": sheet.target_type.value,
            "target_id": sheet.target_id,
            "verified": True,
        }

    def acquire_lock(self, command: AcquireInterventionLockCommand) -> InterventionLock:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        existing_by_key = self._repository.find_lock_by_idempotency_key(
            tenant_id, command.idempotency_key
        )
        if existing_by_key is not None:
            if existing_by_key.sheet_id != sheet.id:
                raise ConflictError("intervention lock idempotency key belongs to another sheet")
            return existing_by_key
        active = self._repository.find_active_lock(
            tenant_id, sheet.target_type.value, sheet.target_id
        )
        if active is not None:
            raise ConflictError("target is already locked by another field operation")
        lock = InterventionLock.create(
            tenant_id=tenant_id,
            sheet_id=sheet.id,
            target_type=sheet.target_type.value,
            target_id=sheet.target_id,
            idempotency_key=command.idempotency_key,
            owner=principal.subject,
            ttl_seconds=command.ttl_seconds,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_lock(lock)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    lock.id,
                    "field.operation.locked",
                    {
                        "sheet_id": sheet.id.value,
                        "target_type": sheet.target_type.value,
                        "target_id": sheet.target_id,
                        "expires_at": lock.expires_at.isoformat(),
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.operation.locked",
                    "intervention_lock",
                    lock.id.value,
                    {
                        "sheet_id": sheet.id.value,
                        "target_type": sheet.target_type.value,
                        "target_id": sheet.target_id,
                        "expires_at": lock.expires_at.isoformat(),
                        "requested_by": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return lock

    def release_lock(self, command: ReleaseInterventionLockCommand) -> InterventionLock:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_WRITE
        )
        lock = self._repository.get_lock(tenant_id, command.lock_id)
        if lock is None:
            raise NotFoundError("intervention lock does not exist")
        sheet = self._required_sheet(tenant_id, lock.sheet_id.value)
        self._authorize_context(principal, Permission.FIELD_WRITE, sheet.location.site)
        released = lock.release(principal.subject)
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_lock(released)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    released.id,
                    "field.operation.unlocked",
                    {
                        "sheet_id": sheet.id.value,
                        "target_type": released.target_type.value,
                        "target_id": released.target_id,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.operation.unlocked",
                    "intervention_lock",
                    released.id.value,
                    {"sheet_id": sheet.id.value, "requested_by": command.actor},
                )
            )
            unit_of_work.commit()
        return released

    def create_offline_package(
        self, command: CreateOfflineSyncPackageCommand
    ) -> OfflineSyncPackage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_SYNC
        )
        sheet = self._required_sheet(tenant_id, command.sheet_id)
        self._authorize_context(principal, Permission.FIELD_SYNC, sheet.location.site)
        existing = self._repository.find_offline_package_by_idempotency_key(
            tenant_id, command.idempotency_key
        )
        if existing is not None:
            if existing.sheet_id != sheet.id:
                raise ConflictError("offline package idempotency key belongs to another sheet")
            return existing
        package = OfflineSyncPackage.create(
            tenant_id=tenant_id,
            sheet=sheet,
            evidence=self._repository.list_evidence(tenant_id, sheet.id.value),
            idempotency_key=command.idempotency_key,
            ttl_seconds=command.ttl_seconds,
            actor=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_offline_package(package)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    package.id,
                    "field.offline.package.created",
                    {
                        "sheet_id": sheet.id.value,
                        "authorized_site": package.authorized_site,
                        "payload_sha256": package.payload_sha256,
                        "expires_at": package.expires_at.isoformat(),
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.offline.package.created",
                    "offline_sync_package",
                    package.id.value,
                    {
                        "sheet_id": sheet.id.value,
                        "authorized_site": package.authorized_site,
                        "payload_sha256": package.payload_sha256,
                        "expires_at": package.expires_at.isoformat(),
                        "requested_by": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return package

    def get_offline_package(self, command: GetOfflineSyncPackageCommand) -> dict[str, object]:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_SYNC
        )
        package = self._required_package(tenant_id, command.package_id)
        self._authorize_context(principal, Permission.FIELD_SYNC, package.authorized_site)
        if package.expired():
            raise ValidationError("offline package is expired")
        return package.as_dict(include_payload=command.include_payload)

    def list_offline_packages(
        self, command: ListOfflineSyncPackagesCommand
    ) -> OfflineSyncPackagePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_SYNC
        )
        return self._repository.list_offline_packages(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.sheet_id,
        )

    def synchronize_offline_package(
        self, command: SynchronizeOfflinePackageCommand
    ) -> OfflineSyncPackage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.FIELD_SYNC
        )
        package = self._required_package(tenant_id, command.package_id)
        self._authorize_context(principal, Permission.FIELD_SYNC, package.authorized_site)
        synchronized = package.synchronize(command.payload_sha256, principal.subject)
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_offline_package(synchronized)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    synchronized.id,
                    "field.offline.sync.completed",
                    {
                        "sheet_id": synchronized.sheet_id.value,
                        "payload_sha256": synchronized.payload_sha256,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    principal.subject,
                    "field.offline.sync.completed",
                    "offline_sync_package",
                    synchronized.id.value,
                    {
                        "sheet_id": synchronized.sheet_id.value,
                        "payload_sha256": synchronized.payload_sha256,
                        "requested_by": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return synchronized

    def _persist_sheet(
        self, sheet: FieldOperationSheet, actor: str, action: str, requested_by: str
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_sheet(sheet)
            self._repository.append_event(
                DomainEvent.create(
                    sheet.tenant_id,
                    sheet.id,
                    action,
                    {
                        "target_type": sheet.target_type.value,
                        "target_id": sheet.target_id,
                        "site": sheet.location.site,
                        "status": sheet.status.value,
                        "version": sheet.version,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    sheet.tenant_id,
                    actor,
                    action,
                    "field_operation_sheet",
                    sheet.id.value,
                    {
                        "target_type": sheet.target_type.value,
                        "target_id": sheet.target_id,
                        "site": sheet.location.site,
                        "status": sheet.status.value,
                        "version": sheet.version,
                        "requested_by": requested_by,
                    },
                )
            )
            unit_of_work.commit()

    def _audit_read(self, tenant_id: TenantId, actor: str, action: str, target_id: str) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    actor,
                    action,
                    "field_operation_sheet",
                    target_id,
                )
            )
            unit_of_work.commit()

    def _required_sheet(self, tenant_id: TenantId, sheet_id: str) -> FieldOperationSheet:
        sheet = self._repository.get_sheet(tenant_id, sheet_id)
        if sheet is None:
            raise NotFoundError("field operation sheet does not exist")
        return sheet

    def _required_package(self, tenant_id: TenantId, package_id: str) -> OfflineSyncPackage:
        package = self._repository.get_offline_package(tenant_id, package_id)
        if package is None:
            raise NotFoundError("offline sync package does not exist")
        return package

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized_tenant = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized_tenant.value, token, permission)
        )
        return normalized_tenant, principal

    def _authorize_context(
        self, principal: AuthenticatedPrincipal, permission: Permission, site: str
    ) -> None:
        self._access_policy_service.authorize(
            principal,
            AccessRequestContext.create(principal.tenant_id, permission, site, None),
        )
