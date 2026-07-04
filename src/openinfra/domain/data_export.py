from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import EntityId, TenantId, ValidationError


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().lstrip(".")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("export format must be csv, json or xlsx") from exc

    @property
    def media_type(self) -> str:
        if self is ExportFormat.CSV:
            return "text/csv; charset=utf-8"
        if self is ExportFormat.JSON:
            return "application/json; charset=utf-8"
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @property
    def extension(self) -> str:
        return self.value


class ExportJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportResource(StrEnum):
    SOURCE_OBJECTS = "source_objects"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("-", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("export resource must be source_objects") from exc


@dataclass(frozen=True, slots=True)
class ExportFilter:
    kind: str | None = None
    tag: str | None = None
    limit: int = 100_000

    @classmethod
    def create(cls, kind: str | None = None, tag: str | None = None, limit: int = 100_000) -> Self:
        normalized_kind = kind.strip().lower() if kind else None
        normalized_tag = tag.strip().lower() if tag else None
        if normalized_kind is not None and not re.fullmatch(
            r"[a-z][a-z0-9_-]{1,63}", normalized_kind
        ):
            raise ValidationError("export kind filter is invalid")
        if normalized_tag is not None and not re.fullmatch(
            r"[a-z0-9][a-z0-9_.:-]{0,63}", normalized_tag
        ):
            raise ValidationError("export tag filter is invalid")
        normalized_limit = int(limit)
        if not 1 <= normalized_limit <= 1_000_000:
            raise ValidationError("export limit must be between 1 and 1000000")
        return cls(kind=normalized_kind, tag=normalized_tag, limit=normalized_limit)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        return cls.create(
            None if value.get("kind") is None else str(value["kind"]),
            None if value.get("tag") is None else str(value["tag"]),
            int(str(value.get("limit", 100_000))),
        )

    def as_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "tag": self.tag, "limit": self.limit}


