from __future__ import annotations

import ipaddress

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ipam import (
    IpAddressRecord,
    IpAddressStatus,
    IpAggregate,
    IpRange,
    IpRangePurpose,
    Prefix,
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
        prefix = Prefix.create(tenant, "prod", "10.20.0.0/24")
        first = IpRange.create(tenant, "prod", prefix, "10.20.0.10", "10.20.0.20")
        overlap = IpRange.create(tenant, "prod", prefix, "10.20.0.15", "10.20.0.30")
        other_prefix = IpRange.create(
            tenant,
            "prod",
            Prefix.create(tenant, "prod", "10.21.0.0/24"),
            "10.21.0.15",
            "10.21.0.30",
        )
        other_vrf = IpRange.create(
            tenant,
            "lab",
            Prefix.create(tenant, "lab", "10.20.0.0/24"),
            "10.20.0.15",
            "10.20.0.30",
        )

        assert first.overlaps(overlap) is True
        assert first.overlaps(other_prefix) is False
        assert first.overlaps(other_vrf) is False
