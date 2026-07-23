from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.rsot_quality_services import (
    EvaluateRsotObjectQualityCommand,
    RsotQualitySummaryCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import AccessDeniedError
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _denied_http_get(base_url: str, path: str, token: str) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        base_url + path,
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        method="GET",
    )
    with pytest.raises(urllib.error.HTTPError) as captured:
        urllib.request.urlopen(request, timeout=5)
    error = captured.value
    return error.code, json.loads(error.read().decode("utf-8"))


def test_tst_rsotqual_047_role_without_quality_permission_cannot_read_any_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data_path = tmp_path / "state.json"
    writer_token = "q" * 40
    denied_token = "d" * 40
    object_key = "device/quality-protected-001"
    object_display_name = "Protected quality appliance"
    object_serial = "SN-PROTECTED-001"

    app = ApplicationFactory().create_json_application(data_path, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="rsot-quality-writer",
            roles=("rsot:operator",),
            token=writer_token,
        )
    )
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="dcim-only-reader",
            roles=("dcim:operator",),
            token=denied_token,
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=writer_token,
            key=object_key,
            kind="device",
            display_name=object_display_name,
            attributes_json=json.dumps({"serial": object_serial, "site": "PAR1"}),
            tags=("production",),
            source="manual",
        )
    )

    state_before_denied_reads = _sha256(data_path)

    with pytest.raises(AccessDeniedError, match="not allowed"):
        app.rsot_quality_service.evaluate_object(
            EvaluateRsotObjectQualityCommand("default", denied_token, object_key)
        )
    with pytest.raises(AccessDeniedError, match="not allowed"):
        app.rsot_quality_service.summarize(
            RsotQualitySummaryCommand("default", denied_token, limit=10, kind="device")
        )

    cli_base = [
        "--backend",
        "json",
        "--data",
        str(data_path),
        "--tenant",
        "default",
        "--admin-token",
        denied_token,
    ]
    assert OpenInfraCLI().run(["rsot", "quality-object", *cli_base, "--key", object_key]) == 2
    cli_object = capsys.readouterr()
    assert cli_object.out == ""
    assert "not allowed to perform this operation" in cli_object.err

    assert OpenInfraCLI().run(["rsot", "quality-summary", *cli_base, "--kind", "device"]) == 2
    cli_summary = capsys.readouterr()
    assert cli_summary.out == ""
    assert "not allowed to perform this operation" in cli_summary.err

    http_app = ApplicationFactory().create_json_application(data_path, seed=False)
    server = OpenInfraThreadingServer(("127.0.0.1", 0), http_app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        object_status, object_error = _denied_http_get(
            base_url,
            "/api/v1/rsot/quality/object?tenant_id=default&key=" + object_key,
            denied_token,
        )
        summary_status, summary_error = _denied_http_get(
            base_url,
            "/api/v1/rsot/quality/summary?tenant_id=default&kind=device&limit=10",
            denied_token,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert object_status == HTTPStatus.UNAUTHORIZED
    assert summary_status == HTTPStatus.UNAUTHORIZED
    expected_error = {"error": "api token is not allowed to perform this operation"}
    assert object_error == expected_error
    assert summary_error == expected_error

    serialized_denials = json.dumps(
        {
            "cli_object": cli_object.err,
            "cli_summary": cli_summary.err,
            "http_object": object_error,
            "http_summary": summary_error,
        },
        sort_keys=True,
    )
    assert object_key not in serialized_denials
    assert object_display_name not in serialized_denials
    assert object_serial not in serialized_denials
    assert _sha256(data_path) == state_before_denied_reads

    authorized_report = app.rsot_quality_service.evaluate_object(
        EvaluateRsotObjectQualityCommand("default", writer_token, object_key)
    )
    assert authorized_report["key"] == object_key
    assert authorized_report["display_name"] == object_display_name
