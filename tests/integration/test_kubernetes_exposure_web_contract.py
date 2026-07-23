from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_exposure_is_available_in_runtime_and_react_discovery_catalogues() -> None:
    for relative in (
        "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        "web/src/domains/discovery.js",
    ):
        source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        assert "kubernetes-exposure-latest" in source
        assert "kubernetes-exposure-snapshot" in source
        assert "/v1/kubernetes/topologies/latest-exposure" in source
        assert "/v1/kubernetes/topologies/exposure" in source
