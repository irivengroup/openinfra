from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import EnrollDiscoveryProxyCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _request(
    url: str, *, token: str | None = None, payload: dict[str, object] | None = None
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
    request = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_enterprise_multisite_regional_discovery_http_cycle(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(
        tmp_path / "state.json", seed=True, edition="enterprise"
    )
    token = "z" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "enterprise-admin", ("admin",), token)
    )
    scope = "region/eu-west/site/par1/vrf/prod"
    collector = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            "default",
            "pytest",
            token,
            "EU West regional proxy",
            "network-proxy",
            "e" * 64,
            (scope,),
            "0.29.103",
            "https://regional-agent.example.invalid:8443",
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/api/v1/multisite/regional-discovery"
        assert _request(base + "/routes?tenant_id=default")[0] == 401
        status, route = _request(
            base + "/routes/configure",
            token=token,
            payload={
                "tenant_id": "default",
                "region_code": "EU-WEST",
                "site_code": "PAR1",
                "vrf_code": "PROD",
                "collector_id": collector.id.value,
            },
        )
        assert status == 200 and route["discovery_scope"] == scope

        query = urllib.parse.urlencode({"tenant_id": "default", "region_code": "EU-WEST"})
        status, routes = _request(base + f"/routes?{query}", token=token)
        assert status == 200 and routes["items"][0]["id"] == route["id"]  # type: ignore[index]
        get_query = urllib.parse.urlencode({"tenant_id": "default", "route_id": route["id"]})
        assert _request(base + f"/routes/get?{get_query}", token=token)[0] == 200

        status, dispatch = _request(
            base + "/jobs/route",
            token=token,
            payload={
                "tenant_id": "default",
                "region_code": "EU-WEST",
                "site_code": "PAR1",
                "vrf_code": "PROD",
                "job_type": "network-inventory",
                "target": "10.20.0.0/24",
                "idempotency_key": "http-regional-route-0001",
            },
        )
        assert status == 201 and dispatch["job"]["collector_id"] == collector.id.value  # type: ignore[index]

        status, disabled = _request(
            base + "/routes/disable",
            token=token,
            payload={"tenant_id": "default", "route_id": route["id"]},
        )
        assert status == 200 and disabled["active"] is False
        assert _request(base + f"/routes/get?{get_query}", token=token)[0] == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
