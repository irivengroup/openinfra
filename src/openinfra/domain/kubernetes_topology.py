from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self, cast

from openinfra.domain.common import EntityId, TenantId, ValidationError


class KubernetesResourceKind(StrEnum):
    NAMESPACE = "namespace"
    NODE = "node"
    WORKLOAD = "workload"
    POD = "pod"
    SERVICE = "service"
    INGRESS = "ingress"
    NETWORK_POLICY = "network-policy"
    VOLUME = "volume"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "networkpolicy": cls.NETWORK_POLICY.value,
            "network-policy": cls.NETWORK_POLICY.value,
            "persistent-volume": cls.VOLUME.value,
            "persistentvolume": cls.VOLUME.value,
            "pvc": cls.VOLUME.value,
        }
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("unsupported Kubernetes resource kind") from exc


class KubernetesTopologyValidator:
    _SAFE_TOKEN = re.compile(r"[a-z0-9][a-z0-9_.:/@+-]{0,254}")
    _DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
    _LABEL_KEY = re.compile(
        r"(?:[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?/)?[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,61}[A-Za-z0-9])?"
    )
    _SENSITIVE_KEY = re.compile(
        r"(?:^|[_\-.])(password|passwd|pwd|secret|token|credential|api[_-]?key|private[_-]?key)(?:$|[_\-.])",
        re.IGNORECASE,
    )

    @classmethod
    def token(cls, value: str, label: str, maximum: int = 255) -> str:
        normalized = value.strip().lower()
        if len(normalized) > maximum or not cls._SAFE_TOKEN.fullmatch(normalized):
            raise ValidationError(f"{label} must use 1 to {maximum} safe characters")
        return normalized

    @classmethod
    def name(cls, value: str, label: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) > 253:
            raise ValidationError(f"{label} exceeds 253 characters")
        parts = normalized.split(".")
        if not parts or any(not cls._DNS_LABEL.fullmatch(part) for part in parts):
            raise ValidationError(f"{label} must use a Kubernetes-compatible DNS name")
        return normalized

    @classmethod
    def optional_token(cls, value: str | None, label: str, maximum: int = 255) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.token(value, label, maximum)

    @classmethod
    def labels(cls, values: dict[str, str]) -> dict[str, str]:
        if len(values) > 64:
            raise ValidationError("Kubernetes resource labels cannot exceed 64 entries")
        normalized: dict[str, str] = {}
        for raw_key, raw_value in values.items():
            key = str(raw_key).strip()
            value = str(raw_value).strip()
            if not cls._LABEL_KEY.fullmatch(key):
                raise ValidationError(f"invalid Kubernetes label key: {key}")
            if len(value) > 63:
                raise ValidationError(f"Kubernetes label value exceeds 63 characters: {key}")
            normalized[key] = value
        return dict(sorted(normalized.items()))

    @classmethod
    def json_object(
        cls, value: dict[str, Any], label: str, maximum_bytes: int = 32768
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        sanitized = cast(dict[str, Any], cls._sanitize(value, label, "$"))
        try:
            encoded = json.dumps(
                sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{label} must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > maximum_bytes:
            raise ValidationError(f"{label} exceeds {maximum_bytes} bytes")
        return sanitized

    @classmethod
    def _sanitize(cls, value: Any, label: str, path: str) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key, item in value.items():
                key = str(raw_key)
                if cls._SENSITIVE_KEY.search(key):
                    raise ValidationError(f"{label} contains a sensitive key at {path}.{key}")
                result[key] = cls._sanitize(item, label, f"{path}.{key}")
            return result
        if isinstance(value, (list, tuple)):
            return [
                cls._sanitize(item, label, f"{path}[{index}]") for index, item in enumerate(value)
            ]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        raise ValidationError(f"{label} contains an unsupported JSON value at {path}")

    @staticmethod
    def aware_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @staticmethod
    def digest(payload: object) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class KubernetesPhysicalPath:
    vm_key: str | None
    hypervisor_key: str | None
    server_key: str | None
    rack_id: str | None
    room_id: str | None
    site_code: str | None

    @classmethod
    def create(
        cls,
        vm_key: str | None = None,
        hypervisor_key: str | None = None,
        server_key: str | None = None,
        rack_id: str | None = None,
        room_id: str | None = None,
        site_code: str | None = None,
    ) -> Self:
        normalized = cls(
            KubernetesTopologyValidator.optional_token(vm_key, "VM key"),
            KubernetesTopologyValidator.optional_token(hypervisor_key, "hypervisor key"),
            KubernetesTopologyValidator.optional_token(server_key, "server key"),
            KubernetesTopologyValidator.optional_token(rack_id, "rack id"),
            KubernetesTopologyValidator.optional_token(room_id, "room id"),
            KubernetesTopologyValidator.optional_token(site_code, "site code", 64),
        )
        if normalized.rack_id and not normalized.site_code:
            raise ValidationError("Kubernetes physical path with a rack requires a site_code")
        if normalized.room_id and not normalized.site_code:
            raise ValidationError("Kubernetes physical path with a room requires a site_code")
        return normalized

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> Self | None:
        if not payload:
            return None
        return cls.create(
            vm_key=str(payload.get("vm_key") or "") or None,
            hypervisor_key=str(payload.get("hypervisor_key") or "") or None,
            server_key=str(payload.get("server_key") or "") or None,
            rack_id=str(payload.get("rack_id") or "") or None,
            room_id=str(payload.get("room_id") or "") or None,
            site_code=str(payload.get("site_code") or "") or None,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "vm_key": self.vm_key,
            "hypervisor_key": self.hypervisor_key,
            "server_key": self.server_key,
            "rack_id": self.rack_id,
            "room_id": self.room_id,
            "site_code": self.site_code,
        }


@dataclass(frozen=True, slots=True)
class KubernetesResource:
    kind: KubernetesResourceKind
    uid: str
    name: str
    namespace: str | None
    node_name: str | None
    owner_uid: str | None
    target_uids: tuple[str, ...]
    labels: dict[str, str]
    attributes: dict[str, Any]
    physical_path: KubernetesPhysicalPath | None

    @classmethod
    def create(
        cls,
        kind: str,
        uid: str,
        name: str,
        namespace: str | None = None,
        node_name: str | None = None,
        owner_uid: str | None = None,
        target_uids: tuple[str, ...] = (),
        labels: dict[str, str] | None = None,
        attributes: dict[str, Any] | None = None,
        physical_path: KubernetesPhysicalPath | None = None,
    ) -> Self:
        normalized_kind = KubernetesResourceKind.from_value(kind)
        normalized_namespace = (
            KubernetesTopologyValidator.name(namespace, "namespace") if namespace else None
        )
        normalized_node_name = (
            KubernetesTopologyValidator.name(node_name, "node_name") if node_name else None
        )
        if normalized_kind is KubernetesResourceKind.NAMESPACE and normalized_namespace is not None:
            raise ValidationError("namespace resources must not define namespace")
        if normalized_kind is KubernetesResourceKind.NODE and normalized_namespace is not None:
            raise ValidationError("node resources must not define namespace")
        if (
            normalized_kind not in {KubernetesResourceKind.NAMESPACE, KubernetesResourceKind.NODE}
            and normalized_namespace is None
        ):
            raise ValidationError(f"{normalized_kind.value} requires a namespace")
        if normalized_node_name is not None and normalized_kind is not KubernetesResourceKind.POD:
            raise ValidationError("node_name is only valid for Kubernetes pods")
        if physical_path is not None and normalized_kind is not KubernetesResourceKind.NODE:
            raise ValidationError("physical_path is only valid for Kubernetes nodes")
        targets = tuple(
            sorted(
                {
                    KubernetesTopologyValidator.token(item, "target uid", 255)
                    for item in target_uids
                    if item.strip()
                }
            )
        )
        if len(targets) > 1024:
            raise ValidationError("Kubernetes resource target_uids cannot exceed 1024 entries")
        return cls(
            kind=normalized_kind,
            uid=KubernetesTopologyValidator.token(uid, "resource uid", 255),
            name=KubernetesTopologyValidator.name(name, "resource name"),
            namespace=normalized_namespace,
            node_name=normalized_node_name,
            owner_uid=KubernetesTopologyValidator.optional_token(owner_uid, "owner uid", 255),
            target_uids=targets,
            labels=KubernetesTopologyValidator.labels(labels or {}),
            attributes=KubernetesTopologyValidator.json_object(
                attributes or {}, "resource attributes"
            ),
            physical_path=physical_path,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        raw_targets = payload.get("target_uids") or []
        if not isinstance(raw_targets, list):
            raise ValidationError("target_uids must be a JSON array")
        raw_labels = payload.get("labels") or {}
        raw_attributes = payload.get("attributes") or {}
        raw_path = payload.get("physical_path")
        if not isinstance(raw_labels, dict) or not isinstance(raw_attributes, dict):
            raise ValidationError("labels and attributes must be JSON objects")
        if raw_path is not None and not isinstance(raw_path, dict):
            raise ValidationError("physical_path must be a JSON object")
        return cls.create(
            kind=str(payload.get("kind") or ""),
            uid=str(payload.get("uid") or ""),
            name=str(payload.get("name") or ""),
            namespace=str(payload.get("namespace") or "") or None,
            node_name=str(payload.get("node_name") or "") or None,
            owner_uid=str(payload.get("owner_uid") or "") or None,
            target_uids=tuple(str(item) for item in raw_targets),
            labels={str(key): str(value) for key, value in raw_labels.items()},
            attributes=cast(dict[str, Any], raw_attributes),
            physical_path=KubernetesPhysicalPath.from_dict(cast(dict[str, Any] | None, raw_path)),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "uid": self.uid,
            "name": self.name,
            "namespace": self.namespace,
            "node_name": self.node_name,
            "owner_uid": self.owner_uid,
            "target_uids": list(self.target_uids),
            "labels": self.labels,
            "attributes": self.attributes,
            "physical_path": None if self.physical_path is None else self.physical_path.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class KubernetesTopologyEdge:
    source: str
    target: str
    relation: str
    external: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "external": self.external,
        }


@dataclass(frozen=True, slots=True)
class KubernetesTopologySnapshot:
    id: EntityId
    tenant_id: TenantId
    cluster_key: str
    cluster_name: str
    provider: str
    kubernetes_version: str
    region: str | None
    site_code: str | None
    source_ref: str
    observed_at: datetime
    imported_at: datetime
    resources: tuple[KubernetesResource, ...]
    fingerprint: str

    _MAX_RESOURCES = 50_000

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        cluster_key: str,
        cluster_name: str,
        provider: str,
        kubernetes_version: str,
        source_ref: str,
        observed_at: datetime,
        resources: tuple[KubernetesResource, ...],
        region: str | None = None,
        site_code: str | None = None,
    ) -> Self:
        imported_at = datetime.now(UTC)
        normalized_resources = cls._validate_resources(resources)
        normalized_cluster_key = KubernetesTopologyValidator.token(cluster_key, "cluster key", 255)
        normalized_cluster_name = KubernetesTopologyValidator.name(cluster_name, "cluster name")
        normalized_provider = KubernetesTopologyValidator.token(provider, "provider", 64)
        normalized_version = KubernetesTopologyValidator.token(
            kubernetes_version, "Kubernetes version", 64
        )
        normalized_source = KubernetesTopologyValidator.token(source_ref, "source reference", 255)
        normalized_observed = KubernetesTopologyValidator.aware_datetime(observed_at, "observed_at")
        normalized_region = KubernetesTopologyValidator.optional_token(region, "region", 128)
        normalized_site = KubernetesTopologyValidator.optional_token(site_code, "site code", 64)
        cls._validate_references(normalized_resources)
        payload = cls._fingerprint_payload(
            normalized_cluster_key,
            normalized_cluster_name,
            normalized_provider,
            normalized_version,
            normalized_region,
            normalized_site,
            normalized_source,
            normalized_observed,
            normalized_resources,
        )
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            cluster_key=normalized_cluster_key,
            cluster_name=normalized_cluster_name,
            provider=normalized_provider,
            kubernetes_version=normalized_version,
            region=normalized_region,
            site_code=normalized_site,
            source_ref=normalized_source,
            observed_at=normalized_observed,
            imported_at=imported_at,
            resources=normalized_resources,
            fingerprint=KubernetesTopologyValidator.digest(payload),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        cluster_key: str,
        cluster_name: str,
        provider: str,
        kubernetes_version: str,
        source_ref: str,
        observed_at: datetime,
        imported_at: datetime,
        resources: tuple[KubernetesResource, ...],
        fingerprint: str,
        region: str | None = None,
        site_code: str | None = None,
    ) -> Self:
        candidate = cls.create(
            tenant_id=tenant_id,
            cluster_key=cluster_key,
            cluster_name=cluster_name,
            provider=provider,
            kubernetes_version=kubernetes_version,
            source_ref=source_ref,
            observed_at=observed_at,
            resources=resources,
            region=region,
            site_code=site_code,
        )
        normalized_imported = KubernetesTopologyValidator.aware_datetime(imported_at, "imported_at")
        normalized_fingerprint = fingerprint.strip().lower()
        if normalized_fingerprint != candidate.fingerprint:
            raise ValidationError("Kubernetes topology snapshot fingerprint mismatch")
        return cls(
            id=id,
            tenant_id=tenant_id,
            cluster_key=candidate.cluster_key,
            cluster_name=candidate.cluster_name,
            provider=candidate.provider,
            kubernetes_version=candidate.kubernetes_version,
            region=candidate.region,
            site_code=candidate.site_code,
            source_ref=candidate.source_ref,
            observed_at=candidate.observed_at,
            imported_at=normalized_imported,
            resources=candidate.resources,
            fingerprint=candidate.fingerprint,
        )

    @classmethod
    def _validate_resources(
        cls, resources: tuple[KubernetesResource, ...]
    ) -> tuple[KubernetesResource, ...]:
        if not resources:
            raise ValidationError("Kubernetes topology snapshot requires resources")
        if len(resources) > cls._MAX_RESOURCES:
            raise ValidationError(
                f"Kubernetes topology snapshot cannot exceed {cls._MAX_RESOURCES} resources"
            )
        by_uid: set[str] = set()
        by_identity: set[tuple[str, str | None, str]] = set()
        ordered = sorted(
            resources, key=lambda item: (item.kind.value, item.namespace or "", item.name, item.uid)
        )
        for resource in ordered:
            if resource.uid in by_uid:
                raise ValidationError(f"duplicate Kubernetes resource uid: {resource.uid}")
            identity = (resource.kind.value, resource.namespace, resource.name)
            if identity in by_identity:
                raise ValidationError(
                    "duplicate Kubernetes resource identity: "
                    f"{resource.kind.value}/{resource.namespace or '-'}:{resource.name}"
                )
            by_uid.add(resource.uid)
            by_identity.add(identity)
        return tuple(ordered)

    @staticmethod
    def _validate_references(resources: tuple[KubernetesResource, ...]) -> None:
        by_uid = {item.uid: item for item in resources}
        namespaces = {
            item.name for item in resources if item.kind is KubernetesResourceKind.NAMESPACE
        }
        nodes = {item.name for item in resources if item.kind is KubernetesResourceKind.NODE}
        target_kinds = {
            KubernetesResourceKind.SERVICE: {
                KubernetesResourceKind.WORKLOAD,
                KubernetesResourceKind.POD,
            },
            KubernetesResourceKind.INGRESS: {KubernetesResourceKind.SERVICE},
            KubernetesResourceKind.NETWORK_POLICY: {
                KubernetesResourceKind.WORKLOAD,
                KubernetesResourceKind.POD,
            },
            KubernetesResourceKind.VOLUME: {KubernetesResourceKind.POD},
        }
        for item in resources:
            if item.namespace is not None and item.namespace not in namespaces:
                raise ValidationError(f"unknown Kubernetes namespace reference: {item.namespace}")
            if item.node_name is not None and item.node_name not in nodes:
                raise ValidationError(f"unknown Kubernetes node reference: {item.node_name}")
            if item.owner_uid is not None:
                owner = by_uid.get(item.owner_uid)
                if owner is None:
                    raise ValidationError(f"unknown Kubernetes owner uid: {item.owner_uid}")
                if owner.uid == item.uid:
                    raise ValidationError("Kubernetes resource cannot own itself")
                if item.namespace is not None and owner.namespace not in {None, item.namespace}:
                    raise ValidationError("Kubernetes owner reference cannot cross namespaces")
            allowed_targets = target_kinds.get(item.kind)
            if item.target_uids and allowed_targets is None:
                raise ValidationError(f"{item.kind.value} does not support target_uids")
            for target_uid in item.target_uids:
                target = by_uid.get(target_uid)
                if target is None:
                    raise ValidationError(f"unknown Kubernetes target uid: {target_uid}")
                if target.uid == item.uid:
                    raise ValidationError("Kubernetes resource cannot target itself")
                if allowed_targets is not None and target.kind not in allowed_targets:
                    expected = ", ".join(sorted(kind.value for kind in allowed_targets))
                    raise ValidationError(f"{item.kind.value} target must be one of: {expected}")
                if item.namespace is not None and target.namespace != item.namespace:
                    raise ValidationError("Kubernetes target reference cannot cross namespaces")

    @staticmethod
    def _fingerprint_payload(
        cluster_key: str,
        cluster_name: str,
        provider: str,
        kubernetes_version: str,
        region: str | None,
        site_code: str | None,
        source_ref: str,
        observed_at: datetime,
        resources: tuple[KubernetesResource, ...],
    ) -> dict[str, object]:
        return {
            "cluster_key": cluster_key,
            "cluster_name": cluster_name,
            "provider": provider,
            "kubernetes_version": kubernetes_version,
            "region": region,
            "site_code": site_code,
            "source_ref": source_ref,
            "observed_at": observed_at.isoformat(),
            "resources": [item.as_dict() for item in resources],
        }

    def summary(self) -> dict[str, object]:
        counts = {kind.value: 0 for kind in KubernetesResourceKind}
        mapped_nodes = 0
        for resource in self.resources:
            counts[resource.kind.value] += 1
            if resource.kind is KubernetesResourceKind.NODE and resource.physical_path is not None:
                mapped_nodes += 1
        nodes = counts[KubernetesResourceKind.NODE.value]
        return {
            "cluster_key": self.cluster_key,
            "resource_count": len(self.resources),
            "counts": counts,
            "mapped_nodes": mapped_nodes,
            "mapping_coverage_percent": 100.0
            if nodes == 0
            else round((mapped_nodes / nodes) * 100.0, 2),
        }

    def topology_edges(self) -> tuple[KubernetesTopologyEdge, ...]:
        edges: set[tuple[str, str, str, bool]] = set()
        cluster_node = f"cluster:{self.cluster_key}"
        by_uid = {item.uid: item for item in self.resources}
        by_node_name = {
            item.name: item for item in self.resources if item.kind is KubernetesResourceKind.NODE
        }
        by_namespace_name = {
            item.name: item
            for item in self.resources
            if item.kind is KubernetesResourceKind.NAMESPACE
        }
        for item in self.resources:
            item_node = f"k8s:{item.uid}"
            if item.kind in {KubernetesResourceKind.NAMESPACE, KubernetesResourceKind.NODE}:
                edges.add((cluster_node, item_node, "contains", False))
            if item.namespace is not None:
                namespace = by_namespace_name[item.namespace]
                edges.add((f"k8s:{namespace.uid}", item_node, "contains", False))
            if item.owner_uid is not None:
                edges.add((f"k8s:{item.owner_uid}", item_node, "owns", False))
            if item.node_name is not None:
                node = by_node_name[item.node_name]
                edges.add((f"k8s:{node.uid}", item_node, "hosts", False))
            for target_uid in item.target_uids:
                target_resource = by_uid[target_uid]
                relation = {
                    KubernetesResourceKind.SERVICE: "routes-to",
                    KubernetesResourceKind.INGRESS: "publishes",
                    KubernetesResourceKind.NETWORK_POLICY: "governs",
                    KubernetesResourceKind.VOLUME: "mounted-by",
                }.get(item.kind, "relates-to")
                edges.add((item_node, f"k8s:{target_resource.uid}", relation, False))
            if item.physical_path is not None:
                previous = item_node
                for relation, physical_target in (
                    ("runs-on-vm", item.physical_path.vm_key),
                    ("hosted-by-hypervisor", item.physical_path.hypervisor_key),
                    ("hosted-by-server", item.physical_path.server_key),
                    ("located-in-rack", item.physical_path.rack_id),
                    ("located-in-room", item.physical_path.room_id),
                    ("located-in-site", item.physical_path.site_code),
                ):
                    if physical_target is not None:
                        external_target = f"rsot:{physical_target}"
                        edges.add((previous, external_target, relation, True))
                        previous = external_target
        return tuple(
            KubernetesTopologyEdge(source, target, relation, external)
            for source, target, relation, external in sorted(edges)
        )

    def topology(self) -> dict[str, object]:
        return {
            "snapshot_id": self.id.value,
            "cluster": {
                "key": self.cluster_key,
                "name": self.cluster_name,
                "provider": self.provider,
                "kubernetes_version": self.kubernetes_version,
                "region": self.region,
                "site_code": self.site_code,
            },
            "summary": self.summary(),
            "resources": [item.as_dict() for item in self.resources],
            "edges": [edge.as_dict() for edge in self.topology_edges()],
            "fingerprint": self.fingerprint,
        }

    def as_dict(self, include_resources: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "cluster_key": self.cluster_key,
            "cluster_name": self.cluster_name,
            "provider": self.provider,
            "kubernetes_version": self.kubernetes_version,
            "region": self.region,
            "site_code": self.site_code,
            "source_ref": self.source_ref,
            "observed_at": self.observed_at.isoformat(),
            "imported_at": self.imported_at.isoformat(),
            "fingerprint": self.fingerprint,
            "summary": self.summary(),
        }
        if include_resources:
            payload["resources"] = [item.as_dict() for item in self.resources]
        return payload
