from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime

from openinfra.application.ports import AuditRepository, SourceOfTruthRepository, TransactionManager
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, NotFoundError, Pagination, TenantId, ValidationError
from openinfra.domain.dependency import (
    DependencyGraph,
    DependencyImpact,
    DependencyPath,
    GraphDirection,
    GraphEdge,
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
class _TraversalState:
    graph: DependencyGraph
    predecessors: dict[str, tuple[str, GraphEdge]]


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
