from __future__ import annotations

import json
from pathlib import Path

from tests.integration.test_kubernetes_capacity_services import seeded_capacity_application

from openinfra.interfaces.cli import OpenInfraCLI


def test_kubernetes_capacity_cli_report_trend_and_export(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    _app, token, snapshots = seeded_capacity_application(state)
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(["kubernetes", "latest-capacity", *common, "--cluster-key", "cluster-par-01"]) == 0
    )
    latest = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert latest["snapshot_id"] == snapshots[-1].id.value

    assert (
        cli.run(
            [
                "kubernetes",
                "capacity-trend",
                *common,
                "--cluster-key",
                "cluster-par-01",
                "--limit",
                "3",
            ]
        )
        == 0
    )
    trend = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert trend["snapshots_evaluated"] == 3

    assert (
        cli.run(
            [
                "kubernetes",
                "capacity-export",
                *common,
                "--snapshot-id",
                snapshots[0].id.value,
                "--format",
                "csv",
            ]
        )
        == 0
    )
    exported = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "scope,scope_key,observed_at" in exported
