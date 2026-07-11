from __future__ import annotations

from datetime import datetime
from typing import Any

from openinfra.domain.common import EntityId, TenantId
from openinfra.domain.field_operations import (
    FieldChecklistItem,
    FieldEvidence,
    FieldOperationSheet,
    FieldPhysicalLocation,
    FieldSafetyWarning,
    InterventionLock,
    OfflineSyncPackage,
)


class FieldOperationRecordMapper:
    @staticmethod
    def location(value: dict[str, Any]) -> FieldPhysicalLocation:
        return FieldPhysicalLocation.create(
            site=str(value["site"]),
            building=str(value["building"]),
            floor=None if value.get("floor") is None else str(value["floor"]),
            room=str(value["room"]),
            row=str(value["row"]),
            column=str(value["column"]),
            zone=None if value.get("zone") is None else str(value["zone"]),
            rack=None if value.get("rack") is None else str(value["rack"]),
            rack_face=None if value.get("rack_face") is None else str(value["rack_face"]),
            u_position=None if value.get("u_position") is None else int(value["u_position"]),
            x=None if value.get("x") is None else float(value["x"]),
            y=None if value.get("y") is None else float(value["y"]),
            z=None if value.get("z") is None else float(value["z"]),
        )

    @classmethod
    def sheet(cls, value: dict[str, Any]) -> FieldOperationSheet:
        checklist = tuple(
            FieldChecklistItem.restore(
                id=EntityId.from_value(str(item["id"])),
                phase=str(item["phase"]),
                order=int(item["order"]),
                title=str(item["title"]),
                instruction=str(item["instruction"]),
                required=bool(item["required"]),
                result=str(item["result"]),
                operator_note=(
                    None if item.get("operator_note") is None else str(item["operator_note"])
                ),
                verified_by=(None if item.get("verified_by") is None else str(item["verified_by"])),
                verified_at=(
                    None
                    if item.get("verified_at") is None
                    else datetime.fromisoformat(str(item["verified_at"]))
                ),
            )
            for item in value.get("checklist", [])
        )
        warnings = tuple(
            FieldSafetyWarning.create(
                str(item["code"]),
                str(item["severity"]),
                str(item["message"]),
                str(item["source"]),
            )
            for item in value.get("warnings", [])
        )
        return FieldOperationSheet.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            target_type=str(value["target_type"]),
            target_id=str(value["target_id"]),
            title=str(value["title"]),
            purpose=str(value["purpose"]),
            owner=str(value["owner"]),
            operator=str(value["operator"]),
            location=cls.location(dict(value["location"])),
            source_object_key=(
                None if value.get("source_object_key") is None else str(value["source_object_key"])
            ),
            qr_payload=str(value["qr_payload"]),
            barcode=str(value["barcode"]),
            checklist=checklist,
            warnings=warnings,
            status=str(value["status"]),
            version=int(value["version"]),
            created_by=str(value["created_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_by=str(value["updated_by"]),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
            started_at=(
                None
                if value.get("started_at") is None
                else datetime.fromisoformat(str(value["started_at"]))
            ),
            completed_at=(
                None
                if value.get("completed_at") is None
                else datetime.fromisoformat(str(value["completed_at"]))
            ),
            cancelled_at=(
                None
                if value.get("cancelled_at") is None
                else datetime.fromisoformat(str(value["cancelled_at"]))
            ),
        )

    @staticmethod
    def evidence(value: dict[str, Any]) -> FieldEvidence:
        return FieldEvidence.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            sheet_id=EntityId.from_value(str(value["sheet_id"])),
            phase=str(value["phase"]),
            media_type=str(value["media_type"]),
            filename=str(value["filename"]),
            content_base64=str(value["content_base64"]),
            content_sha256=str(value["content_sha256"]),
            size_bytes=int(value["size_bytes"]),
            caption=str(value["caption"]),
            status=str(value["status"]),
            attached_by=str(value["attached_by"]),
            attached_at=datetime.fromisoformat(str(value["attached_at"])),
            validated_by=(
                None if value.get("validated_by") is None else str(value["validated_by"])
            ),
            validated_at=(
                None
                if value.get("validated_at") is None
                else datetime.fromisoformat(str(value["validated_at"]))
            ),
        )

    @staticmethod
    def lock(value: dict[str, Any]) -> InterventionLock:
        return InterventionLock.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            sheet_id=EntityId.from_value(str(value["sheet_id"])),
            target_type=str(value["target_type"]),
            target_id=str(value["target_id"]),
            idempotency_key=str(value["idempotency_key"]),
            owner=str(value["owner"]),
            status=str(value["status"]),
            acquired_at=datetime.fromisoformat(str(value["acquired_at"])),
            expires_at=datetime.fromisoformat(str(value["expires_at"])),
            released_at=(
                None
                if value.get("released_at") is None
                else datetime.fromisoformat(str(value["released_at"]))
            ),
            released_by=(None if value.get("released_by") is None else str(value["released_by"])),
        )

    @staticmethod
    def package(value: dict[str, Any]) -> OfflineSyncPackage:
        return OfflineSyncPackage.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            sheet_id=EntityId.from_value(str(value["sheet_id"])),
            idempotency_key=str(value["idempotency_key"]),
            authorized_site=str(value["authorized_site"]),
            payload=dict(value["payload"]),
            payload_sha256=str(value["payload_sha256"]),
            status=str(value["status"]),
            created_by=str(value["created_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            expires_at=datetime.fromisoformat(str(value["expires_at"])),
            synchronized_by=(
                None if value.get("synchronized_by") is None else str(value["synchronized_by"])
            ),
            synchronized_at=(
                None
                if value.get("synchronized_at") is None
                else datetime.fromisoformat(str(value["synchronized_at"]))
            ),
            client_payload_sha256=(
                None
                if value.get("client_payload_sha256") is None
                else str(value["client_payload_sha256"])
            ),
        )
