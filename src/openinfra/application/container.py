from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openinfra.application.access_policy_services import AccessPolicyService
from openinfra.application.async_processing_services import (
    AsyncProcessingService,
    ReportingWorker,
)
from openinfra.application.audit_services import AuditTrailService
from openinfra.application.authentication_services import (
    AuthProviderPolicyService,
    ExternalAuthenticationService,
)
from openinfra.application.certificate_pki_services import CertificatePkiService
from openinfra.application.dcim_services import (
    DcimCablingService,
    DcimEnvironmentService,
    DcimFieldOperationService,
    DcimLocationService,
    DcimRackService,
    DcimTopologyService,
    DcimVisualizationService,
)
from openinfra.application.dependency_graph_services import DependencyGraphService
from openinfra.application.discovery_services import DiscoveryCollectorService
from openinfra.application.edition_services import EditionQueryService, EditionRuntimeGuard
from openinfra.application.export_services import ExportService
from openinfra.application.external_itsm_services import ExternalItsmIntegrationService
from openinfra.application.field_operation_services import (
    FieldLocationResolver,
    FieldOperationService,
    FieldSafetyAssessmentService,
)
from openinfra.application.finops_services import FinOpsService
from openinfra.application.flow_matrix_services import FlowMatrixService
from openinfra.application.greenops_services import GreenOpsService
from openinfra.application.identity_services import IdentityService
from openinfra.application.import_services import GenericImportService
from openinfra.application.ipam_services import (
    IpamAllocationService,
    IpamConflictService,
    IpamDdiService,
    IpamModelService,
    IpamUiService,
)
from openinfra.application.it_resources_management_quality_services import (
    ITResourcesManagementQualityService,
)
from openinfra.application.itam_services import ItamSupportService
from openinfra.application.multisite_services import MultisiteService
from openinfra.application.network_config_compliance_services import NetworkConfigComplianceService
from openinfra.application.ports import (
    AccessPolicyRepository,
    ArtifactStore,
    AsyncProcessingRepository,
    AuditRepository,
    CertificateInventoryRepository,
    DcimRepository,
    DiscoveryRepository,
    ExportRepository,
    FieldOperationRepository,
    FinOpsRepository,
    FlowMatrixRepository,
    GreenOpsRepository,
    IdentityRepository,
    ImportRepository,
    IpamRepository,
    ItamSupportRepository,
    MultisiteRepository,
    NetworkConfigComplianceRepository,
    RagRepository,
    ReadinessProbe,
    RuntimeTelemetry,
    RuntimeUsageRepository,
    SbomRepository,
    SchemaStatusProvider,
    SecurityRepository,
    SimulationRepository,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.rag_services import RagService
from openinfra.application.sbom_services import SbomService
from openinfra.application.search_services import GlobalSearchService
from openinfra.application.security_services import SecurityService
from openinfra.application.simulation_services import (
    SimulationImpactEngine,
    SimulationService,
)
from openinfra.application.source_governance_services import SourceGovernanceService
from openinfra.application.source_of_truth_services import SourceOfTruthService
from openinfra.application.specialized_worker_services import (
    GraphWorker,
    ImportWorker,
    RagWorker,
)
from openinfra.application.telemetry import NullRuntimeTelemetry
from openinfra.infrastructure.async_processing import (
    JsonAsyncProcessingRepository,
    LocalArtifactStore,
    S3ArtifactStore,
)
from openinfra.infrastructure.certificate_parser import CryptographyCertificateParser
from openinfra.infrastructure.cursor_pagination import CursorTokenCodec
from openinfra.infrastructure.ddi_connectors import DdiConnectorFactory
from openinfra.infrastructure.external_identity import LdapIpaDirectoryAuthenticator
from openinfra.infrastructure.import_parsers import ImportDatasetParser
from openinfra.infrastructure.json_store import (
    JsonAccessPolicyRepository,
    JsonAuditRepository,
    JsonCertificateInventoryRepository,
    JsonDcimRepository,
    JsonDiscoveryRepository,
    JsonDocumentStore,
    JsonExportRepository,
    JsonFieldOperationRepository,
    JsonFinOpsRepository,
    JsonFlowMatrixRepository,
    JsonGreenOpsRepository,
    JsonIdentityRepository,
    JsonImportRepository,
    JsonIpamRepository,
    JsonItamSupportRepository,
    JsonMultisiteRepository,
    JsonNetworkConfigComplianceRepository,
    JsonRagRepository,
    JsonReadinessProbe,
    JsonRuntimeUsageRepository,
    JsonSbomRepository,
    JsonSchemaStatusProvider,
    JsonSecurityRepository,
    JsonSimulationRepository,
    JsonSourceGovernanceRepository,
    JsonSourceOfTruthRepository,
    JsonTransactionManager,
    SeedDataFactory,
)
from openinfra.infrastructure.multisite_observability import MultisiteOperationalMetricsProvider
from openinfra.infrastructure.observability import OpenInfraTelemetry
from openinfra.infrastructure.postgresql import (
    PostgreSQLAccessPolicyRepository,
    PostgreSQLAsyncProcessingRepository,
    PostgreSQLAuditRepository,
    PostgreSQLCertificateInventoryRepository,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLConnectionPoolSettings,
    PostgreSQLDcimRepository,
    PostgreSQLDiscoveryRepository,
    PostgreSQLExportRepository,
    PostgreSQLFieldOperationRepository,
    PostgreSQLFinOpsRepository,
    PostgreSQLFlowMatrixRepository,
    PostgreSQLGreenOpsRepository,
    PostgreSQLIdentityRepository,
    PostgreSQLImportRepository,
    PostgreSQLIpamRepository,
    PostgreSQLItamSupportRepository,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLMultisiteRepository,
    PostgreSQLNetworkConfigComplianceRepository,
    PostgreSQLRagRepository,
    PostgreSQLReadinessProbe,
    PostgreSQLRuntimeUsageRepository,
    PostgreSQLSbomRepository,
    PostgreSQLSecurityRepository,
    PostgreSQLSessionRegistry,
    PostgreSQLSimulationRepository,
    PostgreSQLSourceGovernanceRepository,
    PostgreSQLSourceOfTruthRepository,
    PostgreSQLTransactionManager,
)
from openinfra.infrastructure.rag_generator import DeterministicRagGenerator
from openinfra.infrastructure.read_routing import PostgreSQLReadRoutingSettings
from openinfra.infrastructure.runtime_config import RuntimeDatabaseDsnResolver
from openinfra.infrastructure.sbom_parser import SbomPayloadParser


@dataclass(frozen=True, slots=True)
class OpenInfraApplication:
    store: Any
    telemetry: RuntimeTelemetry
    async_processing_service: AsyncProcessingService
    async_processing_repository: AsyncProcessingRepository
    artifact_store: ArtifactStore
    reporting_worker: ReportingWorker
    import_worker: ImportWorker
    graph_worker: GraphWorker
    rag_worker: RagWorker
    dcim_service: DcimLocationService
    dcim_topology_service: DcimTopologyService
    dcim_rack_service: DcimRackService
    dcim_field_operation_service: DcimFieldOperationService
    dcim_visualization_service: DcimVisualizationService
    dcim_cabling_service: DcimCablingService
    dcim_environment_service: DcimEnvironmentService
    ipam_service: IpamAllocationService
    ipam_model_service: IpamModelService
    ipam_conflict_service: IpamConflictService
    ipam_ui_service: IpamUiService
    ipam_ddi_service: IpamDdiService
    import_service: GenericImportService
    export_service: ExportService
    discovery_service: DiscoveryCollectorService
    dependency_graph_service: DependencyGraphService
    field_operation_service: FieldOperationService
    simulation_service: SimulationService
    finops_service: FinOpsService
    greenops_service: GreenOpsService
    sbom_service: SbomService
    rag_service: RagService
    multisite_service: MultisiteService
    flow_matrix_service: FlowMatrixService
    certificate_pki_service: CertificatePkiService
    network_config_compliance_service: NetworkConfigComplianceService
    dcim_repository: DcimRepository
    ipam_repository: IpamRepository
    itam_support_repository: ItamSupportRepository
    import_repository: ImportRepository
    export_repository: ExportRepository
    discovery_repository: DiscoveryRepository
    field_operation_repository: FieldOperationRepository
    simulation_repository: SimulationRepository
    finops_repository: FinOpsRepository
    greenops_repository: GreenOpsRepository
    sbom_repository: SbomRepository
    rag_repository: RagRepository
    multisite_repository: MultisiteRepository
    flow_matrix_repository: FlowMatrixRepository
    certificate_inventory_repository: CertificateInventoryRepository
    network_config_compliance_repository: NetworkConfigComplianceRepository
    security_service: SecurityService
    identity_service: IdentityService
    external_authentication_service: ExternalAuthenticationService
    external_itsm_service: ExternalItsmIntegrationService
    auth_provider_policy_service: AuthProviderPolicyService
    access_policy_service: AccessPolicyService
    audit_service: AuditTrailService
    global_search_service: GlobalSearchService
    itam_support_service: ItamSupportService
    source_of_truth_service: SourceOfTruthService
    source_governance_service: SourceGovernanceService
    it_resources_management_quality_service: ITResourcesManagementQualityService
    identity_repository: IdentityRepository
    security_repository: SecurityRepository
    access_policy_repository: AccessPolicyRepository
    audit_repository: AuditRepository
    source_of_truth_repository: SourceOfTruthRepository
    source_governance_repository: SourceGovernanceRepository
    transaction_manager: TransactionManager
    readiness_probe: ReadinessProbe
    schema_status_provider: SchemaStatusProvider
    edition_guard: EditionRuntimeGuard
    edition_query_service: EditionQueryService
    runtime_usage_repository: RuntimeUsageRepository

    @property
    def it_resources_management_service(self) -> SourceOfTruthService:
        return self.source_of_truth_service

    @property
    def ressources_inventory_quality_service(self) -> ITResourcesManagementQualityService:
        return self.it_resources_management_quality_service


class ApplicationFactory:
    def create_json_application(
        self,
        data_path: Path,
        seed: bool = True,
        edition: str = "enterprise",
    ) -> OpenInfraApplication:
        store = JsonDocumentStore(data_path)
        transaction_manager = JsonTransactionManager(store)
        dcim_repository = JsonDcimRepository(store)
        ipam_repository = JsonIpamRepository(store)
        audit_repository = JsonAuditRepository(store)
        security_repository = JsonSecurityRepository(store)
        identity_repository = JsonIdentityRepository(store)
        access_policy_repository = JsonAccessPolicyRepository(store)
        source_of_truth_repository = JsonSourceOfTruthRepository(store)
        source_governance_repository = JsonSourceGovernanceRepository(store)
        import_repository = JsonImportRepository(store)
        export_repository = JsonExportRepository(store)
        field_operation_repository = JsonFieldOperationRepository(store)
        simulation_repository = JsonSimulationRepository(store)
        finops_repository = JsonFinOpsRepository(store)
        greenops_repository = JsonGreenOpsRepository(store)
        sbom_repository = JsonSbomRepository(store)
        rag_repository = JsonRagRepository(store)
        multisite_repository = JsonMultisiteRepository(store)
        flow_matrix_repository = JsonFlowMatrixRepository(store)
        certificate_inventory_repository = JsonCertificateInventoryRepository(store)
        network_config_compliance_repository = JsonNetworkConfigComplianceRepository(store)
        discovery_repository = JsonDiscoveryRepository(store)
        itam_support_repository = JsonItamSupportRepository(store)
        readiness_probe = JsonReadinessProbe(store)
        schema_status_provider = JsonSchemaStatusProvider()
        runtime_usage_repository = JsonRuntimeUsageRepository(store)
        async_processing_repository = JsonAsyncProcessingRepository(store)
        multisite_metrics_provider = MultisiteOperationalMetricsProvider.from_environment(
            multisite_repository,
            discovery_repository,
        )
        telemetry = OpenInfraTelemetry.from_environment(
            service_name="openinfra-api",
            edition=edition,
            queue_metrics_provider=async_processing_repository.operational_metrics,
            multisite_metrics_provider=multisite_metrics_provider,
        )
        artifact_store = self._create_artifact_store(
            Path(
                os.environ.get(
                    "OPENINFRA_ARTIFACT_ROOT",
                    str(data_path.parent / f"{data_path.name}.artifacts"),
                )
            )
        )
        if seed:
            SeedDataFactory(
                dcim_repository,
                transaction_manager,
            ).ensure_minimal_datacenter("default")
        return self._build_application(
            store=store,
            dcim_repository=dcim_repository,
            ipam_repository=ipam_repository,
            itam_support_repository=itam_support_repository,
            audit_repository=audit_repository,
            security_repository=security_repository,
            identity_repository=identity_repository,
            access_policy_repository=access_policy_repository,
            source_of_truth_repository=source_of_truth_repository,
            source_governance_repository=source_governance_repository,
            import_repository=import_repository,
            export_repository=export_repository,
            discovery_repository=discovery_repository,
            field_operation_repository=field_operation_repository,
            simulation_repository=simulation_repository,
            finops_repository=finops_repository,
            greenops_repository=greenops_repository,
            sbom_repository=sbom_repository,
            rag_repository=rag_repository,
            multisite_repository=multisite_repository,
            flow_matrix_repository=flow_matrix_repository,
            certificate_inventory_repository=certificate_inventory_repository,
            network_config_compliance_repository=network_config_compliance_repository,
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
            runtime_usage_repository=runtime_usage_repository,
            async_processing_repository=async_processing_repository,
            artifact_store=artifact_store,
            telemetry=telemetry,
            edition=edition,
        )

    def create_postgresql_application(
        self,
        dsn: str,
        seed: bool = False,
        profile: PostgreSQLClusterProfile | None = None,
        edition: str = "enterprise",
        pool_settings: PostgreSQLConnectionPoolSettings | None = None,
        read_dsn: str = "",
        read_pool_settings: PostgreSQLConnectionPoolSettings | None = None,
        read_routing_settings: PostgreSQLReadRoutingSettings | None = None,
        cursor_signing_secret: str | None = None,
    ) -> OpenInfraApplication:
        connection_factory = PostgreSQLConnectionFactory(
            dsn,
            profile=profile,
            pool_settings=pool_settings,
        )
        normalized_read_dsn = read_dsn.strip()
        read_factory = (
            PostgreSQLConnectionFactory(
                normalized_read_dsn,
                profile=profile,
                pool_settings=read_pool_settings or pool_settings,
            )
            if normalized_read_dsn
            else None
        )
        registry = PostgreSQLSessionRegistry(
            connection_factory,
            read_factory=read_factory,
            read_routing_settings=read_routing_settings,
        )
        resolved_cursor_secret = RuntimeDatabaseDsnResolver().resolve_cursor_signing_secret(
            cursor_signing_secret
        )
        cursor_codec = CursorTokenCodec(resolved_cursor_secret) if resolved_cursor_secret else None
        transaction_manager = PostgreSQLTransactionManager(registry)
        dcim_repository = PostgreSQLDcimRepository(registry, cursor_codec)
        ipam_repository = PostgreSQLIpamRepository(registry, cursor_codec)
        audit_repository = PostgreSQLAuditRepository(registry, cursor_codec)
        security_repository = PostgreSQLSecurityRepository(registry, cursor_codec)
        identity_repository = PostgreSQLIdentityRepository(registry, cursor_codec)
        access_policy_repository = PostgreSQLAccessPolicyRepository(registry, cursor_codec)
        source_of_truth_repository = PostgreSQLSourceOfTruthRepository(registry, cursor_codec)
        source_governance_repository = PostgreSQLSourceGovernanceRepository(registry, cursor_codec)
        import_repository = PostgreSQLImportRepository(registry, cursor_codec)
        export_repository = PostgreSQLExportRepository(registry, cursor_codec)
        field_operation_repository = PostgreSQLFieldOperationRepository(registry, cursor_codec)
        simulation_repository = PostgreSQLSimulationRepository(registry, cursor_codec)
        finops_repository = PostgreSQLFinOpsRepository(registry, cursor_codec)
        greenops_repository = PostgreSQLGreenOpsRepository(registry, cursor_codec)
        sbom_repository = PostgreSQLSbomRepository(registry, cursor_codec)
        rag_repository = PostgreSQLRagRepository(registry, cursor_codec)
        multisite_repository = PostgreSQLMultisiteRepository(registry, cursor_codec)
        flow_matrix_repository = PostgreSQLFlowMatrixRepository(registry, cursor_codec)
        certificate_inventory_repository = PostgreSQLCertificateInventoryRepository(
            registry, cursor_codec
        )
        network_config_compliance_repository = PostgreSQLNetworkConfigComplianceRepository(
            registry, cursor_codec
        )
        discovery_repository = PostgreSQLDiscoveryRepository(registry, cursor_codec)
        itam_support_repository = PostgreSQLItamSupportRepository(registry, cursor_codec)
        migration_catalog = PostgreSQLMigrationCatalog.from_project_root()
        readiness_probe = PostgreSQLReadinessProbe(registry, migration_catalog)
        schema_status_provider = PostgreSQLMigrationExecutor(registry, migration_catalog)
        runtime_usage_repository = PostgreSQLRuntimeUsageRepository(registry, cursor_codec)
        async_processing_repository = PostgreSQLAsyncProcessingRepository(registry, cursor_codec)

        def queue_metrics_provider() -> dict[str, object]:
            with registry.read_scope():
                return async_processing_repository.operational_metrics()

        raw_multisite_metrics_provider = MultisiteOperationalMetricsProvider.from_environment(
            multisite_repository,
            discovery_repository,
        )

        def multisite_metrics_provider() -> dict[str, object]:
            with registry.read_scope():
                return raw_multisite_metrics_provider()

        telemetry = OpenInfraTelemetry.from_environment(
            service_name="openinfra-api",
            edition=edition,
            queue_metrics_provider=queue_metrics_provider,
            runtime_metrics_provider=registry.operational_metrics,
            multisite_metrics_provider=multisite_metrics_provider,
        )
        artifact_store = self._create_artifact_store(
            Path(os.environ.get("OPENINFRA_ARTIFACT_ROOT", "/data/openinfra/artifacts"))
        )
        if seed:
            SeedDataFactory(
                dcim_repository,
                transaction_manager,
            ).ensure_minimal_datacenter("default")
        return self._build_application(
            store=registry,
            dcim_repository=dcim_repository,
            ipam_repository=ipam_repository,
            audit_repository=audit_repository,
            security_repository=security_repository,
            identity_repository=identity_repository,
            access_policy_repository=access_policy_repository,
            source_of_truth_repository=source_of_truth_repository,
            source_governance_repository=source_governance_repository,
            import_repository=import_repository,
            export_repository=export_repository,
            discovery_repository=discovery_repository,
            field_operation_repository=field_operation_repository,
            simulation_repository=simulation_repository,
            finops_repository=finops_repository,
            greenops_repository=greenops_repository,
            sbom_repository=sbom_repository,
            rag_repository=rag_repository,
            multisite_repository=multisite_repository,
            flow_matrix_repository=flow_matrix_repository,
            certificate_inventory_repository=certificate_inventory_repository,
            network_config_compliance_repository=network_config_compliance_repository,
            itam_support_repository=itam_support_repository,
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
            runtime_usage_repository=runtime_usage_repository,
            async_processing_repository=async_processing_repository,
            artifact_store=artifact_store,
            telemetry=telemetry,
            edition=edition,
        )

    @staticmethod
    def _create_artifact_store(default_root: Path) -> ArtifactStore:
        backend = os.environ.get("OPENINFRA_ASYNC_ARTIFACT_BACKEND", "filesystem").strip().lower()
        if backend == "filesystem":
            return LocalArtifactStore(default_root)
        if backend != "s3":
            raise ValueError("OPENINFRA_ASYNC_ARTIFACT_BACKEND must be filesystem or s3")

        required_names = (
            "OPENINFRA_S3_ENDPOINT",
            "OPENINFRA_S3_BUCKET",
            "OPENINFRA_S3_REGION",
            "OPENINFRA_S3_ACCESS_KEY",
            "OPENINFRA_S3_SECRET_KEY",
        )
        values = {name: os.environ.get(name, "").strip() for name in required_names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError("missing S3 artifact configuration: " + ", ".join(missing))
        verify_value = os.environ.get("OPENINFRA_S3_VERIFY_TLS", "true").strip().lower()
        if verify_value not in {"true", "false"}:
            raise ValueError("OPENINFRA_S3_VERIFY_TLS must be true or false")
        timeout_value = os.environ.get("OPENINFRA_S3_TIMEOUT_SECONDS", "30").strip()
        try:
            timeout_seconds = float(timeout_value)
        except ValueError as exc:
            raise ValueError("OPENINFRA_S3_TIMEOUT_SECONDS must be numeric") from exc
        return S3ArtifactStore(
            endpoint=values["OPENINFRA_S3_ENDPOINT"],
            bucket=values["OPENINFRA_S3_BUCKET"],
            region=values["OPENINFRA_S3_REGION"],
            access_key=values["OPENINFRA_S3_ACCESS_KEY"],
            secret_key=values["OPENINFRA_S3_SECRET_KEY"],
            session_token=os.environ.get("OPENINFRA_S3_SESSION_TOKEN") or None,
            verify_tls=verify_value == "true",
            timeout_seconds=timeout_seconds,
        )

    def _build_application(
        self,
        store: Any,
        dcim_repository: DcimRepository,
        ipam_repository: IpamRepository,
        audit_repository: AuditRepository,
        security_repository: SecurityRepository,
        identity_repository: IdentityRepository,
        access_policy_repository: AccessPolicyRepository,
        transaction_manager: TransactionManager,
        readiness_probe: ReadinessProbe,
        schema_status_provider: SchemaStatusProvider,
        runtime_usage_repository: RuntimeUsageRepository | None = None,
        async_processing_repository: AsyncProcessingRepository | None = None,
        artifact_store: ArtifactStore | None = None,
        telemetry: RuntimeTelemetry | None = None,
        edition: str = "enterprise",
        source_of_truth_repository: SourceOfTruthRepository | None = None,
        source_governance_repository: SourceGovernanceRepository | None = None,
        import_repository: ImportRepository | None = None,
        export_repository: ExportRepository | None = None,
        discovery_repository: DiscoveryRepository | None = None,
        field_operation_repository: FieldOperationRepository | None = None,
        simulation_repository: SimulationRepository | None = None,
        finops_repository: FinOpsRepository | None = None,
        greenops_repository: GreenOpsRepository | None = None,
        sbom_repository: SbomRepository | None = None,
        rag_repository: RagRepository | None = None,
        multisite_repository: MultisiteRepository | None = None,
        flow_matrix_repository: FlowMatrixRepository | None = None,
        certificate_inventory_repository: CertificateInventoryRepository | None = None,
        network_config_compliance_repository: NetworkConfigComplianceRepository | None = None,
        itam_support_repository: ItamSupportRepository | None = None,
    ) -> OpenInfraApplication:
        if source_of_truth_repository is None:
            if hasattr(store, "data"):
                source_of_truth_repository = JsonSourceOfTruthRepository(store)
            else:
                source_of_truth_repository = PostgreSQLSourceOfTruthRepository(store)
        if source_governance_repository is None:
            if hasattr(store, "data"):
                source_governance_repository = JsonSourceGovernanceRepository(store)
            else:
                source_governance_repository = PostgreSQLSourceGovernanceRepository(store)
        if import_repository is None:
            if hasattr(store, "data"):
                import_repository = JsonImportRepository(store)
            else:
                import_repository = PostgreSQLImportRepository(store)
        if export_repository is None:
            if hasattr(store, "data"):
                export_repository = JsonExportRepository(store)
            else:
                export_repository = PostgreSQLExportRepository(store)
        if discovery_repository is None:
            if hasattr(store, "data"):
                discovery_repository = JsonDiscoveryRepository(store)
            else:
                discovery_repository = PostgreSQLDiscoveryRepository(store)
        if field_operation_repository is None:
            if hasattr(store, "data"):
                field_operation_repository = JsonFieldOperationRepository(store)
            else:
                field_operation_repository = PostgreSQLFieldOperationRepository(store)
        if simulation_repository is None:
            if hasattr(store, "data"):
                simulation_repository = JsonSimulationRepository(store)
            else:
                simulation_repository = PostgreSQLSimulationRepository(store)
        if finops_repository is None:
            if hasattr(store, "data"):
                finops_repository = JsonFinOpsRepository(store)
            else:
                finops_repository = PostgreSQLFinOpsRepository(store)
        if greenops_repository is None:
            if hasattr(store, "data"):
                greenops_repository = JsonGreenOpsRepository(store)
            else:
                greenops_repository = PostgreSQLGreenOpsRepository(store)
        if sbom_repository is None:
            if hasattr(store, "data"):
                sbom_repository = JsonSbomRepository(store)
            else:
                sbom_repository = PostgreSQLSbomRepository(store)
        if rag_repository is None:
            if hasattr(store, "data"):
                rag_repository = JsonRagRepository(store)
            else:
                rag_repository = PostgreSQLRagRepository(store)
        if multisite_repository is None:
            if hasattr(store, "data"):
                multisite_repository = JsonMultisiteRepository(store)
            else:
                multisite_repository = PostgreSQLMultisiteRepository(store)
        if flow_matrix_repository is None:
            if hasattr(store, "data"):
                flow_matrix_repository = JsonFlowMatrixRepository(store)
            else:
                flow_matrix_repository = PostgreSQLFlowMatrixRepository(store)
        if certificate_inventory_repository is None:
            if hasattr(store, "data"):
                certificate_inventory_repository = JsonCertificateInventoryRepository(store)
            else:
                certificate_inventory_repository = PostgreSQLCertificateInventoryRepository(store)
        if network_config_compliance_repository is None:
            if hasattr(store, "data"):
                network_config_compliance_repository = JsonNetworkConfigComplianceRepository(store)
            else:
                network_config_compliance_repository = PostgreSQLNetworkConfigComplianceRepository(
                    store
                )
        if itam_support_repository is None:
            if hasattr(store, "data"):
                itam_support_repository = JsonItamSupportRepository(store)
            else:
                itam_support_repository = PostgreSQLItamSupportRepository(store)
        if runtime_usage_repository is None:
            if hasattr(store, "data"):
                runtime_usage_repository = JsonRuntimeUsageRepository(store)
            else:
                runtime_usage_repository = PostgreSQLRuntimeUsageRepository(store)
        if async_processing_repository is None:
            if hasattr(store, "data"):
                async_processing_repository = JsonAsyncProcessingRepository(store)
            else:
                async_processing_repository = PostgreSQLAsyncProcessingRepository(store)
        if artifact_store is None:
            artifact_store = self._create_artifact_store(
                Path(os.environ.get("OPENINFRA_ARTIFACT_ROOT", "/data/openinfra/artifacts"))
            )
        security_service = SecurityService(
            security_repository,
            audit_repository,
            transaction_manager,
            identity_repository,
        )
        auth_provider_policy_service = AuthProviderPolicyService()
        edition_guard = EditionRuntimeGuard(
            edition,
            runtime_usage_repository,
            audit_repository,
            transaction_manager,
        )
        edition_query_service = EditionQueryService(runtime_usage_repository)
        ipam_allocation_service = IpamAllocationService(
            ipam_repository,
            audit_repository,
            transaction_manager,
            edition_guard=edition_guard,
        )
        ipam_conflict_service = IpamConflictService(
            ipam_repository,
            audit_repository,
            transaction_manager,
        )
        ipam_ddi_service = IpamDdiService(
            ipam_repository,
            audit_repository,
            transaction_manager,
            DdiConnectorFactory.default(),
        )
        import_service = GenericImportService(
            import_repository,
            source_of_truth_repository,
            audit_repository,
            transaction_manager,
            security_service,
            ImportDatasetParser(),
        )
        export_service = ExportService(
            export_repository,
            source_of_truth_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        discovery_service = DiscoveryCollectorService(
            discovery_repository,
            audit_repository,
            transaction_manager,
            security_service,
            edition_guard,
        )
        source_of_truth_service = SourceOfTruthService(
            source_of_truth_repository,
            audit_repository,
            transaction_manager,
            security_service,
            source_governance_repository,
        )
        dependency_graph_service = DependencyGraphService(
            source_of_truth_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        flow_matrix_service = FlowMatrixService(
            flow_matrix_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        certificate_pki_service = CertificatePkiService(
            certificate_inventory_repository,
            CryptographyCertificateParser(),
            audit_repository,
            transaction_manager,
            security_service,
        )
        network_config_compliance_service = NetworkConfigComplianceService(
            network_config_compliance_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        ipam_ui_service = IpamUiService(
            ipam_repository,
            audit_repository,
            transaction_manager,
            ipam_allocation_service,
            ipam_conflict_service,
        )
        identity_service = IdentityService(
            identity_repository,
            audit_repository,
            transaction_manager,
            security_service,
            edition_guard,
        )
        external_authentication_service = ExternalAuthenticationService(
            LdapIpaDirectoryAuthenticator(),
            identity_service,
            security_service,
            audit_repository,
            transaction_manager,
            auth_provider_policy_service,
        )
        itam_support_service = ItamSupportService(
            itam_support_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        access_policy_service = AccessPolicyService(
            access_policy_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        field_operation_service = FieldOperationService(
            field_operation_repository,
            audit_repository,
            transaction_manager,
            security_service,
            access_policy_service,
            FieldLocationResolver(dcim_repository, certificate_inventory_repository),
            FieldSafetyAssessmentService(
                dependency_graph_service, flow_matrix_repository, dcim_repository
            ),
        )
        simulation_service = SimulationService(
            simulation_repository,
            audit_repository,
            transaction_manager,
            security_service,
            SimulationImpactEngine(
                source_of_truth_repository,
                flow_matrix_repository,
                dependency_graph_service,
            ),
        )
        finops_service = FinOpsService(
            finops_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        greenops_service = GreenOpsService(
            greenops_repository,
            audit_repository,
            transaction_manager,
            security_service,
        )
        sbom_service = SbomService(
            sbom_repository,
            audit_repository,
            transaction_manager,
            security_service,
            SbomPayloadParser(),
        )
        rag_service = RagService(
            rag_repository,
            audit_repository,
            transaction_manager,
            security_service,
            source_of_truth_service,
            DeterministicRagGenerator(),
        )
        multisite_service = MultisiteService(
            multisite_repository,
            dcim_repository,
            audit_repository,
            transaction_manager,
            security_service,
            edition_guard,
            discovery_repository,
            discovery_service,
        )
        runtime_telemetry = telemetry or NullRuntimeTelemetry()
        async_processing_service = AsyncProcessingService(
            async_processing_repository,
            artifact_store,
            audit_repository,
            transaction_manager,
            security_service,
        )
        reporting_worker = ReportingWorker(async_processing_service, runtime_telemetry)
        import_worker = ImportWorker(
            async_processing_service, import_service, artifact_store, runtime_telemetry
        )
        graph_worker = GraphWorker(
            async_processing_service, dependency_graph_service, runtime_telemetry
        )
        rag_worker = RagWorker(
            async_processing_service, rag_service, artifact_store, runtime_telemetry
        )
        return OpenInfraApplication(
            store=store,
            telemetry=runtime_telemetry,
            async_processing_service=async_processing_service,
            async_processing_repository=async_processing_repository,
            artifact_store=artifact_store,
            reporting_worker=reporting_worker,
            import_worker=import_worker,
            graph_worker=graph_worker,
            rag_worker=rag_worker,
            dcim_service=DcimLocationService(
                dcim_repository,
                audit_repository,
                transaction_manager,
                edition_guard,
            ),
            dcim_topology_service=DcimTopologyService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            dcim_rack_service=DcimRackService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            dcim_field_operation_service=DcimFieldOperationService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            dcim_visualization_service=DcimVisualizationService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            dcim_cabling_service=DcimCablingService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            dcim_environment_service=DcimEnvironmentService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            ipam_service=ipam_allocation_service,
            ipam_model_service=IpamModelService(
                ipam_repository,
                audit_repository,
                transaction_manager,
                edition_guard,
            ),
            ipam_conflict_service=ipam_conflict_service,
            ipam_ddi_service=ipam_ddi_service,
            import_service=import_service,
            export_service=export_service,
            discovery_service=discovery_service,
            dependency_graph_service=dependency_graph_service,
            field_operation_service=field_operation_service,
            simulation_service=simulation_service,
            finops_service=finops_service,
            greenops_service=greenops_service,
            sbom_service=sbom_service,
            rag_service=rag_service,
            multisite_service=multisite_service,
            flow_matrix_service=flow_matrix_service,
            certificate_pki_service=certificate_pki_service,
            network_config_compliance_service=network_config_compliance_service,
            ipam_ui_service=ipam_ui_service,
            security_service=security_service,
            identity_service=identity_service,
            external_authentication_service=external_authentication_service,
            external_itsm_service=ExternalItsmIntegrationService(),
            auth_provider_policy_service=auth_provider_policy_service,
            source_of_truth_service=source_of_truth_service,
            source_governance_service=SourceGovernanceService(
                source_governance_repository,
                audit_repository,
                transaction_manager,
                security_service,
            ),
            it_resources_management_quality_service=ITResourcesManagementQualityService(
                source_of_truth_repository,
                source_governance_repository,
                audit_repository,
                transaction_manager,
                security_service,
            ),
            access_policy_service=access_policy_service,
            audit_service=AuditTrailService(
                audit_repository,
                transaction_manager,
                security_service,
            ),
            global_search_service=GlobalSearchService(
                source_of_truth_service,
                ipam_ui_service,
                discovery_service,
                itam_support_service,
                audit_repository,
                transaction_manager,
            ),
            itam_support_service=itam_support_service,
            dcim_repository=dcim_repository,
            identity_repository=identity_repository,
            ipam_repository=ipam_repository,
            itam_support_repository=itam_support_repository,
            import_repository=import_repository,
            export_repository=export_repository,
            discovery_repository=discovery_repository,
            field_operation_repository=field_operation_repository,
            simulation_repository=simulation_repository,
            finops_repository=finops_repository,
            greenops_repository=greenops_repository,
            sbom_repository=sbom_repository,
            rag_repository=rag_repository,
            multisite_repository=multisite_repository,
            flow_matrix_repository=flow_matrix_repository,
            certificate_inventory_repository=certificate_inventory_repository,
            network_config_compliance_repository=network_config_compliance_repository,
            security_repository=security_repository,
            access_policy_repository=access_policy_repository,
            source_of_truth_repository=source_of_truth_repository,
            source_governance_repository=source_governance_repository,
            audit_repository=audit_repository,
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
            edition_guard=edition_guard,
            edition_query_service=edition_query_service,
            runtime_usage_repository=runtime_usage_repository,
        )
