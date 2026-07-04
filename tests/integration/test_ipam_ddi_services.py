from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineIpPrefixCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
    PreviewDdiReservationCommand,
)
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class TestIpamDdiServices:
    def test_preview_generates_bind_powerdns_kea_changes_and_rollback(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.23.1.0/29")
        )
        allocation = app.ipam_service.allocate(
            AllocateIpCommand("default", "pytest", "prod", "10.23.1.0/29", "srv-ddi-01", "ddi-1")
        )

        preview = app.ipam_ddi_service.preview_reservation(
            PreviewDdiReservationCommand(
                tenant_id="default",
                actor="pytest",
                vrf="prod",
                idempotency_key="ddi-1",
                providers=("all",),
                dns_zone="example.net",
                mac_address="AA-BB-CC-23-00-01",
                ttl=600,
            )
        )
        payload = preview.as_dict()

        assert allocation.reservation.hostname == "srv-ddi-01"
        assert preview.safe_to_apply is True
        assert payload["change_count"] == 5
        assert payload["rollback_change_count"] == 5
        assert payload["divergence_count"] == 0
        assert {item["provider"] for item in payload["changes"]} == {"bind", "powerdns", "kea"}
        assert any(item["name"] == "srv-ddi-01.example.net" for item in payload["changes"])
        assert any(item["action"] == "delete" for item in payload["rollback_changes"])

    def test_preview_blocks_silent_dns_and_dhcp_divergences(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.23.1.0/29")
        )
        app.ipam_service.allocate(
            AllocateIpCommand("default", "pytest", "prod", "10.23.1.0/29", "srv-ddi-02", "ddi-2")
        )
        app.ipam_conflict_service.observe_dns(
            ObserveDnsRecordCommand(
                "default",
                "pytest",
                "prod",
                "srv-ddi-02.example.net",
                "10.23.1.5",
                "legacy.example.net",
            )
        )
        app.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                "default",
                "pytest",
                "prod",
                "10.23.1.0/29",
                "10.23.1.1",
                "aa:bb:cc:23:01:99",
                "legacy-dhcp",
            )
        )

        preview = app.ipam_ddi_service.preview_reservation(
            PreviewDdiReservationCommand(
                "default",
                "pytest",
                "prod",
                "ddi-2",
                ("all",),
                "example.net",
                "aa:bb:cc:23:01:02",
            )
        )

        divergence_kinds = {item.kind for item in preview.divergences}
        assert preview.safe_to_apply is False
        assert "dns_forward_mismatch" in divergence_kinds
        assert "dhcp_address_conflict" in divergence_kinds

    def test_kea_preview_requires_mac_address(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.23.2.0/29")
        )
        app.ipam_service.allocate(
            AllocateIpCommand("default", "pytest", "prod", "10.23.2.0/29", "srv-ddi-03", "ddi-3")
        )

        preview = app.ipam_ddi_service.preview_reservation(
            PreviewDdiReservationCommand(
                "default", "pytest", "prod", "ddi-3", ("kea",), "example.net"
            )
        )

        assert preview.safe_to_apply is False
        assert preview.changes == ()
        assert preview.divergences[0].kind == "dhcp_mac_missing"

    def test_cli_ddi_preview_smoke(self, tmp_path: Path, capsys: object) -> None:
        state = tmp_path / "state.json"
        cli = OpenInfraCLI()
        assert cli.run([
            "ipam", "define-prefix", "--data", str(state), "--tenant", "default",
            "--vrf", "prod", "--cidr", "10.23.3.0/29",
        ]) == 0
        assert cli.run([
            "ipam", "allocate", "--data", str(state), "--tenant", "default",
            "--vrf", "prod", "--prefix", "10.23.3.0/29", "--hostname", "srv-cli-ddi",
            "--idempotency-key", "ddi-cli-1",
        ]) == 0
        assert cli.run([
            "ipam", "ddi-preview", "--data", str(state), "--tenant", "default",
            "--vrf", "prod", "--idempotency-key", "ddi-cli-1", "--provider", "bind",
            "--dns-zone", "example.net",
        ]) == 0

        captured = capsys.readouterr()
        assert '"providers": ["bind"]' in captured.out
        assert "srv-cli-ddi.example.net" in captured.out

    def test_http_ddi_preview_route(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.23.4.0/29")
        )
        app.ipam_service.allocate(
            AllocateIpCommand(
                "default", "pytest", "prod", "10.23.4.0/29", "srv-api-ddi", "ddi-api-1"
            )
        )
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/v1/ipam/ddi-preview"
            payload = self._post_json(
                url,
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "idempotency_key": "ddi-api-1",
                    "providers": ["powerdns"],
                    "dns_zone": "example.net",
                },
            )

            assert payload["safe_to_apply"] is True
            assert payload["providers"] == ["powerdns"]
            assert payload["change_count"] == 2
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def _post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_preview_covers_fqdn_parent_zone_and_all_divergence_shapes(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.23.5.0/29")
        )
        app.ipam_service.allocate(
            AllocateIpCommand(
                "default", "pytest", "prod", "10.23.5.0/29", "srv-ddi-05.example.net", "ddi-5"
            )
        )
        app.ipam_conflict_service.observe_dns(
            ObserveDnsRecordCommand(
                "default",
                "pytest",
                "prod",
                "legacy-owner.example.net",
                "10.23.5.1",
                "legacy-ptr.example.net",
            )
        )
        app.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                "default",
                "pytest",
                "prod",
                "10.23.5.0/29",
                "10.23.5.4",
                "aa:bb:cc:23:05:05",
                "same-mac-other-ip",
            )
        )

        preview = app.ipam_ddi_service.preview_reservation(
            PreviewDdiReservationCommand(
                "default",
                "pytest",
                "prod",
                "ddi-5",
                ("bind", "powerdns"),
                None,
                "aa:bb:cc:23:05:05",
            )
        )

        kinds = {item.kind for item in preview.divergences}
        assert "dns_address_owner_mismatch" in kinds
        assert "dns_ptr_mismatch" in kinds
        assert "dhcp_mac_conflict" in kinds
        assert any(
            change.as_dict()["metadata"].get("zone") == "example.net"
            for change in preview.changes
            if change.record_kind.value == "dns_forward"
        )

    def test_preview_validation_errors_are_explicit(self, tmp_path: Path) -> None:
        from openinfra.application.ipam_services import IpamDdiService

        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "pytest", "prod", "10.23.6.0/29")
        )
        app.ipam_service.allocate(
            AllocateIpCommand("default", "pytest", "prod", "10.23.6.0/29", "srv-ddi-06", "ddi-6")
        )

        commands = [
            PreviewDdiReservationCommand(
                "default", "pytest", "prod", "missing", ("bind",), "example.net"
            ),
            PreviewDdiReservationCommand("default", "pytest", "prod", "ddi-6", ("bind",), None),
            PreviewDdiReservationCommand(
                "default", "pytest", "prod", "ddi-6", ("bind",), "bad_zone"
            ),
            PreviewDdiReservationCommand(
                "default", "pytest", "prod", "ddi-6", ("bind",), "example.net", "bad-mac"
            ),
            PreviewDdiReservationCommand(
                "default", "pytest", "prod", "ddi-6", ("bind",), "example.net", None, 86401
            ),
        ]
        for command in commands:
            with pytest.raises(Exception) as exc_info:
                app.ipam_ddi_service.preview_reservation(command)
            assert str(exc_info.value)

        empty_service = IpamDdiService(
            app.ipam_repository,
            app.audit_repository,
            app.transaction_manager,
            (),
        )
        with pytest.raises(Exception) as exc_info:
            empty_service.preview_reservation(
                PreviewDdiReservationCommand(
                    "default", "pytest", "prod", "ddi-6", ("bind",), "example.net"
                )
            )
        assert "unavailable" in str(exc_info.value)
