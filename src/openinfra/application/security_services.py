from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar

from openinfra.application.ports import (
    AuditRepository,
    IdentityRepository,
    SecurityRepository,
    SecurityTokenPage,
    TransactionManager,
)
from openinfra.domain.common import (
    AccessDeniedError,
    AuditEvent,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.domain.security import (
    ApiTokenCredential,
    AuthenticatedPrincipal,
    Permission,
    SecurityRole,
)


@dataclass(frozen=True, slots=True)
class BootstrapTokenCommand:
    tenant_id: str
    actor: str
    subject: str
    roles: tuple[str, ...]
    token: str | None = None
    ttl_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class BootstrapTokenResult:
    tenant_id: str
    subject: str
    roles: tuple[str, ...]
    token_prefix: str
    token: str | None
    expires_at: str | None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "tenant_id": self.tenant_id,
            "subject": self.subject,
            "roles": list(self.roles),
            "token_prefix": self.token_prefix,
            "expires_at": self.expires_at,
        }
        if self.token is not None:
            payload["token"] = self.token
        return payload


@dataclass(frozen=True, slots=True)
class AuthenticateTokenCommand:
    tenant_id: str
    token: str
    required_permission: Permission


@dataclass(frozen=True, slots=True)
class RevokeTokenCommand:
    tenant_id: str
    actor: str
    target_token: str
    admin_token: str | None = None


@dataclass(frozen=True, slots=True)
class RotateTokenCommand:
    tenant_id: str
    actor: str
    current_token: str
    subject: str | None = None
    roles: tuple[str, ...] = ()
    token: str | None = None
    ttl_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class ListTokensCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class RevokeTokenResult:
    tenant_id: str
    token_prefix: str
    revoked: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "token_prefix": self.token_prefix,
            "revoked": self.revoked,
        }


class BuiltinRolePolicy:
    _ROLE_PERMISSIONS: ClassVar[dict[str, frozenset[Permission]]] = {
        "admin": frozenset(Permission),
        "ipam:operator": frozenset((Permission.IPAM_ALLOCATE, Permission.SCHEMA_READ)),
        "dcim:operator": frozenset(
            (
                Permission.DCIM_LOCATE,
                Permission.DCIM_WRITE,
                Permission.DCIM_IDENTIFY,
                Permission.SCHEMA_READ,
            )
        ),
        "viewer": frozenset(
            (Permission.SCHEMA_READ, Permission.ITRM_READ, Permission.ITRM_QUALITY_READ)
        ),
        "itrm:reader": frozenset(
            (Permission.ITRM_READ, Permission.ITRM_QUALITY_READ, Permission.SCHEMA_READ)
        ),
        "itrm:operator": frozenset(
            (
                Permission.ITRM_READ,
                Permission.ITRM_WRITE,
                Permission.ITRM_QUALITY_READ,
                Permission.SCHEMA_READ,
            )
        ),
        "itrm:governance-admin": frozenset(
            (
                Permission.ITRM_READ,
                Permission.ITRM_WRITE,
                Permission.ITRM_GOVERNANCE_READ,
                Permission.ITRM_GOVERNANCE_WRITE,
                Permission.ITRM_QUALITY_READ,
                Permission.SCHEMA_READ,
                Permission.AUDIT_READ,
            )
        ),
        "ri:reader": frozenset(
            (Permission.ITRM_READ, Permission.ITRM_QUALITY_READ, Permission.SCHEMA_READ)
        ),
        "ri:operator": frozenset(
            (
                Permission.ITRM_READ,
                Permission.ITRM_WRITE,
                Permission.ITRM_QUALITY_READ,
                Permission.SCHEMA_READ,
            )
        ),
        "ri:governance-admin": frozenset(
            (
                Permission.ITRM_READ,
                Permission.ITRM_WRITE,
                Permission.ITRM_GOVERNANCE_READ,
                Permission.ITRM_GOVERNANCE_WRITE,
                Permission.ITRM_QUALITY_READ,
                Permission.SCHEMA_READ,
                Permission.AUDIT_READ,
            )
        ),
        "security:admin": frozenset(
            (
                Permission.SECURITY_ADMIN,
                Permission.SCHEMA_READ,
                Permission.AUDIT_READ,
            )
        ),
        "access:admin": frozenset((Permission.ACCESS_POLICY_ADMIN, Permission.SCHEMA_READ)),
        "audit:reader": frozenset((Permission.AUDIT_READ, Permission.SCHEMA_READ)),
        "sot:reader": frozenset((Permission.ITRM_READ, Permission.SCHEMA_READ)),
        "sot:operator": frozenset(
            (Permission.ITRM_READ, Permission.ITRM_WRITE, Permission.SCHEMA_READ)
        ),
        "sot:governance-admin": frozenset(
            (
                Permission.ITRM_READ,
                Permission.ITRM_WRITE,
                Permission.ITRM_GOVERNANCE_READ,
                Permission.ITRM_GOVERNANCE_WRITE,
                Permission.ITRM_QUALITY_READ,
                Permission.SCHEMA_READ,
                Permission.AUDIT_READ,
            )
        ),
    }

    def permissions_for(self, roles: tuple[SecurityRole, ...]) -> frozenset[Permission]:
        permissions: set[Permission] = set()
        for role in roles:
            role_permissions = self._ROLE_PERMISSIONS.get(role.name)
            if role_permissions is None:
                raise ValidationError("unsupported security role: " + role.name)
            permissions.update(role_permissions)
        return frozenset(permissions)

    def assert_roles_supported(self, roles: tuple[str, ...]) -> None:
        for role in roles:
            normalized = SecurityRole.from_value(role).name
            if normalized not in self._ROLE_PERMISSIONS:
                raise ValidationError("unsupported security role: " + normalized)


