from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    DefineCoolingZoneCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    LocateEquipmentCommand,
    RackEnergyCoolingCapacityCommand,
    RecommendEquipmentPlacementCommand,
    ReserveEquipmentPowerCommand,
    UpdateRackCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ConflictError, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import (
    CoolingRole,
    CoolingZone,
    PowerCircuit,
    PowerDevice,
    PowerDeviceKind,
    PowerFeedSide,
    RackPlacementRequirements,
    RackPowerReservation,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestDcimEnergyCoolingServices:
    def _prepared_app(self, tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                tenant_id="default",
                actor="pytest",
                site_code="PWR1",
                site_name="Power DC",
                country="FR",
                region="IDF",
                city="Paris",
                building_code="BAT-P",
                building_name="Power Building",
                floor_code="F01",
                floor_name="Floor 1",
                floor_index=1,
                room_code="MMR-P",
                room_name="Power Room",
                rows=("A", "B"),
                columns=("01", "02"),
                zone_code="Z1",
                zone_name="Cold Aisle Z1",
                zone_rows=("A",),
                zone_columns=("01", "02"),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                tenant_id="default",
                actor="pytest",
                site="PWR1",
                building="BAT-P",
                floor="L01",
                room="MMR-P",
                zone="Z1",
                rack="R01",
                row="A",
                column="01",
                units=24,
                usable_faces=("front", "rear"),
                power_capacity_watts=10000,
            )
        )
        app.dcim_service.locate_equipment(
            LocateEquipmentCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="SRV-PWR-01",
                equipment_name="Powered Server",
                site="PWR1",
                building="BAT-P",
                floor="L01",
                room="MMR-P",
                zone="Z1",
                row="A",
                column="01",
                rack="R01",
                u_position=10,
                u_height=2,
                rack_face="front",
                x=1.0,
                y=2.0,
                z=0.0,
            )
        )
        return app

    def _configure_capacity(self, app) -> None:
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                tenant_id="default",
                actor="pytest",
                code="PDU-A",
                kind="pdu",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                rack="R01",
                side="A",
                capacity_watts=8000,
                derating_percent=80,
                input_source="UPS-A",
                output_voltage=230,
                label="Left power rail",
            )
        )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                tenant_id="default",
                actor="pytest",
                code="PDU-B",
                kind="ups",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                rack="R01",
                side="B",
                capacity_watts=8000,
                derating_percent=80,
                input_source="UPS-B",
                output_voltage=230,
                label="Right power rail",
            )
        )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                tenant_id="default",
                actor="pytest",
                circuit_id="CIR-A-01",
                source_device="PDU-A",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                rack="R01",
                side="A",
                capacity_watts=4000,
                breaker_rating_amps=16,
                redundancy_group="A",
            )
        )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                tenant_id="default",
                actor="pytest",
                circuit_id="CIR-B-01",
                source_device="PDU-B",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                rack="R01",
                side="B",
                capacity_watts=4000,
                breaker_rating_amps=16,
                redundancy_group="B",
            )
        )
        app.dcim_environment_service.define_cooling_zone(
            DefineCoolingZoneCommand(
                tenant_id="default",
                actor="pytest",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                zone="Z1",
                role="cold_aisle",
                cooling_capacity_watts=6000,
                supply_temperature_c=18,
                return_temperature_c=30,
                label="Cold aisle containment",
            )
        )

    def _configure_single_feed(
        self,
        app,
        *,
        rack: str = "R01",
        device: str = "PDU-SINGLE",
        circuit: str = "CIR-SINGLE",
        capacity_watts: int = 2500,
    ) -> None:
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                tenant_id="default",
                actor="pytest",
                code=device,
                kind="pdu",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                rack=rack,
                side="A",
                capacity_watts=5000,
                derating_percent=100,
            )
        )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                tenant_id="default",
                actor="pytest",
                circuit_id=circuit,
                source_device=device,
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                rack=rack,
                side="A",
                capacity_watts=capacity_watts,
                breaker_rating_amps=16,
            )
        )

    def test_power_cooling_capacity_roundtrip_and_report(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        self._configure_capacity(app)
        first = app.dcim_environment_service.reserve_equipment_power(
            ReserveEquipmentPowerCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="SRV-PWR-01",
                circuit_id="CIR-A-01",
                expected_watts=1200,
                label="PSU A",
            )
        )
        second = app.dcim_environment_service.reserve_equipment_power(
            ReserveEquipmentPowerCommand(
                tenant_id="default",
                actor="pytest",
                asset_tag="SRV-PWR-01",
                circuit_id="CIR-B-01",
                expected_watts=1200,
                label="PSU B",
            )
        )
        report = app.dcim_environment_service.rack_energy_cooling_capacity(
            RackEnergyCoolingCapacityCommand("default", "pytest", "PWR1", "BAT-P", "MMR-P", "R01")
        ).as_dict()
        reloaded = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
        reloaded_report = reloaded.dcim_environment_service.rack_energy_cooling_capacity(
            RackEnergyCoolingCapacityCommand("default", "pytest", "PWR1", "BAT-P", "MMR-P", "R01")
        ).as_dict()

        assert first["side"] == "A"
        assert second["side"] == "B"
        assert report["redundant_power_ready"] is True
        assert report["sides"]["A"]["remaining_watts"] == 2800
        assert report["sides"]["B"]["reserved_watts"] == 1200
        assert report["cooling"]["remaining_watts"] == 3600
        assert reloaded_report["reservations"][0]["asset_tag"] == "SRV-PWR-01"

    def test_equipment_placement_recommendation_is_constraint_aware_and_deterministic(
        self, tmp_path: Path
    ) -> None:
        app = self._prepared_app(tmp_path)
        self._configure_capacity(app)

        recommendation = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                tenant_id="default",
                actor="pytest",
                site="PWR1",
                building="BAT-P",
                room="MMR-P",
                u_height=4,
                required_power_watts=1000,
                required_cooling_watts=900,
                required_power_feeds=2,
                preferred_face="front",
                zone="Z1",
                limit=5,
            )
        ).as_dict()

        assert recommendation["type"] == "equipment_placement_recommendation"
        assert recommendation["evaluated_racks"] == 1
        assert recommendation["compatible_rack_count"] == 1
        assert recommendation["returned_candidate_count"] == 1
        candidate = recommendation["recommendations"][0]
        assert candidate["rack"] == "R01"
        assert candidate["rack_face"] == "front"
        assert candidate["start_u"] == 1
        assert candidate["end_u"] == 4
        assert [feed["side"] for feed in candidate["power_feeds"]] == ["A", "B"]
        assert candidate["cooling"]["remaining_watts_after_placement"] == 5100

        no_space = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 60, 100, zone="Z1"
            )
        ).as_dict()
        assert no_space["recommendations"] == []
        assert no_space["rejected_by_reason"] == {"insufficient_contiguous_u": 1}

        wrong_zone = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 100, zone="Z404"
            )
        ).as_dict()
        assert wrong_zone["rejected_by_reason"] == {"zone_mismatch": 1}

        with pytest.raises(NotFoundError):
            app.dcim_environment_service.recommend_equipment_placement(
                RecommendEquipmentPlacementCommand(
                    "default", "pytest", "PWR1", "BAT-P", "R404", 1, 100
                )
            )

    def test_placement_rejections_are_fail_closed_and_audited(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path / "capacity")
        self._configure_capacity(app)

        rack_power = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 11000
            )
        ).as_dict()
        assert rack_power["rejected_by_reason"] == {"insufficient_rack_power": 1}

        circuit_power = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 5000
            )
        ).as_dict()
        assert circuit_power["rejected_by_reason"] == {"insufficient_power_circuit": 1}

        app.dcim_environment_service.reserve_equipment_power(
            ReserveEquipmentPowerCommand(
                "default", "pytest", "SRV-PWR-01", "CIR-B-01", 500, "existing load"
            )
        )
        redundant = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                1,
                3800,
                required_power_feeds=2,
            )
        ).as_dict()
        assert redundant["rejected_by_reason"] == {"insufficient_redundant_power": 1}

        cooling = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                1,
                100,
                required_cooling_watts=5501,
            )
        ).as_dict()
        assert cooling["rejected_by_reason"] == {"insufficient_cooling_capacity": 1}
        assert any(
            event.action == "dcim.placement.recommended"
            for event in app.audit_repository.list_events()
        )

        missing_capacity_app = self._prepared_app(tmp_path / "missing-capacity")
        self._configure_single_feed(missing_capacity_app)
        missing_capacity = (
            missing_capacity_app.dcim_environment_service.recommend_equipment_placement(
                RecommendEquipmentPlacementCommand(
                    "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 100
                )
            ).as_dict()
        )
        assert missing_capacity["rejected_by_reason"] == {"missing_cooling_capacity": 1}

        retired_app = self._prepared_app(tmp_path / "retired")
        retired_app.dcim_rack_service.update_rack(
            UpdateRackCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", "R01", status="retired"
            )
        )
        retired = retired_app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 100
            )
        ).as_dict()
        assert retired["rejected_by_reason"] == {"rack_not_active": 1}

        no_zone_app = self._prepared_app(tmp_path / "no-zone")
        no_zone_app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R02",
                "A",
                "02",
                12,
                floor="L01",
                zone=None,
                power_capacity_watts=5000,
            )
        )
        self._configure_single_feed(no_zone_app, rack="R02", device="PDU-R02", circuit="CIR-R02")
        no_zone = no_zone_app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 100
            )
        ).as_dict()
        assert no_zone["rejected_by_reason"] == {
            "insufficient_power_circuit": 1,
            "missing_cooling_zone_assignment": 1,
        }

        face_app = self._prepared_app(tmp_path / "face")
        self._configure_capacity(face_app)
        face_app.dcim_rack_service.update_rack(
            UpdateRackCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R01",
                usable_faces=("front",),
            )
        )
        wrong_face = face_app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                1,
                100,
                preferred_face="rear",
            )
        ).as_dict()
        assert wrong_face["rejected_by_reason"] == {"insufficient_contiguous_u": 1}

    def test_placement_accounts_for_patch_panels_faces_limits_and_unbounded_racks(
        self, tmp_path: Path
    ) -> None:
        app = self._prepared_app(tmp_path)
        self._configure_capacity(app)
        app.dcim_rack_service.update_rack(
            UpdateRackCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R01",
                power_capacity_watts=14000,
            )
        )
        app.dcim_cabling_service.define_patch_panel(
            DefinePatchPanelCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R01",
                "PP-01",
                "front",
                1,
                4,
                8,
                "lc",
                "fiber",
            )
        )
        self._configure_single_feed(
            app,
            rack="R01",
            device="PDU-A0",
            circuit="CIR-A-00",
            capacity_watts=4000,
        )

        limited = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 4, 500, limit=1
            )
        ).as_dict()
        assert limited["compatible_rack_count"] == 1
        assert limited["returned_candidate_count"] == 1
        assert limited["recommendations"][0]["rack_face"] == "front"
        assert limited["recommendations"][0]["start_u"] == 5
        assert limited["recommendations"][0]["power_feeds"][0]["circuit_id"] == "CIR-A-00"

        rear = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                2,
                500,
                preferred_face="rear",
            )
        ).as_dict()
        assert rear["recommendations"][0]["start_u"] == 1
        assert rear["recommendations"][0]["rack_face"] == "rear"

        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R02",
                "A",
                "02",
                12,
                floor="L01",
                zone="Z1",
                usable_faces=("front",),
            )
        )
        self._configure_single_feed(app, rack="R02", device="PDU-R02", circuit="CIR-R02")
        all_candidates = app.dcim_environment_service.recommend_equipment_placement(
            RecommendEquipmentPlacementCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", 1, 100, limit=100
            )
        ).as_dict()
        r02 = next(item for item in all_candidates["recommendations"] if item["rack"] == "R02")
        assert r02["rack_remaining_watts_before_placement"] is None
        assert r02["rack_remaining_watts_after_placement"] is None
        assert all_candidates["compatible_rack_count"] == 2

        assert app.dcim_environment_service._contiguous_free_segments(6, {1, 3, 6}) == (
            (2, 1),
            (4, 2),
        )

    def test_power_and_cooling_conflicts_are_rejected(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_device(
                DefinePowerDeviceCommand(
                    "default", "pytest", "PDU-X", "pdu", "PWR1", "BAT-P", "BAD", 1000
                )
            )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                "default",
                "pytest",
                "PDU-A",
                "pdu",
                "PWR1",
                "BAT-P",
                "MMR-P",
                1500,
                rack="R01",
                side="A",
                derating_percent=80,
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-BAD",
                    "PDU-A",
                    "PWR1",
                    "BAT-P",
                    "MMR-P",
                    "R01",
                    "B",
                    500,
                    16,
                )
            )
        with pytest.raises(ConflictError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-HIGH",
                    "PDU-A",
                    "PWR1",
                    "BAT-P",
                    "MMR-P",
                    "R01",
                    "A",
                    1300,
                    16,
                )
            )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                "default",
                "pytest",
                "CIR-A-OK",
                "PDU-A",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R01",
                "A",
                1000,
                16,
            )
        )
        app.dcim_environment_service.define_cooling_zone(
            DefineCoolingZoneCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", "Z1", "neutral", 900, 19, 31
            )
        )
        with pytest.raises(ConflictError):
            app.dcim_environment_service.reserve_equipment_power(
                ReserveEquipmentPowerCommand("default", "pytest", "SRV-PWR-01", "CIR-A-OK", 950)
            )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.rack_energy_cooling_capacity(
                RackEnergyCoolingCapacityCommand(
                    "default", "pytest", "PWR1", "BAT-P", "MMR-P", "R404"
                )
            )

    def test_power_domain_validation_edges(self) -> None:
        tenant = TenantId.from_value("default")
        with pytest.raises(ValidationError):
            PowerFeedSide.from_value("C")
        with pytest.raises(ValidationError):
            PowerDeviceKind.from_value("battery")
        with pytest.raises(ValidationError):
            CoolingRole.from_value("ice")
        with pytest.raises(ValidationError):
            PowerDevice.create(tenant, "PD1", "pdu", "S", "B", "R", None, None, 0)
        with pytest.raises(ValidationError):
            PowerDevice.create(tenant, "PD1", "pdu", "S", "B", "R", None, None, 1, 0)
        with pytest.raises(ValidationError):
            PowerDevice.create(tenant, "PD1", "pdu", "S", "B", "R", None, None, 1, 80, "")
        with pytest.raises(ValidationError):
            PowerCircuit.create(tenant, "C1", "PD1", "S", "B", "R", "RK", "A", 0, 16)
        with pytest.raises(ValidationError):
            PowerCircuit.create(tenant, "C1", "PD1", "S", "B", "R", "RK", "A", 1, 0)
        with pytest.raises(ValidationError):
            CoolingZone.create(tenant, "S", "B", "R", "Z", "cold_aisle", 1, 30, 20)
        with pytest.raises(ValidationError):
            CoolingZone.create(tenant, "S", "B", "R", "Z", "cold_aisle", 0, 18, 30)
        with pytest.raises(ValidationError):
            RackPowerReservation.create(tenant, "A", "C", "A", "S", "B", "R", "RK", 0)
        requirements = RackPlacementRequirements.create(
            u_height=2, required_power_watts=500, preferred_face="rear"
        )
        assert requirements.required_cooling_watts == 500
        assert requirements.as_dict()["preferred_face"] == "rear"
        for kwargs in (
            {"u_height": 0, "required_power_watts": 1},
            {"u_height": 1, "required_power_watts": 0},
            {"u_height": 1, "required_power_watts": 1, "required_cooling_watts": 0},
            {"u_height": 1, "required_power_watts": 1, "required_power_feeds": 3},
            {"u_height": 1, "required_power_watts": 1, "preferred_face": "side"},
            {"u_height": 1, "required_power_watts": 1, "limit": 0},
        ):
            with pytest.raises(ValidationError):
                RackPlacementRequirements.create(**kwargs)

    def test_cli_energy_cooling_commands(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        cli = OpenInfraCLI()
        cli.run(
            [
                "dcim",
                "define-room",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site-code",
                "PWRCLI",
                "--site-name",
                "Power CLI",
                "--country",
                "FR",
                "--city",
                "Paris",
                "--building-code",
                "BAT",
                "--building-name",
                "Building",
                "--floor-index",
                "1",
                "--room-code",
                "MMR",
                "--room-name",
                "Main room",
                "--row",
                "A",
                "--column",
                "01",
                "--zone-code",
                "Z1",
                "--zone-name",
                "Zone 1",
                "--zone-row",
                "A",
                "--zone-column",
                "01",
            ]
        )
        capsys.readouterr()
        cli.run(
            [
                "dcim",
                "define-rack",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--site",
                "PWRCLI",
                "--building",
                "BAT",
                "--floor",
                "L01",
                "--room",
                "MMR",
                "--rack",
                "R01",
                "--row",
                "A",
                "--column",
                "01",
                "--zone",
                "Z1",
                "--units",
                "12",
                "--power-capacity-watts",
                "5000",
            ]
        )
        capsys.readouterr()
        cli.run(
            [
                "dcim",
                "locate",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--asset-tag",
                "SRV-CLI-PWR",
                "--equipment-name",
                "CLI powered",
                "--site",
                "PWRCLI",
                "--building",
                "BAT",
                "--floor",
                "L01",
                "--room",
                "MMR",
                "--zone",
                "Z1",
                "--row",
                "A",
                "--column",
                "01",
                "--rack",
                "R01",
                "--u-position",
                "5",
            ]
        )
        capsys.readouterr()
        assert (
            cli.run(
                [
                    "dcim",
                    "define-power-device",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--code",
                    "PDU-A",
                    "--kind",
                    "pdu",
                    "--site",
                    "PWRCLI",
                    "--building",
                    "BAT",
                    "--room",
                    "MMR",
                    "--rack",
                    "R01",
                    "--side",
                    "A",
                    "--capacity-watts",
                    "5000",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.run(
                [
                    "dcim",
                    "define-power-circuit",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--circuit-id",
                    "CIR-A",
                    "--source-device",
                    "PDU-A",
                    "--site",
                    "PWRCLI",
                    "--building",
                    "BAT",
                    "--room",
                    "MMR",
                    "--rack",
                    "R01",
                    "--side",
                    "A",
                    "--capacity-watts",
                    "2500",
                    "--breaker-rating-amps",
                    "16",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.run(
                [
                    "dcim",
                    "define-cooling-zone",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "PWRCLI",
                    "--building",
                    "BAT",
                    "--room",
                    "MMR",
                    "--zone",
                    "Z1",
                    "--role",
                    "cold_aisle",
                    "--cooling-capacity-watts",
                    "3000",
                    "--supply-temperature-c",
                    "18",
                    "--return-temperature-c",
                    "30",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.run(
                [
                    "dcim",
                    "reserve-power",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--asset-tag",
                    "SRV-CLI-PWR",
                    "--circuit-id",
                    "CIR-A",
                    "--expected-watts",
                    "700",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            cli.run(
                [
                    "dcim",
                    "energy-cooling-capacity",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "PWRCLI",
                    "--building",
                    "BAT",
                    "--room",
                    "MMR",
                    "--rack",
                    "R01",
                ]
            )
            == 0
        )
        report = json.loads(capsys.readouterr().out)
        assert report["sides"]["A"]["reserved_watts"] == 700
        assert report["cooling"]["remaining_watts"] == 2300
        assert (
            cli.run(
                [
                    "dcim",
                    "recommend-placement",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--site",
                    "PWRCLI",
                    "--building",
                    "BAT",
                    "--room",
                    "MMR",
                    "--u-height",
                    "2",
                    "--required-power-watts",
                    "500",
                    "--preferred-face",
                    "front",
                ]
            )
            == 0
        )
        placement = json.loads(capsys.readouterr().out)
        assert placement["recommendations"][0]["rack"] == "R01"
        assert placement["recommendations"][0]["start_u"] == 1

    def test_http_energy_cooling_endpoints(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            self._post_json(
                base_url + "/api/v1/dcim/power-devices",
                {
                    "tenant_id": "default",
                    "code": "PDU-A",
                    "kind": "pdu",
                    "site": "PWR1",
                    "building": "BAT-P",
                    "room": "MMR-P",
                    "rack": "R01",
                    "side": "A",
                    "capacity_watts": 5000,
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/power-circuits",
                {
                    "tenant_id": "default",
                    "circuit_id": "CIR-A",
                    "source_device": "PDU-A",
                    "site": "PWR1",
                    "building": "BAT-P",
                    "room": "MMR-P",
                    "rack": "R01",
                    "side": "A",
                    "capacity_watts": 2000,
                    "breaker_rating_amps": 16,
                },
            )
            self._post_json(
                base_url + "/api/v1/dcim/cooling-zones",
                {
                    "tenant_id": "default",
                    "site": "PWR1",
                    "building": "BAT-P",
                    "room": "MMR-P",
                    "zone": "Z1",
                    "role": "cold_aisle",
                    "cooling_capacity_watts": 3000,
                    "supply_temperature_c": 18,
                    "return_temperature_c": 30,
                },
            )
            reservation = self._post_json(
                base_url + "/api/v1/dcim/power-reservations",
                {
                    "tenant_id": "default",
                    "asset_tag": "SRV-PWR-01",
                    "circuit_id": "CIR-A",
                    "expected_watts": 600,
                },
            )
            report = self._get_json(
                base_url + "/api/v1/dcim/energy-cooling-capacity?tenant_id=default"
                "&site=PWR1&building=BAT-P&room=MMR-P&rack=R01"
            )
            assert reservation["side"] == "A"
            assert report["sides"]["A"]["reserved_watts"] == 600
            assert report["cooling"]["status"] == "ok"
            placement = self._get_json(
                base_url + "/api/v1/dcim/placement-recommendations?tenant_id=default"
                "&site=PWR1&building=BAT-P&room=MMR-P&u_height=2"
                "&required_power_watts=500&preferred_face=front"
            )
            assert placement["compatible_rack_count"] == 1
            assert placement["recommendations"][0]["rack"] == "R01"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_additional_energy_error_branches_and_auth_api(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_device(
                DefinePowerDeviceCommand(
                    "default",
                    "pytest",
                    "PDU-R404",
                    "pdu",
                    "PWR1",
                    "BAT-P",
                    "MMR-P",
                    1000,
                    rack="R404",
                    side="A",
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-MISS-SRC",
                    "PDU404",
                    "PWR1",
                    "BAT-P",
                    "MMR-P",
                    "R01",
                    "A",
                    100,
                    16,
                )
            )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                "default",
                "pytest",
                "PDU-A",
                "pdu",
                "PWR1",
                "BAT-P",
                "MMR-P",
                20000,
                rack="R01",
                side="A",
                derating_percent=100,
            )
        )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                "default",
                "pytest",
                "PDU-ROOMLESS",
                "pdu",
                "PWR1",
                "BAT-P",
                "MMR-P",
                2000,
                side=None,
                derating_percent=100,
            )
        )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-MISS-RACK",
                    "PDU-A",
                    "PWR1",
                    "BAT-P",
                    "MMR-P",
                    "R404",
                    "A",
                    100,
                    16,
                )
            )
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                "default",
                "pytest",
                "OTHER",
                "Other",
                "FR",
                "IDF",
                "Paris",
                "BAT-P",
                "Other Building",
                "F01",
                "Floor 1",
                1,
                "MMR-P",
                "Other Room",
                ("A",),
                ("01",),
                "Z1",
                "Zone",
                ("A",),
                ("01",),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default",
                "pytest",
                "OTHER",
                "BAT-P",
                "MMR-P",
                "R01",
                "A",
                "01",
                12,
                floor="L01",
                zone="Z1",
                power_capacity_watts=12000,
            )
        )
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                "default",
                "pytest",
                "PWR1",
                "Power DC",
                "FR",
                "IDF",
                "Paris",
                "BAT-P",
                "Power Building",
                "F02",
                "Floor 2",
                2,
                "MMR-X",
                "Other Room",
                ("A",),
                ("01",),
                "Z1",
                "Zone",
                ("A",),
                ("01",),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-X",
                "R01",
                "A",
                "01",
                12,
                floor="L02",
                zone="Z1",
                power_capacity_watts=12000,
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-SITE",
                    "PDU-A",
                    "OTHER",
                    "BAT-P",
                    "MMR-P",
                    "R01",
                    "A",
                    100,
                    16,
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-ROOM",
                    "PDU-A",
                    "PWR1",
                    "BAT-P",
                    "MMR-X",
                    "R01",
                    "A",
                    100,
                    16,
                )
            )
        with pytest.raises(ConflictError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default",
                    "pytest",
                    "CIR-RACK-CAP",
                    "PDU-A",
                    "PWR1",
                    "BAT-P",
                    "MMR-P",
                    "R01",
                    "A",
                    10001,
                    16,
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_cooling_zone(
                DefineCoolingZoneCommand(
                    "default", "pytest", "PWR1", "BAT-P", "MMR-P", "Z404", "neutral", 1000, 18, 30
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.reserve_equipment_power(
                ReserveEquipmentPowerCommand("default", "pytest", "NO-SUCH-ASSET", "CIR-A", 1)
            )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.reserve_equipment_power(
                ReserveEquipmentPowerCommand("default", "pytest", "SRV-PWR-01", "CIR404", 1)
            )

        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default",
                "pytest",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R02",
                "A",
                "02",
                12,
                floor="L01",
                zone="Z1",
                power_capacity_watts=12000,
            )
        )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                "default",
                "pytest",
                "CIR-R02",
                "PDU-ROOMLESS",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R02",
                "A",
                500,
                16,
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.reserve_equipment_power(
                ReserveEquipmentPowerCommand("default", "pytest", "SRV-PWR-01", "CIR-R02", 1)
            )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                "default",
                "pytest",
                "CIR-A",
                "PDU-A",
                "PWR1",
                "BAT-P",
                "MMR-P",
                "R01",
                "A",
                1000,
                16,
            )
        )
        with pytest.raises(ConflictError):
            app.dcim_environment_service.reserve_equipment_power(
                ReserveEquipmentPowerCommand("default", "pytest", "SRV-PWR-01", "CIR-A", 1001)
            )

        token = "f" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="dcim-admin",
                roles=("admin",),
                token=token,
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            self._post_json(
                base_url + "/api/v1/dcim/power-devices",
                {
                    "tenant_id": "default",
                    "code": "PDU-B",
                    "kind": "pdu",
                    "site": "PWR1",
                    "building": "BAT-P",
                    "room": "MMR-P",
                    "rack": "R01",
                    "side": "B",
                    "capacity_watts": 2000,
                },
                token=token,
            )
            self._post_json(
                base_url + "/api/v1/dcim/power-circuits",
                {
                    "tenant_id": "default",
                    "circuit_id": "CIR-B",
                    "source_device": "PDU-B",
                    "site": "PWR1",
                    "building": "BAT-P",
                    "room": "MMR-P",
                    "rack": "R01",
                    "side": "B",
                    "capacity_watts": 1000,
                    "breaker_rating_amps": 16,
                },
                token=token,
            )
            self._post_json(
                base_url + "/api/v1/dcim/cooling-zones",
                {
                    "tenant_id": "default",
                    "site": "PWR1",
                    "building": "BAT-P",
                    "room": "MMR-P",
                    "zone": "Z1",
                    "role": "hot_aisle",
                    "cooling_capacity_watts": 5000,
                    "supply_temperature_c": 20,
                    "return_temperature_c": 35,
                },
                token=token,
            )
            self._post_json(
                base_url + "/api/v1/dcim/power-reservations",
                {
                    "tenant_id": "default",
                    "asset_tag": "SRV-PWR-01",
                    "circuit_id": "CIR-B",
                    "expected_watts": 300,
                },
                token=token,
            )
            with pytest.raises(urllib.error.HTTPError) as unauthenticated:
                self._get_json(
                    base_url
                    + "/api/v1/dcim/placement-recommendations?tenant_id=default"
                    + "&site=PWR1&building=BAT-P&room=MMR-P&u_height=1"
                    + "&required_power_watts=100"
                )
            assert unauthenticated.value.code == 401
            with pytest.raises(urllib.error.HTTPError) as invalid_request:
                self._get_json(
                    base_url + "/api/v1/dcim/placement-recommendations?tenant_id=default",
                    token=token,
                )
            assert invalid_request.value.code == 400
            authorized = self._get_json(
                base_url
                + "/api/v1/dcim/placement-recommendations?tenant_id=default"
                + "&site=PWR1&building=BAT-P&room=MMR-P&u_height=1"
                + "&required_power_watts=500",
                token=token,
            )
            assert authorized["recommendations"][0]["rack"] == "R01"

            for path in (
                "/api/v1/dcim/power-devices",
                "/api/v1/dcim/power-circuits",
                "/api/v1/dcim/cooling-zones",
                "/api/v1/dcim/power-reservations",
            ):
                try:
                    self._post_json(base_url + path, {"tenant_id": "default"}, token=token)
                except Exception as exc:
                    assert getattr(exc, "code", None) == 400
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_domain_report_and_validation_edges_for_power_capacity(self) -> None:
        tenant = TenantId.from_value("default")
        reservation = RackPowerReservation.create(
            tenant, "SRV-1", "CIR-A", "A", "S", "B", "R", "RK", 10, "load"
        )
        circuit = PowerCircuit.create(tenant, "CIR-B", "PD", "S", "B", "R", "RK", "B", 100, 16)
        assert circuit.remaining_watts((reservation,)) == 100
        with pytest.raises(ValidationError):
            PowerDevice.create(tenant, "PD1", "pdu", "S", "B", "R", None, None, 1, 80, "src", 47)
        with pytest.raises(ValidationError):
            PowerDevice.create(
                tenant, "PD1", "pdu", "S", "B", "R", None, None, 1, 80, "src", 230, "x" * 161
            )
        with pytest.raises(ValidationError):
            PowerCircuit.create(tenant, "C1", "PD1", "S", "B", "R", "RK", "A", 1, 16, "")
        with pytest.raises(ValidationError):
            PowerCircuit.create(
                tenant, "C1", "PD1", "S", "B", "R", "RK", "A", 1, 16, "g", "x" * 161
            )
        with pytest.raises(ValidationError):
            CoolingZone.create(tenant, "S", "B", "R", "Z", "cold_aisle", 1, 4, 30)
        with pytest.raises(ValidationError):
            CoolingZone.create(tenant, "S", "B", "R", "Z", "cold_aisle", 1, 18, 61)
        with pytest.raises(ValidationError):
            CoolingZone.create(tenant, "S", "B", "R", "Z", "cold_aisle", 1, 18, 30, "x" * 161)
        with pytest.raises(ValidationError):
            RackPowerReservation.create(tenant, "A", "C", "A", "S", "B", "R", "RK", 1, "x" * 161)

    def _get_json(self, url: str, token: str | None = None) -> dict[str, object]:
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(
        self,
        url: str,
        payload: dict[str, object],
        token: str | None = None,
    ) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
