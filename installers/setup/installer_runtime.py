from __future__ import annotations

import argparse
import configparser
import importlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import quote


@dataclass(frozen=True, slots=True)
class InstallerLocation:
    project_root: Path
    installers_root: Path
    setup_root: Path
    scope_root: Path
    edition: str
    edition_directory: str
    scope: str
    config_path: Path


@dataclass(frozen=True, slots=True)
class InstallationCommand:
    label: str
    command: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"label": self.label, "command": list(self.command)}


@dataclass(frozen=True, slots=True)
class InstallationPrerequisite:
    label: str
    executable: str
    mandatory_on_offline_target: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "executable": self.executable,
            "mandatory_on_offline_target": self.mandatory_on_offline_target,
        }


@dataclass(frozen=True, slots=True)
class InstallationPlan:
    edition: str
    edition_directory: str
    scope: str
    config_path: Path
    application_root: Path
    configuration_root: Path
    compatibility_configuration_root: Path
    runtime_config_file: Path
    installation_lock_file: Path
    migrations_root: Path
    systemd_root: Path
    deploy_src: bool
    deploy_requirements: bool
    deploy_migrations: bool
    managed_postgresql: bool
    managed_application_filesystem: bool
    application_filesystem: Any | None
    postgresql_filesystem: Any | None
    postgresql_ha: Any | None
    service_name: str
    requirements_file: str
    actions: tuple[str, ...]
    commands: tuple[InstallationCommand, ...]
    prerequisites: tuple[InstallationPrerequisite, ...]
    transactional_rollback: bool
    start_service: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "edition": self.edition,
            "edition_directory": self.edition_directory,
            "scope": self.scope,
            "config_path": str(self.config_path),
            "application_root": str(self.application_root),
            "configuration_root": str(self.configuration_root),
            "compatibility_configuration_root": str(self.compatibility_configuration_root),
            "runtime_config_file": str(self.runtime_config_file),
            "installation_lock_file": str(self.installation_lock_file),
            "migrations_root": str(self.migrations_root),
            "systemd_root": str(self.systemd_root),
            "deploy_src": self.deploy_src,
            "deploy_requirements": self.deploy_requirements,
            "deploy_migrations": self.deploy_migrations,
            "managed_postgresql": self.managed_postgresql,
            "managed_application_filesystem": self.managed_application_filesystem,
            "application_filesystem": (
                self.application_filesystem.as_dict()
                if self.application_filesystem is not None
                else None
            ),
            "postgresql_filesystem": (
                self.postgresql_filesystem.as_dict()
                if self.postgresql_filesystem is not None
                else None
            ),
            "postgresql_ha": (
                self.postgresql_ha.as_dict() if self.postgresql_ha is not None else None
            ),
            "service_name": self.service_name,
            "requirements_file": self.requirements_file,
            "actions": list(self.actions),
            "commands": [command.as_dict() for command in self.commands],
            "prerequisites": [item.as_dict() for item in self.prerequisites],
            "transactional_rollback": self.transactional_rollback,
            "start_service": self.start_service,
        }


@dataclass(frozen=True, slots=True)
class RollbackEntry:
    destination: Path
    backup: Path | None
    created_directory: bool


class InstallerRuntimeError(RuntimeError):
    pass


class InstallerLocationResolver:
    def resolve(self, entrypoint: Path) -> InstallerLocation:
        scope_root = entrypoint.resolve().parent
        setup_root = self._find_setup_root(scope_root)
        installers_root = setup_root.parent
        project_root = installers_root.parent
        relative = scope_root.relative_to(setup_root)
        parts = relative.parts
        if parts == ("lite",):
            edition_directory = "lite"
            edition = "lite"
            scope = "all-in-one"
        elif len(parts) == 2 and parts[0] in {"pro", "enterprise"}:
            edition_directory = parts[0]
            edition = parts[0]
            scope = parts[1]
        else:
            raise InstallerRuntimeError(
                "installer entrypoint must be under installers/setup/lite, "
                "installers/setup/pro/<scope> or installers/setup/enterprise/<scope>"
            )
        return InstallerLocation(
            project_root=project_root,
            installers_root=installers_root,
            setup_root=setup_root,
            scope_root=scope_root,
            edition=edition,
            edition_directory=edition_directory,
            scope=scope,
            config_path=scope_root / "install.ini",
        )

    def _find_setup_root(self, scope_root: Path) -> Path:
        for parent in scope_root.parents:
            if parent.name == "setup" and (parent / "installer_runtime.py").is_file():
                return parent
        raise InstallerRuntimeError("cannot locate installers/setup/installer_runtime.py")


class OpenInfraImportBootstrap:
    def prepare(self, project_root: Path) -> None:
        src = project_root / "src"
        if not src.is_dir():
            raise InstallerRuntimeError(f"missing OpenInfra src directory: {src}")
        src_text = str(src)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)


class InstallationRollbackJournal:
    def __init__(self) -> None:
        self._entries: list[RollbackEntry] = []
        self._backup_roots: set[Path] = set()

    def record_created_directory(self, path: Path) -> None:
        self._entries.append(RollbackEntry(path, None, True))

    def record_replacement(self, destination: Path, backup: Path | None) -> None:
        self._entries.append(RollbackEntry(destination, backup, False))
        if backup is not None:
            self._backup_roots.add(backup.parent)

    def rollback(self) -> None:
        for entry in reversed(self._entries):
            if entry.created_directory:
                self._remove_empty_directory(entry.destination)
            elif entry.backup is None:
                self._remove_path(entry.destination)
            else:
                self._restore_backup(entry.destination, entry.backup)
        self._cleanup_empty_backup_roots()

    def commit(self) -> None:
        for entry in self._entries:
            if entry.backup is not None:
                self._remove_path(entry.backup)
        self._cleanup_empty_backup_roots()
        self._entries.clear()

    def _restore_backup(self, destination: Path, backup: Path) -> None:
        self._remove_path(destination)
        if backup.exists():
            backup.replace(destination)

    def _remove_path(self, path: Path) -> None:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()

    def _remove_empty_directory(self, path: Path) -> None:
        try:
            path.rmdir()
        except OSError:
            return

    def _cleanup_empty_backup_roots(self) -> None:
        for root in sorted(self._backup_roots, key=lambda item: len(item.parts), reverse=True):
            self._remove_empty_directory(root)
        self._backup_roots.clear()


