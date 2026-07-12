from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.quality.release_security import (
    ReleaseSecurityAuditError,
    ReleaseSecurityAuditService,
)


class ReleaseSecurityAuditCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="release-security-audit")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--evidence-dir", type=Path, required=True)
        parser.add_argument("--image-ref", required=True)
        parser.add_argument("--api-base-url", default="http://127.0.0.1:8080")
        parser.add_argument("--web-base-url", default="http://127.0.0.1:2006")
        parser.add_argument("--offline", action="store_true")
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            report = ReleaseSecurityAuditService().run(
                args.project_root,
                args.output,
                args.evidence_dir,
                image_ref=str(args.image_ref),
                api_base_url=str(args.api_base_url),
                web_base_url=str(args.web_base_url),
                offline=bool(args.offline),
            )
        except ReleaseSecurityAuditError as exc:
            print(f"release-security-audit: error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, sort_keys=True))
        if args.enforce and not bool(report["release_security_certification"]):
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(ReleaseSecurityAuditCli.main())
