from __future__ import annotations

import csv
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
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
        "scripts/validate_coverage.py",
        "pip_audit --strict",
        "npm audit --audit-level=high",
        "scripts/verify_artifact.py",
        "scripts/smoke_installed_wheel.py",
        "tests/integration/test_dcim_energy_cooling_services.py",
        "tests/integration/test_contract_functional_bulk_import.py",
        "tests/integration/test_contract_functional_distributed_discovery.py",
        "tests/integration/test_contract_functional_time_travel.py",
        "tests/integration/test_contract_functional_rag_assistant.py",
        "web/tests/bulk-import.test.mjs",
        "web/tests/distributed-discovery.test.mjs",
        "web/tests/time-travel.test.mjs",
        "web/tests/rag-governance.test.mjs",
        "actions/upload-artifact@v6",
    ):
        assert token in workflow
    assert "pull_request_target:" not in workflow


def test_release_contract_versions_are_consistent() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "0.34.19"
    assert (CDC / "VERSION").read_text(encoding="utf-8").strip() == "4.12.0"
    assert (ROADMAP / "VERSION").read_text(encoding="utf-8").strip() == "2.5.0"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.34.19"' in pyproject
    assert "openinfra-gate14" in pyproject
    assert "precision = 8" in pyproject
    assert '"docs/runbooks/ASYNC_BULK_IMPORTS.md" = ' in pyproject
    assert '"docs/runbooks/DISTRIBUTED_DISCOVERY_RESULTS.md" = ' in pyproject
    assert '"docs/runbooks/APPLICATION_CHANGE_IMPACT.md" = ' in pyproject
    assert '"docs/runbooks/RSOT_TIME_TRAVEL.md" = ' in pyproject
    assert '"docs/runbooks/GOVERNED_RAG_ASSISTANT.md" = ' in pyproject
    artifact_verifier = (ROOT / "scripts/verify_artifact.py").read_text(encoding="utf-8")
    wheel_section = artifact_verifier.split("class SourceDistributionVerifier:", 1)[0]
    assert '"openinfra/docs/runbooks/ASYNC_BULK_IMPORTS.md"' in wheel_section
    assert '"openinfra/docs/runbooks/DISTRIBUTED_DISCOVERY_RESULTS.md"' in wheel_section
    assert '"openinfra/docs/runbooks/APPLICATION_CHANGE_IMPACT.md"' in wheel_section
    assert '"openinfra/docs/runbooks/RSOT_TIME_TRAVEL.md"' in wheel_section
    assert '"openinfra/docs/runbooks/GOVERNED_RAG_ASSISTANT.md"' in wheel_section
    installed_smoke = (ROOT / "scripts/smoke_installed_wheel.py").read_text(encoding="utf-8")
    for token in (
        "ASYNC_BULK_IMPORTS.md",
        "DISTRIBUTED_DISCOVERY_RESULTS.md",
        "APPLICATION_CHANGE_IMPACT.md",
        "RSOT_TIME_TRAVEL.md",
        "GOVERNED_RAG_ASSISTANT.md",
        "automated_proofs != 31",
        "partial_proofs != 588",
        "pytest_selectors != 44",
        "evidence_files != 77",
    ):
        assert token in installed_smoke

    with TemporaryDirectory() as directory:
        evidence = Path(directory) / "coverage.json"
        evidence.write_text(
            json.dumps(
                {
                    "totals": {
                        "num_statements": 10_000,
                        "covered_lines": 9_799,
                        "missing_lines": 201,
                    }
                }
            ),
            encoding="utf-8",
        )
        below = subprocess.run(
            [
                sys.executable,
                "scripts/validate_coverage.py",
                "--coverage-json",
                str(evidence),
                "--minimum",
                "98",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert below.returncode == 1
        assert "97.990000000000% < 98.000000000000%" in below.stderr
        evidence.write_text(
            json.dumps(
                {
                    "totals": {
                        "num_statements": 10_000,
                        "covered_lines": 9_800,
                        "missing_lines": 200,
                    }
                }
            ),
            encoding="utf-8",
        )
        exact = subprocess.run(
            [
                sys.executable,
                "scripts/validate_coverage.py",
                "--coverage-json",
                str(evidence),
                "--minimum",
                "98",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert exact.returncode == 0, exact.stderr


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
    assert levels == {"partial": 588, "external": 48, "automated": 31}
    assert len(selectors) == 44
    assert len(evidence) == 77


def test_active_gate14_documents_publish_current_registry_metrics() -> None:
    expected_fragments = {
        ROOT / "docs/runbooks/CONTRACT_COMPLETENESS_PROMOTION.md": (
            "30 preuves automatisées et 43 sélecteurs pytest résolus",
            "589 preuves partielles, 48 externes, 74 fichiers distincts",
        ),
        ROOT / "docs/TRACEABILITY.md": (
            "667 tests : 30 automatisés, 589 partiels, 48 externes",
            "43 sélecteurs pytest, 74 fichiers d’évidence",
        ),
        CDC / "00-Delta-v4.12.md": (
            "30 preuves automatisées, 589 partielles et 48 externes",
            "43 sélecteurs pytest réels",
            "Référencement de 74 fichiers de preuve distincts",
        ),
        CDC / "11-Matrices/Matrice-completude-contractuelle-v4.12.csv": (
            "43 sélecteurs pytest",
            "74 fichiers de preuve",
        ),
        CDC / "11-Matrices/Tests.csv": (
            "667 tests sont classifiés en 30 automatisés, 589 partiels et 48 externes",
            "43 sélecteurs sont résolus, 74 fichiers de preuve existent",
        ),
        ROADMAP / "09-roadmap-tests-validation.csv": (
            "Résoudre les 43 sélecteurs pytest",
            "Valider 589 preuves partielles, 48 externes et 74 fichiers distincts",
        ),
        ROADMAP / "07-roadmap-go-nogo.csv": (
            "30 preuves automatisées; 589 partielles; 48 externes",
            "43 sélecteurs résolus; 74 fichiers de preuve",
        ),
        ROADMAP / "04-roadmap-epics.csv": ("Résolveur AST; 43 sélecteurs",),
    }
    for path, fragments in expected_fragments.items():
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in content, f"{path}: missing current GATE-14 metric {fragment!r}"


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
