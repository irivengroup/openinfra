from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from urllib.parse import quote

from openinfra.domain.authentication import ExternalDirectoryConfig, ExternalGroupRoleMapping
from openinfra.domain.common import ValidationError
from openinfra.domain.editions import EditionDatabasePolicy
from openinfra.domain.federated_identity import SamlProviderConfig, TeamSyncSourceConfig
from openinfra.infrastructure.oracle import OracleConnectionSettings


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    values: dict[str, str]
    source: Path | None

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)


class RuntimeConfigLoader:
    _candidate_paths = (
        Path("/etc/openinfra/openinfra.conf"),
        Path("/opt/openinfra/config/openinfra.conf"),
    )

    def load(self, explicit_path: Path | None = None) -> RuntimeConfig:
        path = explicit_path or self._first_existing_config()
        if path is None:
            return RuntimeConfig({}, None)
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            normalized_key = key.strip()
            if not normalized_key:
                continue
            values[normalized_key] = self._unquote(value.strip())
        return RuntimeConfig(values, path)

    def _first_existing_config(self) -> Path | None:
        override = os.environ.get("OPENINFRA_RUNTIME_CONFIG", "").strip()
        if override:
            path = Path(override)
            return path if path.is_file() else None
        for path in self._candidate_paths:
            if path.is_file():
                return path
        return None

    def _unquote(self, value: str) -> str:
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            payload = value[1:-1]
            return payload.replace('\\"', '"').replace("\\\\", "\\")
        return value


class RuntimeSecretResolver:
    def resolve(self, reference: str) -> str:
        normalized = reference.strip()
        if not normalized:
            return ""
        if normalized.startswith("env:"):
            name = normalized.removeprefix("env:").strip()
            value = os.environ.get(name, "")
            if not value:
                raise ValidationError("missing environment secret reference: " + name)
            return value
        if normalized.startswith("file://"):
            path = Path(normalized.removeprefix("file://"))
            if not path.is_file():
                raise ValidationError("missing file secret reference: " + str(path))
            return path.read_text(encoding="utf-8").strip()
        if normalized.startswith(("vault://", "sops://", "kms://")):
            raise ValidationError(
                "runtime secret backend is not available in this process: "
                + normalized.split(":", 1)[0]
            )
        return normalized


class RuntimeDatabaseDsnResolver:
    def __init__(
        self,
        loader: RuntimeConfigLoader | None = None,
        secret_resolver: RuntimeSecretResolver | None = None,
    ) -> None:
        self._loader = loader or RuntimeConfigLoader()
        self._secret_resolver = secret_resolver or RuntimeSecretResolver()

    def resolve(self, explicit_dsn: str | None = None) -> str:
        direct = self._resolve_named_dsn(
            explicit_dsn,
            direct_key="OPENINFRA_DATABASE_DSN",
            reference_key="OPENINFRA_DATABASE_DSN_REF",
        )
        if direct:
            return direct
        runtime = self._loader.load()
        user_ref = runtime.get("OPENINFRA_POSTGRES_USER_REF")
        password_ref = runtime.get("OPENINFRA_POSTGRES_PASSWORD_REF")
        if user_ref and password_ref:
            username = self._secret_resolver.resolve(user_ref)
            credential = self._secret_resolver.resolve(password_ref)
            return (
                "postgresql://"
                + quote(username, safe="")
                + ":"
                + quote(credential, safe="")
                + "@127.0.0.1:5432/openinfra"
            )
        return ""

    def resolve_read_replica(self, explicit_dsn: str | None = None) -> str:
        return self._resolve_named_dsn(
            explicit_dsn,
            direct_key="OPENINFRA_DATABASE_READ_DSN",
            reference_key="OPENINFRA_DATABASE_READ_DSN_REF",
        )

    def resolve_cursor_signing_secret(self, explicit_secret: str | None = None) -> str:
        direct = (explicit_secret or "").strip() or os.environ.get(
            "OPENINFRA_CURSOR_SIGNING_SECRET", ""
        ).strip()
        if direct:
            return direct
        runtime = self._loader.load()
        configured = runtime.get("OPENINFRA_CURSOR_SIGNING_SECRET")
        if configured:
            return configured
        reference = runtime.get("OPENINFRA_CURSOR_SIGNING_SECRET_REF")
        if reference:
            return self._secret_resolver.resolve(reference)
        return self.resolve_consistency_secret()

    def resolve_consistency_secret(self, explicit_secret: str | None = None) -> str:
        direct = (explicit_secret or "").strip() or os.environ.get(
            "OPENINFRA_READ_CONSISTENCY_SECRET", ""
        ).strip()
        if direct:
            return direct
        runtime = self._loader.load()
        configured = runtime.get("OPENINFRA_READ_CONSISTENCY_SECRET")
        if configured:
            return configured
        reference = runtime.get("OPENINFRA_READ_CONSISTENCY_SECRET_REF")
        return self._secret_resolver.resolve(reference) if reference else ""

    def _resolve_named_dsn(
        self,
        explicit_dsn: str | None,
        *,
        direct_key: str,
        reference_key: str,
    ) -> str:
        direct = (explicit_dsn or "").strip() or os.environ.get(direct_key, "").strip()
        if direct:
            return direct
        runtime = self._loader.load()
        configured_direct = runtime.get(direct_key)
        if configured_direct:
            return configured_direct
        dsn_ref = runtime.get(reference_key)
        return self._secret_resolver.resolve(dsn_ref) if dsn_ref else ""


