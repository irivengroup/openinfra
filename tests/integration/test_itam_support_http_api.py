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

        assert created["manufacturer_warranty"]["support_reference"] == "SUP-HTTP-001"
        assert updated["third_party_contracts"][0]["contract_reference"] == "TP-HTTP-001"
        assert loaded == updated
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
