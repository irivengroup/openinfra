from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from openinfra.domain.common import ValidationError

_WORKLOADS = ("api", "ipam", "imports", "discovery", "database", "graph")


@dataclass(frozen=True, slots=True)
class BenchmarkWorkload:
    name: str
    path: str
    duration_seconds: float
    concurrency: int
    target_rps: float
    expected_status_codes: tuple[int, ...] = (200,)

    def validate(self) -> None:
        if self.name not in _WORKLOADS:
            raise ValidationError(f"unsupported benchmark workload: {self.name}")
        if not self.path.startswith("/") or self.path.startswith("//"):
            raise ValidationError("benchmark path must be an absolute HTTP path")
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc:
            raise ValidationError("benchmark path must not contain a scheme or authority")
        if self.duration_seconds <= 0 or self.concurrency <= 0 or self.target_rps <= 0:
            raise ValidationError("benchmark duration, concurrency and target_rps must be positive")
        if not self.expected_status_codes or any(
            value < 100 or value > 599 for value in self.expected_status_codes
        ):
            raise ValidationError("expected_status_codes must contain valid HTTP status codes")
        if len(set(self.expected_status_codes)) != len(self.expected_status_codes):
            raise ValidationError("expected_status_codes must be unique")


class EnterpriseWorkloadBenchmarkRunner:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float,
    ) -> None:
        normalized = base_url.rstrip("/")
        parsed = urlsplit(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValidationError("enterprise benchmark base_url must use HTTPS")
        if timeout_seconds <= 0:
            raise ValidationError("timeout_seconds must be positive")
        self._base_url = normalized
        self._token = token
        self._timeout_seconds = timeout_seconds

    async def run(self, workload: BenchmarkWorkload) -> dict[str, object]:
        workload.validate()
        headers = {"accept": "application/json"}
        if self._token:
            headers["authorization"] = f"Bearer {self._token}"
        latencies: list[float] = []
        status_counts: Counter[int] = Counter()
        response_bytes = 0
        failures = 0
        interval = 1.0 / workload.target_rps
        semaphore = asyncio.Semaphore(workload.concurrency)
        pending: set[asyncio.Task[tuple[float, int, int, bool]]] = set()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout_seconds,
            verify=True,
            follow_redirects=False,
            limits=httpx.Limits(
                max_connections=workload.concurrency,
                max_keepalive_connections=workload.concurrency,
            ),
        ) as client:
            started = time.monotonic()
            deadline = started + workload.duration_seconds
            next_dispatch = started
            while time.monotonic() < deadline:
                await asyncio.sleep(max(0.0, next_dispatch - time.monotonic()))
                pending.add(
                    asyncio.create_task(
                        self._request(
                            client, semaphore, workload.path, workload.expected_status_codes
                        )
                    )
                )
                next_dispatch += interval
                if len(pending) >= workload.concurrency * 2:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    result = await asyncio.gather(*done)
                    failures, response_bytes = self._accumulate(
                        result,
                        latencies,
                        status_counts,
                        failures,
                        response_bytes,
                    )
            if pending:
                result = await asyncio.gather(*pending)
                failures, response_bytes = self._accumulate(
                    result,
                    latencies,
                    status_counts,
                    failures,
                    response_bytes,
                )
        elapsed = time.monotonic() - started
        requests = len(latencies)
        if requests == 0:
            raise ValidationError("benchmark workload produced no requests")
        ordered = sorted(latencies)
        return {
            "workload": workload.name,
            "method": "GET",
            "path": workload.path,
            "duration_seconds": elapsed,
            "requests": requests,
            "p95_ms": self._percentile(ordered, 95),
            "p99_ms": self._percentile(ordered, 99),
            "error_rate_percent": failures * 100.0 / requests,
            "throughput_rps": requests / elapsed,
            "response_bytes": response_bytes,
            "expected_status_codes": list(workload.expected_status_codes),
            "status_counts": {str(key): value for key, value in sorted(status_counts.items())},
        }

    async def _request(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        path: str,
        expected_status_codes: tuple[int, ...],
    ) -> tuple[float, int, int, bool]:
        async with semaphore:
            started = time.perf_counter()
            try:
                response = await client.get(path)
                status_code = response.status_code
                body_size = len(response.content)
                failed = status_code not in expected_status_codes
            except httpx.HTTPError:
                status_code = 0
                body_size = 0
                failed = True
            latency_ms = (time.perf_counter() - started) * 1000.0
            return latency_ms, status_code, body_size, failed

    @staticmethod
    def _accumulate(
        results: list[tuple[float, int, int, bool]],
        latencies: list[float],
        status_counts: Counter[int],
        failures: int,
        response_bytes: int,
    ) -> tuple[int, int]:
        for latency_ms, status_code, body_size, failed in results:
            latencies.append(latency_ms)
            status_counts[status_code] += 1
            failures += int(failed)
            response_bytes += body_size
        return failures, response_bytes

    @staticmethod
    def _percentile(values: list[float], percentile: int) -> float:
        if not values:
            return 0.0
        rank = max(0, math.ceil(percentile / 100.0 * len(values)) - 1)
        return values[min(rank, len(values) - 1)]


class EnterpriseWorkloadBenchmarkCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="run-enterprise-workload-benchmark")
        parser.add_argument("--base-url", required=True)
        parser.add_argument("--workload", choices=_WORKLOADS, required=True)
        parser.add_argument("--path", required=True)
        parser.add_argument("--duration-seconds", type=float, required=True)
        parser.add_argument("--concurrency", type=int, required=True)
        parser.add_argument("--target-rps", type=float, required=True)
        parser.add_argument("--timeout-seconds", type=float, default=10.0)
        parser.add_argument("--expected-status", type=int, action="append", default=[])
        parser.add_argument("--token-env", default="OPENINFRA_CAPACITY_BEARER_TOKEN")
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args(argv)
        runner = EnterpriseWorkloadBenchmarkRunner(
            base_url=args.base_url,
            token=os.environ.get(args.token_env, ""),
            timeout_seconds=args.timeout_seconds,
        )
        evidence = asyncio.run(
            runner.run(
                BenchmarkWorkload(
                    name=args.workload,
                    path=args.path,
                    duration_seconds=args.duration_seconds,
                    concurrency=args.concurrency,
                    target_rps=args.target_rps,
                    expected_status_codes=tuple(args.expected_status or [200]),
                )
            )
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(args.output)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                    "workload": args.workload,
                }
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(EnterpriseWorkloadBenchmarkCli.main())
