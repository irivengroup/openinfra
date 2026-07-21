from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from openinfra import __version__


class Gate13QualificationError(RuntimeError):
    """Raised when the RSOT canonical promotion contract is invalid."""


@dataclass(frozen=True, slots=True)
class Gate13Control:
    identifier: str
    passed: bool
    detail: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class Gate13Report:
    schema_version: int
    gate_id: str
    release_version: str
    candidate_id: str
    source_commit: str
    generated_at: datetime
    controls: tuple[Gate13Control, ...]

    @property
    def passed(self) -> bool:
        return all(control.passed for control in self.controls)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "gate_id": self.gate_id,
            "release_version": self.release_version,
            "candidate_id": self.candidate_id,
            "source_commit": self.source_commit,
            "generated_at": self.generated_at.isoformat(),
            "status": "passed" if self.passed else "failed",
            "controls": [control.as_dict() for control in self.controls],
        }


@dataclass(frozen=True, slots=True)
class Gate13Policy:
    schema_version: int
    gate_id: str
    release_id: str
    required_controls: tuple[str, ...]

    EXPECTED_CONTROLS = (
        "RSOT-CLI",
        "RSOT-HTTP",
        "RSOT-RBAC",
        "RSOT-EDITION",
        "RSOT-CODE",
        "RSOT-PACKAGING",
    )

    @classmethod
    def load(cls, path: Path) -> Gate13Policy:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Gate13QualificationError(f"policy is unreadable: {path}") from exc
        if not isinstance(payload, dict):
            raise Gate13QualificationError("policy must be a JSON object")
        if payload.get("schema_version") != 1:
            raise Gate13QualificationError("unsupported policy schema")
        if payload.get("gate_id") != "GATE-13" or payload.get("release_id") != "REL-14":
            raise Gate13QualificationError("policy must target GATE-13 / REL-14")
        controls = payload.get("required_controls")
        if not isinstance(controls, list) or not all(isinstance(item, str) for item in controls):
            raise Gate13QualificationError("required_controls must be a string list")
        normalized = tuple(controls)
        if normalized != cls.EXPECTED_CONTROLS:
            raise Gate13QualificationError(
                "required_controls are incomplete or incorrectly ordered"
            )
        return cls(1, "GATE-13", "REL-14", normalized)


