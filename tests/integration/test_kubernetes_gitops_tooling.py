from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_gitops_validator_reports_complete_contract(tmp_path: Path) -> None:
    output = tmp_path / "kubernetes-gitops-contract.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_kubernetes_gitops.py",
            "--project-root",
            str(ROOT),
            "--output",
            str(output),
            "--enforce",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["complete"] is True
    assert payload["epic"] == "EPIC-2104"
    assert payload["automatic_remediation"] is False
    assert payload["migration_count"] == 56


def test_kubernetes_gitops_contract_is_wired_into_ci_quality_gate_and_packaging() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    quality_gate = (ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    artifact_verifier = (ROOT / "scripts/verify_artifact.py").read_text(encoding="utf-8")
    wheel_smoke = (ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")

    assert "scripts/validate_kubernetes_gitops.py --project-root . --enforce" in workflow
    assert "tests/integration/test_kubernetes_gitops_tooling.py" in workflow
    assert '"scripts/validate_kubernetes_gitops.py"' in quality_gate
    assert '"src/openinfra/domain/kubernetes_gitops.py"' in artifact_verifier
    assert (
        '"installers/migrations/postgresql/0056_kubernetes_gitops_drift.sql"' in artifact_verifier
    )
    assert '"tests/integration/test_kubernetes_gitops_tooling.py"' in artifact_verifier
    assert '"/api/v1/kubernetes/gitops-states"' in wheel_smoke
    assert 'EXPECTED_LAST_MIGRATION = "0056_kubernetes_gitops_drift.sql"' in wheel_smoke
    assert "EXPECTED_MIGRATION_COUNT = 56" in wheel_smoke
