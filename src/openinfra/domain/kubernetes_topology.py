from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self, cast

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.kubernetes_security import KubernetesImageReference, KubernetesSecretReference
from openinfra.domain.source_of_truth import SourceObjectKey


class KubernetesResourceKind(StrEnum):
    NAMESPACE = "namespace"
    NODE = "node"
    WORKLOAD = "workload"
    POD = "pod"
    SERVICE = "service"
    INGRESS = "ingress"
    LOAD_BALANCER = "load-balancer"
    DNS_RECORD = "dns-record"
    MESH_ROUTE = "mesh-route"
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
            "loadbalancer": cls.LOAD_BALANCER.value,
            "load-balancer": cls.LOAD_BALANCER.value,
            "dnsrecord": cls.DNS_RECORD.value,
            "dns-record": cls.DNS_RECORD.value,
            "virtualservice": cls.MESH_ROUTE.value,
            "httproute": cls.MESH_ROUTE.value,
            "mesh-route": cls.MESH_ROUTE.value,
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

    @classmethod
    def exposure_attributes(
        cls, kind: KubernetesResourceKind, value: dict[str, Any]
    ) -> dict[str, Any]:
        normalized = cls.json_object(value, "resource attributes")
        exposure_kinds = {
            KubernetesResourceKind.SERVICE,
            KubernetesResourceKind.INGRESS,
            KubernetesResourceKind.LOAD_BALANCER,
            KubernetesResourceKind.DNS_RECORD,
            KubernetesResourceKind.MESH_ROUTE,
        }
        result = dict(normalized)
        if kind not in exposure_kinds:
            if "capacity" in result:
                result["capacity"] = cls.capacity_attributes(kind, result["capacity"])
            return dict(sorted(result.items()))
        if "scope" in result:
            scope = str(result["scope"]).strip().lower()
            if scope not in {"cluster", "internal", "external"}:
                raise ValidationError(
                    "Kubernetes exposure scope must be cluster, internal or external"
                )
            result["scope"] = scope
        for key in ("hosts",):
            if key in result:
                result[key] = cls._string_array(
                    result[key], key, lambda item, label=key: cls.name(item, label), maximum=128
                )
        for key in ("addresses", "cluster_ips", "external_ips"):
            if key in result:
                result[key] = cls._string_array(result[key], key, cls._ip_address, maximum=128)
        if "ports" in result:
            result["ports"] = cls._ports(result["ports"])
        if "rsot_object_keys" in result:
            result["rsot_object_keys"] = cls._string_array(
                result["rsot_object_keys"],
                "rsot_object_keys",
                lambda item: SourceObjectKey.from_value(item).value,
                maximum=128,
            )
        if "external_name" in result:
            result["external_name"] = cls.name(str(result["external_name"]), "external_name")
        if "service_type" in result:
            service_type = (
                str(result["service_type"]).strip().lower().replace("_", "").replace("-", "")
            )
            aliases = {
                "clusterip": "cluster-ip",
                "nodeport": "node-port",
                "loadbalancer": "load-balancer",
                "externalname": "external-name",
            }
            if service_type not in aliases:
                raise ValidationError(
                    "service_type must be ClusterIP, NodePort, LoadBalancer or ExternalName"
                )
            result["service_type"] = aliases[service_type]
        if "scheme" in result:
            scheme = str(result["scheme"]).strip().lower().replace("_", "-")
            if scheme not in {"internal", "internet-facing"}:
                raise ValidationError("load balancer scheme must be internal or internet-facing")
            result["scheme"] = scheme
        if "tls" in result and not isinstance(result["tls"], bool):
            raise ValidationError("tls must be a boolean")
        if "mesh" in result:
            result["mesh"] = cls.token(str(result["mesh"]), "service mesh", 64)
        if "protocol" in result:
            protocol = str(result["protocol"]).strip().lower()
            if protocol not in {"http", "https", "http2", "grpc", "tcp", "tls"}:
                raise ValidationError("service mesh protocol is unsupported")
            result["protocol"] = protocol
        if kind is KubernetesResourceKind.DNS_RECORD:
            record_type = str(result.get("record_type", "")).strip().upper()
            if record_type not in {"A", "AAAA", "CNAME"}:
                raise ValidationError("DNS record_type must be A, AAAA or CNAME")
            raw_values = result.get("values")
            if record_type in {"A", "AAAA"}:
                values = cls._string_array(
                    raw_values, "DNS record values", cls._ip_address, maximum=128
                )
                expected_version = 4 if record_type == "A" else 6
                if any(ipaddress.ip_address(item).version != expected_version for item in values):
                    raise ValidationError(
                        f"DNS {record_type} record contains an incompatible address"
                    )
            else:
                values = cls._string_array(
                    raw_values,
                    "DNS record values",
                    lambda item: cls.name(item, "DNS target"),
                    maximum=128,
                )
            if not values:
                raise ValidationError("DNS record values cannot be empty")
            ttl = int(result.get("ttl", 300))
            if not 1 <= ttl <= 86_400:
                raise ValidationError("DNS ttl must be between 1 and 86400 seconds")
            result["record_type"] = record_type
            result["values"] = values
            result["ttl"] = ttl
        if "capacity" in result:
            result["capacity"] = cls.capacity_attributes(kind, result["capacity"])
        return dict(sorted(result.items()))

    @classmethod
    def capacity_attributes(cls, kind: KubernetesResourceKind, value: Any) -> dict[str, int]:
        if not isinstance(value, dict):
            raise ValidationError("capacity must be a JSON object")
        allowed_by_kind = {
            KubernetesResourceKind.NODE: {
                "cpu_capacity_millicores",
                "memory_capacity_bytes",
                "storage_capacity_bytes",
            },
            KubernetesResourceKind.POD: {
                "cpu_request_millicores",
                "cpu_limit_millicores",
                "cpu_usage_millicores",
                "memory_request_bytes",
                "memory_limit_bytes",
                "memory_usage_bytes",
            },
            KubernetesResourceKind.VOLUME: {
                "storage_request_bytes",
                "storage_limit_bytes",
                "storage_usage_bytes",
                "storage_capacity_bytes",
            },
        }
        allowed = allowed_by_kind.get(kind)
        if allowed is None:
            raise ValidationError("capacity metrics are only valid for nodes, pods and volumes")
        unknown = sorted({str(key) for key in value} - allowed)
        if unknown:
            raise ValidationError(f"unsupported Kubernetes capacity metric: {unknown[0]}")
        normalized: dict[str, int] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if isinstance(raw_value, bool):
                raise ValidationError(f"{key} must be a non-negative integer")
            try:
                number = int(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{key} must be a non-negative integer") from exc
            if number < 0 or number > 9_223_372_036_854_775_807:
                raise ValidationError(f"{key} must be between 0 and 9223372036854775807")
            normalized[key] = number
        for prefix in ("cpu", "memory", "storage"):
            request = normalized.get(
                f"{prefix}_request_{'millicores' if prefix == 'cpu' else 'bytes'}"
            )
            limit = normalized.get(f"{prefix}_limit_{'millicores' if prefix == 'cpu' else 'bytes'}")
            if request is not None and limit is not None and request > limit:
                raise ValidationError(f"{prefix} request cannot exceed limit")
        return dict(sorted(normalized.items()))

    @classmethod
    def _string_array(
        cls,
        value: Any,
        label: str,
        normalizer: Any,
        maximum: int,
    ) -> list[str]:
        if not isinstance(value, list):
            raise ValidationError(f"{label} must be a JSON array")
        if len(value) > maximum:
            raise ValidationError(f"{label} cannot exceed {maximum} entries")
        return sorted({normalizer(str(item)) for item in value})

    @staticmethod
    def _ip_address(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ValidationError("Kubernetes exposure address is invalid") from exc

    @classmethod
    def _ports(cls, value: Any) -> list[dict[str, object]]:
        if not isinstance(value, list):
            raise ValidationError("ports must be a JSON array")
        if len(value) > 128:
            raise ValidationError("ports cannot exceed 128 entries")
        normalized: dict[tuple[int, str, str], dict[str, object]] = {}
        for raw in value:
            if not isinstance(raw, dict):
                raise ValidationError("each port must be a JSON object")
            raw_port = raw.get("port")
            try:
                port = int(str(raw_port))
            except (TypeError, ValueError) as exc:
                raise ValidationError("port must be an integer") from exc
            if not 1 <= port <= 65_535:
                raise ValidationError("port must be between 1 and 65535")
            protocol = str(raw.get("protocol", "tcp")).strip().lower()
            if protocol not in {"tcp", "udp", "sctp", "http", "https", "http2", "grpc", "tls"}:
                raise ValidationError("Kubernetes exposure port protocol is unsupported")
            name = str(raw.get("name", "")).strip().lower()
            if name:
                name = cls.token(name, "port name", 64)
            entry = {"port": port, "protocol": protocol}
            if name:
                entry["name"] = name
            normalized[(port, protocol, name)] = entry
        return [normalized[key] for key in sorted(normalized)]

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
    images: tuple[KubernetesImageReference, ...]
    certificate_fingerprints: tuple[str, ...]
    secret_refs: tuple[KubernetesSecretReference, ...]
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
        images: tuple[KubernetesImageReference, ...] = (),
        certificate_fingerprints: tuple[str, ...] = (),
        secret_refs: tuple[KubernetesSecretReference, ...] = (),
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
        normalized_images = tuple(
            sorted(
                set(images),
                key=lambda item: (item.reference, item.digest or "", item.sbom_document_ids),
            )
        )
        if len(normalized_images) > 64:
            raise ValidationError("Kubernetes resource images cannot exceed 64 entries")
        if normalized_images and normalized_kind not in {
            KubernetesResourceKind.WORKLOAD,
            KubernetesResourceKind.POD,
        }:
            raise ValidationError("Kubernetes images are only valid for workloads and pods")
        normalized_certificates = tuple(
            sorted({cls._certificate_fingerprint(item) for item in certificate_fingerprints})
        )
        if len(normalized_certificates) > 64:
            raise ValidationError("Kubernetes certificate references cannot exceed 64 entries")
        certificate_kinds = {
            KubernetesResourceKind.WORKLOAD,
            KubernetesResourceKind.POD,
            KubernetesResourceKind.SERVICE,
            KubernetesResourceKind.INGRESS,
            KubernetesResourceKind.LOAD_BALANCER,
            KubernetesResourceKind.MESH_ROUTE,
        }
        if normalized_certificates and normalized_kind not in certificate_kinds:
            raise ValidationError(
                "certificate references are unsupported for this Kubernetes resource kind"
            )
        normalized_secrets = tuple(
            sorted(set(secret_refs), key=lambda item: (item.provider, item.reference_hash))
        )
        if len(normalized_secrets) > 64:
            raise ValidationError("Kubernetes secret references cannot exceed 64 entries")
        secret_kinds = {
            KubernetesResourceKind.WORKLOAD,
            KubernetesResourceKind.POD,
            KubernetesResourceKind.SERVICE,
            KubernetesResourceKind.INGRESS,
            KubernetesResourceKind.MESH_ROUTE,
        }
        if normalized_secrets and normalized_kind not in secret_kinds:
            raise ValidationError(
                "secret references are unsupported for this Kubernetes resource kind"
            )
        return cls(
            kind=normalized_kind,
            uid=KubernetesTopologyValidator.token(uid, "resource uid", 255),
            name=KubernetesTopologyValidator.name(name, "resource name"),
            namespace=normalized_namespace,
            node_name=normalized_node_name,
            owner_uid=KubernetesTopologyValidator.optional_token(owner_uid, "owner uid", 255),
            target_uids=targets,
            labels=KubernetesTopologyValidator.labels(labels or {}),
            attributes=KubernetesTopologyValidator.exposure_attributes(
                normalized_kind, attributes or {}
            ),
            images=normalized_images,
            certificate_fingerprints=normalized_certificates,
            secret_refs=normalized_secrets,
            physical_path=physical_path,
        )

    @staticmethod
    def _certificate_fingerprint(value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValidationError("Kubernetes certificate fingerprint must be a SHA-256 digest")
        return normalized

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        raw_targets = payload.get("target_uids") or []
        if not isinstance(raw_targets, list):
            raise ValidationError("target_uids must be a JSON array")
        raw_labels = payload.get("labels") or {}
        raw_attributes = payload.get("attributes") or {}
        raw_images = payload.get("images") or []
        raw_certificates = payload.get("certificate_fingerprints") or []
        raw_secret_refs = payload.get("secret_refs") or []
        raw_path = payload.get("physical_path")
        if not isinstance(raw_labels, dict) or not isinstance(raw_attributes, dict):
            raise ValidationError("labels and attributes must be JSON objects")
        if not isinstance(raw_images, list):
            raise ValidationError("images must be a JSON array")
        if not isinstance(raw_certificates, list):
            raise ValidationError("certificate_fingerprints must be a JSON array")
        if not isinstance(raw_secret_refs, list):
            raise ValidationError("secret_refs must be a JSON array")
        if raw_path is not None and not isinstance(raw_path, dict):
            raise ValidationError("physical_path must be a JSON object")
        images: list[KubernetesImageReference] = []
        for item in raw_images:
            if not isinstance(item, dict):
                raise ValidationError("each Kubernetes image reference must be a JSON object")
            images.append(KubernetesImageReference.from_dict(cast(dict[str, Any], item)))
        secret_refs: list[KubernetesSecretReference] = []
        for item in raw_secret_refs:
            if isinstance(item, str):
                secret_refs.append(KubernetesSecretReference.create(item))
            elif isinstance(item, dict):
                secret_refs.append(KubernetesSecretReference.from_dict(cast(dict[str, Any], item)))
            else:
                raise ValidationError(
                    "each Kubernetes secret reference must be a string or JSON object"
                )
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
            images=tuple(images),
            certificate_fingerprints=tuple(str(item) for item in raw_certificates),
            secret_refs=tuple(secret_refs),
            physical_path=KubernetesPhysicalPath.from_dict(cast(dict[str, Any] | None, raw_path)),
        )

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
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
        if self.images:
            payload["images"] = [item.as_dict() for item in self.images]
        if self.certificate_fingerprints:
            payload["certificate_fingerprints"] = list(self.certificate_fingerprints)
        if self.secret_refs:
            payload["secret_refs"] = [item.as_dict() for item in self.secret_refs]
        return payload


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
            KubernetesResourceKind.LOAD_BALANCER: {
                KubernetesResourceKind.INGRESS,
                KubernetesResourceKind.SERVICE,
            },
            KubernetesResourceKind.DNS_RECORD: {
                KubernetesResourceKind.INGRESS,
                KubernetesResourceKind.LOAD_BALANCER,
                KubernetesResourceKind.SERVICE,
            },
            KubernetesResourceKind.MESH_ROUTE: {
                KubernetesResourceKind.SERVICE,
                KubernetesResourceKind.WORKLOAD,
                KubernetesResourceKind.POD,
            },
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
            KubernetesTopologySnapshot._validate_exposure_resource(item)

    @staticmethod
    def _validate_exposure_resource(item: KubernetesResource) -> None:
        attributes = item.attributes
        if item.kind is KubernetesResourceKind.LOAD_BALANCER:
            if not item.target_uids:
                raise ValidationError("load-balancer requires at least one target_uids entry")
            if not attributes.get("addresses") and not attributes.get("hosts"):
                raise ValidationError("load-balancer requires addresses or hosts")
            if attributes.get("scope") not in {"internal", "external"}:
                raise ValidationError("load-balancer requires an internal or external scope")
        elif item.kind is KubernetesResourceKind.DNS_RECORD:
            if not item.target_uids:
                raise ValidationError("dns-record requires at least one target_uids entry")
            if attributes.get("scope") not in {"internal", "external"}:
                raise ValidationError("dns-record requires an internal or external scope")
        elif item.kind is KubernetesResourceKind.MESH_ROUTE:
            if not item.target_uids:
                raise ValidationError("mesh-route requires at least one target_uids entry")
            if not attributes.get("mesh"):
                raise ValidationError("mesh-route requires a mesh attribute")
            if not attributes.get("hosts"):
                raise ValidationError("mesh-route requires at least one host")
            if attributes.get("scope") not in {"internal", "external"}:
                raise ValidationError("mesh-route requires an internal or external scope")
        elif item.kind is KubernetesResourceKind.INGRESS and attributes:
            exposure_keys = {"scope", "hosts", "addresses", "ports", "rsot_object_keys", "tls"}
            if exposure_keys.intersection(attributes):
                if not attributes.get("hosts") and not attributes.get("addresses"):
                    raise ValidationError("ingress exposure metadata requires hosts or addresses")
                if attributes.get("scope") not in {"internal", "external"}:
                    raise ValidationError(
                        "ingress exposure metadata requires internal or external scope"
                    )

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
                    KubernetesResourceKind.LOAD_BALANCER: "forwards-to",
                    KubernetesResourceKind.DNS_RECORD: "resolves-to",
                    KubernetesResourceKind.MESH_ROUTE: "routes-to",
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
