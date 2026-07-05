from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast


class OpenInfraScopeInstallerEntrypoint:
    @classmethod
    def main(cls) -> int:
        runtime_path = cls._locate_runtime()
        module = cls._load_runtime(runtime_path)
        program_cls = cast(Any, module).AutonomousInstallerProgram
        return int(program_cls(Path(__file__)).main())

    @classmethod
    def _locate_runtime(cls) -> Path:
        for parent in Path(__file__).resolve().parents:
            runtime = parent / "installer_runtime.py"
            if runtime.is_file():
                return runtime
        raise SystemExit("cannot locate installers/setup/installer_runtime.py")

    @classmethod
    def _load_runtime(cls, runtime_path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(
            "openinfra_scope_installer_runtime", runtime_path
        )
        if spec is None or spec.loader is None:
            raise SystemExit("cannot load installers/setup/installer_runtime.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


if __name__ == "__main__":
    raise SystemExit(OpenInfraScopeInstallerEntrypoint.main())
