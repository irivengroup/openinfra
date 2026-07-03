from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openinfra.application.ports import AuditRepository, DcimRepository, TransactionManager
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    Coordinates3D,
    NotFoundError,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import (
    Building,
    Equipment,
    EquipmentLocation,
    Floor,
    Rack,
    EquipmentLocatorSheet,
    EquipmentScanProof,
    RackCapacityReport,
    RackElevation,
    Room,
    RoomPlan2D,
    RoomZone,
    Site,
)


@dataclass(frozen=True, slots=True)
class DefinePhysicalRoomCommand:
    tenant_id: str
    actor: str
    site_code: str
    site_name: str
    country: str
    region: str
    city: str
    building_code: str
    building_name: str
    floor_code: str
    floor_name: str
    floor_index: int
    room_code: str
    room_name: str
    rows: tuple[str, ...]
    columns: tuple[str, ...]
    zone_code: str | None = None
    zone_name: str | None = None
    zone_rows: tuple[str, ...] = ()
    zone_columns: tuple[str, ...] = ()
    x: float | None = None
    y: float | None = None
    z: float | None = None


@dataclass(frozen=True, slots=True)
class DefineRackCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    rack: str
    row: str
    column: str
    units: int
    floor: str | None = None
    zone: str | None = None
    usable_faces: tuple[str, ...] = ("front",)
    max_weight_kg: float | None = None
    power_capacity_watts: int | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None


@dataclass(frozen=True, slots=True)
class RackCapacityCommand:
    tenant_id: str
    site: str
    building: str
    room: str
    rack: str


@dataclass(frozen=True, slots=True)
class RenderRoomPlanCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    output_format: str = "json"


@dataclass(frozen=True, slots=True)
class RenderRackElevationCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    rack: str
    face: str = "front"
    output_format: str = "json"


@dataclass(frozen=True, slots=True)
class GenerateEquipmentLocatorCommand:
    tenant_id: str
    actor: str
    asset_tag: str
    output_format: str = "json"


@dataclass(frozen=True, slots=True)
class VerifyEquipmentScanCommand:
    tenant_id: str
    actor: str
    asset_tag: str
    payload: str


@dataclass(frozen=True, slots=True)
class LocateEquipmentCommand:
    tenant_id: str
    actor: str
    asset_tag: str
    equipment_name: str
    site: str
    building: str
    room: str
    row: str
    column: str
    rack: str | None
    u_position: int | None
    x: float | None
    y: float | None
    z: float | None
    floor: str | None = None
    zone: str | None = None
    rack_face: str | None = None
    u_height: int | None = None


