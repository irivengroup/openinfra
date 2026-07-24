from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openinfra import __version__
from openinfra.quality import rsot_canonical_promotion as gate13_module
from openinfra.quality.rsot_canonical_promotion import (
    Gate13Control,
    Gate13Policy,
    Gate13Qualification,
    Gate13QualificationCli,
    Gate13QualificationError,
    Gate13Report,
)

COMMIT = "b" * 40
ROOT = Path(__file__).parents[2]


def test_gate13_policy_and_real_project_pass(tmp_path: Path) -> None:
    policy = Gate13Policy.load(ROOT / Gate13Qualification.POLICY_PATH)
    qualification = Gate13Qualification()
    report = qualification.collect(
        project_root=ROOT,
        candidate_id="openinfra-0.34.22-unit",
        source_commit=COMMIT,
        now=datetime(2026, 7, 21, 12, tzinfo=UTC),
        enforce=True,
    )
    assert report.passed is True
    assert report.gate_id == "GATE-13"
    assert report.release_version == __version__
    assert tuple(control.identifier for control in report.controls) == policy.required_controls
    assert all(control.evidence for control in report.controls)

    output = tmp_path / "gate13" / "report.json"
    qualification.write(output, report)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["source_commit"] == COMMIT
    assert len(payload["controls"]) == 6


@pytest.mark.parametrize(
    ("candidate", "commit", "message"),
    [
        ("", COMMIT, "candidate_id"),
        ("x" * 161, COMMIT, "candidate_id"),
        ("candidate", "abc", "SHA-1"),
    ],
)
def test_gate13_invalid_metadata_is_rejected(candidate: str, commit: str, message: str) -> None:
    with pytest.raises(Gate13QualificationError, match=message):
        Gate13Qualification().collect(
            project_root=ROOT,
            candidate_id=candidate,
            source_commit=commit,
        )


def test_gate13_invalid_policy_is_rejected(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    for payload, message in (
        ("not-json", "unreadable"),
        ("[]", "JSON object"),
        ('{"schema_version": 2}', "schema"),
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-X",
                    "release_id": "REL-14",
                    "required_controls": [],
                }
            ),
            "GATE-13 / REL-14",
        ),
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-13",
                    "release_id": "REL-14",
                    "required_controls": "invalid",
                }
            ),
            "required_controls",
        ),
        (
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-13",
                    "release_id": "REL-14",
                    "required_controls": ["wrong"],
                }
            ),
            "incomplete",
        ),
    ):
        policy_path.write_text(payload, encoding="utf-8")
        with pytest.raises(Gate13QualificationError, match=message):
            Gate13Policy.load(policy_path)


def test_gate13_fails_closed_for_legacy_production_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    (root / "src/openinfra").mkdir(parents=True)
    (root / "installers").mkdir()
    (root / "web/src").mkdir(parents=True)
    legacy = root / "src/openinfra/legacy.py"
    legacy.write_text('ROUTE = "/api/v1/itrm/objects"\n', encoding="utf-8")
    qualification = Gate13Qualification()
    failures, evidence = qualification._scan_production(root)
    assert evidence == ["src/openinfra/legacy.py"]
    assert failures and "legacy RSOT alias" in failures[0]

    failed = Gate13Control("RSOT-CODE", False, "legacy", ("legacy.py",))
    monkeypatch.setattr(qualification, "_code_control", lambda _root: failed)
    report = qualification.collect(
        project_root=ROOT,
        candidate_id="candidate",
        source_commit=COMMIT,
    )
    assert report.passed is False
    with pytest.raises(Gate13QualificationError, match="RSOT-CODE"):
        qualification.collect(
            project_root=ROOT,
            candidate_id="candidate",
            source_commit=COMMIT,
            enforce=True,
        )


