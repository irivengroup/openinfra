from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_security_validator_reports_complete_contract(tmp_path: Path) -> None:
    output = tmp_path / "kubernetes-security-contract.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_kubernetes_security.py",
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
    assert payload["epic"] == "EPIC-2103"
    assert payload["secret_material_ingestion"] is False
    assert payload["masked_secret_references"] is True
    assert payload["legacy_snapshot_fingerprint_compatibility"] is True


def test_kubernetes_security_contract_is_wired_into_ci_quality_gate_and_packaging() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    quality_gate = (ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    artifact_verifier = (ROOT / "scripts/verify_artifact.py").read_text(encoding="utf-8")
    wheel_smoke = (ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")

    assert "scripts/validate_kubernetes_security.py --project-root . --enforce" in workflow
    assert "tests/integration/test_kubernetes_security_tooling.py" in workflow
    assert '"scripts/validate_kubernetes_security.py"' in quality_gate
    assert '"src/openinfra/domain/kubernetes_security.py"' in artifact_verifier
    assert '"tests/integration/test_kubernetes_security_tooling.py"' in artifact_verifier
    assert '"/api/v1/kubernetes/topologies/security"' in wheel_smoke
    assert '"/api/v1/kubernetes/topologies/latest-security"' in wheel_smoke
