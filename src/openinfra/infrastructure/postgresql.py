from __future__ import annotations

import hashlib
import importlib
import ipaddress
import json
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, Self, cast

from openinfra.application.ports import (
    AccessPolicyRepository,
    AccessPolicyRulePage,
    AuditRepository,
    DcimRepository,
    IdentityRepository,
    IpamRepository,
    ReadinessProbe,
    ReadinessStatus,
    SchemaStatusProvider,
    SecurityRepository,
    SecurityTokenPage,
    TransactionManager,
    UnitOfWork,
)
from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.common import (
    AuditEvent,
    Code,
    ConflictError,
    Coordinates3D,
    EntityId,
    Name,
    OpenInfraError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import Building, Equipment, EquipmentLocation, Rack, Room, Site
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
    IdentityUser,
)
from openinfra.domain.ipam import IpReservation, Prefix, Vrf
from openinfra.domain.security import ApiTokenCredential, Permission


class CursorProtocol(Protocol):
    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        raise TypeError("adapter contract invoked directly")

    def fetchone(self) -> Mapping[str, object] | None:
        raise TypeError("adapter contract invoked directly")

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        raise TypeError("adapter contract invoked directly")

    def close(self) -> object:
        raise TypeError("adapter contract invoked directly")


class ConnectionProtocol(Protocol):
    def cursor(self) -> CursorProtocol:
        raise TypeError("adapter contract invoked directly")

    def commit(self) -> object:
        raise TypeError("adapter contract invoked directly")

    def rollback(self) -> object:
        raise TypeError("adapter contract invoked directly")

    def close(self) -> object:
        raise TypeError("adapter contract invoked directly")


@dataclass(frozen=True, slots=True)
class PostgreSQLClusterProfile:
    application_name: str
    statement_timeout_ms: int
    lock_timeout_ms: int
    read_only_replica_allowed: bool

    @classmethod
    def production_default(cls) -> Self:
        return cls(
            application_name="openinfra-api",
            statement_timeout_ms=30_000,
            lock_timeout_ms=5_000,
            read_only_replica_allowed=True,
        )

    def dsn_options(self) -> str:
        return (
            f"application_name={self.application_name} "
            f"statement_timeout={self.statement_timeout_ms} "
            f"lock_timeout={self.lock_timeout_ms}"
        )


@dataclass(frozen=True, slots=True)
class PostgreSQLMigration:
    name: str
    path: Path
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        if not self.name.endswith(".sql"):
            raise ValidationError("migration name must end with .sql")
        normalized = self.sql.upper()
        has_schema_change = any(
            marker in normalized
            for marker in ("CREATE TABLE", "ALTER TABLE", "CREATE INDEX", "CREATE EXTENSION")
        )
        if not has_schema_change:
            raise ValidationError("migration must contain a controlled schema change")
        if "CREATE TABLE" in normalized and "PARTITION BY" not in normalized:
            raise ValidationError("table-creating migrations must define partitioning")
        if "CREATE INDEX" not in normalized:
            raise ValidationError("migration must create or maintain indexes")
        if "AUDIT_EVENTS" not in normalized:
            raise ValidationError("migration must include audit persistence or audit indexes")

    def as_dict(self) -> dict[str, object]:
        return {"version": self.name, "checksum": self.checksum}


class PostgreSQLMigrationCatalog:
    def __init__(self, root: Path) -> None:
        self._root = root

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> Self:
        root = project_root or Path.cwd()
        return cls(root / "migrations" / "postgresql")

    def load(self, name: str) -> PostgreSQLMigration:
        safe_name = self._sanitize_name(name)
        path = self._root / safe_name
        if not path.is_file():
            raise ValidationError(f"migration not found: {safe_name}")
        migration = PostgreSQLMigration(
            name=safe_name,
            path=path,
            sql=path.read_text(encoding="utf-8"),
        )
        migration.validate()
        return migration

    def list_names(self) -> tuple[str, ...]:
        return tuple(sorted(path.name for path in self._root.glob("*.sql") if path.is_file()))

    def _sanitize_name(self, name: str) -> str:
        normalized = name.strip()
        if not normalized.endswith(".sql"):
            normalized = f"{normalized}.sql"
        if "/" in normalized or "\\" in normalized or normalized.startswith("."):
            raise ValidationError("unsafe migration name")
        return normalized


@dataclass(frozen=True, slots=True)
class PostgreSQLAppliedMigration:
    version: str
    checksum: str
    applied_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "checksum": self.checksum,
            "applied_at": self.applied_at,
        }


@dataclass(frozen=True, slots=True)
class PostgreSQLSchemaStatus:
    ready: bool
    applied: tuple[PostgreSQLAppliedMigration, ...]
    pending: tuple[PostgreSQLMigration, ...]
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "backend": "postgresql",
            "managed": True,
            "ready": self.ready,
            "detail": self.detail,
            "applied": [item.as_dict() for item in self.applied],
            "pending": [item.as_dict() for item in self.pending],
        }


