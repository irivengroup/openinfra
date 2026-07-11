from __future__ import annotations

from pathlib import Path


def test_simulation_migration_is_partitioned_indexed_and_non_destructive() -> None:
    migration = Path(
        "installers/migrations/postgresql/0045_simulation_migration_planning.sql"
    ).read_text(encoding="utf-8")
    normalized = migration.lower()

    for table in (
        "simulation_scenarios",
        "simulation_impact_reports",
        "simulation_scenario_comparisons",
        "simulation_event_outbox",
    ):
        assert f"create table if not exists {table}" in normalized
        assert f"'{table}'" in normalized
    assert "partition by hash (tenant_id)" in normalized
    assert "for partition_index in 0..15 loop" in normalized
    assert "modulus 16" in normalized
    assert "unique (tenant_id, idempotency_key)" in normalized
    assert "input_sha256" in normalized
    assert "jsonb_path_ops" in normalized
    assert "using brin" in normalized
    assert "where published_at is null" in normalized
    assert "references tenants(id) on delete cascade" in normalized
    assert "drop table" not in normalized
    assert "drop column" not in normalized
