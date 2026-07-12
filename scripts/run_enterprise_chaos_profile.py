from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

import httpx

from openinfra.domain.common import OpenInfraError, ValidationError

_SCENARIO_SERVICES: Final[dict[str, str]] = {
    "api-worker-loss": "api",
    "web-worker-loss": "web",
    "db-replica-loss": "postgres-replica",
    "pgbouncer-restart": "pgbouncer-primary",
}

CommandRunner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


def _run_command(
    command: Sequence[str], timeout_seconds: float
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


class DockerComposeChaosRunner:
    def __init__(
        self,
        *,
        compose_file: Path,
        project_directory: Path,
        health_url: str,
        integrity_url: str,
        timeout_seconds: float,
        command_runner: CommandRunner = _run_command,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValidationError("chaos timeout_seconds must be positive")
        if not compose_file.is_file():
            raise ValidationError(f"compose file does not exist: {compose_file}")
        if not project_directory.is_dir():
            raise ValidationError(f"project directory does not exist: {project_directory}")
        self._compose_file = compose_file.resolve()
        self._project_directory = project_directory.resolve()
        self._health_url = health_url
        self._integrity_url = integrity_url
        self._timeout_seconds = timeout_seconds
        self._command_runner = command_runner

    def run(self, scenario: str) -> dict[str, object]:
        normalized = scenario.strip().lower()
        service = _SCENARIO_SERVICES.get(normalized)
        if service is None:
            raise ValidationError(f"unsupported chaos scenario: {normalized or '<empty>'}")
        before_hash = self._integrity_hash()
        stopped = self._compose("stop", service)
        fault_injected = stopped.returncode == 0
        if not fault_injected:
            raise OpenInfraError(
                f"failed to inject chaos fault for {service}: {stopped.stderr.strip()}"
            )
        started_at = time.monotonic()
        restored = self._compose("up", "-d", service)
        if restored.returncode != 0:
            raise OpenInfraError(f"failed to restore {service}: {restored.stderr.strip()}")
        recovered = self._wait_for_recovery()
        recovery_seconds = max(0.0, time.monotonic() - started_at)
        after_hash = self._integrity_hash() if recovered else ""
        integrity_verified = bool(before_hash and before_hash == after_hash)
        return {
            "scenario": normalized,
            "fault_injected": fault_injected,
            "service_recovered": recovered,
            "recovery_seconds": recovery_seconds,
            "data_integrity_verified": integrity_verified,
            "acknowledged_work_lost": not integrity_verified,
            "service": service,
            "integrity_sha256_before": before_hash,
            "integrity_sha256_after": after_hash,
        }

    def _compose(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        command = (
            "docker",
            "compose",
            "--project-directory",
            str(self._project_directory),
            "--file",
            str(self._compose_file),
            *arguments,
        )
        try:
            return self._command_runner(command, self._timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OpenInfraError(f"docker compose chaos command failed: {exc}") from exc

    def _wait_for_recovery(self) -> bool:
        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            try:
                response = httpx.get(self._health_url, timeout=min(5.0, self._timeout_seconds))
                if response.status_code < 500:
                    return True
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        return False

    def _integrity_hash(self) -> str:
        try:
            response = httpx.get(self._integrity_url, timeout=min(10.0, self._timeout_seconds))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenInfraError(f"integrity probe failed: {exc}") from exc
        return hashlib.sha256(response.content).hexdigest()


class EnterpriseChaosCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="run-enterprise-chaos-profile")
        parser.add_argument("--scenario", choices=tuple(_SCENARIO_SERVICES), required=True)
        parser.add_argument("--compose-file", type=Path, default=Path("compose.yaml"))
        parser.add_argument("--project-directory", type=Path, default=Path("."))
        parser.add_argument("--health-url", required=True)
        parser.add_argument("--integrity-url", required=True)
        parser.add_argument("--timeout-seconds", type=float, default=120.0)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args(argv)
        try:
            report = DockerComposeChaosRunner(
                compose_file=args.compose_file,
                project_directory=args.project_directory,
                health_url=args.health_url,
                integrity_url=args.integrity_url,
                timeout_seconds=args.timeout_seconds,
            ).run(args.scenario)
        except OpenInfraError as exc:
            print(json.dumps({"scenario": args.scenario, "error": str(exc)}, sort_keys=True))
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))
        return (
            0
            if bool(report["service_recovered"]) and bool(report["data_integrity_verified"])
            else 1
        )


if __name__ == "__main__":
    raise SystemExit(EnterpriseChaosCli.main())
