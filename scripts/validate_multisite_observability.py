from __future__ import annotations

import argparse
import importlib
import json
import re
from pathlib import Path
from typing import Any


class MultisiteObservabilityValidationError(RuntimeError):
    pass


yaml = importlib.import_module("yaml")


class MultisiteObservabilityValidator:
    _required_alerts = (
        "OpenInfraMultisiteApiUnavailable",
        "OpenInfraMultisiteApiP95LatencyHigh",
        "OpenInfraMultisiteAgentLagHigh",
        "OpenInfraMultisiteAgentUnhealthy",
        "OpenInfraMultisiteDatabaseLagHigh",
        "OpenInfraMultisiteJobsStalled",
    )
    _required_metrics = (
        "openinfra_multisite_agent_lag_seconds",
        "openinfra_multisite_agent_health",
        "openinfra_multisite_agent_collectors",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        required = (
            "src/openinfra/infrastructure/multisite_observability.py",
            "src/openinfra/infrastructure/observability.py",
            "docker/observability/prometheus.yml",
            "docker/observability/openinfra-alerts.yml",
            "docker/observability/grafana/dashboards/openinfra-multisite-operations.json",
            "docs/operations/multisite-observability-profile.json",
            "docs/runbooks/MULTISITE_OBSERVABILITY.md",
        )
        missing = [name for name in required if not (self._root / name).is_file()]
        if missing:
            raise MultisiteObservabilityValidationError(
                "missing multisite observability assets: " + ", ".join(missing)
            )
        profile = self._validate_profile()
        self._validate_prometheus()
        self._validate_alerts()
        self._validate_dashboard()
        self._validate_runtime()
        self._validate_compose()
        return {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "required_signals": len(profile["required_signals"]),
            "alerts": len(self._required_alerts),
            "status": "passed",
        }

    def _validate_profile(self) -> dict[str, Any]:
        payload = json.loads(
            (self._root / "docs/operations/multisite-observability-profile.json").read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(payload, dict):
            raise MultisiteObservabilityValidationError("multisite profile root must be an object")
        if payload.get("profile_id") != "openinfra-multisite-observability-v1":
            raise MultisiteObservabilityValidationError(
                "invalid multisite observability profile id"
            )
        if payload.get("profile_version") != 1:
            raise MultisiteObservabilityValidationError(
                "multisite observability profile version must be 1"
            )
        expected_signals = [
            "api_availability",
            "api_latency",
            "agent_heartbeat",
            "database_replication",
            "jobs",
            "site_health",
        ]
        if payload.get("required_signals") != expected_signals:
            raise MultisiteObservabilityValidationError(
                "multisite observability profile must define the six EPIC-1705 signals"
            )
        thresholds = payload.get("thresholds")
        if thresholds != {
            "agent_lag_seconds": 120,
            "database_replica_lag_seconds": 5,
            "api_p95_seconds": 0.5,
            "job_oldest_ready_age_seconds": 300,
        }:
            raise MultisiteObservabilityValidationError(
                "multisite observability thresholds are not the approved v1 contract"
            )
        if payload.get("target_labels") != ["region", "site", "service"]:
            raise MultisiteObservabilityValidationError(
                "multisite target labels must be region, site and service"
            )
        if payload.get("max_regional_routes") != 10_000:
            raise MultisiteObservabilityValidationError(
                "multisite route cardinality limit must be 10000"
            )
        return payload

    def _validate_prometheus(self) -> None:
        payload: Any = yaml.safe_load(
            (self._root / "docker/observability/prometheus.yml").read_text(encoding="utf-8")
        )
        configs = payload.get("scrape_configs", []) if isinstance(payload, dict) else []
        jobs = {
            item.get("job_name"): item
            for item in configs
            if isinstance(item, dict) and isinstance(item.get("job_name"), str)
        }
        job = jobs.get("openinfra-multisite")
        if not isinstance(job, dict):
            raise MultisiteObservabilityValidationError(
                "Prometheus openinfra-multisite scrape job is missing"
            )
        if job.get("scheme") != "https" or job.get("metrics_path") != "/metrics":
            raise MultisiteObservabilityValidationError(
                "multisite scrape must use HTTPS and the /metrics endpoint"
            )
        encoded = json.dumps(job, sort_keys=True)
        if "/etc/prometheus/multisite-targets/*.json" not in encoded:
            raise MultisiteObservabilityValidationError(
                "multisite scrape must use bounded file service discovery"
            )
        if job.get("follow_redirects") is not False:
            raise MultisiteObservabilityValidationError(
                "multisite scrape redirects must remain disabled"
            )

    def _validate_alerts(self) -> None:
        alerts = (self._root / "docker/observability/openinfra-alerts.yml").read_text(
            encoding="utf-8"
        )
        missing = [name for name in self._required_alerts if name not in alerts]
        if missing:
            raise MultisiteObservabilityValidationError(
                "missing multisite alerts: " + ", ".join(missing)
            )
        for label in ("region", "site"):
            if f"$labels.{label}" not in alerts:
                raise MultisiteObservabilityValidationError(
                    f"multisite alert annotations must expose the {label} label"
                )

    def _validate_dashboard(self) -> None:
        payload = json.loads(
            (
                self._root
                / "docker/observability/grafana/dashboards/openinfra-multisite-operations.json"
            ).read_text(encoding="utf-8")
        )
        if payload.get("uid") != "openinfra-multisite-operations":
            raise MultisiteObservabilityValidationError("invalid multisite dashboard uid")
        panels = payload.get("panels")
        if not isinstance(panels, list) or len(panels) < 8:
            raise MultisiteObservabilityValidationError(
                "multisite dashboard must expose at least eight operational panels"
            )
        encoded = json.dumps(payload, sort_keys=True)
        for signal in (
            "openinfra_multisite_agent_lag_seconds",
            "openinfra_db_replica_lag_seconds",
            "openinfra_async_oldest_ready_age_seconds",
            "openinfra_http_request_duration_seconds_bucket",
        ):
            if signal not in encoded:
                raise MultisiteObservabilityValidationError(
                    f"multisite dashboard signal is missing: {signal}"
                )
        for variable in ("region", "site"):
            if f'"name": "{variable}"' not in json.dumps(payload, indent=2):
                raise MultisiteObservabilityValidationError(
                    f"multisite dashboard variable is missing: {variable}"
                )

    def _validate_runtime(self) -> None:
        telemetry = (self._root / "src/openinfra/infrastructure/observability.py").read_text(
            encoding="utf-8"
        )
        provider = (
            self._root / "src/openinfra/infrastructure/multisite_observability.py"
        ).read_text(encoding="utf-8")
        for metric in self._required_metrics:
            if metric not in telemetry:
                raise MultisiteObservabilityValidationError(
                    f"multisite runtime metric is missing: {metric}"
                )
        if '"tenant_id"' in telemetry[telemetry.find("self._multisite_agent_lag") :]:
            raise MultisiteObservabilityValidationError(
                "multisite Prometheus labels cannot expose tenant identifiers"
            )
        if "_max_routes: Final[int] = 10_000" not in provider:
            raise MultisiteObservabilityValidationError(
                "multisite metrics provider must retain a hard route cardinality bound"
            )
        if not re.search(r'\("region", "site"\)', telemetry):
            raise MultisiteObservabilityValidationError(
                "multisite metrics must be grouped by bounded region and site labels"
            )

    def _validate_compose(self) -> None:
        compose = (self._root / "compose.yaml").read_text(encoding="utf-8")
        required_mount = (
            "./docker/observability/multisite-targets:/etc/prometheus/multisite-targets:ro"
        )
        if required_mount not in compose:
            raise MultisiteObservabilityValidationError(
                "Prometheus multisite target directory must be mounted read-only"
            )


class MultisiteTargetFileValidator:
    _code = re.compile(r"[A-Z0-9][A-Z0-9_.:-]{0,63}")
    _target = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}:[1-9][0-9]{0,4}")

    @classmethod
    def validate_file(cls, path: Path) -> int:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not payload:
            raise MultisiteObservabilityValidationError(
                "multisite target file must contain a non-empty array"
            )
        count = 0
        seen: set[tuple[str, str, str]] = set()
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                raise MultisiteObservabilityValidationError(
                    f"target group {index} must be an object"
                )
            targets = item.get("targets")
            labels = item.get("labels")
            if not isinstance(targets, list) or not targets or not isinstance(labels, dict):
                raise MultisiteObservabilityValidationError(
                    f"target group {index} requires targets and labels"
                )
            region = str(labels.get("region", "")).strip().upper()
            site = str(labels.get("site", "")).strip().upper()
            service = str(labels.get("service", "")).strip().lower()
            if cls._code.fullmatch(region) is None or cls._code.fullmatch(site) is None:
                raise MultisiteObservabilityValidationError(
                    f"target group {index} region/site labels are invalid"
                )
            if service != "openinfra-api":
                raise MultisiteObservabilityValidationError(
                    f"target group {index} service must be openinfra-api"
                )
            if set(labels) != {"region", "site", "service"}:
                raise MultisiteObservabilityValidationError(
                    f"target group {index} labels must be exactly region, site and service"
                )
            for target in targets:
                normalized = str(target).strip()
                if cls._target.fullmatch(normalized) is None:
                    raise MultisiteObservabilityValidationError(
                        f"target group {index} contains an invalid host:port target"
                    )
                key = (region, site, normalized.lower())
                if key in seen:
                    raise MultisiteObservabilityValidationError(
                        f"duplicate multisite target: {region}/{site}/{normalized}"
                    )
                seen.add(key)
                count += 1
        return count


def validate_project(project_root: Path) -> dict[str, object]:
    return MultisiteObservabilityValidator(project_root).validate()


class MultisiteObservabilityValidatorCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="validate-multisite-observability")
        parser.add_argument("--project-root", type=Path, default=Path("."))
        parser.add_argument("--targets", type=Path)
        args = parser.parse_args(argv)
        try:
            report = validate_project(args.project_root)
            if args.targets is not None:
                report["validated_targets"] = MultisiteTargetFileValidator.validate_file(
                    args.targets
                )
        except (MultisiteObservabilityValidationError, OSError, json.JSONDecodeError) as exc:
            print(f"multisite-observability-validation: FAIL: {exc}")
            return 1
        print(json.dumps(report, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(MultisiteObservabilityValidatorCli.main())
