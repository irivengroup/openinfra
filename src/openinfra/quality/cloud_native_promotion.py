from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

from openinfra import __version__


class CloudNativePromotionError(Exception):
    """Raised when GATE-10 evidence cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class CloudNativeEvidencePolicy:
    identifier: str
    report_kind: str
    max_age_hours: int

    @classmethod
    def from_mapping(cls, value: object) -> CloudNativeEvidencePolicy:
        if not isinstance(value, dict):
            raise CloudNativePromotionError("cloud-native evidence policy entries must be objects")
        identifier = str(value.get("id", "")).strip()
        report_kind = str(value.get("report_kind", "")).strip()
        max_age_hours = value.get("max_age_hours")
        if not identifier or not report_kind:
            raise CloudNativePromotionError("cloud-native evidence policy fields cannot be empty")
        if (
            not isinstance(max_age_hours, int)
            or isinstance(max_age_hours, bool)
            or max_age_hours < 1
        ):
            raise CloudNativePromotionError(
                f"invalid max_age_hours for cloud-native evidence {identifier}"
            )
        return cls(identifier, report_kind, max_age_hours)


@dataclass(frozen=True, slots=True)
class CloudNativePromotionPolicy:
    schema_version: int
    gate_id: str
    release_id: str
    required_evidence: tuple[CloudNativeEvidencePolicy, ...]

    EXPECTED_EVIDENCE: ClassVar[dict[str, str]] = {
        "epic-2101-topology": "kubernetes-cloud-native-topology-contract",
        "epic-2102-exposure": "kubernetes-cloud-native-exposure-contract",
        "epic-2103-security": "kubernetes-cloud-native-security-contract",
        "epic-2104-gitops": "kubernetes-gitops-drift-contract",
        "epic-2105-capacity": "kubernetes-capacity-contract",
        "epic-2106-runtime": "cloud-native-runtime-qualification",
        "epic-2106-contract": "cloud-native-qualification-contract",
    }

    @classmethod
    def load(cls, path: Path) -> CloudNativePromotionPolicy:
        payload = CloudNativeJson.load_object(path, "cloud-native promotion policy")
        if payload.get("schema_version") != 1:
            raise CloudNativePromotionError("unsupported cloud-native promotion policy schema")
        gate_id = str(payload.get("gate_id", "")).strip()
        release_id = str(payload.get("release_id", "")).strip()
        if gate_id != "GATE-10" or release_id != "REL-11":
            raise CloudNativePromotionError("cloud-native policy must target GATE-10 / REL-11")
        raw_evidence = payload.get("required_evidence")
        if not isinstance(raw_evidence, list):
            raise CloudNativePromotionError("cloud-native policy must declare required_evidence")
        evidence = tuple(CloudNativeEvidencePolicy.from_mapping(item) for item in raw_evidence)
        identifiers = [item.identifier for item in evidence]
        if len(identifiers) != len(set(identifiers)):
            raise CloudNativePromotionError("cloud-native evidence identifiers must be unique")
        actual = {item.identifier: item.report_kind for item in evidence}
        if actual != cls.EXPECTED_EVIDENCE:
            missing = sorted(set(cls.EXPECTED_EVIDENCE).difference(actual))
            extra = sorted(set(actual).difference(cls.EXPECTED_EVIDENCE))
            mismatched = sorted(
                identifier
                for identifier in set(actual).intersection(cls.EXPECTED_EVIDENCE)
                if actual[identifier] != cls.EXPECTED_EVIDENCE[identifier]
            )
            raise CloudNativePromotionError(
                "cloud-native evidence catalog is incomplete or unsupported: "
                f"missing={missing}, extra={extra}, mismatched={mismatched}"
            )
        return cls(1, gate_id, release_id, evidence)


@dataclass(frozen=True, slots=True)
class CloudNativeEvidenceReference:
    identifier: str
    report_kind: str
    path: str
    sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> CloudNativeEvidenceReference:
        if not isinstance(value, dict):
            raise CloudNativePromotionError("cloud-native evidence references must be objects")
        result = cls(
            identifier=str(value.get("id", "")).strip(),
            report_kind=str(value.get("report_kind", "")).strip(),
            path=str(value.get("path", "")).strip(),
            sha256=str(value.get("sha256", "")).strip(),
        )
        if not result.identifier or not result.report_kind or not result.path:
            raise CloudNativePromotionError("cloud-native evidence fields cannot be empty")
        CloudNativeJson.require_sha256(result.sha256, f"evidence {result.identifier}")
        return result

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.identifier,
            "report_kind": self.report_kind,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class CloudNativePromotionManifest:
    schema_version: int
    gate_id: str
    release_version: str
    candidate_id: str
    source_commit: str
    generated_at: datetime
    evidence: tuple[CloudNativeEvidenceReference, ...]

    @classmethod
    def load(cls, path: Path) -> CloudNativePromotionManifest:
        payload = CloudNativeJson.load_object(path, "cloud-native promotion manifest")
        if payload.get("schema_version") != 1:
            raise CloudNativePromotionError("unsupported cloud-native promotion manifest schema")
        gate_id = str(payload.get("gate_id", "")).strip()
        release_version = str(payload.get("release_version", "")).strip()
        candidate_id = str(payload.get("candidate_id", "")).strip()
        source_commit = str(payload.get("source_commit", "")).strip().lower()
        generated_at = CloudNativeTime.parse(payload.get("generated_at"), "manifest generated_at")
        if gate_id != "GATE-10":
            raise CloudNativePromotionError("cloud-native promotion manifest must target GATE-10")
        if release_version != __version__:
            raise CloudNativePromotionError(
                f"manifest release_version must match OpenInfra {__version__}"
            )
        if not candidate_id or len(candidate_id) > 160:
            raise CloudNativePromotionError("cloud-native candidate_id is invalid")
        CloudNativeJson.require_sha1(source_commit, "cloud-native source_commit")
        raw_evidence = payload.get("evidence")
        if not isinstance(raw_evidence, list):
            raise CloudNativePromotionError("cloud-native promotion manifest must list evidence")
        evidence = tuple(CloudNativeEvidenceReference.from_mapping(item) for item in raw_evidence)
        identifiers = [item.identifier for item in evidence]
        if len(identifiers) != len(set(identifiers)):
            raise CloudNativePromotionError("cloud-native evidence references must be unique")
        actual = {item.identifier: item.report_kind for item in evidence}
        if actual != CloudNativePromotionPolicy.EXPECTED_EVIDENCE:
            missing = sorted(set(CloudNativePromotionPolicy.EXPECTED_EVIDENCE).difference(actual))
            extra = sorted(set(actual).difference(CloudNativePromotionPolicy.EXPECTED_EVIDENCE))
            mismatched = sorted(
                identifier
                for identifier in set(actual).intersection(
                    CloudNativePromotionPolicy.EXPECTED_EVIDENCE
                )
                if actual[identifier] != CloudNativePromotionPolicy.EXPECTED_EVIDENCE[identifier]
            )
            raise CloudNativePromotionError(
                "cloud-native manifest evidence mismatch: "
                f"missing={missing}, extra={extra}, mismatched={mismatched}"
            )
        return cls(1, gate_id, release_version, candidate_id, source_commit, generated_at, evidence)

    def evidence_by_id(self) -> dict[str, CloudNativeEvidenceReference]:
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
        return hashlib.sha256(CloudNativeJson.canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class CloudNativeCriterionResult:
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


class CloudNativeEvidenceInspector:
    @classmethod
    def inspect(
        cls,
        policy: CloudNativeEvidencePolicy,
        reference: CloudNativeEvidenceReference,
        evidence_root: Path,
        now: datetime,
    ) -> CloudNativeCriterionResult:
        if reference.report_kind != policy.report_kind:
            return cls.failed(policy, "report kind does not match policy")
        try:
            path = cls.resolve(evidence_root, reference.path)
            raw = path.read_bytes()
        except (OSError, CloudNativePromotionError) as exc:
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
        try:
            generated_at = CloudNativeTime.parse(
                payload.get("generated_at"), "evidence generated_at"
            )
        except CloudNativePromotionError as exc:
            failures.append(str(exc))
        else:
            if generated_at > now + timedelta(minutes=5):
                failures.append("evidence timestamp is in the future")
            if now - generated_at > timedelta(hours=policy.max_age_hours):
                failures.append(f"evidence is older than the allowed {policy.max_age_hours} hours")
        if failures:
            return cls.failed(policy, "; ".join(failures), actual_hash)
        return CloudNativeCriterionResult(
            policy.identifier,
            policy.report_kind,
            "passed",
            "required evidence is complete, current and cryptographically pinned",
            actual_hash,
        )

    @classmethod
    def report_failures(cls, report_kind: str, payload: dict[str, object]) -> list[str]:
        failures: list[str] = []
        if str(payload.get("release_version", "")).strip() != __version__:
            failures.append(f"release_version does not match {__version__}")
        if payload.get("phase") != "P21" or payload.get("release") != "REL-11":
            failures.append("evidence must target P21 / REL-11")
        if report_kind == "kubernetes-cloud-native-topology-contract":
            cls.require_epic(payload, failures, "EPIC-2101")
            cls.require_true(
                payload,
                failures,
                "complete",
                "api_cli_web_parity",
                "physical_mapping",
                "secret_values_rejected",
            )
            if cls.integer(payload, "max_resources_per_snapshot") < 50_000:
                failures.append("topology limit must support at least 50000 resources per snapshot")
        elif report_kind == "kubernetes-cloud-native-exposure-contract":
            cls.require_epic(payload, failures, "EPIC-2102")
            cls.require_true(
                payload,
                failures,
                "complete",
                "network_flow_correlation",
                "rsot_dependency_correlation",
                "read_only_projection",
                "api_cli_web_parity",
            )
        elif report_kind == "kubernetes-cloud-native-security-contract":
            cls.require_epic(payload, failures, "EPIC-2103")
            cls.require_true(
                payload,
                failures,
                "complete",
                "image_sbom_correlation",
                "contextual_vulnerability_findings",
                "certificate_correlation",
                "masked_secret_references",
                "legacy_snapshot_fingerprint_compatibility",
                "api_cli_web_parity",
            )
            if payload.get("secret_material_ingestion") is not False:
                failures.append("secret_material_ingestion must be false")
        elif report_kind == "kubernetes-gitops-drift-contract":
            cls.require_epic(payload, failures, "EPIC-2104")
            cls.require_true(
                payload,
                failures,
                "complete",
                "immutable_expected_state",
                "immutable_observed_state",
                "deterministic_drift",
                "audit_enabled",
                "transactional_outbox",
                "api_cli_web_parity",
            )
            if payload.get("automatic_remediation") is not False:
                failures.append("automatic_remediation must be false")
        elif report_kind == "kubernetes-capacity-contract":
            cls.require_epic(payload, failures, "EPIC-2105")
            cls.require_true(
                payload,
                failures,
                "complete",
                "cluster_capacity",
                "namespace_capacity",
                "bounded_trends",
                "alerts",
                "json_csv_exports",
                "api_cli_web_parity",
            )
            if cls.integer(payload, "max_trend_resources") < 1_000_000:
                failures.append("capacity trend must support at least 1000000 resources")
        elif report_kind == "cloud-native-runtime-qualification":
            cls.require_epic(payload, failures, "EPIC-2106")
            cls.require_true(
                payload,
                failures,
                "complete",
                "multi_cluster_verified",
                "max_snapshot_size_verified",
                "deterministic_fingerprints",
                "physical_mapping_verified",
                "capacity_read_model_verified",
                "secrets_rejected",
                "cross_namespace_references_rejected",
                "orphan_physical_paths_rejected",
                "performance_budget_met",
            )
            if payload.get("gate_id") != "GATE-10" or payload.get("status") != "passed":
                failures.append("runtime qualification is not a passed GATE-10 report")
            if payload.get("failures") not in ([], ()):
                failures.append("runtime qualification contains failures")
            if cls.integer(payload, "qualified_cluster_count") < 3:
                failures.append("runtime qualification must validate at least three clusters")
            if cls.integer(payload, "max_resources_per_snapshot") != 50_000:
                failures.append("runtime qualification must exercise 50000 resources per snapshot")
        elif report_kind == "cloud-native-qualification-contract":
            cls.require_epic(payload, failures, "EPIC-2106")
            cls.require_true(
                payload,
                failures,
                "complete",
                "all_epic_validators_present",
                "runtime_benchmark_present",
                "immutable_evidence",
                "path_traversal_protection",
                "freshness_enforced",
                "ci_gate_blocking",
                "runbook_present",
                "packaging_verified",
                "no_new_migration",
            )
            if payload.get("gate_id") != "GATE-10":
                failures.append("qualification contract must target GATE-10")
        else:
            failures.append(f"unsupported cloud-native report kind: {report_kind}")
        return failures

    @staticmethod
    def require_epic(payload: dict[str, object], failures: list[str], epic: str) -> None:
        if payload.get("epic") != epic:
            failures.append(f"evidence must target {epic}")

    @staticmethod
    def require_true(payload: dict[str, object], failures: list[str], *fields: str) -> None:
        failures.extend(
            f"{field} must be true" for field in fields if payload.get(field) is not True
        )

    @staticmethod
    def integer(payload: dict[str, object], field: str) -> int:
        value = payload.get(field)
        return value if isinstance(value, int) and not isinstance(value, bool) else -1

    @staticmethod
    def resolve(root: Path, relative: str) -> Path:
        root_resolved = root.resolve()
        candidate = (root_resolved / relative).resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError as exc:
            raise CloudNativePromotionError(
                f"evidence path escapes evidence root: {relative}"
            ) from exc
        if not candidate.is_file():
            raise CloudNativePromotionError(f"evidence file is missing: {relative}")
        return candidate

    @staticmethod
    def failed(
        policy: CloudNativeEvidencePolicy,
        detail: str,
        evidence_sha256: str = "",
    ) -> CloudNativeCriterionResult:
        return CloudNativeCriterionResult(
            policy.identifier,
            policy.report_kind,
            "failed",
            detail,
            evidence_sha256,
        )


class CloudNativePromotionCertification:
    @classmethod
    def evaluate(
        cls,
        policy: CloudNativePromotionPolicy,
        manifest: CloudNativePromotionManifest,
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
        criteria: list[CloudNativeCriterionResult] = []
        for evidence_policy in policy.required_evidence:
            reference = references.get(evidence_policy.identifier)
            if reference is None:
                criteria.append(
                    CloudNativeCriterionResult(
                        evidence_policy.identifier,
                        evidence_policy.report_kind,
                        "failed",
                        "required evidence reference is missing",
                        "",
                    )
                )
                continue
            criteria.append(
                CloudNativeEvidenceInspector.inspect(
                    evidence_policy,
                    reference,
                    evidence_root,
                    decision_time,
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
            "report_kind": "cloud-native-promotion",
            "openinfra_version": __version__,
            "release_version": __version__,
            "phase": "P21",
            "epic": "EPIC-2106",
            "gate_id": policy.gate_id,
            "release_id": policy.release_id,
            "candidate_id": manifest.candidate_id,
            "source_commit": manifest.source_commit,
            "generated_at": decision_time.isoformat(),
            "manifest_sha256": manifest.canonical_digest(),
            "criteria": [criterion.as_dict() for criterion in criteria],
            "blockers": blockers,
            "status": "certified" if certified else "rejected",
            "cloud_native_promotion_certification": certified,
            "authorized_for_cloud_native_release": certified,
        }


class CloudNativeTime:
    @staticmethod
    def parse(value: object, label: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise CloudNativePromotionError(f"{label} is required")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CloudNativePromotionError(f"{label} must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise CloudNativePromotionError(f"{label} must include a timezone")
        return parsed.astimezone(UTC)


class CloudNativeJson:
    @staticmethod
    def load_object(path: Path, label: str) -> dict[str, object]:
        if not path.is_file():
            raise CloudNativePromotionError(f"{label} is missing: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CloudNativePromotionError(f"{label} is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise CloudNativePromotionError(f"{label} root must be an object")
        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def require_sha1(value: str, label: str) -> None:
        if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
            raise CloudNativePromotionError(f"{label} must be a full lowercase SHA-1")

    @staticmethod
    def require_sha256(value: str, label: str) -> None:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise CloudNativePromotionError(f"{label} SHA-256 must be canonical lowercase hex")

    @staticmethod
    def canonical_bytes(payload: dict[str, object]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
