from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0056_kubernetes_gitops_drift.sql"


def test_kubernetes_gitops_migration_is_partitioned_indexed_constrained_and_non_destructive() -> (
    None
):
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in ("kubernetes_gitops_states", "kubernetes_gitops_event_outbox"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert sql.count("PARTITION BY HASH (tenant_id)") == 2
    assert "UNIQUE (tenant_id, fingerprint)" in sql
    assert "resource_count BETWEEN 1 AND 50000" in sql
    assert "revision ~ '^[a-f0-9]{40}$' OR revision ~ '^[a-f0-9]{64}$'" in sql
    assert "USING gin (payload jsonb_path_ops)" in sql
    assert "idx_kubernetes_gitops_latest" in sql
    assert "idx_kubernetes_gitops_event_outbox_pending" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "TRUNCATE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()


def test_kubernetes_gitops_precedes_federated_identity_migration() -> None:
    names = [
        path.name for path in sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    ]
    assert len(names) == 58
    assert names[-4:] == [
        "0055_kubernetes_topology_inventory.sql",
        "0056_kubernetes_gitops_drift.sql",
        "0057_federated_identity_team_sync.sql",
        "0058_oracle_document_shards.sql",
    ]
