from __future__ import annotations

import json
from pathlib import Path

from openinfra import __version__
from openinfra.quality.advanced_identity_oracle_promotion import Gate11PromotionPolicy


class TestGate11QualificationContract:
    def test_release_assets_workflow_and_packaging_are_complete(self) -> None:
        root = Path(__file__).parents[2]
        policy_path = root / "docs/release/advanced-identity-oracle-promotion-policy.json"
        policy = Gate11PromotionPolicy.load(policy_path)
        assert len(policy.required_evidence) == 5
        assert set(Gate11PromotionPolicy.EXPECTED_EVIDENCE) == {
            "gate11-contracts",
            "gate11-oracle-live",
            "gate11-saml-live",
            "gate11-team-sync-live",
            "gate11-systemd-live",
        }

        workflow = (root / ".github/workflows/advanced-identity-oracle.yml").read_text(
            encoding="utf-8"
        )
        for fragment in (
            "actions/checkout@v6",
            "actions/setup-python@v6",
            "actions/upload-artifact@v6",
            "openinfra-gate11 contracts",
            "openinfra-gate11 assemble",
            "openinfra-gate11 evaluate",
            "runs-on: [self-hosted, linux, openinfra-gate11]",
            "OPENINFRA_GATE11_SAML_REQUEST_JSON_B64",
            "retention-days: 365",
        ):
            assert fragment in workflow
        assert "pull_request_target:" not in workflow

        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        assert (
            "openinfra-gate11 = "
            '"openinfra.quality.advanced_identity_oracle_promotion:'
            'Gate11QualificationCli.main"'
        ) in pyproject
        assert 'version = "0.34.3"' in pyproject
        assert __version__ == "0.34.3"

    def test_policy_is_closed_and_uses_bounded_freshness(self) -> None:
        root = Path(__file__).parents[2]
        payload = json.loads(
            (root / "docs/release/advanced-identity-oracle-promotion-policy.json").read_text(
                encoding="utf-8"
            )
        )
        assert payload["gate_id"] == "GATE-11"
        assert payload["release_id"] == "REL-12"
        assert len(payload["required_evidence"]) == 5
        assert all(1 <= item["max_age_hours"] <= 168 for item in payload["required_evidence"])
        assert len({item["id"] for item in payload["required_evidence"]}) == 5

    def test_runbook_documents_live_qualification_without_secret_arguments(self) -> None:
        root = Path(__file__).parents[2]
        runbook = (root / "docs/runbooks/ADVANCED_IDENTITY_ORACLE_SYSTEMD.md").read_text(
            encoding="utf-8"
        )
        assert "Qualification externe GATE-11" in runbook
        assert "openinfra-gate11 oracle" in runbook
        assert "openinfra-gate11 saml" in runbook
        assert "openinfra-gate11 team-sync" in runbook
        assert "openinfra-gate11 systemd" in runbook
        assert "openinfra-gate11 assemble" in runbook
        assert "openinfra-gate11 evaluate" in runbook
        assert "Le jeton SAML complet n'est jamais écrit" in runbook
