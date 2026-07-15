from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from openinfra.quality.ga_go_no_go import (
    GaApprovalReference,
    GaApprovalVerifier,
    GaCandidateManifest,
    GaEvidenceInspector,
    GaEvidencePolicy,
    GaEvidenceReference,
    GaGoNoGoDecisionService,
    GaGoNoGoError,
    GaGoNoGoPolicy,
    GaRiskEvaluator,
    GaRiskRecord,
    GaTimeParser,
    GaTrustPolicy,
)
from openinfra.quality.release_packaging import (
    ReleaseSignatureVerifier,
    ReleaseSigningMaterial,
)


class GaGoNoGoFixture:
    ROLES = (
        "product-owner",
        "engineering-owner",
        "security-owner",
        "operations-owner",
        "support-owner",
    )

    def __init__(self, root: Path, now: datetime) -> None:
        self.root = root
        self.now = now
        self.evidence_root = root / "evidence"
        self.evidence_root.mkdir()
        self.policy_path = root / "policy.json"
        self.trust_policy_path = root / "trust-policy.json"
        self.manifest_path = root / "candidate.json"
        self.output_path = root / "decision.json"
        self.decision_private_key_path = root / "decision-key.pem"
        self.evidence: list[dict[str, str]] = []
        self.approvals: list[dict[str, str]] = []
        self.risks: list[dict[str, str]] = []
        self.approval_keys: dict[str, list[str]] = {}
        self.decision_fingerprint = self._write_decision_key()
        self._write_policy()

    def _write_policy(self) -> None:
        policy = {
            "schema_version": 1,
            "gate_id": "GATE-07",
            "epic": "EPIC-1805",
            "required_evidence": [
                {
                    "id": identifier,
                    "report_kind": identifier,
                    "category": category,
                    "max_age_days": max_age,
                }
                for identifier, category, max_age in (
                    ("technical-validation", "technical", 7),
                    ("enterprise-capacity", "technical", 30),
                    ("release-security", "security", 7),
                    ("release-packaging", "technical", 7),
                    ("ga-documentation", "operations", 30),
                    ("operations-readiness", "operations", 30),
                    ("support-readiness", "support", 90),
                    ("business-readiness", "business", 30),
                )
            ],
            "required_approval_roles": list(self.ROLES),
            "blocking_risk_severities": ["critical", "high"],
        }
        self.policy_path.write_text(json.dumps(policy), encoding="utf-8")

    def _write_decision_key(self) -> str:
        private_key = Ed25519PrivateKey.generate()
        self.decision_private_key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(public_key).hexdigest()

    def add_complete_evidence(self, generated_at: datetime | None = None) -> None:
        timestamp = (generated_at or self.now).isoformat()
        reports: dict[str, dict[str, object]] = {
            "technical-validation": {
                "schema_version": 1,
                "openinfra_version": "0.33.5",
                "generated_at": timestamp,
                "complete": True,
                "passed": True,
                "coverage_percent": 98.2,
                "failed_tests": 0,
            },
            "enterprise-capacity": {
                "schema_version": 1,
                "openinfra_version": "0.33.5",
                "generated_at": timestamp,
                "capacity_certification": True,
                "status": "certified",
                "failures": [],
            },
            "release-security": {
                "schema_version": 1,
                "openinfra_version": "0.33.5",
                "generated_at": timestamp,
                "complete": True,
                "offline_mode": False,
                "release_security_certification": True,
                "failures": [],
            },
            "release-packaging": {
                "schema_version": 1,
                "release_version": "0.33.5",
                "generated_at": timestamp,
                "complete": True,
                "trusted_signing_key": True,
                "release_packaging_certification": True,
                "failures": [],
            },
            "ga-documentation": {
                "schema_version": 1,
                "version": "0.33.5",
                "generated_at": timestamp,
                "epic": "EPIC-1804",
                "passed": True,
            },
            "operations-readiness": {
                "schema_version": 1,
                "release_version": "0.33.5",
                "generated_at": timestamp,
                "complete": True,
                "operations_readiness": True,
                "pitr_tested": True,
                "failover_tested": True,
                "backup_restore_tested": True,
                "chaos_tested": True,
                "runbooks_validated": True,
            },
            "support-readiness": {
                "schema_version": 1,
                "release_version": "0.33.5",
                "generated_at": timestamp,
                "complete": True,
                "support_readiness": True,
                "sla_defined": True,
                "lifecycle_defined": True,
                "patch_policy_defined": True,
                "migration_policy_defined": True,
                "escalation_matrix_defined": True,
            },
            "business-readiness": {
                "schema_version": 1,
                "release_version": "0.33.5",
                "generated_at": timestamp,
                "complete": True,
                "business_readiness": True,
                "commercial_approved": True,
                "legal_approved": True,
                "licensing_approved": True,
                "release_notes_approved": True,
                "known_risks_accepted": True,
            },
        }
        for identifier, report in reports.items():
            path = self.evidence_root / f"{identifier}.json"
            payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
            path.write_bytes(payload)
            self.evidence.append(
                {
                    "id": identifier,
                    "report_kind": identifier,
                    "path": path.name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )

    def add_approvals(self) -> None:
        for role in self.ROLES:
            private_key = Ed25519PrivateKey.generate()
            statement_path = self.evidence_root / f"approval-{role}.json"
            signature_path = statement_path.with_suffix(".json.sig")
            public_key_path = statement_path.with_suffix(".json.pub")
            statement = {
                "schema_version": 1,
                "release_version": "0.33.5",
                "candidate_id": "openinfra-0.33.5-rc1",
                "role": role,
                "approver": f"OpenInfra {role}",
                "decision": "approve",
                "signed_at": self.now.isoformat(),
                "comment": "Gate GATE-07 approved",
            }
            payload = (json.dumps(statement, indent=2, sort_keys=True) + "\n").encode()
            statement_path.write_bytes(payload)
            signature_path.write_bytes(private_key.sign(payload))
            public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            public_key_path.write_bytes(public_key)
            fingerprint = hashlib.sha256(public_key).hexdigest()
            self.approval_keys[role] = [fingerprint]
            self.approvals.append(
                {
                    "role": role,
                    "statement_path": statement_path.name,
                    "signature_path": signature_path.name,
                    "public_key_path": public_key_path.name,
                    "public_key_sha256": fingerprint,
                }
            )

    def write_inputs(self, trust_decision_key: bool = True) -> None:
        self.trust_policy_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "approval_keys": self.approval_keys,
                    "decision_keys": [self.decision_fingerprint] if trust_decision_key else [],
                }
            ),
            encoding="utf-8",
        )
        self.manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "release_version": "0.33.5",
                    "candidate_id": "openinfra-0.33.5-rc1",
                    "source_commit": "a" * 40,
                    "generated_at": self.now.isoformat(),
                    "evidence": self.evidence,
                    "approvals": self.approvals,
                    "risks": self.risks,
                }
            ),
            encoding="utf-8",
        )

    def service(self) -> GaGoNoGoDecisionService:
        return GaGoNoGoDecisionService()

    def signing_material(self) -> ReleaseSigningMaterial:
        return ReleaseSigningMaterial.from_file(self.decision_private_key_path)


