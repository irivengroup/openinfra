from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from tests.integration.test_certificate_pki_services import certificate_bundle

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestCertificatePkiInterfaces:
    def test_cli_exposes_full_certificate_cycle(self, tmp_path: Path, capsys) -> None:
        data_path = tmp_path / "state.json"
        pem_path = tmp_path / "bundle.pem"
        pem_path.write_text(certificate_bundle(), encoding="utf-8")
        token = "c" * 40
        self._seed(data_path, token)
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
                    "certificate",
                    "import",
                    *common,
                    "--pem-file",
                    str(pem_path),
                    "--owner",
                    "Platform team",
                    "--environment",
                    "production",
                    "--source",
                    "internal-pki",
                    "--object-key",
                    "application/api",
                ]
            )
            == 0
        )
        imported = json.loads(capsys.readouterr().out)
        fingerprint = imported["leaf"]["fingerprint_sha256"]
        assert imported["certificate_count"] == 2

        assert (
            OpenInfraCLI().run(["certificate", "get", *common, "--fingerprint", fingerprint]) == 0
        )
        assert json.loads(capsys.readouterr().out)["owner"] == "Platform team"
        assert OpenInfraCLI().run(["certificate", "list", *common]) == 0
        assert len(json.loads(capsys.readouterr().out)["items"]) == 2

        assert (
            OpenInfraCLI().run(
                [
                    "certificate",
                    "endpoint-observe",
                    *common,
                    "--idempotency-key",
                    "cli-scanner:000001",
                    "--protocol",
                    "https",
                    "--host",
                    "api.example.com",
                    "--port",
                    "443",
                    "--service",
                    "Public API",
                    "--certificate-fingerprint",
                    fingerprint,
                    "--observed-at",
                    datetime(2026, 7, 10, 12, 0, tzinfo=UTC).isoformat(),
                    "--source",
                    "discovery",
                    "--collector",
                    "scanner-cli",
                ]
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out)["endpoint"] == "https://api.example.com:443"
        assert OpenInfraCLI().run(["certificate", "endpoint-list", *common]) == 0
        assert len(json.loads(capsys.readouterr().out)["items"]) == 1
        assert OpenInfraCLI().run(["certificate", "assess", *common]) == 0
        assert json.loads(capsys.readouterr().out)["totals"]["critical"] == 1
        assert (
            OpenInfraCLI().run(["certificate", "retire", *common, "--fingerprint", fingerprint])
            == 0
        )
        assert json.loads(capsys.readouterr().out)["lifecycle"] == "retired"

    def test_http_api_exposes_certificate_inventory_and_authentication(
        self, tmp_path: Path
    ) -> None:
        token = "h" * 40
        app = self._seed(tmp_path / "state.json", token)
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            imported = self._post_json(
                base + "/api/v1/certificates/import",
                {
                    "tenant_id": "default",
                    "pem_bundle": certificate_bundle(),
                    "owner": "Platform team",
                    "environment": "production",
                    "source": "internal-pki",
                    "object_key": "application/api",
                },
                token,
            )
            fingerprint = str(imported["leaf"]["fingerprint_sha256"])
            observed = self._post_json(
                base + "/api/v1/certificates/endpoints/observe",
                {
                    "tenant_id": "default",
                    "idempotency_key": "api-scanner:000001",
                    "protocol": "https",
                    "host": "api.example.com",
                    "port": 443,
                    "service": "Public API",
                    "certificate_fingerprint": fingerprint,
                    "observed_at": "2026-07-10T12:00:00+00:00",
                    "source": "discovery",
                    "collector": "scanner-api",
                },
                token,
            )
            query = urllib.parse.urlencode({"tenant_id": "default", "fingerprint": fingerprint})
            certificate = self._get_json(base + "/api/v1/certificates/get?" + query, token)
            certificates = self._get_json(base + "/api/v1/certificates?tenant_id=default", token)
            endpoints = self._get_json(
                base + "/api/v1/certificates/endpoints?tenant_id=default", token
            )
            assessment = self._get_json(
                base + "/api/v1/certificates/assessment?tenant_id=default", token
            )
            discovery = self._get_json(base + "/api/v1", None)

            assert imported["certificate_count"] == 2
            assert observed["certificate_fingerprint"] == fingerprint
            assert certificate["owner"] == "Platform team"
            assert len(certificates["items"]) == 2
            assert len(endpoints["items"]) == 1
            assert assessment["totals"]["critical"] == 1
            assert discovery["documentation"]["certificates"] == {
                "list": "/api/v1/certificates",
                "get": "/api/v1/certificates/get",
                "import": "/api/v1/certificates/import",
                "retire": "/api/v1/certificates/retire",
                "endpoints": "/api/v1/certificates/endpoints",
                "endpoint_observe": "/api/v1/certificates/endpoints/observe",
                "assessment": "/api/v1/certificates/assessment",
            }

            retired = self._post_json(
                base + "/api/v1/certificates/retire",
                {"tenant_id": "default", "fingerprint": fingerprint},
                token,
            )
            assert retired["lifecycle"] == "retired"

            try:
                self._get_json(base + "/api/v1/certificates?tenant_id=default", None)
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            else:
                raise AssertionError("certificate endpoint accepted a missing bearer token")

            try:
                self._post_json(
                    base + "/api/v1/certificates/endpoints/observe",
                    {"tenant_id": "default"},
                    token,
                )
            except urllib.error.HTTPError as exc:
                assert exc.code == 400
            else:
                raise AssertionError("certificate endpoint accepted a malformed payload")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    @staticmethod
    def _seed(data_path: Path, token: str):
        app = ApplicationFactory().create_json_application(data_path)
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "certificate-interface", ("admin",), token)
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
