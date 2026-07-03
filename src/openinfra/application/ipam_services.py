from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from openinfra.application.ports import AuditRepository, IpamRepository, TransactionManager
from openinfra.domain.common import AuditEvent, ConflictError, TenantId
from openinfra.domain.ipam import (
    AllocationRequest,
    AllocationResult,
    IpAddressRecord,
    IpAggregate,
    IpAllocationPolicy,
    IpRange,
    IpReservation,
    Prefix,
    Vrf,
)


@dataclass(frozen=True, slots=True)
class AllocateIpCommand:
    tenant_id: str
    actor: str
    vrf: str
    prefix: str
    hostname: str
    idempotency_key: str


class IpamAllocationService:
    def __init__(
        self,
        ipam_repository: IpamRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        allocation_policy: IpAllocationPolicy | None = None,
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._allocation_policy = allocation_policy or IpAllocationPolicy()

    def allocate(self, command: AllocateIpCommand) -> AllocationResult:
        request = AllocationRequest.create(
            tenant_id=command.tenant_id,
            vrf_name=command.vrf,
            prefix_cidr=command.prefix,
            hostname=command.hostname,
            idempotency_key=command.idempotency_key,
        )
        with self._transaction_manager.begin() as unit_of_work:
            prefix = self._ipam_repository.get_or_create_prefix(
                Prefix.create(request.tenant_id, request.vrf_name.value, request.prefix_cidr)
            )
            existing = self._ipam_repository.find_reservation_by_key(
                tenant_id=request.tenant_id,
                vrf_name=request.vrf_name.value,
                idempotency_key=request.idempotency_key,
            )
            if existing is not None:
                unit_of_work.commit()
                return AllocationResult(reservation=existing, created=False)
            reservations = self._ipam_repository.list_reservations(
                tenant_id=request.tenant_id,
                vrf_name=request.vrf_name.value,
                prefix_cidr=str(prefix.network),
            )
            next_address = self._allocation_policy.next_available_address(
                prefix,
                {reservation.address for reservation in reservations},
            )
            reservation = IpReservation.create(
                tenant_id=request.tenant_id,
                vrf_name=request.vrf_name.value,
                prefix=prefix,
                address=str(next_address),
                hostname=request.hostname,
                idempotency_key=request.idempotency_key,
            )
            self._ipam_repository.add_reservation(reservation)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=request.tenant_id,
                    actor=command.actor,
                    action="ipam.address.allocated",
                    target_type="ip_reservation",
                    target_id=str(reservation.address),
                    metadata={
                        "vrf": reservation.vrf_name.value,
                        "prefix": reservation.prefix,
                        "hostname": reservation.hostname,
                    },
                )
            )
            unit_of_work.commit()
        return AllocationResult(reservation=reservation, created=True)


@dataclass(frozen=True, slots=True)
class DefineVrfCommand:
    tenant_id: str
    actor: str
    name: str
    route_distinguisher: str | None = None


@dataclass(frozen=True, slots=True)
class DefineIpAggregateCommand:
    tenant_id: str
    actor: str
    vrf: str
    cidr: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class DefineIpPrefixCommand:
    tenant_id: str
    actor: str
    vrf: str
    cidr: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class DefineIpRangeCommand:
    tenant_id: str
    actor: str
    vrf: str
    prefix: str
    start: str
    end: str
    purpose: str = "allocation"
    description: str = ""


@dataclass(frozen=True, slots=True)
class RegisterIpAddressCommand:
    tenant_id: str
    actor: str
    vrf: str
    prefix: str
    address: str
    hostname: str
    interface_name: str | None = None
    status: str = "reserved"


@dataclass(frozen=True, slots=True)
class IpamCapacityCommand:
    tenant_id: str
    vrf: str
    prefix: str


