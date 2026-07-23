from __future__ import annotations

import html
import ipaddress
import re
from dataclasses import dataclass

from openinfra.application.edition_services import EditionRuntimeGuard
from openinfra.application.ports import (
    AuditRepository,
    DdiConnector,
    DdiPreviewContext,
    IpamRepository,
    TransactionManager,
)
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    TenantId,
    ValidationError,
)
from openinfra.domain.editions import QuotaResource
from openinfra.domain.ipam import (
    AllocationRequest,
    AllocationResult,
    AutonomousSystem,
    BgpPeer,
    DdiDivergence,
    DdiProvider,
    DdiReservationPreview,
    IpAddressRecord,
    IpAggregate,
    IpAllocationPolicy,
    IpamConflict,
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
        edition_guard: EditionRuntimeGuard | None = None,
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._allocation_policy = allocation_policy or IpAllocationPolicy()
        self._edition_guard = edition_guard

    def allocate(self, command: AllocateIpCommand) -> AllocationResult:
        request = AllocationRequest.create(
            tenant_id=command.tenant_id,
            vrf_name=command.vrf,
            prefix_cidr=command.prefix,
            hostname=command.hostname,
            idempotency_key=command.idempotency_key,
        )
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_quota(
                request.tenant_id,
                QuotaResource.IP_DNS_RECORD,
                1,
                command.actor,
                "ip_reservation",
                request.idempotency_key,
            )
        with self._transaction_manager.begin() as unit_of_work:
            self._ipam_repository.acquire_allocation_lock(
                request.tenant_id,
                request.vrf_name.value,
                request.prefix_cidr,
            )
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
            address_records = self._ipam_repository.list_address_records(
                tenant_id=request.tenant_id,
                vrf_name=request.vrf_name.value,
                prefix_cidr=str(prefix.network),
            )
            ranges = self._ipam_repository.list_ranges(
                tenant_id=request.tenant_id,
                vrf_name=request.vrf_name.value,
                prefix_cidr=str(prefix.network),
            )
            next_address = self._allocation_policy.next_available_address(
                prefix,
                {reservation.address for reservation in reservations}
                | {record.address for record in address_records},
                ranges,
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
                        "idempotency_key": reservation.idempotency_key,
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
class DefineVlanGroupCommand:
    tenant_id: str
    actor: str
    name: str
    scope: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class DefineVxlanVniCommand:
    tenant_id: str
    actor: str
    vni: int
    name: str
    vrf: str
    route_targets_import: tuple[str, ...] = ()
    route_targets_export: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True, slots=True)
class DefineVlanCommand:
    tenant_id: str
    actor: str
    group: str
    vlan_id: int
    name: str
    vrf: str | None = None
    vni: int | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class DefineAsnCommand:
    tenant_id: str
    actor: str
    asn: int
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class DefineBgpPeerCommand:
    tenant_id: str
    actor: str
    vrf: str
    local_asn: int
    remote_asn: int
    peer_address: str
    address_family: str | None = None
    route_targets_import: tuple[str, ...] = ()
    route_targets_export: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True, slots=True)
class IpamNetworkBindingsCommand:
    tenant_id: str
    vrf: str | None = None


@dataclass(frozen=True, slots=True)
class IpamNetworkBindingsReport:
    tenant_id: str
    vrf: str | None
    vlan_groups: tuple[dict[str, object], ...]
    vlans: tuple[dict[str, object], ...]
    vxlan_vnis: tuple[dict[str, object], ...]
    asns: tuple[dict[str, object], ...]
    bgp_peers: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "vrf": self.vrf,
            "counts": {
                "vlan_groups": len(self.vlan_groups),
                "vlans": len(self.vlans),
                "vxlan_vnis": len(self.vxlan_vnis),
                "asns": len(self.asns),
                "bgp_peers": len(self.bgp_peers),
            },
            "vlan_groups": list(self.vlan_groups),
            "vlans": list(self.vlans),
            "vxlan_vnis": list(self.vxlan_vnis),
            "asns": list(self.asns),
            "bgp_peers": list(self.bgp_peers),
        }


@dataclass(frozen=True, slots=True)
class IpamTopologyCommand:
    tenant_id: str
    actor: str
    vrf: str | None = None


@dataclass(frozen=True, slots=True)
class IpamTopologyReport:
    tenant_id: str
    vrf: str | None
    summary: dict[str, int]
    nodes: tuple[dict[str, object], ...]
    edges: tuple[dict[str, str], ...]
    integrity: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "vrf": self.vrf,
            "summary": self.summary,
            "nodes": list(self.nodes),
            "edges": list(self.edges),
            "integrity": self.integrity,
        }


@dataclass(frozen=True, slots=True)
class ObserveDnsRecordCommand:
    tenant_id: str
    actor: str
    vrf: str
    hostname: str
    address: str
    ptr_hostname: str | None = None
    source: str = "manual"


@dataclass(frozen=True, slots=True)
class ObserveDhcpLeaseCommand:
    tenant_id: str
    actor: str
    vrf: str
    prefix: str
    address: str
    mac_address: str
    hostname: str
    source: str = "manual"
    active: bool = True


@dataclass(frozen=True, slots=True)
class DetectIpamConflictsCommand:
    tenant_id: str
    actor: str
    vrf: str | None = None


@dataclass(frozen=True, slots=True)
class IpamConflictReport:
    tenant_id: str
    vrf: str | None
    total: int
    by_severity: dict[str, int]
    conflicts: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "vrf": self.vrf,
            "total": self.total,
            "by_severity": self.by_severity,
            "conflicts": list(self.conflicts),
        }


@dataclass(frozen=True, slots=True)
class IpamUiDashboardCommand:
    tenant_id: str
    actor: str
    vrf: str | None = None


@dataclass(frozen=True, slots=True)
class IpamSearchCommand:
    tenant_id: str
    actor: str
    query: str
    vrf: str | None = None


@dataclass(frozen=True, slots=True)
class IpamReservationWizardCommand:
    tenant_id: str
    actor: str
    vrf: str
    prefix: str
    hostname: str
    idempotency_key: str
    dry_run: bool = True


@dataclass(frozen=True, slots=True)
class PreviewDdiReservationCommand:
    tenant_id: str
    actor: str
    vrf: str
    idempotency_key: str
    providers: tuple[str, ...] = ("all",)
    dns_zone: str | None = None
    mac_address: str | None = None
    ttl: int = 300
    dry_run: bool = True
    reverse_dns_zone: str | None = None


