from __future__ import annotations

import pytest

from openinfra.domain.common import Coordinates3D, TenantId, ValidationError
from openinfra.domain.dcim import (
    DcimGridValidator,
    EquipmentLocation,
    Floor,
    Rack,
    RackFace,
    Room,
    RoomZone,
    Site,
)


class TestDcimDomain:
    def test_site_lifecycle_status_is_normalized_and_selectable(self) -> None:
        tenant = TenantId.from_value("default")
        site = Site.create(tenant, "par1", "Paris 1", "fr", "Paris")

        assert site.code.value == "PAR1"
        assert site.status.value == "active"
        assert site.selectable() is True

        suspended = site.update(status="suspended")
        assert suspended.status.value == "suspended"
        assert suspended.selectable() is False

        retired = suspended.retire()
        assert retired.status.value == "retired"
        assert retired.selectable() is False

        with pytest.raises(ValidationError):
            site.update(status="deleted")

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

    def test_rack_faces_and_equipment_interval_invariants(self) -> None:
        from openinfra.domain.dcim import Equipment, RackCapacityReport, RackFace

        tenant = TenantId.from_value("default")
        rack = Rack.create(
            tenant,
            "PAR1",
            "BAT-A",
            "MMR1",
            "R10",
            "A",
            "01",
            10,
            None,
            usable_faces=("front", "rear", "front"),
            max_weight_kg=500,
            power_capacity_watts=8000,
        )
        location = EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "A",
            "01",
            rack_code="R10",
            u_position=2,
            u_height=2,
            rack_face="front",
        )
        other = EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "A",
            "01",
            rack_code="R10",
            u_position=3,
            u_height=1,
            rack_face="front",
        )
        rear = EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "A",
            "01",
            rack_code="R10",
            u_position=3,
            u_height=1,
            rack_face="rear",
        )
        equipment = Equipment.create(tenant, "ASSET-1", "Asset 1", location)
        report = RackCapacityReport(rack, (equipment,)).as_dict()

        assert rack.usable_faces == (RackFace.FRONT, RackFace.REAR)
        assert location.occupied_units() == (2, 3)
        assert location.overlaps(other) is True
        assert location.overlaps(rear) is False
        assert report["faces_capacity"]["front"]["used_count"] == 2
        assert report["faces_capacity"]["rear"]["used_count"] == 0

        with pytest.raises(ValidationError):
            Rack.create(
                tenant,
                "PAR1",
                "BAT-A",
                "MMR1",
                "R11",
                "A",
                "01",
                10,
                None,
                usable_faces=("side",),
            )
        with pytest.raises(ValidationError):
            Rack.create(
                tenant,
                "PAR1",
                "BAT-A",
                "MMR1",
                "R12",
                "A",
                "01",
                10,
                None,
                max_weight_kg=0,
            )
        with pytest.raises(ValidationError):
            Rack.create(
                tenant,
                "PAR1",
                "BAT-A",
                "MMR1",
                "R13",
                "A",
                "01",
                10,
                None,
                power_capacity_watts=0,
            )
        with pytest.raises(ValidationError):
            EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01", rack_face="front")
        with pytest.raises(ValidationError):
            EquipmentLocation.create(
                "PAR1", "BAT-A", "MMR1", "A", "01", rack_code="R10", u_height=2
            )

    def test_equipment_locator_payload_qr_sheet_and_scan_proof(self) -> None:
        from openinfra.domain.dcim import (
            Equipment,
            EquipmentLocatorPayload,
            EquipmentLocatorSheet,
            EquipmentScanProof,
            InterventionRouteStep,
            QrCodeSvgDocument,
        )

        tenant = TenantId.from_value("default")
        location = EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "A",
            "01",
            rack_code="R01",
            u_position=10,
            u_height=2,
            rack_face="front",
            floor_code="F01",
            zone_code="Z1",
            coordinates=Coordinates3D.from_values(1.0, 2.0, 0.5),
        )
        equipment = Equipment.create(tenant, "PAR1-SRV-001", "Server 001", location)
        locator = EquipmentLocatorPayload.create(tenant, equipment)
        svg = QrCodeSvgDocument.from_payload(locator.payload).to_svg(module_size=4, border=2)
        sheet = EquipmentLocatorSheet.create(equipment)
        proof = EquipmentScanProof.create(equipment, locator.payload)
        rejected = EquipmentScanProof.create(equipment, "oi:loc:default:OTHER:BAD")

        assert locator.verify_payload(locator.payload) is True
        assert locator.verify_payload(locator.payload + "x") is False
        assert locator.as_dict()["asset_tag"] == "PAR1-SRV-001"
        assert svg.startswith("<svg")
        assert "rect" in svg
        assert sheet.as_dict()["human_path"].startswith("site=PAR1")
        assert "Payload QR" in sheet.html_document()
        assert any(step.title == "Rack" for step in sheet.intervention_steps)
        assert proof.verified is True
        assert rejected.verified is False
        assert rejected.as_dict()["received_payload"] == "oi:loc:default:OTHER:BAD"
        assert InterventionRouteStep.create(1, " A ", "  B   C ").as_dict()["instruction"] == "B C"

    def test_equipment_location_public_payload_contract(self) -> None:
        from openinfra.domain.dcim import Equipment

        tenant = TenantId.from_value("default")
        location = EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "A",
            "01",
            rack_code="R01",
            u_position=12,
            rack_face="rear",
            u_height=2,
            floor_code="F02",
            zone_code="Z2",
            coordinates=Coordinates3D.from_values(3.5, 4.25, 0.0),
        )
        equipment = Equipment.create(tenant, "PAR-SRV-777", "Server 777", location)

        assert location.as_dict() == {
            "site": "PAR1",
            "building": "BAT-A",
            "floor": "F02",
            "room": "MMR1",
            "row": "A",
            "column": "01",
            "zone": "Z2",
            "rack": "R01",
            "u_position": 12,
            "rack_face": "rear",
            "u_height": 2,
            "coordinates": {"x": 3.5, "y": 4.25, "z": 0.0},
            "human_readable": location.human_readable(),
        }
        assert equipment.as_dict()["location"] == location.as_dict()

    def test_qr_and_locator_validation_edges(self) -> None:
        from openinfra.domain.dcim import (
            Equipment,
            EquipmentLocatorPayload,
            InterventionRouteStep,
            QrCodeSvgDocument,
        )

        tenant = TenantId.from_value("default")
        location = EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01")
        equipment = Equipment.create(tenant, "PAR1-SRV-002", "Server 002", location)
        with pytest.raises(ValidationError):
            EquipmentLocatorPayload.create(TenantId.from_value("other"), equipment)
        with pytest.raises(ValidationError):
            QrCodeSvgDocument.from_payload("")
        with pytest.raises(ValidationError):
            QrCodeSvgDocument.from_payload("x" * 54)
        with pytest.raises(ValidationError):
            QrCodeSvgDocument.from_payload("valid").to_svg(module_size=1)
        with pytest.raises(ValidationError):
            QrCodeSvgDocument.from_payload("valid").to_svg(border=17)
        with pytest.raises(ValidationError):
            InterventionRouteStep.create(0, "Title", "Instruction")
        with pytest.raises(ValidationError):
            InterventionRouteStep.create(1, "", "Instruction")
        with pytest.raises(ValidationError):
            InterventionRouteStep.create(1, "Title", "")


