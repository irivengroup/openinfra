from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openinfra.infrastructure.installer_config import InstallerConfigValidator


class AutonomousInstallerValidationCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(
            prog="validate_autonomous_installer",
            description="Validate OpenInfra CDC v4.9.0 installer install.ini files.",
        )
        parser.add_argument("--root", type=Path, default=Path("installers"))
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args()
        report = InstallerConfigValidator().validate_tree(args.root)
        if args.json:
            print(json.dumps(report.as_dict(), sort_keys=True, indent=2))
        else:
            status = "PASS" if report.valid else "FAIL"
            print(f"status={status}")
            print(f"root={report.root}")
            print(f"installers={len(report.reports)}")
            for missing in report.missing_paths:
                print(f"missing={missing}")
            for unexpected in report.unexpected_paths:
                print(f"unexpected={unexpected}")
            for item in report.reports:
                print(
                    "installer="
                    + str(item.path)
                    + f" valid={str(item.valid).lower()} edition={item.edition} "
                    + f"scope={item.scope} service={item.service}"
                )
                for error in item.errors:
                    print("error=" + error)
        return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(AutonomousInstallerValidationCli.main())
