from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import openinfra.quality.advanced_identity_oracle_promotion as promotion
from openinfra.quality.advanced_identity_oracle_promotion import (
    Gate11AccountResolver,
    Gate11CommandResult,
    Gate11ContractsQualification,
    Gate11CriterionResult,
    Gate11EvidencePolicy,
    Gate11EvidenceReference,
    Gate11HttpProbe,
    Gate11Input,
    Gate11OracleQualification,
    Gate11PromotionAssembler,
    Gate11PromotionDecision,
    Gate11PromotionEvaluator,
    Gate11PromotionManifest,
    Gate11PromotionPolicy,
    Gate11QualificationCli,
    Gate11QualificationError,
    Gate11Report,
    Gate11SamlQualification,
    Gate11SystemdQualification,
    Gate11TeamSyncQualification,
)

CANDIDATE = "openinfra-0.34.3-rc1"
COMMIT = "a" * 40
ENVIRONMENT = "qualification-lab-01"
NOW = datetime(2026, 7, 18, 8, tzinfo=UTC)


class _Runner:
    def __init__(self, results: list[Gate11CommandResult]) -> None:
        self.results = list(results)

    def run(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 300,
        environment: dict[str, str] | None = None,
    ) -> Gate11CommandResult:
        assert command
        assert timeout_seconds > 0
        assert environment is None
        return self.results.pop(0)


class _FakeHttpResponse:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self.raw = raw
        self.status = status

    def __enter__(self) -> _FakeHttpResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.raw


def _report(kind: str, *, generated_at: datetime = NOW) -> dict[str, object]:
    return Gate11Report.build(
        report_kind=kind,
        candidate_id=CANDIDATE,
        source_commit=COMMIT,
        environment_id=ENVIRONMENT,
        checks={"qualified": True},
        details={},
        generated_at=generated_at,
    )


def _single_evidence(
    tmp_path: Path,
    payload: dict[str, object],
    *,
    max_age_hours: int = 24,
) -> tuple[Gate11EvidencePolicy, Gate11PromotionManifest, Path]:
    root = tmp_path / "evidence"
    root.mkdir()
    path = root / "report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    reference = Gate11EvidenceReference(
        "gate11-contracts",
        "advanced-identity-oracle-contracts",
        path.name,
        Gate11Input.sha256_file(path),
    )
    policy = Gate11EvidencePolicy(
        "gate11-contracts", "advanced-identity-oracle-contracts", max_age_hours
    )
    manifest = Gate11PromotionManifest(CANDIDATE, COMMIT, ENVIRONMENT, NOW, (reference,))
    return policy, manifest, root


