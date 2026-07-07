from __future__ import annotations

import json
from argparse import Namespace
from io import BytesIO
from pathlib import Path
from urllib import error, request

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.proxy_enrollment import (
    ProxyEnrollmentBatchResult,
    ProxyEnrollmentConfigValidator,
    ProxyEnrollmentConfigWriter,
    ProxyEnrollmentHttpClient,
    ProxyEnrollmentPayloadFactory,
    ProxyEnrollmentResult,
    ProxyEnrollmentTarget,
)


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _admin_token() -> str:
    return "token-value"


def _blank_admin_token() -> str:
    return " "


def _vault_ref() -> str:
    return "vault://openinfra/discovery/proxy/par1"


def _payload() -> dict[str, object]:
    return {
        "tenant_id": "default",
        "actor": "pytest",
        "name": "PAR1 site proxy",
        "kind": "site-proxy",
        "certificate_fingerprint": "a" * 64,
        "scopes": ["site/par1"],
        "version": "0.29.35",
        "vault_secret_ref": None,
        "endpoint_url": "https://proxy-par1.example.test/agent",
    }


def test_proxy_enrollment_target_normalizes_valid_urls() -> None:
    target = ProxyEnrollmentTarget.from_backend_url(" https://backend.example.test/openinfra ")
    loopback = ProxyEnrollmentTarget.from_backend_url("http://127.0.0.1:8080")

    assert target.backend_url == "https://backend.example.test/openinfra"
    assert target.endpoint_url == (
        "https://backend.example.test/openinfra/api/v1/discovery/proxy-enrollments"
    )
    assert loopback.endpoint_url == "http://127.0.0.1:8080/api/v1/discovery/proxy-enrollments"


