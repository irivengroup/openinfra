from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI


def test_multisite_cli_grant_scope_report_and_revoke(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "state.json"
    token = "m" * 40
    app = ApplicationFactory().create_json_application(state, seed=True, edition="pro")
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "multisite-admin", ("admin",), token)
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "multisite",
                "grant-upsert",
                *common,
                "--subject",
                "ops.user",
                "--site-code",
                "PAR1",
                "--access-level",
                "operator",
            ]
        )
        == 0
    )
    grant = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert grant["access_level"] == "operator"

    assert cli.run(["multisite", "grants", *common, "--subject", "ops.user"]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]
    assert (
        cli.run(
            ["multisite", "sites", *common, "--subject", "ops.user", "--required-level", "operator"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["items"][0]["site_code"] == "PAR1"  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "multisite",
                "report-generate",
                *common,
                "--subject",
                "ops.user",
                "--site-code",
                "PAR1",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert report["totals"]["sites"] == 1
    assert cli.run(["multisite", "report-get", *common, "--report-id", report["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == report["id"]  # type: ignore[attr-defined]
    assert cli.run(["multisite", "reports", *common]) == 0
    assert len(json.loads(capsys.readouterr().out)["items"]) == 1  # type: ignore[attr-defined]

    assert (
        cli.run(
            ["multisite", "grant-revoke", *common, "--subject", "ops.user", "--site-code", "PAR1"]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["active"] is False  # type: ignore[attr-defined]
    assert cli.run(["multisite", "grants", *common, "--include-inactive"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["active"] is False  # type: ignore[attr-defined]


def test_multisite_cli_enterprise_regional_discovery_routing(
    tmp_path: Path, capsys: object
) -> None:
    from openinfra.application.discovery_services import EnrollDiscoveryProxyCommand

    state = tmp_path / "enterprise-state.json"
    token = "r" * 40
    app = ApplicationFactory().create_json_application(state, seed=True, edition="enterprise")
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "enterprise-admin", ("admin",), token)
    )
    scope = "region/eu-west/site/par1/vrf/prod"
    collector = app.discovery_service.enroll_proxy(
        EnrollDiscoveryProxyCommand(
            "default",
            "pytest",
            token,
            "EU West regional proxy",
            "network-proxy",
            "d" * 64,
            (scope,),
            "0.29.103",
            "https://regional-agent.example.invalid:8443",
        )
    )
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "multisite",
                "route-configure",
                *common,
                "--region-code",
                "EU-WEST",
                "--site-code",
                "PAR1",
                "--vrf-code",
                "PROD",
                "--collector-id",
                collector.id.value,
            ]
        )
        == 0
    )
    route = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert route["discovery_scope"] == scope

    assert cli.run(["multisite", "routes", *common, "--region-code", "EU-WEST"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == route["id"]  # type: ignore[attr-defined]
    assert cli.run(["multisite", "route-get", *common, "--route-id", route["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["collector_id"] == collector.id.value  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "multisite",
                "job-route",
                *common,
                "--region-code",
                "EU-WEST",
                "--site-code",
                "PAR1",
                "--vrf-code",
                "PROD",
                "--job-type",
                "network-inventory",
                "--target",
                "10.20.0.0/24",
                "--idempotency-key",
                "cli-regional-route-0001",
            ]
        )
        == 0
    )
    dispatch = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert dispatch["job"]["collector_id"] == collector.id.value

    assert cli.run(["multisite", "route-disable", *common, "--route-id", route["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["active"] is False  # type: ignore[attr-defined]
