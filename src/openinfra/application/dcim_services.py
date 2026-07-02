from __future__ import annotations

from dataclasses import dataclass

from openinfra.application.ports import AuditRepository, DcimRepository, TransactionManager
from openinfra.domain.common import AuditEvent, NotFoundError, TenantId, ValidationError
from openinfra.domain.dcim import Equipment, EquipmentLocation, Rack


@dataclass(frozen=True, slots=True)
class LocateEquipmentCommand:
    tenant_id: str
    actor: str
    asset_tag: str
    equipment_name: str
    site: str
    building: str
    room: str
    row: str
    column: str
    rack: str | None
    u_position: int | None
    x: float | None
    y: float | None
    z: float | None


class DcimLocationService:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def locate_equipment(self, command: LocateEquipmentCommand) -> Equipment:
        tenant_id = TenantId.from_value(command.tenant_id)
        room = self._dcim_repository.find_room(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
        )
        if room is None:
            raise NotFoundError("room must exist before locating equipment")
        room.assert_cell_exists(command.row, command.column)
        rack = self._resolve_rack(command, tenant_id)
        location = EquipmentLocation.create(
            site_code=command.site,
            building_code=command.building,
            room_code=command.room,
            row=command.row,
            column=command.column,
            rack_code=command.rack,
            u_position=command.u_position,
            coordinates=None,
        )
        if rack is not None and command.u_position is not None and command.u_position > rack.units:
            raise ValidationError("equipment unit position exceeds rack capacity")
        equipment = Equipment.create(
            tenant_id=tenant_id,
            asset_tag=command.asset_tag,
            name=command.equipment_name,
            location=location,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._dcim_repository.add_equipment(equipment)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="dcim.equipment.located",
                    target_type="equipment",
                    target_id=equipment.asset_tag.value,
                    metadata={"location": equipment.location.human_readable()},
                )
            )
            unit_of_work.commit()
        return equipment

    def _resolve_rack(self, command: LocateEquipmentCommand, tenant_id: TenantId) -> Rack | None:
        if command.rack is None:
            return None
        rack = self._dcim_repository.find_rack(
            tenant_id=tenant_id,
            site=command.site,
            building=command.building,
            room=command.room,
            rack=command.rack,
        )
        if rack is None:
            raise NotFoundError("rack must exist before rack-mounted equipment location")
        if rack.row != command.row.strip().upper() or rack.column != command.column.strip().upper():
            raise ValidationError("rack row and column do not match equipment location")
        return rack
