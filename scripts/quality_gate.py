from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


class QualityGateError(Exception):
    """Raised when the local quality gate fails."""


class ModuleFunctionGuard:
    def __init__(self, root: Path) -> None:
        self._root = root

    def assert_no_module_level_functions(self) -> None:
        violations: list[str] = []
        for path in sorted(self._root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    violations.append(f"{path}:{node.lineno}:{node.name}")
        if violations:
            raise QualityGateError("module-level functions are forbidden: " + ", ".join(violations))


class ContractFileGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_sources_present(self) -> None:
        required = (
            self._project_root / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/VERSION",
            self._project_root / "docs/specifications/OpenInfra-Roadmap-Developpement-v2/VERSION",
            self._project_root
            / "docs/specifications/OpenInfra-Roadmap-Developpement-v2/14-alignement-cdc-v4.8.1.csv",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise QualityGateError("missing contractual source files: " + ", ".join(missing))


class NativeRuntimeGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_runtime_environment_present(self) -> None:
        required = (
            "docs/runbooks/RUNTIME_NATIVE.md",
            "scripts/native_runtime_smoke.py",
            "scripts/validate_autonomous_installer.py",
            "scripts/validate_enterprise_alignment.py",
            "scripts/validate_frontend.py",
            "installers/migrations/postgresql/0001_bootstrap.sql",
            "installers/requirements/common.txt",
            "installers/requirements/backend.txt",
            "installers/requirements/web.txt",
            "installers/requirements/agent.txt",
            "installers/setup/installer_runtime.py",
            "installers/setup/lite/install.py",
            "installers/setup/lite/install.ini",
            "installers/setup/pro/server/install.py",
            "installers/setup/pro/server/install.ini",
            "installers/setup/pro/web/install.py",
            "installers/setup/pro/web/install.ini",
            "installers/setup/enterprise/server/install.py",
            "installers/setup/enterprise/server/install.ini",
            "installers/setup/enterprise/web/install.py",
            "installers/setup/enterprise/web/install.ini",
            "installers/setup/enterprise/agent/install.py",
            "installers/setup/enterprise/agent/install.ini",
        )
        missing = [name for name in required if not (self._project_root / name).is_file()]
        if missing:
            raise QualityGateError("missing native runtime assets: " + ", ".join(missing))
        if (self._project_root / "deploy").exists():
            raise QualityGateError(
                "deploy directory must not be packaged; systemd units are rendered by installer"
            )
        if (self._project_root / "migrations").exists():
            raise QualityGateError(
                "root migrations directory must not be packaged; "
                "use installers/migrations/postgresql"
            )
        for forbidden in ("installers/lite", "installers/pro", "installers/enterprise"):
            if (self._project_root / forbidden).exists():
                raise QualityGateError("legacy installer root must not be packaged: " + forbidden)
        runbook = (self._project_root / "docs/runbooks/RUNTIME_NATIVE.md").read_text(
            encoding="utf-8"
        )
        installer_config = (
            self._project_root / "src/openinfra/infrastructure/installer_config.py"
        ).read_text(encoding="utf-8")
        if "InstallerSystemdUnitRenderer" not in installer_config:
            raise QualityGateError("installer must render systemd units internally")
        if "InstallerPostgreSQLDeploymentPlanner" not in installer_config:
            raise QualityGateError("backend installer must deploy PostgreSQL when absent")
        if "managed_application_filesystem" not in installer_config:
            raise QualityGateError("installer must model application filesystem policy per scope")
        if "application_filesystem_plan" not in installer_config:
            raise QualityGateError(
                "installer must expose application filesystem plans for every installed scope"
            )
        if "create or validate internal application LVM filesystem" not in installer_config:
            raise QualityGateError("installer must orchestrate the CDC application filesystem")
        required_ha_fragments = (
            "InstallerPostgreSQLHaPlan",
            "near-real-time-postgresql-streaming",
            "near-real-time-streaming-cluster",
            "pitr_archive_directory",
            "local_commit_non_blocking",
        )
        missing_ha = [
            fragment for fragment in required_ha_fragments if fragment not in installer_config
        ]
        if missing_ha:
            raise QualityGateError(
                "installer must model PostgreSQL near-real-time HA/PITR P06: "
                + ", ".join(missing_ha)
            )
        installer_runtime = (
            self._project_root / "installers/setup/installer_runtime.py"
        ).read_text(encoding="utf-8")
        required_runtime_fragments = (
            "InstallationPrerequisite",
            "InstallationRollbackJournal",
            "RollbackManager",
            "--verify-only",
            "--migrate-only",
            "--rollback",
            "create Python virtual environment",
            "install scope production requirements",
            "restart OpenInfra service",
            "PostgreSQL DSN cannot be resolved; set OPENINFRA_DATABASE_DSN",
            "_render_postgresql_ha_configuration",
            "postgresql-ha.json",
            "openinfra-ha.conf",
        )
        missing_runtime = [
            fragment for fragment in required_runtime_fragments if fragment not in installer_runtime
        ]
        if missing_runtime:
            raise QualityGateError(
                "autonomous installer runtime is incomplete: " + ", ".join(missing_runtime)
            )
        if "OPENINFRA_DATABASE_DSN" not in runbook:
            raise QualityGateError("native runbook must document the PostgreSQL DSN")
        if "Docker ne fait pas partie de la chaine d'execution production" not in runbook:
            raise QualityGateError(
                "native runbook must state that Docker is not part of production runtime"
            )
        if (self._project_root / ".env").exists():
            raise QualityGateError("local .env must not be packaged or committed")


class CiWorkflowTriggerGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_push_triggers_are_not_branch_locked(self) -> None:
        workflow = self._project_root / ".github/workflows/ci.yml"
        if not workflow.is_file():
            raise QualityGateError("missing GitHub Actions workflow: .github/workflows/ci.yml")
        content = workflow.read_text(encoding="utf-8")
        if "workflow_dispatch:" not in content:
            raise QualityGateError("CI workflow must expose a manual workflow_dispatch trigger")
        forbidden = ("branches: [main]", "branches: ['main']", 'branches: ["main"]')
        if any(pattern in content for pattern in forbidden):
            raise QualityGateError(
                "CI workflow push/pull_request triggers must not be locked to main only"
            )
        if "branches: ['**']" not in content:
            raise QualityGateError("CI workflow must run on every branch push and pull request")


class DockerRuntimeGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_optional_compose_runtime_is_well_scoped(self) -> None:
        dockerfile = (self._project_root / "Dockerfile").read_text(encoding="utf-8")
        compose = (self._project_root / "compose.yaml").read_text(encoding="utf-8")
        env_example = (self._project_root / ".env.example").read_text(encoding="utf-8")
        env_manager = (self._project_root / "scripts/docker_environment.py").read_text(
            encoding="utf-8"
        )
        if "HEALTHCHECK" in dockerfile:
            raise QualityGateError(
                "Dockerfile must not define an API healthcheck inherited by migrate/auth-bootstrap"
            )
        if "openinfra/runtime:${OPENINFRA_IMAGE_TAG:-0.29.28}" not in compose:
            raise QualityGateError("compose.yaml must default to the current OpenInfra image tag")
        if "OPENINFRA_WEB_BACKEND_BEARER_TOKEN:-${OPENINFRA_BOOTSTRAP_TOKEN" not in compose:
            raise QualityGateError(
                "openinfra-web must fall back to OPENINFRA_BOOTSTRAP_TOKEN "
                "when its dedicated backend bearer token is blank"
            )
        stale_tags = (
            "OPENINFRA_IMAGE_TAG=0.9.0",
            "OPENINFRA_IMAGE_TAG=0.14.0",
            "OPENINFRA_IMAGE_TAG=0.22.1",
            "OPENINFRA_IMAGE_TAG=0.22.2",
            "OPENINFRA_IMAGE_TAG=0.28.1",
            "OPENINFRA_IMAGE_TAG=0.29.11",
            "OPENINFRA_IMAGE_TAG=0.29.13",
            "OPENINFRA_IMAGE_TAG=0.29.14",
            "${OPENINFRA_IMAGE_TAG:-0.14.0}",
            "${OPENINFRA_IMAGE_TAG:-0.22.1}",
            "${OPENINFRA_IMAGE_TAG:-0.22.2}",
            "${OPENINFRA_IMAGE_TAG:-0.28.1}",
            "${OPENINFRA_IMAGE_TAG:-0.29.1}",
            "${OPENINFRA_IMAGE_TAG:-0.29.2}",
            "${OPENINFRA_IMAGE_TAG:-0.29.3}",
            "${OPENINFRA_IMAGE_TAG:-0.29.4}",
            "${OPENINFRA_IMAGE_TAG:-0.29.5}",
            "${OPENINFRA_IMAGE_TAG:-0.29.6}",
            "${OPENINFRA_IMAGE_TAG:-0.29.11}",
            "${OPENINFRA_IMAGE_TAG:-0.29.13}",
            "${OPENINFRA_IMAGE_TAG:-0.29.14}",
        )
        stale = [
            fragment for fragment in stale_tags if fragment in compose + env_example + env_manager
        ]
        if stale:
            raise QualityGateError("stale Docker image tag defaults detected: " + ", ".join(stale))

        web_required = (
            "  web:",
            "container_name: openinfra-web",
            "openinfra-web",
            "OPENINFRA_WEB_BACKEND_URL",
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL",
            "OPENINFRA_WEB_ALLOW_INSECURE_BACKEND",
            "${OPENINFRA_WEB_BIND:-127.0.0.1}:${OPENINFRA_WEB_PORT:-2006}:2006",
            "http://127.0.0.1:2006/health",
        )
        missing_web = [fragment for fragment in web_required if fragment not in compose]
        if missing_web:
            raise QualityGateError(
                "compose openinfra-web service is incomplete: " + ", ".join(missing_web)
            )
        web_env_required = (
            "OPENINFRA_WEB_BIND=127.0.0.1",
            "OPENINFRA_WEB_PORT=2006",
            "OPENINFRA_WEB_BACKEND_URL=http://api:8080",
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL=/api",
            "OPENINFRA_WEB_ALLOW_INSECURE_BACKEND=true",
        )
        missing_web_env = [fragment for fragment in web_env_required if fragment not in env_example]
        if missing_web_env:
            raise QualityGateError(
                ".env.example missing openinfra-web variables: " + ", ".join(missing_web_env)
            )
        if "OPENINFRA_WEB_BACKEND_URL=http://api:8080" not in env_manager:
            raise QualityGateError(
                "docker environment manager must generate openinfra-web settings"
            )

        pgadmin_servers = self._project_root / "docker/pgadmin/servers.json"
        if "  pgadmin:" not in compose:
            raise QualityGateError(
                "compose.yaml must include pgAdmin4 service for lab database administration"
            )
        pgadmin_required = (
            "${OPENINFRA_PGADMIN_IMAGE:-dpage/pgadmin4:latest}",
            "openinfra-pgadmin-data:/var/lib/pgadmin",
            "./docker/pgadmin/servers.json:/pgadmin4/servers.json:ro",
            "${OPENINFRA_PGADMIN_BIND:-127.0.0.1}:${OPENINFRA_PGADMIN_PORT:-5050}:80",
            "PGADMIN_DEFAULT_EMAIL",
            "PGADMIN_DEFAULT_PASSWORD",
        )
        missing_pgadmin = [fragment for fragment in pgadmin_required if fragment not in compose]
        if missing_pgadmin:
            raise QualityGateError(
                "compose pgAdmin4 service is incomplete: " + ", ".join(missing_pgadmin)
            )
        if not pgadmin_servers.is_file():
            raise QualityGateError(
                "missing pgAdmin4 server registration: docker/pgadmin/servers.json"
            )
        pgadmin_content = pgadmin_servers.read_text(encoding="utf-8")
        if (
            '"Host": "postgres"' not in pgadmin_content
            or '"MaintenanceDB": "openinfra"' not in pgadmin_content
        ):
            raise QualityGateError(
                "pgAdmin4 server registration must target the Compose PostgreSQL service"
            )
        env_required = (
            "OPENINFRA_PGADMIN_EMAIL=",
            "OPENINFRA_PGADMIN_PASSWORD=",
            "OPENINFRA_PGADMIN_BIND=127.0.0.1",
            "OPENINFRA_PGADMIN_PORT=5050",
            "OPENINFRA_PGADMIN_IMAGE=dpage/pgadmin4:latest",
        )
        missing_env = [fragment for fragment in env_required if fragment not in env_example]
        if missing_env:
            raise QualityGateError(
                ".env.example missing pgAdmin4 variables: " + ", ".join(missing_env)
            )
        if "OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld" not in env_example:
            raise QualityGateError(".env.example must use a pgAdmin4 email accepted by pgAdmin4")
        if "OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld" not in env_manager:
            raise QualityGateError(
                "docker environment manager must generate a pgAdmin4 email accepted by pgAdmin4"
            )
        if "admin@openinfra.local" in env_example + env_manager:
            raise QualityGateError("pgAdmin4 email must not use reserved .local domain")
        if "OPENINFRA_PGADMIN_PASSWORD=" not in env_manager:
            raise QualityGateError("docker environment manager must generate pgAdmin4 credentials")


class PostgreSQLMigrationSchemaGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_audit_indexes_use_created_at(self) -> None:
        payload = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(
                (self._project_root / "installers/migrations/postgresql").glob("*.sql")
            )
        )
        if "occurred_at" in payload:
            raise QualityGateError(
                "PostgreSQL migrations must not reference missing audit_events.occurred_at"
            )

    def assert_enterprise_ipam_migration_backfills_prefix_family(self) -> None:
        migration = (
            self._project_root
            / "installers/migrations/postgresql/0015_ipam_enterprise_foundation.sql"
        ).read_text(encoding="utf-8")
        required = (
            "ALTER TABLE prefixes ADD COLUMN IF NOT EXISTS family smallint",
            (
                "UPDATE prefixes SET family = pg_catalog.family(prefixes.cidr) "
                "WHERE prefixes.family IS NULL"
            ),
            "ALTER TABLE prefixes ALTER COLUMN family SET NOT NULL",
            "CREATE INDEX IF NOT EXISTS idx_prefixes_vrf_family",
        )
        missing = [fragment for fragment in required if fragment not in migration]
        if missing:
            raise QualityGateError(
                "IPAM migration must backfill prefixes.family before indexing it: "
                + ", ".join(missing)
            )


class CompletionMarkerGuard:
    _encoded_markers = (
        ("T", "O", "D", "O"),
        ("F", "I", "X", "M", "E"),
        ("s", "t", "u", "b"),
        ("p", "l", "a", "c", "e", "h", "o", "l", "d", "e", "r"),
        ("d", "u", "m", "m", "y"),
        ("N", "o", "t", "I", "m", "p", "l", "e", "m", "e", "n", "t", "e", "d"),
    )
    _roots = ("src", "tests", "scripts", "docker", ".github", "installers")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def _markers(self) -> tuple[str, ...]:
        return tuple("".join(parts) for parts in self._encoded_markers)

    def assert_clean_sources(self) -> None:
        violations: list[str] = []
        for root_name in self._roots:
            root = self._project_root / root_name
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                if path.suffix not in (".py", ".yml", ".yaml", ".sql", ".md", ".service"):
                    continue
                content = path.read_text(encoding="utf-8")
                for marker in self._markers():
                    if marker in content:
                        violations.append(f"{path}:{marker}")
        if violations:
            raise QualityGateError(
                "disallowed completion markers detected: " + ", ".join(violations)
            )


class CommandRunner:
    def run(self, command: list[str]) -> None:
        completed = subprocess.run(command, check=False, text=True)
        if completed.returncode != 0:
            raise QualityGateError("command failed: " + " ".join(command))


class QualityGate:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def run(self) -> None:
        ModuleFunctionGuard(self._project_root / "src/openinfra").assert_no_module_level_functions()
        ContractFileGuard(self._project_root).assert_sources_present()
        NativeRuntimeGuard(self._project_root).assert_runtime_environment_present()
        CiWorkflowTriggerGuard(self._project_root).assert_push_triggers_are_not_branch_locked()
        DockerRuntimeGuard(self._project_root).assert_optional_compose_runtime_is_well_scoped()
        CommandRunner().run(
            [sys.executable, "scripts/validate_autonomous_installer.py", "--root", "installers"]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_enterprise_alignment.py",
                "--project-root",
                str(self._project_root),
            ]
        )
        postgres_migration_guard = PostgreSQLMigrationSchemaGuard(self._project_root)
        postgres_migration_guard.assert_audit_indexes_use_created_at()
        postgres_migration_guard.assert_enterprise_ipam_migration_backfills_prefix_family()
        CompletionMarkerGuard(self._project_root).assert_clean_sources()
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_frontend.py",
                "--project-root",
                str(self._project_root),
            ]
        )
        CommandRunner().run(
            [sys.executable, "scripts/security_gate.py", "--project-root", str(self._project_root)]
        )
        if not (self._project_root / ".coverage").is_file():
            raise QualityGateError(
                "coverage data is missing; run python -m pytest before quality_gate.py"
            )
        CommandRunner().run([sys.executable, "-m", "coverage", "report", "--fail-under=98"])


class QualityGateCli:
    @classmethod
    def main(cls) -> int:
        try:
            QualityGate(Path.cwd()).run()
        except QualityGateError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(QualityGateCli.main())
