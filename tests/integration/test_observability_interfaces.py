from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.infrastructure.observability import OpenInfraTelemetry
from openinfra.interfaces.asgi import OpenInfraApiAsgiApplication
from openinfra.interfaces.asgi_web import OpenInfraWebAsgiApplication, OpenInfraWebHttpPoolSettings
from openinfra.interfaces.http_api import OpenInfraApiRuntime
from openinfra.interfaces.web import OpenInfraWebConfig, OpenInfraWebStaticLocator


def _request(
    app: Any,
    method: str,
    path: str,
    *,
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
    async def run() -> tuple[int, dict[str, str], bytes]:
        messages = [{"type": "http.request", "body": body, "more_body": False}]
        sent: list[dict[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return (
                messages.pop(0)
                if messages
                else {
                    "type": "http.request",
                    "body": b"",
                    "more_body": False,
                }
            )

        async def send(message: dict[str, Any]) -> None:
            sent.append(message)

        await app(
            {
                "type": "http",
                "http_version": "1.1",
                "method": method,
                "path": path,
                "query_string": b"",
                "headers": [],
                "scheme": "http",
                "server": ("127.0.0.1", 8080),
                "client": ("127.0.0.1", 12345),
            },
            receive,
            send,
        )
        start = next(item for item in sent if item["type"] == "http.response.start")
        headers = {
            bytes(name).decode("latin-1"): bytes(value).decode("latin-1")
            for name, value in start.get("headers", [])
        }
        payload = b"".join(
            bytes(item.get("body", b"")) for item in sent if item["type"] == "http.response.body"
        )
        return int(start["status"]), headers, payload

    return asyncio.run(run())


def _web_config() -> OpenInfraWebConfig:
    return OpenInfraWebConfig(
        host="127.0.0.1",
        port=2006,
        backend_url="http://backend",
        public_api_base_url="/api",
        public_api_docs_base_url="",
        static_root=OpenInfraWebStaticLocator().resolve(None),
        edition="enterprise",
        auth_mode="standard",
        allow_insecure_backend=True,
        backend_bearer_token="t" * 40,
    )


def test_api_prometheus_endpoint_and_trace_response_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    monkeypatch.setenv("OPENINFRA_OTEL_TRACE_SAMPLE_RATIO", "1")
    application = ApplicationFactory().create_json_application(tmp_path / "state.json")
    app = OpenInfraApiAsgiApplication(OpenInfraApiRuntime(application))

    status, headers, _ = _request(app, "GET", "/health")
    assert status == 200
    assert headers["traceparent"].startswith("00-")

    metrics_status, metrics_headers, metrics = _request(app, "GET", "/metrics")
    assert metrics_status == 200
    assert metrics_headers["cache-control"] == "no-store"
    text = metrics.decode("utf-8")
    assert "openinfra_http_requests_total" in text
    assert 'route="/health"' in text
    assert "openinfra_async_queue_depth" in text

    head_status, _, head_body = _request(app, "HEAD", "/metrics")
    assert head_status == 200
    assert head_body == b""


def test_web_metrics_and_bff_trace_propagation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    monkeypatch.setenv("OPENINFRA_OTEL_TRACE_SAMPLE_RATIO", "1")
    captured: list[str] = []

    async def backend(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers.get("traceparent", ""))
        return httpx.Response(200, json={"status": "ok"})

    telemetry = OpenInfraTelemetry(
        service_name="openinfra-web",
        edition="enterprise",
        environment="test",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(backend))
    app = OpenInfraWebAsgiApplication(
        _web_config(),
        OpenInfraWebHttpPoolSettings(20, 10, 30, 2, 30, 30, 2),
        client,
        telemetry=telemetry,
    )

    status, headers, _ = _request(app, "GET", "/api/v1/version")
    assert status == 200
    assert headers["traceparent"].startswith("00-")
    assert captured and captured[0].startswith("00-")

    metrics_status, _, metrics = _request(app, "GET", "/metrics")
    assert metrics_status == 200
    assert 'service="openinfra-web"' in metrics.decode("utf-8")
    asyncio.run(client.aclose())
