from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.kubernetes_topology import (
    KubernetesPhysicalPath,
    KubernetesResource,
    KubernetesResourceKind,
    KubernetesTopologySnapshot,
)


def _resources() -> tuple[KubernetesResource, ...]:
    return (
        KubernetesResource.create("namespace", "ns-prod", "production"),
        KubernetesResource.create(
            "node",
            "node-1",
            "worker-01",
            physical_path=KubernetesPhysicalPath.create(
                vm_key="vm-k8s-01",
                hypervisor_key="esx-01",
                server_key="srv-01",
                rack_id="rack-a01",
                room_id="room-a",
                site_code="par-01",
            ),
        ),
        KubernetesResource.create(
            "workload",
            "deploy-api",
            "api",
            namespace="production",
            labels={"app": "api"},
            attributes={"replicas": 3, "image": "registry.example/openinfra/api:0.33.1"},
        ),
        KubernetesResource.create(
            "pod",
            "pod-api-1",
            "api-abc123",
            namespace="production",
            node_name="worker-01",
            owner_uid="deploy-api",
        ),
        KubernetesResource.create(
            "service",
            "svc-api",
            "api",
            namespace="production",
            target_uids=("pod-api-1", "deploy-api"),
        ),
        KubernetesResource.create(
            "ingress",
            "ing-api",
            "api",
            namespace="production",
            target_uids=("svc-api",),
        ),
        KubernetesResource.create(
            "network-policy",
            "np-api",
            "api-default-deny",
            namespace="production",
            target_uids=("pod-api-1",),
        ),
        KubernetesResource.create(
            "volume",
            "vol-api",
            "api-data",
            namespace="production",
            target_uids=("pod-api-1",),
        ),
    )


def test_snapshot_is_deterministic_and_builds_cloud_native_to_physical_graph() -> None:
    observed = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    first = KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:k8s-prod-par-01",
        observed,
        _resources(),
        region="eu-west",
        site_code="par-01",
    )
    second = KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:k8s-prod-par-01",
        observed,
        tuple(reversed(_resources())),
        region="eu-west",
        site_code="par-01",
    )

    assert first.fingerprint == second.fingerprint
    assert first.summary()["resource_count"] == 8
    assert first.summary()["mapping_coverage_percent"] == 100.0
    edges = {
        (edge.source, edge.target, edge.relation, edge.external) for edge in first.topology_edges()
    }
    assert ("k8s:node-1", "k8s:pod-api-1", "hosts", False) in edges
    assert ("k8s:svc-api", "k8s:pod-api-1", "routes-to", False) in edges
    assert ("k8s:ing-api", "k8s:svc-api", "publishes", False) in edges
    assert ("k8s:node-1", "rsot:vm-k8s-01", "runs-on-vm", True) in edges
    assert ("rsot:srv-01", "rsot:rack-a01", "located-in-rack", True) in edges
    assert first.topology()["cluster"]["site_code"] == "par-01"  # type: ignore[index]


def test_resource_reference_integrity_and_relationship_types_are_strict() -> None:
    namespace = KubernetesResource.create("namespace", "ns-prod", "production")
    node = KubernetesResource.create("node", "node-1", "worker-01")
    with pytest.raises(ValidationError, match="node_name is only valid"):
        KubernetesResource.create(
            "workload", "deploy-api", "api", namespace="production", node_name="worker-01"
        )
    invalid_service = KubernetesResource.create(
        "service", "svc-api", "api", namespace="production", target_uids=("node-1",)
    )
    with pytest.raises(ValidationError, match="service target must be one of"):
        KubernetesTopologySnapshot.create(
            TenantId.from_value("default"),
            "cluster",
            "cluster",
            "kubernetes",
            "v1.34.1",
            "pytest",
            datetime.now(UTC),
            (namespace, node, invalid_service),
        )


def test_snapshot_rejects_broken_cross_namespace_and_secret_bearing_inventory() -> None:
    with pytest.raises(ValidationError, match="sensitive key"):
        KubernetesResource.create(
            "workload",
            "deploy-api",
            "api",
            namespace="production",
            attributes={"credentials": {"api_token": "must-not-be-ingested"}},
        )

    namespaces = (
        KubernetesResource.create("namespace", "ns-a", "a"),
        KubernetesResource.create("namespace", "ns-b", "b"),
    )
    target = KubernetesResource.create("pod", "pod-b", "pod-b", namespace="b")
    service = KubernetesResource.create(
        "service", "svc-a", "svc-a", namespace="a", target_uids=("pod-b",)
    )
    with pytest.raises(ValidationError, match="cannot cross namespaces"):
        KubernetesTopologySnapshot.create(
            TenantId.from_value("default"),
            "cluster",
            "cluster",
            "kubernetes",
            "v1.34.1",
            "pytest",
            datetime.now(UTC),
            (*namespaces, target, service),
        )


