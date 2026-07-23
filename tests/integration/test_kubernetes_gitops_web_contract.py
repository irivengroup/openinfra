from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_gitops_is_available_in_runtime_react_and_search_catalogues() -> None:
    operation_ids = (
        "kubernetes-gitops-states-list",
        "kubernetes-gitops-state-get",
        "kubernetes-gitops-state-latest",
        "kubernetes-gitops-drift-snapshot",
        "kubernetes-gitops-drift-latest",
        "kubernetes-gitops-state-import",
    )
    for relative in (
        "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        "web/src/domains/discovery.js",
    ):
        source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for operation_id in operation_ids:
            assert operation_id in source
        for path in (
            "/v1/kubernetes/gitops-states",
            "/v1/kubernetes/gitops-states/get",
            "/v1/kubernetes/gitops-states/latest",
            "/v1/kubernetes/gitops-states/drift",
            "/v1/kubernetes/gitops-states/latest-drift",
            "/v1/kubernetes/gitops-states/import",
        ):
            assert path in source

    for relative in (
        "src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js",
        "web/src/search-index.js",
    ):
        search = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for operation_id in operation_ids:
            assert operation_id in search
