from __future__ import annotations

import hashlib
import json
import os
import re

# Controlled argv execution is the release audit boundary.
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from openinfra import __version__

_REQUIRED_CONTROL_IDS: Final[frozenset[str]] = frozenset(
    {
        "repository-secrets-and-workflows",
        "sast-bandit",
        "rbac-authentication-regression",
        "python-dependency-audit",
        "frontend-dependency-audit",
        "container-filesystem-scan",
        "container-image-scan",
        "dynamic-http-security-probe",
    }
)


class ReleaseSecurityAuditError(Exception):
    """Raised when the release security audit cannot be executed safely."""


@dataclass(frozen=True, slots=True)
class SecurityControlSpec:
    identifier: str
    category: str
    command: tuple[str, ...]
    network_required: bool = False

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ReleaseSecurityAuditError("security control identifier cannot be empty")
        if not self.command:
            raise ReleaseSecurityAuditError(f"security control {self.identifier} has no command")


@dataclass(frozen=True, slots=True)
class SecurityControlResult:
    identifier: str
    category: str
    status: str
    return_code: int | None
    duration_ms: float
    command: tuple[str, ...]
    stdout_path: str
    stderr_path: str
    stdout_sha256: str
    stderr_sha256: str
    network_required: bool
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "category": self.category,
            "status": self.status,
            "return_code": self.return_code,
            "duration_ms": round(self.duration_ms, 3),
            "command": list(self.command),
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "network_required": self.network_required,
            "detail": self.detail,
        }


