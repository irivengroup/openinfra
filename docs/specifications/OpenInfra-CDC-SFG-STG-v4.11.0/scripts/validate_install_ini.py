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


def require_sections(rel: str, cp: configparser.ConfigParser, sections: tuple[str, ...]) -> None:
    if tuple(cp.sections()) != sections:
        fail(f"{rel}: expected sections {sections}, got {tuple(cp.sections())}")


def require_security(rel: str, edition: str, cp: configparser.ConfigParser) -> None:
    if not cp.has_section("security"):
        fail(f"{rel}: missing section [security]")
        return
    transport = cp.get("security", "transport", fallback="")
    mtls = cp.get("security", "mtls_required", fallback="")
    tls = cp.get("security", "tls_min_version", fallback="")
    loopback = cp.get("security", "loopback_only", fallback="")
    if tls != "TLSv1.3":
        fail(f"{rel}: TLS minimum must be TLSv1.3")
    if edition == "lite":
        if transport != "local" or mtls != "false" or loopback != "true":
            fail(f"{rel}: Lite security must be local, non-mTLS and loopback-only")
        return
    if transport != "mtls" or mtls != "true":
        fail(f"{rel}: Pro/Enterprise must enforce mTLS")
    for key in ("server_ca_cert_ref", "client_cert_ref", "client_key_ref"):
        value = cp.get("security", key, fallback="")
        if not value.startswith(("file://", "vault://", "sops://", "kms://")):
            fail(f"{rel}: security.{key} must be a secure reference")


for edition, scope, rel, _service in expected:
    path = ROOT / rel
    if not path.is_file():
        fail(f"missing install.ini: {rel}")
        continue
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    if edition == "lite":
        require_sections(rel, cp, ("storage", "security", "web_database"))
    elif scope == "server":
        require_sections(rel, cp, ("storage", "api", "identity", "auth", "security"))
    elif scope == "web":
        require_sections(rel, cp, ("api", "auth", "security", "web_database"))
    else:
        require_sections(rel, cp, ("api", "security"))
    require_security(rel, edition, cp)
    if scope in {"all-in-one", "server"}:
        if cp.get("storage", "vgname", fallback="") != "datavg":
            fail(f"{rel}: invalid PostgreSQL vgname")
        if cp.get("storage", "lvname", fallback="") != "openinfradata_lv":
            fail(f"{rel}: invalid PostgreSQL lvname")
        expected_pg_sizes = {
            ("lite", "all-in-one"): "2GB",
            ("pro", "server"): "100GB",
            ("enterprise", "server"): "1TB",
        }
        if cp.get("storage", "lvsize", fallback="") != expected_pg_sizes[(edition, scope)]:
            fail(f"{rel}: invalid PostgreSQL lvsize")
    if scope in {"server", "web", "agent"}:
        endpoint = cp.get("api", "backend_endpoint", fallback="")
        if not endpoint.startswith("https://"):
            fail(f"{rel}: backend_endpoint must be https")
    if scope == "server" and cp.get("auth", "mode", fallback="") != "standard":
        fail(f"{rel}: backend auth.mode must remain standard")
    if scope == "web" and cp.get("auth", "mode", fallback="") not in {"standard", "ldap", "ipa"}:
        fail(f"{rel}: web auth.mode must be standard, ldap or ipa")
    if edition == "lite" and cp.has_section("auth"):
        fail(f"{rel}: Lite must not expose auth")

    if scope in {"all-in-one", "web"}:
        if not cp.has_section("web_database"):
            fail(f"{rel}: web runtime must declare [web_database]")
        else:
            for key in ("postgresql_dsn_ref", "postgresql_user_ref", "postgresql_password_ref"):
                value = cp.get("web_database", key, fallback="")
                if not value.startswith(("env:", "vault://", "sops://", "file://", "kms://")):
                    fail(f"{rel}: web_database.{key} must be a secret/config reference")
    text = path.read_text(encoding="utf-8")
    for bad in ["password =", "token =", "secret ="]:
        if re.search(rf"(?im)^\s*{re.escape(bad)}", text):
            fail(f"{rel}: clear secret-like key {bad!r} is forbidden")

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
for number in range(695, 743):
    rid = f"REQ-{number:05d}"
    if rid not in reqs:
        fail(f"missing v4.8 requirement {rid}")

if errors:
    print("\n".join(f"ERROR: {e}" for e in errors))
    raise SystemExit(1)
print("OK: install.ini v4.8.1 validated for six installer scopes, runtime config and mTLS policy")
