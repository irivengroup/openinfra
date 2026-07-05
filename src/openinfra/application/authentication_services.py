from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    IdentityService,
)
from openinfra.application.ports import AuditRepository, TransactionManager
from openinfra.application.security_services import (
    BootstrapTokenCommand,
    BuiltinRolePolicy,
    SecurityService,
)
from openinfra.domain.authentication import (
    AuthProviderMode,
    ExternalDirectoryConfig,
    ExternalGroupRoleMapping,
)
from openinfra.domain.common import AccessDeniedError, AuditEvent, TenantId, ValidationError
from openinfra.domain.editions import OpenInfraEdition
from openinfra.infrastructure.external_identity import ExternalDirectoryAuthenticator


@dataclass(frozen=True, slots=True)
class AuthProviderPolicyCommand:
    edition: str
    mode: str
    directory_config: ExternalDirectoryConfig | None = None


@dataclass(frozen=True, slots=True)
class ExternalLoginCommand:
    tenant_id: str
    edition: str
    actor: str
    username: str
    password: str
    directory_config: ExternalDirectoryConfig
    mappings: tuple[ExternalGroupRoleMapping, ...]
    ttl_seconds: int | None = 8 * 60 * 60


@dataclass(frozen=True, slots=True)
class ExternalLoginResult:
    tenant_id: str
    subject: str
    provider: str
    token: str
    token_prefix: str
    roles: tuple[str, ...]
    mapped_groups: tuple[str, ...]
    external_group_count: int
    expires_at: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "subject": self.subject,
            "provider": self.provider,
            "token": self.token,
            "token_prefix": self.token_prefix,
            "roles": list(self.roles),
            "mapped_groups": list(self.mapped_groups),
            "external_group_count": self.external_group_count,
            "expires_at": self.expires_at,
        }


class AuthProviderPolicyService:
    def validate(self, command: AuthProviderPolicyCommand) -> dict[str, object]:
        edition = OpenInfraEdition.from_value(command.edition)
        mode = AuthProviderMode.from_value(command.mode)
        if edition == OpenInfraEdition.LITE and mode != AuthProviderMode.STANDARD:
            raise ValidationError("Lite edition supports local standard authentication only")
        if mode == AuthProviderMode.STANDARD:
            if command.directory_config is not None:
                raise ValidationError("standard authentication must not define LDAP/IPA settings")
            return {
                "edition": edition.value,
                "mode": mode.value,
                "external_directory_enabled": False,
                "rbac_authority": "openinfra",
            }
        if command.directory_config is None:
            raise ValidationError("LDAP/IPA authentication requires a directory config")
        if command.directory_config.mode != mode:
            raise ValidationError("authentication mode and directory config mode mismatch")
        return {
            "edition": edition.value,
            "mode": mode.value,
            "external_directory_enabled": True,
            "rbac_authority": "openinfra",
            "directory": command.directory_config.as_safe_dict(),
            "group_mapping_required": True,
            "permissions_source": "openinfra-effective-rbac",
        }


class ExternalAuthenticationService:
    def __init__(
        self,
        authenticator: ExternalDirectoryAuthenticator,
        identity_service: IdentityService,
        security_service: SecurityService,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        policy_service: AuthProviderPolicyService | None = None,
        role_policy: BuiltinRolePolicy | None = None,
    ) -> None:
        self._authenticator = authenticator
        self._identity_service = identity_service
        self._security_service = security_service
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._policy_service = policy_service or AuthProviderPolicyService()
        self._role_policy = role_policy or BuiltinRolePolicy()

    def login(self, command: ExternalLoginCommand) -> ExternalLoginResult:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._policy_service.validate(
            AuthProviderPolicyCommand(
                edition=command.edition,
                mode=command.directory_config.mode.value,
                directory_config=command.directory_config,
            )
        )
        identity = self._authenticator.authenticate(
            command.directory_config,
            command.username,
            command.password,
        )
        mappings = self._matching_mappings(
            tenant_id, identity.provider, identity.external_groups, command.mappings
        )
        if not mappings:
            raise AccessDeniedError("external identity has no OpenInfra RBAC group mapping")
        role_names = self._roles_from_mappings(mappings)
        self._role_policy.assert_roles_supported(role_names)
        admin_token = self._bootstrap_internal_admin_token(tenant_id, command.actor)
        user = self._identity_service.create_user(
            CreateUserCommand(
                tenant_id=tenant_id.value,
                actor="external-auth:" + command.actor,
                admin_token=admin_token,
                username=identity.subject,
                display_name=identity.display_name,
                email=identity.email,
                roles=(),
            )
        )
        for mapping in mappings:
            group_name = mapping.internal_group_name
            self._identity_service.create_group(
                CreateGroupCommand(
                    tenant_id=tenant_id.value,
                    actor="external-auth:" + command.actor,
                    admin_token=admin_token,
                    name=group_name,
                    display_name="External " + mapping.provider.value.upper() + " group",
                    roles=mapping.role_names(),
                )
            )
            self._identity_service.add_user_to_group(
                AddUserToGroupCommand(
                    tenant_id=tenant_id.value,
                    actor="external-auth:" + command.actor,
                    admin_token=admin_token,
                    username=user.username,
                    group_name=group_name,
                )
            )
        token_result = self._security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id=tenant_id.value,
                actor="external-auth:" + command.actor,
                subject=identity.subject,
                roles=role_names,
                ttl_seconds=command.ttl_seconds,
            )
        )
        if token_result.token is None:
            raise ValidationError("external authentication did not receive an issued token")
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=identity.subject,
                    action="auth.external.login",
                    target_type="identity_user",
                    target_id=identity.subject,
                    metadata={
                        "provider": identity.provider.value,
                        "requested_by": command.actor,
                        "mapped_groups": [mapping.internal_group_name for mapping in mappings],
                        "roles": list(role_names),
                        "external_group_count": len(identity.external_groups),
                    },
                )
            )
            unit_of_work.commit()
        return ExternalLoginResult(
            tenant_id=tenant_id.value,
            subject=identity.subject,
            provider=identity.provider.value,
            token=token_result.token,
            token_prefix=token_result.token_prefix,
            roles=token_result.roles,
            mapped_groups=tuple(mapping.internal_group_name for mapping in mappings),
            external_group_count=len(identity.external_groups),
            expires_at=token_result.expires_at,
        )

    def _matching_mappings(
        self,
        tenant_id: TenantId,
        provider: AuthProviderMode,
        external_groups: tuple[str, ...],
        mappings: tuple[ExternalGroupRoleMapping, ...],
    ) -> tuple[ExternalGroupRoleMapping, ...]:
        groups = set(external_groups)
        return tuple(
            mapping
            for mapping in mappings
            if mapping.active
            and mapping.tenant_id == tenant_id
            and mapping.provider == provider
            and mapping.external_group in groups
        )

    def _roles_from_mappings(
        self, mappings: tuple[ExternalGroupRoleMapping, ...]
    ) -> tuple[str, ...]:
        names: set[str] = set()
        for mapping in mappings:
            names.update(mapping.role_names())
        return tuple(sorted(names))

    def _bootstrap_internal_admin_token(self, tenant_id: TenantId, actor: str) -> str:
        result = self._security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id=tenant_id.value,
                actor="external-auth-bootstrap:" + actor,
                subject="external-auth-system",
                roles=("admin",),
                ttl_seconds=300,
            )
        )
        if result.token is None:
            raise ValidationError("external authentication bootstrap token was not returned")
        return result.token
