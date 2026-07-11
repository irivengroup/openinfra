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
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, object] | None = None,
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
            parsed = json.loads(body.decode("utf-8")) if body else {}
            return response.status, parsed, dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        parsed = json.loads(body.decode("utf-8")) if body else {}
        return exc.code, parsed, dict(exc.headers.items())


def _download(url: str, token: str) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/octet-stream", "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())


def _cost_record(external_id: str, amount: str = "125.50") -> dict[str, object]:
    return {
        "external_id": external_id,
        "category": "cloud",
        "source": "aws-cur",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "currency": "EUR",
        "amount": amount,
        "owner": "platform.team",
        "application_key": "openinfra",
        "service_key": "asset-management",
        "cost_center": "cc-100",
        "environment": "production",
        "metadata": {"provider": "aws", "region": "eu-west-3"},
    }


def test_finops_http_end_to_end_and_security(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "f" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "finops-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, rule, _ = _request(
            base + "/api/v1/finops/allocation-rules/create",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "name": "Applications cloud",
                "priority": 10,
                "dimension": "application",
                "selector_key": "application_key",
                "percentage": "100",
                "category": "cloud",
                "source": "aws-cur",
                "active": True,
            },
        )
        assert status == 201
        assert rule["dimension"] == "application"

        status, rules, _ = _request(
            base
            + "/api/v1/finops/allocation-rules?"
            + urllib.parse.urlencode({"tenant_id": "default", "active_only": "true", "limit": 10}),
            token=token,
        )
        assert status == 200
        assert len(rules["items"]) == 1

        status, queued, _ = _request(
            base + "/api/v1/finops/import-jobs/submit",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "idempotency_key": "finops-http-import-0001",
                "source": "aws-cur",
                "records": [_cost_record("aws-2026-06-001")],
            },
        )
        assert status == 202
        job_id = str(queued["id"])
        assert queued["status"] == "queued"

        get_job_url = (
            base
            + "/api/v1/finops/import-jobs/get?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "job_id": job_id, "include_records": "true"}
            )
        )
        status, fetched, _ = _request(get_job_url, token=token)
        assert status == 200
        assert len(fetched["records"]) == 1

        status, completed, _ = _request(
            base + "/api/v1/finops/import-jobs/run",
            token=token,
            payload={"tenant_id": "default", "actor": "pytest", "job_id": job_id},
        )
        assert status == 200
        assert completed["status"] == "completed"
        assert completed["imported_count"] == 1

        status, jobs, _ = _request(
            base
            + "/api/v1/finops/import-jobs?"
            + urllib.parse.urlencode({"tenant_id": "default", "status": "completed"}),
            token=token,
        )
        assert status == 200
        assert jobs["items"][0]["id"] == job_id

        status, records, _ = _request(
            base
            + "/api/v1/finops/cost-records?"
            + urllib.parse.urlencode(
                {
                    "tenant_id": "default",
                    "period_start": "2026-06-01",
                    "period_end": "2026-06-30",
                    "currency": "EUR",
                    "quality_status": "allocated",
                }
            ),
            token=token,
        )
        assert status == 200
        assert records["items"][0]["amount"] == "125.500000"

        status, budget, _ = _request(
            base + "/api/v1/finops/budgets/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "dimension": "application",
                "target": "openinfra",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "currency": "EUR",
                "amount": "100.00",
                "warning_threshold_percent": "80",
                "owner": "finops.team",
            },
        )
        assert status == 200
        assert budget["version"] == 1

        status, budgets, _ = _request(
            base
            + "/api/v1/finops/budgets?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "dimension": "application", "currency": "EUR"}
            ),
            token=token,
        )
        assert status == 200
        assert budgets["items"][0]["target"] == "openinfra"

        status, report, _ = _request(
            base + "/api/v1/finops/reports/generate",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "kind": "showback",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "group_by": "application",
                "currency": "EUR",
            },
        )
        assert status == 201
        report_id = str(report["id"])
        assert report["production_billing_mutation"] is False
        assert report["lines"][0]["target"] == "openinfra"

        status, fetched_report, _ = _request(
            base
            + "/api/v1/finops/reports/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "report_id": report_id}),
            token=token,
        )
        assert status == 200
        assert fetched_report["id"] == report_id

        status, reports, _ = _request(
            base
            + "/api/v1/finops/reports?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "kind": "showback", "currency": "EUR"}
            ),
            token=token,
        )
        assert status == 200
        assert reports["items"][0]["id"] == report_id

        export_url = (
            base
            + "/api/v1/finops/reports/export?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "report_id": report_id, "format": "csv"}
            )
        )
        export_status, content, headers = _download(export_url, token)
        assert export_status == 200
        assert headers["Content-Type"].startswith("text/csv")
        assert b"target,amount" in content

        for path in ("anomalies", "forecasts"):
            status, page, _ = _request(
                base
                + f"/api/v1/finops/{path}?"
                + urllib.parse.urlencode({"tenant_id": "default", "limit": 10}),
                token=token,
            )
            assert status == 200
            assert isinstance(page["items"], list)

        status, closed, _ = _request(
            base + "/api/v1/finops/periods/close",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
                "currency": "EUR",
            },
        )
        assert status == 200
        assert closed["status"] == "closed"

        status, periods, _ = _request(
            base
            + "/api/v1/finops/periods?"
            + urllib.parse.urlencode({"tenant_id": "default", "status": "closed"}),
            token=token,
        )
        assert status == 200
        assert periods["items"][0]["status"] == "closed"

        status, queued_cancel, _ = _request(
            base + "/api/v1/finops/import-jobs/submit",
            token=token,
            payload={
                "tenant_id": "default",
                "idempotency_key": "finops-http-import-0002",
                "source": "aws-cur",
                "records": [
                    _cost_record("aws-2026-07-001")
                    | {
                        "period_start": "2026-07-01",
                        "period_end": "2026-07-31",
                    }
                ],
            },
        )
        assert status == 202
        status, cancelled, _ = _request(
            base + "/api/v1/finops/import-jobs/cancel",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "job_id": str(queued_cancel["id"]),
            },
        )
        assert status == 200
        assert cancelled["status"] == "cancelled"

        unauthorized, payload, _ = _request(base + "/api/v1/finops/reports?tenant_id=default")
        assert unauthorized == 401
        assert "token" in str(payload["error"]).lower()

        invalid, payload, _ = _request(
            base + "/api/v1/finops/import-jobs/submit",
            token=token,
            payload={
                "tenant_id": "default",
                "idempotency_key": "finops-http-invalid-0001",
                "source": "aws-cur",
                "records": ["not-an-object"],
            },
        )
        assert invalid == 400
        assert "array of objects" in str(payload["error"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
