from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from openinfra import __version__


class Gate14QualificationError(RuntimeError):
    """Raised when contractual-completeness qualification is invalid."""


class ProofLevel(StrEnum):
    AUTOMATED = "automated"
    PARTIAL = "partial"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class ContractProof:
    test_id: str
    level: ProofLevel
    pytest_selectors: tuple[str, ...]
    evidence_files: tuple[str, ...]
    qualification_scope: str
    rationale: str


@dataclass(frozen=True, slots=True)
class Gate14Metrics:
    contractual_tests: int
    automated_proofs: int
    partial_proofs: int
    external_proofs: int
    pytest_selectors: int
    evidence_files: int
    missing_proofs: int
    unclassified_n1_requirements: int

    def as_dict(self) -> dict[str, int]:
        return {
            "contractual_tests": self.contractual_tests,
            "automated_proofs": self.automated_proofs,
            "partial_proofs": self.partial_proofs,
            "external_proofs": self.external_proofs,
            "pytest_selectors": self.pytest_selectors,
            "evidence_files": self.evidence_files,
            "missing_proofs": self.missing_proofs,
            "unclassified_n1_requirements": self.unclassified_n1_requirements,
        }


@dataclass(frozen=True, slots=True)
class Gate14Control:
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
class Gate14Report:
    schema_version: int
    gate_id: str
    release_version: str
    candidate_id: str
    source_commit: str
    generated_at: datetime
    metrics: Gate14Metrics
    controls: tuple[Gate14Control, ...]

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
            "metrics": self.metrics.as_dict(),
            "controls": [control.as_dict() for control in self.controls],
        }


