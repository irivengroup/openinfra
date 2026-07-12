from __future__ import annotations

import asyncio
import json
import os
from argparse import Namespace
from email.message import Message
from pathlib import Path
from typing import Any

import httpx
import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLConnectionPoolSettings,
)
from openinfra.infrastructure.read_routing import (
    ReadConsistencyTokenCodec,
    ReadRoute,
    ReadRoutingContext,
)
from openinfra.interfaces import asgi as api_asgi
from openinfra.interfaces import asgi_web as web_asgi
from openinfra.interfaces.asgi import OpenInfraApiAsgiApplication
from openinfra.interfaces.asgi_web import (
    OpenInfraWebAsgiApplication,
    OpenInfraWebHttpPoolSettings,
)
from openinfra.interfaces.http_api import OpenInfraApiEntrypoint, OpenInfraApiRuntime
from openinfra.interfaces.runtime_environment import OpenInfraRuntimeEnvironmentScope
from openinfra.interfaces.web import (
    OpenInfraWebConfig,
    OpenInfraWebConfigValidator,
    OpenInfraWebEntrypoint,
    OpenInfraWebStaticLocator,
)


def _request(
    app: Any,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    headers: tuple[tuple[bytes, bytes], ...] = (),
    query: bytes = b"",
    messages: list[dict[str, Any]] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    async def run() -> tuple[int, dict[str, str], bytes]:
        received = list(messages or [{"type": "http.request", "body": body, "more_body": False}])
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            if received:
                return received.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await app(
            {
                "type": "http",
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": query,
                "headers": list(headers),
                "client": ("127.0.0.1", 1234),
                "server": ("127.0.0.1", 8080),
            },
            receive,
            send,
        )
        start = next(item for item in sent if item["type"] == "http.response.start")
        payload = b"".join(
            item.get("body", b"") for item in sent if item["type"] == "http.response.body"
        )
        response_headers = {
            bytes(name).decode("latin-1"): bytes(value).decode("latin-1")
            for name, value in start.get("headers", [])
        }
        return int(start["status"]), response_headers, payload

    return asyncio.run(run())


def _lifespan(app: Any) -> list[dict[str, Any]]:
    async def run() -> list[dict[str, Any]]:
        messages = [
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
        ]
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return messages.pop(0)

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await app({"type": "lifespan"}, receive, send)
        return sent

    return asyncio.run(run())


def _web_config(**overrides: object) -> OpenInfraWebConfig:
    values: dict[str, object] = {
        "host": "127.0.0.1",
        "port": 2006,
        "backend_url": "http://api:8080",
        "public_api_base_url": "/api",
        "public_api_docs_base_url": "",
        "static_root": OpenInfraWebStaticLocator().resolve(None),
        "edition": "pro",
        "auth_mode": "standard",
        "allow_insecure_backend": True,
        "backend_bearer_token": "t" * 40,
    }
    values.update(overrides)
    return OpenInfraWebConfig(**values)  # type: ignore[arg-type]


def _pool_settings() -> OpenInfraWebHttpPoolSettings:
    return OpenInfraWebHttpPoolSettings(20, 10, 30, 2, 30, 30, 2)


def test_api_asgi_serves_existing_contract_and_method_errors(tmp_path: Path) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "state.json")
    app = OpenInfraApiAsgiApplication(OpenInfraApiRuntime(application), max_request_body_bytes=32)

    status, headers, body = _request(app, "GET", "/health")
    assert status == 200
    assert headers["content-type"] == "application/json; charset=utf-8"
    assert json.loads(body) == {"status": "ok"}

    root_status, _, root_body = _request(app, "GET", "/", query=b"ignored=true")
    assert root_status == 200
    assert json.loads(root_body)["service"] == "openinfra-api"

    method_status, _, method_body = _request(app, "OPTIONS", "/health")
    assert method_status == 405
    assert json.loads(method_body) == {"error": "method not allowed"}


