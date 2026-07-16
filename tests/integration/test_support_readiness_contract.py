from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from openinfra.quality.release_packaging import ReleaseSignatureVerifier
from openinfra.quality.support_readiness import SupportPolicy

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestSupportReadinessContract:
    def test_repository_policy_and_documents_are_operational(self) -> None:
        policy = SupportPolicy.load(PROJECT_ROOT / "docs/release/support-maintenance-policy.json")

        assert {profile.edition for profile in policy.profiles} == {"lite", "pro", "enterprise"}
        assert tuple(stage.name for stage in policy.lifecycle) == (
            "active",
            "maintenance",
            "security-only",
            "end-of-life",
        )
        for relative in policy.required_documents:
            assert (PROJECT_ROOT / relative).is_file()

    def test_cli_generates_gate_07_compatible_signed_evidence(self, tmp_path: Path) -> None:
        output = tmp_path / "support-readiness.json"
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/support_readiness.py",
                "--project-root",
                str(PROJECT_ROOT),
                "--output",
                str(output),
                "--ephemeral-key",
                "--enforce",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 0, completed.stderr
        payload = json.loads(output.read_text(encoding="utf-8"))
        for field in (
            "complete",
            "support_readiness",
            "sla_defined",
            "lifecycle_defined",
            "patch_policy_defined",
            "migration_policy_defined",
            "escalation_matrix_defined",
        ):
            assert payload[field] is True
        assert payload["report_kind"] == "support-readiness"
        assert payload["epic"] == "EPIC-1806"
        ReleaseSignatureVerifier.verify(
            output.with_suffix(".json.pub"), output, output.with_suffix(".json.sig")
        )

    def test_ci_and_quality_gate_require_support_readiness(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/support-readiness.yml").read_text(
            encoding="utf-8"
        )
        quality_gate = (PROJECT_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        for fragment in (
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "python -m pip install -e .",
            "scripts/support_readiness.py",
            "--enforce",
            "retention-days: 365",
        ):
            assert fragment in workflow
        assert "SupportReadinessGuard" in quality_gate
        assert "docs/runbooks/SUPPORT_MAINTENANCE.md" in pyproject
