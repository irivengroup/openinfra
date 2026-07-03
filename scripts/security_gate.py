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
            r"\s*[:=]\s*['\"]?([^'\"\s#]{16,})"
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

    def assert_hardened(self) -> None:
        if not self._workflow.is_file():
            raise SecurityGateError("missing CI workflow")
        dependabot = self._workflow.parent.parent / "dependabot.yml"
        if not dependabot.is_file():
            raise SecurityGateError("missing Dependabot vulnerability update policy")
        content = self._workflow.read_text(encoding="utf-8")
        dependabot_content = dependabot.read_text(encoding="utf-8")
        required_fragments = (
            "branches: ['**']",
            "workflow_dispatch:",
            "security-events: write",
            "blocking-security:",
            "pip_audit",
            "bandit -q -r src/openinfra",
            "scripts/security_gate.py --project-root .",
            "github/codeql-action/init",
            "github/codeql-action/analyze",
            "actions/dependency-review-action",
            "'3.13'",
            "'3.14'",
        )
        missing = [fragment for fragment in required_fragments if fragment not in content]
        if missing:
            raise SecurityGateError(
                "CI workflow missing required security controls: " + ", ".join(missing)
            )
        forbidden_fragments = ("pull_request_target:", "branches: ['main']", 'branches: ["main"]')
        forbidden = [fragment for fragment in forbidden_fragments if fragment in content]
        if forbidden:
            raise SecurityGateError(
                "CI workflow contains unsafe trigger configuration: " + ", ".join(forbidden)
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