class TestGate11HttpAndInputEdges:
    def test_http_probe_success_and_response_validation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            promotion.urllib.request,
            "urlopen",
            lambda *_args, **_kwargs: _FakeHttpResponse(b'{"status":"ok"}', 202),
        )
        response = Gate11HttpProbe().fetch("https://openinfra.example.test/health")
        assert response.status_code == 202
        assert response.payload == {"status": "ok"}

        monkeypatch.setattr(
            promotion.urllib.request,
            "urlopen",
            lambda *_args, **_kwargs: _FakeHttpResponse(b"[]"),
        )
        with pytest.raises(Gate11QualificationError, match="root"):
            Gate11HttpProbe().fetch("http://localhost/health")

        monkeypatch.setattr(
            promotion.urllib.request,
            "urlopen",
            lambda *_args, **_kwargs: _FakeHttpResponse(b"\xff"),
        )
        with pytest.raises(Gate11QualificationError, match="UTF-8 JSON"):
            Gate11HttpProbe().fetch("http://127.0.0.1/health")

        monkeypatch.setattr(
            promotion.urllib.request,
            "urlopen",
            lambda *_args, **_kwargs: _FakeHttpResponse(b"x" * 1_048_577),
        )
        with pytest.raises(Gate11QualificationError, match="exceeds"):
            Gate11HttpProbe().fetch("https://openinfra.example.test/health")

        def _raise(*_args: object, **_kwargs: object) -> Any:
            raise OSError("network unavailable")

        monkeypatch.setattr(promotion.urllib.request, "urlopen", _raise)
        with pytest.raises(Gate11QualificationError, match="probe failed"):
            Gate11HttpProbe().fetch("https://openinfra.example.test/health")

    def test_input_missing_files_bad_timestamps_and_platform(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with pytest.raises(Gate11QualificationError, match="ISO-8601"):
            Gate11Input.utc_datetime(None, "generated_at")
        with pytest.raises(Gate11QualificationError, match="ISO-8601"):
            Gate11Input.utc_datetime("not-a-date", "generated_at")
        with pytest.raises(Gate11QualificationError, match="cannot be read"):
            Gate11Input.regular_file(tmp_path / "missing", "missing")

        file_path = tmp_path / "payload"
        file_path.write_bytes(b"payload")
        assert Gate11Input.sha256_file(file_path) == Gate11Input.sha256_bytes(b"payload")

        monkeypatch.setattr(promotion.os, "name", "nt")
        with pytest.raises(Gate11QualificationError, match="POSIX"):
            Gate11AccountResolver.user_ids("openinfra")


class TestGate11QualificationFailureReports:
    def test_contracts_fail_closed_on_missing_catalog_assets(self, tmp_path: Path) -> None:
        (tmp_path / "installers/migrations/postgresql").mkdir(parents=True)
        (tmp_path / "installers/migrations/oracle").mkdir(parents=True)
        (tmp_path / "installers/systemd").mkdir(parents=True)
        (tmp_path / ".github/workflows").mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

        report = Gate11ContractsQualification.run(
            project_root=tmp_path,
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert report["status"] == "failed"
        assert report["checks"]["oracle_manifest_valid"] is False
        assert report["details"]["oracle_manifest_entry_count"] == 0

    def test_oracle_and_saml_return_failed_reports_for_invalid_live_results(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "oracle"
        root.mkdir()
        (root / "manifest.json").write_text("{}", encoding="utf-8")
        (root / "0001_bootstrap.sql").write_text("SELECT 1 FROM dual;", encoding="utf-8")
        oracle_runner = _Runner(
            [
                Gate11CommandResult(0, '{"backend":"postgresql","newly_applied":null}', ""),
                Gate11CommandResult(
                    0,
                    '{"backend":"postgresql","expected_count":2,"applied_count":0,'
                    '"current":false,"drift":["0001"]}',
                    "",
                ),
            ]
        )
        oracle_report = Gate11OracleQualification.run(
            runner=oracle_runner,  # type: ignore[arg-type]
            openinfra_binary="openinfra",
            migrations_root=root,
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert oracle_report["status"] == "failed"
        assert oracle_report["details"]["newly_applied_count"] == 0

        request = tmp_path / "saml.json"
        request.write_text("{}", encoding="utf-8")
        request.chmod(0o600)
        saml_report = Gate11SamlQualification.run(
            runner=_Runner([Gate11CommandResult(0, "{}", "")]),  # type: ignore[arg-type]
            openinfra_binary="openinfra",
            request_json=request,
            backend="oracle",
            tenant="default",
            edition="enterprise",
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert saml_report["status"] == "failed"
        assert saml_report["details"]["subject_sha256"] == ""
        assert saml_report["details"]["role_count"] == 0

    def test_team_sync_detects_source_fingerprint_and_counter_failures(
        self, tmp_path: Path
    ) -> None:
        token = tmp_path / "token"
        token.write_text("secret", encoding="utf-8")
        token.chmod(0o400)
        first = {"source_id": "wrong", "fingerprint": "one"}
        second = {"source_id": "wrong", "fingerprint": "two"}
        report = Gate11TeamSyncQualification.run(
            runner=_Runner(  # type: ignore[arg-type]
                [
                    Gate11CommandResult(0, json.dumps(first), ""),
                    Gate11CommandResult(0, json.dumps(second), ""),
                ]
            ),
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
        assert report["status"] == "failed"
        assert report["checks"] == {
            "source_id_matches": False,
            "fingerprint_stable": False,
            "second_run_idempotent": False,
            "counters_are_non_negative": False,
        }

    def test_systemd_state_branches_and_failed_runtime_report(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert Gate11SystemdQualification._service_state_ok(
            "openinfra.service", {"ActiveState": "active", "SubState": "running"}
        )
        assert Gate11SystemdQualification._service_state_ok(
            "openinfra-team-sync.timer", {"ActiveState": "active", "SubState": "waiting"}
        )
        assert Gate11SystemdQualification._service_state_ok(
            "openinfra-runtime-secrets.service", {"ActiveState": "active", "Result": "success"}
        )
        assert Gate11SystemdQualification._service_state_ok(
            "openinfra-migrate.service", {"Result": "success", "ExecMainStatus": "0"}
        )
        assert not Gate11SystemdQualification._service_state_ok(
            "openinfra-web.service", {"ActiveState": "failed", "SubState": "dead"}
        )

        values = {
            "LoadState": "not-found",
            "ActiveState": "failed",
            "SubState": "dead",
            "Result": "failed",
            "UnitFileState": "disabled",
            "User": "wrong",
            "Group": "wrong",
            "NoNewPrivileges": "no",
            "PrivateTmp": "no",
            "ProtectSystem": "no",
            "ProtectHome": "no",
            "ExecMainStatus": "1",
        }
        monkeypatch.setattr(
            Gate11SystemdQualification,
            "_unit_properties",
            staticmethod(lambda _runner, _unit: dict(values)),
        )
        monkeypatch.setattr(Gate11AccountResolver, "user_ids", staticmethod(lambda _user: (0, 0)))

        secret_directory = tmp_path / "secrets"
        secret_directory.mkdir()
        secret_directory.chmod(0o755)
        token_file = secret_directory / "token"
        token_file.write_text("token", encoding="utf-8")
        token_file.chmod(0o644)

        class _Http:
            responses = [
                promotion.Gate11HttpResponse(503, {"status": "failed"}),
                promotion.Gate11HttpResponse(503, {"ready": False}),
            ]

            def fetch(self, _url: str, *, timeout_seconds: int = 10) -> Any:
                assert timeout_seconds == 10
                return self.responses.pop(0)

        report = Gate11SystemdQualification.run(
            runner=_Runner([]),  # type: ignore[arg-type]
            http_probe=_Http(),  # type: ignore[arg-type]
            health_url="http://localhost/health",
            ready_url="http://localhost/ready",
            secret_directory=secret_directory,
            token_file=token_file,
            service_user="openinfra",
            candidate_id=CANDIDATE,
            source_commit=COMMIT,
            environment_id=ENVIRONMENT,
        )
        assert report["status"] == "failed"
        assert report["checks"]["systemd_units_loaded_and_enabled"] is False
        assert report["checks"]["systemd_unit_states_valid"] is False
        assert report["checks"]["systemd_hardening_active"] is False
        assert report["checks"]["systemd_service_users_valid"] is False
        assert report["checks"]["health_endpoint_ready"] is False
        assert report["checks"]["readiness_endpoint_ready"] is False
        assert report["checks"]["secret_directory_mode_0700"] is False
        assert report["checks"]["token_mode_0400"] is False


class TestGate11PolicyManifestAndEvaluatorEdges:
    def test_policy_loader_rejects_all_invalid_contract_forms(self, tmp_path: Path) -> None:
        policy_path = tmp_path / "policy.json"
        invalid_payloads = [
            {"schema_version": 2},
            {"schema_version": 1, "gate_id": "OTHER", "release_id": "REL-12"},
            {
                "schema_version": 1,
                "gate_id": "GATE-11",
                "release_id": "REL-12",
                "required_evidence": {},
            },
        ]
        patterns = ("schema", "target", "required_evidence")
        for payload, pattern in zip(invalid_payloads, patterns, strict=True):
            policy_path.write_text(json.dumps(payload), encoding="utf-8")
            with pytest.raises(Gate11QualificationError, match=pattern):
                Gate11PromotionPolicy.load(policy_path)

        with pytest.raises(Gate11QualificationError, match="SHA-256"):
            Gate11EvidenceReference.from_mapping(
                {"id": "x", "report_kind": "x", "path": "x.json", "sha256": "bad"}
            )
        reference = Gate11EvidenceReference("x", "x", "x.json", "0" * 64)
        assert reference.as_dict()["sha256"] == "0" * 64

    def test_manifest_loader_rejects_schema_release_list_and_catalog(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        base: dict[str, object] = {
            "schema_version": 1,
            "gate_id": "GATE-11",
            "release_version": promotion.__version__,
            "candidate_id": CANDIDATE,
            "source_commit": COMMIT,
            "environment_id": ENVIRONMENT,
            "generated_at": NOW.isoformat(),
            "evidence": [],
        }
        cases = [
            ({**base, "schema_version": 2}, "schema"),
            ({**base, "gate_id": "OTHER"}, "metadata"),
            ({**base, "evidence": {}}, "list evidence"),
            (base, "catalog mismatch"),
        ]
        for payload, pattern in cases:
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            with pytest.raises(Gate11QualificationError, match=pattern):
                Gate11PromotionManifest.load(manifest_path)

    def test_assembler_rejects_source_metadata_mismatch(self, tmp_path: Path) -> None:
        sources: dict[str, Path] = {}
        for identifier, kind in Gate11PromotionPolicy.EXPECTED_EVIDENCE.items():
            payload = _report(kind)
            if identifier == "gate11-saml-live":
                payload["candidate_id"] = "other-candidate"
            path = tmp_path / f"{identifier}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            sources[identifier] = path
        with pytest.raises(Gate11QualificationError, match="metadata mismatch"):
            Gate11PromotionAssembler.assemble(
                candidate_id=CANDIDATE,
                source_commit=COMMIT,
                environment_id=ENVIRONMENT,
                sources=sources,
                evidence_root=tmp_path / "evidence",
            )

    @pytest.mark.parametrize(
        ("mutation", "expected_detail"),
        [
            ({"candidate_id": "other"}, "contract mismatch"),
            ({"checks": {}}, "checks are incomplete"),
            ({"failures": ["failure"]}, "qualification failures"),
            ({"generated_at": (NOW + timedelta(minutes=6)).isoformat()}, "future"),
        ],
    )
    def test_evaluator_rejects_invalid_payload_contracts(
        self, tmp_path: Path, mutation: dict[str, object], expected_detail: str
    ) -> None:
        payload = _report("advanced-identity-oracle-contracts")
        payload.update(mutation)
        policy, manifest, root = _single_evidence(tmp_path, payload)
        criterion = Gate11PromotionEvaluator._inspect(
            policy, manifest.evidence[0], manifest, root, NOW
        )
        assert criterion.status == "failed"
        assert expected_detail in criterion.detail

    def test_evaluator_rejects_missing_file_and_empty_decision(self, tmp_path: Path) -> None:
        reference = Gate11EvidenceReference(
            "gate11-contracts",
            "advanced-identity-oracle-contracts",
            "missing.json",
            "0" * 64,
        )
        policy = Gate11EvidencePolicy("gate11-contracts", "advanced-identity-oracle-contracts", 1)
        manifest = Gate11PromotionManifest(CANDIDATE, COMMIT, ENVIRONMENT, NOW, (reference,))
        criterion = Gate11PromotionEvaluator._inspect(policy, reference, manifest, tmp_path, NOW)
        assert criterion.status == "failed"
        assert "missing" in criterion.detail

        decision = Gate11PromotionDecision(CANDIDATE, COMMIT, ENVIRONMENT, NOW, ())
        assert decision.authorized_for_rel12 is False
        assert decision.as_dict()["status"] == "no-go"
        criterion = Gate11CriterionResult("id", "kind", "failed", "detail", "")
        assert criterion.passed is False
        assert criterion.as_dict()["detail"] == "detail"


class TestGate11CliEdges:
    def test_parser_constructs_every_subcommand(self, tmp_path: Path) -> None:
        parser = Gate11QualificationCli._parser()
        common = [
            "--candidate-id",
            CANDIDATE,
            "--source-commit",
            COMMIT,
            "--environment-id",
            ENVIRONMENT,
        ]
        output = ["--output", str(tmp_path / "out.json")]
        request = tmp_path / "request.json"
        token = tmp_path / "token"
        inputs = [
            ["contracts", *common, "--project-root", str(tmp_path), *output],
            ["oracle", *common, "--migrations-root", str(tmp_path), *output],
            ["saml", *common, "--backend", "oracle", "--request-json", str(request), *output],
            [
                "team-sync",
                *common,
                "--backend",
                "postgresql",
                "--source",
                "ldap-main",
                "--token-file",
                str(token),
                *output,
            ],
            ["systemd", *common, *output],
            [
                "assemble",
                *common,
                "--contracts",
                str(request),
                "--oracle",
                str(request),
                "--saml",
                str(request),
                "--team-sync",
                str(request),
                "--systemd",
                str(request),
                "--evidence-root",
                str(tmp_path),
                *output,
            ],
            [
                "evaluate",
                "--policy",
                str(request),
                "--manifest",
                str(request),
                "--evidence-root",
                str(tmp_path),
                *output,
            ],
        ]
        assert [parser.parse_args(arguments).command for arguments in inputs] == [
            "contracts",
            "oracle",
            "saml",
            "team-sync",
            "systemd",
            "assemble",
            "evaluate",
        ]

    def test_dispatch_routes_all_commands(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        sentinel = {"status": "passed"}
        monkeypatch.setattr(
            Gate11ContractsQualification, "run", classmethod(lambda cls, **kwargs: sentinel)
        )
        monkeypatch.setattr(
            Gate11OracleQualification, "run", classmethod(lambda cls, **kwargs: sentinel)
        )
        monkeypatch.setattr(
            Gate11SamlQualification, "run", classmethod(lambda cls, **kwargs: sentinel)
        )
        monkeypatch.setattr(
            Gate11TeamSyncQualification, "run", classmethod(lambda cls, **kwargs: sentinel)
        )
        monkeypatch.setattr(
            Gate11SystemdQualification, "run", classmethod(lambda cls, **kwargs: sentinel)
        )
        monkeypatch.setattr(
            Gate11PromotionAssembler, "assemble", classmethod(lambda cls, **kwargs: sentinel)
        )
        monkeypatch.setattr(
            Gate11PromotionPolicy,
            "load",
            classmethod(lambda cls, path: Gate11PromotionPolicy(())),
        )
        empty_manifest = Gate11PromotionManifest(CANDIDATE, COMMIT, ENVIRONMENT, NOW, ())
        monkeypatch.setattr(
            Gate11PromotionManifest,
            "load",
            classmethod(lambda cls, path: empty_manifest),
        )
        monkeypatch.setattr(
            Gate11PromotionEvaluator,
            "evaluate",
            classmethod(
                lambda cls, **kwargs: Gate11PromotionDecision(
                    CANDIDATE,
                    COMMIT,
                    ENVIRONMENT,
                    NOW,
                    (Gate11CriterionResult("id", "kind", "passed", "ok", "0" * 64),),
                )
            ),
        )

        base = {
            "candidate_id": CANDIDATE,
            "source_commit": COMMIT,
            "environment_id": ENVIRONMENT,
        }
        namespaces = [
            argparse.Namespace(command="contracts", project_root=tmp_path, **base),
            argparse.Namespace(
                command="oracle",
                openinfra_binary="openinfra",
                migrations_root=tmp_path,
                timeout_seconds=1,
                **base,
            ),
            argparse.Namespace(
                command="saml",
                openinfra_binary="openinfra",
                request_json=tmp_path / "request",
                backend="oracle",
                tenant="default",
                edition="enterprise",
                timeout_seconds=1,
                **base,
            ),
            argparse.Namespace(
                command="team-sync",
                openinfra_binary="openinfra",
                token_file=tmp_path / "token",
                source="ldap-main",
                backend="oracle",
                tenant="default",
                edition="enterprise",
                timeout_seconds=1,
                **base,
            ),
            argparse.Namespace(
                command="systemd",
                health_url="http://localhost/health",
                ready_url="http://localhost/ready",
                secret_directory=tmp_path,
                token_file=tmp_path / "token",
                service_user="openinfra",
                **base,
            ),
            argparse.Namespace(
                command="assemble",
                contracts=tmp_path / "one",
                oracle=tmp_path / "two",
                saml=tmp_path / "three",
                team_sync=tmp_path / "four",
                systemd=tmp_path / "five",
                evidence_root=tmp_path,
                **base,
            ),
            argparse.Namespace(
                command="evaluate",
                policy=tmp_path / "policy",
                manifest=tmp_path / "manifest",
                evidence_root=tmp_path,
            ),
        ]
        reports = [Gate11QualificationCli._dispatch(namespace) for namespace in namespaces]
        assert all(report.get("status") in {"passed", "go"} for report in reports)
        with pytest.raises(Gate11QualificationError, match="unsupported"):
            Gate11QualificationCli._dispatch(argparse.Namespace(command="unknown", **base))

    def test_main_writes_output_and_enforces_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        class _Parser:
            def __init__(self, args: argparse.Namespace) -> None:
                self.args = args

            def parse_args(self) -> argparse.Namespace:
                return self.args

            def error(self, message: str) -> None:
                raise RuntimeError(message)

        output = tmp_path / "decision.json"
        args = argparse.Namespace(output=output, enforce=True)
        monkeypatch.setattr(
            Gate11QualificationCli, "_parser", classmethod(lambda cls: _Parser(args))
        )
        monkeypatch.setattr(
            Gate11QualificationCli,
            "_dispatch",
            classmethod(lambda cls, parsed: {"status": "failed"}),
        )
        assert Gate11QualificationCli.main() == 2
        assert json.loads(output.read_text(encoding="utf-8"))["status"] == "failed"
        assert '"status": "failed"' in capsys.readouterr().out

        monkeypatch.setattr(
            Gate11QualificationCli,
            "_dispatch",
            classmethod(lambda cls, parsed: {"authorized_for_rel12": True, "status": "go"}),
        )
        assert Gate11QualificationCli.main() == 0

        monkeypatch.setattr(
            Gate11QualificationCli,
            "_dispatch",
            classmethod(lambda cls, parsed: (_ for _ in ()).throw(Gate11QualificationError("bad"))),
        )
        with pytest.raises(RuntimeError, match="bad"):
            Gate11QualificationCli.main()
