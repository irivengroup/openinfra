from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceObjectKind, SourceSystem


class ImportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().lstrip(".")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("import format must be csv, json or xlsx") from exc


class ImportJobStatus(StrEnum):
    QUEUED = "queued"
    VALIDATED = "validated"
    APPLIED = "applied"
    FAILED = "failed"


class LegacyMigrationSource(StrEnum):
    DEVICE42 = "device42"
    NETBOX = "netbox"
    NAUTOBOT = "nautobot"
    GLPI = "glpi"
    CSV = "csv"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "device-42": "device42",
            "generic-csv": "csv",
            "generic": "csv",
        }
        normalized = aliases.get(normalized, normalized)
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(
                "migration source must be device42, netbox, nautobot, glpi or csv"
            ) from exc


@dataclass(frozen=True, slots=True)
class MigrationGap:
    category: str
    field: str
    severity: Severity
    message: str

    @classmethod
    def create(
        cls,
        category: str,
        field: str,
        message: str,
        severity: Severity = Severity.WARNING,
    ) -> Self:
        normalized_category = category.strip().lower().replace("_", "-")
        if normalized_category not in {"missing-required", "unmapped-source", "mapping-warning"}:
            raise ValidationError("migration gap category is invalid")
        normalized_field = field.strip()
        normalized_message = " ".join(message.strip().split())
        if not normalized_field:
            raise ValidationError("migration gap field is mandatory")
        if not normalized_message:
            raise ValidationError("migration gap message is mandatory")
        return cls(
            category=normalized_category,
            field=normalized_field,
            severity=severity,
            message=normalized_message,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "field": self.field,
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class MigrationTemplate:
    source: LegacyMigrationSource
    name: str
    version: str
    mapping: ImportMapping
    required_columns: tuple[str, ...]
    recommended_columns: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def create(
        cls,
        source: LegacyMigrationSource,
        name: str,
        version: str,
        mapping: ImportMapping,
        required_columns: tuple[str, ...],
        recommended_columns: tuple[str, ...] = (),
        notes: tuple[str, ...] = (),
    ) -> Self:
        normalized_name = " ".join(name.strip().split())
        normalized_version = version.strip()
        if not normalized_name:
            raise ValidationError("migration template name is mandatory")
        if not normalized_version:
            raise ValidationError("migration template version is mandatory")
        normalized_required = tuple(
            dict.fromkeys(column.strip() for column in required_columns if column.strip())
        )
        if not normalized_required:
            raise ValidationError("migration template requires at least one source column")
        normalized_recommended = tuple(
            dict.fromkeys(column.strip() for column in recommended_columns if column.strip())
        )
        normalized_notes = tuple(" ".join(note.strip().split()) for note in notes if note.strip())
        return cls(
            source=source,
            name=normalized_name,
            version=normalized_version,
            mapping=mapping,
            required_columns=normalized_required,
            recommended_columns=normalized_recommended,
            notes=normalized_notes,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "name": self.name,
            "version": self.version,
            "mapping": self.mapping.as_dict(),
            "required_columns": list(self.required_columns),
            "recommended_columns": list(self.recommended_columns),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class BulkImportProgress:
    job_id: EntityId
    tenant_id: TenantId
    status: ImportJobStatus
    next_row_number: int
    processed_rows: int
    valid_rows: int
    invalid_rows: int
    create_count: int
    update_count: int
    batches_completed: int
    resumable: bool
    final_report_available: bool

    @classmethod
    def create(
        cls,
        checkpoint: BulkImportCheckpoint,
        report: BulkImportReport | None = None,
    ) -> Self:
        processed_rows = max(0, checkpoint.next_row_number - 1)
        if checkpoint.total_rows > processed_rows:
            processed_rows = checkpoint.total_rows
        final_report_available = report is not None
        if report is not None:
            if report.job_id != checkpoint.job_id:
                raise ValidationError("bulk import progress report job mismatch")
            if report.tenant_id != checkpoint.tenant_id:
                raise ValidationError("bulk import progress report tenant mismatch")
            processed_rows = report.total_rows
        return cls(
            job_id=checkpoint.job_id,
            tenant_id=checkpoint.tenant_id,
            status=checkpoint.status,
            next_row_number=checkpoint.next_row_number,
            processed_rows=processed_rows,
            valid_rows=checkpoint.valid_rows,
            invalid_rows=checkpoint.invalid_rows,
            create_count=checkpoint.create_count,
            update_count=checkpoint.update_count,
            batches_completed=checkpoint.batches_completed,
            resumable=checkpoint.status is not ImportJobStatus.APPLIED,
            final_report_available=final_report_available,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id.value,
            "tenant_id": self.tenant_id.value,
            "status": self.status.value,
            "next_row_number": self.next_row_number,
            "processed_rows": self.processed_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "create_count": self.create_count,
            "update_count": self.update_count,
            "batches_completed": self.batches_completed,
            "resumable": self.resumable,
            "final_report_available": self.final_report_available,
        }


@dataclass(frozen=True, slots=True)
class MigrationPlanReport:
    job_id: EntityId
    tenant_id: TenantId
    source: LegacyMigrationSource
    format: ImportFormat
    status: ImportJobStatus
    template: MigrationTemplate
    total_rows: int
    valid_rows: int
    invalid_rows: int
    create_count: int
    update_count: int
    gaps: tuple[MigrationGap, ...]
    import_report: ImportReport
    resume_strategy: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        source: LegacyMigrationSource,
        import_format: ImportFormat,
        template: MigrationTemplate,
        gaps: tuple[MigrationGap, ...],
        import_report: ImportReport,
        resume_strategy: str,
        job_id: EntityId | None = None,
    ) -> Self:
        normalized_resume = " ".join(resume_strategy.strip().split())
        if not normalized_resume:
            raise ValidationError("migration resume strategy is mandatory")
        if import_report.tenant_id != tenant_id:
            raise ValidationError("migration plan import report tenant mismatch")
        if import_report.format != import_format:
            raise ValidationError("migration plan import report format mismatch")
        if not import_report.dry_run:
            raise ValidationError("migration plan must be based on a dry-run import report")
        blocking_gaps = any(gap.severity == Severity.ERROR for gap in gaps)
        status = (
            ImportJobStatus.FAILED
            if blocking_gaps or import_report.invalid_rows
            else ImportJobStatus.VALIDATED
        )
        return cls(
            job_id=job_id or EntityId.new(),
            tenant_id=tenant_id,
            source=source,
            format=import_format,
            status=status,
            template=template,
            total_rows=import_report.total_rows,
            valid_rows=import_report.valid_rows,
            invalid_rows=import_report.invalid_rows,
            create_count=sum(1 for impact in import_report.impacts if impact.action == "create"),
            update_count=sum(1 for impact in import_report.impacts if impact.action == "update"),
            gaps=gaps,
            import_report=import_report,
            resume_strategy=normalized_resume,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id.value,
            "tenant_id": self.tenant_id.value,
            "source": self.source.value,
            "format": self.format.value,
            "status": self.status.value,
            "template": self.template.as_dict(),
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "create_count": self.create_count,
            "update_count": self.update_count,
            "gaps": [gap.as_dict() for gap in self.gaps],
            "import_report": self.import_report.as_dict(),
            "resume_strategy": self.resume_strategy,
        }


@dataclass(frozen=True, slots=True)
class ImportFieldMapping:
    target_field: str
    source_field: str

    @classmethod
    def create(cls, target_field: str, source_field: str) -> Self:
        normalized_target = target_field.strip()
        normalized_source = source_field.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", normalized_target):
            raise ValidationError("import target field is invalid")
        if not normalized_source:
            raise ValidationError("import source field cannot be empty")
        return cls(target_field=normalized_target, source_field=normalized_source)

    def as_dict(self) -> dict[str, str]:
        return {"target_field": self.target_field, "source_field": self.source_field}


@dataclass(frozen=True, slots=True)
class ImportMapping:
    fields: tuple[ImportFieldMapping, ...]

    @classmethod
    def from_json(cls, value: str) -> Self:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError("import mapping must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValidationError("import mapping must be a JSON object")
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        fields = tuple(
            ImportFieldMapping.create(str(target), str(source))
            for target, source in sorted(payload.items())
        )
        targets = {field.target_field for field in fields}
        for required in ("key", "kind", "display_name", "source"):
            if required not in targets:
                raise ValidationError("import mapping requires target field: " + required)
        return cls(fields=fields)

    def source_fields(self) -> tuple[str, ...]:
        return tuple(field.source_field for field in self.fields)

    def as_dict(self) -> dict[str, str]:
        return {field.target_field: field.source_field for field in self.fields}


@dataclass(frozen=True, slots=True)
class ImportRowIssue:
    row_number: int
    field: str
    severity: Severity
    message: str

    @classmethod
    def create(
        cls,
        row_number: int,
        field: str,
        message: str,
        severity: Severity = Severity.ERROR,
    ) -> Self:
        if row_number < 1:
            raise ValidationError("import issue row number must be positive")
        normalized_field = field.strip() or "row"
        normalized_message = " ".join(message.strip().split())
        if not normalized_message:
            raise ValidationError("import issue message is mandatory")
        return cls(
            row_number=row_number,
            field=normalized_field,
            severity=severity,
            message=normalized_message,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "row_number": self.row_number,
            "field": self.field,
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ImportRowImpact:
    row_number: int
    action: str
    object_key: str
    object_kind: str

    @classmethod
    def create(cls, row_number: int, action: str, object_key: str, object_kind: str) -> Self:
        normalized_action = action.strip().lower()
        if normalized_action not in {"create", "update"}:
            raise ValidationError("import impact action must be create or update")
        try:
            SourceObjectKind(object_kind.strip().lower())
        except ValueError as exc:
            raise ValidationError("import impact object kind is invalid") from exc
        if row_number < 1:
            raise ValidationError("import impact row number must be positive")
        if not object_key.strip():
            raise ValidationError("import impact object key is mandatory")
        return cls(
            row_number=row_number,
            action=normalized_action,
            object_key=object_key.strip().lower(),
            object_kind=object_kind.strip().lower(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "row_number": self.row_number,
            "action": self.action,
            "object_key": self.object_key,
            "object_kind": self.object_kind,
        }


@dataclass(frozen=True, slots=True)
class ImportCandidate:
    row_number: int
    key: str
    kind: str
    display_name: str
    source: str
    tags: tuple[str, ...]
    attributes: dict[str, object]

    @classmethod
    def create(
        cls,
        row_number: int,
        key: str,
        kind: str,
        display_name: str,
        source: str,
        tags: tuple[str, ...],
        attributes: dict[str, object],
    ) -> Self:
        try:
            SourceObjectKind(kind.strip().lower())
        except ValueError as exc:
            raise ValidationError("import candidate object kind is invalid") from exc
        SourceSystem.from_value(source)
        json.dumps(attributes, sort_keys=True)
        if row_number < 1:
            raise ValidationError("import candidate row number must be positive")
        return cls(
            row_number=row_number,
            key=key.strip().lower(),
            kind=kind.strip().lower(),
            display_name=" ".join(display_name.strip().split()),
            source=source.strip().lower(),
            tags=tuple(tag.strip().lower() for tag in tags if tag.strip()),
            attributes=dict(attributes),
        )


@dataclass(frozen=True, slots=True)
class ImportReport:
    job_id: EntityId
    tenant_id: TenantId
    format: ImportFormat
    dry_run: bool
    status: ImportJobStatus
    total_rows: int
    valid_rows: int
    invalid_rows: int
    mapping: ImportMapping
    impacts: tuple[ImportRowImpact, ...]
    dlq: tuple[ImportRowIssue, ...]

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        import_format: ImportFormat,
        dry_run: bool,
        mapping: ImportMapping,
        total_rows: int,
        impacts: tuple[ImportRowImpact, ...],
        dlq: tuple[ImportRowIssue, ...],
        status: ImportJobStatus,
        job_id: EntityId | None = None,
    ) -> Self:
        if total_rows < 0:
            raise ValidationError("import total rows cannot be negative")
        invalid_rows = len({issue.row_number for issue in dlq if issue.severity == Severity.ERROR})
        valid_rows = total_rows - invalid_rows
        if valid_rows < 0:
            raise ValidationError("import invalid row count exceeds total rows")
        if status in {ImportJobStatus.VALIDATED, ImportJobStatus.APPLIED} and invalid_rows:
            raise ValidationError("validated or applied imports cannot contain invalid rows")
        return cls(
            job_id=job_id or EntityId.new(),
            tenant_id=tenant_id,
            format=import_format,
            dry_run=bool(dry_run),
            status=status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            mapping=mapping,
            impacts=impacts,
            dlq=dlq,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id.value,
            "tenant_id": self.tenant_id.value,
            "format": self.format.value,
            "dry_run": self.dry_run,
            "status": self.status.value,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "create_count": sum(1 for impact in self.impacts if impact.action == "create"),
            "update_count": sum(1 for impact in self.impacts if impact.action == "update"),
            "mapping": self.mapping.as_dict(),
            "impacts": [impact.as_dict() for impact in self.impacts],
            "dlq": [issue.as_dict() for issue in self.dlq],
        }


@dataclass(frozen=True, slots=True)
class BulkImportCheckpoint:
    job_id: EntityId
    tenant_id: TenantId
    next_row_number: int
    total_rows: int
    valid_rows: int
    invalid_rows: int
    create_count: int
    update_count: int
    batches_completed: int
    status: ImportJobStatus

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        next_row_number: int,
        total_rows: int,
        valid_rows: int,
        invalid_rows: int,
        create_count: int,
        update_count: int,
        batches_completed: int,
        status: ImportJobStatus,
        job_id: EntityId | None = None,
    ) -> Self:
        if next_row_number < 1:
            raise ValidationError("bulk import checkpoint next row must be positive")
        for field_name, value in (
            ("total rows", total_rows),
            ("valid rows", valid_rows),
            ("invalid rows", invalid_rows),
            ("create count", create_count),
            ("update count", update_count),
            ("batches completed", batches_completed),
        ):
            if value < 0:
                raise ValidationError(
                    "bulk import checkpoint " + field_name + " cannot be negative"
                )
        if valid_rows + invalid_rows != total_rows:
            raise ValidationError("bulk import checkpoint row counters are inconsistent")
        if create_count + update_count > valid_rows:
            raise ValidationError("bulk import checkpoint impact counters exceed valid rows")
        return cls(
            job_id=job_id or EntityId.new(),
            tenant_id=tenant_id,
            next_row_number=next_row_number,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            create_count=create_count,
            update_count=update_count,
            batches_completed=batches_completed,
            status=status,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id.value,
            "tenant_id": self.tenant_id.value,
            "next_row_number": self.next_row_number,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "create_count": self.create_count,
            "update_count": self.update_count,
            "batches_completed": self.batches_completed,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class BulkImportMetrics:
    batch_size: int
    checkpoint_interval: int
    batches_completed: int
    copy_strategy: str
    resumed_from_row: int | None = None

    @classmethod
    def create(
        cls,
        batch_size: int,
        checkpoint_interval: int,
        batches_completed: int,
        copy_strategy: str,
        resumed_from_row: int | None = None,
    ) -> Self:
        if not 1 <= batch_size <= 100_000:
            raise ValidationError("bulk import batch size must be between 1 and 100000")
        if not 1 <= checkpoint_interval <= 1_000_000:
            raise ValidationError("bulk import checkpoint interval must be between 1 and 1000000")
        if batches_completed < 0:
            raise ValidationError("bulk import batches completed cannot be negative")
        normalized_strategy = " ".join(copy_strategy.strip().split())
        if not normalized_strategy:
            raise ValidationError("bulk import copy strategy is mandatory")
        if resumed_from_row is not None and resumed_from_row < 1:
            raise ValidationError("bulk import resumed row must be positive")
        return cls(
            batch_size=batch_size,
            checkpoint_interval=checkpoint_interval,
            batches_completed=batches_completed,
            copy_strategy=normalized_strategy,
            resumed_from_row=resumed_from_row,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_size": self.batch_size,
            "checkpoint_interval": self.checkpoint_interval,
            "batches_completed": self.batches_completed,
            "copy_strategy": self.copy_strategy,
            "resumed_from_row": self.resumed_from_row,
        }


@dataclass(frozen=True, slots=True)
class BulkImportReport:
    job_id: EntityId
    tenant_id: TenantId
    format: ImportFormat
    dry_run: bool
    status: ImportJobStatus
    total_rows: int
    valid_rows: int
    invalid_rows: int
    create_count: int
    update_count: int
    mapping: ImportMapping
    metrics: BulkImportMetrics
    checkpoint: BulkImportCheckpoint
    impact_sample: tuple[ImportRowImpact, ...]
    dlq_sample: tuple[ImportRowIssue, ...]

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        import_format: ImportFormat,
        dry_run: bool,
        status: ImportJobStatus,
        total_rows: int,
        valid_rows: int,
        invalid_rows: int,
        create_count: int,
        update_count: int,
        mapping: ImportMapping,
        metrics: BulkImportMetrics,
        checkpoint: BulkImportCheckpoint,
        impact_sample: tuple[ImportRowImpact, ...],
        dlq_sample: tuple[ImportRowIssue, ...],
        job_id: EntityId | None = None,
    ) -> Self:
        for field_name, value in (
            ("total rows", total_rows),
            ("valid rows", valid_rows),
            ("invalid rows", invalid_rows),
            ("create count", create_count),
            ("update count", update_count),
        ):
            if value < 0:
                raise ValidationError("bulk import " + field_name + " cannot be negative")
        if valid_rows + invalid_rows != total_rows:
            raise ValidationError("bulk import row counters are inconsistent")
        if create_count + update_count > valid_rows:
            raise ValidationError("bulk import impact counters exceed valid rows")
        resolved_job_id = job_id or checkpoint.job_id
        if checkpoint.job_id != resolved_job_id:
            raise ValidationError("bulk import report checkpoint job mismatch")
        if checkpoint.tenant_id != tenant_id:
            raise ValidationError("bulk import report checkpoint tenant mismatch")
        return cls(
            job_id=resolved_job_id,
            tenant_id=tenant_id,
            format=import_format,
            dry_run=bool(dry_run),
            status=status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            create_count=create_count,
            update_count=update_count,
            mapping=mapping,
            metrics=metrics,
            checkpoint=checkpoint,
            impact_sample=impact_sample,
            dlq_sample=dlq_sample,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id.value,
            "tenant_id": self.tenant_id.value,
            "format": self.format.value,
            "dry_run": self.dry_run,
            "status": self.status.value,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "create_count": self.create_count,
            "update_count": self.update_count,
            "mapping": self.mapping.as_dict(),
            "metrics": self.metrics.as_dict(),
            "checkpoint": self.checkpoint.as_dict(),
            "impact_sample": [impact.as_dict() for impact in self.impact_sample],
            "dlq_sample": [issue.as_dict() for issue in self.dlq_sample],
        }
