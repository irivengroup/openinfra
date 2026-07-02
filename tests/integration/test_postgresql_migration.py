from __future__ import annotations

from openinfra.infrastructure.postgresql import PostgreSQLMigrationCatalog


class TestPostgreSQLMigration:
    def test_bootstrap_migration_is_partitioned_indexed_and_audited(self) -> None:
        migration = PostgreSQLMigrationCatalog.from_project_root().load("0001_bootstrap")

        assert "PARTITION BY HASH" in migration.sql
        assert "PARTITION BY RANGE" in migration.sql
        assert "CREATE INDEX" in migration.sql
        assert "audit_events" in migration.sql
