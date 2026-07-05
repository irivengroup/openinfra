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
    _backend_auth_options = (
        "mode",
        "postgresql_user_ref",
        "postgresql_password_ref",
    )
    _web_auth_options = (
        "mode",
        "postgresql_dsn_ref",
        "postgresql_user_ref",
        "postgresql_password_ref",
    )

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
                    required_sections=("storage",),
                    required_options={"storage": self._storage_options},
                    allowed_options={"storage": self._storage_options},
                ),
                InstallerScopePolicy(
                    edition="pro",
                    scope="server",
                    service="openinfra.service",
                    managed_application_filesystem=True,
                    managed_postgresql=True,
                    apply_backend_migrations=True,
                    postgresql_lvsize_max="100GB",
                    required_sections=("storage", "api", "identity", "auth"),
                    required_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "auth": self._backend_auth_options,
                    },
                    allowed_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "identity": self._identity_options,
                        "auth": self._backend_auth_options,
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
                    required_sections=("api", "auth"),
                    required_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_options,
                    },
                    allowed_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_options,
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
                    required_sections=("storage", "api", "identity", "auth"),
                    required_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "auth": self._backend_auth_options,
                    },
                    allowed_options={
                        "storage": self._storage_options,
                        "api": self._server_api_options,
                        "identity": self._identity_options,
                        "auth": self._backend_auth_options,
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
                    required_sections=("api", "auth"),
                    required_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_options,
                    },
                    allowed_options={
                        "api": self._server_api_options,
                        "auth": self._web_auth_options,
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
                    required_sections=("api",),
                    required_options={"api": self._api_options},
                    allowed_options={"api": self._api_options},
                ),
            )
        }

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
                "After=network-online.target postgresql.service",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                "User=openinfra",
                "Group=openinfra",
                "EnvironmentFile=-/etc/openinfra/openinfra.env",
                "WorkingDirectory=/opt/openinfra",
                "ExecStart=/opt/openinfra/venv/bin/openinfra-api --backend postgresql",
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
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                "User=openinfra",
                "Group=openinfra",
                "EnvironmentFile=-/etc/openinfra/openinfra-web.env",
                "WorkingDirectory=/opt/openinfra/web",
                "ExecStart=/opt/openinfra/venv/bin/python -m http.server 2006 --bind 127.0.0.1",
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

    def _agent_unit(self, service: str) -> str:
        return "\n".join(
            (
                "[Unit]",
                "Description=OpenInfra enterprise discovery collector agent",
                "After=network-online.target",
                "Wants=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                "User=openinfra",
                "Group=openinfra",
                "EnvironmentFile=-/etc/openinfra/openinfra-agent.env",
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
        return InstallerConfigReport(
            path=path,
            edition=policy.edition,
            scope=policy.scope,
            service=policy.service,
            managed_application_filesystem=policy.managed_application_filesystem,
            errors=tuple(errors),
            warnings=tuple(warnings),
            actions=self._render_actions(
                policy, application_filesystem_plan, postgresql_filesystem_plan, postgresql_plan
            ),
            application_filesystem_plan=application_filesystem_plan,
            postgresql_filesystem_plan=postgresql_filesystem_plan,
            postgresql_plan=postgresql_plan,
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
        if mode != "standard":
            errors.append(f"{policy.key} auth.mode must be standard")

    def _render_actions(
        self,
        policy: InstallerScopePolicy,
        application_filesystem: InstallerFilesystemPlan | None,
        postgresql_filesystem: InstallerFilesystemPlan | None,
        postgresql_plan: InstallerPostgreSQLDeploymentPlan | None,
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
                    "apply backend migrations from installers/migrations/postgresql "
                    "before service enablement",
                )
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
        if policy.scope == "web":
            actions.append("install web frontend without PostgreSQL storage deployment")
        if policy.scope == "agent":
            actions.append(
                "enroll enterprise discovery agent through backend API without direct database "
                "access, PostgreSQL storage, PGDATA or backend migrations"
            )
        actions.extend(
            (
                "create Python virtual environment under /opt/openinfra/venv",
                "install scope production requirements from installers/requirements",
                "install OpenInfra application package into the managed virtual environment",
                "execute installer changes with transactional rollback on failure",
                f"enable and restart {policy.service} after successful validation",
            )
        )
        return tuple(actions)
