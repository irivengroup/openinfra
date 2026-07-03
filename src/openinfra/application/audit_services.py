from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from openinfra.application.ports import AuditRepository, TransactionManager
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.audit import (
    AuditEventFilter,
    AuditEventPage,
    AuditExportBundle,
    AuditExportFormat,
    AuditIntegrityReport,
)
from openinfra.domain.common import AuditEvent, Pagination, TenantId, ValidationError
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class ListAuditEventsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    actor: str | None = None
    action: str | None = None
    target_type: str | None = None
    severity: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class ExportAuditEventsCommand:
    tenant_id: str
    admin_token: str
    format: str = "jsonl"
    limit: int = 500
    cursor: str | None = None
    actor: str | None = None
    action: str | None = None
    target_type: str | None = None
    severity: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class VerifyAuditIntegrityCommand:
    tenant_id: str
    admin_token: str
    limit: int = 500


class AuditTrailService:
    def __init__(
        self,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def list_events(self, command: ListAuditEventsCommand) -> AuditEventPage:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.AUDIT_READ)
        )
        event_filter = self._filter_from_command(tenant_id, command)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._audit_repository.list_records(event_filter)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="audit.events.list",
                    target_type="audit_trail",
                    target_id=tenant_id.value,
                    metadata={
                        "limit": event_filter.pagination.limit,
                        "cursor": event_filter.pagination.cursor,
                        "actor_filter": event_filter.actor,
                        "action_filter": event_filter.action,
                        "target_type_filter": event_filter.target_type,
                        "severity_filter": (
                            event_filter.severity.value if event_filter.severity else None
                        ),
                    },
                )
            )
            unit_of_work.commit()
        return page

    def export_events(self, command: ExportAuditEventsCommand) -> AuditExportBundle:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.AUDIT_READ)
        )
        export_format = AuditExportFormat(str(command.format).strip().lower())
        event_filter = self._filter_from_command(tenant_id, command)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._audit_repository.list_records(event_filter)
            bundle = self._bundle(tenant_id, export_format, page)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="audit.events.export",
                    target_type="audit_trail",
                    target_id=tenant_id.value,
                    metadata={
                        "format": export_format.value,
                        "count": bundle.count,
                        "head_hash": bundle.head_hash,
                    },
                )
            )
            unit_of_work.commit()
        return bundle

    def verify_integrity(self, command: VerifyAuditIntegrityCommand) -> AuditIntegrityReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.AUDIT_READ)
        )
        if not 1 <= int(command.limit) <= 10_000:
            raise ValidationError("audit integrity limit must be between 1 and 10000")
        with self._transaction_manager.begin() as unit_of_work:
            report = self._audit_repository.verify_integrity(tenant_id, int(command.limit))
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="audit.integrity.verify",
                    target_type="audit_trail",
                    target_id=tenant_id.value,
                    metadata={
                        "checked": report.checked,
                        "valid": report.valid,
                        "head_hash": report.head_hash,
                    },
                )
            )
            unit_of_work.commit()
        return report

    def _filter_from_command(
        self,
        tenant_id: TenantId,
        command: ListAuditEventsCommand | ExportAuditEventsCommand,
    ) -> AuditEventFilter:
        return AuditEventFilter.create(
            tenant_id=tenant_id,
            pagination=Pagination.from_values(command.limit, command.cursor),
            actor=command.actor,
            action=command.action,
            target_type=command.target_type,
            severity=command.severity,
            created_from=command.created_from,
            created_to=command.created_to,
        )

    def _bundle(
        self,
        tenant_id: TenantId,
        export_format: AuditExportFormat,
        page: AuditEventPage,
    ) -> AuditExportBundle:
        records = [record.as_dict() for record in page.items]
        head_hash = page.items[0].record_hash if page.items else "0" * 64
        if export_format == AuditExportFormat.JSON:
            payload = json.dumps(
                {"items": records, "next_cursor": page.next_cursor},
                sort_keys=True,
            )
            content_type = "application/json"
        else:
            payload = "\n".join(json.dumps(record, sort_keys=True) for record in records)
            content_type = "application/x-ndjson"
        return AuditExportBundle(
            tenant_id=tenant_id,
            format=export_format,
            content_type=content_type,
            payload=payload,
            count=len(records),
            head_hash=head_hash,
        )
