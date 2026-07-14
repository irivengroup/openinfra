from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from scripts.run_enterprise_benchmark_suite import (
    load_recommendations,
    load_workload_paths,
    run_benchmark_suite,
)
from scripts.run_enterprise_workload_benchmark import (
    BenchmarkWorkload,
    EnterpriseWorkloadBenchmarkRunner,
)

from openinfra.domain.common import ValidationError

WORKLOADS = ("api", "ipam", "imports", "discovery", "database", "graph")


def _paths() -> dict[str, str]:
    return {name: f"/api/v1/{name}" for name in WORKLOADS}


def _recommendations() -> dict[str, dict[str, float | int]]:
    return {
        name: {"duration_seconds": 1.0, "target_rps": 1.0, "concurrency": 1} for name in WORKLOADS
    }


def test_benchmark_workload_and_runner_validate_untrusted_configuration() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        EnterpriseWorkloadBenchmarkRunner(
            base_url="http://openinfra.example", token="", timeout_seconds=1
        )
    with pytest.raises(ValidationError, match="positive"):
        EnterpriseWorkloadBenchmarkRunner(
            base_url="https://openinfra.example", token="", timeout_seconds=0
        )
    runner = EnterpriseWorkloadBenchmarkRunner(
        base_url="https://openinfra.example", token="", timeout_seconds=1
    )
    invalid = (
        BenchmarkWorkload("unknown", "/health", 1, 1, 1),
        BenchmarkWorkload("api", "https://evil.example", 1, 1, 1),
        BenchmarkWorkload("api", "/health", 0, 1, 1),
        BenchmarkWorkload("api", "/health", 1, 1, 1, (99,)),
        BenchmarkWorkload("api", "/health", 1, 1, 1, (200, 200)),
    )
    for workload in invalid:
        with pytest.raises(ValidationError):
            workload.validate()
    assert runner._percentile([1.0, 2.0, 3.0], 95) == 3.0
    assert runner._percentile([], 95) == 0.0


def test_workload_runner_produces_bounded_read_only_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_request(self, client, semaphore, path, expected_status_codes):
        del self, client, semaphore, path, expected_status_codes
        return 5.0, 200, 32, False

    monkeypatch.setattr(EnterpriseWorkloadBenchmarkRunner, "_request", fake_request)
    runner = EnterpriseWorkloadBenchmarkRunner(
        base_url="https://openinfra.example", token="", timeout_seconds=1
    )
    report = asyncio.run(runner.run(BenchmarkWorkload("api", "/api/v1/version", 0.02, 2, 100)))

    assert report["workload"] == "api"
    assert report["method"] == "GET"
    assert report["requests"] >= 1
    assert report["error_rate_percent"] == 0
    assert report["response_bytes"] >= 32
    assert report["status_counts"] == {"200": report["requests"]}


def test_benchmark_suite_configuration_and_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths_file = tmp_path / "paths.json"
    paths_file.write_text(json.dumps(_paths()), encoding="utf-8")
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(
        json.dumps(
            {
                "required_benchmark_workloads": list(WORKLOADS),
                "benchmark_recommendations": _recommendations(),
            }
        ),
        encoding="utf-8",
    )
    assert load_workload_paths(paths_file) == _paths()
    assert load_recommendations(profile_file) == _recommendations()

    async def fake_run(self, workload):
        del self
        return {
            "workload": workload.name,
            "method": "GET",
            "path": workload.path,
            "duration_seconds": workload.duration_seconds,
            "requests": 1,
            "p95_ms": 1,
            "p99_ms": 1,
            "error_rate_percent": 0,
            "throughput_rps": 1,
            "response_bytes": 1,
            "expected_status_codes": [200],
            "status_counts": {"200": 1},
        }

    monkeypatch.setattr(EnterpriseWorkloadBenchmarkRunner, "run", fake_run)
    output = tmp_path / "benchmarks"
    reports = asyncio.run(
        run_benchmark_suite(
            base_url="https://openinfra.example",
            token="",
            timeout_seconds=1,
            paths=_paths(),
            recommendations=_recommendations(),
            output_directory=output,
            duration_scale=0.1,
        )
    )
    assert [report["workload"] for report in reports] == list(WORKLOADS)
    assert all((output / f"{name}.json").is_file() for name in WORKLOADS)

    with pytest.raises(ValidationError, match="at most one"):
        asyncio.run(
            run_benchmark_suite(
                base_url="https://openinfra.example",
                token="",
                timeout_seconds=1,
                paths=_paths(),
                recommendations=_recommendations(),
                output_directory=output,
                duration_scale=2,
            )
        )