class IpamDdiService:
    def __init__(
        self,
        ipam_repository: IpamRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        connectors: tuple[DdiConnector, ...],
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._connectors = {connector.provider: connector for connector in connectors}

    def preview_reservation(self, command: PreviewDdiReservationCommand) -> DdiReservationPreview:
        tenant_id = TenantId.from_value(command.tenant_id)
        vrf = command.vrf.strip()
        providers = self._select_providers(command.providers)
        with self._transaction_manager.begin() as unit_of_work:
            reservation = self._ipam_repository.find_reservation_by_key(
                tenant_id,
                vrf,
                command.idempotency_key,
            )
            if reservation is None:
                raise NotFoundError("ip reservation not found for DDI preview")
            fqdn = self._fqdn_for_reservation(reservation.hostname, command.dns_zone)
            mac_address = (
                self._normalize_mac(command.mac_address) if command.mac_address else None
            )
            context = DdiPreviewContext(
                fqdn=fqdn,
                mac_address=mac_address,
                ttl=self._normalize_ttl(command.ttl),
                dns_zone=self._normalize_zone(command.dns_zone) if command.dns_zone else None,
                reverse_dns_zone=(
                    self._normalize_zone(command.reverse_dns_zone)
                    if command.reverse_dns_zone
                    else None
                ),
            )
            changes = tuple(
                change
                for provider in providers
                for change in self._connectors[provider].build_preview_changes(reservation, context)
            )
            divergences = self._detect_divergences(
                reservation, fqdn, mac_address, providers
            )
            preview = DdiReservationPreview.create(
                tenant_id=tenant_id,
                vrf_name=vrf,
                idempotency_key=reservation.idempotency_key,
                providers=providers,
                dry_run=command.dry_run,
                changes=changes,
                divergences=divergences,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.ddi.preview.generated",
                    target_type="ipam_ddi_preview",
                    target_id=preview.id.value,
                    metadata={
                        "vrf": preview.vrf_name.value,
                        "idempotency_key": preview.idempotency_key,
                        "providers": [provider.value for provider in providers],
                        "changes": len(preview.changes),
                        "divergences": len(preview.divergences),
                        "safe_to_apply": preview.safe_to_apply,
                    },
                )
            )
            unit_of_work.commit()
        return preview

    def _select_providers(self, providers: tuple[str, ...]) -> tuple[DdiProvider, ...]:
        requested = tuple(item.strip().lower() for item in providers if item.strip()) or ("all",)
        if "all" in requested:
            selected = tuple(sorted(self._connectors, key=lambda item: item.value))
        else:
            selected = tuple(dict.fromkeys(DdiProvider.from_value(item) for item in requested))
        missing = [provider.value for provider in selected if provider not in self._connectors]
        if missing:
            raise ValidationError(f"DDI connectors unavailable: {', '.join(missing)}")
        return selected

    def _fqdn_for_reservation(self, hostname: str, dns_zone: str | None) -> str:
        normalized = hostname.strip().lower().rstrip(".")
        if not normalized:
            raise ValidationError("reservation hostname is mandatory for DDI preview")
        if "." in normalized:
            return self._validate_fqdn(normalized)
        if not dns_zone:
            raise ValidationError(
                "dns zone is required when reservation hostname is not fully qualified"
            )
        return self._validate_fqdn(f"{normalized}.{self._normalize_zone(dns_zone)}")

    def _normalize_zone(self, dns_zone: str | None) -> str:
        normalized = (dns_zone or "").strip().lower().rstrip(".")
        if not normalized:
            raise ValidationError("dns zone is mandatory for non-FQDN reservation hostnames")
        return self._validate_fqdn(normalized)

    def _validate_fqdn(self, value: str) -> str:
        if not 1 <= len(value) <= 253:
            raise ValidationError("DDI FQDN must contain 1 to 253 characters")
        labels = value.split(".")
        pattern = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
        if len(labels) < 2 or any(not pattern.fullmatch(label) for label in labels):
            raise ValidationError("DDI FQDN is invalid")
        return value

    def _normalize_mac(self, value: str) -> str:
        normalized = value.strip().lower().replace("-", ":")
        if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", normalized):
            raise ValidationError("DDI DHCP MAC address is invalid")
        return normalized

    def _normalize_ttl(self, value: int) -> int:
        if not 0 <= value <= 86400:
            raise ValidationError("DDI TTL must be between 0 and 86400 seconds")
        return value

    def _detect_divergences(
        self,
        reservation: IpReservation,
        fqdn: str,
        mac_address: str | None,
        providers: tuple[DdiProvider, ...],
    ) -> tuple[DdiDivergence, ...]:
        divergences: list[DdiDivergence] = []
        address = str(reservation.address)
        for record in self._ipam_repository.list_dns_observations(
            reservation.tenant_id, reservation.vrf_name.value
        ):
            observed_address = str(record.address)
            if record.hostname == fqdn and observed_address != address:
                divergences.append(
                    DdiDivergence.create(
                        "critical",
                        "dns_forward_mismatch",
                        fqdn,
                        (f"observed {fqdn} -> {observed_address}, planned {address}",),
                        "Resolve the existing forward DNS binding before applying DDI changes.",
                    )
                )
            if observed_address == address and record.hostname != fqdn:
                divergences.append(
                    DdiDivergence.create(
                        "error",
                        "dns_address_owner_mismatch",
                        address,
                        (f"observed {address} owned by {record.hostname}, planned {fqdn}",),
                        "Confirm ownership or rename the reservation hostname before applying.",
                    )
                )
            if observed_address == address and record.ptr_hostname and record.ptr_hostname != fqdn:
                divergences.append(
                    DdiDivergence.create(
                        "error",
                        "dns_ptr_mismatch",
                        address,
                        (f"observed PTR {record.ptr_hostname}, planned {fqdn}",),
                        "Align reverse DNS with the intended reservation hostname.",
                    )
                )
        if DdiProvider.KEA in providers and mac_address is None:
            divergences.append(
                DdiDivergence.create(
                    "error",
                    "dhcp_mac_missing",
                    f"kea:{address}",
                    ("Kea DHCP reservation preview requires a MAC address.",),
                    "Provide --mac-address or exclude the Kea provider from this preview.",
                )
            )
        for lease in self._ipam_repository.list_dhcp_leases(
            reservation.tenant_id, reservation.vrf_name.value
        ):
            observed_address = str(lease.address)
            if observed_address == address and mac_address and lease.mac_address != mac_address:
                divergences.append(
                    DdiDivergence.create(
                        "critical",
                        "dhcp_address_conflict",
                        address,
                        (
                            f"observed {address} leased to {lease.mac_address}",
                            f"planned reservation for {mac_address}",
                        ),
                        "Release or reconcile the active DHCP lease before applying.",
                    )
                )
            if mac_address and lease.mac_address == mac_address and observed_address != address:
                divergences.append(
                    DdiDivergence.create(
                        "error",
                        "dhcp_mac_conflict",
                        mac_address,
                        (
                            f"observed {mac_address} leased to {observed_address}",
                            f"planned reservation for {address}",
                        ),
                        "Update the DHCP reservation target or clean the stale lease.",
                    )
                )
        return tuple(divergences)


