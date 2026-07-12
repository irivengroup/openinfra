from __future__ import annotations

from collections.abc import Mapping

from openinfra.application.ports import HttpRequestObservation, RuntimeTelemetry


class NullHttpRequestObservation(HttpRequestObservation):
    @property
    def traceparent(self) -> str:
        return ""

    def record_exception(self, exception: BaseException) -> None:
        del exception

    def finish(
        self,
        *,
        status_code: int,
        request_size_bytes: int,
        response_size_bytes: int,
    ) -> None:
        del status_code, request_size_bytes, response_size_bytes


class NullRuntimeTelemetry(RuntimeTelemetry):
    def begin_http_request(
        self,
        *,
        method: str,
        route: str,
        headers: Mapping[str, str],
    ) -> HttpRequestObservation:
        del method, route, headers
        return NullHttpRequestObservation()

    def worker_started(self, specialization: str) -> None:
        del specialization

    def worker_finished(self, specialization: str, outcome: str, duration_seconds: float) -> None:
        del specialization, outcome, duration_seconds

    def outbox_dispatch_finished(self, outcome: str, duration_seconds: float) -> None:
        del outcome, duration_seconds

    def render_prometheus(self) -> bytes:
        return b""

    def inject_trace_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        return dict(headers)

    def refresh_operational_metrics(self) -> None:
        return None

    def close(self) -> None:
        return None
