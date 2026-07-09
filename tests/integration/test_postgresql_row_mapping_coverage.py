from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.common import TenantId, ValidationError
from openinfra.infrastructure.postgresql import (
    PostgreSQLAccessPolicyRepository,
    PostgreSQLAuditRepository,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLDcimRepository,
    PostgreSQLIpamRepository,
    PostgreSQLMigration,
    PostgreSQLMigrationCatalog,
    PostgreSQLSchemaStatus,
    PostgreSQLSecurityRepository,
    PostgreSQLSessionRegistry,
    PostgreSQLSourceGovernanceRepository,
    PostgreSQLSourceOfTruthRepository,
)


def _registry() -> PostgreSQLSessionRegistry:
    connection = FakeConnection()
    return PostgreSQLSessionRegistry(
        PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=lambda _dsn, _profile: connection,
        )
    )


def test_postgresql_value_objects_profiles_and_migration_validation(tmp_path: Path) -> None:
    profile = PostgreSQLClusterProfile.production_default()
    assert "application_name=openinfra-api" in profile.dsn_options()
    migration = PostgreSQLMigration(
        "0001_valid.sql",
        tmp_path / "0001_valid.sql",
        "CREATE TABLE x (id uuid) PARTITION BY HASH (id); CREATE INDEX x_i ON x(id); -- audit_events",
    )
    assert migration.checksum == migration.as_dict()["checksum"]
    migration.validate()
    for name, sql, message in (
        ("0001_bad.txt", migration.sql, "end with .sql"),
        ("0001_empty.sql", "SELECT 1", "controlled schema change"),
        (
            "0001_no_partition.sql",
            "CREATE TABLE x (id uuid); CREATE INDEX x_i ON x(id); -- audit_events",
            "partitioning",
        ),
        (
            "0001_no_index.sql",
            "CREATE TABLE x (id uuid) PARTITION BY HASH (id); -- audit_events",
            "indexes",
        ),
        (
            "0001_no_audit.sql",
            "CREATE TABLE x (id uuid) PARTITION BY HASH (id); CREATE INDEX x_i ON x(id);",
            "audit",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            PostgreSQLMigration(name, tmp_path / name, sql).validate()
    assert isinstance(
        PostgreSQLMigrationCatalog.from_project_root(tmp_path), PostgreSQLMigrationCatalog
    )
    assert PostgreSQLSchemaStatus(False, (), (migration,), "pending").as_dict()["ready"] is False


def test_postgresql_dcim_row_mappers_cover_optional_fields() -> None:
    repo = PostgreSQLDcimRepository(_registry())
    now = datetime.now(UTC)
    site = repo._site_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000001",
            "tenant_id": "default",
            "code": "PAR1",
            "name": "Paris",
            "country": "FR",
            "city": "Paris",
            "region": "IDF",
        }
    )
    building = repo._building_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000002",
            "tenant_id": "default",
            "site_code": "PAR1",
            "code": "BAT-A",
            "name": "A",
        }
    )
    floor = repo._floor_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000003",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "code": "F01",
            "name": "First",
            "level_index": 1,
        }
    )
    room = repo._room_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000004",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "code": "MMR1",
            "name": "Main",
            "rows": ["A"],
            "columns": ["01"],
            "floor_code": "F01",
            "zone_codes": ["Z1"],
            "coordinate_x": "1.5",
            "coordinate_y": "2.0",
            "coordinate_z": "0",
        }
    )
    zone = repo._zone_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000005",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "floor_code": "F01",
            "room_code": "MMR1",
            "code": "Z1",
            "name": "Zone",
            "rows": ["A"],
            "columns": ["01"],
        }
    )
    rack = repo._rack_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000006",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "room_code": "MMR1",
            "code": "R01",
            "row_code": "A",
            "column_code": "01",
            "units": 42,
            "coordinate_x": "3",
            "coordinate_y": "4",
            "coordinate_z": "0",
            "floor_code": "F01",
            "zone_code": "Z1",
            "usable_faces": ["front", "rear"],
            "max_weight_kg": "900",
            "power_capacity_watts": 22000,
        }
    )
    equipment = repo._equipment_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000007",
            "tenant_id": "default",
            "asset_tag": "SRV-1",
            "name": "Server",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "room_code": "MMR1",
            "row_code": "A",
            "column_code": "01",
            "rack_code": "R01",
            "u_position": 10,
            "coordinate_x": None,
            "coordinate_y": None,
            "coordinate_z": None,
            "floor_code": "F01",
            "zone_code": "Z1",
            "rack_face": "front",
            "u_height": 2,
        }
    )
    no_options = repo._room_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000008",
            "tenant_id": "default",
            "site_code": "PAR1",
            "building_code": "BAT-A",
            "code": "MMR2",
            "name": "Backup",
            "rows": ["A"],
            "columns": ["01"],
            "floor_code": None,
            "zone_codes": [],
            "coordinate_x": None,
            "coordinate_y": None,
            "coordinate_z": None,
        }
    )
    assert site.region == "IDF"
    assert building.code.value == "BAT-A"
    assert floor.level_index == 1
    assert room.coordinates is not None and room.coordinates.z == 0.0
    assert zone.code.value == "Z1"
    assert rack.power_capacity_watts == 22000
    assert equipment.location.rack_face is not None
    assert no_options.floor_code is None
    assert repo._float_or_none(None) is None
    assert repo._float_or_none("5.5") == 5.5
    assert now.tzinfo is not None


