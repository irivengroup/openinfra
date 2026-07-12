from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.observability import (
    OpenInfraTelemetry,
    PrometheusMultiprocessDirectory,
)


def _queue_metrics() -> dict[str, object]:
    return {
        "jobs": {"queued": 3, "leased": 1, "retry-wait": 0, "completed": 7, "dead-letter": 0},
        "outbox": {"queued": 2, "leased": 0, "retry-wait": 1, "completed": 9, "dead-letter": 0},
        "jobs_by_specialization": {
            "reporting": {"queued": 1},
            "imports": {"queued": 1},
            "graph": {"queued": 1},
            "rag": {"queued": 0},
        },
        "oldest_ready_job_age_seconds": 12.5,
        "oldest_ready_outbox_age_seconds": 3.25,
    }


def _runtime_metrics() -> dict[str, object]:
    return {
        "pools": {
            "primary": {"pool_size": 8, "pool_available": 5, "requests_waiting": 1},
            "replica": {"pool_size": 4, "pool_available": 4},
        },
        "routing": {
            "replica": {"lag_seconds": 0.75, "eligible": True},
            "counters": {"primary_acquisitions": 4, "replica_acquisitions": 6},
        },
    }


def test_prometheus_metrics_and_trace_context_are_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    monkeypatch.setenv("OPENINFRA_OTEL_ENABLED", "false")
    monkeypatch.setenv("OPENINFRA_OTEL_TRACE_SAMPLE_RATIO", "1")
    monkeypatch.setenv("OPENINFRA_API_LIMIT_CONCURRENCY", "250")
    monkeypatch.setenv("OPENINFRA_API_WORKERS_RESOLVED", "4")
    telemetry = OpenInfraTelemetry(
        service_name="openinfra-api",
        edition="enterprise",
        environment="test",
        queue_metrics_provider=_queue_metrics,
        runtime_metrics_provider=_runtime_metrics,
    )

    observation = telemetry.begin_http_request(
        method="get",
        route="/api/v1/async/jobs/123456789",
        headers={},
    )
    assert observation.traceparent.startswith("00-")
    observation.finish(status_code=200, request_size_bytes=4, response_size_bytes=32)
    telemetry.worker_started("imports")
    telemetry.worker_finished("imports", "completed", 0.125)
    telemetry.outbox_dispatch_finished("published", 0.05)

    metrics = telemetry.render_prometheus().decode("utf-8")
    assert 'openinfra_build_info{edition="enterprise",service="openinfra-api"' in metrics
    assert 'route="/api/v1/async/jobs/{id}"' in metrics
    assert 'openinfra_async_queue_depth{kind="jobs",status="queued"} 3.0' in metrics
    assert 'openinfra_async_job_depth{specialization="graph",status="queued"} 1.0' in metrics
    assert "openinfra_db_replica_lag_seconds 0.75" in metrics
    assert "openinfra_db_replica_eligible 1.0" in metrics
    assert 'openinfra_runtime_concurrency_limit{service="openinfra-api"} 250.0' in metrics
    assert 'openinfra_runtime_workers{service="openinfra-api"} 4.0' in metrics
    assert (
        'openinfra_worker_runs_total{outcome="completed",specialization="imports"} 1.0' in metrics
    )
    assert 'openinfra_outbox_dispatch_total{outcome="published"} 1.0' in metrics
    telemetry.close()
    telemetry.close()


def test_route_normalization_and_invalid_telemetry_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (
        OpenInfraTelemetry.normalize_route("/items/08a12c3f-1234-4abc-8def-0123456789ab?q=x")
        == "/items/{id}"
    )
    assert OpenInfraTelemetry.normalize_route("") == "/"
    assert OpenInfraTelemetry.normalize_route("/items/stable-code") == "/items/stable-code"

    with pytest.raises(ValidationError, match="service name"):
        OpenInfraTelemetry(service_name="unknown", edition="pro", environment="test")
    with pytest.raises(ValidationError, match="edition"):
        OpenInfraTelemetry(service_name="openinfra-api", edition="unknown", environment="test")

    monkeypatch.setenv("OPENINFRA_OTEL_TRACE_SAMPLE_RATIO", "2")
    with pytest.raises(ValidationError, match="between"):
        OpenInfraTelemetry(service_name="openinfra-api", edition="pro", environment="test")


