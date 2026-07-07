from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib import error, request
from urllib.parse import urljoin, urlparse

from openinfra.domain.common import ValidationError


@dataclass(frozen=True, slots=True)
class ProxyEnrollmentTarget:
    backend_url: str
    endpoint_url: str

    @classmethod
    def from_backend_url(cls, backend_url: str) -> ProxyEnrollmentTarget:
        normalized = backend_url.strip()
        if not normalized:
            raise ValidationError("backend URL is mandatory")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"https", "http"}:
            raise ValidationError("backend URL must use https")
        host = parsed.hostname or ""
        if parsed.scheme == "http" and host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValidationError("backend URL must use https outside loopback")
        if not host:
            raise ValidationError("backend URL host is mandatory")
        base = normalized if normalized.endswith("/") else normalized + "/"
        return cls(
            backend_url=normalized.rstrip("/"),
            endpoint_url=urljoin(base, "api/v1/discovery/proxy-enrollments"),
        )


@dataclass(frozen=True, slots=True)
class ProxyEnrollmentResult:
    backend_url: str
    status_code: int
    response: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "backend_url": self.backend_url,
            "status_code": self.status_code,
            "response": self.response,
        }


@dataclass(frozen=True, slots=True)
class ProxyEnrollmentBatchResult:
    tenant_id: str
    name: str
    enrolled: bool
    results: tuple[ProxyEnrollmentResult, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "enrolled": self.enrolled,
            "results": [item.as_dict() for item in self.results],
        }


class ProxyEnrollmentHttpClient:
    def enroll_many(
        self,
        *,
        backend_urls: tuple[str, ...],
        admin_token: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> ProxyEnrollmentBatchResult:
        if not backend_urls:
            raise ValidationError("at least one backend URL is required")
        if timeout_seconds <= 0 or timeout_seconds > 120:
            raise ValidationError("timeout seconds must be between 1 and 120")
        token = admin_token.strip()
        if not token:
            raise ValidationError("admin token is mandatory")
        results = tuple(
            self.enroll_one(
                target=ProxyEnrollmentTarget.from_backend_url(backend_url),
                admin_token=token,
                payload=payload,
                timeout_seconds=timeout_seconds,
            )
            for backend_url in backend_urls
        )
        return ProxyEnrollmentBatchResult(
            tenant_id=str(payload["tenant_id"]),
            name=str(payload["name"]),
            enrolled=all(HTTPStatus.OK.value <= result.status_code < 300 for result in results),
            results=results,
        )

    def enroll_one(
        self,
        *,
        target: ProxyEnrollmentTarget,
        admin_token: str,
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> ProxyEnrollmentResult:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + admin_token,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }
        upstream_request = request.Request(  # noqa: S310
            target.endpoint_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(  # noqa: S310  # nosec B310
                upstream_request,
                timeout=timeout_seconds,
            ) as response:
                raw_payload = response.read().decode("utf-8")
                return ProxyEnrollmentResult(
                    backend_url=target.backend_url,
                    status_code=int(response.status),
                    response=self._decode_response(raw_payload),
                )
        except error.HTTPError as exc:
            raw_payload = exc.read().decode("utf-8")
            return ProxyEnrollmentResult(
                backend_url=target.backend_url,
                status_code=int(exc.code),
                response=self._decode_response(raw_payload),
            )
        except error.URLError as exc:
            raise ValidationError("backend unavailable: " + str(exc.reason)) from exc

    def _decode_response(self, payload: str) -> dict[str, object]:
        try:
            decoded = json.loads(payload) if payload else {}
        except json.JSONDecodeError as exc:
            raise ValidationError("backend response is not valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValidationError("backend response must be a JSON object")
        return decoded


class ProxyEnrollmentConfigWriter:
    def write(self, path: Path, result: ProxyEnrollmentBatchResult) -> None:
        destination = path.expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n"
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(destination.parent),
            prefix=destination.name + ".",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        temporary_path.replace(destination)
        destination.chmod(0o600)


class ProxyEnrollmentPayloadFactory:
    def from_args(self, args: Any) -> dict[str, object]:
        scopes = tuple(str(scope) for scope in args.scope)
        if not scopes:
            raise ValidationError("at least one proxy scope is required")
        return {
            "tenant_id": str(args.tenant),
            "actor": str(args.actor),
            "name": str(args.name),
            "kind": str(args.kind),
            "certificate_fingerprint": str(args.certificate_fingerprint),
            "scopes": list(scopes),
            "version": str(args.version),
            "vault_secret_ref": None
            if args.vault_secret_ref is None
            else str(args.vault_secret_ref),
            "endpoint_url": str(args.endpoint_url),
        }
