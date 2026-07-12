from __future__ import annotations

from pathlib import Path

from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_JS = RUNTIME_PORTAL
REACT_JS = REACT_PORTAL
SOURCE_I18N = PROJECT_ROOT / "web/src/i18n.js"
RUNTIME_I18N = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js"


def test_certificate_pki_component_is_exposed_by_both_web_runtimes() -> None:
    static = STATIC_JS.read_text(encoding="utf-8")
    react = REACT_JS.read_text(encoding="utf-8")
    operation_ids = (
        "certificate-import",
        "certificate-get",
        "certificate-list",
        "certificate-retire",
        "certificate-endpoint-observe",
        "certificate-endpoint-list",
        "certificate-assessment",
    )

    for source in (static, react):
        assert "Inventaire PKI" in source
        assert "Endpoints TLS" in source
        assert "Conformité PKI" in source
        assert "id: 'certificates'" not in source
        assert 'id: "certificates"' not in source
        for operation_id in operation_ids:
            assert operation_id in source
        for route in (
            "/v1/certificates/import",
            "/v1/certificates/get",
            "/v1/certificates",
            "/v1/certificates/retire",
            "/v1/certificates/endpoints/observe",
            "/v1/certificates/endpoints",
            "/v1/certificates/assessment",
        ):
            assert route in source


def test_certificate_pki_web_catalog_is_bilingual_and_runtime_i18n_is_identical() -> None:
    source_i18n = SOURCE_I18N.read_text(encoding="utf-8")
    runtime_i18n = RUNTIME_I18N.read_text(encoding="utf-8")

    assert runtime_i18n == source_i18n
    assert "Certificates and PKI" in source_i18n
    assert "PKI inventory" in source_i18n
    assert "TLS endpoints" in source_i18n
    assert "PKI compliance" in source_i18n
    assert "Import PEM certificate chain" in source_i18n


def test_pem_bundle_uses_multiline_accessible_control_in_packaged_runtime() -> None:
    static = STATIC_JS.read_text(encoding="utf-8")

    assert '"name": "pem_bundle"' in static
    assert '"type": "textarea"' in static
    assert '<textarea class="form-control font-monospace"' in static
    assert 'rows="10"' in static
