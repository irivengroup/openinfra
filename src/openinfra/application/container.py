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
from openinfra.application.dcim_services import (
    DcimCablingService,
    DcimEnvironmentService,
    DcimFieldOperationService,
    DcimLocationService,
    DcimRackService,
    DcimTopologyService,
    DcimVisualizationService,
)
from openinfra.application.discovery_services import DiscoveryCollectorService
from openinfra.application.edition_services import EditionQueryService, EditionRuntimeGuard
from openinfra.application.export_services import ExportService
from openinfra.application.identity_services import IdentityService
from openinfra.application.import_services import GenericImportService
from openinfra.application.ipam_services import (
    IpamAllocationService,
    IpamConflictService,
    IpamDdiService,
    IpamModelService,
    IpamUiService,
)
from openinfra.application.ports import (
    AccessPolicyRepository,
    AuditRepository,
    DcimRepository,
    DiscoveryRepository,
    ExportRepository,
    IdentityRepository,
    ImportRepository,
    IpamRepository,
    ReadinessProbe,
    RuntimeUsageRepository,
    SchemaStatusProvider,
    SecurityRepository,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import SecurityService
from openinfra.application.source_governance_services import SourceGovernanceService
from openinfra.application.source_of_truth_services import SourceOfTruthService
from openinfra.infrastructure.ddi_connectors import DdiConnectorFactory
from openinfra.infrastructure.external_identity import LdapIpaDirectoryAuthenticator
from openinfra.infrastructure.import_parsers import ImportDatasetParser
from openinfra.infrastructure.json_store import (
    JsonAccessPolicyRepository,
    JsonAuditRepository,
    JsonDcimRepository,
    JsonDiscoveryRepository,
    JsonDocumentStore,
    JsonExportRepository,
    JsonIdentityRepository,
    JsonImportRepository,
    JsonIpamRepository,
    JsonReadinessProbe,
    JsonRuntimeUsageRepository,
    JsonSchemaStatusProvider,
    JsonSecurityRepository,
    JsonSourceGovernanceRepository,
    JsonSourceOfTruthRepository,
    JsonTransactionManager,
    SeedDataFactory,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLAccessPolicyRepository,
    PostgreSQLAuditRepository,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLDcimRepository,
    PostgreSQLDiscoveryRepository,
    PostgreSQLExportRepository,
    PostgreSQLIdentityRepository,
    PostgreSQLImportRepository,
    PostgreSQLIpamRepository,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLReadinessProbe,
    PostgreSQLRuntimeUsageRepository,
    PostgreSQLSecurityRepository,
    PostgreSQLSessionRegistry,
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
    dcim_repository: DcimRepository
    ipam_repository: IpamRepository
    import_repository: ImportRepository
    export_repository: ExportRepository
    discovery_repository: DiscoveryRepository
    security_service: SecurityService
    identity_service: IdentityService
    external_authentication_service: ExternalAuthenticationService
    auth_provider_policy_service: AuthProviderPolicyService
    access_policy_service: AccessPolicyService
    audit_service: AuditTrailService
    source_of_truth_service: SourceOfTruthService
    source_governance_service: SourceGovernanceService
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
        discovery_repository = JsonDiscoveryRepository(store)
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
            audit_repository=audit_repository,
            security_repository=security_repository,
            identity_repository=identity_repository,
            access_policy_repository=access_policy_repository,
            source_of_truth_repository=source_of_truth_repository,
            source_governance_repository=source_governance_repository,
            import_repository=import_repository,
            export_repository=export_repository,
            discovery_repository=discovery_repository,
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
        discovery_repository = PostgreSQLDiscoveryRepository(registry)
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
            ipam_ui_service=IpamUiService(
                ipam_repository,
                audit_repository,
                transaction_manager,
                ipam_allocation_service,
                ipam_conflict_service,
            ),
            security_service=security_service,
            identity_service=identity_service,
            external_authentication_service=external_authentication_service,
            auth_provider_policy_service=auth_provider_policy_service,
            source_of_truth_service=SourceOfTruthService(
                source_of_truth_repository,
                audit_repository,
                transaction_manager,
                security_service,
                source_governance_repository,
            ),
            source_governance_service=SourceGovernanceService(
                source_governance_repository,
                audit_repository,
                transaction_manager,
                security_service,
            ),
            access_policy_service=AccessPolicyService(
                access_policy_repository,
                audit_repository,
                transaction_manager,
                security_service,
            ),
            audit_service=AuditTrailService(
                audit_repository,
                transaction_manager,
                security_service,
            ),
            dcim_repository=dcim_repository,
            identity_repository=identity_repository,
            ipam_repository=ipam_repository,
            import_repository=import_repository,
            export_repository=export_repository,
            discovery_repository=discovery_repository,
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
