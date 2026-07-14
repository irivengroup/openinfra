from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.flow_matrix_services import UpsertFlowDeclarationCommand
from openinfra.application.kubernetes_topology_services import (
    GetLatestKubernetesTopologyCommand,
    ImportKubernetesTopologyCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    UpsertSourceObjectCommand,
)


def exposure_resources() -> tuple[dict[str, object], ...]:
    return (
        {"kind": "namespace", "uid": "ns-prod", "name": "production"},
        {
            "kind": "workload",
            "uid": "deploy-api",
            "name": "api",
            "namespace": "production",
        },
        {
            "kind": "pod",
            "uid": "pod-api",
            "name": "api-abc123",
            "namespace": "production",
            "owner_uid": "deploy-api",
        },
        {
            "kind": "service",
            "uid": "svc-api",
            "name": "api",
            "namespace": "production",
            "target_uids": ["pod-api"],
            "attributes": {
                "service_type": "ClusterIP",
                "cluster_ips": ["10.96.0.10"],
                "ports": [{"protocol": "https", "port": 443}],
                "rsot_object_keys": ["app:api"],
            },
        },
        {
            "kind": "ingress",
            "uid": "ing-api",
            "name": "api",
            "namespace": "production",
            "target_uids": ["svc-api"],
            "attributes": {
                "scope": "external",
                "hosts": ["api.example.test"],
                "addresses": ["203.0.113.10"],
                "ports": [{"protocol": "https", "port": 443}],
                "tls": True,
                "rsot_object_keys": ["app:api"],
            },
        },
        {
            "kind": "load-balancer",
            "uid": "lb-api",
            "name": "api-public",
            "namespace": "production",
            "target_uids": ["ing-api"],
            "attributes": {
                "scope": "external",
                "scheme": "internet-facing",
                "addresses": ["203.0.113.20"],
                "ports": [{"protocol": "tcp", "port": 443}],
                "rsot_object_keys": ["net:edge-lb"],
            },
        },
        {
            "kind": "dns-record",
            "uid": "dns-api",
            "name": "api-public",
            "namespace": "production",
            "target_uids": ["lb-api"],
            "attributes": {
                "scope": "external",
                "record_type": "CNAME",
                "values": ["api.example.test"],
                "ttl": 60,
            },
        },
    )


def seeded_exposure_application(state: Path):
    token = "e" * 40
    app = ApplicationFactory().create_json_application(state, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-admin", ("admin",), token)
    )
    for key, kind, name in (
        (
            "app:api",
            "application",
            "API",
        ),
        (
            "net:edge-lb",
            "network-device",
            "Edge LB",
        ),
    ):
        app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key=key,
                kind=kind,
                display_name=name,
                attributes_json="{}",
                tags=("kubernetes",),
                source="pytest",
            )
        )
    app.source_of_truth_service.create_relation(
        CreateSourceRelationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            relation_type="depends-on",
            source_key="app:api",
            target_key="net:edge-lb",
            provenance="pytest",
            valid_from=datetime(2026, 7, 1, tzinfo=UTC),
        )
    )
    app.flow_matrix_service.upsert_declaration(
        UpsertFlowDeclarationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            code="FLOW-K8S-EXT",
            source_selector="any",
            destination_selector="cidr:203.0.113.0/24",
            protocol="tcp",
            destination_port_start=443,
            destination_port_end=443,
            decision="allow",
            priority=100,
            owner="Network Team",
            justification="Kubernetes external API exposure",
            valid_from=datetime(2026, 7, 1, tzinfo=UTC),
        )
    )
    snapshot = app.kubernetes_topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            tenant_id="default",
            admin_token=token,
            cluster_key="cluster-par-01",
            cluster_name="prod-par-01",
            provider="kubernetes",
            kubernetes_version="v1.34.1",
            source_ref="discovery:k8s-prod-par-01",
            observed_at=datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
            resources=exposure_resources(),
            region="eu-west",
            site_code="par-01",
            actor="pytest",
        )
    )
    return app, token, snapshot


