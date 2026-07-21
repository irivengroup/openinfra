from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class KubernetesSecurityProjectError(Exception):
    """Raised when the P21/EPIC-2103 cloud-native security contract is incomplete."""


class KubernetesSecurityProjectValidator:
    REQUIRED_FILES = (
        "src/openinfra/domain/kubernetes_topology.py",
        "src/openinfra/domain/kubernetes_security.py",
        "src/openinfra/application/kubernetes_topology_services.py",
        "src/openinfra/interfaces/http_api.py",
        "src/openinfra/interfaces/cli.py",
        "docs/api/openapi.yaml",
        "docs/architecture/kubernetes-cloud-native-security.md",
        "docs/operations/kubernetes-security-correlation.md",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/04-roadmap-epics.csv",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/09-roadmap-tests-validation.csv",
        "tests/unit/test_kubernetes_security.py",
        "tests/integration/test_kubernetes_security_services.py",
        "tests/integration/test_kubernetes_security_http_api.py",
        "tests/integration/test_kubernetes_security_cli.py",
        "tests/integration/test_kubernetes_security_web_contract.py",
        "tests/integration/test_kubernetes_security_tooling.py",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        missing = [item for item in self.REQUIRED_FILES if not (self._root / item).is_file()]
        if missing:
            raise KubernetesSecurityProjectError(
                "missing P21/EPIC-2103 cloud-native security assets: " + ", ".join(missing)
            )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_security.py",
            (
                "class KubernetesImageReference",
                "class KubernetesSecretReference",
                "class KubernetesSecurityCorrelationReport",
                'display = f"{prefix}***"',
                "reference_hash",
                "images_without_sbom",
                "critical_vulnerability_count",
                "unknown_certificate_count",
            ),
        )
        self._assert_fragments(
            "src/openinfra/domain/kubernetes_topology.py",
            (
                "images: tuple[KubernetesImageReference, ...]",
                "certificate_fingerprints: tuple[str, ...]",
                "secret_refs: tuple[KubernetesSecretReference, ...]",
                "if self.images:",
                "if self.certificate_fingerprints:",
                "if self.secret_refs:",
            ),
        )
        self._assert_fragments(
            "src/openinfra/application/kubernetes_topology_services.py",
            (
                "_MAX_SBOM_DOCUMENTS = 2_000",
                "_MAX_SBOM_DIRECT_REFERENCES = 512",
                "_MAX_SBOM_FINDINGS = 10_000",
                "def security(",
                "def latest_security(",
                "SBOM document repository returned a cyclic cursor",
                "SBOM finding repository returned a cyclic cursor",
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/http_api.py",
            (
                '"/api/v1/kubernetes/topologies/security"',
                '"/api/v1/kubernetes/topologies/latest-security"',
            ),
        )
        self._assert_fragments(
            "src/openinfra/interfaces/cli.py",
            ('"security"', '"latest-security"'),
        )
        self._assert_fragments(
            "docs/api/openapi.yaml",
            (
                "/api/v1/kubernetes/topologies/security:",
                "/api/v1/kubernetes/topologies/latest-security:",
                "Secret values are never ingested or resolved",
            ),
        )
        for relative in (
            "web/src/domains/discovery.js",
            "src/openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        ):
            self._assert_fragments(
                relative,
                ("kubernetes-security-latest", "kubernetes-security-snapshot"),
            )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/04-roadmap-epics.csv",
            ("EPIC-2103", "Corrélation images SBOM certificats et secrets référencés"),
        )
        self._assert_fragments(
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/09-roadmap-tests-validation.csv",
            ("TST-P21-K8S-SECURITY-CORRELATION", "Corrélation sécurité"),
        )
        migrations = sorted((self._root / "installers/migrations/postgresql").glob("*.sql"))
        if len(migrations) < 55 or migrations[54].name != "0055_kubernetes_topology_inventory.sql":
            raise KubernetesSecurityProjectError(
                "EPIC-2103 must reuse immutable Kubernetes snapshot storage and keep the "
                "migration chain containing 0055_kubernetes_topology_inventory.sql at position 55"
            )
        return {
            "schema_version": 1,
            "report_kind": "kubernetes-cloud-native-security-contract",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": True,
            "phase": "P21",
            "epic": "EPIC-2103",
            "release": "REL-11",
            "roadmap_version": "2.3.0",
            "image_sbom_correlation": True,
            "contextual_vulnerability_findings": True,
            "certificate_correlation": True,
            "secret_material_ingestion": False,
            "masked_secret_references": True,
            "legacy_snapshot_fingerprint_compatibility": True,
            "max_sbom_documents": 2_000,
            "max_sbom_findings": 10_000,
            "api_cli_web_parity": True,
        }

    def _assert_fragments(self, relative: str, fragments: tuple[str, ...]) -> None:
        content = (self._root / relative).read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in content]
        if missing:
            raise KubernetesSecurityProjectError(
                f"{relative} is incomplete for P21/EPIC-2103: " + ", ".join(missing)
            )


class KubernetesSecurityProjectCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P21/EPIC-2103 contracts")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = KubernetesSecurityProjectValidator(args.project_root).validate()
        except KubernetesSecurityProjectError as exc:
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
    raise SystemExit(KubernetesSecurityProjectCli.main())