class RollbackManager:
    def rollback_target(self, target_root: Path) -> dict[str, object]:
        roots = (
            self._target_path(target_root, "/opt/openinfra"),
            self._target_path(target_root, "/etc/openinfra"),
            self._target_path(target_root, "/etc/systemd/system"),
        )
        restored: list[str] = []
        for root in roots:
            if root.is_dir():
                restored.extend(self._rollback_root(root))
        return {"rolled_back": restored, "count": len(restored)}

    def _rollback_root(self, root: Path) -> list[str]:
        restored: list[str] = []
        for backup_root in sorted(root.rglob(".openinfra-rollback"), reverse=True):
            for backup in sorted(backup_root.iterdir()):
                if not backup.name.endswith(".bak"):
                    continue
                destination = backup_root.parent / backup.name.removesuffix(".bak")
                if destination.exists() or destination.is_symlink():
                    if destination.is_dir() and not destination.is_symlink():
                        shutil.rmtree(destination)
                    else:
                        destination.unlink()
                backup.replace(destination)
                restored.append(str(destination))
            try:
                backup_root.rmdir()
            except OSError:
                continue
        return restored

    def _target_path(self, target_root: Path, absolute: str) -> Path:
        normalized = Path(absolute)
        relative = normalized.relative_to("/")
        return target_root.resolve() / relative if target_root != Path("/") else normalized


