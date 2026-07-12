from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.async_processing_services import (
    GetAsyncArtifactCommand,
    StoreAsyncArtifactCommand,
    SubmitAsyncJobCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.rag_services import AskRagCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.async_processing import WorkStatus


def _app(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "z" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "specialized-admin", ("admin",), token)
    )
    return app, token


def _result(app, token: str, job_id: str) -> bytes:
    return app.async_processing_service.get_artifact(
        GetAsyncArtifactCommand("default", token, job_id, "result")
    ).content


def test_import_worker_consumes_external_artifact_and_applies_dataset(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    source = app.async_processing_service.store_artifact(
        StoreAsyncArtifactCommand(
            "default",
            token,
            "pytest",
            "imports-source",
            (
                b"asset_key,kind,name,source,tags,serial\n"
                b"device/async-01,device,Async server,async_import,prod,SN-ASYNC-01\n"
            ),
            "text/csv",
        )
    )
    job = app.async_processing_service.submit_job(
        SubmitAsyncJobCommand(
            "default",
            token,
            "pytest",
            "imports",
            "imports.dataset",
            "imports-worker-001",
            {
                "source_artifact": source.as_dict(),
                "format": "csv",
                "mapping": {
                    "key": "asset_key",
                    "kind": "kind",
                    "display_name": "name",
                    "source": "source",
                    "tags": "tags",
                    "attributes.serial": "serial",
                },
                "dry_run": False,
            },
        )
    )

    completed = app.import_worker.run_once(
        tenant_id="default", admin_token=token, worker_id="imports-01"
    )

    assert completed is not None and completed.id == job.id
    assert completed.state.status is WorkStatus.COMPLETED
    report = json.loads(_result(app, token, job.id.value))
    assert report["operation"] == "imports.dataset"
    assert report["report"]["status"] == "applied"
    current = app.source_of_truth_service.get_object(
        GetSourceObjectCommand("default", token, "device/async-01")
    )
    assert current["attributes"]["serial"] == "SN-ASYNC-01"


def test_graph_worker_exports_dependency_graph_outside_database(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    for key, kind, name in (
        ("application/async", "application", "Async app"),
        ("service/async", "service", "Async service"),
    ):
        app.source_of_truth_service.upsert_object(
            UpsertSourceObjectCommand(
                "default", "pytest", token, key, kind, name, "{}", (), "manual"
            )
        )
    app.source_of_truth_service.create_relation(
        CreateSourceRelationCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            relation_type="depends_on",
            source_key="application/async",
            target_key="service/async",
            provenance="manual",
        )
    )
    job = app.async_processing_service.submit_job(
        SubmitAsyncJobCommand(
            "default",
            token,
            "pytest",
            "graph",
            "graph.export",
            "graph-worker-001",
            {
                "root_key": "application/async",
                "direction": "outgoing",
                "format": "json",
                "include_spof": False,
            },
        )
    )

    completed = app.graph_worker.run_once(
        tenant_id="default", admin_token=token, worker_id="graph-01"
    )

    assert completed is not None and completed.state.status is WorkStatus.COMPLETED
    exported = json.loads(_result(app, token, job.id.value))
    assert exported["root_key"] == "application/async"
    assert exported["node_count"] == 2
    assert exported["edge_count"] == 1


def test_rag_worker_imports_documents_and_exports_answers(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    documents = app.async_processing_service.store_artifact(
        StoreAsyncArtifactCommand(
            "default",
            token,
            "pytest",
            "rag-source",
            json.dumps(
                {
                    "documents": [
                        {
                            "source_type": "documentation",
                            "source_ref": "async-rag-doc",
                            "title": "Worker RAG",
                            "content": "Le worker RAG traite les documents hors chemin HTTP.",
                            "required_permissions": ["rag.read"],
                            "tags": ["async"],
                        }
                    ]
                }
            ).encode(),
            "application/json",
        )
    )
    import_job = app.async_processing_service.submit_job(
        SubmitAsyncJobCommand(
            "default",
            token,
            "pytest",
            "rag",
            "rag.document-import",
            "rag-worker-import-001",
            {"source_artifact": documents.as_dict()},
        )
    )
    imported = app.rag_worker.run_once(tenant_id="default", admin_token=token, worker_id="rag-01")
    assert imported is not None and imported.state.status is WorkStatus.COMPLETED
    import_result = json.loads(_result(app, token, import_job.id.value))
    assert import_result["processed_count"] == 1

    answer = app.rag_service.ask(
        AskRagCommand("default", token, "Quel worker traite les documents ?")
    )
    export_job = app.async_processing_service.submit_job(
        SubmitAsyncJobCommand(
            "default",
            token,
            "pytest",
            "rag",
            "rag.answer-export",
            "rag-worker-export-001",
            {"format": "csv", "answer_ids": [answer.id.value]},
        )
    )
    exported = app.rag_worker.run_once(tenant_id="default", admin_token=token, worker_id="rag-01")
    assert exported is not None and exported.state.status is WorkStatus.COMPLETED
    content = _result(app, token, export_job.id.value).decode()
    assert "answer_id,question_hash,status,confidence,answer,citations" in content
    assert answer.id.value in content
