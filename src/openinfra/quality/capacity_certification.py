from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from openinfra import __version__
from openinfra.domain.common import ValidationError

_REQUIRED_STAGES: Final[tuple[str, ...]] = (
    "baseline",
    "step-load",
    "endurance",
    "spike",
    "saturation",
)
_REQUIRED_CHAOS_SCENARIOS: Final[tuple[str, ...]] = (
    "api-worker-loss",
    "web-worker-loss",
    "db-replica-loss",
    "pgbouncer-restart",
)


class CapacityEvidenceParser:
    @staticmethod
    def number(value: object, field: str) -> float:
        if isinstance(value, bool):
            raise ValidationError(f"{field} must be numeric")
        try:
            result = float(str(value))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} must be numeric") from exc
        if not math.isfinite(result) or result < 0:
            raise ValidationError(f"{field} must be finite and non-negative")
        return result

    @classmethod
    def integer(cls, value: object, field: str) -> int:
        result = cls.number(value, field)
        if not result.is_integer():
            raise ValidationError(f"{field} must be an integer")
        return int(result)

    @staticmethod
    def boolean(value: object, field: str) -> bool:
        if not isinstance(value, bool):
            raise ValidationError(f"{field} must be a boolean")
        return value

    @staticmethod
    def object_mapping(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValidationError(f"{field} entries must be JSON objects")
        return {str(key): item for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class EnterpriseCapacityThresholds:
    p95_ms: float
    p99_ms: float
    error_rate_percent: float
    saturation_percent: float
    recovery_seconds: float
    memory_growth_percent: float
    replica_lag_seconds: float
    trace_coverage_percent: float

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> EnterpriseCapacityThresholds:
        values = cls(
            p95_ms=CapacityEvidenceParser.number(payload.get("p95_ms"), "thresholds.p95_ms"),
            p99_ms=CapacityEvidenceParser.number(payload.get("p99_ms"), "thresholds.p99_ms"),
            error_rate_percent=CapacityEvidenceParser.number(
                payload.get("error_rate_percent"), "thresholds.error_rate_percent"
            ),
            saturation_percent=CapacityEvidenceParser.number(
                payload.get("saturation_percent"), "thresholds.saturation_percent"
            ),
            recovery_seconds=CapacityEvidenceParser.number(
                payload.get("recovery_seconds"), "thresholds.recovery_seconds"
            ),
            memory_growth_percent=CapacityEvidenceParser.number(
                payload.get("memory_growth_percent"), "thresholds.memory_growth_percent"
            ),
            replica_lag_seconds=CapacityEvidenceParser.number(
                payload.get("replica_lag_seconds"), "thresholds.replica_lag_seconds"
            ),
            trace_coverage_percent=CapacityEvidenceParser.number(
                payload.get("trace_coverage_percent"), "thresholds.trace_coverage_percent"
            ),
        )
        if values.p99_ms < values.p95_ms:
            raise ValidationError("thresholds.p99_ms cannot be lower than p95_ms")
        for field, value in (
            ("error_rate_percent", values.error_rate_percent),
            ("saturation_percent", values.saturation_percent),
            ("memory_growth_percent", values.memory_growth_percent),
            ("trace_coverage_percent", values.trace_coverage_percent),
        ):
            if value > 100:
                raise ValidationError(f"thresholds.{field} cannot exceed 100")
        return values

    def as_dict(self) -> dict[str, float]:
        return {
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "error_rate_percent": self.error_rate_percent,
            "saturation_percent": self.saturation_percent,
            "recovery_seconds": self.recovery_seconds,
            "memory_growth_percent": self.memory_growth_percent,
            "replica_lag_seconds": self.replica_lag_seconds,
            "trace_coverage_percent": self.trace_coverage_percent,
        }


@dataclass(frozen=True, slots=True)
class EnterpriseTopologyEvidence:
    edition: str
    api_instances: int
    web_instances: int
    specialized_workers: int
    database_primaries: int
    database_replicas: int
    pgbouncer_instances: int
    regions: int
    dataset_objects: int
    dataset_relations: int
    topology_fingerprint: str

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> EnterpriseTopologyEvidence:
        value = cls(
            edition=str(payload.get("edition", "")).strip().lower(),
            api_instances=CapacityEvidenceParser.integer(
                payload.get("api_instances"), "topology.api_instances"
            ),
            web_instances=CapacityEvidenceParser.integer(
                payload.get("web_instances"), "topology.web_instances"
            ),
            specialized_workers=CapacityEvidenceParser.integer(
                payload.get("specialized_workers"), "topology.specialized_workers"
            ),
            database_primaries=CapacityEvidenceParser.integer(
                payload.get("database_primaries"), "topology.database_primaries"
            ),
            database_replicas=CapacityEvidenceParser.integer(
                payload.get("database_replicas"), "topology.database_replicas"
            ),
            pgbouncer_instances=CapacityEvidenceParser.integer(
                payload.get("pgbouncer_instances"), "topology.pgbouncer_instances"
            ),
            regions=CapacityEvidenceParser.integer(payload.get("regions"), "topology.regions"),
            dataset_objects=CapacityEvidenceParser.integer(
                payload.get("dataset_objects"), "topology.dataset_objects"
            ),
            dataset_relations=CapacityEvidenceParser.integer(
                payload.get("dataset_relations"), "topology.dataset_relations"
            ),
            topology_fingerprint=str(payload.get("topology_fingerprint", "")).strip().lower(),
        )
        if value.edition != "enterprise":
            raise ValidationError("capacity certification requires the Enterprise edition")
        if not value.topology_fingerprint or len(value.topology_fingerprint) < 32:
            raise ValidationError(
                "topology.topology_fingerprint must contain at least 32 characters"
            )
        return value

    def qualification_failures(self) -> tuple[str, ...]:
        minimums = {
            "api_instances": 2,
            "web_instances": 2,
            "specialized_workers": 4,
            "database_primaries": 1,
            "database_replicas": 1,
            "pgbouncer_instances": 2,
            "regions": 1,
            "dataset_objects": 100_000,
            "dataset_relations": 100_000,
        }
        return tuple(
            f"topology.{field}={getattr(self, field)} is below required minimum {minimum}"
            for field, minimum in minimums.items()
            if getattr(self, field) < minimum
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "edition": self.edition,
            "api_instances": self.api_instances,
            "web_instances": self.web_instances,
            "specialized_workers": self.specialized_workers,
            "database_primaries": self.database_primaries,
            "database_replicas": self.database_replicas,
            "pgbouncer_instances": self.pgbouncer_instances,
            "regions": self.regions,
            "dataset_objects": self.dataset_objects,
            "dataset_relations": self.dataset_relations,
            "topology_fingerprint": self.topology_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class CapacityStageEvidence:
    stage: str
    duration_seconds: float
    requests: int
    p95_ms: float
    p99_ms: float
    error_rate_percent: float
    saturation_percent: float
    memory_growth_percent: float
    replica_lag_seconds: float
    trace_coverage_percent: float
    metrics_complete: bool
    leak_detected: bool

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> CapacityStageEvidence:
        stage = str(payload.get("stage", "")).strip().lower()
        if stage not in _REQUIRED_STAGES:
            raise ValidationError(f"unsupported capacity stage: {stage or '<empty>'}")
        return cls(
            stage=stage,
            duration_seconds=CapacityEvidenceParser.number(
                payload.get("duration_seconds"), f"stages.{stage}.duration_seconds"
            ),
            requests=CapacityEvidenceParser.integer(
                payload.get("requests"), f"stages.{stage}.requests"
            ),
            p95_ms=CapacityEvidenceParser.number(payload.get("p95_ms"), f"stages.{stage}.p95_ms"),
            p99_ms=CapacityEvidenceParser.number(payload.get("p99_ms"), f"stages.{stage}.p99_ms"),
            error_rate_percent=CapacityEvidenceParser.number(
                payload.get("error_rate_percent"), f"stages.{stage}.error_rate_percent"
            ),
            saturation_percent=CapacityEvidenceParser.number(
                payload.get("saturation_percent"), f"stages.{stage}.saturation_percent"
            ),
            memory_growth_percent=CapacityEvidenceParser.number(
                payload.get("memory_growth_percent"), f"stages.{stage}.memory_growth_percent"
            ),
            replica_lag_seconds=CapacityEvidenceParser.number(
                payload.get("replica_lag_seconds"), f"stages.{stage}.replica_lag_seconds"
            ),
            trace_coverage_percent=CapacityEvidenceParser.number(
                payload.get("trace_coverage_percent"), f"stages.{stage}.trace_coverage_percent"
            ),
            metrics_complete=CapacityEvidenceParser.boolean(
                payload.get("metrics_complete"), f"stages.{stage}.metrics_complete"
            ),
            leak_detected=CapacityEvidenceParser.boolean(
                payload.get("leak_detected"), f"stages.{stage}.leak_detected"
            ),
        )

    def failures(self, thresholds: EnterpriseCapacityThresholds) -> tuple[str, ...]:
        failures: list[str] = []
        checks = (
            ("p95_ms", self.p95_ms, thresholds.p95_ms),
            ("p99_ms", self.p99_ms, thresholds.p99_ms),
            ("error_rate_percent", self.error_rate_percent, thresholds.error_rate_percent),
            ("saturation_percent", self.saturation_percent, thresholds.saturation_percent),
            ("memory_growth_percent", self.memory_growth_percent, thresholds.memory_growth_percent),
            ("replica_lag_seconds", self.replica_lag_seconds, thresholds.replica_lag_seconds),
        )
        failures.extend(
            f"stage {self.stage}: {name}={actual:.6f} exceeds {limit:.6f}"
            for name, actual, limit in checks
            if actual > limit
        )
        if self.trace_coverage_percent < thresholds.trace_coverage_percent:
            failures.append(
                f"stage {self.stage}: trace_coverage_percent={self.trace_coverage_percent:.6f} "
                f"is below {thresholds.trace_coverage_percent:.6f}"
            )
        if not self.metrics_complete:
            failures.append(f"stage {self.stage}: required Prometheus metrics are incomplete")
        if self.leak_detected:
            failures.append(f"stage {self.stage}: resource leak detected")
        if self.requests <= 0 or self.duration_seconds <= 0:
            failures.append(f"stage {self.stage}: non-empty duration and request evidence required")
        return tuple(failures)

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "duration_seconds": self.duration_seconds,
            "requests": self.requests,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "error_rate_percent": self.error_rate_percent,
            "saturation_percent": self.saturation_percent,
            "memory_growth_percent": self.memory_growth_percent,
            "replica_lag_seconds": self.replica_lag_seconds,
            "trace_coverage_percent": self.trace_coverage_percent,
            "metrics_complete": self.metrics_complete,
            "leak_detected": self.leak_detected,
        }


@dataclass(frozen=True, slots=True)
class ChaosScenarioEvidence:
    scenario: str
    fault_injected: bool
    service_recovered: bool
    recovery_seconds: float
    data_integrity_verified: bool
    acknowledged_work_lost: bool

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> ChaosScenarioEvidence:
        scenario = str(payload.get("scenario", "")).strip().lower()
        if scenario not in _REQUIRED_CHAOS_SCENARIOS:
            raise ValidationError(f"unsupported chaos scenario: {scenario or '<empty>'}")
        return cls(
            scenario=scenario,
            fault_injected=CapacityEvidenceParser.boolean(
                payload.get("fault_injected"), f"chaos.{scenario}.fault_injected"
            ),
            service_recovered=CapacityEvidenceParser.boolean(
                payload.get("service_recovered"), f"chaos.{scenario}.service_recovered"
            ),
            recovery_seconds=CapacityEvidenceParser.number(
                payload.get("recovery_seconds"), f"chaos.{scenario}.recovery_seconds"
            ),
            data_integrity_verified=CapacityEvidenceParser.boolean(
                payload.get("data_integrity_verified"),
                f"chaos.{scenario}.data_integrity_verified",
            ),
            acknowledged_work_lost=CapacityEvidenceParser.boolean(
                payload.get("acknowledged_work_lost"),
                f"chaos.{scenario}.acknowledged_work_lost",
            ),
        )

    def failures(self, thresholds: EnterpriseCapacityThresholds) -> tuple[str, ...]:
        failures: list[str] = []
        if not self.fault_injected:
            failures.append(f"chaos {self.scenario}: fault was not injected")
        if not self.service_recovered:
            failures.append(f"chaos {self.scenario}: service did not recover")
        if self.recovery_seconds > thresholds.recovery_seconds:
            failures.append(
                f"chaos {self.scenario}: recovery_seconds={self.recovery_seconds:.6f} "
                f"exceeds {thresholds.recovery_seconds:.6f}"
            )
        if not self.data_integrity_verified:
            failures.append(f"chaos {self.scenario}: data integrity was not verified")
        if self.acknowledged_work_lost:
            failures.append(f"chaos {self.scenario}: acknowledged work was lost")
        return tuple(failures)

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario": self.scenario,
            "fault_injected": self.fault_injected,
            "service_recovered": self.service_recovered,
            "recovery_seconds": self.recovery_seconds,
            "data_integrity_verified": self.data_integrity_verified,
            "acknowledged_work_lost": self.acknowledged_work_lost,
        }


@dataclass(frozen=True, slots=True)
class EnterpriseCapacityCertification:
    profile_id: str
    profile_version: int
    topology: EnterpriseTopologyEvidence
    thresholds: EnterpriseCapacityThresholds
    stages: tuple[CapacityStageEvidence, ...]
    chaos: tuple[ChaosScenarioEvidence, ...]
    source_hashes: dict[str, str]

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> EnterpriseCapacityCertification:
        profile_id = str(payload.get("profile_id", "")).strip().lower()
        if not profile_id or len(profile_id) > 80:
            raise ValidationError("profile_id is mandatory and limited to 80 characters")
        profile_version = CapacityEvidenceParser.integer(
            payload.get("profile_version"), "profile_version"
        )
        if profile_version < 1:
            raise ValidationError("profile_version must be greater than zero")
        topology_payload = payload.get("topology")
        thresholds_payload = payload.get("thresholds")
        stages_payload = payload.get("stages")
        chaos_payload = payload.get("chaos")
        hashes_payload = payload.get("source_hashes")
        if not isinstance(topology_payload, dict) or not isinstance(thresholds_payload, dict):
            raise ValidationError("topology and thresholds must be JSON objects")
        if not isinstance(stages_payload, list) or not isinstance(chaos_payload, list):
            raise ValidationError("stages and chaos must be JSON arrays")
        if not isinstance(hashes_payload, dict):
            raise ValidationError("source_hashes must be a JSON object")
        stages = tuple(
            CapacityStageEvidence.from_mapping(
                CapacityEvidenceParser.object_mapping(item, "stages")
            )
            for item in stages_payload
        )
        chaos = tuple(
            ChaosScenarioEvidence.from_mapping(CapacityEvidenceParser.object_mapping(item, "chaos"))
            for item in chaos_payload
        )
        stage_names = tuple(item.stage for item in stages)
        chaos_names = tuple(item.scenario for item in chaos)
        if len(set(stage_names)) != len(stage_names):
            raise ValidationError("capacity stages must be unique")
        if len(set(chaos_names)) != len(chaos_names):
            raise ValidationError("chaos scenarios must be unique")
        source_hashes = {
            str(name).strip(): str(value).strip().lower()
            for name, value in hashes_payload.items()
            if str(name).strip()
        }
        if not source_hashes or any(len(value) != 64 for value in source_hashes.values()):
            raise ValidationError("source_hashes must contain SHA-256 hexadecimal digests")
        return cls(
            profile_id=profile_id,
            profile_version=profile_version,
            topology=EnterpriseTopologyEvidence.from_mapping(topology_payload),
            thresholds=EnterpriseCapacityThresholds.from_mapping(thresholds_payload),
            stages=stages,
            chaos=chaos,
            source_hashes=source_hashes,
        )

    def evaluate(self) -> dict[str, object]:
        failures = list(self.topology.qualification_failures())
        stages_by_name = {item.stage: item for item in self.stages}
        chaos_by_name = {item.scenario: item for item in self.chaos}
        failures.extend(
            f"missing required capacity stage: {name}"
            for name in _REQUIRED_STAGES
            if name not in stages_by_name
        )
        failures.extend(
            f"missing required chaos scenario: {name}"
            for name in _REQUIRED_CHAOS_SCENARIOS
            if name not in chaos_by_name
        )
        for stage in self.stages:
            failures.extend(stage.failures(self.thresholds))
        for scenario in self.chaos:
            failures.extend(scenario.failures(self.thresholds))
        certified = not failures
        canonical = json.dumps(
            {
                "profile_id": self.profile_id,
                "profile_version": self.profile_version,
                "topology": self.topology.as_dict(),
                "thresholds": self.thresholds.as_dict(),
                "stages": [item.as_dict() for item in self.stages],
                "chaos": [item.as_dict() for item in self.chaos],
                "source_hashes": self.source_hashes,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            "schema_version": 1,
            "certification": "openinfra-enterprise-capacity",
            "openinfra_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "evidence_sha256": hashlib.sha256(canonical).hexdigest(),
            "capacity_certification": certified,
            "status": "certified" if certified else "rejected",
            "failures": failures,
            "topology": self.topology.as_dict(),
            "thresholds": self.thresholds.as_dict(),
            "stages": [item.as_dict() for item in self.stages],
            "chaos": [item.as_dict() for item in self.chaos],
            "source_hashes": dict(sorted(self.source_hashes.items())),
        }

    @classmethod
    def load(cls, path: Path) -> EnterpriseCapacityCertification:
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f"cannot read capacity evidence {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValidationError("capacity evidence root must be a JSON object")
        return cls.from_mapping(payload)


class EnterpriseCapacityCertificationService:
    @staticmethod
    def write_report(evidence_path: Path, output_path: Path) -> dict[str, object]:
        report = EnterpriseCapacityCertification.load(evidence_path).evaluate()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output_path)
        return report
