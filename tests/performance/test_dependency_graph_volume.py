from __future__ import annotations

from openinfra.quality.dependency_graph_benchmark import (
    DependencyGraphBenchmarkConfig,
    DependencyGraphBenchmarkRunner,
)


def test_dependency_graph_volume_pagination_filters_and_spof_stay_within_guardrails() -> None:
    report = DependencyGraphBenchmarkRunner(
        DependencyGraphBenchmarkConfig(
            node_count=1000,
            spof_hub_count=40,
            samples=2,
            warmups=1,
            one_level_threshold_ms=2000,
            filtered_threshold_ms=2000,
            spof_threshold_ms=5000,
            pagination_threshold_ms=15000,
        )
    ).run()

    measurements = {measurement.name: measurement for measurement in report.measurements}
    assert report.passed is True
    assert measurements["traverse_one_level"].observations == {
        "nodes": 1000,
        "edges": 999,
        "truncated": False,
    }
    assert measurements["traverse_one_level_filtered"].observations == {
        "nodes": 501,
        "edges": 500,
        "relation_type": "calls",
    }
    assert measurements["spof_analysis"].observations["spof_count"] == 40
    assert measurements["spof_full_pagination"].observations == {
        "spof_count": 40,
        "pages": 2,
        "page_size": 25,
    }
