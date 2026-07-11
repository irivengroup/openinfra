from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.simulation_services import (
    CompareSimulationReportsCommand,
    CreateSimulationScenarioCommand,
    GetSimulationReportCommand,
    GetSimulationScenarioCommand,
    RunSimulationScenarioCommand,
    SimulationImpactEngine,
    _ImpactAggregate,
)
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import EntityId, NotFoundError, Severity, ValidationError
from openinfra.domain.simulation import (
    SimulationBlockingDependency,
    SimulationChangeKind,
    SimulationImpactFinding,
    SimulationMoveGroup,
)


class TestSimulationEdgeCoverage:
    @staticmethod
    def _application(tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "8" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "simulation-edge", ("admin",), token)
        )
        app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                "default",
                "pytest",
                token,
                "server:edge-001",
                "server",
                "Edge server",
                json.dumps(
                    {
                        "site": "par1",
                        "rack": "r01",
                        "power_watts": 500,
                        "cooling_kw": 0.8,
                        "monthly_cost": 400,
                    }
                ),
                ("production",),
                "pytest",
            )
        )
        return app, token

    @staticmethod
    def _create(app, token: str, key: str, changes: tuple[dict[str, object], ...]):
        return app.simulation_service.create_scenario(
            CreateSimulationScenarioCommand(
                "default",
                "pytest",
                token,
                f"Scenario {key}",
                "Scenario covering guarded simulation execution branches.",
                "qa.team",
                key,
                changes,
                site="par1",
                environment="production",
                criticality="high",
            )
        )

    def test_service_reports_missing_resources_and_persists_failed_runs(
        self, tmp_path: Path
    ) -> None:
        app, token = self._application(tmp_path)
        service = app.simulation_service
        with pytest.raises(NotFoundError, match="scenario"):
            service.get_scenario(
                GetSimulationScenarioCommand("default", token, EntityId.new().value)
            )
        with pytest.raises(NotFoundError, match="report"):
            service.get_report(GetSimulationReportCommand("default", token, EntityId.new().value))
        with pytest.raises(NotFoundError, match="one or both"):
            service.compare_reports(
                CompareSimulationReportsCommand(
                    "default", "pytest", token, EntityId.new().value, EntityId.new().value
                )
            )
        with pytest.raises(NotFoundError, match="scenario"):
            service.run_scenario(
                RunSimulationScenarioCommand("default", "pytest", token, EntityId.new().value)
            )
        with pytest.raises(ValidationError, match="JSON object"):
            service._change_from_payload("invalid")  # type: ignore[arg-type]

        invalid_cases = (
            (
                "edge-invalid-subnet",
                {
                    "kind": "subnet-change",
                    "target_key": "server:edge-001",
                    "after": {"prefix": "not-a-prefix"},
                },
                ValidationError,
                "invalid prefix",
            ),
            (
                "edge-existing-add",
                {
                    "kind": "equipment-add",
                    "target_key": "server:edge-001",
                    "after": {"site": "par2"},
                },
                ValidationError,
                "already exists",
            ),
            (
                "edge-missing-target",
                {"kind": "equipment-remove", "target_key": "server:missing-001"},
                NotFoundError,
                "does not exist",
            ),
            (
                "edge-before-mismatch",
                {
                    "kind": "equipment-move",
                    "target_key": "server:edge-001",
                    "before": {"site": "invalid"},
                    "after": {"site": "par2"},
                },
                ValidationError,
                "before state mismatch",
            ),
        )
        for key, change, error_type, message in invalid_cases:
            scenario = self._create(app, token, key, (change,))
            with pytest.raises(error_type, match=message):
                service.run_scenario(
                    RunSimulationScenarioCommand("default", "pytest", token, scenario.id.value)
                )
            restored = service.get_scenario(
                GetSimulationScenarioCommand("default", token, scenario.id.value)
            )
            assert restored.status.value == "failed"
            assert restored.failure_reason

    def test_network_capacity_and_planning_edge_paths(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        service = app.simulation_service
        new_asset = self._create(
            app,
            token,
            "edge-new-asset",
            (
                {
                    "kind": "equipment-add",
                    "target_key": "server:edge-002",
                    "after": {"site": "par2", "power_watts": 250},
                },
            ),
        )
        new_report = service.run_scenario(
            RunSimulationScenarioCommand("default", "pytest", token, new_asset.id.value)
        )
        assert new_report.risk_before == 17

        network = self._create(
            app,
            token,
            "edge-network-controls",
            (
                {
                    "kind": "subnet-change",
                    "target_key": "server:edge-001",
                    "after": {"prefix": "10.42.0.0/24"},
                },
                {
                    "kind": "vlan-change",
                    "target_key": "server:edge-001",
                    "after": {"vlan_id": 42},
                },
                {
                    "kind": "vrf-change",
                    "target_key": "server:edge-001",
                    "after": {"vrf_name": "production"},
                },
                {
                    "kind": "dns-change",
                    "target_key": "server:edge-001",
                    "after": {"dns_name": "edge.example.test"},
                },
                {
                    "kind": "firewall-change",
                    "target_key": "server:edge-001",
                    "after": {"action": "allow"},
                },
            ),
        )
        network_report = service.run_scenario(
            RunSimulationScenarioCommand("default", "pytest", token, network.id.value)
        )
        assert any(item.code == "SUBNET_RENUMBERING" for item in network_report.findings)
        assert sum(item.code == "NETWORK_CONTROL_REQUIRED" for item in network_report.findings) == 4

        outage = self._create(
            app,
            token,
            "edge-pdu-outage",
            ({"kind": "pdu-outage", "target_key": "server:edge-001"},),
        )
        outage_report = service.run_scenario(
            RunSimulationScenarioCommand("default", "pytest", token, outage.id.value)
        )
        assert {"PDU_OUTAGE", "THERMAL_REEVALUATION_REQUIRED"}.issubset(
            {item.code for item in outage_report.findings}
        )

        engine: SimulationImpactEngine = service._impact_engine
        first = SimulationMoveGroup.create("First", ("server:edge-001",), ("site:par1",), 20)
        second = SimulationMoveGroup.create("Second", ("application:erp",), ("site:par2",), 20)
        blockers = engine._build_blocking_dependencies(
            (first, second),
            [
                ("server:edge-001", "application:erp", "depends-on"),
                ("server:edge-001", "application:erp", "depends-on"),
            ],
        )
        assert len(blockers) == 1
        assert len(engine._build_waves((first, second), blockers, 80)) == 2
        same_group = SimulationMoveGroup.create(
            "Internal",
            ("server:edge-001", "application:erp"),
            ("same migration unit",),
            15,
        )
        internal_blocker = SimulationBlockingDependency.create(
            "server:edge-001",
            "application:erp",
            "depends-on",
            "Internal dependency remains inside the migration group.",
        )
        assert len(engine._build_waves((same_group,), (internal_blocker,), 90)) == 1
        cycle = (
            *blockers,
            SimulationBlockingDependency.create(
                "application:erp",
                "server:edge-001",
                "depends-on",
                "Reverse dependency creates a planning cycle.",
            ),
        )
        cyclic_waves = engine._build_waves((first, second), cycle, 80)
        assert cyclic_waves[0].readiness_score == 60
        assert engine._build_waves((), (), 100) == ()

        critical = SimulationImpactFinding.create(
            "dependency", "critical", "CRITICAL_IMPACT", "Critical impact detected."
        )
        warning = SimulationImpactFinding.create(
            "dependency",
            "warning",
            "WARNING_IMPACT",
            "Warning impact detected.",
            "server:edge-001",
        )
        readiness = engine._build_readiness(network, (critical, warning), True)
        assert "complete-impact-graph" in readiness[0].missing_evidence
        assert engine._impact_severity(50, SimulationChangeKind.EQUIPMENT_MOVE) is Severity.CRITICAL
        assert engine._impact_severity(10, SimulationChangeKind.EQUIPMENT_MOVE) is Severity.ERROR
        assert engine._affinity({}, None) == "unclassified"
        with pytest.raises(ValidationError, match="numeric attribute"):
            engine._numeric_value({"power_watts": "invalid"}, ("power_watts",))
        aggregate = _ImpactAggregate(set(), [], [], False, {"new": None}, set(), {})
        assert engine._baseline_risk(new_asset, aggregate) == 17
        assert service._preferred_report(new_report, new_report) is None
