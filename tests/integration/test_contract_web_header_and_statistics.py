from __future__ import annotations

import json
import threading
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from openinfra.interfaces.web import OpenInfraWebConfig, OpenInfraWebServer, OpenInfraWebStaticLocator


_REACT_MAIN = Path("web/src/main.jsx")
_RUNTIME_MAIN = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-web.js")
_RUNTIME_CSS = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-web.css")
_RUNTIME_I18N = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js")


class _ReadyBackendHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        if self.path == "/ready":
            payload = json.dumps({"ready": True, "service": "web-contract-backend"}).encode()
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


def _runtime_surfaces() -> tuple[str, str, str, str]:
    with _RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), _ReadyBackendHandler)) as backend:
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
            runtime="legacy",
        )
        with _RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
            return (
                _get_text(web.base_url + "/"),
                _get_text(web.base_url + "/assets/openinfra-web.js"),
                _get_text(web.base_url + "/assets/openinfra-web.css"),
                _get_text(web.base_url + "/assets/openinfra-i18n.js"),
            )


def test_tst_web_051_reintegrated_double_header_toolbar_is_preserved() -> None:
    index, runtime_js, runtime_css, runtime_i18n = _runtime_surfaces()
    react_main = _REACT_MAIN.read_text(encoding="utf-8")

    for source in (runtime_js, react_main):
        assert source.count("openinfra-header-stack") >= 1
        assert "openinfra-top-header" in source
        assert "openinfra-global-toolbar" in source
        assert "openinfra-global-search" in source
        assert "openinfra-global-search-icon" in source
        assert "openinfra-api-doc-actions" in source
        assert "Swagger" in source
        assert "ReDoc" in source
        assert "Login" not in source
        assert "Sign-up" not in source

    header_start = runtime_js.index('<header class="openinfra-header-stack" role="banner">')
    assert runtime_js.count('<header class="openinfra-header-stack" role="banner">') == 1
    assert runtime_js.index("openinfra-top-header", header_start) < runtime_js.index(
        "this.renderGlobalSearchToolbar()", header_start
    )
    assert "grid-template-columns: minmax(0, 1fr) minmax(18rem, 50%) minmax(0, 1fr)" in runtime_css
    assert "Recherche globale OpenInfra" in runtime_i18n
    assert 'href="/assets/openinfra-web.css' in index


def test_tst_web_052_dashboard_exposes_component_metrics_and_pie_charts() -> None:
    _, runtime_js, runtime_css, runtime_i18n = _runtime_surfaces()
    react_main = _REACT_MAIN.read_text(encoding="utf-8")
    packaged_runtime_js = _RUNTIME_MAIN.read_text(encoding="utf-8")
    packaged_runtime_css = _RUNTIME_CSS.read_text(encoding="utf-8")
    packaged_runtime_i18n = _RUNTIME_I18N.read_text(encoding="utf-8")

    assert runtime_js == packaged_runtime_js
    assert runtime_css == packaged_runtime_css
    assert runtime_i18n == packaged_runtime_i18n

    for source in (runtime_js, react_main):
        assert "openinfra-component-card" in source
        assert "openinfra-pie-chart" in source
        assert "componentStatistics" in source
        assert "readOperations" in source
        assert "writeOperations" in source
        assert "operations" in source
        assert "fields" in source

    assert '${components.map((module) => this.renderComponentStatsCard(module)).join("")}' in runtime_js
    assert "modules.map((module) => <ComponentStatsCard" in react_main
    assert 'role="img"' in runtime_js
    assert "distributionChart" in runtime_js
    assert "conic-gradient" in runtime_css
    assert "--openinfra-pie-size: clamp(8rem, 14vw, 10.5rem)" in runtime_css
    assert "Statistiques des composants OpenInfra" in runtime_i18n
    assert "Accueil — statistiques des composants" in runtime_i18n
