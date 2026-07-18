from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404
import sys
import venv
from pathlib import Path
from typing import Final


class IsolatedWheelSmokeWorkerError(RuntimeError):
    """Raised when the isolated installed-wheel qualification fails."""


class IsolatedWheelSmokeWorker:
    _INSTALL_TIMEOUT_SECONDS: Final[int] = 900
    _CHECK_TIMEOUT_SECONDS: Final[int] = 300
    _SMOKE_TIMEOUT_SECONDS: Final[int] = 300

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="isolated-wheel-smoke")
        parser.add_argument("--project-root", type=Path, required=True)
        parser.add_argument("--wheel", type=Path, required=True)
        parser.add_argument("--work-root", type=Path, required=True)
        args = parser.parse_args(argv)
        try:
            evidence = cls().run(args.project_root, args.wheel, args.work_root)
        except IsolatedWheelSmokeWorkerError as exc:
            print(f"isolated-wheel-smoke: error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(evidence, sort_keys=True))
        return 0

    def run(self, project_root: Path, wheel_path: Path, work_root: Path) -> dict[str, object]:
        project_root = project_root.resolve()
        wheel_path = wheel_path.resolve()
        work_root = work_root.resolve()
        smoke_script = project_root / "scripts/smoke_installed_wheel.py"
        if not wheel_path.is_file():
            raise IsolatedWheelSmokeWorkerError(f"wheel does not exist: {wheel_path}")
        if not smoke_script.is_file():
            raise IsolatedWheelSmokeWorkerError(
                f"installed-wheel smoke script does not exist: {smoke_script}"
            )

        environment_root = work_root / "isolated-wheel"
        if environment_root.exists():
            shutil.rmtree(environment_root)
        environment_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            venv.EnvBuilder(with_pip=True, clear=True).create(environment_root)
        except (OSError, subprocess.SubprocessError) as exc:
            raise IsolatedWheelSmokeWorkerError(
                f"isolated Python environment creation failed: {exc}"
            ) from exc

        python_path = self._python_path(environment_root)
        if not python_path.is_file():
            raise IsolatedWheelSmokeWorkerError(
                f"isolated Python executable was not created: {python_path}"
            )
        environment = self._isolated_environment()
        self._run(
            "wheel installation",
            (
                str(python_path),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(wheel_path),
            ),
            project_root,
            environment,
            self._INSTALL_TIMEOUT_SECONDS,
        )
        self._run(
            "wheel dependency check",
            (str(python_path), "-I", "-m", "pip", "check"),
            project_root,
            environment,
            self._CHECK_TIMEOUT_SECONDS,
        )
        self._run(
            "installed wheel smoke",
            (str(python_path), "-I", str(smoke_script)),
            project_root,
            environment,
            self._SMOKE_TIMEOUT_SECONDS,
        )
        return {
            "python": str(python_path),
            "pip_check": "passed",
            "smoke": "passed",
            "wheel": wheel_path.name,
            "worker_process_isolated": True,
        }

    @classmethod
    def _run(
        cls,
        stage: str,
        command: tuple[str, ...],
        project_root: Path,
        environment: dict[str, str],
        timeout_seconds: int,
    ) -> None:
        try:
            completed = subprocess.run(  # nosec B603
                command,
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise IsolatedWheelSmokeWorkerError(
                f"{stage} exceeded {timeout_seconds} seconds"
            ) from exc
        except OSError as exc:
            raise IsolatedWheelSmokeWorkerError(f"{stage} could not start: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            suffix = f": {detail}" if detail else ""
            raise IsolatedWheelSmokeWorkerError(f"{stage} failed{suffix}")

    @classmethod
    def _isolated_environment(cls) -> dict[str, str]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["PYTHONNOUSERSITE"] = "1"
        return environment

    @classmethod
    def _python_path(cls, environment_root: Path) -> Path:
        windows = environment_root / "Scripts/python.exe"
        return windows if windows.is_file() else environment_root / "bin/python"


if __name__ == "__main__":
    raise SystemExit(IsolatedWheelSmokeWorker.main())
