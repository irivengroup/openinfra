from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from openinfra.application.ports import (
    AuditRepository,
    ExposureContextPage,
    RiskFindingPage,
    SbomComparisonPage,
    SbomDocumentPage,
    SbomPayloadParserPort,
    SbomRepository,
    TransactionManager,
    VulnerabilityRecordPage,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    DomainEvent,
    NotFoundError,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.domain.sbom import (
    ExposureContext,
    RiskFinding,
    SbomComparison,
    SbomComponent,
    SbomDocument,
    VulnerabilityRecord,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class ImportSbomCommand:
    tenant_id: str
    admin_token: str
    application: str
    release: str
    environment: str
    source_name: str
    payload: bytes | str | dict[str, object]
    source_uri: str | None = None
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetSbomCommand:
    tenant_id: str
    admin_token: str
    document_id: str


@dataclass(frozen=True, slots=True)
class ListSbomsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    application: str | None = None
    environment: str | None = None
    format: str | None = None


@dataclass(frozen=True, slots=True)
class ImportVulnerabilityCommand:
    tenant_id: str
    admin_token: str
    cve_id: str
    component_name: str
    component_version: str
    cvss_score: Decimal | str | int | float
    component_purl: str | None = None
    known_exploited: bool = False
    exploit_maturity: str = "unknown"
    source_name: str = "external-scanner"
    published_at: datetime | None = None
    modified_at: datetime | None = None
    references: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class ListVulnerabilitiesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    cve_id: str | None = None
    component: str | None = None
    known_exploited: bool | None = None


@dataclass(frozen=True, slots=True)
class UpsertExposureCommand:
    tenant_id: str
    admin_token: str
    application: str
    environment: str
    internet_exposed: bool
    flow_exposed: bool
    business_criticality: int
    compensating_controls: tuple[str, ...] = ()
    asset_ids: tuple[str, ...] = ()
    service_ids: tuple[str, ...] = ()
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetExposureCommand:
    tenant_id: str
    admin_token: str
    application: str
    environment: str


@dataclass(frozen=True, slots=True)
class ListExposuresCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class AssessSbomRiskCommand:
    tenant_id: str
    admin_token: str
    document_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class ListRiskFindingsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    document_id: str | None = None
    priority: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class CompareSbomsCommand:
    tenant_id: str
    admin_token: str
    base_document_id: str
    target_document_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetSbomComparisonCommand:
    tenant_id: str
    admin_token: str
    comparison_id: str


@dataclass(frozen=True, slots=True)
class ListSbomComparisonsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ExportSbomRiskCommand:
    tenant_id: str
    admin_token: str
    document_id: str
    format: str = "json"


@dataclass(frozen=True, slots=True)
class SbomExport:
    filename: str
    content_type: str
    content: bytes


class SbomService:
    _MAX_VULNERABILITIES = 100_000
    _PAGE_SIZE = 500

    def __init__(
        self,
        repository: SbomRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        parser: SbomPayloadParserPort,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._parser = parser

    def import_sbom(self, command: ImportSbomCommand) -> SbomDocument:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.SBOM_IMPORT
        )
        parsed = self._parser.parse(command.payload)
        candidate = SbomDocument.create(
            tenant_id,
            command.application,
            command.release,
            command.environment,
            parsed.format.value,
            parsed.specification_version,
            command.source_name,
            command.source_uri,
            parsed.source_hash,
            self._repository.next_document_version(
                tenant_id, command.application, command.environment
            ),
            parsed.components,
            parsed.serial_number,
            parsed.metadata,
        )
        existing = self._repository.find_document_by_fingerprint(tenant_id, candidate.fingerprint)
        if existing is not None:
            return existing
        self._save_with_audit(
            candidate,
            command.actor or principal.subject,
            "sbom.document.imported",
            "sbom_document",
            lambda: self._repository.save_document(candidate),
            {
                "application": candidate.application,
                "release": candidate.release,
                "environment": candidate.environment,
                "format": candidate.format.value,
                "source_hash": candidate.source_hash,
                "component_count": candidate.component_count,
            },
        )
        return candidate

    def get_sbom(self, command: GetSbomCommand) -> SbomDocument:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        item = self._repository.get_document(tenant_id, command.document_id)
        if item is None:
            raise NotFoundError("SBOM document not found")
        return item

    def list_sboms(self, command: ListSbomsCommand) -> SbomDocumentPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        return self._repository.list_documents(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.application,
            command.environment,
            command.format,
        )

    def import_vulnerability(self, command: ImportVulnerabilityCommand) -> VulnerabilityRecord:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.SBOM_IMPORT
        )
        candidate = VulnerabilityRecord.create(
            tenant_id,
            command.cve_id,
            command.component_name,
            command.component_version,
            command.cvss_score,
            command.component_purl,
            command.known_exploited,
            command.exploit_maturity,
            command.source_name,
            command.published_at,
            command.modified_at,
            command.references,
            command.metadata,
        )
        existing = self._repository.find_vulnerability_by_identity(
            tenant_id, candidate.identity_key
        )
        if existing is not None:
            if self._same_vulnerability(existing, candidate):
                return existing
            raise ValidationError("vulnerability identity already exists with another payload")
        self._save_with_audit(
            candidate,
            command.actor or principal.subject,
            "sbom.vulnerability.imported",
            "sbom_vulnerability",
            lambda: self._repository.save_vulnerability(candidate),
            {
                "cve_id": candidate.cve_id,
                "component": candidate.component_purl or candidate.component_name,
                "cvss_score": str(candidate.cvss_score),
                "known_exploited": candidate.known_exploited,
                "source_name": candidate.source_name,
            },
        )
        return candidate

    def list_vulnerabilities(self, command: ListVulnerabilitiesCommand) -> VulnerabilityRecordPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        return self._repository.list_vulnerabilities(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.cve_id,
            command.component,
            command.known_exploited,
        )

    def upsert_exposure(self, command: UpsertExposureCommand) -> ExposureContext:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.SBOM_WRITE
        )
        exposure = ExposureContext.create(
            tenant_id,
            command.application,
            command.environment,
            command.internet_exposed,
            command.flow_exposed,
            command.business_criticality,
            command.compensating_controls,
            command.asset_ids,
            command.service_ids,
        )
        self._save_with_audit(
            exposure,
            command.actor or principal.subject,
            "sbom.exposure.updated",
            "sbom_exposure",
            lambda: self._repository.save_exposure(exposure),
        )
        return exposure

    def get_exposure(self, command: GetExposureCommand) -> ExposureContext:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        item = self._repository.get_exposure(tenant_id, command.application, command.environment)
        if item is None:
            raise NotFoundError("SBOM exposure context not found")
        return item

    def list_exposures(self, command: ListExposuresCommand) -> ExposureContextPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        return self._repository.list_exposures(
            tenant_id, Pagination.from_values(command.limit, command.cursor)
        )

    def assess_risk(self, command: AssessSbomRiskCommand) -> RiskFindingPage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.SBOM_EXECUTE
        )
        document = self._repository.get_document(tenant_id, command.document_id)
        if document is None:
            raise NotFoundError("SBOM document not found")
        exposure = self._repository.get_exposure(
            tenant_id, document.application, document.environment
        )
        vulnerabilities = self._all_vulnerabilities(tenant_id)
        findings: list[RiskFinding] = []
        for component in document.components:
            for vulnerability in vulnerabilities:
                if self._matches(component, vulnerability):
                    findings.append(
                        RiskFinding.create(tenant_id, document, component, vulnerability, exposure)
                    )
        findings.sort(
            key=lambda item: (item.contextual_score, item.cve_id, item.component_ref),
            reverse=True,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.replace_findings(tenant_id, document.id.value, tuple(findings))
            event = DomainEvent.create(
                tenant_id,
                document.id,
                "sbom.risk.assessed",
                {
                    "document_id": document.id.value,
                    "finding_count": len(findings),
                    "exposure_context": exposure is not None,
                },
            )
            self._repository.append_event(event)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or principal.subject,
                    "sbom.risk.assessed",
                    "sbom_document",
                    document.id.value,
                    metadata=event.payload,
                )
            )
            unit_of_work.commit()
        return RiskFindingPage(tuple(findings[: self._PAGE_SIZE]), None)

    def list_findings(self, command: ListRiskFindingsCommand) -> RiskFindingPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        return self._repository.list_findings(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.document_id,
            command.priority,
            command.status,
        )

    def compare(self, command: CompareSbomsCommand) -> SbomComparison:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.SBOM_EXECUTE
        )
        base = self._repository.get_document(tenant_id, command.base_document_id)
        target = self._repository.get_document(tenant_id, command.target_document_id)
        if base is None or target is None:
            raise NotFoundError("base or target SBOM document not found")
        if base.application != target.application:
            raise ValidationError("SBOM comparison requires the same application")
        comparison = SbomComparison.create(tenant_id, base, target)
        existing = self._repository.find_comparison_by_digest(tenant_id, comparison.input_digest)
        if existing is not None:
            return existing
        self._save_with_audit(
            comparison,
            command.actor or principal.subject,
            "sbom.comparison.generated",
            "sbom_comparison",
            lambda: self._repository.save_comparison(comparison),
        )
        return comparison

    def get_comparison(self, command: GetSbomComparisonCommand) -> SbomComparison:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        item = self._repository.get_comparison(tenant_id, command.comparison_id)
        if item is None:
            raise NotFoundError("SBOM comparison not found")
        return item

    def list_comparisons(self, command: ListSbomComparisonsCommand) -> SbomComparisonPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.SBOM_READ)
        return self._repository.list_comparisons(
            tenant_id, Pagination.from_values(command.limit, command.cursor)
        )

    def export_risk(self, command: ExportSbomRiskCommand) -> SbomExport:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.SBOM_EXPORT
        )
        document = self._repository.get_document(tenant_id, command.document_id)
        if document is None:
            raise NotFoundError("SBOM document not found")
        findings = self._all_findings(tenant_id, document.id.value)
        normalized_format = command.format.strip().lower()
        if normalized_format == "json":
            content = json.dumps(
                {
                    "document": document.as_dict(),
                    "findings": [item.as_dict() for item in findings],
                },
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            ).encode("utf-8")
            return SbomExport(
                f"openinfra-sbom-risk-{document.id.value}.json",
                "application/json; charset=utf-8",
                content,
            )
        if normalized_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(
                [
                    "application",
                    "release",
                    "environment",
                    "component",
                    "version",
                    "purl",
                    "cve_id",
                    "contextual_score",
                    "priority",
                    "status",
                    "reasons",
                ]
            )
            for finding in findings:
                writer.writerow(
                    [
                        document.application,
                        document.release,
                        document.environment,
                        finding.component_name,
                        finding.component_version,
                        finding.component_purl or "",
                        finding.cve_id,
                        str(finding.contextual_score),
                        finding.priority.value,
                        finding.status.value,
                        " | ".join(finding.reasons),
                    ]
                )
            return SbomExport(
                f"openinfra-sbom-risk-{document.id.value}.csv",
                "text/csv; charset=utf-8",
                output.getvalue().encode("utf-8"),
            )
        raise ValidationError("SBOM export format must be json or csv")

    def _all_vulnerabilities(self, tenant_id: TenantId) -> tuple[VulnerabilityRecord, ...]:
        items: list[VulnerabilityRecord] = []
        cursor: str | None = None
        while len(items) < self._MAX_VULNERABILITIES:
            page = self._repository.list_vulnerabilities(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_VULNERABILITIES - len(items)),
                    cursor,
                ),
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor
        if cursor is not None:
            raise ValidationError("SBOM vulnerability query exceeds 100000 records")
        return tuple(items)

    def _all_findings(self, tenant_id: TenantId, document_id: str) -> tuple[RiskFinding, ...]:
        items: list[RiskFinding] = []
        cursor: str | None = None
        while True:
            page = self._repository.list_findings(
                tenant_id,
                Pagination.from_values(self._PAGE_SIZE, cursor),
                document_id,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor

    @staticmethod
    def _matches(component: SbomComponent, vulnerability: VulnerabilityRecord) -> bool:
        if vulnerability.component_purl:
            return component.purl == vulnerability.component_purl
        return (
            component.name.strip().lower() == vulnerability.component_name.strip().lower()
            and component.version == vulnerability.component_version
        )

    @staticmethod
    def _same_vulnerability(existing: VulnerabilityRecord, candidate: VulnerabilityRecord) -> bool:
        existing_payload = existing.as_dict()
        candidate_payload = candidate.as_dict()
        for field in ("id", "tenant_id", "imported_at"):
            existing_payload.pop(field, None)
            candidate_payload.pop(field, None)
        return existing_payload == candidate_payload

    def _save_with_audit(
        self,
        aggregate: SbomDocument | VulnerabilityRecord | ExposureContext | SbomComparison,
        actor: str,
        event_name: str,
        target_type: str,
        saver: Callable[[], None],
        metadata: dict[str, object] | None = None,
    ) -> None:
        payload = dict(metadata or aggregate.as_dict())
        with self._transaction_manager.begin() as unit_of_work:
            saver()
            self._repository.append_event(
                DomainEvent.create(aggregate.tenant_id, aggregate.id, event_name, payload)
            )
            self._audit_repository.append(
                AuditEvent.record(
                    aggregate.tenant_id,
                    actor,
                    event_name,
                    target_type,
                    aggregate.id.value,
                    metadata=payload,
                )
            )
            unit_of_work.commit()

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized.value, token, permission)
        )
        return normalized, principal
