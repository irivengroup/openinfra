from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_enterprise_alignment import EnterpriseAlignmentValidator

from openinfra.infrastructure.installer_config import InstallerConfigValidator
from openinfra.interfaces.cli import OpenInfraCLI


class TestInstallerAlignment:
    def test_all_installer_install_ini_files_are_valid_and_minimal(self) -> None:
        report = InstallerConfigValidator().validate_tree(Path("installers"))

        assert report.valid is True
        assert len(report.reports) == 6
        assert not report.missing_paths
        assert not report.unexpected_paths
        configs = {
            item.path.as_posix(): item.path.read_text(encoding="utf-8") for item in report.reports
        }
        assert configs["installers/setup/lite/install.ini"].strip().startswith("[storage]")
        assert "[api]" not in configs["installers/setup/lite/install.ini"]
        assert "central_endpoint" not in "\n".join(configs.values())
        assert "[operations]" not in "\n".join(configs.values())
        assert "edition =" not in "\n".join(configs.values())
        assert "scope =" not in "\n".join(configs.values())
        assert "service =" not in "\n".join(configs.values())
        assert any(
            "installers/migrations/postgresql" in action
            for item in report.reports
            for action in item.actions
        )
        assert any(
            "without direct database access" in action
            for item in report.reports
            for action in item.actions
        )
        enterprise_server = next(
            item
            for item in report.reports
            if item.edition == "enterprise" and item.scope == "server"
        )
        assert enterprise_server.postgresql_ha_plan is not None
        assert enterprise_server.postgresql_ha_plan.replication_enabled is True
        assert enterprise_server.postgresql_ha_plan.cluster_sync_port == 2008
        assert "ANY 1" in enterprise_server.postgresql_ha_plan.synchronous_standby_names
        lite = next(item for item in report.reports if item.edition == "lite")
        assert lite.postgresql_ha_plan is not None
        assert lite.postgresql_ha_plan.replication_enabled is False
        assert lite.postgresql_ha_plan.backup_directory == "/data/openinfra/backups"

    def test_installer_validator_rejects_web_scope_storage(self, tmp_path: Path) -> None:
        source = Path("installers/setup/pro/web/install.ini")
        target = tmp_path / "install.ini"
        target.write_text(
            source.read_text(encoding="utf-8")
            + "\n[storage]\nvgname = datavg\nlvname = openinfradata_lv\nlvsize = 10GB\n",
            encoding="utf-8",
        )

        report = InstallerConfigValidator().validate_file(target, edition="pro", scope="web")

        assert report.valid is False
        assert any("must not expose PostgreSQL storage" in error for error in report.errors)

    def test_installer_validator_rejects_clear_secret(self, tmp_path: Path) -> None:
        source = Path("installers/setup/pro/server/install.ini")
        target = tmp_path / "install.ini"
        target.write_text(
            source.read_text(encoding="utf-8").replace(
                "postgresql_password_ref = env:OPENINFRA_POSTGRES_PASSWORD",
                "postgresql_password_ref = ChangeMe123456789",
            ),
            encoding="utf-8",
        )

        report = InstallerConfigValidator().validate_file(target, edition="pro", scope="server")

        assert report.valid is False
        assert any("postgresql_password_ref" in error for error in report.errors)

    def test_cli_installer_validate_dry_run_and_systemd_render(self, capsys: object) -> None:
        validate_code = OpenInfraCLI().run(["installer", "validate", "--root", "installers"])
        validate_payload = json.loads(capsys.readouterr().out)
        dry_run_code = OpenInfraCLI().run(["installer", "dry-run", "--root", "installers"])
        dry_run_payload = json.loads(capsys.readouterr().out)
        render_code = OpenInfraCLI().run(
            ["installer", "render-systemd", "--edition", "enterprise", "--scope", "agent"]
        )
        unit_payload = capsys.readouterr().out
        ha_code = OpenInfraCLI().run(
            [
                "database",
                "ha-plan",
                "--path",
                "installers/setup/enterprise/server/install.ini",
                "--edition",
                "enterprise",
                "--scope",
                "server",
            ]
        )
        ha_payload = json.loads(capsys.readouterr().out)

        assert validate_code == 0
        assert validate_payload["valid"] is True
        assert dry_run_code == 0
        assert dry_run_payload["dry_run"] is True
        assert dry_run_payload["writes_performed"] is False
        assert render_code == 0
        assert ha_code == 0
        assert ha_payload["postgresql_ha"]["replication_enabled"] is True
        assert ha_payload["postgresql_ha"]["cluster_sync_port"] == 2008
        assert "openinfra-agent.service" in unit_payload
        assert "NoNewPrivileges=true" in unit_payload
        assert "PrivateDevices=true" in unit_payload
        assert "CapabilityBoundingSet=" in unit_payload

    def test_installer_embeds_single_migration_source_and_prod_requirements_by_scope(self) -> None:
        installer_migrations = sorted(Path("installers/migrations/postgresql").glob("*.sql"))
        requirements = sorted(Path("installers/requirements").glob("*.txt"))
        combined_requirements = "\n".join(path.read_text(encoding="utf-8") for path in requirements)

        assert not Path("migrations").exists()
        assert len(installer_migrations) == 24
        assert installer_migrations[0].name == "0001_bootstrap.sql"
        assert installer_migrations[-1].name == "0024_postgresql_ha_backup_registry.sql"
        assert "psycopg[binary]" in combined_requirements
        forbidden_dev_tools = ("pytest", "ruff", "mypy", "bandit", "pip-audit", "build")
        assert not any(tool in combined_requirements for tool in forbidden_dev_tools)

    def test_enterprise_alignment_validator_accepts_cdc_v481_and_roadmap_v2(self) -> None:
        report = EnterpriseAlignmentValidator().validate(
            Path("docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1"),
            Path("docs/specifications/OpenInfra-Roadmap-Developpement-v2"),
            Path(),
        )

        assert report.valid is True
