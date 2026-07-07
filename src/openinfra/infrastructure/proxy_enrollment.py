from __future__ import annotations

import json
import os
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


@dataclass(frozen=True, slots=True)
class ProxyEnrollmentValidationReport:
    config_path: str
    valid: bool
    enterprise_only: bool
    tenant_id: str | None
    name: str | None
    backend_count: int
    enrolled: bool | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "config_path": self.config_path,
            "valid": self.valid,
            "enterprise_only": self.enterprise_only,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "backend_count": self.backend_count,
            "enrolled": self.enrolled,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class ProxyEnrollmentConfigValidator:
    def validate(self, path: Path, *, strict: bool = True) -> ProxyEnrollmentValidationReport:
        destination = path.expanduser().resolve()
        errors: list[str] = []
        warnings: list[str] = []
        tenant_id: str | None = None
        name: str | None = None
        backend_count = 0
        enrolled: bool | None = None

        if not destination.is_file():
            return ProxyEnrollmentValidationReport(
                config_path=str(destination),
                valid=False,
                enterprise_only=True,
                tenant_id=None,
                name=None,
                backend_count=0,
                enrolled=None,
                errors=("proxy enrollment config file does not exist",),
                warnings=(),
            )

        if os.name == "posix":
            mode = destination.stat().st_mode & 0o777
            if mode & 0o077:
                message = "proxy enrollment config file must not be group/world readable"
                if strict:
                    errors.append(message)
                else:
                    warnings.append(message)

        try:
            raw = json.loads(destination.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("proxy enrollment config is not valid JSON")
            raw = {}
        if not isinstance(raw, dict):
            errors.append("proxy enrollment config must be a JSON object")
            raw = {}

        tenant_value = raw.get("tenant_id")
        if isinstance(tenant_value, str) and tenant_value.strip():
            tenant_id = tenant_value.strip()
        else:
            errors.append("proxy enrollment config tenant_id is mandatory")

        name_value = raw.get("name")
        if isinstance(name_value, str) and name_value.strip():
            name = name_value.strip()
        else:
            errors.append("proxy enrollment config name is mandatory")

        enrolled_value = raw.get("enrolled")
        if isinstance(enrolled_value, bool):
            enrolled = enrolled_value
        else:
            errors.append("proxy enrollment config enrolled flag must be boolean")

        results_value = raw.get("results")
        if not isinstance(results_value, list) or not results_value:
            errors.append("proxy enrollment config results must be a non-empty list")
            results_value = []

        for index, item in enumerate(results_value):
            item_prefix = f"proxy enrollment result #{index + 1}"
            if not isinstance(item, dict):
                errors.append(item_prefix + " must be a JSON object")
                continue
            backend_url = item.get("backend_url")
            if not isinstance(backend_url, str):
                errors.append(item_prefix + " backend_url is mandatory")
            else:
                try:
                    ProxyEnrollmentTarget.from_backend_url(backend_url)
                except ValidationError as exc:
                    errors.append(item_prefix + " backend_url is invalid: " + str(exc))
            status_code = item.get("status_code")
            if not isinstance(status_code, int) or not 100 <= status_code <= 599:
                errors.append(item_prefix + " status_code must be an HTTP status code")
            elif strict and not HTTPStatus.OK.value <= status_code < 300:
                errors.append(item_prefix + f" failed with HTTP {status_code}")
            response = item.get("response")
            if not isinstance(response, dict):
                errors.append(item_prefix + " response must be a JSON object")
            backend_count += 1

        if strict and enrolled is False:
            errors.append("proxy enrollment config is not fully enrolled")
        if not strict and enrolled is False:
            warnings.append("proxy enrollment config is not fully enrolled")

        return ProxyEnrollmentValidationReport(
            config_path=str(destination),
            valid=not errors,
            enterprise_only=True,
            tenant_id=tenant_id,
            name=name,
            backend_count=backend_count,
            enrolled=enrolled,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )


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
