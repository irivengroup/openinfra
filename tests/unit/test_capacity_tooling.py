from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
import pytest
from scripts.assemble_enterprise_capacity_evidence import assemble_capacity_evidence
from scripts.run_enterprise_chaos_profile import DockerComposeChaosRunner
from scripts.validate_observability import OpenInfraObservabilityValidator

from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.quality.capacity_certification import EnterpriseCapacityCertification


def _profile() -> dict[str, object]:
    return {
        "profile_id": "openinfra-enterprise-capacity-v1",
        "profile_version": 1,
        "required_capacity_stages": [
            "baseline",
            "step-load",
            "endurance",
            "spike",
            "saturation",
        ],
        "required_chaos_scenarios": [
            "api-worker-loss",
            "web-worker-loss",
            "db-replica-loss",
            "pgbouncer-restart",
        ],
        "thresholds": {
            "p95_ms": 500,
            "p99_ms": 1000,
            "error_rate_percent": 1,
            "saturation_percent": 90,
            "recovery_seconds": 120,
            "memory_growth_percent": 10,
            "replica_lag_seconds": 5,
            "trace_coverage_percent": 99,
        },
    }


def _topology() -> dict[str, object]:
    return {
        "edition": "enterprise",
        "api_instances": 2,
        "web_instances": 2,
        "specialized_workers": 4,
        "database_primaries": 1,
        "database_replicas": 1,
        "pgbouncer_instances": 2,
        "regions": 1,
        "dataset_objects": 100000,
        "dataset_relations": 100000,
        "topology_fingerprint": "f" * 64,
    }


def test_capacity_evidence_assembler_produces_certifiable_document(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    topology = tmp_path / "topology.json"
    stages = tmp_path / "stages"
    chaos = tmp_path / "chaos"
    output = tmp_path / "evidence.json"
    stages.mkdir()
    chaos.mkdir()
    profile.write_text(json.dumps(_profile()), encoding="utf-8")
    topology.write_text(json.dumps(_topology()), encoding="utf-8")
    stage_template = {
        "duration_seconds": 300,
        "requests": 1000,
        "p95_ms": 100,
        "p99_ms": 200,
        "error_rate_percent": 0,
        "saturation_percent": 50,
        "memory_growth_percent": 1,
        "replica_lag_seconds": 0.1,
        "trace_coverage_percent": 100,
        "metrics_complete": True,
        "leak_detected": False,
    }
    for name in _profile()["required_capacity_stages"]:  # type: ignore[union-attr]
        (stages / f"{name}.json").write_text(
            json.dumps({"stage": name, **stage_template}), encoding="utf-8"
        )
    chaos_template = {
        "fault_injected": True,
        "service_recovered": True,
        "recovery_seconds": 10,
        "data_integrity_verified": True,
        "acknowledged_work_lost": False,
    }
    for name in _profile()["required_chaos_scenarios"]:  # type: ignore[union-attr]
        (chaos / f"{name}.json").write_text(
            json.dumps({"scenario": name, **chaos_template}), encoding="utf-8"
        )

    payload = assemble_capacity_evidence(
        profile_path=profile,
        topology_path=topology,
        stage_directory=stages,
        chaos_directory=chaos,
        output_path=output,
    )

    assert len(payload["source_hashes"]) == 11  # type: ignore[arg-type]
    assert EnterpriseCapacityCertification.load(output).evaluate()["capacity_certification"] is True


def test_capacity_evidence_assembler_rejects_mismatched_stage(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    topology = tmp_path / "topology.json"
    stages = tmp_path / "stages"
    chaos = tmp_path / "chaos"
    stages.mkdir()
    chaos.mkdir()
    profile.write_text(json.dumps(_profile()), encoding="utf-8")
    topology.write_text(json.dumps(_topology()), encoding="utf-8")
    (stages / "baseline.json").write_text(json.dumps({"stage": "spike"}), encoding="utf-8")
    with pytest.raises(ValidationError, match="does not identify"):
        assemble_capacity_evidence(
            profile_path=profile,
            topology_path=topology,
            stage_directory=stages,
            chaos_directory=chaos,
            output_path=tmp_path / "out.json",
        )


def test_docker_compose_chaos_runner_verifies_recovery_and_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compose = tmp_path / "compose.yaml"
    compose.write_text("services: {}\n", encoding="utf-8")
    commands: list[tuple[str, ...]] = []

    def command_runner(
        command: list[str] | tuple[str, ...], timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        assert timeout_seconds == 2
        commands.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, "", "")

    def get(url: str, timeout: float) -> httpx.Response:
        assert timeout > 0
        if url.endswith("/health"):
            return httpx.Response(200, content=b"healthy", request=httpx.Request("GET", url))
        return httpx.Response(200, content=b"stable-integrity", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    runner = DockerComposeChaosRunner(
        compose_file=compose,
        project_directory=tmp_path,
        health_url="https://openinfra.example/health",
        integrity_url="https://openinfra.example/api/v1/version",
        timeout_seconds=2,
        command_runner=command_runner,
    )

    report = runner.run("api-worker-loss")

    assert report["fault_injected"] is True
    assert report["service_recovered"] is True
    assert report["data_integrity_verified"] is True
    assert report["acknowledged_work_lost"] is False
    assert any("stop" in command for command in commands)
    assert any("up" in command for command in commands)


def test_docker_compose_chaos_runner_rejects_failed_injection(tmp_path: Path) -> None:
    compose = tmp_path / "compose.yaml"
    compose.write_text("services: {}\n", encoding="utf-8")

    def command_runner(
        command: list[str] | tuple[str, ...], timeout_seconds: float
    ) -> subprocess.CompletedProcess[str]:
        del timeout_seconds
        return subprocess.CompletedProcess(command, 1, "", "denied")

    runner = DockerComposeChaosRunner(
        compose_file=compose,
        project_directory=tmp_path,
        health_url="https://openinfra.example/health",
        integrity_url="https://openinfra.example/api/v1/version",
        timeout_seconds=2,
        command_runner=command_runner,
    )
    runner._integrity_hash = lambda: "a" * 64  # type: ignore[method-assign]
    with pytest.raises(OpenInfraError, match="failed to inject"):
        runner.run("api-worker-loss")


def test_observability_configuration_contract_is_valid() -> None:
    OpenInfraObservabilityValidator(Path()).validate()
