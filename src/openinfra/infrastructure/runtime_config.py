from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from openinfra.domain.common import ValidationError


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    values: dict[str, str]
    source: Path | None

    def get(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)


class RuntimeConfigLoader:
    _candidate_paths = (
        Path("/etc/openinfra/openinfra.conf"),
        Path("/opt/openinfra/config/openinfra.conf"),
    )

    def load(self, explicit_path: Path | None = None) -> RuntimeConfig:
        path = explicit_path or self._first_existing_config()
        if path is None:
            return RuntimeConfig({}, None)
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            normalized_key = key.strip()
            if not normalized_key:
                continue
            values[normalized_key] = self._unquote(value.strip())
        return RuntimeConfig(values, path)

    def _first_existing_config(self) -> Path | None:
        override = os.environ.get("OPENINFRA_RUNTIME_CONFIG", "").strip()
        if override:
            path = Path(override)
            return path if path.is_file() else None
        for path in self._candidate_paths:
            if path.is_file():
                return path
        return None

    def _unquote(self, value: str) -> str:
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            payload = value[1:-1]
            return payload.replace('\\"', '"').replace("\\\\", "\\")
        return value


class RuntimeSecretResolver:
    def resolve(self, reference: str) -> str:
        normalized = reference.strip()
        if not normalized:
            return ""
        if normalized.startswith("env:"):
            name = normalized.removeprefix("env:").strip()
            value = os.environ.get(name, "")
            if not value:
                raise ValidationError("missing environment secret reference: " + name)
            return value
        if normalized.startswith("file://"):
            path = Path(normalized.removeprefix("file://"))
            if not path.is_file():
                raise ValidationError("missing file secret reference: " + str(path))
            return path.read_text(encoding="utf-8").strip()
        if normalized.startswith(("vault://", "sops://", "kms://")):
            raise ValidationError(
                "runtime secret backend is not available in this process: "
                + normalized.split(":", 1)[0]
            )
        return normalized


class RuntimeDatabaseDsnResolver:
    def __init__(
        self,
        loader: RuntimeConfigLoader | None = None,
        secret_resolver: RuntimeSecretResolver | None = None,
    ) -> None:
        self._loader = loader or RuntimeConfigLoader()
        self._secret_resolver = secret_resolver or RuntimeSecretResolver()

    def resolve(self, explicit_dsn: str | None = None) -> str:
        direct = self._resolve_named_dsn(
            explicit_dsn,
            direct_key="OPENINFRA_DATABASE_DSN",
            reference_key="OPENINFRA_DATABASE_DSN_REF",
        )
        if direct:
            return direct
        runtime = self._loader.load()
        user_ref = runtime.get("OPENINFRA_POSTGRES_USER_REF")
        password_ref = runtime.get("OPENINFRA_POSTGRES_PASSWORD_REF")
        if user_ref and password_ref:
            username = self._secret_resolver.resolve(user_ref)
            credential = self._secret_resolver.resolve(password_ref)
            return (
                "postgresql://"
                + quote(username, safe="")
                + ":"
                + quote(credential, safe="")
                + "@127.0.0.1:5432/openinfra"
            )
        return ""

    def resolve_read_replica(self, explicit_dsn: str | None = None) -> str:
        return self._resolve_named_dsn(
            explicit_dsn,
            direct_key="OPENINFRA_DATABASE_READ_DSN",
            reference_key="OPENINFRA_DATABASE_READ_DSN_REF",
        )

    def resolve_consistency_secret(self, explicit_secret: str | None = None) -> str:
        direct = (explicit_secret or "").strip() or os.environ.get(
            "OPENINFRA_READ_CONSISTENCY_SECRET", ""
        ).strip()
        if direct:
            return direct
        runtime = self._loader.load()
        configured = runtime.get("OPENINFRA_READ_CONSISTENCY_SECRET")
        if configured:
            return configured
        reference = runtime.get("OPENINFRA_READ_CONSISTENCY_SECRET_REF")
        return self._secret_resolver.resolve(reference) if reference else ""

    def _resolve_named_dsn(
        self,
        explicit_dsn: str | None,
        *,
        direct_key: str,
        reference_key: str,
    ) -> str:
        direct = (explicit_dsn or "").strip() or os.environ.get(direct_key, "").strip()
        if direct:
            return direct
        runtime = self._loader.load()
        configured_direct = runtime.get(direct_key)
        if configured_direct:
            return configured_direct
        dsn_ref = runtime.get(reference_key)
        return self._secret_resolver.resolve(dsn_ref) if dsn_ref else ""
