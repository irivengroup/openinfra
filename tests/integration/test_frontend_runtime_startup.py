from __future__ import annotations

from pathlib import Path

import pytest
from scripts.validate_frontend import FrontendContractValidator, FrontendValidationError

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_JS = ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"


def test_packaged_runtime_catalog_and_startup_resilience_contract() -> None:
    source = RUNTIME_JS.read_text(encoding="utf-8")

    FrontendContractValidator._validate_static_operation_catalog(source)
    assert 'cursor: { name: "cursor"' in source
    assert "validateOperationCatalog(OPENINFRA_MODULES)" in source
    assert "this.render();\n    await this.refreshRuntime();" in source
    assert "renderFatalStartupError(openInfraRoot, error)" in source
    assert ".filter((field) => field?.required)" in source


def test_packaged_runtime_validator_rejects_undefined_shared_fields() -> None:
    source = RUNTIME_JS.read_text(encoding="utf-8")
    broken = source.replace(
        '  cursor: { name: "cursor"',
        '  cursor_missing: { name: "cursor"',
        1,
    )

    with pytest.raises(FrontendValidationError, match="cursor"):
        FrontendContractValidator._validate_static_operation_catalog(broken)
