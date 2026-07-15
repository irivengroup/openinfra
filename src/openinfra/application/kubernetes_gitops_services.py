from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from openinfra.application.ports import (
    AuditRepository,
    KubernetesGitOpsRepository,
    KubernetesGitOpsStatePage,
    KubernetesTopologyRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    DomainEvent,
    NotFoundError,
    Pagination,
    TenantId,
)
from openinfra.domain.kubernetes_gitops import (
    KubernetesGitOpsComplianceReport,
    KubernetesGitOpsComplianceStatus,
    KubernetesGitOpsPolicy,
    KubernetesGitOpsResource,
    KubernetesGitOpsState,
)
from openinfra.domain.kubernetes_topology import KubernetesTopologySnapshot
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class ImportKubernetesGitOpsStateCommand:
    tenant_id: str
    admin_token: str
    cluster_key: str
    repository_ref: str
    revision: str
    source_path: str
    owner: str
    environment: str
    captured_at: datetime
    policy: dict[str, Any]
    resources: tuple[dict[str, Any], ...]
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetKubernetesGitOpsStateCommand:
    tenant_id: str
    admin_token: str
    state_id: str


@dataclass(frozen=True, slots=True)
class GetLatestKubernetesGitOpsStateCommand:
    tenant_id: str
    admin_token: str
    cluster_key: str


@dataclass(frozen=True, slots=True)
class ListKubernetesGitOpsStatesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    cluster_key: str | None = None
    environment: str | None = None
    owner: str | None = None


@dataclass(frozen=True, slots=True)
class AssessKubernetesGitOpsDriftCommand:
    tenant_id: str
    admin_token: str
    expected_state_id: str
    observed_snapshot_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class AssessLatestKubernetesGitOpsDriftCommand:
    tenant_id: str
    admin_token: str
    cluster_key: str
    actor: str | None = None


class KubernetesGitOpsService:
    def __init__(
        self,
        repository: KubernetesGitOpsRepository,
        topology_repository: KubernetesTopologyRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._topology_repository = topology_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def import_state(self, command: ImportKubernetesGitOpsStateCommand) -> KubernetesGitOpsState:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_WRITE
        )
        policy = KubernetesGitOpsPolicy.from_dict(command.policy)
        resources = tuple(
            KubernetesGitOpsResource.from_dict(dict(item)) for item in command.resources
        )
        candidate = KubernetesGitOpsState.create(
            tenant_id=tenant_id,
            cluster_key=command.cluster_key,
            repository_ref=command.repository_ref,
            revision=command.revision,
            source_path=command.source_path,
            owner=command.owner,
            environment=command.environment,
            captured_at=command.captured_at,
            policy=policy,
            resources=resources,
        )
        existing = self._repository.find_state_by_fingerprint(tenant_id, candidate.fingerprint)
        if existing is not None:
            return existing
        actor = command.actor or principal.subject
        metadata = {
            "cluster_key": candidate.cluster_key,
            "environment": candidate.environment,
            "owner": candidate.owner,
            "revision": candidate.revision,
            "resource_count": len(candidate.resources),
            "fingerprint": candidate.fingerprint,
        }
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_state(candidate)
            self._repository.append_event(
                DomainEvent.create(
                    candidate.tenant_id,
                    candidate.id,
                    "kubernetes.gitops.state.imported",
                    metadata,
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    candidate.tenant_id,
                    actor,
                    "kubernetes.gitops.state.imported",
                    "kubernetes_gitops_state",
                    candidate.id.value,
                    metadata=metadata,
                )
            )
            unit_of_work.commit()
        return candidate

    def get_state(self, command: GetKubernetesGitOpsStateCommand) -> KubernetesGitOpsState:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        state = self._repository.get_state(tenant_id, command.state_id)
        if state is None:
            raise NotFoundError("Kubernetes GitOps state not found")
        return state

    def get_latest_state(
        self, command: GetLatestKubernetesGitOpsStateCommand
    ) -> KubernetesGitOpsState:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        state = self._repository.find_latest_state(tenant_id, command.cluster_key)
        if state is None:
            raise NotFoundError("Kubernetes GitOps state not found")
        return state

    def list_states(self, command: ListKubernetesGitOpsStatesCommand) -> KubernetesGitOpsStatePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        return self._repository.list_states(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.cluster_key,
            command.environment,
            command.owner,
        )

    def assess(
        self, command: AssessKubernetesGitOpsDriftCommand
    ) -> KubernetesGitOpsComplianceReport:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        expected = self._repository.get_state(tenant_id, command.expected_state_id)
        if expected is None:
            raise NotFoundError("Kubernetes GitOps state not found")
        observed = self._topology_repository.get_snapshot(tenant_id, command.observed_snapshot_id)
        if observed is None:
            raise NotFoundError("Kubernetes topology snapshot not found")
        return self._record_assessment(
            expected,
            observed,
            command.actor or principal.subject,
        )

    def assess_latest(
        self, command: AssessLatestKubernetesGitOpsDriftCommand
    ) -> KubernetesGitOpsComplianceReport:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.KUBERNETES_READ
        )
        expected = self._repository.find_latest_state(tenant_id, command.cluster_key)
        if expected is None:
            raise NotFoundError("Kubernetes GitOps state not found")
        observed = self._topology_repository.find_latest_snapshot(tenant_id, command.cluster_key)
        if observed is None:
            raise NotFoundError("Kubernetes topology snapshot not found")
        return self._record_assessment(
            expected,
            observed,
            command.actor or principal.subject,
        )

    def _record_assessment(
        self,
        expected: KubernetesGitOpsState,
        observed: KubernetesTopologySnapshot,
        actor: str,
    ) -> KubernetesGitOpsComplianceReport:
        report = KubernetesGitOpsComplianceReport.evaluate(expected, observed)
        metadata = {
            "cluster_key": report.cluster_key,
            "expected_state_id": report.expected_state_id,
            "expected_fingerprint": report.expected_fingerprint,
            "observed_snapshot_id": report.observed_snapshot_id,
            "observed_fingerprint": report.observed_fingerprint,
            "report_fingerprint": report.fingerprint,
            "status": report.status.value,
            "drift_count": len(report.drifts),
            "automatic_remediation": False,
        }
        with self._transaction_manager.begin() as unit_of_work:
            if report.status is KubernetesGitOpsComplianceStatus.DRIFT:
                self._repository.append_event(
                    DomainEvent.create(
                        expected.tenant_id,
                        expected.id,
                        "kubernetes.gitops.drift.detected",
                        metadata,
                    )
                )
            self._audit_repository.append(
                AuditEvent.record(
                    expected.tenant_id,
                    actor,
                    "kubernetes.gitops.assessed",
                    "kubernetes_gitops_state",
                    expected.id.value,
                    metadata=metadata,
                )
            )
            unit_of_work.commit()
        return report

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized_tenant = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized_tenant.value, token, permission)
        )
        return normalized_tenant, principal
