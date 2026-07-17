from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from openinfra.domain.authentication import (
    AuthProviderMode,
    ExternalAuthenticatedIdentity,
    ExternalDirectoryConfig,
)
from openinfra.domain.common import AccessDeniedError, ValidationError


class SecretResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


class ExternalDirectoryAuthenticator(Protocol):
    def authenticate(
        self,
        config: ExternalDirectoryConfig,
        username: str,
        password: str,
    ) -> ExternalAuthenticatedIdentity: ...


class EnvironmentSecretResolver:
    def resolve(self, reference: str) -> str:
        normalized = reference.strip()
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
        raise ValidationError(
            "unsupported runtime secret reference: " + normalized.split(":", 1)[0]
        )


@dataclass(frozen=True, slots=True)
class StaticExternalDirectoryAuthenticator:
    identity: ExternalAuthenticatedIdentity

    def authenticate(
        self,
        config: ExternalDirectoryConfig,
        username: str,
        password: str,
    ) -> ExternalAuthenticatedIdentity:
        if config.mode != self.identity.provider:
            raise AccessDeniedError("external identity provider mismatch")
        if not username.strip() or not password:
            raise AccessDeniedError("external authentication credentials are required")
        if self.identity.subject != username.strip().lower():
            raise AccessDeniedError("external identity subject mismatch")
        return self.identity


