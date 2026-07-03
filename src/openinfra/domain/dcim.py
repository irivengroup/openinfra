from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from openinfra.domain.common import Code, Coordinates3D, EntityId, Name, TenantId, ValidationError


class DcimGridValidator:
    @staticmethod
    def normalized_unique_codes(values: tuple[str, ...], label: str) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(Code.from_value(value, label).value for value in values))
        if not normalized:
            raise ValidationError(f"{label} must contain at least one value")
        return normalized


@dataclass(frozen=True, slots=True)
class Site:
    id: EntityId
    tenant_id: TenantId
    code: Code
    name: Name
    country: str
    city: str
    region: str = ""

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
        )


@dataclass(frozen=True, slots=True)
class Building:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    code: Code
    name: Name

    @classmethod
    def create(cls, tenant_id: TenantId, site_code: str, code: str, name: str) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            code=Code.from_value(code, "building code"),
            name=Name.from_value(name, "building name"),
        )


@dataclass(frozen=True, slots=True)
class Floor:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
    code: Code
    name: Name
    level_index: int

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
    ) -> Self:
        normalized_row = Code.from_value(row, "rack row").value
        normalized_column = Code.from_value(column, "rack column").value
        if not 1 <= units <= 60:
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
            units=units,
            coordinates=coordinates,
            floor_code=Code.from_value(floor_code, "floor code") if floor_code else None,
            zone_code=Code.from_value(zone_code, "zone code") if zone_code else None,
        )


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
    ) -> Self:
        normalized_row = Code.from_value(row, "equipment location row").value
        normalized_column = Code.from_value(column, "equipment location column").value
        if u_position is not None and not 1 <= u_position <= 60:
            raise ValidationError("rack unit position must be between 1 and 60")
        if rack_code is None and u_position is not None:
            raise ValidationError("rack code is mandatory when a rack unit is provided")
        return cls(
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            room_code=Code.from_value(room_code, "room code"),
            row=normalized_row,
            column=normalized_column,
            rack_code=Code.from_value(rack_code, "rack code") if rack_code else None,
            u_position=u_position,
            coordinates=coordinates,
            floor_code=Code.from_value(floor_code, "floor code") if floor_code else None,
            zone_code=Code.from_value(zone_code, "zone code") if zone_code else None,
        )

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
        if self.coordinates:
            parts.append(
                f"xyz={self.coordinates.x:.2f}/{self.coordinates.y:.2f}/{self.coordinates.z:.2f}"
            )
        return " | ".join(parts)


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
