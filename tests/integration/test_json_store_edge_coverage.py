from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.domain.access_policy import AccessPolicyEffect, AccessPolicyRule
from openinfra.domain.audit import AuditEventFilter
from openinfra.domain.common import AuditEvent, Pagination, Severity, TenantId, ValidationError
from openinfra.domain.dcim import DcimCable, DcimCablePathSegment, DcimPortEndpoint
from openinfra.domain.editions import QuotaResource
from openinfra.domain.identity import GroupMembership, IdentityGroup, IdentityUser
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpPeer,
    IpRange,
    IpReservation,
    Prefix,
    Vlan,
    Vrf,
)
from openinfra.domain.security import ApiTokenCredential, Permission
from openinfra.domain.source_governance import SourceGovernanceRule
from openinfra.domain.source_of_truth import SourceOfTruthObject, SourceRelation
from openinfra.infrastructure.json_store import (
    JsonAccessPolicyRepository,
    JsonAuditRepository,
    JsonDcimRepository,
    JsonDocumentStore,
    JsonIdentityRepository,
    JsonImportRepository,
    JsonIpamRepository,
    JsonReadinessProbe,
    JsonRuntimeUsageRepository,
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
    assert identity.grant_group_role(tenant, "netops", "rsot:reader") is True
    assert identity.grant_group_role(tenant, "netops", "rsot:reader") is False
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


def test_json_store_operational_edge_contracts(tmp_path: Path) -> None:
    tenant = TenantId.from_value("default")
    store = JsonDocumentStore(tmp_path / "state.json")
    usage = JsonRuntimeUsageRepository(store)
    assert usage.count_resource(tenant, QuotaResource.EQUIPMENT) == 0
    assert usage.count_resource(tenant, QuotaResource.SUBNET_VLAN) == 0
    assert usage.count_resource(tenant, QuotaResource.IP_DNS_RECORD) == 0
    assert usage.count_resource(tenant, QuotaResource.USER) == 0
    assert usage.count_resource(tenant, QuotaResource.DISCOVERY_COLLECTOR) == 0
    store.data["audit_events"] = [{"tenant_id": "default"}, {"tenant_id": "other"}]
    assert usage._count_items("audit_events", tenant) == 1
    with pytest.raises(AssertionError):
        usage.count_resource(tenant, object())  # type: ignore[arg-type]

    imports = JsonImportRepository(store)
    malformed_cases = (
        ("migration_plans", "plan-text", "not-a-dict"),
        ("migration_plans", "plan-template", {"template": []}),
        ("migration_plans", "plan-details", {"template": {}, "gaps": {}, "import_report": {}}),
        (
            "migration_plans",
            "plan-mapping",
            {"template": {"mapping": []}, "gaps": [], "import_report": {}},
        ),
        (
            "migration_plans",
            "plan-required",
            {
                "template": {"mapping": {}, "source": "device42", "required_columns": {}},
                "gaps": [],
                "import_report": {},
            },
        ),
        (
            "migration_plans",
            "plan-metadata",
            {
                "template": {
                    "mapping": {},
                    "source": "device42",
                    "required_columns": [],
                    "recommended_columns": {},
                    "notes": [],
                },
                "gaps": [],
                "import_report": {},
            },
        ),
        ("import_jobs", "import-mapping", {"mapping": []}),
        ("import_jobs", "import-rows", {"mapping": {}, "impacts": {}, "dlq": []}),
        ("bulk_import_jobs", "bulk-mapping", {"mapping": []}),
        ("bulk_import_jobs", "bulk-metrics", {"mapping": {}, "metrics": [], "checkpoint": {}}),
        (
            "bulk_import_jobs",
            "bulk-samples",
            {"mapping": {}, "metrics": {}, "checkpoint": {}, "impact_sample": {}, "dlq_sample": []},
        ),
    )
    for bucket, job_id, payload in malformed_cases:
        store.data[bucket]["default:" + job_id] = payload
        with pytest.raises(ValidationError):
            if bucket == "migration_plans":
                imports.get_migration_plan_report(tenant, job_id)
            elif bucket == "import_jobs":
                imports.get_import_report(tenant, job_id)
            else:
                imports.get_bulk_import_report(tenant, job_id)


def test_json_store_datetime_cursor_and_filter_edges(tmp_path: Path) -> None:
    tenant = TenantId.from_value("default")
    store = JsonDocumentStore(tmp_path / "state.json")

    security = JsonSecurityRepository(store)
    credential = ApiTokenCredential.create(
        tenant,
        "bob",
        "c" * 64,
        "cccccccccccc",
        ("viewer",),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    security.upsert_token(credential)
    token_key = next(iter(store.data["security_tokens"]))
    store.data["security_tokens"][token_key]["created_at"] = datetime.now(UTC)
    assert security.list_tokens(tenant, Pagination.from_values(10), include_inactive=True).items
    assert security.revoke_token(tenant, "c" * 64, "pytest") is True
    assert security.revoke_token(tenant, "c" * 64, "pytest") is False
    with pytest.raises(ValidationError):
        security.list_tokens(tenant, Pagination.from_values(1, "-1"), include_inactive=True)

    access = JsonAccessPolicyRepository(store)
    rule = AccessPolicyRule.create(
        tenant,
        "rule-b",
        Permission.DCIM_LOCATE,
        AccessPolicyEffect.ALLOW.value,
        subjects=("bob",),
    )
    access.upsert_rule(rule)
    access_key = next(iter(store.data["access_policy_rules"]))
    store.data["access_policy_rules"][access_key]["created_at"] = datetime.now(UTC)
    assert access.list_rules(tenant, Pagination.from_values(10), include_inactive=True).items
    with pytest.raises(ValidationError):
        access.list_rules(tenant, Pagination.from_values(1, "-1"), include_inactive=True)

    governance = JsonSourceGovernanceRepository(store)
    gov_rule = SourceGovernanceRule.create(
        tenant, "asset-authority", "device", "asset", "manual", 10, None, "accept_with_audit"
    )
    governance.upsert_rule(gov_rule)
    governance.upsert_rule(gov_rule)
    gov_key = next(iter(store.data["source_governance_rules"]))
    store.data["source_governance_rules"][gov_key]["created_at"] = "2026-07-07T09:00:00"
    assert governance.find_rule(tenant, "asset-authority") is not None
    with pytest.raises(ValidationError):
        governance.list_rules(tenant, Pagination.from_values(1, "-1"))

    audit = JsonAuditRepository(store)
    event = AuditEvent.record(tenant, "pytest", "audit.edge", "unit", "edge")
    audit.append(event)
    audit_payload = store.data["audit_events"][-1]
    audit_payload["created_at"] = "2026-07-07T09:01:00"
    audit_payload.pop("record_hash", None)
    assert audit.list_records(AuditEventFilter.create(tenant, Pagination.from_values(10))).items
    assert (
        audit.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(10), target_id="other")
        ).items
        == ()
    )
    assert (
        audit.list_records(
            AuditEventFilter.create(
                tenant,
                Pagination.from_values(10),
                created_from=datetime(2026, 7, 7, 10, 0, tzinfo=UTC),
            )
        ).items
        == ()
    )
    with pytest.raises(ValidationError):
        audit.verify_integrity(tenant, limit=0)

    sot = JsonSourceOfTruthRepository(store)
    sot.create_object(
        tenant,
        "device/fw-edge",
        "network-device",
        "Firewall Edge",
        {"resource_category": "network-device", "resource_type": "firewall"},
        ("edge",),
        "manual",
        "pytest",
    )
    object_key = next(iter(store.data["source_objects"]))
    store.data["source_objects"][object_key]["created_at"] = "2026-07-07T09:02:00"
    store.data["source_objects"][object_key]["updated_at"] = "2026-07-07T09:03:00"
    store.data["source_object_snapshots"][0]["changed_at"] = "2026-07-07T09:04:00"
    assert sot.find_object(tenant, "device/fw-edge") is not None
    assert sot.find_object_version(tenant, "device/fw-edge", 1) is not None
    assert sot.list_objects(tenant, Pagination.from_values(10), resource_type="firewall").items
    assert (
        sot.find_object_as_of(tenant, "device/fw-edge", datetime(2026, 7, 7, 8, 0, tzinfo=UTC))
        is None
    )
    sot.create_object(
        tenant,
        "application/fw-policy",
        "application",
        "Firewall Policy",
        {},
        ("edge",),
        "manual",
        "pytest",
    )
    relation = SourceRelation.create(
        tenant,
        "depends_on",
        "application/fw-policy",
        "device/fw-edge",
        "manual",
        valid_to=datetime(2027, 7, 8, 0, 0, tzinfo=UTC),
    )
    sot.add_relation(relation)
    relation_key = next(iter(store.data["source_relations"]))
    store.data["source_relations"][relation_key]["valid_from"] = "2026-07-07T09:05:00"
    store.data["source_relations"][relation_key]["valid_to"] = "2026-07-08T09:05:00"
    store.data["source_relations"][relation_key]["created_at"] = "2026-07-07T09:05:01"
    assert sot.list_relations(
        tenant,
        Pagination.from_values(10),
        source_key="application/fw-policy",
        target_key="device/fw-edge",
        relation_type="depends_on",
        as_of=datetime(2026, 7, 7, 10, 0, tzinfo=UTC),
    ).items