@dataclass(frozen=True, slots=True)
class IpamCapacityReport:
    tenant_id: str
    vrf: str
    prefix: str
    family: int
    usable_addresses: int
    reserved_addresses: int
    free_addresses: int
    range_count: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "tenant_id": self.tenant_id,
            "vrf": self.vrf,
            "prefix": self.prefix,
            "family": self.family,
            "usable_addresses": self.usable_addresses,
            "reserved_addresses": self.reserved_addresses,
            "free_addresses": self.free_addresses,
            "range_count": self.range_count,
        }


class IpamModelService:
    def __init__(
        self,
        ipam_repository: IpamRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def define_vrf(self, command: DefineVrfCommand) -> dict[str, str | None]:
        tenant_id = TenantId.from_value(command.tenant_id)
        vrf = Vrf.create(tenant_id, command.name, command.route_distinguisher)
        with self._transaction_manager.begin() as unit_of_work:
            stored = self._ipam_repository.add_or_get_vrf(vrf)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.vrf.defined",
                    target_type="ipam_vrf",
                    target_id=stored.name.value,
                    metadata={"route_distinguisher": stored.route_distinguisher},
                )
            )
            unit_of_work.commit()
        return self._vrf_as_dict(stored)

    def define_aggregate(self, command: DefineIpAggregateCommand) -> dict[str, str | int]:
        tenant_id = TenantId.from_value(command.tenant_id)
        aggregate = IpAggregate.create(tenant_id, command.vrf, command.cidr, command.description)
        with self._transaction_manager.begin() as unit_of_work:
            self._assert_network_does_not_overlap(
                aggregate.network,
                self._ipam_repository.list_aggregates(tenant_id, command.vrf),
                "aggregate",
            )
            stored = self._ipam_repository.add_aggregate(aggregate)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.aggregate.defined",
                    target_type="ipam_aggregate",
                    target_id=str(stored.network),
                    metadata={"vrf": stored.vrf_name.value, "family": stored.network.version},
                )
            )
            unit_of_work.commit()
        return self._aggregate_as_dict(stored)

    def define_prefix(self, command: DefineIpPrefixCommand) -> dict[str, str | int]:
        tenant_id = TenantId.from_value(command.tenant_id)
        prefix = Prefix.create(tenant_id, command.vrf, command.cidr, command.description)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._ipam_repository.list_prefixes(tenant_id, command.vrf)
            self._assert_network_does_not_overlap(prefix.network, existing, "prefix")
            stored = self._ipam_repository.get_or_create_prefix(prefix)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.prefix.defined",
                    target_type="ipam_prefix",
                    target_id=str(stored.network),
                    metadata={"vrf": stored.vrf_name.value, "family": stored.network.version},
                )
            )
            unit_of_work.commit()
        return self._prefix_as_dict(stored)

    def define_range(self, command: DefineIpRangeCommand) -> dict[str, str]:
        tenant_id = TenantId.from_value(command.tenant_id)
        with self._transaction_manager.begin() as unit_of_work:
            prefix = self._ipam_repository.get_or_create_prefix(
                Prefix.create(tenant_id, command.vrf, command.prefix)
            )
            ip_range = IpRange.create(
                tenant_id,
                command.vrf,
                prefix,
                command.start,
                command.end,
                command.purpose,
                command.description,
            )
            for existing in self._ipam_repository.list_ranges(
                tenant_id, command.vrf, str(prefix.network)
            ):
                if ip_range.overlaps(existing):
                    raise ConflictError(
                        "ip range overlaps an existing range in this VRF and prefix"
                    )
            stored = self._ipam_repository.add_range(ip_range)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.range.defined",
                    target_type="ipam_range",
                    target_id=f"{stored.start}-{stored.end}",
                    metadata={"vrf": stored.vrf_name.value, "prefix": stored.prefix},
                )
            )
            unit_of_work.commit()
        return self._range_as_dict(stored)

    def register_address(self, command: RegisterIpAddressCommand) -> dict[str, str]:
        tenant_id = TenantId.from_value(command.tenant_id)
        with self._transaction_manager.begin() as unit_of_work:
            prefix = self._ipam_repository.get_or_create_prefix(
                Prefix.create(tenant_id, command.vrf, command.prefix)
            )
            record = IpAddressRecord.create(
                tenant_id,
                command.vrf,
                prefix,
                command.address,
                command.hostname,
                command.interface_name,
                command.status,
            )
            stored = self._ipam_repository.upsert_address_record(record)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.address.registered",
                    target_type="ipam_address",
                    target_id=str(stored.address),
                    metadata={"vrf": stored.vrf_name.value, "prefix": stored.prefix},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def capacity(self, command: IpamCapacityCommand) -> IpamCapacityReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        prefix = self._ipam_repository.get_or_create_prefix(
            Prefix.create(tenant_id, command.vrf, command.prefix)
        )
        reservations = self._ipam_repository.list_reservations(
            tenant_id, command.vrf, str(prefix.network)
        )
        records = self._ipam_repository.list_address_records(
            tenant_id, command.vrf, str(prefix.network)
        )
        ranges = self._ipam_repository.list_ranges(tenant_id, command.vrf, str(prefix.network))
        occupied = {int(reservation.address) for reservation in reservations}
        occupied.update(int(record.address) for record in records)
        usable = prefix.last_usable_int - prefix.first_usable_int + 1
        reserved = len(occupied)
        return IpamCapacityReport(
            tenant_id=tenant_id.value,
            vrf=prefix.vrf_name.value,
            prefix=str(prefix.network),
            family=prefix.network.version,
            usable_addresses=usable,
            reserved_addresses=reserved,
            free_addresses=max(usable - reserved, 0),
            range_count=len(ranges),
        )

    def list_prefixes(self, tenant_id: str, vrf: str) -> tuple[dict[str, str | int], ...]:
        tenant = TenantId.from_value(tenant_id)
        return tuple(
            self._prefix_as_dict(prefix)
            for prefix in self._ipam_repository.list_prefixes(tenant, vrf)
        )

    def _assert_network_does_not_overlap(
        self,
        network: ipaddress.IPv4Network | ipaddress.IPv6Network,
        existing_networks: tuple[IpAggregate, ...] | tuple[Prefix, ...],
        label: str,
    ) -> None:
        for existing in existing_networks:
            if str(existing.network) == str(network):
                return
            if existing.network.version == network.version and existing.network.overlaps(network):
                raise ConflictError(f"{label} overlaps existing {label} in this VRF")

    def _vrf_as_dict(self, vrf: Vrf) -> dict[str, str | None]:
        return {
            "tenant_id": vrf.tenant_id.value,
            "name": vrf.name.value,
            "route_distinguisher": vrf.route_distinguisher,
        }

    def _aggregate_as_dict(self, aggregate: IpAggregate) -> dict[str, str | int]:
        return {
            "tenant_id": aggregate.tenant_id.value,
            "vrf": aggregate.vrf_name.value,
            "cidr": str(aggregate.network),
            "family": aggregate.network.version,
            "description": aggregate.description,
        }

    def _prefix_as_dict(self, prefix: Prefix) -> dict[str, str | int]:
        return {
            "tenant_id": prefix.tenant_id.value,
            "vrf": prefix.vrf_name.value,
            "cidr": str(prefix.network),
            "family": prefix.network.version,
            "first_usable": str(ipaddress.ip_address(prefix.first_usable_int)),
            "last_usable": str(ipaddress.ip_address(prefix.last_usable_int)),
            "description": prefix.description,
        }

    def _range_as_dict(self, ip_range: IpRange) -> dict[str, str]:
        return {
            "tenant_id": ip_range.tenant_id.value,
            "vrf": ip_range.vrf_name.value,
            "prefix": ip_range.prefix,
            "start": str(ip_range.start),
            "end": str(ip_range.end),
            "purpose": ip_range.purpose.value,
            "description": ip_range.description,
        }