def test_prometheus_multiprocess_directory_is_created_and_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "prometheus"
    root.mkdir()
    stale = root / "gauge_all_123.db"
    stale.write_bytes(b"stale")
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(root))
    monkeypatch.setenv("OPENINFRA_PROMETHEUS_CLEAN_START", "true")

    assert PrometheusMultiprocessDirectory.prepare_from_environment() == root
    assert not stale.exists()
    assert not list(root.glob(".openinfra-prometheus-write-*"))


def test_prometheus_multiprocess_directory_rejects_unwritable_mount(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from openinfra.infrastructure import observability

    root = tmp_path / "prometheus"
    root.mkdir()
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(root))
    original_open = observability.os.open

    def deny_runtime_probe(path: object, flags: int, mode: int = 0o777) -> int:
        if str(path).startswith(str(root)):
            raise PermissionError(13, "permission denied", str(path))
        return original_open(path, flags, mode)  # type: ignore[arg-type]

    monkeypatch.setattr(observability.os, "open", deny_runtime_probe)

    with pytest.raises(ValidationError, match=r"not writable.*Align the runtime user"):
        PrometheusMultiprocessDirectory.prepare_from_environment()


def test_observability_defensive_branches_and_environment_factory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from opentelemetry import context, trace
    from opentelemetry.sdk.trace.export import SpanExportResult

    from openinfra.infrastructure import observability
    from openinfra.infrastructure.observability import OpenTelemetryHttpObservation

    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    assert PrometheusMultiprocessDirectory.prepare_from_environment() is None

    marked: list[int] = []
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path / "prometheus"))
    from prometheus_client import multiprocess as prometheus_multiprocess

    monkeypatch.setattr(prometheus_multiprocess, "mark_process_dead", marked.append)
    PrometheusMultiprocessDirectory.mark_process_dead()
    assert marked

    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    monkeypatch.setenv("OPENINFRA_OTEL_ENABLED", "false")
    monkeypatch.setenv("OPENINFRA_TELEMETRY_SERVICE_NAME", "openinfra-worker")
    monkeypatch.setenv("OPENINFRA_WORKER_LIMIT_CONCURRENCY", "invalid")
    monkeypatch.setenv("OPENINFRA_RUNTIME_CONCURRENCY_LIMIT", "64")
    monkeypatch.setenv("OPENINFRA_API_WORKERS_RESOLVED", "invalid")
    monkeypatch.setenv("OPENINFRA_WEB_WORKERS", "3")
    telemetry = OpenInfraTelemetry.from_environment(
        service_name="openinfra-api", edition="enterprise"
    )
    rendered = telemetry.render_prometheus().decode("utf-8")
    assert 'service="openinfra-worker"' in rendered
    assert 'openinfra_runtime_concurrency_limit{service="openinfra-worker"} 64.0' in rendered
    assert 'openinfra_runtime_workers{service="openinfra-worker"} 3.0' in rendered

    observation = telemetry.begin_http_request(method="POST", route="/failure/42", headers={})
    observation.record_exception(RuntimeError("boom"))
    observation.finish(status_code=503, request_size_bytes=-1, response_size_bytes=-2)
    observation.finish(status_code=200, request_size_bytes=1, response_size_bytes=1)
    assert 'status_class="5xx"' in telemetry.render_prometheus().decode("utf-8")

    token = context.attach(context.get_current())
    invalid = OpenTelemetryHttpObservation(
        span=trace.INVALID_SPAN,
        context_token=token,
        telemetry=telemetry,
        method="GET",
        route="/invalid",
        started_at=0.0,
    )
    assert invalid.traceparent == ""
    context.detach(token)

    telemetry._apply_queue_metrics(
        {"jobs": "invalid", "outbox": None, "jobs_by_specialization": "invalid"}
    )
    telemetry._apply_runtime_metrics(
        {
            "pools": {"primary": "invalid", "replica": {"!invalid": 1, "size": "bad"}},
            "routing": {"replica": "invalid", "counters": {"!invalid": 1, "reads": "bad"}},
        }
    )
    assert telemetry._numeric(None) == 0.0
    assert telemetry._numeric(True) == 0.0
    assert telemetry._numeric("invalid") == 0.0
    assert telemetry._numeric(-1) == 0.0
    assert telemetry._normalize_specialization("unexpected") == "unknown"
    assert telemetry._normalize_outcome("unexpected") == "failed"
    telemetry.worker_finished("unexpected", "unexpected", -1)
    telemetry.close()

    assert OpenInfraTelemetry._environment_bool("MISSING_BOOL", True) is True
    monkeypatch.setenv("TEST_BOOL", "yes")
    assert OpenInfraTelemetry._environment_bool("TEST_BOOL", False) is True
    monkeypatch.setenv("TEST_BOOL", "off")
    assert OpenInfraTelemetry._environment_bool("TEST_BOOL", True) is False
    monkeypatch.setenv("TEST_BOOL", "invalid")
    with pytest.raises(ValidationError, match="boolean"):
        OpenInfraTelemetry._environment_bool("TEST_BOOL", False)

    monkeypatch.setenv("TEST_INT", "invalid")
    with pytest.raises(ValidationError, match="integer"):
        OpenInfraTelemetry._environment_int("TEST_INT", 1)
    monkeypatch.setenv("TEST_INT", "-1")
    with pytest.raises(ValidationError, match="negative"):
        OpenInfraTelemetry._environment_int("TEST_INT", 1)
    monkeypatch.setenv("TEST_INT", "2")
    assert OpenInfraTelemetry._environment_int("TEST_INT", 1) == 2

    monkeypatch.setenv("TEST_FLOAT", "invalid")
    with pytest.raises(ValidationError, match="numeric"):
        OpenInfraTelemetry._environment_float("TEST_FLOAT", 0.5, 0, 1)

    original_read_text = Path.read_text

    def fail_statm(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if self == Path("/proc/self/statm"):
            raise OSError("unavailable")
        return original_read_text(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_statm)
    assert OpenInfraTelemetry._resident_memory_bytes() == 0

    class Exporter:
        def export(self, spans: object) -> SpanExportResult:
            del spans
            return SpanExportResult.SUCCESS

        def shutdown(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def force_flush(self, *args: object, **kwargs: object) -> bool:
            del args, kwargs
            return True

    monkeypatch.setenv("OPENINFRA_OTEL_ENABLED", "true")
    monkeypatch.setenv("OPENINFRA_OTEL_MAX_QUEUE_SIZE", "16")
    monkeypatch.setenv("OPENINFRA_OTEL_BATCH_DELAY_MILLISECONDS", "1")
    monkeypatch.setenv("OPENINFRA_OTEL_MAX_EXPORT_BATCH_SIZE", "8")
    monkeypatch.setenv("OPENINFRA_OTEL_EXPORT_TIMEOUT_MILLISECONDS", "10")
    monkeypatch.setattr(observability, "OTLPSpanExporter", Exporter)
    otel = OpenInfraTelemetry(service_name="openinfra-api", edition="pro", environment="test")
    otel.close()


def test_multiprocess_render_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from openinfra.infrastructure import observability

    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    monkeypatch.setenv("OPENINFRA_OTEL_ENABLED", "false")
    from prometheus_client import multiprocess as prometheus_multiprocess

    collectors: list[object] = []

    def collect(registry: object) -> None:
        collectors.append(registry)

    def generate(registry: object) -> bytes:
        del registry
        return b"multiprocess"

    monkeypatch.setattr(prometheus_multiprocess, "MultiProcessCollector", collect)
    monkeypatch.setattr(observability, "generate_latest", generate)
    telemetry = OpenInfraTelemetry(service_name="openinfra-web", edition="lite", environment="test")
    assert telemetry.render_prometheus() == b"multiprocess"
    assert collectors
    telemetry.close()


def test_null_telemetry_and_idempotent_asgi_finish() -> None:
    from openinfra.application.telemetry import NullRuntimeTelemetry
    from openinfra.interfaces.asgi_observability import ObservedAsgiSend
    from openinfra.interfaces.openapi_taxonomy import OpenApiDocumentationTaxonomy

    telemetry = NullRuntimeTelemetry()
    observation = telemetry.begin_http_request(method="GET", route="/metrics", headers={})
    observation.record_exception(RuntimeError("ignored by null telemetry"))
    assert telemetry.render_prometheus() == b""
    telemetry.refresh_operational_metrics()

    downstream_messages: list[dict[str, object]] = []

    async def downstream(message: dict[str, object]) -> None:
        downstream_messages.append(message)

    sender = ObservedAsgiSend(downstream, observation)
    asyncio.run(sender({"type": "http.response.body", "body": b"metrics"}))
    sender.finish(0)
    sender.finish(1)

    assert downstream_messages == [{"type": "http.response.body", "body": b"metrics"}]
    assert OpenApiDocumentationTaxonomy.contexts()[1].context == "Observabilité et capacité"
