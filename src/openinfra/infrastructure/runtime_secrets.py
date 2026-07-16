from __future__ import annotations

import argparse
import os
import re
import secrets
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from openinfra.domain.common import OpenInfraError


class RuntimeSecretError(OpenInfraError):
    """Raised when a runtime secret cannot be created, validated or read safely."""


@dataclass(frozen=True, slots=True)
class RuntimeBootstrapTokenStore:
    path: Path
    owner_uid: int = 10001
    owner_gid: int = 10001

    _TOKEN_PATTERN = re.compile(r"^oi_[A-Za-z0-9_-]{43,}$")

    def ensure(self) -> Path:
        self._prepare_parent()
        if self.path.exists() or self.path.is_symlink():
            self.read(require_private=False)
            self._secure_existing_file()
            return self.path
        self._write_atomic(self._generate())
        return self.path

    def rotate(self) -> Path:
        self._prepare_parent()
        self._write_atomic(self._generate())
        return self.path

    def read(self, *, require_private: bool = True) -> str:
        if self.path.is_symlink():
            raise RuntimeSecretError(f"runtime secret path must not be a symlink: {self.path}")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags)
        except OSError as exc:
            raise RuntimeSecretError(f"cannot open runtime bootstrap token: {self.path}") from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeSecretError(
                    f"runtime bootstrap token must be a regular file: {self.path}"
                )
            if require_private and stat.S_IMODE(metadata.st_mode) & 0o077:
                raise RuntimeSecretError(
                    "runtime bootstrap token permissions must not grant group or other access: "
                    + str(self.path)
                )
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                descriptor = -1
                payload = handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        token = payload.strip()
        if self._TOKEN_PATTERN.fullmatch(token) is None:
            raise RuntimeSecretError("runtime bootstrap token has an invalid format")
        return token

    def _prepare_parent(self) -> None:
        parent = self.path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if parent.is_symlink() or not parent.is_dir():
            raise RuntimeSecretError(f"runtime secret directory is invalid: {parent}")
        parent.chmod(0o700)

    def _secure_existing_file(self) -> None:
        self.path.chmod(0o400)
        self._apply_owner()

    def _write_atomic(self, token: str) -> None:
        temporary_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".bootstrap-token-",
            dir=self.path.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(temporary_descriptor, 0o600)
            with os.fdopen(temporary_descriptor, "w", encoding="utf-8") as handle:
                temporary_descriptor = -1
                handle.write(token + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.chmod(0o400)
            self._apply_owner(temporary_path)
            temporary_path.replace(self.path)
            self._fsync_parent()
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        finally:
            if temporary_descriptor >= 0:
                os.close(temporary_descriptor)

    def _apply_owner(self, path: Path | None = None) -> None:
        target = path or self.path
        try:
            os.chown(target, self.owner_uid, self.owner_gid)
        except PermissionError as exc:
            current = target.stat()
            if current.st_uid != self.owner_uid or current.st_gid != self.owner_gid:
                raise RuntimeSecretError(
                    f"cannot assign runtime secret ownership {self.owner_uid}:{self.owner_gid}"
                ) from exc

    def _fsync_parent(self) -> None:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        descriptor = os.open(self.path.parent, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _generate() -> str:
        return "oi_" + secrets.token_urlsafe(48)


class RuntimeSecretsCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-runtime-secrets")
        parser.add_argument("action", choices=("ensure", "rotate", "show", "get"))
        parser.add_argument(
            "--path",
            type=Path,
            default=Path("/run/openinfra/secrets/bootstrap-token"),
        )
        parser.add_argument("--uid", type=int, default=10001)
        parser.add_argument("--gid", type=int, default=10001)
        namespace = parser.parse_args()
        store = RuntimeBootstrapTokenStore(
            path=namespace.path,
            owner_uid=namespace.uid,
            owner_gid=namespace.gid,
        )
        try:
            if namespace.action == "ensure":
                store.ensure()
                sys.stdout.write(f"runtime bootstrap token ready: {store.path}\n")
                return 0
            if namespace.action == "rotate":
                store.rotate()
                sys.stdout.write(f"runtime bootstrap token rotated: {store.path}\n")
                return 0
            if namespace.action == "get":
                store.ensure()
            sys.stdout.write(store.read() + "\n")
            return 0
        except RuntimeSecretError as exc:
            sys.stderr.write(str(exc) + "\n")
            return 1


if __name__ == "__main__":
    raise SystemExit(RuntimeSecretsCli.main())
