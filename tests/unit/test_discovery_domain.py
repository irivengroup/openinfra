from __future__ import annotations

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.discovery import (
    CollectorIdentity,
    CollectorKind,
    DiscoveryCollector,
    DiscoveryJobAuthorization,
    DiscoveryScope,
    LocalDiscoveryPlan,
    LocalDiscoveryProtocol,
    LocalDiscoveryTarget,
)

FINGERPRINT = "a" * 64
OTHER_FINGERPRINT = "b" * 64
LOCAL_VAULT_REF = "vault://" + "openinfra/discovery/local/par1"


def test_collector_identity_requires_sha256_fingerprint() -> None:
    with pytest.raises(ValidationError, match="SHA-256"):
        CollectorIdentity.create("not-a-fingerprint")


def test_collector_registration_normalizes_scope_and_vault_reference() -> None:
    collector = DiscoveryCollector.register(
        tenant_id=TenantId.from_value("default"),
        name="  SNMP Paris  ",
        kind=CollectorKind.from_value("snmp"),
        identity=CollectorIdentity.create(FINGERPRINT, "vault://openinfra/discovery/snmp/paris"),
        scopes=(DiscoveryScope.from_value(" Site/PAR1 "),),
        version="1.0.0",
        registered_by="admin",
    )

    assert collector.name == "SNMP Paris"
    assert collector.scopes[0].value == "site/par1"
    assert collector.identity.vault_secret_ref == "vault://openinfra/discovery/snmp/paris"


def test_job_authorization_rejects_scope_mismatch_and_disabled_collector() -> None:
    collector = DiscoveryCollector.register(
        tenant_id=TenantId.from_value("default"),
        name="SNMP Paris",
        kind=CollectorKind.SNMP,
        identity=CollectorIdentity.create(FINGERPRINT),
        scopes=(DiscoveryScope.from_value("site/par1"),),
        version="1.0.0",
        registered_by="admin",
    ).disable("retired")

    decision = DiscoveryJobAuthorization.decide(
        tenant_id=TenantId.from_value("default"),
        collector=collector,
        collector_id=collector.id.value,
        certificate_fingerprint=OTHER_FINGERPRINT,
        requested_scope="site/lyo1",
        job_type="snmp-scan",
        target="lyo1-core",
    )

    assert decision.authorized is False
    assert decision.reasons == (
        "collector_not_active",
        "fingerprint_mismatch",
        "scope_not_authorized",
    )


def test_job_authorization_rejects_unregistered_collector() -> None:
    decision = DiscoveryJobAuthorization.decide(
        tenant_id=TenantId.from_value("default"),
        collector=None,
        collector_id=EntityId.new().value,
        certificate_fingerprint=FINGERPRINT,
        requested_scope="site/par1",
        job_type="snmp-scan",
        target="par1-core",
    )

    assert decision.authorized is False
    assert decision.reasons == ("collector_not_registered",)


def test_collector_validation_edge_cases() -> None:
    tenant_id = TenantId.from_value("default")
    identity = CollectorIdentity.create(FINGERPRINT)
    scope = DiscoveryScope.from_value("site/par1")

    with pytest.raises(ValidationError, match="unsupported"):
        CollectorKind.from_value("telnet")
    with pytest.raises(ValidationError, match="scope"):
        DiscoveryScope.from_value("!")
    with pytest.raises(ValidationError, match="vault://"):
        CollectorIdentity.create(FINGERPRINT, "file://secret")
    with pytest.raises(ValidationError, match="unsafe"):
        CollectorIdentity.create(FINGERPRINT, "vault://openinfra/../secret")
    with pytest.raises(ValidationError, match="name"):
        DiscoveryCollector.register(
            tenant_id, "x", CollectorKind.SNMP, identity, (scope,), "1", "admin"
        )
    with pytest.raises(ValidationError, match="at least one scope"):
        DiscoveryCollector.register(
            tenant_id, "Collector", CollectorKind.SNMP, identity, (), "1", "admin"
        )
    with pytest.raises(ValidationError, match="registered_by"):
        DiscoveryCollector.register(
            tenant_id, "Collector", CollectorKind.SNMP, identity, (scope,), "1", " "
        )
    with pytest.raises(ValidationError, match="version"):
        DiscoveryCollector.register(
            tenant_id, "Collector", CollectorKind.SNMP, identity, (scope,), "!", "admin"
        )
    with pytest.raises(ValidationError, match="HTTPS"):
        DiscoveryCollector.register(
            tenant_id,
            "Collector",
            CollectorKind.SNMP,
            identity,
            (scope,),
            "1",
            "admin",
            endpoint_url="http://collector",
        )


