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


def test_multisite_migrations_preserve_order_before_later_platform_migrations() -> None:
    migrations = sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    names = [migration.name for migration in migrations]
    expected = [
        "0050_pro_centralized_multisite.sql",
        "0051_enterprise_regional_discovery_routing.sql",
        "0052_multisite_disaster_recovery.sql",
        "0053_keyset_pagination_indexes.sql",
        "0054_async_outbox_workers.sql",
        "0055_kubernetes_topology_inventory.sql",
        "0056_kubernetes_gitops_drift.sql",
    ]
    assert len(migrations) == 57
    assert all(name in names for name in expected)
    assert [names.index(name) for name in expected] == sorted(
        names.index(name) for name in expected
    )


def test_enterprise_regional_discovery_migration_is_safe_and_operable() -> None:
    migration = ROOT / (
        "installers/migrations/postgresql/0051_enterprise_regional_discovery_routing.sql"
    )
    sql = migration.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS multisite_regional_discovery_routes" in sql
    assert "PARTITION BY HASH (tenant_id)" in sql
    assert sql.count("PARTITION OF multisite_regional_discovery_routes") == 8
    assert "UNIQUE (tenant_id, region_code, site_code, vrf_code)" in sql
    assert "REFERENCES discovery_collectors (tenant_id, id) ON DELETE RESTRICT" in sql
    assert "'network-proxy'" in sql and "'datacenter-proxy'" in sql
    assert "idx_multisite_regional_routes_lookup" in sql
    assert "idx_audit_events_multisite_regional_discovery" in sql
    assert sql.count("BEGIN;") == 1 and sql.count("COMMIT;") == 1
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()


def test_multisite_disaster_recovery_migration_is_safe_partitioned_and_audited() -> None:
    migration = ROOT / "installers/migrations/postgresql/0052_multisite_disaster_recovery.sql"
    sql = migration.read_text(encoding="utf-8")
    for table in ("multisite_dr_plans", "multisite_dr_drills"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert sql.count("PARTITION BY HASH (tenant_id)") == 2
    assert sql.count("PARTITION OF multisite_dr_plans") == 8
    assert sql.count("PARTITION OF multisite_dr_drills") == 8
    assert "UNIQUE (tenant_id, primary_site_code, recovery_site_code)" in sql
    assert "REFERENCES multisite_dr_plans (tenant_id, id) ON DELETE RESTRICT" in sql
    assert "idx_multisite_dr_plans_active" in sql
    assert "idx_multisite_dr_drills_plan_time" in sql
    assert "idx_audit_events_multisite_dr" in sql
    assert sql.count("BEGIN;") == 1 and sql.count("COMMIT;") == 1
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()
