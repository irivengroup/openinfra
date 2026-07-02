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
