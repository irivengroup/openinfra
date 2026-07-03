from __future__ import annotations

import ipaddress
import json
import os
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from openinfra.application.ports import (
    AccessPolicyRepository,
    AccessPolicyRulePage,
    AuditRepository,
    DcimRepository,
    IdentityRepository,
    IpamRepository,
    ReadinessProbe,
    ReadinessStatus,
    SchemaStatusProvider,
    SecurityRepository,
    SecurityTokenPage,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
    UnitOfWork,
)
from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.audit import (
    AuditEventFilter,
    AuditEventPage,
    AuditEventRecord,
    AuditIntegrityHasher,
    AuditIntegrityReport,
)
from openinfra.domain.common import (
    AuditEvent,
    Code,
    ConflictError,
    Coordinates3D,
    EntityId,
    Name,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import (
    Building,
    Equipment,
    EquipmentLocation,
    Floor,
    Rack,
    RackFace,
    Room,
    RoomZone,
    Site,
)
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
    IdentityUser,
)
from openinfra.domain.ipam import IpReservation, Prefix, Vrf
from openinfra.domain.security import ApiTokenCredential, Permission
from openinfra.domain.source_governance import SourceGovernanceRule, SourceGovernanceRulePage
from openinfra.domain.source_of_truth import (
    SourceObjectPage,
    SourceObjectSnapshot,
    SourceOfTruthObject,
    SourceRelation,
    SourceRelationPage,
)


@dataclass(slots=True)
class _JsonState:
    data: dict[str, Any]
    dirty: bool


class JsonDocumentStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._state = _JsonState(data=self._empty_state(), dirty=False)
        self._load()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def data(self) -> dict[str, Any]:
        return self._state.data

    def mark_dirty(self) -> None:
        self._state.dirty = True

    def flush(self) -> None:
        if not self._state.dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state.data, indent=2, sort_keys=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(self._path.parent),
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, self._path)
        self._state.dirty = False

    def snapshot(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._state.data))

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._state = _JsonState(data=snapshot, dirty=False)

    def _load(self) -> None:
        if not self._path.exists():
            self._state = _JsonState(data=self._empty_state(), dirty=True)
            self.flush()
            return
        loaded = json.loads(self._path.read_text(encoding="utf-8"))
        self._state = _JsonState(data=self._merge_with_empty(loaded), dirty=False)

    def _merge_with_empty(self, loaded: dict[str, Any]) -> dict[str, Any]:
        merged = self._empty_state()
        for key, value in loaded.items():
            if key in merged:
                merged[key] = value
        return merged

    def _empty_state(self) -> dict[str, Any]:
        return {
            "sites": {},
            "buildings": {},
            "floors": {},
            "rooms": {},
            "room_zones": {},
            "racks": {},
            "equipment": {},
            "vrfs": {},
            "prefixes": {},
            "ip_reservations": {},
            "audit_events": [],
            "security_tokens": {},
            "identity_users": {},
            "identity_groups": {},
            "identity_memberships": {},
            "access_policy_rules": {},
            "source_objects": {},
            "source_object_snapshots": [],
            "source_relations": {},
            "source_governance_rules": {},
        }


class JsonSchemaStatusProvider(SchemaStatusProvider):
    def status_as_dict(self) -> dict[str, object]:
        return {
            "backend": "json",
            "managed": False,
            "ready": True,
            "detail": "json backend does not require PostgreSQL schema migrations",
            "applied": [],
            "pending": [],
        }


class JsonReadinessProbe(ReadinessProbe):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def check(self) -> ReadinessStatus:
        with self._store.lock:
            collections_ready = all(
                key in self._store.data
                for key in (
                    "sites",
                    "buildings",
                    "floors",
                    "rooms",
                    "room_zones",
                    "racks",
                    "equipment",
                    "vrfs",
                    "prefixes",
                    "ip_reservations",
                    "audit_events",
                    "security_tokens",
                    "identity_users",
                    "identity_groups",
                    "identity_memberships",
                    "access_policy_rules",
                    "source_objects",
                    "source_object_snapshots",
                    "source_relations",
                )
            )
        detail = (
            "json document store is writable"
            if collections_ready
            else "json schema is incomplete"
        )
        return ReadinessStatus("json", collections_ready, detail)


class JsonUnitOfWork(UnitOfWork):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store
        self._snapshot: dict[str, Any] | None = None
        self._committed = False

    def __enter__(self) -> JsonUnitOfWork:
        self._store.lock.acquire()
        self._snapshot = self._store.snapshot()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._store.lock.release()

    def commit(self) -> None:
        self._store.mark_dirty()
        self._store.flush()
        self._committed = True

    def rollback(self) -> None:
        if self._snapshot is not None:
            self._store.restore(self._snapshot)
        self._committed = True


class JsonTransactionManager(TransactionManager):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def begin(self) -> JsonUnitOfWork:
        return JsonUnitOfWork(self._store)


