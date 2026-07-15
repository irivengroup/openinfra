from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tests.integration.test_kubernetes_gitops_services import seeded_gitops_application

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


def _post(
    url: str, payload: dict[str, object], token: str | None = None
) -> tuple[int, dict[str, object]]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_kubernetes_gitops_http_routes_are_secured_versioned_and_read_only(tmp_path: Path) -> None:
    app, token, expected, observed = seeded_gitops_application(tmp_path / "gitops-http.json")
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        list_url = (
            base
            + "/api/v1/kubernetes/gitops-states?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"})
        )
        status, _ = _get(list_url)
        assert status == 401
        status, page = _get(list_url, token)
        assert status == 200
        assert page["items"][0]["id"] == expected.id.value  # type: ignore[index]

        exact_url = (
            base
            + "/api/v1/kubernetes/gitops-states/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "state_id": expected.id.value})
        )
        status, exact = _get(exact_url, token)
        assert status == 200
        assert exact["revision"] == "b" * 40
        assert len(exact["resources"]) == 2  # type: ignore[arg-type]

        latest_url = (
            base
            + "/api/v1/kubernetes/gitops-states/latest?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"})
        )
        status, latest = _get(latest_url, token)
        assert status == 200
        assert latest["fingerprint"] == expected.fingerprint

        drift_url = (
            base
            + "/api/v1/kubernetes/gitops-states/drift?"
            + urllib.parse.urlencode(
                {
                    "tenant_id": "default",
                    "expected_state_id": expected.id.value,
                    "observed_snapshot_id": observed.id.value,
                    "actor": "http-test",
                }
            )
        )
        status, drift = _get(drift_url, token)
        assert status == 200
        assert drift["status"] == "drift"
        assert drift["automatic_remediation"] is False

        latest_drift_url = (
            base
            + "/api/v1/kubernetes/gitops-states/latest-drift?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "cluster_key": "cluster-par-01", "actor": "http-test"}
            )
        )
        status, latest_drift = _get(latest_drift_url, token)
        assert status == 200
        assert latest_drift["fingerprint"] == drift["fingerprint"]

        import_payload = {
            "tenant_id": "default",
            "actor": "http-test",
            "cluster_key": "cluster-par-01",
            "repository_ref": "https://git.example.net/platform/kubernetes.git",
            "revision": "c" * 40,
            "source_path": "clusters/prod-par-01",
            "owner": "platform",
            "environment": "production",
            "captured_at": "2026-07-15T08:00:00+00:00",
            "policy": {
                "required_labels": ["app.kubernetes.io/name"],
                "required_annotations": ["openinfra.io/change-ref"],
                "allowed_environments": ["production"],
            },
            "resources": exact["resources"],
        }
        status, imported = _post(
            base + "/api/v1/kubernetes/gitops-states/import", import_payload, token
        )
        assert status == 201
        assert imported["revision"] == "c" * 40
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
