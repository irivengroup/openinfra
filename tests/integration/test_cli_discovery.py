from __future__ import annotations

import json
import threading
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer

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


def test_cli_discovery_proxy_enroll_local_and_remote(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "h" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
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
        == 0
    )
    capsys.readouterr()

    local_code = cli.run(
        [
            "discovery",
            "proxy-enroll-local",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--name",
            "PAR1 site proxy local",
            "--kind",
            "site-proxy",
            "--certificate-fingerprint",
            "2" * 64,
            "--scope",
            "site/par1",
            "--version",
            "0.29.36",
            "--endpoint-url",
            "https://proxy-par1.example.test/agent",
        ]
    )
    local_proxy = json.loads(capsys.readouterr().out)

    app = ApplicationFactory().create_json_application(tmp_path / "remote.json")
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="discovery-admin",
            roles=("security:admin",),
            token=token,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config_output = tmp_path / "proxy-enrollment.json"
        remote_code = cli.run(
            [
                "discovery",
                "proxy-enroll",
                "--backend-url",
                f"http://127.0.0.1:{server.server_port}",
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "PAR1 site proxy remote",
                "--kind",
                "site-proxy",
                "--certificate-fingerprint",
                "3" * 64,
                "--scope",
                "site/par1",
                "--version",
                "0.29.36",
                "--endpoint-url",
                "https://proxy-par1.example.test/agent",
                "--config-output",
                str(config_output),
            ]
        )
        remote_result = json.loads(capsys.readouterr().out)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert local_code == 0
    assert local_proxy["kind"] == "site-proxy"
    assert remote_code == 0
    assert remote_result["enrolled"] is True
    assert remote_result["results"][0]["response"]["kind"] == "site-proxy"
    assert config_output.is_file()
    assert config_output.stat().st_mode & 0o777 == 0o600


