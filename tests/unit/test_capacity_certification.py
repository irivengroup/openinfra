from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.certify_enterprise_capacity import EnterpriseCapacityCertificationCli

from openinfra.domain.common import ValidationError
from openinfra.quality.capacity_certification import (
    EnterpriseCapacityCertification,
    EnterpriseCapacityCertificationService,
)


def _evidence() -> dict[str, object]:
    thresholds = {
        "p95_ms": 500,
        "p99_ms": 1000,
        "error_rate_percent": 1,
        "saturation_percent": 90,
        "recovery_seconds": 120,
        "memory_growth_percent": 10,
        "replica_lag_seconds": 5,
        "trace_coverage_percent": 99,
    }
    stage = {
        "duration_seconds": 300,
        "requests": 5000,
        "p95_ms": 125,
        "p99_ms": 250,
        "error_rate_percent": 0.1,
        "saturation_percent": 45,
        "memory_growth_percent": 2,
        "replica_lag_seconds": 0.5,
        "trace_coverage_percent": 100,
        "metrics_complete": True,
        "leak_detected": False,
    }
    chaos = {
        "fault_injected": True,
        "service_recovered": True,
        "recovery_seconds": 15,
        "data_integrity_verified": True,
        "acknowledged_work_lost": False,
    }
    return {
        "profile_id": "openinfra-enterprise-capacity-v1",
        "profile_version": 1,
        "topology": {
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
            "topology_fingerprint": "b" * 64,
        },
        "thresholds": thresholds,
        "stages": [
            {"stage": name, **stage}
            for name in ("baseline", "step-load", "endurance", "spike", "saturation")
        ],
        "chaos": [
            {"scenario": name, **chaos}
            for name in (
                "api-worker-loss",
                "web-worker-loss",
                "db-replica-loss",
                "pgbouncer-restart",
            )
        ],
        "source_hashes": {"topology": "a" * 64, "metrics": "c" * 64},
    }


