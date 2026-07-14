from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, Final

from openinfra import __version__
from openinfra.quality.release_packaging import (
    ReleaseFileWriter,
    ReleasePackagingError,
    ReleaseSignatureVerifier,
    ReleaseSigningMaterial,
)


class SupportReadinessError(Exception):
    """Raised when the support and maintenance model is incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class SupportTarget:
    severity: str
    response_minutes: int
    update_minutes: int
    restoration_hours: int

    @classmethod
    def from_mapping(cls, severity: str, value: object) -> SupportTarget:
        if not isinstance(value, dict):
            raise SupportReadinessError(f"support target {severity} must be an object")
        response = cls._positive_int(value.get("response_minutes"), "response_minutes", severity)
        update = cls._positive_int(value.get("update_minutes"), "update_minutes", severity)
        restoration = cls._positive_int(
            value.get("restoration_hours"), "restoration_hours", severity
        )
        return cls(severity, response, update, restoration)

    @staticmethod
    def _positive_int(value: object, field: str, severity: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise SupportReadinessError(f"{field} for {severity} must be a positive integer")
        return value


@dataclass(frozen=True, slots=True)
class SupportEditionProfile:
    edition: str
    service_hours: str
    channels: tuple[str, ...]
    targets: tuple[SupportTarget, ...]

    @classmethod
    def from_mapping(cls, edition: str, value: object) -> SupportEditionProfile:
        if not isinstance(value, dict):
            raise SupportReadinessError(f"support profile {edition} must be an object")
        service_hours = str(value.get("service_hours", "")).strip()
        channels = SupportPolicyParser.string_tuple(value.get("channels"), f"{edition} channels")
        raw_targets = value.get("targets")
        if not isinstance(raw_targets, dict):
            raise SupportReadinessError(f"support profile {edition} must declare targets")
        severities = tuple(str(key) for key in raw_targets)
        if set(severities) != SupportPolicy.EXPECTED_SEVERITIES:
            raise SupportReadinessError(
                f"support profile {edition} must define exactly S1, S2, S3 and S4"
            )
        targets = tuple(
            SupportTarget.from_mapping(severity, raw_targets[severity])
            for severity in sorted(severities)
        )
        if not service_hours:
            raise SupportReadinessError(f"support profile {edition} service_hours is required")
        return cls(edition, service_hours, channels, targets)

    def target(self, severity: str) -> SupportTarget:
        for target in self.targets:
            if target.severity == severity:
                return target
        raise SupportReadinessError(f"support target is missing: {self.edition}/{severity}")


@dataclass(frozen=True, slots=True)
class LifecycleStage:
    name: str
    duration_months: int
    fixes: frozenset[str]

    @classmethod
    def from_mapping(cls, value: object) -> LifecycleStage:
        if not isinstance(value, dict):
            raise SupportReadinessError("lifecycle stages must be objects")
        name = str(value.get("name", "")).strip()
        duration = value.get("duration_months")
        raw_fixes = value.get("fixes")
        if not isinstance(raw_fixes, list):
            raise SupportReadinessError(f"{name} fixes must be an array")
        fixes_values = tuple(str(item).strip() for item in raw_fixes)
        if any(not item for item in fixes_values) or len(fixes_values) != len(set(fixes_values)):
            raise SupportReadinessError(f"{name} fixes entries must be non-empty and unique")
        fixes = frozenset(fixes_values)
        if not name:
            raise SupportReadinessError("lifecycle stage name is required")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
            raise SupportReadinessError(f"lifecycle duration for {name} must be non-negative")
        return cls(name, duration, fixes)


@dataclass(frozen=True, slots=True)
class PatchTarget:
    severity: str
    mitigation_hours: int
    fix_days: int

    @classmethod
    def from_mapping(cls, severity: str, value: object) -> PatchTarget:
        if not isinstance(value, dict):
            raise SupportReadinessError(f"patch target {severity} must be an object")
        mitigation = SupportTarget._positive_int(
            value.get("mitigation_hours"), "mitigation_hours", severity
        )
        fix_days = SupportTarget._positive_int(value.get("fix_days"), "fix_days", severity)
        return cls(severity, mitigation, fix_days)


@dataclass(frozen=True, slots=True)
class EscalationLevel:
    level: str
    owner: str
    triggers: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: object) -> EscalationLevel:
        if not isinstance(value, dict):
            raise SupportReadinessError("escalation levels must be objects")
        level = str(value.get("level", "")).strip()
        owner = str(value.get("owner", "")).strip()
        triggers = SupportPolicyParser.string_tuple(value.get("triggers"), f"{level} triggers")
        if not level or not owner:
            raise SupportReadinessError("escalation level and owner are required")
        return cls(level, owner, triggers)


@dataclass(frozen=True, slots=True)
class SupportPolicy:
    schema_version: int
    epic: str
    release_version: str
    profiles: tuple[SupportEditionProfile, ...]
    lifecycle: tuple[LifecycleStage, ...]
    patch_targets: tuple[PatchTarget, ...]
    direct_upgrade_span: int
    staged_upgrade_span: int
    backup_required: bool
    rollback_required: bool
    escalation: tuple[EscalationLevel, ...]
    required_documents: tuple[str, ...]

    EXPECTED_EDITIONS: ClassVar[frozenset[str]] = frozenset({"lite", "pro", "enterprise"})
    EXPECTED_SEVERITIES: ClassVar[frozenset[str]] = frozenset({"S1", "S2", "S3", "S4"})
    EXPECTED_LIFECYCLE: ClassVar[tuple[str, ...]] = (
        "active",
        "maintenance",
        "security-only",
        "end-of-life",
    )
    EXPECTED_PATCH_SEVERITIES: ClassVar[tuple[str, ...]] = (
        "critical",
        "high",
        "medium",
        "low",
    )
    EXPECTED_ESCALATION: ClassVar[tuple[str, ...]] = ("L1", "L2", "L3", "incident-command")

    @classmethod
    def load(cls, path: Path) -> SupportPolicy:
        payload = SupportPolicyParser.load_json(path)
        if payload.get("schema_version") != 1:
            raise SupportReadinessError("unsupported support policy schema")
        if str(payload.get("epic", "")).strip() != "EPIC-1806":
            raise SupportReadinessError("support policy must target EPIC-1806")
        release_version = str(payload.get("release_version", "")).strip()
        if release_version != __version__:
            raise SupportReadinessError(
                f"support policy version {release_version!r} does not match {__version__}"
            )
        profiles = cls._profiles(payload.get("support_profiles"))
        lifecycle = cls._lifecycle(payload.get("lifecycle"))
        patch_targets = cls._patch_targets(payload.get("patch_policy"))
        direct, staged, backup_required, rollback_required = cls._migration(
            payload.get("migration_policy")
        )
        escalation = cls._escalation(payload.get("escalation_matrix"))
        documents = SupportPolicyParser.string_tuple(
            payload.get("required_documents"), "required_documents"
        )
        policy = cls(
            schema_version=1,
            epic="EPIC-1806",
            release_version=release_version,
            profiles=profiles,
            lifecycle=lifecycle,
            patch_targets=patch_targets,
            direct_upgrade_span=direct,
            staged_upgrade_span=staged,
            backup_required=backup_required,
            rollback_required=rollback_required,
            escalation=escalation,
            required_documents=documents,
        )
        SupportPolicyValidator.validate_semantics(policy)
        return policy

    @classmethod
    def _profiles(cls, value: object) -> tuple[SupportEditionProfile, ...]:
        if not isinstance(value, dict) or set(value) != cls.EXPECTED_EDITIONS:
            raise SupportReadinessError("support_profiles must define lite, pro and enterprise")
        return tuple(
            SupportEditionProfile.from_mapping(edition, value[edition])
            for edition in sorted(cls.EXPECTED_EDITIONS)
        )

    @classmethod
    def _lifecycle(cls, value: object) -> tuple[LifecycleStage, ...]:
        if not isinstance(value, dict):
            raise SupportReadinessError("lifecycle must be an object")
        stages_value = value.get("stages")
        if not isinstance(stages_value, list):
            raise SupportReadinessError("lifecycle must declare stages")
        stages = tuple(LifecycleStage.from_mapping(item) for item in stages_value)
        if tuple(stage.name for stage in stages) != cls.EXPECTED_LIFECYCLE:
            raise SupportReadinessError("lifecycle stages are incomplete or out of order")
        return stages

    @classmethod
    def _patch_targets(cls, value: object) -> tuple[PatchTarget, ...]:
        if not isinstance(value, dict) or set(value) != set(cls.EXPECTED_PATCH_SEVERITIES):
            raise SupportReadinessError("patch_policy must define critical, high, medium and low")
        return tuple(
            PatchTarget.from_mapping(severity, value[severity])
            for severity in cls.EXPECTED_PATCH_SEVERITIES
        )

    @staticmethod
    def _migration(value: object) -> tuple[int, int, bool, bool]:
        if not isinstance(value, dict):
            raise SupportReadinessError("migration_policy must be an object")
        direct = value.get("direct_upgrade_span")
        staged = value.get("staged_upgrade_span")
        if not isinstance(direct, int) or isinstance(direct, bool) or direct != 1:
            raise SupportReadinessError("direct_upgrade_span must be 1")
        if not isinstance(staged, int) or isinstance(staged, bool) or staged < 2:
            raise SupportReadinessError("staged_upgrade_span must be at least 2")
        backup_required = value.get("backup_required") is True
        rollback_required = value.get("rollback_required") is True
        if not backup_required or not rollback_required:
            raise SupportReadinessError("migration policy must require backup and rollback")
        return direct, staged, backup_required, rollback_required

    @classmethod
    def _escalation(cls, value: object) -> tuple[EscalationLevel, ...]:
        if not isinstance(value, list):
            raise SupportReadinessError("escalation_matrix must be an array")
        levels = tuple(EscalationLevel.from_mapping(item) for item in value)
        if tuple(level.level for level in levels) != cls.EXPECTED_ESCALATION:
            raise SupportReadinessError("escalation matrix is incomplete or out of order")
        return levels

    def profile(self, edition: str) -> SupportEditionProfile:
        for profile in self.profiles:
            if profile.edition == edition:
                return profile
        raise SupportReadinessError(f"support profile is missing: {edition}")


class SupportPolicyParser:
    @staticmethod
    def load_json(path: Path) -> dict[str, object]:
        if not path.is_file():
            raise SupportReadinessError(f"support policy is missing: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SupportReadinessError("support policy is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise SupportReadinessError("support policy root must be an object")
        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def string_tuple(value: object, field: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not value:
            raise SupportReadinessError(f"{field} must be a non-empty array")
        result = tuple(str(item).strip() for item in value)
        if any(not item for item in result) or len(result) != len(set(result)):
            raise SupportReadinessError(f"{field} entries must be non-empty and unique")
        return result


class SupportPolicyValidator:
    @classmethod
    def validate_semantics(cls, policy: SupportPolicy) -> None:
        cls._validate_support_order(policy)
        cls._validate_lifecycle(policy)
        cls._validate_patch_order(policy)
        cls._validate_escalation(policy)

    @staticmethod
    def _validate_support_order(policy: SupportPolicy) -> None:
        for severity in sorted(SupportPolicy.EXPECTED_SEVERITIES):
            lite = policy.profile("lite").target(severity)
            pro = policy.profile("pro").target(severity)
            enterprise = policy.profile("enterprise").target(severity)
            if not (
                enterprise.response_minutes <= pro.response_minutes <= lite.response_minutes
                and enterprise.update_minutes <= pro.update_minutes <= lite.update_minutes
                and enterprise.restoration_hours <= pro.restoration_hours <= lite.restoration_hours
            ):
                raise SupportReadinessError(
                    f"support targets must improve from Lite to Pro to Enterprise for {severity}"
                )

    @staticmethod
    def _validate_lifecycle(policy: SupportPolicy) -> None:
        if policy.lifecycle[-1].duration_months != 0:
            raise SupportReadinessError("end-of-life duration must be zero")
        if any(stage.duration_months < 1 for stage in policy.lifecycle[:-1]):
            raise SupportReadinessError("supported lifecycle stages require a positive duration")
        if "feature" not in policy.lifecycle[0].fixes:
            raise SupportReadinessError("active lifecycle stage must permit feature delivery")
        if policy.lifecycle[-1].fixes:
            raise SupportReadinessError("end-of-life stage must not permit fixes")

    @staticmethod
    def _validate_patch_order(policy: SupportPolicy) -> None:
        mitigation = [target.mitigation_hours for target in policy.patch_targets]
        fix_days = [target.fix_days for target in policy.patch_targets]
        if mitigation != sorted(mitigation) or fix_days != sorted(fix_days):
            raise SupportReadinessError("patch deadlines must relax from critical to low")

    @staticmethod
    def _validate_escalation(policy: SupportPolicy) -> None:
        owners = [level.owner for level in policy.escalation]
        if len(owners) != len(set(owners)):
            raise SupportReadinessError("escalation owners must be unique")
        if not any(
            "security" in trigger.lower()
            for level in policy.escalation
            for trigger in level.triggers
        ):
            raise SupportReadinessError("escalation matrix must contain a security trigger")


@dataclass(frozen=True, slots=True)
class SupportReadinessReport:
    generated_at: str
    release_version: str
    policy_sha256: str
    document_sha256: str
    profile_count: int
    severity_count: int
    lifecycle_months: int
    complete: bool
    support_readiness: bool
    sla_defined: bool
    lifecycle_defined: bool
    patch_policy_defined: bool
    migration_policy_defined: bool
    escalation_matrix_defined: bool
    signing_key_sha256: str
    trusted_signing_key: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "report_kind": "support-readiness",
            "epic": "EPIC-1806",
            "generated_at": self.generated_at,
            "release_version": self.release_version,
            "policy_sha256": self.policy_sha256,
            "document_sha256": self.document_sha256,
            "profile_count": self.profile_count,
            "severity_count": self.severity_count,
            "lifecycle_months": self.lifecycle_months,
            "complete": self.complete,
            "support_readiness": self.support_readiness,
            "sla_defined": self.sla_defined,
            "lifecycle_defined": self.lifecycle_defined,
            "patch_policy_defined": self.patch_policy_defined,
            "migration_policy_defined": self.migration_policy_defined,
            "escalation_matrix_defined": self.escalation_matrix_defined,
            "signing_key_sha256": self.signing_key_sha256,
            "trusted_signing_key": self.trusted_signing_key,
            "failures": list(self.failures),
        }


class SupportReadinessService:
    _DEFAULT_POLICY: Final[str] = "docs/release/support-maintenance-policy.json"

    def evaluate(
        self,
        project_root: Path,
        policy_path: Path | None = None,
        signing_material: ReleaseSigningMaterial | None = None,
        now: datetime | None = None,
    ) -> SupportReadinessReport:
        root = project_root.resolve()
        selected_policy = (policy_path or root / self._DEFAULT_POLICY).resolve()
        failures: list[str] = []
        try:
            policy = SupportPolicy.load(selected_policy)
            document_hash = self._documents_hash(root, policy.required_documents)
        except SupportReadinessError as exc:
            failures.append(str(exc))
            return self._failed_report(now, signing_material, failures)
        key_hash = signing_material.public_key_sha256() if signing_material else ""
        trusted = signing_material.trusted if signing_material else False
        if signing_material is None:
            failures.append("support readiness report is not signed")
        report_ok = not failures
        return SupportReadinessReport(
            generated_at=(now or datetime.now(UTC)).isoformat(),
            release_version=__version__,
            policy_sha256=hashlib.sha256(selected_policy.read_bytes()).hexdigest(),
            document_sha256=document_hash,
            profile_count=len(policy.profiles),
            severity_count=len(SupportPolicy.EXPECTED_SEVERITIES),
            lifecycle_months=sum(stage.duration_months for stage in policy.lifecycle),
            complete=report_ok,
            support_readiness=report_ok,
            sla_defined=True,
            lifecycle_defined=True,
            patch_policy_defined=True,
            migration_policy_defined=True,
            escalation_matrix_defined=True,
            signing_key_sha256=key_hash,
            trusted_signing_key=trusted,
            failures=tuple(failures),
        )

    def evaluate_and_write(
        self,
        project_root: Path,
        output_path: Path,
        signing_material: ReleaseSigningMaterial,
        policy_path: Path | None = None,
        now: datetime | None = None,
    ) -> SupportReadinessReport:
        report = self.evaluate(project_root, policy_path, signing_material, now)
        ReleaseFileWriter.write_json_atomic(output_path, report.as_dict())
        payload = output_path.read_bytes()
        signature_path = output_path.with_suffix(output_path.suffix + ".sig")
        public_key_path = output_path.with_suffix(output_path.suffix + ".pub")
        ReleaseFileWriter.write_bytes_atomic(signature_path, signing_material.sign(payload))
        ReleaseFileWriter.write_bytes_atomic(public_key_path, signing_material.public_key_pem())
        try:
            ReleaseSignatureVerifier.verify(public_key_path, output_path, signature_path)
        except ReleasePackagingError as exc:
            raise SupportReadinessError("support readiness signature verification failed") from exc
        return report

    @staticmethod
    def _documents_hash(root: Path, documents: tuple[str, ...]) -> str:
        digest = hashlib.sha256()
        for relative in sorted(documents):
            path = (root / relative).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise SupportReadinessError(
                    f"support document path escapes project root: {relative}"
                ) from exc
            if not path.is_file():
                raise SupportReadinessError(f"support document is missing: {relative}")
            content = path.read_text(encoding="utf-8")
            if len(content.strip()) < 600:
                raise SupportReadinessError(f"support document is not operational: {relative}")
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(content.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    @staticmethod
    def _failed_report(
        now: datetime | None,
        signing_material: ReleaseSigningMaterial | None,
        failures: list[str],
    ) -> SupportReadinessReport:
        return SupportReadinessReport(
            generated_at=(now or datetime.now(UTC)).isoformat(),
            release_version=__version__,
            policy_sha256="",
            document_sha256="",
            profile_count=0,
            severity_count=0,
            lifecycle_months=0,
            complete=False,
            support_readiness=False,
            sla_defined=False,
            lifecycle_defined=False,
            patch_policy_defined=False,
            migration_policy_defined=False,
            escalation_matrix_defined=False,
            signing_key_sha256=(signing_material.public_key_sha256() if signing_material else ""),
            trusted_signing_key=(signing_material.trusted if signing_material else False),
            failures=tuple(failures),
        )
