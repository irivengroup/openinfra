from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


class SecurityGateError(Exception):
    """Raised when repository security checks fail."""


@dataclass(frozen=True, slots=True)
class SecretPattern:
    name: str
    expression: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class SecretFinding:
    path: Path
    line_number: int
    pattern_name: str

    def as_text(self) -> str:
        return f"{self.path}:{self.line_number}:{self.pattern_name}"


class RepositorySecretScanner:
    _SCANNED_SUFFIXES = frozenset(
        (
            ".cfg",
            ".env",
            ".ini",
            ".json",
            ".md",
            ".py",
            ".service",
            ".sh",
            ".sql",
            ".toml",
            ".txt",
            ".yaml",
            ".yml",
        )
    )
    _SKIPPED_PARTS = frozenset(
        (
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "__pycache__",
            "build",
            "dist",
        )
    )
    _SAFE_VALUE_PREFIXES = (
        "$",
        "${",
        "$('",
        '$("',
        "<",
        "example",
        "changeme",
        "change-me",
        "replace-me",
        "redacted",
        "masked",
        "secrets.",
        "os.environ",
        "env:",
        "vault://",
        "sops://",
        "file://",
        "kms://",
        "none",
        "null",
        "true",
        "false",
    )

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()
        self._patterns = (
            SecretPattern(
                "private-key",
                re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
            ),
            SecretPattern("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
            SecretPattern(
                "github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b")
            ),
            SecretPattern(
                "github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")
            ),
            SecretPattern("openai-token", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b")),
            SecretPattern("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
            SecretPattern(
                "jwt-token",
                re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
            ),
        )
        self._assignment_pattern = re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b"
            r"\s*[:=]\s*(?!//)['\"]?([^'\"\s#]{16,})"
        )

    def scan(self) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        for path in self._iter_files():
            findings.extend(self._scan_file(path))
        return findings

    def assert_clean(self) -> None:
        findings = self.scan()
        if findings:
            rendered = ", ".join(finding.as_text() for finding in findings)
            raise SecurityGateError("potential committed credentials detected: " + rendered)

    def _iter_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self._project_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self._SKIPPED_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in self._SCANNED_SUFFIXES:
                continue
            files.append(path)
        return sorted(files)

    def _scan_file(self, path: Path) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        relative = path.relative_to(self._project_root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            return findings
        for line_number, line in enumerate(lines, start=1):
            if self._is_comment_only(line):
                continue
            for pattern in self._patterns:
                if pattern.expression.search(line):
                    findings.append(SecretFinding(relative, line_number, pattern.name))
            assignment_match = self._assignment_pattern.search(line)
            if assignment_match and not self._is_safe_assignment_value(assignment_match.group(1)):
                findings.append(SecretFinding(relative, line_number, "credential-assignment"))
        return findings

    def _is_comment_only(self, line: str) -> bool:
        stripped = line.strip()
        return not stripped or stripped.startswith(("#", "//", "<!--"))

    def _is_safe_assignment_value(self, value: str) -> bool:
        normalized = value.strip().strip("'\"").lower()
        return normalized.startswith(self._SAFE_VALUE_PREFIXES)


class GitHubWorkflowSecurityGuard:
    def __init__(self, project_root: Path) -> None:
        self._workflow = project_root / ".github/workflows/ci.yml"
        self._dependency_review_workflow = project_root / ".github/workflows/dependency-review.yml"

    @staticmethod
    def _requirement_payload_lines(path: Path) -> tuple[str, ...]:
        return tuple(
            line.strip().lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    @staticmethod
    def _requirement_package_name(line: str) -> str:
        if line.startswith("-r ") or line.startswith("--requirement "):
            return line
        normalized = line.split(";", 1)[0].split("[", 1)[0]
        for separator in ("==", ">=", "<=", "~=", "!=", ">", "<"):
            if separator in normalized:
                normalized = normalized.split(separator, 1)[0]
                break
        return normalized.strip().replace("_", "-")

    def assert_hardened(self) -> None:
        if not self._workflow.is_file():
            raise SecurityGateError("missing CI workflow")
        dependabot = self._workflow.parent.parent / "dependabot.yml"
        if not dependabot.is_file():
            raise SecurityGateError("missing Dependabot vulnerability update policy")
        content = self._workflow.read_text(encoding="utf-8")
        dependabot_content = dependabot.read_text(encoding="utf-8")
        if not self._dependency_review_workflow.is_file():
            raise SecurityGateError("missing pull request dependency review workflow")
        dependency_review_content = self._dependency_review_workflow.read_text(encoding="utf-8")
        deprecated_node_action_fragments = (
            "actions/checkout@v4",
            "actions/setup-node@v4",
            "actions/setup-python@v5",
        )
        deprecated_node_actions = [
            fragment for fragment in deprecated_node_action_fragments if fragment in content
        ]
        if deprecated_node_actions:
            raise SecurityGateError(
                "CI workflow contains actions using deprecated Node.js 20 runtimes: "
                + ", ".join(deprecated_node_actions)
            )
        deprecated_dependency_review_actions = [
            fragment
            for fragment in deprecated_node_action_fragments
            if fragment in dependency_review_content
        ]
        if deprecated_dependency_review_actions:
            raise SecurityGateError(
                "dependency review workflow contains actions using deprecated Node.js 20 runtimes: "
                + ", ".join(deprecated_dependency_review_actions)
            )
        unsafe_token_generators = ("print(secrets.token_urlsafe(48))",)
        unsafe_token_generator_matches = [
            fragment for fragment in unsafe_token_generators if fragment in content
        ]
        if unsafe_token_generator_matches:
            raise SecurityGateError(
                "CI workflow contains unsafe token generation: "
                + ", ".join(unsafe_token_generator_matches)
            )
        required_fragments = (
            "branches: ['**']",
            "workflow_dispatch:",
            "security-events: write",
            "blocking-security:",
            "Blocking push vulnerability gate",
            "actions/checkout@v6",
            "actions/setup-node@v6",
            "actions/setup-python@v6",
            "pip_audit",
            "--requirement requirements/security-audit.txt",
            "--requirement requirements/dev.txt",
            "bandit -q -r src/openinfra",
            "scripts/security_gate.py --project-root .",
            "github/codeql-action/init",
            "github/codeql-action/analyze",
            "'3.13'",
            "'3.14'",
            'print("ci_" + secrets.token_urlsafe(48))',
        )
        missing = [fragment for fragment in required_fragments if fragment not in content]
        if missing:
            raise SecurityGateError(
                "CI workflow missing required security controls: " + ", ".join(missing)
            )
        dependency_review_required = (
            "pull_request:",
            "branches: ['**']",
            "actions/checkout@v6",
            "actions/dependency-review-action@v5",
            "fail-on-severity: moderate",
        )
        missing_dependency_review = [
            fragment
            for fragment in dependency_review_required
            if fragment not in dependency_review_content
        ]
        if missing_dependency_review:
            raise SecurityGateError(
                "dependency review workflow missing required controls: "
                + ", ".join(missing_dependency_review)
            )
        forbidden_fragments = (
            "pull_request_target:",
            "branches: ['main']",
            'branches: ["main"]',
            "python -m pip_audit --strict --skip-editable --progress-spinner off",
        )
        forbidden = [fragment for fragment in forbidden_fragments if fragment in content]
        if forbidden:
            raise SecurityGateError(
                "CI workflow contains unsafe trigger configuration: " + ", ".join(forbidden)
            )
        ci_forbidden_fragments = (
            "actions/dependency-review-action",
            "if: github.event_name == 'pull_request'",
            'if: github.event_name == "pull_request"',
        )
        ci_forbidden = [fragment for fragment in ci_forbidden_fragments if fragment in content]
        if ci_forbidden:
            raise SecurityGateError(
                "CI push workflow contains PR-only dependency review controls: "
                + ", ".join(ci_forbidden)
            )
        dependency_review_forbidden = ("push:", "workflow_dispatch:")
        dependency_review_forbidden_found = [
            fragment
            for fragment in dependency_review_forbidden
            if fragment in dependency_review_content
        ]
        if dependency_review_forbidden_found:
            raise SecurityGateError(
                "dependency review workflow must remain pull-request only: "
                + ", ".join(dependency_review_forbidden_found)
            )
        requirements_root = self._workflow.parent.parent.parent / "requirements"
        audit_requirements = requirements_root / "security-audit.txt"
        runtime_requirements = requirements_root / "runtime.txt"
        postgresql_requirements = requirements_root / "postgresql.txt"
        dev_requirements = requirements_root / "dev.txt"
        required_requirement_files = (
            audit_requirements,
            runtime_requirements,
            postgresql_requirements,
            dev_requirements,
        )
        missing_requirement_files = [
            str(item.relative_to(requirements_root.parent))
            for item in required_requirement_files
            if not item.is_file()
        ]
        if missing_requirement_files:
            raise SecurityGateError(
                "missing pip-audit requirement input: " + ", ".join(missing_requirement_files)
            )
        audit_lines = self._requirement_payload_lines(audit_requirements)
        if any(line.startswith("openinfra") for line in audit_lines):
            raise SecurityGateError(
                "pip-audit requirement input must not reference local package openinfra"
            )
        required_audit_includes = ("-r runtime.txt", "-r postgresql.txt", "-r dev.txt")
        missing_audit_includes = [
            item for item in required_audit_includes if item not in audit_lines
        ]
        if missing_audit_includes:
            raise SecurityGateError(
                "pip-audit requirement input must preserve runtime/dev separation: "
                + ", ".join(missing_audit_includes)
            )
        runtime_lines = self._requirement_payload_lines(runtime_requirements)
        postgresql_lines = self._requirement_payload_lines(postgresql_requirements)
        dev_lines = self._requirement_payload_lines(dev_requirements)
        dev_only_packages = (
            "bandit",
            "build",
            "hatchling",
            "mypy",
            "pip-audit",
            "pytest",
            "pytest-cov",
            "ruff",
        )
        forbidden_runtime = [
            line
            for line in (*runtime_lines, *postgresql_lines)
            if self._requirement_package_name(line) in dev_only_packages
        ]
        if forbidden_runtime:
            raise SecurityGateError(
                "production requirements contain dev-only packages: " + ", ".join(forbidden_runtime)
            )
        missing_dev_tools = [
            package
            for package in dev_only_packages
            if package not in {self._requirement_package_name(line) for line in dev_lines}
        ]
        if missing_dev_tools:
            raise SecurityGateError(
                "development requirements missing mandatory CI tools: "
                + ", ".join(missing_dev_tools)
            )
        dependabot_required = ("package-ecosystem: pip", "package-ecosystem: github-actions")
        missing_dependabot = [
            fragment for fragment in dependabot_required if fragment not in dependabot_content
        ]
        if missing_dependabot:
            raise SecurityGateError(
                "Dependabot policy missing required ecosystems: " + ", ".join(missing_dependabot)
            )


class SecurityGate:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()

    def run(self) -> None:
        GitHubWorkflowSecurityGuard(self._project_root).assert_hardened()
        RepositorySecretScanner(self._project_root).assert_clean()


class SecurityGateCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Run OpenInfra blocking security checks")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        args = parser.parse_args()
        try:
            SecurityGate(args.project_root).run()
        except SecurityGateError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(SecurityGateCli.main())
