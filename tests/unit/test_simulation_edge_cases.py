from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.simulation import (
    SimulationBlockingDependency,
    SimulationChange,
    SimulationImpactFinding,
    SimulationImpactReport,
    SimulationMigrationWave,
    SimulationMoveGroup,
    SimulationReadinessScore,
    SimulationScenario,
    SimulationScenarioComparison,
    SimulationValueValidator,
)
from openinfra.infrastructure.simulation_mapper import SimulationRecordMapper


class TestSimulationDomainEdgeCases:
    @staticmethod
    def _change() -> SimulationChange:
        return SimulationChange.create(
            "equipment-move",
            "server:edge-001",
            after={"site": "par2"},
        )

    @classmethod
    def _restore(cls, **overrides: object) -> SimulationScenario:
        now = datetime.now(UTC)
        values: dict[str, object] = {
            "id": EntityId.new(),
            "tenant_id": TenantId.from_value("default"),
            "name": "Simulation edge cases",
            "description": "Validate all guarded scenario restoration paths.",
            "owner": "qa.team",
            "site": "par1",
            "environment": "production",
            "criticality": "high",
            "idempotency_key": "edge-case-0001",
            "status": "draft",
            "changes": (cls._change(),),
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "failure_reason": None,
            "version": 1,
        }
        values.update(overrides)
        return SimulationScenario.restore(**values)  # type: ignore[arg-type]

    def test_value_and_change_guards_reject_invalid_payloads(self) -> None:
        with pytest.raises(ValidationError, match="unsupported"):
            SimulationChange.create("unknown", "server:edge-001")
        with pytest.raises(ValidationError, match="characters"):
            SimulationValueValidator.text("x", "label", 2, 3)
        with pytest.raises(ValidationError, match="safe characters"):
            SimulationValueValidator.optional_token("bad value!", "token")
        with pytest.raises(ValidationError, match="idempotency"):
            SimulationValueValidator.idempotency_key("short")
        with pytest.raises(ValidationError, match="JSON object"):
            SimulationValueValidator.json_object([], "payload")  # type: ignore[arg-type]
        with pytest.raises(ValidationError, match="64 KiB"):
            SimulationValueValidator.json_object({"payload": "x" * 70_000}, "payload")
        with pytest.raises(ValidationError, match="50 entries"):
            SimulationValueValidator.assumptions(tuple(f"entry-{index}" for index in range(51)))
        with pytest.raises(ValidationError, match="timezone-aware"):
            SimulationValueValidator.aware_datetime(datetime.now(), "timestamp")

        for kind in ("vlan-change", "vrf-change", "subnet-change", "dns-change", "firewall-change"):
            with pytest.raises(ValidationError, match="requires one of"):
                SimulationChange.create(kind, "server:edge-001")
        with pytest.raises(ValidationError, match="before state"):
            SimulationChange.create("equipment-add", "server:edge-002", before={"site": "par1"})

    def test_scenario_restore_and_state_machine_guards(self) -> None:
        now = datetime.now(UTC)
        with pytest.raises(ValidationError, match="1 to 100"):
            self._restore(changes=())
        duplicate = self._change()
        with pytest.raises(ValidationError, match="duplicate"):
            self._restore(changes=(duplicate, duplicate))
        with pytest.raises(ValidationError, match="updated_at"):
            self._restore(updated_at=now - timedelta(seconds=1), created_at=now)
        with pytest.raises(ValidationError, match="started_at"):
            self._restore(started_at=now - timedelta(seconds=1), created_at=now)
        with pytest.raises(ValidationError, match="completed_at"):
            self._restore(completed_at=now, started_at=None)
        with pytest.raises(ValidationError, match="version"):
            self._restore(version=0)

        scenario = self._restore()
        queued = scenario.queued()
        assert queued.status.value == "queued"
        with pytest.raises(ValidationError, match="queued"):
            queued.queued()
        running = queued.started()
        with pytest.raises(ValidationError, match="complete"):
            scenario.completed()
        with pytest.raises(ValidationError, match="fail"):
            scenario.failed("invalid state")
        completed = running.completed()
        with pytest.raises(ValidationError, match="cannot start"):
            completed.started()
        with pytest.raises(ValidationError, match="cannot be cancelled"):
            completed.cancelled()
        failed = running.failed("Dependency graph unavailable")
        assert failed.queued().failure_reason is None

    def test_report_entities_and_mapper_validate_edge_cases(self) -> None:
        tenant = TenantId.from_value("default")
        with pytest.raises(ValidationError, match="code"):
            SimulationImpactFinding.create("dependency", "warning", "!", "Invalid finding")
        with pytest.raises(ValidationError, match="severity"):
            SimulationImpactFinding.create(
                "dependency", "unknown", "VALID_CODE", "Invalid severity"
            )
        with pytest.raises(ValidationError, match="readiness"):
            SimulationReadinessScore.create("scenario", "scope", 101)
        with pytest.raises(ValidationError, match="at least one member"):
            SimulationMoveGroup.create("Empty group", (), (), 10)
        with pytest.raises(ValidationError, match="risk score"):
            SimulationMoveGroup.create("Invalid risk", ("server:edge-001",), (), -1)
        with pytest.raises(ValidationError, match="relation type"):
            SimulationBlockingDependency.create(
                "server:edge-001", "application:erp", "bad relation!", "Invalid relation"
            )

        group_id = EntityId.new()
        with pytest.raises(ValidationError, match="number"):
            SimulationMigrationWave.create(0, (group_id,), (), 50)
        with pytest.raises(ValidationError, match="at least one"):
            SimulationMigrationWave.create(1, (), (), 50)
        with pytest.raises(ValidationError, match="readiness score"):
            SimulationMigrationWave.create(1, (group_id,), (), 101)

        report_kwargs = {
            "tenant_id": tenant,
            "scenario_id": EntityId.new(),
            "scenario_version": 1,
            "input_sha256": "a" * 64,
            "impacted_keys": ("server:edge-001",),
            "findings": (),
            "baseline_summary": {},
            "projected_summary": {},
            "capacity_delta": {},
            "risk_before": 10,
            "risk_after": 20,
            "readiness_scores": (),
            "move_groups": (),
            "waves": (),
            "blocking_dependencies": (),
            "assumptions": (),
            "truncated": False,
            "engine_version": "1.0",
        }
        with pytest.raises(ValidationError, match="SHA-256"):
            SimulationImpactReport.create(**(report_kwargs | {"input_sha256": "bad"}))
        with pytest.raises(ValidationError, match="risk scores"):
            SimulationImpactReport.create(**(report_kwargs | {"risk_after": 101}))
        with pytest.raises(ValidationError, match="capacity delta key"):
            SimulationImpactReport.create(**(report_kwargs | {"capacity_delta": {"": 1.0}}))

        same_id = EntityId.new()
        with pytest.raises(ValidationError, match="distinct reports"):
            SimulationScenarioComparison.create(tenant, same_id, same_id, {}, None)

        dependency = SimulationBlockingDependency.create(
            "server:edge-001", "application:erp", "depends-on", "Dependency ordering"
        )
        assert SimulationRecordMapper.blocking_dependency(dependency.as_dict()) == dependency
        now = datetime.now(UTC)
        assert SimulationRecordMapper._datetime(now) is now
        assert SimulationRecordMapper._mapping(None) == {}
        assert SimulationRecordMapper._object_list(None) == []
        with pytest.raises(ValidationError, match="JSON object"):
            SimulationRecordMapper._mapping([])
        with pytest.raises(ValidationError, match="JSON array"):
            SimulationRecordMapper._object_list({})
        with pytest.raises(ValidationError, match="object array"):
            SimulationRecordMapper._mapping_list(["invalid"])
