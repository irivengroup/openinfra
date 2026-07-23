from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.ports import ArtifactStore
from openinfra.domain.async_processing import ArtifactReference, OutboxEvent
from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.infrastructure.async_processing import (
    FileOutboxPublisher,
    LocalArtifactStore,
    S3ArtifactStore,
)


def test_local_artifact_store_is_content_addressed_and_tenant_isolated(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")

    first = store.write(tenant, "async-result", b'{"ok":true}', "application/json")
    second = store.write(tenant, "async-result", b'{"ok":true}', "application/json")

    assert second.object_key == first.object_key
    assert first.object_key.endswith(".json")
    assert store.read(tenant, first) == b'{"ok":true}'
    with pytest.raises(ConflictError, match="belong"):
        store.read(TenantId.from_value("other"), first)


def test_local_artifact_store_streams_and_materializes_without_loading_whole_payload(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")
    chunks = (b"", b"header\n", b"row-1\n", b"row-2\n")

    reference = store.write_stream(
        tenant,
        "imports-source",
        chunks,
        "text/csv",
        max_size_bytes=64,
    )
    target = tmp_path / "materialized" / "dataset.csv"
    store.materialize(tenant, reference, target)

    assert reference.size_bytes == len(b"header\nrow-1\nrow-2\n")
    assert reference.object_key.endswith(".csv")
    assert target.read_bytes() == b"header\nrow-1\nrow-2\n"


def test_local_artifact_store_stream_rejects_oversized_content_and_cleans_staging(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")

    with pytest.raises(ValidationError, match="size limit"):
        store.write_stream(
            tenant,
            "imports-source",
            (b"1234", b"5678"),
            "application/octet-stream",
            max_size_bytes=7,
        )

    staging = store.root / "default/.staging/imports-source"
    assert tuple(staging.iterdir()) == ()


def test_local_artifact_store_accepts_a_concurrent_identical_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")
    payload = b"concurrent-payload"
    digest = hashlib.sha256(payload).hexdigest()
    target = store.root / f"default/async-result/{digest[:2]}/{digest}.bin"
    original_exists = Path.exists
    target_checks = 0

    def exists_with_concurrent_publish(path: Path) -> bool:
        nonlocal target_checks
        if path == target:
            target_checks += 1
            if target_checks == 1:
                return False
            if target_checks == 2:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                return True
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists_with_concurrent_publish)

    reference = store.write(tenant, "async-result", payload, "application/octet-stream")

    assert target_checks == 2
    assert reference.object_key == target.relative_to(store.root).as_posix()
    assert store.read(tenant, reference) == payload
    assert tuple(target.parent.glob("tmp*")) == ()


def test_local_artifact_store_detects_content_corruption(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")
    reference = store.write(tenant, "async-result", b"expected", "application/octet-stream")
    (store.root / reference.object_key).write_bytes(b"corrupted")

    with pytest.raises(ConflictError, match="integrity"):
        store.read(tenant, reference)


def test_s3_artifact_store_signs_put_and_get_and_verifies_metadata() -> None:
    objects: dict[str, bytes] = {}
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "objects.example.test"
        assert request.headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=ACCESS123/")
        assert "SignedHeaders=" in request.headers["authorization"]
        assert request.headers["x-amz-security-token"] == "temporary-token"
        key = request.url.path
        if request.method == "PUT":
            objects[key] = request.content
            return httpx.Response(200, request=request)
        payload = objects.get(key)
        if payload is None:
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            content=payload,
            headers={
                "x-amz-meta-sha256": hashlib.sha256(payload).hexdigest(),
                "x-amz-meta-size": str(len(payload)),
            },
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106 -- deterministic test credential
        session_token="temporary-token",  # noqa: S106 -- deterministic test credential
        client=client,
    )
    tenant = TenantId.from_value("default")

    reference = store.write(tenant, "async-payload", b'{"scope":"all"}', "application/json")

    assert reference.object_key.startswith("default/async-payload/")
    assert requests[0].url.path == "/openinfra-artifacts/" + reference.object_key
    assert store.read(tenant, reference) == b'{"scope":"all"}'
    assert [request.method for request in requests] == ["PUT", "GET"]
    store.close()
    client.close()


def test_s3_artifact_store_streams_upload_and_materializes_download(tmp_path: Path) -> None:
    objects: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path
        if request.method == "PUT":
            payload = request.read()
            objects[key] = payload
            assert request.headers["content-length"] == str(len(payload))
            return httpx.Response(200, request=request)
        payload = objects.get(key)
        if payload is None:
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            content=payload,
            headers={
                "x-amz-meta-sha256": hashlib.sha256(payload).hexdigest(),
                "x-amz-meta-size": str(len(payload)),
            },
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=client,
    )
    tenant = TenantId.from_value("default")
    reference = store.write_stream(
        tenant,
        "imports-source",
        (b"first-", b"second"),
        "application/octet-stream",
        max_size_bytes=32,
    )
    target = tmp_path / "downloads" / "artifact.bin"

    store.materialize(tenant, reference, target)

    assert target.read_bytes() == b"first-second"
    assert reference.size_bytes == 12
    client.close()


def test_s3_artifact_store_rejects_unavailable_or_corrupted_content() -> None:
    payload = b"wrong"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("missing.bin"):
            return httpx.Response(404, request=request)
        return httpx.Response(200, content=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = S3ArtifactStore(
        endpoint="http://127.0.0.1:9000",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106 -- deterministic test credential
        verify_tls=False,
        client=client,
    )
    tenant = TenantId.from_value("default")
    expected = ArtifactReference.create(
        object_key="default/async-result/aa/missing.bin",
        sha256=hashlib.sha256(b"expected").hexdigest(),
        size_bytes=8,
        media_type="application/octet-stream",
    )
    with pytest.raises(ConflictError, match="unavailable"):
        store.read(tenant, expected)

    corrupted = ArtifactReference.create(
        object_key="default/async-result/aa/corrupted.bin",
        sha256=hashlib.sha256(b"expected").hexdigest(),
        size_bytes=8,
        media_type="application/octet-stream",
    )
    with pytest.raises(ConflictError, match="integrity"):
        store.read(tenant, corrupted)
    client.close()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"endpoint": "ftp://example.test"}, "endpoint"),
        ({"endpoint": "http://example.test", "verify_tls": True}, "HTTPS"),
        ({"bucket": "Invalid_Bucket"}, "bucket"),
        ({"region": "x"}, "region"),
        ({"access_key": "x"}, "access key"),
        ({"secret_key": "short"}, "secret key"),
        ({"session_token": " "}, "session token"),
        ({"timeout_seconds": 0.5}, "timeout"),
    ],
)
def test_s3_artifact_store_validates_configuration(
    overrides: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "endpoint": "https://objects.example.test",
        "bucket": "openinfra-artifacts",
        "region": "eu-west-3",
        "access_key": "ACCESS123",
        "secret_key": "secret-key-value",
    }
    values.update(overrides)

    with pytest.raises(ValidationError, match=message):
        S3ArtifactStore(**values)  # type: ignore[arg-type]


