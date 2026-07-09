from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import Code, Coordinates3D, EntityId, Name, TenantId, ValidationError


class DcimGridValidator:
    @staticmethod
    def normalized_unique_codes(values: tuple[str, ...], label: str) -> tuple[str, ...]:
        normalized = tuple(
            dict.fromkeys(
                Code.from_value(expanded_value, label).value
                for value in values
                for expanded_value in DcimGridValidator._expand_code_or_range(value, label)
            )
        )
        if not normalized:
            raise ValidationError(f"{label} must contain at least one value")
        if len(normalized) > 512:
            raise ValidationError(f"{label} range cannot exceed 512 generated values")
        return normalized

    @staticmethod
    def _expand_code_or_range(value: str, label: str) -> tuple[str, ...]:
        candidate = value.strip().upper()
        if not candidate:
            return ()
        if "-" not in candidate:
            return (candidate,)
        start, separator, end = candidate.partition("-")
        if not separator or not start or not end or "-" in end:
            return (candidate,)
        if start.isdigit() and end.isdigit():
            first = int(start)
            last = int(end)
            if first > last:
                raise ValidationError(f"{label} numeric range start must be <= end")
            width = max(len(start), len(end)) if start.startswith("0") or end.startswith("0") else 0
            return tuple(
                str(item).zfill(width) if width else str(item) for item in range(first, last + 1)
            )
        if len(start) == 1 and len(end) == 1 and start.isalpha() and end.isalpha():
            first = ord(start)
            last = ord(end)
            if first > last:
                raise ValidationError(f"{label} alpha range start must be <= end")
            return tuple(chr(item) for item in range(first, last + 1))
        return (candidate,)


class DcimLifecycleStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"

    @classmethod
    def from_value(
        cls, value: str | None, label: str = "DCIM lifecycle status"
    ) -> DcimLifecycleStatus:
        normalized = (value or cls.ACTIVE.value).strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(f"{label} must be active, suspended or retired") from exc

    def selectable(self) -> bool:
        return self == DcimLifecycleStatus.ACTIVE


class RackFace(StrEnum):
    FRONT = "front"
    REAR = "rear"

    @classmethod
    def from_value(cls, value: str | None, default: RackFace | None = None) -> RackFace | None:
        if value is None:
            return default
        normalized = value.strip().lower()
        for face in cls:
            if normalized == face.value:
                return face
        raise ValidationError("rack face must be either front or rear")


@dataclass(frozen=True, slots=True)
class Site:
    id: EntityId
    tenant_id: TenantId
    code: Code
    name: Name
    country: str
    city: str
    region: str = ""
    status: DcimLifecycleStatus = DcimLifecycleStatus.ACTIVE

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        name: str,
        country: str,
        city: str,
        region: str = "",
    ) -> Self:
        normalized_country = country.strip().upper()
        normalized_city = " ".join(city.strip().split())
        normalized_region = " ".join(region.strip().split())
        lifecycle_status = DcimLifecycleStatus.from_value(None, "site status")
        if len(normalized_country) != 2 or not normalized_country.isalpha():
            raise ValidationError("country must be an ISO-3166 alpha-2 code")
        if not normalized_city:
            raise ValidationError("site city is mandatory")
        if len(normalized_region) > 128:
            raise ValidationError("site region cannot exceed 128 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            code=Code.from_value(code, "site code"),
            name=Name.from_value(name, "site name"),
            country=normalized_country,
            city=normalized_city,
            region=normalized_region,
            status=lifecycle_status,
        )

    def update(
        self,
        *,
        name: str | None = None,
        country: str | None = None,
        city: str | None = None,
        region: str | None = None,
        status: str | None = None,
    ) -> Site:
        normalized_country = self.country if country is None else country.strip().upper()
        normalized_city = self.city if city is None else " ".join(city.strip().split())
        normalized_region = self.region if region is None else " ".join(region.strip().split())
        if len(normalized_country) != 2 or not normalized_country.isalpha():
            raise ValidationError("country must be an ISO-3166 alpha-2 code")
        if not normalized_city:
            raise ValidationError("site city is mandatory")
        if len(normalized_region) > 128:
            raise ValidationError("site region cannot exceed 128 characters")
        return Site(
            id=self.id,
            tenant_id=self.tenant_id,
            code=self.code,
            name=self.name if name is None else Name.from_value(name, "site name"),
            country=normalized_country,
            city=normalized_city,
            region=normalized_region,
            status=DcimLifecycleStatus.from_value(status, "site status") if status else self.status,
        )

    def retire(self) -> Site:
        return self.update(status=DcimLifecycleStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status.selectable()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "code": self.code.value,
            "name": self.name.value,
            "country": self.country,
            "city": self.city,
            "region": self.region,
            "status": self.status.value,
            "selectable": self.selectable(),
        }


@dataclass(frozen=True, slots=True)
class Building:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    code: Code
    name: Name
    status: DcimLifecycleStatus = DcimLifecycleStatus.ACTIVE

    @classmethod
    def create(cls, tenant_id: TenantId, site_code: str, code: str, name: str) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            code=Code.from_value(code, "building code"),
            name=Name.from_value(name, "building name"),
        )

    def update(self, *, name: str | None = None, status: str | None = None) -> Building:
        return Building(
            id=self.id,
            tenant_id=self.tenant_id,
            site_code=self.site_code,
            code=self.code,
            name=self.name if name is None else Name.from_value(name, "building name"),
            status=DcimLifecycleStatus.from_value(status, "building status")
            if status
            else self.status,
        )

    def retire(self) -> Building:
        return self.update(status=DcimLifecycleStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status.selectable()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "code": self.code.value,
            "name": self.name.value,
            "status": self.status.value,
            "selectable": self.selectable(),
        }


@dataclass(frozen=True, slots=True)
class Floor:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    code: Code
    name: Name
    level_index: int
    status: DcimLifecycleStatus = DcimLifecycleStatus.ACTIVE

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        building_code: str,
        code: str,
        name: str,
        level_index: int,
    ) -> Self:
        normalized_level = int(level_index)
        if not -20 <= normalized_level <= 300:
            raise ValidationError("floor level index must be between -20 and 300")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            code=Code.from_value(code, "floor code"),
            name=Name.from_value(name, "floor name"),
            level_index=normalized_level,
        )

    def update(
        self, *, name: str | None = None, level_index: int | None = None, status: str | None = None
    ) -> Floor:
        normalized_level = self.level_index if level_index is None else int(level_index)
        if not -20 <= normalized_level <= 300:
            raise ValidationError("floor level index must be between -20 and 300")
        return Floor(
            id=self.id,
            tenant_id=self.tenant_id,
            site_code=self.site_code,
            building_code=self.building_code,
            code=self.code,
            name=self.name if name is None else Name.from_value(name, "floor name"),
            level_index=normalized_level,
            status=DcimLifecycleStatus.from_value(status, "floor status")
            if status
            else self.status,
        )

    def retire(self) -> Floor:
        return self.update(status=DcimLifecycleStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status.selectable()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "code": self.code.value,
            "name": self.name.value,
            "level_index": self.level_index,
            "status": self.status.value,
            "selectable": self.selectable(),
        }


@dataclass(frozen=True, slots=True)
class Room:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    code: Code
    name: Name
    rows: tuple[str, ...]
    columns: tuple[str, ...]
    floor_code: Code | None = None
    zone_codes: tuple[Code, ...] = ()
    coordinates: Coordinates3D | None = None
    status: DcimLifecycleStatus = DcimLifecycleStatus.ACTIVE

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        building_code: str,
        code: str,
        name: str,
        rows: tuple[str, ...],
        columns: tuple[str, ...],
        floor_code: str | None = None,
        zone_codes: tuple[str, ...] = (),
        coordinates: Coordinates3D | None = None,
    ) -> Self:
        normalized_rows = DcimGridValidator.normalized_unique_codes(rows, "room row")
        normalized_columns = DcimGridValidator.normalized_unique_codes(columns, "room column")
        normalized_zones = tuple(Code.from_value(zone, "zone code") for zone in zone_codes)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            code=Code.from_value(code, "room code"),
            name=Name.from_value(name, "room name"),
            rows=normalized_rows,
            columns=normalized_columns,
            floor_code=Code.from_value(floor_code, "floor code") if floor_code else None,
            zone_codes=normalized_zones,
            coordinates=coordinates,
        )

    def update(
        self,
        *,
        name: str | None = None,
        rows: tuple[str, ...] | None = None,
        columns: tuple[str, ...] | None = None,
        status: str | None = None,
    ) -> Room:
        return Room(
            id=self.id,
            tenant_id=self.tenant_id,
            site_code=self.site_code,
            building_code=self.building_code,
            code=self.code,
            name=self.name if name is None else Name.from_value(name, "room name"),
            rows=self.rows
            if rows is None
            else DcimGridValidator.normalized_unique_codes(rows, "room row"),
            columns=(
                self.columns
                if columns is None
                else DcimGridValidator.normalized_unique_codes(columns, "room column")
            ),
            floor_code=self.floor_code,
            zone_codes=self.zone_codes,
            coordinates=self.coordinates,
            status=DcimLifecycleStatus.from_value(status, "room status") if status else self.status,
        )

    def retire(self) -> Room:
        return self.update(status=DcimLifecycleStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status.selectable()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "floor": self.floor_code.value if self.floor_code else None,
            "code": self.code.value,
            "name": self.name.value,
            "rows": list(self.rows),
            "columns": list(self.columns),
            "zones": [zone.value for zone in self.zone_codes],
            "status": self.status.value,
            "selectable": self.selectable(),
        }

    def assert_cell_exists(self, row: str, column: str) -> None:
        if Code.from_value(row, "room row").value not in self.rows:
            raise ValidationError(f"unknown room row: {row}")
        if Code.from_value(column, "room column").value not in self.columns:
            raise ValidationError(f"unknown room column: {column}")

    def assert_zone_known(self, zone_code: str | None) -> None:
        if zone_code is None:
            return
        normalized = Code.from_value(zone_code, "zone code")
        if normalized not in self.zone_codes:
            raise ValidationError(f"unknown room zone: {zone_code}")

    def physical_path(self) -> str:
        parts = [
            f"site={self.site_code.value}",
            f"building={self.building_code.value}",
        ]
        if self.floor_code:
            parts.append(f"floor={self.floor_code.value}")
        parts.append(f"room={self.code.value}")
        if self.coordinates:
            parts.append(
                f"xyz={self.coordinates.x:.2f}/{self.coordinates.y:.2f}/{self.coordinates.z:.2f}"
            )
        return " | ".join(parts)


