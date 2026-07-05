from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from openinfra import __version__
from openinfra.domain.common import OpenInfraError
from openinfra.interfaces.web import (
    OpenInfraWebConfig,
    OpenInfraWebConfigValidator,
    OpenInfraWebServer,
    OpenInfraWebStaticLocator,
)


class BackendFakeHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        if self.path == "/ready":
            self._json(HTTPStatus.OK, {"ready": True, "backend": "fake"})
            return
        if self.path == "/v1/version":
            self._json(HTTPStatus.OK, {"version": __version__})
            return
        if self.path == "/openapi.yaml":
            body = b"openapi: 3.1.0\ninfo:\n  title: OpenInfra\n"
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/yaml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": self.path})

    def do_POST(self) -> None:
        if self.path == "/v1/echo":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self._json(
                HTTPStatus.CREATED,
                {
                    "received": payload,
                    "browser_authorization_forwarded": "Authorization" in self.headers,
                    "web_trust": self.headers.get("X-OpenInfra-Web-Trust"),
                },
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": self.path})

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class RunningServer:
    def __init__(self, server: ThreadingHTTPServer) -> None:
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self) -> RunningServer:
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class TestOpenInfraWeb:
    def test_web_serves_assets_config_readiness_and_api_proxy(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url)
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                index = self._get_text(web.base_url + "/")
                bootstrap_css = self._get_text(web.base_url + "/assets/bootstrap.min.css")
                static_css = self._get_text(web.base_url + "/assets/openinfra-web.css")
                static_js = self._get_text(web.base_url + "/assets/openinfra-web.js")
                public_config = self._get_json(web.base_url + "/config.json")
                readiness = self._get_json(web.base_url + "/ready")
                version = self._get_json(web.base_url + "/api/v1/version")
                web_version = self._get_json(web.base_url + "/version")
                openapi = self._get_text(web.base_url + "/openapi.yaml")
                echoed = self._post_json(
                    web.base_url + "/api/v1/echo",
                    {"tenant_id": "default", "value": 42},
                    auth_token="oi_" + "test",
                )

        assert "openinfra-root" in index
        assert "/assets/bootstrap.min.css" in index
        assert "Bootstrap" in bootstrap_css and "v5." in bootstrap_css
        assert "openinfra-sidebar" in static_css
        assert "OpenInfraDashboard" in static_js
        assert "Dashboard de pilotage OpenInfra" in static_js
        assert "Search OpenInfra operations" in static_js
        assert "Login" in static_js and "Sign-up" in static_js
        assert "Ressources Inventory" in static_js
        assert "/v1/ri/objects" in static_js
        assert "openinfra-accordion" in static_js + static_css
        assert "Numéro de série" in static_js
        assert "Token API" not in static_js
        assert "openinfra-method" not in static_js + static_css
        assert "agents proxy collectors Enterprise uniquement" in static_js
        assert "postgresql://" not in index + static_js + static_css
        assert "OPENINFRA_DATABASE_DSN" not in index + static_js + static_css
        assert public_config == {
            "apiBaseUrl": "/api",
            "authMode": "standard",
            "backendProxy": "/api",
            "databaseTrust": "not-configured",
            "edition": "pro",
            "service": "openinfra-web",
            "version": __version__,
            "webBackendTrust": "server-side",
        }
        assert readiness["ready"] is True
        assert version["version"] == __version__
        assert web_version["version"] == __version__
        assert "openapi: 3.1.0" in openapi
        assert echoed == {
            "browser_authorization_forwarded": False,
            "received": {"tenant_id": "default", "value": 42},
            "web_trust": "server-side",
        }

    def test_web_rejects_path_traversal_and_invalid_backend_configuration(self) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        with (
            RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend,
            RunningServer(
                OpenInfraWebServer(("127.0.0.1", 0), self._config(backend.base_url))
            ) as web,
            pytest.raises(urllib.error.HTTPError) as exc,
        ):
            self._get_json(web.base_url + "/../pyproject.toml")

        assert exc.value.code == HTTPStatus.NOT_FOUND.value
        with pytest.raises(OpenInfraError):
            OpenInfraWebConfigValidator().validate(
                OpenInfraWebConfig(
                    host="127.0.0.1",
                    port=2006,
                    backend_url="http://user:pass@example.net",
                    public_api_base_url="/api",
                    static_root=static_root,
                    edition="pro",
                    auth_mode="standard",
                    allow_insecure_backend=True,
                )
            )
        with pytest.raises(OpenInfraError):
            OpenInfraWebConfigValidator().validate(
                OpenInfraWebConfig(
                    host="127.0.0.1",
                    port=2006,
                    backend_url="http://backend.internal",
                    public_api_base_url="/api",
                    static_root=static_root,
                    edition="enterprise",
                    auth_mode="standard",
                    allow_insecure_backend=False,
                )
            )

    def test_entrypoint_returns_success_and_keyboard_interrupt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        parsed = __import__("openinfra.interfaces.web", fromlist=["OpenInfraWebEntrypoint"])
        config = self._config("http://127.0.0.1:8080")

        class ReturningServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                self.started = True

        class InterruptingServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                raise KeyboardInterrupt

        monkeypatch.setattr(
            parsed.OpenInfraWebConfigFactory, "from_args", lambda self, argv: config
        )
        monkeypatch.setattr(parsed, "OpenInfraWebServer", ReturningServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0
        monkeypatch.setattr(parsed, "OpenInfraWebServer", InterruptingServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0

    def _get_json(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _config(self, backend_url: str) -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url=backend_url,
            public_api_base_url="/api",
            static_root=OpenInfraWebStaticLocator().resolve(None),
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
        )

    def _get_text(self, url: str) -> str:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8")

    def _post_json(
        self, url: str, payload: dict[str, object], auth_token: str
    ) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + auth_token},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


class TestOpenInfraWebEdges:
    def test_config_factory_and_validator_negative_branches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        config = OpenInfraWebConfigValidator()
        parsed = __import__("openinfra.interfaces.web", fromlist=["OpenInfraWebConfigFactory"])
        factory = parsed.OpenInfraWebConfigFactory()
        built = factory.from_args(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "2007",
                "--backend-url",
                "https://backend.example.net",
                "--public-api-base-url",
                "/api",
                "--static-root",
                str(static_root),
                "--edition",
                "enterprise",
                "--auth-mode",
                "ipa",
            ]
        )

        assert built.port == 2007
        assert built.static_root == static_root
        invalid_configs = [
            self._raw_config("ftp://backend.example.net", static_root),
            self._raw_config("https://backend.example.net/path", static_root),
            self._raw_config("https://backend.example.net", static_root, edition="unknown"),
            self._raw_config("https://backend.example.net", static_root, auth_mode="oauth"),
            self._raw_config(
                "https://backend.example.net", static_root, edition="lite", auth_mode="ldap"
            ),
            self._raw_config("https://backend.example.net", static_root, max_request_body_bytes=0),
            self._raw_config(
                "https://backend.example.net",
                static_root,
                database_dsn_ref="postgresql://cleartext/openinfra",
            ),
        ]
        for invalid in invalid_configs:
            with pytest.raises(OpenInfraError):
                config.validate(invalid)
        monkeypatch.setattr(parsed.sys, "argv", ["openinfra-web", "--backend-url", "ftp://bad"])
        assert parsed.OpenInfraWebEntrypoint.main() == 2

    def test_proxy_error_branches_head_and_non_api_routes(self) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            small_config = OpenInfraWebConfig(
                host="127.0.0.1",
                port=0,
                backend_url=backend.base_url,
                public_api_base_url="/api",
                static_root=static_root,
                edition="pro",
                auth_mode="standard",
                allow_insecure_backend=True,
                max_request_body_bytes=4,
            )
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), small_config)) as web:
                head_request = urllib.request.Request(web.base_url + "/", method="HEAD")
                with urllib.request.urlopen(head_request, timeout=5) as head_response:
                    assert head_response.status == HTTPStatus.OK.value
                    assert head_response.read() == b""
                health = self._get_json(web.base_url + "/health")
                with pytest.raises(urllib.error.HTTPError) as missing:
                    self._get_json(web.base_url + "/api/v1/missing?tenant_id=default")
                with pytest.raises(urllib.error.HTTPError) as non_api:
                    delete = urllib.request.Request(web.base_url + "/not-api", method="DELETE")
                    urllib.request.urlopen(delete, timeout=5)
                with pytest.raises(urllib.error.HTTPError) as too_large:
                    request = urllib.request.Request(
                        web.base_url + "/api/v1/echo",
                        data=b"12345",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(request, timeout=5)
                with pytest.raises(urllib.error.HTTPError) as put_non_api:
                    put = urllib.request.Request(
                        web.base_url + "/not-api", data=b"{}", method="PUT"
                    )
                    urllib.request.urlopen(put, timeout=5)
                with pytest.raises(urllib.error.HTTPError) as patch_non_api:
                    patch = urllib.request.Request(
                        web.base_url + "/not-api", data=b"{}", method="PATCH"
                    )
                    urllib.request.urlopen(patch, timeout=5)

        assert health["status"] == "ok"
        assert missing.value.code == HTTPStatus.NOT_FOUND.value
        assert non_api.value.code == HTTPStatus.NOT_FOUND.value
        assert put_non_api.value.code == HTTPStatus.NOT_FOUND.value
        assert patch_non_api.value.code == HTTPStatus.NOT_FOUND.value
        assert too_large.value.code == HTTPStatus.BAD_REQUEST.value

    def test_backend_unavailable_and_invalid_content_length(self) -> None:
        import http.client

        static_root = OpenInfraWebStaticLocator().resolve(None)
        unavailable = OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url="http://127.0.0.1:9",
            public_api_base_url="/api",
            static_root=static_root,
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
        )
        with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), unavailable)) as web:
            with pytest.raises(urllib.error.HTTPError) as ready:
                self._get_json(web.base_url + "/ready")
            with pytest.raises(urllib.error.HTTPError) as api:
                self._get_json(web.base_url + "/api/v1/version")

        assert ready.value.code == HTTPStatus.SERVICE_UNAVAILABLE.value
        assert api.value.code == HTTPStatus.BAD_GATEWAY.value
        with (
            RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend,
            RunningServer(
                OpenInfraWebServer(("127.0.0.1", 0), self._config(backend.base_url))
            ) as web,
        ):
            connection = http.client.HTTPConnection("127.0.0.1", web.server.server_port, timeout=5)
            connection.putrequest("POST", "/api/v1/echo")
            connection.putheader("Content-Length", "invalid")
            connection.endheaders()
            response = connection.getresponse()
            payload = response.read().decode("utf-8")
            connection.close()

        assert response.status == HTTPStatus.BAD_REQUEST.value
        assert "invalid Content-Length" in payload

    def test_entrypoint_returns_success_and_keyboard_interrupt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        parsed = __import__("openinfra.interfaces.web", fromlist=["OpenInfraWebEntrypoint"])
        config = self._config("http://127.0.0.1:8080")

        class ReturningServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                self.started = True

        class InterruptingServer:
            def __init__(self, _address: object, _config: object) -> None:
                self.started = False

            def serve_forever(self) -> None:
                raise KeyboardInterrupt

        monkeypatch.setattr(
            parsed.OpenInfraWebConfigFactory, "from_args", lambda self, argv: config
        )
        monkeypatch.setattr(parsed, "OpenInfraWebServer", ReturningServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0
        monkeypatch.setattr(parsed, "OpenInfraWebServer", InterruptingServer)
        assert parsed.OpenInfraWebEntrypoint.main() == 0

    def _get_json(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _config(self, backend_url: str) -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url=backend_url,
            public_api_base_url="/api",
            static_root=OpenInfraWebStaticLocator().resolve(None),
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
        )

    def _raw_config(
        self,
        backend_url: str,
        static_root: Path,
        edition: str = "pro",
        auth_mode: str = "standard",
        max_request_body_bytes: int = 1_048_576,
        database_dsn_ref: str = "",
    ) -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=2006,
            backend_url=backend_url,
            public_api_base_url="/api",
            static_root=static_root,
            edition=edition,
            auth_mode=auth_mode,
            allow_insecure_backend=False,
            max_request_body_bytes=max_request_body_bytes,
            database_dsn_ref=database_dsn_ref,
        )
