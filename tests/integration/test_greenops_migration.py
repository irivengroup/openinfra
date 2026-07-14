from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0047_greenops_energy_capacity.sql"


def test_greenops_migration_is_partitioned_indexed_and_constrained() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())
    for table in (
        "greenops_measurement_sources",
        "greenops_policies",
        "greenops_carbon_factors",
        "greenops_measurement_idempotency",
        "greenops_energy_measurements",
        "greenops_anomalies",
        "greenops_forecasts",
        "greenops_consolidation_candidates",
        "greenops_scores",
        "greenops_reports",
        "greenops_event_outbox",
    ):
        assert f"create table if not exists {table}" in normalized
    assert normalized.count("partition by hash (tenant_id)") == 10
    assert "partition by range (period_start)" in normalized
    assert "primary key (tenant_id, idempotency_key)" in normalized
    assert "payload_digest ~ '^[a-f0-9]{64}$'" in normalized
    assert "using gin (payload jsonb_path_ops)" in normalized
    assert "using brin (period_start)" in normalized
    assert "where published_at is null" in normalized
    assert "payload ->> 'requires_human_approval' = 'true'" in normalized
    assert "drop table" not in normalized
    assert "truncate " not in normalized


def test_greenops_precedes_sbom_and_rag_without_being_modified() -> None:
    names = [
        path.name for path in sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    ]
    expected_order = (
        "0047_greenops_energy_capacity.sql",
        "0048_sbom_vulnerabilities_exposure.sql",
        "0049_rag_governed_assistant.sql",
        "0050_pro_centralized_multisite.sql",
        "0051_enterprise_regional_discovery_routing.sql",
        "0052_multisite_disaster_recovery.sql",
        "0053_keyset_pagination_indexes.sql",
        "0054_async_outbox_workers.sql",
    )
    assert len(names) == 55
    assert [names.index(name) for name in expected_order] == sorted(
        names.index(name) for name in expected_order
    )
