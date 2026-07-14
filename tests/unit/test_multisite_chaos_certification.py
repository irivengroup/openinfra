from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from openinfra.domain.common import ValidationError
from openinfra.quality.multisite_chaos import MultisiteChaosCampaignEvidence


def _scenario(name: str) -> dict[str, object]:
    return {
        "scenario": name,
        "started_at": "2026-07-14T10:00:00+00:00",
        "completed_at": "2026-07-14T10:01:00+00:00",
        "fault_injected": True,
        "controlled_degradation": True,
        "recovery_completed": True,
        "rollback_verified": True,
        "data_integrity_verified": True,
        "corruption_detected": False,
        "acknowledged_work_lost": False,
        "recovery_seconds": 30.0,
        "availability_ratio": 0.99,
        "error_rate": 0.01,
        "probe_count": 30,
        "integrity_sha256_before": "a" * 64,
        "integrity_sha256_after": "a" * 64,
    }


def _payload() -> dict[str, object]:
    scenarios = MultisiteChaosCampaignEvidence.required_scenarios()
    payload: dict[str, object] = {
        "profile_id": "openinfra-multisite-chaos-v1",
        "profile_version": 1,
        "edition": "enterprise",
        "topology_id": "enterprise-eu-west",
        "generated_at": "2026-07-14T12:00:00+00:00",
        "objectives": {
            name: {
                "max_recovery_seconds": 120,
                "min_availability_ratio": 0.95,
                "max_error_rate": 0.05,
            }
            for name in scenarios
        },
        "scenarios": [_scenario(name) for name in scenarios],
        "source_artifacts": [
            {"name": name, "sha256": f"{index:x}" * 64, "size_bytes": index + 1}
            for index, name in enumerate(scenarios, start=1)
        ],
    }
    payload["evidence_digest"] = MultisiteChaosCampaignEvidence.digest_for(payload)
    return payload


def _signed(payload: dict[str, object]) -> dict[str, object]:
    payload["evidence_digest"] = MultisiteChaosCampaignEvidence.digest_for(payload)
    return payload


def test_multisite_chaos_campaign_certifies_six_controlled_scenarios() -> None:
    evidence = MultisiteChaosCampaignEvidence.from_mapping(_payload())
    report = evidence.certification_report()

    assert evidence.generated_at == datetime(2026, 7, 14, 12, tzinfo=UTC)
    assert report["multisite_chaos_certification"] is True
    assert report["status"] == "passed"
    assert report["scenario_count"] == 6
    assert report["failures"] == []


def test_multisite_chaos_campaign_rejects_tampering_and_incomplete_sets() -> None:
    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenario = scenarios[0]
    assert isinstance(scenario, dict)
    scenario["recovery_seconds"] = 31
    with pytest.raises(ValidationError, match="digest mismatch"):
        MultisiteChaosCampaignEvidence.from_mapping(payload)

    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenarios.pop()
    with pytest.raises(ValidationError, match="exactly six"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    assert isinstance(artifacts[1], dict)
    artifacts[1]["name"] = artifacts[0]["name"]
    with pytest.raises(ValidationError, match="unique"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))


def test_multisite_chaos_campaign_reports_all_safety_and_slo_failures() -> None:
    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    first = scenarios[0]
    assert isinstance(first, dict)
    first.update(
        {
            "fault_injected": False,
            "controlled_degradation": False,
            "recovery_completed": False,
            "rollback_verified": False,
            "data_integrity_verified": False,
            "corruption_detected": True,
            "acknowledged_work_lost": True,
            "recovery_seconds": 200,
            "availability_ratio": 0.5,
            "error_rate": 0.5,
            "integrity_sha256_after": "b" * 64,
        }
    )
    evidence = MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))
    failures = "\n".join(evidence.failures())

    assert "fault was not injected" in failures
    assert "degradation was not controlled" in failures
    assert "service did not recover" in failures
    assert "fault rollback was not verified" in failures
    assert "data integrity was not verified" in failures
    assert "data corruption was detected" in failures
    assert "acknowledged work was lost" in failures
    assert "integrity digest changed" in failures
    assert "recovery 200.000s exceeds" in failures
    assert "availability 0.500000 is below" in failures
    assert "error rate 0.500000 exceeds" in failures
    assert evidence.certification_report()["multisite_chaos_certification"] is False


