from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import EntityId, TenantId, ValidationError


class Permission(StrEnum):
    IPAM_ALLOCATE = "ipam.allocate"
    DCIM_LOCATE = "dcim.locate"
    DCIM_WRITE = "dcim.write"
    DCIM_IDENTIFY = "dcim.identify"
    SCHEMA_READ = "database.schema.read"
    SECURITY_ADMIN = "security.admin"
    ACCESS_POLICY_ADMIN = "access.policy.admin"
    AUDIT_READ = "audit.read"
    RSOT_READ = "rsot.read"
    RSOT_WRITE = "rsot.write"
    RSOT_GOVERNANCE_READ = "rsot.governance.read"
    RSOT_GOVERNANCE_WRITE = "rsot.governance.write"
    RSOT_QUALITY_READ = "rsot.quality.read"
    ITAM_READ = "itam.read"
    ITAM_WRITE = "itam.write"
    FLOW_READ = "flow.read"
    FLOW_WRITE = "flow.write"
    CERTIFICATE_READ = "certificate.read"
    CERTIFICATE_WRITE = "certificate.write"
    NETWORK_CONFIG_READ = "network_config.read"
    NETWORK_CONFIG_WRITE = "network_config.write"
    FIELD_READ = "field.read"
    FIELD_WRITE = "field.write"
    FIELD_SYNC = "field.sync"
    FIELD_ADMIN = "field.admin"
    ITRM_READ = "rsot.read"
    ITRM_WRITE = "rsot.write"
    ITRM_GOVERNANCE_READ = "rsot.governance.read"
    ITRM_GOVERNANCE_WRITE = "rsot.governance.write"
    ITRM_QUALITY_READ = "rsot.quality.read"
    RI_READ = "rsot.read"
    RI_WRITE = "rsot.write"
    RI_GOVERNANCE_READ = "rsot.governance.read"
    RI_GOVERNANCE_WRITE = "rsot.governance.write"
    RI_QUALITY_READ = "rsot.quality.read"
    SOT_READ = "rsot.read"
    SOT_WRITE = "rsot.write"
    SOT_GOVERNANCE_READ = "rsot.governance.read"
    SOT_GOVERNANCE_WRITE = "rsot.governance.write"


@dataclass(frozen=True, slots=True)
class SecurityRole:
    name: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized):
            raise ValidationError("security role must use 2 to 64 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class ApiTokenCredential:
    id: EntityId
    tenant_id: TenantId
    subject: str
    token_hash: str
    token_prefix: str
    roles: tuple[SecurityRole, ...]
    active: bool
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    revoked_by: str | None
    last_used_at: datetime | None
    use_count: int

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        subject: str,
        token_hash: str,
        token_prefix: str,
        roles: tuple[str, ...],
        expires_at: datetime | None = None,
    ) -> Self:
        normalized_subject = cls._normalize_subject(subject)
        normalized_hash = cls._normalize_hash(token_hash)
        normalized_prefix = cls._normalize_prefix(token_prefix)
        normalized_roles = tuple(SecurityRole.from_value(role) for role in roles)
        normalized_expires_at = cls._normalize_optional_datetime(expires_at, "expires_at")
        if not normalized_roles:
            raise ValidationError("api token must have at least one role")
        if normalized_expires_at is not None and normalized_expires_at <= datetime.now(UTC):
            raise ValidationError("api token expiration must be in the future")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            subject=normalized_subject,
            token_hash=normalized_hash,
            token_prefix=normalized_prefix,
            roles=normalized_roles,
            active=True,
            created_at=datetime.now(UTC),
            expires_at=normalized_expires_at,
            revoked_at=None,
            revoked_by=None,
            last_used_at=None,
            use_count=0,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        subject: str,
        token_hash: str,
        token_prefix: str,
        roles: tuple[str, ...],
        active: bool,
        created_at: datetime,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
        revoked_by: str | None = None,
        last_used_at: datetime | None = None,
        use_count: int = 0,
    ) -> Self:
        normalized_roles = tuple(SecurityRole.from_value(role) for role in roles)
        if not normalized_roles:
            raise ValidationError("api token must have at least one role")
        return cls(
            id=id,
            tenant_id=tenant_id,
            subject=cls._normalize_subject(subject),
            token_hash=cls._normalize_hash(token_hash),
            token_prefix=cls._normalize_prefix(token_prefix),
            roles=normalized_roles,
            active=bool(active),
            created_at=cls._normalize_required_datetime(created_at, "created_at"),
            expires_at=cls._normalize_optional_datetime(expires_at, "expires_at"),
            revoked_at=cls._normalize_optional_datetime(revoked_at, "revoked_at"),
            revoked_by=cls._normalize_optional_actor(revoked_by),
            last_used_at=cls._normalize_optional_datetime(last_used_at, "last_used_at"),
            use_count=cls._normalize_use_count(use_count),
        )

    @classmethod
    def _normalize_subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.@:-]{1,126}[a-z0-9]", normalized):
            raise ValidationError("api token subject must use 3 to 128 safe characters")
        return normalized

    @classmethod
    def _normalize_hash(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValidationError("api token hash must be a sha256 hex digest")
        return normalized

    @classmethod
    def _normalize_prefix(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,16}", normalized):
            raise ValidationError("api token prefix must use 8 to 16 token-safe characters")
        return normalized

    @classmethod
    def _normalize_required_datetime(cls, value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{field_name} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def _normalize_optional_datetime(
        cls,
        value: datetime | None,
        field_name: str,
    ) -> datetime | None:
        if value is None:
            return None
        return cls._normalize_required_datetime(value, field_name)

    @classmethod
    def _normalize_optional_actor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValidationError("revocation actor cannot be empty")
        return normalized

    @classmethod
    def _normalize_use_count(cls, value: int) -> int:
        normalized = int(value)
        if normalized < 0:
            raise ValidationError("api token use count cannot be negative")
        return normalized

    def role_names(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.roles)

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        current = (now or datetime.now(UTC)).astimezone(UTC)
        return self.expires_at <= current

    def is_revoked(self) -> bool:
        return self.revoked_at is not None or not self.active

    def is_usable(self, now: datetime | None = None) -> bool:
        return self.active and self.revoked_at is None and not self.is_expired(now)

    def revoked(self, actor: str, at: datetime | None = None) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            subject=self.subject,
            token_hash=self.token_hash,
            token_prefix=self.token_prefix,
            roles=self.role_names(),
            active=False,
            created_at=self.created_at,
            expires_at=self.expires_at,
            revoked_at=at or datetime.now(UTC),
            revoked_by=actor,
            last_used_at=self.last_used_at,
            use_count=self.use_count,
        )

    def as_public_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "subject": self.subject,
            "token_prefix": self.token_prefix,
            "roles": list(self.role_names()),
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by": self.revoked_by,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "use_count": self.use_count,
            "expired": self.is_expired(),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    tenant_id: TenantId
    subject: str
    roles: tuple[SecurityRole, ...]
    permissions: frozenset[Permission]

    def require(self, permission: Permission) -> None:
        if permission not in self.permissions:
            raise ValidationError("principal does not carry required permission")

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "subject": self.subject,
            "roles": [role.name for role in self.roles],
            "permissions": sorted(permission.value for permission in self.permissions),
        }
