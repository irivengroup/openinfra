#!/usr/bin/env python3
from __future__ import annotations

import configparser
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

expected = [
    ("lite", "all-in-one", "installers/setup/lite/install.ini", "openinfra.service"),
    ("pro", "server", "installers/setup/pro/server/install.ini", "openinfra.service"),
    ("pro", "web", "installers/setup/pro/web/install.ini", "openinfra-web.service"),
    (
        "enterprise",
        "server",
        "installers/setup/enterprise/server/install.ini",
        "openinfra.service",
    ),
    ("enterprise", "web", "installers/setup/enterprise/web/install.ini", "openinfra-web.service"),
    (
        "enterprise",
        "agent",
        "installers/setup/enterprise/agent/install.ini",
        "openinfra-agent.service",
    ),
]


def fail(msg: str) -> None:
    errors.append(msg)


for edition, scope, rel, service in expected:
    path = ROOT / rel
    if not path.is_file():
        fail(f"missing install.ini: {rel}")
        continue
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    for section in [
        "edition",
        "scope",
        "node",
        "system_user",
        "storage_application",
        "storage_postgresql",
        "database",
        "installer",
    ]:
        if section not in cp:
            fail(f"{rel}: missing section [{section}]")
    if cp.get("edition", "name", fallback="") != edition:
        fail(f"{rel}: invalid edition")
    if cp.get("scope", "name", fallback="") != scope:
        fail(f"{rel}: invalid scope")
    if cp.get("scope", "systemd_service", fallback="") != service:
        fail(f"{rel}: invalid systemd_service")
    if any(token in service for token in ["lite", "pro", "enterprise", "enterprise"]):
        fail(f"{rel}: service contains edition token")
    for key in ["fqdn", "ip", "mask", "vip", "gateway", "dns"]:
        if not cp.get("node", key, fallback="").strip():
            fail(f"{rel}: missing node.{key}")
    if cp.get("system_user", "name", fallback="") != "openinfra":
        fail(f"{rel}: system_user.name must be openinfra")
    if cp.get("system_user", "home", fallback="") != "/opt/openinfra/":
        fail(f"{rel}: system_user.home must be /opt/openinfra/")
    if cp.get("storage_application", "vgname", fallback="") != "rootvg":
        fail(f"{rel}: invalid application vgname")
    if cp.get("storage_application", "lvname", fallback="") != "openinfra_lv":
        fail(f"{rel}: invalid application lvname")
    if cp.get("storage_application", "mountpoint", fallback="") != "/opt/openinfra/":
        fail(f"{rel}: invalid application mountpoint")
    if cp.get("storage_application", "lv_size", fallback="") != "2GB":
        fail(f"{rel}: invalid application lv_size")
    managed = cp.getboolean("database", "managed_postgresql", fallback=False)
    apply_mig = cp.getboolean("database", "apply_backend_migrations", fallback=False)
    if scope in {"all-in-one", "server"}:
        if not managed:
            fail(f"{rel}: backend scope must manage PostgreSQL")
        if not apply_mig:
            fail(f"{rel}: backend scope must apply migrations")
        if cp.get("storage_postgresql", "vgname", fallback="") != "datavg":
            fail(f"{rel}: invalid PostgreSQL vgname")
        if cp.get("storage_postgresql", "lvname", fallback="") != "openinfradata_lv":
            fail(f"{rel}: invalid PostgreSQL lvname")
        if cp.get("storage_postgresql", "mountpoint", fallback="") != "/data/openinfra/":
            fail(f"{rel}: invalid PostgreSQL mountpoint")
        expected_pg_sizes = {
            ("lite", "all-in-one"): "2GB",
            ("pro", "server"): "100GB",
            ("enterprise", "server"): "1TB",
        }
        if (
            cp.get("storage_postgresql", "lv_size", fallback="")
            != expected_pg_sizes[(edition, scope)]
        ):
            fail(f"{rel}: invalid PostgreSQL lv_size")
        if (
            cp.get("storage_postgresql", "owner_mode", fallback="")
            != "postgresql_service_account_auto"
        ):
            fail(f"{rel}: PostgreSQL owner_mode must be logical auto")
        if cp.get("storage_postgresql", "symlink", fallback="") != "/opt/openinfra/data":
            fail(f"{rel}: invalid symlink")
    else:
        if managed or apply_mig:
            fail(f"{rel}: web/agent must not manage PostgreSQL or migrations")
    if scope == "web":
        if (
            cp.get("frontend", "framework", fallback="") != "react"
            or cp.get("frontend", "ui_framework", fallback="") != "bootstrap5"
        ):
            fail(f"{rel}: web must use React + Bootstrap 5")
        if not cp.get("frontend", "api_base_url", fallback="").startswith("https://"):
            fail(f"{rel}: web api_base_url must be https")
    if scope == "agent":
        if not cp.get("agent", "central_api_url", fallback="").startswith("https://"):
            fail(f"{rel}: agent central_api_url must be https")
    if edition == "lite":
        if cp.getboolean("auth", "ldap_enabled", fallback=False) or cp.getboolean(
            "auth", "ipa_enabled", fallback=False
        ):
            fail(f"{rel}: Lite must not enable LDAP/IPA")
        if cp.getboolean("cluster", "enabled", fallback=False):
            fail(f"{rel}: Lite must not enable cluster")
    text = path.read_text(encoding="utf-8")
    for bad in ["password =", "token =", "secret ="]:
        if re.search(rf"(?im)^\s*{re.escape(bad)}", text):
            fail(f"{rel}: clear secret-like key {bad!r} is forbidden")

# Matrix consistency
matrix = ROOT / "11-Matrices/Matrice-install-ini-scopes-v4.8.csv"
if not matrix.is_file():
    fail("missing Matrice-install-ini-scopes-v4.8.csv")
else:
    with matrix.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    actual = {(r["edition"], r["scope"], r["config_path"], r["systemd_service"]) for r in rows}
    expected_set = {(e, s, p, svc) for e, s, p, svc in expected}
    if actual != expected_set:
        fail("install.ini scope matrix does not match templates")

req_path = ROOT / "11-Matrices/Exigences.csv"
with req_path.open(encoding="utf-8", newline="") as f:
    reqs = {r["id"] for r in csv.DictReader(f)}
for number in range(695, 736):
    rid = f"REQ-{number:05d}"
    if rid not in reqs:
        fail(f"missing v4.8 requirement {rid}")

if errors:
    print("\n".join(f"ERROR: {e}" for e in errors))
    raise SystemExit(1)
print("OK: install.ini v4.8.1 validated for 6 installer scopes and edition-specific PGDATA sizes")
