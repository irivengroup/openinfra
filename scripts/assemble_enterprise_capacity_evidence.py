from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from openinfra.domain.common import ValidationError


def _load_object(path: Path) -> dict[str, object]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON evidence {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON evidence must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assemble_capacity_evidence(
    *,
    profile_path: Path,
    topology_path: Path,
    stage_directory: Path,
    chaos_directory: Path,
    output_path: Path,
) -> dict[str, object]:
    profile = _load_object(profile_path)
    topology = _load_object(topology_path)
    required_stages = profile.get("required_capacity_stages")
    required_chaos = profile.get("required_chaos_scenarios")
    thresholds = profile.get("thresholds")
    if not isinstance(required_stages, list) or not all(
        isinstance(value, str) for value in required_stages
    ):
        raise ValidationError("profile required_capacity_stages must be a string array")
    if not isinstance(required_chaos, list) or not all(
        isinstance(value, str) for value in required_chaos
    ):
        raise ValidationError("profile required_chaos_scenarios must be a string array")
    if not isinstance(thresholds, dict):
        raise ValidationError("profile thresholds must be an object")
    source_hashes = {
        "profile": _sha256(profile_path),
        "topology": _sha256(topology_path),
    }
    stages: list[dict[str, object]] = []
    for name in required_stages:
        path = stage_directory / f"{name}.json"
        evidence = _load_object(path)
        if evidence.get("stage") != name:
            raise ValidationError(f"stage file {path} does not identify stage {name}")
        stages.append(evidence)
        source_hashes[f"stage:{name}"] = _sha256(path)
    chaos: list[dict[str, object]] = []
    for name in required_chaos:
        path = chaos_directory / f"{name}.json"
        evidence = _load_object(path)
        if evidence.get("scenario") != name:
            raise ValidationError(f"chaos file {path} does not identify scenario {name}")
        chaos.append(evidence)
        source_hashes[f"chaos:{name}"] = _sha256(path)
    payload: dict[str, object] = {
        "profile_id": profile.get("profile_id"),
        "profile_version": profile.get("profile_version"),
        "topology": topology,
        "thresholds": thresholds,
        "stages": stages,
        "chaos": chaos,
        "source_hashes": source_hashes,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    return payload


class EnterpriseCapacityEvidenceAssemblerCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="assemble-enterprise-capacity-evidence")
        parser.add_argument("--profile", type=Path, required=True)
        parser.add_argument("--topology", type=Path, required=True)
        parser.add_argument("--stages", type=Path, required=True)
        parser.add_argument("--chaos", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args(argv)
        payload = assemble_capacity_evidence(
            profile_path=args.profile,
            topology_path=args.topology,
            stage_directory=args.stages,
            chaos_directory=args.chaos,
            output_path=args.output,
        )
        source_hashes = payload.get("source_hashes")
        source_count = len(source_hashes) if isinstance(source_hashes, dict) else 0
        print(json.dumps({"output": str(args.output), "sources": source_count}))
        return 0


if __name__ == "__main__":
    raise SystemExit(EnterpriseCapacityEvidenceAssemblerCli.main())
