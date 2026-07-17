from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable, Mapping, MutableMapping
from email.message import Message
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from openinfra.application.container import ApplicationFactory, OpenInfraApplication
from openinfra.domain.common import OpenInfraError
from openinfra.infrastructure.oracle import OracleConnectionSettings
from openinfra.infrastructure.postgresql import PostgreSQLConnectionPoolSettings
from openinfra.infrastructure.read_routing import (
    PostgreSQLReadRoutingSettings,
    ReadConsistencyTokenCodec,
    ReadRoute,
    ReadRoutingContext,
)
from openinfra.infrastructure.runtime_config import (
    RuntimeDatabaseDsnResolver,
    RuntimeOracleSettingsResolver,
)
from openinfra.interfaces.asgi_observability import ObservedAsgiSend
from openinfra.interfaces.http_api import OpenInfraApiRuntime, OpenInfraRequestHandler

AsgiMessage = MutableMapping[str, Any]
AsgiReceive = Callable[[], Awaitable[AsgiMessage]]
AsgiSend = Callable[[AsgiMessage], Awaitable[None]]
AsgiScope = Mapping[str, Any]


class OpenInfraAsgiRequestHandler(OpenInfraRequestHandler):
    """In-memory compatibility adapter for the transport-neutral API runtime.

    The existing route contract remains unchanged while the socket lifecycle, keep-alive,
    process model and backpressure are delegated to the ASGI server. Synchronous domain and
    PostgreSQL work is isolated in the ASGI worker thread pool until route modules are migrated
    incrementally to native async handlers.
    """

    def __init__(
        self,
        runtime: OpenInfraApiRuntime,
        method: str,
        path: str,
        headers: Message,
        body: bytes,
    ) -> None:
        self.server = cast(Any, runtime)
        self.command = method.upper()
        self.path = path
        self.headers = headers
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        self.request_version = "HTTP/1.1"
        self.protocol_version = "HTTP/1.1"
        self.client_address = ("asgi", 0)
        self.close_connection = True
        self._response_status = HTTPStatus.INTERNAL_SERVER_ERROR.value
        self._response_headers: list[tuple[str, str]] = []
        self._headers_complete = False

    def dispatch(self) -> tuple[int, tuple[tuple[str, str], ...], bytes]:
        method = getattr(self, "do_" + self.command, None)
        if not callable(method):
            self.send_response(HTTPStatus.METHOD_NOT_ALLOWED.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            body = json.dumps({"error": "method not allowed"}, sort_keys=True).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            method()
        payload = cast(BytesIO, self.wfile).getvalue()
        if not any(name.lower() == "content-length" for name, _ in self._response_headers):
            self._response_headers.append(("Content-Length", str(len(payload))))
        return self._response_status, tuple(self._response_headers), payload

    def send_response(self, code: int, message: str | None = None) -> None:
        del message
        self._response_status = int(code)

    def send_header(self, keyword: str, value: str) -> None:
        self._response_headers.append((str(keyword), str(value)))

    def end_headers(self) -> None:
        self._headers_complete = True

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        del code, size


class OpenInfraApiAsgiApplication:
    def __init__(
        self,
        runtime: OpenInfraApiRuntime,
        *,
        max_request_body_bytes: int = 1_048_576,
        consistency_token_codec: ReadConsistencyTokenCodec | None = None,
    ) -> None:
        if max_request_body_bytes <= 0:
            raise OpenInfraError("ASGI max request body size must be positive")
        self._runtime = runtime
        self._max_request_body_bytes = max_request_body_bytes
        self._consistency_token_codec = consistency_token_codec

    async def __call__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend) -> None:
        scope_type = str(scope.get("type", ""))
        if scope_type == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope_type != "http":
            await self._send_json(
                send,
                HTTPStatus.BAD_REQUEST,
                {"error": "unsupported ASGI scope"},
            )
            return
        method = str(scope.get("method", "GET")).upper()
        raw_path = str(scope.get("path", "/"))
        if raw_path == "/metrics" and method in {"GET", "HEAD"}:
            await self._send_metrics(send, head_only=method == "HEAD")
            return
        header_map = self._header_map(scope)
        observation = self._runtime.application.telemetry.begin_http_request(
            method=method, route=raw_path, headers=header_map
        )
        observed_send = ObservedAsgiSend(send, observation)
        request_size = 0
        try:
            body = await self._read_body(receive)
            request_size = len(body)
            raw_query = bytes(scope.get("query_string", b""))
            path = raw_path + (("?" + raw_query.decode("ascii")) if raw_query else "")
            headers = self._headers(scope, len(body))
            route = self._resolve_read_route(method, headers)
            handler = OpenInfraAsgiRequestHandler(self._runtime, method, path, headers, body)

            def dispatch() -> tuple[int, tuple[tuple[str, str], ...], bytes]:
                with ReadRoutingContext.scope(route):
                    read_scope = getattr(self._runtime.application.store, "read_scope", None)
                    if method in {"GET", "HEAD"} and callable(read_scope):
                        with read_scope():
                            return handler.dispatch()
                    return handler.dispatch()

            status, response_headers, payload = await asyncio.to_thread(dispatch)
            response_headers = self._consistency_response_headers(method, status, response_headers)
            await observed_send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [
                        (name.lower().encode("latin-1"), value.encode("latin-1"))
                        for name, value in response_headers
                    ],
                }
            )
            await observed_send({"type": "http.response.body", "body": payload, "more_body": False})
        except OpenInfraError as exc:
            observed_send.record_exception(exc)
            await self._send_json(observed_send, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            observed_send.record_exception(exc)
            await self._send_json(
                observed_send,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal server error", "reason": type(exc).__name__},
            )
        finally:
            observed_send.finish(request_size)

    def _header_map(self, scope: AsgiScope) -> dict[str, str]:
        values: dict[str, str] = {}
        for raw_name, raw_value in scope.get("headers", []):
            name = bytes(raw_name).decode("latin-1").lower()
            value = bytes(raw_value).decode("latin-1")
            values[name] = value
        return values

    async def _send_metrics(self, send: AsgiSend, *, head_only: bool) -> None:
        payload = self._runtime.application.telemetry.render_prometheus()
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

    def _resolve_read_route(self, method: str, headers: Message) -> ReadRoute:
        if method not in {"GET", "HEAD"}:
            return ReadRoute.PRIMARY
        token = headers.get("X-OpenInfra-Consistency-Token", "").strip()
        if not token:
            return ReadRoute.REPLICA
        codec = self._consistency_token_codec
        if codec is None or not codec.validate(token):
            raise OpenInfraError("invalid or expired read consistency token")
        return ReadRoute.PRIMARY

    def _consistency_response_headers(
        self,
        method: str,
        status: int,
        headers: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        codec = self._consistency_token_codec
        if (
            codec is None
            or method not in {"POST", "PUT", "PATCH", "DELETE"}
            or status >= HTTPStatus.BAD_REQUEST.value
        ):
            return headers
        return (
            *headers,
            ("X-OpenInfra-Consistency-Token", codec.issue()),
            ("Access-Control-Expose-Headers", "X-OpenInfra-Consistency-Token"),
        )

    async def _read_body(self, receive: AsgiReceive) -> bytes:
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "http.disconnect":
                raise OpenInfraError("client disconnected before request body was complete")
            if message_type != "http.request":
                continue
            chunk = bytes(message.get("body", b""))
            size += len(chunk)
            if size > self._max_request_body_bytes:
                raise OpenInfraError("request body exceeds OpenInfra API limit")
            chunks.append(chunk)
            if not bool(message.get("more_body", False)):
                return b"".join(chunks)

    def _headers(self, scope: AsgiScope, body_length: int) -> Message:
        headers = Message()
        for raw_name, raw_value in scope.get("headers", []):
            name = bytes(raw_name).decode("latin-1")
            value = bytes(raw_value).decode("latin-1")
            headers.add_header(name, value)
        if body_length and headers.get("Content-Length") is None:
            headers["Content-Length"] = str(body_length)
        return headers

    async def _lifespan(self, receive: AsgiReceive, send: AsgiSend) -> None:
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
                continue
            if message_type == "lifespan.shutdown":
                close = getattr(self._runtime.application.store, "close", None)
                if callable(close):
                    await asyncio.to_thread(close)
                await asyncio.to_thread(self._runtime.application.telemetry.close)
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def _send_json(
        self,
        send: AsgiSend,
        status: HTTPStatus,
        payload: Mapping[str, object],
    ) -> None:
        body = json.dumps(dict(payload), sort_keys=True).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status.value,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})


