from __future__ import annotations

import atexit
import gc
import os
import re
import time
from collections.abc import Callable, Mapping
from contextvars import Token
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, local
from typing import Final

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

from openinfra import __version__
from openinfra.application.ports import HttpRequestObservation, RuntimeTelemetry
from openinfra.domain.common import ValidationError

MetricsProvider = Callable[[], dict[str, object]]


class PrometheusMultiprocessDirectory:
    _truthy_values: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})

    @classmethod
    def prepare_from_environment(cls) -> Path | None:
        raw = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "").strip()
        if not raw:
            return None
        path = Path(raw)
        try:
            path.mkdir(parents=True, exist_ok=True, mode=0o770)
            if not path.is_dir():
                raise NotADirectoryError(str(path))
            cls._assert_writable(path)
            if (
                os.environ.get("OPENINFRA_PROMETHEUS_CLEAN_START", "true").strip().lower()
                in cls._truthy_values
            ):
                for candidate in path.glob("*.db"):
                    candidate.unlink(missing_ok=True)
            cls._assert_writable(path)
        except OSError as exc:
            effective_uid = getattr(os, "geteuid", lambda: -1)()
            effective_gid = getattr(os, "getegid", lambda: -1)()
            raise ValidationError(
                "Prometheus multiprocess directory is not writable: "
                f"{path} (uid={effective_uid}, gid={effective_gid}). "
                "Align the runtime user with the directory owner or mount permissions."
            ) from exc
        return path

    @staticmethod
    def _assert_writable(path: Path) -> None:
        probe = path / f".openinfra-prometheus-write-{os.getpid()}-{time.time_ns()}"
        descriptor = os.open(
            probe,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(descriptor, b"ok")
        finally:
            try:
                os.close(descriptor)
            finally:
                probe.unlink(missing_ok=True)

    @staticmethod
    def mark_process_dead() -> None:
        if os.environ.get("PROMETHEUS_MULTIPROC_DIR", "").strip():
            multiprocess.mark_process_dead(os.getpid())  # type: ignore[no-untyped-call]


@dataclass(slots=True)
class OpenTelemetryHttpObservation(HttpRequestObservation):
    span: Span
    context_token: Token[context.Context]
    telemetry: OpenInfraTelemetry
    method: str
    route: str
    started_at: float
    _finished: bool = False

    @property
    def traceparent(self) -> str:
        span_context = self.span.get_span_context()
        if not span_context.is_valid:
            return ""
        flags = int(span_context.trace_flags)
        return f"00-{span_context.trace_id:032x}-{span_context.span_id:016x}-{flags:02x}"

    def record_exception(self, exception: BaseException) -> None:
        self.span.record_exception(exception)
        self.span.set_status(Status(StatusCode.ERROR, type(exception).__name__))

    def finish(
        self,
        *,
        status_code: int,
        request_size_bytes: int,
        response_size_bytes: int,
    ) -> None:
        if self._finished:
            return
        self._finished = True
        duration_seconds = max(0.0, time.perf_counter() - self.started_at)
        status_class = f"{max(0, int(status_code)) // 100}xx"
        self.telemetry._http_in_flight.labels(self.method, self.route).dec()
        self.telemetry._http_requests.labels(self.method, self.route, status_class).inc()
        self.telemetry._http_duration.labels(self.method, self.route).observe(duration_seconds)
        self.telemetry._http_request_bytes.labels(self.method, self.route).inc(
            max(0, int(request_size_bytes))
        )
        self.telemetry._http_response_bytes.labels(self.method, self.route).inc(
            max(0, int(response_size_bytes))
        )
        self.span.set_attribute("http.response.status_code", int(status_code))
        self.span.set_attribute("http.request.body.size", max(0, int(request_size_bytes)))
        self.span.set_attribute("http.response.body.size", max(0, int(response_size_bytes)))
        self.span.set_attribute("openinfra.request.duration_seconds", duration_seconds)
        if status_code >= 500:
            self.span.set_status(Status(StatusCode.ERROR, f"HTTP {status_code}"))
        else:
            self.span.set_status(Status(StatusCode.OK))
        context.detach(self.context_token)
        self.span.end()


class OpenInfraTelemetry(RuntimeTelemetry):
    _route_identifier = re.compile(r"(?i)^(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f-]{27,}|[0-9]{1,20})$")
    _histogram_buckets: Final[tuple[float, ...]] = (
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
    )

    def __init__(
        self,
        *,
        service_name: str,
        edition: str,
        environment: str,
        queue_metrics_provider: MetricsProvider | None = None,
        runtime_metrics_provider: MetricsProvider | None = None,
        multisite_metrics_provider: MetricsProvider | None = None,
    ) -> None:
        normalized_service = service_name.strip().lower()
        normalized_edition = edition.strip().lower()
        if normalized_service not in {"openinfra-api", "openinfra-web", "openinfra-worker"}:
            raise ValidationError("unsupported OpenInfra telemetry service name")
        if normalized_edition not in {"lite", "pro", "enterprise"}:
            raise ValidationError("edition must be lite, pro or enterprise")
        self._service_name = normalized_service
        self._edition = normalized_edition
        self._environment = environment.strip().lower() or "production"
        self._queue_metrics_provider = queue_metrics_provider
        self._runtime_metrics_provider = runtime_metrics_provider
        self._multisite_metrics_provider = multisite_metrics_provider
        self._registry = CollectorRegistry(auto_describe=True)
        self._thread_state = local()
        self._close_lock = Lock()
        self._closed = False
        self._started_at = time.monotonic()

        self._build_info = Gauge(
            "openinfra_build_info",
            "OpenInfra build and runtime identity.",
            ("service", "edition", "version"),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._build_info.labels(self._service_name, self._edition, __version__).set(1)
        self._http_requests = Counter(
            "openinfra_http_requests_total",
            "Completed HTTP requests grouped by normalized route and status class.",
            ("method", "route", "status_class"),
            registry=self._registry,
        )
        self._http_duration = Histogram(
            "openinfra_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            ("method", "route"),
            buckets=self._histogram_buckets,
            registry=self._registry,
        )
        self._http_in_flight = Gauge(
            "openinfra_http_requests_in_flight",
            "HTTP requests currently executing.",
            ("method", "route"),
            registry=self._registry,
            multiprocess_mode="livesum",
        )
        self._http_request_bytes = Counter(
            "openinfra_http_request_bytes_total",
            "HTTP request body bytes received.",
            ("method", "route"),
            registry=self._registry,
        )
        self._http_response_bytes = Counter(
            "openinfra_http_response_bytes_total",
            "HTTP response body bytes emitted.",
            ("method", "route"),
            registry=self._registry,
        )
        self._worker_runs = Counter(
            "openinfra_worker_runs_total",
            "Specialized worker execution outcomes.",
            ("specialization", "outcome"),
            registry=self._registry,
        )
        self._worker_duration = Histogram(
            "openinfra_worker_duration_seconds",
            "Specialized worker execution duration in seconds.",
            ("specialization",),
            buckets=self._histogram_buckets,
            registry=self._registry,
        )
        self._worker_in_flight = Gauge(
            "openinfra_worker_executions_in_flight",
            "Specialized worker executions currently active.",
            ("specialization",),
            registry=self._registry,
            multiprocess_mode="livesum",
        )
        self._outbox_runs = Counter(
            "openinfra_outbox_dispatch_total",
            "Transactional outbox dispatch outcomes.",
            ("outcome",),
            registry=self._registry,
        )
        self._outbox_duration = Histogram(
            "openinfra_outbox_dispatch_duration_seconds",
            "Transactional outbox dispatch duration in seconds.",
            buckets=self._histogram_buckets,
            registry=self._registry,
        )
        self._queue_depth = Gauge(
            "openinfra_async_queue_depth",
            "Tenant-neutral asynchronous queue depth.",
            ("kind", "status"),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._queue_specialization_depth = Gauge(
            "openinfra_async_job_depth",
            "Tenant-neutral asynchronous job depth by worker specialization.",
            ("specialization", "status"),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._queue_oldest_ready = Gauge(
            "openinfra_async_oldest_ready_age_seconds",
            "Age in seconds of the oldest ready asynchronous item.",
            ("kind",),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._db_pool = Gauge(
            "openinfra_db_pool_state",
            "PostgreSQL pool state and acquisition counters.",
            ("target", "metric"),
            registry=self._registry,
            multiprocess_mode="livesum",
        )
        self._replica_lag = Gauge(
            "openinfra_db_replica_lag_seconds",
            "Observed PostgreSQL replica replay lag in seconds.",
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._replica_eligible = Gauge(
            "openinfra_db_replica_eligible",
            "Whether the configured PostgreSQL read replica is eligible for reads.",
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._multisite_agent_lag = Gauge(
            "openinfra_multisite_agent_lag_seconds",
            "Maximum Enterprise discovery agent heartbeat age grouped by region and site.",
            ("region", "site"),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._multisite_agent_health = Gauge(
            "openinfra_multisite_agent_health",
            "Whether every routed discovery agent is healthy for a region and site.",
            ("region", "site"),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._multisite_agent_collectors = Gauge(
            "openinfra_multisite_agent_collectors",
            "Discovery agent count grouped by region, site and bounded health state.",
            ("region", "site", "state"),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._runtime_limit = Gauge(
            "openinfra_runtime_concurrency_limit",
            "Configured ASGI concurrency limit per process group.",
            ("service",),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._runtime_workers = Gauge(
            "openinfra_runtime_workers",
            "Configured ASGI worker process count.",
            ("service",),
            registry=self._registry,
            multiprocess_mode="livemostrecent",
        )
        self._process_memory = Gauge(
            "openinfra_process_resident_memory_bytes",
            "Resident memory used by OpenInfra worker processes.",
            ("service",),
            registry=self._registry,
            multiprocess_mode="livesum",
        )
        self._process_cpu = Gauge(
            "openinfra_process_cpu_seconds",
            "CPU seconds consumed by OpenInfra worker processes.",
            ("service",),
            registry=self._registry,
            multiprocess_mode="livesum",
        )
        self._process_uptime = Gauge(
            "openinfra_process_uptime_seconds",
            "OpenInfra process uptime in seconds.",
            ("service",),
            registry=self._registry,
            multiprocess_mode="livemax",
        )
        self._gc_objects = Gauge(
            "openinfra_python_gc_objects",
            "Tracked Python garbage collector objects.",
            ("service",),
            registry=self._registry,
            multiprocess_mode="livesum",
        )
        self._runtime_limit.labels(self._service_name).set(self._resolved_concurrency_limit())
        self._runtime_workers.labels(self._service_name).set(self._resolved_worker_count())

        ratio = self._environment_float("OPENINFRA_OTEL_TRACE_SAMPLE_RATIO", 0.1, 0.0, 1.0)
        resource = Resource.create(
            {
                "service.name": self._service_name,
                "service.version": __version__,
                "deployment.environment.name": self._environment,
                "openinfra.edition": self._edition,
            }
        )
        self._tracer_provider = TracerProvider(
            resource=resource,
            sampler=ParentBased(TraceIdRatioBased(ratio)),
        )
        if self._environment_bool("OPENINFRA_OTEL_ENABLED", False):
            exporter = OTLPSpanExporter()
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    exporter,
                    max_queue_size=self._environment_int("OPENINFRA_OTEL_MAX_QUEUE_SIZE", 2048),
                    schedule_delay_millis=self._environment_int(
                        "OPENINFRA_OTEL_BATCH_DELAY_MILLISECONDS", 5000
                    ),
                    max_export_batch_size=self._environment_int(
                        "OPENINFRA_OTEL_MAX_EXPORT_BATCH_SIZE", 512
                    ),
                    export_timeout_millis=self._environment_int(
                        "OPENINFRA_OTEL_EXPORT_TIMEOUT_MILLISECONDS", 10000
                    ),
                )
            )
        self._tracer = self._tracer_provider.get_tracer("openinfra.runtime", __version__)
        self._propagator = TraceContextTextMapPropagator()
        atexit.register(self.close)
        atexit.register(PrometheusMultiprocessDirectory.mark_process_dead)

    @classmethod
    def from_environment(
        cls,
        *,
        service_name: str,
        edition: str,
        queue_metrics_provider: MetricsProvider | None = None,
        runtime_metrics_provider: MetricsProvider | None = None,
        multisite_metrics_provider: MetricsProvider | None = None,
    ) -> OpenInfraTelemetry:
        configured_service_name = os.environ.get(
            "OPENINFRA_TELEMETRY_SERVICE_NAME", service_name
        ).strip()
        return cls(
            service_name=configured_service_name or service_name,
            edition=edition,
            environment=os.environ.get("OPENINFRA_ENVIRONMENT", "production"),
            queue_metrics_provider=queue_metrics_provider,
            runtime_metrics_provider=runtime_metrics_provider,
            multisite_metrics_provider=multisite_metrics_provider,
        )

    def begin_http_request(
        self,
        *,
        method: str,
        route: str,
        headers: Mapping[str, str],
    ) -> HttpRequestObservation:
        normalized_method = method.strip().upper() or "UNKNOWN"
        normalized_route = self.normalize_route(route)
        parent_context = self._propagator.extract(
            {str(key).lower(): str(value) for key, value in headers.items()}
        )
        span = self._tracer.start_span(
            f"{normalized_method} {normalized_route}",
            context=parent_context,
            kind=SpanKind.SERVER,
            attributes={
                "http.request.method": normalized_method,
                "http.route": normalized_route,
                "server.address": self._service_name,
                "openinfra.edition": self._edition,
            },
        )
        token = context.attach(trace.set_span_in_context(span, parent_context))
        self._http_in_flight.labels(normalized_method, normalized_route).inc()
        return OpenTelemetryHttpObservation(
            span=span,
            context_token=token,
            telemetry=self,
            method=normalized_method,
            route=normalized_route,
            started_at=time.perf_counter(),
        )

    def inject_trace_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        carrier = {str(key): str(value) for key, value in headers.items()}
        self._propagator.inject(carrier)
        return carrier

    def worker_started(self, specialization: str) -> None:
        normalized = self._normalize_specialization(specialization)
        self._worker_in_flight.labels(normalized).inc()
        span = self._tracer.start_span(
            f"worker {normalized}",
            kind=SpanKind.CONSUMER,
            attributes={"openinfra.worker.specialization": normalized},
        )
        token = context.attach(trace.set_span_in_context(span))
        self._thread_state.worker_span = (span, token)

    def worker_finished(self, specialization: str, outcome: str, duration_seconds: float) -> None:
        normalized = self._normalize_specialization(specialization)
        normalized_outcome = self._normalize_outcome(outcome)
        self._worker_in_flight.labels(normalized).dec()
        self._worker_runs.labels(normalized, normalized_outcome).inc()
        self._worker_duration.labels(normalized).observe(max(0.0, float(duration_seconds)))
        value = getattr(self._thread_state, "worker_span", None)
        if value is not None:
            span, token = value
            span.set_attribute("openinfra.worker.outcome", normalized_outcome)
            span.set_attribute("openinfra.worker.duration_seconds", max(0.0, duration_seconds))
            span.set_status(
                Status(
                    StatusCode.ERROR
                    if normalized_outcome in {"failed", "dead-letter"}
                    else StatusCode.OK
                )
            )
            context.detach(token)
            span.end()
            del self._thread_state.worker_span

    def outbox_dispatch_finished(self, outcome: str, duration_seconds: float) -> None:
        normalized_outcome = self._normalize_outcome(outcome)
        self._outbox_runs.labels(normalized_outcome).inc()
        self._outbox_duration.observe(max(0.0, float(duration_seconds)))

    def render_prometheus(self) -> bytes:
        self.refresh_operational_metrics()
        if os.environ.get("PROMETHEUS_MULTIPROC_DIR", "").strip():
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
            return generate_latest(registry)
        return generate_latest(self._registry)

    def refresh_operational_metrics(self) -> None:
        self._process_memory.labels(self._service_name).set(self._resident_memory_bytes())
        self._process_cpu.labels(self._service_name).set(time.process_time())
        self._process_uptime.labels(self._service_name).set(
            max(0.0, time.monotonic() - self._started_at)
        )
        self._gc_objects.labels(self._service_name).set(len(gc.get_objects()))
        if self._queue_metrics_provider is not None:
            self._apply_queue_metrics(self._queue_metrics_provider())
        if self._runtime_metrics_provider is not None:
            self._apply_runtime_metrics(self._runtime_metrics_provider())
        if self._multisite_metrics_provider is not None:
            self._apply_multisite_metrics(self._multisite_metrics_provider())

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            self._tracer_provider.shutdown()

    @classmethod
    def normalize_route(cls, route: str) -> str:
        path = (route.split("?", 1)[0].strip() or "/")[:512]
        segments = []
        for segment in path.split("/"):
            if not segment:
                continue
            segments.append("{id}" if cls._route_identifier.fullmatch(segment) else segment[:80])
        return "/" + "/".join(segments) if segments else "/"

    def _apply_queue_metrics(self, payload: dict[str, object]) -> None:
        statuses = ("queued", "leased", "retry-wait", "completed", "dead-letter")
        for kind in ("jobs", "outbox"):
            raw = payload.get(kind, {})
            values = raw if isinstance(raw, dict) else {}
            for status in statuses:
                self._queue_depth.labels(kind, status).set(self._numeric(values.get(status, 0)))
        by_specialization = payload.get("jobs_by_specialization", {})
        specializations = ("reporting", "imports", "graph", "rag")
        for specialization in specializations:
            raw = (
                by_specialization.get(specialization, {})
                if isinstance(by_specialization, dict)
                else {}
            )
            values = raw if isinstance(raw, dict) else {}
            for status in statuses:
                self._queue_specialization_depth.labels(specialization, status).set(
                    self._numeric(values.get(status, 0))
                )
        self._queue_oldest_ready.labels("jobs").set(
            self._numeric(payload.get("oldest_ready_job_age_seconds", 0.0))
        )
        self._queue_oldest_ready.labels("outbox").set(
            self._numeric(payload.get("oldest_ready_outbox_age_seconds", 0.0))
        )

    def _apply_runtime_metrics(self, payload: dict[str, object]) -> None:
        pools = payload.get("pools", {})
        if isinstance(pools, dict):
            for target in ("primary", "replica"):
                raw = pools.get(target, {})
                if not isinstance(raw, dict):
                    continue
                for name, value in raw.items():
                    if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", str(name)):
                        self._db_pool.labels(target, str(name)).set(self._numeric(value))
        routing = payload.get("routing", {})
        if isinstance(routing, dict):
            replica = routing.get("replica", {})
            if isinstance(replica, dict):
                self._replica_lag.set(self._numeric(replica.get("lag_seconds", 0.0)))
                self._replica_eligible.set(1.0 if bool(replica.get("eligible", False)) else 0.0)
            counters = routing.get("counters", {})
            if isinstance(counters, dict):
                for name, value in counters.items():
                    if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", str(name)):
                        self._db_pool.labels("routing", str(name)).set(self._numeric(value))

    def _apply_multisite_metrics(self, payload: dict[str, object]) -> None:
        raw_sites = payload.get("sites", [])
        if not isinstance(raw_sites, list):
            return
        for raw in raw_sites[:10_000]:
            if not isinstance(raw, dict):
                continue
            region = self._normalize_metric_code(raw.get("region"))
            site = self._normalize_metric_code(raw.get("site"))
            if region is None or site is None:
                continue
            self._multisite_agent_lag.labels(region, site).set(
                self._numeric(raw.get("agent_lag_seconds", 0.0))
            )
            self._multisite_agent_health.labels(region, site).set(
                1.0 if bool(raw.get("healthy", False)) else 0.0
            )
            states = {
                "healthy": raw.get("collectors_healthy", 0),
                "degraded": raw.get("collectors_degraded", 0),
                "maintenance": raw.get("collectors_maintenance", 0),
                "stale": raw.get("collectors_stale", 0),
            }
            for state, value in states.items():
                self._multisite_agent_collectors.labels(region, site, state).set(
                    self._numeric(value)
                )

    @staticmethod
    def _normalize_metric_code(value: object) -> str | None:
        normalized = str(value or "").strip().upper()
        if re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{0,63}", normalized):
            return normalized
        return None

    def _resolved_concurrency_limit(self) -> int:
        service_specific = {
            "openinfra-api": "OPENINFRA_API_LIMIT_CONCURRENCY",
            "openinfra-web": "OPENINFRA_WEB_LIMIT_CONCURRENCY",
            "openinfra-worker": "OPENINFRA_WORKER_LIMIT_CONCURRENCY",
        }[self._service_name]
        for name in (service_specific, "OPENINFRA_RUNTIME_CONCURRENCY_LIMIT"):
            raw = os.environ.get(name, "").strip()
            if not raw:
                continue
            try:
                return max(0, int(raw))
            except ValueError:
                continue
        return 0

    def _resolved_worker_count(self) -> int:
        names = (
            "OPENINFRA_API_WORKERS_RESOLVED",
            "OPENINFRA_WEB_WORKERS_RESOLVED",
            "OPENINFRA_API_WORKERS",
            "OPENINFRA_WEB_WORKERS",
        )
        for name in names:
            raw = os.environ.get(name, "").strip()
            if raw:
                try:
                    return max(1, int(raw))
                except ValueError:
                    continue
        return 1

    @staticmethod
    def _resident_memory_bytes() -> int:
        statm = Path("/proc/self/statm")
        try:
            pages = int(statm.read_text(encoding="ascii").split()[1])
            return pages * int(os.sysconf("SC_PAGE_SIZE"))
        except (OSError, ValueError, IndexError):
            return 0

    @staticmethod
    def _numeric(value: object) -> float:
        if value is None or isinstance(value, bool):
            return 0.0
        try:
            number = float(str(value))
        except (TypeError, ValueError):
            return 0.0
        return number if number >= 0 else 0.0

    @staticmethod
    def _normalize_specialization(value: str) -> str:
        normalized = value.strip().lower()
        return normalized if normalized in {"reporting", "imports", "graph", "rag"} else "unknown"

    @staticmethod
    def _normalize_outcome(value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        allowed = {"completed", "idle", "retry", "failed", "dead-letter", "published"}
        return normalized if normalized in allowed else "failed"

    @staticmethod
    def _environment_bool(name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValidationError(f"{name} must be a boolean")

    @staticmethod
    def _environment_int(name: str, default: int) -> int:
        raw = os.environ.get(name, str(default)).strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValidationError(f"{name} must be an integer") from exc
        if value < 0:
            raise ValidationError(f"{name} cannot be negative")
        return value

    @staticmethod
    def _environment_float(name: str, default: float, minimum: float, maximum: float) -> float:
        raw = os.environ.get(name, str(default)).strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValidationError(f"{name} must be numeric") from exc
        if not minimum <= value <= maximum:
            raise ValidationError(f"{name} must be between {minimum} and {maximum}")
        return value
