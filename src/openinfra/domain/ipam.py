from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from openinfra.domain.common import Code, EntityId, Name, Severity, TenantId, ValidationError


class BgpAddressFamily(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("bgp address family must be ipv4 or ipv6") from exc


class NetworkIdentifierPolicy:
    @staticmethod
    def validate_vlan_id(value: int) -> int:
        if not 1 <= value <= 4094:
            raise ValidationError("vlan id must be between 1 and 4094")
        return value

    @staticmethod
    def validate_vni(value: int) -> int:
        if not 1 <= value <= 16777215:
            raise ValidationError("vxlan vni must be between 1 and 16777215")
        return value

    @staticmethod
    def validate_asn(value: int) -> int:
        if not 1 <= value <= 4294967295:
            raise ValidationError("asn must be between 1 and 4294967295")
        return value

    @staticmethod
    def normalize_route_targets(values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            candidate = value.strip()
            pieces = candidate.split(":")
            if len(pieces) != 2 or not pieces[0].isdigit() or not pieces[1].isdigit():
                raise ValidationError("route target must use ASN:NUMBER format")
            asn = NetworkIdentifierPolicy.validate_asn(int(pieces[0]))
            number = int(pieces[1])
            if not 0 <= number <= 4294967295:
                raise ValidationError("route target number must be between 0 and 4294967295")
            normalized.append(f"{asn}:{number}")
        return tuple(dict.fromkeys(normalized))


@dataclass(frozen=True, slots=True)
class VlanGroup:
    id: EntityId
    tenant_id: TenantId
    name: Name
    scope: Code | None
    description: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        scope: str | None = None,
        description: str = "",
    ) -> Self:
        normalized_scope = Code.from_value(scope, "vlan group scope") if scope else None
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=Name.from_value(name, "vlan group name"),
            scope=normalized_scope,
            description=description.strip(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "name": self.name.value,
            "scope": self.scope.value if self.scope else None,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class VxlanVni:
    id: EntityId
    tenant_id: TenantId
    vni: int
    name: Name
    vrf_name: Name
    route_targets_import: tuple[str, ...]
    route_targets_export: tuple[str, ...]
    description: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vni: int,
        name: str,
        vrf_name: str,
        route_targets_import: tuple[str, ...] = (),
        route_targets_export: tuple[str, ...] = (),
        description: str = "",
    ) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vni=NetworkIdentifierPolicy.validate_vni(vni),
            name=Name.from_value(name, "vni name"),
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            route_targets_import=NetworkIdentifierPolicy.normalize_route_targets(
                route_targets_import
            ),
            route_targets_export=NetworkIdentifierPolicy.normalize_route_targets(
                route_targets_export
            ),
            description=description.strip(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "vni": self.vni,
            "name": self.name.value,
            "vrf": self.vrf_name.value,
            "route_targets_import": list(self.route_targets_import),
            "route_targets_export": list(self.route_targets_export),
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class Vlan:
    id: EntityId
    tenant_id: TenantId
    group_name: Name
    vlan_id: int
    name: Name
    vrf_name: Name | None
    vni: int | None
    description: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        group_name: str,
        vlan_id: int,
        name: str,
        vrf_name: str | None = None,
        vni: int | None = None,
        description: str = "",
    ) -> Self:
        normalized_vrf = Name.from_value(vrf_name, "vrf name") if vrf_name else None
        normalized_vni = NetworkIdentifierPolicy.validate_vni(vni) if vni is not None else None
        if normalized_vni is not None and normalized_vrf is None:
            raise ValidationError("vlan with vni must be attached to a vrf")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            group_name=Name.from_value(group_name, "vlan group name"),
            vlan_id=NetworkIdentifierPolicy.validate_vlan_id(vlan_id),
            name=Name.from_value(name, "vlan name"),
            vrf_name=normalized_vrf,
            vni=normalized_vni,
            description=description.strip(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "group": self.group_name.value,
            "vlan_id": self.vlan_id,
            "name": self.name.value,
            "vrf": self.vrf_name.value if self.vrf_name else None,
            "vni": self.vni,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class AutonomousSystem:
    id: EntityId
    tenant_id: TenantId
    number: int
    name: Name
    description: str

    @classmethod
    def create(cls, tenant_id: TenantId, number: int, name: str, description: str = "") -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            number=NetworkIdentifierPolicy.validate_asn(number),
            name=Name.from_value(name, "asn name"),
            description=description.strip(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "asn": self.number,
            "name": self.name.value,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class BgpPeer:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    local_asn: int
    remote_asn: int
    peer_address: ipaddress.IPv4Address | ipaddress.IPv6Address
    address_family: BgpAddressFamily
    route_targets_import: tuple[str, ...]
    route_targets_export: tuple[str, ...]
    description: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        local_asn: int,
        remote_asn: int,
        peer_address: str,
        address_family: str | None = None,
        route_targets_import: tuple[str, ...] = (),
        route_targets_export: tuple[str, ...] = (),
        description: str = "",
    ) -> Self:
        local = NetworkIdentifierPolicy.validate_asn(local_asn)
        remote = NetworkIdentifierPolicy.validate_asn(remote_asn)
        if local == remote:
            raise ValidationError("bgp local and remote asn must be distinct")
        try:
            parsed_address = ipaddress.ip_address(peer_address.strip())
        except ValueError as exc:
            raise ValidationError("invalid bgp peer address") from exc
        family = BgpAddressFamily.from_value(
            address_family if address_family else f"ipv{parsed_address.version}"
        )
        if (family == BgpAddressFamily.IPV4 and parsed_address.version != 4) or (
            family == BgpAddressFamily.IPV6 and parsed_address.version != 6
        ):
            raise ValidationError("bgp address family must match peer address")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            local_asn=local,
            remote_asn=remote,
            peer_address=parsed_address,
            address_family=family,
            route_targets_import=NetworkIdentifierPolicy.normalize_route_targets(
                route_targets_import
            ),
            route_targets_export=NetworkIdentifierPolicy.normalize_route_targets(
                route_targets_export
            ),
            description=description.strip(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "vrf": self.vrf_name.value,
            "local_asn": self.local_asn,
            "remote_asn": self.remote_asn,
            "peer_address": str(self.peer_address),
            "address_family": self.address_family.value,
            "route_targets_import": list(self.route_targets_import),
            "route_targets_export": list(self.route_targets_export),
            "description": self.description,
        }


class IpamConflictType(StrEnum):
    PREFIX_OVERLAP = "prefix_overlap"
    RANGE_OVERLAP = "range_overlap"
    DUPLICATE_ADDRESS = "duplicate_address"
    ADDRESS_OUT_OF_PREFIX = "address_out_of_prefix"
    LEASE_CONFLICT = "lease_conflict"
    DNS_PTR_DIVERGENCE = "dns_ptr_divergence"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("ipam conflict type is invalid") from exc


@dataclass(frozen=True, slots=True)
class IpamConflict:
    conflict_type: IpamConflictType
    severity: Severity
    tenant_id: TenantId
    vrf_name: Name
    impacted_object: str
    evidence: tuple[str, ...]
    recommended_action: str

    @classmethod
    def create(
        cls,
        conflict_type: str,
        severity: str,
        tenant_id: TenantId,
        vrf_name: str,
        impacted_object: str,
        evidence: tuple[str, ...],
        recommended_action: str,
    ) -> Self:
        normalized_object = impacted_object.strip()
        normalized_action = " ".join(recommended_action.strip().split())
        normalized_evidence = tuple(
            item.strip() for item in evidence if item is not None and item.strip()
        )
        if not normalized_object:
            raise ValidationError("ipam conflict impacted object is mandatory")
        if not normalized_evidence:
            raise ValidationError("ipam conflict evidence is mandatory")
        if not normalized_action:
            raise ValidationError("ipam conflict recommended action is mandatory")
        return cls(
            conflict_type=IpamConflictType.from_value(conflict_type),
            severity=Severity(severity.strip().lower()),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            impacted_object=normalized_object,
            evidence=normalized_evidence,
            recommended_action=normalized_action,
        )

    @property
    def fingerprint(self) -> str:
        return "|".join(
            (
                self.tenant_id.value,
                self.vrf_name.value,
                self.conflict_type.value,
                self.impacted_object,
                ";".join(self.evidence),
            )
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "type": self.conflict_type.value,
            "severity": self.severity.value,
            "tenant_id": self.tenant_id.value,
            "vrf": self.vrf_name.value,
            "impacted_object": self.impacted_object,
            "evidence": list(self.evidence),
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True, slots=True)
class ObservedDnsRecord:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    hostname: str
    address: ipaddress.IPv4Address | ipaddress.IPv6Address
    ptr_hostname: str | None
    source: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        hostname: str,
        address: str,
        ptr_hostname: str | None = None,
        source: str = "manual",
    ) -> Self:
        normalized_hostname = cls._normalize_hostname(hostname, "dns hostname")
        normalized_ptr = (
            cls._normalize_hostname(ptr_hostname, "ptr hostname") if ptr_hostname else None
        )
        normalized_source = cls._normalize_source(source)
        try:
            parsed_address = ipaddress.ip_address(address.strip())
        except ValueError as exc:
            raise ValidationError("invalid observed DNS address") from exc
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            hostname=normalized_hostname,
            address=parsed_address,
            ptr_hostname=normalized_ptr,
            source=normalized_source,
        )

    @staticmethod
    def _normalize_hostname(value: str, label: str) -> str:
        normalized = value.strip().lower().rstrip(".")
        if not 1 <= len(normalized) <= 253 or " " in normalized:
            raise ValidationError(f"{label} is invalid")
        return normalized

    @staticmethod
    def _normalize_source(value: str) -> str:
        normalized = value.strip().lower()
        if not 1 <= len(normalized) <= 64:
            raise ValidationError("observation source must contain 1 to 64 characters")
        return normalized

    def as_dict(self) -> dict[str, str | None]:
        return {
            "tenant_id": self.tenant_id.value,
            "vrf": self.vrf_name.value,
            "hostname": self.hostname,
            "address": str(self.address),
            "ptr_hostname": self.ptr_hostname,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ObservedDhcpLease:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    prefix: str
    address: ipaddress.IPv4Address | ipaddress.IPv6Address
    mac_address: str
    hostname: str
    source: str
    active: bool

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        prefix: str,
        address: str,
        mac_address: str,
        hostname: str,
        source: str = "manual",
        active: bool = True,
    ) -> Self:
        try:
            network = ipaddress.ip_network(prefix.strip(), strict=True)
            parsed_address = ipaddress.ip_address(address.strip())
        except ValueError as exc:
            raise ValidationError("invalid observed DHCP lease address or prefix") from exc
        normalized_mac = mac_address.strip().lower().replace("-", ":")
        if not normalized_mac:
            raise ValidationError("DHCP lease MAC address is mandatory")
        normalized_hostname = ObservedDnsRecord._normalize_hostname(hostname, "lease hostname")
        if parsed_address.version != network.version:
            raise ValidationError("DHCP lease address family must match prefix")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            prefix=str(network),
            address=parsed_address,
            mac_address=normalized_mac,
            hostname=normalized_hostname,
            source=ObservedDnsRecord._normalize_source(source),
            active=bool(active),
        )

    def address_belongs_to_prefix(self) -> bool:
        return self.address in ipaddress.ip_network(self.prefix, strict=True)

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "tenant_id": self.tenant_id.value,
            "vrf": self.vrf_name.value,
            "prefix": self.prefix,
            "address": str(self.address),
            "mac_address": self.mac_address,
            "hostname": self.hostname,
            "source": self.source,
            "active": self.active,
        }


