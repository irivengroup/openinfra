from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from openinfra.domain.common import ValidationError
from openinfra.quality.continuity_certification import (
    BackupRestoreEvidence,
    ContinuityEvidenceParser,
    PointInTimeRecoveryEvidence,
    PraPcaCertificationEvidence,
    ProcedureEvidence,
)


def _payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "profile_id": "openinfra-pra-pca-v1",
        "profile_version": 1,
        "edition": "enterprise",
        "generated_at": "2026-07-14T11:00:00+00:00",
        "plan": {
            "id": "plan-1",
            "active": True,
            "primary_site_code": "PARIS",
            "recovery_site_code": "LYON",
            "rpo_seconds": 300,
            "rto_seconds": 3600,
            "max_backup_age_seconds": 7200,
        },
        "dr_drill": {
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
        },
        "backup_restore": {
            "backup_id": "backup-1",
            "backup_completed_at": "2026-07-14T09:00:00+00:00",
            "restore_started_at": "2026-07-14T10:05:00+00:00",
            "restore_completed_at": "2026-07-14T10:20:00+00:00",
            "restore_verified": True,
            "integrity_verified": True,
            "encryption_verified": True,
        },
        "pitr": {
            "incident_at": "2026-07-14T10:00:00+00:00",
            "target_recovery_point_at": "2026-07-14T09:59:30+00:00",
            "recovered_point_at": "2026-07-14T09:59:20+00:00",
            "recovery_started_at": "2026-07-14T10:05:00+00:00",
            "recovery_completed_at": "2026-07-14T10:20:00+00:00",
            "consistency_verified": True,
        },
        "procedures": {
            "owner": "platform-sre",
            "approved_by": "continuity-manager",
            "reviewed_at": "2026-07-14T10:30:00+00:00",
            "steps": dict.fromkeys(PraPcaCertificationEvidence.required_procedures(), True),
        },
        "source_artifacts": [
            {"name": name, "sha256": character * 64, "size_bytes": index + 1}
            for index, (name, character) in enumerate(
                (
                    ("dr-plan", "a"),
                    ("dr-drill", "b"),
                    ("backup-restore", "c"),
                    ("pitr", "d"),
                    ("procedures", "e"),
                )
            )
        ],
    }
    payload["evidence_digest"] = PraPcaCertificationEvidence.digest_for(payload)
    return payload


def _signed(payload: dict[str, object]) -> dict[str, object]:
    payload["evidence_digest"] = PraPcaCertificationEvidence.digest_for(payload)
    return payload


def test_pra_pca_evidence_certifies_conservative_rpo_rto_measurements() -> None:
    evidence = PraPcaCertificationEvidence.from_mapping(_payload())
    report = evidence.certification_report()

    assert evidence.measured_rpo_seconds == 45
    assert evidence.measured_rto_seconds == 1200
    assert evidence.measured_backup_age_seconds == 3600
    assert report["pra_pca_certification"] is True
    assert report["status"] == "passed"
    assert report["failures"] == []
    assert report["measurements"] == {
        "rpo_seconds": 45,
        "rto_seconds": 1200,
        "backup_age_seconds": 3600,
        "pitr_target_deviation_seconds": 10,
    }


