from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.flow_matrix import FlowDeclaration
from openinfra.domain.kubernetes_exposure import KubernetesExposureReport
from openinfra.domain.kubernetes_topology import KubernetesResource, KubernetesTopologySnapshot
from openinfra.domain.source_of_truth import SourceOfTruthObject, SourceRelation


def _snapshot() -> KubernetesTopologySnapshot:
    resources = (
        KubernetesResource.create("namespace", "ns-prod", "production"),
        KubernetesResource.create("workload", "deploy-api", "api", namespace="production"),
        KubernetesResource.create(
            "pod",
            "pod-api",
            "api-abc123",
            namespace="production",
            owner_uid="deploy-api",
        ),
        KubernetesResource.create(
            "service",
            "svc-api",
            "api",
            namespace="production",
            target_uids=("pod-api",),
            attributes={
                "service_type": "ClusterIP",
                "cluster_ips": ["10.96.0.10"],
                "ports": [{"name": "https", "protocol": "https", "port": 443}],
                "rsot_object_keys": ["app:api"],
            },
        ),
        KubernetesResource.create(
            "ingress",
            "ing-api",
            "api",
            namespace="production",
            target_uids=("svc-api",),
            attributes={
                "scope": "external",
                "hosts": ["api.example.test"],
                "addresses": ["203.0.113.10"],
                "ports": [{"protocol": "https", "port": 443}],
                "tls": True,
                "rsot_object_keys": ["app:api"],
            },
        ),
        KubernetesResource.create(
            "load-balancer",
            "lb-api",
            "api-public",
            namespace="production",
            target_uids=("ing-api",),
            attributes={
                "scope": "external",
                "scheme": "internet-facing",
                "addresses": ["203.0.113.20"],
                "ports": [{"protocol": "tcp", "port": 443}],
                "rsot_object_keys": ["net:edge-lb"],
            },
        ),
        KubernetesResource.create(
            "dns-record",
            "dns-api",
            "api-public",
            namespace="production",
            target_uids=("lb-api",),
            attributes={
                "scope": "external",
                "record_type": "CNAME",
                "values": ["api.example.test"],
                "ttl": 60,
            },
        ),
        KubernetesResource.create(
            "mesh-route",
            "mesh-api",
            "api-mesh",
            namespace="production",
            target_uids=("svc-api",),
            attributes={
                "scope": "internal",
                "mesh": "istio",
                "hosts": ["api.production.svc.cluster.local"],
                "protocol": "http2",
                "ports": [{"protocol": "http2", "port": 8443}],
            },
        ),
    )
    return KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster-par-01",
        "prod-par-01",
        "kubernetes",
        "v1.34.1",
        "discovery:k8s-prod-par-01",
        datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
        resources,
        region="eu-west",
        site_code="par-01",
    )


def _flow(code: str, selector: str, decision: str = "allow") -> FlowDeclaration:
    return FlowDeclaration.create(
        tenant_id=TenantId.from_value("default"),
        code=code,
        source_selector="any",
        destination_selector=selector,
        protocol="tcp",
        destination_port_start=443,
        destination_port_end=443,
        decision=decision,
        priority=100,
        owner="Network Team",
        justification="Kubernetes external API exposure",
        actor="pytest",
        valid_from=datetime(2026, 7, 1, tzinfo=UTC),
    )


def test_exposure_report_correlates_network_flows_and_rsot_dependencies_deterministically() -> None:
    snapshot = _snapshot()
    tenant = TenantId.from_value("default")
    application = SourceOfTruthObject.create(
        tenant, "app:api", "application", "API", {}, (), "pytest"
    )
    load_balancer = SourceOfTruthObject.create(
        tenant, "net:edge-lb", "network-device", "Edge LB", {}, (), "pytest"
    )
    relation = SourceRelation.create(
        tenant,
        "depends-on",
        "app:api",
        "net:edge-lb",
        "pytest",
        valid_from=datetime(2026, 7, 1, tzinfo=UTC),
    )
    flows = (
        _flow("FLOW-K8S-EXT", "cidr:203.0.113.0/24"),
        _flow("FLOW-K8S-APP", "object:app:api"),
    )

    first = KubernetesExposureReport.build(
        snapshot, flows, (relation,), (application, load_balancer)
    )
    second = KubernetesExposureReport.build(
        snapshot,
        tuple(reversed(flows)),
        (relation,),
        tuple(reversed((application, load_balancer))),
    )

    assert first.fingerprint == second.fingerprint
    assert first.summary()["external_exposure_count"] == 3
    assert first.summary()["ungoverned_external_exposure_count"] == 1
    assert first.summary()["dependency_relation_count"] == 1
    assert {item.declaration_code for item in first.flow_correlations} == {
        "FLOW-K8S-APP",
        "FLOW-K8S-EXT",
    }
    edges = {(item["source"], item["target"], item["relation"]) for item in first.graph_edges}
    assert ("k8s:dns-api", "k8s:lb-api", "resolves-to") in edges
    assert ("k8s:lb-api", "k8s:ing-api", "forwards-to") in edges
    assert ("k8s:ing-api", "k8s:svc-api", "publishes") in edges
    assert ("rsot:app:api", "rsot:net:edge-lb", "depends-on") in edges
    assert any(edge[2] == "governed-by-flow" for edge in edges)


