from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class MultisiteChaosValidationError(Exception):
    pass


class MultisiteChaosProjectValidator:
    _required_scenarios = (
        "network-partition",
        "site-loss",
        "agent-loss",
        "database-loss",
        "queue-saturation",
        "frontend-loss",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def validate(self) -> dict[str, object]:
        required_files = (
            "src/openinfra/quality/multisite_chaos.py",
            "scripts/run_multisite_chaos_campaign.py",
            "scripts/assemble_multisite_chaos_evidence.py",
            "scripts/certify_multisite_chaos.py",
            "scripts/validate_multisite_chaos.py",
            "docs/operations/multisite-chaos-profile.json",
            "docs/runbooks/MULTISITE_CHAOS.md",
            ".github/workflows/multisite-chaos.yml",
            "tests/unit/test_multisite_chaos_certification.py",
            "tests/integration/test_multisite_chaos_tooling.py",
        )
        missing = [name for name in required_files if not (self._root / name).is_file()]
        if missing:
            raise MultisiteChaosValidationError(
                "missing multisite chaos assets: " + ", ".join(missing)
            )
        profile = self._load_json(self._root / "docs/operations/multisite-chaos-profile.json")
        if profile.get("profile_id") != "openinfra-multisite-chaos-v1":
            raise MultisiteChaosValidationError("invalid multisite chaos profile_id")
        if profile.get("profile_version") != 1:
            raise MultisiteChaosValidationError("invalid multisite chaos profile_version")
        if profile.get("edition") != "enterprise":
            raise MultisiteChaosValidationError("multisite chaos profile must target Enterprise")
        if profile.get("required_scenarios") != list(self._required_scenarios):
            raise MultisiteChaosValidationError(
                "multisite chaos required scenario order is invalid"
            )
        objectives = profile.get("objectives")
        if not isinstance(objectives, dict) or tuple(objectives) != self._required_scenarios:
            raise MultisiteChaosValidationError(
                "multisite chaos objectives must cover six scenarios"
            )
        workflow = (self._root / ".github/workflows/multisite-chaos.yml").read_text(
            encoding="utf-8"
        )
        required_workflow_fragments = (
            "workflow_dispatch:",
            "runs-on: [self-hosted, linux, x64, openinfra-multisite-chaos]",
            "environment: multisite-chaos-certification",
            "OPENINFRA_MULTISITE_CHAOS_HARNESS",
            "run_multisite_chaos_campaign.py",
            "assemble_multisite_chaos_evidence.py",
            "certify_multisite_chaos.py",
            "--enforce",
            "retention-days: 90",
        )
        absent = [fragment for fragment in required_workflow_fragments if fragment not in workflow]
        if absent:
            raise MultisiteChaosValidationError(
                "multisite chaos workflow is incomplete: " + ", ".join(absent)
            )
        if "pull_request_target:" in workflow:
            raise MultisiteChaosValidationError(
                "multisite chaos workflow must not execute from pull_request_target"
            )
        runner = (self._root / "scripts/run_multisite_chaos_campaign.py").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "preflight",
            "inject",
            "recover",
            "verify-recovered",
            "must not be group/world writable",
            "unsafe to continue chaos campaign after failed recovery",
            "integrity_sha256_before",
            "integrity_sha256_after",
        ):
            if fragment not in runner:
                raise MultisiteChaosValidationError(
                    "multisite chaos runner contract is incomplete: " + fragment
                )
        return {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "scenario_count": len(self._required_scenarios),
            "status": "passed",
        }

    @staticmethod
    def _load_json(path: Path) -> dict[str, object]:
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MultisiteChaosValidationError(f"cannot read JSON {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise MultisiteChaosValidationError(f"JSON root must be an object: {path}")
        return {str(key): value for key, value in payload.items()}


class MultisiteChaosValidatorCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="validate-multisite-chaos")
        parser.add_argument("--project-root", type=Path, default=Path("."))
        args = parser.parse_args(argv)
        try:
            report = MultisiteChaosProjectValidator(args.project_root).validate()
        except MultisiteChaosValidationError as exc:
            print(f"multisite-chaos-validation: FAIL: {exc}")
            return 1
        print(json.dumps(report, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(MultisiteChaosValidatorCli.main())
