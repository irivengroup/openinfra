from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openinfra.domain.common import ValidationError
from openinfra.quality.multisite_chaos import MultisiteChaosCampaignEvidence


def _load_object(path: Path) -> dict[str, object]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def assemble_multisite_chaos_evidence(
    *,
    profile_path: Path,
    topology_id: str,
    reports_directory: Path,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    profile = _load_object(profile_path)
    required = list(MultisiteChaosCampaignEvidence.required_scenarios())
    if profile.get("profile_id") != "openinfra-multisite-chaos-v1":
        raise ValidationError("unsupported multisite chaos profile")
    if profile.get("profile_version") != 1:
        raise ValidationError("multisite chaos profile_version must be 1")
    if profile.get("edition") != "enterprise":
        raise ValidationError("multisite chaos profile must target Enterprise edition")
    if profile.get("required_scenarios") != required:
        raise ValidationError("multisite chaos required scenario order is invalid")
    objectives = profile.get("objectives")
    if not isinstance(objectives, dict):
        raise ValidationError("multisite chaos profile objectives must be an object")
    normalized_topology = " ".join(topology_id.strip().split())
    if not normalized_topology:
        raise ValidationError("topology_id must not be empty")
    timestamp = generated_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValidationError("generated_at must be timezone-aware")
    scenarios: list[dict[str, object]] = []
    artifacts: list[dict[str, object]] = []
    for scenario in required:
        path = reports_directory / f"{scenario}.json"
        content = path.read_bytes()
        if not content:
            raise ValidationError(f"multisite chaos report is empty: {path}")
        report = _load_object(path)
        if report.get("scenario") != scenario:
            raise ValidationError(f"multisite chaos report scenario mismatch: {path}")
        scenarios.append(report)
        artifacts.append(
            {
                "name": scenario,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
            }
        )
    evidence: dict[str, object] = {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "edition": profile["edition"],
        "topology_id": normalized_topology,
        "generated_at": timestamp.astimezone(UTC).isoformat(),
        "objectives": objectives,
        "scenarios": scenarios,
        "source_artifacts": artifacts,
    }
    evidence["evidence_digest"] = MultisiteChaosCampaignEvidence.digest_for(evidence)
    MultisiteChaosCampaignEvidence.from_mapping(evidence)
    return evidence


class MultisiteChaosEvidenceAssemblerCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="assemble-multisite-chaos-evidence")
        parser.add_argument("--profile", type=Path, required=True)
        parser.add_argument("--topology-id", required=True)
        parser.add_argument("--reports", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args(argv)
        try:
            evidence = assemble_multisite_chaos_evidence(
                profile_path=args.profile,
                topology_id=args.topology_id,
                reports_directory=args.reports,
            )
        except (OSError, ValidationError) as exc:
            print(f"multisite-chaos-evidence: FAIL: {exc}")
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(args.output)
        print(json.dumps({"status": "assembled", "output": str(args.output)}, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(MultisiteChaosEvidenceAssemblerCli.main())
