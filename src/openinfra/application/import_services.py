from __future__ import annotations

import json
import re
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
from openinfra.domain.common import AuditEvent, Severity, TenantId, ValidationError
from openinfra.domain.data_import import (
    ImportCandidate,
    ImportFormat,
    ImportJobStatus,
    ImportMapping,
    ImportReport,
    ImportRowImpact,
    ImportRowIssue,
)
from openinfra.domain.security import Permission


class DatasetParser(Protocol):
    def parse(self, path: Path, import_format: ImportFormat) -> tuple[dict[str, str], ...]:
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

    def import_dataset(self, command: ImportDatasetCommand) -> ImportReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_WRITE)
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

    def get_report(self, tenant_id: str, job_id: str) -> ImportReport:
        normalized_tenant = TenantId.from_value(tenant_id)
        report = self._import_repository.get_import_report(normalized_tenant, job_id)
        if report is None:
            raise ValidationError("import job not found: " + job_id)
        return report

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
