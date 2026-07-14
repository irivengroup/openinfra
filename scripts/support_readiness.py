from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.quality.release_packaging import ReleasePackagingError, ReleaseSigningMaterial
from openinfra.quality.support_readiness import SupportReadinessError, SupportReadinessService


class SupportReadinessCli:
    @classmethod
    def build_parser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Validate and sign the OpenInfra EPIC-1806 support readiness evidence"
        )
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--policy", type=Path)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--signing-key", type=Path)
        parser.add_argument("--ephemeral-key", action="store_true")
        parser.add_argument("--enforce", action="store_true")
        return parser

    @classmethod
    def main(cls) -> int:
        args = cls.build_parser().parse_args()
        try:
            signing_material = cls._signing_material(args.signing_key, args.ephemeral_key)
            report = SupportReadinessService().evaluate_and_write(
                project_root=args.project_root,
                output_path=args.output,
                signing_material=signing_material,
                policy_path=args.policy,
            )
        except (SupportReadinessError, ReleasePackagingError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        if args.enforce and not report.support_readiness:
            return 1
        return 0

    @staticmethod
    def _signing_material(signing_key: Path | None, ephemeral_key: bool) -> ReleaseSigningMaterial:
        if signing_key is not None and ephemeral_key:
            raise SupportReadinessError("choose either --signing-key or --ephemeral-key")
        if signing_key is not None:
            return ReleaseSigningMaterial.from_file(signing_key)
        if ephemeral_key:
            return ReleaseSigningMaterial.generate_ephemeral()
        return ReleaseSigningMaterial.from_environment()


if __name__ == "__main__":
    raise SystemExit(SupportReadinessCli.main())
