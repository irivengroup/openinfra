from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.flow_matrix_services import UpsertFlowDeclarationCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.simulation_services import (
    CancelSimulationScenarioCommand,
    CompareSimulationReportsCommand,
    CreateSimulationScenarioCommand,
    GetSimulationReportCommand,
    GetSimulationScenarioCommand,
    ListSimulationComparisonsCommand,
    ListSimulationReportsCommand,
    ListSimulationScenariosCommand,
    RunSimulationScenarioCommand,
)
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.common import TenantId


class TestSimulationServices:
    @staticmethod
    def _application(tmp_path: Path):
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "9" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "simulation-admin", ("admin",), token)
        )
        for key, kind, name, attributes in (
            (
                "server:par-001",
                "server",
                "Serveur PAR-001",
                {
                    "site": "par1",
                    "rack": "r01",
                    "application": "erp",
                    "power_watts": 450,
                    "cooling_kw": 0.6,
                    "monthly_cost": 300,
                },
            ),
            (
                "application:erp",
                "application",
                "ERP",
                {"site": "par1", "criticality": "critical"},
            ),
        ):
            app.source_of_truth_service.upsert_object(
                UpsertSourceObjectCommand(
                    "default",
                    "pytest",
                    token,
                    key,
                    kind,
                    name,
                    json.dumps(attributes),
                    ("production",),
                    "pytest",
                )
            )
        app.source_of_truth_service.create_relation(
            CreateSourceRelationCommand(
                "default",
                "pytest",
                token,
                "depends-on",
                "application:erp",
                "server:par-001",
                "pytest",
            )
        )
        app.flow_matrix_service.upsert_declaration(
            UpsertFlowDeclarationCommand(
                "default",
                "pytest",
                token,
                "ERP-HTTPS",
                "object:application:erp",
                "object:server:par-001",
                "tcp",
                443,
                443,
                "allow",
                100,
                "network.team",
                "Flux ERP vers le serveur principal.",
            )
        )
        return app, token

    def test_scenario_run_is_non_mutating_audited_and_comparable(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        service = app.simulation_service
        original = app.source_of_truth_repository.find_object(
            TenantId.from_value("default"),
            "server:par-001",
        )
        assert original is not None
        scenario = service.create_scenario(
            CreateSimulationScenarioCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="Migration ERP vers PAR2",
                description="Comparer le déplacement du serveur ERP vers le site secondaire.",
                owner="architecture.team",
                idempotency_key="simulation-case-1001",
                site="par1",
                environment="production",
                criticality="high",
                changes=(
                    {
                        "kind": "equipment-move",
                        "target_key": "server:par-001",
                        "before": {"site": "par1", "rack": "r01"},
                        "after": {
                            "site": "par2",
                            "rack": "r20",
                            "power_watts": 400,
                            "monthly_cost": 250,
                        },
                        "assumptions": ["Target rack power and cooling are validated"],
                    },
                ),
            )
        )
        duplicate = service.create_scenario(
            CreateSimulationScenarioCommand(
                "default",
                "pytest",
                token,
                "Ignored duplicate",
                "Cette description est ignorée par idempotence du scénario.",
                "architecture.team",
                "simulation-case-1001",
                ({"kind": "equipment-outage", "target_key": "server:par-001"},),
            )
        )
        assert duplicate.id == scenario.id

        report = service.run_scenario(
            RunSimulationScenarioCommand("default", "pytest", token, scenario.id.value)
        )
        repeated = service.run_scenario(
            RunSimulationScenarioCommand("default", "pytest", token, scenario.id.value)
        )
        assert repeated.id == report.id
        assert "application:erp" in report.impacted_keys
        assert report.capacity_delta["power-watts"] == -50.0
        assert report.capacity_delta["monthly-cost"] == -50.0
        assert report.readiness_scores[0].score <= 100
        assert report.move_groups
        assert report.waves
        assert any(item.code == "DECLARED_FLOW_IMPACT" for item in report.findings)

        unchanged = app.source_of_truth_repository.find_object(
            TenantId.from_value("default"),
            "server:par-001",
        )
        assert unchanged is not None
        assert unchanged.version == original.version
        assert unchanged.attributes == original.attributes

        scenario_get = service.get_scenario(
            GetSimulationScenarioCommand("default", token, scenario.id.value)
        )
        report_get = service.get_report(
            GetSimulationReportCommand("default", token, report.id.value)
        )
        assert scenario_get.status.value == "completed"
        assert report_get.id == report.id
        assert service.list_scenarios(
            ListSimulationScenariosCommand("default", token, status="completed")
        ).items
        assert service.list_reports(
            ListSimulationReportsCommand("default", token, scenario_id=scenario.id.value)
        ).items

        outage = service.create_scenario(
            CreateSimulationScenarioCommand(
                "default",
                "pytest",
                token,
                "Coupure du serveur ERP",
                "Simuler la coupure complète du serveur ERP principal.",
                "architecture.team",
                "simulation-case-1002",
                ({"kind": "equipment-outage", "target_key": "server:par-001"},),
            )
        )
        outage_report = service.run_scenario(
            RunSimulationScenarioCommand("default", "pytest", token, outage.id.value)
        )
        comparison = service.compare_reports(
            CompareSimulationReportsCommand(
                "default", "pytest", token, report.id.value, outage_report.id.value
            )
        )
        assert comparison.preferred_report_id == report.id
        assert service.list_comparisons(
            ListSimulationComparisonsCommand("default", token)
        ).items == (comparison,)
        assert {
            "simulation.scenario.created",
            "simulation.started",
            "simulation.completed",
            "impact.report.generated",
            "simulation.comparison.created",
        }.issubset({item["name"] for item in app.store.data["simulation_event_outbox"].values()})

    def test_draft_scenario_can_be_cancelled(self, tmp_path: Path) -> None:
        app, token = self._application(tmp_path)
        scenario = app.simulation_service.create_scenario(
            CreateSimulationScenarioCommand(
                "default",
                "pytest",
                token,
                "Simulation à annuler",
                "Scénario de validation de l'annulation avant exécution.",
                "architecture.team",
                "simulation-case-2001",
                ({"kind": "equipment-outage", "target_key": "server:par-001"},),
            )
        )
        cancelled = app.simulation_service.cancel_scenario(
            CancelSimulationScenarioCommand("default", "pytest", token, scenario.id.value)
        )
        assert cancelled.status.value == "cancelled"
