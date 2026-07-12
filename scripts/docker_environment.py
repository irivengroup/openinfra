from __future__ import annotations

import argparse
import os
import secrets
import stat
import subprocess
import sys
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


class EnvFileManager:
    _NONEMPTY_KEYS = frozenset(
        {
            "OPENINFRA_POSTGRES_PASSWORD",
            "OPENINFRA_POSTGRES_REPLICATION_PASSWORD",
            "OPENINFRA_READ_CONSISTENCY_SECRET",
            "OPENINFRA_BOOTSTRAP_TOKEN",
            "OPENINFRA_PGADMIN_PASSWORD",
            "OPENINFRA_GRAFANA_ADMIN_PASSWORD",
        }
    )

    def __init__(self, config: RuntimeEnvironmentConfig) -> None:
        self._config = config

    @staticmethod
    def _runtime_image_tag() -> str:
        version_file = Path(__file__).resolve().parents[1] / "VERSION"
        return version_file.read_text(encoding="utf-8").strip()

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
        changed = False
        for index, line in enumerate(lines):
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, current_value = line.split("=", 1)
            key = key.strip()
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
        normalized = "\n".join(lines) + "\n"
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
            "OPENINFRA_IMAGE_TAG": self._runtime_image_tag(),
            "OPENINFRA_BOOTSTRAP_TOKEN": "oi_" + secrets.token_urlsafe(48),
            "OPENINFRA_PGADMIN_EMAIL": "admin@openinfra.tld",
            "OPENINFRA_PGADMIN_PASSWORD": secrets.token_urlsafe(32),
            "OPENINFRA_PGADMIN_BIND": "127.0.0.1",
            "OPENINFRA_PGADMIN_PORT": "5050",
            "OPENINFRA_PGADMIN_IMAGE": "dpage/pgadmin4:latest",
            "OPENINFRA_WEB_BIND": "127.0.0.1",
            "OPENINFRA_WEB_PORT": "2006",
            "OPENINFRA_WEB_BACKEND_URL": "http://api:8080",
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL": "/api",
            "OPENINFRA_WEB_ALLOW_INSECURE_BACKEND": "true",
            "OPENINFRA_WEB_EDITION": "pro",
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
        command = ["docker", "compose", "--env-file", str(self._config.env_file), *args]
        completed = subprocess.run(command, check=False, cwd=self._config.project_root, text=True)
        if completed.returncode != 0:
            raise DockerEnvironmentError("command failed: " + " ".join(command))


class DockerRuntimeEnvironmentCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(prog="python scripts/docker_environment.py")
        parser.add_argument(
            "action",
            choices=("init", "up", "validate", "status", "down", "reset"),
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
        if action in {"up", "validate", "status", "down", "reset"}:
            env_manager.ensure()
        if action == "up":
            runner.run(
                [
                    "up",
                    "--build",
                    "-d",
                    "postgres",
                    "migrate",
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
        if action == "down":
            runner.run(["down"])
            return
        if action == "reset":
            runner.run(["down", "--volumes", "--remove-orphans"])
            return
        raise DockerEnvironmentError("unsupported action: " + action)


if __name__ == "__main__":
    raise SystemExit(DockerRuntimeEnvironmentCli.main())
