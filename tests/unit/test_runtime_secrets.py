from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from openinfra.infrastructure.runtime_secrets import (
    RuntimeBootstrapTokenStore,
    RuntimeSecretError,
)


class TestRuntimeBootstrapTokenStore:
    def _store(self, path: Path) -> RuntimeBootstrapTokenStore:
        return RuntimeBootstrapTokenStore(
            path=path,
            owner_uid=os.getuid(),
            owner_gid=os.getgid(),
        )

    def test_ensure_creates_private_idempotent_token(self, tmp_path: Path) -> None:
        token_path = tmp_path / "runtime" / "secrets" / "bootstrap-token"
        store = self._store(token_path)

        first_path = store.ensure()
        first_token = store.read()
        second_path = store.ensure()
        second_token = store.read()

        assert first_path == token_path
        assert second_path == token_path
        assert first_token == second_token
        assert first_token.startswith("oi_")
        assert len(first_token) >= 46
        assert stat.S_IMODE(token_path.stat().st_mode) == 0o400
        assert stat.S_IMODE(token_path.parent.stat().st_mode) == 0o700

    def test_rotate_replaces_token_atomically(self, tmp_path: Path) -> None:
        token_path = tmp_path / "secrets" / "bootstrap-token"
        store = self._store(token_path)
        store.ensure()
        initial_token = store.read()
        initial_inode = token_path.stat().st_ino

        store.rotate()

        assert store.read() != initial_token
        assert token_path.stat().st_ino != initial_inode
        assert stat.S_IMODE(token_path.stat().st_mode) == 0o400
        assert list(token_path.parent.glob(".bootstrap-token-*")) == []

    def test_ensure_repairs_permissions_without_rotating(self, tmp_path: Path) -> None:
        token_path = tmp_path / "bootstrap-token"
        store = self._store(token_path)
        store.ensure()
        token = store.read()
        token_path.chmod(0o666)

        store.ensure()

        assert store.read() == token
        assert stat.S_IMODE(token_path.stat().st_mode) == 0o400

    def test_read_rejects_group_or_world_access(self, tmp_path: Path) -> None:
        token_path = tmp_path / "bootstrap-token"
        store = self._store(token_path)
        store.ensure()
        token_path.chmod(0o440)

        with pytest.raises(RuntimeSecretError, match="must not grant group or other access"):
            store.read()

        store.ensure()
        assert stat.S_IMODE(token_path.stat().st_mode) == 0o400

    def test_read_rejects_symlink_and_invalid_payload(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.write_text("oi_" + "a" * 64 + "\n", encoding="utf-8")
        symlink = tmp_path / "bootstrap-token"
        symlink.symlink_to(target)

        with pytest.raises(RuntimeSecretError, match="must not be a symlink"):
            self._store(symlink).read()

        symlink.unlink()
        symlink.write_text("invalid\n", encoding="utf-8")
        symlink.chmod(0o400)
        with pytest.raises(RuntimeSecretError, match="invalid format"):
            self._store(symlink).read()
