from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Self
from urllib.parse import urlparse

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.identity import IdentitySubject
from openinfra.domain.security import SecurityRole


class AuthProviderMode(StrEnum):
    STANDARD = "standard"
    LDAP = "ldap"
    IPA = "ipa"
    SAML = "saml"
    OAUTH = "oauth"
    AUTH_PROXY = "auth_proxy"
    OKTA = "okta"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValidationError("unsupported authentication mode: " + normalized)


@dataclass(frozen=True, slots=True)
class ExternalDirectoryConfig:
    mode: AuthProviderMode
    url: str
    base_dn: str
    user_filter: str
    group_filter: str
    bind_dn_ref: str | None
    bind_password_ref: str | None
    ca_cert_ref: str | None
    tls_required: bool
    nested_groups: bool
    cache_ttl_seconds: int
    user_base_dn: str | None = None
    group_base_dn: str | None = None
    username_attribute: str = "uid"
    display_name_attribute: str = "displayName"
    email_attribute: str = "mail"
    group_name_attribute: str = "cn"
    group_member_attribute: str = "member"
    connect_timeout_seconds: int = 5
    operation_timeout_seconds: int = 15
    page_size: int = 500
    size_limit: int = 5000
    follow_referrals: bool = False
    start_tls: bool = False
    nested_group_depth: int = 5

    @classmethod
    def create(
        cls,
        mode: str,
        url: str,
        base_dn: str,
        user_filter: str,
        group_filter: str,
        bind_dn_ref: str | None = None,
        bind_password_ref: str | None = None,
        ca_cert_ref: str | None = None,
        tls_required: bool = True,
        nested_groups: bool = True,
        cache_ttl_seconds: int = 300,
        user_base_dn: str | None = None,
        group_base_dn: str | None = None,
        username_attribute: str = "uid",
        display_name_attribute: str = "displayName",
        email_attribute: str = "mail",
        group_name_attribute: str = "cn",
        group_member_attribute: str = "member",
        connect_timeout_seconds: int = 5,
        operation_timeout_seconds: int = 15,
        page_size: int = 500,
        size_limit: int = 5000,
        follow_referrals: bool = False,
        start_tls: bool = False,
        nested_group_depth: int = 5,
    ) -> Self:
        normalized_mode = AuthProviderMode.from_value(mode)
        if normalized_mode not in {AuthProviderMode.LDAP, AuthProviderMode.IPA}:
            raise ValidationError("external directory config requires ldap or ipa mode")
        normalized_url = cls._normalize_url(url, start_tls=bool(start_tls))
        normalized_base = DirectoryName.normalize(base_dn, "base_dn")
        normalized_user_filter = DirectoryFilter.normalize(user_filter, "user_filter")
        normalized_group_filter = DirectoryFilter.normalize(group_filter, "group_filter")
        normalized_bind_dn_ref = SecretReference.normalize_optional(bind_dn_ref, "bind_dn_ref")
        normalized_bind_password_ref = SecretReference.normalize_optional(
            bind_password_ref,
            "bind_password_ref",
        )
        if (normalized_bind_dn_ref is None) != (normalized_bind_password_ref is None):
            raise ValidationError("bind_dn_ref and bind_password_ref must be provided together")
        ttl = int(cache_ttl_seconds)
        if not 30 <= ttl <= 3600:
            raise ValidationError("cache_ttl_seconds must be between 30 and 3600")
        if not tls_required:
            raise ValidationError("LDAP/IPA TLS validation is mandatory")
        normalized_user_base = (
            DirectoryName.normalize(user_base_dn, "user_base_dn")
            if user_base_dn is not None and user_base_dn.strip()
            else normalized_base
        )
        normalized_group_base = (
            DirectoryName.normalize(group_base_dn, "group_base_dn")
            if group_base_dn is not None and group_base_dn.strip()
            else normalized_base
        )
        attributes = {
            "username_attribute": cls._normalize_attribute(username_attribute),
            "display_name_attribute": cls._normalize_attribute(display_name_attribute),
            "email_attribute": cls._normalize_attribute(email_attribute),
            "group_name_attribute": cls._normalize_attribute(group_name_attribute),
            "group_member_attribute": cls._normalize_attribute(group_member_attribute),
        }
        connect_timeout = int(connect_timeout_seconds)
        operation_timeout = int(operation_timeout_seconds)
        normalized_page_size = int(page_size)
        normalized_size_limit = int(size_limit)
        normalized_depth = int(nested_group_depth)
        if not 1 <= connect_timeout <= 60:
            raise ValidationError("connect_timeout_seconds must be between 1 and 60")
        if not 1 <= operation_timeout <= 120:
            raise ValidationError("operation_timeout_seconds must be between 1 and 120")
        if not 1 <= normalized_page_size <= 1000:
            raise ValidationError("page_size must be between 1 and 1000")
        if not 1 <= normalized_size_limit <= 100000:
            raise ValidationError("size_limit must be between 1 and 100000")
        if not 1 <= normalized_depth <= 20:
            raise ValidationError("nested_group_depth must be between 1 and 20")
        return cls(
            mode=normalized_mode,
            url=normalized_url,
            base_dn=normalized_base,
            user_filter=normalized_user_filter,
            group_filter=normalized_group_filter,
            bind_dn_ref=normalized_bind_dn_ref,
            bind_password_ref=normalized_bind_password_ref,
            ca_cert_ref=SecretReference.normalize_optional(ca_cert_ref, "ca_cert_ref"),
            tls_required=True,
            nested_groups=bool(nested_groups),
            cache_ttl_seconds=ttl,
            user_base_dn=normalized_user_base,
            group_base_dn=normalized_group_base,
            username_attribute=attributes["username_attribute"],
            display_name_attribute=attributes["display_name_attribute"],
            email_attribute=attributes["email_attribute"],
            group_name_attribute=attributes["group_name_attribute"],
            group_member_attribute=attributes["group_member_attribute"],
            connect_timeout_seconds=connect_timeout,
            operation_timeout_seconds=operation_timeout,
            page_size=normalized_page_size,
            size_limit=normalized_size_limit,
            follow_referrals=bool(follow_referrals),
            start_tls=bool(start_tls),
            nested_group_depth=normalized_depth,
        )

    @classmethod
    def _normalize_url(cls, value: str, *, start_tls: bool) -> str:
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme not in {"ldap", "ldaps"} or not parsed.netloc:
            raise ValidationError("directory url must use ldap:// or ldaps:// with a host")
        if parsed.scheme == "ldap" and not start_tls:
            raise ValidationError("ldap:// directory url requires StartTLS")
        if parsed.scheme == "ldaps" and start_tls:
            raise ValidationError("StartTLS must not be enabled with ldaps://")
        if parsed.username or parsed.password:
            raise ValidationError("directory url must not embed credentials")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValidationError("directory url must be an origin URL without path/query")
        return normalized.rstrip("/")

    @staticmethod
    def _normalize_attribute(value: str) -> str:
        normalized = value.strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9;-]{0,63}", normalized) is None:
            raise ValidationError("LDAP attribute names must contain 1 to 64 safe characters")
        return normalized

    def as_safe_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "url": self.url,
            "base_dn": self.base_dn,
            "user_filter": self.user_filter,
            "group_filter": self.group_filter,
            "bind_dn_ref": self.bind_dn_ref,
            "has_bind_password_ref": self.bind_password_ref is not None,
            "ca_cert_ref": self.ca_cert_ref,
            "tls_required": self.tls_required,
            "nested_groups": self.nested_groups,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "user_base_dn": self.user_base_dn,
            "group_base_dn": self.group_base_dn,
            "username_attribute": self.username_attribute,
            "display_name_attribute": self.display_name_attribute,
            "email_attribute": self.email_attribute,
            "group_name_attribute": self.group_name_attribute,
            "group_member_attribute": self.group_member_attribute,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "operation_timeout_seconds": self.operation_timeout_seconds,
            "page_size": self.page_size,
            "size_limit": self.size_limit,
            "follow_referrals": self.follow_referrals,
            "start_tls": self.start_tls,
            "nested_group_depth": self.nested_group_depth,
        }