def test_application_factory_selects_s3_artifact_store_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = {
        "OPENINFRA_ASYNC_ARTIFACT_BACKEND": "s3",
        "OPENINFRA_S3_ENDPOINT": "https://objects.example.test",
        "OPENINFRA_S3_BUCKET": "openinfra-artifacts",
        "OPENINFRA_S3_REGION": "eu-west-3",
        "OPENINFRA_S3_ACCESS_KEY": "ACCESS123",
        "OPENINFRA_S3_SECRET_KEY": "secret-key-value",
        "OPENINFRA_S3_SESSION_TOKEN": "temporary-token",
        "OPENINFRA_S3_VERIFY_TLS": "true",
        "OPENINFRA_S3_TIMEOUT_SECONDS": "15",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)

    assert isinstance(app.artifact_store, S3ArtifactStore)
    app.artifact_store.close()


def test_application_factory_rejects_incomplete_s3_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENINFRA_ASYNC_ARTIFACT_BACKEND", "s3")
    monkeypatch.setenv("OPENINFRA_S3_ENDPOINT", "https://objects.example.test")

    with pytest.raises(ValueError, match="missing S3 artifact configuration"):
        ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)


def test_local_artifact_store_error_contracts(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError, match="purpose"):
        store.write(tenant, "?", b"payload", "application/octet-stream")
    with pytest.raises(ValidationError, match="escapes"):
        store._resolve("../escape")

    missing = ArtifactReference.create(
        object_key="default/async-result/aa/" + "a" * 64 + ".bin",
        sha256="a" * 64,
        size_bytes=1,
        media_type="application/octet-stream",
    )
    with pytest.raises(ConflictError, match="unavailable"):
        store.read(tenant, missing)

    reference = store.write(tenant, "async-result", b"stable", "text/plain")
    target = store.root / reference.object_key
    target.write_bytes(b"different")
    with pytest.raises(ConflictError, match="different content"):
        store.write(tenant, "async-result", b"stable", "text/plain")


