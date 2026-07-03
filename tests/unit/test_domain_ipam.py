from __future__ import annotations

import ipaddress

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ipam import IpAllocationPolicy, IpRange, IpReservation, Prefix


class TestIpamDomain:
    def test_prefix_computes_ipv4_usable_range(self) -> None:
        prefix = Prefix.create(TenantId.from_value("default"), "default", "192.0.2.0/30")

        assert str(ipaddress.ip_address(prefix.first_usable_int)) == "192.0.2.1"
        assert str(ipaddress.ip_address(prefix.last_usable_int)) == "192.0.2.2"

    def test_reservation_rejects_network_address(self) -> None:
        tenant = TenantId.from_value("default")
        prefix = Prefix.create(tenant, "default", "192.0.2.0/24")

        with pytest.raises(ValidationError):
            IpReservation.create(tenant, "default", prefix, "192.0.2.0", "srv", "key")

    def test_policy_returns_next_free_ip(self) -> None:
        tenant = TenantId.from_value("default")
        prefix = Prefix.create(tenant, "default", "192.0.2.0/29")
        policy = IpAllocationPolicy()

        result = policy.next_available_address(prefix, {ipaddress.ip_address("192.0.2.1")})

        assert str(result) == "192.0.2.2"

    def test_policy_detects_exhausted_prefix(self) -> None:
        tenant = TenantId.from_value("default")
        prefix = Prefix.create(tenant, "default", "192.0.2.0/30")
        allocated = {ipaddress.ip_address("192.0.2.1"), ipaddress.ip_address("192.0.2.2")}

        with pytest.raises(ValidationError):
            IpAllocationPolicy().next_available_address(prefix, allocated)


def test_allocation_policy_respects_allocation_and_exclusion_ranges() -> None:
    tenant = TenantId.from_value("default")
    prefix = Prefix.create(tenant, "prod", "10.90.0.0/24")
    allocation_pool = IpRange.create(
        tenant,
        "prod",
        prefix,
        "10.90.0.10",
        "10.90.0.20",
        "allocation",
    )
    exclusion = IpRange.create(
        tenant,
        "prod",
        prefix,
        "10.90.0.10",
        "10.90.0.12",
        "exclusion",
    )

    address = IpAllocationPolicy().next_available_address(
        prefix,
        {ipaddress.ip_address("10.90.0.13")},
        (allocation_pool, exclusion),
    )

    assert str(address) == "10.90.0.14"


def test_allocation_policy_treats_reservation_ranges_as_blocked_capacity() -> None:
    tenant = TenantId.from_value("default")
    prefix = Prefix.create(tenant, "prod", "2001:db8:5::/124")
    reserved = IpRange.create(
        tenant,
        "prod",
        prefix,
        "2001:db8:5::",
        "2001:db8:5::2",
        "reservation",
    )

    address = IpAllocationPolicy().next_available_address(prefix, set(), (reserved,))

    assert str(address) == "2001:db8:5::3"
