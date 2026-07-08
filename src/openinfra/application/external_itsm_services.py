from __future__ import annotations

from dataclasses import dataclass

from openinfra.domain.external_itsm import (
    ExternalItsmCiSyncPlan,
    ExternalItsmConnectorPolicy,
    ExternalItsmConnectorProfile,
)


@dataclass(frozen=True, slots=True)
class ValidateServiceNowConnectorCommand:
    tenant_id: str
    instance_url: str
    table_name: str
    auth_secret_ref: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BuildServiceNowCiSyncPlanCommand:
    tenant_id: str
    resource_key: str
    direction: str = "push_ci"
    target_table: str = "cmdb_ci"
    mapping: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ValidateJiraServiceManagementConnectorCommand:
    tenant_id: str
    instance_url: str
    object_type: str
    auth_secret_ref: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BuildJiraServiceManagementAssetSyncPlanCommand:
    tenant_id: str
    resource_key: str
    direction: str = "push_ci"
    object_type: str = "object"
    mapping: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ValidateGlpiConnectorCommand:
    tenant_id: str
    instance_url: str
    item_type: str
    auth_secret_ref: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BuildGlpiAssetSyncPlanCommand:
    tenant_id: str
    resource_key: str
    direction: str = "push_ci"
    item_type: str = "computer"
    mapping: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ValidateFreshserviceConnectorCommand:
    tenant_id: str
    instance_url: str
    asset_type: str
    auth_secret_ref: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BuildFreshserviceAssetSyncPlanCommand:
    tenant_id: str
    resource_key: str
    direction: str = "push_ci"
    asset_type: str = "asset"
    mapping: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ValidateOpenServiceConnectorCommand:
    tenant_id: str
    instance_url: str
    collection: str
    auth_secret_ref: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class BuildOpenServiceCmdbSyncPlanCommand:
    tenant_id: str
    resource_key: str
    direction: str = "push_ci"
    collection: str = "configuration_item"
    mapping: dict[str, str] | None = None


class ExternalItsmIntegrationService:
    def list_policies(self) -> tuple[ExternalItsmConnectorPolicy, ...]:
        return (
            ExternalItsmConnectorPolicy.servicenow(),
            ExternalItsmConnectorPolicy.jira_service_management(),
            ExternalItsmConnectorPolicy.glpi(),
            ExternalItsmConnectorPolicy.freshservice(),
            ExternalItsmConnectorPolicy.openservice(),
        )

    def validate_servicenow_connector(
        self, command: ValidateServiceNowConnectorCommand
    ) -> ExternalItsmConnectorProfile:
        return ExternalItsmConnectorProfile.create(
            tenant_id=command.tenant_id,
            provider="servicenow",
            instance_url=command.instance_url,
            table_name=command.table_name,
            auth_secret_ref=command.auth_secret_ref,
            enabled=command.enabled,
        )

    def build_servicenow_ci_sync_plan(
        self, command: BuildServiceNowCiSyncPlanCommand
    ) -> ExternalItsmCiSyncPlan:
        mapping = command.mapping or {
            "resource_key": "correlation_id",
            "display_name": "name",
            "resource_type": "sys_class_name",
            "lifecycle": "install_status",
            "source": "discovery_source",
        }
        return ExternalItsmCiSyncPlan.create(
            tenant_id=command.tenant_id,
            provider="servicenow",
            direction=command.direction,
            resource_key=command.resource_key,
            target_table=command.target_table,
            mapping=mapping,
        )

    def validate_jira_service_management_connector(
        self, command: ValidateJiraServiceManagementConnectorCommand
    ) -> ExternalItsmConnectorProfile:
        return ExternalItsmConnectorProfile.create(
            tenant_id=command.tenant_id,
            provider="jira_service_management",
            instance_url=command.instance_url,
            table_name=command.object_type,
            auth_secret_ref=command.auth_secret_ref,
            enabled=command.enabled,
        )

    def build_jira_service_management_asset_sync_plan(
        self, command: BuildJiraServiceManagementAssetSyncPlanCommand
    ) -> ExternalItsmCiSyncPlan:
        mapping = command.mapping or {
            "resource_key": "external_id",
            "display_name": "name",
            "resource_type": "object_type",
            "workspace_id": "workspace_id",
            "source": "openinfra_source",
        }
        return ExternalItsmCiSyncPlan.create(
            tenant_id=command.tenant_id,
            provider="jira_service_management",
            direction=command.direction,
            resource_key=command.resource_key,
            target_table=command.object_type,
            mapping=mapping,
        )

    def validate_glpi_connector(
        self, command: ValidateGlpiConnectorCommand
    ) -> ExternalItsmConnectorProfile:
        return ExternalItsmConnectorProfile.create(
            tenant_id=command.tenant_id,
            provider="glpi",
            instance_url=command.instance_url,
            table_name=command.item_type,
            auth_secret_ref=command.auth_secret_ref,
            enabled=command.enabled,
        )

    def build_glpi_asset_sync_plan(
        self, command: BuildGlpiAssetSyncPlanCommand
    ) -> ExternalItsmCiSyncPlan:
        mapping = command.mapping or {
            "resource_key": "serial",
            "display_name": "name",
            "resource_type": "itemtype",
            "entity": "entities_id",
            "source": "openinfra_source",
        }
        return ExternalItsmCiSyncPlan.create(
            tenant_id=command.tenant_id,
            provider="glpi",
            direction=command.direction,
            resource_key=command.resource_key,
            target_table=command.item_type,
            mapping=mapping,
        )

    def validate_freshservice_connector(
        self, command: ValidateFreshserviceConnectorCommand
    ) -> ExternalItsmConnectorProfile:
        return ExternalItsmConnectorProfile.create(
            tenant_id=command.tenant_id,
            provider="freshservice",
            instance_url=command.instance_url,
            table_name=command.asset_type,
            auth_secret_ref=command.auth_secret_ref,
            enabled=command.enabled,
        )

    def build_freshservice_asset_sync_plan(
        self, command: BuildFreshserviceAssetSyncPlanCommand
    ) -> ExternalItsmCiSyncPlan:
        mapping = command.mapping or {
            "resource_key": "asset_tag",
            "display_name": "name",
            "resource_type": "asset_type_name",
            "asset_tag": "asset_tag",
            "source": "openinfra_source",
        }
        return ExternalItsmCiSyncPlan.create(
            tenant_id=command.tenant_id,
            provider="freshservice",
            direction=command.direction,
            resource_key=command.resource_key,
            target_table=command.asset_type,
            mapping=mapping,
        )


    def validate_openservice_connector(
        self, command: ValidateOpenServiceConnectorCommand
    ) -> ExternalItsmConnectorProfile:
        return ExternalItsmConnectorProfile.create(
            tenant_id=command.tenant_id,
            provider="openservice",
            instance_url=command.instance_url,
            table_name=command.collection,
            auth_secret_ref=command.auth_secret_ref,
            enabled=command.enabled,
        )

    def build_openservice_cmdb_sync_plan(
        self, command: BuildOpenServiceCmdbSyncPlanCommand
    ) -> ExternalItsmCiSyncPlan:
        mapping = command.mapping or {
            "resource_key": "openinfra_resource_key",
            "display_name": "name",
            "resource_type": "cmdb_class",
            "cmdb_class": "cmdb_class",
            "source": "openinfra_source",
        }
        return ExternalItsmCiSyncPlan.create(
            tenant_id=command.tenant_id,
            provider="openservice",
            direction=command.direction,
            resource_key=command.resource_key,
            target_table=command.collection,
            mapping=mapping,
        )
