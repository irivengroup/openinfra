#!/usr/bin/env python3
"""Strict validator for OpenInfra roadmap 2.5.0 / CDC 4.12.0."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
PROJECT_ROOT: Final = ROOT.parents[2]
CDC_ROOT: Final = ROOT.parent / "OpenInfra-CDC-SFG-STG-v4.12.0"
HISTORICAL_ROOT: Final = ROOT.parent / "OpenInfra-Roadmap-Developpement-v2.4"
EXPECTED_COUNTS: Final = {
    "02-roadmap-phases.csv": 26,
    "03-roadmap-releases.csv": 16,
    "04-roadmap-epics.csv": 149,
    "05-roadmap-jalons.csv": 18,
    "06-roadmap-dependances.csv": 24,
    "07-roadmap-go-nogo.csv": 15,
    "08-roadmap-risques.csv": 26,
    "09-roadmap-tests-validation.csv": 135,
    "10-roadmap-streams.csv": 14,
    "14-alignement-cdc-v4.12.0.csv": 140,
    "15-plan-livraison-editions.csv": 3,
    "16-plan-installateurs.csv": 6,
    "17-plan-migration-pgdata-lvm.csv": 5,
}
REQUIRED_FILES: Final = (
    "VERSION",
    "00-README.md",
    "01-roadmap-detaillee-openinfra-v2.md",
    *EXPECTED_COUNTS.keys(),
    "11-plan-90-jours.md",
    "12-plan-equipe-et-gouvernance.md",
    "13-validation-roadmap.md",
    "18-plan-licence-runtime-offline.md",
    "19-plan-migration-rsot-canonical.md",
    "20-plan-completude-contractuelle.md",
    "CHANGELOG.md",
)
EXPECTED_GATE_CONTROLS: Final = {
    "license-domain-cryptography",
    "storage-parity",
    "runtime-enforcement",
    "cli-http-contracts",
    "installer-offline-bootstrap",
    "operator-notifications",
    "private-authority-key-exclusion",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_csv(relative_path: str) -> list[dict[str, str]]:
    path = ROOT / relative_path
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail(f"CSV sans en-tête: {relative_path}")
        rows = list(reader)
    malformed = [index for index, row in enumerate(rows, start=2) if None in row]
    if malformed:
        fail(f"colonnes anonymes dans {relative_path}: lignes {malformed[:10]}")
    return rows


def require_unique(rows: list[dict[str, str]], key: str, label: str) -> set[str]:
    values = [row.get(key, "").strip() for row in rows]
    empty = [index for index, value in enumerate(values, start=2) if not value]
    if empty:
        fail(f"identifiants vides dans {label}: lignes {empty[:10]}")
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        fail(f"identifiants dupliqués dans {label}: {duplicates[:10]}")
    return set(values)


def tokens(pattern: str, value: str) -> set[str]:
    return set(re.findall(pattern, value))


for relative_path in REQUIRED_FILES:
    if not (ROOT / relative_path).is_file():
        fail(f"fichier roadmap obligatoire absent: {relative_path}")

if (ROOT / "VERSION").read_text(encoding="utf-8").strip() != "2.5.0":
    fail("VERSION roadmap attendue: 2.5.0")
if (HISTORICAL_ROOT / "VERSION").read_text(encoding="utf-8").strip() != "2.4.0":
    fail("la roadmap historique 2.4.0 a été modifiée")
if (CDC_ROOT / "VERSION").read_text(encoding="utf-8").strip() != "4.12.0":
    fail("CDC actif attendu: 4.12.0")

catalogues: dict[str, list[dict[str, str]]] = {}
for relative_path, expected_count in EXPECTED_COUNTS.items():
    rows = read_csv(relative_path)
    if len(rows) != expected_count:
        fail(f"{relative_path}: {expected_count} lignes attendues, {len(rows)} obtenues")
    catalogues[relative_path] = rows

phases = catalogues["02-roadmap-phases.csv"]
releases = catalogues["03-roadmap-releases.csv"]
epics = catalogues["04-roadmap-epics.csv"]
milestones = catalogues["05-roadmap-jalons.csv"]
dependencies = catalogues["06-roadmap-dependances.csv"]
gates = catalogues["07-roadmap-go-nogo.csv"]
risks = catalogues["08-roadmap-risques.csv"]
validation_tests = catalogues["09-roadmap-tests-validation.csv"]
streams = catalogues["10-roadmap-streams.csv"]
alignment = catalogues["14-alignement-cdc-v4.12.0.csv"]
installers = catalogues["16-plan-installateurs.csv"]
pgdata = catalogues["17-plan-migration-pgdata-lvm.csv"]

phase_ids = require_unique(phases, "id", "phases")
release_ids = require_unique(releases, "id", "releases")
epic_ids = require_unique(epics, "id", "epics")
milestone_ids = require_unique(milestones, "id", "jalons")
gate_ids = require_unique(gates, "id", "gates")
risk_ids = require_unique(risks, "id", "risques")
test_ids = require_unique(validation_tests, "id", "tests")
stream_ids = require_unique(streams, "id", "streams")

if phase_ids != {f"P{index:02d}" for index in range(26)}:
    fail("les phases doivent être exactement P00 à P25")
if release_ids != {f"REL-{index:02d}" for index in range(16)}:
    fail("les releases doivent être exactement REL-00 à REL-15")
if milestone_ids != {f"M{index:02d}" for index in range(18)}:
    fail("les jalons doivent être exactement M00 à M17")
if gate_ids != {f"GATE-{index:02d}" for index in range(15)}:
    fail("les gates doivent être exactement GATE-00 à GATE-14")
if risk_ids != {f"RSK-{index:03d}" for index in range(1, 27)}:
    fail("les risques doivent être exactement RSK-001 à RSK-026")
if not {f"EPIC-230{index}" for index in range(1, 5)}.issubset(epic_ids):
    fail("EPIC-2301 à EPIC-2304 sont obligatoires")
if not {f"EPIC-240{index}" for index in range(1, 5)}.issubset(epic_ids):
    fail("EPIC-2401 à EPIC-2404 sont obligatoires")
if not {f"EPIC-250{index}" for index in range(1, 5)}.issubset(epic_ids):
    fail("EPIC-2501 à EPIC-2504 sont obligatoires")

for row in phases:
    for field in ("phase", "periode_relative", "objectif", "critere_sortie"):
        if not row.get(field, "").strip():
            fail(f"champ {field} vide pour {row['id']}")

for row in releases:
    referenced_phases = tokens(r"P\d{2}", row.get("phases", ""))
    if not referenced_phases:
        fail(f"aucune phase liée à {row['id']}")
    unknown = sorted(referenced_phases - phase_ids)
    if unknown:
        fail(f"phases inconnues pour {row['id']}: {unknown}")

for row in epics:
    if row.get("phase") not in phase_ids:
        fail(f"phase inconnue pour {row['id']}: {row.get('phase')}")
    if row.get("stream") not in stream_ids:
        fail(f"stream inconnu pour {row['id']}: {row.get('stream')}")
    for field in ("priority", "title", "summary", "deliverables", "dependencies", "acceptance"):
        if not row.get(field, "").strip():
            fail(f"champ {field} vide pour {row['id']}")

for row in milestones:
    if row.get("phase") not in phase_ids:
        fail(f"phase inconnue pour {row['id']}")

for row in dependencies:
    if row.get("phase") not in phase_ids:
        fail(f"phase de dépendance inconnue: {row.get('phase')}")
    unknown = sorted(tokens(r"P\d{2}", row.get("depends_on", "")) - phase_ids)
    if unknown:
        fail(f"dépendances de phase inconnues pour {row['phase']}: {unknown}")

for row in gates:
    unknown = sorted(tokens(r"P\d{2}", row.get("phase_scope", "")) - phase_ids)
    if unknown:
        fail(f"phase_scope inconnu pour {row['id']}: {unknown}")
    if not row.get("criteria", "").strip() or not row.get("decision_rule", "").strip():
        fail(f"critères incomplets pour {row['id']}")

for row in risks:
    if row.get("owner_stream") not in stream_ids:
        fail(f"owner_stream inconnu pour {row['id']}: {row.get('owner_stream')}")

for row in validation_tests:
    if row.get("phase") not in phase_ids:
        fail(f"phase inconnue pour le test {row['id']}: {row.get('phase')}")
    for field in ("test_area", "objective", "test_type"):
        if not row.get(field, "").strip():
            fail(f"champ {field} vide pour {row['id']}")

expected_new_tests = {
    "TST-P23-CRYPTO",
    "TST-P23-STORAGE-JSON",
    "TST-P23-STORAGE-POSTGRESQL",
    "TST-P23-STORAGE-ORACLE",
    "TST-P23-ENFORCEMENT",
    "TST-P23-INTERFACES",
    "TST-P23-INSTALLER-FRONTEND",
    "TST-P23-GATE12-PACKAGING",
}
if not expected_new_tests.issubset(test_ids):
    fail(f"tests P23 absents: {sorted(expected_new_tests - test_ids)}")

expected_rsot_tests = {
    "TST-P24-RSOT-CLI-HTTP",
    "TST-P24-RSOT-RBAC-EDITION",
    "TST-P24-RSOT-CODE-PACKAGING",
    "TST-P24-GATE13",
}
if not expected_rsot_tests.issubset(test_ids):
    fail(f"tests P24 absents: {sorted(expected_rsot_tests - test_ids)}")

expected_p25_tests = {
    "TST-P25-CDC-TRACEABILITY",
    "TST-P25-ROADMAP-ALIGNMENT",
    "TST-P25-PROOF-REGISTRY",
    "TST-P25-PYTEST-AUTOMATION",
    "TST-P25-EVIDENCE-CLASSIFICATION",
    "TST-P25-REPOSITORY-HYGIENE",
}
if not expected_p25_tests.issubset(test_ids):
    fail(f"tests P25 absents: {sorted(expected_p25_tests - test_ids)}")

# Validate every structurally explicit phase/epic token in the CDC alignment.
for index, row in enumerate(alignment, start=2):
    if None in row:
        fail(f"colonne anonyme dans l'alignement, ligne {index}")
    for field in ("cdc_decision_id", "decision", "phase", "epic", "release", "validation"):
        if not row.get(field, "").strip():
            fail(f"champ {field} vide dans l'alignement, ligne {index}")
    unknown_phases = sorted(tokens(r"P\d{2}", row["phase"]) - phase_ids)
    unknown_epics = sorted(tokens(r"EPIC-\d{4}", row["epic"]) - epic_ids)
    if unknown_phases:
        fail(f"phases inconnues dans l'alignement ligne {index}: {unknown_phases}")
    if unknown_epics:
        fail(f"epics inconnus dans l'alignement ligne {index}: {unknown_epics}")

new_requirement_rows = {
    row["cdc_decision_id"]: row
    for row in alignment
    if re.fullmatch(r"REQ-008(?:4[6-9]|5[0-9])", row["cdc_decision_id"])
}
expected_new_requirements = {f"REQ-{index:05d}" for index in range(846, 860)}
if set(new_requirement_rows) != expected_new_requirements:
    fail("l'alignement doit contenir exactement REQ-00846 à REQ-00859 pour P23")
for requirement_id, row in new_requirement_rows.items():
    if row["phase"] != "P23" or row["release"] != "REL-13":
        fail(f"{requirement_id} doit cibler P23 / REL-13")
    unknown_tests = sorted(tokens(r"TST-[A-Z0-9-]+", row["validation"]) - test_ids)
    if unknown_tests:
        fail(f"tests inconnus pour {requirement_id}: {unknown_tests}")

rsot_rows = [row for row in alignment if row["cdc_decision_id"] == "REQ-00860"]
if len(rsot_rows) != 1:
    fail("l'alignement doit contenir exactement une ligne REQ-00860")
rsot_row = rsot_rows[0]
if rsot_row["phase"] != "P24" or rsot_row["release"] != "REL-14":
    fail("REQ-00860 doit cibler P24 / REL-14")
rsot_validation_tests = tokens(r"TST-[A-Z0-9-]+", rsot_row["validation"])
expected_rsot_validation_tests = expected_rsot_tests | {"TST-RSOT-163"}
if rsot_validation_tests != expected_rsot_validation_tests:
    fail(
        "REQ-00860 doit référencer TST-RSOT-163 et exactement les quatre tests P24"
    )

completeness_rows = [row for row in alignment if row["cdc_decision_id"] == "REQ-00861"]
if len(completeness_rows) != 1:
    fail("l alignement doit contenir exactement une ligne REQ-00861")
completeness_row = completeness_rows[0]
if completeness_row["phase"] != "P25" or completeness_row["release"] != "REL-15":
    fail("REQ-00861 doit cibler P25 / REL-15")
if tokens(r"EPIC-\d{4}", completeness_row["epic"]) != {f"EPIC-250{i}" for i in range(1, 5)}:
    fail("REQ-00861 doit référencer EPIC-2501 à EPIC-2504")
if not expected_p25_tests.issubset(tokens(r"TST-[A-Z0-9-]+", completeness_row["validation"])):
    fail("REQ-00861 doit référencer les six tests P25")

# Cross-check the new CDC requirements exist in the active CDC catalogue.
with (CDC_ROOT / "11-Matrices/Exigences.csv").open(
    encoding="utf-8-sig", newline=""
) as handle:
    cdc_requirement_ids = {row["id"] for row in csv.DictReader(handle)}
if not (expected_new_requirements | {"REQ-00860", "REQ-00861"}).issubset(cdc_requirement_ids):
    fail("les exigences de licence ne sont pas toutes présentes dans le CDC 4.12.0")

needed_installer_paths = {
    "installers/setup/lite",
    "installers/setup/pro/server",
    "installers/setup/pro/web",
    "installers/setup/enterprise/server",
    "installers/setup/enterprise/web",
    "installers/setup/enterprise/agent",
}
installer_paths = {row.get("path", "") for row in installers}
if installer_paths != needed_installer_paths:
    fail(f"matrice installateurs incohérente: {sorted(installer_paths)}")

pgdata_rows = {(row.get("domain"), row.get("edition"), row.get("lv_size")) for row in pgdata}
for expected in (
    ("PostgreSQL data", "Lite", "2GB"),
    ("PostgreSQL data", "Pro", "100GB"),
    ("PostgreSQL data", "Entreprise", "1TB"),
):
    if expected not in pgdata_rows:
        fail(f"dimensionnement PGDATA absent: {expected}")

policy_path = PROJECT_ROOT / "docs/release/offline-runtime-licensing-promotion-policy.json"
try:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    fail(f"politique GATE-12 illisible: {exc}")
if policy.get("gate_id") != "GATE-12" or policy.get("release_id") != "REL-13":
    fail("la politique produit doit cibler GATE-12 / REL-13")
if set(policy.get("required_controls", [])) != EXPECTED_GATE_CONTROLS:
    fail("la politique produit ne contient pas exactement les sept contrôles GATE-12")

text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in ROOT.rglob("*")
    if path.is_file() and path.suffix.lower() in {".md", ".csv"}
)
for term in (
    "OpenInfra-CDC-SFG-STG-v4.12.0",
    "openinfra.service",
    "openinfra-web.service",
    "openinfra-agent.service",
    "installers/",
    "config/install.ini",
    "/data/openinfra/",
    "/opt/openinfra/data -> /data/openinfra/",
    "PGDATA",
    "Lite",
    "Pro",
    "Entreprise",
    "LDAP/IPA",
    "RBAC",
    "multisite",
    "quasi temps réel",
    "ITSM externes",
    "React + Bootstrap 5",
    "ASGI",
    "PgBouncer",
    "Kubernetes",
    "cloud-native",
    "REL-13",
    "REL-15",
    "GATE-14",
    "667 tests",
    "GATE-12",
    "Ed25519",
    "30 jours",
    "98 %",
):
    if term not in text:
        fail(f"terme contractuel absent: {term}")
if "openinfra-server.service" in text:
    fail("nom de service interdit: openinfra-server.service")
for marker in ("TODO", "TBD", "PLACEHOLDER", "A COMPLETER", "À COMPLÉTER"):
    if marker in text.upper():
        fail(f"marqueur de brouillon détecté: {marker}")
if re.search(r"BEGIN (?:ENCRYPTED )?PRIVATE KEY", text):
    fail("clé privée interdite dans la roadmap")

print(
    "OK: roadmap 2.5.0 validée - "
    "26 phases, 16 releases, 149 epics, 18 jalons, 15 gates, "
    "135 tests, 140 alignements CDC 4.12.0"
)
