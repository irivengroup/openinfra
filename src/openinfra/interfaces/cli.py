from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, NoReturn

from openinfra import __version__
from openinfra.application.access_policy_services import (
    CreateAccessPolicyRuleCommand,
    DeactivateAccessPolicyRuleCommand,
    EvaluateAccessPolicyCommand,
    ListAccessPolicyRulesCommand,
)
from openinfra.application.audit_services import (
    ExportAuditEventsCommand,
    ListAuditEventsCommand,
    VerifyAuditIntegrityCommand,
)
from openinfra.application.authentication_services import AuthProviderPolicyCommand
from openinfra.application.certificate_pki_services import (
    AssessCertificatesCommand,
    GetCertificateCommand,
    ImportCertificateBundleCommand,
    ListCertificateEndpointsCommand,
    ListCertificatesCommand,
    ObserveCertificateEndpointCommand,
    RetireCertificateCommand,
)
from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.dcim_services import (
    ConnectDcimCableCommand,
    CreateDcimBuildingCommand,
    CreateDcimFloorCommand,
    CreateDcimRoomCommand,
    CreateDcimSiteCommand,
    CreateDcimZoneCommand,
    DcimTopologyCatalogCommand,
    DefineCoolingZoneCommand,
    DefineDcimPortCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    DeleteDcimBuildingCommand,
    DeleteDcimFloorCommand,
    DeleteDcimRoomCommand,
    DeleteDcimSiteCommand,
    DeleteDcimZoneCommand,
    DeleteRackCommand,
    GenerateEquipmentLocatorCommand,
    GetDcimBuildingCommand,
    GetDcimFloorCommand,
    GetDcimRoomCommand,
    GetDcimSiteCommand,
    GetDcimZoneCommand,
    GetRackCommand,
    ListDcimBuildingsCommand,
    ListDcimFloorsCommand,
    ListDcimRoomsCommand,
    ListDcimSitesCommand,
    ListDcimZonesCommand,
    ListRacksCommand,
    LocateEquipmentCommand,
    RackCapacityCommand,
    RackEnergyCoolingCapacityCommand,
    RenderDigitalTwinCommand,
    RenderRackElevationCommand,
    RenderRoomPlanCommand,
    ReserveEquipmentPowerCommand,
    TraceDcimCableCommand,
    UpdateDcimBuildingCommand,
    UpdateDcimFloorCommand,
    UpdateDcimRoomCommand,
    UpdateDcimSiteCommand,
    UpdateDcimZoneCommand,
    UpdateRackCommand,
    VerifyEquipmentScanCommand,
)
from openinfra.application.dependency_graph_services import (
    AnalyzeDependencyImpactCommand,
    AnalyzeDependencySpofCommand,
    ExportDependencyGraphCommand,
    FindDependencyPathCommand,
    TraverseDependencyGraphCommand,
)
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
    BuildEnterpriseAgentBootstrapPlanCommand,
    BuildLocalDiscoveryPlanCommand,
    ClaimDiscoveryJobCommand,
    CompleteDiscoveryJobCommand,
    CreateDiscoveryIntegrationProfileCommand,
    CreateDiscoveryProtocolProfileCommand,
    DisableCollectorCommand,
    DisableDiscoveryIntegrationProfileCommand,
    DisableDiscoveryProtocolProfileCommand,
    EnrollDiscoveryProxyCommand,
    FailDiscoveryJobCommand,
    GetDiscoveryEvidenceCommand,
    GetDiscoveryIntegrationProfileCommand,
    GetDiscoveryJobCommand,
    GetDiscoveryProtocolProfileCommand,
    GetDiscoveryReconciliationCommand,
    HeartbeatCollectorCommand,
    ListCollectorsCommand,
    ListDiscoveryEvidenceCommand,
    ListDiscoveryIntegrationProfilesCommand,
    ListDiscoveryJobsCommand,
    ListDiscoveryProtocolProfilesCommand,
    ListDiscoveryReconciliationsCommand,
    ReconcileDiscoveryEvidenceCommand,
    RegisterCollectorCommand,
    RenewDiscoveryJobLeaseCommand,
    ReplayDiscoveryDeadLetterJobCommand,
    ResolveDiscoveryReconciliationCommand,
    SubmitDiscoveryEvidenceCommand,
    SubmitDiscoveryJobCommand,
    UpdateDiscoveryIntegrationProfileCommand,
    UpdateDiscoveryProtocolProfileCommand,
)
from openinfra.application.edition_services import (
    CheckFeatureCommand,
    CheckQuotaCommand,
    EditionPolicyService,
)
from openinfra.application.export_services import (
    GetExportArtifactChunkCommand,
    GetExportArtifactCommand,
    GetExportJobCommand,
    RequestExportCommand,
    RunExportJobCommand,
)
from openinfra.application.external_itsm_services import (
    BuildFreshserviceAssetSyncPlanCommand,
    BuildGlpiAssetSyncPlanCommand,
    BuildJiraServiceManagementAssetSyncPlanCommand,
    BuildOpenServiceCmdbSyncPlanCommand,
    BuildServiceNowCiSyncPlanCommand,
    ValidateFreshserviceConnectorCommand,
    ValidateGlpiConnectorCommand,
    ValidateJiraServiceManagementConnectorCommand,
    ValidateOpenServiceConnectorCommand,
    ValidateServiceNowConnectorCommand,
)
from openinfra.application.field_operation_services import (
    AcquireInterventionLockCommand,
    AttachFieldEvidenceCommand,
    CancelFieldOperationCommand,
    CompleteFieldOperationCommand,
    CreateOfflineSyncPackageCommand,
    GenerateFieldOperationSheetCommand,
    GetFieldOperationSheetCommand,
    GetOfflineSyncPackageCommand,
    ListFieldOperationSheetsCommand,
    ListOfflineSyncPackagesCommand,
    RecordFieldChecklistCommand,
    ReleaseInterventionLockCommand,
    StartFieldOperationCommand,
    SynchronizeOfflinePackageCommand,
    ValidateFieldEvidenceCommand,
    VerifyFieldQrCommand,
)
from openinfra.application.flow_matrix_services import (
    CompareFlowMatrixCommand,
    ListFlowDeclarationsCommand,
    ListFlowObservationsCommand,
    RetireFlowDeclarationCommand,
    SubmitFlowObservationCommand,
    UpsertFlowDeclarationCommand,
)
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.import_services import (
    BulkImportDatasetCommand,
    BulkImportRollbackCommand,
    ImportDatasetCommand,
    MigrationGuideCommand,
    MigrationTemplateCommand,
    PlanMigrationCommand,
)
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineAsnCommand,
    DefineBgpPeerCommand,
    DefineIpAggregateCommand,
    DefineIpPrefixCommand,
    DefineIpRangeCommand,
    DefineVlanCommand,
    DefineVlanGroupCommand,
    DefineVrfCommand,
    DefineVxlanVniCommand,
    DetectIpamConflictsCommand,
    IpamCapacityCommand,
    IpamNetworkBindingsCommand,
    IpamReservationWizardCommand,
    IpamSearchCommand,
    IpamTopologyCommand,
    IpamUiDashboardCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
    PreviewDdiReservationCommand,
    RegisterIpAddressCommand,
)
from openinfra.application.it_resources_management_quality_services import (
    EvaluateItrmObjectQualityCommand,
    ItrmQualitySummaryCommand,
)
from openinfra.application.it_resources_management_services import (
    CreateSourceRelationCommand,
    GetSourceObjectAsOfCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectAuditCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    ReconcileSourceObjectCommand,
    UpsertSourceObjectCommand,
)
from openinfra.application.itam_services import (
    AddThirdPartySupportCommand,
    CreateItamOrganizationCommand,
    CreateItamPartnerCommand,
    CreateItamTenantCommand,
    DeleteItamOrganizationCommand,
    DeleteItamPartnerCommand,
    DeleteItamTenantCommand,
    GetAssetSupportCoverageReportCommand,
    GetAssetSupportProfileCommand,
    GetItamOrganizationCommand,
    GetItamPartnerCommand,
    GetItamTenantCommand,
    GetSoftwareLicenseCommand,
    GetSoftwareLicenseComplianceCommand,
    ListItamOrganizationsCommand,
    ListItamPartnersCommand,
    ListItamTenantsCommand,
    RegisterManufacturerSupportCommand,
    RegisterSoftwareLicenseCommand,
    UpdateItamOrganizationCommand,
    UpdateItamPartnerCommand,
    UpdateItamTenantCommand,
    UpdateSoftwareLicenseAssignmentCommand,
)
from openinfra.application.network_config_compliance_services import (
    AssessNetworkConfigComplianceCommand,
    ListNetworkConfigBaselinesCommand,
    ListNetworkConfigObservationsCommand,
    RetireNetworkConfigBaselineCommand,
    SubmitNetworkConfigObservationCommand,
    UpsertNetworkConfigBaselineCommand,
)
from openinfra.application.search_services import GlobalSearchCommand
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
)
from openinfra.application.simulation_services import (
    CancelSimulationScenarioCommand,
    CompareSimulationReportsCommand,
    CreateSimulationScenarioCommand,
    GetSimulationReportCommand,
    GetSimulationScenarioCommand,
    ListSimulationComparisonsCommand,
    ListSimulationReportsCommand,
    ListSimulationScenariosCommand,
    RunSimulationScenarioCommand,
)
from openinfra.application.source_governance_services import (
    CreateSourceGovernanceRuleCommand,
    DeactivateSourceGovernanceRuleCommand,
    EvaluateSourceGovernanceCommand,
    ListSourceGovernanceRulesCommand,
)
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.authentication import ExternalDirectoryConfig
from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.domain.resource_taxonomy import ResourceTaxonomy
from openinfra.domain.security import Permission
from openinfra.infrastructure.installer_config import InstallerConfigValidator
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLMigrationCatalog,
    PostgreSQLMigrationExecutor,
    PostgreSQLSessionRegistry,
)
from openinfra.infrastructure.proxy_enrollment import (
    ProxyEnrollmentConfigValidator,
    ProxyEnrollmentConfigWriter,
    ProxyEnrollmentHttpClient,
    ProxyEnrollmentPayloadFactory,
)
from openinfra.infrastructure.runtime_config import RuntimeConfigLoader, RuntimeDatabaseDsnResolver
from openinfra.infrastructure.spec_validation import ContractualSpecValidator


