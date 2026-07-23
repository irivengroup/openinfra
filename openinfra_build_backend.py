from __future__ import annotations

import copy
import gzip
import os
import shutil
import stat
import tarfile
import tempfile
import tomllib
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any, BinaryIO

from setuptools import build_meta as _setuptools_backend


class PackageAssetStager(AbstractContextManager["PackageAssetStager"]):
    """Stage external runtime assets under the Python package for setuptools builds."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = (project_root or Path(__file__).resolve().parent).resolve()
        self._created_roots: list[Path] = []

    def __enter__(self) -> PackageAssetStager:
        config = tomllib.loads((self._root / "pyproject.toml").read_text(encoding="utf-8"))
        mapping = (
            config.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("force-include", {})
        )
        if not isinstance(mapping, dict) or not mapping:
            raise RuntimeError("OpenInfra packaging force-include mapping is missing")
        package_root = (self._root / "src").resolve()
        resolved_mapping: list[tuple[str, Path, Path]] = []
        missing_sources: list[str] = []
        for source_value, destination_value in sorted(mapping.items()):
            source_name = str(source_value)
            source = (self._root / source_name).resolve()
            destination = (package_root / str(destination_value)).resolve()
            source.relative_to(self._root)
            destination.relative_to(package_root)
            if not source.exists():
                missing_sources.append(source_name)
            resolved_mapping.append((source_name, source, destination))

        if missing_sources:
            missing = ", ".join(missing_sources)
            raise RuntimeError(
                "OpenInfra packaging sources are missing: "
                f"{missing}. Restore the complete qualified source archive before building."
            )

        for _source_name, source, destination in resolved_mapping:
            first_missing = self._first_missing_parent(destination, package_root)
            if first_missing is not None:
                self._created_roots.append(first_missing)
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        for path in sorted(set(self._created_roots), key=lambda item: len(item.parts), reverse=True):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        return None

    @staticmethod
    def _first_missing_parent(destination: Path, package_root: Path) -> Path | None:
        current = destination
        missing: list[Path] = []
        while current != package_root and not current.exists():
            missing.append(current)
            current = current.parent
        return missing[-1] if missing else None


class ReproducibleSdistNormalizer:
    """Normalize setuptools sdists when SOURCE_DATE_EPOCH is configured."""

    _MAX_GZIP_EPOCH = (1 << 32) - 1
    _VOLATILE_PAX_HEADERS = frozenset({"atime", "ctime", "mtime"})

    @classmethod
    def normalize(cls, archive_path: Path) -> None:
        raw_epoch = os.environ.get("SOURCE_DATE_EPOCH")
        if raw_epoch is None:
            return
        epoch = cls._parse_epoch(raw_epoch)
        if not archive_path.is_file():
            raise RuntimeError(f"OpenInfra sdist is missing: {archive_path}")

        archive_mode = stat.S_IMODE(archive_path.stat().st_mode)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{archive_path.name}.",
                suffix=".tmp",
                dir=archive_path.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                cls._rewrite_archive(archive_path, temporary_file, epoch)
            temporary_path.chmod(archive_mode)
            os.replace(temporary_path, archive_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @classmethod
    def _rewrite_archive(cls, archive_path: Path, destination: BinaryIO, epoch: int) -> None:
        with tarfile.open(archive_path, mode="r:gz") as source_archive:
            members = sorted(source_archive.getmembers(), key=lambda member: member.name)
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=9,
                fileobj=destination,
                mtime=epoch,
            ) as compressed_stream:
                with tarfile.open(
                    fileobj=compressed_stream,
                    mode="w|",
                    format=tarfile.PAX_FORMAT,
                ) as target_archive:
                    for member in members:
                        normalized = cls._normalize_member(member, epoch)
                        payload = source_archive.extractfile(member) if member.isreg() else None
                        try:
                            target_archive.addfile(normalized, payload)
                        finally:
                            if payload is not None:
                                payload.close()

    @classmethod
    def _normalize_member(cls, member: tarfile.TarInfo, epoch: int) -> tarfile.TarInfo:
        normalized = copy.copy(member)
        normalized.mtime = epoch
        normalized.uid = 0
        normalized.gid = 0
        normalized.uname = ""
        normalized.gname = ""
        normalized.pax_headers = {
            key: value
            for key, value in member.pax_headers.items()
            if key not in cls._VOLATILE_PAX_HEADERS
        }
        return normalized

    @classmethod
    def _parse_epoch(cls, raw_epoch: str) -> int:
        try:
            epoch = int(raw_epoch, 10)
        except ValueError as exc:
            raise RuntimeError("SOURCE_DATE_EPOCH must be a base-10 integer") from exc
        if not 0 <= epoch <= cls._MAX_GZIP_EPOCH:
            raise RuntimeError(
                f"SOURCE_DATE_EPOCH must be between 0 and {cls._MAX_GZIP_EPOCH}"
            )
        return epoch


class OpenInfraBuildBackend:
    @staticmethod
    def build_wheel(
        wheel_directory: str,
        config_settings: dict[str, Any] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        with PackageAssetStager():
            return _setuptools_backend.build_wheel(
                wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )

    @staticmethod
    def build_sdist(
        sdist_directory: str,
        config_settings: dict[str, Any] | None = None,
    ) -> str:
        with PackageAssetStager():
            artifact_name = _setuptools_backend.build_sdist(
                sdist_directory,
                config_settings=config_settings,
            )
        ReproducibleSdistNormalizer.normalize(Path(sdist_directory) / artifact_name)
        return artifact_name

    @staticmethod
    def build_editable(
        wheel_directory: str,
        config_settings: dict[str, Any] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        with PackageAssetStager():
            return _setuptools_backend.build_editable(
                wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )

    @staticmethod
    def prepare_metadata_for_build_wheel(
        metadata_directory: str,
        config_settings: dict[str, Any] | None = None,
    ) -> str:
        return _setuptools_backend.prepare_metadata_for_build_wheel(
            metadata_directory,
            config_settings=config_settings,
        )

    @staticmethod
    def get_requires_for_build_wheel(
        config_settings: dict[str, Any] | None = None,
    ) -> list[str]:
        return _setuptools_backend.get_requires_for_build_wheel(config_settings=config_settings)

    @staticmethod
    def get_requires_for_build_sdist(
        config_settings: dict[str, Any] | None = None,
    ) -> list[str]:
        return _setuptools_backend.get_requires_for_build_sdist(config_settings=config_settings)


build_wheel = OpenInfraBuildBackend.build_wheel
build_sdist = OpenInfraBuildBackend.build_sdist
build_editable = OpenInfraBuildBackend.build_editable
prepare_metadata_for_build_wheel = OpenInfraBuildBackend.prepare_metadata_for_build_wheel
get_requires_for_build_wheel = OpenInfraBuildBackend.get_requires_for_build_wheel
get_requires_for_build_sdist = OpenInfraBuildBackend.get_requires_for_build_sdist
