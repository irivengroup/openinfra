from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import TenantId
from openinfra.domain.dcim import Site
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


def test_multisite_disaster_recovery_http_complete_cycle(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(
        tmp_path / "dr-http.json", seed=True, edition="pro"
    )
    token = "w" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "dr-admin", ("admin",), token)
    )
    with app.transaction_manager.begin() as unit_of_work:
        app.dcim_repository.add_site(
            Site.create(
                TenantId.from_value("default"),
                "LON1",
                "London 1",
                "GB",
                "London",
                "England",
                "1 Datacenter Way",
                "E1 1AA",
                "lon1@example.invalid",
                "+442000000001",
            )
        )
        unit_of_work.commit()
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/api/v1/multisite/disaster-recovery"
        assert _request(base + "/plans?tenant_id=default")[0] == 401
        status, plan = _request(
            base + "/plans/configure",
            token=token,
            payload={
                "tenant_id": "default",
                "name": "Paris to London",
                "primary_site_code": "PAR1",
                "recovery_site_code": "LON1",
                "replication_mode": "asynchronous",
                "rpo_seconds": 300,
                "rto_seconds": 1800,
                "max_backup_age_seconds": 86400,
            },
        )
        assert status == 200 and plan["active"] is True
        query = urllib.parse.urlencode({"tenant_id": "default", "plan_id": plan["id"]})
        assert _request(base + f"/plans/get?{query}")[0] == 401
        assert _request(base + "/plans/get?tenant_id=default", token=token)[0] == 400
        assert _request(base + f"/plans/get?{query}", token=token)[0] == 200
        status, plans = _request(base + "/plans?tenant_id=default", token=token)
        assert status == 200 and len(plans["items"]) == 1  # type: ignore[arg-type]

        status, drill = _request(
            base + "/drills/execute",
            token=token,
            payload={
                "tenant_id": "default",
                "plan_id": plan["id"],
                "replication_lag_seconds": 30,
                "backup_age_seconds": 3600,
                "measured_rto_seconds": 600,
                "restore_verified": True,
                "recovery_available": True,
                "vip_reachable": True,
                "operator_confirmed": True,
            },
        )
        assert status == 201 and drill["status"] == "passed"
        drill_query = urllib.parse.urlencode({"tenant_id": "default", "drill_id": drill["id"]})
        assert _request(base + f"/drills/get?{drill_query}", token=token)[0] == 200
        status, drills = _request(
            base + f"/drills?tenant_id=default&plan_id={plan['id']}&status=passed",
            token=token,
        )
        assert status == 200 and len(drills["items"]) == 1  # type: ignore[arg-type]
        assert _request(base + "/drills?tenant_id=default")[0] == 401
        invalid_status, invalid_error = _request(
            base + "/drills?tenant_id=default&status=unknown", token=token
        )
        assert invalid_status == 400 and "passed or failed" in str(invalid_error["error"])

        status, error = _request(
            base + "/drills/execute",
            token=token,
            payload={
                "tenant_id": "default",
                "plan_id": plan["id"],
                "replication_lag_seconds": 0,
                "backup_age_seconds": 0,
                "measured_rto_seconds": 0,
                "restore_verified": "not-a-boolean",
                "recovery_available": True,
                "vip_reachable": True,
                "operator_confirmed": True,
            },
        )
        assert status == 400 and "boolean" in str(error["error"])

        status, disabled = _request(
            base + "/plans/disable",
            token=token,
            payload={"tenant_id": "default", "plan_id": plan["id"]},
        )
        assert status == 200 and disabled["active"] is False
        assert _request(base + "/plans?tenant_id=default&active_only=false", token=token)[0] == 200
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
