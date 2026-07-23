from __future__ import annotations

import csv
import io
import json
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openinfra.application.async_processing_services import (
    AsyncProcessingService,
    ClaimAsyncJobCommand,
    CompleteAsyncJobCommand,
    FailAsyncJobCommand,
    GetAsyncArtifactCommand,
)
from openinfra.application.dependency_graph_services import (
    AnalyzeChangeImpactCommand,
    AnalyzeDependencyImpactCommand,
    AnalyzeDependencySpofCommand,
    DependencyGraphService,
    ExportDependencyGraphCommand,
    FindDependencyPathCommand,
    TraverseDependencyGraphCommand,
)
from openinfra.application.import_services import (
    BulkImportDatasetCommand,
    GenericImportService,
    ImportDatasetCommand,
)
from openinfra.application.ports import ArtifactStore, RuntimeTelemetry
from openinfra.application.rag_services import (
    GetRagAnswerCommand,
    ListRagAnswersCommand,
    RagService,
    SyncRsotRagCommand,
    UpsertRagDocumentCommand,
)
from openinfra.application.telemetry import NullRuntimeTelemetry
from openinfra.domain.async_processing import (
    ArtifactReference,
    AsyncJob,
    WorkerSpecialization,
    WorkStatus,
)
from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.rag import RagAnswer


@dataclass(frozen=True, slots=True)
class WorkerExecutionResult:
    content: bytes
    media_type: str = "application/json"


