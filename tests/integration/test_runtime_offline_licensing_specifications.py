from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


class TestRuntimeOfflineLicensingSpecifications:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    CDC_49 = PROJECT_ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0"
    CDC_410 = PROJECT_ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.10.0"
    ROADMAP_22 = PROJECT_ROOT / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2"
    ROADMAP_23 = PROJECT_ROOT / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3"

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str | None, str | list[str] | None]]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    @classmethod
    def _run_validator(cls, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(path)],
            cwd=cls.PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_cdc_410_validator_and_exact_metrics(self) -> None:
        result = self._run_validator(self.CDC_410 / "scripts/validate_runtime_licensing.py")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "859 exigences, 665 tests, 859 traces" in result.stdout

        requirements = self._read_csv(self.CDC_410 / "11-Matrices/Exigences.csv")
        tests = self._read_csv(self.CDC_410 / "11-Matrices/Tests.csv")
        traces = self._read_csv(self.CDC_410 / "11-Matrices/Traceabilite.csv")
        assert len(requirements) == 859
        assert len(tests) == 665
        assert len(traces) == 859
        assert all(None not in row for row in (requirements + tests + traces))
        assert requirements[-1]["id"] == "REQ-00859"
        assert {row["requirement_id"] for row in traces} == {row["id"] for row in requirements}

    def test_roadmap_23_validator_and_exact_metrics(self) -> None:
        result = self._run_validator(self.ROADMAP_23 / "scripts/validate_roadmap.py")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "24 phases, 14 releases, 141 epics" in result.stdout
        assert "125 tests, 138 alignements" in result.stdout

        expected_counts = {
            "02-roadmap-phases.csv": 24,
            "03-roadmap-releases.csv": 14,
            "04-roadmap-epics.csv": 141,
            "05-roadmap-jalons.csv": 16,
            "07-roadmap-go-nogo.csv": 13,
            "09-roadmap-tests-validation.csv": 125,
            "14-alignement-cdc-v4.10.0.csv": 138,
        }
        for filename, expected in expected_counts.items():
            rows = self._read_csv(self.ROADMAP_23 / filename)
            assert len(rows) == expected
            assert all(None not in row for row in rows)

    def test_historical_specification_versions_are_preserved(self) -> None:
        assert (self.CDC_49 / "VERSION").read_text(encoding="utf-8").strip() == "4.9.0"
        assert (self.ROADMAP_22 / "VERSION").read_text(encoding="utf-8").strip() == "2.2.0"
        assert len(self._read_csv(self.CDC_49 / "11-Matrices/Exigences.csv")) == 845
        assert len(self._read_csv(self.CDC_49 / "11-Matrices/Tests.csv")) == 645
        assert len(self._read_csv(self.CDC_49 / "11-Matrices/Traceabilite.csv")) == 822
        assert len(self._read_csv(self.ROADMAP_22 / "02-roadmap-phases.csv")) == 23
        assert len(self._read_csv(self.ROADMAP_22 / "04-roadmap-epics.csv")) == 137
        assert len(self._read_csv(self.ROADMAP_22 / "07-roadmap-go-nogo.csv")) == 12

    def test_rel13_alignment_is_complete_and_referentially_valid(self) -> None:
        alignment = self._read_csv(self.ROADMAP_23 / "14-alignement-cdc-v4.10.0.csv")
        rel13 = {
            str(row["cdc_decision_id"]): row
            for row in alignment
            if re.fullmatch(r"REQ-008(?:4[6-9]|5[0-9])", str(row["cdc_decision_id"]))
        }
        assert set(rel13) == {f"REQ-{number:05d}" for number in range(846, 860)}
        assert all(row["phase"] == "P23" for row in rel13.values())
        assert all(row["release"] == "REL-13" for row in rel13.values())

    def test_gate12_workflow_enforces_complete_release_contract(self) -> None:
        workflow = (
            self.PROJECT_ROOT / ".github/workflows/offline-runtime-licensing.yml"
        ).read_text(encoding="utf-8")
        for token in (
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/setup-node@v6",
            "validate_runtime_licensing.py",
            "OpenInfra-Roadmap-Developpement-v2.3/scripts/validate_roadmap.py",
            "ruff format --check",
            "mypy src/openinfra",
            "bandit -q -r src/openinfra",
            "python -m pytest",
            "npm audit --audit-level=high",
            "openinfra-gate12",
            "--enforce",
            "python -m build",
            "python -m twine check",
            "scripts/verify_artifact.py",
            "scripts/smoke_installed_wheel.py",
            "python -m pip_audit --strict",
        ):
            assert token in workflow
        assert "OpenInfra-CDC-SFG-STG-v4.9.0" not in workflow
        assert "OpenInfra-Roadmap-Developpement-v2.2" not in workflow
