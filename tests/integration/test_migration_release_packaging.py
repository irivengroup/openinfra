from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from openinfra.quality.migration_packaging import (
    MigrationCatalog,
    MigrationCatalogArchiveBuilder,
    MigrationCatalogArchiveVerifier,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DATE_EPOCH = 1_700_000_000


def test_release_catalogue_exposes_every_postgresql_and_oracle_migration(
    tmp_path: Path,
) -> None:
    snapshot = MigrationCatalog().load(PROJECT_ROOT, SOURCE_DATE_EPOCH)

    assert snapshot.count == 60
    assert snapshot.first_version == "0001"
    assert snapshot.last_version == "0060"
    assert [item.filename for item in snapshot.postgresql] == [
        item.filename for item in snapshot.oracle
    ]
    assert len({item.sha256 for item in snapshot.postgresql}) == 60
    assert len({item.sha256 for item in snapshot.oracle}) == 60

    archive, built_snapshot = MigrationCatalogArchiveBuilder().build(
        PROJECT_ROOT, tmp_path, SOURCE_DATE_EPOCH
    )
    assert built_snapshot == snapshot
    MigrationCatalogArchiveVerifier().verify(archive, snapshot)

    with zipfile.ZipFile(archive) as packaged:
        members = [name for name in packaged.namelist() if not name.endswith("/")]
        assert len(members) == 123
        manifest_name = next(
            name for name in members if name.endswith("MIGRATIONS-MANIFEST.json")
        )
        manifest = json.loads(packaged.read(manifest_name))
        assert manifest["count_per_database"] == 60
        assert manifest["parity"] is True
        assert manifest["last_version"] == "0060"


def test_release_packaging_workflow_blocks_incomplete_migration_catalogues() -> None:
    workflow = (PROJECT_ROOT / ".github/workflows/release-packaging.yml").read_text(
        encoding="utf-8"
    )
    quality_gate = (PROJECT_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    verifier = (PROJECT_ROOT / "scripts/verify_artifact.py").read_text(encoding="utf-8")

    for fragment in (
        "Verify complete standalone migration catalogue",
        "build_migration_catalog.py",
        "openinfra-${version}-migrations.zip",
        "snapshot.count == 60",
        'snapshot.first_version == "0001"',
        'snapshot.last_version == "0060"',
        "MigrationCatalogArchiveVerifier",
    ):
        assert fragment in workflow
    for fragment in (
        "src/openinfra/quality/migration_packaging.py",
        "scripts/build_migration_catalog.py",
        '"migration-catalog-archive"',
    ):
        assert fragment in quality_gate
    for fragment in (
        "class MigrationArtifactParityVerifier",
        "verify_wheel",
        "verify_sdist",
        "migration checksum mismatch",
    ):
        assert fragment in verifier


def test_oracle_manifest_hashes_cover_the_complete_source_catalogue() -> None:
    oracle_root = PROJECT_ROOT / "installers/migrations/oracle"
    postgresql_root = PROJECT_ROOT / "installers/migrations/postgresql"
    manifest = json.loads((oracle_root / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["count"] == 60
    assert len(manifest["migrations"]) == 60
    for item in manifest["migrations"]:
        filename = item["filename"]
        assert item["source_sha256"] == hashlib.sha256(
            (postgresql_root / filename).read_bytes()
        ).hexdigest()
        assert item["oracle_sha256"] == hashlib.sha256(
            (oracle_root / filename).read_bytes()
        ).hexdigest()
