from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import (
    DefineIpAggregateCommand,
    DefineIpPrefixCommand,
    DefineIpRangeCommand,
    DefineVrfCommand,
    IpamCapacityCommand,
    RegisterIpAddressCommand,
)
from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.domain.ipam import IpAggregate, Vrf
from openinfra.infrastructure.json_store import JsonDocumentStore, JsonIpamRepository
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


class _HttpClient:
    def get_json(self, url: str) -> dict[str, object]:
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


class TestIpamEnterpriseModelServices:
    def test_vrf_aggregate_prefix_range_address_capacity_and_persistence(
        self, tmp_path: Path
    ) -> None:
        data = tmp_path / "state.json"
        app = ApplicationFactory().create_json_application(data)

        vrf = app.ipam_model_service.define_vrf(
            DefineVrfCommand("default", "test", "prod", "65000:100")
        )
        aggregate = app.ipam_model_service.define_aggregate(
            DefineIpAggregateCommand("default", "test", "prod", "10.64.0.0/12", "prod agg")
        )
        prefix = app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "test", "prod", "10.64.10.0/24", "servers")
        )
        ip_range = app.ipam_model_service.define_range(
            DefineIpRangeCommand(
                "default",
                "test",
                "prod",
                "10.64.10.0/24",
                "10.64.10.10",
                "10.64.10.20",
                "allocation",
                "rack r42",
            )
        )
        record = app.ipam_model_service.register_address(
            RegisterIpAddressCommand(
                "default",
                "test",
                "prod",
                "10.64.10.0/24",
                "10.64.10.10",
                "srv01",
                "eth0",
                "active",
            )
        )
        capacity = app.ipam_model_service.capacity(
            IpamCapacityCommand("default", "prod", "10.64.10.0/24")
        )
        reloaded = ApplicationFactory().create_json_application(data)
        persisted = reloaded.ipam_model_service.list_prefixes("default", "prod")

        assert vrf["route_distinguisher"] == "65000:100"
        assert aggregate["family"] == 4
        assert prefix["first_usable"] == "10.64.10.1"
        assert ip_range["end"] == "10.64.10.20"
        assert record["status"] == "active"
        assert capacity.reserved_addresses == 1
        assert capacity.free_addresses == 253
        assert persisted[0]["cidr"] == "10.64.10.0/24"

    def test_overlap_is_rejected_only_inside_same_vrf(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "test", "prod", "10.70.0.0/24")
        )
        same_prefix = DefineIpPrefixCommand("default", "test", "prod", "10.70.0.0/24")
        with pytest.raises(ConflictError):
            app.ipam_model_service.define_prefix(
                DefineIpPrefixCommand("default", "test", "prod", "10.70.0.128/25")
            )
        assert app.ipam_model_service.define_prefix(same_prefix)["cidr"] == "10.70.0.0/24"
        assert (
            app.ipam_model_service.define_prefix(
                DefineIpPrefixCommand("default", "test", "lab", "10.70.0.128/25")
            )["vrf"]
            == "lab"
        )

    def test_range_overlap_and_address_validation_errors_are_controlled(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        app.ipam_model_service.define_range(
            DefineIpRangeCommand(
                "default", "test", "prod", "10.80.0.0/24", "10.80.0.10", "10.80.0.20"
            )
        )
        with pytest.raises(ConflictError):
            app.ipam_model_service.define_range(
                DefineIpRangeCommand(
                    "default", "test", "prod", "10.80.0.0/24", "10.80.0.15", "10.80.0.30"
                )
            )
        with pytest.raises(ValidationError):
            app.ipam_model_service.register_address(
                RegisterIpAddressCommand(
                    "default", "test", "prod", "10.80.0.0/24", "10.80.1.10", "srv"
                )
            )

    def test_json_repository_ipam_model_methods(self, tmp_path: Path) -> None:
        store = JsonDocumentStore(tmp_path / "repo.json")
        repo = JsonIpamRepository(store)
        tenant = TenantId.from_value("default")
        vrf = repo.add_or_get_vrf(Vrf.create(tenant, "blue", "65000:200"))
        same_vrf = repo.add_or_get_vrf(Vrf.create(tenant, "blue"))
        aggregate = repo.add_aggregate(IpAggregate.create(tenant, "blue", "192.0.2.0/24"))
        same_aggregate = repo.add_aggregate(IpAggregate.create(tenant, "blue", "192.0.2.0/24"))

        assert same_vrf.id == vrf.id
        assert repo.list_vrfs(tenant)[0].name.value == "blue"
        assert same_aggregate.id == aggregate.id
        assert repo.list_aggregates(tenant, "blue")[0].network == aggregate.network
        with pytest.raises(ConflictError):
            repo.add_vrf(vrf)

    def test_cli_ipam_model_lifecycle(self, tmp_path: Path, capsys: object) -> None:
        data = tmp_path / "cli.json"
        cli = OpenInfraCLI()

        assert (
            cli.run(
                ["ipam", "define-vrf", "--data", str(data), "--tenant", "default", "--name", "prod"]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "define-aggregate",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--cidr",
                    "172.16.0.0/12",
                ]
            )
            == 0
        )
        assert (
            cli.run(
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
                    "172.16.10.0/24",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "define-range",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--prefix",
                    "172.16.10.0/24",
                    "--start",
                    "172.16.10.10",
                    "--end",
                    "172.16.10.11",
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
                    str(data),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--prefix",
                    "172.16.10.0/24",
                    "--address",
                    "172.16.10.10",
                    "--hostname",
                    "srv-cli",
                    "--interface-name",
                    "eth0",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "list-prefixes",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "capacity",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--prefix",
                    "172.16.10.0/24",
                ]
            )
            == 0
        )
        captured = capsys.readouterr()
        assert "172.16.10.0/24" in captured.out

    def test_http_ipam_model_endpoints(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "api.json")
        server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = _HttpClient()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            vrf = client.post_json(
                base_url + "/api/v1/ipam/vrfs",
                {"tenant_id": "default", "name": "prod", "route_distinguisher": "65000:300"},
            )
            aggregate = client.post_json(
                base_url + "/api/v1/ipam/aggregates",
                {"tenant_id": "default", "vrf": "prod", "cidr": "198.51.100.0/24"},
            )
            prefix = client.post_json(
                base_url + "/api/v1/ipam/prefixes",
                {"tenant_id": "default", "vrf": "prod", "cidr": "198.51.100.0/25"},
            )
            ip_range = client.post_json(
                base_url + "/api/v1/ipam/ranges",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "prefix": "198.51.100.0/25",
                    "start": "198.51.100.10",
                    "end": "198.51.100.20",
                },
            )
            address = client.post_json(
                base_url + "/api/v1/ipam/addresses",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "prefix": "198.51.100.0/25",
                    "address": "198.51.100.10",
                    "hostname": "srv-api",
                    "status": "reserved",
                },
            )
            prefixes = client.get_json(
                base_url + "/api/v1/ipam/prefixes?tenant_id=default&vrf=prod"
            )
            capacity = client.get_json(
                base_url + "/api/v1/ipam/capacity?tenant_id=default&vrf=prod&prefix=198.51.100.0/25"
            )

            assert vrf["name"] == "prod"
            assert aggregate["cidr"] == "198.51.100.0/24"
            assert prefix["family"] == 4
            assert ip_range["purpose"] == "allocation"
            assert address["hostname"] == "srv-api"
            assert prefixes["items"][0]["cidr"] == "198.51.100.0/25"
            assert capacity["reserved_addresses"] == 1
        finally:
            server.shutdown()
            thread.join(timeout=5)
