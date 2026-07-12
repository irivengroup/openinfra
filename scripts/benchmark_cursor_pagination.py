from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns

from openinfra.domain.common import Pagination
from openinfra.infrastructure.cursor_pagination import (
    CursorDirection,
    CursorField,
    CursorTokenCodec,
    CursorValueType,
    PostgreSQLKeysetPage,
)


@dataclass(frozen=True, slots=True)
class CursorLatencyDistribution:
    samples_ms: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.samples_ms:
            raise ValueError("latency samples cannot be empty")

    def percentile(self, percentile: int) -> float:
        if not 1 <= percentile <= 100:
            raise ValueError("percentile must be between 1 and 100")
        ordered = sorted(self.samples_ms)
        index = max(0, min(len(ordered) - 1, (len(ordered) * percentile + 99) // 100 - 1))
        return ordered[index]


class OpenInfraCursorPaginationBenchmark:
    _key_material = hashlib.sha256(b"openinfra-cursor-pagination-benchmark").hexdigest()

    def __init__(self, iterations: int = 5_000, p95_threshold_ms: float = 1.0) -> None:
        if iterations < 100:
            raise ValueError("iterations must be at least 100")
        if p95_threshold_ms <= 0:
            raise ValueError("p95 threshold must be positive")
        self._iterations = iterations
        self._p95_threshold_ms = p95_threshold_ms
        self._codec = CursorTokenCodec(self._key_material)
        self._fields = (
            CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
            CursorField("id", CursorDirection.DESC),
        )

    def run(self) -> dict[str, object]:
        filters = {"severity": "warning", "actor": None}
        tenant_id = "benchmark-tenant"
        scope = "security.audit-events"
        token = self._codec.encode(
            scope,
            {"tenant_id": tenant_id, **filters},
            self._fields,
            {"created_at": datetime(2026, 7, 12, tzinfo=UTC), "id": "f" * 36},
        )
        shallow = self._measure(
            lambda: PostgreSQLKeysetPage.create(
                Pagination.from_values(100),
                scope=scope,
                tenant_id=tenant_id,
                filters=filters,
                fields=self._fields,
                codec=self._codec,
            )
        )
        deep = self._measure(
            lambda: PostgreSQLKeysetPage.create(
                Pagination.from_values(100, token),
                scope=scope,
                tenant_id=tenant_id,
                filters=filters,
                fields=self._fields,
                codec=self._codec,
            )
        )
        results = []
        for name, distribution in (("first-page", shallow), ("deep-page", deep)):
            p95 = distribution.percentile(95)
            results.append(
                {
                    "scenario": name,
                    "iterations": self._iterations,
                    "p50_ms": round(distribution.percentile(50), 6),
                    "p95_ms": round(p95, 6),
                    "p99_ms": round(distribution.percentile(99), 6),
                    "threshold_p95_ms": self._p95_threshold_ms,
                    "passed": p95 <= self._p95_threshold_ms,
                }
            )
        return {
            "scope": "keyset-query-construction-regression",
            "capacity_certification": False,
            "iterations": self._iterations,
            "passed": all(bool(item["passed"]) for item in results),
            "results": results,
        }

    def _measure(self, operation: object) -> CursorLatencyDistribution:
        if not callable(operation):
            raise TypeError("benchmark operation must be callable")
        samples: list[float] = []
        for _ in range(self._iterations):
            started = perf_counter_ns()
            page = operation()
            _ = page.where_sql
            _ = page.parameters
            samples.append((perf_counter_ns() - started) / 1_000_000)
        return CursorLatencyDistribution(tuple(samples))


class OpenInfraCursorPaginationBenchmarkCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(
            description="Benchmark OpenInfra keyset cursor construction"
        )
        parser.add_argument("--iterations", type=int, default=5_000)
        parser.add_argument("--p95-threshold-ms", type=float, default=1.0)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            report = OpenInfraCursorPaginationBenchmark(
                args.iterations, args.p95_threshold_ms
            ).run()
        except (TypeError, ValueError) as exc:
            print(f"openinfra-cursor-benchmark: error: {exc}", file=sys.stderr)
            return 2
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 1 if args.enforce and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(OpenInfraCursorPaginationBenchmarkCli.main())
