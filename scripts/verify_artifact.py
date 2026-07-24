from __future__ import annotations

import hashlib
import re
import sys
import tarfile
import zipfile
from pathlib import Path


class ArtifactVerificationError(Exception):
    """Raised when a packaged artifact does not contain required files."""


class MigrationArtifactParityVerifier:
    MIGRATION_NAME = re.compile(r"[0-9]{4}_[a-z0-9][a-z0-9_]*\.sql")

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = (project_root or Path.cwd()).resolve()
        self._expected = {
            database: self._source_payloads(database)
            for database in ("postgresql", "oracle")
        }

    def verify_wheel(self, archive: zipfile.ZipFile, artifact: Path) -> None:
        names = set(archive.namelist())
        for database, expected in self._expected.items():
            prefix = f"openinfra/migrations/{database}/"
            observed = {
                name.removeprefix(prefix): name
                for name in names
                if name.startswith(prefix) and not name.endswith("/")
            }
            self._verify_members(archive, artifact, database, expected, observed)

    def verify_sdist(self, archive: tarfile.TarFile, artifact: Path) -> None:
        names = {member.name for member in archive.getmembers() if member.isfile()}
        for database, expected in self._expected.items():
            for relative_root in (
                f"installers/migrations/{database}/",
                f"src/openinfra/migrations/{database}/",
            ):
                observed: dict[str, str] = {}
                for name in names:
                    marker = f"/{relative_root}"
                    if marker in name:
                        observed[name.split(marker, 1)[1]] = name
                self._verify_members(archive, artifact, database, expected, observed)

    def _source_payloads(self, database: str) -> dict[str, bytes]:
        root = self._project_root / "installers/migrations" / database
        if not root.is_dir():
            raise ArtifactVerificationError(
                f"source migration catalogue is missing: {root}"
            )
        payloads = {path.name: path.read_bytes() for path in sorted(root.glob("*.sql"))}
        if database == "oracle":
            manifest = root / "manifest.json"
            if not manifest.is_file():
                raise ArtifactVerificationError(
                    f"source Oracle migration manifest is missing: {manifest}"
                )
            payloads[manifest.name] = manifest.read_bytes()
        invalid = [
            name
            for name in payloads
            if name != "manifest.json" and self.MIGRATION_NAME.fullmatch(name) is None
        ]
        if invalid or not payloads:
            raise ArtifactVerificationError(
                f"source {database} migration catalogue is invalid: {invalid}"
            )
        return payloads

    @classmethod
    def _verify_members(
        cls,
        archive: zipfile.ZipFile | tarfile.TarFile,
        artifact: Path,
        database: str,
        expected: dict[str, bytes],
        observed: dict[str, str],
    ) -> None:
        expected_names = set(expected)
        observed_names = set(observed)
        if observed_names != expected_names:
            missing = sorted(expected_names - observed_names)
            unexpected = sorted(observed_names - expected_names)
            raise ArtifactVerificationError(
                f"{artifact.name} has an incomplete {database} migration catalogue: "
                f"missing={missing}, unexpected={unexpected}"
            )
        for filename, source_payload in expected.items():
            member_name = observed[filename]
            if isinstance(archive, zipfile.ZipFile):
                payload = archive.read(member_name)
            else:
                extracted = archive.extractfile(member_name)
                if extracted is None:
                    raise ArtifactVerificationError(
                        f"{artifact.name} migration member cannot be read: {member_name}"
                    )
                payload = extracted.read()
            if hashlib.sha256(payload).digest() != hashlib.sha256(source_payload).digest():
                raise ArtifactVerificationError(
                    f"{artifact.name} migration checksum mismatch: {member_name}"
                )


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
        "openinfra/quality/migration_packaging.py",
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
        "openinfra/migrations/postgresql/0056_kubernetes_gitops_drift.sql",
        "openinfra/migrations/postgresql/0057_federated_identity_team_sync.sql",
        "openinfra/migrations/postgresql/0058_oracle_document_shards.sql",
        "openinfra/migrations/postgresql/0059_runtime_offline_licensing.sql",
        "openinfra/migrations/postgresql/0060_ipam_ddi_execution_journal.sql",
        "openinfra/migrations/oracle/0001_bootstrap.sql",
        "openinfra/migrations/oracle/0057_federated_identity_team_sync.sql",
        "openinfra/migrations/oracle/0058_oracle_document_shards.sql",
        "openinfra/migrations/oracle/0059_runtime_offline_licensing.sql",
        "openinfra/migrations/oracle/0060_ipam_ddi_execution_journal.sql",
        "openinfra/migrations/oracle/manifest.json",
        "openinfra/domain/federated_identity.py",
        "openinfra/application/advanced_identity_services.py",
        "openinfra/infrastructure/advanced_identity.py",
        "openinfra/infrastructure/external_identity.py",
        "openinfra/infrastructure/oracle.py",
        "openinfra/infrastructure/runtime_config.py",
        "openinfra/interfaces/server_runtime.py",
        "openinfra/docs/runbooks/RUNTIME_NATIVE.md",
        "openinfra/docs/runbooks/ADVANCED_IDENTITY_ORACLE_SYSTEMD.md",
        "openinfra/docs/runbooks/OFFLINE_RUNTIME_LICENSING.md",
        "openinfra/docs/runbooks/RSOT_CANONICAL_MIGRATION.md",
        "openinfra/docs/release/rsot-canonical-promotion-policy.json",
        "openinfra/quality/rsot_canonical_promotion.py",
        "openinfra/quality/contract_completeness_promotion.py",
        "openinfra/domain/ddi_sync.py",
        "openinfra/application/ddi_sync_services.py",
        "openinfra/infrastructure/ddi_executors.py",
        "openinfra/infrastructure/ddi_persistence.py",
        "openinfra/docs/release/contract-completeness-promotion-policy.json",
        "openinfra/docs/release/contract-proof-registry-v4.12.csv",
        "openinfra/docs/runbooks/CONTRACT_COMPLETENESS_PROMOTION.md",
        "openinfra/docs/runbooks/ASYNC_BULK_IMPORTS.md",
        "openinfra/docs/runbooks/DISTRIBUTED_DISCOVERY_RESULTS.md",
        "openinfra/docs/runbooks/APPLICATION_CHANGE_IMPACT.md",
        "openinfra/docs/runbooks/RSOT_TIME_TRAVEL.md",
        "openinfra/docs/runbooks/GOVERNED_RAG_ASSISTANT.md",
        "openinfra/docs/runbooks/RSOT_QUALITY_CERTIFICATION.md",
        "openinfra/docs/runbooks/RSOT_QUALITY_RBAC.md",
        "openinfra/docs/runbooks/WEB_TYPED_FORMS_SERVER_TRUST.md",
        "openinfra/docs/runbooks/DCIM_PLACEMENT_RECOMMENDATIONS.md",
        "openinfra/docs/runbooks/DCIM_LOCATION_IPAM_CONCURRENCY.md",
        "openinfra/docs/runbooks/IPAM_DDI_SYNCHRONIZATION.md",
        "openinfra/systemd/openinfra-runtime-secrets.service",
        "openinfra/systemd/openinfra-migrate.service",
        "openinfra/systemd/openinfra-team-sync.service",
        "openinfra/systemd/openinfra-team-sync.timer",
    )

    def verify(self, path: Path) -> None:
        if not path.is_file():
            raise ArtifactVerificationError(f"artifact does not exist: {path}")
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            self._assert_required_files(path, names)
            MigrationArtifactParityVerifier().verify_wheel(archive, path)

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
        "openinfra_build_backend.py",
        "src/openinfra/quality/migration_packaging.py",
        "scripts/build_migration_catalog.py",
        "tests/unit/test_openinfra_build_backend.py",
        "tests/unit/test_migration_packaging.py",
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
        "installers/migrations/postgresql/0057_federated_identity_team_sync.sql",
        "installers/migrations/postgresql/0058_oracle_document_shards.sql",
        "installers/migrations/postgresql/0059_runtime_offline_licensing.sql",
        "installers/migrations/postgresql/0060_ipam_ddi_execution_journal.sql",
        "installers/migrations/oracle/0001_bootstrap.sql",
        "installers/migrations/oracle/0057_federated_identity_team_sync.sql",
        "installers/migrations/oracle/0058_oracle_document_shards.sql",
        "installers/migrations/oracle/0059_runtime_offline_licensing.sql",
        "installers/migrations/oracle/0060_ipam_ddi_execution_journal.sql",
        "installers/migrations/oracle/manifest.json",
        "installers/systemd/openinfra-runtime-secrets.service",
        "installers/systemd/openinfra-migrate.service",
        "installers/systemd/openinfra-team-sync.service",
        "installers/systemd/openinfra-team-sync.timer",
        "src/openinfra/domain/federated_identity.py",
        "src/openinfra/application/advanced_identity_services.py",
        "src/openinfra/infrastructure/advanced_identity.py",
        "src/openinfra/infrastructure/external_identity.py",
        "src/openinfra/infrastructure/oracle.py",
        "src/openinfra/infrastructure/runtime_config.py",
        "src/openinfra/domain/ddi_sync.py",
        "src/openinfra/application/ddi_sync_services.py",
        "src/openinfra/infrastructure/ddi_executors.py",
        "src/openinfra/infrastructure/ddi_persistence.py",
        "src/openinfra/interfaces/server_runtime.py",
        "docs/runbooks/RUNTIME_NATIVE.md",
        "docs/runbooks/ADVANCED_IDENTITY_ORACLE_SYSTEMD.md",
        "docs/runbooks/IPAM_DDI_SYNCHRONIZATION.md",
        ".github/workflows/advanced-identity-oracle.yml",
        "tests/unit/test_federated_identity.py",
        "tests/unit/test_advanced_identity_adapters.py",
        "tests/unit/test_oracle_runtime.py",
        "tests/integration/test_advanced_identity_server_runtime.py",
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
        "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/VERSION",
        "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_runtime_licensing.py",
        "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_rsot_canonical.py",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5/VERSION",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5/scripts/validate_roadmap.py",
        ".github/workflows/offline-runtime-licensing.yml",
        "src/openinfra/quality/rsot_canonical_promotion.py",
        "docs/release/rsot-canonical-promotion-policy.json",
        "docs/runbooks/RSOT_CANONICAL_MIGRATION.md",
        ".github/workflows/rsot-canonical.yml",
        "tests/unit/test_gate13_qualification.py",
        "tests/integration/test_rsot_canonical_contract.py",
        "tests/integration/test_rsot_canonical_specifications.py",
        "src/openinfra/quality/contract_completeness_promotion.py",
        "docs/release/contract-completeness-promotion-policy.json",
        "docs/release/contract-proof-registry-v4.12.csv",
        "docs/runbooks/CONTRACT_COMPLETENESS_PROMOTION.md",
        "docs/runbooks/DCIM_PLACEMENT_RECOMMENDATIONS.md",
        "docs/runbooks/DCIM_LOCATION_IPAM_CONCURRENCY.md",
        ".github/workflows/contract-completeness.yml",
        "tests/unit/test_gate14_qualification.py",
        "tests/integration/test_contract_completeness_specifications.py",
        "tests/integration/test_contract_proof_registry.py",
        "tests/integration/test_contract_functional_physical_location.py",
        "tests/integration/test_contract_functional_ipam_concurrency.py",
        "tests/integration/test_contract_functional_bulk_import.py",
        "tests/integration/test_contract_functional_distributed_discovery.py",
        "tests/integration/test_contract_functional_change_impact.py",
        "tests/integration/test_contract_functional_time_travel.py",
        "tests/integration/test_contract_functional_rag_assistant.py",
        "tests/integration/test_contract_rsot_quality_certification.py",
        "tests/integration/test_contract_rsot_quality_non_authoritative.py",
        "tests/integration/test_contract_web_typed_server_trust.py",
        "tests/integration/test_contract_web_header_and_statistics.py",
        "docs/runbooks/ASYNC_BULK_IMPORTS.md",
        "docs/runbooks/DISTRIBUTED_DISCOVERY_RESULTS.md",
        "docs/runbooks/APPLICATION_CHANGE_IMPACT.md",
        "docs/runbooks/RSOT_TIME_TRAVEL.md",
        "docs/runbooks/GOVERNED_RAG_ASSISTANT.md",
        "docs/runbooks/RSOT_QUALITY_CERTIFICATION.md",
        "docs/runbooks/RSOT_QUALITY_RBAC.md",
        "docs/runbooks/RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md",
        "docs/runbooks/WEB_TYPED_FORMS_SERVER_TRUST.md",
        "web/tests/dcim-location.test.mjs",
        "web/tests/bulk-import.test.mjs",
        "web/tests/component-statistics.test.mjs",
        "web/tests/distributed-discovery.test.mjs",
        "web/tests/change-impact.test.mjs",
        "web/tests/time-travel.test.mjs",
        "web/tests/rag-governance.test.mjs",
        "web/tests/rsot-quality-certification.test.mjs",
        "web/tests/rsot-quality-non-authoritative.test.mjs",
        "scripts/validate_kubernetes_topology.py",
        "scripts/validate_kubernetes_exposure.py",
        "scripts/validate_kubernetes_security.py",
        "scripts/validate_kubernetes_gitops.py",
        "scripts/validate_kubernetes_capacity.py",
        "scripts/validate_cloud_native_promotion.py",
        "scripts/run_cloud_native_qualification.py",
        "scripts/assemble_cloud_native_promotion_evidence.py",
        "scripts/certify_cloud_native_promotion.py",
        "src/openinfra/quality/cloud_native_promotion.py",
        "docs/release/cloud-native-promotion-policy.json",
        "docs/runbooks/CLOUD_NATIVE_PROMOTION.md",
        ".github/workflows/cloud-native-promotion.yml",
        "tests/unit/test_cloud_native_promotion.py",
        "tests/integration/test_cloud_native_promotion_tooling.py",
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
        "tests/integration/test_kubernetes_unit_of_work_regression.py",
        "requirements/runtime.txt",
        "requirements/security-audit.txt",
        "scripts/docker_environment.py",
        "tests/integration/test_runtime_docker_environment.py",
        "tests/integration/test_openinfra_web.py",
        "tests/integration/test_http_api.py",
        ".github/workflows/ci.yml",
        "VALIDATION-REPORT.md",
    )

    def verify(self, path: Path) -> None:
        if not path.is_file():
            raise ArtifactVerificationError(f"artifact does not exist: {path}")
        with tarfile.open(path) as archive:
            names = set(archive.getnames())
            MigrationArtifactParityVerifier().verify_sdist(archive, path)
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