def test_ga_go_no_go_accepts_complete_trusted_candidate(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    fixture = GaGoNoGoFixture(tmp_path, now)
    fixture.add_complete_evidence()
    fixture.add_approvals()
    fixture.write_inputs()

    report = fixture.service().evaluate_and_write(
        manifest_path=fixture.manifest_path,
        policy_path=fixture.policy_path,
        trust_policy_path=fixture.trust_policy_path,
        evidence_root=fixture.evidence_root,
        output_path=fixture.output_path,
        signing_material=fixture.signing_material(),
        now=now,
    )

    assert report["decision"] == "GO"
    assert report["authorized_for_ga"] is True
    assert report["complete"] is True
    assert report["refusal_reasons"] == []
    assert len(report["criteria"]) == 8
    assert len(report["approvals"]) == 5
    ReleaseSignatureVerifier.verify(
        fixture.output_path.with_suffix(".json.pub"),
        fixture.output_path,
        fixture.output_path.with_suffix(".json.sig"),
    )


def test_ga_go_no_go_produces_motivated_refusal_for_missing_proofs(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    fixture = GaGoNoGoFixture(tmp_path, now)
    fixture.write_inputs(trust_decision_key=False)

    report = fixture.service().evaluate_and_write(
        manifest_path=fixture.manifest_path,
        policy_path=fixture.policy_path,
        trust_policy_path=fixture.trust_policy_path,
        evidence_root=fixture.evidence_root,
        output_path=fixture.output_path,
        signing_material=ReleaseSigningMaterial.generate_ephemeral(),
        now=now,
    )

    assert report["decision"] == "NO-GO"
    assert report["authorized_for_ga"] is False
    assert report["complete"] is False
    reasons = "\n".join(report["refusal_reasons"])
    assert "required evidence is missing" in reasons
    assert "required approval is missing" in reasons
    assert "decision signing key is not trusted" in reasons


def test_ga_go_no_go_rejects_stale_evidence_and_blocking_risk(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    fixture = GaGoNoGoFixture(tmp_path, now)
    fixture.add_complete_evidence(now - timedelta(days=120))
    fixture.add_approvals()
    fixture.risks.append(
        {
            "id": "RISK-GA-001",
            "severity": "high",
            "status": "accepted",
            "owner": "operations",
            "mitigation": "Temporary supervision",
            "accepted_by": "product-owner",
            "expires_at": (now + timedelta(days=7)).isoformat(),
        }
    )
    fixture.write_inputs()

    report = fixture.service().evaluate_and_write(
        manifest_path=fixture.manifest_path,
        policy_path=fixture.policy_path,
        trust_policy_path=fixture.trust_policy_path,
        evidence_root=fixture.evidence_root,
        output_path=fixture.output_path,
        signing_material=fixture.signing_material(),
        now=now,
    )

    assert report["decision"] == "NO-GO"
    reasons = "\n".join(report["refusal_reasons"])
    assert "evidence is older" in reasons
    assert "blocking severity high" in reasons


def test_ga_go_no_go_rejects_tampered_evidence_and_path_escape(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    fixture = GaGoNoGoFixture(tmp_path, now)
    fixture.add_complete_evidence()
    fixture.evidence[0]["sha256"] = "0" * 64
    fixture.evidence[1]["path"] = "../outside.json"
    fixture.add_approvals()
    fixture.write_inputs()

    report = fixture.service().evaluate_and_write(
        manifest_path=fixture.manifest_path,
        policy_path=fixture.policy_path,
        trust_policy_path=fixture.trust_policy_path,
        evidence_root=fixture.evidence_root,
        output_path=fixture.output_path,
        signing_material=fixture.signing_material(),
        now=now,
    )

    reasons = "\n".join(report["refusal_reasons"])
    assert "SHA-256 mismatch" in reasons
    assert "escapes evidence root" in reasons


def test_ga_go_no_go_policy_rejects_incomplete_catalog(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate_id": "GATE-07",
                "epic": "EPIC-1805",
                "required_evidence": [],
                "required_approval_roles": ["product-owner"],
                "blocking_risk_severities": ["high"],
            }
        ),
        encoding="utf-8",
    )

    try:
        GaGoNoGoPolicy.load(path)
    except GaGoNoGoError as exc:
        assert "catalog is incomplete" in str(exc)
    else:
        raise AssertionError("incomplete GA policy must be rejected")


def test_ga_schema_validation_rejects_malformed_inputs(tmp_path: Path) -> None:
    with pytest.raises(GaGoNoGoError):
        GaEvidencePolicy.from_mapping("invalid")
    with pytest.raises(GaGoNoGoError):
        GaEvidencePolicy.from_mapping({})
    with pytest.raises(GaGoNoGoError):
        GaEvidencePolicy.from_mapping(
            {"id": "x", "report_kind": "x", "category": "x", "max_age_days": True}
        )
    with pytest.raises(GaGoNoGoError):
        GaEvidenceReference.from_mapping("invalid")
    with pytest.raises(GaGoNoGoError):
        GaEvidenceReference.from_mapping({})
    with pytest.raises(GaGoNoGoError):
        GaEvidenceReference.from_mapping(
            {"id": "x", "report_kind": "x", "path": "x", "sha256": "bad"}
        )
    with pytest.raises(GaGoNoGoError):
        GaApprovalReference.from_mapping("invalid")
    with pytest.raises(GaGoNoGoError):
        GaApprovalReference.from_mapping({})
    with pytest.raises(GaGoNoGoError):
        GaApprovalReference.from_mapping(
            {
                "role": "x",
                "statement_path": "x",
                "signature_path": "x",
                "public_key_path": "x",
                "public_key_sha256": "bad",
            }
        )
    with pytest.raises(GaGoNoGoError):
        GaRiskRecord.from_mapping("invalid")
    with pytest.raises(GaGoNoGoError):
        GaRiskRecord.from_mapping({})
    with pytest.raises(GaGoNoGoError):
        GaRiskRecord.from_mapping(
            {"id": "x", "severity": "low", "status": "unknown", "owner": "owner"}
        )
    for value in (None, "not-a-date", "2026-07-12T18:00:00"):
        with pytest.raises(GaGoNoGoError):
            GaTimeParser.parse(value, "timestamp")

    missing = tmp_path / "missing.json"
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy.load(missing)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy.load(invalid)
    invalid.write_text("[]", encoding="utf-8")
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy.load(invalid)

    invalid.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy.load(invalid)
    invalid.write_text(
        json.dumps({"schema_version": 1, "required_evidence": "invalid"}), encoding="utf-8"
    )
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy.load(invalid)
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy._string_tuple(None, "roles")
    with pytest.raises(GaGoNoGoError):
        GaGoNoGoPolicy._string_tuple(["x", "x"], "roles")

    invalid.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
    with pytest.raises(GaGoNoGoError):
        GaTrustPolicy.load(invalid)
    invalid.write_text(
        json.dumps({"schema_version": 1, "approval_keys": [], "decision_keys": []}),
        encoding="utf-8",
    )
    with pytest.raises(GaGoNoGoError):
        GaTrustPolicy.load(invalid)
    with pytest.raises(GaGoNoGoError):
        GaTrustPolicy._fingerprints("invalid", "keys")
    with pytest.raises(GaGoNoGoError):
        GaTrustPolicy._fingerprints(["bad"], "keys")


def test_candidate_manifest_validation_rejects_invalid_contracts(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC).isoformat()
    base: dict[str, object] = {
        "schema_version": 1,
        "release_version": "0.33.5",
        "candidate_id": "candidate",
        "source_commit": "a" * 40,
        "generated_at": now,
        "evidence": [],
        "approvals": [],
        "risks": [],
    }
    path = tmp_path / "candidate.json"

    mutations = (
        {"schema_version": 2},
        {"evidence": "invalid"},
        {"risks": "invalid"},
        {"release_version": "9.9.9"},
        {"candidate_id": "", "source_commit": "short"},
        {"source_commit": "g" * 40},
        {
            "evidence": [
                {"id": "x", "report_kind": "x", "path": "x", "sha256": "0" * 64},
                {"id": "x", "report_kind": "x", "path": "y", "sha256": "0" * 64},
            ]
        },
        {
            "approvals": [
                {
                    "role": "x",
                    "statement_path": "a",
                    "signature_path": "b",
                    "public_key_path": "c",
                    "public_key_sha256": "0" * 64,
                },
                {
                    "role": "x",
                    "statement_path": "d",
                    "signature_path": "e",
                    "public_key_path": "f",
                    "public_key_sha256": "0" * 64,
                },
            ]
        },
        {
            "risks": [
                {"id": "x", "severity": "low", "status": "closed", "owner": "o"},
                {"id": "x", "severity": "low", "status": "closed", "owner": "o"},
            ]
        },
    )
    for mutation in mutations:
        payload = dict(base)
        payload.update(mutation)
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(GaGoNoGoError):
            GaCandidateManifest.load(path)


def test_evidence_inspector_covers_invalid_reports(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    policy = GaEvidencePolicy("technical-validation", "technical-validation", "technical", 7)
    bad_kind = GaEvidenceReference("technical-validation", "other", "x", "0" * 64)
    assert not GaEvidenceInspector.inspect(policy, bad_kind, tmp_path, now).passed

    missing = GaEvidenceReference(
        "technical-validation", "technical-validation", "missing", "0" * 64
    )
    assert "missing" in GaEvidenceInspector.inspect(policy, missing, tmp_path, now).detail

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    digest = hashlib.sha256(invalid_json.read_bytes()).hexdigest()
    invalid_ref = GaEvidenceReference(
        "technical-validation", "technical-validation", invalid_json.name, digest
    )
    assert "invalid JSON" in GaEvidenceInspector.inspect(policy, invalid_ref, tmp_path, now).detail

    invalid_json.write_text("[]", encoding="utf-8")
    digest = hashlib.sha256(invalid_json.read_bytes()).hexdigest()
    invalid_ref = GaEvidenceReference(
        "technical-validation", "technical-validation", invalid_json.name, digest
    )
    assert (
        "root must be an object"
        in GaEvidenceInspector.inspect(policy, invalid_ref, tmp_path, now).detail
    )

    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "openinfra_version": "wrong",
                "generated_at": (now + timedelta(hours=1)).isoformat(),
                "complete": False,
                "passed": False,
                "coverage_percent": 97,
                "failed_tests": 1,
            }
        ),
        encoding="utf-8",
    )
    ref = GaEvidenceReference(
        "technical-validation",
        "technical-validation",
        report.name,
        hashlib.sha256(report.read_bytes()).hexdigest(),
    )
    detail = GaEvidenceInspector.inspect(policy, ref, tmp_path, now).detail
    assert "does not match" in detail
    assert "coverage_percent" in detail
    assert "failed_tests" in detail
    assert "future" in detail

    assert GaEvidenceInspector._report_failures(
        "enterprise-capacity",
        {
            "openinfra_version": "0.33.5",
            "capacity_certification": False,
            "status": "rejected",
            "failures": ["x"],
        },
    )
    assert GaEvidenceInspector._report_failures(
        "release-security",
        {
            "openinfra_version": "0.33.5",
            "complete": False,
            "release_security_certification": False,
            "offline_mode": True,
            "failures": ["x"],
        },
    )
    assert GaEvidenceInspector._report_failures(
        "release-packaging",
        {
            "release_version": "0.33.5",
            "complete": False,
            "release_packaging_certification": False,
            "trusted_signing_key": False,
            "failures": ["x"],
        },
    )
    assert GaEvidenceInspector._report_failures(
        "ga-documentation",
        {"version": "0.33.5", "passed": False, "epic": "wrong"},
    )
    assert GaEvidenceInspector._report_failures("unsupported", {})