@dataclass(frozen=True, slots=True)
class RoomZone:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    floor_code: Code
    room_code: Code
    code: Code
    name: Name
    rows: tuple[str, ...]
    columns: tuple[str, ...]
    status: DcimLifecycleStatus = DcimLifecycleStatus.ACTIVE

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        building_code: str,
        floor_code: str,
        room_code: str,
        code: str,
        name: str,
        rows: tuple[str, ...],
        columns: tuple[str, ...],
    ) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            floor_code=Code.from_value(floor_code, "floor code"),
            room_code=Code.from_value(room_code, "room code"),
            code=Code.from_value(code, "zone code"),
            name=Name.from_value(name, "zone name"),
            rows=DcimGridValidator.normalized_unique_codes(rows, "zone row"),
            columns=DcimGridValidator.normalized_unique_codes(columns, "zone column"),
        )

    def update(
        self,
        *,
        name: str | None = None,
        rows: tuple[str, ...] | None = None,
        columns: tuple[str, ...] | None = None,
        status: str | None = None,
    ) -> RoomZone:
        return RoomZone(
            id=self.id,
            tenant_id=self.tenant_id,
            site_code=self.site_code,
            building_code=self.building_code,
            floor_code=self.floor_code,
            room_code=self.room_code,
            code=self.code,
            name=self.name if name is None else Name.from_value(name, "zone name"),
            rows=self.rows
            if rows is None
            else DcimGridValidator.normalized_unique_codes(rows, "zone row"),
            columns=(
                self.columns
                if columns is None
                else DcimGridValidator.normalized_unique_codes(columns, "zone column")
            ),
            status=DcimLifecycleStatus.from_value(status, "zone status") if status else self.status,
        )

    def retire(self) -> RoomZone:
        return self.update(status=DcimLifecycleStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status.selectable()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "floor": self.floor_code.value,
            "room": self.room_code.value,
            "code": self.code.value,
            "name": self.name.value,
            "rows": list(self.rows),
            "columns": list(self.columns),
            "status": self.status.value,
            "selectable": self.selectable(),
        }

    def assert_within_room(self, room: Room) -> None:
        if room.floor_code is not None and room.floor_code != self.floor_code:
            raise ValidationError("zone floor does not match room floor")
        for row in self.rows:
            if row not in room.rows:
                raise ValidationError(f"zone row is outside room grid: {row}")
        for column in self.columns:
            if column not in room.columns:
                raise ValidationError(f"zone column is outside room grid: {column}")

    def assert_cell_exists(self, row: str, column: str) -> None:
        if Code.from_value(row, "zone row").value not in self.rows:
            raise ValidationError(f"unknown zone row: {row}")
        if Code.from_value(column, "zone column").value not in self.columns:
            raise ValidationError(f"unknown zone column: {column}")


@dataclass(frozen=True, slots=True)
class Rack:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    room_code: Code
    code: Code
    row: str
    column: str
    units: int
    coordinates: Coordinates3D | None
    floor_code: Code | None = None
    zone_code: Code | None = None
    usable_faces: tuple[RackFace, ...] = (RackFace.FRONT,)
    max_weight_kg: float | None = None
    power_capacity_watts: int | None = None
    status: DcimLifecycleStatus = DcimLifecycleStatus.ACTIVE

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        building_code: str,
        room_code: str,
        code: str,
        row: str,
        column: str,
        units: int,
        coordinates: Coordinates3D | None,
        floor_code: str | None = None,
        zone_code: str | None = None,
        usable_faces: tuple[str, ...] = ("front",),
        max_weight_kg: float | None = None,
        power_capacity_watts: int | None = None,
    ) -> Self:
        normalized_row = Code.from_value(row, "rack row").value
        normalized_column = Code.from_value(column, "rack column").value
        normalized_faces = cls._normalize_faces(usable_faces)
        normalized_weight = cls._normalize_weight(max_weight_kg)
        normalized_power = cls._normalize_power(power_capacity_watts)
        if not 1 <= int(units) <= 60:
            raise ValidationError("rack units must be between 1 and 60")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            room_code=Code.from_value(room_code, "room code"),
            code=Code.from_value(code, "rack code"),
            row=normalized_row,
            column=normalized_column,
            units=int(units),
            coordinates=coordinates,
            floor_code=Code.from_value(floor_code, "floor code") if floor_code else None,
            zone_code=Code.from_value(zone_code, "zone code") if zone_code else None,
            usable_faces=normalized_faces,
            max_weight_kg=normalized_weight,
            power_capacity_watts=normalized_power,
        )

    def update(
        self,
        *,
        row: str | None = None,
        column: str | None = None,
        units: int | None = None,
        usable_faces: tuple[str, ...] | None = None,
        max_weight_kg: float | None = None,
        power_capacity_watts: int | None = None,
        status: str | None = None,
    ) -> Rack:
        normalized_units = self.units if units is None else int(units)
        if not 1 <= normalized_units <= 60:
            raise ValidationError("rack units must be between 1 and 60")
        return Rack(
            id=self.id,
            tenant_id=self.tenant_id,
            site_code=self.site_code,
            building_code=self.building_code,
            room_code=self.room_code,
            code=self.code,
            row=self.row if row is None else Code.from_value(row, "rack row").value,
            column=self.column if column is None else Code.from_value(column, "rack column").value,
            units=normalized_units,
            coordinates=self.coordinates,
            floor_code=self.floor_code,
            zone_code=self.zone_code,
            usable_faces=self.usable_faces
            if usable_faces is None
            else self._normalize_faces(usable_faces),
            max_weight_kg=self.max_weight_kg
            if max_weight_kg is None
            else self._normalize_weight(max_weight_kg),
            power_capacity_watts=self.power_capacity_watts
            if power_capacity_watts is None
            else self._normalize_power(power_capacity_watts),
            status=DcimLifecycleStatus.from_value(status, "rack status") if status else self.status,
        )

    def retire(self) -> Rack:
        return self.update(status=DcimLifecycleStatus.RETIRED.value)

    def selectable(self) -> bool:
        return self.status.selectable()

    @classmethod
    def _normalize_faces(cls, values: tuple[str, ...]) -> tuple[RackFace, ...]:
        if not values:
            raise ValidationError("rack must expose at least one usable face")
        faces: list[RackFace] = []
        for value in values:
            face = RackFace.from_value(value)
            if face is not None and face not in faces:
                faces.append(face)
        if not faces:
            raise ValidationError("rack must expose at least one usable face")
        return tuple(faces)

    @classmethod
    def _normalize_weight(cls, value: float | None) -> float | None:
        if value is None:
            return None
        normalized = float(value)
        if not 1 <= normalized <= 10_000:
            raise ValidationError("rack max weight must be between 1 and 10000 kg")
        return normalized

    @classmethod
    def _normalize_power(cls, value: int | None) -> int | None:
        if value is None:
            return None
        normalized = int(value)
        if not 1 <= normalized <= 1_000_000:
            raise ValidationError("rack power capacity must be between 1 and 1000000 watts")
        return normalized

    def assert_face_supported(self, face: RackFace) -> None:
        if face not in self.usable_faces:
            raise ValidationError(
                f"rack face is not enabled on rack {self.code.value}: {face.value}"
            )

    def assert_unit_interval(self, start_u: int, height_u: int) -> None:
        if not 1 <= start_u <= self.units:
            raise ValidationError("rack unit position exceeds rack capacity")
        if not 1 <= height_u <= self.units:
            raise ValidationError("rack unit height exceeds rack capacity")
        if start_u + height_u - 1 > self.units:
            raise ValidationError("rack unit interval exceeds rack capacity")

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "floor": self.floor_code.value if self.floor_code else None,
            "room": self.room_code.value,
            "zone": self.zone_code.value if self.zone_code else None,
            "code": self.code.value,
            "rack": self.code.value,
            "row": self.row,
            "column": self.column,
            "units": self.units,
            "faces": [face.value for face in self.usable_faces],
            "max_weight_kg": self.max_weight_kg,
            "power_capacity_watts": self.power_capacity_watts,
            "status": self.status.value,
            "selectable": self.selectable(),
        }

    def as_capacity_seed(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "rack": self.code.value,
            "units": self.units,
            "faces": [face.value for face in self.usable_faces],
            "max_weight_kg": self.max_weight_kg,
            "power_capacity_watts": self.power_capacity_watts,
            "status": self.status.value,
            "selectable": self.selectable(),
        }


