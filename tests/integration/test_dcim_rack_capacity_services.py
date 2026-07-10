from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    DefinePhysicalRoomCommand,
    DefineRackCommand,
    LocateEquipmentCommand,
    RackCapacityCommand,
)
from openinfra.domain.common import ConflictError, NotFoundError, ValidationError


class TestDcimRackCapacityServices:
    def _prepared_app(self, tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="PAR4",
                site_name="Paris 4",
                country="FR",
                region="Ile-de-France",
                city="Paris",
                building_code="BAT-D",
                building_name="Building D",
                floor_code="F01",
                floor_name="First floor",
                floor_index=1,
                room_code="MMR4",
                room_name="MMR Paris 4",
                rows=("A", "B"),
                columns=("01", "02"),
                zone_code="Z1",
                zone_name="Compute zone",
                zone_rows=("A",),
                zone_columns=("01", "02"),
            )
        )
        return app

    def test_define_rack_and_capacity_report_by_face(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        rack = app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                rack="R01",
                row="A",
                column="01",
                units=42,
                usable_faces=("front", "rear"),
                max_weight_kg=1200.5,
                power_capacity_watts=16000,
                x=1.0,
                y=2.0,
                z=0.0,
            )
        )
        front_equipment = app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="PAR4-SRV-001",
                equipment_name="Server 001",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                row="A",
                column="01",
                rack="R01",
                u_position=10,
                rack_face="front",
                u_height=2,
                x=None,
                y=None,
                z=None,
            )
        )
        rear_equipment = app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="PAR4-PDU-001",
                equipment_name="Rear PDU 001",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                row="A",
                column="01",
                rack="R01",
                u_position=10,
                rack_face="rear",
                u_height=1,
                x=None,
                y=None,
                z=None,
            )
        )
        report = app.dcim_rack_service.capacity(
            RackCapacityCommand(
                tenant_id="default",
                site="PAR4",
                building="BAT-D",
                room="MMR4",
                rack="R01",
            )
        ).as_dict()

        assert rack["faces"] == ["front", "rear"]
        assert rack["max_weight_kg"] == 1200.5
        assert rack["power_capacity_watts"] == 16000
        assert "face=front" in front_equipment.location.human_readable()
        assert "height_u=2" in front_equipment.location.human_readable()
        assert "face=rear" in rear_equipment.location.human_readable()
        assert report["faces_capacity"]["front"]["used_units"] == [10, 11]
        assert report["faces_capacity"]["rear"]["used_units"] == [10]
        assert report["faces_capacity"]["front"]["free_count"] == 40
        assert report["faces_capacity"]["front"]["equipment"][0]["asset_tag"] == "PAR4-SRV-001"

    def test_rack_overlap_is_rejected_but_same_asset_can_be_moved(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                rack="R02",
                row="A",
                column="02",
                units=12,
                usable_faces=("front",),
            )
        )
        base = {
            "tenant_id": "default",
            "actor": "pytest",
            "site": "PAR4",
            "building": "BAT-D",
            "floor": "L01",
            "room": "MMR4",
            "zone": "Z1",
            "row": "A",
            "column": "02",
            "rack": "R02",
            "x": None,
            "y": None,
            "z": None,
        }
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                **base,
                asset_tag="PAR4-SRV-010",
                equipment_name="Server 010",
                u_position=4,
                u_height=3,
                rack_face="front",
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                **base,
                asset_tag="PAR4-SRV-010",
                equipment_name="Server 010 relocated",
                u_position=7,
                u_height=1,
                rack_face="front",
            )
        )
        with pytest.raises(ConflictError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    **base,
                    asset_tag="PAR4-SRV-011",
                    equipment_name="Server 011",
                    u_position=7,
                    u_height=1,
                    rack_face="front",
                )
            )

    def test_rack_context_and_mounting_invariants(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        with pytest.raises(NotFoundError):
            app.dcim_rack_service.define_rack(
                DefineRackCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="PAR4",
                    building="BAT-D",
                    room="UNKNOWN",
                    rack="R404",
                    row="A",
                    column="01",
                    units=42,
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_rack_service.define_rack(
                DefineRackCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="PAR4",
                    building="BAT-D",
                    floor="F99",
                    room="MMR4",
                    rack="R03",
                    row="A",
                    column="01",
                    units=42,
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_rack_service.define_rack(
                DefineRackCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="PAR4",
                    building="BAT-D",
                    room="MMR4",
                    zone="Z1",
                    rack="R04",
                    row="B",
                    column="01",
                    units=42,
                )
            )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                rack="R05",
                row="A",
                column="01",
                units=2,
                usable_faces=("front",),
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    tenant_id="default",
                    actor="pytest",
                    asset_tag="PAR4-SRV-020",
                    equipment_name="Server 020",
                    site="PAR4",
                    building="BAT-D",
                    floor="L01",
                    room="MMR4",
                    zone="Z1",
                    row="A",
                    column="01",
                    rack="R05",
                    u_position=2,
                    u_height=2,
                    rack_face="front",
                    x=None,
                    y=None,
                    z=None,
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    tenant_id="default",
                    actor="pytest",
                    asset_tag="PAR4-SRV-021",
                    equipment_name="Server 021",
                    site="PAR4",
                    building="BAT-D",
                    floor="L01",
                    room="MMR4",
                    zone="Z1",
                    row="A",
                    column="01",
                    rack="R05",
                    u_position=1,
                    u_height=1,
                    rack_face="rear",
                    x=None,
                    y=None,
                    z=None,
                )
            )

    def test_zone_added_to_existing_room_can_host_rack(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        base = {
            "tenant_id": "default",
            "actor": "pytest",
            "site_code": "LYO1",
            "site_name": "Lyon 1",
            "country": "FR",
            "region": "Auvergne-Rhone-Alpes",
            "city": "Lyon",
            "building_code": "BAT-L",
            "building_name": "Building L",
            "floor_code": "F01",
            "floor_name": "First floor",
            "floor_index": 1,
            "room_code": "MMR-L",
            "room_name": "MMR Lyon",
            "rows": ("A", "B"),
            "columns": ("01", "02"),
        }
        app.dcim_topology_service.define_room(DefinePhysicalRoomCommand(**base))
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                **base,
                zone_code="Z1",
                zone_name="Compute zone",
                zone_rows=("A",),
                zone_columns=("01",),
            )
        )

        rack = app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="LYO1",
                building="BAT-L",
                floor="L01",
                room="MMR-L",
                zone="Z1",
                rack="R01",
                row="A",
                column="01",
                units=24,
                usable_faces=("front",),
            )
        )

        assert rack["zone"] == "Z1"

    def test_locator_sheet_and_scan_verification_service(self, tmp_path: Path) -> None:
        from openinfra.application.dcim_services import (
            GenerateEquipmentLocatorCommand,
            VerifyEquipmentScanCommand,
        )

        app = self._prepared_app(tmp_path)
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                rack="R10",
                row="A",
                column="01",
                units=42,
                usable_faces=("front", "rear"),
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="PAR4-SRV-QR",
                equipment_name="QR Server",
                site="PAR4",
                building="BAT-D",
                floor="L01",
                room="MMR4",
                zone="Z1",
                row="A",
                column="01",
                rack="R10",
                u_position=8,
                rack_face="front",
                u_height=2,
                x=1.0,
                y=2.0,
                z=0.0,
            )
        )
        sheet = app.dcim_field_operation_service.locator_sheet(
            GenerateEquipmentLocatorCommand("default", "pytest", "PAR4-SRV-QR")
        )
        proof = app.dcim_field_operation_service.verify_scan(
            VerifyEquipmentScanCommand(
                "default",
                "pytest",
                "PAR4-SRV-QR",
                str(sheet.as_dict()["locator"]["payload"]),
            )
        )

        assert proof.verified is True
        assert "PAR4-SRV-QR" in sheet.html_document()
        assert len(sheet.intervention_steps) >= 7
        with pytest.raises(ValidationError):
            app.dcim_field_operation_service.locator_sheet(
                GenerateEquipmentLocatorCommand("default", "pytest", "PAR4-SRV-QR", "pdf")
            )
        with pytest.raises(ValidationError):
            app.dcim_field_operation_service.verify_scan(
                VerifyEquipmentScanCommand("default", "pytest", "PAR4-SRV-QR", "bad")
            )
        with pytest.raises(NotFoundError):
            app.dcim_field_operation_service.locator_sheet(
                GenerateEquipmentLocatorCommand("default", "pytest", "UNKNOWN")
            )
        with pytest.raises(NotFoundError):
            app.dcim_field_operation_service.verify_scan(
                VerifyEquipmentScanCommand("default", "pytest", "UNKNOWN", "bad")
            )
