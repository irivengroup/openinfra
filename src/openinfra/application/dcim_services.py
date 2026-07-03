from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openinfra.application.ports import AuditRepository, DcimRepository, TransactionManager
from openinfra.domain.common import AuditEvent, Coordinates3D, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import Building, Equipment, EquipmentLocation, Floor, Rack, Room, RoomZone, Site


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
        )
        if rack is not None and command.u_position is not None and command.u_position > rack.units:
            raise ValidationError("equipment unit position exceeds rack capacity")
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
        room.assert_zone_known(command.zone)

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
