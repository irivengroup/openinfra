from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0049_rag_governed_assistant.sql"


def test_rag_migration_is_partitioned_indexed_constrained_and_non_destructive() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in (
        "rag_documents",
        "rag_chunks",
        "rag_answers",
        "rag_jobs",
        "rag_artifacts",
        "rag_event_outbox",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "PARTITION BY HASH (tenant_id)" in sql
    assert "to_tsvector" in sql and "GIN" in sql
    assert "required_permissions" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()


def test_rag_precedes_multisite_postgresql_migration() -> None:
    names = [
        path.name for path in sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    ]
    expected_order = (
        "0049_rag_governed_assistant.sql",
        "0050_pro_centralized_multisite.sql",
        "0051_enterprise_regional_discovery_routing.sql",
        "0052_multisite_disaster_recovery.sql",
        "0053_keyset_pagination_indexes.sql",
        "0054_async_outbox_workers.sql",
    )
    assert len(names) >= 55
    assert [names.index(name) for name in expected_order] == sorted(
        names.index(name) for name in expected_order
    )
