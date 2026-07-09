from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self, cast
from urllib.parse import urlparse

from openinfra.domain.common import EntityId, TenantId, ValidationError


class DiscoverySource(StrEnum):
    SNMP = "snmp"
    SSH = "ssh"
    VMWARE = "vmware"
    CLOUD = "cloud"
    KUBERNETES = "kubernetes"
    IMPORT = "import"


class CollectorKind(StrEnum):
    SNMP = "snmp"
    SSH = "ssh"
    WINRM = "winrm"
    VMWARE = "vmware"
    PROXMOX = "proxmox"
    HYPERV = "hyperv"
    KUBERNETES = "kubernetes"
    CLOUD = "cloud"
    SITE_PROXY = "site-proxy"
    NETWORK_PROXY = "network-proxy"
    DATACENTER_PROXY = "datacenter-proxy"
    GENERIC = "generic"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"hyper-v": "hyperv", "k8s": "kubernetes", "dc-proxy": "datacenter-proxy"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("collector kind is unsupported") from exc

    @property
    def is_proxy(self) -> bool:
        return self in {
            CollectorKind.SITE_PROXY,
            CollectorKind.NETWORK_PROXY,
            CollectorKind.DATACENTER_PROXY,
        }


class CollectorStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class DiscoveryScope:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:/-]{1,127}", normalized):
            raise ValidationError("discovery scope must use 2 to 128 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class CollectorIdentity:
    certificate_fingerprint: str
    vault_secret_ref: str | None

    @classmethod
    def create(cls, certificate_fingerprint: str, vault_secret_ref: str | None = None) -> Self:
        fingerprint = cls._normalize_fingerprint(certificate_fingerprint)
        secret_ref = cls._normalize_secret_ref(vault_secret_ref)
        return cls(certificate_fingerprint=fingerprint, vault_secret_ref=secret_ref)

    @staticmethod
    def _normalize_fingerprint(value: str) -> str:
        normalized = value.strip().lower().replace(":", "")
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValidationError("collector certificate fingerprint must be a SHA-256 hex digest")
        return normalized

    @staticmethod
    def _normalize_secret_ref(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            return None
        if not re.fullmatch(r"vault://[A-Za-z0-9][A-Za-z0-9_./:-]{2,255}", normalized):
            raise ValidationError("collector secret reference must use vault:// safe syntax")
        if ".." in normalized or "//" in normalized.removeprefix("vault://"):
            raise ValidationError("collector secret reference is unsafe")
        return normalized

    def as_dict(self) -> dict[str, object]:
        return {
            "certificate_fingerprint": self.certificate_fingerprint,
            "vault_secret_ref": self.vault_secret_ref,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryCollector:
    id: EntityId
    tenant_id: TenantId
    name: str
    kind: CollectorKind
    identity: CollectorIdentity
    scopes: tuple[DiscoveryScope, ...]
    version: str
    endpoint_url: str | None
    status: CollectorStatus
    registered_by: str
    registered_at: datetime
    last_heartbeat_at: datetime | None
    last_heartbeat_status: str | None
    last_seen_version: str | None
    disabled_reason: str | None

    @classmethod
    def register(
        cls,
        tenant_id: TenantId,
        name: str,
        kind: CollectorKind,
        identity: CollectorIdentity,
        scopes: tuple[DiscoveryScope, ...],
        version: str,
        registered_by: str,
        endpoint_url: str | None = None,
        collector_id: EntityId | None = None,
        registered_at: datetime | None = None,
    ) -> Self:
        normalized_name = " ".join(name.strip().split())
        if not 2 <= len(normalized_name) <= 128:
            raise ValidationError("collector name must contain 2 to 128 characters")
        if not scopes:
            raise ValidationError("collector must declare at least one scope")
        normalized_version = cls._normalize_version(version)
        actor = " ".join(registered_by.strip().split())
        if not actor:
            raise ValidationError("collector registered_by is mandatory")
        endpoint = cls._normalize_endpoint(endpoint_url)
        created = registered_at or datetime.now(UTC)
        if created.tzinfo is None:
            raise ValidationError("collector registered_at must be timezone-aware")
        return cls(
            id=collector_id or EntityId.new(),
            tenant_id=tenant_id,
            name=normalized_name,
            kind=kind,
            identity=identity,
            scopes=tuple(dict.fromkeys(scopes)),
            version=normalized_version,
            endpoint_url=endpoint,
            status=CollectorStatus.ACTIVE,
            registered_by=actor,
            registered_at=created.astimezone(UTC),
            last_heartbeat_at=None,
            last_heartbeat_status=None,
            last_seen_version=None,
            disabled_reason=None,
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        heartbeat_value = value.get("last_heartbeat_at")
        scopes_value = value.get("scopes", ())
        scopes_iterable = cast(Iterable[object], scopes_value)
        return cls(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            name=str(value["name"]),
            kind=CollectorKind.from_value(str(value["kind"])),
            identity=CollectorIdentity.create(
                str(value["certificate_fingerprint"]),
                None if value.get("vault_secret_ref") is None else str(value["vault_secret_ref"]),
            ),
            scopes=tuple(DiscoveryScope.from_value(str(item)) for item in scopes_iterable),
            version=cls._normalize_version(str(value["version"])),
            endpoint_url=cls._normalize_endpoint(
                None if value.get("endpoint_url") is None else str(value["endpoint_url"])
            ),
            status=CollectorStatus(str(value.get("status", "active"))),
            registered_by=str(value["registered_by"]),
            registered_at=datetime.fromisoformat(str(value["registered_at"])).astimezone(UTC),
            last_heartbeat_at=(
                None
                if heartbeat_value is None
                else datetime.fromisoformat(str(heartbeat_value)).astimezone(UTC)
            ),
            last_heartbeat_status=(
                None
                if value.get("last_heartbeat_status") is None
                else str(value["last_heartbeat_status"])
            ),
            last_seen_version=(
                None if value.get("last_seen_version") is None else str(value["last_seen_version"])
            ),
            disabled_reason=(
                None if value.get("disabled_reason") is None else str(value["disabled_reason"])
            ),
        )

    def record_heartbeat(self, certificate_fingerprint: str, version: str, status: str) -> Self:
        if (
            CollectorIdentity._normalize_fingerprint(certificate_fingerprint)
            != self.identity.certificate_fingerprint
        ):
            raise ValidationError("collector fingerprint does not match registered identity")
        normalized_status = self._normalize_heartbeat_status(status)
        normalized_version = self._normalize_version(version)
        next_status = (
            CollectorStatus.ACTIVE if self.status is not CollectorStatus.DISABLED else self.status
        )
        return self._copy(
            status=next_status,
            last_heartbeat_at=datetime.now(UTC),
            last_heartbeat_status=normalized_status,
            last_seen_version=normalized_version,
        )

    def disable(self, reason: str) -> Self:
        normalized_reason = " ".join(reason.strip().split())
        if not normalized_reason:
            raise ValidationError("collector disable reason is mandatory")
        return self._copy(status=CollectorStatus.DISABLED, disabled_reason=normalized_reason[:512])

    def allows_scope(self, requested_scope: DiscoveryScope) -> bool:
        return requested_scope in self.scopes

    def has_identity(self, certificate_fingerprint: str) -> bool:
        return (
            CollectorIdentity._normalize_fingerprint(certificate_fingerprint)
            == self.identity.certificate_fingerprint
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "kind": self.kind.value,
            "certificate_fingerprint": self.identity.certificate_fingerprint,
            "vault_secret_ref": self.identity.vault_secret_ref,
            "scopes": [scope.value for scope in self.scopes],
            "version": self.version,
            "endpoint_url": self.endpoint_url,
            "status": self.status.value,
            "registered_by": self.registered_by,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat_at": None
            if self.last_heartbeat_at is None
            else self.last_heartbeat_at.isoformat(),
            "last_heartbeat_status": self.last_heartbeat_status,
            "last_seen_version": self.last_seen_version,
            "disabled_reason": self.disabled_reason,
        }

    @staticmethod
    def _normalize_version(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,63}", normalized):
            raise ValidationError("collector version is invalid")
        return normalized

    @staticmethod
    def _normalize_endpoint(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            return None
        if not re.fullmatch(r"https://[A-Za-z0-9][A-Za-z0-9_.:/-]{2,255}", normalized):
            raise ValidationError("collector endpoint URL must be an HTTPS URL")
        return normalized

    @staticmethod
    def _normalize_heartbeat_status(value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"ok", "degraded", "maintenance"}:
            raise ValidationError("collector heartbeat status must be ok, degraded or maintenance")
        return normalized

    def _copy(self, **changes: object) -> Self:
        payload = self.as_dict()
        payload.update(changes)
        if "status" in payload and isinstance(payload["status"], CollectorStatus):
            payload["status"] = payload["status"].value
        if "last_heartbeat_at" in payload and isinstance(payload["last_heartbeat_at"], datetime):
            payload["last_heartbeat_at"] = payload["last_heartbeat_at"].isoformat()
        return self.from_dict(payload)


@dataclass(frozen=True, slots=True)
class DiscoveryJobAuthorization:
    tenant_id: TenantId
    collector_id: EntityId
    authorized: bool
    requested_scope: DiscoveryScope
    job_type: str
    target: str
    reasons: tuple[str, ...]
    authorized_at: datetime

    @classmethod
    def decide(
        cls,
        tenant_id: TenantId,
        collector: DiscoveryCollector | None,
        collector_id: str,
        certificate_fingerprint: str,
        requested_scope: str,
        job_type: str,
        target: str,
    ) -> Self:
        entity_id = EntityId.from_value(collector_id)
        scope = DiscoveryScope.from_value(requested_scope)
        normalized_job_type = cls._normalize_job_type(job_type)
        normalized_target = cls._normalize_target(target)
        reasons: list[str] = []
        if collector is None:
            reasons.append("collector_not_registered")
        else:
            if collector.status is not CollectorStatus.ACTIVE:
                reasons.append("collector_not_active")
            try:
                if not collector.has_identity(certificate_fingerprint):
                    reasons.append("fingerprint_mismatch")
            except ValidationError:
                reasons.append("fingerprint_invalid")
            if not collector.allows_scope(scope):
                reasons.append("scope_not_authorized")
        authorized = not reasons
        return cls(
            tenant_id=tenant_id,
            collector_id=entity_id,
            authorized=authorized,
            requested_scope=scope,
            job_type=normalized_job_type,
            target=normalized_target,
            reasons=tuple(reasons),
            authorized_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "collector_id": self.collector_id.value,
            "authorized": self.authorized,
            "requested_scope": self.requested_scope.value,
            "job_type": self.job_type,
            "target": self.target,
            "reasons": list(self.reasons),
            "authorized_at": self.authorized_at.isoformat(),
        }

    @staticmethod
    def _normalize_job_type(value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9.-]{1,63}", normalized):
            raise ValidationError("discovery job type is invalid")
        return normalized

    @staticmethod
    def _normalize_target(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 255:
            raise ValidationError("discovery target must contain 1 to 255 characters")
        return normalized


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


class EnterpriseAgentRole(StrEnum):
    SITE = "site"
    REGIONAL = "regional"
    DATACENTER = "datacenter"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"region": "regional", "dc": "datacenter", "data-center": "datacenter"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError(
                "enterprise agent role must be site, regional or datacenter"
            ) from exc


@dataclass(frozen=True, slots=True)
class EnterpriseAgentBootstrapPlan:
    id: EntityId
    tenant_id: TenantId
    edition: str
    name: str
    role: EnterpriseAgentRole
    scopes: tuple[DiscoveryScope, ...]
    backend_url: str
    certificate_fingerprint: str
    enrollment_secret_ref: str
    agent_version: str
    service_user: str
    config_path: str
    state_directory: str
    log_directory: str
    systemd_unit_name: str
    systemd_unit: str
    config_document: dict[str, object]
    mtls_required: bool
    publishes_results_via_api: bool
    install_executed: bool
    secrets_materialized: bool
    safeguards: tuple[str, ...]

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        edition: str,
        name: str,
        role: str,
        scopes: tuple[str, ...],
        backend_url: str,
        certificate_fingerprint: str,
        enrollment_secret_ref: str,
        agent_version: str,
        service_user: str,
        config_path: str,
        state_directory: str,
        log_directory: str,
        created_by: str,
    ) -> Self:
        normalized_edition = edition.strip().lower()
        if normalized_edition != "enterprise":
            raise ValidationError("openinfra-agent bootstrap is available only for enterprise")
        normalized_name = " ".join(name.strip().split())
        if not 2 <= len(normalized_name) <= 128:
            raise ValidationError("enterprise agent name must contain 2 to 128 characters")
        actor = " ".join(created_by.strip().split())
        if not actor:
            raise ValidationError("enterprise agent created_by is mandatory")
        if not scopes:
            raise ValidationError("enterprise agent requires at least one scope")
        normalized_role = EnterpriseAgentRole.from_value(role)
        normalized_scopes = tuple(dict.fromkeys(DiscoveryScope.from_value(item) for item in scopes))
        endpoint = cls._normalize_backend_url(backend_url)
        fingerprint = CollectorIdentity._normalize_fingerprint(certificate_fingerprint)
        secret_ref = CollectorIdentity._normalize_secret_ref(enrollment_secret_ref)
        if secret_ref is None:
            raise ValidationError("enterprise agent enrollment_secret_ref is mandatory")
        version = DiscoveryCollector._normalize_version(agent_version)
        user = cls._normalize_service_user(service_user)
        config = cls._normalize_absolute_path(config_path, "config_path")
        state = cls._normalize_absolute_path(state_directory, "state_directory")
        logs = cls._normalize_absolute_path(log_directory, "log_directory")
        unit = cls._render_systemd_unit(user, config, state, logs)
        config_document: dict[str, object] = {
            "agent": {
                "name": normalized_name,
                "role": normalized_role.value,
                "version": version,
                "service_user": user,
            },
            "tenant_id": tenant_id.value,
            "backend": {
                "url": endpoint,
                "heartbeat_endpoint": "/api/v1/discovery/collectors/heartbeat",
                "job_authorize_endpoint": "/api/v1/discovery/jobs/authorize",
                "result_publish_endpoint": "/api/v1/discovery/results",
            },
            "identity": {
                "certificate_fingerprint": fingerprint,
                "enrollment_secret_ref": secret_ref,
                "mtls_required": True,
            },
            "discovery": {
                "scopes": [scope.value for scope in normalized_scopes],
                "result_publication": "api",
            },
            "runtime": {
                "config_path": config,
                "state_directory": state,
                "log_directory": logs,
            },
        }
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            edition=normalized_edition,
            name=normalized_name,
            role=normalized_role,
            scopes=normalized_scopes,
            backend_url=endpoint,
            certificate_fingerprint=fingerprint,
            enrollment_secret_ref=secret_ref,
            agent_version=version,
            service_user=user,
            config_path=config,
            state_directory=state,
            log_directory=logs,
            systemd_unit_name="openinfra-agent.service",
            systemd_unit=unit,
            config_document=config_document,
            mtls_required=True,
            publishes_results_via_api=True,
            install_executed=False,
            secrets_materialized=False,
            safeguards=(
                "enterprise_only",
                "bootstrap_plan_only",
                "no_install_executed",
                "no_secret_materialization",
                "mtls_required",
                "vault_secret_reference_only",
                "api_result_publication",
                "operator_review_required",
            ),
        )

    @staticmethod
    def _normalize_backend_url(value: str) -> str:
        normalized = value.strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValidationError("enterprise agent backend_url must be an HTTPS origin URL")
        if parsed.username or parsed.password:
            raise ValidationError("enterprise agent backend_url must not embed credentials")
        if parsed.params or parsed.query or parsed.fragment:
            raise ValidationError(
                "enterprise agent backend_url must not contain params, query or fragment"
            )
        if parsed.path not in ("", "/"):
            raise ValidationError("enterprise agent backend_url must be an origin URL without path")
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _normalize_service_user(value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"", "root"}:
            raise ValidationError(
                "enterprise agent service_user must be a dedicated non-root account"
            )
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{1,31}", normalized):
            raise ValidationError("enterprise agent service_user must be a safe Unix account name")
        return normalized

    @staticmethod
    def _normalize_absolute_path(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("/") or "//" in normalized or "/../" in normalized:
            raise ValidationError(f"enterprise agent {field_name} must be a safe absolute path")
        if len(normalized) > 255:
            raise ValidationError(f"enterprise agent {field_name} is too long")
        return normalized.rstrip("/") if normalized != "/" else normalized

    @staticmethod
    def _render_systemd_unit(
        user: str, config_path: str, state_directory: str, log_directory: str
    ) -> str:
        return "\n".join(
            (
                "[Unit]",
                "Description=OpenInfra Enterprise Discovery Agent",
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                f"User={user}",
                f"Group={user}",
                f"ExecStart=/usr/local/bin/openinfra-agent --config {config_path}",
                "Restart=on-failure",
                "RestartSec=5s",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "ProtectSystem=strict",
                "ProtectHome=true",
                f"ReadWritePaths={state_directory} {log_directory}",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
            )
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "edition": self.edition,
            "name": self.name,
            "role": self.role.value,
            "scopes": [scope.value for scope in self.scopes],
            "backend_url": self.backend_url,
            "certificate_fingerprint": self.certificate_fingerprint,
            "enrollment_secret_ref": self.enrollment_secret_ref,
            "agent_version": self.agent_version,
            "service_user": self.service_user,
            "config_path": self.config_path,
            "state_directory": self.state_directory,
            "log_directory": self.log_directory,
            "systemd_unit_name": self.systemd_unit_name,
            "systemd_unit": self.systemd_unit,
            "config_document": self.config_document,
            "mtls_required": self.mtls_required,
            "publishes_results_via_api": self.publishes_results_via_api,
            "install_executed": self.install_executed,
            "secrets_materialized": self.secrets_materialized,
            "safeguards": list(self.safeguards),
        }


class LocalDiscoveryProtocol(StrEnum):
    SNMP = "snmp"
    SSH = "ssh"
    WINRM = "winrm"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("local discovery protocol must be snmp, ssh or winrm") from exc


class DiscoveryProtocolProfileStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"

    @classmethod
    def from_value(cls, value: str | None) -> Self:
        normalized = (value or "active").strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(
                "discovery protocol profile status must be active or disabled"
            ) from exc


@dataclass(frozen=True, slots=True)
class DiscoveryProtocolCredentialProfile:
    id: EntityId
    tenant_id: TenantId
    name: str
    protocol: LocalDiscoveryProtocol
    scope: DiscoveryScope
    credential_secret_ref: str
    port: int
    timeout_seconds: int
    max_concurrency: int
    rate_limit_per_minute: int
    retry_count: int
    status: DiscoveryProtocolProfileStatus
    created_by: str
    created_at: datetime
    disabled_reason: str | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        protocol: str,
        scope: str,
        credential_secret_ref: str,
        port: int | None,
        timeout_seconds: int,
        max_concurrency: int,
        rate_limit_per_minute: int,
        retry_count: int,
        created_by: str,
        profile_id: EntityId | None = None,
        created_at: datetime | None = None,
    ) -> Self:
        normalized_name = cls._normalize_name(name)
        discovery_protocol = LocalDiscoveryProtocol.from_value(protocol)
        discovery_scope = DiscoveryScope.from_value(scope)
        secret_ref = CollectorIdentity._normalize_secret_ref(credential_secret_ref)
        if secret_ref is None:
            raise ValidationError("discovery protocol credential_secret_ref is mandatory")
        normalized_port = cls._normalize_port(discovery_protocol, port)
        normalized_timeout = cls._normalize_timeout(timeout_seconds)
        normalized_max_concurrency = cls._normalize_max_concurrency(max_concurrency)
        normalized_rate_limit = cls._normalize_rate_limit(rate_limit_per_minute)
        normalized_retry_count = cls._normalize_retry_count(retry_count)
        actor = cls._normalize_actor(created_by)
        created = created_at or datetime.now(UTC)
        if created.tzinfo is None:
            raise ValidationError("discovery protocol profile created_at must be timezone-aware")
        return cls(
            id=profile_id or EntityId.new(),
            tenant_id=tenant_id,
            name=normalized_name,
            protocol=discovery_protocol,
            scope=discovery_scope,
            credential_secret_ref=secret_ref,
            port=normalized_port,
            timeout_seconds=normalized_timeout,
            max_concurrency=normalized_max_concurrency,
            rate_limit_per_minute=normalized_rate_limit,
            retry_count=normalized_retry_count,
            status=DiscoveryProtocolProfileStatus.ACTIVE,
            created_by=actor,
            created_at=created.astimezone(UTC),
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        created_value = value.get("created_at")
        return cls(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            name=cls._normalize_name(str(value["name"])),
            protocol=LocalDiscoveryProtocol.from_value(str(value["protocol"])),
            scope=DiscoveryScope.from_value(str(value["scope"])),
            credential_secret_ref=cls._required_secret_ref(value.get("credential_secret_ref")),
            port=cls._normalize_port(
                LocalDiscoveryProtocol.from_value(str(value["protocol"])),
                int(value["port"]),
            ),
            timeout_seconds=cls._normalize_timeout(int(value["timeout_seconds"])),
            max_concurrency=cls._normalize_max_concurrency(int(value["max_concurrency"])),
            rate_limit_per_minute=cls._normalize_rate_limit(int(value["rate_limit_per_minute"])),
            retry_count=cls._normalize_retry_count(int(value["retry_count"])),
            status=DiscoveryProtocolProfileStatus.from_value(str(value.get("status", "active"))),
            created_by=cls._normalize_actor(str(value["created_by"])),
            created_at=(
                datetime.now(UTC)
                if created_value is None
                else datetime.fromisoformat(str(created_value)).astimezone(UTC)
            ),
            disabled_reason=None
            if value.get("disabled_reason") is None
            else str(value["disabled_reason"]),
        )

    def update_settings(
        self,
        *,
        name: str | None = None,
        scope: str | None = None,
        credential_secret_ref: str | None = None,
        port: int | None = None,
        timeout_seconds: int | None = None,
        max_concurrency: int | None = None,
        rate_limit_per_minute: int | None = None,
        retry_count: int | None = None,
    ) -> Self:
        if self.status is not DiscoveryProtocolProfileStatus.ACTIVE:
            raise ValidationError("disabled discovery protocol profile cannot be updated")
        return self._copy(
            name=self.name if name is None else self._normalize_name(name),
            scope=self.scope.value if scope is None else DiscoveryScope.from_value(scope).value,
            credential_secret_ref=self.credential_secret_ref
            if credential_secret_ref is None
            else self._required_secret_ref(credential_secret_ref),
            port=self.port if port is None else self._normalize_port(self.protocol, port),
            timeout_seconds=self.timeout_seconds
            if timeout_seconds is None
            else self._normalize_timeout(timeout_seconds),
            max_concurrency=self.max_concurrency
            if max_concurrency is None
            else self._normalize_max_concurrency(max_concurrency),
            rate_limit_per_minute=self.rate_limit_per_minute
            if rate_limit_per_minute is None
            else self._normalize_rate_limit(rate_limit_per_minute),
            retry_count=self.retry_count
            if retry_count is None
            else self._normalize_retry_count(retry_count),
        )

    def disable(self, reason: str) -> Self:
        normalized_reason = " ".join(reason.strip().split())
        if not normalized_reason:
            raise ValidationError("discovery protocol profile disable reason is mandatory")
        return self._copy(
            status=DiscoveryProtocolProfileStatus.DISABLED.value,
            disabled_reason=normalized_reason[:512],
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "protocol": self.protocol.value,
            "scope": self.scope.value,
            "credential_secret_ref": self.credential_secret_ref,
            "port": self.port,
            "timeout_seconds": self.timeout_seconds,
            "max_concurrency": self.max_concurrency,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "retry_count": self.retry_count,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "disabled_reason": self.disabled_reason,
        }

    def as_public_dict(self) -> dict[str, object]:
        payload = self.as_dict()
        payload["credential_secret_ref"] = self.masked_credential_secret_ref
        payload["secret_materialized"] = False
        payload["rate_limit_active"] = True
        payload["transport"] = self.transport_label
        payload["safeguards"] = [
            "vault_reference_only",
            "secret_material_never_returned",
            "protocol_allowlist",
            "rate_limit_active",
            "bounded_concurrency",
        ]
        return payload

    @property
    def masked_credential_secret_ref(self) -> str:
        return "vault://***"

    @property
    def transport_label(self) -> str:
        if self.protocol is LocalDiscoveryProtocol.SNMP:
            return "snmp-v3-credentials-from-vault"
        if self.protocol is LocalDiscoveryProtocol.SSH:
            return "ssh-key-or-password-from-vault"
        return "winrm-https-credentials-from-vault"

    @staticmethod
    def _normalize_name(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 2 <= len(normalized) <= 128:
            raise ValidationError(
                "discovery protocol profile name must contain 2 to 128 characters"
            )
        return normalized

    @staticmethod
    def _normalize_actor(value: str) -> str:
        actor = " ".join(value.strip().split())
        if not actor:
            raise ValidationError("discovery protocol profile created_by is mandatory")
        return actor

    @staticmethod
    def _required_secret_ref(value: object) -> str:
        secret_ref = CollectorIdentity._normalize_secret_ref(None if value is None else str(value))
        if secret_ref is None:
            raise ValidationError("discovery protocol credential_secret_ref is mandatory")
        return secret_ref

    @staticmethod
    def _default_port(protocol: LocalDiscoveryProtocol) -> int:
        if protocol is LocalDiscoveryProtocol.SNMP:
            return 161
        if protocol is LocalDiscoveryProtocol.SSH:
            return 22
        return 5986

    @classmethod
    def _normalize_port(cls, protocol: LocalDiscoveryProtocol, value: int | None) -> int:
        port = cls._default_port(protocol) if value is None else int(value)
        if not 1 <= port <= 65535:
            raise ValidationError("discovery protocol profile port must be between 1 and 65535")
        if protocol is LocalDiscoveryProtocol.WINRM and port == 5985:
            raise ValidationError("winrm discovery profile must use encrypted HTTPS transport")
        return port

    @staticmethod
    def _normalize_timeout(value: int) -> int:
        timeout = int(value)
        if not 1 <= timeout <= 300:
            raise ValidationError("discovery protocol timeout_seconds must be between 1 and 300")
        return timeout

    @staticmethod
    def _normalize_max_concurrency(value: int) -> int:
        concurrency = int(value)
        if not 1 <= concurrency <= 64:
            raise ValidationError("discovery protocol max_concurrency must be between 1 and 64")
        return concurrency

    @staticmethod
    def _normalize_rate_limit(value: int) -> int:
        rate_limit = int(value)
        if not 1 <= rate_limit <= 10_000:
            raise ValidationError(
                "discovery protocol rate_limit_per_minute must be between 1 and 10000"
            )
        return rate_limit

    @staticmethod
    def _normalize_retry_count(value: int) -> int:
        retry_count = int(value)
        if not 0 <= retry_count <= 5:
            raise ValidationError("discovery protocol retry_count must be between 0 and 5")
        return retry_count

    def _copy(self, **changes: object) -> Self:
        payload = self.as_dict()
        payload.update(changes)
        return self.from_dict(payload)


@dataclass(frozen=True, slots=True)
class LocalDiscoveryTarget:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if "://" in normalized or "@" in normalized:
            raise ValidationError(
                "local discovery target must not contain URL credentials or scheme"
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:/-]{1,127}", normalized):
            raise ValidationError("local discovery target must use 2 to 128 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class LocalDiscoveryJobPlan:
    target: LocalDiscoveryTarget
    protocol: LocalDiscoveryProtocol
    scope: DiscoveryScope
    credential_secret_ref: str
    operation: str
    planned_status: str
    protocol_profile_id: str | None = None

    @classmethod
    def create(
        cls,
        target: LocalDiscoveryTarget,
        protocol: LocalDiscoveryProtocol,
        scope: DiscoveryScope,
        credential_secret_ref: str,
        protocol_profile_id: str | None = None,
    ) -> Self:
        secret_ref = CollectorIdentity._normalize_secret_ref(credential_secret_ref)
        if secret_ref is None:
            raise ValidationError("local discovery credential_secret_ref is mandatory")
        return cls(
            target=target,
            protocol=protocol,
            scope=scope,
            credential_secret_ref=secret_ref,
            operation=f"{protocol.value}-inventory-plan",
            planned_status="planned",
            protocol_profile_id=protocol_profile_id,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "target": self.target.value,
            "protocol": self.protocol.value,
            "scope": self.scope.value,
            "credential_secret_ref": self.credential_secret_ref,
            "operation": self.operation,
            "planned_status": self.planned_status,
            "protocol_profile_id": self.protocol_profile_id,
        }


@dataclass(frozen=True, slots=True)
class LocalDiscoveryPlan:
    id: EntityId
    tenant_id: TenantId
    edition: str
    name: str
    scope: DiscoveryScope
    protocol: LocalDiscoveryProtocol
    jobs: tuple[LocalDiscoveryJobPlan, ...]
    max_concurrency: int
    rate_limit_per_minute: int
    created_by: str
    created_at: datetime
    dry_run: bool
    agent_required: bool
    network_scan_executed: bool
    rsot_write_enabled: bool
    safeguards: tuple[str, ...]
    protocol_profile_id: str | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        edition: str,
        name: str,
        scope: str,
        protocol: str,
        targets: tuple[str, ...],
        credential_secret_ref: str,
        max_concurrency: int,
        rate_limit_per_minute: int,
        created_by: str,
        protocol_profile_id: str | None = None,
    ) -> Self:
        normalized_edition = edition.strip().lower()
        if normalized_edition not in {"lite", "pro"}:
            raise ValidationError(
                "local discovery without agent is available only for lite and pro"
            )
        normalized_name = " ".join(name.strip().split())
        if not 2 <= len(normalized_name) <= 128:
            raise ValidationError("local discovery plan name must contain 2 to 128 characters")
        if not targets:
            raise ValidationError("local discovery plan requires at least one target")
        if not 1 <= max_concurrency <= 32:
            raise ValidationError("local discovery max_concurrency must be between 1 and 32")
        if not 1 <= rate_limit_per_minute <= 10_000:
            raise ValidationError(
                "local discovery rate_limit_per_minute must be between 1 and 10000"
            )
        actor = " ".join(created_by.strip().split())
        if not actor:
            raise ValidationError("local discovery created_by is mandatory")
        discovery_scope = DiscoveryScope.from_value(scope)
        discovery_protocol = LocalDiscoveryProtocol.from_value(protocol)
        normalized_targets = tuple(
            dict.fromkeys(LocalDiscoveryTarget.from_value(item) for item in targets)
        )
        jobs = tuple(
            LocalDiscoveryJobPlan.create(
                target=target,
                protocol=discovery_protocol,
                scope=discovery_scope,
                credential_secret_ref=credential_secret_ref,
                protocol_profile_id=protocol_profile_id,
            )
            for target in normalized_targets
        )
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            edition=normalized_edition,
            name=normalized_name,
            scope=discovery_scope,
            protocol=discovery_protocol,
            jobs=jobs,
            max_concurrency=max_concurrency,
            rate_limit_per_minute=rate_limit_per_minute,
            created_by=actor,
            created_at=datetime.now(UTC),
            dry_run=True,
            agent_required=False,
            network_scan_executed=False,
            rsot_write_enabled=False,
            safeguards=(
                "plan_only",
                "dry_run",
                "no_agent_required",
                "no_network_scan_executed",
                "no_rsot_write",
                "vault_secret_reference_only",
                "secret_material_never_returned",
                "rate_limit_active",
                "bounded_concurrency",
                "operator_review_required",
            ),
            protocol_profile_id=protocol_profile_id,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "edition": self.edition,
            "name": self.name,
            "scope": self.scope.value,
            "protocol": self.protocol.value,
            "targets_count": len(self.jobs),
            "max_concurrency": self.max_concurrency,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "dry_run": self.dry_run,
            "agent_required": self.agent_required,
            "network_scan_executed": self.network_scan_executed,
            "rsot_write_enabled": self.rsot_write_enabled,
            "safeguards": list(self.safeguards),
            "protocol_profile_id": self.protocol_profile_id,
            "jobs": [job.as_dict() for job in self.jobs],
        }
