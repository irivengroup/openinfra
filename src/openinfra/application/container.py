from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openinfra.application.access_policy_services import AccessPolicyService
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
from openinfra.application.flow_matrix_services import FlowMatrixService
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
from openinfra.application.network_config_compliance_services import NetworkConfigComplianceService
from openinfra.application.ports import (
    AccessPolicyRepository,
    AuditRepository,
    CertificateInventoryRepository,
    DcimRepository,
    DiscoveryRepository,
    ExportRepository,
    FieldOperationRepository,
    FlowMatrixRepository,
    IdentityRepository,
    ImportRepository,
    IpamRepository,
    ItamSupportRepository,
    NetworkConfigComplianceRepository,
    ReadinessProbe,
    RuntimeUsageRepository,
    SchemaStatusProvider,
    SecurityRepository,
    SimulationRepository,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.search_services import GlobalSearchService
from openinfra.application.security_services import SecurityService
from openinfra.application.simulation_services import (
    SimulationImpactEngine,
    SimulationService,
)
from openinfra.application.source_governance_services import SourceGovernanceService
from openinfra.application.source_of_truth_services import SourceOfTruthService
from openinfra.infrastructure.certificate_parser import CryptographyCertificateParser
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
    JsonFlowMatrixRepository,
    JsonIdentityRepository,
    JsonImportRepository,
    JsonIpamRepository,
    JsonItamSupportRepository,
    JsonNetworkConfigComplianceRepository,
    JsonReadinessProbe,
    JsonRuntimeUsageRepository,
    JsonSchemaStatusProvider,
    JsonSecurityRepository,
    JsonSimulationRepository,
    JsonSourceGovernanceRepository,
    JsonSourceOfTruthRepository,
    JsonTransactionManager,
    SeedDataFactory,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLAccessPolicyRepository,
    PostgreSQLAuditRepository,
    PostgreSQLCertificateInventoryRepository,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLDcimRepository,
    PostgreSQLDiscoveryRepository,
    PostgreSQLExportRepository,
    PostgreSQLFieldOperationRepository,
    PostgreSQLFlowMatrixRepository,
    PostgreSQLIdentityRepository,
    PostgreSQLImportRepository,
    PostgreSQLIpamRepository,
    PostgreSQLItamSupportRepository,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLNetworkConfigComplianceRepository,
    PostgreSQLReadinessProbe,
    PostgreSQLRuntimeUsageRepository,
    PostgreSQLSecurityRepository,
    PostgreSQLSessionRegistry,
    PostgreSQLSimulationRepository,
    PostgreSQLSourceGovernanceRepository,
    PostgreSQLSourceOfTruthRepository,
    PostgreSQLTransactionManager,
)


@dataclass(frozen=True, slots=True)
class OpenInfraApplication:
    store: Any
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
        flow_matrix_repository = JsonFlowMatrixRepository(store)
        certificate_inventory_repository = JsonCertificateInventoryRepository(store)
        network_config_compliance_repository = JsonNetworkConfigComplianceRepository(store)
        discovery_repository = JsonDiscoveryRepository(store)
        itam_support_repository = JsonItamSupportRepository(store)
        readiness_probe = JsonReadinessProbe(store)
        schema_status_provider = JsonSchemaStatusProvider()
        runtime_usage_repository = JsonRuntimeUsageRepository(store)
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
            flow_matrix_repository=flow_matrix_repository,
            certificate_inventory_repository=certificate_inventory_repository,
            network_config_compliance_repository=network_config_compliance_repository,
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
            runtime_usage_repository=runtime_usage_repository,
            edition=edition,
        )

    def create_postgresql_application(
        self,
        dsn: str,
        seed: bool = False,
        profile: PostgreSQLClusterProfile | None = None,
        edition: str = "enterprise",
    ) -> OpenInfraApplication:
        connection_factory = PostgreSQLConnectionFactory(dsn, profile=profile)
        registry = PostgreSQLSessionRegistry(connection_factory)
        transaction_manager = PostgreSQLTransactionManager(registry)
        dcim_repository = PostgreSQLDcimRepository(registry)
        ipam_repository = PostgreSQLIpamRepository(registry)
        audit_repository = PostgreSQLAuditRepository(registry)
        security_repository = PostgreSQLSecurityRepository(registry)
        identity_repository = PostgreSQLIdentityRepository(registry)
        access_policy_repository = PostgreSQLAccessPolicyRepository(registry)
        source_of_truth_repository = PostgreSQLSourceOfTruthRepository(registry)
        source_governance_repository = PostgreSQLSourceGovernanceRepository(registry)
        import_repository = PostgreSQLImportRepository(registry)
        export_repository = PostgreSQLExportRepository(registry)
        field_operation_repository = PostgreSQLFieldOperationRepository(registry)
        simulation_repository = PostgreSQLSimulationRepository(registry)
        flow_matrix_repository = PostgreSQLFlowMatrixRepository(registry)
        certificate_inventory_repository = PostgreSQLCertificateInventoryRepository(registry)
        network_config_compliance_repository = PostgreSQLNetworkConfigComplianceRepository(registry)
        discovery_repository = PostgreSQLDiscoveryRepository(registry)
        itam_support_repository = PostgreSQLItamSupportRepository(registry)
        migration_catalog = PostgreSQLMigrationCatalog.from_project_root()
        readiness_probe = PostgreSQLReadinessProbe(registry, migration_catalog)
        schema_status_provider = PostgreSQLMigrationExecutor(registry, migration_catalog)
        runtime_usage_repository = PostgreSQLRuntimeUsageRepository(registry)
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
            flow_matrix_repository=flow_matrix_repository,
            certificate_inventory_repository=certificate_inventory_repository,
            network_config_compliance_repository=network_config_compliance_repository,
            itam_support_repository=itam_support_repository,
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
            runtime_usage_repository=runtime_usage_repository,
            edition=edition,
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
        edition: str = "enterprise",
        source_of_truth_repository: SourceOfTruthRepository | None = None,
        source_governance_repository: SourceGovernanceRepository | None = None,
        import_repository: ImportRepository | None = None,
        export_repository: ExportRepository | None = None,
        discovery_repository: DiscoveryRepository | None = None,
        field_operation_repository: FieldOperationRepository | None = None,
        simulation_repository: SimulationRepository | None = None,
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
        return OpenInfraApplication(
            store=store,
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
