from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from scripts.run_enterprise_workload_benchmark import (
    BenchmarkWorkload,
    EnterpriseWorkloadBenchmarkRunner,
)

from openinfra.domain.common import ValidationError

_REQUIRED_WORKLOADS = ("api", "ipam", "imports", "discovery", "database", "graph")


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read benchmark JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"benchmark JSON root must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def load_workload_paths(path: Path) -> dict[str, str]:
    payload = _load_json_object(path)
    keys = tuple(sorted(payload))
    expected = tuple(sorted(_REQUIRED_WORKLOADS))
    if keys != expected:
        raise ValidationError(
            "benchmark path configuration must contain exactly: " + ", ".join(_REQUIRED_WORKLOADS)
        )
    result: dict[str, str] = {}
    for workload in _REQUIRED_WORKLOADS:
        value = payload[workload]
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"benchmark path for {workload} must be a non-empty string")
        result[workload] = value.strip()
    return result


def load_recommendations(profile_path: Path) -> dict[str, dict[str, float | int]]:
    profile = _load_json_object(profile_path)
    required = profile.get("required_benchmark_workloads")
    recommendations = profile.get("benchmark_recommendations")
    if required != list(_REQUIRED_WORKLOADS):
        raise ValidationError("capacity profile benchmark workload order is invalid")
    if not isinstance(recommendations, dict):
        raise ValidationError("capacity profile benchmark_recommendations must be an object")
    result: dict[str, dict[str, float | int]] = {}
    for workload in _REQUIRED_WORKLOADS:
        item = recommendations.get(workload)
        if not isinstance(item, dict):
            raise ValidationError(f"missing benchmark recommendation for {workload}")
        try:
            duration = float(item["duration_seconds"])
            target_rps = float(item["target_rps"])
            concurrency = int(item["concurrency"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"invalid benchmark recommendation for {workload}") from exc
        if duration <= 0 or target_rps <= 0 or concurrency <= 0:
            raise ValidationError(f"benchmark recommendation for {workload} must be positive")
        result[workload] = {
            "duration_seconds": duration,
            "target_rps": target_rps,
            "concurrency": concurrency,
        }
    return result


async def run_benchmark_suite(
    *,
    base_url: str,
    token: str,
    timeout_seconds: float,
    paths: dict[str, str],
    recommendations: dict[str, dict[str, float | int]],
    output_directory: Path,
    duration_scale: float = 1.0,
) -> tuple[dict[str, object], ...]:
    if duration_scale <= 0 or duration_scale > 1:
        raise ValidationError("duration_scale must be greater than zero and at most one")
    runner = EnterpriseWorkloadBenchmarkRunner(
        base_url=base_url,
        token=token,
        timeout_seconds=timeout_seconds,
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for workload in _REQUIRED_WORKLOADS:
        recommendation = recommendations[workload]
        report = await runner.run(
            BenchmarkWorkload(
                name=workload,
                path=paths[workload],
                duration_seconds=float(recommendation["duration_seconds"]) * duration_scale,
                concurrency=int(recommendation["concurrency"]),
                target_rps=float(recommendation["target_rps"]),
            )
        )
        output = output_directory / f"{workload}.json"
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(output)
        reports.append(report)
    return tuple(reports)


class EnterpriseBenchmarkSuiteCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="run-enterprise-benchmark-suite")
        parser.add_argument("--base-url", required=True)
        parser.add_argument("--profile", type=Path, required=True)
        parser.add_argument("--paths", type=Path, required=True)
        parser.add_argument("--output-directory", type=Path, required=True)
        parser.add_argument("--timeout-seconds", type=float, default=10.0)
        parser.add_argument("--duration-scale", type=float, default=1.0)
        parser.add_argument("--token-env", default="OPENINFRA_CAPACITY_BEARER_TOKEN")
        args = parser.parse_args(argv)
        reports = asyncio.run(
            run_benchmark_suite(
                base_url=args.base_url,
                token=os.environ.get(args.token_env, ""),
                timeout_seconds=args.timeout_seconds,
                paths=load_workload_paths(args.paths),
                recommendations=load_recommendations(args.profile),
                output_directory=args.output_directory,
                duration_scale=args.duration_scale,
            )
        )
        print(
            json.dumps(
                {
                    "output_directory": str(args.output_directory),
                    "workloads": [report["workload"] for report in reports],
                }
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(EnterpriseBenchmarkSuiteCli.main())
