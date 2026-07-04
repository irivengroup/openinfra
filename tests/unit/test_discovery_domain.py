from __future__ import annotations

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.discovery import (
    CollectorIdentity,
    CollectorKind,
    DiscoveryCollector,
    DiscoveryJobAuthorization,
    DiscoveryScope,
)

FINGERPRINT = "a" * 64
OTHER_FINGERPRINT = "b" * 64


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
