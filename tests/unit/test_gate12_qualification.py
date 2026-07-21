from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openinfra import __version__
from openinfra.quality import offline_licensing_promotion as gate12_module
from openinfra.quality.offline_licensing_promotion import (
    Gate12Control,
    Gate12Policy,
    Gate12Qualification,
    Gate12QualificationCli,
    Gate12QualificationError,
    Gate12Report,
)

COMMIT = "a" * 40


class TestGate12Qualification:
    def test_policy_and_real_project_pass(self, tmp_path: Path) -> None:
        root = Path(__file__).parents[2]
        policy = Gate12Policy.load(
            root / "docs/release/offline-runtime-licensing-promotion-policy.json"
        )
        assert policy.required_controls == Gate12Policy.EXPECTED_CONTROLS

        qualification = Gate12Qualification()
        report = qualification.collect(
            project_root=root,
            candidate_id="openinfra-gate12-unit",
            source_commit=COMMIT,
            now=datetime(2026, 7, 20, 12, tzinfo=UTC),
            enforce=True,
        )
        assert report.passed is True
        assert report.gate_id == "GATE-12"
        assert report.release_version == __version__
        assert report.generated_at == datetime(2026, 7, 20, 12, tzinfo=UTC)
        assert tuple(control.identifier for control in report.controls) == policy.required_controls
        assert all(control.evidence for control in report.controls)

        output = tmp_path / "gate12/report.json"
        qualification.write(output, report)
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["status"] == "passed"
        assert payload["source_commit"] == COMMIT
        assert len(payload["controls"]) == 7
        assert not output.with_name(".report.json.tmp").exists()

    @pytest.mark.parametrize(
        ("candidate", "commit", "message"),
        [
            ("", COMMIT, "candidate_id"),
            ("x" * 161, COMMIT, "candidate_id"),
            ("candidate", "abc", "SHA-1"),
        ],
    )
    def test_invalid_metadata_is_rejected(self, candidate: str, commit: str, message: str) -> None:
        with pytest.raises(Gate12QualificationError, match=message):
            Gate12Qualification().collect(
                project_root=Path(__file__).parents[2],
                candidate_id=candidate,
                source_commit=commit,
            )

    def test_invalid_project_and_policy_are_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(Gate12QualificationError, match="project root"):
            Gate12Qualification().collect(
                project_root=tmp_path,
                candidate_id="candidate",
                source_commit=COMMIT,
            )

        policy_path = tmp_path / "policy.json"
        policy_path.write_text("not-json", encoding="utf-8")
        with pytest.raises(Gate12QualificationError, match="unreadable"):
            Gate12Policy.load(policy_path)
        policy_path.write_text('{"schema_version": 2}', encoding="utf-8")
        with pytest.raises(Gate12QualificationError, match="schema"):
            Gate12Policy.load(policy_path)
        policy_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-X",
                    "release_id": "REL-13",
                    "required_controls": [],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(Gate12QualificationError, match="GATE-12 / REL-13"):
            Gate12Policy.load(policy_path)
        policy_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-12",
                    "release_id": "REL-13",
                    "required_controls": "invalid",
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(Gate12QualificationError, match="required_controls"):
            Gate12Policy.load(policy_path)
        policy_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-12",
                    "release_id": "REL-13",
                    "required_controls": ["wrong"],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(Gate12QualificationError, match="incomplete"):
            Gate12Policy.load(policy_path)

    def test_report_failure_and_enforcement(self, monkeypatch: pytest.MonkeyPatch) -> None:
        qualification = Gate12Qualification()
        failed = Gate12Control("license-domain-cryptography", False, "missing", ())
        monkeypatch.setattr(qualification, "_domain_control", lambda _root: failed)
        report = qualification.collect(
            project_root=Path(__file__).parents[2],
            candidate_id="candidate",
            source_commit=COMMIT,
        )
        assert report.passed is False
        assert report.as_dict()["status"] == "failed"
        with pytest.raises(Gate12QualificationError, match="license-domain-cryptography"):
            qualification.collect(
                project_root=Path(__file__).parents[2],
                candidate_id="candidate",
                source_commit=COMMIT,
                enforce=True,
            )

    def test_control_and_report_serialization(self) -> None:
        control = Gate12Control("control", True, "ok", ("a",))
        report = Gate12Report(
            1,
            "GATE-12",
            __version__,
            "candidate",
            COMMIT,
            datetime(2026, 7, 20, tzinfo=UTC),
            (control,),
        )
        assert control.as_dict() == {
            "id": "control",
            "passed": True,
            "detail": "ok",
            "evidence": ["a"],
        }
        assert report.as_dict()["status"] == "passed"


