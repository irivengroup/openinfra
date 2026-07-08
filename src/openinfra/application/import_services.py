from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openinfra.application.ports import (
    AuditRepository,
    ImportRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, EntityId, Severity, TenantId, ValidationError
from openinfra.domain.data_import import (
    BulkImportCheckpoint,
    BulkImportMetrics,
    BulkImportProgress,
    BulkImportReport,
    ImportCandidate,
    ImportFormat,
    ImportJobStatus,
    ImportMapping,
    ImportReport,
    ImportRowImpact,
    ImportRowIssue,
    LegacyMigrationSource,
    MigrationGap,
    MigrationPlanReport,
    MigrationTemplate,
)
from openinfra.domain.security import Permission


class DatasetParser(Protocol):
    def parse(self, _path: Path, _import_format: ImportFormat) -> tuple[dict[str, str], ...]:
        raise TypeError("adapter contract invoked directly")

    def iter_rows(self, _path: Path, _import_format: ImportFormat) -> Iterator[dict[str, str]]:
        raise TypeError("adapter contract invoked directly")


@dataclass(frozen=True, slots=True)
class ImportDatasetCommand:
    tenant_id: str
    actor: str
    admin_token: str
    file_path: Path
    format: str
    mapping_json: str
    dry_run: bool = True
    batch_size: int = 500


@dataclass(frozen=True, slots=True)
class BulkImportDatasetCommand:
    tenant_id: str
    actor: str
    admin_token: str
    file_path: Path
    format: str
    mapping_json: str
    dry_run: bool = True
    batch_size: int = 5_000
    checkpoint_interval: int = 25_000
    resume_job_id: str | None = None
    sample_limit: int = 100


@dataclass(frozen=True, slots=True)
class MigrationTemplateCommand:
    source: str


@dataclass(frozen=True, slots=True)
class PlanMigrationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    source: str
    file_path: Path
    format: str
    sample_limit: int = 100


class GenericImportService:
    _MAX_ROWS = 1_000_000

    def __init__(
        self,
        import_repository: ImportRepository,
        source_of_truth_repository: SourceOfTruthRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        parser: DatasetParser,
    ) -> None:
        self._import_repository = import_repository
        self._source_repository = source_of_truth_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._parser = parser

    def get_migration_template(self, command: MigrationTemplateCommand) -> MigrationTemplate:
        return self._migration_template(LegacyMigrationSource.from_value(command.source))

    def plan_migration(self, command: PlanMigrationCommand) -> MigrationPlanReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_WRITE)
        )
        source = LegacyMigrationSource.from_value(command.source)
        import_format = ImportFormat.from_value(command.format)
        sample_limit = self._normalize_sample_limit(command.sample_limit)
        base_template = self._migration_template(source)
        rows = self._parser.parse(command.file_path, import_format)
        if len(rows) > self._MAX_ROWS:
            raise ValidationError("migration dataset exceeds 1,000,000 rows")
        gaps = self._migration_gaps(rows, base_template)
        template = self._effective_migration_template(base_template, rows)
        candidates, issues = self._build_candidates(rows, template.mapping)
        impacts = self._build_impacts(tenant_id, candidates)
        if sample_limit:
            impacts = impacts[:sample_limit]
            issues = issues[:sample_limit]
        import_report = ImportReport.create(
            tenant_id=tenant_id,
            import_format=import_format,
            dry_run=True,
            mapping=template.mapping,
            total_rows=len(rows),
            impacts=impacts,
            dlq=issues,
            status=ImportJobStatus.FAILED if issues else ImportJobStatus.VALIDATED,
        )
        report = MigrationPlanReport.create(
            tenant_id=tenant_id,
            source=source,
            import_format=import_format,
            template=template,
            gaps=gaps,
            import_report=import_report,
            resume_strategy=(
                "Run import bulk-dataset with the returned mapping, persist checkpoints, "
                "fix blocking gaps first, then resume with --resume-job-id when interrupted."
            ),
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._import_repository.save_migration_plan_report(report)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="import.migration_plan." + report.status.value,
                    target_type="migration_plan",
                    target_id=report.job_id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "source": source.value,
                        "format": import_format.value,
                        "total_rows": report.total_rows,
                        "valid_rows": report.valid_rows,
                        "invalid_rows": report.invalid_rows,
                        "gap_count": len(report.gaps),
                    },
                    severity=Severity.ERROR
                    if report.status == ImportJobStatus.FAILED
                    else Severity.INFO,
                )
            )
            unit_of_work.commit()
        return report

    def get_migration_plan(self, tenant_id: str, job_id: str) -> MigrationPlanReport:
        normalized_tenant = TenantId.from_value(tenant_id)
        report = self._import_repository.get_migration_plan_report(normalized_tenant, job_id)
        if report is None:
            raise ValidationError("migration plan not found: " + job_id)
        return report

    def import_dataset(self, command: ImportDatasetCommand) -> ImportReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_WRITE)
        )
        import_format = ImportFormat.from_value(command.format)
        mapping = ImportMapping.from_json(command.mapping_json)
        batch_size = self._normalize_batch_size(command.batch_size)
        rows = self._parser.parse(command.file_path, import_format)
        if len(rows) > self._MAX_ROWS:
            raise ValidationError("import dataset exceeds 1,000,000 rows")
        candidates, issues = self._build_candidates(rows, mapping)
        impacts = self._build_impacts(tenant_id, candidates)
        status = self._status_for(command.dry_run, issues)
        report = ImportReport.create(
            tenant_id=tenant_id,
            import_format=import_format,
            dry_run=command.dry_run,
            mapping=mapping,
            total_rows=len(rows),
            impacts=impacts,
            dlq=issues,
            status=status,
        )
        with self._transaction_manager.begin() as unit_of_work:
            if not command.dry_run and not issues:
                self._apply_candidates(tenant_id, command.actor, candidates, batch_size)
            self._import_repository.save_import_report(report)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="import.dataset." + status.value,
                    target_type="import_job",
                    target_id=report.job_id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "format": import_format.value,
                        "dry_run": command.dry_run,
                        "total_rows": report.total_rows,
                        "valid_rows": report.valid_rows,
                        "invalid_rows": report.invalid_rows,
                    },
                    severity=Severity.ERROR if issues else Severity.INFO,
                )
            )
            unit_of_work.commit()
        return report

    def bulk_import_dataset(self, command: BulkImportDatasetCommand) -> BulkImportReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_WRITE)
        )
        import_format = ImportFormat.from_value(command.format)
        mapping = ImportMapping.from_json(command.mapping_json)
        batch_size = self._normalize_bulk_batch_size(command.batch_size)
        checkpoint_interval = self._normalize_checkpoint_interval(command.checkpoint_interval)
        sample_limit = self._normalize_sample_limit(command.sample_limit)
        start_checkpoint = self._resume_checkpoint(tenant_id, command.resume_job_id)
        job_id = start_checkpoint.job_id if start_checkpoint else EntityId.new()
        resumed_from_row = start_checkpoint.next_row_number if start_checkpoint else None
        counters = {
            "total_rows": start_checkpoint.total_rows if start_checkpoint else 0,
            "valid_rows": start_checkpoint.valid_rows if start_checkpoint else 0,
            "invalid_rows": start_checkpoint.invalid_rows if start_checkpoint else 0,
            "create_count": start_checkpoint.create_count if start_checkpoint else 0,
            "update_count": start_checkpoint.update_count if start_checkpoint else 0,
            "batches_completed": start_checkpoint.batches_completed if start_checkpoint else 0,
        }
        next_row_number = start_checkpoint.next_row_number if start_checkpoint else 1
        candidate_batch: list[ImportCandidate] = []
        impact_sample: list[ImportRowImpact] = []
        dlq_sample: list[ImportRowIssue] = []
        last_checkpoint_row = next_row_number - 1
        for row_number, row in self._iter_rows(command.file_path, import_format):
            if row_number < next_row_number:
                continue
            counters["total_rows"] += 1
            candidate, row_issues = self._candidate_from_row(row_number, row, mapping)
            if row_issues:
                counters["invalid_rows"] += 1
                self._extend_sample(dlq_sample, row_issues, sample_limit)
            elif candidate is not None:
                counters["valid_rows"] += 1
                impact = self._impact_for_candidate(tenant_id, candidate)
                if impact.action == "create":
                    counters["create_count"] += 1
                else:
                    counters["update_count"] += 1
                self._append_sample(impact_sample, impact, sample_limit)
                candidate_batch.append(candidate)
            if len(candidate_batch) >= batch_size:
                counters["batches_completed"] += 1
                self._flush_bulk_batch(
                    tenant_id,
                    command.actor,
                    command.dry_run,
                    job_id,
                    row_number + 1,
                    candidate_batch,
                    counters,
                )
                candidate_batch.clear()
                last_checkpoint_row = row_number
            elif row_number - last_checkpoint_row >= checkpoint_interval:
                self._save_bulk_checkpoint(
                    tenant_id,
                    job_id,
                    row_number + 1,
                    counters,
                    self._bulk_status(command.dry_run, counters["invalid_rows"]),
                )
                last_checkpoint_row = row_number
        if candidate_batch:
            counters["batches_completed"] += 1
            self._flush_bulk_batch(
                tenant_id,
                command.actor,
                command.dry_run,
                job_id,
                counters["total_rows"] + 1,
                candidate_batch,
                counters,
            )
        status = self._bulk_status(command.dry_run, counters["invalid_rows"])
        checkpoint = self._save_bulk_checkpoint(
            tenant_id,
            job_id,
            counters["total_rows"] + 1,
            counters,
            status,
        )
        metrics = BulkImportMetrics.create(
            batch_size=batch_size,
            checkpoint_interval=checkpoint_interval,
            batches_completed=counters["batches_completed"],
            copy_strategy=self._import_repository.bulk_import_strategy_name(),
            resumed_from_row=resumed_from_row,
        )
        report = BulkImportReport.create(
            tenant_id=tenant_id,
            import_format=import_format,
            dry_run=command.dry_run,
            status=status,
            total_rows=counters["total_rows"],
            valid_rows=counters["valid_rows"],
            invalid_rows=counters["invalid_rows"],
            create_count=counters["create_count"],
            update_count=counters["update_count"],
            mapping=mapping,
            metrics=metrics,
            checkpoint=checkpoint,
            impact_sample=tuple(impact_sample),
            dlq_sample=tuple(dlq_sample),
            job_id=job_id,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._import_repository.save_bulk_import_report(report)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="import.bulk_dataset." + status.value,
                    target_type="bulk_import_job",
                    target_id=report.job_id.value,
                    metadata={
                        "declared_actor": command.actor,
                        "format": import_format.value,
                        "dry_run": command.dry_run,
                        "total_rows": report.total_rows,
                        "valid_rows": report.valid_rows,
                        "invalid_rows": report.invalid_rows,
                        "batches_completed": report.metrics.batches_completed,
                    },
                    severity=Severity.ERROR if report.invalid_rows else Severity.INFO,
                )
            )
            unit_of_work.commit()
        return report

    def get_bulk_report(self, tenant_id: str, job_id: str) -> BulkImportReport:
        normalized_tenant = TenantId.from_value(tenant_id)
        report = self._import_repository.get_bulk_import_report(normalized_tenant, job_id)
        if report is None:
            raise ValidationError("bulk import job not found: " + job_id)
        return report

    def get_bulk_checkpoint(self, tenant_id: str, job_id: str) -> BulkImportCheckpoint:
        normalized_tenant = TenantId.from_value(tenant_id)
        checkpoint = self._import_repository.get_bulk_import_checkpoint(normalized_tenant, job_id)
        if checkpoint is None:
            raise ValidationError("bulk import checkpoint not found: " + job_id)
        return checkpoint

    def get_bulk_progress(self, tenant_id: str, job_id: str) -> BulkImportProgress:
        normalized_tenant = TenantId.from_value(tenant_id)
        checkpoint = self._import_repository.get_bulk_import_checkpoint(normalized_tenant, job_id)
        if checkpoint is None:
            raise ValidationError("bulk import checkpoint not found: " + job_id)
        report = self._import_repository.get_bulk_import_report(normalized_tenant, job_id)
        return BulkImportProgress.create(checkpoint, report)

    def get_report(self, tenant_id: str, job_id: str) -> ImportReport:
        normalized_tenant = TenantId.from_value(tenant_id)
        report = self._import_repository.get_import_report(normalized_tenant, job_id)
        if report is None:
            raise ValidationError("import job not found: " + job_id)
        return report

    def _normalize_bulk_batch_size(self, value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 100_000:
            raise ValidationError("bulk import batch size must be between 1 and 100000")
        return normalized

    def _normalize_checkpoint_interval(self, value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 1_000_000:
            raise ValidationError("bulk import checkpoint interval must be between 1 and 1000000")
        return normalized

    def _normalize_sample_limit(self, value: int) -> int:
        normalized = int(value)
        if not 0 <= normalized <= 10_000:
            raise ValidationError("bulk import sample limit must be between 0 and 10000")
        return normalized

    def _resume_checkpoint(
        self, tenant_id: TenantId, job_id: str | None
    ) -> BulkImportCheckpoint | None:
        if job_id is None or not job_id.strip():
            return None
        checkpoint = self._import_repository.get_bulk_import_checkpoint(tenant_id, job_id.strip())
        if checkpoint is None:
            raise ValidationError("bulk import checkpoint not found: " + job_id)
        if checkpoint.status == ImportJobStatus.APPLIED:
            raise ValidationError("bulk import job is already applied: " + job_id)
        return checkpoint

    def _iter_rows(
        self, path: Path, import_format: ImportFormat
    ) -> Iterator[tuple[int, dict[str, str]]]:
        for row_number, row in enumerate(self._parser.iter_rows(path, import_format), start=1):
            if row_number > self._MAX_ROWS:
                raise ValidationError("import dataset exceeds 1,000,000 rows")
            yield row_number, row

    def _impact_for_candidate(
        self, tenant_id: TenantId, candidate: ImportCandidate
    ) -> ImportRowImpact:
        existing = self._source_repository.find_object(tenant_id, candidate.key)
        action = "update" if existing is not None else "create"
        return ImportRowImpact.create(candidate.row_number, action, candidate.key, candidate.kind)

    def _flush_bulk_batch(
        self,
        tenant_id: TenantId,
        actor: str,
        dry_run: bool,
        job_id: EntityId,
        next_row_number: int,
        candidates: list[ImportCandidate],
        counters: dict[str, int],
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            if not dry_run:
                self._apply_candidates(tenant_id, actor, tuple(candidates), len(candidates))
            self._import_repository.save_bulk_import_checkpoint(
                BulkImportCheckpoint.create(
                    tenant_id=tenant_id,
                    job_id=job_id,
                    next_row_number=next_row_number,
                    total_rows=counters["total_rows"],
                    valid_rows=counters["valid_rows"],
                    invalid_rows=counters["invalid_rows"],
                    create_count=counters["create_count"],
                    update_count=counters["update_count"],
                    batches_completed=counters["batches_completed"],
                    status=self._bulk_status(dry_run, counters["invalid_rows"]),
                )
            )
            unit_of_work.commit()

    def _save_bulk_checkpoint(
        self,
        tenant_id: TenantId,
        job_id: EntityId,
        next_row_number: int,
        counters: dict[str, int],
        status: ImportJobStatus,
    ) -> BulkImportCheckpoint:
        checkpoint = BulkImportCheckpoint.create(
            tenant_id=tenant_id,
            job_id=job_id,
            next_row_number=next_row_number,
            total_rows=counters["total_rows"],
            valid_rows=counters["valid_rows"],
            invalid_rows=counters["invalid_rows"],
            create_count=counters["create_count"],
            update_count=counters["update_count"],
            batches_completed=counters["batches_completed"],
            status=status,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._import_repository.save_bulk_import_checkpoint(checkpoint)
            unit_of_work.commit()
        return checkpoint

    def _bulk_status(self, dry_run: bool, invalid_rows: int) -> ImportJobStatus:
        if invalid_rows:
            return ImportJobStatus.FAILED
        if dry_run:
            return ImportJobStatus.VALIDATED
        return ImportJobStatus.APPLIED

    def _append_sample(
        self, sample: list[ImportRowImpact], item: ImportRowImpact, sample_limit: int
    ) -> None:
        if len(sample) < sample_limit:
            sample.append(item)

    def _extend_sample(
        self, sample: list[ImportRowIssue], items: tuple[ImportRowIssue, ...], sample_limit: int
    ) -> None:
        remaining = sample_limit - len(sample)
        if remaining > 0:
            sample.extend(items[:remaining])

    def _migration_template(self, source: LegacyMigrationSource) -> MigrationTemplate:
        templates: dict[
            LegacyMigrationSource,
            tuple[str, dict[str, object], tuple[str, ...], tuple[str, ...], tuple[str, ...]],
        ] = {
            LegacyMigrationSource.DEVICE42: (
                "Device42 assets baseline",
                {
                    "key": "device_name",
                    "kind": "literal:device",
                    "display_name": "device_name",
                    "source": "literal:device42_migration",
                    "tags": "tags",
                    "attributes.serial": "serial_no",
                    "attributes.asset_no": "asset_no",
                    "attributes.ip_address": "ip_address",
                    "attributes.manufacturer": "manufacturer",
                    "attributes.model": "model",
                },
                ("device_name",),
                ("serial_no", "asset_no", "ip_address", "manufacturer", "model", "tags"),
                ("Device42 CI and hardware exports should include a stable device_name.",),
            ),
            LegacyMigrationSource.NETBOX: (
                "NetBox devices baseline",
                {
                    "key": "name",
                    "kind": "literal:device",
                    "display_name": "name",
                    "source": "literal:netbox_migration",
                    "tags": "tags",
                    "attributes.status": "status",
                    "attributes.role": "role",
                    "attributes.site": "site",
                    "attributes.rack": "rack",
                    "attributes.serial": "serial",
                },
                ("name",),
                ("status", "role", "site", "rack", "serial", "tags"),
                ("NetBox device exports should preserve name as stable natural key.",),
            ),
            LegacyMigrationSource.NAUTOBOT: (
                "Nautobot devices baseline",
                {
                    "key": "name",
                    "kind": "literal:device",
                    "display_name": "name",
                    "source": "literal:nautobot_migration",
                    "tags": "tags",
                    "attributes.status": "status",
                    "attributes.role": "role",
                    "attributes.location": "location",
                    "attributes.platform": "platform",
                    "attributes.serial": "serial",
                },
                ("name",),
                ("status", "role", "location", "platform", "serial", "tags"),
                (
                    "Nautobot location and role fields are retained as attributes "
                    "for reconciliation.",
                ),
            ),
            LegacyMigrationSource.GLPI: (
                "GLPI computer inventory baseline",
                {
                    "key": "name",
                    "kind": "literal:device",
                    "display_name": "name",
                    "source": "literal:glpi_migration",
                    "tags": "groups",
                    "attributes.serial": "serial",
                    "attributes.inventory_number": "inventory_number",
                    "attributes.location": "location",
                    "attributes.status": "status",
                    "attributes.user": "user",
                },
                ("name",),
                ("serial", "inventory_number", "location", "status", "user", "groups"),
                ("GLPI user ownership is imported as attribute, not as IAM identity.",),
            ),
            LegacyMigrationSource.CSV: (
                "Generic CSV ITRM baseline",
                {
                    "key": "key",
                    "kind": "kind",
                    "display_name": "display_name",
                    "source": "source",
                    "tags": "tags",
                },
                ("key", "kind", "display_name", "source"),
                ("tags",),
                ("Generic CSV keeps explicit source and kind columns under operator control.",),
            ),
        }
        name, mapping_payload, required, recommended, notes = templates[source]
        return MigrationTemplate.create(
            source=source,
            name=name,
            version="1.0",
            mapping=ImportMapping.from_dict(mapping_payload),
            required_columns=required,
            recommended_columns=recommended,
            notes=notes,
        )

    def _effective_migration_template(
        self, template: MigrationTemplate, rows: tuple[dict[str, str], ...]
    ) -> MigrationTemplate:
        columns = set(rows[0].keys()) if rows else set[str]()
        required = set(template.required_columns)
        mapping_payload: dict[str, object] = {}
        for field in template.mapping.fields:
            if (
                field.source_field.startswith("literal:")
                or field.source_field in columns
                or field.source_field in required
            ):
                mapping_payload[field.target_field] = field.source_field
        return MigrationTemplate.create(
            source=template.source,
            name=template.name,
            version=template.version,
            mapping=ImportMapping.from_dict(mapping_payload),
            required_columns=template.required_columns,
            recommended_columns=template.recommended_columns,
            notes=template.notes,
        )

    def _migration_gaps(
        self, rows: tuple[dict[str, str], ...], template: MigrationTemplate
    ) -> tuple[MigrationGap, ...]:
        columns = set(rows[0].keys()) if rows else set[str]()
        gaps: list[MigrationGap] = []
        for required in template.required_columns:
            if required not in columns:
                gaps.append(
                    MigrationGap.create(
                        "missing-required",
                        required,
                        "required source column is absent from migration dataset",
                        Severity.ERROR,
                    )
                )
        mapped_columns = {
            field.source_field
            for field in template.mapping.fields
            if not field.source_field.startswith("literal:")
        }
        for column in sorted(columns - mapped_columns):
            gaps.append(
                MigrationGap.create(
                    "unmapped-source",
                    column,
                    "source column is not mapped by the selected migration template",
                    Severity.WARNING,
                )
            )
        for recommended in template.recommended_columns:
            if recommended not in columns:
                gaps.append(
                    MigrationGap.create(
                        "mapping-warning",
                        recommended,
                        "recommended source column is absent; migration can continue "
                        "with reduced fidelity",
                        Severity.WARNING,
                    )
                )
        return tuple(gaps)

    def _normalize_batch_size(self, value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 10_000:
            raise ValidationError("import batch size must be between 1 and 10000")
        return normalized

    def _build_candidates(
        self,
        rows: tuple[dict[str, str], ...],
        mapping: ImportMapping,
    ) -> tuple[tuple[ImportCandidate, ...], tuple[ImportRowIssue, ...]]:
        candidates: list[ImportCandidate] = []
        issues: list[ImportRowIssue] = []
        for row_number, row in enumerate(rows, start=1):
            candidate, row_issues = self._candidate_from_row(row_number, row, mapping)
            issues.extend(row_issues)
            if candidate is not None and not row_issues:
                candidates.append(candidate)
        return tuple(candidates), tuple(issues)

    def _candidate_from_row(
        self,
        row_number: int,
        row: dict[str, str],
        mapping: ImportMapping,
    ) -> tuple[ImportCandidate | None, tuple[ImportRowIssue, ...]]:
        mapped: dict[str, str] = {}
        issues: list[ImportRowIssue] = []
        for field in mapping.fields:
            if field.source_field.startswith("literal:"):
                mapped[field.target_field] = field.source_field.removeprefix("literal:").strip()
                continue
            if field.source_field not in row:
                issues.append(
                    ImportRowIssue.create(
                        row_number,
                        field.target_field,
                        "missing source column: " + field.source_field,
                    )
                )
                continue
            mapped[field.target_field] = row[field.source_field].strip()
        for required in ("key", "kind", "display_name", "source"):
            if not mapped.get(required):
                issues.append(
                    ImportRowIssue.create(row_number, required, "required field is empty")
                )
        attributes = self._attributes_from_mapped(row_number, mapped, issues)
        try:
            candidate = ImportCandidate.create(
                row_number=row_number,
                key=mapped.get("key", ""),
                kind=mapped.get("kind", ""),
                display_name=mapped.get("display_name", ""),
                source=mapped.get("source", ""),
                tags=self._tags_from_value(mapped.get("tags", "")),
                attributes=attributes,
            )
        except ValidationError as exc:
            issues.append(ImportRowIssue.create(row_number, "row", str(exc)))
            candidate = None
        return candidate, tuple(issues)

    def _attributes_from_mapped(
        self,
        row_number: int,
        mapped: dict[str, str],
        issues: list[ImportRowIssue],
    ) -> dict[str, object]:
        attributes: dict[str, object] = {}
        for target_field, value in mapped.items():
            if not target_field.startswith("attributes."):
                continue
            attribute_key = target_field.removeprefix("attributes.")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", attribute_key):
                issues.append(
                    ImportRowIssue.create(row_number, target_field, "invalid attribute key")
                )
                continue
            attributes[attribute_key] = self._coerce_attribute_value(value)
        return attributes

    def _coerce_attribute_value(self, value: str) -> object:
        normalized = value.strip()
        if normalized == "":
            return ""
        if normalized.lower() in {"true", "false"}:
            return normalized.lower() == "true"
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            return normalized

    def _tags_from_value(self, value: str) -> tuple[str, ...]:
        separators_normalized = value.replace(";", ",")
        return tuple(tag.strip().lower() for tag in separators_normalized.split(",") if tag.strip())

    def _build_impacts(
        self,
        tenant_id: TenantId,
        candidates: tuple[ImportCandidate, ...],
    ) -> tuple[ImportRowImpact, ...]:
        impacts: list[ImportRowImpact] = []
        for candidate in candidates:
            existing = self._source_repository.find_object(tenant_id, candidate.key)
            action = "update" if existing is not None else "create"
            impacts.append(
                ImportRowImpact.create(
                    candidate.row_number,
                    action,
                    candidate.key,
                    candidate.kind,
                )
            )
        return tuple(impacts)

    def _status_for(
        self,
        dry_run: bool,
        issues: tuple[ImportRowIssue, ...],
    ) -> ImportJobStatus:
        if issues:
            return ImportJobStatus.FAILED
        if dry_run:
            return ImportJobStatus.VALIDATED
        return ImportJobStatus.APPLIED

    def _apply_candidates(
        self,
        tenant_id: TenantId,
        actor: str,
        candidates: tuple[ImportCandidate, ...],
        batch_size: int,
    ) -> None:
        for index in range(0, len(candidates), batch_size):
            for candidate in candidates[index : index + batch_size]:
                existing = self._source_repository.find_object(tenant_id, candidate.key)
                if existing is None:
                    self._source_repository.create_object(
                        tenant_id=tenant_id,
                        key=candidate.key,
                        kind=candidate.kind,
                        display_name=candidate.display_name,
                        attributes=candidate.attributes,
                        tags=candidate.tags,
                        source=candidate.source,
                        actor=actor,
                    )
                    continue
                self._source_repository.upsert_object(
                    existing.revise(
                        display_name=candidate.display_name,
                        attributes=candidate.attributes,
                        tags=candidate.tags,
                        source=candidate.source,
                    ),
                    actor,
                )
