from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.security import (
    ApiTokenCredential,
    AuthenticatedPrincipal,
    Permission,
    SecurityRole,
)


def test_security_domain_validation_and_public_serialization_edges() -> None:
    tenant = TenantId.from_value("default")
    created_at = datetime.now(UTC)
    future = created_at + timedelta(hours=1)
    past = created_at - timedelta(hours=1)

    with pytest.raises(ValidationError):
        SecurityRole.from_value("!")
    with pytest.raises(ValidationError):
        ApiTokenCredential.create(tenant, "ab", "a" * 64, "abcdefgh", ("viewer",))
    with pytest.raises(ValidationError):
        ApiTokenCredential.create(tenant, "subject", "not-a-hash", "abcdefgh", ("viewer",))
    with pytest.raises(ValidationError):
        ApiTokenCredential.create(tenant, "subject", "a" * 64, "short", ("viewer",))
    with pytest.raises(ValidationError):
        ApiTokenCredential.create(tenant, "subject", "a" * 64, "abcdefgh", ())
    with pytest.raises(ValidationError):
        ApiTokenCredential.create(
            tenant, "subject", "a" * 64, "abcdefgh", ("viewer",), expires_at=past
        )
    with pytest.raises(ValidationError):
        ApiTokenCredential.restore(
            EntityId.new(), tenant, "subject", "a" * 64, "abcdefgh", (), True, created_at
        )
    with pytest.raises(ValidationError):
        ApiTokenCredential.restore(
            EntityId.new(),
            tenant,
            "subject",
            "a" * 64,
            "abcdefgh",
            ("viewer",),
            True,
            datetime(2026, 1, 1),
        )
    with pytest.raises(ValidationError):
        ApiTokenCredential.restore(
            EntityId.new(),
            tenant,
            "subject",
            "a" * 64,
            "abcdefgh",
            ("viewer",),
            True,
            created_at,
            revoked_by=" ",
        )
    with pytest.raises(ValidationError):
        ApiTokenCredential.restore(
            EntityId.new(),
            tenant,
            "subject",
            "a" * 64,
            "abcdefgh",
            ("viewer",),
            True,
            created_at,
            use_count=-1,
        )

    credential = ApiTokenCredential.create(
        tenant, "Subject.User", "A" * 64, "ABCdef12", ("viewer",), expires_at=future
    )
    assert credential.subject == "subject.user"
    assert credential.token_hash == "a" * 64
    assert credential.role_names() == ("viewer",)
    assert credential.is_expired(future + timedelta(seconds=1)) is True
    assert credential.is_usable(future + timedelta(seconds=1)) is False
    revoked = credential.revoked("security-admin", at=future)
    public = revoked.as_public_dict()
    assert revoked.is_revoked() is True
    assert public["token_prefix"] == "ABCdef12"
    assert public["revoked_by"] == "security-admin"
    assert "token_hash" not in public

    principal = AuthenticatedPrincipal(
        tenant, "subject", (SecurityRole.from_value("viewer"),), frozenset({Permission.SCHEMA_READ})
    )
    principal.require(Permission.SCHEMA_READ)
    with pytest.raises(ValidationError):
        principal.require(Permission.IPAM_ALLOCATE)
    assert principal.as_dict()["permissions"] == [Permission.SCHEMA_READ.value]
