from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openinfra.application.edition_services import EditionRuntimeGuard
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
    CoolingZone,
    DcimCable,
    DcimCablePathSegment,
    DcimPort,
    DcimPortEndpoint,
    DcimPortOwnerType,
    Equipment,
    EquipmentLocation,
    EquipmentLocatorSheet,
    EquipmentScanProof,
    Floor,
    PatchPanel,
    PowerCircuit,
    PowerDevice,
    Rack,
    RackCapacityReport,
    RackElevation,
    RackEnergyCoolingReport,
    RackPowerReservation,
    Room,
    RoomPlan2D,
    RoomZone,
    Site,
)
from openinfra.domain.editions import QuotaResource


@dataclass(frozen=True, slots=True)
class CreateDcimSiteCommand:
    tenant_id: str
    actor: str
    code: str
    name: str
    country: str
    city: str
    region: str = ""


@dataclass(frozen=True, slots=True)
class UpdateDcimSiteCommand:
    tenant_id: str
    actor: str
    code: str
    name: str | None = None
    country: str | None = None
    city: str | None = None
    region: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDcimSiteCommand:
    tenant_id: str
    actor: str
    code: str


@dataclass(frozen=True, slots=True)
class GetDcimSiteCommand:
    tenant_id: str
    code: str


@dataclass(frozen=True, slots=True)
class ListDcimSitesCommand:
    tenant_id: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class CreateDcimBuildingCommand:
    tenant_id: str
    actor: str
    site: str
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class UpdateDcimBuildingCommand:
    tenant_id: str
    actor: str
    site: str
    code: str
    name: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDcimBuildingCommand:
    tenant_id: str
    actor: str
    site: str
    code: str


@dataclass(frozen=True, slots=True)
class GetDcimBuildingCommand:
    tenant_id: str
    site: str
    code: str


@dataclass(frozen=True, slots=True)
class ListDcimBuildingsCommand:
    tenant_id: str
    site: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class CreateDcimFloorCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    code: str
    name: str
    level_index: int


@dataclass(frozen=True, slots=True)
class UpdateDcimFloorCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    code: str
    name: str | None = None
    level_index: int | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDcimFloorCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    code: str


@dataclass(frozen=True, slots=True)
class GetDcimFloorCommand:
    tenant_id: str
    site: str
    building: str
    code: str


@dataclass(frozen=True, slots=True)
class ListDcimFloorsCommand:
    tenant_id: str
    site: str
    building: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class CreateDcimRoomCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    floor: str | None
    code: str
    name: str
    rows: tuple[str, ...]
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UpdateDcimRoomCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    code: str
    name: str | None = None
    rows: tuple[str, ...] | None = None
    columns: tuple[str, ...] | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDcimRoomCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    code: str


@dataclass(frozen=True, slots=True)
class GetDcimRoomCommand:
    tenant_id: str
    site: str
    building: str
    code: str


@dataclass(frozen=True, slots=True)
class ListDcimRoomsCommand:
    tenant_id: str
    site: str
    building: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class CreateDcimZoneCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    code: str
    name: str
    rows: tuple[str, ...]
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UpdateDcimZoneCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    code: str
    name: str | None = None
    rows: tuple[str, ...] | None = None
    columns: tuple[str, ...] | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDcimZoneCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    code: str


@dataclass(frozen=True, slots=True)
class GetDcimZoneCommand:
    tenant_id: str
    site: str
    building: str
    room: str
    code: str


@dataclass(frozen=True, slots=True)
class ListDcimZonesCommand:
    tenant_id: str
    site: str
    building: str
    room: str
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class DcimTopologyCatalogCommand:
    tenant_id: str
    include_retired: bool = False


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
class UpdateRackCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    rack: str
    row: str | None = None
    column: str | None = None
    units: int | None = None
    usable_faces: tuple[str, ...] | None = None
    max_weight_kg: float | None = None
    power_capacity_watts: int | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteRackCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    rack: str


@dataclass(frozen=True, slots=True)
class GetRackCommand:
    tenant_id: str
    site: str
    building: str
    room: str
    rack: str


@dataclass(frozen=True, slots=True)
class ListRacksCommand:
    tenant_id: str
    site: str
    building: str
    room: str
    include_retired: bool = False


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
class RenderDigitalTwinCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str


@dataclass(frozen=True, slots=True)
class DefinePatchPanelCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    rack: str
    patch_panel: str
    rack_face: str
    u_position: int
    u_height: int
    port_count: int
    connector: str
    medium: str
    label: str = ""
    port_prefix: str = "P"


@dataclass(frozen=True, slots=True)
class DefineDcimPortCommand:
    tenant_id: str
    actor: str
    owner_type: str
    owner_code: str
    port_name: str
    connector: str
    medium: str
    site: str | None = None
    building: str | None = None
    room: str | None = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ConnectDcimCableCommand:
    tenant_id: str
    actor: str
    cable_id: str
    a_owner_type: str
    a_owner_code: str
    a_port_name: str
    b_owner_type: str
    b_owner_code: str
    b_port_name: str
    medium: str
    status: str = "installed"
    path_segments: tuple[str, ...] = ()
    length_m: float | None = None
    label: str = ""


@dataclass(frozen=True, slots=True)
class TraceDcimCableCommand:
    tenant_id: str
    actor: str
    cable_id: str


@dataclass(frozen=True, slots=True)
class DefinePowerDeviceCommand:
    tenant_id: str
    actor: str
    code: str
    kind: str
    site: str
    building: str
    room: str
    capacity_watts: int
    rack: str | None = None
    side: str | None = None
    derating_percent: int = 80
    input_source: str = "utility"
    output_voltage: int = 230
    label: str = ""


@dataclass(frozen=True, slots=True)
class DefinePowerCircuitCommand:
    tenant_id: str
    actor: str
    circuit_id: str
    source_device: str
    site: str
    building: str
    room: str
    rack: str
    side: str
    capacity_watts: int
    breaker_rating_amps: int
    redundancy_group: str = "default"
    label: str = ""


@dataclass(frozen=True, slots=True)
class DefineCoolingZoneCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    zone: str
    role: str
    cooling_capacity_watts: int
    supply_temperature_c: float
    return_temperature_c: float
    label: str = ""


@dataclass(frozen=True, slots=True)
class ReserveEquipmentPowerCommand:
    tenant_id: str
    actor: str
    asset_tag: str
    circuit_id: str
    expected_watts: int
    label: str = ""