@dataclass(frozen=True, slots=True)
class IpamUiViewModel:
    tenant_id: str
    vrf: str | None
    summary: dict[str, int]
    vrfs: tuple[dict[str, object], ...]
    prefixes: tuple[dict[str, object], ...]
    reservations: tuple[dict[str, object], ...]
    conflicts: tuple[dict[str, object], ...]
    network_bindings: dict[str, object]
    actions: tuple[dict[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "vrf": self.vrf,
            "summary": self.summary,
            "vrfs": list(self.vrfs),
            "prefixes": list(self.prefixes),
            "reservations": list(self.reservations),
            "conflicts": list(self.conflicts),
            "network_bindings": self.network_bindings,
            "actions": list(self.actions),
        }


class IpamUiHtmlRenderer:
    def render(self, view: IpamUiViewModel) -> str:
        cards = self._cards(view.summary)
        vrfs = self._rows(view.vrfs, ("name", "route_distinguisher", "prefix_count"))
        prefixes = self._rows(
            view.prefixes,
            ("vrf", "prefix", "family", "usable_addresses", "free_addresses", "utilization_pct"),
        )
        conflicts = self._rows(
            view.conflicts,
            ("severity", "type", "vrf", "impacted_object", "recommended_action"),
        )
        return "".join(
            (
                '<!doctype html><html lang="fr"><head><meta charset="utf-8">',
                "<title>OpenInfra IPAM</title>",
                "<style>",
                "body{font-family:system-ui,Arial,sans-serif;margin:2rem;background:#f8fafc;color:#0f172a}",
                ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:1rem}",
                ".card,section{background:white;border:1px solid #e2e8f0;",
                "border-radius:12px;padding:1rem}",
                "table{width:100%;border-collapse:collapse}",
                "th,td{border-bottom:1px solid #e2e8f0;padding:.5rem;text-align:left}",
                "th{background:#f1f5f9}",
                "code{background:#e2e8f0;border-radius:4px;padding:.1rem .25rem}",
                "</style></head><body>",
                f"<h1>OpenInfra IPAM — {html.escape(view.tenant_id)}</h1>",
                f"<p>VRF: <code>{html.escape(view.vrf or '*')}</code></p>",
                f'<div class="grid">{cards}</div>',
                "<section><h2>VRF</h2>",
                vrfs,
                "</section><section><h2>Préfixes et capacité</h2>",
                prefixes,
                "</section><section><h2>Conflits actifs</h2>",
                conflicts,
                "</section></body></html>",
            )
        )

    def _cards(self, summary: dict[str, int]) -> str:
        return "".join(
            f'<div class="card"><strong>{html.escape(key)}</strong><br>{value}</div>'
            for key, value in sorted(summary.items())
        )

    def _rows(self, items: tuple[object, ...], columns: tuple[str, ...]) -> str:
        head = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
        rows: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            cells = "".join(
                f"<td>{html.escape(str(item.get(column, '')))}</td>" for column in columns
            )
            rows.append(f"<tr>{cells}</tr>")
        if not rows:
            rows.append(f'<tr><td colspan="{len(columns)}">Aucune donnée</td></tr>')
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


