from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from openinfra.quality.migration_packaging import (
    MigrationCatalog,
    MigrationCatalogArchiveBuilder,
    MigrationCatalogArchiveVerifier,
    MigrationFileRecord,
    MigrationPackagingError,
)


def _write_catalog(root: Path, names: tuple[str, ...] = ("0001_bootstrap.sql", "0002_next.sql")) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    postgresql_root = root / "installers/migrations/postgresql"
    oracle_root = root / "installers/migrations/oracle"
    postgresql_root.mkdir(parents=True, exist_ok=True)
    oracle_root.mkdir(parents=True, exist_ok=True)
    migrations: list[dict[str, object]] = []
    for name in names:
        version = name.split("_", 1)[0]
        source_payload = f"-- PostgreSQL {name}\nSELECT {int(version)};\n".encode()
        oracle_payload = f"-- Oracle {name}\nSELECT {int(version)} FROM dual;\n".encode()
        (postgresql_root / name).write_bytes(source_payload)
        (oracle_root / name).write_bytes(oracle_payload)
        migrations.append(
            {
                "filename": name,
                "version": version,
                "source_sha256": hashlib.sha256(source_payload).hexdigest(),
                "oracle_sha256": hashlib.sha256(oracle_payload).hexdigest(),
                "statement_count": 1,
            }
        )
    (oracle_root / "manifest.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "source": "postgresql",
                "target": "oracle",
                "count": len(names),
                "migrations": migrations,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _rewrite_zip(source: Path, destination: Path, transform: object) -> None:
    callback = transform
    with zipfile.ZipFile(source) as archive:
        entries = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    assert callable(callback)
    updated = callback(entries)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(updated.items()):
            archive.writestr(name, payload)


class TestMigrationCatalog:
    def test_loads_complete_catalogue_and_serializes_manifest(self, tmp_path: Path) -> None:
        _write_catalog(tmp_path)

        snapshot = MigrationCatalog().load(tmp_path, 1_700_000_000)
        payload = snapshot.as_dict()

        assert snapshot.release_version == "9.9.9"
        assert snapshot.count == 2
        assert snapshot.first_version == "0001"
        assert snapshot.last_version == "0002"
        assert payload["parity"] is True
        assert payload["count_per_database"] == 2
        assert payload["generated_at"] == "2023-11-14T22:13:20Z"
        assert payload["catalogs"]["postgresql"]["count"] == 2
        assert payload["catalogs"]["oracle"]["count"] == 2
        assert len(snapshot.oracle_manifest_sha256) == 64
        assert snapshot.postgresql[0].as_dict()["database"] == "postgresql"

    @pytest.mark.parametrize("epoch", [0, -1])
    def test_rejects_non_positive_epoch(self, tmp_path: Path, epoch: int) -> None:
        _write_catalog(tmp_path)
        with pytest.raises(MigrationPackagingError, match="positive Unix timestamp"):
            MigrationCatalog().load(tmp_path, epoch)

    def test_rejects_missing_and_empty_version(self, tmp_path: Path) -> None:
        with pytest.raises(MigrationPackagingError, match="VERSION file is missing"):
            MigrationCatalog().load(tmp_path, 1)
        (tmp_path / "VERSION").write_text("\n", encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="VERSION file is empty"):
            MigrationCatalog().load(tmp_path, 1)

    def test_rejects_missing_empty_invalid_and_gapped_catalogues(self, tmp_path: Path) -> None:
        (tmp_path / "VERSION").write_text("1\n", encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="postgresql migration directory"):
            MigrationCatalog().load(tmp_path, 1)
        (tmp_path / "installers/migrations/postgresql").mkdir(parents=True)
        with pytest.raises(MigrationPackagingError, match="catalogue is empty"):
            MigrationCatalog().load(tmp_path, 1)

        root = tmp_path / "invalid"
        _write_catalog(root)
        (root / "installers/migrations/postgresql/not-valid.sql").write_text("SELECT 1;")
        with pytest.raises(MigrationPackagingError, match="invalid migration filenames"):
            MigrationCatalog().load(root, 1)

        root = tmp_path / "gap"
        _write_catalog(root, ("0001_bootstrap.sql", "0003_gap.sql"))
        with pytest.raises(MigrationPackagingError, match="not contiguous"):
            MigrationCatalog().load(root, 1)

    def test_rejects_invalid_record_name_and_catalogue_parity(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.sql"
        path.write_text("SELECT 1;", encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="invalid migration filename"):
            MigrationFileRecord.from_path("postgresql", path)

        duplicate_one = MigrationFileRecord(
            "postgresql", "0001", "0001_same.sql", 1, "0" * 64
        )
        duplicate_two = MigrationFileRecord(
            "postgresql", "0002", "0001_same.sql", 1, "1" * 64
        )
        with pytest.raises(MigrationPackagingError, match="filenames are duplicated"):
            MigrationCatalog._validate_sequence((duplicate_one, duplicate_two))

        _write_catalog(tmp_path / "parity")
        (tmp_path / "parity/installers/migrations/oracle/0002_next.sql").unlink()
        with pytest.raises(MigrationPackagingError, match="parity failed"):
            MigrationCatalog().load(tmp_path / "parity", 1)

    def test_rejects_oracle_manifest_structural_errors(self, tmp_path: Path) -> None:
        root = tmp_path / "catalog"
        _write_catalog(root)
        manifest = root / "installers/migrations/oracle/manifest.json"

        manifest.unlink()
        with pytest.raises(MigrationPackagingError, match="manifest is missing"):
            MigrationCatalog().load(root, 1)

        _write_catalog(root)
        manifest.write_text("{", encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="invalid JSON"):
            MigrationCatalog().load(root, 1)

        manifest.write_text("[]", encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="must be a JSON object"):
            MigrationCatalog().load(root, 1)

        manifest.write_text('{"count": 2, "migrations": {}}', encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="must be an array"):
            MigrationCatalog().load(root, 1)

        manifest.write_text('{"count": 1, "migrations": []}', encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="count does not match"):
            MigrationCatalog().load(root, 1)

    def test_rejects_oracle_manifest_entry_errors(self, tmp_path: Path) -> None:
        root = tmp_path / "catalog"
        _write_catalog(root)
        manifest = root / "installers/migrations/oracle/manifest.json"
        original = json.loads(manifest.read_text(encoding="utf-8"))

        payload = dict(original)
        payload["migrations"] = ["bad", original["migrations"][1]]
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="entries must be JSON objects"):
            MigrationCatalog().load(root, 1)

        payload = dict(original)
        payload["migrations"] = [dict(original["migrations"][0]), dict(original["migrations"][1])]
        payload["migrations"][0]["filename"] = "9999_unknown.sql"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="unknown file"):
            MigrationCatalog().load(root, 1)

        payload = dict(original)
        payload["migrations"] = [dict(item) for item in original["migrations"]]
        payload["migrations"][0]["source_sha256"] = "0" * 64
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="entry is inconsistent"):
            MigrationCatalog().load(root, 1)

        payload = dict(original)
        payload["migrations"] = list(reversed(original["migrations"]))
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(MigrationPackagingError, match="order or membership"):
            MigrationCatalog().load(root, 1)


