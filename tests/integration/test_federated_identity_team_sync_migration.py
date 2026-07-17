from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.postgresql import PostgreSQLMigration, PostgreSQLMigrationCatalog

MIGRATION_NAME = "0057_federated_identity_team_sync.sql"
PARTITIONED_TABLES = (
    "identity_team_sync_sources",
    "identity_team_sync_runs",
    "federated_identity_links",
)


def test_federated_identity_team_sync_partition_names_are_zero_padded_without_spaces() -> None:
    migration = PostgreSQLMigrationCatalog.from_project_root().load(MIGRATION_NAME)

    assert "%1$02s" not in migration.sql
    assert "partition_suffix := lpad(partition_index::text, 2, '0');" in migration.sql
    assert migration.sql.count("CREATE TABLE IF NOT EXISTS %I") == len(PARTITIONED_TABLES)

    for table in PARTITIONED_TABLES:
        assert f"'{table}_p' || partition_suffix" in migration.sql
        assert f"PARTITION OF {table} FOR VALUES WITH" in migration.sql

    partition_names = {
        f"{table}_p{partition_index:02d}"
        for table in PARTITIONED_TABLES
        for partition_index in range(32)
    }
    assert len(partition_names) == 96
    assert all(" " not in name for name in partition_names)
    assert "identity_team_sync_sources_p00" in partition_names
    assert "identity_team_sync_sources_p31" in partition_names


def test_migration_validation_rejects_postgresql_format_width_for_identifier_suffix() -> None:
    migration = PostgreSQLMigration(
        name="9999_unsafe_dynamic_partition.sql",
        path=Path("9999_unsafe_dynamic_partition.sql"),
        sql="""
        CREATE TABLE unsafe_dynamic_partition (
            tenant_id text NOT NULL,
            id text NOT NULL,
            PRIMARY KEY (tenant_id, id)
        ) PARTITION BY HASH (tenant_id);
        DO $$
        DECLARE
            partition_index integer := 0;
        BEGIN
            EXECUTE format(
                'CREATE TABLE unsafe_dynamic_partition_p%1$02s '
                'PARTITION OF unsafe_dynamic_partition '
                'FOR VALUES WITH (MODULUS 1, REMAINDER %1$s)',
                partition_index
            );
        END
        $$;
        CREATE INDEX unsafe_dynamic_partition_idx
        ON unsafe_dynamic_partition (tenant_id, id);
        CREATE INDEX unsafe_dynamic_partition_audit_idx
        ON audit_events (tenant_id, created_at DESC);
        """,
    )

    with pytest.raises(ValidationError, match=r"format\(\) string widths"):
        migration.validate()
