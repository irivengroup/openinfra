from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra import __version__
from openinfra.quality.cloud_native_promotion import (
    CloudNativeEvidenceInspector,
    CloudNativeEvidencePolicy,
    CloudNativeEvidenceReference,
    CloudNativeJson,
    CloudNativePromotionCertification,
    CloudNativePromotionError,
    CloudNativePromotionManifest,
    CloudNativePromotionPolicy,
    CloudNativeTime,
)
from openinfra.quality.support_readiness import (
    EscalationLevel,
    LifecycleStage,
    PatchTarget,
    SupportEditionProfile,
    SupportPolicy,
    SupportPolicyParser,
    SupportReadinessError,
    SupportTarget,
)

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def _valid_policy_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "gate_id": "GATE-10",
        "release_id": "REL-11",
        "required_evidence": [
            {"id": identifier, "report_kind": kind, "max_age_hours": 24}
            for identifier, kind in CloudNativePromotionPolicy.EXPECTED_EVIDENCE.items()
        ],
    }


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestCloudNativeGateErrorPaths:
    @pytest.mark.parametrize(
        ("value", "message"),
        [
            ([], "must be objects"),
            ({"id": "", "report_kind": "x", "max_age_hours": 1}, "cannot be empty"),
            ({"id": "x", "report_kind": "y", "max_age_hours": True}, "max_age_hours"),
        ],
    )
    def test_evidence_policy_rejects_invalid_entries(self, value: object, message: str) -> None:
        with pytest.raises(CloudNativePromotionError, match=message):
            CloudNativeEvidencePolicy.from_mapping(value)

    def test_policy_manifest_and_reference_validation(self, tmp_path: Path) -> None:
        for mutation, message in (
            (lambda p: p.update(schema_version=2), "unsupported"),
            (lambda p: p.update(gate_id="GATE-9"), "GATE-10"),
            (lambda p: p.update(required_evidence={}), "required_evidence"),
            (
                lambda p: p["required_evidence"].append(p["required_evidence"][0]),
                "identifiers must be unique",
            ),
        ):
            payload = _valid_policy_payload()
            mutation(payload)
            with pytest.raises(CloudNativePromotionError, match=message):
                CloudNativePromotionPolicy.load(_write(tmp_path / "policy.json", payload))

        with pytest.raises(CloudNativePromotionError, match="references must be objects"):
            CloudNativeEvidenceReference.from_mapping([])
        with pytest.raises(CloudNativePromotionError, match="fields cannot be empty"):
            CloudNativeEvidenceReference.from_mapping(
                {"id": "", "report_kind": "x", "path": "p", "sha256": "0" * 64}
            )
        with pytest.raises(CloudNativePromotionError, match="SHA-256"):
            CloudNativeEvidenceReference.from_mapping(
                {"id": "x", "report_kind": "y", "path": "p", "sha256": "bad"}
            )

        base = {
            "schema_version": 1,
            "gate_id": "GATE-10",
            "release_version": __version__,
            "candidate_id": "candidate",
            "source_commit": "a" * 40,
            "generated_at": NOW.isoformat(),
            "evidence": [
                {
                    "id": identifier,
                    "report_kind": kind,
                    "path": f"{identifier}.json",
                    "sha256": "0" * 64,
                }
                for identifier, kind in CloudNativePromotionPolicy.EXPECTED_EVIDENCE.items()
            ],
        }
        for mutation, message in (
            (lambda p: p.update(schema_version=2), "unsupported"),
            (lambda p: p.update(gate_id="GATE-9"), "target GATE-10"),
            (lambda p: p.update(release_version="0.0.0"), "must match"),
            (lambda p: p.update(candidate_id=""), "candidate_id"),
            (lambda p: p.update(evidence={}), "must list evidence"),
            (lambda p: p["evidence"].append(p["evidence"][0]), "references must be unique"),
        ):
            payload = json.loads(json.dumps(base))
            mutation(payload)
            with pytest.raises(CloudNativePromotionError, match=message):
                CloudNativePromotionManifest.load(_write(tmp_path / "manifest.json", payload))

    def test_inspector_time_json_and_certification_rejections(self, tmp_path: Path) -> None:
        policy = CloudNativeEvidencePolicy("evidence", "unsupported-kind", 1)
        reference = CloudNativeEvidenceReference(
            "evidence", "unsupported-kind", "report.json", "0" * 64
        )
        missing = CloudNativeEvidenceInspector.inspect(policy, reference, tmp_path, NOW)
        assert missing.passed is False
        assert "missing" in missing.detail

        report = tmp_path / "report.json"
        report.write_text("not-json", encoding="utf-8")
        reference = CloudNativeEvidenceReference(
            "evidence",
            "unsupported-kind",
            report.name,
            hashlib.sha256(report.read_bytes()).hexdigest(),
        )
        assert (
            "invalid JSON"
            in CloudNativeEvidenceInspector.inspect(policy, reference, tmp_path, NOW).detail
        )
        _write(report, [])
        reference = CloudNativeEvidenceReference(
            "evidence",
            "unsupported-kind",
            report.name,
            hashlib.sha256(report.read_bytes()).hexdigest(),
        )
        assert (
            "root must be an object"
            in CloudNativeEvidenceInspector.inspect(policy, reference, tmp_path, NOW).detail
        )

        payload = {
            "release_version": "wrong",
            "phase": "wrong",
            "release": "wrong",
            "generated_at": (NOW - timedelta(hours=2)).isoformat(),
        }
        _write(report, payload)
        reference = CloudNativeEvidenceReference(
            "evidence",
            "unsupported-kind",
            report.name,
            hashlib.sha256(report.read_bytes()).hexdigest(),
        )
        detail = CloudNativeEvidenceInspector.inspect(policy, reference, tmp_path, NOW).detail
        assert "unsupported cloud-native report kind" in detail
        assert "older than" in detail

        with pytest.raises(CloudNativePromotionError, match="is required"):
            CloudNativeTime.parse(None, "time")
        with pytest.raises(CloudNativePromotionError, match="ISO-8601"):
            CloudNativeTime.parse("invalid", "time")
        with pytest.raises(CloudNativePromotionError, match="timezone"):
            CloudNativeTime.parse("2026-01-01T00:00:00", "time")
        with pytest.raises(CloudNativePromotionError, match="is missing"):
            CloudNativeJson.load_object(tmp_path / "absent", "payload")
        _write(tmp_path / "array.json", [])
        with pytest.raises(CloudNativePromotionError, match="root must be an object"):
            CloudNativeJson.load_object(tmp_path / "array.json", "payload")

        manifest = CloudNativePromotionManifest(
            1,
            "GATE-10",
            __version__,
            "candidate",
            "a" * 40,
            NOW - timedelta(hours=25),
            (),
        )
        gate_policy = CloudNativePromotionPolicy(
            1,
            "GATE-10",
            "REL-11",
            (CloudNativeEvidencePolicy("missing", "kind", 1),),
        )
        decision = CloudNativePromotionCertification.evaluate(gate_policy, manifest, tmp_path, NOW)
        assert decision["status"] == "rejected"
        assert any("older than 24 hours" in item for item in decision["blockers"])
        assert any("reference is missing" in item for item in decision["blockers"])


