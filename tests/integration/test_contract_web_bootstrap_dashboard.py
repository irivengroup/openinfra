from __future__ import annotations

import json
import threading
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from openinfra import __version__
from openinfra.interfaces.web import OpenInfraWebConfig, OpenInfraWebServer, OpenInfraWebStaticLocator


_RUNTIME_ASSETS = Path("src/openinfra/interfaces/rendering/static/assets")
_DOMAIN_MANIFEST = _RUNTIME_ASSETS / "openinfra-domain-manifest.js"
_EXPECTED_DOMAINS = (
    ("overview", "Dashboard"),
    ("rsot", "RSOT (Ressource Source of Truth)"),
    ("ipam", "IPAM"),
    ("dcim", "DCIM"),
    ("itam", "IT Asset Management"),
    ("discovery", "Discovery"),
    ("data", "Imports / Exports"),
    ("integrations", "Intégrations externes"),
    ("security", "Sécurité / RBAC / Audit"),
)


class _BackendHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        if self.path == "/ready":
            payload = json.dumps({"ready": True, "service": "contract-backend"}).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Length", "0")
        self.end_headers()


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


def _get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310  # nosec B310
        assert response.status == HTTPStatus.OK
        return response.read().decode("utf-8")


def _get_json(url: str) -> dict[str, object]:
    return json.loads(_get_text(url))


def test_tst_web_049_dashboard_is_local_unique_domain_complete_and_secret_free() -> None:
    bearer_secret = "tst-web-049-backend-bearer-secret"
    dsn_secret = "postgresql://tst-web-049-dsn-secret/openinfra"
    password_secret = "tst-web-049-database-password-secret"

    with _RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)) as backend:
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
            database_dsn_ref=dsn_secret,
            database_user_ref="openinfra-runtime-user",
            database_password_ref=password_secret,
            backend_bearer_token=bearer_secret,
            runtime="legacy",
        )
        with _RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
            index = _get_text(web.base_url + "/")
            bootstrap_css = _get_text(web.base_url + "/assets/bootstrap.min.css")
            runtime_css = _get_text(web.base_url + "/assets/openinfra-web.css")
            runtime_js = _get_text(web.base_url + "/assets/openinfra-web.js")
            public_config = _get_json(web.base_url + "/config.json")
            status = _get_json(web.base_url + "/status")
            bootstrap = _get_json(web.base_url + "/bootstrap.json")

    assert f'href="/assets/bootstrap.min.css?v={__version__}"' in index
    assert "cdn.jsdelivr.net" not in index
    assert "cdnjs.cloudflare.com" not in index
    assert "Bootstrap  v5." in bootstrap_css

    assert runtime_js.count('<header class="openinfra-header-stack" role="banner">') == 1
    assert "openinfra-top-header" in runtime_js
    assert 'id="openinfra-sidebar"' in runtime_js
    assert "openinfra-sidebar-dashboard" in runtime_js
    assert ".openinfra-sidebar" in runtime_css

    manifest = _DOMAIN_MANIFEST.read_text(encoding="utf-8")
    for domain_id, label in _EXPECTED_DOMAINS:
        assert f'"id": "{domain_id}"' in manifest
        assert f'"label": "{label}"' in manifest

    assert 'id="openinfra-component-${this.escape(module.id)}"' in runtime_js

    browser_surfaces = "\n".join(
        (
            index,
            bootstrap_css,
            runtime_css,
            runtime_js,
            json.dumps(public_config, sort_keys=True),
            json.dumps(status, sort_keys=True),
            json.dumps(bootstrap, sort_keys=True),
        )
    )
    for secret in (bearer_secret, dsn_secret, password_secret):
        assert secret not in browser_surfaces

    assert public_config["databaseTrust"] == "server-side"
    assert public_config["webBackendTrust"] == "server-side"
    assert status["trust"] == {
        "backendBearer": "configured",
        "database": "server-side",
        "webBackend": "server-side",
    }
    assert bootstrap["config"] == public_config
    assert bootstrap["status"] == status
