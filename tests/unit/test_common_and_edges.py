from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.domain.common import (
    AuditEvent,
    Code,
    Coordinates3D,
    DomainEvent,
    EntityId,
    Name,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.dcim import EquipmentLocation, Site
from openinfra.domain.discovery import DiscoveryEvidence, DiscoverySource, ReconciliationDecision
from openinfra.domain.ipam import AllocationRequest, IpReservation, NetworkInterface, Prefix, Vrf
from openinfra.domain.itam import Asset
from openinfra.infrastructure.json_store import (
    IterableSerializer,
    JsonAuditRepository,
    JsonDocumentStore,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLClusterProfile,
    PostgreSQLMigration,
    PostgreSQLMigrationCatalog,
)
from openinfra.infrastructure.spec_validation import ContractualSpecValidator
from openinfra.interfaces.cli import OpenInfraCLI


class TestCommonDomainEdges:
    def test_entity_id_rejects_invalid_uuid(self) -> None:
        with pytest.raises(ValidationError):
            EntityId.from_value("not-a-uuid")

    def test_tenant_code_name_and_pagination_reject_invalid_values(self) -> None:
        with pytest.raises(ValidationError):
            TenantId.from_value("x")
        with pytest.raises(ValidationError):
            Code.from_value("invalid value")
        with pytest.raises(ValidationError):
            Name.from_value("")
        with pytest.raises(ValidationError):
            Pagination.from_values(0)
        with pytest.raises(ValidationError):
            Pagination.from_values(10, " ")

    def test_domain_and_audit_events_validate_names_and_json_payloads(self) -> None:
        tenant = TenantId.from_value("default")
        aggregate_id = EntityId.new()
        event = DomainEvent.create(tenant, aggregate_id, "asset.created", {"asset": "A1"})
        audit = AuditEvent.record(tenant, "tester", "asset.created", "asset", "A1")

        assert event.name == "asset.created"
        assert audit.severity == Severity.INFO

        with pytest.raises(ValidationError):
            DomainEvent.create(tenant, aggregate_id, "Invalid", {})
        with pytest.raises(ValidationError):
            AuditEvent.record(tenant, "", "asset.created", "asset", "A1")
        with pytest.raises(ValidationError):
            AuditEvent.record(tenant, "tester", "x", "asset", "A1")
        with pytest.raises(ValidationError):
            AuditEvent.record(tenant, "tester", "asset.created", "x", "A1")
        with pytest.raises(ValidationError):
            AuditEvent.record(tenant, "tester", "asset.created", "asset", "")

    def test_site_and_coordinates_validation(self) -> None:
        tenant = TenantId.from_value("default")
        site = Site.create(tenant, "PAR1", "Paris", "FR", "Paris")
        assert site.country == "FR"
        with pytest.raises(ValidationError):
            Site.create(tenant, "PAR1", "Paris", "FRA", "Paris")
        with pytest.raises(ValidationError):
            Coordinates3D.from_values(-1.0, 0.0, 0.0)

    def test_equipment_location_with_coordinates_and_u_rules(self) -> None:
        coordinates = Coordinates3D.from_values(1.0, 2.0, 3.0)
        location = EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "A",
            "01",
            coordinates=coordinates,
        )
        assert "xyz=1.00/2.00/3.00" in location.human_readable()
        with pytest.raises(ValidationError):
            EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01", u_position=1)
        with pytest.raises(ValidationError):
            EquipmentLocation.create("PAR1", "BAT-A", "MMR1", "A", "01", "R1", 99)

    def test_vrf_network_interface_asset_and_discovery(self) -> None:
        tenant = TenantId.from_value("default")
        vrf = Vrf.create(tenant, "default", "65000:1")
        interface = NetworkInterface.create(tenant, "SRV-1", "eth0", "aa:bb:cc:dd:ee:ff")
        asset = Asset.create(tenant, "SRV-1", "Server 1", owner="Ops")
        evidence = DiscoveryEvidence.create(
            tenant,
            DiscoverySource.SNMP,
            "snmp-1",
            0.9,
            {"sysName": "srv"},
        )
        decision = ReconciliationDecision.create(evidence.id, True, "same serial number")

        assert vrf.route_distinguisher == "65000:1"
        assert interface.mac_address == "aa:bb:cc:dd:ee:ff"
        assert asset.owner == "Ops"
        assert decision.accepted is True

        with pytest.raises(ValidationError):
            Vrf.create(tenant, "default", " ")
        with pytest.raises(ValidationError):
            NetworkInterface.create(tenant, "SRV-1", "eth0", "invalid")
        with pytest.raises(ValidationError):
            DiscoveryEvidence.create(tenant, DiscoverySource.SSH, "", 0.5, {})
        with pytest.raises(ValidationError):
            DiscoveryEvidence.create(tenant, DiscoverySource.SSH, "ssh-1", 1.5, {})
        with pytest.raises(ValidationError):
            ReconciliationDecision.create(evidence.id, True, "")

    def test_ipam_validation_edges(self) -> None:
        tenant = TenantId.from_value("default")
        prefix = Prefix.create(tenant, "default", "2001:db8::/126")
        assert prefix.first_usable_int == int(prefix.network.network_address)
        with pytest.raises(ValidationError):
            Prefix.create(tenant, "default", "10.0.0.1/32")
        with pytest.raises(ValidationError):
            Prefix.create(tenant, "default", "not-a-prefix")
        with pytest.raises(ValidationError):
            IpReservation.create(tenant, "default", prefix, "10.0.0.1", "srv", "key")
        with pytest.raises(ValidationError):
            IpReservation.create(tenant, "default", prefix, "2001:db8::1", "", "key")
        with pytest.raises(ValidationError):
            IpReservation.create(tenant, "default", prefix, "2001:db8::1", "srv", "")
        request = AllocationRequest.create("default", "default", "2001:db8::/126", "srv", "req")
        assert request.hostname == "srv"

    def test_json_audit_repository_roundtrip_and_serializer(self, tmp_path: Path) -> None:
        store = JsonDocumentStore(tmp_path / "state.json")
        repo = JsonAuditRepository(store)
        tenant = TenantId.from_value("default")
        repo.append(AuditEvent.record(tenant, "tester", "asset.created", "asset", "A1"))
        store.flush()

        events = JsonAuditRepository(JsonDocumentStore(tmp_path / "state.json")).list_events()
        rendered = IterableSerializer().to_json_array([{"events": len(events)}])

        assert len(events) == 1
        assert '"events": 1' in rendered

    def test_postgresql_helpers_and_invalid_migrations(self, tmp_path: Path) -> None:
        profile = PostgreSQLClusterProfile.production_default()
        assert "statement_timeout" in profile.dsn_options()
        invalid = PostgreSQLMigration("bad.txt", tmp_path / "bad.txt", "SELECT 1")
        with pytest.raises(ValidationError):
            invalid.validate()
        with pytest.raises(ValidationError):
            PostgreSQLMigrationCatalog(tmp_path).load("../bad")
        with pytest.raises(ValidationError):
            PostgreSQLMigrationCatalog(tmp_path).load("missing")

    def test_invalid_spec_and_cli_error(self, tmp_path: Path, capsys: object) -> None:
        report = ContractualSpecValidator().validate(tmp_path)
        assert report.valid is False
        assert "missing required spec file" in report.as_text()

        code = OpenInfraCLI().run(
            [
                "database",
                "render-migration",
                "--name",
                "missing",
                "--root",
                str(tmp_path),
            ]
        )
        captured = capsys.readouterr()
        assert code == 2
        assert "migration not found" in captured.err
