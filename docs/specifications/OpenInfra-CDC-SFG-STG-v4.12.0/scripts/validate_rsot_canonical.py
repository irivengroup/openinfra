#!/usr/bin/env python3
"""Validate the definitive RSOT canonicalisation contract for CDC 4.12.0."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Final

CDC_ROOT: Final = Path(__file__).resolve().parents[1]
PROJECT_ROOT: Final = CDC_ROOT.parents[2]
MATRIX: Final = CDC_ROOT / "11-Matrices/Matrice-rsot-canonical-v4.11.csv"
EXPECTED_CONTROLS: Final = {
    "RSOT-CLI",
    "RSOT-HTTP",
    "RSOT-RBAC",
    "RSOT-EDITION",
    "RSOT-CODE",
    "RSOT-PACKAGING",
}
FORBIDDEN_ACTIVE_PATTERNS: Final = (
    re.compile(r"\bopeninfra\s+(?:itrm|ri|sot)\b", re.IGNORECASE),
    re.compile(r"/api/v1/(?:itrm|ri|sot)(?:/|\b)", re.IGNORECASE),
    re.compile(r'"(?:itrm|ri|sot):'),
    re.compile(r"\b(?:Itrm|RiQuality|RessourcesInventory)"),
    re.compile(r"it_resources_management|ressources_inventory", re.IGNORECASE),
)
SCAN_ROOTS: Final = (
    "src",
    "scripts",
    "installers",
    "web",
    ".github",
    "docs/api",
    "docs/ga",
    "docs/runbooks",
    "docs/release",
)
ALLOWED_EVIDENCE_FILE: Final = "tests/integration/test_rsot_canonical_contract.py"
EXPECTED_REQUIREMENT: Final = "REQ-00860"
EXPECTED_TEST: Final = "TST-RSOT-163"
SCAN_EXCLUSIONS: Final = {
    "src/openinfra/quality/rsot_canonical_promotion.py",
    "src/openinfra/quality/contract_completeness_promotion.py",
    "docs/runbooks/RSOT_CANONICAL_MIGRATION.md",
    str(Path(__file__).resolve().relative_to(PROJECT_ROOT)),
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


if (CDC_ROOT / "VERSION").read_text(encoding="utf-8").strip() != "4.12.0":
    fail("CDC VERSION must be 4.12.0")
if not MATRIX.is_file():
    fail("missing Matrice-rsot-canonical-v4.11.csv")
with MATRIX.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
controls = {row.get("control_id", "").strip() for row in rows}
if controls != EXPECTED_CONTROLS:
    fail(f"unexpected RSOT controls: {sorted(controls)}")
for row in rows:
    for field in ("surface", "required_state", "evidence"):
        if not row.get(field, "").strip():
            fail(f"empty {field} for {row.get('control_id')}")

for obsolete in (
    "src/openinfra/application/it_resources_management_services.py",
    "src/openinfra/application/it_resources_management_quality_services.py",
    "src/openinfra/application/ressources_inventory_quality_services.py",
):
    if (PROJECT_ROOT / obsolete).exists():
        fail(f"obsolete compatibility module still present: {obsolete}")

for relative_root in SCAN_ROOTS:
    root = PROJECT_ROOT / relative_root
    if not root.exists():
        continue
    for path in root.rglob("*"):
        relative_path = str(path.relative_to(PROJECT_ROOT))
        if relative_path in SCAN_EXCLUSIONS:
            continue
        if not path.is_file() or path.suffix.lower() not in {
            ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".js", ".jsx", ".html"
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_ACTIVE_PATTERNS:
            if pattern.search(text):
                fail(f"legacy RSOT alias in active file {path.relative_to(PROJECT_ROOT)}: {pattern.pattern}")

requirements_text = (CDC_ROOT / "11-Matrices/Exigences.csv").read_text(encoding="utf-8-sig")
tests_text = (CDC_ROOT / "11-Matrices/Tests.csv").read_text(encoding="utf-8-sig")
traceability_text = (CDC_ROOT / "11-Matrices/Traceabilite.csv").read_text(
    encoding="utf-8-sig"
)
if EXPECTED_REQUIREMENT not in requirements_text or EXPECTED_REQUIREMENT not in traceability_text:
    fail(f"missing canonical RSOT requirement: {EXPECTED_REQUIREMENT}")
if EXPECTED_TEST not in tests_text or EXPECTED_TEST not in traceability_text:
    fail(f"missing canonical RSOT test: {EXPECTED_TEST}")

contract_test = PROJECT_ROOT / ALLOWED_EVIDENCE_FILE
if not contract_test.is_file():
    fail(f"missing executable RSOT contract test: {ALLOWED_EVIDENCE_FILE}")
contract_text = contract_test.read_text(encoding="utf-8")
for token in (
    "test_cli_rejects_removed_rsot_aliases",
    "test_http_api_returns_not_found_for_removed_rsot_aliases",
    "test_rbac_rejects_removed_rsot_roles",
    "test_feature_registry_rejects_removed_rsot_capability_aliases",
    "test_removed_rsot_compatibility_modules_are_absent",
):
    if token not in contract_text:
        fail(f"missing RSOT regression proof: {token}")

print(f"OK: CDC 4.12.0 RSOT canonicalisation validated - 6/6 controls, {EXPECTED_REQUIREMENT}, {EXPECTED_TEST}")