class OpenInfraApiEnvironmentApplicationFactory:
    def create(self) -> OpenInfraApplication:
        backend = os.environ.get("OPENINFRA_API_BACKEND", "postgresql").strip().lower()
        edition = os.environ.get("OPENINFRA_EDITION", "enterprise").strip().lower()
        if backend == "json":
            data_path = Path(os.environ.get("OPENINFRA_API_DATA", ".openinfra.json"))
            return ApplicationFactory().create_json_application(data_path, edition=edition)
        if backend == "oracle":
            settings = RuntimeOracleSettingsResolver().resolve(
                explicit_dsn=os.environ.get("OPENINFRA_API_ORACLE_DSN"),
                explicit_user=os.environ.get("OPENINFRA_API_ORACLE_USER"),
            )
            if not isinstance(settings, OracleConnectionSettings):
                raise OpenInfraError("invalid Oracle runtime settings")
            return ApplicationFactory().create_oracle_application(
                settings, seed=False, edition=edition
            )
        if backend != "postgresql":
            raise OpenInfraError("OPENINFRA_API_BACKEND must be json, postgresql or oracle")
        dsn = RuntimeDatabaseDsnResolver().resolve(os.environ.get("OPENINFRA_API_POSTGRES_DSN"))
        if not dsn:
            raise OpenInfraError("OPENINFRA_DATABASE_DSN is required for PostgreSQL ASGI runtime")
        workers = int(os.environ.get("OPENINFRA_API_WORKERS_RESOLVED", "1"))
        pool_settings = PostgreSQLConnectionPoolSettings.from_environment(edition, workers)
        read_dsn = RuntimeDatabaseDsnResolver().resolve_read_replica(
            os.environ.get("OPENINFRA_API_POSTGRES_READ_DSN")
        )
        if not read_dsn:
            return ApplicationFactory().create_postgresql_application(
                dsn,
                seed=False,
                edition=edition,
                pool_settings=pool_settings,
            )
        read_routing_settings = PostgreSQLReadRoutingSettings.from_environment(read_dsn)
        return ApplicationFactory().create_postgresql_application(
            dsn,
            seed=False,
            edition=edition,
            pool_settings=pool_settings,
            read_dsn=read_dsn,
            read_pool_settings=pool_settings,
            read_routing_settings=read_routing_settings,
        )


