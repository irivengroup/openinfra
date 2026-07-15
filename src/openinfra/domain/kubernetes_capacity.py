from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from openinfra.domain.common import ValidationError
from openinfra.domain.kubernetes_topology import (
    KubernetesResource,
    KubernetesResourceKind,
    KubernetesTopologySnapshot,
)


class KubernetesCapacitySeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class KubernetesCapacityValues:
    cpu_request_millicores: int = 0
    cpu_limit_millicores: int = 0
    cpu_usage_millicores: int = 0
    cpu_capacity_millicores: int = 0
    memory_request_bytes: int = 0
    memory_limit_bytes: int = 0
    memory_usage_bytes: int = 0
    memory_capacity_bytes: int = 0
    storage_request_bytes: int = 0
    storage_limit_bytes: int = 0
    storage_usage_bytes: int = 0
    storage_capacity_bytes: int = 0

    @classmethod
    def from_resource(cls, resource: KubernetesResource) -> KubernetesCapacityValues:
        raw = resource.attributes.get("capacity")
        if not isinstance(raw, dict):
            return cls()
        values = {field: int(raw.get(field, 0)) for field in cls.__dataclass_fields__}
        return cls(**values)

    def add(self, other: KubernetesCapacityValues) -> KubernetesCapacityValues:
        return KubernetesCapacityValues(
            **{
                field: getattr(self, field) + getattr(other, field)
                for field in self.__dataclass_fields__
            }
        )

    @staticmethod
    def _percent(numerator: int, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return round((numerator / denominator) * 100.0, 2)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            field: getattr(self, field) for field in self.__dataclass_fields__
        }
        payload.update(
            {
                "cpu_usage_percent": self._percent(
                    self.cpu_usage_millicores, self.cpu_capacity_millicores
                ),
                "cpu_request_percent": self._percent(
                    self.cpu_request_millicores, self.cpu_capacity_millicores
                ),
                "memory_usage_percent": self._percent(
                    self.memory_usage_bytes, self.memory_capacity_bytes
                ),
                "memory_request_percent": self._percent(
                    self.memory_request_bytes, self.memory_capacity_bytes
                ),
                "storage_usage_percent": self._percent(
                    self.storage_usage_bytes, self.storage_capacity_bytes
                ),
                "storage_request_percent": self._percent(
                    self.storage_request_bytes, self.storage_capacity_bytes
                ),
                "cpu_margin_millicores": max(
                    self.cpu_capacity_millicores - self.cpu_usage_millicores, 0
                ),
                "memory_margin_bytes": max(self.memory_capacity_bytes - self.memory_usage_bytes, 0),
                "storage_margin_bytes": max(
                    self.storage_capacity_bytes - self.storage_usage_bytes, 0
                ),
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class KubernetesNamespaceCapacity:
    namespace: str
    pod_count: int
    volume_count: int
    values: KubernetesCapacityValues

    def as_dict(self) -> dict[str, object]:
        payload = self.values.as_dict()
        payload.update(
            {
                "namespace": self.namespace,
                "pod_count": self.pod_count,
                "volume_count": self.volume_count,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class KubernetesCapacityAlert:
    severity: KubernetesCapacitySeverity
    scope: str
    scope_key: str
    resource: str
    signal: str
    value_percent: float
    threshold_percent: float

    def as_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity.value,
            "scope": self.scope,
            "scope_key": self.scope_key,
            "resource": self.resource,
            "signal": self.signal,
            "value_percent": self.value_percent,
            "threshold_percent": self.threshold_percent,
        }


@dataclass(frozen=True, slots=True)
class KubernetesCapacityReport:
    snapshot_id: str
    fingerprint: str
    cluster_key: str
    cluster_name: str
    observed_at: datetime
    warning_threshold_percent: float
    critical_threshold_percent: float
    cluster: KubernetesCapacityValues
    namespaces: tuple[KubernetesNamespaceCapacity, ...]
    alerts: tuple[KubernetesCapacityAlert, ...]
    coverage: dict[str, int]

    _MAX_NAMESPACES = 5_000

    @classmethod
    def build(
        cls,
        snapshot: KubernetesTopologySnapshot,
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 90.0,
    ) -> KubernetesCapacityReport:
        warning, critical = cls._thresholds(warning_threshold_percent, critical_threshold_percent)
        node_capacity = KubernetesCapacityValues()
        cluster_workload = KubernetesCapacityValues()
        namespace_values: dict[str, KubernetesCapacityValues] = {}
        pod_counts: dict[str, int] = {}
        volume_counts: dict[str, int] = {}
        coverage = {"nodes": 0, "pods": 0, "volumes": 0, "resources_with_capacity": 0}

        for resource in snapshot.resources:
            values = KubernetesCapacityValues.from_resource(resource)
            has_capacity = any(getattr(values, field) > 0 for field in values.__dataclass_fields__)
            if has_capacity:
                coverage["resources_with_capacity"] += 1
            if resource.kind is KubernetesResourceKind.NODE:
                coverage["nodes"] += int(has_capacity)
                node_capacity = node_capacity.add(
                    KubernetesCapacityValues(
                        cpu_capacity_millicores=values.cpu_capacity_millicores,
                        memory_capacity_bytes=values.memory_capacity_bytes,
                        storage_capacity_bytes=values.storage_capacity_bytes,
                    )
                )
                continue
            if resource.namespace is None:
                continue
            namespace_values.setdefault(resource.namespace, KubernetesCapacityValues())
            if resource.kind is KubernetesResourceKind.POD:
                coverage["pods"] += int(has_capacity)
                pod_counts[resource.namespace] = pod_counts.get(resource.namespace, 0) + 1
                selected = KubernetesCapacityValues(
                    cpu_request_millicores=values.cpu_request_millicores,
                    cpu_limit_millicores=values.cpu_limit_millicores,
                    cpu_usage_millicores=values.cpu_usage_millicores,
                    memory_request_bytes=values.memory_request_bytes,
                    memory_limit_bytes=values.memory_limit_bytes,
                    memory_usage_bytes=values.memory_usage_bytes,
                )
                namespace_values[resource.namespace] = namespace_values[resource.namespace].add(
                    selected
                )
                cluster_workload = cluster_workload.add(selected)
            elif resource.kind is KubernetesResourceKind.VOLUME:
                coverage["volumes"] += int(has_capacity)
                volume_counts[resource.namespace] = volume_counts.get(resource.namespace, 0) + 1
                selected = KubernetesCapacityValues(
                    storage_request_bytes=values.storage_request_bytes,
                    storage_limit_bytes=values.storage_limit_bytes,
                    storage_usage_bytes=values.storage_usage_bytes,
                    storage_capacity_bytes=values.storage_capacity_bytes,
                )
                namespace_values[resource.namespace] = namespace_values[resource.namespace].add(
                    selected
                )
                cluster_workload = cluster_workload.add(selected)

        if len(namespace_values) > cls._MAX_NAMESPACES:
            raise ValidationError(
                f"Kubernetes capacity report cannot exceed {cls._MAX_NAMESPACES} namespaces"
            )

        cluster = cluster_workload.add(node_capacity)
        # Persistent volume capacity is authoritative when present; node storage is only a fallback.
        if cluster_workload.storage_capacity_bytes > 0:
            cluster = KubernetesCapacityValues(
                **{
                    **{field: getattr(cluster, field) for field in cluster.__dataclass_fields__},
                    "storage_capacity_bytes": cluster_workload.storage_capacity_bytes,
                }
            )

        namespaces = tuple(
            KubernetesNamespaceCapacity(
                namespace=name,
                pod_count=pod_counts.get(name, 0),
                volume_count=volume_counts.get(name, 0),
                values=namespace_values[name],
            )
            for name in sorted(namespace_values)
        )
        alerts = cls._alerts(snapshot.cluster_key, cluster, namespaces, warning, critical)
        return cls(
            snapshot_id=snapshot.id.value,
            fingerprint=snapshot.fingerprint,
            cluster_key=snapshot.cluster_key,
            cluster_name=snapshot.cluster_name,
            observed_at=snapshot.observed_at,
            warning_threshold_percent=warning,
            critical_threshold_percent=critical,
            cluster=cluster,
            namespaces=namespaces,
            alerts=alerts,
            coverage=coverage,
        )

    @staticmethod
    def _thresholds(warning: float, critical: float) -> tuple[float, float]:
        warning_value = float(warning)
        critical_value = float(critical)
        if not 1.0 <= warning_value < critical_value <= 100.0:
            raise ValidationError("capacity thresholds must satisfy 1 <= warning < critical <= 100")
        return round(warning_value, 2), round(critical_value, 2)

    @classmethod
    def _alerts(
        cls,
        cluster_key: str,
        cluster: KubernetesCapacityValues,
        namespaces: tuple[KubernetesNamespaceCapacity, ...],
        warning: float,
        critical: float,
    ) -> tuple[KubernetesCapacityAlert, ...]:
        alerts: list[KubernetesCapacityAlert] = []
        for resource in ("cpu", "memory", "storage"):
            usage = int(getattr(cluster, f"{resource}_usage_{cls._unit_suffix(resource)}"))
            capacity = int(getattr(cluster, f"{resource}_capacity_{cls._unit_suffix(resource)}"))
            cls._append_alert(
                alerts,
                "cluster",
                cluster_key,
                resource,
                "usage",
                usage,
                capacity,
                warning,
                critical,
            )
            request = int(getattr(cluster, f"{resource}_request_{cls._unit_suffix(resource)}"))
            cls._append_alert(
                alerts,
                "cluster",
                cluster_key,
                resource,
                "requests",
                request,
                capacity,
                warning,
                critical,
            )
        for namespace in namespaces:
            values = namespace.values
            for resource in ("cpu", "memory", "storage"):
                usage = int(getattr(values, f"{resource}_usage_{cls._unit_suffix(resource)}"))
                limit = int(getattr(values, f"{resource}_limit_{cls._unit_suffix(resource)}"))
                cls._append_alert(
                    alerts,
                    "namespace",
                    namespace.namespace,
                    resource,
                    "limit-usage",
                    usage,
                    limit,
                    warning,
                    critical,
                )
        return tuple(
            sorted(
                alerts,
                key=lambda item: (
                    0 if item.severity is KubernetesCapacitySeverity.CRITICAL else 1,
                    item.scope,
                    item.scope_key,
                    item.resource,
                    item.signal,
                ),
            )
        )

    @staticmethod
    def _unit_suffix(resource: str) -> str:
        return "millicores" if resource == "cpu" else "bytes"

    @staticmethod
    def _append_alert(
        alerts: list[KubernetesCapacityAlert],
        scope: str,
        scope_key: str,
        resource: str,
        signal: str,
        numerator: int,
        denominator: int,
        warning: float,
        critical: float,
    ) -> None:
        if denominator <= 0:
            return
        value = round((numerator / denominator) * 100.0, 2)
        if value < warning:
            return
        severity = (
            KubernetesCapacitySeverity.CRITICAL
            if value >= critical
            else KubernetesCapacitySeverity.WARNING
        )
        alerts.append(
            KubernetesCapacityAlert(
                severity=severity,
                scope=scope,
                scope_key=scope_key,
                resource=resource,
                signal=signal,
                value_percent=value,
                threshold_percent=critical
                if severity is KubernetesCapacitySeverity.CRITICAL
                else warning,
            )
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "fingerprint": self.fingerprint,
            "cluster_key": self.cluster_key,
            "cluster_name": self.cluster_name,
            "observed_at": self.observed_at.isoformat(),
            "warning_threshold_percent": self.warning_threshold_percent,
            "critical_threshold_percent": self.critical_threshold_percent,
            "cluster": self.cluster.as_dict(),
            "namespaces": [item.as_dict() for item in self.namespaces],
            "alerts": [item.as_dict() for item in self.alerts],
            "coverage": dict(self.coverage),
        }

    def export(self, format: str) -> tuple[str, str]:
        normalized = format.strip().lower()
        if normalized == "json":
            return "application/json; charset=utf-8", json.dumps(
                self.as_dict(), sort_keys=True, indent=2
            )
        if normalized != "csv":
            raise ValidationError("capacity export format must be json or csv")
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "scope",
                "scope_key",
                "observed_at",
                *KubernetesCapacityValues.__dataclass_fields__.keys(),
            ]
        )
        writer.writerow(
            [
                "cluster",
                self.cluster_key,
                self.observed_at.isoformat(),
                *(getattr(self.cluster, field) for field in self.cluster.__dataclass_fields__),
            ]
        )
        for namespace in self.namespaces:
            writer.writerow(
                [
                    "namespace",
                    namespace.namespace,
                    self.observed_at.isoformat(),
                    *(
                        getattr(namespace.values, field)
                        for field in namespace.values.__dataclass_fields__
                    ),
                ]
            )
        return "text/csv; charset=utf-8", output.getvalue()


@dataclass(frozen=True, slots=True)
class KubernetesCapacityTrendPoint:
    snapshot_id: str
    observed_at: datetime
    resource_count: int
    cluster: KubernetesCapacityValues
    alert_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "observed_at": self.observed_at.isoformat(),
            "resource_count": self.resource_count,
            "cluster": self.cluster.as_dict(),
            "alert_count": self.alert_count,
        }


