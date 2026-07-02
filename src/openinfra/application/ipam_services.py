from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.ports import AuditRepository, IpamRepository, TransactionManager
from openinfra.domain.common import AuditEvent, TenantId
from openinfra.domain.ipam import (
    AllocationRequest,
    AllocationResult,
    IpAllocationPolicy,
    IpReservation,
    Prefix,
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
