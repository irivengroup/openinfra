from __future__ import annotations

from pathlib import Path

from openinfra.infrastructure.postgresql import PostgreSQLStatementSplitter

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "installers/migrations/postgresql/0054_async_outbox_workers.sql"


def test_async_processing_migration_is_additive_transactional_and_indexed() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    normalized = " ".join(sql.split()).lower()

    assert normalized.startswith("begin;")
    assert normalized.endswith("commit;")
    assert "drop table" not in normalized
    assert "drop column" not in normalized
    assert "create table if not exists async_jobs" in normalized
    assert "create table if not exists outbox_events" in normalized
    assert normalized.count("partition by hash (tenant_id)") == 2
    assert normalized.count("partition of async_jobs") == 8
    assert normalized.count("partition of outbox_events") == 8
    assert "primary key (tenant_id, id)" in normalized
    assert "unique (tenant_id, idempotency_key)" in normalized
    assert "where status in ('queued', 'retry-wait')" in normalized
    assert "where status = 'leased'" in normalized
    assert "where status = 'dead-letter'" in normalized
    assert "payload jsonb not null" in normalized
    assert "octet_length(payload::text) <= 65536" in normalized
    assert "payload_object_key varchar(512) not null" in normalized
    assert "payload_size_bytes between 0 and 10737418240" in normalized
    assert "idx_audit_events_async_processing" in normalized
    assert "target_type in ('async-job', 'outbox-event')" in normalized

    statements = PostgreSQLStatementSplitter.split(sql)
    assert len(statements) >= 10


def test_async_processing_migration_precedes_current_catalog_entry() -> None:
    migrations = sorted((ROOT / "installers/migrations/postgresql").glob("*.sql"))
    names = [migration.name for migration in migrations]

    assert names[-2:] == [
        "0054_async_outbox_workers.sql",
        "0055_kubernetes_topology_inventory.sql",
    ]
    assert len(migrations) == 55
