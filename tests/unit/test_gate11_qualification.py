from __future__ import annotations

import json
import os
import pwd
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.quality.advanced_identity_oracle_promotion import (
    Gate11CommandResult,
    Gate11CommandRunner,
    Gate11ContractsQualification,
    Gate11EvidencePolicy,
    Gate11EvidenceReference,
    Gate11HttpProbe,
    Gate11HttpResponse,
    Gate11Input,
    Gate11OracleQualification,
    Gate11PromotionAssembler,
    Gate11PromotionEvaluator,
    Gate11PromotionManifest,
    Gate11PromotionPolicy,
    Gate11QualificationError,
    Gate11Report,
    Gate11SamlQualification,
    Gate11SystemdQualification,
    Gate11TeamSyncQualification,
)

CANDIDATE = "openinfra-0.34.6-rc1"
COMMIT = "a" * 40
ENVIRONMENT = "qualification-lab-01"


class _Runner(Gate11CommandRunner):
    def __init__(self, results: list[Gate11CommandResult]) -> None:
        self.results = list(results)
        self.commands: list[list[str]] = []

    def run(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 300,
        environment: dict[str, str] | None = None,
    ) -> Gate11CommandResult:
        self.commands.append(command)
        assert timeout_seconds > 0
        assert environment is None
        if not self.results:
            raise AssertionError("unexpected command")
        return self.results.pop(0)


