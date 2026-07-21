from __future__ import annotations

from pathlib import Path

from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL
from tests.runtime_i18n_contract import assert_runtime_i18n_contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_JS = RUNTIME_PORTAL
STATIC_CSS = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.css"
REACT_JS = REACT_PORTAL
REACT_CSS = PROJECT_ROOT / "web/src/openinfra-theme.css"
SOURCE_I18N = PROJECT_ROOT / "web/src/i18n.js"
RUNTIME_I18N = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js"


def test_spof_analysis_and_graph_export_are_exposed_by_both_web_runtimes() -> None:
    for source in (STATIC_JS.read_text(encoding="utf-8"), REACT_JS.read_text(encoding="utf-8")):
        assert "graph-spof" in source
        assert "graph-export" in source
        assert "/v1/graph/spof" in source
        assert "/v1/graph/export" in source
        assert "candidate_resource_category" in source
        assert "minimum_affected_nodes" in source
        assert "include_spof" in source
        assert "URL.createObjectURL" in source
        assert "URL.revokeObjectURL" in source

    static = STATIC_JS.read_text(encoding="utf-8")
    assert "field.defaultValue === true" in static
    assert 'value="true"${defaultBoolean ? " selected" : ""}' in static


def test_graph_visualization_is_accessible_and_has_a_raw_result_fallback() -> None:
    static = STATIC_JS.read_text(encoding="utf-8")
    react = REACT_JS.read_text(encoding="utf-8")
    for source in (static, react):
        assert "openinfra-graph-canvas" in source
        assert "openinfra-spof-ranking" in source
        assert "openinfra-raw-result" in source
        assert "visually-hidden" in source
        assert 'role="img"' in source
    assert 'tabindex="0"' in static
    assert "tabIndex={0}" in react


def test_graph_visualization_styles_are_responsive_and_high_contrast_compatible() -> None:
    for stylesheet in (STATIC_CSS, REACT_CSS):
        css = stylesheet.read_text(encoding="utf-8")
        assert ".openinfra-graph-canvas" in css
        assert ".openinfra-spof-ratio" in css
        assert "overflow: auto" in css
        assert "@media (max-width: 767.98px)" in css
        assert "@media (forced-colors: active)" in css


def test_spof_web_catalog_is_bilingual_and_runtime_i18n_is_generated() -> None:
    assert_runtime_i18n_contract(
        "Detect single points of failure",
        "Export dependency graph",
        "Single points of failure ranking",
        "Classement des points uniques de défaillance",
    )
