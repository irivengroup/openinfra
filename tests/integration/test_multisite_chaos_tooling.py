from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

import pytest
from scripts.assemble_multisite_chaos_evidence import assemble_multisite_chaos_evidence
from scripts.certify_multisite_chaos import certify_multisite_chaos
from scripts.run_multisite_chaos_campaign import ChaosHarness
from scripts.validate_multisite_chaos import MultisiteChaosProjectValidator

from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.quality.multisite_chaos import MultisiteChaosCampaignEvidence

ROOT = Path(__file__).resolve().parents[2]


def _write_reports(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in MultisiteChaosCampaignEvidence.required_scenarios():
        payload = {
            "scenario": name,
            "started_at": "2026-07-14T10:00:00+00:00",
            "completed_at": "2026-07-14T10:01:00+00:00",
            "fault_injected": True,
            "controlled_degradation": True,
            "recovery_completed": True,
            "rollback_verified": True,
            "data_integrity_verified": True,
            "corruption_detected": False,
            "acknowledged_work_lost": False,
            "recovery_seconds": 10,
            "availability_ratio": 1.0,
            "error_rate": 0.0,
            "probe_count": 30,
            "integrity_sha256_before": "a" * 64,
            "integrity_sha256_after": "a" * 64,
        }
        (directory / f"{name}.json").write_text(
            json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
        )


def test_multisite_chaos_assembler_certifier_and_project_contract(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_reports(reports)
    evidence = assemble_multisite_chaos_evidence(
        profile_path=ROOT / "docs/operations/multisite-chaos-profile.json",
        topology_id="enterprise-eu-west",
        reports_directory=reports,
    )
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    certification = certify_multisite_chaos(evidence_path)
    project = MultisiteChaosProjectValidator(ROOT).validate()

    assert certification["multisite_chaos_certification"] is True
    assert certification["scenario_count"] == 6
    assert project == {
        "profile_id": "openinfra-multisite-chaos-v1",
        "profile_version": 1,
        "scenario_count": 6,
        "status": "passed",
    }
    assert len(evidence["source_artifacts"]) == 6


def test_multisite_chaos_assembler_rejects_missing_and_mismatched_reports(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_reports(reports)
    (reports / "frontend-loss.json").unlink()
    with pytest.raises(FileNotFoundError):
        assemble_multisite_chaos_evidence(
            profile_path=ROOT / "docs/operations/multisite-chaos-profile.json",
            topology_id="enterprise-eu-west",
            reports_directory=reports,
        )

    _write_reports(reports)
    path = reports / "frontend-loss.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scenario"] = "site-loss"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError, match="scenario mismatch"):
        assemble_multisite_chaos_evidence(
            profile_path=ROOT / "docs/operations/multisite-chaos-profile.json",
            topology_id="enterprise-eu-west",
            reports_directory=reports,
        )


def test_chaos_harness_enforces_fixed_json_protocol_and_file_permissions(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    harness.write_text("#!/bin/sh\nprintf '%s\\n' '{\"status\":\"ok\"}'\n", encoding="utf-8")
    harness.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], _timeout: float) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        action = command[1]
        scenario = command[3]
        if action == "preflight":
            payload = {
                "status": "ok",
                "supported_scenarios": list(MultisiteChaosCampaignEvidence.required_scenarios()),
            }
        elif action == "inject":
            payload = {"status": "ok", "scenario": scenario, "fault_observed": True}
        elif action == "recover":
            payload = {"status": "ok", "scenario": scenario}
        else:
            payload = {"status": "ok", "scenario": scenario, "rollback_verified": True}
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    adapter = ChaosHarness(harness, timeout_seconds=5, command_runner=runner)
    adapter.preflight()
    assert adapter.inject("site-loss")["fault_observed"] is True
    adapter.recover("site-loss")
    assert adapter.verify_recovered("site-loss")["rollback_verified"] is True
    assert [item[1] for item in calls] == ["preflight", "inject", "recover", "verify-recovered"]

    harness.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IWGRP)
    with pytest.raises(ValidationError, match="group/world writable"):
        ChaosHarness(harness, timeout_seconds=5)


def test_chaos_harness_rejects_invalid_response_and_relative_path(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="absolute"):
        ChaosHarness(Path("relative-harness"), timeout_seconds=5)

    harness = tmp_path / "harness"
    harness.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    harness.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def runner(command: tuple[str, ...], _timeout: float) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "not-json", "")

    adapter = ChaosHarness(harness, timeout_seconds=5, command_runner=runner)
    with pytest.raises(OpenInfraError, match="valid JSON"):
        adapter.inject("network-partition")

    mode = harness.stat().st_mode
    assert mode & stat.S_IXUSR
