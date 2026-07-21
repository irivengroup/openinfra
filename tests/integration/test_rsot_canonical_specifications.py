from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from openinfra.quality.rsot_canonical_promotion import Gate13Policy

ROOT = Path(__file__).parents[2]
CDC = ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0"
ROADMAP = ROOT / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5"


def _run(relative: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(relative)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_cdc_411_rsot_contract_is_executable() -> None:
    result = _run(CDC / "scripts/validate_rsot_canonical.py")
    assert result.returncode == 0, result.stderr
    assert "REQ-00860" in result.stdout
    assert "TST-RSOT-163" in result.stdout


def test_roadmap_24_contract_is_executable() -> None:
    result = _run(ROADMAP / "scripts/validate_roadmap.py")
    assert result.returncode == 0, result.stderr
    assert "roadmap 2.5.0" in result.stdout
    assert "15 gates" in result.stdout


def test_gate13_policy_matches_cdc_matrix() -> None:
    policy = Gate13Policy.load(ROOT / "docs/release/rsot-canonical-promotion-policy.json")
    with (CDC / "11-Matrices/Matrice-rsot-canonical-v4.11.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        matrix_controls = tuple(row["control_id"] for row in csv.DictReader(handle))
    assert matrix_controls == policy.required_controls


def test_gate13_workflow_is_fail_closed_and_complete() -> None:
    workflow = (ROOT / ".github/workflows/rsot-canonical.yml").read_text(encoding="utf-8")
    for token in (
        "openinfra-gate13",
        "--enforce",
        "pytest -n 4 --dist loadfile",
        "--cov-fail-under=98",
        "pip_audit --strict",
        "npm audit --audit-level=high",
        "scripts/verify_artifact.py",
        "scripts/smoke_installed_wheel.py",
    ):
        assert token in workflow


def test_gate13_policy_json_has_exact_six_controls() -> None:
    payload = json.loads(
        (ROOT / "docs/release/rsot-canonical-promotion-policy.json").read_text(encoding="utf-8")
    )
    assert payload["gate_id"] == "GATE-13"
    assert payload["release_id"] == "REL-14"
    assert payload["required_controls"] == list(Gate13Policy.EXPECTED_CONTROLS)
