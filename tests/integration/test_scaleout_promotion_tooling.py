from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from scripts.assemble_scaleout_promotion_evidence import ScaleoutPromotionAssembler
from scripts.validate_scaleout_promotion import ScaleoutPromotionProjectValidator

from openinfra.quality.scaleout_promotion import ScaleoutPromotionError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestScaleoutPromotionTooling:
    def test_project_contract_is_complete(self) -> None:
        report = ScaleoutPromotionProjectValidator(PROJECT_ROOT).validate()
        assert report["complete"] is True
        assert report["gate_id"] == "GATE-09"
        assert report["release_id"] == "REL-10"
        assert report["pgbouncer_and_read_routing"] is True
        assert report["cursor_pagination_and_streaming"] is True
        assert report["outbox_and_specialized_workers"] is True
        assert report["modular_virtualized_frontend"] is True
        assert report["observability_and_capacity_contracts"] is True
        assert report["runbooks_present"] is True

    def test_workflow_is_protected_and_aggregates_existing_certifications(self) -> None:
        workflow = (PROJECT_ROOT / ".github/workflows/enterprise-scaleout-promotion.yml").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "workflow_dispatch:",
            "actions: read",
            "environment: enterprise-scaleout-promotion",
            "openinfra-enterprise-scaleout",
            "gh run download",
            "validate_scaleout_promotion.py",
            "assemble_scaleout_promotion_evidence.py",
            "certify_scaleout_promotion.py",
            "--enforce",
            "retention-days: 90",
        ):
            assert fragment in workflow
        assert "pull_request_target:" not in workflow

    def test_policy_and_runbook_target_gate_09_without_new_runtime_mutation(self) -> None:
        policy = (
            PROJECT_ROOT / "docs/release/enterprise-scaleout-promotion-policy.json"
        ).read_text(encoding="utf-8")
        runbook = (PROJECT_ROOT / "docs/runbooks/ENTERPRISE_SCALEOUT_PROMOTION.md").read_text(
            encoding="utf-8"
        )
        assert '"gate_id": "GATE-09"' in policy
        assert '"release_id": "REL-10"' in policy
        assert policy.count('"id":') == 7
        assert "ne modifie aucune infrastructure" in runbook
        assert "SHA-256" in runbook

    def test_ci_and_quality_gate_enforce_gate_09_contracts(self) -> None:
        ci = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        quality_gate = (PROJECT_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
        assert "GATE-09 Enterprise Scale-out promotion contracts" in ci
        assert "tests/unit/test_scaleout_promotion.py" in ci
        assert "tests/integration/test_scaleout_promotion_tooling.py" in ci
        assert "scripts/validate_scaleout_promotion.py" in quality_gate
        assert '"--enforce"' in quality_gate

    def test_assembler_copies_and_pins_all_seven_reports(self, tmp_path: Path) -> None:
        sources: dict[str, Path] = {}
        for identifier, _ in ScaleoutPromotionAssembler.EVIDENCE:
            path = tmp_path / f"source-{identifier}.json"
            path.write_text(json.dumps({"id": identifier}), encoding="utf-8")
            sources[identifier] = path
        evidence_root = tmp_path / "evidence"
        manifest = ScaleoutPromotionAssembler.assemble(
            candidate_id="openinfra-0.33.4-rc1",
            source_commit="a" * 40,
            sources=sources,
            evidence_root=evidence_root,
        )
        assert manifest["gate_id"] == "GATE-09"
        assert manifest["release_version"] == "0.33.4"
        assert len(manifest["evidence"]) == 7
        for reference in manifest["evidence"]:
            copied = evidence_root / str(reference["path"])
            assert copied.is_file()
            assert reference["sha256"] == hashlib.sha256(copied.read_bytes()).hexdigest()

        with pytest.raises(ScaleoutPromotionError, match="full lowercase SHA-1"):
            ScaleoutPromotionAssembler.assemble(
                candidate_id="candidate",
                source_commit="invalid",
                sources=sources,
                evidence_root=tmp_path / "invalid-commit",
            )
        incomplete = dict(sources)
        incomplete.pop("ga-go-no-go")
        with pytest.raises(ScaleoutPromotionError, match="required evidence is missing"):
            ScaleoutPromotionAssembler.assemble(
                candidate_id="candidate",
                source_commit="b" * 40,
                sources=incomplete,
                evidence_root=tmp_path / "missing-evidence",
            )
