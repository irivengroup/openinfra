from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.identity_services import (
    AddUserToGroupCommand,
    CreateGroupCommand,
    CreateUserCommand,
    EffectiveIdentityCommand,
    GrantGroupRoleCommand,
    GrantUserRoleCommand,
)
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.security_services import (
    AuthenticateTokenCommand,
    BootstrapTokenCommand,
)
from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.domain.security import Permission


class TestIdentityServices:
    def test_user_group_roles_are_merged_with_token_roles(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "a" * 40
        alice_token = "b" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "security-admin", ("admin",), admin_token)
        )
        app.identity_service.create_user(
            CreateUserCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                username="alice",
                display_name="Alice Infra",
                email="alice@example.com",
                roles=("viewer",),
            )
        )
        app.identity_service.create_group(
            CreateGroupCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=admin_token,
                name="ipam-ops",
                display_name="IPAM Operators",
                roles=("ipam:operator",),
            )
        )
        app.identity_service.add_user_to_group(
            AddUserToGroupCommand("default", "pytest", admin_token, "alice", "ipam-ops")
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "alice", ("viewer",), alice_token)
        )

        principal = app.security_service.authenticate_token(
            AuthenticateTokenCommand("default", alice_token, Permission.IPAM_ALLOCATE)
        )
        allocation = app.ipam_service.allocate(
            AllocateIpCommand(
                "default",
                principal.subject,
                "default",
                "10.7.0.0/30",
                "srv",
                "iam-1",
            )
        )
        effective = app.identity_service.effective_identity(
            EffectiveIdentityCommand("default", "pytest", admin_token, "alice")
        )

        assert principal.subject == "alice"
        assert "ipam:operator" in [role.name for role in principal.roles]
        assert allocation.as_dict()["address"] == "10.7.0.1"
        assert effective.as_dict()["groups"] == ["ipam-ops"]

    def test_identity_role_grants_are_idempotent_and_admin_protected(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "c" * 40
        viewer_token = "d" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "security-admin", ("admin",), admin_token)
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "viewer-client", ("viewer",), viewer_token)
        )
        app.identity_service.create_user(
            CreateUserCommand("default", "pytest", admin_token, "bob", "Bob", None, ())
        )
        app.identity_service.create_group(
            CreateGroupCommand("default", "pytest", admin_token, "dcim-ops", "DCIM Operators", ())
        )

        first_user_grant = app.identity_service.grant_user_role(
            GrantUserRoleCommand("default", "pytest", admin_token, "bob", "dcim:operator")
        )
        second_user_grant = app.identity_service.grant_user_role(
            GrantUserRoleCommand("default", "pytest", admin_token, "bob", "dcim:operator")
        )
        group_grant = app.identity_service.grant_group_role(
            GrantGroupRoleCommand("default", "pytest", admin_token, "dcim-ops", "viewer")
        )

        assert first_user_grant["changed"] is True
        assert second_user_grant["changed"] is False
        assert group_grant["changed"] is True
        with pytest.raises(AccessDeniedError):
            app.identity_service.create_user(
                CreateUserCommand("default", "pytest", viewer_token, "eve", "Eve", None, ())
            )
        with pytest.raises(ValidationError):
            app.identity_service.grant_user_role(
                GrantUserRoleCommand("default", "pytest", admin_token, "missing", "viewer")
            )
    def test_group_membership_requires_existing_user_and_group(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "m" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "security-admin", ("admin",), admin_token)
        )
        app.identity_service.create_user(
            CreateUserCommand("default", "pytest", admin_token, "member", "Member", None, ())
        )

        with pytest.raises(ValidationError):
            app.identity_service.add_user_to_group(
                AddUserToGroupCommand("default", "pytest", admin_token, "member", "missing-group")
            )
        with pytest.raises(ValidationError):
            app.identity_service.add_user_to_group(
                AddUserToGroupCommand("default", "pytest", admin_token, "missing", "missing-group")
            )

