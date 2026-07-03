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
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    ListTokensCommand,
    RevokeTokenCommand,
    RotateTokenCommand,
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


class OpenInfraRequestHandler(BaseHTTPRequestHandler):
    server: OpenInfraThreadingServer

    def log_message(self, _format: str, *args: object) -> None:
        return None

    def do_GET(self) -> None:
        responder = JsonHttpResponder(self)
        parsed = urlparse(self.path)
        route = parsed.path
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
                            self._first_query_value(query, "include_inactive", "false")
                            == "true"
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
                            self._first_query_value(query, "include_inactive", "false")
                            == "true"
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
        responder.send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        responder = JsonHttpResponder(self)
        route = urlparse(self.path).path
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
                            str(payload["admin_token"])
                            if payload.get("admin_token")
                            else None
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
                            int(payload["ttl_seconds"])
                            if payload.get("ttl_seconds")
                            else None
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
    ) -> None:
        super().__init__(server_address, OpenInfraRequestHandler)
        self.application = application
        self.auth_required = auth_required


class OpenInfraApiEntrypoint:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-api")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8080)
        parser.add_argument("--backend", choices=("json", "postgresql"), default="json")
        parser.add_argument("--data", type=Path, default=Path(".openinfra.json"))
        parser.add_argument("--postgres-dsn")
        parser.add_argument("--auth-required", action="store_true")
        args = parser.parse_args(sys.argv[1:])
        app = cls()._create_application(args)
        auth_required = args.auth_required or os.environ.get("OPENINFRA_AUTH_REQUIRED") == "true"
        server = OpenInfraThreadingServer((args.host, args.port), app, auth_required=auth_required)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return 0

    def _create_application(self, args: argparse.Namespace) -> OpenInfraApplication:
        if args.backend == "json":
            return ApplicationFactory().create_json_application(args.data)
        dsn = args.postgres_dsn or os.environ.get("OPENINFRA_DATABASE_DSN", "")
        if not dsn:
            raise OpenInfraError(
                "--postgres-dsn or OPENINFRA_DATABASE_DSN is required for postgresql backend"
            )
        return ApplicationFactory().create_postgresql_application(dsn, seed=False)


if __name__ == "__main__":
    raise SystemExit(OpenInfraApiEntrypoint.main())
