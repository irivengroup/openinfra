from __future__ import annotations

from pathlib import Path

import pytest

from openinfra.application.authentication_services import (
    AuthProviderPolicyCommand,
    ExternalAuthenticationService,
    ExternalLoginCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import AuthenticateTokenCommand
from openinfra.domain.authentication import (
    ExternalAuthenticatedIdentity,
    ExternalDirectoryConfig,
    ExternalGroupRoleMapping,
)
from openinfra.domain.common import AccessDeniedError, ValidationError
from openinfra.domain.security import Permission
from openinfra.infrastructure.external_identity import StaticExternalDirectoryAuthenticator


def _directory_config() -> ExternalDirectoryConfig:
    return ExternalDirectoryConfig.create(
        mode="ldap",
        url="ldaps://ldap.example.net",
        base_dn="dc=example,dc=net",
        user_filter="(uid={username})",
        group_filter="(member={user_dn})",
        bind_dn_ref="env:OPENINFRA_LDAP_BIND_DN",
        bind_password_ref="env:OPENINFRA_LDAP_BIND_PASSWORD",  # noqa: S106
    )


def _identity() -> ExternalAuthenticatedIdentity:
    return ExternalAuthenticatedIdentity.create(
        provider="ldap",
        subject="alice",
        display_name="Alice Infra",
        email="alice@example.net",
        external_groups=("cn=ipam-operators,ou=groups,dc=example,dc=net",),
        user_dn="uid=alice,ou=people,dc=example,dc=net",
    )


class TestExternalAuthenticationServices:
    def test_policy_blocks_ldap_ipa_for_lite_and_accepts_pro_enterprise(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        config = _directory_config()

        with pytest.raises(ValidationError):
            app.auth_provider_policy_service.validate(
                AuthProviderPolicyCommand("lite", "ldap", config)
            )
        payload = app.auth_provider_policy_service.validate(
            AuthProviderPolicyCommand("pro", "ldap", config)
        )

        assert payload["external_directory_enabled"] is True
        assert payload["rbac_authority"] == "openinfra"
        assert payload["directory"]["has_bind_password_ref"] is True

    def test_external_login_maps_directory_group_to_openinfra_rbac_and_token(
        self,
        tmp_path: Path,
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json", edition="pro")
        service = ExternalAuthenticationService(
            StaticExternalDirectoryAuthenticator(_identity()),
            app.identity_service,
            app.security_service,
            app.audit_repository,
            app.transaction_manager,
            app.auth_provider_policy_service,
        )
        mapping = ExternalGroupRoleMapping.create(
            tenant_id="default",
            provider="ldap",
            external_group="cn=ipam-operators,ou=groups,dc=example,dc=net",
            roles=("ipam:operator", "viewer"),
        )

        result = service.login(
            ExternalLoginCommand(
                tenant_id="default",
                edition="pro",
                actor="pytest",
                username="alice",
                password="valid-login",  # noqa: S106
                directory_config=_directory_config(),
                mappings=(mapping,),
                ttl_seconds=600,
            )
        )
        principal = app.security_service.authenticate_token(
            AuthenticateTokenCommand("default", result.token, Permission.IPAM_ALLOCATE)
        )
        effective = app.identity_repository.effective_identity_for_subject(
            principal.tenant_id,
            "alice",
        )

        assert result.as_dict()["provider"] == "ldap"
        assert result.provider == "ldap"
        assert result.roles == ("ipam:operator", "viewer")
        assert principal.subject == "alice"
        assert "ipam:operator" in [role.name for role in principal.roles]
        assert effective.groups == (mapping.internal_group_name,)

    def test_external_login_rejects_unmapped_groups(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(
            tmp_path / "state.json", edition="enterprise"
        )
        service = ExternalAuthenticationService(
            StaticExternalDirectoryAuthenticator(_identity()),
            app.identity_service,
            app.security_service,
            app.audit_repository,
            app.transaction_manager,
            app.auth_provider_policy_service,
        )

        with pytest.raises(AccessDeniedError):
            service.login(
                ExternalLoginCommand(
                    tenant_id="default",
                    edition="enterprise",
                    actor="pytest",
                    username="alice",
                    password="valid-login",  # noqa: S106
                    directory_config=_directory_config(),
                    mappings=(),
                )
            )

    def test_policy_standard_and_mismatch_edges(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        assert (
            app.auth_provider_policy_service.validate(
                AuthProviderPolicyCommand("enterprise", "standard", None)
            )["external_directory_enabled"]
            is False
        )
        with pytest.raises(ValidationError):
            app.auth_provider_policy_service.validate(
                AuthProviderPolicyCommand("enterprise", "standard", _directory_config())
            )
        with pytest.raises(ValidationError):
            app.auth_provider_policy_service.validate(
                AuthProviderPolicyCommand("enterprise", "ldap", None)
            )
        with pytest.raises(ValidationError):
            app.auth_provider_policy_service.validate(
                AuthProviderPolicyCommand("enterprise", "ipa", _directory_config())
            )
