from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import LocateEquipmentCommand
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineIpRangeCommand,
    RegisterIpAddressCommand,
)
from openinfra.domain.common import NotFoundError, ValidationError


class TestApplicationServices:
    def test_ipam_allocation_is_idempotent(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        command = AllocateIpCommand(
            tenant_id="default",
            actor="test",
            vrf="default",
            prefix="10.0.0.0/30",
            hostname="srv01",
            idempotency_key="req-1",
        )

        first = app.ipam_service.allocate(command)
        second = app.ipam_service.allocate(command)

        assert first.created is True
        assert second.created is False
        assert str(first.reservation.address) == str(second.reservation.address)
        assert str(first.reservation.address) == "10.0.0.1"

    def test_ipam_allocation_persists_to_json(self, tmp_path: Path) -> None:
        data = tmp_path / "state.json"
        app = ApplicationFactory().create_json_application(data)
        app.ipam_service.allocate(
            AllocateIpCommand("default", "test", "default", "10.1.0.0/29", "srv01", "req-1")
        )
        reloaded = ApplicationFactory().create_json_application(data)
        result = reloaded.ipam_service.allocate(
            AllocateIpCommand("default", "test", "default", "10.1.0.0/29", "srv02", "req-2")
        )

        assert str(result.reservation.address) == "10.1.0.2"

    def test_dcim_location_requires_existing_room(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        command = LocateEquipmentCommand(
            tenant_id="default",
            actor="test",
            asset_tag="SRV-001",
            equipment_name="Server 1",
            site="PAR1",
            building="BAT-A",
            room="MMR1",
            row="B",
            column="12",
            rack="R42",
            u_position=18,
            x=None,
            y=None,
            z=None,
        )

        with pytest.raises(NotFoundError):
            app.dcim_service.locate_equipment(command)

    def test_dcim_location_uses_row_column_and_rack_capacity(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        equipment = app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="test",
                asset_tag="SRV-001",
                equipment_name="Server 1",
                site="PAR1",
                building="BAT-A",
                room="MMR1",
                row="B",
                column="12",
                rack="R42",
                u_position=18,
                x=None,
                y=None,
                z=None,
            )
        )

        assert "row=B" in equipment.location.human_readable()
        assert "column=12" in equipment.location.human_readable()
        assert "rack=R42" in equipment.location.human_readable()

    def test_dcim_location_rejects_unknown_grid_cell(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")

        with pytest.raises(ValidationError):
            app.dcim_service.locate_equipment(
                LocateEquipmentCommand(
                    tenant_id="default",
                    actor="test",
                    asset_tag="SRV-002",
                    equipment_name="Server 2",
                    site="PAR1",
                    building="BAT-A",
                    room="MMR1",
                    row="Z",
                    column="12",
                    rack=None,
                    u_position=None,
                    x=None,
                    y=None,
                    z=None,
                )
            )


def test_ipam_allocation_honors_ranges_exclusions_and_registered_addresses(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    app.ipam_model_service.define_range(
        DefineIpRangeCommand(
            "default", "test", "default", "10.44.0.0/24", "10.44.0.10", "10.44.0.20"
        )
    )
    app.ipam_model_service.define_range(
        DefineIpRangeCommand(
            "default",
            "test",
            "default",
            "10.44.0.0/24",
            "10.44.0.10",
            "10.44.0.12",
            "exclusion",
        )
    )
    app.ipam_model_service.register_address(
        RegisterIpAddressCommand(
            "default", "test", "default", "10.44.0.0/24", "10.44.0.13", "preexisting"
        )
    )

    result = app.ipam_service.allocate(
        AllocateIpCommand("default", "test", "default", "10.44.0.0/24", "srv-ranged", "req-range")
    )

    assert str(result.reservation.address) == "10.44.0.14"


def test_ipam_allocation_is_safe_for_100_concurrent_json_requests(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    app = ApplicationFactory().create_json_application(tmp_path / "state.json")

    def reserve(index: int) -> str:
        result = app.ipam_service.allocate(
            AllocateIpCommand(
                "default",
                "pytest",
                "default",
                "10.45.0.0/24",
                f"srv-{index:03d}",
                f"req-{index:03d}",
            )
        )
        return str(result.reservation.address)

    with ThreadPoolExecutor(max_workers=20) as executor:
        addresses = tuple(executor.map(reserve, range(100)))

    assert len(addresses) == 100
    assert len(set(addresses)) == 100
    assert addresses[0] == "10.45.0.1"
    assert "10.45.0.100" in addresses