def test_approval_and_risk_negative_paths(tmp_path: Path) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    fixture = GaGoNoGoFixture(tmp_path, now)
    fixture.add_complete_evidence()
    fixture.add_approvals()
    fixture.write_inputs()
    candidate = GaCandidateManifest.load(fixture.manifest_path)
    trust = GaTrustPolicy.load(fixture.trust_policy_path)

    missing = GaApprovalVerifier.verify(
        "product-owner", None, trust, fixture.evidence_root, candidate, now
    )
    assert missing.status == "missing"
    mismatch = GaApprovalVerifier.verify(
        "wrong-role", candidate.approvals[0], trust, fixture.evidence_root, candidate, now
    )
    assert mismatch.status == "rejected"
    untrusted = GaApprovalVerifier.verify(
        "product-owner",
        candidate.approvals[0],
        GaTrustPolicy({}, frozenset()),
        fixture.evidence_root,
        candidate,
        now,
    )
    assert "not trusted" in untrusted.detail

    reference = candidate.approvals[0]
    statement = fixture.evidence_root / reference.statement_path
    signature = fixture.evidence_root / reference.signature_path
    signature.write_bytes(b"broken")
    rejected = GaApprovalVerifier.verify(
        reference.role, reference, trust, fixture.evidence_root, candidate, now
    )
    assert "verification failed" in rejected.detail

    policy = GaGoNoGoPolicy.load(fixture.policy_path)
    risks = tuple(
        GaRiskRecord.from_mapping(item)
        for item in (
            {"id": "closed", "severity": "low", "status": "closed", "owner": "o"},
            {"id": "open", "severity": "low", "status": "open", "owner": "o"},
            {"id": "accepted-empty", "severity": "low", "status": "accepted", "owner": "o"},
            {
                "id": "accepted-invalid-date",
                "severity": "low",
                "status": "accepted",
                "owner": "o",
                "mitigation": "m",
                "accepted_by": "a",
                "expires_at": "invalid",
            },
            {
                "id": "accepted-expired",
                "severity": "low",
                "status": "accepted",
                "owner": "o",
                "mitigation": "m",
                "accepted_by": "a",
                "expires_at": (now - timedelta(days=1)).isoformat(),
            },
        )
    )
    blockers = "\n".join(GaRiskEvaluator.blockers(risks, policy, now))
    assert "remains open" in blockers
    assert "lacks owner or mitigation" in blockers
    assert "not a valid ISO-8601" in blockers
    assert "acceptance has expired" in blockers


def test_decision_signature_failure_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 7, 12, 18, 0, tzinfo=UTC)
    fixture = GaGoNoGoFixture(tmp_path, now)
    fixture.write_inputs()

    def fail_verify(*_args: object, **_kwargs: object) -> None:
        from openinfra.quality.release_packaging import ReleasePackagingError

        raise ReleasePackagingError("forced")

    monkeypatch.setattr(ReleaseSignatureVerifier, "verify", fail_verify)
    with pytest.raises(GaGoNoGoError, match="signature verification failed"):
        fixture.service().evaluate_and_write(
            manifest_path=fixture.manifest_path,
            policy_path=fixture.policy_path,
            trust_policy_path=fixture.trust_policy_path,
            evidence_root=fixture.evidence_root,
            output_path=fixture.output_path,
            signing_material=ReleaseSigningMaterial.generate_ephemeral(),
            now=now,
        )
