from __future__ import annotations

import importlib.metadata
from pathlib import Path

import openinfra
from openinfra.interfaces.http_api import OpenApiDocumentProvider
from openinfra.quality.dependency_graph_benchmark import DependencyGraphBenchmarkConfig


class InstalledWheelSmokeError(RuntimeError):
    """Raised when the installed OpenInfra distribution is incomplete."""


class InstalledWheelSmoke:
    EXPECTED_VERSION = "0.29.99"
    EXPECTED_GRAPH_ROUTES = (
        "/api/v1/graph/traverse",
        "/api/v1/graph/impact",
        "/api/v1/graph/path",
        "/api/v1/graph/spof",
        "/api/v1/graph/export",
    )
    EXPECTED_FLOW_ROUTES = (
        "/api/v1/flows/declarations",
        "/api/v1/flows/declarations/upsert",
        "/api/v1/flows/declarations/retire",
        "/api/v1/flows/observations",
        "/api/v1/flows/observations/submit",
        "/api/v1/flows/matrix",
    )
    EXPECTED_CERTIFICATE_ROUTES = (
        "/api/v1/certificates",
        "/api/v1/certificates/get",
        "/api/v1/certificates/import",
        "/api/v1/certificates/retire",
        "/api/v1/certificates/endpoints",
        "/api/v1/certificates/endpoints/observe",
        "/api/v1/certificates/assessment",
    )
    EXPECTED_NETWORK_CONFIG_ROUTES = (
        "/api/v1/network-config/baselines",
        "/api/v1/network-config/baselines/upsert",
        "/api/v1/network-config/baselines/retire",
        "/api/v1/network-config/observations",
        "/api/v1/network-config/observations/submit",
        "/api/v1/network-config/assessment",
    )
    EXPECTED_SIMULATION_ROUTES = (
        "/api/v1/simulation-scenarios",
        "/api/v1/simulation-scenarios/get",
        "/api/v1/simulation-scenarios/create",
        "/api/v1/simulation-scenarios/run",
        "/api/v1/simulation-scenarios/cancel",
        "/api/v1/impact-reports",
        "/api/v1/impact-reports/get",
        "/api/v1/scenario-comparisons",
        "/api/v1/scenario-comparisons/create",
    )
    EXPECTED_FINOPS_ROUTES = (
        "/api/v1/finops/allocation-rules",
        "/api/v1/finops/allocation-rules/create",
        "/api/v1/finops/import-jobs",
        "/api/v1/finops/import-jobs/get",
        "/api/v1/finops/import-jobs/submit",
        "/api/v1/finops/import-jobs/run",
        "/api/v1/finops/import-jobs/cancel",
        "/api/v1/finops/cost-records",
        "/api/v1/finops/budgets",
        "/api/v1/finops/budgets/upsert",
        "/api/v1/finops/periods",
        "/api/v1/finops/periods/close",
        "/api/v1/finops/reports",
        "/api/v1/finops/reports/get",
        "/api/v1/finops/reports/generate",
        "/api/v1/finops/reports/export",
        "/api/v1/finops/anomalies",
        "/api/v1/finops/forecasts",
    )
    EXPECTED_GREENOPS_ROUTES = (
        "/api/v1/greenops/measurement-sources",
        "/api/v1/greenops/measurement-sources/create",
        "/api/v1/greenops/policies/get",
        "/api/v1/greenops/policies/upsert",
        "/api/v1/greenops/carbon-factors",
        "/api/v1/greenops/carbon-factors/create",
        "/api/v1/greenops/energy-measurements",
        "/api/v1/greenops/energy-measurements/ingest",
        "/api/v1/greenops/reports",
        "/api/v1/greenops/reports/get",
        "/api/v1/greenops/reports/generate",
        "/api/v1/greenops/reports/export",
        "/api/v1/greenops/anomalies",
        "/api/v1/greenops/capacity-forecasts",
        "/api/v1/greenops/consolidation-candidates",
        "/api/v1/greenops/green-scores",
    )
    EXPECTED_SBOM_ROUTES = (
        "/api/v1/sbom/documents",
        "/api/v1/sbom/documents/get",
        "/api/v1/sbom/documents/import",
        "/api/v1/sbom/vulnerabilities",
        "/api/v1/sbom/vulnerabilities/import",
        "/api/v1/sbom/exposures",
        "/api/v1/sbom/exposures/get",
        "/api/v1/sbom/exposures/upsert",
        "/api/v1/sbom/findings",
        "/api/v1/sbom/risk/assess",
        "/api/v1/sbom/risk/export",
        "/api/v1/sbom/comparisons",
        "/api/v1/sbom/comparisons/get",
        "/api/v1/sbom/comparisons/create",
    )
    EXPECTED_FIELD_OPERATION_ROUTES = (
        "/api/v1/field-operation-sheets",
        "/api/v1/field-operation-sheets/get",
        "/api/v1/field-operation-sheets/generate",
        "/api/v1/field-operation-sheets/start",
        "/api/v1/field-operation-sheets/checklist",
        "/api/v1/field-operation-sheets/complete",
        "/api/v1/field-operation-sheets/cancel",
        "/api/v1/qr-codes/verify",
        "/api/v1/field-evidence",
        "/api/v1/field-evidence/attach",
        "/api/v1/field-evidence/validate",
        "/api/v1/intervention-locks/acquire",
        "/api/v1/intervention-locks/release",
        "/api/v1/offline-sync-packages",
        "/api/v1/offline-sync-packages/get",
        "/api/v1/offline-sync-packages/create",
        "/api/v1/offline-sync-packages/synchronize",
    )
    EXPECTED_LAST_MIGRATION = "0048_sbom_vulnerabilities_exposure.sql"
    EXPECTED_MIGRATION_COUNT = 48
    EXPECTED_ASSETS = (
        "openinfra-web.js",
        "openinfra-web.css",
        "openinfra-i18n.js",
        "openinfra-form-fields.js",
    )

    def run(self) -> dict[str, object]:
        self._assert_version()
        package_root = Path(openinfra.__file__).resolve().parent
        openapi = OpenApiDocumentProvider().read_yaml()
        self._assert_graph_routes(openapi)
        self._assert_flow_routes(openapi)
        self._assert_certificate_routes(openapi)
        self._assert_network_config_routes(openapi)
        self._assert_field_operation_routes(openapi)
        self._assert_finops_routes(openapi)
        self._assert_greenops_routes(openapi)
        self._assert_sbom_routes(openapi)
        self._assert_simulation_routes(openapi)
        migrations = self._assert_migrations(package_root)
        self._assert_assets(package_root)
        self._assert_benchmark_contract()
        self._assert_console_scripts()
        return {
            "version": openinfra.__version__,
            "graph_routes": len(self.EXPECTED_GRAPH_ROUTES),
            "flow_routes": len(self.EXPECTED_FLOW_ROUTES),
            "certificate_routes": len(self.EXPECTED_CERTIFICATE_ROUTES),
            "network_config_routes": len(self.EXPECTED_NETWORK_CONFIG_ROUTES),
            "field_operation_routes": len(self.EXPECTED_FIELD_OPERATION_ROUTES),
            "finops_routes": len(self.EXPECTED_FINOPS_ROUTES),
            "greenops_routes": len(self.EXPECTED_GREENOPS_ROUTES),
            "sbom_routes": len(self.EXPECTED_SBOM_ROUTES),
            "simulation_routes": len(self.EXPECTED_SIMULATION_ROUTES),
            "migrations": len(migrations),
            "last_migration": migrations[-1].name,
            "runtime_assets": len(self.EXPECTED_ASSETS),
            "dependency_graph_benchmark": True,
        }

    def _assert_version(self) -> None:
        if openinfra.__version__ != self.EXPECTED_VERSION:
            raise InstalledWheelSmokeError(
                f"expected OpenInfra {self.EXPECTED_VERSION}, got {openinfra.__version__}"
            )
        distribution_version = importlib.metadata.version("openinfra")
        if distribution_version != self.EXPECTED_VERSION:
            raise InstalledWheelSmokeError(
                "installed distribution metadata version does not match runtime version"
            )

    def _assert_graph_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_GRAPH_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing graph routes: " + ", ".join(missing)
            )

    def _assert_flow_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_FLOW_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing flow routes: " + ", ".join(missing)
            )

    def _assert_certificate_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_CERTIFICATE_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing certificate routes: " + ", ".join(missing)
            )

    def _assert_network_config_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_NETWORK_CONFIG_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing network configuration routes: "
                + ", ".join(missing)
            )

    def _assert_simulation_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_SIMULATION_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing simulation routes: " + ", ".join(missing)
            )

    def _assert_finops_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_FINOPS_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing FinOps routes: " + ", ".join(missing)
            )

    def _assert_greenops_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_GREENOPS_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing GreenOps routes: " + ", ".join(missing)
            )

    def _assert_sbom_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_SBOM_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing SBOM routes: " + ", ".join(missing)
            )

    def _assert_field_operation_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_FIELD_OPERATION_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing field operation routes: "
                + ", ".join(missing)
            )

    def _assert_migrations(self, package_root: Path) -> tuple[Path, ...]:
        migration_root = package_root / "migrations" / "postgresql"
        migrations = tuple(sorted(migration_root.glob("*.sql")))
        if len(migrations) != self.EXPECTED_MIGRATION_COUNT:
            raise InstalledWheelSmokeError(
                f"expected {self.EXPECTED_MIGRATION_COUNT} migrations, got {len(migrations)}"
            )
        if migrations[-1].name != self.EXPECTED_LAST_MIGRATION:
            raise InstalledWheelSmokeError(f"unexpected last migration: {migrations[-1].name}")
        return migrations

    def _assert_assets(self, package_root: Path) -> None:
        assets_root = package_root / "interfaces" / "rendering" / "static" / "assets"
        missing = [name for name in self.EXPECTED_ASSETS if not (assets_root / name).is_file()]
        if missing:
            raise InstalledWheelSmokeError(
                "installed runtime is missing web assets: " + ", ".join(missing)
            )

    def _assert_benchmark_contract(self) -> None:
        config = DependencyGraphBenchmarkConfig(
            node_count=100,
            spof_hub_count=10,
            samples=1,
            warmups=0,
        ).validate()
        if config.node_count != 100 or config.spof_hub_count != 10:
            raise InstalledWheelSmokeError("dependency graph benchmark contract is invalid")

    def _assert_console_scripts(self) -> None:
        entry_points = {
            entry_point.name: entry_point.value
            for entry_point in importlib.metadata.entry_points(group="console_scripts")
            if entry_point.dist is not None and entry_point.dist.name == "openinfra"
        }
        expected = {
            "openinfra": "openinfra.interfaces.cli:OpenInfraCLI.main",
            "openinfra-api": "openinfra.interfaces.http_api:OpenInfraApiEntrypoint.main",
            "openinfra-web": "openinfra.interfaces.web:OpenInfraWebEntrypoint.main",
        }
        if entry_points != expected:
            raise InstalledWheelSmokeError(
                f"installed console scripts do not match the public contract: {entry_points}"
            )


if __name__ == "__main__":
    print(InstalledWheelSmoke().run())
