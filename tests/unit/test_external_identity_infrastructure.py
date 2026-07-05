from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from openinfra.domain.authentication import (
    AuthProviderMode,
    ExternalAuthenticatedIdentity,
    ExternalDirectoryConfig,
)
from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.infrastructure.external_identity import (
    EnvironmentSecretResolver,
    LdapIpaDirectoryAuthenticator,
    StaticExternalDirectoryAuthenticator,
)


class _FakeEntry:
    def __init__(self, dn: str, attrs: dict[str, object] | None = None) -> None:
        self.entry_dn = dn
        self.entry_attributes_as_dict = attrs or {}


class _FakeConnection:
    searches: list[str] = []

    def __init__(
        self,
        server: object,
        user: str | None = None,
        password: str | None = None,
        auto_bind: bool = False,
        raise_exceptions: bool = False,
    ) -> None:
        self.server = server
        self.user = user
        self.password = password
        self.auto_bind = auto_bind
        self.raise_exceptions = raise_exceptions
        self.entries: list[_FakeEntry] = []
        if user == "uid=alice,ou=people,dc=example,dc=net" and password != "valid-secret":
            raise RuntimeError("invalid bind")

    def search(
        self,
        search_base: str,
        search_filter: str,
        attributes: tuple[str, ...],
        size_limit: int,
    ) -> None:
        _ = (search_base, attributes, size_limit)
        _FakeConnection.searches.append(search_filter)
        if "member=uid=alice" in search_filter:
            self.entries = [_FakeEntry("cn=ops,ou=groups,dc=example,dc=net")]
            return
        if "uid=alice" in search_filter:
            self.entries = [
                _FakeEntry(
                    "uid=alice,ou=people,dc=example,dc=net",
                    {
                        "cn": ["alice"],
                        "displayName": ["Alice Infra"],
                        "mail": ["alice@example.net"],
                    },
                )
            ]
            return
        self.entries = []

    def unbind(self) -> None:
        return None


class _FakeServer:
    def __init__(self, url: str, use_ssl: bool, get_info: object, tls: object | None) -> None:
        self.url = url
        self.use_ssl = use_ssl
        self.get_info = get_info
        self.tls = tls


class _FakeTls:
    def __init__(self, validate: object, ca_certs_file: str) -> None:
        self.validate = validate
        self.ca_certs_file = ca_certs_file


def _fake_ldap3() -> ModuleType:
    module = ModuleType("ldap3")
    module.NONE = object()
    module.ssl = SimpleNamespace(CERT_REQUIRED="required")
    module.Tls = _FakeTls
    module.Server = _FakeServer
    module.Connection = _FakeConnection
    module.utils = SimpleNamespace(
        conv=SimpleNamespace(escape_filter_chars=lambda value: str(value).replace("*", r"\2a"))
    )
    return module


def _config(ca_cert_ref: str | None = None) -> ExternalDirectoryConfig:
    return ExternalDirectoryConfig.create(
        mode="ldap",
        url="ldaps://ldap.example.net",
        base_dn="dc=example,dc=net",
        user_filter="(uid={username})",
        group_filter="(member={user_dn})",
        bind_dn_ref="env:OPENINFRA_LDAP_BIND_DN",
        bind_password_ref="env:OPENINFRA_LDAP_BIND_PASSWORD",  # noqa: S106
        ca_cert_ref=ca_cert_ref,
    )