def test_dcim_domain_validation_edges_for_release_gate() -> None:
    tenant = TenantId.from_value("default")
    for callable_ in (
        lambda: DcimGridValidator.normalized_unique_codes((), "room row"),
        lambda: Site.create(tenant, "PAR1", "Paris", "FRA", "Paris"),
        lambda: Site.create(tenant, "PAR1", "Paris", "FR", ""),
        lambda: Site.create(tenant, "PAR1", "Paris", "FR", "Paris", "x" * 129),
        lambda: Floor.create(tenant, "PAR1", "BAT-A", "F999", "Too High", 301),
        lambda: RackFace.from_value("side"),
        lambda: Rack.create(tenant, "PAR1", "BAT-A", "MMR1", "R01", "A", "01", 0, None),
        lambda: Rack.create(
            tenant, "PAR1", "BAT-A", "MMR1", "R01", "A", "01", 42, None, usable_faces=()
        ),
        lambda: Rack.create(
            tenant, "PAR1", "BAT-A", "MMR1", "R01", "A", "01", 42, None, max_weight_kg=0
        ),
        lambda: Rack.create(
            tenant, "PAR1", "BAT-A", "MMR1", "R01", "A", "01", 42, None, power_capacity_watts=0
        ),
        lambda: EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01", None, 1),
        lambda: EquipmentLocation.create(
            "PAR1", "BAT-A", "MMR1", "A", "01", None, None, u_height=2
        ),
        lambda: EquipmentLocation.create(
            "PAR1", "BAT-A", "MMR1", "A", "01", None, None, rack_face="front"
        ),
        lambda: EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01", "R01", 61),
        lambda: EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01", "R01", 1, u_height=61),
    ):
        with pytest.raises(ValidationError):
            callable_()

    room = Room.create(
        tenant,
        "PAR1",
        "BAT-A",
        "MMR1",
        "Main Room",
        ("A",),
        ("01",),
        floor_code="F01",
        zone_codes=("Z1",),
        coordinates=Coordinates3D.from_values(1, 2, 0),
    )
    assert "floor=F01" in room.physical_path()
    assert "xyz=1.00/2.00/0.00" in room.physical_path()
    for callable_ in (
        lambda: room.assert_cell_exists("B", "01"),
        lambda: room.assert_cell_exists("A", "02"),
        lambda: room.assert_zone_known("Z2"),
    ):
        with pytest.raises(ValidationError):
            callable_()
    zone = RoomZone.create(tenant, "PAR1", "BAT-A", "F02", "MMR1", "Z9", "Bad", ("B",), ("99",))
    for callable_ in (
        lambda: zone.assert_within_room(room),
        lambda: RoomZone.create(
            tenant, "PAR1", "BAT-A", "F01", "MMR1", "Z1", "Z", ("A",), ("01",)
        ).assert_cell_exists("B", "01"),
        lambda: RoomZone.create(
            tenant, "PAR1", "BAT-A", "F01", "MMR1", "Z1", "Z", ("A",), ("01",)
        ).assert_cell_exists("A", "02"),
    ):
        with pytest.raises(ValidationError):
            callable_()
    rack = Rack.create(tenant, "PAR1", "BAT-A", "MMR1", "R01", "A", "01", 4, None)
    for callable_ in (
        lambda: rack.assert_face_supported(RackFace.REAR),
        lambda: rack.assert_unit_interval(0, 1),
        lambda: rack.assert_unit_interval(1, 0),
        lambda: rack.assert_unit_interval(4, 2),
    ):
        with pytest.raises(ValidationError):
            callable_()
    assert rack.as_capacity_seed()["rack"] == "R01"
    loose = EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01")
    rack_a = EquipmentLocation.create(
        "PAR1", "BAT-A", "MMR1", "A", "01", "R01", 1, rack_face="front", u_height=2
    )
    rack_b = EquipmentLocation.create(
        "PAR1", "BAT-A", "MMR1", "A", "01", "R02", 1, rack_face="front", u_height=2
    )
    rack_c = EquipmentLocation.create(
        "PAR1", "BAT-A", "MMR1", "A", "01", "R01", 1, rack_face="rear", u_height=2
    )
    assert loose.effective_rack_face() is None
    assert loose.effective_u_height() is None
    assert loose.occupied_units() == ()
    assert loose.overlaps(rack_a) is False
    assert rack_a.overlaps(rack_b) is False
    assert rack_a.overlaps(rack_c) is False