@pytest.mark.parametrize(
    ("backend_url", "message"),
    [
        (" ", "backend URL is mandatory"),
        ("ftp://backend.example.test", "backend URL must use https"),
        ("http://backend.example.test", "backend URL must use https outside loopback"),
        ("https:///missing-host", "backend URL host is mandatory"),
    ],
)
def test_proxy_enrollment_target_rejects_invalid_urls(backend_url: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        ProxyEnrollmentTarget.from_backend_url(backend_url)


def test_proxy_enrollment_http_client_enrolls_many_and_writes_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def fake_urlopen(
        outbound: request.Request,
        timeout: float,
    ) -> _FakeResponse:
        assert timeout == 7.5
        payload = json.loads(outbound.data.decode("utf-8"))  # type: ignore[union-attr]
        captured.append((outbound.full_url, dict(outbound.header_items()), payload))
        return _FakeResponse(201, {"id": "collector-1", "kind": payload["kind"]})

    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    result = ProxyEnrollmentHttpClient().enroll_many(
        backend_urls=("https://backend-a.example.test", "https://backend-b.example.test"),
        admin_token=_admin_token(),
        payload=_payload(),
        timeout_seconds=7.5,
    )
    output = tmp_path / "conf" / "proxy-enrollment.json"
    ProxyEnrollmentConfigWriter().write(output, result)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result.enrolled is True
    assert result.as_dict()["results"][0]["status_code"] == 201  # type: ignore[index]
    assert len(captured) == 2
    assert captured[0][0].endswith("/api/v1/discovery/proxy-enrollments")
    assert captured[0][1]["Authorization"] == "Bearer token-value"
    assert captured[0][2]["kind"] == "site-proxy"
    assert written["enrolled"] is True
    assert output.stat().st_mode & 0o777 == 0o600


def test_proxy_enrollment_http_client_preserves_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(_outbound: request.Request, timeout: float) -> object:
        assert timeout == 10
        raise error.HTTPError(
            url="https://backend.example.test/api/v1/discovery/proxy-enrollments",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=BytesIO(b'{"error":"edition gate"}'),
        )

    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    result = ProxyEnrollmentHttpClient().enroll_many(
        backend_urls=("https://backend.example.test",),
        admin_token=_admin_token(),
        payload=_payload(),
        timeout_seconds=10,
    )

    assert result.enrolled is False
    assert result.results[0].status_code == 403
    assert result.results[0].response == {"error": "edition gate"}


def test_proxy_enrollment_http_client_rejects_invalid_runtime_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ProxyEnrollmentHttpClient()
    payload = _payload()

    with pytest.raises(ValidationError, match="at least one backend URL"):
        client.enroll_many(
            backend_urls=(),
            admin_token=_admin_token(),
            payload=payload,
            timeout_seconds=10,
        )
    with pytest.raises(ValidationError, match="timeout seconds"):
        client.enroll_many(
            backend_urls=("https://backend.example.test",),
            admin_token=_admin_token(),
            payload=payload,
            timeout_seconds=0,
        )
    with pytest.raises(ValidationError, match="timeout seconds"):
        client.enroll_many(
            backend_urls=("https://backend.example.test",),
            admin_token=_admin_token(),
            payload=payload,
            timeout_seconds=121,
        )
    with pytest.raises(ValidationError, match="admin token"):
        client.enroll_many(
            backend_urls=("https://backend.example.test",),
            admin_token=_blank_admin_token(),
            payload=payload,
            timeout_seconds=10,
        )

    def failing_urlopen(_outbound: request.Request, timeout: float) -> object:
        assert timeout == 10
        raise error.URLError("connection refused")

    monkeypatch.setattr(request, "urlopen", failing_urlopen)
    with pytest.raises(ValidationError, match="backend unavailable"):
        client.enroll_many(
            backend_urls=("https://backend.example.test",),
            admin_token=_admin_token(),
            payload=payload,
            timeout_seconds=10,
        )


def test_proxy_enrollment_http_client_rejects_invalid_json_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ProxyEnrollmentHttpClient()

    class InvalidJsonResponse:
        status = 200

        def __enter__(self) -> InvalidJsonResponse:
            return self

        def __exit__(self, *_exc_info: object) -> None:
            return None

        def read(self) -> bytes:
            return b"not-json"

    def invalid_json_urlopen(_outbound: request.Request, timeout: float) -> InvalidJsonResponse:
        assert timeout == 10
        return InvalidJsonResponse()

    monkeypatch.setattr(request, "urlopen", invalid_json_urlopen)
    with pytest.raises(ValidationError, match="not valid JSON"):
        client.enroll_many(
            backend_urls=("https://backend.example.test",),
            admin_token=_admin_token(),
            payload=_payload(),
            timeout_seconds=10,
        )

    monkeypatch.setattr(
        request,
        "urlopen",
        lambda _outbound, timeout: _FakeResponse(200 if timeout == 10 else 500, []),
    )
    with pytest.raises(ValidationError, match="must be a JSON object"):
        client.enroll_many(
            backend_urls=("https://backend.example.test",),
            admin_token=_admin_token(),
            payload=_payload(),
            timeout_seconds=10,
        )


def test_proxy_enrollment_payload_factory_keeps_values_internal() -> None:
    args = Namespace(
        tenant="default",
        actor="proxy-cli",
        name="PAR1 site proxy",
        kind="network-proxy",
        certificate_fingerprint="b" * 64,
        scope=("site/par1", "vrf/prod"),
        version="0.29.35",
        vault_secret_ref=_vault_ref(),
        endpoint_url="https://proxy-par1.example.test/agent",
    )
    payload = ProxyEnrollmentPayloadFactory().from_args(args)

    assert payload == {
        "tenant_id": "default",
        "actor": "proxy-cli",
        "name": "PAR1 site proxy",
        "kind": "network-proxy",
        "certificate_fingerprint": "b" * 64,
        "scopes": ["site/par1", "vrf/prod"],
        "version": "0.29.35",
        "vault_secret_ref": "vault://openinfra/discovery/proxy/par1",
        "endpoint_url": "https://proxy-par1.example.test/agent",
    }


def test_proxy_enrollment_payload_factory_rejects_empty_scopes() -> None:
    args = Namespace(
        tenant="default",
        actor="proxy-cli",
        name="PAR1 site proxy",
        kind="site-proxy",
        certificate_fingerprint="c" * 64,
        scope=(),
        version="0.29.35",
        vault_secret_ref=None,
        endpoint_url="https://proxy-par1.example.test/agent",
    )

    with pytest.raises(ValidationError, match="at least one proxy scope"):
        ProxyEnrollmentPayloadFactory().from_args(args)


def test_proxy_enrollment_result_serialization() -> None:
    result = ProxyEnrollmentBatchResult(
        tenant_id="default",
        name="PAR1 proxy",
        enrolled=False,
        results=(
            ProxyEnrollmentResult(
                backend_url="https://backend.example.test",
                status_code=500,
                response={"error": "upstream failure"},
            ),
        ),
    )

    assert result.as_dict() == {
        "tenant_id": "default",
        "name": "PAR1 proxy",
        "enrolled": False,
        "results": [
            {
                "backend_url": "https://backend.example.test",
                "status_code": 500,
                "response": {"error": "upstream failure"},
            }
        ],
    }


def test_proxy_enrollment_config_validator_accepts_secure_full_config(tmp_path: Path) -> None:
    result = ProxyEnrollmentBatchResult(
        tenant_id="default",
        name="PAR1 proxy",
        enrolled=True,
        results=(
            ProxyEnrollmentResult(
                backend_url="https://backend.example.test",
                status_code=201,
                response={"id": "collector-1", "kind": "site-proxy"},
            ),
        ),
    )
    output = tmp_path / "proxy-enrollment.json"
    ProxyEnrollmentConfigWriter().write(output, result)

    report = ProxyEnrollmentConfigValidator().validate(output)

    assert report.valid is True
    assert report.enterprise_only is True
    assert report.backend_count == 1
    assert report.errors == ()
    assert report.as_dict()["tenant_id"] == "default"


def test_proxy_enrollment_config_validator_rejects_missing_file(tmp_path: Path) -> None:
    report = ProxyEnrollmentConfigValidator().validate(tmp_path / "missing.json")

    assert report.valid is False
    assert report.errors == ("proxy enrollment config file does not exist",)
    assert report.backend_count == 0


def test_proxy_enrollment_config_validator_reports_schema_and_partial_errors(
    tmp_path: Path,
) -> None:
    output = tmp_path / "proxy-enrollment.json"
    output.write_text(
        json.dumps(
            {
                "tenant_id": "default",
                "name": "PAR1 proxy",
                "enrolled": False,
                "results": [
                    {
                        "backend_url": "http://backend.example.test",
                        "status_code": 403,
                        "response": {"error": "forbidden"},
                    },
                    {"backend_url": "https://backend-b.example.test", "status_code": 200},
                ],
            }
        ),
        encoding="utf-8",
    )
    output.chmod(0o644)

    report = ProxyEnrollmentConfigValidator().validate(output)
    relaxed = ProxyEnrollmentConfigValidator().validate(output, strict=False)

    assert report.valid is False
    assert report.backend_count == 2
    assert any("group/world readable" in item for item in report.errors)
    assert any("backend_url is invalid" in item for item in report.errors)
    assert any("failed with HTTP 403" in item for item in report.errors)
    assert any("not fully enrolled" in item for item in report.errors)
    assert any("response must be a JSON object" in item for item in report.errors)
    assert relaxed.valid is False
    assert any("not fully enrolled" in item for item in relaxed.warnings)


def test_proxy_enrollment_config_validator_rejects_non_json_object(tmp_path: Path) -> None:
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("not-json", encoding="utf-8")
    invalid_json.chmod(0o600)
    array_json = tmp_path / "array.json"
    array_json.write_text("[]", encoding="utf-8")
    array_json.chmod(0o600)

    invalid_report = ProxyEnrollmentConfigValidator().validate(invalid_json)
    array_report = ProxyEnrollmentConfigValidator().validate(array_json)

    assert any("not valid JSON" in item for item in invalid_report.errors)
    assert any("must be a JSON object" in item for item in array_report.errors)


def test_proxy_enrollment_config_validator_reports_malformed_result_items(
    tmp_path: Path,
) -> None:
    output = tmp_path / "proxy-enrollment.json"
    output.write_text(
        json.dumps(
            {
                "tenant_id": "default",
                "name": "PAR1 proxy",
                "enrolled": "yes",
                "results": [
                    "not-object",
                    {"status_code": "created", "response": {}},
                ],
            }
        ),
        encoding="utf-8",
    )
    output.chmod(0o600)

    report = ProxyEnrollmentConfigValidator().validate(output)

    assert any("enrolled flag must be boolean" in item for item in report.errors)
    assert any("result #1 must be a JSON object" in item for item in report.errors)
    assert any("result #2 backend_url is mandatory" in item for item in report.errors)
    assert any(
        "result #2 status_code must be an HTTP status code" in item for item in report.errors
    )
