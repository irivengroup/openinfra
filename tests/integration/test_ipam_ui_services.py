from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import (
    DefineIpPrefixCommand,
    DefineIpRangeCommand,
    DefineVrfCommand,
    IpamReservationWizardCommand,
    IpamSearchCommand,
    IpamUiDashboardCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
)
from openinfra.domain.common import ValidationError
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestIpamUiServices:
    def test_dashboard_search_and_reservation_wizard(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_vrf(DefineVrfCommand("default", "pytest", "prod"))
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.22.1.0/29")
        )
        app.ipam_model_service.define_range(
            DefineIpRangeCommand(
                "default",
                "pytest",
                "prod",
                "10.22.1.0/29",
                "10.22.1.1",
                "10.22.1.6",
                "allocation",
            )
        )

        preview = app.ipam_ui_service.reservation_wizard(
            IpamReservationWizardCommand(
                "default", "pytest", "prod", "10.22.1.0/29", "srv-ui-01", "ui-1"
            )
        )
        applied = app.ipam_ui_service.reservation_wizard(
            IpamReservationWizardCommand(
                "default",
                "pytest",
                "prod",
                "10.22.1.0/29",
                "srv-ui-01",
                "ui-1",
                False,
            )
        )
        dashboard = app.ipam_ui_service.dashboard(IpamUiDashboardCommand("default", "pytest"))
        search = app.ipam_ui_service.search(IpamSearchCommand("default", "pytest", "srv-ui"))
        html = app.ipam_ui_service.render_dashboard_html(
            IpamUiDashboardCommand("default", "pytest")
        )

        assert preview["dry_run"] is True
        assert preview["recommended_address"] == "10.22.1.1"
        assert applied["address"] == "10.22.1.1"
        assert applied["operation"] == "allocated"
        assert dashboard.summary["prefixes"] == 1
        assert dashboard.summary["reservations"] == 1
        assert dashboard.as_dict()["actions"]
        assert search["count"] >= 1
        assert "OpenInfra IPAM" in html
        assert "10.22.1.0/29" in html

    def test_search_includes_observed_dns_and_dhcp(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.22.3.0/29")
        )
        app.ipam_conflict_service.observe_dns(
            ObserveDnsRecordCommand("default", "pytest", "prod", "srv-dns.example.net", "10.22.3.2")
        )
        app.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                "default",
                "pytest",
                "prod",
                "10.22.3.0/29",
                "10.22.3.3",
                "aa:bb:cc:22:03:03",
                "srv-dhcp",
            )
        )

        dns_result = app.ipam_ui_service.search(IpamSearchCommand("default", "pytest", "srv-dns"))
        dhcp_result = app.ipam_ui_service.search(IpamSearchCommand("default", "pytest", "aa:bb"))

        assert any(item["kind"] == "dns" for item in dns_result["items"])
        assert any(item["kind"] == "dhcp_lease" for item in dhcp_result["items"])

    def test_search_rejects_short_query(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        with pytest.raises(ValidationError):
            app.ipam_ui_service.search(IpamSearchCommand("default", "pytest", "x"))

    def test_cli_ipam_ui_commands(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "state.json"
        cli = OpenInfraCLI()
        commands = [
            [
                "ipam",
                "define-prefix",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--vrf",
                "prod",
                "--cidr",
                "10.22.1.0/29",
            ],
            [
                "ipam",
                "reservation-wizard",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--vrf",
                "prod",
                "--prefix",
                "10.22.1.0/29",
                "--hostname",
                "srv-cli-01",
                "--idempotency-key",
                "cli-1",
                "--apply",
            ],
            [
                "ipam",
                "ui-search",
                "--data",
                str(data),
                "--tenant",
                "default",
                "--query",
                "srv-cli",
            ],
            [
                "ipam",
                "ui-dashboard",
                "--data",
                str(data),
                "--tenant",
                "default",
            ],
        ]
        for command in commands:
            assert cli.run(command) == 0
        captured = capsys.readouterr()
        assert '"kind": "reservation"' in captured.out
        assert '"prefixes": 1' in captured.out

    def test_http_ipam_ui_routes(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.22.2.0/29")
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            dashboard = self._get_json(
                base_url + "/api/v1/ipam/ui-dashboard?tenant_id=default&vrf=prod"
            )
            preview = self._post_json(
                base_url + "/api/v1/ipam/reservation-wizard",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "prefix": "10.22.2.0/29",
                    "hostname": "srv-api-ui-01",
                    "idempotency_key": "api-ui-1",
                },
            )
            search = self._get_json(
                base_url + "/api/v1/ipam/ui-search?tenant_id=default&query=10.22.2"
            )
            html = urllib.request.urlopen(base_url + "/ui/ipam?tenant_id=default").read().decode()

            assert dashboard["summary"]["prefixes"] == 1
            assert preview["recommended_address"] == "10.22.2.1"
            assert search["count"] >= 1
            assert "OpenInfra IPAM" in html
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _get_json(self, url: str) -> dict[str, object]:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
