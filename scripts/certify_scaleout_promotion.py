from __future__ import annotations

import argparse
import json
from pathlib import Path

from openinfra.quality.scaleout_promotion import (
    ScaleoutPromotionCertification,
    ScaleoutPromotionError,
    ScaleoutPromotionManifest,
    ScaleoutPromotionPolicy,
)


class ScaleoutPromotionCertificationCli:
    @staticmethod
    def _write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Certify OpenInfra GATE-09 promotion evidence")
        parser.add_argument("--policy", type=Path, required=True)
        parser.add_argument("--manifest", type=Path, required=True)
        parser.add_argument("--evidence-root", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            policy = ScaleoutPromotionPolicy.load(args.policy)
            manifest = ScaleoutPromotionManifest.load(args.manifest)
            report = ScaleoutPromotionCertification.evaluate(
                policy,
                manifest,
                args.evidence_root,
            )
        except ScaleoutPromotionError as exc:
            parser.error(str(exc))
        cls._write_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.enforce and not bool(report["scaleout_promotion_certification"]):
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(ScaleoutPromotionCertificationCli.main())
