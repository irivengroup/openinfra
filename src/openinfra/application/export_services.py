from __future__ import annotations

import csv
import hashlib
import hmac
import json
from dataclasses import dataclass
from html import escape
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from openinfra.application.ports import (
    AuditRepository,
    ExportRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, Pagination, Severity, TenantId, ValidationError
from openinfra.domain.data_export import (
    ExportArtifactMetadata,
    ExportFilter,
    ExportFormat,
    ExportJob,
    ExportJobStatus,
    ExportResource,
)
from openinfra.domain.security import Permission
from openinfra.domain.source_of_truth import SourceOfTruthObject


@dataclass(frozen=True, slots=True)
class RequestExportCommand:
    tenant_id: str
    actor: str
    admin_token: str
    resource: str = "source_objects"
    format: str = "json"
    kind: str | None = None
    tag: str | None = None
    limit: int = 100_000


@dataclass(frozen=True, slots=True)
class RunExportJobCommand:
    tenant_id: str
    actor: str
    admin_token: str
    job_id: str | None = None
    page_size: int = 500


@dataclass(frozen=True, slots=True)
class GetExportJobCommand:
    tenant_id: str
    admin_token: str
    job_id: str


@dataclass(frozen=True, slots=True)
class GetExportArtifactCommand:
    tenant_id: str
    admin_token: str
    job_id: str


@dataclass(frozen=True, slots=True)
class ExportArtifactDownload:
    job: ExportJob
    content: bytes

    def as_dict(self) -> dict[str, object]:
        payload = self.job.as_dict()
        payload["content_sha256"] = hashlib.sha256(self.content).hexdigest()
        payload["content_size_bytes"] = len(self.content)
        return payload


class ExportService:
    def __init__(
        self,
        export_repository: ExportRepository,
        source_repository: SourceOfTruthRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._export_repository = export_repository
        self._source_repository = source_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def request_export(self, command: RequestExportCommand) -> ExportJob:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        resource = ExportResource.from_value(command.resource)
        export_format = ExportFormat.from_value(command.format)
        export_filter = ExportFilter.create(command.kind, command.tag, command.limit)
        job = ExportJob.create(
            tenant_id=tenant_id,
            resource=resource,
            export_format=export_format,
            export_filter=export_filter,
            requested_by=principal.subject,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._export_repository.save_export_job(job)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="export.job.queued",
                    target_type="export_job",
                    target_id=job.id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "resource": resource.value,
                        "format": export_format.value,
                        "filter": export_filter.as_dict(),
                    },
                )
            )
            unit_of_work.commit()
        return job

    def run_export_job(self, command: RunExportJobCommand) -> ExportJob:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        page_size = self._normalize_page_size(command.page_size)
        with self._transaction_manager.begin() as unit_of_work:
            job = self._load_runnable_job(tenant_id, command.job_id).mark_running()
            self._export_repository.save_export_job(job)
            unit_of_work.commit()
        try:
            rows = self._collect_source_objects(job, page_size)
            content = self._serialize_rows(job.format, rows)
            artifact = self._build_artifact(job, content)
            completed = job.mark_completed(len(rows), artifact)
            with self._transaction_manager.begin() as unit_of_work:
                self._export_repository.save_export_artifact(completed, content)
                self._export_repository.save_export_job(completed)
                self._audit_repository.append(
                    AuditEvent.record(
                        tenant_id=tenant_id,
                        actor=principal.subject,
                        action="export.job.completed",
                        target_type="export_job",
                        target_id=completed.id.value,
                        metadata={
                            "declared_actor": command.actor,
                            "total_rows": completed.total_rows,
                            "size_bytes": artifact.size_bytes,
                            "sha256": artifact.sha256,
                            "signature_algorithm": artifact.signature_algorithm,
                        },
                    )
                )
                unit_of_work.commit()
            return completed
        except Exception as exc:
            failed = job.mark_failed(str(exc))
            with self._transaction_manager.begin() as unit_of_work:
                self._export_repository.save_export_job(failed)
                self._audit_repository.append(
                    AuditEvent.record(
                        tenant_id=tenant_id,
                        actor=principal.subject,
                        action="export.job.failed",
                        target_type="export_job",
                        target_id=failed.id.value,
                        metadata={"declared_actor": command.actor, "error": failed.error},
                        severity=Severity.ERROR,
                    )
                )
                unit_of_work.commit()
            if isinstance(exc, ValidationError):
                raise
            raise ValidationError("export job failed: " + str(exc)) from exc

    def get_export_job(self, command: GetExportJobCommand) -> ExportJob:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        job = self._export_repository.get_export_job(tenant_id, command.job_id)
        if job is None:
            raise ValidationError("export job not found: " + command.job_id)
        return job

    def get_export_artifact(self, command: GetExportArtifactCommand) -> ExportArtifactDownload:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        job = self._export_repository.get_export_job(tenant_id, command.job_id)
        if job is None:
            raise ValidationError("export job not found: " + command.job_id)
        if job.status is not ExportJobStatus.COMPLETED or job.artifact is None:
            raise ValidationError("export job artifact is not available: " + command.job_id)
        content = self._export_repository.get_export_artifact(tenant_id, command.job_id)
        if content is None:
            raise ValidationError("export artifact content is missing: " + command.job_id)
        digest = hashlib.sha256(content).hexdigest()
        if digest != job.artifact.sha256:
            raise ValidationError("export artifact digest verification failed")
        signature = self._signature(content)
        if not hmac.compare_digest(signature, job.artifact.signature):
            raise ValidationError("export artifact signature verification failed")
        return ExportArtifactDownload(job=job, content=content)

    def _load_runnable_job(self, tenant_id: TenantId, job_id: str | None) -> ExportJob:
        job = (
            self._export_repository.get_export_job(tenant_id, job_id.strip())
            if job_id is not None and job_id.strip()
            else self._export_repository.get_next_queued_export_job(tenant_id)
        )
        if job is None:
            raise ValidationError("export job not found or queue is empty")
        if job.status is not ExportJobStatus.QUEUED:
            raise ValidationError("export job is not queued: " + job.id.value)
        return job

    def _collect_source_objects(self, job: ExportJob, page_size: int) -> list[dict[str, object]]:
        if job.resource is not ExportResource.SOURCE_OBJECTS:
            raise ValidationError("unsupported export resource: " + job.resource.value)
        rows: list[dict[str, object]] = []
        cursor: str | None = None
        while len(rows) < job.filter.limit:
            remaining = job.filter.limit - len(rows)
            page = self._source_repository.list_objects(
                job.tenant_id,
                Pagination.from_values(min(page_size, remaining), cursor),
                kind=job.filter.kind,
                tag=job.filter.tag,
            )
            rows.extend(self._source_object_row(item) for item in page.items)
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        return rows

    def _source_object_row(self, source_object: SourceOfTruthObject) -> dict[str, object]:
        return {
            "key": source_object.key.value,
            "kind": source_object.kind.value,
            "display_name": source_object.display_name,
            "source": source_object.source.value,
            "tags": [tag.value for tag in source_object.tags],
            "version": source_object.version,
            "status": source_object.status.value,
            "created_at": source_object.created_at.isoformat(),
            "updated_at": source_object.updated_at.isoformat(),
            "attributes": source_object.attributes,
        }

    def _serialize_rows(self, export_format: ExportFormat, rows: list[dict[str, object]]) -> bytes:
        if export_format is ExportFormat.CSV:
            return self._serialize_csv(rows)
        if export_format is ExportFormat.JSON:
            return json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        return self._serialize_xlsx(rows)

    def _serialize_csv(self, rows: list[dict[str, object]]) -> bytes:
        columns = self._columns()
        handle = StringIO(newline="")
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(self._flat_row(row))
        return handle.getvalue().encode("utf-8")

    def _serialize_xlsx(self, rows: list[dict[str, object]]) -> bytes:
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._xlsx_content_types())
            archive.writestr("_rels/.rels", self._xlsx_root_relationships())
            archive.writestr("xl/workbook.xml", self._xlsx_workbook())
            archive.writestr("xl/_rels/workbook.xml.rels", self._xlsx_workbook_relationships())
            archive.writestr("xl/worksheets/sheet1.xml", self._xlsx_sheet(rows))
        return output.getvalue()

    def _build_artifact(self, job: ExportJob, content: bytes) -> ExportArtifactMetadata:
        sha256 = hashlib.sha256(content).hexdigest()
        storage_key = f"exports/{job.tenant_id.value}/{job.id.value}.{job.format.extension}"
        filename = f"openinfra-{job.resource.value}-{job.id.value}.{job.format.extension}"
        return ExportArtifactMetadata.create(
            storage_key=storage_key,
            filename=filename,
            media_type=job.format.media_type,
            size_bytes=len(content),
            sha256=sha256,
            signature_algorithm="hmac-sha256",
            signature=self._signature(content),
        )

    def _signature(self, content: bytes) -> str:
        signing_key = self._export_repository.get_or_create_export_signing_secret()
        return hmac.new(signing_key, content, hashlib.sha256).hexdigest()

    def _normalize_page_size(self, value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 500:
            raise ValidationError("export page size must be between 1 and 500")
        return normalized

    def _flat_row(self, row: dict[str, object]) -> dict[str, object]:
        tags = row["tags"]
        if not isinstance(tags, (list, tuple)):
            raise ValidationError("export source object tags are invalid")
        return {
            "key": row["key"],
            "kind": row["kind"],
            "display_name": row["display_name"],
            "source": row["source"],
            "tags": ",".join(str(item) for item in tags),
            "version": row["version"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "attributes_json": json.dumps(row["attributes"], ensure_ascii=False, sort_keys=True),
        }

    def _columns(self) -> list[str]:
        return [
            "key",
            "kind",
            "display_name",
            "source",
            "tags",
            "version",
            "status",
            "created_at",
            "updated_at",
            "attributes_json",
        ]

    def _xlsx_sheet(self, rows: list[dict[str, object]]) -> str:
        xml_rows = [self._xlsx_row(1, self._columns())]
        for index, row in enumerate(rows, start=2):
            flat = self._flat_row(row)
            xml_rows.append(
                self._xlsx_row(index, [str(flat[column]) for column in self._columns()])
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>" + "".join(xml_rows) + "</sheetData></worksheet>"
        )

    def _xlsx_row(self, index: int, values: list[str]) -> str:
        cells = []
        for column_index, value in enumerate(values, start=1):
            reference = self._xlsx_column_name(column_index) + str(index)
            cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        return f'<row r="{index}">' + "".join(cells) + "</row>"

    def _xlsx_column_name(self, index: int) -> str:
        name = ""
        current = index
        while current:
            current, remainder = divmod(current - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def _xlsx_content_types(self) -> str:
        rels_type = "application/vnd.openxmlformats-package.relationships+xml"
        workbook_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
        worksheet_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            f'<Default Extension="rels" ContentType="{rels_type}"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{workbook_type}"/>'
            f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{worksheet_type}"/>'
            "</Types>"
        )

    def _xlsx_root_relationships(self) -> str:
        relationship_type = (
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{relationship_type}" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _xlsx_workbook(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="source_objects" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>"
        )

    def _xlsx_workbook_relationships(self) -> str:
        relationship_type = (
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{relationship_type}" Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        )
