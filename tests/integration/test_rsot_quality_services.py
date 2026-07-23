from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.rsot_quality_services import (
    EvaluateRsotObjectQualityCommand,
    RsotQualitySummaryCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_governance_services import CreateSourceGovernanceRuleCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import AccessDeniedError
from openinfra.interfaces.cli import OpenInfraCLI


def _bootstrap(app: object, token: str, roles: tuple[str, ...] = ("rsot:operator",)) -> None:
    app.security_service.bootstrap_token(  # type: ignore[attr-defined]
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="rsot-quality-admin",
            roles=roles,
            token=token,
        )
    )


def test_itrm_quality_certifies_complete_authoritative_device(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "r" * 40
    _bootstrap(app, token, ("rsot:governance-admin",))
    app.source_governance_service.create_rule(
        CreateSourceGovernanceRuleCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="serial-authority",
            object_kind="device",
            attribute_path="serial",
            authoritative_source="discovery-core",
            priority=100,
            freshness_seconds=None,
            conflict_strategy="reject",
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/rsot-quality-001",
            kind="device",
            display_name="RSOT Quality 001",
            attributes_json=json.dumps({"serial": "SN001", "site": "PAR1"}),
            tags=("prod",),
            source="discovery-core",
        )
    )

    report = app.rsot_quality_service.evaluate_object(
        EvaluateRsotObjectQualityCommand("default", token, "device/rsot-quality-001")
    )
    summary = app.rsot_quality_service.summarize(
        RsotQualitySummaryCommand("default", token, limit=10, kind="device")
    )

    assert report["domain"] == "rsot"
    assert report["certification_status"] == "certified"
    assert report["score"] >= 90
    assert summary.certified == 1
    assert summary.rejected == 0


def test_itrm_quality_rejects_incomplete_and_warns_non_authoritative_source(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "s" * 40
    _bootstrap(app, token, ("rsot:governance-admin",))
    app.source_governance_service.create_rule(
        CreateSourceGovernanceRuleCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="serial-authority",
            object_kind="device",
            attribute_path="serial",
            authoritative_source="discovery-core",
            priority=100,
            freshness_seconds=None,
            conflict_strategy="reject",
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/rsot-quality-002",
            kind="device",
            display_name="RSOT Quality 002",
            attributes_json=json.dumps({"serial": "SN002"}),
            tags=(),
            source="manual",
        )
    )

    report = app.rsot_quality_service.evaluate_object(
        EvaluateRsotObjectQualityCommand("default", token, "device/rsot-quality-002")
    )
    codes = {issue["code"] for issue in report["issues"]}
    non_authoritative_issue = next(
        issue for issue in report["issues"] if issue["code"] == "non_authoritative_source"
    )

    assert report["certification_status"] == "rejected"
    assert "required_attribute_missing" in codes
    assert "non_authoritative_source" in codes
    assert "no_tags" in codes
    assert non_authoritative_issue["field"] == "serial"
    assert non_authoritative_issue["expected_source"] == "discovery-core"
    assert non_authoritative_issue["actual_source"] == "manual"
    assert non_authoritative_issue["governance_rule"] == "serial-authority"


def test_itrm_quality_requires_dedicated_read_permission(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    writer_token = "t" * 40
    denied_token = "u" * 40
    _bootstrap(app, writer_token, ("rsot:operator",))
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="dcim-only",
            roles=("dcim:operator",),
            token=denied_token,
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=writer_token,
            key="device/rsot-quality-003",
            kind="device",
            display_name="RSOT Quality 003",
            attributes_json=json.dumps({"serial": "SN003", "site": "PAR1"}),
            tags=("prod",),
            source="manual",
        )
    )

    with pytest.raises(AccessDeniedError):
        app.rsot_quality_service.evaluate_object(
            EvaluateRsotObjectQualityCommand("default", denied_token, "device/rsot-quality-003")
        )


def test_cli_rsot_quality_commands_and_legacy_aliases_are_rejected(
    tmp_path: Path, capsys: object
) -> None:
    data = tmp_path / "state.json"
    token = "v" * 40
    OpenInfraCLI().run(
        [
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "rsot-quality-cli",
            "--role",
            "rsot:operator",
            "--token",
            token,
        ]
    )
    capsys.readouterr()
    OpenInfraCLI().run(
        [
            "rsot",
            "upsert-object",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--key",
            "device/rsot-quality-cli",
            "--kind",
            "device",
            "--display-name",
            "RSOT Quality CLI",
            "--attributes-json",
            '{"serial":"SNCLI","site":"PAR1"}',
            "--tag",
            "prod",
            "--source",
            "manual",
        ]
    )
    capsys.readouterr()
    quality_code = OpenInfraCLI().run(
        [
            "rsot",
            "quality-object",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--key",
            "device/rsot-quality-cli",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    summary_code = OpenInfraCLI().run(
        [
            "rsot",
            "quality-summary",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--kind",
            "device",
        ]
    )
    summary = json.loads(capsys.readouterr().out)

    assert quality_code == 0
    assert summary_code == 0
    assert report["key"] == "device/rsot-quality-cli"
    assert summary["total"] == 1
    for alias in ("itrm", "ri", "sot"):
        with pytest.raises(SystemExit) as exc_info:
            OpenInfraCLI().run([alias, "resource-taxonomy"])
        assert exc_info.value.code == 2
