from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from openinfra.quality.contract_completeness_promotion import (
    ContractProofRegistry,
    Gate14Qualification,
    Gate14QualificationCli,
    ProofLevel,
    PytestSelectorResolver,
    RepositoryHygieneScanner,
)

ROOT = Path(__file__).parents[2]
REGISTRY = ROOT / "docs/release/contract-proof-registry-v4.12.csv"
CDC = ROOT / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0"


def test_registry_evidence_files_are_confined_and_existing() -> None:
    proofs = ContractProofRegistry.load(REGISTRY)
    evidence = {item for proof in proofs for item in proof.evidence_files}
    for relative in evidence:
        path = (ROOT / relative).resolve(strict=True)
        path.relative_to(ROOT.resolve())
        assert path.is_file()


def test_registry_automated_selectors_all_resolve() -> None:
    proofs = ContractProofRegistry.load(REGISTRY)
    selectors = tuple(
        selector
        for proof in proofs
        if proof.level is ProofLevel.AUTOMATED
        for selector in proof.pytest_selectors
    )
    assert len(selectors) == 28
    assert PytestSelectorResolver.validate(ROOT, selectors) == ()


def test_registry_classifies_every_n1_requirement() -> None:
    report = Gate14Qualification().collect(
        project_root=ROOT,
        candidate_id="integration-registry",
        source_commit="c" * 40,
        enforce=True,
    )
    assert report.metrics.unclassified_n1_requirements == 0
    assert report.metrics.missing_proofs == 0


def test_hygiene_scanner_excludes_only_exact_rule_definition_files() -> None:
    failures, scanned = RepositoryHygieneScanner.scan(ROOT)
    assert failures == ()
    assert set(RepositoryHygieneScanner.RULE_DEFINITION_FILES).issubset(scanned)
    assert "src/openinfra/domain/licensing.py" in scanned
    assert "scripts/validate_autonomous_installer.py" in scanned
    assert "web/src/main.jsx" in scanned


def test_gate14_cli_writes_enforced_report(tmp_path: Path) -> None:
    output = tmp_path / "gate14-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openinfra.quality.contract_completeness_promotion",
            "--project-root",
            str(ROOT),
            "--candidate-id",
            "integration-cli",
            "--source-commit",
            "d" * 40,
            "--output",
            str(output),
            "--enforce",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["metrics"]["external_proofs"] == 48

    direct_output = tmp_path / "gate14-direct-report.json"
    assert (
        Gate14QualificationCli.main(
            [
                "--project-root",
                str(ROOT),
                "--candidate-id",
                "integration-direct-cli",
                "--source-commit",
                "e" * 40,
                "--output",
                str(direct_output),
                "--enforce",
            ]
        )
        == 0
    )
    assert json.loads(direct_output.read_text(encoding="utf-8"))["status"] == "passed"

    with pytest.raises(SystemExit) as error:
        Gate14QualificationCli.main(
            [
                "--project-root",
                str(ROOT),
                "--candidate-id",
                "integration-invalid-cli",
                "--source-commit",
                "invalid",
                "--output",
                str(tmp_path / "invalid.json"),
            ]
        )
    assert error.value.code == 2
