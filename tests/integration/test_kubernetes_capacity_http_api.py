from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tests.integration.test_kubernetes_capacity_services import seeded_capacity_application

from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _get(url: str, token: str | None = None) -> tuple[int, str, str]:
    headers = {"Accept": "*/*"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return (
                response.status,
                response.headers.get_content_type(),
                response.read().decode("utf-8"),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get_content_type(), exc.read().decode("utf-8")


def test_kubernetes_capacity_http_routes_are_secured_bounded_and_exportable(tmp_path: Path) -> None:
    app, token, snapshots = seeded_capacity_application(tmp_path / "state.json")
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        latest_url = (
            base
            + "/api/v1/kubernetes/topologies/latest-capacity?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"})
        )
        status, _, _ = _get(latest_url)
        assert status == 401

        status, content_type, body = _get(latest_url, token)
        payload = json.loads(body)
        assert status == 200 and content_type == "application/json"
        assert payload["snapshot_id"] == snapshots[-1].id.value
        assert payload["cluster"]["cpu_usage_millicores"] == 1500

        trend_url = (
            base
            + "/api/v1/kubernetes/topologies/capacity-trend?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "cluster_key": "cluster-par-01", "limit": 3}
            )
        )
        status, _, body = _get(trend_url, token)
        trend = json.loads(body)
        assert status == 200
        assert trend["snapshots_evaluated"] == 3

        export_url = (
            base
            + "/api/v1/kubernetes/topologies/capacity-export?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "snapshot_id": snapshots[0].id.value, "format": "csv"}
            )
        )
        status, content_type, body = _get(export_url, token)
        assert status == 200 and content_type == "text/csv"
        assert "scope,scope_key,observed_at" in body

        bad_url = (
            base
            + "/api/v1/kubernetes/topologies/capacity-trend?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "cluster_key": "cluster-par-01", "limit": 1}
            )
        )
        status, _, body = _get(bad_url, token)
        assert status == 400 and "between 2 and 96" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
