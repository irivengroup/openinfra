from __future__ import annotations

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.dependency import (
    DependencyChangeImpactReport,
    DependencyCriticalRisk,
    DependencyGraphExport,
    DependencySpofCandidate,
    DependencySpofReport,
    GraphDirection,
    GraphExportFormat,
    GraphNode,
)


def test_spof_domain_serialization_and_export_metadata() -> None:
    node = GraphNode.from_object_payload(
        {
            "key": "database/main",
            "display_name": "Main database",
            "kind": "database",
            "resource_category": "software-service",
            "resource_type": "database",
            "status": "active",
        },
        2,
    )
    candidate = DependencySpofCandidate(
        rank=1,
        node=node,
        affected_count=3,
        direct_affected_count=1,
        affected_ratio=0.375,
        affected_sample=("storage/main", "service/reporting"),
        affected_sample_truncated=True,
        by_kind={"storage": 1, "service": 2},
        by_resource_category={"software-service": 2, "storage": 1},
    )
    report = DependencySpofReport(
        root_key="application/portal",
        direction=GraphDirection.OUTGOING,
        relation_types=("depends_on",),
        as_of=None,
        node_count=9,
        edge_count=10,
        total_spof_count=1,
        candidates=(candidate,),
        next_cursor=None,
        max_depth_reached=4,
        truncated=False,
        filters={"minimum_affected_nodes": 1},
    )
    export = DependencyGraphExport(
        filename="openinfra-graph-application-portal.json",
        content_type="application/json; charset=utf-8",
        content=b"{}\n",
        format=GraphExportFormat.JSON,
        node_count=9,
        edge_count=10,
        spof_count=1,
    )

    payload = report.as_dict()
    assert payload["complete"] is True
    assert payload["algorithm"] == "rooted-dominators"
    assert payload["items"][0]["affected_ratio"] == 0.375
    assert payload["items"][0]["by_kind"] == {"service": 2, "storage": 1}
    assert export.metadata() == {
        "filename": "openinfra-graph-application-portal.json",
        "content_type": "application/json; charset=utf-8",
        "format": "json",
        "size_bytes": 3,
        "node_count": 9,
        "edge_count": 10,
        "spof_count": 1,
    }


@pytest.mark.parametrize("value", ["JSON", " csv ", "graphml"])
def test_graph_export_format_accepts_supported_values(value: str) -> None:
    assert GraphExportFormat.from_value(value).value == value.strip().lower()


def test_graph_export_format_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError, match="json, csv or graphml"):
        GraphExportFormat.from_value("xlsx")


def test_change_impact_domain_serializes_services_risks_and_completeness() -> None:
    root = GraphNode.from_object_payload(
        {
            "key": "server/db-01",
            "display_name": "Database server",
            "kind": "server",
            "resource_category": "compute",
            "resource_type": "virtual-machine",
            "status": "active",
        },
        0,
    )
    service = GraphNode.from_object_payload(
        {
            "key": "service/api",
            "display_name": "Customer API",
            "kind": "service",
            "resource_category": "software-service",
            "resource_type": "api-service",
            "status": "active",
        },
        1,
    )
    risk = DependencyCriticalRisk(
        node=service,
        affected_business_service_count=1,
        affected_business_service_keys=("application/portal",),
        affected_node_count=2,
        direct_affected_count=1,
        risk_level="medium",
    )
    report = DependencyChangeImpactReport(
        root_key=root.key,
        direction=GraphDirection.INCOMING,
        as_of=None,
        impacted_nodes=(service,),
        impacted_business_services=(service,),
        critical_dependencies=(risk,),
        root_spof_risk=True,
        max_depth_reached=1,
        truncated=True,
        edges=(),
    )

    payload = report.as_dict()
    assert payload["complete"] is False
    assert payload["business_service_count"] == 1
    assert payload["critical_dependency_count"] == 1
    assert payload["root_spof_risk"] is True
    assert payload["critical_dependencies"][0] == {
        "node": service.as_dict(),
        "affected_business_service_count": 1,
        "affected_business_service_keys": ["application/portal"],
        "affected_node_count": 2,
        "direct_affected_count": 1,
        "risk_level": "medium",
    }