def test_kubernetes_exposure_service_correlates_flow_and_dependency_models(tmp_path: Path) -> None:
    app, token, snapshot = seeded_exposure_application(tmp_path / "state.json")
    report = app.kubernetes_topology_service.latest_exposure(
        GetLatestKubernetesTopologyCommand("default", token, "cluster-par-01")
    )

    payload = report.as_dict()
    assert payload["snapshot_id"] == snapshot.id.value
    assert payload["summary"]["external_exposure_count"] == 3  # type: ignore[index]
    assert payload["summary"]["flow_correlated_exposure_count"] == 2  # type: ignore[index]
    assert payload["summary"]["dependency_relation_count"] == 1  # type: ignore[index]
    assert payload["fingerprint"] == report.fingerprint
    assert any(
        edge["relation"] == "depends-on"
        for edge in payload["graph"]["edges"]  # type: ignore[index]
    )


def test_kubernetes_exposure_service_supports_exact_snapshot_lookup(tmp_path: Path) -> None:
    from openinfra.application.kubernetes_topology_services import GetKubernetesTopologyCommand

    app, token, snapshot = seeded_exposure_application(tmp_path / "state.json")
    report = app.kubernetes_topology_service.exposure(
        GetKubernetesTopologyCommand("default", token, snapshot.id.value)
    )
    assert report.snapshot_id == snapshot.id.value


def test_kubernetes_exposure_service_rejects_cyclic_repository_cursors(
    tmp_path: Path, monkeypatch: object
) -> None:
    from types import SimpleNamespace

    from openinfra.domain.common import TenantId, ValidationError

    app, _token, _snapshot = seeded_exposure_application(tmp_path / "state.json")
    service = app.kubernetes_topology_service

    def cyclic_flows(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(items=(), next_cursor="same")

    monkeypatch.setattr(  # type: ignore[attr-defined]
        service._flow_matrix_repository, "list_declarations", cyclic_flows
    )
    with pytest.raises(ValidationError, match="cyclic cursor"):
        service._active_flow_declarations(TenantId.from_value("default"))

    def no_more_flows(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(items=(), next_cursor=None)

    monkeypatch.setattr(  # type: ignore[attr-defined]
        service._flow_matrix_repository, "list_declarations", no_more_flows
    )

    def cyclic_relations(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(items=(), next_cursor="same")

    monkeypatch.setattr(  # type: ignore[attr-defined]
        service._source_of_truth_repository, "list_relations", cyclic_relations
    )
    with pytest.raises(ValidationError, match="cyclic cursor"):
        service._dependency_relations(
            TenantId.from_value("default"),
            ("app:api",),
            datetime(2026, 7, 14, tzinfo=UTC),
        )


def test_kubernetes_exposure_service_marks_bounded_flow_correlation_as_truncated(
    tmp_path: Path, monkeypatch: object
) -> None:
    from types import SimpleNamespace

    app, token, _snapshot = seeded_exposure_application(tmp_path / "state.json")
    service = app.kubernetes_topology_service
    declaration = app.flow_matrix_repository.list_declarations(  # type: ignore[attr-defined]
        __import__("openinfra.domain.common", fromlist=["TenantId"]).TenantId.from_value("default"),
        __import__("openinfra.domain.common", fromlist=["Pagination"]).Pagination.from_values(
            1, None
        ),
        include_retired=False,
    ).items[0]

    monkeypatch.setattr(service, "_MAX_FLOW_DECLARATIONS", 1)  # type: ignore[attr-defined]

    def bounded_page(*_args: object, **_kwargs: object) -> object:
        return SimpleNamespace(items=(declaration,), next_cursor="more")

    monkeypatch.setattr(  # type: ignore[attr-defined]
        service._flow_matrix_repository, "list_declarations", bounded_page
    )
    report = service.latest_exposure(
        GetLatestKubernetesTopologyCommand("default", token, "cluster-par-01")
    )
    assert report.correlation_truncated is True