class TestMigrationCatalogArchive:
    def test_builds_reproducible_complete_archive(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        _write_catalog(project)
        first, snapshot = MigrationCatalogArchiveBuilder().build(
            project, tmp_path / "first", 1_700_000_000
        )
        second, second_snapshot = MigrationCatalogArchiveBuilder().build(
            project, tmp_path / "second", 1_700_000_000
        )

        assert first.read_bytes() == second.read_bytes()
        assert snapshot == second_snapshot
        MigrationCatalogArchiveVerifier().verify(first, snapshot)
        with zipfile.ZipFile(first) as archive:
            names = set(archive.namelist())
            prefix = "openinfra-9.9.9-migrations"
            assert f"{prefix}/README.md" in names
            assert f"{prefix}/MIGRATIONS-MANIFEST.json" in names
            assert f"{prefix}/postgresql/0002_next.sql" in names
            assert f"{prefix}/oracle/0002_next.sql" in names
            assert len(names) == 7

        assert MigrationCatalogArchiveBuilder._zip_timestamp(1) == (1980, 1, 1, 0, 0, 0)
        assert "2 migrations" in MigrationCatalogArchiveBuilder._readme(snapshot)

    def test_verifier_rejects_missing_unexpected_and_manifest_mismatch(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        _write_catalog(project)
        archive, snapshot = MigrationCatalogArchiveBuilder().build(project, tmp_path / "out", 1)

        missing = tmp_path / "missing.zip"
        _rewrite_zip(
            archive,
            missing,
            lambda entries: {
                name: payload
                for name, payload in entries.items()
                if not name.endswith("postgresql/0002_next.sql")
            },
        )
        with pytest.raises(MigrationPackagingError, match="membership is invalid"):
            MigrationCatalogArchiveVerifier().verify(missing, snapshot)

        unexpected = tmp_path / "unexpected.zip"
        _rewrite_zip(
            archive,
            unexpected,
            lambda entries: {**entries, "unexpected.txt": b"bad"},
        )
        with pytest.raises(MigrationPackagingError, match="membership is invalid"):
            MigrationCatalogArchiveVerifier().verify(unexpected, snapshot)

        manifest = tmp_path / "manifest.zip"
        def alter_manifest(entries: dict[str, bytes]) -> dict[str, bytes]:
            name = next(item for item in entries if item.endswith("MIGRATIONS-MANIFEST.json"))
            payload = json.loads(entries[name])
            payload["count_per_database"] = 99
            entries[name] = json.dumps(payload).encode()
            return entries
        _rewrite_zip(archive, manifest, alter_manifest)
        with pytest.raises(MigrationPackagingError, match="manifest does not match"):
            MigrationCatalogArchiveVerifier().verify(manifest, snapshot)

    def test_verifier_rejects_payload_and_oracle_manifest_corruption(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        _write_catalog(project)
        archive, snapshot = MigrationCatalogArchiveBuilder().build(project, tmp_path / "out", 1)

        payload_archive = tmp_path / "payload.zip"
        def alter_payload(entries: dict[str, bytes]) -> dict[str, bytes]:
            name = next(item for item in entries if item.endswith("postgresql/0001_bootstrap.sql"))
            entries[name] = b"tampered"
            return entries
        _rewrite_zip(archive, payload_archive, alter_payload)
        with pytest.raises(MigrationPackagingError, match="size mismatch"):
            MigrationCatalogArchiveVerifier().verify(payload_archive, snapshot)

        same_size_archive = tmp_path / "checksum.zip"
        def alter_same_size(entries: dict[str, bytes]) -> dict[str, bytes]:
            name = next(item for item in entries if item.endswith("oracle/0001_bootstrap.sql"))
            entries[name] = b"x" * len(entries[name])
            return entries
        _rewrite_zip(archive, same_size_archive, alter_same_size)
        with pytest.raises(MigrationPackagingError, match="checksum mismatch"):
            MigrationCatalogArchiveVerifier().verify(same_size_archive, snapshot)

        oracle_manifest_archive = tmp_path / "oracle-manifest.zip"
        def alter_oracle_manifest(entries: dict[str, bytes]) -> dict[str, bytes]:
            name = next(item for item in entries if item.endswith("oracle/manifest.json"))
            entries[name] = b"{}"
            return entries
        _rewrite_zip(archive, oracle_manifest_archive, alter_oracle_manifest)
        with pytest.raises(MigrationPackagingError, match="Oracle manifest checksum"):
            MigrationCatalogArchiveVerifier().verify(oracle_manifest_archive, snapshot)

    def test_builder_replaces_stale_temporary_and_cleans_failed_build(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "project"
        _write_catalog(project)
        output = tmp_path / "out"
        output.mkdir()
        monkeypatch.setattr("openinfra.quality.migration_packaging.os.getpid", lambda: 4242)
        temporary = output / ".openinfra-9.9.9-migrations.zip.tmp-4242"
        temporary.write_bytes(b"stale")

        archive, _ = MigrationCatalogArchiveBuilder().build(project, output, 1)
        assert archive.is_file()
        assert not temporary.exists()

        original = zipfile.ZipFile.writestr

        def failing_writestr(self: zipfile.ZipFile, *args: object, **kwargs: object) -> None:
            del self, args, kwargs
            raise OSError("synthetic write failure")

        monkeypatch.setattr(zipfile.ZipFile, "writestr", failing_writestr)
        with pytest.raises(OSError, match="synthetic write failure"):
            MigrationCatalogArchiveBuilder().build(project, tmp_path / "failed", 1)
        failed_temporary = tmp_path / "failed/.openinfra-9.9.9-migrations.zip.tmp-4242"
        assert not failed_temporary.exists()
        monkeypatch.setattr(zipfile.ZipFile, "writestr", original)

    def test_verifier_rejects_invalid_json_manifest(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        _write_catalog(project)
        archive, snapshot = MigrationCatalogArchiveBuilder().build(project, tmp_path / "out", 1)
        invalid = tmp_path / "invalid-json.zip"

        def alter(entries: dict[str, bytes]) -> dict[str, bytes]:
            name = next(item for item in entries if item.endswith("MIGRATIONS-MANIFEST.json"))
            entries[name] = b"{"
            return entries

        _rewrite_zip(archive, invalid, alter)
        with pytest.raises(MigrationPackagingError, match="manifest is invalid JSON"):
            MigrationCatalogArchiveVerifier().verify(invalid, snapshot)

    def test_verifier_rejects_missing_archive(self, tmp_path: Path) -> None:
        project = tmp_path / "project"
        _write_catalog(project)
        snapshot = MigrationCatalog().load(project, 1)
        with pytest.raises(MigrationPackagingError, match="does not exist"):
            MigrationCatalogArchiveVerifier().verify(tmp_path / "missing.zip", snapshot)
