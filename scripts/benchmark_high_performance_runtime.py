#!/usr/bin/env python3
"""Run the deterministic ASGI transport regression benchmark for OpenInfra."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import ClassVar

import httpx

from openinfra import __version__
from openinfra.application.container import ApplicationFactory
from openinfra.interfaces.asgi import OpenInfraApiAsgiApplication
from openinfra.interfaces.asgi_web import (
    OpenInfraWebAsgiApplication,
    OpenInfraWebHttpPoolSettings,
)
from openinfra.interfaces.http_api import OpenInfraApiRuntime
from openinfra.interfaces.web import OpenInfraWebConfig, OpenInfraWebStaticLocator


@dataclass(frozen=True, slots=True)
class RuntimeBenchmarkThreshold:
    p95_ms: float
    p99_ms: float


@dataclass(frozen=True, slots=True)
class RuntimeBenchmarkResult:
    scenario: str
    requests: int
    concurrency: int
    throughput_requests_per_second: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    threshold_p95_ms: float
    threshold_p99_ms: float
    passed: bool


class RuntimeLatencyDistribution:
    def __init__(self, samples_ms: list[float]) -> None:
        if not samples_ms:
            raise ValueError("at least one latency sample is required")
        self._samples = sorted(samples_ms)

    def percentile(self, percentile: float) -> float:
        if percentile <= 0 or percentile > 100:
            raise ValueError("percentile must be in the interval ]0, 100]")
        rank = max(1, math.ceil((percentile / 100.0) * len(self._samples)))
        return self._samples[min(rank - 1, len(self._samples) - 1)]

    @property
    def maximum(self) -> float:
        return self._samples[-1]


class OpenInfraHighPerformanceRuntimeBenchmark:
    """Measure async API, web bootstrap and BFF proxy transport regressions.

    This benchmark is a deterministic CI transport gate. It validates async
    concurrency, persistent clients, streaming paths and percentile budgets. It
    does not replace the PostgreSQL-backed endurance and chaos qualification
    planned for the dedicated Pro/Enterprise performance environment.
    """

    _thresholds: ClassVar[dict[str, RuntimeBenchmarkThreshold]] = {
        "api-health": RuntimeBenchmarkThreshold(150.0, 300.0),
        "web-bootstrap": RuntimeBenchmarkThreshold(150.0, 300.0),
        "bff-proxy": RuntimeBenchmarkThreshold(200.0, 400.0),
    }

    def __init__(self, requests: int, concurrency: int, warmups: int) -> None:
        if requests <= 0:
            raise ValueError("requests must be positive")
        if concurrency <= 0 or concurrency > requests:
            raise ValueError("concurrency must be positive and not exceed requests")
        if warmups < 0:
            raise ValueError("warmups cannot be negative")
        self._requests = requests
        self._concurrency = concurrency
        self._warmups = warmups

    async def run(self) -> dict[str, object]:
        with tempfile.TemporaryDirectory(prefix="openinfra-asgi-benchmark-") as directory:
            state_path = Path(directory) / "state.json"
            application = ApplicationFactory().create_json_application(state_path, edition="pro")
            api_app = OpenInfraApiAsgiApplication(OpenInfraApiRuntime(application))
            api_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api_app),
                base_url="http://openinfra-api",
            )

            async def backend(request: httpx.Request) -> httpx.Response:
                return httpx.Response(
                    200,
                    json={"service": "openinfra-api", "path": request.url.path},
                    headers={"cache-control": "no-store"},
                )

            backend_client = httpx.AsyncClient(transport=httpx.MockTransport(backend))
            benchmark_token = hashlib.sha256(b"openinfra-runtime-benchmark").hexdigest()
            web_config = OpenInfraWebConfig(
                host="127.0.0.1",
                port=2006,
                backend_url="http://openinfra-api:8080",
                public_api_base_url="/api",
                public_api_docs_base_url="",
                static_root=OpenInfraWebStaticLocator().resolve(None),
                edition="pro",
                auth_mode="standard",
                allow_insecure_backend=True,
                backend_bearer_token=benchmark_token,
            )
            web_app = OpenInfraWebAsgiApplication(
                web_config,
                OpenInfraWebHttpPoolSettings(200, 50, 30, 2, 30, 30, 2),
                client=backend_client,
            )
            web_client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=web_app),
                base_url="http://openinfra-web",
            )
            try:
                results = [
                    await self._measure("api-health", api_client, "/health"),
                    await self._measure("web-bootstrap", web_client, "/bootstrap.json"),
                    await self._measure("bff-proxy", web_client, "/api/v1/version"),
                ]
            finally:
                await api_client.aclose()
                await web_client.aclose()
                await backend_client.aclose()
                close = getattr(application.store, "close", None)
                if callable(close):
                    close()

        return {
            "service": "openinfra",
            "version": __version__,
            "scope": "asgi-transport-regression",
            "capacity_certification": False,
            "requests_per_scenario": self._requests,
            "concurrency": self._concurrency,
            "warmups": self._warmups,
            "passed": all(result.passed for result in results),
            "results": [asdict(result) for result in results],
        }

    async def _measure(
        self,
        scenario: str,
        client: httpx.AsyncClient,
        path: str,
    ) -> RuntimeBenchmarkResult:
        for _ in range(self._warmups):
            response = await client.get(path)
            response.raise_for_status()

        semaphore = asyncio.Semaphore(self._concurrency)

        async def request_once() -> float:
            async with semaphore:
                started = time.perf_counter_ns()
                response = await client.get(path)
                response.raise_for_status()
                elapsed_ns = time.perf_counter_ns() - started
                return elapsed_ns / 1_000_000.0

        started = time.perf_counter()
        samples = await asyncio.gather(*(request_once() for _ in range(self._requests)))
        elapsed = max(time.perf_counter() - started, 0.000001)
        distribution = RuntimeLatencyDistribution(samples)
        threshold = self._thresholds[scenario]
        p50 = distribution.percentile(50)
        p95 = distribution.percentile(95)
        p99 = distribution.percentile(99)
        return RuntimeBenchmarkResult(
            scenario=scenario,
            requests=self._requests,
            concurrency=self._concurrency,
            throughput_requests_per_second=round(self._requests / elapsed, 3),
            p50_ms=round(p50, 3),
            p95_ms=round(p95, 3),
            p99_ms=round(p99, 3),
            max_ms=round(distribution.maximum, 3),
            threshold_p95_ms=threshold.p95_ms,
            threshold_p99_ms=threshold.p99_ms,
            passed=p95 <= threshold.p95_ms and p99 <= threshold.p99_ms,
        )


class OpenInfraHighPerformanceRuntimeBenchmarkCli:
    @staticmethod
    def parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Run the OpenInfra ASGI p95/p99 transport regression benchmark."
        )
        parser.add_argument("--requests", type=int, default=500)
        parser.add_argument("--concurrency", type=int, default=50)
        parser.add_argument("--warmups", type=int, default=25)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--enforce", action="store_true")
        return parser

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = cls.parser().parse_args(argv)
        try:
            report = asyncio.run(
                OpenInfraHighPerformanceRuntimeBenchmark(
                    requests=args.requests,
                    concurrency=args.concurrency,
                    warmups=args.warmups,
                ).run()
            )
        except (OSError, RuntimeError, ValueError, httpx.HTTPError) as exc:
            sys.stderr.write(f"openinfra-performance-benchmark: error: {exc}\n")
            return 2
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        sys.stdout.write(payload)
        return 1 if args.enforce and not bool(report["passed"]) else 0


if __name__ == "__main__":
    raise SystemExit(OpenInfraHighPerformanceRuntimeBenchmarkCli.main())
