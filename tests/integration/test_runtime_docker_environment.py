from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml


class TestRuntimeEnvironment:
    def test_native_runtime_assets_are_present_and_hardened(self) -> None:
        runbook = Path("docs/runbooks/RUNTIME_NATIVE.md").read_text(encoding="utf-8")
        smoke = subprocess.run(
            [sys.executable, "scripts/native_runtime_smoke.py", "--project-root", "."],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(smoke.stdout)
        from openinfra.infrastructure.installer_config import InstallerConfigValidator

        validator = InstallerConfigValidator()
        backend_unit = validator.render_systemd_unit("enterprise", "server")
        web_unit = validator.render_systemd_unit("pro", "web")
        agent_unit = validator.render_systemd_unit("enterprise", "agent")

        assert not Path("deploy").exists()
        assert "ExecStart=/opt/openinfra/venv/bin/openinfra-api" in backend_unit
        assert "ExecStart=/opt/openinfra/venv/bin/openinfra-web" in web_unit
        assert "User=openinfra" in backend_unit
        assert "NoNewPrivileges=true" in backend_unit
        assert "ProtectSystem=strict" in backend_unit
        assert "PrivateDevices=true" in backend_unit
        assert "ProtectKernelTunables=true" in backend_unit
        assert "RestrictSUIDSGID=true" in backend_unit
        assert "openinfra database apply-migrations" not in backend_unit
        assert "openinfra-web.service" in web_unit
        assert "openinfra-agent.service" in agent_unit
        assert "OPENINFRA_DATABASE_DSN" in runbook
        assert "Docker ne fait pas partie de la chaine d'execution production" in runbook
        assert payload["assets"]["rendered_units"] == [
            "openinfra.service",
            "openinfra-web.service",
            "openinfra-agent.service",
        ]

    def test_optional_docker_assets_remain_test_only(self) -> None:
        compose = Path("compose.yaml").read_text(encoding="utf-8")
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        env_example = Path(".env.example").read_text(encoding="utf-8")
        smoke = Path("docker/openinfra-runtime-smoke.py").read_text(encoding="utf-8")
        runbook = Path("docs/runbooks/RUNTIME_DOCKER.md").read_text(encoding="utf-8")
        current_version = Path("VERSION").read_text(encoding="utf-8").strip()

        assert "postgres:" in compose
        assert "migrate:" in compose
        assert "api:" in compose
        assert "smoke:" in compose
        assert "pgadmin:" in compose
        assert "web:" in compose
        assert "openinfra-web" in compose
        assert "service_healthy" in compose
        assert "service_completed_successfully" in compose
        assert "USER openinfra" in dockerfile
        assert "HEALTHCHECK" not in dockerfile
        assert "OPENINFRA_POSTGRES_PASSWORD=" in env_example
        assert "OPENINFRA_IMAGE_TAG=" not in env_example
        assert "OPENINFRA_WEB_EDITION=" not in env_example
        assert "OPENINFRA_WEB_PUBLIC_API_BASE_URL=" not in env_example
        assert "OPENINFRA_BOOTSTRAP_TOKEN=" not in env_example
        assert "OPENINFRA_PGADMIN_EMAIL=" in env_example
        assert "OPENINFRA_PGADMIN_PASSWORD=" in env_example
        assert "OPENINFRA_PGADMIN_PORT=5050" in env_example
        assert "OPENINFRA_WEB_PORT=2006" in env_example
        assert "OPENINFRA_WEB_BACKEND_URL=http://api:8080" in env_example
        assert "OPENINFRA_BOOTSTRAP_TOKEN" not in compose
        assert "  runtime-secrets:" in compose
        assert "openinfra-runtime-secrets" in compose
        assert "--token-file" in compose
        assert "--backend-bearer-token-file" in compose
        assert compose.count("openinfra-runtime-secrets:/run/openinfra/secrets:ro") == 3
        assert f"openinfra/runtime:{current_version}" in compose
        assert "OPENINFRA_IMAGE_TAG" not in compose
        assert "${OPENINFRA_PGADMIN_IMAGE:-dpage/pgadmin4:latest}" in compose
        assert "openinfra-pgadmin-data:/var/lib/pgadmin" in compose
        assert "${OPENINFRA_WEB_BIND:-127.0.0.1}:${OPENINFRA_WEB_PORT:-2006}:2006" in compose
        assert "./docker/pgadmin/servers.json:/pgadmin4/servers.json:ro" in compose
        assert "${OPENINFRA_PGADMIN_BIND:-127.0.0.1}:${OPENINFRA_PGADMIN_PORT:-5050}:80" in compose
        assert "openinfra/runtime:${OPENINFRA_IMAGE_TAG:-0.14.0}" not in compose
        assert "openinfra" in compose
        assert "apply-migrations" in compose
        assert "psql" not in compose
        assert "/ready" in smoke
        assert "OPENINFRA_WEB_BASE_URL" in smoke
        assert "/config.json" in smoke
        assert "/" in smoke
        assert "/api/v1" in smoke
        assert "/api/v1/database/schema" in smoke
        assert 'version.get("version") != __version__' in smoke
        assert 'version.get("version") != "0.17.6"' not in smoke
        servers = Path("docker/pgadmin/servers.json").read_text(encoding="utf-8")
        assert "OpenInfra PostgreSQL" in servers
        assert '"Host": "postgres"' in servers
        assert '"MaintenanceDB": "openinfra"' in servers
        assert "openinfra" in smoke
        assert "production" in runbook.lower()
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "Dynamic Docker, Web and bootstrap secret regression" in workflow
        assert "test_compose_runner_generates_runtime_image_override_from_version" in workflow
        assert "test_config_factory_reads_internally_managed_bootstrap_token_file" in workflow

    def test_docker_build_context_contains_all_forced_wheel_resources(self) -> None:
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        build_section = dockerfile.split("RUN python -m pip install", maxsplit=1)[0]
        copied_sources = []
        for line in build_section.splitlines():
            stripped = line.strip()
            if not stripped.startswith("COPY "):
                continue
            tokens = stripped.split()
            copied_sources.extend(Path(token) for token in tokens[1:-1])

        configuration = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        forced = configuration["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
        missing = []
        for source in forced:
            source_path = Path(source)
            if not any(
                source_path == copied or copied in source_path.parents for copied in copied_sources
            ):
                missing.append(source)

        assert missing == []
        assert "COPY docs/ga ./docs/ga" in dockerfile
        assert "COPY docs/release ./docs/release" in dockerfile
        assert "COPY docs/runbooks ./docs/runbooks" in dockerfile

    def test_minimal_docker_context_can_build_runtime_wheel(self, tmp_path: Path) -> None:
        project_root = Path.cwd()
        staging = tmp_path / "docker-context"
        staging.mkdir()
        for file_name in ("pyproject.toml", "README.md", "LICENSE", "VERSION"):
            shutil.copy2(project_root / file_name, staging / file_name)
        for directory in ("src", "installers", "web"):
            shutil.copytree(project_root / directory, staging / directory)
        for directory in ("api", "ga", "release", "runbooks"):
            shutil.copytree(project_root / "docs" / directory, staging / "docs" / directory)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(tmp_path / "wheelhouse"),
            ],
            cwd=staging,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert list((tmp_path / "wheelhouse").glob("openinfra-0.33.12-*.whl"))

    def test_all_runtime_services_share_the_local_image_build(self) -> None:
        compose = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))
        expected_build = {"context": ".", "dockerfile": "Dockerfile"}
        for service_name in (
            "migrate",
            "runtime-secrets",
            "auth-bootstrap",
            "api",
            "web",
            "smoke",
        ):
            service = compose["services"][service_name]
            assert service["build"] == expected_build
            assert service["image"] == "openinfra/runtime:0.33.12"
            assert service["pull_policy"] == "build"

    def test_runtime_user_matches_prometheus_tmpfs_owner(self) -> None:
        dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
        compose = Path("compose.yaml").read_text(encoding="utf-8")

        assert "ARG OPENINFRA_UID=10001" in dockerfile
        assert "ARG OPENINFRA_GID=10001" in dockerfile
        assert 'groupadd --gid "${OPENINFRA_GID}" openinfra' in dockerfile
        assert 'useradd --uid "${OPENINFRA_UID}" --gid openinfra' in dockerfile
        prometheus_tmpfs = "/tmp/openinfra-prometheus:mode=0770,uid=10001,gid=10001"  # noqa: S108
        assert compose.count(prometheus_tmpfs) == 2

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
        assert "OPENINFRA_POSTGRES_REPLICATION_PASSWORD=" in payload
        assert "OPENINFRA_READ_CONSISTENCY_SECRET=" in payload
        assert "OPENINFRA_GRAFANA_ADMIN_PASSWORD=" in payload
        assert "OPENINFRA_IMAGE_TAG=" not in payload
        assert "OPENINFRA_WEB_EDITION=" not in payload
        assert "OPENINFRA_WEB_PUBLIC_API_BASE_URL=" not in payload
        assert "OPENINFRA_BOOTSTRAP_TOKEN=" not in payload
        assert "OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld" in payload
        assert "admin@openinfra.local" not in payload
        assert "OPENINFRA_PGADMIN_PASSWORD=" in payload
        assert "OPENINFRA_PGADMIN_IMAGE=dpage/pgadmin4:latest" in payload
        assert "OPENINFRA_WEB_BIND=127.0.0.1" in payload
        assert "OPENINFRA_WEB_BACKEND_URL=http://api:8080" in payload
        assert "replace-with" not in payload
        assert os.linesep in payload

    def test_runtime_env_manager_upgrades_missing_and_blank_required_secrets(
        self, tmp_path: Path
    ) -> None:
        module_path = Path("scripts/docker_environment.py")
        spec = importlib.util.spec_from_file_location("docker_environment_upgrade", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["docker_environment_upgrade"] = module
        spec.loader.exec_module(module)
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENINFRA_POSTGRES_PASSWORD=preserved\n"
            "OPENINFRA_POSTGRES_REPLICATION_PASSWORD=\n"
            "OPENINFRA_READ_CONSISTENCY_SECRET=\n"
            "OPENINFRA_IMAGE_TAG=stale\n"
            "OPENINFRA_WEB_EDITION=enterprise\n"
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL=https://legacy.example/api\n"
            "OPENINFRA_BOOTSTRAP_TOKEN=legacy-bootstrap-token\n",
            encoding="utf-8",
        )
        env_file.chmod(0o644)
        config = module.RuntimeEnvironmentConfig(project_root=tmp_path, env_file=env_file)

        module.EnvFileManager(config).ensure()
        first_payload = env_file.read_text(encoding="utf-8")
        module.EnvFileManager(config).ensure()
        second_payload = env_file.read_text(encoding="utf-8")

        values = dict(
            line.split("=", 1)
            for line in first_payload.splitlines()
            if line and not line.startswith("#")
        )
        assert values["OPENINFRA_POSTGRES_PASSWORD"] == "preserved"
        assert values["OPENINFRA_POSTGRES_REPLICATION_PASSWORD"]
        assert values["OPENINFRA_READ_CONSISTENCY_SECRET"]
        assert values["OPENINFRA_GRAFANA_ADMIN_PASSWORD"]
        assert "OPENINFRA_IMAGE_TAG" not in values
        assert "OPENINFRA_WEB_EDITION" not in values
        assert "OPENINFRA_WEB_PUBLIC_API_BASE_URL" not in values
        assert "OPENINFRA_BOOTSTRAP_TOKEN" not in values
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
        assert second_payload == first_payload

    def test_compose_runner_generates_runtime_image_override_from_version(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        module_path = Path("scripts/docker_environment.py")
        spec = importlib.util.spec_from_file_location("docker_environment_runner", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["docker_environment_runner"] = module
        spec.loader.exec_module(module)

        (tmp_path / "VERSION").write_text("9.8.7\n", encoding="utf-8")
        env_file = tmp_path / ".env"
        env_file.write_text("OPENINFRA_POSTGRES_DB=openinfra\n", encoding="utf-8")
        config = module.RuntimeEnvironmentConfig(project_root=tmp_path, env_file=env_file)
        captured: dict[str, object] = {}

        class Completed:
            returncode = 0

        def capture(command, **kwargs):
            captured["command"] = command
            captured["override_path"] = Path(command[7])
            captured["override_payload"] = Path(command[7]).read_text(encoding="utf-8")
            captured.update(kwargs)
            return Completed()

        monkeypatch.setenv("OPENINFRA_IMAGE_TAG", "externally-forced")
        monkeypatch.setattr(module.subprocess, "run", capture)
        module.ComposeCommandRunner(config).run(["config", "--quiet"])

        command = captured["command"]
        assert isinstance(command, list)
        assert command[:8] == [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "-f",
            str(tmp_path / "compose.yaml"),
            "-f",
            command[7],
        ]
        assert command[8:] == ["config", "--quiet"]
        assert captured["override_payload"] == (
            "services:\n"
            "  migrate:\n"
            "    image: openinfra/runtime:9.8.7\n"
            "  runtime-secrets:\n"
            "    image: openinfra/runtime:9.8.7\n"
            "  auth-bootstrap:\n"
            "    image: openinfra/runtime:9.8.7\n"
            "  api:\n"
            "    image: openinfra/runtime:9.8.7\n"
            "  web:\n"
            "    image: openinfra/runtime:9.8.7\n"
            "  smoke:\n"
            "    image: openinfra/runtime:9.8.7\n"
        )
        override_path = captured["override_path"]
        assert isinstance(override_path, Path)
        assert not override_path.exists()
        assert "env" not in captured

    def test_compose_runner_cleans_runtime_override_when_docker_is_unavailable(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        module_path = Path("scripts/docker_environment.py")
        spec = importlib.util.spec_from_file_location("docker_environment_failure", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["docker_environment_failure"] = module
        spec.loader.exec_module(module)

        (tmp_path / "VERSION").write_text("9.8.7\n", encoding="utf-8")
        env_file = tmp_path / ".env"
        env_file.write_text("OPENINFRA_POSTGRES_DB=openinfra\n", encoding="utf-8")
        config = module.RuntimeEnvironmentConfig(project_root=tmp_path, env_file=env_file)
        captured: dict[str, Path] = {}

        def fail(command, **_kwargs):
            captured["override_path"] = Path(command[7])
            assert captured["override_path"].exists()
            raise FileNotFoundError("docker")

        monkeypatch.setattr(module.subprocess, "run", fail)
        with pytest.raises(module.DockerEnvironmentError, match="cannot execute Docker Compose"):
            module.ComposeCommandRunner(config).run(["config", "--quiet"])

        assert not captured["override_path"].exists()

    def test_runtime_managed_version_rejects_invalid_or_missing_version(
        self, tmp_path: Path
    ) -> None:
        module_path = Path("scripts/docker_environment.py")
        spec = importlib.util.spec_from_file_location("docker_environment_invalid", module_path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["docker_environment_invalid"] = module
        spec.loader.exec_module(module)

        resolver = module.RuntimeManagedConfiguration(tmp_path)
        with pytest.raises(module.DockerEnvironmentError):
            resolver.image_tag()
        (tmp_path / "VERSION").write_text("latest; rm -rf /", encoding="utf-8")
        with pytest.raises(module.DockerEnvironmentError):
            resolver.image_tag()

    def test_postgresql_migrations_use_existing_audit_timestamp_column(self) -> None:
        migration_payload = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(Path("installers/migrations/postgresql").glob("*.sql"))
        )

        assert "created_at timestamptz NOT NULL" in migration_payload
        audit_statements = "\n".join(
            statement
            for statement in migration_payload.split(";")
            if "audit_events" in statement.lower()
        )
        assert "occurred_at" not in audit_statements

    def test_ipam_enterprise_migration_backfills_legacy_prefix_family_column(self) -> None:
        migration = Path(
            "installers/migrations/postgresql/0015_ipam_enterprise_foundation.sql"
        ).read_text(encoding="utf-8")

        assert "ALTER TABLE prefixes ADD COLUMN IF NOT EXISTS family smallint" in migration
        assert (
            "UPDATE prefixes SET family = pg_catalog.family(prefixes.cidr) WHERE prefixes.family IS NULL"
            in migration
        )
        assert "ALTER TABLE prefixes ALTER COLUMN family SET NOT NULL" in migration
        assert migration.index("ALTER TABLE prefixes ADD COLUMN IF NOT EXISTS family smallint") < (
            migration.index("CREATE INDEX IF NOT EXISTS idx_prefixes_vrf_family")
        )
