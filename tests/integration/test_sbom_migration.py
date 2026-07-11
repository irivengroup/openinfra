from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0048_sbom_vulnerabilities_exposure.sql"


def test_sbom_migration_is_partitioned_indexed_constrained_and_non_destructive() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in (
        "sbom_documents",
        "sbom_vulnerabilities",
        "sbom_exposure_contexts",
        "sbom_risk_findings",
        "sbom_comparisons",
        "sbom_event_outbox",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "PARTITION BY HASH (tenant_id)" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql
    assert "business_criticality BETWEEN 1 AND 5" in sql
    assert "base_document_id <> target_document_id" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()


def test_sbom_precedes_rag_postgresql_migration() -> None:
    migrations = sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    assert len(migrations) == 50
    assert migrations[-4].name == "0047_greenops_energy_capacity.sql"
    assert migrations[-3].name == "0048_sbom_vulnerabilities_exposure.sql"
    assert migrations[-2].name == "0049_rag_governed_assistant.sql"
    assert migrations[-1].name == "0050_pro_centralized_multisite.sql"
