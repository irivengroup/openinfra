from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_security_is_available_in_runtime_react_and_search_catalogues() -> None:
    for relative in (
        "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        "web/src/domains/discovery.js",
    ):
        source = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        assert "kubernetes-security-latest" in source
        assert "kubernetes-security-snapshot" in source
        assert "/v1/kubernetes/topologies/latest-security" in source
        assert "/v1/kubernetes/topologies/security" in source

    search = (
        PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-search-index.js"
    ).read_text(encoding="utf-8")
    assert "kubernetes-security-latest" in search
    assert "kubernetes-security-snapshot" in search
