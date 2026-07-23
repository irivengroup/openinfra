from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from openinfra.application.field_operation_services import (
    FieldLocationResolver,
    FieldSafetyAssessmentService,
    GenerateFieldOperationSheetCommand,
)
from openinfra.domain.common import NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import (
    Coordinates3D,
    DcimPort,
    DcimPortEndpoint,
    EquipmentLocation,
    PowerDevice,
    PowerFeedSide,
    Rack,
    RackFace,
)
from openinfra.domain.field_operations import FieldPhysicalLocation
from openinfra.domain.flow_matrix import FlowSelectorKind


def _command(
    target_type: str, target_id: str, **overrides: object
) -> GenerateFieldOperationSheetCommand:
    values: dict[str, object] = {
        "tenant_id": "default",
        "actor": "pytest",
        "admin_token": "t" * 40,
        "target_type": target_type,
        "target_id": target_id,
        "title": "Intervention terrain",
        "purpose": "Valider la résolution de localisation physique.",
        "owner": "ops.owner",
        "operator": "field.operator",
    }
    values.update(overrides)
    return GenerateFieldOperationSheetCommand(**values)  # type: ignore[arg-type]


def _rack() -> Rack:
    return Rack.create(
        TenantId.from_value("default"),
        "PAR1",
        "BAT-A",
        "MMR1",
        "R42",
        "B",
        "12",
        42,
        Coordinates3D.from_values(12.0, 4.0, 0.0),
        floor_code="F01",
        zone_code="Z1",
    )


def test_location_resolver_covers_equipment_rack_and_power_device_targets() -> None:
    tenant = TenantId.from_value("default")
    dcim = MagicMock()
    certificates = MagicMock()
    resolver = FieldLocationResolver(dcim, certificates)
    equipment = SimpleNamespace(
        location=EquipmentLocation.create(
            "PAR1",
            "BAT-A",
            "MMR1",
            "B",
            "12",
            "R42",
            10,
            Coordinates3D.from_values(12.0, 4.0, 0.0),
            "F01",
            "Z1",
            "front",
            2,
        )
    )
    rack = _rack()
    power_device = PowerDevice.create(
        tenant, "PDU-A", "pdu", "PAR1", "BAT-A", "MMR1", "R42", "A", 12000
    )
    dcim.find_equipment.return_value = equipment
    dcim.find_rack.return_value = rack
    dcim.find_power_device.return_value = power_device

    equipment_location = resolver.resolve(tenant, _command("equipment", "SRV-01"))
    assert equipment_location.rack == "R42"
    assert equipment_location.rack_face == "front"
    assert equipment_location.u_position == 10

    rack_location = resolver.resolve(
        tenant,
        _command("rack", "R42", site="PAR1", building="BAT-A", room="MMR1"),
    )
    assert rack_location.floor == "F01"
    assert rack_location.zone == "Z1"

    power_location = resolver.resolve(tenant, _command("power-device", "PDU-A"))
    assert power_location.rack == "R42"

    dcim.find_equipment.return_value = None
    with pytest.raises(NotFoundError, match="equipment"):
        resolver.resolve(tenant, _command("equipment", "UNKNOWN"))

    with pytest.raises(ValidationError, match="site, building and room"):
        resolver.resolve(tenant, _command("rack", "R42"))

    dcim.find_rack.return_value = None
    with pytest.raises(NotFoundError, match="rack"):
        resolver.resolve(
            tenant,
            _command("rack", "R404", site="PAR1", building="BAT-A", room="MMR1"),
        )

    dcim.find_power_device.return_value = None
    with pytest.raises(NotFoundError, match="power device"):
        resolver.resolve(tenant, _command("power-device", "PDU-404"))

    dcim.find_power_device.return_value = PowerDevice.create(
        tenant, "UPS-01", "ups", "PAR1", "BAT-A", "MMR1", None, None, 12000
    )
    with pytest.raises(ValidationError, match="no rack"):
        resolver.resolve(tenant, _command("power-device", "UPS-01"))


