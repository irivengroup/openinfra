from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.external_itsm_services import (
    BuildServiceNowCiSyncPlanCommand,
    ValidateServiceNowConnectorCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestExternalItsmIntegrations:
    def test_service_validates_servicenow_connector_and_plan(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        auth_ref = "vault://openinfra/servicenow/oauth"

        profile = app.external_itsm_service.validate_servicenow_connector(
            ValidateServiceNowConnectorCommand(
                tenant_id="default",
                instance_url="https://instance.service-now.com",
                table_name="cmdb_ci_server",
                auth_secret_ref=auth_ref,
            )
        )
        plan = app.external_itsm_service.build_servicenow_ci_sync_plan(
            BuildServiceNowCiSyncPlanCommand(
                tenant_id="default",
                resource_key="SRV-PAR1-001",
                direction="push_ci",
                target_table="cmdb_ci_server",
            )
        )

        assert profile.provider.value == "servicenow"
        assert profile.as_dict()["native_ticketing_enabled"] is False
        assert plan.as_dict()["mapping"]["resource_key"] == "correlation_id"
        assert plan.as_dict()["native_ticketing_enabled"] is False

    def test_cli_servicenow_contracts(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        auth_ref = "vault://openinfra/servicenow/oauth"
        code = OpenInfraCLI().run(
            [
                "integrations",
                "servicenow-validate",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--instance-url",
                "https://instance.service-now.com",
                "--table-name",
                "cmdb_ci",
                "--auth-secret-ref",
                auth_ref,
            ]
        )
        profile = json.loads(capsys.readouterr().out)
        plan_code = OpenInfraCLI().run(
            [
                "integrations",
                "servicenow-ci-sync-plan",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--resource-key",
                "SRV-PAR1-001",
            ]
        )
        plan = json.loads(capsys.readouterr().out)

        assert code == 0
        assert plan_code == 0
        assert profile["native_ticketing_enabled"] is False
        assert plan["target_table"] == "cmdb_ci"

    def test_http_servicenow_contracts_are_security_admin_protected(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        auth_ref = "vault://openinfra/servicenow/oauth"
        token = "n" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "itsm-admin", ("security:admin",), token)
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            policies = self._get_json(
                base_url + "/api/v1/integrations/itsm/providers?tenant_id=default", token=token
            )
            profile = self._post_json(
                base_url + "/api/v1/integrations/itsm/servicenow/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "https://instance.service-now.com",
                    "table_name": "cmdb_ci",
                    "auth_secret_ref": auth_ref,
                },
                token=token,
            )
            plan = self._post_json(
                base_url + "/api/v1/integrations/itsm/servicenow/ci-sync-plan",
                {"tenant_id": "default", "resource_key": "SRV-PAR1-001"},
                token=token,
            )
            try:
                self._get_json(base_url + "/api/v1/integrations/itsm/providers?tenant_id=default")
            except urllib.error.HTTPError as exc:
                assert exc.code == 401

            assert policies["items"][0]["provider"] == "servicenow"
            assert profile["native_ticketing_enabled"] is False
            assert plan["direction"] == "push_ci"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _get_json(self, url: str, token: str | None = None) -> dict[str, object]:
        request = urllib.request.Request(url, headers=self._headers(token), method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(
        self, url: str, payload: dict[str, object], token: str | None = None
    ) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(token) | {"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _headers(self, token: str | None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return headers