class IpRangePurpose(StrEnum):
    ALLOCATION = "allocation"
    RESERVATION = "reservation"
    EXCLUSION = "exclusion"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(
                "ip range purpose must be allocation, reservation or exclusion"
            ) from exc


class IpAddressStatus(StrEnum):
    PLANNED = "planned"
    RESERVED = "reserved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("ip address status is invalid") from exc


@dataclass(frozen=True, slots=True)
class IpAggregate:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    network: ipaddress.IPv4Network | ipaddress.IPv6Network
    description: str

    @classmethod
    def create(cls, tenant_id: TenantId, vrf_name: str, cidr: str, description: str = "") -> Self:
        try:
            network = ipaddress.ip_network(cidr.strip(), strict=True)
        except ValueError as exc:
            raise ValidationError(f"invalid aggregate: {cidr}") from exc
        if network.prefixlen == network.max_prefixlen:
            raise ValidationError("aggregate must contain more than one address")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            network=network,
            description=description.strip(),
        )

    def contains_network(self, network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
        if isinstance(self.network, ipaddress.IPv4Network) and isinstance(
            network, ipaddress.IPv4Network
        ):
            return network.subnet_of(self.network)
        if isinstance(self.network, ipaddress.IPv6Network) and isinstance(
            network, ipaddress.IPv6Network
        ):
            return network.subnet_of(self.network)
        return False


@dataclass(frozen=True, slots=True)
class IpRange:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    prefix: str
    start: ipaddress.IPv4Address | ipaddress.IPv6Address
    end: ipaddress.IPv4Address | ipaddress.IPv6Address
    purpose: IpRangePurpose
    description: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        prefix: Prefix,
        start: str,
        end: str,
        purpose: str = "allocation",
        description: str = "",
    ) -> Self:
        try:
            start_address = ipaddress.ip_address(start.strip())
            end_address = ipaddress.ip_address(end.strip())
        except ValueError as exc:
            raise ValidationError("invalid ip range boundary") from exc
        if (
            start_address.version != prefix.network.version
            or end_address.version != prefix.network.version
        ):
            raise ValidationError("ip range address family must match prefix family")
        if int(start_address) > int(end_address):
            raise ValidationError("ip range start must be lower than or equal to end")
        if not prefix.contains(start_address) or not prefix.contains(end_address):
            raise ValidationError("ip range must stay inside prefix")
        if (
            int(start_address) < prefix.first_usable_int
            or int(end_address) > prefix.last_usable_int
        ):
            raise ValidationError("ip range must use usable prefix addresses")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            prefix=str(prefix.network),
            start=start_address,
            end=end_address,
            purpose=IpRangePurpose.from_value(purpose),
            description=description.strip(),
        )

    @property
    def start_int(self) -> int:
        return int(self.start)

    @property
    def end_int(self) -> int:
        return int(self.end)

    def contains_int(self, address: int) -> bool:
        return self.start_int <= address <= self.end_int

    def overlaps(self, other: Self) -> bool:
        if self.tenant_id != other.tenant_id or self.vrf_name != other.vrf_name:
            return False
        if self.prefix != other.prefix:
            return False
        return self.start_int <= other.end_int and other.start_int <= self.end_int


