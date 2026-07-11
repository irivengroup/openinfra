from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0046_finops_costs_showback.sql"


def test_finops_migration_is_partitioned_indexed_and_constrained() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())
    for table in (
        "finops_allocation_rules",
        "finops_import_jobs",
        "finops_cost_records",
        "finops_budgets",
        "finops_financial_periods",
        "finops_cost_anomalies",
        "finops_forecasts",
        "finops_reports",
        "finops_event_outbox",
    ):
        assert f"create table if not exists {table}" in normalized
    assert normalized.count("partition by hash (tenant_id)") == 8
    assert "partition by range (period_start)" in normalized
    assert "modulus 16" in normalized
    assert "priority between 1 and 10000" in normalized
    assert "'dependency','unallocated'" not in normalized
    assert "using gin (payload jsonb_path_ops)" in normalized
    assert "using brin (period_start)" in normalized
    assert "where published_at is null" in normalized
    assert "drop table" not in normalized
    assert "truncate " not in normalized


def test_finops_migration_precedes_greenops_without_being_modified() -> None:
    migrations = sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    assert MIGRATION in migrations
    assert migrations.index(MIGRATION) == 45
