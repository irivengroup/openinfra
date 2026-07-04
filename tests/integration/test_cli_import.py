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

    assert OpenInfraCLI().run(
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
            "sot:operator",
            "--token",
            token,
        ]
    ) == 0
    capsys.readouterr()

    assert OpenInfraCLI().run(
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
    ) == 0
    created = json.loads(capsys.readouterr().out)

    assert created["status"] == "validated"
    assert created["dry_run"] is True
    assert OpenInfraCLI().run(
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
    ) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["create_count"] == 1
