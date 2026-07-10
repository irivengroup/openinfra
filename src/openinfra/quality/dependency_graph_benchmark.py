from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter_ns
from typing import cast

from openinfra.application.dependency_graph_services import (
    AnalyzeDependencySpofCommand,
    DependencyGraphService,
    TraverseDependencyGraphCommand,
)
from openinfra.application.ports import (
    AuditRepository,
    SourceOfTruthRepository,
    TransactionManager,
    UnitOfWork,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.audit import AuditEventFilter, AuditEventPage, AuditIntegrityReport
from openinfra.domain.common import AuditEvent, Pagination, TenantId, ValidationError
from openinfra.domain.security import AuthenticatedPrincipal, Permission, SecurityRole
from openinfra.domain.source_of_truth import (
    SourceObjectPage,
    SourceObjectSnapshot,
    SourceOfTruthObject,
    SourceRelation,
    SourceRelationPage,
)

_BENCHMARK_TENANT = TenantId.from_value("benchmark")


class _BenchmarkAuthentication:
    @staticmethod
    def value() -> str:
        return "x" * 40


class BenchmarkConfigurationError(ValueError):
    """Raised when a benchmark configuration cannot produce a valid topology."""


@dataclass(frozen=True, slots=True)
class DependencyGraphBenchmarkConfig:
    node_count: int = 5000
    spof_hub_count: int = 100
    samples: int = 3
    warmups: int = 1
    one_level_threshold_ms: float = 1500.0
    filtered_threshold_ms: float = 1500.0
    spof_threshold_ms: float = 5000.0
    pagination_threshold_ms: float = 15000.0

    def validate(self) -> DependencyGraphBenchmarkConfig:
        if not 100 <= self.node_count <= 5000:
            raise BenchmarkConfigurationError("node_count must be between 100 and 5000")
        maximum_hubs = (self.node_count - 1) // 2
        if not 2 <= self.spof_hub_count <= maximum_hubs:
            raise BenchmarkConfigurationError(
                f"spof_hub_count must be between 2 and {maximum_hubs}"
            )
        if not 1 <= self.samples <= 20:
            raise BenchmarkConfigurationError("samples must be between 1 and 20")
        if not 0 <= self.warmups <= 10:
            raise BenchmarkConfigurationError("warmups must be between 0 and 10")
        thresholds = (
            self.one_level_threshold_ms,
            self.filtered_threshold_ms,
            self.spof_threshold_ms,
            self.pagination_threshold_ms,
        )
        if any(not math.isfinite(value) or value <= 0 for value in thresholds):
            raise BenchmarkConfigurationError("all latency thresholds must be positive")
        return self


@dataclass(frozen=True, slots=True)
class BenchmarkMeasurement:
    name: str
    samples_ms: tuple[float, ...]
    p50_ms: float
    p95_ms: float
    threshold_ms: float
    passed: bool
    observations: dict[str, int | str | bool]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "samples_ms": [round(value, 3) for value in self.samples_ms],
            "p50_ms": round(self.p50_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "threshold_ms": round(self.threshold_ms, 3),
            "passed": self.passed,
            "observations": dict(self.observations),
        }


@dataclass(frozen=True, slots=True)
class DependencyGraphBenchmarkReport:
    generated_at: str
    python_version: str
    platform: str
    logical_cpu_count: int
    config: DependencyGraphBenchmarkConfig
    measurements: tuple[BenchmarkMeasurement, ...]

    @property
    def passed(self) -> bool:
        return all(measurement.passed for measurement in self.measurements)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "benchmark": "openinfra-dependency-graph-volumetric",
            "generated_at": self.generated_at,
            "environment": {
                "python_version": self.python_version,
                "platform": self.platform,
                "logical_cpu_count": self.logical_cpu_count,
            },
            "config": {
                "node_count": self.config.node_count,
                "spof_hub_count": self.config.spof_hub_count,
                "samples": self.config.samples,
                "warmups": self.config.warmups,
                "thresholds_ms": {
                    "one_level": self.config.one_level_threshold_ms,
                    "filtered": self.config.filtered_threshold_ms,
                    "spof": self.config.spof_threshold_ms,
                    "pagination": self.config.pagination_threshold_ms,
                },
            },
            "passed": self.passed,
            "measurements": [measurement.as_dict() for measurement in self.measurements],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=True) + "\n"

    def summary_lines(self) -> tuple[str, ...]:
        lines = [
            "OpenInfra dependency graph volumetric benchmark",
            f"overall={'PASS' if self.passed else 'FAIL'} nodes={self.config.node_count}",
        ]
        lines.extend(
            (
                f"{measurement.name}: p95={measurement.p95_ms:.3f} ms "
                f"threshold={measurement.threshold_ms:.3f} ms "
                f"status={'PASS' if measurement.passed else 'FAIL'}"
            )
            for measurement in self.measurements
        )
        return tuple(lines)


