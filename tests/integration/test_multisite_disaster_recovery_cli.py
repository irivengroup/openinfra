from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import TenantId
from openinfra.domain.dcim import Site
from openinfra.interfaces.cli import OpenInfraCLI


def test_multisite_disaster_recovery_cli_complete_cycle(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "dr-cli.json"
    token = "c" * 40
    app = ApplicationFactory().create_json_application(state, seed=True, edition="pro")
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "dr-admin", ("admin",), token)
    )
    with app.transaction_manager.begin() as unit_of_work:
        app.dcim_repository.add_site(
            Site.create(
                TenantId.from_value("default"),
                "LON1",
                "London 1",
                "GB",
                "London",
                "England",
                "1 Datacenter Way",
                "E1 1AA",
                "lon1@example.invalid",
                "+442000000001",
            )
        )
        unit_of_work.commit()
    cli = OpenInfraCLI()
    common = ["--data", str(state), "--tenant", "default", "--admin-token", token]

    assert (
        cli.run(
            [
                "multisite",
                "dr-plan-configure",
                *common,
                "--name",
                "Paris to London",
                "--primary-site-code",
                "PAR1",
                "--recovery-site-code",
                "LON1",
                "--rpo-seconds",
                "300",
                "--rto-seconds",
                "1800",
                "--max-backup-age-seconds",
                "86400",
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert plan["active"] is True

    assert cli.run(["multisite", "dr-plans", *common]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == plan["id"]  # type: ignore[attr-defined]
    assert cli.run(["multisite", "dr-plan-get", *common, "--plan-id", plan["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["rpo_seconds"] == 300  # type: ignore[attr-defined]

    assert (
        cli.run(
            [
                "multisite",
                "dr-drill-execute",
                *common,
                "--plan-id",
                plan["id"],
                "--replication-lag-seconds",
                "30",
                "--backup-age-seconds",
                "3600",
                "--measured-rto-seconds",
                "600",
                "--restore-verified",
                "--recovery-available",
                "--vip-reachable",
                "--operator-confirmed",
            ]
        )
        == 0
    )
    drill = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert drill["status"] == "passed"
    assert cli.run(["multisite", "dr-drills", *common, "--status", "passed"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == drill["id"]  # type: ignore[attr-defined]
    assert cli.run(["multisite", "dr-drill-get", *common, "--drill-id", drill["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["scenario"] == "primary-site-loss"  # type: ignore[attr-defined]

    assert cli.run(["multisite", "dr-plan-disable", *common, "--plan-id", plan["id"]]) == 0
    assert json.loads(capsys.readouterr().out)["active"] is False  # type: ignore[attr-defined]
    assert cli.run(["multisite", "dr-plans", *common, "--include-inactive"]) == 0
    assert json.loads(capsys.readouterr().out)["items"][0]["active"] is False  # type: ignore[attr-defined]
