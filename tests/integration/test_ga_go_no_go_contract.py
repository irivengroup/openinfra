from __future__ import annotations

from pathlib import Path

from openinfra.quality.ga_go_no_go import GaGoNoGoPolicy


class TestGaGoNoGoContract:
    def test_policy_and_workflow_are_complete(self) -> None:
        root = Path(__file__).resolve().parents[2]
        policy = GaGoNoGoPolicy.load(root / "docs/release/ga-go-no-go-policy.json")
        assert policy.gate_id == "GATE-07"
        assert policy.epic == "EPIC-1805"
        assert len(policy.required_evidence) == 8
        assert set(policy.required_approval_roles) == {
            "product-owner",
            "engineering-owner",
            "security-owner",
            "operations-owner",
            "support-owner",
        }
        workflow = (root / ".github/workflows/ga-go-no-go.yml").read_text(encoding="utf-8")
        for fragment in (
            "workflow_dispatch:",
            "workflow_call:",
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/download-artifact@v6",
            "actions/upload-artifact@v6",
            "--enforce-go",
            "retention-days: 365",
        ):
            assert fragment in workflow
        assert "pull_request_target:" not in workflow

    def test_release_documents_state_current_no_go_constraints(self) -> None:
        root = Path(__file__).resolve().parents[2]
        runbook = (root / "docs/runbooks/GA_GO_NO_GO.md").read_text(encoding="utf-8")
        traceability = (root / "docs/TRACEABILITY.md").read_text(encoding="utf-8")
        assert "Version cible : `0.34.6`" in runbook
        assert "EPIC-1806" in runbook
        assert "NO-GO" in runbook
        assert "v0.34.6" in traceability
        assert "EPIC-1805" in traceability
