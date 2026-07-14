from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class ScaleoutPromotionProjectError(Exception):
    """Raised when the P20/GATE-09 project contract is incomplete."""


class ScaleoutPromotionProjectValidator:
    REQUIRED_FILES = (
        "compose.yaml",
        "src/openinfra/infrastructure/read_routing.py",
        "src/openinfra/infrastructure/cursor_pagination.py",
        "src/openinfra/domain/async_processing.py",
        "src/openinfra/application/specialized_worker_services.py",
        "web/src/domain-manifest.js",
        "web/src/core/query-cache.js",
        "web/src/core/virtual-window.js",
        "src/openinfra/infrastructure/observability.py",
        "src/openinfra/quality/capacity_certification.py",
        "src/openinfra/quality/multisite_chaos.py",
        "docs/operations/enterprise-capacity-profile.json",
        "docs/operations/multisite-chaos-profile.json",
        "docs/runbooks/OBSERVABILITY_CAPACITY.md",
        "docs/runbooks/MULTISITE_CHAOS.md",
        "docs/runbooks/PRA_PCA_CERTIFICATION.md",
        "docs/runbooks/ENTERPRISE_SCALEOUT_PROMOTION.md",
        "docs/release/enterprise-scaleout-promotion-policy.json",
        "scripts/assemble_scaleout_promotion_evidence.py",
        "scripts/certify_scaleout_promotion.py",
        ".github/workflows/enterprise-scaleout-promotion.yml",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        missing = [item for item in self.REQUIRED_FILES if not (self._root / item).is_file()]
        if missing:
            raise ScaleoutPromotionProjectError(
                "missing GATE-09 scale-out assets: " + ", ".join(missing)
            )
        self._assert_fragments(
            "compose.yaml",
            ("pgbouncer-primary", "pgbouncer-replica", "postgres-replica"),
        )
        self._assert_fragments(
            "src/openinfra/infrastructure/read_routing.py",
            ("replica", "lag", "primary"),
        )
        self._assert_fragments(
            "src/openinfra/infrastructure/cursor_pagination.py",
            ("cursor", "decode", "encode"),
        )
        self._assert_fragments(
            "src/openinfra/domain/async_processing.py",
            ("dead-letter", "lease", "fencing"),
        )
        self._assert_fragments(
            "web/src/domain-manifest.js",
            ("DOMAIN_LOADERS", "import("),
        )
        self._assert_fragments(
            ".github/workflows/enterprise-scaleout-promotion.yml",
            (
                "actions: read",
                "openinfra-enterprise-scaleout",
                "validate_scaleout_promotion.py",
                "assemble_scaleout_promotion_evidence.py",
                "certify_scaleout_promotion.py",
                "--enforce",
            ),
        )
        return {
            "schema_version": 1,
            "report_kind": "p20-contracts",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "pgbouncer_and_read_routing": True,
            "cursor_pagination_and_streaming": True,
            "outbox_and_specialized_workers": True,
            "modular_virtualized_frontend": True,
            "observability_and_capacity_contracts": True,
            "runbooks_present": True,
            "gate_id": "GATE-09",
            "release_id": "REL-10",
        }

    def _assert_fragments(self, relative: str, fragments: tuple[str, ...]) -> None:
        content = (self._root / relative).read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in content]
        if missing:
            raise ScaleoutPromotionProjectError(
                f"{relative} is incomplete for GATE-09: " + ", ".join(missing)
            )


class ScaleoutPromotionProjectCli:
    @staticmethod
    def _write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra GATE-09 project contracts")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = ScaleoutPromotionProjectValidator(args.project_root).validate()
        except ScaleoutPromotionProjectError as exc:
            if args.enforce:
                print(str(exc))
                return 1
            raise
        if args.output is not None:
            cls._write_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(ScaleoutPromotionProjectCli.main())
