from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_quality_toolchain_is_pinned_in_all_python_dependency_surfaces() -> None:
    requirements = (ROOT / "requirements/dev.txt").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for requirement in ("ruff==0.15.22", "mypy==2.2.0"):
        assert requirement in requirements
        assert f'"{requirement}"' in pyproject
    assert "ruff>=" not in requirements
    assert "mypy>=" not in requirements


def test_gate14_uploads_diagnostics_on_failure_and_strict_evidence_on_success() -> None:
    workflow = (ROOT / ".github/workflows/contract-completeness.yml").read_text(
        encoding="utf-8"
    )

    for token in (
        "Prepare GATE-14 evidence workspace",
        "scripts/prepare_ci_evidence.py",
        "Validate deterministic quality toolchain",
        "scripts/validate_quality_toolchain.py --json",
        "Ruff format check",
        "ruff format --check --diff",
        "Ruff lint",
        "ruff check --output-format=github",
        "Strict typing",
        "artifacts/quality/mypy.log",
        "Upload failed GATE-14 diagnostics",
        "if: failure()",
        "if-no-files-found: warn",
        "Upload immutable GATE-14 evidence",
        "if: success()",
        "artifacts/gate14/report.json",
        "artifacts/gate14/ci-context.json",
        "dist/*",
        "web/dist/**",
        "if-no-files-found: error",
    ):
        assert token in workflow

    immutable = workflow.split("- name: Upload immutable GATE-14 evidence", 1)[1]
    assert "if: always()" not in immutable


def test_gate12_and_gate13_use_the_same_fail_closed_evidence_pattern() -> None:
    workflows = {
        "offline-runtime-licensing.yml": "GATE-12",
        "rsot-canonical.yml": "GATE-13",
    }
    for filename, gate in workflows.items():
        workflow = (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8")
        assert f"Prepare {gate} evidence workspace" in workflow
        assert "scripts/validate_quality_toolchain.py --json" in workflow
        assert f"Upload failed {gate} diagnostics" in workflow
        assert f"Upload immutable {gate} evidence" in workflow
        assert "if: failure()" in workflow
        assert "if: success()" in workflow
        assert "if-no-files-found: warn" in workflow
        assert "if-no-files-found: error" in workflow


def test_all_quality_workflows_validate_the_pinned_toolchain() -> None:
    for filename in (
        "ci.yml",
        "advanced-identity-oracle.yml",
        "release-packaging.yml",
        "offline-runtime-licensing.yml",
        "rsot-canonical.yml",
        "contract-completeness.yml",
    ):
        workflow = (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8")
        assert "Validate deterministic quality toolchain" in workflow
        assert "scripts/validate_quality_toolchain.py" in workflow
