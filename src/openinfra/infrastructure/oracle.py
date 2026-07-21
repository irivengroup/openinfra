from __future__ import annotations

import hashlib
import importlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Self, cast

from openinfra.application.ports import (
    ReadinessProbe,
    ReadinessStatus,
    SchemaStatusProvider,
    TransactionManager,
    UnitOfWork,
)
from openinfra.domain.common import ConflictError, OpenInfraError, ValidationError
from openinfra.infrastructure.json_store import JsonDocumentStore, _JsonState


@dataclass(frozen=True, slots=True)
class OracleConnectionSettings:
    dsn: str
    user: str
    password: str
    pool_min: int = 1
    pool_max: int = 10
    pool_increment: int = 1
    timeout_seconds: int = 30

    @classmethod
    def create(
        cls,
        *,
        dsn: str,
        user: str,
        password: str,
        pool_min: int = 1,
        pool_max: int = 10,
        pool_increment: int = 1,
        timeout_seconds: int = 30,
    ) -> Self:
        normalized_dsn = dsn.strip()
        normalized_user = user.strip()
        if not normalized_dsn or not normalized_user or not password:
            raise ValidationError("Oracle dsn, user and password are required")
        minimum = int(pool_min)
        maximum = int(pool_max)
        increment = int(pool_increment)
        timeout = int(timeout_seconds)
        if not 1 <= minimum <= maximum <= 256:
            raise ValidationError("Oracle pool bounds must satisfy 1 <= min <= max <= 256")
        if not 1 <= increment <= maximum:
            raise ValidationError("Oracle pool_increment must be between 1 and pool_max")
        if not 1 <= timeout <= 300:
            raise ValidationError("Oracle timeout_seconds must be between 1 and 300")
        return cls(
            dsn=normalized_dsn,
            user=normalized_user,
            password=password,
            pool_min=minimum,
            pool_max=maximum,
            pool_increment=increment,
            timeout_seconds=timeout,
        )


class OracleDriver:
    @staticmethod
    def load() -> Any:
        try:
            return importlib.import_module("oracledb")
        except ModuleNotFoundError as exc:
            raise OpenInfraError(
                "python-oracledb is required for the Oracle database backend; "
                "install openinfra[oracle]"
            ) from exc


