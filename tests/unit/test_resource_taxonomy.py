from __future__ import annotations

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.resource_taxonomy import ResourceTaxonomy


class TestResourceTaxonomy:
    def test_catalog_serialization_and_lookup_contracts(self) -> None:
        catalog = ResourceTaxonomy.as_dict()

        assert catalog["version"] == "2026.07"
        assert "server" in ResourceTaxonomy.category_values()
        assert "physical-server" in ResourceTaxonomy.all_type_values()
        assert ResourceTaxonomy.type_values_for_category(" Network_Device ")[0] == "switch"
        assert ResourceTaxonomy.default_type_for_category("server") == "physical-server"
        assert catalog["legacy_kind_aliases"]["virtual-machine"] == {
            "resource_category": "server",
            "resource_type": "virtual-machine",
        }
        assert catalog["categories"][0]["default_type"] == "physical-server"
        assert catalog["categories"][0]["types"][0] == {
            "value": "physical-server",
            "label": "Physical server",
        }

    def test_classification_accepts_legacy_kind_category_type_and_attributes(self) -> None:
        assert ResourceTaxonomy.classify(
            kind="virtual-machine",
            resource_category=None,
            resource_type=None,
        ).as_dict() == {"resource_category": "server", "resource_type": "virtual-machine"}
        assert ResourceTaxonomy.classify(
            kind="network-device",
            resource_category=None,
            resource_type=None,
        ).as_dict() == {"resource_category": "network-device", "resource_type": "switch"}
        assert ResourceTaxonomy.classify(
            kind="firewall",
            resource_category=None,
            resource_type=None,
        ).as_dict() == {"resource_category": "network-device", "resource_type": "firewall"}
        assert ResourceTaxonomy.classify(
            kind="device",
            resource_category="server",
            resource_type=None,
        ).as_dict() == {"resource_category": "server", "resource_type": "physical-server"}
        assert ResourceTaxonomy.classify(
            kind=None,
            resource_category=None,
            resource_type=None,
            attributes={"resource_category": "personal_computer", "resource_type": "laptop"},
        ).as_dict() == {"resource_category": "personal-computer", "resource_type": "laptop"}

    def test_classification_rejects_invalid_tokens_missing_category_and_wrong_pairs(self) -> None:
        for callable_ in (
            lambda: ResourceTaxonomy.normalize_token("?", "resource category"),
            lambda: ResourceTaxonomy.type_values_for_category("missing-category"),
            lambda: ResourceTaxonomy.default_type_for_category("missing-category"),
            lambda: ResourceTaxonomy.classify(
                kind="unsupported-kind", resource_category=None, resource_type=None
            ),
            lambda: ResourceTaxonomy.classify(
                kind=None, resource_category=None, resource_type=None
            ),
            lambda: ResourceTaxonomy.classify(
                kind=None, resource_category="storage", resource_type="firewall"
            ),
            lambda: ResourceTaxonomy.classify(
                kind=None,
                resource_category=None,
                resource_type=None,
                attributes={"resource_category": "   "},
            ),
        ):
            with pytest.raises(ValidationError):
                callable_()
