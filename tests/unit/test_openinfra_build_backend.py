from __future__ import annotations

import hashlib
import io
import tarfile
from contextlib import nullcontext
from pathlib import Path

import pytest

import openinfra_build_backend
from openinfra_build_backend import (
    OpenInfraBuildBackend,
    PackageAssetStager,
    ReproducibleSdistNormalizer,
)


def _write_sdist(path: Path, *, member_mtime: float, content: bytes = b"payload\n") -> None:
    with tarfile.open(path, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        directory = tarfile.TarInfo("openinfra-test")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        directory.mtime = member_mtime
        directory.uid = 1000
        directory.gid = 1000
        directory.uname = "builder"
        directory.gname = "builder"
        archive.addfile(directory)

        file_info = tarfile.TarInfo("openinfra-test/data.txt")
        file_info.mode = 0o644
        file_info.mtime = member_mtime
        file_info.uid = 1000
        file_info.gid = 1000
        file_info.uname = "builder"
        file_info.gname = "builder"
        file_info.size = len(content)
        file_info.pax_headers = {"mtime": str(member_mtime), "comment": "retained"}
        archive.addfile(file_info, io.BytesIO(content))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestReproducibleSdistNormalizer:
    def test_normalizes_distinct_archives_to_identical_bytes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = tmp_path / "first.tar.gz"
        second = tmp_path / "second.tar.gz"
        _write_sdist(first, member_mtime=1_700_000_000.125)
        _write_sdist(second, member_mtime=1_700_000_001.875)
        assert _sha256(first) != _sha256(second)
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1704067200")

        ReproducibleSdistNormalizer.normalize(first)
        ReproducibleSdistNormalizer.normalize(second)

        assert _sha256(first) == _sha256(second)
        with tarfile.open(first, mode="r:gz") as archive:
            members = archive.getmembers()
            assert [member.name for member in members] == [
                "openinfra-test",
                "openinfra-test/data.txt",
            ]
            assert all(member.mtime == 1_704_067_200 for member in members)
            assert all(member.uid == 0 and member.gid == 0 for member in members)
            assert all(member.uname == "" and member.gname == "" for member in members)
            assert members[1].pax_headers == {"comment": "retained"}
            payload = archive.extractfile(members[1])
            assert payload is not None
            assert payload.read() == b"payload\n"

    def test_without_source_date_epoch_preserves_archive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        archive = tmp_path / "source.tar.gz"
        _write_sdist(archive, member_mtime=1_700_000_000.5)
        before = archive.read_bytes()
        monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)

        ReproducibleSdistNormalizer.normalize(archive)

        assert archive.read_bytes() == before

    @pytest.mark.parametrize("value", ["invalid", "-1", str(1 << 32)])
    def test_rejects_invalid_source_date_epoch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        archive = tmp_path / "source.tar.gz"
        _write_sdist(archive, member_mtime=1_700_000_000)
        monkeypatch.setenv("SOURCE_DATE_EPOCH", value)

        with pytest.raises(RuntimeError, match="SOURCE_DATE_EPOCH"):
            ReproducibleSdistNormalizer.normalize(archive)

    def test_build_sdist_normalizes_backend_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        artifact_name = "openinfra-test.tar.gz"
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1704067200")
        monkeypatch.setattr(openinfra_build_backend, "PackageAssetStager", nullcontext)

        def fake_build_sdist(
            sdist_directory: str,
            config_settings: dict[str, object] | None = None,
        ) -> str:
            assert config_settings == {"mode": "test"}
            _write_sdist(
                Path(sdist_directory) / artifact_name,
                member_mtime=1_700_000_000.5,
            )
            return artifact_name

        monkeypatch.setattr(
            openinfra_build_backend._setuptools_backend,
            "build_sdist",
            fake_build_sdist,
        )

        result = OpenInfraBuildBackend.build_sdist(
            str(tmp_path),
            config_settings={"mode": "test"},
        )

        assert result == artifact_name
        with tarfile.open(tmp_path / artifact_name, mode="r:gz") as archive:
            assert all(member.mtime == 1_704_067_200 for member in archive.getmembers())


class TestPackageAssetStager:
    @staticmethod
    def _write_configuration(root: Path, mapping: dict[str, str]) -> None:
        lines = ["[tool.hatch.build.targets.wheel.force-include]"]
        lines.extend(f'"{source}" = "{destination}"' for source, destination in mapping.items())
        (root / "pyproject.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_rejects_all_missing_sources_before_mutating_package_tree(self, tmp_path: Path) -> None:
        existing = tmp_path / "docs" / "existing.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("existing\n", encoding="utf-8")
        (tmp_path / "src" / "openinfra").mkdir(parents=True)
        self._write_configuration(
            tmp_path,
            {
                "docs/existing.md": "openinfra/docs/existing.md",
                "docs/missing.md": "openinfra/docs/missing.md",
            },
        )

        with pytest.raises(RuntimeError, match="Restore the complete qualified source archive"):
            with PackageAssetStager(tmp_path):
                pass

        assert not (tmp_path / "src" / "openinfra" / "docs").exists()

    def test_stages_and_atomically_cleans_external_assets(self, tmp_path: Path) -> None:
        source_file = tmp_path / "docs" / "required.md"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("required\n", encoding="utf-8")
        (tmp_path / "src" / "openinfra").mkdir(parents=True)
        destination = tmp_path / "src" / "openinfra" / "docs" / "required.md"
        self._write_configuration(
            tmp_path,
            {"docs/required.md": "openinfra/docs/required.md"},
        )

        with PackageAssetStager(tmp_path):
            assert destination.read_text(encoding="utf-8") == "required\n"

        assert not destination.exists()
        assert not destination.parent.exists()