def test_physical_mapping_requires_site_for_room_or_rack() -> None:
    with pytest.raises(ValidationError, match="rack requires a site_code"):
        KubernetesPhysicalPath.create(rack_id="rack-a01")
    with pytest.raises(ValidationError, match="room requires a site_code"):
        KubernetesPhysicalPath.create(room_id="room-a")
    assert (
        KubernetesResourceKind.from_value("networkpolicy") is KubernetesResourceKind.NETWORK_POLICY
    )


def test_validator_rejects_invalid_tokens_names_labels_and_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from openinfra.domain.kubernetes_topology import KubernetesTopologyValidator

    with pytest.raises(ValidationError, match="unsupported Kubernetes resource kind"):
        KubernetesResourceKind.from_value("daemon")
    with pytest.raises(ValidationError, match="safe characters"):
        KubernetesTopologyValidator.token("bad token!", "token")
    with pytest.raises(ValidationError, match="exceeds 253 characters"):
        KubernetesTopologyValidator.name("a" * 254, "name")
    with pytest.raises(ValidationError, match="Kubernetes-compatible DNS name"):
        KubernetesTopologyValidator.name("Bad_Name", "name")
    with pytest.raises(ValidationError, match="cannot exceed 64 entries"):
        KubernetesTopologyValidator.labels({f"label-{index}": "x" for index in range(65)})
    with pytest.raises(ValidationError, match="invalid Kubernetes label key"):
        KubernetesTopologyValidator.labels({"bad key": "x"})
    with pytest.raises(ValidationError, match="value exceeds 63 characters"):
        KubernetesTopologyValidator.labels({"app": "x" * 64})
    with pytest.raises(ValidationError, match="must be a JSON object"):
        KubernetesTopologyValidator.json_object([], "payload")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="unsupported JSON value"):
        KubernetesTopologyValidator.json_object({"value": object()}, "payload")
    assert KubernetesTopologyValidator.json_object({"values": [1, "two", True]}, "payload") == {
        "values": [1, "two", True]
    }
    with pytest.raises(ValidationError, match="exceeds 8 bytes"):
        KubernetesTopologyValidator.json_object({"value": "0123456789"}, "payload", 8)

    def fail_json(*_args: object, **_kwargs: object) -> str:
        raise TypeError("forced serialization failure")

    monkeypatch.setattr("openinfra.domain.kubernetes_topology.json.dumps", fail_json)
    with pytest.raises(ValidationError, match="must be JSON serializable"):
        KubernetesTopologyValidator.json_object({"value": "safe"}, "payload")

    with pytest.raises(ValidationError, match="timezone-aware"):
        KubernetesTopologyValidator.aware_datetime(datetime(2026, 7, 14, 12, 0), "observed_at")


def test_resource_shape_and_json_input_validation_are_strict() -> None:
    path = KubernetesPhysicalPath.create(site_code="par-01")
    cases = (
        (
            lambda: KubernetesResource.create("namespace", "ns", "prod", namespace="prod"),
            "must not define namespace",
        ),
        (
            lambda: KubernetesResource.create("node", "node", "worker", namespace="prod"),
            "must not define namespace",
        ),
        (lambda: KubernetesResource.create("workload", "workload", "api"), "requires a namespace"),
        (
            lambda: KubernetesResource.create(
                "pod", "pod", "api-pod", namespace="prod", physical_path=path
            ),
            "physical_path is only valid",
        ),
        (
            lambda: KubernetesResource.create(
                "service",
                "svc",
                "api",
                namespace="prod",
                target_uids=tuple(f"pod-{index}" for index in range(1025)),
            ),
            "cannot exceed 1024 entries",
        ),
        (
            lambda: KubernetesResource.from_dict(
                {
                    "kind": "pod",
                    "uid": "pod",
                    "name": "pod",
                    "namespace": "prod",
                    "target_uids": "pod-2",
                }
            ),
            "target_uids must be a JSON array",
        ),
        (
            lambda: KubernetesResource.from_dict(
                {"kind": "pod", "uid": "pod", "name": "pod", "namespace": "prod", "labels": ["bad"]}
            ),
            "labels and attributes must be JSON objects",
        ),
        (
            lambda: KubernetesResource.from_dict(
                {
                    "kind": "pod",
                    "uid": "pod",
                    "name": "pod",
                    "namespace": "prod",
                    "physical_path": [],
                }
            ),
            "physical_path must be a JSON object",
        ),
    )
    for action, message in cases:
        with pytest.raises(ValidationError, match=message):
            action()


