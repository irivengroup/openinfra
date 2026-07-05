from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar

from openinfra.application.ports import (
    AuditRepository,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import AuditEvent, NotFoundError, Pagination, TenantId
from openinfra.domain.security import Permission
from openinfra.domain.source_of_truth import SourceOfTruthObject


class RiQualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class RiCertificationStatus(StrEnum):
    CERTIFIED = "certified"
    WARNING = "warning"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class RiQualityIssue:
    severity: RiQualitySeverity
    code: str
    field: str
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class RiQualityReport:
    tenant_id: TenantId
    key: str
    kind: str
    display_name: str
    source: str
    version: int
    score: int
    completeness_score: int
    freshness_score: int
    authority_score: int
    confidence_score: int
    certification_status: RiCertificationStatus
    issues: tuple[RiQualityIssue, ...]
    evaluated_at: datetime

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "domain": "ressources_inventory",
            "key": self.key,
            "kind": self.kind,
            "display_name": self.display_name,
            "source": self.source,
            "version": self.version,
            "score": self.score,
            "completeness_score": self.completeness_score,
            "freshness_score": self.freshness_score,
            "authority_score": self.authority_score,
            "confidence_score": self.confidence_score,
            "certification_status": self.certification_status.value,
            "issues": [issue.as_dict() for issue in self.issues],
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RiQualitySummary:
    tenant_id: TenantId
    total: int
    certified: int
    warning: int
    rejected: int
    average_score: float
    reports: tuple[RiQualityReport, ...]
    evaluated_at: datetime

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "domain": "ressources_inventory",
            "total": self.total,
            "certified": self.certified,
            "warning": self.warning,
            "rejected": self.rejected,
            "average_score": self.average_score,
            "reports": [report.as_dict() for report in self.reports],
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class EvaluateRiObjectQualityCommand:
    tenant_id: str
    admin_token: str
    key: str


@dataclass(frozen=True, slots=True)
class RiQualitySummaryCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    kind: str | None = None
    tag: str | None = None


class RessourcesInventoryQualityService:
    _REQUIRED_ATTRIBUTES: ClassVar[dict[str, tuple[str, ...]]] = {
        "generic": (),
        "device": ("serial", "site"),
        "interface": ("parent", "mac_address"),
        "service": ("owner", "protocol"),
        "application": ("owner", "environment"),
    }
    _FRESHNESS_WARNING_SECONDS = 90 * 24 * 60 * 60
    _FRESHNESS_ERROR_SECONDS = 365 * 24 * 60 * 60

    def __init__(
        self,
        repository: SourceOfTruthRepository,
        governance_repository: SourceGovernanceRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._governance_repository = governance_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def evaluate_object(self, command: EvaluateRiObjectQualityCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RI_QUALITY_READ,
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            source_object = self._repository.find_object(tenant_id, command.key)
            if source_object is None:
                raise NotFoundError("ressources inventory object not found: " + command.key)
            report = self._evaluate_source_object(source_object)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="ri.quality.evaluate",
                    target_type="ri_object",
                    target_id=source_object.key.value,
                    metadata={
                        "score": report.score,
                        "certification_status": report.certification_status.value,
                    },
                )
            )
            unit_of_work.commit()
        return report.as_dict()

    def summarize(self, command: RiQualitySummaryCommand) -> RiQualitySummary:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id.value,
                command.admin_token,
                Permission.RI_QUALITY_READ,
            )
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._repository.list_objects(
                tenant_id=tenant_id,
                pagination=pagination,
                kind=command.kind,
                tag=command.tag,
            )
            reports = tuple(self._evaluate_source_object(item) for item in page.items)
            summary = self._summary_from_reports(tenant_id, reports)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="ri.quality.summary",
                    target_type="ri_quality",
                    target_id=tenant_id.value,
                    metadata={
                        "limit": pagination.limit,
                        "kind": command.kind,
                        "total": summary.total,
                        "average_score": summary.average_score,
                    },
                )
            )
            unit_of_work.commit()
        return summary

    def _evaluate_source_object(self, source_object: SourceOfTruthObject) -> RiQualityReport:
        issues: list[RiQualityIssue] = []
        kind = source_object.kind.value
        required_attributes = self._REQUIRED_ATTRIBUTES[kind]
        missing_fields = tuple(
            field for field in required_attributes if not source_object.attributes.get(field)
        )
        for field in missing_fields:
            issues.append(
                RiQualityIssue(
                    RiQualitySeverity.ERROR,
                    "required_attribute_missing",
                    field,
                    "mandatory RI attribute is missing or empty",
                )
            )
        if not source_object.tags:
            issues.append(
                RiQualityIssue(
                    RiQualitySeverity.INFO,
                    "no_tags",
                    "tags",
                    "resource has no classification tag",
                )
            )
        freshness_score = self._freshness_score(source_object, issues)
        authority_score = self._authority_score(source_object, issues)
        completeness_score = max(0, 100 - (35 * len(missing_fields)))
        confidence_score = self._confidence_score(source_object)
        score = round(
            (0.40 * completeness_score)
            + (0.25 * freshness_score)
            + (0.25 * authority_score)
            + (0.10 * confidence_score)
        )
        certification_status = self._certification_status(score, issues)
        return RiQualityReport(
            tenant_id=source_object.tenant_id,
            key=source_object.key.value,
            kind=source_object.kind.value,
            display_name=source_object.display_name,
            source=source_object.source.value,
            version=source_object.version,
            score=score,
            completeness_score=completeness_score,
            freshness_score=freshness_score,
            authority_score=authority_score,
            confidence_score=confidence_score,
            certification_status=certification_status,
            issues=tuple(issues),
            evaluated_at=datetime.now(UTC),
        )

    def _freshness_score(
        self,
        source_object: SourceOfTruthObject,
        issues: list[RiQualityIssue],
    ) -> int:
        age_seconds = (datetime.now(UTC) - source_object.updated_at).total_seconds()
        if age_seconds > self._FRESHNESS_ERROR_SECONDS:
            issues.append(
                RiQualityIssue(
                    RiQualitySeverity.ERROR,
                    "stale_resource",
                    "updated_at",
                    "resource has not been refreshed for more than 365 days",
                )
            )
            return 25
        if age_seconds > self._FRESHNESS_WARNING_SECONDS:
            issues.append(
                RiQualityIssue(
                    RiQualitySeverity.WARNING,
                    "stale_resource",
                    "updated_at",
                    "resource has not been refreshed for more than 90 days",
                )
            )
            return 70
        return 100

    def _authority_score(
        self,
        source_object: SourceOfTruthObject,
        issues: list[RiQualityIssue],
    ) -> int:
        rules = self._governance_repository.find_active_rules_for_kind(
            source_object.tenant_id,
            source_object.kind.value,
        )
        non_authoritative_count = 0
        for rule in rules:
            path = rule.attribute_path.value
            if path == "*":
                governed = bool(source_object.attributes)
                field_name = "*"
            else:
                governed = path in source_object.attributes
                field_name = path
            if governed and not rule.is_authoritative(source_object.source):
                non_authoritative_count += 1
                issues.append(
                    RiQualityIssue(
                        RiQualitySeverity.WARNING,
                        "non_authoritative_source",
                        field_name,
                        "attribute is populated by a source that is not authoritative",
                    )
                )
        return max(0, 100 - (30 * non_authoritative_count))

    def _confidence_score(self, source_object: SourceOfTruthObject) -> int:
        source = source_object.source.value
        if source.startswith(("discovery", "import", "api")):
            return 90
        if source == "manual":
            return 75
        return 80

    def _certification_status(
        self,
        score: int,
        issues: list[RiQualityIssue],
    ) -> RiCertificationStatus:
        if any(issue.severity is RiQualitySeverity.ERROR for issue in issues) or score < 70:
            return RiCertificationStatus.REJECTED
        if any(issue.severity is RiQualitySeverity.WARNING for issue in issues) or score < 90:
            return RiCertificationStatus.WARNING
        return RiCertificationStatus.CERTIFIED

    def _summary_from_reports(
        self,
        tenant_id: TenantId,
        reports: tuple[RiQualityReport, ...],
    ) -> RiQualitySummary:
        certified = sum(
            1
            for report in reports
            if report.certification_status is RiCertificationStatus.CERTIFIED
        )
        warning = sum(
            1 for report in reports if report.certification_status is RiCertificationStatus.WARNING
        )
        rejected = sum(
            1 for report in reports if report.certification_status is RiCertificationStatus.REJECTED
        )
        average = (
            round(sum(report.score for report in reports) / len(reports), 2) if reports else 0.0
        )
        return RiQualitySummary(
            tenant_id=tenant_id,
            total=len(reports),
            certified=certified,
            warning=warning,
            rejected=rejected,
            average_score=average,
            reports=reports,
            evaluated_at=datetime.now(UTC),
        )
