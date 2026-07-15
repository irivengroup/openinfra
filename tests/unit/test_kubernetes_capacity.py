from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.kubernetes_capacity import (
    KubernetesCapacityReport,
    KubernetesCapacitySeverity,
    KubernetesCapacityTrendReport,
)
from openinfra.domain.kubernetes_topology import KubernetesResource, KubernetesTopologySnapshot


def _snapshot(observed_at: datetime, usage_factor: int = 1) -> KubernetesTopologySnapshot:
    gib = 1024**3
    resources = (
        KubernetesResource.create("namespace", "ns-prod", "production"),
        KubernetesResource.create("namespace", "ns-dev", "development"),
        KubernetesResource.create(
            "node",
            "node-1",
            "worker-01",
            attributes={
                "capacity": {
                    "cpu_capacity_millicores": 4000,
                    "memory_capacity_bytes": 16 * gib,
                    "storage_capacity_bytes": 200 * gib,
                }
            },
        ),
        KubernetesResource.create(
            "pod",
            "pod-prod",
            "api-prod",
            namespace="production",
            attributes={
                "capacity": {
                    "cpu_request_millicores": 1000,
                    "cpu_limit_millicores": 2000,
                    "cpu_usage_millicores": 900 * usage_factor,
                    "memory_request_bytes": 2 * gib,
                    "memory_limit_bytes": 4 * gib,
                    "memory_usage_bytes": 3 * gib * usage_factor,
                }
            },
        ),
        KubernetesResource.create(
            "pod",
            "pod-dev",
            "api-dev",
            namespace="development",
            attributes={
                "capacity": {
                    "cpu_request_millicores": 500,
                    "cpu_limit_millicores": 1000,
                    "cpu_usage_millicores": 250,
                    "memory_request_bytes": gib,
                    "memory_limit_bytes": 2 * gib,
                    "memory_usage_bytes": gib,
                }
            },
        ),
        KubernetesResource.create(
            "volume",
            "vol-prod",
            "data-prod",
            namespace="production",
            attributes={
                "capacity": {
                    "storage_request_bytes": 50 * gib,
                    "storage_limit_bytes": 100 * gib,
                    "storage_usage_bytes": 85 * gib,
                    "storage_capacity_bytes": 100 * gib,
                }
            },
        ),
    )
    return KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        f"pytest:{observed_at.isoformat()}",
        observed_at,
        resources,
    )


def test_capacity_report_aggregates_cluster_and_namespaces_and_emits_alerts() -> None:
    report = KubernetesCapacityReport.build(_snapshot(datetime(2026, 7, 15, 10, 0, tzinfo=UTC)))

    assert report.cluster.cpu_capacity_millicores == 4000
    assert report.cluster.cpu_request_millicores == 1500
    assert report.cluster.memory_usage_bytes == 4 * 1024**3
    assert report.cluster.storage_capacity_bytes == 100 * 1024**3
    assert [item.namespace for item in report.namespaces] == ["development", "production"]
    prod = next(item for item in report.namespaces if item.namespace == "production")
    assert prod.pod_count == 1 and prod.volume_count == 1
    assert prod.values.storage_usage_bytes == 85 * 1024**3
    assert any(
        alert.scope == "namespace"
        and alert.scope_key == "production"
        and alert.resource == "storage"
        and alert.severity is KubernetesCapacitySeverity.WARNING
        for alert in report.alerts
    )
    assert report.coverage == {
        "nodes": 1,
        "pods": 2,
        "volumes": 1,
        "resources_with_capacity": 4,
    }


def test_capacity_export_supports_json_and_csv_and_rejects_unknown_format() -> None:
    report = KubernetesCapacityReport.build(_snapshot(datetime(2026, 7, 15, 10, 0, tzinfo=UTC)))
    json_type, json_body = report.export("json")
    csv_type, csv_body = report.export("CSV")

    assert (
        json_type.startswith("application/json") and '"cluster_key": "cluster-par-01"' in json_body
    )
    assert csv_type.startswith("text/csv")
    assert "scope,scope_key,observed_at" in csv_body
    assert "namespace,production" in csv_body
    with pytest.raises(ValidationError, match="json or csv"):
        report.export("xml")


def test_capacity_metrics_are_strict_and_historical_fingerprint_is_preserved() -> None:
    base = KubernetesResource.create("pod", "pod", "api", namespace="production")
    restored = KubernetesResource.from_dict(base.as_dict())
    assert restored.as_dict() == base.as_dict()

    with pytest.raises(ValidationError, match="only valid for nodes, pods and volumes"):
        KubernetesResource.create(
            "service",
            "svc",
            "api",
            namespace="production",
            attributes={"capacity": {"cpu_usage_millicores": 10}},
        )
    with pytest.raises(ValidationError, match="request cannot exceed limit"):
        KubernetesResource.create(
            "pod",
            "pod",
            "api",
            namespace="production",
            attributes={"capacity": {"cpu_request_millicores": 2000, "cpu_limit_millicores": 1000}},
        )
    with pytest.raises(ValidationError, match="unsupported Kubernetes capacity metric"):
        KubernetesResource.create(
            "node",
            "node",
            "worker",
            attributes={"capacity": {"gpu_capacity": 1}},
        )
    with pytest.raises(ValidationError, match="non-negative integer"):
        KubernetesResource.create(
            "node",
            "node",
            "worker",
            attributes={"capacity": {"cpu_capacity_millicores": True}},
        )


def test_capacity_thresholds_and_namespace_bound_are_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(datetime(2026, 7, 15, 10, 0, tzinfo=UTC))
    with pytest.raises(ValidationError, match="warning < critical"):
        KubernetesCapacityReport.build(snapshot, 90, 80)

    monkeypatch.setattr(KubernetesCapacityReport, "_MAX_NAMESPACES", 1)
    with pytest.raises(ValidationError, match="cannot exceed 1 namespaces"):
        KubernetesCapacityReport.build(snapshot)


def test_capacity_trend_is_chronological_bounded_and_reports_truncation() -> None:
    now = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)
    snapshots = (_snapshot(now + timedelta(minutes=10), 1), _snapshot(now, 1))
    report = KubernetesCapacityTrendReport.build("cluster-par-01", snapshots, max_resources=20)
    assert [point.observed_at for point in report.points] == sorted(
        point.observed_at for point in report.points
    )
    assert report.snapshots_evaluated == 2
    assert report.resources_scanned == 12
    assert report.truncated is False

    truncated = KubernetesCapacityTrendReport.build("cluster-par-01", snapshots, max_resources=6)
    assert truncated.snapshots_evaluated == 1
    assert truncated.truncated is True
    with pytest.raises(ValidationError, match="max_resources"):
        KubernetesCapacityTrendReport.build("cluster-par-01", snapshots, max_resources=0)
