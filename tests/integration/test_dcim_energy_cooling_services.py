from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import (
    DefineCoolingZoneCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    LocateEquipmentCommand,
    RackEnergyCoolingCapacityCommand,
    ReserveEquipmentPowerCommand,
)
from openinfra.domain.common import ConflictError, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import (
    CoolingRole,
    CoolingZone,
    PowerCircuit,
    PowerDevice,
    PowerDeviceKind,
    PowerFeedSide,
    RackPowerReservation,
)
from openinfra.application.security_services import BootstrapTokenCommand
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
                floor="F01",
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
                floor="F01",
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
                "default", "pytest", "PDU-A", "pdu", "PWR1", "BAT-P", "MMR-P", 1500,
                rack="R01", side="A", derating_percent=80,
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-BAD", "PDU-A", "PWR1", "BAT-P", "MMR-P",
                    "R01", "B", 500, 16,
                )
            )
        with pytest.raises(ConflictError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-HIGH", "PDU-A", "PWR1", "BAT-P", "MMR-P",
                    "R01", "A", 1300, 16,
                )
            )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                "default", "pytest", "CIR-A-OK", "PDU-A", "PWR1", "BAT-P", "MMR-P",
                "R01", "A", 1000, 16,
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
                RackEnergyCoolingCapacityCommand("default", "pytest", "PWR1", "BAT-P", "MMR-P", "R404")
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

    def test_cli_energy_cooling_commands(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        cli = OpenInfraCLI()
        cli.run([
            "dcim", "define-room", "--data", str(data), "--tenant", "default",
            "--site-code", "PWRCLI", "--site-name", "Power CLI", "--country", "FR",
            "--city", "Paris", "--building-code", "BAT", "--building-name", "Building",
            "--floor-code", "F01", "--floor-name", "Floor 1", "--floor-index", "1",
            "--room-code", "MMR", "--room-name", "Main room", "--row", "A",
            "--column", "01", "--zone-code", "Z1", "--zone-name", "Zone 1",
            "--zone-row", "A", "--zone-column", "01",
        ])
        capsys.readouterr()
        cli.run([
            "dcim", "define-rack", "--data", str(data), "--tenant", "default",
            "--site", "PWRCLI", "--building", "BAT", "--floor", "F01", "--room", "MMR",
            "--rack", "R01", "--row", "A", "--column", "01", "--zone", "Z1",
            "--units", "12", "--power-capacity-watts", "5000",
        ])
        capsys.readouterr()
        cli.run([
            "dcim", "locate", "--data", str(data), "--tenant", "default",
            "--asset-tag", "SRV-CLI-PWR", "--equipment-name", "CLI powered",
            "--site", "PWRCLI", "--building", "BAT", "--floor", "F01", "--room", "MMR",
            "--zone", "Z1", "--row", "A", "--column", "01", "--rack", "R01", "--u-position", "5",
        ])
        capsys.readouterr()
        assert cli.run([
            "dcim", "define-power-device", "--data", str(data), "--tenant", "default",
            "--code", "PDU-A", "--kind", "pdu", "--site", "PWRCLI", "--building", "BAT",
            "--room", "MMR", "--rack", "R01", "--side", "A", "--capacity-watts", "5000",
        ]) == 0
        capsys.readouterr()
        assert cli.run([
            "dcim", "define-power-circuit", "--data", str(data), "--tenant", "default",
            "--circuit-id", "CIR-A", "--source-device", "PDU-A", "--site", "PWRCLI",
            "--building", "BAT", "--room", "MMR", "--rack", "R01", "--side", "A",
            "--capacity-watts", "2500", "--breaker-rating-amps", "16",
        ]) == 0
        capsys.readouterr()
        assert cli.run([
            "dcim", "define-cooling-zone", "--data", str(data), "--tenant", "default",
            "--site", "PWRCLI", "--building", "BAT", "--room", "MMR", "--zone", "Z1",
            "--role", "cold_aisle", "--cooling-capacity-watts", "3000",
            "--supply-temperature-c", "18", "--return-temperature-c", "30",
        ]) == 0
        capsys.readouterr()
        assert cli.run([
            "dcim", "reserve-power", "--data", str(data), "--tenant", "default",
            "--asset-tag", "SRV-CLI-PWR", "--circuit-id", "CIR-A", "--expected-watts", "700",
        ]) == 0
        capsys.readouterr()
        assert cli.run([
            "dcim", "energy-cooling-capacity", "--data", str(data), "--tenant", "default",
            "--site", "PWRCLI", "--building", "BAT", "--room", "MMR", "--rack", "R01",
        ]) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["sides"]["A"]["reserved_watts"] == 700
        assert report["cooling"]["remaining_watts"] == 2300

    def test_http_energy_cooling_endpoints(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            self._post_json(base_url + "/api/v1/dcim/power-devices", {
                "tenant_id": "default", "code": "PDU-A", "kind": "pdu", "site": "PWR1",
                "building": "BAT-P", "room": "MMR-P", "rack": "R01", "side": "A",
                "capacity_watts": 5000,
            })
            self._post_json(base_url + "/api/v1/dcim/power-circuits", {
                "tenant_id": "default", "circuit_id": "CIR-A", "source_device": "PDU-A",
                "site": "PWR1", "building": "BAT-P", "room": "MMR-P", "rack": "R01",
                "side": "A", "capacity_watts": 2000, "breaker_rating_amps": 16,
            })
            self._post_json(base_url + "/api/v1/dcim/cooling-zones", {
                "tenant_id": "default", "site": "PWR1", "building": "BAT-P", "room": "MMR-P",
                "zone": "Z1", "role": "cold_aisle", "cooling_capacity_watts": 3000,
                "supply_temperature_c": 18, "return_temperature_c": 30,
            })
            reservation = self._post_json(base_url + "/api/v1/dcim/power-reservations", {
                "tenant_id": "default", "asset_tag": "SRV-PWR-01", "circuit_id": "CIR-A",
                "expected_watts": 600,
            })
            report = self._get_json(
                base_url + "/api/v1/dcim/energy-cooling-capacity?tenant_id=default"
                "&site=PWR1&building=BAT-P&room=MMR-P&rack=R01"
            )
            assert reservation["side"] == "A"
            assert report["sides"]["A"]["reserved_watts"] == 600
            assert report["cooling"]["status"] == "ok"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


    def test_additional_energy_error_branches_and_auth_api(self, tmp_path: Path) -> None:
        app = self._prepared_app(tmp_path)
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_device(
                DefinePowerDeviceCommand(
                    "default", "pytest", "PDU-R404", "pdu", "PWR1", "BAT-P", "MMR-P", 1000,
                    rack="R404", side="A",
                )
            )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-MISS-SRC", "PDU404", "PWR1", "BAT-P", "MMR-P",
                    "R01", "A", 100, 16,
                )
            )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                "default", "pytest", "PDU-A", "pdu", "PWR1", "BAT-P", "MMR-P", 20000,
                rack="R01", side="A", derating_percent=100,
            )
        )
        app.dcim_environment_service.define_power_device(
            DefinePowerDeviceCommand(
                "default", "pytest", "PDU-ROOMLESS", "pdu", "PWR1", "BAT-P", "MMR-P", 2000,
                side=None, derating_percent=100,
            )
        )
        with pytest.raises(NotFoundError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-MISS-RACK", "PDU-A", "PWR1", "BAT-P", "MMR-P",
                    "R404", "A", 100, 16,
                )
            )
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                "default", "pytest", "OTHER", "Other", "FR", "IDF", "Paris",
                "BAT-P", "Other Building", "F01", "Floor 1", 1, "MMR-P", "Other Room",
                ("A",), ("01",), "Z1", "Zone", ("A",), ("01",),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default", "pytest", "OTHER", "BAT-P", "MMR-P", "R01", "A", "01", 12,
                floor="F01", zone="Z1", power_capacity_watts=12000,
            )
        )
        app.dcim_topology_service.define_room(
            DefinePhysicalRoomCommand(
                "default", "pytest", "PWR1", "Power DC", "FR", "IDF", "Paris",
                "BAT-P", "Power Building", "F02", "Floor 2", 2, "MMR-X", "Other Room",
                ("A",), ("01",), "Z1", "Zone", ("A",), ("01",),
            )
        )
        app.dcim_rack_service.define_rack(
            DefineRackCommand(
                "default", "pytest", "PWR1", "BAT-P", "MMR-X", "R01", "A", "01", 12,
                floor="F02", zone="Z1", power_capacity_watts=12000,
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-SITE", "PDU-A", "OTHER", "BAT-P", "MMR-P",
                    "R01", "A", 100, 16,
                )
            )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-ROOM", "PDU-A", "PWR1", "BAT-P", "MMR-X",
                    "R01", "A", 100, 16,
                )
            )
        with pytest.raises(ConflictError):
            app.dcim_environment_service.define_power_circuit(
                DefinePowerCircuitCommand(
                    "default", "pytest", "CIR-RACK-CAP", "PDU-A", "PWR1", "BAT-P", "MMR-P",
                    "R01", "A", 10001, 16,
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
                "default", "pytest", "PWR1", "BAT-P", "MMR-P", "R02", "A", "02", 12,
                floor="F01", zone="Z1", power_capacity_watts=12000,
            )
        )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                "default", "pytest", "CIR-R02", "PDU-ROOMLESS", "PWR1", "BAT-P", "MMR-P",
                "R02", "A", 500, 16,
            )
        )
        with pytest.raises(ValidationError):
            app.dcim_environment_service.reserve_equipment_power(
                ReserveEquipmentPowerCommand("default", "pytest", "SRV-PWR-01", "CIR-R02", 1)
            )
        app.dcim_environment_service.define_power_circuit(
            DefinePowerCircuitCommand(
                "default", "pytest", "CIR-A", "PDU-A", "PWR1", "BAT-P", "MMR-P", "R01", "A", 1000, 16
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
            self._post_json(base_url + "/api/v1/dcim/power-devices", {
                "tenant_id": "default", "code": "PDU-B", "kind": "pdu", "site": "PWR1",
                "building": "BAT-P", "room": "MMR-P", "rack": "R01", "side": "B",
                "capacity_watts": 2000,
            }, token=token)
            self._post_json(base_url + "/api/v1/dcim/power-circuits", {
                "tenant_id": "default", "circuit_id": "CIR-B", "source_device": "PDU-B",
                "site": "PWR1", "building": "BAT-P", "room": "MMR-P", "rack": "R01",
                "side": "B", "capacity_watts": 1000, "breaker_rating_amps": 16,
            }, token=token)
            self._post_json(base_url + "/api/v1/dcim/cooling-zones", {
                "tenant_id": "default", "site": "PWR1", "building": "BAT-P", "room": "MMR-P",
                "zone": "Z1", "role": "hot_aisle", "cooling_capacity_watts": 5000,
                "supply_temperature_c": 20, "return_temperature_c": 35,
            }, token=token)
            self._post_json(base_url + "/api/v1/dcim/power-reservations", {
                "tenant_id": "default", "asset_tag": "SRV-PWR-01", "circuit_id": "CIR-B",
                "expected_watts": 300,
            }, token=token)
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
            PowerDevice.create(tenant, "PD1", "pdu", "S", "B", "R", None, None, 1, 80, "src", 230, "x" * 161)
        with pytest.raises(ValidationError):
            PowerCircuit.create(tenant, "C1", "PD1", "S", "B", "R", "RK", "A", 1, 16, "")
        with pytest.raises(ValidationError):
            PowerCircuit.create(tenant, "C1", "PD1", "S", "B", "R", "RK", "A", 1, 16, "g", "x" * 161)
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
