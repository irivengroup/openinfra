from __future__ import annotations

import json
from pathlib import Path

from openinfra.interfaces.cli import OpenInfraCLI

FINGERPRINT = "1" * 64


def test_cli_discovery_collector_lifecycle(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "g" * 40
    bootstrap_code = OpenInfraCLI().run(
        [
            "security",
            "bootstrap-token",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--subject",
            "discovery-admin",
            "--role",
            "security:admin",
            "--token",
            token,
        ]
    )
    capsys.readouterr()
    register_code = OpenInfraCLI().run(
        [
            "discovery",
            "collector-register",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--name",
            "SNMP collector",
            "--kind",
            "snmp",
            "--certificate-fingerprint",
            FINGERPRINT,
            "--scope",
            "site/par1",
            "--version",
            "1.0.0",
            "--vault-secret-ref",
            "vault://openinfra/discovery/snmp/par1",
        ]
    )
    collector = json.loads(capsys.readouterr().out)
    heartbeat_code = OpenInfraCLI().run(
        [
            "discovery",
            "collector-heartbeat",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--collector-id",
            str(collector["id"]),
            "--certificate-fingerprint",
            FINGERPRINT,
            "--version",
            "1.0.1",
        ]
    )
    heartbeat = json.loads(capsys.readouterr().out)
    authorize_code = OpenInfraCLI().run(
        [
            "discovery",
            "job-authorize",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--collector-id",
            str(collector["id"]),
            "--certificate-fingerprint",
            FINGERPRINT,
            "--requested-scope",
            "site/par1",
            "--job-type",
            "snmp-scan",
            "--target",
            "par1-core",
        ]
    )
    decision = json.loads(capsys.readouterr().out)
    list_code = OpenInfraCLI().run(
        [
            "discovery",
            "collector-list",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
        ]
    )
    page = json.loads(capsys.readouterr().out)

    assert bootstrap_code == 0
    assert register_code == 0
    assert heartbeat_code == 0
    assert authorize_code == 0
    assert list_code == 0
    assert collector["kind"] == "snmp"
    assert heartbeat["last_seen_version"] == "1.0.1"
    assert decision["authorized"] is True
    assert len(page["items"]) == 1