class RuntimeDatabaseBackendResolver:
    _SUPPORTED: ClassVar[set[str]] = {"postgresql", "oracle", "json"}

    def __init__(self, loader: RuntimeConfigLoader | None = None) -> None:
        self._loader = loader or RuntimeConfigLoader()

    def resolve(
        self,
        explicit_backend: str | None = None,
        explicit_edition: str | None = None,
    ) -> str:
        runtime = self._loader.load()
        value = (
            (explicit_backend or "").strip()
            or os.environ.get("OPENINFRA_DATABASE_BACKEND", "").strip()
            or runtime.get("OPENINFRA_DATABASE_BACKEND", "postgresql").strip()
            or "postgresql"
        ).lower()
        if value not in self._SUPPORTED:
            raise ValidationError("database backend must be postgresql, oracle or json")
        edition = (
            (explicit_edition or "").strip()
            or os.environ.get("OPENINFRA_EDITION", "").strip()
            or runtime.get("OPENINFRA_EDITION", "enterprise").strip()
            or "enterprise"
        )
        return EditionDatabasePolicy.validate(edition, value)


class RuntimeOracleSettingsResolver:
    def __init__(
        self,
        loader: RuntimeConfigLoader | None = None,
        secret_resolver: RuntimeSecretResolver | None = None,
    ) -> None:
        self._loader = loader or RuntimeConfigLoader()
        self._secret_resolver = secret_resolver or RuntimeSecretResolver()

    def resolve(
        self,
        *,
        explicit_dsn: str | None = None,
        explicit_user: str | None = None,
        explicit_password: str | None = None,
    ) -> OracleConnectionSettings:
        runtime = self._loader.load()
        dsn = (
            (explicit_dsn or "").strip()
            or os.environ.get("OPENINFRA_ORACLE_DSN", "").strip()
            or runtime.get("OPENINFRA_ORACLE_DSN").strip()
        )
        user = (
            (explicit_user or "").strip()
            or os.environ.get("OPENINFRA_ORACLE_USER", "").strip()
            or runtime.get("OPENINFRA_ORACLE_USER").strip()
        )
        credential = (explicit_password or "").strip()
        if not credential:
            direct = os.environ.get("OPENINFRA_ORACLE_PASSWORD", "").strip()
            reference = (
                os.environ.get("OPENINFRA_ORACLE_PASSWORD_REF", "").strip()
                or runtime.get("OPENINFRA_ORACLE_PASSWORD_REF").strip()
            )
            credential = direct or (self._secret_resolver.resolve(reference) if reference else "")
        return OracleConnectionSettings.create(
            dsn=dsn,
            user=user,
            password=credential,
            pool_min=int(runtime.get("OPENINFRA_ORACLE_POOL_MIN", "1")),
            pool_max=int(runtime.get("OPENINFRA_ORACLE_POOL_MAX", "10")),
            pool_increment=int(runtime.get("OPENINFRA_ORACLE_POOL_INCREMENT", "1")),
            timeout_seconds=int(runtime.get("OPENINFRA_ORACLE_TIMEOUT_SECONDS", "30")),
        )


