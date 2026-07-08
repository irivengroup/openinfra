from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _post_json(url: str, payload: dict[str, object], token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_itam_support_profile_http_contract(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="itam-http",
            roles=("admin",),
            token=token,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        created = _post_json(
            base + "/api/v1/itam/support-profile/manufacturer",
            {
                "tenant_id": "default",
                "asset_tag": "srv-http-001",
                "manufacturer": "Dell",
                "warranty_reference": "war-http-001",
                "warranty_level": "ProSupport",
                "warranty_start": "2026-01-01",
                "warranty_end": "2029-01-01",
                "support_reference": "sup-http-001",
                "support_level": "24x7",
                "support_contact": "support@example.invalid",
            },
            token,
        )
        updated = _post_json(
            base + "/api/v1/itam/support-profile/third-party",
            {
                "tenant_id": "default",
                "asset_tag": "srv-http-001",
                "provider": "ThirdSupport",
                "contract_reference": "tp-http-001",
                "support_level": "4h onsite",
                "support_start": "2026-02-01",
                "support_end": "2027-02-01",
                "support_contact": "noc@example.invalid",
            },
            token,
        )
        loaded = _get_json(
            base + "/api/v1/itam/support-profile?tenant_id=default&asset_tag=srv-http-001",
            token,
        )
        coverage = _get_json(
            base
            + "/api/v1/itam/support-coverage?tenant_id=default&asset_tag=srv-http-001&as_of=2026-07-01",
            token,
        )

        assert created["manufacturer_warranty"]["support_reference"] == "SUP-HTTP-001"
        assert updated["third_party_contracts"][0]["contract_reference"] == "TP-HTTP-001"
        assert loaded == updated
        assert coverage["coverage_state"] == "manufacturer_active"
        assert coverage["third_party_active_count"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_itam_tenant_http_contract(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state-tenants.json")
    token = "t" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="itam-tenant-http",
            roles=("admin",),
            token=token,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        organizations = _get_json(base + "/api/v1/itam/organizations?tenant_id=default", token)
        assert organizations["default_organization_id"] == "default"

        organization = _post_json(
            base + "/api/v1/itam/organization/create",
            {
                "organization_id": "orange",
                "scope_tenant_id": "default",
                "actor": "pytest",
                "legal_name": "Orange SA",
                "display_name": "Orange",
                "registration_number": "RCS-PARIS-123",
                "tax_identifier": "FR123456789",
                "country_code": "FR",
                "city": "Paris",
                "address": "111 Quai du Président Roosevelt",
                "contact_email": "contact@orange.example",
                "support_contact": "support@orange.example",
            },
            token,
        )
        assert organization["organization_id"] == "orange"
        assert organization["legal_name"] == "Orange SA"

        loaded_organization = _get_json(
            base + "/api/v1/itam/organization?tenant_id=default&organization_id=orange",
            token,
        )
        assert loaded_organization["display_name"] == "Orange"

        updated_organization = _post_json(
            base + "/api/v1/itam/organization/update",
            {
                "organization_id": "orange",
                "scope_tenant_id": "default",
                "legal_name": "Orange France SA",
                "support_contact": "soc@orange.example",
            },
            token,
        )
        assert updated_organization["legal_name"] == "Orange France SA"
        assert updated_organization["support_contact"] == "soc@orange.example"

        catalog = _get_json(base + "/api/v1/itam/tenants?tenant_id=default", token)
        assert catalog["auto_selected_tenant_id"] == "default"

        created = _post_json(
            base + "/api/v1/itam/tenant/create",
            {
                "tenant_id": "finance",
                "organization_id": "orange",
                "scope_tenant_id": "default",
                "name": "Finance",
                "is_default": True,
            },
            token,
        )
        assert created["tenant_id"] == "finance"
        assert created["organization_id"] == "orange"
        assert created["is_default"] is True

        updated = _post_json(
            base + "/api/v1/itam/tenant/update",
            {
                "tenant_id": "finance",
                "scope_tenant_id": "default",
                "name": "Finance IT",
                "is_default": False,
            },
            token,
        )
        assert updated["name"] == "Finance IT"
        assert updated["is_default"] is False

        retired = _post_json(
            base + "/api/v1/itam/tenant/delete",
            {"tenant_id": "finance", "scope_tenant_id": "default"},
            token,
        )
        assert retired["status"] == "retired"

        retired_organization = _post_json(
            base + "/api/v1/itam/organization/delete",
            {"organization_id": "orange", "scope_tenant_id": "default"},
            token,
        )
        assert retired_organization["status"] == "retired"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
