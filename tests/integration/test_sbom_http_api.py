from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import ValidationError
from openinfra.interfaces.http_api import OpenInfraRequestHandler, OpenInfraThreadingServer


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
                json.loads(body.decode()) if body else {},
                dict(response.headers),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, json.loads(body.decode()) if body else {}, dict(exc.headers)


def _download(url: str, token: str) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def _sbom(version: str) -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:openinfra-{version}",
        "components": [
            {
                "bom-ref": f"pkg:pypi/requests@{version}",
                "name": "requests",
                "version": version,
                "purl": f"pkg:pypi/requests@{version}",
            }
        ],
    }


def test_sbom_http_complete_cycle_security_validation_and_exports(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "v" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "sbom-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, _, _ = _request(base + "/api/v1/sbom/documents?tenant_id=default")
        assert status == 401

        document_ids: list[str] = []
        for release, component_version in (("0.29.98", "2.31.0"), ("0.29.99", "2.32.0")):
            status, document, _ = _request(
                base + "/api/v1/sbom/documents/import",
                token=token,
                payload={
                    "tenant_id": "default",
                    "application": "openinfra",
                    "release": release,
                    "environment": "production",
                    "source_name": "github-actions",
                    "source_uri": f"https://example.invalid/sbom/{release}.json",
                    "sbom": _sbom(component_version),
                },
            )
            assert status == 201
            document_ids.append(str(document["id"]))

        query = urllib.parse.urlencode({"tenant_id": "default", "application": "openinfra"})
        status, documents, _ = _request(base + f"/api/v1/sbom/documents?{query}", token=token)
        assert status == 200 and len(documents["items"]) == 2
        status, document, _ = _request(
            base
            + "/api/v1/sbom/documents/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "document_id": document_ids[1]}),
            token=token,
        )
        assert status == 200 and document["release"] == "0.29.99"

        status, vulnerability, _ = _request(
            base + "/api/v1/sbom/vulnerabilities/import",
            token=token,
            payload={
                "tenant_id": "default",
                "cve_id": "CVE-2026-12345",
                "component_name": "requests",
                "component_version": "2.32.0",
                "component_purl": "pkg:pypi/requests@2.32.0",
                "cvss_score": "8.2",
                "known_exploited": True,
                "exploit_maturity": "weaponized",
                "source_name": "scanner-x",
                "published_at": "2026-06-01T00:00:00Z",
                "modified_at": "2026-07-01T00:00:00Z",
                "references": ["https://example.invalid/cve/CVE-2026-12345"],
                "metadata": {"scanner": "x"},
            },
        )
        assert status == 201 and vulnerability["known_exploited"] is True
        status, vulnerabilities, _ = _request(
            base
            + "/api/v1/sbom/vulnerabilities?"
            + urllib.parse.urlencode({"tenant_id": "default", "known_exploited": "true"}),
            token=token,
        )
        assert status == 200 and len(vulnerabilities["items"]) == 1

        status, exposure, _ = _request(
            base + "/api/v1/sbom/exposures/upsert",
            token=token,
            payload={
                "tenant_id": "default",
                "application": "openinfra",
                "environment": "production",
                "internet_exposed": True,
                "flow_exposed": True,
                "business_criticality": 5,
                "compensating_controls": ["waf", "network-segmentation"],
                "asset_ids": ["server-001"],
                "service_ids": ["portal"],
            },
        )
        assert status == 201 and exposure["business_criticality"] == 5
        status, exposures, _ = _request(
            base + "/api/v1/sbom/exposures?tenant_id=default", token=token
        )
        assert status == 200 and len(exposures["items"]) == 1
        status, fetched_exposure, _ = _request(
            base
            + "/api/v1/sbom/exposures/get?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "application": "openinfra", "environment": "production"}
            ),
            token=token,
        )
        assert status == 200 and fetched_exposure["internet_exposed"] is True

        status, findings, _ = _request(
            base + "/api/v1/sbom/risk/assess",
            token=token,
            payload={"tenant_id": "default", "document_id": document_ids[1]},
        )
        assert status == 201 and findings["items"][0]["priority"] == "critical"
        status, listed, _ = _request(
            base
            + "/api/v1/sbom/findings?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "document_id": document_ids[1], "priority": "critical"}
            ),
            token=token,
        )
        assert status == 200 and listed["items"]

        status, comparison, _ = _request(
            base + "/api/v1/sbom/comparisons/create",
            token=token,
            payload={
                "tenant_id": "default",
                "base_document_id": document_ids[0],
                "target_document_id": document_ids[1],
            },
        )
        assert status == 201 and comparison["summary"]["changed"] == 1
        comparison_id = str(comparison["id"])
        status, comparisons, _ = _request(
            base + "/api/v1/sbom/comparisons?tenant_id=default", token=token
        )
        assert status == 200 and comparisons["items"][0]["id"] == comparison_id
        status, fetched_comparison, _ = _request(
            base
            + "/api/v1/sbom/comparisons/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "comparison_id": comparison_id}),
            token=token,
        )
        assert status == 200 and fetched_comparison["id"] == comparison_id

        export_url = (
            base
            + "/api/v1/sbom/risk/export?"
            + urllib.parse.urlencode(
                {"tenant_id": "default", "document_id": document_ids[1], "format": "csv"}
            )
        )
        export_status, content, headers = _download(export_url, token)
        assert export_status == 200
        assert headers["Content-Type"].startswith("text/csv")
        assert b"contextual_score" in content and b"CVE-2026-12345" in content

        status, invalid, _ = _request(
            base + "/api/v1/sbom/vulnerabilities/import",
            token=token,
            payload={"tenant_id": "default", "references": {}},
        )
        assert status == 400 and "error" in invalid
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_payload_string_tuple_rejects_non_array_values() -> None:
    with pytest.raises(ValidationError, match="references must be an array"):
        OpenInfraRequestHandler._payload_string_tuple({"references": {}}, "references")