class _SyntheticSourceOfTruthRepository(SourceOfTruthRepository):
    """Indexed deterministic adapter dedicated to graph algorithm capacity validation."""

    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], SourceOfTruthObject] = {}
        self._relations: dict[str, SourceRelation] = {}
        self._relations_by_tenant: dict[str, list[SourceRelation]] = defaultdict(list)
        self._relations_by_source: dict[tuple[str, str], list[SourceRelation]] = defaultdict(list)
        self._relations_by_target: dict[tuple[str, str], list[SourceRelation]] = defaultdict(list)

    def create_object(
        self,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, object],
        tags: tuple[str, ...],
        source: str,
        actor: str,
    ) -> SourceOfTruthObject:
        del actor
        source_object = SourceOfTruthObject.create(
            tenant_id,
            key,
            kind,
            display_name,
            attributes,
            tags,
            source,
        )
        self.upsert_object(source_object, "benchmark")
        return source_object

    def upsert_object(self, source_object: SourceOfTruthObject, actor: str) -> None:
        del actor
        self._objects[(source_object.tenant_id.value, source_object.key.value)] = source_object

    def find_object(self, tenant_id: TenantId, key: str) -> SourceOfTruthObject | None:
        return self._objects.get((tenant_id.value, key.strip().lower()))

    def list_objects(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        tag: str | None = None,
        resource_type: str | None = None,
    ) -> SourceObjectPage:
        normalized_kind = kind.strip().lower() if kind else None
        normalized_tag = tag.strip().lower() if tag else None
        normalized_resource_type = resource_type.strip().lower() if resource_type else None
        items = [
            item
            for (tenant, _), item in self._objects.items()
            if tenant == tenant_id.value
            and (normalized_kind is None or item.kind.value == normalized_kind)
            and (
                normalized_tag is None
                or normalized_tag in {candidate.value for candidate in item.tags}
            )
            and (
                normalized_resource_type is None
                or item.as_dict().get("resource_type") == normalized_resource_type
            )
        ]
        items.sort(key=lambda item: item.key.value)
        start = self._offset(pagination.cursor)
        selected = tuple(items[start : start + pagination.limit])
        next_offset = start + len(selected)
        return SourceObjectPage(
            selected,
            str(next_offset) if next_offset < len(items) else None,
        )

    def find_object_version(
        self,
        tenant_id: TenantId,
        key: str,
        version: int,
    ) -> SourceObjectSnapshot | None:
        del tenant_id, key, version
        return None

    def find_object_as_of(
        self,
        tenant_id: TenantId,
        key: str,
        as_of: datetime,
    ) -> SourceObjectSnapshot | None:
        del tenant_id, key, as_of
        return None

    def add_relation(self, relation: SourceRelation) -> None:
        if relation.id.value in self._relations:
            return
        self._relations[relation.id.value] = relation
        tenant = relation.tenant_id.value
        self._relations_by_tenant[tenant].append(relation)
        self._relations_by_source[(tenant, relation.source_key.value)].append(relation)
        self._relations_by_target[(tenant, relation.target_key.value)].append(relation)

    def list_relations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_key: str | None = None,
        target_key: str | None = None,
        relation_type: str | None = None,
        as_of: datetime | None = None,
    ) -> SourceRelationPage:
        tenant = tenant_id.value
        normalized_source = source_key.strip().lower() if source_key else None
        normalized_target = target_key.strip().lower() if target_key else None
        normalized_type = relation_type.strip().lower() if relation_type else None
        if normalized_source is not None:
            candidates = self._relations_by_source.get((tenant, normalized_source), ())
        elif normalized_target is not None:
            candidates = self._relations_by_target.get((tenant, normalized_target), ())
        else:
            candidates = self._relations_by_tenant.get(tenant, ())
        filtered = [
            relation
            for relation in candidates
            if (normalized_source is None or relation.source_key.value == normalized_source)
            and (normalized_target is None or relation.target_key.value == normalized_target)
            and (normalized_type is None or relation.relation_type.value == normalized_type)
            and (as_of is None or relation.is_valid_at(as_of))
        ]
        filtered.sort(key=lambda item: (item.created_at.isoformat(), item.id.value), reverse=True)
        start = self._offset(pagination.cursor)
        selected = tuple(filtered[start : start + pagination.limit])
        next_offset = start + len(selected)
        return SourceRelationPage(
            selected,
            str(next_offset) if next_offset < len(filtered) else None,
        )

    @staticmethod
    def _offset(cursor: str | None) -> int:
        try:
            value = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if value < 0:
            raise ValidationError("pagination cursor must be positive")
        return value


