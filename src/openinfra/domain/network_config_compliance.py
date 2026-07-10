from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceObjectKey


class NetworkConfigBaselineStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class NetworkConfigObservationSource(StrEnum):
    SSH = "ssh"
    API = "api"
    NETCONF = "netconf"
    RESTCONF = "restconf"
    GNMI = "gnmi"
    DISCOVERY = "discovery"
    IMPORT = "import"
    MANUAL = "manual"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError(
                "network configuration observation source is unsupported"
            ) from exc


class NetworkConfigComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    DRIFT = "drift"
    MISSING_OBSERVATION = "missing-observation"


class NetworkConfigDriftKind(StrEnum):
    MISSING = "missing"
    UNEXPECTED = "unexpected"
    MISMATCH = "mismatch"
    TYPE_MISMATCH = "type-mismatch"


class NetworkConfigDocumentPolicy:
    MAX_BYTES = 1_048_576
    MAX_DEPTH = 32
    MAX_NODES = 10_000
    _SENSITIVE_KEY = re.compile(
        r"(?:^|[_\-.])(password|passwd|secret|private[_-]?key|api[_-]?key|token|community|credential)(?:$|[_\-.])",
        re.IGNORECASE,
    )

    def normalize(self, value: object) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError("network configuration document must be a JSON object")
        counter = [0]
        normalized = self._normalize_value(value, depth=0, counter=counter)
        if not isinstance(normalized, dict):
            raise ValidationError("network configuration root must be a JSON object")
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.MAX_BYTES:
            raise ValidationError("network configuration document exceeds 1 MiB")
        return normalized

    def fingerprint(self, value: dict[str, Any]) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _normalize_value(self, value: object, depth: int, counter: list[int]) -> Any:
        counter[0] += 1
        if counter[0] > self.MAX_NODES:
            raise ValidationError("network configuration document exceeds 10000 nodes")
        if depth > self.MAX_DEPTH:
            raise ValidationError("network configuration document exceeds maximum depth")
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key in sorted(value):
                if not isinstance(raw_key, str):
                    raise ValidationError("network configuration keys must be strings")
                key = raw_key.strip()
                if not key or len(key) > 128:
                    raise ValidationError(
                        "network configuration keys must contain 1 to 128 characters"
                    )
                if self._SENSITIVE_KEY.search(key):
                    raise ValidationError("network configuration document must not contain secrets")
                result[key] = self._normalize_value(value[raw_key], depth + 1, counter)
            return result
        if isinstance(value, list):
            return [self._normalize_value(item, depth + 1, counter) for item in value]
        if value is None or isinstance(value, (bool, int, float, str)):
            if isinstance(value, str):
                if len(value) > 16_384:
                    raise ValidationError("network configuration scalar exceeds maximum length")
                private_key_marker = "-----BEGIN PRIVATE " + "KEY-----"
                rsa_private_key_marker = "-----BEGIN RSA PRIVATE " + "KEY-----"
                if private_key_marker in value or rsa_private_key_marker in value:
                    raise ValidationError(
                        "network configuration document must not contain private keys"
                    )
            return value
        raise ValidationError("network configuration document contains an unsupported value")


class NetworkConfigPathPolicy:
    _PATH = re.compile(r"/(?:[^/~]|~[01])+(?:/(?:[^/~]|~[01])+)*")

    def normalize_many(self, values: tuple[str, ...], label: str) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            path = value.strip()
            if not self._PATH.fullmatch(path):
                raise ValidationError(f"{label} must use JSON Pointer paths")
            if path not in normalized:
                normalized.append(path)
        return tuple(sorted(normalized))

    @staticmethod
    def is_within(path: str, parent: str) -> bool:
        return path == parent or path.startswith(parent + "/")


