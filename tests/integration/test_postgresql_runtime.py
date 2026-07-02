from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
)
from openinfra.domain.common import (
    AuditEvent,
    Coordinates3D,
    OpenInfraError,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import Building, Equipment, EquipmentLocation, Rack, Room, Site
from openinfra.domain.security import Permission
from openinfra.infrastructure.postgresql import (
    ConnectionProtocol,
    CursorProtocol,
    PostgreSQLAccessPolicyRepository,
    PostgreSQLAuditRepository,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLDriver,
    PostgreSQLDcimRepository,
    PostgreSQLIdentityRepository,
    PostgreSQLIpamRepository,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLReadinessProbe,
    PostgreSQLSecurityRepository,
    PostgreSQLSessionRegistry,
    PostgreSQLTransactionManager,
)
from openinfra.interfaces.cli import OpenInfraCLI


class FakeCursor(CursorProtocol):
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection
        self._row: Mapping[str, object] | None = None
        self._rows: list[Mapping[str, object]] = []
        self.closed = False

    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        assert params is None or isinstance(params, Mapping)
        effective = dict(params or {})
        self._connection.statements.append((" ".join(query.split()), effective))
        if "CREATE TABLE IF NOT EXISTS openinfra_schema_migrations" in query:
            self._connection.schema_history_created = True
        elif "SELECT to_regclass('public.openinfra_schema_migrations')" in query:
            self._row = {
                "migration_table": (
                    "openinfra_schema_migrations"
                    if self._connection.schema_history_created
                    else None
                )
            }
        elif "FROM openinfra_schema_migrations" in query:
            self._rows = list(self._connection.schema_migrations.values())
        elif "INSERT INTO openinfra_schema_migrations" in query:
            self._connection.schema_history_created = True
            version = str(effective["version"])
            self._connection.schema_migrations[version] = {
                "version": version,
                "checksum": str(effective["checksum"]),
                "applied_at": datetime.now(UTC),
            }
        elif "CREATE TABLE" in query and "PARTITION BY" in query:
            self._connection.migration_sql_executions += 1
        elif "SELECT 1 AS ready" in query:
            self._row = {"ready": 1}
        elif "RETURNING id, tenant_id, vrf_name, cidr, description" in query:
            self._row = {
                "id": str(effective["id"]),
                "tenant_id": str(effective["tenant_id"]),
                "vrf_name": str(effective["vrf_name"]),
                "cidr": str(effective["cidr"]),
                "description": str(effective["description"]),
            }
        elif "FROM ip_reservations" in query and "ORDER BY address" in query:
            self._rows = list(self._connection.reservations)
        elif "FROM ip_reservations" in query and "idempotency_key" in query:
            self._row = self._connection.reservation_by_key(str(effective["idempotency_key"]))
        elif "INSERT INTO ip_reservations" in query:
            self._connection.reservations.append(
                {
                    "id": str(effective["id"]),
                    "tenant_id": str(effective["tenant_id"]),
                    "vrf_name": str(effective["vrf_name"]),
                    "prefix_cidr": str(effective["prefix_cidr"]),
                    "address": str(effective["address"]),
                    "hostname": str(effective["hostname"]),
                    "idempotency_key": str(effective["idempotency_key"]),
                }
            )
        elif "FROM rooms" in query:
            self._row = self._connection.rooms.get(str(effective["code"]))
        elif "FROM racks" in query:
            self._row = self._connection.racks.get(str(effective["code"]))
        elif "FROM equipment" in query:
            self._row = self._connection.equipment.get(str(effective["asset_tag"]))
        elif "INSERT INTO identity_users" in query:
            username = str(effective["username"])
            self._connection.identity_users[username] = {
                "id": str(effective["id"]),
                "tenant_id": str(effective["tenant_id"]),
                "username": username,
                "display_name": str(effective["display_name"]),
                "email": effective.get("email"),
                "roles": list(effective["roles"]),
                "active": bool(effective["active"]),
                "created_at": datetime.now(UTC),
            }
        elif "INSERT INTO identity_groups" in query:
            group_name = str(effective["name"])
            self._connection.identity_groups[group_name] = {
                "id": str(effective["id"]),
                "tenant_id": str(effective["tenant_id"]),
                "name": group_name,
                "display_name": str(effective["display_name"]),
                "roles": list(effective["roles"]),
                "active": bool(effective["active"]),
                "created_at": datetime.now(UTC),
            }
        elif "INSERT INTO identity_group_memberships" in query:
            self._connection.identity_memberships.append(
                {
                    "tenant_id": str(effective["tenant_id"]),
                    "username": str(effective["username"]),
                    "group_name": str(effective["group_name"]),
                }
            )
        elif "FROM identity_users" in query and "SELECT roles" in query:
            user = self._connection.identity_users.get(str(effective["username"]))
            self._row = {"roles": list(user.get("roles", []))} if user else None
        elif "FROM identity_groups" in query and "SELECT roles" in query:
            group = self._connection.identity_groups.get(str(effective["group_name"]))
            self._row = {"roles": list(group.get("roles", []))} if group else None
        elif "UPDATE identity_users" in query:
            user = self._connection.identity_users.get(str(effective["username"]))
            if user is not None:
                updated = dict(user)
                updated["roles"] = list(effective["roles"])
                self._connection.identity_users[str(effective["username"])] = updated
        elif "UPDATE identity_groups" in query:
            group = self._connection.identity_groups.get(str(effective["group_name"]))
            if group is not None:
                updated = dict(group)
                updated["roles"] = list(effective["roles"])
                self._connection.identity_groups[str(effective["group_name"])] = updated
        elif "FROM identity_users" in query:
            self._row = self._connection.identity_users.get(str(effective["username"]))
        elif "FROM identity_group_memberships" in query:
            rows = []
            username = str(effective["username"])
            for membership in self._connection.identity_memberships:
                if membership["username"] != username:
                    continue
                group = self._connection.identity_groups.get(str(membership["group_name"]))
                if group is not None and bool(group.get("active", True)):
                    rows.append({"group_name": group["name"], "group_roles": group["roles"]})
            self._rows = rows
        elif "INSERT INTO api_tokens" in query:
            token_hash = str(effective["token_hash"])
            self._connection.tokens[token_hash] = {
                "id": str(effective["id"]),
                "tenant_id": str(effective["tenant_id"]),
                "subject": str(effective["subject"]),
                "token_hash": token_hash,
                "token_prefix": str(effective["token_prefix"]),
                "roles": list(effective["roles"]),
                "active": bool(effective["active"]),
                "created_at": datetime.now(UTC),
                "expires_at": effective.get("expires_at"),
                "revoked_at": effective.get("revoked_at"),
                "revoked_by": effective.get("revoked_by"),
                "last_used_at": effective.get("last_used_at"),
                "use_count": int(effective.get("use_count", 0)),
            }
        elif "FROM api_tokens" in query and "LIMIT" in query:
            self._rows = list(self._connection.tokens.values())
        elif "FROM api_tokens" in query:
            self._row = self._connection.tokens.get(str(effective["token_hash"]))
        elif "UPDATE api_tokens" in query:
            token = self._connection.tokens.get(str(effective["token_hash"]))
            if token is not None:
                updated = dict(token)
                if "revoked_by" in effective:
                    updated["active"] = False
                    updated["revoked_at"] = datetime.now(UTC)
                    updated["revoked_by"] = str(effective["actor"])
                else:
                    updated["last_used_at"] = datetime.now(UTC)
                    updated["use_count"] = int(updated.get("use_count", 0)) + 1
                self._connection.tokens[str(effective["token_hash"])] = updated
        elif "INSERT INTO access_policy_rules" in query:
            self._connection.access_policy_rules[str(effective["name"])] = {
                "id": str(effective["id"]),
                "tenant_id": str(effective["tenant_id"]),
                "name": str(effective["name"]),
                "permission": str(effective["permission"]),
                "effect": str(effective["effect"]),
                "subjects": list(effective["subjects"]),
                "roles": list(effective["roles"]),
                "site_codes": list(effective["site_codes"]),
                "environments": list(effective["environments"]),
                "active": bool(effective["active"]),
                "created_at": datetime.now(UTC),
            }
        elif "FROM access_policy_rules" in query and "LIMIT" in query:
            self._rows = list(self._connection.access_policy_rules.values())
        elif "FROM access_policy_rules" in query:
            permission = str(effective.get("permission", ""))
            self._rows = [
                rule for rule in self._connection.access_policy_rules.values()
                if not permission or rule["permission"] == permission
            ]
        elif "UPDATE access_policy_rules" in query:
            rule = self._connection.access_policy_rules.get(str(effective["name"]))
            if rule is not None:
                updated = dict(rule)
                updated["active"] = False
                self._connection.access_policy_rules[str(effective["name"])] = updated
        elif "SELECT id, tenant_id, actor" in query:
            self._rows = [
                {
                    "id": event["id"],
                    "tenant_id": event["tenant_id"],
                    "actor": event["actor"],
                    "action": event["action"],
                    "target_type": event["target_type"],
                    "target_id": event["target_id"],
                    "severity": event["severity"],
                    "metadata": event["metadata"],
                    "created_at": datetime.now(UTC),
                }
                for event in self._connection.audit_events
            ]
        elif "INSERT INTO audit_events" in query:
            self._connection.audit_events.append(effective)
        return self

    def fetchone(self) -> Mapping[str, object] | None:
        return self._row

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        return tuple(self._rows)

    def close(self) -> object:
        self.closed = True
        return None


class FakeConnection(ConnectionProtocol):
    def __init__(self) -> None:
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.reservations: list[Mapping[str, object]] = []
        self.audit_events: list[Mapping[str, object]] = []
        self.schema_history_created = False
        self.schema_migrations: dict[str, Mapping[str, object]] = {}
        self.migration_sql_executions = 0
        self.rooms: dict[str, Mapping[str, object]] = {}
        self.racks: dict[str, Mapping[str, object]] = {}
        self.equipment: dict[str, Mapping[str, object]] = {}
        self.tokens: dict[str, Mapping[str, object]] = {}
        self.identity_users: dict[str, Mapping[str, object]] = {}
        self.identity_groups: dict[str, Mapping[str, object]] = {}
        self.identity_memberships: list[Mapping[str, object]] = []
        self.access_policy_rules: dict[str, Mapping[str, object]] = {}
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> CursorProtocol:
        return FakeCursor(self)

    def commit(self) -> object:
        self.commits += 1
        return None

    def rollback(self) -> object:
        self.rollbacks += 1
        return None

    def close(self) -> object:
        self.closed = True
        return None

    def reservation_by_key(self, key: str) -> Mapping[str, object] | None:
        for reservation in self.reservations:
            if reservation["idempotency_key"] == key:
                return reservation
        return None


class FakeConnector:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.calls: list[tuple[str, PostgreSQLClusterProfile]] = []

    def connect(self, dsn: str, profile: PostgreSQLClusterProfile) -> ConnectionProtocol:
        self.calls.append((dsn, profile))
        return self.connection


class TestPostgreSQLRuntime:
    def test_ipam_allocation_uses_postgresql_unit_of_work_and_repositories(self) -> None:
        connector = FakeConnector()
        factory = PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=connector.connect,
        )
        registry = PostgreSQLSessionRegistry(factory)
        app = ApplicationFactory()._build_application(
            store=registry,
            dcim_repository=PostgreSQLDcimRepository(registry),
            ipam_repository=PostgreSQLIpamRepository(registry),
            security_repository=PostgreSQLSecurityRepository(registry),
            identity_repository=PostgreSQLIdentityRepository(registry),
            audit_repository=PostgreSQLAuditRepository(registry),
            access_policy_repository=PostgreSQLAccessPolicyRepository(registry),
            transaction_manager=PostgreSQLTransactionManager(registry),
            readiness_probe=PostgreSQLReadinessProbe(registry),
            schema_status_provider=PostgreSQLMigrationExecutor(
                registry,
                PostgreSQLMigrationCatalog(Path("migrations/postgresql")),
            ),
        )

        result = app.ipam_service.allocate(
            AllocateIpCommand(
                tenant_id="default",
                actor="pytest",
                vrf="default",
                prefix="10.50.0.0/30",
                hostname="pg-srv-01",
                idempotency_key="pg-req-1",
            )
        )

        assert result.created is True
        assert result.as_dict()["address"] == "10.50.0.1"
        assert connector.connection.commits == 1
        assert connector.connection.rollbacks == 0
        assert connector.connection.closed is True
        assert any(
            "INSERT INTO prefixes" in statement[0]
            for statement in connector.connection.statements
        )
        assert any(
            "INSERT INTO ip_reservations" in statement[0]
            for statement in connector.connection.statements
        )
        assert any(
            "INSERT INTO audit_events" in statement[0]
            for statement in connector.connection.statements
        )


    def test_security_repository_bootstraps_and_authenticates_postgresql_token(self) -> None:
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        app = ApplicationFactory()._build_application(
            store=registry,
            dcim_repository=PostgreSQLDcimRepository(registry),
            ipam_repository=PostgreSQLIpamRepository(registry),
            security_repository=PostgreSQLSecurityRepository(registry),
            identity_repository=PostgreSQLIdentityRepository(registry),
            audit_repository=PostgreSQLAuditRepository(registry),
            access_policy_repository=PostgreSQLAccessPolicyRepository(registry),
            transaction_manager=PostgreSQLTransactionManager(registry),
            readiness_probe=PostgreSQLReadinessProbe(registry),
            schema_status_provider=PostgreSQLMigrationExecutor(
                registry,
                PostgreSQLMigrationCatalog(Path("migrations/postgresql")),
            ),
        )
        token = "p" * 40

        result = app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="pg-client",
                roles=("admin",),
                token=token,
            )
        )
        principal = app.security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id="default",
                token=token,
                required_permission=Permission.IPAM_ALLOCATE,
            )
        )

        assert result.token_prefix == token[:12]
        assert principal.subject == "pg-client"
        assert connector.connection.commits == 2
        assert any(
            "INSERT INTO api_tokens" in statement[0]
            for statement in connector.connection.statements
        )
        assert any(
            "UPDATE api_tokens" in statement[0]
            for statement in connector.connection.statements
        )

    def test_postgresql_repository_requires_active_unit_of_work(self) -> None:
        connector = FakeConnector()
        factory = PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=connector.connect,
        )
        repository = PostgreSQLIpamRepository(PostgreSQLSessionRegistry(factory))

        with pytest.raises(OpenInfraError):
            repository.list_reservations(TenantId.from_value("default"), "default", "10.0.0.0/30")

    def test_missing_dsn_and_missing_driver_are_reported_cleanly(self, capsys: object) -> None:
        with pytest.raises(ValidationError):
            PostgreSQLConnectionFactory(" ")

        code = OpenInfraCLI().run([
            "ipam",
            "allocate",
            "--backend",
            "postgresql",
            "--tenant",
            "default",
            "--vrf",
            "default",
            "--prefix",
            "10.0.0.0/30",
            "--hostname",
            "srv",
            "--idempotency-key",
            "req",
        ])
        captured = capsys.readouterr()

        assert code == 2
        assert "OPENINFRA_DATABASE_DSN" in captured.err
        with pytest.raises(OpenInfraError):
            PostgreSQLDriver().connect(
                "postgresql://openinfra@db/openinfra",
                PostgreSQLClusterProfile.production_default(),
            )

    def test_dcim_and_audit_postgresql_repositories_map_rows(self) -> None:
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        tenant = TenantId.from_value("default")
        dcim_repository = PostgreSQLDcimRepository(registry)
        audit_repository = PostgreSQLAuditRepository(registry)
        transaction_manager = PostgreSQLTransactionManager(registry)
        connector.connection.rooms["MMR1"] = {
            "id": "00000000-0000-4000-8000-000000000001",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "code": "MMR1",
            "name": "Main Room",
            "rows": ["A", "B"],
            "columns": ["01", "12"],
        }
        connector.connection.racks["R42"] = {
            "id": "00000000-0000-4000-8000-000000000002",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "room_code": "MMR1",
            "code": "R42",
            "row_code": "B",
            "column_code": "12",
            "units": 42,
            "coordinate_x": 12.0,
            "coordinate_y": 4.0,
            "coordinate_z": 0.0,
        }
        connector.connection.equipment["SRV-PG-1"] = {
            "id": "00000000-0000-4000-8000-000000000003",
            "tenant_id": "default",
            "asset_tag": "SRV-PG-1",
            "name": "Server PG",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "room_code": "MMR1",
            "row_code": "B",
            "column_code": "12",
            "rack_code": "R42",
            "u_position": 10,
            "coordinate_x": None,
            "coordinate_y": None,
            "coordinate_z": None,
        }

        with transaction_manager.begin() as unit_of_work:
            dcim_repository.add_site(Site.create(tenant, "PAR1", "Paris", "FR", "Paris"))
            dcim_repository.add_building(Building.create(tenant, "PAR1", "BAT-A", "Building A"))
            dcim_repository.add_room(
                Room.create(tenant, "PAR1", "BAT-A", "MMR2", "Room 2", ("A",), ("01",))
            )
            dcim_repository.add_rack(
                Rack.create(
                    tenant,
                    "PAR1",
                    "BAT-A",
                    "MMR1",
                    "R43",
                    "B",
                    "12",
                    42,
                    Coordinates3D.from_values(1.0, 2.0, 0.0),
                )
            )
            dcim_repository.add_equipment(
                Equipment.create(
                    tenant,
                    "SRV-PG-2",
                    "Server PG 2",
                    EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "B", "12", "R42", 11),
                )
            )
            room = dcim_repository.find_room(tenant, "PAR1", "BAT-A", "MMR1")
            rack = dcim_repository.find_rack(tenant, "PAR1", "BAT-A", "MMR1", "R42")
            equipment = dcim_repository.find_equipment(tenant, "SRV-PG-1")
            audit_repository.append(
                AuditEvent.record(
                    tenant,
                    "pytest",
                    "dcim.equipment.located",
                    "equipment",
                    "SRV-PG-1",
                )
            )
            events = audit_repository.list_events(tenant)
            unit_of_work.commit()

        assert room is not None
        assert room.rows == ("A", "B")
        assert rack is not None
        assert rack.coordinates == Coordinates3D.from_values(12.0, 4.0, 0.0)
        assert equipment is not None
        assert equipment.location.human_readable().startswith("site=PAR1")
        assert len(events) == 1
        assert connector.connection.commits == 1

    def test_postgresql_unit_of_work_rolls_back_uncommitted_changes(self) -> None:
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        manager = PostgreSQLTransactionManager(registry)

        with manager.begin():
            registry.current().cursor().execute("SELECT 1")

        assert connector.connection.rollbacks == 1
        assert connector.connection.closed is True

    def test_postgresql_migration_executor_applies_pending_migrations_idempotently(
        self,
        tmp_path: Path,
    ) -> None:
        migration_root = tmp_path / "migrations"
        migration_root.mkdir()
        migration = migration_root / "0001_bootstrap.sql"
        migration.write_text(
            "\n".join(
                (
                    "BEGIN;",
                    "CREATE TABLE IF NOT EXISTS audit_events (id uuid, created_at timestamptz)",
                    "PARTITION BY RANGE (created_at);",
                    "CREATE INDEX IF NOT EXISTS idx_audit_events_id ON audit_events (id);",
                    "COMMIT;",
                    "",
                )
            ),
            encoding="utf-8",
        )
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        catalog = PostgreSQLMigrationCatalog(migration_root)
        executor = PostgreSQLMigrationExecutor(registry, catalog)

        dry_run_status = executor.apply_all(dry_run=True)
        applied_status = executor.apply_all()
        second_status = executor.apply_all()
        readiness = PostgreSQLReadinessProbe(registry, catalog).check()

        assert dry_run_status.ready is False
        assert len(dry_run_status.pending) == 1
        assert applied_status.ready is True
        assert applied_status.pending == ()
        assert second_status.ready is True
        assert connector.connection.migration_sql_executions == 1
        assert "0001_bootstrap.sql" in connector.connection.schema_migrations
        assert readiness.ready is True

    def test_postgresql_migration_executor_rejects_checksum_drift(
        self,
        tmp_path: Path,
    ) -> None:
        migration_root = tmp_path / "migrations"
        migration_root.mkdir()
        migration = migration_root / "0001_bootstrap.sql"
        migration.write_text(
            " ".join(
                (
                    "CREATE TABLE audit_events (id uuid) PARTITION BY RANGE (id);",
                    "CREATE INDEX idx ON audit_events (id);",
                )
            ),
            encoding="utf-8",
        )
        connector = FakeConnector()
        connector.connection.schema_history_created = True
        connector.connection.schema_migrations["0001_bootstrap.sql"] = {
            "version": "0001_bootstrap.sql",
            "checksum": "not-the-current-checksum",
            "applied_at": datetime.now(UTC),
        }
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )

        with pytest.raises(ValidationError):
            PostgreSQLMigrationExecutor(
                registry,
                PostgreSQLMigrationCatalog(migration_root),
            ).status()

    def test_postgresql_readiness_probe_executes_select_one(self) -> None:
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        status = PostgreSQLReadinessProbe(registry).check()

        assert status.ready is True
        assert status.component == "postgresql"
        assert any(
            "SELECT 1 AS ready" in statement[0]
            for statement in connector.connection.statements
        )
        assert connector.connection.closed is True

    def test_application_factory_builds_postgresql_application_without_connection(self) -> None:
        app = ApplicationFactory().create_postgresql_application(
            "postgresql://openinfra@db/openinfra",
            seed=False,
        )

        assert app.ipam_service is not None
        assert isinstance(app.transaction_manager, PostgreSQLTransactionManager)