@dataclass(frozen=True, slots=True)
class ExternalGroupRoleMapping:
    tenant_id: TenantId
    provider: AuthProviderMode
    external_group: str
    openinfra_roles: tuple[SecurityRole, ...]
    active: bool = True

    @classmethod
    def create(
        cls,
        tenant_id: str | TenantId,
        provider: str,
        external_group: str,
        roles: tuple[str, ...],
        active: bool = True,
    ) -> Self:
        tenant = tenant_id if isinstance(tenant_id, TenantId) else TenantId.from_value(tenant_id)
        normalized_roles = tuple(SecurityRole.from_value(role) for role in dict.fromkeys(roles))
        if not normalized_roles:
            raise ValidationError("external group mapping must grant at least one role")
        return cls(
            tenant_id=tenant,
            provider=AuthProviderMode.from_value(provider),
            external_group=DirectoryGroup.normalize(external_group),
            openinfra_roles=normalized_roles,
            active=bool(active),
        )

    @property
    def internal_group_name(self) -> str:
        digest = hashlib.sha256(
            (self.provider.value + ":" + self.external_group).encode("utf-8")
        ).hexdigest()[:20]
        return "external-" + digest

    def role_names(self) -> tuple[str, ...]:
        return tuple(role.name for role in self.openinfra_roles)

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "provider": self.provider.value,
            "external_group": self.external_group,
            "internal_group_name": self.internal_group_name,
            "roles": list(self.role_names()),
            "active": self.active,
        }


