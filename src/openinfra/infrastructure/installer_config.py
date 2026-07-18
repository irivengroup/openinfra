from __future__ import annotations

import configparser
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from openinfra.domain.common import ValidationError


@dataclass(frozen=True, slots=True)
class InstallerOsProfile:
    family: str
    package_manager: str
    packages: tuple[str, ...]
    service: str
    initdb_command: tuple[str, ...]
    cluster_marker_paths: tuple[str, ...]
    system_user_candidates: tuple[str, ...] = ("postgres", "pgsql")
    system_group_candidates: tuple[str, ...] = ("postgres", "pgsql")

    def as_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "package_manager": self.package_manager,
            "packages": list(self.packages),
            "service": self.service,
            "initdb_command": list(self.initdb_command),
            "cluster_marker_paths": list(self.cluster_marker_paths),
            "system_user_candidates": list(self.system_user_candidates),
            "system_group_candidates": list(self.system_group_candidates),
        }


@dataclass(frozen=True, slots=True)
class InstallerPostgreSQLDeploymentPlan:
    os_profile: InstallerOsProfile
    detection_binary: str
    install_command: tuple[str, ...]
    enable_command: tuple[str, ...]
    start_command: tuple[str, ...]
    verify_command: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "deploy_if_absent": True,
            "detection_binary": self.detection_binary,
            "os_profile": self.os_profile.as_dict(),
            "install_command": list(self.install_command),
            "initdb_command": list(self.os_profile.initdb_command),
            "enable_command": list(self.enable_command),
            "start_command": list(self.start_command),
            "verify_command": list(self.verify_command),
        }


@dataclass(frozen=True, slots=True)
class InstallerPostgreSQLHaPlan:
    replication_enabled: bool
    topology: str
    mode: str
    peer_nodes: tuple[str, ...]
    vip_endpoint: str | None
    replication_port: int = 5432
    cluster_sync_port: int = 2008
    pitr_archive_directory: str = "/data/openinfra/pitr"
    backup_directory: str = "/data/openinfra/backups"
    replication_slot_prefix: str = "openinfra"
    commit_policy: str = "local_commit_non_blocking"
    max_expected_lag_seconds: int = 5

    @property
    def replication_slot_names(self) -> tuple[str, ...]:
        if not self.replication_enabled:
            return ()
        return tuple(
            f"{self.replication_slot_prefix}_{index}"
            for index, _peer in enumerate(self.peer_nodes, start=1)
        )

    @property
    def archive_command(self) -> str:
        return (
            f"test ! -f {self.pitr_archive_directory}/%f && cp %p {self.pitr_archive_directory}/%f"
        )

    @property
    def restore_command(self) -> str:
        return f"cp {self.pitr_archive_directory}/%f %p"

    def postgresql_conf_lines(self) -> tuple[str, ...]:
        lines = [
            "# managed by OpenInfra installer",
            "# near-real-time streaming replication; commits do not wait for remote replay",
            "wal_level = replica",
            "archive_mode = on",
            f"archive_command = '{self.archive_command}'",
            f"restore_command = '{self.restore_command}'",
            "hot_standby = on",
            "max_wal_senders = 16",
            "max_replication_slots = 16",
            "wal_keep_size = '1024MB'",
            "max_slot_wal_keep_size = '4096MB'",
            "synchronous_commit = 'local'",
        ]
        if self.replication_enabled:
            lines.append("# standby selection and lag monitoring are managed by OpenInfra")
        return tuple(lines)

    def as_dict(self) -> dict[str, object]:
        return {
            "enabled": True,
            "replication_enabled": self.replication_enabled,
            "topology": self.topology,
            "mode": self.mode,
            "peer_nodes": list(self.peer_nodes),
            "vip_endpoint": self.vip_endpoint,
            "replication_port": self.replication_port,
            "cluster_sync_port": self.cluster_sync_port,
            "pitr_archive_directory": self.pitr_archive_directory,
            "backup_directory": self.backup_directory,
            "replication_slot_prefix": self.replication_slot_prefix,
            "replication_slot_names": list(self.replication_slot_names),
            "commit_policy": self.commit_policy,
            "max_expected_lag_seconds": self.max_expected_lag_seconds,
            "archive_command": self.archive_command,
            "restore_command": self.restore_command,
            "postgresql_conf_lines": list(self.postgresql_conf_lines()),
            "backup_command": [
                "pg_basebackup",
                "-D",
                self.backup_directory,
                "-Fp",
                "-Xs",
                "-P",
            ],
            "failover_safety": {
                "automatic_promotion": False,
                "requires_operator_confirmation": True,
                "precheck": "verify replay lag, VIP reachability and peer health",
            },
        }