def test_gate12_internal_failure_paths_and_cli_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    qualification = Gate12Qualification()
    root = Path(__file__).parents[2]
    original = qualification._domain_control
    monkeypatch.setattr(
        qualification,
        "_domain_control",
        lambda project_root: Gate12Control("unexpected-control", True, "ok", (str(project_root),)),
    )
    with pytest.raises(Gate12QualificationError, match="does not match its policy"):
        qualification.collect(
            project_root=root,
            candidate_id="policy-mismatch",
            source_commit=COMMIT,
        )
    monkeypatch.setattr(qualification, "_domain_control", original)

    private_root = tmp_path / "private-material"
    private_root.mkdir()
    (private_root / "authority.pem").write_text("PRIVATE", encoding="utf-8")
    private_control = qualification._security_control(private_root)
    assert private_control.passed is False
    assert "authority.pem" in private_control.detail

    source_root = tmp_path / "source-control"
    source_root.mkdir()
    existing = source_root / "contract.txt"
    existing.write_text("present", encoding="utf-8")
    source_control = qualification._source_control(
        "source-test",
        source_root,
        {
            "missing.txt": ("token",),
            "contract.txt": ("absent-token",),
        },
    )
    assert source_control.passed is False
    assert "missing.txt missing" in source_control.detail
    assert "absent-token" in source_control.detail

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("not-json", encoding="utf-8")
    assert qualification._json(invalid_json) == {}
    invalid_json.write_text("[]", encoding="utf-8")
    assert qualification._json(invalid_json) == {}

    with pytest.raises(SystemExit) as exc_info:
        Gate12QualificationCli.main(
            [
                "--project-root",
                str(tmp_path / "missing-project"),
                "--candidate-id",
                "candidate",
                "--source-commit",
                COMMIT,
                "--output",
                str(tmp_path / "report.json"),
                "--enforce",
            ]
        )
    assert exc_info.value.code == 2


def test_gate12_additional_fail_closed_and_cli_success_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_path = tmp_path / "policy.json"
    policy_path.write_text("[]", encoding="utf-8")
    with pytest.raises(Gate12QualificationError, match="JSON object"):
        Gate12Policy.load(policy_path)

    qualification = Gate12Qualification()
    report = qualification.collect(
        project_root=Path(__file__).parents[2],
        candidate_id="gate12-cli-success",
        source_commit=COMMIT,
    )
    failed_output = tmp_path / "failed" / "report.json"
    original_dump = gate12_module.json.dump
    monkeypatch.setattr(
        gate12_module.json,
        "dump",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk failure")),
    )
    with pytest.raises(OSError, match="disk failure"):
        qualification.write(failed_output, report)
    assert not failed_output.exists()
    assert not list(failed_output.parent.glob(".report.json.*"))
    monkeypatch.setattr(gate12_module.json, "dump", original_dump)

    source_root = tmp_path / "source"
    source_root.mkdir()
    unreadable = source_root / "unreadable.txt"
    unreadable.write_text("required-token", encoding="utf-8")
    original_read_text = Path.read_text

    def fail_selected_read(path: Path, *args: object, **kwargs: object) -> str:
        if path == unreadable:
            raise OSError("unreadable evidence")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_selected_read)
    unreadable_control = qualification._source_control(
        "unreadable-source", source_root, {"unreadable.txt": ("required-token",)}
    )
    assert unreadable_control.passed is False
    assert "unreadable" in unreadable_control.detail
    monkeypatch.setattr(Path, "read_text", original_read_text)

    ignored_root = tmp_path / "ignored"
    ignored_private = ignored_root / "node_modules" / "authority.pem"
    ignored_private.parent.mkdir(parents=True)
    ignored_private.write_text("PRIVATE", encoding="utf-8")
    assert qualification._security_control(ignored_root).passed is True

    output = tmp_path / "cli-report.json"
    assert (
        Gate12QualificationCli.main(
            [
                "--project-root",
                str(Path(__file__).parents[2]),
                "--candidate-id",
                "gate12-cli-success",
                "--source-commit",
                COMMIT,
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "passed"
