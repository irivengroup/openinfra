from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openinfra import __version__


class Gate12QualificationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Gate12Control:
    identifier: str
    passed: bool
    detail: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class Gate12Report:
    schema_version: int
    gate_id: str
    release_version: str
    candidate_id: str
    source_commit: str
    generated_at: datetime
    controls: tuple[Gate12Control, ...]

    @property
    def passed(self) -> bool:
        return all(control.passed for control in self.controls)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "gate_id": self.gate_id,
            "release_version": self.release_version,
            "candidate_id": self.candidate_id,
            "source_commit": self.source_commit,
            "generated_at": self.generated_at.isoformat(),
            "status": "passed" if self.passed else "failed",
            "controls": [control.as_dict() for control in self.controls],
        }


@dataclass(frozen=True, slots=True)
class Gate12Policy:
    schema_version: int
    gate_id: str
    release_id: str
    required_controls: tuple[str, ...]

    EXPECTED_CONTROLS = (
        "license-domain-cryptography",
        "storage-parity",
        "runtime-enforcement",
        "cli-http-contracts",
        "installer-offline-bootstrap",
        "operator-notifications",
        "private-authority-key-exclusion",
    )

    @classmethod
    def load(cls, path: Path) -> Gate12Policy:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Gate12QualificationError(f"policy is unreadable: {path}") from exc
        if not isinstance(payload, dict):
            raise Gate12QualificationError("policy must be a JSON object")
        if payload.get("schema_version") != 1:
            raise Gate12QualificationError("unsupported policy schema")
        if payload.get("gate_id") != "GATE-12" or payload.get("release_id") != "REL-13":
            raise Gate12QualificationError("policy must target GATE-12 / REL-13")
        controls = payload.get("required_controls")
        if not isinstance(controls, list) or not all(isinstance(item, str) for item in controls):
            raise Gate12QualificationError("required_controls must be a string list")
        normalized = tuple(controls)
        if normalized != cls.EXPECTED_CONTROLS:
            raise Gate12QualificationError(
                "required_controls are incomplete or incorrectly ordered"
            )
        return cls(1, "GATE-12", "REL-13", normalized)