class OpenInfraApiAsgiFactory:
    def __call__(self) -> OpenInfraApiAsgiApplication:
        application = OpenInfraApiEnvironmentApplicationFactory().create()
        auth_required = os.environ.get("OPENINFRA_AUTH_REQUIRED", "false").strip().lower() == "true"
        openapi_path = os.environ.get("OPENINFRA_API_OPENAPI_PATH", "").strip() or None
        max_body = int(os.environ.get("OPENINFRA_API_MAX_REQUEST_BODY_BYTES", "1048576"))
        read_dsn = RuntimeDatabaseDsnResolver().resolve_read_replica(
            os.environ.get("OPENINFRA_API_POSTGRES_READ_DSN")
        )
        codec: ReadConsistencyTokenCodec | None = None
        if read_dsn:
            key_material = RuntimeDatabaseDsnResolver().resolve_consistency_secret()
            if not key_material:
                raise OpenInfraError(
                    "OPENINFRA_READ_CONSISTENCY_SECRET is required when read routing is enabled"
                )
            codec = ReadConsistencyTokenCodec(
                key_material,
                int(os.environ.get("OPENINFRA_READ_AFTER_WRITE_TTL_SECONDS", "10")),
            )
        return OpenInfraApiAsgiApplication(
            OpenInfraApiRuntime(application, auth_required, openapi_path),
            max_request_body_bytes=max_body,
            consistency_token_codec=codec,
        )


api_app_factory = OpenInfraApiAsgiFactory()