class SecurityEvidenceSanitizer:
    _PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
        (
            re.compile(
                r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----.*?"
                r"-----END (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
                re.DOTALL,
            ),
            "<redacted-private-key>",
        ),
        (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted-aws-access-key>"),
        (
            re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
            "<redacted-github-token>",
        ),
        (
            re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
            "<redacted-github-token>",
        ),
        (re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"), "<redacted-api-token>"),
        (
            re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
            "<redacted-jwt>",
        ),
        (
            re.compile(r'(?i)("(?:match|secret|password|token)"\s*:\s*")[^"]+("\s*[,}])'),
            r"\1<redacted>\2",
        ),
        (
            re.compile(
                r"(?i)(\b(?:password|passwd|secret|token|api[_-]?key|access[_-]?token|auth[_-]?token)"
                r"\b\s*[:=]\s*)[^\s,;]+"
            ),
            r"\1<redacted>",
        ),
        (
            re.compile(r"(?i)(https?://[^:/@\s]+:)[^@/\s]+(@)"),
            r"\1<redacted>\2",
        ),
    )

    @classmethod
    def sanitize(cls, payload: bytes) -> bytes:
        text = payload.decode("utf-8", errors="replace")
        for pattern, replacement in cls._PATTERNS:
            text = pattern.sub(replacement, text)
        return text.encode("utf-8")


class SecurityCommandExecutor:
    def __init__(self, timeout_seconds: float = 900.0) -> None:
        if timeout_seconds <= 0:
            raise ReleaseSecurityAuditError("security command timeout must be positive")
        self._timeout_seconds = timeout_seconds

    def execute(
        self,
        control: SecurityControlSpec,
        project_root: Path,
        evidence_dir: Path,
        *,
        offline: bool,
    ) -> SecurityControlResult:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = evidence_dir / f"{control.identifier}.stdout.log"
        stderr_path = evidence_dir / f"{control.identifier}.stderr.log"
        if offline and control.network_required:
            stdout = b""
            stderr = b"control skipped because offline mode disables network-dependent checks\n"
            self._write_atomic(stdout_path, stdout)
            self._write_atomic(stderr_path, stderr)
            return self._result(
                control,
                status="not-run",
                return_code=None,
                duration_ms=0.0,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                stdout=stdout,
                stderr=stderr,
                detail="network-dependent control not executed in offline mode",
                project_root=project_root,
            )
        started = time.perf_counter()
        try:
            # No shell is used; argv comes from the closed release control catalog.
            completed = subprocess.run(  # noqa: S603  # nosec B603
                control.command,
                cwd=project_root,
                check=False,
                capture_output=True,
                env=self._sanitized_environment(),
                timeout=self._timeout_seconds,
            )
            duration_ms = (time.perf_counter() - started) * 1000
            stdout = SecurityEvidenceSanitizer.sanitize(completed.stdout)
            stderr = SecurityEvidenceSanitizer.sanitize(completed.stderr)
            self._write_atomic(stdout_path, stdout)
            self._write_atomic(stderr_path, stderr)
            return self._result(
                control,
                status="passed" if completed.returncode == 0 else "failed",
                return_code=completed.returncode,
                duration_ms=duration_ms,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                stdout=stdout,
                stderr=stderr,
                detail=(
                    "control completed successfully"
                    if completed.returncode == 0
                    else f"control exited with status {completed.returncode}"
                ),
                project_root=project_root,
            )
        except FileNotFoundError as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            stdout = b""
            stderr = str(exc).encode("utf-8", errors="replace")
            self._write_atomic(stdout_path, stdout)
            self._write_atomic(stderr_path, stderr)
            return self._result(
                control,
                status="unavailable",
                return_code=None,
                duration_ms=duration_ms,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                stdout=stdout,
                stderr=stderr,
                detail="required security tool is unavailable",
                project_root=project_root,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            if isinstance(stdout, str):
                stdout = stdout.encode("utf-8", errors="replace")
            if isinstance(stderr, str):
                stderr = stderr.encode("utf-8", errors="replace")
            stdout = SecurityEvidenceSanitizer.sanitize(stdout)
            stderr = SecurityEvidenceSanitizer.sanitize(stderr)
            self._write_atomic(stdout_path, stdout)
            self._write_atomic(stderr_path, stderr)
            return self._result(
                control,
                status="timeout",
                return_code=None,
                duration_ms=duration_ms,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                stdout=stdout,
                stderr=stderr,
                detail=f"control exceeded timeout of {self._timeout_seconds:g} seconds",
                project_root=project_root,
            )

    @staticmethod
    def _sanitized_environment() -> dict[str, str]:
        allowed_prefixes = (
            "CI",
            "GITHUB_",
            "HOME",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "LANG",
            "LC_",
            "NO_PROXY",
            "NPM_CONFIG_",
            "PATH",
            "PIP_",
            "PYTHON",
            "REQUESTS_CA_BUNDLE",
            "SSL_CERT_",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "VIRTUAL_ENV",
        )
        return {
            key: value
            for key, value in os.environ.items()
            if key == "PATH" or any(key.startswith(prefix) for prefix in allowed_prefixes)
        }

    @classmethod
    def _result(
        cls,
        control: SecurityControlSpec,
        *,
        status: str,
        return_code: int | None,
        duration_ms: float,
        stdout_path: Path,
        stderr_path: Path,
        stdout: bytes,
        stderr: bytes,
        detail: str,
        project_root: Path,
    ) -> SecurityControlResult:
        return SecurityControlResult(
            identifier=control.identifier,
            category=control.category,
            status=status,
            return_code=return_code,
            duration_ms=duration_ms,
            command=control.command,
            stdout_path=cls._relative_path(stdout_path, project_root),
            stderr_path=cls._relative_path(stderr_path, project_root),
            stdout_sha256=hashlib.sha256(stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr).hexdigest(),
            network_required=control.network_required,
            detail=detail,
        )

    @staticmethod
    def _relative_path(path: Path, project_root: Path) -> str:
        try:
            return path.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            return str(path.resolve())

    @staticmethod
    def _write_atomic(path: Path, payload: bytes) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)


class ReleaseSecurityControlCatalog:
    _TRIVY_IMAGE: Final[str] = (
        "aquasec/trivy:0.72.0@sha256:"
        "cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f"
    )

    @classmethod
    def build(
        cls,
        project_root: Path,
        *,
        image_ref: str,
        api_base_url: str,
        web_base_url: str,
    ) -> tuple[SecurityControlSpec, ...]:
        python = sys.executable
        root_mount = f"{project_root.resolve()}:/workspace:ro"
        controls = (
            SecurityControlSpec(
                "repository-secrets-and-workflows",
                "secrets",
                (python, "scripts/security_gate.py", "--project-root", "."),
            ),
            SecurityControlSpec(
                "sast-bandit",
                "sast",
                ("bandit", "-q", "-r", "src/openinfra", "-f", "json"),
            ),
            SecurityControlSpec(
                "rbac-authentication-regression",
                "rbac",
                (
                    python,
                    "-m",
                    "pytest",
                    "-q",
                    "--no-cov",
                    "tests/unit/test_security_domain.py",
                    "tests/unit/test_authentication_domain.py",
                    "tests/integration/test_external_authentication_services.py",
                    "tests/integration/test_security_gate.py",
                ),
            ),
            SecurityControlSpec(
                "python-dependency-audit",
                "dependencies",
                (
                    python,
                    "-m",
                    "pip_audit",
                    "--strict",
                    "--requirement",
                    "requirements/security-audit.txt",
                    "--format",
                    "json",
                    "--progress-spinner",
                    "off",
                ),
                network_required=True,
            ),
            SecurityControlSpec(
                "frontend-dependency-audit",
                "dependencies",
                (
                    "npm",
                    "--prefix",
                    "web",
                    "audit",
                    "--audit-level=moderate",
                    "--json",
                ),
                network_required=True,
            ),
            SecurityControlSpec(
                "container-filesystem-scan",
                "container",
                (
                    "docker",
                    "run",
                    "--rm",
                    "--volume",
                    root_mount,
                    "--workdir",
                    "/workspace",
                    cls._TRIVY_IMAGE,
                    "fs",
                    "--scanners",
                    "vuln,secret,misconfig",
                    "--severity",
                    "HIGH,CRITICAL",
                    "--exit-code",
                    "1",
                    "--format",
                    "json",
                    ".",
                ),
                network_required=True,
            ),
            SecurityControlSpec(
                "container-image-scan",
                "container",
                (
                    "docker",
                    "run",
                    "--rm",
                    "--volume",
                    "/var/run/docker.sock:/var/run/docker.sock",
                    cls._TRIVY_IMAGE,
                    "image",
                    "--scanners",
                    "vuln,secret,misconfig",
                    "--severity",
                    "HIGH,CRITICAL",
                    "--exit-code",
                    "1",
                    "--format",
                    "json",
                    image_ref,
                ),
                network_required=True,
            ),
            SecurityControlSpec(
                "dynamic-http-security-probe",
                "dast",
                (
                    python,
                    "scripts/security_http_probe.py",
                    "--api-base-url",
                    api_base_url,
                    "--web-base-url",
                    web_base_url,
                ),
            ),
        )
        identifiers = {control.identifier for control in controls}
        if identifiers != _REQUIRED_CONTROL_IDS:
            raise ReleaseSecurityAuditError("release security control catalog is incomplete")
        return controls


class ReleaseSecurityAuditService:
    def __init__(self, executor: SecurityCommandExecutor | None = None) -> None:
        self._executor = executor or SecurityCommandExecutor()

    def run(
        self,
        project_root: Path,
        output_path: Path,
        evidence_dir: Path,
        *,
        image_ref: str,
        api_base_url: str,
        web_base_url: str,
        offline: bool,
    ) -> dict[str, object]:
        project_root = project_root.resolve()
        controls = ReleaseSecurityControlCatalog.build(
            project_root,
            image_ref=image_ref,
            api_base_url=api_base_url,
            web_base_url=web_base_url,
        )
        results = tuple(
            self._executor.execute(
                control,
                project_root,
                evidence_dir.resolve(),
                offline=offline,
            )
            for control in controls
        )
        missing = sorted(_REQUIRED_CONTROL_IDS.difference(result.identifier for result in results))
        failures = [
            f"{result.identifier}: {result.status} ({result.detail})"
            for result in results
            if not result.passed
        ]
        if missing:
            failures.extend(f"missing required control: {identifier}" for identifier in missing)
        complete = not missing and all(result.status != "not-run" for result in results)
        certified = complete and not failures
        serialized_results = json.dumps(
            [result.as_dict() for result in results], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        report: dict[str, object] = {
            "schema_version": 1,
            "openinfra_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "release_security_certification": certified,
            "complete": complete,
            "offline_mode": offline,
            "required_controls": sorted(_REQUIRED_CONTROL_IDS),
            "controls": [result.as_dict() for result in results],
            "evidence_digest_sha256": hashlib.sha256(serialized_results).hexdigest(),
            "failures": failures,
        }
        self._write_report(output_path, report)
        return report

    @staticmethod
    def _write_report(output_path: Path, report: dict[str, object]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(output_path)