class WorkerPayload:
    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    @classmethod
    def from_bytes(cls, content: bytes) -> WorkerPayload:
        try:
            value = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("specialized worker payload must be valid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise ValidationError("specialized worker payload must be a JSON object")
        return cls({str(key): item for key, item in value.items()})

    def string(self, name: str, default: str | None = None) -> str:
        value = self._value.get(name, default)
        if value is None:
            raise ValidationError(f"specialized worker payload field {name} is required")
        normalized = str(value).strip()
        if not normalized:
            raise ValidationError(f"specialized worker payload field {name} is required")
        return normalized

    def optional_string(self, name: str) -> str | None:
        value = self._value.get(name)
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def integer(self, name: str, default: int) -> int:
        value = self._value.get(name, default)
        if isinstance(value, bool):
            raise ValidationError(f"specialized worker payload field {name} must be an integer")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"specialized worker payload field {name} must be an integer"
            ) from exc

    def boolean(self, name: str, default: bool) -> bool:
        value = self._value.get(name, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        raise ValidationError(f"specialized worker payload field {name} must be a boolean")

    def strings(self, name: str) -> tuple[str, ...]:
        value = self._value.get(name, [])
        if not isinstance(value, list):
            raise ValidationError(f"specialized worker payload field {name} must be an array")
        return tuple(str(item).strip() for item in value if str(item).strip())

    def mapping_json(self) -> str:
        value = self._value.get("mapping")
        if value is None:
            raw = self._value.get("mapping_json")
            if not isinstance(raw, str):
                raise ValidationError("specialized import payload requires mapping or mapping_json")
            return raw
        if not isinstance(value, dict):
            raise ValidationError("specialized import payload mapping must be a JSON object")
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def artifact(self, name: str = "source_artifact") -> ArtifactReference:
        value = self._value.get(name)
        if not isinstance(value, dict):
            raise ValidationError(f"specialized worker payload field {name} must be an artifact")
        try:
            return ArtifactReference.from_dict({str(key): item for key, item in value.items()})
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(
                f"specialized worker payload field {name} is not a valid artifact reference"
            ) from exc


class SpecializedWorker(ABC):
    specialization: WorkerSpecialization

    def __init__(
        self,
        async_service: AsyncProcessingService,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self._async_service = async_service
        self._telemetry = telemetry or NullRuntimeTelemetry()

    def run_once(
        self,
        *,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
        lease_seconds: int = 60,
        retry_delay_seconds: int = 30,
    ) -> AsyncJob | None:
        started_at = time.perf_counter()
        outcome = "failed"
        self._telemetry.worker_started(self.specialization.value)
        try:
            claimed = self._async_service.claim_job(
                ClaimAsyncJobCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    actor=worker_id,
                    specialization=self.specialization.value,
                    worker_id=worker_id,
                    lease_seconds=lease_seconds,
                )
            )
            if claimed is None:
                outcome = "idle"
                return None
            try:
                artifact = self._async_service.get_artifact(
                    GetAsyncArtifactCommand(tenant_id, admin_token, claimed.id.value, "payload")
                )
                payload = WorkerPayload.from_bytes(artifact.content)
                result = self._execute(
                    claimed=claimed,
                    payload=payload,
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    worker_id=worker_id,
                )
                completed = self._async_service.complete_job(
                    CompleteAsyncJobCommand(
                        tenant_id=tenant_id,
                        admin_token=admin_token,
                        actor=worker_id,
                        job_id=claimed.id.value,
                        worker_id=worker_id,
                        lease_token=claimed.state.lease_token,
                        result=result.content,
                        media_type=self._base_media_type(result.media_type),
                    )
                )
                outcome = "completed"
                return completed
            except Exception as exc:
                failed = self._async_service.fail_job(
                    FailAsyncJobCommand(
                        tenant_id=tenant_id,
                        admin_token=admin_token,
                        actor=worker_id,
                        job_id=claimed.id.value,
                        worker_id=worker_id,
                        lease_token=claimed.state.lease_token,
                        error=str(exc),
                        retry_delay_seconds=retry_delay_seconds,
                    )
                )
                outcome = (
                    "dead-letter" if failed.state.status is WorkStatus.DEAD_LETTER else "retry"
                )
                return failed
        finally:
            self._telemetry.worker_finished(
                self.specialization.value,
                outcome,
                max(0.0, time.perf_counter() - started_at),
            )

    @abstractmethod
    def _execute(
        self,
        *,
        claimed: AsyncJob,
        payload: WorkerPayload,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
    ) -> WorkerExecutionResult:
        raise TypeError("specialized worker contract invoked directly")

    @staticmethod
    def _json_result(value: dict[str, object]) -> WorkerExecutionResult:
        return WorkerExecutionResult(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        )

    @staticmethod
    def _base_media_type(value: str) -> str:
        return value.split(";", 1)[0].strip().lower()


class ImportWorker(SpecializedWorker):
    specialization = WorkerSpecialization.IMPORTS

    def __init__(
        self,
        async_service: AsyncProcessingService,
        import_service: GenericImportService,
        artifact_store: ArtifactStore,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        super().__init__(async_service, telemetry)
        self._import_service = import_service
        self._artifact_store = artifact_store

    def _execute(
        self,
        *,
        claimed: AsyncJob,
        payload: WorkerPayload,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
    ) -> WorkerExecutionResult:
        source = payload.artifact()
        import_format = payload.string("format")
        suffix = "." + import_format.strip().lower().replace("yaml", "yml")
        with tempfile.TemporaryDirectory(prefix="openinfra-import-") as directory:
            path = Path(directory) / ("dataset" + suffix)
            self._artifact_store.materialize(TenantId.from_value(tenant_id), source, path)
            if claimed.operation == "imports.dataset":
                report_payload = self._import_service.import_dataset(
                    ImportDatasetCommand(
                        tenant_id=tenant_id,
                        actor=worker_id,
                        admin_token=admin_token,
                        file_path=path,
                        format=import_format,
                        mapping_json=payload.mapping_json(),
                        dry_run=payload.boolean("dry_run", True),
                        batch_size=payload.integer("batch_size", 500),
                    )
                ).as_dict()
            elif claimed.operation == "imports.bulk-dataset":
                report_payload = self._import_service.bulk_import_dataset(
                    BulkImportDatasetCommand(
                        tenant_id=tenant_id,
                        actor=worker_id,
                        admin_token=admin_token,
                        file_path=path,
                        format=import_format,
                        mapping_json=payload.mapping_json(),
                        dry_run=payload.boolean("dry_run", True),
                        batch_size=payload.integer("batch_size", 5_000),
                        checkpoint_interval=payload.integer("checkpoint_interval", 25_000),
                        resume_job_id=payload.optional_string("resume_job_id"),
                        sample_limit=payload.integer("sample_limit", 100),
                    )
                ).as_dict()
            else:
                raise ValidationError("imports worker does not support this operation")
        return self._json_result(
            {
                "schema_version": "1.0",
                "async_job_id": claimed.id.value,
                "operation": claimed.operation,
                "source_artifact": source.as_dict(),
                "report": report_payload,
            }
        )


class GraphWorker(SpecializedWorker):
    specialization = WorkerSpecialization.GRAPH

    def __init__(
        self,
        async_service: AsyncProcessingService,
        graph_service: DependencyGraphService,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        super().__init__(async_service, telemetry)
        self._graph_service = graph_service

    def _execute(
        self,
        *,
        claimed: AsyncJob,
        payload: WorkerPayload,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
    ) -> WorkerExecutionResult:
        del worker_id
        direction = payload.string("direction", "both")
        max_depth = payload.integer("max_depth", 8)
        max_nodes = payload.integer("max_nodes", 2_000)
        relation_types = payload.strings("relation_types")
        as_of = payload.optional_string("as_of")
        if claimed.operation == "graph.traverse":
            graph = self._graph_service.traverse(
                TraverseDependencyGraphCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    root_key=payload.string("root_key"),
                    direction=direction,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    relation_types=relation_types,
                    as_of=as_of,
                )
            )
            return self._json_result(graph.as_dict())
        if claimed.operation == "graph.impact":
            impact = self._graph_service.impact(
                AnalyzeDependencyImpactCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    root_key=payload.string("root_key"),
                    direction=direction,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    relation_types=relation_types,
                    as_of=as_of,
                )
            )
            return self._json_result(impact.as_dict())
        if claimed.operation == "graph.change-impact":
            report = self._graph_service.analyze_change_impact(
                AnalyzeChangeImpactCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    root_key=payload.string("root_key"),
                    direction=direction,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    relation_types=relation_types,
                    as_of=as_of,
                    business_service_kinds=payload.strings("business_service_kinds"),
                    business_service_resource_types=payload.strings(
                        "business_service_resource_types"
                    ),
                    affected_sample_limit=payload.integer("affected_sample_limit", 25),
                )
            )
            return self._json_result(report.as_dict())
        if claimed.operation == "graph.path":
            path = self._graph_service.find_path(
                FindDependencyPathCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    source_key=payload.string("source_key"),
                    target_key=payload.string("target_key"),
                    direction=direction,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    relation_types=relation_types,
                    as_of=as_of,
                )
            )
            return self._json_result(path.as_dict())
        if claimed.operation == "graph.spof":
            spof = self._graph_service.analyze_spof(
                AnalyzeDependencySpofCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    root_key=payload.string("root_key"),
                    direction=direction,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    relation_types=relation_types,
                    as_of=as_of,
                    candidate_kinds=payload.strings("candidate_kinds"),
                    candidate_resource_categories=payload.strings("candidate_resource_categories"),
                    candidate_resource_types=payload.strings("candidate_resource_types"),
                    candidate_statuses=payload.strings("candidate_statuses"),
                    minimum_affected_nodes=payload.integer("minimum_affected_nodes", 1),
                    affected_sample_limit=payload.integer("affected_sample_limit", 25),
                    limit=payload.integer("limit", 100),
                    cursor=payload.optional_string("cursor"),
                )
            )
            return self._json_result(spof.as_dict())
        if claimed.operation == "graph.export":
            export = self._graph_service.export(
                ExportDependencyGraphCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    root_key=payload.string("root_key"),
                    direction=direction,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    relation_types=relation_types,
                    as_of=as_of,
                    format=payload.string("format", "json"),
                    include_spof=payload.boolean("include_spof", True),
                    candidate_kinds=payload.strings("candidate_kinds"),
                    candidate_resource_categories=payload.strings("candidate_resource_categories"),
                    candidate_resource_types=payload.strings("candidate_resource_types"),
                    candidate_statuses=payload.strings("candidate_statuses"),
                    minimum_affected_nodes=payload.integer("minimum_affected_nodes", 1),
                )
            )
            return WorkerExecutionResult(export.content, export.content_type)
        raise ValidationError("graph worker does not support this operation")