class JsonDcimRepository(DcimRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def add_site(self, site: Site) -> None:
        key = self._key(site.tenant_id, site.code.value)
        self._put_unique("sites", key, self._site_to_dict(site))

    def add_building(self, building: Building) -> None:
        key = self._key(building.tenant_id, building.site_code.value, building.code.value)
        self._put_unique("buildings", key, self._building_to_dict(building))

    def add_floor(self, floor: Floor) -> None:
        key = self._key(
            floor.tenant_id,
            floor.site_code.value,
            floor.building_code.value,
            floor.code.value,
        )
        self._put_unique("floors", key, self._floor_to_dict(floor))

    def add_room(self, room: Room) -> None:
        key = self._key(
            room.tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
        )
        self._put_unique("rooms", key, self._room_to_dict(room))

    def add_zone(self, zone: RoomZone) -> None:
        key = self._key(
            zone.tenant_id,
            zone.site_code.value,
            zone.building_code.value,
            zone.room_code.value,
            zone.code.value,
        )
        self._put_unique("room_zones", key, self._zone_to_dict(zone))

    def add_rack(self, rack: Rack) -> None:
        key = self._key(
            rack.tenant_id,
            rack.site_code.value,
            rack.building_code.value,
            rack.room_code.value,
            rack.code.value,
        )
        self._put_unique("racks", key, self._rack_to_dict(rack))

    def add_equipment(self, equipment: Equipment) -> None:
        key = self._key(equipment.tenant_id, equipment.asset_tag.value)
        self._store.data["equipment"][key] = self._equipment_to_dict(equipment)
        self._store.mark_dirty()

    def find_site(self, tenant_id: TenantId, site: str) -> Site | None:
        key = self._key(tenant_id, Code.from_value(site, "site code").value)
        item = self._store.data["sites"].get(key)
        return self._site_from_dict(item) if item else None

    def find_building(self, tenant_id: TenantId, site: str, building: str) -> Building | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
        )
        item = self._store.data["buildings"].get(key)
        return self._building_from_dict(item) if item else None

    def find_floor(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        floor: str,
    ) -> Floor | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
            Code.from_value(floor, "floor code").value,
        )
        item = self._store.data["floors"].get(key)
        return self._floor_from_dict(item) if item else None

    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        key = self._key(
            tenant_id,
            Code.from_value(site).value,
            Code.from_value(building).value,
            Code.from_value(room).value,
        )
        item = self._store.data["rooms"].get(key)
        return self._room_from_dict(item) if item else None

    def find_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> RoomZone | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
            Code.from_value(room, "room code").value,
            Code.from_value(zone, "zone code").value,
        )
        item = self._store.data["room_zones"].get(key)
        return self._zone_from_dict(item) if item else None

    def find_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> Rack | None:
        key = self._key(
            tenant_id,
            Code.from_value(site).value,
            Code.from_value(building).value,
            Code.from_value(room).value,
            Code.from_value(rack).value,
        )
        item = self._store.data["racks"].get(key)
        return self._rack_from_dict(item) if item else None

    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        key = self._key(tenant_id, Code.from_value(asset_tag).value)
        item = self._store.data["equipment"].get(key)
        return self._equipment_from_dict(item) if item else None

    def list_equipment_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[Equipment, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        normalized_rack = Code.from_value(rack, "rack code").value
        matching: list[Equipment] = []
        for value in self._store.data["equipment"].values():
            location = value.get("location", {})
            if (
                value.get("tenant_id") == tenant_id.value
                and location.get("site_code") == normalized_site
                and location.get("building_code") == normalized_building
                and location.get("room_code") == normalized_room
                and location.get("rack_code") == normalized_rack
            ):
                matching.append(self._equipment_from_dict(value))
        return tuple(sorted(matching, key=lambda item: item.asset_tag.value))

    def _put_unique(self, collection: str, key: str, value: dict[str, Any]) -> None:
        if key in self._store.data[collection]:
            raise ConflictError(f"duplicate {collection} key: {key}")
        self._store.data[collection][key] = value
        self._store.mark_dirty()

    def _key(self, tenant_id: TenantId, *parts: str) -> str:
        return ":".join((tenant_id.value, *parts))

    def _site_to_dict(self, site: Site) -> dict[str, Any]:
        return {
            "id": site.id.value,
            "tenant_id": site.tenant_id.value,
            "code": site.code.value,
            "name": site.name.value,
            "country": site.country,
            "city": site.city,
            "region": site.region,
        }

    def _site_from_dict(self, value: dict[str, Any]) -> Site:
        return Site(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            country=value["country"],
            city=value["city"],
            region=value.get("region", ""),
        )

    def _building_to_dict(self, building: Building) -> dict[str, Any]:
        return {
            "id": building.id.value,
            "tenant_id": building.tenant_id.value,
            "site_code": building.site_code.value,
            "code": building.code.value,
            "name": building.name.value,
        }

    def _building_from_dict(self, value: dict[str, Any]) -> Building:
        return Building(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
        )

    def _floor_to_dict(self, floor: Floor) -> dict[str, Any]:
        return {
            "id": floor.id.value,
            "tenant_id": floor.tenant_id.value,
            "site_code": floor.site_code.value,
            "building_code": floor.building_code.value,
            "code": floor.code.value,
            "name": floor.name.value,
            "level_index": floor.level_index,
        }

    def _floor_from_dict(self, value: dict[str, Any]) -> Floor:
        return Floor(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            level_index=int(value["level_index"]),
        )

    def _room_to_dict(self, room: Room) -> dict[str, Any]:
        return {
            "id": room.id.value,
            "tenant_id": room.tenant_id.value,
            "site_code": room.site_code.value,
            "building_code": room.building_code.value,
            "code": room.code.value,
            "name": room.name.value,
            "rows": list(room.rows),
            "columns": list(room.columns),
            "floor_code": room.floor_code.value if room.floor_code else None,
            "zone_codes": [zone.value for zone in room.zone_codes],
            "coordinates": room.coordinates.as_dict() if room.coordinates else None,
        }

    def _room_from_dict(self, value: dict[str, Any]) -> Room:
        coordinates = value.get("coordinates")
        return Room(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            rows=tuple(value["rows"]),
            columns=tuple(value["columns"]),
            floor_code=Code.from_value(value["floor_code"]) if value.get("floor_code") else None,
            zone_codes=tuple(Code.from_value(zone) for zone in value.get("zone_codes", [])),
            coordinates=Coordinates3D.from_values(**coordinates) if coordinates else None,
        )

    def _zone_to_dict(self, zone: RoomZone) -> dict[str, Any]:
        return {
            "id": zone.id.value,
            "tenant_id": zone.tenant_id.value,
            "site_code": zone.site_code.value,
            "building_code": zone.building_code.value,
            "floor_code": zone.floor_code.value,
            "room_code": zone.room_code.value,
            "code": zone.code.value,
            "name": zone.name.value,
            "rows": list(zone.rows),
            "columns": list(zone.columns),
        }

    def _zone_from_dict(self, value: dict[str, Any]) -> RoomZone:
        return RoomZone(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            floor_code=Code.from_value(value["floor_code"]),
            room_code=Code.from_value(value["room_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            rows=tuple(value["rows"]),
            columns=tuple(value["columns"]),
        )

    def _rack_to_dict(self, rack: Rack) -> dict[str, Any]:
        return {
            "id": rack.id.value,
            "tenant_id": rack.tenant_id.value,
            "site_code": rack.site_code.value,
            "building_code": rack.building_code.value,
            "room_code": rack.room_code.value,
            "code": rack.code.value,
            "row": rack.row,
            "column": rack.column,
            "units": rack.units,
            "coordinates": rack.coordinates.as_dict() if rack.coordinates else None,
            "floor_code": rack.floor_code.value if rack.floor_code else None,
            "zone_code": rack.zone_code.value if rack.zone_code else None,
            "usable_faces": [face.value for face in rack.usable_faces],
            "max_weight_kg": rack.max_weight_kg,
            "power_capacity_watts": rack.power_capacity_watts,
        }

    def _rack_from_dict(self, value: dict[str, Any]) -> Rack:
        coordinates = value["coordinates"]
        return Rack(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            room_code=Code.from_value(value["room_code"]),
            code=Code.from_value(value["code"]),
            row=value["row"],
            column=value["column"],
            units=int(value["units"]),
            coordinates=Coordinates3D.from_values(**coordinates) if coordinates else None,
            floor_code=Code.from_value(value["floor_code"]) if value.get("floor_code") else None,
            zone_code=Code.from_value(value["zone_code"]) if value.get("zone_code") else None,
            usable_faces=tuple(
                RackFace.from_value(face) or RackFace.FRONT
                for face in value.get("usable_faces", ["front"])
            ),
            max_weight_kg=(
                float(value["max_weight_kg"]) if value.get("max_weight_kg") is not None else None
            ),
            power_capacity_watts=(
                int(value["power_capacity_watts"])
                if value.get("power_capacity_watts") is not None
                else None
            ),
        )

    def _equipment_to_dict(self, equipment: Equipment) -> dict[str, Any]:
        location = equipment.location
        return {
            "id": equipment.id.value,
            "tenant_id": equipment.tenant_id.value,
            "asset_tag": equipment.asset_tag.value,
            "name": equipment.name.value,
            "location": {
                "site_code": location.site_code.value,
                "building_code": location.building_code.value,
                "room_code": location.room_code.value,
                "row": location.row,
                "column": location.column,
                "rack_code": location.rack_code.value if location.rack_code else None,
                "u_position": location.u_position,
                "coordinates": location.coordinates.as_dict() if location.coordinates else None,
                "floor_code": location.floor_code.value if location.floor_code else None,
                "zone_code": location.zone_code.value if location.zone_code else None,
                "rack_face": location.rack_face.value if location.rack_face else None,
                "u_height": location.u_height,
            },
        }

    def _equipment_from_dict(self, value: dict[str, Any]) -> Equipment:
        location = value["location"]
        coordinates = location["coordinates"]
        return Equipment(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            asset_tag=Code.from_value(value["asset_tag"]),
            name=Name.from_value(value["name"]),
            location=EquipmentLocation.create(
                site_code=location["site_code"],
                building_code=location["building_code"],
                room_code=location["room_code"],
                row=location["row"],
                column=location["column"],
                rack_code=location["rack_code"],
                u_position=location["u_position"],
                coordinates=Coordinates3D.from_values(**coordinates) if coordinates else None,
                floor_code=location.get("floor_code"),
                zone_code=location.get("zone_code"),
                rack_face=location.get("rack_face"),
                u_height=location.get("u_height"),
            ),
        )


class JsonIpamRepository(IpamRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def add_vrf(self, vrf: Vrf) -> None:
        key = self._key(vrf.tenant_id, vrf.name.value)
        if key in self._store.data["vrfs"]:
            raise ConflictError(f"duplicate vrf: {key}")
        self._store.data["vrfs"][key] = {
            "id": vrf.id.value,
            "tenant_id": vrf.tenant_id.value,
            "name": vrf.name.value,
            "route_distinguisher": vrf.route_distinguisher,
        }
        self._store.mark_dirty()

    def get_or_create_prefix(self, prefix: Prefix) -> Prefix:
        key = self._key(prefix.tenant_id, prefix.vrf_name.value, str(prefix.network))
        existing = self._store.data["prefixes"].get(key)
        if existing:
            return self._prefix_from_dict(existing)
        self._store.data["prefixes"][key] = self._prefix_to_dict(prefix)
        self._store.mark_dirty()
        return prefix

    def find_reservation_by_key(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        idempotency_key: str,
    ) -> IpReservation | None:
        normalized = self._key(tenant_id, Name.from_value(vrf_name).value, idempotency_key.strip())
        item = self._store.data["ip_reservations"].get(normalized)
        return self._reservation_from_dict(item) if item else None

    def list_reservations(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpReservation, ...]:
        matching: list[IpReservation] = []
        normalized_vrf = Name.from_value(vrf_name).value
        for value in self._store.data["ip_reservations"].values():
            if (
                value["tenant_id"] == tenant_id.value
                and value["vrf_name"] == normalized_vrf
                and value["prefix"] == prefix_cidr
            ):
                matching.append(self._reservation_from_dict(value))
        return tuple(matching)

    def add_reservation(self, reservation: IpReservation) -> None:
        key = self._key(
            reservation.tenant_id,
            reservation.vrf_name.value,
            reservation.idempotency_key,
        )
        if key in self._store.data["ip_reservations"]:
            raise ConflictError(f"duplicate ip idempotency key: {key}")
        for value in self._store.data["ip_reservations"].values():
            if (
                value["tenant_id"] == reservation.tenant_id.value
                and value["vrf_name"] == reservation.vrf_name.value
                and value["address"] == str(reservation.address)
            ):
                raise ConflictError(f"duplicate ip address: {reservation.address}")
        self._store.data["ip_reservations"][key] = self._reservation_to_dict(reservation)
        self._store.mark_dirty()

    def _key(self, tenant_id: TenantId, *parts: str) -> str:
        return ":".join((tenant_id.value, *parts))

    def _prefix_to_dict(self, prefix: Prefix) -> dict[str, Any]:
        return {
            "id": prefix.id.value,
            "tenant_id": prefix.tenant_id.value,
            "vrf_name": prefix.vrf_name.value,
            "network": str(prefix.network),
            "description": prefix.description,
        }

    def _prefix_from_dict(self, value: dict[str, Any]) -> Prefix:
        return Prefix(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            vrf_name=Name.from_value(value["vrf_name"]),
            network=ipaddress.ip_network(value["network"], strict=True),
            description=value["description"],
        )

    def _reservation_to_dict(self, reservation: IpReservation) -> dict[str, Any]:
        return {
            "id": reservation.id.value,
            "tenant_id": reservation.tenant_id.value,
            "vrf_name": reservation.vrf_name.value,
            "prefix": reservation.prefix,
            "address": str(reservation.address),
            "hostname": reservation.hostname,
            "idempotency_key": reservation.idempotency_key,
        }

    def _reservation_from_dict(self, value: dict[str, Any]) -> IpReservation:
        prefix = Prefix.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["prefix"],
        )
        reservation = IpReservation.create(
            tenant_id=TenantId.from_value(value["tenant_id"]),
            vrf_name=value["vrf_name"],
            prefix=prefix,
            address=value["address"],
            hostname=value["hostname"],
            idempotency_key=value["idempotency_key"],
        )
        return IpReservation(
            id=EntityId.from_value(value["id"]),
            tenant_id=reservation.tenant_id,
            vrf_name=reservation.vrf_name,
            prefix=reservation.prefix,
            address=reservation.address,
            hostname=reservation.hostname,
            idempotency_key=reservation.idempotency_key,
        )


class JsonIdentityRepository(IdentityRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_user(self, user: IdentityUser) -> None:
        key = self._user_key(user.tenant_id, user.username)
        previous = self._store.data["identity_users"].get(key, {})
        payload = self._user_to_dict(user)
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["identity_users"][key] = payload
        self._store.mark_dirty()

    def upsert_group(self, group: IdentityGroup) -> None:
        key = self._group_key(group.tenant_id, group.name)
        previous = self._store.data["identity_groups"].get(key, {})
        payload = self._group_to_dict(group)
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["identity_groups"][key] = payload
        self._store.mark_dirty()

    def add_membership(self, membership: GroupMembership) -> None:
        user_key = self._user_key(membership.tenant_id, membership.username)
        group_key = self._group_key(membership.tenant_id, membership.group_name)
        if user_key not in self._store.data["identity_users"]:
            raise ValidationError("identity user must exist before group membership")
        if group_key not in self._store.data["identity_groups"]:
            raise ValidationError("identity group must exist before group membership")
        membership_key = self._membership_key(
            membership.tenant_id,
            membership.username,
            membership.group_name,
        )
        self._store.data["identity_memberships"][membership_key] = membership.as_dict()
        self._store.mark_dirty()

    def grant_user_role(self, tenant_id: TenantId, username: str, role: str) -> bool:
        key = self._user_key(tenant_id, username)
        value = self._store.data["identity_users"].get(key)
        if value is None:
            raise ValidationError("identity user must exist before granting a role")
        role_name = IdentityRoleSet.from_names((role,))[0].name
        roles = set(str(item) for item in value.get("roles", []))
        changed = role_name not in roles
        roles.add(role_name)
        value["roles"] = sorted(roles)
        self._store.mark_dirty()
        return changed

    def grant_group_role(self, tenant_id: TenantId, group_name: str, role: str) -> bool:
        key = self._group_key(tenant_id, group_name)
        value = self._store.data["identity_groups"].get(key)
        if value is None:
            raise ValidationError("identity group must exist before granting a role")
        role_name = IdentityRoleSet.from_names((role,))[0].name
        roles = set(str(item) for item in value.get("roles", []))
        changed = role_name not in roles
        roles.add(role_name)
        value["roles"] = sorted(roles)
        self._store.mark_dirty()
        return changed

    def effective_identity_for_subject(
        self,
        tenant_id: TenantId,
        subject: str,
    ) -> EffectiveIdentity:
        username = IdentitySubject.normalize(subject)
        user_value = self._store.data["identity_users"].get(self._user_key(tenant_id, username))
        if user_value is None:
            return EffectiveIdentity.empty(tenant_id, username)
        user = self._user_from_dict(user_value)
        group_names: list[str] = []
        group_roles: list[str] = []
        for value in self._store.data["identity_memberships"].values():
            if value.get("tenant_id") != tenant_id.value or value.get("username") != username:
                continue
            group_key = self._group_key(tenant_id, str(value["group_name"]))
            group_value = self._store.data["identity_groups"].get(group_key)
            if group_value is not None and bool(group_value.get("active", True)):
                group_names.append(str(group_value["name"]))
                group_roles.extend(str(role) for role in group_value.get("roles", []))
        return EffectiveIdentity.from_parts(user, tuple(group_names), tuple(group_roles))

    def _user_key(self, tenant_id: TenantId, username: str) -> str:
        return ":".join((tenant_id.value, IdentitySubject.normalize(username)))

    def _group_key(self, tenant_id: TenantId, group_name: str) -> str:
        return ":".join((tenant_id.value, IdentityGroupName.normalize(group_name)))

    def _membership_key(self, tenant_id: TenantId, username: str, group_name: str) -> str:
        return ":".join((tenant_id.value, username, group_name))

    def _user_to_dict(self, user: IdentityUser) -> dict[str, Any]:
        return user.as_dict()

    def _group_to_dict(self, group: IdentityGroup) -> dict[str, Any]:
        return group.as_dict()

    def _user_from_dict(self, value: dict[str, Any]) -> IdentityUser:
        return IdentityUser.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            username=value["username"],
            display_name=value["display_name"],
            email=value.get("email"),
            roles=tuple(value.get("roles", [])),
            active=bool(value.get("active", True)),
            created_at=self._parse_datetime(value["created_at"]),
        )

    def _group_from_dict(self, value: dict[str, Any]) -> IdentityGroup:
        return IdentityGroup.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=value["name"],
            display_name=value["display_name"],
            roles=tuple(value.get("roles", [])),
            active=bool(value.get("active", True)),
            created_at=self._parse_datetime(value["created_at"]),
        )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class JsonSecurityRepository(SecurityRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_token(self, credential: ApiTokenCredential) -> None:
        key = self._key(credential.tenant_id, credential.token_hash)
        previous = self._store.data["security_tokens"].get(key, {})
        payload = self._credential_to_dict(credential)
        if previous.get("last_used_at") is not None and credential.last_used_at is None:
            payload["last_used_at"] = previous["last_used_at"]
        if previous.get("use_count") is not None and credential.use_count == 0:
            payload["use_count"] = int(previous["use_count"])
        self._store.data["security_tokens"][key] = payload
        self._store.mark_dirty()

    def find_active_token_by_hash(
        self,
        tenant_id: TenantId,
        token_hash: str,
    ) -> ApiTokenCredential | None:
        key = self._key(tenant_id, token_hash)
        value = self._store.data["security_tokens"].get(key)
        if value is None:
            return None
        credential = self._credential_from_dict(value)
        return credential if credential.is_usable() else None

    def revoke_token(self, tenant_id: TenantId, token_hash: str, actor: str) -> bool:
        key = self._key(tenant_id, token_hash)
        value = self._store.data["security_tokens"].get(key)
        if value is None:
            return False
        credential = self._credential_from_dict(value)
        if credential.is_revoked():
            return False
        self._store.data["security_tokens"][key] = self._credential_to_dict(
            credential.revoked(actor)
        )
        self._store.mark_dirty()
        return True

    def list_tokens(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> SecurityTokenPage:
        try:
            start = int(pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if start < 0:
            raise ValidationError("pagination cursor must be positive")
        credentials = [
            self._credential_from_dict(value)
            for value in self._store.data["security_tokens"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if not include_inactive:
            credentials = [credential for credential in credentials if credential.is_usable()]
        credentials.sort(key=lambda item: (item.created_at.isoformat(), item.id.value))
        selected = tuple(credentials[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(credentials) else None
        return SecurityTokenPage(selected, next_cursor)

    def record_token_used(self, tenant_id: TenantId, token_hash: str) -> None:
        key = self._key(tenant_id, token_hash)
        value = self._store.data["security_tokens"].get(key)
        if value is not None:
            value["last_used_at"] = datetime.now(UTC).isoformat()
            value["use_count"] = int(value.get("use_count", 0)) + 1
            self._store.mark_dirty()

    def _key(self, tenant_id: TenantId, token_hash: str) -> str:
        return ":".join((tenant_id.value, token_hash))

    def _credential_to_dict(self, credential: ApiTokenCredential) -> dict[str, Any]:
        return {
            "id": credential.id.value,
            "tenant_id": credential.tenant_id.value,
            "subject": credential.subject,
            "token_hash": credential.token_hash,
            "token_prefix": credential.token_prefix,
            "roles": list(credential.role_names()),
            "active": credential.active,
            "created_at": credential.created_at.isoformat(),
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
            "revoked_at": credential.revoked_at.isoformat() if credential.revoked_at else None,
            "revoked_by": credential.revoked_by,
            "last_used_at": (
                credential.last_used_at.isoformat() if credential.last_used_at else None
            ),
            "use_count": credential.use_count,
        }

    def _credential_from_dict(self, value: dict[str, Any]) -> ApiTokenCredential:
        return ApiTokenCredential.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            subject=value["subject"],
            token_hash=value["token_hash"],
            token_prefix=value["token_prefix"],
            roles=tuple(value["roles"]),
            active=bool(value["active"]),
            created_at=self._parse_datetime(value["created_at"]),
            expires_at=self._parse_optional_datetime(value.get("expires_at")),
            revoked_at=self._parse_optional_datetime(value.get("revoked_at")),
            revoked_by=value.get("revoked_by"),
            last_used_at=self._parse_optional_datetime(value.get("last_used_at")),
            use_count=int(value.get("use_count", 0)),
        )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _parse_optional_datetime(self, value: object) -> datetime | None:
        if value is None:
            return None
        return self._parse_datetime(value)


class JsonAccessPolicyRepository(AccessPolicyRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_rule(self, rule: AccessPolicyRule) -> None:
        key = self._key(rule.tenant_id, rule.name)
        previous = self._store.data["access_policy_rules"].get(key, {})
        payload = rule.as_dict()
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["access_policy_rules"][key] = payload
        self._store.mark_dirty()

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> AccessPolicyRulePage:
        try:
            start = int(pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if start < 0:
            raise ValidationError("pagination cursor must be positive")
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["access_policy_rules"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if not include_inactive:
            rules = [rule for rule in rules if rule.active]
        rules.sort(key=lambda item: (item.name, item.id.value))
        selected = tuple(rules[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(rules) else None
        return AccessPolicyRulePage(selected, next_cursor)

    def find_active_rules_for_permission(
        self,
        tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[AccessPolicyRule, ...]:
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["access_policy_rules"].values()
            if value.get("tenant_id") == tenant_id.value
            and value.get("permission") == permission.value
            and bool(value.get("active", True))
        ]
        rules.sort(key=lambda item: (item.name, item.id.value))
        return tuple(rules)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        normalized_name = AccessPolicyRule.create(
            tenant_id,
            name,
            Permission.SCHEMA_READ,
            "allow",
        ).name
        key = self._key(tenant_id, normalized_name)
        value = self._store.data["access_policy_rules"].get(key)
        if value is None or bool(value.get("active")) is False:
            return False
        value["active"] = False
        self._store.mark_dirty()
        return True

    def _key(self, tenant_id: TenantId, name: str) -> str:
        return ":".join((tenant_id.value, name))

    def _rule_from_dict(self, value: dict[str, Any]) -> AccessPolicyRule:
        return AccessPolicyRule.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=value["name"],
            permission=value["permission"],
            effect=value["effect"],
            subjects=tuple(value.get("subjects", [])),
            roles=tuple(value.get("roles", [])),
            site_codes=tuple(value.get("site_codes", [])),
            environments=tuple(value.get("environments", [])),
            active=bool(value.get("active", True)),
            created_at=self._parse_datetime(value["created_at"]),
        )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class JsonSourceGovernanceRepository(SourceGovernanceRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_rule(self, rule: SourceGovernanceRule) -> None:
        key = self._key(rule.tenant_id, rule.name.value)
        previous = self._store.data["source_governance_rules"].get(key, {})
        payload = rule.as_dict()
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["source_governance_rules"][key] = payload
        self._store.mark_dirty()

    def find_rule(self, tenant_id: TenantId, name: str) -> SourceGovernanceRule | None:
        key = self._key(tenant_id, name.strip().lower())
        value = self._store.data["source_governance_rules"].get(key)
        return self._rule_from_dict(value) if value else None

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool = False,
        object_kind: str | None = None,
    ) -> SourceGovernanceRulePage:
        start = self._cursor_offset(pagination.cursor)
        normalized_kind = object_kind.strip().lower() if object_kind else None
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["source_governance_rules"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if not include_inactive:
            rules = [rule for rule in rules if rule.active]
        if normalized_kind:
            rules = [
                rule for rule in rules
                if rule.object_kind is None or rule.object_kind.value == normalized_kind
            ]
        rules.sort(key=lambda item: (-item.priority, item.name.value, item.id.value))
        selected = tuple(rules[start : start + pagination.limit])
        next_index = start + len(selected)
        return SourceGovernanceRulePage(
            selected,
            str(next_index) if next_index < len(rules) else None,
        )

    def find_active_rules_for_kind(
        self,
        tenant_id: TenantId,
        object_kind: str,
    ) -> tuple[SourceGovernanceRule, ...]:
        normalized_kind = object_kind.strip().lower()
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["source_governance_rules"].values()
            if value.get("tenant_id") == tenant_id.value and bool(value.get("active", True))
        ]
        rules = [
            rule for rule in rules
            if rule.object_kind is None or rule.object_kind.value == normalized_kind
        ]
        rules.sort(key=lambda item: (-item.priority, item.name.value, item.id.value))
        return tuple(rules)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        key = self._key(tenant_id, name.strip().lower())
        value = self._store.data["source_governance_rules"].get(key)
        if value is None or bool(value.get("active")) is False:
            return False
        value["active"] = False
        self._store.mark_dirty()
        return True

    def _cursor_offset(self, cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    def _key(self, tenant_id: TenantId, name: str) -> str:
        return ":".join((tenant_id.value, name))

    def _rule_from_dict(self, value: dict[str, Any]) -> SourceGovernanceRule:
        created_at = datetime.fromisoformat(value["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        object_kind = value.get("object_kind")
        return SourceGovernanceRule.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=value["name"],
            object_kind=None if object_kind in (None, "*") else str(object_kind),
            attribute_path=value["attribute_path"],
            authoritative_source=value["authoritative_source"],
            priority=int(value["priority"]),
            freshness_seconds=(
                int(value["freshness_seconds"])
                if value.get("freshness_seconds") is not None
                else None
            ),
            conflict_strategy=value["conflict_strategy"],
            active=bool(value.get("active", True)),
            created_at=created_at,
        )


class JsonAuditRepository(AuditRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store
        self._hasher = AuditIntegrityHasher()

    def append(self, event: AuditEvent) -> None:
        previous_hash = self._latest_hash(event.tenant_id)
        record = AuditEventRecord.create(event, previous_hash)
        self._store.data["audit_events"].append(self._record_to_dict(record))
        self._store.mark_dirty()

    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        try:
            start = int(event_filter.pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if start < 0:
            raise ValidationError("pagination cursor must be positive")
        records = [
            self._record_from_dict(value)
            for value in self._store.data["audit_events"]
            if value.get("tenant_id") == event_filter.tenant_id.value
        ]
        records = [record for record in records if self._matches(record, event_filter)]
        records.sort(
            key=lambda item: (item.event.created_at.isoformat(), item.event.id.value),
            reverse=True,
        )
        selected = tuple(records[start : start + event_filter.pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(records) else None
        return AuditEventPage(selected, next_cursor)

    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        if not 1 <= int(limit) <= 10_000:
            raise ValidationError("audit integrity limit must be between 1 and 10000")
        records = [
            self._record_from_dict(value)
            for value in self._store.data["audit_events"]
            if value.get("tenant_id") == tenant_id.value
        ]
        records.sort(key=lambda item: (item.event.created_at.isoformat(), item.event.id.value))
        selected = records[-int(limit) :]
        previous_hash = AuditIntegrityHasher.GENESIS_HASH
        checked = 0
        for record in selected:
            if record.previous_hash != previous_hash or not record.verifies():
                return AuditIntegrityReport(
                    tenant_id=tenant_id,
                    checked=checked + 1,
                    valid=False,
                    broken_record_id=record.event.id.value,
                    head_hash=previous_hash,
                )
            previous_hash = record.record_hash
            checked += 1
        return AuditIntegrityReport(
            tenant_id=tenant_id,
            checked=checked,
            valid=True,
            broken_record_id=None,
            head_hash=previous_hash,
        )

    def list_events(self) -> tuple[AuditEvent, ...]:
        return tuple(
            self._record_from_dict(value).event
            for value in self._store.data["audit_events"]
        )

    def _latest_hash(self, tenant_id: TenantId) -> str:
        records = [
            self._record_from_dict(value)
            for value in self._store.data["audit_events"]
            if value.get("tenant_id") == tenant_id.value
        ]
        if not records:
            return AuditIntegrityHasher.GENESIS_HASH
        records.sort(key=lambda item: (item.event.created_at.isoformat(), item.event.id.value))
        return records[-1].record_hash

    def _matches(self, record: AuditEventRecord, event_filter: AuditEventFilter) -> bool:
        event = record.event
        if event_filter.actor is not None and event.actor != event_filter.actor:
            return False
        if event_filter.action is not None and event.action != event_filter.action:
            return False
        if event_filter.target_type is not None and event.target_type != event_filter.target_type:
            return False
        if event_filter.severity is not None and event.severity != event_filter.severity:
            return False
        if event_filter.created_from is not None and event.created_at < event_filter.created_from:
            return False
        if event_filter.created_to is not None and event.created_at > event_filter.created_to:
            return False
        return True

    def _record_to_dict(self, record: AuditEventRecord) -> dict[str, Any]:
        event = record.event
        return {
            "id": event.id.value,
            "tenant_id": event.tenant_id.value,
            "actor": event.actor,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "severity": event.severity.value,
            "created_at": event.created_at.isoformat(),
            "metadata": event.metadata,
            "previous_hash": record.previous_hash,
            "record_hash": record.record_hash,
        }

    def _record_from_dict(self, value: dict[str, Any]) -> AuditEventRecord:
        event = self._event_from_dict(value)
        previous_hash = value.get("previous_hash", AuditIntegrityHasher.GENESIS_HASH)
        record_hash = value.get("record_hash")
        if record_hash is None:
            return AuditEventRecord.create(event, str(previous_hash))
        return AuditEventRecord.restore(event, str(previous_hash), str(record_hash))

    def _event_from_dict(self, value: dict[str, Any]) -> AuditEvent:
        created_at = datetime.fromisoformat(value["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return AuditEvent(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            actor=value["actor"],
            action=value["action"],
            target_type=value["target_type"],
            target_id=value["target_id"],
            severity=Severity(value["severity"]),
            created_at=created_at,
            metadata=value["metadata"],
        )


class JsonSourceOfTruthRepository(SourceOfTruthRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def create_object(
        self,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, object],
        tags: tuple[str, ...],
        source: str,
        actor: str,
    ) -> SourceOfTruthObject:
        source_object = SourceOfTruthObject.create(
            tenant_id=tenant_id,
            key=key,
            kind=kind,
            display_name=display_name,
            attributes=attributes,
            tags=tags,
            source=source,
        )
        self.upsert_object(source_object, actor)
        return source_object

    def upsert_object(self, source_object: SourceOfTruthObject, actor: str) -> None:
        key = self._key(source_object.tenant_id, source_object.key.value)
        self._store.data["source_objects"][key] = self._object_to_dict(source_object)
        self._store.data["source_object_snapshots"].append(
            self._snapshot_to_dict(SourceObjectSnapshot.create(source_object, actor))
        )
        self._store.mark_dirty()

    def find_object(self, tenant_id: TenantId, key: str) -> SourceOfTruthObject | None:
        item = self._store.data["source_objects"].get(
            self._key(tenant_id, key.strip().lower())
        )
        return self._object_from_dict(item) if item else None

    def list_objects(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        tag: str | None = None,
    ) -> SourceObjectPage:
        start = self._cursor_offset(pagination.cursor)
        normalized_kind = kind.strip().lower() if kind else None
        normalized_tag = tag.strip().lower() if tag else None
        objects = [
            self._object_from_dict(value)
            for value in self._store.data["source_objects"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if normalized_kind:
            objects = [item for item in objects if item.kind.value == normalized_kind]
        if normalized_tag:
            objects = [
                item for item in objects if normalized_tag in {tag.value for tag in item.tags}
            ]
        objects.sort(key=lambda item: item.key.value)
        selected = tuple(objects[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(objects) else None
        return SourceObjectPage(selected, next_cursor)

    def find_object_version(
        self,
        tenant_id: TenantId,
        key: str,
        version: int,
    ) -> SourceObjectSnapshot | None:
        normalized_key = key.strip().lower()
        for value in self._store.data["source_object_snapshots"]:
            if (
                value.get("tenant_id") == tenant_id.value
                and value.get("object_key") == normalized_key
                and int(value.get("version", 0)) == int(version)
            ):
                return self._snapshot_from_dict(value)
        return None

    def add_relation(self, relation: SourceRelation) -> None:
        key = self._key(relation.tenant_id, relation.id.value)
        self._store.data["source_relations"][key] = self._relation_to_dict(relation)
        self._store.mark_dirty()

    def list_relations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_key: str | None = None,
        target_key: str | None = None,
        relation_type: str | None = None,
    ) -> SourceRelationPage:
        start = self._cursor_offset(pagination.cursor)
        normalized_source = source_key.strip().lower() if source_key else None
        normalized_target = target_key.strip().lower() if target_key else None
        normalized_type = relation_type.strip().lower() if relation_type else None
        relations = [
            self._relation_from_dict(value)
            for value in self._store.data["source_relations"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if normalized_source:
            relations = [item for item in relations if item.source_key.value == normalized_source]
        if normalized_target:
            relations = [item for item in relations if item.target_key.value == normalized_target]
        if normalized_type:
            relations = [item for item in relations if item.relation_type.value == normalized_type]
        relations.sort(key=lambda item: (item.created_at.isoformat(), item.id.value), reverse=True)
        selected = tuple(relations[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(relations) else None
        return SourceRelationPage(selected, next_cursor)

    def _cursor_offset(self, cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    def _key(self, tenant_id: TenantId, *parts: str) -> str:
        return ":".join((tenant_id.value, *parts))

    def _object_to_dict(self, source_object: SourceOfTruthObject) -> dict[str, Any]:
        return source_object.as_dict()

    def _object_from_dict(self, value: dict[str, Any]) -> SourceOfTruthObject:
        created_at = datetime.fromisoformat(value["created_at"])
        updated_at = datetime.fromisoformat(value["updated_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return SourceOfTruthObject.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            key=value["key"],
            kind=value["kind"],
            display_name=value["display_name"],
            attributes=dict(value["attributes"]),
            tags=tuple(value["tags"]),
            source=value["source"],
            version=int(value["version"]),
            status=value["status"],
            created_at=created_at,
            updated_at=updated_at,
        )

    def _snapshot_to_dict(self, snapshot: SourceObjectSnapshot) -> dict[str, Any]:
        return snapshot.as_dict()

    def _snapshot_from_dict(self, value: dict[str, Any]) -> SourceObjectSnapshot:
        changed_at = datetime.fromisoformat(value["changed_at"])
        if changed_at.tzinfo is None:
            changed_at = changed_at.replace(tzinfo=UTC)
        return SourceObjectSnapshot.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            object_key=value["object_key"],
            object_id=EntityId.from_value(value["object_id"]),
            version=int(value["version"]),
            payload=dict(value["payload"]),
            changed_by=value["changed_by"],
            changed_at=changed_at,
        )

    def _relation_to_dict(self, relation: SourceRelation) -> dict[str, Any]:
        return relation.as_dict()

    def _relation_from_dict(self, value: dict[str, Any]) -> SourceRelation:
        valid_from = datetime.fromisoformat(value["valid_from"])
        created_at = datetime.fromisoformat(value["created_at"])
        valid_to = datetime.fromisoformat(value["valid_to"]) if value.get("valid_to") else None
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=UTC)
        if valid_to is not None and valid_to.tzinfo is None:
            valid_to = valid_to.replace(tzinfo=UTC)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return SourceRelation.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            relation_type=value["relation_type"],
            source_key=value["source_key"],
            target_key=value["target_key"],
            provenance=value["provenance"],
            valid_from=valid_from,
            valid_to=valid_to,
            active=bool(value["active"]),
            created_at=created_at,
        )


class SeedDataFactory:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._transaction_manager = transaction_manager

    def ensure_minimal_datacenter(self, tenant: str) -> None:
        tenant_id = TenantId.from_value(tenant)
        with self._transaction_manager.begin() as unit_of_work:
            self._add_if_missing(tenant_id)
            unit_of_work.commit()

    def _add_if_missing(self, tenant_id: TenantId) -> None:
        room = self._dcim_repository.find_room(tenant_id, "PAR1", "BAT-A", "MMR1")
        if room is not None:
            return
        self._dcim_repository.add_site(Site.create(tenant_id, "PAR1", "Paris 1", "FR", "Paris"))
        self._dcim_repository.add_building(
            Building.create(tenant_id, "PAR1", "BAT-A", "Building A")
        )
        self._dcim_repository.add_floor(
            Floor.create(tenant_id, "PAR1", "BAT-A", "F01", "First floor", 1)
        )
        self._dcim_repository.add_room(
            Room.create(
                tenant_id,
                "PAR1",
                "BAT-A",
                "MMR1",
                "Main Meet-Me Room",
                rows=("A", "B", "C"),
                columns=("01", "02", "12"),
                floor_code="F01",
            )
        )
        self._dcim_repository.add_rack(
            Rack.create(
                tenant_id,
                "PAR1",
                "BAT-A",
                "MMR1",
                "R42",
                "B",
                "12",
                42,
                Coordinates3D.from_values(12.0, 4.0, 0.0),
                floor_code="F01",
            )
        )


class IterableSerializer:
    def to_json_array(self, values: Iterable[dict[str, Any]]) -> str:
        return json.dumps(list(values), indent=2, sort_keys=True)