class PostgreSQLMigrationExecutor(SchemaStatusProvider):
    _HISTORY_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS openinfra_schema_migrations (
        version text PRIMARY KEY,
        checksum text NOT NULL,
        applied_at timestamptz NOT NULL DEFAULT now()
    )
    """

    def __init__(
        self,
        registry: PostgreSQLSessionRegistry,
        catalog: PostgreSQLMigrationCatalog,
    ) -> None:
        self._registry = registry
        self._catalog = catalog

    def status(self) -> PostgreSQLSchemaStatus:
        connection = self._registry.open()
        cursor = connection.cursor()
        try:
            self._ensure_history_table(cursor)
            applied = self._load_applied(cursor)
            pending = self._pending_migrations(applied)
            connection.rollback()
            detail = (
                "postgresql schema is up to date"
                if not pending
                else "postgresql schema has pending migrations"
            )
            return PostgreSQLSchemaStatus(not pending, tuple(applied.values()), pending, detail)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def status_as_dict(self) -> dict[str, object]:
        return self.status().as_dict()

    def apply_all(self, dry_run: bool = False) -> PostgreSQLSchemaStatus:
        connection = self._registry.open()
        cursor = connection.cursor()
        try:
            self._ensure_history_table(cursor)
            applied = self._load_applied(cursor)
            pending = self._pending_migrations(applied)
            if dry_run:
                connection.rollback()
                detail = "dry run completed; no migration was applied"
                return PostgreSQLSchemaStatus(not pending, tuple(applied.values()), pending, detail)
            for migration in pending:
                cursor.execute(self._transactional_sql(migration))
                cursor.execute(
                    """
                    INSERT INTO openinfra_schema_migrations (version, checksum)
                    VALUES (%(version)s, %(checksum)s)
                    ON CONFLICT (version) DO UPDATE SET
                        checksum = EXCLUDED.checksum,
                        applied_at = now()
                    """,
                    {"version": migration.name, "checksum": migration.checksum},
                )
            connection.commit()
            refreshed = self._load_applied(cursor)
            detail = (
                "postgresql schema migrations applied"
                if pending
                else "postgresql schema was already up to date"
            )
            return PostgreSQLSchemaStatus(True, tuple(refreshed.values()), (), detail)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def _transactional_sql(self, migration: PostgreSQLMigration) -> str:
        retained_lines: list[str] = []
        for line in migration.sql.splitlines():
            normalized = line.strip().upper()
            if normalized in {"BEGIN;", "COMMIT;"}:
                continue
            retained_lines.append(line)
        return "\n".join(retained_lines).strip() + "\n"

    def _ensure_history_table(self, cursor: CursorProtocol) -> None:
        cursor.execute(self._HISTORY_TABLE_SQL)

    def _load_applied(self, cursor: CursorProtocol) -> dict[str, PostgreSQLAppliedMigration]:
        cursor.execute(
            """
            SELECT version, checksum, applied_at
            FROM openinfra_schema_migrations
            ORDER BY version
            """
        )
        applied: dict[str, PostgreSQLAppliedMigration] = {}
        for row in cursor.fetchall():
            applied[str(row["version"])] = PostgreSQLAppliedMigration(
                version=str(row["version"]),
                checksum=str(row["checksum"]),
                applied_at=str(row["applied_at"]),
            )
        return applied

    def _pending_migrations(
        self,
        applied: Mapping[str, PostgreSQLAppliedMigration],
    ) -> tuple[PostgreSQLMigration, ...]:
        pending: list[PostgreSQLMigration] = []
        for name in self._catalog.list_names():
            migration = self._catalog.load(name)
            applied_migration = applied.get(migration.name)
            if applied_migration is None:
                pending.append(migration)
                continue
            if applied_migration.checksum != migration.checksum:
                raise ValidationError("applied migration checksum mismatch: " + migration.name)
        return tuple(pending)


class PostgreSQLDriver:
    def connect(self, dsn: str, profile: PostgreSQLClusterProfile) -> ConnectionProtocol:
        try:
            psycopg = importlib.import_module("psycopg")
            rows = importlib.import_module("psycopg.rows")
        except ModuleNotFoundError as exc:
            raise OpenInfraError(
                "postgresql backend requires optional dependency: "
                "pip install openinfra[postgresql]"
            ) from exc
        connect = cast(Callable[..., ConnectionProtocol], getattr(psycopg, "connect"))
        row_factory = getattr(rows, "dict_row")
        return connect(
            dsn,
            autocommit=False,
            row_factory=row_factory,
            options="-c " + profile.dsn_options().replace(" ", " -c "),
        )


class PostgreSQLConnectionFactory:
    def __init__(
        self,
        dsn: str,
        profile: PostgreSQLClusterProfile | None = None,
        connector: Callable[[str, PostgreSQLClusterProfile], ConnectionProtocol] | None = None,
    ) -> None:
        normalized = dsn.strip()
        if not normalized:
            raise ValidationError("postgresql dsn is mandatory")
        self._dsn = normalized
        self._profile = profile or PostgreSQLClusterProfile.production_default()
        self._connector = connector or PostgreSQLDriver().connect

    def create(self) -> ConnectionProtocol:
        return self._connector(self._dsn, self._profile)


class PostgreSQLSessionRegistry:
    def __init__(self, factory: PostgreSQLConnectionFactory) -> None:
        self._factory = factory
        self._local = threading.local()

    def open(self) -> ConnectionProtocol:
        return self._factory.create()

    def bind(self, connection: ConnectionProtocol) -> None:
        self._local.connection = connection

    def unbind(self) -> None:
        if hasattr(self._local, "connection"):
            del self._local.connection

    def current(self) -> ConnectionProtocol:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            raise OpenInfraError("postgresql operation requires an active unit of work")
        return connection


class PostgreSQLUnitOfWork(UnitOfWork):
    def __init__(self, registry: PostgreSQLSessionRegistry) -> None:
        self._registry = registry
        self._connection: ConnectionProtocol | None = None
        self._committed = False

    def __enter__(self) -> PostgreSQLUnitOfWork:
        connection = self._registry.open()
        self._connection = connection
        self._registry.bind(connection)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        connection = self._require_connection()
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._registry.unbind()
            connection.close()
            self._connection = None

    def commit(self) -> None:
        self._require_connection().commit()
        self._committed = True

    def rollback(self) -> None:
        self._require_connection().rollback()
        self._committed = False

    def _require_connection(self) -> ConnectionProtocol:
        if self._connection is None:
            raise OpenInfraError("postgresql unit of work is not active")
        return self._connection


class PostgreSQLReadinessProbe(ReadinessProbe):
    def __init__(
        self,
        registry: PostgreSQLSessionRegistry,
        migration_catalog: PostgreSQLMigrationCatalog | None = None,
    ) -> None:
        self._registry = registry
        self._migration_catalog = migration_catalog

    def check(self) -> ReadinessStatus:
        connection = self._registry.open()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT 1 AS ready")
            row = cursor.fetchone()
            ready_value = row.get("ready") if row else None
            if ready_value != 1:
                connection.rollback()
                return ReadinessStatus("postgresql", False, "unexpected readiness response")
            catalog = self._migration_catalog
            if catalog is not None:
                schema_status = self._check_schema(cursor, catalog)
                connection.rollback()
                if not schema_status.ready:
                    return ReadinessStatus("postgresql", False, schema_status.detail)
                return ReadinessStatus(
                    "postgresql",
                    True,
                    "postgresql connection and schema are ready",
                )
            connection.rollback()
            return ReadinessStatus("postgresql", True, "postgresql primary connection is reachable")
        except Exception as exc:
            connection.rollback()
            return ReadinessStatus("postgresql", False, f"postgresql readiness failed: {exc}")
        finally:
            cursor.close()
            connection.close()

    def _check_schema(
        self,
        cursor: CursorProtocol,
        catalog: PostgreSQLMigrationCatalog,
    ) -> PostgreSQLSchemaStatus:
        cursor.execute(
            "SELECT to_regclass('public.openinfra_schema_migrations') AS migration_table"
        )
        row = cursor.fetchone()
        if row is None or row.get("migration_table") is None:
            pending = tuple(
                catalog.load(name)
                for name in catalog.list_names()
            )
            return PostgreSQLSchemaStatus(
                False,
                (),
                pending,
                "postgresql schema history is missing; run openinfra database apply-migrations",
            )
        cursor.execute(
            """
            SELECT version, checksum, applied_at
            FROM openinfra_schema_migrations
            ORDER BY version
            """
        )
        applied: dict[str, PostgreSQLAppliedMigration] = {}
        for item in cursor.fetchall():
            applied[str(item["version"])] = PostgreSQLAppliedMigration(
                version=str(item["version"]),
                checksum=str(item["checksum"]),
                applied_at=str(item["applied_at"]),
            )
        pending: list[PostgreSQLMigration] = []
        for name in catalog.list_names():
            migration = catalog.load(name)
            applied_migration = applied.get(migration.name)
            if applied_migration is None:
                pending.append(migration)
                continue
            if applied_migration.checksum != migration.checksum:
                return PostgreSQLSchemaStatus(
                    False,
                    tuple(applied.values()),
                    (),
                    "postgresql schema checksum mismatch: " + migration.name,
                )
        detail = (
            "postgresql schema is up to date"
            if not pending
            else "postgresql schema has pending migrations"
        )
        return PostgreSQLSchemaStatus(not pending, tuple(applied.values()), tuple(pending), detail)


class PostgreSQLTransactionManager(TransactionManager):
    def __init__(self, registry: PostgreSQLSessionRegistry) -> None:
        self._registry = registry

    def begin(self) -> PostgreSQLUnitOfWork:
        return PostgreSQLUnitOfWork(self._registry)


class PostgreSQLRepositoryBase:
    def __init__(self, registry: PostgreSQLSessionRegistry) -> None:
        self._registry = registry

    def _execute(self, query: str, params: Mapping[str, object] | None = None) -> CursorProtocol:
        cursor = self._registry.current().cursor()
        try:
            cursor.execute(query, params or {})
        except Exception:
            cursor.close()
            raise
        return cursor

    def _fetch_one(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> Mapping[str, object] | None:
        cursor = self._execute(query, params)
        try:
            return cursor.fetchone()
        finally:
            cursor.close()

    def _fetch_all(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> Sequence[Mapping[str, object]]:
        cursor = self._execute(query, params)
        try:
            return cursor.fetchall()
        finally:
            cursor.close()

    def _execute_without_result(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> CursorProtocol:
        cursor = self._execute(query, params)
        cursor.close()
        return cursor

    def _ensure_tenant(self, tenant_id: TenantId) -> None:
        self._execute_without_result(
            """
            INSERT INTO tenants (id, display_name)
            VALUES (%(tenant_id)s, %(display_name)s)
            ON CONFLICT (id) DO NOTHING
            """,
            {"tenant_id": tenant_id.value, "display_name": tenant_id.value},
        )


class PostgreSQLDcimRepository(PostgreSQLRepositoryBase, DcimRepository):
    def add_site(self, site: Site) -> None:
        self._ensure_tenant(site.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sites (id, tenant_id, code, name, country, city)
            VALUES (%(id)s, %(tenant_id)s, %(code)s, %(name)s, %(country)s, %(city)s)
            """,
            {
                "id": site.id.value,
                "tenant_id": site.tenant_id.value,
                "code": site.code.value,
                "name": site.name.value,
                "country": site.country,
                "city": site.city,
            },
        )

    def add_building(self, building: Building) -> None:
        self._ensure_tenant(building.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO buildings (id, tenant_id, site_code, code, name)
            VALUES (%(id)s, %(tenant_id)s, %(site_code)s, %(code)s, %(name)s)
            """,
            {
                "id": building.id.value,
                "tenant_id": building.tenant_id.value,
                "site_code": building.site_code.value,
                "code": building.code.value,
                "name": building.name.value,
            },
        )

    def add_room(self, room: Room) -> None:
        self._ensure_tenant(room.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO rooms (id, tenant_id, site_code, building_code, code, name, rows, columns)
            VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(code)s,
                %(name)s, %(rows)s, %(columns)s
            )
            """,
            {
                "id": room.id.value,
                "tenant_id": room.tenant_id.value,
                "site_code": room.site_code.value,
                "building_code": room.building_code.value,
                "code": room.code.value,
                "name": room.name.value,
                "rows": list(room.rows),
                "columns": list(room.columns),
            },
        )

    def add_rack(self, rack: Rack) -> None:
        self._ensure_tenant(rack.tenant_id)
        coordinates = rack.coordinates
        self._execute_without_result(
            """
            INSERT INTO racks (
                id, tenant_id, site_code, building_code, room_code, code, row_code, column_code,
                units, coordinate_x, coordinate_y, coordinate_z
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(room_code)s, %(code)s,
                %(row_code)s, %(column_code)s, %(units)s, %(coordinate_x)s,
                %(coordinate_y)s, %(coordinate_z)s
            )
            """,
            {
                "id": rack.id.value,
                "tenant_id": rack.tenant_id.value,
                "site_code": rack.site_code.value,
                "building_code": rack.building_code.value,
                "room_code": rack.room_code.value,
                "code": rack.code.value,
                "row_code": rack.row,
                "column_code": rack.column,
                "units": rack.units,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
            },
        )

    def add_equipment(self, equipment: Equipment) -> None:
        self._ensure_tenant(equipment.tenant_id)
        location = equipment.location
        coordinates = location.coordinates
        self._execute_without_result(
            """
            INSERT INTO equipment (
                id, tenant_id, asset_tag, name, site_code, building_code, room_code, row_code,
                column_code, rack_code, u_position, coordinate_x, coordinate_y, coordinate_z
            ) VALUES (
                %(id)s, %(tenant_id)s, %(asset_tag)s, %(name)s, %(site_code)s, %(building_code)s,
                %(room_code)s, %(row_code)s, %(column_code)s, %(rack_code)s, %(u_position)s,
                %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s
            )
            ON CONFLICT (tenant_id, asset_tag) DO UPDATE SET
                name = EXCLUDED.name,
                site_code = EXCLUDED.site_code,
                building_code = EXCLUDED.building_code,
                room_code = EXCLUDED.room_code,
                row_code = EXCLUDED.row_code,
                column_code = EXCLUDED.column_code,
                rack_code = EXCLUDED.rack_code,
                u_position = EXCLUDED.u_position,
                coordinate_x = EXCLUDED.coordinate_x,
                coordinate_y = EXCLUDED.coordinate_y,
                coordinate_z = EXCLUDED.coordinate_z,
                version = equipment.version + 1,
                updated_at = now()
            """,
            {
                "id": equipment.id.value,
                "tenant_id": equipment.tenant_id.value,
                "asset_tag": equipment.asset_tag.value,
                "name": equipment.name.value,
                "site_code": location.site_code.value,
                "building_code": location.building_code.value,
                "room_code": location.room_code.value,
                "row_code": location.row,
                "column_code": location.column,
                "rack_code": location.rack_code.value if location.rack_code else None,
                "u_position": location.u_position,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
            },
        )

    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, code, name, rows, columns
            FROM rooms
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "code": Code.from_value(room, "room code").value,
            },
        )
        return self._room_from_row(row) if row else None

    def find_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> Rack | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, code, row_code, column_code,
                   units, coordinate_x, coordinate_y, coordinate_z
            FROM racks
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "code": Code.from_value(rack, "rack code").value,
            },
        )
        return self._rack_from_row(row) if row else None

    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, room_code, row_code,
                   column_code, rack_code, u_position, coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s AND asset_tag = %(asset_tag)s
            """,
            {
                "tenant_id": tenant_id.value,
                "asset_tag": Code.from_value(asset_tag, "asset tag").value,
            },
        )
        return self._equipment_from_row(row) if row else None

    def _room_from_row(self, row: Mapping[str, object]) -> Room:
        return Room(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            code=Code.from_value(str(row["code"]), "room code"),
            name=Name.from_value(str(row["name"]), "room name"),
            rows=tuple(str(value) for value in cast(Sequence[object], row["rows"])),
            columns=tuple(str(value) for value in cast(Sequence[object], row["columns"])),
        )

    def _rack_from_row(self, row: Mapping[str, object]) -> Rack:
        coordinates = Coordinates3D.from_values(
            self._float_or_none(row["coordinate_x"]),
            self._float_or_none(row["coordinate_y"]),
            self._float_or_none(row["coordinate_z"]),
        )
        return Rack(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            code=Code.from_value(str(row["code"]), "rack code"),
            row=str(row["row_code"]),
            column=str(row["column_code"]),
            units=int(row["units"]),
            coordinates=coordinates,
        )

    def _equipment_from_row(self, row: Mapping[str, object]) -> Equipment:
        coordinates = Coordinates3D.from_values(
            self._float_or_none(row["coordinate_x"]),
            self._float_or_none(row["coordinate_y"]),
            self._float_or_none(row["coordinate_z"]),
        )
        location = EquipmentLocation.create(
            site_code=str(row["site_code"]),
            building_code=str(row["building_code"]),
            room_code=str(row["room_code"]),
            row=str(row["row_code"]),
            column=str(row["column_code"]),
            rack_code=str(row["rack_code"]) if row["rack_code"] is not None else None,
            u_position=int(row["u_position"]) if row["u_position"] is not None else None,
            coordinates=coordinates,
        )
        return Equipment(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            asset_tag=Code.from_value(str(row["asset_tag"]), "asset tag"),
            name=Name.from_value(str(row["name"]), "equipment name"),
            location=location,
        )

    def _float_or_none(self, value: object) -> float | None:
        return None if value is None else float(value)


class PostgreSQLIpamRepository(PostgreSQLRepositoryBase, IpamRepository):
    def add_vrf(self, vrf: Vrf) -> None:
        self._ensure_tenant(vrf.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO vrfs (id, tenant_id, name, route_distinguisher)
            VALUES (%(id)s, %(tenant_id)s, %(name)s, %(route_distinguisher)s)
            ON CONFLICT (tenant_id, name) DO NOTHING
            """,
            {
                "id": vrf.id.value,
                "tenant_id": vrf.tenant_id.value,
                "name": vrf.name.value,
                "route_distinguisher": vrf.route_distinguisher,
            },
        )

    def get_or_create_prefix(self, prefix: Prefix) -> Prefix:
        self._ensure_tenant(prefix.tenant_id)
        self.add_vrf(Vrf.create(prefix.tenant_id, prefix.vrf_name.value))
        row = self._fetch_one(
            """
            INSERT INTO prefixes (
                id, tenant_id, vrf_name, cidr, family, first_usable, last_usable, description
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(cidr)s, %(family)s,
                %(first_usable)s, %(last_usable)s, %(description)s
            )
            ON CONFLICT (tenant_id, vrf_name, cidr) DO UPDATE SET description = prefixes.description
            RETURNING id, tenant_id, vrf_name, cidr, description
            """,
            {
                "id": prefix.id.value,
                "tenant_id": prefix.tenant_id.value,
                "vrf_name": prefix.vrf_name.value,
                "cidr": str(prefix.network),
                "family": prefix.network.version,
                "first_usable": str(ipaddress.ip_address(prefix.first_usable_int)),
                "last_usable": str(ipaddress.ip_address(prefix.last_usable_int)),
                "description": prefix.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return prefix after upsert")
        return self._prefix_from_row(row)

    def find_reservation_by_key(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        idempotency_key: str,
    ) -> IpReservation | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, address, hostname, idempotency_key
            FROM ip_reservations
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND idempotency_key = %(idempotency_key)s
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "idempotency_key": idempotency_key.strip(),
            },
        )
        return self._reservation_from_row(row) if row else None

    def list_reservations(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpReservation, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, address, hostname, idempotency_key
            FROM ip_reservations
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND prefix_cidr = %(prefix_cidr)s
            ORDER BY address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "prefix_cidr": prefix_cidr,
            },
        )
        return tuple(self._reservation_from_row(row) for row in rows)

    def add_reservation(self, reservation: IpReservation) -> None:
        try:
            self._execute_without_result(
                """
                INSERT INTO ip_reservations (
                    id, tenant_id, vrf_name, prefix_cidr, address, hostname, idempotency_key
                ) VALUES (
                    %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(address)s,
                    %(hostname)s, %(idempotency_key)s
                )
                """,
                {
                    "id": reservation.id.value,
                    "tenant_id": reservation.tenant_id.value,
                    "vrf_name": reservation.vrf_name.value,
                    "prefix_cidr": reservation.prefix,
                    "address": str(reservation.address),
                    "hostname": reservation.hostname,
                    "idempotency_key": reservation.idempotency_key,
                },
            )
        except Exception as exc:
            raise ConflictError(
                f"duplicate or invalid ip reservation: {reservation.address}"
            ) from exc

    def _prefix_from_row(self, row: Mapping[str, object]) -> Prefix:
        return Prefix(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            network=ipaddress.ip_network(str(row["cidr"]), strict=True),
            description=str(row["description"] or ""),
        )

    def _reservation_from_row(self, row: Mapping[str, object]) -> IpReservation:
        prefix = Prefix.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
        )
        reservation = IpReservation.create(
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=str(row["vrf_name"]),
            prefix=prefix,
            address=str(row["address"]),
            hostname=str(row["hostname"]),
            idempotency_key=str(row["idempotency_key"]),
        )
        return IpReservation(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=reservation.tenant_id,
            vrf_name=reservation.vrf_name,
            prefix=reservation.prefix,
            address=reservation.address,
            hostname=reservation.hostname,
            idempotency_key=reservation.idempotency_key,
        )


