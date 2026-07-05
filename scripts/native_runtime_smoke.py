from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openinfra.infrastructure.installer_config import InstallerConfigValidator


@dataclass(frozen=True, slots=True)
class NativeRuntimeAssetReport:
    project_root: Path
    runbook: Path
    version_file: Path
    rendered_units: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "runbook": str(self.runbook),
            "version_file": str(self.version_file),
            "rendered_units": list(self.rendered_units),
        }


class NativeRuntimeSmokeError(RuntimeError):
    """Raised when the native runtime smoke check fails."""


class NativeRuntimeAssetChecker:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()

    def check(self) -> NativeRuntimeAssetReport:
        runbook = self._project_root / "docs/runbooks/RUNTIME_NATIVE.md"
        version = self._project_root / "VERSION"
        missing = [str(path) for path in (runbook, version) if not path.is_file()]
        if missing:
            raise NativeRuntimeSmokeError("missing native runtime asset: " + ", ".join(missing))
        if (self._project_root / "deploy").exists():
            raise NativeRuntimeSmokeError("deploy directory must not be packaged")
        runbook_text = runbook.read_text(encoding="utf-8")
        if "OPENINFRA_DATABASE_DSN" not in runbook_text:
            raise NativeRuntimeSmokeError("native runbook must document OPENINFRA_DATABASE_DSN")
        if "commande docker obligatoire" in runbook_text.lower():
            raise NativeRuntimeSmokeError("native runbook must not require a container runtime")
        validator = InstallerConfigValidator()
        rendered = (
            validator.render_systemd_unit("lite", "all-in-one"),
            validator.render_systemd_unit("pro", "web"),
            validator.render_systemd_unit("enterprise", "agent"),
        )
        required_fragments = (
            "ExecStart=/opt/openinfra/venv/bin/openinfra-api",
            "ExecStart=/opt/openinfra/venv/bin/python -m http.server 2006",
            "openinfra-agent.service",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
        )
        payload = "\n".join(rendered)
        missing_fragments = [fragment for fragment in required_fragments if fragment not in payload]
        if missing_fragments:
            raise NativeRuntimeSmokeError(
                "installer-rendered systemd units are incomplete: " + ", ".join(missing_fragments)
            )
        return NativeRuntimeAssetReport(
            self._project_root,
            runbook,
            version,
            ("openinfra.service", "openinfra-web.service", "openinfra-agent.service"),
        )


class NativeHttpSmokeClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def check(self) -> dict[str, Any]:
        health = self._get_json("/health")
        ready_status, ready = self._get_json_with_status("/ready")
        version = self._get_json("/api/v1/version")
        if health.get("status") != "ok":
            raise NativeRuntimeSmokeError("/health did not return status ok")
        if ready_status not in {200, 503}:
            raise NativeRuntimeSmokeError("/ready returned an unsupported status")
        if "version" not in version:
            raise NativeRuntimeSmokeError("/api/v1/version did not return a version field")
        return {"health": health, "ready_status": ready_status, "ready": ready, "version": version}

    def _get_json(self, path: str) -> dict[str, Any]:
        status, payload = self._get_json_with_status(path)
        if status >= 400:
            raise NativeRuntimeSmokeError(f"{path} returned HTTP {status}")
        return payload

    def _get_json_with_status(self, path: str) -> tuple[int, dict[str, Any]]:
        request = urllib.request.Request(self._base_url + path, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return int(response.status), json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return int(exc.code), json.loads(exc.read().decode("utf-8"))


class NativeRuntimeSmokeCli:
    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(
            description="Validate OpenInfra native server runtime assets"
        )
        parser.add_argument("--project-root", type=Path, default=Path.cwd())
        parser.add_argument("--base-url")
        args = parser.parse_args()
        try:
            report = NativeRuntimeAssetChecker(args.project_root).check()
            result: dict[str, Any] = {"assets": report.as_dict()}
            if args.base_url:
                result["http"] = NativeHttpSmokeClient(args.base_url).check()
            print(json.dumps(result, sort_keys=True))
        except NativeRuntimeSmokeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(NativeRuntimeSmokeCli.main())
