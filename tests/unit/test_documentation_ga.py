from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.quality.documentation_ga import (
    GaDocumentationError,
    GaDocumentationManifest,
    GaMarkdownInspector,
    GaOpenApiCatalog,
)


class TestGaDocumentationManifest:
    def test_load_rejects_invalid_schema(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.json"
        path.write_text('{"schema_version": 2}', encoding="utf-8")
        with pytest.raises(GaDocumentationError, match="unsupported"):
            GaDocumentationManifest.load(path)

    def test_load_rejects_duplicate_paths(self, tmp_path: Path) -> None:
        path = tmp_path / "manifest.json"
        payload = {
            "schema_version": 1,
            "release_version": "0.32.3",
            "epic": "EPIC-1804",
            "documents": [
                {"id": "a", "path": "a.md", "audience": "all", "required_headings": ["A"]},
                {"id": "b", "path": "a.md", "audience": "all", "required_headings": ["B"]},
            ],
            "required_command_fragments": ["openinfra version"],
            "required_api_operations": ["GET /health"],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(GaDocumentationError, match="paths must be unique"):
            GaDocumentationManifest.load(path)


class TestGaMarkdownInspector:
    def test_detects_unbalanced_fence(self, tmp_path: Path) -> None:
        path = tmp_path / "guide.md"
        with pytest.raises(GaDocumentationError, match="unbalanced"):
            GaMarkdownInspector.assert_complete(path, "# Guide\n" + "x" * 700 + "\n```bash\n")

    def test_detects_broken_relative_link(self, tmp_path: Path) -> None:
        path = tmp_path / "guide.md"
        path.write_text("# Guide", encoding="utf-8")
        with pytest.raises(GaDocumentationError, match="broken"):
            GaMarkdownInspector.assert_links_resolve(
                tmp_path, path, "[document absent](missing.md)"
            )

    def test_extracts_cli_commands_from_fences(self) -> None:
        content = """# Guide\n```bash\nopeninfra version\nopeninfra database status \\\n  --root migrations\n```\n"""
        assert GaMarkdownInspector.cli_commands(content) == (
            "openinfra version",
            "openinfra database status",
        )


class TestGaOpenApiCatalog:
    def test_loads_path_methods(self, tmp_path: Path) -> None:
        path = tmp_path / "openapi.yaml"
        path.write_text(
            "openapi: 3.1.0\npaths:\n  /health:\n    get:\n      responses: {}\n",
            encoding="utf-8",
        )
        assert GaOpenApiCatalog.load(path) == frozenset({"GET /health"})


class TestGaDocumentSpecValidation:
    @pytest.mark.parametrize(
        "payload, message",
        [
            ("invalid", "JSON objects"),
            (
                {"id": "", "path": "a.md", "audience": "all", "required_headings": ["A"]},
                "cannot be empty",
            ),
            (
                {"id": "a", "path": "a.md", "audience": "all", "required_headings": []},
                "declare required headings",
            ),
            (
                {"id": "a", "path": "a.md", "audience": "all", "required_headings": [""]},
                "empty required heading",
            ),
        ],
    )
    def test_rejects_invalid_entries(self, payload: object, message: str) -> None:
        from openinfra.quality.documentation_ga import GaDocumentSpec

        with pytest.raises(GaDocumentationError, match=message):
            GaDocumentSpec.from_mapping(payload)


class TestGaManifestFailureModes:
    def test_missing_and_invalid_manifest_are_rejected(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.json"
        with pytest.raises(GaDocumentationError, match="missing"):
            GaDocumentationManifest.load(missing)
        invalid = tmp_path / "invalid.json"
        invalid.write_text("{", encoding="utf-8")
        with pytest.raises(GaDocumentationError, match="invalid JSON"):
            GaDocumentationManifest.load(invalid)

    @pytest.mark.parametrize(
        "payload, message",
        [
            (["invalid"], "root must be an object"),
            ({"schema_version": 1, "documents": []}, "must list documents"),
            (
                {
                    "schema_version": 1,
                    "documents": [
                        {"id": "a", "path": "a.md", "audience": "all", "required_headings": ["A"]},
                        {"id": "a", "path": "b.md", "audience": "all", "required_headings": ["B"]},
                    ],
                    "required_command_fragments": ["openinfra version"],
                    "required_api_operations": ["GET /health"],
                },
                "identifiers must be unique",
            ),
        ],
    )
    def test_rejects_invalid_root_and_catalogs(
        self, tmp_path: Path, payload: object, message: str
    ) -> None:
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(GaDocumentationError, match=message):
            GaDocumentationManifest.load(path)

    def test_rejects_empty_required_commands(self) -> None:
        with pytest.raises(GaDocumentationError, match="must list required commands"):
            GaDocumentationManifest._string_tuple([], "commands")
        with pytest.raises(GaDocumentationError, match="cannot be empty"):
            GaDocumentationManifest._string_tuple([""], "commands")


class TestGaMarkdownFailureModes:
    def test_rejects_short_unfinished_and_unknown_fences(self, tmp_path: Path) -> None:
        path = tmp_path / "guide.md"
        with pytest.raises(GaDocumentationError, match="too short"):
            GaMarkdownInspector.assert_complete(path, "# Guide")
        with pytest.raises(GaDocumentationError, match="unfinished"):
            GaMarkdownInspector.assert_complete(path, "# Guide\n" + "x" * 650 + "\nTBD")
        with pytest.raises(GaDocumentationError, match="unsupported"):
            GaMarkdownInspector.assert_complete(
                path, "# Guide\n" + "x" * 650 + "\n```python\nprint(1)\n```\n"
            )

    def test_external_links_are_accepted_and_escape_is_rejected(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        path = docs / "guide.md"
        GaMarkdownInspector.assert_links_resolve(
            tmp_path,
            path,
            "[web](https://example.invalid) [mail](mailto:ops@example.invalid) [anchor](#top)",
        )
        with pytest.raises(GaDocumentationError, match="escapes project root"):
            GaMarkdownInspector.assert_links_resolve(tmp_path, path, "[outside](../../outside.md)")


class TestGaCatalogFailureModes:
    def test_openapi_missing_or_empty_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(GaDocumentationError, match="missing"):
            GaOpenApiCatalog.load(tmp_path / "missing.yaml")
        empty = tmp_path / "empty.yaml"
        empty.write_text("openapi: 3.1.0\npaths: {}\n", encoding="utf-8")
        with pytest.raises(GaDocumentationError, match="no operations"):
            GaOpenApiCatalog.load(empty)

    def test_cli_path_parsing_rejects_invalid_examples(self) -> None:
        from openinfra.quality.documentation_ga import GaCliCatalog

        with pytest.raises(GaDocumentationError, match="quoting"):
            GaCliCatalog.command_path('openinfra search "unterminated')
        with pytest.raises(GaDocumentationError, match="invalid OpenInfra"):
            GaCliCatalog.command_path("python -m openinfra")
        assert "database status" in GaCliCatalog.command_paths()
        assert (
            GaCliCatalog.command_path("openinfra database status --root migrations")
            == "database status"
        )
