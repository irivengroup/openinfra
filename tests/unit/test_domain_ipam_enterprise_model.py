from __future__ import annotations

import ipaddress

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpAddressFamily,
    BgpPeer,
    IpAddressRecord,
    IpAddressStatus,
    IpAggregate,
    IpamConflict,
    IpamConflictType,
    IpRange,
    IpRangePurpose,
    NetworkIdentifierPolicy,
    ObservedDhcpLease,
    ObservedDnsRecord,
    Prefix,
    Vlan,
    VlanGroup,
    VxlanVni,
)


class TestEnterpriseIpamDomain:
    def test_aggregate_range_and_address_are_validated(self) -> None:
        tenant = TenantId.from_value("default")
        aggregate = IpAggregate.create(tenant, "prod", "2001:db8::/48", "ipv6 aggregate")
        prefix = Prefix.create(tenant, "prod", "2001:db8:0:1::/64")
        ip_range = IpRange.create(
            tenant,
            "prod",
            prefix,
            "2001:db8:0:1::10",
            "2001:db8:0:1::20",
            "allocation",
            "servers",
        )
        record = IpAddressRecord.create(
            tenant,
            "prod",
            prefix,
            "2001:db8:0:1::10",
            "srv01.example.net",
            "eth0",
            "active",
        )

        assert aggregate.contains_network(ipaddress.ip_network("2001:db8:0:1::/64")) is True
        assert ip_range.purpose is IpRangePurpose.ALLOCATION
        assert record.status is IpAddressStatus.ACTIVE
        assert record.as_dict()["interface_name"] == "eth0"

    def test_invalid_enums_and_network_boundaries_are_rejected(self) -> None:
        tenant = TenantId.from_value("default")
        prefix = Prefix.create(tenant, "prod", "10.10.0.0/24")

        with pytest.raises(ValidationError):
            IpRangePurpose.from_value("pool")
        with pytest.raises(ValidationError):
            IpAddressStatus.from_value("leased")
        with pytest.raises(ValidationError):
            IpAggregate.create(tenant, "prod", "not-a-cidr")
        with pytest.raises(ValidationError):
            IpAggregate.create(tenant, "prod", "10.10.0.1/32")
        with pytest.raises(ValidationError):
            IpRange.create(tenant, "prod", prefix, "not-ip", "10.10.0.10")
        with pytest.raises(ValidationError):
            IpRange.create(tenant, "prod", prefix, "10.10.0.20", "10.10.0.10")
        with pytest.raises(ValidationError):
            IpRange.create(tenant, "prod", prefix, "10.10.0.1", "2001:db8::1")
        with pytest.raises(ValidationError):
            IpRange.create(tenant, "prod", prefix, "10.10.1.1", "10.10.1.2")
        with pytest.raises(ValidationError):
            IpAddressRecord.create(tenant, "prod", prefix, "bad-ip", "srv")
        with pytest.raises(ValidationError):
            IpAddressRecord.create(tenant, "prod", prefix, "2001:db8::1", "srv")
        with pytest.raises(ValidationError):
            IpAddressRecord.create(tenant, "prod", prefix, "10.10.0.0", "srv")
        with pytest.raises(ValidationError):
            IpAddressRecord.create(tenant, "prod", prefix, "10.10.0.10", " ")

    def test_range_overlap_is_vrf_and_prefix_scoped(self) -> None:
        tenant = TenantId.from_value("default")
        prefix = Prefix.create(tenant, "prod", "10.21.0.0/24")
        first = IpRange.create(tenant, "prod", prefix, "10.21.0.10", "10.21.0.20")
        overlap = IpRange.create(tenant, "prod", prefix, "10.21.0.15", "10.21.0.30")
        other_prefix = IpRange.create(
            tenant,
            "prod",
            Prefix.create(tenant, "prod", "10.21.1.0/24"),
            "10.21.1.15",
            "10.21.1.30",
        )
        other_vrf = IpRange.create(
            tenant,
            "lab",
            Prefix.create(tenant, "lab", "10.21.0.0/24"),
            "10.21.0.15",
            "10.21.0.30",
        )

        assert first.overlaps(overlap) is True
        assert first.overlaps(other_prefix) is False
        assert first.overlaps(other_vrf) is False


