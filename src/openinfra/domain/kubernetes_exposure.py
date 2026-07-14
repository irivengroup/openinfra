from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.flow_matrix import (
    FlowDecision,
    FlowDeclaration,
    FlowProtocol,
    FlowSelectorKind,
)
from openinfra.domain.kubernetes_topology import (
    KubernetesResource,
    KubernetesResourceKind,
    KubernetesTopologySnapshot,
    KubernetesTopologyValidator,
)
from openinfra.domain.source_of_truth import SourceOfTruthObject, SourceRelation


class KubernetesExposureScope(StrEnum):
    CLUSTER = "cluster"
    INTERNAL = "internal"
    EXTERNAL = "external"

    @classmethod
    def from_value(cls, value: str) -> Self:
        return cls(value.strip().lower())


@dataclass(frozen=True, slots=True)
class KubernetesExposureEndpoint:
    resource_uid: str
    endpoint_kind: str
    value: str
    scope: KubernetesExposureScope
    protocol: str | None
    port: int | None

    @property
    def key(self) -> str:
        protocol = self.protocol or "any"
        port = self.port or 0
        return f"endpoint:{self.endpoint_kind}:{self.value}:{protocol}:{port}"

    @property
    def ip_value(self) -> str | None:
        if self.endpoint_kind != "ip":
            return None
        return self.value

    @property
    def transport_protocol(self) -> str | None:
        if self.protocol is None:
            return None
        if self.protocol in {"http", "https", "http2", "grpc", "tls"}:
            return "tcp"
        return self.protocol

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "resource_uid": self.resource_uid,
            "endpoint_kind": self.endpoint_kind,
            "value": self.value,
            "scope": self.scope.value,
            "protocol": self.protocol,
            "transport_protocol": self.transport_protocol,
            "port": self.port,
        }


