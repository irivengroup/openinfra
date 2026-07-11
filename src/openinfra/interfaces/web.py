from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, request
from urllib.parse import urljoin, urlparse

from openinfra import __version__
from openinfra.domain.common import OpenInfraError


@dataclass(frozen=True, slots=True)
class OpenInfraWebConfig:
    host: str
    port: int
    backend_url: str
    public_api_base_url: str
    public_api_docs_base_url: str
    static_root: Path
    edition: str
    auth_mode: str
    allow_insecure_backend: bool
    request_timeout_seconds: float = 5.0
    max_request_body_bytes: int = 1_048_576
    database_dsn_ref: str = ""
    database_user_ref: str = ""
    database_password_ref: str = ""
    backend_bearer_token: str = ""

    def normalized_backend_url(self) -> str:
        return self.backend_url.rstrip("/") + "/"

    def has_database_trust(self) -> bool:
        return bool(self.database_dsn_ref or self.database_user_ref or self.database_password_ref)

    def as_public_dict(self) -> dict[str, object]:
        return {
            "service": "openinfra-web",
            "version": __version__,
            "edition": self.edition,
            "authMode": self.auth_mode,
            "apiBaseUrl": self.public_api_base_url,
            "apiDocumentation": self.api_documentation_links(),
            "backendProxy": "/api",
            "webBackendTrust": "server-side",
            "databaseTrust": "server-side" if self.has_database_trust() else "not-configured",
        }

    def api_documentation_links(self) -> dict[str, str]:
        root = self._public_api_documentation_root()
        return {
            "swaggerUrl": root + "/docs",
            "swaggerAliasUrl": root + "/swagger",
            "redocUrl": root + "/redoc",
            "openapiUrl": root + "/openapi.yaml",
            "versionedOpenapiUrl": self._public_api_base_root() + "/v1/openapi.yaml",
        }

    def _public_api_documentation_root(self) -> str:
        explicit = self.public_api_docs_base_url.strip().rstrip("/")
        if explicit:
            return explicit
        parsed = urlparse(self.public_api_base_url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return ""

    def _public_api_base_root(self) -> str:
        value = self.public_api_base_url.strip().rstrip("/")
        return value or "/api"

    def as_status_dict(self) -> dict[str, object]:
        backend_bearer_configured = bool(self.backend_bearer_token)
        protected_forms = (
            "enabled" if backend_bearer_configured else "blocked-by-missing-server-bearer"
        )
        status: dict[str, object] = {
            "service": "openinfra-web",
            "version": __version__,
            "ready": True,
            "backendProxy": "/api",
            "backendOrigin": "configured",
            "protectedForms": protected_forms,
            "trust": {
                "webBackend": "server-side",
                "database": "server-side" if self.has_database_trust() else "not-configured",
                "backendBearer": "configured" if backend_bearer_configured else "not-configured",
            },
        }
        if not backend_bearer_configured:
            status["remediation"] = {
                "environment": [
                    "OPENINFRA_WEB_BACKEND_BEARER_TOKEN",
                    "OPENINFRA_BOOTSTRAP_TOKEN",
                ],
                "message": "configure a server-side backend bearer token for protected forms",
            }
        return status


class OpenInfraWebConfigFactory:
    def from_args(self, argv: list[str] | None = None) -> OpenInfraWebConfig:
        parser = argparse.ArgumentParser(
            prog="openinfra-web",
            description="OpenInfra web dashboard serving rendering assets and backend API proxy",
        )
        parser.add_argument("--host", default=os.environ.get("OPENINFRA_WEB_HOST", "127.0.0.1"))
        parser.add_argument(
            "--port", type=int, default=int(os.environ.get("OPENINFRA_WEB_PORT", "2006"))
        )
        parser.add_argument(
            "--backend-url",
            default=os.environ.get(
                "OPENINFRA_WEB_BACKEND_URL",
                os.environ.get("OPENINFRA_API_BASE_URL", "http://127.0.0.1:8080"),
            ),
        )
        parser.add_argument(
            "--public-api-base-url",
            default=os.environ.get("OPENINFRA_WEB_PUBLIC_API_BASE_URL", "/api"),
        )
        parser.add_argument(
            "--public-api-docs-base-url",
            default=os.environ.get("OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL", ""),
            help=(
                "Optional public backend API documentation origin. When omitted, "
                "openinfra-web publishes same-origin proxied /docs and /redoc links."
            ),
        )
        parser.add_argument(
            "--static-root",
            default=os.environ.get("OPENINFRA_WEB_STATIC_ROOT", ""),
        )
        parser.add_argument("--edition", default=os.environ.get("OPENINFRA_EDITION", "lite"))
        parser.add_argument(
            "--auth-mode", default=os.environ.get("OPENINFRA_WEB_AUTH_MODE", "standard")
        )
        parser.add_argument(
            "--allow-insecure-backend",
            action="store_true",
            default=os.environ.get("OPENINFRA_WEB_ALLOW_INSECURE_BACKEND", "false").lower()
            == "true",
        )
        parser.add_argument(
            "--backend-bearer-token",
            default=self._first_non_blank_env(
                "OPENINFRA_WEB_BACKEND_BEARER_TOKEN",
                "OPENINFRA_BOOTSTRAP_TOKEN",
            ),
            help="Optional server-side bearer token used by openinfra-web when proxying API forms.",
        )
        parser.add_argument(
            "--database-dsn-ref",
            default=os.environ.get("OPENINFRA_WEB_DATABASE_DSN_REF", ""),
        )
        parser.add_argument(
            "--database-user-ref",
            default=os.environ.get("OPENINFRA_WEB_DATABASE_USER_REF", ""),
        )
        parser.add_argument(
            "--database-password-ref",
            default=os.environ.get("OPENINFRA_WEB_DATABASE_PASSWORD_REF", ""),
        )
        namespace = parser.parse_args(argv)
        static_root = OpenInfraWebStaticLocator().resolve(namespace.static_root or None)
        config = OpenInfraWebConfig(
            host=str(namespace.host),
            port=int(namespace.port),
            backend_url=str(namespace.backend_url),
            public_api_base_url=str(namespace.public_api_base_url),
            public_api_docs_base_url=str(namespace.public_api_docs_base_url),
            static_root=static_root,
            edition=str(namespace.edition).strip().lower(),
            auth_mode=str(namespace.auth_mode).strip().lower(),
            allow_insecure_backend=bool(namespace.allow_insecure_backend),
            database_dsn_ref=str(namespace.database_dsn_ref).strip(),
            database_user_ref=str(namespace.database_user_ref).strip(),
            database_password_ref=str(namespace.database_password_ref).strip(),
            backend_bearer_token=str(namespace.backend_bearer_token).strip(),
        )
        OpenInfraWebConfigValidator().validate(config)
        return config

    def _first_non_blank_env(self, *names: str) -> str:
        for name in names:
            value = os.environ.get(name, "").strip()
            if value:
                return value
        return ""


class OpenInfraWebStaticLocator:
    def resolve(self, explicit_root: str | None = None) -> Path:
        candidates: list[Path] = []
        if explicit_root:
            candidates.append(Path(explicit_root))
        candidates.extend(
            (
                Path.cwd() / "src/openinfra/interfaces/rendering/static",
                Path(__file__).resolve().parent / "rendering/static",
                Path.cwd() / "web/dist",
                Path(__file__).resolve().parents[3] / "web/dist",
            )
        )
        for candidate in candidates:
            if (candidate / "index.html").is_file():
                return candidate.resolve()
        raise OpenInfraError("OpenInfra web static assets are unavailable")


class OpenInfraWebConfigValidator:
    _allowed_auth_modes = frozenset({"standard", "ldap", "ipa"})
    _allowed_editions = frozenset({"lite", "pro", "enterprise"})
    _allowed_secret_ref_prefixes = ("env:", "vault://", "sops://", "file://", "kms://")

    def validate(self, config: OpenInfraWebConfig) -> None:
        parsed = urlparse(config.normalized_backend_url())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise OpenInfraError("OPENINFRA_WEB_BACKEND_URL must be an http or https origin URL")
        if parsed.username or parsed.password:
            raise OpenInfraError("OPENINFRA_WEB_BACKEND_URL must not embed credentials")
        if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
            raise OpenInfraError("OPENINFRA_WEB_BACKEND_URL must be an origin URL without path")
        if config.edition not in self._allowed_editions:
            raise OpenInfraError("OPENINFRA_EDITION must be lite, pro or enterprise")
        if config.auth_mode not in self._allowed_auth_modes:
            raise OpenInfraError("OPENINFRA_WEB_AUTH_MODE must be standard, ldap or ipa")
        if config.edition == "lite" and config.auth_mode != "standard":
            raise OpenInfraError("Lite web authentication must remain standard")
        if (
            config.edition != "lite"
            and parsed.scheme != "https"
            and not config.allow_insecure_backend
        ):
            raise OpenInfraError(
                "Pro and Enterprise web-backend traffic requires HTTPS or explicit lab override"
            )
        if config.max_request_body_bytes <= 0:
            raise OpenInfraError("max request body size must be positive")
        self._validate_public_api_docs_base_url(config.public_api_docs_base_url)
        for key, value in (
            ("OPENINFRA_WEB_DATABASE_DSN_REF", config.database_dsn_ref),
            ("OPENINFRA_WEB_DATABASE_USER_REF", config.database_user_ref),
            ("OPENINFRA_WEB_DATABASE_PASSWORD_REF", config.database_password_ref),
        ):
            self._validate_secret_reference(key, value)

    def _validate_public_api_docs_base_url(self, value: str) -> None:
        if not value.strip():
            return
        parsed = urlparse(value.strip().rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise OpenInfraError(
                "OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL must be an http or https origin URL"
            )
        if parsed.username or parsed.password:
            raise OpenInfraError(
                "OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL must not embed credentials"
            )
        if parsed.params or parsed.query or parsed.fragment:
            raise OpenInfraError(
                "OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL must not contain params, query or fragment"
            )

    def _validate_secret_reference(self, key: str, value: str) -> None:
        if not value:
            return
        if not value.startswith(self._allowed_secret_ref_prefixes):
            raise OpenInfraError(key + " must be a secret reference, not a cleartext value")


class OpenInfraWebJsonResponder:
    def __init__(self, handler: BaseHTTPRequestHandler) -> None:
        self._handler = handler

    def send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self._handler.send_response(status.value)
        self._handler.send_header("Content-Type", "application/json; charset=utf-8")
        self._handler.send_header("Content-Length", str(len(body)))
        OpenInfraWebSecurityHeaders().write(self._handler)
        self._handler.end_headers()
        self._handler.wfile.write(body)


class OpenInfraWebSecurityHeaders:
    def write(self, handler: BaseHTTPRequestHandler, *, api_docs: bool = False) -> None:
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("Referrer-Policy", "no-referrer")
        handler.send_header("X-Frame-Options", "DENY")
        handler.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        handler.send_header("Cache-Control", "no-store")
        if api_docs:
            handler.send_header(
                "Content-Security-Policy",
                "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline' https://unpkg.com; "
                "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.redoc.ly",
            )
            return
        handler.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
        )


class OpenInfraBackendProxy:
    _forwarded_request_headers = frozenset(
        {
            "accept",
            "content-type",
            "x-request-id",
            "x-openinfra-tenant",
        }
    )
    _response_headers = frozenset({"content-type", "content-disposition"})

    def __init__(self, config: OpenInfraWebConfig) -> None:
        self._config = config

    def proxy(self, handler: BaseHTTPRequestHandler, route: str) -> None:
        body = self._request_body(handler)
        if self._requires_server_side_bearer(handler.command, route):
            OpenInfraWebJsonResponder(handler).send(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "web backend bearer token is not configured",
                    "hint": (
                        "set OPENINFRA_WEB_BACKEND_BEARER_TOKEN or "
                        "OPENINFRA_BOOTSTRAP_TOKEN for openinfra-web"
                    ),
                },
            )
            return
        target_url = self._target_url(handler, route)
        headers = self._request_headers(handler)
        upstream_request = request.Request(  # noqa: S310
            target_url,
            data=body,
            headers=headers,
            method=handler.command,
        )
        try:
            with request.urlopen(  # noqa: S310  # nosec B310
                upstream_request, timeout=self._config.request_timeout_seconds
            ) as response:
                self._send_proxy_response(
                    handler, response.status, response.headers, response.read(), route=route
                )
        except error.HTTPError as exc:
            self._send_upstream_error(handler, exc)
        except error.URLError as exc:
            OpenInfraWebJsonResponder(handler).send(
                HTTPStatus.BAD_GATEWAY, {"error": "backend unavailable", "reason": str(exc.reason)}
            )

    def _requires_server_side_bearer(self, method: str, route: str) -> bool:
        if self._config.backend_bearer_token:
            return False
        if route in {
            "/docs",
            "/swagger",
            "/redoc",
            "/openapi.yaml",
            "/api/v1/openapi.yaml",
            "/api/v1/version",
        }:
            return False
        return route.startswith("/api/v1/") and method.upper() in {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }

    def _target_url(self, handler: BaseHTTPRequestHandler, route: str) -> str:
        # Keep the public /api/v1 prefix when proxying: the backend API contract is
        # versioned as /api/v1/*. Previous stripping to /v1/* made dashboard forms
        # reach non-existing backend routes in the real runtime.
        upstream_path = route or "/"
        query = ""
        if "?" in handler.path:
            query = "?" + handler.path.split("?", 1)[1]
        return urljoin(self._config.normalized_backend_url(), upstream_path.lstrip("/")) + query

    def _request_headers(self, handler: BaseHTTPRequestHandler) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in handler.headers.items():
            if key.lower() in self._forwarded_request_headers:
                headers[key] = value
        headers["X-Forwarded-Proto"] = (
            "https" if self._config.backend_url.startswith("https:") else "http"
        )
        headers["X-OpenInfra-Web"] = "openinfra-web"
        headers["X-OpenInfra-Web-Trust"] = "server-side"
        headers["X-OpenInfra-Web-Version"] = __version__
        if self._config.has_database_trust():
            headers["X-OpenInfra-Web-Database-Trust"] = "configured"
        if self._config.backend_bearer_token:
            headers["Authorization"] = "Bearer " + self._config.backend_bearer_token
        return headers

    def _request_body(self, handler: BaseHTTPRequestHandler) -> bytes | None:
        raw_length = handler.headers.get("Content-Length")
        if not raw_length:
            return None
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise OpenInfraError("invalid Content-Length") from exc
        if length > self._config.max_request_body_bytes:
            raise OpenInfraError("request body exceeds OpenInfra web proxy limit")
        return handler.rfile.read(length)

    def _send_upstream_error(self, handler: BaseHTTPRequestHandler, exc: error.HTTPError) -> None:
        body = exc.read()
        if self._is_raw_missing_bearer_error(body):
            OpenInfraWebJsonResponder(handler).send(
                HTTPStatus.BAD_GATEWAY,
                {
                    "error": "backend authentication failed through openinfra-web",
                    "reason": "server-side backend bearer token was not accepted by the API",
                },
            )
            return
        route = handler.path.split("?", 1)[0]
        self._send_proxy_response(handler, exc.code, exc.headers, body, route=route)

    def _is_raw_missing_bearer_error(self, body: bytes) -> bool:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        message = str(payload.get("error", "")).strip().lower()
        return message == "missing bearer token"

    def _send_proxy_response(
        self,
        handler: BaseHTTPRequestHandler,
        status_code: int,
        headers: Any,
        body: bytes,
        *,
        route: str = "",
    ) -> None:
        handler.send_response(status_code)
        for key, value in headers.items():
            if key.lower() in self._response_headers:
                handler.send_header(key, value)
        handler.send_header("Content-Length", str(len(body)))
        OpenInfraWebSecurityHeaders().write(
            handler, api_docs=route in {"/docs", "/swagger", "/redoc"}
        )
        handler.end_headers()
        handler.wfile.write(body)


