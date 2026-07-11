from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    ROOT / "web/src/main.jsx",
    ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js",
)


def test_multisite_is_grouped_under_dcim_with_api_parity() -> None:
    operations = (
        "multisite-grant-upsert",
        "multisite-grant-revoke",
        "multisite-grants",
        "multisite-sites",
        "multisite-report-generate",
        "multisite-reports",
        "multisite-report-get",
    )
    routes = (
        "/v1/multisite/site-access/grants/upsert",
        "/v1/multisite/site-access/grants/revoke",
        "/v1/multisite/site-access/grants",
        "/v1/multisite/sites",
        "/v1/multisite/reports/generate",
        "/v1/multisite/reports",
        "/v1/multisite/reports/get",
    )
    for path in SOURCES:
        source = path.read_text(encoding="utf-8")
        for operation in operations:
            assert operation in source
        for route in routes:
            assert route in source
        assert "Pilotage multisite" in source
        assert "id: 'multisite'" not in source and 'id: "multisite"' not in source


def test_multisite_static_forms_use_typed_controls_and_no_agent_workflow() -> None:
    source = SOURCES[1].read_text(encoding="utf-8")
    assert 'name: "access_level"' in source and 'type: "select"' in source
    assert 'name: "site_codes"' in source and 'type: "json"' in source
    assert 'name: "active_only"' in source and 'type: "boolean"' in source
    assert "/v1/multisite/agents" not in source
    assert "/v1/multisite/regions" not in source
