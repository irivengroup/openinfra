from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from urllib.parse import urlparse

from openinfra.domain.authentication import SecretReference
from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.identity import (
    IdentityDisplayName,
    IdentityEmail,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
)


class FederatedProvider(StrEnum):
    SAML = "saml"
    LDAP = "ldap"
    OAUTH = "oauth"
    AUTH_PROXY = "auth_proxy"
    OKTA = "okta"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("-", "_")
        for item in cls:
            if item.value == normalized:
                return item
        raise ValidationError("unsupported federated identity provider: " + normalized)


class HttpsOrigin:
    @classmethod
    def normalize(cls, value: str, field_name: str, *, allow_path: bool = False) -> str:
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValidationError(f"{field_name} must use https:// with a host")
        if parsed.username or parsed.password:
            raise ValidationError(f"{field_name} must not embed credentials")
        if parsed.fragment:
            raise ValidationError(f"{field_name} must not include a fragment")
        if not allow_path and (parsed.path not in ("", "/") or parsed.query):
            raise ValidationError(f"{field_name} must be an HTTPS origin without path/query")
        return normalized.rstrip("/")

    @classmethod
    def origin(cls, value: str) -> str:
        parsed = urlparse(value)
        port = f":{parsed.port}" if parsed.port is not None else ""
        return f"{parsed.scheme}://{parsed.hostname}{port}"


@dataclass(frozen=True, slots=True)
class SamlProviderConfig:
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert_ref: str
    sp_entity_id: str
    sp_acs_url: str
    name_id_format: str
    subject_attribute: str
    display_name_attribute: str
    email_attribute: str
    groups_attribute: str
    want_assertions_signed: bool
    want_messages_signed: bool
    allowed_clock_skew_seconds: int

    @classmethod
    def create(
        cls,
        *,
        idp_entity_id: str,
        idp_sso_url: str,
        idp_x509_cert_ref: str,
        sp_entity_id: str,
        sp_acs_url: str,
        name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
        subject_attribute: str = "uid",
        display_name_attribute: str = "displayName",
        email_attribute: str = "mail",
        groups_attribute: str = "groups",
        want_assertions_signed: bool = True,
        want_messages_signed: bool = False,
        allowed_clock_skew_seconds: int = 120,
    ) -> Self:
        entity_id = cls._non_empty(idp_entity_id, "idp_entity_id", 512)
        sp_id = cls._non_empty(sp_entity_id, "sp_entity_id", 512)
        sso_url = HttpsOrigin.normalize(idp_sso_url, "idp_sso_url", allow_path=True)
        acs_url = HttpsOrigin.normalize(sp_acs_url, "sp_acs_url", allow_path=True)
        cert_ref = SecretReference.normalize_optional(idp_x509_cert_ref, "idp_x509_cert_ref")
        if cert_ref is None:
            raise ValidationError("idp_x509_cert_ref is required")
        skew = int(allowed_clock_skew_seconds)
        if not 0 <= skew <= 600:
            raise ValidationError("allowed_clock_skew_seconds must be between 0 and 600")
        attributes = tuple(
            cls._attribute(value, field)
            for value, field in (
                (subject_attribute, "subject_attribute"),
                (display_name_attribute, "display_name_attribute"),
                (email_attribute, "email_attribute"),
                (groups_attribute, "groups_attribute"),
            )
        )
        return cls(
            idp_entity_id=entity_id,
            idp_sso_url=sso_url,
            idp_x509_cert_ref=cert_ref,
            sp_entity_id=sp_id,
            sp_acs_url=acs_url,
            name_id_format=cls._non_empty(name_id_format, "name_id_format", 512),
            subject_attribute=attributes[0],
            display_name_attribute=attributes[1],
            email_attribute=attributes[2],
            groups_attribute=attributes[3],
            want_assertions_signed=bool(want_assertions_signed),
            want_messages_signed=bool(want_messages_signed),
            allowed_clock_skew_seconds=skew,
        )

    @staticmethod
    def _attribute(value: str, field_name: str) -> str:
        normalized = value.strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}", normalized) is None:
            raise ValidationError(f"{field_name} must contain 1 to 128 safe characters")
        return normalized

    @staticmethod
    def _non_empty(value: str, field_name: str, maximum: int) -> str:
        normalized = value.strip()
        if not 1 <= len(normalized) <= maximum:
            raise ValidationError(f"{field_name} must contain 1 to {maximum} characters")
        return normalized

    def as_safe_dict(self) -> dict[str, object]:
        return {
            "idp_entity_id": self.idp_entity_id,
            "idp_sso_url": self.idp_sso_url,
            "has_idp_x509_cert_ref": True,
            "sp_entity_id": self.sp_entity_id,
            "sp_acs_url": self.sp_acs_url,
            "name_id_format": self.name_id_format,
            "subject_attribute": self.subject_attribute,
            "display_name_attribute": self.display_name_attribute,
            "email_attribute": self.email_attribute,
            "groups_attribute": self.groups_attribute,
            "want_assertions_signed": self.want_assertions_signed,
            "want_messages_signed": self.want_messages_signed,
            "allowed_clock_skew_seconds": self.allowed_clock_skew_seconds,
        }


