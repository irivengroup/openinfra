from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from openinfra.application.advanced_identity_services import (
    SamlAuthenticationService,
    SamlLoginCommand,
    TeamSyncCommand,
    TeamSyncService,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.authentication import ExternalDirectoryConfig, ExternalGroupRoleMapping
from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.domain.federated_identity import (
    FederatedIdentity,
    FederatedProvider,
    SamlProviderConfig,
    TeamSyncGroup,
    TeamSyncSnapshot,
    TeamSyncSourceConfig,
    TeamSyncUser,
)
from openinfra.infrastructure.advanced_identity import (
    AuthProxyTeamSyncSource,
    LdapTeamSyncSource,
    OAuthTeamSyncSource,
    Python3SamlAssertionValidator,
    SamlHttpRequestFactory,
    StaticSamlAssertionValidator,
    TeamSyncPayloadParser,
)


class _SecretResolver:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def resolve(self, reference: str) -> str:
        return self.values[reference]


def _saml_config(cert_ref: str = "env://SAML_CERT") -> SamlProviderConfig:
    return SamlProviderConfig.create(
        idp_entity_id="https://idp.example.test/entity",
        idp_sso_url="https://idp.example.test/sso",
        idp_x509_cert_ref=cert_ref,
        sp_entity_id="https://openinfra.example.test/saml",
        sp_acs_url="https://openinfra.example.test/api/v1/auth/saml/acs",
    )


def _identity(provider: str = "saml") -> FederatedIdentity:
    return FederatedIdentity.create(
        provider=provider,
        subject="alice",
        display_name="Alice Example",
        email="alice@example.test",
        external_groups=("cn=openinfra admins,ou=groups,dc=example,dc=test",),
        session_index="session-1",
    )


class _FakeSamlAuth:
    errors: list[str] = []
    authenticated = True
    reason = ""
    attributes: dict[str, list[str]] = {
        "uid": ["alice"],
        "displayName": ["Alice Example"],
        "mail": ["alice@example.test"],
        "groups": [
            "cn=OpenInfra Admins,ou=groups,dc=example,dc=test",
            "cn=Operators,ou=groups,dc=example,dc=test",
        ],
    }

    def __init__(self, request_data: dict[str, object], settings: dict[str, object]) -> None:
        self.request_data = request_data
        self.settings = settings

    def process_response(self) -> None:
        return None

    def get_errors(self) -> list[str]:
        return self.errors

    def is_authenticated(self) -> bool:
        return self.authenticated

    def get_last_error_reason(self) -> str:
        return self.reason

    def get_attributes(self) -> dict[str, list[str]]:
        return self.attributes

    def get_nameid(self) -> str:
        return "fallback-name-id"

    def get_session_index(self) -> str:
        return "session-index"


class _FakeDirectoryAuthenticator:
    def __init__(self, connection: Any) -> None:
        self.connection = connection
        self.unbound = False

    def _load_ldap3(self) -> object:
        return object()

    def _server(self, ldap3: object, directory: ExternalDirectoryConfig) -> object:
        del ldap3, directory
        return object()

    def _service_connection(
        self, ldap3: object, server: object, directory: ExternalDirectoryConfig
    ) -> Any:
        del ldap3, server, directory
        return self.connection

    def _safe_unbind(self, connection: Any) -> None:
        assert connection is self.connection
        self.unbound = True


class _StaticSource:
    def __init__(self, snapshot: TeamSyncSnapshot) -> None:
        self.snapshot = snapshot

    def fetch(self, config: TeamSyncSourceConfig) -> TeamSyncSnapshot:
        assert config.source_id == self.snapshot.source_id
        return self.snapshot


class TestAdvancedIdentityComplete:
    def test_static_and_python_saml_validators_cover_success_and_rejection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        static = StaticSamlAssertionValidator(_identity())
        with pytest.raises(AccessDeniedError, match="SAMLResponse"):
            static.validate(_saml_config(), {"post_data": {}})
        assert (
            static.validate(_saml_config(), {"post_data": {"SAMLResponse": "signed"}}).subject
            == "alice"
        )

        original_load_auth_class = Python3SamlAssertionValidator._load_auth_class
        monkeypatch.setattr(
            Python3SamlAssertionValidator,
            "_load_auth_class",
            staticmethod(lambda: _FakeSamlAuth),
        )
        validator = Python3SamlAssertionValidator(
            _SecretResolver(
                {"env://SAML_CERT": "-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----"}
            )
        )
        result = validator.validate(_saml_config(), {"post_data": {"SAMLResponse": "x"}})
        assert result.subject == "alice"
        assert result.external_groups == (
            "cn=OpenInfra Admins,ou=groups,dc=example,dc=test",
            "cn=Operators,ou=groups,dc=example,dc=test",
        )

        _FakeSamlAuth.errors = ["invalid_signature"]
        _FakeSamlAuth.authenticated = False
        _FakeSamlAuth.reason = "signature rejected"
        with pytest.raises(AccessDeniedError, match="signature rejected"):
            validator.validate(_saml_config(), {"post_data": {"SAMLResponse": "x"}})
        _FakeSamlAuth.errors = []
        _FakeSamlAuth.authenticated = True
        _FakeSamlAuth.reason = ""

        cert = tmp_path / "idp.pem"
        cert.write_text(
            "-----BEGIN CERTIFICATE-----\nY\n-----END CERTIFICATE-----", encoding="utf-8"
        )
        settings = Python3SamlAssertionValidator(
            _SecretResolver({"file://cert": str(cert)})
        )._settings(_saml_config("file://cert"))
        assert "BEGIN CERTIFICATE" in str(settings["idp"])
        with pytest.raises(ValidationError, match="did not resolve"):
            Python3SamlAssertionValidator(
                _SecretResolver({"file://missing": str(tmp_path / "missing.pem")})
            )._settings(_saml_config("file://missing"))

        monkeypatch.setattr(
            Python3SamlAssertionValidator,
            "_load_auth_class",
            staticmethod(original_load_auth_class),
        )
        original_import = __import__("importlib").import_module
        monkeypatch.setattr(
            "openinfra.infrastructure.advanced_identity.importlib.import_module",
            lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
        )
        with pytest.raises(ValidationError, match="python3-saml"):
            Python3SamlAssertionValidator._load_auth_class()
        monkeypatch.setattr(
            "openinfra.infrastructure.advanced_identity.importlib.import_module", original_import
        )

    def test_payload_parser_request_factory_and_validation_branches(self) -> None:
        parser = TeamSyncPayloadParser()
        config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="oauth-main",
            provider="oauth",
            endpoint="https://identity.example.test/sync",
            token_ref="env://TOKEN",  # noqa: S106
            group_role_mappings=(("Operators", ("viewer",)),),
        )
        snapshot = parser.parse(
            config,
            {
                "users": [{"username": "alice", "displayName": "Alice"}],
                "groups": [{"id": "Operators", "members": ["alice"]}],
            },
        )
        assert snapshot.groups[0].roles == ("viewer",)
        assert snapshot.groups[0].name.startswith("sync-oauth-main-")
        assert TeamSyncPayloadParser._managed_group_name("oauth-main", "###").startswith(
            "sync-oauth-main-"
        )
        for payload, message in (
            ([], "JSON object"),
            ({"users": {}, "groups": []}, "must be arrays"),
            ({"users": ["bad"], "groups": []}, "user entries"),
            (
                {"users": [], "groups": ["bad"]},
                "group entries",
            ),
            (
                {"users": [], "groups": [{"name": "g", "roles": {}, "members": []}]},
                "roles and members",
            ),
        ):
            with pytest.raises(ValidationError, match=message):
                parser.parse(config, payload)

        request = SamlHttpRequestFactory.create(
            host="openinfra.example.test",
            path="/acs",
            query_string="relay=one&relay=two&empty=",
            form_data={"SAMLResponse": "x"},
            forwarded_proto="http",
            remote_addr="192.0.2.10",
        )
        assert request["https"] == "off"
        assert request["server_port"] == "80"
        assert request["get_data"] == {"relay": "two"}

    def test_oauth_and_okta_sources_cover_transport_and_validation(self) -> None:
        oauth_config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="oauth-main",
            provider="oauth",
            endpoint="https://identity.example.test/sync",
            token_ref="env://TOKEN",  # noqa: S106
        )

        def invalid_handler(request: httpx.Request) -> httpx.Response:
            del request
            return httpx.Response(200, json=[])

        with (
            httpx.Client(transport=httpx.MockTransport(invalid_handler)) as client,
            pytest.raises(ValidationError, match="JSON object"),
        ):
            OAuthTeamSyncSource(_SecretResolver({"env://TOKEN": "secret"}), client).fetch(
                oauth_config
            )

        def invalid_arrays(request: httpx.Request) -> httpx.Response:
            del request
            return httpx.Response(200, json={"users": {}, "groups": []})

        with (
            httpx.Client(transport=httpx.MockTransport(invalid_arrays)) as client,
            pytest.raises(ValidationError, match="arrays are invalid"),
        ):
            OAuthTeamSyncSource(_SecretResolver({"env://TOKEN": "secret"}), client).fetch(
                oauth_config
            )

        okta_config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="okta-main",
            provider="okta",
            endpoint="https://okta.example.test",
            token_ref="env://OKTA",  # noqa: S106
            page_size=2,
            group_role_mappings=(("Administrators", ("admin",)),),
        )

        def okta_handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/v1/users":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "u1",
                            "status": "ACTIVE",
                            "profile": {
                                "login": "alice",
                                "firstName": "Alice",
                                "lastName": "Admin",
                                "email": "alice@example.test",
                            },
                        },
                        {"id": "user-two", "status": "SUSPENDED", "profile": "invalid"},
                        "ignored",
                    ],
                )
            if path == "/api/v1/groups":
                return httpx.Response(
                    200,
                    json=[
                        {"id": "g1", "profile": {"name": "Administrators"}},
                        "ignored",
                    ],
                )
            if path == "/api/v1/groups/g1/users":
                return httpx.Response(200, json=[{"id": "u1"}, {"id": "user-two"}])
            raise AssertionError(str(request.url))

        with httpx.Client(transport=httpx.MockTransport(okta_handler)) as client:
            snapshot = OAuthTeamSyncSource(
                _SecretResolver({"env://OKTA": "okta-token"}), client
            ).fetch(okta_config)
        assert [user.subject for user in snapshot.users] == ["alice", "user-two"]
        assert snapshot.users[1].active is False
        assert snapshot.groups[0].members == ("alice", "user-two")
        assert OAuthTeamSyncSource._okta_next_link(
            '<https://okta.example.test/api/v1/users?page=2>; rel="next"'
        ).endswith("page=2")
        assert OAuthTeamSyncSource._okta_next_link("invalid; rel=previous") is None

        ldap_config = TeamSyncSourceConfig.create(
            tenant_id="default", source_id="ldap-main", provider="ldap"
        )
        with pytest.raises(ValidationError, match="oauth or okta"):
            OAuthTeamSyncSource(_SecretResolver({})).fetch(ldap_config)

    def test_auth_proxy_and_ldap_sources_cover_all_adapters(self, tmp_path: Path) -> None:
        ldap_config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="ldap-main",
            provider="ldap",
            group_role_mappings=(("Operators", ("operator",)),),
        )
        rows = [
            {
                "type": "searchResEntry",
                "dn": "uid=alice,ou=people,dc=example,dc=test",
                "attributes": {
                    "uid": ["alice"],
                    "displayName": ["Alice"],
                    "mail": ["alice@example.test"],
                },
            },
            {"type": "searchResRef", "dn": "ignored", "attributes": {}},
        ]
        group_rows = [
            {
                "type": "searchResEntry",
                "dn": "cn=Operators,ou=groups,dc=example,dc=test",
                "attributes": {
                    "cn": ["Operators"],
                    "member": ["uid=alice,ou=people,dc=example,dc=test"],
                },
            }
        ]
        calls = 0

        def paged_search(**kwargs: object) -> list[dict[str, object]]:
            nonlocal calls
            calls += 1
            assert kwargs["generator"] is False
            return rows if calls == 1 else group_rows

        connection = SimpleNamespace(
            extend=SimpleNamespace(standard=SimpleNamespace(paged_search=paged_search))
        )
        authenticator = _FakeDirectoryAuthenticator(connection)
        directory = ExternalDirectoryConfig.create(
            mode="ldap",
            url="ldaps://ldap.example.test",
            base_dn="dc=example,dc=test",
            user_filter="(uid={username})",
            group_filter="(member={user_dn})",
        )
        snapshot = LdapTeamSyncSource(directory, authenticator).fetch(ldap_config)
        assert snapshot.users[0].subject == "alice"
        assert snapshot.groups[0].members == ("alice",)
        assert authenticator.unbound is True

        fallback_entries = [
            SimpleNamespace(
                entry_dn="uid=bob,ou=people,dc=example,dc=test",
                entry_attributes_as_dict={"uid": ["bob"]},
            )
        ]
        fallback = SimpleNamespace(entries=fallback_entries)
        fallback.search = lambda **kwargs: kwargs  # type: ignore[attr-defined]
        assert (
            LdapTeamSyncSource(directory, _FakeDirectoryAuthenticator(fallback))
            ._paged_search(fallback, "dc=example,dc=test", "(uid=*)", ("uid",), 10, 20)[0]["dn"]
            .startswith("uid=bob")
        )
        assert LdapTeamSyncSource._attributes({"attributes": []}) == {}
        assert LdapTeamSyncSource._first_value([]) is None
        assert LdapTeamSyncSource._first_value([" value "]) == "value"
        with pytest.raises(ValidationError, match="requires ldap"):
            LdapTeamSyncSource(directory, authenticator).fetch(
                TeamSyncSourceConfig.create(
                    tenant_id="default",
                    source_id="oauth-main",
                    provider="oauth",
                    endpoint="https://identity.example.test/sync",
                    token_ref="env://TOKEN",  # noqa: S106
                )
            )

        payload = {"users": [], "groups": []}
        secret = "example-auth-proxy-secret"
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        snapshot_file = tmp_path / "snapshot.json"
        snapshot_file.write_text(
            json.dumps(
                {
                    "payload": payload,
                    "signature": hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        auth_config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="proxy-main",
            provider="auth_proxy",
            snapshot_file=str(snapshot_file),
            signature_secret_ref="env://PROXY_SECRET",  # noqa: S106
        )
        assert (
            AuthProxyTeamSyncSource(_SecretResolver({"env://PROXY_SECRET": secret}))
            .fetch(auth_config)
            .provider
            is FederatedProvider.AUTH_PROXY
        )
        snapshot_file.write_text("[]", encoding="utf-8")
        with pytest.raises(ValidationError, match="JSON object"):
            AuthProxyTeamSyncSource(_SecretResolver({"env://PROXY_SECRET": secret})).fetch(
                auth_config
            )
        with pytest.raises(ValidationError, match="requires auth_proxy"):
            AuthProxyTeamSyncSource(_SecretResolver({})).fetch(ldap_config)

    def test_saml_and_team_sync_services_end_to_end(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(
            tmp_path / "state.json", edition="enterprise"
        )
        mapping = ExternalGroupRoleMapping.create(
            tenant_id="default",
            provider="saml",
            external_group="cn=OpenInfra Admins,ou=groups,dc=example,dc=test",
            roles=("admin",),
        )
        saml = SamlAuthenticationService(
            StaticSamlAssertionValidator(_identity()),
            app.identity_service,
            app.security_service,
            app.audit_repository,
            app.transaction_manager,
        )
        login = saml.login(
            SamlLoginCommand(
                tenant_id="default",
                edition="enterprise",
                actor="browser",
                request_data={"post_data": {"SAMLResponse": "signed"}},
                provider_config=_saml_config(),
                mappings=(mapping,),
            )
        )
        assert login.subject == "alice"
        assert login.roles == ("admin",)
        assert login.token.startswith("oi_")

        with pytest.raises(ValidationError, match="Lite edition"):
            saml.login(
                SamlLoginCommand(
                    tenant_id="default",
                    edition="lite",
                    actor="browser",
                    request_data={"post_data": {"SAMLResponse": "signed"}},
                    provider_config=_saml_config(),
                    mappings=(mapping,),
                )
            )
        no_mapping = SamlAuthenticationService(
            StaticSamlAssertionValidator(_identity()),
            app.identity_service,
            app.security_service,
            app.audit_repository,
            app.transaction_manager,
        )
        with pytest.raises(AccessDeniedError, match="no OpenInfra RBAC"):
            no_mapping.login(
                SamlLoginCommand(
                    tenant_id="default",
                    edition="enterprise",
                    actor="browser",
                    request_data={"post_data": {"SAMLResponse": "signed"}},
                    provider_config=_saml_config(),
                    mappings=(),
                )
            )

        admin = app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="admin",
                roles=("admin",),
                token="a" * 40,
            )
        )
        assert admin.token_prefix == "a" * 12
        config = TeamSyncSourceConfig.create(
            tenant_id="default", source_id="ldap-main", provider="ldap"
        )
        snapshot = TeamSyncSnapshot.create(
            tenant_id="default",
            source_id="ldap-main",
            provider="ldap",
            users=(TeamSyncUser.create("bob", "Bob", "bob@example.test"),),
            groups=(
                TeamSyncGroup.create(
                    "sync-ldap-main-operators", "Operators", ("viewer",), ("bob",)
                ),
            ),
        )
        service = TeamSyncService(
            app.identity_repository,
            app.audit_repository,
            app.transaction_manager,
            app.security_service,
        )
        service.register_source(FederatedProvider.LDAP, _StaticSource(snapshot))
        result = service.synchronize(
            TeamSyncCommand(
                tenant_id="default",
                actor="pytest",
                admin_token="a" * 40,
                source_config=config,
            )
        )
        assert result["provider"] == "ldap"
        assert result["created_users"] == 1

        missing = TeamSyncService(
            app.identity_repository,
            app.audit_repository,
            app.transaction_manager,
            app.security_service,
        )
        with pytest.raises(ValidationError, match="no team sync source"):
            missing.synchronize(
                TeamSyncCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token="a" * 40,
                    source_config=config,
                )
            )
        other_config = TeamSyncSourceConfig.create(
            tenant_id="other", source_id="ldap-main", provider="ldap"
        )
        with pytest.raises(ValidationError, match="tenant mismatch"):
            service.synchronize(
                TeamSyncCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token="a" * 40,
                    source_config=other_config,
                    snapshot=snapshot,
                )
            )
        wrong_snapshot = TeamSyncSnapshot.create(
            tenant_id="default",
            source_id="other-source",
            provider="ldap",
            users=(),
            groups=(),
        )
        with pytest.raises(ValidationError, match="does not match"):
            service.synchronize(
                TeamSyncCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token="a" * 40,
                    source_config=config,
                    snapshot=wrong_snapshot,
                )
            )
