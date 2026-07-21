from pathlib import Path


def test_react_and_static_portals_surface_accessible_hourly_license_notifications() -> None:
    react = Path("web/src/main.jsx").read_text(encoding="utf-8")
    static = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-web.js").read_text(
        encoding="utf-8"
    )

    for source in (react, static):
        assert "/v1/license/status" in source
        assert "3_600_000" in source
        assert "openinfra-license-banner" in source
        assert 'aria-live="assertive"' in source
        assert "notification_level" in source
        assert "grace_until" in source
        assert "company_name" in source
        assert "installation_private" not in source
        assert "entitlement.json" not in source


def test_runtime_license_notification_catalog_is_bilingual_and_deployed() -> None:
    canonical = Path("web/src/i18n.js").read_text(encoding="utf-8")
    deployed = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js").read_text(
        encoding="utf-8"
    )

    generator = Path("web/scripts/runtime-i18n-build.mjs").read_text(encoding="utf-8")
    package = Path("web/package.json").read_text(encoding="utf-8")
    assert canonical != deployed
    assert len(deployed) < len(canonical)
    assert "runtimeI18nSource" in generator
    assert "runtimeI18nTarget" in generator
    assert "minify: true" in generator
    assert "generate:runtime-i18n" in package
    for token in (
        "Runtime license",
        "Licence runtime",
        "licenseStatus_grace",
        "licenseUnavailable",
        "licenseGraceUntil",
    ):
        assert token in canonical
        assert token in deployed