class TestExternalIdentityInfrastructure:
    def test_environment_secret_resolver_supports_env_and_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("from-file\n", encoding="utf-8")
        monkeypatch.setenv("OPENINFRA_TEST_SECRET", "from-env")
        resolver = EnvironmentSecretResolver()

        assert resolver.resolve("env:OPENINFRA_TEST_SECRET") == "from-env"
        assert resolver.resolve("file://" + str(secret_file)) == "from-file"
        with pytest.raises(ValidationError):
            resolver.resolve("env:OPENINFRA_MISSING_SECRET")
        with pytest.raises(ValidationError):
            resolver.resolve("vault://not-supported-at-runtime")
        with pytest.raises(ValidationError):
            resolver.resolve("file:///tmp/openinfra-missing-secret")

    def test_ldap_authenticator_uses_ldaps_service_bind_user_bind_and_group_search(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("ca", encoding="utf-8")
        monkeypatch.setenv("OPENINFRA_LDAP_BIND_DN", "cn=bind,dc=example,dc=net")
        monkeypatch.setenv("OPENINFRA_LDAP_BIND_PASSWORD", "bind-secret")
        sys.modules["ldap3"] = _fake_ldap3()
        try:
            identity = LdapIpaDirectoryAuthenticator().authenticate(
                _config("file://" + str(ca_file)),
                "alice",
                "valid-secret",
            )
        finally:
            sys.modules.pop("ldap3", None)

        assert identity.subject == "alice"
        assert identity.display_name == "Alice Infra"
        assert identity.external_groups == ("cn=ops,ou=groups,dc=example,dc=net",)
        assert any("uid=alice" in item for item in _FakeConnection.searches)

    def test_ldap_authenticator_rejects_bad_password_and_missing_dependency(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OPENINFRA_LDAP_BIND_DN", "cn=bind,dc=example,dc=net")
        monkeypatch.setenv("OPENINFRA_LDAP_BIND_PASSWORD", "bind-secret")
        sys.modules["ldap3"] = _fake_ldap3()
        try:
            with pytest.raises(AccessDeniedError):
                LdapIpaDirectoryAuthenticator().authenticate(
                    _config(),
                    "alice",
                    "invalid-secret",
                )
        finally:
            sys.modules.pop("ldap3", None)
        with pytest.raises(ValidationError):
            LdapIpaDirectoryAuthenticator().authenticate(
                _config(),
                "alice",
                "valid-secret",
            )

    def test_static_authenticator_and_ldap_edge_cases(self) -> None:
        identity = ExternalAuthenticatedIdentity.create(
            "ldap",
            "alice",
            "Alice Infra",
            None,
            ("cn=ops,dc=example,dc=net",),
            "uid=alice,dc=example,dc=net",
        )
        static = StaticExternalDirectoryAuthenticator(identity)
        with pytest.raises(AccessDeniedError):
            static.authenticate(_config(), "bob", "secret")
        with pytest.raises(AccessDeniedError):
            static.authenticate(_config(), "alice", "")
        ipa_config = ExternalDirectoryConfig.create(
            mode="ipa",
            url="ldaps://ldap.example.net",
            base_dn="dc=example,dc=net",
            user_filter="(uid={username})",
            group_filter="(member={user_dn})",
        )
        with pytest.raises(AccessDeniedError):
            static.authenticate(ipa_config, "alice", "secret")
        standard_config = ExternalDirectoryConfig(
            mode=AuthProviderMode.STANDARD,
            url="ldaps://ldap.example.net",
            base_dn="dc=example,dc=net",
            user_filter="(uid={username})",
            group_filter="(member={user_dn})",
            bind_dn_ref=None,
            bind_password_ref=None,
            ca_cert_ref=None,
            tls_required=True,
            nested_groups=True,
            cache_ttl_seconds=300,
        )
        with pytest.raises(ValidationError):
            LdapIpaDirectoryAuthenticator().authenticate(standard_config, "alice", "secret")
        with pytest.raises(AccessDeniedError):
            LdapIpaDirectoryAuthenticator().authenticate(_config(), "", "secret")

    def test_ldap_authenticator_handles_missing_user_group_and_unbind_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        class BrokenUnbindConnection(_FakeConnection):
            def unbind(self) -> None:
                raise RuntimeError("unbind failed")

        fake = _fake_ldap3()
        fake.Connection = BrokenUnbindConnection
        monkeypatch.setenv("OPENINFRA_LDAP_BIND_DN", "cn=bind,dc=example,dc=net")
        monkeypatch.setenv("OPENINFRA_LDAP_BIND_PASSWORD", "bind-secret")
        sys.modules["ldap3"] = fake
        try:
            with pytest.raises(AccessDeniedError):
                LdapIpaDirectoryAuthenticator().authenticate(_config(), "unknown", "secret")
        finally:
            sys.modules.pop("ldap3", None)

        class NoGroupConnection(_FakeConnection):
            def search(
                self,
                search_base: str,
                search_filter: str,
                attributes: tuple[str, ...],
                size_limit: int,
            ) -> None:
                _ = (search_base, attributes, size_limit)
                if "member=uid=alice" in search_filter:
                    self.entries = []
                    return
                if "uid=alice" in search_filter:
                    self.entries = [
                        _FakeEntry("uid=alice,ou=people,dc=example,dc=net", {"cn": ["alice"]})
                    ]
                    return
                self.entries = []

        fake = _fake_ldap3()
        fake.Connection = NoGroupConnection
        sys.modules["ldap3"] = fake
        try:
            with pytest.raises(AccessDeniedError):
                LdapIpaDirectoryAuthenticator().authenticate(_config(), "alice", "valid-secret")
        finally:
            sys.modules.pop("ldap3", None)

    def test_ldap_authenticator_supports_anonymous_service_bind(self) -> None:
        config = ExternalDirectoryConfig.create(
            mode="ldap",
            url="ldaps://ldap.example.net",
            base_dn="dc=example,dc=net",
            user_filter="(uid={username})",
            group_filter="(member={user_dn})",
        )
        sys.modules["ldap3"] = _fake_ldap3()
        try:
            identity = LdapIpaDirectoryAuthenticator().authenticate(config, "alice", "valid-secret")
        finally:
            sys.modules.pop("ldap3", None)

        assert identity.subject == "alice"
