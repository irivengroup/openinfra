from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
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


def test_multisite_http_routes_auth_validation_and_complete_cycle(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(
        tmp_path / "state.json", seed=True, edition="pro"
    )
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "multisite-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/api/v1/multisite"
        assert _request(base + "/sites?tenant_id=default")[0] == 401
        status, grant = _request(
            base + "/site-access/grants/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "subject": "http.user",
                "site_code": "PAR1",
                "access_level": "viewer",
            },
        )
        assert status == 200 and grant["site_code"] == "PAR1"

        query = urllib.parse.urlencode(
            {"tenant_id": "default", "subject": "http.user", "active_only": "true"}
        )
        status, grants = _request(base + f"/site-access/grants?{query}", token=token)
        assert status == 200 and len(grants["items"]) == 1  # type: ignore[arg-type]
        status, sites = _request(base + "/sites?tenant_id=default&subject=http.user", token=token)
        assert status == 200 and sites["items"][0]["site_code"] == "PAR1"  # type: ignore[index]

        status, report = _request(
            base + "/reports/generate",
            token=token,
            payload={"tenant_id": "default", "subject": "http.user", "site_codes": ["PAR1"]},
        )
        assert status == 201 and report["totals"]["sites"] == 1  # type: ignore[index]
        report_query = urllib.parse.urlencode({"tenant_id": "default", "report_id": report["id"]})
        assert _request(base + f"/reports/get?{report_query}", token=token)[0] == 200
        status, reports = _request(base + "/reports?tenant_id=default", token=token)
        assert status == 200 and len(reports["items"]) == 1  # type: ignore[arg-type]

        status, error = _request(
            base + "/site-access/grants/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "subject": "http.user",
                "site_code": "UNKNOWN",
                "access_level": "viewer",
            },
        )
        assert status == 400 and "site" in str(error["error"]).lower()
        assert (
            _request(base + "/site-access/grants?tenant_id=default&active_only=maybe", token=token)[
                0
            ]
            == 400
        )

        status, revoked = _request(
            base + "/site-access/grants/revoke",
            token=token,
            payload={"tenant_id": "default", "subject": "http.user", "site_code": "PAR1"},
        )
        assert status == 200 and revoked["active"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