class _BenchmarkAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)

    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        del event_filter
        return AuditEventPage((), None)

    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        del limit
        return AuditIntegrityReport(tenant_id, len(self.events), True, None, "benchmark")


class _BenchmarkUnitOfWork(UnitOfWork):
    def __enter__(self) -> _BenchmarkUnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _BenchmarkTransactionManager(TransactionManager):
    def begin(self) -> UnitOfWork:
        return _BenchmarkUnitOfWork()


class _AllowAllSecurityService:
    def authenticate_token(self, command: AuthenticateTokenCommand) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            tenant_id=TenantId.from_value(command.tenant_id),
            subject="dependency-graph-benchmark",
            roles=(SecurityRole.from_value("rsot:operator"),),
            permissions=frozenset(Permission),
        )


class DependencyGraphBenchmarkRunner:
    def __init__(self, config: DependencyGraphBenchmarkConfig) -> None:
        self._config = config.validate()
        self._repository = _SyntheticSourceOfTruthRepository()
        self._audit_repository = _BenchmarkAuditRepository()
        self._service = DependencyGraphService(
            self._repository,
            self._audit_repository,
            _BenchmarkTransactionManager(),
            cast(SecurityService, _AllowAllSecurityService()),
        )
        self._seed_topologies()

    def run(self) -> DependencyGraphBenchmarkReport:
        measurements = (
            self._measure(
                "traverse_one_level",
                self._traverse_one_level,
                self._config.one_level_threshold_ms,
            ),
            self._measure(
                "traverse_one_level_filtered",
                self._traverse_one_level_filtered,
                self._config.filtered_threshold_ms,
            ),
            self._measure(
                "spof_analysis",
                self._spof_analysis,
                self._config.spof_threshold_ms,
            ),
            self._measure(
                "spof_full_pagination",
                self._spof_full_pagination,
                self._config.pagination_threshold_ms,
            ),
        )
        return DependencyGraphBenchmarkReport(
            generated_at=datetime.now(UTC).isoformat(),
            python_version=platform.python_version(),
            platform=platform.platform(),
            logical_cpu_count=os.cpu_count() or 1,
            config=self._config,
            measurements=measurements,
        )

    def _seed_topologies(self) -> None:
        self._add_object("application/one-level-root", "application", "One-level root")
        for index in range(self._config.node_count - 1):
            key = f"server/one-level-{index:05d}"
            self._add_object(key, "server", f"One-level node {index}")
            relation_type = "calls" if index % 2 == 0 else "depends_on"
            self._repository.add_relation(
                SourceRelation.create(
                    _BENCHMARK_TENANT,
                    relation_type,
                    "application/one-level-root",
                    key,
                    "benchmark",
                )
            )

        self._add_object("application/spof-root", "application", "SPOF root")
        hubs = [f"service/spof-hub-{index:04d}" for index in range(self._config.spof_hub_count)]
        for index, hub_key in enumerate(hubs):
            self._add_object(hub_key, "service", f"SPOF hub {index}")
            self._repository.add_relation(
                SourceRelation.create(
                    _BENCHMARK_TENANT,
                    "calls",
                    "application/spof-root",
                    hub_key,
                    "benchmark",
                )
            )
        leaf_count = self._config.node_count - self._config.spof_hub_count - 1
        for index in range(leaf_count):
            leaf_key = f"server/spof-leaf-{index:05d}"
            hub_key = hubs[index % len(hubs)]
            self._add_object(leaf_key, "server", f"SPOF leaf {index}")
            self._repository.add_relation(
                SourceRelation.create(
                    _BENCHMARK_TENANT,
                    "depends_on",
                    hub_key,
                    leaf_key,
                    "benchmark",
                )
            )

    def _add_object(self, key: str, kind: str, display_name: str) -> None:
        self._repository.create_object(
            _BENCHMARK_TENANT,
            key,
            kind,
            display_name,
            {"benchmark": True},
            ("benchmark",),
            "benchmark",
            "benchmark",
        )

    def _traverse_one_level(self) -> dict[str, int | str | bool]:
        graph = self._service.traverse(
            TraverseDependencyGraphCommand(
                tenant_id=_BENCHMARK_TENANT.value,
                admin_token=_BenchmarkAuthentication.value(),
                root_key="application/one-level-root",
                direction="outgoing",
                max_depth=1,
                max_nodes=self._config.node_count,
            )
        )
        if len(graph.nodes) != self._config.node_count or graph.truncated:
            raise RuntimeError("one-level traversal returned an incomplete graph")
        return {
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "truncated": graph.truncated,
        }

    def _traverse_one_level_filtered(self) -> dict[str, int | str | bool]:
        graph = self._service.traverse(
            TraverseDependencyGraphCommand(
                tenant_id=_BENCHMARK_TENANT.value,
                admin_token=_BenchmarkAuthentication.value(),
                root_key="application/one-level-root",
                direction="outgoing",
                max_depth=1,
                max_nodes=self._config.node_count,
                relation_types=("calls",),
            )
        )
        expected_edges = (self._config.node_count - 1 + 1) // 2
        if len(graph.edges) != expected_edges or len(graph.nodes) != expected_edges + 1:
            raise RuntimeError("filtered one-level traversal returned unexpected cardinalities")
        return {
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "relation_type": "calls",
        }

    def _spof_analysis(self) -> dict[str, int | str | bool]:
        report = self._service.analyze_spof(
            AnalyzeDependencySpofCommand(
                tenant_id=_BENCHMARK_TENANT.value,
                admin_token=_BenchmarkAuthentication.value(),
                root_key="application/spof-root",
                direction="outgoing",
                max_depth=2,
                max_nodes=self._config.node_count,
                candidate_kinds=("service",),
                limit=min(100, self._config.spof_hub_count),
            )
        )
        if report.total_spof_count != self._config.spof_hub_count or report.truncated:
            raise RuntimeError("SPOF analysis returned an incomplete candidate set")
        return {
            "nodes": report.node_count,
            "edges": report.edge_count,
            "spof_count": report.total_spof_count,
            "page_size": len(report.candidates),
            "complete": not report.truncated,
        }

    def _spof_full_pagination(self) -> dict[str, int | str | bool]:
        cursor: str | None = None
        seen_keys: set[str] = set()
        page_count = 0
        page_size = min(25, self._config.spof_hub_count)
        while True:
            report = self._service.analyze_spof(
                AnalyzeDependencySpofCommand(
                    tenant_id=_BENCHMARK_TENANT.value,
                    admin_token=_BenchmarkAuthentication.value(),
                    root_key="application/spof-root",
                    direction="outgoing",
                    max_depth=2,
                    max_nodes=self._config.node_count,
                    candidate_kinds=("service",),
                    limit=page_size,
                    cursor=cursor,
                )
            )
            page_count += 1
            seen_keys.update(item.node.key for item in report.candidates)
            cursor = report.next_cursor
            if cursor is None:
                break
            if page_count > self._config.spof_hub_count:
                raise RuntimeError("SPOF pagination did not terminate")
        if len(seen_keys) != self._config.spof_hub_count:
            raise RuntimeError("SPOF pagination returned duplicates or missing candidates")
        return {
            "spof_count": len(seen_keys),
            "pages": page_count,
            "page_size": page_size,
        }

    def _measure(
        self,
        name: str,
        operation: Callable[[], dict[str, int | str | bool]],
        threshold_ms: float,
    ) -> BenchmarkMeasurement:
        for _ in range(self._config.warmups):
            operation()
        samples: list[float] = []
        expected_observations: dict[str, int | str | bool] | None = None
        for _ in range(self._config.samples):
            started = perf_counter_ns()
            observations = operation()
            elapsed_ms = (perf_counter_ns() - started) / 1_000_000
            if expected_observations is None:
                expected_observations = observations
            elif observations != expected_observations:
                raise RuntimeError(f"benchmark {name} produced non-deterministic observations")
            samples.append(elapsed_ms)
        ordered = tuple(sorted(samples))
        p50 = self._percentile(ordered, 0.50)
        p95 = self._percentile(ordered, 0.95)
        return BenchmarkMeasurement(
            name=name,
            samples_ms=tuple(samples),
            p50_ms=p50,
            p95_ms=p95,
            threshold_ms=threshold_ms,
            passed=p95 <= threshold_ms,
            observations=expected_observations or {},
        )

    @staticmethod
    def _percentile(ordered: tuple[float, ...], percentile: float) -> float:
        if not ordered:
            raise BenchmarkConfigurationError("at least one timing sample is required")
        rank = max(1, math.ceil(percentile * len(ordered)))
        return ordered[rank - 1]