def test_api_asgi_request_boundaries_and_lifespan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "state.json")
    closed: list[bool] = []
    application.store.close = lambda: closed.append(True)  # type: ignore[attr-defined,method-assign]
    app = OpenInfraApiAsgiApplication(OpenInfraApiRuntime(application), max_request_body_bytes=3)

    status, _, body = _request(app, "POST", "/api/v1/unknown", body=b"1234")
    assert status == 400
    assert "exceeds OpenInfra API limit" in body.decode()

    disconnect_status, _, disconnect_body = _request(
        app,
        "POST",
        "/api/v1/unknown",
        messages=[{"type": "http.disconnect"}],
    )
    assert disconnect_status == 400
    assert "client disconnected" in disconnect_body.decode()

    async def unsupported() -> tuple[int, dict[str, str], bytes]:
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await app({"type": "websocket"}, receive, send)
        start = sent[0]
        return start["status"], {}, sent[1]["body"]

    unsupported_status, _, unsupported_body = asyncio.run(unsupported())
    assert unsupported_status == 400
    assert "unsupported ASGI scope" in unsupported_body.decode()

    messages = _lifespan(app)
    assert messages == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]
    assert closed == [True]

    class FailingHandler:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def dispatch(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(api_asgi, "OpenInfraAsgiRequestHandler", FailingHandler)
    internal_status, _, internal_body = _request(app, "GET", "/health")
    assert internal_status == 500
    assert json.loads(internal_body)["reason"] == "RuntimeError"


def test_api_asgi_factories_and_worker_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENINFRA_API_BACKEND", "json")
    monkeypatch.setenv("OPENINFRA_API_DATA", str(tmp_path / "state.json"))
    monkeypatch.setenv("OPENINFRA_EDITION", "pro")
    monkeypatch.setenv("OPENINFRA_AUTH_REQUIRED", "true")
    app = api_asgi.api_app_factory()
    assert _request(app, "GET", "/health")[0] == 200

    monkeypatch.setenv("OPENINFRA_API_BACKEND", "invalid")
    with pytest.raises(OpenInfraError, match="json or postgresql"):
        api_asgi.api_app_factory()

    monkeypatch.setenv("OPENINFRA_API_BACKEND", "postgresql")
    monkeypatch.delenv("OPENINFRA_DATABASE_DSN", raising=False)
    monkeypatch.delenv("OPENINFRA_API_POSTGRES_DSN", raising=False)
    monkeypatch.setattr(api_asgi.RuntimeDatabaseDsnResolver, "resolve", lambda self, value: None)
    with pytest.raises(OpenInfraError, match="required"):
        api_asgi.api_app_factory()

    assert OpenInfraApiEntrypoint._resolve_workers("json", "pro", 0) == 1
    with pytest.raises(OpenInfraError, match="exactly one"):
        OpenInfraApiEntrypoint._resolve_workers("json", "pro", 2)
    with pytest.raises(OpenInfraError, match="negative"):
        OpenInfraApiEntrypoint._resolve_workers("postgresql", "pro", -1)
    assert OpenInfraApiEntrypoint._resolve_workers("postgresql", "lite", 0) == 1
    assert OpenInfraApiEntrypoint._resolve_workers("postgresql", "pro", 3) == 3
    with pytest.raises(OpenInfraError, match="exceed 64"):
        OpenInfraApiEntrypoint._resolve_workers("postgresql", "enterprise", 65)
    with pytest.raises(OpenInfraError, match="edition"):
        OpenInfraApiEntrypoint._resolve_workers("postgresql", "unknown", 0)

    for field in ("limit_concurrency", "backlog", "timeout_keep_alive"):
        values = {"limit_concurrency": 1, "backlog": 1, "timeout_keep_alive": 1}
        values[field] = 0
        with pytest.raises(OpenInfraError):
            OpenInfraApiEntrypoint._validate_runtime_limits(Namespace(**values), 1)
    with pytest.raises(OpenInfraError, match="worker count"):
        OpenInfraApiEntrypoint._validate_runtime_limits(
            Namespace(limit_concurrency=1, backlog=1, timeout_keep_alive=1), 0
        )

    calls: list[dict[str, Any]] = []
    runtime_snapshots: list[dict[str, str | None]] = []
    monkeypatch.setattr(api_asgi, "RuntimeDatabaseDsnResolver", RuntimeDatabaseDsnResolverStub)
    monkeypatch.setenv("OPENINFRA_EDITION", "baseline")
    monkeypatch.delenv("OPENINFRA_API_BACKEND", raising=False)

    def capture_api_runtime(*_args: object, **kwargs: Any) -> None:
        calls.append(kwargs)
        runtime_snapshots.append(
            {
                "backend": os.environ.get("OPENINFRA_API_BACKEND"),
                "edition": os.environ.get("OPENINFRA_EDITION"),
                "workers": os.environ.get("OPENINFRA_API_WORKERS_RESOLVED"),
            }
        )

    monkeypatch.setattr("openinfra.interfaces.http_api.uvicorn.run", capture_api_runtime)
    args = Namespace(
        host="127.0.0.1",
        port=8080,
        backend="json",
        data=tmp_path / "api.json",
        postgres_dsn=None,
        edition="pro",
        limit_concurrency=100,
        backlog=200,
        timeout_keep_alive=7,
    )
    assert OpenInfraApiEntrypoint._run_asgi(args, True, 1) == 0
    assert calls[0]["workers"] == 1
    assert calls[0]["limit_concurrency"] == 100
    assert calls[0]["access_log"] is False
    assert runtime_snapshots == [{"backend": "json", "edition": "pro", "workers": "1"}]
    assert "OPENINFRA_API_BACKEND" not in os.environ
    assert "OPENINFRA_API_WORKERS_RESOLVED" not in os.environ
    assert os.environ["OPENINFRA_EDITION"] == "baseline"


class RuntimeDatabaseDsnResolverStub:
    def resolve(self, value: str | None) -> str | None:
        return value


def test_api_asgi_adapter_headers_postgresql_factory_and_interrupts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "factory.json")
    runtime = OpenInfraApiRuntime(application)

    class HeaderlessHandler(api_asgi.OpenInfraAsgiRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    handler = HeaderlessHandler(runtime, "GET", "/", Message(), b"")
    status, headers, payload = handler.dispatch()
    handler.log_request(200, len(payload))
    assert status == 200
    assert ("Content-Length", "2") in headers
    assert payload == b"ok"

    with pytest.raises(OpenInfraError, match="positive"):
        OpenInfraApiAsgiApplication(runtime, max_request_body_bytes=0)

    app = OpenInfraApiAsgiApplication(runtime, max_request_body_bytes=8)
    request_status, _, _ = _request(
        app,
        "POST",
        "/api/v1/unknown",
        headers=((b"content-type", b"application/json"),),
        messages=[
            {"type": "websocket.receive"},
            {"type": "http.request", "body": b"{}", "more_body": False},
        ],
    )
    assert request_status == 404

    captured: dict[str, object] = {}

    def create_postgresql(
        _self: object,
        dsn: str,
        *,
        seed: bool,
        edition: str,
        pool_settings: object,
    ) -> object:
        captured.update(dsn=dsn, seed=seed, edition=edition, pool_settings=pool_settings)
        return application

    monkeypatch.setenv("OPENINFRA_API_BACKEND", "postgresql")
    monkeypatch.setenv("OPENINFRA_EDITION", "pro")
    monkeypatch.setenv("OPENINFRA_API_WORKERS_RESOLVED", "3")
    monkeypatch.setattr(
        api_asgi.RuntimeDatabaseDsnResolver,
        "resolve",
        lambda self, value: "postgresql://db/openinfra",
    )
    monkeypatch.setattr(
        api_asgi.PostgreSQLConnectionPoolSettings,
        "from_environment",
        lambda edition, workers: (edition, workers),
    )
    monkeypatch.setattr(
        api_asgi.ApplicationFactory, "create_postgresql_application", create_postgresql
    )
    assert api_asgi.OpenInfraApiEnvironmentApplicationFactory().create() is application
    assert captured == {
        "dsn": "postgresql://db/openinfra",
        "seed": False,
        "edition": "pro",
        "pool_settings": ("pro", 3),
    }

    args = Namespace(
        host="127.0.0.1",
        port=8080,
        backend="postgresql",
        data=tmp_path / "api.json",
        postgres_dsn="postgresql://db/openinfra",
        edition="enterprise",
        limit_concurrency=10,
        backlog=20,
        timeout_keep_alive=5,
    )
    monkeypatch.setattr(
        "openinfra.interfaces.http_api.uvicorn.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert OpenInfraApiEntrypoint._run_asgi(args, False, 2) == 0
    assert "OPENINFRA_API_POSTGRES_DSN" not in os.environ


def test_postgresql_pool_settings_validate_budgets(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = PostgreSQLConnectionPoolSettings.from_environment("pro", 4)
    assert settings.min_size == 1
    assert settings.max_size == 8
    assert settings.max_size * settings.worker_count <= settings.connection_budget

    monkeypatch.setenv("OPENINFRA_DB_POOL_MIN_SIZE", "3")
    monkeypatch.setenv("OPENINFRA_DB_POOL_MAX_SIZE", "5")
    monkeypatch.setenv("OPENINFRA_DB_CONNECTION_BUDGET", "20")
    explicit = PostgreSQLConnectionPoolSettings.from_environment("enterprise", 4)
    assert explicit.min_size == 3
    assert explicit.max_size == 5

    invalid_values = [
        (-1, 1, 1, 1, 1, 1, 10),
        (2, 1, 1, 1, 1, 1, 10),
        (0, 0, 1, 1, 1, 1, 10),
        (0, 1, 0, 1, 1, 1, 10),
        (0, 1, 1, 0, 1, 1, 10),
        (0, 1, 1, 1, 0, 1, 10),
        (0, 1, 1, 1, 1, 0, 10),
        (0, 1, 1, 1, 1, 1, 0),
        (0, 6, 1, 1, 1, 2, 10),
    ]
    for values in invalid_values:
        with pytest.raises(ValidationError):
            PostgreSQLConnectionPoolSettings(*values)
    with pytest.raises(ValidationError, match="edition"):
        PostgreSQLConnectionPoolSettings.from_environment("invalid", 1)


class FakePooledConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakePostgreSQLPool:
    def __init__(self) -> None:
        self.connection = FakePooledConnection()
        self.returned: list[FakePooledConnection] = []
        self.closed = False

    def getconn(self) -> Any:
        return self.connection

    def putconn(self, connection: Any) -> None:
        self.returned.append(connection)

    def close(self) -> None:
        self.closed = True


def test_postgresql_connection_factory_uses_and_closes_pool() -> None:
    pool = FakePostgreSQLPool()
    settings = PostgreSQLConnectionPoolSettings(1, 2, 1, 30, 60, 1, 10)

    def pool_factory(*_args: object) -> Any:
        return pool

    factory = PostgreSQLConnectionFactory(
        "postgresql://openinfra@db/openinfra",
        pool_settings=settings,
        pool_factory=pool_factory,
    )
    assert factory.pooled is True
    connection = factory.create()
    assert connection is pool.connection
    factory.release(connection)
    assert pool.returned == [pool.connection]
    assert pool.connection.closed is False
    factory.close()
    assert pool.closed is True

    with pytest.raises(ValidationError, match="explicit pool_factory"):
        PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=lambda dsn, profile: pool.connection,
            pool_settings=settings,
        )


def test_web_asgi_static_bootstrap_cache_and_security() -> None:
    app = OpenInfraWebAsgiApplication(_web_config(), _pool_settings())

    for path in ("/health", "/version", "/config.json", "/bootstrap.json", "/status"):
        status, headers, body = _request(app, "GET", path)
        assert status == 200
        assert headers["cache-control"] == "no-store"
        assert headers["x-content-type-options"] == "nosniff"
        assert body

    head_status, _, head_body = _request(app, "HEAD", "/version")
    assert head_status == 200
    assert head_body == b""

    index_status, index_headers, index_body = _request(app, "GET", "/")
    assert index_status == 200
    assert index_headers["cache-control"] == "no-cache, max-age=0, must-revalidate"
    assert b"OpenInfra" in index_body

    asset_status, asset_headers, asset_body = _request(
        app,
        "GET",
        "/assets/openinfra-web.js",
        query=b"v=0.31.2",
        headers=((b"accept-encoding", b"gzip"),),
    )
    assert asset_status == 200
    assert asset_headers["content-encoding"] == "gzip"
    assert asset_headers["cache-control"] == "public, max-age=31536000, immutable"
    assert asset_body.startswith(b"\x1f\x8b")

    not_modified, _, empty = _request(
        app,
        "GET",
        "/assets/openinfra-web.js",
        headers=(
            (b"accept-encoding", b"gzip"),
            (b"if-none-match", asset_headers["etag"].encode()),
        ),
    )
    assert not_modified == 304
    assert empty == b""

    identity_status, identity_headers, _ = _request(
        app,
        "GET",
        "/assets/openinfra-web.js",
        headers=((b"accept-encoding", b"gzip;q=0"),),
    )
    assert identity_status == 200
    assert "content-encoding" not in identity_headers

    invalid_q_status, invalid_q_headers, _ = _request(
        app,
        "GET",
        "/assets/openinfra-web.js",
        headers=((b"accept-encoding", b"gzip;q=bad"),),
    )
    assert invalid_q_status == 200
    assert "content-encoding" not in invalid_q_headers

    missing_status, _, _ = _request(app, "GET", "/missing.js")
    traversal_status, _, _ = _request(app, "GET", "/../VERSION")
    assert missing_status == traversal_status == 404


def test_web_asgi_proxy_streaming_and_errors() -> None:
    async def backend(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-openinfra-web"] == "openinfra-web"
        assert request.headers["authorization"].startswith("Bearer ")
        if request.url.path == "/ready":
            return httpx.Response(200, json={"ready": True})
        if request.url.path == "/docs":
            return httpx.Response(200, text="docs", headers={"content-type": "text/html"})
        if request.url.path.endswith("/missing-token"):
            return httpx.Response(401, json={"error": "missing bearer token"})
        if request.url.path.endswith("/plain-error"):
            return httpx.Response(400, text="bad", headers={"content-type": "text/plain"})
        return httpx.Response(
            200,
            content=b"streamed",
            headers={"content-type": "application/json", "etag": '"abc"'},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(backend))
    app = OpenInfraWebAsgiApplication(_web_config(), _pool_settings(), client=client)

    ready_status, _, ready_body = _request(app, "GET", "/ready")
    assert ready_status == 200
    assert json.loads(ready_body) == {"ready": True}

    status, headers, body = _request(
        app,
        "GET",
        "/api/v1/version",
        query=b"tenant_id=default",
        headers=((b"x-request-id", b"req-1"),),
    )
    assert status == 200
    assert headers["etag"] == '"abc"'
    assert body == b"streamed"

    docs_status, docs_headers, docs_body = _request(app, "GET", "/docs")
    assert docs_status == 200
    assert docs_body == b"docs"
    assert "cdn.redoc.ly" in docs_headers["content-security-policy"]

    missing_status, _, missing_body = _request(app, "GET", "/api/v1/missing-token")
    assert missing_status == 502
    assert "backend authentication failed" in missing_body.decode()

    error_status, error_headers, error_body = _request(app, "GET", "/api/v1/plain-error")
    assert error_status == 400
    assert error_headers["content-length"] == str(len(error_body))
    assert error_body == b"bad"

    asyncio.run(client.aclose())


def test_web_asgi_proxy_boundaries_and_network_failure() -> None:
    no_token = OpenInfraWebAsgiApplication(
        _web_config(backend_bearer_token=""),
        _pool_settings(),
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200))
        ),
    )
    status, _, body = _request(no_token, "GET", "/api/v1/dcim/sites")
    assert status == 503
    assert "not configured" in body.decode()
    docs_status, _, _ = _request(no_token, "GET", "/docs")
    assert docs_status == 200

    async def timeout_backend(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    timeout_client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_backend))
    failing = OpenInfraWebAsgiApplication(_web_config(), _pool_settings(), client=timeout_client)
    timeout_status, _, timeout_body = _request(failing, "GET", "/api/v1/version")
    assert timeout_status == 502
    assert "ConnectTimeout" in timeout_body.decode()

    too_small = OpenInfraWebAsgiApplication(
        _web_config(max_request_body_bytes=2),
        _pool_settings(),
        client=timeout_client,
    )
    large_status, _, large_body = _request(
        too_small,
        "POST",
        "/api/v1/test",
        body=b"123",
    )
    assert large_status == 400
    assert "exceeds" in large_body.decode()

    disconnected_status, _, disconnected_body = _request(
        too_small,
        "POST",
        "/api/v1/test",
        messages=[{"type": "http.disconnect"}],
    )
    assert disconnected_status == 400
    assert "disconnected" in disconnected_body.decode()

    method_status, _, _ = _request(too_small, "OPTIONS", "/api/v1/test")
    assert method_status == 404

    async def unsupported() -> int:
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return {"type": "websocket.receive"}

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await too_small({"type": "websocket"}, receive, send)
        return sent[0]["status"]

    assert asyncio.run(unsupported()) == 400
    asyncio.run(timeout_client.aclose())


