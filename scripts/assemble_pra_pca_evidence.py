from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openinfra.domain.common import ValidationError
from openinfra.quality.continuity_certification import PraPcaCertificationEvidence


def _load_object(path: Path, label: str) -> dict[str, object]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"{label} root must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def _artifact(path: Path, name: str) -> dict[str, object]:
    data = path.read_bytes()
    return {"name": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def assemble_pra_pca_evidence(
    *,
    profile_path: Path,
    edition: str,
    plan_path: Path,
    drill_path: Path,
    backup_restore_path: Path,
    pitr_path: Path,
    procedures_path: Path,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    profile = _load_object(profile_path, "profile")
    if profile.get("profile_id") != "openinfra-pra-pca-v1" or profile.get("profile_version") != 1:
        raise ValidationError("unsupported PRA/PCA profile")
    required = profile.get("required_procedures")
    if required != list(PraPcaCertificationEvidence.required_procedures()):
        raise ValidationError("PRA/PCA profile required procedures are inconsistent")
    plan = _load_object(plan_path, "DR plan")
    drill = _load_object(drill_path, "DR drill")
    backup_restore = _load_object(backup_restore_path, "backup/restore evidence")
    pitr = _load_object(pitr_path, "PITR evidence")
    procedures = _load_object(procedures_path, "procedure evidence")
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValidationError("generated_at must be timezone-aware")
    payload: dict[str, object] = {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "edition": edition.strip().lower(),
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "plan": plan,
        "dr_drill": drill,
        "backup_restore": backup_restore,
        "pitr": pitr,
        "procedures": procedures,
        "source_artifacts": [
            _artifact(plan_path, "dr-plan"),
            _artifact(drill_path, "dr-drill"),
            _artifact(backup_restore_path, "backup-restore"),
            _artifact(pitr_path, "pitr"),
            _artifact(procedures_path, "procedures"),
        ],
    }
    payload["evidence_digest"] = PraPcaCertificationEvidence.digest_for(payload)
    PraPcaCertificationEvidence.from_mapping(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble immutable OpenInfra PRA/PCA evidence")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--edition", required=True, choices=("pro", "enterprise"))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--drill", type=Path, required=True)
    parser.add_argument("--backup-restore", type=Path, required=True)
    parser.add_argument("--pitr", type=Path, required=True)
    parser.add_argument("--procedures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = assemble_pra_pca_evidence(
            profile_path=args.profile,
            edition=args.edition,
            plan_path=args.plan,
            drill_path=args.drill,
            backup_restore_path=args.backup_restore,
            pitr_path=args.pitr,
            procedures_path=args.procedures,
        )
        _write_atomic(args.output, payload)
    except ValidationError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
