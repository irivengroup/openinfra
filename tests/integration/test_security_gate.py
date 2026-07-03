from pathlib import Path

from scripts.security_gate import RepositorySecretScanner, SecurityGate, SecurityGateError


class TestSecurityGate:
    def _write_dependabot_policy(self, root: Path) -> None:
        policy = root / ".github/dependabot.yml"
        policy.write_text(
            "\n".join(
                (
                    "version: 2",
                    "updates:",
                    "  - package-ecosystem: pip",
                    "    directory: /",
                    "    schedule:",
                    "      interval: weekly",
                    "  - package-ecosystem: github-actions",
                    "    directory: /",
                    "    schedule:",
                    "      interval: weekly",
                )
            ),
            encoding="utf-8",
        )

    def test_security_gate_accepts_hardened_workflow(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        requirements = tmp_path / "requirements/security-audit.txt"
        requirements.parent.mkdir(parents=True, exist_ok=True)
        requirements.write_text("pytest>=8.0\n", encoding="utf-8")
        workflow.write_text(
            "\n".join(
                (
                    "on:",
                    "  push:",
                    "    branches: ['**']",
                    "  workflow_dispatch:",
                    "permissions:",
                    "  security-events: write",
                    "jobs:",
                    "  blocking-security:",
                    "    steps:",
                    "      - run: python -m pip_audit --strict --requirement requirements/security-audit.txt",
                    "      - run: bandit -q -r src/openinfra",
                    "      - run: python scripts/security_gate.py --project-root .",
                    "      - uses: github/codeql-action/init@v4",
                    "      - uses: github/codeql-action/analyze@v4",
                    "      - uses: actions/dependency-review-action@v5",
                    "matrix:",
                    "  python-version: ['3.13', '3.14']",
                )
            ),
            encoding="utf-8",
        )
        SecurityGate(tmp_path).run()

    def test_security_gate_rejects_known_token_pattern(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        requirements = tmp_path / "requirements/security-audit.txt"
        requirements.parent.mkdir(parents=True, exist_ok=True)
        requirements.write_text("pytest>=8.0\n", encoding="utf-8")
        workflow.write_text(
            "\n".join(
                (
                    "branches: ['**']",
                    "workflow_dispatch:",
                    "security-events: write",
                    "blocking-security:",
                    "pip_audit",
                    "--requirement requirements/security-audit.txt",
                    "bandit -q -r src/openinfra",
                    "scripts/security_gate.py --project-root .",
                    "github/codeql-action/init",
                    "github/codeql-action/analyze",
                    "actions/dependency-review-action",
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        token_value = "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL"
        (tmp_path / "config.py").write_text(
            f"TOKEN = '{token_value}'\n",
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "potential committed credentials" in str(exc)
        else:
            raise AssertionError("security gate accepted a committed credential")

    def test_security_gate_rejects_environment_pip_audit_on_editable_install(
        self, tmp_path: Path
    ) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        requirements = tmp_path / "requirements/security-audit.txt"
        requirements.parent.mkdir(parents=True, exist_ok=True)
        requirements.write_text("pytest>=8.0\n", encoding="utf-8")
        workflow.write_text(
            "\n".join(
                (
                    "branches: ['**']",
                    "workflow_dispatch:",
                    "security-events: write",
                    "blocking-security:",
                    "pip_audit",
                    "--requirement requirements/security-audit.txt",
                    "python -m pip_audit --strict --skip-editable --progress-spinner off",
                    "bandit -q -r src/openinfra",
                    "scripts/security_gate.py --project-root .",
                    "github/codeql-action/init",
                    "github/codeql-action/analyze",
                    "actions/dependency-review-action",
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "unsafe trigger configuration" in str(exc)
        else:
            raise AssertionError("security gate accepted an environment pip-audit command")

    def test_security_gate_rejects_local_package_in_audit_requirements(
        self, tmp_path: Path
    ) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        requirements = tmp_path / "requirements/security-audit.txt"
        requirements.parent.mkdir(parents=True, exist_ok=True)
        requirements.write_text("openinfra==0.17.4\n", encoding="utf-8")
        workflow.write_text(
            "\n".join(
                (
                    "branches: ['**']",
                    "workflow_dispatch:",
                    "security-events: write",
                    "blocking-security:",
                    "pip_audit",
                    "--requirement requirements/security-audit.txt",
                    "bandit -q -r src/openinfra",
                    "scripts/security_gate.py --project-root .",
                    "github/codeql-action/init",
                    "github/codeql-action/analyze",
                    "actions/dependency-review-action",
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "must not reference local package openinfra" in str(exc)
        else:
            raise AssertionError("security gate accepted local package audit input")

    def test_secret_scanner_accepts_runtime_generated_shell_tokens(self, tmp_path: Path) -> None:
        script = tmp_path / "ci.yml"
        script.write_text(
            "operator_token=\"$(python -c 'import secrets; print(secrets.token_urlsafe(48))')\"\n",
            encoding="utf-8",
        )
        assert RepositorySecretScanner(tmp_path).scan() == []
