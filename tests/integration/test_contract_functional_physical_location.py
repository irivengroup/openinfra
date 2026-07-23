from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer
from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL


def _request_json(
    url: str,
    *,
    token: str,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    body = None
    method = "GET"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_equipment_location_is_unambiguous_through_api_and_web_contract(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "l" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "location-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        status, located = _request_json(
            base_url + "/api/v1/dcim/locations",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "asset_tag": "PAR-SRV-CONTRACT-001",
                "equipment_name": "Serveur contrat localisation",
                "site": "PAR1",
                "building": "BAT-A",
                "floor": "F01",
                "room": "MMR1",
                "row": "B",
                "column": "12",
                "rack": "R42",
                "u_position": 10,
                "rack_face": "front",
                "u_height": 2,
                "x": 12.0,
                "y": 4.0,
                "z": 0.0,
            },
        )
        assert status == 201
        assert located["location"] == {
            "site": "PAR1",
            "building": "BAT-A",
            "floor": "F01",
            "room": "MMR1",
            "row": "B",
            "column": "12",
            "zone": None,
            "rack": "R42",
            "u_position": 10,
            "rack_face": "front",
            "u_height": 2,
            "coordinates": {"x": 12.0, "y": 4.0, "z": 0.0},
            "human_readable": (
                "site=PAR1 | building=BAT-A | floor=F01 | room=MMR1 | row=B | "
                "column=12 | rack=R42 | U=10 | face=front | height_u=2 | "
                "xyz=12.00/4.00/0.00"
            ),
        }

        query = urllib.parse.urlencode(
            {
                "tenant_id": "default",
                "asset_tag": "PAR-SRV-CONTRACT-001",
                "format": "json",
            }
        )
        status, locator = _request_json(
            base_url + "/api/v1/dcim/locator-sheet?" + query,
            token=token,
        )
        assert status == 200
        assert locator["asset_tag"] == "PAR-SRV-CONTRACT-001"
        assert locator["human_path"] == located["location"]["human_readable"]
        assert [step["title"] for step in locator["intervention_steps"]] == [
            "Site",
            "Bâtiment",
            "Étage",
            "Salle",
            "Grille",
            "Rack",
            "Coordonnées",
            "Identification terrain",
        ]
        assert "ligne B, colonne 12" in locator["intervention_steps"][4]["instruction"]
        assert "rack R42, face front, position U 10 sur 2 U" in locator[
            "intervention_steps"
        ][5]["instruction"]
        assert str(locator["locator"]["payload"]).startswith("oi:loc:")

        for portal in (REACT_PORTAL.read_text(), RUNTIME_PORTAL.read_text()):
            assert '"id": "dcim-locate-equipment"' in portal
            assert '"path": "/v1/dcim/locations"' in portal
            assert '"id": "dcim-locator-sheet"' in portal
            assert '"path": "/v1/dcim/locator-sheet"' in portal
            for field in (
                "Étage",
                "Salle",
                "Ligne salle",
                "Colonne salle",
                "Rack",
                "Position U",
                "Face rack",
            ):
                assert field in portal
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
