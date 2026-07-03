from __future__ import annotations

import json
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import (
    DefineIpPrefixCommand,
    DetectIpamConflictsCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
    RegisterIpAddressCommand,
)
from openinfra.domain.common import TenantId
from openinfra.domain.ipam import IpRange, IpReservation, Prefix
from openinfra.interfaces.cli import OpenInfraCLI


class TestIpamConflictServices:
    def _app(self, tmp_path: Path):
        return ApplicationFactory().create_json_application(tmp_path / "state.json")

    def test_conflict_engine_detects_ipam_dns_and_dhcp_anomalies(self, tmp_path: Path) -> None:
        app = self._app(tmp_path)
        tenant = TenantId.from_value("default")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "tester", "prod", "10.50.0.0/24")
        )
        prefix = Prefix.create(tenant, "prod", "10.50.0.0/24")
        app.ipam_repository.get_or_create_prefix(Prefix.create(tenant, "prod", "10.50.0.128/25"))
        app.ipam_repository.add_range(
            IpRange.create(tenant, "prod", prefix, "10.50.0.10", "10.50.0.20")
        )
        app.ipam_repository.add_range(
            IpRange.create(tenant, "prod", prefix, "10.50.0.15", "10.50.0.30")
        )
        app.ipam_model_service.register_address(
            RegisterIpAddressCommand(
                "default", "tester", "prod", "10.50.0.0/24", "10.50.0.10", "app-a"
            )
        )
        app.ipam_repository.add_reservation(
            IpReservation.create(tenant, "prod", prefix, "10.50.0.11", "reserved-a", "idem-1")
        )
        app.ipam_conflict_service.observe_dns(
            ObserveDnsRecordCommand(
                "default", "tester", "prod", "web-a.example.net", "10.99.0.5", "old.example.net"
            )
        )
        app.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                "default",
                "tester",
                "prod",
                "10.50.0.0/24",
                "10.50.0.10",
                "AA:BB:CC:00:00:01",
                "rogue-host",
            )
        )
        app.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                "default",
                "tester",
                "prod",
                "10.50.0.0/24",
                "10.50.1.10",
                "AA:BB:CC:00:00:02",
                "outside-host",
            )
        )

        report = app.ipam_conflict_service.detect(
            DetectIpamConflictsCommand("default", "tester", "prod")
        )

        types = {item["type"] for item in report.conflicts}
        assert {
            "prefix_overlap",
            "range_overlap",
            "duplicate_address",
            "dns_ptr_divergence",
            "address_out_of_prefix",
            "lease_conflict",
        }.issubset(types)
        assert report.total >= 6
        assert report.by_severity["critical"] >= 3

    def test_cli_conflict_detection_smoke(self, tmp_path: Path, capsys: object) -> None:
        state = tmp_path / "state.json"
        cli = OpenInfraCLI()
        assert (
            cli.run(
                [
                    "ipam",
                    "define-prefix",
                    "--data",
                    str(state),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--cidr",
                    "10.51.0.0/24",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "register-address",
                    "--data",
                    str(state),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--prefix",
                    "10.51.0.0/24",
                    "--address",
                    "10.51.0.10",
                    "--hostname",
                    "api-a",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "observe-dhcp-lease",
                    "--data",
                    str(state),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--prefix",
                    "10.51.0.0/24",
                    "--address",
                    "10.51.0.10",
                    "--mac-address",
                    "aa:bb:cc:00:51:10",
                    "--hostname",
                    "rogue-a",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "observe-dns",
                    "--data",
                    str(state),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--hostname",
                    "api-a.example.net",
                    "--address",
                    "10.51.0.10",
                    "--ptr-hostname",
                    "legacy.example.net",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "detect-conflicts",
                    "--data",
                    str(state),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                ]
            )
            == 0
        )
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip().splitlines()[-1])
        assert payload["total"] >= 3
        assert {item["type"] for item in payload["conflicts"]} >= {
            "duplicate_address",
            "lease_conflict",
            "dns_ptr_divergence",
        }