def test_cloud_native_exposure_resource_schemas_are_strict_and_canonical() -> None:
    load_balancer = KubernetesResource.create(
        "loadbalancer",
        "lb-api",
        "api-public",
        namespace="production",
        target_uids=("svc-api",),
        attributes={
            "scope": "EXTERNAL",
            "addresses": ["2001:0db8::1", "2001:db8::1"],
            "ports": [
                {"port": 443, "protocol": "HTTPS", "name": "https"},
                {"port": 443, "protocol": "https", "name": "https"},
            ],
        },
    )
    assert load_balancer.kind.value == "load-balancer"
    assert load_balancer.attributes["addresses"] == ["2001:db8::1"]
    assert load_balancer.attributes["ports"] == [
        {"port": 443, "protocol": "https", "name": "https"}
    ]

    with pytest.raises(ValidationError, match="incompatible address"):
        KubernetesResource.create(
            "dns-record",
            "dns-api",
            "api",
            namespace="production",
            target_uids=("svc-api",),
            attributes={
                "scope": "external",
                "record_type": "A",
                "values": ["2001:db8::1"],
            },
        )
    with pytest.raises(ValidationError, match="internal or external scope"):
        KubernetesTopologySnapshot.create(
            TenantId.from_value("default"),
            "cluster",
            "cluster",
            "kubernetes",
            "v1.34.1",
            "pytest",
            datetime.now(UTC),
            (
                KubernetesResource.create("namespace", "ns-prod", "production"),
                KubernetesResource.create(
                    "load-balancer",
                    "lb-api",
                    "api",
                    namespace="production",
                    target_uids=("svc-api",),
                    attributes={"addresses": ["203.0.113.10"]},
                ),
                KubernetesResource.create("service", "svc-api", "api", namespace="production"),
            ),
        )


def test_exposure_endpoints_cover_service_defaults_external_names_and_flow_matching() -> None:
    from openinfra.domain.flow_matrix import FlowProtocol, FlowSelectorKind
    from openinfra.domain.kubernetes_exposure import (
        KubernetesExposureEndpoint,
        KubernetesExposureResource,
        KubernetesExposureScope,
    )

    service = KubernetesResource.create(
        "service",
        "svc-external",
        "external-api",
        namespace="production",
        target_uids=("pod-api",),
        attributes={
            "service_type": "ExternalName",
            "external_name": "upstream.example.test",
            "external_ips": ["198.51.100.10"],
        },
    )
    exposed = KubernetesExposureResource.from_resource(service)
    assert exposed is not None
    assert exposed.scope is KubernetesExposureScope.EXTERNAL
    assert {item.value for item in exposed.endpoints} == {
        "198.51.100.10",
        "upstream.example.test",
    }
    assert (
        KubernetesExposureResource.from_resource(
            KubernetesResource.create("namespace", "ns-other", "other")
        )
        is None
    )

    endpoint = KubernetesExposureEndpoint(
        "svc-external", "ip", "198.51.100.10", KubernetesExposureScope.EXTERNAL, "https", 443
    )
    assert endpoint.transport_protocol == "tcp"
    assert KubernetesExposureReport._selector_matches(FlowSelectorKind.ANY, "*", endpoint)
    assert not KubernetesExposureReport._selector_matches(
        FlowSelectorKind.OBJECT, "app:api", endpoint
    )
    assert not KubernetesExposureReport._selector_matches(
        FlowSelectorKind.CIDR,
        "not-a-network",
        endpoint,
    )
    assert KubernetesExposureReport._protocol_matches(FlowProtocol.ANY, endpoint)


def test_exposure_report_skips_unaddressed_resources_and_rejects_non_matching_protocols() -> None:
    snapshot = _snapshot()
    plain_service = KubernetesResource.create(
        "service",
        "svc-plain",
        "plain",
        namespace="production",
        target_uids=("pod-api",),
        attributes={"service_type": "ClusterIP"},
    )
    snapshot = KubernetesTopologySnapshot.create(
        snapshot.tenant_id,
        snapshot.cluster_key,
        snapshot.cluster_name,
        snapshot.provider,
        snapshot.kubernetes_version,
        snapshot.source_ref,
        snapshot.observed_at,
        (*snapshot.resources, plain_service),
        region=snapshot.region,
        site_code=snapshot.site_code,
    )
    udp_flow = FlowDeclaration.create(
        tenant_id=TenantId.from_value("default"),
        code="FLOW-UDP",
        source_selector="any",
        destination_selector="cidr:203.0.113.0/24",
        protocol="udp",
        destination_port_start=53,
        destination_port_end=53,
        decision="deny",
        priority=10,
        owner="Network Team",
        justification="Negative protocol and port correlation test",
        actor="pytest",
        valid_from=datetime(2026, 7, 1, tzinfo=UTC),
    )
    report = KubernetesExposureReport.build(snapshot, (udp_flow,), (), ())
    assert report.flow_correlations == ()
    assert any(item.uid == "svc-plain" and not item.endpoints for item in report.resources)


