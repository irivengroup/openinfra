from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final, Iterable


class MigrationPackagingError(Exception):
    """Raised when a migration catalogue or archive is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class MigrationFileRecord:
    database: str
    version: str
    filename: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_path(cls, database: str, path: Path) -> MigrationFileRecord:
        matched = MigrationCatalog.MIGRATION_NAME.fullmatch(path.name)
        if matched is None:
            raise MigrationPackagingError(f"invalid migration filename: {path.name}")
        payload = path.read_bytes()
        return cls(
            database=database,
            version=matched.group("version"),
            filename=path.name,
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "database": self.database,
            "version": self.version,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class MigrationCatalogSnapshot:
    release_version: str
    source_date_epoch: int
    postgresql: tuple[MigrationFileRecord, ...]
    oracle: tuple[MigrationFileRecord, ...]
    oracle_manifest_sha256: str

    @property
    def count(self) -> int:
        return len(self.postgresql)

    @property
    def first_version(self) -> str:
        return self.postgresql[0].version

    @property
    def last_version(self) -> str:
        return self.postgresql[-1].version

    def as_dict(self) -> dict[str, object]:
        generated_at = (
            datetime.fromtimestamp(self.source_date_epoch, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return {
            "schema_version": 1,
            "release_version": self.release_version,
            "generated_at": generated_at,
            "source_date_epoch": self.source_date_epoch,
            "parity": True,
            "count_per_database": self.count,
            "first_version": self.first_version,
            "last_version": self.last_version,
            "catalogs": {
                "postgresql": {
                    "count": len(self.postgresql),
                    "files": [item.as_dict() for item in self.postgresql],
                },
                "oracle": {
                    "count": len(self.oracle),
                    "manifest_sha256": self.oracle_manifest_sha256,
                    "files": [item.as_dict() for item in self.oracle],
                },
            },
        }


class MigrationCatalog:
    MIGRATION_NAME: Final[re.Pattern[str]] = re.compile(
        r"(?P<version>[0-9]{4})_[a-z0-9][a-z0-9_]*\.sql"
    )
    DATABASES: Final[tuple[str, ...]] = ("postgresql", "oracle")

    def load(self, project_root: Path, source_date_epoch: int) -> MigrationCatalogSnapshot:
        root = project_root.resolve()
        if source_date_epoch <= 0:
            raise MigrationPackagingError(
                "migration catalogue SOURCE_DATE_EPOCH must be a positive Unix timestamp"
            )
        release_version = self._release_version(root)
        postgresql = self._records(root, "postgresql")
        oracle = self._records(root, "oracle")
        self._validate_sequence(postgresql)
        self._validate_sequence(oracle)
        self._validate_parity(postgresql, oracle)
        manifest_path = root / "installers/migrations/oracle/manifest.json"
        manifest_sha256 = self._validate_oracle_manifest(
            manifest_path, postgresql, oracle
        )
        return MigrationCatalogSnapshot(
            release_version=release_version,
            source_date_epoch=source_date_epoch,
            postgresql=postgresql,
            oracle=oracle,
            oracle_manifest_sha256=manifest_sha256,
        )

    @classmethod
    def _release_version(cls, project_root: Path) -> str:
        path = project_root / "VERSION"
        if not path.is_file():
            raise MigrationPackagingError(f"release VERSION file is missing: {path}")
        version = path.read_text(encoding="utf-8").strip()
        if not version:
            raise MigrationPackagingError("release VERSION file is empty")
        return version

    @classmethod
    def _records(
        cls, project_root: Path, database: str
    ) -> tuple[MigrationFileRecord, ...]:
        root = project_root / "installers/migrations" / database
        if not root.is_dir():
            raise MigrationPackagingError(
                f"{database} migration directory is missing: {root}"
            )
        unexpected = sorted(
            path.name
            for path in root.iterdir()
            if path.is_file()
            and path.suffix == ".sql"
            and cls.MIGRATION_NAME.fullmatch(path.name) is None
        )
        if unexpected:
            raise MigrationPackagingError(
                f"{database} contains invalid migration filenames: "
                + ", ".join(unexpected)
            )
        records = tuple(
            MigrationFileRecord.from_path(database, path)
            for path in sorted(root.glob("*.sql"))
        )
        if not records:
            raise MigrationPackagingError(f"{database} migration catalogue is empty")
        return records

    @classmethod
    def _validate_sequence(cls, records: tuple[MigrationFileRecord, ...]) -> None:
        observed = [int(item.version) for item in records]
        expected = list(range(1, len(records) + 1))
        if observed != expected:
            database = records[0].database
            raise MigrationPackagingError(
                f"{database} migration versions are not contiguous from 0001: "
                f"observed={observed}"
            )
        filenames = [item.filename for item in records]
        if len(set(filenames)) != len(filenames):
            raise MigrationPackagingError(
                f"{records[0].database} migration filenames are duplicated"
            )

    @classmethod
    def _validate_parity(
        cls,
        postgresql: tuple[MigrationFileRecord, ...],
        oracle: tuple[MigrationFileRecord, ...],
    ) -> None:
        postgresql_names = [item.filename for item in postgresql]
        oracle_names = [item.filename for item in oracle]
        if postgresql_names != oracle_names:
            missing_oracle = sorted(set(postgresql_names) - set(oracle_names))
            missing_postgresql = sorted(set(oracle_names) - set(postgresql_names))
            raise MigrationPackagingError(
                "PostgreSQL/Oracle migration parity failed: "
                f"missing_oracle={missing_oracle}, "
                f"missing_postgresql={missing_postgresql}"
            )

    @classmethod
    def _validate_oracle_manifest(
        cls,
        manifest_path: Path,
        postgresql: tuple[MigrationFileRecord, ...],
        oracle: tuple[MigrationFileRecord, ...],
    ) -> str:
        if not manifest_path.is_file():
            raise MigrationPackagingError(
                f"Oracle migration manifest is missing: {manifest_path}"
            )
        payload_bytes = manifest_path.read_bytes()
        try:
            payload = json.loads(payload_bytes)
        except json.JSONDecodeError as exc:
            raise MigrationPackagingError("Oracle migration manifest is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise MigrationPackagingError("Oracle migration manifest must be a JSON object")
        items = payload.get("migrations")
        if not isinstance(items, list):
            raise MigrationPackagingError(
                "Oracle migration manifest migrations must be an array"
            )
        if payload.get("count") != len(oracle) or len(items) != len(oracle):
            raise MigrationPackagingError(
                "Oracle migration manifest count does not match the migration catalogue"
            )
        source_by_name = {item.filename: item for item in postgresql}
        oracle_by_name = {item.filename: item for item in oracle}
        observed_names: list[str] = []
        for raw in items:
            if not isinstance(raw, dict):
                raise MigrationPackagingError(
                    "Oracle migration manifest entries must be JSON objects"
                )
            filename = str(raw.get("filename", ""))
            observed_names.append(filename)
            source = source_by_name.get(filename)
            target = oracle_by_name.get(filename)
            if source is None or target is None:
                raise MigrationPackagingError(
                    f"Oracle migration manifest references an unknown file: {filename}"
                )
            expected = {
                "version": target.version,
                "source_sha256": source.sha256,
                "oracle_sha256": target.sha256,
            }
            mismatches = [
                key for key, value in expected.items() if raw.get(key) != value
            ]
            if mismatches:
                raise MigrationPackagingError(
                    f"Oracle migration manifest entry is inconsistent for {filename}: "
                    + ", ".join(sorted(mismatches))
                )
        expected_names = [item.filename for item in oracle]
        if observed_names != expected_names:
            raise MigrationPackagingError(
                "Oracle migration manifest order or membership does not match the catalogue"
            )
        return hashlib.sha256(payload_bytes).hexdigest()


class MigrationCatalogArchiveBuilder:
    ARCHIVE_SUFFIX: Final[str] = "-migrations.zip"
    README_NAME: Final[str] = "README.md"
    MANIFEST_NAME: Final[str] = "MIGRATIONS-MANIFEST.json"

    def __init__(self, catalog: MigrationCatalog | None = None) -> None:
        self._catalog = catalog or MigrationCatalog()

    def build(
        self, project_root: Path, output_dir: Path, source_date_epoch: int
    ) -> tuple[Path, MigrationCatalogSnapshot]:
        root = project_root.resolve()
        output = output_dir.resolve()
        snapshot = self._catalog.load(root, source_date_epoch)
        output.mkdir(parents=True, exist_ok=True)
        destination = output / (
            f"openinfra-{snapshot.release_version}{self.ARCHIVE_SUFFIX}"
        )
        temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
        if temporary.exists():
            temporary.unlink()
        prefix = PurePosixPath(f"openinfra-{snapshot.release_version}-migrations")
        timestamp = self._zip_timestamp(source_date_epoch)
        entries: list[tuple[PurePosixPath, bytes]] = [
            (prefix / self.README_NAME, self._readme(snapshot).encode("utf-8")),
            (
                prefix / self.MANIFEST_NAME,
                (json.dumps(snapshot.as_dict(), indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
            ),
        ]
        for database, records in (
            ("postgresql", snapshot.postgresql),
            ("oracle", snapshot.oracle),
        ):
            source_root = root / "installers/migrations" / database
            entries.extend(
                (prefix / database / item.filename, (source_root / item.filename).read_bytes())
                for item in records
            )
        oracle_manifest = root / "installers/migrations/oracle/manifest.json"
        entries.append(
            (prefix / "oracle" / "manifest.json", oracle_manifest.read_bytes())
        )
        try:
            with zipfile.ZipFile(
                temporary,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as archive:
                for relative, payload in sorted(entries, key=lambda item: item[0].as_posix()):
                    info = zipfile.ZipInfo(relative.as_posix(), date_time=timestamp)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, payload)
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        MigrationCatalogArchiveVerifier().verify(destination, snapshot)
        return destination, snapshot

    @classmethod
    def _zip_timestamp(cls, source_date_epoch: int) -> tuple[int, int, int, int, int, int]:
        value = datetime.fromtimestamp(source_date_epoch, tz=UTC)
        if value.year < 1980:
            value = datetime(1980, 1, 1, tzinfo=UTC)
        return (value.year, value.month, value.day, value.hour, value.minute, value.second)

    @classmethod
    def _readme(cls, snapshot: MigrationCatalogSnapshot) -> str:
        return (
            f"# OpenInfra {snapshot.release_version} — catalogue de migrations\n\n"
            "Cette archive autonome contient l’intégralité des migrations versionnées "
            "PostgreSQL et Oracle de la release.\n\n"
            f"- PostgreSQL : {len(snapshot.postgresql)} migrations\n"
            f"- Oracle : {len(snapshot.oracle)} migrations\n"
            f"- Plage : {snapshot.first_version} à {snapshot.last_version}\n"
            "- Parité des noms : validée\n"
            "- Intégrité : SHA-256 par fichier dans MIGRATIONS-MANIFEST.json\n"
        )


class MigrationCatalogArchiveVerifier:
    def verify(self, archive_path: Path, snapshot: MigrationCatalogSnapshot) -> None:
        if not archive_path.is_file():
            raise MigrationPackagingError(
                f"migration catalogue archive does not exist: {archive_path}"
            )
        prefix = PurePosixPath(f"openinfra-{snapshot.release_version}-migrations")
        expected_payloads: dict[str, bytes | None] = {
            (prefix / MigrationCatalogArchiveBuilder.README_NAME).as_posix(): None,
            (prefix / MigrationCatalogArchiveBuilder.MANIFEST_NAME).as_posix(): None,
            (prefix / "oracle" / "manifest.json").as_posix(): None,
        }
        for database, records in (
            ("postgresql", snapshot.postgresql),
            ("oracle", snapshot.oracle),
        ):
            for item in records:
                expected_payloads[(prefix / database / item.filename).as_posix()] = None
        with zipfile.ZipFile(archive_path) as archive:
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            expected_names = sorted(expected_payloads)
            if names != expected_names:
                missing = sorted(set(expected_names) - set(names))
                unexpected = sorted(set(names) - set(expected_names))
                raise MigrationPackagingError(
                    "migration catalogue archive membership is invalid: "
                    f"missing={missing}, unexpected={unexpected}"
                )
            manifest_name = (
                prefix / MigrationCatalogArchiveBuilder.MANIFEST_NAME
            ).as_posix()
            try:
                manifest = json.loads(archive.read(manifest_name))
            except json.JSONDecodeError as exc:
                raise MigrationPackagingError(
                    "migration catalogue archive manifest is invalid JSON"
                ) from exc
            if manifest != snapshot.as_dict():
                raise MigrationPackagingError(
                    "migration catalogue archive manifest does not match the source catalogue"
                )
            self._verify_records(archive, prefix, snapshot.postgresql)
            self._verify_records(archive, prefix, snapshot.oracle)
            oracle_manifest = archive.read((prefix / "oracle" / "manifest.json").as_posix())
            if hashlib.sha256(oracle_manifest).hexdigest() != snapshot.oracle_manifest_sha256:
                raise MigrationPackagingError(
                    "migration catalogue archive Oracle manifest checksum mismatch"
                )

    @classmethod
    def _verify_records(
        cls,
        archive: zipfile.ZipFile,
        prefix: PurePosixPath,
        records: Iterable[MigrationFileRecord],
    ) -> None:
        for item in records:
            name = (prefix / item.database / item.filename).as_posix()
            payload = archive.read(name)
            if len(payload) != item.size_bytes:
                raise MigrationPackagingError(
                    f"migration catalogue archive size mismatch: {name}"
                )
            if hashlib.sha256(payload).hexdigest() != item.sha256:
                raise MigrationPackagingError(
                    f"migration catalogue archive checksum mismatch: {name}"
                )
