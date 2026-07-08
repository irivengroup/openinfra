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
            "/opt/openinfra/share/migrations/postgresql" in action
            for item in report.reports
            for action in item.actions
        )
        assert any(
            "/opt/openinfra/config/openinfra.conf" in action
            for item in report.reports
            for action in item.actions
        )
        assert any("mandatory mTLS" in action for item in report.reports for action in item.actions)
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
        assert enterprise_server.postgresql_ha_plan.commit_policy == "local_commit_non_blocking"
        assert enterprise_server.postgresql_ha_plan.topology == "near-real-time-streaming-cluster"
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
        assert len(installer_migrations) == 29
        assert installer_migrations[0].name == "0001_bootstrap.sql"
        assert installer_migrations[-1].name == "0029_itam_tenant_lifecycle.sql"
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

    def test_installer_auth_policy_keeps_backend_api_only_and_allows_web_ldap(
        self, tmp_path: Path
    ) -> None:
        ldap_payload = "\n".join(
            (
                "mode = ldap",
                "directory_url = ldaps://ldap.example.net:636",
                "base_dn = dc=example,dc=net",
                "user_filter = (uid={username})",
                "group_filter = (member={user_dn})",
                "bind_dn_ref = env:OPENINFRA_LDAP_BIND_DN",
                "bind_password_ref = env:OPENINFRA_LDAP_BIND_PASSWORD",
                "ca_cert_ref = file:///opt/openinfra/config/trust/ldap-ca.pem",
                "cache_ttl_seconds = 300",
            )
        )
        ldap_server = tmp_path / "server-install.ini"
        ldap_server.write_text(
            Path("installers/setup/pro/server/install.ini")
            .read_text(encoding="utf-8")
            .replace("mode = standard", ldap_payload),
            encoding="utf-8",
        )
        ldap_web = tmp_path / "web-install.ini"
        ldap_web.write_text(
            Path("installers/setup/pro/web/install.ini")
            .read_text(encoding="utf-8")
            .replace("mode = standard", ldap_payload),
            encoding="utf-8",
        )

        server_report = InstallerConfigValidator().validate_file(
            ldap_server, edition="pro", scope="server"
        )
        web_report = InstallerConfigValidator().validate_file(ldap_web, edition="pro", scope="web")

        assert server_report.valid is False
        assert any(
            "backend API must not authenticate human operators" in error
            for error in server_report.errors
        )
        assert web_report.valid is True
        assert any(
            "operator LDAP/IPA login is frontend-scoped" in action for action in web_report.actions
        )

    def test_cli_auth_policy_rejects_lite_ldap_and_accepts_enterprise_ipa(
        self, capsys: object
    ) -> None:
        lite_code = OpenInfraCLI().run(
            [
                "auth",
                "policy",
                "--edition",
                "lite",
                "--mode",
                "ldap",
                "--url",
                "ldaps://ldap.example.net",
                "--base-dn",
                "dc=example,dc=net",
            ]
        )
        lite_err = capsys.readouterr().err
        enterprise_code = OpenInfraCLI().run(
            [
                "auth",
                "policy",
                "--edition",
                "enterprise",
                "--mode",
                "ipa",
                "--url",
                "ldaps://ipa.example.net",
                "--base-dn",
                "dc=example,dc=net",
                "--bind-dn-ref",
                "env:OPENINFRA_IPA_BIND_DN",
                "--bind-password-ref",
                "env:OPENINFRA_IPA_BIND_PASSWORD",
            ]
        )
        payload = json.loads(capsys.readouterr().out)

        assert lite_code == 2
        assert "Lite edition supports local standard authentication only" in lite_err
        assert enterprise_code == 0
        assert payload["mode"] == "ipa"
        assert payload["external_directory_enabled"] is True
