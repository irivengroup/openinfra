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


class RuntimeDockerGuard:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    def assert_runtime_environment_present(self) -> None:
        required = (
            "Dockerfile",
            "compose.yaml",
            ".env.example",
            "docker/openinfra-runtime-smoke.py",
            "scripts/docker_environment.py",
            "docs/runbooks/RUNTIME_DOCKER.md",
        )
        missing = [name for name in required if not (self._project_root / name).is_file()]
        if missing:
            raise QualityGateError("missing runtime docker assets: " + ", ".join(missing))
        compose = (self._project_root / "compose.yaml").read_text(encoding="utf-8")
        for service_name in ("postgres:", "migrate:", "auth-bootstrap:", "api:", "smoke:"):
            if service_name not in compose:
                raise QualityGateError("compose service missing: " + service_name.rstrip(":"))
        if "service_healthy" not in compose or "service_completed_successfully" not in compose:
            raise QualityGateError(
                "compose runtime dependencies must enforce health and migration order"
            )
        env_example = (self._project_root / ".env.example").read_text(encoding="utf-8")
        if "OPENINFRA_POSTGRES_PASSWORD=" not in env_example:
            raise QualityGateError(".env.example must document OPENINFRA_POSTGRES_PASSWORD")
        if "OPENINFRA_BOOTSTRAP_TOKEN=" not in env_example:
            raise QualityGateError(".env.example must document OPENINFRA_BOOTSTRAP_TOKEN")
        if "OPENINFRA_AUTH_REQUIRED" not in compose:
            raise QualityGateError("runtime API must enable authentication explicitly")
        if (self._project_root / ".env").exists():
            raise QualityGateError("local .env must not be packaged or committed")


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
        RuntimeDockerGuard(self._project_root).assert_runtime_environment_present()
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
