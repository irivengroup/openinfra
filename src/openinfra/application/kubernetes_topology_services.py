from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from openinfra.application.ports import (
    AuditRepository,
    FlowMatrixRepository,
    KubernetesTopologyRepository,
    KubernetesTopologySnapshotPage,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    DomainEvent,
    NotFoundError,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.domain.flow_matrix import FlowDeclaration
from openinfra.domain.kubernetes_exposure import KubernetesExposureReport
from openinfra.domain.kubernetes_topology import (
    KubernetesResource,
    KubernetesTopologySnapshot,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission
from openinfra.domain.source_of_truth import SourceRelation


@dataclass(frozen=True, slots=True)
class ImportKubernetesTopologyCommand:
    tenant_id: str
    admin_token: str
    cluster_key: str
    cluster_name: str
    provider: str
    kubernetes_version: str
    source_ref: str
    observed_at: datetime
    resources: tuple[dict[str, Any], ...]
    region: str | None = None
    site_code: str | None = None
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetKubernetesTopologyCommand:
    tenant_id: str
    admin_token: str
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class GetLatestKubernetesTopologyCommand:
    tenant_id: str
    admin_token: str
    cluster_key: str


@dataclass(frozen=True, slots=True)
class ListKubernetesTopologiesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    cluster_key: str | None = None
    provider: str | None = None
    site_code: str | None = None


class KubernetesTopologyService:
    _PAGE_SIZE = 500
    _MAX_FLOW_DECLARATIONS = 10_000
    _MAX_CORRELATION_OBJECT_KEYS = 128
    _MAX_DEPENDENCY_RELATIONS = 10_000
    _MAX_DEPENDENCY_OBJECTS = 2_048

    def __init__(
        self,
        repository: KubernetesTopologyRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        flow_matrix_repository: FlowMatrixRepository,
        source_of_truth_repository: SourceOfTruthRepository,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._flow_matrix_repository = flow_matrix_repository
        self._source_of_truth_repository = source_of_truth_repository

    def import_snapshot(
        self, command: ImportKubernetesTopologyCommand
    ) -> KubernetesTopologySnapshot:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_WRITE
        )
        resources = tuple(KubernetesResource.from_dict(dict(item)) for item in command.resources)
        candidate = KubernetesTopologySnapshot.create(
            tenant_id=tenant_id,
            cluster_key=command.cluster_key,
            cluster_name=command.cluster_name,
            provider=command.provider,
            kubernetes_version=command.kubernetes_version,
            source_ref=command.source_ref,
            observed_at=command.observed_at,
            resources=resources,
            region=command.region,
            site_code=command.site_code,
        )
        existing = self._repository.find_snapshot_by_fingerprint(tenant_id, candidate.fingerprint)
        if existing is not None:
            return existing
        actor = command.actor or principal.subject
        metadata = {
            "cluster_key": candidate.cluster_key,
            "provider": candidate.provider,
            "resource_count": len(candidate.resources),
            "fingerprint": candidate.fingerprint,
        }
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_snapshot(candidate)
            self._repository.append_event(
                DomainEvent.create(
                    candidate.tenant_id,
                    candidate.id,
                    "kubernetes.topology.imported",
                    metadata,
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    candidate.tenant_id,
                    actor,
                    "kubernetes.topology.imported",
                    "kubernetes_topology_snapshot",
                    candidate.id.value,
                    metadata=metadata,
                )
            )
            unit_of_work.commit()
        return candidate

    def get_snapshot(self, command: GetKubernetesTopologyCommand) -> KubernetesTopologySnapshot:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        snapshot = self._repository.get_snapshot(tenant_id, command.snapshot_id)
        if snapshot is None:
            raise NotFoundError("Kubernetes topology snapshot not found")
        return snapshot

    def get_latest_snapshot(
        self, command: GetLatestKubernetesTopologyCommand
    ) -> KubernetesTopologySnapshot:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        snapshot = self._repository.find_latest_snapshot(tenant_id, command.cluster_key)
        if snapshot is None:
            raise NotFoundError("Kubernetes topology snapshot not found")
        return snapshot

    def list_snapshots(
        self, command: ListKubernetesTopologiesCommand
    ) -> KubernetesTopologySnapshotPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        return self._repository.list_snapshots(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.cluster_key,
            command.provider,
            command.site_code,
        )

    def topology(self, command: GetKubernetesTopologyCommand) -> dict[str, object]:
        return self.get_snapshot(command).topology()

    def latest_topology(self, command: GetLatestKubernetesTopologyCommand) -> dict[str, object]:
        return self.get_latest_snapshot(command).topology()

    def exposure(self, command: GetKubernetesTopologyCommand) -> KubernetesExposureReport:
        snapshot = self.get_snapshot(command)
        return self._exposure_report(snapshot)

    def latest_exposure(
        self, command: GetLatestKubernetesTopologyCommand
    ) -> KubernetesExposureReport:
        snapshot = self.get_latest_snapshot(command)
        return self._exposure_report(snapshot)

    def _exposure_report(self, snapshot: KubernetesTopologySnapshot) -> KubernetesExposureReport:
        declarations, flow_truncated = self._active_flow_declarations(snapshot.tenant_id)
        object_keys = sorted(
            {
                str(key)
                for resource in snapshot.resources
                for key in resource.attributes.get("rsot_object_keys", [])
                if isinstance(key, str)
            }
        )
        key_truncated = len(object_keys) > self._MAX_CORRELATION_OBJECT_KEYS
        selected_keys = tuple(object_keys[: self._MAX_CORRELATION_OBJECT_KEYS])
        relations, relation_truncated = self._dependency_relations(
            snapshot.tenant_id, selected_keys, snapshot.observed_at
        )
        dependency_keys = set(selected_keys)
        for relation in relations:
            dependency_keys.add(relation.source_key.value)
            dependency_keys.add(relation.target_key.value)
        object_truncated = len(dependency_keys) > self._MAX_DEPENDENCY_OBJECTS
        objects = tuple(
            item
            for key in sorted(dependency_keys)[: self._MAX_DEPENDENCY_OBJECTS]
            if (item := self._source_of_truth_repository.find_object(snapshot.tenant_id, key))
            is not None
        )
        return KubernetesExposureReport.build(
            snapshot,
            declarations,
            relations,
            objects,
            correlation_truncated=(
                flow_truncated or key_truncated or relation_truncated or object_truncated
            ),
        )

    def _active_flow_declarations(
        self, tenant_id: TenantId
    ) -> tuple[tuple[FlowDeclaration, ...], bool]:
        items: list[FlowDeclaration] = []
        cursor: str | None = None
        seen: set[str] = set()
        while len(items) < self._MAX_FLOW_DECLARATIONS:
            page = self._flow_matrix_repository.list_declarations(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_FLOW_DECLARATIONS - len(items)), cursor
                ),
                include_retired=False,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items), False
            if page.next_cursor in seen:
                raise ValidationError("flow declaration repository returned a cyclic cursor")
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        return tuple(items), cursor is not None

    def _dependency_relations(
        self, tenant_id: TenantId, object_keys: tuple[str, ...], as_of: datetime
    ) -> tuple[tuple[SourceRelation, ...], bool]:
        relations: dict[str, SourceRelation] = {}
        truncated = False
        for object_key in object_keys:
            for source_key, target_key in ((object_key, None), (None, object_key)):
                cursor: str | None = None
                seen: set[str] = set()
                while len(relations) < self._MAX_DEPENDENCY_RELATIONS:
                    page = self._source_of_truth_repository.list_relations(
                        tenant_id,
                        Pagination.from_values(
                            min(
                                self._PAGE_SIZE,
                                self._MAX_DEPENDENCY_RELATIONS - len(relations),
                            ),
                            cursor,
                        ),
                        source_key=source_key,
                        target_key=target_key,
                        as_of=as_of,
                    )
                    for relation in page.items:
                        relations[relation.id.value] = relation
                    if page.next_cursor is None:
                        break
                    if page.next_cursor in seen:
                        raise ValidationError("source relation repository returned a cyclic cursor")
                    seen.add(page.next_cursor)
                    cursor = page.next_cursor
                if len(relations) >= self._MAX_DEPENDENCY_RELATIONS:
                    truncated = True
                    break
            if truncated:
                break
        return tuple(relations[key] for key in sorted(relations)), truncated

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized.value, token, permission)
        )
        return normalized, principal
