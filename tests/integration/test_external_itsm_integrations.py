from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.external_itsm_services import (
    BuildFreshserviceAssetSyncPlanCommand,
    BuildGlpiAssetSyncPlanCommand,
    BuildJiraServiceManagementAssetSyncPlanCommand,
    BuildOpenServiceCmdbSyncPlanCommand,
    BuildServiceNowCiSyncPlanCommand,
    ValidateFreshserviceConnectorCommand,
    ValidateGlpiConnectorCommand,
    ValidateJiraServiceManagementConnectorCommand,
    ValidateOpenServiceConnectorCommand,
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


    def test_service_validates_jira_connector_and_plan(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        auth_ref = "vault://openinfra/jira/api-token"

        profile = app.external_itsm_service.validate_jira_service_management_connector(
            ValidateJiraServiceManagementConnectorCommand(
                tenant_id="default",
                instance_url="https://tenant.atlassian.net",
                object_type="server",
                auth_secret_ref=auth_ref,
            )
        )
        plan = app.external_itsm_service.build_jira_service_management_asset_sync_plan(
            BuildJiraServiceManagementAssetSyncPlanCommand(
                tenant_id="default",
                resource_key="SRV-PAR1-001",
                direction="push_ci",
                object_type="server",
            )
        )

        assert profile.provider.value == "jira_service_management"
        assert profile.as_dict()["native_ticketing_enabled"] is False
        assert plan.as_dict()["mapping"]["resource_key"] == "external_id"
        assert plan.as_dict()["target_table"] == "server"

    def test_service_prepares_openservice_connector_without_openinfra_web_ui(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")

        profile = app.external_itsm_service.validate_openservice_connector(
            ValidateOpenServiceConnectorCommand(
                tenant_id="default",
                instance_url="https://openservice.example.com",
                collection="configuration_item",
                auth_secret_ref="vault://openinfra/openservice/oauth",
            )
        )
        plan = app.external_itsm_service.build_openservice_cmdb_sync_plan(
            BuildOpenServiceCmdbSyncPlanCommand(
                tenant_id="default",
                resource_key="SRV-PAR1-001",
                direction="push_ci",
                collection="configuration_item",
            )
        )
        policies = [
            policy.as_dict() for policy in app.external_itsm_service.list_policies()
        ]

        assert profile.provider.value == "openservice"
        assert profile.as_dict()["native_ticketing_enabled"] is False
        assert plan.as_dict()["mapping"]["resource_key"] == "openinfra_resource_key"
        assert policies[-1]["provider"] == "openservice"
        assert policies[-1]["openinfra_web_ui_enabled"] is False
        assert policies[-1]["integration_ui_owner"] == "openservice-web"

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


    def test_cli_jira_contracts(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        auth_ref = "vault://openinfra/jira/api-token"
        code = OpenInfraCLI().run(
            [
                "integrations",
                "jira-validate",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--instance-url",
                "https://tenant.atlassian.net",
                "--object-type",
                "server",
                "--auth-secret-ref",
                auth_ref,
            ]
        )
        profile = json.loads(capsys.readouterr().out)
        plan_code = OpenInfraCLI().run(
            [
                "integrations",
                "jira-asset-sync-plan",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--resource-key",
                "SRV-PAR1-001",
                "--object-type",
                "server",
            ]
        )
        plan = json.loads(capsys.readouterr().out)

        assert code == 0
        assert plan_code == 0
        assert profile["provider"] == "jira_service_management"
        assert plan["target_table"] == "server"

    def test_service_validates_glpi_and_freshservice_connectors_and_plans(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")

        glpi_profile = app.external_itsm_service.validate_glpi_connector(
            ValidateGlpiConnectorCommand(
                tenant_id="default",
                instance_url="https://glpi.example.com",
                item_type="computer",
                auth_secret_ref="vault://openinfra/glpi/tokens",
            )
        )
        glpi_plan = app.external_itsm_service.build_glpi_asset_sync_plan(
            BuildGlpiAssetSyncPlanCommand(
                tenant_id="default",
                resource_key="SRV-PAR1-001",
                direction="push_ci",
                item_type="computer",
            )
        )
        freshservice_profile = app.external_itsm_service.validate_freshservice_connector(
            ValidateFreshserviceConnectorCommand(
                tenant_id="default",
                instance_url="https://tenant.freshservice.com",
                asset_type="server",
                auth_secret_ref="vault://openinfra/freshservice/api-token",
            )
        )
        freshservice_plan = app.external_itsm_service.build_freshservice_asset_sync_plan(
            BuildFreshserviceAssetSyncPlanCommand(
                tenant_id="default",
                resource_key="SRV-PAR1-001",
                direction="push_ci",
                asset_type="server",
            )
        )

        assert glpi_profile.provider.value == "glpi"
        assert glpi_profile.as_dict()["native_ticketing_enabled"] is False
        assert glpi_plan.as_dict()["mapping"]["resource_key"] == "serial"
        assert freshservice_profile.provider.value == "freshservice"
        assert freshservice_profile.as_dict()["native_ticketing_enabled"] is False
        assert freshservice_plan.as_dict()["mapping"]["resource_key"] == "asset_tag"

    def test_cli_glpi_and_freshservice_contracts(
        self, tmp_path: Path, capsys: object
    ) -> None:
        data = tmp_path / "state.json"
        glpi_code = OpenInfraCLI().run(
            [
                "integrations",
                "glpi-validate",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--instance-url",
                "https://glpi.example.com",
                "--item-type",
                "computer",
                "--auth-secret-ref",
                "vault://openinfra/glpi/tokens",
            ]
        )
        glpi_profile = json.loads(capsys.readouterr().out)
        glpi_plan_code = OpenInfraCLI().run(
            [
                "integrations",
                "glpi-asset-sync-plan",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--resource-key",
                "SRV-PAR1-001",
                "--item-type",
                "computer",
            ]
        )
        glpi_plan = json.loads(capsys.readouterr().out)
        freshservice_code = OpenInfraCLI().run(
            [
                "integrations",
                "freshservice-validate",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--instance-url",
                "https://tenant.freshservice.com",
                "--asset-type",
                "server",
                "--auth-secret-ref",
                "vault://openinfra/freshservice/api-token",
            ]
        )
        freshservice_profile = json.loads(capsys.readouterr().out)
        freshservice_plan_code = OpenInfraCLI().run(
            [
                "integrations",
                "freshservice-asset-sync-plan",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--resource-key",
                "SRV-PAR1-001",
                "--asset-type",
                "server",
            ]
        )
        freshservice_plan = json.loads(capsys.readouterr().out)

        assert glpi_code == 0
        assert glpi_plan_code == 0
        assert glpi_profile["provider"] == "glpi"
        assert glpi_plan["target_table"] == "computer"
        assert freshservice_code == 0
        assert freshservice_plan_code == 0
        assert freshservice_profile["provider"] == "freshservice"
        assert freshservice_plan["target_table"] == "server"

    def test_cli_openservice_contracts(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        code = OpenInfraCLI().run(
            [
                "integrations",
                "openservice-validate",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--instance-url",
                "https://openservice.example.com",
                "--collection",
                "configuration_item",
                "--auth-secret-ref",
                "vault://openinfra/openservice/oauth",
            ]
        )
        profile = json.loads(capsys.readouterr().out)
        plan_code = OpenInfraCLI().run(
            [
                "integrations",
                "openservice-cmdb-sync-plan",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--resource-key",
                "SRV-PAR1-001",
                "--collection",
                "configuration_item",
            ]
        )
        plan = json.loads(capsys.readouterr().out)

        assert code == 0
        assert plan_code == 0
        assert profile["provider"] == "openservice"
        assert profile["native_ticketing_enabled"] is False
        assert plan["target_table"] == "configuration_item"
        assert plan["mapping"]["cmdb_class"] == "cmdb_class"

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

            jira_profile = self._post_json(
                base_url + "/api/v1/integrations/itsm/jira/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "https://tenant.atlassian.net",
                    "object_type": "server",
                    "auth_secret_ref": "vault://openinfra/jira/api-token",
                },
                token=token,
            )
            jira_plan = self._post_json(
                base_url + "/api/v1/integrations/itsm/jira/asset-sync-plan",
                {"tenant_id": "default", "resource_key": "SRV-PAR1-001", "object_type": "server"},
                token=token,
            )
            glpi_profile = self._post_json(
                base_url + "/api/v1/integrations/itsm/glpi/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "https://glpi.example.com",
                    "item_type": "computer",
                    "auth_secret_ref": "vault://openinfra/glpi/tokens",
                },
                token=token,
            )
            glpi_plan = self._post_json(
                base_url + "/api/v1/integrations/itsm/glpi/asset-sync-plan",
                {"tenant_id": "default", "resource_key": "SRV-PAR1-001", "item_type": "computer"},
                token=token,
            )
            freshservice_profile = self._post_json(
                base_url + "/api/v1/integrations/itsm/freshservice/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "https://tenant.freshservice.com",
                    "asset_type": "server",
                    "auth_secret_ref": "vault://openinfra/freshservice/api-token",
                },
                token=token,
            )
            freshservice_plan = self._post_json(
                base_url + "/api/v1/integrations/itsm/freshservice/asset-sync-plan",
                {"tenant_id": "default", "resource_key": "SRV-PAR1-001", "asset_type": "server"},
                token=token,
            )
            openservice_profile = self._post_json(
                base_url + "/api/v1/integrations/itsm/openservice/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "https://openservice.example.com",
                    "collection": "configuration_item",
                    "auth_secret_ref": "vault://openinfra/openservice/oauth",
                },
                token=token,
            )
            openservice_plan = self._post_json(
                base_url + "/api/v1/integrations/itsm/openservice/cmdb-sync-plan",
                {
                    "tenant_id": "default",
                    "resource_key": "SRV-PAR1-001",
                    "collection": "configuration_item",
                },
                token=token,
            )

            assert policies["items"][0]["provider"] == "servicenow"
            assert policies["items"][1]["provider"] == "jira_service_management"
            assert policies["items"][2]["provider"] == "glpi"
            assert policies["items"][3]["provider"] == "freshservice"
            assert policies["items"][4]["provider"] == "openservice"
            assert policies["items"][4]["openinfra_web_ui_enabled"] is False
            assert policies["items"][4]["integration_ui_owner"] == "openservice-web"
            assert profile["native_ticketing_enabled"] is False
            assert plan["direction"] == "push_ci"
            assert jira_profile["provider"] == "jira_service_management"
            assert jira_plan["target_table"] == "server"
            assert glpi_profile["provider"] == "glpi"
            assert glpi_plan["target_table"] == "computer"
            assert freshservice_profile["provider"] == "freshservice"
            assert freshservice_plan["target_table"] == "server"
            assert openservice_profile["provider"] == "openservice"
            assert openservice_plan["target_table"] == "configuration_item"
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