class DependencyGraphBenchmarkCli:
    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            handle.write(content)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Run deterministic OpenInfra dependency graph volumetric benchmarks."
        )
        parser.add_argument("--nodes", type=int, default=5000)
        parser.add_argument("--spof-hubs", type=int, default=100)
        parser.add_argument("--samples", type=int, default=3)
        parser.add_argument("--warmups", type=int, default=1)
        parser.add_argument("--one-level-threshold-ms", type=float, default=1500.0)
        parser.add_argument("--filtered-threshold-ms", type=float, default=1500.0)
        parser.add_argument("--spof-threshold-ms", type=float, default=5000.0)
        parser.add_argument("--pagination-threshold-ms", type=float, default=15000.0)
        parser.add_argument("--output", type=Path)
        return parser

    @classmethod
    def main(cls, argv: Sequence[str] | None = None) -> int:
        arguments = cls._parser().parse_args(argv)
        try:
            config = DependencyGraphBenchmarkConfig(
                node_count=arguments.nodes,
                spof_hub_count=arguments.spof_hubs,
                samples=arguments.samples,
                warmups=arguments.warmups,
                one_level_threshold_ms=arguments.one_level_threshold_ms,
                filtered_threshold_ms=arguments.filtered_threshold_ms,
                spof_threshold_ms=arguments.spof_threshold_ms,
                pagination_threshold_ms=arguments.pagination_threshold_ms,
            ).validate()
            report = DependencyGraphBenchmarkRunner(config).run()
        except (BenchmarkConfigurationError, ValidationError, RuntimeError) as exc:
            sys.stderr.write(f"dependency graph benchmark failed: {exc}\n")
            return 2
        if arguments.output is not None:
            cls._atomic_write(arguments.output, report.to_json())
        for line in report.summary_lines():
            sys.stdout.write(line + "\n")
        return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(DependencyGraphBenchmarkCli.main())
