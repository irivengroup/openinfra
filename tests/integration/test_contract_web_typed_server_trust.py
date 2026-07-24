from __future__ import annotations

import json
import threading
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from openinfra import __version__
from openinfra.interfaces.web import OpenInfraWebConfig, OpenInfraWebServer, OpenInfraWebStaticLocator


_REACT_MAIN = Path("web/src/main.jsx")
_REACT_DATA = Path("web/src/domains/data.js")
_RUNTIME_MAIN = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-web.js")
_RUNTIME_DATA = Path("src/openinfra/interfaces/rendering/static/assets/domains/data.js")


class _TrustBackendHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        if self.path == "/ready":
            self._json(HTTPStatus.OK, {"ready": True, "service": "tst-web-050-backend"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": self.path})

    def do_POST(self) -> None:
        if self.path != "/api/v1/echo":
            self._json(HTTPStatus.NOT_FOUND, {"error": self.path})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self._json(
            HTTPStatus.CREATED,
            {
                "received": payload,
                "authorization": self.headers.get("Authorization", ""),
                "web_trust": self.headers.get("X-OpenInfra-Web-Trust", ""),
            },
        )

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _RunningServer:
    def __init__(self, server: ThreadingHTTPServer) -> None:
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self) -> _RunningServer:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310  # nosec B310
        assert response.status == HTTPStatus.OK
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, object], browser_token: str) -> dict[str, object]:
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": "Bearer " + browser_token,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310  # nosec B310
        assert response.status == HTTPStatus.CREATED
        return json.loads(response.read().decode("utf-8"))


def test_tst_web_050_typed_forms_use_server_side_trust_without_browser_authorization() -> None:
    server_token = "tst-web-050-server-side-bearer"
    browser_token = "tst-web-050-browser-supplied-bearer"

    with _RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), _TrustBackendHandler)) as backend:
        config = OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url=backend.base_url,
            public_api_base_url="/api",
            public_api_docs_base_url="",
            static_root=OpenInfraWebStaticLocator().resolve(),
            edition="enterprise",
            auth_mode="standard",
            allow_insecure_backend=True,
            backend_bearer_token=server_token,
            runtime="legacy",
        )
        with _RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
            public_config = _get_json(web.base_url + "/config.json")
            bootstrap = _get_json(web.base_url + "/bootstrap.json")
            version = _get_json(web.base_url + "/version")
            echoed = _post_json(
                web.base_url + "/api/v1/echo",
                {"tenant_id": "default", "asset_key": "device/tst-web-050"},
                browser_token,
            )

    react_main = _REACT_MAIN.read_text(encoding="utf-8")
    runtime_main = _RUNTIME_MAIN.read_text(encoding="utf-8")
    react_data = _REACT_DATA.read_text(encoding="utf-8")
    runtime_data = _RUNTIME_DATA.read_text(encoding="utf-8")
    portal_sources = "\n".join((react_main, runtime_main, react_data, runtime_data))

    for forbidden in (
        "Token API",
        "Jeton administrateur",
        "admin_token",
        '"authField"',
        "headers.Authorization",
        "headers[\"Authorization\"]",
    ):
        assert forbidden not in portal_sources

    assert "<small>{operation.method} {operation.path}</small>" not in react_main
    assert "${this.escape(operation.method)} ${this.escape(operation.path)}" not in runtime_main

    for explicit_business_input in (
        "source_file",
        "actor",
        "format",
        "mapping_json",
        "idempotency_key",
        "batch_size",
        "checkpoint_interval",
        "job_id",
    ):
        assert explicit_business_input in react_data
        assert explicit_business_input in runtime_data

    assert public_config["version"] == __version__
    assert public_config["webBackendTrust"] == "server-side"
    assert public_config["backendProxy"] == "/api"
    assert bootstrap["version"] == {"service": "openinfra-web", "version": __version__}
    assert version == {"service": "openinfra-web", "version": __version__}

    assert echoed["received"] == {
        "asset_key": "device/tst-web-050",
        "tenant_id": "default",
    }
    assert echoed["authorization"] == "Bearer " + server_token
    assert echoed["authorization"] != "Bearer " + browser_token
    assert echoed["web_trust"] == "server-side"
