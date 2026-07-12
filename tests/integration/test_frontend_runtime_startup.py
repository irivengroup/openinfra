from __future__ import annotations

from pathlib import Path

import pytest
from scripts.validate_frontend import FrontendContractValidator, FrontendValidationError

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ASSETS = ROOT / "src/openinfra/interfaces/rendering/static/assets"
RUNTIME_JS = RUNTIME_ASSETS / "openinfra-web.js"
RUNTIME_MANIFEST = RUNTIME_ASSETS / "openinfra-domain-manifest.js"
RUNTIME_SEARCH_INDEX = RUNTIME_ASSETS / "openinfra-search-index.js"
RUNTIME_DOMAIN_ROOT = RUNTIME_ASSETS / "domains"


def test_packaged_runtime_catalog_and_startup_resilience_contract() -> None:
    source = RUNTIME_JS.read_text(encoding="utf-8")

    manifest = RUNTIME_MANIFEST.read_text(encoding="utf-8")
    catalog = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(RUNTIME_DOMAIN_ROOT.glob("*.js"))
    )
    search_index = RUNTIME_SEARCH_INDEX.read_text(encoding="utf-8")

    FrontendContractValidator._validate_static_operation_catalog(
        source, manifest, catalog, search_index
    )
    assert '"name": "cursor"' in catalog
    assert "validateOperationCatalog(OPENINFRA_MODULES)" in source
    assert "this.render();\n    await this.refreshRuntime();" in source
    assert 'fetch("/bootstrap.json"' in source
    assert "void this.refreshReadiness();" in source
    assert "operationCatalogDependencies(operation)" in source
    assert "loadCatalogsForOperation(operation)" in source
    refresh_runtime = source.split("async refreshRuntime()", 1)[1].split(
        "async refreshReadiness()", 1
    )[0]
    assert "refreshCountryCatalog" not in refresh_runtime
    assert "refreshOrganizationCatalog" not in refresh_runtime
    assert "refreshTenantCatalog" not in refresh_runtime
    assert "refreshPartnerCatalog" not in refresh_runtime
    assert "refreshDcimCatalog" not in refresh_runtime
    assert "renderFatalStartupError(openInfraRoot, error)" in source
    assert ".filter((field) => field?.required)" in source


def test_packaged_runtime_validator_rejects_missing_required_operation() -> None:
    source = RUNTIME_JS.read_text(encoding="utf-8")
    manifest = RUNTIME_MANIFEST.read_text(encoding="utf-8")
    catalog = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(RUNTIME_DOMAIN_ROOT.glob("*.js"))
    )
    search_index = RUNTIME_SEARCH_INDEX.read_text(encoding="utf-8")
    broken = catalog.replace('"id": "rsot-list"', '"id": "rsot-list-missing"', 1)

    with pytest.raises(FrontendValidationError, match="rsot-list"):
        FrontendContractValidator._validate_static_operation_catalog(
            source, manifest, broken, search_index
        )