class InstallerOsCatalog:
    _profiles: ClassVar[dict[str, InstallerOsProfile]] = {
        "rhel": InstallerOsProfile(
            family="rhel",
            package_manager="dnf",
            packages=("postgresql-server", "postgresql"),
            service="postgresql.service",
            initdb_command=("postgresql-setup", "--initdb"),
            cluster_marker_paths=("/var/lib/pgsql/data/PG_VERSION",),
        ),
        "debian": InstallerOsProfile(
            family="debian",
            package_manager="apt-get",
            packages=("postgresql", "postgresql-client"),
            service="postgresql.service",
            initdb_command=("pg_createcluster", "--start-conf=manual", "15", "main"),
            cluster_marker_paths=("/etc/postgresql/15/main/postgresql.conf",),
        ),
        "suse": InstallerOsProfile(
            family="suse",
            package_manager="zypper",
            packages=("postgresql-server", "postgresql"),
            service="postgresql.service",
            initdb_command=("postgresql-setup", "--initdb"),
            cluster_marker_paths=("/var/lib/pgsql/data/PG_VERSION",),
        ),
    }

    def profile_from_os_release(self, os_release: str) -> InstallerOsProfile:
        values = self._parse_os_release(os_release)
        candidates = tuple(
            item.lower()
            for item in (values.get("ID", ""), *values.get("ID_LIKE", "").split())
            if item
        )
        for candidate in candidates:
            if candidate in {"rhel", "centos", "fedora", "rocky", "almalinux"}:
                return self._profiles["rhel"]
            if candidate in {"debian", "ubuntu"}:
                return self._profiles["debian"]
            if candidate in {"sles", "suse", "opensuse", "opensuse-leap"}:
                return self._profiles["suse"]
        raise ValidationError("unsupported Linux family for PostgreSQL auto-deployment")

    def profile_from_file(self, path: Path = Path("/etc/os-release")) -> InstallerOsProfile:
        if not path.is_file():
            raise ValidationError("missing /etc/os-release for OS-aware PostgreSQL deployment")
        return self.profile_from_os_release(path.read_text(encoding="utf-8"))

    def _parse_os_release(self, payload: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for raw_line in payload.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip("'\"")
        return values


class InstallerPostgreSQLDeploymentPlanner:
    def __init__(self, os_catalog: InstallerOsCatalog | None = None) -> None:
        self._os_catalog = os_catalog or InstallerOsCatalog()

    def plan(self, os_release: str | None = None) -> InstallerPostgreSQLDeploymentPlan:
        profile = (
            self._os_catalog.profile_from_os_release(os_release)
            if os_release is not None
            else self._os_catalog.profile_from_file()
        )
        install_command = (profile.package_manager, "install", "-y", *profile.packages)
        if profile.package_manager == "apt-get":
            install_command = (
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                *profile.packages,
            )
        if profile.package_manager == "zypper":
            install_command = ("zypper", "--non-interactive", "install", *profile.packages)
        return InstallerPostgreSQLDeploymentPlan(
            os_profile=profile,
            detection_binary="psql",
            install_command=install_command,
            enable_command=("systemctl", "enable", profile.service),
            start_command=("systemctl", "start", profile.service),
            verify_command=("pg_isready", "--timeout=5"),
        )


@dataclass(frozen=True, slots=True)
class InstallerFilesystemPlan:
    name: str
    vgname: str
    lvname: str
    lvsize: str
    filesystem: str
    mountpoint: str
    owner: str
    group: str

    @property
    def lv_path(self) -> str:
        return f"/dev/{self.vgname}/{self.lvname}"

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "vgname": self.vgname,
            "lvname": self.lvname,
            "lvsize": self.lvsize,
            "filesystem": self.filesystem,
            "mountpoint": self.mountpoint,
            "owner": self.owner,
            "group": self.group,
            "lv_path": self.lv_path,
        }


@dataclass(frozen=True, slots=True)
class InstallerScopePolicy:
    edition: str
    scope: str
    service: str
    managed_application_filesystem: bool
    managed_postgresql: bool
    apply_backend_migrations: bool
    postgresql_lvsize_max: str | None
    required_sections: tuple[str, ...]
    required_options: dict[str, tuple[str, ...]]
    allowed_options: dict[str, tuple[str, ...]]

    @property
    def key(self) -> str:
        return self.edition + ":" + self.scope

    @property
    def config_path(self) -> str:
        if self.edition == "lite" and self.scope == "all-in-one":
            return "setup/lite/install.ini"
        return f"setup/{self.edition}/{self.scope}/install.ini"


