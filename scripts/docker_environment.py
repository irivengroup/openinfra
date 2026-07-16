from __future__ import annotations

import argparse
import os
import re
import secrets
import stat

# Docker is invoked with a fixed argv list; shell execution is never used.
import subprocess  # nosec B404
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


class DockerEnvironmentError(Exception):
    """Raised when Docker runtime orchestration fails."""


@dataclass(frozen=True, slots=True)
class RuntimeEnvironmentConfig:
    project_root: Path
    env_file: Path

    @classmethod
    def from_current_directory(cls) -> RuntimeEnvironmentConfig:
        project_root = Path.cwd()
        return cls(project_root=project_root, env_file=project_root / ".env")


@dataclass(frozen=True, slots=True)
class RuntimeManagedConfiguration:
    project_root: Path

    _VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[a-zA-Z0-9.+-]*)?$")
    _RUNTIME_IMAGE_SERVICES = (
        "migrate",
        "runtime-secrets",
        "auth-bootstrap",
        "api",
        "web",
        "smoke",
    )

    def image_tag(self) -> str:
        version_file = self.project_root / "VERSION"
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise DockerEnvironmentError(
                f"cannot read runtime version from {version_file}"
            ) from exc
        if not version or self._VERSION_PATTERN.fullmatch(version) is None:
            raise DockerEnvironmentError(f"invalid runtime version in {version_file}: {version!r}")
        return version

    def runtime_image(self) -> str:
        return f"openinfra/runtime:{self.image_tag()}"

    def compose_override_payload(self) -> str:
        image = self.runtime_image()
        lines = ["services:"]
        for service in self._RUNTIME_IMAGE_SERVICES:
            lines.extend((f"  {service}:", f"    image: {image}"))
        return "\n".join(lines) + "\n"

    @contextmanager
    def compose_override_file(self) -> Iterator[Path]:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="openinfra-runtime-",
            suffix=".compose.yaml",
            delete=False,
        ) as handle:
            handle.write(self.compose_override_payload())
            override_path = Path(handle.name)
        try:
            os.chmod(override_path, 0o600)
            yield override_path
        finally:
            override_path.unlink(missing_ok=True)


