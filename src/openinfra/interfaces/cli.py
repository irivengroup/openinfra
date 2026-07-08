from __future__ import annotations

import argparse
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
from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.dcim_services import (
    ConnectDcimCableCommand,
    DefineCoolingZoneCommand,
    DefineDcimPortCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    GenerateEquipmentLocatorCommand,
    LocateEquipmentCommand,
    RackCapacityCommand,
    RackEnergyCoolingCapacityCommand,
    RenderDigitalTwinCommand,
    RenderRackElevationCommand,
    RenderRoomPlanCommand,
    ReserveEquipmentPowerCommand,
    TraceDcimCableCommand,
    VerifyEquipmentScanCommand,
)
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
    BuildLocalDiscoveryPlanCommand,
    DisableCollectorCommand,
    EnrollDiscoveryProxyCommand,
    HeartbeatCollectorCommand,
    ListCollectorsCommand,
    RegisterCollectorCommand,
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
    CreateItamTenantCommand,
    DeleteItamTenantCommand,
    GetAssetSupportCoverageReportCommand,
    GetAssetSupportProfileCommand,
    GetItamTenantCommand,
    GetSoftwareLicenseCommand,
    GetSoftwareLicenseComplianceCommand,
    ListItamTenantsCommand,
    RegisterManufacturerSupportCommand,
    RegisterSoftwareLicenseCommand,
    UpdateItamTenantCommand,
    UpdateSoftwareLicenseAssignmentCommand,
)
from openinfra.application.search_services import GlobalSearchCommand
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
)
from openinfra.application.source_governance_services import (
    CreateSourceGovernanceRuleCommand,
    DeactivateSourceGovernanceRuleCommand,
    EvaluateSourceGovernanceCommand,
    ListSourceGovernanceRulesCommand,
)
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.authentication import ExternalDirectoryConfig
from openinfra.domain.common import OpenInfraError
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

        tenant_list = itam_subparsers.add_parser("tenants", help="list ITAM tenants")
        self._add_backend_arguments(tenant_list)
        tenant_list.add_argument("--tenant", default="default", help="security tenant scope")
        tenant_list.add_argument("--admin-token", required=True)
        tenant_list.add_argument("--include-retired", action="store_true")
        tenant_list.set_defaults(handler=self._handle_itam_tenants)

        tenant_create = itam_subparsers.add_parser("tenant-create", help="create ITAM tenant")
        self._add_backend_arguments(tenant_create)
        tenant_create.add_argument("--tenant", required=True, help="ITAM tenant id to create")
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
        register_manufacturer.add_argument("--manufacturer", required=True)
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
        add_third_party.add_argument("--provider", required=True)
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
        software_license.add_argument("--vendor", required=True)
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

    def _add_dcim_commands(self, subparsers: Any) -> None:
        dcim = subparsers.add_parser("dcim", help="dcim operations")
        dcim_subparsers = dcim.add_subparsers(dest="dcim_command", required=True)
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
        define_room.add_argument("--floor-code", required=True)
        define_room.add_argument("--floor-name", required=True)
        define_room.add_argument("--floor-index", type=int, required=True)
        define_room.add_argument("--room-code", required=True)
        define_room.add_argument("--room-name", required=True)
        define_room.add_argument("--row", action="append", required=True)
        define_room.add_argument("--column", action="append", required=True)
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
        return Path(runtime_root) if runtime_root else Path("installers/migrations/postgresql")

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
