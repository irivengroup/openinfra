from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable, Mapping, MutableMapping
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from openinfra import __version__
from openinfra.application.ports import RuntimeTelemetry
from openinfra.application.telemetry import NullRuntimeTelemetry
from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.infrastructure.observability import OpenInfraTelemetry
from openinfra.interfaces.asgi_observability import ObservedAsgiReceive, ObservedAsgiSend
from openinfra.interfaces.web import (
    OpenInfraStaticAssetStore,
    OpenInfraWebConfig,
    OpenInfraWebConfigFactory,
)

AsgiMessage = MutableMapping[str, Any]
AsgiReceive = Callable[[], Awaitable[AsgiMessage]]
AsgiSend = Callable[[AsgiMessage], Awaitable[None]]
AsgiScope = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class OpenInfraWebHttpPoolSettings:
    max_connections: int
    max_keepalive_connections: int
    keepalive_expiry_seconds: float
    connect_timeout_seconds: float
    read_timeout_seconds: float
    write_timeout_seconds: float
    pool_timeout_seconds: float

    def __post_init__(self) -> None:
        if self.max_connections <= 0:
            raise ValidationError("web HTTP pool max_connections must be positive")
        if self.max_keepalive_connections <= 0:
            raise ValidationError("web HTTP keepalive capacity must be positive")
        if self.max_keepalive_connections > self.max_connections:
            raise ValidationError("web HTTP keepalive capacity cannot exceed max_connections")
        for value in (
            self.keepalive_expiry_seconds,
            self.connect_timeout_seconds,
            self.read_timeout_seconds,
            self.write_timeout_seconds,
            self.pool_timeout_seconds,
        ):
            if value <= 0:
                raise ValidationError("web HTTP pool timeout values must be positive")

    @classmethod
    def from_environment(cls, edition: str) -> OpenInfraWebHttpPoolSettings:
        normalized = edition.strip().lower()
        defaults = {
            "lite": (32, 8),
            "pro": (200, 50),
            "enterprise": (500, 100),
        }
        if normalized not in defaults:
            raise ValidationError("edition must be lite, pro or enterprise")
        max_connections, keepalive = defaults[normalized]
        return cls(
            max_connections=int(
                os.environ.get("OPENINFRA_WEB_HTTP_MAX_CONNECTIONS", str(max_connections))
            ),
            max_keepalive_connections=int(
                os.environ.get("OPENINFRA_WEB_HTTP_MAX_KEEPALIVE_CONNECTIONS", str(keepalive))
            ),
            keepalive_expiry_seconds=float(
                os.environ.get("OPENINFRA_WEB_HTTP_KEEPALIVE_EXPIRY_SECONDS", "30")
            ),
            connect_timeout_seconds=float(
                os.environ.get("OPENINFRA_WEB_HTTP_CONNECT_TIMEOUT_SECONDS", "2")
            ),
            read_timeout_seconds=float(
                os.environ.get("OPENINFRA_WEB_HTTP_READ_TIMEOUT_SECONDS", "30")
            ),
            write_timeout_seconds=float(
                os.environ.get("OPENINFRA_WEB_HTTP_WRITE_TIMEOUT_SECONDS", "30")
            ),
            pool_timeout_seconds=float(
                os.environ.get("OPENINFRA_WEB_HTTP_POOL_TIMEOUT_SECONDS", "2")
            ),
        )