@dataclass(frozen=True, slots=True)
class KubernetesExposureResource:
    uid: str
    kind: KubernetesResourceKind
    name: str
    namespace: str
    scope: KubernetesExposureScope
    target_uids: tuple[str, ...]
    endpoints: tuple[KubernetesExposureEndpoint, ...]
    rsot_object_keys: tuple[str, ...]

    @classmethod
    def from_resource(cls, resource: KubernetesResource) -> Self | None:
        supported = {
            KubernetesResourceKind.SERVICE,
            KubernetesResourceKind.INGRESS,
            KubernetesResourceKind.LOAD_BALANCER,
            KubernetesResourceKind.DNS_RECORD,
            KubernetesResourceKind.MESH_ROUTE,
        }
        if resource.kind not in supported or resource.namespace is None:
            return None
        attributes = resource.attributes
        scope = cls._scope(resource)
        ports = cls._ports(attributes)
        values: set[tuple[str, str, KubernetesExposureScope]] = set()

        for host in cls._strings(attributes.get("hosts")):
            values.add(("hostname", host, scope))
        for address in cls._strings(attributes.get("addresses")):
            values.add(("ip", address, scope))
        if resource.kind is KubernetesResourceKind.SERVICE:
            for address in cls._strings(attributes.get("cluster_ips")):
                values.add(("ip", address, KubernetesExposureScope.CLUSTER))
            for address in cls._strings(attributes.get("external_ips")):
                values.add(("ip", address, KubernetesExposureScope.EXTERNAL))
            external_name = str(attributes.get("external_name") or "")
            if external_name:
                values.add(("hostname", external_name, KubernetesExposureScope.EXTERNAL))
        if resource.kind is KubernetesResourceKind.DNS_RECORD:
            record_type = str(attributes.get("record_type", ""))
            endpoint_kind = "hostname" if record_type == "CNAME" else "ip"
            for value in cls._strings(attributes.get("values")):
                values.add((endpoint_kind, value, scope))

        endpoints: set[KubernetesExposureEndpoint] = set()
        for endpoint_kind, value, endpoint_scope in values:
            if ports:
                for protocol, port in ports:
                    endpoints.add(
                        KubernetesExposureEndpoint(
                            resource.uid,
                            endpoint_kind,
                            value,
                            endpoint_scope,
                            protocol,
                            port,
                        )
                    )
            else:
                endpoints.add(
                    KubernetesExposureEndpoint(
                        resource.uid,
                        endpoint_kind,
                        value,
                        endpoint_scope,
                        None,
                        None,
                    )
                )
        rsot_object_keys = tuple(sorted(cls._strings(attributes.get("rsot_object_keys"))))
        return cls(
            uid=resource.uid,
            kind=resource.kind,
            name=resource.name,
            namespace=resource.namespace,
            scope=scope,
            target_uids=resource.target_uids,
            endpoints=tuple(
                sorted(
                    endpoints,
                    key=lambda item: (
                        item.scope.value,
                        item.endpoint_kind,
                        item.value,
                        item.protocol or "",
                        item.port or 0,
                    ),
                )
            ),
            rsot_object_keys=rsot_object_keys,
        )

    @staticmethod
    def _scope(resource: KubernetesResource) -> KubernetesExposureScope:
        raw = str(resource.attributes.get("scope") or "")
        if raw:
            return KubernetesExposureScope.from_value(raw)
        if resource.kind is KubernetesResourceKind.SERVICE:
            if resource.attributes.get("external_ips") or resource.attributes.get("external_name"):
                return KubernetesExposureScope.EXTERNAL
            if resource.attributes.get("cluster_ips"):
                return KubernetesExposureScope.CLUSTER
        return KubernetesExposureScope.CLUSTER

    @staticmethod
    def _strings(value: Any) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(str(item) for item in value)

    @staticmethod
    def _ports(attributes: dict[str, Any]) -> tuple[tuple[str, int], ...]:
        raw_ports = attributes.get("ports")
        if not isinstance(raw_ports, list):
            return ()
        result: list[tuple[str, int]] = []
        for item in raw_ports:
            if isinstance(item, dict):
                result.append((str(item["protocol"]), int(item["port"])))
        return tuple(sorted(set(result)))

    @property
    def external(self) -> bool:
        return self.scope is KubernetesExposureScope.EXTERNAL or any(
            item.scope is KubernetesExposureScope.EXTERNAL for item in self.endpoints
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "uid": self.uid,
            "kind": self.kind.value,
            "name": self.name,
            "namespace": self.namespace,
            "scope": self.scope.value,
            "external": self.external,
            "target_uids": list(self.target_uids),
            "rsot_object_keys": list(self.rsot_object_keys),
            "endpoints": [item.as_dict() for item in self.endpoints],
        }


@dataclass(frozen=True, slots=True)
class KubernetesFlowCorrelation:
    resource_uid: str
    declaration_code: str
    decision: FlowDecision
    destination_selector: str
    protocol: str
    destination_port_start: int | None
    destination_port_end: int | None
    matched_endpoints: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "resource_uid": self.resource_uid,
            "declaration_code": self.declaration_code,
            "decision": self.decision.value,
            "destination_selector": self.destination_selector,
            "protocol": self.protocol,
            "destination_port_start": self.destination_port_start,
            "destination_port_end": self.destination_port_end,
            "matched_endpoints": list(self.matched_endpoints),
        }


