from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
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
from openinfra.application.identity_services import CreateUserCommand
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineIpPrefixCommand,
    DefineVlanCommand,
    DefineVlanGroupCommand,
    RegisterIpAddressCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.editions import (
    EditionPolicyCatalog,
    FeatureCapability,
    OpenInfraEdition,
    QuotaDecision,
    QuotaResource,
)
from openinfra.interfaces.cli import OpenInfraCLI

FINGERPRINT = "e" * 64


def _bootstrap(app) -> str:  # type: ignore[no-untyped-def]
    token = "s" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="edition-admin",
            roles=("security:admin",),
            token=token,
        )
    )
    return token


def test_edition_policy_catalog_exposes_expected_gates_and_quotas() -> None:
    catalog = EditionPolicyCatalog()
    service = EditionPolicyService(catalog)

    lite = service.policy_for(OpenInfraEdition.LITE)
    enterprise = service.policy_for("enterprise")
    denied = service.check_feature("lite", "distributed-discovery-agents")
    allowed = service.check_feature(
        OpenInfraEdition.ENTERPRISE, FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS
    )
    limited_decision = QuotaDecision(
        edition=OpenInfraEdition.LITE,
        resource=QuotaResource.USER,
        used=4,
        requested_increment=1,
        limit=5,
    )
    exceeded_decision = QuotaDecision(
        edition=OpenInfraEdition.LITE,
        resource=QuotaResource.USER,
        used=5,
        requested_increment=1,
        limit=5,
    )
    unlimited_decision = QuotaDecision(
        edition=OpenInfraEdition.ENTERPRISE,
        resource=QuotaResource.DISCOVERY_COLLECTOR,
        used=10_000,
        requested_increment=10,
        limit=None,
    )

    assert lite.quota_for(QuotaResource.USER) == 5
    assert lite.quota_for(QuotaResource.DISCOVERY_COLLECTOR) == 0
    assert enterprise.supports(FeatureCapability.INSTALLER_AGENT_SCOPE)
    assert denied.as_dict()["allowed"] is False
    assert allowed.as_dict()["allowed"] is True
    assert limited_decision.allowed is True
    assert limited_decision.as_dict()["remaining"] == 1
    assert exceeded_decision.allowed is False
    assert exceeded_decision.as_dict()["remaining"] == 0
    assert unlimited_decision.allowed is True
    assert unlimited_decision.as_dict()["limit"] == "unlimited"
    assert {policy.edition for policy in service.list_policies()} == set(OpenInfraEdition)
    assert enterprise.as_dict()["quotas"]["discovery_collector"] == "unlimited"

    with pytest.raises(ValidationError):
        OpenInfraEdition.from_value("community")
    with pytest.raises(ValidationError):
        FeatureCapability.from_value("unknown-feature")
    with pytest.raises(ValidationError):
        QuotaResource.from_value("unknown-resource")


def test_lite_backend_rejects_distributed_discovery_collectors_before_persistence(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="lite")
    token = _bootstrap(app)

    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        app.discovery_service.register_collector(
            RegisterCollectorCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="collector-lite",
                kind="snmp",
                certificate_fingerprint=FINGERPRINT,
                scopes=("site/par1",),
                version="0.29.0",
                endpoint_url="https://collector-lite.example.test/agent",
            )
        )

    assert (
        app.runtime_usage_repository.count_resource(
            TenantId.from_value("default"), QuotaResource.DISCOVERY_COLLECTOR
        )
        == 0
    )


def test_lite_backend_rejects_collector_runtime_operations(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="lite")
    token = _bootstrap(app)

    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        app.discovery_service.heartbeat(
            HeartbeatCollectorCommand(
                tenant_id="default",
                collector_id="collector-1",
                certificate_fingerprint=FINGERPRINT,
                version="0.29.0",
            )
        )
    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        app.discovery_service.authorize_job(
            AuthorizeDiscoveryJobCommand(
                tenant_id="default",
                collector_id="collector-1",
                certificate_fingerprint=FINGERPRINT,
                requested_scope="site/par1",
                job_type="snmp-scan",
                target="router-1",
            )
        )
    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        app.discovery_service.disable_collector(
            DisableCollectorCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                collector_id="collector-1",
                reason="edition gate regression test",
            )
        )
    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        app.discovery_service.list_collectors(
            ListCollectorsCommand(tenant_id="default", admin_token=token)
        )


def test_pro_backend_rejects_enterprise_proxy_enrollment(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="pro")
    token = _bootstrap(app)

    with pytest.raises(ValidationError, match="distributed_discovery_agents"):
        app.discovery_service.enroll_proxy(
            EnrollDiscoveryProxyCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="proxy-pro",
                kind="site-proxy",
                certificate_fingerprint="8" * 64,
                scopes=("site/par1",),
                version="0.29.33",
                endpoint_url="https://proxy-pro.example.test/agent",
            )
        )

    assert (
        app.runtime_usage_repository.count_resource(
            TenantId.from_value("default"), QuotaResource.DISCOVERY_COLLECTOR
        )
        == 0
    )


