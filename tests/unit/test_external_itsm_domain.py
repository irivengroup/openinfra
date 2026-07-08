from __future__ import annotations

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.external_itsm import (
    ExternalItsmCiSyncPlan,
    ExternalItsmConnectorPolicy,
    ExternalItsmConnectorProfile,
    ExternalItsmProvider,
    ExternalItsmSyncDirection,
)


def test_servicenow_policy_excludes_native_ticketing() -> None:
    policy = ExternalItsmConnectorPolicy.servicenow().as_dict()

    assert policy["provider"] == "servicenow"
    assert policy["native_ticketing_enabled"] is False
    assert policy["editions"] == ["pro", "enterprise"]
    assert "push_ci" in policy["supported_directions"]


def test_jira_service_management_policy_excludes_native_ticketing() -> None:
    policy = ExternalItsmConnectorPolicy.jira_service_management().as_dict()

    assert policy["provider"] == "jira_service_management"
    assert policy["native_ticketing_enabled"] is False
    assert policy["editions"] == ["pro", "enterprise"]
    assert "OPENINFRA_JIRA_TOKEN_REF" in policy["required_secret_refs"]
    assert "workspace_id" in policy["required_ci_fields"]


def test_openservice_policy_prepares_external_autonomous_cmdb_without_openinfra_web_ui() -> None:
    policy = ExternalItsmConnectorPolicy.openservice().as_dict()

    assert policy["provider"] == "openservice"
    assert policy["editions"] == ["pro", "enterprise"]
    assert policy["native_ticketing_enabled"] is False
    assert policy["openinfra_web_ui_enabled"] is False
    assert policy["integration_ui_owner"] == "openservice-web"
    assert "OPENINFRA_OPENSERVICE_SECRET_REF" in policy["required_secret_refs"]
    assert "cmdb_class" in policy["required_ci_fields"]


def test_servicenow_provider_and_direction_reject_unknown_values() -> None:
    assert (
        ExternalItsmProvider.from_value(ExternalItsmProvider.SERVICENOW)
        is ExternalItsmProvider.SERVICENOW
    )
    assert ExternalItsmProvider.from_value("snow") is ExternalItsmProvider.SERVICENOW
    assert (
        ExternalItsmProvider.from_value("jira")
        is ExternalItsmProvider.JIRA_SERVICE_MANAGEMENT
    )
    assert (
        ExternalItsmProvider.from_value("jsm")
        is ExternalItsmProvider.JIRA_SERVICE_MANAGEMENT
    )
    assert (
        ExternalItsmProvider.from_value("open-service")
        is ExternalItsmProvider.OPENSERVICE
    )
    assert (
        ExternalItsmProvider.from_value("openservice-cmdb")
        is ExternalItsmProvider.OPENSERVICE
    )
    assert (
        ExternalItsmSyncDirection.from_value(ExternalItsmSyncDirection.PUSH_CI)
        is ExternalItsmSyncDirection.PUSH_CI
    )
    assert (
        ExternalItsmSyncDirection.from_value("link-external-ticket")
        is ExternalItsmSyncDirection.LINK_EXTERNAL_TICKET
    )

    with pytest.raises(ValidationError):
        ExternalItsmProvider.from_value("unknown")
    with pytest.raises(ValidationError):
        ExternalItsmSyncDirection.from_value("open-ticket")


def test_servicenow_profile_rejects_secret_material_and_insecure_url() -> None:
    secret_ref = "vault://ok"
    leaked_token_ref = "token=clear"

    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default", "servicenow", "http://snow.example", "cmdb_ci", secret_ref
        )
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default", "servicenow", "https://snow.example", "cmdb_ci", leaked_token_ref
        )


def test_servicenow_profile_rejects_embedded_credentials_invalid_table_and_empty_secret() -> None:
    secret_ref = "vault://openinfra/servicenow/oauth"

    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default",
            "servicenow",
            "https://operator:credential@snow.example",
            "cmdb_ci",
            secret_ref,
        )
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default", "servicenow", "https://snow.example", "incident", secret_ref
        )
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default", "servicenow", "https://snow.example", "cmdb_ci", "   "
        )


def test_servicenow_profile_normalizes_safe_values() -> None:
    profile = ExternalItsmConnectorProfile.create(
        TenantId.from_value("default"),
        ExternalItsmProvider.from_value("service-now"),
        "https://snow.example/",
        "CMDB_CI_SERVER",
        "vault://openinfra/servicenow/oauth",
    )

    assert profile.as_dict() == {
        "tenant_id": "default",
        "provider": "servicenow",
        "instance_url": "https://snow.example",
        "table_name": "cmdb_ci_server",
        "auth_secret_ref": "vault://openinfra/servicenow/oauth",
        "enabled": True,
        "native_ticketing_enabled": False,
    }