@dataclass(frozen=True, slots=True)
class NetworkConfigBaseline:
    id: EntityId
    tenant_id: TenantId
    code: str
    device_object_key: str
    platform: str
    expected_config: dict[str, Any]
    ignored_paths: tuple[str, ...]
    critical_paths: tuple[str, ...]
    owner: str
    justification: str
    status: NetworkConfigBaselineStatus
    version: int
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    fingerprint: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        device_object_key: str,
        platform: str,
        expected_config: object,
        ignored_paths: tuple[str, ...],
        critical_paths: tuple[str, ...],
        owner: str,
        justification: str,
        actor: str,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            code=code,
            device_object_key=device_object_key,
            platform=platform,
            expected_config=expected_config,
            ignored_paths=ignored_paths,
            critical_paths=critical_paths,
            owner=owner,
            justification=justification,
            status="active",
            version=1,
            created_by=actor,
            created_at=now,
            updated_by=actor,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        code: str,
        device_object_key: str,
        platform: str,
        expected_config: object,
        ignored_paths: tuple[str, ...],
        critical_paths: tuple[str, ...],
        owner: str,
        justification: str,
        status: str,
        version: int,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
    ) -> Self:
        policy = NetworkConfigDocumentPolicy()
        config = policy.normalize(expected_config)
        path_policy = NetworkConfigPathPolicy()
        normalized_code = code.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{0,63}", normalized_code):
            raise ValidationError("network configuration baseline code is invalid")
        normalized_platform = platform.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{1,63}", normalized_platform):
            raise ValidationError("network platform must use 2 to 64 safe characters")
        normalized_owner = " ".join(owner.strip().split())
        normalized_justification = " ".join(justification.strip().split())
        normalized_actor = NetworkConfigRules.actor(created_by, "created_by")
        normalized_updated_actor = NetworkConfigRules.actor(updated_by, "updated_by")
        if not 2 <= len(normalized_owner) <= 255:
            raise ValidationError("network configuration owner must contain 2 to 255 characters")
        if not 8 <= len(normalized_justification) <= 1000:
            raise ValidationError(
                "network configuration justification must contain 8 to 1000 characters"
            )
        if version < 1:
            raise ValidationError("network configuration baseline version must be positive")
        return cls(
            id=id,
            tenant_id=tenant_id,
            code=normalized_code,
            device_object_key=SourceObjectKey.from_value(device_object_key).value,
            platform=normalized_platform,
            expected_config=config,
            ignored_paths=path_policy.normalize_many(ignored_paths, "ignored paths"),
            critical_paths=path_policy.normalize_many(critical_paths, "critical paths"),
            owner=normalized_owner,
            justification=normalized_justification,
            status=NetworkConfigBaselineStatus(status),
            version=int(version),
            created_by=normalized_actor,
            created_at=NetworkConfigRules.aware(created_at, "created_at"),
            updated_by=normalized_updated_actor,
            updated_at=NetworkConfigRules.aware(updated_at, "updated_at"),
            fingerprint=policy.fingerprint(config),
        )

    def revise(
        self,
        *,
        platform: str,
        expected_config: object,
        ignored_paths: tuple[str, ...],
        critical_paths: tuple[str, ...],
        owner: str,
        justification: str,
        actor: str,
    ) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            code=self.code,
            device_object_key=self.device_object_key,
            platform=platform,
            expected_config=expected_config,
            ignored_paths=ignored_paths,
            critical_paths=critical_paths,
            owner=owner,
            justification=justification,
            status="active",
            version=self.version + 1,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def retire(self, actor: str) -> Self:
        if self.status is NetworkConfigBaselineStatus.RETIRED:
            return self
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            code=self.code,
            device_object_key=self.device_object_key,
            platform=self.platform,
            expected_config=self.expected_config,
            ignored_paths=self.ignored_paths,
            critical_paths=self.critical_paths,
            owner=self.owner,
            justification=self.justification,
            status="retired",
            version=self.version + 1,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "code": self.code,
            "device_object_key": self.device_object_key,
            "platform": self.platform,
            "expected_config": self.expected_config,
            "ignored_paths": list(self.ignored_paths),
            "critical_paths": list(self.critical_paths),
            "owner": self.owner,
            "justification": self.justification,
            "status": self.status.value,
            "version": self.version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class NetworkConfigObservation:
    id: EntityId
    tenant_id: TenantId
    idempotency_key: str
    source: NetworkConfigObservationSource
    collector: str
    device_object_key: str
    platform: str
    observed_config: dict[str, Any]
    observed_at: datetime
    received_at: datetime
    fingerprint: str

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        idempotency_key: str,
        source: str,
        collector: str,
        device_object_key: str,
        platform: str,
        observed_config: object,
        observed_at: datetime,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            source=source,
            collector=collector,
            device_object_key=device_object_key,
            platform=platform,
            observed_config=observed_config,
            observed_at=observed_at,
            received_at=datetime.now(UTC),
            fingerprint=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        idempotency_key: str,
        source: str,
        collector: str,
        device_object_key: str,
        platform: str,
        observed_config: object,
        observed_at: datetime,
        received_at: datetime,
        fingerprint: str | None,
    ) -> Self:
        policy = NetworkConfigDocumentPolicy()
        config = policy.normalize(observed_config)
        key = idempotency_key.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}", key):
            raise ValidationError("network configuration idempotency key is invalid")
        normalized_collector = " ".join(collector.strip().split())
        if not 2 <= len(normalized_collector) <= 255:
            raise ValidationError(
                "network configuration collector must contain 2 to 255 characters"
            )
        normalized_platform = platform.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{1,63}", normalized_platform):
            raise ValidationError("network platform must use 2 to 64 safe characters")
        payload = {
            "source": NetworkConfigObservationSource.from_value(source).value,
            "collector": normalized_collector,
            "device_object_key": SourceObjectKey.from_value(device_object_key).value,
            "platform": normalized_platform,
            "observed_config": config,
            "observed_at": NetworkConfigRules.aware(observed_at, "observed_at").isoformat(),
        }
        calculated = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if fingerprint is not None and fingerprint != calculated:
            raise ValidationError("network configuration observation fingerprint is invalid")
        return cls(
            id=id,
            tenant_id=tenant_id,
            idempotency_key=key,
            source=NetworkConfigObservationSource.from_value(source),
            collector=normalized_collector,
            device_object_key=SourceObjectKey.from_value(device_object_key).value,
            platform=normalized_platform,
            observed_config=config,
            observed_at=NetworkConfigRules.aware(observed_at, "observed_at"),
            received_at=NetworkConfigRules.aware(received_at, "received_at"),
            fingerprint=calculated,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "idempotency_key": self.idempotency_key,
            "source": self.source.value,
            "collector": self.collector,
            "device_object_key": self.device_object_key,
            "platform": self.platform,
            "observed_config": self.observed_config,
            "observed_at": self.observed_at.isoformat(),
            "received_at": self.received_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class NetworkConfigDrift:
    path: str
    kind: NetworkConfigDriftKind
    expected: object
    observed: object
    severity: Severity

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "kind": self.kind.value,
            "expected": self.expected,
            "observed": self.observed,
            "severity": self.severity.value,
        }