def test_json_store_remaining_repository_branches(tmp_path: Path) -> None:
    tenant = TenantId.from_value("default")
    other_tenant = TenantId.from_value("other")
    store = JsonDocumentStore(tmp_path / "state.json")

    dcim = JsonDcimRepository(store)
    default_endpoint = DcimPortEndpoint.create("equipment", "SRV-EDGE-01", "ETH0")
    default_cable = DcimCable.create(
        tenant,
        "CAB-EDGE-01",
        default_endpoint,
        DcimPortEndpoint.create("patch_panel", "PP-EDGE-01", "P01"),
        "copper",
        "installed",
        (DcimCablePathSegment.create(1, "A01/R01"),),
    )
    foreign_cable = DcimCable.create(
        other_tenant,
        "CAB-FOREIGN-01",
        default_endpoint,
        DcimPortEndpoint.create("patch_panel", "PP-FOREIGN-01", "P01"),
        "copper",
        "installed",
        (DcimCablePathSegment.create(1, "B01/R01"),),
    )
    dcim.add_dcim_cable(foreign_cable)
    dcim.add_dcim_cable(default_cable)
    assert dcim.find_active_dcim_cable_by_endpoint(tenant, default_endpoint) == default_cable
    assert dcim.list_dcim_cables_by_endpoint(tenant, default_endpoint) == (default_cable,)
    with pytest.raises(Exception):
        dcim.add_dcim_cable(default_cable)

    ipam = JsonIpamRepository(store)
    prefix = ipam.get_or_create_prefix(Prefix.create(tenant, "default", "10.20.0.0/29"))
    ip_range = IpRange.create(tenant, "default", prefix, "10.20.0.1", "10.20.0.2")
    assert ipam.add_range(ip_range) == ip_range
    assert ipam.add_range(ip_range) == ip_range
    with pytest.raises(ValidationError):
        ipam.acquire_allocation_lock(tenant, "default", "  ")
    vlan = Vlan.create(tenant, "prod", 120, "Prod VLAN", "default")
    asn = AutonomousSystem.create(tenant, 64512, "edge-as")
    peer = BgpPeer.create(tenant, "default", 64512, 64513, "192.0.2.1")
    assert ipam.add_vlan(vlan) == vlan
    assert ipam.add_vlan(vlan) == vlan
    assert ipam.add_asn(asn) == asn
    assert ipam.add_asn(asn) == asn
    assert ipam.add_bgp_peer(peer) == peer
    assert ipam.add_bgp_peer(peer) == peer

    identity = JsonIdentityRepository(store)
    user = IdentityUser.create(tenant, "edge-user", "Edge User", "edge@example.org", ("viewer",))
    group = IdentityGroup.create(tenant, "edge-team", "Edge Team", ("dcim:operator",))
    identity.upsert_user(user)
    identity.upsert_group(group)
    group_key = next(iter(store.data["identity_groups"]))
    store.data["identity_groups"][group_key]["created_at"] = datetime.now(UTC)
    restored_group = identity._group_from_dict(store.data["identity_groups"][group_key])
    assert restored_group.name == group.name
    store.data["identity_memberships"]["other:edge-user:edge-team"] = {
        "tenant_id": "other",
        "username": "edge-user",
        "group_name": "edge-team",
    }
    assert identity.effective_identity_for_subject(tenant, "edge-user").groups == ()

    security = JsonSecurityRepository(store)
    credential = ApiTokenCredential.create(
        tenant,
        "edge-user",
        "d" * 64,
        "dddddddddddd",
        ("viewer",),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    security.upsert_token(credential)
    security.record_token_used(tenant, "d" * 64)
    security.upsert_token(credential)
    preserved = security.list_tokens(
        tenant, Pagination.from_values(1), include_inactive=True
    ).items[0]
    assert preserved.last_used_at is not None
    assert preserved.use_count == 1
    with pytest.raises(ValidationError):
        security.list_tokens(tenant, Pagination.from_values(1, "abc"), include_inactive=True)