class AutonomousInstallerProgram:
    _requirements_by_scope: ClassVar[dict[tuple[str, str], str]] = {
        ("lite", "all-in-one"): "lite-all-in-one.txt",
        ("pro", "server"): "pro-server.txt",
        ("pro", "web"): "pro-web.txt",
        ("enterprise", "server"): "enterprise-server.txt",
        ("enterprise", "web"): "enterprise-web.txt",
        ("enterprise", "agent"): "enterprise-agent.txt",
    }
    _postgresql_bootstrap_labels: ClassVar[set[str]] = {
        "install PostgreSQL packages",
        "initialize PostgreSQL cluster",
        "enable PostgreSQL service",
        "start PostgreSQL service",
        "verify PostgreSQL readiness",
    }

    def __init__(self, entrypoint: Path) -> None:
        self._location = InstallerLocationResolver().resolve(entrypoint)
        OpenInfraImportBootstrap().prepare(self._location.project_root)
        installer_config = importlib.import_module("openinfra.infrastructure.installer_config")
        self._validator = installer_config.InstallerConfigValidator()

    def main(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(
            prog=str(self._location.scope_root / "install.py"),
            description="OpenInfra autonomous scope installer",
        )
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--execute", action="store_true")
        mode.add_argument("--migrate-only", action="store_true")
        mode.add_argument("--verify-only", action="store_true")
        mode.add_argument("--rollback", action="store_true")
        parser.add_argument("--target-root", type=Path, default=Path("/"))
        parser.add_argument("--json", action="store_true")
        parser.add_argument(
            "--skip-service-enable",
            action="store_true",
            help="write files without calling systemctl; intended for offline image assembly",
        )
        args = parser.parse_args(argv)
        try:
            plan = self.build_plan(args.target_root)
            if args.dry_run:
                return self._emit(plan, executed=False, json_output=args.json)
            if args.verify_only:
                self._assert_prerequisites(plan, skip_service_enable=True)
                return self._emit(plan, executed=False, json_output=args.json)
            if args.rollback:
                payload = RollbackManager().rollback_target(args.target_root)
                return self._emit_payload(payload, json_output=args.json)
            if args.migrate_only:
                self.execute_migrations(plan)
                return self._emit(plan, executed=True, json_output=args.json)
            self.execute(plan, skip_service_enable=bool(args.skip_service_enable))
            return self._emit(plan, executed=True, json_output=args.json)
        except InstallerRuntimeError as exc:
            print(f"openinfra-installer: error: {exc}", file=sys.stderr)
            return 2

    def build_plan(self, target_root: Path) -> InstallationPlan:
        report = self._validator.validate_file(
            self._location.config_path,
            edition=self._location.edition,
            scope=self._location.scope,
        )
        if not report.valid:
            raise InstallerRuntimeError("invalid install.ini: " + "; ".join(report.errors))
        application_root = self._target_path(target_root, "/opt/openinfra")
        configuration_root = application_root / "config"
        compatibility_configuration_root = self._target_path(target_root, "/etc/openinfra")
        systemd_root = self._target_path(target_root, "/etc/systemd/system")
        runtime_config_file = configuration_root / "openinfra.conf"
        installation_lock_file = configuration_root / ".openinfra-installed.lock"
        migrations_root = application_root / "share/migrations/postgresql"
        requirements_file = self._requirements_by_scope[(report.edition, report.scope)]
        commands = self._build_commands(report, target_root, application_root, requirements_file)
        prerequisites = self._build_prerequisites(report, target_root)
        return InstallationPlan(
            edition=report.edition,
            edition_directory=self._location.edition_directory,
            scope=report.scope,
            config_path=self._location.config_path,
            application_root=application_root,
            configuration_root=configuration_root,
            compatibility_configuration_root=compatibility_configuration_root,
            runtime_config_file=runtime_config_file,
            installation_lock_file=installation_lock_file,
            migrations_root=migrations_root,
            systemd_root=systemd_root,
            deploy_src=True,
            deploy_requirements=True,
            deploy_migrations=report.scope in {"all-in-one", "server"},
            managed_postgresql=report.postgresql_plan is not None,
            managed_application_filesystem=report.managed_application_filesystem,
            application_filesystem=report.application_filesystem_plan,
            postgresql_filesystem=report.postgresql_filesystem_plan,
            postgresql_ha=report.postgresql_ha_plan,
            service_name=report.service,
            requirements_file=requirements_file,
            actions=report.actions,
            commands=commands,
            prerequisites=prerequisites,
            transactional_rollback=True,
            start_service=target_root == Path("/"),
        )

    def execute(self, plan: InstallationPlan, skip_service_enable: bool) -> None:
        self._assert_supported_execute_target(plan)
        self._assert_installation_lock_absent(plan)
        self._assert_prerequisites(plan, skip_service_enable=skip_service_enable)
        journal = InstallationRollbackJournal()
        try:
            if plan.application_root == Path("/opt/openinfra"):
                self._prepare_application_filesystem(plan, journal)
            self._create_directory(plan.application_root, journal)
            self._create_directory(plan.configuration_root, journal)
            self._ensure_configuration_symlink(plan, journal)
            self._create_directory(plan.systemd_root, journal)
            self._replace_tree(
                self._location.project_root / "src", plan.application_root / "src", journal
            )
            self._replace_tree(
                self._location.installers_root / "requirements",
                plan.application_root / "requirements",
                journal,
            )
            self._deploy_web_assets(plan, journal)
            self._replace_file(
                self._location.config_path,
                plan.configuration_root / f"install-{plan.edition_directory}-{plan.scope}.ini",
                mode=0o640,
                journal=journal,
            )
            self._render_runtime_configuration(plan, journal)
            self._replace_file(
                self._location.project_root / "pyproject.toml",
                plan.application_root / "pyproject.toml",
                mode=0o644,
                journal=journal,
            )
            if plan.deploy_migrations:
                self._replace_tree(
                    self._location.installers_root / "migrations" / "postgresql",
                    plan.migrations_root,
                    journal,
                )
            unit = self._validator.render_systemd_unit(plan.edition, plan.scope)
            self._replace_text(
                plan.systemd_root / plan.service_name, unit, mode=0o644, journal=journal
            )
            self._prepare_python_runtime(plan, journal)
            if plan.managed_postgresql:
                self._run_postgresql_bootstrap(plan, journal)
                self.execute_migrations(plan)
            self._write_installation_lock(plan, journal)
            if plan.application_root == Path("/opt/openinfra") and not skip_service_enable:
                self._run_command(("systemctl", "daemon-reload"))
                self._run_command(("systemctl", "enable", plan.service_name))
                self._run_command(("systemctl", "restart", plan.service_name))
            journal.commit()
        except Exception:
            journal.rollback()
            raise

    def execute_migrations(self, plan: InstallationPlan) -> None:
        if not plan.deploy_migrations:
            raise InstallerRuntimeError(f"{plan.edition}/{plan.scope} does not manage migrations")
        if plan.application_root != Path("/opt/openinfra"):
            return
        dsn = self._resolve_database_dsn(plan)
        self._run_command(
            (
                str(plan.application_root / "venv/bin/openinfra"),
                "database",
                "apply-migrations",
                "--root",
                str(plan.migrations_root),
            ),
            environment={"OPENINFRA_DATABASE_DSN": dsn},
        )

    def _build_commands(
        self, report: Any, target_root: Path, application_root: Path, requirements_file: str
    ) -> tuple[InstallationCommand, ...]:
        commands: list[InstallationCommand] = []
        venv_python = application_root / "venv/bin/python"
        if report.application_filesystem_plan is not None:
            commands.extend(self._filesystem_commands(report.application_filesystem_plan))
            commands.append(
                InstallationCommand(
                    "ensure OpenInfra system account",
                    (
                        "useradd",
                        "--system",
                        "--home",
                        "/opt/openinfra",
                        "--shell",
                        "/usr/sbin/nologin",
                        "openinfra",
                    ),
                )
            )
        if report.scope in {"all-in-one", "web"}:
            commands.append(
                InstallationCommand(
                    "deploy OpenInfra web assets",
                    ("install", "-d", str(application_root / "web")),
                )
            )
        commands.extend(
            (
                InstallationCommand(
                    "create Python virtual environment",
                    ("python3", "-m", "venv", str(application_root / "venv")),
                ),
                InstallationCommand(
                    "install scope production requirements",
                    (
                        str(venv_python),
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(application_root / "requirements" / requirements_file),
                    ),
                ),
                InstallationCommand(
                    "install OpenInfra application package",
                    (str(venv_python), "-m", "pip", "install", str(application_root)),
                ),
            )
        )
        if report.postgresql_plan is not None:
            postgresql_plan = report.postgresql_plan
            if report.postgresql_filesystem_plan is not None:
                commands.extend(self._filesystem_commands(report.postgresql_filesystem_plan))
                commands.append(
                    InstallationCommand(
                        "create PostgreSQL data symlink",
                        ("ln", "-sfn", "/data/openinfra", "/opt/openinfra/data"),
                    )
                )
            commands.extend(
                (
                    InstallationCommand(
                        "install PostgreSQL packages", postgresql_plan.install_command
                    ),
                    InstallationCommand(
                        "initialize PostgreSQL cluster", postgresql_plan.os_profile.initdb_command
                    ),
                    InstallationCommand(
                        "enable PostgreSQL service", postgresql_plan.enable_command
                    ),
                    InstallationCommand("start PostgreSQL service", postgresql_plan.start_command),
                    InstallationCommand(
                        "verify PostgreSQL readiness", postgresql_plan.verify_command
                    ),
                    InstallationCommand(
                        "render PostgreSQL HA and PITR configuration",
                        ("openinfra-internal", "postgresql-ha", "render"),
                    ),
                    InstallationCommand(
                        "prepare PostgreSQL PITR archive directory",
                        ("mkdir", "-p", "/data/openinfra/pitr"),
                    ),
                    InstallationCommand(
                        "prepare PostgreSQL physical backup directory",
                        ("mkdir", "-p", "/data/openinfra/backups"),
                    ),
                    InstallationCommand(
                        "apply backend migrations",
                        (
                            str(application_root / "venv/bin/openinfra"),
                            "database",
                            "apply-migrations",
                            "--root",
                            str(application_root / "share/migrations/postgresql"),
                        ),
                    ),
                )
            )
        if target_root == Path("/"):
            commands.extend(
                (
                    InstallationCommand("reload systemd", ("systemctl", "daemon-reload")),
                    InstallationCommand(
                        "enable OpenInfra service",
                        ("systemctl", "enable", report.service),
                    ),
                    InstallationCommand(
                        "restart OpenInfra service",
                        ("systemctl", "restart", report.service),
                    ),
                )
            )
        return tuple(commands)

    def _build_prerequisites(
        self, report: Any, target_root: Path
    ) -> tuple[InstallationPrerequisite, ...]:
        prerequisites = [
            InstallationPrerequisite("Python virtualenv support", "python3", True),
        ]
        if target_root == Path("/"):
            prerequisites.append(InstallationPrerequisite("systemd service manager", "systemctl"))
        if target_root == Path("/") and (
            report.application_filesystem_plan is not None
            or report.postgresql_filesystem_plan is not None
        ):
            prerequisites.extend(
                (
                    InstallationPrerequisite("LVM volume group inspection", "vgs"),
                    InstallationPrerequisite("LVM logical volume inspection", "lvs"),
                    InstallationPrerequisite("LVM logical volume creation", "lvcreate"),
                    InstallationPrerequisite("XFS filesystem creation", "mkfs.xfs"),
                    InstallationPrerequisite("mountpoint inspection", "mountpoint"),
                    InstallationPrerequisite("filesystem mount", "mount"),
                    InstallationPrerequisite("ownership management", "chown"),
                )
            )
        if report.postgresql_plan is not None:
            package_manager = report.postgresql_plan.os_profile.package_manager
            prerequisites.append(
                InstallationPrerequisite("PostgreSQL package manager", package_manager)
            )
            prerequisites.append(
                InstallationPrerequisite("PostgreSQL backup utility", "pg_basebackup")
            )
        return tuple(prerequisites)

    def _filesystem_commands(self, filesystem: Any) -> tuple[InstallationCommand, ...]:
        return (
            InstallationCommand(
                f"verify {filesystem.name} volume group", ("vgs", filesystem.vgname)
            ),
            InstallationCommand(
                f"create {filesystem.name} logical volume",
                (
                    "lvcreate",
                    "-L",
                    filesystem.lvsize,
                    "-n",
                    filesystem.lvname,
                    filesystem.vgname,
                ),
            ),
            InstallationCommand(
                f"format {filesystem.name} filesystem",
                ("mkfs.xfs", "-f", filesystem.lv_path),
            ),
            InstallationCommand(
                f"mount {filesystem.name} filesystem",
                ("mount", filesystem.lv_path, filesystem.mountpoint),
            ),
            InstallationCommand(
                f"set {filesystem.name} filesystem ownership",
                ("chown", "-R", f"{filesystem.owner}:{filesystem.group}", filesystem.mountpoint),
            ),
        )

    def _prepare_application_filesystem(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        if plan.application_filesystem is None:
            return
        self._ensure_system_account(
            username="openinfra",
            home=plan.application_filesystem.mountpoint,
            login_shell="/usr/sbin/nologin",
        )
        self._ensure_lvm_filesystem(plan.application_filesystem, journal)

    def _prepare_postgresql_filesystem(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> tuple[str, str] | None:
        if plan.postgresql_filesystem is None:
            return None
        account = self._resolve_or_create_postgresql_account(plan)
        filesystem = self._with_filesystem_owner(plan.postgresql_filesystem, account[0], account[1])
        self._ensure_lvm_filesystem(filesystem, journal)
        self._ensure_data_symlink(Path("/opt/openinfra/data"), Path(filesystem.mountpoint), journal)
        self._render_postgresql_pgdata_override(filesystem, journal)
        return account

    def _with_filesystem_owner(self, filesystem: Any, owner: str, group: str) -> Any:
        return type(filesystem)(
            name=filesystem.name,
            vgname=filesystem.vgname,
            lvname=filesystem.lvname,
            lvsize=filesystem.lvsize,
            filesystem=filesystem.filesystem,
            mountpoint=filesystem.mountpoint,
            owner=owner,
            group=group,
        )

    def _ensure_system_account(self, username: str, home: str, login_shell: str) -> None:
        if self._command_succeeds(("id", "-u", username)):
            return
        self._run_command(("useradd", "--system", "--home", home, "--shell", login_shell, username))

    def _resolve_or_create_postgresql_account(self, plan: InstallationPlan) -> tuple[str, str]:
        report = self._validator.validate_file(
            self._location.config_path,
            edition=plan.edition,
            scope=plan.scope,
        )
        postgresql_plan = report.postgresql_plan
        if postgresql_plan is None:
            return ("postgres", "postgres")
        users = postgresql_plan.os_profile.system_user_candidates
        groups = postgresql_plan.os_profile.system_group_candidates
        for username in users:
            if self._command_succeeds(("id", "-u", username)):
                group = self._first_existing_group(groups) or username
                return (username, group)
        username = users[0]
        group = groups[0]
        self._ensure_group(group)
        self._run_command(
            (
                "useradd",
                "--system",
                "--gid",
                group,
                "--home",
                "/data/openinfra",
                "--shell",
                "/usr/sbin/nologin",
                username,
            )
        )
        return (username, group)

    def _first_existing_group(self, groups: tuple[str, ...]) -> str | None:
        for group in groups:
            if self._command_succeeds(("getent", "group", group)):
                return group
        return None

    def _ensure_group(self, group: str) -> None:
        if self._command_succeeds(("getent", "group", group)):
            return
        self._run_command(("groupadd", "--system", group))

    def _ensure_lvm_filesystem(self, filesystem: Any, journal: InstallationRollbackJournal) -> None:
        self._run_command(("vgs", filesystem.vgname))
        lv_path = Path(filesystem.lv_path)
        if not self._command_succeeds(("lvs", filesystem.lv_path)) and not lv_path.exists():
            self._run_command(
                (
                    "lvcreate",
                    "-L",
                    filesystem.lvsize,
                    "-n",
                    filesystem.lvname,
                    filesystem.vgname,
                )
            )
        if not self._command_succeeds(("blkid", filesystem.lv_path)):
            self._run_command(("mkfs.xfs", "-f", filesystem.lv_path))
        mountpoint = Path(filesystem.mountpoint)
        self._create_directory(mountpoint, journal)
        self._ensure_fstab_entry(filesystem, journal)
        if not self._command_succeeds(("mountpoint", "-q", filesystem.mountpoint)):
            self._run_command(("mount", filesystem.lv_path, filesystem.mountpoint))
        self._run_command(
            ("chown", "-R", f"{filesystem.owner}:{filesystem.group}", filesystem.mountpoint)
        )

    def _ensure_fstab_entry(self, filesystem: Any, journal: InstallationRollbackJournal) -> None:
        path = Path("/etc/fstab")
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        marker = f"# openinfra:{filesystem.name}:{filesystem.mountpoint}"
        if marker in current:
            return
        line = (
            f"{filesystem.lv_path} {filesystem.mountpoint} {filesystem.filesystem} "
            "defaults,nodev,nosuid 0 2"
        )
        suffix = "" if current.endswith("\n") or not current else "\n"
        self._replace_text(path, current + suffix + marker + "\n" + line + "\n", 0o644, journal)

    def _ensure_data_symlink(
        self, link_path: Path, target: Path, journal: InstallationRollbackJournal
    ) -> None:
        if link_path.is_symlink() and link_path.resolve() == target:
            return
        if link_path.exists() or link_path.is_symlink():
            backup = self._backup_existing(link_path)
            journal.record_replacement(link_path, backup)
        self._create_directory(link_path.parent, journal)
        link_path.symlink_to(target)
        journal.record_replacement(link_path, None)

    def _render_postgresql_pgdata_override(
        self, filesystem: Any, journal: InstallationRollbackJournal
    ) -> None:
        override = Path("/etc/systemd/system/postgresql.service.d/openinfra-pgdata.conf")
        content = "\n".join(
            (
                "[Service]",
                f"Environment=PGDATA={filesystem.mountpoint}/",
                "",
            )
        )
        self._replace_text(override, content, 0o644, journal)

    def _render_postgresql_ha_configuration(
        self,
        plan: InstallationPlan,
        journal: InstallationRollbackJournal,
        account: tuple[str, str] | None,
    ) -> None:
        if plan.postgresql_ha is None:
            return
        ha_plan = plan.postgresql_ha
        pitr = Path(ha_plan.pitr_archive_directory)
        backups = Path(ha_plan.backup_directory)
        self._create_directory(pitr, journal)
        self._create_directory(backups, journal)
        if account is not None:
            self._run_command(("chown", "-R", f"{account[0]}:{account[1]}", str(pitr)))
            self._run_command(("chown", "-R", f"{account[0]}:{account[1]}", str(backups)))
        payload = json.dumps(ha_plan.as_dict(), sort_keys=True, indent=2) + "\n"
        self._replace_text(
            Path("/opt/openinfra/config/postgresql-ha.json"), payload, 0o640, journal
        )
        self._render_postgresql_conf_include(ha_plan, journal)

    def _render_postgresql_conf_include(
        self, ha_plan: Any, journal: InstallationRollbackJournal
    ) -> None:
        conf_dir = Path("/data/openinfra/conf.d")
        self._create_directory(conf_dir, journal)
        conf_file = conf_dir / "openinfra-ha.conf"
        content = "\n".join(ha_plan.postgresql_conf_lines()) + "\n"
        self._replace_text(conf_file, content, 0o640, journal)
        postgresql_conf = Path("/data/openinfra/postgresql.conf")
        if not postgresql_conf.exists():
            return
        current = postgresql_conf.read_text(encoding="utf-8")
        include_line = "include_dir = 'conf.d'"
        if include_line in current:
            return
        suffix = "" if current.endswith("\n") or not current else "\n"
        self._replace_text(
            postgresql_conf,
            current + suffix + "# openinfra managed HA/PITR include\n" + include_line + "\n",
            0o640,
            journal,
        )

    def _deploy_web_assets(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        if plan.scope not in {"all-in-one", "web"}:
            return
        web_source = self._location.project_root / "web"
        if web_source.is_dir():
            self._replace_tree(web_source, plan.application_root / "web", journal)

    def _run_postgresql_bootstrap(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        if plan.application_root != Path("/opt/openinfra"):
            return
        install_command = self._command_by_label(plan, "install PostgreSQL packages")
        if shutil.which("psql") is None and install_command is not None:
            self._run_command(install_command.command)
        account = self._prepare_postgresql_filesystem(plan, journal)
        init_command = self._command_by_label(plan, "initialize PostgreSQL cluster")
        if init_command is not None and not self._postgresql_cluster_is_initialized(plan):
            if account is not None and shutil.which("initdb") is not None:
                self._run_command(
                    ("runuser", "-u", account[0], "--", "initdb", "-D", "/data/openinfra")
                )
            elif shutil.which(init_command.command[0]) is not None:
                self._run_command(init_command.command)
        self._render_postgresql_ha_configuration(plan, journal, account)
        for label in (
            "enable PostgreSQL service",
            "start PostgreSQL service",
            "verify PostgreSQL readiness",
        ):
            command = self._command_by_label(plan, label)
            if command is not None:
                self._run_command(command.command)

    def _postgresql_cluster_is_initialized(self, plan: InstallationPlan) -> bool:
        for command in plan.commands:
            if command.label != "initialize PostgreSQL cluster":
                continue
            profile = self._validator.validate_file(
                self._location.config_path,
                edition=plan.edition,
                scope=plan.scope,
            ).postgresql_plan
            if profile is None:
                return True
            markers = ("/data/openinfra/PG_VERSION", *profile.os_profile.cluster_marker_paths)
            return any(Path(marker).exists() for marker in markers)
        return True

    def _assert_installation_lock_absent(self, plan: InstallationPlan) -> None:
        if plan.installation_lock_file.exists():
            raise InstallerRuntimeError(
                "OpenInfra is already installed for this target; remove "
                + str(plan.installation_lock_file)
                + " only after a controlled uninstall or rollback"
            )

    def _ensure_configuration_symlink(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        link = plan.compatibility_configuration_root
        target = Path("/opt/openinfra/config")
        self._create_directory(link.parent, journal)
        if link.is_symlink() and Path(os.readlink(link)) == target:
            return
        if link.exists() or link.is_symlink():
            backup = self._backup_existing(link)
            journal.record_replacement(link, backup)
        link.symlink_to(target)
        journal.record_replacement(link, None)

    def _render_runtime_configuration(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(self._location.config_path, encoding="utf-8")
        values: dict[str, str] = {
            "OPENINFRA_EDITION": plan.edition,
            "OPENINFRA_SCOPE": plan.scope,
            "OPENINFRA_SERVICE": plan.service_name,
            "OPENINFRA_APPLICATION_ROOT": "/opt/openinfra",
            "OPENINFRA_CONFIG_ROOT": "/opt/openinfra/config",
            "OPENINFRA_CONFIG_COMPAT_SYMLINK": "/etc/openinfra",
            "OPENINFRA_RUNTIME_CONFIG": "/opt/openinfra/config/openinfra.conf",
            "OPENINFRA_INSTALL_LOCK": "/opt/openinfra/config/.openinfra-installed.lock",
            "OPENINFRA_MIGRATIONS_ROOT": "/opt/openinfra/share/migrations/postgresql",
        }
        if plan.edition == "lite":
            values["OPENINFRA_DATABASE_DSN"] = "postgresql:///openinfra"
        self._add_performance_runtime_values(plan, values)
        if plan.scope in {"all-in-one", "web"}:
            self._add_web_runtime_values(parser, plan, values)
        for section in parser.sections():
            for key, value in parser.items(section):
                env_key = "OPENINFRA_INSTALL_" + section.upper() + "_" + key.upper()
                values[env_key] = self._sanitize_runtime_value(env_key, value)
        self._add_database_runtime_refs(parser, values)
        self._add_dotenv_runtime_values(values)
        content = "\n".join(
            (
                "# Managed by OpenInfra autonomous installer.",
                "# Canonical runtime path: /opt/openinfra/config/openinfra.conf.",
                "# Compatibility path: /etc/openinfra/openinfra.conf via /etc/openinfra symlink.",
                "# Secrets are stored as references only; cleartext secret values are forbidden.",
                *(
                    key + "=" + self._quote_environment_value(value)
                    for key, value in sorted(values.items())
                ),
                "",
            )
        )
        self._replace_text(plan.runtime_config_file, content, 0o640, journal)

    def _add_performance_runtime_values(
        self, plan: InstallationPlan, values: dict[str, str]
    ) -> None:
        database_defaults = {
            "lite": ("1", "1", "4", "20"),
            "pro": ("0", "1", "8", "80"),
            "enterprise": ("0", "2", "12", "192"),
        }
        web_worker_defaults = {"lite": "1", "pro": "0", "enterprise": "0"}
        api_workers, pool_min, pool_max, connection_budget = database_defaults[plan.edition]
        if plan.scope in {"all-in-one", "server"}:
            values.update(
                {
                    "OPENINFRA_API_RUNTIME": "asgi",
                    "OPENINFRA_API_WORKERS": api_workers,
                    "OPENINFRA_API_LIMIT_CONCURRENCY": "1000",
                    "OPENINFRA_API_BACKLOG": "2048",
                    "OPENINFRA_API_KEEPALIVE_SECONDS": "5",
                    "OPENINFRA_DB_POOL_MIN_SIZE": pool_min,
                    "OPENINFRA_DB_POOL_MAX_SIZE": pool_max,
                    "OPENINFRA_DB_POOL_TIMEOUT_SECONDS": "5",
                    "OPENINFRA_DB_POOL_MAX_IDLE_SECONDS": "300",
                    "OPENINFRA_DB_POOL_MAX_LIFETIME_SECONDS": "1800",
                    "OPENINFRA_DB_CONNECTION_BUDGET": connection_budget,
                }
            )
        if plan.scope in {"all-in-one", "web"}:
            http_defaults = {
                "lite": ("32", "8"),
                "pro": ("200", "50"),
                "enterprise": ("500", "100"),
            }
            max_connections, max_keepalive = http_defaults[plan.edition]
            values.update(
                {
                    "OPENINFRA_WEB_RUNTIME": "asgi",
                    "OPENINFRA_WEB_WORKERS": web_worker_defaults[plan.edition],
                    "OPENINFRA_WEB_LIMIT_CONCURRENCY": "1000",
                    "OPENINFRA_WEB_BACKLOG": "2048",
                    "OPENINFRA_WEB_KEEPALIVE_SECONDS": "5",
                    "OPENINFRA_WEB_HTTP_MAX_CONNECTIONS": max_connections,
                    "OPENINFRA_WEB_HTTP_MAX_KEEPALIVE_CONNECTIONS": max_keepalive,
                    "OPENINFRA_WEB_HTTP_KEEPALIVE_EXPIRY_SECONDS": "30",
                    "OPENINFRA_WEB_HTTP_CONNECT_TIMEOUT_SECONDS": "2",
                    "OPENINFRA_WEB_HTTP_READ_TIMEOUT_SECONDS": "30",
                    "OPENINFRA_WEB_HTTP_WRITE_TIMEOUT_SECONDS": "30",
                    "OPENINFRA_WEB_HTTP_POOL_TIMEOUT_SECONDS": "2",
                }
            )

    def _add_web_runtime_values(
        self, parser: configparser.ConfigParser, plan: InstallationPlan, values: dict[str, str]
    ) -> None:
        values["OPENINFRA_WEB_HOST"] = "127.0.0.1"
        values["OPENINFRA_WEB_PORT"] = "2006"
        values["OPENINFRA_WEB_PUBLIC_API_BASE_URL"] = "/api"
        values["OPENINFRA_WEB_STATIC_ROOT"] = (
            "/opt/openinfra/src/openinfra/interfaces/rendering/static"
        )
        values["OPENINFRA_WEB_AUTH_MODE"] = parser.get("auth", "mode", fallback="standard").strip()
        if plan.scope == "web":
            values["OPENINFRA_WEB_BACKEND_URL"] = parser.get(
                "api", "backend_endpoint", fallback=""
            ).strip()
        else:
            values["OPENINFRA_WEB_BACKEND_URL"] = "http://127.0.0.1:8080"
            values["OPENINFRA_WEB_ALLOW_INSECURE_BACKEND"] = "true"
        self._add_web_database_runtime_values(parser, values)

    def _add_web_database_runtime_values(
        self, parser: configparser.ConfigParser, values: dict[str, str]
    ) -> None:
        if not parser.has_section("web_database"):
            return
        for ini_key, env_key in (
            ("postgresql_dsn_ref", "OPENINFRA_WEB_DATABASE_DSN_REF"),
            ("postgresql_user_ref", "OPENINFRA_WEB_DATABASE_USER_REF"),
            ("postgresql_password_ref", "OPENINFRA_WEB_DATABASE_PASSWORD_REF"),
        ):
            value = parser.get("web_database", ini_key, fallback="").strip()
            if value:
                values[env_key] = self._sanitize_runtime_value(env_key, value)

    def _add_database_runtime_refs(
        self, parser: configparser.ConfigParser, values: dict[str, str]
    ) -> None:
        if not parser.has_section("auth"):
            return
        dsn_ref = parser.get("auth", "postgresql_dsn_ref", fallback="").strip()
        user_ref = parser.get("auth", "postgresql_user_ref", fallback="").strip()
        password_ref = parser.get("auth", "postgresql_password_ref", fallback="").strip()
        if dsn_ref:
            values["OPENINFRA_DATABASE_DSN_REF"] = self._sanitize_runtime_value(
                "OPENINFRA_DATABASE_DSN_REF", dsn_ref
            )
        if user_ref:
            values["OPENINFRA_POSTGRES_USER_REF"] = self._sanitize_runtime_value(
                "OPENINFRA_POSTGRES_USER_REF", user_ref
            )
        if password_ref:
            values["OPENINFRA_POSTGRES_PASSWORD_REF"] = self._sanitize_runtime_value(
                "OPENINFRA_POSTGRES_PASSWORD_REF", password_ref
            )

    def _add_dotenv_runtime_values(self, values: dict[str, str]) -> None:
        dotenv = self._location.project_root / ".env"
        if not dotenv.is_file():
            return
        for raw_line in dotenv.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            normalized_key = key.strip()
            if not normalized_key.startswith("OPENINFRA_"):
                continue
            value = value.strip().strip("'\"")
            values[normalized_key] = self._sanitize_runtime_value(normalized_key, value)

    def _sanitize_runtime_value(self, key: str, value: str) -> str:
        normalized = value.strip()
        if not self._looks_sensitive(key):
            return normalized
        if normalized.startswith(("env:", "vault://", "sops://", "file://", "kms://")):
            return normalized
        if key.startswith("OPENINFRA_"):
            return "env:" + key
        raise InstallerRuntimeError("refusing to materialize cleartext secret in openinfra.conf")

    def _looks_sensitive(self, key: str) -> bool:
        lowered = key.lower()
        return any(marker in lowered for marker in ("password", "secret", "token", "key"))

    def _quote_environment_value(self, value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return '"' + escaped + '"'

    def _write_installation_lock(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        content = "\n".join(
            (
                "edition=" + plan.edition,
                "scope=" + plan.scope,
                "service=" + plan.service_name,
                "installed_at=" + datetime.now(UTC).isoformat(),
                "runtime_config=/opt/openinfra/config/openinfra.conf",
                "",
            )
        )
        self._replace_text(plan.installation_lock_file, content, 0o640, journal)

    def _prepare_python_runtime(
        self, plan: InstallationPlan, journal: InstallationRollbackJournal
    ) -> None:
        if plan.application_root != Path("/opt/openinfra"):
            return
        venv = plan.application_root / "venv"
        if not venv.exists():
            journal.record_replacement(venv, None)
        for label in (
            "create Python virtual environment",
            "install scope production requirements",
            "install OpenInfra application package",
        ):
            command = self._command_by_label(plan, label)
            if command is not None:
                self._run_command(command.command)

    def _command_by_label(self, plan: InstallationPlan, label: str) -> InstallationCommand | None:
        for command in plan.commands:
            if command.label == label:
                return command
        return None

    def _resolve_database_dsn(self, plan: InstallationPlan) -> str:
        direct = os.environ.get("OPENINFRA_DATABASE_DSN", "").strip()
        if direct:
            return direct
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(self._location.config_path, encoding="utf-8")
        if parser.has_option("auth", "postgresql_dsn_ref"):
            return self._resolve_secret_reference(parser.get("auth", "postgresql_dsn_ref"))
        if parser.has_option("auth", "postgresql_user_ref") and parser.has_option(
            "auth", "postgresql_password_ref"
        ):
            username = self._resolve_secret_reference(parser.get("auth", "postgresql_user_ref"))
            credential_value = self._resolve_secret_reference(
                parser.get("auth", "postgresql_password_ref")
            )
            return (
                "postgresql://"
                + quote(username, safe="")
                + ":"
                + quote(credential_value, safe="")
                + "@127.0.0.1:5432/openinfra"
            )
        if plan.edition == "lite":
            return "postgresql:///openinfra"
        raise InstallerRuntimeError(
            "PostgreSQL DSN cannot be resolved; set OPENINFRA_DATABASE_DSN "
            "or env refs from install.ini"
        )

    def _resolve_secret_reference(self, raw_reference: str) -> str:
        reference = raw_reference.strip()
        if reference.startswith("env:"):
            name = reference.removeprefix("env:").strip()
            value = os.environ.get(name, "")
            if not value:
                raise InstallerRuntimeError("missing environment secret reference: " + name)
            return value
        if reference.startswith("file://"):
            path = Path(reference.removeprefix("file://"))
            if not path.is_file():
                raise InstallerRuntimeError("missing file secret reference: " + str(path))
            return path.read_text(encoding="utf-8").strip()
        raise InstallerRuntimeError(
            "unsupported runtime secret reference for autonomous installer: "
            + reference.split(":", 1)[0]
        )

    def _assert_supported_execute_target(self, plan: InstallationPlan) -> None:
        if plan.application_root == Path("/opt/openinfra") and os.geteuid() != 0:
            raise InstallerRuntimeError("execute mode on / requires root privileges")

    def _assert_prerequisites(self, plan: InstallationPlan, skip_service_enable: bool) -> None:
        missing_sources = (
            self._location.project_root / "src",
            self._location.installers_root / "requirements" / plan.requirements_file,
            self._location.project_root / "pyproject.toml",
        )
        missing = [str(path) for path in missing_sources if not path.exists()]
        if plan.deploy_migrations:
            migrations_root = self._location.installers_root / "migrations" / "postgresql"
            if not migrations_root.is_dir() or not any(migrations_root.glob("*.sql")):
                missing.append(str(migrations_root))
        if missing:
            raise InstallerRuntimeError("missing installer payload: " + ", ".join(missing))
        for prerequisite in plan.prerequisites:
            if skip_service_enable and not prerequisite.mandatory_on_offline_target:
                continue
            if shutil.which(prerequisite.executable) is None:
                raise InstallerRuntimeError(
                    f"missing prerequisite {prerequisite.label}: {prerequisite.executable}"
                )

    def _target_path(self, target_root: Path, absolute: str) -> Path:
        normalized = Path(absolute)
        relative = normalized.relative_to("/")
        return target_root.resolve() / relative if target_root != Path("/") else normalized

    def _create_directory(self, path: Path, journal: InstallationRollbackJournal) -> None:
        missing: list[Path] = []
        current = path
        while not current.exists():
            missing.append(current)
            current = current.parent
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o750)
        for created in reversed(missing):
            journal.record_created_directory(created)

    def _replace_tree(
        self, source: Path, destination: Path, journal: InstallationRollbackJournal
    ) -> None:
        if not source.is_dir():
            raise InstallerRuntimeError(f"missing source directory: {source}")
        self._create_directory(destination.parent, journal)
        temporary = self._temporary_path(destination)
        backup = self._backup_existing(destination)
        shutil.copytree(source, temporary)
        temporary.replace(destination)
        journal.record_replacement(destination, backup)

    def _replace_file(
        self, source: Path, destination: Path, mode: int, journal: InstallationRollbackJournal
    ) -> None:
        if not source.is_file():
            raise InstallerRuntimeError(f"missing source file: {source}")
        self._create_directory(destination.parent, journal)
        temporary = self._temporary_path(destination)
        shutil.copy2(source, temporary)
        os.chmod(temporary, mode)
        backup = self._backup_existing(destination)
        temporary.replace(destination)
        journal.record_replacement(destination, backup)

    def _replace_text(
        self, destination: Path, content: str, mode: int, journal: InstallationRollbackJournal
    ) -> None:
        self._create_directory(destination.parent, journal)
        temporary = self._temporary_path(destination)
        temporary.write_text(content, encoding="utf-8")
        os.chmod(temporary, mode)
        backup = self._backup_existing(destination)
        temporary.replace(destination)
        journal.record_replacement(destination, backup)

    def _temporary_path(self, destination: Path) -> Path:
        counter = 0
        while True:
            candidate = destination.with_name(
                f".{destination.name}.openinfra-tmp-{os.getpid()}-{counter}"
            )
            if not candidate.exists():
                return candidate
            counter += 1

    def _backup_existing(self, destination: Path) -> Path | None:
        if not destination.exists() and not destination.is_symlink():
            return None
        backup_root = destination.parent / ".openinfra-rollback"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / f"{destination.name}.bak"
        counter = 0
        while backup.exists():
            counter += 1
            backup = backup_root / f"{destination.name}.{counter}.bak"
        destination.replace(backup)
        return backup

    def _command_succeeds(self, command: tuple[str, ...]) -> bool:
        executable = shutil.which(command[0]) if "/" not in command[0] else command[0]
        if executable is None or not Path(executable).exists():
            return False
        completed = subprocess.run(
            (executable, *command[1:]),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )  # nosec B603
        return completed.returncode == 0

    def _run_command(
        self, command: tuple[str, ...], environment: dict[str, str] | None = None
    ) -> None:
        executable = shutil.which(command[0]) if "/" not in command[0] else command[0]
        if executable is None or not Path(executable).exists():
            raise InstallerRuntimeError("missing required executable: " + command[0])
        resolved = (executable, *command[1:])
        runtime_environment = os.environ.copy()
        if environment:
            runtime_environment.update(environment)
        completed = subprocess.run(resolved, check=False, env=runtime_environment, text=True)  # nosec B603
        if completed.returncode != 0:
            raise InstallerRuntimeError("command failed: " + " ".join(command))

    def _emit(self, plan: InstallationPlan, executed: bool, json_output: bool) -> int:
        payload = {"executed": executed, "plan": plan.as_dict()}
        if json_output:
            print(json.dumps(payload, sort_keys=True, indent=2))
        else:
            status = "EXECUTED" if executed else "DRY-RUN"
            print(f"{status} {plan.edition}/{plan.scope} -> {plan.application_root}")
            for action in plan.actions:
                print(f"- {action}")
        return 0

    def _emit_payload(self, payload: dict[str, object], json_output: bool) -> int:
        if json_output:
            print(json.dumps(payload, sort_keys=True, indent=2))
        else:
            count = payload.get("count", 0)
            print(f"ROLLBACK restored={count}")
            for restored in payload.get("rolled_back", []):
                print(f"- {restored}")
        return 0


if __name__ == "__main__":
    raise SystemExit(AutonomousInstallerProgram(Path(__file__)).main())
