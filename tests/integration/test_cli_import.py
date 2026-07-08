from __future__ import annotations

import json
from pathlib import Path

from openinfra.interfaces.cli import OpenInfraCLI


def test_cli_import_dataset_dry_run_and_report(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "c" * 40
    csv_file = tmp_path / "devices.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial\n"
        "device/cli-501,device,CLI 501,cli_import,prod,SN501\n",
        encoding="utf-8",
    )
    mapping = json.dumps(
        {
            "key": "asset_key",
            "kind": "kind",
            "display_name": "name",
            "source": "source",
            "tags": "tags",
            "attributes.serial": "serial",
        }
    )

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
                "import-cli",
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
                "import",
                "dataset",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--file",
                str(csv_file),
                "--format",
                "csv",
                "--mapping-json",
                mapping,
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)

    assert created["status"] == "validated"
    assert created["dry_run"] is True
    assert (
        OpenInfraCLI().run(
            [
                "import",
                "report",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--job-id",
                str(created["job_id"]),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["create_count"] == 1


def test_cli_bulk_import_dataset_report_and_checkpoint(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "bulk-state.json"
    token = "d" * 40
    csv_file = tmp_path / "bulk.csv"
    csv_file.write_text(
        "asset_key,kind,name,source,tags,serial\n"
        "device/cli-bulk-1,device,CLI Bulk 1,cli_import,prod,SN1\n"
        "device/cli-bulk-2,device,CLI Bulk 2,cli_import,prod,SN2\n",
        encoding="utf-8",
    )
    mapping = json.dumps(
        {
            "key": "asset_key",
            "kind": "kind",
            "display_name": "name",
            "source": "source",
            "tags": "tags",
            "attributes.serial": "serial",
        }
    )

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
                "bulk-import-cli",
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
                "import",
                "bulk-dataset",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--file",
                str(csv_file),
                "--format",
                "csv",
                "--mapping-json",
                mapping,
                "--batch-size",
                "1",
                "--checkpoint-interval",
                "1",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)

    assert created["status"] == "validated"
    assert created["metrics"]["batches_completed"] == 2
    assert (
        OpenInfraCLI().run(
            [
                "import",
                "bulk-report",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--job-id",
                str(created["job_id"]),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["job_id"] == created["job_id"]
    assert (
        OpenInfraCLI().run(
            [
                "import",
                "bulk-checkpoint",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--job-id",
                str(created["job_id"]),
            ]
        )
        == 0
    )
    checkpoint = json.loads(capsys.readouterr().out)
    assert checkpoint["next_row_number"] == 3

    assert (
        OpenInfraCLI().run(
            [
                "import",
                "bulk-progress",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--job-id",
                str(created["job_id"]),
            ]
        )
        == 0
    )
    progress = json.loads(capsys.readouterr().out)
    assert progress["job_id"] == created["job_id"]
    assert progress["next_row_number"] == 3
    assert progress["processed_rows"] == 2
    assert progress["batches_completed"] == 2
    assert progress["final_report_available"] is True


def test_cli_import_migration_template_plan_and_report(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "m" * 40
    csv_file = tmp_path / "glpi.csv"
    csv_file.write_text(
        "name,serial,inventory_number,location,status,user,groups\npc-01,SN-PC01,INV1,Paris,active,alice,desktop\n",
        encoding="utf-8",
    )

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
                "migration-cli",
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
                "import",
                "migration-template",
                "--data",
                str(data),
                "--source",
                "glpi",
            ]
        )
        == 0
    )
    template = json.loads(capsys.readouterr().out)
    assert template["source"] == "glpi"
    assert template["mapping"]["source"] == "literal:glpi_migration"

    assert (
        OpenInfraCLI().run(
            [
                "import",
                "migration-plan",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--source",
                "glpi",
                "--file",
                str(csv_file),
                "--format",
                "csv",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "validated"

    assert (
        OpenInfraCLI().run(
            [
                "import",
                "migration-report",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--job-id",
                report["job_id"],
            ]
        )
        == 0
    )
    persisted = json.loads(capsys.readouterr().out)
    assert persisted["job_id"] == report["job_id"]
