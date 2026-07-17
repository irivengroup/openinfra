from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.oracle import (
    OracleConnectionSettings,
    OracleMigrationCatalog,
    OracleMigrationExecutor,
)
from openinfra.infrastructure.runtime_config import (
    RuntimeConfig,
    RuntimeDatabaseBackendResolver,
    RuntimeOracleSettingsResolver,
)


class _Loader:
    def __init__(self, values: dict[str, str]) -> None:
        self._runtime = RuntimeConfig(values, None)

    def load(self) -> RuntimeConfig:
        return self._runtime


class TestOracleRuntime:
    def test_postgresql_is_default_and_oracle_is_explicit(self) -> None:
        assert RuntimeDatabaseBackendResolver(_Loader({})).resolve() == "postgresql"
        assert (
            RuntimeDatabaseBackendResolver(
                _Loader({"OPENINFRA_DATABASE_BACKEND": "oracle"})
            ).resolve()
            == "oracle"
        )
        with pytest.raises(ValidationError, match="postgresql, oracle or json"):
            RuntimeDatabaseBackendResolver(_Loader({})).resolve("mysql")

    def test_oracle_settings_resolve_password_reference(self, tmp_path: Path) -> None:
        password_file = tmp_path / "oracle-password"
        password_file.write_text("correct-horse-battery-staple\n", encoding="utf-8")
        resolver = RuntimeOracleSettingsResolver(
            _Loader(
                {
                    "OPENINFRA_ORACLE_DSN": "db.example.net:1521/OPENINFRA",
                    "OPENINFRA_ORACLE_USER": "openinfra",
                    "OPENINFRA_ORACLE_PASSWORD_REF": "file://" + str(password_file),
                    "OPENINFRA_ORACLE_POOL_MIN": "2",
                    "OPENINFRA_ORACLE_POOL_MAX": "12",
                    "OPENINFRA_ORACLE_POOL_INCREMENT": "2",
                }
            )
        )

        settings = resolver.resolve()

        assert settings.dsn == "db.example.net:1521/OPENINFRA"
        assert settings.user == "openinfra"
        assert settings.password == "correct-horse-battery-staple"
        assert (settings.pool_min, settings.pool_max, settings.pool_increment) == (2, 12, 2)

    def test_oracle_settings_and_migration_catalog_are_strict(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="pool bounds"):
            OracleConnectionSettings.create(
                dsn="db/OPENINFRA",
                user="openinfra",
                password="secret",  # noqa: S106
                pool_min=10,
                pool_max=2,
            )
        migration = tmp_path / "0001_state.sql"
        migration.write_text("CREATE TABLE sample (id NUMBER);\n", encoding="utf-8")

        catalog = OracleMigrationCatalog(tmp_path)

        assert tuple(item.path.name for item in catalog.migrations()) == ("0001_state.sql",)
        assert OracleMigrationExecutor._split_statements(
            "-- ignored\nCREATE TABLE first_table (id NUMBER);\nBEGIN\nNULL;\nEND;\n/\n"
        ) == (
            "CREATE TABLE first_table (id NUMBER)",
            "BEGIN\nNULL;\nEND;",
        )