def test_web_asgi_streaming_head_body_factory_and_runtime_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ChunkStream(httpx.AsyncByteStream):
        async def __aiter__(self):  # type: ignore[no-untyped-def]
            yield b"chunk-1"
            yield b"chunk-2"

        async def aclose(self) -> None:
            return None

    seen: list[httpx.Request] = []

    async def backend(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            stream=ChunkStream(),
            headers={"content-type": "application/octet-stream"},
        )

    config = _web_config(database_dsn_ref="env:OPENINFRA_DATABASE_DSN")
    client = httpx.AsyncClient(transport=httpx.MockTransport(backend))
    app = OpenInfraWebAsgiApplication(config, _pool_settings(), client=client)

    head_status, _, head_body = _request(app, "HEAD", "/api/v1/version")
    assert head_status == 200
    assert head_body == b""

    stream_status, _, stream_body = _request(app, "GET", "/api/v1/export")
    assert stream_status == 200
    assert stream_body == b"chunk-1chunk-2"
    assert seen[-1].headers["x-openinfra-web-database-trust"] == "configured"

    post_status, _, post_body = _request(
        app,
        "POST",
        "/api/v1/import",
        messages=[
            {"type": "websocket.receive"},
            {"type": "http.request", "body": b"{}", "more_body": False},
        ],
    )
    assert post_status == 200
    assert post_body == b"chunk-1chunk-2"

    assert app._static_cache_control("/custom", b"") == ("no-cache, max-age=0, must-revalidate")

    monkeypatch.setattr(web_asgi.OpenInfraWebConfigFactory, "from_args", lambda self, args: config)
    factory_app = web_asgi.web_app_factory()
    assert isinstance(factory_app, OpenInfraWebAsgiApplication)
    asyncio.run(client.aclose())

    runtime_config = _web_config(workers=2)
    monkeypatch.setattr(
        "openinfra.interfaces.web.uvicorn.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert OpenInfraWebEntrypoint._run_asgi(runtime_config) == 0
    assert "OPENINFRA_WEB_BACKEND_URL" not in os.environ


def test_runtime_environment_scope_restores_values_after_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENINFRA_EXISTING", "original")
    monkeypatch.delenv("OPENINFRA_TRANSIENT", raising=False)
    assert OpenInfraRuntimeEnvironmentScope({}).__exit__(None, None, None) is False

    with (
        pytest.raises(RuntimeError, match="startup failed"),
        OpenInfraRuntimeEnvironmentScope(
            {"OPENINFRA_EXISTING": "overridden", "OPENINFRA_TRANSIENT": "temporary"}
        ),
    ):
        assert os.environ["OPENINFRA_EXISTING"] == "overridden"
        assert os.environ["OPENINFRA_TRANSIENT"] == "temporary"
        raise RuntimeError("startup failed")

    assert os.environ["OPENINFRA_EXISTING"] == "original"
    assert "OPENINFRA_TRANSIENT" not in os.environ


def test_web_pool_settings_lifespan_and_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    validator = OpenInfraWebConfigValidator()
    for config, message in (
        (_web_config(runtime="invalid"), "RUNTIME"),
        (_web_config(workers=-1), "WORKERS"),
        (_web_config(limit_concurrency=0), "concurrency"),
        (_web_config(timeout_keep_alive=0), "keep-alive"),
    ):
        with pytest.raises(OpenInfraError, match=message):
            validator.validate(config)

    pro = OpenInfraWebHttpPoolSettings.from_environment("pro")
    assert pro.max_connections == 200
    assert OpenInfraWebHttpPoolSettings.from_environment("lite").max_connections == 32
    assert OpenInfraWebHttpPoolSettings.from_environment("enterprise").max_connections == 500
    with pytest.raises(ValidationError, match="edition"):
        OpenInfraWebHttpPoolSettings.from_environment("invalid")
    for values in (
        (0, 1, 1, 1, 1, 1, 1),
        (1, 0, 1, 1, 1, 1, 1),
        (1, 2, 1, 1, 1, 1, 1),
        (1, 1, 0, 1, 1, 1, 1),
        (1, 1, 1, 0, 1, 1, 1),
    ):
        with pytest.raises(ValidationError):
            OpenInfraWebHttpPoolSettings(*values)

    app = OpenInfraWebAsgiApplication(_web_config(), pro)
    assert _lifespan(app) == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]

    config = _web_config(workers=3, limit_concurrency=99, backlog=123, timeout_keep_alive=9)
    assert OpenInfraWebEntrypoint._resolve_workers(config) == 3
    assert OpenInfraWebEntrypoint._resolve_workers(_web_config(edition="lite", workers=0)) == 1
    assert OpenInfraWebEntrypoint._resolve_workers(_web_config(edition="pro", workers=0)) >= 2
    assert (
        OpenInfraWebEntrypoint._resolve_workers(_web_config(edition="enterprise", workers=0)) >= 2
    )

    calls: list[dict[str, Any]] = []
    runtime_snapshots: list[dict[str, str | None]] = []
    monkeypatch.setenv("OPENINFRA_EDITION", "baseline")
    monkeypatch.delenv("OPENINFRA_WEB_BACKEND_URL", raising=False)

    def capture_web_runtime(*_args: object, **kwargs: Any) -> None:
        calls.append(kwargs)
        runtime_snapshots.append(
            {
                "backend_url": os.environ.get("OPENINFRA_WEB_BACKEND_URL"),
                "edition": os.environ.get("OPENINFRA_EDITION"),
                "workers": os.environ.get("OPENINFRA_WEB_WORKERS_RESOLVED"),
            }
        )

    monkeypatch.setattr("openinfra.interfaces.web.uvicorn.run", capture_web_runtime)
    assert OpenInfraWebEntrypoint._run_asgi(config) == 0
    assert calls[0]["workers"] == 3
    assert calls[0]["backlog"] == 123
    assert calls[0]["access_log"] is False
    assert OpenInfraWebEntrypoint._run_asgi(config) == 0
    assert runtime_snapshots == [
        {"backend_url": config.backend_url, "edition": "pro", "workers": "3"},
        {"backend_url": config.backend_url, "edition": "pro", "workers": "3"},
    ]
    assert "OPENINFRA_WEB_BACKEND_URL" not in os.environ
    assert "OPENINFRA_WEB_WORKERS_RESOLVED" not in os.environ
    assert os.environ["OPENINFRA_EDITION"] == "baseline"


