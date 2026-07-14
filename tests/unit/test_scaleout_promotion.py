from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra import __version__
from openinfra.quality.scaleout_promotion import (
    ScaleoutCriterionResult,
    ScaleoutEvidenceInspector,
    ScaleoutEvidencePolicy,
    ScaleoutEvidenceReference,
    ScaleoutJson,
    ScaleoutPromotionCertification,
    ScaleoutPromotionError,
    ScaleoutPromotionManifest,
    ScaleoutPromotionPolicy,
    ScaleoutTime,
)


class TestScaleoutPromotion:
    @staticmethod
    def _write(path: Path, payload: dict[str, object]) -> str:
        raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def _fixture(
        cls,
        tmp_path: Path,
        *,
        now: datetime,
    ) -> tuple[Path, Path, Path]:
        evidence_root = tmp_path / "evidence"
        evidence_root.mkdir(parents=True)
        policy = {
            "schema_version": 1,
            "gate_id": "GATE-09",
            "release_id": "REL-10",
            "required_evidence": [
                {"id": "p20-contracts", "report_kind": "p20-contracts", "max_age_hours": 24},
                {
                    "id": "enterprise-capacity",
                    "report_kind": "enterprise-capacity",
                    "max_age_hours": 72,
                },
                {"id": "multisite-chaos", "report_kind": "multisite-chaos", "max_age_hours": 72},
                {"id": "pra-pca", "report_kind": "pra-pca", "max_age_hours": 168},
                {"id": "release-security", "report_kind": "release-security", "max_age_hours": 72},
                {
                    "id": "release-packaging",
                    "report_kind": "release-packaging",
                    "max_age_hours": 72,
                },
                {"id": "ga-go-no-go", "report_kind": "ga-go-no-go", "max_age_hours": 168},
            ],
        }
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        common = {"generated_at": now.isoformat()}
        payloads = {
            "p20-contracts": {
                **common,
                "release_version": __version__,
                "complete": True,
                "pgbouncer_and_read_routing": True,
                "cursor_pagination_and_streaming": True,
                "outbox_and_specialized_workers": True,
                "modular_virtualized_frontend": True,
                "observability_and_capacity_contracts": True,
                "runbooks_present": True,
            },
            "enterprise-capacity": {
                **common,
                "openinfra_version": __version__,
                "capacity_certification": True,
                "status": "certified",
                "failures": [],
            },
            "multisite-chaos": {
                **common,
                "openinfra_version": __version__,
                "multisite_chaos_certification": True,
                "status": "passed",
                "failures": [],
            },
            "pra-pca": {
                **common,
                "openinfra_version": __version__,
                "pra_pca_certification": True,
                "failures": [],
            },
            "release-security": {
                **common,
                "openinfra_version": __version__,
                "complete": True,
                "release_security_certification": True,
                "offline_mode": False,
                "failures": [],
            },
            "release-packaging": {
                "release_version": __version__,
                "source_date_epoch": int(now.timestamp()),
                "complete": True,
                "release_packaging_certification": True,
                "trusted_signing_key": True,
                "failures": [],
            },
            "ga-go-no-go": {
                **common,
                "release_version": __version__,
                "decision": "GO",
                "authorized_for_ga": True,
                "trusted_signing_key": True,
                "source_commit": "a" * 40,
                "refusal_reasons": [],
            },
        }
        kinds = {
            "p20-contracts": "p20-contracts",
            "enterprise-capacity": "enterprise-capacity",
            "multisite-chaos": "multisite-chaos",
            "pra-pca": "pra-pca",
            "release-security": "release-security",
            "release-packaging": "release-packaging",
            "ga-go-no-go": "ga-go-no-go",
        }
        references: list[dict[str, str]] = []
        for identifier, payload in payloads.items():
            path = evidence_root / f"{identifier}.json"
            digest = cls._write(path, payload)
            references.append(
                {
                    "id": identifier,
                    "report_kind": kinds[identifier],
                    "path": path.name,
                    "sha256": digest,
                }
            )
        manifest = {
            "schema_version": 1,
            "gate_id": "GATE-09",
            "release_version": __version__,
            "candidate_id": f"openinfra-{__version__}-rc1",
            "source_commit": "a" * 40,
            "generated_at": now.isoformat(),
            "evidence": references,
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return policy_path, manifest_path, evidence_root

    def test_certifies_complete_current_immutable_evidence(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        policy_path, manifest_path, evidence_root = self._fixture(tmp_path, now=now)
        report = ScaleoutPromotionCertification.evaluate(
            ScaleoutPromotionPolicy.load(policy_path),
            ScaleoutPromotionManifest.load(manifest_path),
            evidence_root,
            now=now,
        )
        assert report["scaleout_promotion_certification"] is True
        assert report["authorized_for_enterprise_scaleout"] is True
        assert report["status"] == "certified"
        assert report["blockers"] == []
        assert len(report["criteria"]) == 7
        assert len(str(report["manifest_sha256"])) == 64

    def test_rejects_tampered_failed_and_stale_evidence(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        policy_path, manifest_path, evidence_root = self._fixture(tmp_path, now=now)
        capacity = evidence_root / "enterprise-capacity.json"
        payload = json.loads(capacity.read_text(encoding="utf-8"))
        payload["capacity_certification"] = False
        capacity.write_text(json.dumps(payload), encoding="utf-8")
        report = ScaleoutPromotionCertification.evaluate(
            ScaleoutPromotionPolicy.load(policy_path),
            ScaleoutPromotionManifest.load(manifest_path),
            evidence_root,
            now=now + timedelta(hours=25),
        )
        assert report["scaleout_promotion_certification"] is False
        blockers = "\n".join(str(item) for item in report["blockers"])
        assert "enterprise-capacity" in blockers
        assert "SHA-256 mismatch" in blockers
        assert "p20-contracts" in blockers
        assert "older than the allowed 24 hours" in blockers

    def test_rejects_noncanonical_hash_wrong_policy_and_path_escape(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        policy_path, manifest_path, _ = self._fixture(tmp_path, now=now)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["evidence"][0]["sha256"] = str(manifest["evidence"][0]["sha256"]).upper()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ScaleoutPromotionError, match="canonical lowercase"):
            ScaleoutPromotionManifest.load(manifest_path)

        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["gate_id"] = "GATE-07"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        with pytest.raises(ScaleoutPromotionError, match="GATE-09 / REL-10"):
            ScaleoutPromotionPolicy.load(policy_path)

        policy_path, manifest_path, evidence_root = self._fixture(tmp_path / "second", now=now)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["evidence"][0]["path"] = "../outside.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        report = ScaleoutPromotionCertification.evaluate(
            ScaleoutPromotionPolicy.load(policy_path),
            ScaleoutPromotionManifest.load(manifest_path),
            evidence_root,
            now=now,
        )
        assert report["scaleout_promotion_certification"] is False
        assert "escapes evidence root" in "\n".join(str(item) for item in report["blockers"])

    def test_policy_reference_manifest_and_json_validation_edges(self, tmp_path: Path) -> None:
        with pytest.raises(ScaleoutPromotionError, match="policy entries"):
            ScaleoutEvidencePolicy.from_mapping([])
        with pytest.raises(ScaleoutPromotionError, match="fields cannot be empty"):
            ScaleoutEvidencePolicy.from_mapping({"id": "", "report_kind": "x", "max_age_hours": 1})
        with pytest.raises(ScaleoutPromotionError, match="invalid max_age_hours"):
            ScaleoutEvidencePolicy.from_mapping(
                {"id": "x", "report_kind": "x", "max_age_hours": True}
            )
        with pytest.raises(ScaleoutPromotionError, match="references must be objects"):
            ScaleoutEvidenceReference.from_mapping("invalid")
        with pytest.raises(ScaleoutPromotionError, match="fields cannot be empty"):
            ScaleoutEvidenceReference.from_mapping(
                {"id": "x", "report_kind": "", "path": "x.json", "sha256": "a" * 64}
            )

        policy_path = tmp_path / "policy.json"
        policy_path.write_text("[]", encoding="utf-8")
        with pytest.raises(ScaleoutPromotionError, match="root must be an object"):
            ScaleoutPromotionPolicy.load(policy_path)
        policy_path.write_text("{", encoding="utf-8")
        with pytest.raises(ScaleoutPromotionError, match="invalid JSON"):
            ScaleoutPromotionPolicy.load(policy_path)
        missing = tmp_path / "missing.json"
        with pytest.raises(ScaleoutPromotionError, match="is missing"):
            ScaleoutJson.load_object(missing, "fixture")

        base = {
            "schema_version": 1,
            "gate_id": "GATE-09",
            "release_id": "REL-10",
            "required_evidence": [
                {"id": identifier, "report_kind": identifier, "max_age_hours": 1}
                for identifier in sorted(ScaleoutPromotionPolicy.EXPECTED_EVIDENCE)
            ],
        }
        bad_cases = (
            ({**base, "schema_version": 2}, "unsupported scale-out promotion policy schema"),
            ({**base, "required_evidence": "invalid"}, "must declare required_evidence"),
            (
                {
                    **base,
                    "required_evidence": base["required_evidence"] + [base["required_evidence"][0]],
                },
                "identifiers must be unique",
            ),
            (
                {**base, "required_evidence": base["required_evidence"][:-1]},
                "catalog is incomplete",
            ),
        )
        for index, (payload, message) in enumerate(bad_cases):
            path = tmp_path / f"bad-policy-{index}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with pytest.raises(ScaleoutPromotionError, match=message):
                ScaleoutPromotionPolicy.load(path)

        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        _, manifest_path, _ = self._fixture(tmp_path / "manifest-cases", now=now)
        original = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_cases = (
            ({**original, "schema_version": 2}, "unsupported scale-out promotion manifest schema"),
            ({**original, "gate_id": "GATE-07"}, "must target GATE-09"),
            ({**original, "release_version": "0.0.0"}, "release_version must match"),
            ({**original, "candidate_id": ""}, "candidate_id is invalid"),
            ({**original, "source_commit": "bad"}, "full lowercase SHA-1"),
            ({**original, "evidence": "invalid"}, "must list evidence"),
            (
                {**original, "evidence": original["evidence"] + [original["evidence"][0]]},
                "references must be unique",
            ),
            ({**original, "evidence": original["evidence"][:-1]}, "manifest evidence mismatch"),
        )
        for index, (payload, message) in enumerate(manifest_cases):
            path = tmp_path / f"bad-manifest-{index}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with pytest.raises(ScaleoutPromotionError, match=message):
                ScaleoutPromotionManifest.load(path)

        with pytest.raises(ScaleoutPromotionError, match="is required"):
            ScaleoutTime.parse(None, "time")
        with pytest.raises(ScaleoutPromotionError, match="ISO-8601"):
            ScaleoutTime.parse("not-a-date", "time")
        with pytest.raises(ScaleoutPromotionError, match="include a timezone"):
            ScaleoutTime.parse("2026-07-14T12:00:00", "time")
        with pytest.raises(ScaleoutPromotionError, match="canonical lowercase"):
            ScaleoutJson.require_sha256("G" * 64, "fixture")

    def test_inspector_rejects_invalid_shapes_timestamps_and_verdicts(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        root = tmp_path / "evidence"
        root.mkdir()
        policy = ScaleoutEvidencePolicy("capacity", "enterprise-capacity", 1)
        wrong_kind = ScaleoutEvidenceReference("capacity", "wrong", "x.json", "a" * 64)
        assert not ScaleoutEvidenceInspector.inspect(policy, wrong_kind, root, now, "a" * 40).passed

        missing = ScaleoutEvidenceReference(
            "capacity", "enterprise-capacity", "missing.json", "a" * 64
        )
        assert (
            "missing"
            in ScaleoutEvidenceInspector.inspect(policy, missing, root, now, "a" * 40).detail
        )

        invalid_json = root / "invalid.json"
        invalid_json.write_text("{", encoding="utf-8")
        invalid_ref = ScaleoutEvidenceReference(
            "capacity",
            "enterprise-capacity",
            invalid_json.name,
            hashlib.sha256(invalid_json.read_bytes()).hexdigest(),
        )
        assert (
            "invalid JSON"
            in ScaleoutEvidenceInspector.inspect(policy, invalid_ref, root, now, "a" * 40).detail
        )

        root_list = root / "list.json"
        root_list.write_text("[]", encoding="utf-8")
        list_ref = ScaleoutEvidenceReference(
            "capacity",
            "enterprise-capacity",
            root_list.name,
            hashlib.sha256(root_list.read_bytes()).hexdigest(),
        )
        assert (
            "root must be an object"
            in ScaleoutEvidenceInspector.inspect(policy, list_ref, root, now, "a" * 40).detail
        )

        future = root / "future.json"
        self._write(
            future,
            {
                "openinfra_version": __version__,
                "generated_at": (now + timedelta(hours=1)).isoformat(),
                "capacity_certification": True,
                "status": "certified",
                "failures": [],
            },
        )
        future_ref = ScaleoutEvidenceReference(
            "capacity",
            "enterprise-capacity",
            future.name,
            hashlib.sha256(future.read_bytes()).hexdigest(),
        )
        assert (
            "timestamp is in the future"
            in ScaleoutEvidenceInspector.inspect(policy, future_ref, root, now, "a" * 40).detail
        )

        missing_time = root / "missing-time.json"
        self._write(
            missing_time,
            {
                "openinfra_version": __version__,
                "capacity_certification": True,
                "status": "certified",
                "failures": [],
            },
        )
        missing_time_ref = ScaleoutEvidenceReference(
            "capacity",
            "enterprise-capacity",
            missing_time.name,
            hashlib.sha256(missing_time.read_bytes()).hexdigest(),
        )
        assert (
            "evidence generated_at is required"
            in ScaleoutEvidenceInspector.inspect(
                policy, missing_time_ref, root, now, "a" * 40
            ).detail
        )

        with pytest.raises(ScaleoutPromotionError, match="source_date_epoch"):
            ScaleoutEvidenceInspector.evidence_time("release-packaging", {})

        invalid_reports = {
            "p20-contracts": {"release_version": "0.0.0"},
            "enterprise-capacity": {
                "openinfra_version": __version__,
                "capacity_certification": False,
                "status": "rejected",
                "failures": ["x"],
            },
            "multisite-chaos": {
                "openinfra_version": __version__,
                "multisite_chaos_certification": False,
                "status": "failed",
                "failures": ["x"],
            },
            "pra-pca": {
                "openinfra_version": __version__,
                "pra_pca_certification": False,
                "failures": ["x"],
            },
            "release-security": {
                "openinfra_version": __version__,
                "complete": False,
                "release_security_certification": False,
                "offline_mode": True,
                "failures": ["x"],
            },
            "release-packaging": {
                "release_version": __version__,
                "complete": False,
                "release_packaging_certification": False,
                "trusted_signing_key": False,
                "failures": ["x"],
            },
            "ga-go-no-go": {
                "release_version": __version__,
                "decision": "NO-GO",
                "authorized_for_ga": False,
                "trusted_signing_key": False,
                "refusal_reasons": ["x"],
            },
            "unsupported": {"openinfra_version": __version__},
        }
        for kind, payload in invalid_reports.items():
            assert ScaleoutEvidenceInspector.report_failures(kind, payload)

    def test_manifest_time_and_ga_commit_are_blocking(self, tmp_path: Path) -> None:
        now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
        policy_path, manifest_path, evidence_root = self._fixture(tmp_path, now=now)
        ga_path = evidence_root / "ga-go-no-go.json"
        ga_payload = json.loads(ga_path.read_text(encoding="utf-8"))
        ga_payload["source_commit"] = "b" * 40
        digest = self._write(ga_path, ga_payload)
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for reference in manifest_payload["evidence"]:
            if reference["id"] == "ga-go-no-go":
                reference["sha256"] = digest
        manifest_payload["generated_at"] = (now + timedelta(hours=1)).isoformat()
        manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
        report = ScaleoutPromotionCertification.evaluate(
            ScaleoutPromotionPolicy.load(policy_path),
            ScaleoutPromotionManifest.load(manifest_path),
            evidence_root,
            now=now,
        )
        blockers = "\n".join(str(item) for item in report["blockers"])
        assert "manifest timestamp is in the future" in blockers
        assert "source_commit does not match" in blockers

        policy = ScaleoutPromotionPolicy.load(policy_path)
        manifest = ScaleoutPromotionManifest.load(manifest_path)
        truncated = ScaleoutPromotionManifest(
            manifest.schema_version,
            manifest.gate_id,
            manifest.release_version,
            manifest.candidate_id,
            manifest.source_commit,
            now - timedelta(hours=25),
            manifest.evidence[:-1],
        )
        report = ScaleoutPromotionCertification.evaluate(policy, truncated, evidence_root, now=now)
        blockers = "\n".join(str(item) for item in report["blockers"])
        assert "manifest is older than 24 hours" in blockers
        assert "required evidence reference is missing" in blockers

    def test_criterion_result_serialization(self) -> None:
        result = ScaleoutCriterionResult("x", "kind", "passed", "ok", "a" * 64)
        assert result.passed is True
        assert result.as_dict()["status"] == "passed"
