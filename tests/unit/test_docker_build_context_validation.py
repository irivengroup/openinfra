from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_minimal_project(root: Path, *, include_source: bool, copy_docs: bool) -> None:
    (root / "docs" / "runbooks").mkdir(parents=True)
    if include_source:
        (root / "docs" / "runbooks" / "required.md").write_text("required\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """
[tool.hatch.build.targets.wheel.force-include]
"docs/runbooks/required.md" = "openinfra/docs/runbooks/required.md"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    copy_instruction = "COPY docs ./docs" if copy_docs else "COPY README.md ./"
    (root / "Dockerfile").write_text(
        f"FROM python:3.11-slim\n{copy_instruction}\n"
        "RUN python scripts/validate_docker_build_context.py --project-root .\n",
        encoding="utf-8",
    )


def _run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/validate_docker_build_context.py",
            "--project-root",
            str(root),
            "--json",
        ],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )


def test_project_docker_context_contains_every_forced_packaging_asset() -> None:
    result = _run_validator(Path.cwd())

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["missing_sources"] == []
    assert payload["uncovered_sources"] == []
    assert "docs/runbooks/RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md" in payload[
        "required_sources"
    ]
    assert "docs" in payload["copied_sources"]


def test_validator_rejects_an_incomplete_qualified_source_tree(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path, include_source=False, copy_docs=True)

    result = _run_validator(tmp_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert payload["missing_sources"] == ["docs/runbooks/required.md"]
    assert payload["uncovered_sources"] == []
    assert "Restore the complete qualified source archive" in result.stderr


def test_validator_rejects_assets_not_copied_before_packaging(tmp_path: Path) -> None:
    _write_minimal_project(tmp_path, include_source=True, copy_docs=False)

    result = _run_validator(tmp_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert payload["missing_sources"] == []
    assert payload["uncovered_sources"] == ["docs/runbooks/required.md"]
