from __future__ import annotations

import argparse
import json
import shlex
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class DockerContextValidationReport:
    project_root: str
    dockerfile: str
    copied_sources: tuple[str, ...]
    required_sources: tuple[str, ...]
    missing_sources: tuple[str, ...]
    uncovered_sources: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.missing_sources and not self.uncovered_sources

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["passed"] = self.passed
        return payload


class DockerBuildContextValidator:
    """Validate that every forced wheel asset exists and enters the Docker build stage."""

    _INSTALL_MARKER = "RUN python scripts/validate_docker_build_context.py"

    def __init__(self, project_root: Path, dockerfile: Path | None = None) -> None:
        self._root = project_root.resolve()
        candidate = dockerfile or Path("Dockerfile")
        self._dockerfile = (
            candidate.resolve() if candidate.is_absolute() else (self._root / candidate).resolve()
        )
        self._dockerfile.relative_to(self._root)

    def validate(self) -> DockerContextValidationReport:
        pyproject = self._root / "pyproject.toml"
        if not pyproject.is_file():
            raise RuntimeError(f"OpenInfra pyproject is missing: {pyproject}")
        if not self._dockerfile.is_file():
            raise RuntimeError(f"OpenInfra Dockerfile is missing: {self._dockerfile}")

        copied_sources = tuple(sorted(self._copied_sources_before_install()))
        required_sources = tuple(sorted(self._forced_wheel_sources(pyproject)))
        missing_sources = tuple(
            source for source in required_sources if not (self._root / source).exists()
        )
        uncovered_sources = tuple(
            source
            for source in required_sources
            if not self._is_covered(Path(source), (Path(item) for item in copied_sources))
        )
        return DockerContextValidationReport(
            project_root=str(self._root),
            dockerfile=str(self._dockerfile),
            copied_sources=copied_sources,
            required_sources=required_sources,
            missing_sources=missing_sources,
            uncovered_sources=uncovered_sources,
        )

    @staticmethod
    def _forced_wheel_sources(pyproject: Path) -> set[str]:
        configuration = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        mapping = (
            configuration.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("force-include", {})
        )
        if not isinstance(mapping, dict) or not mapping:
            raise RuntimeError("OpenInfra packaging force-include mapping is missing")
        return {Path(str(source)).as_posix() for source in mapping}

    def _copied_sources_before_install(self) -> set[str]:
        dockerfile = self._dockerfile.read_text(encoding="utf-8")
        build_section = dockerfile.split(self._INSTALL_MARKER, maxsplit=1)[0]
        logical_lines = self._logical_lines(build_section.splitlines())
        copied_sources: set[str] = set()
        for line in logical_lines:
            stripped = line.strip()
            if not stripped.upper().startswith("COPY "):
                continue
            copied_sources.update(self._parse_copy_sources(stripped[5:].strip()))
        return copied_sources

    @staticmethod
    def _logical_lines(lines: Iterable[str]) -> tuple[str, ...]:
        logical: list[str] = []
        current = ""
        for raw_line in lines:
            stripped = raw_line.rstrip()
            if not current and (not stripped.strip() or stripped.lstrip().startswith("#")):
                continue
            continuation = stripped.endswith("\\")
            fragment = stripped[:-1].strip() if continuation else stripped.strip()
            current = f"{current} {fragment}".strip()
            if not continuation:
                logical.append(current)
                current = ""
        if current:
            logical.append(current)
        return tuple(logical)

    @staticmethod
    def _parse_copy_sources(arguments: str) -> tuple[str, ...]:
        if arguments.startswith("["):
            values = json.loads(arguments)
            if not isinstance(values, list) or len(values) < 2 or not all(
                isinstance(value, str) for value in values
            ):
                raise RuntimeError(f"Unsupported Docker COPY instruction: {arguments}")
            tokens = values
        else:
            tokens = shlex.split(arguments, posix=True)
            while tokens and tokens[0].startswith("--"):
                tokens.pop(0)
        if len(tokens) < 2:
            raise RuntimeError(f"Unsupported Docker COPY instruction: {arguments}")
        return tuple(Path(token).as_posix().rstrip("/") or "." for token in tokens[:-1])

    @staticmethod
    def _is_covered(required: Path, copied_sources: Iterable[Path]) -> bool:
        for copied in copied_sources:
            if copied == Path(".") or required == copied or copied in required.parents:
                return True
        return False


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate OpenInfra packaging assets inside the Docker build context."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dockerfile", type=Path, default=Path("Dockerfile"))
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = DockerBuildContextValidator(args.project_root, args.dockerfile).validate()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Docker build context validation failed: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        print(json.dumps(report.to_payload(), indent=2, sort_keys=True))
    elif report.passed:
        print(
            "Docker build context validation passed: "
            f"{len(report.required_sources)} packaging assets are present and copied."
        )

    if not report.passed:
        if report.missing_sources:
            print(
                "Missing packaging sources: " + ", ".join(report.missing_sources),
                file=sys.stderr,
            )
        if report.uncovered_sources:
            print(
                "Packaging sources absent from Docker COPY instructions: "
                + ", ".join(report.uncovered_sources),
                file=sys.stderr,
            )
        print(
            "Restore the complete qualified source archive before rebuilding the runtime image.",
            file=sys.stderr,
        )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
