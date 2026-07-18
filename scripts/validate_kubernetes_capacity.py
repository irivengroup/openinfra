from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class KubernetesCapacityProjectError(Exception):
    """Raised when the P21/EPIC-2105 capacity contract is incomplete."""


class KubernetesCapacityProjectValidator:
    REQUIRED_FILES = (
        "src/openinfra/domain/kubernetes_capacity.py",
        "src/openinfra/domain/kubernetes_topology.py",
        "src/openinfra/application/kubernetes_topology_services.py",
        "src/openinfra/interfaces/http_api.py",
        "src/openinfra/interfaces/cli.py",
        "docs/api/openapi.yaml",
        "docs/architecture/kubernetes-capacity.md",
        "docs/operations/kubernetes-capacity.md",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/04-roadmap-epics.csv",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/09-roadmap-tests-validation.csv",
        "tests/unit/test_kubernetes_capacity.py",
        "tests/integration/test_kubernetes_capacity_services.py",
        "tests/integration/test_kubernetes_capacity_http_api.py",
        "tests/integration/test_kubernetes_capacity_cli.py",
        "tests/integration/test_kubernetes_capacity_web_contract.py",
        "tests/integration/test_kubernetes_capacity_tooling.py",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        missing = [item for item in self.REQUIRED_FILES if not (self._root / item).is_file()]
        if missing:
            raise KubernetesCapacityProjectError(
                "missing P21/EPIC-2105 capacity assets: " + ", ".join(missing)
            )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_capacity.py",
            (
                "class KubernetesCapacityReport",
                "class KubernetesCapacityTrendReport",
                "_MAX_NAMESPACES = 5_000",
                '"capacity trend max_resources must be between 1 and 1000000"',
                'raise ValidationError("capacity export format must be json or csv")',
            ),
        )
        self._assert_fragments(
            "src/openinfra/application/kubernetes_topology_services.py",
            (
                "_MAX_CAPACITY_TREND_SNAPSHOTS = 96",
                "_MAX_CAPACITY_TREND_RESOURCES = 1_000_000",
                "def capacity(",
                "def latest_capacity(",
                "def capacity_trend(",
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/http_api.py",
            (
                '"/api/v1/kubernetes/topologies/capacity"',
                '"/api/v1/kubernetes/topologies/latest-capacity"',
                '"/api/v1/kubernetes/topologies/capacity-trend"',
                '"/api/v1/kubernetes/topologies/capacity-export"',
                '"/api/v1/kubernetes/topologies/latest-capacity-export"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/cli.py",
            (
                '"capacity"',
                '"latest-capacity"',
                '"capacity-trend"',
                '"capacity-export"',
                '"latest-capacity-export"',
            ),
        )
        for relative in (
            "web/src/domains/discovery.js",
            "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        ):
            self._assert_fragments(
                relative,
                (
                    "kubernetes-capacity-latest",
                    "kubernetes-capacity-snapshot",
                    "kubernetes-capacity-trend",
                    "kubernetes-capacity-export",
                    "kubernetes-capacity-latest-export",
                ),
            )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/04-roadmap-epics.csv",
            ("EPIC-2105", "Capacité cluster et namespace"),
        )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/09-roadmap-tests-validation.csv",
            ("TST-P21-K8S-SCALE-GATE", "Qualification REL-11"),
        )
        migrations = sorted((self._root / "installers/migrations/postgresql").glob("*.sql"))
        if len(migrations) != 58 or migrations[-1].name != "0058_oracle_document_shards.sql":
            raise KubernetesCapacityProjectError(
                "EPIC-2105 must reuse the 56-migration chain ending with "
                "0056_kubernetes_gitops_drift.sql"
            )
        return {
            "schema_version": 1,
            "report_kind": "kubernetes-capacity-contract",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "phase": "P21",
            "epic": "EPIC-2105",
            "release": "REL-11",
            "roadmap_version": "2.2.0",
            "cluster_capacity": True,
            "namespace_capacity": True,
            "bounded_trends": True,
            "alerts": True,
            "json_csv_exports": True,
            "max_trend_snapshots": 96,
            "max_trend_resources": 1_000_000,
            "api_cli_web_parity": True,
            "migration_count": 58,
        }

    def _assert_fragments(self, relative: str, fragments: tuple[str, ...]) -> None:
        content = (self._root / relative).read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in content]
        if missing:
            raise KubernetesCapacityProjectError(
                f"{relative} is incomplete for P21/EPIC-2105: " + ", ".join(missing)
            )


class KubernetesCapacityProjectCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P21/EPIC-2105 contracts")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = KubernetesCapacityProjectValidator(args.project_root).validate()
        except KubernetesCapacityProjectError as exc:
            if args.enforce:
                print(str(exc))
                return 1
            raise
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.output.with_suffix(args.output.suffix + ".tmp")
            temporary.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            temporary.replace(args.output)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(KubernetesCapacityProjectCli.main())
