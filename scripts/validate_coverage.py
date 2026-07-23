from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Self


class CoverageGateError(RuntimeError):
    """Raised when coverage evidence is malformed or below policy."""


@dataclass(frozen=True, slots=True)
class CoverageEvidence:
    statements: int
    covered: int
    missing: int

    @classmethod
    def load(cls, path: Path) -> Self:
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CoverageGateError(f"cannot read coverage JSON: {path}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("totals"), dict):
            raise CoverageGateError("coverage JSON must contain a totals object")
        totals = payload["totals"]
        statements = cls._integer(totals, "num_statements")
        covered = cls._integer(totals, "covered_lines")
        missing = cls._integer(totals, "missing_lines")
        if statements <= 0:
            raise CoverageGateError("coverage statement count must be positive")
        if covered < 0 or missing < 0 or covered + missing != statements:
            raise CoverageGateError("coverage totals are inconsistent")
        return cls(statements=statements, covered=covered, missing=missing)

    @property
    def percent(self) -> Decimal:
        return Decimal(self.covered) * Decimal(100) / Decimal(self.statements)

    @staticmethod
    def _integer(payload: dict[str, Any], key: str) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise CoverageGateError(f"coverage totals.{key} must be an integer")
        return value


class ExactCoverageGate:
    def __init__(self, minimum: Decimal) -> None:
        if minimum <= 0 or minimum > 100:
            raise CoverageGateError("coverage minimum must be in ]0, 100]")
        self._minimum = minimum

    def evaluate(self, evidence: CoverageEvidence) -> None:
        if evidence.percent < self._minimum:
            raise CoverageGateError(
                "coverage below exact threshold: "
                f"{evidence.percent:.12f}% < {self._minimum:.12f}% "
                f"({evidence.covered}/{evidence.statements}, {evidence.missing} missing)"
            )


class ExactCoverageGateCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(
            description="Validate an exact statement-coverage threshold from coverage.py JSON."
        )
        parser.add_argument("--coverage-json", type=Path, default=Path("coverage.json"))
        parser.add_argument("--minimum", default="98")
        args = parser.parse_args(argv)
        try:
            minimum = Decimal(str(args.minimum))
        except InvalidOperation:
            print("coverage minimum must be numeric", file=sys.stderr)
            return 2
        try:
            evidence = CoverageEvidence.load(args.coverage_json)
            ExactCoverageGate(minimum).evaluate(evidence)
        except CoverageGateError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            "exact coverage gate passed: "
            f"{evidence.percent:.12f}% >= {minimum:.12f}% "
            f"({evidence.covered}/{evidence.statements}, {evidence.missing} missing)"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(ExactCoverageGateCli.main())
