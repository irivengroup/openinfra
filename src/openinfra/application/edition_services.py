from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.ports import AuditRepository, RuntimeUsageRepository, TransactionManager
from openinfra.domain.common import AuditEvent, TenantId, ValidationError
from openinfra.domain.editions import (
    EditionPolicy,
    EditionPolicyCatalog,
    FeatureCapability,
    FeatureGateDecision,
    OpenInfraEdition,
    QuotaDecision,
    QuotaResource,
)


@dataclass(frozen=True, slots=True)
class CheckFeatureCommand:
    tenant_id: str
    edition: str
    capability: str


@dataclass(frozen=True, slots=True)
class CheckQuotaCommand:
    tenant_id: str
    edition: str
    resource: str
    requested_increment: int = 1


class EditionPolicyService:
    def __init__(self, catalog: EditionPolicyCatalog | None = None) -> None:
        self._catalog = catalog or EditionPolicyCatalog()

    def policy_for(self, edition: str | OpenInfraEdition) -> EditionPolicy:
        return self._catalog.policy_for(edition)

    def list_policies(self) -> tuple[EditionPolicy, ...]:
        return self._catalog.all_policies()

    def check_feature(
        self,
        edition: str | OpenInfraEdition,
        capability: str | FeatureCapability,
    ) -> FeatureGateDecision:
        policy = self.policy_for(edition)
        normalized_capability = FeatureCapability.from_value(capability)
        allowed = policy.supports(normalized_capability)
        return FeatureGateDecision(
            edition=policy.edition,
            capability=normalized_capability,
            allowed=allowed,
            reason="allowed" if allowed else "capability_not_available_for_edition",
        )


class EditionRuntimeGuard:
    def __init__(
        self,
        edition: str | OpenInfraEdition,
        usage_repository: RuntimeUsageRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        policy_service: EditionPolicyService | None = None,
    ) -> None:
        self._edition = OpenInfraEdition.from_value(edition)
        self._usage_repository = usage_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._policy_service = policy_service or EditionPolicyService()

    @property
    def edition(self) -> OpenInfraEdition:
        return self._edition

    @property
    def limited_runtime(self) -> bool:
        return self._edition is not OpenInfraEdition.ENTERPRISE

    def require_feature(
        self,
        tenant_id: TenantId,
        capability: str | FeatureCapability,
        actor: str,
        target_type: str,
        target_id: str,
    ) -> FeatureGateDecision:
        decision = self._policy_service.check_feature(self._edition, capability)
        self._audit_decision(
            tenant_id,
            actor,
            "edition.feature_gate.checked",
            target_type,
            target_id,
            decision.as_dict(),
        )
        if not decision.allowed:
            raise ValidationError(
                f"feature '{decision.capability.value}' is not available for edition "
                f"'{decision.edition.value}'"
            )
        return decision

    def require_quota(
        self,
        tenant_id: TenantId,
        resource: str | QuotaResource,
        increment: int,
        actor: str,
        target_type: str,
        target_id: str,
    ) -> QuotaDecision:
        if increment < 0:
            raise ValidationError("quota increment cannot be negative")
        normalized_resource = QuotaResource.from_value(resource)
        policy = self._policy_service.policy_for(self._edition)
        used = self._usage_repository.count_resource(tenant_id, normalized_resource)
        decision = QuotaDecision(
            edition=policy.edition,
            resource=normalized_resource,
            used=used,
            requested_increment=increment,
            limit=policy.quota_for(normalized_resource),
        )
        self._audit_decision(
            tenant_id, actor, "edition.quota.checked", target_type, target_id, decision.as_dict()
        )
        if not decision.allowed:
            raise ValidationError(
                f"edition '{decision.edition.value}' quota exceeded for "
                f"'{decision.resource.value}': used={decision.used}, "
                f"requested_increment={decision.requested_increment}, limit={decision.limit}"
            )
        return decision

    def check_quota(self, command: CheckQuotaCommand) -> QuotaDecision:
        tenant_id = TenantId.from_value(command.tenant_id)
        edition = OpenInfraEdition.from_value(command.edition)
        resource = QuotaResource.from_value(command.resource)
        if command.requested_increment < 0:
            raise ValidationError("quota increment cannot be negative")
        policy = self._policy_service.policy_for(edition)
        return QuotaDecision(
            edition=policy.edition,
            resource=resource,
            used=self._usage_repository.count_resource(tenant_id, resource),
            requested_increment=command.requested_increment,
            limit=policy.quota_for(resource),
        )

    def _audit_decision(
        self,
        tenant_id: TenantId,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        metadata: dict[str, object],
    ) -> None:
        safe_actor = actor.strip() or "system"
        safe_target_id = target_id.strip() or tenant_id.value
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=safe_actor,
                    action=action,
                    target_type=target_type,
                    target_id=safe_target_id,
                    metadata=metadata,
                )
            )
            unit_of_work.commit()


class EditionQueryService:
    def __init__(
        self,
        usage_repository: RuntimeUsageRepository,
        policy_service: EditionPolicyService | None = None,
    ) -> None:
        self._usage_repository = usage_repository
        self._policy_service = policy_service or EditionPolicyService()

    def feature_decision(self, command: CheckFeatureCommand) -> FeatureGateDecision:
        TenantId.from_value(command.tenant_id)
        return self._policy_service.check_feature(command.edition, command.capability)

    def quota_decision(self, command: CheckQuotaCommand) -> QuotaDecision:
        tenant_id = TenantId.from_value(command.tenant_id)
        edition = OpenInfraEdition.from_value(command.edition)
        resource = QuotaResource.from_value(command.resource)
        if command.requested_increment < 0:
            raise ValidationError("quota increment cannot be negative")
        policy = self._policy_service.policy_for(edition)
        return QuotaDecision(
            edition=policy.edition,
            resource=resource,
            used=self._usage_repository.count_resource(tenant_id, resource),
            requested_increment=command.requested_increment,
            limit=policy.quota_for(resource),
        )

    def policies(self) -> tuple[dict[str, object], ...]:
        return tuple(policy.as_dict() for policy in self._policy_service.list_policies())
