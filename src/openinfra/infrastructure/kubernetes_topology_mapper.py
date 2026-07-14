from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.kubernetes_topology import (
    KubernetesResource,
    KubernetesTopologySnapshot,
)


class KubernetesTopologyRecordMapper:
    @staticmethod
    def _datetime(value: object, field: str) -> datetime:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError(f"invalid Kubernetes topology datetime: {field}") from exc

    @classmethod
    def snapshot(cls, value: dict[str, Any]) -> KubernetesTopologySnapshot:
        raw_resources = value.get("resources")
        if not isinstance(raw_resources, list):
            raise ValidationError("Kubernetes topology resources must be an array")
        resources: list[KubernetesResource] = []
        for raw in raw_resources:
            if not isinstance(raw, dict):
                raise ValidationError("Kubernetes topology resource must be a JSON object")
            resources.append(KubernetesResource.from_dict(cast(dict[str, Any], raw)))
        return KubernetesTopologySnapshot.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            cluster_key=str(value["cluster_key"]),
            cluster_name=str(value["cluster_name"]),
            provider=str(value["provider"]),
            kubernetes_version=str(value["kubernetes_version"]),
            region=None if value.get("region") is None else str(value["region"]),
            site_code=None if value.get("site_code") is None else str(value["site_code"]),
            source_ref=str(value["source_ref"]),
            observed_at=cls._datetime(value["observed_at"], "observed_at"),
            imported_at=cls._datetime(value["imported_at"], "imported_at"),
            resources=tuple(resources),
            fingerprint=str(value["fingerprint"]),
        )