class RagWorker(SpecializedWorker):
    specialization = WorkerSpecialization.RAG

    def __init__(
        self,
        async_service: AsyncProcessingService,
        rag_service: RagService,
        artifact_store: ArtifactStore,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        super().__init__(async_service, telemetry)
        self._rag_service = rag_service
        self._artifact_store = artifact_store

    def _execute(
        self,
        *,
        claimed: AsyncJob,
        payload: WorkerPayload,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
    ) -> WorkerExecutionResult:
        if claimed.operation == "rag.sync-rsot":
            result = self._rag_service.sync_rsot(
                SyncRsotRagCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    actor=worker_id,
                    max_objects=payload.integer("max_objects", 5_000),
                    deactivate_missing=payload.boolean("deactivate_missing", False),
                )
            )
            return self._json_result(result.as_dict())
        if claimed.operation == "rag.document-import":
            return self._import_documents(claimed, payload, tenant_id, admin_token, worker_id)
        if claimed.operation == "rag.answer-export":
            return self._export_answers(payload, tenant_id, admin_token)
        raise ValidationError("RAG worker does not support this operation")

    def _import_documents(
        self,
        claimed: AsyncJob,
        payload: WorkerPayload,
        tenant_id: str,
        admin_token: str,
        worker_id: str,
    ) -> WorkerExecutionResult:
        source = payload.artifact()
        raw = self._artifact_store.read(TenantId.from_value(tenant_id), source)
        try:
            document_payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("RAG document artifact must be valid UTF-8 JSON") from exc
        documents = (
            document_payload.get("documents")
            if isinstance(document_payload, dict)
            else document_payload
        )
        if not isinstance(documents, list) or not 1 <= len(documents) <= 10_000:
            raise ValidationError("RAG document artifact requires 1 to 10000 documents")
        document_ids: list[str] = []
        for raw_document in documents:
            if not isinstance(raw_document, dict):
                raise ValidationError("RAG document import item must be a JSON object")
            required = raw_document.get("required_permissions", ["rag.read"])
            tags = raw_document.get("tags", [])
            metadata = raw_document.get("metadata", {})
            if not isinstance(required, list) or not isinstance(tags, list):
                raise ValidationError("RAG document permissions and tags must be arrays")
            if not isinstance(metadata, dict):
                raise ValidationError("RAG document metadata must be a JSON object")
            document = self._rag_service.upsert_document(
                UpsertRagDocumentCommand(
                    tenant_id=tenant_id,
                    admin_token=admin_token,
                    source_type=str(raw_document.get("source_type", "documentation")),
                    source_ref=str(raw_document.get("source_ref", "")),
                    title=str(raw_document.get("title", "")),
                    content=str(raw_document.get("content", "")),
                    required_permissions=tuple(str(item) for item in required),
                    tags=tuple(str(item) for item in tags),
                    metadata={str(key): item for key, item in metadata.items()},
                    source_uri=(
                        None
                        if raw_document.get("source_uri") is None
                        else str(raw_document["source_uri"])
                    ),
                    actor=worker_id,
                )
            )
            if len(document_ids) < 100:
                document_ids.append(document.id.value)
        return self._json_result(
            {
                "schema_version": "1.0",
                "async_job_id": claimed.id.value,
                "operation": claimed.operation,
                "source_artifact": source.as_dict(),
                "processed_count": len(documents),
                "document_id_sample": document_ids,
                "sample_truncated": len(documents) > len(document_ids),
            }
        )

    def _export_answers(
        self,
        payload: WorkerPayload,
        tenant_id: str,
        admin_token: str,
    ) -> WorkerExecutionResult:
        answer_ids = payload.strings("answer_ids")
        answers: list[RagAnswer] = []
        if answer_ids:
            if len(answer_ids) > 10_000:
                raise ValidationError("RAG answer export is limited to 10000 answers")
            for answer_id in answer_ids:
                answers.append(
                    self._rag_service.get_answer(
                        GetRagAnswerCommand(tenant_id, admin_token, answer_id)
                    )
                )
        else:
            cursor: str | None = None
            while len(answers) < 10_000:
                page = self._rag_service.list_answers(
                    ListRagAnswersCommand(tenant_id, admin_token, 500, cursor)
                )
                answers.extend(page.items)
                cursor = page.next_cursor
                if cursor is None or not page.items:
                    break
            if cursor is not None:
                raise ValidationError("RAG answer export exceeds 10000 answers")
        export_format = payload.string("format", "json").lower()
        if export_format == "json":
            return self._json_result({"answers": [item.as_dict() for item in answers]})
        if export_format != "csv":
            raise ValidationError("RAG answer export format must be json or csv")
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(
            ["answer_id", "question_hash", "status", "confidence", "answer", "citations"]
        )
        for answer in answers:
            writer.writerow(
                [
                    answer.id.value,
                    answer.question_hash,
                    answer.status.value,
                    str(answer.confidence),
                    answer.answer,
                    len(answer.citations),
                ]
            )
        return WorkerExecutionResult(stream.getvalue().encode("utf-8"), "text/csv")
