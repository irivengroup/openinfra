from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _request(
    url: str, *, token: str | None = None, payload: dict[str, object] | None = None
) -> tuple[int, bytes, dict[str, str]]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def _json(body: bytes) -> dict[str, object]:
    return json.loads(body.decode("utf-8"))


def test_rag_http_complete_cycle_security_validation_and_artifact(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "rag-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, _, _ = _request(base + "/api/v1/rag/documents?tenant_id=default")
        assert status == 401

        status, body, _ = _request(
            base + "/api/v1/rag/documents/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "source_type": "runbook",
                "source_ref": "postgresql-ha",
                "title": "PostgreSQL HA",
                "content": "OpenInfra utilise PostgreSQL avec réplication contrôlée.",
                "required_permissions": ["rag.read"],
                "tags": ["database"],
                "metadata": {"owner": "platform"},
            },
        )
        assert status == 201
        document = _json(body)
        document_id = str(document["id"])

        query = urllib.parse.urlencode({"tenant_id": "default", "document_id": document_id})
        status, body, _ = _request(base + f"/api/v1/rag/documents/get?{query}", token=token)
        assert status == 200 and _json(body)["source_ref"] == "postgresql-ha"

        status, body, _ = _request(
            base + "/api/v1/rag/query",
            token=token,
            payload={"tenant_id": "default", "question": "Quelle base utilise OpenInfra ?"},
        )
        assert status == 201
        answer = _json(body)
        assert answer["status"] == "answered" and answer["citations"]
        answer_id = str(answer["id"])

        status, body, _ = _request(
            base + "/api/v1/rag/jobs/create",
            token=token,
            payload={
                "tenant_id": "default",
                "kind": "answer-export",
                "idempotency_key": "http-export-001",
                "payload": {"format": "csv", "answer_ids": [answer_id]},
            },
        )
        assert status == 201
        job_id = str(_json(body)["id"])
        status, body, _ = _request(
            base + "/api/v1/rag/jobs/run",
            token=token,
            payload={"tenant_id": "default", "job_id": job_id},
        )
        assert status == 200 and _json(body)["status"] == "completed"

        artifact_query = urllib.parse.urlencode({"tenant_id": "default", "job_id": job_id})
        status, body, headers = _request(
            base + f"/api/v1/rag/jobs/artifact?{artifact_query}", token=token
        )
        assert status == 200 and answer_id.encode() in body
        assert headers["Content-Type"].startswith("text/csv")
        assert "attachment" in headers["Content-Disposition"]

        status, body, _ = _request(
            base + "/api/v1/rag/documents/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "source_type": "documentation",
                "source_ref": "invalid",
                "title": "Invalid",
                "content": "Invalid metadata",
                "metadata": ["not-an-object"],
            },
        )
        assert status == 400 and "metadata" in str(_json(body)["error"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_rag_http_all_routes_boolean_filters_and_authentication_errors(tmp_path: Path) -> None:
    from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand

    app = ApplicationFactory().create_json_application(
        tmp_path / "state-all-routes.json", seed=False
    )
    token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "rag-route-admin", ("admin",), token)
    )
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="device/http-rag-001",
            kind="device",
            display_name="HTTP RAG device",
            attributes_json='{"site":"PAR1"}',
            tags=("rag",),
            source="manual",
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        upsert_payload = {
            "tenant_id": "default",
            "source_type": "documentation",
            "source_ref": "all-routes",
            "title": "All routes",
            "content": "OpenInfra fournit un assistant RAG gouverné avec des citations.",
            "required_permissions": ["rag.read"],
        }
        status, body, _ = _request(
            base + "/api/v1/rag/documents/upsert", token=token, payload=upsert_payload
        )
        assert status == 201
        document_id = str(_json(body)["id"])
        assert _request(base + "/api/v1/rag/documents/upsert", payload=upsert_payload)[0] == 401

        for active in ("true", "false", "1", "0"):
            query = urllib.parse.urlencode({"tenant_id": "default", "active": active})
            status, body, _ = _request(base + f"/api/v1/rag/documents?{query}", token=token)
            assert status == 200 and "items" in _json(body)
        invalid_query = urllib.parse.urlencode({"tenant_id": "default", "active": "maybe"})
        assert _request(base + f"/api/v1/rag/documents?{invalid_query}", token=token)[0] == 400

        document_query = urllib.parse.urlencode(
            {"tenant_id": "default", "document_id": document_id}
        )
        assert _request(base + f"/api/v1/rag/documents/get?{document_query}")[0] == 401

        sync_payload = {
            "tenant_id": "default",
            "max_objects": 10,
            "deactivate_missing": True,
        }
        status, body, _ = _request(
            base + "/api/v1/rag/index/rsot", token=token, payload=sync_payload
        )
        assert status == 200 and _json(body)["imported"] == 1
        assert _request(base + "/api/v1/rag/index/rsot", payload=sync_payload)[0] == 401

        question_payload = {"tenant_id": "default", "question": "Que fournit OpenInfra ?"}
        status, body, _ = _request(
            base + "/api/v1/rag/query", token=token, payload=question_payload
        )
        assert status == 201
        answer_id = str(_json(body)["id"])
        assert _request(base + "/api/v1/rag/query", payload=question_payload)[0] == 401

        answers_query = urllib.parse.urlencode({"tenant_id": "default", "limit": 10})
        status, body, _ = _request(base + f"/api/v1/rag/answers?{answers_query}", token=token)
        assert status == 200 and len(_json(body)["items"]) == 1
        assert _request(base + f"/api/v1/rag/answers?{answers_query}")[0] == 401

        answer_query = urllib.parse.urlencode({"tenant_id": "default", "answer_id": answer_id})
        assert _request(base + f"/api/v1/rag/answers/get?{answer_query}", token=token)[0] == 200
        assert _request(base + f"/api/v1/rag/answers/get?{answer_query}")[0] == 401

        job_payload = {
            "tenant_id": "default",
            "kind": "answer-export",
            "idempotency_key": "all-routes-export",
            "payload": {"format": "json", "answer_ids": [answer_id]},
        }
        status, body, _ = _request(
            base + "/api/v1/rag/jobs/create", token=token, payload=job_payload
        )
        assert status == 201
        job_id = str(_json(body)["id"])
        assert _request(base + "/api/v1/rag/jobs/create", payload=job_payload)[0] == 401

        jobs_query = urllib.parse.urlencode({"tenant_id": "default", "limit": 10})
        assert _request(base + f"/api/v1/rag/jobs?{jobs_query}", token=token)[0] == 200
        assert _request(base + f"/api/v1/rag/jobs?{jobs_query}")[0] == 401
        job_query = urllib.parse.urlencode({"tenant_id": "default", "job_id": job_id})
        assert _request(base + f"/api/v1/rag/jobs/get?{job_query}", token=token)[0] == 200
        assert _request(base + f"/api/v1/rag/jobs/get?{job_query}")[0] == 401

        run_payload = {"tenant_id": "default", "job_id": job_id}
        assert _request(base + "/api/v1/rag/jobs/run", token=token, payload=run_payload)[0] == 200
        assert _request(base + "/api/v1/rag/jobs/run", payload=run_payload)[0] == 401
        assert _request(base + f"/api/v1/rag/jobs/artifact?{job_query}")[0] == 401

        deactivate_payload = {"tenant_id": "default", "document_id": document_id}
        assert (
            _request(
                base + "/api/v1/rag/documents/deactivate", token=token, payload=deactivate_payload
            )[0]
            == 200
        )
        assert (
            _request(base + "/api/v1/rag/documents/deactivate", payload=deactivate_payload)[0]
            == 401
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
