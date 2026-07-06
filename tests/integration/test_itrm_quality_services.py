from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.it_resources_management_quality_services import (
    EvaluateItrmObjectQualityCommand,
    ItrmQualitySummaryCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_governance_services import CreateSourceGovernanceRuleCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import AccessDeniedError
from openinfra.interfaces.cli import OpenInfraCLI


def _bootstrap(app: object, token: str, roles: tuple[str, ...] = ("itrm:operator",)) -> None:
    app.security_service.bootstrap_token(  # type: ignore[attr-defined]
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="itrm-quality-admin",
            roles=roles,
            token=token,
        )
    )


def test_itrm_quality_certifies_complete_authoritative_device(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "r" * 40
    _bootstrap(app, token, ("itrm:governance-admin",))
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
            key="device/itrm-quality-001",
            kind="device",
            display_name="ITRM Quality 001",
            attributes_json=json.dumps({"serial": "SN001", "site": "PAR1"}),
            tags=("prod",),
            source="discovery-core",
        )
    )

    report = app.it_resources_management_quality_service.evaluate_object(
        EvaluateItrmObjectQualityCommand("default", token, "device/itrm-quality-001")
    )
    summary = app.it_resources_management_quality_service.summarize(
        ItrmQualitySummaryCommand("default", token, limit=10, kind="device")
    )

    assert report["domain"] == "it_resources_management"
    assert report["certification_status"] == "certified"
    assert report["score"] >= 90
    assert summary.certified == 1
    assert summary.rejected == 0


def test_itrm_quality_rejects_incomplete_and_warns_non_authoritative_source(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "s" * 40
    _bootstrap(app, token, ("itrm:governance-admin",))
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
            key="device/itrm-quality-002",
            kind="device",
            display_name="ITRM Quality 002",
            attributes_json=json.dumps({"serial": "SN002"}),
            tags=(),
            source="manual",
        )
    )

    report = app.it_resources_management_quality_service.evaluate_object(
        EvaluateItrmObjectQualityCommand("default", token, "device/itrm-quality-002")
    )
    codes = {issue["code"] for issue in report["issues"]}

    assert report["certification_status"] == "rejected"
    assert "required_attribute_missing" in codes
    assert "non_authoritative_source" in codes
    assert "no_tags" in codes


def test_itrm_quality_requires_dedicated_read_permission(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    writer_token = "t" * 40
    denied_token = "u" * 40
    _bootstrap(app, writer_token, ("itrm:operator",))
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
            key="device/itrm-quality-003",
            kind="device",
            display_name="ITRM Quality 003",
            attributes_json=json.dumps({"serial": "SN003", "site": "PAR1"}),
            tags=("prod",),
            source="manual",
        )
    )

    with pytest.raises(AccessDeniedError):
        app.it_resources_management_quality_service.evaluate_object(
            EvaluateItrmObjectQualityCommand("default", denied_token, "device/itrm-quality-003")
        )


def test_cli_itrm_quality_commands_and_sot_compatibility_alias(
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
            "itrm-quality-cli",
            "--role",
            "itrm:operator",
            "--token",
            token,
        ]
    )
    capsys.readouterr()
    OpenInfraCLI().run(
        [
            "itrm",
            "upsert-object",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--key",
            "device/itrm-quality-cli",
            "--kind",
            "device",
            "--display-name",
            "ITRM Quality CLI",
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
            "itrm",
            "quality-object",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--key",
            "device/itrm-quality-cli",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    summary_code = OpenInfraCLI().run(
        [
            "sot",
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
    captured_summary = capsys.readouterr()
    summary = json.loads(captured_summary.out)

    assert (
        "DEPRECATION: 'openinfra sot' is a legacy alias; use 'openinfra itrm'"
        in captured_summary.err
    )
    assert quality_code == 0
    assert summary_code == 0
    assert report["key"] == "device/itrm-quality-cli"
    assert summary["total"] == 1


def test_legacy_ri_quality_import_aliases_remain_compatible() -> None:
    from openinfra.application.it_resources_management_quality_services import (
        EvaluateItrmObjectQualityCommand,
        ITResourcesManagementQualityService,
        ItrmQualitySummaryCommand,
    )
    from openinfra.application.ressources_inventory_quality_services import (
        EvaluateRiObjectQualityCommand,
        RessourcesInventoryQualityService,
        RiQualitySummaryCommand,
    )

    assert EvaluateRiObjectQualityCommand is EvaluateItrmObjectQualityCommand
    assert RiQualitySummaryCommand is ItrmQualitySummaryCommand
    assert RessourcesInventoryQualityService is ITResourcesManagementQualityService
