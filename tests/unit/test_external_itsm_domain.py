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


def test_servicenow_provider_and_direction_reject_unknown_values() -> None:
    assert (
        ExternalItsmProvider.from_value(ExternalItsmProvider.SERVICENOW)
        is ExternalItsmProvider.SERVICENOW
    )
    assert ExternalItsmProvider.from_value("snow") is ExternalItsmProvider.SERVICENOW
    assert (
        ExternalItsmSyncDirection.from_value(ExternalItsmSyncDirection.PUSH_CI)
        is ExternalItsmSyncDirection.PUSH_CI
    )
    assert (
        ExternalItsmSyncDirection.from_value("link-external-ticket")
        is ExternalItsmSyncDirection.LINK_EXTERNAL_TICKET
    )

    with pytest.raises(ValidationError):
        ExternalItsmProvider.from_value("jira")
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
