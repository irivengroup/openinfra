from __future__ import annotations

import json
from pathlib import Path

from tests.integration.test_kubernetes_exposure_services import seeded_exposure_application

from openinfra.interfaces.cli import OpenInfraCLI


def test_kubernetes_exposure_cli_snapshot_and_latest_commands(
    tmp_path: Path, capsys: object
) -> None:
    state = tmp_path / "state.json"
    _app, token, snapshot = seeded_exposure_application(state)
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "kubernetes",
                "latest-exposure",
                *common,
                "--cluster-key",
                "cluster-par-01",
            ]
        )
        == 0
    )
    latest = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert latest["snapshot_id"] == snapshot.id.value

    assert (
        cli.run(
            [
                "kubernetes",
                "exposure",
                *common,
                "--snapshot-id",
                snapshot.id.value,
            ]
        )
        == 0
    )
    exact = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert exact["fingerprint"] == latest["fingerprint"]
