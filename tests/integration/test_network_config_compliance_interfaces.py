from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestNetworkConfigComplianceInterfaces:
    def test_cli_complete_cycle(self, tmp_path: Path, capsys) -> None:
        state = tmp_path / "state.json"
        expected = tmp_path / "expected.json"
        observed = tmp_path / "observed.json"
        expected.write_text('{"hostname":"core-01"}', encoding="utf-8")
        observed.write_text('{"hostname":"core-02"}', encoding="utf-8")
        token = "c" * 40
        app = ApplicationFactory().create_json_application(state)
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "admin", ("admin",), token)
        )
        common = [
            "--backend",
            "json",
            "--data",
            str(state),
            "--tenant",
            "default",
            "--admin-token",
            token,
        ]
        assert (
            OpenInfraCLI().run(
                [
                    "network-config",
                    "baseline-upsert",
                    *common,
                    "--code",
                    "CORE-GOLDEN",
                    "--device-object-key",
                    "network-device/core-01",
                    "--platform",
                    "ios-xe",
                    "--expected-config-file",
                    str(expected),
                    "--critical-path",
                    "/hostname",
                    "--owner",
                    "Network Team",
                    "--justification",
                    "Approved production golden configuration",
                ]
            )
            == 0
        )
        baseline = json.loads(capsys.readouterr().out)
        assert baseline["code"] == "CORE-GOLDEN"
        assert (
            OpenInfraCLI().run(
                [
                    "network-config",
                    "observation-submit",
                    *common,
                    "--idempotency-key",
                    "collector-core-0001",
                    "--source",
                    "netconf",
                    "--collector",
                    "collector-paris",
                    "--device-object-key",
                    "network-device/core-01",
                    "--platform",
                    "ios-xe",
                    "--observed-config-file",
                    str(observed),
                    "--observed-at",
                    datetime.now(UTC).isoformat(),
                ]
            )
            == 0
        )
        capsys.readouterr()
        assert (
            OpenInfraCLI().run(
                ["network-config", "assess", *common, "--baseline-code", "CORE-GOLDEN"]
            )
            == 0
        )
        report = json.loads(capsys.readouterr().out)
        assert report["items"][0]["status"] == "drift"

    def test_http_complete_cycle_and_discovery_document(self, tmp_path: Path) -> None:
        token = "h" * 40
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "admin", ("admin",), token)
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            baseline = self._request(
                base + "/api/v1/network-config/baselines/upsert",
                token,
                {
                    "tenant_id": "default",
                    "code": "CORE-GOLDEN",
                    "device_object_key": "network-device/core-01",
                    "platform": "ios-xe",
                    "expected_config": {"hostname": "core-01"},
                    "critical_paths": ["/hostname"],
                    "owner": "Network Team",
                    "justification": "Approved production golden configuration",
                },
            )
            assert baseline["version"] == 1
            self._request(
                base + "/api/v1/network-config/observations/submit",
                token,
                {
                    "tenant_id": "default",
                    "idempotency_key": "collector-core-0001",
                    "source": "netconf",
                    "collector": "collector-paris",
                    "device_object_key": "network-device/core-01",
                    "platform": "ios-xe",
                    "observed_config": {"hostname": "core-02"},
                    "observed_at": datetime.now(UTC).isoformat(),
                },
            )
            assessment = self._request(
                base
                + "/api/v1/network-config/assessment?"
                + urllib.parse.urlencode({"tenant_id": "default", "baseline_code": "CORE-GOLDEN"}),
                token,
                None,
            )
            assert assessment["items"][0]["status"] == "drift"
            baselines = self._request(
                base + "/api/v1/network-config/baselines?tenant_id=default", token, None
            )
            observations = self._request(
                base + "/api/v1/network-config/observations?tenant_id=default", token, None
            )
            assert len(baselines["items"]) == 1
            assert len(observations["items"]) == 1
            retired = self._request(
                base + "/api/v1/network-config/baselines/retire",
                token,
                {"tenant_id": "default", "baseline_id": baseline["id"]},
            )
            assert retired["status"] == "retired"

            unauthorized_requests = (
                (base + "/api/v1/network-config/baselines?tenant_id=default", None),
                (base + "/api/v1/network-config/observations?tenant_id=default", None),
                (base + "/api/v1/network-config/assessment?tenant_id=default", None),
                (
                    base + "/api/v1/network-config/baselines/upsert",
                    {
                        "tenant_id": "default",
                        "code": "UNAUTHORIZED",
                        "device_object_key": "network-device/core-02",
                        "platform": "ios-xe",
                        "expected_config": {"hostname": "core-02"},
                        "owner": "Network Team",
                        "justification": "Unauthorized request must be rejected",
                    },
                ),
                (
                    base + "/api/v1/network-config/baselines/retire",
                    {"tenant_id": "default", "baseline_id": baseline["id"]},
                ),
                (
                    base + "/api/v1/network-config/observations/submit",
                    {
                        "tenant_id": "default",
                        "idempotency_key": "unauthorized-observation-0001",
                        "source": "api",
                        "collector": "collector-paris",
                        "device_object_key": "network-device/core-01",
                        "platform": "ios-xe",
                        "observed_config": {"hostname": "core-01"},
                        "observed_at": datetime.now(UTC).isoformat(),
                    },
                ),
            )
            for url, payload in unauthorized_requests:
                with pytest.raises(urllib.error.HTTPError) as exc_info:
                    self._request(url, None, payload)
                assert exc_info.value.code == 401

            discovery = self._request(base + "/api/v1", None, None)
            assert (
                discovery["documentation"]["network_config"]["assessment"]
                == "/api/v1/network-config/assessment"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    @staticmethod
    def _request(
        url: str, token: str | None, payload: dict[str, object] | None
    ) -> dict[str, object]:
        headers = {"Authorization": "Bearer " + token} if token else {}
        data = None
        method = "GET"
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
            method = "POST"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=5) as response:
            value = json.loads(response.read().decode("utf-8"))
        assert isinstance(value, dict)
        return value


def test_openapi_and_web_catalog_document_network_config_compliance() -> None:
    openapi = Path("docs/api/openapi.yaml").read_text(encoding="utf-8")
    react = Path("web/src/main.jsx").read_text(encoding="utf-8")
    runtime = Path("src/openinfra/interfaces/rendering/static/assets/openinfra-web.js").read_text(
        encoding="utf-8"
    )
    for route in (
        "/api/v1/network-config/baselines:",
        "/api/v1/network-config/baselines/upsert:",
        "/api/v1/network-config/baselines/retire:",
        "/api/v1/network-config/observations:",
        "/api/v1/network-config/observations/submit:",
        "/api/v1/network-config/assessment:",
    ):
        assert route in openapi
    for marker in (
        "network-config-baseline-upsert",
        "network-config-observation-submit",
        "network-config-assessment",
    ):
        assert marker in react
        assert marker in runtime