def test_jira_service_management_profile_and_asset_plan_normalize_safe_values() -> None:
    profile = ExternalItsmConnectorProfile.create(
        "default",
        "jira",
        "https://tenant.atlassian.net/",
        "SERVER",
        "vault://openinfra/jira/api-token",
    )
    plan = ExternalItsmCiSyncPlan.create(
        "default",
        "jira_service_management",
        "push_ci",
        "SRV-PAR1-001",
        "server",
        {
            "resource_key": "external_id",
            "display_name": "name",
            "resource_type": "object_type",
            "workspace_id": "workspace_id",
        },
    )

    assert profile.as_dict()["provider"] == "jira_service_management"
    assert profile.as_dict()["table_name"] == "server"
    assert plan.as_dict()["target_table"] == "server"
    assert plan.as_dict()["mapping"]["workspace_id"] == "workspace_id"
    assert plan.as_dict()["native_ticketing_enabled"] is False


def test_jira_service_management_rejects_unknown_object_type() -> None:
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default",
            "jira",
            "https://tenant.atlassian.net",
            "incident",
            "vault://openinfra/jira/api-token",
        )


def test_servicenow_ci_sync_plan_validates_required_mapping() -> None:
    plan = ExternalItsmCiSyncPlan.create(
        "default",
        "servicenow",
        "push_ci",
        "SRV-PAR1-001",
        "cmdb_ci",
        {
            "resource_key": "correlation_id",
            "display_name": "name",
            "resource_type": "sys_class_name",
        },
    )

    assert plan.safe_to_apply is True
    assert plan.as_dict()["native_ticketing_enabled"] is False
    assert plan.as_dict()["actions"] == [
        "resolve_rsot_resource",
        "map_ci_payload",
        "upsert_external_ci",
        "audit_external_reference",
    ]

    with pytest.raises(ValidationError):
        ExternalItsmCiSyncPlan.create(
            "default", "servicenow", "push_ci", "SRV-PAR1-001", "cmdb_ci", {"resource_key": "id"}
        )


def test_servicenow_ci_sync_plan_rejects_unsafe_inputs() -> None:
    mapping = {
        "resource_key": "correlation_id",
        "display_name": "name",
        "resource_type": "sys_class_name",
    }

    with pytest.raises(ValidationError):
        ExternalItsmCiSyncPlan.create("default", "servicenow", "push_ci", "x", "cmdb_ci", mapping)
    with pytest.raises(ValidationError):
        ExternalItsmCiSyncPlan.create("default", "servicenow", "push_ci", "SRV-001", "cmdb_ci", {})
    with pytest.raises(ValidationError):
        ExternalItsmCiSyncPlan.create(
            "default",
            "servicenow",
            "push_ci",
            "SRV-001",
            "cmdb_ci",
            {"resource_key": " ", "display_name": "name", "resource_type": "sys_class_name"},
        )
    with pytest.raises(ValidationError):
        ExternalItsmCiSyncPlan.create(
            "default",
            "servicenow",
            "push_ci",
            "SRV-001",
            "cmdb_ci",
            {
                "resource-key": "correlation_id",
                "display_name": "name",
                "resource_type": "sys_class_name",
            },
        )


def test_servicenow_ci_sync_plan_supports_ticket_enrichment_and_link_actions() -> None:
    mapping = {
        "resource_key": "correlation_id",
        "display_name": "name",
        "resource_type": "sys_class_name",
    }

    enrich = ExternalItsmCiSyncPlan.create(
        "default",
        "servicenow",
        ExternalItsmSyncDirection.ENRICH_EXTERNAL_TICKET,
        "SRV-PAR1-001",
        "cmdb_ci",
        mapping,
    )
    link = ExternalItsmCiSyncPlan.create(
        "default", "servicenow", "link_external_ticket", "SRV-PAR1-001", "cmdb_ci", mapping
    )

    assert enrich.as_dict()["actions"] == [
        "resolve_external_ticket_reference",
        "render_openinfra_context",
        "patch_external_ticket_notes",
    ]
    assert link.as_dict()["actions"] == [
        "resolve_external_ticket_reference",
        "create_openinfra_external_link",
        "audit_external_link",
    ]


