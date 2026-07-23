from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tests.integration.test_kubernetes_exposure_services import seeded_exposure_application

from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _get(url: str, token: str | None = None) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_kubernetes_exposure_http_routes_are_secured_and_correlated(tmp_path: Path) -> None:
    app, token, snapshot = seeded_exposure_application(tmp_path / "state.json")
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, _ = _get(
            base
            + "/api/v1/kubernetes/topologies/latest-exposure?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"})
        )
        assert status == 401

        status, latest = _get(
            base
            + "/api/v1/kubernetes/topologies/latest-exposure?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"}),
            token,
        )
        assert status == 200
        assert latest["snapshot_id"] == snapshot.id.value
        assert latest["summary"]["external_exposure_count"] == 3  # type: ignore[index]

        status, exact = _get(
            base
            + "/api/v1/kubernetes/topologies/exposure?"
            + urllib.parse.urlencode({"tenant_id": "default", "snapshot_id": snapshot.id.value}),
            token,
        )
        assert status == 200
        assert exact["fingerprint"] == latest["fingerprint"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
