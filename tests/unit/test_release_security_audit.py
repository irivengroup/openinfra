from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import openinfra.quality.release_security as release_security_module
from openinfra.quality.release_security import (
    ReleaseSecurityAuditError,
    ReleaseSecurityAuditService,
    ReleaseSecurityControlCatalog,
    SecurityCommandExecutor,
    SecurityControlResult,
    SecurityControlSpec,
    SecurityEvidenceSanitizer,
)


class DeterministicSecurityCommandExecutor(SecurityCommandExecutor):
    def __init__(self, statuses: dict[str, str] | None = None) -> None:
        super().__init__(timeout_seconds=1)
        self._statuses = statuses or {}

    def execute(
        self,
        control: SecurityControlSpec,
        project_root: Path,
        evidence_dir: Path,
        *,
        offline: bool,
    ) -> SecurityControlResult:
        del project_root, evidence_dir
        status = self._statuses.get(control.identifier, "passed")
        if offline and control.network_required:
            status = "not-run"
        return SecurityControlResult(
            identifier=control.identifier,
            category=control.category,
            status=status,
            return_code=0 if status == "passed" else 1,
            duration_ms=1.0,
            command=control.command,
            stdout_path=f"evidence/{control.identifier}.stdout.log",
            stderr_path=f"evidence/{control.identifier}.stderr.log",
            stdout_sha256="a" * 64,
            stderr_sha256="b" * 64,
            network_required=control.network_required,
            detail="deterministic test result",
        )


class TestReleaseSecurityAudit:
    def test_control_requires_identifier_and_command(self) -> None:
        with pytest.raises(ReleaseSecurityAuditError):
            SecurityControlSpec("", "sast", ("bandit",))
        with pytest.raises(ReleaseSecurityAuditError):
            SecurityControlSpec("sast", "sast", ())

    def test_catalog_contains_all_release_controls(self, tmp_path: Path) -> None:
        controls = ReleaseSecurityControlCatalog.build(
            tmp_path,
            image_ref="openinfra/runtime:0.32.0",
            api_base_url="http://127.0.0.1:8080",
            web_base_url="http://127.0.0.1:2006",
        )

        assert len(controls) == 8
        assert {item.identifier for item in controls} == {
            "repository-secrets-and-workflows",
            "sast-bandit",
            "rbac-authentication-regression",
            "python-dependency-audit",
            "frontend-dependency-audit",
            "container-filesystem-scan",
            "container-image-scan",
            "dynamic-http-security-probe",
        }
        assert (
            "aquasec/trivy:0.72.0@sha256:"
            "cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
            in controls[5].command
        )
        assert controls[3].network_required is True
        assert controls[-1].network_required is False

    def test_certifies_only_when_every_control_passes(self, tmp_path: Path) -> None:
        output = tmp_path / "release-security.json"
        report = ReleaseSecurityAuditService(DeterministicSecurityCommandExecutor()).run(
            tmp_path,
            output,
            tmp_path / "evidence",
            image_ref="openinfra/runtime:0.32.0",
            api_base_url="http://127.0.0.1:8080",
            web_base_url="http://127.0.0.1:2006",
            offline=False,
        )

        assert report["release_security_certification"] is True
        assert report["complete"] is True
        assert report["failures"] == []
        assert json.loads(output.read_text(encoding="utf-8")) == report

    def test_refuses_failed_or_incomplete_audit(self, tmp_path: Path) -> None:
        failed = ReleaseSecurityAuditService(
            DeterministicSecurityCommandExecutor({"sast-bandit": "failed"})
        ).run(
            tmp_path,
            tmp_path / "failed.json",
            tmp_path / "evidence-failed",
            image_ref="openinfra/runtime:0.32.0",
            api_base_url="http://127.0.0.1:8080",
            web_base_url="http://127.0.0.1:2006",
            offline=False,
        )
        offline = ReleaseSecurityAuditService(DeterministicSecurityCommandExecutor()).run(
            tmp_path,
            tmp_path / "offline.json",
            tmp_path / "evidence-offline",
            image_ref="openinfra/runtime:0.32.0",
            api_base_url="http://127.0.0.1:8080",
            web_base_url="http://127.0.0.1:2006",
            offline=True,
        )

        assert failed["release_security_certification"] is False
        assert failed["complete"] is True
        assert "sast-bandit: failed" in str(failed["failures"])
        assert offline["release_security_certification"] is False
        assert offline["complete"] is False
        assert offline["offline_mode"] is True

    def test_evidence_sanitizer_redacts_tokens_passwords_and_matches(self) -> None:
        github_token = "ghp_" + "A" * 40
        payload = (
            f"token={github_token}\n"
            '"Match": "super-secret-value",\n'
            "https://user:password@example.test/path\n"
        ).encode()

        sanitized = SecurityEvidenceSanitizer.sanitize(payload).decode()

        assert github_token not in sanitized
        assert "super-secret-value" not in sanitized
        assert "user:password@" not in sanitized
        assert sanitized.count("<redacted") >= 3

    def test_command_executor_records_digests_and_failures(self, tmp_path: Path) -> None:
        passed = SecurityCommandExecutor(timeout_seconds=10).execute(
            SecurityControlSpec(
                "pass",
                "test",
                (sys.executable, "-c", "print('secure')"),
            ),
            tmp_path,
            tmp_path / "evidence",
            offline=False,
        )
        failed = SecurityCommandExecutor(timeout_seconds=10).execute(
            SecurityControlSpec(
                "fail",
                "test",
                (sys.executable, "-c", "raise SystemExit(7)"),
            ),
            tmp_path,
            tmp_path / "evidence",
            offline=False,
        )

        assert passed.passed is True
        assert passed.return_code == 0
        assert passed.stdout_sha256 != "0" * 64
        assert failed.passed is False
        assert failed.return_code == 7

    def test_command_executor_reports_unavailable_tool_and_offline_skip(
        self, tmp_path: Path
    ) -> None:
        unavailable = SecurityCommandExecutor(timeout_seconds=10).execute(
            SecurityControlSpec("missing", "test", ("definitely-not-installed-openinfra",)),
            tmp_path,
            tmp_path / "evidence",
            offline=False,
        )
        skipped = SecurityCommandExecutor(timeout_seconds=10).execute(
            SecurityControlSpec("network", "test", ("tool",), network_required=True),
            tmp_path,
            tmp_path / "evidence",
            offline=True,
        )

        assert unavailable.status == "unavailable"
        assert skipped.status == "not-run"
        assert skipped.return_code is None


