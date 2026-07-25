from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_global_search_clients_respect_backend_limit_contract() -> None:
    react = (ROOT / "web/src/main.jsx").read_text(encoding="utf-8")
    runtime = (
        ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"
    ).read_text(encoding="utf-8")
    backend = (ROOT / "src/openinfra/application/search_services.py").read_text(
        encoding="utf-8"
    )

    assert "GLOBAL_SEARCH_BACKEND_LIMIT = 25" in react
    assert "normalizeGlobalSearchLimit" in react
    assert "Math.min(GLOBAL_SEARCH_BACKEND_LIMIT, Math.max(1, parsed))" in react
    assert "query, GLOBAL_SEARCH_BACKEND_LIMIT" in react
    assert "this.globalSearchUrl(query, 25)" in runtime
    assert "Math.min(25, Math.max(1, parsedLimit))" in runtime
    assert "global search limit must be between 1 and 25" in backend
    assert "query, 80" not in react
    assert "globalSearchUrl(query, 80)" not in runtime
