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
    migrations = sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    assert len(migrations) == 50
    assert migrations[-3].name == "0048_sbom_vulnerabilities_exposure.sql"
    assert migrations[-2].name == "0049_rag_governed_assistant.sql"
    assert migrations[-1].name == "0050_pro_centralized_multisite.sql"
