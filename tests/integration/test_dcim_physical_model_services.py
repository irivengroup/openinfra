from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import DefinePhysicalRoomCommand, LocateEquipmentCommand
from openinfra.domain.common import NotFoundError, TenantId, ValidationError


class TestDcimPhysicalModelServices:
    def test_define_room_creates_hierarchy_and_is_idempotent(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        command = DefinePhysicalRoomCommand(
            tenant_id="default",
            actor="pytest",
            site_code="PAR2",
            site_name="Paris 2",
            country="FR",
            region="Ile-de-France",
            city="Paris",
            building_code="BAT-B",
            building_name="Building B",
            floor_code="F02",
            floor_name="Second floor",
            floor_index=2,
            room_code="MDF1",
            room_name="Main Distribution Frame",
            rows=("A", "B", "B"),
            columns=("01", "02"),
            zone_code="Z-A",
            zone_name="Zone A",
            zone_rows=("A",),
            zone_columns=("01", "02"),
            x=10.0,
            y=5.5,
            z=2.0,
        )

        first = app.dcim_topology_service.define_room(command)
        second = app.dcim_topology_service.define_room(command)
        tenant_id = TenantId.from_value(command.tenant_id)
        room = app.dcim_repository.find_room(
            tenant_id,
            command.site_code,
            command.building_code,
            command.room_code,
        )
        zone = app.dcim_repository.find_zone(
            tenant_id,
            command.site_code,
            command.building_code,
            command.room_code,
            "Z-A",
        )

        assert first["created"] == {
            "site": True,
            "building": True,
            "floor": True,
            "room": True,
            "zone": True,
        }
        assert second["created"] == {
            "site": False,
            "building": False,
            "floor": False,
            "room": False,
            "zone": False,
        }
        assert first["path"] == "site=PAR2 | building=BAT-B | floor=F02 | room=MDF1 | xyz=10.00/5.50/2.00"
        assert first["rows"] == ["A", "B"]
        assert room is not None
        assert room.floor_code is not None
        assert room.floor_code.value == "F02"
        assert zone is not None
        assert zone.rows == ("A",)

    def test_define_room_rejects_zone_outside_grid(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)

        with pytest.raises(ValidationError):
            app.dcim_topology_service.define_room(
                DefinePhysicalRoomCommand(
                    tenant_id="default",
                    actor="pytest",
                    site_code="PAR3",
                    site_name="Paris 3",
                    country="FR",
                    region="IDF",
                    city="Paris",
                    building_code="BAT-C",
                    building_name="Building C",
                    floor_code="F01",
                    floor_name="First floor",
                    floor_index=1,
                    room_code="TEL1",
                    room_name="Telecom Room",
                    rows=("A",),
                    columns=("01",),
                    zone_code="Z-ERR",
                    zone_name="Invalid zone",
                    zone_rows=("Z",),
                    zone_columns=("01",),
                )
            )

    def test_locate_equipment_uses_floor_zone_and_coordinates(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="LYO1",
                site_name="Lyon 1",
                country="FR",
                region="Auvergne-Rhone-Alpes",
                city="Lyon",
                building_code="BAT-L",
                building_name="Lyon Building",
                floor_code="F03",
                floor_name="Third floor",
                floor_index=3,
                room_code="MMR2",
                room_name="MMR Lyon",
                rows=("A", "B"),
                columns=("01", "02"),
                zone_code="Z1",
                zone_name="Access zone",
                zone_rows=("B",),
                zone_columns=("02",),
            )
        )

        equipment = app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="LYO-SRV-001",
                equipment_name="Lyon Server",
                site="LYO1",
                building="BAT-L",
                room="MMR2",
                row="B",
                column="02",
                rack=None,
                u_position=None,
                x=1.0,
                y=2.0,
                z=3.0,
                floor="F03",
                zone="Z1",
            )
        )

        assert equipment.location.human_readable() == (
            "site=LYO1 | building=BAT-L | floor=F03 | room=MMR2 | row=B | "
            "column=02 | zone=Z1 | xyz=1.00/2.00/3.00"
        )

    def test_locate_rejects_unknown_zone(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")

        with pytest.raises((NotFoundError, ValidationError)):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    tenant_id="default",
                    actor="pytest",
                    asset_tag="BAD-ZONE",
                    equipment_name="Bad Zone",
                    site="PAR1",
                    building="BAT-A",
                    room="MMR1",
                    row="B",
                    column="12",
                    rack=None,
                    u_position=None,
                    x=None,
                    y=None,
                    z=None,
                    zone="NOPE",
                )
            )

    def test_define_room_accepts_room_without_zone(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        result = app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="NTE1",
                site_name="Nantes 1",
                country="FR",
                region="Pays de la Loire",
                city="Nantes",
                building_code="BAT-N",
                building_name="Building N",
                floor_code="F00",
                floor_name="Ground floor",
                floor_index=0,
                room_code="ROOM1",
                room_name="Room 1",
                rows=("A",),
                columns=("01",),
            )
        )

        assert result["zone"] is None
        assert result["created"]["zone"] is False

    def test_define_room_rejects_partial_zone_payload(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        base = {
            "tenant_id": "default",
            "actor": "pytest",
            "site_code": "LIL1",
            "site_name": "Lille 1",
            "country": "FR",
            "region": "Hauts-de-France",
            "city": "Lille",
            "building_code": "BAT-L",
            "building_name": "Building L",
            "floor_code": "F01",
            "floor_name": "First floor",
            "floor_index": 1,
            "room_code": "ROOM1",
            "room_name": "Room 1",
            "rows": ("A",),
            "columns": ("01",),
        }

        with pytest.raises(ValidationError):
            app.dcim_topology_service.define_room(
                DefinePhysicalRoomCommand(**base, zone_name="Missing code")
            )
        with pytest.raises(ValidationError):
            app.dcim_topology_service.define_room(
                DefinePhysicalRoomCommand(**base, zone_code="Z1")
            )

    def test_locate_rejects_floor_mismatch_and_missing_zone_repository(
        self,
        tmp_path: Path,
    ) -> None:
        from openinfra.domain.dcim import Building, Floor, Room, Site
        from openinfra.domain.common import TenantId

        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        tenant = TenantId.from_value("default")
        with app.transaction_manager.begin() as unit_of_work:
            app.dcim_repository.add_site(Site.create(tenant, "REN1", "Rennes 1", "FR", "Rennes"))
            app.dcim_repository.add_building(Building.create(tenant, "REN1", "BAT-R", "Building R"))
            app.dcim_repository.add_floor(Floor.create(tenant, "REN1", "BAT-R", "F01", "First", 1))
            app.dcim_repository.add_room(
                Room.create(
                    tenant,
                    "REN1",
                    "BAT-R",
                    "ROOM1",
                    "Room 1",
                    ("A",),
                    ("01",),
                    floor_code="F01",
                    zone_codes=("Z-MISSING",),
                )
            )
            unit_of_work.commit()

        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    "default",
                    "pytest",
                    "REN-SRV-1",
                    "Server",
                    "REN1",
                    "BAT-R",
                    "ROOM1",
                    "A",
                    "01",
                    None,
                    None,
                    None,
                    None,
                    None,
                    floor="F02",
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    "default",
                    "pytest",
                    "REN-SRV-2",
                    "Server",
                    "REN1",
                    "BAT-R",
                    "ROOM1",
                    "A",
                    "01",
                    None,
                    None,
                    None,
                    None,
                    None,
                    floor="F01",
                    zone="Z-MISSING",
                )
            )

    def test_locate_rejects_rack_capacity_row_floor_and_zone_conflicts(
        self,
        tmp_path: Path,
    ) -> None:
        from openinfra.domain.common import Coordinates3D, TenantId
        from openinfra.domain.dcim import Building, Floor, Rack, Room, RoomZone, Site

        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        tenant = TenantId.from_value("default")
        with app.transaction_manager.begin() as unit_of_work:
            app.dcim_repository.add_site(Site.create(tenant, "BOR1", "Bordeaux 1", "FR", "Bordeaux"))
            app.dcim_repository.add_building(Building.create(tenant, "BOR1", "BAT-B", "Building B"))
            app.dcim_repository.add_floor(Floor.create(tenant, "BOR1", "BAT-B", "F01", "First", 1))
            app.dcim_repository.add_room(
                Room.create(
                    tenant,
                    "BOR1",
                    "BAT-B",
                    "ROOM1",
                    "Room 1",
                    ("A", "B"),
                    ("01", "02"),
                    floor_code="F01",
                    zone_codes=("Z1", "Z2"),
                )
            )
            app.dcim_repository.add_zone(
                RoomZone.create(
                    tenant,
                    "BOR1",
                    "BAT-B",
                    "F01",
                    "ROOM1",
                    "Z1",
                    "Zone 1",
                    ("A",),
                    ("01",),
                )
            )
            app.dcim_repository.add_zone(
                RoomZone.create(
                    tenant,
                    "BOR1",
                    "BAT-B",
                    "F01",
                    "ROOM1",
                    "Z2",
                    "Zone 2",
                    ("A",),
                    ("01",),
                )
            )
            app.dcim_repository.add_rack(
                Rack.create(
                    tenant,
                    "BOR1",
                    "BAT-B",
                    "ROOM1",
                    "R1",
                    "A",
                    "01",
                    2,
                    Coordinates3D.from_values(1.0, 1.0, 0.0),
                    floor_code="F01",
                    zone_code="Z1",
                )
            )
            app.dcim_repository.add_rack(
                Rack.create(
                    tenant,
                    "BOR1",
                    "BAT-B",
                    "ROOM1",
                    "R-FLOOR",
                    "A",
                    "01",
                    2,
                    None,
                    floor_code="F02",
                    zone_code="Z1",
                )
            )
            unit_of_work.commit()

        base = {
            "tenant_id": "default",
            "actor": "pytest",
            "asset_tag": "BOR-SRV",
            "equipment_name": "Server",
            "site": "BOR1",
            "building": "BAT-B",
            "room": "ROOM1",
            "rack": "R1",
            "x": None,
            "y": None,
            "z": None,
            "floor": "F01",
            "zone": "Z1",
        }
        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(**base, row="A", column="01", u_position=3)
            )
        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(**base, row="B", column="01", u_position=1)
            )
        floor_mismatch = dict(base)
        floor_mismatch["rack"] = "R-FLOOR"
        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(**floor_mismatch, row="A", column="01", u_position=1)
            )
        zone_mismatch = dict(base)
        zone_mismatch["zone"] = "Z2"
        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(**zone_mismatch, row="A", column="01", u_position=1)
            )
        missing_rack = dict(base)
        missing_rack["rack"] = "R2"
        with pytest.raises(NotFoundError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(**missing_rack, row="A", column="01", u_position=1)
            )
