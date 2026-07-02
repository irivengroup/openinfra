from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.access_policy_services import (
    CreateAccessPolicyRuleCommand,
    DeactivateAccessPolicyRuleCommand,
    EvaluateAccessPolicyCommand,
    ListAccessPolicyRulesCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.access_policy import AccessRequestContext
from openinfra.domain.common import AccessDeniedError
from openinfra.domain.security import Permission


class TestAccessPolicyServices:
    def test_abac_rule_restricts_context_and_deactivation_restores_default_allow(
        self,
        tmp_path: Path,
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "a" * 40
        worker_token = "w" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "admin-client", ("admin",), admin_token)
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default",
                "pytest",
                "worker-client",
                ("ipam:operator",),
                worker_token,
            )
        )

        rule = app.access_policy_service.create_rule(
            CreateAccessPolicyRuleCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                name="worker-par1-prod",
                permission="ipam.allocate",
                effect="allow",
                subjects=("worker-client",),
                site_codes=("PAR1",),
                environments=("prod",),
            )
        )
        allowed = app.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand(
                "default",
                worker_token,
                "ipam.allocate",
                "PAR1",
                "prod",
            )
        )
        denied = app.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand(
                "default",
                worker_token,
                "ipam.allocate",
                "LON1",
                "prod",
            )
        )
        page = app.access_policy_service.list_rules(
            ListAccessPolicyRulesCommand("default", admin_token, limit=10)
        )
        deactivated = app.access_policy_service.deactivate_rule(
            DeactivateAccessPolicyRuleCommand("default", "pytest", admin_token, rule.name)
        )
        after_deactivate = app.access_policy_service.evaluate(
            EvaluateAccessPolicyCommand(
                "default",
                worker_token,
                "ipam.allocate",
                "LON1",
                "prod",
            )
        )

        assert allowed["allowed"] is True
        assert denied["allowed"] is False
        assert page.as_dict()["items"][0]["name"] == "worker-par1-prod"
        assert deactivated["deactivated"] is True
        assert after_deactivate["allowed"] is True

    def test_deny_rule_takes_precedence_over_allow_rule(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "b" * 40
        worker_token = "c" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "admin-client", ("admin",), admin_token)
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default",
                "pytest",
                "worker-client",
                ("ipam:operator",),
                worker_token,
            )
        )
        app.access_policy_service.create_rule(
            CreateAccessPolicyRuleCommand(
                "default",
                "pytest",
                admin_token,
                "allow-par1",
                "ipam.allocate",
                "allow",
                subjects=("worker-client",),
                site_codes=("PAR1",),
            )
        )
        app.access_policy_service.create_rule(
            CreateAccessPolicyRuleCommand(
                "default",
                "pytest",
                admin_token,
                "deny-prod",
                "ipam.allocate",
                "deny",
                roles=("ipam:operator",),
                site_codes=("PAR1",),
                environments=("prod",),
            )
        )
        principal = app.security_service.inspect_token("default", worker_token)

        with pytest.raises(AccessDeniedError):
            app.access_policy_service.authorize(
                principal,
                AccessRequestContext.create(
                    principal.tenant_id,
                    Permission.IPAM_ALLOCATE,
                    "PAR1",
                    "prod",
                ),
            )
