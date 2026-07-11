from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _request_json(
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_simulation_http_create_run_get_list_and_compare(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "u" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "simulation-admin", ("admin",), token)
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            "default",
            "pytest",
            token,
            "server:http-001",
            "server",
            "Serveur HTTP 001",
            json.dumps({"site": "par1", "rack": "r01", "power_watts": 500}),
            ("production",),
            "pytest",
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        report_ids: list[str] = []
        for index, kind in enumerate(("equipment-move", "equipment-outage"), start=1):
            after: dict[str, object] = {"site": "par2", "rack": f"r2{index}"}
            if kind == "equipment-outage":
                after = {}
            status, created = _request_json(
                base + "/api/v1/simulation-scenarios/create",
                token=token,
                payload={
                    "tenant_id": "default",
                    "actor": "pytest",
                    "name": f"Simulation HTTP {index}",
                    "description": "Valider le contrat HTTP de simulation et comparaison.",
                    "owner": "architecture.team",
                    "idempotency_key": f"simulation-http-000{index}",
                    "site": "par1",
                    "changes": [
                        {
                            "kind": kind,
                            "target_key": "server:http-001",
                            "after": after,
                        }
                    ],
                },
            )
            assert status == 201
            scenario_id = str(created["id"])
            status, report = _request_json(
                base + "/api/v1/simulation-scenarios/run",
                token=token,
                payload={
                    "tenant_id": "default",
                    "actor": "pytest",
                    "scenario_id": scenario_id,
                    "max_depth": 6,
                    "max_nodes": 1000,
                },
            )
            assert status == 200
            assert report["production_mutation"] is False
            report_ids.append(str(report["id"]))

            get_url = (
                base
                + "/api/v1/simulation-scenarios/get?"
                + urllib.parse.urlencode({"tenant_id": "default", "scenario_id": scenario_id})
            )
            status, fetched = _request_json(get_url, token=token)
            assert status == 200
            assert fetched["status"] == "completed"

        status, comparison = _request_json(
            base + "/api/v1/scenario-comparisons/create",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "left_report_id": report_ids[0],
                "right_report_id": report_ids[1],
            },
        )
        assert status == 201
        assert comparison["left_report_id"] == report_ids[0]

        list_url = (
            base
            + "/api/v1/impact-reports?"
            + urllib.parse.urlencode({"tenant_id": "default", "limit": 10})
        )
        status, reports = _request_json(list_url, token=token)
        assert status == 200
        assert len(reports["items"]) == 2

        unauthorized, payload = _request_json(list_url)
        assert unauthorized == 401
        assert "token" in str(payload["error"]).lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