class RuntimeAdvancedIdentityConfigResolver:
    def __init__(self, loader: RuntimeConfigLoader | None = None) -> None:
        self._loader = loader or RuntimeConfigLoader()

    def saml_tenant_id(self) -> str:
        tenant_id = self._loader.load().get("OPENINFRA_SAML_TENANT_ID", "default").strip()
        if not tenant_id:
            raise ValidationError("OPENINFRA_SAML_TENANT_ID cannot be empty")
        return tenant_id

    def saml_config(self) -> SamlProviderConfig:
        runtime = self._loader.load()
        return SamlProviderConfig.create(
            idp_entity_id=runtime.get("OPENINFRA_SAML_IDP_ENTITY_ID"),
            idp_sso_url=runtime.get("OPENINFRA_SAML_IDP_SSO_URL"),
            idp_x509_cert_ref=runtime.get("OPENINFRA_SAML_IDP_X509_CERT_REF"),
            sp_entity_id=runtime.get("OPENINFRA_SAML_SP_ENTITY_ID"),
            sp_acs_url=runtime.get("OPENINFRA_SAML_SP_ACS_URL"),
            name_id_format=runtime.get(
                "OPENINFRA_SAML_NAME_ID_FORMAT",
                "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
            ),
            subject_attribute=runtime.get("OPENINFRA_SAML_SUBJECT_ATTRIBUTE", "uid"),
            display_name_attribute=runtime.get(
                "OPENINFRA_SAML_DISPLAY_NAME_ATTRIBUTE", "displayName"
            ),
            email_attribute=runtime.get("OPENINFRA_SAML_EMAIL_ATTRIBUTE", "mail"),
            groups_attribute=runtime.get("OPENINFRA_SAML_GROUPS_ATTRIBUTE", "groups"),
            want_assertions_signed=self._bool(
                runtime.get("OPENINFRA_SAML_WANT_ASSERTIONS_SIGNED", "true")
            ),
            want_messages_signed=self._bool(
                runtime.get("OPENINFRA_SAML_WANT_MESSAGES_SIGNED", "false")
            ),
            allowed_clock_skew_seconds=int(runtime.get("OPENINFRA_SAML_CLOCK_SKEW_SECONDS", "120")),
        )

    def directory_config(self) -> ExternalDirectoryConfig:
        runtime = self._loader.load()
        return ExternalDirectoryConfig.create(
            mode=runtime.get("OPENINFRA_LDAP_MODE", "ldap"),
            url=runtime.get("OPENINFRA_LDAP_URL"),
            base_dn=runtime.get("OPENINFRA_LDAP_BASE_DN"),
            user_filter=runtime.get("OPENINFRA_LDAP_USER_FILTER", "(uid={username})"),
            group_filter=runtime.get("OPENINFRA_LDAP_GROUP_FILTER", "(member={user_dn})"),
            bind_dn_ref=runtime.get("OPENINFRA_LDAP_BIND_DN_REF") or None,
            bind_password_ref=runtime.get("OPENINFRA_LDAP_BIND_PASSWORD_REF") or None,
            ca_cert_ref=runtime.get("OPENINFRA_LDAP_CA_CERT_REF") or None,
            user_base_dn=runtime.get("OPENINFRA_LDAP_USER_BASE_DN") or None,
            group_base_dn=runtime.get("OPENINFRA_LDAP_GROUP_BASE_DN") or None,
            username_attribute=runtime.get("OPENINFRA_LDAP_USERNAME_ATTRIBUTE", "uid"),
            display_name_attribute=runtime.get(
                "OPENINFRA_LDAP_DISPLAY_NAME_ATTRIBUTE", "displayName"
            ),
            email_attribute=runtime.get("OPENINFRA_LDAP_EMAIL_ATTRIBUTE", "mail"),
            group_name_attribute=runtime.get("OPENINFRA_LDAP_GROUP_NAME_ATTRIBUTE", "cn"),
            group_member_attribute=runtime.get("OPENINFRA_LDAP_GROUP_MEMBER_ATTRIBUTE", "member"),
            connect_timeout_seconds=int(runtime.get("OPENINFRA_LDAP_CONNECT_TIMEOUT_SECONDS", "5")),
            operation_timeout_seconds=int(
                runtime.get("OPENINFRA_LDAP_OPERATION_TIMEOUT_SECONDS", "15")
            ),
            page_size=int(runtime.get("OPENINFRA_LDAP_PAGE_SIZE", "500")),
            size_limit=int(runtime.get("OPENINFRA_LDAP_SIZE_LIMIT", "5000")),
            follow_referrals=self._bool(runtime.get("OPENINFRA_LDAP_FOLLOW_REFERRALS", "false")),
            start_tls=self._bool(runtime.get("OPENINFRA_LDAP_START_TLS", "false")),
            nested_groups=self._bool(runtime.get("OPENINFRA_LDAP_NESTED_GROUPS", "true")),
            nested_group_depth=int(runtime.get("OPENINFRA_LDAP_NESTED_GROUP_DEPTH", "5")),
            cache_ttl_seconds=int(runtime.get("OPENINFRA_LDAP_CACHE_TTL_SECONDS", "300")),
        )

    def team_sync_source(self, source_id: str) -> TeamSyncSourceConfig:
        runtime = self._loader.load()
        normalized_id = source_id.strip().lower()
        prefix = "OPENINFRA_TEAM_SYNC_" + normalized_id.upper().replace("-", "_") + "_"
        mappings = self._role_mappings(runtime.get(prefix + "GROUP_ROLE_MAPPINGS", ""))
        return TeamSyncSourceConfig.create(
            tenant_id=runtime.get(prefix + "TENANT_ID", "default"),
            source_id=normalized_id,
            provider=runtime.get(prefix + "PROVIDER"),
            endpoint=runtime.get(prefix + "ENDPOINT") or None,
            token_ref=runtime.get(prefix + "TOKEN_REF") or None,
            snapshot_file=runtime.get(prefix + "SNAPSHOT_FILE") or None,
            signature_secret_ref=runtime.get(prefix + "SIGNATURE_SECRET_REF") or None,
            timeout_seconds=int(runtime.get(prefix + "TIMEOUT_SECONDS", "30")),
            page_size=int(runtime.get(prefix + "PAGE_SIZE", "500")),
            deactivate_orphans=self._bool(runtime.get(prefix + "DEACTIVATE_ORPHANS", "true")),
            group_role_mappings=mappings,
        )

    def team_sync_sources(self) -> tuple[str, ...]:
        value = self._loader.load().get("OPENINFRA_TEAM_SYNC_SOURCES", "")
        return tuple(
            dict.fromkeys(item.strip().lower() for item in value.split(",") if item.strip())
        )

    def saml_group_role_mappings(self, tenant_id: str) -> tuple[ExternalGroupRoleMapping, ...]:
        runtime = self._loader.load()
        return tuple(
            ExternalGroupRoleMapping.create(
                tenant_id=tenant_id,
                provider="saml",
                external_group=external_group,
                roles=roles,
            )
            for external_group, roles in self._role_mappings(
                runtime.get("OPENINFRA_SAML_GROUP_ROLE_MAPPINGS", "")
            )
        )

    @staticmethod
    def _role_mappings(value: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        mappings: list[tuple[str, tuple[str, ...]]] = []
        for entry in value.split(";"):
            normalized = entry.strip()
            if not normalized:
                continue
            group, separator, roles_value = normalized.rpartition("=")
            if not separator:
                raise ValidationError("group role mappings must use group=role1,role2")
            roles = tuple(item.strip() for item in roles_value.split(",") if item.strip())
            if not roles:
                raise ValidationError("group role mapping must grant at least one role")
            mappings.append((group.strip(), roles))
        return tuple(mappings)

    @staticmethod
    def _bool(value: str) -> bool:
        normalized = value.strip().lower()
        if normalized not in {"true", "false"}:
            raise ValidationError("boolean runtime configuration values must be true or false")
        return normalized == "true"
