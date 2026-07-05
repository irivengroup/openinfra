from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


class FrontendValidationError(Exception):
    """Raised when the OpenInfra frontend contract is incomplete."""


@dataclass(frozen=True, slots=True)
class FrontendValidationReport:
    project_root: Path
    react_declared: bool
    bootstrap_declared: bool
    compose_web_service: bool
    static_assets: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "react_declared": self.react_declared,
            "bootstrap_declared": self.bootstrap_declared,
            "compose_web_service": self.compose_web_service,
            "static_assets": list(self.static_assets),
            "valid": True,
        }


class FrontendContractValidator:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()

    def validate(self) -> FrontendValidationReport:
        package = self._read_json(self._project_root / "web/package.json")
        dependencies = package.get("dependencies", {})
        if not isinstance(dependencies, dict):
            raise FrontendValidationError("web/package.json dependencies must be an object")
        react_declared = "react" in dependencies and "react-dom" in dependencies
        bootstrap_declared = "bootstrap" in dependencies
        if not react_declared:
            raise FrontendValidationError("web/package.json must declare React and React DOM")
        if not bootstrap_declared:
            raise FrontendValidationError("web/package.json must declare Bootstrap 5")
        main_source = (self._project_root / "web/src/main.jsx").read_text(encoding="utf-8")
        if (
            "from 'react'" not in main_source
            or "bootstrap/dist/css/bootstrap.min.css" not in main_source
            or "openinfra-theme.css" not in main_source
            or "Dashboard de pilotage OpenInfra" not in main_source
            or "openinfra-accordion" not in main_source
            or "Numéro de série" not in main_source
            or "Token API" in main_source
        ):
            raise FrontendValidationError(
                "web/src/main.jsx must implement the OpenInfra React + Bootstrap dashboard UI"
            )
        for required_header_fragment in (
            "bg-dark text-white",
            "text-small",
        ):
            if required_header_fragment not in main_source:
                raise FrontendValidationError(
                    "web/src/main.jsx must keep the Bootstrap 5 single-header dashboard theme"
                )
        forbidden_main_source = (
            "Search OpenInfra operations",
            "openinfra-search",
            "Login</button>",
            "Sign-up",
        )
        leaked_main = [fragment for fragment in forbidden_main_source if fragment in main_source]
        if leaked_main:
            raise FrontendValidationError(
                "web/src/main.jsx must not expose the removed secondary header controls: "
                + ", ".join(leaked_main)
            )
        compose = (self._project_root / "compose.yaml").read_text(encoding="utf-8")
        compose_required = (
            "  web:",
            "container_name: openinfra-web",
            "OPENINFRA_WEB_BACKEND_URL",
            "OPENINFRA_WEB_PUBLIC_API_BASE_URL",
            "http://127.0.0.1:2006/health",
        )
        missing_compose = [fragment for fragment in compose_required if fragment not in compose]
        if missing_compose:
            raise FrontendValidationError(
                "compose.yaml openinfra-web service is incomplete: " + ", ".join(missing_compose)
            )
        assets = self._validate_static_assets()
        return FrontendValidationReport(
            project_root=self._project_root,
            react_declared=react_declared,
            bootstrap_declared=bootstrap_declared,
            compose_web_service=True,
            static_assets=assets,
        )

    def _read_json(self, path: Path) -> dict[str, object]:
        if not path.is_file():
            raise FrontendValidationError("missing frontend file: " + str(path))
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FrontendValidationError("invalid JSON object: " + str(path))
        return data

    def _validate_static_assets(self) -> tuple[str, ...]:
        root = self._project_root / "src/openinfra/interfaces/rendering/static"
        required = (
            "index.html",
            "assets/bootstrap.min.css",
            "assets/openinfra-web.js",
            "assets/openinfra-web.css",
        )
        missing = [name for name in required if not (root / name).is_file()]
        if missing:
            raise FrontendValidationError("missing runtime web assets: " + ", ".join(missing))
        payload = "\n".join((root / name).read_text(encoding="utf-8") for name in required)
        for fragment in (
            "Dashboard de pilotage OpenInfra",
            "bg-dark text-white",
            "openinfra-sidebar",
            "openinfra-accordion",
            "Ressources Inventory",
            "agents proxy collectors Enterprise uniquement",
            "Numéro de série",
        ):
            if fragment not in payload:
                raise FrontendValidationError(
                    "runtime web assets do not expose the Bootstrap dashboard contract"
                )
        forbidden = ("OPENINFRA_DATABASE_DSN", "postgresql://", "bind_password", "client_key")
        leaked = [fragment for fragment in forbidden if fragment in payload]
        if leaked:
            raise FrontendValidationError("runtime web assets leak forbidden backend data")
        for forbidden_ui in (
            "Token API",
            "openinfra-method",
            "Search OpenInfra operations",
            "openinfra-search",
            "openinfra-login",
            "openinfra-signup",
            "Sign-up",
        ):
            if forbidden_ui in payload:
                raise FrontendValidationError(
                    "runtime web assets expose a forbidden generic/technical UI fragment: "
                    + forbidden_ui
                )
        return required


class FrontendValidationCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Validate OpenInfra P08 frontend contract")
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        args = parser.parse_args()
        try:
            report = FrontendContractValidator(args.project_root).validate()
        except (FrontendValidationError, json.JSONDecodeError) as exc:
            sys.stderr.write(str(exc) + "\n")
            return 1
        print(json.dumps(report.as_dict(), sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(FrontendValidationCli.main())
