from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openinfra.quality.migration_packaging import (
    MigrationCatalogArchiveBuilder,
    MigrationPackagingError,
)


class MigrationCatalogCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="build-migration-catalog")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output-dir", type=Path, required=True)
        parser.add_argument("--source-date-epoch", type=int, required=True)
        parser.add_argument("--json", action="store_true")
        args = parser.parse_args(argv)
        try:
            archive, snapshot = MigrationCatalogArchiveBuilder().build(
                args.project_root,
                args.output_dir,
                int(args.source_date_epoch),
            )
        except MigrationPackagingError as exc:
            print(f"build-migration-catalog: error: {exc}", file=sys.stderr)
            return 2
        payload = {
            "archive": str(archive),
            "count_per_database": snapshot.count,
            "first_version": snapshot.first_version,
            "last_version": snapshot.last_version,
            "parity": True,
            "release_version": snapshot.release_version,
        }
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(
                "Migration catalogue built: "
                f"{archive} ({snapshot.count} PostgreSQL / {snapshot.count} Oracle)"
            )
        return 0


if __name__ == "__main__":
    raise SystemExit(MigrationCatalogCli.main())
