from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from openinfra.application.discovery_services import ListCollectorsCommand
from openinfra.application.ipam_services import IpamSearchCommand
from openinfra.application.itam_services import GetAssetSupportProfileCommand
from openinfra.application.ports import AuditRepository, TransactionManager
from openinfra.application.source_of_truth_services import ListSourceObjectsCommand
from openinfra.domain.common import (
    AccessDeniedError,
    AuditEvent,
    NotFoundError,
    TenantId,
    ValidationError,
)


@dataclass(frozen=True, slots=True)
class GlobalSearchCommand:
    tenant_id: str
    actor: str
    admin_token: str
    query: str
    limit: int = 5
    include_inactive_discovery: bool = False


@dataclass(frozen=True, slots=True)
class GlobalSearchItem:
    component: str
    kind: str
    label: str
    description: str
    route: str
    score: int
    metadata: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "kind": self.kind,
            "label": self.label,
            "description": self.description,
            "route": self.route,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class GlobalSearchGroup:
    component: str
    label: str
    status: str
    items: tuple[GlobalSearchItem, ...]
    total: int
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "component": self.component,
            "label": self.label,
            "status": self.status,
            "total": self.total,
            "items": [item.as_dict() for item in self.items],
        }
        if self.reason:
            payload["reason"] = self.reason
        return payload


@dataclass(frozen=True, slots=True)
class GlobalSearchResult:
    tenant_id: str
    query: str
    limit: int
    total: int
    groups: tuple[GlobalSearchGroup, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "query": self.query,
            "limit": self.limit,
            "total": self.total,
            "groups": [group.as_dict() for group in self.groups],
        }


