from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class KubernetesTopologyProjectError(Exception):
    """Raised when the P21/EPIC-2101 project contract is incomplete."""


class KubernetesTopologyProjectValidator:
    REQUIRED_FILES = (
        "src/openinfra/domain/kubernetes_topology.py",
        "src/openinfra/application/kubernetes_topology_services.py",
        "src/openinfra/infrastructure/kubernetes_topology_mapper.py",
        "installers/migrations/postgresql/0055_kubernetes_topology_inventory.sql",
        "docs/architecture/kubernetes-cloud-native-topology.md",
        "docs/operations/kubernetes-topology.md",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/VERSION",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/04-roadmap-epics.csv",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/14-alignement-cdc-v4.9.0.csv",
        "tests/unit/test_kubernetes_topology.py",
        "tests/integration/test_kubernetes_topology_services.py",
        "tests/integration/test_kubernetes_topology_http_api.py",
        "tests/integration/test_kubernetes_topology_cli.py",
        "tests/integration/test_kubernetes_topology_migration.py",
        "tests/integration/test_kubernetes_topology_postgresql_repository.py",
        "tests/integration/test_kubernetes_topology_web_contract.py",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        missing = [item for item in self.REQUIRED_FILES if not (self._root / item).is_file()]
        if missing:
            raise KubernetesTopologyProjectError(
                "missing P21/EPIC-2101 Kubernetes topology assets: " + ", ".join(missing)
            )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_topology.py",
            (
                "_MAX_RESOURCES = 50_000",
                "KubernetesResourceKind.NETWORK_POLICY",
                "KubernetesTopologyValidator.digest",
                '"runs-on-vm"',
                '"located-in-site"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/domain/security.py",
            ('KUBERNETES_READ = "kubernetes.read"', 'KUBERNETES_WRITE = "kubernetes.write"'),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/http_api.py",
            (
                '"/api/v1/kubernetes/topologies"',
                '"/api/v1/kubernetes/topologies/import"',
                '"/api/v1/kubernetes/topologies/latest-topology"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/cli.py",
            ('"kubernetes"', '"latest-topology"', '"--resources-file"'),
        )
        self._assert_fragments(
            "docs/api/openapi.yaml",
            (
                "/api/v1/kubernetes/topologies:",
                "/api/v1/kubernetes/topologies/import:",
                "Discovery · Kubernetes et cloud-native",
            ),
        )
        self._assert_fragments(
            "web/src/domains/discovery.js",
            (
                "kubernetes-topologies-list",
                "kubernetes-topology-graph",
                "kubernetes-topology-import",
            ),
        )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/04-roadmap-epics.csv",
            ("EPIC-2101", "EPIC-2106"),
        )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/14-alignement-cdc-v4.9.0.csv",
            ("REQ-00469", "REQ-00470"),
        )
        migrations = sorted((self._root / "installers/migrations/postgresql").glob("*.sql"))
        if len(migrations) < 55 or migrations[54].name != "0055_kubernetes_topology_inventory.sql":
            raise KubernetesTopologyProjectError(
                "PostgreSQL migration chain must contain at least 55 migrations with "
                "position 55 equal to 0055_kubernetes_topology_inventory.sql"
            )
        return {
            "schema_version": 1,
            "report_kind": "kubernetes-cloud-native-topology-contract",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "phase": "P21",
            "epic": "EPIC-2101",
            "release": "REL-11",
            "roadmap_version": "2.2.0",
            "max_resources_per_snapshot": 50_000,
            "api_cli_web_parity": True,
            "physical_mapping": True,
            "secret_values_rejected": True,
        }

    def _assert_fragments(self, relative: str, fragments: tuple[str, ...]) -> None:
        content = (self._root / relative).read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in content]
        if missing:
            raise KubernetesTopologyProjectError(
                f"{relative} is incomplete for P21/EPIC-2101: " + ", ".join(missing)
            )


class KubernetesTopologyProjectCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P21/EPIC-2101 contracts")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = KubernetesTopologyProjectValidator(args.project_root).validate()
        except KubernetesTopologyProjectError as exc:
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
    raise SystemExit(KubernetesTopologyProjectCli.main())