def test_cli_discovery_proxy_enroll_rejects_non_enterprise(capsys: object) -> None:
    code = OpenInfraCLI().run(
        [
            "discovery",
            "proxy-enroll",
            "--edition",
            "pro",
            "--backend-url",
            "https://backend.example.test",
            "--tenant",
            "default",
            "--admin-token",
            "x" * 40,
            "--name",
            "PAR1 site proxy",
            "--kind",
            "site-proxy",
            "--certificate-fingerprint",
            "4" * 64,
            "--scope",
            "site/par1",
            "--version",
            "0.29.36",
            "--endpoint-url",
            "https://proxy-par1.example.test/agent",
        ]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "Enterprise" in captured.err


def test_cli_discovery_proxy_enroll_verify_validates_generated_config(
    tmp_path: Path,
    capsys: object,
) -> None:
    config_output = tmp_path / "proxy-enrollment.json"
    config_output.write_text(
        json.dumps(
            {
                "tenant_id": "default",
                "name": "PAR1 proxy",
                "enrolled": True,
                "results": [
                    {
                        "backend_url": "https://backend.example.test",
                        "status_code": 201,
                        "response": {"id": "collector-1", "kind": "site-proxy"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    config_output.chmod(0o600)

    code = OpenInfraCLI().run(
        [
            "discovery",
            "proxy-enroll-verify",
            "--config",
            str(config_output),
        ]
    )
    report = json.loads(capsys.readouterr().out)

    assert code == 0
    assert report["valid"] is True
    assert report["backend_count"] == 1


def test_cli_discovery_proxy_enroll_verify_rejects_non_enterprise(
    tmp_path: Path,
    capsys: object,
) -> None:
    config_output = tmp_path / "proxy-enrollment.json"
    config_output.write_text("{}", encoding="utf-8")

    code = OpenInfraCLI().run(
        [
            "discovery",
            "proxy-enroll-verify",
            "--edition",
            "pro",
            "--config",
            str(config_output),
        ]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "Enterprise" in captured.err


def test_cli_discovery_job_authorize_outputs_single_json_document(
    tmp_path: Path,
    capsys: object,
) -> None:
    data = tmp_path / "state.json"
    token = "j" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
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
        == 0
    )
    capsys.readouterr()
    assert (
        cli.run(
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
                "0.29.36",
            ]
        )
        == 0
    )
    collector = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
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
        == 0
    )
    output = capsys.readouterr().out

    assert output.count('"authorized"') == 1
    assert json.loads(output)["authorized"] is True


def test_cli_discovery_local_plan_lite_outputs_plan_only_json(
    tmp_path: Path, capsys: object
) -> None:
    data = tmp_path / "state.json"
    token = "l" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
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
        == 0
    )
    capsys.readouterr()

    assert (
        cli.run(
            [
                "discovery",
                "local-plan",
                "--data",
                str(data),
                "--edition",
                "lite",
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "Discovery PAR1",
                "--scope",
                "site/par1",
                "--protocol",
                "snmp",
                "--target",
                "10.20.30.10",
                "--target",
                "srv-app-01",
                "--credential-secret-ref",
                "vault://openinfra/discovery/local/par1",
                "--max-concurrency",
                "2",
                "--rate-limit-per-minute",
                "60",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["edition"] == "lite"
    assert payload["targets_count"] == 2
    assert payload["dry_run"] is True
    assert payload["agent_required"] is False
    assert payload["network_scan_executed"] is False
    assert payload["rsot_write_enabled"] is False
    assert payload["jobs"][0]["operation"] == "snmp-inventory-plan"


def test_cli_discovery_agent_bootstrap_plan_outputs_enterprise_systemd_unit(
    tmp_path: Path, capsys: object
) -> None:
    data = tmp_path / "state.json"
    token = "a" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
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
        == 0
    )
    capsys.readouterr()

    code = cli.run(
        [
            "discovery",
            "agent-bootstrap-plan",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--name",
            "Agent Enterprise PAR1",
            "--role",
            "site",
            "--scope",
            "site/par1",
            "--backend-url",
            "https://openinfra-api.example.test",
            "--certificate-fingerprint",
            "5" * 64,
            "--enrollment-secret-ref",
            "vault://openinfra/discovery/agent/par1",
            "--agent-version",
            "0.29.79",
        ]
    )
    plan = json.loads(capsys.readouterr().out)

    assert code == 0
    assert plan["edition"] == "enterprise"
    assert plan["systemd_unit_name"] == "openinfra-agent.service"
    assert plan["install_executed"] is False
    assert plan["secrets_materialized"] is False
    assert (
        plan["config_document"]["backend"]["result_publish_endpoint"] == "/api/v1/discovery/results"
    )


def test_cli_discovery_protocol_profile_lifecycle(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "r" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
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
        == 0
    )
    capsys.readouterr()

    assert (
        cli.run(
            [
                "discovery",
                "protocol-profile-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "SNMPv3 PAR1",
                "--protocol",
                "snmp",
                "--scope",
                "site/par1",
                "--credential-secret-ref",
                "vault://openinfra/discovery/snmp/par1",
                "--max-concurrency",
                "8",
                "--rate-limit-per-minute",
                "240",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "protocol-profile-update",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--profile-id",
                str(created["id"]),
                "--rate-limit-per-minute",
                "180",
            ]
        )
        == 0
    )
    updated = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "local-plan",
                "--data",
                str(data),
                "--edition",
                "pro",
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "Discovery PAR1 SNMP",
                "--scope",
                "site/par1",
                "--protocol",
                "snmp",
                "--target",
                "10.20.30.10",
                "--credential-secret-ref",
                "vault://openinfra/discovery/unused",
                "--protocol-profile-id",
                str(created["id"]),
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "protocol-profile-list",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    page = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "protocol-profile-delete",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--profile-id",
                str(created["id"]),
                "--reason",
                "rotated",
            ]
        )
        == 0
    )
    disabled = json.loads(capsys.readouterr().out)

    assert created["credential_secret_ref"] == "vault://***"
    assert updated["rate_limit_per_minute"] == 180
    assert plan["protocol_profile_id"] == created["id"]
    assert plan["rate_limit_per_minute"] == 180
    assert len(page["items"]) == 1
    assert disabled["status"] == "disabled"


def test_cli_discovery_integration_profile_lifecycle(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "u" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
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
        == 0
    )
    capsys.readouterr()

    assert (
        cli.run(
            [
                "discovery",
                "integration-profile-create",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--name",
                "vCenter PAR1",
                "--kind",
                "vmware",
                "--scope",
                "site/par1",
                "--endpoint-url",
                "https://vcenter.par1.example.local/sdk",
                "--credential-secret-ref",
                "vault://openinfra/discovery/vcenter/par1",
                "--max-concurrency",
                "8",
                "--rate-limit-per-minute",
                "240",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "integration-profile-update",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--profile-id",
                str(created["id"]),
                "--rate-limit-per-minute",
                "180",
            ]
        )
        == 0
    )
    updated = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "integration-profile-list",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
            ]
        )
        == 0
    )
    page = json.loads(capsys.readouterr().out)

    assert (
        cli.run(
            [
                "discovery",
                "integration-profile-delete",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--profile-id",
                str(created["id"]),
                "--reason",
                "secret rotated",
            ]
        )
        == 0
    )
    disabled = json.loads(capsys.readouterr().out)

    assert created["credential_secret_ref"] == "vault://***"
    assert created["connector_family"] == "virtualization"
    assert updated["rate_limit_per_minute"] == 180
    assert len(page["items"]) == 1
    assert disabled["status"] == "disabled"