@dataclass(frozen=True, slots=True)
class KubernetesExposureReport:
    snapshot_id: str
    cluster_key: str
    fingerprint: str
    resources: tuple[KubernetesExposureResource, ...]
    flow_correlations: tuple[KubernetesFlowCorrelation, ...]
    dependency_relations: tuple[SourceRelation, ...]
    dependency_objects: tuple[SourceOfTruthObject, ...]
    graph_nodes: tuple[dict[str, object], ...]
    graph_edges: tuple[dict[str, object], ...]
    correlation_truncated: bool

    @classmethod
    def build(
        cls,
        snapshot: KubernetesTopologySnapshot,
        flow_declarations: tuple[FlowDeclaration, ...],
        dependency_relations: tuple[SourceRelation, ...],
        dependency_objects: tuple[SourceOfTruthObject, ...],
        correlation_truncated: bool = False,
    ) -> Self:
        resources = tuple(
            item
            for item in (
                KubernetesExposureResource.from_resource(resource)
                for resource in snapshot.resources
            )
            if item is not None
        )
        normalized_relations = tuple(
            sorted(
                dependency_relations,
                key=lambda item: (
                    item.source_key.value,
                    item.target_key.value,
                    item.relation_type,
                    item.id.value,
                ),
            )
        )
        normalized_objects = tuple(sorted(dependency_objects, key=lambda item: item.key.value))
        correlations = cls._flow_correlations(resources, flow_declarations)
        graph_nodes, graph_edges = cls._graph(
            snapshot,
            resources,
            correlations,
            normalized_relations,
            normalized_objects,
        )
        payload = {
            "snapshot_id": snapshot.id.value,
            "cluster_key": snapshot.cluster_key,
            "resources": [item.as_dict() for item in resources],
            "flow_correlations": [item.as_dict() for item in correlations],
            "dependency_relations": [item.as_dict() for item in normalized_relations],
            "dependency_objects": [item.as_dict() for item in normalized_objects],
            "graph_nodes": list(graph_nodes),
            "graph_edges": list(graph_edges),
            "correlation_truncated": correlation_truncated,
        }
        return cls(
            snapshot_id=snapshot.id.value,
            cluster_key=snapshot.cluster_key,
            fingerprint=KubernetesTopologyValidator.digest(payload),
            resources=resources,
            flow_correlations=correlations,
            dependency_relations=normalized_relations,
            dependency_objects=normalized_objects,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            correlation_truncated=correlation_truncated,
        )

    @staticmethod
    def _flow_correlations(
        resources: tuple[KubernetesExposureResource, ...],
        declarations: tuple[FlowDeclaration, ...],
    ) -> tuple[KubernetesFlowCorrelation, ...]:
        correlations: list[KubernetesFlowCorrelation] = []
        for resource in resources:
            if not resource.endpoints and not resource.rsot_object_keys:
                continue
            for declaration in declarations:
                matched = KubernetesExposureReport._matched_endpoints(resource, declaration)
                if not matched and not KubernetesExposureReport._object_selector_matches(
                    resource, declaration
                ):
                    continue
                ports = declaration.destination_ports
                correlations.append(
                    KubernetesFlowCorrelation(
                        resource_uid=resource.uid,
                        declaration_code=declaration.code,
                        decision=declaration.decision,
                        destination_selector=str(declaration.destination_selector),
                        protocol=declaration.protocol.value,
                        destination_port_start=None if ports is None else ports.start,
                        destination_port_end=None if ports is None else ports.end,
                        matched_endpoints=matched,
                    )
                )
        return tuple(
            sorted(
                correlations,
                key=lambda item: (
                    item.resource_uid,
                    item.declaration_code,
                    item.decision.value,
                    item.matched_endpoints,
                ),
            )
        )

    @staticmethod
    def _object_selector_matches(
        resource: KubernetesExposureResource, declaration: FlowDeclaration
    ) -> bool:
        selector = declaration.destination_selector
        return (
            selector.kind is FlowSelectorKind.OBJECT and selector.value in resource.rsot_object_keys
        )

    @staticmethod
    def _matched_endpoints(
        resource: KubernetesExposureResource, declaration: FlowDeclaration
    ) -> tuple[str, ...]:
        selector = declaration.destination_selector
        matched: list[str] = []
        for endpoint in resource.endpoints:
            if not KubernetesExposureReport._selector_matches(
                selector.kind, selector.value, endpoint
            ):
                continue
            if not KubernetesExposureReport._protocol_matches(declaration.protocol, endpoint):
                continue
            if declaration.destination_ports is not None and (
                endpoint.port is None or not declaration.destination_ports.contains(endpoint.port)
            ):
                continue
            matched.append(endpoint.key)
        return tuple(sorted(matched))

    @staticmethod
    def _selector_matches(
        kind: FlowSelectorKind, value: str, endpoint: KubernetesExposureEndpoint
    ) -> bool:
        if kind is FlowSelectorKind.ANY:
            return True
        if kind is FlowSelectorKind.OBJECT:
            return False
        if endpoint.ip_value is None:
            return False
        try:
            return ipaddress.ip_address(endpoint.ip_value) in ipaddress.ip_network(
                value, strict=True
            )
        except ValueError:
            return False

    @staticmethod
    def _protocol_matches(protocol: FlowProtocol, endpoint: KubernetesExposureEndpoint) -> bool:
        if protocol is FlowProtocol.ANY:
            return True
        return endpoint.transport_protocol == protocol.value

    @staticmethod
    def _graph(
        snapshot: KubernetesTopologySnapshot,
        resources: tuple[KubernetesExposureResource, ...],
        correlations: tuple[KubernetesFlowCorrelation, ...],
        dependency_relations: tuple[SourceRelation, ...],
        dependency_objects: tuple[SourceOfTruthObject, ...],
    ) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...]]:
        by_uid = {item.uid: item for item in snapshot.resources}
        by_node_name = {
            item.name: item
            for item in snapshot.resources
            if item.kind is KubernetesResourceKind.NODE
        }
        selected_uids: set[str] = {item.uid for item in resources}
        queue = list(selected_uids)
        while queue:
            uid = queue.pop()
            resource = by_uid.get(uid)
            if resource is None:
                continue
            related = list(resource.target_uids)
            if resource.owner_uid:
                related.append(resource.owner_uid)
            if resource.node_name and resource.node_name in by_node_name:
                related.append(by_node_name[resource.node_name].uid)
            for related_uid in related:
                if related_uid not in selected_uids:
                    selected_uids.add(related_uid)
                    queue.append(related_uid)
        namespaces = {
            item.namespace
            for uid, item in by_uid.items()
            if uid in selected_uids and item.namespace is not None
        }
        selected_uids.update(
            item.uid
            for item in snapshot.resources
            if item.kind is KubernetesResourceKind.NAMESPACE and item.name in namespaces
        )

        nodes: dict[str, dict[str, object]] = {}
        for uid in sorted(selected_uids):
            resource = by_uid[uid]
            nodes[f"k8s:{uid}"] = {
                "id": f"k8s:{uid}",
                "kind": resource.kind.value,
                "name": resource.name,
                "namespace": resource.namespace,
                "external": False,
            }
        cluster_id = f"cluster:{snapshot.cluster_key}"
        nodes[cluster_id] = {
            "id": cluster_id,
            "kind": "cluster",
            "name": snapshot.cluster_name,
            "namespace": None,
            "external": False,
        }

        edges: dict[tuple[str, str, str], dict[str, object]] = {}
        for edge in snapshot.topology_edges():
            if edge.source in nodes and (edge.target in nodes or edge.external):
                if edge.external:
                    nodes.setdefault(
                        edge.target,
                        {
                            "id": edge.target,
                            "kind": "rsot-reference",
                            "name": edge.target.removeprefix("rsot:"),
                            "namespace": None,
                            "external": True,
                        },
                    )
                edges[(edge.source, edge.target, edge.relation)] = edge.as_dict()

        for exposure_resource in resources:
            resource_node = f"k8s:{exposure_resource.uid}"
            for endpoint in exposure_resource.endpoints:
                nodes[endpoint.key] = {
                    "id": endpoint.key,
                    "kind": "network-endpoint",
                    "name": endpoint.value,
                    "namespace": exposure_resource.namespace,
                    "external": endpoint.scope is KubernetesExposureScope.EXTERNAL,
                    "scope": endpoint.scope.value,
                    "protocol": endpoint.protocol,
                    "port": endpoint.port,
                }
                edges[(endpoint.key, resource_node, "exposes")] = {
                    "source": endpoint.key,
                    "target": resource_node,
                    "relation": "exposes",
                    "external": True,
                }
            for key in exposure_resource.rsot_object_keys:
                target = f"rsot:{key}"
                nodes.setdefault(
                    target,
                    {
                        "id": target,
                        "kind": "rsot-reference",
                        "name": key,
                        "namespace": None,
                        "external": True,
                    },
                )
                edges[(resource_node, target, "correlates-to")] = {
                    "source": resource_node,
                    "target": target,
                    "relation": "correlates-to",
                    "external": True,
                }

        for correlation in correlations:
            flow_node = f"flow:{correlation.declaration_code}"
            nodes[flow_node] = {
                "id": flow_node,
                "kind": "flow-declaration",
                "name": correlation.declaration_code,
                "namespace": None,
                "external": True,
                "decision": correlation.decision.value,
            }
            edges[(f"k8s:{correlation.resource_uid}", flow_node, "governed-by-flow")] = {
                "source": f"k8s:{correlation.resource_uid}",
                "target": flow_node,
                "relation": "governed-by-flow",
                "external": True,
            }

        for item in dependency_objects:
            node_id = f"rsot:{item.key.value}"
            nodes[node_id] = {
                "id": node_id,
                "kind": item.kind.value,
                "name": item.display_name,
                "namespace": None,
                "external": True,
                "status": item.status.value,
            }
        for relation in dependency_relations:
            source = f"rsot:{relation.source_key.value}"
            target = f"rsot:{relation.target_key.value}"
            nodes.setdefault(
                source,
                {
                    "id": source,
                    "kind": "rsot-reference",
                    "name": relation.source_key.value,
                    "namespace": None,
                    "external": True,
                },
            )
            nodes.setdefault(
                target,
                {
                    "id": target,
                    "kind": "rsot-reference",
                    "name": relation.target_key.value,
                    "namespace": None,
                    "external": True,
                },
            )
            edges[(source, target, relation.relation_type.value)] = {
                "source": source,
                "target": target,
                "relation": relation.relation_type.value,
                "external": True,
                "provenance": relation.provenance.value,
            }

        return (
            tuple(nodes[key] for key in sorted(nodes)),
            tuple(edges[key] for key in sorted(edges)),
        )

    def summary(self) -> dict[str, object]:
        external_resources = {item.uid for item in self.resources if item.external}
        correlated = {item.resource_uid for item in self.flow_correlations}
        allowed = {
            item.resource_uid
            for item in self.flow_correlations
            if item.decision is FlowDecision.ALLOW
        }
        denied = {
            item.resource_uid
            for item in self.flow_correlations
            if item.decision is FlowDecision.DENY
        }
        endpoints = tuple(endpoint for item in self.resources for endpoint in item.endpoints)
        return {
            "exposure_resource_count": len(self.resources),
            "external_exposure_count": len(external_resources),
            "endpoint_count": len(endpoints),
            "external_endpoint_count": sum(
                1 for item in endpoints if item.scope is KubernetesExposureScope.EXTERNAL
            ),
            "flow_correlated_exposure_count": len(correlated),
            "flow_allowed_exposure_count": len(allowed),
            "flow_denied_exposure_count": len(denied),
            "ungoverned_external_exposure_count": len(external_resources - correlated),
            "dependency_relation_count": len(self.dependency_relations),
            "dependency_object_count": len(self.dependency_objects),
            "graph_node_count": len(self.graph_nodes),
            "graph_edge_count": len(self.graph_edges),
            "correlation_truncated": self.correlation_truncated,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "cluster_key": self.cluster_key,
            "summary": self.summary(),
            "resources": [item.as_dict() for item in self.resources],
            "flow_correlations": [item.as_dict() for item in self.flow_correlations],
            "dependency_relations": [item.as_dict() for item in self.dependency_relations],
            "dependency_objects": [item.as_dict() for item in self.dependency_objects],
            "graph": {
                "nodes": list(self.graph_nodes),
                "edges": list(self.graph_edges),
            },
            "correlation_truncated": self.correlation_truncated,
            "fingerprint": self.fingerprint,
        }
