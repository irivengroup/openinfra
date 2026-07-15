from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0055_kubernetes_topology_inventory.sql"


def test_kubernetes_topology_migration_is_partitioned_indexed_constrained_and_non_destructive() -> (
    None
):
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in ("kubernetes_topology_snapshots", "kubernetes_topology_event_outbox"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert sql.count("PARTITION BY HASH (tenant_id)") == 2
    assert "UNIQUE (tenant_id, fingerprint)" in sql
    assert "resource_count BETWEEN 1 AND 50000" in sql
    assert "USING gin (payload jsonb_path_ops)" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()


def test_kubernetes_topology_migration_remains_ordered_before_gitops_extension() -> None:
    names = [
        path.name for path in sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    ]
    assert len(names) >= 56
    assert "0055_kubernetes_topology_inventory.sql" in names
    assert names.index("0055_kubernetes_topology_inventory.sql") < names.index(
        "0056_kubernetes_gitops_drift.sql"
    )