def test_api_asgi_read_after_write_consistency_token_routing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "consistency.json")
    observed_routes: list[ReadRoute] = []

    class RoutingHandler:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def dispatch(self) -> tuple[int, tuple[tuple[str, str], ...], bytes]:
            observed_routes.append(ReadRoutingContext.current())
            return 200, (("Content-Type", "application/json"),), b"{}"

    monkeypatch.setattr(api_asgi, "OpenInfraAsgiRequestHandler", RoutingHandler)
    now = [1_000.0]
    codec = ReadConsistencyTokenCodec("c" * 32, ttl_seconds=7, clock=lambda: now[0])
    app = OpenInfraApiAsgiApplication(
        OpenInfraApiRuntime(application), consistency_token_codec=codec
    )

    assert _request(app, "GET", "/api/v1/version")[0] == 200
    post_status, post_headers, _ = _request(app, "POST", "/api/v1/test", body=b"{}")
    token = post_headers["x-openinfra-consistency-token"]
    assert post_status == 200
    assert post_headers["access-control-expose-headers"] == ("X-OpenInfra-Consistency-Token")
    assert codec.validate(token) is True
    assert (
        _request(
            app,
            "GET",
            "/api/v1/version",
            headers=((b"x-openinfra-consistency-token", token.encode()),),
        )[0]
        == 200
    )
    assert observed_routes == [ReadRoute.REPLICA, ReadRoute.PRIMARY, ReadRoute.PRIMARY]

    invalid_status, _, invalid_body = _request(
        app,
        "GET",
        "/api/v1/version",
        headers=((b"x-openinfra-consistency-token", b"invalid"),),
    )
    assert invalid_status == 400
    assert "invalid or expired" in invalid_body.decode()