@dataclass(frozen=True, slots=True)
class EquipmentLocation:
    site_code: Code
    building_code: Code
    room_code: Code
    row: str
    column: str
    rack_code: Code | None
    u_position: int | None
    coordinates: Coordinates3D | None
    floor_code: Code | None = None
    zone_code: Code | None = None
    rack_face: RackFace | None = None
    u_height: int | None = None

    @classmethod
    def create(
        cls,
        site_code: str,
        building_code: str,
        room_code: str,
        row: str,
        column: str,
        rack_code: str | None = None,
        u_position: int | None = None,
        coordinates: Coordinates3D | None = None,
        floor_code: str | None = None,
        zone_code: str | None = None,
        rack_face: str | None = None,
        u_height: int | None = None,
    ) -> Self:
        normalized_row = Code.from_value(row, "equipment location row").value
        normalized_column = Code.from_value(column, "equipment location column").value
        normalized_u_position = int(u_position) if u_position is not None else None
        normalized_height = int(u_height) if u_height is not None else None
        normalized_face = RackFace.from_value(rack_face) if rack_face is not None else None
        if normalized_u_position is not None and not 1 <= normalized_u_position <= 60:
            raise ValidationError("rack unit position must be between 1 and 60")
        if normalized_height is not None and not 1 <= normalized_height <= 60:
            raise ValidationError("rack unit height must be between 1 and 60")
        if rack_code is None and normalized_u_position is not None:
            raise ValidationError("rack code is mandatory when a rack unit is provided")
        if rack_code is None and normalized_height is not None:
            raise ValidationError("rack code is mandatory when a rack unit height is provided")
        if rack_code is None and normalized_face is not None:
            raise ValidationError("rack code is mandatory when a rack face is provided")
        if normalized_height is not None and normalized_u_position is None:
            raise ValidationError(
                "rack unit position is mandatory when a rack unit height is provided"
            )
        if normalized_face is not None and normalized_u_position is None:
            raise ValidationError("rack unit position is mandatory when a rack face is provided")
        if normalized_u_position is not None and normalized_height is None:
            normalized_height = 1
        return cls(
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            room_code=Code.from_value(room_code, "room code"),
            row=normalized_row,
            column=normalized_column,
            rack_code=Code.from_value(rack_code, "rack code") if rack_code else None,
            u_position=normalized_u_position,
            coordinates=coordinates,
            floor_code=Code.from_value(floor_code, "floor code") if floor_code else None,
            zone_code=Code.from_value(zone_code, "zone code") if zone_code else None,
            rack_face=normalized_face,
            u_height=normalized_height,
        )

    def effective_rack_face(self) -> RackFace | None:
        if self.rack_code is None or self.u_position is None:
            return None
        return self.rack_face or RackFace.FRONT

    def effective_u_height(self) -> int | None:
        if self.rack_code is None or self.u_position is None:
            return None
        return self.u_height or 1

    def occupied_units(self) -> tuple[int, ...]:
        height = self.effective_u_height()
        if self.u_position is None or height is None:
            return ()
        return tuple(range(self.u_position, self.u_position + height))

    def overlaps(self, other: EquipmentLocation) -> bool:
        if self.rack_code is None or other.rack_code is None:
            return False
        if self.rack_code != other.rack_code:
            return False
        if self.effective_rack_face() != other.effective_rack_face():
            return False
        return bool(set(self.occupied_units()).intersection(other.occupied_units()))

    def human_readable(self) -> str:
        parts = [
            f"site={self.site_code.value}",
            f"building={self.building_code.value}",
        ]
        if self.floor_code:
            parts.append(f"floor={self.floor_code.value}")
        parts.extend(
            (
                f"room={self.room_code.value}",
                f"row={self.row}",
                f"column={self.column}",
            )
        )
        if self.zone_code:
            parts.append(f"zone={self.zone_code.value}")
        if self.rack_code:
            parts.append(f"rack={self.rack_code.value}")
        if self.u_position is not None:
            parts.append(f"U={self.u_position}")
        if self.rack_face:
            parts.append(f"face={self.rack_face.value}")
        if self.u_height is not None and self.u_height != 1:
            parts.append(f"height_u={self.u_height}")
        if self.coordinates:
            parts.append(
                f"xyz={self.coordinates.x:.2f}/{self.coordinates.y:.2f}/{self.coordinates.z:.2f}"
            )
        return " | ".join(parts)

    def as_dict(self) -> dict[str, object]:
        coordinates = self.coordinates.as_dict() if self.coordinates else None
        rack_face = self.effective_rack_face()
        return {
            "site": self.site_code.value,
            "building": self.building_code.value,
            "floor": self.floor_code.value if self.floor_code else None,
            "room": self.room_code.value,
            "row": self.row,
            "column": self.column,
            "zone": self.zone_code.value if self.zone_code else None,
            "rack": self.rack_code.value if self.rack_code else None,
            "u_position": self.u_position,
            "rack_face": rack_face.value if rack_face else None,
            "u_height": self.effective_u_height(),
            "coordinates": coordinates,
            "human_readable": self.human_readable(),
        }


@dataclass(frozen=True, slots=True)
class Equipment:
    id: EntityId
    tenant_id: TenantId
    asset_tag: Code
    name: Name
    location: EquipmentLocation

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        asset_tag: str,
        name: str,
        location: EquipmentLocation,
    ) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            asset_tag=Code.from_value(asset_tag, "asset tag"),
            name=Name.from_value(name, "equipment name"),
            location=location,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "asset_tag": self.asset_tag.value,
            "name": self.name.value,
            "location": self.location.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class RackCapacityReport:
    rack: Rack
    equipment: tuple[Equipment, ...]

    def as_dict(self) -> dict[str, object]:
        by_face: dict[str, dict[str, object]] = {}
        for face in self.rack.usable_faces:
            occupied_units: set[int] = set()
            mounted_items: list[dict[str, object]] = []
            for item in self.equipment:
                location = item.location
                if location.effective_rack_face() != face:
                    continue
                units = location.occupied_units()
                occupied_units.update(units)
                mounted_items.append(
                    {
                        "asset_tag": item.asset_tag.value,
                        "name": item.name.value,
                        "u_position": location.u_position,
                        "u_height": location.effective_u_height(),
                        "rack_face": face.value,
                        "units": list(units),
                    }
                )
            by_face[face.value] = {
                "used_units": sorted(occupied_units),
                "used_count": len(occupied_units),
                "free_count": self.rack.units - len(occupied_units),
                "occupancy_percent": round((len(occupied_units) / self.rack.units) * 100, 2),
                "equipment": mounted_items,
            }
        payload = self.rack.as_capacity_seed()
        payload["faces_capacity"] = by_face
        return payload


@dataclass(frozen=True, slots=True)
class RoomPlanCell:
    row: str
    column: str
    racks: tuple[Rack, ...]
    equipment: tuple[Equipment, ...]

    @property
    def occupied(self) -> bool:
        return bool(self.racks or self.equipment)

    @property
    def status(self) -> str:
        if self.racks and self.equipment:
            return "rack_occupied"
        if self.racks:
            return "rack_empty"
        if self.equipment:
            return "floor_occupied"
        return "empty"

    def as_dict(self) -> dict[str, object]:
        return {
            "row": self.row,
            "column": self.column,
            "status": self.status,
            "occupied": self.occupied,
            "rack_codes": [rack.code.value for rack in self.racks],
            "equipment": [
                {
                    "asset_tag": item.asset_tag.value,
                    "name": item.name.value,
                    "rack": item.location.rack_code.value if item.location.rack_code else None,
                    "rack_face": (
                        face.value
                        if (face := item.location.effective_rack_face()) is not None
                        else None
                    ),
                    "u_position": item.location.u_position,
                    "u_height": item.location.effective_u_height(),
                }
                for item in self.equipment
            ],
        }