def test_multisite_chaos_profile_and_measurements_are_strict() -> None:
    for field, value, message in (
        ("profile_id", "wrong", "unsupported"),
        ("profile_version", 2, "must be 1"),
        ("edition", "pro", "Enterprise edition"),
    ):
        payload = _payload()
        payload[field] = value
        with pytest.raises(ValidationError, match=message):
            MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    objectives = payload["objectives"]
    assert isinstance(objectives, dict)
    objectives.pop("frontend-loss")
    with pytest.raises(ValidationError, match="exactly match"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    objectives = payload["objectives"]
    assert isinstance(objectives, dict)
    network = objectives["network-partition"]
    assert isinstance(network, dict)
    network["min_availability_ratio"] = 1.1
    with pytest.raises(ValidationError, match="between 0 and 1"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenario = scenarios[0]
    assert isinstance(scenario, dict)
    scenario["probe_count"] = 0
    with pytest.raises(ValidationError, match="strictly positive"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))


def test_multisite_chaos_evidence_rejects_noncanonical_sha_and_bad_time_order() -> None:
    payload = _payload()
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)
    artifact["sha256"] = "A" * 64
    with pytest.raises(ValidationError, match="lowercase SHA-256"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenario = scenarios[0]
    assert isinstance(scenario, dict)
    scenario["completed_at"] = "2026-07-14T09:59:59+00:00"
    with pytest.raises(ValidationError, match="cannot precede"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = copy.deepcopy(_payload())
    payload["generated_at"] = "2026-07-14T12:00:00"
    with pytest.raises(ValidationError, match="timezone-aware"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))


def test_multisite_chaos_parser_rejects_invalid_scalar_contracts() -> None:
    from openinfra.quality.multisite_chaos import MultisiteChaosParser

    cases = (
        (lambda: MultisiteChaosParser.mapping([], "field"), "JSON object"),
        (lambda: MultisiteChaosParser.text("", "field"), "1 to 256"),
        (lambda: MultisiteChaosParser.boolean("true", "field"), "boolean"),
        (lambda: MultisiteChaosParser.number(True, "field"), "numeric"),
        (lambda: MultisiteChaosParser.number("bad", "field"), "numeric"),
        (lambda: MultisiteChaosParser.number("nan", "field"), "finite and non-negative"),
        (lambda: MultisiteChaosParser.integer(1.5, "field"), "integer"),
        (lambda: MultisiteChaosParser.timestamp("not-a-time", "field"), "ISO-8601"),
    )
    for action, message in cases:
        with pytest.raises(ValidationError, match=message):
            action()


def test_multisite_chaos_rejects_remaining_objective_scenario_and_artifact_edges() -> None:
    payload = _payload()
    objectives = payload["objectives"]
    assert isinstance(objectives, dict)
    network = objectives["network-partition"]
    assert isinstance(network, dict)
    network["max_recovery_seconds"] = 0
    with pytest.raises(ValidationError, match="strictly positive"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    objectives = payload["objectives"]
    assert isinstance(objectives, dict)
    network = objectives["network-partition"]
    assert isinstance(network, dict)
    network["max_error_rate"] = 2
    with pytest.raises(ValidationError, match="between 0 and 1"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenario = scenarios[0]
    assert isinstance(scenario, dict)
    scenario["scenario"] = "unknown"
    with pytest.raises(ValidationError, match="unsupported"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    scenario = scenarios[0]
    assert isinstance(scenario, dict)
    scenario["availability_ratio"] = 2
    with pytest.raises(ValidationError, match="between 0 and 1"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    first = scenarios[0]
    second = scenarios[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    second["scenario"] = first["scenario"]
    with pytest.raises(ValidationError, match="incomplete or duplicated"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    payload["source_artifacts"] = {}
    with pytest.raises(ValidationError, match="exactly six source artifacts"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)
    artifact["size_bytes"] = 0
    with pytest.raises(ValidationError, match="strictly positive"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))

    payload = _payload()
    artifacts = payload["source_artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)
    artifact["name"] = "unexpected"
    with pytest.raises(ValidationError, match="exactly match required scenarios"):
        MultisiteChaosCampaignEvidence.from_mapping(_signed(payload))
