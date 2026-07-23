#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from openinfra.quality.contract_completeness_promotion import (  # noqa: E402
    Gate14Qualification,
    Gate14QualificationError,
)


class ContractCompletenessValidationCli:
    @classmethod
    def main(cls) -> int:
        try:
            report = Gate14Qualification().collect(
                project_root=PROJECT_ROOT,
                candidate_id="cdc-4.12-validation",
                source_commit="0" * 40,
                enforce=True,
            )
        except Gate14QualificationError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        metrics = report.metrics
        print(
            "OK: CDC 4.12.0 contractual completeness - "
            f"{metrics.contractual_tests} tests, "
            f"{metrics.automated_proofs} automated, "
            f"{metrics.partial_proofs} partial, "
            f"{metrics.external_proofs} external, "
            f"{metrics.pytest_selectors} pytest selectors"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(ContractCompletenessValidationCli.main())
