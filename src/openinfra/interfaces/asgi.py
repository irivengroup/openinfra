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
from openinfra.infrastructure.postgresql import PostgreSQLConnectionPoolSettings
from openinfra.infrastructure.runtime_config import RuntimeDatabaseDsnResolver
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
    ) -> None:
        if max_request_body_bytes <= 0:
            raise OpenInfraError("ASGI max request body size must be positive")
        self._runtime = runtime
        self._max_request_body_bytes = max_request_body_bytes

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
        try:
            body = await self._read_body(receive)
            method = str(scope.get("method", "GET")).upper()
            raw_path = str(scope.get("path", "/"))
            raw_query = bytes(scope.get("query_string", b""))
            path = raw_path + (("?" + raw_query.decode("ascii")) if raw_query else "")
            headers = self._headers(scope, len(body))
            handler = OpenInfraAsgiRequestHandler(self._runtime, method, path, headers, body)
            status, response_headers, payload = await asyncio.to_thread(handler.dispatch)
        except OpenInfraError as exc:
            await self._send_json(send, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive runtime boundary
            await self._send_json(
                send,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "internal server error", "reason": type(exc).__name__},
            )
            return
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (name.lower().encode("latin-1"), value.encode("latin-1"))
                    for name, value in response_headers
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload, "more_body": False})

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
        if backend != "postgresql":
            raise OpenInfraError("OPENINFRA_API_BACKEND must be json or postgresql")
        dsn = RuntimeDatabaseDsnResolver().resolve(os.environ.get("OPENINFRA_API_POSTGRES_DSN"))
        if not dsn:
            raise OpenInfraError("OPENINFRA_DATABASE_DSN is required for PostgreSQL ASGI runtime")
        workers = int(os.environ.get("OPENINFRA_API_WORKERS_RESOLVED", "1"))
        pool_settings = PostgreSQLConnectionPoolSettings.from_environment(edition, workers)
        return ApplicationFactory().create_postgresql_application(
            dsn,
            seed=False,
            edition=edition,
            pool_settings=pool_settings,
        )


class OpenInfraApiAsgiFactory:
    def __call__(self) -> OpenInfraApiAsgiApplication:
        application = OpenInfraApiEnvironmentApplicationFactory().create()
        auth_required = os.environ.get("OPENINFRA_AUTH_REQUIRED", "false").strip().lower() == "true"
        openapi_path = os.environ.get("OPENINFRA_API_OPENAPI_PATH", "").strip() or None
        max_body = int(os.environ.get("OPENINFRA_API_MAX_REQUEST_BODY_BYTES", "1048576"))
        return OpenInfraApiAsgiApplication(
            OpenInfraApiRuntime(application, auth_required, openapi_path),
            max_request_body_bytes=max_body,
        )


api_app_factory = OpenInfraApiAsgiFactory()