@dataclass(frozen=True, slots=True)
class KubernetesCapacityTrendReport:
    cluster_key: str
    points: tuple[KubernetesCapacityTrendPoint, ...]
    snapshots_evaluated: int
    resources_scanned: int
    truncated: bool

    @classmethod
    def build(
        cls,
        cluster_key: str,
        snapshots: Iterable[KubernetesTopologySnapshot],
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 90.0,
        max_resources: int = 1_000_000,
    ) -> KubernetesCapacityTrendReport:
        if not 1 <= max_resources <= 1_000_000:
            raise ValidationError("capacity trend max_resources must be between 1 and 1000000")
        reports: list[tuple[KubernetesTopologySnapshot, KubernetesCapacityReport]] = []
        scanned = 0
        truncated = False
        for snapshot in snapshots:
            if scanned + len(snapshot.resources) > max_resources:
                truncated = True
                break
            scanned += len(snapshot.resources)
            reports.append(
                (
                    snapshot,
                    KubernetesCapacityReport.build(
                        snapshot, warning_threshold_percent, critical_threshold_percent
                    ),
                )
            )
        reports.sort(key=lambda item: (item[0].observed_at, item[0].id.value))
        return cls(
            cluster_key=cluster_key,
            points=tuple(
                KubernetesCapacityTrendPoint(
                    snapshot_id=snapshot.id.value,
                    observed_at=snapshot.observed_at,
                    resource_count=len(snapshot.resources),
                    cluster=report.cluster,
                    alert_count=len(report.alerts),
                )
                for snapshot, report in reports
            ),
            snapshots_evaluated=len(reports),
            resources_scanned=scanned,
            truncated=truncated,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "cluster_key": self.cluster_key,
            "points": [point.as_dict() for point in self.points],
            "snapshots_evaluated": self.snapshots_evaluated,
            "resources_scanned": self.resources_scanned,
            "truncated": self.truncated,
        }
