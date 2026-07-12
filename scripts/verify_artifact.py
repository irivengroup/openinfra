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
        "openinfra/interfaces/rendering/static/assets/openinfra-web.js",
        "openinfra/interfaces/rendering/static/assets/openinfra-web.css",
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
        "scripts/benchmark_cursor_pagination.py",
        "installers/migrations/postgresql/0053_keyset_pagination_indexes.sql",
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
