from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openinfra.quality.contract_completeness_promotion import (
    ContractProof,
    ContractProofRegistry,
    Gate14Control,
    Gate14Metrics,
    Gate14Policy,
    Gate14Qualification,
    Gate14QualificationError,
    Gate14Report,
    ProofLevel,
    PytestSelectorResolver,
    RepositoryHygieneScanner,
)

ROOT = Path(__file__).parents[2]


def test_gate14_policy_and_real_project_pass() -> None:
    report = Gate14Qualification().collect(
        project_root=ROOT,
        candidate_id="openinfra-0.34.19-unit",
        source_commit="a" * 40,
        now=datetime(2026, 7, 21, 12, 0, tzinfo=UTC),
        enforce=True,
    )

    assert report.passed is True
    assert report.gate_id == "GATE-14"
    assert report.release_version == "0.34.19"
    assert report.metrics == Gate14Metrics(667, 31, 588, 48, 44, 77, 0, 0)
    assert tuple(control.identifier for control in report.controls) == (
        Gate14Policy.EXPECTED_CONTROLS
    )


def test_gate14_report_serialization_and_atomic_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = Gate14Report(
        1,
        "GATE-14",
        "0.34.19",
        "candidate",
        "b" * 40,
        datetime(2026, 7, 21, 12, 0, tzinfo=UTC),
        Gate14Metrics(667, 31, 588, 48, 44, 77, 0, 0),
        (Gate14Control("CDC-TRACEABILITY", True, "ok", ("evidence",)),),
    )
    output = tmp_path / "reports/gate14.json"

    Gate14Qualification().write(output, report)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["metrics"]["contractual_tests"] == 667
    assert payload["controls"][0]["evidence"] == ["evidence"]

    failed_output = tmp_path / "reports/failed.json"
    with monkeypatch.context() as context:
        context.setattr(os, "fsync", lambda _descriptor: _raise_os_error("fsync failed"))
        with pytest.raises(OSError, match="fsync failed"):
            Gate14Qualification().write(failed_output, report)
    assert not failed_output.exists()
    assert not tuple(failed_output.parent.glob(f".{failed_output.name}.*"))


@pytest.mark.parametrize(
    ("candidate_id", "source_commit", "message"),
    (
        ("", "a" * 40, "candidate_id"),
        ("x" * 161, "a" * 40, "candidate_id"),
        ("candidate", "abc", "SHA-1"),
    ),
)
def test_gate14_invalid_metadata_is_rejected(
    candidate_id: str, source_commit: str, message: str
) -> None:
    with pytest.raises(Gate14QualificationError, match=message):
        Gate14Qualification().collect(
            project_root=ROOT,
            candidate_id=candidate_id,
            source_commit=source_commit,
        )


