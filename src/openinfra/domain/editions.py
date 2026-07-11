from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from openinfra.domain.common import ValidationError


class OpenInfraEdition(StrEnum):
    LITE = "lite"
    PRO = "pro"
    ENTERPRISE = "enterprise"

    @classmethod
    def from_value(cls, value: str | OpenInfraEdition) -> Self:
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("edition must be one of: lite, pro, enterprise") from exc


class FeatureCapability(StrEnum):
    CORE_RSOT = "core_rsot"
    CORE_IT_RESOURCES_MANAGEMENT = "core_rsot"
    CORE_RESSOURCES_INVENTORY = "core_rsot"
    CORE_SOURCE_OF_TRUTH = "core_rsot"
    DCIM = "dcim"
    IPAM = "ipam"
    RBAC = "rbac"
    AUDIT = "audit"
    IMPORT_EXPORT = "import_export"
    CENTRALIZED_MULTISITE = "centralized_multisite"
    MULTISITE_DISASTER_RECOVERY = "multisite_disaster_recovery"
    DISTRIBUTED_DISCOVERY_AGENTS = "distributed_discovery_agents"
    INSTALLER_AGENT_SCOPE = "installer_agent_scope"

    @classmethod
    def from_value(cls, value: str | FeatureCapability) -> Self:
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower().replace("-", "_")
        aliases = {
            "core_rsot": "core_rsot",
            "core_source_of_truth": "core_rsot",
            "core_ressources_inventory": "core_rsot",
            "core_resources_inventory": "core_rsot",
            "core_sot": "core_rsot",
            "core_ri": "core_rsot",
        }
        normalized = aliases.get(normalized, normalized)
        try:
            return cls(normalized)
        except ValueError as exc:
            supported = ", ".join(item.value for item in cls)
            raise ValidationError(
                f"unsupported feature capability: {value}. Supported: {supported}"
            ) from exc


class QuotaResource(StrEnum):
    EQUIPMENT = "equipment"
    SUBNET_VLAN = "subnet_vlan"
    IP_DNS_RECORD = "ip_dns_record"
    USER = "user"
    DISCOVERY_COLLECTOR = "discovery_collector"

    @classmethod
    def from_value(cls, value: str | QuotaResource) -> Self:
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower().replace("-", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            supported = ", ".join(item.value for item in cls)
            raise ValidationError(
                f"unsupported quota resource: {value}. Supported: {supported}"
            ) from exc


@dataclass(frozen=True, slots=True)
class EditionPolicy:
    edition: OpenInfraEdition
    features: frozenset[FeatureCapability]
    quotas: dict[QuotaResource, int | None]

    def supports(self, capability: FeatureCapability) -> bool:
        return capability in self.features

    def quota_for(self, resource: QuotaResource) -> int | None:
        return self.quotas.get(resource)

    def as_dict(self) -> dict[str, object]:
        return {
            "edition": self.edition.value,
            "features": sorted(feature.value for feature in self.features),
            "quotas": {
                resource.value: ("unlimited" if value is None else value)
                for resource, value in sorted(self.quotas.items(), key=lambda item: item[0].value)
            },
        }


@dataclass(frozen=True, slots=True)
class FeatureGateDecision:
    edition: OpenInfraEdition
    capability: FeatureCapability
    allowed: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "edition": self.edition.value,
            "capability": self.capability.value,
            "allowed": self.allowed,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class QuotaDecision:
    edition: OpenInfraEdition
    resource: QuotaResource
    used: int
    requested_increment: int
    limit: int | None

    @property
    def allowed(self) -> bool:
        if self.limit is None:
            return True
        return self.used + self.requested_increment <= self.limit

    @property
    def remaining(self) -> int | None:
        if self.limit is None:
            return None
        return max(self.limit - self.used, 0)

    def as_dict(self) -> dict[str, object]:
        return {
            "edition": self.edition.value,
            "resource": self.resource.value,
            "used": self.used,
            "requested_increment": self.requested_increment,
            "limit": "unlimited" if self.limit is None else self.limit,
            "remaining": "unlimited" if self.remaining is None else self.remaining,
            "allowed": self.allowed,
        }


class EditionPolicyCatalog:
    def __init__(self) -> None:
        shared = frozenset(
            {
                FeatureCapability.CORE_RSOT,
                FeatureCapability.DCIM,
                FeatureCapability.IPAM,
                FeatureCapability.RBAC,
                FeatureCapability.AUDIT,
                FeatureCapability.IMPORT_EXPORT,
            }
        )
        self._policies = {
            OpenInfraEdition.LITE: EditionPolicy(
                edition=OpenInfraEdition.LITE,
                features=shared,
                quotas={
                    QuotaResource.EQUIPMENT: 200,
                    QuotaResource.SUBNET_VLAN: 20,
                    QuotaResource.IP_DNS_RECORD: 200,
                    QuotaResource.USER: 5,
                    QuotaResource.DISCOVERY_COLLECTOR: 0,
                },
            ),
            OpenInfraEdition.PRO: EditionPolicy(
                edition=OpenInfraEdition.PRO,
                features=shared
                | frozenset(
                    {
                        FeatureCapability.CENTRALIZED_MULTISITE,
                        FeatureCapability.MULTISITE_DISASTER_RECOVERY,
                    }
                ),
                quotas={
                    QuotaResource.EQUIPMENT: 5_000,
                    QuotaResource.SUBNET_VLAN: 100,
                    QuotaResource.IP_DNS_RECORD: 5_000,
                    QuotaResource.USER: 100,
                    QuotaResource.DISCOVERY_COLLECTOR: 0,
                },
            ),
            OpenInfraEdition.ENTERPRISE: EditionPolicy(
                edition=OpenInfraEdition.ENTERPRISE,
                features=shared
                | frozenset(
                    {
                        FeatureCapability.CENTRALIZED_MULTISITE,
                        FeatureCapability.MULTISITE_DISASTER_RECOVERY,
                        FeatureCapability.DISTRIBUTED_DISCOVERY_AGENTS,
                        FeatureCapability.INSTALLER_AGENT_SCOPE,
                    }
                ),
                quotas=dict.fromkeys(QuotaResource, None),
            ),
        }

    def policy_for(self, edition: str | OpenInfraEdition) -> EditionPolicy:
        normalized = OpenInfraEdition.from_value(edition)
        return self._policies[normalized]

    def all_policies(self) -> tuple[EditionPolicy, ...]:
        return tuple(self._policies[edition] for edition in OpenInfraEdition)
