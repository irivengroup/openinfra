#!/usr/bin/env python3
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

required_files = [
    "00-Delta-v4.6.md",
    "Volumes/V28-Authentification-LDAP-IPA-RBAC-Compte-systeme-FS-LVM.md",
    "03-Technique/13-Authentification-LDAP-IPA-RBAC.md",
    "03-Technique/14-Compte-systeme-et-FS-LVM.md",
    "06-Exploitation/Compte-systeme-et-stockage-LVM.md",
    "08-RFC-ADR/ADR-0013-Authentification-LDAP-IPA-RBAC.md",
    "08-RFC-ADR/ADR-0014-Compte-systeme-et-FS-LVM.md",
    "10-Diagrammes/Auth-LDAP-IPA-RBAC.mmd",
    "10-Diagrammes/System-User-LVM.mmd",
    "11-Matrices/Matrice-authentification-editions-v4.6.csv",
    "11-Matrices/Matrice-rbac-groupes-v4.6.csv",
    "11-Matrices/Matrice-compte-systeme-v4.6.csv",
    "11-Matrices/Matrice-sudoers-openinfra-v4.6.csv",
    "11-Matrices/Matrice-fs-lvm-v4.6.csv",
    "installers/shared/auth/ldap-ipa.example.yaml",
    "installers/shared/system-user/openinfra-user.example.yaml",
    "installers/shared/storage/lvm.example.yaml",
]
for rel in required_files:
    if not (ROOT / rel).is_file():
        errors.append(f"Missing required file: {rel}")

text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*.md"))
for must in [
    "LDAP",
    "IPA",
    "FreeIPA",
    "RBAC",
    "openinfra",
    "rootvg",
    "openinfra_lv",
    "/opt/openinfra/",
    "2GB",
    "openinfra.service",
]:
    if must not in text:
        errors.append(f"Missing required term: {must}")

with (ROOT / "11-Matrices/Matrice-authentification-editions-v4.6.csv").open(
    encoding="utf-8", newline=""
) as f:
    auth = {r["edition"]: r for r in csv.DictReader(f)}
if auth.get("lite", {}).get("ldap") != "non" or auth.get("lite", {}).get("ipa_freeipa") != "non":
    errors.append("Lite must not require LDAP/IPA")
for edition in ["pro", "enterprise"]:
    row = auth.get(edition)
    if not row:
        errors.append(f"Missing auth row for {edition}")
    elif row["ldap"] != "oui" or row["ipa_freeipa"] != "oui" or row["group_rbac"] != "oui":
        errors.append(f"{edition} must support LDAP/IPA and group RBAC")

with (ROOT / "11-Matrices/Matrice-compte-systeme-v4.6.csv").open(encoding="utf-8", newline="") as f:
    account = {r["attribute"]: r["default_value"] for r in csv.DictReader(f)}
expected_account = {
    "user": "openinfra",
    "group": "openinfra",
    "home": "/opt/openinfra/",
    "shell": "/usr/sbin/nologin",
}
for key, value in expected_account.items():
    if account.get(key) != value:
        errors.append(f"Invalid system account default {key}: {account.get(key)}")

with (ROOT / "11-Matrices/Matrice-fs-lvm-v4.6.csv").open(encoding="utf-8", newline="") as f:
    lvm = {r["parameter"]: r["default_value"] for r in csv.DictReader(f)}
expected_lvm = {
    "vgname": "rootvg",
    "lvname": "openinfra_lv",
    "lv_size": "2GB",
    "mountpoint": "/opt/openinfra/",
}
for key, value in expected_lvm.items():
    if lvm.get(key) != value:
        errors.append(f"Invalid LVM default {key}: {lvm.get(key)}")

for rel in [
    "11-Matrices/Matrice-installateurs-scopes-v4.4.csv",
    "11-Matrices/Matrice-installateurs-scopes-v4.5.csv",
]:
    with (ROOT / rel).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row.get("creates_system_user") != "oui" or row.get("creates_lvm_fs") != "oui":
            errors.append(f"Installer scope missing system user or LVM flags: {row}")
        if (
            row.get("default_vg") != "rootvg"
            or row.get("default_lv") != "openinfra_lv"
            or row.get("default_lv_size") != "2GB"
        ):
            errors.append(f"Installer scope invalid LVM defaults: {row}")

with (ROOT / "11-Matrices/Exigences.csv").open(encoding="utf-8", newline="") as f:
    reqs = list(csv.DictReader(f))
ids = {r["id"] for r in reqs}
for number in range(583, 643):
    rid = f"REQ-{number:05d}"
    if rid not in ids:
        errors.append(f"Missing v4.6 requirement {rid}")

with (ROOT / "11-Matrices/Tests.csv").open(encoding="utf-8", newline="") as f:
    tests = {r["id"] for r in csv.DictReader(f)}
for prefix, count in [("TST-AUTH", 18), ("TST-SYS", 14), ("TST-LVM", 14)]:
    for i in range(1, count + 1):
        tid = f"{prefix}-{i:03d}"
        if tid not in tests:
            errors.append(f"Missing test {tid}")

if errors:
    print("\n".join(f"ERROR: {e}" for e in errors))
    raise SystemExit(1)
print(f"OK: auth/LVM v4.6 validated with {len(reqs)} requirements")