class OpenInfraWebRequestHandler(BaseHTTPRequestHandler):
    server: OpenInfraWebServer

    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        self._handle_without_body()

    def do_HEAD(self) -> None:
        self._handle_without_body(head_only=True)

    def do_POST(self) -> None:
        self._handle_proxy_request()

    def do_PUT(self) -> None:
        self._handle_proxy_request()

    def do_PATCH(self) -> None:
        self._handle_proxy_request()

    def do_DELETE(self) -> None:
        self._handle_proxy_request()

    def _handle_without_body(self, head_only: bool = False) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "service": "openinfra-web"})
            return
        if route == "/version":
            self._json(HTTPStatus.OK, {"service": "openinfra-web", "version": __version__})
            return
        if route == "/ready":
            self._proxy_readiness()
            return
        if route == "/config.json":
            self._json(HTTPStatus.OK, self.server.config.as_public_dict())
            return
        if route == "/status":
            self._json(HTTPStatus.OK, self.server.config.as_status_dict())
            return
        if route in {"/docs", "/swagger", "/redoc", "/openapi.yaml"} or route.startswith("/api/"):
            self._handle_proxy_request()
            return
        self._serve_static(route, head_only=head_only)

    def _handle_proxy_request(self) -> None:
        route = self.path.split("?", 1)[0]
        if route not in {"/docs", "/swagger", "/redoc", "/openapi.yaml"} and not route.startswith(
            "/api/"
        ):
            self._json(HTTPStatus.NOT_FOUND, {"error": "route not served by openinfra-web"})
            return
        try:
            self.server.backend_proxy.proxy(self, route)
        except OpenInfraError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _proxy_readiness(self) -> None:
        synthetic = request.Request(  # noqa: S310
            urljoin(self.server.config.normalized_backend_url(), "ready"),
            method="GET",
            headers={
                "Accept": "application/json",
                "X-OpenInfra-Web": "openinfra-web",
                "X-OpenInfra-Web-Trust": "server-side",
                "X-OpenInfra-Web-Version": __version__,
            },
        )
        try:
            with request.urlopen(  # noqa: S310  # nosec B310
                synthetic, timeout=self.server.config.request_timeout_seconds
            ) as response:
                body = response.read()
                self.send_response(response.status)
                self.send_header(
                    "Content-Type", response.headers.get("Content-Type", "application/json")
                )
                self.send_header("Content-Length", str(len(body)))
                OpenInfraWebSecurityHeaders().write(self)
                self.end_headers()
                self.wfile.write(body)
        except error.URLError as exc:
            self._json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"ready": False, "service": "openinfra-web", "reason": str(exc.reason)},
            )

    def _serve_static(self, route: str, head_only: bool) -> None:
        relative = "index.html" if route in {"", "/"} else route.lstrip("/")
        candidate = (self.server.config.static_root / relative).resolve()
        if not self._is_safe_static_path(candidate):
            self._json(HTTPStatus.NOT_FOUND, {"error": "asset not found"})
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        body = b"" if head_only else candidate.read_bytes()
        length = candidate.stat().st_size
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-cache, max-age=0, must-revalidate")

        OpenInfraWebSecurityHeaders().write(self)
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _is_safe_static_path(self, candidate: Path) -> bool:
        try:
            candidate.relative_to(self.server.config.static_root)
        except ValueError:
            return False
        return candidate.is_file()

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        OpenInfraWebJsonResponder(self).send(status, payload)


class OpenInfraWebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], config: OpenInfraWebConfig) -> None:
        super().__init__(server_address, OpenInfraWebRequestHandler)
        self.config = config
        self.backend_proxy = OpenInfraBackendProxy(config)


class OpenInfraWebEntrypoint:
    @classmethod
    def main(cls) -> int:
        try:
            config = OpenInfraWebConfigFactory().from_args(sys.argv[1:])
            server = OpenInfraWebServer((config.host, config.port), config)
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        except OpenInfraError as exc:
            sys.stderr.write(f"openinfra-web: error: {exc}\n")
            return 2
        return 0


if __name__ == "__main__":
    raise SystemExit(OpenInfraWebEntrypoint.main())