@dataclass(frozen=True, slots=True)
class RoomPlan2D:
    room: Room
    racks: tuple[Rack, ...]
    equipment: tuple[Equipment, ...]

    @classmethod
    def create(
        cls,
        room: Room,
        racks: tuple[Rack, ...],
        equipment: tuple[Equipment, ...],
    ) -> Self:
        for rack in racks:
            if rack.room_code != room.code or rack.site_code != room.site_code:
                raise ValidationError("rack does not belong to the requested room plan")
            room.assert_cell_exists(rack.row, rack.column)
        for item in equipment:
            location = item.location
            if location.room_code != room.code or location.site_code != room.site_code:
                raise ValidationError("equipment does not belong to the requested room plan")
            room.assert_cell_exists(location.row, location.column)
        return cls(
            room,
            tuple(sorted(racks, key=lambda item: item.code.value)),
            tuple(sorted(equipment, key=lambda item: item.asset_tag.value)),
        )

    def cells(self) -> tuple[RoomPlanCell, ...]:
        result: list[RoomPlanCell] = []
        for row in self.room.rows:
            for column in self.room.columns:
                result.append(
                    RoomPlanCell(
                        row=row,
                        column=column,
                        racks=tuple(
                            rack for rack in self.racks if rack.row == row and rack.column == column
                        ),
                        equipment=tuple(
                            item
                            for item in self.equipment
                            if item.location.row == row and item.location.column == column
                        ),
                    )
                )
        return tuple(result)

    def as_dict(self) -> dict[str, object]:
        cells = self.cells()
        return {
            "type": "room_plan_2d",
            "tenant_id": self.room.tenant_id.value,
            "site": self.room.site_code.value,
            "building": self.room.building_code.value,
            "floor": self.room.floor_code.value if self.room.floor_code else None,
            "room": self.room.code.value,
            "rows": list(self.room.rows),
            "columns": list(self.room.columns),
            "coordinates": self.room.coordinates.as_dict() if self.room.coordinates else None,
            "rack_count": len(self.racks),
            "equipment_count": len(self.equipment),
            "grid": [cell.as_dict() for cell in cells],
        }

    def svg_document(self, cell_size: int = 90) -> str:
        size = int(cell_size)
        if not 48 <= size <= 180:
            raise ValidationError("room plan cell size must be between 48 and 180 pixels")
        margin = 60
        width = margin + len(self.room.columns) * size + 20
        height = margin + len(self.room.rows) * size + 40
        elements = [
            f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="OpenInfra room plan {html.escape(self.room.code.value)}" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
            '<rect width="100%" height="100%" fill="#fff"/>',
            f'<text x="20" y="28" font-size="16">Salle {html.escape(self.room.code.value)}</text>',
        ]
        for column_index, column in enumerate(self.room.columns):
            x = margin + column_index * size + size // 2
            elements.append(
                f'<text x="{x}" y="52" text-anchor="middle" font-size="12">'
                f"{html.escape(column)}</text>"
            )
        for row_index, row in enumerate(self.room.rows):
            y = margin + row_index * size + size // 2
            elements.append(
                f'<text x="36" y="{y}" text-anchor="middle" font-size="12">'
                f"{html.escape(row)}</text>"
            )
        for cell in self.cells():
            row_index = self.room.rows.index(cell.row)
            column_index = self.room.columns.index(cell.column)
            x = margin + column_index * size
            y = margin + row_index * size
            fill = "#e8f5e9" if cell.occupied else "#f8f8f8"
            label = ",".join(rack.code.value for rack in cell.racks) or str(len(cell.equipment))
            elements.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" '
                f'fill="{fill}" stroke="#444"/>'
            )
            elements.append(
                f'<text x="{x + size // 2}" y="{y + size // 2}" text-anchor="middle" '
                f'font-size="11">{html.escape(label)}</text>'
            )
        elements.append("</svg>")
        return "".join(elements)

    def html_document(self) -> str:
        rows = []
        for row in self.room.rows:
            cells = [cell for cell in self.cells() if cell.row == row]
            row_html = "".join(
                "<td>"
                + html.escape(cell.status)
                + "<br>"
                + html.escape(", ".join(rack.code.value for rack in cell.racks))
                + "<br>"
                + html.escape(", ".join(item.asset_tag.value for item in cell.equipment))
                + "</td>"
                for cell in cells
            )
            rows.append(f"<tr><th>{html.escape(row)}</th>{row_html}</tr>")
        header = "".join(f"<th>{html.escape(column)}</th>" for column in self.room.columns)
        return (
            '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            "<title>OpenInfra plan salle 2D</title></head><body>"
            f"<h1>Plan 2D — {html.escape(self.room.code.value)}</h1>"
            f"<p>{html.escape(self.room.physical_path())}</p>"
            f"<section>{self.svg_document()}</section>"
            f"<table><thead><tr><th>Ligne/Colonne</th>{header}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
            "</body></html>"
        )


@dataclass(frozen=True, slots=True)
class RackElevationUnit:
    u: int
    face: RackFace
    equipment: tuple[Equipment, ...]

    @property
    def occupied(self) -> bool:
        return bool(self.equipment)

    def as_dict(self) -> dict[str, object]:
        return {
            "u": self.u,
            "face": self.face.value,
            "occupied": self.occupied,
            "equipment": [
                {
                    "asset_tag": item.asset_tag.value,
                    "name": item.name.value,
                    "u_position": item.location.u_position,
                    "u_height": item.location.effective_u_height(),
                }
                for item in self.equipment
            ],
        }


@dataclass(frozen=True, slots=True)
class RackElevation:
    rack: Rack
    face: RackFace
    equipment: tuple[Equipment, ...]

    @classmethod
    def create(cls, rack: Rack, equipment: tuple[Equipment, ...], face: str | RackFace) -> Self:
        rack_face = face if isinstance(face, RackFace) else RackFace.from_value(face)
        if rack_face is None:
            raise ValidationError("rack elevation face is mandatory")
        rack.assert_face_supported(rack_face)
        filtered = tuple(
            sorted(
                (item for item in equipment if item.location.effective_rack_face() == rack_face),
                key=lambda item: (item.location.u_position or 0, item.asset_tag.value),
            )
        )
        return cls(rack, rack_face, filtered)

    def units(self) -> tuple[RackElevationUnit, ...]:
        result: list[RackElevationUnit] = []
        for unit in range(self.rack.units, 0, -1):
            mounted = tuple(
                item for item in self.equipment if unit in item.location.occupied_units()
            )
            result.append(RackElevationUnit(unit, self.face, mounted))
        return tuple(result)

    def as_dict(self) -> dict[str, object]:
        used_units = sorted(
            {unit for item in self.equipment for unit in item.location.occupied_units()}
        )
        return {
            "type": "rack_elevation",
            "tenant_id": self.rack.tenant_id.value,
            "site": self.rack.site_code.value,
            "building": self.rack.building_code.value,
            "floor": self.rack.floor_code.value if self.rack.floor_code else None,
            "room": self.rack.room_code.value,
            "zone": self.rack.zone_code.value if self.rack.zone_code else None,
            "rack": self.rack.code.value,
            "face": self.face.value,
            "units_total": self.rack.units,
            "used_units": used_units,
            "free_units": self.rack.units - len(used_units),
            "occupancy_percent": round((len(used_units) / self.rack.units) * 100, 2),
            "elevation": [unit.as_dict() for unit in self.units()],
        }

    def svg_document(self, unit_height: int = 22) -> str:
        height_per_unit = int(unit_height)
        if not 12 <= height_per_unit <= 48:
            raise ValidationError("rack elevation unit height must be between 12 and 48 pixels")
        width = 320
        top = 50
        height = top + self.rack.units * height_per_unit + 20
        elements = [
            f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="OpenInfra rack elevation {html.escape(self.rack.code.value)}" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
            '<rect width="100%" height="100%" fill="#fff"/>',
            (
                f'<text x="20" y="28" font-size="16">Rack '
                f"{html.escape(self.rack.code.value)} — {self.face.value}</text>"
            ),
        ]
        for index, unit in enumerate(self.units()):
            y = top + index * height_per_unit
            fill = "#e3f2fd" if unit.occupied else "#f8f8f8"
            label = ", ".join(item.asset_tag.value for item in unit.equipment)
            elements.append(
                f'<rect x="60" y="{y}" width="220" height="{height_per_unit}" '
                f'fill="{fill}" stroke="#444"/>'
            )
            elements.append(
                f'<text x="35" y="{y + height_per_unit - 5}" text-anchor="middle" '
                f'font-size="10">U{unit.u}</text>'
            )
            elements.append(
                f'<text x="70" y="{y + height_per_unit - 5}" font-size="10">'
                f"{html.escape(label)}</text>"
            )
        elements.append("</svg>")
        return "".join(elements)

    def html_document(self) -> str:
        rows = "".join(
            "<tr><td>"
            + str(unit.u)
            + "</td><td>"
            + html.escape(unit.face.value)
            + "</td><td>"
            + html.escape(", ".join(item.asset_tag.value for item in unit.equipment))
            + "</td></tr>"
            for unit in self.units()
        )
        return (
            '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            "<title>OpenInfra rack elevation</title></head><body>"
            f"<h1>Rack elevation — {html.escape(self.rack.code.value)} — {self.face.value}</h1>"
            f"<section>{self.svg_document()}</section>"
            "<table><thead><tr><th>U</th><th>Face</th><th>Équipement</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
            "</body></html>"
        )


class DcimCableMedium(StrEnum):
    COPPER = "copper"
    FIBER = "fiber"
    DAC = "dac"

    @classmethod
    def from_value(cls, value: str) -> DcimCableMedium:
        normalized = value.strip().lower()
        for medium in cls:
            if normalized == medium.value:
                return medium
        raise ValidationError("cable medium must be copper, fiber or dac")


class DcimConnectorType(StrEnum):
    RJ45 = "rj45"
    LC = "lc"
    SC = "sc"
    MPO = "mpo"
    SFP = "sfp"
    QSFP = "qsfp"

    @classmethod
    def from_value(cls, value: str) -> DcimConnectorType:
        normalized = value.strip().lower()
        for connector in cls:
            if normalized == connector.value:
                return connector
        raise ValidationError("connector must be rj45, lc, sc, mpo, sfp or qsfp")

    def compatible_media(self) -> tuple[DcimCableMedium, ...]:
        if self == DcimConnectorType.RJ45:
            return (DcimCableMedium.COPPER,)
        if self in (DcimConnectorType.LC, DcimConnectorType.SC, DcimConnectorType.MPO):
            return (DcimCableMedium.FIBER,)
        return (DcimCableMedium.FIBER, DcimCableMedium.DAC)

    def assert_supports_medium(self, medium: DcimCableMedium) -> None:
        if medium not in self.compatible_media():
            raise ValidationError(
                f"connector {self.value} is not compatible with {medium.value} cabling"
            )


