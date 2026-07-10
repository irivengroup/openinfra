from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from openinfra.domain.common import Code, EntityId, Name, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceOfTruthObject, SourceRelation


class DependencyKind(StrEnum):
    NETWORK_FLOW = "network_flow"
    APPLICATION_CALL = "application_call"
    STORAGE = "storage"
    DATABASE = "database"
    AUTHENTICATION = "authentication"


class GraphDirection(StrEnum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"

    @classmethod
    def from_value(cls, value: str) -> Self:
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("graph direction must be outgoing, incoming or both") from exc


@dataclass(frozen=True, slots=True)
class DependencyNode:
    id: EntityId
    tenant_id: TenantId
    code: Code
    name: Name
    node_type: str

    @classmethod
    def create(cls, tenant_id: TenantId, code: str, name: str, node_type: str) -> Self:
        normalized_type = node_type.strip().lower()
        if not normalized_type:
            raise ValidationError("dependency node type is mandatory")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            code=Code.from_value(code, "dependency node code"),
            name=Name.from_value(name, "dependency node name"),
            node_type=normalized_type,
        )


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    id: EntityId
    tenant_id: TenantId
    source_code: Code
    target_code: Code
    kind: DependencyKind
    protocol: str | None
    port: int | None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        source_code: str,
        target_code: str,
        kind: DependencyKind,
        protocol: str | None = None,
        port: int | None = None,
    ) -> Self:
        normalized_protocol = protocol.strip().lower() if protocol else None
        if port is not None and not 1 <= port <= 65535:
            raise ValidationError("dependency port must be between 1 and 65535")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            source_code=Code.from_value(source_code, "source node code"),
            target_code=Code.from_value(target_code, "target node code"),
            kind=kind,
            protocol=normalized_protocol,
            port=port,
        )


@dataclass(frozen=True, slots=True)
class GraphNode:
    key: str
    display_name: str
    kind: str
    resource_category: str
    resource_type: str
    status: str
    depth: int

    @classmethod
    def from_object_payload(cls, payload: Mapping[str, object], depth: int) -> Self:
        if depth < 0:
            raise ValidationError("graph node depth cannot be negative")
        key = str(payload.get("key", "")).strip().lower()
        display_name = " ".join(str(payload.get("display_name", "")).strip().split())
        kind = str(payload.get("kind", "")).strip().lower()
        if not key or not display_name or not kind:
            raise ValidationError("graph node payload is incomplete")
        return cls(
            key=key,
            display_name=display_name,
            kind=kind,
            resource_category=str(payload.get("resource_category", kind)).strip().lower(),
            resource_type=str(payload.get("resource_type", kind)).strip().lower(),
            status=str(payload.get("status", "active")).strip().lower(),
            depth=depth,
        )

    @classmethod
    def from_source_object(cls, source_object: SourceOfTruthObject, depth: int) -> Self:
        return cls.from_object_payload(source_object.as_dict(), depth)

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "kind": self.kind,
            "resource_category": self.resource_category,
            "resource_type": self.resource_type,
            "status": self.status,
            "depth": self.depth,
        }


@dataclass(frozen=True, slots=True)
class GraphEdge:
    id: str
    relation_type: str
    source_key: str
    target_key: str
    provenance: str
    valid_from: str
    valid_to: str | None

    @classmethod
    def from_relation(cls, relation: SourceRelation) -> Self:
        return cls(
            id=relation.id.value,
            relation_type=relation.relation_type.value,
            source_key=relation.source_key.value,
            target_key=relation.target_key.value,
            provenance=relation.provenance.value,
            valid_from=relation.valid_from.isoformat(),
            valid_to=relation.valid_to.isoformat() if relation.valid_to is not None else None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "relation_type": self.relation_type,
            "source_key": self.source_key,
            "target_key": self.target_key,
            "provenance": self.provenance,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    root_key: str
    direction: GraphDirection
    max_depth: int
    max_nodes: int
    as_of: str | None
    relation_types: tuple[str, ...]
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    max_depth_reached: int
    truncated: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "root_key": self.root_key,
            "direction": self.direction.value,
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "as_of": self.as_of,
            "relation_types": list(self.relation_types),
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "max_depth_reached": self.max_depth_reached,
            "truncated": self.truncated,
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
        }


@dataclass(frozen=True, slots=True)
class DependencyPath:
    source_key: str
    target_key: str
    direction: GraphDirection
    found: bool
    truncated: bool
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "source_key": self.source_key,
            "target_key": self.target_key,
            "direction": self.direction.value,
            "found": self.found,
            "truncated": self.truncated,
            "hop_count": len(self.edges) if self.found else None,
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
        }


@dataclass(frozen=True, slots=True)
class DependencyImpact:
    root_key: str
    direction: GraphDirection
    impacted_nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    direct_count: int
    indirect_count: int
    by_kind: dict[str, int]
    by_resource_category: dict[str, int]
    max_depth_reached: int
    truncated: bool
    as_of: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "root_key": self.root_key,
            "direction": self.direction.value,
            "as_of": self.as_of,
            "impacted_count": len(self.impacted_nodes),
            "direct_count": self.direct_count,
            "indirect_count": self.indirect_count,
            "by_kind": dict(sorted(self.by_kind.items())),
            "by_resource_category": dict(sorted(self.by_resource_category.items())),
            "max_depth_reached": self.max_depth_reached,
            "truncated": self.truncated,
            "nodes": [node.as_dict() for node in self.impacted_nodes],
            "edges": [edge.as_dict() for edge in self.edges],
        }
