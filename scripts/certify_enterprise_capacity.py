from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.domain.common import OpenInfraError
from openinfra.quality.capacity_certification import EnterpriseCapacityCertificationService


class EnterpriseCapacityCertificationCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="certify-enterprise-capacity")
        parser.add_argument("--evidence", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            report = EnterpriseCapacityCertificationService.write_report(args.evidence, args.output)
        except OpenInfraError as exc:
            sys.stderr.write(f"capacity-certification: error: {exc}\n")
            return 2
        print(json.dumps(report, sort_keys=True))
        return 1 if args.enforce and not bool(report["capacity_certification"]) else 0


if __name__ == "__main__":
    raise SystemExit(EnterpriseCapacityCertificationCli.main())
