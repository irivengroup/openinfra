from __future__ import annotations

import importlib.util
import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[2]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_toolchain_accepts_exact_versions() -> None:
    module = _load_script("validate_quality_toolchain.py")
    actual = dict(module.EXPECTED_VERSIONS)
    assert module.validate_versions(actual) == ()


def test_quality_toolchain_rejects_missing_and_drifted_versions() -> None:
    module = _load_script("validate_quality_toolchain.py")
    errors = module.validate_versions({"ruff": "0.16.0"}, ("bandit", "mypy"))
    assert errors == (
        "missing quality tool: bandit",
        "missing quality tool: mypy",
        "quality tool version mismatch for ruff: expected 0.15.22, got 0.16.0",
    )


def test_installed_versions_reports_missing_packages() -> None:
    module = _load_script("validate_quality_toolchain.py")

    versions = {"bandit": "1.9.4", "ruff": "0.15.22"}

    def resolver(package: str) -> str:
        if package == "mypy":
            raise PackageNotFoundError(package)
        return versions[package]

    actual, missing = module.installed_versions(resolver)
    assert actual == {"bandit": "1.9.4", "ruff": "0.15.22"}
    assert missing == ("mypy",)


def test_ci_evidence_is_written_atomically(tmp_path: Path) -> None:
    module = _load_script("prepare_ci_evidence.py")
    payload = module.build_payload(
        gate="GATE-14",
        candidate_id="openinfra-test",
        source_commit="abc123",
        run_id="42",
        environment={
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REPOSITORY": "example/openinfra",
            "GITHUB_WORKFLOW": "Contractual completeness GATE-14",
            "GITHUB_JOB": "gate14",
        },
    )
    output = tmp_path / "artifacts/gate14/ci-context.json"
    module.write_atomic(output, payload)

    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["gate"] == "GATE-14"
    assert persisted["candidate_id"] == "openinfra-test"
    assert persisted["github"]["job"] == "gate14"
    assert not output.with_name(output.name + ".tmp").exists()
