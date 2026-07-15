from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path


class ArtifactVerificationError(Exception):
    """Raised when a packaged artifact does not contain required files."""


class WheelVerifier:
    REQUIRED_SUFFIXES = (
        "openinfra/__init__.py",
        "openinfra/domain/dcim.py",
        "openinfra/domain/dependency.py",
        "openinfra/domain/ipam.py",
        "openinfra/application/dependency_graph_services.py",
        "openinfra/quality/dependency_graph_benchmark.py",
        "openinfra/application/flow_matrix_services.py",
        "openinfra/domain/flow_matrix.py",
        "openinfra/domain/certificate_pki.py",
        "openinfra/application/certificate_pki_services.py",
        "openinfra/infrastructure/certificate_parser.py",
        "openinfra/infrastructure/read_routing.py",
        "openinfra/infrastructure/observability.py",
        "openinfra/infrastructure/multisite_observability.py",
        "openinfra/interfaces/asgi_observability.py",
        "openinfra/quality/capacity_certification.py",
        "openinfra/quality/continuity_certification.py",
        "openinfra/quality/release_security.py",
        "openinfra/quality/release_packaging.py",
        "openinfra/quality/ga_go_no_go.py",
        "openinfra/docs/release/ga-go-no-go-policy.json",
        "openinfra/docs/release/ga-trust-policy.schema.json",
        "openinfra/docs/runbooks/GA_GO_NO_GO.md",
        "openinfra/infrastructure/cursor_pagination.py",
        "openinfra/interfaces/asgi.py",
        "openinfra/interfaces/asgi_web.py",
        "openinfra/interfaces/openapi_taxonomy.py",
        "openinfra/domain/network_config_compliance.py",
        "openinfra/application/network_config_compliance_services.py",
        "openinfra/domain/field_operations.py",
        "openinfra/domain/finops.py",
        "openinfra/infrastructure/greenops_mapper.py",
        "openinfra/application/greenops_services.py",
        "openinfra/domain/greenops.py",
        "openinfra/domain/rag.py",
        "openinfra/domain/multisite.py",
        "openinfra/application/rag_services.py",
        "openinfra/application/multisite_services.py",
        "openinfra/infrastructure/rag_mapper.py",
        "openinfra/infrastructure/rag_generator.py",
        "openinfra/domain/kubernetes_topology.py",
        "openinfra/domain/kubernetes_exposure.py",
        "openinfra/domain/kubernetes_security.py",
        "openinfra/domain/kubernetes_capacity.py",
        "openinfra/application/kubernetes_topology_services.py",
        "openinfra/infrastructure/kubernetes_topology_mapper.py",
        "openinfra/domain/sbom.py",
        "openinfra/application/sbom_services.py",
        "openinfra/infrastructure/sbom_mapper.py",
        "openinfra/infrastructure/sbom_parser.py",
        "openinfra/domain/simulation.py",
        "openinfra/application/simulation_services.py",
        "openinfra/infrastructure/simulation_mapper.py",
        "openinfra/application/finops_services.py",
        "openinfra/infrastructure/finops_mapper.py",
        "openinfra/application/field_operation_services.py",
        "openinfra/infrastructure/field_operation_mapper.py",
        "openinfra/interfaces/cli.py",
        "openinfra/interfaces/rendering/static/assets/openinfra-i18n.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-form-fields.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-domain-manifest.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-management-resources.js",
        "openinfra/interfaces/rendering/static/assets/management/context-hierarchy.js",
        "openinfra/interfaces/rendering/static/assets/management/resources.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-query-cache.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-search-index.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-virtual-list.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-web-vitals.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-web.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-web.css",
        "openinfra/interfaces/rendering/static/assets/domains/rsot.js",
        "openinfra/interfaces/rendering/static/assets/domains/ipam.js",
        "openinfra/interfaces/rendering/static/assets/domains/dcim.js",
        "openinfra/interfaces/rendering/static/assets/domains/itam.js",
        "openinfra/interfaces/rendering/static/assets/domains/discovery.js",
        "openinfra/interfaces/rendering/static/assets/domains/data.js",
        "openinfra/interfaces/rendering/static/assets/domains/integrations.js",
        "openinfra/interfaces/rendering/static/assets/domains/security.js",
        "openinfra/api/openapi.yaml",
        "openinfra/migrations/postgresql/0041_flow_matrix.sql",
        "openinfra/migrations/postgresql/0043_network_config_compliance.sql",
        "openinfra/migrations/postgresql/0044_field_operations_mobile_offline.sql",
        "openinfra/migrations/postgresql/0045_simulation_migration_planning.sql",
        "openinfra/migrations/postgresql/0046_finops_costs_showback.sql",
        "openinfra/migrations/postgresql/0047_greenops_energy_capacity.sql",
        "openinfra/migrations/postgresql/0048_sbom_vulnerabilities_exposure.sql",
        "openinfra/migrations/postgresql/0049_rag_governed_assistant.sql",
        "openinfra/migrations/postgresql/0050_pro_centralized_multisite.sql",
        "openinfra/migrations/postgresql/0051_enterprise_regional_discovery_routing.sql",
        "openinfra/migrations/postgresql/0053_keyset_pagination_indexes.sql",
        "openinfra/migrations/postgresql/0054_async_outbox_workers.sql",
        "openinfra/migrations/postgresql/0055_kubernetes_topology_inventory.sql",
    )

    def verify(self, path: Path) -> None:
        if not path.is_file():
            raise ArtifactVerificationError(f"artifact does not exist: {path}")
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        self._assert_required_files(path, names)

    def _assert_required_files(self, path: Path, names: set[str]) -> None:
        missing = [
            suffix
            for suffix in self.REQUIRED_SUFFIXES
            if not any(name.endswith(suffix) for name in names)
        ]
        if missing:
            raise ArtifactVerificationError(
                f"{path.name} is missing required files: " + ", ".join(missing)
            )


