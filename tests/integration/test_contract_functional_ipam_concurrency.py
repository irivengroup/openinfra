from __future__ import annotations

import json
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import DefineIpPrefixCommand, DefineIpRangeCommand
from openinfra.domain.common import TenantId
from openinfra.interfaces.http_api import OpenInfraThreadingServer
from tests.frontend_contract_sources import REACT_PORTAL, RUNTIME_PORTAL


def _reserve(base_url: str, sequence: int) -> tuple[int, dict[str, object]]:
    payload = {
        "tenant_id": "default",
        "actor": "contract-test",
        "vrf": "production",
        "prefix": "10.72.0.0/27",
        "hostname": f"srv-concurrent-{sequence:02d}",
        "idempotency_key": f"contract-concurrent-{sequence:02d}",
        "apply": True,
    }
    request = urllib.request.Request(
        base_url + "/api/v1/ipam/reservation-wizard",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_concurrent_ip_reservations_never_allocate_the_same_address_and_are_web_exposed(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    app.ipam_model_service.define_prefix(
        DefineIpPrefixCommand("default", "pytest", "production", "10.72.0.0/27")
    )
    app.ipam_model_service.define_range(
        DefineIpRangeCommand(
            "default",
            "pytest",
            "production",
            "10.72.0.0/27",
            "10.72.0.1",
            "10.72.0.30",
            "allocation",
            "Contractual concurrent allocation range",
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with ThreadPoolExecutor(max_workers=12) as executor:
            results = tuple(executor.map(lambda item: _reserve(base_url, item), range(20)))

        assert {status for status, _ in results} == {201}
        payloads = tuple(payload for _, payload in results)
        addresses = tuple(str(payload["address"]) for payload in payloads)
        assert len(addresses) == 20
        assert len(set(addresses)) == 20
        assert sorted(addresses, key=lambda value: tuple(map(int, value.split(".")))) == [
            f"10.72.0.{index}" for index in range(1, 21)
        ]
        assert {payload["operation"] for payload in payloads} == {"allocated"}
        assert {payload["dry_run"] for payload in payloads} == {False}

        replay_status, replay = _reserve(base_url, 0)
        assert replay_status == 201
        assert replay["operation"] == "idempotent_replay"
        assert replay["address"] == payloads[0]["address"]

        reservations = app.ipam_repository.list_reservations(
            TenantId.from_value("default"),
            "production",
            "10.72.0.0/27",
        )
        assert len(reservations) == 20
        assert len({str(item.address) for item in reservations}) == 20

        for portal in (REACT_PORTAL.read_text(), RUNTIME_PORTAL.read_text()):
            assert '"id": "ipam-reservation-wizard"' in portal
            assert '"path": "/v1/ipam/reservation-wizard"' in portal
            assert "Clé d’idempotence" in portal
            assert "Appliquer la réservation" in portal
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
