from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from scripts.benchmark_high_performance_runtime import (
    OpenInfraHighPerformanceRuntimeBenchmark,
    OpenInfraHighPerformanceRuntimeBenchmarkCli,
    RuntimeLatencyDistribution,
)


def test_asgi_transport_benchmark_emits_p95_p99_report(tmp_path: Path) -> None:
    report = asyncio.run(
        OpenInfraHighPerformanceRuntimeBenchmark(requests=60, concurrency=10, warmups=3).run()
    )

    assert report["scope"] == "asgi-transport-regression"
    assert report["capacity_certification"] is False
    assert report["passed"] is True
    results = report["results"]
    assert isinstance(results, list)
    assert {item["scenario"] for item in results} == {
        "api-health",
        "web-bootstrap",
        "bff-proxy",
    }
    assert all(item["p95_ms"] <= item["threshold_p95_ms"] for item in results)
    assert all(item["p99_ms"] <= item["threshold_p99_ms"] for item in results)

    output = tmp_path / "runtime-benchmark.json"
    assert (
        OpenInfraHighPerformanceRuntimeBenchmarkCli.main(
            [
                "--requests",
                "20",
                "--concurrency",
                "5",
                "--warmups",
                "1",
                "--output",
                str(output),
                "--enforce",
            ]
        )
        == 0
    )
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["passed"] is True


@pytest.mark.parametrize(
    ("requests", "concurrency", "warmups", "message"),
    [
        (0, 1, 0, "requests"),
        (1, 0, 0, "concurrency"),
        (1, 2, 0, "concurrency"),
        (1, 1, -1, "warmups"),
    ],
)
def test_asgi_transport_benchmark_rejects_invalid_load_profiles(
    requests: int,
    concurrency: int,
    warmups: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        OpenInfraHighPerformanceRuntimeBenchmark(requests, concurrency, warmups)


def test_latency_distribution_validates_percentiles() -> None:
    distribution = RuntimeLatencyDistribution([3.0, 1.0, 2.0])
    assert distribution.percentile(50) == 2.0
    assert distribution.percentile(100) == 3.0
    assert distribution.maximum == 3.0
    with pytest.raises(ValueError, match="sample"):
        RuntimeLatencyDistribution([])
    with pytest.raises(ValueError, match="percentile"):
        distribution.percentile(0)