def test_benchmark_suite_rejects_incomplete_configuration(tmp_path: Path) -> None:
    paths = tmp_path / "paths.json"
    paths.write_text(json.dumps({"api": "/api/v1/version"}), encoding="utf-8")
    with pytest.raises(ValidationError, match="contain exactly"):
        load_workload_paths(paths)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(ValidationError, match="root must be an object"):
        load_workload_paths(malformed)

    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "required_benchmark_workloads": list(reversed(WORKLOADS)),
                "benchmark_recommendations": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="workload order"):
        load_recommendations(profile)


def test_capacity_assembler_includes_all_benchmark_hashes(tmp_path: Path) -> None:
    from scripts.assemble_enterprise_capacity_evidence import assemble_capacity_evidence

    profile = tmp_path / "profile.json"
    topology = tmp_path / "topology.json"
    benchmarks = tmp_path / "benchmarks"
    stages = tmp_path / "stages"
    chaos = tmp_path / "chaos"
    for directory in (benchmarks, stages, chaos):
        directory.mkdir()
    profile.write_text(
        json.dumps(
            {
                "profile_id": "openinfra-enterprise-capacity-v2",
                "profile_version": 2,
                "required_benchmark_workloads": list(WORKLOADS),
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
        ),
        encoding="utf-8",
    )
    topology.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    for name in WORKLOADS:
        report = {
            "workload": name,
            "method": "GET",
            "path": f"/api/v1/{name}",
            "duration_seconds": 1,
            "requests": 10,
            "p95_ms": 10,
            "p99_ms": 20,
            "error_rate_percent": 0,
            "throughput_rps": 10,
            "response_bytes": 100,
            "expected_status_codes": [200],
        }
        (benchmarks / f"{name}.json").write_text(json.dumps(report), encoding="utf-8")
    stage_payload = {
        "duration_seconds": 1,
        "requests": 10,
        "p95_ms": 10,
        "p99_ms": 20,
        "error_rate_percent": 0,
        "saturation_percent": 10,
        "memory_growth_percent": 0,
        "replica_lag_seconds": 0,
        "trace_coverage_percent": 100,
        "metrics_complete": True,
        "leak_detected": False,
    }
    for name in ("baseline", "step-load", "endurance", "spike", "saturation"):
        (stages / f"{name}.json").write_text(
            json.dumps({"stage": name, **stage_payload}), encoding="utf-8"
        )
    chaos_payload = {
        "fault_injected": True,
        "service_recovered": True,
        "recovery_seconds": 1,
        "data_integrity_verified": True,
        "acknowledged_work_lost": False,
    }
    for name in (
        "api-worker-loss",
        "web-worker-loss",
        "db-replica-loss",
        "pgbouncer-restart",
    ):
        (chaos / f"{name}.json").write_text(
            json.dumps({"scenario": name, **chaos_payload}), encoding="utf-8"
        )

    payload = assemble_capacity_evidence(
        profile_path=profile,
        topology_path=topology,
        benchmark_directory=benchmarks,
        stage_directory=stages,
        chaos_directory=chaos,
        output_path=tmp_path / "evidence.json",
    )

    assert len(payload["benchmarks"]) == 6  # type: ignore[arg-type]
    assert len(payload["source_hashes"]) == 17  # type: ignore[arg-type]
