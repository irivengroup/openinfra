from __future__ import annotations

import hashlib
import json
import threading
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.rag_services import AskRagCommand, SyncRsotRagCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _source_state_digest(data_path: Path) -> str:
    state = json.loads(data_path.read_text(encoding="utf-8"))
    payload = {
        key: state.get(key)
        for key in ("source_objects", "source_object_snapshots", "source_relations")
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _http_query(base: str, token: str, question: str) -> dict[str, object]:
    request = urllib.request.Request(
        base + "/api/v1/rag/query",
        data=json.dumps(
            {"tenant_id": "default", "question": question, "limit": 6}
        ).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 201
        return json.loads(response.read().decode("utf-8"))


def test_tst_func_0010_governed_rag_cites_rsot_objects_and_never_mutates_them(
    tmp_path: Path, capsys
) -> None:
    data_path = tmp_path / "state.json"
    token = "g" * 40
    question = "Quel serveur PostgreSQL héberge la facturation sur le site PAR1 ?"
    app = ApplicationFactory().create_json_application(data_path, seed=False)
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="governed-rag-reader",
            roles=("admin",),
            token=token,
        )
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="inventory-import",
            admin_token=token,
            key="server/rag-postgresql-01",
            kind="server",
            display_name="PostgreSQL facturation PAR1",
            attributes_json=json.dumps(
                {
                    "database": "PostgreSQL",
                    "application": "facturation",
                    "site": "PAR1",
                    "criticality": "high",
                },
                sort_keys=True,
            ),
            tags=("database", "billing", "production"),
            source="inventory.authoritative",
        )
    )
    source_digest = _source_state_digest(data_path)

    sync = app.rag_service.sync_rsot(
        SyncRsotRagCommand(
            tenant_id="default",
            admin_token=token,
            max_objects=100,
            actor="pytest",
        )
    )
    assert sync.imported == 1
    assert _source_state_digest(data_path) == source_digest

    answer = app.rag_service.ask(
        AskRagCommand(
            tenant_id="default",
            admin_token=token,
            question=question,
            limit=6,
            actor="pytest",
        )
    )
    payload = answer.as_dict()
    assert payload["status"] == "answered"
    assert payload["governance"] == {
        "mode": "read-only",
        "source_data_mutation_performed": False,
        "change_validation_required": True,
        "execution_capabilities": [],
    }
    assert payload["source_objects"] == [
        {
            "object_key": "server/rag-postgresql-01",
            "source_uri": "openinfra:rsot/server/rag-postgresql-01",
            "title": "PostgreSQL facturation PAR1",
            "document_id": payload["citations"][0]["document_id"],
            "chunk_id": payload["citations"][0]["chunk_id"],
            "score": payload["citations"][0]["score"],
        }
    ]
    assert payload["citations"][0]["source_type"] == "rsot"
    assert payload["citations"][0]["source_ref"] == "server/rag-postgresql-01"
    assert "PostgreSQL" in str(payload["answer"])
    assert _source_state_digest(data_path) == source_digest

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
    assert OpenInfraCLI().run(["rag", "ask", *base, "--question", question]) == 0
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["governance"]["mode"] == "read-only"
    assert cli_payload["governance"]["source_data_mutation_performed"] is False
    assert cli_payload["source_objects"][0]["object_key"] == "server/rag-postgresql-01"
    assert _source_state_digest(data_path) == source_digest

    http_app = ApplicationFactory().create_json_application(data_path, seed=False)
    server = OpenInfraThreadingServer(("127.0.0.1", 0), http_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        http_payload = _http_query(
            f"http://127.0.0.1:{server.server_port}", token, question
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert http_payload["governance"]["change_validation_required"] is True
    assert http_payload["governance"]["execution_capabilities"] == []
    assert http_payload["source_objects"][0]["source_uri"].startswith("openinfra:rsot/")
    assert _source_state_digest(data_path) == source_digest

    final_state = json.loads(data_path.read_text(encoding="utf-8"))
    query_audits = [
        event
        for event in final_state["audit_events"]
        if event["action"] == "rag.query.completed"
    ]
    assert len(query_audits) == 3
    assert all(event["metadata"]["source_object_count"] == 1 for event in query_audits)
    assert all(
        event["metadata"]["source_data_mutation_performed"] is False
        for event in query_audits
    )
    assert all(
        event["metadata"]["change_validation_required"] is True
        for event in query_audits
    )
