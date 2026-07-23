from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.kubernetes_topology_services import (
    GetKubernetesTopologyCommand,
    GetLatestKubernetesTopologyCommand,
    ImportKubernetesTopologyCommand,
    ListKubernetesTopologiesCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import NotFoundError


def _resources(node: str = "worker-01") -> tuple[dict[str, object], ...]:
    return (
        {"kind": "namespace", "uid": "ns-prod", "name": "production"},
        {
            "kind": "node",
            "uid": f"node-{node}",
            "name": node,
            "physical_path": {"server_key": f"srv-{node}", "site_code": "par-01"},
        },
        {"kind": "workload", "uid": "deploy-api", "name": "api", "namespace": "production"},
        {
            "kind": "pod",
            "uid": f"pod-{node}",
            "name": f"api-{node}",
            "namespace": "production",
            "node_name": node,
            "owner_uid": "deploy-api",
        },
        {
            "kind": "service",
            "uid": "svc-api",
            "name": "api",
            "namespace": "production",
            "target_uids": [f"pod-{node}"],
        },
    )


def _app(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "k" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-admin", ("admin",), token)
    )
    return app, token


def test_kubernetes_topology_import_is_idempotent_audited_filterable_and_versioned(
    tmp_path: Path,
) -> None:
    app, token = _app(tmp_path)
    observed = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
    command = ImportKubernetesTopologyCommand(
        "default",
        token,
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:k8s-prod-par-01",
        observed,
        _resources(),
        "eu-west",
        "par-01",
        "pytest",
    )
    first = app.kubernetes_topology_service.import_snapshot(command)
    assert app.kubernetes_topology_service.import_snapshot(command).id == first.id
    second = app.kubernetes_topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            "default",
            token,
            "cluster-par-01",
            "prod-par-01",
            "kubernetes",
            "v1.34.2",
            "discovery:k8s-prod-par-01",
            observed + timedelta(minutes=10),
            _resources("worker-02"),
            "eu-west",
            "par-01",
            "pytest",
        )
    )
    assert second.id != first.id
    assert (
        app.kubernetes_topology_service.get_snapshot(
            GetKubernetesTopologyCommand("default", token, first.id.value)
        ).fingerprint
        == first.fingerprint
    )
    assert (
        app.kubernetes_topology_service.get_latest_snapshot(
            GetLatestKubernetesTopologyCommand("default", token, "cluster-par-01")
        ).id
        == second.id
    )
    page = app.kubernetes_topology_service.list_snapshots(
        ListKubernetesTopologiesCommand(
            "default",
            token,
            limit=1,
            cluster_key="cluster-par-01",
            provider="kubernetes",
            site_code="par-01",
        )
    )
    assert len(page.items) == 1 and page.next_cursor is not None
    graph = app.kubernetes_topology_service.latest_topology(
        GetLatestKubernetesTopologyCommand("default", token, "cluster-par-01")
    )
    assert graph["fingerprint"] == second.fingerprint
    assert any(edge["external"] for edge in graph["edges"])  # type: ignore[index]
    assert len(app.store.data["kubernetes_topology_event_outbox"]) == 2
    assert any(
        event.get("action") == "kubernetes.topology.imported"
        for event in app.store.data["audit_events"]
    )


def test_kubernetes_topology_service_rejects_unknown_snapshot_and_cluster(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    with pytest.raises(NotFoundError, match="snapshot"):
        app.kubernetes_topology_service.get_snapshot(
            GetKubernetesTopologyCommand("default", token, "00000000-0000-0000-0000-000000000000")
        )
    with pytest.raises(NotFoundError, match="snapshot"):
        app.kubernetes_topology_service.get_latest_snapshot(
            GetLatestKubernetesTopologyCommand("default", token, "unknown-cluster")
        )


def test_kubernetes_dedicated_roles_enforce_read_write_separation(tmp_path: Path) -> None:
    from openinfra.domain.common import AccessDeniedError

    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    operator_token = "o" * 40
    reader_token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            "default", "pytest", "kubernetes-operator", ("kubernetes:operator",), operator_token
        )
    )
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            "default", "pytest", "kubernetes-reader", ("kubernetes:reader",), reader_token
        )
    )
    command = ImportKubernetesTopologyCommand(
        "default",
        operator_token,
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "pytest",
        datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
        _resources(),
        "eu-west",
        "par-01",
        "pytest",
    )
    snapshot = app.kubernetes_topology_service.import_snapshot(command)
    assert (
        app.kubernetes_topology_service.get_snapshot(
            GetKubernetesTopologyCommand("default", reader_token, snapshot.id.value)
        ).id
        == snapshot.id
    )
    with pytest.raises(AccessDeniedError):
        app.kubernetes_topology_service.import_snapshot(
            ImportKubernetesTopologyCommand(
                command.tenant_id,
                reader_token,
                command.cluster_key,
                command.cluster_name,
                command.provider,
                command.kubernetes_version,
                command.source_ref,
                command.observed_at + timedelta(minutes=1),
                command.resources,
                command.region,
                command.site_code,
                command.actor,
            )
        )
