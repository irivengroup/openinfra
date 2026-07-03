from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


class QualityGateError(Exception):
    """Raised when the local quality gate fails."""


class ModuleFunctionGuard:
    def __init__(self, root: Path) -> None:
        self._root = root

    def assert_no_module_level_functions(self) -> None:
        violations: list[str] = []
        for path in sorted(self._root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    violations.append(f"{path}:{node.lineno}:{node.name}")
        if violations:
            raise QualityGateError("module-level functions are forbidden: " + ", ".join(violations))


class ContractFileGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_sources_present(self) -> None:
        required = (
            self._project_root / "docs/specifications/OpenInfra-CDC-SFG-STG-v4/VERSION",
            self._project_root / "docs/specifications/OpenInfra-Roadmap-Developpement-v1/VERSION",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise QualityGateError("missing contractual source files: " + ", ".join(missing))


class NativeRuntimeGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_runtime_environment_present(self) -> None:
        required = (
            "deploy/systemd/openinfra-api.service",
            "docs/runbooks/RUNTIME_NATIVE.md",
            "scripts/native_runtime_smoke.py",
        )
        missing = [name for name in required if not (self._project_root / name).is_file()]
        if missing:
            raise QualityGateError("missing native runtime assets: " + ", ".join(missing))
        unit = (self._project_root / "deploy/systemd/openinfra-api.service").read_text(
            encoding="utf-8"
        )
        runbook = (self._project_root / "docs/runbooks/RUNTIME_NATIVE.md").read_text(
            encoding="utf-8"
        )
        if "ExecStart=/opt/openinfra/venv/bin/openinfra-api" not in unit:
            raise QualityGateError(
                "native systemd service must start openinfra-api from virtualenv"
            )
        if "User=openinfra" not in unit or "NoNewPrivileges=true" not in unit:
            raise QualityGateError("native systemd service must run with a hardened openinfra user")
        if "OPENINFRA_DATABASE_DSN" not in runbook:
            raise QualityGateError("native runbook must document the PostgreSQL DSN")
        if "Docker ne fait pas partie de la chaine d'execution production" not in runbook:
            raise QualityGateError(
                "native runbook must state that Docker is not part of production runtime"
            )
        if (self._project_root / ".env").exists():
            raise QualityGateError("local .env must not be packaged or committed")


class CiWorkflowTriggerGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_push_triggers_are_not_branch_locked(self) -> None:
        workflow = self._project_root / ".github/workflows/ci.yml"
        if not workflow.is_file():
            raise QualityGateError("missing GitHub Actions workflow: .github/workflows/ci.yml")
        content = workflow.read_text(encoding="utf-8")
        if "workflow_dispatch:" not in content:
            raise QualityGateError("CI workflow must expose a manual workflow_dispatch trigger")
        forbidden = ("branches: [main]", "branches: ['main']", 'branches: ["main"]')
        if any(pattern in content for pattern in forbidden):
            raise QualityGateError(
                "CI workflow push/pull_request triggers must not be locked to main only"
            )
        if "branches: ['**']" not in content:
            raise QualityGateError("CI workflow must run on every branch push and pull request")


class CompletionMarkerGuard:
    _encoded_markers = (
        ("T", "O", "D", "O"),
        ("F", "I", "X", "M", "E"),
        ("s", "t", "u", "b"),
        ("p", "l", "a", "c", "e", "h", "o", "l", "d", "e", "r"),
        ("d", "u", "m", "m", "y"),
        ("N", "o", "t", "I", "m", "p", "l", "e", "m", "e", "n", "t", "e", "d"),
    )
    _roots = ("src", "tests", "scripts", "docker", "deploy", ".github", "migrations")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def _markers(self) -> tuple[str, ...]:
        return tuple("".join(parts) for parts in self._encoded_markers)

    def assert_clean_sources(self) -> None:
        violations: list[str] = []
        for root_name in self._roots:
            root = self._project_root / root_name
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
                    continue
                if path.suffix not in (".py", ".yml", ".yaml", ".sql", ".md", ".service"):
                    continue
                content = path.read_text(encoding="utf-8")
                for marker in self._markers():
                    if marker in content:
                        violations.append(f"{path}:{marker}")
        if violations:
            raise QualityGateError(
                "disallowed completion markers detected: " + ", ".join(violations)
            )


class CommandRunner:
    def run(self, command: list[str]) -> None:
        completed = subprocess.run(command, check=False, text=True)
        if completed.returncode != 0:
            raise QualityGateError("command failed: " + " ".join(command))


class QualityGate:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def run(self) -> None:
        ModuleFunctionGuard(self._project_root / "src/openinfra").assert_no_module_level_functions()
        ContractFileGuard(self._project_root).assert_sources_present()
        NativeRuntimeGuard(self._project_root).assert_runtime_environment_present()
        CiWorkflowTriggerGuard(self._project_root).assert_push_triggers_are_not_branch_locked()
        CompletionMarkerGuard(self._project_root).assert_clean_sources()
        CommandRunner().run(
            [sys.executable, "scripts/security_gate.py", "--project-root", str(self._project_root)]
        )
        CommandRunner().run([sys.executable, "-m", "pytest"])


class QualityGateCli:
    @classmethod
    def main(cls) -> int:
        try:
            QualityGate(Path.cwd()).run()
        except QualityGateError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(QualityGateCli.main())
