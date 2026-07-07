from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_governance_services import (
    CreateSourceGovernanceRuleCommand,
    DeactivateSourceGovernanceRuleCommand,
    EvaluateSourceGovernanceCommand,
    ListSourceGovernanceRulesCommand,
)
from openinfra.application.source_of_truth_services import (
    GetSourceObjectCommand,
    ListSourceObjectAuditCommand,
    ReconcileSourceObjectCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.domain.source_governance import (
    GovernedAttributePath,
    SourceGovernanceEvaluator,
    SourceGovernanceRule,
)
from openinfra.domain.source_of_truth import SourceObjectKind, SourceSystem
from openinfra.interfaces.cli import OpenInfraCLI


class TestSourceGovernanceServices:
    def test_authoritative_rule_blocks_non_authoritative_silent_overwrite(
        self,
        tmp_path: Path,
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "g" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default",
                "pytest",
                "governance-admin",
                ("itrm:governance-admin",),
                token,
            )
        )
        app.source_governance_service.create_rule(
            CreateSourceGovernanceRuleCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                name="serial-from-discovery",
                object_kind="device",
                attribute_path="serial",
                authoritative_source="discovery",
                priority=500,
                conflict_strategy="reject",
            )
        )
        created = app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key="device/gov-001",
                kind="device",
                display_name="Governed Server",
                attributes_json='{"serial":"ABC","rack":"R1"}',
                tags=("prod",),
                source="discovery",
            )
        )

        with pytest.raises(ConflictError):
            app.source_of_truth_service.upsert_object(
                UpsertSourceObjectCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    key="device/gov-001",
                    kind="device",
                    display_name="Governed Server",
                    attributes_json='{"serial":"XYZ","rack":"R1"}',
                    tags=("prod",),
                    source="manual",
                )
            )
        accepted = app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key="device/gov-001",
                kind="device",
                display_name="Governed Server",
                attributes_json='{"serial":"XYZ","rack":"R1"}',
                tags=("prod",),
                source="discovery",
            )
        )

        assert created["version"] == 1
        assert accepted["version"] == 2
        assert accepted["attributes"] == {
            "serial": "XYZ",
            "rack": "R1",
            "resource_category": "other",
            "resource_type": "unknown-device",
        }

    def test_list_evaluate_and_deactivate_rule(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "h" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "governance-admin", ("admin",), token)
        )
        rule = app.source_governance_service.create_rule(
            CreateSourceGovernanceRuleCommand(
                "default",
                "pytest",
                token,
                "owner-from-cmdb",
                "application",
                "owner.team",
                "cmdb",
                priority=900,
                freshness_seconds=3600,
                conflict_strategy="reject",
            )
        )
        page = app.source_governance_service.list_rules(
            ListSourceGovernanceRulesCommand("default", token, limit=10, object_kind="application")
        )
        evaluation = app.source_governance_service.evaluate(
            EvaluateSourceGovernanceCommand(
                "default",
                token,
                "application",
                "manual",
                '{"owner":{"team":"finance"}}',
                '{"owner":{"team":"risk"}}',
            )
        )
        deactivated = app.source_governance_service.deactivate_rule(
            DeactivateSourceGovernanceRuleCommand("default", "pytest", token, rule.name.value)
        )
        after = app.source_governance_service.list_rules(
            ListSourceGovernanceRulesCommand("default", token, include_inactive=True)
        )

        assert page.items[0].name.value == "owner-from-cmdb"
        assert evaluation["accepted"] is False
        assert evaluation["conflicts"][0]["attribute_path"] == "owner.team"
        assert deactivated["deactivated"] is True
        assert after.items[0].active is False

    def test_reconcile_object_plans_rejects_and_applies_authoritative_update(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "r" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default",
                "pytest",
                "reconcile-admin",
                ("itrm:governance-admin",),
                token,
            )
        )
        app.source_governance_service.create_rule(
            CreateSourceGovernanceRuleCommand(
                "default",
                "pytest",
                token,
                "serial-from-cmdb",
                "device",
                "serial",
                "cmdb",
                100,
                None,
                "reject",
            )
        )
        app.it_resources_management_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key="device/reconcile-001",
                kind="device",
                display_name="Reconcile 001",
                attributes_json='{"serial":"A","rack":"R1"}',
                tags=("prod",),
                source="cmdb",
            )
        )

        rejected = app.it_resources_management_service.reconcile_object(
            ReconcileSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key="device/reconcile-001",
                attributes_json='{"serial":"B","rack":"R2"}',
                source="manual",
                apply=True,
            )
        )
        applied = app.it_resources_management_service.reconcile_object(
            ReconcileSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key="device/reconcile-001",
                attributes_json='{"serial":"B","rack":"R2"}',
                source="cmdb",
                display_name="Reconciled 001",
                tags=("prod", "reconciled"),
                apply=True,
            )
        )
        current = app.it_resources_management_service.get_object(
            GetSourceObjectCommand("default", token, "device/reconcile-001")
        )
        audit = app.it_resources_management_service.list_object_audit(
            ListSourceObjectAuditCommand("default", token, "device/reconcile-001", limit=10)
        )

        assert rejected["accepted"] is False
        assert rejected["applied"] is False
        assert rejected["conflicts"][0]["attribute_path"] == "serial"
        assert rejected["result_attributes"] == {
            "serial": "A",
            "rack": "R1",
            "resource_category": "other",
            "resource_type": "unknown-device",
        }
        assert applied["accepted"] is True
        assert applied["applied"] is True
        assert applied["version"] == 2
        assert current["display_name"] == "Reconciled 001"
        assert current["attributes"] == {
            "serial": "B",
            "rack": "R2",
            "resource_category": "other",
            "resource_type": "unknown-device",
        }
        assert current["tags"] == ["prod", "reconciled"]
        assert [record.event.action for record in audit.items][:2] == [
            "itrm.reconciliation.apply",
            "itrm.reconciliation.plan",
        ]

    def test_cli_reconcile_object_supports_dry_run_and_apply(
        self, tmp_path: Path, capsys: object
    ) -> None:
        data = tmp_path / "state.json"
        token = "q" * 40
        assert (
            OpenInfraCLI().run(
                [
                    "security",
                    "bootstrap-token",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--subject",
                    "reconcile-cli",
                    "--role",
                    "itrm:operator",
                    "--token",
                    token,
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
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
                    "device/reconcile-cli",
                    "--kind",
                    "device",
                    "--display-name",
                    "Reconcile CLI",
                    "--attributes-json",
                    '{"serial":"CLI1"}',
                    "--source",
                    "manual",
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            OpenInfraCLI().run(
                [
                    "itrm",
                    "reconcile-object",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--admin-token",
                    token,
                    "--key",
                    "device/reconcile-cli",
                    "--attributes-json",
                    '{"serial":"CLI2"}',
                    "--source",
                    "manual",
                ]
            )
            == 0
        )
        planned = json.loads(capsys.readouterr().out)
        assert (
            OpenInfraCLI().run(
                [
                    "itrm",
                    "reconcile-object",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--admin-token",
                    token,
                    "--key",
                    "device/reconcile-cli",
                    "--attributes-json",
                    '{"serial":"CLI2"}',
                    "--source",
                    "manual",
                    "--apply",
                ]
            )
            == 0
        )
        applied = json.loads(capsys.readouterr().out)

        assert planned["accepted"] is True
        assert planned["applied"] is False
        assert applied["applied"] is True
        assert applied["object"]["attributes"] == {
            "serial": "CLI2",
            "resource_category": "other",
            "resource_type": "unknown-device",
        }

    def test_accept_with_audit_is_not_blocking_but_reports_conflict(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "i" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "governance-admin", ("admin",), token)
        )
        app.source_governance_service.create_rule(
            CreateSourceGovernanceRuleCommand(
                "default",
                "pytest",
                token,
                "tag-warn",
                None,
                "classification",
                "cmdb",
                10,
                None,
                "accept_with_audit",
            )
        )
        evaluation = app.source_governance_service.evaluate(
            EvaluateSourceGovernanceCommand(
                "default",
                token,
                "service",
                "manual",
                '{"classification":"gold"}',
                '{"classification":"silver"}',
            )
        )

        assert evaluation["accepted"] is True
        assert evaluation["conflicts"][0]["strategy"] == "accept_with_audit"

    def test_cli_governance_lifecycle(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        token = "j" * 40
        assert (
            OpenInfraCLI().run(
                [
                    "security",
                    "bootstrap-token",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--subject",
                    "gov-cli",
                    "--role",
                    "itrm:governance-admin",
                    "--token",
                    token,
                ]
            )
            == 0
        )
        capsys.readouterr()
        create_code = OpenInfraCLI().run(
            [
                "itrm",
                "create-governance-rule",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "cli-serial",
                "--object-kind",
                "device",
                "--attribute-path",
                "serial",
                "--authoritative-source",
                "discovery",
                "--priority",
                "300",
            ]
        )
        created = json.loads(capsys.readouterr().out)
        list_code = OpenInfraCLI().run(
            [
                "itrm",
                "list-governance-rules",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--object-kind",
                "device",
            ]
        )
        listed = json.loads(capsys.readouterr().out)
        eval_code = OpenInfraCLI().run(
            [
                "itrm",
                "evaluate-governance",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--object-kind",
                "device",
                "--incoming-source",
                "manual",
                "--existing-attributes-json",
                '{"serial":"A"}',
                "--incoming-attributes-json",
                '{"serial":"B"}',
            ]
        )
        evaluated = json.loads(capsys.readouterr().out)
        deactivate_code = OpenInfraCLI().run(
            [
                "itrm",
                "deactivate-governance-rule",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "cli-serial",
            ]
        )
        deactivated = json.loads(capsys.readouterr().out)

        assert create_code == list_code == eval_code == deactivate_code == 0
        assert created["name"] == "cli-serial"
        assert listed["items"][0]["authoritative_source"] == "discovery"
        assert evaluated["accepted"] is False
        assert deactivated["deactivated"] is True


class TestSourceGovernanceDomain:
    def test_validation_and_wildcard_matching(self) -> None:
        assert GovernedAttributePath.from_value("*").matches("owner.team") is True
        with pytest.raises(ValidationError):
            GovernedAttributePath.from_value("../unsafe")

    def test_evaluator_detects_nested_changes(self) -> None:
        rule = SourceGovernanceRule.create(
            tenant_id=TenantId.from_value("default"),
            name="nested-rule",
            object_kind="device",
            attribute_path="owner.team",
            authoritative_source="cmdb",
            priority=1,
            freshness_seconds=None,
            conflict_strategy="reject",
        )
        evaluation = SourceGovernanceEvaluator().evaluate(
            tenant_id=rule.tenant_id,
            object_kind=SourceObjectKind.DEVICE,
            incoming_source=SourceSystem.from_value("manual"),
            existing_attributes={"owner": {"team": "ops"}},
            incoming_attributes={"owner": {"team": "network"}},
            rules=(rule,),
        )
        assert evaluation.accepted is False
        assert evaluation.conflicts[0].existing_value == "ops"


def test_source_governance_evaluate_rejects_invalid_json(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "n" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "governance-json", ("admin",), token)
    )
    with pytest.raises(ValidationError):
        app.source_governance_service.evaluate(
            EvaluateSourceGovernanceCommand(
                "default",
                token,
                "device",
                "manual",
                "{invalid-json}",
                "{}",
            )
        )


def test_source_governance_evaluate_rejects_non_object_json(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "o" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "governance-json-array", ("admin",), token)
    )
    with pytest.raises(ValidationError):
        app.source_governance_service.evaluate(
            EvaluateSourceGovernanceCommand("default", token, "device", "manual", "[]", "{}")
        )