class DcimPortOwnerType(StrEnum):
    EQUIPMENT = "equipment"
    PATCH_PANEL = "patch_panel"

    @classmethod
    def from_value(cls, value: str) -> DcimPortOwnerType:
        normalized = value.strip().lower().replace("-", "_")
        for owner_type in cls:
            if normalized == owner_type.value:
                return owner_type
        raise ValidationError("port owner type must be equipment or patch_panel")


class DcimCableStatus(StrEnum):
    PLANNED = "planned"
    INSTALLED = "installed"
    RETIRED = "retired"

    @classmethod
    def from_value(cls, value: str) -> DcimCableStatus:
        normalized = value.strip().lower()
        for status in cls:
            if normalized == status.value:
                return status
        raise ValidationError("cable status must be planned, installed or retired")

    @property
    def consumes_endpoint_capacity(self) -> bool:
        return self in (DcimCableStatus.PLANNED, DcimCableStatus.INSTALLED)


@dataclass(frozen=True, slots=True)
class PatchPanel:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    room_code: Code
    rack_code: Code
    code: Code
    rack_face: RackFace
    u_position: int
    u_height: int
    port_count: int
    connector: DcimConnectorType
    medium: DcimCableMedium
    label: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
        code: str,
        rack_face: str,
        u_position: int,
        u_height: int,
        port_count: int,
        connector: str,
        medium: str,
        label: str = "",
    ) -> Self:
        normalized_face = RackFace.from_value(rack_face)
        if normalized_face is None:
            raise ValidationError("patch panel rack face is mandatory")
        normalized_u = int(u_position)
        normalized_height = int(u_height)
        normalized_ports = int(port_count)
        normalized_medium = DcimCableMedium.from_value(medium)
        normalized_connector = DcimConnectorType.from_value(connector)
        normalized_connector.assert_supports_medium(normalized_medium)
        if not 1 <= normalized_u <= 60:
            raise ValidationError("patch panel U position must be between 1 and 60")
        if not 1 <= normalized_height <= 10:
            raise ValidationError("patch panel height must be between 1 and 10 U")
        if not 1 <= normalized_ports <= 288:
            raise ValidationError("patch panel port count must be between 1 and 288")
        normalized_label = " ".join(label.strip().split())
        if len(normalized_label) > 160:
            raise ValidationError("patch panel label cannot exceed 160 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site, "site code"),
            building_code=Code.from_value(building, "building code"),
            room_code=Code.from_value(room, "room code"),
            rack_code=Code.from_value(rack, "rack code"),
            code=Code.from_value(code, "patch panel code"),
            rack_face=normalized_face,
            u_position=normalized_u,
            u_height=normalized_height,
            port_count=normalized_ports,
            connector=normalized_connector,
            medium=normalized_medium,
            label=normalized_label,
        )

    def occupied_units(self) -> tuple[int, ...]:
        return tuple(range(self.u_position, self.u_position + self.u_height))

    def overlaps(self, face: RackFace, occupied_units: tuple[int, ...]) -> bool:
        return self.rack_face == face and bool(
            set(self.occupied_units()).intersection(occupied_units)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "room": self.room_code.value,
            "rack": self.rack_code.value,
            "patch_panel": self.code.value,
            "rack_face": self.rack_face.value,
            "u_position": self.u_position,
            "u_height": self.u_height,
            "occupied_units": list(self.occupied_units()),
            "port_count": self.port_count,
            "connector": self.connector.value,
            "medium": self.medium.value,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class DcimPortEndpoint:
    owner_type: DcimPortOwnerType
    owner_code: Code
    port_name: Code

    @classmethod
    def create(cls, owner_type: str, owner_code: str, port_name: str) -> Self:
        return cls(
            owner_type=DcimPortOwnerType.from_value(owner_type),
            owner_code=Code.from_value(owner_code, "port owner code"),
            port_name=Code.from_value(port_name, "port name"),
        )

    def key(self) -> str:
        return f"{self.owner_type.value}:{self.owner_code.value}:{self.port_name.value}"

    def as_dict(self) -> dict[str, str]:
        return {
            "owner_type": self.owner_type.value,
            "owner_code": self.owner_code.value,
            "port_name": self.port_name.value,
        }


@dataclass(frozen=True, slots=True)
class DcimPort:
    id: EntityId
    tenant_id: TenantId
    endpoint: DcimPortEndpoint
    site_code: Code
    building_code: Code
    room_code: Code
    connector: DcimConnectorType
    medium: DcimCableMedium
    enabled: bool = True

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        owner_type: str,
        owner_code: str,
        port_name: str,
        site: str,
        building: str,
        room: str,
        connector: str,
        medium: str,
        enabled: bool = True,
    ) -> Self:
        normalized_medium = DcimCableMedium.from_value(medium)
        normalized_connector = DcimConnectorType.from_value(connector)
        normalized_connector.assert_supports_medium(normalized_medium)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            endpoint=DcimPortEndpoint.create(owner_type, owner_code, port_name),
            site_code=Code.from_value(site, "site code"),
            building_code=Code.from_value(building, "building code"),
            room_code=Code.from_value(room, "room code"),
            connector=normalized_connector,
            medium=normalized_medium,
            enabled=bool(enabled),
        )

    def assert_cable_compatible(self, medium: DcimCableMedium) -> None:
        if not self.enabled:
            raise ValidationError(f"port {self.endpoint.key()} is disabled")
        if self.medium != medium:
            raise ValidationError(f"port {self.endpoint.key()} does not support {medium.value}")
        self.connector.assert_supports_medium(medium)

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            **self.endpoint.as_dict(),
            "site": self.site_code.value,
            "building": self.building_code.value,
            "room": self.room_code.value,
            "connector": self.connector.value,
            "medium": self.medium.value,
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class DcimCablePathSegment:
    order: int
    kind: str
    label: str

    @classmethod
    def create(cls, order: int, label: str, kind: str = "path") -> Self:
        normalized_order = int(order)
        normalized_kind = "-".join(kind.strip().lower().replace("_", "-").split())
        normalized_label = " ".join(label.strip().split())
        if not 1 <= normalized_order <= 100:
            raise ValidationError("cable path segment order must be between 1 and 100")
        if not 1 <= len(normalized_kind) <= 40:
            raise ValidationError("cable path segment kind must contain 1 to 40 characters")
        if not 1 <= len(normalized_label) <= 200:
            raise ValidationError("cable path segment label must contain 1 to 200 characters")
        return cls(normalized_order, normalized_kind, normalized_label)

    def as_dict(self) -> dict[str, object]:
        return {"order": self.order, "kind": self.kind, "label": self.label}


@dataclass(frozen=True, slots=True)
class DcimCable:
    id: EntityId
    tenant_id: TenantId
    cable_id: Code
    a_endpoint: DcimPortEndpoint
    b_endpoint: DcimPortEndpoint
    medium: DcimCableMedium
    status: DcimCableStatus
    path: tuple[DcimCablePathSegment, ...]
    length_m: float | None = None
    label: str = ""

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        cable_id: str,
        a_endpoint: DcimPortEndpoint,
        b_endpoint: DcimPortEndpoint,
        medium: str,
        status: str,
        path: tuple[DcimCablePathSegment, ...],
        length_m: float | None = None,
        label: str = "",
    ) -> Self:
        normalized_medium = DcimCableMedium.from_value(medium)
        normalized_status = DcimCableStatus.from_value(status)
        if a_endpoint.key() == b_endpoint.key():
            raise ValidationError("a cable cannot connect a port to itself")
        if not path:
            raise ValidationError("cable path must contain at least one segment")
        normalized_length = cls._normalize_length(length_m)
        normalized_label = " ".join(label.strip().split())
        if len(normalized_label) > 160:
            raise ValidationError("cable label cannot exceed 160 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            cable_id=Code.from_value(cable_id, "cable id"),
            a_endpoint=a_endpoint,
            b_endpoint=b_endpoint,
            medium=normalized_medium,
            status=normalized_status,
            path=tuple(sorted(path, key=lambda segment: segment.order)),
            length_m=normalized_length,
            label=normalized_label,
        )

    @classmethod
    def _normalize_length(cls, value: float | None) -> float | None:
        if value is None:
            return None
        normalized = float(value)
        if not 0 < normalized <= 100_000:
            raise ValidationError("cable length must be greater than 0 and at most 100000 meters")
        return round(normalized, 3)

    def assert_compatible_ports(self, a_port: DcimPort, b_port: DcimPort) -> None:
        if a_port.tenant_id != self.tenant_id or b_port.tenant_id != self.tenant_id:
            raise ValidationError("cable tenant must match both ports")
        if a_port.endpoint != self.a_endpoint:
            raise ValidationError("cable side A endpoint does not match side A port")
        if b_port.endpoint != self.b_endpoint:
            raise ValidationError("cable side B endpoint does not match side B port")
        a_port.assert_cable_compatible(self.medium)
        b_port.assert_cable_compatible(self.medium)

    def touches(self, endpoint: DcimPortEndpoint) -> bool:
        return endpoint in (self.a_endpoint, self.b_endpoint)

    def human_trace(self) -> str:
        endpoints = f"{self.a_endpoint.key()} -> {self.b_endpoint.key()}"
        path = " > ".join(segment.label for segment in self.path)
        return f"{self.cable_id.value}: {endpoints} via {path}"

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "cable_id": self.cable_id.value,
            "a_endpoint": self.a_endpoint.as_dict(),
            "b_endpoint": self.b_endpoint.as_dict(),
            "medium": self.medium.value,
            "status": self.status.value,
            "path": [segment.as_dict() for segment in self.path],
            "length_m": self.length_m,
            "label": self.label,
            "trace": self.human_trace(),
        }