@dataclass(frozen=True, slots=True)
class Gate14Policy:
    schema_version: int
    gate_id: str
    release_id: str
    required_controls: tuple[str, ...]
    expected_metrics: Gate14Metrics

    EXPECTED_CONTROLS = (
        "CDC-TRACEABILITY",
        "ROADMAP-ALIGNMENT",
        "PROOF-REGISTRY",
        "PYTEST-AUTOMATION",
        "EVIDENCE-CLASSIFICATION",
        "REPOSITORY-HYGIENE",
    )

    @classmethod
    def load(cls, path: Path) -> Gate14Policy:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Gate14QualificationError(f"policy is unreadable: {path}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise Gate14QualificationError("unsupported GATE-14 policy schema")
        if payload.get("gate_id") != "GATE-14" or payload.get("release_id") != "REL-15":
            raise Gate14QualificationError("policy must target GATE-14 / REL-15")
        controls = payload.get("required_controls")
        if not isinstance(controls, list) or not all(isinstance(item, str) for item in controls):
            raise Gate14QualificationError("required_controls must be a string list")
        normalized_controls = tuple(controls)
        if normalized_controls != cls.EXPECTED_CONTROLS:
            raise Gate14QualificationError(
                "required_controls are incomplete or incorrectly ordered"
            )
        metrics = payload.get("expected_metrics")
        if not isinstance(metrics, dict):
            raise Gate14QualificationError("expected_metrics must be an object")
        expected_names = {
            "contractual_tests",
            "automated_proofs",
            "partial_proofs",
            "external_proofs",
            "pytest_selectors",
            "evidence_files",
            "missing_proofs",
            "unclassified_n1_requirements",
        }
        if set(metrics) != expected_names or not all(
            isinstance(value, int) and value >= 0 for value in metrics.values()
        ):
            raise Gate14QualificationError("expected_metrics is invalid")
        expected = Gate14Metrics(**{name: metrics[name] for name in expected_names})
        return cls(1, "GATE-14", "REL-15", normalized_controls, expected)


class ContractProofRegistry:
    FIELD_NAMES = (
        "test_id",
        "proof_level",
        "pytest_selectors",
        "evidence_files",
        "qualification_scope",
        "rationale",
    )

    @classmethod
    def load(cls, path: Path) -> tuple[ContractProof, ...]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if tuple(reader.fieldnames or ()) != cls.FIELD_NAMES:
                    raise Gate14QualificationError("proof registry columns are invalid")
                raw_rows = list(reader)
        except OSError as exc:
            raise Gate14QualificationError(f"proof registry is unreadable: {path}") from exc
        proofs: list[ContractProof] = []
        for line_number, row in enumerate(raw_rows, start=2):
            test_id = row["test_id"].strip()
            if not test_id:
                raise Gate14QualificationError(
                    f"proof registry line {line_number} has an empty test id"
                )
            try:
                level = ProofLevel(row["proof_level"].strip())
            except ValueError as exc:
                raise Gate14QualificationError(
                    f"proof registry line {line_number} has an invalid proof level"
                ) from exc
            selectors = cls._split(row["pytest_selectors"])
            evidence = cls._split(row["evidence_files"])
            scope = row["qualification_scope"].strip()
            rationale = row["rationale"].strip()
            if not rationale:
                raise Gate14QualificationError(
                    f"proof registry line {line_number} has no rationale"
                )
            if level is ProofLevel.AUTOMATED and not selectors:
                raise Gate14QualificationError(f"automated proof {test_id} has no pytest selector")
            if level is not ProofLevel.AUTOMATED and selectors:
                raise Gate14QualificationError(
                    f"non-automated proof {test_id} declares pytest selectors"
                )
            if not evidence:
                raise Gate14QualificationError(f"proof {test_id} has no evidence file")
            if level is ProofLevel.EXTERNAL and not scope:
                raise Gate14QualificationError(
                    f"external proof {test_id} has no qualification scope"
                )
            if level is not ProofLevel.EXTERNAL and scope:
                raise Gate14QualificationError(
                    f"non-external proof {test_id} declares an external scope"
                )
            proofs.append(ContractProof(test_id, level, selectors, evidence, scope, rationale))
        identifiers = [proof.test_id for proof in proofs]
        duplicates = sorted(
            identifier for identifier, count in Counter(identifiers).items() if count > 1
        )
        if duplicates:
            raise Gate14QualificationError(
                "proof registry contains duplicate test ids: " + ", ".join(duplicates[:10])
            )
        return tuple(proofs)

    @staticmethod
    def _split(value: str) -> tuple[str, ...]:
        return tuple(part.strip() for part in value.split(";") if part.strip())


class PytestSelectorResolver:
    @classmethod
    def validate(cls, project_root: Path, selectors: tuple[str, ...]) -> tuple[str, ...]:
        failures: list[str] = []
        for selector in selectors:
            failure = cls._validate_selector(project_root, selector)
            if failure is not None:
                failures.append(failure)
        return tuple(failures)

    @classmethod
    def _validate_selector(cls, project_root: Path, selector: str) -> str | None:
        parts = selector.split("::")
        if len(parts) not in {2, 3}:
            return f"invalid pytest selector: {selector}"
        relative = Path(parts[0])
        if relative.is_absolute() or ".." in relative.parts:
            return f"unsafe pytest selector path: {selector}"
        path = project_root / relative
        if not path.is_file() or path.suffix != ".py":
            return f"pytest selector file missing: {selector}"
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            return f"pytest selector source is invalid: {selector}: {exc}"
        function_name = re.sub(r"\[.*\]$", "", parts[-1])
        if len(parts) == 2:
            candidates = {
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if function_name not in candidates:
                return f"pytest function is missing: {selector}"
            return None
        class_name = parts[1]
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                methods = {
                    child.name
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                if function_name in methods:
                    return None
                return f"pytest method is missing: {selector}"
        return f"pytest class is missing: {selector}"


class RepositoryHygieneScanner:
    SCAN_ROOTS = (
        "src/openinfra",
        "scripts",
        "installers",
        "web/src",
        "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5",
    )
    SCAN_FILES = (
        "README.md",
        "CHANGELOG.md",
        "VALIDATION-REPORT.md",
        "pyproject.toml",
        "Dockerfile",
        "compose.yaml",
    )
    RULE_DEFINITION_FILES = frozenset(
        {
            "src/openinfra/quality/contract_completeness_promotion.py",
            "scripts/quality_gate.py",
            "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_docs.py",
            (
                "docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_runtime_licensing.py"
            ),
            "docs/specifications/OpenInfra-Roadmap-Developpement-v2.5/scripts/validate_roadmap.py",
        }
    )
    OBSOLETE_FILES = (
        "src/openinfra/application/it_resources_management_services.py",
        "src/openinfra/application/it_resources_management_quality_services.py",
        "src/openinfra/application/ressources_inventory_quality_services.py",
        "migrations",
        "docs/specifications/OpenInfra-Roadmap-Developpement-v2.0",
    )
    ALLOWED_SUFFIXES = frozenset(
        {
            ".cfg",
            ".css",
            ".graphql",
            ".html",
            ".ini",
            ".js",
            ".json",
            ".jsx",
            ".md",
            ".mmd",
            ".puml",
            ".py",
            ".service",
            ".sql",
            ".toml",
            ".yaml",
            ".yml",
        }
    )

    @classmethod
    def scan(cls, project_root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
        root = project_root.resolve()
        failures: list[str] = []
        scanned: list[str] = []
        for relative in cls.OBSOLETE_FILES:
            if (root / relative).exists():
                failures.append(f"obsolete path present: {relative}")
        for relative in cls.SCAN_ROOTS:
            scan_root = root / relative
            if not scan_root.is_dir():
                failures.append(f"scan root missing: {relative}")
                continue
            for path in sorted(scan_root.rglob("*")):
                if path.is_file():
                    cls._scan_file(root, path, failures, scanned)
        for relative in cls.SCAN_FILES:
            path = root / relative
            if not path.is_file():
                failures.append(f"scan file missing: {relative}")
                continue
            cls._scan_file(root, path, failures, scanned)
        return tuple(failures), tuple(dict.fromkeys(scanned))

    @classmethod
    def _scan_file(
        cls,
        root: Path,
        path: Path,
        failures: list[str],
        scanned: list[str],
    ) -> None:
        relative = path.relative_to(root).as_posix()
        if relative in cls.RULE_DEFINITION_FILES:
            scanned.append(relative)
            return
        if path.suffix.lower() not in cls.ALLOWED_SUFFIXES and path.name not in {
            "Dockerfile",
            "VERSION",
        }:
            return
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            failures.append(f"unreadable active source: {relative}")
            return
        scanned.append(relative)
        patterns = list(cls._patterns())
        if relative.startswith(("src/openinfra/", "installers/", "web/src/")):
            patterns.extend(cls._legacy_contract_patterns())
        for pattern_name, pattern in patterns:
            if pattern.search(content):
                failures.append(f"{pattern_name} detected in {relative}")

    @classmethod
    def _patterns(cls) -> tuple[tuple[str, re.Pattern[str]], ...]:
        markers = tuple("".join(parts) for parts in (("TO", "DO"), ("FIX", "ME"), ("HA", "CK")))
        placeholder = "".join(("PLACE", "HOLDER"))
        private_key = "".join(("BEGIN ", "PRIVATE KEY"))
        encrypted_private_key = "".join(("BEGIN ENCRYPTED ", "PRIVATE KEY"))
        return (
            ("completion marker", re.compile(r"\b(?:" + "|".join(markers) + r")\b")),
            ("placeholder marker", re.compile(r"\b" + placeholder + r"\b")),
            ("private key material", re.compile(private_key + "|" + encrypted_private_key)),
        )

    @classmethod
    def _legacy_contract_patterns(cls) -> tuple[tuple[str, re.Pattern[str]], ...]:
        return (
            ("legacy CLI alias", re.compile(r"add_parser\([\"'](?:itrm|ri|sot)[\"']")),
            ("legacy HTTP alias", re.compile(r"/api/v1/(?:itrm|ri|sot)/")),
            (
                "legacy RBAC alias",
                re.compile(r"[\"'](?:itrm|ri|sot):(?:reader|operator|governance-admin)[\"']"),
            ),
        )


class Gate14Qualification:
    POLICY_PATH = Path("docs/release/contract-completeness-promotion-policy.json")
    REGISTRY_PATH = Path("docs/release/contract-proof-registry-v4.12.csv")
    CDC_ROOT = Path("docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0")
    ROADMAP_ROOT = Path("docs/specifications/OpenInfra-Roadmap-Developpement-v2.5")

    def collect(
        self,
        *,
        project_root: Path,
        candidate_id: str,
        source_commit: str,
        now: datetime | None = None,
        enforce: bool = False,
    ) -> Gate14Report:
        root = project_root.resolve()
        if not root.is_dir() or not (root / "pyproject.toml").is_file():
            raise Gate14QualificationError("project root is invalid")
        candidate = candidate_id.strip()
        if not candidate or len(candidate) > 160:
            raise Gate14QualificationError("candidate_id must contain between 1 and 160 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit):
            raise Gate14QualificationError("source_commit must be a 40-character SHA-1")
        policy = Gate14Policy.load(root / self.POLICY_PATH)
        proofs = ContractProofRegistry.load(root / self.REGISTRY_PATH)
        contract_test_ids = self._cdc_test_ids(root)
        metrics = self._metrics(root, proofs, contract_test_ids)
        controls = (
            self._cdc_control(root, contract_test_ids),
            self._roadmap_control(root),
            self._registry_control(proofs, contract_test_ids, policy, metrics),
            self._pytest_control(root, proofs, policy),
            self._classification_control(root, proofs, policy),
            self._hygiene_control(root),
        )
        if tuple(control.identifier for control in controls) != policy.required_controls:
            raise Gate14QualificationError("qualification does not match its policy")
        report = Gate14Report(
            1,
            "GATE-14",
            __version__,
            candidate,
            source_commit.lower(),
            now or datetime.now(UTC),
            metrics,
            controls,
        )
        if enforce and not report.passed:
            failed = ", ".join(control.identifier for control in controls if not control.passed)
            raise Gate14QualificationError(f"GATE-14 failed: {failed}")
        return report

    def write(self, output: Path, report: Gate14Report) -> None:
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

    def _cdc_test_ids(self, root: Path) -> tuple[str, ...]:
        path = root / self.CDC_ROOT / "11-Matrices/Tests.csv"
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise Gate14QualificationError(f"CDC test catalogue is unreadable: {path}") from exc
        identifiers = tuple(row.get("id", "").strip() for row in rows)
        if not identifiers or any(not identifier for identifier in identifiers):
            raise Gate14QualificationError("CDC test catalogue contains empty identifiers")
        if len(set(identifiers)) != len(identifiers):
            raise Gate14QualificationError("CDC test catalogue contains duplicate identifiers")
        return identifiers

    def _metrics(
        self,
        root: Path,
        proofs: tuple[ContractProof, ...],
        contract_test_ids: tuple[str, ...],
    ) -> Gate14Metrics:
        levels = Counter(proof.level for proof in proofs)
        registry_ids = {proof.test_id for proof in proofs}
        evidence_files = {item for proof in proofs for item in proof.evidence_files}
        selectors = tuple(item for proof in proofs for item in proof.pytest_selectors)
        return Gate14Metrics(
            contractual_tests=len(contract_test_ids),
            automated_proofs=levels[ProofLevel.AUTOMATED],
            partial_proofs=levels[ProofLevel.PARTIAL],
            external_proofs=levels[ProofLevel.EXTERNAL],
            pytest_selectors=len(selectors),
            evidence_files=len(evidence_files),
            missing_proofs=len(set(contract_test_ids) - registry_ids),
            unclassified_n1_requirements=len(
                self._unclassified_n1_requirements(root, registry_ids)
            ),
        )

    def _cdc_control(self, root: Path, contract_test_ids: tuple[str, ...]) -> Gate14Control:
        failures: list[str] = []
        evidence = (
            str(self.CDC_ROOT / "VERSION"),
            str(self.CDC_ROOT / "11-Matrices/Exigences.csv"),
            str(self.CDC_ROOT / "11-Matrices/Tests.csv"),
            str(self.CDC_ROOT / "11-Matrices/Traceabilite.csv"),
        )
        if (root / self.CDC_ROOT / "VERSION").read_text(encoding="utf-8").strip() != "4.12.0":
            failures.append("CDC version is not 4.12.0")
        requirements = self._csv_rows(root / self.CDC_ROOT / "11-Matrices/Exigences.csv")
        traces = self._csv_rows(root / self.CDC_ROOT / "11-Matrices/Traceabilite.csv")
        if len(requirements) != 861:
            failures.append(f"expected 861 requirements, got {len(requirements)}")
        if len(contract_test_ids) != 667:
            failures.append(f"expected 667 tests, got {len(contract_test_ids)}")
        if len(traces) != 861:
            failures.append(f"expected 861 traceability rows, got {len(traces)}")
        requirement_ids = {row.get("id", "") for row in requirements}
        if "REQ-00861" not in requirement_ids or "TST-COMP-164" not in contract_test_ids:
            failures.append("contractual completeness requirement or test is missing")
        return Gate14Control(
            "CDC-TRACEABILITY",
            not failures,
            "CDC 4.12.0 is exhaustive" if not failures else "; ".join(failures),
            evidence,
        )

    def _roadmap_control(self, root: Path) -> Gate14Control:
        required: dict[str, tuple[str, ...]] = {
            str(self.ROADMAP_ROOT / "VERSION"): ("2.5.0",),
            str(self.ROADMAP_ROOT / "02-roadmap-phases.csv"): ("P25",),
            str(self.ROADMAP_ROOT / "03-roadmap-releases.csv"): ("REL-15",),
            str(self.ROADMAP_ROOT / "04-roadmap-epics.csv"): ("EPIC-2501",),
            str(self.ROADMAP_ROOT / "07-roadmap-go-nogo.csv"): ("GATE-14",),
            str(self.ROADMAP_ROOT / "14-alignement-cdc-v4.12.0.csv"): ("REQ-00861",),
        }
        return self._source_control("ROADMAP-ALIGNMENT", root, required)

    def _registry_control(
        self,
        proofs: tuple[ContractProof, ...],
        contract_test_ids: tuple[str, ...],
        policy: Gate14Policy,
        metrics: Gate14Metrics,
    ) -> Gate14Control:
        failures: list[str] = []
        registry_ids = tuple(proof.test_id for proof in proofs)
        missing = sorted(set(contract_test_ids) - set(registry_ids))
        extra = sorted(set(registry_ids) - set(contract_test_ids))
        if missing:
            failures.append("missing proofs: " + ", ".join(missing[:10]))
        if extra:
            failures.append("unknown proofs: " + ", ".join(extra[:10]))
        if metrics != policy.expected_metrics:
            failures.append(
                "registry metrics differ from policy: "
                + json.dumps(metrics.as_dict(), sort_keys=True)
            )
        evidence = (str(self.REGISTRY_PATH), str(self.POLICY_PATH))
        return Gate14Control(
            "PROOF-REGISTRY",
            not failures,
            "all CDC tests are classified exactly once" if not failures else "; ".join(failures),
            evidence,
        )

    def _pytest_control(
        self,
        root: Path,
        proofs: tuple[ContractProof, ...],
        policy: Gate14Policy,
    ) -> Gate14Control:
        automated = tuple(proof for proof in proofs if proof.level is ProofLevel.AUTOMATED)
        selectors = tuple(selector for proof in automated for selector in proof.pytest_selectors)
        failures = list(PytestSelectorResolver.validate(root, selectors))
        if len(automated) != policy.expected_metrics.automated_proofs:
            failures.append("automated proof count differs from policy")
        if len(selectors) != policy.expected_metrics.pytest_selectors:
            failures.append("pytest selector count differs from policy")
        if len(set(selectors)) != len(selectors):
            failures.append("pytest selectors must be unique")
        evidence = tuple(dict.fromkeys(selector.split("::", 1)[0] for selector in selectors))
        return Gate14Control(
            "PYTEST-AUTOMATION",
            not failures,
            "all declared pytest nodes resolve" if not failures else "; ".join(failures),
            evidence,
        )

    def _classification_control(
        self,
        root: Path,
        proofs: tuple[ContractProof, ...],
        policy: Gate14Policy,
    ) -> Gate14Control:
        failures: list[str] = []
        evidence_paths = sorted({item for proof in proofs for item in proof.evidence_files})
        for relative in evidence_paths:
            if not self._safe_existing_file(root, relative):
                failures.append(f"evidence file is missing or unsafe: {relative}")
        levels = Counter(proof.level for proof in proofs)
        if levels[ProofLevel.PARTIAL] != policy.expected_metrics.partial_proofs:
            failures.append("partial proof count differs from policy")
        if levels[ProofLevel.EXTERNAL] != policy.expected_metrics.external_proofs:
            failures.append("external proof count differs from policy")
        unclassified = self._unclassified_n1_requirements(root, {proof.test_id for proof in proofs})
        if unclassified:
            failures.append("unclassified N1 requirements: " + ", ".join(unclassified[:10]))
        return Gate14Control(
            "EVIDENCE-CLASSIFICATION",
            not failures,
            (
                "partial and external evidence remain explicitly non-equivalent to full validation"
                if not failures
                else "; ".join(failures)
            ),
            tuple(evidence_paths),
        )

    def _hygiene_control(self, root: Path) -> Gate14Control:
        failures, scanned = RepositoryHygieneScanner.scan(root)
        required = {
            "pyproject.toml": (
                'version = "0.34.7"',
                "openinfra-gate14",
                "CONTRACT_COMPLETENESS_PROMOTION.md",
            ),
            "scripts/smoke_installed_wheel.py": ("Gate14Policy", "openinfra-gate14"),
            "scripts/verify_artifact.py": (
                "contract-completeness-promotion-policy.json",
                "contract-proof-registry-v4.12.csv",
            ),
            ".github/workflows/contract-completeness.yml": (
                "openinfra-gate14",
                "--enforce",
                "scripts/smoke_installed_wheel.py",
            ),
        }
        packaging = self._source_control("REPOSITORY-HYGIENE", root, required)
        combined = list(failures)
        if not packaging.passed:
            combined.append(packaging.detail)
        evidence = tuple(dict.fromkeys((*scanned, *packaging.evidence)))
        return Gate14Control(
            "REPOSITORY-HYGIENE",
            not combined,
            "active sources and packaging are clean" if not combined else "; ".join(combined),
            evidence,
        )

    def _unclassified_n1_requirements(self, root: Path, registry_ids: set[str]) -> tuple[str, ...]:
        traces = self._csv_rows(root / self.CDC_ROOT / "11-Matrices/Traceabilite.csv")
        missing: list[str] = []
        for row in traces:
            if row.get("requirement_priority", "").strip() != "N1":
                continue
            linked = {item.strip() for item in row.get("test_id", "").split(";") if item.strip()}
            if not linked or not linked.issubset(registry_ids):
                missing.append(row.get("requirement_id", ""))
        return tuple(sorted(set(missing)))

    def _source_control(
        self,
        identifier: str,
        root: Path,
        requirements: dict[str, tuple[str, ...]],
    ) -> Gate14Control:
        failures: list[str] = []
        evidence: list[str] = []
        for relative, tokens in requirements.items():
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
            for token in tokens:
                if token not in content:
                    failures.append(f"{relative} missing token {token}")
        return Gate14Control(
            identifier,
            not failures,
            "all required evidence is present" if not failures else "; ".join(failures),
            tuple(evidence),
        )

    def _safe_existing_file(self, root: Path, relative: str) -> bool:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            return False
        path = root / candidate
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            return False
        return resolved.is_file()

    def _csv_rows(self, path: Path) -> list[dict[str, str]]:
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                return list(csv.DictReader(stream))
        except OSError as exc:
            raise Gate14QualificationError(f"CSV is unreadable: {path}") from exc


class Gate14QualificationCli:
    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="openinfra-gate14")
        parser.add_argument("--project-root", type=Path, required=True)
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--enforce", action="store_true")
        args = parser.parse_args(argv)
        try:
            qualification = Gate14Qualification()
            report = qualification.collect(
                project_root=args.project_root,
                candidate_id=args.candidate_id,
                source_commit=args.source_commit,
                enforce=args.enforce,
            )
            qualification.write(args.output, report)
            return 0
        except Gate14QualificationError as exc:
            sys.stderr.write(f"{exc}\n")
            raise SystemExit(2) from exc


if __name__ == "__main__":
    raise SystemExit(Gate14QualificationCli.main())
