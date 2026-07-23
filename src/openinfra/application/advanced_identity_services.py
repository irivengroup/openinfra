from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.authentication_services import ExternalLoginResult
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    IdentityService,
)
from openinfra.application.ports import AuditRepository, IdentityRepository, TransactionManager
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
    BuiltinRolePolicy,
    RevokeTokenCommand,
    SecurityService,
)
from openinfra.domain.authentication import AuthProviderMode, ExternalGroupRoleMapping
from openinfra.domain.common import AccessDeniedError, AuditEvent, TenantId, ValidationError
from openinfra.domain.editions import OpenInfraEdition
from openinfra.domain.federated_identity import (
    FederatedIdentity,
    FederatedProvider,
    SamlProviderConfig,
    TeamSyncSnapshot,
    TeamSyncSourceConfig,
)
from openinfra.domain.security import Permission
from openinfra.infrastructure.advanced_identity import SamlAssertionValidator, TeamSyncSource


@dataclass(frozen=True, slots=True)
class SamlLoginCommand:
    tenant_id: str
    edition: str
    actor: str
    request_data: dict[str, object]
    provider_config: SamlProviderConfig
    mappings: tuple[ExternalGroupRoleMapping, ...]
    ttl_seconds: int | None = 8 * 60 * 60


@dataclass(frozen=True, slots=True)
class TeamSyncCommand:
    tenant_id: str
    actor: str
    admin_token: str
    source_config: TeamSyncSourceConfig
    snapshot: TeamSyncSnapshot | None = None


class SamlAuthenticationService:
    def __init__(
        self,
        validator: SamlAssertionValidator,
        identity_service: IdentityService,
        security_service: SecurityService,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        role_policy: BuiltinRolePolicy | None = None,
    ) -> None:
        self._validator = validator
        self._identity_service = identity_service
        self._security_service = security_service
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._role_policy = role_policy or BuiltinRolePolicy()

    def login(self, command: SamlLoginCommand) -> ExternalLoginResult:
        edition = OpenInfraEdition.from_value(command.edition)
        if edition is OpenInfraEdition.LITE:
            raise ValidationError("Lite edition supports local standard authentication only")
        tenant_id = TenantId.from_value(command.tenant_id)
        identity = self._validator.validate(command.provider_config, command.request_data)
        if identity.provider is not FederatedProvider.SAML:
            raise AccessDeniedError("SAML validator returned a non-SAML identity")
        mappings = self._matching_mappings(tenant_id, identity, command.mappings)
        if not mappings:
            raise AccessDeniedError("SAML identity has no OpenInfra RBAC group mapping")
        role_names = tuple(sorted({role for mapping in mappings for role in mapping.role_names()}))
        self._role_policy.assert_roles_supported(role_names)
        admin_token = self._bootstrap_internal_admin_token(tenant_id, command.actor)
        try:
            user = self._identity_service.create_user(
                CreateUserCommand(
                    tenant_id=tenant_id.value,
                    actor="saml-auth:" + command.actor,
                    admin_token=admin_token,
                    username=identity.subject,
                    display_name=identity.display_name,
                    email=identity.email,
                    roles=(),
                )
            )
            for mapping in mappings:
                self._identity_service.create_group(
                    CreateGroupCommand(
                        tenant_id=tenant_id.value,
                        actor="saml-auth:" + command.actor,
                        admin_token=admin_token,
                        name=mapping.internal_group_name,
                        display_name="External SAML group",
                        roles=mapping.role_names(),
                    )
                )
                self._identity_service.add_user_to_group(
                    AddUserToGroupCommand(
                        tenant_id=tenant_id.value,
                        actor="saml-auth:" + command.actor,
                        admin_token=admin_token,
                        username=user.username,
                        group_name=mapping.internal_group_name,
                    )
                )
            token_result = self._security_service.bootstrap_token(
                BootstrapTokenCommand(
                    tenant_id=tenant_id.value,
                    actor="saml-auth:" + command.actor,
                    subject=identity.subject,
                    roles=role_names,
                    ttl_seconds=command.ttl_seconds,
                )
            )
            if token_result.token is None:
                raise ValidationError("SAML authentication did not receive an issued token")
            self._audit_login(tenant_id, command.actor, identity, mappings, role_names)
            return ExternalLoginResult(
                tenant_id=tenant_id.value,
                subject=identity.subject,
                provider=FederatedProvider.SAML.value,
                token=token_result.token,
                token_prefix=token_result.token_prefix,
                roles=token_result.roles,
                mapped_groups=tuple(mapping.internal_group_name for mapping in mappings),
                external_group_count=len(identity.external_groups),
                expires_at=token_result.expires_at,
            )
        finally:
            self._security_service.revoke_token(
                RevokeTokenCommand(
                    tenant_id=tenant_id.value,
                    actor="saml-auth-bootstrap-cleanup:" + command.actor,
                    target_token=admin_token,
                    admin_token=admin_token,
                )
            )

    def _matching_mappings(
        self,
        tenant_id: TenantId,
        identity: FederatedIdentity,
        mappings: tuple[ExternalGroupRoleMapping, ...],
    ) -> tuple[ExternalGroupRoleMapping, ...]:
        groups = set(identity.external_groups)
        return tuple(
            mapping
            for mapping in mappings
            if mapping.active
            and mapping.tenant_id == tenant_id
            and mapping.provider is AuthProviderMode.SAML
            and mapping.external_group in groups
        )

    def _bootstrap_internal_admin_token(self, tenant_id: TenantId, actor: str) -> str:
        result = self._security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id=tenant_id.value,
                actor="saml-auth-bootstrap:" + actor,
                subject="saml-auth-system",
                roles=("admin",),
                ttl_seconds=300,
            )
        )
        if result.token is None:
            raise ValidationError("SAML authentication bootstrap token was not returned")
        return result.token

    def _audit_login(
        self,
        tenant_id: TenantId,
        actor: str,
        identity: FederatedIdentity,
        mappings: tuple[ExternalGroupRoleMapping, ...],
        role_names: tuple[str, ...],
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=identity.subject,
                    action="auth.saml.login",
                    target_type="identity_user",
                    target_id=identity.subject,
                    metadata={
                        "requested_by": actor,
                        "mapped_groups": [mapping.internal_group_name for mapping in mappings],
                        "roles": list(role_names),
                        "external_group_count": len(identity.external_groups),
                        "has_session_index": identity.session_index is not None,
                    },
                )
            )
            unit_of_work.commit()


