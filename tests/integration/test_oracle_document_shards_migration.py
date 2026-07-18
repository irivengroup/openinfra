from __future__ import annotations

import json
import re
from pathlib import Path

POSTGRESQL_ROOT = Path("installers/migrations/postgresql")
ORACLE_ROOT = Path("installers/migrations/oracle")
MIGRATION_NAME = "0058_oracle_document_shards.sql"


def test_oracle_document_shards_migration_is_present_in_both_catalogs() -> None:
    postgresql_names = tuple(
        path.name for path in sorted(POSTGRESQL_ROOT.glob("[0-9]" * 4 + "_*.sql"))
    )
    oracle_names = tuple(path.name for path in sorted(ORACLE_ROOT.glob("[0-9]" * 4 + "_*.sql")))

    assert len(postgresql_names) == 58
    assert postgresql_names == oracle_names
    assert postgresql_names[-1] == MIGRATION_NAME


def test_postgresql_document_shards_use_hash_partitioning_and_partition_safe_key() -> None:
    sql = (POSTGRESQL_ROOT / MIGRATION_NAME).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS openinfra_document_shards" in sql
    assert "PRIMARY KEY (shard_key)" in sql
    assert "PARTITION BY HASH (shard_key)" in sql
    assert len(re.findall(r"PARTITION OF openinfra_document_shards", sql)) == 8
    assert "idx_openinfra_document_shards_updated" in sql
    assert "idx_audit_events_oracle_shards" in sql
    assert not re.search(r"\b(?:DROP|TRUNCATE)\b", sql, re.IGNORECASE)


def test_oracle_document_shards_are_json_checked_and_manifest_pinned() -> None:
    sql_path = ORACLE_ROOT / MIGRATION_NAME
    sql = sql_path.read_text(encoding="utf-8")
    manifest = json.loads((ORACLE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["migrations"]
    final_entry = entries[-1]

    assert "PARTITION BY HASH (shard_key) PARTITIONS 8" in sql
    assert "CHECK (payload IS JSON)" in sql
    assert "shard_key VARCHAR2(128 CHAR)" in sql
    assert not re.search(r"\b(?:DROP|TRUNCATE)\b", sql, re.IGNORECASE)
    assert len(entries) == 58
    assert final_entry["filename"] == MIGRATION_NAME
    assert final_entry["source_sha256"]
    assert final_entry["oracle_sha256"]