class _Http(Gate11HttpProbe):
    def __init__(self, responses: list[Gate11HttpResponse]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def fetch(self, url: str, *, timeout_seconds: int = 10) -> Gate11HttpResponse:
        self.urls.append(url)
        assert timeout_seconds == 10
        return self.responses.pop(0)


class TestGate11InputAndReport:
    def test_identifiers_commit_time_and_json_validation(self, tmp_path: Path) -> None:
        assert Gate11Input.identifier("env-01", "environment") == "env-01"
        assert Gate11Input.source_commit("A" * 40) == "a" * 40
        parsed = Gate11Input.utc_datetime("2026-07-18T08:00:00+02:00", "time")
        assert parsed.hour == 6
        assert Gate11Input.json_object('{"ok": true}', "payload") == {"ok": True}
        assert len(Gate11Input.sha256_bytes(b"openinfra")) == 64

        regular = tmp_path / "private.json"
        regular.write_text("{}", encoding="utf-8")
        regular.chmod(0o600)
        assert Gate11Input.regular_file(regular, "private", private=True) == regular

        with pytest.raises(Gate11QualificationError, match="invalid"):
            Gate11Input.identifier("../escape", "environment")
        with pytest.raises(Gate11QualificationError, match="SHA-1"):
            Gate11Input.source_commit("short")
        with pytest.raises(Gate11QualificationError, match="timezone"):
            Gate11Input.utc_datetime("2026-07-18T08:00:00", "time")
        with pytest.raises(Gate11QualificationError, match="valid JSON"):
            Gate11Input.json_object("{", "payload")
        with pytest.raises(Gate11QualificationError, match="root"):
            Gate11Input.json_object("[]", "payload")
        regular.chmod(0o644)
        with pytest.raises(Gate11QualificationError, match="group or others"):
            Gate11Input.regular_file(regular, "private", private=True)
        symlink = tmp_path / "link"
        symlink.symlink_to(regular)
        with pytest.raises(Gate11QualificationError, match="non-symbolic"):
            Gate11Input.regular_file(symlink, "link")

    def test_report_is_fail_closed_and_atomic(self, tmp_path: Path) -> None:
        report = Gate11Report.build(
            report_kind="oracle-live-qualification",
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
            checks={"one": True, "two": False},
            details={"count": 58},
            failures=["explicit failure"],
            generated_at=datetime(2026, 7, 18, tzinfo=UTC),
        )
        assert report["complete"] is False
        assert report["status"] == "failed"
        assert report["failures"] == ["explicit failure", "two failed"]
        output = tmp_path / "report.json"
        Gate11Report.write_atomic(output, report)
        assert json.loads(output.read_text(encoding="utf-8"))["status"] == "failed"
        assert not output.with_suffix(".json.tmp").exists()
        with pytest.raises(Gate11QualificationError, match="contain checks"):
            Gate11Report.build(
                report_kind="x",
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
                checks={},
                details={},
            )


class TestGate11LiveQualifications:
    def test_oracle_qualification_applies_and_verifies_catalog(self, tmp_path: Path) -> None:
        root = tmp_path / "oracle"
        root.mkdir()
        for number in range(1, 4):
            (root / f"{number:04d}_migration.sql").write_text("SELECT 1 FROM dual;\n")
        (root / "manifest.json").write_text('{"schema_version": 1}\n')
        runner = _Runner(
            [
                Gate11CommandResult(
                    0,
                    json.dumps(
                        {
                            "backend": "oracle",
                            "newly_applied": ["0001_migration.sql"],
                        }
                    ),
                    "",
                ),
                Gate11CommandResult(
                    0,
                    json.dumps(
                        {
                            "backend": "oracle",
                            "expected_count": 3,
                            "applied_count": 3,
                            "current": True,
                            "drift": [],
                        }
                    ),
                    "",
                ),
            ]
        )
        report = Gate11OracleQualification.run(
            runner=runner,
            openinfra_binary="/opt/openinfra/venv/bin/openinfra",
            migrations_root=root,
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert report["status"] == "passed"
        assert report["details"]["catalog_count"] == 3
        assert report["details"]["edition"] == "enterprise"
        assert runner.commands[0][1:3] == ["database", "apply-migrations"]
        assert runner.commands[1][1:3] == ["database", "status"]
        for command in runner.commands:
            assert command[command.index("--edition") + 1] == "enterprise"

        failed = _Runner([Gate11CommandResult(2, "", "ORA-01017")])
        with pytest.raises(Gate11QualificationError, match="application failed"):
            Gate11OracleQualification.run(
                runner=failed,
                openinfra_binary="openinfra",
                migrations_root=root,
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
            )

    def test_oracle_qualification_rejects_empty_catalog_and_bad_status(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "oracle"
        root.mkdir()
        (root / "manifest.json").write_text("{}")
        with pytest.raises(Gate11QualificationError, match="empty"):
            Gate11OracleQualification.run(
                runner=_Runner([]),
                openinfra_binary="openinfra",
                migrations_root=root,
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
            )

        (root / "0001_bootstrap.sql").write_text("SELECT 1 FROM dual;")
        runner = _Runner(
            [
                Gate11CommandResult(0, '{"backend":"oracle","newly_applied":[]}', ""),
                Gate11CommandResult(1, "", "status failed"),
            ]
        )
        with pytest.raises(Gate11QualificationError, match="status failed"):
            Gate11OracleQualification.run(
                runner=runner,
                openinfra_binary="openinfra",
                migrations_root=root,
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
            )

    def test_saml_qualification_redacts_token_and_pins_request(self, tmp_path: Path) -> None:
        request = tmp_path / "saml.json"
        request.write_text('{"SAMLResponse":"signed"}', encoding="utf-8")
        request.chmod(0o600)
        payload = {
            "tenant_id": "default",
            "subject": "alice@example.test",
            "provider": "saml",
            "token": "t" * 64,
            "token_prefix": "abcdef123456",
            "roles": ["admin"],
            "mapped_groups": ["saml-admins"],
            "external_group_count": 2,
        }
        runner = _Runner([Gate11CommandResult(0, json.dumps(payload), "")])
        report = Gate11SamlQualification.run(
            runner=runner,
            openinfra_binary="openinfra",
            request_json=request,
            backend="oracle",
            tenant="default",
            edition="enterprise",
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        serialized = json.dumps(report)
        assert report["status"] == "passed"
        assert "t" * 64 not in serialized
        assert report["details"]["role_count"] == 1
        assert report["details"]["subject_sha256"] != payload["subject"]
        assert "--request-json" in runner.commands[0]

        failed = _Runner([Gate11CommandResult(2, "", "signature rejected")])
        with pytest.raises(Gate11QualificationError, match="signature rejected"):
            Gate11SamlQualification.run(
                runner=failed,
                openinfra_binary="openinfra",
                request_json=request,
                backend="postgresql",
                tenant="default",
                edition="pro",
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
            )

    def test_team_sync_requires_second_run_without_mutation(self, tmp_path: Path) -> None:
        token = tmp_path / "token"
        token.write_text("x" * 40)
        token.chmod(0o400)
        first = {
            "source_id": "ldap-main",
            "fingerprint": "f" * 64,
            "created_users": 2,
            "updated_users": 0,
            "deactivated_users": 0,
            "created_groups": 1,
            "updated_groups": 0,
            "added_memberships": 2,
            "removed_memberships": 0,
        }
        second = {**first, "created_users": 0, "created_groups": 0, "added_memberships": 0}
        runner = _Runner(
            [
                Gate11CommandResult(0, json.dumps(first), ""),
                Gate11CommandResult(0, json.dumps(second), ""),
            ]
        )
        report = Gate11TeamSyncQualification.run(
            runner=runner,
            openinfra_binary="openinfra",
            token_file=token,
            source="ldap-main",
            backend="oracle",
            tenant="default",
            edition="enterprise",
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert report["status"] == "passed"
        assert report["checks"]["second_run_idempotent"] is True
        assert report["details"]["second_run"]["created_users"] == 0
        assert len(runner.commands) == 2

        non_idempotent = {**second, "updated_users": 1}
        runner = _Runner(
            [
                Gate11CommandResult(0, json.dumps(first), ""),
                Gate11CommandResult(0, json.dumps(non_idempotent), ""),
            ]
        )
        report = Gate11TeamSyncQualification.run(
            runner=runner,
            openinfra_binary="openinfra",
            token_file=token,
            source="ldap-main",
            backend="postgresql",
            tenant="default",
            edition="pro",
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert report["status"] == "failed"
        assert "second_run_idempotent failed" in report["failures"]

    def test_team_sync_command_failure_and_invalid_counter(self, tmp_path: Path) -> None:
        token = tmp_path / "token"
        token.write_text("x" * 40)
        token.chmod(0o400)
        with pytest.raises(Gate11QualificationError, match="first Team Sync failed"):
            Gate11TeamSyncQualification.run(
                runner=_Runner([Gate11CommandResult(1, "", "source unavailable")]),
                openinfra_binary="openinfra",
                token_file=token,
                source="oauth-main",
                backend="postgresql",
                tenant="default",
                edition="enterprise",
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
            )
        assert Gate11TeamSyncQualification._counter({"created_users": True}, "created_users") == -1
        assert Gate11TeamSyncQualification._counter({}, "created_users") == -1

    def test_systemd_qualification_checks_runtime_and_secret_permissions(
        self, tmp_path: Path
    ) -> None:
        username = pwd.getpwuid(os.getuid()).pw_name
        secret_dir = tmp_path / "secrets"
        secret_dir.mkdir(mode=0o700)
        secret_dir.chmod(0o700)
        token = secret_dir / "bootstrap-token"
        token.write_text("x" * 40)
        token.chmod(0o400)
        outputs: list[Gate11CommandResult] = []
        for unit in (
            *Gate11SystemdQualification.SERVICE_UNITS,
            Gate11SystemdQualification.TIMER_UNIT,
        ):
            is_app = unit in {"openinfra.service", "openinfra-web.service"}
            is_timer = unit.endswith(".timer")
            is_secret = unit == "openinfra-runtime-secrets.service"
            user = "root" if is_secret else username
            if is_app:
                active, substate = "active", "running"
            elif is_timer:
                active, substate = "active", "waiting"
            elif is_secret:
                active, substate = "active", "exited"
            else:
                active, substate = "inactive", "dead"
            unit_file_state = (
                "enabled" if unit in Gate11SystemdQualification.REQUIRED_ENABLED else "disabled"
            )
            values = {
                "LoadState": "loaded",
                "ActiveState": active,
                "SubState": substate,
                "Result": "success",
                "UnitFileState": unit_file_state,
                "User": user,
                "Group": user,
                "NoNewPrivileges": "yes",
                "PrivateTmp": "yes",
                "ProtectSystem": "strict",
                "ProtectHome": "yes",
                "ExecMainStatus": "0",
            }
            outputs.append(
                Gate11CommandResult(
                    0, "\n".join(f"{key}={value}" for key, value in values.items()), ""
                )
            )
        original_users = dict(Gate11SystemdQualification.SERVICE_UNITS)
        Gate11SystemdQualification.SERVICE_UNITS = {
            key: ("root" if value == "root" else username) for key, value in original_users.items()
        }
        try:
            report = Gate11SystemdQualification.run(
                runner=_Runner(outputs),
                http_probe=_Http(
                    [
                        Gate11HttpResponse(200, {"status": "ok"}),
                        Gate11HttpResponse(200, {"ready": True}),
                    ]
                ),
                health_url="http://127.0.0.1:8080/health",
                ready_url="http://127.0.0.1:8080/ready",
                secret_directory=secret_dir,
                token_file=token,
                service_user=username,
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
            )
        finally:
            Gate11SystemdQualification.SERVICE_UNITS = original_users
        assert report["status"] == "passed"
        assert report["checks"]["systemd_hardening_active"] is True
        assert report["checks"]["token_mode_0400"] is True

    def test_systemd_rejects_incomplete_properties(self) -> None:
        runner = _Runner([Gate11CommandResult(0, "LoadState=loaded\n", "")])
        with pytest.raises(Gate11QualificationError, match="incomplete"):
            Gate11SystemdQualification._unit_properties(runner, "openinfra.service")
        runner = _Runner([Gate11CommandResult(1, "", "unit missing")])
        with pytest.raises(Gate11QualificationError, match="unit missing"):
            Gate11SystemdQualification._unit_properties(runner, "openinfra.service")


class TestGate11PromotionEvidence:
    @staticmethod
    def _report(kind: str, now: datetime) -> dict[str, object]:
        return Gate11Report.build(
            report_kind=kind,
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
            checks={"qualified": True},
            details={},
            generated_at=now,
        )

    def _sources(self, tmp_path: Path, now: datetime) -> dict[str, Path]:
        sources: dict[str, Path] = {}
        for identifier, kind in Gate11PromotionPolicy.EXPECTED_EVIDENCE.items():
            path = tmp_path / f"source-{identifier}.json"
            path.write_text(json.dumps(self._report(kind, now)), encoding="utf-8")
            sources[identifier] = path
        return sources

    def test_policy_manifest_assembly_and_go_decision(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 18, 8, tzinfo=UTC)
        policy_path = (
            Path(__file__).parents[2]
            / "docs/release/advanced-identity-oracle-promotion-policy.json"
        )
        policy = Gate11PromotionPolicy.load(policy_path)
        assert len(policy.required_evidence) == 5
        evidence_root = tmp_path / "evidence"
        manifest_payload = Gate11PromotionAssembler.assemble(
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
            sources=self._sources(tmp_path, now),
            evidence_root=evidence_root,
            generated_at=now,
        )
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
        manifest = Gate11PromotionManifest.load(manifest_path)
        decision = Gate11PromotionEvaluator.evaluate(
            policy=policy,
            manifest=manifest,
            evidence_root=evidence_root,
            now=now + timedelta(hours=1),
        )
        assert decision.authorized_for_rel12 is True
        assert decision.as_dict()["status"] == "go"
        assert all(item.passed for item in decision.criteria)
        assert len({item.evidence_sha256 for item in decision.criteria}) == 5

    def test_evaluator_rejects_hash_drift_stale_and_path_escape(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 18, 8, tzinfo=UTC)
        policy = Gate11PromotionPolicy(
            (Gate11EvidencePolicy("gate11-contracts", "advanced-identity-oracle-contracts", 1),)
        )
        evidence_root = tmp_path / "evidence"
        evidence_root.mkdir()
        report = self._report("advanced-identity-oracle-contracts", now - timedelta(hours=2))
        evidence = evidence_root / "report.json"
        evidence.write_text(json.dumps(report), encoding="utf-8")
        reference = Gate11EvidenceReference(
            "gate11-contracts",
            "advanced-identity-oracle-contracts",
            "report.json",
            Gate11Input.sha256_file(evidence),
        )
        manifest = Gate11PromotionManifest(CANDIDATE, COMMIT, ENVIRONMENT, now, (reference,))
        decision = Gate11PromotionEvaluator.evaluate(
            policy=policy,
            manifest=manifest,
            evidence_root=evidence_root,
            now=now,
        )
        assert decision.authorized_for_rel12 is False
        assert "older" in decision.criteria[0].detail

        evidence.write_text("{}", encoding="utf-8")
        decision = Gate11PromotionEvaluator.evaluate(
            policy=policy,
            manifest=manifest,
            evidence_root=evidence_root,
            now=now,
        )
        assert "SHA-256" in decision.criteria[0].detail

        escaped = Gate11EvidenceReference(
            "gate11-contracts",
            "advanced-identity-oracle-contracts",
            "../outside.json",
            "0" * 64,
        )
        manifest = Gate11PromotionManifest(CANDIDATE, COMMIT, ENVIRONMENT, now, (escaped,))
        decision = Gate11PromotionEvaluator.evaluate(
            policy=policy,
            manifest=manifest,
            evidence_root=evidence_root,
            now=now,
        )
        assert "escapes" in decision.criteria[0].detail

    def test_assembler_and_loaders_reject_incomplete_or_mismatched_contracts(
        self, tmp_path: Path
    ) -> None:
        now = datetime(2026, 7, 18, tzinfo=UTC)
        sources = self._sources(tmp_path, now)
        sources.pop("gate11-saml-live")
        with pytest.raises(Gate11QualificationError, match="all GATE-11"):
            Gate11PromotionAssembler.assemble(
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
                sources=sources,
                evidence_root=tmp_path / "evidence",
            )

        bad_policy = tmp_path / "policy.json"
        bad_policy.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate_id": "GATE-11",
                    "release_id": "REL-12",
                    "required_evidence": [],
                }
            )
        )
        with pytest.raises(Gate11QualificationError, match="incomplete"):
            Gate11PromotionPolicy.load(bad_policy)

        with pytest.raises(Gate11QualificationError, match="objects"):
            Gate11EvidencePolicy.from_mapping("invalid")
        with pytest.raises(Gate11QualificationError, match="max_age"):
            Gate11EvidencePolicy.from_mapping(
                {"id": "x", "report_kind": "x", "max_age_hours": True}
            )
        with pytest.raises(Gate11QualificationError, match="objects"):
            Gate11EvidenceReference.from_mapping("invalid")
        with pytest.raises(Gate11QualificationError, match="relative"):
            Gate11EvidenceReference.from_mapping(
                {
                    "id": "x",
                    "report_kind": "x",
                    "path": "/absolute",
                    "sha256": "0" * 64,
                }
            )

    def test_contract_qualification_reports_current_repository(self) -> None:
        root = Path(__file__).parents[2]
        report = Gate11ContractsQualification.run(
            project_root=root,
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert report["details"]["postgresql_migration_count"] == 59
        assert report["details"]["oracle_migration_count"] == 59
        assert report["checks"]["migration_filenames_match"] is True
        assert report["checks"]["gate11_entrypoint_present"] is True
        assert report["checks"]["promotion_policy_requires_enterprise"] is True
        assert report["checks"]["oracle_enterprise_gate_active"] is True
        assert report["details"]["required_edition"] == "enterprise"


class TestGate11CommandRunnerAndHttp:
    def test_command_runner_validates_command_and_timeout(self) -> None:
        runner = Gate11CommandRunner()
        result = runner.run([sys.executable, "-c", "print('ok')"])
        assert result.returncode == 0
        assert result.stdout.strip() == "ok"
        with pytest.raises(Gate11QualificationError, match="cannot be empty"):
            runner.run([])
        with pytest.raises(Gate11QualificationError, match="timeout_seconds"):
            runner.run(["true"], timeout_seconds=0)

    def test_http_probe_rejects_unsafe_url(self) -> None:
        with pytest.raises(Gate11QualificationError, match="HTTPS"):
            Gate11HttpProbe().fetch("http://example.com/health")
