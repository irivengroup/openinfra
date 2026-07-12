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
    assert "grid-template-columns: repeat(11, minmax(0, 1fr))" in css
    assert "justify-content: flex-end !important" in css
    assert "margin: 0 0 0 auto !important" in css
    assert "minmax(0, 50%)" in css
    assert ".openinfra-component-nav .nav-link.active" in css
    assert "--openinfra-header-nav-active-bg" in css
    assert "background-color: transparent !important" in css
    assert "background-image: var(--openinfra-header-nav-active-bg)" in css
    assert "color: var(--openinfra-header-nav-active-icon)" in css
    assert "opacity: .82" in css
    assert not re.search(
        r"\.openinfra-component-nav \.nav-link\.active,[^}]*"
        r"background:\s*linear-gradient\([^}]*#fff",
        css,
        re.IGNORECASE,
    )


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
    assert "document.addEventListener('keydown', closeResponsiveNavigationFromDocument)" in react_js
    assert 'renderSidebar("compact")' in static_js
    assert 'surface="compact"' in react_js


def test_megamenu_supports_hover_focus_and_click_fallback() -> None:
    static_js = _read(STATIC_JS)
    react_js = _read(REACT_JS)

    assert 'addEventListener("mouseenter", () => this.openMegaMenu' in static_js
    assert 'addEventListener("focus", () => this.openMegaMenu' in static_js
    assert "onMouseEnter={(event) => openMegaMenu(module, event.currentTarget)}" in react_js
    assert "onFocus={(event) => openMegaMenu(module, event.currentTarget)}" in react_js
    assert "openinfra-component-link" in static_js
    assert "openinfra-component-link" in react_js


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    channels: list[float] = []
    for channel in rgb:
        normalized = channel / 255
        channels.append(
            normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4
        )
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(foreground: tuple[int, int, int], background: tuple[int, int, int]) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _blend(
    foreground: tuple[int, int, int],
    background: tuple[int, int, int],
    opacity: float,
) -> tuple[int, int, int]:
    return tuple(
        round(foreground[index] * opacity + background[index] * (1 - opacity)) for index in range(3)
    )


def test_active_header_component_is_translucent_without_white_card() -> None:
    css = _read(STATIC_CSS)

    assert "--openinfra-header-nav-active-color: #e4f7ff" in css
    assert "--openinfra-header-nav-active-icon: #b9f0fc" in css
    assert "--openinfra-header-nav-active-bg: linear-gradient" in css
    assert "background-color: transparent !important" in css
    assert "inset 0 -2px 0 rgba(var(--openinfra-cyan-rgb), .42)" in css

    active_rules = re.findall(
        r"\.openinfra-component-nav \.nav-link\.active,\s*"
        r"\.openinfra-component-nav \.nav-link\[aria-current=\"page\"\]\s*"
        r"\{(?P<body>[^}]*)\}",
        css,
        re.DOTALL,
    )
    assert active_rules
    normal_mode_rules = [rule for rule in active_rules if "background-image" in rule]
    assert normal_mode_rules
    for rule in normal_mode_rules:
        assert "#fff" not in rule.lower()
        assert "rgba(255, 255, 255" not in rule.lower()
        assert "background-color: transparent !important" in rule

    brightest_header_blue = (10, 93, 219)
    active_text = _blend((228, 247, 255), brightest_header_blue, 0.94)
    active_icon = _blend((185, 240, 252), brightest_header_blue, 0.94 * 0.82)
    assert _contrast_ratio(active_text, brightest_header_blue) >= 4.5
    assert _contrast_ratio(active_icon, brightest_header_blue) >= 3.0


def test_active_sidebar_root_hover_changes_only_foreground_to_theme_turquoise() -> None:
    css = _read(STATIC_CSS)

    match = re.search(
        r"\.openinfra-sidebar-dashboard\.active:hover,\s*"
        r"\.openinfra-sidebar-dashboard\.active:focus,\s*"
        r"\.openinfra-accordion-toggle\.active:hover,\s*"
        r"\.openinfra-accordion-toggle\.active:focus\s*"
        r"\{(?P<body>[^}]*)\}",
        css,
        re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    assert "color: var(--openinfra-header-nav-active-icon);" in body
    assert "background" not in body
    assert "border" not in body
    assert "box-shadow" not in body
    assert ".openinfra-accordion-toggle svg" in css
    assert "fill: currentColor" in css
