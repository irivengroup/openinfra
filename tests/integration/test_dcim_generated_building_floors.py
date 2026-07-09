from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    CreateDcimBuildingCommand,
    CreateDcimFloorCommand,
    CreateDcimRoomCommand,
    CreateDcimSiteCommand,
    DeleteDcimFloorCommand,
    GetDcimBuildingCommand,
    ListDcimFloorsCommand,
    UpdateDcimFloorCommand,
)
from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.domain.countries import CountryCatalog
from openinfra.domain.dcim import Building, BuildingType, DcimGridValidator
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDcimGeneratedBuildingFloors:
    def test_building_type_generates_bounded_floors_and_country_options(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.create_site(
            CreateDcimSiteCommand("default", "pytest", "GEN1", "Generated Site", "FR", "Paris")
        )
        building = app.dcim_topology_service.create_building(
            CreateDcimBuildingCommand(
                "default", "pytest", "GEN1", "BAT-G", "Generated Building", "Etages", -1, 2
            )
        )
        assert building["type_batiment"] == "Etages"
        assert building["floor_codes"] == [
            "GEN1_BAT-G_ETG-1",
            "GEN1_BAT-G_ETG0",
            "GEN1_BAT-G_ETG1",
            "GEN1_BAT-G_ETG2",
        ]
        assert (
            app.dcim_topology_service.get_building(
                GetDcimBuildingCommand("default", "GEN1", "BAT-G")
            )["initial_level"]
            == -1
        )
        assert (
            app.dcim_topology_service.list_floors(
                ListDcimFloorsCommand("default", "GEN1", "BAT-G")
            )["count"]
            == 4
        )
        with pytest.raises(ConflictError):
            app.dcim_topology_service.create_building(
                CreateDcimBuildingCommand("default", "pytest", "GEN1", "BAT-G", "Duplicate")
            )
        with pytest.raises(ValidationError):
            Building.create(TenantId.from_value("default"), "GEN1", "BAD", "Bad", "Etages", 1, 2)
        with pytest.raises(ValidationError):
            Building.create(TenantId.from_value("default"), "GEN1", "BAD", "Bad", "Etages", -21, 2)
        with pytest.raises(ValidationError):
            Building.create(TenantId.from_value("default"), "GEN1", "BAD", "Bad", "Etages", 0, 151)
        with pytest.raises(ValidationError):
            BuildingType.from_value("tower")
        with pytest.raises(ValidationError):
            DcimGridValidator.normalized_unique_codes(("B-A",), "rows")
        options = CountryCatalog.options()
        assert any(
            option == {"value": "FR", "label": "France", "group": "Europe"} for option in options
        )
        assert CountryCatalog.options_as_dict()["items"][0]["label"]

    def test_simple_building_rejects_floor_and_manual_floor_crud(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.create_site(
            CreateDcimSiteCommand("default", "pytest", "GEN2", "Simple Site", "FR", "Paris")
        )
        app.dcim_topology_service.create_building(
            CreateDcimBuildingCommand(
                "default", "pytest", "GEN2", "BAT-S", "Simple Building", "simple"
            )
        )
        app.dcim_topology_service.create_room(
            CreateDcimRoomCommand(
                "default", "pytest", "GEN2", "BAT-S", None, "ROOM1", "Room 1", ("0-2",), ("A-C",)
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_topology_service.create_room(
                CreateDcimRoomCommand(
                    "default", "pytest", "GEN2", "BAT-S", "F01", "ROOM2", "Room 2", ("0",), ("A",)
                )
            )
        for action in (
            lambda: app.dcim_topology_service.create_floor(
                CreateDcimFloorCommand("default", "pytest", "GEN2", "BAT-S", "F01", "Floor", 1)
            ),
            lambda: app.dcim_topology_service.update_floor(
                UpdateDcimFloorCommand("default", "pytest", "GEN2", "BAT-S", "F01", "Floor", 1)
            ),
            lambda: app.dcim_topology_service.delete_floor(
                DeleteDcimFloorCommand("default", "pytest", "GEN2", "BAT-S", "F01")
            ),
        ):
            with pytest.raises(ValidationError):
                action()

    def test_http_legacy_floor_endpoints_remain_non_destructive(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(
                base + "/api/v1/reference/countries", timeout=5
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            assert payload["items"][0]["countries"][0]["name"]
            for route, body in (
                (
                    "/api/v1/dcim/floor/create",
                    {
                        "tenant_id": "default",
                        "site": "GEN",
                        "building": "BAT",
                        "code": "F01",
                        "name": "Floor",
                        "level_index": 1,
                    },
                ),
                (
                    "/api/v1/dcim/floor/update",
                    {
                        "tenant_id": "default",
                        "site": "GEN",
                        "building": "BAT",
                        "code": "F01",
                        "name": "Floor",
                        "level_index": 1,
                        "status": "active",
                    },
                ),
                (
                    "/api/v1/dcim/floor/delete",
                    {"tenant_id": "default", "site": "GEN", "building": "BAT", "code": "F01"},
                ),
            ):
                request = urllib.request.Request(
                    base + route,
                    data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with pytest.raises(urllib.error.HTTPError) as exc_info:
                    urllib.request.urlopen(request, timeout=5)
                assert exc_info.value.code == 400
        finally:
            server.shutdown()
            thread.join(timeout=5)
