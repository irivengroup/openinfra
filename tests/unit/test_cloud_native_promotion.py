from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts.run_cloud_native_qualification import CloudNativeRuntimeQualification

from openinfra import __version__
from openinfra.quality.cloud_native_promotion import (
    CloudNativeEvidenceInspector,
    CloudNativePromotionCertification,
    CloudNativePromotionError,
    CloudNativePromotionManifest,
    CloudNativePromotionPolicy,
)

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
COMMIT = "a" * 40


def _payload(report_kind: str, epic: str) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": 1,
        "report_kind": report_kind,
        "release_version": __version__,
        "generated_at": NOW.isoformat(),
        "complete": True,
        "phase": "P21",
        "epic": epic,
        "release": "REL-11",
        "api_cli_web_parity": True,
    }
    if epic == "EPIC-2101":
        base.update(
            physical_mapping=True,
            secret_values_rejected=True,
            max_resources_per_snapshot=50_000,
        )
    elif epic == "EPIC-2102":
        base.update(
            network_flow_correlation=True,
            rsot_dependency_correlation=True,
            read_only_projection=True,
        )
    elif epic == "EPIC-2103":
        base.update(
            image_sbom_correlation=True,
            contextual_vulnerability_findings=True,
            certificate_correlation=True,
            secret_material_ingestion=False,
            masked_secret_references=True,
            legacy_snapshot_fingerprint_compatibility=True,
        )
    elif epic == "EPIC-2104":
        base.update(
            immutable_expected_state=True,
            immutable_observed_state=True,
            deterministic_drift=True,
            audit_enabled=True,
            transactional_outbox=True,
            automatic_remediation=False,
        )
    elif epic == "EPIC-2105":
        base.update(
            cluster_capacity=True,
            namespace_capacity=True,
            bounded_trends=True,
            alerts=True,
            json_csv_exports=True,
            max_trend_resources=1_000_000,
        )
    elif report_kind == "cloud-native-runtime-qualification":
        base.update(
            gate_id="GATE-10",
            qualified_cluster_count=3,
            max_resources_per_snapshot=50_000,
            multi_cluster_verified=True,
            max_snapshot_size_verified=True,
            deterministic_fingerprints=True,
            physical_mapping_verified=True,
            capacity_read_model_verified=True,
            secrets_rejected=True,
            cross_namespace_references_rejected=True,
            orphan_physical_paths_rejected=True,
            performance_budget_met=True,
            status="passed",
            failures=[],
        )
    elif report_kind == "cloud-native-qualification-contract":
        base.update(
            gate_id="GATE-10",
            all_epic_validators_present=True,
            runtime_benchmark_present=True,
            immutable_evidence=True,
            path_traversal_protection=True,
            freshness_enforced=True,
            ci_gate_blocking=True,
            runbook_present=True,
            packaging_verified=True,
            no_new_migration=True,
        )
    return base


def _write_gate_files(root: Path) -> tuple[Path, Path, Path]:
    policy_path = root / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate_id": "GATE-10",
                "release_id": "REL-11",
                "required_evidence": [
                    {"id": identifier, "report_kind": kind, "max_age_hours": 24}
                    for identifier, kind in CloudNativePromotionPolicy.EXPECTED_EVIDENCE.items()
                ],
            }
        ),
        encoding="utf-8",
    )
    evidence_root = root / "evidence"
    evidence_root.mkdir()
    epic_by_identifier = {
        "epic-2101-topology": "EPIC-2101",
        "epic-2102-exposure": "EPIC-2102",
        "epic-2103-security": "EPIC-2103",
        "epic-2104-gitops": "EPIC-2104",
        "epic-2105-capacity": "EPIC-2105",
        "epic-2106-runtime": "EPIC-2106",
        "epic-2106-contract": "EPIC-2106",
    }
    references: list[dict[str, str]] = []
    for identifier, report_kind in CloudNativePromotionPolicy.EXPECTED_EVIDENCE.items():
        raw = json.dumps(
            _payload(report_kind, epic_by_identifier[identifier]), sort_keys=True
        ).encode()
        evidence_path = evidence_root / f"{identifier}.json"
        evidence_path.write_bytes(raw)
        references.append(
            {
                "id": identifier,
                "report_kind": report_kind,
                "path": evidence_path.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate_id": "GATE-10",
                "release_version": __version__,
                "candidate_id": f"openinfra-{__version__}-{COMMIT}",
                "source_commit": COMMIT,
                "generated_at": NOW.isoformat(),
                "evidence": references,
            }
        ),
        encoding="utf-8",
    )
    return policy_path, manifest_path, evidence_root


