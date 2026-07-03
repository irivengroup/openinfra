from __future__ import annotations

import ipaddress

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.ipam import (
    AllocationRequest,
    AllocationResult,
    IpAllocationPolicy,
    IpReservation,
    NetworkInterface,
    Prefix,
    Vrf,
)


def test_ipam_domain_validation_and_exhaustion_edges() -> None:
    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError):
        Vrf.create(tenant, "default", " ")
    with pytest.raises(ValidationError):
        Prefix.create(tenant, "default", "10.0.0.1/24")
    with pytest.raises(ValidationError):
        Prefix.create(tenant, "default", "10.0.0.1/32")

    prefix = Prefix.create(tenant, "default", "10.0.0.0/30", " edge ")
    assert prefix.description == "edge"
    assert prefix.first_usable_int == int(ipaddress.ip_address("10.0.0.1"))
    assert prefix.last_usable_int == int(ipaddress.ip_address("10.0.0.2"))
    ipv6_prefix = Prefix.create(tenant, "default", "2001:db8::/127")
    assert ipv6_prefix.first_usable_int == int(ipaddress.ip_address("2001:db8::"))

    with pytest.raises(ValidationError):
        IpReservation.create(tenant, "default", prefix, "10.0.0.1", " ", "key")
    with pytest.raises(ValidationError):
        IpReservation.create(tenant, "default", prefix, "10.0.0.1", "srv", " ")
    with pytest.raises(ValidationError):
        IpReservation.create(tenant, "default", prefix, "not-ip", "srv", "key")
    with pytest.raises(ValidationError):
        IpReservation.create(tenant, "default", prefix, "2001:db8::1", "srv", "key")
    with pytest.raises(ValidationError):
        IpReservation.create(tenant, "default", prefix, "10.0.0.3", "srv", "key")
    with pytest.raises(ValidationError):
        IpReservation.create(tenant, "default", prefix, "10.0.1.1", "srv", "key")

    policy = IpAllocationPolicy()
    with pytest.raises(ValidationError):
        policy.assert_no_conflict(
            ipaddress.ip_address("10.0.0.1"), {ipaddress.ip_address("10.0.0.1")}
        )
    with pytest.raises(ValidationError):
        policy.next_available_address(
            prefix, {ipaddress.ip_address("10.0.0.1"), ipaddress.ip_address("10.0.0.2")}
        )

    request = AllocationRequest.create("default", "default", " 10.0.0.0/30 ", " srv ", " key ")
    reservation = IpReservation.create(
        tenant, "default", prefix, "10.0.0.1", request.hostname, request.idempotency_key
    )
    result = AllocationResult(reservation, created=True)
    assert result.as_dict()["created"] is True
    assert result.as_dict()["hostname"] == "srv"

    assert (
        NetworkInterface.create(tenant, "ASSET-1", "eth0", "AA:BB:CC:DD:EE:FF").mac_address
        == "aa:bb:cc:dd:ee:ff"
    )
    with pytest.raises(ValidationError):
        NetworkInterface.create(tenant, "ASSET-1", "eth0", "zz:bb:cc:dd:ee:ff")
