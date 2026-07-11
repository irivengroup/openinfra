from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from openinfra import __version__
from openinfra.application.access_policy_services import (
    CreateAccessPolicyRuleCommand,
    DeactivateAccessPolicyRuleCommand,
    EvaluateAccessPolicyCommand,
    ListAccessPolicyRulesCommand,
)
from openinfra.application.audit_services import (
    ExportAuditEventsCommand,
    ListAuditEventsCommand,
    VerifyAuditIntegrityCommand,
)
from openinfra.application.certificate_pki_services import (
    AssessCertificatesCommand,
    GetCertificateCommand,
    ImportCertificateBundleCommand,
    ListCertificateEndpointsCommand,
    ListCertificatesCommand,
    ObserveCertificateEndpointCommand,
    RetireCertificateCommand,
)
from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.dcim_services import (
    ConnectDcimCableCommand,
    CreateDcimBuildingCommand,
    CreateDcimFloorCommand,
    CreateDcimRoomCommand,
    CreateDcimSiteCommand,
    CreateDcimZoneCommand,
    DcimTopologyCatalogCommand,
    DefineCoolingZoneCommand,
    DefineDcimPortCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    DeleteDcimBuildingCommand,
    DeleteDcimFloorCommand,
    DeleteDcimRoomCommand,
    DeleteDcimSiteCommand,
    DeleteDcimZoneCommand,
    DeleteRackCommand,
    GenerateEquipmentLocatorCommand,
    GetDcimBuildingCommand,
    GetDcimFloorCommand,
    GetDcimRoomCommand,
    GetDcimSiteCommand,
    GetDcimZoneCommand,
    GetRackCommand,
    ListDcimBuildingsCommand,
    ListDcimFloorsCommand,
    ListDcimRoomsCommand,
    ListDcimSitesCommand,
    ListDcimZonesCommand,
    ListRacksCommand,
    LocateEquipmentCommand,
    RackCapacityCommand,
    RackEnergyCoolingCapacityCommand,
    RenderDigitalTwinCommand,
    RenderRackElevationCommand,
    RenderRoomPlanCommand,
    ReserveEquipmentPowerCommand,
    TraceDcimCableCommand,
    UpdateDcimBuildingCommand,
    UpdateDcimFloorCommand,
    UpdateDcimRoomCommand,
    UpdateDcimSiteCommand,
    UpdateDcimZoneCommand,
    UpdateRackCommand,
    VerifyEquipmentScanCommand,
)
from openinfra.application.dependency_graph_services import (
    AnalyzeDependencyImpactCommand,
    AnalyzeDependencySpofCommand,
    ExportDependencyGraphCommand,
    FindDependencyPathCommand,
    TraverseDependencyGraphCommand,
)
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
    BuildEnterpriseAgentBootstrapPlanCommand,
    BuildLocalDiscoveryPlanCommand,
    ClaimDiscoveryJobCommand,
    CompleteDiscoveryJobCommand,
    CreateDiscoveryIntegrationProfileCommand,
    CreateDiscoveryProtocolProfileCommand,
    DisableCollectorCommand,
    DisableDiscoveryIntegrationProfileCommand,
    DisableDiscoveryProtocolProfileCommand,
    EnrollDiscoveryProxyCommand,
    FailDiscoveryJobCommand,
    GetDiscoveryEvidenceCommand,
    GetDiscoveryIntegrationProfileCommand,
    GetDiscoveryJobCommand,
    GetDiscoveryProtocolProfileCommand,
    GetDiscoveryReconciliationCommand,
    HeartbeatCollectorCommand,
    ListCollectorsCommand,
    ListDiscoveryEvidenceCommand,
    ListDiscoveryIntegrationProfilesCommand,
    ListDiscoveryJobsCommand,
    ListDiscoveryProtocolProfilesCommand,
    ListDiscoveryReconciliationsCommand,
    ReconcileDiscoveryEvidenceCommand,
    RegisterCollectorCommand,
    RenewDiscoveryJobLeaseCommand,
    ReplayDiscoveryDeadLetterJobCommand,
    ResolveDiscoveryReconciliationCommand,
    SubmitDiscoveryEvidenceCommand,
    SubmitDiscoveryJobCommand,
    UpdateDiscoveryIntegrationProfileCommand,
    UpdateDiscoveryProtocolProfileCommand,
)
from openinfra.application.edition_services import (
    CheckFeatureCommand,
    CheckQuotaCommand,
)
from openinfra.application.export_services import (
    GetExportArtifactChunkCommand,
    GetExportArtifactCommand,
    GetExportJobCommand,
    RequestExportCommand,
    RunExportJobCommand,
)
from openinfra.application.external_itsm_services import (
    BuildFreshserviceAssetSyncPlanCommand,
    BuildGlpiAssetSyncPlanCommand,
    BuildJiraServiceManagementAssetSyncPlanCommand,
    BuildOpenServiceCmdbSyncPlanCommand,
    BuildServiceNowCiSyncPlanCommand,
    ValidateFreshserviceConnectorCommand,
    ValidateGlpiConnectorCommand,
    ValidateJiraServiceManagementConnectorCommand,
    ValidateOpenServiceConnectorCommand,
    ValidateServiceNowConnectorCommand,
)
from openinfra.application.field_operation_services import (
    AcquireInterventionLockCommand,
    AttachFieldEvidenceCommand,
    CancelFieldOperationCommand,
    CompleteFieldOperationCommand,
    CreateOfflineSyncPackageCommand,
    GenerateFieldOperationSheetCommand,
    GetFieldOperationSheetCommand,
    GetOfflineSyncPackageCommand,
    ListFieldOperationSheetsCommand,
    ListOfflineSyncPackagesCommand,
    RecordFieldChecklistCommand,
    ReleaseInterventionLockCommand,
    StartFieldOperationCommand,
    SynchronizeOfflinePackageCommand,
    ValidateFieldEvidenceCommand,
    VerifyFieldQrCommand,
)
from openinfra.application.finops_services import (
    CancelCostImportJobCommand,
    CloseFinancialPeriodCommand,
    CreateCostAllocationRuleCommand,
    ExportFinOpsReportCommand,
    GenerateFinOpsReportCommand,
    GetCostImportJobCommand,
    GetFinOpsReportCommand,
    ListCostAllocationRulesCommand,
    ListCostAnomaliesCommand,
    ListCostImportJobsCommand,
    ListCostRecordsCommand,
    ListFinancialPeriodsCommand,
    ListFinOpsBudgetsCommand,
    ListFinOpsForecastsCommand,
    ListFinOpsReportsCommand,
    RunCostImportJobCommand,
    SubmitCostImportJobCommand,
    UpsertFinOpsBudgetCommand,
)
from openinfra.application.flow_matrix_services import (
    CompareFlowMatrixCommand,
    ListFlowDeclarationsCommand,
    ListFlowObservationsCommand,
    RetireFlowDeclarationCommand,
    SubmitFlowObservationCommand,
    UpsertFlowDeclarationCommand,
)
from openinfra.application.greenops_services import (
    CreateCarbonFactorCommand,
    CreateMeasurementSourceCommand,
    ExportSustainabilityReportCommand,
    GenerateSustainabilityReportCommand,
    GetGreenOpsPolicyCommand,
    GetSustainabilityReportCommand,
    IngestEnergyMeasurementCommand,
    ListCapacityForecastsCommand,
    ListCarbonFactorsCommand,
    ListConsolidationCandidatesCommand,
    ListEnergyAnomaliesCommand,
    ListEnergyMeasurementsCommand,
    ListGreenScoresCommand,
    ListMeasurementSourcesCommand,
    ListSustainabilityReportsCommand,
    UpsertGreenOpsPolicyCommand,
)
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.import_services import (
    BulkImportDatasetCommand,
    BulkImportRollbackCommand,
    ImportDatasetCommand,
    MigrationGuideCommand,
    MigrationTemplateCommand,
    PlanMigrationCommand,
)
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineAsnCommand,
    DefineBgpPeerCommand,
    DefineIpAggregateCommand,
    DefineIpPrefixCommand,
    DefineIpRangeCommand,
    DefineVlanCommand,
    DefineVlanGroupCommand,
    DefineVrfCommand,
    DefineVxlanVniCommand,
    DetectIpamConflictsCommand,
    IpamCapacityCommand,
    IpamNetworkBindingsCommand,
    IpamReservationWizardCommand,
    IpamSearchCommand,
    IpamTopologyCommand,
    IpamUiDashboardCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
    PreviewDdiReservationCommand,
    RegisterIpAddressCommand,
)
from openinfra.application.it_resources_management_quality_services import (
    EvaluateItrmObjectQualityCommand,
    ItrmQualitySummaryCommand,
)
from openinfra.application.it_resources_management_services import (
    CreateSourceRelationCommand,
    GetSourceObjectAsOfCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectAuditCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    ReconcileSourceObjectCommand,
    UpsertSourceObjectCommand,
)
from openinfra.application.itam_services import (
    AddThirdPartySupportCommand,
    CreateItamOrganizationCommand,
    CreateItamPartnerCommand,
    CreateItamTenantCommand,
    DeleteItamOrganizationCommand,
    DeleteItamPartnerCommand,
    DeleteItamTenantCommand,
    GetAssetSupportCoverageReportCommand,
    GetAssetSupportProfileCommand,
    GetItamOrganizationCommand,
    GetItamPartnerCommand,
    GetItamTenantCommand,
    GetSoftwareLicenseCommand,
    GetSoftwareLicenseComplianceCommand,
    ListItamOrganizationsCommand,
    ListItamPartnersCommand,
    ListItamTenantsCommand,
    RegisterManufacturerSupportCommand,
    RegisterSoftwareLicenseCommand,
    UpdateItamOrganizationCommand,
    UpdateItamPartnerCommand,
    UpdateItamTenantCommand,
    UpdateSoftwareLicenseAssignmentCommand,
)
from openinfra.application.network_config_compliance_services import (
    AssessNetworkConfigComplianceCommand,
    ListNetworkConfigBaselinesCommand,
    ListNetworkConfigObservationsCommand,
    RetireNetworkConfigBaselineCommand,
    SubmitNetworkConfigObservationCommand,
    UpsertNetworkConfigBaselineCommand,
)
from openinfra.application.search_services import GlobalSearchCommand
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
)
from openinfra.application.simulation_services import (
    CancelSimulationScenarioCommand,
    CompareSimulationReportsCommand,
    CreateSimulationScenarioCommand,
    GetSimulationReportCommand,
    GetSimulationScenarioCommand,
    ListSimulationComparisonsCommand,
    ListSimulationReportsCommand,
    ListSimulationScenariosCommand,
    RunSimulationScenarioCommand,
)
from openinfra.application.source_governance_services import (
    CreateSourceGovernanceRuleCommand,
    DeactivateSourceGovernanceRuleCommand,
    EvaluateSourceGovernanceCommand,
    ListSourceGovernanceRulesCommand,
)
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.common import AccessDeniedError, OpenInfraError, ValidationError
from openinfra.domain.countries import CountryCatalog
from openinfra.domain.security import AuthenticatedPrincipal, Permission
from openinfra.infrastructure.runtime_config import RuntimeDatabaseDsnResolver


class JsonHttpResponder:
    def __init__(self, handler: BaseHTTPRequestHandler) -> None:
        self._handler = handler

    def send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self._handler.send_response(status.value)
        self._handler.send_header("Content-Type", "application/json; charset=utf-8")
        self._handler.send_header("Content-Length", str(len(body)))
        self._handler.end_headers()
        self._handler.wfile.write(body)


