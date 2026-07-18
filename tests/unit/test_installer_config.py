from __future__ import annotations

import configparser
from dataclasses import replace
from pathlib import Path

import pytest

from openinfra.domain.common import ValidationError
from openinfra.infrastructure.installer_config import (
    InstallerConfigValidator,
    InstallerOsCatalog,
    InstallerPostgreSQLDeploymentPlanner,
    InstallerScopeCatalog,
)


class TestInstallerConfigDomain:
    def _copy_config(self, source: str, target: Path) -> Path:
        path = target / "install.ini"
        path.write_text(Path(source).read_text(encoding="utf-8"), encoding="utf-8")
        return path

    def test_catalog_normalizes_scope_keys_and_lists_policies(self) -> None:
        catalog = InstallerScopeCatalog()

        policy = catalog.policy_for(" Pro ", " Web ")

        assert policy is not None
        assert policy.service == "openinfra-web.service"
        assert len(catalog.policies()) == 6
        assert "setup/pro/web/install.ini" in catalog.expected_config_paths()

    def test_missing_file_is_invalid(self, tmp_path: Path) -> None:
        report = InstallerConfigValidator().validate_file(
            tmp_path / "missing.ini", edition="lite", scope="all-in-one"
        )

        assert report.valid is False
        assert report.edition == "lite"
        assert any("missing install.ini" in error for error in report.errors)

    def test_missing_sections_and_options_are_reported(self, tmp_path: Path) -> None:
        config = tmp_path / "install.ini"
        config.write_text("[storage]\nvgname = datavg\n", encoding="utf-8")

        report = InstallerConfigValidator().validate_file(
            config, edition="lite", scope="all-in-one"
        )

        assert report.valid is False
        assert any("missing option: storage.lvname" in error for error in report.errors)
        assert any("missing option: storage.lvsize" in error for error in report.errors)

    def test_invalid_edition_scope_and_uninferable_path_are_rejected(self, tmp_path: Path) -> None:
        config = self._copy_config("installers/setup/lite/install.ini", tmp_path)

        explicit_report = InstallerConfigValidator().validate_file(
            config, edition="unknown", scope="all-in-one"
        )
        inferred_report = InstallerConfigValidator().validate_file(config)

        assert explicit_report.valid is False
        assert inferred_report.valid is False
        assert any("cannot infer supported installer" in error for error in explicit_report.errors)
        assert any("cannot infer supported installer" in error for error in inferred_report.errors)
        assert inferred_report.actions == ()

    def test_policy_schema_storage_and_identity_errors_are_reported(self, tmp_path: Path) -> None:
        config = self._copy_config("installers/setup/pro/server/install.ini", tmp_path)
        payload = config.read_text(encoding="utf-8")
        payload = payload.replace("lvsize = 100GB", "lvsize = 101GB")
        payload = payload.replace("vgname = datavg", "vgname = invalid/name")
        payload = payload.replace("lvname = openinfradata_lv", "lvname = invalid name")
        payload = payload.replace("mode = standard", "mode = ldap_ipa")
        payload = payload.replace("peer_nodes =", "peer_nodes = peer01.example.com:2008")
        payload += "\n[operations]\nrollback_enabled = true\n"
        payload += "\n[storage.postgresql]\nmountpoint = /data/openinfra/\nowner = postgres\n"
        config.write_text(payload, encoding="utf-8")

        report = InstallerConfigValidator().validate_file(config, edition="pro", scope="server")

        assert report.valid is False
        joined = "\n".join(report.errors)
        for fragment in (
            "storage.lvsize must be <= 100GB",
            "storage.vgname contains invalid LVM characters",
            "storage.lvname contains invalid LVM characters",
            "unexpected section for pro:server: operations",
            "unexpected section for pro:server: storage.postgresql",
            "auth.mode must be standard",
            "identity.peer_nodes must not expose protocol or port",
        ):
            assert fragment in joined

    def test_lite_is_storage_only_and_rejects_api_auth_network(self, tmp_path: Path) -> None:
        config = self._copy_config("installers/setup/lite/install.ini", tmp_path)
        config.write_text(
            config.read_text(encoding="utf-8")
            + "\n[api]\nbackend_endpoint = https://lite.example.com\n"
            + "\n[auth]\nmode = ldap_ipa\n"
            + "\n[network]\nip_address = 192.0.2.10\n",
            encoding="utf-8",
        )

        report = InstallerConfigValidator().validate_file(
            config, edition="lite", scope="all-in-one"
        )

        assert report.valid is False
        joined = "\n".join(report.errors)
        assert "unexpected section for lite:all-in-one: api" in joined
        assert "unexpected section for lite:all-in-one: auth" in joined
        assert "unexpected section for lite:all-in-one: network" in joined

    def test_web_and_agent_endpoint_requirements_are_enforced(self, tmp_path: Path) -> None:
        web = self._copy_config("installers/setup/pro/web/install.ini", tmp_path)
        web.write_text(
            web.read_text(encoding="utf-8").replace(
                "backend_endpoint = https://pro-backend.openinfra.example.com",
                "backend_endpoint = http://pro-backend.openinfra.example.com/path",
            ),
            encoding="utf-8",
        )
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        agent = self._copy_config("installers/setup/enterprise/agent/install.ini", agent_dir)
        agent.write_text(
            agent.read_text(encoding="utf-8")
            .replace(
                "backend_endpoint = https://enterprise-vip.openinfra.example.com",
                "backend_endpoint = https://user:pass@enterprise-vip.openinfra.example.com/api",
            )
            .replace(
                "enrollment_token_ref = env:OPENINFRA_AGENT_ENROLLMENT_TOKEN",
                "enrollment_token_ref = clear-token",
            ),
            encoding="utf-8",
        )

        web_report = InstallerConfigValidator().validate_file(web, edition="pro", scope="web")
        agent_report = InstallerConfigValidator().validate_file(
            agent, edition="enterprise", scope="agent"
        )

        assert any(
            "api.backend_endpoint must be an https URL" in error for error in web_report.errors
        )
        joined = "\n".join(agent_report.errors)
        assert "api.backend_endpoint must not embed credentials" in joined
        assert "api.backend_endpoint must be an origin URL" in joined
        assert "api.enrollment_token_ref must reference" in joined

    def test_security_transport_policy_rejects_weak_back_front_agent_exchanges(
        self, tmp_path: Path
    ) -> None:
        validator = InstallerConfigValidator()
        weak_server = tmp_path / "weak-server.ini"
        weak_server.write_text(
            Path("installers/setup/pro/server/install.ini")
            .read_text(encoding="utf-8")
            .replace("transport = mtls", "transport = tls")
            .replace("tls_min_version = TLSv1.3", "tls_min_version = TLSv1.2")
            .replace("mtls_required = true", "mtls_required = false")
            .replace(
                "server_ca_cert_ref = file:///opt/openinfra/config/trust/openinfra-ca.pem",
                "server_ca_cert_ref = env:OPENINFRA_CA",
            )
            .replace(
                "trusted_proxy_cidrs = 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
                "trusted_proxy_cidrs = bad-cidr",
            ),
            encoding="utf-8",
        )
        weak_lite = tmp_path / "weak-lite.ini"
        weak_lite.write_text(
            Path("installers/setup/lite/install.ini")
            .read_text(encoding="utf-8")
            .replace("transport = local", "transport = mtls")
            .replace("mtls_required = false", "mtls_required = true")
            .replace("loopback_only = true", "loopback_only = false"),
            encoding="utf-8",
        )

        server_errors = "\n".join(
            validator.validate_file(weak_server, edition="pro", scope="server").errors
        )
        lite_errors = "\n".join(
            validator.validate_file(weak_lite, edition="lite", scope="all-in-one").errors
        )

        assert "pro:server security.transport must be mtls" in server_errors
        assert "security.tls_min_version must be TLSv1.3" in server_errors
        assert "pro:server security.mtls_required must be true" in server_errors
        assert "security.server_ca_cert_ref must reference file://" in server_errors
        assert "security.trusted_proxy_cidrs contains invalid CIDR: bad-cidr" in server_errors
        assert "lite security.transport must be local" in lite_errors
        assert "lite security.mtls_required must be false" in lite_errors
        assert "lite security.loopback_only must be true" in lite_errors

    def test_tree_detects_missing_unexpected_and_assert_raises(self, tmp_path: Path) -> None:
        unexpected = tmp_path / "lite/server/config/install.ini"
        unexpected.parent.mkdir(parents=True)
        unexpected.write_text(
            Path("installers/setup/lite/install.ini").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        validator = InstallerConfigValidator()
        report = validator.validate_tree(tmp_path)

        assert report.valid is False
        assert "setup/lite/install.ini" in report.missing_paths
        assert "lite/server/config/install.ini" in report.unexpected_paths
        with pytest.raises(ValidationError):
            validator.assert_tree_valid(tmp_path)

    def test_enterprise_storage_is_unlimited_and_systemd_is_rendered(self, tmp_path: Path) -> None:
        validator = InstallerConfigValidator()
        config = self._copy_config("installers/setup/enterprise/server/install.ini", tmp_path)
        config.write_text(
            config.read_text(encoding="utf-8").replace("lvsize = 1TB", "lvsize = 8TB"),
            encoding="utf-8",
        )

        report = validator.validate_file(config, edition="enterprise", scope="server")
        backend_unit = validator.render_systemd_unit("enterprise", "server")
        web_unit = validator.render_systemd_unit("pro", "web")
        agent_unit = validator.render_systemd_unit("enterprise", "agent")
        success = validator.assert_tree_valid(Path("installers"))

        assert report.valid is True
        assert "ExecStart=/opt/openinfra/venv/bin/openinfra-server-runtime api" in backend_unit
        assert "PrivateDevices=true" in backend_unit
        assert "ProtectKernelTunables=true" in backend_unit
        assert "openinfra-web.service" in web_unit
        assert "openinfra-agent.service" in agent_unit
        assert "openinfra database apply-migrations" not in backend_unit
        assert success.valid is True

    def test_application_filesystem_is_internal_for_every_scope_including_agent(
        self, tmp_path: Path
    ) -> None:
        validator = InstallerConfigValidator()

        server_report = validator.validate_file(
            Path("installers/setup/pro/server/install.ini"), edition="pro", scope="server"
        )
        web_report = validator.validate_file(
            Path("installers/setup/enterprise/web/install.ini"),
            edition="enterprise",
            scope="web",
        )
        agent_report = validator.validate_file(
            Path("installers/setup/enterprise/agent/install.ini"),
            edition="enterprise",
            scope="agent",
        )
        invalid_agent = tmp_path / "install.ini"
        invalid_agent.write_text(
            Path("installers/setup/enterprise/agent/install.ini").read_text(encoding="utf-8")
            + "\n[storage]\nvgname = rootvg\nlvname = openinfra_lv\nlvsize = 2GB\n",
            encoding="utf-8",
        )

        invalid_agent_report = validator.validate_file(
            invalid_agent, edition="enterprise", scope="agent"
        )

        assert server_report.managed_application_filesystem is True
        assert web_report.managed_application_filesystem is True
        assert agent_report.managed_application_filesystem is True
        assert server_report.as_dict()["managed_application_filesystem"] is True
        assert agent_report.as_dict()["managed_application_filesystem"] is True
        assert any(
            "application LVM filesystem /opt/openinfra/" in action
            for action in server_report.actions
        )
        assert any(
            "application LVM filesystem /opt/openinfra/" in action for action in web_report.actions
        )
        assert any(
            "application LVM filesystem /opt/openinfra/" in action
            for action in agent_report.actions
        )
        assert agent_report.as_dict()["application_filesystem"] is not None
        assert any(
            "must not expose PostgreSQL storage settings" in error
            for error in invalid_agent_report.errors
        )
        assert server_report.as_dict()["postgresql_filesystem"] is not None
        assert agent_report.as_dict()["postgresql_filesystem"] is None

    def test_postgresql_deployment_planner_is_os_aware_and_backend_only(
        self, tmp_path: Path
    ) -> None:
        catalog = InstallerOsCatalog()
        rhel = catalog.profile_from_os_release('ID="rhel"\nID_LIKE="fedora"\n')
        debian = catalog.profile_from_os_release('ID=ubuntu\nID_LIKE="debian"\n')
        suse = catalog.profile_from_os_release('ID=sles\nID_LIKE="suse"\n')
        planner = InstallerPostgreSQLDeploymentPlanner()

        debian_plan = planner.plan("ID=debian\n")
        server_report = InstallerConfigValidator().validate_file(
            Path("installers/setup/pro/server/install.ini"), edition="pro", scope="server"
        )
        web_report = InstallerConfigValidator().validate_file(
            Path("installers/setup/pro/web/install.ini"), edition="pro", scope="web"
        )

        assert rhel.package_manager == "dnf"
        assert debian.package_manager == "apt-get"
        suse_plan = planner.plan('ID=sles\nID_LIKE="suse"\n')

        assert suse.package_manager == "zypper"
        assert suse_plan.install_command == (
            "zypper",
            "--non-interactive",
            "install",
            "postgresql-server",
            "postgresql",
        )
        assert debian_plan.install_command == (
            "apt-get",
            "install",
            "-y",
            "--no-install-recommends",
            "postgresql",
            "postgresql-client",
        )
        assert server_report.postgresql_plan is not None
        assert server_report.as_dict()["postgresql_deployment"] is not None
        assert any(
            "install PostgreSQL packages if absent" in action for action in server_report.actions
        )
        assert web_report.postgresql_plan is None
        assert web_report.as_dict()["postgresql_deployment"] is None
        with pytest.raises(ValidationError):
            catalog.profile_from_os_release("ID=solaris\n")
        with pytest.raises(ValidationError):
            catalog.profile_from_file(tmp_path / "missing-os-release")

    def test_installer_config_error_edges_are_reported(self, tmp_path: Path) -> None:
        validator = InstallerConfigValidator()

        short_path_policy = InstallerScopeCatalog().infer_policy_from_path(Path("install.ini"))
        assert short_path_policy is None

        partial_context = validator.validate_file(
            tmp_path / "missing.ini", edition="lite", scope=None
        )
        assert any(
            "edition and scope must be provided together" in error
            for error in partial_context.errors
        )

        broken = tmp_path / "broken.ini"
        broken.write_text("[storage\nvgname = datavg\n", encoding="utf-8")
        broken_report = validator.validate_file(broken, edition="lite", scope="all-in-one")
        assert any("invalid ini syntax" in error for error in broken_report.errors)

        missing_storage = tmp_path / "missing-storage.ini"
        missing_storage.write_text(
            "[api]\nbackend_endpoint = https://backend.example.com\n", encoding="utf-8"
        )
        missing_storage_report = validator.validate_file(
            missing_storage, edition="lite", scope="all-in-one"
        )
        assert any("missing section: storage" in error for error in missing_storage_report.errors)

        invalid_option = tmp_path / "invalid-option.ini"
        invalid_option.write_text(
            "[storage]\nvgname = datavg\nlvname = openinfradata_lv\nlvsize = bad-size\nmountpoint = /data/openinfra\n",
            encoding="utf-8",
        )
        invalid_option_report = validator.validate_file(
            invalid_option, edition="lite", scope="all-in-one"
        )
        joined_invalid_option = "\n".join(invalid_option_report.errors)
        assert "unexpected option for lite:all-in-one: storage.mountpoint" in joined_invalid_option
        assert "invalid storage.lvsize" in joined_invalid_option

        agent_missing_token = tmp_path / "agent-missing-token.ini"
        agent_missing_token.write_text(
            "[api]\nbackend_endpoint = https://enterprise.example.com\nenrollment_token_ref =\n",
            encoding="utf-8",
        )
        agent_missing_token_report = validator.validate_file(
            agent_missing_token, edition="enterprise", scope="agent"
        )
        assert any(
            "empty option: api.enrollment_token_ref" in error
            for error in agent_missing_token_report.errors
        )

        invalid_peer = tmp_path / "invalid-peer.ini"
        invalid_peer.write_text(
            Path("installers/setup/pro/server/install.ini")
            .read_text(encoding="utf-8")
            .replace("peer_nodes =", "peer_nodes = bad_peer!,192.0.2.50"),
            encoding="utf-8",
        )
        invalid_peer_report = validator.validate_file(invalid_peer, edition="pro", scope="server")
        assert any(
            "invalid identity.peer_nodes entry" in error for error in invalid_peer_report.errors
        )

        clear_sensitive = tmp_path / "clear-sensitive.ini"
        clear_sensitive.write_text(
            Path("installers/setup/pro/server/install.ini").read_text(encoding="utf-8")
            + "\n[forbidden]\napi_token = cleartext-token-value-12345\n",
            encoding="utf-8",
        )
        clear_sensitive_report = validator.validate_file(
            clear_sensitive, edition="pro", scope="server"
        )
        assert any(
            "forbidden.api_token must reference" in error for error in clear_sensitive_report.errors
        )

        with pytest.raises(ValidationError):
            validator.render_systemd_unit("lite", "agent")

    def test_postgresql_ha_plan_covers_cluster_and_standalone_edges(self) -> None:
        catalog = InstallerOsCatalog()
        parsed = catalog.profile_from_os_release(
            '# comment\n\nID=ubuntu\nBADLINE\nID_LIKE="debian"\n'
        )
        validator = InstallerConfigValidator()

        enterprise = validator.validate_file(
            Path("installers/setup/enterprise/server/install.ini"),
            edition="enterprise",
            scope="server",
        )
        lite = validator.validate_file(
            Path("installers/setup/lite/install.ini"), edition="lite", scope="all-in-one"
        )
        web = validator.validate_file(
            Path("installers/setup/enterprise/web/install.ini"),
            edition="enterprise",
            scope="web",
        )

        assert parsed.family == "debian"
        assert enterprise.postgresql_ha_plan is not None
        assert enterprise.postgresql_ha_plan.replication_enabled is True
        assert enterprise.postgresql_ha_plan.topology == "near-real-time-streaming-cluster"
        assert enterprise.postgresql_ha_plan.replication_slot_names == (
            "openinfra_1",
            "openinfra_2",
        )
        assert enterprise.postgresql_ha_plan.commit_policy == "local_commit_non_blocking"
        assert (
            "synchronous_commit = 'local'" in enterprise.postgresql_ha_plan.postgresql_conf_lines()
        )
        assert not any(
            "synchronous_standby_names" in line
            for line in enterprise.postgresql_ha_plan.postgresql_conf_lines()
        )
        assert "wal_level = replica" in enterprise.postgresql_ha_plan.postgresql_conf_lines()
        assert (
            enterprise.as_dict()["postgresql_ha"]["failover_safety"]["automatic_promotion"] is False
        )
        assert lite.postgresql_ha_plan is not None
        assert lite.postgresql_ha_plan.replication_enabled is False
        assert lite.postgresql_ha_plan.replication_slot_names == ()
        assert web.postgresql_ha_plan is None
        assert web.as_dict()["postgresql_ha"] is None

    def test_installer_auth_ldap_ipa_invalid_edges_are_reported(self, tmp_path: Path) -> None:
        validator = InstallerConfigValidator()
        web_base = Path("installers/setup/pro/web/install.ini").read_text(encoding="utf-8")
        server_base = Path("installers/setup/pro/server/install.ini").read_text(encoding="utf-8")
        invalid_web = tmp_path / "invalid-ldap.ini"
        invalid_web.write_text(
            web_base.replace(
                "mode = standard",
                "\n".join(
                    (
                        "mode = ldap",
                        "directory_url = ldap://user:pass@ldap.example.net/path",
                        "base_dn = ou=people",
                        "user_filter = (uid=*)",
                        "group_filter = (cn=ops)",
                        "bind_dn_ref = env:OPENINFRA_LDAP_BIND_DN",
                        "cache_ttl_seconds = not-int",
                    )
                ),
            ),
            encoding="utf-8",
        )
        standard_with_directory = tmp_path / "standard-directory.ini"
        standard_with_directory.write_text(
            web_base.replace(
                "mode = standard",
                "mode = standard\ndirectory_url = ldaps://ldap.example.net",
            ),
            encoding="utf-8",
        )
        lite_ldap = tmp_path / "lite-ldap.ini"
        lite_ldap.write_text(
            Path("installers/setup/lite/install.ini").read_text(encoding="utf-8")
            + "\n[auth]\nmode = ldap\n",
            encoding="utf-8",
        )
        invalid_ttl = tmp_path / "invalid-ttl.ini"
        invalid_ttl.write_text(
            web_base.replace(
                "mode = standard",
                "\n".join(
                    (
                        "mode = ipa",
                        "directory_url = ldaps://ipa.example.net",
                        "base_dn = dc=example,dc=net",
                        "user_filter = (uid={username})",
                        "group_filter = (member={user_dn})",
                        "cache_ttl_seconds = 5",
                    )
                ),
            ),
            encoding="utf-8",
        )

        invalid_errors = "\n".join(
            validator.validate_file(invalid_web, edition="pro", scope="web").errors
        )
        standard_errors = "\n".join(
            validator.validate_file(standard_with_directory, edition="pro", scope="server").errors
        )
        lite_errors = "\n".join(
            validator.validate_file(lite_ldap, edition="lite", scope="all-in-one").errors
        )
        ttl_errors = "\n".join(
            validator.validate_file(invalid_ttl, edition="pro", scope="web").errors
        )

        assert "ldap:// auth.directory_url requires auth.start_tls=true" in invalid_errors
        assert "auth.directory_url must not embed credentials" in invalid_errors
        assert "auth.base_dn must be an LDAP distinguished name" in invalid_errors
        assert "auth.user_filter must contain {username}" in invalid_errors
        assert "auth.group_filter must contain {user_dn}" in invalid_errors
        assert "auth.bind_dn_ref and auth.bind_password_ref" in invalid_errors
        assert "auth.cache_ttl_seconds must be an integer" in invalid_errors
        assert "auth.directory_url is only valid for ldap/ipa mode" in standard_errors
        assert "lite auth.mode must remain standard" in lite_errors
        assert "auth.cache_ttl_seconds must be between 30 and 3600" in ttl_errors
        backend_direct = tmp_path / "backend-direct-ldap.ini"
        backend_direct.write_text(
            server_base.replace(
                "mode = standard",
                "\n".join(
                    (
                        "mode = ldap",
                        "directory_url = ldaps://ldap.example.net:636",
                        "base_dn = dc=example,dc=net",
                        "user_filter = (uid={username})",
                        "group_filter = (member={user_dn})",
                        "bind_dn_ref = file:///etc/openinfra/secrets/ldap-bind-dn",
                        "bind_password_ref = file:///etc/openinfra/secrets/ldap-bind-password",
                    )
                ),
            ),
            encoding="utf-8",
        )
        backend_report = validator.validate_file(backend_direct, edition="pro", scope="server")
        assert backend_report.valid is True
        assert any(
            "configure trusted SAML/LDAP identity validation" in action
            for action in backend_report.actions
        )


def _installer_parser(payload: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(payload)
    return parser


def test_installer_oracle_saml_team_sync_and_plan_private_branches() -> None:
    validator = InstallerConfigValidator()
    catalog = InstallerScopeCatalog()
    lite = catalog.policy_for("lite", "all-in-one")
    server = catalog.policy_for("pro", "server")
    enterprise_server = catalog.policy_for("enterprise", "server")
    web = catalog.policy_for("pro", "web")
    agent = catalog.policy_for("enterprise", "agent")
    assert (
        lite is not None
        and server is not None
        and enterprise_server is not None
        and web is not None
        and agent is not None
    )

    empty = _installer_parser("[empty]\nvalue = true\n")
    assert (
        validator._application_filesystem_plan(replace(agent, managed_application_filesystem=False))
        is None
    )
    assert validator._postgresql_filesystem_plan(empty, web) is None
    assert validator._postgresql_ha_plan(empty, web) is None

    errors: list[str] = []
    validator._validate_auth(_installer_parser("[auth]\nmode = saml\n"), lite, errors)
    assert "lite auth.mode must remain standard" in errors
    assert "auth.mode=saml requires a [saml] section" in errors

    errors = []
    validator._validate_auth(
        _installer_parser(
            "[auth]\n"
            "mode = ldap\n"
            "directory_url = ldaps://ldap.example.test\n"
            "base_dn = dc=example,dc=test\n"
            "user_filter = (uid={username})\n"
            "group_filter = (member={user_dn})\n"
        ),
        agent,
        errors,
    )
    assert any("must not configure LDAP/IPA" in error for error in errors)

    errors = []
    validator._validate_auth(
        _installer_parser(
            "[auth]\n"
            "mode = ldap\n"
            "directory_url = https://ldap.example.test\n"
            "base_dn = dc=example,dc=test\n"
            "user_filter = (uid={username})\n"
            "group_filter = (member={user_dn})\n"
        ),
        web,
        errors,
    )
    assert "auth.directory_url must use ldap:// or ldaps:// with a host" in errors

    errors = []
    validator._validate_auth(
        _installer_parser(
            "[auth]\n"
            "mode = ipa\n"
            "directory_url = ldaps://ipa.example.test\n"
            "start_tls = true\n"
            "base_dn = dc=example,dc=test\n"
            "user_filter = (uid={username})\n"
            "group_filter = (member={user_dn})\n"
        ),
        web,
        errors,
    )
    assert "auth.start_tls must be false with ldaps://" in errors

    errors = []
    validator._validate_database(
        _installer_parser("[database]\nbackend = sqlite\n"), server, errors
    )
    assert errors == ["database.backend must be postgresql or oracle"]

    errors = []
    validator._validate_database(_installer_parser("[database]\nbackend = oracle\n"), web, errors)
    assert errors == ["Oracle database backend is supported only by Enterprise server scope"]

    errors = []
    validator._validate_database(
        _installer_parser("[database]\nbackend = oracle\n"), server, errors
    )
    assert errors == ["Oracle database backend is supported only by Enterprise server scope"]

    errors = []
    validator._validate_database(
        _installer_parser("[database]\nbackend = oracle\n"), enterprise_server, errors
    )
    assert errors == ["database.backend=oracle requires an [oracle] section"]

    errors = []
    validator._validate_database(
        _installer_parser("[database]\nbackend = oracle\n[oracle]\ndsn = db/service\n"),
        enterprise_server,
        errors,
    )
    assert "missing option: oracle.user" in errors
    assert "missing option: oracle.password_ref" in errors

    errors = []
    validator._validate_saml(_installer_parser("[saml]\ntenant_id = default\n"), lite, errors)
    assert errors == ["SAML is not available in Lite edition"]

    errors = []
    validator._validate_saml(
        _installer_parser(
            "[saml]\n"
            "tenant_id = default\n"
            "idp_entity_id = urn:idp\n"
            "idp_sso_url = http://idp.example.test/sso\n"
            "idp_x509_cert_ref = file:///etc/openinfra/idp.pem\n"
            "sp_entity_id = urn:openinfra\n"
            "sp_acs_url = not-a-url\n"
            "group_role_mappings = admins=admin\n"
        ),
        server,
        errors,
    )
    assert "saml.idp_sso_url must be an HTTPS URL" in errors
    assert "saml.sp_acs_url must be an HTTPS URL" in errors

    errors = []
    validator._validate_team_sync(
        _installer_parser("[team_sync_ldap]\ntenant_id = default\n"), web, errors
    )
    assert errors == ["Team Sync is supported only by Pro/Enterprise server scopes"]

    errors = []
    validator._validate_team_sync(
        _installer_parser("[team_sync_custom]\nprovider = invalid\n"), server, errors
    )
    assert errors == ["team_sync_custom.provider is invalid"]

    errors = []
    validator._validate_team_sync(
        _installer_parser("[team_sync_oauth]\nprovider = oauth\n"), server, errors
    )
    assert "missing option: team_sync_oauth.tenant_id" in errors
    assert "missing option: team_sync_oauth.endpoint" in errors
    assert "missing option: team_sync_oauth.token_ref" in errors

    errors = []
    validator._validate_team_sync(
        _installer_parser("[team_sync_proxy]\nprovider = auth_proxy\ntenant_id = default\n"),
        server,
        errors,
    )
    assert "missing option: team_sync_proxy.snapshot_file" in errors
    assert "missing option: team_sync_proxy.signature_secret_ref" in errors


def test_installer_security_invalid_boolean_and_transport_values() -> None:
    validator = InstallerConfigValidator()
    policy = InstallerScopeCatalog().policy_for("pro", "server")
    assert policy is not None
    errors: list[str] = []
    validator._validate_security(
        _installer_parser(
            "[security]\n"
            "transport = cleartext\n"
            "tls_min_version = TLSv1.3\n"
            "mtls_required = sometimes\n"
            "loopback_only = maybe\n"
        ),
        policy,
        errors,
    )
    assert "security.transport must be local, tls or mtls" in errors
    assert "security.mtls_required must be true or false" in errors
    assert "security.loopback_only must be true or false" in errors
