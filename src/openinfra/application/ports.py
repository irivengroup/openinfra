from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.audit import AuditEventFilter, AuditEventPage, AuditIntegrityReport
from openinfra.domain.common import AuditEvent, EntityId, Pagination, TenantId
from openinfra.domain.data_export import ExportJob
from openinfra.domain.data_import import (
    BulkImportCheckpoint,
    BulkImportReport,
    ImportReport,
    MigrationPlanReport,
)
from openinfra.domain.dcim import (
    Building,
    CoolingZone,
    DcimCable,
    DcimPort,
    DcimPortEndpoint,
    Equipment,
    Floor,
    PatchPanel,
    PowerCircuit,
    PowerDevice,
    Rack,
    RackPowerReservation,
    Room,
    RoomZone,
    Site,
)
from openinfra.domain.discovery import (
    DiscoveryCollector,
    DiscoveryEvidence,
    DiscoveryIntegrationProfile,
    DiscoveryProtocolCredentialProfile,
    DiscoveryReconciliationCase,
)
from openinfra.domain.discovery_jobs import DiscoveryJob
from openinfra.domain.editions import QuotaResource
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityUser,
)
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpPeer,
    DdiChange,
    DdiProvider,
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
from openinfra.domain.itam import (
    ItamOrganization,
    ItamPartner,
    ItamTenant,
    PhysicalAssetSupportProfile,
    SoftwareLicenseEntitlement,
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

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class AccessPolicyRulePage:
    items: tuple[AccessPolicyRule, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class SecurityTokenPage:
    items: tuple[ApiTokenCredential, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_public_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryCollectorPage:
    items: tuple[DiscoveryCollector, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryJobClaimResult:
    job: DiscoveryJob | None
    dead_lettered_jobs: tuple[DiscoveryJob, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscoveryJobPage:
    items: tuple[DiscoveryJob, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryEvidencePage:
    items: tuple[DiscoveryEvidence, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryReconciliationCasePage:
    items: tuple[DiscoveryReconciliationCase, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryIntegrationProfilePage:
    items: tuple[DiscoveryIntegrationProfile, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_public_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryProtocolProfilePage:
    items: tuple[DiscoveryProtocolCredentialProfile, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_public_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class ReadinessStatus:
    component: str
    ready: bool
    detail: str

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "component": self.component,
            "ready": self.ready,
            "detail": self.detail,
        }


class ItamSupportRepository(ABC):
    @abstractmethod
    def save_organization(self, organization: ItamOrganization) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_organization(self, organization_id: str) -> ItamOrganization | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_organizations(self, include_retired: bool = False) -> tuple[ItamOrganization, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_partner(self, partner: ItamPartner) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_partner(self, organization_id: str, partner_id: str) -> ItamPartner | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_partners(
        self, organization_id: str | None = None, include_retired: bool = False
    ) -> tuple[ItamPartner, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_tenant(self, tenant: ItamTenant) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_tenant(self, tenant_id: TenantId) -> ItamTenant | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_tenants(self, include_retired: bool = False) -> tuple[ItamTenant, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def clear_default_tenant(self, except_tenant_id: TenantId | None = None) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_support_profile(self, profile: PhysicalAssetSupportProfile) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_support_profile(
        self, tenant_id: TenantId, asset_tag: str
    ) -> PhysicalAssetSupportProfile | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_software_license(self, license_: SoftwareLicenseEntitlement) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_software_license(
        self, tenant_id: TenantId, license_reference: str
    ) -> SoftwareLicenseEntitlement | None:
        raise TypeError("adapter contract invoked directly")


class ReadinessProbe(ABC):
    @abstractmethod
    def check(self) -> ReadinessStatus:
        raise TypeError("adapter contract invoked directly")


class SchemaStatusProvider(ABC):
    @abstractmethod
    def status_as_dict(self) -> dict[str, object]:
        raise TypeError("adapter contract invoked directly")


class UnitOfWork(ABC):
    @abstractmethod
    def __enter__(self) -> UnitOfWork:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def commit(self) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def rollback(self) -> None:
        raise TypeError("adapter contract invoked directly")


class Repository(Generic[T], ABC):
    @abstractmethod
    def add(self, entity: T) -> None:
        raise TypeError("adapter contract invoked directly")


class DcimRepository(ABC):
    @abstractmethod
    def add_site(self, site: Site) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_building(self, building: Building) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_floor(self, floor: Floor) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_room(self, room: Room) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_zone(self, zone: RoomZone) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_rack(self, rack: Rack) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_patch_panel(self, patch_panel: PatchPanel) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_dcim_port(self, port: DcimPort) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_dcim_cable(self, cable: DcimCable) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_equipment(self, equipment: Equipment) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_power_device(self, power_device: PowerDevice) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_power_circuit(self, circuit: PowerCircuit) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_cooling_zone(self, cooling_zone: CoolingZone) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_power_reservation(self, reservation: RackPowerReservation) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_site(self, site: Site) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_building(self, building: Building) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_floor(self, floor: Floor) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_room(self, room: Room) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_zone(self, zone: RoomZone) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_rack(self, rack: Rack) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_sites(self, tenant_id: TenantId, include_retired: bool = False) -> tuple[Site, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_buildings(
        self, tenant_id: TenantId, site: str, include_retired: bool = False
    ) -> tuple[Building, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_floors(
        self, tenant_id: TenantId, site: str, building: str, include_retired: bool = False
    ) -> tuple[Floor, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_rooms(
        self, tenant_id: TenantId, site: str, building: str, include_retired: bool = False
    ) -> tuple[Room, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_zones(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        include_retired: bool = False,
    ) -> tuple[RoomZone, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_site(self, tenant_id: TenantId, site: str) -> Site | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_building(self, tenant_id: TenantId, site: str, building: str) -> Building | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_floor(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        floor: str,
    ) -> Floor | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> RoomZone | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> Rack | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_patch_panel(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
        patch_panel: str,
    ) -> PatchPanel | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_dcim_port(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimPort | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_dcim_cable(self, tenant_id: TenantId, cable_id: str) -> DcimCable | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_active_dcim_cable_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimCable | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_power_device(self, tenant_id: TenantId, code: str) -> PowerDevice | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_power_circuit(self, tenant_id: TenantId, circuit_id: str) -> PowerCircuit | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_cooling_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> CoolingZone | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_equipment_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[Equipment, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_racks_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        include_retired: bool = False,
    ) -> tuple[Rack, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_patch_panels_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PatchPanel, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_dcim_ports_by_owner(
        self,
        tenant_id: TenantId,
        owner_type: str,
        owner_code: str,
    ) -> tuple[DcimPort, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_dcim_cables_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> tuple[DcimCable, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_equipment_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
    ) -> tuple[Equipment, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_power_circuits_by_source(
        self,
        tenant_id: TenantId,
        source_device: str,
    ) -> tuple[PowerCircuit, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_power_circuits_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PowerCircuit, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_power_reservations_for_circuit(
        self,
        tenant_id: TenantId,
        circuit_id: str,
    ) -> tuple[RackPowerReservation, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_power_reservations_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[RackPowerReservation, ...]:
        raise TypeError("adapter contract invoked directly")


class IpamRepository(ABC):
    @abstractmethod
    def add_vrf(self, vrf: Vrf) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_or_get_vrf(self, vrf: Vrf) -> Vrf:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_vrfs(self, tenant_id: TenantId) -> tuple[Vrf, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_aggregate(self, aggregate: IpAggregate) -> IpAggregate:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_aggregates(self, tenant_id: TenantId, vrf_name: str) -> tuple[IpAggregate, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_or_create_prefix(self, prefix: Prefix) -> Prefix:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_prefixes(self, tenant_id: TenantId, vrf_name: str) -> tuple[Prefix, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_range(self, ip_range: IpRange) -> IpRange:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_ranges(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpRange, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def upsert_address_record(self, record: IpAddressRecord) -> IpAddressRecord:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_address_records(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpAddressRecord, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def acquire_allocation_lock(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_reservation_by_key(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        idempotency_key: str,
    ) -> IpReservation | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_reservations(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpReservation, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_reservation(self, reservation: IpReservation) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_dns_observation(self, record: ObservedDnsRecord) -> ObservedDnsRecord:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_dns_observations(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[ObservedDnsRecord, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_dhcp_lease(self, lease: ObservedDhcpLease) -> ObservedDhcpLease:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_dhcp_leases(
        self, tenant_id: TenantId, vrf_name: str | None = None, active_only: bool = True
    ) -> tuple[ObservedDhcpLease, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_vlan_group(self, group: VlanGroup) -> VlanGroup:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_vlan_groups(self, tenant_id: TenantId) -> tuple[VlanGroup, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_vlan(self, vlan: Vlan) -> Vlan:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_vlans(self, tenant_id: TenantId, vrf_name: str | None = None) -> tuple[Vlan, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_vxlan_vni(self, vni: VxlanVni) -> VxlanVni:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_vxlan_vni(self, tenant_id: TenantId, vni: int) -> VxlanVni | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_vxlan_vnis(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[VxlanVni, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_asn(self, asn: AutonomousSystem) -> AutonomousSystem:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_asn(self, tenant_id: TenantId, number: int) -> AutonomousSystem | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_asns(self, tenant_id: TenantId) -> tuple[AutonomousSystem, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_bgp_peer(self, peer: BgpPeer) -> BgpPeer:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_bgp_peers(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[BgpPeer, ...]:
        raise TypeError("adapter contract invoked directly")


@dataclass(frozen=True, slots=True)
class DdiPreviewContext:
    fqdn: str
    mac_address: str | None
    ttl: int
    dns_zone: str | None = None


class DdiConnector(ABC):
    @property
    @abstractmethod
    def provider(self) -> DdiProvider:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def build_preview_changes(
        self, reservation: IpReservation, context: DdiPreviewContext
    ) -> tuple[DdiChange, ...]:
        raise TypeError("adapter contract invoked directly")


class ImportRepository(ABC):
    @abstractmethod
    def save_import_report(self, report: ImportReport) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_import_report(self, tenant_id: TenantId, job_id: str) -> ImportReport | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_bulk_import_report(self, report: BulkImportReport) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_bulk_import_report(self, tenant_id: TenantId, job_id: str) -> BulkImportReport | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_bulk_import_checkpoint(self, checkpoint: BulkImportCheckpoint) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_bulk_import_checkpoint(
        self, tenant_id: TenantId, job_id: str
    ) -> BulkImportCheckpoint | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_migration_plan_report(self, report: MigrationPlanReport) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_migration_plan_report(
        self, tenant_id: TenantId, job_id: str
    ) -> MigrationPlanReport | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def bulk_import_strategy_name(self) -> str:
        raise TypeError("adapter contract invoked directly")


class DiscoveryRepository(ABC):
    @abstractmethod
    def save_job(self, job: DiscoveryJob) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_job(self, tenant_id: TenantId, job_id: str) -> DiscoveryJob | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_job_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> DiscoveryJob | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def claim_next_job(
        self,
        tenant_id: TenantId,
        collector_id: EntityId,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
    ) -> DiscoveryJobClaimResult:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_jobs(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: str | None = None,
    ) -> DiscoveryJobPage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_evidence(self, evidence: DiscoveryEvidence) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_evidence(self, tenant_id: TenantId, evidence_id: str) -> DiscoveryEvidence | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_evidence(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        object_key: str | None = None,
    ) -> DiscoveryEvidencePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_reconciliation_case(self, case: DiscoveryReconciliationCase) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_reconciliation_case(
        self, tenant_id: TenantId, case_id: str
    ) -> DiscoveryReconciliationCase | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_reconciliation_case_by_signature(
        self, tenant_id: TenantId, signature: str
    ) -> DiscoveryReconciliationCase | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_reconciliation_cases(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: str | None = None,
    ) -> DiscoveryReconciliationCasePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_integration_profile(self, profile: DiscoveryIntegrationProfile) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_integration_profile(
        self, tenant_id: TenantId, profile_id: str
    ) -> DiscoveryIntegrationProfile | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_integration_profiles(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryIntegrationProfilePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_protocol_profile(self, profile: DiscoveryProtocolCredentialProfile) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_protocol_profile(
        self, tenant_id: TenantId, profile_id: str
    ) -> DiscoveryProtocolCredentialProfile | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_protocol_profiles(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryProtocolProfilePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_collector(self, collector: DiscoveryCollector) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_collector(self, tenant_id: TenantId, collector_id: str) -> DiscoveryCollector | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_collectors(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryCollectorPage:
        raise TypeError("adapter contract invoked directly")


class ExportRepository(ABC):
    @abstractmethod
    def save_export_job(self, job: ExportJob) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_export_job(self, tenant_id: TenantId, job_id: str) -> ExportJob | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_next_queued_export_job(self, tenant_id: TenantId) -> ExportJob | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def save_export_artifact(self, job: ExportJob, content: bytes) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_export_artifact(self, tenant_id: TenantId, job_id: str) -> bytes | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_or_create_export_signing_secret(self) -> bytes:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def export_storage_strategy_name(self) -> str:
        raise TypeError("adapter contract invoked directly")


class RuntimeUsageRepository(ABC):
    @abstractmethod
    def count_resource(self, tenant_id: TenantId, resource: QuotaResource) -> int:
        raise TypeError("adapter contract invoked directly")


class IdentityRepository(ABC):
    @abstractmethod
    def upsert_user(self, user: IdentityUser) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def upsert_group(self, group: IdentityGroup) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_membership(self, membership: GroupMembership) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def grant_user_role(self, tenant_id: TenantId, username: str, role: str) -> bool:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def grant_group_role(self, tenant_id: TenantId, group_name: str, role: str) -> bool:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def effective_identity_for_subject(
        self,
        tenant_id: TenantId,
        subject: str,
    ) -> EffectiveIdentity:
        raise TypeError("adapter contract invoked directly")


class SecurityRepository(ABC):
    @abstractmethod
    def upsert_token(self, credential: ApiTokenCredential) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_active_token_by_hash(
        self,
        tenant_id: TenantId,
        token_hash: str,
    ) -> ApiTokenCredential | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def revoke_token(self, tenant_id: TenantId, token_hash: str, actor: str) -> bool:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_tokens(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> SecurityTokenPage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def record_token_used(self, tenant_id: TenantId, token_hash: str) -> None:
        raise TypeError("adapter contract invoked directly")


class AccessPolicyRepository(ABC):
    @abstractmethod
    def upsert_rule(self, rule: AccessPolicyRule) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> AccessPolicyRulePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_active_rules_for_permission(
        self,
        tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[AccessPolicyRule, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        raise TypeError("adapter contract invoked directly")


class SourceOfTruthRepository(ABC):
    @abstractmethod
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
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def upsert_object(self, source_object: SourceOfTruthObject, actor: str) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_object(self, tenant_id: TenantId, key: str) -> SourceOfTruthObject | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_objects(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        tag: str | None = None,
        resource_type: str | None = None,
    ) -> SourceObjectPage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_object_version(
        self,
        tenant_id: TenantId,
        key: str,
        version: int,
    ) -> SourceObjectSnapshot | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_object_as_of(
        self,
        tenant_id: TenantId,
        key: str,
        as_of: datetime,
    ) -> SourceObjectSnapshot | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_relation(self, relation: SourceRelation) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_relations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_key: str | None = None,
        target_key: str | None = None,
        relation_type: str | None = None,
        as_of: datetime | None = None,
    ) -> SourceRelationPage:
        raise TypeError("adapter contract invoked directly")


class SourceGovernanceRepository(ABC):
    @abstractmethod
    def upsert_rule(self, rule: SourceGovernanceRule) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_rule(self, tenant_id: TenantId, name: str) -> SourceGovernanceRule | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool = False,
        object_kind: str | None = None,
    ) -> SourceGovernanceRulePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_active_rules_for_kind(
        self,
        tenant_id: TenantId,
        object_kind: str,
    ) -> tuple[SourceGovernanceRule, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        raise TypeError("adapter contract invoked directly")


class AuditRepository(ABC):
    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        raise TypeError("adapter contract invoked directly")


class TransactionManager(ABC):
    @abstractmethod
    def begin(self) -> UnitOfWork:
        raise TypeError("adapter contract invoked directly")
