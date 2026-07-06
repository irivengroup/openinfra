from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from openinfra.application.ports import (
    AuditRepository,
    SourceGovernanceRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, NotFoundError, Pagination, TenantId, ValidationError
from openinfra.domain.security import Permission
from openinfra.domain.source_governance import (
    SourceGovernanceEvaluator,
    SourceGovernanceRule,
    SourceGovernanceRulePage,
)
from openinfra.domain.source_of_truth import SourceObjectKind, SourceSystem


@dataclass(frozen=True, slots=True)
class CreateSourceGovernanceRuleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    object_kind: str | None
    attribute_path: str
    authoritative_source: str
    priority: int = 100
    freshness_seconds: int | None = None
    conflict_strategy: str = "reject"


@dataclass(frozen=True, slots=True)
class ListSourceGovernanceRulesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_inactive: bool = False
    object_kind: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluateSourceGovernanceCommand:
    tenant_id: str
    admin_token: str
    object_kind: str
    incoming_source: str
    existing_attributes_json: str
    incoming_attributes_json: str
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DeactivateSourceGovernanceRuleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str


class SourceGovernanceService:
    def __init__(
        self,
        repository: SourceGovernanceRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        evaluator: SourceGovernanceEvaluator | None = None,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._evaluator = evaluator or SourceGovernanceEvaluator()

    def create_rule(self, command: CreateSourceGovernanceRuleCommand) -> SourceGovernanceRule:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.ITRM_GOVERNANCE_WRITE,
            )
        )
        rule = SourceGovernanceRule.create(
            tenant_id=tenant_id,
            name=command.name,
            object_kind=command.object_kind,
            attribute_path=command.attribute_path,
            authoritative_source=command.authoritative_source,
            priority=command.priority,
            freshness_seconds=command.freshness_seconds,
            conflict_strategy=command.conflict_strategy,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.upsert_rule(rule)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itrm.governance.rule.upsert",
                    target_type="source_governance_rule",
                    target_id=rule.name.value,
                    metadata={
                        "declared_actor": command.actor,
                        "attribute_path": rule.attribute_path.value,
                        "authoritative_source": rule.authoritative_source.value,
                        "object_kind": rule.object_kind.value if rule.object_kind else "*",
                        "conflict_strategy": rule.conflict_strategy.value,
                    },
                )
            )
            unit_of_work.commit()
        return rule

    def list_rules(self, command: ListSourceGovernanceRulesCommand) -> SourceGovernanceRulePage:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.ITRM_GOVERNANCE_READ,
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._repository.list_rules(
                tenant_id,
                pagination,
                include_inactive=command.include_inactive,
                object_kind=command.object_kind,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itrm.governance.rule.list",
                    target_type="source_governance_rule",
                    target_id=tenant_id.value,
                    metadata={"limit": pagination.limit},
                )
            )
            unit_of_work.commit()
        return page

    def evaluate(self, command: EvaluateSourceGovernanceCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.ITRM_GOVERNANCE_READ,
            )
        )
        object_kind = SourceObjectKind(str(command.object_kind).strip().lower())
        incoming_source = SourceSystem.from_value(command.incoming_source)
        existing_attributes = self._attributes_from_json(command.existing_attributes_json)
        incoming_attributes = self._attributes_from_json(command.incoming_attributes_json)
        with self._transaction_manager.begin() as unit_of_work:
            rules = self._repository.find_active_rules_for_kind(tenant_id, object_kind.value)
            evaluation = self._evaluator.evaluate(
                tenant_id=tenant_id,
                object_kind=object_kind,
                incoming_source=incoming_source,
                existing_attributes=existing_attributes,
                incoming_attributes=incoming_attributes,
                rules=rules,
                observed_at=command.observed_at,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itrm.governance.evaluate",
                    target_type="source_governance",
                    target_id=object_kind.value,
                    metadata={
                        "incoming_source": incoming_source.value,
                        "accepted": evaluation.accepted,
                        "conflict_count": len(evaluation.conflicts),
                    },
                )
            )
            unit_of_work.commit()
        return evaluation.as_dict()

    def deactivate_rule(self, command: DeactivateSourceGovernanceRuleCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.ITRM_GOVERNANCE_WRITE,
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            if self._repository.find_rule(tenant_id, command.name) is None:
                raise NotFoundError("source governance rule not found: " + command.name)
            deactivated = self._repository.deactivate_rule(tenant_id, command.name)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itrm.governance.rule.deactivate",
                    target_type="source_governance_rule",
                    target_id=command.name.strip().lower(),
                    metadata={"declared_actor": command.actor, "deactivated": deactivated},
                )
            )
            unit_of_work.commit()
        return {
            "tenant_id": tenant_id.value,
            "name": command.name.strip().lower(),
            "deactivated": deactivated,
        }

    def _attributes_from_json(self, payload: str) -> dict[str, object]:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError("governance attributes must be valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValidationError("governance attributes must be a JSON object")
        return dict(decoded)