def test_web_asgi_persists_and_forwards_consistency_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_tokens: list[str] = []

    async def backend(request: httpx.Request) -> httpx.Response:
        received_tokens.append(request.headers.get("x-openinfra-consistency-token", ""))
        headers = {"content-type": "application/json"}
        if request.method == "POST":
            headers["x-openinfra-consistency-token"] = "signed-token"
            headers["access-control-expose-headers"] = "X-OpenInfra-Consistency-Token"
        return httpx.Response(200, content=b"{}", headers=headers)

    client = httpx.AsyncClient(transport=httpx.MockTransport(backend))
    app = OpenInfraWebAsgiApplication(
        _web_config(),
        _pool_settings(),
        client=client,
        consistency_cookie_ttl_seconds=7,
    )
    status, headers, _ = _request(app, "POST", "/api/v1/test", body=b"{}")
    assert status == 200
    assert "openinfra_read_consistency=signed-token" in headers["set-cookie"]
    assert "Max-Age=7" in headers["set-cookie"]
    assert "Secure" not in headers["set-cookie"]
    secure_status, secure_headers, _ = _request(
        app,
        "POST",
        "/api/v1/test",
        body=b"{}",
        headers=((b"x-forwarded-proto", b"https"),),
    )
    assert secure_status == 200
    assert "; Secure" in secure_headers["set-cookie"]
    assert app._consistency_token_from_cookie("\x00") == ""

    class BrokenCookie:
        def load(self, raw_cookie: str) -> None:
            raise ValueError(raw_cookie)

    original_cookie = web_asgi.SimpleCookie
    monkeypatch.setattr(web_asgi, "SimpleCookie", BrokenCookie)
    assert app._consistency_token_from_cookie("malformed") == ""
    monkeypatch.setattr(web_asgi, "SimpleCookie", original_cookie)

    get_status, _, _ = _request(
        app,
        "GET",
        "/api/v1/version",
        headers=((b"cookie", b"openinfra_read_consistency=signed-token"),),
    )
    assert get_status == 200
    assert received_tokens == ["", "", "signed-token"]
    asyncio.run(client.aclose())

    with pytest.raises(ValidationError, match="cookie TTL"):
        OpenInfraWebAsgiApplication(
            _web_config(), _pool_settings(), consistency_cookie_ttl_seconds=0
        )