def test_glpi_and_freshservice_policies_exclude_native_ticketing() -> None:
    glpi = ExternalItsmConnectorPolicy.glpi().as_dict()
    freshservice = ExternalItsmConnectorPolicy.freshservice().as_dict()

    assert glpi["provider"] == "glpi"
    assert glpi["native_ticketing_enabled"] is False
    assert "OPENINFRA_GLPI_APP_TOKEN_REF" in glpi["required_secret_refs"]
    assert "entity" in glpi["required_ci_fields"]
    assert freshservice["provider"] == "freshservice"
    assert freshservice["native_ticketing_enabled"] is False
    assert "OPENINFRA_FRESHSERVICE_API_TOKEN_REF" in freshservice["required_secret_refs"]
    assert "asset_tag" in freshservice["required_ci_fields"]


def test_glpi_and_freshservice_aliases_profiles_and_asset_plans_are_safe() -> None:
    assert ExternalItsmProvider.from_value("glpi-assets") is ExternalItsmProvider.GLPI
    assert ExternalItsmProvider.from_value("fresh-service") is ExternalItsmProvider.FRESHSERVICE

    glpi_profile = ExternalItsmConnectorProfile.create(
        "default",
        "glpi-inventory",
        "https://glpi.example.com/",
        "NETWORK_EQUIPMENT",
        "vault://openinfra/glpi/tokens",
    )
    glpi_plan = ExternalItsmCiSyncPlan.create(
        "default",
        "glpi",
        "push_ci",
        "NET-PAR1-001",
        "network_equipment",
        {
            "resource_key": "serial",
            "display_name": "name",
            "resource_type": "itemtype",
            "entity": "entities_id",
        },
    )
    freshservice_profile = ExternalItsmConnectorProfile.create(
        "default",
        "freshservice-assets",
        "https://tenant.freshservice.com/",
        "SERVER",
        "vault://openinfra/freshservice/api-token",
    )
    freshservice_plan = ExternalItsmCiSyncPlan.create(
        "default",
        "freshworks",
        "push_ci",
        "SRV-PAR1-001",
        "server",
        {
            "resource_key": "asset_tag",
            "display_name": "name",
            "resource_type": "asset_type_name",
            "asset_tag": "asset_tag",
        },
    )

    assert glpi_profile.as_dict()["provider"] == "glpi"
    assert glpi_profile.as_dict()["table_name"] == "network_equipment"
    assert glpi_plan.as_dict()["target_table"] == "network_equipment"
    assert glpi_plan.as_dict()["mapping"]["entity"] == "entities_id"
    assert freshservice_profile.as_dict()["provider"] == "freshservice"
    assert freshservice_profile.as_dict()["table_name"] == "server"
    assert freshservice_plan.as_dict()["target_table"] == "server"
    assert freshservice_plan.as_dict()["mapping"]["asset_tag"] == "asset_tag"


def test_glpi_and_freshservice_reject_invalid_asset_types() -> None:
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default",
            "glpi",
            "https://glpi.example.com",
            "ticket",
            "vault://openinfra/glpi/tokens",
        )
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default",
            "freshservice",
            "https://tenant.freshservice.com",
            "change",
            "vault://openinfra/freshservice/api-token",
        )


def test_openservice_profile_and_cmdb_plan_are_safe_and_future_cdc_neutral() -> None:
    profile = ExternalItsmConnectorProfile.create(
        "default",
        "openservice-itsm",
        "https://openservice.example.com/",
        "CONFIGURATION_ITEM",
        "vault://openinfra/openservice/oauth",
    )
    plan = ExternalItsmCiSyncPlan.create(
        "default",
        "openservice",
        "push_ci",
        "SRV-PAR1-001",
        "configuration_item",
        {
            "resource_key": "openinfra_resource_key",
            "display_name": "name",
            "resource_type": "cmdb_class",
            "cmdb_class": "cmdb_class",
        },
    )

    assert profile.as_dict()["provider"] == "openservice"
    assert profile.as_dict()["table_name"] == "configuration_item"
    assert profile.as_dict()["native_ticketing_enabled"] is False
    assert plan.as_dict()["target_table"] == "configuration_item"
    assert plan.as_dict()["mapping"]["cmdb_class"] == "cmdb_class"
    assert plan.as_dict()["native_ticketing_enabled"] is False


def test_openservice_rejects_unbounded_future_collections() -> None:
    with pytest.raises(ValidationError):
        ExternalItsmConnectorProfile.create(
            "default",
            "openservice",
            "https://openservice.example.com",
            "incident",
            "vault://openinfra/openservice/oauth",
        )
