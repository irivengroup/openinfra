from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any


class ObservabilityValidationError(RuntimeError):
    pass


yaml = importlib.import_module("yaml")


class OpenInfraObservabilityValidator:
    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> None:
        required = (
            "src/openinfra/infrastructure/observability.py",
            "src/openinfra/interfaces/asgi_observability.py",
            "docker/observability/prometheus.yml",
            "docker/observability/openinfra-alerts.yml",
            "docker/observability/otel-collector.yaml",
            "docker/observability/tempo.yaml",
            "docker/observability/grafana/provisioning/datasources/openinfra.yml",
            "docker/observability/grafana/provisioning/dashboards/openinfra.yml",
            "docker/observability/grafana/dashboards/openinfra-enterprise-runtime.json",
            "docs/architecture/enterprise-observability-capacity.md",
            "docs/runbooks/OBSERVABILITY_CAPACITY.md",
            "docs/operations/enterprise-capacity-profile.json",
            ".github/workflows/enterprise-capacity.yml",
            "scripts/run_enterprise_capacity_profile.py",
            "scripts/run_enterprise_chaos_profile.py",
            "scripts/assemble_enterprise_capacity_evidence.py",
            "scripts/certify_enterprise_capacity.py",
        )
        missing = [name for name in required if not (self._root / name).is_file()]
        if missing:
            raise ObservabilityValidationError(
                "missing observability assets: " + ", ".join(missing)
            )
        self._validate_yaml()
        self._validate_dashboard()
        self._validate_compose()
        self._validate_runtime_contracts()
        self._validate_capacity_profile()

    def _validate_yaml(self) -> None:
        files = (
            "docker/observability/prometheus.yml",
            "docker/observability/openinfra-alerts.yml",
            "docker/observability/otel-collector.yaml",
            "docker/observability/tempo.yaml",
            "docker/observability/grafana/provisioning/datasources/openinfra.yml",
            "docker/observability/grafana/provisioning/dashboards/openinfra.yml",
        )
        for name in files:
            payload: Any = yaml.safe_load((self._root / name).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ObservabilityValidationError(
                    f"observability YAML root must be an object: {name}"
                )
        alerts: Any = yaml.safe_load(
            (self._root / "docker/observability/openinfra-alerts.yml").read_text(encoding="utf-8")
        )
        encoded = json.dumps(alerts)
        for alert in (
            "OpenInfraApiP95LatencyHigh",
            "OpenInfraApiP99LatencyCritical",
            "OpenInfraHttpErrorRateHigh",
            "OpenInfraAsyncQueueStalled",
            "OpenInfraDeadLetterQueueNotEmpty",
            "OpenInfraReplicaLagHigh",
            "OpenInfraDatabasePoolWaiting",
            "OpenInfraRuntimeSaturationHigh",
            "OpenInfraMetricsMissing",
        ):
            if alert not in encoded:
                raise ObservabilityValidationError(f"missing Prometheus alert: {alert}")

    def _validate_dashboard(self) -> None:
        dashboard: Any = json.loads(
            (
                self._root
                / "docker/observability/grafana/dashboards/openinfra-enterprise-runtime.json"
            ).read_text(encoding="utf-8")
        )
        if (
            not isinstance(dashboard, dict)
            or dashboard.get("uid") != "openinfra-enterprise-runtime"
        ):
            raise ObservabilityValidationError("invalid OpenInfra Grafana dashboard identity")
        panels = dashboard.get("panels")
        if not isinstance(panels, list) or len(panels) < 7:
            raise ObservabilityValidationError(
                "OpenInfra Grafana dashboard must expose core SLO panels"
            )

    def _validate_compose(self) -> None:
        compose: Any = yaml.safe_load((self._root / "compose.yaml").read_text(encoding="utf-8"))
        if not isinstance(compose, dict) or not isinstance(compose.get("services"), dict):
            raise ObservabilityValidationError("compose.yaml services are invalid")
        services = compose["services"]
        for name in ("otel-collector", "tempo", "prometheus", "grafana"):
            service = services.get(name)
            if not isinstance(service, dict) or "observability" not in service.get("profiles", []):
                raise ObservabilityValidationError(
                    f"compose observability service must be profile-scoped: {name}"
                )
        expected_tmpfs = "/tmp/openinfra-prometheus:mode=0770,uid=10001,gid=10001"  # noqa: S108
        for name in ("api", "web"):
            service = services.get(name)
            if not isinstance(service, dict):
                raise ObservabilityValidationError(f"compose service missing: {name}")
            environment = service.get("environment", {})
            if not isinstance(environment, dict) or "PROMETHEUS_MULTIPROC_DIR" not in environment:
                raise ObservabilityValidationError(
                    f"compose {name} lacks multiprocess Prometheus setup"
                )
            tmpfs = service.get("tmpfs", [])
            if not isinstance(tmpfs, list) or expected_tmpfs not in tmpfs:
                raise ObservabilityValidationError(
                    f"compose {name} Prometheus tmpfs owner must be 10001:10001"
                )

        dockerfile = (self._root / "Dockerfile").read_text(encoding="utf-8")
        required_runtime_identity = (
            "ARG OPENINFRA_UID=10001",
            "ARG OPENINFRA_GID=10001",
            'groupadd --gid "${OPENINFRA_GID}" openinfra',
            'useradd --uid "${OPENINFRA_UID}" --gid openinfra',
        )
        if any(fragment not in dockerfile for fragment in required_runtime_identity):
            raise ObservabilityValidationError(
                "Docker runtime user must match the Prometheus tmpfs owner 10001:10001"
            )

    def _validate_runtime_contracts(self) -> None:
        observability = (self._root / "src/openinfra/infrastructure/observability.py").read_text(
            encoding="utf-8"
        )
        forbidden = ('"tenant_id"', '"actor"', '"subject"', '"object_id"')
        metric_region = observability[observability.find("self._build_info") :]
        if any(value in metric_region for value in forbidden):
            raise ObservabilityValidationError(
                "Prometheus metric definitions cannot expose tenant or business identifiers"
            )
        required_metrics = (
            "openinfra_http_request_duration_seconds",
            "openinfra_async_queue_depth",
            "openinfra_worker_runs_total",
            "openinfra_db_pool_state",
            "openinfra_db_replica_lag_seconds",
            "openinfra_process_resident_memory_bytes",
        )
        missing = [name for name in required_metrics if name not in observability]
        if missing:
            raise ObservabilityValidationError("missing runtime metrics: " + ", ".join(missing))
        for name in (
            "src/openinfra/interfaces/asgi.py",
            "src/openinfra/interfaces/asgi_web.py",
        ):
            content = (self._root / name).read_text(encoding="utf-8")
            if '"/metrics"' not in content or "begin_http_request" not in content:
                raise ObservabilityValidationError(
                    f"ASGI observability integration incomplete: {name}"
                )
        for name in (
            "docs/api/openapi.yaml",
            "docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml",
        ):
            if "  /metrics:" not in (self._root / name).read_text(encoding="utf-8"):
                raise ObservabilityValidationError(f"OpenAPI metrics contract missing: {name}")

    def _validate_capacity_profile(self) -> None:
        profile: Any = json.loads(
            (self._root / "docs/operations/enterprise-capacity-profile.json").read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(profile, dict) or profile.get("profile_version") != 2:
            raise ObservabilityValidationError("capacity profile must use certification schema v2")
        if profile.get("required_benchmark_workloads") != [
            "api",
            "ipam",
            "imports",
            "discovery",
            "database",
            "graph",
        ]:
            raise ObservabilityValidationError(
                "capacity profile must define the six EPIC-1801 benchmark workloads"
            )
        if len(profile.get("required_capacity_stages", [])) != 5:
            raise ObservabilityValidationError("capacity profile must define five load stages")
        if len(profile.get("required_chaos_scenarios", [])) != 4:
            raise ObservabilityValidationError("capacity profile must define four chaos scenarios")


class OpenInfraObservabilityValidatorCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="validate-observability")
        parser.add_argument("--project-root", type=Path, default=Path("."))
        args = parser.parse_args(argv)
        try:
            OpenInfraObservabilityValidator(args.project_root).validate()
        except ObservabilityValidationError as exc:
            print(f"observability-validation: FAIL: {exc}")
            return 1
        print("observability-validation: PASS")
        return 0


if __name__ == "__main__":
    raise SystemExit(OpenInfraObservabilityValidatorCli.main())