@dataclass(frozen=True, slots=True)
class InstallerConfigReport:
    path: Path
    edition: str
    scope: str
    service: str
    managed_application_filesystem: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    actions: tuple[str, ...]
    application_filesystem_plan: InstallerFilesystemPlan | None = None
    postgresql_filesystem_plan: InstallerFilesystemPlan | None = None
    postgresql_plan: InstallerPostgreSQLDeploymentPlan | None = None
    postgresql_ha_plan: InstallerPostgreSQLHaPlan | None = None

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "edition": self.edition,
            "scope": self.scope,
            "service": self.service,
            "managed_application_filesystem": self.managed_application_filesystem,
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "actions": list(self.actions),
            "application_filesystem": (
                self.application_filesystem_plan.as_dict()
                if self.application_filesystem_plan is not None
                else None
            ),
            "postgresql_filesystem": (
                self.postgresql_filesystem_plan.as_dict()
                if self.postgresql_filesystem_plan is not None
                else None
            ),
            "postgresql_deployment": (
                self.postgresql_plan.as_dict() if self.postgresql_plan is not None else None
            ),
            "postgresql_ha": (
                self.postgresql_ha_plan.as_dict() if self.postgresql_ha_plan is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class InstallerFleetReport:
    root: Path
    reports: tuple[InstallerConfigReport, ...]
    missing_paths: tuple[str, ...]
    unexpected_paths: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return (
            not self.missing_paths
            and not self.unexpected_paths
            and all(report.valid for report in self.reports)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "valid": self.valid,
            "missing_paths": list(self.missing_paths),
            "unexpected_paths": list(self.unexpected_paths),
            "reports": [report.as_dict() for report in self.reports],
        }


class InstallerScopeCatalog:
    _storage_options = ("vgname", "lvname", "lvsize")
    _api_options = ("backend_endpoint", "enrollment_token_ref")
    _server_api_options = ("backend_endpoint",)
    _identity_options = ("peer_nodes",)
    _security_options = (
        "transport",
        "tls_min_version",
        "mtls_required",
        "server_ca_cert_ref",
        "client_cert_ref",
        "client_key_ref",
        "trusted_proxy_cidrs",
        "loopback_only",
    )
    _lite_security_required_options = (
        "transport",
        "tls_min_version",
        "mtls_required",
        "loopback_only",
    )
    _network_security_required_options = (
        "transport",
        "tls_min_version",
        "mtls_required",
        "server_ca_cert_ref",
        "client_cert_ref",
        "client_key_ref",
    )
    _backend_auth_required_options = ("mode",)
    _directory_auth_options = (
        "directory_url",
        "base_dn",
        "user_filter",
        "group_filter",
        "bind_dn_ref",
        "bind_password_ref",
        "ca_cert_ref",
        "cache_ttl_seconds",
        "user_base_dn",
        "group_base_dn",
        "username_attribute",
        "display_name_attribute",
        "email_attribute",
        "group_name_attribute",
        "group_member_attribute",
        "connect_timeout_seconds",
        "operation_timeout_seconds",
        "page_size",
        "size_limit",
        "follow_referrals",
        "start_tls",
        "nested_groups",
        "nested_group_depth",
    )
    _backend_auth_options = (
        "mode",
        "postgresql_user_ref",
        "postgresql_password_ref",
        *_directory_auth_options,
    )
    _web_auth_required_options = ("mode",)
    _web_auth_options = ("mode", *_directory_auth_options)
    _database_options = ("backend",)
    _oracle_options = (
        "dsn",
        "user",
        "password_ref",
        "pool_min",
        "pool_max",
        "pool_increment",
        "timeout_seconds",
    )
    _saml_options = (
        "tenant_id",
        "idp_entity_id",
        "idp_sso_url",
        "idp_x509_cert_ref",
        "sp_entity_id",
        "sp_acs_url",
        "name_id_format",
        "subject_attribute",
        "display_name_attribute",
        "email_attribute",
        "groups_attribute",
        "want_assertions_signed",
        "want_messages_signed",
        "clock_skew_seconds",
        "group_role_mappings",
    )
    _team_sync_options = (
        "source_id",
        "tenant_id",
        "provider",
        "endpoint",
        "token_ref",
        "snapshot_file",
        "signature_secret_ref",
        "timeout_seconds",
        "page_size",
        "deactivate_orphans",
        "group_role_mappings",
    )
    _web_database_required_options = (
        "postgresql_dsn_ref",
        "postgresql_user_ref",
        "postgresql_password_ref",
    )
    _web_database_options = _web_database_required_options

    def __init__(self) -> None:
        self._policies = {
            policy.key: policy
            for policy in (
                InstallerScopePolicy(
                    edition="lite",
                    scope="all-in-one",
                    service="openinfra.service",
                    managed_application_filesystem=True,
                    managed_postgresql=True,
                    apply_backend_migrations=True,
                    postgresql_lvsize_max="2GB",
                    required_sections=("storage", "security", "web_database"),
                    required_options={
                        "storage": self._storage_options,
                        "security": self._lite_security_required_options,
                        "web_database": self._web_database_required_options,
                    },
                    allowed_options={
                        "storage": self._storage_options,
                        "security": self._security_options,
                        "web_database": self._web_database_options,
                    },
                ),
                InstallerScopePolicy(
                    edition="pro",
                    scope="server",
                    service="openinfra.service",
                    managed_application_filesystem=True,
                    managed_postgresql=True,
                    apply_backend_migrations=True,
                    postgresql_lvsize_max="100GB",
                    required_sections=("storage", "api", "identity", "auth", "security"),
                    required_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "auth": self._backend_auth_required_options,
                        "security": self._network_security_required_options,
                    },
                    allowed_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "identity": self._identity_options,
                        "auth": self._backend_auth_options,
                        "security": self._security_options,
                    },
                ),
                InstallerScopePolicy(
                    edition="pro",
                    scope="web",
                    service="openinfra-web.service",
                    managed_application_filesystem=True,
                    managed_postgresql=False,
                    apply_backend_migrations=False,
                    postgresql_lvsize_max=None,
                    required_sections=("api", "auth", "security", "web_database"),
                    required_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_required_options,
                        "security": self._network_security_required_options,
                        "web_database": self._web_database_required_options,
                    },
                    allowed_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_options,
                        "security": self._security_options,
                        "web_database": self._web_database_options,
                    },
                ),
                InstallerScopePolicy(
                    edition="enterprise",
                    scope="server",
                    service="openinfra.service",
                    managed_application_filesystem=True,
                    managed_postgresql=True,
                    apply_backend_migrations=True,
                    postgresql_lvsize_max=None,
                    required_sections=("storage", "api", "identity", "auth", "security"),
                    required_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "auth": self._backend_auth_required_options,
                        "security": self._network_security_required_options,
                    },
                    allowed_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "identity": self._identity_options,
                        "auth": self._backend_auth_options,
                        "security": self._security_options,
                    },
                ),
                InstallerScopePolicy(
                    edition="enterprise",
                    scope="web",
                    service="openinfra-web.service",
                    managed_application_filesystem=True,
                    managed_postgresql=False,
                    apply_backend_migrations=False,
                    postgresql_lvsize_max=None,
                    required_sections=("api", "auth", "security", "web_database"),
                    required_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_required_options,
                        "security": self._network_security_required_options,
                        "web_database": self._web_database_required_options,
                    },
                    allowed_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_options,
                        "security": self._security_options,
                        "web_database": self._web_database_options,
                    },
                ),
                InstallerScopePolicy(
                    edition="enterprise",
                    scope="agent",
                    service="openinfra-agent.service",
                    managed_application_filesystem=True,
                    managed_postgresql=False,
                    apply_backend_migrations=False,
                    postgresql_lvsize_max=None,
                    required_sections=("api", "security"),
                    required_options={
                        "api": self._api_options,
                        "security": self._network_security_required_options,
                    },
                    allowed_options={
                        "api": self._api_options,
                        "security": self._security_options,
                    },
                ),
            )
        }
        for policy in self._policies.values():
            policy.allowed_options["database"] = self._database_options
            if policy.edition in {"pro", "enterprise"} and policy.scope in {
                "server",
                "web",
            }:
                policy.allowed_options["saml"] = self._saml_options
            if policy.edition in {"pro", "enterprise"} and policy.scope == "server":
                policy.allowed_options["oracle"] = self._oracle_options
                for provider in ("ldap", "oauth", "auth_proxy", "okta"):
                    policy.allowed_options["team_sync_" + provider] = self._team_sync_options

    def policy_for(self, edition: str, scope: str) -> InstallerScopePolicy | None:
        return self._policies.get(self._key(edition, scope))

    def expected_config_paths(self) -> tuple[str, ...]:
        return tuple(policy.config_path for policy in self.policies())

    def policies(self) -> tuple[InstallerScopePolicy, ...]:
        return tuple(sorted(self._policies.values(), key=lambda item: item.key))

    def infer_policy_from_path(self, path: Path) -> InstallerScopePolicy | None:
        parts = tuple(path.as_posix().split("/"))
        if len(parts) < 3 or parts[-1] != "install.ini":
            return None
        if parts[-3:] == ("setup", "lite", "install.ini"):
            return self.policy_for("lite", "all-in-one")
        if len(parts) >= 4 and parts[-4] == "setup":
            return self.policy_for(parts[-3], parts[-2])
        return None

    def _key(self, edition: str, scope: str) -> str:
        normalized = edition.strip().lower()
        return normalized + ":" + scope.strip().lower()