class TeamSyncService:
    def __init__(
        self,
        identity_repository: IdentityRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        sources: dict[FederatedProvider, TeamSyncSource] | None = None,
    ) -> None:
        self._identity_repository = identity_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._sources = dict(sources or {})

    def register_source(self, provider: FederatedProvider, source: TeamSyncSource) -> None:
        self._sources[provider] = source

    def synchronize(self, command: TeamSyncCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        if command.source_config.tenant_id != tenant_id:
            raise ValidationError("team sync command and source tenant mismatch")
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id=tenant_id.value,
                token=command.admin_token,
                required_permission=Permission.SECURITY_ADMIN,
            )
        )
        snapshot = command.snapshot
        if snapshot is None:
            source = self._sources.get(command.source_config.provider)
            if source is None:
                raise ValidationError(
                    "no team sync source registered for " + command.source_config.provider.value
                )
            snapshot = source.fetch(command.source_config)
        if snapshot.tenant_id != tenant_id or snapshot.source_id != command.source_config.source_id:
            raise ValidationError("team sync snapshot does not match source configuration")
        with self._transaction_manager.begin() as unit_of_work:
            result = self._identity_repository.apply_team_sync(
                snapshot,
                command.source_config.deactivate_orphans,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="identity.team_sync.apply",
                    target_type="identity_team_sync_source",
                    target_id=snapshot.source_id,
                    metadata={
                        "requested_by": command.actor,
                        "provider": snapshot.provider.value,
                        "fingerprint": snapshot.fingerprint,
                        **result,
                    },
                )
            )
            unit_of_work.commit()
        return {
            "tenant_id": tenant_id.value,
            "source_id": snapshot.source_id,
            "provider": snapshot.provider.value,
            "captured_at": snapshot.captured_at.isoformat(),
            **result,
        }
