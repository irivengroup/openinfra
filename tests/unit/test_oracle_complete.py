from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.domain.common import ConflictError, OpenInfraError, ValidationError
from openinfra.infrastructure.oracle import (
    OracleConnectionSettings,
    OracleDocumentStore,
    OracleDriver,
    OracleMigrationCatalog,
    OracleMigrationExecutor,
    OracleReadinessProbe,
    OracleTransactionManager,
    OracleUnitOfWork,
)


class _Lob:
    def __init__(self, value: str) -> None:
        self.value = value

    def read(self) -> str:
        return self.value


class _Cursor:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.rowcount = 1
        self._last = ""
        self.executed: list[tuple[str, object]] = []

    def execute(self, statement: str, parameters: object = None, **kwargs: object) -> None:
        self._last = " ".join(statement.split())
        self.executed.append((self._last, parameters or kwargs))
        if self.connection.raise_on and self.connection.raise_on in self._last:
            raise RuntimeError("oracle failure")
        if self._last.startswith("UPDATE openinfra_document_state"):
            self.rowcount = self.connection.update_rowcount
            if self.rowcount == 1:
                values = parameters if isinstance(parameters, dict) else kwargs
                self.connection.state_row = _Lob(str(values["payload"]))
                self.connection.version += 1
        if self._last.startswith("INSERT INTO openinfra_schema_migrations"):
            values = parameters if isinstance(parameters, list) else []
            self.connection.migrations.append((str(values[0]), str(values[1])))

    def fetchone(self) -> tuple[object, ...] | None:
        if "COUNT(*) FROM user_tables" in self._last:
            return (1 if self.connection.history_exists else 0,)
        if "openinfra_document_state" in self._last:
            if self.connection.state_row is None:
                return None
            return (self.connection.state_row, self.connection.version)
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        if self._last == "SELECT version FROM openinfra_schema_migrations":
            return [(version,) for version, _ in self.connection.migrations]
        if "SELECT version, filename" in self._last:
            return list(self.connection.migrations)
        return []


