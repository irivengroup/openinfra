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
    TransactionManager,
    UnitOfWork,
)
from openinfra.domain.access_policy import AccessPolicyRule
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
from openinfra.domain.dcim import Building, Equipment, EquipmentLocation, Rack, Room, Site
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
            "rooms": {},
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
                    "rooms",
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

    def add_room(self, room: Room) -> None:
        key = self._key(
            room.tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
        )
        self._put_unique("rooms", key, self._room_to_dict(room))

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

    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        key = self._key(
            tenant_id,
            Code.from_value(site).value,
            Code.from_value(building).value,
            Code.from_value(room).value,
        )
        item = self._store.data["rooms"].get(key)
        return self._room_from_dict(item) if item else None

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
        }

    def _site_from_dict(self, value: dict[str, Any]) -> Site:
        return Site(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            country=value["country"],
            city=value["city"],
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
        }

    def _room_from_dict(self, value: dict[str, Any]) -> Room:
        return Room(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
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


class JsonAuditRepository(AuditRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def append(self, event: AuditEvent) -> None:
        self._store.data["audit_events"].append(self._event_to_dict(event))
        self._store.mark_dirty()

    def list_events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._event_from_dict(value) for value in self._store.data["audit_events"])

    def _event_to_dict(self, event: AuditEvent) -> dict[str, Any]:
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
        }

    def _event_from_dict(self, value: dict[str, Any]) -> AuditEvent:
        return AuditEvent(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            actor=value["actor"],
            action=value["action"],
            target_type=value["target_type"],
            target_id=value["target_id"],
            severity=Severity(value["severity"]),
            created_at=datetime.fromisoformat(value["created_at"]),
            metadata=value["metadata"],
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
        self._dcim_repository.add_room(
            Room.create(
                tenant_id,
                "PAR1",
                "BAT-A",
                "MMR1",
                "Main Meet-Me Room",
                rows=("A", "B", "C"),
                columns=("01", "02", "12"),
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
            )
        )


class IterableSerializer:
    def to_json_array(self, values: Iterable[dict[str, Any]]) -> str:
        return json.dumps(list(values), indent=2, sort_keys=True)
