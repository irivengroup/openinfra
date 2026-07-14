from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openinfra.domain.common import ValidationError
from openinfra.quality.multisite_chaos import MultisiteChaosCampaignEvidence


def certify_multisite_chaos(evidence_path: Path) -> dict[str, object]:
    try:
        payload: Any = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read multisite chaos evidence: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError("multisite chaos evidence root must be a JSON object")
    evidence = MultisiteChaosCampaignEvidence.from_mapping(
        {str(key): value for key, value in payload.items()}
    )
    return evidence.certification_report()


class MultisiteChaosCertificationCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="certify-multisite-chaos")
        parser.add_argument("--evidence", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            report = certify_multisite_chaos(args.evidence)
        except (OSError, ValidationError) as exc:
            print(f"multisite-chaos-certification: FAIL: {exc}")
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(args.output)
        print(json.dumps(report, sort_keys=True))
        if args.enforce and report["multisite_chaos_certification"] is not True:
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(MultisiteChaosCertificationCli.main())