class TokenHasher:
    def digest(self, token: str) -> str:
        normalized = token.strip()
        if len(normalized) < 32:
            raise ValidationError("api token must contain at least 32 characters")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def prefix(self, token: str) -> str:
        normalized = token.strip()
        if len(normalized) < 32:
            raise ValidationError("api token must contain at least 32 characters")
        return normalized[:12]

    def matches(self, token: str, expected_hash: str) -> bool:
        return hmac.compare_digest(self.digest(token), expected_hash)


class TokenGenerator:
    def create(self) -> str:
        return "oi_" + secrets.token_urlsafe(48)


class TokenExpirationPolicy:
    _MIN_TTL_SECONDS = 60
    _MAX_TTL_SECONDS = 366 * 24 * 60 * 60

    def compute(self, ttl_seconds: int | None) -> datetime | None:
        if ttl_seconds is None:
            return None
        normalized = int(ttl_seconds)
        if not self._MIN_TTL_SECONDS <= normalized <= self._MAX_TTL_SECONDS:
            raise ValidationError("api token ttl must be between 60 seconds and 366 days")
        return datetime.now(UTC) + timedelta(seconds=normalized)


class SecurityService:
    def __init__(
        self,
        security_repository: SecurityRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        identity_repository: IdentityRepository | None = None,
        role_policy: BuiltinRolePolicy | None = None,
        hasher: TokenHasher | None = None,
        generator: TokenGenerator | None = None,
        expiration_policy: TokenExpirationPolicy | None = None,
    ) -> None:
        self._security_repository = security_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._identity_repository = identity_repository
        self._role_policy = role_policy or BuiltinRolePolicy()
        self._hasher = hasher or TokenHasher()
        self._generator = generator or TokenGenerator()
        self._expiration_policy = expiration_policy or TokenExpirationPolicy()

    def bootstrap_token(self, command: BootstrapTokenCommand) -> BootstrapTokenResult:
        tenant_id = TenantId.from_value(command.tenant_id)
        roles = command.roles or ("admin",)
        self._role_policy.assert_roles_supported(roles)
        token = command.token.strip() if command.token else self._generator.create()
        credential = ApiTokenCredential.create(
            tenant_id=tenant_id,
            subject=command.subject,
            token_hash=self._hasher.digest(token),
            token_prefix=self._hasher.prefix(token),
            roles=roles,
            expires_at=self._expiration_policy.compute(command.ttl_seconds),
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._security_repository.upsert_token(credential)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="security.token.bootstrap",
                    target_type="api_token",
                    target_id=credential.subject,
                    metadata={
                        "roles": list(credential.role_names()),
                        "token_prefix": credential.token_prefix,
                        "expires_at": (
                            credential.expires_at.isoformat() if credential.expires_at else None
                        ),
                    },
                )
            )
            unit_of_work.commit()
        return self._bootstrap_result(tenant_id, credential, None if command.token else token)

    def authenticate_token(self, command: AuthenticateTokenCommand) -> AuthenticatedPrincipal:
        tenant_id = TenantId.from_value(command.tenant_id)
        token_hash = self._hasher.digest(command.token)
        with self._transaction_manager.begin() as unit_of_work:
            credential = self._security_repository.find_active_token_by_hash(tenant_id, token_hash)
            if credential is None or not self._hasher.matches(command.token, credential.token_hash):
                raise AccessDeniedError("invalid api token")
            if not credential.is_usable():
                raise AccessDeniedError("api token is revoked or expired")
            effective_roles = self._effective_roles_for_credential(tenant_id, credential)
            permissions = self._role_policy.permissions_for(effective_roles)
            if command.required_permission not in permissions:
                raise AccessDeniedError("api token is not allowed to perform this operation")
            self._security_repository.record_token_used(tenant_id, credential.token_hash)
            unit_of_work.commit()
        return AuthenticatedPrincipal(
            tenant_id=tenant_id,
            subject=credential.subject,
            roles=effective_roles,
            permissions=permissions,
        )

    def _effective_roles_for_credential(
        self,
        tenant_id: TenantId,
        credential: ApiTokenCredential,
    ) -> tuple[SecurityRole, ...]:
        role_names = {role.name for role in credential.roles}
        identity_repository = self._identity_repository
        if identity_repository is not None:
            identity = identity_repository.effective_identity_for_subject(
                tenant_id,
                credential.subject,
            )
            if identity.active:
                role_names.update(identity.role_names())
        return tuple(SecurityRole.from_value(name) for name in sorted(role_names))

    def inspect_token(self, tenant_id: str, token: str) -> AuthenticatedPrincipal:
        return self.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id=tenant_id,
                token=token,
                required_permission=Permission.SCHEMA_READ,
            )
        )

    def revoke_token(self, command: RevokeTokenCommand) -> RevokeTokenResult:
        tenant_id = TenantId.from_value(command.tenant_id)
        admin_token = command.admin_token or command.target_token
        principal = self.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, admin_token, Permission.SECURITY_ADMIN)
        )
        target_hash = self._hasher.digest(command.target_token)
        target_prefix = self._hasher.prefix(command.target_token)
        with self._transaction_manager.begin() as unit_of_work:
            revoked = self._security_repository.revoke_token(tenant_id, target_hash, command.actor)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="security.token.revoke",
                    target_type="api_token",
                    target_id=target_prefix,
                    metadata={"revoked": revoked, "requested_by": command.actor},
                )
            )
            unit_of_work.commit()
        return RevokeTokenResult(tenant_id.value, target_prefix, revoked)

    def rotate_token(self, command: RotateTokenCommand) -> BootstrapTokenResult:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.current_token,
                Permission.SECURITY_ADMIN,
            )
        )
        current_hash = self._hasher.digest(command.current_token)
        current_prefix = self._hasher.prefix(command.current_token)
        roles = command.roles or tuple(role.name for role in principal.roles)
        self._role_policy.assert_roles_supported(roles)
        subject = command.subject or principal.subject
        new_token = command.token.strip() if command.token else self._generator.create()
        replacement = ApiTokenCredential.create(
            tenant_id=tenant_id,
            subject=subject,
            token_hash=self._hasher.digest(new_token),
            token_prefix=self._hasher.prefix(new_token),
            roles=roles,
            expires_at=self._expiration_policy.compute(command.ttl_seconds),
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._security_repository.revoke_token(tenant_id, current_hash, command.actor)
            self._security_repository.upsert_token(replacement)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="security.token.rotate",
                    target_type="api_token",
                    target_id=replacement.subject,
                    metadata={
                        "old_token_prefix": current_prefix,
                        "new_token_prefix": replacement.token_prefix,
                        "roles": list(replacement.role_names()),
                    },
                )
            )
            unit_of_work.commit()
        return self._bootstrap_result(tenant_id, replacement, None if command.token else new_token)

    def list_tokens(self, command: ListTokensCommand) -> SecurityTokenPage:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.SECURITY_ADMIN,
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._security_repository.list_tokens(
                tenant_id,
                pagination,
                command.include_inactive,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="security.token.list",
                    target_type="api_token",
                    target_id=tenant_id.value,
                    metadata={
                        "limit": pagination.limit,
                        "include_inactive": command.include_inactive,
                    },
                )
            )
            unit_of_work.commit()
        return page

    def _bootstrap_result(
        self,
        tenant_id: TenantId,
        credential: ApiTokenCredential,
        token: str | None,
    ) -> BootstrapTokenResult:
        return BootstrapTokenResult(
            tenant_id=tenant_id.value,
            subject=credential.subject,
            roles=credential.role_names(),
            token_prefix=credential.token_prefix,
            token=token,
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None,
        )