@pytest.mark.parametrize(
    ("kind", "attributes", "message"),
    (
        ("service", {"scope": "public"}, "scope must be cluster"),
        ("service", {"service_type": "Headless"}, "service_type must be"),
        ("load-balancer", {"scheme": "public"}, "scheme must be"),
        ("ingress", {"tls": "yes"}, "tls must be a boolean"),
        ("mesh-route", {"protocol": "quic"}, "protocol is unsupported"),
        ("dns-record", {"record_type": "TXT", "values": ["x"]}, "record_type"),
        ("dns-record", {"record_type": "A", "values": []}, "cannot be empty"),
        ("dns-record", {"record_type": "A", "values": ["192.0.2.1"], "ttl": 0}, "ttl"),
        ("service", {"addresses": "192.0.2.1"}, "must be a JSON array"),
        ("service", {"addresses": ["invalid"]}, "address is invalid"),
        ("service", {"ports": "443"}, "ports must be a JSON array"),
        ("service", {"ports": ["443"]}, "each port must be a JSON object"),
        ("service", {"ports": [{"port": "bad"}]}, "port must be an integer"),
        ("service", {"ports": [{"port": 0}]}, "between 1 and 65535"),
        ("service", {"ports": [{"port": 443, "protocol": "quic"}]}, "protocol is unsupported"),
    ),
)
def test_exposure_attribute_validation_rejects_invalid_values(
    kind: str, attributes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        KubernetesResource.create(
            kind,
            f"resource-{kind}",
            "resource",
            namespace="production",
            attributes=attributes,
        )


def test_exposure_topology_requires_typed_targets_and_complete_metadata() -> None:
    base = (
        KubernetesResource.create("namespace", "ns-prod", "production"),
        KubernetesResource.create("workload", "deploy-api", "api", namespace="production"),
        KubernetesResource.create(
            "service",
            "svc-api",
            "api",
            namespace="production",
            target_uids=("deploy-api",),
            attributes={"service_type": "ClusterIP", "cluster_ips": ["10.96.0.10"]},
        ),
    )

    invalid_resources = (
        KubernetesResource.create(
            "load-balancer",
            "lb-no-target",
            "lb",
            namespace="production",
            attributes={"scope": "external", "addresses": ["203.0.113.10"]},
        ),
        KubernetesResource.create(
            "load-balancer",
            "lb-no-endpoint",
            "lb",
            namespace="production",
            target_uids=("svc-api",),
            attributes={"scope": "external"},
        ),
        KubernetesResource.create(
            "dns-record",
            "dns-no-target",
            "dns",
            namespace="production",
            attributes={"scope": "external", "record_type": "A", "values": ["203.0.113.10"]},
        ),
        KubernetesResource.create(
            "mesh-route",
            "mesh-no-target",
            "mesh",
            namespace="production",
            attributes={"scope": "internal", "mesh": "istio", "hosts": ["api.local"]},
        ),
        KubernetesResource.create(
            "mesh-route",
            "mesh-no-name",
            "mesh",
            namespace="production",
            target_uids=("svc-api",),
            attributes={"scope": "internal", "hosts": ["api.local"]},
        ),
        KubernetesResource.create(
            "mesh-route",
            "mesh-no-host",
            "mesh",
            namespace="production",
            target_uids=("svc-api",),
            attributes={"scope": "internal", "mesh": "istio"},
        ),
        KubernetesResource.create(
            "ingress",
            "ing-no-host",
            "ing",
            namespace="production",
            target_uids=("svc-api",),
            attributes={"scope": "external", "tls": True},
        ),
    )
    expected = (
        "requires at least one target_uids",
        "requires addresses or hosts",
        "requires at least one target_uids",
        "requires at least one target_uids",
        "requires a mesh attribute",
        "requires at least one host",
        "requires hosts or addresses",
    )
    for resource, message in zip(invalid_resources, expected, strict=True):
        with pytest.raises(ValidationError, match=message):
            KubernetesTopologySnapshot.create(
                TenantId.from_value("default"),
                f"cluster-{resource.uid}",
                "cluster",
                "kubernetes",
                "v1.34.1",
                "pytest",
                datetime(2026, 7, 14, tzinfo=UTC),
                (*base, resource),
            )
