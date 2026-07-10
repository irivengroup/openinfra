from __future__ import annotations

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.dependency import (
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
