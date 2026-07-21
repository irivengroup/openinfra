#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required_files = [
    "Volumes/V26-Installation-autonome-cluster.md",
    "Volumes/V27-Service-backend-canonique.md",
    "03-Technique/11-Installation-autonome-cluster.md",
    "03-Technique/12-Installateurs-hors-src-et-migrations.md",
    "06-Exploitation/Installation-bootstrap-cluster.md",
    "08-RFC-ADR/ADR-0011-Installation-autonome-cluster.md",
    "08-RFC-ADR/ADR-0012-Installateurs-hors-src-et-migrations-backend.md",
    "10-Diagrammes/Installation-autonome-cluster.mmd",
    "11-Matrices/Matrice-installateurs-scopes-v4.4.csv",
    "11-Matrices/Matrice-installateurs-scopes-v4.5.csv",
    "11-Matrices/Matrice-dependances-installation-v4.4.csv",
    "11-Matrices/Matrice-migrations-backend-v4.4.csv",
    "11-Matrices/Matrice-ports-flux-installation-v4.4.csv",
    "11-Matrices/Matrice-installation-autonome-v4.4.csv",
    "installers/README.md",
    "installers/setup/lite/README.md",
    "installers/setup/pro/server/README.md",
    "installers/setup/pro/web/README.md",
    "installers/setup/enterprise/server/README.md",
    "installers/setup/enterprise/web/README.md",
    "installers/setup/enterprise/agent/README.md",
    "installers/shared/network/inventory.example.yaml",
    "installers/shared/system-user/openinfra-user.example.yaml",
    "installers/shared/storage/lvm.example.yaml",
]
for rel in required_files:
    if not (ROOT / rel).is_file():
        errors.append(f"Missing required file: {rel}")

if (ROOT / "src" / "installers").exists():
    errors.append("installers directory must not be inside src")

text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*.md"))
for must in [
    "FQDN",
    "IP",
    "masque",
    "VIP",
    "passerelle",
    "DNS",
    "openinfra.service",
    "openinfra-web.service",
    "openinfra-agent.service",
    "installers/",
    "toutes les migrations backend",
    "React + Bootstrap 5",
    "openinfra_lv",
    "rootvg",
    "/opt/openinfra/",
    "2GB",
]:
    if must not in text:
        errors.append(f"Missing required wording: {must}")

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

with (ROOT / "11-Matrices/Exigences.csv").open(encoding="utf-8", newline="") as f:
    reqs = list(csv.DictReader(f))
ids = {r["id"] for r in reqs}
for number in range(509, 583):
    rid = f"REQ-{number:05d}"
    if rid not in ids:
        errors.append(f"Missing installer/service requirement {rid}")

with (ROOT / "11-Matrices/Matrice-installateurs-scopes-v4.4.csv").open(
    encoding="utf-8", newline=""
) as f:
    scopes = list(csv.DictReader(f))
expected = {
    ("lite", "all-in-one", "installers/setup/lite", "openinfra.service"),
    ("pro", "server", "installers/setup/pro/server", "openinfra.service"),
    ("pro", "web", "installers/setup/pro/web", "openinfra-web.service"),
    ("enterprise", "server", "installers/setup/enterprise/server", "openinfra.service"),
    ("enterprise", "web", "installers/setup/enterprise/web", "openinfra-web.service"),
    ("enterprise", "agent", "installers/setup/enterprise/agent", "openinfra-agent.service"),
}
actual = {(r["edition"], r["scope"], r["installer_path"], r["systemd_service"]) for r in scopes}
if expected - actual:
    errors.append(f"Missing installer scope rows: {sorted(expected - actual)}")
if any(r["systemd_service"] == "openinfra-server.service" for r in scopes):
    errors.append("Installer matrix must not use openinfra-server.service")
for r in scopes:
    if r["installs_dependencies"] != "oui":
        errors.append(f"Installer must install dependencies: {r}")
    if r["scope"] == "server" and r["applies_migrations"] != "oui":
        errors.append(f"Server installer must apply migrations: {r}")
    if r["scope"] in {"web", "agent"} and r["applies_migrations"] != "non":
        errors.append(f"Web/agent installer must not apply migrations: {r}")

with (ROOT / "11-Matrices/Matrice-migrations-backend-v4.4.csv").open(
    encoding="utf-8", newline=""
) as f:
    migs = list(csv.DictReader(f))
if not any(r["phase"] == "apply" and r["responsible_scope"] == "server" for r in migs):
    errors.append("Migration matrix must include server apply phase")
if not any(r["phase"] == "forbidden_web" for r in migs):
    errors.append("Migration matrix must forbid web migrations")
if not any(r["phase"] == "forbidden_agent" for r in migs):
    errors.append("Migration matrix must forbid agent migrations")

if errors:
    print("\n".join(f"ERROR: {e}" for e in errors))
    raise SystemExit(1)
print(
    f"OK: autonomous installer v4.6 validated with {len(reqs)} requirements and {len(scopes)} installer scopes"
)
