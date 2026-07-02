from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityUser,
)


class TestIdentityDomain:
    def test_user_group_membership_and_effective_identity_are_normalized(self) -> None:
        tenant = TenantId.from_value("default")
        user = IdentityUser.create(
            tenant,
            "Alice.Example@EXAMPLE.COM",
            "  Alice   Example  ",
            "Alice.Example@Example.COM",
            ("viewer",),
        )
        group = IdentityGroup.create(tenant, "IPAM-OPS", "IPAM Operators", ("ipam:operator",))
        membership = GroupMembership.create(tenant, user.username, group.name)
        effective = EffectiveIdentity.from_parts(user, (group.name,), group.role_names())

        assert user.username == "alice.example@example.com"
        assert user.display_name == "Alice Example"
        assert user.email == "alice.example@example.com"
        assert group.name == "ipam-ops"
        assert membership.group_name == "ipam-ops"
        assert effective.role_names() == ("ipam:operator", "viewer")
        assert effective.as_dict()["groups"] == ["ipam-ops"]

    def test_identity_restore_and_empty_identity_validate_inputs(self) -> None:
        tenant = TenantId.from_value("default")
        created_at = datetime.now(UTC)
        user = IdentityUser.restore(
            EntityId.from_value("00000000-0000-4000-8000-000000000101"),
            tenant,
            "bob",
            "Bob",
            None,
            ("viewer",),
            True,
            created_at,
        )
        group = IdentityGroup.restore(
            EntityId.from_value("00000000-0000-4000-8000-000000000102"),
            tenant,
            "viewers",
            "Viewers",
            ("viewer",),
            True,
            created_at,
        )
        membership = GroupMembership.restore(tenant, "bob", "viewers", created_at)
        empty = EffectiveIdentity.empty(tenant, "unknown-user")

        assert user.as_dict()["active"] is True
        assert group.as_dict()["roles"] == ["viewer"]
        assert membership.as_dict()["username"] == "bob"
        assert empty.as_dict()["effective_roles"] == []
        with pytest.raises(ValidationError):
            IdentityUser.create(tenant, "x", "X", "invalid-email")
        with pytest.raises(ValidationError):
            IdentityGroup.create(tenant, "1bad", "Bad")