class TestPostgreSQLSecurityLifecycle:
    def test_postgresql_security_repository_lists_and_revokes_tokens(self) -> None:
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        app = ApplicationFactory()._build_application(
            store=registry,
            dcim_repository=PostgreSQLDcimRepository(registry),
            ipam_repository=PostgreSQLIpamRepository(registry),
            security_repository=PostgreSQLSecurityRepository(registry),
            identity_repository=PostgreSQLIdentityRepository(registry),
            audit_repository=PostgreSQLAuditRepository(registry),
            access_policy_repository=PostgreSQLAccessPolicyRepository(registry),
            transaction_manager=PostgreSQLTransactionManager(registry),
            readiness_probe=PostgreSQLReadinessProbe(registry),
            schema_status_provider=PostgreSQLMigrationExecutor(
                registry,
                PostgreSQLMigrationCatalog(Path("migrations/postgresql")),
            ),
        )
        admin_token = "g" * 40
        worker_token = "h" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="pg-admin",
                roles=("admin",),
                token=admin_token,
                ttl_seconds=3600,
            )
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="pg-worker",
                roles=("viewer",),
                token=worker_token,
            )
        )

        listed = app.security_service.list_tokens(
            ListTokensCommand(tenant_id="default", admin_token=admin_token, limit=10)
        )
        revoked = app.security_service.revoke_token(
            RevokeTokenCommand(
                tenant_id="default",
                actor="pytest",
                target_token=worker_token,
                admin_token=admin_token,
            )
        )

        assert len(listed.items) == 2
        assert revoked.revoked is True
        assert any(
            "SELECT id, tenant_id, subject" in statement[0] and "LIMIT" in statement[0]
            for statement in connector.connection.statements
        )
        assert any(
            "SET active = false" in statement[0]
            for statement in connector.connection.statements
        )


