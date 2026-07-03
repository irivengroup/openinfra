from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.ports import (
    AccessPolicyRepository,
    AccessPolicyRulePage,
    AuditRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.access_policy import (
    AccessPolicyEffect,
    AccessPolicyRule,
    AccessRequestContext,
)
from openinfra.domain.common import AccessDeniedError, AuditEvent, Pagination, TenantId
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class CreateAccessPolicyRuleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    permission: str
    effect: str
    subjects: tuple[str, ...] = ("*",)
    roles: tuple[str, ...] = ()
    site_codes: tuple[str, ...] = ()
    environments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ListAccessPolicyRulesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class DeactivateAccessPolicyRuleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str


@dataclass(frozen=True, slots=True)
class EvaluateAccessPolicyCommand:
    tenant_id: str
    token: str
    permission: str
    site_code: str | None = None
    environment: str | None = None


class AccessPolicyService:
    def __init__(
        self,
        access_policy_repository: AccessPolicyRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._access_policy_repository = access_policy_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def create_rule(self, command: CreateAccessPolicyRuleCommand) -> AccessPolicyRule:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._authenticate_admin(command.tenant_id, command.admin_token)
        rule = AccessPolicyRule.create(
            tenant_id=tenant_id,
            name=command.name,
            permission=Permission(command.permission),
            effect=command.effect,
            subjects=command.subjects,
            roles=command.roles,
            site_codes=command.site_codes,
            environments=command.environments,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._access_policy_repository.upsert_rule(rule)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="access.policy.rule.upsert",
                    target_type="access_policy_rule",
                    target_id=rule.name,
                    metadata={
                        "requested_by": command.actor,
                        "permission": rule.permission.value,
                        "effect": rule.effect.value,
                        "subjects": list(rule.subjects),
                        "roles": list(rule.role_names()),
                        "site_codes": list(rule.site_codes),
                        "environments": list(rule.environments),
                    },
                )
            )
            unit_of_work.commit()
        return rule

    def list_rules(self, command: ListAccessPolicyRulesCommand) -> AccessPolicyRulePage:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._authenticate_admin(command.tenant_id, command.admin_token)
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._access_policy_repository.list_rules(
                tenant_id,
                pagination,
                command.include_inactive,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="access.policy.rule.list",
                    target_type="access_policy_rule",
                    target_id=tenant_id.value,
                    metadata={
                        "limit": pagination.limit,
                        "include_inactive": command.include_inactive,
                    },
                )
            )
            unit_of_work.commit()
        return page

    def deactivate_rule(self, command: DeactivateAccessPolicyRuleCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._authenticate_admin(command.tenant_id, command.admin_token)
        rule_name = AccessPolicyRule.create(
            tenant_id,
            command.name,
            Permission.SCHEMA_READ,
            AccessPolicyEffect.ALLOW.value,
        ).name
        with self._transaction_manager.begin() as unit_of_work:
            changed = self._access_policy_repository.deactivate_rule(tenant_id, rule_name)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="access.policy.rule.deactivate",
                    target_type="access_policy_rule",
                    target_id=rule_name,
                    metadata={"requested_by": command.actor, "changed": changed},
                )
            )
            unit_of_work.commit()
        return {"tenant_id": tenant_id.value, "name": rule_name, "deactivated": changed}

    def evaluate(self, command: EvaluateAccessPolicyCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        permission = Permission(command.permission)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.token, permission)
        )
        context = AccessRequestContext.create(
            tenant_id,
            permission,
            command.site_code,
            command.environment,
        )
        allowed = self.is_allowed(principal, context)
        return {
            "tenant_id": tenant_id.value,
            "subject": principal.subject,
            "permission": permission.value,
            "allowed": allowed,
            "context": context.attributes(),
        }

    def authorize(self, principal: AuthenticatedPrincipal, context: AccessRequestContext) -> None:
        if not self.is_allowed(principal, context):
            raise AccessDeniedError("access policy denies this operation for the requested context")

    def is_allowed(self, principal: AuthenticatedPrincipal, context: AccessRequestContext) -> bool:
        with self._transaction_manager.begin() as unit_of_work:
            rules = self._access_policy_repository.find_active_rules_for_permission(
                context.tenant_id,
                context.permission,
            )
            unit_of_work.commit()
        applicable = tuple(rule for rule in rules if rule.applies_to_principal(principal))
        if not applicable:
            return True
        context_matches = tuple(rule for rule in applicable if rule.matches_context(context))
        if any(rule.effect == AccessPolicyEffect.DENY for rule in context_matches):
            return False
        return bool(any(rule.effect == AccessPolicyEffect.ALLOW for rule in context_matches))

    def _authenticate_admin(self, tenant_id: str, token: str) -> AuthenticatedPrincipal:
        return self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id=tenant_id,
                token=token,
                required_permission=Permission.ACCESS_POLICY_ADMIN,
            )
        )