class DcimTopologyService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def define_room(self, command: DefinePhysicalRoomCommand) -> dict[str, Any]:
        tenant_id = TenantId.from_value(command.tenant_id)
        coordinates = Coordinates3D.from_values(command.x, command.y, command.z)
        site = Site.create(
            tenant_id,
            command.site_code,
            command.site_name,
            command.country,
            command.city,
            command.region,
        )
        building = Building.create(
            tenant_id,
            command.site_code,
            command.building_code,
            command.building_name,
        )
        floor = Floor.create(
            tenant_id,
            command.site_code,
            command.building_code,
            command.floor_code,
            command.floor_name,
            command.floor_index,
        )
        zone_codes = (command.zone_code,) if command.zone_code else ()
        room = Room.create(
            tenant_id,
            command.site_code,
            command.building_code,
            command.room_code,
            command.room_name,
            command.rows,
            command.columns,
            floor_code=command.floor_code,
            zone_codes=zone_codes,
            coordinates=coordinates,
        )
        zone = self._create_optional_zone(command, tenant_id, room)
        with self._transaction_manager.begin() as unit_of_work:
            created = self._ensure_physical_hierarchy(site, building, floor, room, zone)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.physical-room.defined",
                    target_type="room",
                    target_id=room.code.value,
                    metadata={
                        "site": site.code.value,
                        "building": building.code.value,
                        "floor": floor.code.value,
                        "room": room.code.value,
                        "zone": zone.code.value if zone else None,
                        "rows": list(room.rows),
                        "columns": list(room.columns),
                        "created": created,
                    },
                )
            )
            unit_of_work.commit()
        return {
            "tenant_id": tenant_id.value,
            "site": site.code.value,
            "building": building.code.value,
            "floor": floor.code.value,
            "room": room.code.value,
            "zone": zone.code.value if zone else None,
            "path": room.physical_path(),
            "rows": list(room.rows),
            "columns": list(room.columns),
            "created": created,
        }

    def _create_optional_zone(
        self,
        command: DefinePhysicalRoomCommand,
        tenant_id: TenantId,
        room: Room,
    ) -> RoomZone | None:
        if command.zone_code is None:
            if command.zone_name or command.zone_rows or command.zone_columns:
                raise ValidationError("zone code is mandatory when zone details are provided")
            return None
        if not command.zone_name:
            raise ValidationError("zone name is mandatory when zone code is provided")
        rows = command.zone_rows or command.rows
        columns = command.zone_columns or command.columns
        zone = RoomZone.create(
            tenant_id,
            command.site_code,
            command.building_code,
            command.floor_code,
            command.room_code,
            command.zone_code,
            command.zone_name,
            rows,
            columns,
        )
        zone.assert_within_room(room)
        return zone

    def _ensure_physical_hierarchy(
        self,
        site: Site,
        building: Building,
        floor: Floor,
        room: Room,
        zone: RoomZone | None,
    ) -> dict[str, bool]:
        created = {
            "site": False,
            "building": False,
            "floor": False,
            "room": False,
            "zone": False,
        }
        if self._dcim_repository.find_site(site.tenant_id, site.code.value) is None:
            self._dcim_repository.add_site(site)
            created["site"] = True
        if self._dcim_repository.find_building(
            building.tenant_id,
            building.site_code.value,
            building.code.value,
        ) is None:
            self._dcim_repository.add_building(building)
            created["building"] = True
        if self._dcim_repository.find_floor(
            floor.tenant_id,
            floor.site_code.value,
            floor.building_code.value,
            floor.code.value,
        ) is None:
            self._dcim_repository.add_floor(floor)
            created["floor"] = True
        if self._dcim_repository.find_room(
            room.tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
        ) is None:
            self._dcim_repository.add_room(room)
            created["room"] = True
        if zone is not None and self._dcim_repository.find_zone(
            zone.tenant_id,
            zone.site_code.value,
            zone.building_code.value,
            zone.room_code.value,
            zone.code.value,
        ) is None:
            self._dcim_repository.add_zone(zone)
            created["zone"] = True
        return created


class DcimRackService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def define_rack(self, command: DefineRackCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._dcim_repository.find_room(
            tenant_id,
            command.site,
            command.building,
            command.room,
        )
        if room is None:
            raise NotFoundError("room must exist before defining a rack")
        self._validate_rack_context(command, room)
        zone = self._resolve_zone(command, tenant_id, room)
        coordinates = Coordinates3D.from_values(command.x, command.y, command.z)
        rack = Rack.create(
            tenant_id=tenant_id,
            site_code=command.site,
            building_code=command.building,
            room_code=command.room,
            code=command.rack,
            row=command.row,
            column=command.column,
            units=command.units,
            coordinates=coordinates,
            floor_code=command.floor or (room.floor_code.value if room.floor_code else None),
            zone_code=zone.code.value if zone else command.zone,
            usable_faces=command.usable_faces,
            max_weight_kg=command.max_weight_kg,
            power_capacity_watts=command.power_capacity_watts,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_rack(rack)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.rack.defined",
                    target_type="rack",
                    target_id=rack.code.value,
                    metadata=rack.as_capacity_seed(),
                )
            )
            unit_of_work.commit()
        return {
            "tenant_id": tenant_id.value,
            "site": rack.site_code.value,
            "building": rack.building_code.value,
            "floor": rack.floor_code.value if rack.floor_code else None,
            "room": rack.room_code.value,
            "zone": rack.zone_code.value if rack.zone_code else None,
            "rack": rack.code.value,
            "row": rack.row,
            "column": rack.column,
            "units": rack.units,
            "faces": [face.value for face in rack.usable_faces],
            "max_weight_kg": rack.max_weight_kg,
            "power_capacity_watts": rack.power_capacity_watts,
        }

    def capacity(self, command: RackCapacityCommand) -> RackCapacityReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        rack = self._dcim_repository.find_rack(
            tenant_id,
            command.site,
            command.building,
            command.room,
            command.rack,
        )
        if rack is None:
            raise NotFoundError("rack does not exist")
        equipment = self._dcim_repository.list_equipment_in_rack(
            tenant_id,
            command.site,
            command.building,
            command.room,
            command.rack,
        )
        return RackCapacityReport(rack, equipment)

    def _validate_rack_context(self, command: DefineRackCommand, room: Room) -> None:
        if command.floor is not None and room.floor_code is not None:
            if command.floor.strip().upper() != room.floor_code.value:
                raise ValidationError("rack floor does not match room floor")
        room.assert_cell_exists(command.row, command.column)

    def _resolve_zone(
        self,
        command: DefineRackCommand,
        tenant_id: TenantId,
        room: Room,
    ) -> RoomZone | None:
        if command.zone is None:
            return None
        zone = self._dcim_repository.find_zone(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
            zone=command.zone,
        )
        if zone is None:
            raise NotFoundError("zone must exist before defining a rack in a zone")
        zone.assert_within_room(room)
        zone.assert_cell_exists(command.row, command.column)
        return zone


