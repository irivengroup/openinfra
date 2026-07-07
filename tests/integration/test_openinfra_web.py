from __future__ import annotations

import json
import re
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


def _test_server_side_bearer() -> str:
    return "-".join(("server", "side", "secret"))


def _test_browser_bearer() -> str:
    return "-".join(("browser", "token"))


class BackendFakeHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return None

    def do_GET(self) -> None:
        if self.path == "/ready":
            self._json(HTTPStatus.OK, {"ready": True, "backend": "fake"})
            return
        if self.path == "/api/v1/version":
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
        if self.path == "/api/v1/echo":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self._json(
                HTTPStatus.CREATED,
                {
                    "received": payload,
                    "authorization": self.headers.get("Authorization", ""),
                    "browser_authorization_forwarded": self.headers.get("Authorization")
                    == "Bearer browser-token",
                    "web_trust": self.headers.get("X-OpenInfra-Web-Trust"),
                },
            )
            return
        if self.path == "/api/v1/raw-missing-bearer":
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "missing bearer token"})
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
            config = self._config(backend.base_url, backend_bearer_token=_test_server_side_bearer())
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                index = self._get_text(web.base_url + "/")
                bootstrap_css = self._get_text(web.base_url + "/assets/bootstrap.min.css")
                static_css = self._get_text(web.base_url + "/assets/openinfra-web.css")
                static_js = self._get_text(web.base_url + "/assets/openinfra-web.js")
                public_config = self._get_json(web.base_url + "/config.json")
                bff_status = self._get_json(web.base_url + "/status")
                readiness = self._get_json(web.base_url + "/ready")
                version = self._get_json(web.base_url + "/api/v1/version")
                web_version = self._get_json(web.base_url + "/version")
                openapi = self._get_text(web.base_url + "/openapi.yaml")
                echoed = self._post_json(
                    web.base_url + "/api/v1/echo",
                    {"tenant_id": "default", "value": 42},
                    browser_bearer=_test_browser_bearer(),
                )

        assert "openinfra-root" in index
        assert "/assets/bootstrap.min.css" in index
        assert "Bootstrap" in bootstrap_css and "v5." in bootstrap_css
        assert "openinfra-sidebar" in static_css
        assert "OpenInfraDashboard" in static_js
        assert "Dashboard de pilotage OpenInfra" in static_js
        assert "Search OpenInfra operations" not in static_js
        assert "openinfra-login" not in static_js and "openinfra-signup" not in static_js
        assert "Login" not in static_js and "Sign-up" not in static_js
        assert "IT Ressources Management" in static_js
        assert "/v1/itrm/objects" in static_js
        assert "Backend prêt" not in static_js
        assert "Soumission exécutée avec succès" in static_js
        assert "openinfra-accordion" in static_js + static_css
        assert "Statistiques des composants OpenInfra" in static_js
        assert "Accueil — statistiques des composants" in static_js
        assert "openinfra-component-card" in static_js + static_css
        assert "openinfra-pie-chart" in static_js + static_css
        assert "padding-block: clamp(1rem, 2vw, 1.75rem)" in static_css
        assert "openinfra-titlebar h1" in static_css
        assert "--openinfra-pie-size: clamp(8rem, 14vw, 10.5rem)" in static_css
        assert "Formulaires protégés" in static_js
        assert 'fetch("/status"' in static_js
        assert "@media (max-width: 575.98px)" in static_css
        assert "Camembert" in static_js
        assert 'path: "/v1/ipam/ui-search"' in static_js
        assert "idempotency_key" in static_js
        assert "endpoint_url" in static_js
        assert "requested_scope" in static_js
        assert 'path: "/api/v1/database/schema"' not in static_js
        assert "Numéro de série" in static_js
        assert 'path: "/v1/itrm/reconcile-object"' in static_js
        assert "Réconcilier une ressource" in static_js
        assert "Catalogue catégories / types" in static_js
        assert "RESOURCE_TAXONOMY" in static_js
        assert "physical-server" not in static_js
        assert "Rack server" in static_js and "Firewall" in static_js
        assert '"value": "rack-server"' in static_js
        assert '"label": "Rack server"' in static_js
        assert "optionLabel(option)" in static_js
        assert "optionValue(option)" in static_js
        assert "data-options-by-field" in static_js
        assert "resource_type" in static_js
        assert "Token API" not in static_js
        assert "openinfra-method" not in static_js + static_css
        assert "agents proxy collectors Enterprise uniquement" in static_js
        assert 'path: "/v1/dcim/locations"' in static_js
        assert "Localiser un équipement" in static_js
        assert 'path: "/v1/dcim/rack-elevation"' in static_js
        assert "Élévation rack" in static_js
        assert "Format rendu" in static_js
        assert "Face rack" in static_js
        assert "Position U" in static_js
        assert 'path: "/v1/dcim/patch-panels"' in static_js
        assert "Définir un panneau de brassage" in static_js
        assert 'path: "/v1/dcim/ports"' in static_js
        assert "Définir un port DCIM" in static_js
        assert 'path: "/v1/dcim/cables"' in static_js
        assert "Connecter un câble" in static_js
        assert "Chemin câble" in static_js
        assert "Média câble" in static_js
        assert 'path: "/v1/dcim/power-devices"' in static_js
        assert "Définir un équipement électrique" in static_js
        assert 'path: "/v1/dcim/power-circuits"' in static_js
        assert "Définir un circuit électrique" in static_js
        assert 'path: "/v1/dcim/cooling-zones"' in static_js
        assert "Définir une zone de refroidissement" in static_js
        assert 'path: "/v1/dcim/power-reservations"' in static_js
        assert "Réserver la puissance équipement" in static_js
        assert 'path: "/v1/dcim/energy-cooling-capacity"' in static_js
        assert "Capacité énergie/refroidissement" in static_js
        assert "Chaîne électrique" in static_js
        assert "Capacité froid watts" in static_js
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
        assert bff_status["protectedForms"] == "enabled"
        assert bff_status["trust"]["backendBearer"] == "configured"
        assert "server-side-secret" not in json.dumps(bff_status, sort_keys=True)
        assert version["version"] == __version__
        assert web_version["version"] == __version__
        assert "openapi: 3.1.0" in openapi
        assert echoed == {
            "authorization": "Bearer server-side-secret",
            "browser_authorization_forwarded": False,
            "received": {"tenant_id": "default", "value": 42},
            "web_trust": "server-side",
        }

    def test_dashboard_form_operation_paths_are_real_backend_contracts(self) -> None:
        static_js = Path(
            "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js"
        ).read_text(encoding="utf-8")
        api_source = Path("src/openinfra/interfaces/http_api.py").read_text(encoding="utf-8")
        operation_paths = sorted(set(re.findall(r'path: "([^"]+)"', static_js)))
        api_routes = set(re.findall(r'"(/api/v1/[^"]+)"', api_source))

        assert operation_paths
        assert "/v1/ipam/search" not in operation_paths
        assert "/api/v1/database/schema" not in operation_paths
        for operation_path in operation_paths:
            assert operation_path.startswith("/v1/")
            backend_route = "/api" + operation_path
            if backend_route in api_routes:
                continue
            if backend_route.startswith("/api/v1/itrm/"):
                legacy_route = "/api/v1/sot/" + backend_route.removeprefix("/api/v1/itrm/")
                assert legacy_route in api_routes
                continue
            raise AssertionError("dashboard operation route is not backed by API: " + backend_route)

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

    def test_web_injects_server_side_backend_bearer_token_without_exposing_it(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url, backend_bearer_token=_test_server_side_bearer())
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                static_js = self._get_text(web.base_url + "/assets/openinfra-web.js")
                public_config = self._get_json(web.base_url + "/config.json")
                echoed = self._post_json(
                    web.base_url + "/api/v1/echo",
                    {"tenant_id": "default", "value": 99},
                )

        assert "server-side-secret" not in static_js + json.dumps(public_config, sort_keys=True)
        assert echoed["authorization"] == "Bearer server-side-secret"
        assert echoed["browser_authorization_forwarded"] is False
        assert echoed["web_trust"] == "server-side"

    def test_config_factory_falls_back_to_bootstrap_token_when_web_token_is_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        static_root = OpenInfraWebStaticLocator().resolve(None)
        monkeypatch.setenv("OPENINFRA_WEB_BACKEND_BEARER_TOKEN", "   ")
        monkeypatch.setenv("OPENINFRA_BOOTSTRAP_TOKEN", "bootstrap-runtime-token")
        factory = __import__(
            "openinfra.interfaces.web", fromlist=["OpenInfraWebConfigFactory"]
        ).OpenInfraWebConfigFactory()

        config = factory.from_args(
            [
                "--backend-url",
                "http://backend.internal",
                "--static-root",
                str(static_root),
                "--edition",
                "pro",
                "--allow-insecure-backend",
            ]
        )

        assert config.backend_bearer_token == "bootstrap-runtime-token"

    def test_protected_web_proxy_never_returns_raw_missing_bearer_token(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url)
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                status = self._get_json(web.base_url + "/status")
                with pytest.raises(urllib.error.HTTPError) as exc:
                    self._post_json(web.base_url + "/api/v1/echo", {"tenant_id": "default"})
                payload = json.loads(exc.value.read().decode("utf-8"))

        assert status["protectedForms"] == "blocked-by-missing-server-bearer"
        assert status["trust"]["backendBearer"] == "not-configured"
        assert "OPENINFRA_BOOTSTRAP_TOKEN" in status["remediation"]["environment"]
        assert exc.value.code == HTTPStatus.SERVICE_UNAVAILABLE.value
        assert payload["error"] == "web backend bearer token is not configured"
        assert "missing bearer token" not in json.dumps(payload)

    def test_web_proxy_sanitizes_backend_raw_missing_bearer_response(self) -> None:
        with RunningServer(ThreadingHTTPServer(("127.0.0.1", 0), BackendFakeHandler)) as backend:
            config = self._config(backend.base_url, backend_bearer_token=_test_server_side_bearer())
            with RunningServer(OpenInfraWebServer(("127.0.0.1", 0), config)) as web:
                with pytest.raises(urllib.error.HTTPError) as exc:
                    self._post_json(web.base_url + "/api/v1/raw-missing-bearer", {})
                payload = json.loads(exc.value.read().decode("utf-8"))

        assert exc.value.code == HTTPStatus.BAD_GATEWAY.value
        assert payload == {
            "error": "backend authentication failed through openinfra-web",
            "reason": "server-side backend bearer token was not accepted by the API",
        }
        assert "missing bearer token" not in json.dumps(payload)

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

    def _config(self, backend_url: str, backend_bearer_token: str = "") -> OpenInfraWebConfig:
        return OpenInfraWebConfig(
            host="127.0.0.1",
            port=0,
            backend_url=backend_url,
            public_api_base_url="/api",
            static_root=OpenInfraWebStaticLocator().resolve(None),
            edition="pro",
            auth_mode="standard",
            allow_insecure_backend=True,
            backend_bearer_token=backend_bearer_token,
        )

    def _get_text(self, url: str) -> str:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8")

    def _post_json(
        self, url: str, payload: dict[str, object], browser_bearer: str = ""
    ) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if browser_bearer:
            headers["Authorization"] = "Bearer " + browser_bearer
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
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
                backend_bearer_token=_test_server_side_bearer(),
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
