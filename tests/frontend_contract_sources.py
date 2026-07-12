from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class FrontendSourceBundle:
    paths: tuple[Path, ...]

    def read_text(self, encoding: str = "utf-8") -> str:
        return "\n".join(path.read_text(encoding=encoding) for path in self.paths)

    def read_bytes(self) -> bytes:
        return b"\n".join(path.read_bytes() for path in self.paths)


_REACT_DOMAIN_ROOT = PROJECT_ROOT / "web/src/domains"
_RUNTIME_ASSET_ROOT = PROJECT_ROOT / "src/openinfra/interfaces/rendering/static/assets"
_RUNTIME_DOMAIN_ROOT = _RUNTIME_ASSET_ROOT / "domains"

REACT_PORTAL = FrontendSourceBundle(
    (
        PROJECT_ROOT / "web/src/main.jsx",
        PROJECT_ROOT / "web/src/domain-manifest.js",
        *tuple(sorted(_REACT_DOMAIN_ROOT.glob("*.js"))),
        PROJECT_ROOT / "web/src/search-index.js",
    )
)

RUNTIME_PORTAL = FrontendSourceBundle(
    (
        _RUNTIME_ASSET_ROOT / "openinfra-web.js",
        _RUNTIME_ASSET_ROOT / "openinfra-domain-manifest.js",
        *tuple(sorted(_RUNTIME_DOMAIN_ROOT.glob("*.js"))),
        _RUNTIME_ASSET_ROOT / "openinfra-search-index.js",
    )
)


def javascript_contract_text(source: str) -> str:
    """Return source plus a whitespace-normalized view of JSON-style JS objects.

    Modular domain chunks are generated as JSON-compatible JavaScript. The normalized
    suffix lets legacy contract assertions remain semantic while the original source is
    still present for exact runtime checks.
    """
    legacy = re.sub(r'"([A-Za-z_$][A-Za-z0-9_$]*)"\s*:', r"\1:", source)
    legacy = re.sub(r"\s+", " ", legacy).strip()
    return source + "\n" + legacy
