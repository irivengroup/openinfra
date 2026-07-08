from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    CreateDcimSiteCommand,
    DcimTopologyCatalogCommand,
    DefinePhysicalRoomCommand,
    DeleteDcimSiteCommand,
    ListDcimSitesCommand,
    UpdateDcimSiteCommand,
)
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

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, url: str) -> dict[str, object]:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
