from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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
        self.it_resources_management_service = _RsotService()
        self.ipam_model_service = _IpamModelService()
        self.dcim_topology_service = _DcimTopologyService()


def _args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        actor="pytest",
        admin_token="a" * 40,
        as_of="2026-07-09T00:00:00Z",
        backend="json",
        building="BAT-A",
        clear_default=False,
        code="PAR1_BAT-A_ETG1",
        cursor=None,
        collector_id="collector-1",
        data=tmp_path / "state.json",
        description="test",
        edition="enterprise",
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
        name="Name",
        organization="ORG-1",
        postgres_dsn=None,
        prefix="10.0.0.0/24",
        profile_id="profile-1",
        reason="rotated",
        root=None,
        scope="site/par1",
        scope_tenant="filiale-1",
        site="PAR1",
        status="active",
        tenant="default",
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


def test_cli_direct_handlers_cover_legacy_rsot_alias_paths(tmp_path: Path, capsys: object) -> None:
    cli = OpenInfraCLI()
    _install_fake_application(cli, _Application())
    args = _args(tmp_path)

    for marker in ("itrm_command", "ri_command", "sot_command"):
        legacy_args = SimpleNamespace(**vars(args))
        setattr(legacy_args, marker, "legacy")
        assert cli._handle_sot_resource_taxonomy(legacy_args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert "categories" in payload

    assert cli._handle_sot_upsert_object(args) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True
    assert cli._handle_sot_get_object_as_of(args) == 0
    assert json.loads(capsys.readouterr().out)["key"] == "device/srv1"
    assert cli._handle_sot_list_object_audit(args) == 0
    assert json.loads(capsys.readouterr().out)["items"]


def test_cli_runtime_resolution_edges(tmp_path: Path, monkeypatch: object) -> None:
    cli = OpenInfraCLI()
    explicit = SimpleNamespace(root=tmp_path / "migrations")
    assert cli._resolve_migration_root(explicit) == tmp_path / "migrations"
    runtime_args = SimpleNamespace(root=None)
    runtime_config = tmp_path / "openinfra.conf"
    runtime_config.write_text(
        "OPENINFRA_MIGRATIONS_ROOT=" + str(tmp_path / "runtime-migrations") + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(runtime_config))
    assert cli._resolve_migration_root(runtime_args) == tmp_path / "runtime-migrations"

    monkeypatch.delenv("OPENINFRA_RUNTIME_CONFIG")
    assert cli._resolve_migration_root(runtime_args) == Path("installers/migrations/postgresql")
    assert cli._packaged_migration_root().as_posix().endswith("openinfra/migrations/postgresql")

    monkeypatch.chdir(tmp_path)
    packaged_root = tmp_path / "installed-openinfra" / "migrations" / "postgresql"
    packaged_root.mkdir(parents=True)
    monkeypatch.setattr(cli, "_packaged_migration_root", lambda: packaged_root)
    assert cli._resolve_migration_root(runtime_args) == packaged_root
    packaged_root.rmdir()
    assert cli._resolve_migration_root(runtime_args) == Path("installers/migrations/postgresql")
