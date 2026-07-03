from __future__ import annotations

from datetime import datetime

import pytest

from openinfra.domain.access_policy import AccessPolicyRule, AccessRequestContext
from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.security import AuthenticatedPrincipal, Permission, SecurityRole


def test_access_policy_validation_matching_and_serialization_edges() -> None:
    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError):
        AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, environment="bad env!")
    assert AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE).attributes() == {"site_code": None, "environment": None}
    assert AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, site_code="par1", environment="PROD").environment == "prod"

    with pytest.raises(ValidationError):
        AccessPolicyRule.create(tenant, "!", Permission.IPAM_ALLOCATE, "allow")
    with pytest.raises(ValidationError):
        AccessPolicyRule.create(tenant, "rule-a", Permission.IPAM_ALLOCATE, "allow", subjects=("bad subject!",))
    with pytest.raises(ValidationError):
        AccessPolicyRule.create(tenant, "rule-a", Permission.IPAM_ALLOCATE, "allow", environments=("bad env!",))

    default_rule = AccessPolicyRule.create(tenant, "default-subject", Permission.IPAM_ALLOCATE, "allow", subjects=(), roles=())
    assert default_rule.subjects == ("*",)

    restored = AccessPolicyRule.restore(
        EntityId.new(), tenant, "role-rule", Permission.IPAM_ALLOCATE.value, "deny", (), ("ipam:operator",), ("*",), ("*",), True, datetime(2026, 1, 1)
    )
    principal = AuthenticatedPrincipal(
        tenant, "operator", (SecurityRole.from_value("ipam:operator"),), frozenset({Permission.IPAM_ALLOCATE})
    )
    assert restored.applies_to_principal(principal) is True
    assert restored.matches_context(AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, site_code="PAR1", environment="prod")) is True
    assert restored.matches_context(AccessRequestContext.create(tenant, Permission.SCHEMA_READ, site_code="PAR1", environment="prod")) is False
    inactive = restored.deactivated()
    assert inactive.applies_to_principal(principal) is False
    assert inactive.as_dict()["active"] is False

    site_rule = AccessPolicyRule.create(tenant, "site-only", Permission.IPAM_ALLOCATE, "allow", site_codes=("PAR1",), environments=("prod",))
    assert site_rule.matches_context(AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, site_code=None, environment="prod")) is False
    assert site_rule.matches_context(AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, site_code="PAR1", environment=None)) is False
