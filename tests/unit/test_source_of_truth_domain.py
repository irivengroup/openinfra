from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.source_of_truth import (
    SourceObjectKey,
    SourceObjectSnapshot,
    SourceObjectTimeTravelReport,
    SourceOfTruthObject,
    SourceRelation,
    SourceTag,
)


class TestSourceOfTruthDomain:
    def test_object_create_revise_snapshot_and_dict(self) -> None:
        tenant = TenantId.from_value("default")
        source_object = SourceOfTruthObject.create(
            tenant_id=tenant,
            key="Device/SRV-001",
            kind="device",
            display_name="  Server   001 ",
            attributes={"serial": "ABC", "cpu_count": 16},
            tags=("Prod", "linux", "prod"),
            source="manual",
        )
        snapshot = SourceObjectSnapshot.create(source_object, "pytest")
        revised = source_object.revise(
            display_name="Server 001 updated",
            attributes={"serial": "ABC", "cpu_count": 32},
            tags=("prod", "critical"),
            source="manual",
        )

        assert source_object.key.value == "device/srv-001"
        assert source_object.display_name == "Server 001"
        assert source_object.as_dict()["tags"] == ["linux", "prod"]
        assert snapshot.payload["version"] == 1
        assert revised.version == 2
        assert revised.attributes["cpu_count"] == 32

    def test_relation_validity_and_invariants(self) -> None:
        tenant = TenantId.from_value("default")
        start = datetime.now(UTC)
        relation = SourceRelation.create(
            tenant,
            "depends_on",
            "application/app1",
            "service/db1",
            "manual",
            valid_from=start,
            valid_to=start + timedelta(days=1),
        )

        assert relation.is_valid_at(start + timedelta(minutes=1)) is True
        assert relation.is_valid_at(start + timedelta(days=2)) is False
        with pytest.raises(ValidationError):
            SourceRelation.create(tenant, "depends_on", "a/a1", "a/a1", "manual")
        with pytest.raises(ValidationError):
            SourceRelation.create(
                tenant,
                "depends_on",
                "a/a1",
                "b/b1",
                "manual",
                valid_from=start,
                valid_to=start,
            )

    def test_safe_values_reject_unsafe_inputs(self) -> None:
        with pytest.raises(ValidationError):
            SourceObjectKey.from_value("../etc/passwd")
        with pytest.raises(ValidationError):
            SourceTag.from_value("bad tag")
        with pytest.raises(ValidationError):
            SourceOfTruthObject.create(
                TenantId.from_value("default"),
                "device/srv",
                "device",
                "Server",
                {"bad key": "value"},
                (),
                "manual",
            )

    def test_restore_and_value_object_error_branches(self) -> None:
        tenant = TenantId.from_value("default")
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            SourceObjectKey.from_value("device//srv")
        from openinfra.domain.source_of_truth import RelationType, SourceSystem

        with pytest.raises(ValidationError):
            SourceSystem.from_value("1bad")
        with pytest.raises(ValidationError):
            RelationType.from_value("bad type")
        with pytest.raises(ValidationError):
            SourceOfTruthObject.restore(
                id=SourceOfTruthObject.create(
                    tenant, "device/srv-a", "device", "A", {}, (), "manual"
                ).id,
                tenant_id=tenant,
                key="device/srv-a",
                kind="device",
                display_name=" ",
                attributes={},
                tags=(),
                source="manual",
                version=1,
                status="active",
                created_at=now,
                updated_at=now,
            )
        with pytest.raises(ValidationError):
            SourceOfTruthObject.restore(
                id=SourceOfTruthObject.create(
                    tenant, "device/srv-b", "device", "B", {}, (), "manual"
                ).id,
                tenant_id=tenant,
                key="device/srv-b",
                kind="device",
                display_name="B",
                attributes={},
                tags=(),
                source="manual",
                version=0,
                status="active",
                created_at=now,
                updated_at=now,
            )
        with pytest.raises(ValidationError):
            SourceOfTruthObject.restore(
                id=SourceOfTruthObject.create(
                    tenant, "device/srv-c", "device", "C", {}, (), "manual"
                ).id,
                tenant_id=tenant,
                key="device/srv-c",
                kind="device",
                display_name="C",
                attributes={},
                tags=(),
                source="manual",
                version=1,
                status="active",
                created_at=now,
                updated_at=now - timedelta(seconds=1),
            )
        with pytest.raises(ValidationError):
            SourceOfTruthObject.restore(
                id=SourceOfTruthObject.create(
                    tenant, "device/srv-d", "device", "D", {}, (), "manual"
                ).id,
                tenant_id=tenant,
                key="device/srv-d",
                kind="device",
                display_name="D",
                attributes={},
                tags=(),
                source="manual",
                version=1,
                status="active",
                created_at=datetime.now(),
                updated_at=now,
            )

    def test_snapshot_restore_error_branches(self) -> None:
        tenant = TenantId.from_value("default")
        source_object = SourceOfTruthObject.create(
            tenant, "device/srv-e", "device", "E", {}, (), "manual"
        )
        with pytest.raises(ValidationError):
            SourceObjectSnapshot.create(source_object, " ")
        with pytest.raises(ValidationError):
            SourceObjectSnapshot.restore(
                id=source_object.id,
                tenant_id=tenant,
                object_key="device/srv-e",
                object_id=source_object.id,
                version=0,
                payload=source_object.as_dict(),
                changed_by="pytest",
                changed_at=datetime.now(UTC),
            )

    def test_time_travel_report_validates_snapshot_and_relation_coherence(self) -> None:
        tenant = TenantId.from_value("default")
        source_object = SourceOfTruthObject.create(
            tenant,
            "server/time-travel",
            "server",
            "Time travel server",
            {"site": "PAR1"},
            ("history",),
            "discovery.snmp",
        )
        snapshot = SourceObjectSnapshot.create(source_object, "collector-1")
        relation = SourceRelation.create(
            tenant,
            "runs_on",
            "application/history",
            "server/time-travel",
            "discovery.ssh",
            valid_from=snapshot.changed_at - timedelta(minutes=1),
            valid_to=snapshot.changed_at + timedelta(minutes=1),
        )
        report = SourceObjectTimeTravelReport.create(
            requested_at=snapshot.changed_at,
            snapshot=snapshot,
            relations=(relation,),
            complete=True,
        )
        payload = report.as_dict()
        assert payload["coherent"] is True
        assert payload["provenance"]["source_system"] == "discovery.snmp"
        assert payload["relation_count"] == 1

        invalid_payloads = (
            {**snapshot.payload, "key": "server/other"},
            {**snapshot.payload, "id": SourceOfTruthObject.create(
                tenant, "server/other-id", "server", "Other", {}, (), "manual"
            ).id.value},
            {**snapshot.payload, "version": 99},
        )
        for invalid_payload in invalid_payloads:
            invalid_snapshot = SourceObjectSnapshot.restore(
                id=snapshot.id,
                tenant_id=tenant,
                object_key="server/time-travel",
                object_id=source_object.id,
                version=source_object.version,
                payload=invalid_payload,
                changed_by="collector-1",
                changed_at=snapshot.changed_at,
            )
            with pytest.raises(ValidationError):
                SourceObjectTimeTravelReport.create(
                    requested_at=snapshot.changed_at,
                    snapshot=invalid_snapshot,
                    relations=(),
                    complete=True,
                )

        with pytest.raises(ValidationError):
            SourceObjectTimeTravelReport.create(
                requested_at=snapshot.changed_at - timedelta(seconds=1),
                snapshot=snapshot,
                relations=(),
                complete=True,
            )
        unrelated = SourceRelation.create(
            tenant,
            "depends_on",
            "application/a",
            "service/b",
            "manual",
            valid_from=snapshot.changed_at - timedelta(minutes=1),
        )
        with pytest.raises(ValidationError):
            SourceObjectTimeTravelReport.create(
                requested_at=snapshot.changed_at,
                snapshot=snapshot,
                relations=(unrelated,),
                complete=True,
            )
        expired = SourceRelation.create(
            tenant,
            "runs_on",
            "application/history",
            "server/time-travel",
            "manual",
            valid_from=snapshot.changed_at - timedelta(minutes=2),
            valid_to=snapshot.changed_at - timedelta(minutes=1),
        )
        with pytest.raises(ValidationError):
            SourceObjectTimeTravelReport.create(
                requested_at=snapshot.changed_at,
                snapshot=snapshot,
                relations=(expired,),
                complete=True,
            )