def test_location_resolver_covers_certificate_and_cable_endpoints() -> None:
    tenant = TenantId.from_value("default")
    dcim = MagicMock()
    certificates = MagicMock()
    resolver = FieldLocationResolver(dcim, certificates)
    rack = _rack()
    equipment = SimpleNamespace(
        location=EquipmentLocation.create(
            "PAR1", "BAT-A", "MMR1", "B", "12", "R42", 10, floor_code="F01"
        )
    )
    certificates.get_certificate_by_fingerprint.return_value = object()
    dcim.find_rack.return_value = rack

    certificate_location = resolver.resolve(
        tenant,
        _command(
            "certificate",
            "cert-fingerprint",
            location_target_type="rack",
            location_target_id="R42",
            site="PAR1",
            building="BAT-A",
            room="MMR1",
        ),
    )
    assert certificate_location.rack == "R42"

    certificates.get_certificate_by_fingerprint.return_value = None
    certificates.get_certificate.return_value = None
    with pytest.raises(NotFoundError, match="certificate"):
        resolver.resolve(
            tenant,
            _command(
                "certificate",
                "missing",
                location_target_type="rack",
                location_target_id="R42",
                site="PAR1",
                building="BAT-A",
                room="MMR1",
            ),
        )

    certificates.get_certificate.return_value = object()
    with pytest.raises(ValidationError, match="physical location target"):
        resolver.resolve(tenant, _command("certificate", "cert-id"))
    with pytest.raises(ValidationError, match="own physical location"):
        resolver.resolve(
            tenant,
            _command(
                "certificate",
                "cert-id",
                location_target_type="certificate",
                location_target_id="cert-id",
            ),
        )

    equipment_endpoint = DcimPortEndpoint.create("equipment", "SRV-01", "ETH0")
    dcim.find_dcim_cable.return_value = SimpleNamespace(
        a_endpoint=equipment_endpoint,
        b_endpoint=DcimPortEndpoint.create("equipment", "SRV-02", "ETH0"),
    )
    dcim.find_equipment.side_effect = [equipment]
    cable_location = resolver.resolve(tenant, _command("cable", "CBL-01"))
    assert cable_location.rack == "R42"

    patch_endpoint = DcimPortEndpoint.create("patch_panel", "PP-01", "P01")
    dcim.find_dcim_cable.return_value = SimpleNamespace(
        a_endpoint=patch_endpoint,
        b_endpoint=DcimPortEndpoint.create("patch_panel", "PP-02", "P01"),
    )
    dcim.find_dcim_port.return_value = DcimPort.create(
        tenant,
        "patch_panel",
        "PP-01",
        "P01",
        "PAR1",
        "BAT-A",
        "MMR1",
        "rj45",
        "copper",
    )
    dcim.list_racks_in_room.return_value = (rack,)
    dcim.find_patch_panel.return_value = SimpleNamespace(
        rack_face=RackFace.REAR,
        u_position=20,
    )
    patch_location = resolver.resolve(tenant, _command("cable", "CBL-02"))
    assert patch_location.rack_face == "rear"
    assert patch_location.u_position == 20

    dcim.find_dcim_cable.return_value = None
    with pytest.raises(NotFoundError, match="cable"):
        resolver.resolve(tenant, _command("cable", "CBL-404"))

    dcim.find_dcim_cable.return_value = SimpleNamespace(
        a_endpoint=patch_endpoint,
        b_endpoint=DcimPortEndpoint.create("patch_panel", "PP-02", "P01"),
    )
    dcim.find_dcim_port.return_value = None
    with pytest.raises(ValidationError, match="endpoints"):
        resolver.resolve(tenant, _command("cable", "CBL-03"))


def test_safety_assessment_reports_power_graph_spof_and_flow_risks() -> None:
    graph = MagicMock()
    flows = MagicMock()
    dcim = MagicMock()
    graph.impact.return_value = SimpleNamespace(
        impacted_nodes=(object(), object()), direct_count=1, truncated=True
    )
    graph.analyze_spof.return_value = SimpleNamespace(total_spof_count=2)
    declaration = SimpleNamespace(
        source_selector=SimpleNamespace(kind=FlowSelectorKind.OBJECT, value="device/SRV-01"),
        destination_selector=SimpleNamespace(kind=FlowSelectorKind.CIDR, value="10.0.0.0/24"),
    )
    flows.list_declarations.return_value = SimpleNamespace(items=(declaration,), next_cursor="next")
    dcim.list_power_circuits_for_rack.return_value = (SimpleNamespace(side=PowerFeedSide.A),)
    service = FieldSafetyAssessmentService(graph, flows, dcim)
    location = FieldPhysicalLocation.create(
        site="PAR1",
        building="BAT-A",
        floor="F01",
        room="MMR1",
        row="B",
        column="12",
        rack="R42",
    )

    warnings = service.assess(TenantId.from_value("default"), "t" * 40, "device/SRV-01", location)
    assert {warning.code for warning in warnings} == {
        "POWER_REDUNDANCY_MISSING",
        "DEPENDENCY_IMPACT",
        "DEPENDENCY_ANALYSIS_TRUNCATED",
        "SPOF_PRESENT",
        "DECLARED_FLOWS",
        "FLOW_ANALYSIS_TRUNCATED",
    }

    dcim.list_power_circuits_for_rack.return_value = ()
    no_source = service.assess(TenantId.from_value("default"), "t" * 40, None, location)
    assert {warning.code for warning in no_source} == {
        "POWER_PATH_UNDOCUMENTED",
        "RSOT_LINK_MISSING",
    }

    no_rack = FieldPhysicalLocation.create(
        site="PAR1", building="BAT-A", room="MMR1", row="B", column="12"
    )
    graph.impact.return_value = SimpleNamespace(impacted_nodes=(), direct_count=0, truncated=False)
    graph.analyze_spof.return_value = SimpleNamespace(total_spof_count=0)
    flows.list_declarations.return_value = SimpleNamespace(items=(), next_cursor=None)
    assert service.assess(TenantId.from_value("default"), "t" * 40, "device/SRV-02", no_rack) == ()
