from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    CreateDcimBuildingCommand,
    CreateDcimRoomCommand,
    CreateDcimSiteCommand,
    CreateDcimZoneCommand,
    DcimTopologyCatalogCommand,
    DefinePhysicalRoomCommand,
    DefineRackCommand,
    DeleteDcimBuildingCommand,
    DeleteDcimFloorCommand,
    DeleteDcimRoomCommand,
    DeleteDcimSiteCommand,
    DeleteDcimZoneCommand,
    DeleteRackCommand,
    GetDcimBuildingCommand,
    GetDcimFloorCommand,
    GetDcimRoomCommand,
    GetDcimZoneCommand,
    GetRackCommand,
    ListDcimBuildingsCommand,
    ListDcimFloorsCommand,
    ListDcimRoomsCommand,
    ListDcimSitesCommand,
    ListDcimZonesCommand,
    ListRacksCommand,
    UpdateDcimBuildingCommand,
    UpdateDcimFloorCommand,
    UpdateDcimRoomCommand,
    UpdateDcimSiteCommand,
    UpdateDcimZoneCommand,
    UpdateRackCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ValidationError
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDcimSiteLifecycle:
    def test_site_crud_cascade_and_catalog(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)

        created = app.dcim_topology_service.create_site(
            CreateDcimSiteCommand(
                tenant_id="default",
                actor="pytest",
                code="par1",
                name="Paris 1",
                country="fr",
                city="Paris",
                region="IDF",
                street_address="111 Quai du Président Roosevelt",
                postal_code="92130",
                contact_email="par1@example.invalid",
                phone="+33123456789",
            )
        )
        updated = app.dcim_topology_service.update_site(
            UpdateDcimSiteCommand(
                tenant_id="default",
                actor="pytest",
                code="PAR1",
                name="Paris DC 1",
            )
        )

        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="PAR1",
                site_name="Paris DC 1",
                country="FR",
                region="IDF",
                city="Paris",
                building_code="BAT-A",
                building_name="Building A",
                floor_code="F01",
                floor_name="Floor 1",
                floor_index=1,
                room_code="MMR1",
                room_name="Main Room",
                rows=("A",),
                columns=("01",),
                zone_code="Z1",
                zone_name="Zone 1",
            )
        )
        catalog = app.dcim_topology_service.topology_catalog(DcimTopologyCatalogCommand("default"))
        retired = app.dcim_topology_service.delete_site(
            DeleteDcimSiteCommand("default", "pytest", "PAR1")
        )
        active_sites = app.dcim_topology_service.list_sites(ListDcimSitesCommand("default"))
        all_sites = app.dcim_topology_service.list_sites(
            ListDcimSitesCommand("default", include_retired=True)
        )
        retired_catalog = app.dcim_topology_service.topology_catalog(
            DcimTopologyCatalogCommand("default", include_retired=True)
        )

        assert created["code"] == "PAR1"
        assert updated["name"] == "Paris DC 1"
        assert catalog["sites"][0]["buildings"][0]["rooms"][0]["code"] == "MMR1"
        assert retired["status"] == "retired"
        assert active_sites["count"] == 0
        assert all_sites["items"][0]["status"] == "retired"
        building = retired_catalog["sites"][0]["buildings"][0]
        assert building["status"] == "retired"
        assert building["floors"][0]["status"] == "retired"
        assert building["rooms"][0]["status"] == "retired"
        assert building["rooms"][0]["zones"][0]["status"] == "retired"

    def test_dependency_crud_cascade_and_catalog(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        service = app.dcim_topology_service

        service.create_site(
            CreateDcimSiteCommand(
                tenant_id="default",
                actor="pytest",
                code="TLS2",
                name="Toulouse 2",
                country="FR",
                city="Toulouse",
                region="",
                street_address="1 Rue de Toulouse",
                postal_code="31000",
                contact_email="tls2@example.invalid",
                phone="+33500000002",
            )
        )
        building = service.create_building(
            CreateDcimBuildingCommand(
                "default", "pytest", "TLS2", "BAT-A", "Building A", "floors", 0, 1
            )
        )
        floor = service.get_floor(GetDcimFloorCommand("default", "TLS2", "BAT-A", "L01"))
        room = service.create_room(
            CreateDcimRoomCommand(
                "default",
                "pytest",
                "TLS2",
                "BAT-A",
                "L01",
                "MMR1",
                "Main Room",
                ("A",),
                ("01",),
            )
        )
        zone = service.create_zone(
            CreateDcimZoneCommand(
                "default", "pytest", "TLS2", "BAT-A", "MMR1", "Z1", "Zone 1", ("A",), ("01",)
            )
        )
        fetched_building = service.get_building(GetDcimBuildingCommand("default", "TLS2", "BAT-A"))
        updated_building = service.update_building(
            UpdateDcimBuildingCommand("default", "pytest", "TLS2", "BAT-A", name="Building A Prime")
        )
        fetched_floor = service.get_floor(GetDcimFloorCommand("default", "TLS2", "BAT-A", "L01"))
        with pytest.raises(ValidationError, match="generated from building type"):
            service.update_floor(
                UpdateDcimFloorCommand("default", "pytest", "TLS2", "BAT-A", "L01", level_index=2)
            )
        updated_floor = floor
        fetched_room = service.get_room(GetDcimRoomCommand("default", "TLS2", "BAT-A", "MMR1"))
        updated_room = service.update_room(
            UpdateDcimRoomCommand(
                "default", "pytest", "TLS2", "BAT-A", "MMR1", name="Main Meet-Me Room"
            )
        )
        fetched_zone = service.get_zone(
            GetDcimZoneCommand("default", "TLS2", "BAT-A", "MMR1", "Z1")
        )
        updated_zone = service.update_zone(
            UpdateDcimZoneCommand(
                "default", "pytest", "TLS2", "BAT-A", "MMR1", "Z1", name="Zone One"
            )
        )
        listed_buildings = service.list_buildings(ListDcimBuildingsCommand("default", "TLS2"))
        listed_floors = service.list_floors(ListDcimFloorsCommand("default", "TLS2", "BAT-A"))
        listed_rooms = service.list_rooms(ListDcimRoomsCommand("default", "TLS2", "BAT-A"))
        listed_zones = service.list_zones(ListDcimZonesCommand("default", "TLS2", "BAT-A", "MMR1"))
        active_catalog = service.topology_catalog(DcimTopologyCatalogCommand("default"))
        retired_zone = service.delete_zone(
            DeleteDcimZoneCommand("default", "pytest", "TLS2", "BAT-A", "MMR1", "Z1")
        )
        retired_room = service.delete_room(
            DeleteDcimRoomCommand("default", "pytest", "TLS2", "BAT-A", "MMR1")
        )
        with pytest.raises(ValidationError, match="generated from building type"):
            service.delete_floor(
                DeleteDcimFloorCommand("default", "pytest", "TLS2", "BAT-A", "L01")
            )
        retired_floor = floor
        retired = service.delete_building(
            DeleteDcimBuildingCommand("default", "pytest", "TLS2", "BAT-A")
        )
        after_retire = service.topology_catalog(
            DcimTopologyCatalogCommand("default", include_retired=True)
        )

        assert building["code"] == "BAT-A"
        assert floor["level_index"] == 1
        assert room["rows"] == ["A"]
        assert zone["columns"] == ["01"]
        assert fetched_building["code"] == "BAT-A"
        assert updated_building["name"] == "Building A Prime"
        assert fetched_floor["code"] == "L01"
        assert updated_floor["level_index"] == 1
        assert fetched_room["code"] == "MMR1"
        assert updated_room["name"] == "Main Meet-Me Room"
        assert fetched_zone["code"] == "Z1"
        assert updated_zone["name"] == "Zone One"
        assert listed_buildings["count"] == 1
        assert listed_floors["count"] == 2
        assert listed_rooms["count"] == 1
        assert listed_zones["count"] == 1
        assert active_catalog["sites"][0]["buildings"][0]["rooms"][0]["zones"][0]["code"] == "Z1"
        assert retired_zone["status"] == "retired"
        assert retired_room["status"] == "retired"
        assert retired_floor["status"] == "active"
        assert retired["status"] == "retired"
        retired_building = after_retire["sites"][0]["buildings"][0]
        assert retired_building["status"] == "retired"
        assert retired_building["floors"][0]["status"] == "retired"
        assert retired_building["rooms"][0]["status"] == "retired"
        assert retired_building["rooms"][0]["zones"][0]["status"] == "retired"

    def test_dcim_site_cli_contract(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        create_code = OpenInfraCLI().run(
            [
                "dcim",
                "site-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--code",
                "LYO1",
                "--name",
                "Lyon 1",
                "--country",
                "FR",
                "--city",
                "Lyon",
                "--street-address",
                "1 Rue Lyon",
                "--postal-code",
                "75000",
                "--contact-email",
                "site-lyon@example.invalid",
                "--phone",
                "+33123456789",
            ]
        )
        created = json.loads(capsys.readouterr().out)
        get_code = OpenInfraCLI().run(
            ["dcim", "site", "--data", str(data), "--tenant", "default", "--code", "LYO1"]
        )
        fetched = json.loads(capsys.readouterr().out)
        update_code = OpenInfraCLI().run(
            [
                "dcim",
                "site-update",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--code",
                "LYO1",
                "--name",
                "Lyon DC 1",
                "--status",
                "suspended",
            ]
        )
        updated = json.loads(capsys.readouterr().out)
        list_code = OpenInfraCLI().run(
            ["dcim", "sites", "--data", str(data), "--tenant", "default", "--include-retired"]
        )
        listed = json.loads(capsys.readouterr().out)
        catalog_code = OpenInfraCLI().run(
            [
                "dcim",
                "topology-catalog",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--include-retired",
            ]
        )
        catalog = json.loads(capsys.readouterr().out)
        delete_code = OpenInfraCLI().run(
            ["dcim", "site-delete", "--data", str(data), "--tenant", "default", "--code", "LYO1"]
        )
        deleted = json.loads(capsys.readouterr().out)

        assert create_code == 0
        assert get_code == 0
        assert update_code == 0
        assert list_code == 0
        assert catalog_code == 0
        assert delete_code == 0
        assert created["code"] == "LYO1"
        assert fetched["code"] == "LYO1"
        assert updated["name"] == "Lyon DC 1"
        assert updated["status"] == "suspended"
        assert any(item["code"] == "LYO1" for item in listed["items"])
        assert any(site["code"] == "LYO1" for site in catalog["sites"])
        assert deleted["status"] == "retired"

    def test_dcim_dependency_cli_contract(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        commands = [
            [
                "dcim",
                "site-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--code",
                "CLI1",
                "--name",
                "CLI Site",
                "--country",
                "FR",
                "--city",
                "Paris",
                "--street-address",
                "1 Rue Paris",
                "--postal-code",
                "75000",
                "--contact-email",
                "site-paris@example.invalid",
                "--phone",
                "+33123456789",
            ],
            [
                "dcim",
                "building-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI1",
                "--code",
                "BAT-C",
                "--name",
                "Building C",
                "--building-type",
                "floors",
                "--initial-level",
                "0",
                "--final-level",
                "1",
            ],
            [
                "dcim",
                "room-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI1",
                "--building",
                "BAT-C",
                "--floor",
                "L01",
                "--code",
                "RM1",
                "--name",
                "Room 1",
                "--row",
                "A",
                "--column",
                "01",
            ],
            [
                "dcim",
                "zone-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI1",
                "--building",
                "BAT-C",
                "--room",
                "RM1",
                "--code",
                "Z1",
                "--name",
                "Zone 1",
                "--row",
                "A",
                "--column",
                "01",
            ],
            [
                "dcim",
                "zones",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI1",
                "--building",
                "BAT-C",
                "--room",
                "RM1",
            ],
            [
                "dcim",
                "building-delete",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI1",
                "--code",
                "BAT-C",
            ],
        ]
        outputs: list[dict[str, object]] = []
        for command in commands:
            assert OpenInfraCLI().run(command) == 0
            outputs.append(json.loads(capsys.readouterr().out))

        assert outputs[1]["code"] == "BAT-C"
        assert outputs[1]["floor_codes"] == ["L00", "L01"]
        assert outputs[2]["code"] == "RM1"
        assert outputs[3]["code"] == "Z1"
        assert outputs[4]["count"] == 1
        assert outputs[5]["status"] == "retired"

    def test_dcim_site_http_contract(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            created = self._post_json(
                base_url + "/api/v1/dcim/site/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "code": "TLS1",
                    "name": "Toulouse 1",
                    "country": "FR",
                    "city": "Toulouse",
                    "street_address": "1 Rue Toulouse",
                    "postal_code": "31000",
                    "contact_email": "site-toulouse@example.invalid",
                    "phone": "+33512345678",
                },
            )
            fetched = self._get_json(base_url + "/api/v1/dcim/site?tenant_id=default&code=TLS1")
            listed = self._get_json(base_url + "/api/v1/dcim/sites?tenant_id=default")
            catalog = self._get_json(base_url + "/api/v1/dcim/topology-catalog?tenant_id=default")
            updated = self._post_json(
                base_url + "/api/v1/dcim/site/update",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "code": "TLS1",
                    "name": "Toulouse DC 1",
                    "status": "suspended",
                },
            )
            deleted = self._post_json(
                base_url + "/api/v1/dcim/site/delete",
                {"tenant_id": "default", "actor": "pytest", "code": "TLS1"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert created["code"] == "TLS1"
        assert fetched["code"] == "TLS1"
        assert listed["count"] == 1
        assert any(site["code"] == "TLS1" for site in catalog["sites"])
        assert updated["name"] == "Toulouse DC 1"
        assert updated["status"] == "suspended"
        assert deleted["status"] == "retired"

    def test_dcim_dependency_http_contract(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            self._post_json(
                base_url + "/api/v1/dcim/site/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "code": "HTTP1",
                    "name": "HTTP Site",
                    "country": "FR",
                    "city": "Paris",
                    "street_address": "1 Rue Paris",
                    "postal_code": "75000",
                    "contact_email": "site-paris@example.invalid",
                    "phone": "+33123456789",
                },
            )
            building = self._post_json(
                base_url + "/api/v1/dcim/building/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP1",
                    "code": "BAT-H",
                    "name": "Building H",
                    "building_type": "floors",
                    "initial_level": 0,
                    "final_level": 1,
                },
            )
            floor = self._get_json(
                base_url + "/api/v1/dcim/floor?tenant_id=default&site=HTTP1&building=BAT-H&code=L01"
            )
            room = self._post_json(
                base_url + "/api/v1/dcim/room/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP1",
                    "building": "BAT-H",
                    "floor": "L01",
                    "code": "RM1",
                    "name": "Room 1",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            zone = self._post_json(
                base_url + "/api/v1/dcim/zone/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP1",
                    "building": "BAT-H",
                    "room": "RM1",
                    "code": "Z1",
                    "name": "Zone 1",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            rooms = self._get_json(
                base_url + "/api/v1/dcim/rooms?tenant_id=default&site=HTTP1&building=BAT-H"
            )
            zones = self._get_json(
                base_url + "/api/v1/dcim/zones?tenant_id=default&site=HTTP1&building=BAT-H&room=RM1"
            )
            deleted = self._post_json(
                base_url + "/api/v1/dcim/room/delete",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP1",
                    "building": "BAT-H",
                    "code": "RM1",
                },
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert building["code"] == "BAT-H"
        assert floor["code"] == "L01"
        assert room["code"] == "RM1"
        assert zone["code"] == "Z1"
        assert rooms["count"] == 1
        assert zones["items"][0]["code"] == "Z1"
        assert deleted["status"] == "retired"

    def test_dcim_dependency_cli_full_lifecycle_contract(
        self, tmp_path: Path, capsys: object
    ) -> None:
        data = tmp_path / "state-full-cli.json"
        common = ["--data", str(data), "--tenant", "default"]
        commands = [
            [
                "dcim",
                "site-create",
                *common,
                "--code",
                "CLI2",
                "--name",
                "CLI Site 2",
                "--country",
                "FR",
                "--city",
                "Paris",
                "--street-address",
                "1 Rue Paris",
                "--postal-code",
                "75000",
                "--contact-email",
                "site-paris@example.invalid",
                "--phone",
                "+33123456789",
            ],
            [
                "dcim",
                "building-create",
                *common,
                "--site",
                "CLI2",
                "--code",
                "BAT-D",
                "--name",
                "Building D",
                "--building-type",
                "floors",
                "--initial-level",
                "0",
                "--final-level",
                "1",
            ],
            [
                "dcim",
                "room-create",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--floor",
                "L01",
                "--code",
                "RM1",
                "--name",
                "Room 1",
                "--row",
                "A",
                "--column",
                "01",
            ],
            [
                "dcim",
                "zone-create",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--room",
                "RM1",
                "--code",
                "Z1",
                "--name",
                "Zone 1",
                "--row",
                "A",
                "--column",
                "01",
            ],
            ["dcim", "buildings", *common, "--site", "CLI2"],
            ["dcim", "building", *common, "--site", "CLI2", "--code", "BAT-D"],
            [
                "dcim",
                "building-update",
                *common,
                "--site",
                "CLI2",
                "--code",
                "BAT-D",
                "--name",
                "Building Delta",
            ],
            ["dcim", "floors", *common, "--site", "CLI2", "--building", "BAT-D"],
            [
                "dcim",
                "floor",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--code",
                "L01",
            ],
            ["dcim", "rooms", *common, "--site", "CLI2", "--building", "BAT-D"],
            ["dcim", "room", *common, "--site", "CLI2", "--building", "BAT-D", "--code", "RM1"],
            [
                "dcim",
                "room-update",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--code",
                "RM1",
                "--name",
                "Room One",
                "--row",
                "A",
                "--column",
                "01",
            ],
            ["dcim", "zones", *common, "--site", "CLI2", "--building", "BAT-D", "--room", "RM1"],
            [
                "dcim",
                "zone",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--room",
                "RM1",
                "--code",
                "Z1",
            ],
            [
                "dcim",
                "zone-update",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--room",
                "RM1",
                "--code",
                "Z1",
                "--name",
                "Zone One",
                "--row",
                "A",
                "--column",
                "01",
            ],
            [
                "dcim",
                "zone-delete",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--room",
                "RM1",
                "--code",
                "Z1",
            ],
            [
                "dcim",
                "room-delete",
                *common,
                "--site",
                "CLI2",
                "--building",
                "BAT-D",
                "--code",
                "RM1",
            ],
            ["dcim", "building-delete", *common, "--site", "CLI2", "--code", "BAT-D"],
        ]
        outputs: list[dict[str, object]] = []
        for command in commands:
            assert OpenInfraCLI().run(command) == 0
            outputs.append(json.loads(capsys.readouterr().out))

        assert outputs[4]["count"] == 1
        assert outputs[6]["name"] == "Building Delta"
        assert outputs[7]["count"] == 2
        assert outputs[8]["code"] == "L01"
        assert outputs[9]["count"] == 1
        assert outputs[11]["name"] == "Room One"
        assert outputs[12]["count"] == 1
        assert outputs[14]["name"] == "Zone One"
        assert outputs[15]["status"] == "retired"
        assert outputs[16]["status"] == "retired"
        assert outputs[17]["status"] == "retired"

    def test_dcim_dependency_http_full_lifecycle_contract(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(
            tmp_path / "state-full-http.json", seed=False
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            self._post_json(
                base_url + "/api/v1/dcim/site/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "code": "HTTP2",
                    "name": "HTTP Site 2",
                    "country": "FR",
                    "city": "Paris",
                    "street_address": "1 Rue Paris",
                    "postal_code": "75000",
                    "contact_email": "site-paris@example.invalid",
                    "phone": "+33123456789",
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/building/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "code": "BAT-H2",
                    "name": "Building H2",
                    "building_type": "floors",
                    "initial_level": 0,
                    "final_level": 1,
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/room/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "building": "BAT-H2",
                    "floor": "L01",
                    "code": "RM1",
                    "name": "Room 1",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/zone/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "building": "BAT-H2",
                    "room": "RM1",
                    "code": "Z1",
                    "name": "Zone 1",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            buildings = self._get_json(
                base_url + "/api/v1/dcim/buildings?tenant_id=default&site=HTTP2"
            )
            building = self._get_json(
                base_url + "/api/v1/dcim/building?tenant_id=default&site=HTTP2&code=BAT-H2"
            )
            building_update = self._post_json(
                base_url + "/api/v1/dcim/building/update",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "code": "BAT-H2",
                    "name": "Building HTTP 2",
                },
            )
            floors = self._get_json(
                base_url + "/api/v1/dcim/floors?tenant_id=default&site=HTTP2&building=BAT-H2"
            )
            floor = self._get_json(
                base_url
                + "/api/v1/dcim/floor?tenant_id=default&site=HTTP2&building=BAT-H2&code=L01"
            )
            floor_update = floor
            rooms = self._get_json(
                base_url + "/api/v1/dcim/rooms?tenant_id=default&site=HTTP2&building=BAT-H2"
            )
            room = self._get_json(
                base_url + "/api/v1/dcim/room?tenant_id=default&site=HTTP2&building=BAT-H2&code=RM1"
            )
            room_update = self._post_json(
                base_url + "/api/v1/dcim/room/update",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "building": "BAT-H2",
                    "code": "RM1",
                    "name": "Room One",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            zones = self._get_json(
                base_url
                + "/api/v1/dcim/zones?tenant_id=default&site=HTTP2&building=BAT-H2&room=RM1"
            )
            zone = self._get_json(
                base_url
                + "/api/v1/dcim/zone?tenant_id=default&site=HTTP2&building=BAT-H2&room=RM1&code=Z1"
            )
            zone_update = self._post_json(
                base_url + "/api/v1/dcim/zone/update",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "building": "BAT-H2",
                    "room": "RM1",
                    "code": "Z1",
                    "name": "Zone One",
                    "rows": ["A"],
                    "columns": ["01"],
                },
            )
            zone_delete = self._post_json(
                base_url + "/api/v1/dcim/zone/delete",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "building": "BAT-H2",
                    "room": "RM1",
                    "code": "Z1",
                },
            )
            room_delete = self._post_json(
                base_url + "/api/v1/dcim/room/delete",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTP2",
                    "building": "BAT-H2",
                    "code": "RM1",
                },
            )
            floor_delete = floor
            building_delete = self._post_json(
                base_url + "/api/v1/dcim/building/delete",
                {"tenant_id": "default", "actor": "pytest", "site": "HTTP2", "code": "BAT-H2"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert buildings["count"] == 1
        assert building["code"] == "BAT-H2"
        assert building_update["name"] == "Building HTTP 2"
        assert floors["count"] == 2
        assert floor["code"] == "L01"
        assert floor_update["level_index"] == 1
        assert rooms["count"] == 1
        assert room["code"] == "RM1"
        assert room_update["name"] == "Room One"
        assert zones["count"] == 1
        assert zone["code"] == "Z1"
        assert zone_update["name"] == "Zone One"
        assert zone_delete["status"] == "retired"
        assert room_delete["status"] == "retired"
        assert floor_delete["status"] == "active"
        assert building_delete["status"] == "retired"

    def test_dcim_dependency_http_auth_and_error_branches(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(
            tmp_path / "state-auth-http.json", seed=False
        )
        token = "d" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "dcim-admin", ("admin",), token)
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            self._post_json(
                base_url + "/api/v1/dcim/site/create",
                {
                    "tenant_id": "default",
                    "code": "AUTH1",
                    "name": "Auth Site",
                    "country": "FR",
                    "city": "Paris",
                    "street_address": "1 Rue Paris",
                    "postal_code": "75000",
                    "contact_email": "site-paris@example.invalid",
                    "phone": "+33123456789",
                },
                token=token,
            )
            self._post_json(
                base_url + "/api/v1/dcim/building/create",
                {
                    "tenant_id": "default",
                    "site": "AUTH1",
                    "code": "BAT-A",
                    "name": "Auth Building",
                    "building_type": "floors",
                    "initial_level": 0,
                    "final_level": 1,
                },
                token=token,
            )
            self._post_json(
                base_url + "/api/v1/dcim/room/create",
                {
                    "tenant_id": "default",
                    "site": "AUTH1",
                    "building": "BAT-A",
                    "floor": "L01",
                    "code": "RM1",
                    "name": "Auth Room",
                    "rows": ["A"],
                    "columns": ["01"],
                },
                token=token,
            )
            self._post_json(
                base_url + "/api/v1/dcim/zone/create",
                {
                    "tenant_id": "default",
                    "site": "AUTH1",
                    "building": "BAT-A",
                    "room": "RM1",
                    "code": "Z1",
                    "name": "Auth Zone",
                    "rows": ["A"],
                    "columns": ["01"],
                },
                token=token,
            )

            authorized_gets = (
                "/api/v1/dcim/sites?tenant_id=default",
                "/api/v1/dcim/site?tenant_id=default&code=AUTH1",
                "/api/v1/dcim/buildings?tenant_id=default&site=AUTH1",
                "/api/v1/dcim/building?tenant_id=default&site=AUTH1&code=BAT-A",
                "/api/v1/dcim/floors?tenant_id=default&site=AUTH1&building=BAT-A",
                "/api/v1/dcim/floor?tenant_id=default&site=AUTH1&building=BAT-A&code=L01",
                "/api/v1/dcim/rooms?tenant_id=default&site=AUTH1&building=BAT-A",
                "/api/v1/dcim/room?tenant_id=default&site=AUTH1&building=BAT-A&code=RM1",
                "/api/v1/dcim/zones?tenant_id=default&site=AUTH1&building=BAT-A&room=RM1",
                "/api/v1/dcim/zone?tenant_id=default&site=AUTH1&building=BAT-A&room=RM1&code=Z1",
            )
            for route in authorized_gets:
                assert self._get_json(base_url + route, token=token)

            for route in authorized_gets:
                try:
                    self._get_json(base_url + route)
                except Exception as exc:
                    assert getattr(exc, "code", None) == 401

            for route in (
                "/api/v1/dcim/building/update",
                "/api/v1/dcim/building/delete",
                "/api/v1/dcim/room/update",
                "/api/v1/dcim/room/delete",
                "/api/v1/dcim/zone/update",
                "/api/v1/dcim/zone/delete",
            ):
                try:
                    self._post_json(base_url + route, {"tenant_id": "default"}, token=token)
                except Exception as exc:
                    assert getattr(exc, "code", None) == 400

            assert (
                self._post_json(
                    base_url + "/api/v1/dcim/zone/delete",
                    {
                        "tenant_id": "default",
                        "site": "AUTH1",
                        "building": "BAT-A",
                        "room": "RM1",
                        "code": "Z1",
                    },
                    token=token,
                )["status"]
                == "retired"
            )
            assert (
                self._post_json(
                    base_url + "/api/v1/dcim/room/delete",
                    {"tenant_id": "default", "site": "AUTH1", "building": "BAT-A", "code": "RM1"},
                    token=token,
                )["status"]
                == "retired"
            )
            assert (
                self._post_json(
                    base_url + "/api/v1/dcim/building/delete",
                    {"tenant_id": "default", "site": "AUTH1", "code": "BAT-A"},
                    token=token,
                )["status"]
                == "retired"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_room_floor_is_required_only_when_building_has_active_floors(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        service = app.dcim_topology_service
        service.create_site(
            CreateDcimSiteCommand(
                "default",
                "pytest",
                "NTE1",
                "Nantes 1",
                "FR",
                "Nantes",
                "",
                "1 Rue de Nantes",
                "44000",
                "nte1@example.invalid",
                "+33200000001",
            )
        )
        service.create_building(
            CreateDcimBuildingCommand("default", "pytest", "NTE1", "BAT-PLAIN", "Plain")
        )
        no_floor_room = service.create_room(
            CreateDcimRoomCommand(
                "default",
                "pytest",
                "NTE1",
                "BAT-PLAIN",
                None,
                "RDC1",
                "Plain room",
                ("0-2",),
                ("A-C",),
            )
        )
        service.create_building(
            CreateDcimBuildingCommand(
                "default", "pytest", "NTE1", "BAT-TOWER", "Tower", "floors", 0, 1
            )
        )
        with pytest.raises(ValidationError, match="room floor is mandatory"):
            service.create_room(
                CreateDcimRoomCommand(
                    "default",
                    "pytest",
                    "NTE1",
                    "BAT-TOWER",
                    None,
                    "ROOM1",
                    "Tower room",
                    ("0-2",),
                    ("A-C",),
                )
            )
        with_floor_room = service.create_room(
            CreateDcimRoomCommand(
                "default",
                "pytest",
                "NTE1",
                "BAT-TOWER",
                "L01",
                "ROOM1",
                "Tower room",
                ("0-2",),
                ("A-C",),
            )
        )

        assert no_floor_room["floor"] is None
        assert no_floor_room["rows"] == ["0", "1", "2"]
        assert no_floor_room["columns"] == ["A", "B", "C"]
        assert with_floor_room["floor"] == "L01"

    def test_rack_crud_lifecycle_and_cascade(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        topology = app.dcim_topology_service
        racks = app.dcim_rack_service
        topology.create_site(
            CreateDcimSiteCommand(
                "default",
                "pytest",
                "LIL1",
                "Lille 1",
                "FR",
                "Lille",
                "",
                "1 Rue de Lille",
                "59000",
                "lil1@example.invalid",
                "+33300000001",
            )
        )
        topology.create_building(
            CreateDcimBuildingCommand("default", "pytest", "LIL1", "BAT-A", "Building A")
        )
        topology.create_room(
            CreateDcimRoomCommand(
                "default", "pytest", "LIL1", "BAT-A", None, "RM1", "Room 1", ("0-2",), ("A-C",)
            )
        )
        created = racks.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="LIL1",
                building="BAT-A",
                room="RM1",
                rack="RK1",
                row="1",
                column="B",
                units=42,
                usable_faces=("front", "rear"),
            )
        )
        fetched = racks.get_rack(GetRackCommand("default", "LIL1", "BAT-A", "RM1", "RK1"))
        listed = racks.list_racks(ListRacksCommand("default", "LIL1", "BAT-A", "RM1"))
        updated = racks.update_rack(
            UpdateRackCommand(
                tenant_id="default",
                actor="pytest",
                site="LIL1",
                building="BAT-A",
                room="RM1",
                rack="RK1",
                units=48,
                status="suspended",
            )
        )
        active_after_suspend = racks.list_racks(ListRacksCommand("default", "LIL1", "BAT-A", "RM1"))
        all_after_suspend = racks.list_racks(
            ListRacksCommand("default", "LIL1", "BAT-A", "RM1", include_retired=True)
        )
        reactivated = racks.update_rack(
            UpdateRackCommand(
                tenant_id="default",
                actor="pytest",
                site="LIL1",
                building="BAT-A",
                room="RM1",
                rack="RK1",
                status="active",
            )
        )
        retired = racks.delete_rack(
            DeleteRackCommand("default", "pytest", "LIL1", "BAT-A", "RM1", "RK1")
        )

        assert created["code"] == "RK1"
        assert fetched["rack"] == "RK1"
        assert listed["count"] == 1
        assert updated["units"] == 48
        assert updated["status"] == "suspended"
        assert active_after_suspend["count"] == 0
        assert all_after_suspend["count"] == 1
        assert reactivated["status"] == "active"
        assert retired["status"] == "retired"

    def test_dcim_rack_cli_contract_with_grid_ranges(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        commands = [
            [
                "dcim",
                "site-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--code",
                "CLI-R",
                "--name",
                "CLI Rack",
                "--country",
                "FR",
                "--city",
                "Paris",
                "--street-address",
                "1 Rue Paris",
                "--postal-code",
                "75000",
                "--contact-email",
                "site-paris@example.invalid",
                "--phone",
                "+33123456789",
            ],
            [
                "dcim",
                "building-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--code",
                "BAT-R",
                "--name",
                "Rack building",
            ],
            [
                "dcim",
                "room-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--building",
                "BAT-R",
                "--code",
                "RM1",
                "--name",
                "Room 1",
                "--row-range",
                "0-2",
                "--column-range",
                "A-C",
            ],
            [
                "dcim",
                "define-rack",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--building",
                "BAT-R",
                "--room",
                "RM1",
                "--rack",
                "RK1",
                "--row",
                "1",
                "--column",
                "B",
                "--units",
                "42",
                "--face",
                "front",
                "--face",
                "rear",
            ],
            [
                "dcim",
                "rack",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--building",
                "BAT-R",
                "--room",
                "RM1",
                "--rack",
                "RK1",
            ],
            [
                "dcim",
                "racks",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--building",
                "BAT-R",
                "--room",
                "RM1",
            ],
            [
                "dcim",
                "rack-update",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--building",
                "BAT-R",
                "--room",
                "RM1",
                "--rack",
                "RK1",
                "--units",
                "48",
            ],
            [
                "dcim",
                "rack-delete",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "CLI-R",
                "--building",
                "BAT-R",
                "--room",
                "RM1",
                "--rack",
                "RK1",
            ],
        ]

        outputs = []
        for command in commands:
            assert OpenInfraCLI().run(command) == 0
            outputs.append(json.loads(capsys.readouterr().out))

        assert outputs[2]["rows"] == ["0", "1", "2"]
        assert outputs[2]["floor"] is None
        assert outputs[3]["rack"] == "RK1"
        assert outputs[4]["code"] == "RK1"
        assert outputs[5]["count"] == 1
        assert outputs[6]["units"] == 48
        assert outputs[7]["status"] == "retired"

    def test_dcim_rack_http_contract(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=False)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            self._post_json(
                base_url + "/api/v1/dcim/site/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "code": "HTTPR",
                    "name": "HTTP Rack",
                    "country": "FR",
                    "city": "Paris",
                    "street_address": "1 Rue Paris",
                    "postal_code": "75000",
                    "contact_email": "site-paris@example.invalid",
                    "phone": "+33123456789",
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/building/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTPR",
                    "code": "BAT-R",
                    "name": "Rack building",
                },
            )
            room = self._post_json(
                base_url + "/api/v1/dcim/room/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTPR",
                    "building": "BAT-R",
                    "code": "RM1",
                    "name": "Room 1",
                    "rows": ["0-2"],
                    "columns": ["A-C"],
                },
            )
            created = self._post_json(
                base_url + "/api/v1/dcim/racks",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTPR",
                    "building": "BAT-R",
                    "room": "RM1",
                    "rack": "RK1",
                    "row": "1",
                    "column": "B",
                    "units": 42,
                    "faces": ["front", "rear"],
                },
            )
            listed = self._get_json(
                base_url + "/api/v1/dcim/racks?tenant_id=default&site=HTTPR&building=BAT-R&room=RM1"
            )
            fetched = self._get_json(
                base_url
                + "/api/v1/dcim/rack?tenant_id=default&site=HTTPR&building=BAT-R&room=RM1&rack=RK1"
            )
            updated = self._post_json(
                base_url + "/api/v1/dcim/rack/update",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTPR",
                    "building": "BAT-R",
                    "room": "RM1",
                    "rack": "RK1",
                    "units": 48,
                },
            )
            deleted = self._post_json(
                base_url + "/api/v1/dcim/rack/delete",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "site": "HTTPR",
                    "building": "BAT-R",
                    "room": "RM1",
                    "rack": "RK1",
                },
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert room["floor"] is None
        assert created["rack"] == "RK1"
        assert listed["count"] == 1
        assert fetched["code"] == "RK1"
        assert updated["units"] == 48
        assert deleted["status"] == "retired"

    def _post_json(
        self, url: str, payload: dict[str, object], token: str | None = None
    ) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, url: str, token: str | None = None) -> dict[str, object]:
        headers = {"Authorization": "Bearer " + token} if token is not None else {}
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
