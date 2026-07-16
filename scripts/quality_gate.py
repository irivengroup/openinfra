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
            self._project_root / "docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/VERSION",
            self._project_root / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/VERSION",
            self._project_root
            / "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2"
            / "14-alignement-cdc-v4.9.0.csv",
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


class ReleaseSecurityGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_release_security_controls_are_present(self) -> None:
        required_files = (
            "src/openinfra/quality/release_security.py",
            "scripts/release_security_audit.py",
            "scripts/security_http_probe.py",
            ".github/workflows/release-security.yml",
            "docs/runbooks/RELEASE_SECURITY.md",
        )
        missing = [
            relative for relative in required_files if not (self._project_root / relative).is_file()
        ]
        if missing:
            raise QualityGateError("missing release security controls: " + ", ".join(missing))
        workflow = (self._project_root / ".github/workflows/release-security.yml").read_text(
            encoding="utf-8"
        )
        required_fragments = (
            "tags: ['v*']",
            "workflow_dispatch:",
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/setup-node@v6",
            "actions/upload-artifact@v6",
            "python scripts/docker_environment.py init",
            "docker compose --env-file .env build api",
            "scripts/release_security_audit.py",
            "--enforce",
            "retention-days: 90",
        )
        missing_fragments = [
            fragment for fragment in required_fragments if fragment not in workflow
        ]
        if missing_fragments:
            raise QualityGateError(
                "release security workflow is incomplete: " + ", ".join(missing_fragments)
            )
        if "pull_request_target:" in workflow:
            raise QualityGateError(
                "release security workflow must not execute from pull_request_target"
            )
        environment_manager = (self._project_root / "scripts/docker_environment.py").read_text(
            encoding="utf-8"
        )
        required_environment_keys = (
            "OPENINFRA_POSTGRES_REPLICATION_PASSWORD",
            "OPENINFRA_READ_CONSISTENCY_SECRET",
            "OPENINFRA_GRAFANA_ADMIN_PASSWORD",
        )
        missing_environment_keys = [
            key for key in required_environment_keys if key not in environment_manager
        ]
        if missing_environment_keys:
            raise QualityGateError(
                "runtime environment generator misses mandatory secrets: "
                + ", ".join(missing_environment_keys)
            )


class ReleasePackagingGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_release_packaging_controls_are_present(self) -> None:
        required_files = (
            "src/openinfra/quality/release_packaging.py",
            "scripts/release_packaging_audit.py",
            ".github/workflows/release-packaging.yml",
            "docs/architecture/release-packaging-certification.md",
            "docs/runbooks/RELEASE_PACKAGING.md",
            "tests/unit/test_release_packaging.py",
            "tests/integration/test_release_packaging_workflow.py",
            "tests/integration/test_release_packaging_installer_rollback.py",
        )
        missing = [
            relative for relative in required_files if not (self._project_root / relative).is_file()
        ]
        if missing:
            raise QualityGateError("missing release packaging controls: " + ", ".join(missing))
        workflow = (self._project_root / ".github/workflows/release-packaging.yml").read_text(
            encoding="utf-8"
        )
        required_fragments = (
            "tags: ['v*']",
            "workflow_dispatch:",
            "actions/checkout@v6",
            "fetch-depth: 0",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64",
            "release_packaging_audit.py",
            "--signing-key-from-env",
            "--enforce",
            "sha256sum --check",
            "ReleaseSignatureVerifier",
            "retention-days: 90",
        )
        missing_fragments = [
            fragment for fragment in required_fragments if fragment not in workflow
        ]
        if missing_fragments:
            raise QualityGateError(
                "release packaging workflow is incomplete: " + ", ".join(missing_fragments)
            )
        if "pull_request_target:" in workflow:
            raise QualityGateError(
                "release packaging workflow must not execute from pull_request_target"
            )
        package_lock = (self._project_root / "web/package-lock.json").read_text(encoding="utf-8")
        for forbidden in ("applied-caas", ".internal.api", "artifactory/api/npm"):
            if forbidden in package_lock:
                raise QualityGateError(
                    "frontend lockfile must not expose an internal registry: " + forbidden
                )
        source = (self._project_root / "src/openinfra/quality/release_packaging.py").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "ReproducibleDistributionBuilder",
            "ReleaseSbomBuilder",
            "ReleaseSigningMaterial",
            "InstallerPackagingValidator",
            "IsolatedWheelSmokeValidator",
            "ReleaseChecksumManifest",
        ):
            if fragment not in source:
                raise QualityGateError(
                    "release packaging implementation is incomplete: " + fragment
                )


class GaDocumentationGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_ga_documentation_controls_are_present(self) -> None:
        required_files = (
            "src/openinfra/quality/documentation_ga.py",
            "scripts/validate_ga_documentation.py",
            ".github/workflows/documentation-ga.yml",
            "docs/architecture/ga-documentation-governance.md",
            "docs/ga/documentation-manifest.json",
            "docs/ga/README.md",
            "docs/ga/INSTALLATION.md",
            "docs/ga/ADMINISTRATION.md",
            "docs/ga/USER_GUIDE.md",
            "docs/ga/API_GUIDE.md",
            "docs/ga/OPERATIONS.md",
            "docs/ga/DISASTER_RECOVERY.md",
            "docs/ga/UPGRADE.md",
            "docs/ga/TROUBLESHOOTING.md",
            "docs/ga/SUPPORT.md",
            "tests/unit/test_documentation_ga.py",
            "tests/integration/test_documentation_ga_contract.py",
        )
        missing = [
            relative for relative in required_files if not (self._project_root / relative).is_file()
        ]
        if missing:
            raise QualityGateError("missing GA documentation controls: " + ", ".join(missing))
        workflow = (self._project_root / ".github/workflows/documentation-ga.yml").read_text(
            encoding="utf-8"
        )
        required_fragments = (
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "validate_ga_documentation.py",
            "ga-documentation-report.json",
            "retention-days: 90",
        )
        absent = [fragment for fragment in required_fragments if fragment not in workflow]
        if absent:
            raise QualityGateError("GA documentation workflow is incomplete: " + ", ".join(absent))
        if "pull_request_target:" in workflow:
            raise QualityGateError(
                "GA documentation workflow must not execute from pull_request_target"
            )


class GaGoNoGoGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_ga_go_no_go_controls_are_present(self) -> None:
        required_files = (
            "src/openinfra/quality/ga_go_no_go.py",
            "scripts/ga_go_no_go.py",
            ".github/workflows/ga-go-no-go.yml",
            "docs/release/ga-go-no-go-policy.json",
            "docs/release/ga-trust-policy.schema.json",
            "docs/runbooks/GA_GO_NO_GO.md",
            "tests/unit/test_ga_go_no_go.py",
        )
        missing = [
            relative for relative in required_files if not (self._project_root / relative).is_file()
        ]
        if missing:
            raise QualityGateError("missing GA Go/No-Go controls: " + ", ".join(missing))
        workflow = (self._project_root / ".github/workflows/ga-go-no-go.yml").read_text(
            encoding="utf-8"
        )
        required_fragments = (
            "workflow_dispatch:",
            "workflow_call:",
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/download-artifact@v6",
            "actions/upload-artifact@v6",
            "OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64",
            "OPENINFRA_GA_TRUST_POLICY_B64",
            "scripts/ga_go_no_go.py",
            "--enforce-go",
            "retention-days: 365",
        )
        absent = [fragment for fragment in required_fragments if fragment not in workflow]
        if absent:
            raise QualityGateError("GA Go/No-Go workflow is incomplete: " + ", ".join(absent))
        if "pull_request_target:" in workflow:
            raise QualityGateError("GA Go/No-Go workflow must not use pull_request_target")
        source = (self._project_root / "src/openinfra/quality/ga_go_no_go.py").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "GATE-07",
            "EPIC-1805",
            "GaApprovalVerifier",
            "GaRiskEvaluator",
            "ReleaseSignatureVerifier",
            "authorized_for_ga",
        ):
            if fragment not in source:
                raise QualityGateError("GA Go/No-Go implementation is incomplete: " + fragment)


class SupportReadinessGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_support_readiness_controls_are_present(self) -> None:
        required_files = (
            "src/openinfra/quality/support_readiness.py",
            "scripts/support_readiness.py",
            ".github/workflows/support-readiness.yml",
            "docs/release/support-maintenance-policy.json",
            "docs/ga/SUPPORT.md",
            "docs/runbooks/SUPPORT_MAINTENANCE.md",
            "tests/unit/test_support_readiness.py",
            "tests/integration/test_support_readiness_contract.py",
        )
        missing = [
            relative for relative in required_files if not (self._project_root / relative).is_file()
        ]
        if missing:
            raise QualityGateError("missing support readiness controls: " + ", ".join(missing))
        workflow = (self._project_root / ".github/workflows/support-readiness.yml").read_text(
            encoding="utf-8"
        )
        required_fragments = (
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "scripts/support_readiness.py",
            "--ephemeral-key",
            "--enforce",
            "retention-days: 365",
        )
        absent = [fragment for fragment in required_fragments if fragment not in workflow]
        if absent:
            raise QualityGateError("support readiness workflow is incomplete: " + ", ".join(absent))
        if "pull_request_target:" in workflow:
            raise QualityGateError("support readiness workflow must not use pull_request_target")
        source = (self._project_root / "src/openinfra/quality/support_readiness.py").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "EPIC-1806",
            "support-readiness",
            "SupportReadinessService",
            "ReleaseSignatureVerifier",
            "sla_defined",
            "lifecycle_defined",
            "patch_policy_defined",
            "migration_policy_defined",
            "escalation_matrix_defined",
        ):
            if fragment not in source:
                raise QualityGateError(
                    "support readiness implementation is incomplete: " + fragment
                )


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
        current_version = (self._project_root / "VERSION").read_text(encoding="utf-8").strip()
        expected_image = f"openinfra/runtime:${{OPENINFRA_IMAGE_TAG:-{current_version}}}"
        if expected_image not in compose:
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
            "OPENINFRA_IMAGE_TAG=0.29.28",
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
            "${OPENINFRA_IMAGE_TAG:-0.29.28}",
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
        if (
            '"OPENINFRA_WEB_BACKEND_URL"' not in env_manager
            or '"http://api:8080"' not in env_manager
        ):
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
        if (
            '"OPENINFRA_PGADMIN_EMAIL"' not in env_manager
            or '"admin@openinfra.tld"' not in env_manager
        ):
            raise QualityGateError(
                "docker environment manager must generate a pgAdmin4 email accepted by pgAdmin4"
            )
        if "admin@openinfra.local" in env_example + env_manager:
            raise QualityGateError("pgAdmin4 email must not use reserved .local domain")
        if '"OPENINFRA_PGADMIN_PASSWORD"' not in env_manager:
            raise QualityGateError("docker environment manager must generate pgAdmin4 credentials")


class HighPerformanceRuntimeGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_pro_enterprise_runtime_is_bounded(self) -> None:
        required_files = (
            "src/openinfra/interfaces/asgi.py",
            "src/openinfra/interfaces/asgi_web.py",
            "docs/architecture/high-performance-pro-enterprise.md",
            "docs/runbooks/HIGH_PERFORMANCE_RUNTIME.md",
            "tests/integration/test_asgi_performance_runtime.py",
            "tests/performance/test_high_performance_runtime_benchmark.py",
            "scripts/benchmark_high_performance_runtime.py",
            "src/openinfra/infrastructure/cursor_pagination.py",
            "installers/migrations/postgresql/0053_keyset_pagination_indexes.sql",
            "installers/migrations/postgresql/0054_async_outbox_workers.sql",
            "src/openinfra/domain/async_processing.py",
            "src/openinfra/application/async_processing_services.py",
            "src/openinfra/infrastructure/async_processing.py",
            "docs/architecture/transactional-outbox-workers.md",
            "docs/runbooks/ASYNC_WORKERS.md",
            "tests/integration/test_async_processing_migration.py",
            "tests/unit/test_cursor_pagination.py",
            "tests/unit/test_export_stream_builder.py",
            "tests/performance/test_cursor_pagination_benchmark.py",
            "scripts/benchmark_cursor_pagination.py",
            "docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/00-Delta-v4.9.md",
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/02-roadmap-phases.csv",
        )
        missing = [name for name in required_files if not (self._project_root / name).is_file()]
        if missing:
            raise QualityGateError("missing high-performance runtime assets: " + ", ".join(missing))
        pyproject = (self._project_root / "pyproject.toml").read_text(encoding="utf-8")
        for dependency in ("uvicorn>=", "httpx>=", "psycopg_pool>="):
            if dependency not in pyproject:
                raise QualityGateError("missing high-performance runtime dependency: " + dependency)
        api = (self._project_root / "src/openinfra/interfaces/http_api.py").read_text(
            encoding="utf-8"
        )
        web = (self._project_root / "src/openinfra/interfaces/web.py").read_text(encoding="utf-8")
        postgresql = (self._project_root / "src/openinfra/infrastructure/postgresql.py").read_text(
            encoding="utf-8"
        )
        bff = (self._project_root / "src/openinfra/interfaces/asgi_web.py").read_text(
            encoding="utf-8"
        )
        required_fragments = {
            "api": (
                'default=os.environ.get("OPENINFRA_API_RUNTIME", "asgi")',
                'choices=("asgi", "legacy")',
                "limit_concurrency",
                "workers",
            ),
            "web": (
                'default=os.environ.get("OPENINFRA_WEB_RUNTIME", "asgi")',
                'choices=("asgi", "legacy")',
                "limit_concurrency",
            ),
            "postgresql": (
                "PostgreSQLConnectionPoolSettings",
                "OPENINFRA_DB_CONNECTION_BUDGET",
                "max_size * self.worker_count",
                "psycopg_pool",
            ),
            "bff": (
                "httpx.AsyncClient",
                "max_keepalive_connections",
                "client.stream",
                "pool_timeout_seconds",
            ),
        }
        payloads = {"api": api, "web": web, "postgresql": postgresql, "bff": bff}
        for component, fragments in required_fragments.items():
            absent = [fragment for fragment in fragments if fragment not in payloads[component]]
            if absent:
                raise QualityGateError(
                    component + " high-performance contract is incomplete: " + ", ".join(absent)
                )
        env_example = (self._project_root / ".env.example").read_text(encoding="utf-8")
        for setting in (
            "OPENINFRA_API_RUNTIME=asgi",
            "OPENINFRA_DB_CONNECTION_BUDGET=",
            "OPENINFRA_WEB_RUNTIME=asgi",
            "OPENINFRA_WEB_HTTP_MAX_CONNECTIONS=",
        ):
            if setting not in env_example:
                raise QualityGateError("missing runtime setting in .env.example: " + setting)
        workflow = (self._project_root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for marker in (
            "High-performance ASGI and pooling regression",
            "benchmark_high_performance_runtime.py",
            "high-performance-runtime.json",
        ):
            if marker not in workflow:
                raise QualityGateError(
                    "CI must execute and persist the high-performance runtime regression: " + marker
                )
        for marker in (
            "Cursor pagination and streaming export regression",
            "benchmark_cursor_pagination.py",
            "cursor-pagination.json",
        ):
            if marker not in workflow:
                raise QualityGateError(
                    "CI must execute and persist the cursor pagination regression: " + marker
                )
        cursor_source = (
            self._project_root / "src/openinfra/infrastructure/cursor_pagination.py"
        ).read_text(encoding="utf-8")
        postgresql_source = (
            self._project_root / "src/openinfra/infrastructure/postgresql.py"
        ).read_text(encoding="utf-8")
        export_source = (
            self._project_root / "src/openinfra/application/export_services.py"
        ).read_text(encoding="utf-8")
        for fragment in ("CursorTokenCodec", "PostgreSQLKeysetPage", "legacy_offset"):
            if fragment not in cursor_source:
                raise QualityGateError("cursor pagination contract is incomplete: " + fragment)
        if " OFFSET %(" in postgresql_source:
            raise QualityGateError("PostgreSQL repositories must not use direct OFFSET pagination")
        for fragment in ("SpooledTemporaryFile", "_iterate_source_objects", "spooled_to_disk"):
            if fragment not in export_source:
                raise QualityGateError("streaming export contract is incomplete: " + fragment)


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
        audit_statements = "\n".join(
            statement for statement in payload.split(";") if "audit_events" in statement.lower()
        )
        if "occurred_at" in audit_statements:
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
        HighPerformanceRuntimeGuard(self._project_root).assert_pro_enterprise_runtime_is_bounded()
        CiWorkflowTriggerGuard(self._project_root).assert_push_triggers_are_not_branch_locked()
        ReleaseSecurityGuard(self._project_root).assert_release_security_controls_are_present()
        ReleasePackagingGuard(self._project_root).assert_release_packaging_controls_are_present()
        GaDocumentationGuard(self._project_root).assert_ga_documentation_controls_are_present()
        GaGoNoGoGuard(self._project_root).assert_ga_go_no_go_controls_are_present()
        SupportReadinessGuard(self._project_root).assert_support_readiness_controls_are_present()
        CommandRunner().run(
            [
                sys.executable,
                "scripts/support_readiness.py",
                "--project-root",
                str(self._project_root),
                "--output",
                "artifacts/quality-gate/support-readiness.json",
                "--ephemeral-key",
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_ga_documentation.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
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
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_pra_pca.py",
                "--project-root",
                str(self._project_root),
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_multisite_observability.py",
                "--project-root",
                str(self._project_root),
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_multisite_chaos.py",
                "--project-root",
                str(self._project_root),
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_scaleout_promotion.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_kubernetes_topology.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_kubernetes_exposure.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_kubernetes_security.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_kubernetes_gitops.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_kubernetes_capacity.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
            ]
        )
        CommandRunner().run(
            [
                sys.executable,
                "scripts/validate_cloud_native_promotion.py",
                "--project-root",
                str(self._project_root),
                "--enforce",
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