def test_gate14_invalid_project_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(Gate14QualificationError, match="project root"):
        Gate14Qualification().collect(
            project_root=tmp_path,
            candidate_id="candidate",
            source_commit="a" * 40,
        )

    qualification = Gate14Qualification()
    source_control = qualification._source_control(
        "SOURCE", tmp_path, {"missing.txt": ("required",)}
    )
    assert source_control.passed is False
    assert "missing" in source_control.detail

    invalid_utf8 = tmp_path / "invalid.txt"
    invalid_utf8.write_text("content", encoding="utf-8")
    original_read_text = Path.read_text

    def _read_text_or_fail(path: Path, *args: object, **kwargs: object) -> str:
        if path == invalid_utf8:
            raise OSError("forced read failure")
        return original_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

    with monkeypatch.context() as context:
        context.setattr(Path, "read_text", _read_text_or_fail)
        unreadable_control = qualification._source_control(
            "SOURCE", tmp_path, {"invalid.txt": ("required",)}
        )
    assert unreadable_control.passed is False
    assert "unreadable" in unreadable_control.detail

    missing_token = tmp_path / "missing-token.txt"
    missing_token.write_text("clean", encoding="utf-8")
    token_control = qualification._source_control(
        "SOURCE", tmp_path, {"missing-token.txt": ("required",)}
    )
    assert token_control.passed is False
    assert "missing token" in token_control.detail
    assert qualification._safe_existing_file(tmp_path.resolve(), "/absolute") is False
    assert qualification._safe_existing_file(tmp_path.resolve(), "../escape") is False
    assert qualification._safe_existing_file(tmp_path.resolve(), "missing.txt") is False
    with pytest.raises(Gate14QualificationError, match="CSV is unreadable"):
        qualification._csv_rows(tmp_path / "missing.csv")

    cdc_root = tmp_path / qualification.CDC_ROOT
    matrix_root = cdc_root / "11-Matrices"
    matrix_root.mkdir(parents=True)
    (cdc_root / "VERSION").write_text("4.11.0\n", encoding="utf-8")
    _write_dict_csv(matrix_root / "Exigences.csv", [{"id": "REQ-1"}])
    _write_dict_csv(
        matrix_root / "Traceabilite.csv",
        [{"requirement_id": "REQ-1", "requirement_priority": "N1", "test_id": ""}],
    )
    cdc_control = qualification._cdc_control(tmp_path, ("TST-OTHER",))
    assert cdc_control.passed is False
    assert "expected 861 requirements" in cdc_control.detail
    assert "expected 667 tests" in cdc_control.detail
    assert "expected 861 traceability rows" in cdc_control.detail

    proof = ContractProof(
        "TST-EXTRA",
        ProofLevel.AUTOMATED,
        ("tests/test_sample.py::test_sample", "tests/test_sample.py::test_sample"),
        ("missing-evidence.md",),
        "",
        "covered",
    )
    zero_metrics = Gate14Metrics(0, 0, 0, 0, 0, 0, 0, 0)
    policy = Gate14Policy(1, "GATE-14", "REL-15", Gate14Policy.EXPECTED_CONTROLS, zero_metrics)
    registry_control = qualification._registry_control(
        (proof,), ("TST-MISSING",), policy, Gate14Metrics(1, 1, 0, 0, 2, 1, 1, 1)
    )
    assert registry_control.passed is False
    assert "missing proofs" in registry_control.detail
    assert "unknown proofs" in registry_control.detail
    assert "metrics differ" in registry_control.detail

    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_sample.py").write_text("def test_sample():\n    pass\n", encoding="utf-8")
    pytest_control = qualification._pytest_control(tmp_path, (proof,), policy)
    assert pytest_control.passed is False
    assert "automated proof count" in pytest_control.detail
    assert "pytest selector count" in pytest_control.detail
    assert "pytest selectors must be unique" in pytest_control.detail

    classification_control = qualification._classification_control(tmp_path, (proof,), policy)
    assert classification_control.passed is False
    assert "evidence file is missing or unsafe" in classification_control.detail
    assert "external proof count" not in classification_control.detail
    assert "unclassified N1 requirements" in classification_control.detail

    with monkeypatch.context() as context:
        context.setattr(
            Gate14Qualification,
            "_hygiene_control",
            lambda self, root: Gate14Control("REPOSITORY-HYGIENE", False, "forced", ()),
        )
        with pytest.raises(Gate14QualificationError, match="GATE-14 failed"):
            Gate14Qualification().collect(
                project_root=ROOT,
                candidate_id="forced-failure",
                source_commit="a" * 40,
                enforce=True,
            )