@dataclass(frozen=True, slots=True)
class RackEnergyCoolingCapacityCommand:
    tenant_id: str
    actor: str
    site: str
    building: str
    room: str
    rack: str


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

    def create_site(self, command: CreateDcimSiteCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = Site.create(
            tenant_id=tenant_id,
            code=command.code,
            name=command.name,
            country=command.country,
            city=command.city,
            region=command.region,
        )
        with self._transaction_manager.begin() as unit_of_work:
            if self._dcim_repository.find_site(tenant_id, site.code.value) is not None:
                raise ConflictError("DCIM site already exists")
            self._dcim_repository.add_site(site)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.site.created",
                    target_type="site",
                    target_id=site.code.value,
                    metadata=site.as_dict(),
                )
            )
            unit_of_work.commit()
        return site.as_dict()

    def update_site(self, command: UpdateDcimSiteCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = self._dcim_repository.find_site(tenant_id, command.code)
        if site is None:
            raise NotFoundError("DCIM site does not exist")
        updated = site.update(
            name=command.name,
            country=command.country,
            city=command.city,
            region=command.region,
            status=command.status,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_site(updated)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.site.updated",
                    target_type="site",
                    target_id=updated.code.value,
                    metadata=updated.as_dict(),
                )
            )
            unit_of_work.commit()
        return updated.as_dict()

    def delete_site(self, command: DeleteDcimSiteCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = self._dcim_repository.find_site(tenant_id, command.code)
        if site is None:
            raise NotFoundError("DCIM site does not exist")
        retired_site = site.retire()
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_site(retired_site)
            for building in self._dcim_repository.list_buildings(
                tenant_id, retired_site.code.value, include_retired=True
            ):
                self._retire_building_tree(tenant_id, building)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.site.retired",
                    target_type="site",
                    target_id=retired_site.code.value,
                    metadata={
                        "site": retired_site.as_dict(),
                        "cascade": ["buildings", "floors", "rooms", "zones", "racks"],
                    },
                )
            )
            unit_of_work.commit()
        return retired_site.as_dict()

    def get_site(self, command: GetDcimSiteCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = self._dcim_repository.find_site(tenant_id, command.code)
        if site is None:
            raise NotFoundError("DCIM site does not exist")
        return site.as_dict()

    def list_sites(self, command: ListDcimSitesCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        items = self._dcim_repository.list_sites(tenant_id, command.include_retired)
        return {
            "tenant_id": tenant_id.value,
            "items": [item.as_dict() for item in items],
            "count": len(items),
        }

    def create_building(self, command: CreateDcimBuildingCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = self._require_selectable_site(tenant_id, command.site)
        building = Building.create(tenant_id, site.code.value, command.code, command.name)
        with self._transaction_manager.begin() as unit_of_work:
            if (
                self._dcim_repository.find_building(tenant_id, site.code.value, building.code.value)
                is not None
            ):
                raise ConflictError("DCIM building already exists")
            self._dcim_repository.add_building(building)
            self._audit_topology(command.actor, tenant_id, "dcim.building.created", building)
            unit_of_work.commit()
        return building.as_dict()

    def update_building(self, command: UpdateDcimBuildingCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = self._require_site(tenant_id, command.site)
        building = self._dcim_repository.find_building(tenant_id, site.code.value, command.code)
        if building is None:
            raise NotFoundError("DCIM building does not exist")
        if command.status == "active" and not site.selectable():
            raise ValidationError("cannot activate building under a non-active site")
        updated = building.update(name=command.name, status=command.status)
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_building(updated)
            self._audit_topology(command.actor, tenant_id, "dcim.building.updated", updated)
            unit_of_work.commit()
        return updated.as_dict()

    def delete_building(self, command: DeleteDcimBuildingCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        building = self._require_building(tenant_id, command.site, command.code)
        retired = building.retire()
        with self._transaction_manager.begin() as unit_of_work:
            self._retire_building_tree(tenant_id, retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.building.retired",
                    target_type="building",
                    target_id=retired.code.value,
                    metadata={
                        "building": retired.as_dict(),
                        "cascade": ["floors", "rooms", "zones", "racks"],
                    },
                )
            )
            unit_of_work.commit()
        return retired.as_dict()

    def get_building(self, command: GetDcimBuildingCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        return self._require_building(tenant_id, command.site, command.code).as_dict()

    def list_buildings(self, command: ListDcimBuildingsCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        site = self._require_site(tenant_id, command.site)
        items = self._dcim_repository.list_buildings(
            tenant_id, site.code.value, command.include_retired
        )
        return {
            "tenant_id": tenant_id.value,
            "site": site.code.value,
            "items": [item.as_dict() for item in items],
            "count": len(items),
        }

    def create_floor(self, command: CreateDcimFloorCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        building = self._require_selectable_building(tenant_id, command.site, command.building)
        floor = Floor.create(
            tenant_id,
            building.site_code.value,
            building.code.value,
            command.code,
            command.name,
            command.level_index,
        )
        with self._transaction_manager.begin() as unit_of_work:
            if (
                self._dcim_repository.find_floor(
                    tenant_id,
                    building.site_code.value,
                    building.code.value,
                    floor.code.value,
                )
                is not None
            ):
                raise ConflictError("DCIM floor already exists")
            self._dcim_repository.add_floor(floor)
            self._audit_topology(command.actor, tenant_id, "dcim.floor.created", floor)
            unit_of_work.commit()
        return floor.as_dict()

    def update_floor(self, command: UpdateDcimFloorCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        building = self._require_building(tenant_id, command.site, command.building)
        floor = self._dcim_repository.find_floor(
            tenant_id, building.site_code.value, building.code.value, command.code
        )
        if floor is None:
            raise NotFoundError("DCIM floor does not exist")
        if command.status == "active" and not building.selectable():
            raise ValidationError("cannot activate floor under a non-active building")
        updated = floor.update(
            name=command.name, level_index=command.level_index, status=command.status
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_floor(updated)
            self._audit_topology(command.actor, tenant_id, "dcim.floor.updated", updated)
            unit_of_work.commit()
        return updated.as_dict()

    def delete_floor(self, command: DeleteDcimFloorCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        floor = self._require_floor(tenant_id, command.site, command.building, command.code)
        retired = floor.retire()
        with self._transaction_manager.begin() as unit_of_work:
            self._retire_floor_tree(tenant_id, retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.floor.retired",
                    target_type="floor",
                    target_id=retired.code.value,
                    metadata={"floor": retired.as_dict(), "cascade": ["rooms", "zones", "racks"]},
                )
            )
            unit_of_work.commit()
        return retired.as_dict()

    def get_floor(self, command: GetDcimFloorCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        return self._require_floor(
            tenant_id, command.site, command.building, command.code
        ).as_dict()

    def list_floors(self, command: ListDcimFloorsCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        building = self._require_building(tenant_id, command.site, command.building)
        items = self._dcim_repository.list_floors(
            tenant_id, building.site_code.value, building.code.value, command.include_retired
        )
        return {
            "tenant_id": tenant_id.value,
            "site": building.site_code.value,
            "building": building.code.value,
            "items": [item.as_dict() for item in items],
            "count": len(items),
        }

    def create_room(self, command: CreateDcimRoomCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        building = self._require_selectable_building(tenant_id, command.site, command.building)
        floor = self._resolve_room_floor_for_creation(tenant_id, building, command.floor)
        room = Room.create(
            tenant_id,
            building.site_code.value,
            building.code.value,
            command.code,
            command.name,
            command.rows,
            command.columns,
            floor_code=floor.code.value if floor else None,
        )
        with self._transaction_manager.begin() as unit_of_work:
            if (
                self._dcim_repository.find_room(
                    tenant_id, building.site_code.value, building.code.value, room.code.value
                )
                is not None
            ):
                raise ConflictError("DCIM room already exists")
            self._dcim_repository.add_room(room)
            self._audit_topology(command.actor, tenant_id, "dcim.room.created", room)
            unit_of_work.commit()
        return room.as_dict()

    def update_room(self, command: UpdateDcimRoomCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._require_room(tenant_id, command.site, command.building, command.code)
        if command.status == "active":
            building = self._require_building(
                tenant_id, room.site_code.value, room.building_code.value
            )
            if not building.selectable():
                raise ValidationError("cannot activate room under a non-active building")
            if room.floor_code is not None:
                floor = self._require_floor(
                    tenant_id, room.site_code.value, room.building_code.value, room.floor_code.value
                )
                if not floor.selectable():
                    raise ValidationError("cannot activate room under a non-active floor")
            elif self._building_has_active_floors(tenant_id, building):
                raise ValidationError("room floor is mandatory when building has active floors")
        updated = room.update(
            name=command.name,
            rows=command.rows,
            columns=command.columns,
            status=command.status,
        )
        with self._transaction_manager.begin() as unit_of_work:
            for zone in self._dcim_repository.list_zones(
                tenant_id,
                updated.site_code.value,
                updated.building_code.value,
                updated.code.value,
                include_retired=True,
            ):
                zone.assert_within_room(updated)
            self._dcim_repository.save_room(updated)
            self._audit_topology(command.actor, tenant_id, "dcim.room.updated", updated)
            unit_of_work.commit()
        return updated.as_dict()

    def delete_room(self, command: DeleteDcimRoomCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._require_room(tenant_id, command.site, command.building, command.code)
        retired = room.retire()
        with self._transaction_manager.begin() as unit_of_work:
            self._retire_room_tree(tenant_id, retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.room.retired",
                    target_type="room",
                    target_id=retired.code.value,
                    metadata={"room": retired.as_dict(), "cascade": ["zones", "racks"]},
                )
            )
            unit_of_work.commit()
        return retired.as_dict()

    def get_room(self, command: GetDcimRoomCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        return self._require_room(tenant_id, command.site, command.building, command.code).as_dict()

    def list_rooms(self, command: ListDcimRoomsCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        building = self._require_building(tenant_id, command.site, command.building)
        items = self._dcim_repository.list_rooms(
            tenant_id, building.site_code.value, building.code.value, command.include_retired
        )
        return {
            "tenant_id": tenant_id.value,
            "site": building.site_code.value,
            "building": building.code.value,
            "items": [item.as_dict() for item in items],
            "count": len(items),
        }

    def create_zone(self, command: CreateDcimZoneCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._require_selectable_room(
            tenant_id, command.site, command.building, command.room
        )
        if room.floor_code is None:
            raise ValidationError("room floor is mandatory to create a zone")
        zone = RoomZone.create(
            tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.floor_code.value,
            room.code.value,
            command.code,
            command.name,
            command.rows,
            command.columns,
        )
        zone.assert_within_room(room)
        with self._transaction_manager.begin() as unit_of_work:
            if (
                self._dcim_repository.find_zone(
                    tenant_id,
                    room.site_code.value,
                    room.building_code.value,
                    room.code.value,
                    zone.code.value,
                )
                is not None
            ):
                raise ConflictError("DCIM zone already exists")
            self._dcim_repository.add_zone(zone)
            self._audit_topology(command.actor, tenant_id, "dcim.zone.created", zone)
            unit_of_work.commit()
        return zone.as_dict()

    def update_zone(self, command: UpdateDcimZoneCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._require_room(tenant_id, command.site, command.building, command.room)
        zone = self._dcim_repository.find_zone(
            tenant_id, room.site_code.value, room.building_code.value, room.code.value, command.code
        )
        if zone is None:
            raise NotFoundError("DCIM zone does not exist")
        if command.status == "active" and not room.selectable():
            raise ValidationError("cannot activate zone under a non-active room")
        updated = zone.update(
            name=command.name,
            rows=command.rows,
            columns=command.columns,
            status=command.status,
        )
        updated.assert_within_room(room)
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_zone(updated)
            self._audit_topology(command.actor, tenant_id, "dcim.zone.updated", updated)
            unit_of_work.commit()
        return updated.as_dict()

    def delete_zone(self, command: DeleteDcimZoneCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        zone = self._require_zone(
            tenant_id, command.site, command.building, command.room, command.code
        )
        retired = zone.retire()
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_zone(retired)
            self._audit_topology(command.actor, tenant_id, "dcim.zone.retired", retired)
            unit_of_work.commit()
        return retired.as_dict()

    def get_zone(self, command: GetDcimZoneCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        return self._require_zone(
            tenant_id, command.site, command.building, command.room, command.code
        ).as_dict()

    def list_zones(self, command: ListDcimZonesCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._require_room(tenant_id, command.site, command.building, command.room)
        items = self._dcim_repository.list_zones(
            tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
            command.include_retired,
        )
        return {
            "tenant_id": tenant_id.value,
            "site": room.site_code.value,
            "building": room.building_code.value,
            "room": room.code.value,
            "items": [item.as_dict() for item in items],
            "count": len(items),
        }

    def _require_site(self, tenant_id: TenantId, site_code: str) -> Site:
        site = self._dcim_repository.find_site(tenant_id, site_code)
        if site is None:
            raise NotFoundError("DCIM site does not exist")
        return site

    def _require_selectable_site(self, tenant_id: TenantId, site_code: str) -> Site:
        site = self._require_site(tenant_id, site_code)
        if not site.selectable():
            raise ValidationError("DCIM site is not active")
        return site

    def _require_building(
        self, tenant_id: TenantId, site_code: str, building_code: str
    ) -> Building:
        building = self._dcim_repository.find_building(tenant_id, site_code, building_code)
        if building is None:
            raise NotFoundError("DCIM building does not exist")
        return building

    def _require_selectable_building(
        self, tenant_id: TenantId, site_code: str, building_code: str
    ) -> Building:
        self._require_selectable_site(tenant_id, site_code)
        building = self._require_building(tenant_id, site_code, building_code)
        if not building.selectable():
            raise ValidationError("DCIM building is not active")
        return building

    def _building_has_active_floors(self, tenant_id: TenantId, building: Building) -> bool:
        return bool(
            self._dcim_repository.list_floors(
                tenant_id, building.site_code.value, building.code.value, include_retired=False
            )
        )

    def _resolve_room_floor_for_creation(
        self, tenant_id: TenantId, building: Building, floor_code: str | None
    ) -> Floor | None:
        normalized_floor = (floor_code or "").strip()
        has_active_floors = self._building_has_active_floors(tenant_id, building)
        if not normalized_floor:
            if has_active_floors:
                raise ValidationError("room floor is mandatory when building has active floors")
            return None
        floor = self._require_selectable_floor(
            tenant_id, building.site_code.value, building.code.value, normalized_floor
        )
        return floor

    def _require_floor(
        self, tenant_id: TenantId, site_code: str, building_code: str, floor_code: str
    ) -> Floor:
        floor = self._dcim_repository.find_floor(tenant_id, site_code, building_code, floor_code)
        if floor is None:
            raise NotFoundError("DCIM floor does not exist")
        return floor

    def _require_selectable_floor(
        self, tenant_id: TenantId, site_code: str, building_code: str, floor_code: str
    ) -> Floor:
        self._require_selectable_building(tenant_id, site_code, building_code)
        floor = self._require_floor(tenant_id, site_code, building_code, floor_code)
        if not floor.selectable():
            raise ValidationError("DCIM floor is not active")
        return floor

    def _require_room(
        self, tenant_id: TenantId, site_code: str, building_code: str, room_code: str
    ) -> Room:
        room = self._dcim_repository.find_room(tenant_id, site_code, building_code, room_code)
        if room is None:
            raise NotFoundError("DCIM room does not exist")
        return room

    def _require_selectable_room(
        self, tenant_id: TenantId, site_code: str, building_code: str, room_code: str
    ) -> Room:
        room = self._require_room(tenant_id, site_code, building_code, room_code)
        if not room.selectable():
            raise ValidationError("DCIM room is not active")
        if room.floor_code is not None:
            self._require_selectable_floor(
                tenant_id, room.site_code.value, room.building_code.value, room.floor_code.value
            )
        return room

    def _require_zone(
        self,
        tenant_id: TenantId,
        site_code: str,
        building_code: str,
        room_code: str,
        zone_code: str,
    ) -> RoomZone:
        zone = self._dcim_repository.find_zone(
            tenant_id, site_code, building_code, room_code, zone_code
        )
        if zone is None:
            raise NotFoundError("DCIM zone does not exist")
        return zone

    def _retire_building_tree(self, tenant_id: TenantId, building: Building) -> None:
        self._dcim_repository.save_building(building.retire())
        for floor in self._dcim_repository.list_floors(
            tenant_id, building.site_code.value, building.code.value, include_retired=True
        ):
            self._retire_floor_tree(tenant_id, floor)
        for room in self._dcim_repository.list_rooms(
            tenant_id, building.site_code.value, building.code.value, include_retired=True
        ):
            if room.floor_code is None:
                self._retire_room_tree(tenant_id, room)

    def _retire_floor_tree(self, tenant_id: TenantId, floor: Floor) -> None:
        self._dcim_repository.save_floor(floor.retire())
        for room in self._dcim_repository.list_rooms(
            tenant_id, floor.site_code.value, floor.building_code.value, include_retired=True
        ):
            if room.floor_code == floor.code:
                self._retire_room_tree(tenant_id, room)

    def _retire_room_tree(self, tenant_id: TenantId, room: Room) -> None:
        self._dcim_repository.save_room(room.retire())
        for zone in self._dcim_repository.list_zones(
            tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
            include_retired=True,
        ):
            self._dcim_repository.save_zone(zone.retire())
        for rack in self._dcim_repository.list_racks_in_room(
            tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
            include_retired=True,
        ):
            self._dcim_repository.save_rack(rack.retire())

    def _audit_topology(
        self,
        actor: str,
        tenant_id: TenantId,
        action: str,
        entity: Building | Floor | Room | RoomZone,
    ) -> None:
        self._audit_repository.append(
            AuditEvent.record(
                tenant_id=tenant_id,
                actor=actor,
                action=action,
                target_type=action.split(".")[1],
                target_id=entity.code.value,
                metadata=entity.as_dict(),
            )
        )

    def topology_catalog(self, command: DcimTopologyCatalogCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        sites_payload: list[dict[str, object]] = []
        for site in self._dcim_repository.list_sites(tenant_id, command.include_retired):
            buildings_payload: list[dict[str, object]] = []
            for building in self._dcim_repository.list_buildings(
                tenant_id, site.code.value, command.include_retired
            ):
                floors = self._dcim_repository.list_floors(
                    tenant_id, site.code.value, building.code.value, command.include_retired
                )
                rooms_payload: list[dict[str, object]] = []
                for room in self._dcim_repository.list_rooms(
                    tenant_id, site.code.value, building.code.value, command.include_retired
                ):
                    zones = self._dcim_repository.list_zones(
                        tenant_id,
                        site.code.value,
                        building.code.value,
                        room.code.value,
                        command.include_retired,
                    )
                    racks = self._dcim_repository.list_racks_in_room(
                        tenant_id, site.code.value, building.code.value, room.code.value
                    )
                    rooms_payload.append(
                        {
                            **room.as_dict(),
                            "zones": [zone.as_dict() for zone in zones],
                            "racks": [rack.as_capacity_seed() for rack in racks],
                        }
                    )
                buildings_payload.append(
                    {
                        **building.as_dict(),
                        "floors": [floor.as_dict() for floor in floors],
                        "rooms": rooms_payload,
                    }
                )
            sites_payload.append({**site.as_dict(), "buildings": buildings_payload})
        return {"tenant_id": tenant_id.value, "sites": sites_payload}

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
        if (
            self._dcim_repository.find_building(
                building.tenant_id,
                building.site_code.value,
                building.code.value,
            )
            is None
        ):
            self._dcim_repository.add_building(building)
            created["building"] = True
        if (
            self._dcim_repository.find_floor(
                floor.tenant_id,
                floor.site_code.value,
                floor.building_code.value,
                floor.code.value,
            )
            is None
        ):
            self._dcim_repository.add_floor(floor)
            created["floor"] = True
        if (
            self._dcim_repository.find_room(
                room.tenant_id,
                room.site_code.value,
                room.building_code.value,
                room.code.value,
            )
            is None
        ):
            self._dcim_repository.add_room(room)
            created["room"] = True
        if (
            zone is not None
            and self._dcim_repository.find_zone(
                zone.tenant_id,
                zone.site_code.value,
                zone.building_code.value,
                zone.room_code.value,
                zone.code.value,
            )
            is None
        ):
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
        room = self._require_selectable_room(
            tenant_id, command.site, command.building, command.room
        )
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
            if (
                self._dcim_repository.find_rack(
                    tenant_id,
                    rack.site_code.value,
                    rack.building_code.value,
                    rack.room_code.value,
                    rack.code.value,
                )
                is not None
            ):
                raise ConflictError("DCIM rack already exists")
            self._dcim_repository.add_rack(rack)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.rack.created",
                    target_type="rack",
                    target_id=rack.code.value,
                    metadata=rack.as_dict(),
                )
            )
            unit_of_work.commit()
        return rack.as_dict()

    def update_rack(self, command: UpdateRackCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        rack = self._require_rack(
            tenant_id, command.site, command.building, command.room, command.rack
        )
        room = self._dcim_repository.find_room(
            tenant_id, rack.site_code.value, rack.building_code.value, rack.room_code.value
        )
        if room is None:
            raise NotFoundError("rack room does not exist")
        if command.row is not None or command.column is not None:
            room.assert_cell_exists(command.row or rack.row, command.column or rack.column)
        if command.status == "active" and not room.selectable():
            raise ValidationError("cannot activate rack under a non-active room")
        updated = rack.update(
            row=command.row,
            column=command.column,
            units=command.units,
            usable_faces=command.usable_faces,
            max_weight_kg=command.max_weight_kg,
            power_capacity_watts=command.power_capacity_watts,
            status=command.status,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_rack(updated)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.rack.updated",
                    target_type="rack",
                    target_id=updated.code.value,
                    metadata=updated.as_dict(),
                )
            )
            unit_of_work.commit()
        return updated.as_dict()

    def delete_rack(self, command: DeleteRackCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        rack = self._require_rack(
            tenant_id, command.site, command.building, command.room, command.rack
        )
        retired = rack.retire()
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.save_rack(retired)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.rack.retired",
                    target_type="rack",
                    target_id=retired.code.value,
                    metadata=retired.as_dict(),
                )
            )
            unit_of_work.commit()
        return retired.as_dict()

    def get_rack(self, command: GetRackCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        return self._require_rack(
            tenant_id, command.site, command.building, command.room, command.rack
        ).as_dict()

    def list_racks(self, command: ListRacksCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._require_room(tenant_id, command.site, command.building, command.room)
        racks = self._dcim_repository.list_racks_in_room(
            tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
            command.include_retired,
        )
        return {
            "tenant_id": tenant_id.value,
            "site": room.site_code.value,
            "building": room.building_code.value,
            "room": room.code.value,
            "items": [rack.as_dict() for rack in racks],
            "count": len(racks),
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
        if not rack.selectable():
            raise ValidationError("DCIM rack is not active")
        equipment = self._dcim_repository.list_equipment_in_rack(
            tenant_id,
            command.site,
            command.building,
            command.room,
            command.rack,
        )
        return RackCapacityReport(rack, equipment)

    def _require_room(
        self, tenant_id: TenantId, site_code: str, building_code: str, room_code: str
    ) -> Room:
        room = self._dcim_repository.find_room(tenant_id, site_code, building_code, room_code)
        if room is None:
            raise NotFoundError("DCIM room does not exist")
        return room

    def _require_selectable_room(
        self, tenant_id: TenantId, site_code: str, building_code: str, room_code: str
    ) -> Room:
        room = self._require_room(tenant_id, site_code, building_code, room_code)
        if not room.selectable():
            raise ValidationError("DCIM room is not active")
        return room

    def _require_rack(
        self,
        tenant_id: TenantId,
        site_code: str,
        building_code: str,
        room_code: str,
        rack_code: str,
    ) -> Rack:
        rack = self._dcim_repository.find_rack(
            tenant_id, site_code, building_code, room_code, rack_code
        )
        if rack is None:
            raise NotFoundError("DCIM rack does not exist")
        return rack

    def _validate_rack_context(self, command: DefineRackCommand, room: Room) -> None:
        if (
            command.floor is not None
            and room.floor_code is not None
            and command.floor.strip().upper() != room.floor_code.value
        ):
            raise ValidationError("rack floor does not match room floor")
        if command.floor is not None and room.floor_code is None:
            raise ValidationError("rack floor cannot be set when room has no floor")
        if command.floor is None and room.floor_code is not None:
            command_floor = room.floor_code.value
        else:
            command_floor = command.floor
        if room.floor_code is not None and command_floor is None:
            raise ValidationError("rack floor is mandatory when room has a floor")
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


class DcimCablingService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def define_patch_panel(self, command: DefinePatchPanelCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        rack = self._dcim_repository.find_rack(
            tenant_id,
            command.site,
            command.building,
            command.room,
            command.rack,
        )
        if rack is None:
            raise NotFoundError("rack must exist before defining a patch panel")
        patch_panel = PatchPanel.create(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
            rack=command.rack,
            code=command.patch_panel,
            rack_face=command.rack_face,
            u_position=command.u_position,
            u_height=command.u_height,
            port_count=command.port_count,
            connector=command.connector,
            medium=command.medium,
            label=command.label,
        )
        rack.assert_face_supported(patch_panel.rack_face)
        rack.assert_unit_interval(patch_panel.u_position, patch_panel.u_height)
        self._assert_patch_panel_interval_available(tenant_id, patch_panel)
        generated_ports = self._build_patch_panel_ports(command, tenant_id, patch_panel)
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_patch_panel(patch_panel)
            for port in generated_ports:
                self._dcim_repository.add_dcim_port(port)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.patch-panel.defined",
                    target_type="patch_panel",
                    target_id=patch_panel.code.value,
                    metadata={
                        "rack": rack.code.value,
                        "ports": patch_panel.port_count,
                        "medium": patch_panel.medium.value,
                        "connector": patch_panel.connector.value,
                    },
                )
            )
            unit_of_work.commit()
        payload = patch_panel.as_dict()
        payload["generated_ports"] = [port.endpoint.port_name.value for port in generated_ports]
        return payload

    def define_port(self, command: DefineDcimPortCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        owner_type = DcimPortOwnerType.from_value(command.owner_type)
        site, building, room = self._resolve_port_location(tenant_id, owner_type, command)
        port = DcimPort.create(
            tenant_id=tenant_id,
            owner_type=owner_type.value,
            owner_code=command.owner_code,
            port_name=command.port_name,
            site=site,
            building=building,
            room=room,
            connector=command.connector,
            medium=command.medium,
            enabled=command.enabled,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_dcim_port(port)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.port.defined",
                    target_type="dcim_port",
                    target_id=port.endpoint.key(),
                    metadata={"medium": port.medium.value, "connector": port.connector.value},
                )
            )
            unit_of_work.commit()
        return port.as_dict()

    def connect_cable(self, command: ConnectDcimCableCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        a_endpoint = DcimPortEndpoint.create(
            command.a_owner_type,
            command.a_owner_code,
            command.a_port_name,
        )
        b_endpoint = DcimPortEndpoint.create(
            command.b_owner_type,
            command.b_owner_code,
            command.b_port_name,
        )
        a_port = self._dcim_repository.find_dcim_port(tenant_id, a_endpoint)
        b_port = self._dcim_repository.find_dcim_port(tenant_id, b_endpoint)
        if a_port is None or b_port is None:
            raise NotFoundError("both cable endpoints must reference existing DCIM ports")
        path = self._build_path(command.path_segments)
        cable = DcimCable.create(
            tenant_id=tenant_id,
            cable_id=command.cable_id,
            a_endpoint=a_endpoint,
            b_endpoint=b_endpoint,
            medium=command.medium,
            status=command.status,
            path=path,
            length_m=command.length_m,
            label=command.label,
        )
        cable.assert_compatible_ports(a_port, b_port)
        self._assert_endpoint_available(tenant_id, a_endpoint)
        self._assert_endpoint_available(tenant_id, b_endpoint)
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_dcim_cable(cable)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.cable.connected",
                    target_type="dcim_cable",
                    target_id=cable.cable_id.value,
                    metadata={
                        "a_endpoint": cable.a_endpoint.key(),
                        "b_endpoint": cable.b_endpoint.key(),
                        "status": cable.status.value,
                        "medium": cable.medium.value,
                    },
                )
            )
            unit_of_work.commit()
        return cable.as_dict()

    def trace_cable(self, command: TraceDcimCableCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        cable = self._dcim_repository.find_dcim_cable(tenant_id, command.cable_id)
        if cable is None:
            raise NotFoundError("cable does not exist")
        a_port = self._dcim_repository.find_dcim_port(tenant_id, cable.a_endpoint)
        b_port = self._dcim_repository.find_dcim_port(tenant_id, cable.b_endpoint)
        if a_port is None or b_port is None:
            raise NotFoundError("cable references a missing endpoint port")
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.cable.traced",
                    target_type="dcim_cable",
                    target_id=cable.cable_id.value,
                    metadata={"trace": cable.human_trace()},
                )
            )
            unit_of_work.commit()
        payload = cable.as_dict()
        payload["a_port"] = a_port.as_dict()
        payload["b_port"] = b_port.as_dict()
        return payload

    def _resolve_port_location(
        self,
        tenant_id: TenantId,
        owner_type: DcimPortOwnerType,
        command: DefineDcimPortCommand,
    ) -> tuple[str, str, str]:
        if owner_type == DcimPortOwnerType.EQUIPMENT:
            equipment = self._dcim_repository.find_equipment(tenant_id, command.owner_code)
            if equipment is None:
                raise NotFoundError("equipment must exist before defining an equipment port")
            location = equipment.location
            return location.site_code.value, location.building_code.value, location.room_code.value
        if not command.site or not command.building or not command.room:
            raise ValidationError("site, building and room are mandatory for patch panel ports")
        existing = self._find_patch_panel_by_code(
            tenant_id,
            command.site,
            command.building,
            command.room,
            command.owner_code,
        )
        if existing is None:
            raise NotFoundError("patch panel must exist before defining a patch panel port")
        return existing.site_code.value, existing.building_code.value, existing.room_code.value

    def _find_patch_panel_by_code(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        code: str,
    ) -> PatchPanel | None:
        racks = self._dcim_repository.list_racks_in_room(tenant_id, site, building, room)
        normalized = code.strip().upper()
        for rack in racks:
            panel = self._dcim_repository.find_patch_panel(
                tenant_id,
                site,
                building,
                room,
                rack.code.value,
                normalized,
            )
            if panel is not None:
                return panel
        return None

    def _assert_patch_panel_interval_available(
        self,
        tenant_id: TenantId,
        patch_panel: PatchPanel,
    ) -> None:
        occupied_units = patch_panel.occupied_units()
        for item in self._dcim_repository.list_equipment_in_rack(
            tenant_id,
            patch_panel.site_code.value,
            patch_panel.building_code.value,
            patch_panel.room_code.value,
            patch_panel.rack_code.value,
        ):
            if item.location.effective_rack_face() == patch_panel.rack_face and set(
                occupied_units
            ).intersection(item.location.occupied_units()):
                raise ConflictError("patch panel interval overlaps existing rack equipment")
        for existing in self._dcim_repository.list_patch_panels_in_rack(
            tenant_id,
            patch_panel.site_code.value,
            patch_panel.building_code.value,
            patch_panel.room_code.value,
            patch_panel.rack_code.value,
        ):
            if existing.overlaps(patch_panel.rack_face, occupied_units):
                raise ConflictError("patch panel interval overlaps existing patch panel")

    def _build_patch_panel_ports(
        self,
        command: DefinePatchPanelCommand,
        tenant_id: TenantId,
        patch_panel: PatchPanel,
    ) -> tuple[DcimPort, ...]:
        prefix = command.port_prefix.strip().upper()
        if not prefix or len(prefix) > 8:
            raise ValidationError("patch panel port prefix must contain 1 to 8 characters")
        return tuple(
            DcimPort.create(
                tenant_id=tenant_id,
                owner_type=DcimPortOwnerType.PATCH_PANEL.value,
                owner_code=patch_panel.code.value,
                port_name=f"{prefix}{index:02d}",
                site=patch_panel.site_code.value,
                building=patch_panel.building_code.value,
                room=patch_panel.room_code.value,
                connector=patch_panel.connector.value,
                medium=patch_panel.medium.value,
            )
            for index in range(1, patch_panel.port_count + 1)
        )

    def _build_path(self, path_segments: tuple[str, ...]) -> tuple[DcimCablePathSegment, ...]:
        return tuple(
            DcimCablePathSegment.create(index, label)
            for index, label in enumerate(path_segments, start=1)
        )

    def _assert_endpoint_available(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> None:
        existing = self._dcim_repository.find_active_dcim_cable_by_endpoint(tenant_id, endpoint)
        if existing is not None:
            raise ConflictError(
                f"endpoint {endpoint.key()} is already used by cable {existing.cable_id.value}"
            )


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

    def digital_twin(self, command: RenderDigitalTwinCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._dcim_repository.find_room(
            tenant_id, command.site, command.building, command.room
        )
        if room is None:
            raise NotFoundError("room does not exist")
        racks = self._dcim_repository.list_racks_in_room(
            tenant_id, command.site, command.building, command.room
        )
        equipment = self._dcim_repository.list_equipment_in_room(
            tenant_id, command.site, command.building, command.room
        )
        room_plan = RoomPlan2D.create(room, racks, equipment)
        rack_payloads: list[dict[str, object]] = []
        room_cables: dict[str, object] = {}
        port_count = 0
        patch_panel_count = 0
        circuit_count = 0
        reservation_count = 0
        cooling_zone_codes: set[str] = set()
        for rack in racks:
            rack_equipment = tuple(
                item
                for item in equipment
                if item.location.rack_code is not None
                and item.location.rack_code.value == rack.code.value
            )
            patch_panels = self._dcim_repository.list_patch_panels_in_rack(
                tenant_id,
                command.site,
                command.building,
                command.room,
                rack.code.value,
            )
            rack_ports = self._collect_rack_ports(tenant_id, rack_equipment, patch_panels)
            rack_cables = self._collect_cables_for_ports(tenant_id, rack_ports)
            for cable in rack_cables:
                room_cables[cable.cable_id.value] = cable.as_dict()
            circuits = self._dcim_repository.list_power_circuits_for_rack(
                tenant_id,
                command.site,
                command.building,
                command.room,
                rack.code.value,
            )
            reservations = self._dcim_repository.list_power_reservations_for_rack(
                tenant_id,
                command.site,
                command.building,
                command.room,
                rack.code.value,
            )
            cooling_zone = (
                self._dcim_repository.find_cooling_zone(
                    tenant_id,
                    command.site,
                    command.building,
                    command.room,
                    rack.zone_code.value,
                )
                if rack.zone_code is not None
                else None
            )
            if cooling_zone is not None:
                cooling_zone_codes.add(cooling_zone.zone_code.value)
            energy_cooling = RackEnergyCoolingReport(
                rack, circuits, reservations, cooling_zone
            ).as_dict()
            elevations = {
                face.value: RackElevation.create(rack, rack_equipment, face).as_dict()
                for face in rack.usable_faces
            }
            rack_payloads.append(
                {
                    "rack": self._rack_payload(rack),
                    "equipment": [item.as_dict() for item in rack_equipment],
                    "patch_panels": [panel.as_dict() for panel in patch_panels],
                    "ports": [port.as_dict() for port in rack_ports],
                    "cables": [cable.as_dict() for cable in rack_cables],
                    "power_circuits": [circuit.as_dict() for circuit in circuits],
                    "power_reservations": [item.as_dict() for item in reservations],
                    "energy_cooling": energy_cooling,
                    "elevations": elevations,
                }
            )
            port_count += len(rack_ports)
            patch_panel_count += len(patch_panels)
            circuit_count += len(circuits)
            reservation_count += len(reservations)
        floor_equipment = tuple(item for item in equipment if item.location.rack_code is None)
        payload: dict[str, object] = {
            "type": "dcim_digital_twin",
            "tenant_id": tenant_id.value,
            "site": room.site_code.value,
            "building": room.building_code.value,
            "floor": room.floor_code.value if room.floor_code else None,
            "room": room.code.value,
            "room_path": room.physical_path(),
            "summary": {
                "rack_count": len(racks),
                "equipment_count": len(equipment),
                "floor_equipment_count": len(floor_equipment),
                "patch_panel_count": patch_panel_count,
                "port_count": port_count,
                "cable_count": len(room_cables),
                "power_circuit_count": circuit_count,
                "power_reservation_count": reservation_count,
                "cooling_zone_count": len(cooling_zone_codes),
            },
            "room_plan": room_plan.as_dict(),
            "racks": rack_payloads,
            "floor_equipment": [item.as_dict() for item in floor_equipment],
            "cables": [room_cables[key] for key in sorted(room_cables)],
            "integrity": {
                "status": "ok",
                "source": "dcim_repository",
                "scope": "room",
            },
        }
        self._record_visualization_audit(
            tenant_id,
            command.actor,
            "dcim.digital-twin.rendered",
            "room",
            room.code.value,
            "json",
        )
        return payload

    def _collect_rack_ports(
        self,
        tenant_id: TenantId,
        equipment: tuple[Equipment, ...],
        patch_panels: tuple[PatchPanel, ...],
    ) -> tuple[DcimPort, ...]:
        ports: list[DcimPort] = []
        for item in equipment:
            ports.extend(
                self._dcim_repository.list_dcim_ports_by_owner(
                    tenant_id, DcimPortOwnerType.EQUIPMENT.value, item.asset_tag.value
                )
            )
        for panel in patch_panels:
            ports.extend(
                self._dcim_repository.list_dcim_ports_by_owner(
                    tenant_id, DcimPortOwnerType.PATCH_PANEL.value, panel.code.value
                )
            )
        return tuple(sorted(ports, key=lambda item: item.endpoint.key()))

    def _collect_cables_for_ports(
        self, tenant_id: TenantId, ports: tuple[DcimPort, ...]
    ) -> tuple[DcimCable, ...]:
        cables: dict[str, DcimCable] = {}
        for port in ports:
            for cable in self._dcim_repository.list_dcim_cables_by_endpoint(
                tenant_id, port.endpoint
            ):
                cables[cable.cable_id.value] = cable
        return tuple(cables[key] for key in sorted(cables))

    def _rack_payload(self, rack: Rack) -> dict[str, object]:
        payload = rack.as_capacity_seed()
        payload.update(
            {
                "tenant_id": rack.tenant_id.value,
                "site": rack.site_code.value,
                "building": rack.building_code.value,
                "floor": rack.floor_code.value if rack.floor_code else None,
                "room": rack.room_code.value,
                "zone": rack.zone_code.value if rack.zone_code else None,
                "row": rack.row,
                "column": rack.column,
                "coordinates": rack.coordinates.as_dict() if rack.coordinates else None,
            }
        )
        return payload

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


class DcimEnvironmentService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def define_power_device(self, command: DefinePowerDeviceCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._dcim_repository.find_room(
            tenant_id, command.site, command.building, command.room
        )
        if room is None:
            raise NotFoundError("room must exist before defining a power device")
        if command.rack is not None:
            rack = self._dcim_repository.find_rack(
                tenant_id, command.site, command.building, command.room, command.rack
            )
            if rack is None:
                raise NotFoundError("rack must exist before defining a rack power device")
        device = PowerDevice.create(
            tenant_id=tenant_id,
            code=command.code,
            kind=command.kind,
            site=command.site,
            building=command.building,
            room=command.room,
            rack=command.rack,
            side=command.side,
            capacity_watts=command.capacity_watts,
            derating_percent=command.derating_percent,
            input_source=command.input_source,
            output_voltage=command.output_voltage,
            label=command.label,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_power_device(device)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.power-device.defined",
                    target_type="power_device",
                    target_id=device.code.value,
                    metadata=device.as_dict(),
                )
            )
            unit_of_work.commit()
        return device.as_dict()

    def define_power_circuit(self, command: DefinePowerCircuitCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        source = self._dcim_repository.find_power_device(tenant_id, command.source_device)
        if source is None:
            raise NotFoundError("source power device must exist before defining a circuit")
        rack = self._dcim_repository.find_rack(
            tenant_id, command.site, command.building, command.room, command.rack
        )
        if rack is None:
            raise NotFoundError("rack must exist before defining a power circuit")
        circuit = PowerCircuit.create(
            tenant_id=tenant_id,
            circuit_id=command.circuit_id,
            source_device_code=source.code.value,
            site=command.site,
            building=command.building,
            room=command.room,
            rack=command.rack,
            side=command.side,
            capacity_watts=command.capacity_watts,
            breaker_rating_amps=command.breaker_rating_amps,
            redundancy_group=command.redundancy_group,
            label=command.label,
        )
        if source.side is not None and source.side != circuit.side:
            raise ValidationError("power circuit side must match the source power device side")
        if source.site_code != circuit.site_code or source.building_code != circuit.building_code:
            raise ValidationError("power circuit source must be in the same site and building")
        if source.room_code != circuit.room_code:
            raise ValidationError("power circuit source must be in the same room")
        allocated = sum(
            item.capacity_watts
            for item in self._dcim_repository.list_power_circuits_by_source(
                tenant_id, source.code.value
            )
        )
        if allocated + circuit.capacity_watts > source.derated_capacity_watts:
            raise ConflictError("power circuit allocation exceeds source derated capacity")
        if rack.power_capacity_watts is not None:
            rack_capacity = sum(
                item.capacity_watts
                for item in self._dcim_repository.list_power_circuits_for_rack(
                    tenant_id, command.site, command.building, command.room, command.rack
                )
            )
            if rack_capacity + circuit.capacity_watts > rack.power_capacity_watts:
                raise ConflictError("power circuit allocation exceeds rack power capacity")
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_power_circuit(circuit)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.power-circuit.defined",
                    target_type="power_circuit",
                    target_id=circuit.circuit_id.value,
                    metadata=circuit.as_dict(),
                )
            )
            unit_of_work.commit()
        return circuit.as_dict()

    def define_cooling_zone(self, command: DefineCoolingZoneCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        zone = self._dcim_repository.find_zone(
            tenant_id, command.site, command.building, command.room, command.zone
        )
        if zone is None:
            raise NotFoundError("room zone must exist before defining a cooling zone")
        cooling_zone = CoolingZone.create(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
            zone=command.zone,
            role=command.role,
            cooling_capacity_watts=command.cooling_capacity_watts,
            supply_temperature_c=command.supply_temperature_c,
            return_temperature_c=command.return_temperature_c,
            label=command.label,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_cooling_zone(cooling_zone)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.cooling-zone.defined",
                    target_type="cooling_zone",
                    target_id=cooling_zone.zone_code.value,
                    metadata=cooling_zone.as_dict(),
                )
            )
            unit_of_work.commit()
        return cooling_zone.as_dict()

    def reserve_equipment_power(self, command: ReserveEquipmentPowerCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        equipment = self._dcim_repository.find_equipment(tenant_id, command.asset_tag)
        if equipment is None:
            raise NotFoundError("equipment must exist before reserving power")
        if equipment.location.rack_code is None:
            raise ValidationError("equipment must be rack-mounted before reserving rack power")
        circuit = self._dcim_repository.find_power_circuit(tenant_id, command.circuit_id)
        if circuit is None:
            raise NotFoundError("power circuit must exist before reserving power")
        if circuit.rack_code != equipment.location.rack_code:
            raise ValidationError("power reservation circuit must target the equipment rack")
        reservation = RackPowerReservation.create(
            tenant_id=tenant_id,
            asset_tag=equipment.asset_tag.value,
            circuit_id=circuit.circuit_id.value,
            side=circuit.side.value,
            site=equipment.location.site_code.value,
            building=equipment.location.building_code.value,
            room=equipment.location.room_code.value,
            rack=equipment.location.rack_code.value,
            expected_watts=command.expected_watts,
            label=command.label,
        )
        self._assert_power_capacity(tenant_id, reservation, circuit)
        self._assert_cooling_capacity(tenant_id, reservation, equipment)
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_power_reservation(reservation)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.power-reservation.created",
                    target_type="equipment",
                    target_id=reservation.asset_tag.value,
                    metadata=reservation.as_dict(),
                )
            )
            unit_of_work.commit()
        return reservation.as_dict()

    def rack_energy_cooling_capacity(
        self,
        command: RackEnergyCoolingCapacityCommand,
    ) -> RackEnergyCoolingReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        rack = self._dcim_repository.find_rack(
            tenant_id, command.site, command.building, command.room, command.rack
        )
        if rack is None:
            raise NotFoundError("rack does not exist")
        cooling_zone = None
        if rack.zone_code is not None:
            cooling_zone = self._dcim_repository.find_cooling_zone(
                tenant_id, command.site, command.building, command.room, rack.zone_code.value
            )
        report = RackEnergyCoolingReport(
            rack=rack,
            circuits=self._dcim_repository.list_power_circuits_for_rack(
                tenant_id, command.site, command.building, command.room, command.rack
            ),
            reservations=self._dcim_repository.list_power_reservations_for_rack(
                tenant_id, command.site, command.building, command.room, command.rack
            ),
            cooling_zone=cooling_zone,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.energy-cooling-capacity.reported",
                    target_type="rack",
                    target_id=rack.code.value,
                    metadata={"rack": rack.code.value},
                )
            )
            unit_of_work.commit()
        return report

    def _assert_power_capacity(
        self,
        tenant_id: TenantId,
        reservation: RackPowerReservation,
        circuit: PowerCircuit,
    ) -> None:
        circuit_reservations = self._dcim_repository.list_power_reservations_for_circuit(
            tenant_id, circuit.circuit_id.value
        )
        circuit_load = sum(item.expected_watts for item in circuit_reservations)
        if circuit_load + reservation.expected_watts > circuit.capacity_watts:
            raise ConflictError("power reservation exceeds circuit capacity")
        rack = self._dcim_repository.find_rack(
            tenant_id,
            reservation.site_code.value,
            reservation.building_code.value,
            reservation.room_code.value,
            reservation.rack_code.value,
        )
        if rack is not None and rack.power_capacity_watts is not None:
            rack_reservations = self._dcim_repository.list_power_reservations_for_rack(
                tenant_id,
                reservation.site_code.value,
                reservation.building_code.value,
                reservation.room_code.value,
                reservation.rack_code.value,
            )
            rack_load = sum(item.expected_watts for item in rack_reservations)
            if rack_load + reservation.expected_watts > rack.power_capacity_watts:
                raise ConflictError("power reservation exceeds rack declared power capacity")

    def _assert_cooling_capacity(
        self,
        tenant_id: TenantId,
        reservation: RackPowerReservation,
        equipment: Equipment,
    ) -> None:
        if equipment.location.zone_code is None:
            return
        cooling_zone = self._dcim_repository.find_cooling_zone(
            tenant_id,
            equipment.location.site_code.value,
            equipment.location.building_code.value,
            equipment.location.room_code.value,
            equipment.location.zone_code.value,
        )
        if cooling_zone is None:
            return
        zone_load = self._zone_power_load(tenant_id, cooling_zone)
        if zone_load + reservation.expected_watts > cooling_zone.cooling_capacity_watts:
            raise ConflictError("power reservation exceeds cooling zone capacity")

    def _zone_power_load(self, tenant_id: TenantId, cooling_zone: CoolingZone) -> int:
        total = 0
        for rack in self._dcim_repository.list_racks_in_room(
            tenant_id,
            cooling_zone.site_code.value,
            cooling_zone.building_code.value,
            cooling_zone.room_code.value,
        ):
            if rack.zone_code != cooling_zone.zone_code:
                continue
            total += sum(
                item.expected_watts
                for item in self._dcim_repository.list_power_reservations_for_rack(
                    tenant_id,
                    rack.site_code.value,
                    rack.building_code.value,
                    rack.room_code.value,
                    rack.code.value,
                )
            )
        return total


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
        edition_guard: EditionRuntimeGuard | None = None,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._edition_guard = edition_guard

    def locate_equipment(self, command: LocateEquipmentCommand) -> Equipment:
        tenant_id = TenantId.from_value(command.tenant_id)
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            existing = self._dcim_repository.find_equipment(tenant_id, command.asset_tag)
            if existing is None:
                self._edition_guard.require_quota(
                    tenant_id,
                    QuotaResource.EQUIPMENT,
                    1,
                    command.actor,
                    "equipment",
                    command.asset_tag,
                )
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
        if (
            command.floor is not None
            and rack.floor_code is not None
            and command.floor.strip().upper() != rack.floor_code.value
        ):
            raise ValidationError("rack floor does not match equipment location")
        if (
            command.zone is not None
            and rack.zone_code is not None
            and command.zone.strip().upper() != rack.zone_code.value
        ):
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