class DcimVisualizationService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def room_plan(self, command: RenderRoomPlanCommand) -> RoomPlan2D:
        tenant_id = TenantId.from_value(command.tenant_id)
        output_format = self._normalize_output_format(command.output_format)
        room = self._dcim_repository.find_room(
            tenant_id,
            command.site,
            command.building,
            command.room,
        )
        if room is None:
            raise NotFoundError("room does not exist")
        plan = RoomPlan2D.create(
            room,
            self._dcim_repository.list_racks_in_room(
                tenant_id,
                command.site,
                command.building,
                command.room,
            ),
            self._dcim_repository.list_equipment_in_room(
                tenant_id,
                command.site,
                command.building,
                command.room,
            ),
        )
        self._record_visualization_audit(
            tenant_id,
            command.actor,
            "dcim.room-plan.rendered",
            "room",
            room.code.value,
            output_format,
        )
        return plan

    def rack_elevation(self, command: RenderRackElevationCommand) -> RackElevation:
        tenant_id = TenantId.from_value(command.tenant_id)
        output_format = self._normalize_output_format(command.output_format)
        rack = self._dcim_repository.find_rack(
            tenant_id,
            command.site,
            command.building,
            command.room,
            command.rack,
        )
        if rack is None:
            raise NotFoundError("rack does not exist")
        elevation = RackElevation.create(
            rack,
            self._dcim_repository.list_equipment_in_rack(
                tenant_id,
                command.site,
                command.building,
                command.room,
                command.rack,
            ),
            command.face,
        )
        self._record_visualization_audit(
            tenant_id,
            command.actor,
            "dcim.rack-elevation.rendered",
            "rack",
            rack.code.value,
            output_format,
        )
        return elevation

    def _normalize_output_format(self, value: str) -> str:
        output_format = value.strip().lower()
        if output_format not in ("json", "svg", "html"):
            raise ValidationError("visualization format must be json, svg or html")
        return output_format

    def _record_visualization_audit(
        self,
        tenant_id: TenantId,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        output_format: str,
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    metadata={"format": output_format},
                )
            )
            unit_of_work.commit()


class DcimFieldOperationService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def locator_sheet(self, command: GenerateEquipmentLocatorCommand) -> EquipmentLocatorSheet:
        tenant_id = TenantId.from_value(command.tenant_id)
        equipment = self._dcim_repository.find_equipment(tenant_id, command.asset_tag)
        if equipment is None:
            raise NotFoundError("equipment does not exist")
        sheet = EquipmentLocatorSheet.create(equipment)
        output_format = command.output_format.strip().lower()
        if output_format not in ("json", "html"):
            raise ValidationError("locator sheet format must be json or html")
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.locator-sheet.generated",
                    target_type="equipment",
                    target_id=equipment.asset_tag.value,
                    metadata={
                        "format": output_format,
                        "payload_checksum": sheet.locator_payload.checksum,
                    },
                )
            )
            unit_of_work.commit()
        return sheet

    def verify_scan(self, command: VerifyEquipmentScanCommand) -> EquipmentScanProof:
        tenant_id = TenantId.from_value(command.tenant_id)
        equipment = self._dcim_repository.find_equipment(tenant_id, command.asset_tag)
        if equipment is None:
            raise NotFoundError("equipment does not exist")
        proof = EquipmentScanProof.create(equipment, command.payload)
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.qr-scan.verified" if proof.verified else "dcim.qr-scan.rejected",
                    target_type="equipment",
                    target_id=equipment.asset_tag.value,
                    metadata={
                        "verified": proof.verified,
                        "expected_payload": proof.expected_payload,
                        "received_payload": proof.received_payload,
                    },
                )
            )
            unit_of_work.commit()
        if not proof.verified:
            raise ValidationError("QR payload does not match the equipment locator")
        return proof


