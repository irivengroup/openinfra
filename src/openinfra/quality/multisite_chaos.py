from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Self

from openinfra import __version__
from openinfra.domain.common import ValidationError

_REQUIRED_SCENARIOS: Final[tuple[str, ...]] = (
    "network-partition",
    "site-loss",
    "agent-loss",
    "database-loss",
    "queue-saturation",
    "frontend-loss",
)
_PROFILE_ID: Final[str] = "openinfra-multisite-chaos-v1"
_PROFILE_VERSION: Final[int] = 1


class MultisiteChaosParser:
    @staticmethod
    def mapping(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValidationError(f"{field} must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def text(value: object, field: str, *, maximum: int = 256) -> str:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized or len(normalized) > maximum:
            raise ValidationError(f"{field} must contain 1 to {maximum} characters")
        return normalized

    @staticmethod
    def boolean(value: object, field: str) -> bool:
        if not isinstance(value, bool):
            raise ValidationError(f"{field} must be a boolean")
        return value

    @staticmethod
    def number(value: object, field: str) -> float:
        if isinstance(value, bool):
            raise ValidationError(f"{field} must be numeric")
        try:
            parsed = float(str(value))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} must be numeric") from exc
        if not math.isfinite(parsed) or parsed < 0:
            raise ValidationError(f"{field} must be finite and non-negative")
        return parsed

    @classmethod
    def integer(cls, value: object, field: str) -> int:
        parsed = cls.number(value, field)
        if not parsed.is_integer():
            raise ValidationError(f"{field} must be an integer")
        return int(parsed)

    @staticmethod
    def timestamp(value: object, field: str) -> datetime:
        raw = str(value or "").strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field} must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValidationError(f"{field} must be timezone-aware")
        return parsed.astimezone(UTC)

    @staticmethod
    def sha256(value: object, field: str) -> str:
        normalized = str(value or "").strip()
        if len(normalized) != 64 or any(
            character not in "0123456789abcdef" for character in normalized
        ):
            raise ValidationError(f"{field} must be a lowercase SHA-256 digest")
        return normalized


@dataclass(frozen=True, slots=True)
class ChaosObjective:
    max_recovery_seconds: float
    min_availability_ratio: float
    max_error_rate: float

    @classmethod
    def from_mapping(cls, payload: dict[str, object], scenario: str) -> Self:
        field = f"objectives.{scenario}"
        value = cls(
            max_recovery_seconds=MultisiteChaosParser.number(
                payload.get("max_recovery_seconds"), f"{field}.max_recovery_seconds"
            ),
            min_availability_ratio=MultisiteChaosParser.number(
                payload.get("min_availability_ratio"), f"{field}.min_availability_ratio"
            ),
            max_error_rate=MultisiteChaosParser.number(
                payload.get("max_error_rate"), f"{field}.max_error_rate"
            ),
        )
        if value.max_recovery_seconds <= 0:
            raise ValidationError(f"{field}.max_recovery_seconds must be strictly positive")
        if not 0 <= value.min_availability_ratio <= 1:
            raise ValidationError(f"{field}.min_availability_ratio must be between 0 and 1")
        if not 0 <= value.max_error_rate <= 1:
            raise ValidationError(f"{field}.max_error_rate must be between 0 and 1")
        return value


