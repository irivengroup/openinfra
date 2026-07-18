from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from scripts.isolated_wheel_smoke import (
    IsolatedWheelSmokeWorker,
    IsolatedWheelSmokeWorkerError,
)


class TestIsolatedWheelSmokeWorker:
    def test_success_runs_install_check_and_smoke(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project_root = tmp_path / "project"
        scripts = project_root / "scripts"
        scripts.mkdir(parents=True)
        smoke_script = scripts / "smoke_installed_wheel.py"
        smoke_script.write_text("smoke", encoding="utf-8")
        wheel = tmp_path / "openinfra.whl"
        wheel.write_bytes(b"wheel")
        calls: list[tuple[str, ...]] = []

        def create(root: Path) -> None:
            python = Path(root) / "bin/python"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("", encoding="utf-8")

        def run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            assert kwargs["cwd"] == project_root.resolve()
            environment = kwargs["env"]
            assert isinstance(environment, dict)
            assert environment["PYTHONNOUSERSITE"] == "1"
            return subprocess.CompletedProcess(command, 0, "", "")

        monkeypatch.setattr(
            "scripts.isolated_wheel_smoke.venv.EnvBuilder.create",
            lambda self, root: create(Path(root)),
        )
        monkeypatch.setattr("scripts.isolated_wheel_smoke.subprocess.run", run)
        evidence = IsolatedWheelSmokeWorker().run(project_root, wheel, tmp_path / "work")
        assert evidence == {
            "python": str((tmp_path / "work/isolated-wheel/bin/python").resolve()),
            "pip_check": "passed",
            "smoke": "passed",
            "wheel": "openinfra.whl",
            "worker_process_isolated": True,
        }
        assert len(calls) == 3
        assert calls[0][2:5] == ("-m", "pip", "install")
        assert calls[1][-2:] == ("pip", "check")
        assert calls[2][-1] == str(smoke_script.resolve())

    @pytest.mark.parametrize(
        ("failed_call", "expected"),
        (
            (1, "wheel installation failed"),
            (2, "wheel dependency check failed"),
            (3, "installed wheel smoke failed"),
        ),
    )
    def test_subprocess_failure_is_stage_specific(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        failed_call: int,
        expected: str,
    ) -> None:
        project_root, wheel = self._fixture(tmp_path)
        self._mock_venv(monkeypatch)
        calls = {"count": 0}

        def run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
            del kwargs
            calls["count"] += 1
            return subprocess.CompletedProcess(
                command,
                1 if calls["count"] == failed_call else 0,
                "",
                "stage-error",
            )

        monkeypatch.setattr("scripts.isolated_wheel_smoke.subprocess.run", run)
        with pytest.raises(IsolatedWheelSmokeWorkerError, match=expected):
            IsolatedWheelSmokeWorker().run(project_root, wheel, tmp_path / "work")

    def test_timeout_os_error_and_invalid_inputs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worker = IsolatedWheelSmokeWorker()
        with pytest.raises(IsolatedWheelSmokeWorkerError, match="wheel does not exist"):
            worker.run(tmp_path, tmp_path / "missing.whl", tmp_path / "work")
        wheel = tmp_path / "openinfra.whl"
        wheel.write_bytes(b"wheel")
        with pytest.raises(IsolatedWheelSmokeWorkerError, match="smoke script does not exist"):
            worker.run(tmp_path, wheel, tmp_path / "work")

        project_root, wheel = self._fixture(tmp_path / "valid")
        self._mock_venv(monkeypatch)

        def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            del args, kwargs
            raise subprocess.TimeoutExpired(["pip"], 1)

        monkeypatch.setattr("scripts.isolated_wheel_smoke.subprocess.run", timeout)
        with pytest.raises(IsolatedWheelSmokeWorkerError, match="exceeded"):
            worker.run(project_root, wheel, tmp_path / "timeout-work")

        def os_error(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            del args, kwargs
            raise OSError("unavailable")

        monkeypatch.setattr("scripts.isolated_wheel_smoke.subprocess.run", os_error)
        with pytest.raises(IsolatedWheelSmokeWorkerError, match="could not start"):
            worker.run(project_root, wheel, tmp_path / "os-work")

    def test_main_outputs_json_and_failure_code(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        project_root, wheel = self._fixture(tmp_path)
        evidence = {
            "python": "/isolated/python",
            "pip_check": "passed",
            "smoke": "passed",
            "wheel": wheel.name,
            "worker_process_isolated": True,
        }
        monkeypatch.setattr(
            IsolatedWheelSmokeWorker,
            "run",
            lambda self, project, artifact, work: evidence,
        )
        assert (
            IsolatedWheelSmokeWorker.main(
                [
                    "--project-root",
                    str(project_root),
                    "--wheel",
                    str(wheel),
                    "--work-root",
                    str(tmp_path / "work"),
                ]
            )
            == 0
        )
        assert json.loads(capsys.readouterr().out) == evidence

        def fail(*args: object, **kwargs: object) -> dict[str, object]:
            del args, kwargs
            raise IsolatedWheelSmokeWorkerError("failure")

        monkeypatch.setattr(IsolatedWheelSmokeWorker, "run", fail)
        assert (
            IsolatedWheelSmokeWorker.main(
                [
                    "--project-root",
                    str(project_root),
                    "--wheel",
                    str(wheel),
                    "--work-root",
                    str(tmp_path / "work"),
                ]
            )
            == 2
        )
        assert "failure" in capsys.readouterr().err

    @staticmethod
    def _fixture(tmp_path: Path) -> tuple[Path, Path]:
        project_root = tmp_path / "project"
        scripts = project_root / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "smoke_installed_wheel.py").write_text("smoke", encoding="utf-8")
        wheel = tmp_path / "openinfra.whl"
        wheel.write_bytes(b"wheel")
        return project_root, wheel

    @staticmethod
    def _mock_venv(monkeypatch: pytest.MonkeyPatch) -> None:
        def create(root: Path) -> None:
            python = Path(root) / "bin/python"
            python.parent.mkdir(parents=True, exist_ok=True)
            python.write_text("", encoding="utf-8")

        monkeypatch.setattr(
            "scripts.isolated_wheel_smoke.venv.EnvBuilder.create",
            lambda self, root: create(Path(root)),
        )
