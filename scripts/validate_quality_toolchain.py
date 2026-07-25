from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Callable, Mapping, Sequence

EXPECTED_VERSIONS: Mapping[str, str] = {
    "bandit": "1.9.4",
    "mypy": "2.2.0",
    "ruff": "0.15.22",
}


def installed_versions(
    resolver: Callable[[str], str] = version,
) -> tuple[dict[str, str], tuple[str, ...]]:
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for package in sorted(EXPECTED_VERSIONS):
        try:
            resolved[package] = resolver(package)
        except PackageNotFoundError:
            missing.append(package)
    return resolved, tuple(missing)


def validate_versions(
    actual: Mapping[str, str],
    missing: Sequence[str] = (),
) -> tuple[str, ...]:
    errors = [f"missing quality tool: {package}" for package in sorted(missing)]
    for package, expected in sorted(EXPECTED_VERSIONS.items()):
        current = actual.get(package)
        if current is None:
            if package not in missing:
                errors.append(f"missing quality tool: {package}")
            continue
        if current != expected:
            errors.append(
                f"quality tool version mismatch for {package}: expected {expected}, got {current}"
            )
    return tuple(errors)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the deterministic OpenInfra formatting, typing, and SAST toolchain.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    actual, missing = installed_versions()
    errors = validate_versions(actual, missing)
    payload = {
        "expected": dict(sorted(EXPECTED_VERSIONS.items())),
        "installed": dict(sorted(actual.items())),
        "missing": list(missing),
        "passed": not errors,
        "errors": list(errors),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(error, file=sys.stderr)
    else:
        versions = ", ".join(f"{name}={value}" for name, value in sorted(actual.items()))
        print(f"OpenInfra quality toolchain validated: {versions}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
