from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ASSETS = ROOT / "src/openinfra/interfaces/rendering/static/assets"
RUNTIME_DOMAINS = RUNTIME_ASSETS / "domains"
REACT_DOMAINS = ROOT / "web/src/domains"
EXPECTED_DOMAINS = {
    "rsot",
    "ipam",
    "dcim",
    "itam",
    "discovery",
    "data",
    "integrations",
    "security",
}
INITIAL_RUNTIME_JS = (
    "openinfra-web.js",
    "openinfra-i18n.js",
    "openinfra-form-fields.js",
    "openinfra-domain-manifest.js",
    "openinfra-query-cache.js",
    "openinfra-virtual-list.js",
    "openinfra-web-vitals.js",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _module_definition(path: Path) -> dict[str, object]:
    source = _read(path)
    match = re.search(r"const moduleDefinition = (\{.*?\n\});\n", source, re.DOTALL)
    assert match is not None, f"missing moduleDefinition in {path}"
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


def test_packaged_runtime_loads_all_business_domains_on_demand() -> None:
    shell = _read(RUNTIME_ASSETS / "openinfra-web.js")
    manifest = _read(RUNTIME_ASSETS / "openinfra-domain-manifest.js")
    domain_files = {path.stem for path in RUNTIME_DOMAINS.glob("*.js")}

    assert domain_files == EXPECTED_DOMAINS
    for domain in sorted(EXPECTED_DOMAINS):
        assert f'import("./domains/{domain}.js?v=0.34.21")' in manifest
    assert '"operations": []' in manifest
    assert '"loaded": false' in manifest
    assert '"path": "/v1/discovery/evidence"' not in shell
    assert "ensureModuleLoaded(moduleId)" in shell
    assert "loadSearchIndex()" in shell


def test_runtime_domain_catalog_preserves_all_unique_operations() -> None:
    operation_ids: list[str] = []
    for path in sorted(RUNTIME_DOMAINS.glob("*.js")):
        module = _module_definition(path)
        operations = module.get("operations")
        assert isinstance(operations, list)
        for operation in operations:
            assert isinstance(operation, dict)
            operation_id = operation.get("id")
            assert isinstance(operation_id, str) and operation_id
            operation_ids.append(operation_id)

    assert len(operation_ids) == 300
    assert len(set(operation_ids)) == 300


def test_react_reference_portal_exposes_a_chunk_for_every_business_domain() -> None:
    manifest = _read(ROOT / "web/src/domain-manifest.js")
    domain_files = {
        path.stem for path in REACT_DOMAINS.glob("*.js") if path.name != "rsot-taxonomy.js"
    }

    assert domain_files == EXPECTED_DOMAINS
    for domain in sorted(EXPECTED_DOMAINS):
        assert f"import('./domains/{domain}.js')" in manifest
    assert "build: {" in _read(ROOT / "web/vite.config.js")
    assert "manifest: true" in _read(ROOT / "web/vite.config.js")


def test_initial_runtime_shell_respects_epic_2004_size_budgets() -> None:
    javascript = b"\n".join((RUNTIME_ASSETS / name).read_bytes() for name in INITIAL_RUNTIME_JS)
    css = (RUNTIME_ASSETS / "openinfra-web.css").read_bytes()
    initial_raw_javascript_bytes = len(javascript)
    initial_shell_gzip_bytes = len(gzip.compress(javascript + b"\n" + css, compresslevel=9))

    assert initial_raw_javascript_bytes <= 250 * 1024
    assert initial_shell_gzip_bytes <= 150 * 1024


def test_query_cache_is_ephemeral_deduplicated_and_generation_safe() -> None:
    runtime_cache = _read(RUNTIME_ASSETS / "openinfra-query-cache.js")
    react_cache = _read(ROOT / "web/src/core/query-cache.js")

    assert runtime_cache == react_cache
    for forbidden_storage in ("localStorage", "sessionStorage", "indexedDB"):
        assert forbidden_storage not in runtime_cache
    for contract in (
        "this.inflight",
        "AbortController",
        "this.generations",
        "invalidate(prefix",
        "this.generations.get(key) !== generation",
    ):
        assert contract in runtime_cache


def test_large_result_virtualization_and_web_vitals_are_integrated() -> None:
    runtime_shell = _read(RUNTIME_ASSETS / "openinfra-web.js")
    react_shell = _read(ROOT / "web/src/main.jsx")
    runtime_virtual = _read(RUNTIME_ASSETS / "openinfra-virtual-list.js")
    runtime_vitals = _read(RUNTIME_ASSETS / "openinfra-web-vitals.js")

    assert "group.items.length > 40" in runtime_shell
    assert "VirtualizedList" in react_shell
    assert "virtualWindow" in runtime_virtual
    assert "LCP: 2500" in runtime_vitals
    assert "INP: 200" in runtime_vitals
    assert "LONG_TASK: 200" in runtime_vitals
    assert "PerformanceObserver" in runtime_vitals
