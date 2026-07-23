from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectAsOfCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectAuditCommand,
    UpsertSourceObjectCommand,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def test_tst_func_0009_time_travel_is_coherent_timestamped_and_provenanced(
    tmp_path: Path, capsys
) -> None:
    data_path = tmp_path / "state.json"
    token = "t" * 40
    app = ApplicationFactory().create_json_application(data_path)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="time-travel-reader",
            roles=("rsot:operator",),
            token=token,
        )
    )

    app.rsot_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="collector-snmp-01",
            admin_token=token,
            key="server/history-db-01",
            kind="server",
            display_name="Historical database v1",
            attributes_json='{"serial":"TT-001","site":"PAR1","rack":"R01"}',
            tags=("history", "prod"),
            source="discovery.snmp",
        )
    )
    first_snapshot = app.rsot_service.get_object_version(
        GetSourceObjectVersionCommand(
            tenant_id="default",
            admin_token=token,
            key="server/history-db-01",
            version=1,
        )
    )
    historical_at = datetime.fromisoformat(str(first_snapshot["changed_at"]))

    for key, kind, name in (
        ("application/history-billing", "application", "Historical billing"),
        ("rack-facility/history-r01", "rack-facility", "Historical rack R01"),
    ):
        app.rsot_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="inventory-import",
                admin_token=token,
                key=key,
                kind=kind,
                display_name=name,
                attributes_json="{}",
                tags=("history",),
                source="manual",
            )
        )

    for relation_type, source_key, target_key, provenance in (
        (
            "runs_on",
            "application/history-billing",
            "server/history-db-01",
            "discovery.ssh",
        ),
        (
            "installed_in",
            "server/history-db-01",
            "rack-facility/history-r01",
            "dcim.operator",
        ),
    ):
        app.rsot_service.create_relation(
            CreateSourceRelationCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                relation_type=relation_type,
                source_key=source_key,
                target_key=target_key,
                provenance=provenance,
                valid_from=historical_at - timedelta(minutes=1),
                valid_to=historical_at + timedelta(days=1),
            )
        )

    app.rsot_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="operator-change-42",
            admin_token=token,
            key="server/history-db-01",
            kind="server",
            display_name="Historical database v2",
            attributes_json='{"serial":"TT-001","site":"PAR2","rack":"R42"}',
            tags=("history", "prod", "migrated"),
            source="manual",
        )
    )

    report = app.rsot_service.get_object_as_of(
        GetSourceObjectAsOfCommand(
            tenant_id="default",
            admin_token=token,
            key="server/history-db-01",
            as_of=historical_at,
            relation_limit=10,
        )
    )
    current = app.rsot_service.get_object(
        GetSourceObjectCommand("default", token, "server/history-db-01")
    )

    assert report["display_name"] == "Historical database v1"
    assert report["resolved_version"] == 1
    assert report["as_of"] == historical_at.isoformat()
    assert report["snapshot_changed_at"] == first_snapshot["changed_at"]
    assert report["snapshot_changed_by"] == "collector-snmp-01"
    assert report["provenance"] == {
        "source_system": "discovery.snmp",
        "changed_by": "collector-snmp-01",
        "snapshot_id": report["snapshot_id"],
        "snapshot_changed_at": first_snapshot["changed_at"],
    }
    assert report["coherent"] is True
    assert report["complete"] is True
    assert report["relation_count"] == 2
    assert {
        (relation["relation_type"], relation["provenance"])
        for relation in report["relations"]
    } == {("installed_in", "dcim.operator"), ("runs_on", "discovery.ssh")}
    assert current["display_name"] == "Historical database v2"

    base = [
        "--backend",
        "json",
        "--data",
        str(data_path),
        "--tenant",
        "default",
        "--admin-token",
        token,
    ]
    assert (
        OpenInfraCLI().run(
            [
                "rsot",
                "get-object-as-of",
                *base,
                "--key",
                "server/history-db-01",
                "--as-of",
                historical_at.isoformat(),
                "--relation-limit",
                "10",
            ]
        )
        == 0
    )
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["resolved_version"] == 1
    assert cli_payload["provenance"]["source_system"] == "discovery.snmp"
    assert cli_payload["relation_count"] == 2

    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        query = urllib.parse.urlencode(
            {
                "tenant_id": "default",
                "key": "server/history-db-01",
                "as_of": historical_at.isoformat(),
                "relation_limit": 10,
            }
        )
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/api/v1/rsot/object-as-of?{query}",
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            http_payload = json.loads(response.read().decode("utf-8"))
        assert http_payload["coherent"] is True
        assert http_payload["resolved_version"] == 1
        assert http_payload["relation_count"] == 2
        assert http_payload["provenance"]["changed_by"] == "collector-snmp-01"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    audit = app.rsot_service.list_object_audit(
        ListSourceObjectAuditCommand(
            tenant_id="default",
            admin_token=token,
            key="server/history-db-01",
            limit=20,
        )
    )
    reads = [
        record
        for record in audit.items
        if record.event.action == "rsot.object.time-travel.read"
    ]
    assert len(reads) == 2
    assert all(record.event.metadata["resolved_version"] == 1 for record in reads)
    assert all(record.event.metadata["relation_count"] == 2 for record in reads)


def test_time_travel_relation_bound_is_explicit(tmp_path: Path) -> None:
    data_path = tmp_path / "state.json"
    token = "u" * 40
    app = ApplicationFactory().create_json_application(data_path)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="bounded-time-travel-reader",
            roles=("rsot:operator",),
            token=token,
        )
    )
    for key in ("server/root", "application/a", "application/b"):
        kind = "server" if key == "server/root" else "application"
        app.rsot_service.upsert_object(
            UpsertSourceObjectCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                key=key,
                kind=kind,
                display_name=key,
                attributes_json="{}",
                tags=(),
                source="manual",
            )
        )
    snapshot = app.rsot_service.get_object_version(
        GetSourceObjectVersionCommand("default", token, "server/root", 1)
    )
    as_of = datetime.fromisoformat(str(snapshot["changed_at"]))
    for source_key in ("application/a", "application/b"):
        app.rsot_service.create_relation(
            CreateSourceRelationCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                relation_type="runs_on",
                source_key=source_key,
                target_key="server/root",
                provenance="manual",
                valid_from=as_of - timedelta(seconds=1),
            )
        )

    report = app.rsot_service.get_object_as_of(
        GetSourceObjectAsOfCommand("default", token, "server/root", as_of, relation_limit=1)
    )
    assert report["complete"] is False
    assert report["relation_count"] == 1