@dataclass(frozen=True, slots=True)
class FederatedIdentity:
    provider: FederatedProvider
    subject: str
    display_name: str
    email: str | None
    external_groups: tuple[str, ...]
    session_index: str | None = None

    @classmethod
    def create(
        cls,
        provider: str,
        subject: str,
        display_name: str,
        email: str | None,
        external_groups: tuple[str, ...],
        session_index: str | None = None,
    ) -> Self:
        groups = tuple(sorted({cls._group(group) for group in external_groups if group.strip()}))
        if not groups:
            raise ValidationError("federated identity must expose at least one external group")
        normalized_session = None if session_index is None else session_index.strip() or None
        if normalized_session is not None and len(normalized_session) > 512:
            raise ValidationError("SAML session index must not exceed 512 characters")
        return cls(
            provider=FederatedProvider.from_value(provider),
            subject=IdentitySubject.normalize(subject),
            display_name=IdentityDisplayName.normalize(display_name),
            email=IdentityEmail.normalize_optional(email),
            external_groups=groups,
            session_index=normalized_session,
        )

    @staticmethod
    def _group(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 512:
            raise ValidationError("external group must contain 1 to 512 characters")
        return normalized


@dataclass(frozen=True, slots=True)
class TeamSyncUser:
    subject: str
    display_name: str
    email: str | None
    active: bool = True

    @classmethod
    def create(
        cls,
        subject: str,
        display_name: str,
        email: str | None = None,
        active: bool = True,
    ) -> Self:
        return cls(
            subject=IdentitySubject.normalize(subject),
            display_name=IdentityDisplayName.normalize(display_name),
            email=IdentityEmail.normalize_optional(email),
            active=bool(active),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "display_name": self.display_name,
            "email": self.email,
            "active": self.active,
        }


@dataclass(frozen=True, slots=True)
class TeamSyncGroup:
    name: str
    display_name: str
    roles: tuple[str, ...]
    members: tuple[str, ...]

    @classmethod
    def create(
        cls,
        name: str,
        display_name: str,
        roles: tuple[str, ...],
        members: tuple[str, ...],
    ) -> Self:
        return cls(
            name=IdentityGroupName.normalize(name),
            display_name=IdentityDisplayName.normalize(display_name),
            roles=tuple(role.name for role in IdentityRoleSet.from_names(roles)),
            members=tuple(sorted({IdentitySubject.normalize(member) for member in members})),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "roles": list(self.roles),
            "members": list(self.members),
        }


@dataclass(frozen=True, slots=True)
class TeamSyncSnapshot:
    tenant_id: TenantId
    source_id: str
    provider: FederatedProvider
    users: tuple[TeamSyncUser, ...]
    groups: tuple[TeamSyncGroup, ...]
    captured_at: datetime
    fingerprint: str

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        source_id: str,
        provider: str,
        users: tuple[TeamSyncUser, ...],
        groups: tuple[TeamSyncGroup, ...],
        captured_at: datetime | None = None,
    ) -> Self:
        tenant = TenantId.from_value(tenant_id)
        normalized_source = source_id.strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized_source) is None:
            raise ValidationError("team sync source_id must use 2 to 64 safe characters")
        if len(users) > 100_000 or len(groups) > 20_000:
            raise ValidationError("team sync snapshot exceeds safety limits")
        users_by_subject = {user.subject: user for user in users}
        if len(users_by_subject) != len(users):
            raise ValidationError("team sync users must have unique subjects")
        groups_by_name = {group.name: group for group in groups}
        if len(groups_by_name) != len(groups):
            raise ValidationError("team sync groups must have unique names")
        unknown = sorted(
            {
                member
                for group in groups
                for member in group.members
                if member not in users_by_subject
            }
        )
        if unknown:
            raise ValidationError("team sync group members must exist in snapshot: " + unknown[0])
        timestamp = captured_at or datetime.now(UTC)
        if timestamp.tzinfo is None:
            raise ValidationError("team sync captured_at must be timezone-aware")
        normalized_users = tuple(users_by_subject[key] for key in sorted(users_by_subject))
        normalized_groups = tuple(groups_by_name[key] for key in sorted(groups_by_name))
        payload = {
            "tenant_id": tenant.value,
            "source_id": normalized_source,
            "provider": FederatedProvider.from_value(provider).value,
            "users": [user.as_dict() for user in normalized_users],
            "groups": [group.as_dict() for group in normalized_groups],
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            tenant_id=tenant,
            source_id=normalized_source,
            provider=FederatedProvider.from_value(provider),
            users=normalized_users,
            groups=normalized_groups,
            captured_at=timestamp.astimezone(UTC),
            fingerprint=fingerprint,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "source_id": self.source_id,
            "provider": self.provider.value,
            "users": [user.as_dict() for user in self.users],
            "groups": [group.as_dict() for group in self.groups],
            "captured_at": self.captured_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class TeamSyncSourceConfig:
    tenant_id: TenantId
    source_id: str
    provider: FederatedProvider
    endpoint: str | None
    token_ref: str | None
    snapshot_file: str | None
    signature_secret_ref: str | None
    timeout_seconds: int
    page_size: int
    deactivate_orphans: bool
    group_role_mappings: tuple[tuple[str, tuple[str, ...]], ...]

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        source_id: str,
        provider: str,
        endpoint: str | None = None,
        token_ref: str | None = None,
        snapshot_file: str | None = None,
        signature_secret_ref: str | None = None,
        timeout_seconds: int = 30,
        page_size: int = 500,
        deactivate_orphans: bool = True,
        group_role_mappings: tuple[tuple[str, tuple[str, ...]], ...] = (),
    ) -> Self:
        normalized_provider = FederatedProvider.from_value(provider)
        normalized_source = TeamSyncSnapshot.create(
            tenant_id=tenant_id,
            source_id=source_id,
            provider=normalized_provider.value,
            users=(),
            groups=(),
        ).source_id
        normalized_endpoint = None
        if endpoint is not None and endpoint.strip():
            normalized_endpoint = HttpsOrigin.normalize(
                endpoint, "team sync endpoint", allow_path=True
            )
        normalized_token = SecretReference.normalize_optional(token_ref, "token_ref")
        normalized_signature = SecretReference.normalize_optional(
            signature_secret_ref, "signature_secret_ref"
        )
        normalized_snapshot = None if snapshot_file is None else snapshot_file.strip() or None
        if normalized_provider in {FederatedProvider.OAUTH, FederatedProvider.OKTA} and (
            normalized_endpoint is None or normalized_token is None
        ):
            raise ValidationError("OAuth/Okta team sync requires endpoint and token_ref")
        if normalized_provider is FederatedProvider.AUTH_PROXY and (
            normalized_snapshot is None or normalized_signature is None
        ):
            raise ValidationError(
                "auth_proxy team sync requires snapshot_file and signature_secret_ref"
            )
        timeout = int(timeout_seconds)
        page = int(page_size)
        if not 1 <= timeout <= 120:
            raise ValidationError("team sync timeout_seconds must be between 1 and 120")
        if not 1 <= page <= 1000:
            raise ValidationError("team sync page_size must be between 1 and 1000")
        normalized_mappings: list[tuple[str, tuple[str, ...]]] = []
        seen_groups: set[str] = set()
        for external_group, roles in group_role_mappings:
            group_key = " ".join(external_group.strip().split()).lower()
            if not group_key or len(group_key) > 512:
                raise ValidationError("team sync external group mapping is invalid")
            if group_key in seen_groups:
                raise ValidationError("team sync external group mappings must be unique")
            seen_groups.add(group_key)
            normalized_roles = tuple(role.name for role in IdentityRoleSet.from_names(roles))
            normalized_mappings.append((group_key, normalized_roles))
        return cls(
            tenant_id=TenantId.from_value(tenant_id),
            source_id=normalized_source,
            provider=normalized_provider,
            endpoint=normalized_endpoint,
            token_ref=normalized_token,
            snapshot_file=normalized_snapshot,
            signature_secret_ref=normalized_signature,
            timeout_seconds=timeout,
            page_size=page,
            deactivate_orphans=bool(deactivate_orphans),
            group_role_mappings=tuple(normalized_mappings),
        )

    def roles_for_external_group(self, external_group: str) -> tuple[str, ...]:
        key = " ".join(external_group.strip().split()).lower()
        for candidate, roles in self.group_role_mappings:
            if candidate == key:
                return roles
        return ()
