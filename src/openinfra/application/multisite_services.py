from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.discovery_services import (
    DiscoveryCollectorService,
    SubmitDiscoveryJobCommand,
)
from openinfra.application.edition_services import EditionRuntimeGuard
from openinfra.application.ports import (
    AuditRepository,
    DcimRepository,
    DiscoveryRepository,
    MultisiteReportPage,
    MultisiteRepository,
    RegionalDiscoveryRoutePage,
    SiteAccessGrantPage,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AccessDeniedError,
    AuditEvent,
    NotFoundError,
    Pagination,
    TenantId,
)
from openinfra.domain.dcim import Site
from openinfra.domain.discovery import (
    CollectorKind,
    CollectorStatus,
    DiscoveryCollector,
    DiscoveryScope,
)
from openinfra.domain.discovery_jobs import DiscoveryJob
from openinfra.domain.editions import FeatureCapability
from openinfra.domain.multisite import (
    MultisitePortfolioReport,
    MultisiteValidator,
    RegionalDiscoveryRoute,
    SiteAccessGrant,
    SiteAccessLevel,
    SitePortfolioEntry,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission


@dataclass(frozen=True, slots=True)
class UpsertSiteAccessCommand:
    tenant_id: str
    admin_token: str
    subject: str
    site_code: str
    access_level: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class RevokeSiteAccessCommand:
    tenant_id: str
    admin_token: str
    subject: str
    site_code: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class ListSiteAccessCommand:
    tenant_id: str
    admin_token: str
    subject: str | None = None
    site_code: str | None = None
    active_only: bool = True
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ListAccessibleSitesCommand:
    tenant_id: str
    admin_token: str
    subject: str | None = None
    required_level: str = "viewer"


@dataclass(frozen=True, slots=True)
class GenerateMultisiteReportCommand:
    tenant_id: str
    admin_token: str
    site_codes: tuple[str, ...] = ()
    subject: str | None = None
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetMultisiteReportCommand:
    tenant_id: str
    admin_token: str
    report_id: str


@dataclass(frozen=True, slots=True)
class ListMultisiteReportsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ConfigureRegionalDiscoveryRouteCommand:
    tenant_id: str
    admin_token: str
    region_code: str
    site_code: str
    vrf_code: str
    collector_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class DisableRegionalDiscoveryRouteCommand:
    tenant_id: str
    admin_token: str
    route_id: str
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class GetRegionalDiscoveryRouteCommand:
    tenant_id: str
    admin_token: str
    route_id: str


@dataclass(frozen=True, slots=True)
class ListRegionalDiscoveryRoutesCommand:
    tenant_id: str
    admin_token: str
    region_code: str | None = None
    site_code: str | None = None
    active_only: bool = True
    limit: int = 100
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class RouteRegionalDiscoveryJobCommand:
    tenant_id: str
    admin_token: str
    region_code: str
    site_code: str
    vrf_code: str
    job_type: str
    target: str
    idempotency_key: str
    max_attempts: int = 3
    actor: str | None = None


@dataclass(frozen=True, slots=True)
class RegionalDiscoveryDispatch:
    route: RegionalDiscoveryRoute
    job: DiscoveryJob

    def as_dict(self) -> dict[str, object]:
        return {"route": self.route.as_dict(), "job": self.job.as_dict()}


class MultisiteService:
    def __init__(
        self,
        repository: MultisiteRepository,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        edition_guard: EditionRuntimeGuard,
        discovery_repository: DiscoveryRepository,
        discovery_service: DiscoveryCollectorService,
    ) -> None:
        self._repository = repository
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._edition_guard = edition_guard
        self._discovery_repository = discovery_repository
        self._discovery_service = discovery_service

    def upsert_site_access(self, command: UpsertSiteAccessCommand) -> SiteAccessGrant:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_pro_multisite(tenant_id, principal.subject, command.site_code)
        site = self._dcim_repository.find_site(tenant_id, command.site_code)
        if site is None:
            raise NotFoundError("DCIM site not found")
        existing = self._repository.find_grant(tenant_id, command.subject, site.code.value)
        actor = command.actor or principal.subject
        grant = (
            SiteAccessGrant.create(
                tenant_id, command.subject, site.code.value, command.access_level, actor
            )
            if existing is None
            else existing.revise(command.access_level, actor)
        )
        self._save_grant(grant, actor, "multisite.site_access.upserted")
        return grant

    def revoke_site_access(self, command: RevokeSiteAccessCommand) -> SiteAccessGrant:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_pro_multisite(tenant_id, principal.subject, command.site_code)
        grant = self._repository.find_grant(tenant_id, command.subject, command.site_code)
        if grant is None:
            raise NotFoundError("site access grant not found")
        actor = command.actor or principal.subject
        revoked = grant.revoke(actor)
        self._save_grant(revoked, actor, "multisite.site_access.revoked")
        return revoked

    def list_site_access(self, command: ListSiteAccessCommand) -> SiteAccessGrantPage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_pro_multisite(tenant_id, principal.subject, command.site_code or "portfolio")
        return self._repository.list_grants(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.subject,
            command.site_code,
            command.active_only,
        )

    def list_accessible_sites(
        self, command: ListAccessibleSitesCommand
    ) -> tuple[dict[str, object], ...]:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_READ
        )
        subject = MultisiteValidator.subject(command.subject or principal.subject)
        if subject != principal.subject and Permission.MULTISITE_ADMIN not in principal.permissions:
            raise AccessDeniedError("cannot inspect another subject site scope")
        self._require_pro_multisite(tenant_id, principal.subject, subject)
        required = SiteAccessLevel.from_value(command.required_level)
        sites = self._accessible_sites(tenant_id, subject, required, principal.permissions)
        return tuple(self._site_dict(site) for site in sites)

    def generate_report(self, command: GenerateMultisiteReportCommand) -> MultisitePortfolioReport:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_REPORT
        )
        subject = MultisiteValidator.subject(command.subject or principal.subject)
        if subject != principal.subject and Permission.MULTISITE_ADMIN not in principal.permissions:
            raise AccessDeniedError("cannot generate a report for another subject")
        self._require_pro_multisite(tenant_id, principal.subject, subject)
        accessible = self._accessible_sites(
            tenant_id, subject, SiteAccessLevel.VIEWER, principal.permissions
        )
        by_code = {site.code.value: site for site in accessible}
        selected_codes = tuple(dict.fromkeys(code.strip().upper() for code in command.site_codes))
        selected = (
            accessible
            if not selected_codes
            else tuple(by_code[code] for code in selected_codes if code in by_code)
        )
        if selected_codes and len(selected) != len(selected_codes):
            raise AccessDeniedError("report includes an unknown or unauthorized site")
        entries = tuple(self._portfolio_entry(tenant_id, site) for site in selected)
        report = MultisitePortfolioReport.create(
            tenant_id,
            subject,
            command.actor or principal.subject,
            entries,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_report(report)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or principal.subject,
                    "multisite.report.generated",
                    "multisite_report",
                    report.id.value,
                    {"subject": subject, "site_codes": [item.site_code for item in entries]},
                )
            )
            unit_of_work.commit()
        return report

    def get_report(self, command: GetMultisiteReportCommand) -> MultisitePortfolioReport:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_REPORT
        )
        self._require_pro_multisite(tenant_id, principal.subject, command.report_id)
        report = self._repository.get_report(tenant_id, command.report_id)
        if report is None:
            raise NotFoundError("multisite report not found")
        if (
            report.requested_subject != principal.subject
            and Permission.MULTISITE_ADMIN not in principal.permissions
        ):
            raise AccessDeniedError("multisite report is outside the principal site scope")
        return report

    def list_reports(self, command: ListMultisiteReportsCommand) -> MultisiteReportPage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_REPORT
        )
        self._require_pro_multisite(tenant_id, principal.subject, "reports")
        subject = None if Permission.MULTISITE_ADMIN in principal.permissions else principal.subject
        return self._repository.list_reports(
            tenant_id, Pagination.from_values(command.limit, command.cursor), subject
        )

    def configure_regional_discovery_route(
        self, command: ConfigureRegionalDiscoveryRouteCommand
    ) -> RegionalDiscoveryRoute:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_enterprise_multisite(tenant_id, principal.subject, command.site_code)
        site = self._dcim_repository.find_site(tenant_id, command.site_code)
        if site is None:
            raise NotFoundError("DCIM site not found")
        candidate = RegionalDiscoveryRoute.create(
            tenant_id,
            command.region_code,
            site.code.value,
            command.vrf_code,
            command.collector_id,
            command.actor or principal.subject,
        )
        collector = self._discovery_repository.get_collector(tenant_id, command.collector_id)
        self._validate_regional_collector(collector, candidate)
        existing = self._repository.find_regional_route(
            tenant_id, candidate.region_code, candidate.site_code, candidate.vrf_code
        )
        route = (
            candidate
            if existing is None
            else existing.reassign(candidate.collector_id, command.actor or principal.subject)
        )
        self._save_regional_route(route, "multisite.regional_route.configured")
        return route

    def disable_regional_discovery_route(
        self, command: DisableRegionalDiscoveryRouteCommand
    ) -> RegionalDiscoveryRoute:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_enterprise_multisite(tenant_id, principal.subject, command.route_id)
        route = self._repository.get_regional_route(tenant_id, command.route_id)
        if route is None:
            raise NotFoundError("regional discovery route not found")
        disabled = route.disable(command.actor or principal.subject)
        self._save_regional_route(disabled, "multisite.regional_route.disabled")
        return disabled

    def get_regional_discovery_route(
        self, command: GetRegionalDiscoveryRouteCommand
    ) -> RegionalDiscoveryRoute:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_enterprise_multisite(tenant_id, principal.subject, command.route_id)
        route = self._repository.get_regional_route(tenant_id, command.route_id)
        if route is None:
            raise NotFoundError("regional discovery route not found")
        return route

    def list_regional_discovery_routes(
        self, command: ListRegionalDiscoveryRoutesCommand
    ) -> RegionalDiscoveryRoutePage:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_enterprise_multisite(
            tenant_id, principal.subject, command.site_code or command.region_code or "routes"
        )
        return self._repository.list_regional_routes(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.region_code,
            command.site_code,
            command.active_only,
        )

    def route_regional_discovery_job(
        self, command: RouteRegionalDiscoveryJobCommand
    ) -> RegionalDiscoveryDispatch:
        tenant_id, principal = self._authorize(
            command.tenant_id, command.admin_token, Permission.MULTISITE_ADMIN
        )
        self._require_enterprise_multisite(tenant_id, principal.subject, command.site_code)
        route = self._repository.find_regional_route(
            tenant_id, command.region_code, command.site_code, command.vrf_code
        )
        if route is None or not route.active:
            raise NotFoundError("active regional discovery route not found")
        collector = self._discovery_repository.get_collector(tenant_id, route.collector_id.value)
        self._validate_regional_collector(collector, route)
        job = self._discovery_service.submit_job(
            SubmitDiscoveryJobCommand(
                tenant_id=tenant_id.value,
                actor=command.actor or principal.subject,
                admin_token=command.admin_token,
                collector_id=route.collector_id.value,
                requested_scope=route.discovery_scope,
                job_type=command.job_type,
                target=command.target,
                idempotency_key=command.idempotency_key,
                max_attempts=command.max_attempts,
            )
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or principal.subject,
                    "multisite.regional_discovery.routed",
                    "discovery_job",
                    job.id.value,
                    {
                        "route_id": route.id.value,
                        "region_code": route.region_code,
                        "site_code": route.site_code,
                        "vrf_code": route.vrf_code,
                        "collector_id": route.collector_id.value,
                        "discovery_scope": route.discovery_scope,
                    },
                )
            )
            unit_of_work.commit()
        return RegionalDiscoveryDispatch(route, job)

    def _accessible_sites(
        self,
        tenant_id: TenantId,
        subject: str,
        required: SiteAccessLevel,
        permissions: frozenset[Permission],
    ) -> tuple[Site, ...]:
        sites = self._dcim_repository.list_sites(tenant_id)
        if Permission.MULTISITE_ADMIN in permissions:
            return sites
        grants: list[SiteAccessGrant] = []
        cursor: str | None = None
        while True:
            page = self._repository.list_grants(
                tenant_id, Pagination.from_values(500, cursor), subject, None, True
            )
            grants.extend(page.items)
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        allowed = {grant.site_code for grant in grants if grant.allows(required)}
        return tuple(site for site in sites if site.code.value in allowed)

    def _portfolio_entry(self, tenant_id: TenantId, site: Site) -> SitePortfolioEntry:
        buildings = self._dcim_repository.list_buildings(tenant_id, site.code.value)
        floors = 0
        rooms = 0
        racks = 0
        equipment = 0
        for building in buildings:
            building_rooms = self._dcim_repository.list_rooms(
                tenant_id, site.code.value, building.code.value
            )
            floors += len(
                self._dcim_repository.list_floors(tenant_id, site.code.value, building.code.value)
            )
            rooms += len(building_rooms)
            for room in building_rooms:
                room_racks = self._dcim_repository.list_racks_in_room(
                    tenant_id, site.code.value, building.code.value, room.code.value
                )
                racks += len(room_racks)
                equipment += len(
                    self._dcim_repository.list_equipment_in_room(
                        tenant_id, site.code.value, building.code.value, room.code.value
                    )
                )
        return SitePortfolioEntry(
            site_code=site.code.value,
            site_name=site.name.value,
            country=site.country,
            city=site.city,
            status=site.status.value,
            buildings=len(buildings),
            floors=floors,
            rooms=rooms,
            racks=racks,
            equipment=equipment,
        )

    @staticmethod
    def _site_dict(site: Site) -> dict[str, object]:
        return {
            "site_code": site.code.value,
            "site_name": site.name.value,
            "country": site.country,
            "city": site.city,
            "status": site.status.value,
        }

    def _save_grant(self, grant: SiteAccessGrant, actor: str, action: str) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_grant(grant)
            self._audit_repository.append(
                AuditEvent.record(
                    grant.tenant_id,
                    actor,
                    action,
                    "site_access_grant",
                    grant.id.value,
                    {
                        "subject": grant.subject,
                        "site_code": grant.site_code,
                        "access_level": grant.access_level.label,
                        "active": grant.active,
                    },
                )
            )
            unit_of_work.commit()

    def _authorize(
        self, tenant: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        tenant_id = TenantId.from_value(tenant)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, token, permission)
        )
        return tenant_id, principal

    def _save_regional_route(self, route: RegionalDiscoveryRoute, action: str) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_regional_route(route)
            self._audit_repository.append(
                AuditEvent.record(
                    route.tenant_id,
                    route.configured_by,
                    action,
                    "regional_discovery_route",
                    route.id.value,
                    {
                        "region_code": route.region_code,
                        "site_code": route.site_code,
                        "vrf_code": route.vrf_code,
                        "collector_id": route.collector_id.value,
                        "discovery_scope": route.discovery_scope,
                        "active": route.active,
                    },
                )
            )
            unit_of_work.commit()

    @staticmethod
    def _validate_regional_collector(
        collector: DiscoveryCollector | None, route: RegionalDiscoveryRoute
    ) -> None:
        if collector is None:
            raise NotFoundError("regional discovery collector not found")
        if collector.status is not CollectorStatus.ACTIVE:
            raise AccessDeniedError("regional discovery collector is not active")
        if collector.kind not in {CollectorKind.NETWORK_PROXY, CollectorKind.DATACENTER_PROXY}:
            raise AccessDeniedError("regional discovery route requires a regional proxy collector")
        if collector.endpoint_url is None:
            raise AccessDeniedError("regional discovery collector requires an HTTPS endpoint")
        if not collector.allows_scope(DiscoveryScope.from_value(route.discovery_scope)):
            raise AccessDeniedError("regional discovery collector does not authorize route scope")

    def _require_enterprise_multisite(self, tenant_id: TenantId, actor: str, target: str) -> None:
        self._edition_guard.require_feature(
            tenant_id,
            FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
            actor,
            "multisite_regional_discovery",
            target,
        )

    def _require_pro_multisite(self, tenant_id: TenantId, actor: str, target: str) -> None:
        self._edition_guard.require_feature(
            tenant_id,
            FeatureCapability.CENTRALIZED_MULTISITE,
            actor,
            "multisite",
            target,
        )
