from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.quality.ga_go_no_go import GaGoNoGoDecisionService, GaGoNoGoError
from openinfra.quality.release_packaging import ReleasePackagingError, ReleaseSigningMaterial


class GaGoNoGoCli:
    @classmethod
    def build_parser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="ga-go-no-go")
        parser.add_argument("--manifest", type=Path, required=True)
        parser.add_argument(
            "--policy",
            type=Path,
            default=Path("docs/release/ga-go-no-go-policy.json"),
        )
        parser.add_argument("--trust-policy", type=Path, required=True)
        parser.add_argument("--evidence-root", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--signing-key", type=Path)
        parser.add_argument("--ephemeral-signing-key", action="store_true")
        parser.add_argument("--enforce-go", action="store_true")
        return parser

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = cls.build_parser().parse_args(argv)
        try:
            signing_material = cls._signing_material(args)
            report = GaGoNoGoDecisionService().evaluate_and_write(
                manifest_path=args.manifest,
                policy_path=args.policy,
                trust_policy_path=args.trust_policy,
                evidence_root=args.evidence_root,
                output_path=args.output,
                signing_material=signing_material,
            )
        except (GaGoNoGoError, ReleasePackagingError) as exc:
            print(f"ga-go-no-go: error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, sort_keys=True))
        if args.enforce_go and report["decision"] != "GO":
            return 1
        return 0

    @classmethod
    def _signing_material(cls, args: argparse.Namespace) -> ReleaseSigningMaterial:
        if args.signing_key is not None and args.ephemeral_signing_key:
            raise GaGoNoGoError("--signing-key and --ephemeral-signing-key are mutually exclusive")
        if args.ephemeral_signing_key:
            return ReleaseSigningMaterial.generate_ephemeral()
        if args.signing_key is not None:
            return ReleaseSigningMaterial.from_file(args.signing_key)
        return ReleaseSigningMaterial.from_environment()


if __name__ == "__main__":
    raise SystemExit(GaGoNoGoCli.main())
