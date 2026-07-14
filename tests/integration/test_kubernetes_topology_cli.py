from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI


def test_kubernetes_topology_cli_complete_cycle(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "l" * 40
    app = ApplicationFactory().create_json_application(state, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-admin", ("admin",), token)
    )
    resources = tmp_path / "resources.json"
    resources.write_text(
        json.dumps(
            [
                {"kind": "namespace", "uid": "ns-prod", "name": "production"},
                {
                    "kind": "node",
                    "uid": "node-1",
                    "name": "worker-01",
                    "physical_path": {"server_key": "srv-01", "site_code": "par-01"},
                },
                {
                    "kind": "workload",
                    "uid": "deploy-api",
                    "name": "api",
                    "namespace": "production",
                },
                {
                    "kind": "pod",
                    "uid": "pod-api-1",
                    "name": "api-abc123",
                    "namespace": "production",
                    "node_name": "worker-01",
                    "owner_uid": "deploy-api",
                },
            ]
        ),
        encoding="utf-8",
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]
    assert (
        cli.run(
            [
                "kubernetes",
                "import",
                *common,
                "--cluster-key",
                "cluster-par-01",
                "--cluster-name",
                "prod-par-01",
                "--provider",
                "kubernetes",
                "--kubernetes-version",
                "v1.34.1",
                "--source-ref",
                "discovery:k8s-prod-par-01",
                "--observed-at",
                "2026-07-14T12:00:00Z",
                "--resources-file",
                str(resources),
                "--region",
                "eu-west",
                "--site-code",
                "par-01",
            ]
        )
        == 0
    )
    imported = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    snapshot_id = str(imported["id"])

    assert cli.run(["kubernetes", "list", *common, "--cluster-key", "cluster-par-01"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]
    assert cli.run(["kubernetes", "get", *common, "--snapshot-id", snapshot_id]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == snapshot_id  # type: ignore[attr-defined]
    assert cli.run(["kubernetes", "latest", *common, "--cluster-key", "cluster-par-01"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == snapshot_id  # type: ignore[attr-defined]
    assert cli.run(["kubernetes", "topology", *common, "--snapshot-id", snapshot_id]) == 0
    assert json.loads(capsys.readouterr().out)["edges"]  # type: ignore[attr-defined]
    assert (
        cli.run(["kubernetes", "latest-topology", *common, "--cluster-key", "cluster-par-01"]) == 0
    )
    assert json.loads(capsys.readouterr().out)["fingerprint"] == imported["fingerprint"]  # type: ignore[attr-defined]
