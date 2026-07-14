from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from openinfra.application.ports import (
    AuditRepository,
    KubernetesTopologyRepository,
    KubernetesTopologySnapshotPage,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, DomainEvent, NotFoundError, Pagination, TenantId
from openinfra.domain.kubernetes_topology import (
    KubernetesResource,
    KubernetesTopologySnapshot,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission


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
    def __init__(
        self,
        repository: KubernetesTopologyRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

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

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized.value, token, permission)
        )
        return normalized, principal
