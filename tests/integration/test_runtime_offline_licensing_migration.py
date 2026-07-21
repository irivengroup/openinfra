from __future__ import annotations

import json
import re
from pathlib import Path

POSTGRESQL_ROOT = Path("installers/migrations/postgresql")
ORACLE_ROOT = Path("installers/migrations/oracle")
MIGRATION_NAME = "0059_runtime_offline_licensing.sql"


def test_runtime_license_migration_is_additive_and_partitioned_for_postgresql() -> None:
    sql = (POSTGRESQL_ROOT / MIGRATION_NAME).read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS runtime_license_state" in sql
    assert "identity jsonb NOT NULL" in sql
    assert "entitlement jsonb" in sql
    assert "PRIMARY KEY (state_key)" in sql
    assert "PARTITION BY HASH (state_key)" in sql
    assert len(re.findall(r"PARTITION OF runtime_license_state", sql)) == 4
    assert "idx_runtime_license_state_updated" in sql
    assert "idx_audit_events_runtime_license" in sql
    assert not re.search(r"\b(?:DROP|TRUNCATE)\b", sql, re.IGNORECASE)


def test_runtime_license_migration_is_generated_and_json_checked_for_oracle() -> None:
    sql = (ORACLE_ROOT / MIGRATION_NAME).read_text(encoding="utf-8")
    manifest = json.loads((ORACLE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in manifest["migrations"] if item["filename"] == MIGRATION_NAME)

    assert "PARTITION BY HASH (state_key) PARTITIONS 4" in sql
    assert "CHECK (identity IS JSON)" in sql
    assert "CHECK (entitlement IS JSON)" in sql
    assert "idx_runtime_license_state_updated" in sql
    assert entry["source_sha256"]
    assert entry["oracle_sha256"]
    assert entry["statement_count"] == 3