def test_capacity_certification_accepts_complete_enterprise_evidence(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output = tmp_path / "report.json"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")

    report = EnterpriseCapacityCertificationService.write_report(evidence_path, output)

    assert report["capacity_certification"] is True
    assert report["status"] == "certified"
    assert report["failures"] == []
    assert len(str(report["evidence_sha256"])) == 64
    assert json.loads(output.read_text(encoding="utf-8"))["capacity_certification"] is True
    assert (
        EnterpriseCapacityCertificationCli.main(
            ["--evidence", str(evidence_path), "--output", str(output), "--enforce"]
        )
        == 0
    )


def test_capacity_certification_rejects_missing_or_failed_proofs(tmp_path: Path) -> None:
    payload = _evidence()
    topology = payload["topology"]
    assert isinstance(topology, dict)
    topology["api_instances"] = 1
    stages = payload["stages"]
    assert isinstance(stages, list)
    stages.pop()
    first_stage = stages[0]
    assert isinstance(first_stage, dict)
    first_stage["p99_ms"] = 1500
    chaos = payload["chaos"]
    assert isinstance(chaos, list)
    first_chaos = chaos[0]
    assert isinstance(first_chaos, dict)
    first_chaos["data_integrity_verified"] = False
    evidence_path = tmp_path / "failed.json"
    output = tmp_path / "report.json"
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    report = EnterpriseCapacityCertificationService.write_report(evidence_path, output)

    assert report["capacity_certification"] is False
    failure_values = report["failures"]
    assert isinstance(failure_values, list)
    failures = "\n".join(str(value) for value in failure_values)
    assert "api_instances" in failures
    assert "missing required capacity stage: saturation" in failures
    assert "p99_ms" in failures
    assert "data integrity" in failures
    assert (
        EnterpriseCapacityCertificationCli.main(
            ["--evidence", str(evidence_path), "--output", str(output), "--enforce"]
        )
        == 1
    )


def test_capacity_evidence_validation_rejects_untrusted_shapes() -> None:
    payload = _evidence()
    payload["profile_version"] = 0
    with pytest.raises(ValidationError, match="greater than zero"):
        EnterpriseCapacityCertification.from_mapping(payload)

    payload = _evidence()
    payload["source_hashes"] = {"metrics": "invalid"}
    with pytest.raises(ValidationError, match="SHA-256"):
        EnterpriseCapacityCertification.from_mapping(payload)

    payload = _evidence()
    payload["stages"] = [{"stage": "unknown"}]
    with pytest.raises(ValidationError, match="unsupported capacity stage"):
        EnterpriseCapacityCertification.from_mapping(payload)

    payload = _evidence()
    payload["benchmarks"] = {}
    with pytest.raises(ValidationError, match="benchmarks must be a JSON array"):
        EnterpriseCapacityCertification.from_mapping(payload)


def test_capacity_validation_covers_all_untrusted_scalar_and_shape_branches(tmp_path: Path) -> None:
    from copy import deepcopy

    from openinfra.quality.capacity_certification import (
        CapacityStageEvidence,
        ChaosScenarioEvidence,
        EnterpriseCapacityThresholds,
        EnterpriseTopologyEvidence,
    )

    invalid_scalars: list[tuple[str, object, str]] = [
        ("profile_version", True, "numeric"),
        ("profile_version", "not-a-number", "numeric"),
        ("profile_version", -1, "non-negative"),
        ("profile_version", 1.5, "integer"),
    ]
    for field, value, message in invalid_scalars:
        payload = deepcopy(_evidence())
        payload[field] = value
        with pytest.raises(ValidationError, match=message):
            EnterpriseCapacityCertification.from_mapping(payload)

    thresholds = deepcopy(_evidence()["thresholds"])
    assert isinstance(thresholds, dict)
    thresholds["p99_ms"] = 100
    thresholds["p95_ms"] = 200
    with pytest.raises(ValidationError, match="cannot be lower"):
        EnterpriseCapacityThresholds.from_mapping(thresholds)
    thresholds = deepcopy(_evidence()["thresholds"])
    assert isinstance(thresholds, dict)
    thresholds["saturation_percent"] = 101
    with pytest.raises(ValidationError, match="cannot exceed"):
        EnterpriseCapacityThresholds.from_mapping(thresholds)

    topology = deepcopy(_evidence()["topology"])
    assert isinstance(topology, dict)
    topology["edition"] = "pro"
    with pytest.raises(ValidationError, match="Enterprise edition"):
        EnterpriseTopologyEvidence.from_mapping(topology)
    topology = deepcopy(_evidence()["topology"])
    assert isinstance(topology, dict)
    topology["topology_fingerprint"] = "short"
    with pytest.raises(ValidationError, match="at least 32"):
        EnterpriseTopologyEvidence.from_mapping(topology)

    with pytest.raises(ValidationError, match="unsupported chaos"):
        ChaosScenarioEvidence.from_mapping({"scenario": "unknown"})
    with pytest.raises(ValidationError, match="must be a boolean"):
        ChaosScenarioEvidence.from_mapping(
            {
                "scenario": "api-worker-loss",
                "fault_injected": "yes",
                "service_recovered": True,
                "recovery_seconds": 1,
                "data_integrity_verified": True,
                "acknowledged_work_lost": False,
            }
        )

    stage = deepcopy(_evidence()["stages"])
    assert isinstance(stage, list) and isinstance(stage[0], dict)
    failing_stage = dict(stage[0])
    failing_stage.update(
        {
            "requests": 0,
            "duration_seconds": 0,
            "trace_coverage_percent": 1,
            "metrics_complete": False,
            "leak_detected": True,
        }
    )
    parsed_stage = CapacityStageEvidence.from_mapping(failing_stage)
    stage_failures = "\n".join(
        parsed_stage.failures(
            EnterpriseCapacityThresholds.from_mapping(
                _evidence()["thresholds"]  # type: ignore[arg-type]
            )
        )
    )
    assert "trace_coverage_percent" in stage_failures
    assert "metrics are incomplete" in stage_failures
    assert "resource leak" in stage_failures
    assert "non-empty duration" in stage_failures

    failing_chaos = ChaosScenarioEvidence.from_mapping(
        {
            "scenario": "api-worker-loss",
            "fault_injected": False,
            "service_recovered": False,
            "recovery_seconds": 999,
            "data_integrity_verified": False,
            "acknowledged_work_lost": True,
        }
    )
    chaos_failures = "\n".join(
        failing_chaos.failures(
            EnterpriseCapacityThresholds.from_mapping(
                _evidence()["thresholds"]  # type: ignore[arg-type]
            )
        )
    )
    assert "fault was not injected" in chaos_failures
    assert "did not recover" in chaos_failures
    assert "recovery_seconds" in chaos_failures
    assert "data integrity" in chaos_failures
    assert "acknowledged work" in chaos_failures

    invalid_shapes: list[tuple[str, object, str]] = [
        ("profile_id", "", "profile_id"),
        ("topology", [], "topology and thresholds"),
        ("thresholds", [], "topology and thresholds"),
        ("stages", {}, "JSON arrays"),
        ("chaos", {}, "JSON arrays"),
        ("source_hashes", [], "JSON object"),
    ]
    for field, value, message in invalid_shapes:
        payload = deepcopy(_evidence())
        payload[field] = value
        with pytest.raises(ValidationError, match=message):
            EnterpriseCapacityCertification.from_mapping(payload)

    payload = deepcopy(_evidence())
    stages = payload["stages"]
    assert isinstance(stages, list)
    stages.append(deepcopy(stages[0]))
    with pytest.raises(ValidationError, match="stages must be unique"):
        EnterpriseCapacityCertification.from_mapping(payload)

    payload = deepcopy(_evidence())
    chaos = payload["chaos"]
    assert isinstance(chaos, list)
    chaos.append(deepcopy(chaos[0]))
    with pytest.raises(ValidationError, match="scenarios must be unique"):
        EnterpriseCapacityCertification.from_mapping(payload)

    payload = deepcopy(_evidence())
    payload["stages"] = ["invalid"]
    with pytest.raises(ValidationError, match="entries must be JSON objects"):
        EnterpriseCapacityCertification.from_mapping(payload)

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValidationError, match="cannot read"):
        EnterpriseCapacityCertification.load(invalid_json)
    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValidationError, match="root must be"):
        EnterpriseCapacityCertification.load(non_object)


