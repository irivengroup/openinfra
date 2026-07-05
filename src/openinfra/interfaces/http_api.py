from __future__ import annotations

import argparse
import json
import os
import sys
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
from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.application.dcim_services import (
    ConnectDcimCableCommand,
    DefineCoolingZoneCommand,
    DefineDcimPortCommand,
    DefinePatchPanelCommand,
    DefinePhysicalRoomCommand,
    DefinePowerCircuitCommand,
    DefinePowerDeviceCommand,
    DefineRackCommand,
    GenerateEquipmentLocatorCommand,
    RackCapacityCommand,
    RackEnergyCoolingCapacityCommand,
    RenderRackElevationCommand,
    RenderRoomPlanCommand,
    ReserveEquipmentPowerCommand,
    TraceDcimCableCommand,
    VerifyEquipmentScanCommand,
)
from openinfra.application.discovery_services import (
    AuthorizeDiscoveryJobCommand,
    DisableCollectorCommand,
    HeartbeatCollectorCommand,
    ListCollectorsCommand,
    RegisterCollectorCommand,
)
from openinfra.application.export_services import (
    GetExportArtifactCommand,
    GetExportJobCommand,
    RequestExportCommand,
    RunExportJobCommand,
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
    ImportDatasetCommand,
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
    IpamUiDashboardCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
    PreviewDdiReservationCommand,
    RegisterIpAddressCommand,
)
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
)
from openinfra.application.source_governance_services import (
    CreateSourceGovernanceRuleCommand,
    DeactivateSourceGovernanceRuleCommand,
    EvaluateSourceGovernanceCommand,
    ListSourceGovernanceRulesCommand,
)
from openinfra.application.source_of_truth_services import (
    CreateSourceRelationCommand,
    GetSourceObjectCommand,
    GetSourceObjectVersionCommand,
    ListSourceObjectsCommand,
    ListSourceRelationsCommand,
    UpsertSourceObjectCommand,
)
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.common import AccessDeniedError, OpenInfraError
from openinfra.domain.security import AuthenticatedPrincipal, Permission


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
        route = parsed.path
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
        if route == "/api/v1/database/schema":
            status = self.server.application.schema_status_provider.status_as_dict()
            http_status = HTTPStatus.OK if status.get("ready") is True else HTTPStatus.CONFLICT
            responder.send(http_status, status)
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

        if route == "/api/v1/sot/governance-rules":
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

        if route == "/api/v1/sot/objects":
            try:
                query = parse_qs(parsed.query)
                key = query.get("key", [None])[0]
                if key:
                    result = self.server.application.source_of_truth_service.get_object(
                        GetSourceObjectCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            key=key,
                        )
                    )
                    responder.send(HTTPStatus.OK, result)
                else:
                    page = self.server.application.source_of_truth_service.list_objects(
                        ListSourceObjectsCommand(
                            tenant_id=self._first_query_value(query, "tenant_id"),
                            admin_token=self._bearer_token(),
                            limit=int(self._first_query_value(query, "limit", "100")),
                            cursor=query.get("cursor", [None])[0],
                            kind=query.get("kind", [None])[0],
                            tag=query.get("tag", [None])[0],
                        )
                    )
                    responder.send(HTTPStatus.OK, page.as_dict())
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (ValueError, OpenInfraError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/sot/object-versions":
            try:
                query = parse_qs(parsed.query)
                result = self.server.application.source_of_truth_service.get_object_version(
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
        if route == "/api/v1/sot/relations":
            try:
                query = parse_qs(parsed.query)
                page = self.server.application.source_of_truth_service.list_relations(
                    ListSourceRelationsCommand(
                        tenant_id=self._first_query_value(query, "tenant_id"),
                        admin_token=self._bearer_token(),
                        limit=int(self._first_query_value(query, "limit", "100")),
                        cursor=query.get("cursor", [None])[0],
                        source_key=query.get("source_key", [None])[0],
                        target_key=query.get("target_key", [None])[0],
                        relation_type=query.get("relation_type", [None])[0],
                    )
                )
                responder.send(HTTPStatus.OK, page.as_dict())
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
        route = urlparse(self.path).path
        result: Any
        rule: Any

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
                        floor_code=str(payload["floor_code"]),
                        floor_name=str(payload["floor_name"]),
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

        if route == "/api/v1/sot/governance-rules":
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
        if route == "/api/v1/sot/governance/evaluate":
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
        if route == "/api/v1/sot/governance/deactivate-rule":
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
        if route == "/api/v1/sot/objects":
            try:
                payload = self._read_json_body()
                tags_payload = payload.get("tags", [])
                if not isinstance(tags_payload, list):
                    raise OpenInfraError("tags must be a list")
                result = self.server.application.source_of_truth_service.upsert_object(
                    UpsertSourceObjectCommand(
                        tenant_id=str(payload["tenant_id"]),
                        actor=str(payload.get("actor", "api")),
                        admin_token=self._bearer_token(),
                        key=str(payload["key"]),
                        kind=str(payload["kind"]),
                        display_name=str(payload["display_name"]),
                        attributes_json=json.dumps(payload.get("attributes", {}), sort_keys=True),
                        tags=tuple(str(tag) for tag in tags_payload),
                        source=str(payload["source"]),
                    )
                )
                responder.send(HTTPStatus.CREATED, result)
            except AccessDeniedError as exc:
                responder.send(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            except (KeyError, json.JSONDecodeError, OpenInfraError, ValueError) as exc:
                responder.send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if route == "/api/v1/sot/relations":
            try:
                payload = self._read_json_body()
                result = self.server.application.source_of_truth_service.create_relation(
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

    def _optional_payload_value(self, payload: dict[str, Any], name: str) -> str | None:
        value = payload.get(name)
        if value is None or str(value).strip() == "":
            return None
        return str(value)

    def _roles_from_payload(self, payload: dict[str, Any]) -> tuple[str, ...]:
        roles_payload = payload.get("roles", [])
        if not isinstance(roles_payload, list):
            raise OpenInfraError("roles must be a list")
        return tuple(str(role) for role in roles_payload)

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
                },
                "discovery": {
                    "collectors": "/api/v1/discovery/collectors",
                    "heartbeat": "/api/v1/discovery/collectors/heartbeat",
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
        dsn = args.postgres_dsn or os.environ.get("OPENINFRA_DATABASE_DSN", "")
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn or OPENINFRA_DATABASE_DSN is required for postgresql backend"
            )
        if edition == "enterprise":
            return ApplicationFactory().create_postgresql_application(dsn, seed=False)
        return ApplicationFactory().create_postgresql_application(dsn, seed=False, edition=edition)


if __name__ == "__main__":
    raise SystemExit(OpenInfraApiEntrypoint.main())
