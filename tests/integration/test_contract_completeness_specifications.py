from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from openinfra.quality.contract_completeness_promotion import Gate14Policy

ROOT = Path(__file__).parents[2]
CDC = ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0"
ROADMAP = ROOT / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5"


def test_cdc_412_contract_is_executable() -> None:
    result = _run(CDC / "scripts/validate_docs.py")
    assert result.returncode == 0, result.stderr
    assert "861 requirements" in result.stdout
    assert "667 tests" in result.stdout


def test_roadmap_25_contract_is_executable() -> None:
    result = _run(ROADMAP / "scripts/validate_roadmap.py")
    assert result.returncode == 0, result.stderr
    assert "roadmap 2.5.0" in result.stdout
    assert "15 gates" in result.stdout


def test_gate14_policy_matches_cdc_control_matrix() -> None:
    policy = Gate14Policy.load(ROOT / "docs/release/contract-completeness-promotion-policy.json")
    with (CDC / "11-Matrices/Matrice-completude-contractuelle-v4.12.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        controls = tuple(row["control_id"] for row in csv.DictReader(stream))
    assert controls == policy.required_controls


def test_gate14_workflow_is_fail_closed_and_complete() -> None:
    workflow = (ROOT / ".github/workflows/contract-completeness.yml").read_text(encoding="utf-8")
    for token in (
        "openinfra-gate14",
        "--enforce",
        "pytest -n 4 --dist loadfile",
        "--cov-fail-under=98",
        "pip_audit --strict",
        "npm audit --audit-level=high",
        "scripts/verify_artifact.py",
        "scripts/smoke_installed_wheel.py",
        "actions/upload-artifact@v6",
    ):
        assert token in workflow
    assert "pull_request_target:" not in workflow


def test_release_contract_versions_are_consistent() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "0.34.7"
    assert (CDC / "VERSION").read_text(encoding="utf-8").strip() == "4.12.0"
    assert (ROADMAP / "VERSION").read_text(encoding="utf-8").strip() == "2.5.0"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.34.7"' in pyproject
    assert "openinfra-gate14" in pyproject


def test_registry_has_exact_policy_metrics() -> None:
    path = ROOT / "docs/release/contract-proof-registry-v4.12.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    levels: dict[str, int] = {}
    selectors: set[str] = set()
    evidence: set[str] = set()
    for row in rows:
        levels[row["proof_level"]] = levels.get(row["proof_level"], 0) + 1
        selectors.update(item for item in row["pytest_selectors"].split(";") if item)
        evidence.update(item for item in row["evidence_files"].split(";") if item)
    assert len(rows) == 667
    assert levels == {"partial": 600, "external": 48, "automated": 19}
    assert len(selectors) == 27
    assert len(evidence) == 54


def test_historical_specifications_are_preserved() -> None:
    assert (ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.11.0/VERSION").read_text(
        encoding="utf-8"
    ).strip() == "4.11.0"
    assert (ROOT / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.4/VERSION").read_text(
        encoding="utf-8"
    ).strip() == "2.4.0"


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
