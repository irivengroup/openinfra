from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openinfra.application.access_policy_services import AccessPolicyService
from openinfra.application.audit_services import AuditTrailService
from openinfra.application.dcim_services import DcimLocationService
from openinfra.application.identity_services import IdentityService
from openinfra.application.ipam_services import IpamAllocationService
from openinfra.application.ports import (
    AccessPolicyRepository,
    AuditRepository,
    DcimRepository,
    IdentityRepository,
    IpamRepository,
    ReadinessProbe,
    SchemaStatusProvider,
    SecurityRepository,
    TransactionManager,
)
from openinfra.application.security_services import SecurityService
from openinfra.infrastructure.json_store import (
    JsonAccessPolicyRepository,
    JsonAuditRepository,
    JsonDcimRepository,
    JsonDocumentStore,
    JsonIdentityRepository,
    JsonIpamRepository,
    JsonReadinessProbe,
    JsonSchemaStatusProvider,
    JsonSecurityRepository,
    JsonTransactionManager,
    SeedDataFactory,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLAccessPolicyRepository,
    PostgreSQLAuditRepository,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLDcimRepository,
    PostgreSQLIdentityRepository,
    PostgreSQLIpamRepository,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLReadinessProbe,
    PostgreSQLSecurityRepository,
    PostgreSQLSessionRegistry,
    PostgreSQLTransactionManager,
)


@dataclass(frozen=True, slots=True)
class OpenInfraApplication:
    store: Any
    dcim_service: DcimLocationService
    ipam_service: IpamAllocationService
    dcim_repository: DcimRepository
    ipam_repository: IpamRepository
    security_service: SecurityService
    identity_service: IdentityService
    access_policy_service: AccessPolicyService
    audit_service: AuditTrailService
    identity_repository: IdentityRepository
    security_repository: SecurityRepository
    access_policy_repository: AccessPolicyRepository
    audit_repository: AuditRepository
    transaction_manager: TransactionManager
    readiness_probe: ReadinessProbe
    schema_status_provider: SchemaStatusProvider


class ApplicationFactory:
    def create_json_application(self, data_path: Path, seed: bool = True) -> OpenInfraApplication:
        store = JsonDocumentStore(data_path)
        transaction_manager = JsonTransactionManager(store)
        dcim_repository = JsonDcimRepository(store)
        ipam_repository = JsonIpamRepository(store)
        audit_repository = JsonAuditRepository(store)
        security_repository = JsonSecurityRepository(store)
        identity_repository = JsonIdentityRepository(store)
        access_policy_repository = JsonAccessPolicyRepository(store)
        readiness_probe = JsonReadinessProbe(store)
        schema_status_provider = JsonSchemaStatusProvider()
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
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
        )

    def create_postgresql_application(
        self,
        dsn: str,
        seed: bool = False,
        profile: PostgreSQLClusterProfile | None = None,
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
        migration_catalog = PostgreSQLMigrationCatalog.from_project_root()
        readiness_probe = PostgreSQLReadinessProbe(registry, migration_catalog)
        schema_status_provider = PostgreSQLMigrationExecutor(registry, migration_catalog)
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
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
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
    ) -> OpenInfraApplication:
        security_service = SecurityService(
            security_repository,
            audit_repository,
            transaction_manager,
            identity_repository,
        )
        return OpenInfraApplication(
            store=store,
            dcim_service=DcimLocationService(
                dcim_repository,
                audit_repository,
                transaction_manager,
            ),
            ipam_service=IpamAllocationService(
                ipam_repository,
                audit_repository,
                transaction_manager,
            ),
            security_service=security_service,
            identity_service=IdentityService(
                identity_repository,
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
            security_repository=security_repository,
            access_policy_repository=access_policy_repository,
            audit_repository=audit_repository,
            transaction_manager=transaction_manager,
            readiness_probe=readiness_probe,
            schema_status_provider=schema_status_provider,
        )
