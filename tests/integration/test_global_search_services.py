from __future__ import annotations

import json

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import RegisterCollectorCommand
from openinfra.application.ipam_services import (
    AllocateIpCommand,
    DefineIpPrefixCommand,
    DefineVrfCommand,
)
from openinfra.application.itam_services import RegisterManufacturerSupportCommand
from openinfra.application.search_services import GlobalSearchCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.application.source_of_truth_services import UpsertSourceObjectCommand
from openinfra.domain.common import ValidationError


def _admin_token(app: object) -> str:
    result = app.security_service.bootstrap_token(  # type: ignore[attr-defined]
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="global-search-admin",
            roles=("admin",),
            token="gs_" + "a" * 40,
        )
    )
    return result.token or "gs_" + "a" * 40


def test_global_search_groups_backend_results_by_component(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    app.it_resources_management_service.upsert_object(
        UpsertSourceObjectCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            key="server/paris-db-01",
            kind="server",
            display_name="Paris DB 01",
            attributes_json=json.dumps({"hostname": "paris-db-01", "serial_number": "SN-DB-01"}),
            tags=("paris", "database"),
            source="manual",
            resource_category="server",
            resource_type="rack-server",
        )
    )
    app.ipam_model_service.define_vrf(DefineVrfCommand("default", "pytest", "global"))
    app.ipam_model_service.define_prefix(
        DefineIpPrefixCommand("default", "pytest", "global", "10.38.0.0/29", "Paris DB")
    )
    app.ipam_service.allocate(
        AllocateIpCommand("default", "pytest", "global", "10.38.0.0/29", "paris-db-01", "db01")
    )
    app.discovery_service.register_collector(
        RegisterCollectorCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            name="Paris discovery proxy",
            kind="site-proxy",
            certificate_fingerprint="b" * 64,
            scopes=("site/paris",),
            version="1.0.0",
            endpoint_url="https://collector-paris.openinfra.local",
        )
    )

    app.itam_support_service.register_manufacturer_support(
        RegisterManufacturerSupportCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            asset_tag="PARIS-ITAM-001",
            manufacturer="Dell",
            warranty_reference="WR-PARIS-001",
            warranty_level="ProSupport",
            warranty_start="2026-01-01",
            warranty_end="2029-01-01",
            support_reference="SUP-PARIS-001",
            support_level="24x7",
            support_contact="support@example.com",
        )
    )

    result = app.global_search_service.search(
        GlobalSearchCommand("default", "pytest", token, "paris", limit=3)
    ).as_dict()

    assert result["total"] >= 3
    groups = {group["component"]: group for group in result["groups"]}
    assert {"rsot", "itam", "ipam", "discovery"}.issubset(groups)
    assert groups["rsot"]["items"][0]["label"] == "Paris DB 01"
    assert groups["ipam"]["items"]
    assert groups["discovery"]["items"][0]["label"] == "Paris discovery proxy"
    assert groups["rsot"]["items"][0]["route"].startswith("/api/v1/rsot/objects")

    itam_result = app.global_search_service.search(
        GlobalSearchCommand("default", "pytest", token, "PARIS-ITAM-001", limit=3)
    ).as_dict()
    itam_groups = {group["component"]: group for group in itam_result["groups"]}
    assert itam_groups["itam"]["items"][0]["label"] == "PARIS-ITAM-001"
    assert itam_groups["itam"]["items"][0]["route"].startswith("/api/v1/itam/support-profile")


