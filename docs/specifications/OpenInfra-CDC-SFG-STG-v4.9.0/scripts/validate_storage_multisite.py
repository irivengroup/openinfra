#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
required = [
    "00-Delta-v4.7.md",
    "Volumes/V29-Stockage-PostgreSQL-Multisite-Replication.md",
    "03-Technique/15-Stockage-PostgreSQL-dedie.md",
    "03-Technique/16-Replication-quasi-synchrone-multisite.md",
    "06-Exploitation/Stockage-PostgreSQL-et-replication.md",
    "08-RFC-ADR/ADR-0015-Stockage-PostgreSQL-separe.md",
    "08-RFC-ADR/ADR-0016-Replication-quasi-synchrone-multisite.md",
    "10-Diagrammes/Storage-PostgreSQL-Dedie.mmd",
    "10-Diagrammes/Multisite-Replication-v4.7.mmd",
    "installers/shared/storage/postgresql-data-lvm.example.yaml",
    "installers/shared/cluster/replication-multisite.example.yaml",
    "11-Matrices/Matrice-stockage-lvm-v4.7.csv",
    "11-Matrices/Matrice-pgsql-service-account-v4.7.csv",
    "11-Matrices/Matrice-symlinks-v4.7.csv",
    "11-Matrices/Matrice-replication-quasi-synchrone-v4.7.csv",
    "11-Matrices/Matrice-multisite-editions-v4.7.csv",
]
for rel in required:
    if not (ROOT / rel).is_file():
        errors.append(f"Missing required file: {rel}")

text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*.md"))
for term in [
    "/opt/openinfra/",
    "/data/openinfra/",
    "datavg",
    "openinfradata_lv",
    "2GB",
    "100GB",
    "1TB",
    "postgresql_service_account",
    "quasi temps réel",
    "multisite",
]:
    if term not in text:
        errors.append(f"Missing required term: {term}")

with (ROOT / "11-Matrices/Matrice-stockage-lvm-v4.7.csv").open(encoding="utf-8", newline="") as f:
    rows = {r["scope"]: r for r in csv.DictReader(f)}
app = rows.get("application", {})
if (
    app.get("vgname") != "rootvg"
    or app.get("lvname") != "openinfra_lv"
    or app.get("mountpoint") != "/opt/openinfra/"
    or app.get("lv_size") != "2GB"
):
    errors.append("Invalid application LVM defaults")
for scope, size in {
    "postgresql_data_lite": "2GB",
    "postgresql_data_pro": "100GB",
    "postgresql_data_enterprise": "1TB",
}.items():
    pg = rows.get(scope, {})
    if (
        pg.get("vgname") != "datavg"
        or pg.get("lvname") != "openinfradata_lv"
        or pg.get("mountpoint") != "/data/openinfra/"
        or pg.get("lv_size") != size
    ):
        errors.append(f"Invalid PostgreSQL LVM defaults for {scope}")
    if pg.get("owner_logical") != "postgresql_service_account":
        errors.append(f"PostgreSQL owner must be logical postgresql_service_account for {scope}")

with (ROOT / "11-Matrices/Matrice-pgsql-service-account-v4.7.csv").open(
    encoding="utf-8", newline=""
) as f:
    acct = {r["logical_name"]: r for r in csv.DictReader(f)}
if acct.get("postgresql_service_account", {}).get("must_be_fixed_username") != "non":
    errors.append("postgresql_service_account must not be a fixed username")

with (ROOT / "11-Matrices/Matrice-symlinks-v4.7.csv").open(encoding="utf-8", newline="") as f:
    syms = list(csv.DictReader(f))
if not any(
    r["symlink"] == "/opt/openinfra/data" and r["target"] == "/data/openinfra/" for r in syms
):
    errors.append("Missing required symlink mapping")

with (ROOT / "11-Matrices/Matrice-replication-quasi-synchrone-v4.7.csv").open(
    encoding="utf-8", newline=""
) as f:
    repl = {r["edition"]: r for r in csv.DictReader(f)}
if repl.get("pro", {}).get("sync_mode_default") != "near_real_time_streaming":
    errors.append("Pro cluster default must be near_real_time_streaming")
if repl.get("enterprise", {}).get("sync_mode_default") != "near_real_time_streaming":
    errors.append("Entreprise cluster default must be near_real_time_streaming")
if repl.get("lite", {}).get("replication") != "non":
    errors.append("Lite must not enable replication")

with (ROOT / "11-Matrices/Matrice-multisite-editions-v4.7.csv").open(
    encoding="utf-8", newline=""
) as f:
    ms = {r["edition"]: r for r in csv.DictReader(f)}
if (
    ms.get("pro", {}).get("multisite_inventory") != "oui"
    or ms.get("pro", {}).get("distributed_agents") != "non"
):
    errors.append("Pro multisite capabilities inconsistent")
if (
    ms.get("enterprise", {}).get("distributed_agents") != "oui"
    or ms.get("enterprise", {}).get("agent_clustering") != "oui"
):
    errors.append("Enterprise multisite distributed capabilities missing")

with (ROOT / "11-Matrices/Exigences.csv").open(encoding="utf-8", newline="") as f:
    reqs = list(csv.DictReader(f))
ids = {r["id"] for r in reqs}
for number in range(643, 695):
    rid = f"REQ-{number:05d}"
    if rid not in ids:
        errors.append(f"Missing v4.7 requirement {rid}")

with (ROOT / "11-Matrices/Tests.csv").open(encoding="utf-8", newline="") as f:
    tests = {r["id"] for r in csv.DictReader(f)}
for prefix, count in [("TST-STOR", 24), ("TST-REPL", 14), ("TST-MSITE", 14)]:
    for i in range(1, count + 1):
        tid = f"{prefix}-{i:03d}"
        if tid not in tests:
            errors.append(f"Missing test {tid}")

if errors:
    print("\n".join(f"ERROR: {e}" for e in errors))
    raise SystemExit(1)
print(
    f"OK: storage/multisite v4.8.1 validated with {len(reqs)} requirements and edition-specific PGDATA sizing"
)
