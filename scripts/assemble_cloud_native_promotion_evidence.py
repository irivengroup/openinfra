from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__
from openinfra.quality.cloud_native_promotion import (
    CloudNativePromotionError,
    CloudNativePromotionPolicy,
)


class CloudNativePromotionAssembler:
    EVIDENCE = tuple(CloudNativePromotionPolicy.EXPECTED_EVIDENCE.items())

    @classmethod
    def assemble(
        cls,
        *,
        candidate_id: str,
        source_commit: str,
        sources: dict[str, Path],
        evidence_root: Path,
    ) -> dict[str, object]:
        normalized_commit = source_commit.strip().lower()
        if len(normalized_commit) != 40 or any(
            char not in "0123456789abcdef" for char in normalized_commit
        ):
            raise CloudNativePromotionError("source_commit must be a full lowercase SHA-1")
        normalized_candidate = candidate_id.strip()
        if not normalized_candidate or len(normalized_candidate) > 160:
            raise CloudNativePromotionError("candidate_id is invalid")
        evidence_root.mkdir(parents=True, exist_ok=True)
        references: list[dict[str, str]] = []
        for identifier, report_kind in cls.EVIDENCE:
            source = sources.get(identifier)
            if source is None or not source.is_file():
                raise CloudNativePromotionError(f"required evidence is missing: {identifier}")
            raw = source.read_bytes()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise CloudNativePromotionError(f"evidence is invalid JSON: {identifier}") from exc
            if not isinstance(payload, dict):
                raise CloudNativePromotionError(f"evidence root must be an object: {identifier}")
            if payload.get("report_kind") != report_kind:
                raise CloudNativePromotionError(
                    f"evidence report_kind mismatch for {identifier}: expected {report_kind}"
                )
            if payload.get("release_version") != __version__:
                raise CloudNativePromotionError(
                    f"evidence release_version mismatch for {identifier}: expected {__version__}"
                )
            target = evidence_root / f"{identifier}.json"
            temporary = target.with_suffix(".json.tmp")
            temporary.write_bytes(raw)
            temporary.replace(target)
            references.append(
                {
                    "id": identifier,
                    "report_kind": report_kind,
                    "path": target.name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        return {
            "schema_version": 1,
            "gate_id": "GATE-10",
            "release_version": __version__,
            "candidate_id": normalized_candidate,
            "source_commit": normalized_commit,
            "generated_at": datetime.now(UTC).isoformat(),
            "evidence": references,
        }


class CloudNativePromotionAssemblerCli:
    @staticmethod
    def _write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Assemble immutable GATE-10 evidence")
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--topology", type=Path, required=True)
        parser.add_argument("--exposure", type=Path, required=True)
        parser.add_argument("--security", type=Path, required=True)
        parser.add_argument("--gitops", type=Path, required=True)
        parser.add_argument("--capacity", type=Path, required=True)
        parser.add_argument("--runtime", type=Path, required=True)
        parser.add_argument("--qualification", type=Path, required=True)
        parser.add_argument("--evidence-root", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args()
        sources = {
            "epic-2101-topology": args.topology,
            "epic-2102-exposure": args.exposure,
            "epic-2103-security": args.security,
            "epic-2104-gitops": args.gitops,
            "epic-2105-capacity": args.capacity,
            "epic-2106-runtime": args.runtime,
            "epic-2106-contract": args.qualification,
        }
        try:
            report = CloudNativePromotionAssembler.assemble(
                candidate_id=args.candidate_id,
                source_commit=args.source_commit,
                sources=sources,
                evidence_root=args.evidence_root,
            )
        except (OSError, CloudNativePromotionError) as exc:
            parser.error(str(exc))
        cls._write_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(CloudNativePromotionAssemblerCli.main())
