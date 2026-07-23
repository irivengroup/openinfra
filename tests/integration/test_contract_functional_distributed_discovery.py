from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer
from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL

_SNMP_FINGERPRINT = "4" * 64
_SSH_FINGERPRINT = "5" * 64
_OBJECT_KEY = "network-device/par1-core-01"


def test_tst_func_0004_distributed_snmp_ssh_discovery_is_historized_and_conflict_safe(
    tmp_path: Path,
) -> None:
    token = "distributed-discovery-admin-0123456789"
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "discovery-contract-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        for protocol in ("snmp", "ssh"):
            status, profile = _post_json(
                base + "/api/v1/discovery/protocol-profile/create",
                {
                    "tenant_id": "default",
                    "actor": "pytest",
                    "name": f"{protocol.upper()} PAR1",
                    "protocol": protocol,
                    "scope": "site/par1",
                    "credential_secret_ref": f"vault://openinfra/discovery/{protocol}/par1",
                    "max_concurrency": 4,
                    "rate_limit_per_minute": 120,
                },
                token=token,
            )
            assert status == 201
            assert profile["protocol"] == protocol
            assert str(profile["credential_secret_ref"]).startswith("vault://***")

        snmp_collector = _register_collector(
            base,
            token,
            name="PAR1 SNMP collector",
            kind="snmp",
            fingerprint=_SNMP_FINGERPRINT,
        )
        ssh_collector = _register_collector(
            base,
            token,
            name="PAR1 SSH collector",
            kind="ssh",
            fingerprint=_SSH_FINGERPRINT,
        )

        first_snmp = _execute_discovery_job(
            base,
            token,
            collector=snmp_collector,
            fingerprint=_SNMP_FINGERPRINT,
            worker_id="worker-snmp-par1",
            job_type="snmp-inventory",
            target="10.20.30.1",
            idempotency_key="tst-func-0004-snmp-001",
            observed_at="2026-07-22T18:00:00+00:00",
            payload={
                "hostname": "par1-core-01",
                "serial_number": "SN-PAR1-001",
                "vendor": "example-networks",
                "os_version": "17.6.5",
                "interfaces": ["xe0", "xe1"],
            },
        )
        assert first_snmp["job"]["status"] == "completed"
        assert first_snmp["evidence"]["id"] == first_snmp["job"]["id"]
        assert first_snmp["job"]["result_hash"] == first_snmp["evidence"]["payload_hash"]
        assert first_snmp["evidence"]["source"] == "snmp"
        assert first_snmp["evidence"]["immutable"] is True
        assert first_snmp["idempotent_replay"] is False

        replay_status, replay = _post_json(
            base + "/api/v1/discovery/jobs/result",
            _result_payload(
                collector_id=str(snmp_collector["id"]),
                fingerprint=_SNMP_FINGERPRINT,
                job_id=str(first_snmp["job"]["id"]),
                worker_id="worker-snmp-par1",
                lease_token=int(first_snmp["job"]["lease_token"]),
                observed_at="2026-07-22T18:00:00+00:00",
                payload=dict(first_snmp["evidence"]["payload"]),
            ),
        )
        assert replay_status == 200
        assert replay["idempotent_replay"] is True
        assert replay["evidence"] == first_snmp["evidence"]

        conflict_status, conflict_error = _post_error(
            base + "/api/v1/discovery/jobs/result",
            _result_payload(
                collector_id=str(snmp_collector["id"]),
                fingerprint=_SNMP_FINGERPRINT,
                job_id=str(first_snmp["job"]["id"]),
                worker_id="worker-snmp-par1",
                lease_token=int(first_snmp["job"]["lease_token"]),
                observed_at="2026-07-22T18:00:00+00:00",
                payload={**dict(first_snmp["evidence"]["payload"]), "serial_number": "MUTATED"},
            ),
        )
        assert conflict_status == 400
        assert "conflicts with stored result" in str(conflict_error["error"])

        latest_snmp = _execute_discovery_job(
            base,
            token,
            collector=snmp_collector,
            fingerprint=_SNMP_FINGERPRINT,
            worker_id="worker-snmp-par1",
            job_type="snmp-inventory",
            target="10.20.30.1",
            idempotency_key="tst-func-0004-snmp-002",
            observed_at="2026-07-22T18:10:00+00:00",
            payload={
                "hostname": "par1-core-01",
                "serial_number": "SN-PAR1-001",
                "vendor": "example-networks",
                "os_version": "17.9.4",
                "interfaces": ["xe0", "xe1", "xe2"],
            },
        )
        ssh = _execute_discovery_job(
            base,
            token,
            collector=ssh_collector,
            fingerprint=_SSH_FINGERPRINT,
            worker_id="worker-ssh-par1",
            job_type="ssh-inventory",
            target="10.20.30.1",
            idempotency_key="tst-func-0004-ssh-001",
            observed_at="2026-07-22T18:12:00+00:00",
            payload={
                "hostname": "par1-core-01",
                "serial_number": "SN-PAR1-CONFLICT",
                "vendor": "example-networks",
                "os_version": "17.9.4",
                "interfaces": ["xe0", "xe1", "xe2"],
            },
        )

        history = _get_json(
            base
            + "/api/v1/discovery/evidence-list?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "object_key": _OBJECT_KEY, "limit": 20}
            ),
            token=token,
        )
        assert [item["id"] for item in history["items"]] == [
            first_snmp["evidence"]["id"],
            latest_snmp["evidence"]["id"],
            ssh["evidence"]["id"],
        ]
        persisted_first = _get_json(
            base
            + "/api/v1/discovery/evidence?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "evidence_id": first_snmp["evidence"]["id"]}
            ),
            token=token,
        )
        assert persisted_first["payload"]["os_version"] == "17.6.5"
        assert persisted_first["payload"]["serial_number"] == "SN-PAR1-001"

        reconciliation_status, reconciliation = _post_json(
            base + "/api/v1/discovery/reconciliation",
            {
                "tenant_id": "default",
                "actor": "pytest",
                "object_key": _OBJECT_KEY,
                "evidence_ids": [latest_snmp["evidence"]["id"], ssh["evidence"]["id"]],
                "max_age_seconds": 31_622_400,
            },
            token=token,
        )
        assert reconciliation_status == 201
        assert reconciliation["status"] == "conflict"
        assert reconciliation["rsot_write_executed"] is False
        assert any(item["attribute_path"] == "serial_number" for item in reconciliation["conflicts"])
        assert set(reconciliation["evidence_ids"]) == {
            latest_snmp["evidence"]["id"],
            ssh["evidence"]["id"],
        }

        actions = [event.action for event in app.audit_repository.list_events()]
        assert actions.count("discovery.job.result-recorded") == 3

        for portal in (REACT_PORTAL.read_text(), RUNTIME_PORTAL.read_text()):
            assert '"id": "discovery-job-submit"' in portal
            assert '"id": "discovery-job-result"' in portal
            assert '"path": "/v1/discovery/jobs/result"' in portal
            assert '"id": "discovery-evidence-list"' in portal
            assert '"id": "discovery-reconcile"' in portal
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_discovery_job_result_rejects_wrong_protocol_collector_and_secret_payload(
    tmp_path: Path,
) -> None:
    token = "distributed-discovery-security-012345"
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "discovery-security", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        collector = _register_collector(
            base,
            token,
            name="PAR1 SSH collector",
            kind="ssh",
            fingerprint=_SSH_FINGERPRINT,
        )
        job = _submit_and_claim(
            base,
            token,
            collector=collector,
            fingerprint=_SSH_FINGERPRINT,
            worker_id="worker-ssh-security",
            job_type="snmp-inventory",
            target="10.20.30.2",
            idempotency_key="tst-func-0004-security-001",
        )
        status, error = _post_error(
            base + "/api/v1/discovery/jobs/result",
            _result_payload(
                collector_id=str(collector["id"]),
                fingerprint=_SSH_FINGERPRINT,
                job_id=str(job["id"]),
                worker_id="worker-ssh-security",
                lease_token=int(job["lease_token"]),
                observed_at="2026-07-22T18:20:00+00:00",
                payload={"hostname": "par1-core-02"},
            ),
        )
        assert status == 400
        assert "collector kind" in str(error["error"])

        ssh_job = _submit_and_claim(
            base,
            token,
            collector=collector,
            fingerprint=_SSH_FINGERPRINT,
            worker_id="worker-ssh-security",
            job_type="ssh-inventory",
            target="10.20.30.3",
            idempotency_key="tst-func-0004-security-002",
        )
        status, error = _post_error(
            base + "/api/v1/discovery/jobs/result",
            _result_payload(
                collector_id=str(collector["id"]),
                fingerprint=_SSH_FINGERPRINT,
                job_id=str(ssh_job["id"]),
                worker_id="worker-ssh-security",
                lease_token=int(ssh_job["lease_token"]),
                observed_at="2026-07-22T18:20:00+00:00",
                payload={"hostname": "par1-core-03", "password": "forbidden"},
            ),
        )
        assert status == 400
        assert "secret material" in str(error["error"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)



def test_discovery_job_result_error_contracts_and_implicit_observation_time(
    tmp_path: Path,
) -> None:
    token = "distributed-discovery-errors-0123456789"
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "discovery-errors", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        collector = _register_collector(
            base, token, name="PAR1 SNMP primary", kind="snmp", fingerprint=_SNMP_FINGERPRINT
        )
        other = _register_collector(
            base, token, name="PAR1 SNMP secondary", kind="snmp", fingerprint="6" * 64
        )
        generic = _register_collector(
            base, token, name="PAR1 generic proxy", kind="generic", fingerprint="7" * 64
        )

        job = _submit_and_claim(
            base,
            token,
            collector=collector,
            fingerprint=_SNMP_FINGERPRINT,
            worker_id="worker-errors",
            job_type="snmp-inventory",
            target="10.20.30.10",
            idempotency_key="tst-func-0004-errors-001",
        )
        base_payload = _result_payload(
            collector_id=str(collector["id"]),
            fingerprint=_SNMP_FINGERPRINT,
            job_id=str(job["id"]),
            worker_id="worker-errors",
            lease_token=int(job["lease_token"]),
            observed_at=None,
            payload={"hostname": "par1-edge-10"},
        )

        invalid_body = dict(base_payload)
        invalid_body["payload"] = ["not", "an", "object"]
        status, error = _post_error(base + "/api/v1/discovery/jobs/result", invalid_body)
        assert status == 400
        assert error["error"] == "payload must be a JSON object"

        invalid_certificate = dict(base_payload)
        invalid_certificate["certificate_fingerprint"] = "8" * 64
        status, error = _post_error(base + "/api/v1/discovery/jobs/result", invalid_certificate)
        assert status == 401
        assert "authentication rejected" in str(error["error"]).lower()

        unknown_job = dict(base_payload)
        unknown_job["job_id"] = "00000000-0000-4000-8000-000000000099"
        status, error = _post_error(base + "/api/v1/discovery/jobs/result", unknown_job)
        assert status == 400
        assert "not registered" in str(error["error"])

        wrong_collector = dict(base_payload)
        wrong_collector["collector_id"] = other["id"]
        wrong_collector["certificate_fingerprint"] = "6" * 64
        status, error = _post_error(base + "/api/v1/discovery/jobs/result", wrong_collector)
        assert status == 400
        assert "another collector" in str(error["error"])

        status, receipt = _post_json(base + "/api/v1/discovery/jobs/result", base_payload)
        assert status == 201
        assert receipt["evidence"]["observed_at"]
        assert receipt["evidence"]["observed_at"] == receipt["evidence"]["received_at"]

        for suffix, job_type, expected in (
            ("vmware", "vmware-inventory", "SNMP, SSH or WinRM"),
            ("custom", "custom-inventory", "SNMP, SSH or WinRM"),
        ):
            unsupported = _submit_and_claim(
                base,
                token,
                collector=generic,
                fingerprint="7" * 64,
                worker_id=f"worker-{suffix}",
                job_type=job_type,
                target=f"target-{suffix}",
                idempotency_key=f"tst-func-0004-errors-{suffix}",
            )
            status, error = _post_error(
                base + "/api/v1/discovery/jobs/result",
                _result_payload(
                    collector_id=str(generic["id"]),
                    fingerprint="7" * 64,
                    job_id=str(unsupported["id"]),
                    worker_id=f"worker-{suffix}",
                    lease_token=int(unsupported["lease_token"]),
                    observed_at=None,
                    payload={"hostname": suffix},
                ),
            )
            assert status == 400
            assert expected in str(error["error"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

def _register_collector(
    base: str,
    token: str,
    *,
    name: str,
    kind: str,
    fingerprint: str,
) -> dict[str, Any]:
    status, collector = _post_json(
        base + "/api/v1/discovery/collectors",
        {
            "tenant_id": "default",
            "actor": "pytest",
            "name": name,
            "kind": kind,
            "certificate_fingerprint": fingerprint,
            "scopes": ["site/par1"],
            "version": "0.34.19",
            "vault_secret_ref": f"vault://openinfra/discovery/{kind}/par1",
        },
        token=token,
    )
    assert status == 201
    return collector


def _execute_discovery_job(
    base: str,
    token: str,
    *,
    collector: dict[str, Any],
    fingerprint: str,
    worker_id: str,
    job_type: str,
    target: str,
    idempotency_key: str,
    observed_at: str,
    payload: dict[str, object],
) -> dict[str, Any]:
    claimed = _submit_and_claim(
        base,
        token,
        collector=collector,
        fingerprint=fingerprint,
        worker_id=worker_id,
        job_type=job_type,
        target=target,
        idempotency_key=idempotency_key,
    )
    status, receipt = _post_json(
        base + "/api/v1/discovery/jobs/result",
        _result_payload(
            collector_id=str(collector["id"]),
            fingerprint=fingerprint,
            job_id=str(claimed["id"]),
            worker_id=worker_id,
            lease_token=int(claimed["lease_token"]),
            observed_at=observed_at,
            payload=payload,
        ),
    )
    assert status == 201
    return receipt


def _submit_and_claim(
    base: str,
    token: str,
    *,
    collector: dict[str, Any],
    fingerprint: str,
    worker_id: str,
    job_type: str,
    target: str,
    idempotency_key: str,
) -> dict[str, Any]:
    status, submitted = _post_json(
        base + "/api/v1/discovery/jobs",
        {
            "tenant_id": "default",
            "actor": "pytest",
            "collector_id": collector["id"],
            "requested_scope": "site/par1",
            "job_type": job_type,
            "target": target,
            "idempotency_key": idempotency_key,
            "max_attempts": 3,
        },
        token=token,
    )
    assert status == 201
    status, claim = _post_json(
        base + "/api/v1/discovery/jobs/claim",
        {
            "tenant_id": "default",
            "collector_id": collector["id"],
            "certificate_fingerprint": fingerprint,
            "worker_id": worker_id,
            "lease_seconds": 60,
        },
    )
    assert status == 200
    assert claim["job"]["id"] == submitted["id"]
    return dict(claim["job"])


def _result_payload(
    *,
    collector_id: str,
    fingerprint: str,
    job_id: str,
    worker_id: str,
    lease_token: int,
    observed_at: str | None,
    payload: dict[str, object],
) -> dict[str, object]:
    result: dict[str, object] = {
        "tenant_id": "default",
        "collector_id": collector_id,
        "certificate_fingerprint": fingerprint,
        "job_id": job_id,
        "worker_id": worker_id,
        "lease_token": lease_token,
        "object_key": _OBJECT_KEY,
        "object_kind": "network-device",
        "confidence": 0.95,
        "payload": payload,
    }
    if observed_at is not None:
        result["observed_at"] = observed_at
    return result


def _get_json(url: str, *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
    assert isinstance(result, dict)
    return result


def _post_json(
    url: str,
    payload: dict[str, object],
    *,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
        status = response.status
    assert isinstance(result, dict)
    return status, result


def _post_error(
    url: str,
    payload: dict[str, object],
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as exc:
        result = json.loads(exc.read().decode("utf-8"))
        assert isinstance(result, dict)
        return exc.code, result
    raise AssertionError("request unexpectedly succeeded")
