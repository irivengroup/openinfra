from __future__ import annotations

from datetime import datetime
from typing import Any

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.kubernetes_gitops import (
    KubernetesGitOpsPolicy,
    KubernetesGitOpsResource,
    KubernetesGitOpsState,
)


class KubernetesGitOpsRecordMapper:
    @classmethod
    def state(cls, value: dict[str, Any]) -> KubernetesGitOpsState:
        raw_resources = value.get("resources") or []
        raw_policy = value.get("policy") or {}
        if not isinstance(raw_resources, list):
            raise ValidationError("stored GitOps resources must be a JSON array")
        if not isinstance(raw_policy, dict):
            raise ValidationError("stored GitOps policy must be a JSON object")
        resources: list[KubernetesGitOpsResource] = []
        for item in raw_resources:
            if not isinstance(item, dict):
                raise ValidationError("stored GitOps resource must be a JSON object")
            resources.append(KubernetesGitOpsResource.from_dict(dict(item)))
        return KubernetesGitOpsState.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            cluster_key=str(value["cluster_key"]),
            repository_ref=str(value["repository_ref"]),
            revision=str(value["revision"]),
            source_path=str(value["source_path"]),
            owner=str(value["owner"]),
            environment=str(value["environment"]),
            captured_at=datetime.fromisoformat(str(value["captured_at"])),
            imported_at=datetime.fromisoformat(str(value["imported_at"])),
            policy=KubernetesGitOpsPolicy.from_dict(dict(raw_policy)),
            resources=tuple(resources),
            fingerprint=str(value["fingerprint"]),
        )
