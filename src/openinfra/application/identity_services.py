from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.edition_services import EditionRuntimeGuard
from openinfra.application.ports import AuditRepository, IdentityRepository, TransactionManager
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BuiltinRolePolicy,
    SecurityService,
)
from openinfra.domain.common import AuditEvent, TenantId
from openinfra.domain.editions import QuotaResource
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityUser,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission, SecurityRole


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    tenant_id: str
    actor: str
    admin_token: str
    username: str
    display_name: str
    email: str | None = None
    roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreateGroupCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    display_name: str
    roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AddUserToGroupCommand:
    tenant_id: str
    actor: str
    admin_token: str
    username: str
    group_name: str


@dataclass(frozen=True, slots=True)
class GrantUserRoleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    username: str
    role: str


@dataclass(frozen=True, slots=True)
class GrantGroupRoleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    group_name: str
    role: str


@dataclass(frozen=True, slots=True)
class EffectiveIdentityCommand:
    tenant_id: str
    actor: str
    admin_token: str
    subject: str


class IdentityService:
    def __init__(
        self,
        identity_repository: IdentityRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        edition_guard: EditionRuntimeGuard | None = None,
    ) -> None:
        self._identity_repository = identity_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._role_policy = BuiltinRolePolicy()
        self._edition_guard = edition_guard

    def create_user(self, command: CreateUserCommand) -> IdentityUser:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._require_security_admin(command.tenant_id, command.admin_token)
        self._role_policy.assert_roles_supported(command.roles)
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_quota(
                tenant_id,
                QuotaResource.USER,
                1,
                principal.subject,
                "identity_user",
                command.username,
            )
        user = IdentityUser.create(
            tenant_id=tenant_id,
            username=command.username,
            display_name=command.display_name,
            email=command.email,
            roles=command.roles,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._identity_repository.upsert_user(user)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.user.upsert",
                    target_type="identity_user",
                    target_id=user.username,
                    metadata={
                        "requested_by": command.actor,
                        "roles": list(user.role_names()),
                    },
                )
            )
            unit_of_work.commit()
        return user

    def create_group(self, command: CreateGroupCommand) -> IdentityGroup:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._require_security_admin(command.tenant_id, command.admin_token)
        self._role_policy.assert_roles_supported(command.roles)
        group = IdentityGroup.create(
            tenant_id=tenant_id,
            name=command.name,
            display_name=command.display_name,
            roles=command.roles,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._identity_repository.upsert_group(group)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.group.upsert",
                    target_type="identity_group",
                    target_id=group.name,
                    metadata={
                        "requested_by": command.actor,
                        "roles": list(group.role_names()),
                    },
                )
            )
            unit_of_work.commit()
        return group

    def add_user_to_group(self, command: AddUserToGroupCommand) -> GroupMembership:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._require_security_admin(command.tenant_id, command.admin_token)
        membership = GroupMembership.create(tenant_id, command.username, command.group_name)
        with self._transaction_manager.begin() as unit_of_work:
            self._identity_repository.add_membership(membership)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.group.membership.add",
                    target_type="identity_group",
                    target_id=membership.group_name,
                    metadata={
                        "requested_by": command.actor,
                        "username": membership.username,
                    },
                )
            )
            unit_of_work.commit()
        return membership

    def grant_user_role(self, command: GrantUserRoleCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._require_security_admin(command.tenant_id, command.admin_token)
        self._role_policy.assert_roles_supported((command.role,))
        role = SecurityRole.from_value(command.role)
        with self._transaction_manager.begin() as unit_of_work:
            changed = self._identity_repository.grant_user_role(
                tenant_id,
                command.username,
                role.name,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.user.role.grant",
                    target_type="identity_user",
                    target_id=command.username.strip().lower(),
                    metadata={
                        "requested_by": command.actor,
                        "role": role.name,
                        "changed": changed,
                    },
                )
            )
            unit_of_work.commit()
        return {
            "tenant_id": tenant_id.value,
            "username": command.username.strip().lower(),
            "role": role.name,
            "changed": changed,
        }

    def grant_group_role(self, command: GrantGroupRoleCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._require_security_admin(command.tenant_id, command.admin_token)
        self._role_policy.assert_roles_supported((command.role,))
        role = SecurityRole.from_value(command.role)
        with self._transaction_manager.begin() as unit_of_work:
            changed = self._identity_repository.grant_group_role(
                tenant_id,
                command.group_name,
                role.name,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.group.role.grant",
                    target_type="identity_group",
                    target_id=command.group_name.strip().lower(),
                    metadata={
                        "requested_by": command.actor,
                        "role": role.name,
                        "changed": changed,
                    },
                )
            )
            unit_of_work.commit()
        return {
            "tenant_id": tenant_id.value,
            "group_name": command.group_name.strip().lower(),
            "role": role.name,
            "changed": changed,
        }

    def effective_identity(self, command: EffectiveIdentityCommand) -> EffectiveIdentity:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._require_security_admin(command.tenant_id, command.admin_token)
        with self._transaction_manager.begin() as unit_of_work:
            identity = self._identity_repository.effective_identity_for_subject(
                tenant_id,
                command.subject,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.effective.read",
                    target_type="identity_user",
                    target_id=identity.subject,
                    metadata={"requested_by": command.actor},
                )
            )
            unit_of_work.commit()
        return identity

    def _require_security_admin(self, tenant_id: str, token: str) -> AuthenticatedPrincipal:
        return self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id=tenant_id,
                token=token,
                required_permission=Permission.SECURITY_ADMIN,
            )
        )