@dataclass(frozen=True, slots=True)
class ChaosScenarioEvidence:
    scenario: str
    started_at: datetime
    completed_at: datetime
    fault_injected: bool
    controlled_degradation: bool
    recovery_completed: bool
    rollback_verified: bool
    data_integrity_verified: bool
    corruption_detected: bool
    acknowledged_work_lost: bool
    recovery_seconds: float
    availability_ratio: float
    error_rate: float
    probe_count: int
    integrity_sha256_before: str
    integrity_sha256_after: str

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        scenario = MultisiteChaosParser.text(payload.get("scenario"), "scenario").lower()
        if scenario not in _REQUIRED_SCENARIOS:
            raise ValidationError(f"unsupported multisite chaos scenario: {scenario}")
        started = MultisiteChaosParser.timestamp(payload.get("started_at"), "started_at")
        completed = MultisiteChaosParser.timestamp(payload.get("completed_at"), "completed_at")
        if completed < started:
            raise ValidationError("chaos scenario completion cannot precede its start")
        probe_count = MultisiteChaosParser.integer(payload.get("probe_count"), "probe_count")
        if probe_count <= 0:
            raise ValidationError("probe_count must be strictly positive")
        availability = MultisiteChaosParser.number(
            payload.get("availability_ratio"), "availability_ratio"
        )
        error_rate = MultisiteChaosParser.number(payload.get("error_rate"), "error_rate")
        if not 0 <= availability <= 1 or not 0 <= error_rate <= 1:
            raise ValidationError("availability_ratio and error_rate must be between 0 and 1")
        before = MultisiteChaosParser.sha256(
            payload.get("integrity_sha256_before"), "integrity_sha256_before"
        )
        after = MultisiteChaosParser.sha256(
            payload.get("integrity_sha256_after"), "integrity_sha256_after"
        )
        return cls(
            scenario=scenario,
            started_at=started,
            completed_at=completed,
            fault_injected=MultisiteChaosParser.boolean(
                payload.get("fault_injected"), "fault_injected"
            ),
            controlled_degradation=MultisiteChaosParser.boolean(
                payload.get("controlled_degradation"), "controlled_degradation"
            ),
            recovery_completed=MultisiteChaosParser.boolean(
                payload.get("recovery_completed"), "recovery_completed"
            ),
            rollback_verified=MultisiteChaosParser.boolean(
                payload.get("rollback_verified"), "rollback_verified"
            ),
            data_integrity_verified=MultisiteChaosParser.boolean(
                payload.get("data_integrity_verified"), "data_integrity_verified"
            ),
            corruption_detected=MultisiteChaosParser.boolean(
                payload.get("corruption_detected"), "corruption_detected"
            ),
            acknowledged_work_lost=MultisiteChaosParser.boolean(
                payload.get("acknowledged_work_lost"), "acknowledged_work_lost"
            ),
            recovery_seconds=MultisiteChaosParser.number(
                payload.get("recovery_seconds"), "recovery_seconds"
            ),
            availability_ratio=availability,
            error_rate=error_rate,
            probe_count=probe_count,
            integrity_sha256_before=before,
            integrity_sha256_after=after,
        )

    def failures(self, objective: ChaosObjective) -> tuple[str, ...]:
        failures: list[str] = []
        prefix = self.scenario
        checks = (
            (self.fault_injected, "fault was not injected"),
            (self.controlled_degradation, "degradation was not controlled"),
            (self.recovery_completed, "service did not recover"),
            (self.rollback_verified, "fault rollback was not verified"),
            (self.data_integrity_verified, "data integrity was not verified"),
            (not self.corruption_detected, "data corruption was detected"),
            (not self.acknowledged_work_lost, "acknowledged work was lost"),
            (
                self.integrity_sha256_before == self.integrity_sha256_after,
                "integrity digest changed",
            ),
        )
        failures.extend(f"{prefix}: {message}" for passed, message in checks if not passed)
        if self.recovery_seconds > objective.max_recovery_seconds:
            failures.append(
                f"{prefix}: recovery {self.recovery_seconds:.3f}s exceeds "
                f"{objective.max_recovery_seconds:.3f}s"
            )
        if self.availability_ratio < objective.min_availability_ratio:
            failures.append(
                f"{prefix}: availability {self.availability_ratio:.6f} is below "
                f"{objective.min_availability_ratio:.6f}"
            )
        if self.error_rate > objective.max_error_rate:
            failures.append(
                f"{prefix}: error rate {self.error_rate:.6f} exceeds {objective.max_error_rate:.6f}"
            )
        return tuple(failures)


@dataclass(frozen=True, slots=True)
class ChaosSourceArtifact:
    name: str
    sha256: str
    size_bytes: int

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        size = MultisiteChaosParser.integer(payload.get("size_bytes"), "artifact.size_bytes")
        if size <= 0:
            raise ValidationError("artifact.size_bytes must be strictly positive")
        return cls(
            name=MultisiteChaosParser.text(payload.get("name"), "artifact.name"),
            sha256=MultisiteChaosParser.sha256(payload.get("sha256"), "artifact.sha256"),
            size_bytes=size,
        )