@dataclass(frozen=True, slots=True)
class NetworkConfigComplianceReport:
    baseline: NetworkConfigBaseline
    observation: NetworkConfigObservation | None
    status: NetworkConfigComplianceStatus
    drifts: tuple[NetworkConfigDrift, ...]

    @classmethod
    def evaluate(
        cls, baseline: NetworkConfigBaseline, observation: NetworkConfigObservation | None
    ) -> Self:
        if observation is None:
            return cls(baseline, None, NetworkConfigComplianceStatus.MISSING_OBSERVATION, ())
        if observation.device_object_key != baseline.device_object_key:
            raise ValidationError("network configuration observation targets a different device")
        if observation.platform != baseline.platform:
            drift = NetworkConfigDrift(
                "/platform",
                NetworkConfigDriftKind.MISMATCH,
                baseline.platform,
                observation.platform,
                Severity.CRITICAL,
            )
            return cls(baseline, observation, NetworkConfigComplianceStatus.DRIFT, (drift,))
        drifts: list[NetworkConfigDrift] = []
        cls._compare(baseline.expected_config, observation.observed_config, "", baseline, drifts)
        return cls(
            baseline,
            observation,
            NetworkConfigComplianceStatus.COMPLIANT
            if not drifts
            else NetworkConfigComplianceStatus.DRIFT,
            tuple(drifts),
        )

    @classmethod
    def _compare(
        cls,
        expected: object,
        observed: object,
        path: str,
        baseline: NetworkConfigBaseline,
        drifts: list[NetworkConfigDrift],
    ) -> None:
        pointer = path or "/"
        policy = NetworkConfigPathPolicy()
        if any(policy.is_within(pointer, ignored) for ignored in baseline.ignored_paths):
            return
        severity = (
            Severity.CRITICAL
            if any(policy.is_within(pointer, critical) for critical in baseline.critical_paths)
            else Severity.WARNING
        )
        if type(expected) is not type(observed):
            drifts.append(
                NetworkConfigDrift(
                    pointer, NetworkConfigDriftKind.TYPE_MISMATCH, expected, observed, severity
                )
            )
            return
        if isinstance(expected, dict) and isinstance(observed, dict):
            for key in sorted(expected.keys() - observed.keys()):
                child = cls._path(path, key)
                if not any(policy.is_within(child, ignored) for ignored in baseline.ignored_paths):
                    drifts.append(
                        NetworkConfigDrift(
                            child,
                            NetworkConfigDriftKind.MISSING,
                            expected[key],
                            None,
                            NetworkConfigRules.severity(child, baseline),
                        )
                    )
            for key in sorted(observed.keys() - expected.keys()):
                child = cls._path(path, key)
                if not any(policy.is_within(child, ignored) for ignored in baseline.ignored_paths):
                    drifts.append(
                        NetworkConfigDrift(
                            child,
                            NetworkConfigDriftKind.UNEXPECTED,
                            None,
                            observed[key],
                            NetworkConfigRules.severity(child, baseline),
                        )
                    )
            for key in sorted(expected.keys() & observed.keys()):
                cls._compare(expected[key], observed[key], cls._path(path, key), baseline, drifts)
            return
        if isinstance(expected, list) and isinstance(observed, list):
            for index in range(max(len(expected), len(observed))):
                child = cls._path(path, str(index))
                if index >= len(expected):
                    drifts.append(
                        NetworkConfigDrift(
                            child,
                            NetworkConfigDriftKind.UNEXPECTED,
                            None,
                            observed[index],
                            NetworkConfigRules.severity(child, baseline),
                        )
                    )
                elif index >= len(observed):
                    drifts.append(
                        NetworkConfigDrift(
                            child,
                            NetworkConfigDriftKind.MISSING,
                            expected[index],
                            None,
                            NetworkConfigRules.severity(child, baseline),
                        )
                    )
                else:
                    cls._compare(expected[index], observed[index], child, baseline, drifts)
            return
        if expected != observed:
            drifts.append(
                NetworkConfigDrift(
                    pointer, NetworkConfigDriftKind.MISMATCH, expected, observed, severity
                )
            )

    @staticmethod
    def _path(parent: str, token: str) -> str:
        escaped = token.replace("~", "~0").replace("/", "~1")
        return f"{parent}/{escaped}" if parent else f"/{escaped}"

    def as_dict(self) -> dict[str, object]:
        counts = {
            kind.value: sum(1 for item in self.drifts if item.kind is kind)
            for kind in NetworkConfigDriftKind
        }
        return {
            "baseline": self.baseline.as_dict(),
            "observation": None if self.observation is None else self.observation.as_dict(),
            "status": self.status.value,
            "drifts": [item.as_dict() for item in self.drifts],
            "summary": {"total": len(self.drifts), **counts},
        }


class NetworkConfigRules:
    @staticmethod
    def aware(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def actor(value: str, label: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 2 <= len(normalized) <= 255:
            raise ValidationError(f"{label} must contain 2 to 255 characters")
        return normalized

    @staticmethod
    def severity(path: str, baseline: NetworkConfigBaseline) -> Severity:
        policy = NetworkConfigPathPolicy()
        return (
            Severity.CRITICAL
            if any(policy.is_within(path, critical) for critical in baseline.critical_paths)
            else Severity.WARNING
        )
