from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__
from openinfra.quality.scaleout_promotion import ScaleoutPromotionError


class ScaleoutPromotionAssembler:
    EVIDENCE = (
        ("p20-contracts", "p20-contracts"),
        ("enterprise-capacity", "enterprise-capacity"),
        ("multisite-chaos", "multisite-chaos"),
        ("pra-pca", "pra-pca"),
        ("release-security", "release-security"),
        ("release-packaging", "release-packaging"),
        ("ga-go-no-go", "ga-go-no-go"),
    )

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
            raise ScaleoutPromotionError("source_commit must be a full lowercase SHA-1")
        normalized_candidate = candidate_id.strip()
        if not normalized_candidate or len(normalized_candidate) > 160:
            raise ScaleoutPromotionError("candidate_id is invalid")
        evidence_root.mkdir(parents=True, exist_ok=True)
        references: list[dict[str, str]] = []
        for identifier, report_kind in cls.EVIDENCE:
            source = sources.get(identifier)
            if source is None or not source.is_file():
                raise ScaleoutPromotionError(f"required evidence is missing: {identifier}")
            target = evidence_root / f"{identifier}.json"
            raw = source.read_bytes()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ScaleoutPromotionError(f"evidence is invalid JSON: {identifier}") from exc
            if not isinstance(payload, dict):
                raise ScaleoutPromotionError(f"evidence root must be an object: {identifier}")
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
            "gate_id": "GATE-09",
            "release_version": __version__,
            "candidate_id": normalized_candidate,
            "source_commit": normalized_commit,
            "generated_at": datetime.now(UTC).isoformat(),
            "evidence": references,
        }


class ScaleoutPromotionAssemblerCli:
    @staticmethod
    def _write_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def main(cls) -> int:
        parser = argparse.ArgumentParser(description="Assemble immutable GATE-09 evidence")
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--p20-contracts", type=Path, required=True)
        parser.add_argument("--enterprise-capacity", type=Path, required=True)
        parser.add_argument("--multisite-chaos", type=Path, required=True)
        parser.add_argument("--pra-pca", type=Path, required=True)
        parser.add_argument("--release-security", type=Path, required=True)
        parser.add_argument("--release-packaging", type=Path, required=True)
        parser.add_argument("--ga-go-no-go", type=Path, required=True)
        parser.add_argument("--evidence-root", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args()
        sources = {
            "p20-contracts": args.p20_contracts,
            "enterprise-capacity": args.enterprise_capacity,
            "multisite-chaos": args.multisite_chaos,
            "pra-pca": args.pra_pca,
            "release-security": args.release_security,
            "release-packaging": args.release_packaging,
            "ga-go-no-go": args.ga_go_no_go,
        }
        try:
            report = ScaleoutPromotionAssembler.assemble(
                candidate_id=args.candidate_id,
                source_commit=args.source_commit,
                sources=sources,
                evidence_root=args.evidence_root,
            )
        except (OSError, ScaleoutPromotionError, shutil.Error) as exc:
            parser.error(str(exc))
        cls._write_atomic(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(ScaleoutPromotionAssemblerCli.main())
