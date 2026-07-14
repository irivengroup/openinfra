from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from openinfra.quality.documentation_ga import GaDocumentationValidator


class TestGaDocumentationContract:
    def test_repository_documentation_is_complete(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        report = GaDocumentationValidator(project_root).validate()
        assert report.passed is True
        assert report.version == "0.32.10"
        assert report.epic == "EPIC-1804"
        assert report.document_count == 10
        assert report.command_count >= 20
        assert len(report.content_sha256) == 64

    def test_cli_writes_a_machine_readable_report(self, tmp_path: Path) -> None:
        project_root = Path(__file__).resolve().parents[2]
        output = tmp_path / "ga-documentation-report.json"
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/validate_ga_documentation.py",
                "--project-root",
                str(project_root),
                "--output",
                str(output),
                "--enforce",
            ],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["passed"] is True
        assert payload["version"] == "0.32.10"

    def test_ci_executes_documentation_gate(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        workflow = (project_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        dedicated = (project_root / ".github/workflows/documentation-ga.yml").read_text(
            encoding="utf-8"
        )
        assert "validate_ga_documentation.py" in workflow
        for fragment in (
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "validate_ga_documentation.py",
            "ga-documentation-report.json",
        ):
            assert fragment in dedicated
