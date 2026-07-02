from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import EntityId, TenantId, ValidationError


class DiscoverySource(StrEnum):
    SNMP = "snmp"
    SSH = "ssh"
    VMWARE = "vmware"
    CLOUD = "cloud"
    KUBERNETES = "kubernetes"
    IMPORT = "import"


@dataclass(frozen=True, slots=True)
class DiscoveryEvidence:
    id: EntityId
    tenant_id: TenantId
    source: DiscoverySource
    external_id: str
    confidence: float
    observed_at: datetime
    payload: dict[str, Any]

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        source: DiscoverySource,
        external_id: str,
        confidence: float,
        payload: dict[str, Any],
    ) -> Self:
        normalized_external_id = external_id.strip()
        if not normalized_external_id:
            raise ValidationError("discovery external id is mandatory")
        if not 0.0 <= confidence <= 1.0:
            raise ValidationError("confidence must be between 0 and 1")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            source=source,
            external_id=normalized_external_id,
            confidence=confidence,
            observed_at=datetime.now(UTC),
            payload=payload,
        )


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    evidence_id: EntityId
    accepted: bool
    reason: str

    @classmethod
    def create(cls, evidence_id: EntityId, accepted: bool, reason: str) -> Self:
        normalized_reason = " ".join(reason.strip().split())
        if not normalized_reason:
            raise ValidationError("reconciliation reason is mandatory")
        return cls(evidence_id=evidence_id, accepted=accepted, reason=normalized_reason)
