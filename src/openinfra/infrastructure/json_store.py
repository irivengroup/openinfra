from __future__ import annotations

import ipaddress
import json
import secrets
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

from openinfra.application.ports import (
    AccessPolicyRepository,
    AccessPolicyRulePage,
    AuditRepository,
    DcimRepository,
    DiscoveryCollectorPage,
    DiscoveryRepository,
    ExportRepository,
    IdentityRepository,
    ImportRepository,
    IpamRepository,
    ItamSupportRepository,
    ReadinessProbe,
    ReadinessStatus,
    RuntimeUsageRepository,
    SchemaStatusProvider,
    SecurityRepository,
    SecurityTokenPage,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
    UnitOfWork,
)
from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.audit import (
    AuditEventFilter,
    AuditEventPage,
    AuditEventRecord,
    AuditIntegrityHasher,
    AuditIntegrityReport,
)
from openinfra.domain.common import (
    AuditEvent,
    Code,
    ConflictError,
    Coordinates3D,
    EntityId,
    Name,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.data_export import ExportJob
from openinfra.domain.data_import import (
    BulkImportCheckpoint,
    BulkImportMetrics,
    BulkImportReport,
    ImportFormat,
    ImportJobStatus,
    ImportMapping,
    ImportReport,
    ImportRowImpact,
    ImportRowIssue,
    LegacyMigrationSource,
    MigrationGap,
    MigrationPlanReport,
    MigrationTemplate,
)
from openinfra.domain.dcim import (
    Building,
    CoolingRole,
    CoolingZone,
    DcimCable,
    DcimCableMedium,
    DcimCablePathSegment,
    DcimCableStatus,
    DcimConnectorType,
    DcimPort,
    DcimPortEndpoint,
    DcimPortOwnerType,
    Equipment,
    EquipmentLocation,
    Floor,
    PatchPanel,
    PowerCircuit,
    PowerDevice,
    PowerDeviceKind,
    PowerFeedSide,
    Rack,
    RackFace,
    RackPowerReservation,
    Room,
    RoomZone,
    Site,
)
from openinfra.domain.discovery import CollectorStatus, DiscoveryCollector
from openinfra.domain.editions import QuotaResource
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
    IdentityUser,
)
from openinfra.domain.itam import (
    ManufacturerWarranty,
    PhysicalAssetSupportProfile,
    ThirdPartySupportContract,
    ItamDateParser,
)
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpAddressFamily,
    BgpPeer,
    IpAddressRecord,
    IpAggregate,
    IpRange,
    IpReservation,
    ObservedDhcpLease,
    ObservedDnsRecord,
    Prefix,
    Vlan,
    VlanGroup,
    Vrf,
    VxlanVni,
)
from openinfra.domain.security import ApiTokenCredential, Permission
from openinfra.domain.source_governance import SourceGovernanceRule, SourceGovernanceRulePage
from openinfra.domain.source_of_truth import (
    SourceObjectPage,
    SourceObjectSnapshot,
    SourceOfTruthObject,
    SourceRelation,
    SourceRelationPage,
)

_EXPORT_SIGNING_STORAGE_KEY = "export_signing_" + "secret"


@dataclass(slots=True)
class _JsonState:
    data: dict[str, Any]
    dirty: bool


class JsonDocumentStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._state = _JsonState(data=self._empty_state(), dirty=False)
        self._load()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def data(self) -> dict[str, Any]:
        return self._state.data

    def mark_dirty(self) -> None:
        self._state.dirty = True

    def flush(self) -> None:
        if not self._state.dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state.data, indent=2, sort_keys=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(self._path.parent),
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(self._path)
        self._state.dirty = False

    def snapshot(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(json.dumps(self._state.data)))

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._state = _JsonState(data=snapshot, dirty=False)

    def _load(self) -> None:
        if not self._path.exists():
            self._state = _JsonState(data=self._empty_state(), dirty=True)
            self.flush()
            return
        loaded = json.loads(self._path.read_text(encoding="utf-8"))
        self._state = _JsonState(data=self._merge_with_empty(loaded), dirty=False)

    def _merge_with_empty(self, loaded: dict[str, Any]) -> dict[str, Any]:
        merged = self._empty_state()
        for key, value in loaded.items():
            if key in merged or key == _EXPORT_SIGNING_STORAGE_KEY:
                merged[key] = value
        return merged

    def _empty_state(self) -> dict[str, Any]:
        return {
            "sites": {},
            "buildings": {},
            "floors": {},
            "rooms": {},
            "room_zones": {},
            "racks": {},
            "patch_panels": {},
            "dcim_ports": {},
            "dcim_cables": {},
            "power_devices": {},
            "power_circuits": {},
            "cooling_zones": {},
            "power_reservations": {},
            "equipment": {},
            "vrfs": {},
            "ip_aggregates": {},
            "prefixes": {},
            "ip_ranges": {},
            "ip_address_records": {},
            "ip_reservations": {},
            "vlan_groups": {},
            "vlans": {},
            "vxlan_vnis": {},
            "autonomous_systems": {},
            "bgp_peers": {},
            "dns_observations": {},
            "dhcp_leases": {},
            "audit_events": [],
            "security_tokens": {},
            "identity_users": {},
            "identity_groups": {},
            "identity_memberships": {},
            "access_policy_rules": {},
            "source_objects": {},
            "source_object_snapshots": [],
            "source_relations": {},
            "source_governance_rules": {},
            "import_jobs": {},
            "bulk_import_jobs": {},
            "bulk_import_checkpoints": {},
            "migration_plans": {},
            "export_jobs": {},
            "export_artifacts": {},
            "discovery_collectors": {},
            "asset_support_profiles": {},
        }