def test_postgresql_list_racks_in_room_uses_static_parameterized_sql() -> None:
    source = inspect.getsource(PostgreSQLDcimRepository.list_racks_in_room)

    assert "status_filter" not in source
    assert "{status_filter}" not in source
    assert "AND status = %(status)s" in source


def test_postgresql_security_access_identity_and_ipam_row_mappers() -> None:
    registry = _registry()
    tenant = TenantId.from_value("default")
    ipam = PostgreSQLIpamRepository(registry)
    security = PostgreSQLSecurityRepository(registry)
    access = PostgreSQLAccessPolicyRepository(registry)
    governance = PostgreSQLSourceGovernanceRepository(registry)
    now = datetime.now(UTC)
    prefix = ipam._prefix_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000011",
            "tenant_id": "default",
            "vrf_name": "default",
            "cidr": "10.0.0.0/30",
            "description": None,
        }
    )
    reservation = ipam._reservation_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000012",
            "tenant_id": "default",
            "vrf_name": "default",
            "prefix_cidr": "10.0.0.0/30",
            "address": "10.0.0.1",
            "hostname": "srv",
            "idempotency_key": "req",
        }
    )
    credential = security._credential_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000013",
            "tenant_id": "default",
            "subject": "admin",
            "token_hash": "a" * 64,
            "token_prefix": "aaaaaaaaaaaa",
            "roles": ["admin"],
            "active": True,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
            "last_used_at": None,
            "use_count": 0,
        }
    )
    access_rule = access._rule_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000014",
            "tenant_id": "default",
            "name": "rule-ok",
            "permission": "ipam.allocate",
            "effect": "allow",
            "subjects": ["admin"],
            "roles": ["admin"],
            "site_codes": ["PAR1"],
            "environments": ["prod"],
            "active": True,
            "created_at": now.isoformat(),
        }
    )
    governance_rule = governance._rule_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000015",
            "tenant_id": "default",
            "name": "serial-authority",
            "object_kind": "device",
            "attribute_path": "serial",
            "authoritative_source": "discovery",
            "priority": 10,
            "freshness_seconds": 3600,
            "conflict_strategy": "reject",
            "active": True,
            "created_at": now.isoformat(),
            "updated_at": now,
        }
    )
    assert prefix.description == ""
    assert reservation.address.exploded == "10.0.0.1"
    assert credential.is_usable(now) is True
    assert access_rule.matches_context(
        AccessRequestContext.create(tenant, access_rule.permission, "PAR1", "prod")
    )
    assert governance_rule.authoritative_source.value == "discovery"
    with pytest.raises(ValidationError):
        governance._offset("bad")
    with pytest.raises(ValidationError):
        governance._offset("-1")


def test_postgresql_source_of_truth_and_audit_row_mappers() -> None:
    registry = _registry()
    sot = PostgreSQLSourceOfTruthRepository(registry)
    audit = PostgreSQLAuditRepository(registry)
    tenant = TenantId.from_value("default")
    now = datetime.now(UTC)
    obj = sot._object_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000021",
            "tenant_id": "default",
            "object_key": "device/srv-1",
            "kind": "device",
            "display_name": "Server",
            "attributes": '{"serial":"S1"}',
            "tags": ["prod"],
            "source_system": "manual",
            "version": 2,
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now,
        }
    )
    snapshot = sot._snapshot_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000022",
            "tenant_id": "default",
            "object_key": "device/srv-1",
            "object_id": "00000000-0000-4000-8000-000000000021",
            "version": 2,
            "payload": {"display_name": "Server"},
            "changed_by": "pytest",
            "changed_at": now.isoformat(),
        }
    )
    relation = sot._relation_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000023",
            "tenant_id": "default",
            "relation_type": "runs_on",
            "source_key": "application/app",
            "target_key": "device/srv-1",
            "provenance": "manual",
            "valid_from": now.isoformat(),
            "valid_to": (now + timedelta(days=1)).isoformat(),
            "active": True,
            "created_at": now,
        }
    )
    params = sot._object_params(obj)
    event_record = audit._record_from_row(
        {
            "id": "00000000-0000-4000-8000-000000000024",
            "tenant_id": "default",
            "actor": "pytest",
            "action": "audit.test",
            "target_type": "unit",
            "target_id": "row",
            "severity": "info",
            "metadata": '{"k":"v"}',
            "created_at": now,
            "previous_hash": None,
            "record_hash": None,
        }
    )
    assert obj.attributes["serial"] == "S1"
    assert snapshot.payload["display_name"] == "Server"
    assert relation.valid_to is not None
    assert params["object_key"] == "device/srv-1"
    assert event_record.verifies() is True
    with pytest.raises(ValidationError):
        sot._offset("bad")
    with pytest.raises(ValidationError):
        sot._offset("-1")
    with pytest.raises(ValidationError):
        audit.list_events(tenant, 0)
    with pytest.raises(ValidationError):
        audit.verify_integrity(tenant, 0)
