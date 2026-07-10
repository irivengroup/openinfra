from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestFlowMatrixInterfaces:
    def test_cli_exposes_declarations_observations_and_matrix(self, tmp_path: Path, capsys) -> None:
        data_path = tmp_path / "state.json"
        token = "c" * 40
        self._seed(data_path, token)
        now = datetime.now(UTC) - timedelta(minutes=2)
        start = now - timedelta(hours=1)
        common = [
            "--backend",
            "json",
            "--data",
            str(data_path),
            "--tenant",
            "default",
            "--admin-token",
            token,
        ]

        assert (
            OpenInfraCLI().run(
                [
                    "flow",
                    "declaration-upsert",
                    *common,
                    "--code",
                    "APP-HTTPS",
                    "--source-selector",
                    "any",
                    "--destination-selector",
                    "cidr:10.20.30.0/24",
                    "--protocol",
                    "tcp",
                    "--destination-port-start",
                    "443",
                    "--decision",
                    "allow",
                    "--owner",
                    "network team",
                    "--justification",
                    "approved application flow",
                    "--valid-from",
                    start.isoformat(),
                ]
            )
            == 0
        )
        declaration = json.loads(capsys.readouterr().out)
        assert declaration["code"] == "APP-HTTPS"

        assert (
            OpenInfraCLI().run(
                [
                    "flow",
                    "observation-submit",
                    *common,
                    "--idempotency-key",
                    "cli-flow:000001",
                    "--source",
                    "ipfix",
                    "--collector",
                    "collector-cli",
                    "--source-ip",
                    "10.1.1.10",
                    "--destination-ip",
                    "10.20.30.40",
                    "--protocol",
                    "tcp",
                    "--destination-port",
                    "443",
                    "--packets",
                    "2",
                    "--bytes",
                    "1024",
                    "--first-seen",
                    (now - timedelta(minutes=1)).isoformat(),
                    "--last-seen",
                    now.isoformat(),
                ]
            )
            == 0
        )
        observation = json.loads(capsys.readouterr().out)
        assert observation["source"] == "ipfix"

        assert OpenInfraCLI().run(["flow", "declaration-list", *common]) == 0
        assert len(json.loads(capsys.readouterr().out)["items"]) == 1
        assert (
            OpenInfraCLI().run(
                [
                    "flow",
                    "observation-list",
                    *common,
                    "--window-start",
                    start.isoformat(),
                    "--window-end",
                    (now + timedelta(minutes=1)).isoformat(),
                ]
            )
            == 0
        )
        assert len(json.loads(capsys.readouterr().out)["items"]) == 1
        assert (
            OpenInfraCLI().run(
                [
                    "flow",
                    "matrix",
                    *common,
                    "--window-start",
                    start.isoformat(),
                    "--window-end",
                    (now + timedelta(minutes=1)).isoformat(),
                ]
            )
            == 0
        )
        matrix = json.loads(capsys.readouterr().out)
        assert matrix["totals"]["compliant"] == 1

        assert (
            OpenInfraCLI().run(
                [
                    "flow",
                    "declaration-retire",
                    *common,
                    "--declaration-id",
                    declaration["id"],
                ]
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["status"] == "retired"

    def test_http_api_exposes_full_flow_cycle_and_authentication(self, tmp_path: Path) -> None:
        token = "h" * 40
        app = self._seed(tmp_path / "state.json", token)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            now = datetime.now(UTC) - timedelta(minutes=2)
            start = now - timedelta(hours=1)
            declaration = self._post_json(
                base + "/api/v1/flows/declarations/upsert",
                {
                    "tenant_id": "default",
                    "code": "API-HTTPS",
                    "source_selector": "any",
                    "destination_selector": "cidr:10.40.0.0/16",
                    "protocol": "tcp",
                    "destination_port_start": 443,
                    "decision": "allow",
                    "priority": 100,
                    "owner": "network team",
                    "justification": "approved API flow",
                    "valid_from": start.isoformat(),
                },
                token,
            )
            observation = self._post_json(
                base + "/api/v1/flows/observations/submit",
                {
                    "tenant_id": "default",
                    "idempotency_key": "api-flow:000001",
                    "source": "firewall-log",
                    "collector": "fw-par-01",
                    "source_ip": "10.1.1.10",
                    "destination_ip": "10.40.1.20",
                    "protocol": "tcp",
                    "destination_port": 443,
                    "packets": 5,
                    "bytes": 4096,
                    "first_seen": (now - timedelta(minutes=1)).isoformat(),
                    "last_seen": now.isoformat(),
                },
                token,
            )
            params = urllib.parse.urlencode(
                {
                    "tenant_id": "default",
                    "window_start": start.isoformat(),
                    "window_end": (now + timedelta(minutes=1)).isoformat(),
                }
            )
            declarations = self._get_json(
                base + "/api/v1/flows/declarations?tenant_id=default", token
            )
            observations = self._get_json(base + "/api/v1/flows/observations?" + params, token)
            matrix = self._get_json(base + "/api/v1/flows/matrix?" + params, token)
            discovery = self._get_json(base + "/api/v1", None)

            assert declaration["code"] == "API-HTTPS"
            assert observation["source"] == "firewall-log"
            assert len(declarations["items"]) == 1
            assert len(observations["items"]) == 1
            assert matrix["totals"]["compliant"] == 1
            assert discovery["documentation"]["flows"] == {
                "declarations": "/api/v1/flows/declarations",
                "declaration_upsert": "/api/v1/flows/declarations/upsert",
                "declaration_retire": "/api/v1/flows/declarations/retire",
                "observations": "/api/v1/flows/observations",
                "observation_submit": "/api/v1/flows/observations/submit",
                "matrix": "/api/v1/flows/matrix",
            }

            retired = self._post_json(
                base + "/api/v1/flows/declarations/retire",
                {"tenant_id": "default", "declaration_id": declaration["id"]},
                token,
            )
            assert retired["status"] == "retired"

            try:
                self._get_json(base + "/api/v1/flows/declarations?tenant_id=default", None)
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            else:
                raise AssertionError("flow endpoint accepted a missing bearer token")

            try:
                self._post_json(
                    base + "/api/v1/flows/observations/submit",
                    {"tenant_id": "default"},
                    token,
                )
            except urllib.error.HTTPError as exc:
                assert exc.code == 400
            else:
                raise AssertionError("flow endpoint accepted a malformed payload")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _seed(self, data_path: Path, token: str):
        app = ApplicationFactory().create_json_application(data_path)
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "flow-interface", ("admin",), token)
        )
        return app

    @staticmethod
    def _get_json(url: str, token: str | None) -> dict[str, object]:
        headers = {"Authorization": "Bearer " + token} if token else {}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert isinstance(payload, dict)
        return payload

    @staticmethod
    def _post_json(url: str, payload: dict[str, object], token: str) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        assert isinstance(result, dict)
        return result


def test_openapi_and_web_assets_document_flow_matrix() -> None:
    openapi = Path("docs/api/openapi.yaml").read_text(encoding="utf-8")
    react = Path("web/src/main.jsx").read_text(encoding="utf-8")
    static = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-web.js").read_text(
        encoding="utf-8"
    )
    i18n = Path("web/src/i18n.js").read_text(encoding="utf-8")

    for route in (
        "/api/v1/flows/declarations:",
        "/api/v1/flows/declarations/upsert:",
        "/api/v1/flows/declarations/retire:",
        "/api/v1/flows/observations:",
        "/api/v1/flows/observations/submit:",
        "/api/v1/flows/matrix:",
    ):
        assert route in openapi
    for operation in (
        "flow-declaration-upsert",
        "flow-declaration-list",
        "flow-declaration-retire",
        "flow-observation-submit",
        "flow-observation-list",
        "flow-matrix",
    ):
        assert operation in react
        assert operation in static
        assert operation in i18n
    assert "flows: ['Flow matrix', 'Flows']" in i18n
    assert (
        Path("web/src/i18n.js").read_bytes()
        == Path("src/openinfra/interfaces/rendering/static/assets/openinfra-i18n.js").read_bytes()
    )
