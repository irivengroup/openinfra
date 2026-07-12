from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.runtime_config import (
    RuntimeConfigLoader,
    RuntimeDatabaseDsnResolver,
    RuntimeSecretResolver,
)


class TestRuntimeConfig:
    def test_loader_reads_quoted_environment_file(self, tmp_path: Path) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text(
            "# managed\n"
            'OPENINFRA_EDITION="enterprise"\n'
            'OPENINFRA_INSTALL_SECURITY_TRANSPORT="mtls"\n'
            'OPENINFRA_ESCAPED="a\\\\b\\"c"\n'
            "=ignored\n"
            "OPENINFRA_RAW=raw-value\n",
            encoding="utf-8",
        )

        loaded = RuntimeConfigLoader().load(config)

        assert loaded.source == config
        assert loaded.get("OPENINFRA_EDITION") == "enterprise"
        assert loaded.get("OPENINFRA_INSTALL_SECURITY_TRANSPORT") == "mtls"
        assert loaded.get("OPENINFRA_ESCAPED") == 'a\\b"c'
        assert loaded.get("OPENINFRA_RAW") == "raw-value"
        assert loaded.get("MISSING", "fallback") == "fallback"

    def test_loader_uses_runtime_override_and_candidate_paths(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        override = tmp_path / "missing.conf"
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(override))
        assert RuntimeConfigLoader().load().source is None

        monkeypatch.delenv("OPENINFRA_RUNTIME_CONFIG", raising=False)
        candidate = tmp_path / "candidate.conf"
        candidate.write_text('OPENINFRA_EDITION="pro"\n', encoding="utf-8")
        loader = RuntimeConfigLoader()
        monkeypatch.setattr(loader, "_candidate_paths", (candidate,))

        loaded = loader.load()

        assert loaded.source == candidate
        assert loaded.get("OPENINFRA_EDITION") == "pro"

    def test_loader_returns_empty_without_candidates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENINFRA_RUNTIME_CONFIG", raising=False)
        loader = RuntimeConfigLoader()
        monkeypatch.setattr(loader, "_candidate_paths", ())

        loaded = loader.load()

        assert loaded.source is None
        assert loaded.values == {}

    def test_database_dsn_resolver_prefers_explicit_environment_and_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text('OPENINFRA_DATABASE_DSN="postgresql:///from-config"\n', encoding="utf-8")
        monkeypatch.setenv("OPENINFRA_DATABASE_DSN", "postgresql:///from-env")
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(config))

        resolver = RuntimeDatabaseDsnResolver(loader=RuntimeConfigLoader())

        assert resolver.resolve("postgresql:///explicit") == "postgresql:///explicit"
        assert resolver.resolve() == "postgresql:///from-env"
        monkeypatch.delenv("OPENINFRA_DATABASE_DSN", raising=False)
        assert resolver.resolve() == "postgresql:///from-config"

    def test_database_dsn_resolver_uses_config_references(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text(
            'OPENINFRA_POSTGRES_USER_REF="env:OPENINFRA_POSTGRES_USER"\n'
            'OPENINFRA_POSTGRES_PASSWORD_REF="env:OPENINFRA_POSTGRES_PASSWORD"\n',
            encoding="utf-8",
        )
        monkeypatch.delenv("OPENINFRA_DATABASE_DSN", raising=False)
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(config))
        monkeypatch.setenv("OPENINFRA_POSTGRES_USER", "openinfra")
        monkeypatch.setenv("OPENINFRA_POSTGRES_PASSWORD", "secret:value")

        assert RuntimeDatabaseDsnResolver().resolve() == (
            "postgresql://openinfra:secret%3Avalue@127.0.0.1:5432/openinfra"
        )

    def test_database_dsn_resolver_uses_dsn_ref(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text(
            'OPENINFRA_DATABASE_DSN_REF="env:OPENINFRA_DATABASE_DSN_SECRET"\n',
            encoding="utf-8",
        )
        monkeypatch.delenv("OPENINFRA_DATABASE_DSN", raising=False)
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(config))
        monkeypatch.setenv("OPENINFRA_DATABASE_DSN_SECRET", "postgresql:///secret-ref")

        assert RuntimeDatabaseDsnResolver().resolve() == "postgresql:///secret-ref"

    def test_database_dsn_resolver_returns_empty_without_runtime_database_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text('OPENINFRA_EDITION="lite"\n', encoding="utf-8")
        monkeypatch.delenv("OPENINFRA_DATABASE_DSN", raising=False)
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(config))

        assert RuntimeDatabaseDsnResolver().resolve() == ""

    def test_secret_resolver_rejects_missing_or_unavailable_backends(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("file-secret\n", encoding="utf-8")
        resolver = RuntimeSecretResolver()
        monkeypatch.delenv("OPENINFRA_MISSING", raising=False)

        assert resolver.resolve("file://" + str(secret_file)) == "file-secret"
        assert resolver.resolve("literal") == "literal"
        assert resolver.resolve("") == ""
        with pytest.raises(ValidationError):
            resolver.resolve("env:OPENINFRA_MISSING")
        with pytest.raises(ValidationError):
            resolver.resolve("file://" + str(tmp_path / "missing.secret"))
        with pytest.raises(ValidationError):
            resolver.resolve("vault://secret/openinfra")

    def test_database_read_dsn_and_consistency_secret_resolution(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        config = tmp_path / "openinfra.conf"
        config.write_text(
            'OPENINFRA_DATABASE_READ_DSN_REF="env:OPENINFRA_READ_DSN_SECRET"\n'
            'OPENINFRA_READ_CONSISTENCY_SECRET_REF="env:OPENINFRA_CONSISTENCY_SECRET_REF"\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("OPENINFRA_RUNTIME_CONFIG", str(config))
        monkeypatch.setenv("OPENINFRA_READ_DSN_SECRET", "postgresql:///replica")
        monkeypatch.setenv("OPENINFRA_CONSISTENCY_SECRET_REF", "r" * 32)
        resolver = RuntimeDatabaseDsnResolver()
        assert resolver.resolve_read_replica() == "postgresql:///replica"
        assert resolver.resolve_consistency_secret() == "r" * 32

        monkeypatch.setenv("OPENINFRA_DATABASE_READ_DSN", "postgresql:///environment")
        monkeypatch.setenv("OPENINFRA_READ_CONSISTENCY_SECRET", "e" * 32)
        assert resolver.resolve_read_replica() == "postgresql:///environment"
        assert resolver.resolve_consistency_secret() == "e" * 32
        assert resolver.resolve_read_replica("postgresql:///explicit") == ("postgresql:///explicit")
        assert resolver.resolve_consistency_secret("x" * 32) == "x" * 32

        monkeypatch.delenv("OPENINFRA_READ_CONSISTENCY_SECRET", raising=False)
        config.write_text(
            'OPENINFRA_READ_CONSISTENCY_SECRET="' + "c" * 32 + '"\n',
            encoding="utf-8",
        )
        assert resolver.resolve_consistency_secret() == "c" * 32

        assert resolver.resolve_cursor_signing_secret() == "c" * 32
        monkeypatch.setenv("OPENINFRA_CURSOR_SIGNING_SECRET", "k" * 32)
        assert resolver.resolve_cursor_signing_secret() == "k" * 32
        assert resolver.resolve_cursor_signing_secret("z" * 32) == "z" * 32