@dataclass(frozen=True, slots=True)
class ExternalAuthenticatedIdentity:
    provider: AuthProviderMode
    subject: str
    display_name: str
    email: str | None
    external_groups: tuple[str, ...]
    user_dn: str

    @classmethod
    def create(
        cls,
        provider: str,
        subject: str,
        display_name: str,
        email: str | None,
        external_groups: tuple[str, ...],
        user_dn: str,
    ) -> Self:
        normalized_groups = tuple(
            sorted({DirectoryGroup.normalize(group) for group in external_groups})
        )
        if not normalized_groups:
            raise ValidationError("external authenticated identity must carry at least one group")
        return cls(
            provider=AuthProviderMode.from_value(provider),
            subject=IdentitySubject.normalize(subject),
            display_name=DisplayName.normalize(display_name),
            email=Email.normalize_optional(email),
            external_groups=normalized_groups,
            user_dn=DirectoryName.normalize(user_dn, "user_dn"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "subject": self.subject,
            "display_name": self.display_name,
            "email": self.email,
            "external_groups": list(self.external_groups),
            "user_dn_hash": hashlib.sha256(self.user_dn.encode("utf-8")).hexdigest(),
        }


class DirectoryName:
    @classmethod
    def normalize(cls, value: str, field_name: str) -> str:
        normalized = ",".join(part.strip() for part in value.strip().split(",") if part.strip())
        if not 3 <= len(normalized) <= 1024:
            raise ValidationError(field_name + " must contain 3 to 1024 characters")
        if any(ord(char) < 32 for char in normalized):
            raise ValidationError(field_name + " contains control characters")
        return normalized


class DirectoryFilter:
    _username_marker = "{username}"

    @classmethod
    def normalize(cls, value: str, field_name: str) -> str:
        normalized = value.strip()
        if not 5 <= len(normalized) <= 512:
            raise ValidationError(field_name + " must contain 5 to 512 characters")
        if not (normalized.startswith("(") and normalized.endswith(")")):
            raise ValidationError(field_name + " must be an LDAP filter enclosed in parentheses")
        if field_name == "user_filter" and cls._username_marker not in normalized:
            raise ValidationError("user_filter must contain {username}")
        if any(char in normalized for char in ("\x00", "\n", "\r")):
            raise ValidationError(field_name + " contains unsafe characters")
        return normalized


class DirectoryGroup:
    @classmethod
    def normalize(cls, value: str) -> str:
        normalized = DirectoryName.normalize(value, "external_group")
        if not re.search(r"(?:^|,)cn=[^,]+", normalized, flags=re.IGNORECASE):
            raise ValidationError("external_group must include a cn= component")
        return normalized.lower()


class SecretReference:
    _allowed_prefixes = ("env:", "vault://", "sops://", "file://", "kms://")

    @classmethod
    def normalize_optional(cls, value: str | None, field_name: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not normalized.startswith(cls._allowed_prefixes):
            raise ValidationError(
                field_name + " must reference env:, vault://, sops://, file:// or kms://"
            )
        return normalized


class DisplayName:
    @classmethod
    def normalize(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 255:
            raise ValidationError("display name must contain 1 to 255 characters")
        return normalized


class Email:
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not re.fullmatch(r"[a-z0-9._%+-]{1,128}@[a-z0-9.-]{1,190}\.[a-z]{2,24}", normalized):
            raise ValidationError("email is invalid")
        return normalized
