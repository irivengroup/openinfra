from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineAsnCommand,
    DefineBgpPeerCommand,
    DefineIpAggregateCommand,
    DefineIpPrefixCommand,
    DefineIpRangeCommand,
    DefineVlanCommand,
    DefineVlanGroupCommand,
    DefineVrfCommand,
    DefineVxlanVniCommand,
    IpamCapacityCommand,
    IpamNetworkBindingsCommand,
    IpamTopologyCommand,
    ObserveDhcpLeaseCommand,
    ObserveDnsRecordCommand,
    RegisterIpAddressCommand,
)
from openinfra.domain.common import ConflictError, NotFoundError, TenantId, ValidationError
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpPeer,
    IpAggregate,
    Vlan,
    VlanGroup,
    Vrf,
    VxlanVni,
)
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
    def test_networking_foundation_service_and_json_persistence(self, tmp_path: Path) -> None:
        data = tmp_path / "networking.json"
        app = ApplicationFactory().create_json_application(data)

        group = app.ipam_model_service.define_vlan_group(
            DefineVlanGroupCommand("default", "netops", "fabric", "dc1", "datacenter fabric")
        )
        vni = app.ipam_model_service.define_vxlan_vni(
            DefineVxlanVniCommand(
                "default",
                "netops",
                100100,
                "prod-vni",
                "prod",
                ("65000:100",),
                ("65000:100",),
                "prod overlay",
            )
        )
        vlan = app.ipam_model_service.define_vlan(
            DefineVlanCommand("default", "netops", "fabric", 100, "servers", "prod", 100100)
        )
        local = app.ipam_model_service.define_asn(
            DefineAsnCommand("default", "netops", 65000, "local")
        )
        remote = app.ipam_model_service.define_asn(
            DefineAsnCommand("default", "netops", 65100, "remote")
        )
        peer = app.ipam_model_service.define_bgp_peer(
            DefineBgpPeerCommand(
                "default",
                "netops",
                "prod",
                65000,
                65100,
                "192.0.2.1",
                None,
                ("65000:100",),
                ("65100:100",),
            )
        )
        report = app.ipam_model_service.network_bindings(
            IpamNetworkBindingsCommand("default", "prod")
        )
        reloaded = ApplicationFactory().create_json_application(data)
        persisted = reloaded.ipam_model_service.network_bindings(
            IpamNetworkBindingsCommand("default", "prod")
        )

        assert group["scope"] == "DC1"
        assert vni["route_targets_import"] == ["65000:100"]
        assert vlan["vlan_id"] == 100
        assert local["asn"] == 65000
        assert remote["asn"] == 65100
        assert peer["address_family"] == "ipv4"
        assert report.as_dict()["counts"]["bgp_peers"] == 1
        assert persisted.as_dict()["vxlan_vnis"][0]["vni"] == 100100

    def test_ipam_topology_consolidates_l3_l2_bgp_and_allocations(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "topology.json")
        app.ipam_model_service.define_vrf(
            DefineVrfCommand("default", "netops", "prod", "65000:100")
        )
        app.ipam_model_service.define_aggregate(
            DefineIpAggregateCommand("default", "netops", "prod", "10.90.0.0/16")
        )
        app.ipam_model_service.define_prefix(
            DefineIpPrefixCommand("default", "netops", "prod", "10.90.10.0/29")
        )
        app.ipam_model_service.define_range(
            DefineIpRangeCommand(
                "default",
                "netops",
                "prod",
                "10.90.10.0/29",
                "10.90.10.1",
                "10.90.10.4",
            )
        )
        app.ipam_model_service.register_address(
            RegisterIpAddressCommand(
                "default", "netops", "prod", "10.90.10.0/29", "10.90.10.2", "srv-topo"
            )
        )
        app.ipam_service.allocate(
            AllocateIpCommand("default", "netops", "prod", "10.90.10.0/29", "srv-auto", "topo-1")
        )
        app.ipam_model_service.define_vlan_group(
            DefineVlanGroupCommand("default", "netops", "fabric", "dc1")
        )
        app.ipam_model_service.define_vxlan_vni(
            DefineVxlanVniCommand("default", "netops", 100090, "prod-vni", "prod")
        )
        app.ipam_model_service.define_vlan(
            DefineVlanCommand("default", "netops", "fabric", 90, "prod", "prod", 100090)
        )
        app.ipam_model_service.define_asn(DefineAsnCommand("default", "netops", 65000, "local"))
        app.ipam_model_service.define_asn(DefineAsnCommand("default", "netops", 65090, "remote"))
        app.ipam_model_service.define_bgp_peer(
            DefineBgpPeerCommand("default", "netops", "prod", 65000, 65090, "192.0.2.90")
        )
        app.ipam_conflict_service.observe_dns(
            ObserveDnsRecordCommand(
                "default",
                "netops",
                "prod",
                "srv-topo.example.net",
                "10.90.10.2",
                "ptr-topo.example.net",
            )
        )
        app.ipam_conflict_service.observe_dhcp_lease(
            ObserveDhcpLeaseCommand(
                "default",
                "netops",
                "prod",
                "10.90.10.0/29",
                "10.90.10.3",
                "AA:BB:CC:90:00:03",
                "srv-dhcp",
            )
        )

        report = app.ipam_model_service.topology(IpamTopologyCommand("default", "netops", "prod"))
        payload = report.as_dict()
        node_kinds = {str(node["kind"]) for node in payload["nodes"]}
        relations = {edge["relation"] for edge in payload["edges"]}

        assert payload["summary"]["vrfs"] == 1
        assert payload["summary"]["prefixes"] == 1
        assert payload["summary"]["reservations"] == 1
        assert payload["summary"]["vlans"] == 1
        assert payload["summary"]["bgp_peers"] == 1
        assert payload["summary"]["dns_observations"] == 1
        assert payload["summary"]["dhcp_leases"] == 1
        assert (
            app.ipam_model_service.topology(IpamTopologyCommand("default", "netops")).as_dict()[
                "summary"
            ]["vrfs"]
            == 1
        )
        assert payload["integrity"]["valid"] is True
        assert {
            "vrf",
            "prefix",
            "range",
            "address_record",
            "reservation",
            "vlan",
            "vxlan_vni",
            "bgp_peer",
            "dns_observation",
            "dhcp_lease",
        } <= node_kinds
        assert {
            "contains",
            "assigns",
            "reserves",
            "maps_to_vni",
            "has_bgp_peer",
            "observes_dns",
            "observes_dhcp",
        } <= relations

    def test_networking_foundation_rejects_incoherent_relations(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "bad-networking.json")
        app.ipam_model_service.define_vxlan_vni(
            DefineVxlanVniCommand("default", "netops", 100100, "prod-vni", "prod")
        )
        with pytest.raises(ConflictError):
            app.ipam_model_service.define_vxlan_vni(
                DefineVxlanVniCommand("default", "netops", 100100, "lab-vni", "lab")
            )
        with pytest.raises(ConflictError):
            app.ipam_model_service.define_vlan(
                DefineVlanCommand("default", "netops", "fabric", 100, "bad", "lab", 100100)
            )
        with pytest.raises(NotFoundError):
            app.ipam_model_service.define_vlan(
                DefineVlanCommand("default", "netops", "fabric", 101, "missing", "prod", 100101)
            )
        with pytest.raises(NotFoundError):
            app.ipam_model_service.define_bgp_peer(
                DefineBgpPeerCommand("default", "netops", "prod", 65000, 65100, "192.0.2.1")
            )

    def test_json_repository_networking_methods(self, tmp_path: Path) -> None:
        store = JsonDocumentStore(tmp_path / "network-repo.json")
        repo = JsonIpamRepository(store)
        tenant = TenantId.from_value("default")
        group = repo.add_vlan_group(VlanGroup.create(tenant, "fabric", "dc1"))
        same_group = repo.add_vlan_group(VlanGroup.create(tenant, "fabric"))
        vni = repo.add_vxlan_vni(VxlanVni.create(tenant, 5000, "prod", "prod"))
        same_vni = repo.add_vxlan_vni(VxlanVni.create(tenant, 5000, "prod", "prod"))
        vlan = repo.add_vlan(Vlan.create(tenant, "fabric", 100, "servers", "prod", 5000))
        asn = repo.add_asn(AutonomousSystem.create(tenant, 65000, "local"))
        peer = repo.add_bgp_peer(BgpPeer.create(tenant, "prod", 65000, 65100, "192.0.2.1"))

        assert same_group.id == group.id
        assert repo.list_vlan_groups(tenant)[0].name.value == "fabric"
        assert same_vni.id == vni.id
        assert repo.find_vxlan_vni(tenant, 5000) == vni
        assert repo.list_vlans(tenant, "prod")[0] == vlan
        assert repo.find_asn(tenant, 65000) == asn
        assert repo.list_asns(tenant)[0] == asn
        assert repo.list_bgp_peers(tenant, "prod")[0] == peer

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
        assert (
            cli.run(
                [
                    "ipam",
                    "define-vxlan-vni",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--vni",
                    "100100",
                    "--name",
                    "prod-vni",
                    "--vrf",
                    "prod",
                    "--route-target-import",
                    "65000:100",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "define-vlan",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--group",
                    "fabric",
                    "--vlan-id",
                    "100",
                    "--name",
                    "servers",
                    "--vrf",
                    "prod",
                    "--vni",
                    "100100",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "define-asn",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--asn",
                    "65000",
                    "--name",
                    "local",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "define-asn",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--asn",
                    "65100",
                    "--name",
                    "remote",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "define-bgp-peer",
                    "--data",
                    str(data),
                    "--tenant",
                    "default",
                    "--vrf",
                    "prod",
                    "--local-asn",
                    "65000",
                    "--remote-asn",
                    "65100",
                    "--peer-address",
                    "192.0.2.1",
                ]
            )
            == 0
        )
        assert (
            cli.run(
                [
                    "ipam",
                    "network-bindings",
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
                    "topology",
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
        captured = capsys.readouterr()
        assert "172.16.10.0/24" in captured.out
        assert '"kind": "prefix"' in captured.out

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
            client.post_json(
                base_url + "/api/v1/ipam/vlan-groups", {"tenant_id": "default", "name": "fabric"}
            )
            client.post_json(
                base_url + "/api/v1/ipam/vxlan-vnis",
                {
                    "tenant_id": "default",
                    "vni": 100100,
                    "name": "prod-vni",
                    "vrf": "prod",
                    "route_targets_import": ["65000:100"],
                },
            )
            client.post_json(
                base_url + "/api/v1/ipam/vlans",
                {
                    "tenant_id": "default",
                    "group": "fabric",
                    "vlan_id": 100,
                    "name": "servers",
                    "vrf": "prod",
                    "vni": 100100,
                },
            )
            client.post_json(
                base_url + "/api/v1/ipam/asns",
                {"tenant_id": "default", "asn": 65000, "name": "local"},
            )
            client.post_json(
                base_url + "/api/v1/ipam/asns",
                {"tenant_id": "default", "asn": 65100, "name": "remote"},
            )
            client.post_json(
                base_url + "/api/v1/ipam/bgp-peers",
                {
                    "tenant_id": "default",
                    "vrf": "prod",
                    "local_asn": 65000,
                    "remote_asn": 65100,
                    "peer_address": "192.0.2.1",
                },
            )
            bindings = client.get_json(
                base_url + "/api/v1/ipam/network-bindings?tenant_id=default&vrf=prod"
            )
            topology = client.get_json(
                base_url + "/api/v1/ipam/topology?tenant_id=default&vrf=prod"
            )

            assert vrf["name"] == "prod"
            assert aggregate["cidr"] == "198.51.100.0/24"
            assert prefix["family"] == 4
            assert ip_range["purpose"] == "allocation"
            assert address["hostname"] == "srv-api"
            assert prefixes["items"][0]["cidr"] == "198.51.100.0/25"
            assert capacity["reserved_addresses"] == 1
            assert bindings["counts"]["vlans"] == 1
            assert bindings["counts"]["bgp_peers"] == 1
            assert topology["summary"]["vlans"] == 1
            assert topology["summary"]["bgp_peers"] == 1
            assert topology["integrity"]["valid"] is True
        finally:
            server.shutdown()
            thread.join(timeout=5)