class IpamUiService:
    def __init__(
        self,
        ipam_repository: IpamRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        allocation_service: IpamAllocationService,
        conflict_service: IpamConflictService,
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._allocation_service = allocation_service
        self._conflict_service = conflict_service
        self._renderer = IpamUiHtmlRenderer()

    def dashboard(self, command: IpamUiDashboardCommand) -> IpamUiViewModel:
        tenant_id = TenantId.from_value(command.tenant_id)
        requested_vrf = command.vrf.strip() if command.vrf else None
        vrfs = self._selected_vrfs(tenant_id, requested_vrf)
        prefix_rows = self._prefix_rows(tenant_id, vrfs)
        reservation_rows = self._reservation_rows(tenant_id, vrfs)
        conflicts = self._conflict_service.detect(
            DetectIpamConflictsCommand(tenant_id.value, command.actor, requested_vrf)
        )
        bindings = IpamModelService(
            self._ipam_repository, self._audit_repository, self._transaction_manager
        ).network_bindings(IpamNetworkBindingsCommand(tenant_id.value, requested_vrf))
        view = IpamUiViewModel(
            tenant_id=tenant_id.value,
            vrf=requested_vrf,
            summary=self._summary(vrfs, prefix_rows, reservation_rows, conflicts.conflicts),
            vrfs=tuple(self._vrf_row(vrf, prefix_rows) for vrf in vrfs),
            prefixes=tuple(prefix_rows),
            reservations=tuple(reservation_rows),
            conflicts=conflicts.conflicts,
            network_bindings=bindings.as_dict(),
            actions=self._actions(requested_vrf),
        )
        self._audit_repository.append(
            AuditEvent.record(
                tenant_id=tenant_id,
                actor=command.actor,
                action="ipam.ui.dashboard.rendered",
                target_type="ipam_ui_dashboard",
                target_id=requested_vrf or "*",
                metadata={"prefixes": len(prefix_rows), "conflicts": len(conflicts.conflicts)},
            )
        )
        return view

    def render_dashboard_html(self, command: IpamUiDashboardCommand) -> str:
        return self._renderer.render(self.dashboard(command))

    def search(self, command: IpamSearchCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        query = command.query.strip().lower()
        if len(query) < 2:
            raise ValidationError("ipam search query must contain at least 2 characters")
        vrfs = self._selected_vrfs(tenant_id, command.vrf.strip() if command.vrf else None)
        matches: list[dict[str, object]] = []
        for row in self._prefix_rows(tenant_id, vrfs):
            if self._matches(row, query):
                matches.append({"kind": "prefix", **row})
        for row in self._reservation_rows(tenant_id, vrfs):
            if self._matches(row, query):
                matches.append({"kind": "reservation", **row})
        for vrf in vrfs:
            for record in self._ipam_repository.list_dns_observations(tenant_id, vrf.name.value):
                dns_row: dict[str, object] = dict(record.as_dict())
                if self._matches(dns_row, query):
                    matches.append({"kind": "dns", **dns_row})
            for lease in self._ipam_repository.list_dhcp_leases(tenant_id, vrf.name.value):
                dhcp_row: dict[str, object] = dict(lease.as_dict())
                if self._matches(dhcp_row, query):
                    matches.append({"kind": "dhcp_lease", **dhcp_row})
        result = {
            "tenant_id": tenant_id.value,
            "query": command.query,
            "count": len(matches),
            "items": matches,
        }
        self._audit_repository.append(
            AuditEvent.record(
                tenant_id=tenant_id,
                actor=command.actor,
                action="ipam.ui.search.executed",
                target_type="ipam_ui_search",
                target_id=query,
                metadata={"matches": len(matches)},
            )
        )
        return result

    def reservation_wizard(self, command: IpamReservationWizardCommand) -> dict[str, object]:
        if command.dry_run:
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
            next_ip = IpAllocationPolicy().next_available_address(
                prefix,
                {reservation.address for reservation in reservations}
                | {record.address for record in records},
                ranges,
            )
            return {
                "tenant_id": tenant_id.value,
                "vrf": prefix.vrf_name.value,
                "prefix": str(prefix.network),
                "hostname": command.hostname,
                "idempotency_key": command.idempotency_key,
                "dry_run": True,
                "recommended_address": str(next_ip),
                "operation": "preview",
            }
        result = self._allocation_service.allocate(
            AllocateIpCommand(
                tenant_id=command.tenant_id,
                actor=command.actor,
                vrf=command.vrf,
                prefix=command.prefix,
                hostname=command.hostname,
                idempotency_key=command.idempotency_key,
            )
        )
        payload: dict[str, object] = dict(result.as_dict())
        payload["dry_run"] = False
        payload["operation"] = "allocated" if result.created else "idempotent_replay"
        return payload

    def _selected_vrfs(self, tenant_id: TenantId, requested_vrf: str | None) -> tuple[Vrf, ...]:
        if requested_vrf:
            return (self._ipam_repository.add_or_get_vrf(Vrf.create(tenant_id, requested_vrf)),)
        return self._ipam_repository.list_vrfs(tenant_id)

    def _prefix_rows(self, tenant_id: TenantId, vrfs: tuple[Vrf, ...]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for vrf in vrfs:
            for prefix in self._ipam_repository.list_prefixes(tenant_id, vrf.name.value):
                reservations = self._ipam_repository.list_reservations(
                    tenant_id, vrf.name.value, str(prefix.network)
                )
                records = self._ipam_repository.list_address_records(
                    tenant_id, vrf.name.value, str(prefix.network)
                )
                ranges = self._ipam_repository.list_ranges(
                    tenant_id, vrf.name.value, str(prefix.network)
                )
                occupied = {int(item.address) for item in reservations}
                occupied.update(int(item.address) for item in records)
                usable = prefix.last_usable_int - prefix.first_usable_int + 1
                free = max(usable - len(occupied), 0)
                utilization = round((len(occupied) / usable) * 100, 2) if usable else 100.0
                rows.append(
                    {
                        "vrf": vrf.name.value,
                        "prefix": str(prefix.network),
                        "family": prefix.network.version,
                        "usable_addresses": usable,
                        "reserved_addresses": len(occupied),
                        "free_addresses": free,
                        "utilization_pct": utilization,
                        "range_count": len(ranges),
                    }
                )
        return rows

    def _reservation_rows(
        self, tenant_id: TenantId, vrfs: tuple[Vrf, ...]
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for vrf in vrfs:
            for prefix in self._ipam_repository.list_prefixes(tenant_id, vrf.name.value):
                for reservation in self._ipam_repository.list_reservations(
                    tenant_id, vrf.name.value, str(prefix.network)
                ):
                    rows.append(
                        {
                            "vrf": vrf.name.value,
                            "prefix": reservation.prefix,
                            "address": str(reservation.address),
                            "hostname": reservation.hostname,
                            "idempotency_key": reservation.idempotency_key,
                        }
                    )
        return rows

    def _vrf_row(self, vrf: Vrf, prefixes: list[dict[str, object]]) -> dict[str, object]:
        prefix_count = sum(1 for prefix in prefixes if prefix["vrf"] == vrf.name.value)
        free = sum(
            int(str(prefix["free_addresses"]))
            for prefix in prefixes
            if prefix["vrf"] == vrf.name.value
        )
        return {
            "name": vrf.name.value,
            "route_distinguisher": vrf.route_distinguisher,
            "prefix_count": prefix_count,
            "free_addresses": free,
        }

    def _summary(
        self,
        vrfs: tuple[Vrf, ...],
        prefixes: list[dict[str, object]],
        reservations: list[dict[str, object]],
        conflicts: tuple[dict[str, object], ...],
    ) -> dict[str, int]:
        return {
            "vrfs": len(vrfs),
            "prefixes": len(prefixes),
            "free_addresses": sum(int(str(prefix["free_addresses"])) for prefix in prefixes),
            "reservations": len(reservations),
            "conflicts": len(conflicts),
        }

    def _actions(self, vrf: str | None) -> tuple[dict[str, str], ...]:
        suffix = f" --vrf {vrf}" if vrf else ""
        return (
            {
                "label": "Rechercher une IP",
                "command": f"openinfra ipam ui-search --query <ip|host>{suffix}",
            },
            {
                "label": "Réserver une IP",
                "command": (
                    f"openinfra ipam reservation-wizard --prefix <cidr> --hostname <host>{suffix}"
                ),
            },
            {
                "label": "Analyser les conflits",
                "command": f"openinfra ipam detect-conflicts{suffix}",
            },
        )

    def _matches(self, row: dict[str, object], query: str) -> bool:
        return any(query in str(value).lower() for value in row.values())


class IpamConflictService:
    def __init__(
        self,
        ipam_repository: IpamRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def observe_dns(self, command: ObserveDnsRecordCommand) -> dict[str, str | None]:
        tenant_id = TenantId.from_value(command.tenant_id)
        record = ObservedDnsRecord.create(
            tenant_id,
            command.vrf,
            command.hostname,
            command.address,
            command.ptr_hostname,
            command.source,
        )
        with self._transaction_manager.begin() as unit_of_work:
            stored = self._ipam_repository.add_dns_observation(record)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.dns_observation.recorded",
                    target_type="ipam_dns_observation",
                    target_id=f"{stored.hostname}:{stored.address}",
                    metadata={"vrf": stored.vrf_name.value, "source": stored.source},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def observe_dhcp_lease(self, command: ObserveDhcpLeaseCommand) -> dict[str, str | bool]:
        tenant_id = TenantId.from_value(command.tenant_id)
        lease = ObservedDhcpLease.create(
            tenant_id,
            command.vrf,
            command.prefix,
            command.address,
            command.mac_address,
            command.hostname,
            command.source,
            command.active,
        )
        with self._transaction_manager.begin() as unit_of_work:
            stored = self._ipam_repository.add_dhcp_lease(lease)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.dhcp_lease.observed",
                    target_type="ipam_dhcp_lease",
                    target_id=f"{stored.vrf_name.value}:{stored.address}",
                    metadata={"mac_address": stored.mac_address, "source": stored.source},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def detect(self, command: DetectIpamConflictsCommand) -> IpamConflictReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        selected_vrf = command.vrf.strip() if command.vrf else None
        vrfs = self._target_vrfs(tenant_id, selected_vrf)
        conflicts: list[IpamConflict] = []
        for vrf in vrfs:
            prefixes = self._ipam_repository.list_prefixes(tenant_id, vrf)
            conflicts.extend(self._detect_prefix_overlaps(tenant_id, vrf, prefixes))
            conflicts.extend(self._detect_range_overlaps(tenant_id, vrf, prefixes))
            conflicts.extend(self._detect_duplicate_addresses(tenant_id, vrf, prefixes))
            conflicts.extend(self._detect_dns_ptr_divergences(tenant_id, vrf, prefixes))
            conflicts.extend(self._detect_dhcp_lease_conflicts(tenant_id, vrf, prefixes))
        ordered = tuple(sorted(conflicts, key=lambda item: item.fingerprint))
        by_severity: dict[str, int] = {}
        for conflict in ordered:
            by_severity[conflict.severity.value] = by_severity.get(conflict.severity.value, 0) + 1
        self._audit_repository.append(
            AuditEvent.record(
                tenant_id=tenant_id,
                actor=command.actor,
                action="ipam.conflicts.detected",
                target_type="ipam_conflict_scan",
                target_id=selected_vrf or "*",
                metadata={"total": len(ordered), "vrf": selected_vrf},
            )
        )
        return IpamConflictReport(
            tenant_id=tenant_id.value,
            vrf=selected_vrf,
            total=len(ordered),
            by_severity=by_severity,
            conflicts=tuple(conflict.as_dict() for conflict in ordered),
        )

    def _target_vrfs(self, tenant_id: TenantId, requested_vrf: str | None) -> tuple[str, ...]:
        if requested_vrf:
            return (requested_vrf,)
        names = {vrf.name.value for vrf in self._ipam_repository.list_vrfs(tenant_id)}
        names.update(
            record.vrf_name.value
            for record in self._ipam_repository.list_dns_observations(tenant_id)
        )
        names.update(
            lease.vrf_name.value for lease in self._ipam_repository.list_dhcp_leases(tenant_id)
        )
        return tuple(sorted(names))

    def _detect_prefix_overlaps(
        self, tenant_id: TenantId, vrf: str, prefixes: tuple[Prefix, ...]
    ) -> list[IpamConflict]:
        conflicts: list[IpamConflict] = []
        for index, first in enumerate(prefixes):
            for second in prefixes[index + 1 :]:
                if first.network.version == second.network.version and first.network.overlaps(
                    second.network
                ):
                    conflicts.append(
                        IpamConflict.create(
                            "prefix_overlap",
                            "critical",
                            tenant_id,
                            vrf,
                            f"prefix:{first.network}",
                            (f"{first.network} overlaps {second.network}",),
                            "Split, resize or move one prefix to another VRF before allocation.",
                        )
                    )
        return conflicts

    def _detect_range_overlaps(
        self, tenant_id: TenantId, vrf: str, prefixes: tuple[Prefix, ...]
    ) -> list[IpamConflict]:
        conflicts: list[IpamConflict] = []
        for prefix in prefixes:
            ranges = self._ipam_repository.list_ranges(tenant_id, vrf, str(prefix.network))
            for index, first in enumerate(ranges):
                for second in ranges[index + 1 :]:
                    if first.overlaps(second) and not self._is_pool_overlay(first, second):
                        conflicts.append(
                            IpamConflict.create(
                                "range_overlap",
                                "error",
                                tenant_id,
                                vrf,
                                f"range:{first.start}-{first.end}",
                                (
                                    f"{first.purpose.value} range {first.start}-{first.end} "
                                    f"overlaps {second.purpose.value} range "
                                    f"{second.start}-{second.end}",
                                ),
                                (
                                    "Adjust range boundaries or mark the smaller pool as "
                                    "exclusion/reservation."
                                ),
                            )
                        )
        return conflicts

    def _detect_duplicate_addresses(
        self, tenant_id: TenantId, vrf: str, prefixes: tuple[Prefix, ...]
    ) -> list[IpamConflict]:
        claims: dict[str, list[str]] = {}
        for prefix in prefixes:
            prefix_cidr = str(prefix.network)
            for record in self._ipam_repository.list_address_records(tenant_id, vrf, prefix_cidr):
                claims.setdefault(str(record.address), []).append(
                    f"address-record:{record.hostname}:{record.status.value}"
                )
            for reservation in self._ipam_repository.list_reservations(tenant_id, vrf, prefix_cidr):
                claims.setdefault(str(reservation.address), []).append(
                    f"reservation:{reservation.hostname}:{reservation.idempotency_key}"
                )
        for lease in self._ipam_repository.list_dhcp_leases(tenant_id, vrf):
            if lease.active:
                claims.setdefault(str(lease.address), []).append(
                    f"dhcp-lease:{lease.hostname}:{lease.mac_address}"
                )
        conflicts: list[IpamConflict] = []
        for address, owners in claims.items():
            unique = tuple(dict.fromkeys(owners))
            if len(unique) > 1:
                conflicts.append(
                    IpamConflict.create(
                        "duplicate_address",
                        "critical",
                        tenant_id,
                        vrf,
                        f"ip:{address}",
                        unique,
                        (
                            "Keep a single authoritative owner or move conflicting claims "
                            "to distinct VRFs."
                        ),
                    )
                )
        return conflicts

    def _detect_dns_ptr_divergences(
        self, tenant_id: TenantId, vrf: str, prefixes: tuple[Prefix, ...]
    ) -> list[IpamConflict]:
        conflicts: list[IpamConflict] = []
        for record in self._ipam_repository.list_dns_observations(tenant_id, vrf):
            if record.ptr_hostname and record.ptr_hostname != record.hostname:
                conflicts.append(
                    IpamConflict.create(
                        "dns_ptr_divergence",
                        "warning",
                        tenant_id,
                        vrf,
                        f"dns:{record.hostname}",
                        (
                            f"A/AAAA {record.hostname} -> {record.address}",
                            f"PTR {record.address} -> {record.ptr_hostname}",
                        ),
                        "Align forward and reverse DNS ownership before publishing DDI changes.",
                    )
                )
            if prefixes and not any(record.address in prefix.network for prefix in prefixes):
                conflicts.append(
                    IpamConflict.create(
                        "address_out_of_prefix",
                        "error",
                        tenant_id,
                        vrf,
                        f"dns:{record.address}",
                        (
                            f"observed DNS address {record.address} is outside "
                            "all known VRF prefixes",
                        ),
                        "Create the containing prefix or move the DNS record to the correct VRF.",
                    )
                )
        return conflicts

    def _detect_dhcp_lease_conflicts(
        self, tenant_id: TenantId, vrf: str, prefixes: tuple[Prefix, ...]
    ) -> list[IpamConflict]:
        conflicts: list[IpamConflict] = []
        known_prefixes = {str(prefix.network) for prefix in prefixes}
        for lease in self._ipam_repository.list_dhcp_leases(tenant_id, vrf):
            if not lease.active:
                continue
            if lease.prefix not in known_prefixes or not lease.address_belongs_to_prefix():
                conflicts.append(
                    IpamConflict.create(
                        "address_out_of_prefix",
                        "error",
                        tenant_id,
                        vrf,
                        f"lease:{lease.address}",
                        (f"DHCP lease {lease.address} is outside managed prefix {lease.prefix}",),
                        "Correct the DHCP scope or create the missing managed prefix.",
                    )
                )
            records = self._ipam_repository.list_address_records(tenant_id, vrf, lease.prefix)
            reservations = self._ipam_repository.list_reservations(tenant_id, vrf, lease.prefix)
            authoritative_names = {str(record.address): record.hostname for record in records} | {
                str(reservation.address): reservation.hostname for reservation in reservations
            }
            expected = authoritative_names.get(str(lease.address))
            if expected is not None and expected != lease.hostname:
                conflicts.append(
                    IpamConflict.create(
                        "lease_conflict",
                        "critical",
                        tenant_id,
                        vrf,
                        f"lease:{lease.address}",
                        (
                            f"lease hostname {lease.hostname} with MAC {lease.mac_address}",
                            f"authoritative owner {expected}",
                        ),
                        "Reclaim the lease, update reservation ownership or quarantine the client.",
                    )
                )
        return conflicts

    def _is_pool_overlay(self, first: IpRange, second: IpRange) -> bool:
        purposes = {first.purpose.value, second.purpose.value}
        return "allocation" in purposes and purposes != {"allocation"}


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
        edition_guard: EditionRuntimeGuard | None = None,
    ) -> None:
        self._ipam_repository = ipam_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._edition_guard = edition_guard

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
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_quota(
                tenant_id,
                QuotaResource.SUBNET_VLAN,
                1,
                command.actor,
                "ipam_prefix",
                str(prefix.network),
            )
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
                if ip_range.overlaps(existing) and not self._is_pool_overlay(ip_range, existing):
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
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            self._edition_guard.require_quota(
                tenant_id,
                QuotaResource.IP_DNS_RECORD,
                1,
                command.actor,
                "ipam_address",
                command.address,
            )
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

    def define_vlan_group(self, command: DefineVlanGroupCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        group = VlanGroup.create(tenant_id, command.name, command.scope, command.description)
        with self._transaction_manager.begin() as unit_of_work:
            stored = self._ipam_repository.add_vlan_group(group)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.vlan_group.defined",
                    target_type="ipam_vlan_group",
                    target_id=stored.name.value,
                    metadata={"scope": stored.scope.value if stored.scope else None},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def define_vxlan_vni(self, command: DefineVxlanVniCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        vni = VxlanVni.create(
            tenant_id,
            command.vni,
            command.name,
            command.vrf,
            command.route_targets_import,
            command.route_targets_export,
            command.description,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._ipam_repository.add_or_get_vrf(Vrf.create(tenant_id, command.vrf))
            existing = self._ipam_repository.find_vxlan_vni(tenant_id, vni.vni)
            if existing is not None and existing.vrf_name != vni.vrf_name:
                raise ConflictError("vxlan vni is already attached to another VRF")
            stored = self._ipam_repository.add_vxlan_vni(vni)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.vxlan_vni.defined",
                    target_type="ipam_vxlan_vni",
                    target_id=str(stored.vni),
                    metadata={"vrf": stored.vrf_name.value},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def define_vlan(self, command: DefineVlanCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        if self._edition_guard is not None and self._edition_guard.limited_runtime:
            existing_vlans = self._ipam_repository.list_vlans(tenant_id)
            exists = any(
                item.group_name.value == command.group.strip().upper()
                and item.vlan_id == command.vlan_id
                for item in existing_vlans
            )
            if not exists:
                self._edition_guard.require_quota(
                    tenant_id,
                    QuotaResource.SUBNET_VLAN,
                    1,
                    command.actor,
                    "ipam_vlan",
                    f"{command.group}:{command.vlan_id}",
                )
        vlan = Vlan.create(
            tenant_id,
            command.group,
            command.vlan_id,
            command.name,
            command.vrf,
            command.vni,
            command.description,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._ipam_repository.add_vlan_group(VlanGroup.create(tenant_id, command.group))
            if vlan.vrf_name is not None:
                self._ipam_repository.add_or_get_vrf(Vrf.create(tenant_id, vlan.vrf_name.value))
            if vlan.vni is not None:
                existing_vni = self._ipam_repository.find_vxlan_vni(tenant_id, vlan.vni)
                if existing_vni is None:
                    raise NotFoundError("vxlan vni must be defined before VLAN attachment")
                if vlan.vrf_name is None or existing_vni.vrf_name != vlan.vrf_name:
                    raise ConflictError("vlan VRF must match attached vxlan vni VRF")
            stored = self._ipam_repository.add_vlan(vlan)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.vlan.defined",
                    target_type="ipam_vlan",
                    target_id=f"{stored.group_name.value}:{stored.vlan_id}",
                    metadata={
                        "vrf": stored.vrf_name.value if stored.vrf_name else None,
                        "vni": stored.vni,
                    },
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def define_asn(self, command: DefineAsnCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        autonomous_system = AutonomousSystem.create(
            tenant_id,
            command.asn,
            command.name,
            command.description,
        )
        with self._transaction_manager.begin() as unit_of_work:
            stored = self._ipam_repository.add_asn(autonomous_system)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.asn.defined",
                    target_type="ipam_asn",
                    target_id=str(stored.number),
                    metadata={"name": stored.name.value},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def define_bgp_peer(self, command: DefineBgpPeerCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        peer = BgpPeer.create(
            tenant_id,
            command.vrf,
            command.local_asn,
            command.remote_asn,
            command.peer_address,
            command.address_family,
            command.route_targets_import,
            command.route_targets_export,
            command.description,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._ipam_repository.add_or_get_vrf(Vrf.create(tenant_id, command.vrf))
            if self._ipam_repository.find_asn(tenant_id, peer.local_asn) is None:
                raise NotFoundError("local ASN must be defined before BGP peer")
            if self._ipam_repository.find_asn(tenant_id, peer.remote_asn) is None:
                raise NotFoundError("remote ASN must be defined before BGP peer")
            stored = self._ipam_repository.add_bgp_peer(peer)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="ipam.bgp_peer.defined",
                    target_type="ipam_bgp_peer",
                    target_id=f"{stored.vrf_name.value}:{stored.peer_address}",
                    metadata={"local_asn": stored.local_asn, "remote_asn": stored.remote_asn},
                )
            )
            unit_of_work.commit()
        return stored.as_dict()

    def network_bindings(self, command: IpamNetworkBindingsCommand) -> IpamNetworkBindingsReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        vrf = command.vrf.strip() if command.vrf else None
        return IpamNetworkBindingsReport(
            tenant_id=tenant_id.value,
            vrf=vrf,
            vlan_groups=tuple(
                group.as_dict() for group in self._ipam_repository.list_vlan_groups(tenant_id)
            ),
            vlans=tuple(
                vlan.as_dict() for vlan in self._ipam_repository.list_vlans(tenant_id, vrf)
            ),
            vxlan_vnis=tuple(
                vni.as_dict() for vni in self._ipam_repository.list_vxlan_vnis(tenant_id, vrf)
            ),
            asns=tuple(asn.as_dict() for asn in self._ipam_repository.list_asns(tenant_id)),
            bgp_peers=tuple(
                peer.as_dict() for peer in self._ipam_repository.list_bgp_peers(tenant_id, vrf)
            ),
        )

    def topology(self, command: IpamTopologyCommand) -> IpamTopologyReport:
        tenant_id = TenantId.from_value(command.tenant_id)
        requested_vrf = command.vrf.strip() if command.vrf else None
        vrfs = self._topology_vrfs(tenant_id, requested_vrf)
        nodes: list[dict[str, object]] = [
            self._topology_node(
                f"tenant:{tenant_id.value}",
                "tenant",
                tenant_id.value,
                tenant_id=tenant_id.value,
            )
        ]
        edges: list[dict[str, str]] = []
        summary: dict[str, int] = {
            "vrfs": len(vrfs),
            "aggregates": 0,
            "prefixes": 0,
            "ranges": 0,
            "address_records": 0,
            "reservations": 0,
            "vlan_groups": 0,
            "vlans": 0,
            "vxlan_vnis": 0,
            "asns": 0,
            "bgp_peers": 0,
            "dns_observations": 0,
            "dhcp_leases": 0,
        }
        for vrf in vrfs:
            self._append_vrf_topology(tenant_id, vrf, nodes, edges, summary)
        self._append_network_binding_topology(tenant_id, requested_vrf, nodes, edges, summary)
        unique_nodes = self._deduplicate_nodes(nodes)
        unique_edges = self._deduplicate_edges(edges)
        summary["nodes"] = len(unique_nodes)
        summary["edges"] = len(unique_edges)
        orphan_edges = tuple(
            edge
            for edge in unique_edges
            if edge["source"] not in {str(node["id"]) for node in unique_nodes}
            or edge["target"] not in {str(node["id"]) for node in unique_nodes}
        )
        report = IpamTopologyReport(
            tenant_id=tenant_id.value,
            vrf=requested_vrf,
            summary=summary,
            nodes=unique_nodes,
            edges=unique_edges,
            integrity={
                "orphan_edges": len(orphan_edges),
                "valid": len(orphan_edges) == 0,
            },
        )
        self._audit_repository.append(
            AuditEvent.record(
                tenant_id=tenant_id,
                actor=command.actor,
                action="ipam.topology.generated",
                target_type="ipam_topology",
                target_id=requested_vrf or "*",
                metadata={"nodes": len(unique_nodes), "edges": len(unique_edges)},
            )
        )
        return report

    def list_prefixes(self, tenant_id: str, vrf: str) -> tuple[dict[str, str | int], ...]:
        tenant = TenantId.from_value(tenant_id)
        return tuple(
            self._prefix_as_dict(prefix)
            for prefix in self._ipam_repository.list_prefixes(tenant, vrf)
        )

    def _topology_vrfs(self, tenant_id: TenantId, requested_vrf: str | None) -> tuple[Vrf, ...]:
        vrfs = self._ipam_repository.list_vrfs(tenant_id)
        if requested_vrf is None:
            return vrfs
        return tuple(vrf for vrf in vrfs if vrf.name.value == requested_vrf)

    def _append_vrf_topology(
        self,
        tenant_id: TenantId,
        vrf: Vrf,
        nodes: list[dict[str, object]],
        edges: list[dict[str, str]],
        summary: dict[str, int],
    ) -> None:
        tenant_node = f"tenant:{tenant_id.value}"
        vrf_node = f"vrf:{vrf.name.value}"
        nodes.append(
            self._topology_node(
                vrf_node,
                "vrf",
                vrf.name.value,
                route_distinguisher=vrf.route_distinguisher,
            )
        )
        edges.append(self._topology_edge(tenant_node, vrf_node, "contains"))
        for aggregate in self._ipam_repository.list_aggregates(tenant_id, vrf.name.value):
            aggregate_node = f"aggregate:{vrf.name.value}:{aggregate.network}"
            nodes.append(
                self._topology_node(
                    aggregate_node,
                    "aggregate",
                    str(aggregate.network),
                    vrf=vrf.name.value,
                    family=aggregate.network.version,
                    description=aggregate.description,
                )
            )
            edges.append(self._topology_edge(vrf_node, aggregate_node, "announces"))
            summary["aggregates"] += 1
        for prefix in self._ipam_repository.list_prefixes(tenant_id, vrf.name.value):
            self._append_prefix_topology(tenant_id, vrf, prefix, nodes, edges, summary)
        for record in self._ipam_repository.list_dns_observations(tenant_id, vrf.name.value):
            node_id = f"dns:{vrf.name.value}:{record.hostname}:{record.address}"
            nodes.append(
                self._topology_node(
                    node_id,
                    "dns_observation",
                    record.hostname,
                    vrf=vrf.name.value,
                    address=str(record.address),
                    ptr_hostname=record.ptr_hostname,
                    source=record.source,
                )
            )
            edges.append(self._topology_edge(vrf_node, node_id, "observes_dns"))
            summary["dns_observations"] += 1
        for lease in self._ipam_repository.list_dhcp_leases(tenant_id, vrf.name.value):
            node_id = f"dhcp:{vrf.name.value}:{lease.address}:{lease.mac_address}"
            nodes.append(
                self._topology_node(
                    node_id,
                    "dhcp_lease",
                    lease.hostname,
                    vrf=vrf.name.value,
                    prefix=lease.prefix,
                    address=str(lease.address),
                    mac_address=lease.mac_address,
                    active=lease.active,
                    source=lease.source,
                )
            )
            edges.append(self._topology_edge(vrf_node, node_id, "observes_dhcp"))
            summary["dhcp_leases"] += 1

    def _append_prefix_topology(
        self,
        tenant_id: TenantId,
        vrf: Vrf,
        prefix: Prefix,
        nodes: list[dict[str, object]],
        edges: list[dict[str, str]],
        summary: dict[str, int],
    ) -> None:
        vrf_node = f"vrf:{vrf.name.value}"
        prefix_node = f"prefix:{vrf.name.value}:{prefix.network}"
        nodes.append(
            self._topology_node(
                prefix_node,
                "prefix",
                str(prefix.network),
                vrf=vrf.name.value,
                family=prefix.network.version,
                first_usable=str(ipaddress.ip_address(prefix.first_usable_int)),
                last_usable=str(ipaddress.ip_address(prefix.last_usable_int)),
                description=prefix.description,
            )
        )
        edges.append(self._topology_edge(vrf_node, prefix_node, "contains"))
        summary["prefixes"] += 1
        for ip_range in self._ipam_repository.list_ranges(
            tenant_id, vrf.name.value, str(prefix.network)
        ):
            range_node = f"range:{vrf.name.value}:{prefix.network}:{ip_range.start}-{ip_range.end}"
            nodes.append(
                self._topology_node(
                    range_node,
                    "range",
                    f"{ip_range.start}-{ip_range.end}",
                    vrf=vrf.name.value,
                    prefix=str(prefix.network),
                    purpose=ip_range.purpose.value,
                    description=ip_range.description,
                )
            )
            edges.append(self._topology_edge(prefix_node, range_node, "segments"))
            summary["ranges"] += 1
        for record in self._ipam_repository.list_address_records(
            tenant_id, vrf.name.value, str(prefix.network)
        ):
            record_node = f"address:{vrf.name.value}:{record.address}"
            nodes.append(
                self._topology_node(
                    record_node,
                    "address_record",
                    str(record.address),
                    vrf=vrf.name.value,
                    prefix=str(prefix.network),
                    hostname=record.hostname,
                    status=record.status.value,
                    interface_name=record.interface_name.value if record.interface_name else "",
                )
            )
            edges.append(self._topology_edge(prefix_node, record_node, "assigns"))
            summary["address_records"] += 1
        for reservation in self._ipam_repository.list_reservations(
            tenant_id, vrf.name.value, str(prefix.network)
        ):
            reservation_node = (
                f"reservation:{vrf.name.value}:{reservation.address}:{reservation.idempotency_key}"
            )
            nodes.append(
                self._topology_node(
                    reservation_node,
                    "reservation",
                    str(reservation.address),
                    vrf=vrf.name.value,
                    prefix=str(prefix.network),
                    hostname=reservation.hostname,
                    idempotency_key=reservation.idempotency_key,
                )
            )
            edges.append(self._topology_edge(prefix_node, reservation_node, "reserves"))
            summary["reservations"] += 1

    def _append_network_binding_topology(
        self,
        tenant_id: TenantId,
        requested_vrf: str | None,
        nodes: list[dict[str, object]],
        edges: list[dict[str, str]],
        summary: dict[str, int],
    ) -> None:
        tenant_node = f"tenant:{tenant_id.value}"
        for group in self._ipam_repository.list_vlan_groups(tenant_id):
            group_node = f"vlan-group:{group.name.value}"
            nodes.append(
                self._topology_node(
                    group_node,
                    "vlan_group",
                    group.name.value,
                    scope=group.scope.value if group.scope else None,
                    description=group.description,
                )
            )
            edges.append(self._topology_edge(tenant_node, group_node, "contains"))
            summary["vlan_groups"] += 1
        for vni in self._ipam_repository.list_vxlan_vnis(tenant_id, requested_vrf):
            vni_node = f"vni:{vni.vni}"
            nodes.append(
                self._topology_node(
                    vni_node,
                    "vxlan_vni",
                    str(vni.vni),
                    name=vni.name.value,
                    vrf=vni.vrf_name.value,
                    route_targets_import=list(vni.route_targets_import),
                    route_targets_export=list(vni.route_targets_export),
                )
            )
            edges.append(self._topology_edge(f"vrf:{vni.vrf_name.value}", vni_node, "owns_vni"))
            summary["vxlan_vnis"] += 1
        for vlan in self._ipam_repository.list_vlans(tenant_id, requested_vrf):
            vlan_node = f"vlan:{vlan.group_name.value}:{vlan.vlan_id}"
            nodes.append(
                self._topology_node(
                    vlan_node,
                    "vlan",
                    str(vlan.vlan_id),
                    group=vlan.group_name.value,
                    name=vlan.name.value,
                    vrf=vlan.vrf_name.value if vlan.vrf_name else None,
                    vni=vlan.vni,
                )
            )
            edges.append(
                self._topology_edge(f"vlan-group:{vlan.group_name.value}", vlan_node, "contains")
            )
            if vlan.vrf_name is not None:
                edges.append(
                    self._topology_edge(f"vrf:{vlan.vrf_name.value}", vlan_node, "binds_vlan")
                )
            if vlan.vni is not None:
                edges.append(self._topology_edge(vlan_node, f"vni:{vlan.vni}", "maps_to_vni"))
            summary["vlans"] += 1
        for asn in self._ipam_repository.list_asns(tenant_id):
            asn_node = f"asn:{asn.number}"
            nodes.append(
                self._topology_node(
                    asn_node,
                    "asn",
                    str(asn.number),
                    name=asn.name.value,
                    description=asn.description,
                )
            )
            edges.append(self._topology_edge(tenant_node, asn_node, "owns_asn"))
            summary["asns"] += 1
        for peer in self._ipam_repository.list_bgp_peers(tenant_id, requested_vrf):
            peer_node = f"bgp-peer:{peer.vrf_name.value}:{peer.peer_address}"
            nodes.append(
                self._topology_node(
                    peer_node,
                    "bgp_peer",
                    str(peer.peer_address),
                    vrf=peer.vrf_name.value,
                    local_asn=peer.local_asn,
                    remote_asn=peer.remote_asn,
                    address_family=peer.address_family.value,
                    route_targets_import=list(peer.route_targets_import),
                    route_targets_export=list(peer.route_targets_export),
                )
            )
            edges.append(
                self._topology_edge(f"vrf:{peer.vrf_name.value}", peer_node, "has_bgp_peer")
            )
            edges.append(self._topology_edge(f"asn:{peer.local_asn}", peer_node, "local_asn"))
            edges.append(self._topology_edge(peer_node, f"asn:{peer.remote_asn}", "remote_asn"))
            summary["bgp_peers"] += 1

    def _topology_node(
        self, node_id: str, kind: str, label: str, **attributes: object
    ) -> dict[str, object]:
        return {
            "id": node_id,
            "kind": kind,
            "label": label,
            "attributes": {key: value for key, value in attributes.items() if value is not None},
        }

    def _topology_edge(self, source: str, target: str, relation: str) -> dict[str, str]:
        return {"source": source, "target": target, "relation": relation}

    def _deduplicate_nodes(self, nodes: list[dict[str, object]]) -> tuple[dict[str, object], ...]:
        deduplicated: dict[str, dict[str, object]] = {}
        for node in nodes:
            deduplicated[str(node["id"])] = node
        return tuple(deduplicated[key] for key in sorted(deduplicated))

    def _deduplicate_edges(self, edges: list[dict[str, str]]) -> tuple[dict[str, str], ...]:
        deduplicated = {(edge["source"], edge["target"], edge["relation"]): edge for edge in edges}
        return tuple(deduplicated[key] for key in sorted(deduplicated))

    def _is_pool_overlay(self, first: IpRange, second: IpRange) -> bool:
        purposes = {first.purpose.value, second.purpose.value}
        return "allocation" in purposes and purposes != {"allocation"}

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
