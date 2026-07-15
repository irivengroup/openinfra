from __future__ import annotations

import json
from pathlib import Path

from tests.integration.test_kubernetes_gitops_services import seeded_gitops_application

from openinfra.interfaces.cli import OpenInfraCLI


def test_kubernetes_gitops_cli_import_list_get_latest_and_drift(
    tmp_path: Path, capsys: object
) -> None:
    state_path = tmp_path / "gitops-cli.json"
    _app, token, expected, observed = seeded_gitops_application(state_path)
    cli = OpenInfraCLI()
    common = ["--data", str(state_path), "--tenant", "default", "--admin-token", token]

    assert cli.run(["kubernetes", "gitops-list", *common, "--cluster-key", "cluster-par-01"]) == 0
    page = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert page["items"][0]["id"] == expected.id.value

    assert cli.run(["kubernetes", "gitops-get", *common, "--state-id", expected.id.value]) == 0
    exact = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert exact["revision"] == "b" * 40

    assert cli.run(["kubernetes", "gitops-latest", *common, "--cluster-key", "cluster-par-01"]) == 0
    latest = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert latest["fingerprint"] == expected.fingerprint

    assert (
        cli.run(
            [
                "kubernetes",
                "gitops-drift",
                *common,
                "--expected-state-id",
                expected.id.value,
                "--observed-snapshot-id",
                observed.id.value,
            ]
        )
        == 0
    )
    drift = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert drift["status"] == "drift"
    assert drift["automatic_remediation"] is False

    assert (
        cli.run(
            [
                "kubernetes",
                "gitops-latest-drift",
                *common,
                "--cluster-key",
                "cluster-par-01",
            ]
        )
        == 0
    )
    latest_drift = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert latest_drift["fingerprint"] == drift["fingerprint"]

    resources = tmp_path / "resources.json"
    resources.write_text(json.dumps(exact["resources"]), encoding="utf-8")
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(exact["policy"]), encoding="utf-8")
    assert (
        cli.run(
            [
                "kubernetes",
                "gitops-import",
                *common,
                "--cluster-key",
                "cluster-par-01",
                "--repository-ref",
                "https://git.example.net/platform/kubernetes.git",
                "--revision",
                "c" * 40,
                "--source-path",
                "clusters/prod-par-01",
                "--owner",
                "platform",
                "--environment",
                "production",
                "--captured-at",
                "2026-07-15T08:00:00+00:00",
                "--resources-file",
                str(resources),
                "--policy-file",
                str(policy),
            ]
        )
        == 0
    )
    imported = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert imported["revision"] == "c" * 40
