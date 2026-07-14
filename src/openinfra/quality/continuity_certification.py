from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Self

from openinfra import __version__
from openinfra.domain.common import ValidationError

_REQUIRED_PROCEDURES: Final[tuple[str, ...]] = (
    "incident-declaration",
    "stakeholder-communication",
    "backup-selection",
    "restore-execution",
    "pitr-execution",
    "service-validation",
    "data-integrity-validation",
    "business-validation",
    "failback-readiness",
    "postmortem",
)
_ALLOWED_EDITIONS: Final[frozenset[str]] = frozenset({"pro", "enterprise"})


class ContinuityEvidenceParser:
    @staticmethod
    def mapping(value: object, field: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise ValidationError(f"{field} must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def text(value: object, field: str, *, minimum: int = 1, maximum: int = 256) -> str:
        normalized = " ".join(str(value or "").strip().split())
        if not minimum <= len(normalized) <= maximum:
            raise ValidationError(f"{field} must contain {minimum} to {maximum} characters")
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
class ContinuityPlanEvidence:
    plan_id: str
    active: bool
    primary_site_code: str
    recovery_site_code: str
    rpo_seconds: int
    rto_seconds: int
    max_backup_age_seconds: int

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        primary = ContinuityEvidenceParser.text(
            payload.get("primary_site_code"), "plan.primary_site_code"
        )
        recovery = ContinuityEvidenceParser.text(
            payload.get("recovery_site_code"), "plan.recovery_site_code"
        )
        if primary == recovery:
            raise ValidationError("plan primary and recovery sites must be different")
        values = cls(
            plan_id=ContinuityEvidenceParser.text(payload.get("id"), "plan.id"),
            active=ContinuityEvidenceParser.boolean(payload.get("active"), "plan.active"),
            primary_site_code=primary,
            recovery_site_code=recovery,
            rpo_seconds=ContinuityEvidenceParser.integer(
                payload.get("rpo_seconds"), "plan.rpo_seconds"
            ),
            rto_seconds=ContinuityEvidenceParser.integer(
                payload.get("rto_seconds"), "plan.rto_seconds"
            ),
            max_backup_age_seconds=ContinuityEvidenceParser.integer(
                payload.get("max_backup_age_seconds"), "plan.max_backup_age_seconds"
            ),
        )
        if min(values.rpo_seconds, values.rto_seconds, values.max_backup_age_seconds) <= 0:
            raise ValidationError("plan continuity objectives must be strictly positive")
        return values


@dataclass(frozen=True, slots=True)
class DisasterRecoveryDrillEvidence:
    drill_id: str
    plan_id: str
    status: str
    replication_lag_seconds: int
    backup_age_seconds: int
    measured_rto_seconds: int
    restore_verified: bool
    recovery_available: bool
    vip_reachable: bool
    operator_confirmed: bool
    failure_reasons: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        reasons_value = payload.get("failure_reasons", [])
        if not isinstance(reasons_value, list):
            raise ValidationError("dr_drill.failure_reasons must be a JSON array")
        status = str(payload.get("status", "")).strip().lower()
        if status not in {"passed", "failed"}:
            raise ValidationError("dr_drill.status must be passed or failed")
        return cls(
            drill_id=ContinuityEvidenceParser.text(payload.get("id"), "dr_drill.id"),
            plan_id=ContinuityEvidenceParser.text(payload.get("plan_id"), "dr_drill.plan_id"),
            status=status,
            replication_lag_seconds=ContinuityEvidenceParser.integer(
                payload.get("replication_lag_seconds"), "dr_drill.replication_lag_seconds"
            ),
            backup_age_seconds=ContinuityEvidenceParser.integer(
                payload.get("backup_age_seconds"), "dr_drill.backup_age_seconds"
            ),
            measured_rto_seconds=ContinuityEvidenceParser.integer(
                payload.get("measured_rto_seconds"), "dr_drill.measured_rto_seconds"
            ),
            restore_verified=ContinuityEvidenceParser.boolean(
                payload.get("restore_verified"), "dr_drill.restore_verified"
            ),
            recovery_available=ContinuityEvidenceParser.boolean(
                payload.get("recovery_available"), "dr_drill.recovery_available"
            ),
            vip_reachable=ContinuityEvidenceParser.boolean(
                payload.get("vip_reachable"), "dr_drill.vip_reachable"
            ),
            operator_confirmed=ContinuityEvidenceParser.boolean(
                payload.get("operator_confirmed"), "dr_drill.operator_confirmed"
            ),
            failure_reasons=tuple(str(item).strip() for item in reasons_value if str(item).strip()),
        )


@dataclass(frozen=True, slots=True)
class BackupRestoreEvidence:
    backup_id: str
    backup_completed_at: datetime
    restore_started_at: datetime
    restore_completed_at: datetime
    restore_verified: bool
    integrity_verified: bool
    encryption_verified: bool

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        completed = ContinuityEvidenceParser.timestamp(
            payload.get("backup_completed_at"), "backup_restore.backup_completed_at"
        )
        started = ContinuityEvidenceParser.timestamp(
            payload.get("restore_started_at"), "backup_restore.restore_started_at"
        )
        restored = ContinuityEvidenceParser.timestamp(
            payload.get("restore_completed_at"), "backup_restore.restore_completed_at"
        )
        if restored < started:
            raise ValidationError("backup restore completion cannot precede its start")
        return cls(
            backup_id=ContinuityEvidenceParser.text(
                payload.get("backup_id"), "backup_restore.backup_id"
            ),
            backup_completed_at=completed,
            restore_started_at=started,
            restore_completed_at=restored,
            restore_verified=ContinuityEvidenceParser.boolean(
                payload.get("restore_verified"), "backup_restore.restore_verified"
            ),
            integrity_verified=ContinuityEvidenceParser.boolean(
                payload.get("integrity_verified"), "backup_restore.integrity_verified"
            ),
            encryption_verified=ContinuityEvidenceParser.boolean(
                payload.get("encryption_verified"), "backup_restore.encryption_verified"
            ),
        )

    def age_at(self, incident_at: datetime) -> int:
        if self.backup_completed_at > incident_at:
            raise ValidationError("backup completion cannot be after the incident")
        return int((incident_at - self.backup_completed_at).total_seconds())


@dataclass(frozen=True, slots=True)
class PointInTimeRecoveryEvidence:
    incident_at: datetime
    target_recovery_point_at: datetime
    recovered_point_at: datetime
    recovery_started_at: datetime
    recovery_completed_at: datetime
    consistency_verified: bool

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        incident = ContinuityEvidenceParser.timestamp(
            payload.get("incident_at"), "pitr.incident_at"
        )
        target = ContinuityEvidenceParser.timestamp(
            payload.get("target_recovery_point_at"), "pitr.target_recovery_point_at"
        )
        recovered = ContinuityEvidenceParser.timestamp(
            payload.get("recovered_point_at"), "pitr.recovered_point_at"
        )
        started = ContinuityEvidenceParser.timestamp(
            payload.get("recovery_started_at"), "pitr.recovery_started_at"
        )
        completed = ContinuityEvidenceParser.timestamp(
            payload.get("recovery_completed_at"), "pitr.recovery_completed_at"
        )
        if target > incident or recovered > incident:
            raise ValidationError("PITR recovery points cannot be after the incident")
        if started < incident:
            raise ValidationError("PITR recovery cannot start before the incident")
        if completed < started:
            raise ValidationError("PITR recovery completion cannot precede its start")
        return cls(
            incident_at=incident,
            target_recovery_point_at=target,
            recovered_point_at=recovered,
            recovery_started_at=started,
            recovery_completed_at=completed,
            consistency_verified=ContinuityEvidenceParser.boolean(
                payload.get("consistency_verified"), "pitr.consistency_verified"
            ),
        )

    @property
    def measured_data_loss_seconds(self) -> int:
        return int((self.incident_at - self.recovered_point_at).total_seconds())

    @property
    def measured_recovery_seconds(self) -> int:
        return int((self.recovery_completed_at - self.incident_at).total_seconds())

    @property
    def target_deviation_seconds(self) -> int:
        return abs(int((self.recovered_point_at - self.target_recovery_point_at).total_seconds()))


@dataclass(frozen=True, slots=True)
class ProcedureEvidence:
    owner: str
    approved_by: str
    reviewed_at: datetime
    steps: tuple[tuple[str, bool], ...]

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        raw_steps = ContinuityEvidenceParser.mapping(payload.get("steps"), "procedures.steps")
        if set(raw_steps) != set(_REQUIRED_PROCEDURES):
            missing = sorted(set(_REQUIRED_PROCEDURES) - set(raw_steps))
            extra = sorted(set(raw_steps) - set(_REQUIRED_PROCEDURES))
            raise ValidationError(
                "procedures.steps must exactly match required procedures; "
                f"missing={missing}, extra={extra}"
            )
        steps = tuple(
            (name, ContinuityEvidenceParser.boolean(raw_steps[name], f"procedures.steps.{name}"))
            for name in _REQUIRED_PROCEDURES
        )
        return cls(
            owner=ContinuityEvidenceParser.text(payload.get("owner"), "procedures.owner"),
            approved_by=ContinuityEvidenceParser.text(
                payload.get("approved_by"), "procedures.approved_by"
            ),
            reviewed_at=ContinuityEvidenceParser.timestamp(
                payload.get("reviewed_at"), "procedures.reviewed_at"
            ),
            steps=steps,
        )

    @property
    def incomplete_steps(self) -> tuple[str, ...]:
        return tuple(name for name, completed in self.steps if not completed)


@dataclass(frozen=True, slots=True)
class SourceArtifactEvidence:
    name: str
    sha256: str
    size_bytes: int

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        return cls(
            name=ContinuityEvidenceParser.text(payload.get("name"), "source_artifacts.name"),
            sha256=ContinuityEvidenceParser.sha256(
                payload.get("sha256"), "source_artifacts.sha256"
            ),
            size_bytes=ContinuityEvidenceParser.integer(
                payload.get("size_bytes"), "source_artifacts.size_bytes"
            ),
        )


@dataclass(frozen=True, slots=True)
class PraPcaCertificationEvidence:
    profile_id: str
    profile_version: int
    edition: str
    generated_at: datetime
    plan: ContinuityPlanEvidence
    dr_drill: DisasterRecoveryDrillEvidence
    backup_restore: BackupRestoreEvidence
    pitr: PointInTimeRecoveryEvidence
    procedures: ProcedureEvidence
    source_artifacts: tuple[SourceArtifactEvidence, ...]
    evidence_digest: str

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> Self:
        profile_id = str(payload.get("profile_id", "")).strip()
        if profile_id != "openinfra-pra-pca-v1":
            raise ValidationError("unsupported PRA/PCA certification profile")
        profile_version = ContinuityEvidenceParser.integer(
            payload.get("profile_version"), "profile_version"
        )
        if profile_version != 1:
            raise ValidationError("PRA/PCA certification profile_version must be 1")
        edition = str(payload.get("edition", "")).strip().lower()
        if edition not in _ALLOWED_EDITIONS:
            raise ValidationError("PRA/PCA certification requires the Pro or Enterprise edition")
        raw_artifacts = payload.get("source_artifacts")
        if not isinstance(raw_artifacts, list) or len(raw_artifacts) != 5:
            raise ValidationError("source_artifacts must contain exactly five source files")
        artifacts = tuple(
            SourceArtifactEvidence.from_mapping(
                ContinuityEvidenceParser.mapping(item, f"source_artifacts[{index}]")
            )
            for index, item in enumerate(raw_artifacts)
        )
        if len({artifact.name for artifact in artifacts}) != len(artifacts):
            raise ValidationError("source_artifacts names must be unique")
        evidence = cls(
            profile_id=profile_id,
            profile_version=profile_version,
            edition=edition,
            generated_at=ContinuityEvidenceParser.timestamp(
                payload.get("generated_at"), "generated_at"
            ),
            plan=ContinuityPlanEvidence.from_mapping(
                ContinuityEvidenceParser.mapping(payload.get("plan"), "plan")
            ),
            dr_drill=DisasterRecoveryDrillEvidence.from_mapping(
                ContinuityEvidenceParser.mapping(payload.get("dr_drill"), "dr_drill")
            ),
            backup_restore=BackupRestoreEvidence.from_mapping(
                ContinuityEvidenceParser.mapping(payload.get("backup_restore"), "backup_restore")
            ),
            pitr=PointInTimeRecoveryEvidence.from_mapping(
                ContinuityEvidenceParser.mapping(payload.get("pitr"), "pitr")
            ),
            procedures=ProcedureEvidence.from_mapping(
                ContinuityEvidenceParser.mapping(payload.get("procedures"), "procedures")
            ),
            source_artifacts=artifacts,
            evidence_digest=ContinuityEvidenceParser.sha256(
                payload.get("evidence_digest"), "evidence_digest"
            ),
        )
        if evidence.dr_drill.plan_id != evidence.plan.plan_id:
            raise ValidationError("DR drill does not belong to the certified plan")
        expected_digest = cls.digest_for(payload)
        if evidence.evidence_digest != expected_digest:
            raise ValidationError("PRA/PCA evidence digest mismatch")
        return evidence

    @staticmethod
    def digest_for(payload: dict[str, object]) -> str:
        canonical = {str(key): value for key, value in payload.items() if key != "evidence_digest"}
        encoded = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def measured_rpo_seconds(self) -> int:
        return max(self.dr_drill.replication_lag_seconds, self.pitr.measured_data_loss_seconds)

    @property
    def measured_rto_seconds(self) -> int:
        return max(self.dr_drill.measured_rto_seconds, self.pitr.measured_recovery_seconds)

    @property
    def measured_backup_age_seconds(self) -> int:
        return max(
            self.dr_drill.backup_age_seconds,
            self.backup_restore.age_at(self.pitr.incident_at),
        )

    def failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        if not self.plan.active:
            failures.append("certified DR plan is inactive")
        if self.dr_drill.status != "passed":
            failures.append("DR drill did not pass")
        if self.dr_drill.failure_reasons:
            failures.append("DR drill contains failure reasons")
        for field, passed in (
            ("dr_drill.restore_verified", self.dr_drill.restore_verified),
            ("dr_drill.recovery_available", self.dr_drill.recovery_available),
            ("dr_drill.vip_reachable", self.dr_drill.vip_reachable),
            ("dr_drill.operator_confirmed", self.dr_drill.operator_confirmed),
            ("backup_restore.restore_verified", self.backup_restore.restore_verified),
            ("backup_restore.integrity_verified", self.backup_restore.integrity_verified),
            ("backup_restore.encryption_verified", self.backup_restore.encryption_verified),
            ("pitr.consistency_verified", self.pitr.consistency_verified),
        ):
            if not passed:
                failures.append(f"{field} is not verified")
        if self.measured_rpo_seconds > self.plan.rpo_seconds:
            failures.append(
                "measured RPO "
                f"{self.measured_rpo_seconds}s exceeds objective {self.plan.rpo_seconds}s"
            )
        if self.measured_rto_seconds > self.plan.rto_seconds:
            failures.append(
                "measured RTO "
                f"{self.measured_rto_seconds}s exceeds objective {self.plan.rto_seconds}s"
            )
        if self.measured_backup_age_seconds > self.plan.max_backup_age_seconds:
            failures.append(
                "measured backup age "
                f"{self.measured_backup_age_seconds}s exceeds objective "
                f"{self.plan.max_backup_age_seconds}s"
            )
        if self.pitr.target_deviation_seconds > self.plan.rpo_seconds:
            failures.append(
                "PITR recovered point deviates from requested target by "
                f"{self.pitr.target_deviation_seconds}s"
            )
        failures.extend(
            f"required procedure step is incomplete: {name}"
            for name in self.procedures.incomplete_steps
        )
        return tuple(failures)

    def certification_report(self) -> dict[str, object]:
        failures = self.failures()
        return {
            "openinfra_version": __version__,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "edition": self.edition,
            "generated_at": self.generated_at.isoformat(),
            "pra_pca_certification": not failures,
            "status": "passed" if not failures else "failed",
            "failures": list(failures),
            "objectives": {
                "rpo_seconds": self.plan.rpo_seconds,
                "rto_seconds": self.plan.rto_seconds,
                "max_backup_age_seconds": self.plan.max_backup_age_seconds,
            },
            "measurements": {
                "rpo_seconds": self.measured_rpo_seconds,
                "rto_seconds": self.measured_rto_seconds,
                "backup_age_seconds": self.measured_backup_age_seconds,
                "pitr_target_deviation_seconds": self.pitr.target_deviation_seconds,
            },
            "plan_id": self.plan.plan_id,
            "drill_id": self.dr_drill.drill_id,
            "backup_id": self.backup_restore.backup_id,
            "evidence_digest": self.evidence_digest,
            "source_artifacts": [
                {
                    "name": artifact.name,
                    "sha256": artifact.sha256,
                    "size_bytes": artifact.size_bytes,
                }
                for artifact in self.source_artifacts
            ],
        }

    @staticmethod
    def required_procedures() -> tuple[str, ...]:
        return _REQUIRED_PROCEDURES