def _benchmark(workload: str) -> dict[str, object]:
    return {
        "workload": workload,
        "method": "GET",
        "path": f"/api/v1/{workload}",
        "duration_seconds": 300,
        "requests": 5000,
        "p95_ms": 125,
        "p99_ms": 250,
        "error_rate_percent": 0.1,
        "throughput_rps": 50,
        "response_bytes": 1024,
        "expected_status_codes": [200],
    }


def test_capacity_v2_requires_and_certifies_all_enterprise_benchmark_workloads() -> None:
    payload = _evidence()
    payload["profile_id"] = "openinfra-enterprise-capacity-v2"
    payload["profile_version"] = 2
    payload["benchmarks"] = [
        _benchmark(name) for name in ("api", "ipam", "imports", "discovery", "database", "graph")
    ]

    report = EnterpriseCapacityCertification.from_mapping(payload).evaluate()

    assert report["schema_version"] == 2
    assert report["capacity_certification"] is True
    assert len(report["benchmarks"]) == 6  # type: ignore[arg-type]

    payload["benchmarks"] = payload["benchmarks"][:-1]  # type: ignore[index]
    report = EnterpriseCapacityCertification.from_mapping(payload).evaluate()
    assert report["capacity_certification"] is False
    assert "missing required benchmark workload: graph" in report["failures"]


def test_benchmark_workload_validation_and_threshold_failures() -> None:
    from openinfra.quality.capacity_certification import (
        BenchmarkWorkloadEvidence,
        EnterpriseCapacityThresholds,
    )

    thresholds = EnterpriseCapacityThresholds.from_mapping(
        _evidence()["thresholds"]  # type: ignore[arg-type]
    )
    failing = _benchmark("api")
    failing.update(
        {
            "duration_seconds": 0,
            "requests": 0,
            "p95_ms": 501,
            "p99_ms": 1001,
            "error_rate_percent": 2,
            "throughput_rps": 0,
        }
    )
    failures = "\n".join(BenchmarkWorkloadEvidence.from_mapping(failing).failures(thresholds))
    assert "non-empty load evidence" in failures
    assert "p95_ms" in failures
    assert "p99_ms" in failures
    assert "error_rate_percent" in failures
    assert "positive throughput" in failures

    invalid_cases = (
        ({**_benchmark("api"), "workload": "unknown"}, "unsupported benchmark workload"),
        ({**_benchmark("api"), "method": "POST"}, "only read-only GET"),
        ({**_benchmark("api"), "path": "https://evil.example"}, "absolute HTTP path"),
        ({**_benchmark("api"), "expected_status_codes": []}, "non-empty array"),
        ({**_benchmark("api"), "expected_status_codes": [99]}, "invalid expected HTTP"),
        ({**_benchmark("api"), "expected_status_codes": [200, 200]}, "must be unique"),
    )
    for invalid, message in invalid_cases:
        with pytest.raises(ValidationError, match=message):
            BenchmarkWorkloadEvidence.from_mapping(invalid)

    duplicate = _evidence()
    duplicate["benchmarks"] = [_benchmark("api"), _benchmark("api")]
    with pytest.raises(ValidationError, match="benchmark workloads must be unique"):
        EnterpriseCapacityCertification.from_mapping(duplicate)
