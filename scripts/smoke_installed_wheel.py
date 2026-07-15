from __future__ import annotations

import importlib.metadata
from pathlib import Path

import openinfra
from openinfra.infrastructure.multisite_observability import (
    MultisiteOperationalMetricsProvider,
)
from openinfra.interfaces.http_api import OpenApiDocumentProvider
from openinfra.quality.continuity_certification import PraPcaCertificationEvidence
from openinfra.quality.dependency_graph_benchmark import DependencyGraphBenchmarkConfig
from openinfra.quality.ga_go_no_go import GaGoNoGoPolicy
from openinfra.quality.multisite_chaos import MultisiteChaosCampaignEvidence
from openinfra.quality.release_packaging import ReleaseSigningMaterial
from openinfra.quality.release_security import ReleaseSecurityControlCatalog
from openinfra.quality.scaleout_promotion import ScaleoutPromotionPolicy
from openinfra.quality.support_readiness import SupportPolicy


class InstalledWheelSmokeError(RuntimeError):
    """Raised when the installed OpenInfra distribution is incomplete."""


class InstalledWheelSmoke:
    EXPECTED_VERSION = "0.33.4"
    EXPECTED_ASYNC_ROUTES = (
        "/api/v1/async/jobs",
        "/api/v1/async/jobs/get",
        "/api/v1/async/jobs/submit",
        "/api/v1/async/jobs/claim",
        "/api/v1/async/jobs/renew",
        "/api/v1/async/jobs/complete",
        "/api/v1/async/jobs/fail",
        "/api/v1/async/jobs/replay",
        "/api/v1/async/artifacts/put",
        "/api/v1/async/artifacts/get",
        "/api/v1/async/workers/reporting/run-once",
        "/api/v1/async/workers/imports/run-once",
        "/api/v1/async/workers/graph/run-once",
        "/api/v1/async/workers/rag/run-once",
        "/api/v1/async/outbox-events",
        "/api/v1/async/outbox-events/get",
        "/api/v1/async/outbox-events/claim",
        "/api/v1/async/outbox-events/renew",
        "/api/v1/async/outbox-events/publish",
        "/api/v1/async/outbox-events/fail",
        "/api/v1/async/outbox-events/replay",
        "/api/v1/async/metrics",
    )
    EXPECTED_OBSERVABILITY_ROUTES = ("/metrics",)
    EXPECTED_DATA_PLANE_ROUTES = ("/api/v1/database/routing",)
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
    EXPECTED_RAG_ROUTES = (
        "/api/v1/rag/documents",
        "/api/v1/rag/documents/get",
        "/api/v1/rag/documents/upsert",
        "/api/v1/rag/documents/deactivate",
        "/api/v1/rag/index/rsot",
        "/api/v1/rag/query",
        "/api/v1/rag/answers",
        "/api/v1/rag/answers/get",
        "/api/v1/rag/jobs",
        "/api/v1/rag/jobs/get",
        "/api/v1/rag/jobs/create",
        "/api/v1/rag/jobs/run",
        "/api/v1/rag/jobs/artifact",
    )
    EXPECTED_KUBERNETES_ROUTES = (
        "/api/v1/kubernetes/topologies",
        "/api/v1/kubernetes/topologies/get",
        "/api/v1/kubernetes/topologies/latest",
        "/api/v1/kubernetes/topologies/topology",
        "/api/v1/kubernetes/topologies/latest-topology",
        "/api/v1/kubernetes/topologies/exposure",
        "/api/v1/kubernetes/topologies/latest-exposure",
        "/api/v1/kubernetes/topologies/security",
        "/api/v1/kubernetes/topologies/latest-security",
        "/api/v1/kubernetes/topologies/import",
    )
    EXPECTED_MULTISITE_ROUTES = (
        "/api/v1/multisite/site-access/grants",
        "/api/v1/multisite/site-access/grants/upsert",
        "/api/v1/multisite/site-access/grants/revoke",
        "/api/v1/multisite/sites",
        "/api/v1/multisite/reports",
        "/api/v1/multisite/reports/get",
        "/api/v1/multisite/reports/generate",
        "/api/v1/multisite/disaster-recovery/plans",
        "/api/v1/multisite/disaster-recovery/plans/get",
        "/api/v1/multisite/disaster-recovery/plans/configure",
        "/api/v1/multisite/disaster-recovery/plans/disable",
        "/api/v1/multisite/disaster-recovery/drills",
        "/api/v1/multisite/disaster-recovery/drills/get",
        "/api/v1/multisite/disaster-recovery/drills/execute",
        "/api/v1/multisite/regional-discovery/routes",
        "/api/v1/multisite/regional-discovery/routes/get",
        "/api/v1/multisite/regional-discovery/routes/configure",
        "/api/v1/multisite/regional-discovery/routes/disable",
        "/api/v1/multisite/regional-discovery/jobs/route",
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
    EXPECTED_LAST_MIGRATION = "0055_kubernetes_topology_inventory.sql"
    EXPECTED_MIGRATION_COUNT = 55
    EXPECTED_ASSETS = (
        "openinfra-web.js",
        "openinfra-web.css",
        "openinfra-i18n.js",
        "openinfra-form-fields.js",
        "openinfra-domain-manifest.js",
        "openinfra-management-resources.js",
        "management/context-hierarchy.js",
        "management/resources.js",
        "openinfra-query-cache.js",
        "openinfra-search-index.js",
        "openinfra-virtual-list.js",
        "openinfra-web-vitals.js",
    )
    EXPECTED_DOMAIN_ASSETS = (
        "rsot.js",
        "ipam.js",
        "dcim.js",
        "itam.js",
        "discovery.js",
        "data.js",
        "integrations.js",
        "security.js",
    )
    EXPECTED_GA_DOCUMENTS = (
        "documentation-manifest.json",
        "README.md",
        "INSTALLATION.md",
        "ADMINISTRATION.md",
        "USER_GUIDE.md",
        "API_GUIDE.md",
        "OPERATIONS.md",
        "DISASTER_RECOVERY.md",
        "UPGRADE.md",
        "TROUBLESHOOTING.md",
        "SUPPORT.md",
    )

    def run(self) -> dict[str, object]:
        self._assert_version()
        package_root = Path(openinfra.__file__).resolve().parent
        openapi = OpenApiDocumentProvider().read_yaml()
        self._assert_openapi_taxonomy(openapi)
        self._assert_async_routes(openapi)
        self._assert_observability_routes(openapi)
        self._assert_data_plane_routes(openapi)
        self._assert_graph_routes(openapi)
        self._assert_flow_routes(openapi)
        self._assert_certificate_routes(openapi)
        self._assert_network_config_routes(openapi)
        self._assert_field_operation_routes(openapi)
        self._assert_finops_routes(openapi)
        self._assert_greenops_routes(openapi)
        self._assert_sbom_routes(openapi)
        self._assert_rag_routes(openapi)
        self._assert_kubernetes_routes(openapi)
        self._assert_multisite_routes(openapi)
        self._assert_simulation_routes(openapi)
        migrations = self._assert_migrations(package_root)
        self._assert_assets(package_root)
        self._assert_ga_documentation(package_root)
        self._assert_ga_go_no_go_contract(package_root)
        self._assert_support_readiness_contract(package_root)
        self._assert_pra_pca_contract()
        self._assert_multisite_observability_contract()
        self._assert_multisite_chaos_contract()
        self._assert_scaleout_promotion_contract(package_root)
        self._assert_benchmark_contract()
        self._assert_release_security_contract(package_root)
        self._assert_release_packaging_contract()
        self._assert_console_scripts()
        return {
            "version": openinfra.__version__,
            "openapi_taxonomy": True,
            "async_routes": len(self.EXPECTED_ASYNC_ROUTES),
            "observability_routes": len(self.EXPECTED_OBSERVABILITY_ROUTES),
            "data_plane_routes": len(self.EXPECTED_DATA_PLANE_ROUTES),
            "graph_routes": len(self.EXPECTED_GRAPH_ROUTES),
            "flow_routes": len(self.EXPECTED_FLOW_ROUTES),
            "certificate_routes": len(self.EXPECTED_CERTIFICATE_ROUTES),
            "network_config_routes": len(self.EXPECTED_NETWORK_CONFIG_ROUTES),
            "field_operation_routes": len(self.EXPECTED_FIELD_OPERATION_ROUTES),
            "finops_routes": len(self.EXPECTED_FINOPS_ROUTES),
            "greenops_routes": len(self.EXPECTED_GREENOPS_ROUTES),
            "sbom_routes": len(self.EXPECTED_SBOM_ROUTES),
            "rag_routes": len(self.EXPECTED_RAG_ROUTES),
            "kubernetes_routes": len(self.EXPECTED_KUBERNETES_ROUTES),
            "multisite_routes": len(self.EXPECTED_MULTISITE_ROUTES),
            "simulation_routes": len(self.EXPECTED_SIMULATION_ROUTES),
            "migrations": len(migrations),
            "last_migration": migrations[-1].name,
            "runtime_assets": len(self.EXPECTED_ASSETS) + len(self.EXPECTED_DOMAIN_ASSETS),
            "ga_documents": len(self.EXPECTED_GA_DOCUMENTS),
            "ga_go_no_go_gate": "GATE-07",
            "dependency_graph_benchmark": True,
            "release_security_controls": 8,
            "release_packaging_controls": 7,
            "support_readiness": True,
            "pra_pca_certification": True,
            "multisite_observability": True,
            "multisite_chaos_certification": True,
            "enterprise_scaleout_gate": "GATE-09",
        }

    @staticmethod
    def _assert_scaleout_promotion_contract(package_root: Path) -> None:
        policy_path = (
            package_root / "docs" / "release" / "enterprise-scaleout-promotion-policy.json"
        )
        runbook_path = package_root / "docs" / "runbooks" / "ENTERPRISE_SCALEOUT_PROMOTION.md"
        if not runbook_path.is_file():
            raise InstalledWheelSmokeError(
                "installed wheel is missing the Enterprise Scale-out promotion runbook"
            )
        policy = ScaleoutPromotionPolicy.load(policy_path)
        if policy.gate_id != "GATE-09" or policy.release_id != "REL-10":
            raise InstalledWheelSmokeError("installed Enterprise Scale-out policy is inconsistent")
        if len(policy.required_evidence) != 7:
            raise InstalledWheelSmokeError("installed Enterprise Scale-out policy is incomplete")

    @staticmethod
    def _assert_multisite_observability_contract() -> None:
        if MultisiteOperationalMetricsProvider._max_routes != 10_000:
            raise InstalledWheelSmokeError(
                "installed multisite observability route bound is incomplete"
            )

    @staticmethod
    def _assert_multisite_chaos_contract() -> None:
        scenarios = MultisiteChaosCampaignEvidence.required_scenarios()
        if len(scenarios) != 6 or scenarios[-1] != "frontend-loss":
            raise InstalledWheelSmokeError(
                "installed multisite chaos certification contract is incomplete"
            )

    @staticmethod
    def _assert_pra_pca_contract() -> None:
        required = PraPcaCertificationEvidence.required_procedures()
        if len(required) != 10 or "pitr-execution" not in required:
            raise InstalledWheelSmokeError("installed PRA/PCA certification contract is incomplete")

    def _assert_openapi_taxonomy(self, openapi: str) -> None:
        required_fragments = (
            "x-tagGroups:",
            "Plateforme · Exploitation et documentation",
            "Plateforme · Observabilité et capacité",
            "Sécurité · Inventaire PKI",
            "IPAM · Conformité réseau",
            "Multisite · Reprise d'activité",
        )
        missing = [fragment for fragment in required_fragments if fragment not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI taxonomy is incomplete: " + ", ".join(missing)
            )

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

    def _assert_async_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_ASYNC_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing async routes: " + ", ".join(missing)
            )

    def _assert_observability_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_OBSERVABILITY_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing observability routes: " + ", ".join(missing)
            )

    def _assert_data_plane_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_DATA_PLANE_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI document is missing data-plane routes: " + ", ".join(missing)
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

    def _assert_rag_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_RAG_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI is missing RAG routes: " + ", ".join(missing)
            )

    def _assert_kubernetes_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_KUBERNETES_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI is missing Kubernetes topology routes: " + ", ".join(missing)
            )

    def _assert_multisite_routes(self, openapi: str) -> None:
        missing = [route for route in self.EXPECTED_MULTISITE_ROUTES if route not in openapi]
        if missing:
            raise InstalledWheelSmokeError(
                "installed OpenAPI is missing multisite routes: " + ", ".join(missing)
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
        domains_root = assets_root / "domains"
        missing.extend(
            f"domains/{name}"
            for name in self.EXPECTED_DOMAIN_ASSETS
            if not (domains_root / name).is_file()
        )
        if missing:
            raise InstalledWheelSmokeError(
                "installed runtime is missing web assets: " + ", ".join(missing)
            )

    def _assert_ga_documentation(self, package_root: Path) -> None:
        documentation_root = package_root / "docs" / "ga"
        missing = [
            name for name in self.EXPECTED_GA_DOCUMENTS if not (documentation_root / name).is_file()
        ]
        if missing:
            raise InstalledWheelSmokeError(
                "installed wheel is missing GA documentation: " + ", ".join(missing)
            )
        manifest = (documentation_root / "documentation-manifest.json").read_text(encoding="utf-8")
        if f'"release_version": "{self.EXPECTED_VERSION}"' not in manifest:
            raise InstalledWheelSmokeError(
                "installed GA documentation manifest version is inconsistent"
            )

    @staticmethod
    def _assert_ga_go_no_go_contract(package_root: Path) -> None:
        policy_path = package_root / "docs" / "release" / "ga-go-no-go-policy.json"
        runbook_path = package_root / "docs" / "runbooks" / "GA_GO_NO_GO.md"
        if not runbook_path.is_file():
            raise InstalledWheelSmokeError("installed wheel is missing the GA Go/No-Go runbook")
        policy = GaGoNoGoPolicy.load(policy_path)
        if policy.gate_id != "GATE-07" or policy.epic != "EPIC-1805":
            raise InstalledWheelSmokeError("installed GA Go/No-Go policy is inconsistent")
        if len(policy.required_evidence) != 8 or len(policy.required_approval_roles) != 5:
            raise InstalledWheelSmokeError("installed GA Go/No-Go policy is incomplete")

    @staticmethod
    def _assert_support_readiness_contract(package_root: Path) -> None:
        policy_path = package_root / "docs" / "release" / "support-maintenance-policy.json"
        runbook_path = package_root / "docs" / "runbooks" / "SUPPORT_MAINTENANCE.md"
        if not runbook_path.is_file():
            raise InstalledWheelSmokeError(
                "installed wheel is missing the support maintenance runbook"
            )
        policy = SupportPolicy.load(policy_path)
        if policy.epic != "EPIC-1806" or len(policy.profiles) != 3:
            raise InstalledWheelSmokeError("installed support readiness policy is incomplete")

    def _assert_benchmark_contract(self) -> None:
        config = DependencyGraphBenchmarkConfig(
            node_count=100,
            spof_hub_count=10,
            samples=1,
            warmups=0,
        ).validate()
        if config.node_count != 100 or config.spof_hub_count != 10:
            raise InstalledWheelSmokeError("dependency graph benchmark contract is invalid")

    @staticmethod
    def _assert_release_packaging_contract() -> None:
        material = ReleaseSigningMaterial.generate_ephemeral()
        payload = b"openinfra-installed-wheel"
        signature = material.sign(payload)
        material.verify(payload, signature)
        if len(signature) != 64:
            raise InstalledWheelSmokeError("installed release packaging signature is invalid")

    @staticmethod
    def _assert_release_security_contract(package_root: Path) -> None:
        controls = ReleaseSecurityControlCatalog.build(
            package_root,
            image_ref="openinfra/runtime:0.33.4",
            api_base_url="http://127.0.0.1:8080",
            web_base_url="http://127.0.0.1:2006",
        )
        if len(controls) != 8:
            raise InstalledWheelSmokeError(
                f"expected 8 release security controls, got {len(controls)}"
            )
        trivy_commands = [
            control.command for control in controls if control.identifier.startswith("container-")
        ]
        digest = "sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
        if len(trivy_commands) != 2 or any(
            not any(digest in argument for argument in command) for command in trivy_commands
        ):
            raise InstalledWheelSmokeError(
                "installed release security controls do not pin the Trivy OCI digest"
            )

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