class TestSupportReadinessErrorPaths:
    def test_support_value_objects_reject_invalid_contracts(self, tmp_path: Path) -> None:
        with pytest.raises(SupportReadinessError, match="must be an object"):
            SupportTarget.from_mapping("S1", [])
        with pytest.raises(SupportReadinessError, match="positive integer"):
            SupportTarget.from_mapping(
                "S1", {"response_minutes": 0, "update_minutes": 1, "restoration_hours": 1}
            )
        with pytest.raises(SupportReadinessError, match="exactly S1"):
            SupportEditionProfile.from_mapping(
                "lite", {"service_hours": "24x7", "channels": ["email"], "targets": {}}
            )
        profile = SupportEditionProfile(
            "lite",
            "24x7",
            ("email",),
            (SupportTarget("S1", 1, 1, 1),),
        )
        with pytest.raises(SupportReadinessError, match="target is missing"):
            profile.target("S2")
        with pytest.raises(SupportReadinessError, match="stages must be objects"):
            LifecycleStage.from_mapping([])
        with pytest.raises(SupportReadinessError, match="fixes must be an array"):
            LifecycleStage.from_mapping({"name": "active", "duration_months": 1})
        with pytest.raises(SupportReadinessError, match="non-empty and unique"):
            LifecycleStage.from_mapping(
                {"name": "active", "duration_months": 1, "fixes": ["security", "security"]}
            )
        with pytest.raises(SupportReadinessError, match="name is required"):
            LifecycleStage.from_mapping({"name": "", "duration_months": 1, "fixes": []})
        with pytest.raises(SupportReadinessError, match="non-negative"):
            LifecycleStage.from_mapping({"name": "active", "duration_months": -1, "fixes": []})
        with pytest.raises(SupportReadinessError, match="patch target"):
            PatchTarget.from_mapping("critical", [])
        with pytest.raises(SupportReadinessError, match="levels must be objects"):
            EscalationLevel.from_mapping([])
        with pytest.raises(SupportReadinessError, match="level and owner"):
            EscalationLevel.from_mapping({"level": "", "owner": "", "triggers": ["x"]})

        missing = tmp_path / "missing.json"
        with pytest.raises(SupportReadinessError, match="is missing"):
            SupportPolicyParser.load_json(missing)
        invalid = tmp_path / "invalid.json"
        invalid.write_text("{", encoding="utf-8")
        with pytest.raises(SupportReadinessError, match="invalid JSON"):
            SupportPolicyParser.load_json(invalid)
        _write(invalid, [])
        with pytest.raises(SupportReadinessError, match="root must be an object"):
            SupportPolicyParser.load_json(invalid)
        with pytest.raises(SupportReadinessError, match="non-empty array"):
            SupportPolicyParser.string_tuple([], "channels")
        with pytest.raises(SupportReadinessError, match="non-empty and unique"):
            SupportPolicyParser.string_tuple(["email", "email"], "channels")

    def test_support_policy_static_helpers_reject_invalid_shapes(self) -> None:
        with pytest.raises(SupportReadinessError, match="lifecycle must be an object"):
            SupportPolicy._lifecycle([])
        with pytest.raises(SupportReadinessError, match="declare stages"):
            SupportPolicy._lifecycle({})
        with pytest.raises(SupportReadinessError, match="patch_policy"):
            SupportPolicy._patch_targets({})
        with pytest.raises(SupportReadinessError, match="migration_policy"):
            SupportPolicy._migration([])
        with pytest.raises(SupportReadinessError, match="direct_upgrade_span"):
            SupportPolicy._migration(
                {
                    "direct_upgrade_span": 2,
                    "staged_upgrade_span": 2,
                    "backup_required": True,
                    "rollback_required": True,
                }
            )
        with pytest.raises(SupportReadinessError, match="staged_upgrade_span"):
            SupportPolicy._migration(
                {
                    "direct_upgrade_span": 1,
                    "staged_upgrade_span": 1,
                    "backup_required": True,
                    "rollback_required": True,
                }
            )
        with pytest.raises(SupportReadinessError, match="must be an array"):
            SupportPolicy._escalation({})
        with pytest.raises(SupportReadinessError, match="out of order"):
            SupportPolicy._escalation([{"level": "L1", "owner": "support", "triggers": ["ticket"]}])
