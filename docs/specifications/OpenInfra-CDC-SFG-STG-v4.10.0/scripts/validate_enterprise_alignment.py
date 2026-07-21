#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required = [
    "Volumes/V25-Editions-Packaging-Alignement-Entreprise.md",
    "Volumes/V27-Service-backend-canonique.md",
    "09-API/Integrations-ITSM-externes.md",
    "03-Technique/10-Architecture-par-edition.md",
    "02-Fonctionnel/25-Garantie-support-constructeur-et-tiers.md",
    "11-Matrices/Matrice-capacites-editions-v4.3.csv",
    "11-Matrices/Matrice-services-systemd-v4.3.csv",
    "11-Matrices/Matrice-services-systemd-v4.5.csv",
    "11-Matrices/Matrice-integrations-ITSM-v4.3.csv",
    "11-Matrices/Matrice-alignement-enterprise-v4.3.csv",
]
for rel in required:
    if not (ROOT / rel).is_file():
        errors.append(f"Missing required file: {rel}")

text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*.md"))
for must in [
    "openinfra.service",
    "openinfra-web.service",
    "openinfra-agent.service",
    "React + Bootstrap 5",
    "aucun ITSM intégré",
    "support constructeur",
    "LDAP",
    "IPA",
    "RBAC",
    "openinfra_lv",
]:
    if must not in text:
        errors.append(f"Missing required term: {must}")

# forbidden edition-coupled service names in documentation, except if listed as forbidden examples.
for forbidden in [
    "openinfra-pro-server.service",
    "openinfra-enterprise-server.service",
    "openinfra-proxy.service",
    "openinfra-proxy-worker.service",
]:
    occurrences = [
        line
        for line in text.splitlines()
        if forbidden in line and "Interdit" not in line and not line.strip().startswith("- `")
    ]
    if occurrences:
        errors.append(f"Forbidden service name used outside forbidden list: {forbidden}")

# requirements uniqueness and count
req_path = ROOT / "11-Matrices/Exigences.csv"
with req_path.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
ids = [r["id"] for r in rows]
if len(ids) != len(set(ids)):
    errors.append("Duplicate requirement IDs detected")
for rid in [
    "REQ-00489",
    "REQ-00490",
    "REQ-00492",
    "REQ-00493",
    "REQ-00495",
    "REQ-00496",
    "REQ-00498",
    "REQ-00499",
    "REQ-00508",
    "REQ-00571",
    "REQ-00582",
]:
    if rid not in set(ids):
        errors.append(f"Missing requirement {rid}")

# editions matrix checks
cap_path = ROOT / "11-Matrices/Matrice-capacites-editions-v4.3.csv"
with cap_path.open(encoding="utf-8", newline="") as f:
    caps = {r["edition"]: r for r in csv.DictReader(f)}
if set(caps) != {"lite", "pro", "enterprise"}:
    errors.append("Edition matrix must contain exactly lite, pro, enterprise")
if caps["lite"]["itsm_connectors"] != "non":
    errors.append("Lite must not have ITSM connectors")
if caps["pro"]["itsm_connectors"] != "oui" or caps["enterprise"]["itsm_connectors"] != "oui":
    errors.append("Pro and Entreprise must have ITSM connectors")
if caps["enterprise"]["autodiscovery_agent"] != "oui":
    errors.append("Entreprise must support autodiscovery agents")

# services matrix checks
svc_path = ROOT / "11-Matrices/Matrice-services-systemd-v4.3.csv"
with svc_path.open(encoding="utf-8", newline="") as f:
    services = list(csv.DictReader(f))
svc_names = {r["service"] for r in services}
for name in {"openinfra.service", "openinfra-web.service", "openinfra-agent.service"}:
    if name not in svc_names:
        errors.append(f"Missing systemd service {name}")
if "openinfra-server.service" in svc_names:
    errors.append("openinfra-server.service must not be present in operational systemd matrix")
for r in services:
    if r["edition_name_allowed"].lower() != "non":
        errors.append(f"Edition name allowed for service {r['service']}")
    if any(token in r["service"] for token in ["lite", "pro", "enterprise", "enterprise"]):
        errors.append(f"Service contains edition token: {r['service']}")

# ITSM matrix checks
itsm_path = ROOT / "11-Matrices/Matrice-integrations-ITSM-v4.3.csv"
with itsm_path.open(encoding="utf-8", newline="") as f:
    itsm = {r["solution"]: r for r in csv.DictReader(f)}
for solution in ["ServiceNow", "Jira Service Management", "GLPI", "Freshservice"]:
    if solution not in itsm:
        errors.append(f"Missing ITSM connector {solution}")
    else:
        if (
            itsm[solution]["lite"] != "non"
            or itsm[solution]["pro"] != "oui"
            or itsm[solution]["enterprise"] != "oui"
        ):
            errors.append(f"Invalid edition support for {solution}")

if errors:
    print("\n".join(f"ERROR: {e}" for e in errors))
    raise SystemExit(1)
print(
    f"OK: enterprise alignment v4.6 validated with {len(rows)} requirements and {len(services)} systemd services"
)
