from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from openinfra import __version__
from openinfra.interfaces.cli import OpenInfraCLI


class GaDocumentationError(Exception):
    """Raised when the GA documentation set is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class GaDocumentSpec:
    identifier: str
    path: str
    audience: str
    required_headings: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: object) -> GaDocumentSpec:
        if not isinstance(payload, dict):
            raise GaDocumentationError("documentation manifest entries must be JSON objects")
        identifier = str(payload.get("id", "")).strip()
        path = str(payload.get("path", "")).strip()
        audience = str(payload.get("audience", "")).strip()
        raw_headings = payload.get("required_headings", [])
        if not identifier or not path or not audience:
            raise GaDocumentationError("documentation manifest entry fields cannot be empty")
        if not isinstance(raw_headings, list) or not raw_headings:
            raise GaDocumentationError(f"document {identifier} must declare required headings")
        headings = tuple(str(value).strip() for value in raw_headings)
        if any(not heading for heading in headings):
            raise GaDocumentationError(f"document {identifier} has an empty required heading")
        return cls(identifier, path, audience, headings)


@dataclass(frozen=True, slots=True)
class GaDocumentationManifest:
    schema_version: int
    release_version: str
    epic: str
    documents: tuple[GaDocumentSpec, ...]
    required_command_fragments: tuple[str, ...]
    required_api_operations: tuple[str, ...]

    @classmethod
    def load(cls, path: Path) -> GaDocumentationManifest:
        if not path.is_file():
            raise GaDocumentationError(f"GA documentation manifest is missing: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise GaDocumentationError("GA documentation manifest is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GaDocumentationError("GA documentation manifest root must be an object")
        schema_version = payload.get("schema_version")
        if schema_version != 1:
            raise GaDocumentationError("unsupported GA documentation manifest schema")
        documents_value = payload.get("documents")
        if not isinstance(documents_value, list) or not documents_value:
            raise GaDocumentationError("GA documentation manifest must list documents")
        documents = tuple(GaDocumentSpec.from_mapping(item) for item in documents_value)
        identifiers = [document.identifier for document in documents]
        paths = [document.path for document in documents]
        if len(identifiers) != len(set(identifiers)):
            raise GaDocumentationError("GA documentation document identifiers must be unique")
        if len(paths) != len(set(paths)):
            raise GaDocumentationError("GA documentation document paths must be unique")
        commands = cls._string_tuple(payload.get("required_command_fragments"), "commands")
        operations = cls._string_tuple(payload.get("required_api_operations"), "operations")
        return cls(
            schema_version=1,
            release_version=str(payload.get("release_version", "")).strip(),
            epic=str(payload.get("epic", "")).strip(),
            documents=documents,
            required_command_fragments=commands,
            required_api_operations=operations,
        )

    @staticmethod
    def _string_tuple(value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not value:
            raise GaDocumentationError(f"GA documentation manifest must list required {field}")
        result = tuple(str(item).strip() for item in value)
        if any(not item for item in result):
            raise GaDocumentationError(f"GA documentation required {field} cannot be empty")
        return result


@dataclass(frozen=True, slots=True)
class GaDocumentationReport:
    generated_at: str
    version: str
    epic: str
    document_count: int
    command_count: int
    api_operation_count: int
    content_sha256: str
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "version": self.version,
            "epic": self.epic,
            "document_count": self.document_count,
            "command_count": self.command_count,
            "api_operation_count": self.api_operation_count,
            "content_sha256": self.content_sha256,
            "passed": self.passed,
        }


class GaMarkdownInspector:
    _HEADING_PATTERN: Final[re.Pattern[str]] = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
    _LINK_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    _FENCE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^```([A-Za-z0-9_-]*)\s*$")
    _UNFINISHED_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
        re.compile(r"\bT(?:O)DO\b", re.IGNORECASE),
        re.compile(r"\bF(?:I)XME\b", re.IGNORECASE),
        re.compile(r"\bTBD\b", re.IGNORECASE),
        re.compile(r"\bXXX\b"),
        re.compile(r"\bà compléter\b", re.IGNORECASE),
        re.compile(r"\bcoming soon\b", re.IGNORECASE),
    )
    _ALLOWED_FENCE_LANGUAGES: Final[frozenset[str]] = frozenset(
        {"", "bash", "console", "dotenv", "http", "json", "powershell", "text", "yaml"}
    )

    @classmethod
    def headings(cls, content: str) -> frozenset[str]:
        return frozenset(match.group(1).strip() for match in cls._HEADING_PATTERN.finditer(content))

    @classmethod
    def assert_complete(cls, path: Path, content: str) -> None:
        if len(content.strip()) < 600:
            raise GaDocumentationError(f"GA document is too short to be operational: {path}")
        for pattern in cls._UNFINISHED_PATTERNS:
            if pattern.search(content):
                raise GaDocumentationError(f"unfinished documentation marker detected in {path}")
        open_fence = False
        for line_number, line in enumerate(content.splitlines(), start=1):
            match = cls._FENCE_PATTERN.match(line)
            if not match:
                continue
            language = match.group(1).lower()
            if not open_fence and language not in cls._ALLOWED_FENCE_LANGUAGES:
                raise GaDocumentationError(
                    f"unsupported code fence language in {path}:{line_number}: {language}"
                )
            open_fence = not open_fence
        if open_fence:
            raise GaDocumentationError(f"unbalanced code fence in {path}")

    @classmethod
    def assert_links_resolve(cls, project_root: Path, path: Path, content: str) -> None:
        for match in cls._LINK_PATTERN.finditer(content):
            target = match.group(1).strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            file_target = target.split("#", maxsplit=1)[0]
            if not file_target:
                continue
            resolved = (path.parent / file_target).resolve()
            try:
                resolved.relative_to(project_root.resolve())
            except ValueError as exc:
                raise GaDocumentationError(
                    f"documentation link escapes project root: {target}"
                ) from exc
            if not resolved.exists():
                raise GaDocumentationError(f"broken documentation link in {path}: {target}")

    @classmethod
    def cli_commands(cls, content: str) -> tuple[str, ...]:
        commands: list[str] = []
        inside = False
        for line in content.splitlines():
            fence = cls._FENCE_PATTERN.match(line)
            if fence:
                inside = not inside
                continue
            stripped = line.strip()
            if inside and stripped.startswith("openinfra "):
                commands.append(stripped.rstrip("\\").strip())
        return tuple(commands)


class GaOpenApiCatalog:
    _PATH_PATTERN: Final[re.Pattern[str]] = re.compile(r"^  (/[^:]*):\s*$")
    _METHOD_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"^    (get|post|put|patch|delete|head|options):\s*$", re.IGNORECASE
    )

    @classmethod
    def load(cls, path: Path) -> frozenset[str]:
        if not path.is_file():
            raise GaDocumentationError(f"OpenAPI contract is missing: {path}")
        current_path = ""
        operations: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            path_match = cls._PATH_PATTERN.match(line)
            if path_match:
                current_path = path_match.group(1)
                continue
            method_match = cls._METHOD_PATTERN.match(line)
            if method_match and current_path:
                operations.add(f"{method_match.group(1).upper()} {current_path}")
        if not operations:
            raise GaDocumentationError("OpenAPI contract exposes no operations")
        return frozenset(operations)


class GaCliCatalog:
    @classmethod
    def command_paths(cls) -> frozenset[str]:
        return frozenset(cls._collect_paths(OpenInfraCLI()._build_parser(), ()))

    @classmethod
    def _collect_paths(cls, parser: argparse.ArgumentParser, prefix: tuple[str, ...]) -> set[str]:
        paths: set[str] = set()
        for action in parser._actions:
            if not isinstance(action, argparse._SubParsersAction):
                continue
            for name, subparser in action.choices.items():
                path = (*prefix, str(name))
                paths.add(" ".join(path))
                paths.update(cls._collect_paths(subparser, path))
        return paths

    @classmethod
    def command_path(cls, command: str) -> str:
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise GaDocumentationError(f"invalid CLI example quoting: {command}") from exc
        if not tokens or tokens[0] != "openinfra":
            raise GaDocumentationError(f"invalid OpenInfra CLI example: {command}")
        leading: list[str] = []
        for token in tokens[1:]:
            if token.startswith("-"):
                break
            leading.append(token)
        return " ".join(leading)


class GaDocumentationValidator:
    _MANIFEST_PATH: Final[str] = "docs/ga/documentation-manifest.json"

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()

    def validate(self) -> GaDocumentationReport:
        manifest = GaDocumentationManifest.load(self._project_root / self._MANIFEST_PATH)
        if manifest.release_version != __version__:
            raise GaDocumentationError(
                "GA documentation version "
                f"{manifest.release_version} differs from package {__version__}"
            )
        if manifest.epic != "EPIC-1804":
            raise GaDocumentationError("GA documentation manifest must target EPIC-1804")
        combined: list[str] = []
        documented_cli_commands: list[str] = []
        for document in manifest.documents:
            path = self._project_root / document.path
            if not path.is_file():
                raise GaDocumentationError(f"required GA document is missing: {document.path}")
            content = path.read_text(encoding="utf-8")
            GaMarkdownInspector.assert_complete(path, content)
            GaMarkdownInspector.assert_links_resolve(self._project_root, path, content)
            required_version = f"Version cible : `{__version__}`"
            if required_version not in content:
                raise GaDocumentationError(
                    f"GA document version marker is missing: {document.path}"
                )
            headings = GaMarkdownInspector.headings(content)
            missing_headings = [
                heading for heading in document.required_headings if heading not in headings
            ]
            if missing_headings:
                raise GaDocumentationError(
                    f"GA document {document.path} misses headings: {', '.join(missing_headings)}"
                )
            documented_cli_commands.extend(GaMarkdownInspector.cli_commands(content))
            combined.append(f"{document.path}\n{content}")
        self._assert_required_commands(manifest, combined)
        self._assert_cli_commands_exist(documented_cli_commands)
        self._assert_api_operations_exist(manifest)
        digest = hashlib.sha256("\n".join(combined).encode("utf-8")).hexdigest()
        return GaDocumentationReport(
            generated_at=datetime.now(tz=UTC).isoformat(),
            version=__version__,
            epic=manifest.epic,
            document_count=len(manifest.documents),
            command_count=len(documented_cli_commands),
            api_operation_count=len(manifest.required_api_operations),
            content_sha256=digest,
            passed=True,
        )

    def _assert_required_commands(
        self, manifest: GaDocumentationManifest, combined_documents: list[str]
    ) -> None:
        content = "\n".join(combined_documents)
        missing = [
            command for command in manifest.required_command_fragments if command not in content
        ]
        if missing:
            raise GaDocumentationError(
                "GA documentation misses required commands: " + ", ".join(missing)
            )

    def _assert_cli_commands_exist(self, commands: list[str]) -> None:
        available = GaCliCatalog.command_paths()
        invalid = [
            command for command in commands if GaCliCatalog.command_path(command) not in available
        ]
        if invalid:
            raise GaDocumentationError(
                "GA documentation references unknown CLI commands: " + ", ".join(invalid)
            )

    def _assert_api_operations_exist(self, manifest: GaDocumentationManifest) -> None:
        available = GaOpenApiCatalog.load(self._project_root / "docs/api/openapi.yaml")
        missing = [
            operation
            for operation in manifest.required_api_operations
            if operation not in available
        ]
        if missing:
            raise GaDocumentationError(
                "GA documentation references unknown API operations: " + ", ".join(missing)
            )
