from __future__ import annotations

import pytest

from openinfra.domain.common import Coordinates3D, TenantId, ValidationError
from openinfra.domain.dcim import EquipmentLocation, Rack, Room


class TestDcimDomain:
    def test_room_requires_rows_and_columns(self) -> None:
        tenant = TenantId.from_value("default")
        room = Room.create(
            tenant,
            "PAR1",
            "BAT-A",
            "MMR1",
            "Main Room",
            rows=("A", "B"),
            columns=("01", "02"),
        )

        room.assert_cell_exists("A", "01")

        with pytest.raises(ValidationError):
            room.assert_cell_exists("Z", "01")

    def test_equipment_location_requires_column_and_row(self) -> None:
        with pytest.raises(ValidationError):
            EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "", "01")

        with pytest.raises(ValidationError):
            EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "")

    def test_rack_requires_valid_units_and_coordinates(self) -> None:
        tenant = TenantId.from_value("default")
        coordinates = Coordinates3D.from_values(1.0, 2.0, 0.0)
        rack = Rack.create(tenant, "PAR1", "BAT-A", "MMR1", "R42", "B", "12", 42, coordinates)

        assert rack.row == "B"
        assert rack.column == "12"
        assert rack.coordinates == coordinates

        with pytest.raises(ValidationError):
            Rack.create(tenant, "PAR1", "BAT-A", "MMR1", "R99", "B", "12", 99, None)

    def test_coordinates_are_all_or_nothing(self) -> None:
        assert Coordinates3D.from_values(None, None, None) is None
        with pytest.raises(ValidationError):
            Coordinates3D.from_values(1.0, None, 2.0)

    def test_site_region_floor_and_zone_invariants(self) -> None:
        from openinfra.domain.dcim import Floor, RoomZone, Site

        tenant = TenantId.from_value("default")
        site = Site.create(tenant, "lon1", "London 1", "gb", "London", "England")
        floor = Floor.create(tenant, "LON1", "BAT-A", "F10", "Tenth floor", 10)
        room = Room.create(
            tenant,
            "LON1",
            "BAT-A",
            "ROOM1",
            "Room 1",
            rows=("A", "A", "B"),
            columns=("01", "02"),
            floor_code="F10",
            zone_codes=("Z1",),
        )
        zone = RoomZone.create(
            tenant,
            "LON1",
            "BAT-A",
            "F10",
            "ROOM1",
            "Z1",
            "Zone 1",
            rows=("A",),
            columns=("01",),
        )

        zone.assert_within_room(room)
        zone.assert_cell_exists("A", "01")
        assert site.country == "GB"
        assert site.region == "England"
        assert floor.level_index == 10
        assert room.rows == ("A", "B")
        assert room.physical_path() == "site=LON1 | building=BAT-A | floor=F10 | room=ROOM1"
