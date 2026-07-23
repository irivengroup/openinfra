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
    GetDcimFloorCommand,
    ListDcimFloorsCommand,
    UpdateDcimFloorCommand,
)
from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.domain.countries import CountryCatalog
from openinfra.domain.dcim import Building, BuildingType, DcimGridValidator, FloorNomenclature
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDcimGeneratedBuildingFloors:
    def test_floor_nomenclature_is_building_local_sortable_and_backward_readable(self) -> None:
        assert FloorNomenclature.code(-2) == "L-02"
        assert FloorNomenclature.code(-1) == "L-01"
        assert FloorNomenclature.code(0) == "L00"
        assert FloorNomenclature.code(1) == "L01"
        assert FloorNomenclature.code(100) == "L100"
        assert FloorNomenclature.name(-1) == "Basement 1"
        assert FloorNomenclature.name(0) == "Ground floor"
        assert FloorNomenclature.name(2) == "Level 2"
        for alias in ("L01", "F01", "ETG1", "S1_B1_ETG1"):
            assert FloorNomenclature.level_from_code(alias) == 1
            assert FloorNomenclature.references_same_level(alias, "L01")
        assert FloorNomenclature.references_same_level("L01", "L01")
        assert FloorNomenclature.legacy_code("S1", "B1", -1) == "S1_B1_ETG-1"
        assert FloorNomenclature.is_generated_name("S1/B1/ETG-1", "S1", "B1", -1)
        assert FloorNomenclature.is_generated_name("Sous-sol 1", "S1", "B1", -1)
        assert FloorNomenclature.is_generated_name("Rez-de-chaussée", "S1", "B1", 0)
        assert FloorNomenclature.is_generated_name("Étage 1", "S1", "B1", 1)
        assert not FloorNomenclature.is_generated_name("Executive", "S1", "B1", 1)
        assert FloorNomenclature.level_from_code("UNKNOWN") is None
        assert FloorNomenclature.level_from_code("L-00") is None
        assert FloorNomenclature.level_from_code("L999") is None
        assert FloorNomenclature.level_from_code("ETG999") is None
        with pytest.raises(ValidationError):
            FloorNomenclature.code(-21)
        with pytest.raises(ValidationError):
            FloorNomenclature.code(151)

    def test_building_type_generates_bounded_floors_and_country_options(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.create_site(
            CreateDcimSiteCommand(
                "default",
                "pytest",
                "GEN1",
                "Generated Site",
                "FR",
                "Paris",
                "",
                "1 Rue Generated",
                "75000",
                "gen1@example.invalid",
                "+33100000001",
            )
        )
        building = app.dcim_topology_service.create_building(
            CreateDcimBuildingCommand(
                "default", "pytest", "GEN1", "BAT-G", "Generated Building", "Etages", -1, 2
            )
        )
        assert building["type_batiment"] == "Etages"
        assert building["floor_codes"] == [
            "L-01",
            "L00",
            "L01",
            "L02",
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
        with pytest.raises(ValidationError):
            DcimGridValidator.normalized_unique_codes(("2-1",), "rows")
        with pytest.raises(ValidationError):
            DcimGridValidator.normalized_unique_codes(("",), "rows")
        with pytest.raises(ValidationError):
            DcimGridValidator.normalized_unique_codes(("0-512",), "rows")
        assert DcimGridValidator.normalized_unique_codes(("A-B-C",), "rows") == ("A-B-C",)
        assert DcimGridValidator.normalized_unique_codes(("A-2",), "rows") == ("A-2",)
        options = CountryCatalog.options()
        assert any(
            option == {"value": "FR", "label": "France", "group": "Europe"} for option in options
        )
        assert CountryCatalog.options_as_dict()["items"][0]["label"]

    def test_simple_building_rejects_floor_and_manual_floor_crud(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.create_site(
            CreateDcimSiteCommand(
                "default",
                "pytest",
                "GEN2",
                "Simple Site",
                "FR",
                "Paris",
                "",
                "2 Rue Generated",
                "75000",
                "gen2@example.invalid",
                "+33100000002",
            )
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

    def test_json_state_migrates_legacy_floor_codes_and_preserves_custom_names(
        self, tmp_path: Path
    ) -> None:
        state_path = tmp_path / "state.json"
        factory = ApplicationFactory()
        app = factory.create_json_application(state_path, seed=False)
        app.dcim_topology_service.create_site(
            CreateDcimSiteCommand(
                "default",
                "pytest",
                "MIG1",
                "Migration Site",
                "FR",
                "Paris",
                "",
                "3 Rue Generated",
                "75000",
                "mig1@example.invalid",
                "+33100000003",
            )
        )
        app.dcim_topology_service.create_building(
            CreateDcimBuildingCommand(
                "default", "pytest", "MIG1", "BAT-M", "Migration Building", "floors", 0, 1
            )
        )
        app.dcim_topology_service.create_room(
            CreateDcimRoomCommand(
                "default", "pytest", "MIG1", "BAT-M", "L01", "ROOM-M", "Room", ("0",), ("A",)
            )
        )

        state = json.loads(state_path.read_text(encoding="utf-8"))
        ground = state["floors"].pop("default:MIG1:BAT-M:L00")
        ground["code"] = "MIG1_BAT-M_ETG0"
        ground["name"] = "MIG1/BAT-M/ETG0"
        state["floors"]["default:MIG1:BAT-M:MIG1_BAT-M_ETG0"] = ground
        first = state["floors"].pop("default:MIG1:BAT-M:L01")
        first["code"] = "F01"
        first["name"] = "Executive"
        state["floors"]["default:MIG1:BAT-M:F01"] = first
        state["rooms"]["default:MIG1:BAT-M:ROOM-M"]["floor_code"] = "F01"
        state_path.write_text(json.dumps(state), encoding="utf-8")

        migrated = factory.create_json_application(state_path, seed=False)
        stored = json.loads(state_path.read_text(encoding="utf-8"))
        assert set(stored["floors"]) >= {
            "default:MIG1:BAT-M:L00",
            "default:MIG1:BAT-M:L01",
        }
        assert stored["floors"]["default:MIG1:BAT-M:L00"]["name"] == "Ground floor"
        assert stored["floors"]["default:MIG1:BAT-M:L01"]["name"] == "Executive"
        assert stored["rooms"]["default:MIG1:BAT-M:ROOM-M"]["floor_code"] == "L01"
        assert (
            migrated.dcim_topology_service.get_floor(
                GetDcimFloorCommand("default", "MIG1", "BAT-M", "F01")
            )["code"]
            == "L01"
        )
        assert (
            migrated.dcim_topology_service.get_floor(
                GetDcimFloorCommand("default", "MIG1", "BAT-M", "MIG1_BAT-M_ETG0")
            )["code"]
            == "L00"
        )