class PowerFeedSide(StrEnum):
    A = "A"
    B = "B"

    @classmethod
    def from_value(cls, value: str) -> PowerFeedSide:
        normalized = value.strip().upper()
        for side in cls:
            if normalized == side.value:
                return side
        raise ValidationError("power feed side must be A or B")


class PowerDeviceKind(StrEnum):
    PDU = "pdu"
    UPS = "ups"

    @classmethod
    def from_value(cls, value: str) -> PowerDeviceKind:
        normalized = value.strip().lower()
        for kind in cls:
            if normalized == kind.value:
                return kind
        raise ValidationError("power device kind must be pdu or ups")


class CoolingRole(StrEnum):
    COLD_AISLE = "cold_aisle"
    HOT_AISLE = "hot_aisle"
    NEUTRAL = "neutral"

    @classmethod
    def from_value(cls, value: str) -> CoolingRole:
        normalized = value.strip().lower().replace("-", "_")
        for role in cls:
            if normalized == role.value:
                return role
        raise ValidationError("cooling role must be cold_aisle, hot_aisle or neutral")


@dataclass(frozen=True, slots=True)
class PowerDevice:
    id: EntityId
    tenant_id: TenantId
    code: Code
    kind: PowerDeviceKind
    site_code: Code
    building_code: Code
    room_code: Code
    rack_code: Code | None
    side: PowerFeedSide | None
    capacity_watts: int
    derating_percent: int
    input_source: str
    output_voltage: int
    label: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        kind: str,
        site: str,
        building: str,
        room: str,
        rack: str | None,
        side: str | None,
        capacity_watts: int,
        derating_percent: int = 80,
        input_source: str = "utility",
        output_voltage: int = 230,
        label: str = "",
    ) -> Self:
        normalized_kind = PowerDeviceKind.from_value(kind)
        normalized_side = PowerFeedSide.from_value(side) if side is not None else None
        normalized_capacity = int(capacity_watts)
        normalized_derating = int(derating_percent)
        normalized_voltage = int(output_voltage)
        normalized_input = " ".join(input_source.strip().split())
        normalized_label = " ".join(label.strip().split())
        if not 1 <= normalized_capacity <= 10_000_000:
            raise ValidationError("power device capacity must be between 1 and 10000000 watts")
        if not 1 <= normalized_derating <= 100:
            raise ValidationError("power device derating percent must be between 1 and 100")
        if not 48 <= normalized_voltage <= 1000:
            raise ValidationError("power device output voltage must be between 48 and 1000 volts")
        if not 1 <= len(normalized_input) <= 120:
            raise ValidationError("power device input source must contain 1 to 120 characters")
        if len(normalized_label) > 160:
            raise ValidationError("power device label cannot exceed 160 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            code=Code.from_value(code, "power device code"),
            kind=normalized_kind,
            site_code=Code.from_value(site, "site code"),
            building_code=Code.from_value(building, "building code"),
            room_code=Code.from_value(room, "room code"),
            rack_code=Code.from_value(rack, "rack code") if rack else None,
            side=normalized_side,
            capacity_watts=normalized_capacity,
            derating_percent=normalized_derating,
            input_source=normalized_input,
            output_voltage=normalized_voltage,
            label=normalized_label,
        )

    @property
    def derated_capacity_watts(self) -> int:
        return self.capacity_watts * self.derating_percent // 100

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "power_device": self.code.value,
            "kind": self.kind.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "room": self.room_code.value,
            "rack": self.rack_code.value if self.rack_code else None,
            "side": self.side.value if self.side else None,
            "capacity_watts": self.capacity_watts,
            "derating_percent": self.derating_percent,
            "derated_capacity_watts": self.derated_capacity_watts,
            "input_source": self.input_source,
            "output_voltage": self.output_voltage,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class PowerCircuit:
    id: EntityId
    tenant_id: TenantId
    circuit_id: Code
    source_device_code: Code
    site_code: Code
    building_code: Code
    room_code: Code
    rack_code: Code
    side: PowerFeedSide
    capacity_watts: int
    breaker_rating_amps: int
    redundancy_group: str
    label: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        circuit_id: str,
        source_device_code: str,
        site: str,
        building: str,
        room: str,
        rack: str,
        side: str,
        capacity_watts: int,
        breaker_rating_amps: int,
        redundancy_group: str = "default",
        label: str = "",
    ) -> Self:
        normalized_capacity = int(capacity_watts)
        normalized_breaker = int(breaker_rating_amps)
        normalized_group = "-".join(redundancy_group.strip().lower().replace("_", "-").split())
        normalized_label = " ".join(label.strip().split())
        if not 1 <= normalized_capacity <= 1_000_000:
            raise ValidationError("power circuit capacity must be between 1 and 1000000 watts")
        if not 1 <= normalized_breaker <= 10_000:
            raise ValidationError("power circuit breaker rating must be between 1 and 10000 amps")
        if not 1 <= len(normalized_group) <= 80:
            raise ValidationError("power circuit redundancy group must contain 1 to 80 characters")
        if len(normalized_label) > 160:
            raise ValidationError("power circuit label cannot exceed 160 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            circuit_id=Code.from_value(circuit_id, "power circuit id"),
            source_device_code=Code.from_value(source_device_code, "power device code"),
            site_code=Code.from_value(site, "site code"),
            building_code=Code.from_value(building, "building code"),
            room_code=Code.from_value(room, "room code"),
            rack_code=Code.from_value(rack, "rack code"),
            side=PowerFeedSide.from_value(side),
            capacity_watts=normalized_capacity,
            breaker_rating_amps=normalized_breaker,
            redundancy_group=normalized_group,
            label=normalized_label,
        )

    def remaining_watts(self, reservations: tuple[RackPowerReservation, ...]) -> int:
        used = sum(
            item.expected_watts for item in reservations if item.circuit_id == self.circuit_id
        )
        return self.capacity_watts - used

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "circuit_id": self.circuit_id.value,
            "source_device": self.source_device_code.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "room": self.room_code.value,
            "rack": self.rack_code.value,
            "side": self.side.value,
            "capacity_watts": self.capacity_watts,
            "breaker_rating_amps": self.breaker_rating_amps,
            "redundancy_group": self.redundancy_group,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class CoolingZone:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    room_code: Code
    zone_code: Code
    role: CoolingRole
    cooling_capacity_watts: int
    supply_temperature_c: float
    return_temperature_c: float
    label: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
        role: str,
        cooling_capacity_watts: int,
        supply_temperature_c: float,
        return_temperature_c: float,
        label: str = "",
    ) -> Self:
        normalized_capacity = int(cooling_capacity_watts)
        normalized_supply = round(float(supply_temperature_c), 2)
        normalized_return = round(float(return_temperature_c), 2)
        normalized_label = " ".join(label.strip().split())
        if not 1 <= normalized_capacity <= 10_000_000:
            raise ValidationError("cooling capacity must be between 1 and 10000000 watts")
        if not 5 <= normalized_supply <= 35:
            raise ValidationError("cooling supply temperature must be between 5 and 35 Celsius")
        if not 10 <= normalized_return <= 60:
            raise ValidationError("cooling return temperature must be between 10 and 60 Celsius")
        if normalized_return <= normalized_supply:
            raise ValidationError("cooling return temperature must exceed supply temperature")
        if len(normalized_label) > 160:
            raise ValidationError("cooling zone label cannot exceed 160 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site, "site code"),
            building_code=Code.from_value(building, "building code"),
            room_code=Code.from_value(room, "room code"),
            zone_code=Code.from_value(zone, "zone code"),
            role=CoolingRole.from_value(role),
            cooling_capacity_watts=normalized_capacity,
            supply_temperature_c=normalized_supply,
            return_temperature_c=normalized_return,
            label=normalized_label,
        )

    def remaining_watts(self, reservations: tuple[RackPowerReservation, ...]) -> int:
        return self.cooling_capacity_watts - sum(item.expected_watts for item in reservations)

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "room": self.room_code.value,
            "zone": self.zone_code.value,
            "role": self.role.value,
            "cooling_capacity_watts": self.cooling_capacity_watts,
            "supply_temperature_c": self.supply_temperature_c,
            "return_temperature_c": self.return_temperature_c,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class RackPowerReservation:
    id: EntityId
    tenant_id: TenantId
    asset_tag: Code
    circuit_id: Code
    side: PowerFeedSide
    site_code: Code
    building_code: Code
    room_code: Code
    rack_code: Code
    expected_watts: int
    label: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        asset_tag: str,
        circuit_id: str,
        side: str,
        site: str,
        building: str,
        room: str,
        rack: str,
        expected_watts: int,
        label: str = "",
    ) -> Self:
        normalized_watts = int(expected_watts)
        normalized_label = " ".join(label.strip().split())
        if not 1 <= normalized_watts <= 1_000_000:
            raise ValidationError("power reservation must be between 1 and 1000000 watts")
        if len(normalized_label) > 160:
            raise ValidationError("power reservation label cannot exceed 160 characters")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            asset_tag=Code.from_value(asset_tag, "asset tag"),
            circuit_id=Code.from_value(circuit_id, "power circuit id"),
            side=PowerFeedSide.from_value(side),
            site_code=Code.from_value(site, "site code"),
            building_code=Code.from_value(building, "building code"),
            room_code=Code.from_value(room, "room code"),
            rack_code=Code.from_value(rack, "rack code"),
            expected_watts=normalized_watts,
            label=normalized_label,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "asset_tag": self.asset_tag.value,
            "circuit_id": self.circuit_id.value,
            "side": self.side.value,
            "site": self.site_code.value,
            "building": self.building_code.value,
            "room": self.room_code.value,
            "rack": self.rack_code.value,
            "expected_watts": self.expected_watts,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class RackEnergyCoolingReport:
    rack: Rack
    circuits: tuple[PowerCircuit, ...]
    reservations: tuple[RackPowerReservation, ...]
    cooling_zone: CoolingZone | None

    def as_dict(self) -> dict[str, object]:
        side_capacity: dict[str, dict[str, Any]] = {}
        for side in PowerFeedSide:
            side_circuits = tuple(circuit for circuit in self.circuits if circuit.side == side)
            side_reservations = tuple(item for item in self.reservations if item.side == side)
            capacity = sum(circuit.capacity_watts for circuit in side_circuits)
            reserved = sum(item.expected_watts for item in side_reservations)
            side_capacity[side.value] = {
                "circuit_count": len(side_circuits),
                "capacity_watts": capacity,
                "reserved_watts": reserved,
                "remaining_watts": capacity - reserved,
                "status": "over_capacity" if reserved > capacity else "ok",
                "circuits": [circuit.as_dict() for circuit in side_circuits],
            }
        reserved_total = sum(item.expected_watts for item in self.reservations)
        rack_limit_remaining = (
            None
            if self.rack.power_capacity_watts is None
            else self.rack.power_capacity_watts - reserved_total
        )
        cooling_remaining = (
            None
            if self.cooling_zone is None
            else self.cooling_zone.remaining_watts(self.reservations)
        )
        return {
            "type": "rack_energy_cooling_report",
            "tenant_id": self.rack.tenant_id.value,
            "site": self.rack.site_code.value,
            "building": self.rack.building_code.value,
            "room": self.rack.room_code.value,
            "zone": self.rack.zone_code.value if self.rack.zone_code else None,
            "rack": self.rack.code.value,
            "rack_power_capacity_watts": self.rack.power_capacity_watts,
            "rack_reserved_watts": reserved_total,
            "rack_remaining_watts": rack_limit_remaining,
            "rack_power_status": (
                "unbounded"
                if rack_limit_remaining is None
                else "over_capacity"
                if rack_limit_remaining < 0
                else "ok"
            ),
            "redundant_power_ready": (
                side_capacity[PowerFeedSide.A.value]["capacity_watts"] > 0
                and side_capacity[PowerFeedSide.B.value]["capacity_watts"] > 0
            ),
            "sides": side_capacity,
            "cooling": None
            if self.cooling_zone is None
            else {
                **self.cooling_zone.as_dict(),
                "reserved_watts": reserved_total,
                "remaining_watts": cooling_remaining,
                "status": "over_capacity"
                if cooling_remaining is not None and cooling_remaining < 0
                else "ok",
            },
            "reservations": [reservation.as_dict() for reservation in self.reservations],
        }