class JsonRuntimeUsageRepository(RuntimeUsageRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def count_resource(self, tenant_id: TenantId, resource: QuotaResource) -> int:
        with self._store.lock:
            if resource is QuotaResource.EQUIPMENT:
                return self._count_items("equipment", tenant_id)
            if resource is QuotaResource.SUBNET_VLAN:
                return self._count_items("prefixes", tenant_id) + self._count_items(
                    "vlans", tenant_id
                )
            if resource is QuotaResource.IP_DNS_RECORD:
                return (
                    self._count_items("ip_reservations", tenant_id)
                    + self._count_items("ip_address_records", tenant_id)
                    + self._count_items("dns_observations", tenant_id)
                )
            if resource is QuotaResource.USER:
                return self._count_items("identity_users", tenant_id)
            if resource is QuotaResource.DISCOVERY_COLLECTOR:
                return self._count_items("discovery_collectors", tenant_id)
            raise AssertionError(f"unhandled quota resource: {resource}")

    def _count_items(self, bucket: str, tenant_id: TenantId) -> int:
        values = self._store.data[bucket]
        if isinstance(values, list):
            return sum(1 for item in values if item.get("tenant_id") == tenant_id.value)
        return sum(1 for item in values.values() if item.get("tenant_id") == tenant_id.value)


class JsonDiscoveryRepository(DiscoveryRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def save_collector(self, collector: DiscoveryCollector) -> None:
        with self._store.lock:
            self._store.data["discovery_collectors"][
                self._key(collector.tenant_id, collector.id.value)
            ] = collector.as_dict()
            self._store.mark_dirty()

    def get_collector(self, tenant_id: TenantId, collector_id: str) -> DiscoveryCollector | None:
        with self._store.lock:
            payload = self._store.data["discovery_collectors"].get(
                self._key(tenant_id, collector_id)
            )
            if payload is None:
                return None
            return DiscoveryCollector.from_dict(cast(dict[str, object], payload))

    def list_collectors(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryCollectorPage:
        with self._store.lock:
            prefix = tenant_id.value + ":"
            collectors = [
                DiscoveryCollector.from_dict(cast(dict[str, object], payload))
                for key, payload in self._store.data["discovery_collectors"].items()
                if key.startswith(prefix)
            ]
        filtered = tuple(
            collector
            for collector in sorted(
                collectors, key=lambda item: (item.registered_at, item.id.value)
            )
            if include_inactive or collector.status is not CollectorStatus.DISABLED
        )
        start = 0
        if pagination.cursor:
            ids = [collector.id.value for collector in filtered]
            if pagination.cursor in ids:
                start = ids.index(pagination.cursor) + 1
        page = filtered[start : start + pagination.limit]
        next_cursor = page[-1].id.value if len(page) == pagination.limit else None
        return DiscoveryCollectorPage(items=page, next_cursor=next_cursor)

    def _key(self, tenant_id: TenantId, collector_id: str) -> str:
        return tenant_id.value + ":" + collector_id.strip()


class JsonImportRepository(ImportRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def save_import_report(self, report: ImportReport) -> None:
        with self._store.lock:
            self._store.data["import_jobs"][self._key(report.tenant_id, report.job_id.value)] = (
                report.as_dict()
            )
            self._store.mark_dirty()

    def get_import_report(self, tenant_id: TenantId, job_id: str) -> ImportReport | None:
        with self._store.lock:
            payload = self._store.data["import_jobs"].get(self._key(tenant_id, job_id))
            if payload is None:
                return None
            return self._report_from_payload(payload)

    def _key(self, tenant_id: TenantId, job_id: str) -> str:
        return tenant_id.value + ":" + job_id.strip()

    def save_bulk_import_report(self, report: BulkImportReport) -> None:
        with self._store.lock:
            self._store.data["bulk_import_jobs"][
                self._key(report.tenant_id, report.job_id.value)
            ] = report.as_dict()
            self._store.mark_dirty()

    def get_bulk_import_report(self, tenant_id: TenantId, job_id: str) -> BulkImportReport | None:
        with self._store.lock:
            payload = self._store.data["bulk_import_jobs"].get(self._key(tenant_id, job_id))
            if payload is None:
                return None
            return self._bulk_report_from_payload(payload)

    def save_bulk_import_checkpoint(self, checkpoint: BulkImportCheckpoint) -> None:
        with self._store.lock:
            self._store.data["bulk_import_checkpoints"][
                self._key(checkpoint.tenant_id, checkpoint.job_id.value)
            ] = checkpoint.as_dict()
            self._store.mark_dirty()

    def get_bulk_import_checkpoint(
        self, tenant_id: TenantId, job_id: str
    ) -> BulkImportCheckpoint | None:
        with self._store.lock:
            payload = self._store.data["bulk_import_checkpoints"].get(self._key(tenant_id, job_id))
            if payload is None:
                return None
            return self._checkpoint_from_payload(payload)

    def save_migration_plan_report(self, report: MigrationPlanReport) -> None:
        with self._store.lock:
            self._store.data["migration_plans"][
                self._key(report.tenant_id, report.job_id.value)
            ] = report.as_dict()
            self._store.mark_dirty()

    def get_migration_plan_report(
        self, tenant_id: TenantId, job_id: str
    ) -> MigrationPlanReport | None:
        with self._store.lock:
            payload = self._store.data["migration_plans"].get(self._key(tenant_id, job_id))
            if payload is None:
                return None
            if not isinstance(payload, dict):
                raise ValidationError("stored migration plan is invalid")
            return self._migration_plan_from_payload(payload)

    def bulk_import_strategy_name(self) -> str:
        return "json-streaming-batch-checkpoint"

    def _migration_plan_from_payload(self, payload: dict[str, object]) -> MigrationPlanReport:
        template_payload = payload.get("template", {})
        gaps_payload = payload.get("gaps", [])
        import_payload = payload.get("import_report", {})
        if not isinstance(template_payload, dict):
            raise ValidationError("stored migration template is invalid")
        if not isinstance(gaps_payload, list) or not isinstance(import_payload, dict):
            raise ValidationError("stored migration plan details are invalid")
        mapping_payload = template_payload.get("mapping", {})
        if not isinstance(mapping_payload, dict):
            raise ValidationError("stored migration template mapping is invalid")
        source = LegacyMigrationSource.from_value(str(template_payload["source"]))
        required_columns_payload = template_payload.get("required_columns", [])
        recommended_columns_payload = template_payload.get("recommended_columns", [])
        notes_payload = template_payload.get("notes", [])
        if not isinstance(required_columns_payload, list):
            raise ValidationError("stored migration template required columns are invalid")
        if not isinstance(recommended_columns_payload, list) or not isinstance(notes_payload, list):
            raise ValidationError("stored migration template metadata is invalid")
        template = MigrationTemplate.create(
            source=source,
            name=str(template_payload["name"]),
            version=str(template_payload["version"]),
            mapping=ImportMapping.from_dict({str(k): str(v) for k, v in mapping_payload.items()}),
            required_columns=tuple(str(item) for item in required_columns_payload),
            recommended_columns=tuple(str(item) for item in recommended_columns_payload),
            notes=tuple(str(item) for item in notes_payload),
        )
        gaps = tuple(
            MigrationGap.create(
                str(item["category"]),
                str(item["field"]),
                str(item["message"]),
                Severity(str(item["severity"])),
            )
            for item in gaps_payload
            if isinstance(item, dict)
        )
        return MigrationPlanReport.create(
            tenant_id=TenantId.from_value(str(payload["tenant_id"])),
            source=LegacyMigrationSource.from_value(str(payload["source"])),
            import_format=ImportFormat.from_value(str(payload["format"])),
            template=template,
            gaps=gaps,
            import_report=self._report_from_payload(import_payload),
            resume_strategy=str(payload["resume_strategy"]),
            job_id=EntityId.from_value(str(payload["job_id"])),
        )

    def _report_from_payload(self, payload: dict[str, object]) -> ImportReport:
        mapping_payload = payload.get("mapping", {})
        if not isinstance(mapping_payload, dict):
            raise ValidationError("stored import mapping is invalid")
        impacts_payload = payload.get("impacts", [])
        dlq_payload = payload.get("dlq", [])
        if not isinstance(impacts_payload, list) or not isinstance(dlq_payload, list):
            raise ValidationError("stored import report rows are invalid")
        mapping = ImportMapping.from_dict({str(k): str(v) for k, v in mapping_payload.items()})
        impacts = tuple(
            ImportRowImpact.create(
                int(item["row_number"]),
                str(item["action"]),
                str(item["object_key"]),
                str(item["object_kind"]),
            )
            for item in impacts_payload
            if isinstance(item, dict)
        )
        issues = tuple(
            ImportRowIssue.create(
                int(item["row_number"]),
                str(item["field"]),
                str(item["message"]),
                Severity(str(item["severity"])),
            )
            for item in dlq_payload
            if isinstance(item, dict)
        )
        return ImportReport.create(
            tenant_id=TenantId.from_value(str(payload["tenant_id"])),
            import_format=ImportFormat.from_value(str(payload["format"])),
            dry_run=bool(payload["dry_run"]),
            mapping=mapping,
            total_rows=int(str(payload["total_rows"])),
            impacts=impacts,
            dlq=issues,
            status=ImportJobStatus(str(payload["status"])),
            job_id=EntityId.from_value(str(payload["job_id"])),
        )

    def _bulk_report_from_payload(self, payload: dict[str, object]) -> BulkImportReport:
        mapping_payload = payload.get("mapping", {})
        metrics_payload = payload.get("metrics", {})
        checkpoint_payload = payload.get("checkpoint", {})
        impacts_payload = payload.get("impact_sample", [])
        dlq_payload = payload.get("dlq_sample", [])
        if not isinstance(mapping_payload, dict):
            raise ValidationError("stored bulk import mapping is invalid")
        if not isinstance(metrics_payload, dict) or not isinstance(checkpoint_payload, dict):
            raise ValidationError("stored bulk import metrics are invalid")
        if not isinstance(impacts_payload, list) or not isinstance(dlq_payload, list):
            raise ValidationError("stored bulk import samples are invalid")
        mapping = ImportMapping.from_dict({str(k): str(v) for k, v in mapping_payload.items()})
        metrics = BulkImportMetrics.create(
            batch_size=int(str(metrics_payload["batch_size"])),
            checkpoint_interval=int(str(metrics_payload["checkpoint_interval"])),
            batches_completed=int(str(metrics_payload["batches_completed"])),
            copy_strategy=str(metrics_payload["copy_strategy"]),
            resumed_from_row=(
                None
                if metrics_payload.get("resumed_from_row") is None
                else int(str(metrics_payload["resumed_from_row"]))
            ),
        )
        checkpoint = self._checkpoint_from_payload(checkpoint_payload)
        impacts = tuple(
            ImportRowImpact.create(
                int(item["row_number"]),
                str(item["action"]),
                str(item["object_key"]),
                str(item["object_kind"]),
            )
            for item in impacts_payload
            if isinstance(item, dict)
        )
        issues = tuple(
            ImportRowIssue.create(
                int(item["row_number"]),
                str(item["field"]),
                str(item["message"]),
                Severity(str(item["severity"])),
            )
            for item in dlq_payload
            if isinstance(item, dict)
        )
        return BulkImportReport.create(
            tenant_id=TenantId.from_value(str(payload["tenant_id"])),
            import_format=ImportFormat.from_value(str(payload["format"])),
            dry_run=bool(payload["dry_run"]),
            status=ImportJobStatus(str(payload["status"])),
            total_rows=int(str(payload["total_rows"])),
            valid_rows=int(str(payload["valid_rows"])),
            invalid_rows=int(str(payload["invalid_rows"])),
            create_count=int(str(payload["create_count"])),
            update_count=int(str(payload["update_count"])),
            mapping=mapping,
            metrics=metrics,
            checkpoint=checkpoint,
            impact_sample=impacts,
            dlq_sample=issues,
            job_id=EntityId.from_value(str(payload["job_id"])),
        )

    def _checkpoint_from_payload(self, payload: dict[str, object]) -> BulkImportCheckpoint:
        return BulkImportCheckpoint.create(
            tenant_id=TenantId.from_value(str(payload["tenant_id"])),
            next_row_number=int(str(payload["next_row_number"])),
            total_rows=int(str(payload["total_rows"])),
            valid_rows=int(str(payload["valid_rows"])),
            invalid_rows=int(str(payload["invalid_rows"])),
            create_count=int(str(payload["create_count"])),
            update_count=int(str(payload["update_count"])),
            batches_completed=int(str(payload["batches_completed"])),
            status=ImportJobStatus(str(payload["status"])),
            job_id=EntityId.from_value(str(payload["job_id"])),
        )


class JsonExportRepository(ExportRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def save_export_job(self, job: ExportJob) -> None:
        with self._store.lock:
            self._store.data["export_jobs"][self._key(job.tenant_id, job.id.value)] = job.as_dict()
            self._store.mark_dirty()

    def get_export_job(self, tenant_id: TenantId, job_id: str) -> ExportJob | None:
        with self._store.lock:
            payload = self._store.data["export_jobs"].get(self._key(tenant_id, job_id))
            if payload is None:
                return None
            if not isinstance(payload, dict):
                raise ValidationError("stored export job is invalid")
            return ExportJob.from_dict(payload)

    def get_next_queued_export_job(self, tenant_id: TenantId) -> ExportJob | None:
        with self._store.lock:
            jobs = [
                ExportJob.from_dict(payload)
                for payload in self._store.data["export_jobs"].values()
                if isinstance(payload, dict)
                and payload.get("tenant_id") == tenant_id.value
                and payload.get("status") == "queued"
            ]
            jobs.sort(key=lambda item: (item.created_at, item.id.value))
            return jobs[0] if jobs else None

    def save_export_artifact(self, job: ExportJob, content: bytes) -> None:
        with self._store.lock:
            self._store.data["export_artifacts"][self._key(job.tenant_id, job.id.value)] = {
                "content_hex": content.hex()
            }
            self._store.mark_dirty()

    def get_export_artifact(self, tenant_id: TenantId, job_id: str) -> bytes | None:
        with self._store.lock:
            payload = self._store.data["export_artifacts"].get(self._key(tenant_id, job_id))
            if payload is None:
                return None
            if not isinstance(payload, dict):
                raise ValidationError("stored export artifact is invalid")
            return bytes.fromhex(str(payload["content_hex"]))

    def get_or_create_export_signing_secret(self) -> bytes:
        with self._store.lock:
            value = str(self._store.data.get(_EXPORT_SIGNING_STORAGE_KEY, ""))
            if not value:
                value = secrets.token_hex(32)
                self._store.data[_EXPORT_SIGNING_STORAGE_KEY] = value
                self._store.mark_dirty()
            return bytes.fromhex(value)

    def export_storage_strategy_name(self) -> str:
        return "json-managed-object-storage"

    def _key(self, tenant_id: TenantId, job_id: str) -> str:
        return tenant_id.value + ":" + job_id.strip()


class JsonSchemaStatusProvider(SchemaStatusProvider):
    def status_as_dict(self) -> dict[str, object]:
        return {
            "backend": "json",
            "managed": False,
            "ready": True,
            "detail": "json backend does not require PostgreSQL schema migrations",
            "applied": [],
            "pending": [],
        }


class JsonReadinessProbe(ReadinessProbe):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def check(self) -> ReadinessStatus:
        with self._store.lock:
            collections_ready = all(
                key in self._store.data
                for key in (
                    "sites",
                    "buildings",
                    "floors",
                    "rooms",
                    "room_zones",
                    "racks",
                    "patch_panels",
                    "dcim_ports",
                    "dcim_cables",
                    "power_devices",
                    "power_circuits",
                    "cooling_zones",
                    "power_reservations",
                    "equipment",
                    "vrfs",
                    "ip_aggregates",
                    "prefixes",
                    "ip_ranges",
                    "ip_address_records",
                    "ip_reservations",
                    "audit_events",
                    "security_tokens",
                    "identity_users",
                    "identity_groups",
                    "identity_memberships",
                    "access_policy_rules",
                    "source_objects",
                    "source_object_snapshots",
                    "source_relations",
                    "source_governance_rules",
                    "import_jobs",
                    "bulk_import_jobs",
                    "bulk_import_checkpoints",
                    "export_jobs",
                    "export_artifacts",
                    "discovery_collectors",
                    "asset_support_profiles",
                )
            )
        detail = (
            "json document store is writable" if collections_ready else "json schema is incomplete"
        )
        return ReadinessStatus("json", collections_ready, detail)


class JsonUnitOfWork(UnitOfWork):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store
        self._snapshot: dict[str, Any] | None = None
        self._committed = False

    def __enter__(self) -> JsonUnitOfWork:
        self._store.lock.acquire()
        self._snapshot = self._store.snapshot()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._store.lock.release()

    def commit(self) -> None:
        self._store.mark_dirty()
        self._store.flush()
        self._committed = True

    def rollback(self) -> None:
        if self._snapshot is not None:
            self._store.restore(self._snapshot)
        self._committed = True


class JsonTransactionManager(TransactionManager):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def begin(self) -> JsonUnitOfWork:
        return JsonUnitOfWork(self._store)


class JsonDcimRepository(DcimRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def add_site(self, site: Site) -> None:
        key = self._key(site.tenant_id, site.code.value)
        self._put_unique("sites", key, self._site_to_dict(site))

    def add_building(self, building: Building) -> None:
        key = self._key(building.tenant_id, building.site_code.value, building.code.value)
        self._put_unique("buildings", key, self._building_to_dict(building))

    def add_floor(self, floor: Floor) -> None:
        key = self._key(
            floor.tenant_id,
            floor.site_code.value,
            floor.building_code.value,
            floor.code.value,
        )
        self._put_unique("floors", key, self._floor_to_dict(floor))

    def add_room(self, room: Room) -> None:
        key = self._key(
            room.tenant_id,
            room.site_code.value,
            room.building_code.value,
            room.code.value,
        )
        self._put_unique("rooms", key, self._room_to_dict(room))

    def add_zone(self, zone: RoomZone) -> None:
        key = self._key(
            zone.tenant_id,
            zone.site_code.value,
            zone.building_code.value,
            zone.room_code.value,
            zone.code.value,
        )
        self._put_unique("room_zones", key, self._zone_to_dict(zone))

    def add_rack(self, rack: Rack) -> None:
        key = self._key(
            rack.tenant_id,
            rack.site_code.value,
            rack.building_code.value,
            rack.room_code.value,
            rack.code.value,
        )
        self._put_unique("racks", key, self._rack_to_dict(rack))

    def add_patch_panel(self, patch_panel: PatchPanel) -> None:
        key = self._key(
            patch_panel.tenant_id,
            patch_panel.site_code.value,
            patch_panel.building_code.value,
            patch_panel.room_code.value,
            patch_panel.rack_code.value,
            patch_panel.code.value,
        )
        self._put_unique("patch_panels", key, self._patch_panel_to_dict(patch_panel))

    def add_dcim_port(self, port: DcimPort) -> None:
        key = self._key(port.tenant_id, port.endpoint.key())
        self._put_unique("dcim_ports", key, self._dcim_port_to_dict(port))

    def add_dcim_cable(self, cable: DcimCable) -> None:
        key = self._key(cable.tenant_id, cable.cable_id.value)
        self._put_unique("dcim_cables", key, self._dcim_cable_to_dict(cable))

    def add_equipment(self, equipment: Equipment) -> None:
        key = self._key(equipment.tenant_id, equipment.asset_tag.value)
        self._store.data["equipment"][key] = self._equipment_to_dict(equipment)
        self._store.mark_dirty()

    def add_power_device(self, power_device: PowerDevice) -> None:
        key = self._key(power_device.tenant_id, power_device.code.value)
        self._put_unique("power_devices", key, self._power_device_to_dict(power_device))

    def add_power_circuit(self, circuit: PowerCircuit) -> None:
        key = self._key(circuit.tenant_id, circuit.circuit_id.value)
        self._put_unique("power_circuits", key, self._power_circuit_to_dict(circuit))

    def add_cooling_zone(self, cooling_zone: CoolingZone) -> None:
        key = self._key(
            cooling_zone.tenant_id,
            cooling_zone.site_code.value,
            cooling_zone.building_code.value,
            cooling_zone.room_code.value,
            cooling_zone.zone_code.value,
        )
        self._put_unique("cooling_zones", key, self._cooling_zone_to_dict(cooling_zone))

    def add_power_reservation(self, reservation: RackPowerReservation) -> None:
        key = self._key(
            reservation.tenant_id,
            reservation.asset_tag.value,
            reservation.side.value,
            reservation.circuit_id.value,
        )
        self._put_unique("power_reservations", key, self._power_reservation_to_dict(reservation))

    def find_site(self, tenant_id: TenantId, site: str) -> Site | None:
        key = self._key(tenant_id, Code.from_value(site, "site code").value)
        item = self._store.data["sites"].get(key)
        return self._site_from_dict(item) if item else None

    def find_building(self, tenant_id: TenantId, site: str, building: str) -> Building | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
        )
        item = self._store.data["buildings"].get(key)
        return self._building_from_dict(item) if item else None

    def find_floor(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        floor: str,
    ) -> Floor | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
            Code.from_value(floor, "floor code").value,
        )
        item = self._store.data["floors"].get(key)
        return self._floor_from_dict(item) if item else None

    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        key = self._key(
            tenant_id,
            Code.from_value(site).value,
            Code.from_value(building).value,
            Code.from_value(room).value,
        )
        item = self._store.data["rooms"].get(key)
        return self._room_from_dict(item) if item else None

    def find_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> RoomZone | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
            Code.from_value(room, "room code").value,
            Code.from_value(zone, "zone code").value,
        )
        item = self._store.data["room_zones"].get(key)
        return self._zone_from_dict(item) if item else None

    def find_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> Rack | None:
        key = self._key(
            tenant_id,
            Code.from_value(site).value,
            Code.from_value(building).value,
            Code.from_value(room).value,
            Code.from_value(rack).value,
        )
        item = self._store.data["racks"].get(key)
        return self._rack_from_dict(item) if item else None

    def find_patch_panel(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
        patch_panel: str,
    ) -> PatchPanel | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
            Code.from_value(room, "room code").value,
            Code.from_value(rack, "rack code").value,
            Code.from_value(patch_panel, "patch panel code").value,
        )
        item = self._store.data["patch_panels"].get(key)
        return self._patch_panel_from_dict(item) if item else None

    def find_dcim_port(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimPort | None:
        item = self._store.data["dcim_ports"].get(self._key(tenant_id, endpoint.key()))
        return self._dcim_port_from_dict(item) if item else None

    def find_dcim_cable(self, tenant_id: TenantId, cable_id: str) -> DcimCable | None:
        key = self._key(tenant_id, Code.from_value(cable_id, "cable id").value)
        item = self._store.data["dcim_cables"].get(key)
        return self._dcim_cable_from_dict(item) if item else None

    def find_active_dcim_cable_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimCable | None:
        for value in self._store.data["dcim_cables"].values():
            if value.get("tenant_id") != tenant_id.value:
                continue
            cable = self._dcim_cable_from_dict(value)
            if cable.status.consumes_endpoint_capacity and cable.touches(endpoint):
                return cable
        return None

    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        key = self._key(tenant_id, Code.from_value(asset_tag).value)
        item = self._store.data["equipment"].get(key)
        return self._equipment_from_dict(item) if item else None

    def find_power_device(self, tenant_id: TenantId, code: str) -> PowerDevice | None:
        key = self._key(tenant_id, Code.from_value(code, "power device code").value)
        item = self._store.data["power_devices"].get(key)
        return self._power_device_from_dict(item) if item else None

    def find_power_circuit(self, tenant_id: TenantId, circuit_id: str) -> PowerCircuit | None:
        key = self._key(tenant_id, Code.from_value(circuit_id, "power circuit id").value)
        item = self._store.data["power_circuits"].get(key)
        return self._power_circuit_from_dict(item) if item else None

    def find_cooling_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> CoolingZone | None:
        key = self._key(
            tenant_id,
            Code.from_value(site, "site code").value,
            Code.from_value(building, "building code").value,
            Code.from_value(room, "room code").value,
            Code.from_value(zone, "zone code").value,
        )
        item = self._store.data["cooling_zones"].get(key)
        return self._cooling_zone_from_dict(item) if item else None

    def list_equipment_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[Equipment, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        normalized_rack = Code.from_value(rack, "rack code").value
        matching: list[Equipment] = []
        for value in self._store.data["equipment"].values():
            location = value.get("location", {})
            if (
                value.get("tenant_id") == tenant_id.value
                and location.get("site_code") == normalized_site
                and location.get("building_code") == normalized_building
                and location.get("room_code") == normalized_room
                and location.get("rack_code") == normalized_rack
            ):
                matching.append(self._equipment_from_dict(value))
        return tuple(sorted(matching, key=lambda item: item.asset_tag.value))

    def list_racks_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
    ) -> tuple[Rack, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        matching: list[Rack] = []
        for value in self._store.data["racks"].values():
            if (
                value.get("tenant_id") == tenant_id.value
                and value.get("site_code") == normalized_site
                and value.get("building_code") == normalized_building
                and value.get("room_code") == normalized_room
            ):
                matching.append(self._rack_from_dict(value))
        return tuple(sorted(matching, key=lambda item: (item.row, item.column, item.code.value)))

    def list_patch_panels_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PatchPanel, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        normalized_rack = Code.from_value(rack, "rack code").value
        matching: list[PatchPanel] = []
        for value in self._store.data["patch_panels"].values():
            if (
                value.get("tenant_id") == tenant_id.value
                and value.get("site_code") == normalized_site
                and value.get("building_code") == normalized_building
                and value.get("room_code") == normalized_room
                and value.get("rack_code") == normalized_rack
            ):
                matching.append(self._patch_panel_from_dict(value))
        return tuple(sorted(matching, key=lambda item: (item.rack_face.value, item.u_position)))

    def list_dcim_ports_by_owner(
        self,
        tenant_id: TenantId,
        owner_type: str,
        owner_code: str,
    ) -> tuple[DcimPort, ...]:
        normalized_owner_type = DcimPortOwnerType.from_value(owner_type).value
        normalized_owner_code = Code.from_value(owner_code, "port owner code").value
        matching: list[DcimPort] = []
        for value in self._store.data["dcim_ports"].values():
            endpoint = value.get("endpoint", {})
            if (
                value.get("tenant_id") == tenant_id.value
                and endpoint.get("owner_type") == normalized_owner_type
                and endpoint.get("owner_code") == normalized_owner_code
            ):
                matching.append(self._dcim_port_from_dict(value))
        return tuple(sorted(matching, key=lambda item: item.endpoint.port_name.value))

    def list_dcim_cables_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> tuple[DcimCable, ...]:
        matching: list[DcimCable] = []
        for value in self._store.data["dcim_cables"].values():
            if value.get("tenant_id") != tenant_id.value:
                continue
            cable = self._dcim_cable_from_dict(value)
            if cable.touches(endpoint):
                matching.append(cable)
        return tuple(sorted(matching, key=lambda item: item.cable_id.value))

    def list_equipment_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
    ) -> tuple[Equipment, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        matching: list[Equipment] = []
        for value in self._store.data["equipment"].values():
            location = value.get("location", {})
            if (
                value.get("tenant_id") == tenant_id.value
                and location.get("site_code") == normalized_site
                and location.get("building_code") == normalized_building
                and location.get("room_code") == normalized_room
            ):
                matching.append(self._equipment_from_dict(value))
        return tuple(sorted(matching, key=lambda item: item.asset_tag.value))

    def list_power_circuits_by_source(
        self,
        tenant_id: TenantId,
        source_device: str,
    ) -> tuple[PowerCircuit, ...]:
        normalized_source = Code.from_value(source_device, "power device code").value
        matching = [
            self._power_circuit_from_dict(value)
            for value in self._store.data["power_circuits"].values()
            if value.get("tenant_id") == tenant_id.value
            and value.get("source_device_code") == normalized_source
        ]
        return tuple(sorted(matching, key=lambda item: item.circuit_id.value))

    def list_power_circuits_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PowerCircuit, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        normalized_rack = Code.from_value(rack, "rack code").value
        matching = [
            self._power_circuit_from_dict(value)
            for value in self._store.data["power_circuits"].values()
            if value.get("tenant_id") == tenant_id.value
            and value.get("site_code") == normalized_site
            and value.get("building_code") == normalized_building
            and value.get("room_code") == normalized_room
            and value.get("rack_code") == normalized_rack
        ]
        return tuple(sorted(matching, key=lambda item: (item.side.value, item.circuit_id.value)))

    def list_power_reservations_for_circuit(
        self,
        tenant_id: TenantId,
        circuit_id: str,
    ) -> tuple[RackPowerReservation, ...]:
        normalized_circuit = Code.from_value(circuit_id, "power circuit id").value
        matching = [
            self._power_reservation_from_dict(value)
            for value in self._store.data["power_reservations"].values()
            if value.get("tenant_id") == tenant_id.value
            and value.get("circuit_id") == normalized_circuit
        ]
        return tuple(sorted(matching, key=lambda item: (item.asset_tag.value, item.side.value)))

    def list_power_reservations_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[RackPowerReservation, ...]:
        normalized_site = Code.from_value(site, "site code").value
        normalized_building = Code.from_value(building, "building code").value
        normalized_room = Code.from_value(room, "room code").value
        normalized_rack = Code.from_value(rack, "rack code").value
        matching = [
            self._power_reservation_from_dict(value)
            for value in self._store.data["power_reservations"].values()
            if value.get("tenant_id") == tenant_id.value
            and value.get("site_code") == normalized_site
            and value.get("building_code") == normalized_building
            and value.get("room_code") == normalized_room
            and value.get("rack_code") == normalized_rack
        ]
        return tuple(sorted(matching, key=lambda item: (item.side.value, item.asset_tag.value)))

    def _power_device_to_dict(self, power_device: PowerDevice) -> dict[str, Any]:
        return {
            "id": power_device.id.value,
            "tenant_id": power_device.tenant_id.value,
            "code": power_device.code.value,
            "kind": power_device.kind.value,
            "site_code": power_device.site_code.value,
            "building_code": power_device.building_code.value,
            "room_code": power_device.room_code.value,
            "rack_code": power_device.rack_code.value if power_device.rack_code else None,
            "side": power_device.side.value if power_device.side else None,
            "capacity_watts": power_device.capacity_watts,
            "derating_percent": power_device.derating_percent,
            "input_source": power_device.input_source,
            "output_voltage": power_device.output_voltage,
            "label": power_device.label,
        }

    def _power_device_from_dict(self, value: dict[str, Any]) -> PowerDevice:
        return PowerDevice(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            code=Code.from_value(value["code"], "power device code"),
            kind=PowerDeviceKind.from_value(value["kind"]),
            site_code=Code.from_value(value["site_code"], "site code"),
            building_code=Code.from_value(value["building_code"], "building code"),
            room_code=Code.from_value(value["room_code"], "room code"),
            rack_code=Code.from_value(value["rack_code"], "rack code")
            if value.get("rack_code")
            else None,
            side=PowerFeedSide.from_value(value["side"]) if value.get("side") else None,
            capacity_watts=int(value["capacity_watts"]),
            derating_percent=int(value["derating_percent"]),
            input_source=str(value["input_source"]),
            output_voltage=int(value["output_voltage"]),
            label=str(value.get("label", "")),
        )

    def _power_circuit_to_dict(self, circuit: PowerCircuit) -> dict[str, Any]:
        return {
            "id": circuit.id.value,
            "tenant_id": circuit.tenant_id.value,
            "circuit_id": circuit.circuit_id.value,
            "source_device_code": circuit.source_device_code.value,
            "site_code": circuit.site_code.value,
            "building_code": circuit.building_code.value,
            "room_code": circuit.room_code.value,
            "rack_code": circuit.rack_code.value,
            "side": circuit.side.value,
            "capacity_watts": circuit.capacity_watts,
            "breaker_rating_amps": circuit.breaker_rating_amps,
            "redundancy_group": circuit.redundancy_group,
            "label": circuit.label,
        }

    def _power_circuit_from_dict(self, value: dict[str, Any]) -> PowerCircuit:
        return PowerCircuit(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            circuit_id=Code.from_value(value["circuit_id"], "power circuit id"),
            source_device_code=Code.from_value(value["source_device_code"], "power device code"),
            site_code=Code.from_value(value["site_code"], "site code"),
            building_code=Code.from_value(value["building_code"], "building code"),
            room_code=Code.from_value(value["room_code"], "room code"),
            rack_code=Code.from_value(value["rack_code"], "rack code"),
            side=PowerFeedSide.from_value(value["side"]),
            capacity_watts=int(value["capacity_watts"]),
            breaker_rating_amps=int(value["breaker_rating_amps"]),
            redundancy_group=str(value["redundancy_group"]),
            label=str(value.get("label", "")),
        )

    def _cooling_zone_to_dict(self, cooling_zone: CoolingZone) -> dict[str, Any]:
        return {
            "id": cooling_zone.id.value,
            "tenant_id": cooling_zone.tenant_id.value,
            "site_code": cooling_zone.site_code.value,
            "building_code": cooling_zone.building_code.value,
            "room_code": cooling_zone.room_code.value,
            "zone_code": cooling_zone.zone_code.value,
            "role": cooling_zone.role.value,
            "cooling_capacity_watts": cooling_zone.cooling_capacity_watts,
            "supply_temperature_c": cooling_zone.supply_temperature_c,
            "return_temperature_c": cooling_zone.return_temperature_c,
            "label": cooling_zone.label,
        }

    def _cooling_zone_from_dict(self, value: dict[str, Any]) -> CoolingZone:
        return CoolingZone(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"], "site code"),
            building_code=Code.from_value(value["building_code"], "building code"),
            room_code=Code.from_value(value["room_code"], "room code"),
            zone_code=Code.from_value(value["zone_code"], "zone code"),
            role=CoolingRole.from_value(value["role"]),
            cooling_capacity_watts=int(value["cooling_capacity_watts"]),
            supply_temperature_c=float(value["supply_temperature_c"]),
            return_temperature_c=float(value["return_temperature_c"]),
            label=str(value.get("label", "")),
        )

    def _power_reservation_to_dict(self, reservation: RackPowerReservation) -> dict[str, Any]:
        return {
            "id": reservation.id.value,
            "tenant_id": reservation.tenant_id.value,
            "asset_tag": reservation.asset_tag.value,
            "circuit_id": reservation.circuit_id.value,
            "side": reservation.side.value,
            "site_code": reservation.site_code.value,
            "building_code": reservation.building_code.value,
            "room_code": reservation.room_code.value,
            "rack_code": reservation.rack_code.value,
            "expected_watts": reservation.expected_watts,
            "label": reservation.label,
        }

    def _power_reservation_from_dict(self, value: dict[str, Any]) -> RackPowerReservation:
        return RackPowerReservation(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            asset_tag=Code.from_value(value["asset_tag"], "asset tag"),
            circuit_id=Code.from_value(value["circuit_id"], "power circuit id"),
            side=PowerFeedSide.from_value(value["side"]),
            site_code=Code.from_value(value["site_code"], "site code"),
            building_code=Code.from_value(value["building_code"], "building code"),
            room_code=Code.from_value(value["room_code"], "room code"),
            rack_code=Code.from_value(value["rack_code"], "rack code"),
            expected_watts=int(value["expected_watts"]),
            label=str(value.get("label", "")),
        )

    def _put_unique(self, collection: str, key: str, value: dict[str, Any]) -> None:
        if key in self._store.data[collection]:
            raise ConflictError(f"duplicate {collection} key: {key}")
        self._store.data[collection][key] = value
        self._store.mark_dirty()

    def _key(self, tenant_id: TenantId, *parts: str) -> str:
        return ":".join((tenant_id.value, *parts))

    def _site_to_dict(self, site: Site) -> dict[str, Any]:
        return {
            "id": site.id.value,
            "tenant_id": site.tenant_id.value,
            "code": site.code.value,
            "name": site.name.value,
            "country": site.country,
            "city": site.city,
            "region": site.region,
        }

    def _site_from_dict(self, value: dict[str, Any]) -> Site:
        return Site(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            country=value["country"],
            city=value["city"],
            region=value.get("region", ""),
        )

    def _building_to_dict(self, building: Building) -> dict[str, Any]:
        return {
            "id": building.id.value,
            "tenant_id": building.tenant_id.value,
            "site_code": building.site_code.value,
            "code": building.code.value,
            "name": building.name.value,
        }

    def _building_from_dict(self, value: dict[str, Any]) -> Building:
        return Building(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
        )

    def _floor_to_dict(self, floor: Floor) -> dict[str, Any]:
        return {
            "id": floor.id.value,
            "tenant_id": floor.tenant_id.value,
            "site_code": floor.site_code.value,
            "building_code": floor.building_code.value,
            "code": floor.code.value,
            "name": floor.name.value,
            "level_index": floor.level_index,
        }

    def _floor_from_dict(self, value: dict[str, Any]) -> Floor:
        return Floor(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            level_index=int(value["level_index"]),
        )

    def _room_to_dict(self, room: Room) -> dict[str, Any]:
        return {
            "id": room.id.value,
            "tenant_id": room.tenant_id.value,
            "site_code": room.site_code.value,
            "building_code": room.building_code.value,
            "code": room.code.value,
            "name": room.name.value,
            "rows": list(room.rows),
            "columns": list(room.columns),
            "floor_code": room.floor_code.value if room.floor_code else None,
            "zone_codes": [zone.value for zone in room.zone_codes],
            "coordinates": room.coordinates.as_dict() if room.coordinates else None,
        }

    def _room_from_dict(self, value: dict[str, Any]) -> Room:
        coordinates = value.get("coordinates")
        return Room(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            rows=tuple(value["rows"]),
            columns=tuple(value["columns"]),
            floor_code=Code.from_value(value["floor_code"]) if value.get("floor_code") else None,
            zone_codes=tuple(Code.from_value(zone) for zone in value.get("zone_codes", [])),
            coordinates=Coordinates3D.from_values(**coordinates) if coordinates else None,
        )

    def _zone_to_dict(self, zone: RoomZone) -> dict[str, Any]:
        return {
            "id": zone.id.value,
            "tenant_id": zone.tenant_id.value,
            "site_code": zone.site_code.value,
            "building_code": zone.building_code.value,
            "floor_code": zone.floor_code.value,
            "room_code": zone.room_code.value,
            "code": zone.code.value,
            "name": zone.name.value,
            "rows": list(zone.rows),
            "columns": list(zone.columns),
        }

    def _zone_from_dict(self, value: dict[str, Any]) -> RoomZone:
        return RoomZone(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            floor_code=Code.from_value(value["floor_code"]),
            room_code=Code.from_value(value["room_code"]),
            code=Code.from_value(value["code"]),
            name=Name.from_value(value["name"]),
            rows=tuple(value["rows"]),
            columns=tuple(value["columns"]),
        )

    def _rack_to_dict(self, rack: Rack) -> dict[str, Any]:
        return {
            "id": rack.id.value,
            "tenant_id": rack.tenant_id.value,
            "site_code": rack.site_code.value,
            "building_code": rack.building_code.value,
            "room_code": rack.room_code.value,
            "code": rack.code.value,
            "row": rack.row,
            "column": rack.column,
            "units": rack.units,
            "coordinates": rack.coordinates.as_dict() if rack.coordinates else None,
            "floor_code": rack.floor_code.value if rack.floor_code else None,
            "zone_code": rack.zone_code.value if rack.zone_code else None,
            "usable_faces": [face.value for face in rack.usable_faces],
            "max_weight_kg": rack.max_weight_kg,
            "power_capacity_watts": rack.power_capacity_watts,
        }

    def _rack_from_dict(self, value: dict[str, Any]) -> Rack:
        coordinates = value["coordinates"]
        return Rack(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"]),
            building_code=Code.from_value(value["building_code"]),
            room_code=Code.from_value(value["room_code"]),
            code=Code.from_value(value["code"]),
            row=value["row"],
            column=value["column"],
            units=int(value["units"]),
            coordinates=Coordinates3D.from_values(**coordinates) if coordinates else None,
            floor_code=Code.from_value(value["floor_code"]) if value.get("floor_code") else None,
            zone_code=Code.from_value(value["zone_code"]) if value.get("zone_code") else None,
            usable_faces=tuple(
                RackFace.from_value(face) or RackFace.FRONT
                for face in value.get("usable_faces", ["front"])
            ),
            max_weight_kg=(
                float(value["max_weight_kg"]) if value.get("max_weight_kg") is not None else None
            ),
            power_capacity_watts=(
                int(value["power_capacity_watts"])
                if value.get("power_capacity_watts") is not None
                else None
            ),
        )

    def _equipment_to_dict(self, equipment: Equipment) -> dict[str, Any]:
        location = equipment.location
        return {
            "id": equipment.id.value,
            "tenant_id": equipment.tenant_id.value,
            "asset_tag": equipment.asset_tag.value,
            "name": equipment.name.value,
            "location": {
                "site_code": location.site_code.value,
                "building_code": location.building_code.value,
                "room_code": location.room_code.value,
                "row": location.row,
                "column": location.column,
                "rack_code": location.rack_code.value if location.rack_code else None,
                "u_position": location.u_position,
                "coordinates": location.coordinates.as_dict() if location.coordinates else None,
                "floor_code": location.floor_code.value if location.floor_code else None,
                "zone_code": location.zone_code.value if location.zone_code else None,
                "rack_face": location.rack_face.value if location.rack_face else None,
                "u_height": location.u_height,
            },
        }

    def _equipment_from_dict(self, value: dict[str, Any]) -> Equipment:
        location = value["location"]
        coordinates = location["coordinates"]
        return Equipment(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            asset_tag=Code.from_value(value["asset_tag"]),
            name=Name.from_value(value["name"]),
            location=EquipmentLocation.create(
                site_code=location["site_code"],
                building_code=location["building_code"],
                room_code=location["room_code"],
                row=location["row"],
                column=location["column"],
                rack_code=location["rack_code"],
                u_position=location["u_position"],
                coordinates=Coordinates3D.from_values(**coordinates) if coordinates else None,
                floor_code=location.get("floor_code"),
                zone_code=location.get("zone_code"),
                rack_face=location.get("rack_face"),
                u_height=location.get("u_height"),
            ),
        )

    def _patch_panel_to_dict(self, patch_panel: PatchPanel) -> dict[str, Any]:
        return {
            "id": patch_panel.id.value,
            "tenant_id": patch_panel.tenant_id.value,
            "site_code": patch_panel.site_code.value,
            "building_code": patch_panel.building_code.value,
            "room_code": patch_panel.room_code.value,
            "rack_code": patch_panel.rack_code.value,
            "code": patch_panel.code.value,
            "rack_face": patch_panel.rack_face.value,
            "u_position": patch_panel.u_position,
            "u_height": patch_panel.u_height,
            "port_count": patch_panel.port_count,
            "connector": patch_panel.connector.value,
            "medium": patch_panel.medium.value,
            "label": patch_panel.label,
        }

    def _patch_panel_from_dict(self, value: dict[str, Any]) -> PatchPanel:
        return PatchPanel(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            site_code=Code.from_value(value["site_code"], "site code"),
            building_code=Code.from_value(value["building_code"], "building code"),
            room_code=Code.from_value(value["room_code"], "room code"),
            rack_code=Code.from_value(value["rack_code"], "rack code"),
            code=Code.from_value(value["code"], "patch panel code"),
            rack_face=RackFace.from_value(value["rack_face"]) or RackFace.FRONT,
            u_position=int(value["u_position"]),
            u_height=int(value["u_height"]),
            port_count=int(value["port_count"]),
            connector=DcimConnectorType.from_value(value["connector"]),
            medium=DcimCableMedium.from_value(value["medium"]),
            label=str(value.get("label", "")),
        )

    def _dcim_port_to_dict(self, port: DcimPort) -> dict[str, Any]:
        return {
            "id": port.id.value,
            "tenant_id": port.tenant_id.value,
            "endpoint": port.endpoint.as_dict(),
            "site_code": port.site_code.value,
            "building_code": port.building_code.value,
            "room_code": port.room_code.value,
            "connector": port.connector.value,
            "medium": port.medium.value,
            "enabled": port.enabled,
        }

    def _dcim_port_from_dict(self, value: dict[str, Any]) -> DcimPort:
        endpoint = value["endpoint"]
        return DcimPort(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            endpoint=DcimPortEndpoint.create(
                endpoint["owner_type"], endpoint["owner_code"], endpoint["port_name"]
            ),
            site_code=Code.from_value(value["site_code"], "site code"),
            building_code=Code.from_value(value["building_code"], "building code"),
            room_code=Code.from_value(value["room_code"], "room code"),
            connector=DcimConnectorType.from_value(value["connector"]),
            medium=DcimCableMedium.from_value(value["medium"]),
            enabled=bool(value.get("enabled", True)),
        )

    def _dcim_cable_to_dict(self, cable: DcimCable) -> dict[str, Any]:
        return {
            "id": cable.id.value,
            "tenant_id": cable.tenant_id.value,
            "cable_id": cable.cable_id.value,
            "a_endpoint": cable.a_endpoint.as_dict(),
            "b_endpoint": cable.b_endpoint.as_dict(),
            "medium": cable.medium.value,
            "status": cable.status.value,
            "path": [segment.as_dict() for segment in cable.path],
            "length_m": cable.length_m,
            "label": cable.label,
        }

    def _dcim_cable_from_dict(self, value: dict[str, Any]) -> DcimCable:
        a_endpoint = value["a_endpoint"]
        b_endpoint = value["b_endpoint"]
        return DcimCable(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            cable_id=Code.from_value(value["cable_id"], "cable id"),
            a_endpoint=DcimPortEndpoint.create(
                a_endpoint["owner_type"], a_endpoint["owner_code"], a_endpoint["port_name"]
            ),
            b_endpoint=DcimPortEndpoint.create(
                b_endpoint["owner_type"], b_endpoint["owner_code"], b_endpoint["port_name"]
            ),
            medium=DcimCableMedium.from_value(value["medium"]),
            status=DcimCableStatus.from_value(value["status"]),
            path=tuple(
                DcimCablePathSegment.create(
                    int(segment["order"]), str(segment["label"]), str(segment.get("kind", "path"))
                )
                for segment in value.get("path", [])
            ),
            length_m=(float(value["length_m"]) if value.get("length_m") is not None else None),
            label=str(value.get("label", "")),
        )


class JsonIpamRepository(IpamRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def add_vrf(self, vrf: Vrf) -> None:
        key = self._key(vrf.tenant_id, vrf.name.value)
        if key in self._store.data["vrfs"]:
            raise ConflictError(f"duplicate vrf: {key}")
        self._store.data["vrfs"][key] = self._vrf_to_dict(vrf)
        self._store.mark_dirty()

    def add_or_get_vrf(self, vrf: Vrf) -> Vrf:
        key = self._key(vrf.tenant_id, vrf.name.value)
        existing = self._store.data["vrfs"].get(key)
        if existing:
            return self._vrf_from_dict(existing)
        self._store.data["vrfs"][key] = self._vrf_to_dict(vrf)
        self._store.mark_dirty()
        return vrf

    def list_vrfs(self, tenant_id: TenantId) -> tuple[Vrf, ...]:
        return tuple(
            self._vrf_from_dict(value)
            for value in self._store.data["vrfs"].values()
            if value["tenant_id"] == tenant_id.value
        )

    def add_aggregate(self, aggregate: IpAggregate) -> IpAggregate:
        self.add_or_get_vrf(Vrf.create(aggregate.tenant_id, aggregate.vrf_name.value))
        key = self._key(aggregate.tenant_id, aggregate.vrf_name.value, str(aggregate.network))
        if key in self._store.data["ip_aggregates"]:
            return self._aggregate_from_dict(self._store.data["ip_aggregates"][key])
        self._store.data["ip_aggregates"][key] = self._aggregate_to_dict(aggregate)
        self._store.mark_dirty()
        return aggregate

    def list_aggregates(self, tenant_id: TenantId, vrf_name: str) -> tuple[IpAggregate, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value
        return tuple(
            self._aggregate_from_dict(value)
            for value in self._store.data["ip_aggregates"].values()
            if value["tenant_id"] == tenant_id.value and value["vrf_name"] == normalized_vrf
        )

    def get_or_create_prefix(self, prefix: Prefix) -> Prefix:
        self.add_or_get_vrf(Vrf.create(prefix.tenant_id, prefix.vrf_name.value))
        key = self._key(prefix.tenant_id, prefix.vrf_name.value, str(prefix.network))
        existing = self._store.data["prefixes"].get(key)
        if existing:
            return self._prefix_from_dict(existing)
        self._store.data["prefixes"][key] = self._prefix_to_dict(prefix)
        self._store.mark_dirty()
        return prefix

    def list_prefixes(self, tenant_id: TenantId, vrf_name: str) -> tuple[Prefix, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value
        return tuple(
            self._prefix_from_dict(value)
            for value in self._store.data["prefixes"].values()
            if value["tenant_id"] == tenant_id.value and value["vrf_name"] == normalized_vrf
        )

    def add_range(self, ip_range: IpRange) -> IpRange:
        key = self._key(
            ip_range.tenant_id,
            ip_range.vrf_name.value,
            ip_range.prefix,
            str(ip_range.start),
            str(ip_range.end),
        )
        if key in self._store.data["ip_ranges"]:
            return self._range_from_dict(self._store.data["ip_ranges"][key])
        self._store.data["ip_ranges"][key] = self._range_to_dict(ip_range)
        self._store.mark_dirty()
        return ip_range

    def list_ranges(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpRange, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value
        return tuple(
            self._range_from_dict(value)
            for value in self._store.data["ip_ranges"].values()
            if value["tenant_id"] == tenant_id.value
            and value["vrf_name"] == normalized_vrf
            and value["prefix"] == prefix_cidr
        )

    def upsert_address_record(self, record: IpAddressRecord) -> IpAddressRecord:
        key = self._key(record.tenant_id, record.vrf_name.value, str(record.address))
        self._store.data["ip_address_records"][key] = self._address_record_to_dict(record)
        self._store.mark_dirty()
        return record

    def list_address_records(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpAddressRecord, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value
        return tuple(
            self._address_record_from_dict(value)
            for value in self._store.data["ip_address_records"].values()
            if value["tenant_id"] == tenant_id.value
            and value["vrf_name"] == normalized_vrf
            and value["prefix"] == prefix_cidr
        )

    def acquire_allocation_lock(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> None:
        TenantId.from_value(tenant_id.value)
        Name.from_value(vrf_name, "vrf name")
        if not prefix_cidr.strip():
            raise ValidationError("allocation prefix is mandatory")

    def find_reservation_by_key(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        idempotency_key: str,
    ) -> IpReservation | None:
        normalized = self._key(tenant_id, Name.from_value(vrf_name).value, idempotency_key.strip())
        item = self._store.data["ip_reservations"].get(normalized)
        return self._reservation_from_dict(item) if item else None

    def list_reservations(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpReservation, ...]:
        matching: list[IpReservation] = []
        normalized_vrf = Name.from_value(vrf_name).value
        for value in self._store.data["ip_reservations"].values():
            if (
                value["tenant_id"] == tenant_id.value
                and value["vrf_name"] == normalized_vrf
                and value["prefix"] == prefix_cidr
            ):
                matching.append(self._reservation_from_dict(value))
        return tuple(matching)

    def add_reservation(self, reservation: IpReservation) -> None:
        key = self._key(
            reservation.tenant_id,
            reservation.vrf_name.value,
            reservation.idempotency_key,
        )
        if key in self._store.data["ip_reservations"]:
            raise ConflictError(f"duplicate ip idempotency key: {key}")
        for value in self._store.data["ip_reservations"].values():
            if (
                value["tenant_id"] == reservation.tenant_id.value
                and value["vrf_name"] == reservation.vrf_name.value
                and value["address"] == str(reservation.address)
            ):
                raise ConflictError(f"duplicate ip address: {reservation.address}")
        self._store.data["ip_reservations"][key] = self._reservation_to_dict(reservation)
        self._store.mark_dirty()

    def add_dns_observation(self, record: ObservedDnsRecord) -> ObservedDnsRecord:
        key = self._key(
            record.tenant_id, record.vrf_name.value, record.hostname, str(record.address)
        )
        self._store.data["dns_observations"][key] = self._dns_observation_to_dict(record)
        self._store.mark_dirty()
        return record

    def list_dns_observations(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[ObservedDnsRecord, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value if vrf_name else None
        return tuple(
            self._dns_observation_from_dict(value)
            for value in self._store.data["dns_observations"].values()
            if value["tenant_id"] == tenant_id.value
            and (normalized_vrf is None or value["vrf_name"] == normalized_vrf)
        )

    def add_dhcp_lease(self, lease: ObservedDhcpLease) -> ObservedDhcpLease:
        key = self._key(
            lease.tenant_id,
            lease.vrf_name.value,
            lease.prefix,
            str(lease.address),
            lease.mac_address,
        )
        self._store.data["dhcp_leases"][key] = self._dhcp_lease_to_dict(lease)
        self._store.mark_dirty()
        return lease

    def list_dhcp_leases(
        self, tenant_id: TenantId, vrf_name: str | None = None, active_only: bool = True
    ) -> tuple[ObservedDhcpLease, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value if vrf_name else None
        return tuple(
            self._dhcp_lease_from_dict(value)
            for value in self._store.data["dhcp_leases"].values()
            if value["tenant_id"] == tenant_id.value
            and (normalized_vrf is None or value["vrf_name"] == normalized_vrf)
            and (not active_only or bool(value.get("active", True)))
        )

    def add_vlan_group(self, group: VlanGroup) -> VlanGroup:
        key = self._key(group.tenant_id, group.name.value)
        existing = self._store.data["vlan_groups"].get(key)
        if existing:
            return self._vlan_group_from_dict(existing)
        self._store.data["vlan_groups"][key] = self._vlan_group_to_dict(group)
        self._store.mark_dirty()
        return group

    def list_vlan_groups(self, tenant_id: TenantId) -> tuple[VlanGroup, ...]:
        return tuple(
            self._vlan_group_from_dict(value)
            for value in self._store.data["vlan_groups"].values()
            if value["tenant_id"] == tenant_id.value
        )

    def add_vlan(self, vlan: Vlan) -> Vlan:
        key = self._key(vlan.tenant_id, vlan.group_name.value, str(vlan.vlan_id))
        existing = self._store.data["vlans"].get(key)
        if existing:
            return self._vlan_from_dict(existing)
        self._store.data["vlans"][key] = self._vlan_to_dict(vlan)
        self._store.mark_dirty()
        return vlan

    def list_vlans(self, tenant_id: TenantId, vrf_name: str | None = None) -> tuple[Vlan, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value if vrf_name else None
        return tuple(
            self._vlan_from_dict(value)
            for value in self._store.data["vlans"].values()
            if value["tenant_id"] == tenant_id.value
            and (normalized_vrf is None or value.get("vrf_name") == normalized_vrf)
        )

    def add_vxlan_vni(self, vni: VxlanVni) -> VxlanVni:
        key = self._key(vni.tenant_id, str(vni.vni))
        existing = self._store.data["vxlan_vnis"].get(key)
        if existing:
            return self._vxlan_vni_from_dict(existing)
        self._store.data["vxlan_vnis"][key] = self._vxlan_vni_to_dict(vni)
        self._store.mark_dirty()
        return vni

    def find_vxlan_vni(self, tenant_id: TenantId, vni: int) -> VxlanVni | None:
        item = self._store.data["vxlan_vnis"].get(self._key(tenant_id, str(vni)))
        return self._vxlan_vni_from_dict(item) if item else None

    def list_vxlan_vnis(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[VxlanVni, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value if vrf_name else None
        return tuple(
            self._vxlan_vni_from_dict(value)
            for value in self._store.data["vxlan_vnis"].values()
            if value["tenant_id"] == tenant_id.value
            and (normalized_vrf is None or value["vrf_name"] == normalized_vrf)
        )

    def add_asn(self, asn: AutonomousSystem) -> AutonomousSystem:
        key = self._key(asn.tenant_id, str(asn.number))
        existing = self._store.data["autonomous_systems"].get(key)
        if existing:
            return self._asn_from_dict(existing)
        self._store.data["autonomous_systems"][key] = self._asn_to_dict(asn)
        self._store.mark_dirty()
        return asn

    def find_asn(self, tenant_id: TenantId, number: int) -> AutonomousSystem | None:
        item = self._store.data["autonomous_systems"].get(self._key(tenant_id, str(number)))
        return self._asn_from_dict(item) if item else None

    def list_asns(self, tenant_id: TenantId) -> tuple[AutonomousSystem, ...]:
        return tuple(
            self._asn_from_dict(value)
            for value in self._store.data["autonomous_systems"].values()
            if value["tenant_id"] == tenant_id.value
        )

    def add_bgp_peer(self, peer: BgpPeer) -> BgpPeer:
        key = self._key(
            peer.tenant_id, peer.vrf_name.value, str(peer.local_asn), str(peer.peer_address)
        )
        existing = self._store.data["bgp_peers"].get(key)
        if existing:
            return self._bgp_peer_from_dict(existing)
        self._store.data["bgp_peers"][key] = self._bgp_peer_to_dict(peer)
        self._store.mark_dirty()
        return peer

    def list_bgp_peers(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[BgpPeer, ...]:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value if vrf_name else None
        return tuple(
            self._bgp_peer_from_dict(value)
            for value in self._store.data["bgp_peers"].values()
            if value["tenant_id"] == tenant_id.value
            and (normalized_vrf is None or value["vrf_name"] == normalized_vrf)
        )

    def _key(self, tenant_id: TenantId, *parts: str) -> str:
        return ":".join((tenant_id.value, *parts))

    def _vrf_to_dict(self, vrf: Vrf) -> dict[str, Any]:
        return {
            "id": vrf.id.value,
            "tenant_id": vrf.tenant_id.value,
            "name": vrf.name.value,
            "route_distinguisher": vrf.route_distinguisher,
        }

    def _vrf_from_dict(self, value: dict[str, Any]) -> Vrf:
        return Vrf(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=Name.from_value(value["name"], "vrf name"),
            route_distinguisher=value.get("route_distinguisher"),
        )

    def _aggregate_to_dict(self, aggregate: IpAggregate) -> dict[str, Any]:
        return {
            "id": aggregate.id.value,
            "tenant_id": aggregate.tenant_id.value,
            "vrf_name": aggregate.vrf_name.value,
            "network": str(aggregate.network),
            "description": aggregate.description,
        }

    def _aggregate_from_dict(self, value: dict[str, Any]) -> IpAggregate:
        aggregate = IpAggregate.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["network"],
            value["description"],
        )
        return IpAggregate(
            id=EntityId.from_value(value["id"]),
            tenant_id=aggregate.tenant_id,
            vrf_name=aggregate.vrf_name,
            network=aggregate.network,
            description=aggregate.description,
        )

    def _prefix_to_dict(self, prefix: Prefix) -> dict[str, Any]:
        return {
            "id": prefix.id.value,
            "tenant_id": prefix.tenant_id.value,
            "vrf_name": prefix.vrf_name.value,
            "network": str(prefix.network),
            "description": prefix.description,
        }

    def _prefix_from_dict(self, value: dict[str, Any]) -> Prefix:
        return Prefix(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            vrf_name=Name.from_value(value["vrf_name"]),
            network=ipaddress.ip_network(value["network"], strict=True),
            description=value["description"],
        )

    def _range_to_dict(self, ip_range: IpRange) -> dict[str, Any]:
        return {
            "id": ip_range.id.value,
            "tenant_id": ip_range.tenant_id.value,
            "vrf_name": ip_range.vrf_name.value,
            "prefix": ip_range.prefix,
            "start": str(ip_range.start),
            "end": str(ip_range.end),
            "purpose": ip_range.purpose.value,
            "description": ip_range.description,
        }

    def _range_from_dict(self, value: dict[str, Any]) -> IpRange:
        prefix = Prefix.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["prefix"],
        )
        ip_range = IpRange.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            prefix,
            value["start"],
            value["end"],
            value["purpose"],
            value["description"],
        )
        return IpRange(
            id=EntityId.from_value(value["id"]),
            tenant_id=ip_range.tenant_id,
            vrf_name=ip_range.vrf_name,
            prefix=ip_range.prefix,
            start=ip_range.start,
            end=ip_range.end,
            purpose=ip_range.purpose,
            description=ip_range.description,
        )

    def _address_record_to_dict(self, record: IpAddressRecord) -> dict[str, Any]:
        return {
            "id": record.id.value,
            "tenant_id": record.tenant_id.value,
            "vrf_name": record.vrf_name.value,
            "prefix": record.prefix,
            "address": str(record.address),
            "hostname": record.hostname,
            "interface_name": record.interface_name.value if record.interface_name else None,
            "status": record.status.value,
        }

    def _address_record_from_dict(self, value: dict[str, Any]) -> IpAddressRecord:
        prefix = Prefix.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["prefix"],
        )
        record = IpAddressRecord.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            prefix,
            value["address"],
            value["hostname"],
            value.get("interface_name"),
            value["status"],
        )
        return IpAddressRecord(
            id=EntityId.from_value(value["id"]),
            tenant_id=record.tenant_id,
            vrf_name=record.vrf_name,
            prefix=record.prefix,
            address=record.address,
            hostname=record.hostname,
            interface_name=record.interface_name,
            status=record.status,
        )

    def _reservation_to_dict(self, reservation: IpReservation) -> dict[str, Any]:
        return {
            "id": reservation.id.value,
            "tenant_id": reservation.tenant_id.value,
            "vrf_name": reservation.vrf_name.value,
            "prefix": reservation.prefix,
            "address": str(reservation.address),
            "hostname": reservation.hostname,
            "idempotency_key": reservation.idempotency_key,
        }

    def _reservation_from_dict(self, value: dict[str, Any]) -> IpReservation:
        prefix = Prefix.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["prefix"],
        )
        reservation = IpReservation.create(
            tenant_id=TenantId.from_value(value["tenant_id"]),
            vrf_name=value["vrf_name"],
            prefix=prefix,
            address=value["address"],
            hostname=value["hostname"],
            idempotency_key=value["idempotency_key"],
        )
        return IpReservation(
            id=EntityId.from_value(value["id"]),
            tenant_id=reservation.tenant_id,
            vrf_name=reservation.vrf_name,
            prefix=reservation.prefix,
            address=reservation.address,
            hostname=reservation.hostname,
            idempotency_key=reservation.idempotency_key,
        )

    def _dns_observation_to_dict(self, record: ObservedDnsRecord) -> dict[str, Any]:
        return {
            "id": record.id.value,
            "tenant_id": record.tenant_id.value,
            "vrf_name": record.vrf_name.value,
            "hostname": record.hostname,
            "address": str(record.address),
            "ptr_hostname": record.ptr_hostname,
            "source": record.source,
        }

    def _dns_observation_from_dict(self, value: dict[str, Any]) -> ObservedDnsRecord:
        record = ObservedDnsRecord.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["hostname"],
            value["address"],
            value.get("ptr_hostname"),
            value.get("source", "manual"),
        )
        return ObservedDnsRecord(
            id=EntityId.from_value(value["id"]),
            tenant_id=record.tenant_id,
            vrf_name=record.vrf_name,
            hostname=record.hostname,
            address=record.address,
            ptr_hostname=record.ptr_hostname,
            source=record.source,
        )

    def _dhcp_lease_to_dict(self, lease: ObservedDhcpLease) -> dict[str, Any]:
        return {
            "id": lease.id.value,
            "tenant_id": lease.tenant_id.value,
            "vrf_name": lease.vrf_name.value,
            "prefix": lease.prefix,
            "address": str(lease.address),
            "mac_address": lease.mac_address,
            "hostname": lease.hostname,
            "source": lease.source,
            "active": lease.active,
        }

    def _dhcp_lease_from_dict(self, value: dict[str, Any]) -> ObservedDhcpLease:
        lease = ObservedDhcpLease.create(
            TenantId.from_value(value["tenant_id"]),
            value["vrf_name"],
            value["prefix"],
            value["address"],
            value["mac_address"],
            str(value.get("hostname", "")),
            str(value.get("source", "manual")),
            bool(value.get("active", True)),
        )
        return ObservedDhcpLease(
            id=EntityId.from_value(value["id"]),
            tenant_id=lease.tenant_id,
            vrf_name=lease.vrf_name,
            prefix=lease.prefix,
            address=lease.address,
            mac_address=lease.mac_address,
            hostname=lease.hostname,
            source=lease.source,
            active=lease.active,
        )

    def _vlan_group_to_dict(self, group: VlanGroup) -> dict[str, Any]:
        return {
            "id": group.id.value,
            "tenant_id": group.tenant_id.value,
            "name": group.name.value,
            "scope": group.scope.value if group.scope else None,
            "description": group.description,
        }

    def _vlan_group_from_dict(self, value: dict[str, Any]) -> VlanGroup:
        return VlanGroup(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=Name.from_value(value["name"], "vlan group name"),
            scope=Code.from_value(value["scope"], "vlan group scope")
            if value.get("scope")
            else None,
            description=str(value.get("description", "")),
        )

    def _vlan_to_dict(self, vlan: Vlan) -> dict[str, Any]:
        return {
            "id": vlan.id.value,
            "tenant_id": vlan.tenant_id.value,
            "group_name": vlan.group_name.value,
            "vlan_id": vlan.vlan_id,
            "name": vlan.name.value,
            "vrf_name": vlan.vrf_name.value if vlan.vrf_name else None,
            "vni": vlan.vni,
            "description": vlan.description,
        }

    def _vlan_from_dict(self, value: dict[str, Any]) -> Vlan:
        return Vlan(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            group_name=Name.from_value(value["group_name"], "vlan group name"),
            vlan_id=int(value["vlan_id"]),
            name=Name.from_value(value["name"], "vlan name"),
            vrf_name=Name.from_value(value["vrf_name"], "vrf name")
            if value.get("vrf_name")
            else None,
            vni=int(value["vni"]) if value.get("vni") is not None else None,
            description=str(value.get("description", "")),
        )

    def _vxlan_vni_to_dict(self, vni: VxlanVni) -> dict[str, Any]:
        return {
            "id": vni.id.value,
            "tenant_id": vni.tenant_id.value,
            "vni": vni.vni,
            "name": vni.name.value,
            "vrf_name": vni.vrf_name.value,
            "route_targets_import": list(vni.route_targets_import),
            "route_targets_export": list(vni.route_targets_export),
            "description": vni.description,
        }

    def _vxlan_vni_from_dict(self, value: dict[str, Any]) -> VxlanVni:
        return VxlanVni(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            vni=int(value["vni"]),
            name=Name.from_value(value["name"], "vni name"),
            vrf_name=Name.from_value(value["vrf_name"], "vrf name"),
            route_targets_import=tuple(str(item) for item in value.get("route_targets_import", [])),
            route_targets_export=tuple(str(item) for item in value.get("route_targets_export", [])),
            description=str(value.get("description", "")),
        )

    def _asn_to_dict(self, asn: AutonomousSystem) -> dict[str, Any]:
        return {
            "id": asn.id.value,
            "tenant_id": asn.tenant_id.value,
            "number": asn.number,
            "name": asn.name.value,
            "description": asn.description,
        }

    def _asn_from_dict(self, value: dict[str, Any]) -> AutonomousSystem:
        return AutonomousSystem(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            number=int(value["number"]),
            name=Name.from_value(value["name"], "asn name"),
            description=str(value.get("description", "")),
        )

    def _bgp_peer_to_dict(self, peer: BgpPeer) -> dict[str, Any]:
        return {
            "id": peer.id.value,
            "tenant_id": peer.tenant_id.value,
            "vrf_name": peer.vrf_name.value,
            "local_asn": peer.local_asn,
            "remote_asn": peer.remote_asn,
            "peer_address": str(peer.peer_address),
            "address_family": peer.address_family.value,
            "route_targets_import": list(peer.route_targets_import),
            "route_targets_export": list(peer.route_targets_export),
            "description": peer.description,
        }

    def _bgp_peer_from_dict(self, value: dict[str, Any]) -> BgpPeer:
        return BgpPeer(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            vrf_name=Name.from_value(value["vrf_name"], "vrf name"),
            local_asn=int(value["local_asn"]),
            remote_asn=int(value["remote_asn"]),
            peer_address=ipaddress.ip_address(str(value["peer_address"])),
            address_family=BgpAddressFamily.from_value(str(value["address_family"])),
            route_targets_import=tuple(str(item) for item in value.get("route_targets_import", [])),
            route_targets_export=tuple(str(item) for item in value.get("route_targets_export", [])),
            description=str(value.get("description", "")),
        )


class JsonIdentityRepository(IdentityRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_user(self, user: IdentityUser) -> None:
        key = self._user_key(user.tenant_id, user.username)
        previous = self._store.data["identity_users"].get(key, {})
        payload = self._user_to_dict(user)
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["identity_users"][key] = payload
        self._store.mark_dirty()

    def upsert_group(self, group: IdentityGroup) -> None:
        key = self._group_key(group.tenant_id, group.name)
        previous = self._store.data["identity_groups"].get(key, {})
        payload = self._group_to_dict(group)
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["identity_groups"][key] = payload
        self._store.mark_dirty()

    def add_membership(self, membership: GroupMembership) -> None:
        user_key = self._user_key(membership.tenant_id, membership.username)
        group_key = self._group_key(membership.tenant_id, membership.group_name)
        if user_key not in self._store.data["identity_users"]:
            raise ValidationError("identity user must exist before group membership")
        if group_key not in self._store.data["identity_groups"]:
            raise ValidationError("identity group must exist before group membership")
        membership_key = self._membership_key(
            membership.tenant_id,
            membership.username,
            membership.group_name,
        )
        self._store.data["identity_memberships"][membership_key] = membership.as_dict()
        self._store.mark_dirty()

    def grant_user_role(self, tenant_id: TenantId, username: str, role: str) -> bool:
        key = self._user_key(tenant_id, username)
        value = self._store.data["identity_users"].get(key)
        if value is None:
            raise ValidationError("identity user must exist before granting a role")
        role_name = IdentityRoleSet.from_names((role,))[0].name
        roles = {str(item) for item in value.get("roles", [])}
        changed = role_name not in roles
        roles.add(role_name)
        value["roles"] = sorted(roles)
        self._store.mark_dirty()
        return changed

    def grant_group_role(self, tenant_id: TenantId, group_name: str, role: str) -> bool:
        key = self._group_key(tenant_id, group_name)
        value = self._store.data["identity_groups"].get(key)
        if value is None:
            raise ValidationError("identity group must exist before granting a role")
        role_name = IdentityRoleSet.from_names((role,))[0].name
        roles = {str(item) for item in value.get("roles", [])}
        changed = role_name not in roles
        roles.add(role_name)
        value["roles"] = sorted(roles)
        self._store.mark_dirty()
        return changed

    def effective_identity_for_subject(
        self,
        tenant_id: TenantId,
        subject: str,
    ) -> EffectiveIdentity:
        username = IdentitySubject.normalize(subject)
        user_value = self._store.data["identity_users"].get(self._user_key(tenant_id, username))
        if user_value is None:
            return EffectiveIdentity.empty(tenant_id, username)
        user = self._user_from_dict(user_value)
        group_names: list[str] = []
        group_roles: list[str] = []
        for value in self._store.data["identity_memberships"].values():
            if value.get("tenant_id") != tenant_id.value or value.get("username") != username:
                continue
            group_key = self._group_key(tenant_id, str(value["group_name"]))
            group_value = self._store.data["identity_groups"].get(group_key)
            if group_value is not None and bool(group_value.get("active", True)):
                group_names.append(str(group_value["name"]))
                group_roles.extend(str(role) for role in group_value.get("roles", []))
        return EffectiveIdentity.from_parts(user, tuple(group_names), tuple(group_roles))

    def _user_key(self, tenant_id: TenantId, username: str) -> str:
        return ":".join((tenant_id.value, IdentitySubject.normalize(username)))

    def _group_key(self, tenant_id: TenantId, group_name: str) -> str:
        return ":".join((tenant_id.value, IdentityGroupName.normalize(group_name)))

    def _membership_key(self, tenant_id: TenantId, username: str, group_name: str) -> str:
        return ":".join((tenant_id.value, username, group_name))

    def _user_to_dict(self, user: IdentityUser) -> dict[str, Any]:
        return user.as_dict()

    def _group_to_dict(self, group: IdentityGroup) -> dict[str, Any]:
        return group.as_dict()

    def _user_from_dict(self, value: dict[str, Any]) -> IdentityUser:
        return IdentityUser.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            username=value["username"],
            display_name=value["display_name"],
            email=value.get("email"),
            roles=tuple(value.get("roles", [])),
            active=bool(value.get("active", True)),
            created_at=self._parse_datetime(value["created_at"]),
        )

    def _group_from_dict(self, value: dict[str, Any]) -> IdentityGroup:
        return IdentityGroup.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=value["name"],
            display_name=value["display_name"],
            roles=tuple(value.get("roles", [])),
            active=bool(value.get("active", True)),
            created_at=self._parse_datetime(value["created_at"]),
        )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class JsonSecurityRepository(SecurityRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_token(self, credential: ApiTokenCredential) -> None:
        key = self._key(credential.tenant_id, credential.token_hash)
        previous = self._store.data["security_tokens"].get(key, {})
        payload = self._credential_to_dict(credential)
        if previous.get("last_used_at") is not None and credential.last_used_at is None:
            payload["last_used_at"] = previous["last_used_at"]
        if previous.get("use_count") is not None and credential.use_count == 0:
            payload["use_count"] = int(previous["use_count"])
        self._store.data["security_tokens"][key] = payload
        self._store.mark_dirty()

    def find_active_token_by_hash(
        self,
        tenant_id: TenantId,
        token_hash: str,
    ) -> ApiTokenCredential | None:
        key = self._key(tenant_id, token_hash)
        value = self._store.data["security_tokens"].get(key)
        if value is None:
            return None
        credential = self._credential_from_dict(value)
        return credential if credential.is_usable() else None

    def revoke_token(self, tenant_id: TenantId, token_hash: str, actor: str) -> bool:
        key = self._key(tenant_id, token_hash)
        value = self._store.data["security_tokens"].get(key)
        if value is None:
            return False
        credential = self._credential_from_dict(value)
        if credential.is_revoked():
            return False
        self._store.data["security_tokens"][key] = self._credential_to_dict(
            credential.revoked(actor)
        )
        self._store.mark_dirty()
        return True

    def list_tokens(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> SecurityTokenPage:
        try:
            start = int(pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if start < 0:
            raise ValidationError("pagination cursor must be positive")
        credentials = [
            self._credential_from_dict(value)
            for value in self._store.data["security_tokens"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if not include_inactive:
            credentials = [credential for credential in credentials if credential.is_usable()]
        credentials.sort(key=lambda item: (item.created_at.isoformat(), item.id.value))
        selected = tuple(credentials[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(credentials) else None
        return SecurityTokenPage(selected, next_cursor)

    def record_token_used(self, tenant_id: TenantId, token_hash: str) -> None:
        key = self._key(tenant_id, token_hash)
        value = self._store.data["security_tokens"].get(key)
        if value is not None:
            value["last_used_at"] = datetime.now(UTC).isoformat()
            value["use_count"] = int(value.get("use_count", 0)) + 1
            self._store.mark_dirty()

    def _key(self, tenant_id: TenantId, token_hash: str) -> str:
        return ":".join((tenant_id.value, token_hash))

    def _credential_to_dict(self, credential: ApiTokenCredential) -> dict[str, Any]:
        return {
            "id": credential.id.value,
            "tenant_id": credential.tenant_id.value,
            "subject": credential.subject,
            "token_hash": credential.token_hash,
            "token_prefix": credential.token_prefix,
            "roles": list(credential.role_names()),
            "active": credential.active,
            "created_at": credential.created_at.isoformat(),
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
            "revoked_at": credential.revoked_at.isoformat() if credential.revoked_at else None,
            "revoked_by": credential.revoked_by,
            "last_used_at": (
                credential.last_used_at.isoformat() if credential.last_used_at else None
            ),
            "use_count": credential.use_count,
        }

    def _credential_from_dict(self, value: dict[str, Any]) -> ApiTokenCredential:
        return ApiTokenCredential.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            subject=value["subject"],
            token_hash=value["token_hash"],
            token_prefix=value["token_prefix"],
            roles=tuple(value["roles"]),
            active=bool(value["active"]),
            created_at=self._parse_datetime(value["created_at"]),
            expires_at=self._parse_optional_datetime(value.get("expires_at")),
            revoked_at=self._parse_optional_datetime(value.get("revoked_at")),
            revoked_by=value.get("revoked_by"),
            last_used_at=self._parse_optional_datetime(value.get("last_used_at")),
            use_count=int(value.get("use_count", 0)),
        )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _parse_optional_datetime(self, value: object) -> datetime | None:
        if value is None:
            return None
        return self._parse_datetime(value)


class JsonAccessPolicyRepository(AccessPolicyRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_rule(self, rule: AccessPolicyRule) -> None:
        key = self._key(rule.tenant_id, rule.name)
        previous = self._store.data["access_policy_rules"].get(key, {})
        payload = rule.as_dict()
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["access_policy_rules"][key] = payload
        self._store.mark_dirty()

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> AccessPolicyRulePage:
        try:
            start = int(pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if start < 0:
            raise ValidationError("pagination cursor must be positive")
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["access_policy_rules"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if not include_inactive:
            rules = [rule for rule in rules if rule.active]
        rules.sort(key=lambda item: (item.name, item.id.value))
        selected = tuple(rules[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(rules) else None
        return AccessPolicyRulePage(selected, next_cursor)

    def find_active_rules_for_permission(
        self,
        tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[AccessPolicyRule, ...]:
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["access_policy_rules"].values()
            if value.get("tenant_id") == tenant_id.value
            and value.get("permission") == permission.value
            and bool(value.get("active", True))
        ]
        rules.sort(key=lambda item: (item.name, item.id.value))
        return tuple(rules)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        normalized_name = AccessPolicyRule.create(
            tenant_id,
            name,
            Permission.SCHEMA_READ,
            "allow",
        ).name
        key = self._key(tenant_id, normalized_name)
        value = self._store.data["access_policy_rules"].get(key)
        if value is None or bool(value.get("active")) is False:
            return False
        value["active"] = False
        self._store.mark_dirty()
        return True

    def _key(self, tenant_id: TenantId, name: str) -> str:
        return ":".join((tenant_id.value, name))

    def _rule_from_dict(self, value: dict[str, Any]) -> AccessPolicyRule:
        return AccessPolicyRule.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=value["name"],
            permission=value["permission"],
            effect=value["effect"],
            subjects=tuple(value.get("subjects", [])),
            roles=tuple(value.get("roles", [])),
            site_codes=tuple(value.get("site_codes", [])),
            environments=tuple(value.get("environments", [])),
            active=bool(value.get("active", True)),
            created_at=self._parse_datetime(value["created_at"]),
        )

    def _parse_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class JsonSourceGovernanceRepository(SourceGovernanceRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def upsert_rule(self, rule: SourceGovernanceRule) -> None:
        key = self._key(rule.tenant_id, rule.name.value)
        previous = self._store.data["source_governance_rules"].get(key, {})
        payload = rule.as_dict()
        if previous.get("created_at") is not None:
            payload["created_at"] = previous["created_at"]
            payload["id"] = previous["id"]
        self._store.data["source_governance_rules"][key] = payload
        self._store.mark_dirty()

    def find_rule(self, tenant_id: TenantId, name: str) -> SourceGovernanceRule | None:
        key = self._key(tenant_id, name.strip().lower())
        value = self._store.data["source_governance_rules"].get(key)
        return self._rule_from_dict(value) if value else None

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool = False,
        object_kind: str | None = None,
    ) -> SourceGovernanceRulePage:
        start = self._cursor_offset(pagination.cursor)
        normalized_kind = object_kind.strip().lower() if object_kind else None
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["source_governance_rules"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if not include_inactive:
            rules = [rule for rule in rules if rule.active]
        if normalized_kind:
            rules = [
                rule
                for rule in rules
                if rule.object_kind is None or rule.object_kind.value == normalized_kind
            ]
        rules.sort(key=lambda item: (-item.priority, item.name.value, item.id.value))
        selected = tuple(rules[start : start + pagination.limit])
        next_index = start + len(selected)
        return SourceGovernanceRulePage(
            selected,
            str(next_index) if next_index < len(rules) else None,
        )

    def find_active_rules_for_kind(
        self,
        tenant_id: TenantId,
        object_kind: str,
    ) -> tuple[SourceGovernanceRule, ...]:
        normalized_kind = object_kind.strip().lower()
        rules = [
            self._rule_from_dict(value)
            for value in self._store.data["source_governance_rules"].values()
            if value.get("tenant_id") == tenant_id.value and bool(value.get("active", True))
        ]
        rules = [
            rule
            for rule in rules
            if rule.object_kind is None or rule.object_kind.value == normalized_kind
        ]
        rules.sort(key=lambda item: (-item.priority, item.name.value, item.id.value))
        return tuple(rules)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        key = self._key(tenant_id, name.strip().lower())
        value = self._store.data["source_governance_rules"].get(key)
        if value is None or bool(value.get("active")) is False:
            return False
        value["active"] = False
        self._store.mark_dirty()
        return True

    def _cursor_offset(self, cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    def _key(self, tenant_id: TenantId, name: str) -> str:
        return ":".join((tenant_id.value, name))

    def _rule_from_dict(self, value: dict[str, Any]) -> SourceGovernanceRule:
        created_at = datetime.fromisoformat(value["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        object_kind = value.get("object_kind")
        return SourceGovernanceRule.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            name=value["name"],
            object_kind=None if object_kind in (None, "*") else str(object_kind),
            attribute_path=value["attribute_path"],
            authoritative_source=value["authoritative_source"],
            priority=int(value["priority"]),
            freshness_seconds=(
                int(value["freshness_seconds"])
                if value.get("freshness_seconds") is not None
                else None
            ),
            conflict_strategy=value["conflict_strategy"],
            active=bool(value.get("active", True)),
            created_at=created_at,
        )


class JsonAuditRepository(AuditRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store
        self._hasher = AuditIntegrityHasher()

    def append(self, event: AuditEvent) -> None:
        previous_hash = self._latest_hash(event.tenant_id)
        record = AuditEventRecord.create(event, previous_hash)
        self._store.data["audit_events"].append(self._record_to_dict(record))
        self._store.mark_dirty()

    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        try:
            start = int(event_filter.pagination.cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if start < 0:
            raise ValidationError("pagination cursor must be positive")
        records = [
            self._record_from_dict(value)
            for value in self._store.data["audit_events"]
            if value.get("tenant_id") == event_filter.tenant_id.value
        ]
        records = [record for record in records if self._matches(record, event_filter)]
        records.sort(
            key=lambda item: (item.event.created_at.isoformat(), item.event.id.value),
            reverse=True,
        )
        selected = tuple(records[start : start + event_filter.pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(records) else None
        return AuditEventPage(selected, next_cursor)

    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        if not 1 <= int(limit) <= 10_000:
            raise ValidationError("audit integrity limit must be between 1 and 10000")
        records = [
            self._record_from_dict(value)
            for value in self._store.data["audit_events"]
            if value.get("tenant_id") == tenant_id.value
        ]
        records.sort(key=lambda item: (item.event.created_at.isoformat(), item.event.id.value))
        selected = records[-int(limit) :]
        previous_hash = AuditIntegrityHasher.GENESIS_HASH
        checked = 0
        for record in selected:
            if record.previous_hash != previous_hash or not record.verifies():
                return AuditIntegrityReport(
                    tenant_id=tenant_id,
                    checked=checked + 1,
                    valid=False,
                    broken_record_id=record.event.id.value,
                    head_hash=previous_hash,
                )
            previous_hash = record.record_hash
            checked += 1
        return AuditIntegrityReport(
            tenant_id=tenant_id,
            checked=checked,
            valid=True,
            broken_record_id=None,
            head_hash=previous_hash,
        )

    def list_events(self) -> tuple[AuditEvent, ...]:
        return tuple(
            self._record_from_dict(value).event for value in self._store.data["audit_events"]
        )

    def _latest_hash(self, tenant_id: TenantId) -> str:
        records = [
            self._record_from_dict(value)
            for value in self._store.data["audit_events"]
            if value.get("tenant_id") == tenant_id.value
        ]
        if not records:
            return AuditIntegrityHasher.GENESIS_HASH
        records.sort(key=lambda item: (item.event.created_at.isoformat(), item.event.id.value))
        return records[-1].record_hash

    def _matches(self, record: AuditEventRecord, event_filter: AuditEventFilter) -> bool:
        event = record.event
        if event_filter.actor is not None and event.actor != event_filter.actor:
            return False
        if event_filter.action is not None and event.action != event_filter.action:
            return False
        if event_filter.target_type is not None and event.target_type != event_filter.target_type:
            return False
        if event_filter.target_id is not None and event.target_id != event_filter.target_id:
            return False
        if event_filter.severity is not None and event.severity != event_filter.severity:
            return False
        if event_filter.created_from is not None and event.created_at < event_filter.created_from:
            return False
        return not (
            event_filter.created_to is not None and event.created_at > event_filter.created_to
        )

    def _record_to_dict(self, record: AuditEventRecord) -> dict[str, Any]:
        event = record.event
        return {
            "id": event.id.value,
            "tenant_id": event.tenant_id.value,
            "actor": event.actor,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "severity": event.severity.value,
            "created_at": event.created_at.isoformat(),
            "metadata": event.metadata,
            "previous_hash": record.previous_hash,
            "record_hash": record.record_hash,
        }

    def _record_from_dict(self, value: dict[str, Any]) -> AuditEventRecord:
        event = self._event_from_dict(value)
        previous_hash = value.get("previous_hash", AuditIntegrityHasher.GENESIS_HASH)
        record_hash = value.get("record_hash")
        if record_hash is None:
            return AuditEventRecord.create(event, str(previous_hash))
        return AuditEventRecord.restore(event, str(previous_hash), str(record_hash))

    def _event_from_dict(self, value: dict[str, Any]) -> AuditEvent:
        created_at = datetime.fromisoformat(value["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return AuditEvent(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            actor=value["actor"],
            action=value["action"],
            target_type=value["target_type"],
            target_id=value["target_id"],
            severity=Severity(value["severity"]),
            created_at=created_at,
            metadata=value["metadata"],
        )


class JsonSourceOfTruthRepository(SourceOfTruthRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def create_object(
        self,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, object],
        tags: tuple[str, ...],
        source: str,
        actor: str,
    ) -> SourceOfTruthObject:
        source_object = SourceOfTruthObject.create(
            tenant_id=tenant_id,
            key=key,
            kind=kind,
            display_name=display_name,
            attributes=attributes,
            tags=tags,
            source=source,
        )
        self.upsert_object(source_object, actor)
        return source_object

    def upsert_object(self, source_object: SourceOfTruthObject, actor: str) -> None:
        key = self._key(source_object.tenant_id, source_object.key.value)
        self._store.data["source_objects"][key] = self._object_to_dict(source_object)
        self._store.data["source_object_snapshots"].append(
            self._snapshot_to_dict(SourceObjectSnapshot.create(source_object, actor))
        )
        self._store.mark_dirty()

    def find_object(self, tenant_id: TenantId, key: str) -> SourceOfTruthObject | None:
        item = self._store.data["source_objects"].get(self._key(tenant_id, key.strip().lower()))
        return self._object_from_dict(item) if item else None

    def list_objects(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        tag: str | None = None,
        resource_type: str | None = None,
    ) -> SourceObjectPage:
        start = self._cursor_offset(pagination.cursor)
        normalized_kind = kind.strip().lower() if kind else None
        normalized_tag = tag.strip().lower() if tag else None
        normalized_resource_type = resource_type.strip().lower() if resource_type else None
        objects = [
            self._object_from_dict(value)
            for value in self._store.data["source_objects"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if normalized_kind:
            objects = [item for item in objects if item.kind.value == normalized_kind]
        if normalized_tag:
            objects = [
                item for item in objects if normalized_tag in {tag.value for tag in item.tags}
            ]
        if normalized_resource_type:
            objects = [
                item
                for item in objects
                if item.as_dict().get("resource_type") == normalized_resource_type
            ]
        objects.sort(key=lambda item: item.key.value)
        selected = tuple(objects[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(objects) else None
        return SourceObjectPage(selected, next_cursor)

    def find_object_version(
        self,
        tenant_id: TenantId,
        key: str,
        version: int,
    ) -> SourceObjectSnapshot | None:
        normalized_key = key.strip().lower()
        for value in self._store.data["source_object_snapshots"]:
            if (
                value.get("tenant_id") == tenant_id.value
                and value.get("object_key") == normalized_key
                and int(value.get("version", 0)) == int(version)
            ):
                return self._snapshot_from_dict(value)
        return None

    def find_object_as_of(
        self,
        tenant_id: TenantId,
        key: str,
        as_of: datetime,
    ) -> SourceObjectSnapshot | None:
        normalized_key = key.strip().lower()
        candidates = [
            self._snapshot_from_dict(value)
            for value in self._store.data["source_object_snapshots"]
            if value.get("tenant_id") == tenant_id.value
            and value.get("object_key") == normalized_key
        ]
        candidates = [snapshot for snapshot in candidates if snapshot.changed_at <= as_of]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.changed_at, item.version), reverse=True)
        return candidates[0]

    def add_relation(self, relation: SourceRelation) -> None:
        key = self._key(relation.tenant_id, relation.id.value)
        self._store.data["source_relations"][key] = self._relation_to_dict(relation)
        self._store.mark_dirty()

    def list_relations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_key: str | None = None,
        target_key: str | None = None,
        relation_type: str | None = None,
        as_of: datetime | None = None,
    ) -> SourceRelationPage:
        start = self._cursor_offset(pagination.cursor)
        normalized_source = source_key.strip().lower() if source_key else None
        normalized_target = target_key.strip().lower() if target_key else None
        normalized_type = relation_type.strip().lower() if relation_type else None
        relations = [
            self._relation_from_dict(value)
            for value in self._store.data["source_relations"].values()
            if value.get("tenant_id") == tenant_id.value
        ]
        if normalized_source:
            relations = [item for item in relations if item.source_key.value == normalized_source]
        if normalized_target:
            relations = [item for item in relations if item.target_key.value == normalized_target]
        if normalized_type:
            relations = [item for item in relations if item.relation_type.value == normalized_type]
        if as_of is not None:
            relations = [item for item in relations if item.is_valid_at(as_of)]
        relations.sort(key=lambda item: (item.created_at.isoformat(), item.id.value), reverse=True)
        selected = tuple(relations[start : start + pagination.limit])
        next_index = start + len(selected)
        next_cursor = str(next_index) if next_index < len(relations) else None
        return SourceRelationPage(selected, next_cursor)

    def _cursor_offset(self, cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    def _key(self, tenant_id: TenantId, *parts: str) -> str:
        return ":".join((tenant_id.value, *parts))

    def _object_to_dict(self, source_object: SourceOfTruthObject) -> dict[str, Any]:
        return source_object.as_dict()

    def _object_from_dict(self, value: dict[str, Any]) -> SourceOfTruthObject:
        created_at = datetime.fromisoformat(value["created_at"])
        updated_at = datetime.fromisoformat(value["updated_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return SourceOfTruthObject.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            key=value["key"],
            kind=value["kind"],
            display_name=value["display_name"],
            attributes=dict(value["attributes"]),
            tags=tuple(value["tags"]),
            source=value["source"],
            version=int(value["version"]),
            status=value["status"],
            created_at=created_at,
            updated_at=updated_at,
        )

    def _snapshot_to_dict(self, snapshot: SourceObjectSnapshot) -> dict[str, Any]:
        return snapshot.as_dict()

    def _snapshot_from_dict(self, value: dict[str, Any]) -> SourceObjectSnapshot:
        changed_at = datetime.fromisoformat(value["changed_at"])
        if changed_at.tzinfo is None:
            changed_at = changed_at.replace(tzinfo=UTC)
        return SourceObjectSnapshot.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            object_key=value["object_key"],
            object_id=EntityId.from_value(value["object_id"]),
            version=int(value["version"]),
            payload=dict(value["payload"]),
            changed_by=value["changed_by"],
            changed_at=changed_at,
        )

    def _relation_to_dict(self, relation: SourceRelation) -> dict[str, Any]:
        return relation.as_dict()

    def _relation_from_dict(self, value: dict[str, Any]) -> SourceRelation:
        valid_from = datetime.fromisoformat(value["valid_from"])
        created_at = datetime.fromisoformat(value["created_at"])
        valid_to = datetime.fromisoformat(value["valid_to"]) if value.get("valid_to") else None
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=UTC)
        if valid_to is not None and valid_to.tzinfo is None:
            valid_to = valid_to.replace(tzinfo=UTC)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return SourceRelation.restore(
            id=EntityId.from_value(value["id"]),
            tenant_id=TenantId.from_value(value["tenant_id"]),
            relation_type=value["relation_type"],
            source_key=value["source_key"],
            target_key=value["target_key"],
            provenance=value["provenance"],
            valid_from=valid_from,
            valid_to=valid_to,
            active=bool(value["active"]),
            created_at=created_at,
        )


class SeedDataFactory:
    def __init__(
        self,
        dcim_repository: DcimRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._dcim_repository = dcim_repository
        self._transaction_manager = transaction_manager

    def ensure_minimal_datacenter(self, tenant: str) -> None:
        tenant_id = TenantId.from_value(tenant)
        with self._transaction_manager.begin() as unit_of_work:
            self._add_if_missing(tenant_id)
            unit_of_work.commit()

    def _add_if_missing(self, tenant_id: TenantId) -> None:
        room = self._dcim_repository.find_room(tenant_id, "PAR1", "BAT-A", "MMR1")
        if room is not None:
            return
        self._dcim_repository.add_site(Site.create(tenant_id, "PAR1", "Paris 1", "FR", "Paris"))
        self._dcim_repository.add_building(
            Building.create(tenant_id, "PAR1", "BAT-A", "Building A")
        )
        self._dcim_repository.add_floor(
            Floor.create(tenant_id, "PAR1", "BAT-A", "F01", "First floor", 1)
        )
        self._dcim_repository.add_room(
            Room.create(
                tenant_id,
                "PAR1",
                "BAT-A",
                "MMR1",
                "Main Meet-Me Room",
                rows=("A", "B", "C"),
                columns=("01", "02", "12"),
                floor_code="F01",
            )
        )
        self._dcim_repository.add_rack(
            Rack.create(
                tenant_id,
                "PAR1",
                "BAT-A",
                "MMR1",
                "R42",
                "B",
                "12",
                42,
                Coordinates3D.from_values(12.0, 4.0, 0.0),
                floor_code="F01",
            )
        )


class IterableSerializer:
    def to_json_array(self, values: Iterable[dict[str, Any]]) -> str:
        return json.dumps(list(values), indent=2, sort_keys=True)


class JsonItamSupportRepository(ItamSupportRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def save_support_profile(self, profile: PhysicalAssetSupportProfile) -> None:
        key = self._key(profile.tenant_id, profile.asset_tag.value)
        self._store.data["asset_support_profiles"][key] = profile.as_dict()
        self._store.mark_dirty()

    def find_support_profile(
        self, tenant_id: TenantId, asset_tag: str
    ) -> PhysicalAssetSupportProfile | None:
        key = self._key(tenant_id, Code.from_value(asset_tag, "asset tag").value)
        value = self._store.data["asset_support_profiles"].get(key)
        if value is None:
            return None
        return self._profile_from_dict(value)

    def _key(self, tenant_id: TenantId, asset_tag: str) -> str:
        return f"{tenant_id.value}:{asset_tag.upper()}"

    def _profile_from_dict(self, value: dict[str, Any]) -> PhysicalAssetSupportProfile:
        warranty_payload = value["manufacturer_warranty"]
        warranty = ManufacturerWarranty.restore(
            manufacturer=str(warranty_payload["manufacturer"]),
            warranty_reference=str(warranty_payload["warranty_reference"]),
            warranty_level=str(warranty_payload["warranty_level"]),
            warranty_start=ItamDateParser.parse_date(
                str(warranty_payload["warranty_start"]), "manufacturer warranty start"
            ),
            warranty_end=ItamDateParser.parse_date(
                str(warranty_payload["warranty_end"]), "manufacturer warranty end"
            ),
            support_reference=str(warranty_payload["support_reference"]),
            support_level=str(warranty_payload["support_level"]),
            support_contact=str(warranty_payload["support_contact"]),
        )
        third_party_contracts = tuple(
            self._third_party_from_dict(item)
            for item in value.get("third_party_contracts", [])
            if isinstance(item, dict)
        )
        return PhysicalAssetSupportProfile.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            asset_tag=str(value["asset_tag"]),
            manufacturer_warranty=warranty,
            third_party_contracts=third_party_contracts,
            created_by=str(value["created_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_by=str(value["updated_by"]),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
        )

    def _third_party_from_dict(self, value: dict[str, Any]) -> ThirdPartySupportContract:
        return ThirdPartySupportContract.restore(
            id=EntityId.from_value(str(value["id"])),
            provider=str(value["provider"]),
            contract_reference=str(value["contract_reference"]),
            support_level=str(value["support_level"]),
            support_start=ItamDateParser.parse_date(str(value["support_start"]), "third-party support start"),
            support_end=ItamDateParser.parse_date(str(value["support_end"]), "third-party support end"),
            support_contact=str(value["support_contact"]),
            status=str(value["status"]),
            notes=(None if value.get("notes") is None else str(value.get("notes"))),
            created_at=datetime.fromisoformat(str(value["created_at"])),
        )
