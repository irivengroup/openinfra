from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    ROOT / "web/src/main.jsx",
    ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js",
)


def test_sbom_is_grouped_under_security_with_route_parity() -> None:
    operations = (
        "sbom-import",
        "sbom-documents",
        "sbom-document-get",
        "sbom-vulnerability-import",
        "sbom-vulnerabilities",
        "sbom-exposure-upsert",
        "sbom-exposures",
        "sbom-exposure-get",
        "sbom-risk-assess",
        "sbom-findings",
        "sbom-risk-export",
        "sbom-compare",
        "sbom-comparisons",
        "sbom-comparison-get",
    )
    routes = (
        "/v1/sbom/documents/import",
        "/v1/sbom/documents",
        "/v1/sbom/documents/get",
        "/v1/sbom/vulnerabilities/import",
        "/v1/sbom/vulnerabilities",
        "/v1/sbom/exposures/upsert",
        "/v1/sbom/exposures",
        "/v1/sbom/exposures/get",
        "/v1/sbom/risk/assess",
        "/v1/sbom/findings",
        "/v1/sbom/risk/export",
        "/v1/sbom/comparisons/create",
        "/v1/sbom/comparisons",
        "/v1/sbom/comparisons/get",
    )
    for source_path in SOURCES:
        source = source_path.read_text(encoding="utf-8")
        for operation in operations:
            assert operation in source
        for route in routes:
            assert route in source
        assert "SBOM — inventaire & versions" in source
        assert "Vulnérabilités & exposition" in source
        assert "Risque contextualisé" in source
        assert "id: 'sbom'" not in source
        assert 'id: "sbom"' not in source


def test_sbom_dates_json_validation_and_download_are_real_controls() -> None:
    for source_path in SOURCES:
        source = source_path.read_text(encoding="utf-8")
        assert "published_at" in source and "datetime-local" in source
        assert "modified_at" in source
        assert "type: 'json'" in source or 'type: "json"' in source
        assert "sbom-risk-export" in source and "download" in source
    react = SOURCES[0].read_text(encoding="utf-8")
    assert "selected.id.startsWith('sbom-')" in react