def test_s3_artifact_store_http_and_metadata_failures() -> None:
    tenant = TenantId.from_value("default")

    def status_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "PUT":
            return httpx.Response(503, request=request)
        return httpx.Response(500, request=request)

    client = httpx.Client(transport=httpx.MockTransport(status_handler))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=client,
    )
    with pytest.raises(ConflictError, match="write failed"):
        store.write(tenant, "async-result", b"payload", "application/octet-stream")
    reference = ArtifactReference.create(
        object_key="default/async-result/aa/" + "a" * 64 + ".bin",
        sha256=hashlib.sha256(b"payload").hexdigest(),
        size_bytes=7,
        media_type="application/octet-stream",
    )
    with pytest.raises(ConflictError, match="read failed"):
        store.read(tenant, reference)
    with pytest.raises(ConflictError, match="belong"):
        store.read(TenantId.from_value("other"), reference)
    client.close()

    def metadata_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"payload",
            headers={"x-amz-meta-sha256": "0" * 64, "x-amz-meta-size": "999"},
            request=request,
        )

    metadata_client = httpx.Client(transport=httpx.MockTransport(metadata_handler))
    metadata_store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=metadata_client,
    )
    with pytest.raises(ConflictError, match="metadata"):
        metadata_store.read(tenant, reference)
    metadata_client.close()


def test_s3_artifact_store_wraps_transport_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=client,
    )
    with pytest.raises(ConflictError, match="request failed"):
        store.write(
            TenantId.from_value("default"),
            "async-result",
            b"payload",
            "application/octet-stream",
        )
    client.close()


def test_s3_artifact_store_rejects_size_and_metadata_size_mismatch() -> None:
    tenant = TenantId.from_value("default")
    payload = b"payload"
    digest = hashlib.sha256(payload).hexdigest()

    responses = (
        ({}, 8, "integrity"),
        ({"x-amz-meta-sha256": digest, "x-amz-meta-size": "8"}, 7, "metadata"),
    )
    for headers, size, message in responses:
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request, headers=headers: httpx.Response(
                    200, content=payload, headers=headers, request=request
                )
            )
        )
        store = S3ArtifactStore(
            endpoint="https://objects.example.test",
            bucket="openinfra-artifacts",
            region="eu-west-3",
            access_key="ACCESS123",
            secret_key="secret-key-value",  # noqa: S106
            client=client,
        )
        reference = ArtifactReference.create(
            object_key="default/async-result/aa/" + digest + ".bin",
            sha256=digest,
            size_bytes=size,
            media_type="application/octet-stream",
        )
        with pytest.raises(ConflictError, match=message):
            store.read(tenant, reference)
        client.close()


