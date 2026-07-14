from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

from openinfra import __version__


class ScaleoutPromotionError(Exception):
    """Raised when GATE-09 evidence cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class ScaleoutEvidencePolicy:
    identifier: str
    report_kind: str
    max_age_hours: int

    @classmethod
    def from_mapping(cls, value: object) -> ScaleoutEvidencePolicy:
        if not isinstance(value, dict):
            raise ScaleoutPromotionError("scale-out evidence policy entries must be objects")
        identifier = str(value.get("id", "")).strip()
        report_kind = str(value.get("report_kind", "")).strip()
        max_age_hours = value.get("max_age_hours")
        if not identifier or not report_kind:
            raise ScaleoutPromotionError("scale-out evidence policy fields cannot be empty")
        if (
            not isinstance(max_age_hours, int)
            or isinstance(max_age_hours, bool)
            or max_age_hours < 1
        ):
            raise ScaleoutPromotionError(
                f"invalid max_age_hours for scale-out evidence {identifier}"
            )
        return cls(identifier, report_kind, max_age_hours)


@dataclass(frozen=True, slots=True)
class ScaleoutPromotionPolicy:
    schema_version: int
    gate_id: str
    release_id: str
    required_evidence: tuple[ScaleoutEvidencePolicy, ...]

    EXPECTED_EVIDENCE: ClassVar[frozenset[str]] = frozenset(
        {
            "p20-contracts",
            "enterprise-capacity",
            "multisite-chaos",
            "pra-pca",
            "release-security",
            "release-packaging",
            "ga-go-no-go",
        }
    )

    @classmethod
    def load(cls, path: Path) -> ScaleoutPromotionPolicy:
        payload = ScaleoutJson.load_object(path, "scale-out promotion policy")
        if payload.get("schema_version") != 1:
            raise ScaleoutPromotionError("unsupported scale-out promotion policy schema")
        gate_id = str(payload.get("gate_id", "")).strip()
        release_id = str(payload.get("release_id", "")).strip()
        if gate_id != "GATE-09" or release_id != "REL-10":
            raise ScaleoutPromotionError("scale-out policy must target GATE-09 / REL-10")
        raw_evidence = payload.get("required_evidence")
        if not isinstance(raw_evidence, list):
            raise ScaleoutPromotionError("scale-out policy must declare required_evidence")
        evidence = tuple(ScaleoutEvidencePolicy.from_mapping(item) for item in raw_evidence)
        identifiers = [item.identifier for item in evidence]
        if len(identifiers) != len(set(identifiers)):
            raise ScaleoutPromotionError("scale-out evidence identifiers must be unique")
        if set(identifiers) != cls.EXPECTED_EVIDENCE:
            missing = sorted(cls.EXPECTED_EVIDENCE.difference(identifiers))
            extra = sorted(set(identifiers).difference(cls.EXPECTED_EVIDENCE))
            raise ScaleoutPromotionError(
                "scale-out evidence catalog is incomplete or unsupported: "
                f"missing={missing}, extra={extra}"
            )
        return cls(1, gate_id, release_id, evidence)


@dataclass(frozen=True, slots=True)
class ScaleoutEvidenceReference:
    identifier: str
    report_kind: str
    path: str
    sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> ScaleoutEvidenceReference:
        if not isinstance(value, dict):
            raise ScaleoutPromotionError("scale-out evidence references must be objects")
        result = cls(
            identifier=str(value.get("id", "")).strip(),
            report_kind=str(value.get("report_kind", "")).strip(),
            path=str(value.get("path", "")).strip(),
            sha256=str(value.get("sha256", "")).strip(),
        )
        if not result.identifier or not result.report_kind or not result.path:
            raise ScaleoutPromotionError("scale-out evidence reference fields cannot be empty")
        ScaleoutJson.require_sha256(result.sha256, f"evidence {result.identifier}")
        return result

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.identifier,
            "report_kind": self.report_kind,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ScaleoutPromotionManifest:
    schema_version: int
    gate_id: str
    release_version: str
    candidate_id: str
    source_commit: str
    generated_at: datetime
    evidence: tuple[ScaleoutEvidenceReference, ...]

    @classmethod
    def load(cls, path: Path) -> ScaleoutPromotionManifest:
        payload = ScaleoutJson.load_object(path, "scale-out promotion manifest")
        if payload.get("schema_version") != 1:
            raise ScaleoutPromotionError("unsupported scale-out promotion manifest schema")
        gate_id = str(payload.get("gate_id", "")).strip()
        release_version = str(payload.get("release_version", "")).strip()
        candidate_id = str(payload.get("candidate_id", "")).strip()
        source_commit = str(payload.get("source_commit", "")).strip().lower()
        generated_at = ScaleoutTime.parse(payload.get("generated_at"), "manifest generated_at")
        if gate_id != "GATE-09":
            raise ScaleoutPromotionError("scale-out promotion manifest must target GATE-09")
        if release_version != __version__:
            raise ScaleoutPromotionError(
                f"manifest release_version must match OpenInfra {__version__}"
            )
        if not candidate_id or len(candidate_id) > 160:
            raise ScaleoutPromotionError("scale-out candidate_id is invalid")
        if len(source_commit) != 40 or any(
            char not in "0123456789abcdef" for char in source_commit
        ):
            raise ScaleoutPromotionError("scale-out source_commit must be a full lowercase SHA-1")
        raw_evidence = payload.get("evidence")
        if not isinstance(raw_evidence, list):
            raise ScaleoutPromotionError("scale-out promotion manifest must list evidence")
        evidence = tuple(ScaleoutEvidenceReference.from_mapping(item) for item in raw_evidence)
        identifiers = [item.identifier for item in evidence]
        if len(identifiers) != len(set(identifiers)):
            raise ScaleoutPromotionError("scale-out evidence references must be unique")
        if set(identifiers) != ScaleoutPromotionPolicy.EXPECTED_EVIDENCE:
            missing = sorted(ScaleoutPromotionPolicy.EXPECTED_EVIDENCE.difference(identifiers))
            extra = sorted(set(identifiers).difference(ScaleoutPromotionPolicy.EXPECTED_EVIDENCE))
            raise ScaleoutPromotionError(
                f"scale-out manifest evidence mismatch: missing={missing}, extra={extra}"
            )
        return cls(1, gate_id, release_version, candidate_id, source_commit, generated_at, evidence)

    def evidence_by_id(self) -> dict[str, ScaleoutEvidenceReference]:
        return {item.identifier: item for item in self.evidence}

    def canonical_digest(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "gate_id": self.gate_id,
            "release_version": self.release_version,
            "candidate_id": self.candidate_id,
            "source_commit": self.source_commit,
            "generated_at": self.generated_at.isoformat(),
            "evidence": [
                item.as_dict() for item in sorted(self.evidence, key=lambda value: value.identifier)
            ],
        }
        return hashlib.sha256(ScaleoutJson.canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class ScaleoutCriterionResult:
    identifier: str
    report_kind: str
    status: str
    detail: str
    evidence_sha256: str

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.identifier,
            "report_kind": self.report_kind,
            "status": self.status,
            "detail": self.detail,
            "evidence_sha256": self.evidence_sha256,
        }


class ScaleoutEvidenceInspector:
    @classmethod
    def inspect(
        cls,
        policy: ScaleoutEvidencePolicy,
        reference: ScaleoutEvidenceReference,
        evidence_root: Path,
        now: datetime,
        source_commit: str,
    ) -> ScaleoutCriterionResult:
        if reference.report_kind != policy.report_kind:
            return cls.failed(policy, "report kind does not match policy")
        try:
            path = cls.resolve(evidence_root, reference.path)
            raw = path.read_bytes()
        except (OSError, ScaleoutPromotionError) as exc:
            return cls.failed(policy, str(exc))
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != reference.sha256:
            return cls.failed(policy, "evidence SHA-256 mismatch", actual_hash)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return cls.failed(policy, "evidence report is invalid JSON", actual_hash)
        if not isinstance(value, dict):
            return cls.failed(policy, "evidence report root must be an object", actual_hash)
        payload = {str(key): item for key, item in value.items()}
        failures = cls.report_failures(policy.report_kind, payload)
        if policy.report_kind == "ga-go-no-go" and payload.get("source_commit") != source_commit:
            failures.append("GA decision source_commit does not match promotion manifest")
        try:
            generated_at = cls.evidence_time(policy.report_kind, payload)
        except ScaleoutPromotionError as exc:
            failures.append(str(exc))
        else:
            if generated_at > now + timedelta(minutes=5):
                failures.append("evidence timestamp is in the future")
            if now - generated_at > timedelta(hours=policy.max_age_hours):
                failures.append(f"evidence is older than the allowed {policy.max_age_hours} hours")
        if failures:
            return cls.failed(policy, "; ".join(failures), actual_hash)
        return ScaleoutCriterionResult(
            policy.identifier,
            policy.report_kind,
            "passed",
            "required evidence is complete, current and cryptographically pinned",
            actual_hash,
        )

    @staticmethod
    def evidence_time(report_kind: str, payload: dict[str, object]) -> datetime:
        if report_kind == "release-packaging" and "generated_at" not in payload:
            epoch = payload.get("source_date_epoch")
            if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
                raise ScaleoutPromotionError(
                    "release packaging evidence must contain generated_at or source_date_epoch"
                )
            return datetime.fromtimestamp(epoch, tz=UTC)
        return ScaleoutTime.parse(payload.get("generated_at"), "evidence generated_at")

    @classmethod
    def report_failures(cls, report_kind: str, payload: dict[str, object]) -> list[str]:
        failures: list[str] = []
        version_field = "openinfra_version"
        if report_kind in {"p20-contracts", "release-packaging", "ga-go-no-go"}:
            version_field = "release_version"
        if str(payload.get(version_field, "")).strip() != __version__:
            failures.append(f"{version_field} does not match {__version__}")
        if report_kind == "p20-contracts":
            cls.require_true(
                payload,
                failures,
                "complete",
                "pgbouncer_and_read_routing",
                "cursor_pagination_and_streaming",
                "outbox_and_specialized_workers",
                "modular_virtualized_frontend",
                "observability_and_capacity_contracts",
                "runbooks_present",
            )
        elif report_kind == "enterprise-capacity":
            cls.require_true(payload, failures, "capacity_certification")
            if payload.get("status") != "certified" or payload.get("failures") not in ([], ()):
                failures.append("enterprise capacity report is not certified")
        elif report_kind == "multisite-chaos":
            cls.require_true(payload, failures, "multisite_chaos_certification")
            if payload.get("status") not in (None, "passed"):
                failures.append("multisite chaos report is not certified")
            if payload.get("failures") not in (None, [], ()):
                failures.append("multisite chaos report contains failures")
        elif report_kind == "pra-pca":
            cls.require_true(payload, failures, "pra_pca_certification")
            if payload.get("failures") not in ([], ()):
                failures.append("PRA/PCA report contains failures")
        elif report_kind == "release-security":
            cls.require_true(payload, failures, "complete", "release_security_certification")
            if payload.get("offline_mode") is not False or payload.get("failures") not in ([], ()):
                failures.append("release security report is incomplete, offline or failed")
        elif report_kind == "release-packaging":
            cls.require_true(
                payload,
                failures,
                "complete",
                "release_packaging_certification",
                "trusted_signing_key",
            )
            if payload.get("failures") not in ([], ()):
                failures.append("release packaging report contains failures")
        elif report_kind == "ga-go-no-go":
            cls.require_true(payload, failures, "authorized_for_ga", "trusted_signing_key")
            if payload.get("decision") != "GO" or payload.get("refusal_reasons") not in ([], ()):
                failures.append("GA decision is not an unblocked GO")
        else:
            failures.append(f"unsupported scale-out report kind: {report_kind}")
        return failures

    @staticmethod
    def require_true(payload: dict[str, object], failures: list[str], *fields: str) -> None:
        failures.extend(
            f"{field} must be true" for field in fields if payload.get(field) is not True
        )

    @staticmethod
    def resolve(root: Path, relative: str) -> Path:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise ScaleoutPromotionError(
                f"evidence path escapes evidence root: {relative}"
            ) from exc
        if not candidate.is_file():
            raise ScaleoutPromotionError(f"evidence file is missing: {relative}")
        return candidate

    @staticmethod
    def failed(
        policy: ScaleoutEvidencePolicy,
        detail: str,
        evidence_sha256: str = "",
    ) -> ScaleoutCriterionResult:
        return ScaleoutCriterionResult(
            policy.identifier,
            policy.report_kind,
            "failed",
            detail,
            evidence_sha256,
        )


class ScaleoutPromotionCertification:
    @classmethod
    def evaluate(
        cls,
        policy: ScaleoutPromotionPolicy,
        manifest: ScaleoutPromotionManifest,
        evidence_root: Path,
        now: datetime | None = None,
    ) -> dict[str, object]:
        decision_time = (now or datetime.now(UTC)).astimezone(UTC)
        blockers: list[str] = []
        if manifest.generated_at > decision_time + timedelta(minutes=5):
            blockers.append("promotion manifest timestamp is in the future")
        if decision_time - manifest.generated_at > timedelta(hours=24):
            blockers.append("promotion manifest is older than 24 hours")
        references = manifest.evidence_by_id()
        criteria: list[ScaleoutCriterionResult] = []
        for evidence_policy in policy.required_evidence:
            reference = references.get(evidence_policy.identifier)
            if reference is None:
                criteria.append(
                    ScaleoutCriterionResult(
                        evidence_policy.identifier,
                        evidence_policy.report_kind,
                        "failed",
                        "required evidence reference is missing",
                        "",
                    )
                )
                continue
            criteria.append(
                ScaleoutEvidenceInspector.inspect(
                    evidence_policy,
                    reference,
                    evidence_root,
                    decision_time,
                    manifest.source_commit,
                )
            )
        blockers.extend(
            f"{criterion.identifier}: {criterion.detail}"
            for criterion in criteria
            if not criterion.passed
        )
        certified = not blockers
        return {
            "schema_version": 1,
            "report_kind": "enterprise-scaleout-promotion",
            "openinfra_version": __version__,
            "release_version": __version__,
            "gate_id": policy.gate_id,
            "release_id": policy.release_id,
            "candidate_id": manifest.candidate_id,
            "source_commit": manifest.source_commit,
            "generated_at": decision_time.isoformat(),
            "manifest_sha256": manifest.canonical_digest(),
            "criteria": [criterion.as_dict() for criterion in criteria],
            "blockers": blockers,
            "status": "certified" if certified else "rejected",
            "scaleout_promotion_certification": certified,
            "authorized_for_enterprise_scaleout": certified,
        }


class ScaleoutTime:
    @staticmethod
    def parse(value: object, label: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ScaleoutPromotionError(f"{label} is required")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ScaleoutPromotionError(f"{label} must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ScaleoutPromotionError(f"{label} must include a timezone")
        return parsed.astimezone(UTC)


class ScaleoutJson:
    @staticmethod
    def load_object(path: Path, label: str) -> dict[str, object]:
        if not path.is_file():
            raise ScaleoutPromotionError(f"{label} is missing: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ScaleoutPromotionError(f"{label} is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ScaleoutPromotionError(f"{label} root must be an object")
        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def require_sha256(value: str, label: str) -> None:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ScaleoutPromotionError(f"{label} SHA-256 must be canonical lowercase hex")

    @staticmethod
    def canonical_bytes(payload: dict[str, object]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
