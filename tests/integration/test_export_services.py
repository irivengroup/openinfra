from __future__ import annotations

import csv
import json
import zipfile
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.export_services import (
    GetExportArtifactChunkCommand,
    GetExportArtifactCommand,
    GetExportJobCommand,
    RequestExportCommand,
    RunExportJobCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import ValidationError
from openinfra.domain.data_export import (
    ExportArtifactMetadata,
    ExportFilter,
    ExportFormat,
    ExportJob,
    ExportJobStatus,
    ExportResource,
)


def _bootstrap(app: Any) -> str:
    token = "e" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="export-admin",
            roles=("itrm:operator", "audit:reader"),
            token=token,
        )
    )
    return token


def _create_object(app: Any, token: str, key: str, tag: str = "prod") -> None:
    app.source_of_truth_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key=key,
            kind="device",
            display_name="Export " + key.rsplit("/", 1)[-1],
            attributes_json=json.dumps({"serial": key.rsplit("/", 1)[-1].upper()}),
            tags=(tag,),
            source="pytest_export",
        )
    )


class TestExportService:
    def test_request_is_queued_and_run_creates_signed_json_artifact(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        _create_object(app, token, "device/export-001")

        queued = app.export_service.request_export(
            RequestExportCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                resource="source_objects",
                format="json",
                kind="device",
                tag="prod",
                limit=10,
            )
        )
        persisted_queued = app.export_service.get_export_job(
            GetExportJobCommand("default", token, queued.id.value)
        )

        assert queued.status is ExportJobStatus.QUEUED
        assert persisted_queued.artifact is None

        completed = app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, queued.id.value, page_size=2)
        )
        download = app.export_service.get_export_artifact(
            GetExportArtifactCommand("default", token, completed.id.value)
        )
        payload = json.loads(download.content.decode("utf-8"))

        assert completed.status is ExportJobStatus.COMPLETED
        assert completed.total_rows == 1
        assert completed.artifact is not None
        assert completed.artifact.signature_algorithm == "hmac-sha256"
        assert len(completed.artifact.signature) == 64
        assert payload[0]["key"] == "device/export-001"
        assert download.as_dict()["content_size_bytes"] == len(download.content)

    def test_signed_artifact_chunk_is_bounded_and_resumable(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        _create_object(app, token, "device/export-chunk-001")

        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="json", limit=10)
        )
        app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, queued.id.value, page_size=1)
        )

        first = app.export_service.get_export_artifact_chunk(
            GetExportArtifactChunkCommand("default", token, queued.id.value, offset=0, size=24)
        )
        second = app.export_service.get_export_artifact_chunk(
            GetExportArtifactChunkCommand(
                "default", token, queued.id.value, offset=first.next_offset or 0, size=4096
            )
        )
        combined = first.content + second.content
        full = app.export_service.get_export_artifact(
            GetExportArtifactCommand("default", token, queued.id.value)
        )

        assert first.as_dict()["chunk_size_bytes"] == 24
        assert first.as_dict()["next_offset"] == 24
        assert first.as_dict()["final_chunk"] is False
        assert second.as_dict()["final_chunk"] is True
        assert second.as_dict()["content_base64"]
        assert combined == full.content

        with pytest.raises(ValidationError, match="chunk size"):
            app.export_service.get_export_artifact_chunk(
                GetExportArtifactChunkCommand("default", token, queued.id.value, size=0)
            )
        with pytest.raises(ValidationError, match="offset exceeds"):
            app.export_service.get_export_artifact_chunk(
                GetExportArtifactChunkCommand("default", token, queued.id.value, offset=len(full.content) + 1)
            )

    def test_json_backend_signing_secret_is_lazy_and_survives_reload(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        app = ApplicationFactory().create_json_application(state_path)
        token = _bootstrap(app)
        persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
        assert "export_signing_secret" not in persisted_state
        _create_object(app, token, "device/export-reload")

        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="json")
        )
        app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, queued.id.value)
        )
        signed_state = json.loads(state_path.read_text(encoding="utf-8"))
        assert len(signed_state["export_signing_secret"]) == 64

        reloaded = ApplicationFactory().create_json_application(state_path)
        download = reloaded.export_service.get_export_artifact(
            GetExportArtifactCommand("default", token, queued.id.value)
        )
        payload = json.loads(download.content.decode("utf-8"))
        assert payload[0]["key"] == "device/export-reload"

    def test_csv_export_uses_queue_order_and_filters(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        _create_object(app, token, "device/export-101", tag="prod")
        _create_object(app, token, "device/export-102", tag="dev")

        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="csv", tag="prod")
        )
        completed = app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, None, page_size=1)
        )
        download = app.export_service.get_export_artifact(
            GetExportArtifactCommand("default", token, queued.id.value)
        )
        rows = tuple(csv.DictReader(StringIO(download.content.decode("utf-8"))))

        assert completed.id == queued.id
        assert rows[0]["key"] == "device/export-101"
        assert rows[0]["attributes_json"] == (
            '{"resource_category": "other", '
            '"resource_type": "unknown-device", '
            '"serial": "EXPORT-101"}'
        )
        assert len(rows) == 1

    def test_xlsx_export_binary_opens_from_bytes(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        _create_object(app, token, "device/export-202")
        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="xlsx")
        )
        app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, queued.id.value)
        )
        download = app.export_service.get_export_artifact(
            GetExportArtifactCommand("default", token, queued.id.value)
        )
        workbook_path = tmp_path / "export.xlsx"
        workbook_path.write_bytes(download.content)

        with zipfile.ZipFile(workbook_path) as workbook:
            assert "xl/worksheets/sheet1.xml" in workbook.namelist()
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            assert "device/export-202" in sheet

    def test_artifact_retrieval_rejects_tampering(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        _create_object(app, token, "device/export-301")
        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="json")
        )
        app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, queued.id.value)
        )
        key = "default:" + queued.id.value
        app.store.data["export_artifacts"][key]["content_hex"] = b"tampered".hex()
        app.store.mark_dirty()

        with pytest.raises(ValidationError, match="digest verification failed"):
            app.export_service.get_export_artifact(
                GetExportArtifactCommand("default", token, queued.id.value)
            )

    def test_export_domain_validates_filters_and_completed_artifact(self) -> None:
        with pytest.raises(ValidationError, match="limit"):
            ExportFilter.create(limit=0)
        with pytest.raises(ValidationError, match="requires an artifact"):
            ExportJob.create(
                tenant_id=app_tenant(),
                resource=ExportResource.SOURCE_OBJECTS,
                export_format=ExportFormat.JSON,
                export_filter=ExportFilter.create(),
                requested_by="pytest",
                status=ExportJobStatus.COMPLETED,
            )
        with pytest.raises(ValidationError, match="sha256"):
            ExportArtifactMetadata.create(
                "exports/default/job.json",
                "openinfra-export.json",
                "application/json",
                1,
                "bad",
                "hmac-sha256",
                "0" * 64,
            )

    def test_export_validation_and_repository_error_edges(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)

        assert ExportFormat.from_value(".csv").media_type == "text/csv; charset=utf-8"
        assert ExportFormat.XLSX.extension == "xlsx"
        with pytest.raises(ValidationError, match="format"):
            ExportFormat.from_value("xml")
        with pytest.raises(ValidationError, match="resource"):
            ExportResource.from_value("asset")
        with pytest.raises(ValidationError, match="kind"):
            ExportFilter.create(kind="1bad")
        with pytest.raises(ValidationError, match="tag"):
            ExportFilter.create(tag="-bad")
        with pytest.raises(ValidationError, match="page size"):
            app.export_service.run_export_job(
                RunExportJobCommand("default", "pytest", token, page_size=0)
            )
        with pytest.raises(ValidationError, match="queue is empty"):
            app.export_service.run_export_job(RunExportJobCommand("default", "pytest", token))
        with pytest.raises(ValidationError, match="not found"):
            app.export_service.get_export_job(GetExportJobCommand("default", token, "missing"))
        with pytest.raises(ValidationError, match="not found"):
            app.export_service.get_export_artifact(
                GetExportArtifactCommand("default", token, "missing")
            )
        assert app.export_repository.export_storage_strategy_name() == "json-managed-object-storage"

        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="json")
        )
        with pytest.raises(ValidationError, match="not available"):
            app.export_service.get_export_artifact(
                GetExportArtifactCommand("default", token, queued.id.value)
            )
        app.store.data["export_jobs"]["default:" + queued.id.value] = "invalid"
        app.store.mark_dirty()
        with pytest.raises(ValidationError, match="stored export job"):
            app.export_service.get_export_job(
                GetExportJobCommand("default", token, queued.id.value)
            )

    def test_export_artifact_metadata_and_job_validation_edges(self) -> None:
        now = datetime.now(UTC)
        artifact = ExportArtifactMetadata.create(
            "exports/default/job.json",
            "openinfra-export.json",
            "application/json",
            2,
            "a" * 64,
            "hmac-sha256",
            "b" * 64,
            created_at=now,
        )

        invalid_artifacts = (
            {"storage_key": "x"},
            {"storage_key": "exports/default/../job.json"},
            {"filename": "..bad"},
            {"size_bytes": -1},
            {"sha256": "bad"},
            {"signature": "bad"},
            {"signature_algorithm": "plain"},
            {"created_at": datetime.now()},
        )
        for override in invalid_artifacts:
            values = {
                "storage_key": "exports/default/job.json",
                "filename": "openinfra-export.json",
                "media_type": "application/json",
                "size_bytes": 1,
                "sha256": "a" * 64,
                "signature_algorithm": "hmac-sha256",
                "signature": "b" * 64,
                "created_at": now,
            }
            values.update(override)
            with pytest.raises(ValidationError):
                ExportArtifactMetadata.create(**values)

        tenant = app_tenant()
        export_filter = ExportFilter.create()
        with pytest.raises(ValidationError, match="requested_by"):
            ExportJob.create(
                tenant, ExportResource.SOURCE_OBJECTS, ExportFormat.JSON, export_filter, " "
            )
        with pytest.raises(ValidationError, match="negative"):
            ExportJob.create(
                tenant,
                ExportResource.SOURCE_OBJECTS,
                ExportFormat.JSON,
                export_filter,
                "pytest",
                total_rows=-1,
            )
        with pytest.raises(ValidationError, match="requires an error"):
            ExportJob.create(
                tenant,
                ExportResource.SOURCE_OBJECTS,
                ExportFormat.JSON,
                export_filter,
                "pytest",
                status=ExportJobStatus.FAILED,
            )
        with pytest.raises(ValidationError, match="timezone"):
            ExportJob.create(
                tenant,
                ExportResource.SOURCE_OBJECTS,
                ExportFormat.JSON,
                export_filter,
                "pytest",
                created_at=datetime.now(),
            )
        with pytest.raises(ValidationError, match="before created"):
            ExportJob.create(
                tenant,
                ExportResource.SOURCE_OBJECTS,
                ExportFormat.JSON,
                export_filter,
                "pytest",
                created_at=now,
                updated_at=now - timedelta(seconds=1),
            )
        failed = ExportJob.create(
            tenant,
            ExportResource.SOURCE_OBJECTS,
            ExportFormat.JSON,
            export_filter,
            "pytest",
        ).mark_failed("boom")
        assert failed.status is ExportJobStatus.FAILED
        assert failed.error == "boom"

        completed = ExportJob.create(
            tenant,
            ExportResource.SOURCE_OBJECTS,
            ExportFormat.JSON,
            export_filter,
            "pytest",
        ).mark_completed(2, artifact)
        payload = completed.as_dict()
        payload["filter"] = "invalid"
        with pytest.raises(ValidationError, match="stored export filter"):
            ExportJob.from_dict(payload)

    def test_export_run_failure_artifact_integrity_and_pagination_edges(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = _bootstrap(app)
        for index in range(3):
            _create_object(app, token, f"device/export-page-{index}")
        queued = app.export_service.request_export(
            RequestExportCommand("default", "pytest", token, format="csv", limit=3)
        )
        completed = app.export_service.run_export_job(
            RunExportJobCommand("default", "pytest", token, queued.id.value, page_size=2)
        )
        assert completed.total_rows == 3
        with pytest.raises(ValidationError, match="not queued"):
            app.export_service.run_export_job(
                RunExportJobCommand("default", "pytest", token, queued.id.value)
            )

        job_key = "default:" + queued.id.value
        original_signature = app.store.data["export_jobs"][job_key]["artifact"]["signature"]
        app.store.data["export_jobs"][job_key]["artifact"]["signature"] = "0" * 64
        app.store.mark_dirty()
        with pytest.raises(ValidationError, match="signature verification failed"):
            app.export_service.get_export_artifact(
                GetExportArtifactCommand("default", token, queued.id.value)
            )
        app.store.data["export_jobs"][job_key]["artifact"]["signature"] = original_signature
        app.store.data["export_artifacts"].pop(job_key)
        app.store.mark_dirty()
        with pytest.raises(ValidationError, match="content is missing"):
            app.export_service.get_export_artifact(
                GetExportArtifactCommand("default", token, queued.id.value)
            )
        app.store.data["export_artifacts"][job_key] = "invalid"
        app.store.mark_dirty()
        with pytest.raises(ValidationError, match="stored export artifact"):
            app.export_service.get_export_artifact(
                GetExportArtifactCommand("default", token, queued.id.value)
            )

        failing = ApplicationFactory().create_json_application(tmp_path / "failing-state.json")
        failing_token = _bootstrap(failing)
        failing_job = failing.export_service.request_export(
            RequestExportCommand("default", "pytest", failing_token, format="json")
        )

        def broken_list_objects(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("backend unavailable")

        monkeypatch.setattr(failing.source_of_truth_repository, "list_objects", broken_list_objects)
        with pytest.raises(ValidationError, match="export job failed"):
            failing.export_service.run_export_job(
                RunExportJobCommand("default", "pytest", failing_token, failing_job.id.value)
            )
        failed_job = failing.export_service.get_export_job(
            GetExportJobCommand("default", failing_token, failing_job.id.value)
        )
        assert failed_job.status is ExportJobStatus.FAILED
        assert failed_job.error == "backend unavailable"

        validation_failing = ApplicationFactory().create_json_application(
            tmp_path / "validation-failing-state.json"
        )
        validation_token = _bootstrap(validation_failing)
        validation_job = validation_failing.export_service.request_export(
            RequestExportCommand("default", "pytest", validation_token, format="json")
        )

        def validation_error_list_objects(*_args: object, **_kwargs: object) -> object:
            raise ValidationError("backend validation failed")

        monkeypatch.setattr(
            validation_failing.source_of_truth_repository,
            "list_objects",
            validation_error_list_objects,
        )
        with pytest.raises(ValidationError, match="backend validation failed"):
            validation_failing.export_service.run_export_job(
                RunExportJobCommand("default", "pytest", validation_token, validation_job.id.value)
            )

        class UnsupportedResource:
            value = "unsupported"

        unsupported_job = ExportJob.create(
            tenant_id=app_tenant(),
            resource=ExportResource.SOURCE_OBJECTS,
            export_format=ExportFormat.JSON,
            export_filter=ExportFilter.create(),
            requested_by="pytest",
        )
        object.__setattr__(unsupported_job, "resource", UnsupportedResource())
        with pytest.raises(ValidationError, match="unsupported export resource"):
            app.export_service._collect_source_objects(unsupported_job, 10)

        with pytest.raises(ValidationError, match="tags are invalid"):
            app.export_service._flat_row(
                {
                    "key": "device/invalid",
                    "kind": "device",
                    "display_name": "Invalid",
                    "source": "pytest",
                    "tags": "prod",
                    "version": 1,
                    "status": "active",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                    "attributes": {},
                }
            )


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def app_tenant() -> Any:
    from openinfra.domain.common import TenantId

    return TenantId.from_value("default")