def test_cli_discovery_evidence_reconciliation_lifecycle(tmp_path: Path, capsys: object) -> None:
    data = tmp_path / "state.json"
    token = "z" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--actor",
                "pytest",
                "--subject",
                "governance-admin",
                "--role",
                "rsot:governance-admin",
                "--token",
                token,
            ]
        )
        == 0
    )
    capsys.readouterr()

    ids: list[str] = []
    for source, source_ref, external_id, cores in (
        ("vmware", "vcenter-par1", "vm-101", 8),
        ("aws", "aws-prod", "i-101", 16),
    ):
        assert (
            cli.run(
                [
                    "discovery",
                    "evidence-submit",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--admin-token",
                    token,
                    "--object-key",
                    "server/cli-01",
                    "--object-kind",
                    "server",
                    "--source",
                    source,
                    "--source-ref",
                    source_ref,
                    "--scope",
                    "site/par1",
                    "--external-id",
                    external_id,
                    "--confidence",
                    "0.9",
                    "--payload-json",
                    json.dumps({"name": "cli-01", "cpu": {"cores": cores}}),
                    "--observed-at",
                    "2026-07-10T12:00:00+00:00",
                ]
            )
            == 0
        )
        ids.append(str(json.loads(capsys.readouterr().out)["id"]))

    assert (
        cli.run(
            [
                "discovery",
                "reconcile",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--object-key",
                "server/cli-01",
                "--evidence-id",
                ids[0],
                "--evidence-id",
                ids[1],
            ]
        )
        == 0
    )
    case = json.loads(capsys.readouterr().out)
    assert case["status"] == "conflict"

    assert (
        cli.run(
            [
                "discovery",
                "reconciliation-resolve",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--case-id",
                str(case["id"]),
                "--selections-json",
                json.dumps({"cpu.cores": ids[0]}),
                "--justification",
                "VMware is authoritative for this on-premise server.",
            ]
        )
        == 0
    )
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["status"] == "resolved"
    assert resolved["rsot_write_executed"] is False


def test_cli_discovery_job_result_records_immutable_evidence(
    tmp_path: Path,
    capsys: object,
) -> None:
    data = tmp_path / "state.json"
    token = "r" * 40
    cli = OpenInfraCLI()
    assert (
        cli.run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--subject",
                "discovery-result-admin",
                "--role",
                "admin",
                "--token",
                token,
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli.run(
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
                "CLI SSH collector",
                "--kind",
                "ssh",
                "--certificate-fingerprint",
                FINGERPRINT,
                "--scope",
                "site/par1",
                "--version",
                "0.34.20",
            ]
        )
        == 0
    )
    collector = json.loads(capsys.readouterr().out)
    assert (
        cli.run(
            [
                "discovery",
                "job-submit",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--actor",
                "pytest",
                "--admin-token",
                token,
                "--collector-id",
                str(collector["id"]),
                "--requested-scope",
                "site/par1",
                "--job-type",
                "ssh-inventory",
                "--target",
                "10.20.30.10",
                "--idempotency-key",
                "cli-discovery-result-001",
            ]
        )
        == 0
    )
    submitted = json.loads(capsys.readouterr().out)
    assert (
        cli.run(
            [
                "discovery",
                "job-claim",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--collector-id",
                str(collector["id"]),
                "--certificate-fingerprint",
                FINGERPRINT,
                "--worker-id",
                "cli-worker-ssh",
            ]
        )
        == 0
    )
    claimed = json.loads(capsys.readouterr().out)
    assert claimed["id"] == submitted["id"]
    payload = json.dumps(
        {
            "hostname": "srv-cli-discovery",
            "serial_number": "CLI-SERIAL-001",
            "os_version": "9.4",
        },
        sort_keys=True,
    )
    assert (
        cli.run(
            [
                "discovery",
                "job-result",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--collector-id",
                str(collector["id"]),
                "--certificate-fingerprint",
                FINGERPRINT,
                "--job-id",
                str(claimed["id"]),
                "--worker-id",
                "cli-worker-ssh",
                "--lease-token",
                str(claimed["lease_token"]),
                "--object-key",
                "server/srv-cli-discovery",
                "--object-kind",
                "server",
                "--confidence",
                "0.97",
                "--observed-at",
                "2026-07-22T19:00:00+00:00",
                "--payload-json",
                payload,
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["job"]["status"] == "completed"
    assert receipt["evidence"]["id"] == receipt["job"]["id"]
    assert receipt["evidence"]["source"] == "ssh"
    assert receipt["evidence"]["payload"]["serial_number"] == "CLI-SERIAL-001"
    assert receipt["idempotent_replay"] is False