def test_gate_10_certifies_complete_current_and_pinned_evidence(tmp_path: Path) -> None:
    policy_path, manifest_path, evidence_root = _write_gate_files(tmp_path)
    report = CloudNativePromotionCertification.evaluate(
        CloudNativePromotionPolicy.load(policy_path),
        CloudNativePromotionManifest.load(manifest_path),
        evidence_root,
        NOW + timedelta(minutes=1),
    )

    assert report["status"] == "certified"
    assert report["cloud_native_promotion_certification"] is True
    assert report["authorized_for_cloud_native_release"] is True
    assert len(report["criteria"]) == 7
    assert report["blockers"] == []


def test_gate_10_rejects_tampered_stale_and_unsafe_security_evidence(tmp_path: Path) -> None:
    policy_path, manifest_path, evidence_root = _write_gate_files(tmp_path)
    security_path = evidence_root / "epic-2103-security.json"
    payload = json.loads(security_path.read_text(encoding="utf-8"))
    payload["secret_material_ingestion"] = True
    payload["generated_at"] = (NOW - timedelta(hours=25)).isoformat()
    security_path.write_text(json.dumps(payload), encoding="utf-8")

    report = CloudNativePromotionCertification.evaluate(
        CloudNativePromotionPolicy.load(policy_path),
        CloudNativePromotionManifest.load(manifest_path),
        evidence_root,
        NOW,
    )

    assert report["status"] == "rejected"
    assert report["cloud_native_promotion_certification"] is False
    assert any("SHA-256 mismatch" in blocker for blocker in report["blockers"])


def test_evidence_path_traversal_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    root = tmp_path / "evidence"
    root.mkdir()

    with pytest.raises(CloudNativePromotionError, match="escapes evidence root"):
        CloudNativeEvidenceInspector.resolve(root, "../outside.json")


def test_policy_and_manifest_reject_catalog_drift(tmp_path: Path) -> None:
    policy_path, manifest_path, _ = _write_gate_files(tmp_path)
    policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
    policy_payload["required_evidence"].pop()
    policy_path.write_text(json.dumps(policy_payload), encoding="utf-8")
    with pytest.raises(CloudNativePromotionError, match="catalog"):
        CloudNativePromotionPolicy.load(policy_path)

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["source_commit"] = "short"
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
    with pytest.raises(CloudNativePromotionError, match="SHA-1"):
        CloudNativePromotionManifest.load(manifest_path)


def test_runtime_qualification_probes_are_effective() -> None:
    assert CloudNativeRuntimeQualification._secret_probe() is True
    assert CloudNativeRuntimeQualification._cross_namespace_probe(NOW) is True
    assert CloudNativeRuntimeQualification._orphan_path_probe() is True
    assert CloudNativeRuntimeQualification._deterministic_probe(NOW) is True
    assert CloudNativeRuntimeQualification._capacity_probe(NOW) is True


def test_runtime_qualification_enforces_multi_cluster_and_scale_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_snapshot(index: int, resource_count: int, _observed_at: datetime) -> SimpleNamespace:
        return SimpleNamespace(
            cluster_key=f"cluster-{index}",
            resources=tuple(range(resource_count)),
            summary=lambda: {
                "resource_count": resource_count,
                "mapping_coverage_percent": 100.0,
            },
        )

    monkeypatch.setattr(CloudNativeRuntimeQualification, "_build_snapshot", fake_snapshot)
    monkeypatch.setattr(CloudNativeRuntimeQualification, "_deterministic_probe", lambda _now: True)
    monkeypatch.setattr(CloudNativeRuntimeQualification, "_capacity_probe", lambda _now: True)
    monkeypatch.setattr(CloudNativeRuntimeQualification, "_secret_probe", lambda: True)
    monkeypatch.setattr(
        CloudNativeRuntimeQualification, "_cross_namespace_probe", lambda _now: True
    )
    monkeypatch.setattr(CloudNativeRuntimeQualification, "_orphan_path_probe", lambda: True)

    report = CloudNativeRuntimeQualification.run(
        cluster_count=3,
        resources_per_snapshot=50_000,
        max_seconds=30,
    )

    assert report["status"] == "passed"
    assert report["qualified_cluster_count"] == 3
    assert report["max_resources_per_snapshot"] == 50_000