class GlobalSearchService:
    def __init__(
        self,
        rsot_service: Any,
        ipam_ui_service: Any,
        discovery_service: Any,
        itam_support_service: Any,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._rsot_service = rsot_service
        self._ipam_ui_service = ipam_ui_service
        self._discovery_service = discovery_service
        self._itam_support_service = itam_support_service
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager

    def search(self, command: GlobalSearchCommand) -> GlobalSearchResult:
        tenant_id = TenantId.from_value(command.tenant_id)
        query = " ".join(command.query.strip().split())
        if not 2 <= len(query) <= 128:
            raise ValidationError("global search query must contain 2 to 128 characters")
        limit = self._normalize_limit(command.limit)
        groups = (
            self._search_rsot(tenant_id, command, query, limit),
            self._search_itam(tenant_id, command, query, limit),
            self._search_ipam(tenant_id, command, query, limit),
            self._search_discovery(tenant_id, command, query, limit),
        )
        visible_total = sum(group.total for group in groups if group.status == "ok")
        with self._transaction_manager.begin() as unit_of_work:
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=command.actor,
                    action="global.search.executed",
                    target_type="global_search",
                    target_id=self._normalized(query),
                    metadata={
                        "query_length": len(query),
                        "limit": limit,
                        "total": visible_total,
                        "groups": [group.component for group in groups],
                    },
                )
            )
            unit_of_work.commit()
        return GlobalSearchResult(
            tenant_id=tenant_id.value,
            query=query,
            limit=limit,
            total=visible_total,
            groups=groups,
        )

    def _normalize_limit(self, value: int) -> int:
        normalized = int(value)
        if not 1 <= normalized <= 25:
            raise ValidationError("global search limit must be between 1 and 25")
        return normalized

    def _search_rsot(
        self, tenant_id: TenantId, command: GlobalSearchCommand, query: str, limit: int
    ) -> GlobalSearchGroup:
        try:
            page = self._rsot_service.list_objects(
                ListSourceObjectsCommand(
                    tenant_id=tenant_id.value,
                    admin_token=command.admin_token,
                    limit=200,
                )
            )
        except AccessDeniedError:
            return self._skipped("rsot", "RSOT", "permission denied")
        matches: list[GlobalSearchItem] = []
        for source_object in page.items:
            row = source_object.as_dict()
            fields = (
                str(row.get("key", "")),
                str(row.get("display_name", "")),
                str(row.get("kind", "")),
                str(row.get("resource_category", "")),
                str(row.get("resource_type", "")),
                " ".join(str(item) for item in row.get("tags", ())),
                json.dumps(row.get("attributes", {}), sort_keys=True, ensure_ascii=False),
            )
            score = self._score(query, fields)
            if score == 0:
                continue
            label = str(row.get("display_name") or row.get("key"))
            key = str(row.get("key", ""))
            matches.append(
                GlobalSearchItem(
                    component="rsot",
                    kind=str(row.get("resource_type") or row.get("kind") or "object"),
                    label=label,
                    description=(
                        f"{row.get('kind', 'object')} · {key} · "
                        f"source {row.get('source', 'unknown')}"
                    ),
                    route=(
                        "/api/v1/rsot/objects?tenant_id="
                        f"{quote(tenant_id.value)}&key={quote(key)}"
                    ),
                    score=score,
                    metadata={
                        "key": key,
                        "kind": row.get("kind"),
                        "resource_category": row.get("resource_category"),
                        "resource_type": row.get("resource_type"),
                        "version": row.get("version"),
                    },
                )
            )
        return self._ok("rsot", "RSOT", matches, limit)

    def _search_itam(
        self, tenant_id: TenantId, command: GlobalSearchCommand, query: str, limit: int
    ) -> GlobalSearchGroup:
        try:
            profile = self._itam_support_service.get_support_profile(
                GetAssetSupportProfileCommand(
                    tenant_id=tenant_id.value,
                    admin_token=command.admin_token,
                    asset_tag=query,
                )
            )
        except AccessDeniedError:
            return self._skipped("itam", "ITAM", "permission denied")
        except (NotFoundError, ValidationError):
            return self._ok("itam", "ITAM", [], limit)

        row = profile.as_dict()
        warranty = row.get("manufacturer_warranty", {})
        if not isinstance(warranty, dict):
            warranty = {}
        fields = (
            str(row.get("asset_tag", "")),
            str(warranty.get("manufacturer", "")),
            str(warranty.get("warranty_reference", "")),
            str(warranty.get("support_reference", "")),
            str(warranty.get("support_level", "")),
            json.dumps(row.get("third_party_contracts", []), sort_keys=True, ensure_ascii=False),
        )
        score = self._score(query, fields)
        if score == 0:
            return self._ok("itam", "ITAM", [], limit)
        asset_tag = str(row.get("asset_tag", query))
        manufacturer = str(warranty.get("manufacturer", "constructeur"))
        item = GlobalSearchItem(
            component="itam",
            kind="support-profile",
            label=asset_tag,
            description=f"{manufacturer} · garantie {warranty.get('warranty_reference', 'n/a')}",
            route=(
                "/api/v1/itam/support-profile?tenant_id="
                f"{quote(tenant_id.value)}&asset_tag={quote(asset_tag)}"
            ),
            score=score,
            metadata={
                "asset_tag": asset_tag,
                "manufacturer": warranty.get("manufacturer"),
                "warranty_reference": warranty.get("warranty_reference"),
                "support_reference": warranty.get("support_reference"),
            },
        )
        return self._ok("itam", "ITAM", [item], limit)

    def _search_ipam(
        self, tenant_id: TenantId, command: GlobalSearchCommand, query: str, limit: int
    ) -> GlobalSearchGroup:
        payload = self._ipam_ui_service.search(
            IpamSearchCommand(
                tenant_id=tenant_id.value,
                actor=command.actor,
                query=query,
            )
        )
        matches: list[GlobalSearchItem] = []
        for row in payload.get("items", []):
            if not isinstance(row, dict):
                continue
            fields = tuple(str(value) for value in row.values())
            score = self._score(query, fields)
            if score == 0:
                continue
            kind = str(row.get("kind", "ipam"))
            label = self._ipam_label(kind, row)
            route = (
                f"/api/v1/ipam/ui-search?tenant_id={quote(tenant_id.value)}"
                f"&query={quote(query)}"
            )
            vrf = str(row.get("vrf", ""))
            matches.append(
                GlobalSearchItem(
                    component="ipam",
                    kind=kind,
                    label=label,
                    description=f"{kind} · VRF {vrf or '*'}",
                    route=route,
                    score=score,
                    metadata={key: value for key, value in row.items() if key != "kind"},
                )
            )
        return self._ok("ipam", "IPAM", matches, limit)

    def _search_discovery(
        self, tenant_id: TenantId, command: GlobalSearchCommand, query: str, limit: int
    ) -> GlobalSearchGroup:
        try:
            page = self._discovery_service.list_collectors(
                ListCollectorsCommand(
                    tenant_id=tenant_id.value,
                    admin_token=command.admin_token,
                    limit=200,
                    include_inactive=command.include_inactive_discovery,
                )
            )
        except AccessDeniedError:
            return self._skipped("discovery", "Discovery", "permission denied")
        matches: list[GlobalSearchItem] = []
        for collector in page.items:
            row = collector.as_dict()
            fields = (
                str(row.get("id", "")),
                str(row.get("name", "")),
                str(row.get("kind", "")),
                str(row.get("status", "")),
                " ".join(str(item) for item in row.get("scopes", ())),
                str(row.get("endpoint_url", "")),
            )
            score = self._score(query, fields)
            if score == 0:
                continue
            collector_id = str(row.get("id", ""))
            matches.append(
                GlobalSearchItem(
                    component="discovery",
                    kind=str(row.get("kind", "collector")),
                    label=str(row.get("name") or collector_id),
                    description=(
                        f"{row.get('kind', 'collector')} · {row.get('status', 'unknown')} · "
                        f"{len(row.get('scopes', []))} scope(s)"
                    ),
                    route=(
                        "/api/v1/discovery/collectors?tenant_id="
                        f"{quote(tenant_id.value)}&include_inactive=true"
                    ),
                    score=score,
                    metadata={
                        "collector_id": collector_id,
                        "kind": row.get("kind"),
                        "status": row.get("status"),
                        "endpoint_url": row.get("endpoint_url"),
                    },
                )
            )
        return self._ok("discovery", "Discovery", matches, limit)

    def _ok(
        self, component: str, label: str, matches: list[GlobalSearchItem], limit: int
    ) -> GlobalSearchGroup:
        ordered = tuple(sorted(matches, key=lambda item: (-item.score, item.label.lower())))
        return GlobalSearchGroup(
            component=component,
            label=label,
            status="ok",
            items=ordered[:limit],
            total=len(ordered),
        )

    def _skipped(self, component: str, label: str, reason: str) -> GlobalSearchGroup:
        return GlobalSearchGroup(
            component=component,
            label=label,
            status="skipped",
            items=(),
            total=0,
            reason=reason,
        )

    def _ipam_label(self, kind: str, row: dict[str, object]) -> str:
        if kind == "prefix":
            return str(row.get("prefix", "prefix"))
        if kind == "reservation":
            return f"{row.get('address', '')} · {row.get('hostname', '')}".strip(" ·")
        if kind == "dns":
            return f"{row.get('hostname', '')} → {row.get('address', '')}".strip(" →")
        if kind == "dhcp_lease":
            return f"{row.get('address', '')} · {row.get('mac_address', '')}".strip(" ·")
        return str(row.get("address") or row.get("hostname") or row.get("prefix") or kind)

    def _score(self, query: str, fields: tuple[str, ...]) -> int:
        normalized_query = self._normalized(query)
        best = 0
        for field in fields:
            normalized_field = self._normalized(field)
            if not normalized_field:
                continue
            if normalized_field == normalized_query:
                best = max(best, 100)
            elif normalized_field.startswith(normalized_query):
                best = max(best, 85)
            elif normalized_query in normalized_field:
                best = max(best, 60)
        return best

    def _normalized(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value)
        without_marks = "".join(char for char in ascii_value if not unicodedata.combining(char))
        return " ".join(without_marks.lower().split())