@dataclass(frozen=True, slots=True)
class MultisiteChaosCampaignEvidence:
    profile_id: str
    profile_version: int
    edition: str
    topology_id: str
    generated_at: datetime
    objectives: dict[str, ChaosObjective]
    scenarios: tuple[ChaosScenarioEvidence, ...]
    source_artifacts: tuple[ChaosSourceArtifact, ...]
    evidence_digest: str

    @classmethod
    def required_scenarios(cls) -> tuple[str, ...]:
        return _REQUIRED_SCENARIOS

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        profile_id = MultisiteChaosParser.text(payload.get("profile_id"), "profile_id")
        if profile_id != _PROFILE_ID:
            raise ValidationError(f"unsupported multisite chaos profile: {profile_id}")
        profile_version = MultisiteChaosParser.integer(
            payload.get("profile_version"), "profile_version"
        )
        if profile_version != _PROFILE_VERSION:
            raise ValidationError("multisite chaos profile_version must be 1")
        edition = MultisiteChaosParser.text(payload.get("edition"), "edition").lower()
        if edition != "enterprise":
            raise ValidationError("multisite chaos certification requires Enterprise edition")
        objectives_payload = MultisiteChaosParser.mapping(payload.get("objectives"), "objectives")
        if tuple(sorted(objectives_payload)) != tuple(sorted(_REQUIRED_SCENARIOS)):
            raise ValidationError(
                "multisite chaos objectives must exactly match required scenarios"
            )
        objectives = {
            scenario: ChaosObjective.from_mapping(
                MultisiteChaosParser.mapping(
                    objectives_payload[scenario], f"objectives.{scenario}"
                ),
                scenario,
            )
            for scenario in _REQUIRED_SCENARIOS
        }
        scenarios_value = payload.get("scenarios")
        if not isinstance(scenarios_value, list) or len(scenarios_value) != len(
            _REQUIRED_SCENARIOS
        ):
            raise ValidationError("multisite chaos evidence must contain exactly six scenarios")
        scenarios = tuple(
            ChaosScenarioEvidence.from_mapping(
                MultisiteChaosParser.mapping(item, f"scenarios[{index}]")
            )
            for index, item in enumerate(scenarios_value)
        )
        scenario_names = tuple(item.scenario for item in scenarios)
        if tuple(sorted(scenario_names)) != tuple(sorted(_REQUIRED_SCENARIOS)):
            raise ValidationError("multisite chaos scenario set is incomplete or duplicated")
        artifacts_value = payload.get("source_artifacts")
        if not isinstance(artifacts_value, list) or len(artifacts_value) != len(
            _REQUIRED_SCENARIOS
        ):
            raise ValidationError(
                "multisite chaos evidence must contain exactly six source artifacts"
            )
        artifacts = tuple(
            ChaosSourceArtifact.from_mapping(
                MultisiteChaosParser.mapping(item, f"source_artifacts[{index}]")
            )
            for index, item in enumerate(artifacts_value)
        )
        artifact_names = tuple(item.name for item in artifacts)
        if len(set(artifact_names)) != len(artifact_names):
            raise ValidationError("multisite chaos source artifact names must be unique")
        if tuple(sorted(artifact_names)) != tuple(sorted(_REQUIRED_SCENARIOS)):
            raise ValidationError("multisite chaos artifacts must exactly match required scenarios")
        evidence_digest = MultisiteChaosParser.sha256(
            payload.get("evidence_digest"), "evidence_digest"
        )
        expected_digest = cls.digest_for(payload)
        if evidence_digest != expected_digest:
            raise ValidationError("multisite chaos evidence digest mismatch")
        return cls(
            profile_id=profile_id,
            profile_version=profile_version,
            edition=edition,
            topology_id=MultisiteChaosParser.text(payload.get("topology_id"), "topology_id"),
            generated_at=MultisiteChaosParser.timestamp(
                payload.get("generated_at"), "generated_at"
            ),
            objectives=objectives,
            scenarios=scenarios,
            source_artifacts=artifacts,
            evidence_digest=evidence_digest,
        )

    @staticmethod
    def digest_for(payload: dict[str, object]) -> str:
        unsigned = {key: value for key, value in payload.items() if key != "evidence_digest"}
        canonical = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        for scenario in self.scenarios:
            failures.extend(scenario.failures(self.objectives[scenario.scenario]))
        return tuple(failures)

    def certification_report(self) -> dict[str, object]:
        failures = self.failures()
        return {
            "openinfra_version": __version__,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "edition": self.edition,
            "topology_id": self.topology_id,
            "generated_at": self.generated_at.isoformat(),
            "multisite_chaos_certification": not failures,
            "status": "passed" if not failures else "failed",
            "failures": list(failures),
            "scenario_count": len(self.scenarios),
            "scenarios": {
                item.scenario: {
                    "recovery_seconds": item.recovery_seconds,
                    "availability_ratio": item.availability_ratio,
                    "error_rate": item.error_rate,
                    "probe_count": item.probe_count,
                    "data_integrity_verified": item.data_integrity_verified,
                }
                for item in self.scenarios
            },
            "evidence_digest": self.evidence_digest,
        }
