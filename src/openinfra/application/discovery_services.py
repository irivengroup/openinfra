from __future__ import annotations

from dataclasses import dataclass

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
)
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


class DiscoveryCollectorService:
    def __init__(
        self,
        discovery_repository: DiscoveryRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._discovery_repository = discovery_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def register_collector(self, command: RegisterCollectorCommand) -> DiscoveryCollector:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        collector = DiscoveryCollector.register(
            tenant_id=tenant_id,
            name=command.name,
            kind=CollectorKind.from_value(command.kind),
            identity=CollectorIdentity.create(
                command.certificate_fingerprint,
                command.vault_secret_ref,
            ),
            scopes=tuple(DiscoveryScope.from_value(scope) for scope in command.scopes),
            version=command.version,
            registered_by=principal.subject,
            endpoint_url=command.endpoint_url,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_collector(collector)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.collector.registered",
                    target_type="discovery_collector",
                    target_id=collector.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "kind": collector.kind.value,
                        "scopes": [scope.value for scope in collector.scopes],
                        "has_vault_secret_ref": collector.identity.vault_secret_ref is not None,
                    },
                )
            )
            unit_of_work.commit()
        return collector

    def heartbeat(self, command: HeartbeatCollectorCommand) -> DiscoveryCollector:
        tenant_id = TenantId.from_value(command.tenant_id)
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
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        return self._discovery_repository.list_collectors(
            tenant_id,
            pagination,
            command.include_inactive,
        )