class InstallerSecretPolicy:
    _sensitive_key = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key)")
    _allowed_prefixes = ("env:", "vault://", "sops://", "file://", "kms://")

    def validate(self, parser: configparser.ConfigParser) -> list[str]:
        errors: list[str] = []
        for section in parser.sections():
            for key, value in parser.items(section):
                if key.endswith("_ref") and value.strip():
                    self._validate_reference(section, key, value, errors)
                elif (
                    self._sensitive_key.search(key)
                    and value.strip()
                    and not value.strip().startswith(self._allowed_prefixes)
                ):
                    errors.append(
                        f"{section}.{key} must reference env:, vault://, sops://, file:// or kms://"
                    )
        return errors

    def _validate_reference(self, section: str, key: str, value: str, errors: list[str]) -> None:
        if not value.strip().startswith(self._allowed_prefixes):
            errors.append(
                f"{section}.{key} must reference env:, vault://, sops://, file:// or kms://"
            )


class LogicalVolumeSizeParser:
    _pattern = re.compile(r"^(?P<value>[1-9][0-9]*)(?P<unit>MB|GB|TB)$", re.IGNORECASE)
    _multipliers: ClassVar[dict[str, int]] = {"MB": 1, "GB": 1024, "TB": 1024 * 1024}

    def to_mebibytes(self, raw: str) -> int:
        match = self._pattern.match(raw.strip())
        if not match:
            raise ValueError("logical volume size must use MB, GB or TB, for example 100GB")
        value = int(match.group("value"))
        unit = match.group("unit").upper()
        return value * self._multipliers[unit]


class InstallerSystemdUnitRenderer:
    _hardening_directives: ClassVar[tuple[str, ...]] = (
        "CapabilityBoundingSet=",
        "LockPersonality=true",
        "MemoryDenyWriteExecute=true",
        "PrivateDevices=true",
        "ProtectClock=true",
        "ProtectControlGroups=true",
        "ProtectHostname=true",
        "ProtectKernelLogs=true",
        "ProtectKernelModules=true",
        "ProtectKernelTunables=true",
        "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
        "RestrictNamespaces=true",
        "RestrictRealtime=true",
        "RestrictSUIDSGID=true",
        "SystemCallArchitectures=native",
    )

    def render(self, policy: InstallerScopePolicy) -> str:
        if policy.service == "openinfra-web.service":
            return self._web_unit(policy.service)
        if policy.service == "openinfra-agent.service":
            return self._agent_unit(policy.service)
        return self._backend_unit(policy.service)

    def _backend_unit(self, service: str) -> str:
        return "\n".join(
            (
                "[Unit]",
                "Description=OpenInfra backend service",
                "After=network-online.target openinfra-migrate.service",
                "Requires=openinfra-migrate.service",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                "User=openinfra",
                "Group=openinfra",
                "EnvironmentFile=/etc/openinfra/openinfra.conf",
                "WorkingDirectory=/opt/openinfra",
                "ExecStart=/opt/openinfra/venv/bin/openinfra-server-runtime api",
                "Restart=on-failure",
                "RestartSec=5s",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "ProtectSystem=strict",
                "ProtectHome=true",
                *self._hardening_directives,
                "ReadWritePaths=/opt/openinfra /data/openinfra /var/log/openinfra",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
                f"# rendered_service={service}",
            )
        )

    def _web_unit(self, service: str) -> str:
        return "\n".join(
            (
                "[Unit]",
                "Description=OpenInfra web frontend service",
                "After=network-online.target openinfra-runtime-secrets.service",
                "Requires=openinfra-runtime-secrets.service",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                "User=openinfra",
                "Group=openinfra",
                "EnvironmentFile=/etc/openinfra/openinfra.conf",
                "WorkingDirectory=/opt/openinfra",
                "ExecStart=/opt/openinfra/venv/bin/openinfra-web "
                "--backend-bearer-token-file /var/lib/openinfra/secrets/bootstrap-token",
                "Restart=on-failure",
                "RestartSec=5s",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "ProtectSystem=strict",
                "ProtectHome=true",
                *self._hardening_directives,
                "ReadOnlyPaths=/var/lib/openinfra/secrets",
                "ReadWritePaths=/var/log/openinfra",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
                f"# rendered_service={service}",
            )
        )

    def _agent_unit(self, service: str) -> str:
        return "\n".join(
            (
                "[Unit]",
                "Description=OpenInfra enterprise discovery proxy collector agent",
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                "User=openinfra",
                "Group=openinfra",
                "EnvironmentFile=/etc/openinfra/openinfra.conf",
                "WorkingDirectory=/opt/openinfra",
                "ExecStart=/opt/openinfra/venv/bin/openinfra "
                "discovery collector-list --backend json",
                "Restart=on-failure",
                "RestartSec=5s",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "ProtectSystem=strict",
                "ProtectHome=true",
                *self._hardening_directives,
                "ReadWritePaths=/var/log/openinfra",
                "",
                "[Install]",
                "WantedBy=multi-user.target",
                "",
                f"# rendered_service={service}",
            )
        )


