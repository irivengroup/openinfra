from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from enum import StrEnum

from openinfra.domain.common import ValidationError


class ReadRoute(StrEnum):
    PRIMARY = "primary"
    REPLICA = "replica"


class ReadRoutingContext:
    _current: ContextVar[ReadRoute] = ContextVar(
        "openinfra_current_read_route", default=ReadRoute.PRIMARY
    )

    @classmethod
    def current(cls) -> ReadRoute:
        return cls._current.get()

    @classmethod
    @contextmanager
    def scope(cls, route: ReadRoute) -> Iterator[None]:
        token: Token[ReadRoute] = cls._current.set(route)
        try:
            yield
        finally:
            cls._current.reset(token)


@dataclass(frozen=True, slots=True)
class PostgreSQLReadRoutingSettings:
    enabled: bool
    max_replica_lag_seconds: float
    probe_interval_seconds: float
    fallback_to_primary: bool
    require_recovery: bool = True

    def __post_init__(self) -> None:
        if self.max_replica_lag_seconds < 0:
            raise ValidationError("postgresql replica lag threshold cannot be negative")
        if self.probe_interval_seconds <= 0:
            raise ValidationError("postgresql replica probe interval must be positive")

    @classmethod
    def from_environment(cls, read_dsn: str) -> PostgreSQLReadRoutingSettings:
        enabled = bool(read_dsn.strip()) and cls._environment_bool(
            "OPENINFRA_DB_READ_ROUTING_ENABLED", True
        )
        return cls(
            enabled=enabled,
            max_replica_lag_seconds=float(
                os.environ.get("OPENINFRA_DB_MAX_REPLICA_LAG_SECONDS", "5")
            ),
            probe_interval_seconds=float(
                os.environ.get("OPENINFRA_DB_REPLICA_PROBE_INTERVAL_SECONDS", "2")
            ),
            fallback_to_primary=cls._environment_bool(
                "OPENINFRA_DB_READ_FALLBACK_TO_PRIMARY", True
            ),
            require_recovery=cls._environment_bool("OPENINFRA_DB_READ_REQUIRE_RECOVERY", True),
        )

    @staticmethod
    def _environment_bool(name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValidationError(f"{name} must be a boolean")


@dataclass(frozen=True, slots=True)
class PostgreSQLReplicaHealth:
    configured: bool
    eligible: bool
    is_replica: bool
    lag_seconds: float | None
    checked_at_epoch: float | None
    detail: str

    @classmethod
    def disabled(cls) -> PostgreSQLReplicaHealth:
        return cls(False, False, False, None, None, "read replica is not configured")

    def as_dict(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "eligible": self.eligible,
            "is_replica": self.is_replica,
            "lag_seconds": self.lag_seconds,
            "checked_at_epoch": self.checked_at_epoch,
            "detail": self.detail,
        }


class ReadConsistencyTokenCodec:
    _version = "v1"

    def __init__(
        self,
        secret: str,
        ttl_seconds: int = 10,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        normalized = secret.strip()
        if len(normalized) < 32:
            raise ValidationError("read consistency secret must contain at least 32 characters")
        if ttl_seconds <= 0 or ttl_seconds > 300:
            raise ValidationError("read consistency token TTL must be between 1 and 300 seconds")
        self._secret = normalized.encode("utf-8")
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def issue(self) -> str:
        issued_at = int(self._clock())
        expires_at = issued_at + self._ttl_seconds
        nonce = secrets.token_hex(8)
        payload = f"{self._version}:{issued_at}:{expires_at}:{nonce}".encode("ascii")
        signature = hmac.new(self._secret, payload, hashlib.sha256).digest()
        return self._urlsafe_encode(payload) + "." + self._urlsafe_encode(signature)

    def validate(self, token: str) -> bool:
        normalized = token.strip()
        if not normalized or len(normalized) > 512:
            return False
        try:
            encoded_payload, encoded_signature = normalized.split(".", 1)
            payload = self._urlsafe_decode(encoded_payload)
            signature = self._urlsafe_decode(encoded_signature)
            version, issued_at_raw, expires_at_raw, nonce = payload.decode("ascii").split(":", 3)
            issued_at = int(issued_at_raw)
            expires_at = int(expires_at_raw)
        except (ValueError, UnicodeDecodeError):
            return False
        expected = hmac.new(self._secret, payload, hashlib.sha256).digest()
        now = int(self._clock())
        return (
            version == self._version
            and len(nonce) == 16
            and hmac.compare_digest(signature, expected)
            and issued_at <= now <= expires_at
            and expires_at - issued_at == self._ttl_seconds
        )

    @staticmethod
    def _urlsafe_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _urlsafe_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