@dataclass(frozen=True, slots=True)
class ExportArtifactMetadata:
    storage_key: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    signature_algorithm: str
    signature: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        storage_key: str,
        filename: str,
        media_type: str,
        size_bytes: int,
        sha256: str,
        signature_algorithm: str,
        signature: str,
        created_at: datetime | None = None,
    ) -> Self:
        normalized_storage_key = storage_key.strip()
        normalized_filename = filename.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_./:-]{2,255}", normalized_storage_key):
            raise ValidationError("export storage key is invalid")
        if ".." in normalized_storage_key or "//" in normalized_storage_key:
            raise ValidationError("export storage key is unsafe")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,127}", normalized_filename):
            raise ValidationError("export filename is invalid")
        if size_bytes < 0:
            raise ValidationError("export artifact size cannot be negative")
        if not re.fullmatch(r"[a-f0-9]{64}", sha256):
            raise ValidationError("export artifact sha256 is invalid")
        if not re.fullmatch(r"[a-f0-9]{64}", signature):
            raise ValidationError("export artifact signature is invalid")
        if signature_algorithm != "hmac-sha256":
            raise ValidationError("export signature algorithm must be hmac-sha256")
        created = created_at or datetime.now(UTC)
        if created.tzinfo is None:
            raise ValidationError("export artifact created_at must be timezone-aware")
        return cls(
            storage_key=normalized_storage_key,
            filename=normalized_filename,
            media_type=" ".join(media_type.strip().split()),
            size_bytes=size_bytes,
            sha256=sha256,
            signature_algorithm=signature_algorithm,
            signature=signature,
            created_at=created.astimezone(UTC),
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        return cls.create(
            storage_key=str(value["storage_key"]),
            filename=str(value["filename"]),
            media_type=str(value["media_type"]),
            size_bytes=int(str(value["size_bytes"])),
            sha256=str(value["sha256"]),
            signature_algorithm=str(value["signature_algorithm"]),
            signature=str(value["signature"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "storage_key": self.storage_key,
            "filename": self.filename,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "signature_algorithm": self.signature_algorithm,
            "signature": self.signature,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ExportJob:
    id: EntityId
    tenant_id: TenantId
    resource: ExportResource
    format: ExportFormat
    status: ExportJobStatus
    filter: ExportFilter
    requested_by: str
    total_rows: int
    artifact: ExportArtifactMetadata | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        resource: ExportResource,
        export_format: ExportFormat,
        export_filter: ExportFilter,
        requested_by: str,
        status: ExportJobStatus = ExportJobStatus.QUEUED,
        total_rows: int = 0,
        artifact: ExportArtifactMetadata | None = None,
        error: str | None = None,
        job_id: EntityId | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> Self:
        actor = " ".join(requested_by.strip().split())
        if not actor:
            raise ValidationError("export requested_by is mandatory")
        if total_rows < 0:
            raise ValidationError("export total rows cannot be negative")
        if status is ExportJobStatus.COMPLETED and artifact is None:
            raise ValidationError("completed export requires an artifact")
        if status is ExportJobStatus.FAILED and not error:
            raise ValidationError("failed export requires an error")
        created = created_at or datetime.now(UTC)
        updated = updated_at or created
        if created.tzinfo is None or updated.tzinfo is None:
            raise ValidationError("export timestamps must be timezone-aware")
        if updated < created:
            raise ValidationError("export updated_at cannot be before created_at")
        normalized_error = None if error is None else " ".join(error.strip().split())[:1024]
        return cls(
            id=job_id or EntityId.new(),
            tenant_id=tenant_id,
            resource=resource,
            format=export_format,
            status=status,
            filter=export_filter,
            requested_by=actor,
            total_rows=total_rows,
            artifact=artifact,
            error=normalized_error,
            created_at=created.astimezone(UTC),
            updated_at=updated.astimezone(UTC),
        )

    def mark_running(self) -> Self:
        return self._copy(status=ExportJobStatus.RUNNING, artifact=None, error=None)

    def mark_completed(self, total_rows: int, artifact: ExportArtifactMetadata) -> Self:
        return self._copy(
            status=ExportJobStatus.COMPLETED,
            total_rows=total_rows,
            artifact=artifact,
            error=None,
        )

    def mark_failed(self, error: str) -> Self:
        return self._copy(status=ExportJobStatus.FAILED, artifact=None, error=error)

    def _copy(
        self,
        status: ExportJobStatus,
        total_rows: int | None = None,
        artifact: ExportArtifactMetadata | None = None,
        error: str | None = None,
    ) -> Self:
        return self.create(
            tenant_id=self.tenant_id,
            resource=self.resource,
            export_format=self.format,
            export_filter=self.filter,
            requested_by=self.requested_by,
            status=status,
            total_rows=self.total_rows if total_rows is None else total_rows,
            artifact=artifact,
            error=error,
            job_id=self.id,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        artifact_payload = value.get("artifact")
        artifact = (
            ExportArtifactMetadata.from_dict(artifact_payload)
            if isinstance(artifact_payload, dict)
            else None
        )
        filter_payload = value.get("filter", {})
        if not isinstance(filter_payload, dict):
            raise ValidationError("stored export filter is invalid")
        return cls.create(
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            resource=ExportResource.from_value(str(value["resource"])),
            export_format=ExportFormat.from_value(str(value["format"])),
            export_filter=ExportFilter.from_dict(filter_payload),
            requested_by=str(value["requested_by"]),
            status=ExportJobStatus(str(value["status"])),
            total_rows=int(str(value.get("total_rows", 0))),
            artifact=artifact,
            error=None if value.get("error") is None else str(value["error"]),
            job_id=EntityId.from_value(str(value.get("id", value.get("job_id")))),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "resource": self.resource.value,
            "format": self.format.value,
            "status": self.status.value,
            "filter": self.filter.as_dict(),
            "requested_by": self.requested_by,
            "total_rows": self.total_rows,
            "artifact": None if self.artifact is None else self.artifact.as_dict(),
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