class EnvFileManager:
    _INTERNALLY_MANAGED_KEYS = frozenset(
        {
            "OPENINFRA_IMAGE_TAG",
            "OPENINFRA_WEB_EDITION",
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL",
            "OPENINFRA_BOOTSTRAP_TOKEN",
        }
    )
    _NONEMPTY_KEYS = frozenset(
        {
            "OPENINFRA_POSTGRES_PASSWORD",
            "OPENINFRA_POSTGRES_REPLICATION_PASSWORD",
            "OPENINFRA_READ_CONSISTENCY_SECRET",
            "OPENINFRA_PGADMIN_PASSWORD",
            "OPENINFRA_GRAFANA_ADMIN_PASSWORD",
        }
    )

    def __init__(self, config: RuntimeEnvironmentConfig) -> None:
        self._config = config

    def ensure(self) -> Path:
        if self._config.env_file.exists():
            self._upgrade_existing_file()
            self._assert_private_permissions()
            return self._config.env_file
        values = self._required_values()
        payload = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(self._config.env_file, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        self._assert_private_permissions()
        return self._config.env_file

    def _upgrade_existing_file(self) -> None:
        payload = self._config.env_file.read_text(encoding="utf-8")
        lines = payload.splitlines()
        required = self._required_values()
        existing_keys: set[str] = set()
        removed_indices: set[int] = set()
        changed = False
        for index, line in enumerate(lines):
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, current_value = line.split("=", 1)
            key = key.strip()
            if key in self._INTERNALLY_MANAGED_KEYS:
                removed_indices.add(index)
                changed = True
                continue
            existing_keys.add(key)
            if key in self._NONEMPTY_KEYS and not current_value.strip():
                lines[index] = f"{key}={required[key]}"
                changed = True
        for key, value in required.items():
            if key not in existing_keys:
                lines.append(f"{key}={value}")
                changed = True
        if not changed:
            return
        normalized = (
            "\n".join(line for index, line in enumerate(lines) if index not in removed_indices)
            + "\n"
        )
        temporary = self._config.env_file.with_suffix(self._config.env_file.suffix + ".tmp")
        temporary.write_text(normalized, encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self._config.env_file)

    def _required_values(self) -> dict[str, str]:
        return {
            "OPENINFRA_POSTGRES_DB": "openinfra",
            "OPENINFRA_POSTGRES_USER": "openinfra",
            "OPENINFRA_POSTGRES_PASSWORD": secrets.token_urlsafe(32),
            "OPENINFRA_POSTGRES_REPLICATION_USER": "openinfra_replica",
            "OPENINFRA_POSTGRES_REPLICATION_PASSWORD": secrets.token_urlsafe(32),
            "OPENINFRA_READ_CONSISTENCY_SECRET": secrets.token_urlsafe(48),
            "OPENINFRA_API_BIND": "127.0.0.1",
            "OPENINFRA_API_PORT": "8080",
            "OPENINFRA_PGADMIN_EMAIL": "admin@openinfra.tld",
            "OPENINFRA_PGADMIN_PASSWORD": secrets.token_urlsafe(32),
            "OPENINFRA_PGADMIN_BIND": "127.0.0.1",
            "OPENINFRA_PGADMIN_PORT": "5050",
            "OPENINFRA_PGADMIN_IMAGE": "dpage/pgadmin4:latest",
            "OPENINFRA_WEB_BIND": "127.0.0.1",
            "OPENINFRA_WEB_PORT": "2006",
            "OPENINFRA_WEB_BACKEND_URL": "http://api:8080",
            "OPENINFRA_WEB_ALLOW_INSECURE_BACKEND": "true",
            "OPENINFRA_WEB_AUTH_MODE": "standard",
            "OPENINFRA_OTEL_ENABLED": "false",
            "OPENINFRA_GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(32),
        }

    def _assert_private_permissions(self) -> None:
        mode = stat.S_IMODE(self._config.env_file.stat().st_mode)
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            os.chmod(self._config.env_file, 0o600)


class ComposeCommandRunner:
    def __init__(self, config: RuntimeEnvironmentConfig) -> None:
        self._config = config

    def run(self, args: list[str]) -> None:
        managed = RuntimeManagedConfiguration(self._config.project_root)
        with managed.compose_override_file() as override_file:
            command = [
                "docker",
                "compose",
                "--env-file",
                str(self._config.env_file),
                "-f",
                str(self._config.project_root / "compose.yaml"),
                "-f",
                str(override_file),
                *args,
            ]
            # The executable and argument structure are fixed; no shell interpolation occurs.
            try:
                completed = subprocess.run(  # nosec B603
                    command,
                    check=False,
                    cwd=self._config.project_root,
                    text=True,
                )
            except OSError as exc:
                raise DockerEnvironmentError(
                    "cannot execute Docker Compose: " + " ".join(command[:2])
                ) from exc
        if completed.returncode != 0:
            raise DockerEnvironmentError("command failed: " + " ".join(command))


class DockerRuntimeEnvironmentCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(prog="python scripts/docker_environment.py")
        parser.add_argument(
            "action",
            choices=(
                "init",
                "up",
                "validate",
                "status",
                "bootstrap-token",
                "down",
                "reset",
            ),
            help="manage the OpenInfra runtime validation environment",
        )
        args = parser.parse_args(sys.argv[1:])
        try:
            cls().run(str(args.action))
        except DockerEnvironmentError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    def run(self, action: str) -> None:
        config = RuntimeEnvironmentConfig.from_current_directory()
        env_manager = EnvFileManager(config)
        runner = ComposeCommandRunner(config)
        if action == "init":
            env_path = env_manager.ensure()
            print(f"runtime environment file ready: {env_path}")
            return
        if action in {
            "up",
            "validate",
            "status",
            "bootstrap-token",
            "down",
            "reset",
        }:
            env_manager.ensure()
        if action == "up":
            runner.run(
                [
                    "up",
                    "--build",
                    "-d",
                    "postgres",
                    "migrate",
                    "runtime-secrets",
                    "auth-bootstrap",
                    "api",
                    "web",
                    "pgadmin",
                ]
            )
            return
        if action == "validate":
            runner.run(
                [
                    "--profile",
                    "validation",
                    "up",
                    "--build",
                    "--abort-on-container-exit",
                    "--exit-code-from",
                    "smoke",
                    "smoke",
                ]
            )
            return
        if action == "status":
            runner.run(["ps"])
            return
        if action == "bootstrap-token":
            runner.run(
                [
                    "run",
                    "--rm",
                    "--no-deps",
                    "runtime-secrets",
                    "openinfra-runtime-secrets",
                    "get",
                    "--path",
                    "/run/openinfra/secrets/bootstrap-token",
                    "--uid",
                    "10001",
                    "--gid",
                    "10001",
                ]
            )
            return
        if action == "down":
            runner.run(["down"])
            return
        if action == "reset":
            runner.run(["down", "--volumes", "--remove-orphans"])
            return
        raise DockerEnvironmentError("unsupported action: " + action)


if __name__ == "__main__":
    raise SystemExit(DockerRuntimeEnvironmentCli.main())
