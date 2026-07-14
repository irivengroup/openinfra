from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openinfra.domain.common import ValidationError
from openinfra.quality.continuity_certification import PraPcaCertificationEvidence


def _load(path: Path) -> dict[str, object]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read PRA/PCA evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise ValidationError("PRA/PCA evidence root must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def certify_pra_pca(evidence_path: Path) -> dict[str, object]:
    evidence = PraPcaCertificationEvidence.from_mapping(_load(evidence_path))
    return evidence.certification_report()


def main() -> int:
    parser = argparse.ArgumentParser(description="Certify OpenInfra PRA/PCA evidence")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    try:
        report = certify_pra_pca(args.evidence)
        _write_atomic(args.output, report)
    except ValidationError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.enforce and not bool(report["pra_pca_certification"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
