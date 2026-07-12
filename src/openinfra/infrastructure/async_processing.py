from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast
from urllib.parse import quote, urlparse

import httpx

from openinfra.application.ports import (
    ArtifactStore,
    AsyncJobPage,
    AsyncProcessingRepository,
    OutboxEventPage,
    OutboxPublisher,
)
from openinfra.domain.async_processing import (
    ArtifactReference,
    AsyncJob,
    OutboxEvent,
    WorkerSpecialization,
    WorkStatus,
)
from openinfra.domain.common import ConflictError, Pagination, TenantId, ValidationError
from openinfra.infrastructure.json_store import JsonDocumentStore


class LocalArtifactStore(ArtifactStore):
    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def write(
        self,
        tenant_id: TenantId,
        purpose: str,
        content: bytes,
        media_type: str,
    ) -> ArtifactReference:
        normalized_purpose = self._normalize_purpose(purpose)
        payload = bytes(content)
        digest = hashlib.sha256(payload).hexdigest()
        extension = self._extension(media_type)
        object_key = f"{tenant_id.value}/{normalized_purpose}/{digest[:2]}/{digest}{extension}"
        target = self._resolve(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            self._verify_existing(target, payload, digest)
        else:
            with NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            try:
                if target.exists():
                    self._verify_existing(target, payload, digest)
                else:
                    temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return ArtifactReference.create(
            object_key=object_key,
            sha256=digest,
            size_bytes=len(payload),
            media_type=media_type,
        )

    def read(self, tenant_id: TenantId, reference: ArtifactReference) -> bytes:
        if not reference.object_key.startswith(tenant_id.value + "/"):
            raise ConflictError("artifact does not belong to the requested tenant")
        target = self._resolve(reference.object_key)
        try:
            payload = target.read_bytes()
        except OSError as exc:
            raise ConflictError("artifact content is unavailable") from exc
        digest = hashlib.sha256(payload).hexdigest()
        if digest != reference.sha256 or len(payload) != reference.size_bytes:
            raise ConflictError("artifact integrity verification failed")
        return payload

    def _resolve(self, object_key: str) -> Path:
        target = (self._root / object_key).resolve()
        root = self._root.resolve()
        if target != root and root not in target.parents:
            raise ValidationError("artifact path escapes configured root")
        return target

    @staticmethod
    def _verify_existing(target: Path, payload: bytes, digest: str) -> None:
        existing = target.read_bytes()
        if hashlib.sha256(existing).hexdigest() != digest or existing != payload:
            raise ConflictError("artifact object key already contains different content")

    @staticmethod
    def _normalize_purpose(value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", normalized):
            raise ValidationError("artifact purpose is invalid")
        return normalized

    @staticmethod
    def _extension(media_type: str) -> str:
        normalized = media_type.strip().lower()
        return {
            "application/json": ".json",
            "text/csv": ".csv",
            "text/plain": ".txt",
            "application/zip": ".zip",
            "application/octet-stream": ".bin",
        }.get(normalized, ".bin")


class S3ArtifactStore(ArtifactStore):
    """S3-compatible, content-addressed artifact store signed with AWS Signature V4."""

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        session_token: str | None = None,
        verify_tls: bool = True,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        parsed = urlparse(endpoint.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise ValidationError("S3 endpoint must be an absolute HTTP(S) URL without query")
        if parsed.scheme != "https" and verify_tls:
            raise ValidationError("S3 endpoint must use HTTPS when TLS verification is enabled")
        normalized_bucket = bucket.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", normalized_bucket):
            raise ValidationError("S3 bucket name is invalid")
        normalized_region = region.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", normalized_region):
            raise ValidationError("S3 region is invalid")
        normalized_access_key = access_key.strip()
        if not 3 <= len(normalized_access_key) <= 128:
            raise ValidationError("S3 access key is invalid")
        if not 8 <= len(secret_key) <= 256:
            raise ValidationError("S3 secret key is invalid")
        if session_token is not None and not session_token.strip():
            raise ValidationError("S3 session token cannot be empty")
        if not 1 <= float(timeout_seconds) <= 300:
            raise ValidationError("S3 timeout must be between 1 and 300 seconds")
        self._endpoint = endpoint.strip().rstrip("/")
        self._bucket = normalized_bucket
        self._region = normalized_region
        self._access_key = normalized_access_key
        self._secret_key = secret_key
        self._session_token = None if session_token is None else session_token.strip()
        self._client = client or httpx.Client(
            verify=verify_tls,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def write(
        self,
        tenant_id: TenantId,
        purpose: str,
        content: bytes,
        media_type: str,
    ) -> ArtifactReference:
        normalized_purpose = LocalArtifactStore._normalize_purpose(purpose)
        payload = bytes(content)
        digest = hashlib.sha256(payload).hexdigest()
        extension = LocalArtifactStore._extension(media_type)
        object_key = f"{tenant_id.value}/{normalized_purpose}/{digest[:2]}/{digest}{extension}"
        response = self._request(
            "PUT",
            object_key,
            payload,
            {
                "content-type": media_type.strip().lower(),
                "x-amz-meta-sha256": digest,
                "x-amz-meta-size": str(len(payload)),
            },
        )
        if response.status_code not in {200, 201, 204}:
            raise ConflictError(f"S3 artifact write failed with status {response.status_code}")
        return ArtifactReference.create(
            object_key=object_key,
            sha256=digest,
            size_bytes=len(payload),
            media_type=media_type,
        )

    def read(self, tenant_id: TenantId, reference: ArtifactReference) -> bytes:
        if not reference.object_key.startswith(tenant_id.value + "/"):
            raise ConflictError("artifact does not belong to the requested tenant")
        response = self._request("GET", reference.object_key, b"", {})
        if response.status_code == 404:
            raise ConflictError("artifact content is unavailable")
        if response.status_code != 200:
            raise ConflictError(f"S3 artifact read failed with status {response.status_code}")
        payload = response.content
        if hashlib.sha256(payload).hexdigest() != reference.sha256:
            raise ConflictError("artifact integrity verification failed")
        if len(payload) != reference.size_bytes:
            raise ConflictError("artifact integrity verification failed")
        metadata_hash = response.headers.get("x-amz-meta-sha256")
        metadata_size = response.headers.get("x-amz-meta-size")
        if metadata_hash is not None and metadata_hash != reference.sha256:
            raise ConflictError("artifact metadata verification failed")
        if metadata_size is not None and metadata_size != str(reference.size_bytes):
            raise ConflictError("artifact metadata verification failed")
        return payload

    def _request(
        self,
        method: str,
        object_key: str,
        payload: bytes,
        headers: dict[str, str],
    ) -> httpx.Response:
        now = datetime.now(UTC)
        payload_hash = hashlib.sha256(payload).hexdigest()
        canonical_uri = "/" + quote(self._bucket, safe="") + "/" + quote(object_key, safe="/-_.~")
        url = self._endpoint + canonical_uri
        parsed = urlparse(url)
        signed_headers = {
            "host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": now.strftime("%Y%m%dT%H%M%SZ"),
            **{key.lower(): value.strip() for key, value in headers.items()},
        }
        if self._session_token is not None:
            signed_headers["x-amz-security-token"] = self._session_token
        canonical_header_names = sorted(signed_headers)
        canonical_headers = "".join(
            f"{name}:{' '.join(signed_headers[name].split())}\n" for name in canonical_header_names
        )
        signed_header_list = ";".join(canonical_header_names)
        canonical_request = "\n".join(
            (
                method,
                canonical_uri,
                "",
                canonical_headers,
                signed_header_list,
                payload_hash,
            )
        )
        date = now.strftime("%Y%m%d")
        scope = f"{date}/{self._region}/s3/aws4_request"
        string_to_sign = "\n".join(
            (
                "AWS4-HMAC-SHA256",
                signed_headers["x-amz-date"],
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            )
        )
        signing_key = self._signing_key(date)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        request_headers = {
            **signed_headers,
            "authorization": (
                "AWS4-HMAC-SHA256 "
                f"Credential={self._access_key}/{scope},"
                f"SignedHeaders={signed_header_list},Signature={signature}"
            ),
        }
        try:
            return self._client.request(
                method, url, content=payload if method == "PUT" else None, headers=request_headers
            )
        except httpx.HTTPError as exc:
            raise ConflictError("S3 artifact request failed") from exc

    def _signing_key(self, date: str) -> bytes:
        key_date = hmac.new(
            ("AWS4" + self._secret_key).encode("utf-8"), date.encode("ascii"), hashlib.sha256
        ).digest()
        key_region = hmac.new(key_date, self._region.encode("utf-8"), hashlib.sha256).digest()
        key_service = hmac.new(key_region, b"s3", hashlib.sha256).digest()
        return hmac.new(key_service, b"aws4_request", hashlib.sha256).digest()


class FileOutboxPublisher(OutboxPublisher):
    def __init__(self, root: Path) -> None:
        self._root = root

    def publish(self, event: OutboxEvent) -> None:
        payload = json.dumps(
            event.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        target = self._target(event)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != payload:
                raise ConflictError("published event file conflicts with existing event id")
            return
        with NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        try:
            if target.exists():
                if target.read_bytes() != payload:
                    raise ConflictError("published event file conflicts with existing event id")
            else:
                temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def _target(self, event: OutboxEvent) -> Path:
        target = (self._root / event.tenant_id.value / f"{event.id.value}.json").resolve()
        root = self._root.resolve()
        if root not in target.parents:
            raise ValidationError("event sink path escapes configured root")
        return target


class JsonAsyncProcessingRepository(AsyncProcessingRepository):
    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def save_job(self, job: AsyncJob) -> None:
        key = self._key(job.tenant_id, job.id.value)
        with self._store.lock:
            self._assert_unique_idempotency("async_jobs", key, job.tenant_id, job.idempotency_key)
            current_payload = self._store.data["async_jobs"].get(key)
            if current_payload is not None:
                current = AsyncJob.from_dict(cast(dict[str, object], current_payload))
                job.assert_persistence_transition_from(current)
                if job == current:
                    return
            self._store.data["async_jobs"][key] = job.as_dict()
            self._store.mark_dirty()

    def get_job(self, tenant_id: TenantId, job_id: str) -> AsyncJob | None:
        with self._store.lock:
            payload = self._store.data["async_jobs"].get(self._key(tenant_id, job_id))
            return None if payload is None else AsyncJob.from_dict(cast(dict[str, object], payload))

    def find_job_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> AsyncJob | None:
        with self._store.lock:
            for payload in self._tenant_payloads("async_jobs", tenant_id):
                if str(payload.get("idempotency_key", "")) == idempotency_key.strip():
                    return AsyncJob.from_dict(payload)
        return None

    def lock_job_idempotency(self, tenant_id: TenantId, idempotency_key: str) -> None:
        TenantId.from_value(tenant_id.value)
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise ValidationError("idempotency key is required")
        # JsonUnitOfWork already holds the process-wide reentrant store lock.

    def claim_next_job(
        self,
        tenant_id: TenantId,
        specialization: WorkerSpecialization,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
    ) -> AsyncJob | None:
        with self._store.lock:
            jobs = sorted(
                (
                    AsyncJob.from_dict(payload)
                    for payload in self._tenant_payloads("async_jobs", tenant_id)
                    if str(payload.get("specialization")) == specialization.value
                ),
                key=lambda item: (item.created_at, item.id.value),
            )
            for job in jobs:
                if (
                    job.state.status is WorkStatus.LEASED
                    and job.state.leased_until is not None
                    and job.state.leased_until <= now
                    and job.state.attempt_count >= job.state.max_attempts
                ):
                    expired = job.expire_final_lease(now)
                    self._store.data["async_jobs"][self._key(tenant_id, job.id.value)] = (
                        expired.as_dict()
                    )
                    self._store.mark_dirty()
                    continue
                if job.state.is_claimable(now):
                    claimed = job.claim(worker_id, lease_seconds, now)
                    self._store.data["async_jobs"][self._key(tenant_id, job.id.value)] = (
                        claimed.as_dict()
                    )
                    self._store.mark_dirty()
                    return claimed
        return None

    def list_jobs(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: WorkStatus | None = None,
        specialization: WorkerSpecialization | None = None,
    ) -> AsyncJobPage:
        with self._store.lock:
            items = sorted(
                (
                    AsyncJob.from_dict(payload)
                    for payload in self._tenant_payloads("async_jobs", tenant_id)
                    if (status is None or str(payload.get("status")) == status.value)
                    and (
                        specialization is None
                        or str(payload.get("specialization")) == specialization.value
                    )
                ),
                key=lambda item: (item.created_at, item.id.value),
            )
        selected, cursor = self._page(items, pagination)
        return AsyncJobPage(tuple(selected), cursor)

    def save_outbox_event(self, event: OutboxEvent) -> None:
        key = self._key(event.tenant_id, event.id.value)
        with self._store.lock:
            self._assert_unique_idempotency(
                "outbox_events", key, event.tenant_id, event.idempotency_key
            )
            current_payload = self._store.data["outbox_events"].get(key)
            if current_payload is not None:
                current = OutboxEvent.from_dict(cast(dict[str, object], current_payload))
                event.assert_persistence_transition_from(current)
                if event == current:
                    return
            self._store.data["outbox_events"][key] = event.as_dict()
            self._store.mark_dirty()

    def get_outbox_event(self, tenant_id: TenantId, event_id: str) -> OutboxEvent | None:
        with self._store.lock:
            payload = self._store.data["outbox_events"].get(self._key(tenant_id, event_id))
            return (
                None if payload is None else OutboxEvent.from_dict(cast(dict[str, object], payload))
            )

    def claim_next_outbox_event(
        self,
        tenant_id: TenantId,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
    ) -> OutboxEvent | None:
        with self._store.lock:
            events = sorted(
                (
                    OutboxEvent.from_dict(payload)
                    for payload in self._tenant_payloads("outbox_events", tenant_id)
                ),
                key=lambda item: (item.created_at, item.id.value),
            )
            for event in events:
                if (
                    event.state.status is WorkStatus.LEASED
                    and event.state.leased_until is not None
                    and event.state.leased_until <= now
                    and event.state.attempt_count >= event.state.max_attempts
                ):
                    expired = event.expire_final_lease(now)
                    self._store.data["outbox_events"][self._key(tenant_id, event.id.value)] = (
                        expired.as_dict()
                    )
                    self._store.mark_dirty()
                    continue
                if event.state.is_claimable(now):
                    claimed = event.claim(worker_id, lease_seconds, now)
                    self._store.data["outbox_events"][self._key(tenant_id, event.id.value)] = (
                        claimed.as_dict()
                    )
                    self._store.mark_dirty()
                    return claimed
        return None

    def list_outbox_events(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: WorkStatus | None = None,
    ) -> OutboxEventPage:
        with self._store.lock:
            items = sorted(
                (
                    OutboxEvent.from_dict(payload)
                    for payload in self._tenant_payloads("outbox_events", tenant_id)
                    if status is None or str(payload.get("status")) == status.value
                ),
                key=lambda item: (item.created_at, item.id.value),
            )
        selected, cursor = self._page(items, pagination)
        return OutboxEventPage(tuple(selected), cursor)

    def queue_metrics(self, tenant_id: TenantId) -> dict[str, object]:
        with self._store.lock:
            jobs = Counter(
                str(payload.get("status"))
                for payload in self._tenant_payloads("async_jobs", tenant_id)
            )
            outbox = Counter(
                str(payload.get("status"))
                for payload in self._tenant_payloads("outbox_events", tenant_id)
            )
        return {
            "tenant_id": tenant_id.value,
            "generated_at": datetime.now(UTC).isoformat(),
            "jobs": {status.value: jobs.get(status.value, 0) for status in WorkStatus},
            "outbox": {status.value: outbox.get(status.value, 0) for status in WorkStatus},
        }

    def _tenant_payloads(self, bucket: str, tenant_id: TenantId) -> list[dict[str, object]]:
        prefix = tenant_id.value + ":"
        return [
            cast(dict[str, object], payload)
            for key, payload in self._store.data[bucket].items()
            if key.startswith(prefix)
        ]

    def _assert_unique_idempotency(
        self,
        bucket: str,
        current_key: str,
        tenant_id: TenantId,
        idempotency_key: str,
    ) -> None:
        prefix = tenant_id.value + ":"
        for key, payload in self._store.data[bucket].items():
            if key == current_key or not key.startswith(prefix):
                continue
            if str(payload.get("idempotency_key", "")) == idempotency_key:
                raise ConflictError("idempotency key already exists")

    @staticmethod
    def _key(tenant_id: TenantId, entity_id: str) -> str:
        return tenant_id.value + ":" + entity_id

    @staticmethod
    def _page(items: list[Any], pagination: Pagination) -> tuple[list[Any], str | None]:
        start = 0
        if pagination.cursor:
            ids = [item.id.value for item in items]
            if pagination.cursor not in ids:
                raise ValidationError("pagination cursor is invalid")
            start = ids.index(pagination.cursor) + 1
        selected = items[start : start + pagination.limit]
        next_cursor = (
            selected[-1].id.value if start + len(selected) < len(items) and selected else None
        )
        return selected, next_cursor
