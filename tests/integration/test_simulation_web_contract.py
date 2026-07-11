from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_JS = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"
REACT_JS = PROJECT_ROOT / "web/src/main.jsx"
SOURCE_I18N = PROJECT_ROOT / "web/src/i18n.js"
RUNTIME_I18N = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js"


def test_simulation_is_grouped_under_rsot_in_both_web_runtimes() -> None:
    operation_ids = (
        "simulation-create",
        "simulation-list",
        "simulation-run",
        "simulation-reports",
        "simulation-compare",
        "simulation-comparisons",
    )
    for path in (STATIC_JS, REACT_JS):
        source = path.read_text(encoding="utf-8")
        assert "Simulation & migrations" in source
        for operation_id in operation_ids:
            assert operation_id in source
        for route in (
            "/v1/simulation-scenarios/create",
            "/v1/simulation-scenarios",
            "/v1/simulation-scenarios/run",
            "/v1/impact-reports",
            "/v1/scenario-comparisons/create",
            "/v1/scenario-comparisons",
        ):
            assert route in source
        assert "{ id: 'simulation'" not in source
        assert '{ id: "simulation"' not in source


def test_simulation_forms_are_typed_and_execute_against_backend() -> None:
    static = STATIC_JS.read_text(encoding="utf-8")
    react = REACT_JS.read_text(encoding="utf-8")
    for source in (static, react):
        assert "Changements JSON" in source
        assert 'type: "json"' in source or "type: 'json'" in source
        assert "max_depth" in source
        assert "max_nodes" in source
    assert "selected.id.startsWith('simulation-')" in react


def test_simulation_web_catalog_is_bilingual_and_i18n_is_identical() -> None:
    source_i18n = SOURCE_I18N.read_text(encoding="utf-8")
    runtime_i18n = RUNTIME_I18N.read_text(encoding="utf-8")
    assert runtime_i18n == source_i18n
    assert "Create change scenario" in source_i18n
    assert "Calculate scenario impact" in source_i18n
    assert "Compare two reports" in source_i18n
