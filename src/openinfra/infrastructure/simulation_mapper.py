from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

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
)


class SimulationRecordMapper:
    @classmethod
    def scenario(cls, value: Mapping[str, Any]) -> SimulationScenario:
        return SimulationScenario.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            name=str(value["name"]),
            description=str(value["description"]),
            owner=str(value["owner"]),
            site=cls._optional_text(value.get("site")),
            environment=cls._optional_text(value.get("environment")),
            criticality=cls._optional_text(value.get("criticality")),
            idempotency_key=str(value["idempotency_key"]),
            status=str(value["status"]),
            changes=tuple(cls.change(item) for item in cls._mapping_list(value.get("changes"))),
            created_at=cls._datetime(value["created_at"]),
            updated_at=cls._datetime(value["updated_at"]),
            started_at=cls._optional_datetime(value.get("started_at")),
            completed_at=cls._optional_datetime(value.get("completed_at")),
            failure_reason=cls._optional_text(value.get("failure_reason")),
            version=int(value["version"]),
        )

    @classmethod
    def change(cls, value: Mapping[str, Any]) -> SimulationChange:
        return SimulationChange.restore(
            id=EntityId.from_value(str(value["id"])),
            kind=str(value["kind"]),
            target_key=str(value["target_key"]),
            before=cls._mapping(value.get("before")),
            after=cls._mapping(value.get("after")),
            assumptions=tuple(str(item) for item in cls._object_list(value.get("assumptions"))),
        )

    @classmethod
    def report(cls, value: Mapping[str, Any]) -> SimulationImpactReport:
        report = SimulationImpactReport.create(
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            scenario_id=EntityId.from_value(str(value["scenario_id"])),
            scenario_version=int(value["scenario_version"]),
            input_sha256=str(value["input_sha256"]),
            impacted_keys=tuple(str(item) for item in cls._object_list(value.get("impacted_keys"))),
            findings=tuple(cls.finding(item) for item in cls._mapping_list(value.get("findings"))),
            baseline_summary=cls._mapping(value.get("baseline_summary")),
            projected_summary=cls._mapping(value.get("projected_summary")),
            capacity_delta={
                str(key): float(item)
                for key, item in cls._mapping(value.get("capacity_delta")).items()
            },
            risk_before=int(value["risk_before"]),
            risk_after=int(value["risk_after"]),
            readiness_scores=tuple(
                cls.readiness(item) for item in cls._mapping_list(value.get("readiness_scores"))
            ),
            move_groups=tuple(
                cls.move_group(item) for item in cls._mapping_list(value.get("move_groups"))
            ),
            waves=tuple(cls.wave(item) for item in cls._mapping_list(value.get("waves"))),
            blocking_dependencies=tuple(
                cls.blocking_dependency(item)
                for item in cls._mapping_list(value.get("blocking_dependencies"))
            ),
            assumptions=tuple(str(item) for item in cls._object_list(value.get("assumptions"))),
            truncated=bool(value.get("truncated", False)),
            engine_version=str(value["engine_version"]),
        )
        return replace(
            report,
            id=EntityId.from_value(str(value["id"])),
            generated_at=cls._datetime(value["generated_at"]),
        )

    @classmethod
    def finding(cls, value: Mapping[str, Any]) -> SimulationImpactFinding:
        return SimulationImpactFinding.create(
            dimension=str(value["dimension"]),
            severity=str(value["severity"]),
            code=str(value["code"]),
            message=str(value["message"]),
            object_key=cls._optional_text(value.get("object_key")),
            evidence=cls._mapping(value.get("evidence")),
        )

    @classmethod
    def readiness(cls, value: Mapping[str, Any]) -> SimulationReadinessScore:
        return SimulationReadinessScore.create(
            scope_type=str(value["scope_type"]),
            scope_key=str(value["scope_key"]),
            score=int(value["score"]),
            blockers=tuple(str(item) for item in cls._object_list(value.get("blockers"))),
            warnings=tuple(str(item) for item in cls._object_list(value.get("warnings"))),
            missing_evidence=tuple(
                str(item) for item in cls._object_list(value.get("missing_evidence"))
            ),
        )

    @classmethod
    def move_group(cls, value: Mapping[str, Any]) -> SimulationMoveGroup:
        group = SimulationMoveGroup.create(
            name=str(value["name"]),
            member_keys=tuple(str(item) for item in cls._object_list(value.get("member_keys"))),
            affinity_reasons=tuple(
                str(item) for item in cls._object_list(value.get("affinity_reasons"))
            ),
            risk_score=int(value["risk_score"]),
        )
        return replace(group, id=EntityId.from_value(str(value["id"])))

    @classmethod
    def blocking_dependency(cls, value: Mapping[str, Any]) -> SimulationBlockingDependency:
        return SimulationBlockingDependency.create(
            source_key=str(value["source_key"]),
            target_key=str(value["target_key"]),
            relation_type=str(value["relation_type"]),
            reason=str(value["reason"]),
        )

    @classmethod
    def wave(cls, value: Mapping[str, Any]) -> SimulationMigrationWave:
        return SimulationMigrationWave.create(
            number=int(value["number"]),
            group_ids=tuple(
                EntityId.from_value(str(item)) for item in cls._object_list(value.get("group_ids"))
            ),
            blocked_by_group_ids=tuple(
                EntityId.from_value(str(item))
                for item in cls._object_list(value.get("blocked_by_group_ids"))
            ),
            readiness_score=int(value["readiness_score"]),
        )

    @classmethod
    def comparison(cls, value: Mapping[str, Any]) -> SimulationScenarioComparison:
        comparison = SimulationScenarioComparison.create(
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            left_report_id=EntityId.from_value(str(value["left_report_id"])),
            right_report_id=EntityId.from_value(str(value["right_report_id"])),
            summary=cls._mapping(value.get("summary")),
            preferred_report_id=(
                None
                if value.get("preferred_report_id") is None
                else EntityId.from_value(str(value["preferred_report_id"]))
            ),
        )
        return replace(
            comparison,
            id=EntityId.from_value(str(value["id"])),
            created_at=cls._datetime(value["created_at"]),
        )

    @staticmethod
    def _datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @classmethod
    def _optional_datetime(cls, value: object) -> datetime | None:
        return None if value in (None, "") else cls._datetime(value)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return None if value in (None, "") else str(value)

    @staticmethod
    def _mapping(value: object) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValidationError("simulation record JSON object is invalid")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def _object_list(value: object) -> list[object]:
        if value is None:
            return []
        if not isinstance(value, list | tuple):
            raise ValidationError("simulation record JSON array is invalid")
        return list(value)

    @classmethod
    def _mapping_list(cls, value: object) -> list[Mapping[str, Any]]:
        items = cls._object_list(value)
        result: list[Mapping[str, Any]] = []
        for item in items:
            if not isinstance(item, Mapping):
                raise ValidationError("simulation record object array is invalid")
            result.append(item)
        return result
