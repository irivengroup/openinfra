from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_capacity_is_available_in_runtime_react_search_and_openapi_catalogues() -> None:
    operation_ids = (
        "kubernetes-capacity-latest",
        "kubernetes-capacity-snapshot",
        "kubernetes-capacity-trend",
        "kubernetes-capacity-export",
        "kubernetes-capacity-latest-export",
    )
    paths = (
        "/v1/kubernetes/topologies/latest-capacity",
        "/v1/kubernetes/topologies/capacity",
        "/v1/kubernetes/topologies/capacity-trend",
        "/v1/kubernetes/topologies/capacity-export",
        "/v1/kubernetes/topologies/latest-capacity-export",
    )
    for relative in (
        "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        "web/src/domains/discovery.js",
    ):
        source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for operation_id in operation_ids:
            assert operation_id in source
        for path in paths:
            assert path in source

    for relative in (
        "src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js",
        "web/src/search-index.js",
    ):
        search = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for operation_id in operation_ids:
            assert operation_id in search

    openapi = (PROJECT_ROOT / "docs/api/openapi.yaml").read_text(encoding="utf-8")
    for path in paths:
        assert f"/api{path}:" in openapi
    assert "Discovery · Kubernetes et cloud-native" in openapi
