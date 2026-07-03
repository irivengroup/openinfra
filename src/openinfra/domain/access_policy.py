from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import Code, EntityId, TenantId, ValidationError
from openinfra.domain.security import AuthenticatedPrincipal, Permission, SecurityRole


class AccessPolicyEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class AccessRequestContext:
    tenant_id: TenantId
    permission: Permission
    site_code: str | None = None
    environment: str | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        permission: Permission,
        site_code: str | None = None,
        environment: str | None = None,
    ) -> Self:
        return cls(
            tenant_id=tenant_id,
            permission=permission,
            site_code=cls._normalize_optional_site(site_code),
            environment=cls._normalize_optional_environment(environment),
        )

    @classmethod
    def _normalize_optional_site(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        return Code.from_value(value, "site code").value

    @classmethod
    def _normalize_optional_environment(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,63}", normalized):
            raise ValidationError("environment must use 1 to 64 safe characters")
        return normalized

    def attributes(self) -> dict[str, str | None]:
        return {
            "site_code": self.site_code,
            "environment": self.environment,
        }


@dataclass(frozen=True, slots=True)
class AccessPolicyRule:
    id: EntityId
    tenant_id: TenantId
    name: str
    permission: Permission
    effect: AccessPolicyEffect
    subjects: tuple[str, ...]
    roles: tuple[SecurityRole, ...]
    site_codes: tuple[str, ...]
    environments: tuple[str, ...]
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        permission: Permission,
        effect: str,
        subjects: tuple[str, ...] = ("*",),
        roles: tuple[str, ...] = (),
        site_codes: tuple[str, ...] = (),
        environments: tuple[str, ...] = (),
    ) -> Self:
        normalized_subjects = cls._normalize_subjects(subjects)
        normalized_roles = tuple(SecurityRole.from_value(role) for role in roles)
        if not normalized_subjects and not normalized_roles:
            normalized_subjects = ("*",)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=cls._normalize_name(name),
            permission=permission,
            effect=AccessPolicyEffect(effect.strip().lower()),
            subjects=normalized_subjects,
            roles=normalized_roles,
            site_codes=cls._normalize_site_codes(site_codes),
            environments=cls._normalize_environments(environments),
            active=True,
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        name: str,
        permission: str,
        effect: str,
        subjects: tuple[str, ...],
        roles: tuple[str, ...],
        site_codes: tuple[str, ...],
        environments: tuple[str, ...],
        active: bool,
        created_at: datetime,
    ) -> Self:
        normalized_created_at = (
            created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=UTC)
        )
        return cls(
            id=id,
            tenant_id=tenant_id,
            name=cls._normalize_name(name),
            permission=Permission(permission),
            effect=AccessPolicyEffect(effect),
            subjects=cls._normalize_subjects(subjects),
            roles=tuple(SecurityRole.from_value(role) for role in roles),
            site_codes=cls._normalize_site_codes(site_codes),
            environments=cls._normalize_environments(environments),
            active=bool(active),
            created_at=normalized_created_at.astimezone(UTC),
        )

    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized):
            raise ValidationError("access policy rule name must use 2 to 64 safe characters")
        return normalized

    @classmethod
    def _normalize_subjects(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            item = value.strip().lower()
            if item == "*":
                normalized.append(item)
                continue
            if not re.fullmatch(r"[a-z0-9][a-z0-9_.@:-]{1,126}[a-z0-9]", item):
                raise ValidationError("access policy subject must be '*' or a safe subject")
            normalized.append(item)
        return tuple(sorted(set(normalized)))

    @classmethod
    def _normalize_site_codes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item == "*":
                normalized.append(item)
            else:
                normalized.append(Code.from_value(item, "site code").value)
        return tuple(sorted(set(normalized)))

    @classmethod
    def _normalize_environments(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            item = value.strip().lower()
            if item == "*":
                normalized.append(item)
                continue
            if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,63}", item):
                raise ValidationError("access policy environment must use safe characters")
            normalized.append(item)
        return tuple(sorted(set(normalized)))

    def role_names(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.roles)

    def applies_to_principal(self, principal: AuthenticatedPrincipal) -> bool:
        subject_match = "*" in self.subjects or principal.subject in self.subjects
        principal_roles = {role.name for role in principal.roles}
        role_names = set(self.role_names())
        role_match = bool(role_names.intersection(principal_roles))
        return (
            self.active
            and self.permission in principal.permissions
            and (subject_match or role_match)
        )

    def matches_context(self, context: AccessRequestContext) -> bool:
        if self.permission != context.permission:
            return False
        site_match = self._matches_optional(self.site_codes, context.site_code)
        environment_match = self._matches_optional(self.environments, context.environment)
        return site_match and environment_match

    def _matches_optional(self, allowed: tuple[str, ...], value: str | None) -> bool:
        if not allowed:
            return True
        if "*" in allowed:
            return True
        return value is not None and value in allowed

    def deactivated(self) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            permission=self.permission.value,
            effect=self.effect.value,
            subjects=self.subjects,
            roles=self.role_names(),
            site_codes=self.site_codes,
            environments=self.environments,
            active=False,
            created_at=self.created_at,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "permission": self.permission.value,
            "effect": self.effect.value,
            "subjects": list(self.subjects),
            "roles": list(self.role_names()),
            "site_codes": list(self.site_codes),
            "environments": list(self.environments),
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }
