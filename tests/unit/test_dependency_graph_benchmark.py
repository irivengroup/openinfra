from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.quality.dependency_graph_benchmark import (
    BenchmarkConfigurationError,
    BenchmarkMeasurement,
    DependencyGraphBenchmarkCli,
    DependencyGraphBenchmarkConfig,
    DependencyGraphBenchmarkReport,
    DependencyGraphBenchmarkRunner,
)


def test_dependency_graph_benchmark_configuration_guards_invalid_values() -> None:
    with pytest.raises(BenchmarkConfigurationError, match="node_count"):
        DependencyGraphBenchmarkConfig(node_count=99).validate()
    with pytest.raises(BenchmarkConfigurationError, match="spof_hub_count"):
        DependencyGraphBenchmarkConfig(node_count=100, spof_hub_count=50).validate()
    with pytest.raises(BenchmarkConfigurationError, match="samples"):
        DependencyGraphBenchmarkConfig(samples=0).validate()
    with pytest.raises(BenchmarkConfigurationError, match="warmups"):
        DependencyGraphBenchmarkConfig(warmups=11).validate()
    with pytest.raises(BenchmarkConfigurationError, match="threshold"):
        DependencyGraphBenchmarkConfig(one_level_threshold_ms=0).validate()


def test_dependency_graph_benchmark_percentile_and_report_serialization() -> None:
    assert DependencyGraphBenchmarkRunner._percentile((1.0, 2.0, 3.0, 4.0), 0.50) == 2.0
    assert DependencyGraphBenchmarkRunner._percentile((1.0, 2.0, 3.0, 4.0), 0.95) == 4.0
    with pytest.raises(BenchmarkConfigurationError, match="sample"):
        DependencyGraphBenchmarkRunner._percentile((), 0.95)

    measurement = BenchmarkMeasurement(
        name="graph",
        samples_ms=(2.0, 1.0),
        p50_ms=1.0,
        p95_ms=2.0,
        threshold_ms=3.0,
        passed=True,
        observations={"nodes": 100},
    )
    report = DependencyGraphBenchmarkReport(
        generated_at="2026-07-11T00:00:00+00:00",
        python_version="3.13.5",
        platform="test",
        logical_cpu_count=4,
        config=DependencyGraphBenchmarkConfig(node_count=100, spof_hub_count=10),
        measurements=(measurement,),
    )

    payload = json.loads(report.to_json())
    assert report.passed is True
    assert payload["schema_version"] == 1
    assert payload["measurements"][0]["p95_ms"] == 2.0
    assert "overall=PASS" in report.summary_lines()[1]


def test_dependency_graph_benchmark_cli_writes_json_and_reports_threshold_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_path = tmp_path / "reports" / "dependency-graph.json"
    success = DependencyGraphBenchmarkCli.main(
        (
            "--nodes",
            "100",
            "--spof-hubs",
            "10",
            "--samples",
            "1",
            "--warmups",
            "0",
            "--output",
            str(report_path),
        )
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert success == 0
    assert payload["passed"] is True
    assert "overall=PASS" in capsys.readouterr().out

    failure = DependencyGraphBenchmarkCli.main(
        (
            "--nodes",
            "100",
            "--spof-hubs",
            "10",
            "--samples",
            "1",
            "--warmups",
            "0",
            "--one-level-threshold-ms",
            "0.000001",
        )
    )
    assert failure == 1
    assert "overall=FAIL" in capsys.readouterr().out


def test_dependency_graph_benchmark_cli_rejects_invalid_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert DependencyGraphBenchmarkCli.main(("--nodes", "10")) == 2
    assert "node_count" in capsys.readouterr().err


def test_synthetic_benchmark_adapters_cover_pagination_filters_and_integrity() -> None:
    from datetime import UTC, datetime

    from openinfra.domain.audit import AuditEventFilter
    from openinfra.domain.common import AuditEvent, Pagination, TenantId, ValidationError
    from openinfra.domain.source_of_truth import SourceRelation
    from openinfra.quality import dependency_graph_benchmark as benchmark

    tenant = TenantId.from_value("benchmark")
    repository = benchmark._SyntheticSourceOfTruthRepository()
    first = repository.create_object(
        tenant,
        "server/benchmark-a",
        "server",
        "Benchmark A",
        {"resource_type": "rack-server"},
        ("benchmark",),
        "benchmark",
        "pytest",
    )
    second = repository.create_object(
        tenant,
        "service/benchmark-b",
        "service",
        "Benchmark B",
        {},
        ("benchmark",),
        "benchmark",
        "pytest",
    )

    page = repository.list_objects(
        tenant,
        Pagination.from_values(1),
        kind="server",
        tag="benchmark",
        resource_type="rack-server",
    )
    assert page.items == (first,)
    assert repository.find_object(tenant, "SERVER/BENCHMARK-A") == first
    assert repository.find_object_version(tenant, first.key.value, 1) is None
    assert repository.find_object_as_of(tenant, first.key.value, datetime.now(UTC)) is None

    relation = SourceRelation.create(
        tenant,
        "calls",
        first.key.value,
        second.key.value,
        "benchmark",
    )
    repository.add_relation(relation)
    repository.add_relation(relation)
    by_target = repository.list_relations(
        tenant,
        Pagination.from_values(1),
        target_key=second.key.value,
        relation_type="calls",
        as_of=datetime.now(UTC),
    )
    all_relations = repository.list_relations(tenant, Pagination.from_values(1))
    assert by_target.items == (relation,)
    assert all_relations.items == (relation,)
    with pytest.raises(ValidationError, match="numeric offset"):
        repository._offset("invalid")
    with pytest.raises(ValidationError, match="positive"):
        repository._offset("-1")

    audit = benchmark._BenchmarkAuditRepository()
    event = AuditEvent.record(tenant, "pytest", "graph.benchmark", "graph", "root")
    audit.append(event)
    assert audit.list_records(AuditEventFilter(tenant, Pagination.from_values(10))).items == ()
    integrity = audit.verify_integrity(tenant, limit=1)
    assert integrity.checked == 1
    assert integrity.valid is True

    unit_of_work = benchmark._BenchmarkUnitOfWork()
    assert unit_of_work.__enter__() is unit_of_work
    unit_of_work.commit()
    unit_of_work.rollback()
    unit_of_work.__exit__(None, None, None)
