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
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read()
            return response.status, json.loads(body.decode()) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, json.loads(body.decode()) if body else {}


def _resources() -> list[dict[str, object]]:
    return [
        {"kind": "namespace", "uid": "ns-prod", "name": "production"},
        {
            "kind": "node",
            "uid": "node-1",
            "name": "worker-01",
            "physical_path": {
                "vm_key": "vm-k8s-01",
                "hypervisor_key": "esx-01",
                "server_key": "srv-01",
                "rack_id": "rack-a01",
                "room_id": "room-a",
                "site_code": "par-01",
            },
        },
        {"kind": "workload", "uid": "deploy-api", "name": "api", "namespace": "production"},
        {
            "kind": "pod",
            "uid": "pod-api-1",
            "name": "api-abc123",
            "namespace": "production",
            "node_name": "worker-01",
            "owner_uid": "deploy-api",
        },
        {
            "kind": "service",
            "uid": "svc-api",
            "name": "api",
            "namespace": "production",
            "target_uids": ["pod-api-1"],
        },
    ]


def test_kubernetes_topology_http_complete_cycle_and_security(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, _ = _request(base + "/api/v1/kubernetes/topologies?tenant_id=default")
        assert status == 401

        status, imported = _request(
            base + "/api/v1/kubernetes/topologies/import",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "cluster_key": "cluster-par-01",
                "cluster_name": "prod-par-01",
                "provider": "kubernetes",
                "kubernetes_version": "v1.34.1",
                "region": "eu-west",
                "site_code": "par-01",
                "source_ref": "discovery:k8s-prod-par-01",
                "observed_at": "2026-07-14T12:00:00Z",
                "resources": _resources(),
            },
        )
        assert status == 201
        snapshot_id = str(imported["id"])
        assert imported["summary"]["mapping_coverage_percent"] == 100.0  # type: ignore[index]

        query = urllib.parse.urlencode(
            {"tenant_id": "default", "cluster_key": "cluster-par-01", "site_code": "par-01"}
        )
        status, page = _request(base + f"/api/v1/kubernetes/topologies?{query}", token=token)
        assert status == 200 and len(page["items"]) == 1  # type: ignore[arg-type]

        status, fetched = _request(
            base
            + "/api/v1/kubernetes/topologies/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "snapshot_id": snapshot_id}),
            token=token,
        )
        assert status == 200 and len(fetched["resources"]) == 5  # type: ignore[arg-type]

        status, latest = _request(
            base
            + "/api/v1/kubernetes/topologies/latest?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"}),
            token=token,
        )
        assert status == 200 and latest["id"] == snapshot_id

        status, graph = _request(
            base
            + "/api/v1/kubernetes/topologies/latest-topology?"
            + urllib.parse.urlencode({"tenant_id": "default", "cluster_key": "cluster-par-01"}),
            token=token,
        )
        assert status == 200
        assert any(edge["external"] for edge in graph["edges"])  # type: ignore[index]

        status, invalid = _request(
            base + "/api/v1/kubernetes/topologies/import",
            token=token,
            payload={"tenant_id": "default", "resources": {}},
        )
        assert status == 400 and "error" in invalid
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
