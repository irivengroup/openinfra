from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_oracle_migrations import (  # noqa: E402
    ConversionError,
    _convert_index,
    convert_migration,
    generate_catalog,
    validate_catalog_structure,
    validate_payload,
)


class TestOracleMigrationGeneration:
    def test_complete_catalog_is_deterministic_and_structurally_safe(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = root / "installers/migrations/postgresql"
        target = root / "installers/migrations/oracle"

        converted = generate_catalog(source, target, check=True)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))

        assert len(converted) == 58
        assert manifest["count"] == 58
        assert converted[0].name == "0001_bootstrap.sql"
        assert converted[-1].name == "0058_oracle_document_shards.sql"
        assert all(item.source_sha256 and item.oracle_sha256 for item in converted)
        assert "VARCHAR2(64 CHAR))" not in converted[0].output.split("UNIQUE", 1)[1]
        assert "CREATE UNIQUE INDEX uq_rag_documents_active_source" in converted[48].output
        assert "CASE WHEN active = 1 THEN tenant_id END" in converted[48].output
        assert "RETURNING VARCHAR2(64 CHAR)" in converted[26].output

    def test_generation_detects_target_drift(self, tmp_path: Path) -> None:
        root = Path(__file__).resolve().parents[2]
        source = root / "installers/migrations/postgresql"
        target = tmp_path / "oracle"
        generate_catalog(source, target, check=False)
        (target / "0001_bootstrap.sql").write_text("changed\n", encoding="utf-8")

        with pytest.raises(ConversionError, match="migration drift"):
            generate_catalog(source, target, check=True)

        generate_catalog(source, target, check=False)
        manifest = target / "manifest.json"
        manifest.write_text("{}\n", encoding="utf-8")
        with pytest.raises(ConversionError, match="manifest drift"):
            generate_catalog(source, target, check=True)

    def test_generation_rejects_non_contiguous_and_unsupported_sources(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "postgresql"
        target = tmp_path / "oracle"
        source.mkdir()
        (source / "0002_gap.sql").write_text(
            "CREATE TABLE IF NOT EXISTS sample (id uuid PRIMARY KEY);\n",
            encoding="utf-8",
        )
        with pytest.raises(ConversionError, match="not contiguous"):
            generate_catalog(source, target, check=False)

        shutil.rmtree(source)
        source.mkdir()
        (source / "0001_invalid.sql").write_text("VACUUM sample;\n", encoding="utf-8")
        with pytest.raises(ConversionError, match="unsupported PostgreSQL statement"):
            generate_catalog(source, target, check=False)

    def test_conversion_removes_postgresql_validation_and_restrict_syntax(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path / "0001_sample.sql"
        source.write_text(
            """
            CREATE TABLE IF NOT EXISTS parent (id uuid PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS child (
                id uuid PRIMARY KEY,
                parent_id uuid REFERENCES parent(id) ON DELETE RESTRICT,
                value text NOT NULL,
                CONSTRAINT ck_child_value CHECK (btrim(value) <> '') NOT VALID
            );
            """,
            encoding="utf-8",
        )

        migration = convert_migration(source)

        assert "NOT VALID" not in migration.output
        assert "ON DELETE RESTRICT" not in migration.output
        assert "TRIM(value)" in migration.output

    def test_partial_unique_index_and_payload_guards(self) -> None:
        assert _convert_index(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_sample ON sample "
            "(tenant_id, source_ref) WHERE active;"
        ) == (
            "CREATE UNIQUE INDEX uq_sample ON sample "
            "(CASE WHEN active = 1 THEN tenant_id END, "
            "CASE WHEN active = 1 THEN source_ref END)",
        )
        with pytest.raises(ConversionError, match="non-column expression"):
            _convert_index(
                "CREATE UNIQUE INDEX uq_sample ON sample (lower(source_ref)) WHERE active;"
            )
        with pytest.raises(ConversionError, match="NOT VALID"):
            validate_payload("invalid.sql", "ALTER TABLE sample ADD CHECK (id > 0) NOT VALID;\n")

    def test_catalog_structure_rejects_lob_oversize_and_unknown_expression(self) -> None:
        def item(output: str):
            from generate_oracle_migrations import ConvertedMigration

            return ConvertedMigration("0001_x.sql", "a", "b", 1, output)

        with pytest.raises(ConversionError, match="LOB"):
            validate_catalog_structure(
                [item("CREATE TABLE sample (payload CLOB, UNIQUE (payload));")]
            )
        with pytest.raises(ConversionError, match="exceeds 6000"):
            validate_catalog_structure(
                [
                    item(
                        "CREATE TABLE sample (a VARCHAR2(1000 CHAR), "
                        "b VARCHAR2(1000 CHAR)); CREATE INDEX idx_sample ON sample (a, b);"
                    )
                ]
            )
        with pytest.raises(ConversionError, match="unsupported Oracle index expression"):
            validate_catalog_structure(
                [
                    item(
                        "CREATE TABLE sample (a VARCHAR2(64 CHAR)); "
                        "CREATE INDEX idx_sample ON sample (LOWER(a));"
                    )
                ]
            )
