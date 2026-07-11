from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from openinfra.application.ports import (
    AuditRepository,
    CapacityForecastPage,
    CarbonFactorPage,
    ConsolidationCandidatePage,
    EnergyAnomalyPage,
    EnergyMeasurementPage,
    GreenOpsRepository,
    GreenScorePage,
    MeasurementSourcePage,
    SustainabilityReportPage,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    DomainEvent,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.greenops import (
    CapacityDimension,
    CapacityForecast,
    CarbonEstimate,
    CarbonFactor,
    ConsolidationAction,
    ConsolidationCandidate,
    EnergyAnomaly,
    EnergyMeasurement,
    EnergyScope,
    GreenOpsPolicy,
    GreenOpsValidator,
    GreenScore,
    MeasurementKind,
    MeasurementSource,
    SustainabilityReport,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class CreateMeasurementSourceCommand:
    tenant_id: str
    admin_token: str
    actor: str
    code: str
    name: str
    source_type: str
    owner: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class ListMeasurementSourcesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    active_only: bool = False


@dataclass(frozen=True, slots=True)
class UpsertGreenOpsPolicyCommand:
    tenant_id: str
    admin_token: str
    actor: str
    site_code: str
    default_pue: str
    energy_cost_per_kwh: str
    currency: str
    carbon_factor_code: str
    underutilized_percent: str = "20"
    warning_capacity_percent: str = "80"
    critical_capacity_percent: str = "90"
    minimum_samples: int = 3


@dataclass(frozen=True, slots=True)
class GetGreenOpsPolicyCommand:
    tenant_id: str
    admin_token: str
    site_code: str


@dataclass(frozen=True, slots=True)
class CreateCarbonFactorCommand:
    tenant_id: str
    admin_token: str
    actor: str
    code: str
    region: str
    grams_co2e_per_kwh: str
    source_name: str
    period_start: date
    period_end: date
    source_uri: str | None = None


@dataclass(frozen=True, slots=True)
class ListCarbonFactorsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    code: str | None = None
    region: str | None = None


@dataclass(frozen=True, slots=True)
class IngestEnergyMeasurementCommand:
    tenant_id: str
    admin_token: str
    actor: str
    idempotency_key: str
    source_code: str
    kind: str
    scope: str
    scope_key: str
    site_code: str
    period_start: datetime
    period_end: datetime
    energy_kwh: str
    application_key: str | None = None
    it_energy_kwh: str | None = None
    facility_energy_kwh: str | None = None
    utilization_percent: str | None = None
    energy_capacity_percent: str | None = None
    cooling_capacity_percent: str | None = None
    space_capacity_percent: str | None = None
    weight_capacity_percent: str | None = None
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ListEnergyMeasurementsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    site_code: str | None = None
    scope: str | None = None
    scope_key: str | None = None
    kind: str | None = None


@dataclass(frozen=True, slots=True)
class GenerateSustainabilityReportCommand:
    tenant_id: str
    admin_token: str
    actor: str
    site_code: str
    period_start: date
    period_end: date
    scope: str = "site"
    scope_key: str | None = None


@dataclass(frozen=True, slots=True)
class GetSustainabilityReportCommand:
    tenant_id: str
    admin_token: str
    report_id: str


@dataclass(frozen=True, slots=True)
class ListSustainabilityReportsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    site_code: str | None = None
    scope: str | None = None


@dataclass(frozen=True, slots=True)
class ExportSustainabilityReportCommand:
    tenant_id: str
    admin_token: str
    report_id: str
    format: str = "json"


@dataclass(frozen=True, slots=True)
class ListEnergyAnomaliesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    severity: str | None = None
    site_code: str | None = None


@dataclass(frozen=True, slots=True)
class ListCapacityForecastsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    site_code: str | None = None
    dimension: str | None = None


@dataclass(frozen=True, slots=True)
class ListConsolidationCandidatesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    site_code: str | None = None
    risk_level: str | None = None


@dataclass(frozen=True, slots=True)
class ListGreenScoresCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    scope: str | None = None


@dataclass(frozen=True, slots=True)
class SustainabilityReportExport:
    filename: str
    content_type: str
    content: bytes


class GreenOpsService:
    _PAGE_SIZE = 500
    _MAX_ANALYTIC_MEASUREMENTS = 100_000

    def __init__(
        self,
        repository: GreenOpsRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def create_source(self, command: CreateMeasurementSourceCommand) -> MeasurementSource:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_WRITE
        )
        source = MeasurementSource.create(
            tenant_id,
            command.code,
            command.name,
            command.source_type,
            command.owner,
            command.active,
        )
        existing = self._repository.find_source(tenant_id, source.code)
        if existing is not None:
            if (
                existing.as_dict()
                | {"id": source.id.value, "created_at": source.created_at.isoformat()}
                == source.as_dict()
            ):
                return existing
            raise ValidationError("measurement source code already exists")
        self._save_with_audit(
            source,
            command.actor or principal.subject,
            "green.source.created",
            "green_measurement_source",
            lambda: self._repository.save_source(source),
        )
        return source

    def list_sources(self, command: ListMeasurementSourcesCommand) -> MeasurementSourcePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_sources(
            tenant_id, Pagination.from_values(command.limit, command.cursor), command.active_only
        )

    def upsert_policy(self, command: UpsertGreenOpsPolicyCommand) -> GreenOpsPolicy:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_ADMIN
        )
        candidate = GreenOpsPolicy.create(
            tenant_id,
            command.site_code,
            command.default_pue,
            command.energy_cost_per_kwh,
            command.currency,
            command.carbon_factor_code,
            command.underutilized_percent,
            command.warning_capacity_percent,
            command.critical_capacity_percent,
            command.minimum_samples,
        )
        current = self._repository.get_policy(tenant_id, candidate.site_code)
        policy = (
            candidate
            if current is None
            else GreenOpsPolicy.restore(
                current.id,
                tenant_id,
                candidate.site_code,
                candidate.default_pue,
                candidate.energy_cost_per_kwh,
                candidate.currency,
                candidate.carbon_factor_code,
                candidate.underutilized_percent,
                candidate.warning_capacity_percent,
                candidate.critical_capacity_percent,
                candidate.minimum_samples,
                datetime.now(UTC),
            )
        )
        self._save_with_audit(
            policy,
            command.actor or principal.subject,
            "green.policy.upserted",
            "greenops_policy",
            lambda: self._repository.save_policy(policy),
            {
                "old_state": None if current is None else current.as_dict(),
                "new_state": policy.as_dict(),
            },
        )
        return policy

    def get_policy(self, command: GetGreenOpsPolicyCommand) -> GreenOpsPolicy:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        policy = self._repository.get_policy(tenant_id, command.site_code)
        if policy is None:
            raise NotFoundError("GreenOps policy does not exist for this site")
        return policy

    def create_carbon_factor(self, command: CreateCarbonFactorCommand) -> CarbonFactor:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_WRITE
        )
        factor = CarbonFactor.create(
            tenant_id,
            command.code,
            command.region,
            command.grams_co2e_per_kwh,
            command.source_name,
            command.period_start,
            command.period_end,
            command.source_uri,
        )
        self._save_with_audit(
            factor,
            command.actor or principal.subject,
            "green.carbon-factor.created",
            "green_carbon_factor",
            lambda: self._repository.save_carbon_factor(factor),
        )
        return factor

    def list_carbon_factors(self, command: ListCarbonFactorsCommand) -> CarbonFactorPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_carbon_factors(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.code,
            command.region,
        )

    def ingest_measurement(self, command: IngestEnergyMeasurementCommand) -> EnergyMeasurement:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_IMPORT
        )
        source = self._repository.find_source(tenant_id, command.source_code)
        if source is None or not source.active:
            raise ValidationError("measurement source is missing or inactive")
        measurement = EnergyMeasurement.create(
            tenant_id,
            command.idempotency_key,
            command.source_code,
            command.kind,
            command.scope,
            command.scope_key,
            command.site_code,
            command.period_start,
            command.period_end,
            command.energy_kwh,
            application_key=command.application_key,
            it_energy_kwh=command.it_energy_kwh,
            facility_energy_kwh=command.facility_energy_kwh,
            utilization_percent=command.utilization_percent,
            energy_capacity_percent=command.energy_capacity_percent,
            cooling_capacity_percent=command.cooling_capacity_percent,
            space_capacity_percent=command.space_capacity_percent,
            weight_capacity_percent=command.weight_capacity_percent,
            metadata=dict(command.metadata or {}),
        )
        existing = self._repository.find_measurement_by_idempotency_key(
            tenant_id, measurement.idempotency_key
        )
        if existing is not None:
            left = existing.as_dict() | {
                "id": measurement.id.value,
                "recorded_at": measurement.recorded_at.isoformat(),
            }
            if left != measurement.as_dict():
                raise ValidationError(
                    "GreenOps idempotency key is already bound to another payload"
                )
            return existing
        self._save_with_audit(
            measurement,
            command.actor or principal.subject,
            "green.energy.measurement.ingested",
            "green_energy_measurement",
            lambda: self._repository.save_measurement(measurement),
            {
                "measurement_id": measurement.id.value,
                "source_code": measurement.source_code,
                "scope": measurement.scope.value,
                "scope_key": measurement.scope_key,
                "kind": measurement.kind.value,
                "energy_kwh": str(measurement.energy_kwh),
            },
        )
        return measurement

    def list_measurements(self, command: ListEnergyMeasurementsCommand) -> EnergyMeasurementPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_measurements(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.period_start,
            command.period_end,
            command.site_code,
            command.scope,
            command.scope_key,
            command.kind,
        )

    def generate_report(self, command: GenerateSustainabilityReportCommand) -> SustainabilityReport:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_EXECUTE
        )
        GreenOpsValidator.date_range(command.period_start, command.period_end)
        site_code = GreenOpsValidator.token(command.site_code, "site code", 64)
        scope = EnergyScope.from_value(command.scope)
        scope_key = GreenOpsValidator.token(command.scope_key or site_code, "scope key")
        policy = self._repository.get_policy(tenant_id, site_code)
        if policy is None:
            raise ValidationError("GreenOps policy must be configured before reporting")
        factor = self._select_factor(
            tenant_id, policy.carbon_factor_code, command.period_start, command.period_end
        )
        start = datetime.combine(command.period_start, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(
            command.period_end + timedelta(days=1), datetime.min.time(), tzinfo=UTC
        )
        measurements = self._all_measurements(
            tenant_id, start, end, site_code, scope.value, scope_key
        )
        if not measurements:
            raise ValidationError("no GreenOps measurements match the requested report scope")
        site_measurements = self._all_measurements(tenant_id, start, end, site_code, None, None)
        input_digest = GreenOpsValidator.digest(
            {
                "measurements": [
                    item.as_dict()
                    for item in sorted(site_measurements, key=lambda item: item.id.value)
                ],
                "policy": policy.as_dict(),
                "factor": factor.as_dict(),
                "scope": scope.value,
                "scope_key": scope_key,
            }
        )
        total_energy = sum((item.energy_kwh for item in measurements), Decimal("0"))
        explicit_it = [
            item.it_energy_kwh for item in measurements if item.it_energy_kwh is not None
        ]
        explicit_facility = [
            item.facility_energy_kwh
            for item in measurements
            if item.facility_energy_kwh is not None
        ]
        assumptions: list[str] = []
        if explicit_it and explicit_facility:
            it_energy = sum(explicit_it, Decimal("0"))
            facility_energy = sum(explicit_facility, Decimal("0"))
            pue = (facility_energy / it_energy).quantize(GreenOpsValidator._QUANTUM)
            pue_source = "measured"
        else:
            pue = policy.default_pue
            facility_energy = total_energy
            it_energy = (facility_energy / pue).quantize(GreenOpsValidator._QUANTUM)
            pue_source = "policy-estimate"
            assumptions.append(
                f"PUE {pue} issued from site policy because complete IT/facility "
                "measurements were unavailable"
            )
        carbon_kg = (facility_energy * factor.grams_co2e_per_kwh / Decimal("1000")).quantize(
            GreenOpsValidator._QUANTUM
        )
        carbon = CarbonEstimate(
            facility_energy,
            carbon_kg,
            factor.code,
            factor.grams_co2e_per_kwh,
            factor.source_name,
            factor.source_uri,
            factor.period_start,
            factor.period_end,
            f"{scope.value}:{scope_key}",
        )
        energy_cost = (facility_energy * policy.energy_cost_per_kwh).quantize(
            GreenOpsValidator._QUANTUM
        )
        anomalies = self._detect_anomalies(tenant_id, site_code, measurements)
        forecasts = self._build_forecasts(
            tenant_id, site_code, site_measurements, policy, input_digest
        )
        candidates = self._build_candidates(
            tenant_id, site_code, site_measurements, policy, factor, input_digest
        )
        score = self._build_score(
            tenant_id,
            f"{scope.value}:{scope_key}",
            command.period_start,
            command.period_end,
            pue,
            measurements,
        )
        report = SustainabilityReport.create(
            tenant_id,
            site_code,
            f"{scope.value}:{scope_key}",
            command.period_start,
            command.period_end,
            total_energy,
            it_energy,
            facility_energy,
            pue,
            pue_source,
            energy_cost,
            policy.currency,
            carbon,
            score,
            len(measurements),
            sum(item.kind is MeasurementKind.OBSERVED for item in measurements),
            sum(item.kind is MeasurementKind.ESTIMATED for item in measurements),
            tuple(item.id.value for item in anomalies),
            tuple(item.id.value for item in forecasts),
            tuple(item.id.value for item in candidates),
            tuple(assumptions),
            input_digest,
        )
        existing = self._repository.find_report_by_reproducibility_key(
            tenant_id, report.reproducibility_key()
        )
        if existing is not None:
            return existing
        actor = command.actor or principal.subject
        with self._transaction_manager.begin() as unit_of_work:
            for anomaly in anomalies:
                self._repository.save_anomaly(anomaly)
                self._repository.append_event(
                    DomainEvent.create(
                        tenant_id, anomaly.id, "green.energy.anomaly.detected", anomaly.as_dict()
                    )
                )
            for forecast in forecasts:
                self._repository.save_forecast(forecast)
                self._repository.append_event(
                    DomainEvent.create(
                        tenant_id,
                        forecast.id,
                        "green.capacity.forecast.updated",
                        forecast.as_dict(),
                    )
                )
            for candidate in candidates:
                self._repository.save_candidate(candidate)
            self._repository.save_score(score)
            self._repository.save_report(report)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    report.id,
                    "green.report.generated",
                    {
                        "report_id": report.id.value,
                        "site_code": site_code,
                        "scope": report.scope,
                        "input_digest": input_digest,
                        "production_mutation": False,
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    actor,
                    "green.report.generated",
                    "green_sustainability_report",
                    report.id.value,
                    metadata={
                        "report": report.as_dict(),
                        "source": "greenops-analytics",
                        "production_mutation": False,
                    },
                )
            )
            unit_of_work.commit()
        return report

    def get_report(self, command: GetSustainabilityReportCommand) -> SustainabilityReport:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        report = self._repository.get_report(tenant_id, command.report_id)
        if report is None:
            raise NotFoundError("sustainability report does not exist")
        return report

    def list_reports(self, command: ListSustainabilityReportsCommand) -> SustainabilityReportPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_reports(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.site_code,
            command.scope,
        )

    def export_report(
        self, command: ExportSustainabilityReportCommand
    ) -> SustainabilityReportExport:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_EXPORT
        )
        report = self._repository.get_report(tenant_id, command.report_id)
        if report is None:
            raise NotFoundError("sustainability report does not exist")
        normalized = command.format.strip().lower()
        if normalized == "json":
            content = json.dumps(
                report.as_dict(), ensure_ascii=False, sort_keys=True, indent=2
            ).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        elif normalized == "csv":
            output = io.StringIO(newline="")
            writer = csv.DictWriter(
                output,
                fieldnames=(
                    "site_code",
                    "scope",
                    "period_start",
                    "period_end",
                    "total_energy_kwh",
                    "it_energy_kwh",
                    "facility_energy_kwh",
                    "pue",
                    "pue_source",
                    "energy_cost",
                    "currency",
                    "kilograms_co2e",
                    "carbon_factor_code",
                    "green_score",
                    "measurement_count",
                    "observed_measurement_count",
                    "estimated_measurement_count",
                ),
            )
            writer.writeheader()
            writer.writerow(
                {
                    "site_code": report.site_code,
                    "scope": report.scope,
                    "period_start": report.period_start.isoformat(),
                    "period_end": report.period_end.isoformat(),
                    "total_energy_kwh": str(report.total_energy_kwh),
                    "it_energy_kwh": str(report.it_energy_kwh),
                    "facility_energy_kwh": str(report.facility_energy_kwh),
                    "pue": str(report.pue),
                    "pue_source": report.pue_source,
                    "energy_cost": str(report.energy_cost),
                    "currency": report.currency,
                    "kilograms_co2e": str(report.carbon_estimate.kilograms_co2e),
                    "carbon_factor_code": report.carbon_estimate.factor_code,
                    "green_score": str(report.green_score.score),
                    "measurement_count": report.measurement_count,
                    "observed_measurement_count": report.observed_measurement_count,
                    "estimated_measurement_count": report.estimated_measurement_count,
                }
            )
            content = output.getvalue().encode("utf-8")
            content_type = "text/csv; charset=utf-8"
        else:
            raise ValidationError("GreenOps report export format must be json or csv")
        return SustainabilityReportExport(
            f"greenops-{report.site_code}-{report.id.value}.{normalized}", content_type, content
        )

    def list_anomalies(self, command: ListEnergyAnomaliesCommand) -> EnergyAnomalyPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_anomalies(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.severity,
            command.site_code,
        )

    def list_forecasts(self, command: ListCapacityForecastsCommand) -> CapacityForecastPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_forecasts(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.site_code,
            command.dimension,
        )

    def list_candidates(
        self, command: ListConsolidationCandidatesCommand
    ) -> ConsolidationCandidatePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_candidates(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.site_code,
            command.risk_level,
        )

    def list_scores(self, command: ListGreenScoresCommand) -> GreenScorePage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.GREENOPS_READ
        )
        return self._repository.list_scores(
            tenant_id, Pagination.from_values(command.limit, command.cursor), command.scope
        )

    def _select_factor(
        self, tenant_id: TenantId, code: str, start: date, end: date
    ) -> CarbonFactor:
        cursor: str | None = None
        matches: list[CarbonFactor] = []
        while True:
            page = self._repository.list_carbon_factors(
                tenant_id, Pagination.from_values(self._PAGE_SIZE, cursor), code, None
            )
            matches.extend(
                item for item in page.items if item.period_start <= end and item.period_end >= start
            )
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        if not matches:
            raise ValidationError("no carbon factor covers the requested period")
        return sorted(
            matches,
            key=lambda item: (item.period_start, item.created_at, item.id.value),
            reverse=True,
        )[0]

    def _all_measurements(
        self,
        tenant_id: TenantId,
        start: datetime,
        end: datetime,
        site_code: str,
        scope: str | None,
        scope_key: str | None,
    ) -> tuple[EnergyMeasurement, ...]:
        items: list[EnergyMeasurement] = []
        cursor: str | None = None
        while len(items) < self._MAX_ANALYTIC_MEASUREMENTS:
            page = self._repository.list_measurements(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_ANALYTIC_MEASUREMENTS - len(items)), cursor
                ),
                start,
                end,
                site_code,
                scope,
                scope_key,
                None,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items)
            cursor = page.next_cursor
        if cursor is not None:
            raise ValidationError("GreenOps analytic query exceeds 100000 measurements")
        return tuple(items)

    @staticmethod
    def _detect_anomalies(
        tenant_id: TenantId, site_code: str, measurements: tuple[EnergyMeasurement, ...]
    ) -> tuple[EnergyAnomaly, ...]:
        grouped: dict[tuple[EnergyScope, str], list[EnergyMeasurement]] = {}
        for item in measurements:
            grouped.setdefault((item.scope, item.scope_key), []).append(item)
        anomalies: list[EnergyAnomaly] = []
        for (scope, scope_key), values in grouped.items():
            ordered = sorted(values, key=lambda item: (item.period_end, item.id.value))
            if len(ordered) < 3:
                continue
            baseline = sum((item.energy_kwh for item in ordered[:-1]), Decimal("0")) / Decimal(
                len(ordered) - 1
            )
            latest = ordered[-1]
            if baseline > 0 and latest.energy_kwh >= baseline * Decimal("1.5"):
                ratio = latest.energy_kwh / baseline
                severity = Severity.CRITICAL if ratio >= Decimal("2") else Severity.WARNING
                anomalies.append(
                    EnergyAnomaly.create(
                        tenant_id,
                        site_code,
                        scope,
                        scope_key,
                        "energy-spike",
                        severity,
                        latest.energy_kwh,
                        baseline.quantize(GreenOpsValidator._QUANTUM),
                        (
                            "Latest energy usage is "
                            f"{ratio.quantize(Decimal('0.01'))} times the historical baseline"
                        ),
                    )
                )
        return tuple(anomalies)

    @staticmethod
    def _build_forecasts(
        tenant_id: TenantId,
        site_code: str,
        measurements: tuple[EnergyMeasurement, ...],
        policy: GreenOpsPolicy,
        digest: str,
    ) -> tuple[CapacityForecast, ...]:
        grouped: dict[tuple[EnergyScope, str, CapacityDimension], list[tuple[date, Decimal]]] = {}
        for measurement in measurements:
            for dimension, value in measurement.capacity_values().items():
                grouped.setdefault(
                    (measurement.scope, measurement.scope_key, dimension), []
                ).append((measurement.period_end.date(), value))
        results: list[CapacityForecast] = []
        for (scope, scope_key, dimension), samples in grouped.items():
            ordered = sorted(samples)
            if len(ordered) < policy.minimum_samples:
                continue
            first_date, first_value = ordered[0]
            last_date, last_value = ordered[-1]
            days = max(1, (last_date - first_date).days)
            growth = ((last_value - first_value) / Decimal(days)).quantize(
                GreenOpsValidator._QUANTUM
            )
            projected: date | None = None
            if growth > 0 and last_value < Decimal("100"):
                saturation_days = int(
                    ((Decimal("100") - last_value) / growth).to_integral_value(
                        rounding=ROUND_CEILING
                    )
                )
                projected = last_date + timedelta(days=saturation_days)
            confidence = min(Decimal("100"), Decimal(len(ordered) * 10))
            results.append(
                CapacityForecast.create(
                    tenant_id,
                    site_code,
                    scope,
                    scope_key,
                    dimension,
                    last_value,
                    max(Decimal("0"), growth),
                    projected,
                    confidence,
                    len(ordered),
                    digest,
                )
            )
        return tuple(results)

    @staticmethod
    def _build_candidates(
        tenant_id: TenantId,
        site_code: str,
        measurements: tuple[EnergyMeasurement, ...],
        policy: GreenOpsPolicy,
        factor: CarbonFactor,
        digest: str,
    ) -> tuple[ConsolidationCandidate, ...]:
        latest: dict[str, EnergyMeasurement] = {}
        for item in measurements:
            if item.scope is EnergyScope.ASSET and item.utilization_percent is not None:
                current = latest.get(item.scope_key)
                if current is None or item.period_end > current.period_end:
                    latest[item.scope_key] = item
        results: list[ConsolidationCandidate] = []
        for item in latest.values():
            if (
                item.utilization_percent is None
                or item.utilization_percent > policy.underutilized_percent
            ):
                continue
            duration_hours = Decimal(
                str(max(1.0, (item.period_end - item.period_start).total_seconds() / 3600))
            )
            annual_energy = (item.energy_kwh / duration_hours * Decimal("8760")).quantize(
                GreenOpsValidator._QUANTUM
            )
            saving_ratio = (Decimal("100") - item.utilization_percent) / Decimal("100")
            saving = (annual_energy * saving_ratio).quantize(GreenOpsValidator._QUANTUM)
            carbon_saving = (saving * factor.grams_co2e_per_kwh / Decimal("1000")).quantize(
                GreenOpsValidator._QUANTUM
            )
            results.append(
                ConsolidationCandidate.create(
                    tenant_id,
                    site_code,
                    item.scope,
                    item.scope_key,
                    ConsolidationAction.CONSOLIDATE,
                    (
                        f"Asset utilization {item.utilization_percent}% is below policy "
                        f"threshold {policy.underutilized_percent}%"
                    ),
                    saving,
                    carbon_saving,
                    Severity.WARNING,
                    digest,
                )
            )
        return tuple(results)

    @staticmethod
    def _build_score(
        tenant_id: TenantId,
        scope: str,
        start: date,
        end: date,
        pue: Decimal,
        measurements: tuple[EnergyMeasurement, ...],
    ) -> GreenScore:
        pue_component = max(
            Decimal("0"), min(Decimal("100"), Decimal("100") - (pue - Decimal("1")) * Decimal("80"))
        )
        capacities = [value for item in measurements for value in item.capacity_values().values()]
        max_capacity = max(capacities, default=Decimal("0"))
        capacity_component = max(Decimal("0"), Decimal("100") - max_capacity)
        observed = sum(item.kind is MeasurementKind.OBSERVED for item in measurements)
        data_quality = (Decimal(observed) / Decimal(len(measurements)) * Decimal("100")).quantize(
            GreenOpsValidator._PERCENT_QUANTUM
        )
        score = ((pue_component + capacity_component + data_quality) / Decimal("3")).quantize(
            GreenOpsValidator._PERCENT_QUANTUM
        )
        return GreenScore.create(
            tenant_id, scope, score, pue_component, capacity_component, data_quality, start, end
        )

    def _save_with_audit(
        self,
        aggregate: MeasurementSource | GreenOpsPolicy | CarbonFactor | EnergyMeasurement,
        actor: str,
        event_name: str,
        target_type: str,
        saver: Callable[[], None],
        metadata: dict[str, object] | None = None,
    ) -> None:
        tenant_id = aggregate.tenant_id
        aggregate_id = aggregate.id
        payload = dict(metadata or aggregate.as_dict())
        with self._transaction_manager.begin() as unit_of_work:
            saver()
            self._repository.append_event(
                DomainEvent.create(tenant_id, aggregate_id, event_name, payload)
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id, actor, event_name, target_type, aggregate_id.value, metadata=payload
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