def test_pra_pca_certification_rejects_failed_controls_and_objectives() -> None:
    payload = _payload()
    plan = payload["plan"]
    drill = payload["dr_drill"]
    backup = payload["backup_restore"]
    pitr = payload["pitr"]
    procedures = payload["procedures"]
    assert isinstance(plan, dict)
    assert isinstance(drill, dict)
    assert isinstance(backup, dict)
    assert isinstance(pitr, dict)
    assert isinstance(procedures, dict)
    plan.update(
        {"active": False, "rpo_seconds": 20, "rto_seconds": 600, "max_backup_age_seconds": 1200}
    )
    drill.update(
        {
            "status": "failed",
            "replication_lag_seconds": 90,
            "backup_age_seconds": 4000,
            "measured_rto_seconds": 1800,
            "restore_verified": False,
            "recovery_available": False,
            "vip_reachable": False,
            "operator_confirmed": False,
            "failure_reasons": ["rto-exceeded"],
        }
    )
    backup.update(
        {"restore_verified": False, "integrity_verified": False, "encryption_verified": False}
    )
    pitr.update({"consistency_verified": False, "recovered_point_at": "2026-07-14T09:50:00+00:00"})
    steps = procedures["steps"]
    assert isinstance(steps, dict)
    steps["postmortem"] = False
    evidence = PraPcaCertificationEvidence.from_mapping(_signed(payload))
    failures = "\n".join(evidence.failures())

    assert "inactive" in failures
    assert "DR drill did not pass" in failures
    assert "failure reasons" in failures
    assert "restore_verified is not verified" in failures
    assert "recovery_available is not verified" in failures
    assert "vip_reachable is not verified" in failures
    assert "operator_confirmed is not verified" in failures
    assert "integrity_verified is not verified" in failures
    assert "encryption_verified is not verified" in failures
    assert "pitr.consistency_verified is not verified" in failures
    assert "measured RPO" in failures
    assert "measured RTO" in failures
    assert "measured backup age" in failures
    assert "deviates from requested target" in failures
    assert "postmortem" in failures
    assert evidence.certification_report()["pra_pca_certification"] is False


