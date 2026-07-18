from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import stat
import subprocess  # nosec B404
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

from openinfra import __version__
from openinfra.domain.common import OpenInfraError
from openinfra.infrastructure.oracle import OracleMigrationCatalog


class Gate11QualificationError(Exception):
    """Raised when REL-12 qualification evidence cannot be produced or trusted."""


@dataclass(frozen=True, slots=True)
class Gate11CommandResult:
    returncode: int
    stdout: str
    stderr: str


class Gate11CommandRunner:
    def run(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 300,
        environment: dict[str, str] | None = None,
    ) -> Gate11CommandResult:
        if not command or any(not str(item).strip() for item in command):
            raise Gate11QualificationError("qualification command cannot be empty")
        if timeout_seconds < 1 or timeout_seconds > 3600:
            raise Gate11QualificationError("timeout_seconds must be between 1 and 3600")
        completed = subprocess.run(  # noqa: S603  # nosec B603
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
        )
        return Gate11CommandResult(completed.returncode, completed.stdout, completed.stderr)


@dataclass(frozen=True, slots=True)
class Gate11HttpResponse:
    status_code: int
    payload: dict[str, object]


class Gate11HttpProbe:
    def fetch(self, url: str, *, timeout_seconds: int = 10) -> Gate11HttpResponse:
        normalized = url.strip()
        if not normalized.startswith(("http://127.0.0.1", "http://localhost", "https://")):
            raise Gate11QualificationError(
                "qualification HTTP URLs must use HTTPS or a loopback HTTP address"
            )
        request = urllib.request.Request(  # noqa: S310
            normalized,
            headers={"Accept": "application/json", "User-Agent": f"openinfra-gate11/{__version__}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(  # noqa: S310  # nosec B310
                request, timeout=timeout_seconds
            ) as response:
                status_code = int(response.status)
                raw = response.read(1_048_577)
        except (OSError, urllib.error.URLError) as exc:
            raise Gate11QualificationError(
                f"HTTP qualification probe failed for {normalized}"
            ) from exc
        if len(raw) > 1_048_576:
            raise Gate11QualificationError("HTTP qualification response exceeds 1 MiB")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Gate11QualificationError(
                "HTTP qualification response must be UTF-8 JSON"
            ) from exc
        if not isinstance(value, dict):
            raise Gate11QualificationError("HTTP qualification response root must be an object")
        return Gate11HttpResponse(status_code, {str(key): item for key, item in value.items()})


class Gate11AccountResolver:
    @staticmethod
    def user_ids(username: str) -> tuple[int, int]:
        if os.name != "posix":
            raise Gate11QualificationError("systemd qualification requires a POSIX host")
        password_database: Any = importlib.import_module("pwd")
        entry = password_database.getpwnam(username)
        return int(entry.pw_uid), int(entry.pw_gid)


class Gate11Input:
    _safe_identifier = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")

    @classmethod
    def identifier(cls, value: str, field: str) -> str:
        normalized = value.strip()
        if cls._safe_identifier.fullmatch(normalized) is None:
            raise Gate11QualificationError(f"{field} is invalid")
        return normalized

    @staticmethod
    def source_commit(value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 40 or any(char not in "0123456789abcdef" for char in normalized):
            raise Gate11QualificationError("source_commit must be a full lowercase SHA-1")
        return normalized

    @staticmethod
    def utc_datetime(value: object, field: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise Gate11QualificationError(f"{field} must be an ISO-8601 timestamp")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise Gate11QualificationError(f"{field} must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise Gate11QualificationError(f"{field} must contain a timezone")
        return parsed.astimezone(UTC)

    @staticmethod
    def regular_file(path: Path, field: str, *, private: bool = False) -> Path:
        try:
            value = path.lstat()
        except OSError as exc:
            raise Gate11QualificationError(f"{field} cannot be read: {path}") from exc
        if stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode):
            raise Gate11QualificationError(f"{field} must be a regular non-symbolic file")
        if private and value.st_mode & 0o077:
            raise Gate11QualificationError(f"{field} must not be readable by group or others")
        return path

    @staticmethod
    def json_object(raw: str, context: str) -> dict[str, object]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise Gate11QualificationError(f"{context} did not return valid JSON") from exc
        if not isinstance(value, dict):
            raise Gate11QualificationError(f"{context} JSON root must be an object")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def sha256_bytes(raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def sha256_file(path: Path) -> str:
        return Gate11Input.sha256_bytes(path.read_bytes())


class Gate11Report:
    @classmethod
    def build(
        cls,
        *,
        report_kind: str,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
        checks: dict[str, bool],
        details: dict[str, object],
        failures: list[str] | None = None,
        generated_at: datetime | None = None,
    ) -> dict[str, object]:
        normalized_candidate = Gate11Input.identifier(candidate_id, "candidate_id")
        normalized_commit = Gate11Input.source_commit(source_commit)
        normalized_environment = Gate11Input.identifier(environment_id, "environment_id")
        normalized_kind = Gate11Input.identifier(report_kind, "report_kind")
        if not checks:
            raise Gate11QualificationError("qualification report must contain checks")
        normalized_checks = {str(key): bool(value) for key, value in checks.items()}
        failure_list = list(failures or [])
        failure_list.extend(
            name + " failed" for name, passed in normalized_checks.items() if not passed
        )
        unique_failures = list(dict.fromkeys(failure_list))
        complete = not unique_failures and all(normalized_checks.values())
        return {
            "schema_version": 1,
            "report_kind": normalized_kind,
            "release_version": __version__,
            "gate_id": "GATE-11",
            "release_id": "REL-12",
            "candidate_id": normalized_candidate,
            "source_commit": normalized_commit,
            "environment_id": normalized_environment,
            "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
            "complete": complete,
            "status": "passed" if complete else "failed",
            "checks": normalized_checks,
            "details": details,
            "failures": unique_failures,
        }

    @staticmethod
    def write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)


class Gate11ContractsQualification:
    REQUIRED_SYSTEMD_ASSETS: ClassVar[tuple[str, ...]] = (
        "openinfra-runtime-secrets.service",
        "openinfra-migrate.service",
        "openinfra-team-sync.service",
        "openinfra-team-sync.timer",
    )

    @classmethod
    def run(
        cls,
        *,
        project_root: Path,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
    ) -> dict[str, object]:
        root = project_root.resolve()
        postgres_root = root / "installers/migrations/postgresql"
        oracle_root = root / "installers/migrations/oracle"
        postgres_names = tuple(
            path.name for path in sorted(postgres_root.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        )
        oracle_names = tuple(
            path.name for path in sorted(oracle_root.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        )
        manifest_path = oracle_root / "manifest.json"
        catalog_valid = False
        manifest_entries = 0
        try:
            migrations = OracleMigrationCatalog(oracle_root, postgres_root).migrations()
            manifest = Gate11Input.json_object(
                manifest_path.read_text(encoding="utf-8"), "Oracle manifest"
            )
            raw_entries = manifest.get("migrations")
            manifest_entries = len(raw_entries) if isinstance(raw_entries, list) else 0
            catalog_valid = len(migrations) == len(oracle_names) == manifest_entries
        except (OSError, Gate11QualificationError, OpenInfraError):
            catalog_valid = False
        systemd_root = root / "installers/systemd"
        systemd_present = all(
            (systemd_root / name).is_file() for name in cls.REQUIRED_SYSTEMD_ASSETS
        )
        workflow_path = root / ".github/workflows/advanced-identity-oracle.yml"
        workflow = workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else ""
        workflow_complete = all(
            fragment in workflow
            for fragment in (
                "GATE-11 Oracle migration parity",
                "openinfra-gate11 contracts",
                "openinfra-gate11 assemble",
                "openinfra-gate11 evaluate",
                "runs-on: [self-hosted, linux, openinfra-gate11]",
            )
        )
        package_source = (root / "pyproject.toml").read_text(encoding="utf-8")
        entrypoint_present = "openinfra-gate11" in package_source
        checks = {
            "postgresql_catalog_present": len(postgres_names) > 0,
            "oracle_catalog_present": len(oracle_names) > 0,
            "migration_filenames_match": postgres_names == oracle_names,
            "oracle_manifest_valid": catalog_valid,
            "systemd_assets_present": systemd_present,
            "gate11_workflow_complete": workflow_complete,
            "gate11_entrypoint_present": entrypoint_present,
        }
        return Gate11Report.build(
            report_kind="advanced-identity-oracle-contracts",
            candidate_id=candidate_id,
            source_commit=source_commit,
            environment_id=environment_id,
            checks=checks,
            details={
                "postgresql_migration_count": len(postgres_names),
                "oracle_migration_count": len(oracle_names),
                "oracle_manifest_entry_count": manifest_entries,
                "systemd_assets": list(cls.REQUIRED_SYSTEMD_ASSETS),
            },
        )


class Gate11OracleQualification:
    @classmethod
    def run(
        cls,
        *,
        runner: Gate11CommandRunner,
        openinfra_binary: str,
        migrations_root: Path,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
        timeout_seconds: int = 900,
    ) -> dict[str, object]:
        root = migrations_root.resolve()
        manifest_path = Gate11Input.regular_file(root / "manifest.json", "Oracle manifest")
        expected_catalog_count = len(tuple(root.glob("[0-9][0-9][0-9][0-9]_*.sql")))
        if expected_catalog_count < 1:
            raise Gate11QualificationError("Oracle migration catalog is empty")
        common = ["--backend", "oracle", "--root", str(root)]
        apply_result = runner.run(
            [openinfra_binary, "database", "apply-migrations", *common],
            timeout_seconds=timeout_seconds,
        )
        if apply_result.returncode != 0:
            raise Gate11QualificationError(
                "Oracle migration application failed: " + apply_result.stderr.strip()[:1000]
            )
        apply_payload = Gate11Input.json_object(apply_result.stdout, "Oracle apply-migrations")
        status_result = runner.run(
            [openinfra_binary, "database", "status", *common],
            timeout_seconds=timeout_seconds,
        )
        if status_result.returncode != 0:
            raise Gate11QualificationError(
                "Oracle migration status failed: " + status_result.stderr.strip()[:1000]
            )
        status = Gate11Input.json_object(status_result.stdout, "Oracle database status")
        drift = status.get("drift")
        checks = {
            "backend_is_oracle": status.get("backend") == "oracle",
            "catalog_count_matches": status.get("expected_count") == expected_catalog_count,
            "all_migrations_applied": status.get("applied_count") == expected_catalog_count,
            "schema_is_current": status.get("current") is True,
            "migration_drift_empty": isinstance(drift, list) and not drift,
            "apply_backend_is_oracle": apply_payload.get("backend") == "oracle",
        }
        newly_applied = apply_payload.get("newly_applied")
        return Gate11Report.build(
            report_kind="oracle-live-qualification",
            candidate_id=candidate_id,
            source_commit=source_commit,
            environment_id=environment_id,
            checks=checks,
            details={
                "catalog_count": expected_catalog_count,
                "applied_count": status.get("applied_count"),
                "newly_applied_count": len(newly_applied) if isinstance(newly_applied, list) else 0,
                "manifest_sha256": Gate11Input.sha256_file(manifest_path),
            },
        )


class Gate11SamlQualification:
    @classmethod
    def run(
        cls,
        *,
        runner: Gate11CommandRunner,
        openinfra_binary: str,
        request_json: Path,
        backend: str,
        tenant: str,
        edition: str,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
        timeout_seconds: int = 300,
    ) -> dict[str, object]:
        request_path = Gate11Input.regular_file(request_json, "SAML request", private=True)
        command = [
            openinfra_binary,
            "auth",
            "saml-login",
            "--backend",
            backend,
            "--tenant",
            tenant,
            "--edition",
            edition,
            "--actor",
            "gate11-live-qualification",
            "--request-json",
            str(request_path),
        ]
        result = runner.run(command, timeout_seconds=timeout_seconds)
        if result.returncode != 0:
            raise Gate11QualificationError(
                "SAML live qualification failed: " + result.stderr.strip()[:1000]
            )
        payload = Gate11Input.json_object(result.stdout, "SAML login")
        roles = payload.get("roles")
        mapped_groups = payload.get("mapped_groups")
        token = payload.get("token")
        subject = str(payload.get("subject", "")).strip()
        checks = {
            "provider_is_saml": payload.get("provider") == "saml",
            "subject_present": bool(subject),
            "roles_mapped": isinstance(roles, list) and bool(roles),
            "groups_mapped": isinstance(mapped_groups, list) and bool(mapped_groups),
            "token_issued": isinstance(token, str) and len(token) >= 32,
            "tenant_matches": payload.get("tenant_id") == tenant,
        }
        return Gate11Report.build(
            report_kind="saml-live-qualification",
            candidate_id=candidate_id,
            source_commit=source_commit,
            environment_id=environment_id,
            checks=checks,
            details={
                "backend": backend,
                "tenant": tenant,
                "subject_sha256": Gate11Input.sha256_bytes(subject.encode("utf-8"))
                if subject
                else "",
                "role_count": len(roles) if isinstance(roles, list) else 0,
                "mapped_group_count": len(mapped_groups) if isinstance(mapped_groups, list) else 0,
                "external_group_count": payload.get("external_group_count", 0),
                "token_prefix": str(payload.get("token_prefix", ""))[:16],
                "request_sha256": Gate11Input.sha256_file(request_path),
            },
        )


class Gate11TeamSyncQualification:
    MUTATION_FIELDS: ClassVar[tuple[str, ...]] = (
        "created_users",
        "updated_users",
        "deactivated_users",
        "created_groups",
        "updated_groups",
        "added_memberships",
        "removed_memberships",
    )

    @classmethod
    def run(
        cls,
        *,
        runner: Gate11CommandRunner,
        openinfra_binary: str,
        token_file: Path,
        source: str,
        backend: str,
        tenant: str,
        edition: str,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
        timeout_seconds: int = 600,
    ) -> dict[str, object]:
        token_path = Gate11Input.regular_file(token_file, "Team Sync token", private=True)
        common = [
            openinfra_binary,
            "identity",
            "team-sync",
            "--backend",
            backend,
            "--tenant",
            tenant,
            "--edition",
            edition,
            "--actor",
            "gate11-live-qualification",
            "--source",
            source,
            "--token-file",
            str(token_path),
        ]
        first = cls._execute(runner, common, timeout_seconds, "first Team Sync")
        second = cls._execute(runner, common, timeout_seconds, "second Team Sync")
        second_zero = all(cls._counter(second, field) == 0 for field in cls.MUTATION_FIELDS)
        checks = {
            "source_id_matches": first.get("source_id") == source
            and second.get("source_id") == source,
            "fingerprint_stable": bool(first.get("fingerprint"))
            and first.get("fingerprint") == second.get("fingerprint"),
            "second_run_idempotent": second_zero,
            "counters_are_non_negative": all(
                cls._counter(payload, field) >= 0
                for payload in (first, second)
                for field in cls.MUTATION_FIELDS
            ),
        }
        return Gate11Report.build(
            report_kind="team-sync-live-qualification",
            candidate_id=candidate_id,
            source_commit=source_commit,
            environment_id=environment_id,
            checks=checks,
            details={
                "backend": backend,
                "tenant": tenant,
                "source_id": source,
                "fingerprint": str(second.get("fingerprint", "")),
                "first_run": {field: cls._counter(first, field) for field in cls.MUTATION_FIELDS},
                "second_run": {field: cls._counter(second, field) for field in cls.MUTATION_FIELDS},
            },
        )

    @staticmethod
    def _execute(
        runner: Gate11CommandRunner,
        command: list[str],
        timeout_seconds: int,
        context: str,
    ) -> dict[str, object]:
        result = runner.run(command, timeout_seconds=timeout_seconds)
        if result.returncode != 0:
            raise Gate11QualificationError(context + " failed: " + result.stderr.strip()[:1000])
        return Gate11Input.json_object(result.stdout, context)

    @staticmethod
    def _counter(payload: dict[str, object], field: str) -> int:
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            return -1
        return value


class Gate11SystemdQualification:
    SERVICE_UNITS: ClassVar[dict[str, str]] = {
        "openinfra-runtime-secrets.service": "root",
        "openinfra-migrate.service": "openinfra",
        "openinfra.service": "openinfra",
        "openinfra-web.service": "openinfra",
        "openinfra-team-sync.service": "openinfra",
    }
    TIMER_UNIT: ClassVar[str] = "openinfra-team-sync.timer"
    REQUIRED_ENABLED: ClassVar[set[str]] = {
        "openinfra-runtime-secrets.service",
        "openinfra.service",
        "openinfra-web.service",
        "openinfra-team-sync.timer",
    }

    @classmethod
    def run(
        cls,
        *,
        runner: Gate11CommandRunner,
        http_probe: Gate11HttpProbe,
        health_url: str,
        ready_url: str,
        secret_directory: Path,
        token_file: Path,
        service_user: str,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
    ) -> dict[str, object]:
        units: dict[str, dict[str, str]] = {}
        for unit in (*cls.SERVICE_UNITS, cls.TIMER_UNIT):
            units[unit] = cls._unit_properties(runner, unit)
        service_uid, service_gid = Gate11AccountResolver.user_ids(service_user)
        directory_status = secret_directory.lstat()
        token_status = token_file.lstat()
        secret_checks = {
            "secret_directory_regular": stat.S_ISDIR(directory_status.st_mode)
            and not stat.S_ISLNK(directory_status.st_mode),
            "secret_directory_mode_0700": stat.S_IMODE(directory_status.st_mode) == 0o700,
            "secret_directory_owned_by_service": directory_status.st_uid == service_uid
            and directory_status.st_gid == service_gid,
            "token_regular_non_symlink": stat.S_ISREG(token_status.st_mode)
            and not stat.S_ISLNK(token_status.st_mode),
            "token_mode_0400": stat.S_IMODE(token_status.st_mode) == 0o400,
            "token_owned_by_service": token_status.st_uid == service_uid
            and token_status.st_gid == service_gid,
        }
        service_state_ok = all(
            cls._service_state_ok(name, values) for name, values in units.items()
        )
        hardening_ok = all(
            values.get("NoNewPrivileges") == "yes"
            and values.get("PrivateTmp") == "yes"
            and values.get("ProtectSystem") == "strict"
            and values.get("ProtectHome") == "yes"
            for name, values in units.items()
            if name.endswith(".service")
        )
        users_ok = all(
            values.get("User", "") == expected_user
            for name, expected_user in cls.SERVICE_UNITS.items()
            for values in (units[name],)
        )
        enabled_ok = all(
            units[name].get("UnitFileState") == "enabled" for name in cls.REQUIRED_ENABLED
        ) and all(units[name].get("LoadState") == "loaded" for name in units)
        health = http_probe.fetch(health_url)
        readiness = http_probe.fetch(ready_url)
        checks = {
            "systemd_units_loaded_and_enabled": enabled_ok,
            "systemd_unit_states_valid": service_state_ok,
            "systemd_hardening_active": hardening_ok,
            "systemd_service_users_valid": users_ok,
            "health_endpoint_ready": health.status_code == 200
            and health.payload.get("status") == "ok",
            "readiness_endpoint_ready": readiness.status_code == 200
            and readiness.payload.get("ready") is True,
            **secret_checks,
        }
        return Gate11Report.build(
            report_kind="systemd-live-qualification",
            candidate_id=candidate_id,
            source_commit=source_commit,
            environment_id=environment_id,
            checks=checks,
            details={
                "units": {
                    name: {
                        key: values.get(key, "")
                        for key in (
                            "ActiveState",
                            "SubState",
                            "Result",
                            "UnitFileState",
                            "User",
                        )
                    }
                    for name, values in units.items()
                },
                "health_status_code": health.status_code,
                "readiness_status_code": readiness.status_code,
                "secret_directory": str(secret_directory),
                "token_file": str(token_file),
            },
        )

    @staticmethod
    def _unit_properties(runner: Gate11CommandRunner, unit: str) -> dict[str, str]:
        properties = (
            "LoadState",
            "ActiveState",
            "SubState",
            "Result",
            "UnitFileState",
            "User",
            "Group",
            "NoNewPrivileges",
            "PrivateTmp",
            "ProtectSystem",
            "ProtectHome",
            "ExecMainStatus",
        )
        command = ["systemctl", "show", unit]
        for prop in properties:
            command.extend(("--property", prop))
        result = runner.run(command, timeout_seconds=30)
        if result.returncode != 0:
            raise Gate11QualificationError(
                f"systemd qualification failed for {unit}: {result.stderr.strip()[:500]}"
            )
        values: dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                values[key] = value
        if set(properties).difference(values):
            raise Gate11QualificationError(f"systemd properties are incomplete for {unit}")
        return values

    @classmethod
    def _service_state_ok(cls, name: str, values: dict[str, str]) -> bool:
        if name in {"openinfra.service", "openinfra-web.service"}:
            return values.get("ActiveState") == "active" and values.get("SubState") == "running"
        if name == cls.TIMER_UNIT:
            return values.get("ActiveState") == "active" and values.get("SubState") == "waiting"
        if name == "openinfra-runtime-secrets.service":
            return values.get("ActiveState") == "active" and values.get("Result") == "success"
        return values.get("Result") == "success" and values.get("ExecMainStatus") == "0"


@dataclass(frozen=True, slots=True)
class Gate11EvidencePolicy:
    identifier: str
    report_kind: str
    max_age_hours: int

    @classmethod
    def from_mapping(cls, value: object) -> Gate11EvidencePolicy:
        if not isinstance(value, dict):
            raise Gate11QualificationError("GATE-11 evidence policy entries must be objects")
        identifier = Gate11Input.identifier(str(value.get("id", "")), "evidence id")
        report_kind = Gate11Input.identifier(str(value.get("report_kind", "")), "report_kind")
        max_age_hours = value.get("max_age_hours")
        if (
            not isinstance(max_age_hours, int)
            or isinstance(max_age_hours, bool)
            or max_age_hours < 1
        ):
            raise Gate11QualificationError(f"invalid max_age_hours for {identifier}")
        return cls(identifier, report_kind, max_age_hours)


@dataclass(frozen=True, slots=True)
class Gate11PromotionPolicy:
    required_evidence: tuple[Gate11EvidencePolicy, ...]

    EXPECTED_EVIDENCE: ClassVar[dict[str, str]] = {
        "gate11-contracts": "advanced-identity-oracle-contracts",
        "gate11-oracle-live": "oracle-live-qualification",
        "gate11-saml-live": "saml-live-qualification",
        "gate11-team-sync-live": "team-sync-live-qualification",
        "gate11-systemd-live": "systemd-live-qualification",
    }

    @classmethod
    def load(cls, path: Path) -> Gate11PromotionPolicy:
        payload = Gate11Input.json_object(path.read_text(encoding="utf-8"), "GATE-11 policy")
        if payload.get("schema_version") != 1:
            raise Gate11QualificationError("unsupported GATE-11 policy schema")
        if payload.get("gate_id") != "GATE-11" or payload.get("release_id") != "REL-12":
            raise Gate11QualificationError("GATE-11 policy must target GATE-11 / REL-12")
        raw_evidence = payload.get("required_evidence")
        if not isinstance(raw_evidence, list):
            raise Gate11QualificationError("GATE-11 policy must declare required_evidence")
        evidence = tuple(Gate11EvidencePolicy.from_mapping(item) for item in raw_evidence)
        actual = {item.identifier: item.report_kind for item in evidence}
        if actual != cls.EXPECTED_EVIDENCE:
            raise Gate11QualificationError("GATE-11 evidence catalog is incomplete or unsupported")
        return cls(evidence)


@dataclass(frozen=True, slots=True)
class Gate11EvidenceReference:
    identifier: str
    report_kind: str
    path: str
    sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> Gate11EvidenceReference:
        if not isinstance(value, dict):
            raise Gate11QualificationError("GATE-11 evidence references must be objects")
        identifier = Gate11Input.identifier(str(value.get("id", "")), "evidence id")
        report_kind = Gate11Input.identifier(str(value.get("report_kind", "")), "report_kind")
        path = str(value.get("path", "")).strip()
        sha256 = str(value.get("sha256", "")).strip().lower()
        if not path or Path(path).is_absolute():
            raise Gate11QualificationError("GATE-11 evidence path must be relative")
        if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise Gate11QualificationError("GATE-11 evidence SHA-256 is invalid")
        return cls(identifier, report_kind, path, sha256)

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.identifier,
            "report_kind": self.report_kind,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class Gate11PromotionManifest:
    candidate_id: str
    source_commit: str
    environment_id: str
    generated_at: datetime
    evidence: tuple[Gate11EvidenceReference, ...]

    @classmethod
    def load(cls, path: Path) -> Gate11PromotionManifest:
        payload = Gate11Input.json_object(path.read_text(encoding="utf-8"), "GATE-11 manifest")
        if payload.get("schema_version") != 1:
            raise Gate11QualificationError("unsupported GATE-11 manifest schema")
        if payload.get("gate_id") != "GATE-11" or payload.get("release_version") != __version__:
            raise Gate11QualificationError("GATE-11 manifest release metadata mismatch")
        candidate_id = Gate11Input.identifier(str(payload.get("candidate_id", "")), "candidate_id")
        source_commit = Gate11Input.source_commit(str(payload.get("source_commit", "")))
        environment_id = Gate11Input.identifier(
            str(payload.get("environment_id", "")), "environment_id"
        )
        generated_at = Gate11Input.utc_datetime(
            payload.get("generated_at"), "manifest generated_at"
        )
        raw_evidence = payload.get("evidence")
        if not isinstance(raw_evidence, list):
            raise Gate11QualificationError("GATE-11 manifest must list evidence")
        evidence = tuple(Gate11EvidenceReference.from_mapping(item) for item in raw_evidence)
        actual = {item.identifier: item.report_kind for item in evidence}
        if actual != Gate11PromotionPolicy.EXPECTED_EVIDENCE:
            raise Gate11QualificationError("GATE-11 manifest evidence catalog mismatch")
        return cls(candidate_id, source_commit, environment_id, generated_at, evidence)


class Gate11PromotionAssembler:
    @classmethod
    def assemble(
        cls,
        *,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
        sources: dict[str, Path],
        evidence_root: Path,
        generated_at: datetime | None = None,
    ) -> dict[str, object]:
        normalized_candidate = Gate11Input.identifier(candidate_id, "candidate_id")
        normalized_commit = Gate11Input.source_commit(source_commit)
        normalized_environment = Gate11Input.identifier(environment_id, "environment_id")
        expected = Gate11PromotionPolicy.EXPECTED_EVIDENCE
        if set(sources) != set(expected):
            raise Gate11QualificationError("all GATE-11 evidence sources are required")
        evidence_root.mkdir(parents=True, exist_ok=True)
        references: list[dict[str, str]] = []
        for identifier, report_kind in expected.items():
            source = Gate11Input.regular_file(sources[identifier], identifier)
            raw = source.read_bytes()
            payload = Gate11Input.json_object(raw.decode("utf-8"), identifier)
            cls._assert_source_metadata(
                payload,
                report_kind=report_kind,
                candidate_id=normalized_candidate,
                source_commit=normalized_commit,
                environment_id=normalized_environment,
            )
            target = evidence_root / f"{identifier}.json"
            temporary = target.with_suffix(".json.tmp")
            temporary.write_bytes(raw)
            temporary.replace(target)
            references.append(
                {
                    "id": identifier,
                    "report_kind": report_kind,
                    "path": target.name,
                    "sha256": Gate11Input.sha256_bytes(raw),
                }
            )
        return {
            "schema_version": 1,
            "gate_id": "GATE-11",
            "release_id": "REL-12",
            "release_version": __version__,
            "candidate_id": normalized_candidate,
            "source_commit": normalized_commit,
            "environment_id": normalized_environment,
            "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
            "evidence": references,
        }

    @staticmethod
    def _assert_source_metadata(
        payload: dict[str, object],
        *,
        report_kind: str,
        candidate_id: str,
        source_commit: str,
        environment_id: str,
    ) -> None:
        expected = {
            "schema_version": 1,
            "gate_id": "GATE-11",
            "release_id": "REL-12",
            "release_version": __version__,
            "report_kind": report_kind,
            "candidate_id": candidate_id,
            "source_commit": source_commit,
            "environment_id": environment_id,
        }
        mismatched = [key for key, value in expected.items() if payload.get(key) != value]
        if mismatched:
            raise Gate11QualificationError(
                "GATE-11 evidence metadata mismatch: " + ", ".join(mismatched)
            )


@dataclass(frozen=True, slots=True)
class Gate11CriterionResult:
    identifier: str
    report_kind: str
    status: str
    detail: str
    evidence_sha256: str

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.identifier,
            "report_kind": self.report_kind,
            "status": self.status,
            "detail": self.detail,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class Gate11PromotionDecision:
    candidate_id: str
    source_commit: str
    environment_id: str
    evaluated_at: datetime
    criteria: tuple[Gate11CriterionResult, ...]

    @property
    def authorized_for_rel12(self) -> bool:
        return bool(self.criteria) and all(item.passed for item in self.criteria)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "report_kind": "advanced-identity-oracle-promotion-decision",
            "release_version": __version__,
            "gate_id": "GATE-11",
            "release_id": "REL-12",
            "candidate_id": self.candidate_id,
            "source_commit": self.source_commit,
            "environment_id": self.environment_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "authorized_for_rel12": self.authorized_for_rel12,
            "status": "go" if self.authorized_for_rel12 else "no-go",
            "criteria": [item.as_dict() for item in self.criteria],
        }


class Gate11PromotionEvaluator:
    @classmethod
    def evaluate(
        cls,
        *,
        policy: Gate11PromotionPolicy,
        manifest: Gate11PromotionManifest,
        evidence_root: Path,
        now: datetime | None = None,
    ) -> Gate11PromotionDecision:
        evaluated_at = (now or datetime.now(UTC)).astimezone(UTC)
        references = {item.identifier: item for item in manifest.evidence}
        criteria = tuple(
            cls._inspect(
                evidence_policy,
                references[evidence_policy.identifier],
                manifest,
                evidence_root,
                evaluated_at,
            )
            for evidence_policy in policy.required_evidence
        )
        return Gate11PromotionDecision(
            manifest.candidate_id,
            manifest.source_commit,
            manifest.environment_id,
            evaluated_at,
            criteria,
        )

    @classmethod
    def _inspect(
        cls,
        policy: Gate11EvidencePolicy,
        reference: Gate11EvidenceReference,
        manifest: Gate11PromotionManifest,
        evidence_root: Path,
        now: datetime,
    ) -> Gate11CriterionResult:
        actual_hash = ""
        try:
            path = cls._resolve(evidence_root, reference.path)
            raw = path.read_bytes()
            actual_hash = Gate11Input.sha256_bytes(raw)
            if actual_hash != reference.sha256:
                raise Gate11QualificationError("evidence SHA-256 mismatch")
            payload = Gate11Input.json_object(raw.decode("utf-8"), policy.identifier)
            cls._validate_payload(policy, payload, manifest, now)
        except (OSError, UnicodeDecodeError, Gate11QualificationError) as exc:
            return Gate11CriterionResult(
                policy.identifier,
                policy.report_kind,
                "failed",
                str(exc),
                actual_hash,
            )
        return Gate11CriterionResult(
            policy.identifier,
            policy.report_kind,
            "passed",
            "required evidence is complete, current and cryptographically pinned",
            actual_hash,
        )

    @staticmethod
    def _resolve(root: Path, relative: str) -> Path:
        resolved_root = root.resolve()
        candidate = (resolved_root / relative).resolve()
        if candidate == resolved_root or resolved_root not in candidate.parents:
            raise Gate11QualificationError("evidence path escapes evidence root")
        if not candidate.is_file():
            raise Gate11QualificationError("evidence file is missing")
        return candidate

    @staticmethod
    def _validate_payload(
        policy: Gate11EvidencePolicy,
        payload: dict[str, object],
        manifest: Gate11PromotionManifest,
        now: datetime,
    ) -> None:
        expected = {
            "schema_version": 1,
            "report_kind": policy.report_kind,
            "release_version": __version__,
            "gate_id": "GATE-11",
            "release_id": "REL-12",
            "candidate_id": manifest.candidate_id,
            "source_commit": manifest.source_commit,
            "environment_id": manifest.environment_id,
            "complete": True,
            "status": "passed",
        }
        mismatched = [key for key, value in expected.items() if payload.get(key) != value]
        if mismatched:
            raise Gate11QualificationError("evidence contract mismatch: " + ", ".join(mismatched))
        checks = payload.get("checks")
        if (
            not isinstance(checks, dict)
            or not checks
            or not all(value is True for value in checks.values())
        ):
            raise Gate11QualificationError("evidence checks are incomplete or failed")
        failures = payload.get("failures")
        if not isinstance(failures, list) or failures:
            raise Gate11QualificationError("evidence contains qualification failures")
        generated_at = Gate11Input.utc_datetime(
            payload.get("generated_at"), "evidence generated_at"
        )
        if generated_at > now + timedelta(minutes=5):
            raise Gate11QualificationError("evidence timestamp is in the future")
        if now - generated_at > timedelta(hours=policy.max_age_hours):
            raise Gate11QualificationError(
                f"evidence is older than the allowed {policy.max_age_hours} hours"
            )


class Gate11QualificationCli:
    @classmethod
    def main(cls) -> int:
        parser = cls._parser()
        args = parser.parse_args()
        try:
            report = cls._dispatch(args)
        except (OSError, KeyError, Gate11QualificationError, subprocess.TimeoutExpired) as exc:
            parser.error(str(exc))
        output = getattr(args, "output", None)
        if output is not None:
            Gate11Report.write_atomic(output, report)
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        enforce = bool(getattr(args, "enforce", False))
        if (
            enforce
            and report.get("authorized_for_rel12") is not True
            and report.get("status")
            not in {
                "passed",
                "go",
            }
        ):
            return 2
        return 0

    @classmethod
    def _dispatch(cls, args: argparse.Namespace) -> dict[str, object]:
        if args.command == "evaluate":
            policy = Gate11PromotionPolicy.load(args.policy)
            manifest = Gate11PromotionManifest.load(args.manifest)
            return Gate11PromotionEvaluator.evaluate(
                policy=policy,
                manifest=manifest,
                evidence_root=args.evidence_root,
            ).as_dict()
        common = {
            "candidate_id": args.candidate_id,
            "source_commit": args.source_commit,
            "environment_id": args.environment_id,
        }
        if args.command == "contracts":
            return Gate11ContractsQualification.run(project_root=args.project_root, **common)
        if args.command == "oracle":
            return Gate11OracleQualification.run(
                runner=Gate11CommandRunner(),
                openinfra_binary=args.openinfra_binary,
                migrations_root=args.migrations_root,
                timeout_seconds=args.timeout_seconds,
                **common,
            )
        if args.command == "saml":
            return Gate11SamlQualification.run(
                runner=Gate11CommandRunner(),
                openinfra_binary=args.openinfra_binary,
                request_json=args.request_json,
                backend=args.backend,
                tenant=args.tenant,
                edition=args.edition,
                timeout_seconds=args.timeout_seconds,
                **common,
            )
        if args.command == "team-sync":
            return Gate11TeamSyncQualification.run(
                runner=Gate11CommandRunner(),
                openinfra_binary=args.openinfra_binary,
                token_file=args.token_file,
                source=args.source,
                backend=args.backend,
                tenant=args.tenant,
                edition=args.edition,
                timeout_seconds=args.timeout_seconds,
                **common,
            )
        if args.command == "systemd":
            return Gate11SystemdQualification.run(
                runner=Gate11CommandRunner(),
                http_probe=Gate11HttpProbe(),
                health_url=args.health_url,
                ready_url=args.ready_url,
                secret_directory=args.secret_directory,
                token_file=args.token_file,
                service_user=args.service_user,
                **common,
            )
        if args.command == "assemble":
            return Gate11PromotionAssembler.assemble(
                sources={
                    "gate11-contracts": args.contracts,
                    "gate11-oracle-live": args.oracle,
                    "gate11-saml-live": args.saml,
                    "gate11-team-sync-live": args.team_sync,
                    "gate11-systemd-live": args.systemd,
                },
                evidence_root=args.evidence_root,
                **common,
            )
        raise Gate11QualificationError("unsupported GATE-11 command")

    @classmethod
    def _parser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Collect and evaluate OpenInfra GATE-11 evidence"
        )
        subparsers = parser.add_subparsers(dest="command", required=True)
        contracts = subparsers.add_parser("contracts", help="validate REL-12 static contracts")
        cls._common_arguments(contracts)
        contracts.add_argument("--project-root", type=Path, default=Path.cwd())
        cls._output_arguments(contracts)

        oracle = subparsers.add_parser("oracle", help="apply and qualify Oracle migrations live")
        cls._common_arguments(oracle)
        cls._binary_arguments(oracle)
        oracle.add_argument("--migrations-root", type=Path, required=True)
        oracle.add_argument("--timeout-seconds", type=int, default=900)
        cls._output_arguments(oracle)

        saml = subparsers.add_parser("saml", help="qualify a signed SAML assertion live")
        cls._common_arguments(saml)
        cls._binary_arguments(saml)
        cls._backend_arguments(saml)
        saml.add_argument("--request-json", type=Path, required=True)
        saml.add_argument("--timeout-seconds", type=int, default=300)
        cls._output_arguments(saml)

        team_sync = subparsers.add_parser("team-sync", help="qualify Team Sync idempotence live")
        cls._common_arguments(team_sync)
        cls._binary_arguments(team_sync)
        cls._backend_arguments(team_sync)
        team_sync.add_argument("--source", required=True)
        team_sync.add_argument("--token-file", type=Path, required=True)
        team_sync.add_argument("--timeout-seconds", type=int, default=600)
        cls._output_arguments(team_sync)

        systemd = subparsers.add_parser("systemd", help="qualify native systemd runtime live")
        cls._common_arguments(systemd)
        systemd.add_argument("--health-url", default="http://127.0.0.1:8080/health")
        systemd.add_argument("--ready-url", default="http://127.0.0.1:8080/ready")
        systemd.add_argument(
            "--secret-directory",
            type=Path,
            default=Path("/var/lib/openinfra/secrets"),
        )
        systemd.add_argument(
            "--token-file",
            type=Path,
            default=Path("/var/lib/openinfra/secrets/bootstrap-token"),
        )
        systemd.add_argument("--service-user", default="openinfra")
        cls._output_arguments(systemd)

        assemble = subparsers.add_parser("assemble", help="assemble immutable GATE-11 evidence")
        cls._common_arguments(assemble)
        assemble.add_argument("--contracts", type=Path, required=True)
        assemble.add_argument("--oracle", type=Path, required=True)
        assemble.add_argument("--saml", type=Path, required=True)
        assemble.add_argument("--team-sync", type=Path, required=True)
        assemble.add_argument("--systemd", type=Path, required=True)
        assemble.add_argument("--evidence-root", type=Path, required=True)
        cls._output_arguments(assemble)

        evaluate = subparsers.add_parser("evaluate", help="evaluate GATE-11 promotion evidence")
        evaluate.add_argument("--policy", type=Path, required=True)
        evaluate.add_argument("--manifest", type=Path, required=True)
        evaluate.add_argument("--evidence-root", type=Path, required=True)
        cls._output_arguments(evaluate)
        return parser

    @staticmethod
    def _common_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--environment-id", required=True)

    @staticmethod
    def _binary_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--openinfra-binary", default="openinfra")

    @staticmethod
    def _backend_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--backend", choices=("postgresql", "oracle"), required=True)
        parser.add_argument("--tenant", default="default")
        parser.add_argument("--edition", choices=("pro", "enterprise"), default="enterprise")

    @staticmethod
    def _output_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")


if __name__ == "__main__":
    raise SystemExit(Gate11QualificationCli.main())
