from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest


class InstallerRuntimeModule:
    def load(self) -> ModuleType:
        module_path = Path("installers/setup/installer_runtime.py").resolve()
        spec = importlib.util.spec_from_file_location("openinfra_installer_runtime", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load installers/setup/installer_runtime.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


class TestAutonomousScopeInstallers:
    def test_setup_tree_is_the_only_installer_entrypoint_layout(self) -> None:
        expected = (
            Path("installers/setup/lite"),
            Path("installers/setup/pro/server"),
            Path("installers/setup/pro/web"),
            Path("installers/setup/enterprise/server"),
            Path("installers/setup/enterprise/web"),
            Path("installers/setup/enterprise/agent"),
        )

        for scope_root in expected:
            assert (scope_root / "install.ini").is_file()
            assert (scope_root / "install.py").is_file()
        for forbidden in (
            Path("installers/lite"),
            Path("installers/pro"),
            Path("installers/enterprise"),
            Path("installers/setup/entreprise"),
        ):
            assert not forbidden.exists()

    def test_autonomous_programs_build_scope_specific_plans(self, tmp_path: Path) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram
        installers = {
            ("lite", "all-in-one"): Path("installers/setup/lite/install.py"),
            ("pro", "server"): Path("installers/setup/pro/server/install.py"),
            ("pro", "web"): Path("installers/setup/pro/web/install.py"),
            ("enterprise", "server"): Path("installers/setup/enterprise/server/install.py"),
            ("enterprise", "web"): Path("installers/setup/enterprise/web/install.py"),
            ("enterprise", "agent"): Path("installers/setup/enterprise/agent/install.py"),
        }

        for (edition, scope), entrypoint in installers.items():
            plan = program_cls(entrypoint).build_plan(tmp_path)

            assert plan.edition == edition
            assert plan.scope == scope
            assert plan.deploy_src is True
            assert plan.deploy_requirements is True
            assert plan.application_root == tmp_path / "opt/openinfra"
            if scope in {"all-in-one", "server"}:
                assert plan.deploy_migrations is True
                assert plan.managed_postgresql is True
            else:
                assert plan.deploy_migrations is False
                assert plan.managed_postgresql is False
            command_labels = {command.label for command in plan.commands}
            assert plan.managed_application_filesystem is True
            assert plan.application_filesystem is not None
            assert "create application logical volume" in command_labels
            assert "mount application filesystem" in command_labels
            if scope in {"all-in-one", "server"}:
                assert plan.postgresql_filesystem is not None
                assert plan.postgresql_ha is not None
                assert "create postgresql logical volume" in command_labels
                assert "create PostgreSQL data symlink" in command_labels
                assert "render PostgreSQL HA and PITR configuration" in command_labels
                assert "prepare PostgreSQL PITR archive directory" in command_labels
                assert "prepare PostgreSQL physical backup directory" in command_labels
                if edition == "enterprise" and scope == "server":
                    assert plan.postgresql_ha.replication_enabled is True
                    assert plan.postgresql_ha.topology == "near-real-time-streaming-cluster"
                else:
                    assert plan.postgresql_ha.replication_enabled is False
            else:
                assert plan.postgresql_filesystem is None
                assert plan.postgresql_ha is None
                assert "create postgresql logical volume" not in command_labels
                assert "create PostgreSQL data symlink" not in command_labels
                assert "render PostgreSQL HA and PITR configuration" not in command_labels

    def test_execute_to_offline_target_deploys_src_requirements_and_scoped_assets(
        self, tmp_path: Path
    ) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram

        lite_installer = program_cls(Path("installers/setup/lite/install.py"))
        lite_plan = lite_installer.build_plan(tmp_path / "lite-target")
        lite_installer.execute(lite_plan, skip_service_enable=True)

        lite_app = tmp_path / "lite-target/opt/openinfra"
        assert (lite_app / "src/openinfra").is_dir()
        assert (lite_app / "requirements/lite-all-in-one.txt").is_file()
        assert (lite_app / "installers/migrations/postgresql/0001_bootstrap.sql").is_file()
        assert (
            lite_app / "installers/migrations/postgresql/0024_postgresql_ha_backup_registry.sql"
        ).is_file()
        assert (tmp_path / "lite-target/etc/openinfra/install-lite-all-in-one.ini").is_file()
        assert (tmp_path / "lite-target/etc/systemd/system/openinfra.service").is_file()

        agent_installer = program_cls(Path("installers/setup/enterprise/agent/install.py"))
        agent_plan = agent_installer.build_plan(tmp_path / "agent-target")
        agent_installer.execute(agent_plan, skip_service_enable=True)

        agent_app = tmp_path / "agent-target/opt/openinfra"
        assert (agent_app / "src/openinfra").is_dir()
        assert (agent_app / "requirements/enterprise-agent.txt").is_file()
        assert not (agent_app / "installers/migrations").exists()
        assert (tmp_path / "agent-target/etc/openinfra/install-enterprise-agent.ini").is_file()
        agent_unit = tmp_path / "agent-target/etc/systemd/system/openinfra-agent.service"
        assert agent_unit.is_file()
        assert "WorkingDirectory=/opt/openinfra" in agent_unit.read_text(encoding="utf-8")

    def test_plans_include_runtime_bootstrap_prerequisites_and_rollback(
        self, tmp_path: Path
    ) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram

        server_plan = program_cls(Path("installers/setup/pro/server/install.py")).build_plan(
            tmp_path
        )
        agent_plan = program_cls(Path("installers/setup/enterprise/agent/install.py")).build_plan(
            tmp_path
        )

        server_labels = {command.label for command in server_plan.commands}
        prerequisite_bins = {item.executable for item in server_plan.prerequisites}
        agent_labels = {command.label for command in agent_plan.commands}

        assert server_plan.transactional_rollback is True
        assert server_plan.start_service is False
        assert "python3" in prerequisite_bins
        assert prerequisite_bins & {"dnf", "apt-get", "zypper"}
        assert "create Python virtual environment" in server_labels
        assert "install scope production requirements" in server_labels
        assert "install OpenInfra application package" in server_labels
        assert "apply backend migrations" in server_labels
        assert "apply backend migrations" not in agent_labels
        assert agent_plan.transactional_rollback is True

    def test_offline_execution_rolls_back_created_payload_after_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram
        runtime_error = cast(Any, module).InstallerRuntimeError
        installer = program_cls(Path("installers/setup/lite/install.py"))
        plan = installer.build_plan(tmp_path / "rollback-target")

        def fail_after_first_tree(*_args: object, **_kwargs: object) -> None:
            raise runtime_error("forced copy failure")

        monkeypatch.setattr(installer, "_replace_file", fail_after_first_tree)

        with pytest.raises(runtime_error):
            installer.execute(plan, skip_service_enable=True)

        assert not (tmp_path / "rollback-target/opt/openinfra/src").exists()
        assert not (tmp_path / "rollback-target/opt/openinfra/requirements").exists()

    def test_backend_migration_dsn_is_resolved_from_secret_refs_without_cli_exposure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram
        installer = program_cls(Path("installers/setup/pro/server/install.py"))
        plan = installer.build_plan(Path("/"))
        recorded: list[tuple[tuple[str, ...], dict[str, str] | None]] = []

        monkeypatch.setenv("OPENINFRA_POSTGRES_USER", "openinfra")
        monkeypatch.setenv("OPENINFRA_POSTGRES_PASSWORD", "secret:value")

        def record_command(
            command: tuple[str, ...], environment: dict[str, str] | None = None
        ) -> None:
            recorded.append((command, environment))

        monkeypatch.setattr(installer, "_run_command", record_command)

        installer.execute_migrations(plan)

        command, environment = recorded[0]
        assert "--postgres-dsn" not in command
        assert environment is not None
        assert environment["OPENINFRA_DATABASE_DSN"] == (
            "postgresql://openinfra:secret%3Avalue@127.0.0.1:5432/openinfra"
        )

    def test_missing_backend_secret_reference_is_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram
        runtime_error = cast(Any, module).InstallerRuntimeError
        installer = program_cls(Path("installers/setup/pro/server/install.py"))
        plan = installer.build_plan(Path("/"))

        monkeypatch.delenv("OPENINFRA_DATABASE_DSN", raising=False)
        monkeypatch.delenv("OPENINFRA_POSTGRES_USER", raising=False)
        monkeypatch.delenv("OPENINFRA_POSTGRES_PASSWORD", raising=False)

        with pytest.raises(runtime_error):
            installer.execute_migrations(plan)

    def test_manual_rollback_restores_stale_backups(self, tmp_path: Path) -> None:
        module = InstallerRuntimeModule().load()
        rollback_manager = cast(Any, module).RollbackManager()
        root = tmp_path / "image"
        destination = root / "opt/openinfra/src"
        backup_root = root / "opt/openinfra/.openinfra-rollback"
        destination.mkdir(parents=True)
        (destination / "old.txt").write_text("old", encoding="utf-8")
        backup = backup_root / "src.bak"
        backup.mkdir(parents=True)
        (backup / "restored.txt").write_text("restored", encoding="utf-8")

        result = rollback_manager.rollback_target(root)

        assert result["count"] == 1
        assert not (destination / "old.txt").exists()
        assert (destination / "restored.txt").read_text(encoding="utf-8") == "restored"

    def test_legacy_french_enterprise_directory_is_rejected(self, tmp_path: Path) -> None:
        module = InstallerRuntimeModule().load()
        program_cls = cast(Any, module).AutonomousInstallerProgram
        runtime_error = cast(Any, module).InstallerRuntimeError
        legacy_root = tmp_path / "installers/setup/entreprise/agent"
        legacy_root.mkdir(parents=True)
        entrypoint = legacy_root / "install.py"
        entrypoint.write_text("", encoding="utf-8")
        (legacy_root.parent.parent / "installer_runtime.py").write_text("", encoding="utf-8")

        try:
            program_cls(entrypoint)
        except runtime_error as exc:
            assert "installers/setup/enterprise/<scope>" in str(exc)
        else:
            raise AssertionError("legacy installers/setup/entreprise must be rejected")