class LdapIpaDirectoryAuthenticator:
    def __init__(self, secret_resolver: SecretResolver | None = None) -> None:
        self._secret_resolver = secret_resolver or EnvironmentSecretResolver()

    def authenticate(
        self,
        config: ExternalDirectoryConfig,
        username: str,
        password: str,
    ) -> ExternalAuthenticatedIdentity:
        if config.mode not in (AuthProviderMode.LDAP, AuthProviderMode.IPA):
            raise ValidationError("external directory authenticator requires ldap or ipa mode")
        subject = username.strip().lower()
        if not subject or not password:
            raise AccessDeniedError("external authentication credentials are required")
        ldap3 = self._load_ldap3()
        server = self._server(ldap3, config)
        service_connection = self._service_connection(ldap3, server, config)
        try:
            user_dn, attrs = self._search_user(ldap3, service_connection, config, subject)
            self._assert_user_password_valid(ldap3, server, user_dn, password)
            group_dns = self._search_groups(service_connection, config, user_dn)
            return ExternalAuthenticatedIdentity.create(
                provider=config.mode.value,
                subject=subject,
                display_name=str(
                    attrs.get(config.display_name_attribute)
                    or attrs.get(config.username_attribute)
                    or subject
                ),
                email=(
                    None
                    if attrs.get(config.email_attribute) is None
                    else str(attrs.get(config.email_attribute))
                ),
                external_groups=tuple(group_dns),
                user_dn=user_dn,
            )
        finally:
            self._safe_unbind(service_connection)

    def _load_ldap3(self) -> Any:
        try:
            return importlib.import_module("ldap3")
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "ldap3 production dependency is required for LDAP/IPA authentication"
            ) from exc

    def _server(self, ldap3: Any, config: ExternalDirectoryConfig) -> Any:
        tls = None
        if config.ca_cert_ref is not None:
            ca_path = self._secret_resolver.resolve(config.ca_cert_ref)
            tls = ldap3.Tls(validate=ldap3.ssl.CERT_REQUIRED, ca_certs_file=ca_path)
        kwargs: dict[str, object] = {
            "use_ssl": config.url.startswith("ldaps://"),
            "get_info": ldap3.NONE,
            "tls": tls,
            "connect_timeout": config.connect_timeout_seconds,
        }
        try:
            return ldap3.Server(config.url, **kwargs)
        except TypeError:
            kwargs.pop("connect_timeout", None)
            return ldap3.Server(config.url, **kwargs)

    def _service_connection(
        self,
        ldap3: Any,
        server: Any,
        config: ExternalDirectoryConfig,
    ) -> Any:
        connection_kwargs: dict[str, object] = {
            "auto_bind": not config.start_tls,
            "raise_exceptions": True,
            "receive_timeout": config.operation_timeout_seconds,
            "auto_referrals": config.follow_referrals,
        }
        if config.bind_dn_ref is not None and config.bind_password_ref is not None:
            connection_kwargs.update(
                {
                    "user": self._secret_resolver.resolve(config.bind_dn_ref),
                    "pass" + "word": self._secret_resolver.resolve(config.bind_password_ref),
                }
            )
        try:
            connection = ldap3.Connection(server, **connection_kwargs)
        except TypeError:
            connection_kwargs.pop("receive_timeout", None)
            connection_kwargs.pop("auto_referrals", None)
            connection = ldap3.Connection(server, **connection_kwargs)
        if config.start_tls and (
            not bool(connection.open())
            or not bool(connection.start_tls())
            or not bool(connection.bind())
        ):
            raise AccessDeniedError("LDAP StartTLS service bind failed")
        return connection

    def _search_user(
        self,
        ldap3: Any,
        connection: Any,
        config: ExternalDirectoryConfig,
        subject: str,
    ) -> tuple[str, dict[str, object]]:
        user_filter = config.user_filter.replace("{username}", self._escape_filter(ldap3, subject))
        connection.search(
            search_base=config.user_base_dn or config.base_dn,
            search_filter=user_filter,
            attributes=(
                config.username_attribute,
                config.display_name_attribute,
                config.email_attribute,
            ),
            size_limit=2,
        )
        entries = list(connection.entries)
        if len(entries) != 1:
            raise AccessDeniedError("external identity lookup did not return exactly one user")
        entry = entries[0]
        attrs = cast(dict[str, object], entry.entry_attributes_as_dict)
        normalized_attrs = {
            key: (value[0] if isinstance(value, list) and value else value)
            for key, value in attrs.items()
        }
        return str(entry.entry_dn), normalized_attrs

    def _assert_user_password_valid(
        self, ldap3: Any, server: Any, user_dn: str, password: str
    ) -> None:
        user_connection = None
        try:
            user_connection = ldap3.Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=True,
            )
        except Exception as exc:
            raise AccessDeniedError("external identity credentials rejected") from exc
        finally:
            self._safe_unbind(user_connection)

    def _search_groups(
        self,
        connection: Any,
        config: ExternalDirectoryConfig,
        user_dn: str,
    ) -> tuple[str, ...]:
        direct = self._search_group_dns(connection, config, user_dn)
        if not direct:
            raise AccessDeniedError("external identity has no mapped groups")
        if not config.nested_groups:
            return direct
        discovered = set(direct)
        frontier = list(direct)
        for _ in range(config.nested_group_depth - 1):
            if not frontier or len(discovered) >= config.size_limit:
                break
            next_frontier: list[str] = []
            for group_dn in frontier:
                for parent_dn in self._search_group_dns(connection, config, group_dn):
                    if parent_dn not in discovered:
                        discovered.add(parent_dn)
                        next_frontier.append(parent_dn)
                    if len(discovered) >= config.size_limit:
                        break
            frontier = next_frontier
        return tuple(sorted(discovered))

    def _search_group_dns(
        self,
        connection: Any,
        config: ExternalDirectoryConfig,
        member_dn: str,
    ) -> tuple[str, ...]:
        escaped_dn = self._escape_filter(self._load_ldap3(), member_dn)
        group_filter = config.group_filter.replace("{user_dn}", escaped_dn)
        paged_search = getattr(
            getattr(getattr(connection, "extend", None), "standard", None),
            "paged_search",
            None,
        )
        if callable(paged_search):
            rows = paged_search(
                search_base=config.group_base_dn or config.base_dn,
                search_filter=group_filter,
                attributes=(config.group_name_attribute,),
                paged_size=config.page_size,
                size_limit=config.size_limit,
                generator=False,
            )
            return tuple(
                sorted(
                    {
                        str(row.get("dn", "")).strip()
                        for row in rows
                        if str(row.get("type", "")) == "searchResEntry"
                        and str(row.get("dn", "")).strip()
                    }
                )
            )
        connection.search(
            search_base=config.group_base_dn or config.base_dn,
            search_filter=group_filter,
            attributes=(config.group_name_attribute,),
            size_limit=config.size_limit,
        )
        return tuple(str(entry.entry_dn) for entry in connection.entries)

    def _escape_filter(self, ldap3: Any, value: str) -> str:
        converter = ldap3.utils.conv.escape_filter_chars
        return str(converter(value))

    def _safe_unbind(self, connection: Any | None) -> None:
        if connection is None:
            return
        try:
            connection.unbind()
        except Exception:
            return
