from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest

from openinfra.application.async_processing_services import AsyncProcessingService
from openinfra.application.specialized_worker_services import (
    GraphWorker,
    ImportWorker,
    RagWorker,
    SpecializedWorker,
    WorkerExecutionResult,
    WorkerPayload,
)
from openinfra.domain.async_processing import (
    ArtifactReference,
    AsyncJob,
    WorkerSpecialization,
)
from openinfra.domain.common import TenantId, ValidationError

ADMIN_TOKEN = "t" * 40


def _artifact() -> ArtifactReference:
    return ArtifactReference.create(
        object_key="default/async-payload/aa/" + "a" * 64 + ".json",
        sha256="a" * 64,
        size_bytes=2,
        media_type="application/json",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _job(specialization: WorkerSpecialization, operation: str) -> AsyncJob:
    created = AsyncJob.create(
        tenant_id=TenantId.from_value("default"),
        specialization=specialization,
        operation=operation,
        idempotency_key="worker-test-001",
        payload_artifact=_artifact(),
        max_attempts=3,
        requested_by="pytest",
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return created.claim("worker-01", 60, datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"not-json", "UTF-8 JSON"),
        (b"[]", "JSON object"),
        (b'"text"', "JSON object"),
        (b"\xff", "UTF-8 JSON"),
    ],
)
def test_worker_payload_rejects_invalid_documents(raw: bytes, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        WorkerPayload.from_bytes(raw)


def test_worker_payload_parses_supported_types_and_defaults() -> None:
    artifact = _artifact()
    payload = WorkerPayload.from_bytes(
        json.dumps(
            {
                "required": " value ",
                "optional": " ",
                "integer": "42",
                "enabled": "yes",
                "disabled": "off",
                "items": [" one ", "", 2],
                "mapping": {"key": "asset_key"},
                "source_artifact": artifact.as_dict(),
            }
        ).encode()
    )
    assert payload.string("required") == "value"
    assert payload.string("defaulted", "fallback") == "fallback"
    assert payload.optional_string("optional") is None
    assert payload.optional_string("missing") is None
    assert payload.integer("integer", 1) == 42
    assert payload.integer("missing", 7) == 7
    assert payload.boolean("enabled", False) is True
    assert payload.boolean("disabled", True) is False
    assert payload.boolean("missing", True) is True
    assert payload.strings("items") == ("one", "2")
    assert payload.strings("missing") == ()
    assert payload.mapping_json() == '{"key":"asset_key"}'
    assert payload.artifact() == artifact


def test_worker_payload_mapping_json_string_and_validation_edges() -> None:
    assert WorkerPayload({"mapping_json": '{"key":"id"}'}).mapping_json() == '{"key":"id"}'
    invalid_calls = (
        (lambda: WorkerPayload({}).string("required"), "required"),
        (lambda: WorkerPayload({"required": " "}).string("required"), "required"),
        (lambda: WorkerPayload({"number": True}).integer("number", 0), "integer"),
        (lambda: WorkerPayload({"number": "x"}).integer("number", 0), "integer"),
        (lambda: WorkerPayload({"flag": "sometimes"}).boolean("flag", False), "boolean"),
        (lambda: WorkerPayload({"items": "bad"}).strings("items"), "array"),
        (lambda: WorkerPayload({}).mapping_json(), "requires mapping"),
        (lambda: WorkerPayload({"mapping": []}).mapping_json(), "JSON object"),
        (lambda: WorkerPayload({}).artifact(), "must be an artifact"),
        (lambda: WorkerPayload({"source_artifact": {}}).artifact(), "valid artifact"),
    )
    for call, message in invalid_calls:
        with pytest.raises(ValidationError, match=message):
            call()


class _FakeAsyncService:
    def __init__(self, claimed: AsyncJob | None, *, payload: bytes = b"{}") -> None:
        self.claimed = claimed
        self.payload = payload
        self.completed: Any = None
        self.failed: Any = None

    def claim_job(self, command: Any) -> AsyncJob | None:
        self.claim_command = command
        return self.claimed

    def get_artifact(self, command: Any) -> Any:
        self.get_command = command
        return SimpleNamespace(content=self.payload)

    def complete_job(self, command: Any) -> AsyncJob:
        self.completed = command
        assert self.claimed is not None
        return self.claimed

    def fail_job(self, command: Any) -> AsyncJob:
        self.failed = command
        assert self.claimed is not None
        return self.claimed


class _EchoWorker(SpecializedWorker):
    specialization = WorkerSpecialization.IMPORTS

    def __init__(self, service: Any, *, fail: bool = False) -> None:
        super().__init__(cast(AsyncProcessingService, service))
        self.fail = fail

    def _execute(self, **_: Any) -> WorkerExecutionResult:
        if self.fail:
            raise ValidationError("worker failure")
        return WorkerExecutionResult(b'{"ok":true}', "application/json; charset=utf-8")


def test_specialized_worker_idle_success_and_failure_paths() -> None:
    idle_service = _FakeAsyncService(None)
    assert (
        _EchoWorker(idle_service).run_once(
            tenant_id="default", admin_token=ADMIN_TOKEN, worker_id="worker-01"
        )
        is None
    )

    claimed = _job(WorkerSpecialization.IMPORTS, "imports.dataset")
    service = _FakeAsyncService(claimed)
    completed = _EchoWorker(service).run_once(
        tenant_id="default", admin_token=ADMIN_TOKEN, worker_id="worker-01"
    )
    assert completed == claimed
    assert service.completed.media_type == "application/json"
    assert service.completed.result == b'{"ok":true}'

    failing = _FakeAsyncService(claimed)
    failed = _EchoWorker(failing, fail=True).run_once(
        tenant_id="default",
        admin_token=ADMIN_TOKEN,
        worker_id="worker-01",
        retry_delay_seconds=11,
    )
    assert failed == claimed
    assert failing.failed.error == "worker failure"
    assert failing.failed.retry_delay_seconds == 11


def test_specialized_worker_abstract_contract_and_helpers() -> None:
    with pytest.raises(TypeError, match="abstract"):
        SpecializedWorker(cast(AsyncProcessingService, object()))
    assert SpecializedWorker._base_media_type("Text/CSV; charset=UTF-8") == "text/csv"
    result = SpecializedWorker._json_result({"ok": True})
    assert json.loads(result.content) == {"ok": True}


def test_import_worker_dispatches_dataset_and_bulk_import() -> None:
    report = SimpleNamespace(as_dict=lambda: {"status": "applied"})
    import_service = Mock()
    import_service.import_dataset.return_value = report
    import_service.bulk_import_dataset.return_value = report
    store = Mock()
    store.read.return_value = b"asset_key,kind\nserver/1,server\n"
    worker = ImportWorker(cast(AsyncProcessingService, object()), import_service, store)
    payload = WorkerPayload(
        {
            "source_artifact": _artifact().as_dict(),
            "format": "csv",
            "mapping": {"key": "asset_key", "kind": "kind"},
            "dry_run": False,
            "batch_size": 10,
            "checkpoint_interval": 20,
            "sample_limit": 3,
            "resume_job_id": "resume-01",
        }
    )
    for operation in ("imports.dataset", "imports.bulk-dataset"):
        result = worker._execute(
            claimed=_job(WorkerSpecialization.IMPORTS, operation),
            payload=payload,
            tenant_id="default",
            admin_token=ADMIN_TOKEN,
            worker_id="worker-01",
        )
        assert json.loads(result.content)["report"]["status"] == "applied"
    assert import_service.import_dataset.call_count == 1
    assert import_service.bulk_import_dataset.call_count == 1
    with pytest.raises(ValidationError, match="does not support"):
        worker._execute(
            claimed=_job(WorkerSpecialization.IMPORTS, "imports.unknown"),
            payload=payload,
            tenant_id="default",
            admin_token=ADMIN_TOKEN,
            worker_id="worker-01",
        )


def test_graph_worker_dispatches_every_supported_operation() -> None:
    graph_service = Mock()
    response = SimpleNamespace(as_dict=lambda: {"ok": True})
    graph_service.traverse.return_value = response
    graph_service.impact.return_value = response
    graph_service.find_path.return_value = response
    graph_service.analyze_spof.return_value = response
    graph_service.export.return_value = SimpleNamespace(content=b"export", content_type="text/csv")
    worker = GraphWorker(cast(AsyncProcessingService, object()), graph_service)
    payload = WorkerPayload(
        {
            "root_key": "application/1",
            "source_key": "application/1",
            "target_key": "service/1",
            "direction": "both",
            "max_depth": 4,
            "max_nodes": 100,
            "relation_types": ["depends_on"],
            "as_of": "2026-01-01T00:00:00+00:00",
            "candidate_kinds": ["service"],
            "candidate_resource_categories": ["server"],
            "candidate_resource_types": ["virtual-machine"],
            "candidate_statuses": ["active"],
            "minimum_affected_nodes": 2,
            "affected_sample_limit": 5,
            "limit": 10,
            "cursor": "cursor-01",
            "format": "csv",
            "include_spof": False,
        }
    )
    for operation in ("graph.traverse", "graph.impact", "graph.path", "graph.spof"):
        result = worker._execute(
            claimed=_job(WorkerSpecialization.GRAPH, operation),
            payload=payload,
            tenant_id="default",
            admin_token=ADMIN_TOKEN,
            worker_id="worker-01",
        )
        assert json.loads(result.content) == {"ok": True}
    exported = worker._execute(
        claimed=_job(WorkerSpecialization.GRAPH, "graph.export"),
        payload=payload,
        tenant_id="default",
        admin_token=ADMIN_TOKEN,
        worker_id="worker-01",
    )
    assert exported == WorkerExecutionResult(b"export", "text/csv")
    with pytest.raises(ValidationError, match="does not support"):
        worker._execute(
            claimed=_job(WorkerSpecialization.GRAPH, "graph.unknown"),
            payload=payload,
            tenant_id="default",
            admin_token=ADMIN_TOKEN,
            worker_id="worker-01",
        )


def _answer(answer_id: str = "answer-01") -> Any:
    return SimpleNamespace(
        id=SimpleNamespace(value=answer_id),
        question_hash="hash",
        status=SimpleNamespace(value="grounded"),
        confidence=0.9,
        answer="answer",
        citations=("citation",),
        as_dict=lambda: {"id": answer_id},
    )


def test_rag_worker_sync_document_import_and_exports() -> None:
    rag_service = Mock()
    rag_service.sync_rsot.return_value = SimpleNamespace(as_dict=lambda: {"synced": 2})
    rag_service.upsert_document.side_effect = [
        SimpleNamespace(id=SimpleNamespace(value="doc-01")),
        SimpleNamespace(id=SimpleNamespace(value="doc-02")),
    ]
    rag_service.get_answer.return_value = _answer()
    rag_service.list_answers.return_value = SimpleNamespace(
        items=(_answer("answer-02"),), next_cursor=None
    )
    store = Mock()
    store.read.return_value = json.dumps(
        {
            "documents": [
                {
                    "source_type": "documentation",
                    "source_ref": "doc-01",
                    "title": "Title",
                    "content": "Content",
                    "required_permissions": ["rag.read"],
                    "tags": ["async"],
                    "metadata": {"kind": "runbook"},
                    "source_uri": "https://example.invalid/doc",
                },
                {
                    "source_ref": "doc-02",
                    "title": "Title 2",
                    "content": "Content 2",
                    "source_uri": None,
                },
            ]
        }
    ).encode()
    worker = RagWorker(cast(AsyncProcessingService, object()), rag_service, store)

    sync = worker._execute(
        claimed=_job(WorkerSpecialization.RAG, "rag.sync-rsot"),
        payload=WorkerPayload({"max_objects": 10, "deactivate_missing": True}),
        tenant_id="default",
        admin_token=ADMIN_TOKEN,
        worker_id="worker-01",
    )
    assert json.loads(sync.content) == {"synced": 2}

    imported = worker._execute(
        claimed=_job(WorkerSpecialization.RAG, "rag.document-import"),
        payload=WorkerPayload({"source_artifact": _artifact().as_dict()}),
        tenant_id="default",
        admin_token=ADMIN_TOKEN,
        worker_id="worker-01",
    )
    assert json.loads(imported.content)["processed_count"] == 2

    exported_json = worker._execute(
        claimed=_job(WorkerSpecialization.RAG, "rag.answer-export"),
        payload=WorkerPayload({"format": "json"}),
        tenant_id="default",
        admin_token=ADMIN_TOKEN,
        worker_id="worker-01",
    )
    assert json.loads(exported_json.content) == {"answers": [{"id": "answer-02"}]}

    exported_csv = worker._execute(
        claimed=_job(WorkerSpecialization.RAG, "rag.answer-export"),
        payload=WorkerPayload({"format": "csv", "answer_ids": ["answer-01"]}),
        tenant_id="default",
        admin_token=ADMIN_TOKEN,
        worker_id="worker-01",
    )
    assert exported_csv.media_type == "text/csv"
    assert "answer-01,hash,grounded,0.9,answer,1" in exported_csv.content.decode()

    with pytest.raises(ValidationError, match="does not support"):
        worker._execute(
            claimed=_job(WorkerSpecialization.RAG, "rag.unknown"),
            payload=WorkerPayload({}),
            tenant_id="default",
            admin_token=ADMIN_TOKEN,
            worker_id="worker-01",
        )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"bad", "valid UTF-8 JSON"),
        (b"[]", "1 to 10000"),
        (json.dumps(["bad"]).encode(), "JSON object"),
        (
            json.dumps({"documents": [{"required_permissions": "bad"}]}).encode(),
            "permissions and tags",
        ),
        (
            json.dumps({"documents": [{"metadata": []}]}).encode(),
            "metadata",
        ),
    ],
)
def test_rag_document_import_validation(raw: bytes, message: str) -> None:
    store = Mock()
    store.read.return_value = raw
    worker = RagWorker(cast(AsyncProcessingService, object()), Mock(), store)
    with pytest.raises(ValidationError, match=message):
        worker._import_documents(
            _job(WorkerSpecialization.RAG, "rag.document-import"),
            WorkerPayload({"source_artifact": _artifact().as_dict()}),
            "default",
            ADMIN_TOKEN,
            "worker-01",
        )


def test_rag_answer_export_validation_and_pagination_limit() -> None:
    rag_service = Mock()
    worker = RagWorker(cast(AsyncProcessingService, object()), rag_service, Mock())
    with pytest.raises(ValidationError, match="limited"):
        worker._export_answers(
            WorkerPayload({"answer_ids": [f"a-{index}" for index in range(10_001)]}),
            "default",
            ADMIN_TOKEN,
        )
    rag_service.list_answers.return_value = SimpleNamespace(items=(), next_cursor=None)
    with pytest.raises(ValidationError, match="json or csv"):
        worker._export_answers(WorkerPayload({"format": "xml"}), "default", ADMIN_TOKEN)

    page = SimpleNamespace(
        items=tuple(_answer(f"a-{index}") for index in range(500)), next_cursor="next"
    )
    rag_service.list_answers.return_value = page
    with pytest.raises(ValidationError, match="exceeds"):
        worker._export_answers(WorkerPayload({"format": "json"}), "default", ADMIN_TOKEN)
