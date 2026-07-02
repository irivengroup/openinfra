from __future__ import annotations

import pytest

from openinfra.domain.access_policy import AccessPolicyEffect, AccessPolicyRule, AccessRequestContext
from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.security import AuthenticatedPrincipal, Permission, SecurityRole


class TestAccessPolicyDomain:
    def test_rule_normalizes_selectors_and_matches_context(self) -> None:
        tenant = TenantId.from_value("default")
        rule = AccessPolicyRule.create(
            tenant_id=tenant,
            name="Ipam-Par1-Prod",
            permission=Permission.IPAM_ALLOCATE,
            effect="allow",
            subjects=("Api-Client-01",),
            roles=("ipam:operator",),
            site_codes=("par1",),
            environments=("PROD",),
        )
        principal = AuthenticatedPrincipal(
            tenant_id=tenant,
            subject="api-client-01",
            roles=(SecurityRole.from_value("ipam:operator"),),
            permissions=frozenset((Permission.IPAM_ALLOCATE,)),
        )

        assert rule.name == "ipam-par1-prod"
        assert rule.effect == AccessPolicyEffect.ALLOW
        assert rule.site_codes == ("PAR1",)
        assert rule.environments == ("prod",)
        assert rule.applies_to_principal(principal) is True
        assert rule.matches_context(
            AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, "PAR1", "prod")
        ) is True
        assert rule.matches_context(
            AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, "LON1", "prod")
        ) is False

    def test_wildcards_and_validation_are_explicit(self) -> None:
        tenant = TenantId.from_value("default")
        rule = AccessPolicyRule.create(
            tenant_id=tenant,
            name="global-ipam",
            permission=Permission.IPAM_ALLOCATE,
            effect="deny",
            subjects=("*",),
            site_codes=("*",),
            environments=("*",),
        )
        restored = AccessPolicyRule.restore(
            id=rule.id,
            tenant_id=rule.tenant_id,
            name=rule.name,
            permission=rule.permission.value,
            effect=rule.effect.value,
            subjects=rule.subjects,
            roles=rule.role_names(),
            site_codes=rule.site_codes,
            environments=rule.environments,
            active=rule.active,
            created_at=rule.created_at.replace(tzinfo=None),
        )

        assert restored.as_dict()["subjects"] == ["*"]
        assert restored.deactivated().active is False
        with pytest.raises(ValidationError):
            AccessRequestContext.create(tenant, Permission.IPAM_ALLOCATE, "PAR 1", "prod")
        with pytest.raises(ValidationError):
            AccessPolicyRule.create(
                tenant,
                "bad rule name",
                Permission.IPAM_ALLOCATE,
                "allow",
            )