def test_snapshot_rejects_duplicate_and_unresolved_references() -> None:
    tenant = TenantId.from_value("default")
    observed = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)

    def build(*resources: KubernetesResource) -> KubernetesTopologySnapshot:
        return KubernetesTopologySnapshot.create(
            tenant,
            "cluster",
            "cluster",
            "kubernetes",
            "v1.34.1",
            "pytest",
            observed,
            resources,
        )

    namespace = KubernetesResource.create("namespace", "ns-prod", "prod")
    node = KubernetesResource.create("node", "node-1", "worker-01")

    with pytest.raises(ValidationError, match="requires resources"):
        build()
    with pytest.raises(ValidationError, match="cannot exceed 50000 resources"):
        build(*(namespace,) * 50_001)

    duplicate_uid = KubernetesResource.create("namespace", "ns-prod", "other")
    with pytest.raises(ValidationError, match="duplicate Kubernetes resource uid"):
        build(namespace, duplicate_uid)
    duplicate_identity = KubernetesResource.create("namespace", "ns-other", "prod")
    with pytest.raises(ValidationError, match="duplicate Kubernetes resource identity"):
        build(namespace, duplicate_identity)

    unknown_namespace = KubernetesResource.create("pod", "pod-1", "pod-1", namespace="missing")
    with pytest.raises(ValidationError, match="unknown Kubernetes namespace reference"):
        build(namespace, unknown_namespace)

    unknown_node = KubernetesResource.create(
        "pod", "pod-1", "pod-1", namespace="prod", node_name="worker-404"
    )
    with pytest.raises(ValidationError, match="unknown Kubernetes node reference"):
        build(namespace, unknown_node)

    unknown_owner = KubernetesResource.create(
        "pod", "pod-1", "pod-1", namespace="prod", owner_uid="missing-owner"
    )
    with pytest.raises(ValidationError, match="unknown Kubernetes owner uid"):
        build(namespace, unknown_owner)

    self_owner = KubernetesResource.create(
        "pod", "pod-1", "pod-1", namespace="prod", owner_uid="pod-1"
    )
    with pytest.raises(ValidationError, match="cannot own itself"):
        build(namespace, self_owner)

    namespace_b = KubernetesResource.create("namespace", "ns-b", "other")
    owner_b = KubernetesResource.create("workload", "owner-b", "owner", namespace="other")
    cross_owner = KubernetesResource.create(
        "pod", "pod-1", "pod-1", namespace="prod", owner_uid="owner-b"
    )
    with pytest.raises(ValidationError, match="owner reference cannot cross namespaces"):
        build(namespace, namespace_b, owner_b, cross_owner)

    unsupported_targets = KubernetesResource.create(
        "workload", "workload-1", "api", namespace="prod", target_uids=("node-1",)
    )
    with pytest.raises(ValidationError, match="does not support target_uids"):
        build(namespace, node, unsupported_targets)

    unknown_target = KubernetesResource.create(
        "service", "svc", "api", namespace="prod", target_uids=("missing-target",)
    )
    with pytest.raises(ValidationError, match="unknown Kubernetes target uid"):
        build(namespace, unknown_target)

    self_target = KubernetesResource.create(
        "service", "svc", "api", namespace="prod", target_uids=("svc",)
    )
    with pytest.raises(ValidationError, match="cannot target itself"):
        build(namespace, self_target)


def test_snapshot_restore_rejects_tampered_fingerprint() -> None:
    snapshot = KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster",
        "cluster",
        "kubernetes",
        "v1.34.1",
        "pytest",
        datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
        (KubernetesResource.create("namespace", "ns", "prod"),),
    )
    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        KubernetesTopologySnapshot.restore(
            snapshot.id,
            snapshot.tenant_id,
            snapshot.cluster_key,
            snapshot.cluster_name,
            snapshot.provider,
            snapshot.kubernetes_version,
            snapshot.source_ref,
            snapshot.observed_at,
            snapshot.imported_at,
            snapshot.resources,
            "0" * 64,
            region=snapshot.region,
            site_code=snapshot.site_code,
        )
