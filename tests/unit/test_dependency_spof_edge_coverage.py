from __future__ import annotations

import base64
import json

import pytest

from openinfra.application.dependency_graph_services import DependencyGraphService
from openinfra.domain.common import ValidationError
from openinfra.domain.dependency import (
    DependencyGraph,
    GraphDirection,
    GraphEdge,
    GraphExportFormat,
    GraphNode,
)


def _node(key: str, depth: int = 0) -> GraphNode:
    return GraphNode(
        key=key,
        display_name=key.title(),
        kind="service",
        resource_category="software-service",
        resource_type="service",
        status="active",
        depth=depth,
    )


def _edge(identifier: str, source: str, target: str) -> GraphEdge:
    return GraphEdge(
        id=identifier,
        relation_type="depends_on",
        source_key=source,
        target_key=target,
        provenance="pytest",
        valid_from="2026-07-10T00:00:00+00:00",
        valid_to=None,
    )


def _graph(
    *,
    root_key: str = "service/root",
    direction: GraphDirection = GraphDirection.OUTGOING,
    nodes: tuple[GraphNode, ...] = (),
    edges: tuple[GraphEdge, ...] = (),
) -> DependencyGraph:
    return DependencyGraph(
        root_key=root_key,
        direction=direction,
        max_depth=8,
        max_nodes=100,
        as_of=None,
        relation_types=(),
        nodes=nodes,
        edges=edges,
        max_depth_reached=max((node.depth for node in nodes), default=0),
        truncated=False,
    )


def _service() -> DependencyGraphService:
    return object.__new__(DependencyGraphService)


def _cursor(payload: object) -> str:
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def test_spof_graph_analysis_rejects_invalid_graphs() -> None:
    service = _service()

    with pytest.raises(ValidationError, match="cannot be empty"):
        service._analyze_spof_graph(_graph())

    with pytest.raises(ValidationError, match="root is missing"):
        service._analyze_spof_graph(_graph(nodes=(_node("service/other"),)))


def test_spof_graph_analysis_supports_incoming_both_self_loops_and_disconnected_nodes() -> None:
    service = _service()
    root = _node("service/root")
    upstream = _node("service/upstream", 1)

    incoming = service._analyze_spof_graph(
        _graph(
            direction=GraphDirection.INCOMING,
            nodes=(root, upstream),
            edges=(_edge("incoming", "service/upstream", "service/root"),),
        )
    )
    assert incoming.successors[0] == (1,)

    disconnected = _node("service/disconnected", 1)
    both = service._analyze_spof_graph(
        _graph(
            direction=GraphDirection.BOTH,
            nodes=(root, upstream, disconnected),
            edges=(
                _edge("connected", "service/root", "service/upstream"),
                _edge("self-loop", "service/upstream", "service/upstream"),
            ),
        )
    )
    assert both.successors[0] == (1,)
    assert both.dominators[2] == 1 << 2


def test_spof_validation_helpers_reject_unbounded_filters_and_invalid_cursors() -> None:
    service = _service()

    with pytest.raises(ValidationError, match="more than 100"):
        service._filter_values(tuple(f"kind-{index}" for index in range(101)), "kind")
    with pytest.raises(ValidationError, match="120 characters"):
        service._filter_values(("x" * 121,), "kind")
    with pytest.raises(ValidationError, match="between 1 and max_nodes"):
        service._minimum_affected_nodes(0, 100)
    with pytest.raises(ValidationError, match="between 1 and 200"):
        service._sample_limit(201)

    with pytest.raises(ValidationError, match="cursor is invalid"):
        service._cursor_offset(_cursor(["not", "an", "object"]), "fingerprint")
    with pytest.raises(ValidationError, match="offset cannot be negative"):
        service._cursor_offset(_cursor({"offset": -1, "fingerprint": "fingerprint"}), "fingerprint")


def test_graphml_export_ignores_relations_outside_the_bounded_graph() -> None:
    service = _service()
    graph = _graph(
        nodes=(_node("service/root"),),
        edges=(_edge("dangling", "service/root", "service/missing"),),
    )

    content, content_type, extension = service._render_export(graph, GraphExportFormat.GRAPHML, {})

    assert content_type.startswith("application/graphml+xml")
    assert extension == "graphml"
    assert b'<edge id="dangling"' not in content
