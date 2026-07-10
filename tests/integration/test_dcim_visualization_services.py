from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    ConnectDcimCableCommand,
    DefineCoolingZoneCommand,
    DefineDcimPortCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    LocateEquipmentCommand,
    RackCapacityCommand,
    RenderDigitalTwinCommand,
    RenderRackElevationCommand,
    RenderRoomPlanCommand,
    ReserveEquipmentPowerCommand,
)
from openinfra.domain.common import EntityId, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import (
    Equipment,
    EquipmentLocation,
    QrCodeSvgDocument,
    Rack,
    RackElevation,
    RoomPlan2D,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDcimVisualizationServices:
    def _prepared_app(self, tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="VIS1",
                site_name="Visualization DC",
                country="FR",
                region="IDF",
                city="Paris",
                building_code="BAT-V",
                building_name="Visualization Building",
                floor_code="F01",
                floor_name="Floor 1",
                floor_index=1,
                room_code="ROOM-V",
                room_name="Visualization Room",
                rows=("A", "B"),
                columns=("01", "02"),
                zone_code="Z1",
                zone_name="Zone 1",
                zone_rows=("A",),
                zone_columns=("01", "02"),
                x=1.0,
                y=2.0,
                z=3.0,
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                floor="L01",
                room="ROOM-V",
                zone="Z1",
                rack="R01",
                row="A",
                column="01",
                units=6,
                usable_faces=("front", "rear"),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                floor="L01",
                room="ROOM-V",
                rack="R02",
                row="B",
                column="02",
                units=4,
                usable_faces=("front",),
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="VIS-SRV-01",
                equipment_name="Visualization Server 1",
                site="VIS1",
                building="BAT-V",
                floor="L01",
                room="ROOM-V",
                zone="Z1",
                row="A",
                column="01",
                rack="R01",
                u_position=2,
                u_height=2,
                rack_face="front",
                x=1.1,
                y=2.1,
                z=0.1,
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="VIS-SRV-02",
                equipment_name="Visualization Server 2",
                site="VIS1",
                building="BAT-V",
                floor="L01",
                room="ROOM-V",
                row="A",
                column="01",
                rack="R01",
                u_position=5,
                u_height=1,
                rack_face="rear",
                x=None,
                y=None,
                z=None,
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="VIS-FLOOR-01",
                equipment_name="Floor Device",
                site="VIS1",
                building="BAT-V",
                floor="L01",
                room="ROOM-V",
                row="B",
                column="01",
                rack=None,
                u_position=None,
                x=None,
                y=None,
                z=None,
            )
        )
        return app

    def test_room_plan_and_rack_elevation_models_render_json_svg_and_html(
        self,
        tmp_path: Path,
    ) -> None:
        app = self._prepared_app(tmp_path)
        plan = app.dcim_visualization_service.room_plan(
            RenderRoomPlanCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
                output_format="json",
            )
        )
        plan_payload = plan.as_dict()
        svg = plan.svg_document()
        html = plan.html_document()
        cell_statuses = {
            cell["row"] + cell["column"]: cell["status"] for cell in plan_payload["grid"]
        }

        assert plan_payload["type"] == "room_plan_2d"
        assert plan_payload["rack_count"] == 2
        assert plan_payload["equipment_count"] == 3
        assert cell_statuses["A01"] == "rack_occupied"
        assert cell_statuses["B01"] == "floor_occupied"
        assert cell_statuses["A02"] == "empty"
        assert svg.startswith("<svg")
        assert "R01" in svg
        assert html.startswith("<!doctype html>")
        assert "Plan 2D" in html

        elevation = app.dcim_visualization_service.rack_elevation(
            RenderRackElevationCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
                rack="R01",
                face="front",
                output_format="svg",
            )
        )
        elevation_payload = elevation.as_dict()
        elevation_svg = elevation.svg_document()
        elevation_html = elevation.html_document()

        assert elevation_payload["type"] == "rack_elevation"
        assert elevation_payload["used_units"] == [2, 3]
        assert elevation_payload["free_units"] == 4
        assert elevation_payload["occupancy_percent"] == 33.33
        assert elevation_payload["elevation"][0]["u"] == 6
        assert elevation_payload["elevation"][-1]["u"] == 1
        assert "VIS-SRV-01" in elevation_svg
        assert elevation_html.startswith("<!doctype html>")

    def test_digital_twin_rejects_unknown_room(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)

        with pytest.raises(NotFoundError):
            app.dcim_visualization_service.digital_twin(
                RenderDigitalTwinCommand("default", "pytest", "VIS1", "BAT-V", "ROOM-V")
            )

    def test_digital_twin_consolidates_room_racks_cabling_power_and_cooling(
        self, tmp_path: Path
    ) -> None:
        app = self._prepared_app(tmp_path)
        app.dcim_cabling_service.define_patch_panel(
            DefinePatchPanelCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
                rack="R01",
                patch_panel="PP01",
                rack_face="front",
                u_position=1,
                u_height=1,
                port_count=2,
                connector="rj45",
                medium="copper",
            )
        )
        app.dcim_cabling_service.define_port(
            DefineDcimPortCommand(
                tenant_id="default",
                actor="pytest",
                owner_type="equipment",
                owner_code="VIS-SRV-01",
                port_name="ETH0",
                connector="rj45",
                medium="copper",
            )
        )
        app.dcim_cabling_service.connect_cable(
            ConnectDcimCableCommand(
                tenant_id="default",
                actor="pytest",
                cable_id="CAB-VIS-001",
                a_owner_type="equipment",
                a_owner_code="VIS-SRV-01",
                a_port_name="ETH0",
                b_owner_type="patch_panel",
                b_owner_code="PP01",
                b_port_name="P01",
                medium="copper",
                path_segments=("R01 serveur", "PP01"),
            )
        )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                tenant_id="default",
                actor="pytest",
                code="PDU-A-R01",
                kind="pdu",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
                rack="R01",
                side="A",
                capacity_watts=2000,
                derating_percent=100,
            )
        )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                tenant_id="default",
                actor="pytest",
                circuit_id="CIR-A-R01",
                source_device="PDU-A-R01",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
                rack="R01",
                side="A",
                capacity_watts=1200,
                breaker_rating_amps=16,
            )
        )
        app.dcim_environment_service.define_cooling_zone(
            DefineCoolingZoneCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
                zone="Z1",
                role="cold_aisle",
                cooling_capacity_watts=5000,
                supply_temperature_c=18.0,
                return_temperature_c=30.0,
            )
        )
        app.dcim_environment_service.reserve_equipment_power(
            ReserveEquipmentPowerCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="VIS-SRV-01",
                circuit_id="CIR-A-R01",
                expected_watts=450,
            )
        )

        twin = app.dcim_visualization_service.digital_twin(
            RenderDigitalTwinCommand(
                tenant_id="default",
                actor="pytest",
                site="VIS1",
                building="BAT-V",
                room="ROOM-V",
            )
        )

        assert twin["type"] == "dcim_digital_twin"
        assert twin["summary"] == {
            "rack_count": 2,
            "equipment_count": 3,
            "floor_equipment_count": 1,
            "patch_panel_count": 1,
            "port_count": 3,
            "cable_count": 1,
            "power_circuit_count": 1,
            "power_reservation_count": 1,
            "cooling_zone_count": 1,
        }
        assert twin["room_plan"]["type"] == "room_plan_2d"
        assert twin["integrity"] == {
            "status": "ok",
            "source": "dcim_repository",
            "scope": "room",
        }
        r01 = next(rack for rack in twin["racks"] if rack["rack"]["rack"] == "R01")
        assert [panel["patch_panel"] for panel in r01["patch_panels"]] == ["PP01"]
        assert [cable["cable_id"] for cable in r01["cables"]] == ["CAB-VIS-001"]
        assert r01["energy_cooling"]["rack_reserved_watts"] == 450
        assert r01["energy_cooling"]["cooling"]["status"] == "ok"
        assert "front" in r01["elevations"] and "rear" in r01["elevations"]

    def test_visualization_rejects_unknown_room_rack_face_and_format(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        with pytest.raises(NotFoundError):
            app.dcim_rack_service.capacity(
                RackCapacityCommand(
                    tenant_id="default",
                    site="VIS1",
                    building="BAT-V",
                    room="ROOM-V",
                    rack="UNKNOWN",
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_rack_service.define_rack(
                DefineRackCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    floor="L01",
                    room="ROOM-V",
                    zone="UNKNOWN",
                    rack="R404",
                    row="A",
                    column="01",
                    units=4,
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_visualization_service.room_plan(
                RenderRoomPlanCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    room="UNKNOWN",
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_visualization_service.rack_elevation(
                RenderRackElevationCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    room="ROOM-V",
                    rack="UNKNOWN",
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_visualization_service.rack_elevation(
                RenderRackElevationCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    room="ROOM-V",
                    rack="R02",
                    face="rear",
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_visualization_service.room_plan(
                RenderRoomPlanCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    room="ROOM-V",
                    output_format="pdf",
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_visualization_service.room_plan(
                RenderRoomPlanCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    room="ROOM-V",
                    output_format="json",
                )
            ).svg_document(cell_size=10)
        with pytest.raises(ValidationError):
            app.dcim_visualization_service.rack_elevation(
                RenderRackElevationCommand(
                    tenant_id="default",
                    actor="pytest",
                    site="VIS1",
                    building="BAT-V",
                    room="ROOM-V",
                    rack="R01",
                )
            ).svg_document(unit_height=4)
        tenant = TenantId.from_value("default")
        room = app.dcim_repository.find_room(tenant, "VIS1", "BAT-V", "ROOM-V")
        rack = app.dcim_repository.find_rack(tenant, "VIS1", "BAT-V", "ROOM-V", "R01")
        equipment = app.dcim_repository.find_equipment(tenant, "VIS-SRV-01")
        assert room is not None
        assert rack is not None
        assert equipment is not None
        wrong_room_rack = Rack.create(
            tenant,
            "VIS1",
            "BAT-V",
            "OTHER",
            "R-WRONG",
            "A",
            "01",
            4,
            None,
        )
        with pytest.raises(ValidationError):
            RoomPlan2D.create(room, (wrong_room_rack,), ())
        wrong_equipment = Equipment.create(
            tenant,
            "WRONG-EQ",
            "Wrong equipment",
            EquipmentLocation.create("VIS1", "BAT-V", "OTHER", "A", "01"),
        )
        with pytest.raises(ValidationError):
            RoomPlan2D.create(room, (), (wrong_equipment,))
        with pytest.raises(ValidationError):
            RackElevation.create(rack, (), None)
        room.assert_zone_known(None)
        with pytest.raises(ValidationError):
            EntityId.from_value("   ")
        assert (
            QrCodeSvgDocument.from_payload("A")
            .to_svg(
                module_size=2,
                border=0,
            )
            .startswith("<svg")
        )

    def test_visualization_cli_commands(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        app = self._prepared_app(tmp_path)
        app.store.flush()

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "room-plan",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                ]
            )
            == 0
        )
        plan_payload = json.loads(capsys.readouterr().out)
        assert plan_payload["type"] == "room_plan_2d"

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "room-plan",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                    "--format",
                    "svg",
                ]
            )
            == 0
        )
        assert capsys.readouterr().out.startswith("<svg")

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "room-plan",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                    "--format",
                    "html",
                ]
            )
            == 0
        )
        assert "Plan 2D" in capsys.readouterr().out

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "rack-elevation",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                    "--rack",
                    "R01",
                    "--face",
                    "front",
                ]
            )
            == 0
        )
        rack_json = json.loads(capsys.readouterr().out)
        assert rack_json["type"] == "rack_elevation"

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "rack-elevation",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                    "--rack",
                    "R01",
                    "--face",
                    "front",
                    "--format",
                    "svg",
                ]
            )
            == 0
        )
        assert capsys.readouterr().out.startswith("<svg")

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "rack-elevation",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                    "--rack",
                    "R01",
                    "--face",
                    "front",
                    "--format",
                    "html",
                ]
            )
            == 0
        )
        assert "Rack elevation" in capsys.readouterr().out

        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "digital-twin",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "VIS1",
                    "--building",
                    "BAT-V",
                    "--room",
                    "ROOM-V",
                ]
            )
            == 0
        )
        twin_json = json.loads(capsys.readouterr().out)
        assert twin_json["type"] == "dcim_digital_twin"
        assert twin_json["summary"]["rack_count"] == 2

    def test_visualization_http_api(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            plan = self._get_json(
                base_url
                + "/api/v1/dcim/room-plan?tenant_id=default&site=VIS1&building=BAT-V&room=ROOM-V"
            )
            svg = self._get_json(
                base_url
                + "/api/v1/dcim/room-plan?tenant_id=default&site=VIS1"
                + "&building=BAT-V&room=ROOM-V&format=svg"
            )
            elevation = self._get_json(
                base_url
                + "/api/v1/dcim/rack-elevation?tenant_id=default&site=VIS1"
                + "&building=BAT-V&room=ROOM-V&rack=R01&face=front"
            )
            html = self._get_json(
                base_url
                + "/api/v1/dcim/rack-elevation?tenant_id=default&site=VIS1"
                + "&building=BAT-V&room=ROOM-V&rack=R01&face=front&format=html"
            )
            twin = self._get_json(
                base_url
                + "/api/v1/dcim/digital-twin?tenant_id=default&site=VIS1"
                + "&building=BAT-V&room=ROOM-V"
            )

            assert plan["type"] == "room_plan_2d"
            assert svg["svg"].startswith("<svg")
            assert elevation["type"] == "rack_elevation"
            assert twin["type"] == "dcim_digital_twin"
            assert twin["summary"]["equipment_count"] == 3
            assert html["html"].startswith("<!doctype html>")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _get_json(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