class SourceDistributionVerifier:
    REQUIRED_SUFFIXES = (
        "src/openinfra/interfaces/openapi_taxonomy.py",
        "docs/api/openapi.yaml",
        "docs/operations/api-documentation-organization.md",
        "docs/operations/keyset-pagination-streaming.md",
        "docs/architecture/modular-virtualized-frontend.md",
        "docs/architecture/enterprise-observability-capacity.md",
        "docs/runbooks/OBSERVABILITY_CAPACITY.md",
        "docs/runbooks/PRA_PCA_CERTIFICATION.md",
        "docs/runbooks/MULTISITE_OBSERVABILITY.md",
        "docs/operations/multisite-observability-profile.json",
        "docs/runbooks/MULTISITE_CHAOS.md",
        "docs/runbooks/ENTERPRISE_SCALEOUT_PROMOTION.md",
        "docs/release/enterprise-scaleout-promotion-policy.json",
        "scripts/validate_scaleout_promotion.py",
        "scripts/assemble_scaleout_promotion_evidence.py",
        "scripts/certify_scaleout_promotion.py",
        ".github/workflows/enterprise-scaleout-promotion.yml",
        "docs/operations/multisite-chaos-profile.json",
        "scripts/run_multisite_chaos_campaign.py",
        "scripts/assemble_multisite_chaos_evidence.py",
        "scripts/certify_multisite_chaos.py",
        "scripts/validate_multisite_chaos.py",
        ".github/workflows/multisite-chaos.yml",
        "docker/observability/grafana/dashboards/openinfra-multisite-operations.json",
        "docker/observability/multisite-targets/.keep",
        "scripts/validate_multisite_observability.py",
        "src/openinfra/infrastructure/multisite_observability.py",
        "docs/operations/pra-pca-profile.json",
        "docs/runbooks/RELEASE_SECURITY.md",
        "docs/runbooks/RELEASE_PACKAGING.md",
        "docs/architecture/release-packaging-certification.md",
        "docs/architecture/release-security-certification.md",
        "docs/operations/enterprise-capacity-profile.json",
        "docker/observability/prometheus.yml",
        "docker/observability/openinfra-alerts.yml",
        "docker/observability/otel-collector.yaml",
        "docker/observability/tempo.yaml",
        "scripts/run_enterprise_capacity_profile.py",
        "scripts/run_enterprise_workload_benchmark.py",
        "scripts/run_enterprise_benchmark_suite.py",
        "scripts/run_enterprise_chaos_profile.py",
        "scripts/assemble_enterprise_capacity_evidence.py",
        "scripts/certify_enterprise_capacity.py",
        "scripts/assemble_pra_pca_evidence.py",
        "scripts/certify_pra_pca.py",
        "scripts/validate_pra_pca.py",
        ".github/workflows/enterprise-capacity.yml",
        ".github/workflows/pra-pca-certification.yml",
        ".github/workflows/release-security.yml",
        ".github/workflows/release-packaging.yml",
        ".github/workflows/ga-go-no-go.yml",
        "scripts/ga_go_no_go.py",
        "docs/release/ga-go-no-go-policy.json",
        "docs/release/ga-trust-policy.schema.json",
        "docs/runbooks/GA_GO_NO_GO.md",
        "scripts/release_security_audit.py",
        "scripts/release_packaging_audit.py",
        "scripts/security_http_probe.py",
        "docs/operations/frontend-performance.md",
        "scripts/benchmark_cursor_pagination.py",
        "installers/migrations/postgresql/0053_keyset_pagination_indexes.sql",
        "installers/migrations/postgresql/0054_async_outbox_workers.sql",
        "installers/migrations/postgresql/0055_kubernetes_topology_inventory.sql",
        "installers/migrations/postgresql/0056_kubernetes_gitops_drift.sql",
        "src/openinfra/domain/kubernetes_topology.py",
        "src/openinfra/domain/kubernetes_exposure.py",
        "src/openinfra/domain/kubernetes_security.py",
        "src/openinfra/domain/kubernetes_gitops.py",
        "src/openinfra/domain/kubernetes_capacity.py",
        "src/openinfra/application/kubernetes_gitops_services.py",
        "src/openinfra/infrastructure/kubernetes_gitops_mapper.py",
        "src/openinfra/application/kubernetes_topology_services.py",
        "src/openinfra/infrastructure/kubernetes_topology_mapper.py",
        "docs/architecture/kubernetes-cloud-native-topology.md",
        "docs/operations/kubernetes-topology.md",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/VERSION",
        "scripts/validate_kubernetes_topology.py",
        "scripts/validate_kubernetes_exposure.py",
        "scripts/validate_kubernetes_security.py",
        "scripts/validate_kubernetes_gitops.py",
        "scripts/validate_kubernetes_capacity.py",
        "docs/architecture/kubernetes-gitops-drift.md",
        "docs/operations/kubernetes-gitops-drift.md",
        "docs/architecture/kubernetes-capacity.md",
        "docs/operations/kubernetes-capacity.md",
        "docs/architecture/kubernetes-cloud-native-security.md",
        "docs/operations/kubernetes-security-correlation.md",
        "tests/unit/test_kubernetes_exposure.py",
        "tests/unit/test_kubernetes_security.py",
        "tests/integration/test_kubernetes_exposure_services.py",
        "tests/integration/test_kubernetes_exposure_http_api.py",
        "tests/integration/test_kubernetes_exposure_cli.py",
        "tests/integration/test_kubernetes_exposure_web_contract.py",
        "tests/integration/test_kubernetes_security_services.py",
        "tests/integration/test_kubernetes_security_http_api.py",
        "tests/integration/test_kubernetes_security_cli.py",
        "tests/integration/test_kubernetes_security_web_contract.py",
        "tests/integration/test_kubernetes_security_tooling.py",
        "tests/unit/test_kubernetes_gitops.py",
        "tests/integration/test_kubernetes_gitops_services.py",
        "tests/integration/test_kubernetes_gitops_http_api.py",
        "tests/integration/test_kubernetes_gitops_cli.py",
        "tests/integration/test_kubernetes_gitops_postgresql_repository.py",
        "tests/integration/test_kubernetes_gitops_migration.py",
        "tests/integration/test_kubernetes_gitops_web_contract.py",
        "tests/integration/test_kubernetes_gitops_tooling.py",
        "tests/unit/test_kubernetes_capacity.py",
        "tests/integration/test_kubernetes_capacity_services.py",
        "tests/integration/test_kubernetes_capacity_http_api.py",
        "tests/integration/test_kubernetes_capacity_cli.py",
        "tests/integration/test_kubernetes_capacity_web_contract.py",
        "tests/integration/test_kubernetes_capacity_tooling.py",
        "requirements/runtime.txt",
        "requirements/security-audit.txt",
        ".github/workflows/ci.yml",
        "VALIDATION-REPORT.md",
    )

    def verify(self, path: Path) -> None:
        if not path.is_file():
            raise ArtifactVerificationError(f"artifact does not exist: {path}")
        with tarfile.open(path) as archive:
            names = set(archive.getnames())
        missing = [
            suffix
            for suffix in self.REQUIRED_SUFFIXES
            if not any(name.endswith(suffix) for name in names)
        ]
        if missing:
            raise ArtifactVerificationError(
                f"{path.name} is missing required files: " + ", ".join(missing)
            )


class ArtifactVerifierCli:
    @classmethod
    def main(cls) -> int:
        if len(sys.argv) < 2:
            print("usage: verify_artifact.py <artifact> [<artifact>...]", file=sys.stderr)
            return 2
        wheel_verifier = WheelVerifier()
        sdist_verifier = SourceDistributionVerifier()
        try:
            for item in sys.argv[1:]:
                path = Path(item)
                if path.suffix == ".whl":
                    wheel_verifier.verify(path)
                elif path.name.endswith(".tar.gz"):
                    sdist_verifier.verify(path)
                else:
                    raise ArtifactVerificationError(f"unsupported artifact type: {path.name}")
        except ArtifactVerificationError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(ArtifactVerifierCli.main())