class InstallerConfigValidator:
    _safe_lvm_name = re.compile(r"^[A-Za-z0-9_+.-]{1,64}$")

    def __init__(self, catalog: InstallerScopeCatalog | None = None) -> None:
        self._catalog = catalog or InstallerScopeCatalog()
        self._secret_policy = InstallerSecretPolicy()
        self._size_parser = LogicalVolumeSizeParser()
        self._postgresql_planner = InstallerPostgreSQLDeploymentPlanner()

    def validate_file(
        self, path: Path, edition: str | None = None, scope: str | None = None
    ) -> InstallerConfigReport:
        errors: list[str] = []
        warnings: list[str] = []
        policy = self._resolve_policy(path, edition, scope, errors)
        parser = self._parse(path, errors)
        if parser is not None and policy is not None:
            self._validate_schema(parser, policy, errors)
            self._validate_storage(parser, policy, errors)
            self._validate_api(parser, policy, errors)
            self._validate_identity(parser, policy, errors)
            self._validate_auth(parser, policy, errors)
            self._validate_database(parser, policy, errors)
            self._validate_saml(parser, policy, errors)
            self._validate_team_sync(parser, policy, errors)
            self._validate_security(parser, policy, errors)
            errors.extend(self._secret_policy.validate(parser))
        if policy is None:
            return InstallerConfigReport(
                path,
                edition or "unknown",
                scope or "unknown",
                "unknown",
                False,
                tuple(errors),
                (),
                (),
            )
        application_filesystem_plan = self._application_filesystem_plan(policy)
        postgresql_plan = self._postgresql_planner.plan() if policy.managed_postgresql else None
        postgresql_filesystem_plan = (
            self._postgresql_filesystem_plan(parser, policy)
            if parser is not None and postgresql_plan is not None and not errors
            else None
        )
        postgresql_ha_plan = (
            self._postgresql_ha_plan(parser, policy)
            if parser is not None and postgresql_plan is not None and not errors
            else None
        )
        return InstallerConfigReport(
            path=path,
            edition=policy.edition,
            scope=policy.scope,
            service=policy.service,
            managed_application_filesystem=policy.managed_application_filesystem,
            errors=tuple(errors),
            warnings=tuple(warnings),
            actions=self._render_actions(
                policy,
                application_filesystem_plan,
                postgresql_filesystem_plan,
                postgresql_plan,
                postgresql_ha_plan,
            ),
            application_filesystem_plan=application_filesystem_plan,
            postgresql_filesystem_plan=postgresql_filesystem_plan,
            postgresql_plan=postgresql_plan,
            postgresql_ha_plan=postgresql_ha_plan,
        )

    def validate_tree(self, root: Path) -> InstallerFleetReport:
        expected = self._catalog.expected_config_paths()
        reports: list[InstallerConfigReport] = []
        missing: list[str] = []
        for relative in expected:
            path = root / relative
            policy = self._catalog.infer_policy_from_path(path)
            if path.is_file() and policy is not None:
                reports.append(self.validate_file(path, policy.edition, policy.scope))
            else:
                missing.append(relative)
        expected_set = set(expected)
        unexpected = tuple(
            sorted(
                str(path.relative_to(root))
                for path in root.rglob("install.ini")
                if str(path.relative_to(root)) not in expected_set
            )
        )
        return InstallerFleetReport(root, tuple(reports), tuple(missing), unexpected)

    def assert_tree_valid(self, root: Path) -> InstallerFleetReport:
        report = self.validate_tree(root)
        if not report.valid:
            raise ValidationError(str(report.as_dict()))
        return report

    def render_systemd_unit(self, edition: str, scope: str) -> str:
        policy = self._catalog.policy_for(edition, scope)
        if policy is None:
            raise ValidationError(f"unsupported edition/scope combination: {edition}/{scope}")
        return InstallerSystemdUnitRenderer().render(policy)

    def _resolve_policy(
        self, path: Path, edition: str | None, scope: str | None, errors: list[str]
    ) -> InstallerScopePolicy | None:
        if edition is not None or scope is not None:
            if not edition or not scope:
                errors.append("edition and scope must be provided together")
                return None
            policy = self._catalog.policy_for(edition, scope)
        else:
            policy = self._catalog.infer_policy_from_path(path)
        if policy is None:
            errors.append(
                "cannot infer supported installer edition/scope from path; "
                "use installers/setup/lite/install.ini or "
                "installers/setup/<pro|enterprise>/<scope>/install.ini"
            )
        return policy

    def _parse(self, path: Path, errors: list[str]) -> configparser.ConfigParser | None:
        if not path.is_file():
            errors.append(f"missing install.ini: {path}")
            return None
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(path, encoding="utf-8")
        except configparser.Error as exc:
            errors.append(f"invalid ini syntax: {exc}")
            return None
        return parser

    def _application_filesystem_plan(
        self, policy: InstallerScopePolicy
    ) -> InstallerFilesystemPlan | None:
        if not policy.managed_application_filesystem:
            return None
        return InstallerFilesystemPlan(
            name="application",
            vgname="rootvg",
            lvname="openinfra_lv",
            lvsize="2GB",
            filesystem="xfs",
            mountpoint="/opt/openinfra",
            owner="openinfra",
            group="openinfra",
        )

    def _postgresql_filesystem_plan(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy
    ) -> InstallerFilesystemPlan | None:
        if not policy.managed_postgresql or not parser.has_section("storage"):
            return None
        return InstallerFilesystemPlan(
            name="postgresql",
            vgname=parser.get("storage", "vgname").strip(),
            lvname=parser.get("storage", "lvname").strip(),
            lvsize=parser.get("storage", "lvsize").strip(),
            filesystem="xfs",
            mountpoint="/data/openinfra",
            owner="postgresql-system-user",
            group="postgresql-system-group",
        )

    def _postgresql_ha_plan(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy
    ) -> InstallerPostgreSQLHaPlan | None:
        if not policy.managed_postgresql:
            return None
        peers = self._identity_peer_nodes(parser)
        endpoint = (
            parser.get("api", "backend_endpoint", fallback="").strip()
            if parser.has_section("api")
            else None
        )
        replication_enabled = policy.scope == "server" and bool(peers)
        topology = (
            "near-real-time-streaming-cluster" if replication_enabled else "standalone-managed"
        )
        return InstallerPostgreSQLHaPlan(
            replication_enabled=replication_enabled,
            topology=topology,
            mode="near-real-time-postgresql-streaming",
            peer_nodes=peers,
            vip_endpoint=endpoint or None,
        )

    def _identity_peer_nodes(self, parser: configparser.ConfigParser) -> tuple[str, ...]:
        if not parser.has_section("identity"):
            return ()
        raw = parser.get("identity", "peer_nodes", fallback="").strip()
        return tuple(item.strip() for item in raw.split(",") if item.strip())

    def _validate_schema(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        declared_sections = set(parser.sections())
        allowed_sections = set(policy.allowed_options)
        for section in policy.required_sections:
            if section not in declared_sections:
                errors.append(f"missing section: {section}")
        for section in sorted(declared_sections - allowed_sections):
            errors.append(f"unexpected section for {policy.key}: {section}")
        for section, options in policy.allowed_options.items():
            if not parser.has_section(section):
                continue
            allowed_options = set(options)
            for option in parser.options(section):
                if option not in allowed_options:
                    errors.append(f"unexpected option for {policy.key}: {section}.{option}")
        for section, options in policy.required_options.items():
            if not parser.has_section(section):
                continue
            for option in options:
                self._required(parser, section, option, errors)

    def _required(
        self, parser: configparser.ConfigParser, section: str, option: str, errors: list[str]
    ) -> str:
        if not parser.has_option(section, option):
            errors.append(f"missing option: {section}.{option}")
            return ""
        value = parser.get(section, option).strip()
        if not value:
            errors.append(f"empty option: {section}.{option}")
        return value

    def _validate_storage(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        if not policy.managed_postgresql:
            if parser.has_section("storage"):
                errors.append(f"{policy.key} must not expose PostgreSQL storage settings")
            return
        if not parser.has_section("storage"):
            return
        vgname = self._required(parser, "storage", "vgname", errors)
        lvname = self._required(parser, "storage", "lvname", errors)
        lvsize = self._required(parser, "storage", "lvsize", errors)
        for key, value in (("vgname", vgname), ("lvname", lvname)):
            if value and not self._safe_lvm_name.fullmatch(value):
                errors.append(f"storage.{key} contains invalid LVM characters")
        if not lvsize:
            return
        try:
            requested = self._size_parser.to_mebibytes(lvsize)
            if policy.postgresql_lvsize_max is not None:
                maximum = self._size_parser.to_mebibytes(policy.postgresql_lvsize_max)
                if requested > maximum:
                    errors.append(
                        f"{policy.key} storage.lvsize must be <= {policy.postgresql_lvsize_max}"
                    )
        except ValueError as exc:
            errors.append(f"invalid storage.lvsize: {exc}")

    def _validate_api(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        if not parser.has_section("api"):
            return
        endpoint = parser.get("api", "backend_endpoint", fallback="").strip()
        if endpoint:
            self._validate_https_endpoint(endpoint, "api.backend_endpoint", errors)
        if policy.scope == "agent":
            token = parser.get("api", "enrollment_token_ref", fallback="").strip()
            if not token:
                errors.append("empty option: api.enrollment_token_ref")

    def _validate_https_endpoint(self, raw: str, key: str, errors: list[str]) -> None:
        parsed = urlparse(raw)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{key} must be an https URL")
            return
        if parsed.username or parsed.password:
            errors.append(f"{key} must not embed credentials")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            errors.append(f"{key} must be an origin URL without path, query or fragment")

    def _validate_identity(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        if policy.scope != "server" or not parser.has_section("identity"):
            return
        peers = parser.get("identity", "peer_nodes", fallback="").strip()
        if not peers:
            return
        for peer in (item.strip() for item in peers.split(",") if item.strip()):
            if "://" in peer or ":" in peer:
                errors.append(
                    "identity.peer_nodes must not expose protocol or port; port 2008 is internal"
                )
                continue
            self._validate_host_like(peer, errors)

    def _validate_host_like(self, peer: str, errors: list[str]) -> None:
        try:
            ipaddress.ip_address(peer)
            return
        except ValueError:
            labels = peer.split(".")
            valid = (
                all(
                    re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                    for label in labels
                    if label
                )
                and "" not in labels
            )
            if not valid:
                errors.append(f"invalid identity.peer_nodes entry: {peer}")

    def _validate_auth(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        if not parser.has_section("auth"):
            return
        mode = parser.get("auth", "mode", fallback="").strip().lower()
        if mode not in {"standard", "ldap", "ipa", "saml"}:
            errors.append(f"{policy.key} auth.mode must be standard, ldap, ipa or saml")
            return
        directory_options = InstallerScopeCatalog._directory_auth_options
        if mode == "standard":
            for option in directory_options:
                if parser.get("auth", option, fallback="").strip():
                    errors.append(f"{policy.key} auth.{option} is only valid for ldap/ipa mode")
            return
        if mode == "saml":
            if policy.edition == "lite":
                errors.append("lite auth.mode must remain standard")
            if not parser.has_section("saml"):
                errors.append("auth.mode=saml requires a [saml] section")
            return
        if policy.edition == "lite":
            errors.append("lite auth.mode must remain standard")
            return
        if policy.scope not in {"server", "web"}:
            errors.append(f"{policy.key} must not configure LDAP/IPA")
            return
        url = self._required(parser, "auth", "directory_url", errors)
        base_dn = self._required(parser, "auth", "base_dn", errors)
        user_filter = self._required(parser, "auth", "user_filter", errors)
        group_filter = self._required(parser, "auth", "group_filter", errors)
        if url:
            parsed = urlparse(url)
            start_tls = parser.getboolean("auth", "start_tls", fallback=False)
            if parsed.scheme not in {"ldap", "ldaps"} or not parsed.netloc:
                errors.append("auth.directory_url must use ldap:// or ldaps:// with a host")
            if parsed.scheme == "ldap" and not start_tls:
                errors.append("ldap:// auth.directory_url requires auth.start_tls=true")
            if parsed.scheme == "ldaps" and start_tls:
                errors.append("auth.start_tls must be false with ldaps://")
            if parsed.username or parsed.password:
                errors.append("auth.directory_url must not embed credentials")
        if base_dn and not re.search(r"(^|,)dc=[^,]+", base_dn, flags=re.IGNORECASE):
            errors.append("auth.base_dn must be an LDAP distinguished name")
        if user_filter and "{username}" not in user_filter:
            errors.append("auth.user_filter must contain {username}")
        if group_filter and "{user_dn}" not in group_filter:
            errors.append("auth.group_filter must contain {user_dn}")
        bind_dn_ref = parser.get("auth", "bind_dn_ref", fallback="").strip()
        bind_password_ref = parser.get("auth", "bind_password_ref", fallback="").strip()
        if bool(bind_dn_ref) != bool(bind_password_ref):
            errors.append("auth.bind_dn_ref and auth.bind_password_ref must be provided together")
        ttl = parser.get("auth", "cache_ttl_seconds", fallback="300").strip()
        if ttl:
            try:
                value = int(ttl)
            except ValueError:
                errors.append("auth.cache_ttl_seconds must be an integer")
            else:
                if not 30 <= value <= 3600:
                    errors.append("auth.cache_ttl_seconds must be between 30 and 3600")

    def _validate_database(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        backend = parser.get("database", "backend", fallback="postgresql").strip().lower()
        if backend not in {"postgresql", "oracle"}:
            errors.append("database.backend must be postgresql or oracle")
            return
        if backend == "oracle":
            if policy.edition != "enterprise" or policy.scope != "server":
                errors.append(
                    "Oracle database backend is supported only by Enterprise server scope"
                )
                return
            if not parser.has_section("oracle"):
                errors.append("database.backend=oracle requires an [oracle] section")
                return
            for option in ("dsn", "user", "password_ref"):
                self._required(parser, "oracle", option, errors)
        elif policy.scope in {"server", "all-in-one"} and policy.edition != "lite":
            for option in ("postgresql_user_ref", "postgresql_password_ref"):
                self._required(parser, "auth", option, errors)

    def _validate_saml(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        if not parser.has_section("saml"):
            return
        if policy.edition == "lite":
            errors.append("SAML is not available in Lite edition")
            return
        for option in (
            "tenant_id",
            "idp_entity_id",
            "idp_sso_url",
            "idp_x509_cert_ref",
            "sp_entity_id",
            "sp_acs_url",
            "group_role_mappings",
        ):
            self._required(parser, "saml", option, errors)
        for option in ("idp_sso_url", "sp_acs_url"):
            value = parser.get("saml", option, fallback="").strip()
            if value:
                parsed = urlparse(value)
                if parsed.scheme != "https" or not parsed.netloc:
                    errors.append(f"saml.{option} must be an HTTPS URL")

    def _validate_team_sync(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        for section in parser.sections():
            if not section.startswith("team_sync_"):
                continue
            if policy.edition == "lite" or policy.scope != "server":
                errors.append("Team Sync is supported only by Pro/Enterprise server scopes")
                continue
            provider = parser.get(section, "provider", fallback=section.removeprefix("team_sync_"))
            provider = provider.strip().lower()
            if provider not in {"ldap", "oauth", "auth_proxy", "okta"}:
                errors.append(f"{section}.provider is invalid")
                continue
            self._required(parser, section, "tenant_id", errors)
            if provider in {"oauth", "okta"}:
                self._required(parser, section, "endpoint", errors)
                self._required(parser, section, "token_ref", errors)
            if provider == "auth_proxy":
                self._required(parser, section, "snapshot_file", errors)
                self._required(parser, section, "signature_secret_ref", errors)

    def _validate_security(
        self, parser: configparser.ConfigParser, policy: InstallerScopePolicy, errors: list[str]
    ) -> None:
        if not parser.has_section("security"):
            return
        transport = parser.get("security", "transport", fallback="").strip().lower()
        tls_min_version = parser.get("security", "tls_min_version", fallback="").strip()
        mtls_required = parser.get("security", "mtls_required", fallback="").strip().lower()
        loopback_only = parser.get("security", "loopback_only", fallback="false").strip().lower()
        if transport not in {"local", "tls", "mtls"}:
            errors.append("security.transport must be local, tls or mtls")
        if tls_min_version != "TLSv1.3":
            errors.append("security.tls_min_version must be TLSv1.3")
        if mtls_required not in {"true", "false"}:
            errors.append("security.mtls_required must be true or false")
        if loopback_only not in {"true", "false"}:
            errors.append("security.loopback_only must be true or false")
        if policy.edition == "lite":
            if transport != "local":
                errors.append("lite security.transport must be local")
            if mtls_required != "false":
                errors.append("lite security.mtls_required must be false")
            if loopback_only != "true":
                errors.append("lite security.loopback_only must be true")
            return
        if transport != "mtls":
            errors.append(f"{policy.key} security.transport must be mtls")
        if mtls_required != "true":
            errors.append(f"{policy.key} security.mtls_required must be true")
        for option in ("server_ca_cert_ref", "client_cert_ref", "client_key_ref"):
            value = parser.get("security", option, fallback="").strip()
            if value and not value.startswith(("file://", "vault://", "sops://", "kms://")):
                errors.append(
                    "security." + option + " must reference file://, vault://, sops:// or kms://"
                )
        trusted_proxy_cidrs = parser.get("security", "trusted_proxy_cidrs", fallback="").strip()
        if trusted_proxy_cidrs:
            for cidr in (item.strip() for item in trusted_proxy_cidrs.split(",") if item.strip()):
                try:
                    ipaddress.ip_network(cidr, strict=False)
                except ValueError:
                    errors.append("security.trusted_proxy_cidrs contains invalid CIDR: " + cidr)

    def _render_actions(
        self,
        policy: InstallerScopePolicy,
        application_filesystem: InstallerFilesystemPlan | None,
        postgresql_filesystem: InstallerFilesystemPlan | None,
        postgresql_plan: InstallerPostgreSQLDeploymentPlan | None,
        postgresql_ha_plan: InstallerPostgreSQLHaPlan | None,
    ) -> tuple[str, ...]:
        actions = [
            "infer edition and scope from installer directory",
            "validate minimal install.ini without edition, scope, service or operations fields",
            f"render adapted systemd unit {policy.service} from installer internals",
        ]
        if application_filesystem is not None:
            actions.append(
                "create or validate internal application LVM filesystem "
                f"{application_filesystem.mountpoint}/ with openinfra ownership"
            )
        if policy.managed_postgresql and postgresql_plan is not None:
            actions.extend(
                (
                    "detect PostgreSQL client/server availability before backend installation",
                    "install PostgreSQL packages if absent via "
                    + " ".join(postgresql_plan.install_command),
                    "resolve or create PostgreSQL system account from OS packaging",
                    "create PostgreSQL LVM filesystem with internal mountpoint /data/openinfra/",
                    "create internal symlink /opt/openinfra/data -> /data/openinfra/",
                    "render PostgreSQL systemd PGDATA override under /data/openinfra/",
                    "initialize PostgreSQL PGDATA under /data/openinfra/",
                    "enable and start internal PostgreSQL service "
                    + postgresql_plan.os_profile.service,
                    "verify PostgreSQL readiness with " + " ".join(postgresql_plan.verify_command),
                    "apply backend migrations from /opt/openinfra/share/migrations/postgresql "
                    "before service enablement",
                )
            )
        if postgresql_ha_plan is not None:
            actions.extend(
                (
                    "render native PostgreSQL HA/PITR configuration under /opt/openinfra/config",
                    "enable WAL archiving to /data/openinfra/pitr with idempotent archive command",
                    "prepare physical backup directory /data/openinfra/backups",
                )
            )
            if postgresql_ha_plan.replication_enabled:
                actions.append(
                    "enable near-real-time PostgreSQL streaming replication from "
                    "identity.peer_nodes with internal ports and operator-controlled failover"
                )
            else:
                actions.append(
                    "run managed standalone PostgreSQL with PITR-ready backup primitives"
                )
        if postgresql_filesystem is not None:
            actions.append(
                "enforce PostgreSQL LV maximum from install.ini storage.lvsize "
                f"for {postgresql_filesystem.mountpoint}/"
            )
        if policy.scope == "all-in-one":
            actions.append(
                "force local app+database session mode without LDAP, network or API sections"
            )
        if policy.scope == "server" and policy.edition in {"pro", "enterprise"}:
            actions.append(
                "configure trusted SAML/LDAP identity validation, Team Sync, RBAC and audit "
                "without accepting provider secrets from client requests"
            )
        if policy.scope == "web":
            actions.append(
                "install web frontend without PostgreSQL storage deployment; browser sessions "
                "use the server-side BFF and trusted backend identity endpoints"
            )
        if policy.scope == "agent":
            actions.append(
                "enroll enterprise discovery proxy collector agent through backend API without "
                "direct database access, PostgreSQL storage, PGDATA or backend migrations"
            )
        actions.extend(
            (
                "create Python virtual environment under /opt/openinfra/venv",
                "materialize runtime configuration in /opt/openinfra/config/openinfra.conf "
                "with /etc/openinfra symlink",
                "create hidden installation lock /opt/openinfra/config/.openinfra-installed.lock",
                "install scope production requirements from installers/requirements",
                "install OpenInfra application package into the managed virtual environment",
                "secure backend/frontend/agent-proxy exchanges with TLS 1.3 and mandatory mTLS "
                "outside Lite",
                "execute installer changes with transactional rollback on failure",
                f"enable and restart {policy.service} after successful validation",
            )
        )
        return tuple(actions)
