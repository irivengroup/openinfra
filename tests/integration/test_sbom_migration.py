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
    names = [
        path.name for path in sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    ]
    expected_order = (
        "0048_sbom_vulnerabilities_exposure.sql",
        "0049_rag_governed_assistant.sql",
        "0050_pro_centralized_multisite.sql",
        "0051_enterprise_regional_discovery_routing.sql",
        "0052_multisite_disaster_recovery.sql",
    )
    assert len(names) == 52
    assert [names.index(name) for name in expected_order] == sorted(
        names.index(name) for name in expected_order
    )
