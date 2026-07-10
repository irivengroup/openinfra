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

    def _write_dependency_review_workflow(self, root: Path) -> None:
        workflow = root / ".github/workflows/dependency-review.yml"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(
            "\n".join(
                (
                    "on:",
                    "  pull_request:",
                    "    branches: ['**']",
                    "jobs:",
                    "  dependency-review:",
                    "    steps:",
                    "      - uses: actions/checkout@v6",
                    "      - uses: actions/dependency-review-action@v5",
                    "        with:",
                    "          fail-on-severity: moderate",
                )
            ),
            encoding="utf-8",
        )

    def _write_audit_requirements(self, root: Path) -> None:
        requirements = root / "requirements"
        requirements.mkdir(parents=True, exist_ok=True)
        (requirements / "runtime.txt").write_text("defusedxml>=0.7.1\n", encoding="utf-8")
        (requirements / "postgresql.txt").write_text("psycopg[binary]>=3.2\n", encoding="utf-8")
        (requirements / "dev.txt").write_text(
            "\n".join(
                (
                    "hatchling>=1.25",
                    "pytest>=8.0",
                    "pytest-cov>=5.0",
                    "ruff>=0.5",
                    "mypy>=1.10",
                    "bandit>=1.7",
                    "pip-audit>=2.7",
                    "build>=1.2",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        (requirements / "security-audit.txt").write_text(
            "-r runtime.txt\n-r postgresql.txt\n-r dev.txt\n",
            encoding="utf-8",
        )

    def test_security_gate_accepts_hardened_workflow(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
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
                    "      - uses: actions/checkout@v6",
                    "      - uses: actions/setup-node@v6",
                    "      - uses: actions/setup-python@v6",
                    "      - run: python -m pip_audit --strict --requirement requirements/security-audit.txt",
                    "      - run: python -m pip install --requirement requirements/dev.txt",
                    "      - run: bandit -q -r src/openinfra",
                    "      - run: python scripts/security_gate.py --project-root .",
                    "      - uses: github/codeql-action/init@v4",
                    "      - uses: github/codeql-action/analyze@v4",
                    'print("ci_" + secrets.token_urlsafe(48))',
                    "  name: Blocking push vulnerability gate",
                    "matrix:",
                    "  python-version: ['3.13', '3.14']",
                )
            ),
            encoding="utf-8",
        )
        SecurityGate(tmp_path).run()

    def test_security_gate_accepts_referenced_installer_secret(self, tmp_path: Path) -> None:
        config = tmp_path / "install.ini"
        config.write_text(
            "[auth]\nbind_password_ref = env:OPENINFRA_LDAP_BIND_PASSWORD\n",
            encoding="utf-8",
        )

        findings = RepositorySecretScanner(tmp_path).scan()

        assert findings == []

    def test_security_gate_rejects_known_token_pattern(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        workflow.write_text(
            "\n".join(
                (
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
                    'print("ci_" + secrets.token_urlsafe(48))',
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
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        workflow.write_text(
            "\n".join(
                (
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
                    "python -m pip_audit --strict --skip-editable --progress-spinner off",
                    "bandit -q -r src/openinfra",
                    "scripts/security_gate.py --project-root .",
                    "github/codeql-action/init",
                    "github/codeql-action/analyze",
                    'print("ci_" + secrets.token_urlsafe(48))',
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
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        requirements = tmp_path / "requirements/security-audit.txt"
        requirements.write_text("openinfra==0.17.6\n", encoding="utf-8")
        workflow.write_text(
            "\n".join(
                (
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
                    'print("ci_" + secrets.token_urlsafe(48))',
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

    def test_security_gate_rejects_dev_tool_in_runtime_requirements(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        (tmp_path / "requirements/runtime.txt").write_text(
            "defusedxml>=0.7.1\npytest>=8.0\n",
            encoding="utf-8",
        )
        workflow.write_text(
            "\n".join(
                (
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
                    'print("ci_" + secrets.token_urlsafe(48))',
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "production requirements contain dev-only packages" in str(exc)
        else:
            raise AssertionError("security gate accepted dev-only tools in runtime requirements")

    def test_security_gate_rejects_unseparated_audit_requirements(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        (tmp_path / "requirements/security-audit.txt").write_text(
            "defusedxml>=0.7.1\npytest>=8.0\n",
            encoding="utf-8",
        )
        workflow.write_text(
            "\n".join(
                (
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
                    'print("ci_" + secrets.token_urlsafe(48))',
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "must preserve runtime/dev separation" in str(exc)
        else:
            raise AssertionError("security gate accepted an unseparated audit requirements file")

    def test_security_gate_rejects_dependency_review_in_push_workflow(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        workflow.write_text(
            "\n".join(
                (
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
                    'print("ci_" + secrets.token_urlsafe(48))',
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
            assert "PR-only dependency review controls" in str(exc)
        else:
            raise AssertionError("security gate accepted dependency review in push workflow")

    def test_security_gate_rejects_push_trigger_on_dependency_review_workflow(
        self, tmp_path: Path
    ) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        dependency_review = tmp_path / ".github/workflows/dependency-review.yml"
        dependency_review.write_text(
            dependency_review.read_text(encoding="utf-8") + "\npush:\n",
            encoding="utf-8",
        )
        self._write_audit_requirements(tmp_path)
        workflow.write_text(
            "\n".join(
                (
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
                    'print("ci_" + secrets.token_urlsafe(48))',
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "must remain pull-request only" in str(exc)
        else:
            raise AssertionError("security gate accepted push trigger in dependency review")

    def test_security_gate_rejects_unprefixed_ci_token_generation(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        workflow.write_text(
            "\n".join(
                (
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
                    "print(secrets.token_urlsafe(48))",
                    "'3.13'",
                    "'3.14'",
                )
            ),
            encoding="utf-8",
        )
        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "unsafe token generation" in str(exc)
        else:
            raise AssertionError("security gate accepted unprefixed CI token generation")

    def test_secret_scanner_accepts_runtime_generated_shell_tokens(self, tmp_path: Path) -> None:
        script = tmp_path / "ci.yml"
        script.write_text(
            'operator_token="$(python -c \'import secrets; print("ci_" + secrets.token_urlsafe(48))\')"\n',
            encoding="utf-8",
        )
        assert RepositorySecretScanner(tmp_path).scan() == []

    def test_security_gate_rejects_deprecated_node20_action_runtimes(self, tmp_path: Path) -> None:
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.parent.mkdir(parents=True)
        self._write_dependabot_policy(tmp_path)
        self._write_dependency_review_workflow(tmp_path)
        self._write_audit_requirements(tmp_path)
        workflow.write_text(
            "\n".join(
                (
                    "branches: ['**']",
                    "workflow_dispatch:",
                    "security-events: write",
                    "blocking-security:",
                    "Blocking push vulnerability gate",
                    "actions/checkout@v4",
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
            ),
            encoding="utf-8",
        )

        try:
            SecurityGate(tmp_path).run()
        except SecurityGateError as exc:
            assert "actions/checkout@v4" in str(exc)
        else:
            raise AssertionError("security gate accepted a deprecated Node.js 20 action")
