from __future__ import annotations

import json
from pathlib import Path

import pytest

import openinfra.infrastructure.oracle as oracle_module
from openinfra.domain.common import ConflictError, OpenInfraError, ValidationError
from openinfra.infrastructure.oracle import (
    OracleConnectionSettings,
    OracleDocumentStore,
    OracleDriver,
    OracleMigration,
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
        self._parameters: object = None

    def execute(self, statement: str, parameters: object = None, **kwargs: object) -> None:
        self._last = " ".join(statement.split())
        self._parameters = parameters or kwargs
        self.executed.append((self._last, self._parameters))
        if self.connection.raise_on and self.connection.raise_on in self._last:
            raise RuntimeError("oracle failure")
        for pattern, error in self.connection.errors.items():
            if pattern in self._last:
                raise error
        if self._last.startswith("UPDATE openinfra_document_state"):
            self.rowcount = self.connection.update_rowcount
            if self.rowcount == 1:
                values = parameters if isinstance(parameters, dict) else kwargs
                self.connection.state_row = _Lob(str(values["payload"]))
                self.connection.version += 1
        values = parameters if isinstance(parameters, dict) else kwargs
        if self._last.startswith("MERGE INTO openinfra_document_shards target"):
            key = str(values["shard_key"])
            self.connection.shards.setdefault(key, (_Lob(str(values["payload"])), 0))
        if self._last.startswith("UPDATE openinfra_document_shards"):
            key = str(values["shard_key"])
            current = self.connection.shards.get(key)
            expected = int(values["expected_version"])
            if current is None or current[1] != expected or self.connection.update_rowcount == 0:
                self.rowcount = 0
            else:
                self.rowcount = 1
                self.connection.shards[key] = (
                    _Lob(str(values["payload"])),
                    current[1] + 1,
                )
        if self._last.startswith("MERGE INTO openinfra_schema_migrations target"):
            self.connection.upsert_migration(
                str(values["version"]),
                str(values["filename"]),
                str(values["oracle_checksum"]),
                "" if values["source_checksum"] is None else str(values["source_checksum"]),
                None,
                "applying",
            )
        if self._last.startswith("UPDATE openinfra_schema_migrations"):
            status = "failed" if "status = 'failed'" in self._last else "applied"
            self.connection.upsert_migration(
                str(values["version"]),
                str(values["filename"]),
                str(values["oracle_checksum"]),
                "" if values["source_checksum"] is None else str(values["source_checksum"]),
                "now" if status == "applied" else None,
                status,
            )
        if self._last.startswith("CREATE TABLE openinfra_schema_migrations"):
            self.connection.history_exists = True

    def fetchone(self) -> tuple[object, ...] | None:
        if "COUNT(*) FROM user_tables" in self._last:
            values = self._parameters if isinstance(self._parameters, dict) else {}
            if values.get("table_name") == "OPENINFRA_DOCUMENT_SHARDS":
                return (1 if self.connection.shard_table_exists else 0,)
            return (1 if self.connection.history_exists else 0,)
        if self._last.startswith("SELECT COUNT(*) FROM openinfra_document_shards"):
            return (len(self.connection.shards),)
        if "openinfra_document_state" in self._last:
            if self.connection.state_row is None:
                return None
            if self._last.startswith("SELECT version"):
                return (self.connection.version,)
            return (self.connection.state_row, self.connection.version)
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        if self._last.startswith(
            "SELECT shard_key, payload, version FROM openinfra_document_shards"
        ):
            return [
                (key, payload, version)
                for key, (payload, version) in sorted(self.connection.shards.items())
            ]
        if "SELECT column_name FROM user_tab_columns" in self._last:
            return [(column,) for column in self.connection.history_columns]
        if self._last.startswith(
            "SELECT version, filename, oracle_checksum, source_checksum, status"
        ):
            return [
                (version, filename, oracle_checksum, source_checksum, status)
                for version, filename, oracle_checksum, source_checksum, _applied_at, status in self.connection.migrations
            ]
        if "FROM openinfra_schema_migrations ORDER BY version" in self._last:
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
        self.shard_table_exists = False
        self.shards: dict[str, tuple[object, int]] = {}
        self.migrations: list[tuple[str, str, str, str, object, str]] = []
        self.history_columns = {
            "VERSION",
            "FILENAME",
            "ORACLE_CHECKSUM",
            "SOURCE_CHECKSUM",
            "STATUS",
            "STARTED_AT",
            "APPLIED_AT",
            "ERROR_MESSAGE",
        }
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.raise_on = ""
        self.errors: dict[str, Exception] = {}
        self.cursors: list[_Cursor] = []

    def cursor(self) -> _Cursor:
        cursor = _Cursor(self)
        self.cursors.append(cursor)
        return cursor

    def upsert_migration(
        self,
        version: str,
        filename: str,
        oracle_checksum: str,
        source_checksum: str,
        applied_at: object,
        status: str,
    ) -> None:
        row = (version, filename, oracle_checksum, source_checksum, applied_at, status)
        self.migrations = [item for item in self.migrations if item[0] != version]
        self.migrations.append(row)
        self.migrations.sort(key=lambda item: item[0])

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

    def test_document_store_bootstraps_and_updates_oracle_shards(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connection = _Connection(
            {
                "identity_users": {"default:alice": {"username": "alice"}},
                "sites": {},
            }
        )
        connection.shard_table_exists = True
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))

        store = OracleDocumentStore(_settings())

        assert store.sharded is True
        assert connection.commits == 1
        assert "identity_users" in connection.shards
        assert "sites" in connection.shards

        manager = OracleTransactionManager(store)
        with manager.begin() as unit_of_work:
            store.data["identity_users"]["default:bob"] = {"username": "bob"}
            unit_of_work.commit()

        shard_updates = [
            parameters
            for cursor in connection.cursors
            for statement, parameters in cursor.executed
            if statement.startswith("UPDATE openinfra_document_shards")
        ]
        assert len(shard_updates) == 1
        assert shard_updates[0]["shard_key"] == "identity_users"
        payload, version = connection.shards["identity_users"]
        assert version == 1
        assert json.loads(payload.read())["default:bob"]["username"] == "bob"

    def test_document_store_detects_concurrent_update_per_shard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connection = _Connection({"identity_users": {}, "sites": {}})
        connection.shard_table_exists = True
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())
        manager = OracleTransactionManager(store)

        with manager.begin() as unit_of_work:
            store.data["sites"]["default:par1"] = {"code": "PAR1"}
            payload, version = connection.shards["sites"]
            connection.shards["sites"] = (payload, version + 1)
            with pytest.raises(ConflictError, match="shard changed concurrently: sites"):
                unit_of_work.commit()

        with manager.begin() as unit_of_work:
            store.data["identity_users"]["default:alice"] = {"username": "alice"}
            unit_of_work.commit()
        assert connection.shards["identity_users"][1] == 1

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
        driver = _Driver([apply_connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        result = OracleMigrationExecutor(_settings(), catalog).apply_all()
        assert result["backend"] == "oracle"
        assert result["current"] is True
        assert apply_connection.commits == 5
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
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        migration_path = tmp_path / "0001_state.sql"
        migration_path.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")
        catalog = OracleMigrationCatalog(tmp_path)
        migration = catalog.migrations()[0]
        connection = _Connection()
        connection.migrations = [
            (
                "0001",
                migration.path.name,
                migration.oracle_checksum,
                migration.source_checksum,
                "now",
                "applied",
            )
        ]
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())
        probe = OracleReadinessProbe(store, catalog)
        assert probe.check().ready is True
        connection.state_row = None
        status = probe.check()
        assert status.ready is False
        assert "incomplete" in status.detail
        connection.state_row = (1,)
        connection.migrations[0] = (
            "0001",
            migration.path.name,
            "",
            migration.source_checksum,
            "now",
            "applied",
        )
        assert probe.check().ready is False
        driver.pool.raise_on_acquire = True
        status = probe.check()
        assert status.ready is False
        assert "RuntimeError" in status.detail

    def test_catalog_manifest_source_parity_and_drift(self, tmp_path: Path) -> None:
        project_root = Path(__file__).resolve().parents[2]
        oracle_root = project_root / "installers/migrations/oracle"
        postgresql_root = project_root / "installers/migrations/postgresql"

        migrations = OracleMigrationCatalog(oracle_root, postgresql_root).migrations()

        assert len(migrations) == 59
        assert migrations[0].version == "0001"
        assert migrations[-1].version == "0059"
        assert all(migration.oracle_checksum for migration in migrations)
        assert all(migration.source_checksum for migration in migrations)
        manifest_only = OracleMigrationCatalog(oracle_root).migrations()
        assert [migration.source_checksum for migration in manifest_only] == [
            migration.source_checksum for migration in migrations
        ]

        copied_oracle = tmp_path / "oracle"
        copied_postgresql = tmp_path / "postgresql"
        import shutil

        shutil.copytree(oracle_root, copied_oracle)
        shutil.copytree(postgresql_root, copied_postgresql)
        (copied_oracle / "0001_bootstrap.sql").write_text("drift\n", encoding="utf-8")
        with pytest.raises(OpenInfraError, match="checksum drift"):
            OracleMigrationCatalog(copied_oracle, copied_postgresql).migrations()

        shutil.rmtree(copied_oracle)
        shutil.copytree(oracle_root, copied_oracle)
        (copied_postgresql / "0059_runtime_offline_licensing.sql").unlink()
        with pytest.raises(OpenInfraError, match="filenames diverge"):
            OracleMigrationCatalog(copied_oracle, copied_postgresql).migrations()

    def test_catalog_rejects_invalid_manifest_and_version_gap(self, tmp_path: Path) -> None:
        root = tmp_path / "oracle"
        root.mkdir()
        (root / "0002_gap.sql").write_text("SELECT 1 FROM dual;\n", encoding="utf-8")
        with pytest.raises(OpenInfraError, match="contiguous"):
            OracleMigrationCatalog(root).migrations()

        (root / "0002_gap.sql").rename(root / "0001_state.sql")
        (root / "manifest.json").write_text("not-json\n", encoding="utf-8")
        with pytest.raises(OpenInfraError, match="manifest is invalid"):
            OracleMigrationCatalog(root).migrations()

        (root / "manifest.json").write_text(
            json.dumps({"schema": "wrong", "count": 0, "migrations": []}),
            encoding="utf-8",
        )
        with pytest.raises(OpenInfraError, match="schema is invalid"):
            OracleMigrationCatalog(root).migrations()

        project_root = Path(__file__).resolve().parents[2]
        payload = project_root / "installers/migrations/oracle/manifest.json"
        manifest = json.loads(payload.read_text(encoding="utf-8"))
        single = manifest["migrations"][0]
        (root / "0001_state.sql").unlink()
        (root / str(single["filename"])).write_bytes(
            (project_root / "installers/migrations/oracle" / str(single["filename"])).read_bytes()
        )
        single["source_sha256"] = "invalid"
        (root / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": "openinfra.oracle-migration-catalog/v1",
                    "count": 1,
                    "migrations": [single],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(OpenInfraError, match="source migration checksum is invalid"):
            OracleMigrationCatalog(root).migrations()

    def test_executor_recovers_legacy_document_state_history(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        migration = tmp_path / "0001_bootstrap.sql"
        migration.write_text(
            "CREATE TABLE openinfra_document_state (id NUMBER);\n"
            "CREATE TABLE new_table (id NUMBER);\n",
            encoding="utf-8",
        )
        connection = _Connection()
        connection.migrations = [("0001", "0001_document_state.sql", "", "", "now", "applied")]
        connection.errors = {
            "CREATE TABLE openinfra_document_state": RuntimeError(
                "ORA-00955: name is already used by an existing object"
            )
        }
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))

        result = OracleMigrationExecutor(_settings(), OracleMigrationCatalog(tmp_path)).apply_all()

        assert result["current"] is True
        assert result["newly_applied"] == ["0001_bootstrap.sql"]
        assert connection.migrations[0][1] == "0001_bootstrap.sql"
        assert connection.migrations[0][5] == "applied"
        assert any(
            statement.startswith("CREATE TABLE new_table")
            for cursor in connection.cursors
            for statement, _parameters in cursor.executed
        )

    def test_executor_detects_database_checksum_drift(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        migration_path = tmp_path / "0001_state.sql"
        migration_path.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")
        migration = OracleMigrationCatalog(tmp_path).migrations()[0]
        connection = _Connection()
        connection.migrations = [
            (
                migration.version,
                migration.path.name,
                "0" * 64,
                "",
                "now",
                "applied",
            )
        ]
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))

        with pytest.raises(OpenInfraError, match="checksum drift"):
            OracleMigrationExecutor(_settings(), OracleMigrationCatalog(tmp_path)).apply_all()

    def test_executor_failure_is_persisted_and_recovery_errors_are_narrow(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        migration_path = tmp_path / "0001_state.sql"
        migration_path.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")
        connection = _Connection()
        connection.raise_on = "CREATE TABLE sample"
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))

        with pytest.raises(RuntimeError, match="oracle failure"):
            OracleMigrationExecutor(_settings(), OracleMigrationCatalog(tmp_path)).apply_all()

        assert connection.migrations[0][5] == "failed"
        assert connection.rollbacks == 1
        assert (
            OracleMigrationExecutor._oracle_error_code(RuntimeError("ORA-00955: duplicate")) == 955
        )
        assert OracleMigrationExecutor._is_recoverable_ddl_error(
            "CREATE TABLE sample (id NUMBER)", RuntimeError("ORA-00955: duplicate")
        )
        assert not OracleMigrationExecutor._is_recoverable_ddl_error(
            "INSERT INTO sample VALUES (1)", RuntimeError("ORA-00955: duplicate")
        )
        assert not OracleMigrationExecutor._is_recoverable_ddl_error(
            "CREATE TABLE sample (id NUMBER)", RuntimeError("ORA-00001: unique")
        )
        assert OracleMigrationExecutor._is_recoverable_ddl_error(
            "CREATE UNIQUE INDEX uq_sample ON sample (id)",
            RuntimeError("ORA-00955: duplicate"),
        )
        assert OracleMigrationExecutor._is_recoverable_ddl_error(
            "CREATE GLOBAL TEMPORARY TABLE sample_tmp (id NUMBER)",
            RuntimeError("ORA-00955: duplicate"),
        )

    def test_history_upgrade_and_status_drift_reporting(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        migration_path = tmp_path / "0001_state.sql"
        migration_path.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")
        migration = OracleMigrationCatalog(tmp_path).migrations()[0]
        connection = _Connection()
        connection.history_columns = {"VERSION", "FILENAME", "APPLIED_AT"}
        connection.migrations = [
            (
                migration.version,
                migration.path.name,
                migration.oracle_checksum,
                "",
                "now",
                "failed",
            ),
            ("9999", "9999_unexpected.sql", "", "", "now", "applied"),
        ]
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        executor = OracleMigrationExecutor(_settings(), OracleMigrationCatalog(tmp_path))

        status = executor.status_as_dict()

        assert status["current"] is False
        assert "0001:failed" in status["drift"]
        assert "9999:unexpected" in status["drift"]
        altered = [
            statement
            for cursor in connection.cursors
            for statement, _parameters in cursor.executed
            if statement.startswith("ALTER TABLE openinfra_schema_migrations ADD")
        ]
        assert len(altered) == 5

    def test_document_store_noop_unavailable_and_external_reload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connection = _Connection({"identity_users": []})
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())

        commits = connection.commits
        store.flush_with_connection(connection)
        assert connection.commits == commits

        store.reload(connection, for_update=True)
        assert any("FOR UPDATE" in statement for statement, _ in connection.cursors[-1].executed)

        monkeypatch.setattr(store._pool, "acquire", lambda: None)  # private test double
        with pytest.raises(OpenInfraError, match="connection is unavailable"):
            store.reload()

    def test_catalog_packaged_path_and_manifest_error_matrix(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        fake_module = tmp_path / "site" / "openinfra" / "infrastructure" / "oracle.py"
        fake_module.parent.mkdir(parents=True)
        fake_module.write_text("# test\n", encoding="utf-8")
        packaged_oracle = fake_module.parents[1] / "migrations" / "oracle"
        packaged_postgresql = fake_module.parents[1] / "migrations" / "postgresql"
        packaged_oracle.mkdir(parents=True)
        packaged_postgresql.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(oracle_module, "__file__", str(fake_module))
        catalog = OracleMigrationCatalog.from_project_root()
        assert catalog.root == packaged_oracle
        assert catalog.source_root == packaged_postgresql

        root = tmp_path / "catalog"
        root.mkdir()
        migration = root / "0001_state.sql"
        migration.write_text("CREATE TABLE state_table (id NUMBER);\n", encoding="utf-8")
        checksum = OracleMigrationCatalog._sha256(migration)

        def write_manifest(migrations: object, count: object = 1) -> None:
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema": "openinfra.oracle-migration-catalog/v1",
                        "count": count,
                        "migrations": migrations,
                    }
                ),
                encoding="utf-8",
            )

        write_manifest([], 1)
        with pytest.raises(OpenInfraError, match="count is invalid"):
            OracleMigrationCatalog(root).migrations()
        write_manifest(["bad"])
        with pytest.raises(OpenInfraError, match="entry is invalid"):
            OracleMigrationCatalog(root).migrations()
        entry = {
            "version": "0001",
            "filename": migration.name,
            "oracle_sha256": checksum,
            "source_sha256": "1" * 64,
        }
        write_manifest([entry, entry], 2)
        with pytest.raises(OpenInfraError, match="duplicate filenames"):
            OracleMigrationCatalog(root).migrations()
        write_manifest([{**entry, "filename": "0001_other.sql"}])
        with pytest.raises(OpenInfraError, match="filenames diverge"):
            OracleMigrationCatalog(root).migrations()
        write_manifest([{**entry, "version": "9999"}])
        with pytest.raises(OpenInfraError, match="version mismatch"):
            OracleMigrationCatalog(root).migrations()

        source_missing = tmp_path / "missing-postgresql"
        with pytest.raises(OpenInfraError, match="PostgreSQL migration directory is missing"):
            OracleMigrationCatalog(root, source_missing).migrations()

        source = tmp_path / "postgresql"
        source.mkdir()
        source_migration = source / migration.name
        source_migration.write_text("CREATE TABLE source_table (id BIGINT);\n", encoding="utf-8")
        source_checksum = OracleMigrationCatalog._sha256(source_migration)
        write_manifest([{**entry, "source_sha256": "2" * 64}])
        with pytest.raises(OpenInfraError, match="source migration checksum drift"):
            OracleMigrationCatalog(root, source).migrations()
        write_manifest([{**entry, "source_sha256": source_checksum}])
        assert (
            OracleMigrationCatalog(root, source).migrations()[0].source_checksum == source_checksum
        )

    def test_executor_status_verification_and_splitter_edges(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        migration_path = tmp_path / "0001_state.sql"
        migration_path.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")
        migration = OracleMigrationCatalog(tmp_path).migrations()[0]
        connection = _Connection()
        connection.migrations = [
            ("0001", "wrong.sql", "", "bad", "now", "applied"),
        ]
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        status = OracleMigrationExecutor(
            _settings(), OracleMigrationCatalog(tmp_path)
        ).status_as_dict()
        assert status["current"] is False
        assert set(status["drift"]) >= {
            "0001:filename",
            "0001:oracle-checksum",
        }

        sourced = OracleMigration(
            migration.version,
            migration.path,
            migration.oracle_checksum,
            "1" * 64,
        )
        with pytest.raises(OpenInfraError, match="invalid status"):
            OracleMigrationExecutor._verify_applied(
                sourced,
                (
                    migration.path.name,
                    migration.oracle_checksum,
                    sourced.source_checksum,
                    None,
                    "failed",
                ),
            )
        with pytest.raises(OpenInfraError, match="filename drift"):
            OracleMigrationExecutor._verify_applied(
                sourced,
                (
                    "wrong.sql",
                    migration.oracle_checksum,
                    sourced.source_checksum,
                    None,
                    "applied",
                ),
            )
        with pytest.raises(OpenInfraError, match="source checksum drift"):
            OracleMigrationExecutor._verify_applied(
                sourced,
                (
                    migration.path.name,
                    migration.oracle_checksum,
                    "2" * 64,
                    None,
                    "applied",
                ),
            )

        class _OracleError:
            code = -955

        assert OracleMigrationExecutor._oracle_error_code(RuntimeError(_OracleError())) == 955
        statements = OracleMigrationExecutor._split_statements(
            "-- heading\n"
            "INSERT INTO sample(text_value) VALUES ('a;''b');\n"
            'INSERT INTO sample(text_value) VALUES ("quoted;name");\n'
            "BEGIN\n  NULL;\nEND;\n/\n"
        )
        assert len(statements) == 3
        assert "a;''b" in statements[0]
        assert '"quoted;name"' in statements[1]

    def test_readiness_rejects_unexpected_and_missing_source_checksum(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        oracle_root = tmp_path / "oracle"
        source_root = tmp_path / "postgresql"
        oracle_root.mkdir()
        source_root.mkdir()
        name = "0001_state.sql"
        oracle_path = oracle_root / name
        source_path = source_root / name
        oracle_path.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")
        source_path.write_text("CREATE TABLE sample (id BIGINT);\n", encoding="utf-8")
        catalog = OracleMigrationCatalog(oracle_root, source_root)
        migration = catalog.migrations()[0]
        connection = _Connection()
        driver = _Driver([connection])
        monkeypatch.setattr(OracleDriver, "load", staticmethod(lambda: driver))
        store = OracleDocumentStore(_settings())
        probe = OracleReadinessProbe(store, catalog)

        connection.migrations = [
            (
                "9999",
                "9999_unknown.sql",
                migration.oracle_checksum,
                migration.source_checksum,
                "now",
                "applied",
            )
        ]
        assert probe.check().ready is False
        connection.migrations = [
            (
                migration.version,
                migration.path.name,
                migration.oracle_checksum,
                "",
                "now",
                "applied",
            )
        ]
        assert probe.check().ready is False