def test_gate13_atomic_write_cleanup_and_cli_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qualification = Gate13Qualification()
    report = qualification.collect(
        project_root=ROOT,
        candidate_id="gate13-cli",
        source_commit=COMMIT,
    )
    output = tmp_path / "failed" / "report.json"
    original_dump = gate13_module.json.dump
    monkeypatch.setattr(
        gate13_module.json,
        "dump",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk failure")),
    )
    with pytest.raises(OSError, match="disk failure"):
        qualification.write(output, report)
    assert not output.exists()
    assert not list(output.parent.glob(".report.json.*"))
    monkeypatch.setattr(gate13_module.json, "dump", original_dump)

    successful_output = tmp_path / "success.json"
    assert (
        Gate13QualificationCli.main(
            [
                "--project-root",
                str(ROOT),
                "--candidate-id",
                "gate13-cli",
                "--source-commit",
                COMMIT,
                "--output",
                str(successful_output),
                "--enforce",
            ]
        )
        == 0
    )
    assert json.loads(successful_output.read_text(encoding="utf-8"))["status"] == "passed"

    with pytest.raises(SystemExit) as exc_info:
        Gate13QualificationCli.main(
            [
                "--project-root",
                str(tmp_path / "missing"),
                "--candidate-id",
                "gate13-cli",
                "--source-commit",
                COMMIT,
                "--output",
                str(tmp_path / "missing.json"),
            ]
        )
    assert exc_info.value.code == 2


def test_gate13_serialization_contract() -> None:
    control = Gate13Control("RSOT-CLI", True, "ok", ("evidence",))
    report = Gate13Report(
        1,
        "GATE-13",
        __version__,
        "candidate",
        COMMIT,
        datetime(2026, 7, 21, tzinfo=UTC),
        (control,),
    )
    assert control.as_dict()["evidence"] == ["evidence"]
    assert report.as_dict()["status"] == "passed"


def test_gate13_rejects_policy_control_order_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mismatched = Gate13Policy(
        1,
        "GATE-13",
        "REL-14",
        tuple(reversed(Gate13Policy.EXPECTED_CONTROLS)),
    )
    monkeypatch.setattr(Gate13Policy, "load", classmethod(lambda _cls, _path: mismatched))

    with pytest.raises(Gate13QualificationError, match="does not match its policy"):
        Gate13Qualification().collect(
            project_root=ROOT,
            candidate_id="gate13-policy-drift",
            source_commit=COMMIT,
        )


def test_gate13_evidence_failures_are_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qualification = Gate13Qualification()
    project = tmp_path / "project"
    project.mkdir()

    failures, evidence = qualification._scan_production(project)
    assert evidence == []
    assert len(failures) == 3
    assert all("scan root missing" in failure for failure in failures)

    missing = qualification._source_control(
        "RSOT-TEST",
        project,
        {"missing.txt": ("required",)},
    )
    assert missing.passed is False
    assert "missing.txt missing" in missing.detail

    obsolete_module = project / qualification.OBSOLETE_MODULES[0]
    obsolete_module.parent.mkdir(parents=True, exist_ok=True)
    obsolete_module.write_text("# obsolete compatibility module\n", encoding="utf-8")
    obsolete_control = qualification._code_control(project)
    assert obsolete_control.passed is False
    assert "obsolete module present" in obsolete_control.detail

    evidence_file = project / "evidence.txt"
    evidence_file.write_text("present but incomplete", encoding="utf-8")
    incomplete = qualification._source_control(
        "RSOT-TEST",
        project,
        {"evidence.txt": ("required-token",)},
    )
    assert incomplete.passed is False
    assert "missing token required-token" in incomplete.detail

    source_root = project / "src/openinfra"
    source_root.mkdir(parents=True, exist_ok=True)
    unreadable = source_root / "unreadable.py"
    unreadable.write_text("VALUE = 1\n", encoding="utf-8")
    (project / "installers").mkdir()
    (project / "web/src").mkdir(parents=True)
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path in (unreadable, evidence_file):
            raise OSError("permission denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    scan_failures, _ = qualification._scan_production(project)
    assert scan_failures == ["unreadable production file: src/openinfra/unreadable.py"]

    unreadable_control = qualification._source_control(
        "RSOT-TEST",
        project,
        {"evidence.txt": ("required-token",)},
    )
    assert unreadable_control.passed is False
    assert "evidence.txt unreadable" in unreadable_control.detail
