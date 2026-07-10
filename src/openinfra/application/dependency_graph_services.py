from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape

from openinfra.application.ports import AuditRepository, SourceOfTruthRepository, TransactionManager
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, NotFoundError, Pagination, TenantId, ValidationError
from openinfra.domain.dependency import (
    DependencyGraph,
    DependencyGraphExport,
    DependencyImpact,
    DependencyPath,
    DependencySpofCandidate,
    DependencySpofReport,
    GraphDirection,
    GraphEdge,
    GraphExportFormat,
    GraphNode,
)
from openinfra.domain.security import Permission
from openinfra.domain.source_of_truth import RelationType, SourceRelation


@dataclass(frozen=True, slots=True)
class TraverseDependencyGraphCommand:
    tenant_id: str
    admin_token: str
    root_key: str
    direction: str = GraphDirection.BOTH.value
    max_depth: int = 3
    max_nodes: int = 500
    relation_types: tuple[str, ...] = ()
    as_of: str | datetime | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeDependencyImpactCommand:
    tenant_id: str
    admin_token: str
    root_key: str
    direction: str = GraphDirection.INCOMING.value
    max_depth: int = 6
    max_nodes: int = 1000
    relation_types: tuple[str, ...] = ()
    as_of: str | datetime | None = None


@dataclass(frozen=True, slots=True)
class FindDependencyPathCommand:
    tenant_id: str
    admin_token: str
    source_key: str
    target_key: str
    direction: str = GraphDirection.OUTGOING.value
    max_depth: int = 8
    max_nodes: int = 1000
    relation_types: tuple[str, ...] = ()
    as_of: str | datetime | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeDependencySpofCommand:
    tenant_id: str
    admin_token: str
    root_key: str
    direction: str = GraphDirection.BOTH.value
    max_depth: int = 8
    max_nodes: int = 2000
    relation_types: tuple[str, ...] = ()
    as_of: str | datetime | None = None
    candidate_kinds: tuple[str, ...] = ()
    candidate_resource_categories: tuple[str, ...] = ()
    candidate_resource_types: tuple[str, ...] = ()
    candidate_statuses: tuple[str, ...] = ()
    minimum_affected_nodes: int = 1
    affected_sample_limit: int = 25
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ExportDependencyGraphCommand:
    tenant_id: str
    admin_token: str
    root_key: str
    format: str = GraphExportFormat.JSON.value
    direction: str = GraphDirection.BOTH.value
    max_depth: int = 8
    max_nodes: int = 2000
    relation_types: tuple[str, ...] = ()
    as_of: str | datetime | None = None
    include_spof: bool = True
    candidate_kinds: tuple[str, ...] = ()
    candidate_resource_categories: tuple[str, ...] = ()
    candidate_resource_types: tuple[str, ...] = ()
    candidate_statuses: tuple[str, ...] = ()
    minimum_affected_nodes: int = 1


@dataclass(frozen=True, slots=True)
class _TraversalState:
    graph: DependencyGraph
    predecessors: dict[str, tuple[str, GraphEdge]]


@dataclass(frozen=True, slots=True)
class _SpofAnalysis:
    graph: DependencyGraph
    nodes: tuple[GraphNode, ...]
    indexes: dict[str, int]
    dominators: tuple[int, ...]
    successors: tuple[tuple[int, ...], ...]
    affected_counts: tuple[int, ...]