class TestPostgreSQLIdentityRuntime:
    def test_postgresql_identity_repository_merges_group_roles(self) -> None:
        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        app = ApplicationFactory()._build_application(
            store=registry,
            dcim_repository=PostgreSQLDcimRepository(registry),
            ipam_repository=PostgreSQLIpamRepository(registry),
            security_repository=PostgreSQLSecurityRepository(registry),
            identity_repository=PostgreSQLIdentityRepository(registry),
            audit_repository=PostgreSQLAuditRepository(registry),
            access_policy_repository=PostgreSQLAccessPolicyRepository(registry),
            transaction_manager=PostgreSQLTransactionManager(registry),
            readiness_probe=PostgreSQLReadinessProbe(registry),
            schema_status_provider=PostgreSQLMigrationExecutor(
                registry,
                PostgreSQLMigrationCatalog(Path("migrations/postgresql")),
            ),
        )
        admin_token = "j" * 40
        alice_token = "k" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "pg-admin", ("admin",), admin_token)
        )
        app.identity_service.create_user(
            CreateUserCommand("default", "pytest", admin_token, "pg-alice", "PG Alice", None, ())
        )
        app.identity_service.create_group(
            CreateGroupCommand(
                "default",
                "pytest",
                admin_token,
                "pg-ipam",
                "PG IPAM",
                ("viewer",),
            )
        )
        group_grant = app.identity_service.grant_group_role(
            GrantGroupRoleCommand("default", "pytest", admin_token, "pg-ipam", "ipam:operator")
        )
        user_grant = app.identity_service.grant_user_role(
            GrantUserRoleCommand("default", "pytest", admin_token, "pg-alice", "dcim:operator")
        )
        app.identity_service.add_user_to_group(
            AddUserToGroupCommand("default", "pytest", admin_token, "pg-alice", "pg-ipam")
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "pg-alice", ("viewer",), alice_token)
        )
        principal = app.security_service.authenticate_token(
            AuthenticateTokenCommand("default", alice_token, Permission.IPAM_ALLOCATE)
        )
        effective = app.identity_service.effective_identity(
            EffectiveIdentityCommand("default", "pytest", admin_token, "pg-alice")
        )

        assert group_grant["changed"] is True
        assert user_grant["changed"] is True
        assert "ipam:operator" in [role.name for role in principal.roles]
        assert effective.as_dict()["effective_roles"] == [
            "dcim:operator",
            "ipam:operator",
            "viewer",
        ]
        assert any(
            "INSERT INTO identity_users" in statement[0]
            for statement in connector.connection.statements
        )
        assert any(
            "UPDATE identity_groups" in statement[0]
            for statement in connector.connection.statements
        )

