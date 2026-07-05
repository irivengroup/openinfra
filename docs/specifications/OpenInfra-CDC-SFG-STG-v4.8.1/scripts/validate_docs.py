#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ["TODO", "PLACEHOLDER", "à compléter", "TBD", "lorem ipsum"]
REQUIRED = [
    "00-README.md",
    "00-Index-general.md",
    "00-Note-de-cadrage-CCTP-CdCF.md",
    "11-Matrices/Exigences.csv",
    "11-Matrices/Traceabilite.csv",
    "04-Donnees/Dictionnaire.csv",
    "09-API/OpenAPI/openapi.yaml",
    "09-API/GraphQL/schema.graphql",
    "00-Delta-v4.md",
    "00-Delta-v4.5.md",
    "00-Delta-v4.6.md",
    "00-Delta-v4.8.md",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


for rel in REQUIRED:
    if not (ROOT / rel).exists():
        fail(f"missing required file: {rel}")


for n in range(13, 31):
    matches = list((ROOT / "Volumes").glob(f"V{n:02d}-*.md"))
    if not matches:
        fail(f"missing v4 volume V{n:02d}")

for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix.lower() in {
        ".md",
        ".csv",
        ".yaml",
        ".yml",
        ".graphql",
        ".puml",
        ".mmd",
    }:
        text = path.read_text(encoding="utf-8", errors="ignore")
        upper = text.upper()
        for marker in FORBIDDEN:
            if marker.upper() in upper:
                fail(f"forbidden marker {marker!r} in {path.relative_to(ROOT)}")

req_path = ROOT / "11-Matrices/Exigences.csv"
ids: list[str] = []
with req_path.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rid = row.get("id", "")
        if not re.fullmatch(r"REQ-\d{5}", rid):
            fail(f"invalid requirement id: {rid}")
        ids.append(rid)
        for field in ["requirement", "verification", "acceptance"]:
            if not row.get(field):
                fail(f"missing {field} for {rid}")
if len(ids) != len(set(ids)):
    fail("duplicate requirement ids")
if len(ids) < 735:
    fail("not enough requirements for enterprise dossier")

trace_path = ROOT / "11-Matrices/Traceabilite.csv"
with trace_path.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    traced = {row["requirement_id"] for row in reader if row.get("requirement_id")}
missing = [rid for rid in ids[:50] if rid not in traced]
if missing:
    fail(f"untraced requirements in first critical set: {missing[:5]}")

with (ROOT / "04-Donnees/Dictionnaire.csv").open(newline="", encoding="utf-8") as f:
    entity_count = sum(1 for _ in csv.DictReader(f))
if entity_count < 450:
    fail(f"data dictionary too small: {entity_count}")

print(f"OK: {len(ids)} requirements, {entity_count} entities, traceability present")
