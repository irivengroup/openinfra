from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.edition_services import EditionRuntimeGuard
from openinfra.application.ports import (
    AuditRepository,
    DiscoveryCollectorPage,
    DiscoveryRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, Pagination, TenantId, ValidationError
from openinfra.domain.discovery import (
    CollectorIdentity,
    CollectorKind,
    DiscoveryCollector,
    DiscoveryJobAuthorization,
    DiscoveryScope,
    LocalDiscoveryPlan,
)
from openinfra.domain.editions import FeatureCapability, QuotaResource
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class RegisterCollectorCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    kind: str
    certificate_fingerprint: str
    scopes: tuple[str, ...]
    version: str
    vault_secret_ref: str | None = None
    endpoint_url: str | None = None


@dataclass(frozen=True, slots=True)
class EnrollDiscoveryProxyCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    kind: str
    certificate_fingerprint: str
    scopes: tuple[str, ...]
    version: str
    endpoint_url: str
    vault_secret_ref: str | None = None


@dataclass(frozen=True, slots=True)
class HeartbeatCollectorCommand:
    tenant_id: str
    collector_id: str
    certificate_fingerprint: str
    version: str
    status: str = "ok"


@dataclass(frozen=True, slots=True)
class AuthorizeDiscoveryJobCommand:
    tenant_id: str
    collector_id: str
    certificate_fingerprint: str
    requested_scope: str
    job_type: str
    target: str


@dataclass(frozen=True, slots=True)
class DisableCollectorCommand:
    tenant_id: str
    actor: str
    admin_token: str
    collector_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ListCollectorsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class BuildLocalDiscoveryPlanCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    scope: str
    protocol: str
    targets: tuple[str, ...]
    credential_secret_ref: str
    max_concurrency: int = 4
    rate_limit_per_minute: int = 120


class DiscoveryCollectorService:
    def __init__(
        self,
        discovery_repository: DiscoveryRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        edition_guard: EditionRuntimeGuard | None = None,
    ) -> None:
        self._discovery_repository = discovery_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._edition_guard = edition_guard

    def build_local_discovery_plan(
        self, command: BuildLocalDiscoveryPlanCommand
    ) -> LocalDiscoveryPlan:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        edition = "enterprise"
        if self._edition_guard is not None:
            edition = self._edition_guard.edition.value
        plan = LocalDiscoveryPlan.create(
            tenant_id=tenant_id,
            edition=edition,
            name=command.name,
            scope=command.scope,
            protocol=command.protocol,
            targets=command.targets,
            credential_secret_ref=command.credential_secret_ref,
            max_concurrency=command.max_concurrency,
            rate_limit_per_minute=command.rate_limit_per_minute,
            created_by=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.local.plan_built",
                    target_type="local_discovery_plan",
                    target_id=plan.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "edition": plan.edition,
                        "scope": plan.scope.value,
                        "protocol": plan.protocol.value,
                        "targets_count": len(plan.jobs),
                        "dry_run": plan.dry_run,
                        "agent_required": plan.agent_required,
                        "network_scan_executed": plan.network_scan_executed,
                        "rsot_write_enabled": plan.rsot_write_enabled,
                    },
                )
            )
            unit_of_work.commit()
        return plan

    def register_collector(self, command: RegisterCollectorCommand) -> DiscoveryCollector:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                principal.subject,
                "discovery_collector",
                command.name,
            )
            self._edition_guard.require_quota(
                tenant_id,
                QuotaResource.DISCOVERY_COLLECTOR,
                1,
                principal.subject,
                "discovery_collector",
                command.name,
            )
        return self._persist_collector(
            tenant_id=tenant_id,
            actor=principal.subject,
            declared_actor=command.actor,
            name=command.name,
            kind=CollectorKind.from_value(command.kind),
            certificate_fingerprint=command.certificate_fingerprint,
            scopes=command.scopes,
            version=command.version,
            vault_secret_ref=command.vault_secret_ref,
            endpoint_url=command.endpoint_url,
            audit_action="discovery.collector.registered",
        )

    def enroll_proxy(self, command: EnrollDiscoveryProxyCommand) -> DiscoveryCollector:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        kind = CollectorKind.from_value(command.kind)
        if not kind.is_proxy:
            raise ValidationError(
                "proxy enrollment kind must be site-proxy, network-proxy or datacenter-proxy"
            )
        if not command.endpoint_url.strip():
            raise ValidationError("proxy enrollment endpoint URL is mandatory")
        if self._edition_guard is not None:
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                principal.subject,
                "discovery_proxy",
                command.name,
            )
            self._edition_guard.require_quota(
                tenant_id,
                QuotaResource.DISCOVERY_COLLECTOR,
                1,
                principal.subject,
                "discovery_proxy",
                command.name,
            )
        return self._persist_collector(
            tenant_id=tenant_id,
            actor=principal.subject,
            declared_actor=command.actor,
            name=command.name,
            kind=kind,
            certificate_fingerprint=command.certificate_fingerprint,
            scopes=command.scopes,
            version=command.version,
            vault_secret_ref=command.vault_secret_ref,
            endpoint_url=command.endpoint_url,
            audit_action="discovery.proxy.enrolled",
        )

    def _persist_collector(
        self,
        *,
        tenant_id: TenantId,
        actor: str,
        declared_actor: str,
        name: str,
        kind: CollectorKind,
        certificate_fingerprint: str,
        scopes: tuple[str, ...],
        version: str,
        vault_secret_ref: str | None,
        endpoint_url: str | None,
        audit_action: str,
    ) -> DiscoveryCollector:
        collector = DiscoveryCollector.register(
            tenant_id=tenant_id,
            name=name,
            kind=kind,
            identity=CollectorIdentity.create(certificate_fingerprint, vault_secret_ref),
            scopes=tuple(DiscoveryScope.from_value(scope) for scope in scopes),
            version=version,
            registered_by=actor,
            endpoint_url=endpoint_url,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_collector(collector)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action=audit_action,
                    target_type="discovery_collector",
                    target_id=collector.id.value,
                    metadata={
                        "declared_actor": declared_actor,
                        "kind": collector.kind.value,
                        "scopes": [scope.value for scope in collector.scopes],
                        "has_vault_secret_ref": collector.identity.vault_secret_ref is not None,
                        "proxy_enrollment": collector.kind.is_proxy,
                    },
                )
            )
            unit_of_work.commit()
        return collector

    def heartbeat(self, command: HeartbeatCollectorCommand) -> DiscoveryCollector:
        tenant_id = TenantId.from_value(command.tenant_id)
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                "collector:" + command.collector_id.strip(),
                "discovery_collector",
                command.collector_id,
            )
        collector = self._discovery_repository.get_collector(tenant_id, command.collector_id)
        if collector is None:
            raise ValidationError("collector is not registered")
        refreshed = collector.record_heartbeat(
            certificate_fingerprint=command.certificate_fingerprint,
            version=command.version,
            status=command.status,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_collector(refreshed)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor="collector:" + refreshed.id.value,
                    action="discovery.collector.heartbeat",
                    target_type="discovery_collector",
                    target_id=refreshed.id.value,
                    metadata={
                        "status": refreshed.last_heartbeat_status,
                        "version": refreshed.last_seen_version,
                    },
                )
            )
            unit_of_work.commit()
        return refreshed

    def authorize_job(self, command: AuthorizeDiscoveryJobCommand) -> DiscoveryJobAuthorization:
        tenant_id = TenantId.from_value(command.tenant_id)
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                "collector:" + command.collector_id.strip(),
                "discovery_job",
                command.collector_id,
            )
        collector = self._discovery_repository.get_collector(tenant_id, command.collector_id)
        decision = DiscoveryJobAuthorization.decide(
            tenant_id=tenant_id,
            collector=collector,
            collector_id=command.collector_id,
            certificate_fingerprint=command.certificate_fingerprint,
            requested_scope=command.requested_scope,
            job_type=command.job_type,
            target=command.target,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor="collector:" + command.collector_id.strip(),
                    action=(
                        "discovery.job.authorized"
                        if decision.authorized
                        else "discovery.job.rejected"
                    ),
                    target_type="discovery_job",
                    target_id=decision.collector_id.value,
                    metadata=decision.as_dict(),
                )
            )
            unit_of_work.commit()
        return decision

    def disable_collector(self, command: DisableCollectorCommand) -> DiscoveryCollector:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                principal.subject,
                "discovery_collector",
                command.collector_id,
            )
        collector = self._discovery_repository.get_collector(tenant_id, command.collector_id)
        if collector is None:
            raise ValidationError("collector is not registered")
        disabled = collector.disable(command.reason)
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_collector(disabled)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.collector.disabled",
                    target_type="discovery_collector",
                    target_id=disabled.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "reason": disabled.disabled_reason,
                    },
                )
            )
            unit_of_work.commit()
        return disabled

    def list_collectors(self, command: ListCollectorsCommand) -> DiscoveryCollectorPage:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                principal.subject,
                "discovery_collector",
                tenant_id.value,
            )
        pagination = Pagination.from_values(command.limit, command.cursor)
        return self._discovery_repository.list_collectors(
            tenant_id,
            pagination,
            command.include_inactive,
        )
