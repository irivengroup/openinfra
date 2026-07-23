from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import openinfra.interfaces.cli as cli_module
from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.domain.federated_identity import FederatedProvider, TeamSyncSourceConfig
from openinfra.infrastructure.oracle import OracleConnectionSettings
from openinfra.interfaces.cli import OpenInfraCLI


class _Payload:
    def __init__(self, **payload: object) -> None:
        self._payload = payload

    def as_dict(self) -> dict[str, object]:
        return dict(self._payload)

    def as_public_dict(self) -> dict[str, object]:
        return {**self._payload, "credential_secret_ref": "vault://***"}


class _Policy(_Payload):
    pass


class _Page:
    def __init__(self, item: _Payload | None = None) -> None:
        self._item = item or _Payload(id="item-1")

    def as_dict(self) -> dict[str, object]:
        return {"items": [self._item.as_dict()], "next_cursor": None}


class _ExternalItsmService:
    def list_policies(self) -> list[_Policy]:
        return [_Policy(provider="servicenow")]


class _ItamSupportService:
    def get_tenant(self, _command: object) -> _Payload:
        return _Payload(id="tenant-1", name="Filiale")

    def update_tenant(self, _command: object) -> _Payload:
        return _Payload(id="tenant-1", status="active")

    def delete_tenant(self, _command: object) -> _Payload:
        return _Payload(id="tenant-1", status="retired")

    def get_software_license(self, _command: object) -> _Payload:
        return _Payload(license_reference="LIC-1")


class _DiscoveryService:
    def submit_evidence(self, _command: object) -> _Payload:
        return _Payload(id="evidence-1", object_key="device/srv1")

    def get_evidence(self, _command: object) -> _Payload:
        return _Payload(id="evidence-1", object_key="device/srv1")

    def list_evidence(self, _command: object) -> _Page:
        return _Page(_Payload(id="evidence-1", object_key="device/srv1"))

    def reconcile_evidence(self, _command: object) -> _Payload:
        return _Payload(id="case-1", status="open")

    def get_reconciliation(self, _command: object) -> _Payload:
        return _Payload(id="case-1", status="open")

    def list_reconciliations(self, _command: object) -> _Page:
        return _Page(_Payload(id="case-1", status="open"))

    def resolve_reconciliation(self, _command: object) -> _Payload:
        return _Payload(id="case-1", status="resolved")

    def get_protocol_profile(self, _command: object) -> _Payload:
        return _Payload(id="protocol-1", protocol="snmp")

    def list_protocol_profiles(self, _command: object) -> _Page:
        return _Page(_Payload(id="protocol-1", protocol="snmp"))

    def disable_protocol_profile(self, _command: object) -> _Payload:
        return _Payload(id="protocol-1", status="disabled")

    def get_integration_profile(self, _command: object) -> _Payload:
        return _Payload(id="integration-1", kind="vmware")

    def disable_collector(self, _command: object) -> _Payload:
        return _Payload(id="collector-1", status="disabled")


class _RsotService:
    def upsert_object(self, _command: object) -> dict[str, object]:
        return {"key": "device/srv1", "changed": True}

    def get_object_as_of(self, _command: object) -> dict[str, object]:
        return {"key": "device/srv1", "as_of": "2026-07-09T00:00:00Z"}

    def list_object_audit(self, _command: object) -> _Page:
        return _Page(_Payload(key="device/srv1"))


class _IpamModelService:
    def capacity(self, _command: object) -> _Payload:
        return _Payload(prefix="10.0.0.0/24")

    def define_vlan_group(self, _command: object) -> dict[str, object]:
        return {"name": "DC", "scope": "site/par1"}


class _DcimTopologyService:
    def create_floor(self, _command: object) -> dict[str, object]:
        return {"status": "operator_floor_crud_disabled", "operation": "create"}

    def update_floor(self, _command: object) -> dict[str, object]:
        return {"status": "operator_floor_crud_disabled", "operation": "update"}

    def delete_floor(self, _command: object) -> dict[str, object]:
        return {"status": "operator_floor_crud_disabled", "operation": "delete"}


class _Application:
    def __init__(self) -> None:
        self.external_itsm_service = _ExternalItsmService()
        self.itam_support_service = _ItamSupportService()
        self.discovery_service = _DiscoveryService()
        self.rsot_service = _RsotService()
        self.ipam_model_service = _IpamModelService()
        self.dcim_topology_service = _DcimTopologyService()