def test_file_outbox_publisher_is_idempotent_and_detects_conflicts(tmp_path: Path) -> None:
    event = OutboxEvent.create(
        tenant_id=TenantId.from_value("default"),
        aggregate_type="async-job",
        aggregate_id="job-001",
        event_name="async.job.submitted",
        idempotency_key="publisher-001",
        payload={"job_id": "job-001"},
    )
    publisher = FileOutboxPublisher(tmp_path / "events")
    publisher.publish(event)
    publisher.publish(event)
    target = tmp_path / "events" / "default" / f"{event.id.value}.json"
    target.write_text("conflict", encoding="utf-8")
    with pytest.raises(ConflictError, match="conflicts"):
        publisher.publish(event)


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({"OPENINFRA_ASYNC_ARTIFACT_BACKEND": "invalid"}, "filesystem or s3"),
        (
            {
                "OPENINFRA_ASYNC_ARTIFACT_BACKEND": "s3",
                "OPENINFRA_S3_ENDPOINT": "https://objects.example.test",
                "OPENINFRA_S3_BUCKET": "openinfra-artifacts",
                "OPENINFRA_S3_REGION": "eu-west-3",
                "OPENINFRA_S3_ACCESS_KEY": "ACCESS123",
                "OPENINFRA_S3_SECRET_KEY": "secret-key-value",
                "OPENINFRA_S3_VERIFY_TLS": "maybe",
            },
            "must be true or false",
        ),
        (
            {
                "OPENINFRA_ASYNC_ARTIFACT_BACKEND": "s3",
                "OPENINFRA_S3_ENDPOINT": "https://objects.example.test",
                "OPENINFRA_S3_BUCKET": "openinfra-artifacts",
                "OPENINFRA_S3_REGION": "eu-west-3",
                "OPENINFRA_S3_ACCESS_KEY": "ACCESS123",
                "OPENINFRA_S3_SECRET_KEY": "secret-key-value",
                "OPENINFRA_S3_TIMEOUT_SECONDS": "not-a-number",
            },
            "must be numeric",
        ),
    ],
)
def test_application_factory_rejects_invalid_artifact_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    environment: dict[str, str],
    message: str,
) -> None:
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=message):
        ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)


class _FallbackArtifactStore(ArtifactStore):
    def __init__(self) -> None:
        self.payload = b""

    def write(
        self,
        tenant_id: TenantId,
        purpose: str,
        content: bytes,
        media_type: str,
    ) -> ArtifactReference:
        self.payload = bytes(content)
        return ArtifactReference.create(
            object_key=f"{tenant_id.value}/{purpose}/fallback.bin",
            sha256=hashlib.sha256(self.payload).hexdigest(),
            size_bytes=len(self.payload),
            media_type=media_type,
        )

    def read(self, tenant_id: TenantId, reference: ArtifactReference) -> bytes:
        assert reference.object_key.startswith(tenant_id.value + "/")
        return self.payload


def test_artifact_store_default_stream_and_materialize_contract(tmp_path: Path) -> None:
    store = _FallbackArtifactStore()
    tenant = TenantId.from_value("default")

    with pytest.raises(ValidationError, match="positive"):
        store.write_stream(
            tenant,
            "fallback",
            (b"payload",),
            "application/octet-stream",
            max_size_bytes=0,
        )
    with pytest.raises(ValidationError, match="size limit"):
        store.write_stream(
            tenant,
            "fallback",
            (b"1234", b"5678"),
            "application/octet-stream",
            max_size_bytes=7,
        )

    reference = store.write_stream(
        tenant,
        "fallback",
        (b"", b"first-", b"second"),
        "application/octet-stream",
        max_size_bytes=32,
    )
    target = tmp_path / "fallback" / "nested" / "artifact.bin"
    store.materialize(tenant, reference, target)

    assert target.read_bytes() == b"first-second"


