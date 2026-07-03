from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.common import AccessDeniedError, NotFoundError, ValidationError
from openinfra.interfaces.cli import OpenInfraCLI


class TestSourceOfTruthServices:
    def test_object_relation_and_time_travel_lifecycle(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "z" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="sot-admin",
                roles=("sot:operator", "audit:reader"),
                token=admin_token,
            )
        )

        first = app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                key="device/srv-001",
                kind="device",
                display_name="Server 001",
                attributes_json='{"serial":"ABC","site":"PAR1"}',
                tags=("prod", "linux"),
                source="manual",
            )
        )
        app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                key="application/billing",
                kind="application",
                display_name="Billing",
                attributes_json='{"owner":"finance"}',
                tags=("prod",),
                source="manual",
            )
        )
        updated = app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                key="device/srv-001",
                kind="device",
                display_name="Server 001 renamed",
                attributes_json='{"serial":"ABC","site":"PAR1","rack":"R42"}',
                tags=("prod", "linux", "critical"),
                source="manual",
            )
        )
        relation = app.source_of_truth_service.create_relation(
            CreateSourceRelationCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                relation_type="runs_on",
                source_key="application/billing",
                target_key="device/srv-001",
                provenance="manual",
            )
        )
        listed = app.source_of_truth_service.list_objects(
            ListSourceObjectsCommand(
                tenant_id="default",
                admin_token=admin_token,
                limit=10,
                kind="device",
                tag="critical",
            )
        )
        relations = app.source_of_truth_service.list_relations(
            ListSourceRelationsCommand(
                tenant_id="default",
                admin_token=admin_token,
                limit=10,
                source_key="application/billing",
            )
        )
        version_one = app.source_of_truth_service.get_object_version(
            GetSourceObjectVersionCommand(
                tenant_id="default",
                admin_token=admin_token,
                key="device/srv-001",
                version=1,
            )
        )
        current = app.source_of_truth_service.get_object(
            GetSourceObjectCommand("default", admin_token, "device/srv-001")
        )

        assert first["version"] == 1
        assert updated["version"] == 2
        assert relation["relation_type"] == "runs_on"
        assert len(listed.items) == 1
        assert relations.items[0].target_key.value == "device/srv-001"
        assert version_one["payload"]["display_name"] == "Server 001"
        assert current["display_name"] == "Server 001 renamed"

    def test_access_denied_and_validation_errors_are_controlled(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        viewer_token = "v" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="sot-viewer",
                roles=("viewer",),
                token=viewer_token,
            )
        )
        with pytest.raises(AccessDeniedError):
            app.source_of_truth_service.upsert_object(
                UpsertSourceObjectCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=viewer_token,
                    key="device/srv-002",
                    kind="device",
                    display_name="Server 002",
                    attributes_json="{}",
                    tags=(),
                    source="manual",
                )
            )
        with pytest.raises(ValidationError):
            app.source_of_truth_service.list_objects(
                ListSourceObjectsCommand("default", viewer_token, limit=0)
            )
        with pytest.raises(NotFoundError):
            app.source_of_truth_service.get_object(
                GetSourceObjectCommand("default", viewer_token, "device/missing")
            )

    def test_cli_source_of_truth_lifecycle(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        token = "q" * 40
        OpenInfraCLI().run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--subject",
                "sot-cli-admin",
                "--role",
                "sot:operator",
                "--token",
                token,
            ]
        )
        capsys.readouterr()
        create_code = OpenInfraCLI().run(
            [
                "sot",
                "upsert-object",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--key",
                "device/srv-cli",
                "--kind",
                "device",
                "--display-name",
                "CLI Server",
                "--attributes-json",
                '{"serial":"CLI"}',
                "--tag",
                "prod",
                "--source",
                "manual",
            ]
        )
        created = json.loads(capsys.readouterr().out)
        list_code = OpenInfraCLI().run(
            [
                "sot",
                "list-objects",
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
        listed = json.loads(capsys.readouterr().out)
        version_code = OpenInfraCLI().run(
            [
                "sot",
                "get-object-version",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--key",
                "device/srv-cli",
                "--version",
                "1",
            ]
        )
        version = json.loads(capsys.readouterr().out)

        assert create_code == 0
        assert list_code == 0
        assert version_code == 0
        assert created["key"] == "device/srv-cli"
        assert listed["items"][0]["key"] == "device/srv-cli"
        assert version["payload"]["display_name"] == "CLI Server"

    def test_cli_source_relation_lifecycle(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        token = "u" * 40
        OpenInfraCLI().run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--subject",
                "sot-cli-admin-2",
                "--role",
                "sot:operator",
                "--token",
                token,
            ]
        )
        capsys.readouterr()
        for key, kind in (("application/app-cli", "application"), ("service/svc-cli", "service")):
            OpenInfraCLI().run(
                [
                    "sot",
                    "upsert-object",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--admin-token",
                    token,
                    "--key",
                    key,
                    "--kind",
                    kind,
                    "--display-name",
                    key,
                    "--source",
                    "manual",
                ]
            )
            capsys.readouterr()
        relation_code = OpenInfraCLI().run(
            [
                "sot",
                "create-relation",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--relation-type",
                "depends_on",
                "--source-key",
                "application/app-cli",
                "--target-key",
                "service/svc-cli",
                "--provenance",
                "manual",
            ]
        )
        relation = json.loads(capsys.readouterr().out)
        list_code = OpenInfraCLI().run(
            [
                "sot",
                "list-relations",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--source-key",
                "application/app-cli",
            ]
        )
        listed = json.loads(capsys.readouterr().out)

        assert relation_code == 0
        assert list_code == 0
        assert relation["target_key"] == "service/svc-cli"
        assert listed["items"][0]["relation_type"] == "depends_on"

    def test_service_error_branches_for_source_of_truth(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "m" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                tenant_id="default",
                actor="pytest",
                subject="sot-admin-errors",
                roles=("sot:operator",),
                token=token,
            )
        )
        with pytest.raises(ValidationError):
            app.source_of_truth_service.upsert_object(
                UpsertSourceObjectCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    key="device/error-json",
                    kind="device",
                    display_name="Broken JSON",
                    attributes_json="{bad-json",
                    tags=(),
                    source="manual",
                )
            )
        with pytest.raises(ValidationError):
            app.source_of_truth_service.upsert_object(
                UpsertSourceObjectCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    key="device/error-list",
                    kind="device",
                    display_name="Broken JSON list",
                    attributes_json="[]",
                    tags=(),
                    source="manual",
                )
            )
        with pytest.raises(NotFoundError):
            app.source_of_truth_service.get_object_version(
                GetSourceObjectVersionCommand("default", token, "device/missing", 1)
            )
        with pytest.raises(ValidationError):
            app.source_of_truth_service.get_object_version(
                GetSourceObjectVersionCommand("default", token, "device/missing", 0)
            )
        with pytest.raises(NotFoundError):
            app.source_of_truth_service.create_relation(
                CreateSourceRelationCommand(
                    tenant_id="default",
                    actor="pytest",
                    admin_token=token,
                    relation_type="runs_on",
                    source_key="application/missing",
                    target_key="device/missing",
                    provenance="manual",
                )
            )