@dataclass(frozen=True, slots=True)
class InterventionRouteStep:
    order: int
    title: str
    instruction: str

    @classmethod
    def create(cls, order: int, title: str, instruction: str) -> Self:
        normalized_order = int(order)
        normalized_title = " ".join(title.strip().split())
        normalized_instruction = " ".join(instruction.strip().split())
        if not 1 <= normalized_order <= 50:
            raise ValidationError("intervention route step order must be between 1 and 50")
        if not 1 <= len(normalized_title) <= 80:
            raise ValidationError("intervention route step title must contain 1 to 80 characters")
        if not 1 <= len(normalized_instruction) <= 500:
            raise ValidationError("intervention route instruction must contain 1 to 500 characters")
        return cls(normalized_order, normalized_title, normalized_instruction)

    def as_dict(self) -> dict[str, object]:
        return {"order": self.order, "title": self.title, "instruction": self.instruction}


@dataclass(frozen=True, slots=True)
class EquipmentLocatorPayload:
    tenant_id: TenantId
    asset_tag: Code
    payload: str
    token: str
    checksum: str

    @classmethod
    def create(cls, tenant_id: TenantId, equipment: Equipment) -> Self:
        if tenant_id != equipment.tenant_id:
            raise ValidationError("locator tenant does not match equipment tenant")
        path = equipment.location.human_readable()
        digest = hashlib.sha256(
            f"{tenant_id.value}|{equipment.asset_tag.value}|{path}".encode()
        ).hexdigest()
        token = digest[:20].upper()
        payload = f"oi:loc:{digest[:32].upper()}"
        if len(payload.encode("utf-8")) > QrCodeSvgDocument.MAX_BYTE_CAPACITY:
            raise ValidationError("locator payload exceeds supported QR byte capacity")
        return cls(
            tenant_id=tenant_id,
            asset_tag=equipment.asset_tag,
            payload=payload,
            token=token,
            checksum=digest,
        )

    def verify_payload(self, candidate: str) -> bool:
        return candidate.strip() == self.payload

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "asset_tag": self.asset_tag.value,
            "payload": self.payload,
            "token": self.token,
            "checksum": self.checksum,
        }


