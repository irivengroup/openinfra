from __future__ import annotations

import importlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self, cast

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
                "python-oracledb is required for the Oracle backend; install openinfra[oracle]"
            ) from exc


class OracleDocumentStore(JsonDocumentStore):
    _STATE_KEY = "global"

    def __init__(self, settings: OracleConnectionSettings) -> None:
        self._settings = settings
        self._driver = OracleDriver.load()
        self._lock = threading.RLock()
        self._state = _JsonState(data=self._empty_state(), dirty=False)
        self._version = 0
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
            statement = (
                "SELECT payload, version FROM openinfra_document_state "
                "WHERE state_key = :state_key FOR UPDATE"
                if for_update
                else "SELECT payload, version FROM openinfra_document_state "
                "WHERE state_key = :state_key"
            )
            cursor.execute(statement, state_key=self._STATE_KEY)  # nosec B608 - fixed statements
            row = cursor.fetchone()
            if row is None:
                raise OpenInfraError("Oracle OpenInfra schema is not initialized")
            raw_payload = row[0].read() if hasattr(row[0], "read") else str(row[0])
            loaded = json.loads(raw_payload)
            if not isinstance(loaded, dict):
                raise OpenInfraError("Oracle OpenInfra state payload is invalid")
            self._state = _JsonState(data=self._merge_with_empty(loaded), dirty=False)
            self._version = int(row[1])
        finally:
            if owned:
                self._pool.release(conn)

    def flush_with_connection(self, connection: Any) -> None:
        if not self._state.dirty:
            return
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
        self._version += 1
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
        self._store.flush_with_connection(connection)
        connection.commit()
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


class OracleMigrationCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def from_project_root(cls) -> OracleMigrationCatalog:
        source = Path("installers/migrations/oracle")
        if source.is_dir():
            return cls(source)
        packaged = Path(__file__).resolve().parents[1] / "migrations" / "oracle"
        return cls(packaged)

    def migrations(self) -> tuple[OracleMigration, ...]:
        if not self.root.is_dir():
            raise OpenInfraError("Oracle migration directory is missing: " + str(self.root))
        values = tuple(
            OracleMigration(path.stem.split("_", 1)[0], path)
            for path in sorted(self.root.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        )
        if not values:
            raise OpenInfraError("Oracle migration catalog is empty")
        return values


class OracleMigrationExecutor(SchemaStatusProvider):
    def __init__(self, settings: OracleConnectionSettings, catalog: OracleMigrationCatalog) -> None:
        self._settings = settings
        self._catalog = catalog
        self._driver = OracleDriver.load()

    def apply_all(self) -> dict[str, object]:
        connection = self._driver.connect(
            user=self._settings.user,
            password=self._settings.password,
            dsn=self._settings.dsn,
        )
        applied: list[str] = []
        try:
            cursor = connection.cursor()
            self._ensure_history(cursor)
            cursor.execute("SELECT version FROM openinfra_schema_migrations")
            existing = {str(row[0]) for row in cursor.fetchall()}
            for migration in self._catalog.migrations():
                if migration.version in existing:
                    continue
                for statement in self._split_statements(migration.path.read_text(encoding="utf-8")):
                    cursor.execute(statement)
                cursor.execute(
                    "INSERT INTO openinfra_schema_migrations (version, filename) VALUES (:1, :2)",
                    [migration.version, migration.path.name],
                )
                connection.commit()
                applied.append(migration.path.name)
            return {"backend": "oracle", "applied": applied, **self.status_as_dict()}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def status_as_dict(self) -> dict[str, object]:
        connection = self._driver.connect(
            user=self._settings.user,
            password=self._settings.password,
            dsn=self._settings.dsn,
        )
        try:
            cursor = connection.cursor()
            self._ensure_history(cursor)
            cursor.execute(
                "SELECT version, filename FROM openinfra_schema_migrations ORDER BY version"
            )
            applied = [
                {"version": str(row[0]), "filename": str(row[1])} for row in cursor.fetchall()
            ]
            expected = [migration.path.name for migration in self._catalog.migrations()]
            return {
                "backend": "oracle",
                "expected_count": len(expected),
                "applied_count": len(applied),
                "current": len(applied) == len(expected),
                "applied": applied,
            }
        finally:
            connection.close()

    def _ensure_history(self, cursor: Any) -> None:
        cursor.execute(
            "SELECT COUNT(*) FROM user_tables WHERE table_name = 'OPENINFRA_SCHEMA_MIGRATIONS'"
        )
        if int(cursor.fetchone()[0]) == 0:
            cursor.execute(
                """
                CREATE TABLE openinfra_schema_migrations (
                    version VARCHAR2(32) PRIMARY KEY,
                    filename VARCHAR2(255) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
                )
                """
            )

    @staticmethod
    def _split_statements(payload: str) -> tuple[str, ...]:
        statements: list[str] = []
        buffer: list[str] = []
        in_block = False
        for raw_line in payload.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            upper = stripped.upper()
            if upper.startswith("BEGIN") or upper.startswith("DECLARE"):
                in_block = True
            if in_block and stripped == "/":
                statements.append("\n".join(buffer).strip())
                buffer = []
                in_block = False
                continue
            buffer.append(line)
            if not in_block and stripped.endswith(";"):
                statements.append("\n".join(buffer).strip()[:-1])
                buffer = []
        if buffer:
            statements.append("\n".join(buffer).strip().rstrip(";"))
        return tuple(statement for statement in statements if statement)


class OracleReadinessProbe(ReadinessProbe):
    def __init__(self, store: OracleDocumentStore, catalog: OracleMigrationCatalog) -> None:
        self._store = store
        self._catalog = catalog

    def check(self) -> ReadinessStatus:
        try:
            with self._store.pool.acquire() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT version FROM openinfra_document_state WHERE state_key = 'global'"
                )
                row = cursor.fetchone()
            ready = row is not None
            detail = (
                "Oracle document state is available" if ready else "Oracle state row is missing"
            )
            return ReadinessStatus("oracle", ready, detail)
        except Exception as exc:
            return ReadinessStatus(
                "oracle", False, "Oracle readiness failed: " + type(exc).__name__
            )
