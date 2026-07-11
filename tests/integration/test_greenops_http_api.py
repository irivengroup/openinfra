from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _request(
    url: str, *, token: str | None = None, payload: dict[str, object] | None = None
) -> tuple[int, dict[str, object], dict[str, str]]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read()
            return (
                response.status,
                json.loads(body.decode("utf-8")) if body else {},
                dict(response.headers.items()),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, json.loads(body.decode("utf-8")) if body else {}, dict(exc.headers.items())


def _download(url: str, token: str) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/octet-stream"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())


def test_greenops_http_end_to_end_security_and_exports(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "greenops-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, _, _ = _request(base + "/api/v1/greenops/measurement-sources?tenant_id=default")
        assert status == 401

        status, source, _ = _request(
            base + "/api/v1/greenops/measurement-sources/create",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "code": "meter-01",
                "name": "Meter 01",
                "source_type": "dcim",
                "owner": "facilities",
                "active": True,
            },
        )
        assert status == 201 and source["code"] == "meter-01"
        status, sources, _ = _request(
            base
            + "/api/v1/greenops/measurement-sources?"
            + urllib.parse.urlencode({"tenant_id": "default", "active_only": "true"}),
            token=token,
        )
        assert status == 200 and len(sources["items"]) == 1

        status, factor, _ = _request(
            base + "/api/v1/greenops/carbon-factors/create",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "code": "fr-2026",
                "region": "fr",
                "grams_co2e_per_kwh": "50",
                "source_name": "RTE",
                "source_uri": "https://example.invalid/rte",
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
            },
        )
        assert status == 201 and factor["source_name"] == "RTE"
        status, factors, _ = _request(
            base
            + "/api/v1/greenops/carbon-factors?"
            + urllib.parse.urlencode({"tenant_id": "default", "code": "fr-2026"}),
            token=token,
        )
        assert status == 200 and len(factors["items"]) == 1

        status, policy, _ = _request(
            base + "/api/v1/greenops/policies/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "site_code": "par-01",
                "default_pue": "1.4",
                "energy_cost_per_kwh": "0.20",
                "currency": "EUR",
                "carbon_factor_code": "fr-2026",
            },
        )
        assert status == 200 and policy["currency"] == "EUR"
        status, fetched_policy, _ = _request(
            base
            + "/api/v1/greenops/policies/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "site_code": "par-01"}),
            token=token,
        )
        assert status == 200 and fetched_policy["site_code"] == "par-01"

        for index, energy in enumerate(("100", "110", "250"), start=1):
            status, measurement, _ = _request(
                base + "/api/v1/greenops/energy-measurements/ingest",
                token=token,
                payload={
                    "tenant_id": "default",
                    "actor": "pytest",
                    "idempotency_key": f"greenops-http-000{index}",
                    "source_code": "meter-01",
                    "kind": "observed",
                    "scope": "site",
                    "scope_key": "par-01",
                    "site_code": "par-01",
                    "period_start": f"2026-07-0{index}T00:00:00Z",
                    "period_end": f"2026-07-0{index + 1}T00:00:00Z",
                    "energy_kwh": energy,
                    "energy_capacity_percent": str(35 + index * 20),
                    "metadata": {"collector": "pytest"},
                },
            )
            assert status == 201 and measurement["source_code"] == "meter-01"

        status, measurements, _ = _request(
            base
            + "/api/v1/greenops/energy-measurements?"
            + urllib.parse.urlencode({"tenant_id": "default", "site_code": "par-01"}),
            token=token,
        )
        assert status == 200 and len(measurements["items"]) == 3
        status, invalid, _ = _request(
            base + "/api/v1/greenops/energy-measurements/ingest",
            token=token,
            payload={"tenant_id": "default", "metadata": []},
        )
        assert status == 400 and "error" in invalid

        status, report, _ = _request(
            base + "/api/v1/greenops/reports/generate",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "site_code": "par-01",
                "period_start": "2026-07-01",
                "period_end": "2026-07-03",
                "scope": "site",
            },
        )
        assert status == 201 and report["production_mutation"] is False
        report_id = str(report["id"])
        status, fetched, _ = _request(
            base
            + "/api/v1/greenops/reports/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "report_id": report_id}),
            token=token,
        )
        assert status == 200 and fetched["id"] == report_id
        status, reports, _ = _request(
            base
            + "/api/v1/greenops/reports?"
            + urllib.parse.urlencode({"tenant_id": "default", "site_code": "par-01"}),
            token=token,
        )
        assert status == 200 and reports["items"][0]["id"] == report_id

        export_url = (
            base
            + "/api/v1/greenops/reports/export?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "report_id": report_id, "format": "csv"}
            )
        )
        export_status, content, headers = _download(export_url, token)
        assert export_status == 200
        assert headers["Content-Type"].startswith("text/csv")
        assert b"kilograms_co2e" in content

        for path in ("anomalies", "capacity-forecasts", "consolidation-candidates", "green-scores"):
            status, page, _ = _request(
                base
                + f"/api/v1/greenops/{path}?"
                + urllib.parse.urlencode({"tenant_id": "default", "site_code": "par-01"}),
                token=token,
            )
            assert status == 200 and isinstance(page["items"], list)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