def _args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        actor="pytest",
        admin_token="a" * 40,
        as_of="2026-07-09T00:00:00Z",
        relation_limit=100,
        backend="json",
        building="BAT-A",
        clear_default=False,
        code="L01",
        cursor=None,
        collector_id="collector-1",
        confidence="0.95",
        case_id="case-1",
        data=tmp_path / "state.json",
        description="test",
        edition="enterprise",
        evidence_id="evidence-1",
        external_id="external-1",
        group_name="group",
        idempotency_key="req-1",
        include_inactive=True,
        kind="device",
        display_name="Server",
        attributes_json="{}",
        tag=["dc"],
        source="manual",
        resource_category="server",
        resource_type="physical-server",
        is_default=True,
        key="device/srv1",
        license_reference="LIC-1",
        limit=10,
        level_index=1,
        max_age_seconds=3600,
        name="Name",
        object_key="device/srv1",
        object_kind="device",
        observed_at="2026-07-12T12:00:00Z",
        organization="ORG-1",
        payload_json='{"hostname":"srv1"}',
        postgres_dsn=None,
        prefix="10.0.0.0/24",
        profile_id="profile-1",
        reason="rotated",
        root=None,
        scope="site/par1",
        scope_tenant="filiale-1",
        selections_json='{"hostname":"evidence-1"}',
        source_ref="collector/par1",
        site="PAR1",
        status="open",
        tenant="default",
        justification="operator-reviewed evidence",
        username="user",
        vrf="default",
    )


def _install_fake_application(cli: OpenInfraCLI, app: _Application) -> None:
    cli._create_application = lambda args: app  # type: ignore[method-assign]


def test_cli_direct_handlers_cover_operator_read_disable_paths(
    tmp_path: Path, capsys: object
) -> None:
    cli = OpenInfraCLI()
    _install_fake_application(cli, _Application())
    args = _args(tmp_path)

    handlers = (
        cli._handle_integrations_itsm_providers,
        cli._handle_itam_tenant,
        cli._handle_itam_tenant_update,
        cli._handle_itam_tenant_delete,
        cli._handle_itam_software_license,
        cli._handle_discovery_protocol_profile_get,
        cli._handle_discovery_protocol_profile_list,
        cli._handle_discovery_protocol_profile_delete,
        cli._handle_discovery_integration_profile_get,
        cli._handle_discovery_collector_disable,
        cli._handle_ipam_capacity,
        cli._handle_ipam_define_vlan_group,
        cli._handle_dcim_floor_create,
        cli._handle_dcim_floor_update,
        cli._handle_dcim_floor_delete,
    )
    for handler in handlers:
        assert handler(args) == 0
        assert capsys.readouterr().out.strip()


def test_cli_direct_handlers_cover_canonical_rsot_paths(tmp_path: Path, capsys: object) -> None:
    cli = OpenInfraCLI()
    _install_fake_application(cli, _Application())
    args = _args(tmp_path)

    assert cli._handle_rsot_resource_taxonomy(args) == 0
    assert "categories" in json.loads(capsys.readouterr().out)
    assert cli._handle_rsot_upsert_object(args) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True
    assert cli._handle_rsot_get_object_as_of(args) == 0
    assert json.loads(capsys.readouterr().out)["key"] == "device/srv1"
    assert cli._handle_rsot_list_object_audit(args) == 0
    assert json.loads(capsys.readouterr().out)["items"]


def test_cli_runtime_resolution_edges(tmp_path: Path, monkeypatch: object) -> None:
    cli = OpenInfraCLI()
    explicit = SimpleNamespace(root=tmp_path / "migrations")
    assert cli._resolve_migration_root(explicit) == tmp_path / "migrations"
    assert cli._resolve_oracle_migration_catalog(explicit).root == tmp_path / "migrations"
    runtime_args = SimpleNamespace(root=None)
    runtime_config = tmp_path / "openinfra.conf"
    runtime_config.write_text(
        "OPENINFRA_MIGRATIONS_ROOT=" + str(tmp_path / "runtime-migrations") + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(runtime_config))
    assert cli._resolve_migration_root(runtime_args) == tmp_path / "runtime-migrations"
    assert (
        cli._resolve_oracle_migration_catalog(runtime_args).root == tmp_path / "runtime-migrations"
    )

    monkeypatch.delenv("OPENINFRA_RUNTIME_CONFIG")
    assert cli._resolve_migration_root(runtime_args) == Path("installers/migrations/postgresql")
    assert cli._resolve_oracle_migration_catalog(runtime_args).root == Path(
        "installers/migrations/oracle"
    )
    assert cli._packaged_migration_root().as_posix().endswith("openinfra/migrations/postgresql")

    monkeypatch.chdir(tmp_path)
    packaged_root = tmp_path / "installed-openinfra" / "migrations" / "postgresql"
    packaged_root.mkdir(parents=True)
    monkeypatch.setattr(cli, "_packaged_migration_root", lambda: packaged_root)
    assert cli._resolve_migration_root(runtime_args) == packaged_root
    packaged_root.rmdir()
    assert cli._resolve_migration_root(runtime_args) == Path("installers/migrations/postgresql")