class Gate13Qualification:
    POLICY_PATH = Path("docs/release/rsot-canonical-promotion-policy.json")
    OBSOLETE_MODULES = (
        "src/openinfra/application/it_resources_management_services.py",
        "src/openinfra/application/it_resources_management_quality_services.py",
        "src/openinfra/application/ressources_inventory_quality_services.py",
    )
    FORBIDDEN_PRODUCTION_PATTERNS = (
        re.compile(r"add_parser\([\"'](?:itrm|ri|sot)[\"']"),
        re.compile(r"/api/v1/(?:itrm|ri|sot)/"),
        re.compile(r"[\"'](?:itrm|ri|sot):(?:reader|operator|governance-admin)[\"']"),
        re.compile(r"core_(?:ri|sot|source_of_truth|resources_inventory|ressources_inventory)"),
        re.compile(r"CORE_(?:IT_RESOURCES_MANAGEMENT|RESSOURCES_INVENTORY|SOURCE_OF_TRUTH)"),
        re.compile(r"openinfra\.application\.(?:it_resources_management|ressources_inventory)"),
    )

    def collect(
        self,
        *,
        project_root: Path,
        candidate_id: str,
        source_commit: str,
        now: datetime | None = None,
        enforce: bool = False,
    ) -> Gate13Report:
        root = project_root.resolve()
        if not root.is_dir() or not (root / "pyproject.toml").is_file():
            raise Gate13QualificationError("project root is invalid")
        candidate = candidate_id.strip()
        if not candidate or len(candidate) > 160:
            raise Gate13QualificationError("candidate_id must contain between 1 and 160 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit):
            raise Gate13QualificationError("source_commit must be a 40-character SHA-1")
        policy = Gate13Policy.load(root / self.POLICY_PATH)
        controls = (
            self._cli_control(root),
            self._http_control(root),
            self._rbac_control(root),
            self._edition_control(root),
            self._code_control(root),
            self._packaging_control(root),
        )
        if tuple(control.identifier for control in controls) != policy.required_controls:
            raise Gate13QualificationError("qualification does not match its policy")
        report = Gate13Report(
            1,
            "GATE-13",
            __version__,
            candidate,
            source_commit.lower(),
            now or datetime.now(UTC),
            controls,
        )
        if enforce and not report.passed:
            failed = ", ".join(control.identifier for control in controls if not control.passed)
            raise Gate13QualificationError(f"GATE-13 failed: {failed}")
        return report

    def write(self, output: Path, report: Gate13Report) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(report.as_dict(), stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(output)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _cli_control(self, root: Path) -> Gate13Control:
        return self._source_control(
            "RSOT-CLI",
            root,
            {
                "src/openinfra/interfaces/cli.py": (
                    "def _add_rsot_commands",
                    'command_name="rsot"',
                    "_handle_rsot_upsert_object",
                ),
                "tests/integration/test_rsot_canonical_contract.py": (
                    "test_cli_rejects_removed_rsot_aliases",
                    'LEGACY_RSOT_ALIASES = ("itrm", "ri", "sot")',
                ),
            },
        )

    def _http_control(self, root: Path) -> Gate13Control:
        return self._source_control(
            "RSOT-HTTP",
            root,
            {
                "src/openinfra/interfaces/http_api.py": (
                    'route == "/api/v1/rsot/objects"',
                    '"objects": "/api/v1/rsot/objects"',
                ),
                "tests/integration/test_rsot_canonical_contract.py": (
                    "test_http_api_returns_not_found_for_removed_rsot_aliases",
                    "assert exc_info.value.code == 404",
                ),
            },
        )

    def _rbac_control(self, root: Path) -> Gate13Control:
        return self._source_control(
            "RSOT-RBAC",
            root,
            {
                "src/openinfra/application/security_services.py": (
                    '"rsot:reader"',
                    '"rsot:operator"',
                    '"rsot:governance-admin"',
                ),
                "src/openinfra/domain/security.py": (
                    'RSOT_READ = "rsot.read"',
                    'RSOT_WRITE = "rsot.write"',
                ),
                "tests/integration/test_rsot_canonical_contract.py": (
                    "test_rbac_rejects_removed_rsot_roles",
                ),
            },
        )

    def _edition_control(self, root: Path) -> Gate13Control:
        return self._source_control(
            "RSOT-EDITION",
            root,
            {
                "src/openinfra/domain/editions.py": (
                    'CORE_RSOT = "core_rsot"',
                    "FeatureCapability.CORE_RSOT",
                ),
                "tests/integration/test_rsot_canonical_contract.py": (
                    "test_feature_registry_rejects_removed_rsot_capability_aliases",
                    "CORE_IT_RESOURCES_MANAGEMENT",
                ),
            },
        )

    def _code_control(self, root: Path) -> Gate13Control:
        base = self._source_control(
            "RSOT-CODE",
            root,
            {
                "src/openinfra/application/source_of_truth_services.py": (
                    "class SourceOfTruthService",
                ),
                "src/openinfra/application/rsot_quality_services.py": ("class RsotQualityService",),
                "src/openinfra/application/container.py": (
                    "rsot_service",
                    "rsot_quality_service",
                ),
                (
                    "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/"
                    "validate_rsot_canonical.py"
                ): ("REQ-00860", "TST-RSOT-163"),
            },
        )
        failures = [] if base.passed else [base.detail]
        evidence = list(base.evidence)
        for relative in self.OBSOLETE_MODULES:
            if (root / relative).exists():
                failures.append(f"obsolete module present: {relative}")
        scan_failures, scanned = self._scan_production(root)
        failures.extend(scan_failures)
        evidence.extend(scanned)
        return Gate13Control(
            "RSOT-CODE",
            not failures,
            "canonical RSOT code only" if not failures else "; ".join(failures),
            tuple(dict.fromkeys(evidence)),
        )

    def _packaging_control(self, root: Path) -> Gate13Control:
        return self._source_control(
            "RSOT-PACKAGING",
            root,
            {
                "pyproject.toml": (
                    "openinfra-gate13",
                    "RSOT_CANONICAL_MIGRATION.md",
                ),
                "docs/runbooks/RSOT_CANONICAL_MIGRATION.md": (
                    "openinfra rsot",
                    "/api/v1/rsot/",
                    "rsot:*",
                    "core_rsot",
                ),
                "docs/release/rsot-canonical-promotion-policy.json": (
                    '"gate_id": "GATE-13"',
                    '"release_id": "REL-14"',
                ),
                ".github/workflows/rsot-canonical.yml": (
                    "openinfra-gate13",
                    "validate_rsot_canonical.py",
                    "scripts/smoke_installed_wheel.py",
                ),
                "scripts/verify_artifact.py": (
                    "rsot-canonical-promotion-policy.json",
                    "RSOT_CANONICAL_MIGRATION.md",
                ),
                "scripts/smoke_installed_wheel.py": (
                    "Gate13Policy",
                    "openinfra-gate13",
                ),
            },
        )

    def _scan_production(self, root: Path) -> tuple[list[str], list[str]]:
        failures: list[str] = []
        evidence: list[str] = []
        scan_roots = (
            root / "src/openinfra",
            root / "installers",
            root / "web/src",
        )
        excluded = {Path(__file__).name}
        for scan_root in scan_roots:
            if not scan_root.is_dir():
                failures.append(f"scan root missing: {scan_root.relative_to(root)}")
                continue
            for path in sorted(scan_root.rglob("*")):
                if not path.is_file() or path.name in excluded:
                    continue
                if path.suffix.lower() not in {".py", ".js", ".jsx", ".json", ".toml", ".ini"}:
                    continue
                relative = str(path.relative_to(root))
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError:
                    failures.append(f"unreadable production file: {relative}")
                    continue
                evidence.append(relative)
                for pattern in self.FORBIDDEN_PRODUCTION_PATTERNS:
                    if pattern.search(content):
                        failures.append(f"legacy RSOT alias in {relative}: {pattern.pattern}")
        return failures, evidence

    def _source_control(
        self, identifier: str, root: Path, requirements: dict[str, tuple[str, ...]]
    ) -> Gate13Control:
        failures: list[str] = []
        evidence: list[str] = []
        for relative, required_tokens in requirements.items():
            path = root / relative
            if not path.is_file():
                failures.append(f"{relative} missing")
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                failures.append(f"{relative} unreadable")
                continue
            evidence.append(relative)
            for token in required_tokens:
                if token not in content:
                    failures.append(f"{relative} missing token {token}")
        return Gate13Control(
            identifier,
            not failures,
            "all required evidence is present" if not failures else "; ".join(failures),
            tuple(evidence),
        )


class Gate13QualificationCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-gate13")
        parser.add_argument("--project-root", type=Path, required=True)
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            qualification = Gate13Qualification()
            report = qualification.collect(
                project_root=args.project_root,
                candidate_id=args.candidate_id,
                source_commit=args.source_commit,
                enforce=args.enforce,
            )
            qualification.write(args.output, report)
            return 0
        except Gate13QualificationError as exc:
            sys.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc


if __name__ == "__main__":
    raise SystemExit(Gate13QualificationCli.main())
