from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self, cast
from urllib.parse import urlparse

from openinfra.domain.common import EntityId, TenantId, ValidationError


class DiscoverySource(StrEnum):
    SNMP = "snmp"
    SSH = "ssh"
    WINRM = "winrm"
    VMWARE = "vmware"
    PROXMOX = "proxmox"
    HYPERV = "hyperv"
    KUBERNETES = "kubernetes"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OPENSTACK = "openstack"
    CLOUD = "cloud"
    IMPORT = "import"
    MANUAL = "manual"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"hyper-v": "hyperv", "k8s": "kubernetes"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("discovery source is unsupported") from exc


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
    object_key: str
    object_kind: str
    scope: DiscoveryScope
    source_ref: str
    received_at: datetime
    payload_hash: str
    completeness: float

    _MAX_PAYLOAD_BYTES = 1_048_576
    _SENSITIVE_KEY_TOKENS = frozenset(
        {
            "accesstoken",
            "apitoken",
            "clientsecret",
            "credential",
            "credentials",
            "password",
            "passwd",
            "privatekey",
            "refreshtoken",
            "secret",
            "secrets",
            "token",
            "tokens",
        }
    )

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        source: DiscoverySource,
        external_id: str,
        confidence: float,
        payload: dict[str, Any],
        *,
        object_key: str | None = None,
        object_kind: str = "resource",
        scope: str = "global",
        source_ref: str | None = None,
        observed_at: datetime | None = None,
        evidence_id: EntityId | None = None,
        received_at: datetime | None = None,
    ) -> Self:
        normalized_external_id = cls._normalize_identifier(
            external_id, "discovery external id", 1, 255
        )
        normalized_confidence = cls._normalize_score(confidence, "confidence")
        normalized_payload = cls._normalize_payload(payload)
        observed = observed_at or datetime.now(UTC)
        received = received_at or datetime.now(UTC)
        cls._require_aware(observed, "discovery observed_at")
        cls._require_aware(received, "discovery received_at")
        normalized_key = cls._normalize_object_key(object_key or normalized_external_id)
        normalized_kind = cls._normalize_object_kind(object_kind)
        normalized_source_ref = cls._normalize_identifier(
            source_ref or source.value, "discovery source_ref", 2, 255
        )
        canonical_payload = json.dumps(
            normalized_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return cls(
            id=evidence_id or EntityId.new(),
            tenant_id=tenant_id,
            source=source,
            external_id=normalized_external_id,
            confidence=normalized_confidence,
            observed_at=observed.astimezone(UTC),
            payload=normalized_payload,
            object_key=normalized_key,
            object_kind=normalized_kind,
            scope=DiscoveryScope.from_value(scope),
            source_ref=normalized_source_ref,
            received_at=received.astimezone(UTC),
            payload_hash=hashlib.sha256(canonical_payload).hexdigest(),
            completeness=cls._calculate_completeness(normalized_payload),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        payload_value = value.get("payload", {})
        if not isinstance(payload_value, dict):
            raise ValidationError("stored discovery evidence payload must be an object")
        source = DiscoverySource.from_value(str(value["source"]))
        return cls.create(
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            source=source,
            external_id=str(value["external_id"]),
            confidence=float(str(value["confidence"])),
            payload=cast(dict[str, Any], payload_value),
            object_key=str(value.get("object_key", value["external_id"])),
            object_kind=str(value.get("object_kind", "resource")),
            scope=str(value.get("scope", "global")),
            source_ref=str(value.get("source_ref", source.value)),
            observed_at=datetime.fromisoformat(str(value["observed_at"])),
            evidence_id=EntityId.from_value(str(value["id"])),
            received_at=datetime.fromisoformat(str(value.get("received_at", value["observed_at"]))),
        )

    def quality_scores(self, max_age_seconds: int, now: datetime | None = None) -> dict[str, float]:
        normalized_max_age = self._normalize_max_age(max_age_seconds)
        current = now or datetime.now(UTC)
        self._require_aware(current, "reconciliation evaluation time")
        age_seconds = max(
            0.0,
            (current.astimezone(UTC) - self.observed_at).total_seconds(),
        )
        freshness = max(0.0, 1.0 - (age_seconds / normalized_max_age))
        overall = (0.60 * self.confidence) + (0.25 * freshness) + (0.15 * self.completeness)
        return {
            "confidence": round(self.confidence, 6),
            "freshness": round(freshness, 6),
            "completeness": round(self.completeness, 6),
            "overall": round(overall, 6),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "source": self.source.value,
            "source_ref": self.source_ref,
            "scope": self.scope.value,
            "external_id": self.external_id,
            "object_key": self.object_key,
            "object_kind": self.object_kind,
            "confidence": self.confidence,
            "completeness": self.completeness,
            "observed_at": self.observed_at.isoformat(),
            "received_at": self.received_at.isoformat(),
            "payload_hash": self.payload_hash,
            "payload": self.payload,
            "immutable": True,
        }

    @classmethod
    def _normalize_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValidationError("discovery evidence payload must be a JSON object")
        cls._validate_payload_node(payload, "payload")
        try:
            serialized = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            restored = json.loads(serialized)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("discovery evidence payload must be JSON serializable") from exc
        if len(serialized.encode("utf-8")) > cls._MAX_PAYLOAD_BYTES:
            raise ValidationError("discovery evidence payload exceeds 1 MiB")
        return cast(dict[str, Any], restored)

    @classmethod
    def _validate_payload_node(cls, value: object, path: str) -> None:
        if isinstance(value, dict):
            if len(value) > 1024:
                raise ValidationError("discovery evidence object exceeds 1024 keys")
            for raw_key, child in value.items():
                if not isinstance(raw_key, str):
                    raise ValidationError("discovery evidence keys must be strings")
                key = raw_key.strip()
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_:-]{0,63}", key):
                    raise ValidationError("discovery evidence keys must use safe characters")
                compact_key = re.sub(r"[^a-z0-9]", "", key.lower())
                if compact_key in cls._SENSITIVE_KEY_TOKENS:
                    raise ValidationError(
                        "discovery evidence payload must not contain secret material"
                    )
                cls._validate_payload_node(child, path + "." + key)
            return
        if isinstance(value, list):
            if len(value) > 4096:
                raise ValidationError("discovery evidence list exceeds 4096 items")
            for index, child in enumerate(value):
                cls._validate_payload_node(child, f"{path}[{index}]")
            return
        if value is None or isinstance(value, (str, int, float, bool)):
            return
        raise ValidationError("discovery evidence payload contains an unsupported value")

    @classmethod
    def _calculate_completeness(cls, payload: Mapping[str, Any]) -> float:
        leaves = cls._flatten_payload(payload)
        if not leaves:
            return 0.0
        populated = sum(1 for value in leaves.values() if cls._is_populated(value))
        return round(populated / len(leaves), 6)

    @staticmethod
    def _is_populated(value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return bool(value)
        return True

    @classmethod
    def _flatten_payload(cls, payload: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for key in sorted(payload):
            path = f"{prefix}.{key}" if prefix else key
            value = payload[key]
            if isinstance(value, dict):
                nested = cls._flatten_payload(cast(Mapping[str, Any], value), path)
                if nested:
                    flattened.update(nested)
                else:
                    flattened[path] = {}
            else:
                flattened[path] = value
        return flattened

    @staticmethod
    def _normalize_identifier(value: str, label: str, minimum: int, maximum: int) -> str:
        normalized = " ".join(value.strip().split())
        if not minimum <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain {minimum} to {maximum} characters")
        return normalized

    @staticmethod
    def _normalize_object_key(value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{1,255}", normalized):
            raise ValidationError("discovery object key must use 2 to 256 safe characters")
        return normalized

    @staticmethod
    def _normalize_object_kind(value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9.-]{1,63}", normalized):
            raise ValidationError("discovery object kind must use 2 to 64 safe characters")
        return normalized

    @staticmethod
    def _normalize_score(value: float, label: str) -> float:
        normalized = float(value)
        if not 0.0 <= normalized <= 1.0:
            raise ValidationError(f"{label} must be between 0 and 1")
        return round(normalized, 6)

    @staticmethod
    def _normalize_max_age(value: int) -> int:
        normalized = int(value)
        if normalized < 60 or normalized > 366 * 24 * 60 * 60:
            raise ValidationError("reconciliation max age must be between 60 seconds and 366 days")
        return normalized

    @staticmethod
    def _require_aware(value: datetime, label: str) -> None:
        if value.tzinfo is None:
            raise ValidationError(label + " must be timezone-aware")


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


class DiscoveryReconciliationStatus(StrEnum):
    READY = "ready"
    CONFLICT = "conflict"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class DiscoveryConflictVariant:
    evidence_id: EntityId
    source: DiscoverySource
    source_ref: str
    score: float
    value: Any

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id.value,
            "source": self.source.value,
            "source_ref": self.source_ref,
            "score": self.score,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        return cls(
            evidence_id=EntityId.from_value(str(value["evidence_id"])),
            source=DiscoverySource.from_value(str(value["source"])),
            source_ref=str(value["source_ref"]),
            score=float(str(value["score"])),
            value=value.get("value"),
        )


@dataclass(frozen=True, slots=True)
class DiscoveryReconciliationConflict:
    attribute_path: str
    variants: tuple[DiscoveryConflictVariant, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "attribute_path": self.attribute_path,
            "variants": [variant.as_dict() for variant in self.variants],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        raw_variants = value.get("variants", ())
        if not isinstance(raw_variants, Sequence) or isinstance(
            raw_variants, (str, bytes, bytearray)
        ):
            raise ValidationError("stored reconciliation conflict variants are invalid")
        return cls(
            attribute_path=str(value["attribute_path"]),
            variants=tuple(
                DiscoveryConflictVariant.from_dict(cast(Mapping[str, object], item))
                for item in raw_variants
                if isinstance(item, Mapping)
            ),
        )


@dataclass(frozen=True, slots=True)
class DiscoveryReconciliationResolution:
    actor: str
    justification: str
    selected_evidence_by_path: dict[str, str]
    resolved_at: datetime

    @classmethod
    def create(
        cls,
        actor: str,
        justification: str,
        selected_evidence_by_path: Mapping[str, str],
        resolved_at: datetime | None = None,
    ) -> Self:
        normalized_actor = " ".join(actor.strip().split())
        normalized_justification = " ".join(justification.strip().split())
        if not normalized_actor:
            raise ValidationError("reconciliation resolution actor is mandatory")
        if not 8 <= len(normalized_justification) <= 1024:
            raise ValidationError(
                "reconciliation resolution justification must contain 8 to 1024 characters"
            )
        timestamp = resolved_at or datetime.now(UTC)
        DiscoveryEvidence._require_aware(timestamp, "reconciliation resolved_at")
        return cls(
            actor=normalized_actor,
            justification=normalized_justification,
            selected_evidence_by_path=dict(sorted(selected_evidence_by_path.items())),
            resolved_at=timestamp.astimezone(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor,
            "justification": self.justification,
            "selected_evidence_by_path": dict(self.selected_evidence_by_path),
            "resolved_at": self.resolved_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        raw_selections = value.get("selected_evidence_by_path", {})
        if not isinstance(raw_selections, Mapping):
            raise ValidationError("stored reconciliation selections are invalid")
        return cls.create(
            actor=str(value["actor"]),
            justification=str(value["justification"]),
            selected_evidence_by_path={str(key): str(item) for key, item in raw_selections.items()},
            resolved_at=datetime.fromisoformat(str(value["resolved_at"])),
        )


@dataclass(frozen=True, slots=True)
class DiscoveryReconciliationCase:
    id: EntityId
    tenant_id: TenantId
    object_key: str
    object_kind: str
    evidence_ids: tuple[EntityId, ...]
    source_count: int
    confidence_score: float
    freshness_score: float
    completeness_score: float
    overall_score: float
    status: DiscoveryReconciliationStatus
    conflicts: tuple[DiscoveryReconciliationConflict, ...]
    merged_payload: dict[str, Any]
    evaluated_at: datetime
    evaluated_by: str
    signature: str
    resolution: DiscoveryReconciliationResolution | None
    rsot_write_executed: bool = False

    @classmethod
    def evaluate(
        cls,
        tenant_id: TenantId,
        object_key: str,
        evidences: tuple[DiscoveryEvidence, ...],
        max_age_seconds: int,
        evaluated_by: str,
        *,
        case_id: EntityId | None = None,
        evaluated_at: datetime | None = None,
    ) -> Self:
        normalized_key = DiscoveryEvidence._normalize_object_key(object_key)
        normalized_max_age = DiscoveryEvidence._normalize_max_age(max_age_seconds)
        actor = " ".join(evaluated_by.strip().split())
        if not actor:
            raise ValidationError("reconciliation evaluated_by is mandatory")
        if len(evidences) < 2:
            raise ValidationError("multisource reconciliation requires at least two evidences")
        if any(evidence.tenant_id != tenant_id for evidence in evidences):
            raise ValidationError("reconciliation evidences must belong to the same tenant")
        if any(evidence.object_key != normalized_key for evidence in evidences):
            raise ValidationError("reconciliation evidences must target the same object key")
        kinds = {evidence.object_kind for evidence in evidences}
        if len(kinds) != 1:
            raise ValidationError("reconciliation evidences must target the same object kind")
        source_identities = {(evidence.source.value, evidence.source_ref) for evidence in evidences}
        if len(source_identities) < 2:
            raise ValidationError("multisource reconciliation requires two distinct sources")
        timestamp = evaluated_at or datetime.now(UTC)
        DiscoveryEvidence._require_aware(timestamp, "reconciliation evaluated_at")
        ordered_evidences = tuple(
            sorted(evidences, key=lambda item: (item.source.value, item.source_ref, item.id.value))
        )
        scores_by_id = {
            evidence.id.value: evidence.quality_scores(normalized_max_age, timestamp)
            for evidence in ordered_evidences
        }
        payloads = {
            evidence.id.value: DiscoveryEvidence._flatten_payload(evidence.payload)
            for evidence in ordered_evidences
        }
        merged_flat: dict[str, Any] = {}
        conflicts: list[DiscoveryReconciliationConflict] = []
        all_paths = sorted({path for payload in payloads.values() for path in payload})
        for path in all_paths:
            present = [
                evidence for evidence in ordered_evidences if path in payloads[evidence.id.value]
            ]
            canonical_values = {
                json.dumps(
                    payloads[evidence.id.value][path],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                for evidence in present
            }
            if len(canonical_values) == 1:
                merged_flat[path] = payloads[present[0].id.value][path]
                continue
            variants = tuple(
                DiscoveryConflictVariant(
                    evidence_id=evidence.id,
                    source=evidence.source,
                    source_ref=evidence.source_ref,
                    score=scores_by_id[evidence.id.value]["overall"],
                    value=payloads[evidence.id.value][path],
                )
                for evidence in sorted(
                    present,
                    key=lambda item: (
                        -scores_by_id[item.id.value]["overall"],
                        item.source.value,
                        item.source_ref,
                        item.id.value,
                    ),
                )
            )
            conflicts.append(
                DiscoveryReconciliationConflict(attribute_path=path, variants=variants)
            )
        confidence = cls._mean(
            tuple(scores_by_id[evidence.id.value]["confidence"] for evidence in ordered_evidences)
        )
        freshness = cls._mean(
            tuple(scores_by_id[evidence.id.value]["freshness"] for evidence in ordered_evidences)
        )
        completeness = cls._mean(
            tuple(scores_by_id[evidence.id.value]["completeness"] for evidence in ordered_evidences)
        )
        overall = cls._mean(
            tuple(scores_by_id[evidence.id.value]["overall"] for evidence in ordered_evidences)
        )
        signature_material = {
            "tenant_id": tenant_id.value,
            "object_key": normalized_key,
            "object_kind": next(iter(kinds)),
            "evidences": [
                {"id": evidence.id.value, "payload_hash": evidence.payload_hash}
                for evidence in ordered_evidences
            ],
        }
        signature = hashlib.sha256(
            json.dumps(signature_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            id=case_id or EntityId.new(),
            tenant_id=tenant_id,
            object_key=normalized_key,
            object_kind=next(iter(kinds)),
            evidence_ids=tuple(evidence.id for evidence in ordered_evidences),
            source_count=len(source_identities),
            confidence_score=confidence,
            freshness_score=freshness,
            completeness_score=completeness,
            overall_score=overall,
            status=(
                DiscoveryReconciliationStatus.CONFLICT
                if conflicts
                else DiscoveryReconciliationStatus.READY
            ),
            conflicts=tuple(conflicts),
            merged_payload=cls._unflatten_payload(merged_flat),
            evaluated_at=timestamp.astimezone(UTC),
            evaluated_by=actor,
            signature=signature,
            resolution=None,
            rsot_write_executed=False,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Self:
        raw_evidence_ids = value.get("evidence_ids", ())
        raw_conflicts = value.get("conflicts", ())
        raw_payload = value.get("merged_payload", {})
        raw_resolution = value.get("resolution")
        if not isinstance(raw_evidence_ids, Sequence) or isinstance(raw_evidence_ids, str):
            raise ValidationError("stored reconciliation evidence ids are invalid")
        if not isinstance(raw_conflicts, Sequence) or isinstance(raw_conflicts, str):
            raise ValidationError("stored reconciliation conflicts are invalid")
        if not isinstance(raw_payload, dict):
            raise ValidationError("stored reconciliation merged payload is invalid")
        return cls(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            object_key=DiscoveryEvidence._normalize_object_key(str(value["object_key"])),
            object_kind=DiscoveryEvidence._normalize_object_kind(str(value["object_kind"])),
            evidence_ids=tuple(EntityId.from_value(str(item)) for item in raw_evidence_ids),
            source_count=int(str(value["source_count"])),
            confidence_score=DiscoveryEvidence._normalize_score(
                float(str(value["confidence_score"])), "confidence score"
            ),
            freshness_score=DiscoveryEvidence._normalize_score(
                float(str(value["freshness_score"])), "freshness score"
            ),
            completeness_score=DiscoveryEvidence._normalize_score(
                float(str(value["completeness_score"])), "completeness score"
            ),
            overall_score=DiscoveryEvidence._normalize_score(
                float(str(value["overall_score"])), "overall score"
            ),
            status=DiscoveryReconciliationStatus(str(value["status"])),
            conflicts=tuple(
                DiscoveryReconciliationConflict.from_dict(cast(Mapping[str, object], item))
                for item in raw_conflicts
                if isinstance(item, Mapping)
            ),
            merged_payload=DiscoveryEvidence._normalize_payload(cast(dict[str, Any], raw_payload)),
            evaluated_at=datetime.fromisoformat(str(value["evaluated_at"])).astimezone(UTC),
            evaluated_by=str(value["evaluated_by"]),
            signature=str(value["signature"]),
            resolution=(
                None
                if raw_resolution is None
                else DiscoveryReconciliationResolution.from_dict(
                    cast(Mapping[str, object], raw_resolution)
                )
            ),
            rsot_write_executed=bool(value.get("rsot_write_executed", False)),
        )

    def resolve(
        self,
        selected_evidence_by_path: Mapping[str, str],
        actor: str,
        justification: str,
        resolved_at: datetime | None = None,
    ) -> Self:
        if self.status is not DiscoveryReconciliationStatus.CONFLICT:
            raise ValidationError("only a conflicting reconciliation case can be resolved")
        expected_paths = {conflict.attribute_path for conflict in self.conflicts}
        provided_paths = set(selected_evidence_by_path)
        if provided_paths != expected_paths:
            missing = sorted(expected_paths - provided_paths)
            unexpected = sorted(provided_paths - expected_paths)
            detail = {"missing": missing, "unexpected": unexpected}
            raise ValidationError(
                "reconciliation resolution selections are incomplete: " + str(detail)
            )
        merged_flat = DiscoveryEvidence._flatten_payload(self.merged_payload)
        normalized_selections: dict[str, str] = {}
        for conflict in self.conflicts:
            selected_id = str(selected_evidence_by_path[conflict.attribute_path]).strip()
            selected = next(
                (
                    variant
                    for variant in conflict.variants
                    if variant.evidence_id.value == selected_id
                ),
                None,
            )
            if selected is None:
                raise ValidationError(
                    "selected evidence does not provide conflict path " + conflict.attribute_path
                )
            merged_flat[conflict.attribute_path] = selected.value
            normalized_selections[conflict.attribute_path] = selected.evidence_id.value
        resolution = DiscoveryReconciliationResolution.create(
            actor=actor,
            justification=justification,
            selected_evidence_by_path=normalized_selections,
            resolved_at=resolved_at,
        )
        return self.__class__(
            id=self.id,
            tenant_id=self.tenant_id,
            object_key=self.object_key,
            object_kind=self.object_kind,
            evidence_ids=self.evidence_ids,
            source_count=self.source_count,
            confidence_score=self.confidence_score,
            freshness_score=self.freshness_score,
            completeness_score=self.completeness_score,
            overall_score=self.overall_score,
            status=DiscoveryReconciliationStatus.RESOLVED,
            conflicts=self.conflicts,
            merged_payload=self._unflatten_payload(merged_flat),
            evaluated_at=self.evaluated_at,
            evaluated_by=self.evaluated_by,
            signature=self.signature,
            resolution=resolution,
            rsot_write_executed=False,
        )

    @property
    def ready_for_rsot_reconciliation(self) -> bool:
        return self.status in {
            DiscoveryReconciliationStatus.READY,
            DiscoveryReconciliationStatus.RESOLVED,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "object_key": self.object_key,
            "object_kind": self.object_kind,
            "evidence_ids": [item.value for item in self.evidence_ids],
            "evidence_count": len(self.evidence_ids),
            "source_count": self.source_count,
            "confidence_score": self.confidence_score,
            "freshness_score": self.freshness_score,
            "completeness_score": self.completeness_score,
            "overall_score": self.overall_score,
            "status": self.status.value,
            "conflict_count": len(self.conflicts),
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
            "merged_payload": self.merged_payload,
            "evaluated_at": self.evaluated_at.isoformat(),
            "evaluated_by": self.evaluated_by,
            "signature": self.signature,
            "resolution": None if self.resolution is None else self.resolution.as_dict(),
            "ready_for_rsot_reconciliation": self.ready_for_rsot_reconciliation,
            "rsot_write_executed": self.rsot_write_executed,
        }

    @staticmethod
    def _mean(values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 6)

    @classmethod
    def _unflatten_payload(cls, flattened: Mapping[str, Any]) -> dict[str, Any]:
        root: dict[str, Any] = {}
        for path in sorted(flattened):
            segments = path.split(".")
            current = root
            for segment in segments[:-1]:
                existing = current.get(segment)
                if existing is None:
                    nested: dict[str, Any] = {}
                    current[segment] = nested
                    current = nested
                elif isinstance(existing, dict):
                    current = cast(dict[str, Any], existing)
                else:
                    raise ValidationError(
                        "reconciliation payload paths are structurally inconsistent"
                    )
            current[segments[-1]] = flattened[path]
        return root


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
                int(str(value["port"])),
            ),
            timeout_seconds=cls._normalize_timeout(int(str(value["timeout_seconds"]))),
            max_concurrency=cls._normalize_max_concurrency(int(str(value["max_concurrency"]))),
            rate_limit_per_minute=cls._normalize_rate_limit(
                int(str(value["rate_limit_per_minute"]))
            ),
            retry_count=cls._normalize_retry_count(int(str(value["retry_count"]))),
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


class DiscoveryIntegrationKind(StrEnum):
    VMWARE = "vmware"
    PROXMOX = "proxmox"
    HYPERV = "hyperv"
    KUBERNETES = "kubernetes"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OPENSTACK = "openstack"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "hyper-v": "hyperv",
            "k8s": "kubernetes",
            "amazon-web-services": "aws",
            "google-cloud": "gcp",
            "google-cloud-platform": "gcp",
        }
        normalized = aliases.get(normalized, normalized)
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(
                "discovery integration kind must be vmware, proxmox, hyperv, "
                "kubernetes, aws, azure, gcp or openstack"
            ) from exc


class DiscoveryIntegrationProfileStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"

    @classmethod
    def from_value(cls, value: str | None) -> Self:
        normalized = (value or "active").strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(
                "discovery integration profile status must be active or disabled"
            ) from exc


@dataclass(frozen=True, slots=True)
class DiscoveryIntegrationProfile:
    id: EntityId
    tenant_id: TenantId
    name: str
    kind: DiscoveryIntegrationKind
    scope: DiscoveryScope
    endpoint_url: str | None
    credential_secret_ref: str
    verify_tls: bool
    inventory_enabled: bool
    max_concurrency: int
    rate_limit_per_minute: int
    status: DiscoveryIntegrationProfileStatus
    created_by: str
    created_at: datetime
    disabled_reason: str | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        kind: str,
        scope: str,
        endpoint_url: str | None,
        credential_secret_ref: str,
        verify_tls: bool,
        inventory_enabled: bool,
        max_concurrency: int,
        rate_limit_per_minute: int,
        created_by: str,
        profile_id: EntityId | None = None,
        created_at: datetime | None = None,
    ) -> Self:
        integration_kind = DiscoveryIntegrationKind.from_value(kind)
        endpoint = cls._normalize_endpoint(integration_kind, endpoint_url)
        secret_ref = CollectorIdentity._normalize_secret_ref(credential_secret_ref)
        if secret_ref is None:
            raise ValidationError("discovery integration credential_secret_ref is mandatory")
        actor = DiscoveryProtocolCredentialProfile._normalize_actor(created_by)
        created = created_at or datetime.now(UTC)
        if created.tzinfo is None:
            raise ValidationError("discovery integration profile created_at must be timezone-aware")
        return cls(
            id=profile_id or EntityId.new(),
            tenant_id=tenant_id,
            name=DiscoveryProtocolCredentialProfile._normalize_name(name),
            kind=integration_kind,
            scope=DiscoveryScope.from_value(scope),
            endpoint_url=endpoint,
            credential_secret_ref=secret_ref,
            verify_tls=bool(verify_tls),
            inventory_enabled=bool(inventory_enabled),
            max_concurrency=DiscoveryProtocolCredentialProfile._normalize_max_concurrency(
                max_concurrency
            ),
            rate_limit_per_minute=DiscoveryProtocolCredentialProfile._normalize_rate_limit(
                rate_limit_per_minute
            ),
            status=DiscoveryIntegrationProfileStatus.ACTIVE,
            created_by=actor,
            created_at=created.astimezone(UTC),
        )

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> Self:
        created_value = value.get("created_at")
        kind = DiscoveryIntegrationKind.from_value(str(value["kind"]))
        return cls(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            name=DiscoveryProtocolCredentialProfile._normalize_name(str(value["name"])),
            kind=kind,
            scope=DiscoveryScope.from_value(str(value["scope"])),
            endpoint_url=cls._normalize_endpoint(
                kind,
                None if value.get("endpoint_url") is None else str(value["endpoint_url"]),
            ),
            credential_secret_ref=DiscoveryProtocolCredentialProfile._required_secret_ref(
                value.get("credential_secret_ref")
            ),
            verify_tls=bool(value.get("verify_tls", True)),
            inventory_enabled=bool(value.get("inventory_enabled", True)),
            max_concurrency=DiscoveryProtocolCredentialProfile._normalize_max_concurrency(
                int(str(value["max_concurrency"]))
            ),
            rate_limit_per_minute=DiscoveryProtocolCredentialProfile._normalize_rate_limit(
                int(str(value["rate_limit_per_minute"]))
            ),
            status=DiscoveryIntegrationProfileStatus.from_value(str(value.get("status", "active"))),
            created_by=DiscoveryProtocolCredentialProfile._normalize_actor(
                str(value["created_by"])
            ),
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
        endpoint_url: str | None = None,
        credential_secret_ref: str | None = None,
        verify_tls: bool | None = None,
        inventory_enabled: bool | None = None,
        max_concurrency: int | None = None,
        rate_limit_per_minute: int | None = None,
    ) -> Self:
        if self.status is not DiscoveryIntegrationProfileStatus.ACTIVE:
            raise ValidationError("disabled discovery integration profile cannot be updated")
        return self._copy(
            name=self.name
            if name is None
            else DiscoveryProtocolCredentialProfile._normalize_name(name),
            scope=self.scope.value if scope is None else DiscoveryScope.from_value(scope).value,
            endpoint_url=self.endpoint_url
            if endpoint_url is None
            else self._normalize_endpoint(self.kind, endpoint_url),
            credential_secret_ref=self.credential_secret_ref
            if credential_secret_ref is None
            else DiscoveryProtocolCredentialProfile._required_secret_ref(credential_secret_ref),
            verify_tls=self.verify_tls if verify_tls is None else bool(verify_tls),
            inventory_enabled=self.inventory_enabled
            if inventory_enabled is None
            else bool(inventory_enabled),
            max_concurrency=self.max_concurrency
            if max_concurrency is None
            else DiscoveryProtocolCredentialProfile._normalize_max_concurrency(max_concurrency),
            rate_limit_per_minute=self.rate_limit_per_minute
            if rate_limit_per_minute is None
            else DiscoveryProtocolCredentialProfile._normalize_rate_limit(rate_limit_per_minute),
        )

    def disable(self, reason: str) -> Self:
        normalized_reason = " ".join(reason.strip().split())
        if not normalized_reason:
            raise ValidationError("discovery integration profile disable reason is mandatory")
        return self._copy(
            status=DiscoveryIntegrationProfileStatus.DISABLED.value,
            disabled_reason=normalized_reason[:512],
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "kind": self.kind.value,
            "scope": self.scope.value,
            "endpoint_url": self.endpoint_url,
            "credential_secret_ref": self.credential_secret_ref,
            "verify_tls": self.verify_tls,
            "inventory_enabled": self.inventory_enabled,
            "max_concurrency": self.max_concurrency,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "disabled_reason": self.disabled_reason,
        }

    def as_public_dict(self) -> dict[str, object]:
        payload = self.as_dict()
        payload["credential_secret_ref"] = "vault://" + "***"
        payload["secret_materialized"] = False
        payload["rate_limit_active"] = True
        payload["connector_family"] = self.connector_family
        payload["discovery_execution"] = "plan_only_no_scan"
        payload["safeguards"] = [
            "vault_reference_only",
            "secret_material_never_returned",
            "connector_allowlist",
            "rate_limit_active",
            "bounded_concurrency",
            "inventory_plan_only",
        ]
        return payload

    @property
    def connector_family(self) -> str:
        if self.kind in {
            DiscoveryIntegrationKind.VMWARE,
            DiscoveryIntegrationKind.PROXMOX,
            DiscoveryIntegrationKind.HYPERV,
        }:
            return "virtualization"
        if self.kind is DiscoveryIntegrationKind.KUBERNETES:
            return "kubernetes"
        return "cloud"

    @classmethod
    def _normalize_endpoint(cls, kind: DiscoveryIntegrationKind, value: str | None) -> str | None:
        if value is None or not value.strip():
            if kind in {
                DiscoveryIntegrationKind.AWS,
                DiscoveryIntegrationKind.AZURE,
                DiscoveryIntegrationKind.GCP,
            }:
                return None
            raise ValidationError("discovery integration endpoint_url is mandatory")
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValidationError("discovery integration endpoint_url must be an https URL")
        return normalized.rstrip("/")

    def _copy(self, **changes: object) -> Self:
        payload = self.as_dict()
        payload.update(changes)
        return type(self).from_dict(payload)


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
