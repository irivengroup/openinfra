from __future__ import annotations

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.dependency import (
    DependencyEdge,
    DependencyGraph,
    DependencyImpact,
    DependencyKind,
    DependencyNode,
    DependencyPath,
    GraphDirection,
    GraphEdge,
    GraphNode,
)


class TestDependencyDomain:
    def test_legacy_dependency_entities_remain_compatible(self) -> None:
        tenant_id = TenantId.from_value("default")
        node = DependencyNode.create(tenant_id, "APP-01", "Portal", " Application ")
        edge = DependencyEdge.create(
            tenant_id,
            "APP-01",
            "DB-01",
            DependencyKind.DATABASE,
            protocol=" TCP ",
            port=5432,
        )

        assert node.node_type == "application"
        assert node.code.value == "APP-01"
        assert edge.protocol == "tcp"
        assert edge.port == 5432

        with pytest.raises(ValidationError, match="node type"):
            DependencyNode.create(tenant_id, "APP-02", "Empty", " ")
        with pytest.raises(ValidationError, match="between 1 and 65535"):
            DependencyEdge.create(
                tenant_id,
                "APP-01",
                "DB-01",
                DependencyKind.DATABASE,
                port=70000,
            )

    def test_graph_node_normalization_and_validation(self) -> None:
        node = GraphNode.from_object_payload(
            {
                "key": " Application/Portal ",
                "display_name": "  Customer   Portal ",
                "kind": " Application ",
                "resource_category": " Software ",
                "resource_type": " Web-App ",
                "status": " Active ",
                "attributes": {"secret": "not exposed"},
            },
            2,
        )

        assert node.as_dict() == {
            "key": "application/portal",
            "display_name": "Customer Portal",
            "kind": "application",
            "resource_category": "software",
            "resource_type": "web-app",
            "status": "active",
            "depth": 2,
        }
        assert "attributes" not in node.as_dict()

        with pytest.raises(ValidationError, match="cannot be negative"):
            GraphNode.from_object_payload(
                {"key": "application/a", "display_name": "A", "kind": "application"},
                -1,
            )
        with pytest.raises(ValidationError, match="incomplete"):
            GraphNode.from_object_payload({"key": "application/a"}, 0)

    def test_graph_result_serialization_is_deterministic(self) -> None:
        root = GraphNode.from_object_payload(
            {"key": "application/a", "display_name": "A", "kind": "application"}, 0
        )
        child = GraphNode.from_object_payload(
            {"key": "service/b", "display_name": "B", "kind": "service"}, 1
        )
        edge = GraphEdge(
            id="rel-1",
            relation_type="calls",
            source_key="application/a",
            target_key="service/b",
            provenance="manual",
            valid_from="2026-01-01T00:00:00+00:00",
            valid_to=None,
        )
        graph = DependencyGraph(
            root_key="application/a",
            direction=GraphDirection.OUTGOING,
            max_depth=3,
            max_nodes=50,
            as_of=None,
            relation_types=("calls",),
            nodes=(root, child),
            edges=(edge,),
            max_depth_reached=1,
            truncated=False,
        )
        found_path = DependencyPath(
            source_key="application/a",
            target_key="service/b",
            direction=GraphDirection.OUTGOING,
            found=True,
            truncated=False,
            nodes=(root, child),
            edges=(edge,),
        )
        missing_path = DependencyPath(
            source_key="application/a",
            target_key="server/missing",
            direction=GraphDirection.OUTGOING,
            found=False,
            truncated=False,
            nodes=(),
            edges=(),
        )
        impact = DependencyImpact(
            root_key="application/a",
            direction=GraphDirection.OUTGOING,
            impacted_nodes=(child,),
            edges=(edge,),
            direct_count=1,
            indirect_count=0,
            by_kind={"service": 1},
            by_resource_category={"service": 1},
            max_depth_reached=1,
            truncated=False,
            as_of=None,
        )

        graph_payload = graph.as_dict()
        assert graph_payload["node_count"] == 2
        assert graph_payload["edge_count"] == 1
        assert found_path.as_dict()["hop_count"] == 1
        assert missing_path.as_dict()["hop_count"] is None
        assert impact.as_dict()["impacted_count"] == 1
        assert edge.as_dict()["valid_to"] is None

    @pytest.mark.parametrize("value", ["OUTGOING", " incoming ", "both"])
    def test_graph_direction_accepts_supported_values(self, value: str) -> None:
        assert GraphDirection.from_value(value).value == value.strip().lower()

    def test_graph_direction_rejects_unknown_value(self) -> None:
        with pytest.raises(ValidationError, match="outgoing, incoming or both"):
            GraphDirection.from_value("sideways")
