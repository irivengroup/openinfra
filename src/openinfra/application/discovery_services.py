from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from openinfra.application.edition_services import EditionRuntimeGuard
from openinfra.application.ports import (
    AuditRepository,
    DiscoveryCollectorPage,
    DiscoveryEvidencePage,
    DiscoveryIntegrationProfilePage,
    DiscoveryProtocolProfilePage,
    DiscoveryReconciliationCasePage,
    DiscoveryRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, EntityId, Pagination, TenantId, ValidationError
from openinfra.domain.discovery import (
    CollectorIdentity,
    CollectorKind,
    DiscoveryCollector,
    DiscoveryEvidence,
    DiscoveryIntegrationProfile,
    DiscoveryJobAuthorization,
    DiscoveryProtocolCredentialProfile,
    DiscoveryReconciliationCase,
    DiscoveryReconciliationStatus,
    DiscoveryScope,
    DiscoverySource,
    EnterpriseAgentBootstrapPlan,
    LocalDiscoveryPlan,
)
from openinfra.domain.editions import FeatureCapability, QuotaResource
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class CreateDiscoveryProtocolProfileCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    protocol: str
    scope: str
    credential_secret_ref: str
    port: int | None = None
    timeout_seconds: int = 30
    max_concurrency: int = 4
    rate_limit_per_minute: int = 120
    retry_count: int = 1


@dataclass(frozen=True, slots=True)
class UpdateDiscoveryProtocolProfileCommand:
    tenant_id: str
    actor: str
    admin_token: str
    profile_id: str
    name: str | None = None
    scope: str | None = None
    credential_secret_ref: str | None = None
    port: int | None = None
    timeout_seconds: int | None = None
    max_concurrency: int | None = None
    rate_limit_per_minute: int | None = None
    retry_count: int | None = None


@dataclass(frozen=True, slots=True)
class GetDiscoveryProtocolProfileCommand:
    tenant_id: str
    admin_token: str
    profile_id: str


@dataclass(frozen=True, slots=True)
class DisableDiscoveryProtocolProfileCommand:
    tenant_id: str
    actor: str
    admin_token: str
    profile_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ListDiscoveryProtocolProfilesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class CreateDiscoveryIntegrationProfileCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    kind: str
    scope: str
    endpoint_url: str | None
    credential_secret_ref: str
    verify_tls: bool = True
    inventory_enabled: bool = True
    max_concurrency: int = 4
    rate_limit_per_minute: int = 120


@dataclass(frozen=True, slots=True)
class UpdateDiscoveryIntegrationProfileCommand:
    tenant_id: str
    actor: str
    admin_token: str
    profile_id: str
    name: str | None = None
    scope: str | None = None
    endpoint_url: str | None = None
    credential_secret_ref: str | None = None
    verify_tls: bool | None = None
    inventory_enabled: bool | None = None
    max_concurrency: int | None = None
    rate_limit_per_minute: int | None = None


@dataclass(frozen=True, slots=True)
class GetDiscoveryIntegrationProfileCommand:
    tenant_id: str
    admin_token: str
    profile_id: str


@dataclass(frozen=True, slots=True)
class DisableDiscoveryIntegrationProfileCommand:
    tenant_id: str
    actor: str
    admin_token: str
    profile_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ListDiscoveryIntegrationProfilesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_inactive: bool = False


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
class BuildEnterpriseAgentBootstrapPlanCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    role: str
    scopes: tuple[str, ...]
    backend_url: str
    certificate_fingerprint: str
    enrollment_secret_ref: str
    agent_version: str
    service_user: str = "openinfra-agent"
    config_path: str = "/etc/openinfra/agent.yaml"
    state_directory: str = "/var/lib/openinfra-agent"
    log_directory: str = "/var/log/openinfra-agent"


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
    protocol_profile_id: str | None = None


@dataclass(frozen=True, slots=True)
class SubmitDiscoveryEvidenceCommand:
    tenant_id: str
    actor: str
    admin_token: str
    object_key: str
    object_kind: str
    source: str
    source_ref: str
    scope: str
    external_id: str
    confidence: float
    payload: dict[str, Any]
    observed_at: str | None = None
    evidence_id: str | None = None


@dataclass(frozen=True, slots=True)
class GetDiscoveryEvidenceCommand:
    tenant_id: str
    admin_token: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class ListDiscoveryEvidenceCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    object_key: str | None = None


@dataclass(frozen=True, slots=True)
class ReconcileDiscoveryEvidenceCommand:
    tenant_id: str
    actor: str
    admin_token: str
    object_key: str
    evidence_ids: tuple[str, ...]
    max_age_seconds: int = 86_400


@dataclass(frozen=True, slots=True)
class GetDiscoveryReconciliationCommand:
    tenant_id: str
    admin_token: str
    case_id: str


@dataclass(frozen=True, slots=True)
class ListDiscoveryReconciliationsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class ResolveDiscoveryReconciliationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    case_id: str
    selected_evidence_by_path: dict[str, str]
    justification: str


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

    def submit_evidence(self, command: SubmitDiscoveryEvidenceCommand) -> DiscoveryEvidence:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_WRITE,
            )
        )
        observed_at = self._parse_optional_datetime(command.observed_at, "observed_at")
        evidence_id = None
        if command.evidence_id is not None:
            evidence_id = EntityId.from_value(command.evidence_id)
        evidence = DiscoveryEvidence.create(
            tenant_id=tenant_id,
            source=DiscoverySource.from_value(command.source),
            external_id=command.external_id,
            confidence=command.confidence,
            payload=command.payload,
            object_key=command.object_key,
            object_kind=command.object_kind,
            scope=command.scope,
            source_ref=command.source_ref,
            observed_at=observed_at,
            evidence_id=evidence_id,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_evidence(evidence)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.evidence.submitted",
                    target_type="discovery_evidence",
                    target_id=evidence.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "object_key": evidence.object_key,
                        "object_kind": evidence.object_kind,
                        "source": evidence.source.value,
                        "source_ref": evidence.source_ref,
                        "scope": evidence.scope.value,
                        "payload_hash": evidence.payload_hash,
                        "confidence": evidence.confidence,
                        "completeness": evidence.completeness,
                        "immutable": True,
                        "payload_audited": False,
                        "rsot_write_executed": False,
                    },
                )
            )
            unit_of_work.commit()
        return evidence

    def get_evidence(self, command: GetDiscoveryEvidenceCommand) -> DiscoveryEvidence:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_READ,
            )
        )
        evidence = self._discovery_repository.get_evidence(tenant_id, command.evidence_id)
        if evidence is None:
            raise ValidationError("discovery evidence is not registered")
        return evidence

    def list_evidence(self, command: ListDiscoveryEvidenceCommand) -> DiscoveryEvidencePage:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_READ,
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        object_key = None if command.object_key is None else command.object_key.strip()
        return self._discovery_repository.list_evidence(tenant_id, pagination, object_key)

    def reconcile_evidence(
        self, command: ReconcileDiscoveryEvidenceCommand
    ) -> DiscoveryReconciliationCase:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_WRITE,
            )
        )
        normalized_ids = tuple(dict.fromkeys(item.strip() for item in command.evidence_ids))
        if len(normalized_ids) < 2:
            raise ValidationError("reconciliation requires at least two distinct evidence ids")
        evidences: list[DiscoveryEvidence] = []
        for evidence_id in normalized_ids:
            evidence = self._discovery_repository.get_evidence(tenant_id, evidence_id)
            if evidence is None:
                raise ValidationError("discovery evidence is not registered: " + evidence_id)
            evidences.append(evidence)
        candidate = DiscoveryReconciliationCase.evaluate(
            tenant_id=tenant_id,
            object_key=command.object_key,
            evidences=tuple(evidences),
            max_age_seconds=command.max_age_seconds,
            evaluated_by=principal.subject,
        )
        existing = self._discovery_repository.find_reconciliation_case_by_signature(
            tenant_id,
            candidate.signature,
        )
        if existing is not None:
            return existing
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_reconciliation_case(candidate)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.reconciliation.evaluated",
                    target_type="discovery_reconciliation_case",
                    target_id=candidate.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "object_key": candidate.object_key,
                        "object_kind": candidate.object_kind,
                        "evidence_count": len(candidate.evidence_ids),
                        "source_count": candidate.source_count,
                        "conflict_count": len(candidate.conflicts),
                        "status": candidate.status.value,
                        "overall_score": candidate.overall_score,
                        "signature": candidate.signature,
                        "rsot_write_executed": False,
                    },
                )
            )
            unit_of_work.commit()
        return candidate

    def get_reconciliation(
        self, command: GetDiscoveryReconciliationCommand
    ) -> DiscoveryReconciliationCase:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_READ,
            )
        )
        case = self._discovery_repository.get_reconciliation_case(tenant_id, command.case_id)
        if case is None:
            raise ValidationError("discovery reconciliation case is not registered")
        return case

    def list_reconciliations(
        self, command: ListDiscoveryReconciliationsCommand
    ) -> DiscoveryReconciliationCasePage:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_READ,
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        status = None
        if command.status is not None:
            status = DiscoveryReconciliationStatus(command.status.strip().lower()).value
        return self._discovery_repository.list_reconciliation_cases(
            tenant_id,
            pagination,
            status,
        )

    def resolve_reconciliation(
        self, command: ResolveDiscoveryReconciliationCommand
    ) -> DiscoveryReconciliationCase:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RSOT_GOVERNANCE_WRITE,
            )
        )
        case = self._discovery_repository.get_reconciliation_case(tenant_id, command.case_id)
        if case is None:
            raise ValidationError("discovery reconciliation case is not registered")
        resolved = case.resolve(
            selected_evidence_by_path=command.selected_evidence_by_path,
            actor=principal.subject,
            justification=command.justification,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_reconciliation_case(resolved)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.reconciliation.resolved",
                    target_type="discovery_reconciliation_case",
                    target_id=resolved.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "justification": resolved.resolution.justification
                        if resolved.resolution is not None
                        else "",
                        "selection_count": len(command.selected_evidence_by_path),
                        "signature": resolved.signature,
                        "status": resolved.status.value,
                        "rsot_write_executed": False,
                    },
                )
            )
            unit_of_work.commit()
        return resolved

    @staticmethod
    def _parse_optional_datetime(value: str | None, label: str) -> datetime | None:
        if value is None or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(label + " must use ISO-8601 syntax") from exc
        if parsed.tzinfo is None:
            raise ValidationError(label + " must include a timezone")
        return parsed

    def create_protocol_profile(
        self, command: CreateDiscoveryProtocolProfileCommand
    ) -> DiscoveryProtocolCredentialProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = DiscoveryProtocolCredentialProfile.create(
            tenant_id=tenant_id,
            name=command.name,
            protocol=command.protocol,
            scope=command.scope,
            credential_secret_ref=command.credential_secret_ref,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            max_concurrency=command.max_concurrency,
            rate_limit_per_minute=command.rate_limit_per_minute,
            retry_count=command.retry_count,
            created_by=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_protocol_profile(profile)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.protocol_profile.created",
                    target_type="discovery_protocol_profile",
                    target_id=profile.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "protocol": profile.protocol.value,
                        "scope": profile.scope.value,
                        "rate_limit_per_minute": profile.rate_limit_per_minute,
                        "max_concurrency": profile.max_concurrency,
                        "credential_reference_only": True,
                    },
                )
            )
            unit_of_work.commit()
        return profile

    def update_protocol_profile(
        self, command: UpdateDiscoveryProtocolProfileCommand
    ) -> DiscoveryProtocolCredentialProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = self._discovery_repository.get_protocol_profile(tenant_id, command.profile_id)
        if profile is None:
            raise ValidationError("discovery protocol profile is not registered")
        updated = profile.update_settings(
            name=command.name,
            scope=command.scope,
            credential_secret_ref=command.credential_secret_ref,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            max_concurrency=command.max_concurrency,
            rate_limit_per_minute=command.rate_limit_per_minute,
            retry_count=command.retry_count,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_protocol_profile(updated)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.protocol_profile.updated",
                    target_type="discovery_protocol_profile",
                    target_id=updated.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "protocol": updated.protocol.value,
                        "scope": updated.scope.value,
                        "rate_limit_per_minute": updated.rate_limit_per_minute,
                        "max_concurrency": updated.max_concurrency,
                        "credential_reference_only": True,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def get_protocol_profile(
        self, command: GetDiscoveryProtocolProfileCommand
    ) -> DiscoveryProtocolCredentialProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = self._discovery_repository.get_protocol_profile(tenant_id, command.profile_id)
        if profile is None:
            raise ValidationError("discovery protocol profile is not registered")
        return profile

    def disable_protocol_profile(
        self, command: DisableDiscoveryProtocolProfileCommand
    ) -> DiscoveryProtocolCredentialProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = self._discovery_repository.get_protocol_profile(tenant_id, command.profile_id)
        if profile is None:
            raise ValidationError("discovery protocol profile is not registered")
        disabled = profile.disable(command.reason)
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_protocol_profile(disabled)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.protocol_profile.disabled",
                    target_type="discovery_protocol_profile",
                    target_id=disabled.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "reason": disabled.disabled_reason,
                        "credential_reference_only": True,
                    },
                )
            )
            unit_of_work.commit()
        return disabled

    def list_protocol_profiles(
        self, command: ListDiscoveryProtocolProfilesCommand
    ) -> DiscoveryProtocolProfilePage:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        return self._discovery_repository.list_protocol_profiles(
            tenant_id,
            pagination,
            command.include_inactive,
        )

    def create_integration_profile(
        self, command: CreateDiscoveryIntegrationProfileCommand
    ) -> DiscoveryIntegrationProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = DiscoveryIntegrationProfile.create(
            tenant_id=tenant_id,
            name=command.name,
            kind=command.kind,
            scope=command.scope,
            endpoint_url=command.endpoint_url,
            credential_secret_ref=command.credential_secret_ref,
            verify_tls=command.verify_tls,
            inventory_enabled=command.inventory_enabled,
            max_concurrency=command.max_concurrency,
            rate_limit_per_minute=command.rate_limit_per_minute,
            created_by=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_integration_profile(profile)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.integration_profile.created",
                    target_type="discovery_integration_profile",
                    target_id=profile.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "kind": profile.kind.value,
                        "scope": profile.scope.value,
                        "connector_family": profile.connector_family,
                        "credential_reference_only": True,
                        "inventory_plan_only": True,
                    },
                )
            )
            unit_of_work.commit()
        return profile

    def update_integration_profile(
        self, command: UpdateDiscoveryIntegrationProfileCommand
    ) -> DiscoveryIntegrationProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = self._discovery_repository.get_integration_profile(tenant_id, command.profile_id)
        if profile is None:
            raise ValidationError("discovery integration profile is not registered")
        updated = profile.update_settings(
            name=command.name,
            scope=command.scope,
            endpoint_url=command.endpoint_url,
            credential_secret_ref=command.credential_secret_ref,
            verify_tls=command.verify_tls,
            inventory_enabled=command.inventory_enabled,
            max_concurrency=command.max_concurrency,
            rate_limit_per_minute=command.rate_limit_per_minute,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_integration_profile(updated)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.integration_profile.updated",
                    target_type="discovery_integration_profile",
                    target_id=updated.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "kind": updated.kind.value,
                        "scope": updated.scope.value,
                        "credential_reference_only": True,
                    },
                )
            )
            unit_of_work.commit()
        return updated

    def get_integration_profile(
        self, command: GetDiscoveryIntegrationProfileCommand
    ) -> DiscoveryIntegrationProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = self._discovery_repository.get_integration_profile(tenant_id, command.profile_id)
        if profile is None:
            raise ValidationError("discovery integration profile is not registered")
        return profile

    def disable_integration_profile(
        self, command: DisableDiscoveryIntegrationProfileCommand
    ) -> DiscoveryIntegrationProfile:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        profile = self._discovery_repository.get_integration_profile(tenant_id, command.profile_id)
        if profile is None:
            raise ValidationError("discovery integration profile is not registered")
        disabled = profile.disable(command.reason)
        with self._transaction_manager.begin() as unit_of_work:
            self._discovery_repository.save_integration_profile(disabled)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.integration_profile.disabled",
                    target_type="discovery_integration_profile",
                    target_id=disabled.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "reason": disabled.disabled_reason,
                        "credential_reference_only": True,
                    },
                )
            )
            unit_of_work.commit()
        return disabled

    def list_integration_profiles(
        self, command: ListDiscoveryIntegrationProfilesCommand
    ) -> DiscoveryIntegrationProfilePage:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        return self._discovery_repository.list_integration_profiles(
            tenant_id,
            pagination,
            command.include_inactive,
        )

    def build_enterprise_agent_bootstrap_plan(
        self, command: BuildEnterpriseAgentBootstrapPlanCommand
    ) -> EnterpriseAgentBootstrapPlan:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value, command.admin_token, Permission.SECURITY_ADMIN
            )
        )
        edition = "enterprise"
        if self._edition_guard is not None:
            edition = self._edition_guard.edition.value
            self._edition_guard.require_feature(
                tenant_id,
                FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                principal.subject,
                "openinfra_agent",
                command.name,
            )
            self._edition_guard.require_quota(
                tenant_id,
                QuotaResource.DISCOVERY_COLLECTOR,
                1,
                principal.subject,
                "openinfra_agent",
                command.name,
            )
        plan = EnterpriseAgentBootstrapPlan.create(
            tenant_id=tenant_id,
            edition=edition,
            name=command.name,
            role=command.role,
            scopes=command.scopes,
            backend_url=command.backend_url,
            certificate_fingerprint=command.certificate_fingerprint,
            enrollment_secret_ref=command.enrollment_secret_ref,
            agent_version=command.agent_version,
            service_user=command.service_user,
            config_path=command.config_path,
            state_directory=command.state_directory,
            log_directory=command.log_directory,
            created_by=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="discovery.agent.bootstrap_plan_built",
                    target_type="openinfra_agent_bootstrap_plan",
                    target_id=plan.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "edition": plan.edition,
                        "role": plan.role.value,
                        "scopes": [scope.value for scope in plan.scopes],
                        "backend_url": plan.backend_url,
                        "mtls_required": plan.mtls_required,
                        "publishes_results_via_api": plan.publishes_results_via_api,
                        "install_executed": plan.install_executed,
                        "secrets_materialized": plan.secrets_materialized,
                    },
                )
            )
            unit_of_work.commit()
        return plan

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
        protocol_profile_id = None
        scope = command.scope
        protocol = command.protocol
        credential_secret_ref = command.credential_secret_ref
        max_concurrency = command.max_concurrency
        rate_limit_per_minute = command.rate_limit_per_minute
        if command.protocol_profile_id:
            protocol_profile = self._discovery_repository.get_protocol_profile(
                tenant_id,
                command.protocol_profile_id,
            )
            if protocol_profile is None:
                raise ValidationError("discovery protocol profile is not registered")
            if protocol_profile.status.value != "active":
                raise ValidationError("discovery protocol profile must be active")
            expected_scope = DiscoveryScope.from_value(command.scope)
            expected_protocol = type(protocol_profile.protocol).from_value(command.protocol)
            if expected_scope != protocol_profile.scope:
                raise ValidationError("local discovery scope must match selected protocol profile")
            if expected_protocol != protocol_profile.protocol:
                raise ValidationError(
                    "local discovery protocol must match selected protocol profile"
                )
            protocol_profile_id = protocol_profile.id.value
            scope = protocol_profile.scope.value
            protocol = protocol_profile.protocol.value
            credential_secret_ref = protocol_profile.credential_secret_ref
            max_concurrency = protocol_profile.max_concurrency
            rate_limit_per_minute = protocol_profile.rate_limit_per_minute
        plan = LocalDiscoveryPlan.create(
            tenant_id=tenant_id,
            edition=edition,
            name=command.name,
            scope=scope,
            protocol=protocol,
            targets=command.targets,
            credential_secret_ref=credential_secret_ref,
            max_concurrency=max_concurrency,
            rate_limit_per_minute=rate_limit_per_minute,
            created_by=principal.subject,
            protocol_profile_id=protocol_profile_id,
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