def test_gate14_policy_rejects_invalid_contracts(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    valid = {
        "schema_version": 1,
        "gate_id": "GATE-14",
        "release_id": "REL-15",
        "required_controls": list(Gate14Policy.EXPECTED_CONTROLS),
        "expected_metrics": Gate14Metrics(667, 31, 588, 48, 44, 77, 0, 0).as_dict(),
    }

    with pytest.raises(Gate14QualificationError, match="unreadable"):
        Gate14Policy.load(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(Gate14QualificationError, match="unreadable"):
        Gate14Policy.load(path)
    _write_json(path, {**valid, "schema_version": 2})
    with pytest.raises(Gate14QualificationError, match="unsupported"):
        Gate14Policy.load(path)
    _write_json(path, {**valid, "release_id": "REL-14"})
    with pytest.raises(Gate14QualificationError, match="GATE-14 / REL-15"):
        Gate14Policy.load(path)
    _write_json(path, {**valid, "required_controls": "invalid"})
    with pytest.raises(Gate14QualificationError, match="string list"):
        Gate14Policy.load(path)
    _write_json(path, {**valid, "expected_metrics": []})
    with pytest.raises(Gate14QualificationError, match="must be an object"):
        Gate14Policy.load(path)
    _write_json(path, {**valid, "expected_metrics": {"contractual_tests": -1}})
    with pytest.raises(Gate14QualificationError, match="expected_metrics is invalid"):
        Gate14Policy.load(path)
    _write_json(
        path,
        {**valid, "required_controls": list(reversed(Gate14Policy.EXPECTED_CONTROLS))},
    )

    with pytest.raises(Gate14QualificationError, match="incorrectly ordered"):
        Gate14Policy.load(path)


def test_registry_rejects_invalid_columns(tmp_path: Path) -> None:
    path = tmp_path / "registry.csv"
    with pytest.raises(Gate14QualificationError, match="unreadable"):
        ContractProofRegistry.load(path)
    path.write_text("test_id,level\nTST-1,partial\n", encoding="utf-8")

    with pytest.raises(Gate14QualificationError, match="columns"):
        ContractProofRegistry.load(path)

    empty_id = _registry_row("", "partial", evidence="README.md")
    path = _write_registry(tmp_path, [empty_id])
    with pytest.raises(Gate14QualificationError, match="empty test id"):
        ContractProofRegistry.load(path)

    invalid_level = _registry_row("TST-1", "invalid", evidence="README.md")
    path = _write_registry(tmp_path, [invalid_level])
    with pytest.raises(Gate14QualificationError, match="invalid proof level"):
        ContractProofRegistry.load(path)

    missing_rationale = _registry_row("TST-1", "partial", evidence="README.md")
    missing_rationale["rationale"] = ""
    path = _write_registry(tmp_path, [missing_rationale])
    with pytest.raises(Gate14QualificationError, match="no rationale"):
        ContractProofRegistry.load(path)


def test_registry_rejects_duplicate_test_ids(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _registry_row("TST-1", "partial", evidence="README.md"),
            _registry_row("TST-1", "partial", evidence="CHANGELOG.md"),
        ],
    )

    with pytest.raises(Gate14QualificationError, match="duplicate"):
        ContractProofRegistry.load(path)


def test_registry_rejects_automated_proof_without_selector(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [_registry_row("TST-1", "automated", evidence="README.md")],
    )

    with pytest.raises(Gate14QualificationError, match="no pytest selector"):
        ContractProofRegistry.load(path)


def test_registry_rejects_non_automated_selector(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _registry_row(
                "TST-1",
                "partial",
                selectors="tests/test_sample.py::test_sample",
                evidence="README.md",
            )
        ],
    )

    with pytest.raises(Gate14QualificationError, match="declares pytest selectors"):
        ContractProofRegistry.load(path)


def test_registry_rejects_missing_evidence(tmp_path: Path) -> None:
    path = _write_registry(tmp_path, [_registry_row("TST-1", "partial")])

    with pytest.raises(Gate14QualificationError, match="no evidence file"):
        ContractProofRegistry.load(path)


def test_registry_rejects_external_proof_without_scope(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [_registry_row("TST-1", "external", evidence="README.md")],
    )

    with pytest.raises(Gate14QualificationError, match="no qualification scope"):
        ContractProofRegistry.load(path)


def test_registry_rejects_scope_on_non_external_proof(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            _registry_row(
                "TST-1",
                "partial",
                evidence="README.md",
                scope="external lab",
            )
        ],
    )

    with pytest.raises(Gate14QualificationError, match="declares an external scope"):
        ContractProofRegistry.load(path)