def test_global_search_validates_query_and_limit(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    with pytest.raises(ValidationError, match="2 to 128"):
        app.global_search_service.search(GlobalSearchCommand("default", "pytest", token, "x"))
    with pytest.raises(ValidationError, match="1 and 25"):
        app.global_search_service.search(
            GlobalSearchCommand("default", "pytest", token, "valid", limit=26)
        )


def test_global_search_handles_skipped_groups_and_ipam_label_variants(tmp_path) -> None:
    from openinfra.domain.common import AccessDeniedError

    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    class DenyRsot:
        def list_objects(self, _command: object) -> object:
            raise AccessDeniedError("rsot denied")

    class DenyItam:
        def get_support_profile(self, _command: object) -> object:
            raise AccessDeniedError("itam denied")

    class DenyDiscovery:
        def list_collectors(self, _command: object) -> object:
            raise AccessDeniedError("discovery denied")

    class IpamWithVariants:
        def search(self, _command: object) -> dict[str, object]:
            return {
                "items": [
                    "ignored-row",
                    {"kind": "prefix", "prefix": "alpha-prefix", "vrf": "global"},
                    {
                        "kind": "reservation",
                        "address": "10.0.0.7",
                        "hostname": "alpha-reservation",
                        "vrf": "global",
                    },
                    {
                        "kind": "dns",
                        "hostname": "alpha.example.org",
                        "address": "10.0.0.8",
                        "vrf": "global",
                    },
                    {
                        "kind": "dhcp_lease",
                        "address": "10.0.0.9",
                        "mac_address": "aa:bb:cc:dd:ee:ff",
                        "comment": "alpha lease",
                        "vrf": "global",
                    },
                    {"kind": "address", "address": "10.0.0.10", "hostname": "alpha-host"},
                    {"kind": "address", "address": "10.0.0.11", "hostname": "beta-host"},
                ]
            }

    app.global_search_service._rsot_service = DenyRsot()
    app.global_search_service._itam_support_service = DenyItam()
    app.global_search_service._discovery_service = DenyDiscovery()
    app.global_search_service._ipam_ui_service = IpamWithVariants()

    result = app.global_search_service.search(
        GlobalSearchCommand("default", "pytest", token, "alpha", limit=10)
    ).as_dict()

    groups = {group["component"]: group for group in result["groups"]}
    assert groups["rsot"]["reason"] == "permission denied"
    assert groups["itam"]["reason"] == "permission denied"
    assert groups["discovery"]["reason"] == "permission denied"
    ipam_items = groups["ipam"]["items"]
    assert {item["kind"] for item in ipam_items} == {
        "prefix",
        "reservation",
        "dns",
        "dhcp_lease",
        "address",
    }
    labels_by_kind = {item["kind"]: item["label"] for item in ipam_items}
    assert labels_by_kind["reservation"] == "10.0.0.7 · alpha-reservation"
    assert labels_by_kind["dns"] == "alpha.example.org → 10.0.0.8"


def test_global_search_empty_itam_result_when_profile_fields_do_not_match(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)

    class EmptyPage:
        items: tuple[object, ...] = ()

    class EmptyRsot:
        def list_objects(self, _command: object) -> EmptyPage:
            return EmptyPage()

    class ItamProfileWithoutMatchingFields:
        def as_dict(self) -> dict[str, object]:
            return {"asset_tag": "OTHER-ASSET", "manufacturer_warranty": "invalid-shape"}

    class ItamWithProfile:
        def get_support_profile(self, _command: object) -> ItamProfileWithoutMatchingFields:
            return ItamProfileWithoutMatchingFields()

    class EmptyIpam:
        def search(self, _command: object) -> dict[str, object]:
            return {"items": []}

    class EmptyDiscovery:
        def list_collectors(self, _command: object) -> EmptyPage:
            return EmptyPage()

    app.global_search_service._rsot_service = EmptyRsot()
    app.global_search_service._itam_support_service = ItamWithProfile()
    app.global_search_service._ipam_ui_service = EmptyIpam()
    app.global_search_service._discovery_service = EmptyDiscovery()

    result = app.global_search_service.search(
        GlobalSearchCommand("default", "pytest", token, "nomatch", limit=5)
    ).as_dict()

    groups = {group["component"]: group for group in result["groups"]}
    assert groups["itam"]["items"] == []
