from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.domain.common import ValidationError
from openinfra.domain.federated_identity import (
    FederatedIdentity,
    FederatedProvider,
    HttpsOrigin,
    SamlProviderConfig,
    TeamSyncGroup,
    TeamSyncSnapshot,
    TeamSyncSourceConfig,
    TeamSyncUser,
)
from openinfra.infrastructure.json_store import (
    JsonDocumentStore,
    JsonReadinessProbe,
    JsonSchemaStatusProvider,
    JsonTransactionManager,
)
from openinfra.infrastructure.oracle import OracleConnectionSettings
from openinfra.infrastructure.runtime_config import (
    RuntimeAdvancedIdentityConfigResolver,
    RuntimeConfig,
    RuntimeConfigLoader,
    RuntimeDatabaseDsnResolver,
    RuntimeSecretResolver,
)
from openinfra.infrastructure.runtime_secrets import (
    RuntimeBootstrapTokenStore,
    RuntimeSecretError,
    RuntimeSecretsCli,
)


class _Loader:
    def __init__(self, values: dict[str, str]) -> None:
        self.runtime = RuntimeConfig(values, None)

    def load(self, explicit_path: Path | None = None) -> RuntimeConfig:
        del explicit_path
        return self.runtime


class TestRuntimeIdentityConfigurationComplete:
    def test_runtime_config_loader_secret_and_dsn_resolution(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text(
            '# comment\nINVALID\n =skip\nKEY="quoted\\\\value\\"x"\nPLAIN=value\n',
            encoding="utf-8",
        )
        loader = RuntimeConfigLoader()
        runtime = loader.load(config)
        assert runtime.source == config
        assert runtime.get("KEY") == 'quoted\\value"x'
        assert runtime.get("PLAIN") == "value"
        assert runtime.get("MISSING", "fallback") == "fallback"
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(config))
        assert loader.load().source == config
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(tmp_path / "missing"))
        assert loader.load().source is None

        resolver = RuntimeSecretResolver()
        assert resolver.resolve("") == ""
        monkeypatch.setenv("RUNTIME_SECRET", "value")
        assert resolver.resolve("env:RUNTIME_SECRET") == "value"
        monkeypatch.delenv("RUNTIME_SECRET")
        with pytest.raises(ValidationError, match="missing environment"):
            resolver.resolve("env:RUNTIME_SECRET")
        secret_file = tmp_path / "secret"
        secret_file.write_text("file-value\n", encoding="utf-8")
        assert resolver.resolve("file://" + str(secret_file)) == "file-value"
        with pytest.raises(ValidationError, match="missing file"):
            resolver.resolve("file://" + str(tmp_path / "absent"))
        with pytest.raises(ValidationError, match="not available"):
            resolver.resolve("vault://secret/openinfra")
        assert resolver.resolve("literal") == "literal"

        dsn = RuntimeDatabaseDsnResolver(
            _Loader(
                {
                    "OPENINFRA_POSTGRES_USER_REF": "literal-user",
                    "OPENINFRA_POSTGRES_PASSWORD_REF": "p@ss word",
                    "OPENINFRA_CURSOR_SIGNING_SECRET_REF": "cursor-secret",
                    "OPENINFRA_READ_CONSISTENCY_SECRET_REF": "consistency-secret",
                }
            ),
            resolver,
        )
        assert dsn.resolve() == "postgresql://literal-user:p%40ss%20word@127.0.0.1:5432/openinfra"
        assert dsn.resolve_cursor_signing_secret() == "cursor-secret"
        assert dsn.resolve_consistency_secret() == "consistency-secret"
        assert dsn.resolve_read_replica("postgresql://replica") == "postgresql://replica"

    def test_advanced_identity_runtime_configuration(self) -> None:
        values = {
            "OPENINFRA_SAML_TENANT_ID": "tenant-a",
            "OPENINFRA_SAML_IDP_ENTITY_ID": "https://idp.example.test/entity",
            "OPENINFRA_SAML_IDP_SSO_URL": "https://idp.example.test/sso",
            "OPENINFRA_SAML_IDP_X509_CERT_REF": "env://SAML_CERT",
            "OPENINFRA_SAML_SP_ENTITY_ID": "https://openinfra.example.test/saml",
            "OPENINFRA_SAML_SP_ACS_URL": "https://openinfra.example.test/api/v1/auth/saml/acs",
            "OPENINFRA_SAML_GROUP_ROLE_MAPPINGS": "cn=Admins,ou=groups,dc=x=admin;cn=Ops,ou=groups,dc=x=operator,viewer",
            "OPENINFRA_LDAP_URL": "ldaps://ldap.example.test",
            "OPENINFRA_LDAP_BASE_DN": "dc=example,dc=test",
            "OPENINFRA_TEAM_SYNC_SOURCES": " LDAP-Main,oauth-main,ldap-main ",
            "OPENINFRA_TEAM_SYNC_LDAP_MAIN_PROVIDER": "ldap",
            "OPENINFRA_TEAM_SYNC_LDAP_MAIN_TENANT_ID": "tenant-a",
            "OPENINFRA_TEAM_SYNC_LDAP_MAIN_GROUP_ROLE_MAPPINGS": "Operators=operator,viewer",
            "OPENINFRA_TEAM_SYNC_LDAP_MAIN_DEACTIVATE_ORPHANS": "false",
        }
        resolver = RuntimeAdvancedIdentityConfigResolver(_Loader(values))
        assert resolver.saml_tenant_id() == "tenant-a"
        assert resolver.saml_config().idp_entity_id.endswith("/entity")
        assert resolver.directory_config().base_dn == "dc=example,dc=test"
        assert resolver.team_sync_sources() == ("ldap-main", "oauth-main")
        source = resolver.team_sync_source("LDAP-Main")
        assert source.provider is FederatedProvider.LDAP
        assert source.deactivate_orphans is False
        assert source.roles_for_external_group("operators") == ("operator", "viewer")
        mappings = resolver.saml_group_role_mappings("tenant-a")
        assert len(mappings) == 2

        with pytest.raises(ValidationError, match="cannot be empty"):
            RuntimeAdvancedIdentityConfigResolver(
                _Loader({"OPENINFRA_SAML_TENANT_ID": " "})
            ).saml_tenant_id()
        for value, message in (("invalid", "must use"), ("group=", "at least one")):
            with pytest.raises(ValidationError, match=message):
                RuntimeAdvancedIdentityConfigResolver._role_mappings(value)
        with pytest.raises(ValidationError, match="must be true or false"):
            RuntimeAdvancedIdentityConfigResolver._bool("yes")

    def test_federated_domain_failure_contracts(self) -> None:
        with pytest.raises(ValidationError, match="unsupported"):
            FederatedProvider.from_value("kerberos")
        for value, message, kwargs in (
            ("http://example.test", "must use https", {}),
            ("https://user:pass@example.test", "credentials", {}),
            ("https://example.test/#fragment", "fragment", {}),
            ("https://example.test/path", "without path", {}),
        ):
            with pytest.raises(ValidationError, match=message):
                HttpsOrigin.normalize(value, "endpoint", **kwargs)
        assert HttpsOrigin.origin("https://example.test:8443/path") == "https://example.test:8443"

        valid = {
            "idp_entity_id": "https://idp.example.test/entity",
            "idp_sso_url": "https://idp.example.test/sso",
            "idp_x509_cert_ref": "env://CERT",
            "sp_entity_id": "https://openinfra.example.test/saml",
            "sp_acs_url": "https://openinfra.example.test/acs",
        }
        with pytest.raises(ValidationError, match="required"):
            SamlProviderConfig.create(**{**valid, "idp_x509_cert_ref": ""})
        with pytest.raises(ValidationError, match="between 0 and 600"):
            SamlProviderConfig.create(**valid, allowed_clock_skew_seconds=601)
        with pytest.raises(ValidationError, match="safe characters"):
            SamlProviderConfig.create(**valid, subject_attribute="bad attribute")
        assert SamlProviderConfig.create(**valid).as_safe_dict()["has_idp_x509_cert_ref"] is True

        with pytest.raises(ValidationError, match="at least one external group"):
            FederatedIdentity.create("saml", "alice", "Alice", None, ())
        with pytest.raises(ValidationError, match="session index"):
            FederatedIdentity.create("saml", "alice", "Alice", None, ("group",), "x" * 513)
        with pytest.raises(ValidationError, match="external group"):
            FederatedIdentity._group("")

        user = TeamSyncUser.create("alice", "Alice")
        group = TeamSyncGroup.create("operators", "Operators", ("viewer",), ("alice",))
        with pytest.raises(ValidationError, match="source_id"):
            TeamSyncSnapshot.create(
                tenant_id="default", source_id="x", provider="ldap", users=(), groups=()
            )
        with pytest.raises(ValidationError, match="unique subjects"):
            TeamSyncSnapshot.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                users=(user, user),
                groups=(),
            )
        with pytest.raises(ValidationError, match="unique names"):
            TeamSyncSnapshot.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                users=(user,),
                groups=(group, group),
            )
        with pytest.raises(ValidationError, match="must exist"):
            TeamSyncSnapshot.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                users=(),
                groups=(group,),
            )
        assert (
            TeamSyncSnapshot.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                users=(user,),
                groups=(group,),
            ).as_dict()["provider"]
            == "ldap"
        )

        with pytest.raises(ValidationError, match="timeout_seconds"):
            TeamSyncSourceConfig.create(
                tenant_id="default", source_id="ldap-main", provider="ldap", timeout_seconds=0
            )
        with pytest.raises(ValidationError, match="page_size"):
            TeamSyncSourceConfig.create(
                tenant_id="default", source_id="ldap-main", provider="ldap", page_size=1001
            )
        with pytest.raises(ValidationError, match="mapping is invalid"):
            TeamSyncSourceConfig.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                group_role_mappings=(("", ("viewer",)),),
            )
        with pytest.raises(ValidationError, match="must be unique"):
            TeamSyncSourceConfig.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                group_role_mappings=(("ops", ("viewer",)), ("OPS", ("operator",))),
            )
        config = TeamSyncSourceConfig.create(
            tenant_id="default", source_id="ldap-main", provider="ldap"
        )
        assert config.roles_for_external_group("missing") == ()

    def test_runtime_secret_store_and_cli(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        uid, gid = os.getuid(), os.getgid()
        path = tmp_path / "secrets" / "bootstrap-token"
        store = RuntimeBootstrapTokenStore(path, uid, gid)
        assert store.ensure() == path
        first = store.read()
        assert first.startswith("oi_")
        assert stat.S_IMODE(path.stat().st_mode) == 0o400
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert store.ensure() == path
        store.rotate()
        assert store.read() != first

        path.chmod(0o440)
        with pytest.raises(RuntimeSecretError, match="permissions"):
            store.read()
        path.chmod(0o400)
        path.write_text("invalid", encoding="utf-8")
        path.chmod(0o400)
        with pytest.raises(RuntimeSecretError, match="invalid format"):
            store.read()

        link = tmp_path / "link"
        link.symlink_to(path)
        with pytest.raises(RuntimeSecretError, match="symlink"):
            RuntimeBootstrapTokenStore(link, uid, gid).read()
        with pytest.raises(RuntimeSecretError, match="cannot open"):
            RuntimeBootstrapTokenStore(tmp_path / "missing", uid, gid).read()

        parent_link = tmp_path / "parent-link"
        parent_link.symlink_to(tmp_path / "secrets", target_is_directory=True)
        with pytest.raises(RuntimeSecretError, match="directory is invalid"):
            RuntimeBootstrapTokenStore(parent_link / "token", uid, gid).ensure()

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "openinfra-runtime-secrets",
                "ensure",
                "--path",
                str(path),
                "--uid",
                str(uid),
                "--gid",
                str(gid),
            ],
        )
        path.unlink()
        assert RuntimeSecretsCli.main() == 0
        assert "ready" in capsys.readouterr().out
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "openinfra-runtime-secrets",
                "rotate",
                "--path",
                str(path),
                "--uid",
                str(uid),
                "--gid",
                str(gid),
            ],
        )
        assert RuntimeSecretsCli.main() == 0
        assert "rotated" in capsys.readouterr().out
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "openinfra-runtime-secrets",
                "get",
                "--path",
                str(path),
                "--uid",
                str(uid),
                "--gid",
                str(gid),
            ],
        )
        assert RuntimeSecretsCli.main() == 0
        assert capsys.readouterr().out.startswith("oi_")
        path.write_text("invalid", encoding="utf-8")
        path.chmod(0o400)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "openinfra-runtime-secrets",
                "show",
                "--path",
                str(path),
                "--uid",
                str(uid),
                "--gid",
                str(gid),
            ],
        )
        assert RuntimeSecretsCli.main() == 1
        assert "invalid format" in capsys.readouterr().err

    def test_oracle_application_factory_wires_native_backend(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        state_path = tmp_path / "oracle-state.json"
        store = JsonDocumentStore(state_path)
        monkeypatch.setattr(
            "openinfra.application.container.OracleDocumentStore", lambda settings: store
        )
        monkeypatch.setattr(
            "openinfra.application.container.OracleTransactionManager",
            JsonTransactionManager,
        )
        monkeypatch.setattr(
            "openinfra.application.container.OracleReadinessProbe",
            lambda value, catalog: JsonReadinessProbe(value),
        )
        monkeypatch.setattr(
            "openinfra.application.container.OracleMigrationExecutor",
            lambda settings, catalog: JsonSchemaStatusProvider(),
        )
        monkeypatch.setattr(
            "openinfra.application.container.OracleMigrationCatalog.from_project_root",
            object,
        )
        monkeypatch.setattr(
            "openinfra.application.container.OpenInfraTelemetry.from_environment",
            lambda **kwargs: SimpleNamespace(record=lambda *args, **kw: None),
        )
        settings = OracleConnectionSettings.create(
            dsn="db/OPENINFRA",
            user="openinfra",
            password="secret",  # noqa: S106
        )
        app = ApplicationFactory().create_oracle_application(settings, seed=True)
        assert app.store is store
        assert app.readiness_probe.check().ready is True
        assert app.schema_status_provider.status_as_dict()["backend"] == "json"