class QrCodeSvgDocument:
    VERSION = 3
    SIZE = 29
    DATA_CODEWORDS = 55
    ERROR_CODEWORDS = 15
    MAX_BYTE_CAPACITY = 53
    FORMAT_BITS_L_MASK_0 = 0b111011111000100

    def __init__(self, payload: str) -> None:
        self._payload = payload
        self._matrix: list[list[bool | None]] = [
            [None for _ in range(self.SIZE)] for _ in range(self.SIZE)
        ]
        self._function: list[list[bool]] = [
            [False for _ in range(self.SIZE)] for _ in range(self.SIZE)
        ]

    @classmethod
    def from_payload(cls, payload: str) -> Self:
        normalized = payload.strip()
        if not normalized:
            raise ValidationError("QR payload cannot be empty")
        if len(normalized.encode("utf-8")) > cls.MAX_BYTE_CAPACITY:
            raise ValidationError("QR payload exceeds version 3-L byte capacity")
        document = cls(normalized)
        document._draw_function_patterns()
        document._draw_codewords(document._final_codewords())
        document._draw_format_bits()
        return document

    def to_svg(self, module_size: int = 8, border: int = 4) -> str:
        if not 2 <= int(module_size) <= 32:
            raise ValidationError("QR module size must be between 2 and 32 pixels")
        if not 0 <= int(border) <= 16:
            raise ValidationError("QR border must be between 0 and 16 modules")
        size = (self.SIZE + border * 2) * module_size
        rects = [
            f'<rect width="{size}" height="{size}" fill="#fff"/>',
        ]
        for row in range(self.SIZE):
            for col in range(self.SIZE):
                if self._matrix[row][col]:
                    x = (col + border) * module_size
                    y = (row + border) * module_size
                    rects.append(
                        f'<rect x="{x}" y="{y}" width="{module_size}" '
                        f'height="{module_size}" fill="#000"/>'
                    )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="OpenInfra equipment locator QR" viewBox="0 0 {size} {size}" '
            f'width="{size}" height="{size}">' + "".join(rects) + "</svg>"
        )

    def _draw_function_patterns(self) -> None:
        self._draw_finder(0, 0)
        self._draw_finder(self.SIZE - 7, 0)
        self._draw_finder(0, self.SIZE - 7)
        self._draw_alignment(22, 22)
        for index in range(8, self.SIZE - 8):
            self._set_function(6, index, index % 2 == 0)
            self._set_function(index, 6, index % 2 == 0)
        self._set_function(4 * self.VERSION + 9, 8, True)
        self._reserve_format_areas()

    def _draw_finder(self, left: int, top: int) -> None:
        for row_offset in range(-1, 8):
            for col_offset in range(-1, 8):
                row = top + row_offset
                col = left + col_offset
                if not 0 <= row < self.SIZE or not 0 <= col < self.SIZE:
                    continue
                if 0 <= row_offset <= 6 and 0 <= col_offset <= 6:
                    is_black = (
                        row_offset in (0, 6)
                        or col_offset in (0, 6)
                        or (2 <= row_offset <= 4 and 2 <= col_offset <= 4)
                    )
                else:
                    is_black = False
                self._set_function(row, col, is_black)

    def _draw_alignment(self, center_row: int, center_col: int) -> None:
        for row_offset in range(-2, 3):
            for col_offset in range(-2, 3):
                row = center_row + row_offset
                col = center_col + col_offset
                distance = max(abs(row_offset), abs(col_offset))
                self._set_function(row, col, distance != 1)

    def _reserve_format_areas(self) -> None:
        for index in range(9):
            if index != 6:
                self._mark_function(8, index)
                self._mark_function(index, 8)
        for index in range(8):
            self._mark_function(self.SIZE - 1 - index, 8)
            self._mark_function(8, self.SIZE - 1 - index)

    def _draw_format_bits(self) -> None:
        bits = self.FORMAT_BITS_L_MASK_0
        for index in range(6):
            self._set_function(8, index, self._bit(bits, index))
        self._set_function(8, 7, self._bit(bits, 6))
        self._set_function(8, 8, self._bit(bits, 7))
        self._set_function(7, 8, self._bit(bits, 8))
        for index in range(9, 15):
            self._set_function(14 - index, 8, self._bit(bits, index))
        for index in range(8):
            self._set_function(self.SIZE - 1 - index, 8, self._bit(bits, index))
        for index in range(8, 15):
            self._set_function(8, self.SIZE - 15 + index, self._bit(bits, index))

    def _draw_codewords(self, codewords: tuple[int, ...]) -> None:
        bits = tuple(
            (codeword >> shift) & 1 for codeword in codewords for shift in range(7, -1, -1)
        )
        bit_index = 0
        upward = True
        col = self.SIZE - 1
        while col > 0:
            if col == 6:
                col -= 1
            row_range = range(self.SIZE - 1, -1, -1) if upward else range(self.SIZE)
            for row in row_range:
                for current_col in (col, col - 1):
                    if self._function[row][current_col]:
                        continue
                    bit = bits[bit_index] if bit_index < len(bits) else 0
                    bit_index += 1
                    masked = bool(bit) ^ ((row + current_col) % 2 == 0)
                    self._matrix[row][current_col] = masked
            upward = not upward
            col -= 2

    def _final_codewords(self) -> tuple[int, ...]:
        data = self._data_codewords()
        return data + self._reed_solomon_remainder(data, self.ERROR_CODEWORDS)

    def _data_codewords(self) -> tuple[int, ...]:
        payload_bytes = self._payload.encode("utf-8")
        bits: list[int] = []
        self._append_bits(bits, 0b0100, 4)
        self._append_bits(bits, len(payload_bytes), 8)
        for value in payload_bytes:
            self._append_bits(bits, value, 8)
        remaining = self.DATA_CODEWORDS * 8 - len(bits)
        self._append_bits(bits, 0, min(4, remaining))
        while len(bits) % 8 != 0:
            bits.append(0)
        codewords = [
            int("".join(str(bit) for bit in bits[index : index + 8]), 2)
            for index in range(0, len(bits), 8)
        ]
        pad = (0xEC, 0x11)
        pad_index = 0
        while len(codewords) < self.DATA_CODEWORDS:
            codewords.append(pad[pad_index % 2])
            pad_index += 1
        return tuple(codewords)

    @staticmethod
    def _append_bits(bits: list[int], value: int, length: int) -> None:
        for shift in range(length - 1, -1, -1):
            bits.append((value >> shift) & 1)

    @classmethod
    def _reed_solomon_remainder(cls, data: tuple[int, ...], degree: int) -> tuple[int, ...]:
        generator = cls._reed_solomon_generator(degree)
        result = [0] * degree
        for value in data:
            factor = value ^ result.pop(0)
            result.append(0)
            for index in range(degree):
                result[index] ^= cls._gf_multiply(generator[index + 1], factor)
        return tuple(result)

    @classmethod
    def _reed_solomon_generator(cls, degree: int) -> tuple[int, ...]:
        generator = [1]
        for index in range(degree):
            generator = cls._poly_multiply(generator, [1, cls._gf_power(index)])
        return tuple(generator)

    @classmethod
    def _poly_multiply(cls, left: list[int], right: list[int]) -> list[int]:
        result = [0] * (len(left) + len(right) - 1)
        for left_index, left_value in enumerate(left):
            for right_index, right_value in enumerate(right):
                result[left_index + right_index] ^= cls._gf_multiply(left_value, right_value)
        return result

    @staticmethod
    def _gf_power(power: int) -> int:
        value = 1
        for _ in range(power):
            value <<= 1
            if value & 0x100:
                value ^= 0x11D
        return value

    @classmethod
    def _gf_multiply(cls, left: int, right: int) -> int:
        result = 0
        a = left
        b = right
        while b:
            if b & 1:
                result ^= a
            a <<= 1
            if a & 0x100:
                a ^= 0x11D
            b >>= 1
        return result & 0xFF

    @staticmethod
    def _bit(value: int, index: int) -> bool:
        return ((value >> index) & 1) != 0

    def _set_function(self, row: int, col: int, black: bool) -> None:
        self._matrix[row][col] = black
        self._function[row][col] = True

    def _mark_function(self, row: int, col: int) -> None:
        self._function[row][col] = True


@dataclass(frozen=True, slots=True)
class EquipmentLocatorSheet:
    equipment: Equipment
    locator_payload: EquipmentLocatorPayload
    qr_svg: str
    intervention_steps: tuple[InterventionRouteStep, ...]

    @classmethod
    def create(cls, equipment: Equipment) -> Self:
        payload = EquipmentLocatorPayload.create(equipment.tenant_id, equipment)
        qr_svg = QrCodeSvgDocument.from_payload(payload.payload).to_svg()
        return cls(
            equipment=equipment,
            locator_payload=payload,
            qr_svg=qr_svg,
            intervention_steps=cls._build_steps(equipment),
        )

    @classmethod
    def _build_steps(cls, equipment: Equipment) -> tuple[InterventionRouteStep, ...]:
        location = equipment.location
        steps = [
            InterventionRouteStep.create(
                1,
                "Site",
                f"Se rendre sur le site {location.site_code.value}.",
            ),
            InterventionRouteStep.create(
                2,
                "Bâtiment",
                f"Entrer dans le bâtiment {location.building_code.value}.",
            ),
        ]
        order = 3
        if location.floor_code:
            steps.append(
                InterventionRouteStep.create(
                    order,
                    "Étage",
                    f"Rejoindre l'étage {location.floor_code.value}.",
                )
            )
            order += 1
        steps.append(
            InterventionRouteStep.create(
                order,
                "Salle",
                f"Accéder à la salle {location.room_code.value}.",
            )
        )
        order += 1
        steps.append(
            InterventionRouteStep.create(
                order,
                "Grille",
                f"Repérer la cellule ligne {location.row}, colonne {location.column}.",
            )
        )
        order += 1
        if location.zone_code:
            steps.append(
                InterventionRouteStep.create(
                    order,
                    "Zone",
                    f"Contrôler la zone {location.zone_code.value}.",
                )
            )
            order += 1
        if location.rack_code:
            rack_instruction = f"Identifier le rack {location.rack_code.value}"
            if location.rack_face:
                rack_instruction += f", face {location.rack_face.value}"
            if location.u_position is not None:
                rack_instruction += f", position U {location.u_position}"
            if location.u_height is not None and location.u_height != 1:
                rack_instruction += f" sur {location.u_height} U"
            rack_instruction += "."
            steps.append(InterventionRouteStep.create(order, "Rack", rack_instruction))
            order += 1
        if location.coordinates:
            coordinates = location.coordinates
            steps.append(
                InterventionRouteStep.create(
                    order,
                    "Coordonnées",
                    "Vérifier le point X/Y/Z "
                    f"{coordinates.x:.2f}/{coordinates.y:.2f}/{coordinates.z:.2f}.",
                )
            )
            order += 1
        steps.append(
            InterventionRouteStep.create(
                order,
                "Identification terrain",
                (
                    "Scanner le QR OpenInfra et comparer l'asset tag affiché "
                    "avec l'étiquette physique."
                ),
            )
        )
        return tuple(steps)

    def html_document(self) -> str:
        equipment_name = html.escape(self.equipment.name.value)
        asset_tag = html.escape(self.equipment.asset_tag.value)
        human_path = html.escape(self.equipment.location.human_readable())
        payload = html.escape(self.locator_payload.payload)
        rows = "".join(
            "<li>" + html.escape(f"{step.order}. {step.title} — {step.instruction}") + "</li>"
            for step in self.intervention_steps
        )
        return (
            '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            "<title>OpenInfra fiche localisation</title></head><body>"
            f"<h1>{asset_tag} — {equipment_name}</h1>"
            f"<section>{self.qr_svg}</section>"
            f"<p><strong>Chemin physique :</strong> {human_path}</p>"
            f"<p><strong>Payload QR :</strong> <code>{payload}</code></p>"
            f"<ol>{rows}</ol>"
            "</body></html>"
        )

    def as_dict(self, include_svg: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "tenant_id": self.equipment.tenant_id.value,
            "asset_tag": self.equipment.asset_tag.value,
            "equipment_name": self.equipment.name.value,
            "human_path": self.equipment.location.human_readable(),
            "locator": self.locator_payload.as_dict(),
            "intervention_steps": [step.as_dict() for step in self.intervention_steps],
        }
        if include_svg:
            payload["qr_svg"] = self.qr_svg
        return payload


@dataclass(frozen=True, slots=True)
class EquipmentScanProof:
    tenant_id: TenantId
    asset_tag: Code
    verified: bool
    expected_payload: str
    received_payload: str

    @classmethod
    def create(cls, equipment: Equipment, received_payload: str) -> Self:
        locator = EquipmentLocatorPayload.create(equipment.tenant_id, equipment)
        normalized_received = received_payload.strip()
        return cls(
            tenant_id=equipment.tenant_id,
            asset_tag=equipment.asset_tag,
            verified=locator.verify_payload(normalized_received),
            expected_payload=locator.payload,
            received_payload=normalized_received,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "asset_tag": self.asset_tag.value,
            "verified": self.verified,
            "expected_payload": self.expected_payload,
            "received_payload": self.received_payload,
        }
