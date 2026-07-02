from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Self

from openinfra.domain.common import Code, EntityId, Name, TenantId, ValidationError


@dataclass(frozen=True, slots=True)
class Vrf:
    id: EntityId
    tenant_id: TenantId
    name: Name
    route_distinguisher: str | None

    @classmethod
    def create(cls, tenant_id: TenantId, name: str, route_distinguisher: str | None = None) -> Self:
        rd = route_distinguisher.strip() if route_distinguisher else None
        if rd == "":
            raise ValidationError("route distinguisher cannot be blank")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=Name.from_value(name, "vrf name"),
            route_distinguisher=rd,
        )


@dataclass(frozen=True, slots=True)
class Prefix:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    network: ipaddress.IPv4Network | ipaddress.IPv6Network
    description: str

    @classmethod
    def create(cls, tenant_id: TenantId, vrf_name: str, cidr: str, description: str = "") -> Self:
        try:
            network = ipaddress.ip_network(cidr, strict=True)
        except ValueError as exc:
            raise ValidationError(f"invalid prefix: {cidr}") from exc
        if network.prefixlen == network.max_prefixlen:
            raise ValidationError("prefix must contain more than one address")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            network=network,
            description=description.strip(),
        )

    @property
    def first_usable_int(self) -> int:
        if self.network.version == 4 and self.network.num_addresses > 2:
            return int(self.network.network_address) + 1
        return int(self.network.network_address)

    @property
    def last_usable_int(self) -> int:
        if self.network.version == 4 and self.network.num_addresses > 2:
            return int(self.network.broadcast_address) - 1
        return int(self.network.broadcast_address)

    def contains(self, address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        return address in self.network


@dataclass(frozen=True, slots=True)
class IpReservation:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    prefix: str
    address: ipaddress.IPv4Address | ipaddress.IPv6Address
    hostname: str
    idempotency_key: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        prefix: Prefix,
        address: str,
        hostname: str,
        idempotency_key: str,
    ) -> Self:
        normalized_hostname = hostname.strip().lower()
        normalized_key = idempotency_key.strip()
        if not normalized_hostname:
            raise ValidationError("hostname is mandatory")
        if not normalized_key:
            raise ValidationError("idempotency key is mandatory")
        try:
            ip_address = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValidationError(f"invalid ip address: {address}") from exc
        if ip_address.version != prefix.network.version:
            raise ValidationError("address family does not match prefix family")
        if not prefix.contains(ip_address):
            raise ValidationError("address does not belong to prefix")
        address_int = int(ip_address)
        if not prefix.first_usable_int <= address_int <= prefix.last_usable_int:
            raise ValidationError("address is not usable in prefix")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            prefix=str(prefix.network),
            address=ip_address,
            hostname=normalized_hostname,
            idempotency_key=normalized_key,
        )


@dataclass(frozen=True, slots=True)
class AllocationRequest:
    tenant_id: TenantId
    vrf_name: Name
    prefix_cidr: str
    hostname: str
    idempotency_key: str

    @classmethod
    def create(
        cls,
        tenant_id: str,
        vrf_name: str,
        prefix_cidr: str,
        hostname: str,
        idempotency_key: str,
    ) -> Self:
        return cls(
            tenant_id=TenantId.from_value(tenant_id),
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            prefix_cidr=prefix_cidr.strip(),
            hostname=hostname.strip(),
            idempotency_key=idempotency_key.strip(),
        )


@dataclass(frozen=True, slots=True)
class AllocationResult:
    reservation: IpReservation
    created: bool

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "tenant_id": self.reservation.tenant_id.value,
            "vrf": self.reservation.vrf_name.value,
            "prefix": self.reservation.prefix,
            "address": str(self.reservation.address),
            "hostname": self.reservation.hostname,
            "idempotency_key": self.reservation.idempotency_key,
            "created": self.created,
        }


class IpAllocationPolicy:
    def next_available_address(
        self,
        prefix: Prefix,
        allocated_addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address],
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        allocated_ints = {int(address) for address in allocated_addresses}
        current = prefix.first_usable_int
        while current <= prefix.last_usable_int:
            if current not in allocated_ints:
                return ipaddress.ip_address(current)
            current += 1
        raise ValidationError(f"prefix is exhausted: {prefix.network}")

    def assert_no_conflict(
        self,
        requested: ipaddress.IPv4Address | ipaddress.IPv6Address,
        allocated_addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address],
    ) -> None:
        if requested in allocated_addresses:
            raise ValidationError(f"ip address already allocated: {requested}")


@dataclass(frozen=True, slots=True)
class NetworkInterface:
    id: EntityId
    tenant_id: TenantId
    equipment_asset_tag: Code
    name: Name
    mac_address: str | None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        equipment_asset_tag: str,
        name: str,
        mac_address: str | None = None,
    ) -> Self:
        mac = mac_address.strip().lower() if mac_address else None
        if mac and not _MacAddressValidator(mac).is_valid():
            raise ValidationError("invalid mac address")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            equipment_asset_tag=Code.from_value(equipment_asset_tag, "asset tag"),
            name=Name.from_value(name, "interface name"),
            mac_address=mac,
        )


class _MacAddressValidator:
    def __init__(self, value: str) -> None:
        self._value = value

    def is_valid(self) -> bool:
        chunks = self._value.split(":")
        return len(chunks) == 6 and all(len(chunk) == 2 and self._is_hex(chunk) for chunk in chunks)

    def _is_hex(self, value: str) -> bool:
        try:
            int(value, 16)
        except ValueError:
            return False
        return True
