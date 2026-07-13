from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.quality.documentation_ga import GaDocumentationError, GaDocumentationValidator


class GaDocumentationValidationCli:
    @classmethod
    def build_parser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Validate OpenInfra GA documentation")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        return parser

    @classmethod
    def main(cls) -> int:
        args = cls.build_parser().parse_args()
        try:
            report = GaDocumentationValidator(args.project_root).validate()
        except GaDocumentationError as exc:
            if args.enforce:
                print(str(exc), file=sys.stderr)
                return 1
            print(json.dumps({"passed": False, "error": str(exc)}, indent=2, sort_keys=True))
            return 0
        payload = report.as_dict()
        encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_name(f".{args.output.name}.tmp")
            temporary.write_text(encoded, encoding="utf-8")
            temporary.replace(args.output)
        print(encoded, end="")
        return 0


if __name__ == "__main__":
    raise SystemExit(GaDocumentationValidationCli.main())
