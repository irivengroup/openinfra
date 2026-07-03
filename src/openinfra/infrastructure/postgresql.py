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
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
    UnitOfWork,
)
from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.audit import (
    AuditEventFilter,
    AuditEventPage,
    AuditEventRecord,
    AuditIntegrityHasher,
    AuditIntegrityReport,
)
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
from openinfra.domain.dcim import (
    Building,
    CoolingRole,
    CoolingZone,
    DcimCable,
    DcimCableMedium,
    DcimCablePathSegment,
    DcimCableStatus,
    DcimConnectorType,
    DcimPort,
    DcimPortEndpoint,
    DcimPortOwnerType,
    Equipment,
    EquipmentLocation,
    Floor,
    PatchPanel,
    PowerCircuit,
    PowerDevice,
    PowerDeviceKind,
    PowerFeedSide,
    Rack,
    RackFace,
    RackPowerReservation,
    Room,
    RoomZone,
    Site,
)
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
    IdentityUser,
)
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpAddressFamily,
    BgpPeer,
    IpAddressRecord,
    IpAggregate,
    IpRange,
    IpReservation,
    Prefix,
    Vlan,
    VlanGroup,
    Vrf,
    VxlanVni,
)
from openinfra.domain.security import ApiTokenCredential, Permission
from openinfra.domain.source_governance import SourceGovernanceRule, SourceGovernanceRulePage
from openinfra.domain.source_of_truth import (
    SourceObjectPage,
    SourceObjectSnapshot,
    SourceOfTruthObject,
    SourceRelation,
    SourceRelationPage,
)


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
                "postgresql backend requires optional dependency: pip install openinfra[postgresql]"
            ) from exc
        connect = cast(Callable[..., ConnectionProtocol], psycopg.connect)
        row_factory = rows.dict_row
        try:
            return connect(
                dsn,
                autocommit=False,
                row_factory=row_factory,
                options="-c " + profile.dsn_options().replace(" ", " -c "),
            )
        except Exception as exc:  # pragma: no cover - depends on external PostgreSQL runtime
            raise OpenInfraError("postgresql connection failed: " + str(exc)) from exc


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
        return cast(ConnectionProtocol, connection)


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
            missing_history_pending = tuple(catalog.load(name) for name in catalog.list_names())
            return PostgreSQLSchemaStatus(
                False,
                (),
                missing_history_pending,
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

    def _row_int(self, row: Mapping[str, object], key: str) -> int:
        return int(str(row[key]))

    def _row_int_or_default(self, row: Mapping[str, object], key: str, default: int) -> int:
        value = row.get(key)
        return default if value is None else int(str(value))

    def _row_float(self, row: Mapping[str, object], key: str) -> float:
        return float(str(row[key]))

    def _row_sequence(self, row: Mapping[str, object], key: str) -> Sequence[object]:
        return cast(Sequence[object], row[key])

    def _row_optional_sequence(
        self,
        row: Mapping[str, object],
        key: str,
        default: Sequence[object],
    ) -> Sequence[object]:
        value = row.get(key)
        return default if value is None else cast(Sequence[object], value)


class PostgreSQLDcimRepository(PostgreSQLRepositoryBase, DcimRepository):
    def add_site(self, site: Site) -> None:
        self._ensure_tenant(site.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sites (id, tenant_id, code, name, country, city, region)
            VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(name)s, %(country)s,
                %(city)s, %(region)s
            )
            ON CONFLICT (tenant_id, code) DO NOTHING
            """,
            {
                "id": site.id.value,
                "tenant_id": site.tenant_id.value,
                "code": site.code.value,
                "name": site.name.value,
                "country": site.country,
                "city": site.city,
                "region": site.region,
            },
        )

    def add_building(self, building: Building) -> None:
        self._ensure_tenant(building.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO buildings (id, tenant_id, site_code, code, name)
            VALUES (%(id)s, %(tenant_id)s, %(site_code)s, %(code)s, %(name)s)
            ON CONFLICT (tenant_id, site_code, code) DO NOTHING
            """,
            {
                "id": building.id.value,
                "tenant_id": building.tenant_id.value,
                "site_code": building.site_code.value,
                "code": building.code.value,
                "name": building.name.value,
            },
        )

    def add_floor(self, floor: Floor) -> None:
        self._ensure_tenant(floor.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO floors (id, tenant_id, site_code, building_code, code, name, level_index)
            VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s,
                %(code)s, %(name)s, %(level_index)s
            )
            ON CONFLICT (tenant_id, site_code, building_code, code) DO NOTHING
            """,
            {
                "id": floor.id.value,
                "tenant_id": floor.tenant_id.value,
                "site_code": floor.site_code.value,
                "building_code": floor.building_code.value,
                "code": floor.code.value,
                "name": floor.name.value,
                "level_index": floor.level_index,
            },
        )

    def add_room(self, room: Room) -> None:
        self._ensure_tenant(room.tenant_id)
        coordinates = room.coordinates
        self._execute_without_result(
            """
            INSERT INTO rooms (
                id, tenant_id, site_code, building_code, floor_code, code, name, rows, columns,
                zone_codes, coordinate_x, coordinate_y, coordinate_z
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(floor_code)s,
                %(code)s, %(name)s, %(rows)s, %(columns)s, %(zone_codes)s,
                %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s
            )
            ON CONFLICT (tenant_id, site_code, building_code, code) DO NOTHING
            """,
            {
                "id": room.id.value,
                "tenant_id": room.tenant_id.value,
                "site_code": room.site_code.value,
                "building_code": room.building_code.value,
                "floor_code": room.floor_code.value if room.floor_code else None,
                "code": room.code.value,
                "name": room.name.value,
                "rows": list(room.rows),
                "columns": list(room.columns),
                "zone_codes": [zone.value for zone in room.zone_codes],
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
            },
        )

    def add_zone(self, zone: RoomZone) -> None:
        self._ensure_tenant(zone.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO room_zones (
                id, tenant_id, site_code, building_code, floor_code, room_code, code,
                name, rows, columns
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(floor_code)s,
                %(room_code)s, %(code)s, %(name)s, %(rows)s, %(columns)s
            )
            ON CONFLICT (tenant_id, site_code, building_code, room_code, code) DO NOTHING
            """,
            {
                "id": zone.id.value,
                "tenant_id": zone.tenant_id.value,
                "site_code": zone.site_code.value,
                "building_code": zone.building_code.value,
                "floor_code": zone.floor_code.value,
                "room_code": zone.room_code.value,
                "code": zone.code.value,
                "name": zone.name.value,
                "rows": list(zone.rows),
                "columns": list(zone.columns),
            },
        )

    def add_rack(self, rack: Rack) -> None:
        self._ensure_tenant(rack.tenant_id)
        coordinates = rack.coordinates
        self._execute_without_result(
            """
            INSERT INTO racks (
                id, tenant_id, site_code, building_code, floor_code, room_code, code,
                row_code, column_code, zone_code, units, coordinate_x, coordinate_y, coordinate_z,
                usable_faces, max_weight_kg, power_capacity_watts
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(floor_code)s,
                %(room_code)s, %(code)s, %(row_code)s, %(column_code)s, %(zone_code)s,
                %(units)s, %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s,
                %(usable_faces)s, %(max_weight_kg)s, %(power_capacity_watts)s
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
                "floor_code": rack.floor_code.value if rack.floor_code else None,
                "zone_code": rack.zone_code.value if rack.zone_code else None,
                "units": rack.units,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
                "usable_faces": [face.value for face in rack.usable_faces],
                "max_weight_kg": rack.max_weight_kg,
                "power_capacity_watts": rack.power_capacity_watts,
            },
        )

    def add_patch_panel(self, patch_panel: PatchPanel) -> None:
        self._ensure_tenant(patch_panel.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_patch_panels (
                id, tenant_id, site_code, building_code, room_code, rack_code, code,
                rack_face, u_position, u_height, port_count, connector, medium, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(room_code)s,
                %(rack_code)s, %(code)s, %(rack_face)s, %(u_position)s, %(u_height)s,
                %(port_count)s, %(connector)s, %(medium)s, %(label)s
            )
            """,
            {
                "id": patch_panel.id.value,
                "tenant_id": patch_panel.tenant_id.value,
                "site_code": patch_panel.site_code.value,
                "building_code": patch_panel.building_code.value,
                "room_code": patch_panel.room_code.value,
                "rack_code": patch_panel.rack_code.value,
                "code": patch_panel.code.value,
                "rack_face": patch_panel.rack_face.value,
                "u_position": patch_panel.u_position,
                "u_height": patch_panel.u_height,
                "port_count": patch_panel.port_count,
                "connector": patch_panel.connector.value,
                "medium": patch_panel.medium.value,
                "label": patch_panel.label,
            },
        )

    def add_dcim_port(self, port: DcimPort) -> None:
        self._ensure_tenant(port.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_ports (
                id, tenant_id, owner_type, owner_code, port_name, site_code,
                building_code, room_code, connector, medium, enabled
            ) VALUES (
                %(id)s, %(tenant_id)s, %(owner_type)s, %(owner_code)s, %(port_name)s,
                %(site_code)s, %(building_code)s, %(room_code)s, %(connector)s,
                %(medium)s, %(enabled)s
            )
            """,
            {
                "id": port.id.value,
                "tenant_id": port.tenant_id.value,
                "owner_type": port.endpoint.owner_type.value,
                "owner_code": port.endpoint.owner_code.value,
                "port_name": port.endpoint.port_name.value,
                "site_code": port.site_code.value,
                "building_code": port.building_code.value,
                "room_code": port.room_code.value,
                "connector": port.connector.value,
                "medium": port.medium.value,
                "enabled": port.enabled,
            },
        )

    def add_dcim_cable(self, cable: DcimCable) -> None:
        self._ensure_tenant(cable.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_cables (
                id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                length_m, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(cable_id)s, %(a_owner_type)s, %(a_owner_code)s,
                %(a_port_name)s, %(b_owner_type)s, %(b_owner_code)s, %(b_port_name)s,
                %(medium)s, %(status)s, %(path_segments)s, %(length_m)s, %(label)s
            )
            """,
            {
                "id": cable.id.value,
                "tenant_id": cable.tenant_id.value,
                "cable_id": cable.cable_id.value,
                "a_owner_type": cable.a_endpoint.owner_type.value,
                "a_owner_code": cable.a_endpoint.owner_code.value,
                "a_port_name": cable.a_endpoint.port_name.value,
                "b_owner_type": cable.b_endpoint.owner_type.value,
                "b_owner_code": cable.b_endpoint.owner_code.value,
                "b_port_name": cable.b_endpoint.port_name.value,
                "medium": cable.medium.value,
                "status": cable.status.value,
                "path_segments": json.dumps([segment.as_dict() for segment in cable.path]),
                "length_m": cable.length_m,
                "label": cable.label,
            },
        )

    def add_equipment(self, equipment: Equipment) -> None:
        self._ensure_tenant(equipment.tenant_id)
        location = equipment.location
        coordinates = location.coordinates
        self._execute_without_result(
            """
            INSERT INTO equipment (
                id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                coordinate_x, coordinate_y, coordinate_z
            ) VALUES (
                %(id)s, %(tenant_id)s, %(asset_tag)s, %(name)s, %(site_code)s, %(building_code)s,
                %(floor_code)s, %(room_code)s, %(row_code)s, %(column_code)s, %(zone_code)s,
                %(rack_code)s, %(u_position)s, %(rack_face)s, %(u_height)s,
                %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s
            )
            ON CONFLICT (tenant_id, asset_tag) DO UPDATE SET
                name = EXCLUDED.name,
                site_code = EXCLUDED.site_code,
                building_code = EXCLUDED.building_code,
                floor_code = EXCLUDED.floor_code,
                room_code = EXCLUDED.room_code,
                row_code = EXCLUDED.row_code,
                column_code = EXCLUDED.column_code,
                zone_code = EXCLUDED.zone_code,
                rack_code = EXCLUDED.rack_code,
                u_position = EXCLUDED.u_position,
                rack_face = EXCLUDED.rack_face,
                u_height = EXCLUDED.u_height,
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
                "floor_code": location.floor_code.value if location.floor_code else None,
                "room_code": location.room_code.value,
                "row_code": location.row,
                "column_code": location.column,
                "zone_code": location.zone_code.value if location.zone_code else None,
                "rack_code": location.rack_code.value if location.rack_code else None,
                "u_position": location.u_position,
                "rack_face": location.rack_face.value if location.rack_face else None,
                "u_height": location.u_height,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
            },
        )

    def add_power_device(self, power_device: PowerDevice) -> None:
        self._ensure_tenant(power_device.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_power_devices (
                id, tenant_id, code, kind, site_code, building_code, room_code, rack_code,
                side, capacity_watts, derating_percent, input_source, output_voltage, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(kind)s, %(site_code)s, %(building_code)s,
                %(room_code)s, %(rack_code)s, %(side)s, %(capacity_watts)s,
                %(derating_percent)s, %(input_source)s, %(output_voltage)s, %(label)s
            )
            """,
            {
                "id": power_device.id.value,
                "tenant_id": power_device.tenant_id.value,
                "code": power_device.code.value,
                "kind": power_device.kind.value,
                "site_code": power_device.site_code.value,
                "building_code": power_device.building_code.value,
                "room_code": power_device.room_code.value,
                "rack_code": power_device.rack_code.value if power_device.rack_code else None,
                "side": power_device.side.value if power_device.side else None,
                "capacity_watts": power_device.capacity_watts,
                "derating_percent": power_device.derating_percent,
                "input_source": power_device.input_source,
                "output_voltage": power_device.output_voltage,
                "label": power_device.label,
            },
        )

    def add_power_circuit(self, circuit: PowerCircuit) -> None:
        self._ensure_tenant(circuit.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_power_circuits (
                id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                redundancy_group, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(circuit_id)s, %(source_device_code)s,
                %(site_code)s, %(building_code)s, %(room_code)s, %(rack_code)s, %(side)s,
                %(capacity_watts)s, %(breaker_rating_amps)s, %(redundancy_group)s, %(label)s
            )
            """,
            {
                "id": circuit.id.value,
                "tenant_id": circuit.tenant_id.value,
                "circuit_id": circuit.circuit_id.value,
                "source_device_code": circuit.source_device_code.value,
                "site_code": circuit.site_code.value,
                "building_code": circuit.building_code.value,
                "room_code": circuit.room_code.value,
                "rack_code": circuit.rack_code.value,
                "side": circuit.side.value,
                "capacity_watts": circuit.capacity_watts,
                "breaker_rating_amps": circuit.breaker_rating_amps,
                "redundancy_group": circuit.redundancy_group,
                "label": circuit.label,
            },
        )

    def add_cooling_zone(self, cooling_zone: CoolingZone) -> None:
        self._ensure_tenant(cooling_zone.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_cooling_zones (
                id, tenant_id, site_code, building_code, room_code, zone_code, role,
                cooling_capacity_watts, supply_temperature_c, return_temperature_c, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(room_code)s,
                %(zone_code)s, %(role)s, %(cooling_capacity_watts)s,
                %(supply_temperature_c)s, %(return_temperature_c)s, %(label)s
            )
            """,
            {
                "id": cooling_zone.id.value,
                "tenant_id": cooling_zone.tenant_id.value,
                "site_code": cooling_zone.site_code.value,
                "building_code": cooling_zone.building_code.value,
                "room_code": cooling_zone.room_code.value,
                "zone_code": cooling_zone.zone_code.value,
                "role": cooling_zone.role.value,
                "cooling_capacity_watts": cooling_zone.cooling_capacity_watts,
                "supply_temperature_c": cooling_zone.supply_temperature_c,
                "return_temperature_c": cooling_zone.return_temperature_c,
                "label": cooling_zone.label,
            },
        )

    def add_power_reservation(self, reservation: RackPowerReservation) -> None:
        self._ensure_tenant(reservation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_power_reservations (
                id, tenant_id, asset_tag, circuit_id, side, site_code, building_code,
                room_code, rack_code, expected_watts, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(asset_tag)s, %(circuit_id)s, %(side)s,
                %(site_code)s, %(building_code)s, %(room_code)s, %(rack_code)s,
                %(expected_watts)s, %(label)s
            )
            """,
            {
                "id": reservation.id.value,
                "tenant_id": reservation.tenant_id.value,
                "asset_tag": reservation.asset_tag.value,
                "circuit_id": reservation.circuit_id.value,
                "side": reservation.side.value,
                "site_code": reservation.site_code.value,
                "building_code": reservation.building_code.value,
                "room_code": reservation.room_code.value,
                "rack_code": reservation.rack_code.value,
                "expected_watts": reservation.expected_watts,
                "label": reservation.label,
            },
        )

    def find_site(self, tenant_id: TenantId, site: str) -> Site | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, code, name, country, city, region
            FROM sites
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "code": Code.from_value(site, "site code").value,
            },
        )
        return self._site_from_row(row) if row else None

    def find_building(self, tenant_id: TenantId, site: str, building: str) -> Building | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, code, name
            FROM buildings
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "code": Code.from_value(building, "building code").value,
            },
        )
        return self._building_from_row(row) if row else None

    def find_floor(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        floor: str,
    ) -> Floor | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, code, name, level_index
            FROM floors
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "code": Code.from_value(floor, "floor code").value,
            },
        )
        return self._floor_from_row(row) if row else None

    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, floor_code, code, name, rows, columns,
                   zone_codes, coordinate_x, coordinate_y, coordinate_z
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

    def find_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> RoomZone | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   name, rows, columns
            FROM room_zones
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
                "code": Code.from_value(zone, "zone code").value,
            },
        )
        return self._zone_from_row(row) if row else None

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
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   row_code, column_code, zone_code, units,
                   coordinate_x, coordinate_y, coordinate_z, usable_faces,
                   max_weight_kg, power_capacity_watts
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

    def find_patch_panel(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
        patch_panel: str,
    ) -> PatchPanel | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, rack_code, code,
                   rack_face, u_position, u_height, port_count, connector, medium, label
            FROM dcim_patch_panels
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
                "code": Code.from_value(patch_panel, "patch panel code").value,
            },
        )
        return self._patch_panel_from_row(row) if row else None

    def find_dcim_port(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimPort | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, owner_type, owner_code, port_name, site_code,
                   building_code, room_code, connector, medium, enabled
            FROM dcim_ports
            WHERE tenant_id = %(tenant_id)s AND owner_type = %(owner_type)s
              AND owner_code = %(owner_code)s AND port_name = %(port_name)s
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": endpoint.owner_type.value,
                "owner_code": endpoint.owner_code.value,
                "port_name": endpoint.port_name.value,
            },
        )
        return self._dcim_port_from_row(row) if row else None

    def find_dcim_cable(self, tenant_id: TenantId, cable_id: str) -> DcimCable | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                   b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                   length_m, label
            FROM dcim_cables
            WHERE tenant_id = %(tenant_id)s AND cable_id = %(cable_id)s
            """,
            {"tenant_id": tenant_id.value, "cable_id": Code.from_value(cable_id).value},
        )
        return self._dcim_cable_from_row(row) if row else None

    def find_active_dcim_cable_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimCable | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                   b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                   length_m, label
            FROM dcim_cables
            WHERE tenant_id = %(tenant_id)s AND status IN ('planned', 'installed')
              AND (
                (a_owner_type = %(owner_type)s AND a_owner_code = %(owner_code)s
                 AND a_port_name = %(port_name)s)
                OR (b_owner_type = %(owner_type)s AND b_owner_code = %(owner_code)s
                    AND b_port_name = %(port_name)s)
              )
            ORDER BY cable_id
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": endpoint.owner_type.value,
                "owner_code": endpoint.owner_code.value,
                "port_name": endpoint.port_name.value,
            },
        )
        return self._dcim_cable_from_row(row) if row else None

    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                   row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                   coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s AND asset_tag = %(asset_tag)s
            """,
            {
                "tenant_id": tenant_id.value,
                "asset_tag": Code.from_value(asset_tag, "asset tag").value,
            },
        )
        return self._equipment_from_row(row) if row else None

    def find_power_device(self, tenant_id: TenantId, code: str) -> PowerDevice | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, code, kind, site_code, building_code, room_code,
                   rack_code, side, capacity_watts, derating_percent, input_source,
                   output_voltage, label
            FROM dcim_power_devices
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "code": Code.from_value(code, "power device code").value,
            },
        )
        return self._power_device_from_row(row) if row else None

    def find_power_circuit(self, tenant_id: TenantId, circuit_id: str) -> PowerCircuit | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                   room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                   redundancy_group, label
            FROM dcim_power_circuits
            WHERE tenant_id = %(tenant_id)s AND circuit_id = %(circuit_id)s
            """,
            {
                "tenant_id": tenant_id.value,
                "circuit_id": Code.from_value(circuit_id, "power circuit id").value,
            },
        )
        return self._power_circuit_from_row(row) if row else None

    def find_cooling_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> CoolingZone | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, zone_code, role,
                   cooling_capacity_watts, supply_temperature_c, return_temperature_c, label
            FROM dcim_cooling_zones
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND zone_code = %(zone_code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "zone_code": Code.from_value(zone, "zone code").value,
            },
        )
        return self._cooling_zone_from_row(row) if row else None

    def list_equipment_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[Equipment, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                   row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                   coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY rack_face NULLS FIRST, u_position NULLS FIRST, asset_tag
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._equipment_from_row(row) for row in rows)

    def list_racks_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
    ) -> tuple[Rack, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   row_code, column_code, zone_code, units,
                   coordinate_x, coordinate_y, coordinate_z, usable_faces,
                   max_weight_kg, power_capacity_watts
            FROM racks
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
            ORDER BY row_code, column_code, code
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
            },
        )
        return tuple(self._rack_from_row(row) for row in rows)

    def list_patch_panels_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PatchPanel, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, rack_code, code,
                   rack_face, u_position, u_height, port_count, connector, medium, label
            FROM dcim_patch_panels
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY rack_face, u_position, code
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._patch_panel_from_row(row) for row in rows)

    def list_dcim_ports_by_owner(
        self,
        tenant_id: TenantId,
        owner_type: str,
        owner_code: str,
    ) -> tuple[DcimPort, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, owner_type, owner_code, port_name, site_code,
                   building_code, room_code, connector, medium, enabled
            FROM dcim_ports
            WHERE tenant_id = %(tenant_id)s AND owner_type = %(owner_type)s
              AND owner_code = %(owner_code)s
            ORDER BY port_name
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": DcimPortOwnerType.from_value(owner_type).value,
                "owner_code": Code.from_value(owner_code).value,
            },
        )
        return tuple(self._dcim_port_from_row(row) for row in rows)

    def list_dcim_cables_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> tuple[DcimCable, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                   b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                   length_m, label
            FROM dcim_cables
            WHERE tenant_id = %(tenant_id)s AND (
                (a_owner_type = %(owner_type)s AND a_owner_code = %(owner_code)s
                 AND a_port_name = %(port_name)s)
                OR (b_owner_type = %(owner_type)s AND b_owner_code = %(owner_code)s
                    AND b_port_name = %(port_name)s)
              )
            ORDER BY cable_id
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": endpoint.owner_type.value,
                "owner_code": endpoint.owner_code.value,
                "port_name": endpoint.port_name.value,
            },
        )
        return tuple(self._dcim_cable_from_row(row) for row in rows)

    def list_equipment_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
    ) -> tuple[Equipment, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                   row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                   coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
            ORDER BY row_code, column_code, rack_code NULLS FIRST, asset_tag
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
            },
        )
        return tuple(self._equipment_from_row(row) for row in rows)

    def list_power_circuits_by_source(
        self,
        tenant_id: TenantId,
        source_device: str,
    ) -> tuple[PowerCircuit, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                   room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                   redundancy_group, label
            FROM dcim_power_circuits
            WHERE tenant_id = %(tenant_id)s AND source_device_code = %(source_device_code)s
            ORDER BY circuit_id
            """,
            {
                "tenant_id": tenant_id.value,
                "source_device_code": Code.from_value(source_device, "power device code").value,
            },
        )
        return tuple(self._power_circuit_from_row(row) for row in rows)

    def list_power_circuits_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PowerCircuit, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                   room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                   redundancy_group, label
            FROM dcim_power_circuits
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY side, circuit_id
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._power_circuit_from_row(row) for row in rows)

    def list_power_reservations_for_circuit(
        self,
        tenant_id: TenantId,
        circuit_id: str,
    ) -> tuple[RackPowerReservation, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, circuit_id, side, site_code, building_code,
                   room_code, rack_code, expected_watts, label
            FROM dcim_power_reservations
            WHERE tenant_id = %(tenant_id)s AND circuit_id = %(circuit_id)s
            ORDER BY asset_tag, side
            """,
            {
                "tenant_id": tenant_id.value,
                "circuit_id": Code.from_value(circuit_id, "power circuit id").value,
            },
        )
        return tuple(self._power_reservation_from_row(row) for row in rows)

    def list_power_reservations_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[RackPowerReservation, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, circuit_id, side, site_code, building_code,
                   room_code, rack_code, expected_watts, label
            FROM dcim_power_reservations
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY side, asset_tag
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._power_reservation_from_row(row) for row in rows)

    def _site_from_row(self, row: Mapping[str, object]) -> Site:
        return Site(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            code=Code.from_value(str(row["code"]), "site code"),
            name=Name.from_value(str(row["name"]), "site name"),
            country=str(row["country"]),
            city=str(row["city"]),
            region=str(row.get("region") or ""),
        )

    def _building_from_row(self, row: Mapping[str, object]) -> Building:
        return Building(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            code=Code.from_value(str(row["code"]), "building code"),
            name=Name.from_value(str(row["name"]), "building name"),
        )

    def _floor_from_row(self, row: Mapping[str, object]) -> Floor:
        return Floor(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            code=Code.from_value(str(row["code"]), "floor code"),
            name=Name.from_value(str(row["name"]), "floor name"),
            level_index=self._row_int(row, "level_index"),
        )

    def _room_from_row(self, row: Mapping[str, object]) -> Room:
        coordinates = Coordinates3D.from_values(
            self._float_or_none(row.get("coordinate_x")),
            self._float_or_none(row.get("coordinate_y")),
            self._float_or_none(row.get("coordinate_z")),
        )
        zone_values = self._row_optional_sequence(row, "zone_codes", ())
        return Room(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            code=Code.from_value(str(row["code"]), "room code"),
            name=Name.from_value(str(row["name"]), "room name"),
            rows=tuple(str(value) for value in self._row_sequence(row, "rows")),
            columns=tuple(str(value) for value in self._row_sequence(row, "columns")),
            floor_code=(
                Code.from_value(str(row["floor_code"]), "floor code")
                if row.get("floor_code") is not None
                else None
            ),
            zone_codes=tuple(Code.from_value(str(value), "zone code") for value in zone_values),
            coordinates=coordinates,
        )

    def _zone_from_row(self, row: Mapping[str, object]) -> RoomZone:
        return RoomZone(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            floor_code=Code.from_value(str(row["floor_code"]), "floor code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            code=Code.from_value(str(row["code"]), "zone code"),
            name=Name.from_value(str(row["name"]), "zone name"),
            rows=tuple(str(value) for value in self._row_sequence(row, "rows")),
            columns=tuple(str(value) for value in self._row_sequence(row, "columns")),
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
            units=self._row_int(row, "units"),
            coordinates=coordinates,
            floor_code=(
                Code.from_value(str(row["floor_code"]), "floor code")
                if row.get("floor_code") is not None
                else None
            ),
            zone_code=(
                Code.from_value(str(row["zone_code"]), "zone code")
                if row.get("zone_code") is not None
                else None
            ),
            usable_faces=tuple(
                RackFace.from_value(str(face)) or RackFace.FRONT
                for face in self._row_optional_sequence(row, "usable_faces", ("front",))
            ),
            max_weight_kg=(
                self._float_or_none(row.get("max_weight_kg"))
                if row.get("max_weight_kg") is not None
                else None
            ),
            power_capacity_watts=(
                self._row_int(row, "power_capacity_watts")
                if row.get("power_capacity_watts") is not None
                else None
            ),
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
            u_position=self._row_int(row, "u_position") if row["u_position"] is not None else None,
            coordinates=coordinates,
            floor_code=str(row["floor_code"]) if row.get("floor_code") is not None else None,
            zone_code=str(row["zone_code"]) if row.get("zone_code") is not None else None,
            rack_face=str(row["rack_face"]) if row.get("rack_face") is not None else None,
            u_height=self._row_int(row, "u_height") if row.get("u_height") is not None else None,
        )
        return Equipment(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            asset_tag=Code.from_value(str(row["asset_tag"]), "asset tag"),
            name=Name.from_value(str(row["name"]), "equipment name"),
            location=location,
        )

    def _patch_panel_from_row(self, row: Mapping[str, object]) -> PatchPanel:
        rack_face = RackFace.from_value(str(row["rack_face"]))
        if rack_face is None:
            raise ValidationError("postgresql patch panel row has no rack face")
        return PatchPanel(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code"),
            code=Code.from_value(str(row["code"]), "patch panel code"),
            rack_face=rack_face,
            u_position=self._row_int(row, "u_position"),
            u_height=self._row_int(row, "u_height"),
            port_count=self._row_int(row, "port_count"),
            connector=DcimConnectorType.from_value(str(row["connector"])),
            medium=DcimCableMedium.from_value(str(row["medium"])),
            label=str(row.get("label") or ""),
        )

    def _dcim_port_from_row(self, row: Mapping[str, object]) -> DcimPort:
        return DcimPort(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            endpoint=DcimPortEndpoint.create(
                str(row["owner_type"]),
                str(row["owner_code"]),
                str(row["port_name"]),
            ),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            connector=DcimConnectorType.from_value(str(row["connector"])),
            medium=DcimCableMedium.from_value(str(row["medium"])),
            enabled=bool(row["enabled"]),
        )

    def _dcim_cable_from_row(self, row: Mapping[str, object]) -> DcimCable:
        return DcimCable(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            cable_id=Code.from_value(str(row["cable_id"]), "cable id"),
            a_endpoint=DcimPortEndpoint.create(
                str(row["a_owner_type"]),
                str(row["a_owner_code"]),
                str(row["a_port_name"]),
            ),
            b_endpoint=DcimPortEndpoint.create(
                str(row["b_owner_type"]),
                str(row["b_owner_code"]),
                str(row["b_port_name"]),
            ),
            medium=DcimCableMedium.from_value(str(row["medium"])),
            status=DcimCableStatus.from_value(str(row["status"])),
            path=self._dcim_cable_path_from_row(row),
            length_m=self._float_or_none(row.get("length_m")),
            label=str(row.get("label") or ""),
        )

    def _dcim_cable_path_from_row(
        self,
        row: Mapping[str, object],
    ) -> tuple[DcimCablePathSegment, ...]:
        raw_path = row.get("path_segments")
        decoded = json.loads(raw_path) if isinstance(raw_path, str) else raw_path
        path_items = cast(Sequence[Mapping[str, object]], decoded or ())
        return tuple(
            DcimCablePathSegment.create(
                order=self._row_int(item, "order"),
                kind=str(item.get("kind") or "path"),
                label=str(item["label"]),
            )
            for item in path_items
        )

    def _power_device_from_row(self, row: Mapping[str, object]) -> PowerDevice:
        return PowerDevice(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            code=Code.from_value(str(row["code"]), "power device code"),
            kind=PowerDeviceKind.from_value(str(row["kind"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code")
            if row.get("rack_code") is not None
            else None,
            side=PowerFeedSide.from_value(str(row["side"]))
            if row.get("side") is not None
            else None,
            capacity_watts=self._row_int(row, "capacity_watts"),
            derating_percent=self._row_int(row, "derating_percent"),
            input_source=str(row["input_source"]),
            output_voltage=self._row_int(row, "output_voltage"),
            label=str(row.get("label") or ""),
        )

    def _power_circuit_from_row(self, row: Mapping[str, object]) -> PowerCircuit:
        return PowerCircuit(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            circuit_id=Code.from_value(str(row["circuit_id"]), "power circuit id"),
            source_device_code=Code.from_value(str(row["source_device_code"]), "power device code"),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code"),
            side=PowerFeedSide.from_value(str(row["side"])),
            capacity_watts=self._row_int(row, "capacity_watts"),
            breaker_rating_amps=self._row_int(row, "breaker_rating_amps"),
            redundancy_group=str(row["redundancy_group"]),
            label=str(row.get("label") or ""),
        )

    def _cooling_zone_from_row(self, row: Mapping[str, object]) -> CoolingZone:
        return CoolingZone(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            zone_code=Code.from_value(str(row["zone_code"]), "zone code"),
            role=CoolingRole.from_value(str(row["role"])),
            cooling_capacity_watts=self._row_int(row, "cooling_capacity_watts"),
            supply_temperature_c=self._row_float(row, "supply_temperature_c"),
            return_temperature_c=self._row_float(row, "return_temperature_c"),
            label=str(row.get("label") or ""),
        )

    def _power_reservation_from_row(self, row: Mapping[str, object]) -> RackPowerReservation:
        return RackPowerReservation(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            asset_tag=Code.from_value(str(row["asset_tag"]), "asset tag"),
            circuit_id=Code.from_value(str(row["circuit_id"]), "power circuit id"),
            side=PowerFeedSide.from_value(str(row["side"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code"),
            expected_watts=self._row_int(row, "expected_watts"),
            label=str(row.get("label") or ""),
        )

    def _float_or_none(self, value: object) -> float | None:
        return None if value is None else float(str(value))


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

    def add_or_get_vrf(self, vrf: Vrf) -> Vrf:
        self._ensure_tenant(vrf.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO vrfs (id, tenant_id, name, route_distinguisher)
            VALUES (%(id)s, %(tenant_id)s, %(name)s, %(route_distinguisher)s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET route_distinguisher = COALESCE(
                vrfs.route_distinguisher,
                EXCLUDED.route_distinguisher
            )
            RETURNING id, tenant_id, name, route_distinguisher
            """,
            {
                "id": vrf.id.value,
                "tenant_id": vrf.tenant_id.value,
                "name": vrf.name.value,
                "route_distinguisher": vrf.route_distinguisher,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return vrf after upsert")
        return self._vrf_from_row(row)

    def list_vrfs(self, tenant_id: TenantId) -> tuple[Vrf, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, route_distinguisher
            FROM vrfs
            WHERE tenant_id = %(tenant_id)s
            ORDER BY name
            """,
            {"tenant_id": tenant_id.value},
        )
        return tuple(self._vrf_from_row(row) for row in rows)

    def add_aggregate(self, aggregate: IpAggregate) -> IpAggregate:
        self._ensure_tenant(aggregate.tenant_id)
        self.add_vrf(Vrf.create(aggregate.tenant_id, aggregate.vrf_name.value))
        row = self._fetch_one(
            """
            INSERT INTO ip_aggregates (id, tenant_id, vrf_name, cidr, family, description)
            VALUES (%(id)s, %(tenant_id)s, %(vrf_name)s, %(cidr)s, %(family)s, %(description)s)
            ON CONFLICT (tenant_id, vrf_name, cidr)
            DO UPDATE SET description = ip_aggregates.description
            RETURNING id, tenant_id, vrf_name, cidr, description
            """,
            {
                "id": aggregate.id.value,
                "tenant_id": aggregate.tenant_id.value,
                "vrf_name": aggregate.vrf_name.value,
                "cidr": str(aggregate.network),
                "family": aggregate.network.version,
                "description": aggregate.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return aggregate after upsert")
        return self._aggregate_from_row(row)

    def list_aggregates(self, tenant_id: TenantId, vrf_name: str) -> tuple[IpAggregate, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, cidr, description
            FROM ip_aggregates
            WHERE tenant_id = %(tenant_id)s AND vrf_name = %(vrf_name)s
            ORDER BY cidr
            """,
            {"tenant_id": tenant_id.value, "vrf_name": Name.from_value(vrf_name, "vrf name").value},
        )
        return tuple(self._aggregate_from_row(row) for row in rows)

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

    def list_prefixes(self, tenant_id: TenantId, vrf_name: str) -> tuple[Prefix, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, cidr, description
            FROM prefixes
            WHERE tenant_id = %(tenant_id)s AND vrf_name = %(vrf_name)s
            ORDER BY cidr
            """,
            {"tenant_id": tenant_id.value, "vrf_name": Name.from_value(vrf_name, "vrf name").value},
        )
        return tuple(self._prefix_from_row(row) for row in rows)

    def add_range(self, ip_range: IpRange) -> IpRange:
        row = self._fetch_one(
            """
            INSERT INTO ip_ranges (
                id, tenant_id, vrf_name, prefix_cidr, start_address, end_address,
                purpose, description
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(start_address)s,
                %(end_address)s, %(purpose)s, %(description)s
            )
            ON CONFLICT (tenant_id, vrf_name, prefix_cidr, start_address, end_address)
            DO UPDATE SET description = ip_ranges.description
            RETURNING id, tenant_id, vrf_name, prefix_cidr, start_address, end_address,
                purpose, description
            """,
            {
                "id": ip_range.id.value,
                "tenant_id": ip_range.tenant_id.value,
                "vrf_name": ip_range.vrf_name.value,
                "prefix_cidr": ip_range.prefix,
                "start_address": str(ip_range.start),
                "end_address": str(ip_range.end),
                "purpose": ip_range.purpose.value,
                "description": ip_range.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return range after upsert")
        return self._range_from_row(row)

    def list_ranges(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpRange, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, start_address, end_address,
                purpose, description
            FROM ip_ranges
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND prefix_cidr = %(prefix_cidr)s
            ORDER BY start_address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "prefix_cidr": prefix_cidr,
            },
        )
        return tuple(self._range_from_row(row) for row in rows)

    def upsert_address_record(self, record: IpAddressRecord) -> IpAddressRecord:
        row = self._fetch_one(
            """
            INSERT INTO ip_address_records (
                id, tenant_id, vrf_name, prefix_cidr, address, hostname, interface_name, status
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(address)s,
                %(hostname)s, %(interface_name)s, %(status)s
            )
            ON CONFLICT (tenant_id, vrf_name, address)
            DO UPDATE SET
                prefix_cidr = EXCLUDED.prefix_cidr,
                hostname = EXCLUDED.hostname,
                interface_name = EXCLUDED.interface_name,
                status = EXCLUDED.status
            RETURNING id, tenant_id, vrf_name, prefix_cidr, address, hostname,
                interface_name, status
            """,
            {
                "id": record.id.value,
                "tenant_id": record.tenant_id.value,
                "vrf_name": record.vrf_name.value,
                "prefix_cidr": record.prefix,
                "address": str(record.address),
                "hostname": record.hostname,
                "interface_name": record.interface_name.value if record.interface_name else None,
                "status": record.status.value,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return address record after upsert")
        return self._address_record_from_row(row)

    def list_address_records(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpAddressRecord, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, address, hostname, interface_name, status
            FROM ip_address_records
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
        return tuple(self._address_record_from_row(row) for row in rows)

    def acquire_allocation_lock(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> None:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value
        normalized_prefix = str(ipaddress.ip_network(prefix_cidr.strip(), strict=True))
        self._execute_without_result(
            """
            SELECT pg_advisory_xact_lock(
                hashtextextended(%(lock_scope)s, 0)
            )
            """,
            {"lock_scope": f"ipam:{tenant_id.value}:{normalized_vrf}:{normalized_prefix}"},
        )

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

    def add_vlan_group(self, group: VlanGroup) -> VlanGroup:
        self._ensure_tenant(group.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_vlan_groups (id, tenant_id, name, scope, description)
            VALUES (%(id)s, %(tenant_id)s, %(name)s, %(scope)s, %(description)s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET description = ipam_vlan_groups.description
            RETURNING id, tenant_id, name, scope, description
            """,
            {
                "id": group.id.value,
                "tenant_id": group.tenant_id.value,
                "name": group.name.value,
                "scope": group.scope.value if group.scope else None,
                "description": group.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return VLAN group after upsert")
        return self._vlan_group_from_row(row)

    def list_vlan_groups(self, tenant_id: TenantId) -> tuple[VlanGroup, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, scope, description
            FROM ipam_vlan_groups
            WHERE tenant_id = %(tenant_id)s
            ORDER BY name
            """,
            {"tenant_id": tenant_id.value},
        )
        return tuple(self._vlan_group_from_row(row) for row in rows)

    def add_vlan(self, vlan: Vlan) -> Vlan:
        self._ensure_tenant(vlan.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_vlans (
                id, tenant_id, group_name, vlan_id, name, vrf_name, vni, description
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(group_name)s, %(vlan_id)s,
                %(name)s, %(vrf_name)s, %(vni)s, %(description)s
            )
            ON CONFLICT (tenant_id, group_name, vlan_id)
            DO UPDATE SET description = ipam_vlans.description
            RETURNING id, tenant_id, group_name, vlan_id, name, vrf_name, vni, description
            """,
            {
                "id": vlan.id.value,
                "tenant_id": vlan.tenant_id.value,
                "group_name": vlan.group_name.value,
                "vlan_id": vlan.vlan_id,
                "name": vlan.name.value,
                "vrf_name": vlan.vrf_name.value if vlan.vrf_name else None,
                "vni": vlan.vni,
                "description": vlan.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return VLAN after upsert")
        return self._vlan_from_row(row)

    def list_vlans(self, tenant_id: TenantId, vrf_name: str | None = None) -> tuple[Vlan, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, group_name, vlan_id, name, vrf_name, vni, description
            FROM ipam_vlans
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY group_name, vlan_id
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._vlan_from_row(row) for row in rows)

    def add_vxlan_vni(self, vni: VxlanVni) -> VxlanVni:
        self._ensure_tenant(vni.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_vxlan_vnis (
                id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vni)s, %(name)s, %(vrf_name)s,
                %(route_targets_import)s, %(route_targets_export)s, %(description)s
            )
            ON CONFLICT (tenant_id, vni)
            DO UPDATE SET description = ipam_vxlan_vnis.description
            RETURNING id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            """,
            {
                "id": vni.id.value,
                "tenant_id": vni.tenant_id.value,
                "vni": vni.vni,
                "name": vni.name.value,
                "vrf_name": vni.vrf_name.value,
                "route_targets_import": list(vni.route_targets_import),
                "route_targets_export": list(vni.route_targets_export),
                "description": vni.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return VXLAN VNI after upsert")
        return self._vxlan_vni_from_row(row)

    def find_vxlan_vni(self, tenant_id: TenantId, vni: int) -> VxlanVni | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            FROM ipam_vxlan_vnis
            WHERE tenant_id = %(tenant_id)s AND vni = %(vni)s
            """,
            {"tenant_id": tenant_id.value, "vni": vni},
        )
        return self._vxlan_vni_from_row(row) if row else None

    def list_vxlan_vnis(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[VxlanVni, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            FROM ipam_vxlan_vnis
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY vni
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._vxlan_vni_from_row(row) for row in rows)

    def add_asn(self, asn: AutonomousSystem) -> AutonomousSystem:
        self._ensure_tenant(asn.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_autonomous_systems (id, tenant_id, asn, name, description)
            VALUES (%(id)s, %(tenant_id)s, %(asn)s, %(name)s, %(description)s)
            ON CONFLICT (tenant_id, asn)
            DO UPDATE SET description = ipam_autonomous_systems.description
            RETURNING id, tenant_id, asn, name, description
            """,
            {
                "id": asn.id.value,
                "tenant_id": asn.tenant_id.value,
                "asn": asn.number,
                "name": asn.name.value,
                "description": asn.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return ASN after upsert")
        return self._asn_from_row(row)

    def find_asn(self, tenant_id: TenantId, number: int) -> AutonomousSystem | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, asn, name, description
            FROM ipam_autonomous_systems
            WHERE tenant_id = %(tenant_id)s AND asn = %(asn)s
            """,
            {"tenant_id": tenant_id.value, "asn": number},
        )
        return self._asn_from_row(row) if row else None

    def list_asns(self, tenant_id: TenantId) -> tuple[AutonomousSystem, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asn, name, description
            FROM ipam_autonomous_systems
            WHERE tenant_id = %(tenant_id)s
            ORDER BY asn
            """,
            {"tenant_id": tenant_id.value},
        )
        return tuple(self._asn_from_row(row) for row in rows)

    def add_bgp_peer(self, peer: BgpPeer) -> BgpPeer:
        self._ensure_tenant(peer.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_bgp_peers (
                id, tenant_id, vrf_name, local_asn, remote_asn, peer_address,
                address_family, route_targets_import, route_targets_export, description
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(local_asn)s, %(remote_asn)s,
                %(peer_address)s, %(address_family)s, %(route_targets_import)s,
                %(route_targets_export)s, %(description)s
            )
            ON CONFLICT (tenant_id, vrf_name, local_asn, peer_address)
            DO UPDATE SET description = ipam_bgp_peers.description
            RETURNING id, tenant_id, vrf_name, local_asn, remote_asn, peer_address,
                address_family, route_targets_import, route_targets_export, description
            """,
            {
                "id": peer.id.value,
                "tenant_id": peer.tenant_id.value,
                "vrf_name": peer.vrf_name.value,
                "local_asn": peer.local_asn,
                "remote_asn": peer.remote_asn,
                "peer_address": str(peer.peer_address),
                "address_family": peer.address_family.value,
                "route_targets_import": list(peer.route_targets_import),
                "route_targets_export": list(peer.route_targets_export),
                "description": peer.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return BGP peer after upsert")
        return self._bgp_peer_from_row(row)

    def list_bgp_peers(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[BgpPeer, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, local_asn, remote_asn, peer_address,
                address_family, route_targets_import, route_targets_export, description
            FROM ipam_bgp_peers
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY vrf_name, local_asn, peer_address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._bgp_peer_from_row(row) for row in rows)

    def _vlan_group_from_row(self, row: Mapping[str, object]) -> VlanGroup:
        return VlanGroup(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=Name.from_value(str(row["name"]), "vlan group name"),
            scope=(
                None
                if row.get("scope") is None
                else Code.from_value(str(row["scope"]), "vlan group scope")
            ),
            description=str(row.get("description") or ""),
        )

    def _vlan_from_row(self, row: Mapping[str, object]) -> Vlan:
        return Vlan(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            group_name=Name.from_value(str(row["group_name"]), "vlan group name"),
            vlan_id=int(str(row["vlan_id"])),
            name=Name.from_value(str(row["name"]), "vlan name"),
            vrf_name=(
                None
                if row.get("vrf_name") is None
                else Name.from_value(str(row["vrf_name"]), "vrf name")
            ),
            vni=None if row.get("vni") is None else int(str(row["vni"])),
            description=str(row.get("description") or ""),
        )

    def _vxlan_vni_from_row(self, row: Mapping[str, object]) -> VxlanVni:
        return VxlanVni(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vni=int(str(row["vni"])),
            name=Name.from_value(str(row["name"]), "vni name"),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            route_targets_import=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_import"])
            ),
            route_targets_export=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_export"])
            ),
            description=str(row.get("description") or ""),
        )

    def _asn_from_row(self, row: Mapping[str, object]) -> AutonomousSystem:
        return AutonomousSystem(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            number=int(str(row["asn"])),
            name=Name.from_value(str(row["name"]), "asn name"),
            description=str(row.get("description") or ""),
        )

    def _bgp_peer_from_row(self, row: Mapping[str, object]) -> BgpPeer:
        return BgpPeer(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            local_asn=int(str(row["local_asn"])),
            remote_asn=int(str(row["remote_asn"])),
            peer_address=ipaddress.ip_address(str(row["peer_address"])),
            address_family=BgpAddressFamily.from_value(str(row["address_family"])),
            route_targets_import=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_import"])
            ),
            route_targets_export=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_export"])
            ),
            description=str(row.get("description") or ""),
        )

    def _vrf_from_row(self, row: Mapping[str, object]) -> Vrf:
        return Vrf(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=Name.from_value(str(row["name"]), "vrf name"),
            route_distinguisher=(
                None if row.get("route_distinguisher") is None else str(row["route_distinguisher"])
            ),
        )

    def _aggregate_from_row(self, row: Mapping[str, object]) -> IpAggregate:
        return IpAggregate(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            network=ipaddress.ip_network(str(row["cidr"]), strict=True),
            description=str(row["description"] or ""),
        )

    def _prefix_from_row(self, row: Mapping[str, object]) -> Prefix:
        return Prefix(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            network=ipaddress.ip_network(str(row["cidr"]), strict=True),
            description=str(row["description"] or ""),
        )

    def _range_from_row(self, row: Mapping[str, object]) -> IpRange:
        prefix = Prefix.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
        )
        ip_range = IpRange.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            prefix,
            str(row["start_address"]),
            str(row["end_address"]),
            str(row["purpose"]),
            str(row["description"] or ""),
        )
        return IpRange(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=ip_range.tenant_id,
            vrf_name=ip_range.vrf_name,
            prefix=ip_range.prefix,
            start=ip_range.start,
            end=ip_range.end,
            purpose=ip_range.purpose,
            description=ip_range.description,
        )

    def _address_record_from_row(self, row: Mapping[str, object]) -> IpAddressRecord:
        prefix = Prefix.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
        )
        record = IpAddressRecord.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            prefix,
            str(row["address"]),
            str(row["hostname"]),
            None if row.get("interface_name") is None else str(row["interface_name"]),
            str(row["status"]),
        )
        return IpAddressRecord(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=record.tenant_id,
            vrf_name=record.vrf_name,
            prefix=record.prefix,
            address=record.address,
            hostname=record.hostname,
            interface_name=record.interface_name,
            status=record.status,
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
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, subject, token_hash, token_prefix, roles, active, created_at,
                   expires_at, revoked_at, revoked_by, last_used_at, use_count
            FROM api_tokens
            WHERE tenant_id = %(tenant_id)s
              AND (
                %(include_inactive)s
                OR (
                    active = true
                    AND revoked_at IS NULL
                    AND (expires_at IS NULL OR expires_at > now())
                )
              )
            ORDER BY created_at ASC, id ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "include_inactive": include_inactive,
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
            use_count=self._row_int_or_default(row, "use_count", 0),
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
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                   environments, active, created_at
            FROM access_policy_rules
            WHERE tenant_id = %(tenant_id)s
              AND (%(include_inactive)s OR active = true)
            ORDER BY name ASC, id ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "include_inactive": include_inactive,
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
            environments=tuple(str(item) for item in cast(Sequence[object], row["environments"])),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLSourceGovernanceRepository(PostgreSQLRepositoryBase, SourceGovernanceRepository):
    def upsert_rule(self, rule: SourceGovernanceRule) -> None:
        self._ensure_tenant(rule.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO source_governance_rules (
                id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                priority, freshness_seconds, conflict_strategy, active, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(object_kind)s, %(attribute_path)s,
                %(authoritative_source)s, %(priority)s, %(freshness_seconds)s,
                %(conflict_strategy)s, %(active)s, %(created_at)s
            )
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                object_kind = EXCLUDED.object_kind,
                attribute_path = EXCLUDED.attribute_path,
                authoritative_source = EXCLUDED.authoritative_source,
                priority = EXCLUDED.priority,
                freshness_seconds = EXCLUDED.freshness_seconds,
                conflict_strategy = EXCLUDED.conflict_strategy,
                active = EXCLUDED.active
            """,
            self._rule_params(rule),
        )

    def find_rule(self, tenant_id: TenantId, name: str) -> SourceGovernanceRule | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                   priority, freshness_seconds, conflict_strategy, active, created_at
            FROM source_governance_rules
            WHERE tenant_id = %(tenant_id)s AND name = %(name)s
            """,
            {"tenant_id": tenant_id.value, "name": name.strip().lower()},
        )
        return self._rule_from_row(row) if row else None

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool = False,
        object_kind: str | None = None,
    ) -> SourceGovernanceRulePage:
        offset = self._offset(pagination.cursor)
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                   priority, freshness_seconds, conflict_strategy, active, created_at
            FROM source_governance_rules
            WHERE tenant_id = %(tenant_id)s
              AND (%(include_inactive)s OR active IS TRUE)
              AND (
                %(object_kind)s IS NULL
                OR object_kind IS NULL
                OR object_kind = %(object_kind)s
              )
            ORDER BY priority DESC, name ASC, id ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "include_inactive": include_inactive,
                "object_kind": object_kind.strip().lower() if object_kind is not None else None,
                "limit": pagination.limit + 1,
                "offset": offset,
            },
        )
        selected = tuple(rows[: pagination.limit])
        next_cursor = str(offset + pagination.limit) if len(rows) > pagination.limit else None
        return SourceGovernanceRulePage(
            tuple(self._rule_from_row(row) for row in selected),
            next_cursor,
        )

    def find_active_rules_for_kind(
        self,
        tenant_id: TenantId,
        object_kind: str,
    ) -> tuple[SourceGovernanceRule, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                   priority, freshness_seconds, conflict_strategy, active, created_at
            FROM source_governance_rules
            WHERE tenant_id = %(tenant_id)s
              AND active IS TRUE
              AND (object_kind IS NULL OR object_kind = %(object_kind)s)
            ORDER BY priority DESC, name ASC, id ASC
            """,
            {"tenant_id": tenant_id.value, "object_kind": object_kind.strip().lower()},
        )
        return tuple(self._rule_from_row(row) for row in rows)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        cursor = self._execute_without_result(
            """
            UPDATE source_governance_rules
            SET active = FALSE
            WHERE tenant_id = %(tenant_id)s AND name = %(name)s AND active IS TRUE
            """,
            {"tenant_id": tenant_id.value, "name": name.strip().lower()},
        )
        rowcount = getattr(cursor, "rowcount", None)
        return True if rowcount is None else int(rowcount) > 0

    def _rule_params(self, rule: SourceGovernanceRule) -> dict[str, object]:
        return {
            "id": rule.id.value,
            "tenant_id": rule.tenant_id.value,
            "name": rule.name.value,
            "object_kind": rule.object_kind.value if rule.object_kind else None,
            "attribute_path": rule.attribute_path.value,
            "authoritative_source": rule.authoritative_source.value,
            "priority": rule.priority,
            "freshness_seconds": rule.freshness_seconds,
            "conflict_strategy": rule.conflict_strategy.value,
            "active": rule.active,
            "created_at": rule.created_at,
        }

    def _offset(self, cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    def _rule_from_row(self, row: Mapping[str, object]) -> SourceGovernanceRule:
        return SourceGovernanceRule.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=str(row["name"]),
            object_kind=(str(row["object_kind"]) if row.get("object_kind") else None),
            attribute_path=str(row["attribute_path"]),
            authoritative_source=str(row["authoritative_source"]),
            priority=self._row_int(row, "priority"),
            freshness_seconds=(
                self._row_int(row, "freshness_seconds")
                if row.get("freshness_seconds") is not None
                else None
            ),
            conflict_strategy=str(row["conflict_strategy"]),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLSourceOfTruthRepository(PostgreSQLRepositoryBase, SourceOfTruthRepository):
    def create_object(
        self,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, object],
        tags: tuple[str, ...],
        source: str,
        actor: str,
    ) -> SourceOfTruthObject:
        source_object = SourceOfTruthObject.create(
            tenant_id=tenant_id,
            key=key,
            kind=kind,
            display_name=display_name,
            attributes=attributes,
            tags=tags,
            source=source,
        )
        self.upsert_object(source_object, actor)
        return source_object

    def upsert_object(self, source_object: SourceOfTruthObject, actor: str) -> None:
        self._ensure_tenant(source_object.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO source_objects (
                id, tenant_id, object_key, kind, display_name, attributes, tags, source_system,
                version, status, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(object_key)s, %(kind)s, %(display_name)s,
                %(attributes)s, %(tags)s, %(source_system)s, %(version)s, %(status)s,
                %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, object_key) DO UPDATE SET
                kind = EXCLUDED.kind,
                display_name = EXCLUDED.display_name,
                attributes = EXCLUDED.attributes,
                tags = EXCLUDED.tags,
                source_system = EXCLUDED.source_system,
                version = EXCLUDED.version,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """,
            self._object_params(source_object),
        )
        snapshot = SourceObjectSnapshot.create(source_object, actor)
        self._execute_without_result(
            """
            INSERT INTO source_object_snapshots (
                id, tenant_id, object_key, object_id, version, payload, changed_by, changed_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(object_key)s, %(object_id)s, %(version)s,
                %(payload)s, %(changed_by)s, %(changed_at)s
            )
            ON CONFLICT (tenant_id, object_key, version) DO NOTHING
            """,
            {
                "id": snapshot.id.value,
                "tenant_id": snapshot.tenant_id.value,
                "object_key": snapshot.object_key.value,
                "object_id": snapshot.object_id.value,
                "version": snapshot.version,
                "payload": json.dumps(snapshot.payload, sort_keys=True),
                "changed_by": snapshot.changed_by,
                "changed_at": snapshot.changed_at,
            },
        )

    def find_object(self, tenant_id: TenantId, key: str) -> SourceOfTruthObject | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, kind, display_name, attributes, tags, source_system,
                   version, status, created_at, updated_at
            FROM source_objects
            WHERE tenant_id = %(tenant_id)s AND object_key = %(object_key)s
            """,
            {"tenant_id": tenant_id.value, "object_key": key.strip().lower()},
        )
        return self._object_from_row(row) if row else None

    def list_objects(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        tag: str | None = None,
    ) -> SourceObjectPage:
        offset = self._offset(pagination.cursor)
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, object_key, kind, display_name, attributes, tags, source_system,
                   version, status, created_at, updated_at
            FROM source_objects
            WHERE tenant_id = %(tenant_id)s
              AND (%(kind)s IS NULL OR kind = %(kind)s)
              AND (%(tag)s IS NULL OR tags @> %(tag)s)
            ORDER BY object_key ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "kind": kind.strip().lower() if kind is not None else None,
                "tag": [tag.strip().lower()] if tag is not None else None,
                "limit": pagination.limit + 1,
                "offset": offset,
            },
        )
        selected = tuple(rows[: pagination.limit])
        next_cursor = str(offset + pagination.limit) if len(rows) > pagination.limit else None
        return SourceObjectPage(tuple(self._object_from_row(row) for row in selected), next_cursor)

    def find_object_version(
        self,
        tenant_id: TenantId,
        key: str,
        version: int,
    ) -> SourceObjectSnapshot | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, object_id, version,
                   payload, changed_by, changed_at
            FROM source_object_snapshots
            WHERE tenant_id = %(tenant_id)s
              AND object_key = %(object_key)s
              AND version = %(version)s
            """,
            {
                "tenant_id": tenant_id.value,
                "object_key": key.strip().lower(),
                "version": int(version),
            },
        )
        return self._snapshot_from_row(row) if row else None

    def add_relation(self, relation: SourceRelation) -> None:
        self._ensure_tenant(relation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO source_relations (
                id, tenant_id, relation_type, source_key, target_key, provenance,
                valid_from, valid_to, active, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(relation_type)s, %(source_key)s, %(target_key)s,
                %(provenance)s, %(valid_from)s, %(valid_to)s, %(active)s, %(created_at)s
            )
            """,
            {
                "id": relation.id.value,
                "tenant_id": relation.tenant_id.value,
                "relation_type": relation.relation_type.value,
                "source_key": relation.source_key.value,
                "target_key": relation.target_key.value,
                "provenance": relation.provenance.value,
                "valid_from": relation.valid_from,
                "valid_to": relation.valid_to,
                "active": relation.active,
                "created_at": relation.created_at,
            },
        )

    def list_relations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_key: str | None = None,
        target_key: str | None = None,
        relation_type: str | None = None,
    ) -> SourceRelationPage:
        offset = self._offset(pagination.cursor)
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, relation_type, source_key, target_key, provenance,
                   valid_from, valid_to, active, created_at
            FROM source_relations
            WHERE tenant_id = %(tenant_id)s
              AND (%(source_key)s IS NULL OR source_key = %(source_key)s)
              AND (%(target_key)s IS NULL OR target_key = %(target_key)s)
              AND (%(relation_type)s IS NULL OR relation_type = %(relation_type)s)
            ORDER BY created_at DESC, id DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": tenant_id.value,
                "source_key": source_key.strip().lower() if source_key is not None else None,
                "target_key": target_key.strip().lower() if target_key is not None else None,
                "relation_type": relation_type.strip().lower()
                if relation_type is not None
                else None,
                "limit": pagination.limit + 1,
                "offset": offset,
            },
        )
        selected = tuple(rows[: pagination.limit])
        next_cursor = str(offset + pagination.limit) if len(rows) > pagination.limit else None
        return SourceRelationPage(
            tuple(self._relation_from_row(row) for row in selected), next_cursor
        )

    def _object_params(self, source_object: SourceOfTruthObject) -> dict[str, object]:
        return {
            "id": source_object.id.value,
            "tenant_id": source_object.tenant_id.value,
            "object_key": source_object.key.value,
            "kind": source_object.kind.value,
            "display_name": source_object.display_name,
            "attributes": json.dumps(source_object.attributes, sort_keys=True),
            "tags": [tag.value for tag in source_object.tags],
            "source_system": source_object.source.value,
            "version": source_object.version,
            "status": source_object.status.value,
            "created_at": source_object.created_at,
            "updated_at": source_object.updated_at,
        }

    def _offset(self, cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    def _object_from_row(self, row: Mapping[str, object]) -> SourceOfTruthObject:
        attributes = row["attributes"]
        return SourceOfTruthObject.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            key=str(row["object_key"]),
            kind=str(row["kind"]),
            display_name=str(row["display_name"]),
            attributes=(
                json.loads(str(attributes))
                if isinstance(attributes, str)
                else dict(cast(Mapping[str, Any], attributes))
            ),
            tags=tuple(str(item) for item in self._row_sequence(row, "tags")),
            source=str(row["source_system"]),
            version=self._row_int(row, "version"),
            status=str(row["status"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _snapshot_from_row(self, row: Mapping[str, object]) -> SourceObjectSnapshot:
        payload = row["payload"]
        return SourceObjectSnapshot.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            object_key=str(row["object_key"]),
            object_id=EntityId.from_value(str(row["object_id"])),
            version=self._row_int(row, "version"),
            payload=(
                json.loads(str(payload))
                if isinstance(payload, str)
                else dict(cast(Mapping[str, Any], payload))
            ),
            changed_by=str(row["changed_by"]),
            changed_at=self._row_datetime(row["changed_at"]),
        )

    def _relation_from_row(self, row: Mapping[str, object]) -> SourceRelation:
        return SourceRelation.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            relation_type=str(row["relation_type"]),
            source_key=str(row["source_key"]),
            target_key=str(row["target_key"]),
            provenance=str(row["provenance"]),
            valid_from=self._row_datetime(row["valid_from"]),
            valid_to=(self._row_datetime(row["valid_to"]) if row.get("valid_to") else None),
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
        previous_hash = self._latest_hash(event.tenant_id)
        record = AuditEventRecord.create(event, previous_hash)
        self._execute_without_result(
            """
            INSERT INTO audit_events (
                id, tenant_id, actor, action, target_type, target_id, severity, metadata,
                created_at, previous_hash, record_hash
            ) VALUES (
                %(id)s, %(tenant_id)s, %(actor)s, %(action)s, %(target_type)s, %(target_id)s,
                %(severity)s, %(metadata)s, %(created_at)s, %(previous_hash)s, %(record_hash)s
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
                "previous_hash": record.previous_hash,
                "record_hash": record.record_hash,
            },
        )

    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        try:
            offset = int(event_filter.pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, actor, action, target_type, target_id, severity,
                   metadata, created_at, previous_hash, record_hash
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
              AND (%(actor)s IS NULL OR actor = %(actor)s)
              AND (%(action)s IS NULL OR action = %(action)s)
              AND (%(target_type)s IS NULL OR target_type = %(target_type)s)
              AND (%(severity)s IS NULL OR severity = %(severity)s)
              AND (%(created_from)s IS NULL OR created_at >= %(created_from)s)
              AND (%(created_to)s IS NULL OR created_at <= %(created_to)s)
            ORDER BY created_at DESC, id DESC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {
                "tenant_id": event_filter.tenant_id.value,
                "actor": event_filter.actor,
                "action": event_filter.action,
                "target_type": event_filter.target_type,
                "severity": event_filter.severity.value
                if event_filter.severity is not None
                else None,
                "created_from": event_filter.created_from,
                "created_to": event_filter.created_to,
                "limit": event_filter.pagination.limit + 1,
                "offset": offset,
            },
        )
        records = tuple(self._record_from_row(row) for row in rows[: event_filter.pagination.limit])
        next_cursor = (
            str(offset + event_filter.pagination.limit)
            if len(rows) > event_filter.pagination.limit
            else None
        )
        return AuditEventPage(records, next_cursor)

    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        if not 1 <= int(limit) <= 10_000:
            raise ValidationError("audit integrity limit must be between 1 and 10000")
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, actor, action, target_type, target_id, severity,
                   metadata, created_at, previous_hash, record_hash
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at ASC, id ASC
            LIMIT %(limit)s
            """,
            {"tenant_id": tenant_id.value, "limit": int(limit)},
        )
        previous_hash = AuditIntegrityHasher.GENESIS_HASH
        checked = 0
        for row in rows:
            record = self._record_from_row(row)
            if record.previous_hash != previous_hash or not record.verifies():
                return AuditIntegrityReport(
                    tenant_id=tenant_id,
                    checked=checked + 1,
                    valid=False,
                    broken_record_id=record.event.id.value,
                    head_hash=previous_hash,
                )
            previous_hash = record.record_hash
            checked += 1
        return AuditIntegrityReport(
            tenant_id=tenant_id,
            checked=checked,
            valid=True,
            broken_record_id=None,
            head_hash=previous_hash,
        )

    def list_events(self, tenant_id: TenantId, limit: int = 100) -> tuple[AuditEvent, ...]:
        if not 1 <= limit <= 500:
            raise ValidationError("audit list limit must be between 1 and 500")
        event_filter = AuditEventFilter.create(
            tenant_id,
            Pagination.from_values(limit),
        )
        return tuple(record.event for record in self.list_records(event_filter).items)

    def _latest_hash(self, tenant_id: TenantId) -> str:
        row = self._fetch_one(
            """
            SELECT record_hash
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            {"tenant_id": tenant_id.value},
        )
        if row is None or row.get("record_hash") is None:
            return AuditIntegrityHasher.GENESIS_HASH
        return AuditIntegrityHasher.normalize_hash(str(row["record_hash"]), "record_hash")

    def _record_from_row(self, row: Mapping[str, object]) -> AuditEventRecord:
        event = self._event_from_row(row)
        previous_hash = str(row.get("previous_hash") or AuditIntegrityHasher.GENESIS_HASH)
        record_hash = row.get("record_hash")
        if record_hash is None:
            return AuditEventRecord.create(event, previous_hash)
        return AuditEventRecord.restore(event, previous_hash, str(record_hash))

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
            created_at=(
                created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=UTC)
            ),
            metadata=(
                json.loads(str(metadata))
                if isinstance(metadata, str)
                else dict(cast(Mapping[str, Any], metadata))
            ),
        )
