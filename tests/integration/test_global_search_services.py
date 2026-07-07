from __future__ import annotations

import json

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.discovery_services import RegisterCollectorCommand
from openinfra.application.ipam_services import AllocateIpCommand, DefineIpPrefixCommand, DefineVrfCommand
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
            attributes_json=json.dumps(
                {"hostname": "paris-db-01", "serial_number": "SN-DB-01"}
            ),
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

    result = app.global_search_service.search(
        GlobalSearchCommand("default", "pytest", token, "paris", limit=3)
    ).as_dict()

    assert result["total"] >= 3
    groups = {group["component"]: group for group in result["groups"]}
    assert {"itrm", "ipam", "discovery"}.issubset(groups)
    assert groups["itrm"]["items"][0]["label"] == "Paris DB 01"
    assert groups["ipam"]["items"]
    assert groups["discovery"]["items"][0]["label"] == "Paris discovery proxy"
    assert groups["itrm"]["items"][0]["route"].startswith("/api/v1/itrm/objects")


def test_global_search_validates_query_and_limit(tmp_path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    with pytest.raises(ValidationError, match="2 to 128"):
        app.global_search_service.search(GlobalSearchCommand("default", "pytest", token, "x"))
    with pytest.raises(ValidationError, match="1 and 25"):
        app.global_search_service.search(
            GlobalSearchCommand("default", "pytest", token, "valid", limit=26)
        )