class OracleDocumentStore(JsonDocumentStore):
    _STATE_KEY = "global"
    _SHARD_TABLE = "OPENINFRA_DOCUMENT_SHARDS"

    def __init__(self, settings: OracleConnectionSettings) -> None:
        self._settings = settings
        self._driver = OracleDriver.load()
        self._lock = threading.RLock()
        self._state = _JsonState(data=self._empty_state(), dirty=False)
        self._version = 0
        self._shard_versions: dict[str, int] = {}
        self._sharded = False
        self._pool = self._driver.create_pool(
            user=settings.user,
            password=settings.password,
            dsn=settings.dsn,
            min=settings.pool_min,
            max=settings.pool_max,
            increment=settings.pool_increment,
            timeout=settings.timeout_seconds,
            getmode=getattr(self._driver, "POOL_GETMODE_WAIT", None),
        )
        self.reload()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def data(self) -> dict[str, Any]:
        return self._state.data

    @property
    def pool(self) -> Any:
        return self._pool

    @property
    def sharded(self) -> bool:
        return self._sharded

    def mark_dirty(self) -> None:
        self._state.dirty = True

    def flush(self) -> None:
        raise OpenInfraError("Oracle state must be committed through an active UnitOfWork")

    def reload(self, connection: Any | None = None, *, for_update: bool = False) -> None:
        owned = connection is None
        conn = self._pool.acquire() if owned else connection
        if conn is None:
            raise OpenInfraError("Oracle connection is unavailable")
        try:
            cursor = conn.cursor()
            self._sharded = self._shard_table_exists(cursor)
            if self._sharded:
                loaded, versions = self._load_shards(cursor)
                legacy_row = self._load_legacy(cursor, required=not loaded, for_update=False)
                legacy = {} if legacy_row is None else legacy_row[0]
                merged = self._merge_with_empty(legacy)
                for key, value in loaded.items():
                    if key in merged or key == "export_signing_secret":
                        merged[key] = value
                missing = tuple(key for key in merged if key not in loaded)
                if missing:
                    self._bootstrap_shards(cursor, merged, missing)
                    versions.update(dict.fromkeys(missing, 0))
                    if owned:
                        conn.commit()
                self._state = _JsonState(data=merged, dirty=False)
                self._shard_versions = versions
                return

            legacy_row = self._load_legacy(
                cursor,
                required=True,
                for_update=for_update,
            )
            if legacy_row is None:
                raise OpenInfraError("Oracle OpenInfra schema is not initialized")
            loaded, version = legacy_row
            self._state = _JsonState(data=self._merge_with_empty(loaded), dirty=False)
            self._version = version
            self._shard_versions = {}
        finally:
            if owned:
                self._pool.release(conn)

    def _shard_table_exists(self, cursor: Any) -> bool:
        cursor.execute(
            "SELECT COUNT(*) FROM user_tables WHERE table_name = :table_name",
            table_name=self._SHARD_TABLE,
        )
        row = cursor.fetchone()
        return row is not None and int(row[0]) == 1

    @staticmethod
    def _read_payload(value: object) -> object:
        raw = value.read() if hasattr(value, "read") else str(value)
        return json.loads(raw)

    def _load_legacy(
        self,
        cursor: Any,
        *,
        required: bool,
        for_update: bool,
    ) -> tuple[dict[str, Any], int] | None:
        statement = (
            "SELECT payload, version FROM openinfra_document_state "
            "WHERE state_key = :state_key FOR UPDATE"
            if for_update
            else "SELECT payload, version FROM openinfra_document_state "
            "WHERE state_key = :state_key"
        )
        cursor.execute(statement, state_key=self._STATE_KEY)
        row = cursor.fetchone()
        if row is None:
            if required:
                raise OpenInfraError("Oracle OpenInfra schema is not initialized")
            return None
        loaded = self._read_payload(row[0])
        if not isinstance(loaded, dict):
            raise OpenInfraError("Oracle OpenInfra state payload is invalid")
        return cast(dict[str, Any], loaded), int(row[1])

    def _load_shards(self, cursor: Any) -> tuple[dict[str, Any], dict[str, int]]:
        cursor.execute(
            "SELECT shard_key, payload, version FROM openinfra_document_shards ORDER BY shard_key"
        )
        loaded: dict[str, Any] = {}
        versions: dict[str, int] = {}
        for row in cursor.fetchall():
            key = str(row[0])
            payload = self._read_payload(row[1])
            if payload is not None and not isinstance(payload, (dict, list, str)):
                raise OpenInfraError("Oracle OpenInfra shard payload is invalid: " + key)
            loaded[key] = payload
            versions[key] = int(row[2])
        return loaded, versions

    @staticmethod
    def _bootstrap_shards(
        cursor: Any,
        state: dict[str, Any],
        keys: tuple[str, ...],
    ) -> None:
        statement = """
            MERGE INTO openinfra_document_shards target
            USING (SELECT :shard_key AS shard_key, :payload AS payload FROM dual) source
            ON (target.shard_key = source.shard_key)
            WHEN NOT MATCHED THEN INSERT (shard_key, payload, version)
            VALUES (source.shard_key, source.payload, 0)
        """
        for key in keys:
            cursor.execute(
                statement,
                shard_key=key,
                payload=json.dumps(state[key], sort_keys=True, separators=(",", ":")),
            )

    def flush_with_connection(
        self,
        connection: Any,
        baseline: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        if not self._state.dirty:
            return {}
        if not self._sharded:
            payload = json.dumps(self._state.data, sort_keys=True, separators=(",", ":"))
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE openinfra_document_state
                SET payload = :payload, version = version + 1, updated_at = SYSTIMESTAMP
                WHERE state_key = :state_key AND version = :expected_version
                """,
                payload=payload,
                state_key=self._STATE_KEY,
                expected_version=self._version,
            )
            if int(cursor.rowcount or 0) != 1:
                raise ConflictError(
                    "Oracle OpenInfra state changed concurrently; retry the transaction"
                )
            return {self._STATE_KEY: self._version + 1}

        previous = baseline or self._empty_state()
        changed = tuple(
            sorted(
                key
                for key in set(previous) | set(self._state.data)
                if previous.get(key) != self._state.data.get(key)
            )
        )
        if not changed:
            return {}
        cursor = connection.cursor()
        next_versions: dict[str, int] = {}
        for key in changed:
            expected_version = self._shard_versions.get(key, 0)
            payload = json.dumps(self._state.data.get(key), sort_keys=True, separators=(",", ":"))
            cursor.execute(
                """
                UPDATE openinfra_document_shards
                SET payload = :payload, version = version + 1, updated_at = SYSTIMESTAMP
                WHERE shard_key = :shard_key AND version = :expected_version
                """,
                payload=payload,
                shard_key=key,
                expected_version=expected_version,
            )
            if int(cursor.rowcount or 0) != 1:
                raise ConflictError("Oracle OpenInfra shard changed concurrently: " + key)
            next_versions[key] = expected_version + 1
        return next_versions

    def accept_flush(self, next_versions: dict[str, int]) -> None:
        if not self._sharded:
            if self._STATE_KEY in next_versions:
                self._version = next_versions[self._STATE_KEY]
        else:
            self._shard_versions.update(next_versions)
        self._state.dirty = False

    def snapshot(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(json.dumps(self._state.data)))

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._state = _JsonState(data=snapshot, dirty=False)

    def close(self) -> None:
        self._pool.close(force=True)


class OracleUnitOfWork(UnitOfWork):
    def __init__(self, store: OracleDocumentStore) -> None:
        self._store = store
        self._connection: Any | None = None
        self._snapshot: dict[str, Any] | None = None
        self._committed = False

    def __enter__(self) -> OracleUnitOfWork:
        self._store.lock.acquire()
        try:
            self._connection = self._store.pool.acquire()
            self._store.reload(self._connection, for_update=True)
            self._snapshot = self._store.snapshot()
            return self
        except Exception:
            if self._connection is not None:
                self._store.pool.release(self._connection)
                self._connection = None
            self._store.lock.release()
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc, traceback
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            if self._connection is not None:
                self._store.pool.release(self._connection)
                self._connection = None
            self._store.lock.release()

    def commit(self) -> None:
        connection = self._connection
        if connection is None:
            raise OpenInfraError("Oracle commit requires an active UnitOfWork")
        self._store.mark_dirty()
        next_versions = self._store.flush_with_connection(connection, self._snapshot)
        connection.commit()
        self._store.accept_flush(next_versions)
        self._committed = True

    def rollback(self) -> None:
        if self._connection is not None:
            self._connection.rollback()
        if self._snapshot is not None:
            self._store.restore(self._snapshot)
        self._committed = True


class OracleTransactionManager(TransactionManager):
    def __init__(self, store: OracleDocumentStore) -> None:
        self._store = store

    def begin(self) -> OracleUnitOfWork:
        return OracleUnitOfWork(self._store)


@dataclass(frozen=True, slots=True)
class OracleMigration:
    version: str
    path: Path
    oracle_checksum: str
    source_checksum: str = ""


class OracleMigrationCatalog:
    _MANIFEST_SCHEMA = "openinfra.oracle-migration-catalog/v1"

    def __init__(self, root: Path, source_root: Path | None = None) -> None:
        self.root = root
        self.source_root = source_root

    @classmethod
    def from_project_root(cls) -> OracleMigrationCatalog:
        source = Path("installers/migrations/oracle")
        postgresql = Path("installers/migrations/postgresql")
        if source.is_dir():
            return cls(source, postgresql if postgresql.is_dir() else None)
        package_root = Path(__file__).resolve().parents[1]
        packaged = package_root / "migrations" / "oracle"
        packaged_postgresql = package_root / "migrations" / "postgresql"
        return cls(packaged, packaged_postgresql if packaged_postgresql.is_dir() else None)

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _paths(root: Path) -> tuple[Path, ...]:
        return tuple(sorted(root.glob("[0-9][0-9][0-9][0-9]_*.sql")))

    @staticmethod
    def _validate_continuity(paths: tuple[Path, ...], backend: str) -> None:
        versions = [path.name.split("_", 1)[0] for path in paths]
        expected = [f"{index:04d}" for index in range(1, len(paths) + 1)]
        if versions != expected:
            raise OpenInfraError(
                f"{backend} migration versions must be contiguous from 0001: "
                f"expected {expected}, got {versions}"
            )

    def _manifest_entries(self) -> dict[str, dict[str, object]] | None:
        manifest_path = self.root / "manifest.json"
        if not manifest_path.is_file():
            return None
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OpenInfraError("Oracle migration manifest is invalid") from exc
        if not isinstance(payload, dict) or payload.get("schema") != self._MANIFEST_SCHEMA:
            raise OpenInfraError("Oracle migration manifest schema is invalid")
        migrations = payload.get("migrations")
        if not isinstance(migrations, list) or payload.get("count") != len(migrations):
            raise OpenInfraError("Oracle migration manifest count is invalid")
        entries: dict[str, dict[str, object]] = {}
        for raw in migrations:
            if not isinstance(raw, dict) or not isinstance(raw.get("filename"), str):
                raise OpenInfraError("Oracle migration manifest entry is invalid")
            filename = str(raw["filename"])
            if filename in entries:
                raise OpenInfraError("Oracle migration manifest contains duplicate filenames")
            entries[filename] = raw
        return entries

    def migrations(self) -> tuple[OracleMigration, ...]:
        if not self.root.is_dir():
            raise OpenInfraError("Oracle migration directory is missing: " + str(self.root))
        paths = self._paths(self.root)
        if not paths:
            raise OpenInfraError("Oracle migration catalog is empty")
        self._validate_continuity(paths, "Oracle")

        source_by_name: dict[str, Path] = {}
        if self.source_root is not None:
            if not self.source_root.is_dir():
                raise OpenInfraError(
                    "PostgreSQL migration directory is missing: " + str(self.source_root)
                )
            source_paths = self._paths(self.source_root)
            self._validate_continuity(source_paths, "PostgreSQL")
            if [path.name for path in paths] != [path.name for path in source_paths]:
                raise OpenInfraError("Oracle and PostgreSQL migration filenames diverge")
            source_by_name = {path.name: path for path in source_paths}

        manifest = self._manifest_entries()
        if manifest is not None and set(manifest) != {path.name for path in paths}:
            raise OpenInfraError("Oracle migration manifest filenames diverge from the catalog")

        values: list[OracleMigration] = []
        for path in paths:
            oracle_checksum = self._sha256(path)
            source_path = source_by_name.get(path.name)
            source_checksum = self._sha256(source_path) if source_path is not None else ""
            if manifest is not None:
                entry = manifest[path.name]
                if entry.get("version") != path.name.split("_", 1)[0]:
                    raise OpenInfraError("Oracle migration manifest version mismatch: " + path.name)
                manifest_oracle_checksum = entry.get("oracle_sha256")
                manifest_source_checksum = entry.get("source_sha256")
                if (
                    not isinstance(manifest_oracle_checksum, str)
                    or re.fullmatch(r"[0-9a-f]{64}", manifest_oracle_checksum) is None
                    or manifest_oracle_checksum != oracle_checksum
                ):
                    raise OpenInfraError("Oracle migration checksum drift detected: " + path.name)
                if (
                    not isinstance(manifest_source_checksum, str)
                    or re.fullmatch(r"[0-9a-f]{64}", manifest_source_checksum) is None
                ):
                    raise OpenInfraError(
                        "PostgreSQL source migration checksum is invalid: " + path.name
                    )
                if source_path is not None and manifest_source_checksum != source_checksum:
                    raise OpenInfraError(
                        "PostgreSQL source migration checksum drift detected: " + path.name
                    )
                source_checksum = manifest_source_checksum
            values.append(
                OracleMigration(
                    version=path.name.split("_", 1)[0],
                    path=path,
                    oracle_checksum=oracle_checksum,
                    source_checksum=source_checksum,
                )
            )
        return tuple(values)


class OracleMigrationExecutor(SchemaStatusProvider):
    _APPLIED = "applied"
    _APPLYING = "applying"
    _FAILED = "failed"
    _HISTORY_COLUMNS: ClassVar[dict[str, str]] = {
        "ORACLE_CHECKSUM": "VARCHAR2(64 CHAR)",
        "SOURCE_CHECKSUM": "VARCHAR2(64 CHAR)",
        "STATUS": "VARCHAR2(16 CHAR) DEFAULT 'applied' NOT NULL",
        "STARTED_AT": "TIMESTAMP WITH TIME ZONE",
        "ERROR_MESSAGE": "VARCHAR2(4000 CHAR)",
    }

    def __init__(self, settings: OracleConnectionSettings, catalog: OracleMigrationCatalog) -> None:
        self._settings = settings
        self._catalog = catalog
        self._driver = OracleDriver.load()

    def _connect(self) -> Any:
        return self._driver.connect(
            user=self._settings.user,
            password=self._settings.password,
            dsn=self._settings.dsn,
        )

    def apply_all(self) -> dict[str, object]:
        migrations = self._catalog.migrations()
        connection = self._connect()
        applied: list[str] = []
        try:
            cursor = connection.cursor()
            self._ensure_history(cursor)
            connection.commit()
            existing = self._history(cursor)
            for migration in migrations:
                row = existing.get(migration.version)
                recovery = row is not None and (
                    row[4] in {self._APPLYING, self._FAILED}
                    or (migration.version == "0001" and row[0] == "0001_document_state.sql")
                )
                if row is not None and row[4] == self._APPLIED and not recovery:
                    self._verify_applied(migration, row)
                    if not row[1] or (migration.source_checksum and not row[2]):
                        self._mark_applied(cursor, migration)
                        connection.commit()
                    continue
                self._mark_applying(cursor, migration)
                connection.commit()
                try:
                    self._execute_migration(cursor, migration, recovery=recovery)
                    self._mark_applied(cursor, migration)
                    connection.commit()
                    applied.append(migration.path.name)
                except Exception as exc:
                    connection.rollback()
                    self._mark_failed(cursor, migration, exc)
                    connection.commit()
                    raise
            status = self._status(cursor, migrations)
            return {"backend": "oracle", "newly_applied": applied, **status}
        finally:
            connection.close()

    def status_as_dict(self) -> dict[str, object]:
        migrations = self._catalog.migrations()
        connection = self._connect()
        try:
            cursor = connection.cursor()
            self._ensure_history(cursor)
            return {"backend": "oracle", **self._status(cursor, migrations)}
        finally:
            connection.close()

    def _status(self, cursor: Any, migrations: tuple[OracleMigration, ...]) -> dict[str, object]:
        existing = self._history(cursor)
        expected_versions = {migration.version for migration in migrations}
        applied: list[dict[str, object]] = []
        drift: list[str] = []
        for migration in migrations:
            row = existing.get(migration.version)
            if row is None:
                continue
            filename, oracle_checksum, source_checksum, applied_at, status = row
            entry = {
                "version": migration.version,
                "filename": filename,
                "status": status,
                "applied_at": applied_at,
            }
            applied.append(entry)
            if filename != migration.path.name:
                drift.append(migration.version + ":filename")
            if oracle_checksum != migration.oracle_checksum:
                drift.append(migration.version + ":oracle-checksum")
            if migration.source_checksum and source_checksum != migration.source_checksum:
                drift.append(migration.version + ":source-checksum")
            if status != self._APPLIED:
                drift.append(migration.version + ":" + status)
        unexpected = sorted(set(existing) - expected_versions)
        drift.extend(version + ":unexpected" for version in unexpected)
        current = len(applied) == len(migrations) and not drift
        return {
            "expected_count": len(migrations),
            "applied_count": sum(1 for entry in applied if entry["status"] == self._APPLIED),
            "current": current,
            "drift": drift,
            "applied": applied,
        }

    @staticmethod
    def _history(cursor: Any) -> dict[str, tuple[str, str, str, object, str]]:
        cursor.execute(
            "SELECT version, filename, oracle_checksum, source_checksum, applied_at, status "
            "FROM openinfra_schema_migrations ORDER BY version"
        )
        return {
            str(row[0]): (
                str(row[1]),
                "" if row[2] is None else str(row[2]),
                "" if row[3] is None else str(row[3]),
                row[4],
                OracleMigrationExecutor._APPLIED if row[5] is None else str(row[5]),
            )
            for row in cursor.fetchall()
        }

    @staticmethod
    def _verify_applied(migration: OracleMigration, row: tuple[str, str, str, object, str]) -> None:
        filename, oracle_checksum, source_checksum, _applied_at, status = row
        if status != OracleMigrationExecutor._APPLIED:
            raise OpenInfraError(
                f"Oracle migration {migration.version} has invalid status {status}"
            )
        if filename != migration.path.name:
            raise OpenInfraError(
                f"Oracle migration filename drift detected for {migration.version}: {filename}"
            )
        if oracle_checksum and oracle_checksum != migration.oracle_checksum:
            raise OpenInfraError(
                f"Oracle migration checksum drift detected for {migration.path.name}"
            )
        if (
            migration.source_checksum
            and source_checksum
            and source_checksum != migration.source_checksum
        ):
            raise OpenInfraError(
                f"PostgreSQL source checksum drift detected for {migration.path.name}"
            )

    def _execute_migration(
        self, cursor: Any, migration: OracleMigration, *, recovery: bool
    ) -> None:
        payload = migration.path.read_text(encoding="utf-8")
        for statement in self._split_statements(payload):
            try:
                cursor.execute(statement)
            except Exception as exc:
                if recovery and self._is_recoverable_ddl_error(statement, exc):
                    continue
                raise

    @staticmethod
    def _oracle_error_code(exc: Exception) -> int | None:
        if exc.args:
            candidate = exc.args[0]
            code = getattr(candidate, "code", None)
            if isinstance(code, int):
                return abs(code)
        match = re.search(r"ORA-(\d{5})", str(exc))
        return int(match.group(1)) if match is not None else None

    @classmethod
    def _is_recoverable_ddl_error(cls, statement: str, exc: Exception) -> bool:
        code = cls._oracle_error_code(exc)
        upper = statement.lstrip().upper()
        return bool(
            (
                code == 955
                and upper.startswith(
                    (
                        "CREATE TABLE",
                        "CREATE GLOBAL TEMPORARY TABLE",
                        "CREATE INDEX",
                        "CREATE UNIQUE INDEX",
                    )
                )
            )
            or (code == 1430 and upper.startswith("ALTER TABLE") and " ADD " in upper)
            or (
                code in {2264, 2275}
                and upper.startswith("ALTER TABLE")
                and "ADD CONSTRAINT" in upper
            )
            or (code == 2443 and upper.startswith("ALTER TABLE") and "DROP CONSTRAINT" in upper)
            or (code == 942 and upper.startswith("DROP TABLE"))
        )

    @staticmethod
    def _mark_applying(cursor: Any, migration: OracleMigration) -> None:
        cursor.execute(
            """
            MERGE INTO openinfra_schema_migrations target
            USING (SELECT :version AS version FROM dual) source
            ON (target.version = source.version)
            WHEN MATCHED THEN UPDATE SET
                filename = :filename,
                oracle_checksum = :oracle_checksum,
                source_checksum = :source_checksum,
                status = 'applying',
                started_at = SYSTIMESTAMP,
                applied_at = NULL,
                error_message = NULL
            WHEN NOT MATCHED THEN INSERT (
                version, filename, oracle_checksum, source_checksum, status, started_at
            ) VALUES (
                :version, :filename, :oracle_checksum, :source_checksum, 'applying', SYSTIMESTAMP
            )
            """,
            version=migration.version,
            filename=migration.path.name,
            oracle_checksum=migration.oracle_checksum,
            source_checksum=migration.source_checksum or None,
        )

    @staticmethod
    def _mark_applied(cursor: Any, migration: OracleMigration) -> None:
        cursor.execute(
            """
            UPDATE openinfra_schema_migrations
            SET filename = :filename,
                oracle_checksum = :oracle_checksum,
                source_checksum = :source_checksum,
                status = 'applied',
                applied_at = SYSTIMESTAMP,
                error_message = NULL
            WHERE version = :version
            """,
            version=migration.version,
            filename=migration.path.name,
            oracle_checksum=migration.oracle_checksum,
            source_checksum=migration.source_checksum or None,
        )

    @staticmethod
    def _mark_failed(cursor: Any, migration: OracleMigration, exc: Exception) -> None:
        message = (type(exc).__name__ + ": " + str(exc))[:4000]
        cursor.execute(
            """
            UPDATE openinfra_schema_migrations
            SET filename = :filename,
                oracle_checksum = :oracle_checksum,
                source_checksum = :source_checksum,
                status = 'failed',
                error_message = :error_message
            WHERE version = :version
            """,
            version=migration.version,
            filename=migration.path.name,
            oracle_checksum=migration.oracle_checksum,
            source_checksum=migration.source_checksum or None,
            error_message=message,
        )

    @classmethod
    def _ensure_history(cls, cursor: Any) -> None:
        cursor.execute(
            "SELECT COUNT(*) FROM user_tables WHERE table_name = 'OPENINFRA_SCHEMA_MIGRATIONS'"
        )
        if int(cursor.fetchone()[0]) == 0:
            cursor.execute(
                """
                CREATE TABLE openinfra_schema_migrations (
                    version VARCHAR2(32 CHAR) PRIMARY KEY,
                    filename VARCHAR2(255 CHAR) NOT NULL,
                    oracle_checksum VARCHAR2(64 CHAR),
                    source_checksum VARCHAR2(64 CHAR),
                    status VARCHAR2(16 CHAR) DEFAULT 'applied' NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
                    error_message VARCHAR2(4000 CHAR),
                    CONSTRAINT ck_openinfra_schema_migrations_status
                        CHECK (status IN ('applying', 'applied', 'failed'))
                )
                """
            )
            return
        cursor.execute(
            "SELECT column_name FROM user_tab_columns "
            "WHERE table_name = 'OPENINFRA_SCHEMA_MIGRATIONS'"
        )
        existing = {str(row[0]).upper() for row in cursor.fetchall()}
        for column, data_type in cls._HISTORY_COLUMNS.items():
            if column not in existing:
                cursor.execute(
                    f"ALTER TABLE openinfra_schema_migrations ADD ({column.lower()} {data_type})"
                )

    @staticmethod
    def _split_statements(payload: str) -> tuple[str, ...]:
        statements: list[str] = []
        buffer: list[str] = []
        in_block = False
        single_quote = False
        double_quote = False

        def emit() -> None:
            statement = "".join(buffer).strip()
            buffer.clear()
            if statement:
                statements.append(statement)

        for raw_line in payload.splitlines(keepends=True):
            stripped = raw_line.strip()
            has_content = bool("".join(buffer).strip())
            if not has_content and (not stripped or stripped.startswith("--")):
                buffer.clear()
                continue
            if in_block and stripped == "/":
                emit()
                in_block = False
                single_quote = False
                double_quote = False
                continue
            if not has_content and re.match(r"^(?:DECLARE|BEGIN)\b", stripped, re.I):
                buffer.clear()
                in_block = True
            index = 0
            while index < len(raw_line):
                char = raw_line[index]
                nxt = raw_line[index + 1] if index + 1 < len(raw_line) else ""
                if single_quote:
                    buffer.append(char)
                    if char == "'" and nxt == "'":
                        buffer.append(nxt)
                        index += 2
                        continue
                    if char == "'":
                        single_quote = False
                    index += 1
                    continue
                if double_quote:
                    buffer.append(char)
                    if char == '"' and nxt == '"':
                        buffer.append(nxt)
                        index += 2
                        continue
                    if char == '"':
                        double_quote = False
                    index += 1
                    continue
                if char == "'":
                    single_quote = True
                    buffer.append(char)
                elif char == '"':
                    double_quote = True
                    buffer.append(char)
                elif char == ";" and not in_block:
                    emit()
                elif buffer or not char.isspace():
                    buffer.append(char)
                index += 1
        emit()
        return tuple(statements)


class OracleReadinessProbe(ReadinessProbe):
    def __init__(self, store: OracleDocumentStore, catalog: OracleMigrationCatalog) -> None:
        self._store = store
        self._catalog = catalog

    def check(self) -> ReadinessStatus:
        try:
            migrations = self._catalog.migrations()
            with self._store.pool.acquire() as connection:
                cursor = connection.cursor()
                requires_shards = any(migration.version == "0058" for migration in migrations)
                if requires_shards:
                    cursor.execute("SELECT COUNT(*) FROM openinfra_document_shards")
                    state_row = cursor.fetchone()
                    state_ready = state_row is not None and int(state_row[0]) > 0
                else:
                    cursor.execute(
                        "SELECT version FROM openinfra_document_state WHERE state_key = 'global'"
                    )
                    state_row = cursor.fetchone()
                    state_ready = state_row is not None
                cursor.execute(
                    "SELECT version, filename, oracle_checksum, source_checksum, status "
                    "FROM openinfra_schema_migrations ORDER BY version"
                )
                rows = cursor.fetchall()
            expected = {migration.version: migration for migration in migrations}
            ready = state_ready and len(rows) == len(expected)
            for row in rows:
                version = str(row[0])
                migration = expected.get(version)
                if migration is None:
                    ready = False
                    continue
                ready = ready and str(row[1]) == migration.path.name
                ready = ready and str(row[4]) == OracleMigrationExecutor._APPLIED
                ready = ready and row[2] is not None
                if row[2] is not None:
                    ready = ready and str(row[2]) == migration.oracle_checksum
                if migration.source_checksum:
                    ready = ready and row[3] is not None
                    if row[3] is not None:
                        ready = ready and str(row[3]) == migration.source_checksum
            detail = (
                f"Oracle document state and {len(migrations)} migrations are current"
                if ready
                else "Oracle schema or migration catalog is incomplete"
            )
            return ReadinessStatus("oracle", ready, detail)
        except Exception as exc:
            return ReadinessStatus(
                "oracle", False, "Oracle readiness failed: " + type(exc).__name__
            )
