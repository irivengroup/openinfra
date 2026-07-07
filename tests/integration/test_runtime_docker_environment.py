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
        assert "OPENINFRA_IMAGE_TAG=0.29.33" in env_example
        assert "OPENINFRA_PGADMIN_EMAIL=" in env_example
        assert "OPENINFRA_PGADMIN_PASSWORD=" in env_example
        assert "OPENINFRA_PGADMIN_PORT=5050" in env_example
        assert "OPENINFRA_WEB_PORT=2006" in env_example
        assert "OPENINFRA_WEB_BACKEND_URL=http://api:8080" in env_example
        assert "OPENINFRA_WEB_BACKEND_BEARER_TOKEN:-${OPENINFRA_BOOTSTRAP_TOKEN" in compose
        assert "openinfra/runtime:${OPENINFRA_IMAGE_TAG:-0.29.33}" in compose
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
        assert "OPENINFRA_IMAGE_TAG=0.29.33" in payload
        assert "OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld" in payload
        assert "admin@openinfra.local" not in payload
        assert "OPENINFRA_PGADMIN_PASSWORD=" in payload
        assert "OPENINFRA_PGADMIN_IMAGE=dpage/pgadmin4:latest" in payload
        assert "OPENINFRA_WEB_BIND=127.0.0.1" in payload
        assert "OPENINFRA_WEB_BACKEND_URL=http://api:8080" in payload
        assert "replace-with" not in payload
        assert os.linesep in payload

    def test_postgresql_migrations_use_existing_audit_timestamp_column(self) -> None:
        migration_payload = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(Path("installers/migrations/postgresql").glob("*.sql"))
        )

        assert "created_at timestamptz NOT NULL" in migration_payload
        assert "occurred_at" not in migration_payload

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