@dataclass(frozen=True, slots=True)
class IpAddressRecord:
    id: EntityId
    tenant_id: TenantId
    vrf_name: Name
    prefix: str
    address: ipaddress.IPv4Address | ipaddress.IPv6Address
    hostname: str
    interface_name: Name | None
    status: IpAddressStatus

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        vrf_name: str,
        prefix: Prefix,
        address: str,
        hostname: str,
        interface_name: str | None = None,
        status: str = "reserved",
    ) -> Self:
        try:
            ip_address = ipaddress.ip_address(address.strip())
        except ValueError as exc:
            raise ValidationError(f"invalid ip address: {address}") from exc
        normalized_hostname = hostname.strip().lower()
        if not normalized_hostname:
            raise ValidationError("hostname is mandatory")
        if ip_address.version != prefix.network.version:
            raise ValidationError("address family does not match prefix family")
        if not prefix.contains(ip_address):
            raise ValidationError("address does not belong to prefix")
        if not prefix.first_usable_int <= int(ip_address) <= prefix.last_usable_int:
            raise ValidationError("address is not usable in prefix")
        normalized_interface = (
            Name.from_value(interface_name, "interface name")
            if interface_name is not None
            else None
        )
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            vrf_name=Name.from_value(vrf_name, "vrf name"),
            prefix=str(prefix.network),
            address=ip_address,
            hostname=normalized_hostname,
            interface_name=normalized_interface,
            status=IpAddressStatus.from_value(status),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "tenant_id": self.tenant_id.value,
            "vrf": self.vrf_name.value,
            "prefix": self.prefix,
            "address": str(self.address),
            "hostname": self.hostname,
            "interface_name": self.interface_name.value if self.interface_name else "",
            "status": self.status.value,
        }


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
        ranges: tuple[IpRange, ...] = (),
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        allocated_ints = {int(address) for address in allocated_addresses}
        allocation_ranges = tuple(
            ip_range for ip_range in ranges if ip_range.purpose == IpRangePurpose.ALLOCATION
        )
        blocked_ranges = tuple(
            ip_range
            for ip_range in ranges
            if ip_range.purpose in (IpRangePurpose.RESERVATION, IpRangePurpose.EXCLUSION)
        )
        for start, end in self._candidate_windows(prefix, allocation_ranges):
            current = start
            while current <= end:
                if current not in allocated_ints and not self._is_blocked(current, blocked_ranges):
                    return ipaddress.ip_address(current)
                current += 1
        raise ValidationError(f"prefix is exhausted: {prefix.network}")

    def _candidate_windows(
        self,
        prefix: Prefix,
        allocation_ranges: tuple[IpRange, ...],
    ) -> tuple[tuple[int, int], ...]:
        if not allocation_ranges:
            return ((prefix.first_usable_int, prefix.last_usable_int),)
        windows: list[tuple[int, int]] = []
        for ip_range in sorted(allocation_ranges, key=lambda item: item.start_int):
            start = max(prefix.first_usable_int, ip_range.start_int)
            end = min(prefix.last_usable_int, ip_range.end_int)
            if start <= end:
                windows.append((start, end))
        return tuple(windows)

    def _is_blocked(self, address: int, blocked_ranges: tuple[IpRange, ...]) -> bool:
        return any(ip_range.contains_int(address) for ip_range in blocked_ranges)

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
