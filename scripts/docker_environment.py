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
    def __init__(self, config: RuntimeEnvironmentConfig) -> None:
        self._config = config

    def ensure(self) -> Path:
        if self._config.env_file.exists():
            self._assert_private_permissions()
            return self._config.env_file
        password = secrets.token_urlsafe(32)
        pgadmin_password = secrets.token_urlsafe(32)
        bootstrap_token = "oi_" + secrets.token_urlsafe(48)
        payload = "\n".join(
            (
                "OPENINFRA_POSTGRES_DB=openinfra",
                "OPENINFRA_POSTGRES_USER=openinfra",
                f"OPENINFRA_POSTGRES_PASSWORD={password}",
                "OPENINFRA_API_BIND=127.0.0.1",
                "OPENINFRA_API_PORT=8080",
                "OPENINFRA_IMAGE_TAG=0.24.0",
                f"OPENINFRA_BOOTSTRAP_TOKEN={bootstrap_token}",
                "OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld",
                f"OPENINFRA_PGADMIN_PASSWORD={pgadmin_password}",
                "OPENINFRA_PGADMIN_BIND=127.0.0.1",
                "OPENINFRA_PGADMIN_PORT=5050",
                "OPENINFRA_PGADMIN_IMAGE=dpage/pgadmin4:latest",
                "",
            )
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(self._config.env_file, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        self._assert_private_permissions()
        return self._config.env_file

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
                ["up", "--build", "-d", "postgres", "migrate", "auth-bootstrap", "api", "pgadmin"]
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
