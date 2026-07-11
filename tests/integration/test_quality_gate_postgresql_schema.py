from __future__ import annotations

from pathlib import Path

import pytest
from scripts.quality_gate import PostgreSQLMigrationSchemaGuard, QualityGateError


def _migration_root(tmp_path: Path) -> Path:
    root = tmp_path / "installers/migrations/postgresql"
    root.mkdir(parents=True)
    return root


def test_quality_gate_allows_occurred_at_on_domain_event_outbox(tmp_path: Path) -> None:
    migrations = _migration_root(tmp_path)
    (migrations / "0001.sql").write_text(
        "CREATE TABLE audit_events (created_at timestamptz NOT NULL);\n"
        "CREATE TABLE field_event_outbox (occurred_at timestamptz NOT NULL);\n",
        encoding="utf-8",
    )

    PostgreSQLMigrationSchemaGuard(tmp_path).assert_audit_indexes_use_created_at()


def test_quality_gate_rejects_occurred_at_on_audit_events(tmp_path: Path) -> None:
    migrations = _migration_root(tmp_path)
    (migrations / "0001.sql").write_text(
        "CREATE INDEX bad_audit_index ON audit_events (tenant_id, occurred_at);\n",
        encoding="utf-8",
    )

    with pytest.raises(QualityGateError, match=r"audit_events\.occurred_at"):
        PostgreSQLMigrationSchemaGuard(tmp_path).assert_audit_indexes_use_created_at()
