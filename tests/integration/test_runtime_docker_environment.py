from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


class TestRuntimeEnvironment:
    def test_native_runtime_assets_are_present_and_hardened(self) -> None:
        unit = Path("deploy/systemd/openinfra-api.service").read_text(encoding="utf-8")
        runbook = Path("docs/runbooks/RUNTIME_NATIVE.md").read_text(encoding="utf-8")
        smoke = subprocess.run(
            [sys.executable, "scripts/native_runtime_smoke.py", "--project-root", "."],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(smoke.stdout)

        assert "ExecStart=/opt/openinfra/venv/bin/openinfra-api" in unit
        assert "User=openinfra" in unit
        assert "NoNewPrivileges=true" in unit
        assert "ProtectSystem=strict" in unit
        assert "OPENINFRA_DATABASE_DSN" in runbook
        assert "Docker ne fait pas partie de la chaine d'execution production" in runbook
        assert payload["assets"]["systemd_unit"].endswith("deploy/systemd/openinfra-api.service")

    def test_optional_docker_assets_remain_test_only(self) -> None:
        compose = Path("compose.yaml").read_text(encoding="utf-8")
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        env_example = Path(".env.example").read_text(encoding="utf-8")
        smoke = Path("docker/openinfra-runtime-smoke.py").read_text(encoding="utf-8")
        runbook = Path("docs/runbooks/RUNTIME_DOCKER.md").read_text(encoding="utf-8")

        assert "postgres:" in compose
        assert "migrate:" in compose
        assert "api:" in compose
        assert "smoke:" in compose
        assert "service_healthy" in compose
        assert "service_completed_successfully" in compose
        assert "USER openinfra" in dockerfile
        assert "OPENINFRA_POSTGRES_PASSWORD=" in env_example
        assert "openinfra" in compose
        assert "apply-migrations" in compose
        assert "psql" not in compose
        assert "/ready" in smoke
        assert "/api/v1/database/schema" in smoke
        assert "openinfra" in smoke
        assert "production" in runbook.lower()

    def test_runtime_env_manager_creates_private_env_file(self, tmp_path: Path) -> None:
        module_path = Path("scripts/docker_environment.py")
        spec = importlib.util.spec_from_file_location("docker_environment", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["docker_environment"] = module
        spec.loader.exec_module(module)

        config = module.RuntimeEnvironmentConfig(project_root=tmp_path, env_file=tmp_path / ".env")
        env_path = module.EnvFileManager(config).ensure()
        mode = stat.S_IMODE(env_path.stat().st_mode)
        payload = env_path.read_text(encoding="utf-8")

        assert mode == 0o600
        assert "OPENINFRA_POSTGRES_PASSWORD=" in payload
        assert "replace-with" not in payload
        assert os.linesep in payload