def test_cli_main_fail_fast_and_single_installer_file_validation(
    monkeypatch: object, capsys: object
) -> None:
    monkeypatch.setattr(sys, "argv", ["openinfra", "version"])
    assert OpenInfraCLI.main() == 0
    assert capsys.readouterr().out.strip()

    cli = OpenInfraCLI()
    with pytest.raises(OpenInfraError, match="expected failure"):
        cli.fail_fast("expected failure")

    args = SimpleNamespace(
        path=Path("installers/setup/enterprise/server/install.ini"),
        edition="enterprise",
        scope="server",
        root=Path("installers/setup"),
    )
    assert cli._handle_installer_validate(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True


def test_cli_direct_handlers_cover_discovery_reconciliation_lifecycle(
    tmp_path: Path, capsys: object
) -> None:
    cli = OpenInfraCLI()
    _install_fake_application(cli, _Application())
    args = _args(tmp_path)

    handlers = (
        cli._handle_discovery_evidence_submit,
        cli._handle_discovery_evidence_get,
        cli._handle_discovery_evidence_list,
        cli._handle_discovery_reconcile,
        cli._handle_discovery_reconciliation_get,
        cli._handle_discovery_reconciliation_list,
        cli._handle_discovery_reconciliation_resolve,
    )
    for handler in handlers:
        assert handler(args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload


def test_cli_json_object_parser_rejects_invalid_or_non_object_payloads() -> None:
    cli = OpenInfraCLI()

    assert cli._parse_json_object('{"key":"value"}', "payload") == {"key": "value"}
    with pytest.raises(Exception, match="must contain valid JSON"):
        cli._parse_json_object("{", "payload")
    with pytest.raises(Exception, match="must be a JSON object"):
        cli._parse_json_object("[]", "payload")


class _UniversalResult(_Payload):
    content = b"openinfra-export\n"

    def export(self, _format: str) -> tuple[str, str]:
        return "text/plain", "openinfra-export\n"


class _UniversalService:
    def __getattr__(self, _name: str) -> object:
        def operation(*_args: object, **_kwargs: object) -> _UniversalResult:
            return _UniversalResult(id="result-1", status="ok")

        return operation


class _TeamSyncService:
    def synchronize(self, _command: object) -> dict[str, object]:
        return {"status": "synchronized"}


class _SamlService:
    def login(self, _command: object) -> _UniversalResult:
        return _UniversalResult(subject="alice", status="authenticated")


class _IpamUiService:
    def render_dashboard_html(self, _command: object) -> str:
        return "<main>IPAM</main>"

    def dashboard(self, _command: object) -> _UniversalResult:
        return _UniversalResult(status="ok")


class _BroadApplication(_Application):
    def __init__(self) -> None:
        super().__init__()
        self.network_config_compliance_service = _UniversalService()
        self.kubernetes_topology_service = _UniversalService()
        self.rag_service = _UniversalService()
        self.sbom_service = _UniversalService()
        self.greenops_service = _UniversalService()
        self.finops_service = _UniversalService()
        self.saml_authentication_service = _SamlService()
        self.team_sync_service = _TeamSyncService()
        self.ipam_ui_service = _IpamUiService()


def test_cli_oracle_migration_handlers_and_runtime_factories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = OpenInfraCLI()

    class FakeOracleExecutor:
        def status_as_dict(self) -> dict[str, object]:
            return {"backend": "oracle", "pending": 60}

        def apply_all(self) -> dict[str, object]:
            return {"backend": "oracle", "applied": 60}

    monkeypatch.setattr(cli_module, "OracleMigrationExecutor", FakeOracleExecutor)
    cli._create_migration_executor = lambda _args: FakeOracleExecutor()  # type: ignore[method-assign]
    args = SimpleNamespace(dry_run=True)
    assert cli._handle_database_apply_migrations(args) == 0
    assert json.loads(capsys.readouterr().out)["pending"] == 60
    args.dry_run = False
    assert cli._handle_database_apply_migrations(args) == 0
    assert json.loads(capsys.readouterr().out)["applied"] == 60

    cli = OpenInfraCLI()

    class BackendResolver:
        selected = "oracle"

        def resolve(self, _explicit: object, _edition: object = None) -> str:
            return self.selected

    backend_resolver = BackendResolver()
    settings = OracleConnectionSettings.create(
        dsn="db.example.test:1521/OPENINFRA", user="OPENINFRA", password=tmp_path.name
    )

    class OracleResolver:
        value: object = settings

        def resolve(self, **_kwargs: object) -> object:
            return self.value

    oracle_resolver = OracleResolver()
    monkeypatch.setattr(cli_module, "RuntimeDatabaseBackendResolver", lambda: backend_resolver)
    monkeypatch.setattr(cli_module, "RuntimeOracleSettingsResolver", lambda: oracle_resolver)
    monkeypatch.setattr(cli, "_resolve_oracle_migration_catalog", lambda _args: object())
    monkeypatch.setattr(cli_module, "OracleMigrationExecutor", lambda *_args: "oracle-executor")
    factory_args = SimpleNamespace(
        backend="oracle", oracle_dsn=None, oracle_user=None, root=tmp_path
    )
    assert cli._create_migration_executor(factory_args) == "oracle-executor"

    oracle_resolver.value = object()
    with pytest.raises(OpenInfraError, match="invalid Oracle runtime settings"):
        cli._create_migration_executor(factory_args)
    backend_resolver.selected = "sqlite"
    with pytest.raises(ValidationError, match="postgresql or oracle"):
        cli._create_migration_executor(factory_args)

    backend_resolver.selected = "postgresql"
    monkeypatch.setattr(
        cli_module,
        "RuntimeDatabaseDsnResolver",
        lambda: SimpleNamespace(resolve=lambda _dsn: "postgresql://db"),
    )
    monkeypatch.setattr(cli_module, "PostgreSQLSessionRegistry", lambda value: ("registry", value))
    monkeypatch.setattr(cli_module, "PostgreSQLConnectionFactory", lambda dsn: ("factory", dsn))
    monkeypatch.setattr(cli_module, "PostgreSQLMigrationCatalog", lambda root: ("catalog", root))
    monkeypatch.setattr(
        cli_module, "PostgreSQLMigrationExecutor", lambda registry, catalog: (registry, catalog)
    )
    monkeypatch.setattr(cli, "_resolve_migration_root", lambda _args: tmp_path)
    result = cli._create_migration_executor(
        SimpleNamespace(backend="postgresql", postgres_dsn=None)
    )
    assert result[0][0] == "registry"
    assert result[1] == ("catalog", tmp_path)


def test_cli_application_factory_backend_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = OpenInfraCLI()

    class BackendResolver:
        selected = "json"

        def resolve(self, _explicit: object, _edition: object = None) -> str:
            return self.selected

    class Factory:
        def create_json_application(
            self, path: Path, *, seed: bool, edition: str
        ) -> tuple[object, ...]:
            return "json", path, seed, edition

        def create_oracle_application(
            self, settings: OracleConnectionSettings, *, seed: bool, edition: str
        ) -> tuple[object, ...]:
            return "oracle", settings, seed, edition

        def create_postgresql_application(
            self, dsn: str, *, seed: bool, edition: str
        ) -> tuple[object, ...]:
            return "postgresql", dsn, seed, edition

    backend = BackendResolver()
    factory = Factory()
    settings = OracleConnectionSettings.create(dsn="db/service", user="app", password=tmp_path.name)
    oracle = SimpleNamespace(value=settings, resolve=lambda **_kwargs: oracle.value)
    dsn = SimpleNamespace(value="postgresql://db", resolve=lambda _explicit: dsn.value)
    monkeypatch.setattr(cli_module, "RuntimeDatabaseBackendResolver", lambda: backend)
    monkeypatch.setattr(cli_module, "RuntimeOracleSettingsResolver", lambda: oracle)
    monkeypatch.setattr(cli_module, "RuntimeDatabaseDsnResolver", lambda: dsn)
    monkeypatch.setattr(cli_module, "ApplicationFactory", lambda: factory)
    args = SimpleNamespace(
        backend="json",
        data=tmp_path / "state.json",
        edition="pro",
        oracle_dsn=None,
        oracle_user=None,
        postgres_dsn=None,
    )
    assert cli._create_application(args, enforce_license=False) == (
        "json",
        args.data,
        True,
        "pro",
    )
    backend.selected = "oracle"
    assert cli._create_application(args, enforce_license=False)[0] == "oracle"
    oracle.value = object()
    with pytest.raises(OpenInfraError, match="invalid Oracle runtime settings"):
        cli._create_application(args, enforce_license=False)
    oracle.value = settings
    backend.selected = "postgresql"
    assert cli._create_application(args, enforce_license=False)[0] == "postgresql"
    dsn.value = ""
    with pytest.raises(OpenInfraError, match="required for postgresql backend"):
        cli._create_application(args, enforce_license=False)


def test_cli_invalid_ha_auth_policy_and_saml_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = OpenInfraCLI()
    report = SimpleNamespace(valid=False, as_dict=lambda: {"valid": False})
    monkeypatch.setattr(
        cli_module,
        "InstallerConfigValidator",
        lambda: SimpleNamespace(validate_file=lambda *_args: report),
    )
    assert (
        cli._handle_database_ha_plan(
            SimpleNamespace(path=tmp_path, edition="enterprise", scope="server")
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["valid"] is False

    with pytest.raises(OpenInfraError, match="requires --url and --base-dn"):
        cli._handle_auth_policy(SimpleNamespace(mode="ldap", url=None, base_dn=None))

    request_path = tmp_path / "saml.json"
    request_path.write_text("[]", encoding="utf-8")
    args = SimpleNamespace(request_json=request_path)
    with pytest.raises(ValidationError, match="JSON object"):
        cli._handle_auth_saml_login(args)

    request_path.write_text('{"SAMLResponse":"assertion"}', encoding="utf-8")
    resolver = SimpleNamespace(saml_config=object, saml_group_role_mappings=lambda _tenant: ())
    monkeypatch.setattr(cli_module, "RuntimeAdvancedIdentityConfigResolver", lambda: resolver)
    app = _BroadApplication()
    _install_fake_application(cli, app)
    args = SimpleNamespace(
        request_json=request_path,
        tenant="default",
        edition="enterprise",
        actor="pytest",
        ttl_seconds=3600,
    )
    assert cli._handle_auth_saml_login(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "authenticated"


def test_cli_team_sync_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = OpenInfraCLI()
    app = _BroadApplication()
    _install_fake_application(cli, app)
    config = TeamSyncSourceConfig.create(
        tenant_id="default", source_id="ldap-main", provider="ldap"
    )
    foreign = TeamSyncSourceConfig.create(
        tenant_id="other", source_id="ldap-other", provider="ldap"
    )

    class Resolver:
        sources: tuple[str, ...] = ("foreign", "main")

        def team_sync_source(self, source: str) -> TeamSyncSourceConfig:
            return foreign if source == "foreign" else config

        def team_sync_sources(self) -> tuple[str, ...]:
            return self.sources

        def directory_config(self) -> object:
            return object()

    resolver = Resolver()
    monkeypatch.setattr(cli_module, "RuntimeAdvancedIdentityConfigResolver", lambda: resolver)
    monkeypatch.setattr(
        cli, "_team_sync_source", lambda *_args: SimpleNamespace(fetch=lambda _cfg: None)
    )
    token_file = tmp_path / "token"
    token_file.write_text("t" * 40, encoding="utf-8")
    monkeypatch.setattr(
        cli_module,
        "RuntimeBootstrapTokenStore",
        lambda _path: SimpleNamespace(read=lambda: "t" * 40),
    )

    missing = SimpleNamespace(admin_token="", token_file=None)
    with pytest.raises(ValidationError, match="admin-token"):
        cli._handle_identity_team_sync(missing)

    mismatch = SimpleNamespace(
        admin_token="t" * 40,
        token_file=None,
        source="foreign",
        tenant="default",
        actor="pytest",
    )
    with pytest.raises(ValidationError, match="tenant does not match"):
        cli._handle_identity_team_sync(mismatch)

    direct = SimpleNamespace(
        admin_token="",
        token_file=token_file,
        source="main",
        tenant="default",
        actor="pytest",
    )
    assert cli._handle_identity_team_sync(direct) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "synchronized"

    runtime = SimpleNamespace(token_file=token_file, tenant="default", actor="pytest")
    resolver.sources = ()
    assert cli._handle_identity_team_sync_runtime(runtime) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "skipped"
    resolver.sources = ("foreign", "main")
    assert cli._handle_identity_team_sync_runtime(runtime) == 0
    assert len(json.loads(capsys.readouterr().out)["sources"]) == 1

    monkeypatch.setattr(cli_module, "LdapTeamSyncSource", lambda value: ("ldap", value))
    monkeypatch.setattr(cli_module, "OAuthTeamSyncSource", lambda: "oauth")
    monkeypatch.setattr(cli_module, "AuthProxyTeamSyncSource", lambda: "proxy")
    provider_cli = OpenInfraCLI()
    assert provider_cli._team_sync_source(FederatedProvider.LDAP, resolver)[0] == "ldap"
    assert provider_cli._team_sync_source(FederatedProvider.OAUTH, resolver) == "oauth"
    assert provider_cli._team_sync_source(FederatedProvider.OKTA, resolver) == "oauth"
    assert provider_cli._team_sync_source(FederatedProvider.AUTH_PROXY, resolver) == "proxy"
    with pytest.raises(ValidationError, match="unsupported Team Sync provider"):
        provider_cli._team_sync_source(FederatedProvider.SAML, resolver)


def test_cli_direct_read_list_export_and_boolean_branches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = OpenInfraCLI()
    app = _BroadApplication()
    app.discovery_service.renew_job_lease = lambda _command: _UniversalResult(id="job-1")  # type: ignore[attr-defined,method-assign]
    app.discovery_service.get_job = lambda _command: _UniversalResult(id="job-1")  # type: ignore[attr-defined,method-assign]
    _install_fake_application(cli, app)
    args = _args(tmp_path)
    for key, value in {
        "include_retired": True,
        "baseline_id": "baseline-1",
        "device_object_key": "device/srv1",
        "platform": "ios",
        "observed_before": None,
        "certificate_fingerprint": "a" * 64,
        "job_id": "job-1",
        "worker_id": "worker-1",
        "lease_token": "lease-1",
        "lease_seconds": 60,
        "active": False,
        "inactive": True,
        "source_type": None,
        "document_id": "doc-1",
        "max_objects": 100,
        "deactivate_missing": True,
        "answer_id": "answer-1",
        "output": tmp_path / "export.bin",
        "format": "json",
        "warning_threshold": 70,
        "critical_threshold": 90,
        "snapshot_id": "snapshot-1",
        "cluster_key": "cluster-1",
        "not_known_exploited": True,
        "known_exploited": False,
        "cve_id": None,
        "component": None,
        "report_id": "report-1",
    }.items():
        setattr(args, key, value)

    handlers = (
        cli._handle_network_config_baseline_list,
        cli._handle_network_config_baseline_retire,
        cli._handle_network_config_observation_list,
        cli._handle_discovery_job_renew,
        cli._handle_discovery_job_get,
        cli._handle_kubernetes_capacity,
        cli._handle_kubernetes_latest_capacity_export,
        cli._handle_sbom_vulnerabilities,
        cli._handle_rag_documents,
        cli._handle_rag_document,
        cli._handle_rag_document_deactivate,
        cli._handle_rag_sync_rsot,
        cli._handle_rag_answers,
        cli._handle_rag_answer,
        cli._handle_rag_jobs,
        cli._handle_rag_job,
    )
    for handler in handlers:
        assert handler(args) == 0
        assert capsys.readouterr().out.strip()

    assert cli._optional_bool(None) is None
    assert cli._optional_bool("TRUE") is True
    assert cli._optional_bool("false") is False
    args.clear_default = True
    args.is_default = False
    assert cli._handle_itam_tenant_update(args) == 0
    assert capsys.readouterr().out.strip()

    # File-output branches preserve binary payloads without terminal encoding conversions.
    assert cli._handle_sbom_risk_export(args) == 0
    assert args.output.read_bytes() == _UniversalResult.content
    args.output = tmp_path / "rag.bin"
    assert cli._handle_rag_artifact(args) == 0
    assert args.output.read_bytes() == _UniversalResult.content
    args.output = tmp_path / "greenops.bin"
    assert cli._handle_greenops_report_export(args) == 0
    assert args.output.read_bytes() == _UniversalResult.content
    args.output = tmp_path / "finops.bin"
    assert cli._handle_finops_report_export(args) == 0
    assert args.output.read_bytes() == _UniversalResult.content

    args.format = "html"
    assert cli._handle_ipam_ui_dashboard(args) == 0
    assert "<main>IPAM</main>" in capsys.readouterr().out


def test_cli_static_file_parser_error_matrix(tmp_path: Path) -> None:
    cli = OpenInfraCLI()
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    scalar = tmp_path / "scalar.json"
    scalar.write_text('"value"', encoding="utf-8")
    array_with_scalar = tmp_path / "array.json"
    array_with_scalar.write_text('[{"kind":"Pod"}, 2]', encoding="utf-8")

    for path in (missing, invalid):
        with pytest.raises(ValidationError, match="valid JSON"):
            cli._read_kubernetes_resources(path)
    with pytest.raises(ValidationError, match="JSON array"):
        cli._read_kubernetes_resources(scalar)
    with pytest.raises(ValidationError, match="JSON object"):
        cli._read_kubernetes_resources(array_with_scalar)
    with pytest.raises(ValidationError, match="ISO-8601"):
        cli._kubernetes_datetime("not-a-date")
    for path in (missing, invalid):
        with pytest.raises(ValidationError, match="valid JSON"):
            cli._read_kubernetes_gitops_policy(path)
    with pytest.raises(ValidationError, match="one JSON object"):
        cli._read_kubernetes_gitops_policy(array_with_scalar)

    assert cli._read_sbom_json_object(None, "metadata") == {}
    for path in (missing, invalid):
        with pytest.raises(ValidationError, match="metadata file"):
            cli._read_sbom_json_object(path, "metadata")
    with pytest.raises(ValidationError, match="one JSON object"):
        cli._read_sbom_json_object(scalar, "metadata")
    assert cli._sbom_datetime(None) is None

    for path in (missing, invalid):
        with pytest.raises(ValidationError, match="RAG metadata"):
            cli._read_rag_json_object(path, "RAG metadata")
    with pytest.raises(ValidationError, match="one JSON object"):
        cli._read_rag_json_object(scalar, "RAG metadata")

    assert cli._read_greenops_metadata(None) == {}
    for path in (missing, invalid):
        with pytest.raises(ValidationError, match="GreenOps metadata"):
            cli._read_greenops_metadata(path)
    with pytest.raises(ValidationError, match="one JSON object"):
        cli._read_greenops_metadata(scalar)

    bad_sbom_args = SimpleNamespace(file=missing)
    with pytest.raises(ValidationError, match="cannot read SBOM"):
        cli._handle_sbom_import(bad_sbom_args)
    bad_rag_args = SimpleNamespace(file=missing)
    with pytest.raises(ValidationError, match="cannot read RAG document"):
        cli._handle_rag_document_upsert(bad_rag_args)


def test_cli_greenops_required_period_validation(tmp_path: Path) -> None:
    cli = OpenInfraCLI()
    _install_fake_application(cli, _BroadApplication())
    args = _args(tmp_path)
    args.period_start = None
    args.period_end = None
    with pytest.raises(ValidationError, match="period is required"):
        cli._handle_greenops_measurement_ingest(args)


def test_cli_remaining_active_metadata_and_binary_stdout_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = OpenInfraCLI()
    _install_fake_application(cli, _BroadApplication())
    args = _args(tmp_path)
    args.active = True
    args.inactive = False
    args.source_type = None
    assert cli._handle_rag_documents(args) == 0

    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"source":"meter"}', encoding="utf-8")
    assert cli._read_greenops_metadata(metadata) == {"source": "meter"}

    class BinaryStdout:
        def __init__(self) -> None:
            from io import BytesIO

            self.buffer = BytesIO()

    sink = BinaryStdout()
    monkeypatch.setattr(cli_module.sys, "stdout", sink)
    args.output = None
    args.document_id = "doc-1"
    args.job_id = "job-1"
    args.report_id = "report-1"
    args.format = "json"
    for handler in (
        cli._handle_sbom_risk_export,
        cli._handle_rag_artifact,
        cli._handle_greenops_report_export,
        cli._handle_finops_report_export,
    ):
        assert handler(args) == 0
    assert sink.buffer.getvalue() == _UniversalResult.content * 4
