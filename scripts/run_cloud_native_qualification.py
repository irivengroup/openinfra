from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from openinfra import __version__
from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.kubernetes_capacity import KubernetesCapacityReport
from openinfra.domain.kubernetes_topology import (
    KubernetesPhysicalPath,
    KubernetesResource,
    KubernetesTopologySnapshot,
)


class CloudNativeRuntimeQualificationError(Exception):
    """Raised when the P21 runtime qualification cannot be completed safely."""


class CloudNativeRuntimeQualification:
    MIN_CLUSTERS = 3
    MAX_RESOURCES = 50_000

    @classmethod
    def run(
        cls,
        *,
        cluster_count: int = MIN_CLUSTERS,
        resources_per_snapshot: int = MAX_RESOURCES,
        max_seconds: float = 30.0,
    ) -> dict[str, object]:
        if cluster_count < cls.MIN_CLUSTERS or cluster_count > 16:
            raise CloudNativeRuntimeQualificationError("cluster_count must be between 3 and 16")
        if resources_per_snapshot != cls.MAX_RESOURCES:
            raise CloudNativeRuntimeQualificationError(
                "GATE-10 requires exactly 50000 resources per maximum-size snapshot"
            )
        if max_seconds <= 0.0 or max_seconds > 300.0:
            raise CloudNativeRuntimeQualificationError("max_seconds must be between 0 and 300")

        started = perf_counter()
        failures: list[str] = []
        observed_at = datetime.now(UTC)
        snapshots: list[KubernetesTopologySnapshot] = []
        for index in range(cluster_count):
            size = resources_per_snapshot if index == 0 else 128
            snapshot = cls._build_snapshot(index, size, observed_at)
            snapshots.append(snapshot)
        elapsed = round(perf_counter() - started, 6)

        max_snapshot = snapshots[0]
        max_summary = max_snapshot.summary()
        deterministic = cls._deterministic_probe(observed_at)
        capacity_verified = cls._capacity_probe(observed_at)
        secrets_rejected = cls._secret_probe()
        cross_namespace_rejected = cls._cross_namespace_probe(observed_at)
        orphan_paths_rejected = cls._orphan_path_probe()
        multi_cluster_verified = len({item.cluster_key for item in snapshots}) == cluster_count
        physical_mapping_verified = all(
            item.summary()["mapping_coverage_percent"] == 100.0 for item in snapshots
        )
        max_snapshot_size_verified = max_summary["resource_count"] == resources_per_snapshot
        performance_budget_met = elapsed <= max_seconds

        checks = {
            "multi_cluster_verified": multi_cluster_verified,
            "max_snapshot_size_verified": max_snapshot_size_verified,
            "deterministic_fingerprints": deterministic,
            "physical_mapping_verified": physical_mapping_verified,
            "capacity_read_model_verified": capacity_verified,
            "secrets_rejected": secrets_rejected,
            "cross_namespace_references_rejected": cross_namespace_rejected,
            "orphan_physical_paths_rejected": orphan_paths_rejected,
            "performance_budget_met": performance_budget_met,
        }
        failures.extend(f"{name} failed" for name, passed in checks.items() if not passed)
        complete = not failures
        return {
            "schema_version": 1,
            "report_kind": "cloud-native-runtime-qualification",
            "release_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "complete": complete,
            "phase": "P21",
            "epic": "EPIC-2106",
            "release": "REL-11",
            "gate_id": "GATE-10",
            "qualified_cluster_count": cluster_count,
            "qualified_resource_count": sum(len(item.resources) for item in snapshots),
            "max_resources_per_snapshot": resources_per_snapshot,
            "elapsed_seconds": elapsed,
            "performance_budget_seconds": max_seconds,
            **checks,
            "status": "passed" if complete else "failed",
            "failures": failures,
        }

    @classmethod
    def _build_snapshot(
        cls,
        index: int,
        resource_count: int,
        observed_at: datetime,
    ) -> KubernetesTopologySnapshot:
        cluster_suffix = f"{index + 1:02d}"
        namespace = "benchmark"
        node_name = f"worker-{cluster_suffix}"
        resources: list[KubernetesResource] = [
            KubernetesResource.create("namespace", f"ns-{cluster_suffix}", namespace),
            KubernetesResource.create(
                "node",
                f"node-{cluster_suffix}",
                node_name,
                physical_path=KubernetesPhysicalPath.create(
                    vm_key=f"vm-k8s-{cluster_suffix}",
                    hypervisor_key=f"hypervisor-{cluster_suffix}",
                    server_key=f"server-{cluster_suffix}",
                    rack_id=f"rack-{cluster_suffix}",
                    room_id=f"room-{cluster_suffix}",
                    site_code=f"site-{cluster_suffix}",
                ),
            ),
        ]
        resources.extend(
            KubernetesResource.create(
                "pod",
                f"pod-{cluster_suffix}-{item:05d}",
                f"pod-{item:05d}",
                namespace=namespace,
                node_name=node_name,
            )
            for item in range(resource_count - 2)
        )
        return KubernetesTopologySnapshot.create(
            TenantId.from_value("default"),
            f"cluster-{cluster_suffix}",
            f"cluster-{cluster_suffix}",
            "kubernetes",
            "v1.34.1",
            f"qualification:cluster-{cluster_suffix}",
            observed_at,
            tuple(resources),
            region="qualification-region",
            site_code=f"site-{cluster_suffix}",
        )

    @classmethod
    def _deterministic_probe(cls, observed_at: datetime) -> bool:
        resources = (
            KubernetesResource.create("namespace", "ns-deterministic", "deterministic"),
            KubernetesResource.create(
                "node",
                "node-deterministic",
                "worker-deterministic",
                physical_path=KubernetesPhysicalPath.create(site_code="site-deterministic"),
            ),
            KubernetesResource.create(
                "pod",
                "pod-deterministic",
                "pod-deterministic",
                namespace="deterministic",
                node_name="worker-deterministic",
            ),
        )
        arguments = (
            TenantId.from_value("default"),
            "cluster-deterministic",
            "cluster-deterministic",
            "kubernetes",
            "v1.34.1",
            "qualification:deterministic",
            observed_at,
        )
        first = KubernetesTopologySnapshot.create(*arguments, resources)
        second = KubernetesTopologySnapshot.create(*arguments, tuple(reversed(resources)))
        return first.fingerprint == second.fingerprint

    @classmethod
    def _capacity_probe(cls, observed_at: datetime) -> bool:
        gibibyte = 1024**3
        resources = (
            KubernetesResource.create("namespace", "ns-capacity", "capacity"),
            KubernetesResource.create(
                "node",
                "node-capacity",
                "worker-capacity",
                attributes={
                    "capacity": {
                        "cpu_capacity_millicores": 8000,
                        "memory_capacity_bytes": 32 * gibibyte,
                        "storage_capacity_bytes": 500 * gibibyte,
                    }
                },
                physical_path=KubernetesPhysicalPath.create(site_code="site-capacity"),
            ),
            KubernetesResource.create(
                "pod",
                "pod-capacity",
                "pod-capacity",
                namespace="capacity",
                node_name="worker-capacity",
                attributes={
                    "capacity": {
                        "cpu_request_millicores": 1000,
                        "cpu_limit_millicores": 2000,
                        "cpu_usage_millicores": 750,
                        "memory_request_bytes": 2 * gibibyte,
                        "memory_limit_bytes": 4 * gibibyte,
                        "memory_usage_bytes": gibibyte,
                    }
                },
            ),
            KubernetesResource.create(
                "volume",
                "volume-capacity",
                "volume-capacity",
                namespace="capacity",
                target_uids=("pod-capacity",),
                attributes={
                    "capacity": {
                        "storage_request_bytes": 20 * gibibyte,
                        "storage_limit_bytes": 40 * gibibyte,
                        "storage_usage_bytes": 10 * gibibyte,
                        "storage_capacity_bytes": 100 * gibibyte,
                    }
                },
            ),
        )
        snapshot = KubernetesTopologySnapshot.create(
            TenantId.from_value("default"),
            "cluster-capacity",
            "cluster-capacity",
            "kubernetes",
            "v1.34.1",
            "qualification:capacity",
            observed_at,
            resources,
            site_code="site-capacity",
        )
        report = KubernetesCapacityReport.build(snapshot)
        return (
            len(report.namespaces) == 1
            and report.cluster.cpu_capacity_millicores == 8000
            and report.cluster.storage_capacity_bytes == 100 * gibibyte
        )

    @staticmethod
    def _secret_probe() -> bool:
        try:
            KubernetesResource.create(
                "pod",
                "pod-secret",
                "pod-secret",
                namespace="benchmark",
                attributes={"api_token": "must-never-be-stored"},
            )
        except ValidationError:
            return True
        return False

    @staticmethod
    def _cross_namespace_probe(observed_at: datetime) -> bool:
        resources = (
            KubernetesResource.create("namespace", "ns-a", "namespace-a"),
            KubernetesResource.create("namespace", "ns-b", "namespace-b"),
            KubernetesResource.create("pod", "pod-b", "pod-b", namespace="namespace-b"),
            KubernetesResource.create(
                "service",
                "service-a",
                "service-a",
                namespace="namespace-a",
                target_uids=("pod-b",),
            ),
        )
        try:
            KubernetesTopologySnapshot.create(
                TenantId.from_value("default"),
                "cluster-cross-namespace",
                "cluster-cross-namespace",
                "kubernetes",
                "v1.34.1",
                "qualification:cross-namespace",
                observed_at,
                resources,
            )
        except ValidationError:
            return True
        return False

    @staticmethod
    def _orphan_path_probe() -> bool:
        try:
            KubernetesPhysicalPath.create(rack_id="rack-without-site")
        except ValidationError:
            return True
        return False


class CloudNativeRuntimeQualificationCli:
    @staticmethod
    def _write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Run OpenInfra P21 GATE-10 qualification")
        parser.add_argument("--clusters", type=int, default=3)
        parser.add_argument("--resources", type=int, default=50_000)
        parser.add_argument("--max-seconds", type=float, default=30.0)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args()
        try:
            report = CloudNativeRuntimeQualification.run(
                cluster_count=args.clusters,
                resources_per_snapshot=args.resources,
                max_seconds=args.max_seconds,
            )
        except CloudNativeRuntimeQualificationError as exc:
            if args.enforce:
                print(str(exc))
                return 1
            raise
        if args.output is not None:
            cls._write_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.enforce and report["status"] != "passed":
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(CloudNativeRuntimeQualificationCli.main())
