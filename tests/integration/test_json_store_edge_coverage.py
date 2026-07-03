from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.domain.access_policy import AccessPolicyEffect, AccessPolicyRule
from openinfra.domain.audit import AuditEventFilter
from openinfra.domain.common import AuditEvent, Pagination, Severity, TenantId, ValidationError
from openinfra.domain.identity import GroupMembership, IdentityGroup, IdentityUser
from openinfra.domain.ipam import IpReservation, Prefix, Vrf
from openinfra.domain.security import ApiTokenCredential, Permission
from openinfra.domain.source_governance import SourceGovernanceRule
from openinfra.domain.source_of_truth import SourceOfTruthObject, SourceRelation
from openinfra.infrastructure.json_store import (
    JsonAccessPolicyRepository,
    JsonAuditRepository,
    JsonDocumentStore,
    JsonIdentityRepository,
    JsonIpamRepository,
    JsonReadinessProbe,
    JsonSecurityRepository,
    JsonSourceGovernanceRepository,
    JsonSourceOfTruthRepository,
    JsonTransactionManager,
)


def test_json_store_repository_edge_paths(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"unknown": {}, "vrfs": {}}), encoding="utf-8")
    store = JsonDocumentStore(state_path)
    store.flush()
    assert "unknown" not in store.data
    assert JsonReadinessProbe(store).check().ready is True
    snapshot = store.snapshot()
    with JsonTransactionManager(store).begin():
        store.data["vrfs"]["dirty"] = {"value": True}
    assert "dirty" not in store.data["vrfs"]
    store.restore(snapshot)

    tenant = TenantId.from_value("default")
    ipam = JsonIpamRepository(store)
    vrf = Vrf.create(tenant, "default")
    ipam.add_vrf(vrf)
    with pytest.raises(Exception):
        ipam.add_vrf(vrf)
    prefix = ipam.get_or_create_prefix(Prefix.create(tenant, "default", "10.1.0.0/30"))
    assert ipam.get_or_create_prefix(prefix).network == prefix.network
    reservation = IpReservation.create(tenant, "default", prefix, "10.1.0.1", "srv", "req-1")
    ipam.add_reservation(reservation)
    assert ipam.find_reservation_by_key(tenant, "default", "req-1") is not None
    assert ipam.list_reservations(tenant, "default", "10.1.0.0/30")
    with pytest.raises(Exception):
        ipam.add_reservation(reservation)
    duplicate_address = IpReservation.create(tenant, "default", prefix, "10.1.0.1", "srv2", "req-2")
    with pytest.raises(Exception):
        ipam.add_reservation(duplicate_address)

    identity = JsonIdentityRepository(store)
    user = IdentityUser.create(tenant, "alice", "Alice", "alice@example.org", ("viewer",))
    group = IdentityGroup.create(tenant, "netops", "NetOps", ("ipam:operator",))
    identity.upsert_user(user)
    identity.upsert_user(user)
    identity.upsert_group(group)
    identity.upsert_group(group)
    with pytest.raises(ValidationError):
        identity.add_membership(GroupMembership.create(tenant, "missing", "netops"))
    with pytest.raises(ValidationError):
        identity.add_membership(GroupMembership.create(tenant, "alice", "missing"))
    identity.add_membership(GroupMembership.create(tenant, "alice", "netops"))
    assert identity.grant_user_role(tenant, "alice", "dcim:operator") is True
    assert identity.grant_user_role(tenant, "alice", "dcim:operator") is False
    assert identity.grant_group_role(tenant, "netops", "sot:reader") is True
    assert identity.grant_group_role(tenant, "netops", "sot:reader") is False
    assert identity.effective_identity_for_subject(tenant, "alice").groups == ("netops",)
    assert identity.effective_identity_for_subject(tenant, "unknown").active is False
    with pytest.raises(ValidationError):
        identity.grant_user_role(tenant, "unknown", "viewer")
    with pytest.raises(ValidationError):
        identity.grant_group_role(tenant, "unknown", "viewer")

    security = JsonSecurityRepository(store)
    credential = ApiTokenCredential.create(
        tenant,
        "alice",
        "a" * 64,
        "aaaaaaaaaaaa",
        ("viewer",),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    security.upsert_token(credential)
    assert security.find_active_token_by_hash(tenant, "a" * 64) is not None
    assert (
        security.list_tokens(tenant, Pagination.from_values(1), include_inactive=False).next_cursor
        is None
    )
    assert security.record_token_used(tenant, "a" * 64) is None
    assert security.revoke_token(tenant, "a" * 64, "pytest") is True
    assert security.revoke_token(tenant, "b" * 64, "pytest") is False
    assert security.find_active_token_by_hash(tenant, "a" * 64) is None

    access = JsonAccessPolicyRepository(store)
    rule = AccessPolicyRule.create(
        tenant,
        "rule-a",
        Permission.IPAM_ALLOCATE,
        AccessPolicyEffect.ALLOW.value,
        subjects=("alice",),
        site_codes=("PAR1",),
        environments=("prod",),
    )
    access.upsert_rule(rule)
    access.upsert_rule(rule)
    assert access.list_rules(tenant, Pagination.from_values(1), include_inactive=True).items
    assert access.find_active_rules_for_permission(tenant, rule.permission)
    assert access.deactivate_rule(tenant, "rule-a") is True
    assert access.deactivate_rule(tenant, "missing") is False
    assert access.find_active_rules_for_permission(tenant, rule.permission) == ()
    with pytest.raises(ValidationError):
        access.list_rules(tenant, Pagination.from_values(1, "bad"), include_inactive=True)

    governance = JsonSourceGovernanceRepository(store)
    gov_rule = SourceGovernanceRule.create(
        tenant, "serial-authority", "device", "serial", "discovery", 100, None, "reject"
    )
    governance.upsert_rule(gov_rule)
    assert governance.find_rule(tenant, "serial-authority") is not None
    assert governance.list_rules(tenant, Pagination.from_values(1), object_kind="device").items
    assert governance.find_active_rules_for_kind(tenant, "device")
    assert governance.deactivate_rule(tenant, "serial-authority") is True
    assert governance.deactivate_rule(tenant, "missing") is False
    with pytest.raises(ValidationError):
        governance.list_rules(tenant, Pagination.from_values(1, "bad"))

    audit = JsonAuditRepository(store)
    first = AuditEvent.record(tenant, "pytest", "audit.first", "unit", "1")
    second = AuditEvent.record(
        tenant, "pytest", "audit.second", "unit", "2", severity=Severity.WARNING
    )
    audit.append(first)
    audit.append(second)
    assert (
        audit.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(1), actor="pytest")
        ).next_cursor
        == "1"
    )
    assert (
        audit.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(10), action="none")
        ).items
        == ()
    )
    assert audit.list_records(
        AuditEventFilter.create(tenant, Pagination.from_values(10), target_type="unit")
    ).items
    assert audit.list_records(
        AuditEventFilter.create(tenant, Pagination.from_values(10), severity="warning")
    ).items
    assert audit.verify_integrity(tenant).valid is True
    with pytest.raises(ValidationError):
        audit.list_records(AuditEventFilter.create(tenant, Pagination.from_values(1, "bad")))
    with pytest.raises(ValidationError):
        audit.list_records(AuditEventFilter.create(tenant, Pagination.from_values(1, "-1")))

    sot = JsonSourceOfTruthRepository(store)
    obj1 = SourceOfTruthObject.create(
        tenant, "device/srv-a", "device", "Srv A", {"serial": "A"}, ("prod",), "manual"
    )
    SourceOfTruthObject.create(
        tenant, "application/app-a", "application", "App A", {}, ("prod",), "manual"
    )
    sot.create_object(
        tenant, "device/srv-a", "device", "Srv A", {"serial": "A"}, ("prod",), "manual", "pytest"
    )
    sot.upsert_object(obj1.revise(None, {"serial": "B"}, None, "manual"), "pytest")
    sot.create_object(
        tenant, "application/app-a", "application", "App A", {}, ("prod",), "manual", "pytest"
    )
    relation = SourceRelation.create(
        tenant, "runs_on", "application/app-a", "device/srv-a", "manual"
    )
    sot.add_relation(relation)
    assert sot.find_object(tenant, "device/srv-a") is not None
    assert sot.find_object_version(tenant, "device/srv-a", 1) is not None
    assert (
        sot.list_objects(tenant, Pagination.from_values(1), kind="device", tag="prod").next_cursor
        is None
    )
    assert sot.list_relations(
        tenant,
        Pagination.from_values(1),
        source_key="application/app-a",
        target_key="device/srv-a",
        relation_type="runs_on",
    ).items
    with pytest.raises(ValidationError):
        sot.list_objects(tenant, Pagination.from_values(1, "bad"))
    with pytest.raises(ValidationError):
        sot.list_relations(tenant, Pagination.from_values(1, "-1"))
