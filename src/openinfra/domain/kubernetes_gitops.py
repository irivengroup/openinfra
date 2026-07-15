from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Self
from urllib.parse import urlsplit

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.kubernetes_topology import (
    KubernetesResource,
    KubernetesResourceKind,
    KubernetesTopologySnapshot,
    KubernetesTopologyValidator,
)


class KubernetesGitOpsComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    DRIFT = "drift"


class KubernetesGitOpsDriftKind(StrEnum):
    MISSING_RESOURCE = "missing-resource"
    UNEXPECTED_RESOURCE = "unexpected-resource"
    MISSING_LABEL = "missing-label"
    LABEL_MISMATCH = "label-mismatch"
    MISSING_ANNOTATION = "missing-annotation"
    ANNOTATION_MISMATCH = "annotation-mismatch"
    MISSING_OWNER = "missing-owner"
    OWNER_MISMATCH = "owner-mismatch"
    MISSING_ENVIRONMENT = "missing-environment"
    ENVIRONMENT_MISMATCH = "environment-mismatch"
    ENVIRONMENT_NOT_ALLOWED = "environment-not-allowed"
    MISSING_ATTRIBUTE = "missing-attribute"
    ATTRIBUTE_MISMATCH = "attribute-mismatch"


class KubernetesGitOpsValidator:
    _GIT_REVISION = re.compile(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})")
    _ANNOTATION_KEY = re.compile(
        r"(?:[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?/)?"
        r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,61}[A-Za-z0-9])?"
    )
    _SENSITIVE_KEY = re.compile(
        r"(?:^|[_\-.])(password|passwd|pwd|secret|token|credential|api[_-]?key|private[_-]?key)"
        r"(?:$|[_\-.])",
        re.IGNORECASE,
    )

    @classmethod
    def repository_ref(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 1024:
            raise ValidationError("GitOps repository_ref must contain 1 to 1024 characters")
        if any(ord(char) < 32 for char in normalized) or any(char.isspace() for char in normalized):
            raise ValidationError(
                "GitOps repository_ref must not contain whitespace or control characters"
            )
        if "://" in normalized:
            parsed = urlsplit(normalized)
            if parsed.scheme not in {"https", "ssh"}:
                raise ValidationError("GitOps repository_ref must use HTTPS or SSH")
            if not parsed.hostname:
                raise ValidationError("GitOps repository_ref must define a host")
            if parsed.password is not None:
                raise ValidationError("GitOps repository_ref must not embed credentials")
            if parsed.query or parsed.fragment:
                raise ValidationError(
                    "GitOps repository_ref must not contain query or fragment data"
                )
        return normalized

    @classmethod
    def revision(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not cls._GIT_REVISION.fullmatch(normalized):
            raise ValidationError(
                "GitOps revision must be a full 40 or 64 hexadecimal commit digest"
            )
        return normalized

    @staticmethod
    def source_path(value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        if not normalized or len(normalized) > 512 or normalized.startswith("/"):
            raise ValidationError(
                "GitOps source_path must be a relative path of 1 to 512 characters"
            )
        path = PurePosixPath(normalized)
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValidationError(
                "GitOps source_path must not contain empty, dot or parent segments"
            )
        return path.as_posix()

    @classmethod
    def annotations(cls, values: dict[str, str]) -> dict[str, str]:
        if len(values) > 64:
            raise ValidationError("Kubernetes GitOps annotations cannot exceed 64 entries")
        normalized: dict[str, str] = {}
        total_bytes = 0
        for raw_key, raw_value in values.items():
            key = str(raw_key).strip()
            value = str(raw_value)
            if not cls._ANNOTATION_KEY.fullmatch(key):
                raise ValidationError(f"invalid Kubernetes annotation key: {key}")
            if cls._SENSITIVE_KEY.search(key):
                raise ValidationError("GitOps annotations must not contain sensitive keys")
            if len(value) > 4096:
                raise ValidationError(f"Kubernetes annotation value exceeds 4096 characters: {key}")
            total_bytes += len(key.encode("utf-8")) + len(value.encode("utf-8"))
            normalized[key] = value
        if total_bytes > 32_768:
            raise ValidationError("Kubernetes GitOps annotations exceed 32768 bytes")
        return dict(sorted(normalized.items()))

    @classmethod
    def metadata_keys(cls, values: tuple[str, ...], label: str) -> tuple[str, ...]:
        if len(values) > 64:
            raise ValidationError(f"{label} cannot exceed 64 entries")
        normalized: set[str] = set()
        for value in values:
            key = value.strip()
            if not cls._ANNOTATION_KEY.fullmatch(key):
                raise ValidationError(f"invalid Kubernetes metadata key: {key}")
            if cls._SENSITIVE_KEY.search(key):
                raise ValidationError(f"{label} must not contain sensitive keys")
            normalized.add(key)
        return tuple(sorted(normalized))

    @staticmethod
    def metadata_value(value: str | None, label: str) -> str | None:
        if value is None or not value.strip():
            return None
        return KubernetesTopologyValidator.token(value, label, 255)


@dataclass(frozen=True, slots=True)
class KubernetesGitOpsPolicy:
    required_labels: tuple[str, ...]
    required_annotations: tuple[str, ...]
    owner_label_key: str
    owner_annotation_key: str | None
    environment_label_key: str
    environment_annotation_key: str | None
    allowed_environments: tuple[str, ...]
    include_unexpected_resources: bool
    require_owner: bool
    require_environment: bool

    @classmethod
    def create(
        cls,
        required_labels: tuple[str, ...] = (),
        required_annotations: tuple[str, ...] = (),
        owner_label_key: str = "app.kubernetes.io/owner",
        owner_annotation_key: str | None = "openinfra.io/owner",
        environment_label_key: str = "app.kubernetes.io/environment",
        environment_annotation_key: str | None = "openinfra.io/environment",
        allowed_environments: tuple[str, ...] = (),
        include_unexpected_resources: bool = True,
        require_owner: bool = True,
        require_environment: bool = True,
    ) -> Self:
        labels = KubernetesGitOpsValidator.metadata_keys(required_labels, "required_labels")
        annotations = KubernetesGitOpsValidator.metadata_keys(
            required_annotations, "required_annotations"
        )
        owner_label = KubernetesGitOpsValidator.metadata_keys(
            (owner_label_key,), "owner_label_key"
        )[0]
        environment_label = KubernetesGitOpsValidator.metadata_keys(
            (environment_label_key,), "environment_label_key"
        )[0]
        owner_annotation = (
            KubernetesGitOpsValidator.metadata_keys(
                (owner_annotation_key,), "owner_annotation_key"
            )[0]
            if owner_annotation_key
            else None
        )
        environment_annotation = (
            KubernetesGitOpsValidator.metadata_keys(
                (environment_annotation_key,), "environment_annotation_key"
            )[0]
            if environment_annotation_key
            else None
        )
        environments = tuple(
            sorted(
                {
                    KubernetesTopologyValidator.token(value, "allowed environment", 128)
                    for value in allowed_environments
                }
            )
        )
        return cls(
            labels,
            annotations,
            owner_label,
            owner_annotation,
            environment_label,
            environment_annotation,
            environments,
            bool(include_unexpected_resources),
            bool(require_owner),
            bool(require_environment),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> Self:
        raw = payload or {}
        required_labels = raw.get("required_labels") or []
        required_annotations = raw.get("required_annotations") or []
        allowed_environments = raw.get("allowed_environments") or []
        if not isinstance(required_labels, list) or not isinstance(required_annotations, list):
            raise ValidationError("GitOps required metadata policies must be JSON arrays")
        if not isinstance(allowed_environments, list):
            raise ValidationError("GitOps allowed_environments must be a JSON array")
        return cls.create(
            required_labels=tuple(str(item) for item in required_labels),
            required_annotations=tuple(str(item) for item in required_annotations),
            owner_label_key=str(raw.get("owner_label_key") or "app.kubernetes.io/owner"),
            owner_annotation_key=(
                str(raw["owner_annotation_key"]) if raw.get("owner_annotation_key") else None
            ),
            environment_label_key=str(
                raw.get("environment_label_key") or "app.kubernetes.io/environment"
            ),
            environment_annotation_key=(
                str(raw["environment_annotation_key"])
                if raw.get("environment_annotation_key")
                else None
            ),
            allowed_environments=tuple(str(item) for item in allowed_environments),
            include_unexpected_resources=bool(raw.get("include_unexpected_resources", True)),
            require_owner=bool(raw.get("require_owner", True)),
            require_environment=bool(raw.get("require_environment", True)),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "required_labels": list(self.required_labels),
            "required_annotations": list(self.required_annotations),
            "owner_label_key": self.owner_label_key,
            "owner_annotation_key": self.owner_annotation_key,
            "environment_label_key": self.environment_label_key,
            "environment_annotation_key": self.environment_annotation_key,
            "allowed_environments": list(self.allowed_environments),
            "include_unexpected_resources": self.include_unexpected_resources,
            "require_owner": self.require_owner,
            "require_environment": self.require_environment,
        }


@dataclass(frozen=True, slots=True)
class KubernetesGitOpsResource:
    kind: KubernetesResourceKind
    name: str
    namespace: str | None
    labels: dict[str, str]
    annotations: dict[str, str]
    owner: str | None
    environment: str | None
    attributes: dict[str, Any]

    @classmethod
    def create(
        cls,
        kind: str,
        name: str,
        namespace: str | None = None,
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
        owner: str | None = None,
        environment: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Self:
        normalized_kind = KubernetesResourceKind.from_value(kind)
        normalized_namespace = (
            KubernetesTopologyValidator.name(namespace, "namespace") if namespace else None
        )
        if normalized_kind in {KubernetesResourceKind.NAMESPACE, KubernetesResourceKind.NODE}:
            if normalized_namespace is not None:
                raise ValidationError(f"GitOps {normalized_kind.value} must not define namespace")
        elif normalized_namespace is None:
            raise ValidationError(f"GitOps {normalized_kind.value} requires a namespace")
        return cls(
            kind=normalized_kind,
            name=KubernetesTopologyValidator.name(name, "resource name"),
            namespace=normalized_namespace,
            labels=KubernetesTopologyValidator.labels(labels or {}),
            annotations=KubernetesGitOpsValidator.annotations(annotations or {}),
            owner=KubernetesGitOpsValidator.metadata_value(owner, "GitOps owner"),
            environment=KubernetesGitOpsValidator.metadata_value(environment, "GitOps environment"),
            attributes=KubernetesTopologyValidator.json_object(
                attributes or {}, "GitOps expected attributes"
            ),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        labels = payload.get("labels") or {}
        annotations = payload.get("annotations") or {}
        attributes = payload.get("attributes") or {}
        if not isinstance(labels, dict) or not isinstance(annotations, dict):
            raise ValidationError("GitOps labels and annotations must be JSON objects")
        if not isinstance(attributes, dict):
            raise ValidationError("GitOps attributes must be a JSON object")
        return cls.create(
            kind=str(payload.get("kind", "")),
            name=str(payload.get("name", "")),
            namespace=str(payload["namespace"]) if payload.get("namespace") else None,
            labels={str(key): str(value) for key, value in labels.items()},
            annotations={str(key): str(value) for key, value in annotations.items()},
            owner=str(payload["owner"]) if payload.get("owner") else None,
            environment=str(payload["environment"]) if payload.get("environment") else None,
            attributes={str(key): value for key, value in attributes.items()},
        )

    @property
    def identity(self) -> tuple[str, str | None, str]:
        return (self.kind.value, self.namespace, self.name)

    @property
    def key(self) -> str:
        return f"{self.kind.value}:{self.namespace or '-'}:{self.name}"

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "namespace": self.namespace,
            "labels": self.labels,
            "annotations": self.annotations,
            "owner": self.owner,
            "environment": self.environment,
            "attributes": self.attributes,
        }


@dataclass(frozen=True, slots=True)
class KubernetesGitOpsState:
    id: EntityId
    tenant_id: TenantId
    cluster_key: str
    repository_ref: str
    revision: str
    source_path: str
    owner: str
    environment: str
    captured_at: datetime
    imported_at: datetime
    policy: KubernetesGitOpsPolicy
    resources: tuple[KubernetesGitOpsResource, ...]
    fingerprint: str

    _MAX_RESOURCES = 50_000

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        cluster_key: str,
        repository_ref: str,
        revision: str,
        source_path: str,
        owner: str,
        environment: str,
        captured_at: datetime,
        policy: KubernetesGitOpsPolicy,
        resources: tuple[KubernetesGitOpsResource, ...],
    ) -> Self:
        normalized_resources = cls._validate_resources(resources, policy)
        normalized_cluster = KubernetesTopologyValidator.token(cluster_key, "cluster key", 255)
        normalized_owner = KubernetesTopologyValidator.token(owner, "GitOps state owner", 255)
        normalized_environment = KubernetesTopologyValidator.token(
            environment, "GitOps state environment", 128
        )
        if (
            policy.allowed_environments
            and normalized_environment not in policy.allowed_environments
        ):
            raise ValidationError("GitOps state environment is not allowed by policy")
        normalized_captured = KubernetesTopologyValidator.aware_datetime(captured_at, "captured_at")
        normalized_repository = KubernetesGitOpsValidator.repository_ref(repository_ref)
        normalized_revision = KubernetesGitOpsValidator.revision(revision)
        normalized_path = KubernetesGitOpsValidator.source_path(source_path)
        payload = {
            "cluster_key": normalized_cluster,
            "repository_ref": normalized_repository,
            "revision": normalized_revision,
            "source_path": normalized_path,
            "owner": normalized_owner,
            "environment": normalized_environment,
            "captured_at": normalized_captured.isoformat(),
            "policy": policy.as_dict(),
            "resources": [item.as_dict() for item in normalized_resources],
        }
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            cluster_key=normalized_cluster,
            repository_ref=normalized_repository,
            revision=normalized_revision,
            source_path=normalized_path,
            owner=normalized_owner,
            environment=normalized_environment,
            captured_at=normalized_captured,
            imported_at=datetime.now(UTC),
            policy=policy,
            resources=normalized_resources,
            fingerprint=KubernetesTopologyValidator.digest(payload),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        cluster_key: str,
        repository_ref: str,
        revision: str,
        source_path: str,
        owner: str,
        environment: str,
        captured_at: datetime,
        imported_at: datetime,
        policy: KubernetesGitOpsPolicy,
        resources: tuple[KubernetesGitOpsResource, ...],
        fingerprint: str,
    ) -> Self:
        candidate = cls.create(
            tenant_id,
            cluster_key,
            repository_ref,
            revision,
            source_path,
            owner,
            environment,
            captured_at,
            policy,
            resources,
        )
        normalized_imported = KubernetesTopologyValidator.aware_datetime(imported_at, "imported_at")
        normalized_fingerprint = fingerprint.strip().lower()
        if normalized_fingerprint != candidate.fingerprint:
            raise ValidationError("GitOps state fingerprint mismatch")
        return cls(
            id=id,
            tenant_id=tenant_id,
            cluster_key=candidate.cluster_key,
            repository_ref=candidate.repository_ref,
            revision=candidate.revision,
            source_path=candidate.source_path,
            owner=candidate.owner,
            environment=candidate.environment,
            captured_at=candidate.captured_at,
            imported_at=normalized_imported,
            policy=candidate.policy,
            resources=candidate.resources,
            fingerprint=candidate.fingerprint,
        )

    @classmethod
    def _validate_resources(
        cls,
        resources: tuple[KubernetesGitOpsResource, ...],
        policy: KubernetesGitOpsPolicy,
    ) -> tuple[KubernetesGitOpsResource, ...]:
        if not resources:
            raise ValidationError("GitOps state requires at least one expected resource")
        if len(resources) > cls._MAX_RESOURCES:
            raise ValidationError(
                f"GitOps state cannot exceed {cls._MAX_RESOURCES} expected resources"
            )
        ordered = tuple(sorted(resources, key=lambda item: item.identity))
        seen: set[tuple[str, str | None, str]] = set()
        for resource in ordered:
            if resource.identity in seen:
                raise ValidationError(f"duplicate GitOps resource identity: {resource.key}")
            seen.add(resource.identity)
            for key in policy.required_labels:
                if key not in resource.labels:
                    raise ValidationError(
                        f"GitOps expected resource {resource.key} misses required label {key}"
                    )
            for key in policy.required_annotations:
                if key not in resource.annotations:
                    raise ValidationError(
                        f"GitOps expected resource {resource.key} misses required annotation {key}"
                    )
            if policy.require_owner and not resource.owner:
                raise ValidationError(f"GitOps expected resource {resource.key} requires an owner")
            if policy.require_environment and not resource.environment:
                raise ValidationError(
                    f"GitOps expected resource {resource.key} requires an environment"
                )
            if (
                resource.environment
                and policy.allowed_environments
                and resource.environment not in policy.allowed_environments
            ):
                raise ValidationError(
                    f"GitOps expected resource {resource.key} uses a disallowed environment"
                )
        return ordered

    def as_dict(self, include_resources: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "cluster_key": self.cluster_key,
            "repository_ref": self.repository_ref,
            "revision": self.revision,
            "source_path": self.source_path,
            "owner": self.owner,
            "environment": self.environment,
            "captured_at": self.captured_at.isoformat(),
            "imported_at": self.imported_at.isoformat(),
            "policy": self.policy.as_dict(),
            "fingerprint": self.fingerprint,
            "resource_count": len(self.resources),
        }
        if include_resources:
            payload["resources"] = [item.as_dict() for item in self.resources]
        return payload


@dataclass(frozen=True, slots=True)
class KubernetesGitOpsDrift:
    resource_key: str
    kind: KubernetesGitOpsDriftKind
    path: str
    severity: Severity
    expected: object | None
    observed: object | None

    def as_dict(self) -> dict[str, object | None]:
        return {
            "resource_key": self.resource_key,
            "kind": self.kind.value,
            "path": self.path,
            "severity": self.severity.value,
            "expected": self.expected,
            "observed": self.observed,
        }


@dataclass(frozen=True, slots=True)
class KubernetesGitOpsComplianceReport:
    expected_state_id: str
    expected_fingerprint: str
    observed_snapshot_id: str
    observed_fingerprint: str
    cluster_key: str
    status: KubernetesGitOpsComplianceStatus
    assessed_at: datetime
    drifts: tuple[KubernetesGitOpsDrift, ...]
    fingerprint: str

    @classmethod
    def evaluate(
        cls,
        expected: KubernetesGitOpsState,
        observed: KubernetesTopologySnapshot,
        assessed_at: datetime | None = None,
    ) -> Self:
        if expected.tenant_id != observed.tenant_id:
            raise ValidationError(
                "GitOps expected and observed states must belong to the same tenant"
            )
        if expected.cluster_key != observed.cluster_key:
            raise ValidationError(
                "GitOps expected and observed states must target the same cluster"
            )
        observed_by_identity = {
            (item.kind.value, item.namespace, item.name): item for item in observed.resources
        }
        expected_by_identity = {item.identity: item for item in expected.resources}
        drifts: list[KubernetesGitOpsDrift] = []
        for identity, desired in expected_by_identity.items():
            actual = observed_by_identity.get(identity)
            if actual is None:
                drifts.append(
                    KubernetesGitOpsDrift(
                        desired.key,
                        KubernetesGitOpsDriftKind.MISSING_RESOURCE,
                        "/",
                        Severity.CRITICAL,
                        desired.as_dict(),
                        None,
                    )
                )
                continue
            cls._compare_resource(desired, actual, expected.policy, drifts)
        if expected.policy.include_unexpected_resources:
            managed_kinds = {item.kind.value for item in expected.resources}
            for identity, actual in observed_by_identity.items():
                if identity in expected_by_identity or actual.kind.value not in managed_kinds:
                    continue
                drifts.append(
                    KubernetesGitOpsDrift(
                        cls._resource_key(actual),
                        KubernetesGitOpsDriftKind.UNEXPECTED_RESOURCE,
                        "/",
                        Severity.WARNING,
                        None,
                        cls._observed_summary(actual),
                    )
                )
        ordered = tuple(
            sorted(
                drifts,
                key=lambda item: (item.resource_key, item.path, item.kind.value),
            )
        )
        normalized_assessed = KubernetesTopologyValidator.aware_datetime(
            assessed_at or datetime.now(UTC), "assessed_at"
        )
        status = (
            KubernetesGitOpsComplianceStatus.COMPLIANT
            if not ordered
            else KubernetesGitOpsComplianceStatus.DRIFT
        )
        fingerprint = KubernetesTopologyValidator.digest(
            {
                "expected_fingerprint": expected.fingerprint,
                "observed_fingerprint": observed.fingerprint,
                "status": status.value,
                "drifts": [item.as_dict() for item in ordered],
            }
        )
        return cls(
            expected_state_id=expected.id.value,
            expected_fingerprint=expected.fingerprint,
            observed_snapshot_id=observed.id.value,
            observed_fingerprint=observed.fingerprint,
            cluster_key=expected.cluster_key,
            status=status,
            assessed_at=normalized_assessed,
            drifts=ordered,
            fingerprint=fingerprint,
        )

    @classmethod
    def _compare_resource(
        cls,
        expected: KubernetesGitOpsResource,
        observed: KubernetesResource,
        policy: KubernetesGitOpsPolicy,
        drifts: list[KubernetesGitOpsDrift],
    ) -> None:
        annotations = cls._observed_annotations(observed)
        for key in sorted(set(policy.required_labels).union(expected.labels)):
            desired = expected.labels.get(key)
            actual = observed.labels.get(key)
            if actual is None:
                cls._append_metadata_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.MISSING_LABEL,
                    f"/labels/{cls._escape(key)}",
                    desired,
                    None,
                )
            elif desired is not None and actual != desired:
                cls._append_metadata_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.LABEL_MISMATCH,
                    f"/labels/{cls._escape(key)}",
                    desired,
                    actual,
                )
        for key in sorted(set(policy.required_annotations).union(expected.annotations)):
            desired = expected.annotations.get(key)
            actual = annotations.get(key)
            if actual is None:
                cls._append_metadata_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.MISSING_ANNOTATION,
                    f"/annotations/{cls._escape(key)}",
                    desired,
                    None,
                )
            elif desired is not None and actual != desired:
                cls._append_metadata_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.ANNOTATION_MISMATCH,
                    f"/annotations/{cls._escape(key)}",
                    desired,
                    actual,
                )
        owner = cls._metadata_value(
            observed,
            annotations,
            policy.owner_label_key,
            policy.owner_annotation_key,
        )
        if expected.owner is not None or policy.require_owner:
            if owner is None:
                cls._append_governance_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.MISSING_OWNER,
                    "/governance/owner",
                    expected.owner,
                    None,
                )
            elif expected.owner is not None and owner != expected.owner:
                cls._append_governance_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.OWNER_MISMATCH,
                    "/governance/owner",
                    expected.owner,
                    owner,
                )
        environment = cls._metadata_value(
            observed,
            annotations,
            policy.environment_label_key,
            policy.environment_annotation_key,
        )
        if expected.environment is not None or policy.require_environment:
            if environment is None:
                cls._append_governance_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.MISSING_ENVIRONMENT,
                    "/governance/environment",
                    expected.environment,
                    None,
                )
            elif expected.environment is not None and environment != expected.environment:
                cls._append_governance_drift(
                    drifts,
                    expected.key,
                    KubernetesGitOpsDriftKind.ENVIRONMENT_MISMATCH,
                    "/governance/environment",
                    expected.environment,
                    environment,
                )
        if (
            environment is not None
            and policy.allowed_environments
            and environment not in policy.allowed_environments
        ):
            cls._append_governance_drift(
                drifts,
                expected.key,
                KubernetesGitOpsDriftKind.ENVIRONMENT_NOT_ALLOWED,
                "/governance/environment",
                list(policy.allowed_environments),
                environment,
            )
        cls._compare_attributes(expected.key, expected.attributes, observed.attributes, "", drifts)

    @classmethod
    def _compare_attributes(
        cls,
        resource_key: str,
        expected: object,
        observed: object,
        path: str,
        drifts: list[KubernetesGitOpsDrift],
    ) -> None:
        if isinstance(expected, dict):
            if not isinstance(observed, dict):
                drifts.append(
                    KubernetesGitOpsDrift(
                        resource_key,
                        KubernetesGitOpsDriftKind.ATTRIBUTE_MISMATCH,
                        path or "/attributes",
                        Severity.ERROR,
                        expected,
                        observed,
                    )
                )
                return
            for key in sorted(expected):
                child_path = (
                    f"{path}/{cls._escape(str(key))}"
                    if path
                    else f"/attributes/{cls._escape(str(key))}"
                )
                if key not in observed:
                    drifts.append(
                        KubernetesGitOpsDrift(
                            resource_key,
                            KubernetesGitOpsDriftKind.MISSING_ATTRIBUTE,
                            child_path,
                            Severity.ERROR,
                            expected[key],
                            None,
                        )
                    )
                    continue
                cls._compare_attributes(
                    resource_key, expected[key], observed[key], child_path, drifts
                )
            return
        if expected != observed:
            drifts.append(
                KubernetesGitOpsDrift(
                    resource_key,
                    KubernetesGitOpsDriftKind.ATTRIBUTE_MISMATCH,
                    path or "/attributes",
                    Severity.ERROR,
                    expected,
                    observed,
                )
            )

    @staticmethod
    def _observed_annotations(resource: KubernetesResource) -> dict[str, str]:
        value = resource.attributes.get("annotations", {})
        if not isinstance(value, dict):
            return {}
        result: dict[str, str] = {}
        for key, item in value.items():
            if isinstance(key, str) and isinstance(item, str):
                result[key] = item
        return result

    @staticmethod
    def _metadata_value(
        resource: KubernetesResource,
        annotations: dict[str, str],
        label_key: str,
        annotation_key: str | None,
    ) -> str | None:
        value = resource.labels.get(label_key)
        if value is not None and value.strip():
            return value.strip().lower()
        if annotation_key is not None:
            value = annotations.get(annotation_key)
            if value is not None and value.strip():
                return value.strip().lower()
        return None

    @staticmethod
    def _append_metadata_drift(
        drifts: list[KubernetesGitOpsDrift],
        resource_key: str,
        kind: KubernetesGitOpsDriftKind,
        path: str,
        expected: object | None,
        observed: object | None,
    ) -> None:
        drifts.append(
            KubernetesGitOpsDrift(resource_key, kind, path, Severity.WARNING, expected, observed)
        )

    @staticmethod
    def _append_governance_drift(
        drifts: list[KubernetesGitOpsDrift],
        resource_key: str,
        kind: KubernetesGitOpsDriftKind,
        path: str,
        expected: object | None,
        observed: object | None,
    ) -> None:
        drifts.append(
            KubernetesGitOpsDrift(resource_key, kind, path, Severity.ERROR, expected, observed)
        )

    @staticmethod
    def _resource_key(resource: KubernetesResource) -> str:
        return f"{resource.kind.value}:{resource.namespace or '-'}:{resource.name}"

    @staticmethod
    def _observed_summary(resource: KubernetesResource) -> dict[str, object]:
        return {
            "kind": resource.kind.value,
            "name": resource.name,
            "namespace": resource.namespace,
        }

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    def summary(self) -> dict[str, object]:
        by_kind = {kind.value: 0 for kind in KubernetesGitOpsDriftKind}
        by_severity = {severity.value: 0 for severity in Severity}
        for drift in self.drifts:
            by_kind[drift.kind.value] += 1
            by_severity[drift.severity.value] += 1
        return {
            "total": len(self.drifts),
            "by_kind": by_kind,
            "by_severity": by_severity,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_state_id": self.expected_state_id,
            "expected_fingerprint": self.expected_fingerprint,
            "observed_snapshot_id": self.observed_snapshot_id,
            "observed_fingerprint": self.observed_fingerprint,
            "cluster_key": self.cluster_key,
            "status": self.status.value,
            "assessed_at": self.assessed_at.isoformat(),
            "drifts": [item.as_dict() for item in self.drifts],
            "summary": self.summary(),
            "fingerprint": self.fingerprint,
            "automatic_remediation": False,
        }
