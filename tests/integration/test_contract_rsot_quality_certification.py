from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.rsot_quality_services import (
    EvaluateRsotObjectQualityCommand,
    RsotQualitySummaryCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_governance_services import CreateSourceGovernanceRuleCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _http_get(base_url: str, path: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        base_url + path,
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def test_tst_rsotqual_046_complete_authoritative_object_is_certified_across_interfaces(
    tmp_path: Path, capsys
) -> None:
    data_path = tmp_path / "state.json"
    token = "q" * 40
    object_key = "device/quality-certified-001"
    app = ApplicationFactory().create_json_application(data_path, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="rsot-quality-certifier",
            roles=("rsot:governance-admin",),
            token=token,
        )
    )
    app.source_governance_service.create_rule(
        CreateSourceGovernanceRuleCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="authoritative-device-serial",
            object_kind="device",
            attribute_path="serial",
            authoritative_source="discovery.authoritative",
            priority=100,
            freshness_seconds=None,
            conflict_strategy="reject",
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="discovery-worker",
            admin_token=token,
            key=object_key,
            kind="device",
            display_name="Certified network appliance",
            attributes_json=json.dumps(
                {"serial": "SN-CERT-001", "site": "PAR1", "owner": "network-team"},
                sort_keys=True,
            ),
            tags=("production", "network", "authoritative"),
            source="discovery.authoritative",
        )
    )

    service_report = app.rsot_quality_service.evaluate_object(
        EvaluateRsotObjectQualityCommand("default", token, object_key)
    )
    service_summary = app.rsot_quality_service.summarize(
        RsotQualitySummaryCommand("default", token, limit=10, kind="device")
    ).as_dict()

    assert service_report["certification_status"] == "certified"
    assert service_report["score"] >= 90
    assert service_report["completeness_score"] == 100
    assert service_report["freshness_score"] == 100
    assert service_report["authority_score"] == 100
    assert service_report["issues"] == []
    assert service_summary["certified"] == 1
    assert service_summary["warning"] == 0
    assert service_summary["rejected"] == 0

    cli_base = [
        "--backend",
        "json",
        "--data",
        str(data_path),
        "--tenant",
        "default",
        "--admin-token",
        token,
    ]
    assert OpenInfraCLI().run(["rsot", "quality-object", *cli_base, "--key", object_key]) == 0
    cli_report = json.loads(capsys.readouterr().out)
    assert OpenInfraCLI().run(["rsot", "quality-summary", *cli_base, "--kind", "device"]) == 0
    cli_summary = json.loads(capsys.readouterr().out)
    assert cli_report["certification_status"] == "certified"
    assert cli_report["score"] == service_report["score"]
    assert cli_summary["certified"] == 1

    http_app = ApplicationFactory().create_json_application(data_path, seed=False)
    server = OpenInfraThreadingServer(("127.0.0.1", 0), http_app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        http_report = _http_get(
            base_url,
            "/api/v1/rsot/quality/object?tenant_id=default&key=" + object_key,
            token,
        )
        http_summary = _http_get(
            base_url,
            "/api/v1/rsot/quality/summary?tenant_id=default&kind=device&limit=10",
            token,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert http_report["certification_status"] == "certified"
    assert http_report["score"] == service_report["score"]
    assert http_summary["certified"] == 1
    assert http_summary["reports"][0]["key"] == object_key

    state = json.loads(data_path.read_text(encoding="utf-8"))
    quality_events = [
        event
        for event in state["audit_events"]
        if event["action"] in {"rsot.quality.evaluate", "rsot.quality.summary"}
    ]
    assert len(quality_events) == 6
    evaluate_events = [event for event in quality_events if event["action"] == "rsot.quality.evaluate"]
    assert len(evaluate_events) == 3
    assert all(event["metadata"]["score"] >= 90 for event in evaluate_events)
    assert all(
        event["metadata"]["certification_status"] == "certified"
        for event in evaluate_events
    )
