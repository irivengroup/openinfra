from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.kubernetes_topology_services import (
    GetKubernetesCapacityCommand,
    GetKubernetesCapacityTrendCommand,
    GetLatestKubernetesCapacityCommand,
    ImportKubernetesTopologyCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import NotFoundError, ValidationError


def _resources(cpu_usage: int) -> tuple[dict[str, object], ...]:
    gib = 1024**3
    return (
        {"kind": "namespace", "uid": "ns-prod", "name": "production"},
        {
            "kind": "node",
            "uid": "node-1",
            "name": "worker-01",
            "attributes": {
                "capacity": {
                    "cpu_capacity_millicores": 4000,
                    "memory_capacity_bytes": 16 * gib,
                }
            },
        },
        {
            "kind": "pod",
            "uid": "pod-api",
            "name": "api-1",
            "namespace": "production",
            "attributes": {
                "capacity": {
                    "cpu_request_millicores": 1000,
                    "cpu_limit_millicores": 2000,
                    "cpu_usage_millicores": cpu_usage,
                    "memory_request_bytes": 2 * gib,
                    "memory_limit_bytes": 4 * gib,
                    "memory_usage_bytes": 3 * gib,
                }
            },
        },
    )


def _app(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "k" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-admin", ("admin",), token)
    )
    return app, token


def seeded_capacity_application(state: Path):
    app = ApplicationFactory().create_json_application(state, seed=False)
    token = "k" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-admin", ("admin",), token)
    )
    observed = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
    snapshots = []
    for index, usage in enumerate((500, 1000, 1500)):
        snapshots.append(
            app.kubernetes_topology_service.import_snapshot(
                ImportKubernetesTopologyCommand(
                    "default",
                    token,
                    "cluster-par-01",
                    "prod-par-01",
                    "kubernetes",
                    "v1.34.1",
                    f"pytest:{index}",
                    observed + timedelta(minutes=index * 10),
                    _resources(usage),
                )
            )
        )
    return app, token, tuple(snapshots)


def test_capacity_service_reports_latest_snapshot_and_bounded_trend(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    observed = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
    snapshots = []
    for index, usage in enumerate((500, 1000, 1500)):
        snapshots.append(
            app.kubernetes_topology_service.import_snapshot(
                ImportKubernetesTopologyCommand(
                    "default",
                    token,
                    "cluster-par-01",
                    "prod-par-01",
                    "kubernetes",
                    "v1.34.1",
                    f"pytest:{index}",
                    observed + timedelta(minutes=index * 10),
                    _resources(usage),
                )
            )
        )

    exact = app.kubernetes_topology_service.capacity(
        GetKubernetesCapacityCommand("default", token, snapshots[0].id.value)
    )
    latest = app.kubernetes_topology_service.latest_capacity(
        GetLatestKubernetesCapacityCommand("default", token, "cluster-par-01")
    )
    trend = app.kubernetes_topology_service.capacity_trend(
        GetKubernetesCapacityTrendCommand("default", token, "cluster-par-01", limit=3)
    )

    assert exact.cluster.cpu_usage_millicores == 500
    assert latest.cluster.cpu_usage_millicores == 1500
    assert [point.cluster.cpu_usage_millicores for point in trend.points] == [500, 1000, 1500]
    assert trend.snapshots_evaluated == 3 and trend.truncated is False


def test_capacity_trend_rejects_invalid_limit_and_unknown_cluster(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    with pytest.raises(ValidationError, match="between 2 and 96"):
        app.kubernetes_topology_service.capacity_trend(
            GetKubernetesCapacityTrendCommand("default", token, "cluster", limit=1)
        )
    with pytest.raises(NotFoundError, match="snapshot"):
        app.kubernetes_topology_service.capacity_trend(
            GetKubernetesCapacityTrendCommand("default", token, "missing", limit=2)
        )
