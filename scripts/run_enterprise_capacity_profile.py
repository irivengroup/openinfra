from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from openinfra.domain.common import ValidationError


@dataclass(frozen=True, slots=True)
class LoadStage:
    name: str
    duration_seconds: float
    concurrency: int
    target_rps: float


class EnterpriseCapacityLoadRunner:
    def __init__(
        self,
        *,
        base_url: str,
        metrics_url: str,
        path: str,
        token: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._metrics_url = metrics_url
        self._path = "/" + path.lstrip("/")
        self._token = token
        self._timeout_seconds = timeout_seconds

    async def run(self, stage: LoadStage) -> dict[str, object]:
        if stage.duration_seconds <= 0 or stage.concurrency <= 0 or stage.target_rps <= 0:
            raise ValidationError(
                "capacity stage duration, concurrency and target_rps must be positive"
            )
        headers = {"accept": "application/json"}
        if self._token:
            headers["authorization"] = f"Bearer {self._token}"
        before_metrics = await self._metrics()
        latencies: list[float] = []
        failures = 0
        requests = 0
        deadline = time.monotonic() + stage.duration_seconds
        interval = 1.0 / stage.target_rps
        semaphore = asyncio.Semaphore(stage.concurrency)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout_seconds,
            verify=True,
        ) as client:
            tasks: set[asyncio.Task[tuple[float, bool]]] = set()
            scheduled_at = time.monotonic()
            while time.monotonic() < deadline:
                await asyncio.sleep(max(0.0, scheduled_at - time.monotonic()))
                tasks.add(asyncio.create_task(self._request(client, semaphore)))
                scheduled_at += interval
                completed = {task for task in tasks if task.done()}
                for task in completed:
                    latency, failed = await task
                    latencies.append(latency)
                    failures += int(failed)
                    requests += 1
                tasks.difference_update(completed)
            for latency, failed in await asyncio.gather(*tasks):
                latencies.append(latency)
                failures += int(failed)
                requests += 1
        after_metrics = await self._metrics()
        if not latencies:
            raise ValidationError("capacity stage produced no requests")
        ordered = sorted(latencies)
        return {
            "stage": stage.name,
            "duration_seconds": stage.duration_seconds,
            "requests": requests,
            "p95_ms": self._percentile(ordered, 95),
            "p99_ms": self._percentile(ordered, 99),
            "error_rate_percent": failures * 100.0 / requests,
            "saturation_percent": self._saturation(after_metrics),
            "memory_growth_percent": self._memory_growth(before_metrics, after_metrics),
            "replica_lag_seconds": self._metric_max(
                after_metrics, "openinfra_db_replica_lag_seconds"
            ),
            "trace_coverage_percent": self._trace_coverage(after_metrics),
            "metrics_complete": self._metrics_complete(after_metrics),
            "leak_detected": self._leak_detected(before_metrics, after_metrics),
        }

    async def _request(
        self, client: httpx.AsyncClient, semaphore: asyncio.Semaphore
    ) -> tuple[float, bool]:
        async with semaphore:
            started = time.perf_counter()
            try:
                response = await client.get(self._path)
                failed = response.status_code >= 500
            except httpx.HTTPError:
                failed = True
            return (time.perf_counter() - started) * 1000.0, failed

    async def _metrics(self) -> dict[str, list[float]]:
        async with httpx.AsyncClient(timeout=self._timeout_seconds, verify=True) as client:
            response = await client.get(self._metrics_url)
            response.raise_for_status()
        result: dict[str, list[float]] = {}
        for line in response.text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            left, _, raw = stripped.rpartition(" ")
            name = left.split("{", 1)[0]
            try:
                value = float(raw)
            except ValueError:
                continue
            if math.isfinite(value):
                result.setdefault(name, []).append(value)
        return result

    @staticmethod
    def _percentile(values: list[float], percentile: int) -> float:
        rank = max(0, math.ceil(percentile / 100.0 * len(values)) - 1)
        return values[min(rank, len(values) - 1)]

    @staticmethod
    def _metric_max(metrics: dict[str, list[float]], name: str) -> float:
        values = metrics.get(name, [])
        return max(values, default=0.0)

    def _saturation(self, metrics: dict[str, list[float]]) -> float:
        limit = sum(metrics.get("openinfra_runtime_concurrency_limit", []))
        in_flight = sum(metrics.get("openinfra_http_requests_in_flight", []))
        if limit <= 0:
            return 0.0
        return min(100.0, max(0.0, in_flight * 100.0 / limit))

    @staticmethod
    def _memory_growth(before: dict[str, list[float]], after: dict[str, list[float]]) -> float:
        initial = sum(before.get("openinfra_process_resident_memory_bytes", []))
        final = sum(after.get("openinfra_process_resident_memory_bytes", []))
        if initial <= 0:
            return 0.0
        return max(0.0, (final - initial) * 100.0 / initial)

    @staticmethod
    def _trace_coverage(metrics: dict[str, list[float]]) -> float:
        completed = sum(metrics.get("openinfra_http_requests_total", []))
        traceable = sum(metrics.get("openinfra_http_request_duration_seconds_count", []))
        if completed <= 0:
            return 0.0
        return min(100.0, traceable * 100.0 / completed)

    @staticmethod
    def _metrics_complete(metrics: dict[str, list[float]]) -> bool:
        required = {
            "openinfra_build_info",
            "openinfra_http_requests_total",
            "openinfra_http_request_duration_seconds_count",
            "openinfra_process_resident_memory_bytes",
            "openinfra_process_cpu_seconds",
        }
        return required.issubset(metrics)

    @staticmethod
    def _leak_detected(before: dict[str, list[float]], after: dict[str, list[float]]) -> bool:
        before_gc = sum(before.get("openinfra_python_gc_objects", []))
        after_gc = sum(after.get("openinfra_python_gc_objects", []))
        if before_gc <= 0:
            return False
        return after_gc > before_gc * 1.25


class EnterpriseCapacityLoadCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="run-enterprise-capacity-profile")
        parser.add_argument("--base-url", required=True)
        parser.add_argument("--metrics-url", required=True)
        parser.add_argument("--path", default="/health")
        parser.add_argument(
            "--stage",
            choices=("baseline", "step-load", "endurance", "spike", "saturation"),
            required=True,
        )
        parser.add_argument("--duration-seconds", type=float, required=True)
        parser.add_argument("--concurrency", type=int, required=True)
        parser.add_argument("--target-rps", type=float, required=True)
        parser.add_argument("--timeout-seconds", type=float, default=10.0)
        parser.add_argument("--token-env", default="OPENINFRA_CAPACITY_BEARER_TOKEN")
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args(argv)
        runner = EnterpriseCapacityLoadRunner(
            base_url=args.base_url,
            metrics_url=args.metrics_url,
            path=args.path,
            token=os.environ.get(args.token_env, ""),
            timeout_seconds=args.timeout_seconds,
        )
        evidence = asyncio.run(
            runner.run(
                LoadStage(args.stage, args.duration_seconds, args.concurrency, args.target_rps)
            )
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
        args.output.write_text(encoded, encoding="utf-8")
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        print(json.dumps({"output": str(args.output), "sha256": digest, "stage": args.stage}))
        return 0


if __name__ == "__main__":
    raise SystemExit(EnterpriseCapacityLoadCli.main())
