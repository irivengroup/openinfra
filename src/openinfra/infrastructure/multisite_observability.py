from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from openinfra.application.ports import DiscoveryRepository, MultisiteRepository
from openinfra.domain.common import Pagination, TenantId, ValidationError
from openinfra.domain.multisite import RegionalDiscoveryRoute

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class MultisiteAgentSiteMetrics:
    region: str
    site: str
    agent_lag_seconds: float
    collectors_total: int
    collectors_healthy: int
    collectors_degraded: int
    collectors_maintenance: int
    collectors_stale: int

    @property
    def healthy(self) -> bool:
        return self.collectors_total > 0 and self.collectors_healthy == self.collectors_total

    def as_dict(self) -> dict[str, object]:
        return {
            "region": self.region,
            "site": self.site,
            "agent_lag_seconds": self.agent_lag_seconds,
            "collectors_total": self.collectors_total,
            "collectors_healthy": self.collectors_healthy,
            "collectors_degraded": self.collectors_degraded,
            "collectors_maintenance": self.collectors_maintenance,
            "collectors_stale": self.collectors_stale,
            "healthy": self.healthy,
        }


class MultisiteOperationalMetricsProvider:
    _page_size: Final[int] = 500
    _max_routes: Final[int] = 10_000

    def __init__(
        self,
        multisite_repository: MultisiteRepository,
        discovery_repository: DiscoveryRepository,
        *,
        tenant_id: str = "default",
        agent_stale_after_seconds: int = 120,
        clock: Clock | None = None,
    ) -> None:
        self._multisite_repository = multisite_repository
        self._discovery_repository = discovery_repository
        self._tenant_id = TenantId.from_value(tenant_id)
        if not 10 <= int(agent_stale_after_seconds) <= 86_400:
            raise ValidationError(
                "multisite agent stale threshold must be between 10 and 86400 seconds"
            )
        self._agent_stale_after_seconds = int(agent_stale_after_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))

    @classmethod
    def from_environment(
        cls,
        multisite_repository: MultisiteRepository,
        discovery_repository: DiscoveryRepository,
        *,
        clock: Clock | None = None,
    ) -> MultisiteOperationalMetricsProvider:
        raw_threshold = os.environ.get(
            "OPENINFRA_MULTISITE_AGENT_STALE_AFTER_SECONDS", "120"
        ).strip()
        try:
            threshold = int(raw_threshold)
        except ValueError as exc:
            raise ValidationError(
                "OPENINFRA_MULTISITE_AGENT_STALE_AFTER_SECONDS must be an integer"
            ) from exc
        return cls(
            multisite_repository,
            discovery_repository,
            tenant_id=os.environ.get("OPENINFRA_OBSERVABILITY_TENANT_ID", "default"),
            agent_stale_after_seconds=threshold,
            clock=clock,
        )

    def __call__(self) -> dict[str, object]:
        now = self._clock()
        if now.tzinfo is None:
            raise ValidationError("multisite observability clock must be timezone-aware")
        now = now.astimezone(UTC)
        grouped: dict[tuple[str, str], dict[str, tuple[float, str]]] = defaultdict(dict)
        for route in self._routes():
            collector = self._discovery_repository.get_collector(
                self._tenant_id, route.collector_id.value
            )
            if collector is None:
                grouped[(route.region_code, route.site_code)][route.collector_id.value] = (
                    float(self._agent_stale_after_seconds + 1),
                    "stale",
                )
                continue
            observed_at = collector.last_heartbeat_at or collector.registered_at
            age = max(0.0, (now - observed_at.astimezone(UTC)).total_seconds())
            state = self._collector_state(
                collector_status=collector.status.value,
                heartbeat_status=collector.last_heartbeat_status,
                age_seconds=age,
            )
            grouped[(route.region_code, route.site_code)][route.collector_id.value] = (age, state)

        sites = tuple(
            self._site_metrics(region, site, list(samples.values()))
            for (region, site), samples in sorted(grouped.items())
        )
        return {
            "tenant_scope": self._tenant_id.value,
            "agent_stale_after_seconds": self._agent_stale_after_seconds,
            "sites": [item.as_dict() for item in sites],
        }

    def _routes(self) -> tuple[RegionalDiscoveryRoute, ...]:
        cursor: str | None = None
        routes: list[RegionalDiscoveryRoute] = []
        seen_cursors: set[str] = set()
        while True:
            page = self._multisite_repository.list_regional_routes(
                self._tenant_id,
                Pagination.from_values(self._page_size, cursor),
                active_only=True,
            )
            routes.extend(page.items)
            if len(routes) > self._max_routes:
                raise ValidationError(
                    f"multisite observability exceeds the bounded route limit {self._max_routes}"
                )
            cursor = page.next_cursor
            if cursor is None:
                return tuple(routes)
            if cursor in seen_cursors:
                raise ValidationError("multisite route pagination cursor loop detected")
            seen_cursors.add(cursor)

    def _collector_state(
        self,
        *,
        collector_status: str,
        heartbeat_status: str | None,
        age_seconds: float,
    ) -> str:
        if collector_status != "active" or age_seconds > self._agent_stale_after_seconds:
            return "stale"
        normalized = (heartbeat_status or "degraded").strip().lower()
        if normalized == "ok":
            return "healthy"
        if normalized == "maintenance":
            return "maintenance"
        return "degraded"

    @staticmethod
    def _site_metrics(
        region: str,
        site: str,
        samples: list[tuple[float, str]],
    ) -> MultisiteAgentSiteMetrics:
        counts = dict.fromkeys(("healthy", "degraded", "maintenance", "stale"), 0)
        for _age, state in samples:
            counts[state] += 1
        return MultisiteAgentSiteMetrics(
            region=region,
            site=site,
            agent_lag_seconds=max((age for age, _state in samples), default=0.0),
            collectors_total=len(samples),
            collectors_healthy=counts["healthy"],
            collectors_degraded=counts["degraded"],
            collectors_maintenance=counts["maintenance"],
            collectors_stale=counts["stale"],
        )
