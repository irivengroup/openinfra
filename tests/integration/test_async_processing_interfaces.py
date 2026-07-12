from __future__ import annotations

import base64
import json
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def test_cli_async_processing_cycle(tmp_path: Path, capsys) -> None:
    data = tmp_path / "state.json"
    payload = tmp_path / "payload.json"
    payload.write_text('{"scope":"all"}', encoding="utf-8")
    token = "a" * 40
    app = ApplicationFactory().create_json_application(data, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "async-cli", ("admin",), token)
    )
    common = [
        "--backend",
        "json",
        "--data",
        str(data),
        "--tenant",
        "default",
        "--admin-token",
        token,
    ]
    cli = OpenInfraCLI()
    assert (
        cli.run(
            [
                "async",
                "job-submit",
                *common,
                "--idempotency-key",
                "cli-health-001",
                "--payload-file",
                str(payload),
            ]
        )
        == 0
    )
    submitted = json.loads(capsys.readouterr().out)
    assert submitted["status"] == "queued"
    assert (
        cli.run(
            [
                "async",
                "worker-run-once",
                *common,
                "--worker-id",
                "reporting-cli-01",
            ]
        )
        == 0
    )
    completed = json.loads(capsys.readouterr().out)
    assert completed["status"] == "completed"
    output = tmp_path / "result.json"
    assert (
        cli.run(
            [
                "async",
                "artifact-get",
                *common,
                "--job-id",
                submitted["id"],
                "--output",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert json.loads(output.read_text(encoding="utf-8"))["operation"] == (
        "reporting.async-queue-health"
    )
    assert cli.run(["async", "metrics", *common]) == 0
    metrics = json.loads(capsys.readouterr().out)
    assert metrics["jobs"]["completed"] == 1


def test_http_async_processing_cycle(tmp_path: Path) -> None:
    token = "b" * 40
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "async-api", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        submitted = post_json(
            base + "/api/v1/async/jobs/submit",
            {
                "tenant_id": "default",
                "idempotency_key": "api-health-001",
                "payload": {"scope": "all"},
            },
            token,
        )
        assert submitted["status"] == "queued"
        completed_wrapper = post_json(
            base + "/api/v1/async/workers/reporting/run-once",
            {"tenant_id": "default", "worker_id": "reporting-api-01"},
            token,
        )
        completed = completed_wrapper["item"]
        assert isinstance(completed, dict) and completed["status"] == "completed"
        artifact = get_json(
            base
            + "/api/v1/async/artifacts/get?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "job_id": submitted["id"], "kind": "result"}
            ),
            token,
        )
        report = json.loads(base64.b64decode(str(artifact["content_base64"])))
        assert report["operation"] == "reporting.async-queue-health"
        events = get_json(base + "/api/v1/async/outbox-events?tenant_id=default", token)
        metrics = get_json(base + "/api/v1/async/metrics?tenant_id=default", token)
        discovery = get_json(base + "/api/v1", None)
        assert len(events["items"]) == 2
        assert metrics["jobs"]["completed"] == 1
        assert discovery["documentation"]["async_processing"]["job_submit"] == (
            "/api/v1/async/jobs/submit"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get_json(url: str, token: str | None) -> dict[str, object]:
    headers = {"Authorization": "Bearer " + token} if token else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def post_json(url: str, payload: dict[str, object], token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.loads(response.read().decode("utf-8"))
    assert isinstance(result, dict)
    return result


def test_cli_exercises_all_async_management_commands(tmp_path: Path, capsys) -> None:
    data = tmp_path / "all-state.json"
    payload = tmp_path / "payload.json"
    payload.write_text('{"scope":"all"}', encoding="utf-8")
    result_file = tmp_path / "worker-result.json"
    result_file.write_text('{"result":"ok"}', encoding="utf-8")
    token = "c" * 40
    app = ApplicationFactory().create_json_application(data, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "async-cli-all", ("admin",), token)
    )
    common = [
        "--backend",
        "json",
        "--data",
        str(data),
        "--tenant",
        "default",
        "--admin-token",
        token,
    ]
    cli = OpenInfraCLI()

    def run(command: list[str]) -> object:
        assert cli.run(["async", *command, *common]) == 0
        return json.loads(capsys.readouterr().out)

    first = run(
        [
            "job-submit",
            "--idempotency-key",
            "cli-all-job-001",
            "--payload-file",
            str(payload),
        ]
    )
    assert isinstance(first, dict)
    first_id = str(first["id"])
    jobs = run(["jobs", "--status", "queued", "--specialization", "reporting"])
    assert isinstance(jobs, dict) and len(jobs["items"]) == 1
    fetched = run(["job-get", "--job-id", first_id])
    assert isinstance(fetched, dict) and fetched["id"] == first_id
    claimed = run(["job-claim", "--worker-id", "cli-worker-01", "--lease-seconds", "10"])
    assert isinstance(claimed, dict)
    lease_token = str(claimed["lease_token"])
    renewed = run(
        [
            "job-renew",
            "--job-id",
            first_id,
            "--worker-id",
            "cli-worker-01",
            "--lease-token",
            lease_token,
            "--lease-seconds",
            "30",
        ]
    )
    assert isinstance(renewed, dict) and renewed["status"] == "leased"
    completed = run(
        [
            "job-complete",
            "--job-id",
            first_id,
            "--worker-id",
            "cli-worker-01",
            "--lease-token",
            lease_token,
            "--result-file",
            str(result_file),
        ]
    )
    assert isinstance(completed, dict) and completed["status"] == "completed"

    payload_output = tmp_path / "payload-output.json"
    artifact = run(
        [
            "artifact-get",
            "--job-id",
            first_id,
            "--kind",
            "payload",
            "--output",
            str(payload_output),
        ]
    )
    assert isinstance(artifact, dict) and payload_output.exists()

    second = run(
        [
            "job-submit",
            "--idempotency-key",
            "cli-all-job-002",
            "--payload-file",
            str(payload),
            "--max-attempts",
            "1",
        ]
    )
    assert isinstance(second, dict)
    second_id = str(second["id"])
    second_claim = run(["job-claim", "--worker-id", "cli-worker-02"])
    assert isinstance(second_claim, dict) and second_claim["id"] == second_id
    dead = run(
        [
            "job-fail",
            "--job-id",
            second_id,
            "--worker-id",
            "cli-worker-02",
            "--lease-token",
            str(second_claim["lease_token"]),
            "--error",
            "permanent",
            "--retry-delay-seconds",
            "0",
        ]
    )
    assert isinstance(dead, dict) and dead["status"] == "dead-letter"
    replayed = run(["job-replay", "--job-id", second_id])
    assert isinstance(replayed, dict) and replayed["status"] == "queued"

    events = run(["outbox-events"])
    assert isinstance(events, dict) and events["items"]
    event_id = str(events["items"][0]["id"])
    event = run(["outbox-get", "--event-id", event_id])
    assert isinstance(event, dict) and event["id"] == event_id
    event_claim = run(["outbox-claim", "--worker-id", "cli-outbox-01"])
    assert isinstance(event_claim, dict)
    claimed_event_id = str(event_claim["id"])
    event_token = str(event_claim["lease_token"])
    event_renew = run(
        [
            "outbox-renew",
            "--event-id",
            claimed_event_id,
            "--worker-id",
            "cli-outbox-01",
            "--lease-token",
            event_token,
        ]
    )
    assert isinstance(event_renew, dict) and event_renew["status"] == "leased"
    event_publish = run(
        [
            "outbox-publish",
            "--event-id",
            claimed_event_id,
            "--worker-id",
            "cli-outbox-01",
            "--lease-token",
            event_token,
        ]
    )
    assert isinstance(event_publish, dict) and event_publish["status"] == "completed"

    event_fail_claim = run(["outbox-claim", "--worker-id", "cli-outbox-02"])
    assert isinstance(event_fail_claim, dict)
    event_failed = run(
        [
            "outbox-fail",
            "--event-id",
            str(event_fail_claim["id"]),
            "--worker-id",
            "cli-outbox-02",
            "--lease-token",
            str(event_fail_claim["lease_token"]),
            "--error",
            "temporary",
            "--retry-delay-seconds",
            "0",
        ]
    )
    assert isinstance(event_failed, dict) and event_failed["status"] == "retry-wait"

    # Persist one real dead-letter event to exercise the administrative replay command.
    state = json.loads(data.read_text(encoding="utf-8"))
    failed_key = "default:" + str(event_fail_claim["id"])
    state["outbox_events"][failed_key]["max_attempts"] = 1
    state["outbox_events"][failed_key]["attempt_count"] = 1
    state["outbox_events"][failed_key]["status"] = "dead-letter"
    state["outbox_events"][failed_key]["lease_owner"] = None
    state["outbox_events"][failed_key]["leased_until"] = None
    state["outbox_events"][failed_key]["next_attempt_at"] = None
    state["outbox_events"][failed_key]["last_error"] = "permanent"
    data.write_text(json.dumps(state), encoding="utf-8")
    replayed_event = run(["outbox-replay", "--event-id", str(event_fail_claim["id"])])
    assert isinstance(replayed_event, dict) and replayed_event["status"] == "queued"

    sink = tmp_path / "event-sink"
    dispatched = run(
        [
            "outbox-dispatch-once",
            "--worker-id",
            "cli-dispatch-01",
            "--event-sink",
            str(sink),
        ]
    )
    assert dispatched is None or isinstance(dispatched, dict)
    metrics = run(["metrics"])
    assert isinstance(metrics, dict) and metrics["tenant_id"] == "default"


def test_cli_rejects_non_object_async_payload(tmp_path: Path) -> None:
    data = tmp_path / "invalid-state.json"
    payload = tmp_path / "invalid-payload.json"
    payload.write_text("[]", encoding="utf-8")
    token = "d" * 40
    app = ApplicationFactory().create_json_application(data, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "async-cli-invalid", ("admin",), token)
    )
    cli = OpenInfraCLI()
    assert (
        cli.run(
            [
                "async",
                "job-submit",
                "--backend",
                "json",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--idempotency-key",
                "cli-invalid-001",
                "--payload-file",
                str(payload),
            ]
        )
        == 2
    )


def test_http_async_management_routes_cover_leases_and_publication(tmp_path: Path) -> None:
    token = "e" * 40
    app = ApplicationFactory().create_json_application(tmp_path / "http-all-state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "async-http-all", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        submitted = post_json(
            base + "/api/v1/async/jobs/submit",
            {
                "tenant_id": "default",
                "idempotency_key": "api-all-job-001",
                "payload": {"scope": "all"},
            },
            token,
        )
        job_id = str(submitted["id"])
        jobs = get_json(
            base
            + "/api/v1/async/jobs?"
            + urllib.parse.urlencode(
                {
                    "tenant_id": "default",
                    "status": "queued",
                    "specialization": "reporting",
                }
            ),
            token,
        )
        assert len(jobs["items"]) == 1
        fetched = get_json(
            base
            + "/api/v1/async/jobs/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "job_id": job_id}),
            token,
        )
        assert fetched["id"] == job_id

        claimed_wrapper = post_json(
            base + "/api/v1/async/jobs/claim",
            {
                "tenant_id": "default",
                "worker_id": "api-worker-01",
                "lease_seconds": 10,
            },
            token,
        )
        claimed = claimed_wrapper["item"]
        assert isinstance(claimed, dict)
        lease_token = int(claimed["lease_token"])
        renewed = post_json(
            base + "/api/v1/async/jobs/renew",
            {
                "tenant_id": "default",
                "job_id": job_id,
                "worker_id": "api-worker-01",
                "lease_token": lease_token,
                "lease_seconds": 30,
            },
            token,
        )
        assert renewed["status"] == "leased"
        completed = post_json(
            base + "/api/v1/async/jobs/complete",
            {
                "tenant_id": "default",
                "job_id": job_id,
                "worker_id": "api-worker-01",
                "lease_token": lease_token,
                "result": {"ok": True},
            },
            token,
        )
        assert completed["status"] == "completed"

        events = get_json(base + "/api/v1/async/outbox-events?tenant_id=default", token)
        event_id = str(events["items"][0]["id"])
        fetched_event = get_json(
            base
            + "/api/v1/async/outbox-events/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "event_id": event_id}),
            token,
        )
        assert fetched_event["id"] == event_id
        event_claim_wrapper = post_json(
            base + "/api/v1/async/outbox-events/claim",
            {"tenant_id": "default", "worker_id": "api-outbox-01", "lease_seconds": 10},
            token,
        )
        event_claim = event_claim_wrapper["item"]
        assert isinstance(event_claim, dict)
        claimed_event_id = str(event_claim["id"])
        event_token = int(event_claim["lease_token"])
        event_renew = post_json(
            base + "/api/v1/async/outbox-events/renew",
            {
                "tenant_id": "default",
                "event_id": claimed_event_id,
                "worker_id": "api-outbox-01",
                "lease_token": event_token,
                "lease_seconds": 30,
            },
            token,
        )
        assert event_renew["status"] == "leased"
        event_publish = post_json(
            base + "/api/v1/async/outbox-events/publish",
            {
                "tenant_id": "default",
                "event_id": claimed_event_id,
                "worker_id": "api-outbox-01",
                "lease_token": event_token,
            },
            token,
        )
        assert event_publish["status"] == "completed"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
