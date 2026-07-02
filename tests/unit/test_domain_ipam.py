from __future__ import annotations

import ipaddress

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ipam import IpAllocationPolicy, IpReservation, Prefix


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
