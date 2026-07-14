from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.quality.multisite_chaos import MultisiteChaosCampaignEvidence

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


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


class ChaosHarness:
    def __init__(
        self,
        executable: Path,
        *,
        timeout_seconds: float,
        command_runner: CommandRunner = _run_command,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValidationError("harness timeout_seconds must be positive")
        resolved = executable.expanduser()
        if not resolved.is_absolute():
            raise ValidationError("chaos harness path must be absolute")
        if resolved.is_symlink() or not resolved.is_file():
            raise ValidationError("chaos harness must be a regular non-symlink file")
        mode = resolved.stat().st_mode
        if not os.access(resolved, os.X_OK):
            raise ValidationError("chaos harness must be executable")
        if mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValidationError("chaos harness must not be group/world writable")
        self._executable = resolved
        self._timeout_seconds = timeout_seconds
        self._command_runner = command_runner

    def preflight(self) -> None:
        payload = self._invoke("preflight", "all")
        if payload.get("status") != "ok":
            raise OpenInfraError("chaos harness preflight did not return status=ok")
        supported = payload.get("supported_scenarios")
        expected = list(MultisiteChaosCampaignEvidence.required_scenarios())
        if supported != expected:
            raise OpenInfraError("chaos harness supported scenario order does not match profile")

    def inject(self, scenario: str) -> dict[str, object]:
        payload = self._invoke("inject", scenario)
        if payload.get("status") != "ok" or payload.get("fault_observed") is not True:
            raise OpenInfraError(f"chaos harness did not confirm fault injection for {scenario}")
        return payload

    def recover(self, scenario: str) -> None:
        payload = self._invoke("recover", scenario)
        if payload.get("status") != "ok":
            raise OpenInfraError(f"chaos harness recovery failed for {scenario}")

    def verify_recovered(self, scenario: str) -> dict[str, object]:
        payload = self._invoke("verify-recovered", scenario)
        if payload.get("status") != "ok":
            raise OpenInfraError(f"chaos harness recovery verification failed for {scenario}")
        return payload

    def _invoke(self, action: str, scenario: str) -> dict[str, object]:
        command = (str(self._executable), action, "--scenario", scenario)
        try:
            completed = self._command_runner(command, self._timeout_seconds)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OpenInfraError(f"chaos harness command failed: {exc}") from exc
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise OpenInfraError(
                f"chaos harness {action}/{scenario} returned {completed.returncode}: {stderr}"
            )
        try:
            payload: Any = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise OpenInfraError(
                f"chaos harness {action}/{scenario} did not return valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise OpenInfraError(f"chaos harness {action}/{scenario} JSON root must be an object")
        returned_scenario = str(payload.get("scenario", "")).strip().lower()
        if scenario not in ("all", returned_scenario):
            raise OpenInfraError(
                f"chaos harness {action} returned unexpected scenario: {returned_scenario}"
            )
        return {str(key): value for key, value in payload.items()}


class MultisiteChaosCampaignRunner:
    def __init__(
        self,
        *,
        harness: ChaosHarness,
        health_url: str,
        integrity_url: str,
        token: str,
        observation_seconds: float,
        probe_interval_seconds: float,
        recovery_timeout_seconds: float,
        request_timeout_seconds: float = 10.0,
    ) -> None:
        for name, value in (
            ("observation_seconds", observation_seconds),
            ("probe_interval_seconds", probe_interval_seconds),
            ("recovery_timeout_seconds", recovery_timeout_seconds),
            ("request_timeout_seconds", request_timeout_seconds),
        ):
            if value <= 0:
                raise ValidationError(f"{name} must be positive")
        for name, url in (("health_url", health_url), ("integrity_url", integrity_url)):
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValidationError(f"{name} must be an absolute HTTPS URL")
        self._harness = harness
        self._health_url = health_url
        self._integrity_url = integrity_url
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._observation_seconds = observation_seconds
        self._probe_interval_seconds = probe_interval_seconds
        self._recovery_timeout_seconds = recovery_timeout_seconds
        self._request_timeout_seconds = request_timeout_seconds

    def run_campaign(self, output_directory: Path) -> tuple[dict[str, object], ...]:
        output_directory.mkdir(parents=True, exist_ok=True)
        self._harness.preflight()
        reports: list[dict[str, object]] = []
        with httpx.Client(headers=self._headers, follow_redirects=False) as client:
            for scenario in MultisiteChaosCampaignEvidence.required_scenarios():
                report = self._run_scenario(client, scenario)
                self._write_report(output_directory / f"{scenario}.json", report)
                reports.append(report)
                if not bool(report["recovery_completed"]) or not bool(report["rollback_verified"]):
                    raise OpenInfraError(
                        f"unsafe to continue chaos campaign after failed recovery: {scenario}"
                    )
        return tuple(reports)

    def _run_scenario(self, client: httpx.Client, scenario: str) -> dict[str, object]:
        integrity_before = self._integrity_hash(client)
        started_at = datetime.now(UTC)
        injected = False
        injection_payload: dict[str, object] = {}
        recovery_started = 0.0
        try:
            injection_payload = self._harness.inject(scenario)
            injected = True
            probe_count, available_count = self._observe_fault(client)
        finally:
            if injected:
                recovery_started = time.monotonic()
                self._harness.recover(scenario)
        recovery_completed = self._wait_for_recovery(client) if injected else False
        recovery_seconds = (
            max(0.0, time.monotonic() - recovery_started) if recovery_started else 0.0
        )
        verification = self._harness.verify_recovered(scenario) if recovery_completed else {}
        integrity_after = self._integrity_hash(client) if recovery_completed else "0" * 64
        integrity_verified = integrity_before == integrity_after
        availability_ratio = available_count / probe_count if probe_count else 0.0
        error_rate = 1.0 - availability_ratio
        corruption_detected = injection_payload.get("corruption_detected") is True or (
            verification.get("corruption_detected") is True
        )
        work_lost = injection_payload.get("acknowledged_work_lost") is True or (
            verification.get("acknowledged_work_lost") is True
        )
        return {
            "scenario": scenario,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "fault_injected": injected,
            "controlled_degradation": bool(
                injection_payload.get("fault_observed") is True and probe_count > 0
            ),
            "recovery_completed": recovery_completed,
            "rollback_verified": verification.get("rollback_verified") is True,
            "data_integrity_verified": integrity_verified,
            "corruption_detected": corruption_detected,
            "acknowledged_work_lost": work_lost,
            "recovery_seconds": recovery_seconds,
            "availability_ratio": availability_ratio,
            "error_rate": error_rate,
            "probe_count": probe_count,
            "integrity_sha256_before": integrity_before,
            "integrity_sha256_after": integrity_after,
        }

    def _observe_fault(self, client: httpx.Client) -> tuple[int, int]:
        deadline = time.monotonic() + self._observation_seconds
        total = 0
        available = 0
        while time.monotonic() < deadline or total == 0:
            total += 1
            try:
                response = client.get(self._health_url, timeout=self._request_timeout_seconds)
                if response.status_code < 500:
                    available += 1
            except httpx.HTTPError:
                pass
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(self._probe_interval_seconds, remaining))
        return total, available

    def _wait_for_recovery(self, client: httpx.Client) -> bool:
        deadline = time.monotonic() + self._recovery_timeout_seconds
        while time.monotonic() < deadline:
            try:
                response = client.get(self._health_url, timeout=self._request_timeout_seconds)
                if response.status_code < 500:
                    return True
            except httpx.HTTPError:
                pass
            time.sleep(min(self._probe_interval_seconds, 1.0))
        return False

    def _integrity_hash(self, client: httpx.Client) -> str:
        try:
            response = client.get(self._integrity_url, timeout=self._request_timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenInfraError(f"integrity probe failed: {exc}") from exc
        return hashlib.sha256(response.content).hexdigest()

    @staticmethod
    def _write_report(path: Path, report: dict[str, object]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)


class MultisiteChaosCampaignCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="run-multisite-chaos-campaign")
        parser.add_argument("--harness", type=Path, required=True)
        parser.add_argument("--health-url", required=True)
        parser.add_argument("--integrity-url", required=True)
        parser.add_argument("--profile", type=Path, required=True)
        parser.add_argument("--output-directory", type=Path, required=True)
        parser.add_argument("--token-env", default="OPENINFRA_MULTISITE_CHAOS_BEARER_TOKEN")
        parser.add_argument("--harness-timeout-seconds", type=float, default=120.0)
        args = parser.parse_args(argv)
        try:
            profile = _load_json_object(args.profile)
            runner = MultisiteChaosCampaignRunner(
                harness=ChaosHarness(
                    args.harness,
                    timeout_seconds=args.harness_timeout_seconds,
                ),
                health_url=args.health_url,
                integrity_url=args.integrity_url,
                token=os.environ.get(args.token_env, ""),
                observation_seconds=float(profile["observation_seconds"]),
                probe_interval_seconds=float(profile["probe_interval_seconds"]),
                recovery_timeout_seconds=float(profile["recovery_timeout_seconds"]),
            )
            reports = runner.run_campaign(args.output_directory)
        except (KeyError, TypeError, ValueError, OSError, OpenInfraError) as exc:
            print(f"multisite-chaos-campaign: FAIL: {exc}")
            return 2
        print(
            json.dumps(
                {
                    "status": "completed",
                    "scenario_count": len(reports),
                    "scenarios": [str(report["scenario"]) for report in reports],
                    "output_directory": str(args.output_directory),
                },
                sort_keys=True,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(MultisiteChaosCampaignCli.main())
