from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create deterministic CI diagnostic metadata.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True)
    return parser


def build_payload(
    *,
    gate: str,
    candidate_id: str,
    source_commit: str,
    run_id: str,
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    env = os.environ if environment is None else environment
    return {
        "schema_version": 1,
        "gate": gate,
        "candidate_id": candidate_id,
        "source_commit": source_commit,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runner": {
            "os": env.get("RUNNER_OS", platform.system()),
            "architecture": env.get("RUNNER_ARCH", platform.machine()),
            "python": platform.python_version(),
        },
        "github": {
            "ref": env.get("GITHUB_REF", ""),
            "repository": env.get("GITHUB_REPOSITORY", ""),
            "workflow": env.get("GITHUB_WORKFLOW", ""),
            "job": env.get("GITHUB_JOB", ""),
        },
    }


def write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_payload(
        gate=args.gate,
        candidate_id=args.candidate_id,
        source_commit=args.source_commit,
        run_id=args.run_id,
    )
    write_atomic(args.output, payload)
    print(f"CI evidence context written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
