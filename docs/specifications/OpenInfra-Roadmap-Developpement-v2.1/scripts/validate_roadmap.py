#!/usr/bin/env python3
from __future__ import annotations
import csv
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = [
    "00-README.md",
    "01-roadmap-detaillee-openinfra-v2.md",
    "02-roadmap-phases.csv",
    "03-roadmap-releases.csv",
    "04-roadmap-epics.csv",
    "05-roadmap-jalons.csv",
    "06-roadmap-dependances.csv",
    "07-roadmap-go-nogo.csv",
    "08-roadmap-risques.csv",
    "09-roadmap-tests-validation.csv",
    "10-roadmap-streams.csv",
    "11-plan-90-jours.md",
    "12-plan-equipe-et-gouvernance.md",
    "13-validation-roadmap.md",
    "14-alignement-cdc-v4.9.0.csv",
    "15-plan-livraison-editions.csv",
    "16-plan-installateurs.csv",
    "17-plan-migration-pgdata-lvm.csv",
    "CHANGELOG.md",
]
for rel in required:
    if not (root / rel).exists():
        raise SystemExit(f"Missing required file: {rel}")


def read_csv(rel):
    with (root / rel).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


phases = read_csv("02-roadmap-phases.csv")
epics = read_csv("04-roadmap-epics.csv")
gates = read_csv("07-roadmap-go-nogo.csv")
tests = read_csv("09-roadmap-tests-validation.csv")
alignment = read_csv("14-alignement-cdc-v4.9.0.csv")
installers = read_csv("16-plan-installateurs.csv")
pg = read_csv("17-plan-migration-pgdata-lvm.csv")
if len(phases) < 21:
    raise SystemExit(f"Expected at least 21 phases, got {len(phases)}")
if len(epics) < 125:
    raise SystemExit(f"Expected at least 125 epics, got {len(epics)}")
if len(gates) < 10:
    raise SystemExit(f"Expected at least 10 gates, got {len(gates)}")
if len(tests) < 100:
    raise SystemExit(f"Expected at least 100 tests, got {len(tests)}")
if len(alignment) < 20:
    raise SystemExit(f"Expected at least 20 CDC alignment rows, got {len(alignment)}")
text = "\n".join(
    p.read_text(encoding="utf-8")
    for p in root.rglob("*")
    if p.is_file() and p.suffix in {".md", ".csv"} and p.name != "SHA256SUMS.txt"
)
required_terms = [
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
    "2GB",
    "100GB",
    "1TB",
    "ASGI",
    "PgBouncer",
    "p95",
    "p99",
    "streaming",
]
for term in required_terms:
    if term not in text:
        raise SystemExit(f"Missing required term: {term}")
if "openinfra-server.service" in text:
    raise SystemExit("Forbidden service name found: openinfra-server.service")
for marker in ["TODO", "TBD", "PLACEHOLDER", "A COMPLETER", "À COMPLÉTER"]:
    if marker in text:
        raise SystemExit(f"Draft marker found: {marker}")
expected_paths = {row["path"] for row in installers}
needed = {
    "installers/setup/lite",
    "installers/setup/pro/server",
    "installers/setup/pro/web",
    "installers/setup/enterprise/server",
    "installers/setup/enterprise/web",
    "installers/setup/enterprise/agent",
}
missing = needed - expected_paths
if missing:
    raise SystemExit(f"Missing installer paths: {sorted(missing)}")
pg_rows = {(row["domain"], row["edition"], row["lv_size"]) for row in pg}
for expected in [
    ("PostgreSQL data", "Lite", "2GB"),
    ("PostgreSQL data", "Pro", "100GB"),
    ("PostgreSQL data", "Entreprise", "1TB"),
]:
    if expected not in pg_rows:
        raise SystemExit(f"Missing PGDATA sizing: {expected}")
print(
    f"OK: roadmap v2.1 validated with {len(phases)} phases, {len(epics)} epics, {len(gates)} gates, {len(tests)} tests"
)