class DcimLocationService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def locate_equipment(self, command: LocateEquipmentCommand) -> Equipment:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._dcim_repository.find_room(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
        )
        if room is None:
            raise NotFoundError("room must exist before locating equipment")
        self._validate_room_context(command, room)
        rack = self._resolve_rack(command, tenant_id)
        zone = self._resolve_zone(command, tenant_id, room)
        coordinates = Coordinates3D.from_values(command.x, command.y, command.z)
        location = EquipmentLocation.create(
            site_code=command.site,
            building_code=command.building,
            room_code=command.room,
            row=command.row,
            column=command.column,
            rack_code=command.rack,
            u_position=command.u_position,
            coordinates=coordinates,
            floor_code=command.floor or (room.floor_code.value if room.floor_code else None),
            zone_code=zone.code.value if zone else command.zone,
            rack_face=command.rack_face,
            u_height=command.u_height,
        )
        if rack is not None and location.u_position is not None:
            rack_face = location.effective_rack_face()
            unit_height = location.effective_u_height()
            if rack_face is None or unit_height is None:
                raise ValidationError("rack face and unit height must be resolvable")
            rack.assert_face_supported(rack_face)
            rack.assert_unit_interval(location.u_position, unit_height)
            self._assert_no_rack_overlap(tenant_id, command.asset_tag, rack, location)
        equipment = Equipment.create(
            tenant_id=tenant_id,
            asset_tag=command.asset_tag,
            name=command.equipment_name,
            location=location,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_equipment(equipment)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.equipment.located",
                    target_type="equipment",
                    target_id=equipment.asset_tag.value,
                    metadata={"location": equipment.location.human_readable()},
                )
            )
            unit_of_work.commit()
        return equipment

    def _validate_room_context(self, command: LocateEquipmentCommand, room: Room) -> None:
        if command.floor is not None and room.floor_code is not None:
            requested_floor = command.floor.strip().upper()
            if requested_floor != room.floor_code.value:
                raise ValidationError("requested floor does not match room floor")
        room.assert_cell_exists(command.row, command.column)

    def _resolve_zone(
        self,
        command: LocateEquipmentCommand,
        tenant_id: TenantId,
        room: Room,
    ) -> RoomZone | None:
        if command.zone is None:
            return None
        zone = self._dcim_repository.find_zone(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
            zone=command.zone,
        )
        if zone is None:
            raise NotFoundError("zone must exist before locating equipment in a zone")
        zone.assert_within_room(room)
        zone.assert_cell_exists(command.row, command.column)
        return zone

    def _resolve_rack(self, command: LocateEquipmentCommand, tenant_id: TenantId) -> Rack | None:
        if command.rack is None:
            return None
        rack = self._dcim_repository.find_rack(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
            rack=command.rack,
        )
        if rack is None:
            raise NotFoundError("rack must exist before rack-mounted equipment location")
        if rack.row != command.row.strip().upper() or rack.column != command.column.strip().upper():
            raise ValidationError("rack row and column do not match equipment location")
        if command.floor is not None and rack.floor_code is not None:
            if command.floor.strip().upper() != rack.floor_code.value:
                raise ValidationError("rack floor does not match equipment location")
        if command.zone is not None and rack.zone_code is not None:
            if command.zone.strip().upper() != rack.zone_code.value:
                raise ValidationError("rack zone does not match equipment location")
        return rack

    def _assert_no_rack_overlap(
        self,
        tenant_id: TenantId,
        asset_tag: str,
        rack: Rack,
        location: EquipmentLocation,
    ) -> None:
        existing_items = self._dcim_repository.list_equipment_in_rack(
            tenant_id,
            rack.site_code.value,
            rack.building_code.value,
            rack.room_code.value,
            rack.code.value,
        )
        normalized_asset_tag = asset_tag.strip().upper()
        for item in existing_items:
            if item.asset_tag.value == normalized_asset_tag:
                continue
            if location.overlaps(item.location):
                raise ConflictError(
                    "rack unit interval overlaps existing equipment " + item.asset_tag.value
                )