class _Connection:
    def __init__(self, payload: object = None) -> None:
        if payload is None:
            payload = {}
        self.state_row: object | None = _Lob(json.dumps(payload))
        self.version = 1
        self.update_rowcount = 1
        self.history_exists = True
        self.migrations: list[tuple[str, str]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.raise_on = ""
        self.cursors: list[_Cursor] = []

    def cursor(self) -> _Cursor:
        cursor = _Cursor(self)
        self.cursors.append(cursor)
        return cursor

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.released: list[_Connection] = []
        self.closed = False
        self.raise_on_acquire = False

    def acquire(self) -> _Connection:
        if self.raise_on_acquire:
            raise RuntimeError("pool unavailable")
        return self.connection

    def release(self, connection: _Connection) -> None:
        self.released.append(connection)

    def close(self, *, force: bool) -> None:
        assert force is True
        self.closed = True


class _Driver:
    POOL_GETMODE_WAIT = "WAIT"

    def __init__(self, connections: list[_Connection] | None = None) -> None:
        self.connections = connections or [_Connection()]
        self.pool = _Pool(self.connections[0])
        self.pool_kwargs: dict[str, object] = {}
        self.connect_calls = 0

    def create_pool(self, **kwargs: object) -> _Pool:
        self.pool_kwargs = kwargs
        return self.pool

    def connect(self, **kwargs: object) -> _Connection:
        del kwargs
        index = min(self.connect_calls, len(self.connections) - 1)
        self.connect_calls += 1
        return self.connections[index]


def _settings() -> OracleConnectionSettings:
    return OracleConnectionSettings.create(
        dsn="db.example.test:1521/OPENINFRA",
        user="openinfra",
        password="secret",  # noqa: S106
        pool_min=1,
        pool_max=4,
        pool_increment=2,
        timeout_seconds=15,
    )


class TestOracleComplete:
    def test_settings_and_driver_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _settings().pool_increment == 2
        for kwargs, message in (
            ({"dsn": "", "user": "u", "password": "x"}, "required"),
            (
                {"dsn": "d", "user": "u", "password": "x", "pool_increment": 11},
                "pool_increment",
            ),
            (
                {"dsn": "d", "user": "u", "password": "x", "timeout_seconds": 301},
                "timeout_seconds",
            ),
        ):
            with pytest.raises(ValidationError, match=message):
                OracleConnectionSettings.create(**kwargs)  # type: ignore[arg-type]
        monkeypatch.setattr(
            "openinfra.infrastructure.oracle.importlib.import_module",
            lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
        )
        with pytest.raises(OpenInfraError, match=r"openinfra\[oracle\]"):
            OracleDriver.load()

    def test_document_store_transactions_and_conflict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connection = _Connection({"identity_users": []})
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())
        assert store.data["identity_users"] == []
        assert driver.pool_kwargs["getmode"] == "WAIT"
        with pytest.raises(OpenInfraError, match="active UnitOfWork"):
            store.flush()

        manager = OracleTransactionManager(store)
        with manager.begin() as uow:
            store.data["identity_users"].append({"username": "alice"})
            uow.commit()
        assert connection.commits == 1
        assert store.snapshot()["identity_users"][0]["username"] == "alice"

        before = store.snapshot()
        with manager.begin():
            store.data["identity_users"].append({"username": "bob"})
        assert store.snapshot() == before
        assert connection.rollbacks >= 1

        connection.update_rowcount = 0
        with manager.begin() as uow:
            store.data["identity_users"].append({"username": "charlie"})
            with pytest.raises(ConflictError, match="changed concurrently"):
                uow.commit()
        connection.update_rowcount = 1

        detached = OracleUnitOfWork(store)
        with pytest.raises(OpenInfraError, match="active UnitOfWork"):
            detached.commit()
        store.close()
        assert driver.pool.closed is True

    def test_document_store_reload_errors_and_enter_cleanup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connection = _Connection()
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())

        connection.state_row = None
        with pytest.raises(OpenInfraError, match="schema is not initialized"):
            store.reload()
        connection.state_row = _Lob("[]")
        with pytest.raises(OpenInfraError, match="payload is invalid"):
            store.reload()
        connection.state_row = _Lob("{}")

        original_reload = store.reload
        store.reload = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("reload"))  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="reload"), OracleUnitOfWork(store):
            pass
        assert driver.pool.released
        store.reload = original_reload  # type: ignore[method-assign]

    def test_migration_executor_success_status_and_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        first = tmp_path / "0001_state.sql"
        first.write_text("CREATE TABLE one_table (id NUMBER);\n", encoding="utf-8")
        second = tmp_path / "0002_block.sql"
        second.write_text("BEGIN\nNULL;\nEND;\n/\n", encoding="utf-8")
        catalog = OracleMigrationCatalog(tmp_path)

        apply_connection = _Connection()
        apply_connection.history_exists = False
        status_connection = _Connection()
        status_connection.migrations = [("0001", "0001_state.sql"), ("0002", "0002_block.sql")]
        driver = _Driver([apply_connection, status_connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        result = OracleMigrationExecutor(_settings(), catalog).apply_all()
        assert result["backend"] == "oracle"
        assert result["current"] is True
        assert apply_connection.commits == 2
        assert apply_connection.closed is True
        assert any(
            "CREATE TABLE openinfra_schema_migrations" in stmt
            for stmt, _ in apply_connection.cursors[0].executed
        )

        failure = _Connection()
        failure.raise_on = "CREATE TABLE one_table"
        fail_driver = _Driver([failure])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: fail_driver))
        with pytest.raises(RuntimeError, match="oracle failure"):
            OracleMigrationExecutor(_settings(), catalog).apply_all()
        assert failure.rollbacks == 1
        assert failure.closed is True

        missing = OracleMigrationCatalog(tmp_path / "missing")
        with pytest.raises(OpenInfraError, match="directory is missing"):
            missing.migrations()
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(OpenInfraError, match="catalog is empty"):
            OracleMigrationCatalog(empty).migrations()

    def test_readiness_reports_ready_missing_and_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connection = _Connection()
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())
        probe = OracleReadinessProbe(store, OracleMigrationCatalog(Path("unused")))
        assert probe.check().ready is True
        connection.state_row = None
        status = probe.check()
        assert status.ready is False
        assert "missing" in status.detail
        driver.pool.raise_on_acquire = True
        status = probe.check()
        assert status.ready is False
        assert "RuntimeError" in status.detail
