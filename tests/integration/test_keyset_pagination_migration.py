from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0053_keyset_pagination_indexes.sql"


def test_keyset_pagination_migration_is_additive_transactional_and_complete() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    normalized = " ".join(sql.lower().split())
    assert sql.count("BEGIN;") == 1
    assert sql.count("COMMIT;") == 1
    assert normalized.count("create index if not exists") >= 45
    for table in (
        "source_objects",
        "source_relations",
        "audit_events",
        "finops_cost_records",
        "greenops_energy_measurements",
        "sbom_vulnerabilities",
        "rag_documents",
        "multisite_dr_drills",
        "certificate_inventory",
        "flow_observations",
        "network_config_observations",
    ):
        assert f" on {table} " in normalized
    assert "drop table" not in normalized
    assert "drop index" not in normalized
    assert "truncate" not in normalized
    assert "delete from" not in normalized
    assert "update " not in normalized


def test_postgresql_runtime_uses_offset_only_for_legacy_cursor_compatibility() -> None:
    source = (ROOT / "src/openinfra/infrastructure/postgresql.py").read_text(encoding="utf-8")
    pagination = (ROOT / "src/openinfra/infrastructure/cursor_pagination.py").read_text(
        encoding="utf-8"
    )

    assert " OFFSET %(" not in source
    assert "page.offset_sql" in source
    assert '" OFFSET %(legacy_offset)s"' in pagination
    assert "legacy_offset" in pagination
