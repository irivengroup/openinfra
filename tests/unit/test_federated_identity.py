from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.federated_identity import (
    FederatedIdentity,
    HttpsOrigin,
    SamlProviderConfig,
    TeamSyncGroup,
    TeamSyncSnapshot,
    TeamSyncSourceConfig,
    TeamSyncUser,
)


class TestFederatedIdentityDomain:
    def test_saml_configuration_is_strict_and_secret_safe(self) -> None:
        config = SamlProviderConfig.create(
            idp_entity_id="https://idp.example.net/metadata",
            idp_sso_url="https://idp.example.net/saml/sso",
            idp_x509_cert_ref="file:///etc/openinfra/secrets/idp.crt",
            sp_entity_id="https://openinfra.example.net/saml/metadata",
            sp_acs_url="https://openinfra.example.net/api/v1/auth/saml/acs",
        )

        safe = config.as_safe_dict()

        assert config.want_assertions_signed is True
        assert safe["has_idp_x509_cert_ref"] is True
        assert "idp_x509_cert_ref" not in safe
        with pytest.raises(ValidationError, match="must use https"):
            SamlProviderConfig.create(
                idp_entity_id="urn:idp",
                idp_sso_url="http://idp.example.net/sso",
                idp_x509_cert_ref="file:///idp.crt",
                sp_entity_id="urn:openinfra",
                sp_acs_url="https://openinfra.example.net/acs",
            )

    def test_federated_identity_normalizes_groups(self) -> None:
        identity = FederatedIdentity.create(
            provider="saml",
            subject=" alice ",
            display_name=" Alice Example ",
            email="alice@example.net",
            external_groups=("Platform Admins", "Platform   Admins", "Operators"),
            session_index=" session-1 ",
        )

        assert identity.subject == "alice"
        assert identity.external_groups == ("Operators", "Platform Admins")
        assert identity.session_index == "session-1"

    def test_team_sync_snapshot_is_deterministic_and_rejects_unknown_members(self) -> None:
        users = (
            TeamSyncUser.create("bob", "Bob"),
            TeamSyncUser.create("alice", "Alice", "alice@example.net"),
        )
        group = TeamSyncGroup.create(
            "sync-ldap-operators",
            "Operators",
            ("operator",),
            ("bob", "alice"),
        )
        captured_at = datetime(2026, 7, 17, 10, 0, tzinfo=UTC)

        first = TeamSyncSnapshot.create(
            tenant_id="default",
            source_id="ldap-main",
            provider="ldap",
            users=users,
            groups=(group,),
            captured_at=captured_at,
        )
        second = TeamSyncSnapshot.create(
            tenant_id="default",
            source_id="ldap-main",
            provider="ldap",
            users=tuple(reversed(users)),
            groups=(group,),
            captured_at=captured_at,
        )

        assert first.fingerprint == second.fingerprint
        assert tuple(user.subject for user in first.users) == ("alice", "bob")
        with pytest.raises(ValidationError, match="members must exist"):
            TeamSyncSnapshot.create(
                tenant_id="default",
                source_id="ldap-main",
                provider="ldap",
                users=(TeamSyncUser.create("alice", "Alice"),),
                groups=(
                    TeamSyncGroup.create(
                        "sync-ldap-operators",
                        "Operators",
                        ("operator",),
                        ("missing",),
                    ),
                ),
            )

    def test_team_sync_source_enforces_provider_contracts_and_https(self) -> None:
        config = TeamSyncSourceConfig.create(
            tenant_id="default",
            source_id="okta-main",
            provider="okta",
            endpoint="https://tenant.okta.com",
            token_ref="file:///etc/openinfra/secrets/okta-token",  # noqa: S106
            group_role_mappings=(("Platform Admins", ("admin",)),),
        )

        assert config.roles_for_external_group(" platform admins ") == ("admin",)
        assert HttpsOrigin.origin(config.endpoint or "") == "https://tenant.okta.com"
        with pytest.raises(ValidationError, match="requires endpoint and token_ref"):
            TeamSyncSourceConfig.create(
                tenant_id="default",
                source_id="oauth-main",
                provider="oauth",
            )
        with pytest.raises(ValidationError, match="must use https"):
            TeamSyncSourceConfig.create(
                tenant_id="default",
                source_id="oauth-main",
                provider="oauth",
                endpoint="http://identity.example.net/sync",
                token_ref="env:OAUTH_TOKEN",  # noqa: S106
            )
