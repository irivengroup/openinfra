from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE_I18N: Final = PROJECT_ROOT / "web/src/i18n.js"
RUNTIME_I18N: Final = (
    PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js"
)
GENERATED_HEADER_PREFIX: Final = "// Generated from web/src/i18n.js by Rolldown. Source SHA-256: "


def assert_runtime_i18n_contract(*required_tokens: str) -> None:
    """Validate the generated runtime catalog without requiring byte identity.

    Semantic equivalence and reproducibility are exercised by the Node test suite,
    which rebuilds the asset with Rolldown. Python integration tests only assert the
    packaging contract and the domain labels they own.
    """

    source = SOURCE_I18N.read_text(encoding="utf-8")
    runtime = RUNTIME_I18N.read_text(encoding="utf-8")

    source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    generated_header = f"{GENERATED_HEADER_PREFIX}{source_digest}. Do not edit.\n"
    assert runtime.startswith(generated_header)
    assert len(runtime.encode("utf-8")) < len(source.encode("utf-8"))
    for token in required_tokens:
        assert token in source
        assert token in runtime