def test_lite_identity_runtime_quota_blocks_sixth_user(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="lite")
    token = _bootstrap(app)

    for index in range(5):
        app.identity_service.create_user(
            CreateUserCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                username=f"user-{index}",
                display_name=f"User {index}",
                email=f"user-{index}@example.test",
                roles=("viewer",),
            )
        )

    with pytest.raises(ValidationError, match="quota exceeded"):
        app.identity_service.create_user(
            CreateUserCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                username="user-5",
                display_name="User 5",
                email="user-5@example.test",
                roles=("viewer",),
            )
        )

    decision = app.edition_query_service.quota_decision(
        CheckQuotaCommand("default", "lite", "user", 1)
    )
    assert decision.used == 5
    assert decision.allowed is False


def test_lite_ipam_runtime_quota_is_checked_for_ip_and_subnet_vlan_resources(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="lite")

    reservation = app.ipam_service.allocate(
        AllocateIpCommand("default", "pytest", "default", "10.81.0.0/30", "srv-1", "key-1")
    )
    registered = app.ipam_model_service.register_address(
        RegisterIpAddressCommand(
            tenant_id="default",
            actor="pytest",
            vrf="default",
            prefix="10.81.0.0/30",
            address="10.81.0.2",
            hostname="srv-2",
        )
    )
    app.ipam_model_service.define_prefix(
        DefineIpPrefixCommand("default", "pytest", "default", "10.82.0.0/30")
    )
    app.ipam_model_service.define_vlan_group(DefineVlanGroupCommand("default", "pytest", "campus"))
    app.ipam_model_service.define_vlan(
        DefineVlanCommand("default", "pytest", "campus", 100, "users")
    )

    assert reservation.as_dict()["address"] == "10.81.0.1"
    assert registered["address"] == "10.81.0.2"
    assert (
        app.edition_query_service.quota_decision(
            CheckQuotaCommand("default", "lite", "ip_dns_record", 1)
        ).used
        == 2
    )
    assert (
        app.edition_query_service.quota_decision(
            CheckQuotaCommand("default", "lite", "subnet-vlan", 1)
        ).used
        == 3
    )


def test_edition_query_service_validates_negative_increment(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="pro")

    decision = app.edition_query_service.feature_decision(
        CheckFeatureCommand("default", "pro", "core_it_resources_management")
    )
    assert decision.allowed is True
    with pytest.raises(ValidationError, match="quota increment cannot be negative"):
        app.edition_query_service.quota_decision(CheckQuotaCommand("default", "pro", "user", -1))
    with pytest.raises(ValidationError, match="quota increment cannot be negative"):
        app.edition_guard.check_quota(CheckQuotaCommand("default", "pro", "user", -1))


def test_edition_cli_commands_report_policy_feature_and_quota(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data_path = tmp_path / "state.json"
    cli = OpenInfraCLI()

    assert cli.run(["edition", "list", "--data", str(data_path)]) == 0
    listed = capsys.readouterr().out
    assert "enterprise" in listed
    assert "discovery_collector" in listed

    assert (
        cli.run(
            [
                "edition",
                "feature-check",
                "--tenant",
                "default",
                "--edition",
                "lite",
                "--capability",
                "distributed_discovery_agents",
            ]
        )
        == 2
    )
    denied = capsys.readouterr().out
    assert '"allowed": false' in denied

    assert (
        cli.run(
            [
                "edition",
                "quota-check",
                "--data",
                str(data_path),
                "--edition",
                "lite",
                "--tenant",
                "default",
                "--resource",
                "user",
                "--increment",
                "1",
            ]
        )
        == 0
    )
    quota = capsys.readouterr().out
    assert '"limit": 5' in quota


def test_enterprise_runtime_guard_positive_paths_are_backward_compatible(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    tenant_id = TenantId.from_value("default")

    assert app.edition_guard.edition is OpenInfraEdition.ENTERPRISE
    feature = app.edition_guard.require_feature(
        tenant_id,
        FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
        "pytest",
        "edition_test",
        "enterprise",
    )
    quota = app.edition_guard.require_quota(
        tenant_id,
        QuotaResource.USER,
        1,
        "pytest",
        "edition_test",
        "enterprise",
    )
    explicit_quota = app.edition_guard.check_quota(
        CheckQuotaCommand("default", "enterprise", "user", 1)
    )

    assert feature.allowed is True
    assert quota.allowed is True
    assert explicit_quota.limit is None
    with pytest.raises(ValidationError, match="quota increment cannot be negative"):
        app.edition_guard.require_quota(
            tenant_id,
            QuotaResource.USER,
            -1,
            "pytest",
            "edition_test",
            "negative",
        )
