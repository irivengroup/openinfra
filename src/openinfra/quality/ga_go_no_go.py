from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar, Final

from openinfra import __version__
from openinfra.quality.release_packaging import (
    ReleaseFileWriter,
    ReleasePackagingError,
    ReleaseSignatureVerifier,
    ReleaseSigningMaterial,
)


class GaGoNoGoError(Exception):
    """Raised when the GA promotion decision cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class GaEvidencePolicy:
    identifier: str
    report_kind: str
    category: str
    max_age_days: int

    @classmethod
    def from_mapping(cls, value: object) -> GaEvidencePolicy:
        if not isinstance(value, dict):
            raise GaGoNoGoError("GA evidence policy entries must be objects")
        identifier = str(value.get("id", "")).strip()
        report_kind = str(value.get("report_kind", "")).strip()
        category = str(value.get("category", "")).strip()
        max_age_days = value.get("max_age_days")
        if not identifier or not report_kind or not category:
            raise GaGoNoGoError("GA evidence policy fields cannot be empty")
        if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or max_age_days < 1:
            raise GaGoNoGoError(f"invalid max_age_days for GA evidence {identifier}")
        return cls(identifier, report_kind, category, max_age_days)


@dataclass(frozen=True, slots=True)
class GaGoNoGoPolicy:
    schema_version: int
    gate_id: str
    epic: str
    required_evidence: tuple[GaEvidencePolicy, ...]
    required_approval_roles: tuple[str, ...]
    blocking_risk_severities: frozenset[str]

    _EXPECTED_EVIDENCE: ClassVar[frozenset[str]] = frozenset(
        {
            "technical-validation",
            "enterprise-capacity",
            "release-security",
            "release-packaging",
            "ga-documentation",
            "operations-readiness",
            "support-readiness",
            "business-readiness",
        }
    )

    @classmethod
    def load(cls, path: Path) -> GaGoNoGoPolicy:
        payload = cls._load_json(path, "GA Go/No-Go policy")
        if payload.get("schema_version") != 1:
            raise GaGoNoGoError("unsupported GA Go/No-Go policy schema")
        evidence_value = payload.get("required_evidence")
        if not isinstance(evidence_value, list):
            raise GaGoNoGoError("GA policy must declare required_evidence")
        evidence = tuple(GaEvidencePolicy.from_mapping(item) for item in evidence_value)
        identifiers = [item.identifier for item in evidence]
        if len(identifiers) != len(set(identifiers)):
            raise GaGoNoGoError("GA evidence identifiers must be unique")
        if set(identifiers) != cls._EXPECTED_EVIDENCE:
            missing = sorted(cls._EXPECTED_EVIDENCE.difference(identifiers))
            extra = sorted(set(identifiers).difference(cls._EXPECTED_EVIDENCE))
            raise GaGoNoGoError(
                "GA evidence catalog is incomplete or unsupported: "
                f"missing={missing}, extra={extra}"
            )
        roles = cls._string_tuple(payload.get("required_approval_roles"), "approval roles")
        severities = frozenset(
            value.lower()
            for value in cls._string_tuple(
                payload.get("blocking_risk_severities"), "blocking risk severities"
            )
        )
        gate_id = str(payload.get("gate_id", "")).strip()
        epic = str(payload.get("epic", "")).strip()
        if gate_id != "GATE-07" or epic != "EPIC-1805":
            raise GaGoNoGoError("GA policy must target GATE-07 / EPIC-1805")
        return cls(1, gate_id, epic, evidence, roles, severities)

    @staticmethod
    def _load_json(path: Path, label: str) -> dict[str, object]:
        if not path.is_file():
            raise GaGoNoGoError(f"{label} is missing: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GaGoNoGoError(f"{label} is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GaGoNoGoError(f"{label} root must be an object")
        return {str(key): value for key, value in payload.items()}

    @staticmethod
    def _string_tuple(value: object, label: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not value:
            raise GaGoNoGoError(f"GA policy must list {label}")
        result = tuple(str(item).strip() for item in value)
        if any(not item for item in result) or len(result) != len(set(result)):
            raise GaGoNoGoError(f"GA policy {label} must be non-empty and unique")
        return result


@dataclass(frozen=True, slots=True)
class GaTrustPolicy:
    approval_keys: dict[str, frozenset[str]]
    decision_keys: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> GaTrustPolicy:
        payload = GaGoNoGoPolicy._load_json(path, "GA trust policy")
        if payload.get("schema_version") != 1:
            raise GaGoNoGoError("unsupported GA trust policy schema")
        raw_approvals = payload.get("approval_keys")
        if not isinstance(raw_approvals, dict):
            raise GaGoNoGoError("GA trust policy must declare approval_keys")
        approval_keys: dict[str, frozenset[str]] = {}
        for role, keys in raw_approvals.items():
            approval_keys[str(role)] = cls._fingerprints(keys, f"approval role {role}")
        decision_keys = cls._fingerprints(payload.get("decision_keys"), "decision keys")
        return cls(approval_keys, decision_keys)

    @staticmethod
    def _fingerprints(value: object, label: str) -> frozenset[str]:
        if not isinstance(value, list):
            raise GaGoNoGoError(f"GA trust policy {label} must be an array")
        result = frozenset(str(item).strip().lower() for item in value)
        if any(
            len(item) != 64 or any(char not in "0123456789abcdef" for char in item)
            for item in result
        ):
            raise GaGoNoGoError(f"GA trust policy {label} contains an invalid SHA-256 fingerprint")
        return result


@dataclass(frozen=True, slots=True)
class GaEvidenceReference:
    identifier: str
    report_kind: str
    path: str
    sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> GaEvidenceReference:
        if not isinstance(value, dict):
            raise GaGoNoGoError("GA evidence references must be objects")
        result = cls(
            identifier=str(value.get("id", "")).strip(),
            report_kind=str(value.get("report_kind", "")).strip(),
            path=str(value.get("path", "")).strip(),
            sha256=str(value.get("sha256", "")).strip().lower(),
        )
        if not result.identifier or not result.report_kind or not result.path:
            raise GaGoNoGoError("GA evidence reference fields cannot be empty")
        if len(result.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in result.sha256
        ):
            raise GaGoNoGoError(f"invalid evidence SHA-256 for {result.identifier}")
        return result


@dataclass(frozen=True, slots=True)
class GaApprovalReference:
    role: str
    statement_path: str
    signature_path: str
    public_key_path: str
    public_key_sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> GaApprovalReference:
        if not isinstance(value, dict):
            raise GaGoNoGoError("GA approval references must be objects")
        result = cls(
            role=str(value.get("role", "")).strip(),
            statement_path=str(value.get("statement_path", "")).strip(),
            signature_path=str(value.get("signature_path", "")).strip(),
            public_key_path=str(value.get("public_key_path", "")).strip(),
            public_key_sha256=str(value.get("public_key_sha256", "")).strip().lower(),
        )
        if not all(
            (result.role, result.statement_path, result.signature_path, result.public_key_path)
        ):
            raise GaGoNoGoError("GA approval reference fields cannot be empty")
        if len(result.public_key_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in result.public_key_sha256
        ):
            raise GaGoNoGoError(f"invalid approval public key fingerprint for {result.role}")
        return result


@dataclass(frozen=True, slots=True)
class GaRiskRecord:
    identifier: str
    severity: str
    status: str
    owner: str
    mitigation: str
    accepted_by: str
    expires_at: str

    @classmethod
    def from_mapping(cls, value: object) -> GaRiskRecord:
        if not isinstance(value, dict):
            raise GaGoNoGoError("GA risk entries must be objects")
        result = cls(
            identifier=str(value.get("id", "")).strip(),
            severity=str(value.get("severity", "")).strip().lower(),
            status=str(value.get("status", "")).strip().lower(),
            owner=str(value.get("owner", "")).strip(),
            mitigation=str(value.get("mitigation", "")).strip(),
            accepted_by=str(value.get("accepted_by", "")).strip(),
            expires_at=str(value.get("expires_at", "")).strip(),
        )
        if not result.identifier or not result.severity or not result.status or not result.owner:
            raise GaGoNoGoError("GA risk identifiers, severity, status and owner are required")
        if result.status not in {"open", "mitigated", "accepted", "closed"}:
            raise GaGoNoGoError(f"unsupported GA risk status: {result.status}")
        return result


@dataclass(frozen=True, slots=True)
class GaCandidateManifest:
    release_version: str
    candidate_id: str
    source_commit: str
    generated_at: str
    evidence: tuple[GaEvidenceReference, ...]
    approvals: tuple[GaApprovalReference, ...]
    risks: tuple[GaRiskRecord, ...]

    @classmethod
    def load(cls, path: Path) -> GaCandidateManifest:
        payload = GaGoNoGoPolicy._load_json(path, "GA candidate manifest")
        if payload.get("schema_version") != 1:
            raise GaGoNoGoError("unsupported GA candidate manifest schema")
        evidence_value = payload.get("evidence", [])
        approvals_value = payload.get("approvals", [])
        risks_value = payload.get("risks", [])
        if not isinstance(evidence_value, list) or not isinstance(approvals_value, list):
            raise GaGoNoGoError("GA candidate evidence and approvals must be arrays")
        if not isinstance(risks_value, list):
            raise GaGoNoGoError("GA candidate risks must be an array")
        result = cls(
            release_version=str(payload.get("release_version", "")).strip(),
            candidate_id=str(payload.get("candidate_id", "")).strip(),
            source_commit=str(payload.get("source_commit", "")).strip().lower(),
            generated_at=str(payload.get("generated_at", "")).strip(),
            evidence=tuple(GaEvidenceReference.from_mapping(item) for item in evidence_value),
            approvals=tuple(GaApprovalReference.from_mapping(item) for item in approvals_value),
            risks=tuple(GaRiskRecord.from_mapping(item) for item in risks_value),
        )
        if result.release_version != __version__:
            raise GaGoNoGoError(
                f"candidate release {result.release_version} differs from package {__version__}"
            )
        if not result.candidate_id or len(result.source_commit) not in {40, 64}:
            raise GaGoNoGoError("candidate_id and a 40/64-character source_commit are required")
        if any(char not in "0123456789abcdef" for char in result.source_commit):
            raise GaGoNoGoError("source_commit must be hexadecimal")
        GaTimeParser.parse(result.generated_at, "candidate generated_at")
        if len({item.identifier for item in result.evidence}) != len(result.evidence):
            raise GaGoNoGoError("candidate evidence identifiers must be unique")
        if len({item.role for item in result.approvals}) != len(result.approvals):
            raise GaGoNoGoError("candidate approval roles must be unique")
        if len({item.identifier for item in result.risks}) != len(result.risks):
            raise GaGoNoGoError("candidate risk identifiers must be unique")
        return result


class GaTimeParser:
    @classmethod
    def parse(cls, value: object, label: str) -> datetime:
        text = str(value or "").strip()
        if not text:
            raise GaGoNoGoError(f"{label} is required")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GaGoNoGoError(f"{label} is not a valid ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise GaGoNoGoError(f"{label} must include a timezone")
        return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class GaCriterionResult:
    identifier: str
    category: str
    status: str
    detail: str
    evidence_sha256: str

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "category": self.category,
            "status": self.status,
            "detail": self.detail,
            "evidence_sha256": self.evidence_sha256,
        }


class GaEvidenceInspector:
    _BOOLEAN_FIELDS: Final[dict[str, tuple[str, ...]]] = {
        "operations-readiness": (
            "complete",
            "operations_readiness",
            "pitr_tested",
            "failover_tested",
            "backup_restore_tested",
            "chaos_tested",
            "runbooks_validated",
        ),
        "support-readiness": (
            "complete",
            "support_readiness",
            "sla_defined",
            "lifecycle_defined",
            "patch_policy_defined",
            "migration_policy_defined",
            "escalation_matrix_defined",
        ),
        "business-readiness": (
            "complete",
            "business_readiness",
            "commercial_approved",
            "legal_approved",
            "licensing_approved",
            "release_notes_approved",
            "known_risks_accepted",
        ),
    }

    @classmethod
    def inspect(
        cls,
        policy: GaEvidencePolicy,
        reference: GaEvidenceReference,
        evidence_root: Path,
        now: datetime,
    ) -> GaCriterionResult:
        if reference.report_kind != policy.report_kind:
            return cls._failed(policy, "report kind does not match policy")
        try:
            path = cls._resolve(evidence_root, reference.path)
            payload_bytes = path.read_bytes()
        except (OSError, GaGoNoGoError) as exc:
            return cls._failed(policy, str(exc))
        actual_hash = hashlib.sha256(payload_bytes).hexdigest()
        if actual_hash != reference.sha256:
            return cls._failed(policy, "evidence SHA-256 mismatch")
        try:
            payload_value = json.loads(payload_bytes)
        except json.JSONDecodeError:
            return cls._failed(policy, "evidence report is invalid JSON", actual_hash)
        if not isinstance(payload_value, dict):
            return cls._failed(policy, "evidence report root must be an object", actual_hash)
        payload = {str(key): value for key, value in payload_value.items()}
        failures = cls._report_failures(policy.report_kind, payload)
        try:
            generated_at = GaTimeParser.parse(payload.get("generated_at"), "evidence generated_at")
        except GaGoNoGoError as exc:
            failures.append(str(exc))
        else:
            if generated_at > now + timedelta(minutes=5):
                failures.append("evidence timestamp is in the future")
            if now - generated_at > timedelta(days=policy.max_age_days):
                failures.append(f"evidence is older than the allowed {policy.max_age_days} days")
        if failures:
            return cls._failed(policy, "; ".join(failures), actual_hash)
        return GaCriterionResult(
            policy.identifier,
            policy.category,
            "passed",
            "required evidence is complete, current and valid",
            actual_hash,
        )

    @classmethod
    def _report_failures(cls, report_kind: str, payload: dict[str, object]) -> list[str]:
        failures: list[str] = []
        version_field = (
            "release_version" if report_kind == "release-packaging" else "openinfra_version"
        )
        if report_kind == "ga-documentation":
            version_field = "version"
        if report_kind in cls._BOOLEAN_FIELDS:
            version_field = "release_version"
        if str(payload.get(version_field, "")).strip() != __version__:
            failures.append(f"{version_field} does not match {__version__}")
        if report_kind == "technical-validation":
            cls._require_true(payload, failures, "complete", "passed")
            coverage = payload.get("coverage_percent")
            if not isinstance(coverage, int | float) or isinstance(coverage, bool) or coverage < 98:
                failures.append("coverage_percent must be at least 98")
            if payload.get("failed_tests") != 0:
                failures.append("failed_tests must be zero")
        elif report_kind == "enterprise-capacity":
            cls._require_true(payload, failures, "capacity_certification")
            if payload.get("status") != "certified" or payload.get("failures") not in ([], ()):
                failures.append("enterprise capacity report is not certified")
        elif report_kind == "release-security":
            cls._require_true(payload, failures, "complete", "release_security_certification")
            if payload.get("offline_mode") is not False or payload.get("failures") not in ([], ()):
                failures.append("release security report is incomplete, offline or failed")
        elif report_kind == "release-packaging":
            cls._require_true(
                payload,
                failures,
                "complete",
                "release_packaging_certification",
                "trusted_signing_key",
            )
            if payload.get("failures") not in ([], ()):
                failures.append("release packaging report contains failures")
        elif report_kind == "ga-documentation":
            cls._require_true(payload, failures, "passed")
            if payload.get("epic") != "EPIC-1804":
                failures.append("GA documentation report does not target EPIC-1804")
        elif report_kind in cls._BOOLEAN_FIELDS:
            cls._require_true(payload, failures, *cls._BOOLEAN_FIELDS[report_kind])
        else:
            failures.append(f"unsupported GA report kind: {report_kind}")
        return failures

    @staticmethod
    def _require_true(payload: dict[str, object], failures: list[str], *fields: str) -> None:
        failures.extend(
            f"{field} must be true" for field in fields if payload.get(field) is not True
        )

    @staticmethod
    def _resolve(root: Path, relative: str) -> Path:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise GaGoNoGoError(f"evidence path escapes evidence root: {relative}") from exc
        if not candidate.is_file():
            raise GaGoNoGoError(f"evidence file is missing: {relative}")
        return candidate

    @staticmethod
    def _failed(
        policy: GaEvidencePolicy, detail: str, evidence_sha256: str = ""
    ) -> GaCriterionResult:
        return GaCriterionResult(
            policy.identifier,
            policy.category,
            "failed",
            detail,
            evidence_sha256,
        )


@dataclass(frozen=True, slots=True)
class GaApprovalResult:
    role: str
    status: str
    detail: str
    approver: str
    public_key_sha256: str

    @property
    def passed(self) -> bool:
        return self.status == "approved"

    def as_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "status": self.status,
            "detail": self.detail,
            "approver": self.approver,
            "public_key_sha256": self.public_key_sha256,
        }


class GaApprovalVerifier:
    @classmethod
    def verify(
        cls,
        role: str,
        reference: GaApprovalReference | None,
        trust_policy: GaTrustPolicy,
        evidence_root: Path,
        candidate: GaCandidateManifest,
        now: datetime,
    ) -> GaApprovalResult:
        if reference is None:
            return GaApprovalResult(role, "missing", "required approval is missing", "", "")
        if reference.role != role:
            return GaApprovalResult(role, "rejected", "approval role mismatch", "", "")
        trusted = trust_policy.approval_keys.get(role, frozenset())
        if reference.public_key_sha256 not in trusted:
            return GaApprovalResult(
                role,
                "rejected",
                "approval key is not trusted for this role",
                "",
                reference.public_key_sha256,
            )
        try:
            statement = GaEvidenceInspector._resolve(evidence_root, reference.statement_path)
            signature = GaEvidenceInspector._resolve(evidence_root, reference.signature_path)
            public_key = GaEvidenceInspector._resolve(evidence_root, reference.public_key_path)
            actual_fingerprint = hashlib.sha256(public_key.read_bytes()).hexdigest()
            if actual_fingerprint != reference.public_key_sha256:
                raise GaGoNoGoError("approval public key fingerprint mismatch")
            ReleaseSignatureVerifier.verify(public_key, statement, signature)
            payload_value = json.loads(statement.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ReleasePackagingError, GaGoNoGoError) as exc:
            return GaApprovalResult(
                role,
                "rejected",
                f"approval verification failed: {exc}",
                "",
                reference.public_key_sha256,
            )
        if not isinstance(payload_value, dict):
            return GaApprovalResult(
                role,
                "rejected",
                "approval statement root must be an object",
                "",
                reference.public_key_sha256,
            )
        payload = {str(key): value for key, value in payload_value.items()}
        approver = str(payload.get("approver", "")).strip()
        failures: list[str] = []
        if payload.get("schema_version") != 1:
            failures.append("unsupported approval schema")
        if payload.get("release_version") != candidate.release_version:
            failures.append("approval release version mismatch")
        if payload.get("candidate_id") != candidate.candidate_id:
            failures.append("approval candidate mismatch")
        if payload.get("role") != role:
            failures.append("approval statement role mismatch")
        if payload.get("decision") != "approve":
            failures.append("approval decision is not approve")
        if not approver:
            failures.append("approval approver is missing")
        try:
            signed_at = GaTimeParser.parse(payload.get("signed_at"), "approval signed_at")
        except GaGoNoGoError as exc:
            failures.append(str(exc))
        else:
            if signed_at > now + timedelta(minutes=5):
                failures.append("approval timestamp is in the future")
            if now - signed_at > timedelta(days=30):
                failures.append("approval is older than 30 days")
        if failures:
            return GaApprovalResult(
                role,
                "rejected",
                "; ".join(failures),
                approver,
                reference.public_key_sha256,
            )
        return GaApprovalResult(
            role,
            "approved",
            "signed approval is valid and trusted",
            approver,
            reference.public_key_sha256,
        )


class GaRiskEvaluator:
    @classmethod
    def blockers(
        cls,
        risks: tuple[GaRiskRecord, ...],
        policy: GaGoNoGoPolicy,
        now: datetime,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        for risk in risks:
            if risk.status in {"closed", "mitigated"}:
                continue
            if risk.severity in policy.blocking_risk_severities:
                blockers.append(
                    f"risk {risk.identifier} is {risk.status} with blocking "
                    f"severity {risk.severity}"
                )
                continue
            if risk.status == "open":
                blockers.append(f"risk {risk.identifier} remains open")
                continue
            if risk.status == "accepted":
                if not risk.accepted_by or not risk.mitigation:
                    blockers.append(f"risk {risk.identifier} acceptance lacks owner or mitigation")
                    continue
                try:
                    expires_at = GaTimeParser.parse(
                        risk.expires_at, f"risk {risk.identifier} expires_at"
                    )
                except GaGoNoGoError as exc:
                    blockers.append(str(exc))
                    continue
                if expires_at <= now:
                    blockers.append(f"risk {risk.identifier} acceptance has expired")
        return tuple(blockers)


class GaGoNoGoDecisionService:
    def evaluate_and_write(
        self,
        *,
        manifest_path: Path,
        policy_path: Path,
        trust_policy_path: Path,
        evidence_root: Path,
        output_path: Path,
        signing_material: ReleaseSigningMaterial,
        now: datetime | None = None,
    ) -> dict[str, object]:
        decision_time = (now or datetime.now(UTC)).astimezone(UTC)
        policy = GaGoNoGoPolicy.load(policy_path)
        trust_policy = GaTrustPolicy.load(trust_policy_path)
        candidate = GaCandidateManifest.load(manifest_path)
        evidence_by_id = {item.identifier: item for item in candidate.evidence}
        criteria: list[GaCriterionResult] = []
        for evidence_policy in policy.required_evidence:
            reference = evidence_by_id.get(evidence_policy.identifier)
            if reference is None:
                criteria.append(
                    GaCriterionResult(
                        evidence_policy.identifier,
                        evidence_policy.category,
                        "missing",
                        "required evidence is missing",
                        "",
                    )
                )
            else:
                criteria.append(
                    GaEvidenceInspector.inspect(
                        evidence_policy,
                        reference,
                        evidence_root,
                        decision_time,
                    )
                )
        approvals_by_role = {item.role: item for item in candidate.approvals}
        approvals = [
            GaApprovalVerifier.verify(
                role,
                approvals_by_role.get(role),
                trust_policy,
                evidence_root,
                candidate,
                decision_time,
            )
            for role in policy.required_approval_roles
        ]
        blockers = [
            f"criterion {item.identifier}: {item.detail}" for item in criteria if not item.passed
        ]
        blockers.extend(
            f"approval {item.role}: {item.detail}" for item in approvals if not item.passed
        )
        blockers.extend(GaRiskEvaluator.blockers(candidate.risks, policy, decision_time))
        candidate_time = GaTimeParser.parse(candidate.generated_at, "candidate generated_at")
        if candidate_time > decision_time + timedelta(minutes=5):
            blockers.append("candidate manifest timestamp is in the future")
        if decision_time - candidate_time > timedelta(days=7):
            blockers.append("candidate manifest is older than 7 days")
        expected_evidence_ids = {item.identifier for item in policy.required_evidence}
        blockers.extend(
            f"unsupported evidence reference: {identifier}"
            for identifier in sorted(set(evidence_by_id).difference(expected_evidence_ids))
        )
        expected_roles = set(policy.required_approval_roles)
        blockers.extend(
            f"unsupported approval role: {role}"
            for role in sorted(set(approvals_by_role).difference(expected_roles))
        )
        decision_fingerprint = signing_material.public_key_sha256()
        trusted_decision_key = (
            signing_material.trusted and decision_fingerprint in trust_policy.decision_keys
        )
        if not trusted_decision_key:
            blockers.append("decision signing key is not trusted by the GA trust policy")
        decision = "GO" if not blockers else "NO-GO"
        evidence_digest = hashlib.sha256(
            json.dumps(
                {
                    "criteria": [item.as_dict() for item in criteria],
                    "approvals": [item.as_dict() for item in approvals],
                    "risks": [
                        {
                            "id": risk.identifier,
                            "severity": risk.severity,
                            "status": risk.status,
                            "owner": risk.owner,
                            "mitigation": risk.mitigation,
                            "accepted_by": risk.accepted_by,
                            "expires_at": risk.expires_at,
                        }
                        for risk in candidate.risks
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        report: dict[str, object] = {
            "schema_version": 1,
            "gate_id": policy.gate_id,
            "epic": policy.epic,
            "release_version": candidate.release_version,
            "candidate_id": candidate.candidate_id,
            "source_commit": candidate.source_commit,
            "generated_at": decision_time.isoformat(),
            "decision": decision,
            "authorized_for_ga": decision == "GO",
            "complete": all(item.status != "missing" for item in criteria)
            and all(item.status != "missing" for item in approvals),
            "criteria": [item.as_dict() for item in criteria],
            "approvals": [item.as_dict() for item in approvals],
            "risks": [
                {
                    "id": item.identifier,
                    "severity": item.severity,
                    "status": item.status,
                    "owner": item.owner,
                    "mitigation": item.mitigation,
                    "accepted_by": item.accepted_by,
                    "expires_at": item.expires_at,
                }
                for item in candidate.risks
            ],
            "refusal_reasons": blockers,
            "evidence_digest_sha256": evidence_digest,
            "candidate_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            "trust_policy_sha256": hashlib.sha256(trust_policy_path.read_bytes()).hexdigest(),
            "signing_key_origin": signing_material.origin,
            "trusted_signing_key": trusted_decision_key,
            "decision_public_key_sha256": decision_fingerprint,
        }
        payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        signature = signing_material.sign(payload)
        public_key = signing_material.public_key_pem()
        signature_path = output_path.with_suffix(output_path.suffix + ".sig")
        public_key_path = output_path.with_suffix(output_path.suffix + ".pub")
        ReleaseFileWriter.write_bytes_atomic(output_path, payload)
        ReleaseFileWriter.write_bytes_atomic(signature_path, signature)
        ReleaseFileWriter.write_bytes_atomic(public_key_path, public_key)
        try:
            ReleaseSignatureVerifier.verify(public_key_path, output_path, signature_path)
        except ReleasePackagingError as exc:
            raise GaGoNoGoError("GA decision signature verification failed") from exc
        return report
