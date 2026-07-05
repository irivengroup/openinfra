from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.security import SecurityRole


@dataclass(frozen=True, slots=True)
class IdentityUser:
    id: EntityId
    tenant_id: TenantId
    username: str
    display_name: str
    email: str | None
    roles: tuple[SecurityRole, ...]
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        username: str,
        display_name: str,
        email: str | None,
        roles: tuple[str, ...] = (),
    ) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            username=IdentitySubject.normalize(username),
            display_name=IdentityDisplayName.normalize(display_name),
            email=IdentityEmail.normalize_optional(email),
            roles=IdentityRoleSet.from_names(roles),
            active=True,
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        username: str,
        display_name: str,
        email: str | None,
        roles: tuple[str, ...],
        active: bool,
        created_at: datetime,
    ) -> Self:
        return cls(
            id=id,
            tenant_id=tenant_id,
            username=IdentitySubject.normalize(username),
            display_name=IdentityDisplayName.normalize(display_name),
            email=IdentityEmail.normalize_optional(email),
            roles=IdentityRoleSet.from_names(roles),
            active=bool(active),
            created_at=IdentityTimestamp.normalize(created_at, "created_at"),
        )

    def role_names(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.roles)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "roles": list(self.role_names()),
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class IdentityGroup:
    id: EntityId
    tenant_id: TenantId
    name: str
    display_name: str
    roles: tuple[SecurityRole, ...]
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        display_name: str,
        roles: tuple[str, ...] = (),
    ) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=IdentityGroupName.normalize(name),
            display_name=IdentityDisplayName.normalize(display_name),
            roles=IdentityRoleSet.from_names(roles),
            active=True,
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        name: str,
        display_name: str,
        roles: tuple[str, ...],
        active: bool,
        created_at: datetime,
    ) -> Self:
        return cls(
            id=id,
            tenant_id=tenant_id,
            name=IdentityGroupName.normalize(name),
            display_name=IdentityDisplayName.normalize(display_name),
            roles=IdentityRoleSet.from_names(roles),
            active=bool(active),
            created_at=IdentityTimestamp.normalize(created_at, "created_at"),
        )

    def role_names(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.roles)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "display_name": self.display_name,
            "roles": list(self.role_names()),
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class GroupMembership:
    tenant_id: TenantId
    username: str
    group_name: str
    created_at: datetime

    @classmethod
    def create(cls, tenant_id: TenantId, username: str, group_name: str) -> Self:
        return cls(
            tenant_id=tenant_id,
            username=IdentitySubject.normalize(username),
            group_name=IdentityGroupName.normalize(group_name),
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        tenant_id: TenantId,
        username: str,
        group_name: str,
        created_at: datetime,
    ) -> Self:
        return cls(
            tenant_id=tenant_id,
            username=IdentitySubject.normalize(username),
            group_name=IdentityGroupName.normalize(group_name),
            created_at=IdentityTimestamp.normalize(created_at, "created_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "username": self.username,
            "group_name": self.group_name,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class EffectiveIdentity:
    tenant_id: TenantId
    subject: str
    active: bool
    display_name: str | None
    email: str | None
    direct_roles: tuple[SecurityRole, ...]
    group_roles: tuple[SecurityRole, ...]
    groups: tuple[str, ...]

    @classmethod
    def empty(cls, tenant_id: TenantId, subject: str) -> Self:
        return cls(
            tenant_id=tenant_id,
            subject=IdentitySubject.normalize(subject),
            active=False,
            display_name=None,
            email=None,
            direct_roles=(),
            group_roles=(),
            groups=(),
        )

    @classmethod
    def from_parts(
        cls,
        user: IdentityUser,
        group_names: tuple[str, ...],
        group_roles: tuple[str, ...],
    ) -> Self:
        return cls(
            tenant_id=user.tenant_id,
            subject=user.username,
            active=user.active,
            display_name=user.display_name,
            email=user.email,
            direct_roles=user.roles,
            group_roles=IdentityRoleSet.from_names(group_roles),
            groups=tuple(sorted({IdentityGroupName.normalize(name) for name in group_names})),
        )

    @property
    def exists(self) -> bool:
        return (
            self.active
            or self.display_name is not None
            or self.email is not None
            or bool(self.direct_roles)
            or bool(self.group_roles)
            or bool(self.groups)
        )

    def role_names(self) -> tuple[str, ...]:
        return IdentityRoleSet.unique_names((*self.direct_roles, *self.group_roles))

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "subject": self.subject,
            "active": self.active,
            "display_name": self.display_name,
            "email": self.email,
            "direct_roles": [role.name for role in self.direct_roles],
            "group_roles": [role.name for role in self.group_roles],
            "groups": list(self.groups),
            "effective_roles": list(self.role_names()),
        }


class IdentitySubject:
    @classmethod
    def normalize(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.@:-]{1,126}[a-z0-9]", normalized):
            raise ValidationError("identity subject must use 3 to 128 safe characters")
        return normalized


class IdentityGroupName:
    @classmethod
    def normalize(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized):
            raise ValidationError("identity group must use 2 to 64 safe characters")
        return normalized


class IdentityDisplayName:
    @classmethod
    def normalize(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 255:
            raise ValidationError("identity display name must contain 1 to 255 characters")
        return normalized


class IdentityEmail:
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not re.fullmatch(r"[a-z0-9._%+-]{1,128}@[a-z0-9.-]{1,190}\.[a-z]{2,24}", normalized):
            raise ValidationError("identity email is invalid")
        return normalized


class IdentityTimestamp:
    @classmethod
    def normalize(cls, value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{field_name} must be timezone-aware")
        return value.astimezone(UTC)


class IdentityRoleSet:
    @classmethod
    def from_names(cls, roles: tuple[str, ...]) -> tuple[SecurityRole, ...]:
        names = tuple(dict.fromkeys(SecurityRole.from_value(role).name for role in roles))
        return tuple(SecurityRole.from_value(name) for name in names)

    @classmethod
    def unique_names(cls, roles: tuple[SecurityRole, ...]) -> tuple[str, ...]:
        return tuple(sorted({role.name for role in roles}))
