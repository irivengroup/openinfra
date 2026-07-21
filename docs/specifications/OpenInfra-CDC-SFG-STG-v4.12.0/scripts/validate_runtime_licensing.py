#!/usr/bin/env python3
"""Validate the OpenInfra CDC 4.12.0 offline runtime licensing increment."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Final

CDC_ROOT: Final = Path(__file__).resolve().parents[1]
PROJECT_ROOT: Final = CDC_ROOT.parents[2]
MATRICES: Final = CDC_ROOT / "11-Matrices"
EXPECTED_REQUIREMENTS: Final = 861
EXPECTED_TESTS: Final = 667
EXPECTED_TRACE_ROWS: Final = 861
EXPECTED_CONTROLS: Final = {
    "license-domain-cryptography",
    "storage-parity",
    "runtime-enforcement",
    "cli-http-contracts",
    "installer-offline-bootstrap",
    "operator-notifications",
    "private-authority-key-exclusion",
}
REQUIRED_FILES: Final = (
    "VERSION",
    "00-README.md",
    "00-Delta-v4.10.md",
    "00-Delta-v4.12.md",
    "03-Technique/19-Licence-runtime-offline.md",
    "08-RFC-ADR/ADR-0021-Licence-runtime-offline.md",
    "Volumes/V31-Licence-runtime-offline.md",
    "09-API/OpenAPI/openapi.yaml",
    "11-Matrices/Exigences.csv",
    "11-Matrices/Tests.csv",
    "11-Matrices/Traceabilite.csv",
    "11-Matrices/Matrice-licence-runtime-offline-v4.10.csv",
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail(f"CSV sans en-tête: {path.relative_to(CDC_ROOT)}")
        rows = list(reader)
    malformed = [index for index, row in enumerate(rows, start=2) if None in row]
    if malformed:
        fail(
            f"colonnes anonymes dans {path.relative_to(CDC_ROOT)} aux lignes "
            f"{malformed[:5]}"
        )
    return rows


def require_non_empty(row: dict[str, str], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if not row.get(field, "").strip()]
    if missing:
        fail(f"champs vides {missing} pour {label}")


for relative_path in REQUIRED_FILES:
    if not (CDC_ROOT / relative_path).is_file():
        fail(f"fichier CDC obligatoire absent: {relative_path}")

version = (CDC_ROOT / "VERSION").read_text(encoding="utf-8").strip()
if version != "4.12.0":
    fail(f"VERSION CDC attendue 4.12.0, obtenue {version!r}")

requirements = read_csv(MATRICES / "Exigences.csv")
tests = read_csv(MATRICES / "Tests.csv")
traceability = read_csv(MATRICES / "Traceabilite.csv")
license_matrix = read_csv(MATRICES / "Matrice-licence-runtime-offline-v4.10.csv")

if len(requirements) != EXPECTED_REQUIREMENTS:
    fail(f"861 exigences attendues, {len(requirements)} obtenues")
if len(tests) != EXPECTED_TESTS:
    fail(f"667 tests attendus, {len(tests)} obtenus")
if len(traceability) != EXPECTED_TRACE_ROWS:
    fail(f"861 lignes de traçabilité attendues, {len(traceability)} obtenues")

requirement_ids: list[str] = []
for row in requirements:
    requirement_id = row.get("id", "").strip()
    if not re.fullmatch(r"REQ-\d{5}", requirement_id):
        fail(f"identifiant d'exigence invalide: {requirement_id!r}")
    require_non_empty(
        row,
        ("volume", "domain", "type", "priority", "requirement", "verification", "acceptance"),
        requirement_id,
    )
    requirement_ids.append(requirement_id)

expected_requirement_ids = [f"REQ-{index:05d}" for index in range(1, 862)]
if requirement_ids != expected_requirement_ids:
    fail("la séquence des exigences doit être exactement REQ-00001 à REQ-00861")
if len(set(requirement_ids)) != len(requirement_ids):
    fail("identifiants d'exigences dupliqués")

requirement_id_set = set(requirement_ids)
test_ids: list[str] = []
for row in tests:
    test_id = row.get("id", "").strip()
    if not re.fullmatch(r"TST-[A-Z0-9]+(?:-[A-Z0-9]+)*", test_id):
        fail(f"identifiant de test invalide: {test_id!r}")
    require_non_empty(row, ("type", "scope", "method", "acceptance", "linked"), test_id)
    linked_requirement_ids = set(re.findall(r"REQ-\d{5}", row["linked"]))
    unknown_linked_ids = sorted(linked_requirement_ids - requirement_id_set)
    if unknown_linked_ids:
        fail(f"exigences inconnues liées à {test_id}: {unknown_linked_ids}")
    test_ids.append(test_id)

if len(set(test_ids)) != len(test_ids):
    duplicates = sorted(test_id for test_id, count in Counter(test_ids).items() if count > 1)
    fail(f"identifiants de tests dupliqués: {duplicates}")
test_id_set = set(test_ids)

required_test_ids = {
    "TST-WEB-091",
    "TST-WEB-092",
    "TST-WEB-095",
    *(f"TST-LIC-{index}" for index in range(146, 163)),
    "TST-RSOT-163",
}
missing_required_tests = sorted(required_test_ids - test_id_set)
if missing_required_tests:
    fail(f"tests v4.12 obligatoires absents: {missing_required_tests}")

trace_requirement_ids: list[str] = []
for row in traceability:
    requirement_id = row.get("requirement_id", "").strip()
    require_non_empty(
        row,
        ("requirement_id", "requirement_priority", "domain", "test_id", "verification"),
        requirement_id or "ligne de traçabilité",
    )
    if requirement_id not in requirement_id_set:
        fail(f"exigence inconnue dans la traçabilité: {requirement_id}")
    referenced_tests = {
        value.strip() for value in row["test_id"].split(";") if value.strip()
    }
    if not referenced_tests:
        fail(f"aucun test associé à {requirement_id}")
    unknown_tests = sorted(referenced_tests - test_id_set)
    if unknown_tests:
        fail(f"tests inconnus pour {requirement_id}: {unknown_tests}")
    trace_requirement_ids.append(requirement_id)

trace_counts = Counter(trace_requirement_ids)
duplicated_trace = sorted(key for key, count in trace_counts.items() if count != 1)
if duplicated_trace:
    fail(f"exigences non tracées exactement une fois: {duplicated_trace[:10]}")
missing_trace = sorted(requirement_id_set - set(trace_requirement_ids))
if missing_trace:
    fail(f"exigences sans traçabilité: {missing_trace[:10]}")

expected_new_requirements = {f"REQ-{index:05d}" for index in range(846, 860)}
if not expected_new_requirements.issubset(requirement_id_set):
    fail("les exigences REQ-00846 à REQ-00859 ne sont pas toutes présentes")

if len(license_matrix) < 7:
    fail("la matrice de licence doit couvrir au moins les sept preuves GATE-12")
for row in license_matrix:
    require_non_empty(
        row,
        ("control_id", "edition", "requirement", "enforcement", "evidence"),
        row.get("control_id", "contrôle licence"),
    )

openapi_text = (CDC_ROOT / "09-API/OpenAPI/openapi.yaml").read_text(encoding="utf-8")
for token in (
    "/api/v1/license/status",
    "/api/v1/license/activate",
    "/api/v1/license/renew",
    "Plateforme · Licence runtime",
):
    if token not in openapi_text:
        fail(f"contrat OpenAPI licence incomplet: {token}")

for migration in (
    "installers/migrations/postgresql/0059_runtime_offline_licensing.sql",
    "installers/migrations/oracle/0059_runtime_offline_licensing.sql",
):
    if not (PROJECT_ROOT / migration).is_file():
        fail(f"migration 0059 absente: {migration}")

policy_path = PROJECT_ROOT / "docs/release/offline-runtime-licensing-promotion-policy.json"
try:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    fail(f"politique GATE-12 illisible: {exc}")
if policy.get("gate_id") != "GATE-12" or policy.get("release_id") != "REL-13":
    fail("la politique doit cibler GATE-12 et REL-13")
if set(policy.get("required_controls", [])) != EXPECTED_CONTROLS:
    fail("la politique GATE-12 ne déclare pas exactement les sept contrôles attendus")

for project_file in (
    "docs/runbooks/OFFLINE_RUNTIME_LICENSING.md",
    "src/openinfra/quality/offline_licensing_promotion.py",
    "tests/unit/test_runtime_offline_licensing.py",
    "tests/unit/test_gate12_qualification.py",
):
    if not (PROJECT_ROOT / project_file).is_file():
        fail(f"actif produit GATE-12 absent: {project_file}")

for path in CDC_ROOT.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".yaml", ".yml"}:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    upper_text = text.upper()
    for marker in ("TODO", "PLACEHOLDER", "TBD", "À COMPLÉTER", "A COMPLETER"):
        if marker in upper_text:
            fail(f"marqueur de brouillon {marker!r} dans {path.relative_to(CDC_ROOT)}")
    if "OPENINFRA_LICENSE_AUTHORITY_PRIVATE_KEY" in upper_text or re.search(
        r"BEGIN (?:ENCRYPTED )?PRIVATE KEY", text
    ):
        fail(f"matériel privé d'autorité interdit dans {path.relative_to(CDC_ROOT)}")

print(
    "OK: CDC 4.12.0 validé - "
    f"{len(requirements)} exigences, {len(tests)} tests, "
    f"{len(traceability)} traces, 7 contrôles GATE-12"
)