def test_local_artifact_store_materialize_rejects_invalid_sources(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "objects")
    tenant = TenantId.from_value("default")
    other_tenant = TenantId.from_value("other")

    with pytest.raises(ValidationError, match="positive"):
        store.write_stream(
            tenant,
            "imports-source",
            (b"payload",),
            "application/octet-stream",
            max_size_bytes=0,
        )

    missing = ArtifactReference.create(
        object_key="default/imports-source/aa/" + "a" * 64 + ".bin",
        sha256="a" * 64,
        size_bytes=1,
        media_type="application/octet-stream",
    )
    with pytest.raises(ConflictError, match="belong"):
        store.materialize(other_tenant, missing, tmp_path / "wrong-tenant.bin")
    with pytest.raises(ConflictError, match="unavailable"):
        store.materialize(tenant, missing, tmp_path / "missing.bin")

    reference = store.write(
        tenant,
        "imports-source",
        b"expected",
        "application/octet-stream",
    )
    (store.root / reference.object_key).write_bytes(b"corrupt!")
    target = tmp_path / "corrupted" / "artifact.bin"
    with pytest.raises(ConflictError, match="integrity"):
        store.materialize(tenant, reference, target)
    assert not target.exists()
    assert tuple(target.parent.iterdir()) == ()


def test_s3_stream_validation_and_failed_publication() -> None:
    tenant = TenantId.from_value("default")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=client,
    )

    with pytest.raises(ValidationError, match="positive"):
        store.write_stream(
            tenant,
            "imports-source",
            (b"payload",),
            "application/octet-stream",
            max_size_bytes=0,
        )
    with pytest.raises(ValidationError, match="size limit"):
        store.write_stream(
            tenant,
            "imports-source",
            (b"", b"1234", b"5678"),
            "application/octet-stream",
            max_size_bytes=7,
        )
    assert requests == []

    with pytest.raises(ConflictError, match="write failed"):
        store.write_stream(
            tenant,
            "imports-source",
            (b"payload",),
            "application/octet-stream",
            max_size_bytes=32,
        )
    assert len(requests) == 1
    client.close()


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("missing", "unavailable"),
        ("server-error", "read failed"),
        ("corrupt", "integrity"),
        ("metadata-hash", "metadata"),
        ("metadata-size", "metadata"),
        ("transport", "request failed"),
    ],
)
def test_s3_materialize_fail_closed(
    tmp_path: Path,
    mode: str,
    message: str,
) -> None:
    tenant = TenantId.from_value("default")
    payload = b"payload"
    digest = hashlib.sha256(payload).hexdigest()
    reference = ArtifactReference.create(
        object_key=f"default/imports-source/{digest[:2]}/{digest}.bin",
        sha256=digest,
        size_bytes=len(payload),
        media_type="application/octet-stream",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if mode == "transport":
            raise httpx.ConnectError("offline", request=request)
        if mode == "missing":
            return httpx.Response(404, request=request)
        if mode == "server-error":
            return httpx.Response(503, request=request)
        response_payload = b"corrupt" if mode == "corrupt" else payload
        headers = {
            "x-amz-meta-sha256": "0" * 64 if mode == "metadata-hash" else digest,
            "x-amz-meta-size": "999" if mode == "metadata-size" else str(len(payload)),
        }
        return httpx.Response(200, content=response_payload, headers=headers, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=client,
    )
    target = tmp_path / mode / "artifact.bin"

    with pytest.raises(ConflictError, match=message):
        store.materialize(tenant, reference, target)
    assert not target.exists()
    if target.parent.exists():
        assert tuple(target.parent.iterdir()) == ()
    client.close()


def test_s3_materialize_enforces_tenant_ownership(tmp_path: Path) -> None:
    reference = ArtifactReference.create(
        object_key="default/imports-source/aa/" + "a" * 64 + ".bin",
        sha256="a" * 64,
        size_bytes=1,
        media_type="application/octet-stream",
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    store = S3ArtifactStore(
        endpoint="https://objects.example.test",
        bucket="openinfra-artifacts",
        region="eu-west-3",
        access_key="ACCESS123",
        secret_key="secret-key-value",  # noqa: S106
        client=client,
    )

    with pytest.raises(ConflictError, match="belong"):
        store.materialize(TenantId.from_value("other"), reference, tmp_path / "artifact.bin")
    client.close()