def test_api_asgi_read_scope_and_read_replica_factories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "read-scope.json")
    scope_events: list[str] = []

    class ReadScope:
        def __enter__(self) -> None:
            scope_events.append("enter")

        def __exit__(self, *args: object) -> None:
            del args
            scope_events.append("exit")

    application.store.read_scope = ReadScope  # type: ignore[attr-defined]
    assert (
        _request(
            OpenInfraApiAsgiApplication(OpenInfraApiRuntime(application)),
            "GET",
            "/health",
        )[0]
        == 200
    )
    assert scope_events == ["enter", "exit"]

    captured: dict[str, object] = {}

    def create_postgresql(_self: object, dsn: str, **kwargs: object) -> object:
        captured.update(dsn=dsn, **kwargs)
        return application

    monkeypatch.setenv("OPENINFRA_API_BACKEND", "postgresql")
    monkeypatch.setenv("OPENINFRA_EDITION", "pro")
    monkeypatch.setenv("OPENINFRA_API_WORKERS_RESOLVED", "2")
    monkeypatch.setenv("OPENINFRA_DB_READ_ROUTING_ENABLED", "true")
    monkeypatch.setattr(
        api_asgi.RuntimeDatabaseDsnResolver,
        "resolve",
        lambda self, value: "postgresql:///primary",
    )
    monkeypatch.setattr(
        api_asgi.RuntimeDatabaseDsnResolver,
        "resolve_read_replica",
        lambda self, value=None: "postgresql:///replica",
    )
    monkeypatch.setattr(
        api_asgi.PostgreSQLConnectionPoolSettings,
        "from_environment",
        lambda edition, workers: (edition, workers),
    )
    monkeypatch.setattr(
        api_asgi.ApplicationFactory, "create_postgresql_application", create_postgresql
    )
    assert api_asgi.OpenInfraApiEnvironmentApplicationFactory().create() is application
    assert captured["read_dsn"] == "postgresql:///replica"
    assert captured["read_pool_settings"] == ("pro", 2)
    assert captured["read_routing_settings"].enabled is True  # type: ignore[union-attr]


def test_api_asgi_factory_requires_and_accepts_consistency_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = ApplicationFactory().create_json_application(tmp_path / "factory-key.json")
    monkeypatch.setattr(
        api_asgi.OpenInfraApiEnvironmentApplicationFactory,
        "create",
        lambda self: application,
    )
    monkeypatch.setattr(
        api_asgi.RuntimeDatabaseDsnResolver,
        "resolve_read_replica",
        lambda self, value=None: "postgresql:///replica",
    )
    monkeypatch.setattr(
        api_asgi.RuntimeDatabaseDsnResolver,
        "resolve_consistency_secret",
        lambda self: "",
    )
    with pytest.raises(OpenInfraError, match="CONSISTENCY_SECRET"):
        api_asgi.OpenInfraApiAsgiFactory()()

    monkeypatch.setattr(
        api_asgi.RuntimeDatabaseDsnResolver,
        "resolve_consistency_secret",
        lambda self: "k" * 32,
    )
    monkeypatch.setenv("OPENINFRA_READ_AFTER_WRITE_TTL_SECONDS", "9")
    app = api_asgi.OpenInfraApiAsgiFactory()()
    assert app._consistency_token_codec is not None
    assert app._consistency_token_codec.ttl_seconds == 9