class TestPostgreSQLAccessPolicyRuntime:
    def test_postgresql_access_policy_repository_and_service_evaluate_context(self) -> None:
        from openinfra.application.access_policy_services import (
            CreateAccessPolicyRuleCommand,
            EvaluateAccessPolicyCommand,
            ListAccessPolicyRulesCommand,
        )

        connector = FakeConnector()
        registry = PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=connector.connect,
            )
        )
        app = ApplicationFactory()._build_application(
            store=registry,
            dcim_repository=PostgreSQLDcimRepository(registry),
            ipam_repository=PostgreSQLIpamRepository(registry),
            security_repository=PostgreSQLSecurityRepository(registry),
            identity_repository=PostgreSQLIdentityRepository(registry),
            audit_repository=PostgreSQLAuditRepository(registry),
            access_policy_repository=PostgreSQLAccessPolicyRepository(registry),
            transaction_manager=PostgreSQLTransactionManager(registry),
            readiness_probe=PostgreSQLReadinessProbe(registry),
            schema_status_provider=PostgreSQLMigrationExecutor(
                registry,
                PostgreSQLMigrationCatalog(Path("migrations/postgresql")),
            ),
        )
        admin_token = "q" * 40
        worker_token = "z" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "pg-admin", ("admin",), admin_token)
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default",
                "pytest",
                "pg-worker",
                ("ipam:operator",),
                worker_token,
            )
        )
        rule = app.access_policy_service.create_rule(
            CreateAccessPolicyRuleCommand(
                "default",
                "pytest",
                admin_token,
                "pg-par1",
                "ipam.allocate",
                "allow",
                subjects=("pg-worker",),
                site_codes=("PAR1",),
            )
        )
        page = app.access_policy_service.list_rules(
            ListAccessPolicyRulesCommand("default", admin_token, 10)
        )
        allowed = app.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand("default", worker_token, "ipam.allocate", "PAR1", None)
        )
        denied = app.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand("default", worker_token, "ipam.allocate", "LON1", None)
        )

        assert rule.name == "pg-par1"
        assert page.as_dict()["items"][0]["name"] == "pg-par1"
        assert allowed["allowed"] is True
        assert denied["allowed"] is False
        assert any(
            "INSERT INTO access_policy_rules" in statement[0]
            for statement in connector.connection.statements
        )
