from __future__ import annotations

import pytest

from openinfra.domain.authentication import (
    ExternalAuthenticatedIdentity,
    ExternalDirectoryConfig,
    ExternalGroupRoleMapping,
)
from openinfra.domain.common import ValidationError


class TestAuthenticationDomain:
    def test_external_directory_config_requires_ldaps_and_secret_references(self) -> None:
        config = ExternalDirectoryConfig.create(
            mode="ipa",
            url="ldaps://ipa.example.net:636",
            base_dn="dc=example,dc=net",
            user_filter="(uid={username})",
            group_filter="(member={user_dn})",
            bind_dn_ref="env:OPENINFRA_LDAP_BIND_DN",
            bind_password_ref="vault://openinfra/ldap/bind-password",  # noqa: S106
            ca_cert_ref="file:///etc/openinfra/ipa-ca.pem",
        )

        assert config.as_safe_dict()["mode"] == "ipa"
        assert config.as_safe_dict()["has_bind_password_ref"] is True
        assert "bind-password" not in str(config.as_safe_dict())

    def test_external_directory_config_rejects_insecure_or_incomplete_values(self) -> None:
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldap://ipa.example.net:389",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ipa.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid=*)",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ipa.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
                bind_dn_ref="env:BIND_DN",
            )

    def test_external_group_mapping_derives_safe_internal_group_and_roles(self) -> None:
        mapping = ExternalGroupRoleMapping.create(
            tenant_id="default",
            provider="ldap",
            external_group="cn=ipam-admins,ou=groups,dc=example,dc=net",
            roles=("viewer", "ipam:operator", "viewer"),
        )

        assert mapping.internal_group_name.startswith("external-")
        assert mapping.role_names() == ("viewer", "ipam:operator")
        assert mapping.as_dict()["provider"] == "ldap"

    def test_external_authenticated_identity_redacts_user_dn(self) -> None:
        identity = ExternalAuthenticatedIdentity.create(
            provider="ldap",
            subject="Alice",
            display_name="Alice Infra",
            email="alice@example.net",
            external_groups=("cn=ops,ou=groups,dc=example,dc=net",),
            user_dn="uid=alice,ou=people,dc=example,dc=net",
        )

        payload = identity.as_dict()
        assert payload["subject"] == "alice"
        assert "user_dn" not in payload
        assert "user_dn_hash" in payload

    def test_authentication_domain_rejects_edge_cases(self) -> None:
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="standard",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="oauth",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://user:secret@ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ldap.example.net/search",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
                tls_required=False,
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
                cache_ttl_seconds=3,
            )
        with pytest.raises(ValidationError):
            ExternalGroupRoleMapping.create("default", "ldap", "cn=ops,dc=example,dc=net", ())
        with pytest.raises(ValidationError):
            ExternalGroupRoleMapping.create(
                "default", "ldap", "ou=groups,dc=example,dc=net", ("viewer",)
            )
        with pytest.raises(ValidationError):
            ExternalAuthenticatedIdentity.create(
                "ldap",
                "alice",
                "Alice",
                "bad-email",
                ("cn=ops,dc=example,dc=net",),
                "uid=alice,dc=example,dc=net",
            )
        with pytest.raises(ValidationError):
            ExternalAuthenticatedIdentity.create(
                "ldap",
                "alice",
                "Alice",
                None,
                (),
                "uid=alice,dc=example,dc=net",
            )

    def test_authentication_domain_normalizers_reject_low_level_invalid_values(self) -> None:
        with pytest.raises(ValidationError):
            ExternalGroupRoleMapping.create("default", "ldap", "x", ("viewer",))
        with pytest.raises(ValidationError):
            ExternalGroupRoleMapping.create(
                "default", "ldap", "cn=ops,dc=example,\x01dc=net", ("viewer",)
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="uid={username}",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username}\n)",
                group_filter="(member={user_dn})",
            )
        with pytest.raises(ValidationError):
            ExternalDirectoryConfig.create(
                mode="ldap",
                url="ldaps://ldap.example.net",
                base_dn="dc=example,dc=net",
                user_filter="(uid={username})",
                group_filter="(member={user_dn})",
                ca_cert_ref="clear-ca-path",
            )
        with pytest.raises(ValidationError):
            ExternalAuthenticatedIdentity.create(
                "ldap",
                "alice",
                "   ",
                None,
                ("cn=ops,dc=example,dc=net",),
                "uid=alice,dc=example,dc=net",
            )
        identity = ExternalAuthenticatedIdentity.create(
            "ldap",
            "alice",
            "Alice",
            "   ",
            ("cn=ops,dc=example,dc=net",),
            "uid=alice,dc=example,dc=net",
        )
        assert identity.email is None
