from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from scripts.assemble_pra_pca_evidence import assemble_pra_pca_evidence
from scripts.certify_pra_pca import certify_pra_pca
from scripts.validate_pra_pca import validate_project

from openinfra.domain.common import ValidationError
from openinfra.quality.continuity_certification import PraPcaCertificationEvidence

ROOT = Path(__file__).resolve().parents[2]


def _write_inputs(root: Path) -> dict[str, Path]:
    paths = {
        "plan": root / "plan.json",
        "drill": root / "drill.json",
        "backup": root / "backup.json",
        "pitr": root / "pitr.json",
        "procedures": root / "procedures.json",
    }
    paths["plan"].write_text(
        json.dumps(
            {
                "id": "plan-1",
                "active": True,
                "primary_site_code": "PARIS",
                "recovery_site_code": "LYON",
                "rpo_seconds": 300,
                "rto_seconds": 3600,
                "max_backup_age_seconds": 7200,
            }
        ),
        encoding="utf-8",
    )
    paths["drill"].write_text(
        json.dumps(
            {
                "id": "drill-1",
                "plan_id": "plan-1",
                "status": "passed",
                "replication_lag_seconds": 45,
                "backup_age_seconds": 1800,
                "measured_rto_seconds": 900,
                "restore_verified": True,
                "recovery_available": True,
                "vip_reachable": True,
                "operator_confirmed": True,
                "failure_reasons": [],
            }
        ),
        encoding="utf-8",
    )
    paths["backup"].write_text(
        json.dumps(
            {
                "backup_id": "backup-1",
                "backup_completed_at": "2026-07-14T09:00:00+00:00",
                "restore_started_at": "2026-07-14T10:05:00+00:00",
                "restore_completed_at": "2026-07-14T10:20:00+00:00",
                "restore_verified": True,
                "integrity_verified": True,
                "encryption_verified": True,
            }
        ),
        encoding="utf-8",
    )
    paths["pitr"].write_text(
        json.dumps(
            {
                "incident_at": "2026-07-14T10:00:00+00:00",
                "target_recovery_point_at": "2026-07-14T09:59:30+00:00",
                "recovered_point_at": "2026-07-14T09:59:20+00:00",
                "recovery_started_at": "2026-07-14T10:05:00+00:00",
                "recovery_completed_at": "2026-07-14T10:20:00+00:00",
                "consistency_verified": True,
            }
        ),
        encoding="utf-8",
    )
    paths["procedures"].write_text(
        json.dumps(
            {
                "owner": "platform-sre",
                "approved_by": "continuity-manager",
                "reviewed_at": "2026-07-14T10:30:00+00:00",
                "steps": dict.fromkeys(PraPcaCertificationEvidence.required_procedures(), True),
            }
        ),
        encoding="utf-8",
    )
    return paths


def test_pra_pca_assembler_and_certifier_produce_hashed_positive_evidence(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    payload = assemble_pra_pca_evidence(
        profile_path=ROOT / "docs/operations/pra-pca-profile.json",
        edition="enterprise",
        plan_path=paths["plan"],
        drill_path=paths["drill"],
        backup_restore_path=paths["backup"],
        pitr_path=paths["pitr"],
        procedures_path=paths["procedures"],
        generated_at=datetime(2026, 7, 14, 11, tzinfo=UTC),
    )
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")
    report = certify_pra_pca(evidence_path)

    assert report["pra_pca_certification"] is True
    assert report["measurements"] == {
        "rpo_seconds": 45,
        "rto_seconds": 1200,
        "backup_age_seconds": 3600,
        "pitr_target_deviation_seconds": 10,
    }
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    assert len(artifacts) == 5
    assert all(isinstance(item, dict) and len(str(item["sha256"])) == 64 for item in artifacts)


def test_pra_pca_assembler_rejects_invalid_profile_and_naive_generation_time(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"profile_id": "wrong", "profile_version": 1}), encoding="utf-8")
    with pytest.raises(ValidationError, match="unsupported"):
        assemble_pra_pca_evidence(
            profile_path=profile,
            edition="enterprise",
            plan_path=paths["plan"],
            drill_path=paths["drill"],
            backup_restore_path=paths["backup"],
            pitr_path=paths["pitr"],
            procedures_path=paths["procedures"],
        )

    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "profile_id": "openinfra-pra-pca-v1",
                "profile_version": 1,
                "required_procedures": list(PraPcaCertificationEvidence.required_procedures()),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="timezone-aware"):
        assemble_pra_pca_evidence(
            profile_path=profile,
            edition="enterprise",
            plan_path=paths["plan"],
            drill_path=paths["drill"],
            backup_restore_path=paths["backup"],
            pitr_path=paths["pitr"],
            procedures_path=paths["procedures"],
            generated_at=datetime(2026, 7, 14, 11),
        )


def test_pra_pca_project_contract_and_workflow_are_complete() -> None:
    report = validate_project(ROOT)
    assert report == {
        "profile_id": "openinfra-pra-pca-v1",
        "profile_version": 1,
        "required_procedures": 10,
        "status": "passed",
    }
    workflow = (ROOT / ".github/workflows/pra-pca-certification.yml").read_text(encoding="utf-8")
    assert "pull_request_target:" not in workflow
    assert "--enforce" in workflow
    assert "retention-days: 90" in workflow
