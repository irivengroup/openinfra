from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REACT_JS = PROJECT_ROOT / "web/src/main.jsx"
RUNTIME_JS = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"
REACT_CSS = PROJECT_ROOT / "web/src/openinfra-theme.css"
RUNTIME_CSS = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.css"
REACT_HTML = PROJECT_ROOT / "web/index.html"
RUNTIME_HTML = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/index.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_accessibility_contract_is_shared_by_react_and_packaged_portals() -> None:
    react_js = _read(REACT_JS)
    runtime_js = _read(RUNTIME_JS)
    react_css = _read(REACT_CSS)
    runtime_css = _read(RUNTIME_CSS)

    assert react_css == runtime_css
    for source in (react_js, runtime_js):
        for token in (
            "openinfra-skip-links",
            "openinfra-live-region",
            "openinfra-component-navigation",
            "componentNavigationInstructions",
            "skipToNavigation",
            "skipToSearch",
            'role="status"',
            'aria-live="polite"',
            'aria-atomic="true"',
            "ArrowRight",
            "ArrowLeft",
            "ArrowDown",
            "Home",
            "End",
            "opensNewWindow",
        ):
            assert token in source

    for token in (
        "@media (prefers-reduced-motion: reduce)",
        "@media (prefers-contrast: more)",
        "@media (forced-colors: active)",
        "openinfra-component-bounce-fade",
        "openinfra-megamenu-bounce-fade",
        "openinfra-required-marker",
        "openinfra-error-summary",
        "scroll-padding-top",
    ):
        assert token in runtime_css


def test_root_container_does_not_create_nested_main_landmarks() -> None:
    assert '<main id="openinfra-root"' not in _read(REACT_HTML)
    assert '<main id="openinfra-root"' not in _read(RUNTIME_HTML)
    assert '<div id="openinfra-root"' in _read(REACT_HTML)
    assert '<div id="openinfra-root"' in _read(RUNTIME_HTML)


def test_portal_has_no_sound_only_or_uncaptioned_media_contract() -> None:
    combined = "\n".join(
        (_read(REACT_JS), _read(RUNTIME_JS), _read(REACT_HTML), _read(RUNTIME_HTML))
    ).lower()
    assert "<audio" not in combined
    assert "<video" not in combined
    assert "new audio(" not in combined


def test_packaged_form_validation_is_exposed_to_assistive_technology() -> None:
    runtime_js = _read(RUNTIME_JS)
    for token in (
        'id="openinfra-operation-form"',
        "requiredFieldsNotice",
        "requiredIndicator",
        "aria-invalid",
        "checkValidity()",
        "reportValidity()",
        'role="alert"',
    ):
        assert token in runtime_js
