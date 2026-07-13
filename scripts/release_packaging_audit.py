from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.quality.release_packaging import (
    ReleasePackagingAuditService,
    ReleasePackagingError,
    ReleaseSigningMaterial,
)


class ReleasePackagingAuditCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="release-packaging-audit")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output-dir", type=Path, required=True)
        parser.add_argument("--source-date-epoch", type=int, required=True)
        signing = parser.add_mutually_exclusive_group(required=True)
        signing.add_argument("--signing-key", type=Path)
        signing.add_argument("--signing-key-from-env", action="store_true")
        signing.add_argument("--ephemeral-signing-key", action="store_true")
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            material = cls._signing_material(args)
            report = ReleasePackagingAuditService().run(
                args.project_root,
                args.output_dir,
                int(args.source_date_epoch),
                material,
            )
        except ReleasePackagingError as exc:
            print(f"release-packaging-audit: error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, sort_keys=True))
        if args.enforce and not bool(report["release_packaging_certification"]):
            return 1
        return 0

    @classmethod
    def _signing_material(cls, args: argparse.Namespace) -> ReleaseSigningMaterial:
        if args.signing_key is not None:
            return ReleaseSigningMaterial.from_file(args.signing_key)
        if bool(args.signing_key_from_env):
            return ReleaseSigningMaterial.from_environment()
        return ReleaseSigningMaterial.generate_ephemeral()


if __name__ == "__main__":
    raise SystemExit(ReleasePackagingAuditCli.main())
