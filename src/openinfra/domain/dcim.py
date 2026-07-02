from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from openinfra.domain.common import Code, Coordinates3D, EntityId, Name, TenantId, ValidationError


@dataclass(frozen=True, slots=True)
class Site:
    id: EntityId
    tenant_id: TenantId
    code: Code
    name: Name
    country: str
    city: str

    @classmethod
    def create(cls, tenant_id: TenantId, code: str, name: str, country: str, city: str) -> Self:
        normalized_country = country.strip().upper()
        normalized_city = " ".join(city.strip().split())
        if len(normalized_country) != 2 or not normalized_country.isalpha():
            raise ValidationError("country must be an ISO-3166 alpha-2 code")
        if not normalized_city:
            raise ValidationError("site city is mandatory")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            code=Code.from_value(code, "site code"),
            name=Name.from_value(name, "site name"),
            country=normalized_country,
            city=normalized_city,
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
class Room:
    id: EntityId
    tenant_id: TenantId
    site_code: Code
    building_code: Code
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
        code: str,
        name: str,
        rows: tuple[str, ...],
        columns: tuple[str, ...],
    ) -> Self:
        normalized_rows = tuple(dict.fromkeys(row.strip().upper() for row in rows if row.strip()))
        normalized_columns = tuple(
            dict.fromkeys(col.strip().upper() for col in columns if col.strip())
        )
        if not normalized_rows:
            raise ValidationError("room must define at least one row")
        if not normalized_columns:
            raise ValidationError("room must define at least one column")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            site_code=Code.from_value(site_code, "site code"),
            building_code=Code.from_value(building_code, "building code"),
            code=Code.from_value(code, "room code"),
            name=Name.from_value(name, "room name"),
            rows=normalized_rows,
            columns=normalized_columns,
        )

    def assert_cell_exists(self, row: str, column: str) -> None:
        if row.strip().upper() not in self.rows:
            raise ValidationError(f"unknown room row: {row}")
        if column.strip().upper() not in self.columns:
            raise ValidationError(f"unknown room column: {column}")


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
    ) -> Self:
        normalized_row = row.strip().upper()
        normalized_column = column.strip().upper()
        if not normalized_row:
            raise ValidationError("rack row is mandatory")
        if not normalized_column:
            raise ValidationError("rack column is mandatory")
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
    ) -> Self:
        normalized_row = row.strip().upper()
        normalized_column = column.strip().upper()
        if not normalized_row:
            raise ValidationError("equipment location row is mandatory")
        if not normalized_column:
            raise ValidationError("equipment location column is mandatory")
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
        )

    def human_readable(self) -> str:
        parts = [
            f"site={self.site_code.value}",
            f"building={self.building_code.value}",
            f"room={self.room_code.value}",
            f"row={self.row}",
            f"column={self.column}",
        ]
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
