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


class ExternalItsmIntegrationService:
    def list_policies(self) -> tuple[ExternalItsmConnectorPolicy, ...]:
        return (ExternalItsmConnectorPolicy.servicenow(),)

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