class TextHttpResponder:
    def __init__(self, handler: BaseHTTPRequestHandler) -> None:
        self._handler = handler

    def send(self, status: HTTPStatus, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self._handler.send_response(status.value)
        self._handler.send_header("Content-Type", content_type)
        self._handler.send_header("Content-Length", str(len(payload)))
        self._handler.end_headers()
        self._handler.wfile.write(payload)


class BinaryHttpResponder:
    def __init__(self, handler: BaseHTTPRequestHandler) -> None:
        self._handler = handler

    def send(
        self,
        status: HTTPStatus,
        body: bytes,
        content_type: str,
        filename: str,
    ) -> None:
        self._handler.send_response(status.value)
        self._handler.send_header("Content-Type", content_type)
        self._handler.send_header("Content-Length", str(len(body)))
        self._handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self._handler.end_headers()
        self._handler.wfile.write(body)


class OpenApiDocumentProvider:
    def __init__(self, explicit_path: str | None = None) -> None:
        self._explicit_path = explicit_path

    def read_yaml(self) -> str:
        for candidate in self._candidate_paths():
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        raise OpenInfraError("OpenAPI document is unavailable; expected docs/api/openapi.yaml")

    def _candidate_paths(self) -> tuple[Path, ...]:
        configured = self._explicit_path or os.environ.get("OPENINFRA_OPENAPI_PATH")
        candidates: list[Path] = []
        if configured:
            candidates.append(Path(configured))
        candidates.extend(
            (
                Path.cwd() / "docs/api/openapi.yaml",
                Path(__file__).resolve().parents[1] / "api/openapi.yaml",
                Path(__file__).resolve().parents[3] / "docs/api/openapi.yaml",
            )
        )
        return tuple(candidates)


class ApiDocumentationRenderer:
    @staticmethod
    def swagger_html(openapi_url: str) -> str:
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>OpenInfra API - Swagger UI</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui.css\">
</head>
<body>
  <div id=\"swagger-ui\"></div>
  <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
  <script>
    window.ui = SwaggerUIBundle({{
      url: \"{openapi_url}\",
      dom_id: '#swagger-ui',
      deepLinking: true,
      layout: 'BaseLayout'
    }});
  </script>
</body>
</html>"""

    @staticmethod
    def redoc_html(openapi_url: str) -> str:
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>OpenInfra API - ReDoc</title>
</head>
<body>
  <redoc spec-url=\"{openapi_url}\"></redoc>
  <script src=\"https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js\"></script>
</body>
</html>"""


class OpenInfraRequestHandler(BaseHTTPRequestHandler):
    server: OpenInfraThreadingServer

    def log_message(self, _format: str, *args: object) -> None:
        return None

    def do_GET(self) -> None:
        responder = JsonHttpResponder(self)
        text_responder = TextHttpResponder(self)
        binary_responder = BinaryHttpResponder(self)
        parsed = urlparse(self.path)
        status: Any
        page: Any
        report: Any
        result: Any
        route = self._canonical_route(parsed.path)
        if route in ("/", "/api/v1"):
            responder.send(HTTPStatus.OK, self.server.discovery_document())
            return
        if route in ("/docs", "/swagger"):
            text_responder.send(
                HTTPStatus.OK,
                ApiDocumentationRenderer.swagger_html("/openapi.yaml"),
                "text/html; charset=utf-8",
            )
            return
        if route == "/redoc":
            text_responder.send(
                HTTPStatus.OK,
                ApiDocumentationRenderer.redoc_html("/openapi.yaml"),
                "text/html; charset=utf-8",
            )
            return
        if route in ("/openapi.yaml", "/api/v1/openapi.yaml"):
            try:
                text_responder.send(
                    HTTPStatus.OK,
                    self.server.openapi_document_provider.read_yaml(),
                    "application/yaml; charset=utf-8",
                )
            except OpenInfraError as exc:
                responder.send(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
            return
        if route == "/health":
            responder.send(HTTPStatus.OK, {"status": "ok"})
            return
        if route == "/ready":
            status = self.server.application.readiness_probe.check()
            http_status = HTTPStatus.OK if status.ready else HTTPStatus.SERVICE_UNAVAILABLE
            responder.send(http_status, status.as_dict())
            return
        if route == "/api/v1/version":
            responder.send(HTTPStatus.OK, {"version": __version__})
            return
        if route == "/api/v1/reference/countries":
            responder.send(HTTPStatus.OK, CountryCatalog.groups_as_dict())
            return
        if route == "/api/v1/database/schema":
            status = self.server.application.schema_status_provider.status_as_dict()
            http_status = HTTPStatus.OK if status.get("ready") is True else HTTPStatus.CONFLICT
            responder.send(http_status, status)
            return
        if route == "/api/v1/editions/policies":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                responder.send(
                    HTTPStatus.OK,
                    {"items": list(self.server.application.edition_query_service.policies())},
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/editions/feature-check":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                decision = self.server.application.edition_query_service.feature_decision(
                    CheckFeatureCommand(
                        tenant_id=tenant_id,
                        edition=self._first_query_value(query, "edition"),
                        capability=self._first_query_value(query, "capability"),
                    )
                )
                responder.send(HTTPStatus.OK, decision.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/editions/quota-check":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                quota_decision = self.server.application.edition_query_service.quota_decision(
                    CheckQuotaCommand(
                        tenant_id=tenant_id,
                        edition=self._first_query_value(query, "edition"),
                        resource=self._first_query_value(query, "resource"),
                        requested_increment=int(
                            self._first_query_value(query, "requested_increment", "1")
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, quota_decision.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/search/global":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.RSOT_READ)
                    actor = principal.subject
                result = self.server.application.global_search_service.search(
                    GlobalSearchCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        admin_token=self._bearer_token(),
                        query=self._first_query_value(query, "query"),
                        limit=int(self._first_query_value(query, "limit", "5")),
                        include_inactive_discovery=(
                            self._first_query_value(query, "include_inactive_discovery", "false")
                            == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/organizations":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                organization_catalog = (
                    self.server.application.itam_support_service.list_organizations(
                        ListItamOrganizationsCommand(
                            tenant_id=tenant_id,
                            admin_token=self._bearer_token(),
                            include_retired=(
                                self._first_query_value(query, "include_retired", "false") == "true"
                            ),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, organization_catalog.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/organization":
            try:
                query = parse_qs(parsed.query)
                scope_tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(scope_tenant_id, Permission.ITAM_READ)
                organization = self.server.application.itam_support_service.get_organization(
                    GetItamOrganizationCommand(
                        organization_id=self._first_query_value(query, "organization_id"),
                        scope_tenant_id=scope_tenant_id,
                        admin_token=self._bearer_token(),
                    )
                )
                responder.send(HTTPStatus.OK, organization.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/partners":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                partner_catalog = self.server.application.itam_support_service.list_partners(
                    ListItamPartnersCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                        organization_id=self._optional_query_value(query, "organization_id"),
                        kind=self._optional_query_value(query, "kind"),
                        include_retired=(
                            self._first_query_value(query, "include_retired", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, partner_catalog.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/partner":
            try:
                query = parse_qs(parsed.query)
                scope_tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(scope_tenant_id, Permission.ITAM_READ)
                partner = self.server.application.itam_support_service.get_partner(
                    GetItamPartnerCommand(
                        organization_id=self._first_query_value(query, "organization_id"),
                        partner_id=self._first_query_value(query, "partner_id"),
                        scope_tenant_id=scope_tenant_id,
                        admin_token=self._bearer_token(),
                    )
                )
                responder.send(HTTPStatus.OK, partner.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/tenants":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                tenant_catalog = self.server.application.itam_support_service.list_tenants(
                    ListItamTenantsCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                        include_retired=(
                            self._first_query_value(query, "include_retired", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, tenant_catalog.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/tenant":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                tenant = self.server.application.itam_support_service.get_tenant(
                    GetItamTenantCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                    )
                )
                responder.send(HTTPStatus.OK, tenant.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/support-profile":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                profile = self.server.application.itam_support_service.get_support_profile(
                    GetAssetSupportProfileCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                        asset_tag=self._first_query_value(query, "asset_tag"),
                    )
                )
                responder.send(HTTPStatus.OK, profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except OpenInfraError as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/support-coverage":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                report = self.server.application.itam_support_service.get_support_coverage_report(
                    GetAssetSupportCoverageReportCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                        asset_tag=self._first_query_value(query, "asset_tag"),
                        as_of=self._optional_query_value(query, "as_of"),
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except OpenInfraError as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/software-license":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                license_ = self.server.application.itam_support_service.get_software_license(
                    GetSoftwareLicenseCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                        license_reference=self._first_query_value(query, "license_reference"),
                    )
                )
                responder.send(HTTPStatus.OK, license_.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except OpenInfraError as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/itam/software-license/compliance":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.ITAM_READ)
                report = (
                    self.server.application.itam_support_service.get_software_license_compliance(
                        GetSoftwareLicenseComplianceCommand(
                            tenant_id=tenant_id,
                            admin_token=self._bearer_token(),
                            license_reference=self._first_query_value(query, "license_reference"),
                            as_of=self._optional_query_value(query, "as_of"),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except OpenInfraError as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/security/tokens":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                page = self.server.application.security_service.list_tokens(
                    ListTokensCommand(
                        tenant_id=tenant_id,
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_inactive=(
                            self._first_query_value(query, "include_inactive", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/access/rules":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.access_policy_service.list_rules(
                    ListAccessPolicyRulesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_inactive=(
                            self._first_query_value(query, "include_inactive", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/audit/events":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.audit_service.list_events(
                    ListAuditEventsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        actor=query.get("actor", [None])[0],
                        action=query.get("action", [None])[0],
                        target_type=query.get("target_type", [None])[0],
                        target_id=query.get("target_id", [None])[0],
                        severity=query.get("severity", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/audit/integrity":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.audit_service.verify_integrity(
                    VerifyAuditIntegrityCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "500")),
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/job":
            try:
                query = parse_qs(parsed.query)
                discovery_job = self.server.application.discovery_service.get_job(
                    GetDiscoveryJobCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        job_id=self._first_query_value(query, "job_id"),
                    )
                )
                responder.send(HTTPStatus.OK, discovery_job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.discovery_service.list_jobs(
                    ListDiscoveryJobsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        status=query.get("status", [None])[0],
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/evidence":
            try:
                query = parse_qs(parsed.query)
                evidence = self.server.application.discovery_service.get_evidence(
                    GetDiscoveryEvidenceCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        evidence_id=self._first_query_value(query, "evidence_id"),
                    )
                )
                responder.send(HTTPStatus.OK, evidence.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/evidence-list":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.discovery_service.list_evidence(
                    ListDiscoveryEvidenceCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        object_key=query.get("object_key", [None])[0],
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/reconciliation":
            try:
                query = parse_qs(parsed.query)
                case = self.server.application.discovery_service.get_reconciliation(
                    GetDiscoveryReconciliationCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        case_id=self._first_query_value(query, "case_id"),
                    )
                )
                responder.send(HTTPStatus.OK, case.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/reconciliation-list":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.discovery_service.list_reconciliations(
                    ListDiscoveryReconciliationsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        status=query.get("status", [None])[0],
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/protocol-profiles":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.discovery_service.list_protocol_profiles(
                    ListDiscoveryProtocolProfilesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_inactive=(
                            self._first_query_value(query, "include_inactive", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/protocol-profile":
            try:
                query = parse_qs(parsed.query)
                protocol_profile = self.server.application.discovery_service.get_protocol_profile(
                    GetDiscoveryProtocolProfileCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        profile_id=self._first_query_value(query, "profile_id"),
                    )
                )
                responder.send(HTTPStatus.OK, protocol_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/integration-profiles":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.discovery_service.list_integration_profiles(
                    ListDiscoveryIntegrationProfilesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_inactive=(
                            self._first_query_value(query, "include_inactive", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/integration-profile":
            try:
                query = parse_qs(parsed.query)
                integration_profile = (
                    self.server.application.discovery_service.get_integration_profile(
                        GetDiscoveryIntegrationProfileCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            profile_id=self._first_query_value(query, "profile_id"),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, integration_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/collectors":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.discovery_service.list_collectors(
                    ListCollectorsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_inactive=(
                            self._first_query_value(query, "include_inactive", "false") == "true"
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/report":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.import_service.get_report(
                    self._first_query_value(query, "tenant_id"),
                    self._first_query_value(query, "job_id"),
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/bulk-report":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.import_service.get_bulk_report(
                    self._first_query_value(query, "tenant_id"),
                    self._first_query_value(query, "job_id"),
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/bulk-checkpoint":
            try:
                query = parse_qs(parsed.query)
                checkpoint = self.server.application.import_service.get_bulk_checkpoint(
                    self._first_query_value(query, "tenant_id"),
                    self._first_query_value(query, "job_id"),
                )
                responder.send(HTTPStatus.OK, checkpoint.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/bulk-progress":
            try:
                query = parse_qs(parsed.query)
                progress = self.server.application.import_service.get_bulk_progress(
                    self._first_query_value(query, "tenant_id"),
                    self._first_query_value(query, "job_id"),
                )
                responder.send(HTTPStatus.OK, progress.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/migration-template":
            try:
                query = parse_qs(parsed.query)
                template = self.server.application.import_service.get_migration_template(
                    MigrationTemplateCommand(self._first_query_value(query, "source"))
                )
                responder.send(HTTPStatus.OK, template.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/migration-guide":
            try:
                query = parse_qs(parsed.query)
                guide = self.server.application.import_service.get_migration_guide(
                    MigrationGuideCommand(self._first_query_value(query, "source"))
                )
                responder.send(HTTPStatus.OK, guide.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/migration-report":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.import_service.get_migration_plan(
                    self._first_query_value(query, "tenant_id"),
                    self._first_query_value(query, "job_id"),
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/exports/jobs":
            try:
                query = parse_qs(parsed.query)
                job = self.server.application.export_service.get_export_job(
                    GetExportJobCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        job_id=self._first_query_value(query, "job_id"),
                    )
                )
                responder.send(HTTPStatus.OK, job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/exports/artifact":
            try:
                query = parse_qs(parsed.query)
                download = self.server.application.export_service.get_export_artifact(
                    GetExportArtifactCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        job_id=self._first_query_value(query, "job_id"),
                    )
                )
                artifact = download.job.artifact
                if artifact is None:
                    raise OpenInfraError("export artifact metadata is unavailable")
                binary_responder.send(
                    HTTPStatus.OK,
                    download.content,
                    artifact.media_type,
                    artifact.filename,
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/exports/artifact-chunk":
            try:
                query = parse_qs(parsed.query)
                chunk_download = self.server.application.export_service.get_export_artifact_chunk(
                    GetExportArtifactChunkCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        job_id=self._first_query_value(query, "job_id"),
                        offset=int(self._first_query_value(query, "offset", "0")),
                        size=int(self._first_query_value(query, "size", "65536")),
                    )
                )
                responder.send(HTTPStatus.OK, chunk_download.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/network-config/baselines":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.network_config_compliance_service.list_baselines(
                    ListNetworkConfigBaselinesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/network-config/observations":
            try:
                query = parse_qs(parsed.query)
                result = (
                    self.server.application.network_config_compliance_service.list_observations(
                        ListNetworkConfigObservationsCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            limit=int(self._first_query_value(query, "limit", "100")),
                            cursor=query.get("cursor", [None])[0],
                            device_object_key=query.get("device_object_key", [None])[0],
                            platform=query.get("platform", [None])[0],
                            observed_before=query.get("observed_before", [None])[0],
                        )
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/network-config/assessment":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.network_config_compliance_service.assess(
                    AssessNetworkConfigComplianceCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=self._first_query_value(query, "actor", "api"),
                        baseline_code=query.get("baseline_code", [None])[0],
                        as_of=query.get("as_of", [None])[0],
                        status=query.get("status", [None])[0],
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.certificate_pki_service.list_certificates(
                    ListCertificatesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        in {"1", "true", "yes"},
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.certificate_pki_service.get_certificate(
                    GetCertificateCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        fingerprint=self._first_query_value(query, "fingerprint"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates/endpoints":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.certificate_pki_service.list_endpoints(
                    ListCertificateEndpointsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        certificate_fingerprint=query.get("certificate_fingerprint", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates/assessment":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.certificate_pki_service.assess(
                    AssessCertificatesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        as_of=query.get("as_of", [None])[0],
                        critical_days=int(self._first_query_value(query, "critical_days", "7")),
                        warning_days=int(self._first_query_value(query, "warning_days", "30")),
                        health=query.get("health", [None])[0],
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/flows/declarations":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.flow_matrix_service.list_declarations(
                    ListFlowDeclarationsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        in {"1", "true", "yes"},
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/flows/observations":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.flow_matrix_service.list_observations(
                    ListFlowObservationsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        window_start=self._first_query_value(query, "window_start"),
                        window_end=self._first_query_value(query, "window_end"),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        source=query.get("source", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/flows/matrix":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.flow_matrix_service.compare(
                    CompareFlowMatrixCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        window_start=query.get("window_start", [None])[0],
                        window_end=query.get("window_end", [None])[0],
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        status=query.get("status", [None])[0],
                        source=query.get("source", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/greenops/measurement-sources":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_sources(
                    ListMeasurementSourcesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        active_only=self._first_query_value(query, "active_only", "false").lower()
                        in {"1", "true", "yes"},
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/policies/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.get_policy(
                    GetGreenOpsPolicyCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        site_code=self._first_query_value(query, "site_code"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/carbon-factors":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_carbon_factors(
                    ListCarbonFactorsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        code=query.get("code", [None])[0],
                        region=query.get("region", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/energy-measurements":
            try:
                query = parse_qs(parsed.query)
                start = query.get("period_start", [None])[0]
                end = query.get("period_end", [None])[0]
                result = self.server.application.greenops_service.list_measurements(
                    ListEnergyMeasurementsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        period_start=(
                            None
                            if start is None
                            else datetime.fromisoformat(start.replace("Z", "+00:00"))
                        ),
                        period_end=(
                            None
                            if end is None
                            else datetime.fromisoformat(end.replace("Z", "+00:00"))
                        ),
                        site_code=query.get("site_code", [None])[0],
                        scope=query.get("scope", [None])[0],
                        scope_key=query.get("scope_key", [None])[0],
                        kind=query.get("kind", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/reports":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_reports(
                    ListSustainabilityReportsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        site_code=query.get("site_code", [None])[0],
                        scope=query.get("scope", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/reports/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.get_report(
                    GetSustainabilityReportCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        report_id=self._first_query_value(query, "report_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/reports/export":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.export_report(
                    ExportSustainabilityReportCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        report_id=self._first_query_value(query, "report_id"),
                        format=self._first_query_value(query, "format", "json"),
                    )
                )
                BinaryHttpResponder(self).send(
                    HTTPStatus.OK, result.content, result.content_type, result.filename
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/anomalies":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_anomalies(
                    ListEnergyAnomaliesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        severity=query.get("severity", [None])[0],
                        site_code=query.get("site_code", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/capacity-forecasts":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_forecasts(
                    ListCapacityForecastsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        site_code=query.get("site_code", [None])[0],
                        dimension=query.get("dimension", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/consolidation-candidates":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_candidates(
                    ListConsolidationCandidatesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        site_code=query.get("site_code", [None])[0],
                        risk_level=query.get("risk_level", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/green-scores":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.greenops_service.list_scores(
                    ListGreenScoresCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        scope=query.get("scope", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/finops/allocation-rules":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_allocation_rules(
                    ListCostAllocationRulesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        active_only=self._first_query_value(query, "active_only", "false").lower()
                        in {"1", "true", "yes"},
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/import-jobs":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_import_jobs(
                    ListCostImportJobsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        status=query.get("status", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/import-jobs/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.get_import_job(
                    GetCostImportJobCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        job_id=self._first_query_value(query, "job_id"),
                        include_records=self._first_query_value(
                            query, "include_records", "false"
                        ).lower()
                        in {"1", "true", "yes"},
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/cost-records":
            try:
                query = parse_qs(parsed.query)
                start = query.get("period_start", [None])[0]
                end = query.get("period_end", [None])[0]
                result = self.server.application.finops_service.list_cost_records(
                    ListCostRecordsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        period_start=None if start is None else date.fromisoformat(start),
                        period_end=None if end is None else date.fromisoformat(end),
                        currency=query.get("currency", [None])[0],
                        category=query.get("category", [None])[0],
                        source=query.get("source", [None])[0],
                        quality_status=query.get("quality_status", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/budgets":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_budgets(
                    ListFinOpsBudgetsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        dimension=query.get("dimension", [None])[0],
                        target=query.get("target", [None])[0],
                        currency=query.get("currency", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/periods":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_periods(
                    ListFinancialPeriodsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        status=query.get("status", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/reports":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_reports(
                    ListFinOpsReportsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        kind=query.get("kind", [None])[0],
                        currency=query.get("currency", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/reports/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.get_report(
                    GetFinOpsReportCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        report_id=self._first_query_value(query, "report_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/reports/export":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.export_report(
                    ExportFinOpsReportCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        report_id=self._first_query_value(query, "report_id"),
                        format=self._first_query_value(query, "format", "json"),
                    )
                )
                BinaryHttpResponder(self).send(
                    HTTPStatus.OK, result.content, result.content_type, result.filename
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/anomalies":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_anomalies(
                    ListCostAnomaliesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        severity=query.get("severity", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/forecasts":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.finops_service.list_forecasts(
                    ListFinOpsForecastsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        dimension=query.get("dimension", [None])[0],
                        target=query.get("target", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/simulation-scenarios":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.simulation_service.list_scenarios(
                    ListSimulationScenariosCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        status=query.get("status", [None])[0],
                        site=query.get("site", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/simulation-scenarios/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.simulation_service.get_scenario(
                    GetSimulationScenarioCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        scenario_id=self._first_query_value(query, "scenario_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/impact-reports":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.simulation_service.list_reports(
                    ListSimulationReportsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        scenario_id=query.get("scenario_id", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/impact-reports/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.simulation_service.get_report(
                    GetSimulationReportCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        report_id=self._first_query_value(query, "report_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/scenario-comparisons":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.simulation_service.list_comparisons(
                    ListSimulationComparisonsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/field-operation-sheets":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.field_operation_service.list_sheets(
                    ListFieldOperationSheetsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        status=query.get("status", [None])[0],
                        target_type=query.get("target_type", [None])[0],
                        site=query.get("site", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/field-operation-sheets/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.field_operation_service.get_sheet(
                    GetFieldOperationSheetCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        sheet_id=self._first_query_value(query, "sheet_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/field-evidence":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.field_operation_service.list_evidence(
                    GetFieldOperationSheetCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        sheet_id=self._first_query_value(query, "sheet_id"),
                    )
                )
                responder.send(
                    HTTPStatus.OK,
                    {"items": [item.as_dict(include_content=False) for item in result]},
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/offline-sync-packages":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.field_operation_service.list_offline_packages(
                    ListOfflineSyncPackagesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        sheet_id=query.get("sheet_id", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/offline-sync-packages/get":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.field_operation_service.get_offline_package(
                    GetOfflineSyncPackageCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        package_id=self._first_query_value(query, "package_id"),
                        include_payload=self._first_query_value(
                            query, "include_payload", "true"
                        ).lower()
                        in {"1", "true", "yes"},
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/graph/traverse":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.dependency_graph_service.traverse(
                    TraverseDependencyGraphCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        root_key=self._first_query_value(query, "root_key"),
                        direction=self._first_query_value(query, "direction", "both"),
                        max_depth=int(self._first_query_value(query, "max_depth", "3")),
                        max_nodes=int(self._first_query_value(query, "max_nodes", "500")),
                        relation_types=tuple(query.get("relation_type", [])),
                        as_of=query.get("as_of", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/graph/impact":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.dependency_graph_service.impact(
                    AnalyzeDependencyImpactCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        root_key=self._first_query_value(query, "root_key"),
                        direction=self._first_query_value(query, "direction", "incoming"),
                        max_depth=int(self._first_query_value(query, "max_depth", "6")),
                        max_nodes=int(self._first_query_value(query, "max_nodes", "1000")),
                        relation_types=tuple(query.get("relation_type", [])),
                        as_of=query.get("as_of", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/graph/path":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.dependency_graph_service.find_path(
                    FindDependencyPathCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        source_key=self._first_query_value(query, "source_key"),
                        target_key=self._first_query_value(query, "target_key"),
                        direction=self._first_query_value(query, "direction", "outgoing"),
                        max_depth=int(self._first_query_value(query, "max_depth", "8")),
                        max_nodes=int(self._first_query_value(query, "max_nodes", "1000")),
                        relation_types=tuple(query.get("relation_type", [])),
                        as_of=query.get("as_of", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/graph/spof":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.dependency_graph_service.analyze_spof(
                    AnalyzeDependencySpofCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        root_key=self._first_query_value(query, "root_key"),
                        direction=self._first_query_value(query, "direction", "both"),
                        max_depth=int(self._first_query_value(query, "max_depth", "8")),
                        max_nodes=int(self._first_query_value(query, "max_nodes", "2000")),
                        relation_types=tuple(query.get("relation_type", [])),
                        as_of=query.get("as_of", [None])[0],
                        candidate_kinds=tuple(query.get("candidate_kind", [])),
                        candidate_resource_categories=tuple(
                            query.get("candidate_resource_category", [])
                        ),
                        candidate_resource_types=tuple(query.get("candidate_resource_type", [])),
                        candidate_statuses=tuple(query.get("candidate_status", [])),
                        minimum_affected_nodes=int(
                            self._first_query_value(query, "minimum_affected_nodes", "1")
                        ),
                        affected_sample_limit=int(
                            self._first_query_value(query, "affected_sample_limit", "25")
                        ),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/graph/export":
            try:
                query = parse_qs(parsed.query)
                include_spof = self._first_query_value(query, "include_spof", "true").lower() in {
                    "1",
                    "true",
                    "yes",
                }
                result = self.server.application.dependency_graph_service.export(
                    ExportDependencyGraphCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        root_key=self._first_query_value(query, "root_key"),
                        format=self._first_query_value(query, "format", "json"),
                        direction=self._first_query_value(query, "direction", "both"),
                        max_depth=int(self._first_query_value(query, "max_depth", "8")),
                        max_nodes=int(self._first_query_value(query, "max_nodes", "2000")),
                        relation_types=tuple(query.get("relation_type", [])),
                        as_of=query.get("as_of", [None])[0],
                        include_spof=include_spof,
                        candidate_kinds=tuple(query.get("candidate_kind", [])),
                        candidate_resource_categories=tuple(
                            query.get("candidate_resource_category", [])
                        ),
                        candidate_resource_types=tuple(query.get("candidate_resource_type", [])),
                        candidate_statuses=tuple(query.get("candidate_status", [])),
                        minimum_affected_nodes=int(
                            self._first_query_value(query, "minimum_affected_nodes", "1")
                        ),
                    )
                )
                binary_responder.send(
                    HTTPStatus.OK, result.content, result.content_type, result.filename
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/rsot/governance-rules":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.source_governance_service.list_rules(
                    ListSourceGovernanceRulesCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        include_inactive=(
                            self._first_query_value(query, "include_inactive", "false") == "true"
                        ),
                        object_kind=query.get("object_kind", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/rsot/resource-taxonomy":
            responder.send(
                HTTPStatus.OK,
                self.server.application.it_resources_management_service.resource_taxonomy(),
            )
            return

        if route == "/api/v1/rsot/objects":
            try:
                query = parse_qs(parsed.query)
                key = query.get("key", [None])[0]
                if key:
                    result = self.server.application.it_resources_management_service.get_object(
                        GetSourceObjectCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            key=key,
                        )
                    )
                    responder.send(HTTPStatus.OK, result)
                else:
                    page = self.server.application.it_resources_management_service.list_objects(
                        ListSourceObjectsCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            limit=int(self._first_query_value(query, "limit", "100")),
                            cursor=query.get("cursor", [None])[0],
                            kind=(query.get("resource_category", query.get("kind", [None]))[0]),
                            tag=query.get("tag", [None])[0],
                            resource_type=query.get("resource_type", [None])[0],
                        )
                    )
                    responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/object-versions":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.it_resources_management_service.get_object_version(
                    GetSourceObjectVersionCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        key=self._first_query_value(query, "key"),
                        version=int(self._first_query_value(query, "version")),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/object-as-of":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.it_resources_management_service.get_object_as_of(
                    GetSourceObjectAsOfCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        key=self._first_query_value(query, "key"),
                        as_of=self._first_query_value(query, "as_of"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/object-audit":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.it_resources_management_service.list_object_audit(
                    ListSourceObjectAuditCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        key=self._first_query_value(query, "key"),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/quality/object":
            try:
                query = parse_qs(parsed.query)
                result = (
                    self.server.application.it_resources_management_quality_service.evaluate_object(
                        EvaluateItrmObjectQualityCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            key=self._first_query_value(query, "key"),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/quality/summary":
            try:
                query = parse_qs(parsed.query)
                summary = self.server.application.it_resources_management_quality_service.summarize(
                    ItrmQualitySummaryCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        kind=query.get("kind", [None])[0],
                        tag=query.get("tag", [None])[0],
                        resource_category=query.get("resource_category", [None])[0],
                        resource_type=query.get("resource_type", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, summary.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/relations":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.it_resources_management_service.list_relations(
                    ListSourceRelationsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        source_key=query.get("source_key", [None])[0],
                        target_key=query.get("target_key", [None])[0],
                        relation_type=query.get("relation_type", [None])[0],
                        as_of=query.get("as_of", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/dcim/sites":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.list_sites(
                    ListDcimSitesCommand(
                        tenant_id=tenant_id,
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/site":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.get_site(
                    GetDcimSiteCommand(
                        tenant_id=tenant_id,
                        code=self._first_query_value(query, "code"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/buildings":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.list_buildings(
                    ListDcimBuildingsCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/building":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.get_building(
                    GetDcimBuildingCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        code=self._first_query_value(query, "code"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/floors":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.list_floors(
                    ListDcimFloorsCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/floor":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.get_floor(
                    GetDcimFloorCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        code=self._first_query_value(query, "code"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rooms":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.list_rooms(
                    ListDcimRoomsCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/room":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.get_room(
                    GetDcimRoomCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        code=self._first_query_value(query, "code"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/zones":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.list_zones(
                    ListDcimZonesCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/zone":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.get_zone(
                    GetDcimZoneCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        code=self._first_query_value(query, "code"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/racks":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_rack_service.list_racks(
                    ListRacksCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rack":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_rack_service.get_rack(
                    GetRackCommand(
                        tenant_id=tenant_id,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        rack=self._first_query_value(query, "rack"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/topology-catalog":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                result = self.server.application.dcim_topology_service.topology_catalog(
                    DcimTopologyCatalogCommand(
                        tenant_id=tenant_id,
                        include_retired=self._first_query_value(
                            query, "include_retired", "false"
                        ).lower()
                        == "true",
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rack-capacity":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.dcim_rack_service.capacity(
                    RackCapacityCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        rack=self._first_query_value(query, "rack"),
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/locator-sheet":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_IDENTIFY)
                    actor = principal.subject
                sheet = self.server.application.dcim_field_operation_service.locator_sheet(
                    GenerateEquipmentLocatorCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        asset_tag=self._first_query_value(query, "asset_tag"),
                        output_format=self._first_query_value(query, "format", "json"),
                    )
                )
                if self._first_query_value(query, "format", "json") == "html":
                    responder.send(HTTPStatus.OK, {"html": sheet.html_document()})
                else:
                    responder.send(HTTPStatus.OK, sheet.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/dcim/room-plan":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                    actor = principal.subject
                output_format = self._first_query_value(query, "format", "json")
                plan = self.server.application.dcim_visualization_service.room_plan(
                    RenderRoomPlanCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        output_format=output_format,
                    )
                )
                if output_format == "svg":
                    responder.send(HTTPStatus.OK, {"svg": plan.svg_document()})
                elif output_format == "html":
                    responder.send(HTTPStatus.OK, {"html": plan.html_document()})
                else:
                    responder.send(HTTPStatus.OK, plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/integrations/itsm/providers":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id", "default")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                policies = self.server.application.external_itsm_service.list_policies()
                responder.send(
                    HTTPStatus.OK,
                    {"items": [policy.as_dict() for policy in policies]},
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except OpenInfraError as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rack-elevation":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                    actor = principal.subject
                output_format = self._first_query_value(query, "format", "json")
                elevation = self.server.application.dcim_visualization_service.rack_elevation(
                    RenderRackElevationCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                        rack=self._first_query_value(query, "rack"),
                        face=self._first_query_value(query, "face", "front"),
                        output_format=output_format,
                    )
                )
                if output_format == "svg":
                    responder.send(HTTPStatus.OK, {"svg": elevation.svg_document()})
                elif output_format == "html":
                    responder.send(HTTPStatus.OK, {"html": elevation.html_document()})
                else:
                    responder.send(HTTPStatus.OK, elevation.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/dcim/digital-twin":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                    actor = principal.subject
                result = self.server.application.dcim_visualization_service.digital_twin(
                    RenderDigitalTwinCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=self._first_query_value(query, "site"),
                        building=self._first_query_value(query, "building"),
                        room=self._first_query_value(query, "room"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/dcim/cable-trace":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                    actor = principal.subject
                result = self.server.application.dcim_cabling_service.trace_cable(
                    TraceDcimCableCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        cable_id=self._first_query_value(query, "cable_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/dcim/energy-cooling-capacity":
            try:
                query = parse_qs(parsed.query)
                tenant_id = self._first_query_value(query, "tenant_id")
                actor = "api"
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                    actor = principal.subject
                report = (
                    self.server.application.dcim_environment_service.rack_energy_cooling_capacity(
                        RackEnergyCoolingCapacityCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            site=self._first_query_value(query, "site"),
                            building=self._first_query_value(query, "building"),
                            room=self._first_query_value(query, "room"),
                            rack=self._first_query_value(query, "rack"),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/identity/effective":
            try:
                query = parse_qs(parsed.query)
                identity = self.server.application.identity_service.effective_identity(
                    EffectiveIdentityCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        actor="api",
                        admin_token=self._bearer_token(),
                        subject=self._first_query_value(query, "subject"),
                    )
                )
                responder.send(HTTPStatus.OK, identity.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/ui/ipam":
            try:
                query = parse_qs(parsed.query)
                html = self.server.application.ipam_ui_service.render_dashboard_html(
                    IpamUiDashboardCommand(
                        tenant_id=self._first_query_value(query, "tenant_id", "default"),
                        actor="api",
                        vrf=query.get("vrf", [None])[0],
                    )
                )
                text_responder.send(HTTPStatus.OK, html, "text/html; charset=utf-8")
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/ipam/ui-dashboard":
            try:
                query = parse_qs(parsed.query)
                view = self.server.application.ipam_ui_service.dashboard(
                    IpamUiDashboardCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        actor="api",
                        vrf=query.get("vrf", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, view.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/ipam/ui-search":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.ipam_ui_service.search(
                    IpamSearchCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        actor="api",
                        query=self._first_query_value(query, "query"),
                        vrf=query.get("vrf", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/ipam/prefixes":
            try:
                query = parse_qs(parsed.query)
                items = self.server.application.ipam_model_service.list_prefixes(
                    self._first_query_value(query, "tenant_id"),
                    self._first_query_value(query, "vrf"),
                )
                responder.send(HTTPStatus.OK, {"items": list(items)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/ipam/capacity":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.ipam_model_service.capacity(
                    IpamCapacityCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        vrf=self._first_query_value(query, "vrf"),
                        prefix=self._first_query_value(query, "prefix"),
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/ipam/network-bindings":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.ipam_model_service.network_bindings(
                    IpamNetworkBindingsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        vrf=query.get("vrf", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/ipam/topology":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.ipam_model_service.topology(
                    IpamTopologyCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        actor="api",
                        vrf=query.get("vrf", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/ipam/conflicts":
            try:
                query = parse_qs(parsed.query)
                report = self.server.application.ipam_conflict_service.detect(
                    DetectIpamConflictsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        actor="api",
                        vrf=query.get("vrf", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, report.as_dict())
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        responder.send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        responder = JsonHttpResponder(self)
        route = self._canonical_route(urlparse(self.path).path)
        result: Any
        rule: Any

        if route == "/api/v1/network-config/baselines/upsert":
            try:
                payload = self._read_json_body()
                result = self.server.application.network_config_compliance_service.upsert_baseline(
                    UpsertNetworkConfigBaselineCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        code=self._required_payload_value(payload, "code"),
                        device_object_key=self._required_payload_value(
                            payload, "device_object_key"
                        ),
                        platform=self._required_payload_value(payload, "platform"),
                        expected_config=payload["expected_config"],
                        ignored_paths=tuple(str(item) for item in payload.get("ignored_paths", [])),
                        critical_paths=tuple(
                            str(item) for item in payload.get("critical_paths", [])
                        ),
                        owner=self._required_payload_value(payload, "owner"),
                        justification=self._required_payload_value(payload, "justification"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/greenops/measurement-sources/create":
            try:
                payload = self._read_json_body()
                result = self.server.application.greenops_service.create_source(
                    CreateMeasurementSourceCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        code=self._required_payload_value(payload, "code"),
                        name=self._required_payload_value(payload, "name"),
                        source_type=self._required_payload_value(payload, "source_type"),
                        owner=self._required_payload_value(payload, "owner"),
                        active=self._payload_bool(payload, "active", True),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/policies/upsert":
            try:
                payload = self._read_json_body()
                result = self.server.application.greenops_service.upsert_policy(
                    UpsertGreenOpsPolicyCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        site_code=self._required_payload_value(payload, "site_code"),
                        default_pue=self._required_payload_value(payload, "default_pue"),
                        energy_cost_per_kwh=self._required_payload_value(
                            payload, "energy_cost_per_kwh"
                        ),
                        currency=self._required_payload_value(payload, "currency"),
                        carbon_factor_code=self._required_payload_value(
                            payload, "carbon_factor_code"
                        ),
                        underutilized_percent=str(payload.get("underutilized_percent", "20")),
                        warning_capacity_percent=str(payload.get("warning_capacity_percent", "80")),
                        critical_capacity_percent=str(
                            payload.get("critical_capacity_percent", "90")
                        ),
                        minimum_samples=int(payload.get("minimum_samples", 3)),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/carbon-factors/create":
            try:
                payload = self._read_json_body()
                result = self.server.application.greenops_service.create_carbon_factor(
                    CreateCarbonFactorCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        code=self._required_payload_value(payload, "code"),
                        region=self._required_payload_value(payload, "region"),
                        grams_co2e_per_kwh=self._required_payload_value(
                            payload, "grams_co2e_per_kwh"
                        ),
                        source_name=self._required_payload_value(payload, "source_name"),
                        period_start=date.fromisoformat(
                            self._required_payload_value(payload, "period_start")
                        ),
                        period_end=date.fromisoformat(
                            self._required_payload_value(payload, "period_end")
                        ),
                        source_uri=self._optional_payload_value(payload, "source_uri"),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/energy-measurements/ingest":
            try:
                payload = self._read_json_body()
                metadata = payload.get("metadata", {})
                if not isinstance(metadata, dict):
                    raise ValidationError("GreenOps metadata must be a JSON object")
                result = self.server.application.greenops_service.ingest_measurement(
                    IngestEnergyMeasurementCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        source_code=self._required_payload_value(payload, "source_code"),
                        kind=self._required_payload_value(payload, "kind"),
                        scope=self._required_payload_value(payload, "scope"),
                        scope_key=self._required_payload_value(payload, "scope_key"),
                        site_code=self._required_payload_value(payload, "site_code"),
                        period_start=datetime.fromisoformat(
                            self._required_payload_value(payload, "period_start").replace(
                                "Z", "+00:00"
                            )
                        ),
                        period_end=datetime.fromisoformat(
                            self._required_payload_value(payload, "period_end").replace(
                                "Z", "+00:00"
                            )
                        ),
                        energy_kwh=self._required_payload_value(payload, "energy_kwh"),
                        application_key=self._optional_payload_value(payload, "application_key"),
                        it_energy_kwh=self._optional_payload_value(payload, "it_energy_kwh"),
                        facility_energy_kwh=self._optional_payload_value(
                            payload, "facility_energy_kwh"
                        ),
                        utilization_percent=self._optional_payload_value(
                            payload, "utilization_percent"
                        ),
                        energy_capacity_percent=self._optional_payload_value(
                            payload, "energy_capacity_percent"
                        ),
                        cooling_capacity_percent=self._optional_payload_value(
                            payload, "cooling_capacity_percent"
                        ),
                        space_capacity_percent=self._optional_payload_value(
                            payload, "space_capacity_percent"
                        ),
                        weight_capacity_percent=self._optional_payload_value(
                            payload, "weight_capacity_percent"
                        ),
                        metadata=dict(metadata),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/greenops/reports/generate":
            try:
                payload = self._read_json_body()
                result = self.server.application.greenops_service.generate_report(
                    GenerateSustainabilityReportCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        site_code=self._required_payload_value(payload, "site_code"),
                        period_start=date.fromisoformat(
                            self._required_payload_value(payload, "period_start")
                        ),
                        period_end=date.fromisoformat(
                            self._required_payload_value(payload, "period_end")
                        ),
                        scope=str(payload.get("scope", "site")),
                        scope_key=self._optional_payload_value(payload, "scope_key"),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/finops/allocation-rules/create":
            try:
                payload = self._read_json_body()
                result = self.server.application.finops_service.create_allocation_rule(
                    CreateCostAllocationRuleCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        name=self._required_payload_value(payload, "name"),
                        priority=int(payload.get("priority", 100)),
                        dimension=self._required_payload_value(payload, "dimension"),
                        selector_key=self._required_payload_value(payload, "selector_key"),
                        percentage=self._required_payload_value(payload, "percentage"),
                        category=self._optional_payload_value(payload, "category"),
                        source=self._optional_payload_value(payload, "source"),
                        fixed_target=self._optional_payload_value(payload, "fixed_target"),
                        active=self._payload_bool(payload, "active", True),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/import-jobs/submit":
            try:
                payload = self._read_json_body()
                records = payload.get("records")
                if not isinstance(records, list) or any(
                    not isinstance(item, dict) for item in records
                ):
                    raise ValidationError("finops records must be a JSON array of objects")
                result = self.server.application.finops_service.submit_import_job(
                    SubmitCostImportJobCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        source=self._required_payload_value(payload, "source"),
                        records=tuple(dict(item) for item in records),
                    )
                )
                responder.send(HTTPStatus.ACCEPTED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/import-jobs/run":
            try:
                payload = self._read_json_body()
                result = self.server.application.finops_service.run_import_job(
                    RunCostImportJobCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        job_id=self._required_payload_value(payload, "job_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/import-jobs/cancel":
            try:
                payload = self._read_json_body()
                result = self.server.application.finops_service.cancel_import_job(
                    CancelCostImportJobCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        job_id=self._required_payload_value(payload, "job_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/budgets/upsert":
            try:
                payload = self._read_json_body()
                result = self.server.application.finops_service.upsert_budget(
                    UpsertFinOpsBudgetCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        dimension=self._required_payload_value(payload, "dimension"),
                        target=self._required_payload_value(payload, "target"),
                        period_start=date.fromisoformat(
                            self._required_payload_value(payload, "period_start")
                        ),
                        period_end=date.fromisoformat(
                            self._required_payload_value(payload, "period_end")
                        ),
                        currency=self._required_payload_value(payload, "currency"),
                        amount=self._required_payload_value(payload, "amount"),
                        warning_threshold_percent=self._required_payload_value(
                            payload, "warning_threshold_percent"
                        ),
                        owner=self._required_payload_value(payload, "owner"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/periods/close":
            try:
                payload = self._read_json_body()
                result = self.server.application.finops_service.close_period(
                    CloseFinancialPeriodCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        period_start=date.fromisoformat(
                            self._required_payload_value(payload, "period_start")
                        ),
                        period_end=date.fromisoformat(
                            self._required_payload_value(payload, "period_end")
                        ),
                        currency=self._required_payload_value(payload, "currency"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/finops/reports/generate":
            try:
                payload = self._read_json_body()
                result = self.server.application.finops_service.generate_report(
                    GenerateFinOpsReportCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        actor=str(payload.get("actor", "api")),
                        kind=self._required_payload_value(payload, "kind"),
                        period_start=date.fromisoformat(
                            self._required_payload_value(payload, "period_start")
                        ),
                        period_end=date.fromisoformat(
                            self._required_payload_value(payload, "period_end")
                        ),
                        group_by=self._required_payload_value(payload, "group_by"),
                        currency=self._required_payload_value(payload, "currency"),
                        chargeback_markup_percent=str(
                            payload.get("chargeback_markup_percent", "0")
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/simulation-scenarios/create":
            try:
                payload = self._read_json_body()
                raw_changes = payload.get("changes")
                if not isinstance(raw_changes, list):
                    raise ValidationError("simulation changes must be a JSON array")
                changes = tuple(dict(item) for item in raw_changes if isinstance(item, dict))
                if len(changes) != len(raw_changes):
                    raise ValidationError("each simulation change must be a JSON object")
                result = self.server.application.simulation_service.create_scenario(
                    CreateSimulationScenarioCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=self._required_payload_value(payload, "name"),
                        description=self._required_payload_value(payload, "description"),
                        owner=self._required_payload_value(payload, "owner"),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        changes=changes,
                        site=self._optional_payload_value(payload, "site"),
                        environment=self._optional_payload_value(payload, "environment"),
                        criticality=self._optional_payload_value(payload, "criticality"),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/simulation-scenarios/run":
            try:
                payload = self._read_json_body()
                result = self.server.application.simulation_service.run_scenario(
                    RunSimulationScenarioCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        scenario_id=self._required_payload_value(payload, "scenario_id"),
                        max_depth=int(payload.get("max_depth", 8)),
                        max_nodes=int(payload.get("max_nodes", 2000)),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/simulation-scenarios/cancel":
            try:
                payload = self._read_json_body()
                result = self.server.application.simulation_service.cancel_scenario(
                    CancelSimulationScenarioCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        scenario_id=self._required_payload_value(payload, "scenario_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/scenario-comparisons/create":
            try:
                payload = self._read_json_body()
                result = self.server.application.simulation_service.compare_reports(
                    CompareSimulationReportsCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        left_report_id=self._required_payload_value(payload, "left_report_id"),
                        right_report_id=self._required_payload_value(payload, "right_report_id"),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/field-operation-sheets/generate":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.generate_sheet(
                    GenerateFieldOperationSheetCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        target_type=self._required_payload_value(payload, "target_type"),
                        target_id=self._required_payload_value(payload, "target_id"),
                        title=self._required_payload_value(payload, "title"),
                        purpose=self._required_payload_value(payload, "purpose"),
                        owner=self._required_payload_value(payload, "owner"),
                        operator=self._required_payload_value(payload, "operator"),
                        source_object_key=self._optional_payload_value(
                            payload, "source_object_key"
                        ),
                        site=self._optional_payload_value(payload, "site"),
                        building=self._optional_payload_value(payload, "building"),
                        room=self._optional_payload_value(payload, "room"),
                        location_target_type=self._optional_payload_value(
                            payload, "location_target_type"
                        ),
                        location_target_id=self._optional_payload_value(
                            payload, "location_target_id"
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route in {
            "/api/v1/field-operation-sheets/start",
            "/api/v1/field-operation-sheets/complete",
            "/api/v1/field-operation-sheets/cancel",
        }:
            try:
                payload = self._read_json_body()
                common = {
                    "tenant_id": self._required_payload_value(payload, "tenant_id"),
                    "actor": str(payload.get("actor", "api")),
                    "admin_token": self._bearer_token(),
                    "sheet_id": self._required_payload_value(payload, "sheet_id"),
                }
                if route.endswith("/start"):
                    result = self.server.application.field_operation_service.start(
                        StartFieldOperationCommand(**common)
                    )
                elif route.endswith("/complete"):
                    result = self.server.application.field_operation_service.complete(
                        CompleteFieldOperationCommand(**common)
                    )
                else:
                    result = self.server.application.field_operation_service.cancel(
                        CancelFieldOperationCommand(**common)
                    )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/field-operation-sheets/checklist":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.record_checklist(
                    RecordFieldChecklistCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        sheet_id=self._required_payload_value(payload, "sheet_id"),
                        item_id=self._required_payload_value(payload, "item_id"),
                        result=self._required_payload_value(payload, "result"),
                        operator_note=self._optional_payload_value(payload, "operator_note"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/qr-codes/verify":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.verify_qr(
                    VerifyFieldQrCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        admin_token=self._bearer_token(),
                        sheet_id=self._required_payload_value(payload, "sheet_id"),
                        payload=self._required_payload_value(payload, "payload"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/field-evidence/attach":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.attach_evidence(
                    AttachFieldEvidenceCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        sheet_id=self._required_payload_value(payload, "sheet_id"),
                        phase=self._required_payload_value(payload, "phase"),
                        media_type=self._required_payload_value(payload, "media_type"),
                        filename=self._required_payload_value(payload, "filename"),
                        content_base64=self._required_payload_value(payload, "content_base64"),
                        caption=self._required_payload_value(payload, "caption"),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict(include_content=False))
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/field-evidence/validate":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.validate_evidence(
                    ValidateFieldEvidenceCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        evidence_id=self._required_payload_value(payload, "evidence_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict(include_content=False))
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/intervention-locks/acquire":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.acquire_lock(
                    AcquireInterventionLockCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        sheet_id=self._required_payload_value(payload, "sheet_id"),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        ttl_seconds=int(payload.get("ttl_seconds", 3600)),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/intervention-locks/release":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.release_lock(
                    ReleaseInterventionLockCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        lock_id=self._required_payload_value(payload, "lock_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/offline-sync-packages/create":
            try:
                payload = self._read_json_body()
                result = self.server.application.field_operation_service.create_offline_package(
                    CreateOfflineSyncPackageCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        sheet_id=self._required_payload_value(payload, "sheet_id"),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        ttl_seconds=int(payload.get("ttl_seconds", 86400)),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict(include_payload=True))
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/offline-sync-packages/synchronize":
            try:
                payload = self._read_json_body()
                result = (
                    self.server.application.field_operation_service.synchronize_offline_package(
                        SynchronizeOfflinePackageCommand(
                            tenant_id=self._required_payload_value(payload, "tenant_id"),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            package_id=self._required_payload_value(payload, "package_id"),
                            payload_sha256=self._required_payload_value(payload, "payload_sha256"),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict(include_payload=False))
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/network-config/baselines/retire":
            try:
                payload = self._read_json_body()
                result = self.server.application.network_config_compliance_service.retire_baseline(
                    RetireNetworkConfigBaselineCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        baseline_id=self._required_payload_value(payload, "baseline_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/network-config/observations/submit":
            try:
                payload = self._read_json_body()
                result = (
                    self.server.application.network_config_compliance_service.submit_observation(
                        SubmitNetworkConfigObservationCommand(
                            tenant_id=self._required_payload_value(payload, "tenant_id"),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            idempotency_key=self._required_payload_value(
                                payload, "idempotency_key"
                            ),
                            source=self._required_payload_value(payload, "source"),
                            collector=self._required_payload_value(payload, "collector"),
                            device_object_key=self._required_payload_value(
                                payload, "device_object_key"
                            ),
                            platform=self._required_payload_value(payload, "platform"),
                            observed_config=payload["observed_config"],
                            observed_at=self._required_payload_value(payload, "observed_at"),
                        )
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates/import":
            try:
                payload = self._read_json_body()
                result = self.server.application.certificate_pki_service.import_bundle(
                    ImportCertificateBundleCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        pem_bundle=self._required_payload_value(payload, "pem_bundle"),
                        owner=self._required_payload_value(payload, "owner"),
                        environment=self._required_payload_value(payload, "environment"),
                        source=self._required_payload_value(payload, "source"),
                        object_key=(
                            None
                            if payload.get("object_key") is None
                            else str(payload["object_key"])
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates/retire":
            try:
                payload = self._read_json_body()
                result = self.server.application.certificate_pki_service.retire_certificate(
                    RetireCertificateCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        fingerprint=self._required_payload_value(payload, "fingerprint"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/certificates/endpoints/observe":
            try:
                payload = self._read_json_body()
                result = self.server.application.certificate_pki_service.observe_endpoint(
                    ObserveCertificateEndpointCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        protocol=self._required_payload_value(payload, "protocol"),
                        host=self._required_payload_value(payload, "host"),
                        port=int(payload["port"]),
                        service=self._required_payload_value(payload, "service"),
                        certificate_fingerprint=self._required_payload_value(
                            payload, "certificate_fingerprint"
                        ),
                        observed_at=self._required_payload_value(payload, "observed_at"),
                        source=self._required_payload_value(payload, "source"),
                        collector=self._required_payload_value(payload, "collector"),
                        object_key=(
                            None
                            if payload.get("object_key") is None
                            else str(payload["object_key"])
                        ),
                        tls_version=(
                            None
                            if payload.get("tls_version") is None
                            else str(payload["tls_version"])
                        ),
                        cipher=(None if payload.get("cipher") is None else str(payload["cipher"])),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/flows/declarations/upsert":
            try:
                payload = self._read_json_body()
                result = self.server.application.flow_matrix_service.upsert_declaration(
                    UpsertFlowDeclarationCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        code=self._required_payload_value(payload, "code"),
                        source_selector=self._required_payload_value(payload, "source_selector"),
                        destination_selector=self._required_payload_value(
                            payload, "destination_selector"
                        ),
                        protocol=self._required_payload_value(payload, "protocol"),
                        destination_port_start=(
                            None
                            if payload.get("destination_port_start") is None
                            else int(payload["destination_port_start"])
                        ),
                        destination_port_end=(
                            None
                            if payload.get("destination_port_end") is None
                            else int(payload["destination_port_end"])
                        ),
                        decision=self._required_payload_value(payload, "decision"),
                        priority=int(payload.get("priority", 100)),
                        owner=self._required_payload_value(payload, "owner"),
                        justification=self._required_payload_value(payload, "justification"),
                        valid_from=(
                            None
                            if payload.get("valid_from") is None
                            else str(payload["valid_from"])
                        ),
                        valid_to=(
                            None if payload.get("valid_to") is None else str(payload["valid_to"])
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/flows/declarations/retire":
            try:
                payload = self._read_json_body()
                result = self.server.application.flow_matrix_service.retire_declaration(
                    RetireFlowDeclarationCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        declaration_id=self._required_payload_value(payload, "declaration_id"),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/flows/observations/submit":
            try:
                payload = self._read_json_body()
                result = self.server.application.flow_matrix_service.submit_observation(
                    SubmitFlowObservationCommand(
                        tenant_id=self._required_payload_value(payload, "tenant_id"),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        idempotency_key=self._required_payload_value(payload, "idempotency_key"),
                        source=self._required_payload_value(payload, "source"),
                        collector=self._required_payload_value(payload, "collector"),
                        source_ip=self._required_payload_value(payload, "source_ip"),
                        destination_ip=self._required_payload_value(payload, "destination_ip"),
                        source_object_key=(
                            None
                            if payload.get("source_object_key") is None
                            else str(payload["source_object_key"])
                        ),
                        destination_object_key=(
                            None
                            if payload.get("destination_object_key") is None
                            else str(payload["destination_object_key"])
                        ),
                        protocol=self._required_payload_value(payload, "protocol"),
                        destination_port=(
                            None
                            if payload.get("destination_port") is None
                            else int(payload["destination_port"])
                        ),
                        packets=int(payload["packets"]),
                        bytes_count=int(payload["bytes"]),
                        first_seen=self._required_payload_value(payload, "first_seen"),
                        last_seen=self._required_payload_value(payload, "last_seen"),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/servicenow/validate":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                service = self.server.application.external_itsm_service
                profile = service.validate_servicenow_connector(
                    ValidateServiceNowConnectorCommand(
                        tenant_id=tenant_id,
                        instance_url=self._required_payload_value(payload, "instance_url"),
                        table_name=str(payload.get("table_name", "cmdb_ci")),
                        auth_secret_ref=self._required_payload_value(payload, "auth_secret_ref"),
                        enabled=bool(payload.get("enabled", True)),
                    )
                )
                responder.send(HTTPStatus.OK, profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/servicenow/ci-sync-plan":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                raw_mapping = payload.get("mapping")
                if raw_mapping is not None and not isinstance(raw_mapping, dict):
                    raise OpenInfraError("mapping must be a JSON object")
                mapping = (
                    {str(key): str(value) for key, value in raw_mapping.items()}
                    if isinstance(raw_mapping, dict)
                    else None
                )
                service = self.server.application.external_itsm_service
                servicenow_ci_sync_plan = service.build_servicenow_ci_sync_plan(
                    BuildServiceNowCiSyncPlanCommand(
                        tenant_id=tenant_id,
                        resource_key=self._required_payload_value(payload, "resource_key"),
                        direction=str(payload.get("direction", "push_ci")),
                        target_table=str(payload.get("target_table", "cmdb_ci")),
                        mapping=mapping,
                    )
                )
                responder.send(HTTPStatus.OK, servicenow_ci_sync_plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/jira/validate":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                service = self.server.application.external_itsm_service
                profile = service.validate_jira_service_management_connector(
                    ValidateJiraServiceManagementConnectorCommand(
                        tenant_id=tenant_id,
                        instance_url=self._required_payload_value(payload, "instance_url"),
                        object_type=str(payload.get("object_type", "object")),
                        auth_secret_ref=self._required_payload_value(payload, "auth_secret_ref"),
                        enabled=bool(payload.get("enabled", True)),
                    )
                )
                responder.send(HTTPStatus.OK, profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/jira/asset-sync-plan":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                raw_mapping = payload.get("mapping")
                if raw_mapping is not None and not isinstance(raw_mapping, dict):
                    raise OpenInfraError("mapping must be a JSON object")
                mapping = (
                    {str(key): str(value) for key, value in raw_mapping.items()}
                    if isinstance(raw_mapping, dict)
                    else None
                )
                service = self.server.application.external_itsm_service
                plan = service.build_jira_service_management_asset_sync_plan(
                    BuildJiraServiceManagementAssetSyncPlanCommand(
                        tenant_id=tenant_id,
                        resource_key=self._required_payload_value(payload, "resource_key"),
                        direction=str(payload.get("direction", "push_ci")),
                        object_type=str(payload.get("object_type", "object")),
                        mapping=mapping,
                    )
                )
                responder.send(HTTPStatus.OK, plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/glpi/validate":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                service = self.server.application.external_itsm_service
                profile = service.validate_glpi_connector(
                    ValidateGlpiConnectorCommand(
                        tenant_id=tenant_id,
                        instance_url=self._required_payload_value(payload, "instance_url"),
                        item_type=str(payload.get("item_type", "computer")),
                        auth_secret_ref=self._required_payload_value(payload, "auth_secret_ref"),
                        enabled=bool(payload.get("enabled", True)),
                    )
                )
                responder.send(HTTPStatus.OK, profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/glpi/asset-sync-plan":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                raw_mapping = payload.get("mapping")
                if raw_mapping is not None and not isinstance(raw_mapping, dict):
                    raise OpenInfraError("mapping must be a JSON object")
                mapping = (
                    {str(key): str(value) for key, value in raw_mapping.items()}
                    if isinstance(raw_mapping, dict)
                    else None
                )
                service = self.server.application.external_itsm_service
                plan = service.build_glpi_asset_sync_plan(
                    BuildGlpiAssetSyncPlanCommand(
                        tenant_id=tenant_id,
                        resource_key=self._required_payload_value(payload, "resource_key"),
                        direction=str(payload.get("direction", "push_ci")),
                        item_type=str(payload.get("item_type", "computer")),
                        mapping=mapping,
                    )
                )
                responder.send(HTTPStatus.OK, plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/freshservice/validate":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                service = self.server.application.external_itsm_service
                profile = service.validate_freshservice_connector(
                    ValidateFreshserviceConnectorCommand(
                        tenant_id=tenant_id,
                        instance_url=self._required_payload_value(payload, "instance_url"),
                        asset_type=str(payload.get("asset_type", "asset")),
                        auth_secret_ref=self._required_payload_value(payload, "auth_secret_ref"),
                        enabled=bool(payload.get("enabled", True)),
                    )
                )
                responder.send(HTTPStatus.OK, profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/freshservice/asset-sync-plan":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                raw_mapping = payload.get("mapping")
                if raw_mapping is not None and not isinstance(raw_mapping, dict):
                    raise OpenInfraError("mapping must be a JSON object")
                mapping = (
                    {str(key): str(value) for key, value in raw_mapping.items()}
                    if isinstance(raw_mapping, dict)
                    else None
                )
                service = self.server.application.external_itsm_service
                plan = service.build_freshservice_asset_sync_plan(
                    BuildFreshserviceAssetSyncPlanCommand(
                        tenant_id=tenant_id,
                        resource_key=self._required_payload_value(payload, "resource_key"),
                        direction=str(payload.get("direction", "push_ci")),
                        asset_type=str(payload.get("asset_type", "asset")),
                        mapping=mapping,
                    )
                )
                responder.send(HTTPStatus.OK, plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/openservice/validate":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                service = self.server.application.external_itsm_service
                profile = service.validate_openservice_connector(
                    ValidateOpenServiceConnectorCommand(
                        tenant_id=tenant_id,
                        instance_url=self._required_payload_value(payload, "instance_url"),
                        collection=str(payload.get("collection", "configuration_item")),
                        auth_secret_ref=self._required_payload_value(payload, "auth_secret_ref"),
                        enabled=bool(payload.get("enabled", True)),
                    )
                )
                responder.send(HTTPStatus.OK, profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/integrations/itsm/openservice/cmdb-sync-plan":
            try:
                payload = self._read_json_body()
                tenant_id = self._required_payload_value(payload, "tenant_id")
                if self.server.auth_required:
                    self._authenticate(tenant_id, Permission.SECURITY_ADMIN)
                raw_mapping = payload.get("mapping")
                if raw_mapping is not None and not isinstance(raw_mapping, dict):
                    raise OpenInfraError("mapping must be a JSON object")
                mapping = (
                    {str(key): str(value) for key, value in raw_mapping.items()}
                    if isinstance(raw_mapping, dict)
                    else None
                )
                service = self.server.application.external_itsm_service
                plan = service.build_openservice_cmdb_sync_plan(
                    BuildOpenServiceCmdbSyncPlanCommand(
                        tenant_id=tenant_id,
                        resource_key=self._required_payload_value(payload, "resource_key"),
                        direction=str(payload.get("direction", "push_ci")),
                        collection=str(payload.get("collection", "configuration_item")),
                        mapping=mapping,
                    )
                )
                responder.send(HTTPStatus.OK, plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/organization/create":
            try:
                payload = self._read_json_body()
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                organization = self.server.application.itam_support_service.create_organization(
                    CreateItamOrganizationCommand(
                        organization_id=str(payload["organization_id"]),
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                        legal_name=str(payload["legal_name"]),
                        display_name=(
                            None
                            if payload.get("display_name") is None
                            else str(payload.get("display_name"))
                        ),
                        status=str(payload.get("status", "active")),
                        registration_number=str(payload["registration_number"]),
                        tax_identifier=str(payload["tax_identifier"]),
                        country_code=str(payload["country_code"]),
                        city=str(payload["city"]),
                        postal_code=str(payload["postal_code"]),
                        address=str(payload["address"]),
                        contact_email=str(payload["contact_email"]),
                        phone=str(payload.get("phone", "+33000000000")),
                        support_contact=str(payload["support_contact"]),
                        description=(
                            None
                            if payload.get("description") is None
                            else str(payload.get("description"))
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, organization.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/organization/update":
            try:
                payload = self._read_json_body()
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                organization = self.server.application.itam_support_service.update_organization(
                    UpdateItamOrganizationCommand(
                        organization_id=str(payload["organization_id"]),
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                        legal_name=(
                            None
                            if payload.get("legal_name") is None
                            else str(payload.get("legal_name"))
                        ),
                        display_name=(
                            None
                            if payload.get("display_name") is None
                            else str(payload.get("display_name"))
                        ),
                        status=(
                            None if payload.get("status") is None else str(payload.get("status"))
                        ),
                        registration_number=(
                            None
                            if payload.get("registration_number") is None
                            else str(payload.get("registration_number"))
                        ),
                        tax_identifier=(
                            None
                            if payload.get("tax_identifier") is None
                            else str(payload.get("tax_identifier"))
                        ),
                        country_code=(
                            None
                            if payload.get("country_code") is None
                            else str(payload.get("country_code"))
                        ),
                        city=(None if payload.get("city") is None else str(payload.get("city"))),
                        postal_code=(
                            None
                            if payload.get("postal_code") is None
                            else str(payload.get("postal_code"))
                        ),
                        address=(
                            None if payload.get("address") is None else str(payload.get("address"))
                        ),
                        contact_email=(
                            None
                            if payload.get("contact_email") is None
                            else str(payload.get("contact_email"))
                        ),
                        phone=(None if payload.get("phone") is None else str(payload.get("phone"))),
                        support_contact=(
                            None
                            if payload.get("support_contact") is None
                            else str(payload.get("support_contact"))
                        ),
                        description=(
                            None
                            if payload.get("description") is None
                            else str(payload.get("description"))
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, organization.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/organization/delete":
            try:
                payload = self._read_json_body()
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                organization = self.server.application.itam_support_service.delete_organization(
                    DeleteItamOrganizationCommand(
                        organization_id=str(payload["organization_id"]),
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                    )
                )
                responder.send(HTTPStatus.OK, organization.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/partner/create":
            try:
                payload = self._read_json_body()
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                partner = self.server.application.itam_support_service.create_partner(
                    CreateItamPartnerCommand(
                        organization_id=str(payload["organization_id"]),
                        partner_id=str(payload["partner_id"]),
                        kind=str(payload["kind"]),
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                        legal_name=str(payload["legal_name"]),
                        display_name=(
                            None
                            if payload.get("display_name") is None
                            else str(payload.get("display_name"))
                        ),
                        status=str(payload.get("status", "active")),
                        registration_number=str(payload["registration_number"]),
                        tax_identifier=str(payload["tax_identifier"]),
                        country_code=str(payload["country_code"]),
                        city=str(payload["city"]),
                        postal_code=str(payload["postal_code"]),
                        address=str(payload["address"]),
                        contact_email=str(payload["contact_email"]),
                        phone=str(payload["phone"]),
                        support_contact=str(payload["support_contact"]),
                        website=(
                            None if payload.get("website") is None else str(payload.get("website"))
                        ),
                        description=(
                            None
                            if payload.get("description") is None
                            else str(payload.get("description"))
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, partner.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/partner/update":
            try:
                payload = self._read_json_body()
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                partner = self.server.application.itam_support_service.update_partner(
                    UpdateItamPartnerCommand(
                        organization_id=str(payload["organization_id"]),
                        partner_id=str(payload["partner_id"]),
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                        kind=(None if payload.get("kind") is None else str(payload.get("kind"))),
                        legal_name=(
                            None
                            if payload.get("legal_name") is None
                            else str(payload.get("legal_name"))
                        ),
                        display_name=(
                            None
                            if payload.get("display_name") is None
                            else str(payload.get("display_name"))
                        ),
                        status=(
                            None if payload.get("status") is None else str(payload.get("status"))
                        ),
                        registration_number=(
                            None
                            if payload.get("registration_number") is None
                            else str(payload.get("registration_number"))
                        ),
                        tax_identifier=(
                            None
                            if payload.get("tax_identifier") is None
                            else str(payload.get("tax_identifier"))
                        ),
                        country_code=(
                            None
                            if payload.get("country_code") is None
                            else str(payload.get("country_code"))
                        ),
                        city=(None if payload.get("city") is None else str(payload.get("city"))),
                        postal_code=(
                            None
                            if payload.get("postal_code") is None
                            else str(payload.get("postal_code"))
                        ),
                        address=(
                            None if payload.get("address") is None else str(payload.get("address"))
                        ),
                        contact_email=(
                            None
                            if payload.get("contact_email") is None
                            else str(payload.get("contact_email"))
                        ),
                        phone=(None if payload.get("phone") is None else str(payload.get("phone"))),
                        support_contact=(
                            None
                            if payload.get("support_contact") is None
                            else str(payload.get("support_contact"))
                        ),
                        website=(
                            None if payload.get("website") is None else str(payload.get("website"))
                        ),
                        description=(
                            None
                            if payload.get("description") is None
                            else str(payload.get("description"))
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, partner.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/partner/delete":
            try:
                payload = self._read_json_body()
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                partner = self.server.application.itam_support_service.delete_partner(
                    DeleteItamPartnerCommand(
                        organization_id=str(payload["organization_id"]),
                        partner_id=str(payload["partner_id"]),
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                    )
                )
                responder.send(HTTPStatus.OK, partner.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/tenant/create":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                tenant = self.server.application.itam_support_service.create_tenant(
                    CreateItamTenantCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                        scope_tenant_id=scope_tenant_id,
                        organization_id=str(payload.get("organization_id", "default")),
                        status=str(payload.get("status", "active")),
                        is_default=bool(payload.get("is_default", False)),
                        description=(
                            None
                            if payload.get("description") is None
                            else str(payload.get("description"))
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, tenant.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/tenant/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                tenant = self.server.application.itam_support_service.update_tenant(
                    UpdateItamTenantCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                        organization_id=(
                            None
                            if payload.get("organization_id") is None
                            else str(payload.get("organization_id"))
                        ),
                        name=(None if payload.get("name") is None else str(payload.get("name"))),
                        status=(
                            None if payload.get("status") is None else str(payload.get("status"))
                        ),
                        is_default=(
                            None
                            if payload.get("is_default") is None
                            else bool(payload.get("is_default"))
                        ),
                        description=(
                            None
                            if payload.get("description") is None
                            else str(payload.get("description"))
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, tenant.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/tenant/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                scope_tenant_id = str(payload.get("scope_tenant_id", "default"))
                if self.server.auth_required:
                    principal = self._authenticate(scope_tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                tenant = self.server.application.itam_support_service.delete_tenant(
                    DeleteItamTenantCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        admin_token=self._bearer_token(),
                        scope_tenant_id=scope_tenant_id,
                    )
                )
                responder.send(HTTPStatus.OK, tenant.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/support-profile/manufacturer":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                manufacturer_support_profile = (
                    self.server.application.itam_support_service.register_manufacturer_support(
                        RegisterManufacturerSupportCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            admin_token=self._bearer_token(),
                            asset_tag=str(payload["asset_tag"]),
                            manufacturer=str(
                                payload.get("manufacturer", payload["manufacturer_partner_id"])
                            ),
                            manufacturer_partner_id=str(payload["manufacturer_partner_id"]),
                            warranty_reference=str(payload["warranty_reference"]),
                            warranty_level=str(payload["warranty_level"]),
                            warranty_start=str(payload["warranty_start"]),
                            warranty_end=str(payload["warranty_end"]),
                            support_reference=str(payload["support_reference"]),
                            support_level=str(payload["support_level"]),
                            support_contact=str(payload["support_contact"]),
                        )
                    )
                )
                responder.send(HTTPStatus.CREATED, manufacturer_support_profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/support-profile/third-party":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                third_party_support_profile = (
                    self.server.application.itam_support_service.add_third_party_support(
                        AddThirdPartySupportCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            admin_token=self._bearer_token(),
                            asset_tag=str(payload["asset_tag"]),
                            provider=str(payload.get("provider", payload["provider_partner_id"])),
                            provider_partner_id=str(payload["provider_partner_id"]),
                            contract_reference=str(payload["contract_reference"]),
                            support_level=str(payload["support_level"]),
                            support_start=str(payload["support_start"]),
                            support_end=str(payload["support_end"]),
                            support_contact=str(payload["support_contact"]),
                            status=str(payload.get("status", "active")),
                            notes=(
                                None if payload.get("notes") is None else str(payload.get("notes"))
                            ),
                        )
                    )
                )
                responder.send(HTTPStatus.CREATED, third_party_support_profile.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/software-license":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                license_ = self.server.application.itam_support_service.register_software_license(
                    RegisterSoftwareLicenseCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        admin_token=self._bearer_token(),
                        product_name=str(payload["product_name"]),
                        vendor=str(payload.get("vendor", payload["vendor_partner_id"])),
                        vendor_partner_id=str(payload["vendor_partner_id"]),
                        license_reference=str(payload["license_reference"]),
                        metric=str(payload["metric"]),
                        purchased_quantity=int(payload["purchased_quantity"]),
                        assigned_quantity=int(payload.get("assigned_quantity", 0)),
                        entitlement_start=str(payload["entitlement_start"]),
                        entitlement_end=str(payload["entitlement_end"]),
                        contract_reference=(
                            None
                            if payload.get("contract_reference") is None
                            else str(payload.get("contract_reference"))
                        ),
                        version=(
                            None if payload.get("version") is None else str(payload.get("version"))
                        ),
                        status=str(payload.get("status", "active")),
                        owner=(None if payload.get("owner") is None else str(payload.get("owner"))),
                        notes=(None if payload.get("notes") is None else str(payload.get("notes"))),
                    )
                )
                responder.send(HTTPStatus.CREATED, license_.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/itam/software-license/assignment":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.ITAM_WRITE)
                    actor = principal.subject
                license_ = (
                    self.server.application.itam_support_service.update_software_license_assignment(
                        UpdateSoftwareLicenseAssignmentCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            admin_token=self._bearer_token(),
                            license_reference=str(payload["license_reference"]),
                            assigned_quantity=int(payload["assigned_quantity"]),
                            notes=(
                                None if payload.get("notes") is None else str(payload.get("notes"))
                            ),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, license_.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/site/create":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.create_site(
                    CreateDcimSiteCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        code=str(payload["code"]),
                        name=str(payload["name"]),
                        country=str(payload["country"]),
                        city=str(payload["city"]),
                        region=str(payload.get("region", "")),
                        street_address=str(payload["street_address"]),
                        postal_code=str(payload["postal_code"]),
                        contact_email=str(payload["contact_email"]),
                        phone=str(payload["phone"]),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/site/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.update_site(
                    UpdateDcimSiteCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        code=str(payload["code"]),
                        name=str(payload["name"]) if payload.get("name") else None,
                        country=str(payload["country"]) if payload.get("country") else None,
                        city=str(payload["city"]) if payload.get("city") else None,
                        region=str(payload["region"])
                        if payload.get("region") is not None
                        else None,
                        street_address=str(payload["street_address"])
                        if payload.get("street_address") is not None
                        else None,
                        postal_code=str(payload["postal_code"])
                        if payload.get("postal_code") is not None
                        else None,
                        contact_email=str(payload["contact_email"])
                        if payload.get("contact_email") is not None
                        else None,
                        phone=str(payload["phone"]) if payload.get("phone") is not None else None,
                        status=str(payload["status"]) if payload.get("status") else None,
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/site/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.delete_site(
                    DeleteDcimSiteCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        code=str(payload["code"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/building/create":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.create_building(
                    CreateDcimBuildingCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]),
                        building_type=str(
                            payload.get("building_type") or payload.get("type_batiment") or "simple"
                        ),
                        initial_level=int(payload["initial_level"])
                        if payload.get("initial_level") is not None
                        else None,
                        final_level=int(payload["final_level"])
                        if payload.get("final_level") is not None
                        else None,
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/building/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.update_building(
                    UpdateDcimBuildingCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]) if payload.get("name") else None,
                        status=str(payload["status"]) if payload.get("status") else None,
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/building/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.delete_building(
                    DeleteDcimBuildingCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        code=str(payload["code"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/floor/create":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.create_floor(
                    CreateDcimFloorCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]),
                        level_index=int(payload["level_index"]),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/floor/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.update_floor(
                    UpdateDcimFloorCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]) if payload.get("name") else None,
                        level_index=(
                            int(payload["level_index"])
                            if payload.get("level_index") is not None
                            else None
                        ),
                        status=str(payload["status"]) if payload.get("status") else None,
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/floor/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.delete_floor(
                    DeleteDcimFloorCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        code=str(payload["code"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/room/create":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.create_room(
                    CreateDcimRoomCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        floor=(str(payload["floor"]) if payload.get("floor") else None),
                        code=str(payload["code"]),
                        name=str(payload["name"]),
                        rows=self._tuple_payload(payload, "rows", ()),
                        columns=self._tuple_payload(payload, "columns", ()),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/room/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.update_room(
                    UpdateDcimRoomCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]) if payload.get("name") else None,
                        rows=(
                            self._tuple_payload(payload, "rows", ())
                            if payload.get("rows") is not None
                            else None
                        ),
                        columns=(
                            self._tuple_payload(payload, "columns", ())
                            if payload.get("columns") is not None
                            else None
                        ),
                        status=str(payload["status"]) if payload.get("status") else None,
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/room/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.delete_room(
                    DeleteDcimRoomCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        code=str(payload["code"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/zone/create":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.create_zone(
                    CreateDcimZoneCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]),
                        rows=self._tuple_payload(payload, "rows", ()),
                        columns=self._tuple_payload(payload, "columns", ()),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/zone/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.update_zone(
                    UpdateDcimZoneCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        code=str(payload["code"]),
                        name=str(payload["name"]) if payload.get("name") else None,
                        rows=(
                            self._tuple_payload(payload, "rows", ())
                            if payload.get("rows") is not None
                            else None
                        ),
                        columns=(
                            self._tuple_payload(payload, "columns", ())
                            if payload.get("columns") is not None
                            else None
                        ),
                        status=str(payload["status"]) if payload.get("status") else None,
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/zone/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.delete_zone(
                    DeleteDcimZoneCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        code=str(payload["code"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rooms":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_topology_service.define_room(
                    DefinePhysicalRoomCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site_code=str(payload["site_code"]),
                        site_name=str(payload["site_name"]),
                        country=str(payload["country"]),
                        region=str(payload.get("region", "")),
                        city=str(payload["city"]),
                        building_code=str(payload["building_code"]),
                        building_name=str(payload["building_name"]),
                        floor_code=(
                            str(payload["floor_code"]) if payload.get("floor_code") else None
                        ),
                        floor_name=(
                            str(payload["floor_name"]) if payload.get("floor_name") else None
                        ),
                        floor_index=int(payload["floor_index"]),
                        room_code=str(payload["room_code"]),
                        room_name=str(payload["room_name"]),
                        rows=self._tuple_payload(payload, "rows", ()),
                        columns=self._tuple_payload(payload, "columns", ()),
                        zone_code=(str(payload["zone_code"]) if payload.get("zone_code") else None),
                        zone_name=(str(payload["zone_name"]) if payload.get("zone_name") else None),
                        zone_rows=self._tuple_payload(payload, "zone_rows", ()),
                        zone_columns=self._tuple_payload(payload, "zone_columns", ()),
                        x=(float(payload["x"]) if payload.get("x") is not None else None),
                        y=(float(payload["y"]) if payload.get("y") is not None else None),
                        z=(float(payload["z"]) if payload.get("z") is not None else None),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/racks":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_rack_service.define_rack(
                    DefineRackCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        floor=(str(payload["floor"]) if payload.get("floor") else None),
                        room=str(payload["room"]),
                        zone=(str(payload["zone"]) if payload.get("zone") else None),
                        rack=str(payload["rack"]),
                        row=str(payload["row"]),
                        column=str(payload["column"]),
                        units=int(payload["units"]),
                        usable_faces=self._tuple_payload(payload, "faces", ("front",)),
                        max_weight_kg=(
                            float(payload["max_weight_kg"])
                            if payload.get("max_weight_kg") is not None
                            else None
                        ),
                        power_capacity_watts=(
                            int(payload["power_capacity_watts"])
                            if payload.get("power_capacity_watts") is not None
                            else None
                        ),
                        x=(float(payload["x"]) if payload.get("x") is not None else None),
                        y=(float(payload["y"]) if payload.get("y") is not None else None),
                        z=(float(payload["z"]) if payload.get("z") is not None else None),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rack/update":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_rack_service.update_rack(
                    UpdateRackCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        rack=str(payload["rack"]),
                        row=str(payload["row"]) if payload.get("row") else None,
                        column=str(payload["column"]) if payload.get("column") else None,
                        units=int(payload["units"]) if payload.get("units") is not None else None,
                        usable_faces=(
                            self._tuple_payload(payload, "faces", ())
                            if payload.get("faces") is not None
                            else None
                        ),
                        max_weight_kg=(
                            float(payload["max_weight_kg"])
                            if payload.get("max_weight_kg") is not None
                            else None
                        ),
                        power_capacity_watts=(
                            int(payload["power_capacity_watts"])
                            if payload.get("power_capacity_watts") is not None
                            else None
                        ),
                        status=str(payload["status"]) if payload.get("status") else None,
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/rack/delete":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_rack_service.delete_rack(
                    DeleteRackCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        rack=str(payload["rack"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/locations":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_LOCATE)
                    actor = principal.subject
                equipment = self.server.application.dcim_service.locate_equipment(
                    LocateEquipmentCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        asset_tag=str(payload["asset_tag"]),
                        equipment_name=str(payload["equipment_name"]),
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        floor=self._optional_payload_value(payload, "floor"),
                        room=str(payload["room"]),
                        zone=self._optional_payload_value(payload, "zone"),
                        row=str(payload["row"]),
                        column=str(payload["column"]),
                        rack=self._optional_payload_value(payload, "rack"),
                        u_position=(
                            int(payload["u_position"])
                            if payload.get("u_position") is not None
                            else None
                        ),
                        rack_face=self._optional_payload_value(payload, "rack_face"),
                        u_height=(
                            int(payload["u_height"])
                            if payload.get("u_height") is not None
                            else None
                        ),
                        x=(float(payload["x"]) if payload.get("x") is not None else None),
                        y=(float(payload["y"]) if payload.get("y") is not None else None),
                        z=(float(payload["z"]) if payload.get("z") is not None else None),
                    )
                )
                responder.send(HTTPStatus.CREATED, equipment.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/patch-panels":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_cabling_service.define_patch_panel(
                    DefinePatchPanelCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        rack=str(payload["rack"]),
                        patch_panel=str(payload["patch_panel"]),
                        rack_face=str(payload.get("rack_face", "front")),
                        u_position=int(payload["u_position"]),
                        u_height=int(payload.get("u_height", 1)),
                        port_count=int(payload["port_count"]),
                        connector=str(payload["connector"]),
                        medium=str(payload["medium"]),
                        label=str(payload.get("label", "")),
                        port_prefix=str(payload.get("port_prefix", "P")),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/ports":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_cabling_service.define_port(
                    DefineDcimPortCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        owner_type=str(payload["owner_type"]),
                        owner_code=str(payload["owner_code"]),
                        port_name=str(payload["port_name"]),
                        connector=str(payload["connector"]),
                        medium=str(payload["medium"]),
                        site=(str(payload["site"]) if payload.get("site") else None),
                        building=(str(payload["building"]) if payload.get("building") else None),
                        room=(str(payload["room"]) if payload.get("room") else None),
                        enabled=bool(payload.get("enabled", True)),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/cables":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                path_payload = payload.get("path_segments", [])
                if not isinstance(path_payload, list):
                    raise OpenInfraError("path_segments must be a list")
                result = self.server.application.dcim_cabling_service.connect_cable(
                    ConnectDcimCableCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        cable_id=str(payload["cable_id"]),
                        a_owner_type=str(payload["a_owner_type"]),
                        a_owner_code=str(payload["a_owner_code"]),
                        a_port_name=str(payload["a_port_name"]),
                        b_owner_type=str(payload["b_owner_type"]),
                        b_owner_code=str(payload["b_owner_code"]),
                        b_port_name=str(payload["b_port_name"]),
                        medium=str(payload["medium"]),
                        status=str(payload.get("status", "installed")),
                        path_segments=tuple(str(segment) for segment in path_payload),
                        length_m=(
                            float(payload["length_m"])
                            if payload.get("length_m") is not None
                            else None
                        ),
                        label=str(payload.get("label", "")),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/power-devices":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_environment_service.define_power_device(
                    DefinePowerDeviceCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        code=str(payload["code"]),
                        kind=str(payload["kind"]),
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        rack=self._optional_payload_value(payload, "rack"),
                        side=self._optional_payload_value(payload, "side"),
                        capacity_watts=int(payload["capacity_watts"]),
                        derating_percent=int(payload.get("derating_percent", 80)),
                        input_source=str(payload.get("input_source", "utility")),
                        output_voltage=int(payload.get("output_voltage", 230)),
                        label=str(payload.get("label", "")),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/power-circuits":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_environment_service.define_power_circuit(
                    DefinePowerCircuitCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        circuit_id=str(payload["circuit_id"]),
                        source_device=str(payload["source_device"]),
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        rack=str(payload["rack"]),
                        side=str(payload["side"]),
                        capacity_watts=int(payload["capacity_watts"]),
                        breaker_rating_amps=int(payload["breaker_rating_amps"]),
                        redundancy_group=str(payload.get("redundancy_group", "default")),
                        label=str(payload.get("label", "")),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/cooling-zones":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_environment_service.define_cooling_zone(
                    DefineCoolingZoneCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        site=str(payload["site"]),
                        building=str(payload["building"]),
                        room=str(payload["room"]),
                        zone=str(payload["zone"]),
                        role=str(payload["role"]),
                        cooling_capacity_watts=int(payload["cooling_capacity_watts"]),
                        supply_temperature_c=float(payload["supply_temperature_c"]),
                        return_temperature_c=float(payload["return_temperature_c"]),
                        label=str(payload.get("label", "")),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/power-reservations":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_WRITE)
                    actor = principal.subject
                result = self.server.application.dcim_environment_service.reserve_equipment_power(
                    ReserveEquipmentPowerCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        asset_tag=str(payload["asset_tag"]),
                        circuit_id=str(payload["circuit_id"]),
                        expected_watts=int(payload["expected_watts"]),
                        label=str(payload.get("label", "")),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/dcim/verify-scan":
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if self.server.auth_required:
                    principal = self._authenticate(tenant_id, Permission.DCIM_IDENTIFY)
                    actor = principal.subject
                proof = self.server.application.dcim_field_operation_service.verify_scan(
                    VerifyEquipmentScanCommand(
                        tenant_id=tenant_id,
                        actor=actor,
                        asset_tag=str(payload["asset_tag"]),
                        payload=str(payload["payload"]),
                    )
                )
                responder.send(HTTPStatus.OK, proof.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/rsot/governance-rules":
            try:
                payload = self._read_json_body()
                rule = self.server.application.source_governance_service.create_rule(
                    CreateSourceGovernanceRuleCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                        object_kind=(
                            str(payload["object_kind"]) if payload.get("object_kind") else None
                        ),
                        attribute_path=str(payload["attribute_path"]),
                        authoritative_source=str(payload["authoritative_source"]),
                        priority=int(payload.get("priority", 100)),
                        freshness_seconds=(
                            int(payload["freshness_seconds"])
                            if payload.get("freshness_seconds") is not None
                            else None
                        ),
                        conflict_strategy=str(payload.get("conflict_strategy", "reject")),
                    )
                )
                responder.send(HTTPStatus.CREATED, rule.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/governance/evaluate":
            try:
                payload = self._read_json_body()
                result = self.server.application.source_governance_service.evaluate(
                    EvaluateSourceGovernanceCommand(
                        tenant_id=str(payload["tenant_id"]),
                        admin_token=self._bearer_token(),
                        object_kind=str(payload["object_kind"]),
                        incoming_source=str(payload["incoming_source"]),
                        existing_attributes_json=json.dumps(
                            payload.get("existing_attributes", {}),
                            sort_keys=True,
                        ),
                        incoming_attributes_json=json.dumps(
                            payload.get("incoming_attributes", {}),
                            sort_keys=True,
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/governance/deactivate-rule":
            try:
                payload = self._read_json_body()
                result = self.server.application.source_governance_service.deactivate_rule(
                    DeactivateSourceGovernanceRuleCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/reconcile-object":
            try:
                payload = self._read_json_body()
                tags_payload = payload.get("tags")
                if tags_payload is not None and not isinstance(tags_payload, list):
                    raise OpenInfraError("tags must be a list")
                result = self.server.application.it_resources_management_service.reconcile_object(
                    ReconcileSourceObjectCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        key=str(payload["key"]),
                        attributes_json=json.dumps(payload.get("attributes", {}), sort_keys=True),
                        source=str(payload["source"]),
                        display_name=(
                            str(payload["display_name"])
                            if payload.get("display_name") is not None
                            else None
                        ),
                        tags=tuple(str(tag) for tag in tags_payload)
                        if tags_payload is not None
                        else None,
                        apply=bool(payload.get("apply", False)),
                        resource_category=(
                            str(payload["resource_category"])
                            if payload.get("resource_category") is not None
                            else None
                        ),
                        resource_type=(
                            str(payload["resource_type"])
                            if payload.get("resource_type") is not None
                            else None
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/objects":
            try:
                payload = self._read_json_body()
                tags_payload = payload.get("tags", [])
                if not isinstance(tags_payload, list):
                    raise OpenInfraError("tags must be a list")
                result = self.server.application.it_resources_management_service.upsert_object(
                    UpsertSourceObjectCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        key=str(payload["key"]),
                        kind=str(payload.get("kind") or payload.get("resource_category") or ""),
                        display_name=str(payload["display_name"]),
                        attributes_json=json.dumps(payload.get("attributes", {}), sort_keys=True),
                        tags=tuple(str(tag) for tag in tags_payload),
                        source=str(payload["source"]),
                        resource_category=(
                            str(payload["resource_category"])
                            if payload.get("resource_category") is not None
                            else None
                        ),
                        resource_type=(
                            str(payload["resource_type"])
                            if payload.get("resource_type") is not None
                            else None
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/rsot/relations":
            try:
                payload = self._read_json_body()
                result = self.server.application.it_resources_management_service.create_relation(
                    CreateSourceRelationCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        relation_type=str(payload["relation_type"]),
                        source_key=str(payload["source_key"]),
                        target_key=str(payload["target_key"]),
                        provenance=str(payload["provenance"]),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/audit/export":
            try:
                payload = self._read_json_body()
                bundle = self.server.application.audit_service.export_events(
                    ExportAuditEventsCommand(
                        tenant_id=str(payload["tenant_id"]),
                        admin_token=self._bearer_token(),
                        format=str(payload.get("format", "jsonl")),
                        limit=int(payload.get("limit", 500)),
                        cursor=str(payload["cursor"]) if payload.get("cursor") else None,
                        actor=str(payload["actor"]) if payload.get("actor") else None,
                        action=str(payload["action"]) if payload.get("action") else None,
                        target_type=(
                            str(payload["target_type"]) if payload.get("target_type") else None
                        ),
                        severity=str(payload["severity"]) if payload.get("severity") else None,
                    )
                )
                responder.send(HTTPStatus.OK, bundle.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/security/whoami":
            try:
                payload = self._read_json_body()
                principal = self.server.application.security_service.inspect_token(
                    str(payload["tenant_id"]),
                    str(payload["token"]),
                )
                responder.send(HTTPStatus.OK, principal.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/security/revoke-token":
            try:
                payload = self._read_json_body()
                result = self.server.application.security_service.revoke_token(
                    RevokeTokenCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        target_token=str(payload["target_token"]),
                        admin_token=(
                            str(payload["admin_token"]) if payload.get("admin_token") else None
                        ),
                    )
                )
                responder.send(HTTPStatus.OK, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/security/rotate-token":
            try:
                payload = self._read_json_body()
                roles_payload = payload.get("roles", [])
                if not isinstance(roles_payload, list):
                    raise OpenInfraError("roles must be a list")
                result = self.server.application.security_service.rotate_token(
                    RotateTokenCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        current_token=str(payload["current_token"]),
                        subject=str(payload["subject"]) if payload.get("subject") else None,
                        roles=tuple(str(role) for role in roles_payload),
                        token=str(payload["token"]) if payload.get("token") else None,
                        ttl_seconds=(
                            int(payload["ttl_seconds"]) if payload.get("ttl_seconds") else None
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, result.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/access/rules":
            try:
                payload = self._read_json_body()
                rule = self.server.application.access_policy_service.create_rule(
                    CreateAccessPolicyRuleCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                        permission=str(payload["permission"]),
                        effect=str(payload["effect"]),
                        subjects=self._tuple_payload(payload, "subjects", ("*",)),
                        roles=self._tuple_payload(payload, "roles", ()),
                        site_codes=self._tuple_payload(payload, "site_codes", ()),
                        environments=self._tuple_payload(payload, "environments", ()),
                    )
                )
                responder.send(HTTPStatus.CREATED, rule.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/access/deactivate-rule":
            try:
                payload = self._read_json_body()
                result = self.server.application.access_policy_service.deactivate_rule(
                    DeactivateAccessPolicyRuleCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/access/evaluate":
            try:
                payload = self._read_json_body()
                result = self.server.application.access_policy_service.evaluate(
                    EvaluateAccessPolicyCommand(
                        tenant_id=str(payload["tenant_id"]),
                        token=str(payload["token"]),
                        permission=str(payload["permission"]),
                        site_code=self._optional_payload_value(payload, "site_code"),
                        environment=self._optional_payload_value(payload, "environment"),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/identity/users":
            try:
                payload = self._read_json_body()
                roles = self._roles_from_payload(payload)
                user = self.server.application.identity_service.create_user(
                    CreateUserCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        username=str(payload["username"]),
                        display_name=str(payload["display_name"]),
                        email=str(payload["email"]) if payload.get("email") else None,
                        roles=roles,
                    )
                )
                responder.send(HTTPStatus.CREATED, user.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/identity/groups":
            try:
                payload = self._read_json_body()
                roles = self._roles_from_payload(payload)
                group = self.server.application.identity_service.create_group(
                    CreateGroupCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                        display_name=str(payload["display_name"]),
                        roles=roles,
                    )
                )
                responder.send(HTTPStatus.CREATED, group.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/identity/group-memberships":
            try:
                payload = self._read_json_body()
                membership = self.server.application.identity_service.add_user_to_group(
                    AddUserToGroupCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        username=str(payload["username"]),
                        group_name=str(payload["group_name"]),
                    )
                )
                responder.send(HTTPStatus.CREATED, membership.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/identity/user-roles":
            try:
                payload = self._read_json_body()
                result = self.server.application.identity_service.grant_user_role(
                    GrantUserRoleCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        username=str(payload["username"]),
                        role=str(payload["role"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/identity/group-roles":
            try:
                payload = self._read_json_body()
                result = self.server.application.identity_service.grant_group_role(
                    GrantGroupRoleCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        group_name=str(payload["group_name"]),
                        role=str(payload["role"]),
                    )
                )
                responder.send(HTTPStatus.OK, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/evidence":
            try:
                payload = self._read_json_body()
                raw_evidence_payload = payload["payload"]
                if not isinstance(raw_evidence_payload, dict):
                    raise OpenInfraError("payload must be a JSON object")
                evidence = self.server.application.discovery_service.submit_evidence(
                    SubmitDiscoveryEvidenceCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        evidence_id=(
                            None
                            if payload.get("evidence_id") is None
                            else str(payload["evidence_id"])
                        ),
                        object_key=str(payload["object_key"]),
                        object_kind=str(payload["object_kind"]),
                        source=str(payload["source"]),
                        source_ref=str(payload["source_ref"]),
                        scope=str(payload["scope"]),
                        external_id=str(payload["external_id"]),
                        confidence=float(payload["confidence"]),
                        payload={str(key): value for key, value in raw_evidence_payload.items()},
                        observed_at=(
                            None
                            if payload.get("observed_at") is None
                            else str(payload["observed_at"])
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, evidence.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/reconciliation":
            try:
                payload = self._read_json_body()
                evidence_ids = payload["evidence_ids"]
                if not isinstance(evidence_ids, list):
                    raise OpenInfraError("evidence_ids must be a JSON array")
                case = self.server.application.discovery_service.reconcile_evidence(
                    ReconcileDiscoveryEvidenceCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        object_key=str(payload["object_key"]),
                        evidence_ids=tuple(str(item) for item in evidence_ids),
                        max_age_seconds=int(payload.get("max_age_seconds", 86_400)),
                    )
                )
                responder.send(HTTPStatus.CREATED, case.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/reconciliation/resolve":
            try:
                payload = self._read_json_body()
                raw_selections = payload["selected_evidence_by_path"]
                if not isinstance(raw_selections, dict):
                    raise OpenInfraError("selected_evidence_by_path must be a JSON object")
                case = self.server.application.discovery_service.resolve_reconciliation(
                    ResolveDiscoveryReconciliationCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        case_id=str(payload["case_id"]),
                        selected_evidence_by_path={
                            str(key): str(value) for key, value in raw_selections.items()
                        },
                        justification=str(payload["justification"]),
                    )
                )
                responder.send(HTTPStatus.OK, case.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/protocol-profile/create":
            try:
                payload = self._read_json_body()
                created_protocol_profile = (
                    self.server.application.discovery_service.create_protocol_profile(
                        CreateDiscoveryProtocolProfileCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            name=str(payload["name"]),
                            protocol=str(payload["protocol"]),
                            scope=str(payload["scope"]),
                            credential_secret_ref=str(payload["credential_secret_ref"]),
                            port=None if payload.get("port") is None else int(payload["port"]),
                            timeout_seconds=int(payload.get("timeout_seconds", 30)),
                            max_concurrency=int(payload.get("max_concurrency", 4)),
                            rate_limit_per_minute=int(payload.get("rate_limit_per_minute", 120)),
                            retry_count=int(payload.get("retry_count", 1)),
                        )
                    )
                )
                responder.send(HTTPStatus.CREATED, created_protocol_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/protocol-profile/update":
            try:
                payload = self._read_json_body()
                updated_protocol_profile = (
                    self.server.application.discovery_service.update_protocol_profile(
                        UpdateDiscoveryProtocolProfileCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            profile_id=str(payload["profile_id"]),
                            name=None if payload.get("name") is None else str(payload["name"]),
                            scope=None if payload.get("scope") is None else str(payload["scope"]),
                            credential_secret_ref=None
                            if payload.get("credential_secret_ref") is None
                            else str(payload["credential_secret_ref"]),
                            port=None if payload.get("port") is None else int(payload["port"]),
                            timeout_seconds=None
                            if payload.get("timeout_seconds") is None
                            else int(payload["timeout_seconds"]),
                            max_concurrency=None
                            if payload.get("max_concurrency") is None
                            else int(payload["max_concurrency"]),
                            rate_limit_per_minute=None
                            if payload.get("rate_limit_per_minute") is None
                            else int(payload["rate_limit_per_minute"]),
                            retry_count=None
                            if payload.get("retry_count") is None
                            else int(payload["retry_count"]),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, updated_protocol_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/protocol-profile/delete":
            try:
                payload = self._read_json_body()
                disabled_protocol_profile = (
                    self.server.application.discovery_service.disable_protocol_profile(
                        DisableDiscoveryProtocolProfileCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            profile_id=str(payload["profile_id"]),
                            reason=str(payload["reason"]),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, disabled_protocol_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/integration-profile/create":
            try:
                payload = self._read_json_body()
                created_integration_profile = (
                    self.server.application.discovery_service.create_integration_profile(
                        CreateDiscoveryIntegrationProfileCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            name=str(payload["name"]),
                            kind=str(payload["kind"]),
                            scope=str(payload["scope"]),
                            endpoint_url=None
                            if payload.get("endpoint_url") is None
                            else str(payload["endpoint_url"]),
                            credential_secret_ref=str(payload["credential_secret_ref"]),
                            verify_tls=bool(payload.get("verify_tls", True)),
                            inventory_enabled=bool(payload.get("inventory_enabled", True)),
                            max_concurrency=int(payload.get("max_concurrency", 4)),
                            rate_limit_per_minute=int(payload.get("rate_limit_per_minute", 120)),
                        )
                    )
                )
                responder.send(HTTPStatus.CREATED, created_integration_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/integration-profile/update":
            try:
                payload = self._read_json_body()
                updated_integration_profile = (
                    self.server.application.discovery_service.update_integration_profile(
                        UpdateDiscoveryIntegrationProfileCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            profile_id=str(payload["profile_id"]),
                            name=None if payload.get("name") is None else str(payload["name"]),
                            scope=None if payload.get("scope") is None else str(payload["scope"]),
                            endpoint_url=None
                            if payload.get("endpoint_url") is None
                            else str(payload["endpoint_url"]),
                            credential_secret_ref=None
                            if payload.get("credential_secret_ref") is None
                            else str(payload["credential_secret_ref"]),
                            verify_tls=None
                            if payload.get("verify_tls") is None
                            else bool(payload["verify_tls"]),
                            inventory_enabled=None
                            if payload.get("inventory_enabled") is None
                            else bool(payload["inventory_enabled"]),
                            max_concurrency=None
                            if payload.get("max_concurrency") is None
                            else int(payload["max_concurrency"]),
                            rate_limit_per_minute=None
                            if payload.get("rate_limit_per_minute") is None
                            else int(payload["rate_limit_per_minute"]),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, updated_integration_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/integration-profile/delete":
            try:
                payload = self._read_json_body()
                disabled_integration_profile = (
                    self.server.application.discovery_service.disable_integration_profile(
                        DisableDiscoveryIntegrationProfileCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            profile_id=str(payload["profile_id"]),
                            reason=str(payload["reason"]),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, disabled_integration_profile.as_public_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/local-plan":
            try:
                payload = self._read_json_body()
                local_discovery_plan = (
                    self.server.application.discovery_service.build_local_discovery_plan(
                        BuildLocalDiscoveryPlanCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            name=str(payload["name"]),
                            scope=str(payload["scope"]),
                            protocol=str(payload["protocol"]),
                            targets=tuple(str(item) for item in payload["targets"]),
                            credential_secret_ref=str(payload["credential_secret_ref"]),
                            max_concurrency=int(payload.get("max_concurrency", 4)),
                            rate_limit_per_minute=int(payload.get("rate_limit_per_minute", 120)),
                            protocol_profile_id=None
                            if payload.get("protocol_profile_id") is None
                            else str(payload["protocol_profile_id"]),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, local_discovery_plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/agent-bootstrap-plan":
            try:
                payload = self._read_json_body()
                agent_bootstrap_plan = (
                    self.server.application.discovery_service.build_enterprise_agent_bootstrap_plan(
                        BuildEnterpriseAgentBootstrapPlanCommand(
                            tenant_id=str(payload["tenant_id"]),
                            actor=str(payload.get("actor", "api")),
                            admin_token=self._bearer_token(),
                            name=str(payload["name"]),
                            role=str(payload.get("role", "site")),
                            scopes=tuple(str(item) for item in payload["scopes"]),
                            backend_url=str(payload["backend_url"]),
                            certificate_fingerprint=str(payload["certificate_fingerprint"]),
                            enrollment_secret_ref=str(payload["enrollment_secret_ref"]),
                            agent_version=str(payload.get("agent_version", __version__)),
                            service_user=str(payload.get("service_user", "openinfra-agent")),
                            config_path=str(
                                payload.get("config_path", "/etc/openinfra/agent.yaml")
                            ),
                            state_directory=str(
                                payload.get("state_directory", "/var/lib/openinfra-agent")
                            ),
                            log_directory=str(
                                payload.get("log_directory", "/var/log/openinfra-agent")
                            ),
                        )
                    )
                )
                responder.send(HTTPStatus.OK, agent_bootstrap_plan.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/proxy-enrollments":
            try:
                payload = self._read_json_body()
                collector = self.server.application.discovery_service.enroll_proxy(
                    EnrollDiscoveryProxyCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                        kind=str(payload["kind"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        scopes=tuple(str(item) for item in payload["scopes"]),
                        version=str(payload["version"]),
                        vault_secret_ref=(
                            None
                            if payload.get("vault_secret_ref") is None
                            else str(payload["vault_secret_ref"])
                        ),
                        endpoint_url=str(payload["endpoint_url"]),
                    )
                )
                response = collector.as_dict()
                response["enrollment_type"] = "enterprise_proxy"
                responder.send(HTTPStatus.CREATED, response)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/collectors":
            try:
                payload = self._read_json_body()
                collector = self.server.application.discovery_service.register_collector(
                    RegisterCollectorCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        name=str(payload["name"]),
                        kind=str(payload["kind"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        scopes=tuple(str(item) for item in payload["scopes"]),
                        version=str(payload["version"]),
                        vault_secret_ref=(
                            None
                            if payload.get("vault_secret_ref") is None
                            else str(payload["vault_secret_ref"])
                        ),
                        endpoint_url=(
                            None
                            if payload.get("endpoint_url") is None
                            else str(payload["endpoint_url"])
                        ),
                    )
                )
                responder.send(HTTPStatus.CREATED, collector.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/collectors/heartbeat":
            try:
                payload = self._read_json_body()
                collector = self.server.application.discovery_service.heartbeat(
                    HeartbeatCollectorCommand(
                        tenant_id=str(payload["tenant_id"]),
                        collector_id=str(payload["collector_id"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        version=str(payload["version"]),
                        status=str(payload.get("status", "ok")),
                    )
                )
                responder.send(HTTPStatus.OK, collector.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs":
            try:
                payload = self._read_json_body()
                discovery_job = self.server.application.discovery_service.submit_job(
                    SubmitDiscoveryJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        collector_id=str(payload["collector_id"]),
                        requested_scope=str(payload["requested_scope"]),
                        job_type=str(payload["job_type"]),
                        target=str(payload["target"]),
                        idempotency_key=str(payload["idempotency_key"]),
                        max_attempts=int(payload.get("max_attempts", 3)),
                    )
                )
                responder.send(HTTPStatus.CREATED, discovery_job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs/claim":
            try:
                payload = self._read_json_body()
                claimed_job = self.server.application.discovery_service.claim_job(
                    ClaimDiscoveryJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        collector_id=str(payload["collector_id"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        worker_id=str(payload["worker_id"]),
                        lease_seconds=int(payload.get("lease_seconds", 60)),
                    )
                )
                responder.send(
                    HTTPStatus.OK,
                    {"job": None if claimed_job is None else claimed_job.as_dict()},
                )
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs/renew":
            try:
                payload = self._read_json_body()
                discovery_job = self.server.application.discovery_service.renew_job_lease(
                    RenewDiscoveryJobLeaseCommand(
                        tenant_id=str(payload["tenant_id"]),
                        collector_id=str(payload["collector_id"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        job_id=str(payload["job_id"]),
                        worker_id=str(payload["worker_id"]),
                        lease_token=int(payload["lease_token"]),
                        lease_seconds=int(payload.get("lease_seconds", 60)),
                    )
                )
                responder.send(HTTPStatus.OK, discovery_job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs/complete":
            try:
                payload = self._read_json_body()
                discovery_job = self.server.application.discovery_service.complete_job(
                    CompleteDiscoveryJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        collector_id=str(payload["collector_id"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        job_id=str(payload["job_id"]),
                        worker_id=str(payload["worker_id"]),
                        lease_token=int(payload["lease_token"]),
                        result_hash=str(payload["result_hash"]),
                    )
                )
                responder.send(HTTPStatus.OK, discovery_job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs/fail":
            try:
                payload = self._read_json_body()
                discovery_job = self.server.application.discovery_service.fail_job(
                    FailDiscoveryJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        collector_id=str(payload["collector_id"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        job_id=str(payload["job_id"]),
                        worker_id=str(payload["worker_id"]),
                        lease_token=int(payload["lease_token"]),
                        error=str(payload["error"]),
                        retry_delay_seconds=int(payload.get("retry_delay_seconds", 30)),
                    )
                )
                responder.send(HTTPStatus.OK, discovery_job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs/replay":
            try:
                payload = self._read_json_body()
                discovery_job = self.server.application.discovery_service.replay_dead_letter_job(
                    ReplayDiscoveryDeadLetterJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        job_id=str(payload["job_id"]),
                    )
                )
                responder.send(HTTPStatus.OK, discovery_job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError, TypeError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/jobs/authorize":
            try:
                payload = self._read_json_body()
                decision = self.server.application.discovery_service.authorize_job(
                    AuthorizeDiscoveryJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        collector_id=str(payload["collector_id"]),
                        certificate_fingerprint=str(payload["certificate_fingerprint"]),
                        requested_scope=str(payload["requested_scope"]),
                        job_type=str(payload["job_type"]),
                        target=str(payload["target"]),
                    )
                )
                status = HTTPStatus.OK if decision.authorized else HTTPStatus.FORBIDDEN
                responder.send(status, decision.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/discovery/collectors/disable":
            try:
                payload = self._read_json_body()
                collector = self.server.application.discovery_service.disable_collector(
                    DisableCollectorCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        collector_id=str(payload["collector_id"]),
                        reason=str(payload["reason"]),
                    )
                )
                responder.send(HTTPStatus.OK, collector.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/migration-plans":
            try:
                payload = self._read_json_body()
                migration_report = self.server.application.import_service.plan_migration(
                    PlanMigrationCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=str(payload["admin_token"]),
                        source=str(payload["source"]),
                        file_path=Path(str(payload["file_path"])),
                        format=str(payload["format"]),
                        sample_limit=int(payload.get("sample_limit", 100)),
                    )
                )
                responder.send(HTTPStatus.OK, migration_report.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/exports/jobs":
            try:
                payload = self._read_json_body()
                job = self.server.application.export_service.request_export(
                    RequestExportCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=str(payload["admin_token"]),
                        resource=str(payload.get("resource", "source_objects")),
                        format=str(payload.get("format", "json")),
                        kind=None if payload.get("kind") is None else str(payload["kind"]),
                        tag=None if payload.get("tag") is None else str(payload["tag"]),
                        limit=int(payload.get("limit", 100_000)),
                    )
                )
                responder.send(HTTPStatus.ACCEPTED, job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/exports/run":
            try:
                payload = self._read_json_body()
                job = self.server.application.export_service.run_export_job(
                    RunExportJobCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=str(payload["admin_token"]),
                        job_id=None if payload.get("job_id") is None else str(payload["job_id"]),
                        page_size=int(payload.get("page_size", 500)),
                    )
                )
                responder.send(HTTPStatus.OK, job.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/datasets":
            try:
                payload = self._read_json_body()
                import_report = self.server.application.import_service.import_dataset(
                    ImportDatasetCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=str(payload["admin_token"]),
                        file_path=Path(str(payload["file_path"])),
                        format=str(payload["format"]),
                        mapping_json=json.dumps(payload["mapping"], sort_keys=True),
                        dry_run=not bool(payload.get("apply", False)),
                        batch_size=int(payload.get("batch_size", 500)),
                    )
                )
                status = HTTPStatus.OK if import_report.dry_run else HTTPStatus.CREATED
                responder.send(status, import_report.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/bulk-datasets":
            try:
                payload = self._read_json_body()
                bulk_report = self.server.application.import_service.bulk_import_dataset(
                    BulkImportDatasetCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=str(payload["admin_token"]),
                        file_path=Path(str(payload["file_path"])),
                        format=str(payload["format"]),
                        mapping_json=json.dumps(payload["mapping"], sort_keys=True),
                        dry_run=not bool(payload.get("apply", False)),
                        batch_size=int(payload.get("batch_size", 5_000)),
                        checkpoint_interval=int(payload.get("checkpoint_interval", 25_000)),
                        resume_job_id=(
                            str(payload["resume_job_id"]) if payload.get("resume_job_id") else None
                        ),
                        sample_limit=int(payload.get("sample_limit", 100)),
                    )
                )
                status = HTTPStatus.OK if bulk_report.dry_run else HTTPStatus.CREATED
                responder.send(status, bulk_report.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/imports/bulk-rollback":
            try:
                payload = self._read_json_body()
                rollback_report = self.server.application.import_service.bulk_import_rollback(
                    BulkImportRollbackCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=str(payload["admin_token"]),
                        import_job_id=str(payload["job_id"]),
                        file_path=Path(str(payload["file_path"])),
                        format=str(payload["format"]),
                        mapping_json=json.dumps(payload["mapping"], sort_keys=True),
                        dry_run=not bool(payload.get("apply", False)),
                        conflict_policy=str(payload.get("conflict_policy", "fail")),
                    )
                )
                status = HTTPStatus.OK if rollback_report.dry_run else HTTPStatus.CREATED
                responder.send(status, rollback_report.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route in (
            "/api/v1/ipam/vrfs",
            "/api/v1/ipam/aggregates",
            "/api/v1/ipam/prefixes",
            "/api/v1/ipam/ranges",
            "/api/v1/ipam/addresses",
            "/api/v1/ipam/vlan-groups",
            "/api/v1/ipam/vxlan-vnis",
            "/api/v1/ipam/vlans",
            "/api/v1/ipam/asns",
            "/api/v1/ipam/bgp-peers",
            "/api/v1/ipam/dns-observations",
            "/api/v1/ipam/dhcp-leases",
        ):
            try:
                payload = self._read_json_body()
                tenant_id = str(payload["tenant_id"])
                actor = str(payload.get("actor", "api"))
                if route == "/api/v1/ipam/vrfs":
                    result = self.server.application.ipam_model_service.define_vrf(
                        DefineVrfCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            name=str(payload["name"]),
                            route_distinguisher=(
                                str(payload["route_distinguisher"])
                                if payload.get("route_distinguisher")
                                else None
                            ),
                        )
                    )
                elif route == "/api/v1/ipam/aggregates":
                    result = self.server.application.ipam_model_service.define_aggregate(
                        DefineIpAggregateCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            cidr=str(payload["cidr"]),
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/prefixes":
                    result = self.server.application.ipam_model_service.define_prefix(
                        DefineIpPrefixCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            cidr=str(payload["cidr"]),
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/ranges":
                    result = self.server.application.ipam_model_service.define_range(
                        DefineIpRangeCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            prefix=str(payload["prefix"]),
                            start=str(payload["start"]),
                            end=str(payload["end"]),
                            purpose=str(payload.get("purpose", "allocation")),
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/addresses":
                    result = self.server.application.ipam_model_service.register_address(
                        RegisterIpAddressCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            prefix=str(payload["prefix"]),
                            address=str(payload["address"]),
                            hostname=str(payload["hostname"]),
                            interface_name=(
                                str(payload["interface_name"])
                                if payload.get("interface_name")
                                else None
                            ),
                            status=str(payload.get("status", "reserved")),
                        )
                    )
                elif route == "/api/v1/ipam/vlan-groups":
                    result = self.server.application.ipam_model_service.define_vlan_group(
                        DefineVlanGroupCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            name=str(payload["name"]),
                            scope=str(payload["scope"]) if payload.get("scope") else None,
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/vxlan-vnis":
                    result = self.server.application.ipam_model_service.define_vxlan_vni(
                        DefineVxlanVniCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vni=int(payload["vni"]),
                            name=str(payload["name"]),
                            vrf=str(payload["vrf"]),
                            route_targets_import=self._tuple_payload(
                                payload, "route_targets_import", ()
                            ),
                            route_targets_export=self._tuple_payload(
                                payload, "route_targets_export", ()
                            ),
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/vlans":
                    result = self.server.application.ipam_model_service.define_vlan(
                        DefineVlanCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            group=str(payload["group"]),
                            vlan_id=int(payload["vlan_id"]),
                            name=str(payload["name"]),
                            vrf=str(payload["vrf"]) if payload.get("vrf") else None,
                            vni=int(payload["vni"]) if payload.get("vni") is not None else None,
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/asns":
                    result = self.server.application.ipam_model_service.define_asn(
                        DefineAsnCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            asn=int(payload["asn"]),
                            name=str(payload["name"]),
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/bgp-peers":
                    result = self.server.application.ipam_model_service.define_bgp_peer(
                        DefineBgpPeerCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            local_asn=int(payload["local_asn"]),
                            remote_asn=int(payload["remote_asn"]),
                            peer_address=str(payload["peer_address"]),
                            address_family=(
                                str(payload["address_family"])
                                if payload.get("address_family")
                                else None
                            ),
                            route_targets_import=self._tuple_payload(
                                payload, "route_targets_import", ()
                            ),
                            route_targets_export=self._tuple_payload(
                                payload, "route_targets_export", ()
                            ),
                            description=str(payload.get("description", "")),
                        )
                    )
                elif route == "/api/v1/ipam/dns-observations":
                    result = self.server.application.ipam_conflict_service.observe_dns(
                        ObserveDnsRecordCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            hostname=str(payload["hostname"]),
                            address=str(payload["address"]),
                            ptr_hostname=(
                                str(payload["ptr_hostname"])
                                if payload.get("ptr_hostname")
                                else None
                            ),
                            source=str(payload.get("source", "api")),
                        )
                    )
                else:
                    result = self.server.application.ipam_conflict_service.observe_dhcp_lease(
                        ObserveDhcpLeaseCommand(
                            tenant_id=tenant_id,
                            actor=actor,
                            vrf=str(payload["vrf"]),
                            prefix=str(payload["prefix"]),
                            address=str(payload["address"]),
                            mac_address=str(payload["mac_address"]),
                            hostname=str(payload["hostname"]),
                            source=str(payload.get("source", "api")),
                            active=bool(payload.get("active", True)),
                        )
                    )
                responder.send(HTTPStatus.CREATED, result)
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/ipam/ddi-preview":
            try:
                payload = self._read_json_body()
                preview = self.server.application.ipam_ddi_service.preview_reservation(
                    PreviewDdiReservationCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        vrf=str(payload["vrf"]),
                        idempotency_key=str(payload["idempotency_key"]),
                        providers=self._tuple_payload(payload, "providers", ("all",)),
                        dns_zone=str(payload["dns_zone"]) if payload.get("dns_zone") else None,
                        mac_address=(
                            str(payload["mac_address"]) if payload.get("mac_address") else None
                        ),
                        ttl=int(payload.get("ttl", 300)),
                        dry_run=not bool(payload.get("apply_preview", False)),
                    )
                )
                responder.send(HTTPStatus.OK, preview.as_dict())
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if route == "/api/v1/ipam/reservation-wizard":
            try:
                payload = self._read_json_body()
                result = self.server.application.ipam_ui_service.reservation_wizard(
                    IpamReservationWizardCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        vrf=str(payload["vrf"]),
                        prefix=str(payload["prefix"]),
                        hostname=str(payload["hostname"]),
                        idempotency_key=str(payload["idempotency_key"]),
                        dry_run=not bool(payload.get("apply", False)),
                    )
                )
                status = HTTPStatus.OK if bool(result.get("dry_run", False)) else HTTPStatus.CREATED
                responder.send(status, result)
            except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route != "/api/v1/ipam/allocate":
            responder.send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            payload = self._read_json_body()
            tenant_id = str(payload["tenant_id"])
            actor = str(payload.get("actor", "api"))
            if self.server.auth_required:
                principal = self._authenticate(tenant_id, Permission.IPAM_ALLOCATE)
                self.server.application.access_policy_service.authorize(
                    principal,
                    AccessRequestContext.create(
                        principal.tenant_id,
                        Permission.IPAM_ALLOCATE,
                        self._optional_payload_value(payload, "site_code"),
                        self._optional_payload_value(payload, "environment"),
                    ),
                )
                actor = principal.subject
            result = self.server.application.ipam_service.allocate(
                AllocateIpCommand(
                    tenant_id=tenant_id,
                    actor=actor,
                    vrf=str(payload["vrf"]),
                    prefix=str(payload["prefix"]),
                    hostname=str(payload["hostname"]),
                    idempotency_key=str(payload["idempotency_key"]),
                )
            )
            status = HTTPStatus.CREATED if result.created else HTTPStatus.OK
            responder.send(status, result.as_dict())
        except AccessDeniedError as exc:
            responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
        except (KeyError, json.JSONDecodeError, OpenInfraError) as exc:
            responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _first_query_value(
        self,
        query: dict[str, list[str]],
        name: str,
        default: str | None = None,
    ) -> str:
        values = query.get(name)
        if not values or values[0] == "":
            if default is None:
                raise OpenInfraError("missing query parameter: " + name)
            return default
        return values[0]

    def _optional_query_value(self, query: dict[str, list[str]], name: str) -> str | None:
        values = query.get(name)
        if not values or values[0] == "":
            return None
        return values[0]

    def _bearer_token(self) -> str:
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            raise AccessDeniedError("missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise AccessDeniedError("missing bearer token")
        return token

    def _authenticate(self, tenant_id: str, permission: Permission) -> AuthenticatedPrincipal:
        token = self._bearer_token()
        return self.server.application.security_service.authenticate_token(
            AuthenticateTokenCommand(
                tenant_id=tenant_id,
                token=token,
                required_permission=permission,
            )
        )

    def _tuple_payload(
        self,
        payload: dict[str, Any],
        name: str,
        default: tuple[str, ...],
    ) -> tuple[str, ...]:
        value = payload.get(name)
        if value is None:
            return default
        if not isinstance(value, list):
            raise OpenInfraError(name + " must be a list")
        return tuple(str(item) for item in value)

    @staticmethod
    def _payload_bool(payload: dict[str, Any], name: str, default: bool) -> bool:
        value = payload.get(name, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        raise OpenInfraError(name + " must be a boolean")

    def _optional_payload_value(self, payload: dict[str, Any], name: str) -> str | None:
        value = payload.get(name)
        if value is None or str(value).strip() == "":
            return None
        return str(value)

    def _required_payload_value(self, payload: dict[str, Any], name: str) -> str:
        value = self._optional_payload_value(payload, name)
        if value is None:
            raise OpenInfraError(name + " is required")
        return value

    def _roles_from_payload(self, payload: dict[str, Any]) -> tuple[str, ...]:
        roles_payload = payload.get("roles", [])
        if not isinstance(roles_payload, list):
            raise OpenInfraError("roles must be a list")
        return tuple(str(role) for role in roles_payload)

    @staticmethod
    def _canonical_route(route: str) -> str:
        if route.startswith("/api/v1/rsot/"):
            return route
        if route == "/api/v1/rsot":
            return route
        for legacy_prefix in ("/api/v1/itrm", "/api/v1/sot", "/api/v1/ri"):
            if route.startswith(legacy_prefix + "/"):
                return "/api/v1/rsot/" + route.removeprefix(legacy_prefix + "/")
            if route == legacy_prefix:
                return "/api/v1/rsot"
        return route

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > 1_048_576:
            raise OpenInfraError("invalid content length")
        raw = self.rfile.read(content_length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise OpenInfraError("json body must be an object")
        return payload


class OpenInfraThreadingServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        application: OpenInfraApplication,
        auth_required: bool = False,
        openapi_path: str | None = None,
    ) -> None:
        super().__init__(server_address, OpenInfraRequestHandler)
        self.application = application
        self.auth_required = auth_required
        self.openapi_document_provider = OpenApiDocumentProvider(openapi_path)

    def discovery_document(self) -> dict[str, object]:
        return {
            "service": "openinfra-api",
            "version": __version__,
            "status": "ok",
            "health": "/health",
            "readiness": "/ready",
            "api": {
                "version": "v1",
                "base_path": "/api/v1",
                "version_url": "/api/v1/version",
                "schema_url": "/api/v1/database/schema",
                "openapi_url": "/openapi.yaml",
            },
            "documentation": {
                "swagger_ui": "/docs",
                "swagger_alias": "/swagger",
                "redoc": "/redoc",
                "openapi_yaml": "/openapi.yaml",
                "versioned_openapi_yaml": "/api/v1/openapi.yaml",
                "exports": {
                    "request": "/api/v1/exports/jobs",
                    "run": "/api/v1/exports/run",
                    "report": "/api/v1/exports/jobs",
                    "artifact": "/api/v1/exports/artifact",
                    "artifact_chunk": "/api/v1/exports/artifact-chunk",
                },
                "imports": {
                    "dataset": "/api/v1/imports/datasets",
                    "bulk_dataset": "/api/v1/imports/bulk-datasets",
                    "bulk_report": "/api/v1/imports/bulk-report",
                    "bulk_checkpoint": "/api/v1/imports/bulk-checkpoint",
                    "bulk_progress": "/api/v1/imports/bulk-progress",
                    "bulk_rollback": "/api/v1/imports/bulk-rollback",
                    "migration_template": "/api/v1/imports/migration-template",
                    "migration_guide": "/api/v1/imports/migration-guide",
                    "migration_plans": "/api/v1/imports/migration-plans",
                    "migration_report": "/api/v1/imports/migration-report",
                },
                "search": {"global": "/api/v1/search/global"},
                "editions": {
                    "policies": "/api/v1/editions/policies",
                    "feature_check": "/api/v1/editions/feature-check",
                    "quota_check": "/api/v1/editions/quota-check",
                },
                "reference": {"countries": "/api/v1/reference/countries"},
                "integrations": {
                    "itsm_providers": "/api/v1/integrations/itsm/providers",
                    "servicenow_validate": "/api/v1/integrations/itsm/servicenow/validate",
                    "servicenow_ci_sync_plan": "/api/v1/integrations/itsm/servicenow/ci-sync-plan",
                    "jira_validate": "/api/v1/integrations/itsm/jira/validate",
                    "jira_asset_sync_plan": "/api/v1/integrations/itsm/jira/asset-sync-plan",
                    "glpi_validate": "/api/v1/integrations/itsm/glpi/validate",
                    "glpi_asset_sync_plan": "/api/v1/integrations/itsm/glpi/asset-sync-plan",
                    "freshservice_validate": "/api/v1/integrations/itsm/freshservice/validate",
                    "freshservice_asset_sync_plan": (
                        "/api/v1/integrations/itsm/freshservice/asset-sync-plan"
                    ),
                    "openservice_validate": "/api/v1/integrations/itsm/openservice/validate",
                    "openservice_cmdb_sync_plan": (
                        "/api/v1/integrations/itsm/openservice/cmdb-sync-plan"
                    ),
                },
                "itam": {
                    "organizations": "/api/v1/itam/organizations",
                    "organization": "/api/v1/itam/organization",
                    "organization_create": "/api/v1/itam/organization/create",
                    "organization_update": "/api/v1/itam/organization/update",
                    "organization_delete": "/api/v1/itam/organization/delete",
                    "tenants": "/api/v1/itam/tenants",
                    "tenant": "/api/v1/itam/tenant",
                    "tenant_create": "/api/v1/itam/tenant/create",
                    "tenant_update": "/api/v1/itam/tenant/update",
                    "tenant_delete": "/api/v1/itam/tenant/delete",
                    "support_profile": "/api/v1/itam/support-profile",
                    "support_coverage": "/api/v1/itam/support-coverage",
                    "manufacturer_support": "/api/v1/itam/support-profile/manufacturer",
                    "third_party_support": "/api/v1/itam/support-profile/third-party",
                    "software_license": "/api/v1/itam/software-license",
                    "software_license_assignment": "/api/v1/itam/software-license/assignment",
                    "software_license_compliance": "/api/v1/itam/software-license/compliance",
                },
                "greenops": {
                    "measurement_sources": "/api/v1/greenops/measurement-sources",
                    "measurement_source_create": "/api/v1/greenops/measurement-sources/create",
                    "policy_get": "/api/v1/greenops/policies/get",
                    "policy_upsert": "/api/v1/greenops/policies/upsert",
                    "carbon_factors": "/api/v1/greenops/carbon-factors",
                    "carbon_factor_create": "/api/v1/greenops/carbon-factors/create",
                    "energy_measurements": "/api/v1/greenops/energy-measurements",
                    "energy_measurement_ingest": "/api/v1/greenops/energy-measurements/ingest",
                    "reports": "/api/v1/greenops/reports",
                    "report_get": "/api/v1/greenops/reports/get",
                    "report_generate": "/api/v1/greenops/reports/generate",
                    "report_export": "/api/v1/greenops/reports/export",
                    "anomalies": "/api/v1/greenops/anomalies",
                    "capacity_forecasts": "/api/v1/greenops/capacity-forecasts",
                    "consolidation_candidates": "/api/v1/greenops/consolidation-candidates",
                    "green_scores": "/api/v1/greenops/green-scores",
                },
                "finops": {
                    "allocation_rules": "/api/v1/finops/allocation-rules",
                    "allocation_rule_create": "/api/v1/finops/allocation-rules/create",
                    "import_jobs": "/api/v1/finops/import-jobs",
                    "import_job_get": "/api/v1/finops/import-jobs/get",
                    "import_job_submit": "/api/v1/finops/import-jobs/submit",
                    "import_job_run": "/api/v1/finops/import-jobs/run",
                    "import_job_cancel": "/api/v1/finops/import-jobs/cancel",
                    "cost_records": "/api/v1/finops/cost-records",
                    "budgets": "/api/v1/finops/budgets",
                    "budget_upsert": "/api/v1/finops/budgets/upsert",
                    "periods": "/api/v1/finops/periods",
                    "period_close": "/api/v1/finops/periods/close",
                    "reports": "/api/v1/finops/reports",
                    "report_get": "/api/v1/finops/reports/get",
                    "report_generate": "/api/v1/finops/reports/generate",
                    "report_export": "/api/v1/finops/reports/export",
                    "anomalies": "/api/v1/finops/anomalies",
                    "forecasts": "/api/v1/finops/forecasts",
                },
                "simulation": {
                    "scenarios": "/api/v1/simulation-scenarios",
                    "scenario_get": "/api/v1/simulation-scenarios/get",
                    "scenario_create": "/api/v1/simulation-scenarios/create",
                    "scenario_run": "/api/v1/simulation-scenarios/run",
                    "scenario_cancel": "/api/v1/simulation-scenarios/cancel",
                    "impact_reports": "/api/v1/impact-reports",
                    "impact_report_get": "/api/v1/impact-reports/get",
                    "comparisons": "/api/v1/scenario-comparisons",
                    "comparison_create": "/api/v1/scenario-comparisons/create",
                },
                "field_operations": {
                    "sheets": "/api/v1/field-operation-sheets",
                    "sheet_get": "/api/v1/field-operation-sheets/get",
                    "sheet_generate": "/api/v1/field-operation-sheets/generate",
                    "sheet_start": "/api/v1/field-operation-sheets/start",
                    "sheet_checklist": "/api/v1/field-operation-sheets/checklist",
                    "sheet_complete": "/api/v1/field-operation-sheets/complete",
                    "sheet_cancel": "/api/v1/field-operation-sheets/cancel",
                    "qr_verify": "/api/v1/qr-codes/verify",
                    "evidence": "/api/v1/field-evidence",
                    "evidence_attach": "/api/v1/field-evidence/attach",
                    "evidence_validate": "/api/v1/field-evidence/validate",
                    "lock_acquire": "/api/v1/intervention-locks/acquire",
                    "lock_release": "/api/v1/intervention-locks/release",
                    "offline_packages": "/api/v1/offline-sync-packages",
                    "offline_package_get": "/api/v1/offline-sync-packages/get",
                    "offline_package_create": "/api/v1/offline-sync-packages/create",
                    "offline_package_sync": "/api/v1/offline-sync-packages/synchronize",
                },
                "graph": {
                    "traverse": "/api/v1/graph/traverse",
                    "impact": "/api/v1/graph/impact",
                    "path": "/api/v1/graph/path",
                    "spof": "/api/v1/graph/spof",
                    "export": "/api/v1/graph/export",
                },
                "network_config": {
                    "baselines": "/api/v1/network-config/baselines",
                    "baseline_upsert": "/api/v1/network-config/baselines/upsert",
                    "baseline_retire": "/api/v1/network-config/baselines/retire",
                    "observations": "/api/v1/network-config/observations",
                    "observation_submit": "/api/v1/network-config/observations/submit",
                    "assessment": "/api/v1/network-config/assessment",
                },
                "certificates": {
                    "list": "/api/v1/certificates",
                    "get": "/api/v1/certificates/get",
                    "import": "/api/v1/certificates/import",
                    "retire": "/api/v1/certificates/retire",
                    "endpoints": "/api/v1/certificates/endpoints",
                    "endpoint_observe": "/api/v1/certificates/endpoints/observe",
                    "assessment": "/api/v1/certificates/assessment",
                },
                "flows": {
                    "declarations": "/api/v1/flows/declarations",
                    "declaration_upsert": "/api/v1/flows/declarations/upsert",
                    "declaration_retire": "/api/v1/flows/declarations/retire",
                    "observations": "/api/v1/flows/observations",
                    "observation_submit": "/api/v1/flows/observations/submit",
                    "matrix": "/api/v1/flows/matrix",
                },
                "rsot": {
                    "objects": "/api/v1/rsot/objects",
                    "resource_taxonomy": "/api/v1/rsot/resource-taxonomy",
                    "object_versions": "/api/v1/rsot/object-versions",
                    "object_as_of": "/api/v1/rsot/object-as-of",
                    "object_audit": "/api/v1/rsot/object-audit",
                    "reconcile_object": "/api/v1/rsot/reconcile-object",
                    "relations": "/api/v1/rsot/relations",
                    "governance_rules": "/api/v1/rsot/governance-rules",
                    "quality_object": "/api/v1/rsot/quality/object",
                    "quality_summary": "/api/v1/rsot/quality/summary",
                    "deprecated_itrm_alias": "/api/v1/itrm/objects",
                    "deprecated_sot_alias": "/api/v1/sot/objects",
                    "deprecated_ri_alias": "/api/v1/ri/objects",
                },
                "ipam": {
                    "ui_dashboard": "/api/v1/ipam/ui-dashboard",
                    "ui_search": "/api/v1/ipam/ui-search",
                    "vrfs": "/api/v1/ipam/vrfs",
                    "aggregates": "/api/v1/ipam/aggregates",
                    "prefixes": "/api/v1/ipam/prefixes",
                    "ranges": "/api/v1/ipam/ranges",
                    "addresses": "/api/v1/ipam/addresses",
                    "allocate": "/api/v1/ipam/allocate",
                    "reservation_wizard": "/api/v1/ipam/reservation-wizard",
                    "capacity": "/api/v1/ipam/capacity",
                    "network_bindings": "/api/v1/ipam/network-bindings",
                    "topology": "/api/v1/ipam/topology",
                    "vlan_groups": "/api/v1/ipam/vlan-groups",
                    "vxlan_vnis": "/api/v1/ipam/vxlan-vnis",
                    "vlans": "/api/v1/ipam/vlans",
                    "asns": "/api/v1/ipam/asns",
                    "bgp_peers": "/api/v1/ipam/bgp-peers",
                    "dns_observations": "/api/v1/ipam/dns-observations",
                    "dhcp_leases": "/api/v1/ipam/dhcp-leases",
                    "conflicts": "/api/v1/ipam/conflicts",
                    "ddi_preview": "/api/v1/ipam/ddi-preview",
                },
                "dcim": {
                    "sites": "/api/v1/dcim/sites",
                    "site": "/api/v1/dcim/site",
                    "site_create": "/api/v1/dcim/site/create",
                    "site_update": "/api/v1/dcim/site/update",
                    "site_delete": "/api/v1/dcim/site/delete",
                    "buildings": "/api/v1/dcim/buildings",
                    "building": "/api/v1/dcim/building",
                    "building_create": "/api/v1/dcim/building/create",
                    "building_update": "/api/v1/dcim/building/update",
                    "building_delete": "/api/v1/dcim/building/delete",
                    "floors": "/api/v1/dcim/floors",
                    "floor": "/api/v1/dcim/floor",
                    "rooms_list": "/api/v1/dcim/rooms",
                    "room": "/api/v1/dcim/room",
                    "room_create": "/api/v1/dcim/room/create",
                    "room_update": "/api/v1/dcim/room/update",
                    "room_delete": "/api/v1/dcim/room/delete",
                    "zones": "/api/v1/dcim/zones",
                    "zone": "/api/v1/dcim/zone",
                    "zone_create": "/api/v1/dcim/zone/create",
                    "zone_update": "/api/v1/dcim/zone/update",
                    "zone_delete": "/api/v1/dcim/zone/delete",
                    "topology_catalog": "/api/v1/dcim/topology-catalog",
                    "rooms": "/api/v1/dcim/rooms",
                    "racks": "/api/v1/dcim/racks",
                    "rack": "/api/v1/dcim/rack",
                    "rack_update": "/api/v1/dcim/rack/update",
                    "rack_delete": "/api/v1/dcim/rack/delete",
                    "locations": "/api/v1/dcim/locations",
                    "rack_capacity": "/api/v1/dcim/rack-capacity",
                    "room_plan": "/api/v1/dcim/room-plan",
                    "rack_elevation": "/api/v1/dcim/rack-elevation",
                    "digital_twin": "/api/v1/dcim/digital-twin",
                    "locator_sheet": "/api/v1/dcim/locator-sheet",
                    "verify_scan": "/api/v1/dcim/verify-scan",
                    "patch_panels": "/api/v1/dcim/patch-panels",
                    "ports": "/api/v1/dcim/ports",
                    "cables": "/api/v1/dcim/cables",
                    "cable_trace": "/api/v1/dcim/cable-trace",
                    "power_devices": "/api/v1/dcim/power-devices",
                    "power_circuits": "/api/v1/dcim/power-circuits",
                    "cooling_zones": "/api/v1/dcim/cooling-zones",
                    "power_reservations": "/api/v1/dcim/power-reservations",
                    "energy_cooling_capacity": "/api/v1/dcim/energy-cooling-capacity",
                },
                "discovery": {
                    "collectors": "/api/v1/discovery/collectors",
                    "evidence": "/api/v1/discovery/evidence",
                    "evidence_list": "/api/v1/discovery/evidence-list",
                    "reconciliation": "/api/v1/discovery/reconciliation",
                    "reconciliation_list": "/api/v1/discovery/reconciliation-list",
                    "reconciliation_resolve": "/api/v1/discovery/reconciliation/resolve",
                    "local_plan": "/api/v1/discovery/local-plan",
                    "protocol_profiles": "/api/v1/discovery/protocol-profiles",
                    "integration_profiles": "/api/v1/discovery/integration-profiles",
                    "protocol_profile": "/api/v1/discovery/protocol-profile",
                    "protocol_profile_create": "/api/v1/discovery/protocol-profile/create",
                    "protocol_profile_update": "/api/v1/discovery/protocol-profile/update",
                    "protocol_profile_delete": "/api/v1/discovery/protocol-profile/delete",
                    "integration_profile": "/api/v1/discovery/integration-profile",
                    "integration_profile_create": "/api/v1/discovery/integration-profile/create",
                    "integration_profile_update": "/api/v1/discovery/integration-profile/update",
                    "integration_profile_delete": "/api/v1/discovery/integration-profile/delete",
                    "agent_bootstrap_plan": "/api/v1/discovery/agent-bootstrap-plan",
                    "proxy_enrollments": "/api/v1/discovery/proxy-enrollments",
                    "heartbeat": "/api/v1/discovery/collectors/heartbeat",
                    "job": "/api/v1/discovery/job",
                    "jobs": "/api/v1/discovery/jobs",
                    "job_claim": "/api/v1/discovery/jobs/claim",
                    "job_renew": "/api/v1/discovery/jobs/renew",
                    "job_complete": "/api/v1/discovery/jobs/complete",
                    "job_fail": "/api/v1/discovery/jobs/fail",
                    "job_replay": "/api/v1/discovery/jobs/replay",
                    "authorize_job": "/api/v1/discovery/jobs/authorize",
                },
            },
        }


class OpenInfraApiEntrypoint:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-api")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8080)
        parser.add_argument("--backend", choices=("json", "postgresql"), default="json")
        parser.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        parser.add_argument("--postgres-dsn")
        parser.add_argument("--edition", default=os.environ.get("OPENINFRA_EDITION", "enterprise"))
        parser.add_argument("--auth-required", action="store_true")
        args = parser.parse_args(sys.argv[1:])
        app = cls()._create_application(args)
        auth_required = args.auth_required or os.environ.get("OPENINFRA_AUTH_REQUIRED") == "true"
        server = OpenInfraThreadingServer((args.host, args.port), app, auth_required=auth_required)
        cls._write_startup_log(args, auth_required)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return 0

    @staticmethod
    def _write_startup_log(args: argparse.Namespace, auth_required: bool) -> None:
        sys.stdout.write(
            json.dumps(
                {
                    "event": "openinfra_api_started",
                    "service": "openinfra-api",
                    "version": __version__,
                    "host": str(args.host),
                    "port": int(args.port),
                    "backend": str(args.backend),
                    "edition": str(args.edition),
                    "auth_required": auth_required,
                    "root_url": "/",
                    "health_url": "/health",
                    "readiness_url": "/ready",
                    "version_url": "/api/v1/version",
                    "swagger_url": "/docs",
                    "redoc_url": "/redoc",
                    "openapi_url": "/openapi.yaml",
                },
                sort_keys=True,
            )
            + "\n"
        )
        sys.stdout.flush()

    def _create_application(self, args: argparse.Namespace) -> OpenInfraApplication:
        edition = getattr(args, "edition", os.environ.get("OPENINFRA_EDITION", "enterprise"))
        if args.backend == "json":
            return ApplicationFactory().create_json_application(args.data, edition=edition)
        dsn = RuntimeDatabaseDsnResolver().resolve(args.postgres_dsn)
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn, OPENINFRA_DATABASE_DSN or /opt/openinfra/config/"
                "openinfra.conf is required for postgresql backend"
            )
        if edition == "enterprise":
            return ApplicationFactory().create_postgresql_application(dsn, seed=False)
        return ApplicationFactory().create_postgresql_application(dsn, seed=False, edition=edition)


if __name__ == "__main__":
    raise SystemExit(OpenInfraApiEntrypoint.main())