class OpenInfraCLI:
    @classmethod
    def main(cls) -> int:
        return cls().run(sys.argv[1:])

    def run(self, argv: list[str]) -> int:
        parser = self._build_parser()
        args = parser.parse_args(argv)
        try:
            return int(args.handler(args))
        except OpenInfraError as exc:
            print(f"openinfra: error: {exc}", file=sys.stderr)
            return 2

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="openinfra", description="OpenInfra management CLI")
        subparsers = parser.add_subparsers(dest="command", required=True)
        self._add_version_command(subparsers)
        self._add_spec_commands(subparsers)
        self._add_installer_commands(subparsers)
        self._add_edition_commands(subparsers)
        self._add_database_commands(subparsers)
        self._add_auth_commands(subparsers)
        self._add_security_commands(subparsers)
        self._add_identity_commands(subparsers)
        self._add_access_policy_commands(subparsers)
        self._add_audit_commands(subparsers)
        self._add_search_commands(subparsers)
        self._add_itam_commands(subparsers)
        self._add_import_commands(subparsers)
        self._add_export_commands(subparsers)
        self._add_integrations_commands(subparsers)
        self._add_discovery_commands(subparsers)
        self._add_graph_commands(subparsers)
        self._add_simulation_commands(subparsers)
        self._add_flow_commands(subparsers)
        self._add_certificate_commands(subparsers)
        self._add_network_config_commands(subparsers)
        self._add_rsot_commands(subparsers)
        self._add_itrm_commands(subparsers)
        self._add_ri_commands(subparsers)
        self._add_sot_commands(subparsers)
        self._add_ipam_commands(subparsers)
        self._add_dcim_commands(subparsers)
        return parser

    def _add_version_command(self, subparsers: Any) -> None:
        parser = subparsers.add_parser("version", help="print OpenInfra version")
        parser.set_defaults(handler=self._handle_version)

    def _add_spec_commands(self, subparsers: Any) -> None:
        spec = subparsers.add_parser("spec", help="contractual specification operations")
        spec_subparsers = spec.add_subparsers(dest="spec_command", required=True)
        validate = spec_subparsers.add_parser("validate", help="validate CDC/SFG/STG source files")
        validate.add_argument("--root", type=Path, required=True)
        validate.set_defaults(handler=self._handle_spec_validate)

    def _add_installer_commands(self, subparsers: Any) -> None:
        installer = subparsers.add_parser("installer", help="autonomous installer validation")
        installer_subparsers = installer.add_subparsers(dest="installer_command", required=True)
        validate = installer_subparsers.add_parser("validate", help="validate install.ini files")
        validate.add_argument("--root", type=Path, default=Path("installers"))
        validate.add_argument("--path", type=Path)
        validate.add_argument("--edition", choices=("lite", "pro", "enterprise"))
        validate.add_argument("--scope", choices=("all-in-one", "server", "web", "agent"))
        validate.set_defaults(handler=self._handle_installer_validate)
        dry_run = installer_subparsers.add_parser("dry-run", help="render installer impact plan")
        dry_run.add_argument("--root", type=Path, default=Path("installers"))
        dry_run.add_argument("--path", type=Path)
        dry_run.add_argument("--edition", choices=("lite", "pro", "enterprise"))
        dry_run.add_argument("--scope", choices=("all-in-one", "server", "web", "agent"))
        dry_run.set_defaults(handler=self._handle_installer_dry_run)
        render_systemd = installer_subparsers.add_parser(
            "render-systemd", help="render the systemd unit managed by an installer scope"
        )
        render_systemd.add_argument(
            "--edition", choices=("lite", "pro", "enterprise"), required=True
        )
        render_systemd.add_argument(
            "--scope", choices=("all-in-one", "server", "web", "agent"), required=True
        )
        render_systemd.set_defaults(handler=self._handle_installer_render_systemd)

    def _add_edition_commands(self, subparsers: Any) -> None:
        edition = subparsers.add_parser("edition", help="runtime edition gates and quotas")
        edition_subparsers = edition.add_subparsers(dest="edition_command", required=True)

        list_policies = edition_subparsers.add_parser(
            "list", help="list Lite, Pro and Enterprise capabilities and quotas"
        )
        self._add_backend_arguments(list_policies)
        list_policies.set_defaults(handler=self._handle_edition_list)

        feature_check = edition_subparsers.add_parser(
            "feature-check", help="check whether an edition allows a feature capability"
        )
        feature_check.add_argument("--backend", choices=("json", "postgresql"), default="json")
        feature_check.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        feature_check.add_argument("--postgres-dsn")
        feature_check.add_argument("--tenant", default="default")
        feature_check.add_argument(
            "--edition", choices=("lite", "pro", "enterprise"), required=True
        )
        feature_check.add_argument("--capability", required=True)
        feature_check.set_defaults(handler=self._handle_edition_feature_check)

        quota_check = edition_subparsers.add_parser(
            "quota-check", help="check tenant runtime usage against an edition quota"
        )
        self._add_backend_arguments(quota_check)
        quota_check.add_argument("--tenant", required=True)
        quota_check.add_argument("--resource", required=True)
        quota_check.add_argument("--increment", type=int, default=1)
        quota_check.set_defaults(handler=self._handle_edition_quota_check)

    def _add_database_commands(self, subparsers: Any) -> None:
        database = subparsers.add_parser("database", help="database operations")
        database_subparsers = database.add_subparsers(dest="database_command", required=True)
        render = database_subparsers.add_parser(
            "render-migration",
            help="render a versioned migration",
        )
        render.add_argument("--name", required=True)
        render.add_argument("--root", type=Path)
        render.set_defaults(handler=self._handle_database_render_migration)
        status = database_subparsers.add_parser(
            "status",
            help="report PostgreSQL schema migration status",
        )
        status.add_argument("--postgres-dsn")
        status.add_argument("--root", type=Path)
        status.set_defaults(handler=self._handle_database_status)
        apply = database_subparsers.add_parser(
            "apply-migrations",
            help="apply PostgreSQL migrations idempotently",
        )
        apply.add_argument("--postgres-dsn")
        apply.add_argument("--root", type=Path)
        apply.add_argument("--dry-run", action="store_true")
        apply.set_defaults(handler=self._handle_database_apply_migrations)
        ha_plan = database_subparsers.add_parser(
            "ha-plan",
            help="render PostgreSQL HA/PITR plan from an autonomous installer scope",
        )
        ha_plan.add_argument("--path", type=Path, required=True)
        ha_plan.add_argument("--edition", choices=("lite", "pro", "enterprise"), required=True)
        ha_plan.add_argument(
            "--scope", choices=("all-in-one", "server", "web", "agent"), required=True
        )
        ha_plan.set_defaults(handler=self._handle_database_ha_plan)

    def _add_auth_commands(self, subparsers: Any) -> None:
        auth = subparsers.add_parser("auth", help="authentication provider policy operations")
        auth_subparsers = auth.add_subparsers(dest="auth_command", required=True)
        policy = auth_subparsers.add_parser(
            "policy",
            help="validate local, LDAP or IPA authentication policy for an edition",
        )
        self._add_backend_arguments(policy)
        policy.add_argument("--mode", choices=("standard", "ldap", "ipa"), required=True)
        policy.add_argument("--url")
        policy.add_argument("--base-dn")
        policy.add_argument("--user-filter", default="(uid={username})")
        policy.add_argument("--group-filter", default="(member={user_dn})")
        policy.add_argument("--bind-dn-ref")
        policy.add_argument("--bind-password-ref")
        policy.add_argument("--ca-cert-ref")
        policy.add_argument("--cache-ttl-seconds", type=int, default=300)
        policy.add_argument("--no-nested-groups", action="store_true")
        policy.set_defaults(handler=self._handle_auth_policy)

    def _add_security_commands(self, subparsers: Any) -> None:
        security = subparsers.add_parser("security", help="api token and rbac operations")
        security_subparsers = security.add_subparsers(dest="security_command", required=True)
        bootstrap = security_subparsers.add_parser(
            "bootstrap-token",
            help="create or replace an API token hash and role binding",
        )
        bootstrap.add_argument("--backend", choices=("json", "postgresql"), default="json")
        bootstrap.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        bootstrap.add_argument("--postgres-dsn")
        bootstrap.add_argument("--tenant", required=True)
        bootstrap.add_argument("--actor", default="cli")
        bootstrap.add_argument("--subject", required=True)
        bootstrap.add_argument("--role", action="append", default=[])
        bootstrap.add_argument("--token")
        bootstrap.add_argument("--ttl-seconds", type=int)
        bootstrap.set_defaults(handler=self._handle_security_bootstrap_token)
        whoami = security_subparsers.add_parser(
            "whoami",
            help="validate an API token and print the authenticated principal",
        )
        whoami.add_argument("--backend", choices=("json", "postgresql"), default="json")
        whoami.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        whoami.add_argument("--postgres-dsn")
        whoami.add_argument("--tenant", required=True)
        whoami.add_argument("--token", required=True)
        whoami.set_defaults(handler=self._handle_security_whoami)
        revoke = security_subparsers.add_parser(
            "revoke-token",
            help="revoke an API token using a security administrator token",
        )
        revoke.add_argument("--backend", choices=("json", "postgresql"), default="json")
        revoke.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        revoke.add_argument("--postgres-dsn")
        revoke.add_argument("--tenant", required=True)
        revoke.add_argument("--actor", default="cli")
        revoke.add_argument("--target-token", required=True)
        revoke.add_argument("--admin-token")
        revoke.set_defaults(handler=self._handle_security_revoke_token)
        rotate = security_subparsers.add_parser(
            "rotate-token",
            help="rotate a security administrator token and revoke the previous token",
        )
        rotate.add_argument("--backend", choices=("json", "postgresql"), default="json")
        rotate.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        rotate.add_argument("--postgres-dsn")
        rotate.add_argument("--tenant", required=True)
        rotate.add_argument("--actor", default="cli")
        rotate.add_argument("--current-token", required=True)
        rotate.add_argument("--subject")
        rotate.add_argument("--role", action="append", default=[])
        rotate.add_argument("--token")
        rotate.add_argument("--ttl-seconds", type=int)
        rotate.set_defaults(handler=self._handle_security_rotate_token)
        list_tokens = security_subparsers.add_parser(
            "list-tokens",
            help="list API token metadata without exposing token hashes or secrets",
        )
        list_tokens.add_argument("--backend", choices=("json", "postgresql"), default="json")
        list_tokens.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        list_tokens.add_argument("--postgres-dsn")
        list_tokens.add_argument("--tenant", required=True)
        list_tokens.add_argument("--admin-token", required=True)
        list_tokens.add_argument("--limit", type=int, default=100)
        list_tokens.add_argument("--cursor")
        list_tokens.add_argument("--include-inactive", action="store_true")
        list_tokens.set_defaults(handler=self._handle_security_list_tokens)

    def _add_identity_commands(self, subparsers: Any) -> None:
        identity = subparsers.add_parser("identity", help="users, groups and role bindings")
        identity_subparsers = identity.add_subparsers(dest="identity_command", required=True)
        create_user = identity_subparsers.add_parser("create-user", help="upsert an IAM user")
        self._add_backend_arguments(create_user)
        create_user.add_argument("--tenant", required=True)
        create_user.add_argument("--actor", default="cli")
        create_user.add_argument("--admin-token", required=True)
        create_user.add_argument("--username", required=True)
        create_user.add_argument("--display-name", required=True)
        create_user.add_argument("--email")
        create_user.add_argument("--role", action="append", default=[])
        create_user.set_defaults(handler=self._handle_identity_create_user)
        create_group = identity_subparsers.add_parser("create-group", help="upsert an IAM group")
        self._add_backend_arguments(create_group)
        create_group.add_argument("--tenant", required=True)
        create_group.add_argument("--actor", default="cli")
        create_group.add_argument("--admin-token", required=True)
        create_group.add_argument("--name", required=True)
        create_group.add_argument("--display-name", required=True)
        create_group.add_argument("--role", action="append", default=[])
        create_group.set_defaults(handler=self._handle_identity_create_group)
        add_member = identity_subparsers.add_parser(
            "add-user-to-group",
            help="add a user to an IAM group",
        )
        self._add_backend_arguments(add_member)
        add_member.add_argument("--tenant", required=True)
        add_member.add_argument("--actor", default="cli")
        add_member.add_argument("--admin-token", required=True)
        add_member.add_argument("--username", required=True)
        add_member.add_argument("--group", required=True)
        add_member.set_defaults(handler=self._handle_identity_add_user_to_group)
        grant_user = identity_subparsers.add_parser(
            "grant-user-role",
            help="grant a built-in role directly to a user",
        )
        self._add_backend_arguments(grant_user)
        grant_user.add_argument("--tenant", required=True)
        grant_user.add_argument("--actor", default="cli")
        grant_user.add_argument("--admin-token", required=True)
        grant_user.add_argument("--username", required=True)
        grant_user.add_argument("--role", required=True)
        grant_user.set_defaults(handler=self._handle_identity_grant_user_role)
        grant_group = identity_subparsers.add_parser(
            "grant-group-role",
            help="grant a built-in role to a group",
        )
        self._add_backend_arguments(grant_group)
        grant_group.add_argument("--tenant", required=True)
        grant_group.add_argument("--actor", default="cli")
        grant_group.add_argument("--admin-token", required=True)
        grant_group.add_argument("--group", required=True)
        grant_group.add_argument("--role", required=True)
        grant_group.set_defaults(handler=self._handle_identity_grant_group_role)
        effective = identity_subparsers.add_parser(
            "effective",
            help="print effective roles for a user subject",
        )
        self._add_backend_arguments(effective)
        effective.add_argument("--tenant", required=True)
        effective.add_argument("--actor", default="cli")
        effective.add_argument("--admin-token", required=True)
        effective.add_argument("--subject", required=True)
        effective.set_defaults(handler=self._handle_identity_effective)

    def _add_access_policy_commands(self, subparsers: Any) -> None:
        access = subparsers.add_parser("access", help="attribute-based access policy operations")
        access_subparsers = access.add_subparsers(dest="access_command", required=True)
        create_rule = access_subparsers.add_parser("create-rule", help="upsert an ABAC rule")
        self._add_backend_arguments(create_rule)
        create_rule.add_argument("--tenant", required=True)
        create_rule.add_argument("--actor", default="cli")
        create_rule.add_argument("--admin-token", required=True)
        create_rule.add_argument("--name", required=True)
        create_rule.add_argument("--permission", required=True)
        create_rule.add_argument("--effect", choices=("allow", "deny"), required=True)
        create_rule.add_argument("--subject", action="append", default=[])
        create_rule.add_argument("--role", action="append", default=[])
        create_rule.add_argument("--site-code", action="append", default=[])
        create_rule.add_argument("--environment", action="append", default=[])
        create_rule.set_defaults(handler=self._handle_access_create_rule)
        list_rules = access_subparsers.add_parser("list-rules", help="list ABAC rules")
        self._add_backend_arguments(list_rules)
        list_rules.add_argument("--tenant", required=True)
        list_rules.add_argument("--admin-token", required=True)
        list_rules.add_argument("--limit", type=int, default=100)
        list_rules.add_argument("--cursor")
        list_rules.add_argument("--include-inactive", action="store_true")
        list_rules.set_defaults(handler=self._handle_access_list_rules)
        deactivate_rule = access_subparsers.add_parser(
            "deactivate-rule",
            help="deactivate an ABAC rule",
        )
        self._add_backend_arguments(deactivate_rule)
        deactivate_rule.add_argument("--tenant", required=True)
        deactivate_rule.add_argument("--actor", default="cli")
        deactivate_rule.add_argument("--admin-token", required=True)
        deactivate_rule.add_argument("--name", required=True)
        deactivate_rule.set_defaults(handler=self._handle_access_deactivate_rule)
        evaluate = access_subparsers.add_parser("evaluate", help="evaluate token access context")
        self._add_backend_arguments(evaluate)
        evaluate.add_argument("--tenant", required=True)
        evaluate.add_argument("--token", required=True)
        evaluate.add_argument("--permission", required=True)
        evaluate.add_argument("--site-code")
        evaluate.add_argument("--environment")
        evaluate.set_defaults(handler=self._handle_access_evaluate)

    def _add_search_commands(self, subparsers: Any) -> None:
        search = subparsers.add_parser("search", help="global cross-component search")
        search_subparsers = search.add_subparsers(dest="search_command", required=True)
        global_search = search_subparsers.add_parser(
            "global",
            help="search RSOT, IPAM and authorized Discovery data grouped by component",
        )
        self._add_backend_arguments(global_search)
        global_search.add_argument("--tenant", required=True)
        global_search.add_argument("--admin-token", required=True)
        global_search.add_argument("--query", required=True)
        global_search.add_argument("--limit", type=int, default=5)
        global_search.add_argument("--actor", default="cli")
        global_search.add_argument("--include-inactive-discovery", action="store_true")
        global_search.set_defaults(handler=self._handle_search_global)

    def _add_itam_commands(self, subparsers: Any) -> None:
        itam = subparsers.add_parser("itam", help="IT asset management operations")
        itam_subparsers = itam.add_subparsers(dest="itam_command", required=True)

        organization_list = itam_subparsers.add_parser(
            "organizations", help="list ITAM organizations"
        )
        self._add_backend_arguments(organization_list)
        organization_list.add_argument("--tenant", default="default", help="security tenant scope")
        organization_list.add_argument("--admin-token", required=True)
        organization_list.add_argument("--include-retired", action="store_true")
        organization_list.set_defaults(handler=self._handle_itam_organizations)

        organization_create = itam_subparsers.add_parser(
            "organization-create", help="create ITAM organization identity"
        )
        self._add_backend_arguments(organization_create)
        organization_create.add_argument("--organization", required=True)
        organization_create.add_argument("--actor", default="cli")
        organization_create.add_argument("--admin-token", required=True)
        organization_create.add_argument("--scope-tenant", default="default")
        organization_create.add_argument("--legal-name", required=True)
        organization_create.add_argument("--display-name")
        organization_create.add_argument(
            "--status", default="active", choices=("active", "suspended", "retired")
        )
        organization_create.add_argument("--registration-number", required=True)
        organization_create.add_argument("--tax-identifier", required=True)
        organization_create.add_argument("--country-code", required=True)
        organization_create.add_argument("--city", required=True)
        organization_create.add_argument("--postal-code", required=True)
        organization_create.add_argument("--address", required=True)
        organization_create.add_argument("--contact-email", required=True)
        organization_create.add_argument("--phone", default="+33000000000")
        organization_create.add_argument("--support-contact", required=True)
        organization_create.add_argument("--description")
        organization_create.set_defaults(handler=self._handle_itam_organization_create)

        organization_show = itam_subparsers.add_parser(
            "organization", help="show ITAM organization"
        )
        self._add_backend_arguments(organization_show)
        organization_show.add_argument("--organization", required=True)
        organization_show.add_argument("--tenant", default="default", help="security tenant scope")
        organization_show.add_argument("--admin-token", required=True)
        organization_show.set_defaults(handler=self._handle_itam_organization)

        organization_update = itam_subparsers.add_parser(
            "organization-update", help="update ITAM organization identity"
        )
        self._add_backend_arguments(organization_update)
        organization_update.add_argument("--organization", required=True)
        organization_update.add_argument("--actor", default="cli")
        organization_update.add_argument("--admin-token", required=True)
        organization_update.add_argument("--scope-tenant", default="default")
        organization_update.add_argument("--legal-name")
        organization_update.add_argument("--display-name")
        organization_update.add_argument("--status", choices=("active", "suspended", "retired"))
        organization_update.add_argument("--registration-number")
        organization_update.add_argument("--tax-identifier")
        organization_update.add_argument("--country-code")
        organization_update.add_argument("--city")
        organization_update.add_argument("--postal-code")
        organization_update.add_argument("--address")
        organization_update.add_argument("--contact-email")
        organization_update.add_argument("--phone")
        organization_update.add_argument("--support-contact")
        organization_update.add_argument("--description")
        organization_update.set_defaults(handler=self._handle_itam_organization_update)

        organization_delete = itam_subparsers.add_parser(
            "organization-delete", help="retire ITAM organization and attached tenants"
        )
        self._add_backend_arguments(organization_delete)
        organization_delete.add_argument("--organization", required=True)
        organization_delete.add_argument("--actor", default="cli")
        organization_delete.add_argument("--admin-token", required=True)
        organization_delete.add_argument("--scope-tenant", default="default")
        organization_delete.set_defaults(handler=self._handle_itam_organization_delete)

        partner_list = itam_subparsers.add_parser("partners", help="list ITAM accredited partners")
        self._add_backend_arguments(partner_list)
        partner_list.add_argument("--tenant", default="default", help="security tenant scope")
        partner_list.add_argument("--admin-token", required=True)
        partner_list.add_argument("--organization")
        partner_list.add_argument(
            "--kind", choices=("manufacturer", "software_publisher", "third_party_support")
        )
        partner_list.add_argument("--include-retired", action="store_true")
        partner_list.set_defaults(handler=self._handle_itam_partners)

        partner_create = itam_subparsers.add_parser(
            "partner-create", help="create ITAM accredited partner"
        )
        self._add_backend_arguments(partner_create)
        partner_create.add_argument("--organization", required=True)
        partner_create.add_argument("--partner", required=True)
        partner_create.add_argument(
            "--kind",
            required=True,
            choices=("manufacturer", "software_publisher", "third_party_support"),
        )
        partner_create.add_argument("--actor", default="cli")
        partner_create.add_argument("--admin-token", required=True)
        partner_create.add_argument("--scope-tenant", default="default")
        partner_create.add_argument("--legal-name", required=True)
        partner_create.add_argument("--display-name")
        partner_create.add_argument(
            "--status", default="active", choices=("active", "suspended", "retired")
        )
        partner_create.add_argument("--registration-number", required=True)
        partner_create.add_argument("--tax-identifier", required=True)
        partner_create.add_argument("--country-code", required=True)
        partner_create.add_argument("--city", required=True)
        partner_create.add_argument("--postal-code", required=True)
        partner_create.add_argument("--address", required=True)
        partner_create.add_argument("--contact-email", required=True)
        partner_create.add_argument("--phone", required=True)
        partner_create.add_argument("--support-contact", required=True)
        partner_create.add_argument("--website")
        partner_create.add_argument("--description")
        partner_create.set_defaults(handler=self._handle_itam_partner_create)

        partner_show = itam_subparsers.add_parser("partner", help="show ITAM accredited partner")
        self._add_backend_arguments(partner_show)
        partner_show.add_argument("--organization", required=True)
        partner_show.add_argument("--partner", required=True)
        partner_show.add_argument("--tenant", default="default", help="security tenant scope")
        partner_show.add_argument("--admin-token", required=True)
        partner_show.set_defaults(handler=self._handle_itam_partner)

        partner_update = itam_subparsers.add_parser(
            "partner-update", help="update ITAM accredited partner"
        )
        self._add_backend_arguments(partner_update)
        partner_update.add_argument("--organization", required=True)
        partner_update.add_argument("--partner", required=True)
        partner_update.add_argument("--actor", default="cli")
        partner_update.add_argument("--admin-token", required=True)
        partner_update.add_argument("--scope-tenant", default="default")
        partner_update.add_argument(
            "--kind", choices=("manufacturer", "software_publisher", "third_party_support")
        )
        partner_update.add_argument("--legal-name")
        partner_update.add_argument("--display-name")
        partner_update.add_argument("--status", choices=("active", "suspended", "retired"))
        partner_update.add_argument("--registration-number")
        partner_update.add_argument("--tax-identifier")
        partner_update.add_argument("--country-code")
        partner_update.add_argument("--city")
        partner_update.add_argument("--postal-code")
        partner_update.add_argument("--address")
        partner_update.add_argument("--contact-email")
        partner_update.add_argument("--phone")
        partner_update.add_argument("--support-contact")
        partner_update.add_argument("--website")
        partner_update.add_argument("--description")
        partner_update.set_defaults(handler=self._handle_itam_partner_update)

        partner_delete = itam_subparsers.add_parser(
            "partner-delete", help="retire ITAM accredited partner"
        )
        self._add_backend_arguments(partner_delete)
        partner_delete.add_argument("--organization", required=True)
        partner_delete.add_argument("--partner", required=True)
        partner_delete.add_argument("--actor", default="cli")
        partner_delete.add_argument("--admin-token", required=True)
        partner_delete.add_argument("--scope-tenant", default="default")
        partner_delete.set_defaults(handler=self._handle_itam_partner_delete)

        tenant_list = itam_subparsers.add_parser("tenants", help="list ITAM tenants")
        self._add_backend_arguments(tenant_list)
        tenant_list.add_argument("--tenant", default="default", help="security tenant scope")
        tenant_list.add_argument("--admin-token", required=True)
        tenant_list.add_argument("--include-retired", action="store_true")
        tenant_list.set_defaults(handler=self._handle_itam_tenants)

        tenant_create = itam_subparsers.add_parser("tenant-create", help="create ITAM tenant")
        self._add_backend_arguments(tenant_create)
        tenant_create.add_argument("--tenant", required=True, help="ITAM tenant id to create")
        tenant_create.add_argument(
            "--organization", default="default", help="parent ITAM organization id"
        )
        tenant_create.add_argument("--actor", default="cli")
        tenant_create.add_argument("--admin-token", required=True)
        tenant_create.add_argument("--scope-tenant", default="default")
        tenant_create.add_argument("--name", required=True)
        tenant_create.add_argument(
            "--status", default="active", choices=("active", "suspended", "retired")
        )
        tenant_create.add_argument("--default", action="store_true", dest="is_default")
        tenant_create.add_argument("--description")
        tenant_create.set_defaults(handler=self._handle_itam_tenant_create)

        tenant_show = itam_subparsers.add_parser("tenant", help="show ITAM tenant")
        self._add_backend_arguments(tenant_show)
        tenant_show.add_argument("--tenant", required=True)
        tenant_show.add_argument("--admin-token", required=True)
        tenant_show.set_defaults(handler=self._handle_itam_tenant)

        tenant_update = itam_subparsers.add_parser("tenant-update", help="update ITAM tenant")
        self._add_backend_arguments(tenant_update)
        tenant_update.add_argument("--tenant", required=True)
        tenant_update.add_argument("--organization", help="parent ITAM organization id")
        tenant_update.add_argument("--actor", default="cli")
        tenant_update.add_argument("--admin-token", required=True)
        tenant_update.add_argument("--scope-tenant", default="default")
        tenant_update.add_argument("--name")
        tenant_update.add_argument("--status", choices=("active", "suspended", "retired"))
        tenant_update.add_argument("--default", action="store_true", dest="is_default")
        tenant_update.add_argument("--clear-default", action="store_true")
        tenant_update.add_argument("--description")
        tenant_update.set_defaults(handler=self._handle_itam_tenant_update)

        tenant_delete = itam_subparsers.add_parser(
            "tenant-delete", help="retire ITAM tenant without destructive deletion"
        )
        self._add_backend_arguments(tenant_delete)
        tenant_delete.add_argument("--tenant", required=True)
        tenant_delete.add_argument("--actor", default="cli")
        tenant_delete.add_argument("--admin-token", required=True)
        tenant_delete.add_argument("--scope-tenant", default="default")
        tenant_delete.set_defaults(handler=self._handle_itam_tenant_delete)

        register_manufacturer = itam_subparsers.add_parser(
            "register-manufacturer-support",
            help="register immutable manufacturer warranty and initial support for an asset",
        )
        self._add_backend_arguments(register_manufacturer)
        register_manufacturer.add_argument("--tenant", required=True)
        register_manufacturer.add_argument("--actor", default="cli")
        register_manufacturer.add_argument("--admin-token", required=True)
        register_manufacturer.add_argument("--asset-tag", required=True)
        register_manufacturer.add_argument(
            "--manufacturer", required=True, help="display label retained for compatibility"
        )
        register_manufacturer.add_argument(
            "--manufacturer-partner", required=True, dest="manufacturer_partner_id"
        )
        register_manufacturer.add_argument("--warranty-reference", required=True)
        register_manufacturer.add_argument("--warranty-level", required=True)
        register_manufacturer.add_argument("--warranty-start", required=True)
        register_manufacturer.add_argument("--warranty-end", required=True)
        register_manufacturer.add_argument("--support-reference", required=True)
        register_manufacturer.add_argument("--support-level", required=True)
        register_manufacturer.add_argument("--support-contact", required=True)
        register_manufacturer.set_defaults(handler=self._handle_itam_register_manufacturer_support)

        add_third_party = itam_subparsers.add_parser(
            "add-third-party-support",
            help="add separated third-party support without modifying manufacturer support",
        )
        self._add_backend_arguments(add_third_party)
        add_third_party.add_argument("--tenant", required=True)
        add_third_party.add_argument("--actor", default="cli")
        add_third_party.add_argument("--admin-token", required=True)
        add_third_party.add_argument("--asset-tag", required=True)
        add_third_party.add_argument(
            "--provider", required=True, help="display label retained for compatibility"
        )
        add_third_party.add_argument(
            "--provider-partner", required=True, dest="provider_partner_id"
        )
        add_third_party.add_argument("--contract-reference", required=True)
        add_third_party.add_argument("--support-level", required=True)
        add_third_party.add_argument("--support-start", required=True)
        add_third_party.add_argument("--support-end", required=True)
        add_third_party.add_argument("--support-contact", required=True)
        add_third_party.add_argument("--status", default="active")
        add_third_party.add_argument("--notes")
        add_third_party.set_defaults(handler=self._handle_itam_add_third_party_support)

        show = itam_subparsers.add_parser("support-profile", help="show asset support profile")
        self._add_backend_arguments(show)
        show.add_argument("--tenant", required=True)
        show.add_argument("--admin-token", required=True)
        show.add_argument("--asset-tag", required=True)
        show.set_defaults(handler=self._handle_itam_support_profile)

        coverage = itam_subparsers.add_parser(
            "support-coverage",
            help="evaluate manufacturer warranty and third-party support coverage for an asset",
        )
        self._add_backend_arguments(coverage)
        coverage.add_argument("--tenant", required=True)
        coverage.add_argument("--admin-token", required=True)
        coverage.add_argument("--asset-tag", required=True)
        coverage.add_argument("--as-of")
        coverage.set_defaults(handler=self._handle_itam_support_coverage)

        software_license = itam_subparsers.add_parser(
            "register-software-license",
            help="register or update software license entitlement and contract metadata",
        )
        self._add_backend_arguments(software_license)
        software_license.add_argument("--tenant", required=True)
        software_license.add_argument("--actor", default="cli")
        software_license.add_argument("--admin-token", required=True)
        software_license.add_argument("--product-name", required=True)
        software_license.add_argument(
            "--vendor", required=True, help="display label retained for compatibility"
        )
        software_license.add_argument("--vendor-partner", required=True, dest="vendor_partner_id")
        software_license.add_argument("--license-reference", required=True)
        software_license.add_argument("--metric", required=True)
        software_license.add_argument("--purchased-quantity", required=True, type=int)
        software_license.add_argument("--assigned-quantity", default=0, type=int)
        software_license.add_argument("--entitlement-start", required=True)
        software_license.add_argument("--entitlement-end", required=True)
        software_license.add_argument("--contract-reference")
        software_license.add_argument("--version")
        software_license.add_argument("--status", default="active")
        software_license.add_argument("--owner")
        software_license.add_argument("--notes")
        software_license.set_defaults(handler=self._handle_itam_register_software_license)

        software_assignment = itam_subparsers.add_parser(
            "update-license-assignment",
            help="update assigned quantity for a software license entitlement",
        )
        self._add_backend_arguments(software_assignment)
        software_assignment.add_argument("--tenant", required=True)
        software_assignment.add_argument("--actor", default="cli")
        software_assignment.add_argument("--admin-token", required=True)
        software_assignment.add_argument("--license-reference", required=True)
        software_assignment.add_argument("--assigned-quantity", required=True, type=int)
        software_assignment.add_argument("--notes")
        software_assignment.set_defaults(handler=self._handle_itam_update_license_assignment)

        software_show = itam_subparsers.add_parser(
            "software-license",
            help="show software license entitlement",
        )
        self._add_backend_arguments(software_show)
        software_show.add_argument("--tenant", required=True)
        software_show.add_argument("--admin-token", required=True)
        software_show.add_argument("--license-reference", required=True)
        software_show.set_defaults(handler=self._handle_itam_software_license)

        software_compliance = itam_subparsers.add_parser(
            "software-license-compliance",
            help="evaluate software license compliance and utilization",
        )
        self._add_backend_arguments(software_compliance)
        software_compliance.add_argument("--tenant", required=True)
        software_compliance.add_argument("--admin-token", required=True)
        software_compliance.add_argument("--license-reference", required=True)
        software_compliance.add_argument("--as-of")
        software_compliance.set_defaults(handler=self._handle_itam_software_license_compliance)

    def _add_audit_commands(self, subparsers: Any) -> None:
        audit = subparsers.add_parser("audit", help="audit trail operations")
        audit_subparsers = audit.add_subparsers(dest="audit_command", required=True)
        list_events = audit_subparsers.add_parser("list", help="list audit events safely")
        self._add_backend_arguments(list_events)
        list_events.add_argument("--tenant", required=True)
        list_events.add_argument("--admin-token", required=True)
        list_events.add_argument("--limit", type=int, default=100)
        list_events.add_argument("--cursor")
        list_events.add_argument("--actor")
        list_events.add_argument("--action")
        list_events.add_argument("--target-type")
        list_events.add_argument("--target-id")
        list_events.add_argument("--severity")
        list_events.set_defaults(handler=self._handle_audit_list)
        export = audit_subparsers.add_parser("export", help="export audit events as JSON or JSONL")
        self._add_backend_arguments(export)
        export.add_argument("--tenant", required=True)
        export.add_argument("--admin-token", required=True)
        export.add_argument("--format", choices=("json", "jsonl"), default="jsonl")
        export.add_argument("--limit", type=int, default=500)
        export.add_argument("--cursor")
        export.add_argument("--actor")
        export.add_argument("--action")
        export.add_argument("--target-type")
        export.add_argument("--target-id")
        export.add_argument("--severity")
        export.set_defaults(handler=self._handle_audit_export)
        verify = audit_subparsers.add_parser("verify-integrity", help="verify audit hash chain")
        self._add_backend_arguments(verify)
        verify.add_argument("--tenant", required=True)
        verify.add_argument("--admin-token", required=True)
        verify.add_argument("--limit", type=int, default=500)
        verify.set_defaults(handler=self._handle_audit_verify_integrity)

    def _add_import_commands(self, subparsers: Any) -> None:
        imports = subparsers.add_parser("import", help="generic data import operations")
        import_subparsers = imports.add_subparsers(dest="import_command", required=True)
        dataset = import_subparsers.add_parser(
            "dataset",
            help=(
                "validate or apply a mapped CSV, JSON or XLSX dataset into "
                "RSOT (Ressource Source of Truth)"
            ),
        )
        self._add_backend_arguments(dataset)
        dataset.add_argument("--tenant", required=True)
        dataset.add_argument("--actor", default="cli")
        dataset.add_argument("--admin-token", required=True)
        dataset.add_argument("--file", type=Path, required=True)
        dataset.add_argument("--format", choices=("csv", "json", "xlsx"), required=True)
        dataset.add_argument("--mapping-json", required=True)
        dataset.add_argument("--apply", action="store_true")
        dataset.add_argument("--batch-size", type=int, default=500)
        dataset.set_defaults(handler=self._handle_import_dataset)

        bulk_dataset = import_subparsers.add_parser(
            "bulk-dataset",
            help="stream and apply a massive mapped CSV, JSON or XLSX dataset with checkpoints",
        )
        self._add_backend_arguments(bulk_dataset)
        bulk_dataset.add_argument("--tenant", required=True)
        bulk_dataset.add_argument("--actor", default="cli")
        bulk_dataset.add_argument("--admin-token", required=True)
        bulk_dataset.add_argument("--file", type=Path, required=True)
        bulk_dataset.add_argument("--format", choices=("csv", "json", "xlsx"), required=True)
        bulk_dataset.add_argument("--mapping-json", required=True)
        bulk_dataset.add_argument("--apply", action="store_true")
        bulk_dataset.add_argument("--batch-size", type=int, default=5_000)
        bulk_dataset.add_argument("--checkpoint-interval", type=int, default=25_000)
        bulk_dataset.add_argument("--resume-job-id")
        bulk_dataset.add_argument("--sample-limit", type=int, default=100)
        bulk_dataset.set_defaults(handler=self._handle_import_bulk_dataset)

        report = import_subparsers.add_parser("report", help="read a persisted import report")
        self._add_backend_arguments(report)
        report.add_argument("--tenant", required=True)
        report.add_argument("--job-id", required=True)
        report.set_defaults(handler=self._handle_import_report)

        bulk_rollback = import_subparsers.add_parser(
            "bulk-rollback",
            help="plan or apply a safe rollback for an applied bulk import job",
        )
        self._add_backend_arguments(bulk_rollback)
        bulk_rollback.add_argument("--tenant", required=True)
        bulk_rollback.add_argument("--actor", default="cli")
        bulk_rollback.add_argument("--admin-token", required=True)
        bulk_rollback.add_argument("--job-id", required=True)
        bulk_rollback.add_argument("--file", type=Path, required=True)
        bulk_rollback.add_argument("--format", choices=("csv", "json", "xlsx"), required=True)
        bulk_rollback.add_argument("--mapping-json", required=True)
        bulk_rollback.add_argument("--apply", action="store_true")
        bulk_rollback.add_argument("--conflict-policy", choices=("fail", "skip"), default="fail")
        bulk_rollback.set_defaults(handler=self._handle_import_bulk_rollback)

        bulk_report = import_subparsers.add_parser(
            "bulk-report", help="read a persisted bulk import report"
        )
        self._add_backend_arguments(bulk_report)
        bulk_report.add_argument("--tenant", required=True)
        bulk_report.add_argument("--job-id", required=True)
        bulk_report.set_defaults(handler=self._handle_import_bulk_report)

        bulk_checkpoint = import_subparsers.add_parser(
            "bulk-checkpoint", help="read the latest checkpoint for a bulk import job"
        )
        self._add_backend_arguments(bulk_checkpoint)
        bulk_checkpoint.add_argument("--tenant", required=True)
        bulk_checkpoint.add_argument("--job-id", required=True)
        bulk_checkpoint.set_defaults(handler=self._handle_import_bulk_checkpoint)

        bulk_progress = import_subparsers.add_parser(
            "bulk-progress",
            help="read resumability and processed-row counters for a bulk import job",
        )
        self._add_backend_arguments(bulk_progress)
        bulk_progress.add_argument("--tenant", required=True)
        bulk_progress.add_argument("--job-id", required=True)
        bulk_progress.set_defaults(handler=self._handle_import_bulk_progress)

        migration_template = import_subparsers.add_parser(
            "migration-template",
            help=(
                "print a built-in migration mapping template for Device42, "
                "NetBox, Nautobot, GLPI or generic CSV"
            ),
        )
        self._add_backend_arguments(migration_template)
        migration_template.add_argument(
            "--source", choices=("device42", "netbox", "nautobot", "glpi", "csv"), required=True
        )
        migration_template.set_defaults(handler=self._handle_import_migration_template)

        migration_guide = import_subparsers.add_parser(
            "migration-guide",
            help=(
                "print an operator migration guide for Device42, "
                "NetBox, Nautobot, GLPI or generic CSV"
            ),
        )
        self._add_backend_arguments(migration_guide)
        migration_guide.add_argument(
            "--source", choices=("device42", "netbox", "nautobot", "glpi", "csv"), required=True
        )
        migration_guide.set_defaults(handler=self._handle_import_migration_guide)

        migration_plan = import_subparsers.add_parser(
            "migration-plan",
            help=(
                "simulate a legacy inventory migration and persist a gap report "
                "without mutating RSOT"
            ),
        )
        self._add_backend_arguments(migration_plan)
        migration_plan.add_argument("--tenant", required=True)
        migration_plan.add_argument("--actor", default="cli")
        migration_plan.add_argument("--admin-token", required=True)
        migration_plan.add_argument(
            "--source", choices=("device42", "netbox", "nautobot", "glpi", "csv"), required=True
        )
        migration_plan.add_argument("--file", type=Path, required=True)
        migration_plan.add_argument("--format", choices=("csv", "json", "xlsx"), required=True)
        migration_plan.add_argument("--sample-limit", type=int, default=100)
        migration_plan.set_defaults(handler=self._handle_import_migration_plan)

        migration_report = import_subparsers.add_parser(
            "migration-report", help="read a persisted legacy migration gap report"
        )
        self._add_backend_arguments(migration_report)
        migration_report.add_argument("--tenant", required=True)
        migration_report.add_argument("--job-id", required=True)
        migration_report.set_defaults(handler=self._handle_import_migration_report)

    def _add_integrations_commands(self, subparsers: Any) -> None:
        integrations = subparsers.add_parser(
            "integrations", help="external integration connectors without native ITSM ticketing"
        )
        integration_subparsers = integrations.add_subparsers(
            dest="integrations_command", required=True
        )

        providers = integration_subparsers.add_parser(
            "itsm-providers", help="list supported external ITSM connector policies"
        )
        self._add_backend_arguments(providers)
        providers.set_defaults(handler=self._handle_integrations_itsm_providers)

        validate = integration_subparsers.add_parser(
            "servicenow-validate", help="validate a ServiceNow external connector profile"
        )
        self._add_backend_arguments(validate)
        validate.add_argument("--tenant", required=True)
        validate.add_argument("--instance-url", required=True)
        validate.add_argument("--table-name", default="cmdb_ci")
        validate.add_argument("--auth-secret-ref", required=True)
        validate.add_argument("--disabled", action="store_true")
        validate.set_defaults(handler=self._handle_integrations_servicenow_validate)

        plan = integration_subparsers.add_parser(
            "servicenow-ci-sync-plan", help="build a safe ServiceNow CI sync plan"
        )
        self._add_backend_arguments(plan)
        plan.add_argument("--tenant", required=True)
        plan.add_argument("--resource-key", required=True)
        plan.add_argument("--direction", default="push_ci")
        plan.add_argument("--target-table", default="cmdb_ci")
        plan.set_defaults(handler=self._handle_integrations_servicenow_ci_sync_plan)

        jira_validate = integration_subparsers.add_parser(
            "jira-validate",
            help="validate a Jira Service Management Assets external connector profile",
        )
        self._add_backend_arguments(jira_validate)
        jira_validate.add_argument("--tenant", required=True)
        jira_validate.add_argument("--instance-url", required=True)
        jira_validate.add_argument("--object-type", default="object")
        jira_validate.add_argument("--auth-secret-ref", required=True)
        jira_validate.add_argument("--disabled", action="store_true")
        jira_validate.set_defaults(handler=self._handle_integrations_jira_validate)

        jira_plan = integration_subparsers.add_parser(
            "jira-asset-sync-plan",
            help="build a safe Jira Service Management Assets synchronization plan",
        )
        self._add_backend_arguments(jira_plan)
        jira_plan.add_argument("--tenant", required=True)
        jira_plan.add_argument("--resource-key", required=True)
        jira_plan.add_argument("--direction", default="push_ci")
        jira_plan.add_argument("--object-type", default="object")
        jira_plan.set_defaults(handler=self._handle_integrations_jira_asset_sync_plan)

        glpi_validate = integration_subparsers.add_parser(
            "glpi-validate",
            help="validate a GLPI Inventory external connector profile",
        )
        self._add_backend_arguments(glpi_validate)
        glpi_validate.add_argument("--tenant", required=True)
        glpi_validate.add_argument("--instance-url", required=True)
        glpi_validate.add_argument("--item-type", default="computer")
        glpi_validate.add_argument("--auth-secret-ref", required=True)
        glpi_validate.add_argument("--disabled", action="store_true")
        glpi_validate.set_defaults(handler=self._handle_integrations_glpi_validate)

        glpi_plan = integration_subparsers.add_parser(
            "glpi-asset-sync-plan",
            help="build a safe GLPI Inventory asset synchronization plan",
        )
        self._add_backend_arguments(glpi_plan)
        glpi_plan.add_argument("--tenant", required=True)
        glpi_plan.add_argument("--resource-key", required=True)
        glpi_plan.add_argument("--direction", default="push_ci")
        glpi_plan.add_argument("--item-type", default="computer")
        glpi_plan.set_defaults(handler=self._handle_integrations_glpi_asset_sync_plan)

        freshservice_validate = integration_subparsers.add_parser(
            "freshservice-validate",
            help="validate a Freshservice Assets external connector profile",
        )
        self._add_backend_arguments(freshservice_validate)
        freshservice_validate.add_argument("--tenant", required=True)
        freshservice_validate.add_argument("--instance-url", required=True)
        freshservice_validate.add_argument("--asset-type", default="asset")
        freshservice_validate.add_argument("--auth-secret-ref", required=True)
        freshservice_validate.add_argument("--disabled", action="store_true")
        freshservice_validate.set_defaults(handler=self._handle_integrations_freshservice_validate)

        freshservice_plan = integration_subparsers.add_parser(
            "freshservice-asset-sync-plan",
            help="build a safe Freshservice Assets synchronization plan",
        )
        self._add_backend_arguments(freshservice_plan)
        freshservice_plan.add_argument("--tenant", required=True)
        freshservice_plan.add_argument("--resource-key", required=True)
        freshservice_plan.add_argument("--direction", default="push_ci")
        freshservice_plan.add_argument("--asset-type", default="asset")
        freshservice_plan.set_defaults(
            handler=self._handle_integrations_freshservice_asset_sync_plan
        )

        openservice_validate = integration_subparsers.add_parser(
            "openservice-validate",
            help=(
                "validate a future OpenService external CMDB connector profile; "
                "OpenService keeps its own web UI"
            ),
        )
        self._add_backend_arguments(openservice_validate)
        openservice_validate.add_argument("--tenant", required=True)
        openservice_validate.add_argument("--instance-url", required=True)
        openservice_validate.add_argument("--collection", default="configuration_item")
        openservice_validate.add_argument("--auth-secret-ref", required=True)
        openservice_validate.add_argument("--disabled", action="store_true")
        openservice_validate.set_defaults(handler=self._handle_integrations_openservice_validate)

        openservice_plan = integration_subparsers.add_parser(
            "openservice-cmdb-sync-plan",
            help=(
                "build a safe OpenService CMDB synchronization plan without "
                "OpenInfra native ticketing"
            ),
        )
        self._add_backend_arguments(openservice_plan)
        openservice_plan.add_argument("--tenant", required=True)
        openservice_plan.add_argument("--resource-key", required=True)
        openservice_plan.add_argument("--direction", default="push_ci")
        openservice_plan.add_argument("--collection", default="configuration_item")
        openservice_plan.set_defaults(handler=self._handle_integrations_openservice_cmdb_sync_plan)

    def _add_discovery_commands(self, subparsers: Any) -> None:
        discovery = subparsers.add_parser(
            "discovery", help="distributed discovery collector registry operations"
        )
        discovery_subparsers = discovery.add_subparsers(dest="discovery_command", required=True)

        profile_create = discovery_subparsers.add_parser(
            "protocol-profile-create",
            help="create a secured SNMP/SSH/WinRM discovery protocol profile",
        )
        self._add_backend_arguments(profile_create)
        profile_create.add_argument("--tenant", required=True)
        profile_create.add_argument("--actor", default="cli")
        profile_create.add_argument("--admin-token", required=True)
        profile_create.add_argument("--name", required=True)
        profile_create.add_argument("--protocol", choices=("snmp", "ssh", "winrm"), required=True)
        profile_create.add_argument("--scope", required=True)
        profile_create.add_argument("--credential-secret-ref", required=True)
        profile_create.add_argument("--port", type=int)
        profile_create.add_argument("--timeout-seconds", type=int, default=30)
        profile_create.add_argument("--max-concurrency", type=int, default=4)
        profile_create.add_argument("--rate-limit-per-minute", type=int, default=120)
        profile_create.add_argument("--retry-count", type=int, default=1)
        profile_create.set_defaults(handler=self._handle_discovery_protocol_profile_create)

        profile_update = discovery_subparsers.add_parser(
            "protocol-profile-update",
            help="update a secured discovery protocol profile without materializing secrets",
        )
        self._add_backend_arguments(profile_update)
        profile_update.add_argument("--tenant", required=True)
        profile_update.add_argument("--actor", default="cli")
        profile_update.add_argument("--admin-token", required=True)
        profile_update.add_argument("--profile-id", required=True)
        profile_update.add_argument("--name")
        profile_update.add_argument("--scope")
        profile_update.add_argument("--credential-secret-ref")
        profile_update.add_argument("--port", type=int)
        profile_update.add_argument("--timeout-seconds", type=int)
        profile_update.add_argument("--max-concurrency", type=int)
        profile_update.add_argument("--rate-limit-per-minute", type=int)
        profile_update.add_argument("--retry-count", type=int)
        profile_update.set_defaults(handler=self._handle_discovery_protocol_profile_update)

        profile_get = discovery_subparsers.add_parser(
            "protocol-profile", help="get a discovery protocol profile with masked secret reference"
        )
        self._add_backend_arguments(profile_get)
        profile_get.add_argument("--tenant", required=True)
        profile_get.add_argument("--admin-token", required=True)
        profile_get.add_argument("--profile-id", required=True)
        profile_get.set_defaults(handler=self._handle_discovery_protocol_profile_get)

        profile_list = discovery_subparsers.add_parser(
            "protocol-profile-list", help="list discovery protocol profiles"
        )
        self._add_backend_arguments(profile_list)
        profile_list.add_argument("--tenant", required=True)
        profile_list.add_argument("--admin-token", required=True)
        profile_list.add_argument("--limit", type=int, default=100)
        profile_list.add_argument("--cursor")
        profile_list.add_argument("--include-inactive", action="store_true")
        profile_list.set_defaults(handler=self._handle_discovery_protocol_profile_list)

        profile_delete = discovery_subparsers.add_parser(
            "protocol-profile-delete", help="disable a discovery protocol profile"
        )
        self._add_backend_arguments(profile_delete)
        profile_delete.add_argument("--tenant", required=True)
        profile_delete.add_argument("--actor", default="cli")
        profile_delete.add_argument("--admin-token", required=True)
        profile_delete.add_argument("--profile-id", required=True)
        profile_delete.add_argument("--reason", required=True)
        profile_delete.set_defaults(handler=self._handle_discovery_protocol_profile_delete)

        integration_create = discovery_subparsers.add_parser(
            "integration-profile-create",
            help="create a secured virtualization, Kubernetes or cloud discovery profile",
        )
        self._add_backend_arguments(integration_create)
        integration_create.add_argument("--tenant", required=True)
        integration_create.add_argument("--actor", default="cli")
        integration_create.add_argument("--admin-token", required=True)
        integration_create.add_argument("--name", required=True)
        integration_create.add_argument(
            "--kind",
            choices=(
                "vmware",
                "proxmox",
                "hyperv",
                "kubernetes",
                "aws",
                "azure",
                "gcp",
                "openstack",
            ),
            required=True,
        )
        integration_create.add_argument("--scope", required=True)
        integration_create.add_argument("--endpoint-url")
        integration_create.add_argument("--credential-secret-ref", required=True)
        integration_create.add_argument("--no-verify-tls", action="store_true")
        integration_create.add_argument("--disable-inventory", action="store_true")
        integration_create.add_argument("--max-concurrency", type=int, default=4)
        integration_create.add_argument("--rate-limit-per-minute", type=int, default=120)
        integration_create.set_defaults(handler=self._handle_discovery_integration_profile_create)

        integration_update = discovery_subparsers.add_parser(
            "integration-profile-update",
            help="update a secured discovery integration profile without materializing secrets",
        )
        self._add_backend_arguments(integration_update)
        integration_update.add_argument("--tenant", required=True)
        integration_update.add_argument("--actor", default="cli")
        integration_update.add_argument("--admin-token", required=True)
        integration_update.add_argument("--profile-id", required=True)
        integration_update.add_argument("--name")
        integration_update.add_argument("--scope")
        integration_update.add_argument("--endpoint-url")
        integration_update.add_argument("--credential-secret-ref")
        integration_update.add_argument("--verify-tls", choices=("true", "false"))
        integration_update.add_argument("--inventory-enabled", choices=("true", "false"))
        integration_update.add_argument("--max-concurrency", type=int)
        integration_update.add_argument("--rate-limit-per-minute", type=int)
        integration_update.set_defaults(handler=self._handle_discovery_integration_profile_update)

        integration_get = discovery_subparsers.add_parser(
            "integration-profile",
            help="get a discovery integration profile with masked secret reference",
        )
        self._add_backend_arguments(integration_get)
        integration_get.add_argument("--tenant", required=True)
        integration_get.add_argument("--admin-token", required=True)
        integration_get.add_argument("--profile-id", required=True)
        integration_get.set_defaults(handler=self._handle_discovery_integration_profile_get)

        integration_list = discovery_subparsers.add_parser(
            "integration-profile-list", help="list discovery integration profiles"
        )
        self._add_backend_arguments(integration_list)
        integration_list.add_argument("--tenant", required=True)
        integration_list.add_argument("--admin-token", required=True)
        integration_list.add_argument("--limit", type=int, default=100)
        integration_list.add_argument("--cursor")
        integration_list.add_argument("--include-inactive", action="store_true")
        integration_list.set_defaults(handler=self._handle_discovery_integration_profile_list)

        integration_delete = discovery_subparsers.add_parser(
            "integration-profile-delete", help="disable a discovery integration profile"
        )
        self._add_backend_arguments(integration_delete)
        integration_delete.add_argument("--tenant", required=True)
        integration_delete.add_argument("--actor", default="cli")
        integration_delete.add_argument("--admin-token", required=True)
        integration_delete.add_argument("--profile-id", required=True)
        integration_delete.add_argument("--reason", required=True)
        integration_delete.set_defaults(handler=self._handle_discovery_integration_profile_delete)

        evidence_submit = discovery_subparsers.add_parser(
            "evidence-submit",
            help="store immutable discovery evidence without mutating the RSOT",
        )
        self._add_backend_arguments(evidence_submit)
        evidence_submit.add_argument("--tenant", required=True)
        evidence_submit.add_argument("--actor", default="cli")
        evidence_submit.add_argument("--admin-token", required=True)
        evidence_submit.add_argument("--evidence-id")
        evidence_submit.add_argument("--object-key", required=True)
        evidence_submit.add_argument("--object-kind", required=True)
        evidence_submit.add_argument(
            "--source",
            choices=(
                "snmp",
                "ssh",
                "winrm",
                "vmware",
                "proxmox",
                "hyperv",
                "kubernetes",
                "aws",
                "azure",
                "gcp",
                "openstack",
                "cloud",
                "import",
                "manual",
            ),
            required=True,
        )
        evidence_submit.add_argument("--source-ref", required=True)
        evidence_submit.add_argument("--scope", required=True)
        evidence_submit.add_argument("--external-id", required=True)
        evidence_submit.add_argument("--confidence", required=True, type=float)
        evidence_submit.add_argument("--payload-json", required=True)
        evidence_submit.add_argument("--observed-at")
        evidence_submit.set_defaults(handler=self._handle_discovery_evidence_submit)

        evidence_get = discovery_subparsers.add_parser(
            "evidence", help="get immutable discovery evidence"
        )
        self._add_backend_arguments(evidence_get)
        evidence_get.add_argument("--tenant", required=True)
        evidence_get.add_argument("--admin-token", required=True)
        evidence_get.add_argument("--evidence-id", required=True)
        evidence_get.set_defaults(handler=self._handle_discovery_evidence_get)

        evidence_list = discovery_subparsers.add_parser(
            "evidence-list", help="list immutable discovery evidence"
        )
        self._add_backend_arguments(evidence_list)
        evidence_list.add_argument("--tenant", required=True)
        evidence_list.add_argument("--admin-token", required=True)
        evidence_list.add_argument("--object-key")
        evidence_list.add_argument("--limit", type=int, default=100)
        evidence_list.add_argument("--cursor")
        evidence_list.set_defaults(handler=self._handle_discovery_evidence_list)

        reconcile = discovery_subparsers.add_parser(
            "reconcile",
            help="evaluate multisource discovery evidence and expose explicit conflicts",
        )
        self._add_backend_arguments(reconcile)
        reconcile.add_argument("--tenant", required=True)
        reconcile.add_argument("--actor", default="cli")
        reconcile.add_argument("--admin-token", required=True)
        reconcile.add_argument("--object-key", required=True)
        reconcile.add_argument("--evidence-id", action="append", required=True)
        reconcile.add_argument("--max-age-seconds", type=int, default=86_400)
        reconcile.set_defaults(handler=self._handle_discovery_reconcile)

        reconciliation_get = discovery_subparsers.add_parser(
            "reconciliation", help="get a discovery reconciliation case"
        )
        self._add_backend_arguments(reconciliation_get)
        reconciliation_get.add_argument("--tenant", required=True)
        reconciliation_get.add_argument("--admin-token", required=True)
        reconciliation_get.add_argument("--case-id", required=True)
        reconciliation_get.set_defaults(handler=self._handle_discovery_reconciliation_get)

        reconciliation_list = discovery_subparsers.add_parser(
            "reconciliation-list", help="list discovery reconciliation cases"
        )
        self._add_backend_arguments(reconciliation_list)
        reconciliation_list.add_argument("--tenant", required=True)
        reconciliation_list.add_argument("--admin-token", required=True)
        reconciliation_list.add_argument("--status", choices=("ready", "conflict", "resolved"))
        reconciliation_list.add_argument("--limit", type=int, default=100)
        reconciliation_list.add_argument("--cursor")
        reconciliation_list.set_defaults(handler=self._handle_discovery_reconciliation_list)

        reconciliation_resolve = discovery_subparsers.add_parser(
            "reconciliation-resolve",
            help="resolve every conflict with explicit evidence selections and justification",
        )
        self._add_backend_arguments(reconciliation_resolve)
        reconciliation_resolve.add_argument("--tenant", required=True)
        reconciliation_resolve.add_argument("--actor", default="cli")
        reconciliation_resolve.add_argument("--admin-token", required=True)
        reconciliation_resolve.add_argument("--case-id", required=True)
        reconciliation_resolve.add_argument("--selections-json", required=True)
        reconciliation_resolve.add_argument("--justification", required=True)
        reconciliation_resolve.set_defaults(handler=self._handle_discovery_reconciliation_resolve)

        register = discovery_subparsers.add_parser(
            "collector-register", help="register an authorized discovery collector"
        )
        self._add_backend_arguments(register)
        register.add_argument("--tenant", required=True)
        register.add_argument("--actor", default="cli")
        register.add_argument("--admin-token", required=True)
        register.add_argument("--name", required=True)
        register.add_argument("--kind", required=True)
        register.add_argument("--certificate-fingerprint", required=True)
        register.add_argument("--scope", action="append", required=True)
        register.add_argument("--version", required=True)
        register.add_argument("--vault-secret-ref")
        register.add_argument("--endpoint-url")
        register.set_defaults(handler=self._handle_discovery_collector_register)

        enroll = discovery_subparsers.add_parser(
            "proxy-enroll",
            help="enroll an Enterprise discovery proxy directly against one or more backends",
        )
        enroll.add_argument(
            "--backend-url",
            action="append",
            required=True,
            help="OpenInfra backend URL; repeat for HA backend enrollment",
        )
        enroll.add_argument(
            "--edition",
            choices=("lite", "pro", "enterprise"),
            default=os.environ.get("OPENINFRA_EDITION", "enterprise"),
        )
        enroll.add_argument("--tenant", required=True)
        enroll.add_argument("--actor", default="proxy-cli")
        enroll.add_argument("--admin-token", required=True)
        enroll.add_argument("--name", required=True)
        enroll.add_argument(
            "--kind",
            choices=("site-proxy", "network-proxy", "datacenter-proxy"),
            default="site-proxy",
        )
        enroll.add_argument("--certificate-fingerprint", required=True)
        enroll.add_argument("--scope", action="append", required=True)
        enroll.add_argument("--version", required=True)
        enroll.add_argument("--endpoint-url", required=True)
        enroll.add_argument("--vault-secret-ref")
        enroll.add_argument("--timeout-seconds", type=float, default=10.0)
        enroll.add_argument("--config-output", type=Path)
        enroll.set_defaults(handler=self._handle_discovery_proxy_enroll)

        enroll_local = discovery_subparsers.add_parser(
            "proxy-enroll-local",
            help="enroll an Enterprise discovery proxy into the selected backend store",
        )
        self._add_backend_arguments(enroll_local)
        enroll_local.add_argument("--tenant", required=True)
        enroll_local.add_argument("--actor", default="proxy-cli")
        enroll_local.add_argument("--admin-token", required=True)
        enroll_local.add_argument("--name", required=True)
        enroll_local.add_argument(
            "--kind",
            choices=("site-proxy", "network-proxy", "datacenter-proxy"),
            default="site-proxy",
        )
        enroll_local.add_argument("--certificate-fingerprint", required=True)
        enroll_local.add_argument("--scope", action="append", required=True)
        enroll_local.add_argument("--version", required=True)
        enroll_local.add_argument("--endpoint-url", required=True)
        enroll_local.add_argument("--vault-secret-ref")
        enroll_local.set_defaults(handler=self._handle_discovery_proxy_enroll_local)

        enroll_verify = discovery_subparsers.add_parser(
            "proxy-enroll-verify",
            help="validate a generated Enterprise discovery proxy enrollment config",
        )
        enroll_verify.add_argument(
            "--edition",
            choices=("lite", "pro", "enterprise"),
            default=os.environ.get("OPENINFRA_EDITION", "enterprise"),
        )
        enroll_verify.add_argument("--config", type=Path, required=True)
        enroll_verify.add_argument(
            "--allow-partial",
            action="store_true",
            help="report partial backend enrollment as a warning instead of an error",
        )
        enroll_verify.set_defaults(handler=self._handle_discovery_proxy_enroll_verify)

        agent_bootstrap = discovery_subparsers.add_parser(
            "agent-bootstrap-plan",
            help="build an Enterprise openinfra-agent.service bootstrap plan",
        )
        self._add_backend_arguments(agent_bootstrap)
        agent_bootstrap.add_argument("--tenant", required=True)
        agent_bootstrap.add_argument("--actor", default="cli")
        agent_bootstrap.add_argument("--admin-token", required=True)
        agent_bootstrap.add_argument("--name", required=True)
        agent_bootstrap.add_argument(
            "--role", choices=("site", "regional", "datacenter"), default="site"
        )
        agent_bootstrap.add_argument("--scope", action="append", required=True)
        agent_bootstrap.add_argument("--backend-url", required=True)
        agent_bootstrap.add_argument("--certificate-fingerprint", required=True)
        agent_bootstrap.add_argument("--enrollment-secret-ref", required=True)
        agent_bootstrap.add_argument("--agent-version", default=__version__)
        agent_bootstrap.add_argument("--service-user", default="openinfra-agent")
        agent_bootstrap.add_argument("--config-path", default="/etc/openinfra/agent.yaml")
        agent_bootstrap.add_argument("--state-directory", default="/var/lib/openinfra-agent")
        agent_bootstrap.add_argument("--log-directory", default="/var/log/openinfra-agent")
        agent_bootstrap.set_defaults(handler=self._handle_discovery_agent_bootstrap_plan)

        heartbeat = discovery_subparsers.add_parser(
            "collector-heartbeat", help="record collector heartbeat using strong identity"
        )
        self._add_backend_arguments(heartbeat)
        heartbeat.add_argument("--tenant", required=True)
        heartbeat.add_argument("--collector-id", required=True)
        heartbeat.add_argument("--certificate-fingerprint", required=True)
        heartbeat.add_argument("--version", required=True)
        heartbeat.add_argument("--status", choices=("ok", "degraded", "maintenance"), default="ok")
        heartbeat.set_defaults(handler=self._handle_discovery_collector_heartbeat)

        authorize = discovery_subparsers.add_parser(
            "job-authorize", help="authorize or reject a discovery job for a collector"
        )
        self._add_backend_arguments(authorize)
        authorize.add_argument("--tenant", required=True)
        authorize.add_argument("--collector-id", required=True)
        authorize.add_argument("--certificate-fingerprint", required=True)
        authorize.add_argument("--requested-scope", required=True)
        authorize.add_argument("--job-type", required=True)
        authorize.add_argument("--target", required=True)
        authorize.set_defaults(handler=self._handle_discovery_job_authorize)

        job_submit = discovery_subparsers.add_parser(
            "job-submit", help="submit an idempotent discovery job to a collector queue"
        )
        self._add_backend_arguments(job_submit)
        job_submit.add_argument("--tenant", required=True)
        job_submit.add_argument("--actor", default="cli")
        job_submit.add_argument("--admin-token", required=True)
        job_submit.add_argument("--collector-id", required=True)
        job_submit.add_argument("--requested-scope", required=True)
        job_submit.add_argument("--job-type", required=True)
        job_submit.add_argument("--target", required=True)
        job_submit.add_argument("--idempotency-key", required=True)
        job_submit.add_argument("--max-attempts", type=int, default=3)
        job_submit.set_defaults(handler=self._handle_discovery_job_submit)

        job_claim = discovery_subparsers.add_parser(
            "job-claim", help="atomically claim or reclaim the next discovery job"
        )
        self._add_backend_arguments(job_claim)
        job_claim.add_argument("--tenant", required=True)
        job_claim.add_argument("--collector-id", required=True)
        job_claim.add_argument("--certificate-fingerprint", required=True)
        job_claim.add_argument("--worker-id", required=True)
        job_claim.add_argument("--lease-seconds", type=int, default=60)
        job_claim.set_defaults(handler=self._handle_discovery_job_claim)

        job_renew = discovery_subparsers.add_parser(
            "job-renew", help="renew a discovery job lease using its fencing token"
        )
        self._add_backend_arguments(job_renew)
        job_renew.add_argument("--tenant", required=True)
        job_renew.add_argument("--collector-id", required=True)
        job_renew.add_argument("--certificate-fingerprint", required=True)
        job_renew.add_argument("--job-id", required=True)
        job_renew.add_argument("--worker-id", required=True)
        job_renew.add_argument("--lease-token", type=int, required=True)
        job_renew.add_argument("--lease-seconds", type=int, default=60)
        job_renew.set_defaults(handler=self._handle_discovery_job_renew)

        job_complete = discovery_subparsers.add_parser(
            "job-complete", help="complete a discovery job idempotently"
        )
        self._add_backend_arguments(job_complete)
        job_complete.add_argument("--tenant", required=True)
        job_complete.add_argument("--collector-id", required=True)
        job_complete.add_argument("--certificate-fingerprint", required=True)
        job_complete.add_argument("--job-id", required=True)
        job_complete.add_argument("--worker-id", required=True)
        job_complete.add_argument("--lease-token", type=int, required=True)
        job_complete.add_argument("--result-hash", required=True)
        job_complete.set_defaults(handler=self._handle_discovery_job_complete)

        job_fail = discovery_subparsers.add_parser(
            "job-fail", help="schedule retry or dead-letter an exhausted discovery job"
        )
        self._add_backend_arguments(job_fail)
        job_fail.add_argument("--tenant", required=True)
        job_fail.add_argument("--collector-id", required=True)
        job_fail.add_argument("--certificate-fingerprint", required=True)
        job_fail.add_argument("--job-id", required=True)
        job_fail.add_argument("--worker-id", required=True)
        job_fail.add_argument("--lease-token", type=int, required=True)
        job_fail.add_argument("--error", required=True)
        job_fail.add_argument("--retry-delay-seconds", type=int, default=30)
        job_fail.set_defaults(handler=self._handle_discovery_job_fail)

        job_get = discovery_subparsers.add_parser("job", help="get a persisted discovery job")
        self._add_backend_arguments(job_get)
        job_get.add_argument("--tenant", required=True)
        job_get.add_argument("--admin-token", required=True)
        job_get.add_argument("--job-id", required=True)
        job_get.set_defaults(handler=self._handle_discovery_job_get)

        job_list = discovery_subparsers.add_parser(
            "job-list", help="list discovery jobs, including retry and DLQ states"
        )
        self._add_backend_arguments(job_list)
        job_list.add_argument("--tenant", required=True)
        job_list.add_argument("--admin-token", required=True)
        job_list.add_argument(
            "--status",
            choices=("queued", "leased", "retry-wait", "completed", "dead-letter"),
        )
        job_list.add_argument("--limit", type=int, default=100)
        job_list.add_argument("--cursor")
        job_list.set_defaults(handler=self._handle_discovery_job_list)

        job_replay = discovery_subparsers.add_parser(
            "job-replay", help="requeue a dead-letter discovery job with audit trace"
        )
        self._add_backend_arguments(job_replay)
        job_replay.add_argument("--tenant", required=True)
        job_replay.add_argument("--actor", default="cli")
        job_replay.add_argument("--admin-token", required=True)
        job_replay.add_argument("--job-id", required=True)
        job_replay.set_defaults(handler=self._handle_discovery_job_replay)

        disable = discovery_subparsers.add_parser(
            "collector-disable", help="disable a discovery collector"
        )
        self._add_backend_arguments(disable)
        disable.add_argument("--tenant", required=True)
        disable.add_argument("--actor", default="cli")
        disable.add_argument("--admin-token", required=True)
        disable.add_argument("--collector-id", required=True)
        disable.add_argument("--reason", required=True)
        disable.set_defaults(handler=self._handle_discovery_collector_disable)

        list_collectors = discovery_subparsers.add_parser(
            "collector-list", help="list registered discovery collectors"
        )
        self._add_backend_arguments(list_collectors)
        list_collectors.add_argument("--tenant", required=True)
        list_collectors.add_argument("--admin-token", required=True)
        list_collectors.add_argument("--limit", type=int, default=100)
        list_collectors.add_argument("--cursor")
        list_collectors.add_argument("--include-inactive", action="store_true")
        list_collectors.set_defaults(handler=self._handle_discovery_collector_list)

        local_plan = discovery_subparsers.add_parser(
            "local-plan",
            help="build a Lite/Pro local discovery plan without agent or RSOT mutation",
        )
        self._add_backend_arguments(local_plan)
        local_plan.add_argument("--tenant", required=True)
        local_plan.add_argument("--actor", default="cli")
        local_plan.add_argument("--admin-token", required=True)
        local_plan.add_argument("--name", required=True)
        local_plan.add_argument("--scope", required=True)
        local_plan.add_argument("--protocol", choices=("snmp", "ssh", "winrm"), required=True)
        local_plan.add_argument("--target", action="append", required=True)
        local_plan.add_argument("--credential-secret-ref", required=True)
        local_plan.add_argument("--protocol-profile-id")
        local_plan.add_argument("--max-concurrency", type=int, default=4)
        local_plan.add_argument("--rate-limit-per-minute", type=int, default=120)
        local_plan.set_defaults(handler=self._handle_discovery_local_plan)

    def _add_export_commands(self, subparsers: Any) -> None:
        exports = subparsers.add_parser("export", help="asynchronous signed export operations")
        export_subparsers = exports.add_subparsers(dest="export_command", required=True)

        request = export_subparsers.add_parser(
            "request", help="queue a signed asynchronous export job"
        )
        self._add_backend_arguments(request)
        request.add_argument("--tenant", required=True)
        request.add_argument("--actor", default="cli")
        request.add_argument("--admin-token", required=True)
        request.add_argument("--resource", choices=("source_objects",), default="source_objects")
        request.add_argument("--format", choices=("csv", "json", "xlsx"), default="json")
        request.add_argument("--kind")
        request.add_argument("--tag")
        request.add_argument("--limit", type=int, default=100_000)
        request.set_defaults(handler=self._handle_export_request)

        run = export_subparsers.add_parser(
            "run", help="run one queued export job as a worker action"
        )
        self._add_backend_arguments(run)
        run.add_argument("--tenant", required=True)
        run.add_argument("--actor", default="cli")
        run.add_argument("--admin-token", required=True)
        run.add_argument("--job-id")
        run.add_argument("--page-size", type=int, default=500)
        run.set_defaults(handler=self._handle_export_run)

        report = export_subparsers.add_parser("report", help="read an export job report")
        self._add_backend_arguments(report)
        report.add_argument("--tenant", required=True)
        report.add_argument("--admin-token", required=True)
        report.add_argument("--job-id", required=True)
        report.set_defaults(handler=self._handle_export_report)

        artifact = export_subparsers.add_parser(
            "artifact", help="download and verify an export artifact"
        )
        self._add_backend_arguments(artifact)
        artifact.add_argument("--tenant", required=True)
        artifact.add_argument("--admin-token", required=True)
        artifact.add_argument("--job-id", required=True)
        artifact.add_argument("--output", type=Path, required=True)
        artifact.set_defaults(handler=self._handle_export_artifact)

        artifact_chunk = export_subparsers.add_parser(
            "artifact-chunk", help="download and verify one signed artifact byte chunk"
        )
        self._add_backend_arguments(artifact_chunk)
        artifact_chunk.add_argument("--tenant", required=True)
        artifact_chunk.add_argument("--admin-token", required=True)
        artifact_chunk.add_argument("--job-id", required=True)
        artifact_chunk.add_argument("--offset", type=int, default=0)
        artifact_chunk.add_argument("--size", type=int, default=65_536)
        artifact_chunk.add_argument("--output", type=Path)
        artifact_chunk.set_defaults(handler=self._handle_export_artifact_chunk)

    def _add_graph_commands(self, subparsers: Any) -> None:
        graph = subparsers.add_parser(
            "graph", help="tenant-aware RSOT dependency graph and impact analysis"
        )
        graph_subparsers = graph.add_subparsers(dest="graph_command", required=True)

        traverse = graph_subparsers.add_parser(
            "traverse", help="traverse dependencies from a root RSOT object"
        )
        self._add_backend_arguments(traverse)
        self._add_graph_common_arguments(traverse, default_direction="both", default_depth=3)
        traverse.add_argument("--root-key", required=True)
        traverse.set_defaults(handler=self._handle_graph_traverse)

        impact = graph_subparsers.add_parser(
            "impact", help="analyze direct and indirect impact around an RSOT object"
        )
        self._add_backend_arguments(impact)
        self._add_graph_common_arguments(impact, default_direction="incoming", default_depth=6)
        impact.add_argument("--root-key", required=True)
        impact.set_defaults(handler=self._handle_graph_impact)

        path = graph_subparsers.add_parser(
            "path", help="find the shortest dependency path between two RSOT objects"
        )
        self._add_backend_arguments(path)
        self._add_graph_common_arguments(path, default_direction="outgoing", default_depth=8)
        path.add_argument("--source-key", required=True)
        path.add_argument("--target-key", required=True)
        path.set_defaults(handler=self._handle_graph_path)

        spof = graph_subparsers.add_parser(
            "spof", help="identify single points of failure with rooted dominator analysis"
        )
        self._add_backend_arguments(spof)
        self._add_graph_common_arguments(spof, default_direction="both", default_depth=8)
        spof.add_argument("--root-key", required=True)
        self._add_graph_spof_filter_arguments(spof, include_pagination=True)
        spof.set_defaults(handler=self._handle_graph_spof)

        export = graph_subparsers.add_parser(
            "export", help="export a dependency graph as JSON, CSV or GraphML"
        )
        self._add_backend_arguments(export)
        self._add_graph_common_arguments(export, default_direction="both", default_depth=8)
        export.add_argument("--root-key", required=True)
        export.add_argument("--format", choices=("json", "csv", "graphml"), default="json")
        export.add_argument(
            "--include-spof",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="annotate exported nodes with SPOF impact counts",
        )
        export.add_argument("--output", type=Path)
        self._add_graph_spof_filter_arguments(export, include_pagination=False)
        export.set_defaults(handler=self._handle_graph_export)

    def _add_simulation_commands(self, subparsers: Any) -> None:
        simulation = subparsers.add_parser(
            "simulation",
            help="RSOT change and migration impact simulation without production mutation",
        )
        commands = simulation.add_subparsers(dest="simulation_command", required=True)

        create = commands.add_parser("create", help="create an immutable simulation scenario")
        self._add_backend_arguments(create)
        create.add_argument("--tenant", required=True)
        create.add_argument("--actor", default="cli")
        create.add_argument("--admin-token", required=True)
        create.add_argument("--name", required=True)
        create.add_argument("--description", required=True)
        create.add_argument("--owner", required=True)
        create.add_argument("--idempotency-key", required=True)
        create.add_argument("--changes-file", type=Path, required=True)
        create.add_argument("--site")
        create.add_argument("--environment")
        create.add_argument("--criticality")
        create.set_defaults(handler=self._handle_simulation_create)

        listing = commands.add_parser("list", help="list simulation scenarios")
        self._add_backend_arguments(listing)
        listing.add_argument("--tenant", required=True)
        listing.add_argument("--admin-token", required=True)
        listing.add_argument("--limit", type=int, default=100)
        listing.add_argument("--cursor")
        listing.add_argument("--status")
        listing.add_argument("--site")
        listing.set_defaults(handler=self._handle_simulation_list)

        get = commands.add_parser("get", help="read a simulation scenario")
        self._add_backend_arguments(get)
        get.add_argument("--tenant", required=True)
        get.add_argument("--admin-token", required=True)
        get.add_argument("--scenario-id", required=True)
        get.set_defaults(handler=self._handle_simulation_get)

        run = commands.add_parser("run", help="generate an impact report for a scenario")
        self._add_backend_arguments(run)
        run.add_argument("--tenant", required=True)
        run.add_argument("--actor", default="cli")
        run.add_argument("--admin-token", required=True)
        run.add_argument("--scenario-id", required=True)
        run.add_argument("--max-depth", type=int, default=8)
        run.add_argument("--max-nodes", type=int, default=2000)
        run.set_defaults(handler=self._handle_simulation_run)

        cancel = commands.add_parser("cancel", help="cancel a non-terminal simulation scenario")
        self._add_backend_arguments(cancel)
        cancel.add_argument("--tenant", required=True)
        cancel.add_argument("--actor", default="cli")
        cancel.add_argument("--admin-token", required=True)
        cancel.add_argument("--scenario-id", required=True)
        cancel.set_defaults(handler=self._handle_simulation_cancel)

        report = commands.add_parser("report", help="read a simulation impact report")
        self._add_backend_arguments(report)
        report.add_argument("--tenant", required=True)
        report.add_argument("--admin-token", required=True)
        report.add_argument("--report-id", required=True)
        report.set_defaults(handler=self._handle_simulation_report)

        reports = commands.add_parser("reports", help="list simulation impact reports")
        self._add_backend_arguments(reports)
        reports.add_argument("--tenant", required=True)
        reports.add_argument("--admin-token", required=True)
        reports.add_argument("--scenario-id")
        reports.add_argument("--limit", type=int, default=100)
        reports.add_argument("--cursor")
        reports.set_defaults(handler=self._handle_simulation_reports)

        compare = commands.add_parser("compare", help="compare two impact reports")
        self._add_backend_arguments(compare)
        compare.add_argument("--tenant", required=True)
        compare.add_argument("--actor", default="cli")
        compare.add_argument("--admin-token", required=True)
        compare.add_argument("--left-report-id", required=True)
        compare.add_argument("--right-report-id", required=True)
        compare.set_defaults(handler=self._handle_simulation_compare)

        comparisons = commands.add_parser("comparisons", help="list report comparisons")
        self._add_backend_arguments(comparisons)
        comparisons.add_argument("--tenant", required=True)
        comparisons.add_argument("--admin-token", required=True)
        comparisons.add_argument("--limit", type=int, default=100)
        comparisons.add_argument("--cursor")
        comparisons.set_defaults(handler=self._handle_simulation_comparisons)

    def _add_graph_spof_filter_arguments(
        self, parser: argparse.ArgumentParser, *, include_pagination: bool
    ) -> None:
        parser.add_argument("--candidate-kind", action="append", default=[])
        parser.add_argument("--candidate-resource-category", action="append", default=[])
        parser.add_argument("--candidate-resource-type", action="append", default=[])
        parser.add_argument("--candidate-status", action="append", default=[])
        parser.add_argument("--minimum-affected-nodes", type=int, default=1)
        if include_pagination:
            parser.add_argument("--affected-sample-limit", type=int, default=25)
            parser.add_argument("--limit", type=int, default=100)
            parser.add_argument("--cursor")

    def _add_graph_common_arguments(
        self,
        parser: argparse.ArgumentParser,
        *,
        default_direction: str,
        default_depth: int,
    ) -> None:
        parser.add_argument("--tenant", required=True)
        parser.add_argument("--admin-token", required=True)
        parser.add_argument(
            "--direction",
            choices=("outgoing", "incoming", "both"),
            default=default_direction,
        )
        parser.add_argument("--max-depth", type=int, default=default_depth)
        parser.add_argument("--max-nodes", type=int, default=1000)
        parser.add_argument("--relation-type", action="append", default=[])
        parser.add_argument("--as-of")

    def _add_network_config_commands(self, subparsers: Any) -> None:
        network_config = subparsers.add_parser(
            "network-config", help="network golden configuration compliance operations"
        )
        commands = network_config.add_subparsers(dest="network_config_command", required=True)

        baseline = commands.add_parser(
            "baseline-upsert", help="create or revise a golden configuration baseline"
        )
        self._add_backend_arguments(baseline)
        baseline.add_argument("--tenant", required=True)
        baseline.add_argument("--actor", default="cli")
        baseline.add_argument("--admin-token", required=True)
        baseline.add_argument("--code", required=True)
        baseline.add_argument("--device-object-key", required=True)
        baseline.add_argument("--platform", required=True)
        baseline.add_argument("--expected-config-file", type=Path, required=True)
        baseline.add_argument("--ignored-path", action="append", default=[])
        baseline.add_argument("--critical-path", action="append", default=[])
        baseline.add_argument("--owner", required=True)
        baseline.add_argument("--justification", required=True)
        baseline.set_defaults(handler=self._handle_network_config_baseline_upsert)

        baseline_list = commands.add_parser(
            "baseline-list", help="list golden configuration baselines"
        )
        self._add_backend_arguments(baseline_list)
        baseline_list.add_argument("--tenant", required=True)
        baseline_list.add_argument("--admin-token", required=True)
        baseline_list.add_argument("--limit", type=int, default=100)
        baseline_list.add_argument("--cursor")
        baseline_list.add_argument("--include-retired", action="store_true")
        baseline_list.set_defaults(handler=self._handle_network_config_baseline_list)

        retire = commands.add_parser(
            "baseline-retire", help="retire a golden configuration baseline"
        )
        self._add_backend_arguments(retire)
        retire.add_argument("--tenant", required=True)
        retire.add_argument("--actor", default="cli")
        retire.add_argument("--admin-token", required=True)
        retire.add_argument("--baseline-id", required=True)
        retire.set_defaults(handler=self._handle_network_config_baseline_retire)

        observation = commands.add_parser(
            "observation-submit", help="ingest one immutable discovered network configuration"
        )
        self._add_backend_arguments(observation)
        observation.add_argument("--tenant", required=True)
        observation.add_argument("--actor", default="cli")
        observation.add_argument("--admin-token", required=True)
        observation.add_argument("--idempotency-key", required=True)
        observation.add_argument(
            "--source",
            choices=("ssh", "api", "netconf", "restconf", "gnmi", "discovery", "import", "manual"),
            required=True,
        )
        observation.add_argument("--collector", required=True)
        observation.add_argument("--device-object-key", required=True)
        observation.add_argument("--platform", required=True)
        observation.add_argument("--observed-config-file", type=Path, required=True)
        observation.add_argument("--observed-at", required=True)
        observation.set_defaults(handler=self._handle_network_config_observation_submit)

        observation_list = commands.add_parser(
            "observation-list", help="list discovered network configurations"
        )
        self._add_backend_arguments(observation_list)
        observation_list.add_argument("--tenant", required=True)
        observation_list.add_argument("--admin-token", required=True)
        observation_list.add_argument("--limit", type=int, default=100)
        observation_list.add_argument("--cursor")
        observation_list.add_argument("--device-object-key")
        observation_list.add_argument("--platform")
        observation_list.add_argument("--observed-before")
        observation_list.set_defaults(handler=self._handle_network_config_observation_list)

        assess = commands.add_parser(
            "assess", help="compare golden and discovered network configurations"
        )
        self._add_backend_arguments(assess)
        assess.add_argument("--tenant", required=True)
        assess.add_argument("--actor", default="cli")
        assess.add_argument("--admin-token", required=True)
        assess.add_argument("--baseline-code")
        assess.add_argument("--as-of")
        assess.add_argument("--status", choices=("compliant", "drift", "missing-observation"))
        assess.add_argument("--limit", type=int, default=100)
        assess.add_argument("--cursor")
        assess.set_defaults(handler=self._handle_network_config_assess)

    def _add_certificate_commands(self, subparsers: Any) -> None:
        certificate = subparsers.add_parser(
            "certificate", help="certificate and PKI inventory operations"
        )
        commands = certificate.add_subparsers(dest="certificate_command", required=True)

        import_bundle = commands.add_parser(
            "import", help="import and cryptographically validate a PEM certificate chain"
        )
        self._add_backend_arguments(import_bundle)
        import_bundle.add_argument("--tenant", required=True)
        import_bundle.add_argument("--actor", default="cli")
        import_bundle.add_argument("--admin-token", required=True)
        import_bundle.add_argument("--pem-file", type=Path, required=True)
        import_bundle.add_argument("--owner", required=True)
        import_bundle.add_argument("--environment", required=True)
        import_bundle.add_argument(
            "--source",
            choices=("manual", "discovery", "import", "acme", "internal-pki", "external-pki"),
            required=True,
        )
        import_bundle.add_argument("--object-key")
        import_bundle.set_defaults(handler=self._handle_certificate_import)

        get = commands.add_parser("get", help="get one certificate by SHA-256 fingerprint")
        self._add_backend_arguments(get)
        get.add_argument("--tenant", required=True)
        get.add_argument("--admin-token", required=True)
        get.add_argument("--fingerprint", required=True)
        get.set_defaults(handler=self._handle_certificate_get)

        list_certificates = commands.add_parser("list", help="list certificate inventory")
        self._add_backend_arguments(list_certificates)
        list_certificates.add_argument("--tenant", required=True)
        list_certificates.add_argument("--admin-token", required=True)
        list_certificates.add_argument("--limit", type=int, default=100)
        list_certificates.add_argument("--cursor")
        list_certificates.add_argument("--include-retired", action="store_true")
        list_certificates.set_defaults(handler=self._handle_certificate_list)

        retire = commands.add_parser("retire", help="retire a certificate inventory record")
        self._add_backend_arguments(retire)
        retire.add_argument("--tenant", required=True)
        retire.add_argument("--actor", default="cli")
        retire.add_argument("--admin-token", required=True)
        retire.add_argument("--fingerprint", required=True)
        retire.set_defaults(handler=self._handle_certificate_retire)

        observe = commands.add_parser(
            "endpoint-observe", help="record an immutable certificate endpoint observation"
        )
        self._add_backend_arguments(observe)
        observe.add_argument("--tenant", required=True)
        observe.add_argument("--actor", default="cli")
        observe.add_argument("--admin-token", required=True)
        observe.add_argument("--idempotency-key", required=True)
        observe.add_argument("--protocol", required=True)
        observe.add_argument("--host", required=True)
        observe.add_argument("--port", type=int, required=True)
        observe.add_argument("--service", required=True)
        observe.add_argument("--certificate-fingerprint", required=True)
        observe.add_argument("--observed-at", required=True)
        observe.add_argument(
            "--source",
            choices=("manual", "discovery", "import", "acme", "internal-pki", "external-pki"),
            required=True,
        )
        observe.add_argument("--collector", required=True)
        observe.add_argument("--object-key")
        observe.add_argument("--tls-version")
        observe.add_argument("--cipher")
        observe.set_defaults(handler=self._handle_certificate_endpoint_observe)

        endpoint_list = commands.add_parser(
            "endpoint-list", help="list certificate endpoint observations"
        )
        self._add_backend_arguments(endpoint_list)
        endpoint_list.add_argument("--tenant", required=True)
        endpoint_list.add_argument("--admin-token", required=True)
        endpoint_list.add_argument("--certificate-fingerprint")
        endpoint_list.add_argument("--limit", type=int, default=100)
        endpoint_list.add_argument("--cursor")
        endpoint_list.set_defaults(handler=self._handle_certificate_endpoint_list)

        assess = commands.add_parser(
            "assess", help="assess expiration, chain completeness and hostname coverage"
        )
        self._add_backend_arguments(assess)
        assess.add_argument("--tenant", required=True)
        assess.add_argument("--admin-token", required=True)
        assess.add_argument("--as-of")
        assess.add_argument("--critical-days", type=int, default=7)
        assess.add_argument("--warning-days", type=int, default=30)
        assess.add_argument(
            "--health",
            choices=("retired", "not-yet-valid", "expired", "critical", "warning", "healthy"),
        )
        assess.add_argument("--limit", type=int, default=100)
        assess.add_argument("--cursor")
        assess.set_defaults(handler=self._handle_certificate_assess)

    def _add_flow_commands(self, subparsers: Any) -> None:
        flow = subparsers.add_parser(
            "flow", help="declared and observed network flow matrix operations"
        )
        commands = flow.add_subparsers(dest="flow_command", required=True)

        declare = commands.add_parser(
            "declaration-upsert", help="create or revise a governed flow declaration"
        )
        self._add_backend_arguments(declare)
        declare.add_argument("--tenant", required=True)
        declare.add_argument("--actor", default="cli")
        declare.add_argument("--admin-token", required=True)
        declare.add_argument("--code", required=True)
        declare.add_argument("--source-selector", required=True)
        declare.add_argument("--destination-selector", required=True)
        declare.add_argument(
            "--protocol",
            choices=("any", "tcp", "udp", "sctp", "icmp", "icmpv6", "esp", "ah", "gre"),
            required=True,
        )
        declare.add_argument("--destination-port-start", type=int)
        declare.add_argument("--destination-port-end", type=int)
        declare.add_argument("--decision", choices=("allow", "deny"), required=True)
        declare.add_argument("--priority", type=int, default=100)
        declare.add_argument("--owner", required=True)
        declare.add_argument("--justification", required=True)
        declare.add_argument("--valid-from")
        declare.add_argument("--valid-to")
        declare.set_defaults(handler=self._handle_flow_declaration_upsert)

        declaration_list = commands.add_parser(
            "declaration-list", help="list governed flow declarations"
        )
        self._add_backend_arguments(declaration_list)
        declaration_list.add_argument("--tenant", required=True)
        declaration_list.add_argument("--admin-token", required=True)
        declaration_list.add_argument("--limit", type=int, default=100)
        declaration_list.add_argument("--cursor")
        declaration_list.add_argument("--include-retired", action="store_true")
        declaration_list.set_defaults(handler=self._handle_flow_declaration_list)

        retire = commands.add_parser(
            "declaration-retire", help="retire a governed flow declaration"
        )
        self._add_backend_arguments(retire)
        retire.add_argument("--tenant", required=True)
        retire.add_argument("--actor", default="cli")
        retire.add_argument("--admin-token", required=True)
        retire.add_argument("--declaration-id", required=True)
        retire.set_defaults(handler=self._handle_flow_declaration_retire)

        observe = commands.add_parser(
            "observation-submit", help="ingest one immutable idempotent observed network flow"
        )
        self._add_backend_arguments(observe)
        observe.add_argument("--tenant", required=True)
        observe.add_argument("--actor", default="cli")
        observe.add_argument("--admin-token", required=True)
        observe.add_argument("--idempotency-key", required=True)
        observe.add_argument(
            "--source",
            choices=(
                "netflow",
                "sflow",
                "ipfix",
                "firewall-log",
                "application-log",
                "import",
                "manual",
            ),
            required=True,
        )
        observe.add_argument("--collector", required=True)
        observe.add_argument("--source-ip", required=True)
        observe.add_argument("--destination-ip", required=True)
        observe.add_argument("--source-object-key")
        observe.add_argument("--destination-object-key")
        observe.add_argument(
            "--protocol",
            choices=("tcp", "udp", "sctp", "icmp", "icmpv6", "esp", "ah", "gre"),
            required=True,
        )
        observe.add_argument("--destination-port", type=int)
        observe.add_argument("--packets", type=int, required=True)
        observe.add_argument("--bytes", dest="bytes_count", type=int, required=True)
        observe.add_argument("--first-seen", required=True)
        observe.add_argument("--last-seen", required=True)
        observe.set_defaults(handler=self._handle_flow_observation_submit)

        observation_list = commands.add_parser(
            "observation-list", help="list observed network flows in a bounded time window"
        )
        self._add_backend_arguments(observation_list)
        observation_list.add_argument("--tenant", required=True)
        observation_list.add_argument("--admin-token", required=True)
        observation_list.add_argument("--window-start", required=True)
        observation_list.add_argument("--window-end", required=True)
        observation_list.add_argument("--source")
        observation_list.add_argument("--limit", type=int, default=100)
        observation_list.add_argument("--cursor")
        observation_list.set_defaults(handler=self._handle_flow_observation_list)

        matrix = commands.add_parser(
            "matrix", help="compare declared and observed flows and expose violations"
        )
        self._add_backend_arguments(matrix)
        matrix.add_argument("--tenant", required=True)
        matrix.add_argument("--admin-token", required=True)
        matrix.add_argument("--window-start")
        matrix.add_argument("--window-end")
        matrix.add_argument(
            "--status",
            choices=(
                "compliant",
                "denied-observed",
                "undeclared-observed",
                "declared-unobserved",
            ),
        )
        matrix.add_argument("--source")
        matrix.add_argument("--limit", type=int, default=100)
        matrix.add_argument("--cursor")
        matrix.set_defaults(handler=self._handle_flow_matrix)

    def _add_rsot_commands(self, subparsers: Any) -> None:
        self._add_inventory_commands(
            subparsers,
            command_name="rsot",
            help_text="RSOT (Ressource Source of Truth) objects, relations and governance",
            command_dest="rsot_command",
            short_label="RSOT",
        )

    def _add_itrm_commands(self, subparsers: Any) -> None:
        self._add_inventory_commands(
            subparsers,
            command_name="itrm",
            help_text="deprecated legacy alias for RSOT commands",
            command_dest="itrm_command",
            short_label="RSOT legacy compatibility",
        )

    def _add_ri_commands(self, subparsers: Any) -> None:
        self._add_inventory_commands(
            subparsers,
            command_name="ri",
            help_text="legacy alias for RSOT commands",
            command_dest="ri_command",
            short_label="RSOT legacy compatibility",
        )

    def _add_sot_commands(self, subparsers: Any) -> None:
        self._add_inventory_commands(
            subparsers,
            command_name="sot",
            help_text="legacy alias for RSOT (Ressource Source of Truth) commands",
            command_dest="sot_command",
            short_label="SOT compatibility",
        )

    def _add_inventory_commands(
        self,
        subparsers: Any,
        command_name: str,
        help_text: str,
        command_dest: str,
        short_label: str,
    ) -> None:
        sot = subparsers.add_parser(command_name, help=help_text)
        sot_subparsers = sot.add_subparsers(dest=command_dest, required=True)
        taxonomy = sot_subparsers.add_parser(
            "resource-taxonomy",
            help=f"list supported {short_label} resource categories and category-filtered types",
        )
        taxonomy.set_defaults(handler=self._handle_sot_resource_taxonomy)
        upsert = sot_subparsers.add_parser(
            "upsert-object", help=f"create or update a {short_label} object"
        )
        self._add_backend_arguments(upsert)
        upsert.add_argument("--tenant", required=True)
        upsert.add_argument("--actor", default="cli")
        upsert.add_argument("--admin-token", required=True)
        upsert.add_argument("--key", required=True)
        upsert.add_argument(
            "--kind",
            choices=ResourceTaxonomy.category_values() + tuple(ResourceTaxonomy.LEGACY_KIND_MAP),
            help="resource category; legacy kind aliases remain accepted during migration",
        )
        upsert.add_argument(
            "--resource-category",
            choices=ResourceTaxonomy.category_values(),
            help="RSOT category used to filter compatible resource types",
        )
        upsert.add_argument(
            "--resource-type",
            choices=ResourceTaxonomy.all_type_values(),
            help="RSOT resource type allowed by the selected category",
        )
        upsert.add_argument("--display-name", required=True)
        upsert.add_argument("--attributes-json", default="{}")
        upsert.add_argument("--tag", action="append", default=[])
        upsert.add_argument("--source", required=True)
        upsert.set_defaults(handler=self._handle_sot_upsert_object)
        get_object = sot_subparsers.add_parser(
            "get-object", help=f"get a {short_label} object by key"
        )
        self._add_backend_arguments(get_object)
        get_object.add_argument("--tenant", required=True)
        get_object.add_argument("--admin-token", required=True)
        get_object.add_argument("--key", required=True)
        get_object.set_defaults(handler=self._handle_sot_get_object)
        list_objects = sot_subparsers.add_parser("list-objects", help=f"list {short_label} objects")
        self._add_backend_arguments(list_objects)
        list_objects.add_argument("--tenant", required=True)
        list_objects.add_argument("--admin-token", required=True)
        list_objects.add_argument("--limit", type=int, default=100)
        list_objects.add_argument("--cursor")
        list_objects.add_argument("--kind")
        list_objects.add_argument("--resource-category", choices=ResourceTaxonomy.category_values())
        list_objects.add_argument("--resource-type", choices=ResourceTaxonomy.all_type_values())
        list_objects.add_argument("--tag")
        list_objects.set_defaults(handler=self._handle_sot_list_objects)
        get_version = sot_subparsers.add_parser(
            "get-object-version", help=f"get a {short_label} object historical version"
        )
        self._add_backend_arguments(get_version)
        get_version.add_argument("--tenant", required=True)
        get_version.add_argument("--admin-token", required=True)
        get_version.add_argument("--key", required=True)
        get_version.add_argument("--version", type=int, required=True)
        get_version.set_defaults(handler=self._handle_sot_get_object_version)
        get_as_of = sot_subparsers.add_parser(
            "get-object-as-of", help=f"get a {short_label} object as it was at an ISO-8601 date"
        )
        self._add_backend_arguments(get_as_of)
        get_as_of.add_argument("--tenant", required=True)
        get_as_of.add_argument("--admin-token", required=True)
        get_as_of.add_argument("--key", required=True)
        get_as_of.add_argument("--as-of", required=True)
        get_as_of.set_defaults(handler=self._handle_sot_get_object_as_of)
        list_object_audit = sot_subparsers.add_parser(
            "list-object-audit", help=f"list audit records for a {short_label} object"
        )
        self._add_backend_arguments(list_object_audit)
        list_object_audit.add_argument("--tenant", required=True)
        list_object_audit.add_argument("--admin-token", required=True)
        list_object_audit.add_argument("--key", required=True)
        list_object_audit.add_argument("--limit", type=int, default=100)
        list_object_audit.add_argument("--cursor")
        list_object_audit.set_defaults(handler=self._handle_sot_list_object_audit)
        reconcile = sot_subparsers.add_parser(
            "reconcile-object",
            help=f"plan or apply a governed {short_label} object reconciliation",
        )
        self._add_backend_arguments(reconcile)
        reconcile.add_argument("--tenant", required=True)
        reconcile.add_argument("--actor", default="cli")
        reconcile.add_argument("--admin-token", required=True)
        reconcile.add_argument("--key", required=True)
        reconcile.add_argument("--attributes-json", required=True)
        reconcile.add_argument("--resource-category", choices=ResourceTaxonomy.category_values())
        reconcile.add_argument("--resource-type", choices=ResourceTaxonomy.all_type_values())
        reconcile.add_argument("--source", required=True)
        reconcile.add_argument("--display-name")
        reconcile.add_argument("--tag", action="append")
        reconcile.add_argument("--apply", action="store_true")
        reconcile.set_defaults(handler=self._handle_sot_reconcile_object)
        create_relation = sot_subparsers.add_parser(
            "create-relation", help=f"create a typed {short_label} relation"
        )
        self._add_backend_arguments(create_relation)
        create_relation.add_argument("--tenant", required=True)
        create_relation.add_argument("--actor", default="cli")
        create_relation.add_argument("--admin-token", required=True)
        create_relation.add_argument("--relation-type", required=True)
        create_relation.add_argument("--source-key", required=True)
        create_relation.add_argument("--target-key", required=True)
        create_relation.add_argument("--provenance", required=True)
        create_relation.set_defaults(handler=self._handle_sot_create_relation)
        list_relations = sot_subparsers.add_parser(
            "list-relations", help=f"list typed {short_label} relations"
        )
        self._add_backend_arguments(list_relations)
        list_relations.add_argument("--tenant", required=True)
        list_relations.add_argument("--admin-token", required=True)
        list_relations.add_argument("--limit", type=int, default=100)
        list_relations.add_argument("--cursor")
        list_relations.add_argument("--source-key")
        list_relations.add_argument("--target-key")
        list_relations.add_argument("--relation-type")
        list_relations.add_argument("--as-of")
        list_relations.set_defaults(handler=self._handle_sot_list_relations)
        governance_create = sot_subparsers.add_parser(
            "create-governance-rule",
            help=f"create or update a {short_label} authoritative source governance rule",
        )
        self._add_backend_arguments(governance_create)
        governance_create.add_argument("--tenant", required=True)
        governance_create.add_argument("--actor", default="cli")
        governance_create.add_argument("--admin-token", required=True)
        governance_create.add_argument("--name", required=True)
        governance_create.add_argument("--object-kind")
        governance_create.add_argument("--attribute-path", required=True)
        governance_create.add_argument("--authoritative-source", required=True)
        governance_create.add_argument("--priority", type=int, default=100)
        governance_create.add_argument("--freshness-seconds", type=int)
        governance_create.add_argument(
            "--conflict-strategy",
            choices=("reject", "accept_with_audit"),
            default="reject",
        )
        governance_create.set_defaults(handler=self._handle_sot_create_governance_rule)
        governance_list = sot_subparsers.add_parser(
            "list-governance-rules",
            help=f"list {short_label} governance rules with pagination",
        )
        self._add_backend_arguments(governance_list)
        governance_list.add_argument("--tenant", required=True)
        governance_list.add_argument("--admin-token", required=True)
        governance_list.add_argument("--limit", type=int, default=100)
        governance_list.add_argument("--cursor")
        governance_list.add_argument("--include-inactive", action="store_true")
        governance_list.add_argument("--object-kind")
        governance_list.set_defaults(handler=self._handle_sot_list_governance_rules)
        governance_eval = sot_subparsers.add_parser(
            "evaluate-governance",
            help=f"evaluate a source update against {short_label} governance rules",
        )
        self._add_backend_arguments(governance_eval)
        governance_eval.add_argument("--tenant", required=True)
        governance_eval.add_argument("--admin-token", required=True)
        governance_eval.add_argument("--object-kind", required=True)
        governance_eval.add_argument("--incoming-source", required=True)
        governance_eval.add_argument("--existing-attributes-json", default="{}")
        governance_eval.add_argument("--incoming-attributes-json", default="{}")
        governance_eval.set_defaults(handler=self._handle_sot_evaluate_governance)
        governance_deactivate = sot_subparsers.add_parser(
            "deactivate-governance-rule",
            help=f"deactivate a {short_label} governance rule",
        )
        self._add_backend_arguments(governance_deactivate)
        governance_deactivate.add_argument("--tenant", required=True)
        governance_deactivate.add_argument("--actor", default="cli")
        governance_deactivate.add_argument("--admin-token", required=True)
        governance_deactivate.add_argument("--name", required=True)
        governance_deactivate.set_defaults(handler=self._handle_sot_deactivate_governance_rule)
        quality_object = sot_subparsers.add_parser(
            "quality-object", help=f"evaluate one {short_label} object quality and certification"
        )
        self._add_backend_arguments(quality_object)
        quality_object.add_argument("--tenant", required=True)
        quality_object.add_argument("--admin-token", required=True)
        quality_object.add_argument("--key", required=True)
        quality_object.set_defaults(handler=self._handle_sot_quality_object)
        quality_summary = sot_subparsers.add_parser(
            "quality-summary", help=f"summarize {short_label} quality and certification status"
        )
        self._add_backend_arguments(quality_summary)
        quality_summary.add_argument("--tenant", required=True)
        quality_summary.add_argument("--admin-token", required=True)
        quality_summary.add_argument("--limit", type=int, default=100)
        quality_summary.add_argument("--cursor")
        quality_summary.add_argument("--kind")
        quality_summary.add_argument(
            "--resource-category", choices=ResourceTaxonomy.category_values()
        )
        quality_summary.add_argument("--resource-type", choices=ResourceTaxonomy.all_type_values())
        quality_summary.add_argument("--tag")
        quality_summary.set_defaults(handler=self._handle_sot_quality_summary)

    def _add_backend_arguments(self, parser: Any) -> None:
        parser.add_argument("--backend", choices=("json", "postgresql"), default="json")
        parser.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        parser.add_argument("--postgres-dsn")
        parser.add_argument(
            "--edition",
            choices=("lite", "pro", "enterprise"),
            default=os.environ.get("OPENINFRA_EDITION", "enterprise"),
        )

    def _add_ipam_commands(self, subparsers: Any) -> None:
        ipam = subparsers.add_parser("ipam", help="ipam operations")
        ipam_subparsers = ipam.add_subparsers(dest="ipam_command", required=True)
        allocate = ipam_subparsers.add_parser(
            "allocate",
            help="allocate an address transactionally",
        )
        allocate.add_argument("--backend", choices=("json", "postgresql"), default="json")
        allocate.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        allocate.add_argument("--postgres-dsn")
        allocate.add_argument("--tenant", required=True)
        allocate.add_argument("--actor", default="cli")
        allocate.add_argument("--vrf", required=True)
        allocate.add_argument("--prefix", required=True)
        allocate.add_argument("--hostname", required=True)
        allocate.add_argument("--idempotency-key", required=True)
        allocate.add_argument("--auth-token")
        allocate.add_argument("--site-code")
        allocate.add_argument("--environment")
        allocate.set_defaults(handler=self._handle_ipam_allocate)

        define_vrf = ipam_subparsers.add_parser("define-vrf", help="define an IPAM VRF")
        self._add_backend_arguments(define_vrf)
        define_vrf.add_argument("--tenant", required=True)
        define_vrf.add_argument("--actor", default="cli")
        define_vrf.add_argument("--name", required=True)
        define_vrf.add_argument("--route-distinguisher")
        define_vrf.set_defaults(handler=self._handle_ipam_define_vrf)

        define_aggregate = ipam_subparsers.add_parser(
            "define-aggregate", help="define an IPAM IPv4/IPv6 aggregate"
        )
        self._add_backend_arguments(define_aggregate)
        define_aggregate.add_argument("--tenant", required=True)
        define_aggregate.add_argument("--actor", default="cli")
        define_aggregate.add_argument("--vrf", required=True)
        define_aggregate.add_argument("--cidr", required=True)
        define_aggregate.add_argument("--description", default="")
        define_aggregate.set_defaults(handler=self._handle_ipam_define_aggregate)

        define_prefix = ipam_subparsers.add_parser(
            "define-prefix", help="define a non-overlapping IPAM prefix inside a VRF"
        )
        self._add_backend_arguments(define_prefix)
        define_prefix.add_argument("--tenant", required=True)
        define_prefix.add_argument("--actor", default="cli")
        define_prefix.add_argument("--vrf", required=True)
        define_prefix.add_argument("--cidr", required=True)
        define_prefix.add_argument("--description", default="")
        define_prefix.set_defaults(handler=self._handle_ipam_define_prefix)

        define_range = ipam_subparsers.add_parser(
            "define-range", help="define an allocation, reservation or exclusion range"
        )
        self._add_backend_arguments(define_range)
        define_range.add_argument("--tenant", required=True)
        define_range.add_argument("--actor", default="cli")
        define_range.add_argument("--vrf", required=True)
        define_range.add_argument("--prefix", required=True)
        define_range.add_argument("--start", required=True)
        define_range.add_argument("--end", required=True)
        define_range.add_argument("--purpose", default="allocation")
        define_range.add_argument("--description", default="")
        define_range.set_defaults(handler=self._handle_ipam_define_range)

        register_address = ipam_subparsers.add_parser(
            "register-address", help="register or update a tracked IP address record"
        )
        self._add_backend_arguments(register_address)
        register_address.add_argument("--tenant", required=True)
        register_address.add_argument("--actor", default="cli")
        register_address.add_argument("--vrf", required=True)
        register_address.add_argument("--prefix", required=True)
        register_address.add_argument("--address", required=True)
        register_address.add_argument("--hostname", required=True)
        register_address.add_argument("--interface-name")
        register_address.add_argument("--status", default="reserved")
        register_address.set_defaults(handler=self._handle_ipam_register_address)

        list_prefixes = ipam_subparsers.add_parser("list-prefixes", help="list prefixes for a VRF")
        self._add_backend_arguments(list_prefixes)
        list_prefixes.add_argument("--tenant", required=True)
        list_prefixes.add_argument("--vrf", required=True)
        list_prefixes.set_defaults(handler=self._handle_ipam_list_prefixes)

        capacity = ipam_subparsers.add_parser("capacity", help="report IPAM prefix capacity")
        self._add_backend_arguments(capacity)
        capacity.add_argument("--tenant", required=True)
        capacity.add_argument("--vrf", required=True)
        capacity.add_argument("--prefix", required=True)
        capacity.set_defaults(handler=self._handle_ipam_capacity)

        define_vlan_group = ipam_subparsers.add_parser(
            "define-vlan-group", help="define an IPAM VLAN group"
        )
        self._add_backend_arguments(define_vlan_group)
        define_vlan_group.add_argument("--tenant", required=True)
        define_vlan_group.add_argument("--actor", default="cli")
        define_vlan_group.add_argument("--name", required=True)
        define_vlan_group.add_argument("--scope")
        define_vlan_group.add_argument("--description", default="")
        define_vlan_group.set_defaults(handler=self._handle_ipam_define_vlan_group)

        define_vxlan_vni = ipam_subparsers.add_parser(
            "define-vxlan-vni", help="define a VXLAN VNI attached to an IPAM VRF"
        )
        self._add_backend_arguments(define_vxlan_vni)
        define_vxlan_vni.add_argument("--tenant", required=True)
        define_vxlan_vni.add_argument("--actor", default="cli")
        define_vxlan_vni.add_argument("--vni", type=int, required=True)
        define_vxlan_vni.add_argument("--name", required=True)
        define_vxlan_vni.add_argument("--vrf", required=True)
        define_vxlan_vni.add_argument("--route-target-import", action="append", default=[])
        define_vxlan_vni.add_argument("--route-target-export", action="append", default=[])
        define_vxlan_vni.add_argument("--description", default="")
        define_vxlan_vni.set_defaults(handler=self._handle_ipam_define_vxlan_vni)

        define_vlan = ipam_subparsers.add_parser(
            "define-vlan", help="define a VLAN and optionally bind it to a VRF/VNI"
        )
        self._add_backend_arguments(define_vlan)
        define_vlan.add_argument("--tenant", required=True)
        define_vlan.add_argument("--actor", default="cli")
        define_vlan.add_argument("--group", required=True)
        define_vlan.add_argument("--vlan-id", type=int, required=True)
        define_vlan.add_argument("--name", required=True)
        define_vlan.add_argument("--vrf")
        define_vlan.add_argument("--vni", type=int)
        define_vlan.add_argument("--description", default="")
        define_vlan.set_defaults(handler=self._handle_ipam_define_vlan)

        define_asn = ipam_subparsers.add_parser("define-asn", help="define an autonomous system")
        self._add_backend_arguments(define_asn)
        define_asn.add_argument("--tenant", required=True)
        define_asn.add_argument("--actor", default="cli")
        define_asn.add_argument("--asn", type=int, required=True)
        define_asn.add_argument("--name", required=True)
        define_asn.add_argument("--description", default="")
        define_asn.set_defaults(handler=self._handle_ipam_define_asn)

        define_bgp_peer = ipam_subparsers.add_parser(
            "define-bgp-peer", help="define a BGP peer attached to a VRF and existing ASNs"
        )
        self._add_backend_arguments(define_bgp_peer)
        define_bgp_peer.add_argument("--tenant", required=True)
        define_bgp_peer.add_argument("--actor", default="cli")
        define_bgp_peer.add_argument("--vrf", required=True)
        define_bgp_peer.add_argument("--local-asn", type=int, required=True)
        define_bgp_peer.add_argument("--remote-asn", type=int, required=True)
        define_bgp_peer.add_argument("--peer-address", required=True)
        define_bgp_peer.add_argument("--address-family")
        define_bgp_peer.add_argument("--route-target-import", action="append", default=[])
        define_bgp_peer.add_argument("--route-target-export", action="append", default=[])
        define_bgp_peer.add_argument("--description", default="")
        define_bgp_peer.set_defaults(handler=self._handle_ipam_define_bgp_peer)

        network_bindings = ipam_subparsers.add_parser(
            "network-bindings", help="render coherent VRF/VLAN/VNI/ASN/BGP bindings"
        )
        self._add_backend_arguments(network_bindings)
        network_bindings.add_argument("--tenant", required=True)
        network_bindings.add_argument("--vrf")
        network_bindings.set_defaults(handler=self._handle_ipam_network_bindings)

        topology = ipam_subparsers.add_parser(
            "topology", help="render the operational IPAM topology graph"
        )
        self._add_backend_arguments(topology)
        topology.add_argument("--tenant", required=True)
        topology.add_argument("--actor", default="cli")
        topology.add_argument("--vrf")
        topology.set_defaults(handler=self._handle_ipam_topology)

        observe_dns = ipam_subparsers.add_parser(
            "observe-dns", help="record an observed forward/reverse DNS binding for conflict scans"
        )
        self._add_backend_arguments(observe_dns)
        observe_dns.add_argument("--tenant", required=True)
        observe_dns.add_argument("--actor", default="cli")
        observe_dns.add_argument("--vrf", required=True)
        observe_dns.add_argument("--hostname", required=True)
        observe_dns.add_argument("--address", required=True)
        observe_dns.add_argument("--ptr-hostname")
        observe_dns.add_argument("--source", default="manual")
        observe_dns.set_defaults(handler=self._handle_ipam_observe_dns)

        observe_dhcp = ipam_subparsers.add_parser(
            "observe-dhcp-lease", help="record an observed DHCP lease for conflict scans"
        )
        self._add_backend_arguments(observe_dhcp)
        observe_dhcp.add_argument("--tenant", required=True)
        observe_dhcp.add_argument("--actor", default="cli")
        observe_dhcp.add_argument("--vrf", required=True)
        observe_dhcp.add_argument("--prefix", required=True)
        observe_dhcp.add_argument("--address", required=True)
        observe_dhcp.add_argument("--mac-address", required=True)
        observe_dhcp.add_argument("--hostname", required=True)
        observe_dhcp.add_argument("--source", default="manual")
        observe_dhcp.add_argument("--inactive", action="store_true")
        observe_dhcp.set_defaults(handler=self._handle_ipam_observe_dhcp_lease)

        detect_conflicts = ipam_subparsers.add_parser(
            "detect-conflicts", help="detect IPAM overlaps, duplicate IPs and DNS/DHCP divergences"
        )
        self._add_backend_arguments(detect_conflicts)
        detect_conflicts.add_argument("--tenant", required=True)
        detect_conflicts.add_argument("--actor", default="cli")
        detect_conflicts.add_argument("--vrf")
        detect_conflicts.set_defaults(handler=self._handle_ipam_detect_conflicts)

        ui_dashboard = ipam_subparsers.add_parser(
            "ui-dashboard", help="render the operational IPAM dashboard view model"
        )
        self._add_backend_arguments(ui_dashboard)
        ui_dashboard.add_argument("--tenant", required=True)
        ui_dashboard.add_argument("--actor", default="cli")
        ui_dashboard.add_argument("--vrf")
        ui_dashboard.add_argument("--format", choices=("json", "html"), default="json")
        ui_dashboard.set_defaults(handler=self._handle_ipam_ui_dashboard)

        ui_search = ipam_subparsers.add_parser(
            "ui-search", help="search IPAM prefixes, reservations and observed data"
        )
        self._add_backend_arguments(ui_search)
        ui_search.add_argument("--tenant", required=True)
        ui_search.add_argument("--actor", default="cli")
        ui_search.add_argument("--query", required=True)
        ui_search.add_argument("--vrf")
        ui_search.set_defaults(handler=self._handle_ipam_ui_search)

        reservation_wizard = ipam_subparsers.add_parser(
            "reservation-wizard", help="preview or execute an IPAM reservation workflow"
        )
        self._add_backend_arguments(reservation_wizard)
        reservation_wizard.add_argument("--tenant", required=True)
        reservation_wizard.add_argument("--actor", default="cli")
        reservation_wizard.add_argument("--vrf", required=True)
        reservation_wizard.add_argument("--prefix", required=True)
        reservation_wizard.add_argument("--hostname", required=True)
        reservation_wizard.add_argument("--idempotency-key", required=True)
        reservation_wizard.add_argument("--apply", action="store_true")
        reservation_wizard.set_defaults(handler=self._handle_ipam_reservation_wizard)

        ddi_preview = ipam_subparsers.add_parser(
            "ddi-preview",
            help="preview DNS/DHCP changes for an existing IPAM reservation",
        )
        self._add_backend_arguments(ddi_preview)
        ddi_preview.add_argument("--tenant", required=True)
        ddi_preview.add_argument("--actor", default="cli")
        ddi_preview.add_argument("--vrf", required=True)
        ddi_preview.add_argument("--idempotency-key", required=True)
        ddi_preview.add_argument(
            "--provider",
            choices=("all", "bind", "powerdns", "kea"),
            action="append",
            default=[],
        )
        ddi_preview.add_argument("--dns-zone")
        ddi_preview.add_argument("--mac-address")
        ddi_preview.add_argument("--ttl", type=int, default=300)
        ddi_preview.add_argument("--apply-preview", action="store_true")
        ddi_preview.set_defaults(handler=self._handle_ipam_ddi_preview)

    def _add_dcim_field_operation_commands(self, commands: Any) -> None:
        list_sheets = commands.add_parser(
            "field-sheet-list", help="list DCIM field operation sheets"
        )
        self._add_backend_arguments(list_sheets)
        list_sheets.add_argument("--tenant", default="default")
        list_sheets.add_argument("--admin-token", required=True)
        list_sheets.add_argument("--limit", type=int, default=100)
        list_sheets.add_argument("--cursor")
        list_sheets.add_argument(
            "--status", choices=("ready", "in-progress", "completed", "cancelled")
        )
        list_sheets.add_argument(
            "--target-type",
            choices=("equipment", "rack", "cable", "power-device", "certificate"),
        )
        list_sheets.add_argument("--site")
        list_sheets.set_defaults(handler=self._handle_dcim_field_sheet_list)

        get_sheet = commands.add_parser(
            "field-sheet-get", help="show one DCIM field operation sheet"
        )
        self._add_backend_arguments(get_sheet)
        get_sheet.add_argument("--tenant", default="default")
        get_sheet.add_argument("--admin-token", required=True)
        get_sheet.add_argument("--sheet-id", required=True)
        get_sheet.set_defaults(handler=self._handle_dcim_field_sheet_get)

        generate = commands.add_parser(
            "field-sheet-generate", help="generate a governed field operation sheet"
        )
        self._add_backend_arguments(generate)
        generate.add_argument("--tenant", default="default")
        generate.add_argument("--actor", default="cli")
        generate.add_argument("--admin-token", required=True)
        generate.add_argument(
            "--target-type",
            choices=("equipment", "rack", "cable", "power-device", "certificate"),
            required=True,
        )
        generate.add_argument("--target-id", required=True)
        generate.add_argument("--title", required=True)
        generate.add_argument("--purpose", required=True)
        generate.add_argument("--owner", required=True)
        generate.add_argument("--operator", required=True)
        generate.add_argument("--source-object-key")
        generate.add_argument("--site")
        generate.add_argument("--building")
        generate.add_argument("--room")
        generate.add_argument("--location-target-type")
        generate.add_argument("--location-target-id")
        generate.set_defaults(handler=self._handle_dcim_field_sheet_generate)

        lock = commands.add_parser(
            "field-lock-acquire", help="acquire an idempotent logical intervention lock"
        )
        self._add_backend_arguments(lock)
        self._add_field_write_arguments(lock)
        lock.add_argument("--sheet-id", required=True)
        lock.add_argument("--idempotency-key", required=True)
        lock.add_argument("--ttl-seconds", type=int, default=3600)
        lock.set_defaults(handler=self._handle_dcim_field_lock_acquire)

        start = commands.add_parser("field-start", help="start a locked field operation")
        self._add_backend_arguments(start)
        self._add_field_write_arguments(start)
        start.add_argument("--sheet-id", required=True)
        start.set_defaults(handler=self._handle_dcim_field_start)

        checklist = commands.add_parser(
            "field-checklist-record", help="record one before/after checklist result"
        )
        self._add_backend_arguments(checklist)
        self._add_field_write_arguments(checklist)
        checklist.add_argument("--sheet-id", required=True)
        checklist.add_argument("--item-id", required=True)
        checklist.add_argument(
            "--result", choices=("passed", "failed", "not-applicable"), required=True
        )
        checklist.add_argument("--operator-note")
        checklist.set_defaults(handler=self._handle_dcim_field_checklist_record)

        attach = commands.add_parser(
            "field-evidence-attach", help="attach an immutable photo or PDF evidence"
        )
        self._add_backend_arguments(attach)
        self._add_field_write_arguments(attach)
        attach.add_argument("--sheet-id", required=True)
        attach.add_argument("--phase", choices=("before", "after"), required=True)
        attach.add_argument(
            "--media-type",
            choices=("image/jpeg", "image/png", "image/webp", "application/pdf"),
            required=True,
        )
        attach.add_argument("--file", type=Path, required=True)
        attach.add_argument("--caption", required=True)
        attach.set_defaults(handler=self._handle_dcim_field_evidence_attach)

        evidence_list = commands.add_parser(
            "field-evidence-list", help="list evidence attached to a field sheet"
        )
        self._add_backend_arguments(evidence_list)
        evidence_list.add_argument("--tenant", default="default")
        evidence_list.add_argument("--admin-token", required=True)
        evidence_list.add_argument("--sheet-id", required=True)
        evidence_list.set_defaults(handler=self._handle_dcim_field_evidence_list)

        validate = commands.add_parser(
            "field-evidence-validate", help="validate immutable field evidence"
        )
        self._add_backend_arguments(validate)
        self._add_field_write_arguments(validate)
        validate.add_argument("--evidence-id", required=True)
        validate.set_defaults(handler=self._handle_dcim_field_evidence_validate)

        complete = commands.add_parser(
            "field-complete", help="complete a field operation after mandatory controls"
        )
        self._add_backend_arguments(complete)
        self._add_field_write_arguments(complete)
        complete.add_argument("--sheet-id", required=True)
        complete.set_defaults(handler=self._handle_dcim_field_complete)

        cancel = commands.add_parser("field-cancel", help="cancel an open field operation")
        self._add_backend_arguments(cancel)
        self._add_field_write_arguments(cancel)
        cancel.add_argument("--sheet-id", required=True)
        cancel.set_defaults(handler=self._handle_dcim_field_cancel)

        qr = commands.add_parser("field-qr-verify", help="verify a field sheet QR payload")
        self._add_backend_arguments(qr)
        qr.add_argument("--tenant", default="default")
        qr.add_argument("--admin-token", required=True)
        qr.add_argument("--sheet-id", required=True)
        qr_source = qr.add_mutually_exclusive_group(required=True)
        qr_source.add_argument("--payload")
        qr_source.add_argument("--payload-file", type=Path)
        qr.set_defaults(handler=self._handle_dcim_field_qr_verify)

        unlock = commands.add_parser("field-lock-release", help="release an intervention lock")
        self._add_backend_arguments(unlock)
        self._add_field_write_arguments(unlock)
        unlock.add_argument("--lock-id", required=True)
        unlock.set_defaults(handler=self._handle_dcim_field_lock_release)

        offline_create = commands.add_parser(
            "field-offline-create", help="create a bounded offline synchronization package"
        )
        self._add_backend_arguments(offline_create)
        self._add_field_write_arguments(offline_create)
        offline_create.add_argument("--sheet-id", required=True)
        offline_create.add_argument("--idempotency-key", required=True)
        offline_create.add_argument("--ttl-seconds", type=int, default=86400)
        offline_create.set_defaults(handler=self._handle_dcim_field_offline_create)

        offline_list = commands.add_parser(
            "field-offline-list", help="list offline synchronization packages"
        )
        self._add_backend_arguments(offline_list)
        offline_list.add_argument("--tenant", default="default")
        offline_list.add_argument("--admin-token", required=True)
        offline_list.add_argument("--sheet-id")
        offline_list.add_argument("--limit", type=int, default=100)
        offline_list.add_argument("--cursor")
        offline_list.set_defaults(handler=self._handle_dcim_field_offline_list)

        offline_get = commands.add_parser(
            "field-offline-get", help="show one offline synchronization package"
        )
        self._add_backend_arguments(offline_get)
        offline_get.add_argument("--tenant", default="default")
        offline_get.add_argument("--admin-token", required=True)
        offline_get.add_argument("--package-id", required=True)
        offline_get.add_argument(
            "--include-payload", action=argparse.BooleanOptionalAction, default=True
        )
        offline_get.set_defaults(handler=self._handle_dcim_field_offline_get)

        offline_sync = commands.add_parser(
            "field-offline-sync", help="synchronize and close an offline package"
        )
        self._add_backend_arguments(offline_sync)
        self._add_field_write_arguments(offline_sync)
        offline_sync.add_argument("--package-id", required=True)
        offline_sync.add_argument("--payload-sha256", required=True)
        offline_sync.set_defaults(handler=self._handle_dcim_field_offline_sync)

    @staticmethod
    def _add_field_write_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--actor", default="cli")
        parser.add_argument("--admin-token", required=True)

    def _add_dcim_commands(self, subparsers: Any) -> None:
        dcim = subparsers.add_parser("dcim", help="dcim operations")
        dcim_subparsers = dcim.add_subparsers(dest="dcim_command", required=True)
        self._add_dcim_field_operation_commands(dcim_subparsers)
        sites = dcim_subparsers.add_parser("sites", help="list DCIM sites")
        self._add_backend_arguments(sites)
        sites.add_argument("--tenant", default="default")
        sites.add_argument("--include-retired", action="store_true")
        sites.set_defaults(handler=self._handle_dcim_sites)

        site = dcim_subparsers.add_parser("site", help="show one DCIM site")
        self._add_backend_arguments(site)
        site.add_argument("--tenant", default="default")
        site.add_argument("--code", required=True)
        site.set_defaults(handler=self._handle_dcim_site)

        create_site = dcim_subparsers.add_parser("site-create", help="create a DCIM site")
        self._add_backend_arguments(create_site)
        create_site.add_argument("--tenant", default="default")
        create_site.add_argument("--actor", default="cli")
        create_site.add_argument("--code", required=True)
        create_site.add_argument("--name", required=True)
        create_site.add_argument("--country", required=True)
        create_site.add_argument("--city", required=True)
        create_site.add_argument("--region", default="")
        create_site.add_argument("--street-address", required=True)
        create_site.add_argument("--postal-code", required=True)
        create_site.add_argument("--contact-email", required=True)
        create_site.add_argument("--phone", required=True)
        create_site.set_defaults(handler=self._handle_dcim_site_create)

        update_site = dcim_subparsers.add_parser("site-update", help="update a DCIM site")
        self._add_backend_arguments(update_site)
        update_site.add_argument("--tenant", default="default")
        update_site.add_argument("--actor", default="cli")
        update_site.add_argument("--code", required=True)
        update_site.add_argument("--name")
        update_site.add_argument("--country")
        update_site.add_argument("--city")
        update_site.add_argument("--region")
        update_site.add_argument("--street-address")
        update_site.add_argument("--postal-code")
        update_site.add_argument("--contact-email")
        update_site.add_argument("--phone")
        update_site.add_argument("--status", choices=("active", "suspended", "retired"))
        update_site.set_defaults(handler=self._handle_dcim_site_update)

        delete_site = dcim_subparsers.add_parser("site-delete", help="retire a DCIM site")
        self._add_backend_arguments(delete_site)
        delete_site.add_argument("--tenant", default="default")
        delete_site.add_argument("--actor", default="cli")
        delete_site.add_argument("--code", required=True)
        delete_site.set_defaults(handler=self._handle_dcim_site_delete)

        topology_catalog = dcim_subparsers.add_parser(
            "topology-catalog", help="list active DCIM site/building/room dependencies"
        )
        self._add_backend_arguments(topology_catalog)
        topology_catalog.add_argument("--tenant", default="default")
        topology_catalog.add_argument("--include-retired", action="store_true")
        topology_catalog.set_defaults(handler=self._handle_dcim_topology_catalog)

        buildings = dcim_subparsers.add_parser("buildings", help="list DCIM buildings for a site")
        self._add_backend_arguments(buildings)
        buildings.add_argument("--tenant", default="default")
        buildings.add_argument("--site", required=True)
        buildings.add_argument("--include-retired", action="store_true")
        buildings.set_defaults(handler=self._handle_dcim_buildings)

        building = dcim_subparsers.add_parser("building", help="show one DCIM building")
        self._add_backend_arguments(building)
        building.add_argument("--tenant", default="default")
        building.add_argument("--site", required=True)
        building.add_argument("--code", required=True)
        building.set_defaults(handler=self._handle_dcim_building)

        create_building = dcim_subparsers.add_parser(
            "building-create", help="create a DCIM building"
        )
        self._add_backend_arguments(create_building)
        create_building.add_argument("--tenant", default="default")
        create_building.add_argument("--actor", default="cli")
        create_building.add_argument("--site", required=True)
        create_building.add_argument("--code", required=True)
        create_building.add_argument("--name", required=True)
        create_building.add_argument(
            "--building-type",
            choices=("simple", "floors", "Simple", "Etages", "etages"),
            default="simple",
            help="building type: Simple or Etages",
        )
        create_building.add_argument("--initial-level", type=int)
        create_building.add_argument("--final-level", type=int)
        create_building.set_defaults(handler=self._handle_dcim_building_create)

        update_building = dcim_subparsers.add_parser(
            "building-update", help="update a DCIM building"
        )
        self._add_backend_arguments(update_building)
        update_building.add_argument("--tenant", default="default")
        update_building.add_argument("--actor", default="cli")
        update_building.add_argument("--site", required=True)
        update_building.add_argument("--code", required=True)
        update_building.add_argument("--name")
        update_building.add_argument("--status", choices=("active", "suspended", "retired"))
        update_building.set_defaults(handler=self._handle_dcim_building_update)

        delete_building = dcim_subparsers.add_parser(
            "building-delete", help="retire a DCIM building"
        )
        self._add_backend_arguments(delete_building)
        delete_building.add_argument("--tenant", default="default")
        delete_building.add_argument("--actor", default="cli")
        delete_building.add_argument("--site", required=True)
        delete_building.add_argument("--code", required=True)
        delete_building.set_defaults(handler=self._handle_dcim_building_delete)

        floors = dcim_subparsers.add_parser("floors", help="list DCIM floors for a building")
        self._add_backend_arguments(floors)
        floors.add_argument("--tenant", default="default")
        floors.add_argument("--site", required=True)
        floors.add_argument("--building", required=True)
        floors.add_argument("--include-retired", action="store_true")
        floors.set_defaults(handler=self._handle_dcim_floors)

        floor = dcim_subparsers.add_parser("floor", help="show one DCIM floor")
        self._add_backend_arguments(floor)
        floor.add_argument("--tenant", default="default")
        floor.add_argument("--site", required=True)
        floor.add_argument("--building", required=True)
        floor.add_argument("--code", required=True)
        floor.set_defaults(handler=self._handle_dcim_floor)

        create_floor = dcim_subparsers.add_parser("floor-create", help=argparse.SUPPRESS)
        self._add_backend_arguments(create_floor)
        create_floor.add_argument("--tenant", default="default")
        create_floor.add_argument("--actor", default="cli")
        create_floor.add_argument("--site", required=True)
        create_floor.add_argument("--building", required=True)
        create_floor.add_argument("--code", required=True)
        create_floor.add_argument("--name", required=True)
        create_floor.add_argument("--level-index", type=int, required=True)
        create_floor.set_defaults(handler=self._handle_dcim_floor_create)

        update_floor = dcim_subparsers.add_parser("floor-update", help=argparse.SUPPRESS)
        self._add_backend_arguments(update_floor)
        update_floor.add_argument("--tenant", default="default")
        update_floor.add_argument("--actor", default="cli")
        update_floor.add_argument("--site", required=True)
        update_floor.add_argument("--building", required=True)
        update_floor.add_argument("--code", required=True)
        update_floor.add_argument("--name")
        update_floor.add_argument("--level-index", type=int)
        update_floor.add_argument("--status", choices=("active", "suspended", "retired"))
        update_floor.set_defaults(handler=self._handle_dcim_floor_update)

        delete_floor = dcim_subparsers.add_parser("floor-delete", help=argparse.SUPPRESS)
        self._add_backend_arguments(delete_floor)
        delete_floor.add_argument("--tenant", default="default")
        delete_floor.add_argument("--actor", default="cli")
        delete_floor.add_argument("--site", required=True)
        delete_floor.add_argument("--building", required=True)
        delete_floor.add_argument("--code", required=True)
        delete_floor.set_defaults(handler=self._handle_dcim_floor_delete)

        rooms = dcim_subparsers.add_parser("rooms", help="list DCIM rooms for a building")
        self._add_backend_arguments(rooms)
        rooms.add_argument("--tenant", default="default")
        rooms.add_argument("--site", required=True)
        rooms.add_argument("--building", required=True)
        rooms.add_argument("--include-retired", action="store_true")
        rooms.set_defaults(handler=self._handle_dcim_rooms)

        room = dcim_subparsers.add_parser("room", help="show one DCIM room")
        self._add_backend_arguments(room)
        room.add_argument("--tenant", default="default")
        room.add_argument("--site", required=True)
        room.add_argument("--building", required=True)
        room.add_argument("--code", required=True)
        room.set_defaults(handler=self._handle_dcim_room)

        create_room = dcim_subparsers.add_parser("room-create", help="create a DCIM room")
        self._add_backend_arguments(create_room)
        create_room.add_argument("--tenant", default="default")
        create_room.add_argument("--actor", default="cli")
        create_room.add_argument("--site", required=True)
        create_room.add_argument("--building", required=True)
        create_room.add_argument("--floor")
        create_room.add_argument("--code", required=True)
        create_room.add_argument("--name", required=True)
        create_room.add_argument("--row", action="append", default=[])
        create_room.add_argument("--row-range", dest="row", action="append")
        create_room.add_argument("--column", action="append", default=[])
        create_room.add_argument("--column-range", dest="column", action="append")
        create_room.set_defaults(handler=self._handle_dcim_room_create)

        update_room = dcim_subparsers.add_parser("room-update", help="update a DCIM room")
        self._add_backend_arguments(update_room)
        update_room.add_argument("--tenant", default="default")
        update_room.add_argument("--actor", default="cli")
        update_room.add_argument("--site", required=True)
        update_room.add_argument("--building", required=True)
        update_room.add_argument("--code", required=True)
        update_room.add_argument("--name")
        update_room.add_argument("--row", action="append")
        update_room.add_argument("--column", action="append")
        update_room.add_argument("--status", choices=("active", "suspended", "retired"))
        update_room.set_defaults(handler=self._handle_dcim_room_update)

        delete_room = dcim_subparsers.add_parser("room-delete", help="retire a DCIM room")
        self._add_backend_arguments(delete_room)
        delete_room.add_argument("--tenant", default="default")
        delete_room.add_argument("--actor", default="cli")
        delete_room.add_argument("--site", required=True)
        delete_room.add_argument("--building", required=True)
        delete_room.add_argument("--code", required=True)
        delete_room.set_defaults(handler=self._handle_dcim_room_delete)

        zones = dcim_subparsers.add_parser("zones", help="list DCIM zones for a room")
        self._add_backend_arguments(zones)
        zones.add_argument("--tenant", default="default")
        zones.add_argument("--site", required=True)
        zones.add_argument("--building", required=True)
        zones.add_argument("--room", required=True)
        zones.add_argument("--include-retired", action="store_true")
        zones.set_defaults(handler=self._handle_dcim_zones)

        zone = dcim_subparsers.add_parser("zone", help="show one DCIM zone")
        self._add_backend_arguments(zone)
        zone.add_argument("--tenant", default="default")
        zone.add_argument("--site", required=True)
        zone.add_argument("--building", required=True)
        zone.add_argument("--room", required=True)
        zone.add_argument("--code", required=True)
        zone.set_defaults(handler=self._handle_dcim_zone)

        create_zone = dcim_subparsers.add_parser("zone-create", help="create a DCIM room zone")
        self._add_backend_arguments(create_zone)
        create_zone.add_argument("--tenant", default="default")
        create_zone.add_argument("--actor", default="cli")
        create_zone.add_argument("--site", required=True)
        create_zone.add_argument("--building", required=True)
        create_zone.add_argument("--room", required=True)
        create_zone.add_argument("--code", required=True)
        create_zone.add_argument("--name", required=True)
        create_zone.add_argument("--row", action="append", required=True)
        create_zone.add_argument("--column", action="append", required=True)
        create_zone.set_defaults(handler=self._handle_dcim_zone_create)

        update_zone = dcim_subparsers.add_parser("zone-update", help="update a DCIM room zone")
        self._add_backend_arguments(update_zone)
        update_zone.add_argument("--tenant", default="default")
        update_zone.add_argument("--actor", default="cli")
        update_zone.add_argument("--site", required=True)
        update_zone.add_argument("--building", required=True)
        update_zone.add_argument("--room", required=True)
        update_zone.add_argument("--code", required=True)
        update_zone.add_argument("--name")
        update_zone.add_argument("--row", action="append")
        update_zone.add_argument("--column", action="append")
        update_zone.add_argument("--status", choices=("active", "suspended", "retired"))
        update_zone.set_defaults(handler=self._handle_dcim_zone_update)

        delete_zone = dcim_subparsers.add_parser("zone-delete", help="retire a DCIM room zone")
        self._add_backend_arguments(delete_zone)
        delete_zone.add_argument("--tenant", default="default")
        delete_zone.add_argument("--actor", default="cli")
        delete_zone.add_argument("--site", required=True)
        delete_zone.add_argument("--building", required=True)
        delete_zone.add_argument("--room", required=True)
        delete_zone.add_argument("--code", required=True)
        delete_zone.set_defaults(handler=self._handle_dcim_zone_delete)

        define_room = dcim_subparsers.add_parser(
            "define-room",
            help="define a physical DCIM room hierarchy",
        )
        define_room.add_argument("--backend", choices=("json", "postgresql"), default="json")
        define_room.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_room.add_argument("--postgres-dsn")
        define_room.add_argument("--tenant", default="default")
        define_room.add_argument("--actor", default="cli")
        define_room.add_argument("--site-code", required=True)
        define_room.add_argument("--site-name", required=True)
        define_room.add_argument("--country", required=True)
        define_room.add_argument("--region", default="")
        define_room.add_argument("--city", required=True)
        define_room.add_argument("--building-code", required=True)
        define_room.add_argument("--building-name", required=True)
        define_room.add_argument(
            "--floor-code",
            help="deprecated compatibility hint; the code is generated from --floor-index",
        )
        define_room.add_argument(
            "--floor-name",
            help="deprecated compatibility hint; the name is generated from --floor-index",
        )
        define_room.add_argument("--floor-index", type=int, required=True)
        define_room.add_argument("--room-code", required=True)
        define_room.add_argument("--room-name", required=True)
        define_room.add_argument("--row", action="append", default=[])
        define_room.add_argument("--row-range", dest="row", action="append")
        define_room.add_argument("--column", action="append", default=[])
        define_room.add_argument("--column-range", dest="column", action="append")
        define_room.add_argument("--zone-code")
        define_room.add_argument("--zone-name")
        define_room.add_argument("--zone-row", action="append", default=[])
        define_room.add_argument("--zone-column", action="append", default=[])
        define_room.add_argument("--x", type=float)
        define_room.add_argument("--y", type=float)
        define_room.add_argument("--z", type=float)
        define_room.set_defaults(handler=self._handle_dcim_define_room)

        define_rack = dcim_subparsers.add_parser(
            "define-rack",
            help="define a rack with U capacity and usable mounting faces",
        )
        define_rack.add_argument("--backend", choices=("json", "postgresql"), default="json")
        define_rack.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_rack.add_argument("--postgres-dsn")
        define_rack.add_argument("--tenant", default="default")
        define_rack.add_argument("--actor", default="cli")
        define_rack.add_argument("--site", required=True)
        define_rack.add_argument("--building", required=True)
        define_rack.add_argument("--floor")
        define_rack.add_argument("--room", required=True)
        define_rack.add_argument("--zone")
        define_rack.add_argument("--rack", required=True)
        define_rack.add_argument("--row", required=True)
        define_rack.add_argument("--column", required=True)
        define_rack.add_argument("--units", type=int, required=True)
        define_rack.add_argument("--face", action="append", default=[])
        define_rack.add_argument("--max-weight-kg", type=float)
        define_rack.add_argument("--power-capacity-watts", type=int)
        define_rack.add_argument("--x", type=float)
        define_rack.add_argument("--y", type=float)
        define_rack.add_argument("--z", type=float)
        define_rack.set_defaults(handler=self._handle_dcim_define_rack)

        racks = dcim_subparsers.add_parser("racks", help="list DCIM racks for a room")
        self._add_backend_arguments(racks)
        racks.add_argument("--tenant", default="default")
        racks.add_argument("--site", required=True)
        racks.add_argument("--building", required=True)
        racks.add_argument("--room", required=True)
        racks.add_argument("--include-retired", action="store_true")
        racks.set_defaults(handler=self._handle_dcim_racks)

        rack = dcim_subparsers.add_parser("rack", help="show one DCIM rack")
        self._add_backend_arguments(rack)
        rack.add_argument("--tenant", default="default")
        rack.add_argument("--site", required=True)
        rack.add_argument("--building", required=True)
        rack.add_argument("--room", required=True)
        rack.add_argument("--rack", required=True)
        rack.set_defaults(handler=self._handle_dcim_rack)

        update_rack = dcim_subparsers.add_parser("rack-update", help="update a DCIM rack")
        self._add_backend_arguments(update_rack)
        update_rack.add_argument("--tenant", default="default")
        update_rack.add_argument("--actor", default="cli")
        update_rack.add_argument("--site", required=True)
        update_rack.add_argument("--building", required=True)
        update_rack.add_argument("--room", required=True)
        update_rack.add_argument("--rack", required=True)
        update_rack.add_argument("--row")
        update_rack.add_argument("--column")
        update_rack.add_argument("--units", type=int)
        update_rack.add_argument("--face", action="append")
        update_rack.add_argument("--max-weight-kg", type=float)
        update_rack.add_argument("--power-capacity-watts", type=int)
        update_rack.add_argument("--status", choices=("active", "suspended", "retired"))
        update_rack.set_defaults(handler=self._handle_dcim_rack_update)

        delete_rack = dcim_subparsers.add_parser("rack-delete", help="retire a DCIM rack")
        self._add_backend_arguments(delete_rack)
        delete_rack.add_argument("--tenant", default="default")
        delete_rack.add_argument("--actor", default="cli")
        delete_rack.add_argument("--site", required=True)
        delete_rack.add_argument("--building", required=True)
        delete_rack.add_argument("--room", required=True)
        delete_rack.add_argument("--rack", required=True)
        delete_rack.set_defaults(handler=self._handle_dcim_rack_delete)

        rack_capacity = dcim_subparsers.add_parser(
            "rack-capacity",
            help="report rack U occupation by face",
        )
        rack_capacity.add_argument("--backend", choices=("json", "postgresql"), default="json")
        rack_capacity.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        rack_capacity.add_argument("--postgres-dsn")
        rack_capacity.add_argument("--tenant", default="default")
        rack_capacity.add_argument("--site", required=True)
        rack_capacity.add_argument("--building", required=True)
        rack_capacity.add_argument("--room", required=True)
        rack_capacity.add_argument("--rack", required=True)
        rack_capacity.set_defaults(handler=self._handle_dcim_rack_capacity)

        locate = dcim_subparsers.add_parser("locate", help="locate equipment physically")
        locate.add_argument("--backend", choices=("json", "postgresql"), default="json")
        locate.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        locate.add_argument("--postgres-dsn")
        locate.add_argument("--tenant", default="default")
        locate.add_argument("--actor", default="cli")
        locate.add_argument("--asset-tag", required=True)
        locate.add_argument("--equipment-name", default="Unnamed equipment")
        locate.add_argument("--site", required=True)
        locate.add_argument("--building", required=True)
        locate.add_argument("--floor")
        locate.add_argument("--room", required=True)
        locate.add_argument("--zone")
        locate.add_argument("--row", required=True)
        locate.add_argument("--column", required=True)
        locate.add_argument("--rack")
        locate.add_argument("--u-position", type=int)
        locate.add_argument("--u-height", type=int)
        locate.add_argument("--rack-face", choices=("front", "rear"))
        locate.add_argument("--x", type=float)
        locate.add_argument("--y", type=float)
        locate.add_argument("--z", type=float)
        locate.set_defaults(handler=self._handle_dcim_locate)

        define_patch_panel = dcim_subparsers.add_parser(
            "define-patch-panel",
            help="define a rack-mounted patch panel and generate its ports",
        )
        define_patch_panel.add_argument("--backend", choices=("json", "postgresql"), default="json")
        define_patch_panel.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_patch_panel.add_argument("--postgres-dsn")
        define_patch_panel.add_argument("--tenant", default="default")
        define_patch_panel.add_argument("--actor", default="cli")
        define_patch_panel.add_argument("--site", required=True)
        define_patch_panel.add_argument("--building", required=True)
        define_patch_panel.add_argument("--room", required=True)
        define_patch_panel.add_argument("--rack", required=True)
        define_patch_panel.add_argument("--patch-panel", required=True)
        define_patch_panel.add_argument("--rack-face", choices=("front", "rear"), default="front")
        define_patch_panel.add_argument("--u-position", type=int, required=True)
        define_patch_panel.add_argument("--u-height", type=int, default=1)
        define_patch_panel.add_argument("--port-count", type=int, required=True)
        define_patch_panel.add_argument("--connector", required=True)
        define_patch_panel.add_argument("--medium", required=True)
        define_patch_panel.add_argument("--label", default="")
        define_patch_panel.add_argument("--port-prefix", default="P")
        define_patch_panel.set_defaults(handler=self._handle_dcim_define_patch_panel)

        define_port = dcim_subparsers.add_parser(
            "define-port",
            help="define a DCIM port on an equipment or patch panel",
        )
        define_port.add_argument("--backend", choices=("json", "postgresql"), default="json")
        define_port.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_port.add_argument("--postgres-dsn")
        define_port.add_argument("--tenant", default="default")
        define_port.add_argument("--actor", default="cli")
        define_port.add_argument(
            "--owner-type", choices=("equipment", "patch_panel"), required=True
        )
        define_port.add_argument("--owner-code", required=True)
        define_port.add_argument("--port-name", required=True)
        define_port.add_argument("--connector", required=True)
        define_port.add_argument("--medium", required=True)
        define_port.add_argument("--site")
        define_port.add_argument("--building")
        define_port.add_argument("--room")
        define_port.add_argument("--disabled", action="store_true")
        define_port.set_defaults(handler=self._handle_dcim_define_port)

        connect_cable = dcim_subparsers.add_parser(
            "connect-cable",
            help="connect two compatible DCIM ports with a point-to-point cable",
        )
        connect_cable.add_argument("--backend", choices=("json", "postgresql"), default="json")
        connect_cable.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        connect_cable.add_argument("--postgres-dsn")
        connect_cable.add_argument("--tenant", default="default")
        connect_cable.add_argument("--actor", default="cli")
        connect_cable.add_argument("--cable-id", required=True)
        connect_cable.add_argument(
            "--a-owner-type", choices=("equipment", "patch_panel"), required=True
        )
        connect_cable.add_argument("--a-owner-code", required=True)
        connect_cable.add_argument("--a-port-name", required=True)
        connect_cable.add_argument(
            "--b-owner-type", choices=("equipment", "patch_panel"), required=True
        )
        connect_cable.add_argument("--b-owner-code", required=True)
        connect_cable.add_argument("--b-port-name", required=True)
        connect_cable.add_argument("--medium", required=True)
        connect_cable.add_argument(
            "--status", choices=("planned", "installed", "retired"), default="installed"
        )
        connect_cable.add_argument("--path", action="append", required=True)
        connect_cable.add_argument("--length-m", type=float)
        connect_cable.add_argument("--label", default="")
        connect_cable.set_defaults(handler=self._handle_dcim_connect_cable)

        cable_trace = dcim_subparsers.add_parser(
            "cable-trace",
            help="trace a DCIM cable path and endpoints",
        )
        cable_trace.add_argument("--backend", choices=("json", "postgresql"), default="json")
        cable_trace.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        cable_trace.add_argument("--postgres-dsn")
        cable_trace.add_argument("--tenant", default="default")
        cable_trace.add_argument("--actor", default="cli")
        cable_trace.add_argument("--cable-id", required=True)
        cable_trace.set_defaults(handler=self._handle_dcim_cable_trace)

        locator_sheet = dcim_subparsers.add_parser(
            "locator-sheet",
            help="generate QR-backed field locator sheet for an equipment",
        )
        locator_sheet.add_argument("--backend", choices=("json", "postgresql"), default="json")
        locator_sheet.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        locator_sheet.add_argument("--postgres-dsn")
        locator_sheet.add_argument("--tenant", default="default")
        locator_sheet.add_argument("--actor", default="cli")
        locator_sheet.add_argument("--asset-tag", required=True)
        locator_sheet.add_argument("--format", choices=("json", "html"), default="json")
        locator_sheet.set_defaults(handler=self._handle_dcim_locator_sheet)

        verify_scan = dcim_subparsers.add_parser(
            "verify-scan",
            help="verify a field QR payload against the current equipment location",
        )
        verify_scan.add_argument("--backend", choices=("json", "postgresql"), default="json")
        verify_scan.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        verify_scan.add_argument("--postgres-dsn")
        verify_scan.add_argument("--tenant", default="default")
        verify_scan.add_argument("--actor", default="cli")
        verify_scan.add_argument("--asset-tag", required=True)
        verify_scan.add_argument("--payload", required=True)
        verify_scan.set_defaults(handler=self._handle_dcim_verify_scan)

        room_plan = dcim_subparsers.add_parser(
            "room-plan",
            help="render a 2D room grid with racks and equipment occupancy",
        )
        room_plan.add_argument("--backend", choices=("json", "postgresql"), default="json")
        room_plan.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        room_plan.add_argument("--postgres-dsn")
        room_plan.add_argument("--tenant", default="default")
        room_plan.add_argument("--actor", default="cli")
        room_plan.add_argument("--site", required=True)
        room_plan.add_argument("--building", required=True)
        room_plan.add_argument("--room", required=True)
        room_plan.add_argument("--format", choices=("json", "svg", "html"), default="json")
        room_plan.set_defaults(handler=self._handle_dcim_room_plan)

        rack_elevation = dcim_subparsers.add_parser(
            "rack-elevation",
            help="render rack U occupation for one rack face",
        )
        rack_elevation.add_argument("--backend", choices=("json", "postgresql"), default="json")
        rack_elevation.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        rack_elevation.add_argument("--postgres-dsn")
        rack_elevation.add_argument("--tenant", default="default")
        rack_elevation.add_argument("--actor", default="cli")
        rack_elevation.add_argument("--site", required=True)
        rack_elevation.add_argument("--building", required=True)
        rack_elevation.add_argument("--room", required=True)
        rack_elevation.add_argument("--rack", required=True)
        rack_elevation.add_argument("--face", choices=("front", "rear"), default="front")
        rack_elevation.add_argument("--format", choices=("json", "svg", "html"), default="json")
        rack_elevation.set_defaults(handler=self._handle_dcim_rack_elevation)

        define_power_device = dcim_subparsers.add_parser(
            "define-power-device",
            help="define a DCIM PDU or UPS power source",
        )
        define_power_device.add_argument(
            "--backend", choices=("json", "postgresql"), default="json"
        )
        define_power_device.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_power_device.add_argument("--postgres-dsn")
        define_power_device.add_argument("--tenant", default="default")
        define_power_device.add_argument("--actor", default="cli")
        define_power_device.add_argument("--code", required=True)
        define_power_device.add_argument("--kind", choices=("pdu", "ups"), required=True)
        define_power_device.add_argument("--site", required=True)
        define_power_device.add_argument("--building", required=True)
        define_power_device.add_argument("--room", required=True)
        define_power_device.add_argument("--rack")
        define_power_device.add_argument("--side", choices=("A", "B"))
        define_power_device.add_argument("--capacity-watts", type=int, required=True)
        define_power_device.add_argument("--derating-percent", type=int, default=80)
        define_power_device.add_argument("--input-source", default="utility")
        define_power_device.add_argument("--output-voltage", type=int, default=230)
        define_power_device.add_argument("--label", default="")
        define_power_device.set_defaults(handler=self._handle_dcim_define_power_device)

        define_power_circuit = dcim_subparsers.add_parser(
            "define-power-circuit",
            help="define an A/B power circuit from a power source to a rack",
        )
        define_power_circuit.add_argument(
            "--backend", choices=("json", "postgresql"), default="json"
        )
        define_power_circuit.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_power_circuit.add_argument("--postgres-dsn")
        define_power_circuit.add_argument("--tenant", default="default")
        define_power_circuit.add_argument("--actor", default="cli")
        define_power_circuit.add_argument("--circuit-id", required=True)
        define_power_circuit.add_argument("--source-device", required=True)
        define_power_circuit.add_argument("--site", required=True)
        define_power_circuit.add_argument("--building", required=True)
        define_power_circuit.add_argument("--room", required=True)
        define_power_circuit.add_argument("--rack", required=True)
        define_power_circuit.add_argument("--side", choices=("A", "B"), required=True)
        define_power_circuit.add_argument("--capacity-watts", type=int, required=True)
        define_power_circuit.add_argument("--breaker-rating-amps", type=int, required=True)
        define_power_circuit.add_argument("--redundancy-group", default="default")
        define_power_circuit.add_argument("--label", default="")
        define_power_circuit.set_defaults(handler=self._handle_dcim_define_power_circuit)

        define_cooling_zone = dcim_subparsers.add_parser(
            "define-cooling-zone",
            help="define a hot/cold aisle cooling capacity zone",
        )
        define_cooling_zone.add_argument(
            "--backend", choices=("json", "postgresql"), default="json"
        )
        define_cooling_zone.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        define_cooling_zone.add_argument("--postgres-dsn")
        define_cooling_zone.add_argument("--tenant", default="default")
        define_cooling_zone.add_argument("--actor", default="cli")
        define_cooling_zone.add_argument("--site", required=True)
        define_cooling_zone.add_argument("--building", required=True)
        define_cooling_zone.add_argument("--room", required=True)
        define_cooling_zone.add_argument("--zone", required=True)
        define_cooling_zone.add_argument(
            "--role", choices=("cold_aisle", "hot_aisle", "neutral"), required=True
        )
        define_cooling_zone.add_argument("--cooling-capacity-watts", type=int, required=True)
        define_cooling_zone.add_argument("--supply-temperature-c", type=float, required=True)
        define_cooling_zone.add_argument("--return-temperature-c", type=float, required=True)
        define_cooling_zone.add_argument("--label", default="")
        define_cooling_zone.set_defaults(handler=self._handle_dcim_define_cooling_zone)

        reserve_power = dcim_subparsers.add_parser(
            "reserve-power",
            help="reserve expected power draw for a rack-mounted equipment on a circuit",
        )
        reserve_power.add_argument("--backend", choices=("json", "postgresql"), default="json")
        reserve_power.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        reserve_power.add_argument("--postgres-dsn")
        reserve_power.add_argument("--tenant", default="default")
        reserve_power.add_argument("--actor", default="cli")
        reserve_power.add_argument("--asset-tag", required=True)
        reserve_power.add_argument("--circuit-id", required=True)
        reserve_power.add_argument("--expected-watts", type=int, required=True)
        reserve_power.add_argument("--label", default="")
        reserve_power.set_defaults(handler=self._handle_dcim_reserve_power)

        energy_cooling = dcim_subparsers.add_parser(
            "energy-cooling-capacity",
            help="report rack A/B power and cooling capacity",
        )
        energy_cooling.add_argument("--backend", choices=("json", "postgresql"), default="json")
        energy_cooling.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        energy_cooling.add_argument("--postgres-dsn")
        energy_cooling.add_argument("--tenant", default="default")
        energy_cooling.add_argument("--actor", default="cli")
        energy_cooling.add_argument("--site", required=True)
        energy_cooling.add_argument("--building", required=True)
        energy_cooling.add_argument("--room", required=True)
        energy_cooling.add_argument("--rack", required=True)
        energy_cooling.set_defaults(handler=self._handle_dcim_energy_cooling_capacity)

        digital_twin = dcim_subparsers.add_parser(
            "digital-twin",
            help="render the initial room digital twin across racks, cabling and capacity",
        )
        digital_twin.add_argument("--backend", choices=("json", "postgresql"), default="json")
        digital_twin.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        digital_twin.add_argument("--postgres-dsn")
        digital_twin.add_argument("--tenant", default="default")
        digital_twin.add_argument("--actor", default="cli")
        digital_twin.add_argument("--site", required=True)
        digital_twin.add_argument("--building", required=True)
        digital_twin.add_argument("--room", required=True)
        digital_twin.set_defaults(handler=self._handle_dcim_digital_twin)

    def _handle_version(self, args: argparse.Namespace) -> int:
        print(__version__)
        return 0

    def _handle_spec_validate(self, args: argparse.Namespace) -> int:
        report = ContractualSpecValidator().assert_valid(args.root)
        print(report.as_text())
        return 0

    def _handle_installer_validate(self, args: argparse.Namespace) -> int:
        validator = InstallerConfigValidator()
        if args.path:
            file_report = validator.validate_file(args.path, args.edition, args.scope)
            print(json.dumps(file_report.as_dict(), sort_keys=True, indent=2))
            return 0 if file_report.valid else 2
        fleet_report = validator.validate_tree(args.root)
        print(json.dumps(fleet_report.as_dict(), sort_keys=True, indent=2))
        return 0 if fleet_report.valid else 2

    def _handle_installer_dry_run(self, args: argparse.Namespace) -> int:
        validator = InstallerConfigValidator()
        reports = (
            (validator.validate_file(args.path, args.edition, args.scope),)
            if args.path
            else validator.validate_tree(args.root).reports
        )
        payload = {
            "dry_run": True,
            "installers": [report.as_dict() for report in reports],
            "writes_performed": False,
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0 if all(report.valid for report in reports) else 2

    def _handle_installer_render_systemd(self, args: argparse.Namespace) -> int:
        unit = InstallerConfigValidator().render_systemd_unit(args.edition, args.scope)
        print(unit)
        return 0

    def _handle_edition_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        print(json.dumps(app.edition_query_service.policies(), sort_keys=True, indent=2))
        return 0

    def _handle_edition_feature_check(self, args: argparse.Namespace) -> int:
        command = CheckFeatureCommand(args.tenant, args.edition, args.capability)
        decision = EditionPolicyService().check_feature(command.edition, command.capability)
        print(json.dumps(decision.as_dict(), sort_keys=True, indent=2))
        return 0 if decision.allowed else 2

    def _handle_edition_quota_check(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        decision = app.edition_query_service.quota_decision(
            CheckQuotaCommand(args.tenant, args.edition, args.resource, args.increment)
        )
        print(json.dumps(decision.as_dict(), sort_keys=True, indent=2))
        return 0 if decision.allowed else 2

    def _handle_database_render_migration(self, args: argparse.Namespace) -> int:
        root = self._resolve_migration_root(args)
        migration = PostgreSQLMigrationCatalog(root).load(args.name)
        print(migration.sql, end="")
        return 0

    def _handle_database_status(self, args: argparse.Namespace) -> int:
        executor = self._create_migration_executor(args)
        print(json.dumps(executor.status_as_dict(), sort_keys=True))
        return 0

    def _handle_database_apply_migrations(self, args: argparse.Namespace) -> int:
        executor = self._create_migration_executor(args)
        status = executor.apply_all(dry_run=bool(args.dry_run))
        print(json.dumps(status.as_dict(), sort_keys=True))
        return 0

    def _handle_database_ha_plan(self, args: argparse.Namespace) -> int:
        report = InstallerConfigValidator().validate_file(args.path, args.edition, args.scope)
        if not report.valid:
            print(json.dumps(report.as_dict(), sort_keys=True, indent=2))
            return 2
        payload = {
            "edition": report.edition,
            "scope": report.scope,
            "managed_postgresql": report.postgresql_plan is not None,
            "postgresql_ha": (
                report.postgresql_ha_plan.as_dict()
                if report.postgresql_ha_plan is not None
                else None
            ),
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0 if report.postgresql_ha_plan is not None else 2

    def _handle_auth_policy(self, args: argparse.Namespace) -> int:
        directory_config = None
        if args.mode in {"ldap", "ipa"}:
            if not args.url or not args.base_dn:
                raise OpenInfraError("LDAP/IPA mode requires --url and --base-dn")
            directory_config = ExternalDirectoryConfig.create(
                mode=args.mode,
                url=args.url,
                base_dn=args.base_dn,
                user_filter=args.user_filter,
                group_filter=args.group_filter,
                bind_dn_ref=args.bind_dn_ref,
                bind_password_ref=args.bind_password_ref,
                ca_cert_ref=args.ca_cert_ref,
                nested_groups=not bool(args.no_nested_groups),
                cache_ttl_seconds=args.cache_ttl_seconds,
            )
        application = self._create_application(args)
        payload = application.auth_provider_policy_service.validate(
            AuthProviderPolicyCommand(
                edition=args.edition,
                mode=args.mode,
                directory_config=directory_config,
            )
        )
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0

    def _handle_security_bootstrap_token(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        roles = tuple(args.role) if args.role else ("admin",)
        result = application.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                subject=args.subject,
                roles=roles,
                token=args.token,
                ttl_seconds=args.ttl_seconds,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_security_whoami(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        principal = application.security_service.inspect_token(args.tenant, args.token)
        print(json.dumps(principal.as_dict(), sort_keys=True))
        return 0

    def _handle_security_revoke_token(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.security_service.revoke_token(
            RevokeTokenCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                target_token=args.target_token,
                admin_token=args.admin_token,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_security_rotate_token(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.security_service.rotate_token(
            RotateTokenCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                current_token=args.current_token,
                subject=args.subject,
                roles=tuple(args.role),
                token=args.token,
                ttl_seconds=args.ttl_seconds,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_security_list_tokens(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.security_service.list_tokens(
            ListTokensCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=bool(args.include_inactive),
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_create_user(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        user = application.identity_service.create_user(
            CreateUserCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                username=args.username,
                display_name=args.display_name,
                email=args.email,
                roles=tuple(args.role),
            )
        )
        print(json.dumps(user.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_create_group(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        group = application.identity_service.create_group(
            CreateGroupCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                display_name=args.display_name,
                roles=tuple(args.role),
            )
        )
        print(json.dumps(group.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_add_user_to_group(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        membership = application.identity_service.add_user_to_group(
            AddUserToGroupCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                username=args.username,
                group_name=args.group,
            )
        )
        print(json.dumps(membership.as_dict(), sort_keys=True))
        return 0

    def _handle_identity_grant_user_role(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.identity_service.grant_user_role(
            GrantUserRoleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                username=args.username,
                role=args.role,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_identity_grant_group_role(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.identity_service.grant_group_role(
            GrantGroupRoleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                group_name=args.group,
                role=args.role,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_identity_effective(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        identity = application.identity_service.effective_identity(
            EffectiveIdentityCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                subject=args.subject,
            )
        )
        print(json.dumps(identity.as_dict(), sort_keys=True))
        return 0

    def _handle_access_create_rule(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        subjects = tuple(args.subject) if args.subject else ("*",)
        rule = application.access_policy_service.create_rule(
            CreateAccessPolicyRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                permission=args.permission,
                effect=args.effect,
                subjects=subjects,
                roles=tuple(args.role),
                site_codes=tuple(args.site_code),
                environments=tuple(args.environment),
            )
        )
        print(json.dumps(rule.as_dict(), sort_keys=True))
        return 0

    def _handle_access_list_rules(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.access_policy_service.list_rules(
            ListAccessPolicyRulesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=bool(args.include_inactive),
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_access_deactivate_rule(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.access_policy_service.deactivate_rule(
            DeactivateAccessPolicyRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_access_evaluate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand(
                tenant_id=args.tenant,
                token=args.token,
                permission=args.permission,
                site_code=args.site_code,
                environment=args.environment,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_audit_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        page = application.audit_service.list_events(
            ListAuditEventsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                actor=args.actor,
                action=args.action,
                target_type=args.target_type,
                target_id=args.target_id,
                severity=args.severity,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_audit_export(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        bundle = application.audit_service.export_events(
            ExportAuditEventsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                format=args.format,
                limit=args.limit,
                cursor=args.cursor,
                actor=args.actor,
                action=args.action,
                target_type=args.target_type,
                target_id=args.target_id,
                severity=args.severity,
            )
        )
        print(json.dumps(bundle.as_dict(), sort_keys=True))
        return 0

    def _handle_audit_verify_integrity(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.audit_service.verify_integrity(
            VerifyAuditIntegrityCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
            )
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0

    def _handle_import_dataset(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.import_dataset(
            ImportDatasetCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                file_path=args.file,
                format=args.format,
                mapping_json=args.mapping_json,
                dry_run=not bool(args.apply),
                batch_size=args.batch_size,
            )
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_report(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.get_report(args.tenant, args.job_id)
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_bulk_dataset(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.bulk_import_dataset(
            BulkImportDatasetCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                file_path=args.file,
                format=args.format,
                mapping_json=args.mapping_json,
                dry_run=not bool(args.apply),
                batch_size=args.batch_size,
                checkpoint_interval=args.checkpoint_interval,
                resume_job_id=args.resume_job_id,
                sample_limit=args.sample_limit,
            )
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_bulk_rollback(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.bulk_import_rollback(
            BulkImportRollbackCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                import_job_id=args.job_id,
                file_path=args.file,
                format=args.format,
                mapping_json=args.mapping_json,
                dry_run=not bool(args.apply),
                conflict_policy=args.conflict_policy,
            )
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_bulk_report(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.get_bulk_report(args.tenant, args.job_id)
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_bulk_checkpoint(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        checkpoint = app.import_service.get_bulk_checkpoint(args.tenant, args.job_id)
        print(json.dumps(checkpoint.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_bulk_progress(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        progress = app.import_service.get_bulk_progress(args.tenant, args.job_id)
        print(json.dumps(progress.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_migration_template(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        template = app.import_service.get_migration_template(
            MigrationTemplateCommand(source=args.source)
        )
        print(json.dumps(template.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_migration_guide(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        guide = app.import_service.get_migration_guide(MigrationGuideCommand(source=args.source))
        print(json.dumps(guide.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_migration_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.plan_migration(
            PlanMigrationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                source=args.source,
                file_path=args.file,
                format=args.format,
                sample_limit=args.sample_limit,
            )
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_import_migration_report(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.import_service.get_migration_plan(args.tenant, args.job_id)
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_itsm_providers(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        print(
            json.dumps(
                {
                    "items": [
                        policy.as_dict() for policy in app.external_itsm_service.list_policies()
                    ]
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    def _handle_integrations_servicenow_validate(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.external_itsm_service.validate_servicenow_connector(
            ValidateServiceNowConnectorCommand(
                tenant_id=args.tenant,
                instance_url=args.instance_url,
                table_name=args.table_name,
                auth_secret_ref=args.auth_secret_ref,
                enabled=not args.disabled,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_servicenow_ci_sync_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.external_itsm_service.build_servicenow_ci_sync_plan(
            BuildServiceNowCiSyncPlanCommand(
                tenant_id=args.tenant,
                resource_key=args.resource_key,
                direction=args.direction,
                target_table=args.target_table,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_jira_validate(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.external_itsm_service.validate_jira_service_management_connector(
            ValidateJiraServiceManagementConnectorCommand(
                tenant_id=args.tenant,
                instance_url=args.instance_url,
                object_type=args.object_type,
                auth_secret_ref=args.auth_secret_ref,
                enabled=not args.disabled,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_jira_asset_sync_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.external_itsm_service.build_jira_service_management_asset_sync_plan(
            BuildJiraServiceManagementAssetSyncPlanCommand(
                tenant_id=args.tenant,
                resource_key=args.resource_key,
                direction=args.direction,
                object_type=args.object_type,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_glpi_validate(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.external_itsm_service.validate_glpi_connector(
            ValidateGlpiConnectorCommand(
                tenant_id=args.tenant,
                instance_url=args.instance_url,
                item_type=args.item_type,
                auth_secret_ref=args.auth_secret_ref,
                enabled=not args.disabled,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_glpi_asset_sync_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.external_itsm_service.build_glpi_asset_sync_plan(
            BuildGlpiAssetSyncPlanCommand(
                tenant_id=args.tenant,
                resource_key=args.resource_key,
                direction=args.direction,
                item_type=args.item_type,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_freshservice_validate(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.external_itsm_service.validate_freshservice_connector(
            ValidateFreshserviceConnectorCommand(
                tenant_id=args.tenant,
                instance_url=args.instance_url,
                asset_type=args.asset_type,
                auth_secret_ref=args.auth_secret_ref,
                enabled=not args.disabled,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_freshservice_asset_sync_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.external_itsm_service.build_freshservice_asset_sync_plan(
            BuildFreshserviceAssetSyncPlanCommand(
                tenant_id=args.tenant,
                resource_key=args.resource_key,
                direction=args.direction,
                asset_type=args.asset_type,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_openservice_validate(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.external_itsm_service.validate_openservice_connector(
            ValidateOpenServiceConnectorCommand(
                tenant_id=args.tenant,
                instance_url=args.instance_url,
                collection=args.collection,
                auth_secret_ref=args.auth_secret_ref,
                enabled=not args.disabled,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_integrations_openservice_cmdb_sync_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.external_itsm_service.build_openservice_cmdb_sync_plan(
            BuildOpenServiceCmdbSyncPlanCommand(
                tenant_id=args.tenant,
                resource_key=args.resource_key,
                direction=args.direction,
                collection=args.collection,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_collector_register(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        collector = app.discovery_service.register_collector(
            RegisterCollectorCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                kind=args.kind,
                certificate_fingerprint=args.certificate_fingerprint,
                scopes=tuple(args.scope),
                version=args.version,
                vault_secret_ref=args.vault_secret_ref,
                endpoint_url=args.endpoint_url,
            )
        )
        print(json.dumps(collector.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_proxy_enroll_local(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        collector = app.discovery_service.enroll_proxy(
            EnrollDiscoveryProxyCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                kind=args.kind,
                certificate_fingerprint=args.certificate_fingerprint,
                scopes=tuple(args.scope),
                version=args.version,
                vault_secret_ref=args.vault_secret_ref,
                endpoint_url=args.endpoint_url,
            )
        )
        print(json.dumps(collector.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_proxy_enroll(self, args: argparse.Namespace) -> int:
        if args.edition != "enterprise":
            raise OpenInfraError("proxy CLI enrollment requires the Enterprise edition")
        payload = ProxyEnrollmentPayloadFactory().from_args(args)
        result = ProxyEnrollmentHttpClient().enroll_many(
            backend_urls=tuple(args.backend_url),
            admin_token=args.admin_token,
            payload=payload,
            timeout_seconds=args.timeout_seconds,
        )
        if args.config_output is not None:
            ProxyEnrollmentConfigWriter().write(args.config_output, result)
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0 if result.enrolled else 2

    def _handle_discovery_proxy_enroll_verify(self, args: argparse.Namespace) -> int:
        if args.edition != "enterprise":
            raise OpenInfraError(
                "proxy enrollment config verification requires the Enterprise edition"
            )
        report = ProxyEnrollmentConfigValidator().validate(
            args.config,
            strict=not args.allow_partial,
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0 if report.valid else 2

    def _handle_search_global(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        result = app.global_search_service.search(
            GlobalSearchCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                query=args.query,
                limit=args.limit,
                include_inactive_discovery=args.include_inactive_discovery,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_organizations(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        catalog = app.itam_support_service.list_organizations(
            ListItamOrganizationsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                include_retired=args.include_retired,
            )
        )
        print(json.dumps(catalog.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_organization_create(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        organization = app.itam_support_service.create_organization(
            CreateItamOrganizationCommand(
                organization_id=args.organization,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
                legal_name=args.legal_name,
                display_name=args.display_name,
                status=args.status,
                registration_number=args.registration_number,
                tax_identifier=args.tax_identifier,
                country_code=args.country_code,
                city=args.city,
                postal_code=args.postal_code,
                address=args.address,
                contact_email=args.contact_email,
                phone=args.phone,
                support_contact=args.support_contact,
                description=args.description,
            )
        )
        print(json.dumps(organization.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_organization(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        organization = app.itam_support_service.get_organization(
            GetItamOrganizationCommand(
                organization_id=args.organization,
                scope_tenant_id=args.tenant,
                admin_token=args.admin_token,
            )
        )
        print(json.dumps(organization.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_organization_update(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        organization = app.itam_support_service.update_organization(
            UpdateItamOrganizationCommand(
                organization_id=args.organization,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
                legal_name=args.legal_name,
                display_name=args.display_name,
                status=args.status,
                registration_number=args.registration_number,
                tax_identifier=args.tax_identifier,
                country_code=args.country_code,
                city=args.city,
                postal_code=args.postal_code,
                address=args.address,
                contact_email=args.contact_email,
                phone=args.phone,
                support_contact=args.support_contact,
                description=args.description,
            )
        )
        print(json.dumps(organization.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_organization_delete(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        organization = app.itam_support_service.delete_organization(
            DeleteItamOrganizationCommand(
                organization_id=args.organization,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
            )
        )
        print(json.dumps(organization.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_partners(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        catalog = app.itam_support_service.list_partners(
            ListItamPartnersCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                organization_id=args.organization,
                kind=args.kind,
                include_retired=args.include_retired,
            )
        )
        print(json.dumps(catalog.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_partner_create(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        partner = app.itam_support_service.create_partner(
            CreateItamPartnerCommand(
                organization_id=args.organization,
                partner_id=args.partner,
                kind=args.kind,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
                legal_name=args.legal_name,
                display_name=args.display_name,
                status=args.status,
                registration_number=args.registration_number,
                tax_identifier=args.tax_identifier,
                country_code=args.country_code,
                city=args.city,
                postal_code=args.postal_code,
                address=args.address,
                contact_email=args.contact_email,
                phone=args.phone,
                support_contact=args.support_contact,
                website=args.website,
                description=args.description,
            )
        )
        print(json.dumps(partner.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_partner(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        partner = app.itam_support_service.get_partner(
            GetItamPartnerCommand(
                organization_id=args.organization,
                partner_id=args.partner,
                scope_tenant_id=args.tenant,
                admin_token=args.admin_token,
            )
        )
        print(json.dumps(partner.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_partner_update(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        partner = app.itam_support_service.update_partner(
            UpdateItamPartnerCommand(
                organization_id=args.organization,
                partner_id=args.partner,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
                kind=args.kind,
                legal_name=args.legal_name,
                display_name=args.display_name,
                status=args.status,
                registration_number=args.registration_number,
                tax_identifier=args.tax_identifier,
                country_code=args.country_code,
                city=args.city,
                postal_code=args.postal_code,
                address=args.address,
                contact_email=args.contact_email,
                phone=args.phone,
                support_contact=args.support_contact,
                website=args.website,
                description=args.description,
            )
        )
        print(json.dumps(partner.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_partner_delete(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        partner = app.itam_support_service.delete_partner(
            DeleteItamPartnerCommand(
                organization_id=args.organization,
                partner_id=args.partner,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
            )
        )
        print(json.dumps(partner.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_tenants(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        catalog = app.itam_support_service.list_tenants(
            ListItamTenantsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                include_retired=args.include_retired,
            )
        )
        print(json.dumps(catalog.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_tenant_create(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        tenant = app.itam_support_service.create_tenant(
            CreateItamTenantCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                scope_tenant_id=args.scope_tenant,
                organization_id=args.organization,
                status=args.status,
                is_default=args.is_default,
                description=args.description,
            )
        )
        print(json.dumps(tenant.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_tenant(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        tenant = app.itam_support_service.get_tenant(
            GetItamTenantCommand(tenant_id=args.tenant, admin_token=args.admin_token)
        )
        print(json.dumps(tenant.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_tenant_update(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        is_default = None
        if args.is_default:
            is_default = True
        elif args.clear_default:
            is_default = False
        tenant = app.itam_support_service.update_tenant(
            UpdateItamTenantCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
                organization_id=args.organization,
                name=args.name,
                status=args.status,
                is_default=is_default,
                description=args.description,
            )
        )
        print(json.dumps(tenant.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_tenant_delete(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        tenant = app.itam_support_service.delete_tenant(
            DeleteItamTenantCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                scope_tenant_id=args.scope_tenant,
            )
        )
        print(json.dumps(tenant.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_register_manufacturer_support(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.itam_support_service.register_manufacturer_support(
            RegisterManufacturerSupportCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                asset_tag=args.asset_tag,
                manufacturer=args.manufacturer,
                manufacturer_partner_id=args.manufacturer_partner_id,
                warranty_reference=args.warranty_reference,
                warranty_level=args.warranty_level,
                warranty_start=args.warranty_start,
                warranty_end=args.warranty_end,
                support_reference=args.support_reference,
                support_level=args.support_level,
                support_contact=args.support_contact,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_add_third_party_support(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.itam_support_service.add_third_party_support(
            AddThirdPartySupportCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                asset_tag=args.asset_tag,
                provider=args.provider,
                provider_partner_id=args.provider_partner_id,
                contract_reference=args.contract_reference,
                support_level=args.support_level,
                support_start=args.support_start,
                support_end=args.support_end,
                support_contact=args.support_contact,
                status=args.status,
                notes=args.notes,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_support_profile(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.itam_support_service.get_support_profile(
            GetAssetSupportProfileCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                asset_tag=args.asset_tag,
            )
        )
        print(json.dumps(profile.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_support_coverage(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.itam_support_service.get_support_coverage_report(
            GetAssetSupportCoverageReportCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                asset_tag=args.asset_tag,
                as_of=args.as_of,
            )
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_register_software_license(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        license_ = app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                product_name=args.product_name,
                vendor=args.vendor,
                vendor_partner_id=args.vendor_partner_id,
                license_reference=args.license_reference,
                metric=args.metric,
                purchased_quantity=args.purchased_quantity,
                assigned_quantity=args.assigned_quantity,
                entitlement_start=args.entitlement_start,
                entitlement_end=args.entitlement_end,
                contract_reference=args.contract_reference,
                version=args.version,
                status=args.status,
                owner=args.owner,
                notes=args.notes,
            )
        )
        print(json.dumps(license_.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_update_license_assignment(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        license_ = app.itam_support_service.update_software_license_assignment(
            UpdateSoftwareLicenseAssignmentCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                license_reference=args.license_reference,
                assigned_quantity=args.assigned_quantity,
                notes=args.notes,
            )
        )
        print(json.dumps(license_.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_software_license(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        license_ = app.itam_support_service.get_software_license(
            GetSoftwareLicenseCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                license_reference=args.license_reference,
            )
        )
        print(json.dumps(license_.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_itam_software_license_compliance(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        report = app.itam_support_service.get_software_license_compliance(
            GetSoftwareLicenseComplianceCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                license_reference=args.license_reference,
                as_of=args.as_of,
            )
        )
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_evidence_submit(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        payload = self._parse_json_object(args.payload_json, "payload-json")
        evidence = app.discovery_service.submit_evidence(
            SubmitDiscoveryEvidenceCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                evidence_id=args.evidence_id,
                object_key=args.object_key,
                object_kind=args.object_kind,
                source=args.source,
                source_ref=args.source_ref,
                scope=args.scope,
                external_id=args.external_id,
                confidence=args.confidence,
                payload=payload,
                observed_at=args.observed_at,
            )
        )
        print(json.dumps(evidence.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_evidence_get(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        evidence = app.discovery_service.get_evidence(
            GetDiscoveryEvidenceCommand(args.tenant, args.admin_token, args.evidence_id)
        )
        print(json.dumps(evidence.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_evidence_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        page = app.discovery_service.list_evidence(
            ListDiscoveryEvidenceCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                object_key=args.object_key,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(page.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_reconcile(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        case = app.discovery_service.reconcile_evidence(
            ReconcileDiscoveryEvidenceCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                object_key=args.object_key,
                evidence_ids=tuple(args.evidence_id),
                max_age_seconds=args.max_age_seconds,
            )
        )
        print(json.dumps(case.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_reconciliation_get(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        case = app.discovery_service.get_reconciliation(
            GetDiscoveryReconciliationCommand(args.tenant, args.admin_token, args.case_id)
        )
        print(json.dumps(case.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_reconciliation_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        page = app.discovery_service.list_reconciliations(
            ListDiscoveryReconciliationsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                status=args.status,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(page.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_reconciliation_resolve(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        raw = self._parse_json_object(args.selections_json, "selections-json")
        selections = {str(key): str(value) for key, value in raw.items()}
        case = app.discovery_service.resolve_reconciliation(
            ResolveDiscoveryReconciliationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                case_id=args.case_id,
                selected_evidence_by_path=selections,
                justification=args.justification,
            )
        )
        print(json.dumps(case.as_dict(), indent=2, sort_keys=True))
        return 0

    @staticmethod
    def _parse_json_object(value: str, label: str) -> dict[str, Any]:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError(label + " must contain valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValidationError(label + " must be a JSON object")
        return {str(key): item for key, item in decoded.items()}

    def _handle_discovery_protocol_profile_create(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.create_protocol_profile(
            CreateDiscoveryProtocolProfileCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                protocol=args.protocol,
                scope=args.scope,
                credential_secret_ref=args.credential_secret_ref,
                port=args.port,
                timeout_seconds=args.timeout_seconds,
                max_concurrency=args.max_concurrency,
                rate_limit_per_minute=args.rate_limit_per_minute,
                retry_count=args.retry_count,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_protocol_profile_update(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.update_protocol_profile(
            UpdateDiscoveryProtocolProfileCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                profile_id=args.profile_id,
                name=args.name,
                scope=args.scope,
                credential_secret_ref=args.credential_secret_ref,
                port=args.port,
                timeout_seconds=args.timeout_seconds,
                max_concurrency=args.max_concurrency,
                rate_limit_per_minute=args.rate_limit_per_minute,
                retry_count=args.retry_count,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_protocol_profile_get(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.get_protocol_profile(
            GetDiscoveryProtocolProfileCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                profile_id=args.profile_id,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_protocol_profile_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        page = app.discovery_service.list_protocol_profiles(
            ListDiscoveryProtocolProfilesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=args.include_inactive,
            )
        )
        print(json.dumps(page.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_protocol_profile_delete(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.disable_protocol_profile(
            DisableDiscoveryProtocolProfileCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                profile_id=args.profile_id,
                reason=args.reason,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    @staticmethod
    def _optional_bool(value: str | None) -> bool | None:
        if value is None:
            return None
        return value.lower() == "true"

    def _handle_discovery_integration_profile_create(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.create_integration_profile(
            CreateDiscoveryIntegrationProfileCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                kind=args.kind,
                scope=args.scope,
                endpoint_url=args.endpoint_url,
                credential_secret_ref=args.credential_secret_ref,
                verify_tls=not args.no_verify_tls,
                inventory_enabled=not args.disable_inventory,
                max_concurrency=args.max_concurrency,
                rate_limit_per_minute=args.rate_limit_per_minute,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_integration_profile_update(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.update_integration_profile(
            UpdateDiscoveryIntegrationProfileCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                profile_id=args.profile_id,
                name=args.name,
                scope=args.scope,
                endpoint_url=args.endpoint_url,
                credential_secret_ref=args.credential_secret_ref,
                verify_tls=self._optional_bool(args.verify_tls),
                inventory_enabled=self._optional_bool(args.inventory_enabled),
                max_concurrency=args.max_concurrency,
                rate_limit_per_minute=args.rate_limit_per_minute,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_integration_profile_get(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.get_integration_profile(
            GetDiscoveryIntegrationProfileCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                profile_id=args.profile_id,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_integration_profile_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        page = app.discovery_service.list_integration_profiles(
            ListDiscoveryIntegrationProfilesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=args.include_inactive,
            )
        )
        print(json.dumps(page.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_integration_profile_delete(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        profile = app.discovery_service.disable_integration_profile(
            DisableDiscoveryIntegrationProfileCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                profile_id=args.profile_id,
                reason=args.reason,
            )
        )
        print(json.dumps(profile.as_public_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_local_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.discovery_service.build_local_discovery_plan(
            BuildLocalDiscoveryPlanCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                scope=args.scope,
                protocol=args.protocol,
                targets=tuple(args.target),
                credential_secret_ref=args.credential_secret_ref,
                max_concurrency=args.max_concurrency,
                rate_limit_per_minute=args.rate_limit_per_minute,
                protocol_profile_id=args.protocol_profile_id,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_agent_bootstrap_plan(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        plan = app.discovery_service.build_enterprise_agent_bootstrap_plan(
            BuildEnterpriseAgentBootstrapPlanCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                role=args.role,
                scopes=tuple(args.scope),
                backend_url=args.backend_url,
                certificate_fingerprint=args.certificate_fingerprint,
                enrollment_secret_ref=args.enrollment_secret_ref,
                agent_version=args.agent_version,
                service_user=args.service_user,
                config_path=args.config_path,
                state_directory=args.state_directory,
                log_directory=args.log_directory,
            )
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_collector_heartbeat(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        collector = app.discovery_service.heartbeat(
            HeartbeatCollectorCommand(
                tenant_id=args.tenant,
                collector_id=args.collector_id,
                certificate_fingerprint=args.certificate_fingerprint,
                version=args.version,
                status=args.status,
            )
        )
        print(json.dumps(collector.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_authorize(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        decision = app.discovery_service.authorize_job(
            AuthorizeDiscoveryJobCommand(
                tenant_id=args.tenant,
                collector_id=args.collector_id,
                certificate_fingerprint=args.certificate_fingerprint,
                requested_scope=args.requested_scope,
                job_type=args.job_type,
                target=args.target,
            )
        )
        print(json.dumps(decision.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_submit(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                collector_id=args.collector_id,
                requested_scope=args.requested_scope,
                job_type=args.job_type,
                target=args.target,
                idempotency_key=args.idempotency_key,
                max_attempts=args.max_attempts,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_claim(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.claim_job(
            ClaimDiscoveryJobCommand(
                tenant_id=args.tenant,
                collector_id=args.collector_id,
                certificate_fingerprint=args.certificate_fingerprint,
                worker_id=args.worker_id,
                lease_seconds=args.lease_seconds,
            )
        )
        print(json.dumps(None if job is None else job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_renew(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.renew_job_lease(
            RenewDiscoveryJobLeaseCommand(
                tenant_id=args.tenant,
                collector_id=args.collector_id,
                certificate_fingerprint=args.certificate_fingerprint,
                job_id=args.job_id,
                worker_id=args.worker_id,
                lease_token=args.lease_token,
                lease_seconds=args.lease_seconds,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_complete(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.complete_job(
            CompleteDiscoveryJobCommand(
                tenant_id=args.tenant,
                collector_id=args.collector_id,
                certificate_fingerprint=args.certificate_fingerprint,
                job_id=args.job_id,
                worker_id=args.worker_id,
                lease_token=args.lease_token,
                result_hash=args.result_hash,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_fail(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.fail_job(
            FailDiscoveryJobCommand(
                tenant_id=args.tenant,
                collector_id=args.collector_id,
                certificate_fingerprint=args.certificate_fingerprint,
                job_id=args.job_id,
                worker_id=args.worker_id,
                lease_token=args.lease_token,
                error=args.error,
                retry_delay_seconds=args.retry_delay_seconds,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_get(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.get_job(
            GetDiscoveryJobCommand(args.tenant, args.admin_token, args.job_id)
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        page = app.discovery_service.list_jobs(
            ListDiscoveryJobsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                status=args.status,
            )
        )
        print(json.dumps(page.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_job_replay(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.discovery_service.replay_dead_letter_job(
            ReplayDiscoveryDeadLetterJobCommand(
                args.tenant, args.actor, args.admin_token, args.job_id
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_collector_disable(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        collector = app.discovery_service.disable_collector(
            DisableCollectorCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                collector_id=args.collector_id,
                reason=args.reason,
            )
        )
        print(json.dumps(collector.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_discovery_collector_list(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        page = app.discovery_service.list_collectors(
            ListCollectorsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=args.include_inactive,
            )
        )
        print(json.dumps(page.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_export_request(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.export_service.request_export(
            RequestExportCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                resource=args.resource,
                format=args.format,
                kind=args.kind,
                tag=args.tag,
                limit=args.limit,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_export_run(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.export_service.run_export_job(
            RunExportJobCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                job_id=args.job_id,
                page_size=args.page_size,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_export_report(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        job = app.export_service.get_export_job(
            GetExportJobCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                job_id=args.job_id,
            )
        )
        print(json.dumps(job.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_export_artifact(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        download = app.export_service.get_export_artifact(
            GetExportArtifactCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                job_id=args.job_id,
            )
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(download.content)
        print(json.dumps(download.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_export_artifact_chunk(self, args: argparse.Namespace) -> int:
        app = self._create_application(args)
        download = app.export_service.get_export_artifact_chunk(
            GetExportArtifactChunkCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                job_id=args.job_id,
                offset=args.offset,
                size=args.size,
            )
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(download.content)
        print(json.dumps(download.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_network_config_baseline_upsert(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.network_config_compliance_service.upsert_baseline(
            UpsertNetworkConfigBaselineCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                code=args.code,
                device_object_key=args.device_object_key,
                platform=args.platform,
                expected_config=args.expected_config_file.read_text(encoding="utf-8"),
                ignored_paths=tuple(args.ignored_path),
                critical_paths=tuple(args.critical_path),
                owner=args.owner,
                justification=args.justification,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_network_config_baseline_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.network_config_compliance_service.list_baselines(
            ListNetworkConfigBaselinesCommand(
                args.tenant, args.admin_token, args.limit, args.cursor, args.include_retired
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_network_config_baseline_retire(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.network_config_compliance_service.retire_baseline(
            RetireNetworkConfigBaselineCommand(
                args.tenant, args.actor, args.admin_token, args.baseline_id
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_network_config_observation_submit(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.network_config_compliance_service.submit_observation(
            SubmitNetworkConfigObservationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                idempotency_key=args.idempotency_key,
                source=args.source,
                collector=args.collector,
                device_object_key=args.device_object_key,
                platform=args.platform,
                observed_config=args.observed_config_file.read_text(encoding="utf-8"),
                observed_at=args.observed_at,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_network_config_observation_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.network_config_compliance_service.list_observations(
            ListNetworkConfigObservationsCommand(
                args.tenant,
                args.admin_token,
                args.limit,
                args.cursor,
                args.device_object_key,
                args.platform,
                args.observed_before,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_network_config_assess(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.network_config_compliance_service.assess(
            AssessNetworkConfigComplianceCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                actor=args.actor,
                baseline_code=args.baseline_code,
                as_of=args.as_of,
                status=args.status,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_import(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.import_bundle(
            ImportCertificateBundleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                pem_bundle=args.pem_file.read_text(encoding="utf-8"),
                owner=args.owner,
                environment=args.environment,
                source=args.source,
                object_key=args.object_key,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_get(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.get_certificate(
            GetCertificateCommand(args.tenant, args.admin_token, args.fingerprint)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.list_certificates(
            ListCertificatesCommand(
                args.tenant,
                args.admin_token,
                args.limit,
                args.cursor,
                args.include_retired,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_retire(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.retire_certificate(
            RetireCertificateCommand(args.tenant, args.actor, args.admin_token, args.fingerprint)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_endpoint_observe(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.observe_endpoint(
            ObserveCertificateEndpointCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                idempotency_key=args.idempotency_key,
                protocol=args.protocol,
                host=args.host,
                port=args.port,
                service=args.service,
                certificate_fingerprint=args.certificate_fingerprint,
                observed_at=args.observed_at,
                source=args.source,
                collector=args.collector,
                object_key=args.object_key,
                tls_version=args.tls_version,
                cipher=args.cipher,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_endpoint_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.list_endpoints(
            ListCertificateEndpointsCommand(
                args.tenant,
                args.admin_token,
                args.limit,
                args.cursor,
                args.certificate_fingerprint,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_certificate_assess(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.certificate_pki_service.assess(
            AssessCertificatesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                as_of=args.as_of,
                critical_days=args.critical_days,
                warning_days=args.warning_days,
                health=args.health,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_flow_declaration_upsert(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.flow_matrix_service.upsert_declaration(
            UpsertFlowDeclarationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                code=args.code,
                source_selector=args.source_selector,
                destination_selector=args.destination_selector,
                protocol=args.protocol,
                destination_port_start=args.destination_port_start,
                destination_port_end=args.destination_port_end,
                decision=args.decision,
                priority=args.priority,
                owner=args.owner,
                justification=args.justification,
                valid_from=args.valid_from,
                valid_to=args.valid_to,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_flow_declaration_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.flow_matrix_service.list_declarations(
            ListFlowDeclarationsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_retired=args.include_retired,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_flow_declaration_retire(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.flow_matrix_service.retire_declaration(
            RetireFlowDeclarationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                declaration_id=args.declaration_id,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_flow_observation_submit(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.flow_matrix_service.submit_observation(
            SubmitFlowObservationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                idempotency_key=args.idempotency_key,
                source=args.source,
                collector=args.collector,
                source_ip=args.source_ip,
                destination_ip=args.destination_ip,
                source_object_key=args.source_object_key,
                destination_object_key=args.destination_object_key,
                protocol=args.protocol,
                destination_port=args.destination_port,
                packets=args.packets,
                bytes_count=args.bytes_count,
                first_seen=args.first_seen,
                last_seen=args.last_seen,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_flow_observation_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.flow_matrix_service.list_observations(
            ListFlowObservationsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                window_start=args.window_start,
                window_end=args.window_end,
                limit=args.limit,
                cursor=args.cursor,
                source=args.source,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_flow_matrix(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.flow_matrix_service.compare(
            CompareFlowMatrixCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                window_start=args.window_start,
                window_end=args.window_end,
                limit=args.limit,
                cursor=args.cursor,
                status=args.status,
                source=args.source,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    @staticmethod
    def _read_simulation_changes(path: Path) -> tuple[dict[str, Any], ...]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ValidationError(f"cannot read simulation changes file: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ValidationError(f"simulation changes file is invalid JSON: {exc}") from exc
        if not isinstance(payload, list) or not payload:
            raise ValidationError("simulation changes file must contain a non-empty JSON array")
        changes: list[dict[str, Any]] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValidationError(f"simulation change at index {index} must be a JSON object")
            changes.append(dict(item))
        return tuple(changes)

    def _handle_simulation_create(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.create_scenario(
            CreateSimulationScenarioCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                description=args.description,
                owner=args.owner,
                idempotency_key=args.idempotency_key,
                changes=self._read_simulation_changes(args.changes_file),
                site=args.site,
                environment=args.environment,
                criticality=args.criticality,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_list(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.list_scenarios(
            ListSimulationScenariosCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                status=args.status,
                site=args.site,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_get(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.get_scenario(
            GetSimulationScenarioCommand(args.tenant, args.admin_token, args.scenario_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_run(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.run_scenario(
            RunSimulationScenarioCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                scenario_id=args.scenario_id,
                max_depth=args.max_depth,
                max_nodes=args.max_nodes,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_cancel(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.cancel_scenario(
            CancelSimulationScenarioCommand(
                args.tenant, args.actor, args.admin_token, args.scenario_id
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_report(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.get_report(
            GetSimulationReportCommand(args.tenant, args.admin_token, args.report_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_reports(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.list_reports(
            ListSimulationReportsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                scenario_id=args.scenario_id,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_compare(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.compare_reports(
            CompareSimulationReportsCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                left_report_id=args.left_report_id,
                right_report_id=args.right_report_id,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_simulation_comparisons(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.simulation_service.list_comparisons(
            ListSimulationComparisonsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_graph_traverse(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dependency_graph_service.traverse(
            TraverseDependencyGraphCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                root_key=args.root_key,
                direction=args.direction,
                max_depth=args.max_depth,
                max_nodes=args.max_nodes,
                relation_types=tuple(args.relation_type),
                as_of=args.as_of,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_graph_impact(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dependency_graph_service.impact(
            AnalyzeDependencyImpactCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                root_key=args.root_key,
                direction=args.direction,
                max_depth=args.max_depth,
                max_nodes=args.max_nodes,
                relation_types=tuple(args.relation_type),
                as_of=args.as_of,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_graph_spof(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dependency_graph_service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                root_key=args.root_key,
                direction=args.direction,
                max_depth=args.max_depth,
                max_nodes=args.max_nodes,
                relation_types=tuple(args.relation_type),
                as_of=args.as_of,
                candidate_kinds=tuple(args.candidate_kind),
                candidate_resource_categories=tuple(args.candidate_resource_category),
                candidate_resource_types=tuple(args.candidate_resource_type),
                candidate_statuses=tuple(args.candidate_status),
                minimum_affected_nodes=args.minimum_affected_nodes,
                affected_sample_limit=args.affected_sample_limit,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_graph_export(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dependency_graph_service.export(
            ExportDependencyGraphCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                root_key=args.root_key,
                format=args.format,
                direction=args.direction,
                max_depth=args.max_depth,
                max_nodes=args.max_nodes,
                relation_types=tuple(args.relation_type),
                as_of=args.as_of,
                include_spof=bool(args.include_spof),
                candidate_kinds=tuple(args.candidate_kind),
                candidate_resource_categories=tuple(args.candidate_resource_category),
                candidate_resource_types=tuple(args.candidate_resource_type),
                candidate_statuses=tuple(args.candidate_status),
                minimum_affected_nodes=args.minimum_affected_nodes,
            )
        )
        if args.output is None:
            sys.stdout.buffer.write(result.content)
            return 0
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        try:
            temporary.write_bytes(result.content)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        print(json.dumps({**result.metadata(), "output": str(output)}, sort_keys=True))
        return 0

    def _handle_graph_path(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dependency_graph_service.find_path(
            FindDependencyPathCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                source_key=args.source_key,
                target_key=args.target_key,
                direction=args.direction,
                max_depth=args.max_depth,
                max_nodes=args.max_nodes,
                relation_types=tuple(args.relation_type),
                as_of=args.as_of,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _warn_legacy_inventory_alias(self, args: argparse.Namespace) -> None:
        if hasattr(args, "itrm_command"):
            sys.stderr.write(
                "DEPRECATION: 'openinfra itrm' is a legacy alias; use 'openinfra rsot'. "
                "The ITRM alias is scheduled for removal in a future major release.\n"
            )
        elif hasattr(args, "ri_command"):
            sys.stderr.write(
                "DEPRECATION: 'openinfra ri' is a legacy alias; use 'openinfra rsot'. "
                "The RI alias is scheduled for removal in a future major release.\n"
            )
        elif hasattr(args, "sot_command"):
            sys.stderr.write(
                "DEPRECATION: 'openinfra sot' is a legacy alias; use 'openinfra rsot'. "
                "The SOT alias is scheduled for removal in a future major release.\n"
            )

    def _handle_sot_resource_taxonomy(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        print(json.dumps(ResourceTaxonomy.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_upsert_object(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                key=args.key,
                kind=args.resource_category or args.kind or "",
                display_name=args.display_name,
                attributes_json=args.attributes_json,
                tags=tuple(args.tag),
                source=args.source,
                resource_category=args.resource_category,
                resource_type=args.resource_type,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_get_object(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_service.get_object(
            GetSourceObjectCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_list_objects(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        page = application.it_resources_management_service.list_objects(
            ListSourceObjectsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                kind=args.resource_category or args.kind,
                tag=args.tag,
                resource_type=args.resource_type,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_get_object_version(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_service.get_object_version(
            GetSourceObjectVersionCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
                version=args.version,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_get_object_as_of(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_service.get_object_as_of(
            GetSourceObjectAsOfCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
                as_of=args.as_of,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_list_object_audit(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        page = application.it_resources_management_service.list_object_audit(
            ListSourceObjectAuditCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
                limit=args.limit,
                cursor=args.cursor,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_reconcile_object(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_service.reconcile_object(
            ReconcileSourceObjectCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                key=args.key,
                attributes_json=args.attributes_json,
                source=args.source,
                display_name=args.display_name,
                tags=tuple(args.tag) if args.tag is not None else None,
                apply=bool(args.apply),
                resource_category=args.resource_category,
                resource_type=args.resource_type,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_create_relation(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_service.create_relation(
            CreateSourceRelationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                relation_type=args.relation_type,
                source_key=args.source_key,
                target_key=args.target_key,
                provenance=args.provenance,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_list_relations(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        page = application.it_resources_management_service.list_relations(
            ListSourceRelationsCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                source_key=args.source_key,
                target_key=args.target_key,
                relation_type=args.relation_type,
                as_of=args.as_of,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_create_governance_rule(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        rule = application.source_governance_service.create_rule(
            CreateSourceGovernanceRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
                object_kind=args.object_kind,
                attribute_path=args.attribute_path,
                authoritative_source=args.authoritative_source,
                priority=args.priority,
                freshness_seconds=args.freshness_seconds,
                conflict_strategy=args.conflict_strategy,
            )
        )
        print(json.dumps(rule.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_list_governance_rules(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        page = application.source_governance_service.list_rules(
            ListSourceGovernanceRulesCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                include_inactive=bool(args.include_inactive),
                object_kind=args.object_kind,
            )
        )
        print(json.dumps(page.as_dict(), sort_keys=True))
        return 0

    def _handle_sot_evaluate_governance(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.source_governance_service.evaluate(
            EvaluateSourceGovernanceCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                object_kind=args.object_kind,
                incoming_source=args.incoming_source,
                existing_attributes_json=args.existing_attributes_json,
                incoming_attributes_json=args.incoming_attributes_json,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_deactivate_governance_rule(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.source_governance_service.deactivate_rule(
            DeactivateSourceGovernanceRuleCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                admin_token=args.admin_token,
                name=args.name,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_quality_object(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        result = application.it_resources_management_quality_service.evaluate_object(
            EvaluateItrmObjectQualityCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                key=args.key,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_sot_quality_summary(self, args: argparse.Namespace) -> int:
        self._warn_legacy_inventory_alias(args)
        application = self._create_application(args)
        summary = application.it_resources_management_quality_service.summarize(
            ItrmQualitySummaryCommand(
                tenant_id=args.tenant,
                admin_token=args.admin_token,
                limit=args.limit,
                cursor=args.cursor,
                kind=args.resource_category or args.kind,
                tag=args.tag,
                resource_type=args.resource_type,
            )
        )
        print(json.dumps(summary.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_allocate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        actor = args.actor
        if args.auth_token:
            principal = application.security_service.authenticate_token(
                AuthenticateTokenCommand(args.tenant, args.auth_token, Permission.IPAM_ALLOCATE)
            )
            application.access_policy_service.authorize(
                principal,
                AccessRequestContext.create(
                    principal.tenant_id,
                    Permission.IPAM_ALLOCATE,
                    args.site_code,
                    args.environment,
                ),
            )
            actor = principal.subject
        result = application.ipam_service.allocate(
            AllocateIpCommand(
                tenant_id=args.tenant,
                actor=actor,
                vrf=args.vrf,
                prefix=args.prefix,
                hostname=args.hostname,
                idempotency_key=args.idempotency_key,
            )
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_define_vrf(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_vrf(
            DefineVrfCommand(args.tenant, args.actor, args.name, args.route_distinguisher)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_aggregate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_aggregate(
            DefineIpAggregateCommand(args.tenant, args.actor, args.vrf, args.cidr, args.description)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_prefix(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_prefix(
            DefineIpPrefixCommand(args.tenant, args.actor, args.vrf, args.cidr, args.description)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_range(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_range(
            DefineIpRangeCommand(
                args.tenant,
                args.actor,
                args.vrf,
                args.prefix,
                args.start,
                args.end,
                args.purpose,
                args.description,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_register_address(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.register_address(
            RegisterIpAddressCommand(
                args.tenant,
                args.actor,
                args.vrf,
                args.prefix,
                args.address,
                args.hostname,
                args.interface_name,
                args.status,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_list_prefixes(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        print(
            json.dumps(
                application.ipam_model_service.list_prefixes(args.tenant, args.vrf), sort_keys=True
            )
        )
        return 0

    def _handle_ipam_capacity(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.capacity(
            IpamCapacityCommand(args.tenant, args.vrf, args.prefix)
        )
        print(json.dumps(result.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_define_vlan_group(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_vlan_group(
            DefineVlanGroupCommand(args.tenant, args.actor, args.name, args.scope, args.description)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_vxlan_vni(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_vxlan_vni(
            DefineVxlanVniCommand(
                args.tenant,
                args.actor,
                args.vni,
                args.name,
                args.vrf,
                tuple(args.route_target_import),
                tuple(args.route_target_export),
                args.description,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_vlan(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_vlan(
            DefineVlanCommand(
                args.tenant,
                args.actor,
                args.group,
                args.vlan_id,
                args.name,
                args.vrf,
                args.vni,
                args.description,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_asn(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_asn(
            DefineAsnCommand(args.tenant, args.actor, args.asn, args.name, args.description)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_define_bgp_peer(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_model_service.define_bgp_peer(
            DefineBgpPeerCommand(
                args.tenant,
                args.actor,
                args.vrf,
                args.local_asn,
                args.remote_asn,
                args.peer_address,
                args.address_family,
                tuple(args.route_target_import),
                tuple(args.route_target_export),
                args.description,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_network_bindings(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.ipam_model_service.network_bindings(
            IpamNetworkBindingsCommand(args.tenant, args.vrf)
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_topology(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.ipam_model_service.topology(
            IpamTopologyCommand(args.tenant, args.actor, args.vrf)
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_observe_dns(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_conflict_service.observe_dns(
            ObserveDnsRecordCommand(
                args.tenant,
                args.actor,
                args.vrf,
                args.hostname,
                args.address,
                args.ptr_hostname,
                args.source,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_observe_dhcp_lease(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                args.tenant,
                args.actor,
                args.vrf,
                args.prefix,
                args.address,
                args.mac_address,
                args.hostname,
                args.source,
                not args.inactive,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_detect_conflicts(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.ipam_conflict_service.detect(
            DetectIpamConflictsCommand(args.tenant, args.actor, args.vrf)
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_ui_dashboard(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        command = IpamUiDashboardCommand(args.tenant, args.actor, args.vrf)
        if args.format == "html":
            print(application.ipam_ui_service.render_dashboard_html(command))
            return 0
        view = application.ipam_ui_service.dashboard(command)
        print(json.dumps(view.as_dict(), sort_keys=True))
        return 0

    def _handle_ipam_ui_search(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_ui_service.search(
            IpamSearchCommand(args.tenant, args.actor, args.query, args.vrf)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_reservation_wizard(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.ipam_ui_service.reservation_wizard(
            IpamReservationWizardCommand(
                args.tenant,
                args.actor,
                args.vrf,
                args.prefix,
                args.hostname,
                args.idempotency_key,
                not args.apply,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_ipam_ddi_preview(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        preview = application.ipam_ddi_service.preview_reservation(
            PreviewDdiReservationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                vrf=args.vrf,
                idempotency_key=args.idempotency_key,
                providers=tuple(args.provider or ["all"]),
                dns_zone=args.dns_zone,
                mac_address=args.mac_address,
                ttl=args.ttl,
                dry_run=not args.apply_preview,
            )
        )
        print(json.dumps(preview.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_field_sheet_list(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.list_sheets(
            ListFieldOperationSheetsCommand(
                args.tenant,
                args.admin_token,
                args.limit,
                args.cursor,
                args.status,
                args.target_type,
                args.site,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_sheet_get(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.get_sheet(
            GetFieldOperationSheetCommand(args.tenant, args.admin_token, args.sheet_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_sheet_generate(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.generate_sheet(
            GenerateFieldOperationSheetCommand(
                args.tenant,
                args.actor,
                args.admin_token,
                args.target_type,
                args.target_id,
                args.title,
                args.purpose,
                args.owner,
                args.operator,
                args.source_object_key,
                args.site,
                args.building,
                args.room,
                args.location_target_type,
                args.location_target_id,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_lock_acquire(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.acquire_lock(
            AcquireInterventionLockCommand(
                args.tenant,
                args.actor,
                args.admin_token,
                args.sheet_id,
                args.idempotency_key,
                args.ttl_seconds,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_start(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.start(
            StartFieldOperationCommand(args.tenant, args.actor, args.admin_token, args.sheet_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_checklist_record(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.record_checklist(
            RecordFieldChecklistCommand(
                args.tenant,
                args.actor,
                args.admin_token,
                args.sheet_id,
                args.item_id,
                args.result,
                args.operator_note,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_evidence_attach(self, args: argparse.Namespace) -> int:
        content = base64.b64encode(args.file.read_bytes()).decode("ascii")
        result = self._create_application(args).field_operation_service.attach_evidence(
            AttachFieldEvidenceCommand(
                args.tenant,
                args.actor,
                args.admin_token,
                args.sheet_id,
                args.phase,
                args.media_type,
                args.file.name,
                content,
                args.caption,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_evidence_list(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.list_evidence(
            GetFieldOperationSheetCommand(args.tenant, args.admin_token, args.sheet_id)
        )
        print(json.dumps({"items": [item.as_dict() for item in result]}, indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_evidence_validate(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.validate_evidence(
            ValidateFieldEvidenceCommand(
                args.tenant, args.actor, args.admin_token, args.evidence_id
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_complete(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.complete(
            CompleteFieldOperationCommand(args.tenant, args.actor, args.admin_token, args.sheet_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_cancel(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.cancel(
            CancelFieldOperationCommand(args.tenant, args.actor, args.admin_token, args.sheet_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_qr_verify(self, args: argparse.Namespace) -> int:
        payload = args.payload
        if args.payload_file is not None:
            payload = args.payload_file.read_text(encoding="utf-8")
        result = self._create_application(args).field_operation_service.verify_qr(
            VerifyFieldQrCommand(args.tenant, args.admin_token, args.sheet_id, payload or "")
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_lock_release(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.release_lock(
            ReleaseInterventionLockCommand(args.tenant, args.actor, args.admin_token, args.lock_id)
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_offline_create(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.create_offline_package(
            CreateOfflineSyncPackageCommand(
                args.tenant,
                args.actor,
                args.admin_token,
                args.sheet_id,
                args.idempotency_key,
                args.ttl_seconds,
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_offline_list(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.list_offline_packages(
            ListOfflineSyncPackagesCommand(
                args.tenant, args.admin_token, args.limit, args.cursor, args.sheet_id
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_offline_get(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.get_offline_package(
            GetOfflineSyncPackageCommand(
                args.tenant, args.admin_token, args.package_id, bool(args.include_payload)
            )
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    def _handle_dcim_field_offline_sync(self, args: argparse.Namespace) -> int:
        result = self._create_application(args).field_operation_service.synchronize_offline_package(
            SynchronizeOfflinePackageCommand(
                args.tenant, args.actor, args.admin_token, args.package_id, args.payload_sha256
            )
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0

    def _handle_dcim_sites(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.list_sites(
            ListDcimSitesCommand(args.tenant, include_retired=args.include_retired)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_site(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.get_site(
            GetDcimSiteCommand(args.tenant, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_site_create(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.create_site(
            CreateDcimSiteCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                code=args.code,
                name=args.name,
                country=args.country,
                city=args.city,
                region=args.region,
                street_address=args.street_address,
                postal_code=args.postal_code,
                contact_email=args.contact_email,
                phone=args.phone,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_site_update(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.update_site(
            UpdateDcimSiteCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                code=args.code,
                name=args.name,
                country=args.country,
                city=args.city,
                region=args.region,
                street_address=args.street_address,
                postal_code=args.postal_code,
                contact_email=args.contact_email,
                phone=args.phone,
                status=args.status,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_site_delete(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.delete_site(
            DeleteDcimSiteCommand(args.tenant, args.actor, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_topology_catalog(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.topology_catalog(
            DcimTopologyCatalogCommand(args.tenant, include_retired=args.include_retired)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_buildings(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.list_buildings(
            ListDcimBuildingsCommand(args.tenant, args.site, args.include_retired)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_building(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.get_building(
            GetDcimBuildingCommand(args.tenant, args.site, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_building_create(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.create_building(
            CreateDcimBuildingCommand(
                args.tenant,
                args.actor,
                args.site,
                args.code,
                args.name,
                args.building_type,
                args.initial_level,
                args.final_level,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_building_update(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.update_building(
            UpdateDcimBuildingCommand(
                args.tenant, args.actor, args.site, args.code, args.name, args.status
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_building_delete(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.delete_building(
            DeleteDcimBuildingCommand(args.tenant, args.actor, args.site, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_floors(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.list_floors(
            ListDcimFloorsCommand(args.tenant, args.site, args.building, args.include_retired)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_floor(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.get_floor(
            GetDcimFloorCommand(args.tenant, args.site, args.building, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_floor_create(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.create_floor(
            CreateDcimFloorCommand(
                args.tenant,
                args.actor,
                args.site,
                args.building,
                args.code,
                args.name,
                args.level_index,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_floor_update(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.update_floor(
            UpdateDcimFloorCommand(
                args.tenant,
                args.actor,
                args.site,
                args.building,
                args.code,
                args.name,
                args.level_index,
                args.status,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_floor_delete(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.delete_floor(
            DeleteDcimFloorCommand(args.tenant, args.actor, args.site, args.building, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_rooms(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.list_rooms(
            ListDcimRoomsCommand(args.tenant, args.site, args.building, args.include_retired)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_room(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.get_room(
            GetDcimRoomCommand(args.tenant, args.site, args.building, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_room_create(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.create_room(
            CreateDcimRoomCommand(
                args.tenant,
                args.actor,
                args.site,
                args.building,
                args.floor,
                args.code,
                args.name,
                tuple(args.row),
                tuple(args.column),
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_room_update(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.update_room(
            UpdateDcimRoomCommand(
                args.tenant,
                args.actor,
                args.site,
                args.building,
                args.code,
                args.name,
                tuple(args.row) if args.row else None,
                tuple(args.column) if args.column else None,
                args.status,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_room_delete(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.delete_room(
            DeleteDcimRoomCommand(args.tenant, args.actor, args.site, args.building, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_zones(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.list_zones(
            ListDcimZonesCommand(
                args.tenant, args.site, args.building, args.room, args.include_retired
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_zone(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.get_zone(
            GetDcimZoneCommand(args.tenant, args.site, args.building, args.room, args.code)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_zone_create(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.create_zone(
            CreateDcimZoneCommand(
                args.tenant,
                args.actor,
                args.site,
                args.building,
                args.room,
                args.code,
                args.name,
                tuple(args.row),
                tuple(args.column),
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_zone_update(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.update_zone(
            UpdateDcimZoneCommand(
                args.tenant,
                args.actor,
                args.site,
                args.building,
                args.room,
                args.code,
                args.name,
                tuple(args.row) if args.row else None,
                tuple(args.column) if args.column else None,
                args.status,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_zone_delete(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.delete_zone(
            DeleteDcimZoneCommand(
                args.tenant, args.actor, args.site, args.building, args.room, args.code
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_define_room(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site_code=args.site_code,
                site_name=args.site_name,
                country=args.country,
                region=args.region,
                city=args.city,
                building_code=args.building_code,
                building_name=args.building_name,
                floor_code=args.floor_code,
                floor_name=args.floor_name,
                floor_index=args.floor_index,
                room_code=args.room_code,
                room_name=args.room_name,
                rows=tuple(args.row),
                columns=tuple(args.column),
                zone_code=args.zone_code,
                zone_name=args.zone_name,
                zone_rows=tuple(args.zone_row),
                zone_columns=tuple(args.zone_column),
                x=args.x,
                y=args.y,
                z=args.z,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_define_rack(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        faces = tuple(args.face) if args.face else ("front",)
        result = application.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                floor=args.floor,
                room=args.room,
                zone=args.zone,
                rack=args.rack,
                row=args.row,
                column=args.column,
                units=args.units,
                usable_faces=faces,
                max_weight_kg=args.max_weight_kg,
                power_capacity_watts=args.power_capacity_watts,
                x=args.x,
                y=args.y,
                z=args.z,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_racks(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_rack_service.list_racks(
            ListRacksCommand(args.tenant, args.site, args.building, args.room, args.include_retired)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_rack(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_rack_service.get_rack(
            GetRackCommand(args.tenant, args.site, args.building, args.room, args.rack)
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_rack_update(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_rack_service.update_rack(
            UpdateRackCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
                row=args.row,
                column=args.column,
                units=args.units,
                usable_faces=tuple(args.face) if args.face else None,
                max_weight_kg=args.max_weight_kg,
                power_capacity_watts=args.power_capacity_watts,
                status=args.status,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_rack_delete(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_rack_service.delete_rack(
            DeleteRackCommand(
                args.tenant, args.actor, args.site, args.building, args.room, args.rack
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_rack_capacity(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.dcim_rack_service.capacity(
            RackCapacityCommand(
                tenant_id=args.tenant,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
            )
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_locate(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        equipment = application.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                asset_tag=args.asset_tag,
                equipment_name=args.equipment_name,
                site=args.site,
                building=args.building,
                room=args.room,
                floor=args.floor,
                zone=args.zone,
                row=args.row,
                column=args.column,
                rack=args.rack,
                u_position=args.u_position,
                rack_face=args.rack_face,
                u_height=args.u_height,
                x=args.x,
                y=args.y,
                z=args.z,
            )
        )
        print(equipment.location.human_readable())
        return 0

    def _handle_dcim_define_patch_panel(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_cabling_service.define_patch_panel(
            DefinePatchPanelCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
                patch_panel=args.patch_panel,
                rack_face=args.rack_face,
                u_position=args.u_position,
                u_height=args.u_height,
                port_count=args.port_count,
                connector=args.connector,
                medium=args.medium,
                label=args.label,
                port_prefix=args.port_prefix,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_define_port(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_cabling_service.define_port(
            DefineDcimPortCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                owner_type=args.owner_type,
                owner_code=args.owner_code,
                port_name=args.port_name,
                connector=args.connector,
                medium=args.medium,
                site=args.site,
                building=args.building,
                room=args.room,
                enabled=not args.disabled,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_connect_cable(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_cabling_service.connect_cable(
            ConnectDcimCableCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                cable_id=args.cable_id,
                a_owner_type=args.a_owner_type,
                a_owner_code=args.a_owner_code,
                a_port_name=args.a_port_name,
                b_owner_type=args.b_owner_type,
                b_owner_code=args.b_owner_code,
                b_port_name=args.b_port_name,
                medium=args.medium,
                status=args.status,
                path_segments=tuple(args.path),
                length_m=args.length_m,
                label=args.label,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_cable_trace(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_cabling_service.trace_cable(
            TraceDcimCableCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                cable_id=args.cable_id,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_locator_sheet(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        sheet = application.dcim_field_operation_service.locator_sheet(
            GenerateEquipmentLocatorCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                asset_tag=args.asset_tag,
                output_format=args.format,
            )
        )
        if args.format == "html":
            print(sheet.html_document())
        else:
            print(json.dumps(sheet.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_verify_scan(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        proof = application.dcim_field_operation_service.verify_scan(
            VerifyEquipmentScanCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                asset_tag=args.asset_tag,
                payload=args.payload,
            )
        )
        print(json.dumps(proof.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_room_plan(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        plan = application.dcim_visualization_service.room_plan(
            RenderRoomPlanCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
                output_format=args.format,
            )
        )
        if args.format == "svg":
            print(plan.svg_document())
        elif args.format == "html":
            print(plan.html_document())
        else:
            print(json.dumps(plan.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_rack_elevation(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        elevation = application.dcim_visualization_service.rack_elevation(
            RenderRackElevationCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
                face=args.face,
                output_format=args.format,
            )
        )
        if args.format == "svg":
            print(elevation.svg_document())
        elif args.format == "html":
            print(elevation.html_document())
        else:
            print(json.dumps(elevation.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_define_power_device(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                code=args.code,
                kind=args.kind,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
                side=args.side,
                capacity_watts=args.capacity_watts,
                derating_percent=args.derating_percent,
                input_source=args.input_source,
                output_voltage=args.output_voltage,
                label=args.label,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_define_power_circuit(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                circuit_id=args.circuit_id,
                source_device=args.source_device,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
                side=args.side,
                capacity_watts=args.capacity_watts,
                breaker_rating_amps=args.breaker_rating_amps,
                redundancy_group=args.redundancy_group,
                label=args.label,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_define_cooling_zone(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_environment_service.define_cooling_zone(
            DefineCoolingZoneCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
                zone=args.zone,
                role=args.role,
                cooling_capacity_watts=args.cooling_capacity_watts,
                supply_temperature_c=args.supply_temperature_c,
                return_temperature_c=args.return_temperature_c,
                label=args.label,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_reserve_power(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_environment_service.reserve_equipment_power(
            ReserveEquipmentPowerCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                asset_tag=args.asset_tag,
                circuit_id=args.circuit_id,
                expected_watts=args.expected_watts,
                label=args.label,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _handle_dcim_energy_cooling_capacity(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        report = application.dcim_environment_service.rack_energy_cooling_capacity(
            RackEnergyCoolingCapacityCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
                rack=args.rack,
            )
        )
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0

    def _handle_dcim_digital_twin(self, args: argparse.Namespace) -> int:
        application = self._create_application(args)
        result = application.dcim_visualization_service.digital_twin(
            RenderDigitalTwinCommand(
                tenant_id=args.tenant,
                actor=args.actor,
                site=args.site,
                building=args.building,
                room=args.room,
            )
        )
        print(json.dumps(result, sort_keys=True))
        return 0

    def _create_migration_executor(self, args: argparse.Namespace) -> PostgreSQLMigrationExecutor:
        dsn = RuntimeDatabaseDsnResolver().resolve(args.postgres_dsn)
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn, OPENINFRA_DATABASE_DSN or /opt/openinfra/config/"
                "openinfra.conf is required for PostgreSQL migrations"
            )
        registry = PostgreSQLSessionRegistry(PostgreSQLConnectionFactory(dsn))
        return PostgreSQLMigrationExecutor(
            registry,
            PostgreSQLMigrationCatalog(self._resolve_migration_root(args)),
        )

    def _resolve_migration_root(self, args: argparse.Namespace) -> Path:
        explicit_root = getattr(args, "root", None)
        if explicit_root is not None:
            return Path(explicit_root)
        runtime_root = RuntimeConfigLoader().load().get("OPENINFRA_MIGRATIONS_ROOT")
        if runtime_root:
            return Path(runtime_root)
        source_root = Path("installers/migrations/postgresql")
        if source_root.is_dir():
            return source_root
        packaged_root = self._packaged_migration_root()
        return packaged_root if packaged_root.is_dir() else source_root

    def _packaged_migration_root(self) -> Path:
        return Path(__file__).resolve().parents[1] / "migrations" / "postgresql"

    def _create_application(self, args: argparse.Namespace) -> OpenInfraApplication:
        backend = str(args.backend)
        edition = getattr(args, "edition", os.environ.get("OPENINFRA_EDITION", "enterprise"))
        if backend == "json":
            return ApplicationFactory().create_json_application(args.data, edition=edition)
        dsn = RuntimeDatabaseDsnResolver().resolve(args.postgres_dsn)
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn, OPENINFRA_DATABASE_DSN or /opt/openinfra/config/"
                "openinfra.conf is required for postgresql backend"
            )
        return ApplicationFactory().create_postgresql_application(dsn, seed=False, edition=edition)

    def fail_fast(self, message: str) -> NoReturn:
        raise OpenInfraError(message)


if __name__ == "__main__":
    raise SystemExit(OpenInfraCLI.main())
