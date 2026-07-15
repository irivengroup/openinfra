from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ASSETS = ROOT / "src/openinfra/interfaces/rendering/static/assets"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_unified_crud_management_assets_are_packaged_and_synchronized() -> None:
    react_registry = _read("web/src/management/resources.js")
    runtime_registry = _read(
        "src/openinfra/interfaces/rendering/static/assets/management/resources.js"
    )
    react_hierarchy = _read("web/src/management/context-hierarchy.js")
    runtime_hierarchy = _read(
        "src/openinfra/interfaces/rendering/static/assets/management/context-hierarchy.js"
    )
    assert react_registry == runtime_registry
    assert react_hierarchy == runtime_hierarchy
    assert (
        _read("web/src/management-resources.js") == "export * from './management/resources.js';\n"
    )
    assert (
        _read("src/openinfra/interfaces/rendering/static/assets/openinfra-management-resources.js")
        == "export * from './management/resources.js';\n"
    )
    assert "MANAGEMENT_RESOURCES" in react_registry
    assert "MANAGEMENT_CONTEXT_LEVELS" in react_hierarchy
    assert react_registry.count("id: 'dcim-") >= 5
    assert react_registry.count("id: 'itam-") >= 3

    assert _read("web/src/i18n.js") == _read(
        "src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js"
    )
    assert _read("web/src/openinfra-theme.css") == _read(
        "src/openinfra/interfaces/rendering/static/assets/openinfra-web.css"
    )


def test_runtime_management_workspace_preserves_raw_crud_contracts() -> None:
    shell = _read("src/openinfra/interfaces/rendering/static/assets/openinfra-web.js")
    for contract in (
        "collapseManagementOperations",
        "renderManagementWorkspace",
        "openinfra-management-filter-form",
        "openinfra-management-detail-link",
        "data-management-edit",
        "data-management-delete",
        "executeManagementForm",
        "executeManagementDelete",
        "managementIdentityPayload",
        "updateManagementFilters",
        "normalizeManagementFilters",
        "orderManagementContextEntries",
        "isManagementContextAncestor",
        "data-dcim-reference-level",
        "bindDcimReferenceSelects",
        "selectParentContextFirst",
    ):
        assert contract in shell

    dcim = _read("src/openinfra/interfaces/rendering/static/assets/domains/dcim.js")
    itam = _read("src/openinfra/interfaces/rendering/static/assets/domains/itam.js")
    for operation_id in (
        "dcim-site-create",
        "dcim-site-update",
        "dcim-site-delete",
        "dcim-rack-create",
        "dcim-rack-update",
        "dcim-rack-delete",
        "itam-organization-create",
        "itam-organization-update",
        "itam-organization-delete",
        "itam-partner-create",
        "itam-partner-update",
        "itam-partner-delete",
    ):
        assert f'"id": "{operation_id}"' in (dcim if operation_id.startswith("dcim-") else itam)


def test_react_reference_portal_uses_the_same_management_pattern() -> None:
    source = _read("web/src/main.jsx")
    for contract in (
        "collapseManagementOperations",
        "ManagementWorkspace",
        "loadManagementOperationSchema",
        "openinfra-management-table",
        "openinfra-management-detail-link",
        "managementIdentityPayload",
        "updateManagementFilters",
        "normalizeManagementFilters",
        "orderManagementContextEntries",
    ):
        assert contract in source


def test_management_layout_uses_existing_theme_tokens_only() -> None:
    css = _read("web/src/openinfra-theme.css")
    management_css = css[css.index(".openinfra-management-card") :]
    assert "opacity:" not in management_css
    assert "--openinfra-" in management_css
    for forbidden in ("#ff0000", "#00ff00", "#0000ff"):
        assert forbidden not in management_css.lower()