@pytest.mark.parametrize(
    "selector",
    (
        "tests/test_sample.py::test_sample",
        "tests/test_sample.py::TestSample::test_method",
    ),
)
def test_pytest_selector_resolver_accepts_real_nodes(tmp_path: Path, selector: str) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_sample():\n    pass\n\n"
        "class TestSample:\n"
        "    def test_method(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    assert PytestSelectorResolver.validate(tmp_path, (selector,)) == ()


@pytest.mark.parametrize(
    ("selector", "message"),
    (
        ("invalid", "invalid pytest selector"),
        ("../test_sample.py::test_sample", "unsafe pytest selector path"),
        ("tests/missing.py::test_sample", "selector file missing"),
        ("tests/test_sample.py::missing", "pytest function is missing"),
    ),
)
def test_pytest_selector_resolver_rejects_invalid_nodes(
    tmp_path: Path, selector: str, message: str
) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "def test_sample():\n    pass\n\n"
        "class TestSample:\n"
        "    def test_method(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    failures = PytestSelectorResolver.validate(tmp_path, (selector,))

    assert len(failures) == 1
    assert message in failures[0]

    (tests / "bad.py").write_bytes(b"def broken(:\n")
    additional = PytestSelectorResolver.validate(
        tmp_path,
        (
            "tests/bad.py::test_bad",
            "tests/test_sample.py::TestSample::missing",
            "tests/test_sample.py::Missing::test_method",
        ),
    )
    assert len(additional) == 3
    assert "selector source is invalid" in additional[0]
    assert "pytest method is missing" in additional[1]
    assert "pytest class is missing" in additional[2]


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    (
        ("src/openinfra/bad.py", "# " + "TO" + "DO remove\n", "completion marker"),
        ("scripts/bad.py", "token = 'BEGIN PRIVATE KEY'\n", "private key material"),
        ("web/src/bad.js", "const url = '/api/v1/itrm/items';\n", "legacy HTTP alias"),
        ("migrations", "", "obsolete path present"),
    ),
)
def test_repository_hygiene_scanner_detects_real_findings(
    tmp_path: Path, relative: str, content: str, expected: str
) -> None:
    _materialize_scanner_roots(tmp_path)
    target = tmp_path / relative
    if relative == "migrations":
        target.mkdir()
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    failures, _ = RepositoryHygieneScanner.scan(tmp_path)

    assert any(expected in failure for failure in failures)

    missing_root = tmp_path / "missing-root"
    _materialize_scanner_roots(missing_root)
    shutil.rmtree(missing_root / RepositoryHygieneScanner.SCAN_ROOTS[0])
    failures, _ = RepositoryHygieneScanner.scan(missing_root)
    assert any("scan root missing" in failure for failure in failures)

    missing_file = tmp_path / "missing-file"
    _materialize_scanner_roots(missing_file)
    (missing_file / RepositoryHygieneScanner.SCAN_FILES[0]).unlink()
    failures, _ = RepositoryHygieneScanner.scan(missing_file)
    assert any("scan file missing" in failure for failure in failures)

    unreadable = tmp_path / "unreadable"
    _materialize_scanner_roots(unreadable)
    invalid_source = unreadable / "src/openinfra/invalid.py"
    invalid_source.write_bytes(b"\xff")
    failures, _ = RepositoryHygieneScanner.scan(unreadable)
    assert any("unreadable active source" in failure for failure in failures)

    hygiene_control = Gate14Qualification()._hygiene_control(unreadable)
    assert hygiene_control.passed is False


def _write_registry(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "registry.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ContractProofRegistry.FIELD_NAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _registry_row(
    test_id: str,
    level: str,
    *,
    selectors: str = "",
    evidence: str = "",
    scope: str = "",
) -> dict[str, str]:
    return {
        "test_id": test_id,
        "proof_level": level,
        "pytest_selectors": selectors,
        "evidence_files": evidence,
        "qualification_scope": scope,
        "rationale": "explicit rationale",
    }


def _materialize_scanner_roots(root: Path) -> None:
    for relative in RepositoryHygieneScanner.SCAN_ROOTS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in RepositoryHygieneScanner.SCAN_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("clean\n", encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_dict_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _raise_os_error(message: str) -> None:
    raise OSError(message)
