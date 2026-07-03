from __future__ import annotations

from datetime import datetime

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.identity import (
    IdentityDisplayName,
    IdentityEmail,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
    IdentityTimestamp,
)
from openinfra.domain.itam import Asset
from openinfra.domain.security import SecurityRole


def test_identity_and_itam_validation_edges() -> None:
    with pytest.raises(ValidationError):
        IdentitySubject.normalize("x")
    with pytest.raises(ValidationError):
        IdentityGroupName.normalize("1bad")
    with pytest.raises(ValidationError):
        IdentityDisplayName.normalize(" ")
    assert IdentityEmail.normalize_optional(None) is None
    assert IdentityEmail.normalize_optional(" ") is None
    with pytest.raises(ValidationError):
        IdentityEmail.normalize_optional("not-email")
    with pytest.raises(ValidationError):
        IdentityTimestamp.normalize(datetime(2026, 1, 1), "created_at")
    roles = IdentityRoleSet.from_names(("viewer", "viewer", "admin"))
    assert IdentityRoleSet.unique_names(roles) == ("admin", "viewer")
    assert IdentityRoleSet.unique_names((SecurityRole.from_value("viewer"),)) == ("viewer",)

    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError):
        Asset.create(tenant, "ASSET-1", "Asset", owner=" ")
    assert Asset.create(tenant, "ASSET-1", "Asset", owner="  Ops   Team ").owner == "Ops Team"