class OpenInfraWebAsgiApplication:
    _forwarded_request_headers = frozenset(
        {
            "accept",
            "accept-encoding",
            "content-type",
            "x-request-id",
            "x-openinfra-tenant",
            "x-openinfra-consistency-token",
        }
    )
    _forwarded_response_headers = frozenset(
        {
            "content-type",
            "content-disposition",
            "content-encoding",
            "etag",
            "last-modified",
            "x-openinfra-consistency-token",
            "access-control-expose-headers",
        }
    )
    _consistency_cookie_name = "openinfra_read_consistency"

    def __init__(
        self,
        config: OpenInfraWebConfig,
        pool_settings: OpenInfraWebHttpPoolSettings,
        client: httpx.AsyncClient | None = None,
        *,
        consistency_cookie_ttl_seconds: int = 10,
        telemetry: RuntimeTelemetry | None = None,
    ) -> None:
        self._config = config
        self._pool_settings = pool_settings
        self._static_assets = OpenInfraStaticAssetStore()
        if consistency_cookie_ttl_seconds <= 0 or consistency_cookie_ttl_seconds > 300:
            raise ValidationError("web consistency cookie TTL must be between 1 and 300 seconds")
        self._client = client
        self._client_lock = asyncio.Lock()
        self._owns_client = client is None
        self._consistency_cookie_ttl_seconds = consistency_cookie_ttl_seconds
        self._telemetry = telemetry or NullRuntimeTelemetry()

    async def __call__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend) -> None:
        scope_type = str(scope.get("type", ""))
        if scope_type == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope_type != "http":
            await self._json(send, HTTPStatus.BAD_REQUEST, {"error": "unsupported ASGI scope"})
            return
        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", "/"))
        if path == "/metrics" and method in {"GET", "HEAD"}:
            await self._send_metrics(send, head_only=method == "HEAD")
            return
        headers = self._request_header_map(scope)
        observation = self._telemetry.begin_http_request(method=method, route=path, headers=headers)
        observed_receive = ObservedAsgiReceive(receive)
        observed_send = ObservedAsgiSend(send, observation)
        try:
            await self._dispatch_http(
                scope,
                observed_receive,
                observed_send,
                method=method,
                path=path,
                headers=headers,
            )
        except OpenInfraError as exc:
            observed_send.record_exception(exc)
            await self._json(observed_send, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            observed_send.record_exception(exc)
            await self._json(
                observed_send,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal server error", "reason": type(exc).__name__},
            )
        finally:
            observed_send.finish(observed_receive.request_size_bytes)

    async def _dispatch_http(
        self,
        scope: AsgiScope,
        receive: AsgiReceive,
        send: AsgiSend,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
    ) -> None:
        query_string = bytes(scope.get("query_string", b""))
        if method in {"GET", "HEAD"}:
            if path == "/health":
                await self._json(
                    send,
                    HTTPStatus.OK,
                    {"status": "ok", "service": "openinfra-web"},
                    head_only=method == "HEAD",
                )
                return
            if path == "/version":
                await self._json(
                    send,
                    HTTPStatus.OK,
                    {"service": "openinfra-web", "version": __version__},
                    head_only=method == "HEAD",
                )
                return
            if path == "/config.json":
                await self._json(
                    send,
                    HTTPStatus.OK,
                    self._config.as_public_dict(),
                    head_only=method == "HEAD",
                )
                return
            if path == "/bootstrap.json":
                await self._json(
                    send,
                    HTTPStatus.OK,
                    self._config.as_bootstrap_dict(),
                    head_only=method == "HEAD",
                )
                return
            if path == "/status":
                await self._json(
                    send,
                    HTTPStatus.OK,
                    self._config.as_status_dict(),
                    head_only=method == "HEAD",
                )
                return
            if path == "/ready":
                await self._proxy(
                    scope,
                    receive,
                    send,
                    route="/ready",
                    query_string=query_string,
                    headers=headers,
                    force_method="GET",
                )
                return
            if self._is_proxy_route(path):
                await self._proxy(
                    scope,
                    receive,
                    send,
                    route=path,
                    query_string=query_string,
                    headers=headers,
                )
                return
            await self._serve_static(
                send,
                path,
                bytes(headers.get("accept-encoding", ""), "latin-1"),
                headers.get("if-none-match", ""),
                query_string,
                head_only=method == "HEAD",
            )
            return
        if method in {"POST", "PUT", "PATCH", "DELETE"} and self._is_proxy_route(path):
            await self._proxy(
                scope,
                receive,
                send,
                route=path,
                query_string=query_string,
                headers=headers,
            )
            return
        await self._json(send, HTTPStatus.NOT_FOUND, {"error": "route not served by openinfra-web"})

    async def _send_metrics(self, send: AsgiSend, *, head_only: bool) -> None:
        payload = self._telemetry.render_prometheus()
        await send(
            {
                "type": "http.response.start",
                "status": HTTPStatus.OK.value,
                "headers": [
                    (b"content-type", b"text/plain; version=0.0.4; charset=utf-8"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"" if head_only else payload,
                "more_body": False,
            }
        )

    def _is_proxy_route(self, path: str) -> bool:
        return path in {"/docs", "/swagger", "/redoc", "/openapi.yaml"} or path.startswith("/api/")

    async def _proxy(
        self,
        scope: AsgiScope,
        receive: AsgiReceive,
        send: AsgiSend,
        *,
        route: str,
        query_string: bytes,
        headers: Mapping[str, str],
        force_method: str | None = None,
    ) -> None:
        method = force_method or str(scope.get("method", "GET")).upper()
        if self._requires_server_side_bearer(method, route):
            await self._json(
                send,
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "web backend bearer token is not configured",
                    "hint": (
                        "set OPENINFRA_WEB_BACKEND_BEARER_TOKEN or use "
                        "--backend-bearer-token-file for openinfra-web"
                    ),
                },
            )
            return
        try:
            body = await self._read_body(receive) if method not in {"GET", "HEAD"} else b""
            client = await self._ensure_client()
            target = self._target_url(route, query_string)
            request_headers = self._proxy_headers(headers)
            async with client.stream(
                method,
                target,
                content=body or None,
                headers=request_headers,
            ) as response:
                if response.status_code >= HTTPStatus.BAD_REQUEST.value:
                    error_body = await response.aread()
                    if self._is_raw_missing_bearer_error(error_body):
                        await self._json(
                            send,
                            HTTPStatus.BAD_GATEWAY,
                            {
                                "error": "backend authentication failed through openinfra-web",
                                "reason": (
                                    "server-side backend bearer token was not accepted by the API"
                                ),
                            },
                        )
                        return
                    await self._buffered_upstream_response(
                        send,
                        response.status_code,
                        response.headers,
                        error_body,
                        route,
                        method=method,
                        secure=self._is_secure_request(scope, headers),
                    )
                    return
                response_headers = self._response_headers(
                    response.headers,
                    route,
                    method=method,
                    secure=self._is_secure_request(scope, headers),
                )
                await send(
                    {
                        "type": "http.response.start",
                        "status": response.status_code,
                        "headers": response_headers,
                    }
                )
                if method == "HEAD":
                    await send({"type": "http.response.body", "body": b"", "more_body": False})
                    return
                if response.is_stream_consumed:
                    await send(
                        {
                            "type": "http.response.body",
                            "body": response.content,
                            "more_body": False,
                        }
                    )
                    return
                async for chunk in response.aiter_raw():
                    await send({"type": "http.response.body", "body": chunk, "more_body": True})
                await send({"type": "http.response.body", "body": b"", "more_body": False})
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            await self._json(
                send,
                HTTPStatus.BAD_GATEWAY,
                {"error": "backend unavailable", "reason": type(exc).__name__},
            )
        except OpenInfraError as exc:
            await self._json(send, HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    async def _buffered_upstream_response(
        self,
        send: AsgiSend,
        status: int,
        headers: httpx.Headers,
        body: bytes,
        route: str,
        *,
        method: str,
        secure: bool,
    ) -> None:
        response_headers = self._response_headers(headers, route, method=method, secure=secure)
        response_headers = [
            (name, value) for name, value in response_headers if name != b"content-length"
        ]
        response_headers.append((b"content-length", str(len(body)).encode("ascii")))
        await send({"type": "http.response.start", "status": status, "headers": response_headers})
        await send({"type": "http.response.body", "body": body, "more_body": False})

    async def _serve_static(
        self,
        send: AsgiSend,
        route: str,
        accept_encoding: bytes,
        if_none_match: str,
        query_string: bytes,
        *,
        head_only: bool,
    ) -> None:
        relative = "index.html" if route in {"", "/"} else route.lstrip("/")
        candidate = (self._config.static_root / relative).resolve()
        if not self._is_safe_static_path(candidate):
            await self._json(send, HTTPStatus.NOT_FOUND, {"error": "asset not found"})
            return
        asset = await asyncio.to_thread(self._static_assets.load, candidate)
        use_gzip = self._accepts_gzip(accept_encoding) and asset.gzip_body is not None
        body = asset.gzip_body if use_gzip and asset.gzip_body is not None else asset.identity_body
        etag = (asset.gzip_etag or asset.identity_etag) if use_gzip else asset.identity_etag
        cache_control = self._static_cache_control(route, query_string)
        response_headers = [
            (b"etag", etag.encode("ascii")),
            (b"last-modified", asset.last_modified.encode("ascii")),
            (b"vary", b"Accept-Encoding"),
            *self._security_headers(cache_control=cache_control),
        ]
        if if_none_match.strip() == etag:
            await send(
                {
                    "type": "http.response.start",
                    "status": HTTPStatus.NOT_MODIFIED.value,
                    "headers": response_headers,
                }
            )
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return
        response_headers.extend(
            [
                (b"content-type", asset.content_type.encode("latin-1")),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )
        if use_gzip:
            response_headers.append((b"content-encoding", b"gzip"))
        await send(
            {
                "type": "http.response.start",
                "status": HTTPStatus.OK.value,
                "headers": response_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"" if head_only else body,
                "more_body": False,
            }
        )

    async def _read_body(self, receive: AsgiReceive) -> bytes:
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                raise OpenInfraError("client disconnected before request body was complete")
            if message.get("type") != "http.request":
                continue
            chunk = bytes(message.get("body", b""))
            size += len(chunk)
            if size > self._config.max_request_body_bytes:
                raise OpenInfraError("request body exceeds OpenInfra web proxy limit")
            chunks.append(chunk)
            if not bool(message.get("more_body", False)):
                return b"".join(chunks)

    async def _json(
        self,
        send: AsgiSend,
        status: HTTPStatus,
        payload: Mapping[str, object],
        *,
        head_only: bool = False,
    ) -> None:
        body = json.dumps(dict(payload), sort_keys=True).encode("utf-8")
        headers = [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"content-length", str(len(body)).encode("ascii")),
            *self._security_headers(cache_control="no-store"),
        ]
        await send({"type": "http.response.start", "status": status.value, "headers": headers})
        await send(
            {
                "type": "http.response.body",
                "body": b"" if head_only else body,
                "more_body": False,
            }
        )

    def _request_header_map(self, scope: AsgiScope) -> dict[str, str]:
        result: dict[str, str] = {}
        for raw_name, raw_value in scope.get("headers", []):
            result[bytes(raw_name).decode("latin-1").lower()] = bytes(raw_value).decode("latin-1")
        return result

    def _proxy_headers(self, incoming: Mapping[str, str]) -> dict[str, str]:
        headers = {
            key: value
            for key, value in incoming.items()
            if key.lower() in self._forwarded_request_headers
        }
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
        consistency_token = incoming.get("x-openinfra-consistency-token", "").strip()
        if not consistency_token:
            consistency_token = self._consistency_token_from_cookie(incoming.get("cookie", ""))
        if consistency_token:
            headers["X-OpenInfra-Consistency-Token"] = consistency_token
        return self._telemetry.inject_trace_headers(headers)

    def _response_headers(
        self,
        headers: httpx.Headers,
        route: str,
        *,
        method: str,
        secure: bool,
    ) -> list[tuple[bytes, bytes]]:
        result = [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in headers.multi_items()
            if name.lower() in self._forwarded_response_headers
        ]
        result.extend(
            self._security_headers(
                api_docs=route in {"/docs", "/swagger", "/redoc"},
                cache_control="no-store",
            )
        )
        token = headers.get("x-openinfra-consistency-token", "").strip()
        if token and method in {"POST", "PUT", "PATCH", "DELETE"}:
            cookie = (
                f"{self._consistency_cookie_name}={token}; Path=/api; HttpOnly; "
                "SameSite=Strict; "
                f"Max-Age={self._consistency_cookie_ttl_seconds}"
            )
            if secure:
                cookie += "; Secure"
            result.append((b"set-cookie", cookie.encode("latin-1")))
        return result

    def _consistency_token_from_cookie(self, raw_cookie: str) -> str:
        if not raw_cookie.strip():
            return ""
        cookie = SimpleCookie()
        try:
            cookie.load(raw_cookie)
        except Exception:
            return ""
        morsel = cookie.get(self._consistency_cookie_name)
        return morsel.value.strip() if morsel is not None else ""

    def _is_secure_request(self, scope: AsgiScope, headers: Mapping[str, str]) -> bool:
        forwarded = headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
        return forwarded == "https" or str(scope.get("scheme", "http")).lower() == "https"

    def _security_headers(
        self,
        *,
        api_docs: bool = False,
        cache_control: str | None,
    ) -> list[tuple[bytes, bytes]]:
        headers = [
            (b"x-content-type-options", b"nosniff"),
            (b"referrer-policy", b"no-referrer"),
            (b"x-frame-options", b"DENY"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
        ]
        if cache_control is not None:
            headers.append((b"cache-control", cache_control.encode("ascii")))
        if api_docs:
            csp = (
                "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline' https://unpkg.com; "
                "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.redoc.ly"
            )
        else:
            csp = (
                "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; script-src 'self'"
            )
        headers.append((b"content-security-policy", csp.encode("ascii")))
        return headers

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
        return route.startswith("/api/v1/") and method in {"GET", "POST", "PUT", "PATCH", "DELETE"}

    def _target_url(self, route: str, query_string: bytes) -> str:
        target = urljoin(self._config.normalized_backend_url(), route.lstrip("/"))
        if query_string:
            target += "?" + query_string.decode("ascii")
        return target

    def _is_raw_missing_bearer_error(self, body: bytes) -> bool:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        return isinstance(payload, dict) and str(payload.get("error", "")).strip().lower() == (
            "missing bearer token"
        )

    def _accepts_gzip(self, accept_encoding: bytes) -> bool:
        for value in accept_encoding.decode("latin-1").lower().split(","):
            encoding, *parameters = (part.strip() for part in value.split(";"))
            if encoding != "gzip":
                continue
            for parameter in parameters:
                name, separator, raw_value = parameter.partition("=")
                if separator and name.strip() == "q":
                    try:
                        return float(raw_value.strip()) > 0
                    except ValueError:
                        return False
            return True
        return False

    def _static_cache_control(self, route: str, query_string: bytes) -> str:
        if route in {"", "/", "/index.html"}:
            return "no-cache, max-age=0, must-revalidate"
        if route.startswith("/assets/"):
            versioned = any(
                pair == f"v={__version__}"
                for pair in query_string.decode("ascii").split("&")
                if pair
            )
            if versioned:
                return "public, max-age=31536000, immutable"
            return "public, max-age=3600, must-revalidate"
        return "no-cache, max-age=0, must-revalidate"

    def _is_safe_static_path(self, candidate: Path) -> bool:
        try:
            candidate.relative_to(self._config.static_root)
        except ValueError:
            return False
        return candidate.is_file()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    limits=httpx.Limits(
                        max_connections=self._pool_settings.max_connections,
                        max_keepalive_connections=(self._pool_settings.max_keepalive_connections),
                        keepalive_expiry=self._pool_settings.keepalive_expiry_seconds,
                    ),
                    timeout=httpx.Timeout(
                        connect=self._pool_settings.connect_timeout_seconds,
                        read=self._pool_settings.read_timeout_seconds,
                        write=self._pool_settings.write_timeout_seconds,
                        pool=self._pool_settings.pool_timeout_seconds,
                    ),
                    follow_redirects=False,
                )
        return self._client

    async def _lifespan(self, receive: AsgiReceive, send: AsgiSend) -> None:
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "lifespan.startup":
                await self._ensure_client()
                await send({"type": "lifespan.startup.complete"})
                continue
            if message_type == "lifespan.shutdown":
                if self._owns_client and self._client is not None:
                    await self._client.aclose()
                    self._client = None
                await asyncio.to_thread(self._telemetry.close)
                await send({"type": "lifespan.shutdown.complete"})
                return


class OpenInfraWebAsgiFactory:
    def __call__(self) -> OpenInfraWebAsgiApplication:
        config = OpenInfraWebConfigFactory().from_args([])
        telemetry = OpenInfraTelemetry.from_environment(
            service_name="openinfra-web", edition=config.edition
        )
        return OpenInfraWebAsgiApplication(
            config,
            OpenInfraWebHttpPoolSettings.from_environment(config.edition),
            consistency_cookie_ttl_seconds=int(
                os.environ.get("OPENINFRA_READ_AFTER_WRITE_TTL_SECONDS", "10")
            ),
            telemetry=telemetry,
        )


web_app_factory = OpenInfraWebAsgiFactory()