class RenamingSecurityCommandExecutor(DeterministicSecurityCommandExecutor):
    def execute(
        self,
        control: SecurityControlSpec,
        project_root: Path,
        evidence_dir: Path,
        *,
        offline: bool,
    ) -> SecurityControlResult:
        result = super().execute(control, project_root, evidence_dir, offline=offline)
        if control.identifier != "sast-bandit":
            return result
        return SecurityControlResult(
            identifier="unexpected-control",
            category=result.category,
            status=result.status,
            return_code=result.return_code,
            duration_ms=result.duration_ms,
            command=result.command,
            stdout_path=result.stdout_path,
            stderr_path=result.stderr_path,
            stdout_sha256=result.stdout_sha256,
            stderr_sha256=result.stderr_sha256,
            network_required=result.network_required,
            detail=result.detail,
        )


class TestReleaseSecurityAuditEdgeCases:
    def test_command_executor_rejects_non_positive_timeout(self) -> None:
        with pytest.raises(ReleaseSecurityAuditError, match="timeout must be positive"):
            SecurityCommandExecutor(timeout_seconds=0)

    def test_command_executor_reports_timeout_and_sanitizes_partial_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def timeout_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            del args, kwargs
            raise subprocess.TimeoutExpired(
                cmd=("security-tool",),
                timeout=0.01,
                output="password=secret-value",
                stderr="token=secret-token",
            )

        monkeypatch.setattr(subprocess, "run", timeout_run)
        result = SecurityCommandExecutor(timeout_seconds=0.01).execute(
            SecurityControlSpec("timeout", "test", ("security-tool",)),
            tmp_path,
            tmp_path / "evidence",
            offline=False,
        )

        assert result.status == "timeout"
        assert result.return_code is None
        assert "0.01 seconds" in result.detail
        assert "secret-value" not in (tmp_path / result.stdout_path).read_text()
        assert "secret-token" not in (tmp_path / result.stderr_path).read_text()

    def test_command_executor_records_absolute_paths_outside_project(self, tmp_path: Path) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        evidence_dir = tmp_path / "external-evidence"

        result = SecurityCommandExecutor(timeout_seconds=10).execute(
            SecurityControlSpec("external", "test", (sys.executable, "-c", "print('ok')")),
            project_root,
            evidence_dir,
            offline=False,
        )

        assert Path(result.stdout_path).is_absolute()
        assert Path(result.stderr_path).is_absolute()

    def test_catalog_integrity_guard_rejects_modified_required_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            release_security_module,
            "_REQUIRED_CONTROL_IDS",
            frozenset({"unexpected-control"}),
        )

        with pytest.raises(ReleaseSecurityAuditError, match="catalog is incomplete"):
            ReleaseSecurityControlCatalog.build(
                tmp_path,
                image_ref="openinfra/runtime:0.32.0",
                api_base_url="http://127.0.0.1:8080",
                web_base_url="http://127.0.0.1:2006",
            )

    def test_report_marks_renamed_required_control_as_missing(self, tmp_path: Path) -> None:
        report = ReleaseSecurityAuditService(RenamingSecurityCommandExecutor()).run(
            tmp_path,
            tmp_path / "missing.json",
            tmp_path / "evidence",
            image_ref="openinfra/runtime:0.32.0",
            api_base_url="http://127.0.0.1:8080",
            web_base_url="http://127.0.0.1:2006",
            offline=False,
        )

        assert report["release_security_certification"] is False
        assert report["complete"] is False
        assert "missing required control: sast-bandit" in report["failures"]