class PostgreSQLIdentityRepository(PostgreSQLRepositoryBase, IdentityRepository):
    def upsert_user(self, user: IdentityUser) -> None:
        self._ensure_tenant(user.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO identity_users (
                id, tenant_id, username, display_name, email, roles, active
            ) VALUES (
                %(id)s, %(tenant_id)s, %(username)s, %(display_name)s, %(email)s,
                %(roles)s, %(active)s
            )
            ON CONFLICT (tenant_id, username) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                email = EXCLUDED.email,
                roles = EXCLUDED.roles,
                active = EXCLUDED.active,
                updated_at = now()
            """,
            {
                "id": user.id.value,
                "tenant_id": user.tenant_id.value,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "roles": list(user.role_names()),
                "active": user.active,
            },
        )

    def upsert_group(self, group: IdentityGroup) -> None:
        self._ensure_tenant(group.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO identity_groups (
                id, tenant_id, name, display_name, roles, active
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(display_name)s, %(roles)s,
                %(active)s
            )
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                roles = EXCLUDED.roles,
                active = EXCLUDED.active,
                updated_at = now()
            """,
            {
                "id": group.id.value,
                "tenant_id": group.tenant_id.value,
                "name": group.name,
                "display_name": group.display_name,
                "roles": list(group.role_names()),
                "active": group.active,
            },
        )

    def add_membership(self, membership: GroupMembership) -> None:
        self._ensure_tenant(membership.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO identity_group_memberships (tenant_id, username, group_name)
            VALUES (%(tenant_id)s, %(username)s, %(group_name)s)
            ON CONFLICT (tenant_id, username, group_name) DO NOTHING
            """,
            {
                "tenant_id": membership.tenant_id.value,
                "username": membership.username,
                "group_name": membership.group_name,
            },
        )

    def grant_user_role(self, tenant_id: TenantId, username: str, role: str) -> bool:
        normalized_user = IdentitySubject.normalize(username)
        normalized_role = IdentityRoleSet.from_names((role,))[0].name
        row = self._fetch_one(
            """
            SELECT roles
            FROM identity_users
            WHERE tenant_id = %(tenant_id)s AND username = %(username)s
            """,
            {"tenant_id": tenant_id.value, "username": normalized_user},
        )
        if row is None:
            raise ValidationError("identity user must exist before granting a role")
        roles = {str(item) for item in cast(Sequence[object], row.get("roles", []))}
        changed = normalized_role not in roles
        roles.add(normalized_role)
        self._execute_without_result(
            """
            UPDATE identity_users
            SET roles = %(roles)s, updated_at = now()
            WHERE tenant_id = %(tenant_id)s AND username = %(username)s
            """,
            {
                "tenant_id": tenant_id.value,
                "username": normalized_user,
                "roles": sorted(roles),
            },
        )
        return changed

    def grant_group_role(self, tenant_id: TenantId, group_name: str, role: str) -> bool:
        normalized_group = IdentityGroupName.normalize(group_name)
        normalized_role = IdentityRoleSet.from_names((role,))[0].name
        row = self._fetch_one(
            """
            SELECT roles
            FROM identity_groups
            WHERE tenant_id = %(tenant_id)s AND name = %(group_name)s
            """,
            {"tenant_id": tenant_id.value, "group_name": normalized_group},
        )
        if row is None:
            raise ValidationError("identity group must exist before granting a role")
        roles = {str(item) for item in cast(Sequence[object], row.get("roles", []))}
        changed = normalized_role not in roles
        roles.add(normalized_role)
        self._execute_without_result(
            """
            UPDATE identity_groups
            SET roles = %(roles)s, updated_at = now()
            WHERE tenant_id = %(tenant_id)s AND name = %(group_name)s
            """,
            {
                "tenant_id": tenant_id.value,
                "group_name": normalized_group,
                "roles": sorted(roles),
            },
        )
        return changed

    def effective_identity_for_subject(
        self,
        tenant_id: TenantId,
        subject: str,
    ) -> EffectiveIdentity:
        normalized_subject = IdentitySubject.normalize(subject)
        user_row = self._fetch_one(
            """
            SELECT id, tenant_id, username, display_name, email, roles, active, created_at
            FROM identity_users
            WHERE tenant_id = %(tenant_id)s AND username = %(username)s
            """,
            {"tenant_id": tenant_id.value, "username": normalized_subject},
        )
        if user_row is None:
            return EffectiveIdentity.empty(tenant_id, normalized_subject)
        user = self._user_from_row(user_row)
        rows = self._fetch_all(
            """
            SELECT g.name AS group_name, g.roles AS group_roles
            FROM identity_group_memberships m
            JOIN identity_groups g
              ON g.tenant_id = m.tenant_id AND g.name = m.group_name
            WHERE m.tenant_id = %(tenant_id)s
              AND m.username = %(username)s
              AND g.active = true
            ORDER BY g.name ASC
            """,
            {"tenant_id": tenant_id.value, "username": normalized_subject},
        )
        group_names: list[str] = []
        group_roles: list[str] = []
        for row in rows:
            group_names.append(str(row["group_name"]))
            group_roles.extend(str(role) for role in cast(Sequence[object], row["group_roles"]))
        return EffectiveIdentity.from_parts(user, tuple(group_names), tuple(group_roles))

    def _user_from_row(self, row: Mapping[str, object]) -> IdentityUser:
        roles = row["roles"]
        return IdentityUser.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            email=str(row["email"]) if row.get("email") is not None else None,
            roles=tuple(str(role) for role in cast(Sequence[object], roles)),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLSecurityRepository(PostgreSQLRepositoryBase, SecurityRepository):
    def upsert_token(self, credential: ApiTokenCredential) -> None:
        self._ensure_tenant(credential.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO api_tokens (
                id, tenant_id, subject, token_hash, token_prefix, roles, active,
                expires_at, revoked_at, revoked_by, last_used_at, use_count
            ) VALUES (
                %(id)s, %(tenant_id)s, %(subject)s, %(token_hash)s,
                %(token_prefix)s, %(roles)s, %(active)s, %(expires_at)s,
                %(revoked_at)s, %(revoked_by)s, %(last_used_at)s, %(use_count)s
            )
            ON CONFLICT (tenant_id, token_hash) DO UPDATE SET
                subject = EXCLUDED.subject,
                token_prefix = EXCLUDED.token_prefix,
                roles = EXCLUDED.roles,
                active = EXCLUDED.active,
                expires_at = EXCLUDED.expires_at,
                revoked_at = EXCLUDED.revoked_at,
                revoked_by = EXCLUDED.revoked_by,
                last_used_at = COALESCE(api_tokens.last_used_at, EXCLUDED.last_used_at),
                use_count = GREATEST(api_tokens.use_count, EXCLUDED.use_count)
            """,
            {
                "id": credential.id.value,
                "tenant_id": credential.tenant_id.value,
                "subject": credential.subject,
                "token_hash": credential.token_hash,
                "token_prefix": credential.token_prefix,
                "roles": list(credential.role_names()),
                "active": credential.active,
                "expires_at": credential.expires_at,
                "revoked_at": credential.revoked_at,
                "revoked_by": credential.revoked_by,
                "last_used_at": credential.last_used_at,
                "use_count": credential.use_count,
            },
        )

    def find_active_token_by_hash(
        self,
        tenant_id: TenantId,
        token_hash: str,
    ) -> ApiTokenCredential | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, subject, token_hash, token_prefix, roles, active, created_at,
                   expires_at, revoked_at, revoked_by, last_used_at, use_count
            FROM api_tokens
            WHERE tenant_id = %(tenant_id)s
              AND token_hash = %(token_hash)s
              AND active = true
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > now())
            """,
            {"tenant_id": tenant_id.value, "token_hash": token_hash},
        )
        return self._credential_from_row(row) if row else None

    def revoke_token(self, tenant_id: TenantId, token_hash: str, actor: str) -> bool:
        updated = self._execute_without_result(
            """
            UPDATE api_tokens
            SET active = false, revoked_at = now(), revoked_by = %(actor)s
            WHERE tenant_id = %(tenant_id)s
              AND token_hash = %(token_hash)s
              AND active = true
              AND revoked_at IS NULL
            """,
            {"tenant_id": tenant_id.value, "token_hash": token_hash, "actor": actor},
        )
        rowcount = getattr(updated, "rowcount", None)
        return True if rowcount is None else int(rowcount) > 0

    def list_tokens(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> SecurityTokenPage:
        try:
            cursor_offset = int(pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if cursor_offset < 0:
            raise ValidationError("pagination cursor must be positive")
        predicate = "tenant_id = %(tenant_id)s"
        if not include_inactive:
            predicate += (
                " AND active = true"
                " AND revoked_at IS NULL"
                " AND (expires_at IS NULL OR expires_at > now())"
            )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, subject, token_hash, token_prefix, roles, active, created_at,
                   expires_at, revoked_at, revoked_by, last_used_at, use_count
            FROM api_tokens
            WHERE {predicate}
            ORDER BY created_at ASC, id ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "limit": pagination.limit + 1,
                "offset": cursor_offset,
            },
        )
        selected_rows = tuple(rows[: pagination.limit])
        credentials = tuple(self._credential_from_row(row) for row in selected_rows)
        next_cursor = (
            str(cursor_offset + pagination.limit) if len(rows) > pagination.limit else None
        )
        return SecurityTokenPage(credentials, next_cursor)

    def record_token_used(self, tenant_id: TenantId, token_hash: str) -> None:
        self._execute_without_result(
            """
            UPDATE api_tokens
            SET last_used_at = now(), use_count = use_count + 1
            WHERE tenant_id = %(tenant_id)s AND token_hash = %(token_hash)s AND active = true
            """,
            {"tenant_id": tenant_id.value, "token_hash": token_hash},
        )

    def _credential_from_row(self, row: Mapping[str, object]) -> ApiTokenCredential:
        roles = row["roles"]
        return ApiTokenCredential.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            subject=str(row["subject"]),
            token_hash=str(row["token_hash"]),
            token_prefix=str(row["token_prefix"]),
            roles=tuple(str(role) for role in cast(Sequence[object], roles)),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
            expires_at=self._row_optional_datetime(row.get("expires_at")),
            revoked_at=self._row_optional_datetime(row.get("revoked_at")),
            revoked_by=str(row["revoked_by"]) if row.get("revoked_by") is not None else None,
            last_used_at=self._row_optional_datetime(row.get("last_used_at")),
            use_count=int(row.get("use_count", 0)),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    def _row_optional_datetime(self, value: object | None) -> datetime | None:
        if value is None:
            return None
        return self._row_datetime(value)


class PostgreSQLAccessPolicyRepository(PostgreSQLRepositoryBase, AccessPolicyRepository):
    def upsert_rule(self, rule: AccessPolicyRule) -> None:
        self._ensure_tenant(rule.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO access_policy_rules (
                id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                environments, active, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(permission)s, %(effect)s,
                %(subjects)s, %(roles)s, %(site_codes)s, %(environments)s,
                %(active)s, %(created_at)s
            )
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                permission = EXCLUDED.permission,
                effect = EXCLUDED.effect,
                subjects = EXCLUDED.subjects,
                roles = EXCLUDED.roles,
                site_codes = EXCLUDED.site_codes,
                environments = EXCLUDED.environments,
                active = EXCLUDED.active,
                updated_at = now()
            """,
            {
                "id": rule.id.value,
                "tenant_id": rule.tenant_id.value,
                "name": rule.name,
                "permission": rule.permission.value,
                "effect": rule.effect.value,
                "subjects": list(rule.subjects),
                "roles": list(rule.role_names()),
                "site_codes": list(rule.site_codes),
                "environments": list(rule.environments),
                "active": rule.active,
                "created_at": rule.created_at,
            },
        )

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> AccessPolicyRulePage:
        try:
            cursor_offset = int(pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if cursor_offset < 0:
            raise ValidationError("pagination cursor must be positive")
        predicate = "tenant_id = %(tenant_id)s"
        if not include_inactive:
            predicate += " AND active = true"
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                   environments, active, created_at
            FROM access_policy_rules
            WHERE {predicate}
            ORDER BY name ASC, id ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "limit": pagination.limit + 1,
                "offset": cursor_offset,
            },
        )
        selected_rows = tuple(rows[: pagination.limit])
        next_cursor = (
            str(cursor_offset + pagination.limit) if len(rows) > pagination.limit else None
        )
        return AccessPolicyRulePage(
            tuple(self._rule_from_row(row) for row in selected_rows),
            next_cursor,
        )

    def find_active_rules_for_permission(
        self,
        tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[AccessPolicyRule, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                   environments, active, created_at
            FROM access_policy_rules
            WHERE tenant_id = %(tenant_id)s
              AND permission = %(permission)s
              AND active = true
            ORDER BY name ASC, id ASC
            """,
            {"tenant_id": tenant_id.value, "permission": permission.value},
        )
        return tuple(self._rule_from_row(row) for row in rows)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        normalized_name = AccessPolicyRule.create(
            tenant_id,
            name,
            Permission.SCHEMA_READ,
            "allow",
        ).name
        cursor = self._execute_without_result(
            """
            UPDATE access_policy_rules
            SET active = false, updated_at = now()
            WHERE tenant_id = %(tenant_id)s AND name = %(name)s AND active = true
            """,
            {"tenant_id": tenant_id.value, "name": normalized_name},
        )
        rowcount = getattr(cursor, "rowcount", None)
        return True if rowcount is None else int(rowcount) > 0

    def _rule_from_row(self, row: Mapping[str, object]) -> AccessPolicyRule:
        return AccessPolicyRule.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=str(row["name"]),
            permission=str(row["permission"]),
            effect=str(row["effect"]),
            subjects=tuple(str(item) for item in cast(Sequence[object], row["subjects"])),
            roles=tuple(str(item) for item in cast(Sequence[object], row["roles"])),
            site_codes=tuple(str(item) for item in cast(Sequence[object], row["site_codes"])),
            environments=tuple(
                str(item) for item in cast(Sequence[object], row["environments"])
            ),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLAuditRepository(PostgreSQLRepositoryBase, AuditRepository):
    def append(self, event: AuditEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO audit_events (
                id, tenant_id, actor, action, target_type, target_id, severity, metadata, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(actor)s, %(action)s, %(target_type)s, %(target_id)s,
                %(severity)s, %(metadata)s, %(created_at)s
            )
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "actor": event.actor,
                "action": event.action,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "severity": event.severity.value,
                "metadata": json.dumps(event.metadata, sort_keys=True),
                "created_at": event.created_at,
            },
        )

    def list_events(self, tenant_id: TenantId, limit: int = 100) -> tuple[AuditEvent, ...]:
        if not 1 <= limit <= 500:
            raise ValidationError("audit list limit must be between 1 and 500")
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, actor, action, target_type, target_id, severity,
                   metadata, created_at
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at DESC, id DESC
            LIMIT %(limit)s
            """,
            {"tenant_id": tenant_id.value, "limit": limit},
        )
        return tuple(self._event_from_row(row) for row in rows)

    def _event_from_row(self, row: Mapping[str, object]) -> AuditEvent:
        metadata = row["metadata"]
        created_at = row["created_at"]
        if not isinstance(created_at, datetime):
            raise ValidationError("audit event created_at must be a datetime")
        return AuditEvent(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            actor=str(row["actor"]),
            action=str(row["action"]),
            target_type=str(row["target_type"]),
            target_id=str(row["target_id"]),
            severity=Severity(str(row["severity"])),
            created_at=created_at,
            metadata=(
                json.loads(str(metadata))
                if isinstance(metadata, str)
                else dict(cast(Mapping[str, Any], metadata))
            ),
        )
