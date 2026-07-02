from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from openinfra.domain.common import Code, EntityId, Name, TenantId, ValidationError


class DependencyKind(StrEnum):
    NETWORK_FLOW = "network_flow"
    APPLICATION_CALL = "application_call"
    STORAGE = "storage"
    DATABASE = "database"
    AUTHENTICATION = "authentication"


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
