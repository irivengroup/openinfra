from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path


class TestRuntimeDockerEnvironment:
    def test_runtime_docker_assets_are_present_and_securely_configured(self) -> None:
        compose = Path("compose.yaml").read_text(encoding="utf-8")
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        env_example = Path(".env.example").read_text(encoding="utf-8")
        smoke = Path("docker/openinfra-runtime-smoke.py").read_text(encoding="utf-8")

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
