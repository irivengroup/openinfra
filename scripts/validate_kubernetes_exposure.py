from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class KubernetesExposureProjectError(Exception):
    """Raised when the P21/EPIC-2102 cloud-native exposure contract is incomplete."""


class KubernetesExposureProjectValidator:
    REQUIRED_FILES = (
        "src/openinfra/domain/kubernetes_topology.py",
        "src/openinfra/domain/kubernetes_exposure.py",
        "src/openinfra/application/kubernetes_topology_services.py",
        "src/openinfra/interfaces/http_api.py",
        "src/openinfra/interfaces/cli.py",
        "docs/api/openapi.yaml",
        "docs/architecture/kubernetes-cloud-native-topology.md",
        "docs/operations/kubernetes-topology.md",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/04-roadmap-epics.csv",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/14-alignement-cdc-v4.10.0.csv",
        "tests/unit/test_kubernetes_exposure.py",
        "tests/integration/test_kubernetes_exposure_services.py",
        "tests/integration/test_kubernetes_exposure_http_api.py",
        "tests/integration/test_kubernetes_exposure_cli.py",
        "tests/integration/test_kubernetes_exposure_web_contract.py",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        missing = [item for item in self.REQUIRED_FILES if not (self._root / item).is_file()]
        if missing:
            raise KubernetesExposureProjectError(
                "missing P21/EPIC-2102 cloud-native exposure assets: " + ", ".join(missing)
            )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_topology.py",
            (
                'LOAD_BALANCER = "load-balancer"',
                'DNS_RECORD = "dns-record"',
                'MESH_ROUTE = "mesh-route"',
                '"forwards-to"',
                '"resolves-to"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_exposure.py",
            (
                "class KubernetesExposureReport",
                "class KubernetesFlowCorrelation",
                '"governed-by-flow"',
                '"correlates-to"',
                '"ungoverned_external_exposure_count"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/application/kubernetes_topology_services.py",
            (
                "_MAX_FLOW_DECLARATIONS = 10_000",
                "_MAX_DEPENDENCY_RELATIONS = 10_000",
                "_MAX_DEPENDENCY_OBJECTS = 2_048",
                "def exposure(",
                "def latest_exposure(",
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/http_api.py",
            (
                '"/api/v1/kubernetes/topologies/exposure"',
                '"/api/v1/kubernetes/topologies/latest-exposure"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/cli.py",
            ('"exposure"', '"latest-exposure"'),
        )
        self._assert_fragments(
            "docs/api/openapi.yaml",
            (
                "/api/v1/kubernetes/topologies/exposure:",
                "/api/v1/kubernetes/topologies/latest-exposure:",
                "Discovery · Kubernetes et cloud-native",
            ),
        )
        for relative in (
            "web/src/domains/discovery.js",
            "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        ):
            self._assert_fragments(
                relative,
                ("kubernetes-exposure-latest", "kubernetes-exposure-snapshot"),
            )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/04-roadmap-epics.csv",
            ("EPIC-2102", "Expositions et dépendances réseau cloud-native"),
        )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/14-alignement-cdc-v4.10.0.csv",
            ("REQ-00470", "EPIC-2102"),
        )
        migrations = sorted((self._root / "installers/migrations/postgresql").glob("*.sql"))
        if len(migrations) < 55 or migrations[54].name != "0055_kubernetes_topology_inventory.sql":
            raise KubernetesExposureProjectError(
                "EPIC-2102 must reuse the immutable Kubernetes snapshot schema and keep the "
                "migration chain containing 0055_kubernetes_topology_inventory.sql at position 55"
            )
        return {
            "schema_version": 1,
            "report_kind": "kubernetes-cloud-native-exposure-contract",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "phase": "P21",
            "epic": "EPIC-2102",
            "release": "REL-11",
            "roadmap_version": "2.3.0",
            "network_flow_correlation": True,
            "rsot_dependency_correlation": True,
            "read_only_projection": True,
            "max_flow_declarations": 10_000,
            "max_dependency_relations": 10_000,
            "max_dependency_objects": 2_048,
            "api_cli_web_parity": True,
        }

    def _assert_fragments(self, relative: str, fragments: tuple[str, ...]) -> None:
        content = (self._root / relative).read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in content]
        if missing:
            raise KubernetesExposureProjectError(
                f"{relative} is incomplete for P21/EPIC-2102: " + ", ".join(missing)
            )


class KubernetesExposureProjectCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P21/EPIC-2102 contracts")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = KubernetesExposureProjectValidator(args.project_root).validate()
        except KubernetesExposureProjectError as exc:
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
    raise SystemExit(KubernetesExposureProjectCli.main())
