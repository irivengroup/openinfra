from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self
from urllib.parse import urlparse

from openinfra.domain.common import TenantId, ValidationError


class ExternalItsmProvider(StrEnum):
    SERVICENOW = "servicenow"

    @classmethod
    def from_value(cls, value: str | ExternalItsmProvider) -> Self:
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"service-now": "servicenow", "snow": "servicenow"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("external ITSM provider must be one of: servicenow") from exc


class ExternalItsmSyncDirection(StrEnum):
    PUSH_CI = "push_ci"
    ENRICH_EXTERNAL_TICKET = "enrich_external_ticket"
    LINK_EXTERNAL_TICKET = "link_external_ticket"

    @classmethod
    def from_value(cls, value: str | ExternalItsmSyncDirection) -> Self:
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower().replace("-", "_")
        try:
            return cls(normalized)
        except ValueError as exc:
            supported = ", ".join(item.value for item in cls)
            raise ValidationError(
                f"external ITSM sync direction must be one of: {supported}"
            ) from exc


@dataclass(frozen=True, slots=True)
class ExternalItsmConnectorPolicy:
    provider: ExternalItsmProvider
    editions: tuple[str, ...]
    supported_directions: tuple[ExternalItsmSyncDirection, ...]
    native_ticketing_enabled: bool
    required_secret_refs: tuple[str, ...]
    required_ci_fields: tuple[str, ...]

    @classmethod
    def servicenow(cls) -> Self:
        return cls(
            provider=ExternalItsmProvider.SERVICENOW,
            editions=("pro", "enterprise"),
            supported_directions=(
                ExternalItsmSyncDirection.PUSH_CI,
                ExternalItsmSyncDirection.ENRICH_EXTERNAL_TICKET,
                ExternalItsmSyncDirection.LINK_EXTERNAL_TICKET,
            ),
            native_ticketing_enabled=False,
            required_secret_refs=(
                "OPENINFRA_SERVICENOW_CLIENT_ID_REF",
                "OPENINFRA_SERVICENOW_SECRET_REF",
            ),
            required_ci_fields=(
                "resource_key",
                "display_name",
                "resource_type",
                "lifecycle",
                "source",
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "editions": list(self.editions),
            "supported_directions": [direction.value for direction in self.supported_directions],
            "native_ticketing_enabled": self.native_ticketing_enabled,
            "required_secret_refs": list(self.required_secret_refs),
            "required_ci_fields": list(self.required_ci_fields),
        }


@dataclass(frozen=True, slots=True)
class ExternalItsmConnectorProfile:
    tenant_id: TenantId
    provider: ExternalItsmProvider
    instance_url: str
    table_name: str
    auth_secret_ref: str
    enabled: bool

    @classmethod
    def create(
        cls,
        tenant_id: str | TenantId,
        provider: str | ExternalItsmProvider,
        instance_url: str,
        table_name: str,
        auth_secret_ref: str,
        enabled: bool = True,
    ) -> Self:
        normalized_tenant = (
            tenant_id if isinstance(tenant_id, TenantId) else TenantId.from_value(tenant_id)
        )
        normalized_provider = ExternalItsmProvider.from_value(provider)
        normalized_url = cls._normalize_instance_url(instance_url)
        normalized_table = cls._normalize_table_name(table_name)
        normalized_secret_ref = cls._normalize_secret_ref(auth_secret_ref)
        return cls(
            tenant_id=normalized_tenant,
            provider=normalized_provider,
            instance_url=normalized_url,
            table_name=normalized_table,
            auth_secret_ref=normalized_secret_ref,
            enabled=bool(enabled),
        )

    @staticmethod
    def _normalize_instance_url(value: str) -> str:
        normalized = value.strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValidationError("ServiceNow instance URL must be an absolute HTTPS URL")
        if parsed.username or parsed.password:
            raise ValidationError("ServiceNow instance URL must not embed credentials")
        return normalized

    @staticmethod
    def _normalize_table_name(value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"cmdb_ci", "cmdb_ci_server", "cmdb_ci_netgear", "cmdb_ci_computer"}
        if normalized not in allowed:
            raise ValidationError(
                "ServiceNow CI table must be one of: " + ", ".join(sorted(allowed))
            )
        return normalized

    @staticmethod
    def _normalize_secret_ref(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValidationError("ServiceNow auth secret reference cannot be empty")
        if any(token in normalized.lower() for token in ("password=", "secret=", "token=")):
            raise ValidationError(
                "ServiceNow auth secret reference must not contain secret material"
            )
        return normalized

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "provider": self.provider.value,
            "instance_url": self.instance_url,
            "table_name": self.table_name,
            "auth_secret_ref": self.auth_secret_ref,
            "enabled": self.enabled,
            "native_ticketing_enabled": False,
        }


@dataclass(frozen=True, slots=True)
class ExternalItsmCiSyncPlan:
    tenant_id: TenantId
    provider: ExternalItsmProvider
    direction: ExternalItsmSyncDirection
    resource_key: str
    target_table: str
    mapping: dict[str, str]
    actions: tuple[str, ...]
    safe_to_apply: bool

    @classmethod
    def create(
        cls,
        tenant_id: str | TenantId,
        provider: str | ExternalItsmProvider,
        direction: str | ExternalItsmSyncDirection,
        resource_key: str,
        target_table: str,
        mapping: dict[str, str],
    ) -> Self:
        normalized_tenant = (
            tenant_id if isinstance(tenant_id, TenantId) else TenantId.from_value(tenant_id)
        )
        normalized_provider = ExternalItsmProvider.from_value(provider)
        normalized_direction = ExternalItsmSyncDirection.from_value(direction)
        normalized_resource_key = " ".join(resource_key.strip().split())
        if not 3 <= len(normalized_resource_key) <= 128:
            raise ValidationError("resource key must contain 3 to 128 characters")
        normalized_table = ExternalItsmConnectorProfile._normalize_table_name(target_table)
        normalized_mapping = cls._normalize_mapping(mapping)
        actions = cls._actions_for(normalized_direction)
        return cls(
            tenant_id=normalized_tenant,
            provider=normalized_provider,
            direction=normalized_direction,
            resource_key=normalized_resource_key,
            target_table=normalized_table,
            mapping=normalized_mapping,
            actions=actions,
            safe_to_apply=True,
        )

    @staticmethod
    def _normalize_mapping(mapping: dict[str, str]) -> dict[str, str]:
        if not mapping:
            raise ValidationError("ServiceNow CI mapping cannot be empty")
        normalized: dict[str, str] = {}
        for source_field, target_field in mapping.items():
            source = source_field.strip().lower()
            target = target_field.strip().lower()
            if not source or not target:
                raise ValidationError("ServiceNow CI mapping fields cannot be empty")
            if not source.replace("_", "").isalnum() or not target.replace("_", "").isalnum():
                raise ValidationError(
                    "ServiceNow CI mapping fields must use safe field identifiers"
                )
            normalized[source] = target
        required = {"resource_key", "display_name", "resource_type"}
        missing = sorted(required - set(normalized))
        if missing:
            raise ValidationError(
                "ServiceNow CI mapping misses required fields: " + ", ".join(missing)
            )
        return dict(sorted(normalized.items()))

    @staticmethod
    def _actions_for(direction: ExternalItsmSyncDirection) -> tuple[str, ...]:
        if direction is ExternalItsmSyncDirection.PUSH_CI:
            return (
                "resolve_rsot_resource",
                "map_ci_payload",
                "upsert_external_ci",
                "audit_external_reference",
            )
        if direction is ExternalItsmSyncDirection.ENRICH_EXTERNAL_TICKET:
            return (
                "resolve_external_ticket_reference",
                "render_openinfra_context",
                "patch_external_ticket_notes",
            )
        return (
            "resolve_external_ticket_reference",
            "create_openinfra_external_link",
            "audit_external_link",
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "provider": self.provider.value,
            "direction": self.direction.value,
            "resource_key": self.resource_key,
            "target_table": self.target_table,
            "mapping": self.mapping,
            "actions": list(self.actions),
            "safe_to_apply": self.safe_to_apply,
            "native_ticketing_enabled": False,
        }
