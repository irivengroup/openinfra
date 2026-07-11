from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0050_pro_centralized_multisite.sql"


def test_multisite_migration_is_partitioned_indexed_constrained_and_non_destructive() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in ("multisite_site_access_grants", "multisite_reports"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert sql.count("PARTITION BY HASH (tenant_id)") == 2
    assert "UNIQUE (tenant_id, subject, site_code)" in sql
    assert "CHECK ((active AND revoked_at IS NULL)" in sql
    assert "idx_multisite_grants_subject_active" in sql
    assert "idx_multisite_reports_subject_generated" in sql
    assert "idx_audit_events_multisite" in sql
    assert sql.count("BEGIN;") == 1
    assert sql.count("COMMIT;") == 1
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()


def test_multisite_is_latest_postgresql_migration() -> None:
    migrations = sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    assert len(migrations) == 50
    assert migrations[-2].name == "0049_rag_governed_assistant.sql"
    assert migrations[-1].name == "0050_pro_centralized_multisite.sql"
