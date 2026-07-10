from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    ConnectDcimCableCommand,
    DefineDcimPortCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefineRackCommand,
    LocateEquipmentCommand,
    TraceDcimCableCommand,
)
from openinfra.domain.common import ConflictError, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import (
    DcimCable,
    DcimCableMedium,
    DcimCablePathSegment,
    DcimCableStatus,
    DcimConnectorType,
    DcimPort,
    DcimPortEndpoint,
    DcimPortOwnerType,
    PatchPanel,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDcimCablingServices:
    def _prepared_app(self, tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="CBL1",
                site_name="Cabling DC",
                country="FR",
                region="IDF",
                city="Paris",
                building_code="BAT-C",
                building_name="Cabling Building",
                floor_code="F01",
                floor_name="Floor 1",
                floor_index=1,
                room_code="MMR-C",
                room_name="Cabling Room",
                rows=("A", "B"),
                columns=("01", "02"),
                zone_code="Z1",
                zone_name="Network Zone",
                zone_rows=("A",),
                zone_columns=("01", "02"),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="CBL1",
                building="BAT-C",
                floor="L01",
                room="MMR-C",
                zone="Z1",
                rack="R01",
                row="A",
                column="01",
                units=12,
                usable_faces=("front", "rear"),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="CBL1",
                building="BAT-C",
                floor="L01",
                room="MMR-C",
                rack="R02",
                row="A",
                column="02",
                units=12,
                usable_faces=("front",),
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="SRV-CBL-01",
                equipment_name="Cabled Server",
                site="CBL1",
                building="BAT-C",
                floor="L01",
                room="MMR-C",
                zone="Z1",
                row="A",
                column="01",
                rack="R01",
                u_position=6,
                u_height=1,
                rack_face="front",
                x=None,
                y=None,
                z=None,
            )
        )
        return app

    def test_patch_panel_ports_cable_trace_and_json_repository_roundtrip(
        self, tmp_path: Path
    ) -> None:
        app = self._prepared_app(tmp_path)
        panel = app.dcim_cabling_service.define_patch_panel(
            DefinePatchPanelCommand(
                tenant_id="default",
                actor="pytest",
                site="CBL1",
                building="BAT-C",
                room="MMR-C",
                rack="R01",
                patch_panel="PP01",
                rack_face="front",
                u_position=2,
                u_height=1,
                port_count=4,
                connector="rj45",
                medium="copper",
                label="Top of rack copper panel",
                port_prefix="P",
            )
        )
        equipment_port = app.dcim_cabling_service.define_port(
            DefineDcimPortCommand(
                tenant_id="default",
                actor="pytest",
                owner_type="equipment",
                owner_code="SRV-CBL-01",
                port_name="ETH0",
                connector="rj45",
                medium="copper",
            )
        )
        operator_port = app.dcim_cabling_service.define_port(
            DefineDcimPortCommand(
                tenant_id="default",
                actor="pytest",
                owner_type="patch_panel",
                owner_code="PP01",
                port_name="P05",
                connector="rj45",
                medium="copper",
                site="CBL1",
                building="BAT-C",
                room="MMR-C",
            )
        )
        cable = app.dcim_cabling_service.connect_cable(
            ConnectDcimCableCommand(
                tenant_id="default",
                actor="pytest",
                cable_id="CAB-0001",
                a_owner_type="equipment",
                a_owner_code="SRV-CBL-01",
                a_port_name="ETH0",
                b_owner_type="patch_panel",
                b_owner_code="PP01",
                b_port_name="P01",
                medium="copper",
                status="installed",
                path_segments=("Rack R01 front vertical manager", "Patch panel PP01 port P01"),
                length_m=2.34567,
                label="server uplink",
            )
        )
        trace = app.dcim_cabling_service.trace_cable(
            TraceDcimCableCommand("default", "pytest", "CAB-0001")
        )
        tenant = TenantId.from_value("default")
        endpoint = DcimPortEndpoint.create("equipment", "SRV-CBL-01", "ETH0")
        listed_cables = app.dcim_repository.list_dcim_cables_by_endpoint(tenant, endpoint)
        listed_ports = app.dcim_repository.list_dcim_ports_by_owner(tenant, "patch-panel", "PP01")

        assert panel["generated_ports"] == ["P01", "P02", "P03", "P04"]
        assert panel["occupied_units"] == [2]
        assert equipment_port["owner_type"] == "equipment"
        assert operator_port["owner_type"] == "patch_panel"
        assert operator_port["site"] == "CBL1"
        assert cable["length_m"] == 2.346
        assert cable["trace"].startswith("CAB-0001: equipment:SRV-CBL-01:ETH0")
        assert trace["a_port"]["connector"] == "rj45"
        assert trace["b_port"]["owner_code"] == "PP01"
        assert listed_cables[0].cable_id.value == "CAB-0001"
        assert [port.endpoint.port_name.value for port in listed_ports] == [
            "P01",
            "P02",
            "P03",
            "P04",
            "P05",
        ]

    def test_cabling_validation_rejects_missing_conflicting_and_incompatible_links(
        self,
        tmp_path: Path,
    ) -> None:
        app = self._prepared_app(tmp_path)
        with pytest.raises(NotFoundError):
            app.dcim_cabling_service.define_patch_panel(
                DefinePatchPanelCommand(
                    "default",
                    "pytest",
                    "CBL1",
                    "BAT-C",
                    "MMR-C",
                    "UNKNOWN",
                    "PP404",
                    "front",
                    1,
                    1,
                    2,
                    "rj45",
                    "copper",
                )
            )
        with pytest.raises(ValidationError):
            PatchPanel.create(
                TenantId.from_value("default"),
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "BAD",
                "front",
                1,
                1,
                2,
                "rj45",
                "fiber",
            )
        with pytest.raises(ValidationError):
            DcimConnectorType.from_value("bad")
        with pytest.raises(ValidationError):
            DcimCableMedium.from_value("bad")
        with pytest.raises(ValidationError):
            DcimCableStatus.from_value("bad")
        with pytest.raises(ValidationError):
            DcimCablePathSegment.create(0, "invalid")
        with pytest.raises(ValidationError):
            DcimCablePathSegment.create(1, "path", kind="")
        assert DcimConnectorType.SFP.compatible_media() == (
            DcimCableMedium.FIBER,
            DcimCableMedium.DAC,
        )
        with pytest.raises(ValidationError):
            DcimPortOwnerType.from_value("building")
        with pytest.raises(ValidationError):
            PatchPanel.create(
                TenantId.from_value("default"),
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "BAD",
                "",
                1,
                1,
                2,
                "rj45",
                "copper",
            )
        with pytest.raises(ValidationError):
            PatchPanel.create(
                TenantId.from_value("default"),
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "BAD",
                "front",
                0,
                1,
                2,
                "rj45",
                "copper",
            )
        with pytest.raises(ValidationError):
            PatchPanel.create(
                TenantId.from_value("default"),
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "BAD",
                "front",
                1,
                0,
                2,
                "rj45",
                "copper",
            )
        with pytest.raises(ValidationError):
            PatchPanel.create(
                TenantId.from_value("default"),
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "BAD",
                "front",
                1,
                1,
                0,
                "rj45",
                "copper",
            )
        with pytest.raises(ValidationError):
            PatchPanel.create(
                TenantId.from_value("default"),
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "BAD",
                "front",
                1,
                1,
                2,
                "rj45",
                "copper",
                "x" * 161,
            )
        endpoint = DcimPortEndpoint.create("equipment", "SRV-CBL-01", "ETH0")
        with pytest.raises(ValidationError):
            DcimCable.create(
                TenantId.from_value("default"),
                "BAD-CABLE",
                endpoint,
                endpoint,
                "copper",
                "installed",
                (DcimCablePathSegment.create(1, "loop"),),
            )
        with pytest.raises(ValidationError):
            DcimCable.create(
                TenantId.from_value("default"),
                "BAD-CABLE",
                endpoint,
                DcimPortEndpoint.create("patch_panel", "PP01", "P01"),
                "copper",
                "installed",
                (),
            )
        with pytest.raises(ValidationError):
            DcimCable.create(
                TenantId.from_value("default"),
                "BAD-CABLE",
                endpoint,
                DcimPortEndpoint.create("patch_panel", "PP01", "P01"),
                "copper",
                "installed",
                (DcimCablePathSegment.create(1, "path"),),
                length_m=0,
            )
        with pytest.raises(ValidationError):
            DcimCable.create(
                TenantId.from_value("default"),
                "BAD-CABLE",
                endpoint,
                DcimPortEndpoint.create("patch_panel", "PP01", "P01"),
                "copper",
                "installed",
                (DcimCablePathSegment.create(1, "path"),),
                label="x" * 161,
            )
        good_a = DcimPort.create(
            TenantId.from_value("default"),
            "equipment",
            "SRV-CBL-01",
            "ETH0",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "rj45",
            "copper",
        )
        good_b = DcimPort.create(
            TenantId.from_value("default"),
            "patch_panel",
            "PP01",
            "P01",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "rj45",
            "copper",
        )
        good_cable = DcimCable.create(
            TenantId.from_value("default"),
            "CAB-TENANT",
            good_a.endpoint,
            good_b.endpoint,
            "copper",
            "installed",
            (DcimCablePathSegment.create(1, "path"),),
        )
        foreign_port = DcimPort.create(
            TenantId.from_value("other"),
            "patch_panel",
            "PP01",
            "P01",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "rj45",
            "copper",
        )
        with pytest.raises(ValidationError):
            good_cable.assert_compatible_ports(good_a, foreign_port)
        wrong_a = DcimPort.create(
            TenantId.from_value("default"),
            "equipment",
            "SRV-CBL-01",
            "ETH9",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "rj45",
            "copper",
        )
        wrong_b = DcimPort.create(
            TenantId.from_value("default"),
            "patch_panel",
            "PP01",
            "P09",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "rj45",
            "copper",
        )
        with pytest.raises(ValidationError):
            good_cable.assert_compatible_ports(wrong_a, good_b)
        with pytest.raises(ValidationError):
            good_cable.assert_compatible_ports(good_a, wrong_b)
        disabled = DcimPort.create(
            TenantId.from_value("default"),
            "equipment",
            "SRV-CBL-01",
            "ETH1",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "rj45",
            "copper",
            enabled=False,
        )
        with pytest.raises(ValidationError):
            disabled.assert_cable_compatible(DcimCableMedium.COPPER)
        fiber = DcimPort.create(
            TenantId.from_value("default"),
            "equipment",
            "SRV-CBL-01",
            "ETH2",
            "CBL1",
            "BAT-C",
            "MMR-C",
            "lc",
            "fiber",
        )
        with pytest.raises(ValidationError):
            fiber.assert_cable_compatible(DcimCableMedium.COPPER)

        app.dcim_cabling_service.define_patch_panel(
            DefinePatchPanelCommand(
                "default",
                "pytest",
                "CBL1",
                "BAT-C",
                "MMR-C",
                "R01",
                "PP01",
                "front",
                2,
                1,
                2,
                "rj45",
                "copper",
            )
        )
        with pytest.raises(ConflictError):
            app.dcim_cabling_service.define_patch_panel(
                DefinePatchPanelCommand(
                    "default",
                    "pytest",
                    "CBL1",
                    "BAT-C",
                    "MMR-C",
                    "R01",
                    "PP02",
                    "front",
                    2,
                    1,
                    2,
                    "rj45",
                    "copper",
                )
            )
        with pytest.raises(ConflictError):
            app.dcim_cabling_service.define_patch_panel(
                DefinePatchPanelCommand(
                    "default",
                    "pytest",
                    "CBL1",
                    "BAT-C",
                    "MMR-C",
                    "R01",
                    "PP03",
                    "front",
                    6,
                    1,
                    2,
                    "rj45",
                    "copper",
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_cabling_service.define_patch_panel(
                DefinePatchPanelCommand(
                    "default",
                    "pytest",
                    "CBL1",
                    "BAT-C",
                    "MMR-C",
                    "R01",
                    "PP04",
                    "front",
                    8,
                    1,
                    2,
                    "rj45",
                    "copper",
                    port_prefix="",
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_cabling_service.define_port(
                DefineDcimPortCommand(
                    "default", "pytest", "equipment", "UNKNOWN", "ETH0", "rj45", "copper"
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_cabling_service.define_port(
                DefineDcimPortCommand(
                    "default", "pytest", "patch_panel", "PP01", "P99", "rj45", "copper"
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_cabling_service.define_port(
                DefineDcimPortCommand(
                    "default",
                    "pytest",
                    "patch_panel",
                    "UNKNOWN",
                    "P99",
                    "rj45",
                    "copper",
                    site="CBL1",
                    building="BAT-C",
                    room="MMR-C",
                )
            )
        app.dcim_cabling_service.define_port(
            DefineDcimPortCommand(
                "default", "pytest", "equipment", "SRV-CBL-01", "ETH0", "rj45", "copper"
            )
        )
        with pytest.raises(NotFoundError):
            app.dcim_cabling_service.connect_cable(
                ConnectDcimCableCommand(
                    "default",
                    "pytest",
                    "CAB-MISS",
                    "equipment",
                    "SRV-CBL-01",
                    "ETH9",
                    "patch_panel",
                    "PP01",
                    "P01",
                    "copper",
                    path_segments=("path",),
                )
            )
        app.dcim_cabling_service.connect_cable(
            ConnectDcimCableCommand(
                "default",
                "pytest",
                "CAB-OK",
                "equipment",
                "SRV-CBL-01",
                "ETH0",
                "patch_panel",
                "PP01",
                "P01",
                "copper",
                path_segments=("path",),
            )
        )
        with pytest.raises(ConflictError):
            app.dcim_cabling_service.connect_cable(
                ConnectDcimCableCommand(
                    "default",
                    "pytest",
                    "CAB-DUP",
                    "equipment",
                    "SRV-CBL-01",
                    "ETH0",
                    "patch_panel",
                    "PP01",
                    "P02",
                    "copper",
                    path_segments=("path",),
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_cabling_service.trace_cable(TraceDcimCableCommand("default", "pytest", "NOPE"))

    def test_cli_and_http_cabling_endpoints(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        data_path = tmp_path / "cli-state.json"
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "define-room",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--site-code",
                    "CBL2",
                    "--site-name",
                    "CLI DC",
                    "--country",
                    "FR",
                    "--city",
                    "Paris",
                    "--building-code",
                    "BAT-C",
                    "--building-name",
                    "CLI Building",
                    "--floor-index",
                    "1",
                    "--room-code",
                    "MMR-C",
                    "--room-name",
                    "CLI Room",
                    "--row",
                    "A",
                    "--column",
                    "01",
                ]
            )
            == 0
        )
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "define-rack",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--site",
                    "CBL2",
                    "--building",
                    "BAT-C",
                    "--floor",
                    "L01",
                    "--room",
                    "MMR-C",
                    "--rack",
                    "R01",
                    "--row",
                    "A",
                    "--column",
                    "01",
                    "--units",
                    "12",
                    "--face",
                    "front",
                ]
            )
            == 0
        )
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "locate",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--asset-tag",
                    "SRV-CLI-01",
                    "--equipment-name",
                    "CLI Server",
                    "--site",
                    "CBL2",
                    "--building",
                    "BAT-C",
                    "--floor",
                    "L01",
                    "--room",
                    "MMR-C",
                    "--row",
                    "A",
                    "--column",
                    "01",
                    "--rack",
                    "R01",
                    "--u-position",
                    "6",
                    "--rack-face",
                    "front",
                ]
            )
            == 0
        )
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "define-patch-panel",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--site",
                    "CBL2",
                    "--building",
                    "BAT-C",
                    "--room",
                    "MMR-C",
                    "--rack",
                    "R01",
                    "--patch-panel",
                    "PP01",
                    "--rack-face",
                    "front",
                    "--u-position",
                    "2",
                    "--port-count",
                    "2",
                    "--connector",
                    "rj45",
                    "--medium",
                    "copper",
                ]
            )
            == 0
        )
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "define-port",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--owner-type",
                    "equipment",
                    "--owner-code",
                    "SRV-CLI-01",
                    "--port-name",
                    "ETH0",
                    "--connector",
                    "rj45",
                    "--medium",
                    "copper",
                ]
            )
            == 0
        )
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "connect-cable",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--cable-id",
                    "CAB-CLI",
                    "--a-owner-type",
                    "equipment",
                    "--a-owner-code",
                    "SRV-CLI-01",
                    "--a-port-name",
                    "ETH0",
                    "--b-owner-type",
                    "patch_panel",
                    "--b-owner-code",
                    "PP01",
                    "--b-port-name",
                    "P01",
                    "--medium",
                    "copper",
                    "--path",
                    "rack path",
                ]
            )
            == 0
        )
        assert (
            OpenInfraCLI().run(
                [
                    "dcim",
                    "cable-trace",
                    "--data",
                    str(data_path),
                    "--tenant",
                    "default",
                    "--cable-id",
                    "CAB-CLI",
                ]
            )
            == 0
        )
        assert "CAB-CLI" in capsys.readouterr().out

        app = ApplicationFactory().create_json_application(tmp_path / "api-state.json", seed=False)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            self._post_json(
                base_url + "/api/v1/dcim/rooms",
                {
                    "tenant_id": "default",
                    "site_code": "CBL3",
                    "site_name": "API DC",
                    "country": "FR",
                    "city": "Paris",
                    "building_code": "BAT-C",
                    "building_name": "API Building",
                    "floor_code": "F01",
                    "floor_name": "Floor 1",
                    "floor_index": 1,
                    "room_code": "MMR-C",
                    "room_name": "API Room",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/racks",
                {
                    "tenant_id": "default",
                    "site": "CBL3",
                    "building": "BAT-C",
                    "floor": "L01",
                    "room": "MMR-C",
                    "rack": "R01",
                    "row": "A",
                    "column": "01",
                    "units": 12,
                    "faces": ["front"],
                },
            )
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    "default",
                    "pytest",
                    "SRV-API-01",
                    "API Server",
                    "CBL3",
                    "BAT-C",
                    "MMR-C",
                    "A",
                    "01",
                    "R01",
                    6,
                    None,
                    None,
                    None,
                    floor="L01",
                    rack_face="front",
                )
            )
            panel = self._post_json(
                base_url + "/api/v1/dcim/patch-panels",
                {
                    "tenant_id": "default",
                    "site": "CBL3",
                    "building": "BAT-C",
                    "room": "MMR-C",
                    "rack": "R01",
                    "patch_panel": "PP01",
                    "rack_face": "front",
                    "u_position": 2,
                    "port_count": 2,
                    "connector": "rj45",
                    "medium": "copper",
                },
            )
            port = self._post_json(
                base_url + "/api/v1/dcim/ports",
                {
                    "tenant_id": "default",
                    "owner_type": "equipment",
                    "owner_code": "SRV-API-01",
                    "port_name": "ETH0",
                    "connector": "rj45",
                    "medium": "copper",
                },
            )
            cable = self._post_json(
                base_url + "/api/v1/dcim/cables",
                {
                    "tenant_id": "default",
                    "cable_id": "CAB-API",
                    "a_owner_type": "equipment",
                    "a_owner_code": "SRV-API-01",
                    "a_port_name": "ETH0",
                    "b_owner_type": "patch_panel",
                    "b_owner_code": "PP01",
                    "b_port_name": "P01",
                    "medium": "copper",
                    "path_segments": ["api path"],
                },
            )
            trace = self._get_json(
                base_url + "/api/v1/dcim/cable-trace?tenant_id=default&cable_id=CAB-API"
            )

            assert panel["patch_panel"] == "PP01"
            assert port["port_name"] == "ETH0"
            assert cable["cable_id"] == "CAB-API"
            assert trace["b_port"]["owner_code"] == "PP01"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
