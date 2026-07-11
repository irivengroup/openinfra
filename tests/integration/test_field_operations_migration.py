from __future__ import annotations

from pathlib import Path


def test_field_operations_migration_is_partitioned_indexed_and_non_destructive() -> None:
    migration = Path(
        "installers/migrations/postgresql/0044_field_operations_mobile_offline.sql"
    ).read_text(encoding="utf-8")
    normalized = migration.lower()

    for table in (
        "field_operation_sheets",
        "field_evidence",
        "intervention_locks",
        "offline_sync_packages",
        "field_event_outbox",
    ):
        assert f"create table if not exists {table}" in normalized
    assert normalized.count("partition of field_operation_sheets") == 16
    assert normalized.count("partition of field_evidence") == 16
    assert normalized.count("partition of field_event_outbox") == 16
    assert "unique" in normalized
    assert "idempotency_key" in normalized
    assert "payload_sha256" in normalized
    assert "content_sha256" in normalized
    assert "drop table" not in normalized
    assert "drop column" not in normalized
