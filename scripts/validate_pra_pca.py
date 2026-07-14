from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openinfra.domain.common import ValidationError
from openinfra.quality.continuity_certification import PraPcaCertificationEvidence


def validate_project(project_root: Path) -> dict[str, object]:
    required_files = (
        "src/openinfra/quality/continuity_certification.py",
        "scripts/assemble_pra_pca_evidence.py",
        "scripts/certify_pra_pca.py",
        "docs/operations/pra-pca-profile.json",
        "docs/runbooks/PRA_PCA_CERTIFICATION.md",
        ".github/workflows/pra-pca-certification.yml",
        "tests/unit/test_continuity_certification.py",
        "tests/integration/test_pra_pca_certification_tooling.py",
    )
    missing = [relative for relative in required_files if not (project_root / relative).is_file()]
    if missing:
        raise ValidationError("missing PRA/PCA certification assets: " + ", ".join(missing))
    profile_path = project_root / "docs/operations/pra-pca-profile.json"
    try:
        profile: Any = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("PRA/PCA profile is not valid JSON") from exc
    if not isinstance(profile, dict):
        raise ValidationError("PRA/PCA profile root must be an object")
    if profile.get("profile_id") != "openinfra-pra-pca-v1" or profile.get("profile_version") != 1:
        raise ValidationError("PRA/PCA profile identity is invalid")
    if profile.get("required_procedures") != list(
        PraPcaCertificationEvidence.required_procedures()
    ):
        raise ValidationError("PRA/PCA required procedures are inconsistent")
    workflow = (project_root / ".github/workflows/pra-pca-certification.yml").read_text(
        encoding="utf-8"
    )
    required_fragments = (
        "workflow_dispatch:",
        "runs-on: [self-hosted, linux, x64, openinfra-pra-pca]",
        "environment: pra-pca-certification",
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "actions/upload-artifact@v6",
        "assemble_pra_pca_evidence.py",
        "certify_pra_pca.py",
        "--enforce",
        "retention-days: 90",
    )
    missing_fragments = [fragment for fragment in required_fragments if fragment not in workflow]
    if missing_fragments:
        raise ValidationError("PRA/PCA workflow is incomplete: " + ", ".join(missing_fragments))
    if "pull_request_target:" in workflow:
        raise ValidationError("PRA/PCA workflow must not execute from pull_request_target")
    return {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "required_procedures": len(PraPcaCertificationEvidence.required_procedures()),
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate OpenInfra PRA/PCA certification contracts"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        report = validate_project(args.project_root.resolve())
    except ValidationError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