class TestIpamNetworkingDomain:
    def test_vlan_vxlan_asn_and_bgp_peer_contracts(self) -> None:
        tenant = TenantId.from_value("default")
        group = VlanGroup.create(tenant, "fabric", "dc1", "core switching")
        vni = VxlanVni.create(
            tenant,
            100100,
            "prod servers",
            "prod",
            ("65000:100", "65000:100"),
            ("65000:100",),
        )
        vlan = Vlan.create(tenant, "fabric", 100, "servers", "prod", 100100)
        asn = AutonomousSystem.create(tenant, 65000, "local fabric")
        peer = BgpPeer.create(
            tenant,
            "prod",
            65000,
            65100,
            "2001:db8::1",
            "ipv6",
            ("65000:100",),
            ("65100:100",),
        )

        assert group.as_dict()["scope"] == "DC1"
        assert vni.route_targets_import == ("65000:100",)
        assert vlan.as_dict()["vni"] == 100100
        assert asn.as_dict()["asn"] == 65000
        assert peer.address_family is BgpAddressFamily.IPV6
        assert peer.as_dict()["peer_address"] == "2001:db8::1"

    def test_network_identifier_policy_rejects_invalid_values(self) -> None:
        tenant = TenantId.from_value("default")
        with pytest.raises(ValidationError):
            NetworkIdentifierPolicy.validate_vlan_id(4095)
        with pytest.raises(ValidationError):
            NetworkIdentifierPolicy.validate_vni(0)
        with pytest.raises(ValidationError):
            NetworkIdentifierPolicy.validate_asn(0)
        with pytest.raises(ValidationError):
            NetworkIdentifierPolicy.normalize_route_targets(("not-a-rt",))
        with pytest.raises(ValidationError):
            NetworkIdentifierPolicy.normalize_route_targets(("65000:4294967296",))
        with pytest.raises(ValidationError):
            Vlan.create(tenant, "fabric", 100, "servers", None, 100100)
        with pytest.raises(ValidationError):
            BgpPeer.create(tenant, "prod", 65000, 65000, "192.0.2.1")
        with pytest.raises(ValidationError):
            BgpPeer.create(tenant, "prod", 65000, 65100, "bad-address")
        with pytest.raises(ValidationError):
            BgpPeer.create(tenant, "prod", 65000, 65100, "192.0.2.1", "ipv6")
        with pytest.raises(ValidationError):
            BgpAddressFamily.from_value("evpn")


class TestIpamConflictDomain:
    def test_conflict_and_observations_are_normalized(self) -> None:
        tenant = TenantId.from_value("default")
        conflict = IpamConflict.create(
            "duplicate_address",
            "critical",
            tenant,
            "prod",
            " address/10.0.0.10 ",
            ("  owner-a  ", "owner-b"),
            "  reconcile source of truth  ",
        )
        dns = ObservedDnsRecord.create(
            tenant,
            "prod",
            "Srv01.Example.Net.",
            "10.0.0.10",
            "Srv01.Example.Net.",
            "Discovery",
        )
        lease = ObservedDhcpLease.create(
            tenant,
            "prod",
            "10.0.0.0/24",
            "10.0.0.20",
            "AA-BB-CC-00-00-20",
            "Lease01.Example.Net.",
            "Dhcp",
        )

        assert (
            IpamConflictType.from_value("DUPLICATE_ADDRESS") is IpamConflictType.DUPLICATE_ADDRESS
        )
        assert (
            conflict.fingerprint
            == "default|prod|duplicate_address|address/10.0.0.10|owner-a;owner-b"
        )
        assert conflict.as_dict()["severity"] == "critical"
        assert dns.as_dict()["hostname"] == "srv01.example.net"
        assert dns.as_dict()["ptr_hostname"] == "srv01.example.net"
        assert lease.mac_address == "aa:bb:cc:00:00:20"
        assert lease.address_belongs_to_prefix() is True
        assert lease.as_dict()["active"] is True

    def test_conflict_observation_validation_rejects_invalid_values(self) -> None:
        tenant = TenantId.from_value("default")
        with pytest.raises(ValidationError):
            IpamConflictType.from_value("unknown")
        with pytest.raises(ValidationError):
            IpamConflict.create("duplicate_address", "error", tenant, "prod", " ", ("x",), "fix")
        with pytest.raises(ValidationError):
            IpamConflict.create("duplicate_address", "error", tenant, "prod", "ip", (), "fix")
        with pytest.raises(ValidationError):
            IpamConflict.create("duplicate_address", "error", tenant, "prod", "ip", ("x",), " ")
        with pytest.raises(ValidationError):
            ObservedDnsRecord.create(tenant, "prod", "bad host", "10.0.0.10")
        with pytest.raises(ValidationError):
            ObservedDnsRecord.create(tenant, "prod", "srv", "bad-ip")
        with pytest.raises(ValidationError):
            ObservedDnsRecord.create(tenant, "prod", "srv", "10.0.0.10", source=" ")
        with pytest.raises(ValidationError):
            ObservedDhcpLease.create(tenant, "prod", "bad-prefix", "10.0.0.10", "aa", "lease")
        with pytest.raises(ValidationError):
            ObservedDhcpLease.create(tenant, "prod", "10.0.0.0/24", "10.0.0.10", " ", "lease")
        with pytest.raises(ValidationError):
            ObservedDhcpLease.create(tenant, "prod", "10.0.0.0/24", "2001:db8::1", "aa", "lease")
