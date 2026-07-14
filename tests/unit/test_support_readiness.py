from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openinfra.quality.release_packaging import ReleaseSignatureVerifier, ReleaseSigningMaterial
from openinfra.quality.support_readiness import (
    SupportPolicy,
    SupportReadinessError,
    SupportReadinessService,
)


class SupportReadinessFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.policy_path = root / "docs/release/support-maintenance-policy.json"
        self.policy_path.parent.mkdir(parents=True)
        for relative in (
            "docs/ga/SUPPORT.md",
            "docs/ga/UPGRADE.md",
            "docs/ga/TROUBLESHOOTING.md",
            "docs/runbooks/SUPPORT_MAINTENANCE.md",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Operational document\n\n" + ("validated content " * 80), encoding="utf-8"
            )
        self.payload = {
            "schema_version": 1,
            "epic": "EPIC-1806",
            "release_version": "0.33.1",
            "support_profiles": {
                "lite": self._profile(480, 1440, 48),
                "pro": self._profile(120, 240, 12),
                "enterprise": self._profile(30, 60, 4),
            },
            "lifecycle": {
                "stages": [
                    {
                        "name": "active",
                        "duration_months": 12,
                        "fixes": ["feature", "defect", "security"],
                    },
                    {"name": "maintenance", "duration_months": 6, "fixes": ["defect", "security"]},
                    {"name": "security-only", "duration_months": 6, "fixes": ["security"]},
                    {"name": "end-of-life", "duration_months": 0, "fixes": []},
                ]
            },
            "patch_policy": {
                "critical": {"mitigation_hours": 24, "fix_days": 3},
                "high": {"mitigation_hours": 72, "fix_days": 14},
                "medium": {"mitigation_hours": 336, "fix_days": 60},
                "low": {"mitigation_hours": 720, "fix_days": 180},
            },
            "migration_policy": {
                "direct_upgrade_span": 1,
                "staged_upgrade_span": 2,
                "backup_required": True,
                "rollback_required": True,
            },
            "escalation_matrix": [
                {"level": "L1", "owner": "support", "triggers": ["ticket"]},
                {"level": "L2", "owner": "engineering", "triggers": ["defect"]},
                {"level": "L3", "owner": "security-and-sre", "triggers": ["security incident"]},
                {"level": "incident-command", "owner": "commander", "triggers": ["s1"]},
            ],
            "required_documents": [
                "docs/ga/SUPPORT.md",
                "docs/ga/UPGRADE.md",
                "docs/ga/TROUBLESHOOTING.md",
                "docs/runbooks/SUPPORT_MAINTENANCE.md",
            ],
        }
        self.write()

    @staticmethod
    def _profile(response: int, update: int, restoration: int) -> dict[str, object]:
        return {
            "service_hours": "defined-hours",
            "channels": ["email"],
            "targets": {
                "S1": {
                    "response_minutes": response,
                    "update_minutes": update,
                    "restoration_hours": restoration,
                },
                "S2": {
                    "response_minutes": response * 2,
                    "update_minutes": update * 2,
                    "restoration_hours": restoration * 2,
                },
                "S3": {
                    "response_minutes": response * 4,
                    "update_minutes": update * 4,
                    "restoration_hours": restoration * 4,
                },
                "S4": {
                    "response_minutes": response * 8,
                    "update_minutes": update * 8,
                    "restoration_hours": restoration * 8,
                },
            },
        }

    def write(self) -> None:
        self.policy_path.write_text(json.dumps(self.payload), encoding="utf-8")


def test_support_policy_loads_complete_model(tmp_path: Path) -> None:
    fixture = SupportReadinessFixture(tmp_path)
    policy = SupportPolicy.load(fixture.policy_path)

    assert policy.epic == "EPIC-1806"
    assert policy.profile("enterprise").target("S1").response_minutes == 30
    assert sum(stage.duration_months for stage in policy.lifecycle) == 24


def test_support_readiness_writes_and_verifies_signed_evidence(tmp_path: Path) -> None:
    fixture = SupportReadinessFixture(tmp_path)
    output = tmp_path / "artifacts/support-readiness.json"
    signing = ReleaseSigningMaterial.generate_ephemeral()

    report = SupportReadinessService().evaluate_and_write(
        project_root=tmp_path,
        output_path=output,
        signing_material=signing,
        now=datetime(2026, 7, 13, 18, 0, tzinfo=UTC),
    )

    assert report.support_readiness is True
    assert report.complete is True
    assert report.profile_count == 3
    assert report.lifecycle_months == 24
    ReleaseSignatureVerifier.verify(
        output.with_suffix(".json.pub"), output, output.with_suffix(".json.sig")
    )


def test_support_readiness_without_signature_is_not_complete(tmp_path: Path) -> None:
    SupportReadinessFixture(tmp_path)

    report = SupportReadinessService().evaluate(tmp_path)

    assert report.support_readiness is False
    assert report.failures == ("support readiness report is not signed",)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"epic": "EPIC-0000"}), "EPIC-1806"),
        (
            lambda value: value["support_profiles"].pop("lite"),
            "lite, pro and enterprise",
        ),
        (
            lambda value: value["lifecycle"]["stages"].reverse(),
            "incomplete or out of order",
        ),
        (
            lambda value: value["migration_policy"].update({"backup_required": False}),
            "backup and rollback",
        ),
        (lambda value: value.update({"schema_version": 2}), "unsupported support policy schema"),
        (lambda value: value.update({"release_version": "0.0.0"}), "does not match"),
        (lambda value: value["support_profiles"].update({"lite": []}), "must be an object"),
        (
            lambda value: value["support_profiles"]["lite"].pop("targets"),
            "must declare targets",
        ),
        (
            lambda value: value["support_profiles"]["lite"].update({"service_hours": ""}),
            "service_hours is required",
        ),
        (
            lambda value: value["patch_policy"]["critical"].update({"fix_days": 365}),
            "patch deadlines must relax",
        ),
        (
            lambda value: value["escalation_matrix"][1].update({"owner": "support"}),
            "owners must be unique",
        ),
        (
            lambda value: [
                level.update({"triggers": ["generic"]}) for level in value["escalation_matrix"]
            ],
            "must contain a security trigger",
        ),
    ],
)
def test_support_policy_rejects_invalid_contracts(
    tmp_path: Path, mutation: object, message: str
) -> None:
    fixture = SupportReadinessFixture(tmp_path)
    mutation(fixture.payload)  # type: ignore[operator]
    fixture.write()

    with pytest.raises(SupportReadinessError, match=message):
        SupportPolicy.load(fixture.policy_path)


def test_support_readiness_rejects_missing_or_short_document(tmp_path: Path) -> None:
    fixture = SupportReadinessFixture(tmp_path)
    (tmp_path / "docs/ga/SUPPORT.md").write_text("short", encoding="utf-8")

    report = SupportReadinessService().evaluate(
        tmp_path, signing_material=ReleaseSigningMaterial.generate_ephemeral()
    )

    assert report.support_readiness is False
    assert "not operational" in report.failures[0]