class Gate12Qualification:
    POLICY_PATH = Path("docs/release/offline-runtime-licensing-promotion-policy.json")

    def collect(
        self,
        *,
        project_root: Path,
        candidate_id: str,
        source_commit: str,
        now: datetime | None = None,
        enforce: bool = False,
    ) -> Gate12Report:
        root = project_root.resolve()
        if not root.is_dir() or not (root / "pyproject.toml").is_file():
            raise Gate12QualificationError("project root is invalid")
        candidate = candidate_id.strip()
        if not candidate or len(candidate) > 160:
            raise Gate12QualificationError("candidate_id must contain between 1 and 160 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit):
            raise Gate12QualificationError("source_commit must be a 40-character SHA-1")
        policy = Gate12Policy.load(root / self.POLICY_PATH)
        controls = (
            self._domain_control(root),
            self._storage_control(root),
            self._runtime_control(root),
            self._interface_control(root),
            self._installer_control(root),
            self._notification_control(root),
            self._security_control(root),
        )
        identifiers = tuple(control.identifier for control in controls)
        if identifiers != policy.required_controls:
            raise Gate12QualificationError("qualification does not match its policy")
        report = Gate12Report(
            1,
            "GATE-12",
            __version__,
            candidate,
            source_commit.lower(),
            now or datetime.now(UTC),
            controls,
        )
        if enforce and not report.passed:
            failed = ", ".join(c.identifier for c in controls if not c.passed)
            raise Gate12QualificationError(f"GATE-12 failed: {failed}")
        return report

    def write(self, output: Path, report: Gate12Report) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(report.as_dict(), stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(output)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _domain_control(self, root: Path) -> Gate12Control:
        return self._source_control(
            "license-domain-cryptography",
            root,
            {
                "src/openinfra/domain/licensing.py": ("LicenseEntitlement", "grace_days"),
                "src/openinfra/infrastructure/licensing.py": ("Ed25519", "verify_entitlement"),
                "tests/unit/test_runtime_offline_licensing.py": ("clock_rollback", "tampering"),
            },
        )

    def _storage_control(self, root: Path) -> Gate12Control:
        return self._source_control(
            "storage-parity",
            root,
            {
                "src/openinfra/infrastructure/json_store.py": ("JsonLicenseRepository",),
                "src/openinfra/infrastructure/postgresql.py": (
                    "PostgreSQLLicenseRepository",
                    "FOR UPDATE",
                    "runtime_license_state",
                ),
                "src/openinfra/application/container.py": (
                    "PostgreSQLLicenseRepository",
                    "OracleDocumentStore",
                    "JsonLicenseRepository(store)",
                ),
                "installers/migrations/postgresql/0059_runtime_offline_licensing.sql": (
                    "runtime_license_state",
                    "PARTITION BY HASH",
                ),
                "installers/migrations/oracle/0059_runtime_offline_licensing.sql": (
                    "runtime_license_state",
                    "PARTITION BY HASH",
                ),
                "tests/integration/test_runtime_offline_licensing_postgresql_repository.py": (
                    "FOR UPDATE",
                    "fails_closed",
                ),
            },
        )

    def _runtime_control(self, root: Path) -> Gate12Control:
        return self._source_control(
            "runtime-enforcement",
            root,
            {
                "src/openinfra/application/licensing_services.py": (
                    "require_runtime_access",
                    "require_host_capacity_in_current_transaction",
                ),
                "src/openinfra/application/dcim_services.py": (
                    "require_host_capacity_in_current_transaction",
                    "find_equipment",
                ),
                "tests/integration/test_runtime_offline_licensing_interfaces.py": (
                    "assert blocked_code == 402",
                    "allowed_code == 200",
                ),
            },
        )

    def _interface_control(self, root: Path) -> Gate12Control:
        return self._source_control(
            "cli-http-contracts",
            root,
            {
                "src/openinfra/interfaces/cli.py": (
                    "authority-generate",
                    "license",
                    "renew",
                ),
                "src/openinfra/interfaces/http_api.py": (
                    "/api/v1/license/status",
                    "/api/v1/license/activate",
                    "HTTPStatus.PAYMENT_REQUIRED",
                ),
                "docs/api/openapi.yaml": (
                    "/api/v1/license/status:",
                    "Plateforme · Licence runtime",
                ),
                "tests/integration/test_runtime_offline_licensing_interfaces.py": (
                    "test_http_license_enforcement_activation_and_renewal",
                    "test_cli_offline_license_lifecycle_and_business_command_blocking",
                ),
                "pyproject.toml": ("openinfra-gate12",),
                "scripts/smoke_installed_wheel.py": ("openinfra-gate12",),
                ".github/workflows/offline-runtime-licensing.yml": (
                    "openinfra-gate12",
                    "python -m pip_audit --strict",
                    "scripts/smoke_installed_wheel.py",
                ),
                (
                    "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/"
                    "validate_runtime_licensing.py"
                ): (
                    "EXPECTED_REQUIREMENTS",
                    "EXPECTED_TESTS",
                    "EXPECTED_TRACE_ROWS",
                ),
                (
                    "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5/scripts/"
                    "validate_roadmap.py"
                ): (
                    "EXPECTED_COUNTS",
                    "REL-13",
                    "GATE-12",
                ),
            },
        )

    def _installer_control(self, root: Path) -> Gate12Control:
        return self._source_control(
            "installer-offline-bootstrap",
            root,
            {
                "installers/setup/installer_runtime.py": (
                    "configure_runtime_license",
                    "_prepare_runtime_license_material",
                    "OPENINFRA_LICENSE_ENFORCEMENT",
                ),
                "tests/integration/test_autonomous_installers.py": (
                    "test_commercial_server_installer_requires_and_generates_offline_license_material",
                    "0o600",
                ),
                "docs/runbooks/OFFLINE_RUNTIME_LICENSING.md": (
                    "bootstrap",
                    "activation",
                    "/opt/openinfra/config/licensing",
                ),
            },
        )

    def _notification_control(self, root: Path) -> Gate12Control:
        return self._source_control(
            "operator-notifications",
            root,
            {
                "web/src/main.jsx": (
                    "/v1/license/status",
                    "3_600_000",
                    "openinfra-license-banner",
                ),
                "src/openinfra/interfaces/rendering/static/assets/openinfra-web.js": (
                    "/v1/license/status",
                    "3_600_000",
                    'aria-live="assertive"',
                ),
                "web/src/i18n.js": (
                    "Runtime license",
                    "Licence runtime",
                    "licenseStatus_grace",
                ),
                "tests/integration/test_runtime_offline_licensing_frontend.py": (
                    "accessible_hourly_license_notifications",
                    "bilingual",
                ),
                "docs/runbooks/OFFLINE_RUNTIME_LICENSING.md": ("grace", "30"),
            },
        )

    def _security_control(self, root: Path) -> Gate12Control:
        hits: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(
                part in {".git", ".venv", "node_modules", "dist", "build"}
                for part in relative.parts
            ):
                continue
            name = path.name.lower()
            if "authority" in name and path.suffix.lower() in {".pem", ".key"}:
                hits.append(str(relative))
        passed = not hits
        return Gate12Control(
            "private-authority-key-exclusion",
            passed,
            "no private authority key is present"
            if passed
            else "private authority material found: " + ", ".join(hits),
            ("repository-tree-scan",),
        )

    def _source_control(
        self, identifier: str, root: Path, requirements: dict[str, tuple[str, ...]]
    ) -> Gate12Control:
        failures: list[str] = []
        evidence: list[str] = []
        for relative, tokens in requirements.items():
            path = root / relative
            if not path.is_file():
                failures.append(f"{relative} missing")
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                failures.append(f"{relative} unreadable")
                continue
            evidence.append(relative)
            for token in tokens:
                if token not in content:
                    failures.append(f"{relative} missing token {token}")
        return Gate12Control(
            identifier,
            not failures,
            "all required evidence is present" if not failures else "; ".join(failures),
            tuple(evidence),
        )

    def _json(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}


class Gate12QualificationCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-gate12")
        parser.add_argument("--project-root", type=Path, required=True)
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            report = Gate12Qualification().collect(
                project_root=args.project_root,
                candidate_id=args.candidate_id,
                source_commit=args.source_commit,
                enforce=args.enforce,
            )
            Gate12Qualification().write(args.output, report)
            return 0
        except Gate12QualificationError as exc:
            sys.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc


if __name__ == "__main__":
    raise SystemExit(Gate12QualificationCli.main())