def test_pra_pca_evidence_rejects_tampering_wrong_plan_and_bad_artifacts() -> None:
    payload = _payload()
    plan = payload["plan"]
    assert isinstance(plan, dict)
    plan["rpo_seconds"] = 301
    with pytest.raises(ValidationError, match="digest mismatch"):
        PraPcaCertificationEvidence.from_mapping(payload)

    payload = _payload()
    drill = payload["dr_drill"]
    assert isinstance(drill, dict)
    drill["plan_id"] = "another-plan"
    with pytest.raises(ValidationError, match="does not belong"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    payload["source_artifacts"] = []
    with pytest.raises(ValidationError, match="exactly five"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    assert isinstance(artifacts[1], dict)
    artifacts[1]["name"] = "dr-plan"
    with pytest.raises(ValidationError, match="unique"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))


def test_profile_identity_edition_and_plan_contract_are_strict() -> None:
    cases = (
        ("profile_id", "unknown", "unsupported PRA/PCA"),
        ("profile_version", 2, "profile_version must be 1"),
        ("edition", "lite", "Pro or Enterprise"),
    )
    for field, value, message in cases:
        payload = _payload()
        payload[field] = value
        with pytest.raises(ValidationError, match=message):
            PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    plan = payload["plan"]
    assert isinstance(plan, dict)
    plan["recovery_site_code"] = "PARIS"
    with pytest.raises(ValidationError, match="must be different"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    plan = payload["plan"]
    assert isinstance(plan, dict)
    plan["rpo_seconds"] = 0
    with pytest.raises(ValidationError, match="strictly positive"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))


def test_dr_drill_and_procedure_payloads_are_strict() -> None:
    payload = _payload()
    drill = payload["dr_drill"]
    assert isinstance(drill, dict)
    drill["status"] = "unknown"
    with pytest.raises(ValidationError, match="passed or failed"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    drill = payload["dr_drill"]
    assert isinstance(drill, dict)
    drill["failure_reasons"] = "bad"
    with pytest.raises(ValidationError, match="JSON array"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    procedures = payload["procedures"]
    assert isinstance(procedures, dict)
    steps = procedures["steps"]
    assert isinstance(steps, dict)
    steps.pop("postmortem")
    with pytest.raises(ValidationError, match="exactly match"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    procedures = payload["procedures"]
    assert isinstance(procedures, dict)
    steps = procedures["steps"]
    assert isinstance(steps, dict)
    steps["postmortem"] = "yes"
    with pytest.raises(ValidationError, match="must be a boolean"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))


def test_backup_and_pitr_temporal_constraints_are_enforced() -> None:
    payload = _payload()
    backup = payload["backup_restore"]
    assert isinstance(backup, dict)
    backup["restore_completed_at"] = "2026-07-14T10:00:00+00:00"
    with pytest.raises(ValidationError, match="completion cannot precede"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))

    payload = _payload()
    backup = payload["backup_restore"]
    assert isinstance(backup, dict)
    backup["backup_completed_at"] = "2026-07-14T10:01:00+00:00"
    evidence = PraPcaCertificationEvidence.from_mapping(_signed(payload))
    with pytest.raises(ValidationError, match="after the incident"):
        _ = evidence.measured_backup_age_seconds

    for field, value, message in (
        ("target_recovery_point_at", "2026-07-14T10:01:00+00:00", "cannot be after"),
        ("recovered_point_at", "2026-07-14T10:01:00+00:00", "cannot be after"),
        ("recovery_started_at", "2026-07-14T09:59:00+00:00", "cannot start before"),
        ("recovery_completed_at", "2026-07-14T10:04:00+00:00", "cannot precede"),
    ):
        payload = _payload()
        pitr = payload["pitr"]
        assert isinstance(pitr, dict)
        pitr[field] = value
        with pytest.raises(ValidationError, match=message):
            PraPcaCertificationEvidence.from_mapping(_signed(payload))


def test_parser_rejects_invalid_scalar_types_and_timestamps() -> None:
    with pytest.raises(ValidationError, match="JSON object"):
        ContinuityEvidenceParser.mapping([], "value")
    with pytest.raises(ValidationError, match="1 to 256"):
        ContinuityEvidenceParser.text("", "value")
    with pytest.raises(ValidationError, match="boolean"):
        ContinuityEvidenceParser.boolean(1, "value")
    for value in (True, "bad", -1, float("inf")):
        with pytest.raises(ValidationError, match=r"numeric|finite"):
            ContinuityEvidenceParser.number(value, "value")
    with pytest.raises(ValidationError, match="integer"):
        ContinuityEvidenceParser.integer(1.5, "value")
    with pytest.raises(ValidationError, match="ISO-8601"):
        ContinuityEvidenceParser.timestamp("bad", "value")
    with pytest.raises(ValidationError, match="timezone-aware"):
        ContinuityEvidenceParser.timestamp("2026-07-14T10:00:00", "value")
    with pytest.raises(ValidationError, match="SHA-256"):
        ContinuityEvidenceParser.sha256("xyz", "value")


def test_backup_pitr_and_procedure_helpers_report_measurements() -> None:
    evidence = PraPcaCertificationEvidence.from_mapping(_payload())
    assert isinstance(evidence.backup_restore, BackupRestoreEvidence)
    assert evidence.backup_restore.age_at(datetime(2026, 7, 14, 10, tzinfo=UTC)) == 3600
    assert isinstance(evidence.pitr, PointInTimeRecoveryEvidence)
    assert evidence.pitr.measured_data_loss_seconds == 40
    assert evidence.pitr.measured_recovery_seconds == 1200
    assert evidence.pitr.target_deviation_seconds == 10
    assert isinstance(evidence.procedures, ProcedureEvidence)
    assert evidence.procedures.incomplete_steps == ()
    assert len(PraPcaCertificationEvidence.required_procedures()) == 10


def test_source_artifact_digest_requires_lowercase_sha256() -> None:
    payload = _payload()
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    broken = copy.deepcopy(artifacts)
    assert isinstance(broken[0], dict)
    broken[0]["sha256"] = "A" * 64
    payload["source_artifacts"] = broken
    with pytest.raises(ValidationError, match="lowercase SHA-256"):
        PraPcaCertificationEvidence.from_mapping(_signed(payload))
