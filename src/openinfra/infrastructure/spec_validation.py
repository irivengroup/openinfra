from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from openinfra.domain.common import ValidationError


@dataclass(frozen=True, slots=True)
class SpecValidationReport:
    root: Path
    version: str
    requirements: int
    tests: int
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_text(self) -> str:
        status = "valid" if self.valid else "invalid"
        details = [
            f"status={status}",
            f"root={self.root}",
            f"version={self.version}",
            f"requirements={self.requirements}",
            f"tests={self.tests}",
        ]
        details.extend(f"error={error}" for error in self.errors)
        return "\n".join(details)


class ContractualSpecValidator:
    SUPPORTED_VERSIONS = frozenset({"4.0.0", "4.8.1", "4.9.0", "4.10.0", "4.11.0"})

    def validate(self, root: Path) -> SpecValidationReport:
        errors: list[str] = []
        self._assert_required_files(root, errors)
        version = self._read_version(root, errors)
        requirements = self._count_csv_rows(root / "11-Matrices" / "Exigences.csv", errors)
        tests = self._count_csv_rows(root / "11-Matrices" / "Tests.csv", errors)
        self._assert_no_integrated_itsm(root, errors)
        return SpecValidationReport(
            root=root,
            version=version,
            requirements=requirements,
            tests=tests,
            errors=tuple(errors),
        )

    def assert_valid(self, root: Path) -> SpecValidationReport:
        report = self.validate(root)
        if not report.valid:
            raise ValidationError(report.as_text())
        return report

    def _assert_required_files(self, root: Path, errors: list[str]) -> None:
        required = (
            "00-README.md",
            "03-Technique/02-PostgreSQL-Cluster.md",
            "04-Donnees/Partitions.md",
            "08-RFC-ADR/ADR-0005-No-Integrated-ITSM.md",
            "11-Matrices/Exigences.csv",
            "11-Matrices/Tests.csv",
            "VERSION",
        )
        for relative in required:
            if not (root / relative).is_file():
                errors.append(f"missing required spec file: {relative}")

    def _read_version(self, root: Path, errors: list[str]) -> str:
        version_file = root / "VERSION"
        if not version_file.is_file():
            return "unknown"
        version = version_file.read_text(encoding="utf-8").strip()
        if version not in self.SUPPORTED_VERSIONS:
            errors.append(f"unsupported specification version: {version}")
        return version

    def _count_csv_rows(self, path: Path, errors: list[str]) -> int:
        if not path.is_file():
            return 0
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if not rows:
            errors.append(f"csv file is empty: {path.name}")
        return len(rows)

    def _assert_no_integrated_itsm(self, root: Path, errors: list[str]) -> None:
        adr = root / "08-RFC-ADR" / "ADR-0005-No-Integrated-ITSM.md"
        if not adr.is_file():
            return
        content = adr.read_text(encoding="utf-8").lower()
        if "aucune" not in content and "sans" not in content:
            errors.append("no-itsm ADR does not explicitly exclude integrated ITSM")