class DependencyGraphService:
    _RELATION_PAGE_SIZE = 500
    _MAX_DEPTH = 12
    _MAX_NODES = 5000

    def __init__(
        self,
        repository: SourceOfTruthRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def traverse(self, command: TraverseDependencyGraphCommand) -> DependencyGraph:
        tenant_id, subject = self._authorize(command.tenant_id, command.admin_token)
        direction = GraphDirection.from_value(command.direction)
        max_depth, max_nodes = self._limits(command.max_depth, command.max_nodes)
        relation_types = self._relation_types(command.relation_types)
        as_of = self._datetime(command.as_of)
        with self._transaction_manager.begin() as unit_of_work:
            state = self._traverse(
                tenant_id,
                command.root_key,
                direction,
                max_depth,
                max_nodes,
                relation_types,
                as_of,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="graph.traverse",
                    target_type="source_object",
                    target_id=state.graph.root_key,
                    metadata={
                        "direction": direction.value,
                        "max_depth": max_depth,
                        "max_nodes": max_nodes,
                        "node_count": len(state.graph.nodes),
                        "edge_count": len(state.graph.edges),
                        "truncated": state.graph.truncated,
                    },
                )
            )
            unit_of_work.commit()
        return state.graph

    def impact(self, command: AnalyzeDependencyImpactCommand) -> DependencyImpact:
        tenant_id, subject = self._authorize(command.tenant_id, command.admin_token)
        direction = GraphDirection.from_value(command.direction)
        max_depth, max_nodes = self._limits(command.max_depth, command.max_nodes)
        relation_types = self._relation_types(command.relation_types)
        as_of = self._datetime(command.as_of)
        with self._transaction_manager.begin() as unit_of_work:
            graph = self._traverse(
                tenant_id,
                command.root_key,
                direction,
                max_depth,
                max_nodes,
                relation_types,
                as_of,
            ).graph
            impacted_nodes = tuple(node for node in graph.nodes if node.key != graph.root_key)
            by_kind: dict[str, int] = {}
            by_category: dict[str, int] = {}
            for node in impacted_nodes:
                by_kind[node.kind] = by_kind.get(node.kind, 0) + 1
                by_category[node.resource_category] = by_category.get(node.resource_category, 0) + 1
            result = DependencyImpact(
                root_key=graph.root_key,
                direction=graph.direction,
                impacted_nodes=impacted_nodes,
                edges=graph.edges,
                direct_count=sum(1 for node in impacted_nodes if node.depth == 1),
                indirect_count=sum(1 for node in impacted_nodes if node.depth > 1),
                by_kind=by_kind,
                by_resource_category=by_category,
                max_depth_reached=graph.max_depth_reached,
                truncated=graph.truncated,
                as_of=graph.as_of,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="graph.impact.analyze",
                    target_type="source_object",
                    target_id=graph.root_key,
                    metadata={
                        "direction": direction.value,
                        "impacted_count": len(impacted_nodes),
                        "direct_count": result.direct_count,
                        "indirect_count": result.indirect_count,
                        "truncated": result.truncated,
                    },
                )
            )
            unit_of_work.commit()
        return result

    def analyze_spof(self, command: AnalyzeDependencySpofCommand) -> DependencySpofReport:
        tenant_id, subject = self._authorize(command.tenant_id, command.admin_token)
        direction = GraphDirection.from_value(command.direction)
        max_depth, max_nodes = self._limits(command.max_depth, command.max_nodes)
        relation_types = self._relation_types(command.relation_types)
        as_of = self._datetime(command.as_of)
        candidate_kinds = self._filter_values(command.candidate_kinds, "candidate kind")
        candidate_categories = self._filter_values(
            command.candidate_resource_categories, "candidate resource category"
        )
        candidate_types = self._filter_values(
            command.candidate_resource_types, "candidate resource type"
        )
        candidate_statuses = self._filter_values(command.candidate_statuses, "candidate status")
        minimum_affected_nodes = self._minimum_affected_nodes(
            command.minimum_affected_nodes, max_nodes
        )
        sample_limit = self._sample_limit(command.affected_sample_limit)
        pagination = Pagination.from_values(command.limit, command.cursor)
        filters = self._spof_filters(
            candidate_kinds,
            candidate_categories,
            candidate_types,
            candidate_statuses,
            minimum_affected_nodes,
            sample_limit,
        )
        with self._transaction_manager.begin() as unit_of_work:
            graph = self._traverse(
                tenant_id,
                command.root_key,
                direction,
                max_depth,
                max_nodes,
                relation_types,
                as_of,
            ).graph
            analysis = self._analyze_spof_graph(graph)
            candidate_indexes = self._matching_spof_indexes(
                analysis,
                candidate_kinds,
                candidate_categories,
                candidate_types,
                candidate_statuses,
                minimum_affected_nodes,
            )
            fingerprint = self._cursor_fingerprint(graph, filters)
            offset = self._cursor_offset(pagination.cursor, fingerprint)
            if offset > len(candidate_indexes):
                raise ValidationError("SPOF cursor is outside the result set")
            page_indexes = candidate_indexes[offset : offset + pagination.limit]
            ranks = {index: rank for rank, index in enumerate(candidate_indexes, start=1)}
            candidates = tuple(
                self._spof_candidate(analysis, index, ranks[index], sample_limit)
                for index in page_indexes
            )
            next_offset = offset + len(page_indexes)
            next_cursor = (
                self._encode_cursor(next_offset, fingerprint)
                if next_offset < len(candidate_indexes)
                else None
            )
            report = DependencySpofReport(
                root_key=graph.root_key,
                direction=graph.direction,
                relation_types=graph.relation_types,
                as_of=graph.as_of,
                node_count=len(graph.nodes),
                edge_count=len(graph.edges),
                total_spof_count=len(candidate_indexes),
                candidates=candidates,
                next_cursor=next_cursor,
                max_depth_reached=graph.max_depth_reached,
                truncated=graph.truncated,
                filters=filters,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="graph.spof.analyze",
                    target_type="source_object",
                    target_id=graph.root_key,
                    metadata={
                        "direction": direction.value,
                        "node_count": len(graph.nodes),
                        "spof_count": len(candidate_indexes),
                        "returned_count": len(candidates),
                        "truncated": graph.truncated,
                    },
                )
            )
            unit_of_work.commit()
        return report

    def export(self, command: ExportDependencyGraphCommand) -> DependencyGraphExport:
        tenant_id, subject = self._authorize(command.tenant_id, command.admin_token)
        direction = GraphDirection.from_value(command.direction)
        export_format = GraphExportFormat.from_value(command.format)
        max_depth, max_nodes = self._limits(command.max_depth, command.max_nodes)
        relation_types = self._relation_types(command.relation_types)
        as_of = self._datetime(command.as_of)
        candidate_kinds = self._filter_values(command.candidate_kinds, "candidate kind")
        candidate_categories = self._filter_values(
            command.candidate_resource_categories, "candidate resource category"
        )
        candidate_types = self._filter_values(
            command.candidate_resource_types, "candidate resource type"
        )
        candidate_statuses = self._filter_values(command.candidate_statuses, "candidate status")
        minimum_affected_nodes = self._minimum_affected_nodes(
            command.minimum_affected_nodes, max_nodes
        )
        with self._transaction_manager.begin() as unit_of_work:
            graph = self._traverse(
                tenant_id,
                command.root_key,
                direction,
                max_depth,
                max_nodes,
                relation_types,
                as_of,
            ).graph
            spof_counts: dict[str, int] = {}
            if command.include_spof:
                analysis = self._analyze_spof_graph(graph)
                for index in self._matching_spof_indexes(
                    analysis,
                    candidate_kinds,
                    candidate_categories,
                    candidate_types,
                    candidate_statuses,
                    minimum_affected_nodes,
                ):
                    spof_counts[analysis.nodes[index].key] = analysis.affected_counts[index]
            content, content_type, suffix = self._render_export(graph, export_format, spof_counts)
            filename = f"openinfra-graph-{self._safe_filename(graph.root_key)}.{suffix}"
            result = DependencyGraphExport(
                filename=filename,
                content_type=content_type,
                content=content,
                format=export_format,
                node_count=len(graph.nodes),
                edge_count=len(graph.edges),
                spof_count=len(spof_counts),
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="graph.export",
                    target_type="source_object",
                    target_id=graph.root_key,
                    metadata={
                        "direction": direction.value,
                        "format": export_format.value,
                        "include_spof": command.include_spof,
                        "node_count": result.node_count,
                        "edge_count": result.edge_count,
                        "spof_count": result.spof_count,
                        "size_bytes": len(result.content),
                    },
                )
            )
            unit_of_work.commit()
        return result

    def find_path(self, command: FindDependencyPathCommand) -> DependencyPath:
        tenant_id, subject = self._authorize(command.tenant_id, command.admin_token)
        direction = GraphDirection.from_value(command.direction)
        max_depth, max_nodes = self._limits(command.max_depth, command.max_nodes)
        relation_types = self._relation_types(command.relation_types)
        as_of = self._datetime(command.as_of)
        source_key = command.source_key.strip().lower()
        target_key = command.target_key.strip().lower()
        with self._transaction_manager.begin() as unit_of_work:
            state = self._traverse(
                tenant_id,
                source_key,
                direction,
                max_depth,
                max_nodes,
                relation_types,
                as_of,
                stop_key=target_key,
            )
            nodes_by_key = {node.key: node for node in state.graph.nodes}
            found = target_key in nodes_by_key
            path_nodes: list[GraphNode] = []
            path_edges: list[GraphEdge] = []
            if found:
                cursor = target_key
                path_nodes.append(nodes_by_key[cursor])
                while cursor != source_key:
                    previous_key, edge = state.predecessors[cursor]
                    path_edges.append(edge)
                    cursor = previous_key
                    path_nodes.append(nodes_by_key[cursor])
                path_nodes.reverse()
                path_edges.reverse()
            result = DependencyPath(
                source_key=source_key,
                target_key=target_key,
                direction=direction,
                found=found,
                truncated=state.graph.truncated,
                nodes=tuple(path_nodes),
                edges=tuple(path_edges),
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="graph.path.find",
                    target_type="source_object",
                    target_id=source_key,
                    metadata={
                        "target_key": target_key,
                        "direction": direction.value,
                        "found": found,
                        "hop_count": len(path_edges) if found else None,
                        "truncated": result.truncated,
                    },
                )
            )
            unit_of_work.commit()
        return result

    def _analyze_spof_graph(self, graph: DependencyGraph) -> _SpofAnalysis:
        nodes = graph.nodes
        if not nodes:
            raise ValidationError("dependency graph cannot be empty")
        indexes = {node.key: index for index, node in enumerate(nodes)}
        root_index = indexes.get(graph.root_key)
        if root_index is None:
            raise ValidationError("dependency graph root is missing from nodes")
        predecessors: list[set[int]] = [set() for _ in nodes]
        successors: list[set[int]] = [set() for _ in nodes]
        for edge in graph.edges:
            source_index = indexes.get(edge.source_key)
            target_index = indexes.get(edge.target_key)
            if source_index is None or target_index is None:
                continue
            directed_edges: tuple[tuple[int, int], ...]
            if graph.direction is GraphDirection.OUTGOING:
                directed_edges = ((source_index, target_index),)
            elif graph.direction is GraphDirection.INCOMING:
                directed_edges = ((target_index, source_index),)
            else:
                directed_edges = ((source_index, target_index), (target_index, source_index))
            for origin, destination in directed_edges:
                if origin == destination:
                    continue
                successors[origin].add(destination)
                predecessors[destination].add(origin)
        all_bits = (1 << len(nodes)) - 1
        dominators = [all_bits for _ in nodes]
        dominators[root_index] = 1 << root_index
        ordered_indexes = tuple(index for index in range(len(nodes)) if index != root_index)
        converged = False
        for _ in range(len(nodes) + 1):
            changed = False
            for index in ordered_indexes:
                node_predecessors = predecessors[index]
                if not node_predecessors:
                    new_value = 1 << index
                else:
                    intersection = all_bits
                    for predecessor in sorted(node_predecessors):
                        intersection &= dominators[predecessor]
                    new_value = intersection | (1 << index)
                if new_value != dominators[index]:
                    dominators[index] = new_value
                    changed = True
            if not changed:
                converged = True
                break
        if not converged:
            raise ValidationError("SPOF dominator analysis did not converge")
        affected_counts = [0 for _ in nodes]
        for node_index, dominator_bits in enumerate(dominators):
            bits = dominator_bits & ~(1 << node_index)
            while bits:
                least_significant = bits & -bits
                dominator_index = least_significant.bit_length() - 1
                affected_counts[dominator_index] += 1
                bits ^= least_significant
        return _SpofAnalysis(
            graph=graph,
            nodes=nodes,
            indexes=indexes,
            dominators=tuple(dominators),
            successors=tuple(tuple(sorted(values)) for values in successors),
            affected_counts=tuple(affected_counts),
        )

    def _matching_spof_indexes(
        self,
        analysis: _SpofAnalysis,
        kinds: tuple[str, ...],
        categories: tuple[str, ...],
        resource_types: tuple[str, ...],
        statuses: tuple[str, ...],
        minimum_affected_nodes: int,
    ) -> tuple[int, ...]:
        root_index = analysis.indexes[analysis.graph.root_key]
        matched = [
            index
            for index, node in enumerate(analysis.nodes)
            if index != root_index
            and analysis.affected_counts[index] >= minimum_affected_nodes
            and (not kinds or node.kind in kinds)
            and (not categories or node.resource_category in categories)
            and (not resource_types or node.resource_type in resource_types)
            and (not statuses or node.status in statuses)
        ]
        matched.sort(
            key=lambda index: (
                -analysis.affected_counts[index],
                analysis.nodes[index].depth,
                analysis.nodes[index].key,
            )
        )
        return tuple(matched)

    def _spof_candidate(
        self, analysis: _SpofAnalysis, index: int, rank: int, sample_limit: int
    ) -> DependencySpofCandidate:
        node = analysis.nodes[index]
        marker = 1 << index
        affected_indexes = [
            candidate_index
            for candidate_index, dominators in enumerate(analysis.dominators)
            if candidate_index != index and dominators & marker
        ]
        affected_indexes.sort(
            key=lambda candidate_index: (
                analysis.nodes[candidate_index].depth,
                analysis.nodes[candidate_index].key,
            )
        )
        by_kind: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for affected_index in affected_indexes:
            affected = analysis.nodes[affected_index]
            by_kind[affected.kind] = by_kind.get(affected.kind, 0) + 1
            by_category[affected.resource_category] = (
                by_category.get(affected.resource_category, 0) + 1
            )
        direct_count = sum(
            1
            for successor in analysis.successors[index]
            if successor != index and analysis.dominators[successor] & marker
        )
        population = max(1, len(analysis.nodes) - 1)
        sample = tuple(
            analysis.nodes[affected_index].key for affected_index in affected_indexes[:sample_limit]
        )
        return DependencySpofCandidate(
            rank=rank,
            node=node,
            affected_count=len(affected_indexes),
            direct_affected_count=direct_count,
            affected_ratio=len(affected_indexes) / population,
            affected_sample=sample,
            affected_sample_truncated=len(affected_indexes) > sample_limit,
            by_kind=by_kind,
            by_resource_category=by_category,
        )

    def _render_export(
        self,
        graph: DependencyGraph,
        export_format: GraphExportFormat,
        spof_counts: dict[str, int],
    ) -> tuple[bytes, str, str]:
        if export_format is GraphExportFormat.JSON:
            payload = graph.as_dict()
            payload["spof"] = {
                "algorithm": "rooted-dominators",
                "count": len(spof_counts),
                "items": [
                    {"key": key, "affected_count": affected_count}
                    for key, affected_count in sorted(
                        spof_counts.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
            }
            content = (
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            return content, "application/json; charset=utf-8", "json"
        if export_format is GraphExportFormat.CSV:
            stream = io.StringIO(newline="")
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(
                (
                    "record_type",
                    "key",
                    "display_name",
                    "kind",
                    "resource_category",
                    "resource_type",
                    "status",
                    "depth",
                    "is_spof",
                    "affected_count",
                    "relation_id",
                    "relation_type",
                    "source_key",
                    "target_key",
                    "provenance",
                    "valid_from",
                    "valid_to",
                )
            )
            for node in graph.nodes:
                writer.writerow(
                    (
                        "node",
                        node.key,
                        node.display_name,
                        node.kind,
                        node.resource_category,
                        node.resource_type,
                        node.status,
                        node.depth,
                        str(node.key in spof_counts).lower(),
                        spof_counts.get(node.key, 0),
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    )
                )
            for edge in graph.edges:
                writer.writerow(
                    (
                        "edge",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        edge.id,
                        edge.relation_type,
                        edge.source_key,
                        edge.target_key,
                        edge.provenance,
                        edge.valid_from,
                        edge.valid_to or "",
                    )
                )
            return (
                stream.getvalue().encode("utf-8"),
                "text/csv; charset=utf-8",
                "csv",
            )
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <key id="display_name" for="node" attr.name="display_name" attr.type="string"/>',
            '  <key id="kind" for="node" attr.name="kind" attr.type="string"/>',
            (
                '  <key id="resource_category" for="node" '
                'attr.name="resource_category" attr.type="string"/>'
            ),
            '  <key id="resource_type" for="node" attr.name="resource_type" attr.type="string"/>',
            '  <key id="status" for="node" attr.name="status" attr.type="string"/>',
            '  <key id="depth" for="node" attr.name="depth" attr.type="int"/>',
            '  <key id="is_spof" for="node" attr.name="is_spof" attr.type="boolean"/>',
            '  <key id="affected_count" for="node" attr.name="affected_count" attr.type="int"/>',
            '  <key id="relation_type" for="edge" attr.name="relation_type" attr.type="string"/>',
            '  <key id="provenance" for="edge" attr.name="provenance" attr.type="string"/>',
            f'  <graph id="{escape(graph.root_key)}" edgedefault="directed">',
        ]
        for node in graph.nodes:
            lines.extend(
                (
                    f'    <node id="{escape(node.key)}">',
                    f'      <data key="display_name">{escape(node.display_name)}</data>',
                    f'      <data key="kind">{escape(node.kind)}</data>',
                    f'      <data key="resource_category">{escape(node.resource_category)}</data>',
                    f'      <data key="resource_type">{escape(node.resource_type)}</data>',
                    f'      <data key="status">{escape(node.status)}</data>',
                    f'      <data key="depth">{node.depth}</data>',
                    f'      <data key="is_spof">{str(node.key in spof_counts).lower()}</data>',
                    f'      <data key="affected_count">{spof_counts.get(node.key, 0)}</data>',
                    "    </node>",
                )
            )
        node_keys = {node.key for node in graph.nodes}
        for edge in graph.edges:
            if edge.source_key not in node_keys or edge.target_key not in node_keys:
                continue
            lines.extend(
                (
                    (
                        f'    <edge id="{escape(edge.id)}" '
                        f'source="{escape(edge.source_key)}" '
                        f'target="{escape(edge.target_key)}">'
                    ),
                    f'      <data key="relation_type">{escape(edge.relation_type)}</data>',
                    f'      <data key="provenance">{escape(edge.provenance)}</data>',
                    "    </edge>",
                )
            )
        lines.extend(("  </graph>", "</graphml>", ""))
        return (
            "\n".join(lines).encode("utf-8"),
            "application/graphml+xml; charset=utf-8",
            "graphml",
        )

    def _spof_filters(
        self,
        kinds: tuple[str, ...],
        categories: tuple[str, ...],
        resource_types: tuple[str, ...],
        statuses: tuple[str, ...],
        minimum_affected_nodes: int,
        sample_limit: int,
    ) -> dict[str, object]:
        return {
            "candidate_kinds": list(kinds),
            "candidate_resource_categories": list(categories),
            "candidate_resource_types": list(resource_types),
            "candidate_statuses": list(statuses),
            "minimum_affected_nodes": minimum_affected_nodes,
            "affected_sample_limit": sample_limit,
        }

    def _filter_values(self, values: tuple[str, ...], label: str) -> tuple[str, ...]:
        normalized = tuple(sorted({value.strip().lower() for value in values if value.strip()}))
        if len(normalized) > 100:
            raise ValidationError(f"{label} filter cannot contain more than 100 values")
        if any(len(value) > 120 for value in normalized):
            raise ValidationError(f"{label} filter values cannot exceed 120 characters")
        return normalized

    def _minimum_affected_nodes(self, value: int, max_nodes: int) -> int:
        normalized = int(value)
        if not 1 <= normalized < max_nodes:
            raise ValidationError("minimum affected nodes must be between 1 and max_nodes - 1")
        return normalized

    def _sample_limit(self, value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 200:
            raise ValidationError("affected sample limit must be between 1 and 200")
        return normalized

    def _cursor_fingerprint(self, graph: DependencyGraph, filters: dict[str, object]) -> str:
        payload = json.dumps(
            {
                "root_key": graph.root_key,
                "direction": graph.direction.value,
                "max_depth": graph.max_depth,
                "max_nodes": graph.max_nodes,
                "as_of": graph.as_of,
                "relation_types": graph.relation_types,
                "filters": filters,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:24]

    def _encode_cursor(self, offset: int, fingerprint: str) -> str:
        payload = json.dumps(
            {"offset": offset, "fingerprint": fingerprint},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    def _cursor_offset(self, cursor: str | None, fingerprint: str) -> int:
        if cursor is None:
            return 0
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("cursor payload is not an object")
            if payload.get("fingerprint") != fingerprint:
                raise ValidationError("SPOF cursor does not match the current query")
            offset = int(payload["offset"])
        except ValidationError:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError) as exc:
            raise ValidationError("SPOF cursor is invalid") from exc
        if offset < 0:
            raise ValidationError("SPOF cursor offset cannot be negative")
        return offset

    def _safe_filename(self, value: str) -> str:
        normalized = "".join(
            character.lower() if character.isalnum() else "-" for character in value
        )
        compact = "-".join(part for part in normalized.split("-") if part)
        return compact[:120] or "dependency-graph"

    def _traverse(
        self,
        tenant_id: TenantId,
        root_key: str,
        direction: GraphDirection,
        max_depth: int,
        max_nodes: int,
        relation_types: tuple[str, ...],
        as_of: datetime | None,
        stop_key: str | None = None,
    ) -> _TraversalState:
        normalized_root = root_key.strip().lower()
        root_payload = self._object_payload(tenant_id, normalized_root, as_of)
        if root_payload is None:
            raise NotFoundError("source object not found: " + normalized_root)
        nodes: dict[str, GraphNode] = {
            normalized_root: GraphNode.from_object_payload(root_payload, 0)
        }
        edges: dict[str, GraphEdge] = {}
        predecessors: dict[str, tuple[str, GraphEdge]] = {}
        queue: deque[tuple[str, int]] = deque(((normalized_root, 0),))
        truncated = False
        while queue:
            current_key, depth = queue.popleft()
            if stop_key is not None and current_key == stop_key:
                break
            if depth >= max_depth:
                continue
            for relation in self._relations(tenant_id, current_key, direction, as_of):
                if relation_types and relation.relation_type.value not in relation_types:
                    continue
                neighbor_key = self._neighbor_key(current_key, relation, direction)
                if neighbor_key is None:
                    raise ValidationError("relation repository returned an unrelated relation")
                graph_edge = GraphEdge.from_relation(relation)
                edges[graph_edge.id] = graph_edge
                if neighbor_key in nodes:
                    continue
                if len(nodes) >= max_nodes:
                    truncated = True
                    continue
                payload = self._object_payload(tenant_id, neighbor_key, as_of)
                if payload is None:
                    continue
                nodes[neighbor_key] = GraphNode.from_object_payload(payload, depth + 1)
                predecessors[neighbor_key] = (current_key, graph_edge)
                queue.append((neighbor_key, depth + 1))
                if stop_key is not None and neighbor_key == stop_key:
                    queue.clear()
                    break
        ordered_nodes = tuple(sorted(nodes.values(), key=lambda item: (item.depth, item.key)))
        ordered_edges = tuple(
            sorted(edges.values(), key=lambda item: (item.source_key, item.target_key, item.id))
        )
        graph = DependencyGraph(
            root_key=normalized_root,
            direction=direction,
            max_depth=max_depth,
            max_nodes=max_nodes,
            as_of=as_of.isoformat() if as_of is not None else None,
            relation_types=relation_types,
            nodes=ordered_nodes,
            edges=ordered_edges,
            max_depth_reached=max((node.depth for node in ordered_nodes), default=0),
            truncated=truncated,
        )
        return _TraversalState(graph, predecessors)

    def _relations(
        self,
        tenant_id: TenantId,
        key: str,
        direction: GraphDirection,
        as_of: datetime | None,
    ) -> tuple[SourceRelation, ...]:
        relations: dict[str, SourceRelation] = {}
        if direction in (GraphDirection.OUTGOING, GraphDirection.BOTH):
            for relation in self._relation_pages(tenant_id, source_key=key, as_of=as_of):
                relations[relation.id.value] = relation
        if direction in (GraphDirection.INCOMING, GraphDirection.BOTH):
            for relation in self._relation_pages(tenant_id, target_key=key, as_of=as_of):
                relations[relation.id.value] = relation
        return tuple(
            sorted(
                relations.values(),
                key=lambda item: (
                    item.source_key.value,
                    item.target_key.value,
                    item.relation_type.value,
                    item.id.value,
                ),
            )
        )

    def _relation_pages(
        self,
        tenant_id: TenantId,
        *,
        source_key: str | None = None,
        target_key: str | None = None,
        as_of: datetime | None = None,
    ) -> tuple[SourceRelation, ...]:
        items: list[SourceRelation] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            page = self._repository.list_relations(
                tenant_id=tenant_id,
                pagination=Pagination.from_values(self._RELATION_PAGE_SIZE, cursor),
                source_key=source_key,
                target_key=target_key,
                as_of=as_of,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                break
            if page.next_cursor in seen_cursors:
                raise ValidationError("relation repository returned a cyclic pagination cursor")
            seen_cursors.add(page.next_cursor)
            cursor = page.next_cursor
        return tuple(items)

    def _object_payload(
        self,
        tenant_id: TenantId,
        key: str,
        as_of: datetime | None,
    ) -> dict[str, object] | None:
        if as_of is None:
            source_object = self._repository.find_object(tenant_id, key)
            return source_object.as_dict() if source_object is not None else None
        snapshot = self._repository.find_object_as_of(tenant_id, key, as_of)
        return dict(snapshot.payload) if snapshot is not None else None

    def _authorize(self, tenant_id: str, token: str) -> tuple[TenantId, str]:
        normalized_tenant = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized_tenant.value, token, Permission.RSOT_READ)
        )
        return normalized_tenant, principal.subject

    def _limits(self, max_depth: int, max_nodes: int) -> tuple[int, int]:
        depth = int(max_depth)
        nodes = int(max_nodes)
        if not 1 <= depth <= self._MAX_DEPTH:
            raise ValidationError(f"graph max_depth must be between 1 and {self._MAX_DEPTH}")
        if not 2 <= nodes <= self._MAX_NODES:
            raise ValidationError(f"graph max_nodes must be between 2 and {self._MAX_NODES}")
        return depth, nodes

    def _relation_types(self, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({RelationType.from_value(value).value for value in values}))

    def _datetime(self, value: str | datetime | None) -> datetime | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError("graph as_of must be an ISO-8601 datetime") from exc
        if parsed.tzinfo is None:
            raise ValidationError("graph as_of must be timezone-aware")
        return parsed.astimezone(UTC)

    def _neighbor_key(
        self,
        current_key: str,
        relation: SourceRelation,
        direction: GraphDirection,
    ) -> str | None:
        if (
            direction in (GraphDirection.OUTGOING, GraphDirection.BOTH)
            and relation.source_key.value == current_key
        ):
            return relation.target_key.value
        if (
            direction in (GraphDirection.INCOMING, GraphDirection.BOTH)
            and relation.target_key.value == current_key
        ):
            return relation.source_key.value
        return None
