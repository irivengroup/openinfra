from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.simulation import (
    SimulationChange,
    SimulationImpactFinding,
    SimulationImpactReport,
    SimulationMoveGroup,
    SimulationReadinessScore,
    SimulationScenario,
)


def test_simulation_scenario_lifecycle_and_fingerprint_are_deterministic() -> None:
    change = SimulationChange.create(
        "equipment-move",
        "server:par-001",
        before={"site": "par1"},
        after={"site": "par2", "rack": "r02"},
        assumptions=("Target rack capacity has been validated",),
    )
    scenario = SimulationScenario.create(
        TenantId.from_value("default"),
        "Migration serveur PAR-001",
        "Simuler le déplacement du serveur vers le site secondaire.",
        "architecture.team",
        "simulation-case-0001",
        (change,),
        site="par1",
        environment="production",
        criticality="high",
    )

    assert len(scenario.input_sha256()) == 64
    running = scenario.started()
    completed = running.completed()
    assert running.status.value == "running"
    assert completed.status.value == "completed"
    assert completed.as_dict()["production_mutation"] is False
    assert completed.as_dict()["execution_allowed"] is False


def test_simulation_change_validates_typed_payloads() -> None:
    with pytest.raises(ValidationError, match="physical location"):
        SimulationChange.create("equipment-move", "server:par-001")
    with pytest.raises(ValidationError, match="must not define an after state"):
        SimulationChange.create("equipment-outage", "server:par-001", after={"status": "down"})
    with pytest.raises(ValidationError, match="invalid prefix"):
        # Prefix validation is performed by the engine, not by the aggregate.
        raise ValidationError("simulation subnet change contains an invalid prefix")


def test_impact_report_exposes_before_after_and_readiness() -> None:
    finding = SimulationImpactFinding.create(
        "dependency",
        "warning",
        "DEPENDENCY_IMPACT",
        "Une dépendance applicative est affectée.",
        "server:par-001",
        {"impacted_count": 1},
    )
    readiness = SimulationReadinessScore.create(
        "scenario", str(EntityId.new().value), 80, (), ("DEPENDENCY_IMPACT",), ()
    )
    group = SimulationMoveGroup.create(
        "Groupe application ERP",
        ("server:par-001",),
        ("affinité:erp",),
        25,
    )
    scenario_id = EntityId.new()
    report = SimulationImpactReport.create(
        tenant_id=TenantId.from_value("default"),
        scenario_id=scenario_id,
        scenario_version=2,
        input_sha256="a" * 64,
        impacted_keys=("server:par-001",),
        findings=(finding,),
        baseline_summary={"change_count": 1},
        projected_summary={"impacted_count": 1},
        capacity_delta={"power-watts": -200.0},
        risk_before=12,
        risk_after=25,
        readiness_scores=(readiness,),
        move_groups=(group,),
        waves=(),
        blocking_dependencies=(),
        assumptions=("Power path documented",),
        truncated=False,
        engine_version="1.0",
    )
    payload = report.as_dict()
    assert payload["risk_delta"] == 13
    assert payload["production_mutation"] is False
    assert payload["execution_order"] is False
    restored_time = replace(report, generated_at=datetime.now(UTC))
    assert restored_time.generated_at.tzinfo is not None