def test_collector_heartbeat_and_job_validation_edges() -> None:
    collector = DiscoveryCollector.register(
        tenant_id=TenantId.from_value("default"),
        name="SNMP Paris",
        kind=CollectorKind.from_value("k8s"),
        identity=CollectorIdentity.create(FINGERPRINT),
        scopes=(DiscoveryScope.from_value("site/par1"),),
        version="1.0.0",
        registered_by="admin",
        endpoint_url="",
    )

    assert collector.kind is CollectorKind.KUBERNETES
    assert CollectorIdentity.create(FINGERPRINT, "").vault_secret_ref is None
    with pytest.raises(ValidationError, match="fingerprint"):
        collector.record_heartbeat(OTHER_FINGERPRINT, "1.0.1", "ok")
    with pytest.raises(ValidationError, match="heartbeat status"):
        collector.record_heartbeat(FINGERPRINT, "1.0.1", "bad")
    with pytest.raises(ValidationError, match="disable reason"):
        collector.disable(" ")
    with pytest.raises(ValidationError, match="job type"):
        DiscoveryJobAuthorization.decide(
            TenantId.from_value("default"),
            collector,
            collector.id.value,
            "bad",
            "site/par1",
            "!",
            "x",
        )
    with pytest.raises(ValidationError, match="target"):
        DiscoveryJobAuthorization.decide(
            TenantId.from_value("default"),
            collector,
            collector.id.value,
            FINGERPRINT,
            "site/par1",
            "snmp-scan",
            "",
        )

    invalid_fingerprint_decision = DiscoveryJobAuthorization.decide(
        TenantId.from_value("default"),
        collector,
        collector.id.value,
        "bad",
        "site/par1",
        "snmp-scan",
        "par1-core",
    )
    assert invalid_fingerprint_decision.reasons == ("fingerprint_invalid",)


def test_collector_kind_accepts_enterprise_proxy_aliases() -> None:
    assert CollectorKind.from_value("site-proxy").is_proxy is True
    assert CollectorKind.from_value("network_proxy").value == "network-proxy"
    assert CollectorKind.from_value("dc-proxy") is CollectorKind.DATACENTER_PROXY
    assert CollectorKind.from_value("snmp").is_proxy is False


def test_local_discovery_plan_is_plan_only_and_masks_execution_side_effects() -> None:
    plan = LocalDiscoveryPlan.create(
        tenant_id=TenantId.from_value("default"),
        edition="lite",
        name="  Discovery PAR1  ",
        scope="site/PAR1",
        protocol="snmp",
        targets=("10.20.30.10", "10.20.30.10", "srv-app-01"),
        credential_secret_ref=LOCAL_VAULT_REF,
        max_concurrency=4,
        rate_limit_per_minute=120,
        created_by="admin",
    )

    payload = plan.as_dict()

    assert plan.name == "Discovery PAR1"
    assert payload["edition"] == "lite"
    assert payload["targets_count"] == 2
    assert payload["dry_run"] is True
    assert payload["agent_required"] is False
    assert payload["network_scan_executed"] is False
    assert payload["rsot_write_enabled"] is False
    assert payload["jobs"][0]["credential_secret_ref"].startswith("vault://")
    assert "no_rsot_write" in payload["safeguards"]


def test_local_discovery_plan_validation_edges() -> None:
    assert LocalDiscoveryProtocol.from_value("ssh").value == "ssh"
    assert LocalDiscoveryTarget.from_value("SRV-APP-01").value == "srv-app-01"

    with pytest.raises(ValidationError, match="lite and pro"):
        LocalDiscoveryPlan.create(
            TenantId.from_value("default"),
            "enterprise",
            "Discovery",
            "site/par1",
            "snmp",
            ("10.0.0.1",),
            LOCAL_VAULT_REF,
            4,
            120,
            "admin",
        )
    with pytest.raises(ValidationError, match="credential_secret_ref"):
        LocalDiscoveryPlan.create(
            TenantId.from_value("default"),
            "pro",
            "Discovery",
            "site/par1",
            "snmp",
            ("10.0.0.1",),
            "",
            4,
            120,
            "admin",
        )
    with pytest.raises(ValidationError, match="URL credentials"):
        LocalDiscoveryTarget.from_value("https://admin:secret@example.test")
    with pytest.raises(ValidationError, match="protocol"):
        LocalDiscoveryProtocol.from_value("telnet")
