from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.benchmark_cursor_pagination import (
    CursorLatencyDistribution,
    OpenInfraCursorPaginationBenchmark,
    OpenInfraCursorPaginationBenchmarkCli,
)


def test_cursor_benchmark_reports_stable_deep_page_latency(tmp_path: Path) -> None:
    report = OpenInfraCursorPaginationBenchmark(iterations=200, p95_threshold_ms=5.0).run()
    assert report["scope"] == "keyset-query-construction-regression"
    assert report["capacity_certification"] is False
    assert report["passed"] is True
    results = report["results"]
    assert isinstance(results, list)
    assert {item["scenario"] for item in results} == {"first-page", "deep-page"}

    output = tmp_path / "cursor-pagination.json"
    assert (
        OpenInfraCursorPaginationBenchmarkCli.main(
            [
                "--iterations",
                "100",
                "--p95-threshold-ms",
                "5",
                "--output",
                str(output),
                "--enforce",
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


@pytest.mark.parametrize(
    ("iterations", "threshold", "message"),
    ((99, 1.0, "iterations"), (100, 0.0, "threshold")),
)
def test_cursor_benchmark_rejects_invalid_profiles(
    iterations: int, threshold: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        OpenInfraCursorPaginationBenchmark(iterations, threshold)


def test_cursor_latency_distribution_validates_samples_and_percentiles() -> None:
    distribution = CursorLatencyDistribution((3.0, 1.0, 2.0))
    assert distribution.percentile(50) == 2.0
    assert distribution.percentile(100) == 3.0
    with pytest.raises(ValueError, match="empty"):
        CursorLatencyDistribution(())
    with pytest.raises(ValueError, match="percentile"):
        distribution.percentile(0)
