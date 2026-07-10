from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer

FINGERPRINT = "9" * 64
RESULT_HASH = "c" * 64


def _cli_json(
    cli: OpenInfraCLI,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> dict[str, object]:
    assert cli.run(arguments) == 0
    output = capsys.readouterr().out
    decoded = json.loads(output)
    assert isinstance(decoded, dict)
    return decoded


def _post_json(url: str, payload: dict[str, object], token: str | None = None) -> dict[str, object]:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _get_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def test_cli_discovery_job_resilience_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
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
                "job-admin",
                "--role",
                "security:admin",
                "--token",
                token,
            ]
        )
        == 0
    )
    capsys.readouterr()
    collector = _cli_json(
        cli,
        capsys,
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
            "CLI resilient collector",
            "--kind",
            "ssh",
            "--certificate-fingerprint",
            FINGERPRINT,
            "--scope",
            "site/par1",
            "--version",
            "0.29.83",
        ],
    )
    collector_id = str(collector["id"])
    submitted = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-submit",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--collector-id",
            collector_id,
            "--requested-scope",
            "site/par1",
            "--job-type",
            "ssh-inventory",
            "--target",
            "srv-cli-01",
            "--idempotency-key",
            "cli-job-0001",
            "--max-attempts",
            "1",
        ],
    )
    claimed = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-claim",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--collector-id",
            collector_id,
            "--certificate-fingerprint",
            FINGERPRINT,
            "--worker-id",
            "worker-cli-a",
            "--lease-seconds",
            "60",
        ],
    )
    dead_letter = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-fail",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--collector-id",
            collector_id,
            "--certificate-fingerprint",
            FINGERPRINT,
            "--job-id",
            str(submitted["id"]),
            "--worker-id",
            "worker-cli-a",
            "--lease-token",
            str(claimed["lease_token"]),
            "--error",
            "collector process crashed",
            "--retry-delay-seconds",
            "0",
        ],
    )
    assert dead_letter["status"] == "dead-letter"
    replayed = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-replay",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--job-id",
            str(submitted["id"]),
        ],
    )
    assert replayed["status"] == "queued"
    reclaimed = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-claim",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--collector-id",
            collector_id,
            "--certificate-fingerprint",
            FINGERPRINT,
            "--worker-id",
            "worker-cli-b",
            "--lease-seconds",
            "60",
        ],
    )
    completed = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-complete",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--collector-id",
            collector_id,
            "--certificate-fingerprint",
            FINGERPRINT,
            "--job-id",
            str(submitted["id"]),
            "--worker-id",
            "worker-cli-b",
            "--lease-token",
            str(reclaimed["lease_token"]),
            "--result-hash",
            RESULT_HASH,
        ],
    )
    page = _cli_json(
        cli,
        capsys,
        [
            "discovery",
            "job-list",
            "--data",
            str(data),
            "--tenant",
            "default",
            "--admin-token",
            token,
            "--status",
            "completed",
        ],
    )

    assert completed["status"] == "completed"
    assert completed["result_hash"] == RESULT_HASH
    assert page["items"] == [completed]


def test_http_discovery_job_resilience_contract(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="job-api-admin",
            roles=("security:admin",),
            token=token,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        collector = _post_json(
            base_url + "/api/v1/discovery/collectors",
            {
                "tenant_id": "default",
                "name": "HTTP resilient collector",
                "kind": "ssh",
                "certificate_fingerprint": FINGERPRINT,
                "scopes": ["site/par1"],
                "version": "0.29.83",
                "vault_secret_ref": "vault://openinfra/discovery/http/par1",
            },
            token,
        )
        submit_payload: dict[str, object] = {
            "tenant_id": "default",
            "collector_id": collector["id"],
            "requested_scope": "site/par1",
            "job_type": "ssh-inventory",
            "target": "srv-http-01",
            "idempotency_key": "http-job-0001",
            "max_attempts": 1,
        }
        submitted = _post_json(base_url + "/api/v1/discovery/jobs", submit_payload, token)
        duplicate = _post_json(base_url + "/api/v1/discovery/jobs", submit_payload, token)
        assert duplicate["id"] == submitted["id"]

        with pytest.raises(urllib.error.HTTPError) as rejected_identity:
            _post_json(
                base_url + "/api/v1/discovery/jobs/claim",
                {
                    "tenant_id": "default",
                    "collector_id": collector["id"],
                    "certificate_fingerprint": "8" * 64,
                    "worker_id": "worker-http-rejected",
                    "lease_seconds": 60,
                },
            )
        assert rejected_identity.value.code == 401

        claimed_response = _post_json(
            base_url + "/api/v1/discovery/jobs/claim",
            {
                "tenant_id": "default",
                "collector_id": collector["id"],
                "certificate_fingerprint": FINGERPRINT,
                "worker_id": "worker-http-a",
                "lease_seconds": 60,
            },
        )
        claimed = claimed_response["job"]
        assert isinstance(claimed, dict)
        renewed = _post_json(
            base_url + "/api/v1/discovery/jobs/renew",
            {
                "tenant_id": "default",
                "collector_id": collector["id"],
                "certificate_fingerprint": FINGERPRINT,
                "job_id": submitted["id"],
                "worker_id": "worker-http-a",
                "lease_token": claimed["lease_token"],
                "lease_seconds": 120,
            },
        )
        dead_letter = _post_json(
            base_url + "/api/v1/discovery/jobs/fail",
            {
                "tenant_id": "default",
                "collector_id": collector["id"],
                "certificate_fingerprint": FINGERPRINT,
                "job_id": submitted["id"],
                "worker_id": "worker-http-a",
                "lease_token": renewed["lease_token"],
                "error": "worker terminated unexpectedly",
                "retry_delay_seconds": 0,
            },
        )
        assert dead_letter["status"] == "dead-letter"
        replayed = _post_json(
            base_url + "/api/v1/discovery/jobs/replay",
            {"tenant_id": "default", "job_id": submitted["id"]},
            token,
        )
        assert replayed["status"] == "queued"
        reclaimed_response = _post_json(
            base_url + "/api/v1/discovery/jobs/claim",
            {
                "tenant_id": "default",
                "collector_id": collector["id"],
                "certificate_fingerprint": FINGERPRINT,
                "worker_id": "worker-http-b",
                "lease_seconds": 60,
            },
        )
        reclaimed = reclaimed_response["job"]
        assert isinstance(reclaimed, dict)
        completed = _post_json(
            base_url + "/api/v1/discovery/jobs/complete",
            {
                "tenant_id": "default",
                "collector_id": collector["id"],
                "certificate_fingerprint": FINGERPRINT,
                "job_id": submitted["id"],
                "worker_id": "worker-http-b",
                "lease_token": reclaimed["lease_token"],
                "result_hash": RESULT_HASH,
            },
        )
        fetched = _get_json(
            base_url
            + "/api/v1/discovery/job?tenant_id=default&job_id="
            + urllib.parse.quote(str(submitted["id"])),
            token,
        )
        page = _get_json(
            base_url + "/api/v1/discovery/jobs?tenant_id=default&status=completed&limit=10",
            token,
        )

        assert completed["status"] == "completed"
        assert fetched == completed
        assert page["items"] == [completed]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
