from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_JS = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"
STATIC_CSS = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.css"
REACT_JS = PROJECT_ROOT / "web/src/main.jsx"
REACT_CSS = PROJECT_ROOT / "web/src/openinfra-theme.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_react_and_packaged_runtime_share_responsive_navigation_styles() -> None:
    static_css = _read(STATIC_CSS)
    react_css = _read(REACT_CSS)

    assert static_css == react_css
    assert "--openinfra-header-shadow: 0 .5rem 1.25rem" in static_css
    assert "--openinfra-content-shadow: 0 .16rem .55rem" in static_css
    assert "padding-block: .5rem !important" in static_css
    assert "--openinfra-toolbar-control-height: 2rem" in static_css
    assert "@media (pointer: coarse)" in static_css
    assert "--openinfra-toolbar-control-height: 2.75rem" in static_css


def test_navigation_contract_has_three_non_overlapping_layout_modes() -> None:
    css = _read(STATIC_CSS)

    assert re.search(
        r"@media \(max-width: 1199\.98px\).*?\.openinfra-sidebar\s*\{.*?display: none !important;",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"@media \(min-width: 768px\) and \(max-width: 1199\.98px\).*?"
        r"\.openinfra-mega-menu\s*\{.*?display: block;",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"@media \(max-width: 767\.98px\).*?\.openinfra-component-nav\s*\{.*?display: none;",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"@media \(max-width: 767\.98px\).*?\.openinfra-compact-menu-button\s*\{.*?"
        r"display: inline-flex;",
        css,
        re.DOTALL,
    )
    assert "grid-template-columns: repeat(10, minmax(0, 1fr))" in css
    assert "justify-content: flex-end !important" in css
    assert "margin: 0 0 0 auto !important" in css
    assert "minmax(0, 50%)" in css
    assert ".openinfra-component-nav .nav-link.active" in css


def test_both_portals_expose_accessible_megamenu_and_compact_navigation() -> None:
    static_js = _read(STATIC_JS)
    react_js = _read(REACT_JS)

    for source in (static_js, react_js):
        assert "openinfra-component-nav" in source
        assert "openinfra-mega-menu" in source
        assert "openinfra-compact-menu-button" in source
        assert "openinfra-compact-navigation" in source
        assert "openinfra-navigation-backdrop" in source
        assert "openinfra-toolbar-actions" in source
        assert "aria-haspopup" in source
        assert "aria-expanded" in source
        assert "closeResponsiveNavigation" in source
        assert "isMegamenuViewport" in source
        assert "openMegaMenu" in source

    assert 'document.addEventListener("keydown", this.handleDocumentKeydown)' in static_js
    assert "document.addEventListener('keydown', closeResponsiveNavigation)" in react_js
    assert 'renderSidebar("compact")' in static_js
    assert 'surface="compact"' in react_js


def test_megamenu_supports_hover_focus_and_click_fallback() -> None:
    static_js = _read(STATIC_JS)
    react_js = _read(REACT_JS)

    assert 'addEventListener("mouseenter", () => this.openMegaMenu' in static_js
    assert 'addEventListener("focus", () => this.openMegaMenu' in static_js
    assert "onMouseEnter={() => openMegaMenu(module)}" in react_js
    assert "onFocus={() => openMegaMenu(module)}" in react_js
    assert "openinfra-component-link" in static_js
    assert "openinfra-component-link" in react_js
