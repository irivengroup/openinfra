from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import LocateEquipmentCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _request_json(
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_field_operation_http_contract_exposes_generate_list_qr_and_lock(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "h" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "field-http-admin", ("admin",), token)
    )
    app.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="PAR-SRV-HTTP",
            equipment_name="Serveur HTTP terrain",
            site="PAR1",
            building="BAT-A",
            room="MMR1",
            row="B",
            column="12",
            rack="R42",
            u_position=10,
            x=12.0,
            y=4.0,
            z=0.0,
            floor="F01",
            rack_face="front",
            u_height=2,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, generated = _request_json(
            base + "/api/v1/field-operation-sheets/generate",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "target_type": "equipment",
                "target_id": "PAR-SRV-HTTP",
                "title": "Intervention HTTP",
                "purpose": "Valider le parcours HTTP des opérations terrain.",
                "owner": "ops.owner",
                "operator": "field.operator",
            },
        )
        assert status == 201
        sheet_id = str(generated["id"])

        list_url = (
            base
            + "/api/v1/field-operation-sheets?"
            + urllib.parse.urlencode({"tenant_id": "default", "limit": "10"})
        )
        status, listed = _request_json(list_url, token=token)
        assert status == 200
        assert [item["id"] for item in listed["items"]] == [sheet_id]

        status, verified = _request_json(
            base + "/api/v1/qr-codes/verify",
            token=token,
            payload={
                "tenant_id": "default",
                "sheet_id": sheet_id,
                "payload": generated["qr_payload"],
            },
        )
        assert status == 200
        assert verified["verified"] is True

        status, lock = _request_json(
            base + "/api/v1/intervention-locks/acquire",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "sheet_id": sheet_id,
                "idempotency_key": "http-field-lock-0001",
                "ttl_seconds": 3600,
            },
        )
        assert status == 201
        assert lock["active"] is True

        unauthorized_status, unauthorized = _request_json(list_url)
        assert unauthorized_status == 401
        assert "token" in str(unauthorized["error"]).lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_field_evidence_http_rejects_invalid_base64(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "i" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "field-http-admin", ("admin",), token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, response = _request_json(
            f"http://127.0.0.1:{server.server_port}/api/v1/field-evidence/attach",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "sheet_id": "00000000-0000-4000-8000-000000000001",
                "phase": "before",
                "media_type": "image/png",
                "filename": "before.png",
                "content_base64": "%%%",
                "caption": "Preuve invalide",
            },
        )
        assert status == 400
        assert (
            "does not exist" in str(response["error"]).lower()
            or "base64" in str(response["error"]).lower()
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_field_operation_http_full_offline_evidence_and_completion_workflow(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = "j" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "field-http-admin", ("admin",), token)
    )
    app.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="PAR-SRV-HTTP-FULL",
            equipment_name="Serveur HTTP terrain complet",
            site="PAR1",
            building="BAT-A",
            room="MMR1",
            row="B",
            column="12",
            rack="R42",
            u_position=10,
            x=12.0,
            y=4.0,
            z=0.0,
            floor="F01",
            rack_face="front",
            u_height=2,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, generated = _request_json(
            base + "/api/v1/field-operation-sheets/generate",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "target_type": "equipment",
                "target_id": "PAR-SRV-HTTP-FULL",
                "title": "Intervention HTTP complète",
                "purpose": "Valider le parcours HTTP complet et la synchronisation hors ligne.",
                "owner": "ops.owner",
                "operator": "field.operator",
            },
        )
        assert status == 201
        sheet_id = str(generated["id"])

        get_url = (
            base
            + "/api/v1/field-operation-sheets/get?"
            + urllib.parse.urlencode({"tenant_id": "default", "sheet_id": sheet_id})
        )
        status, fetched = _request_json(get_url, token=token)
        assert status == 200
        assert fetched["id"] == sheet_id

        status, lock = _request_json(
            base + "/api/v1/intervention-locks/acquire",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "sheet_id": sheet_id,
                "idempotency_key": "http-field-full-lock-0001",
                "ttl_seconds": 3600,
            },
        )
        assert status == 201

        status, started = _request_json(
            base + "/api/v1/field-operation-sheets/start",
            token=token,
            payload={"tenant_id": "default", "actor": "pytest", "sheet_id": sheet_id},
        )
        assert status == 200
        assert started["status"] == "in-progress"

        for checklist_item in started["checklist"]:
            status, checked = _request_json(
                base + "/api/v1/field-operation-sheets/checklist",
                token=token,
                payload={
                    "tenant_id": "default",
                    "actor": "pytest",
                    "sheet_id": sheet_id,
                    "item_id": checklist_item["id"],
                    "result": "passed",
                    "operator_note": "Contrôle HTTP validé",
                },
            )
            assert status == 200
            assert checked["id"] == sheet_id

        evidence_ids: list[str] = []
        for phase in ("before", "after"):
            status, evidence = _request_json(
                base + "/api/v1/field-evidence/attach",
                token=token,
                payload={
                    "tenant_id": "default",
                    "actor": "pytest",
                    "sheet_id": sheet_id,
                    "phase": phase,
                    "media_type": "image/png",
                    "filename": f"{phase}.png",
                    "content_base64": base64.b64encode(f"http-evidence-{phase}".encode()).decode(),
                    "caption": f"Photo {phase}",
                },
            )
            assert status == 201
            evidence_id = str(evidence["id"])
            evidence_ids.append(evidence_id)
            status, validated = _request_json(
                base + "/api/v1/field-evidence/validate",
                token=token,
                payload={
                    "tenant_id": "default",
                    "actor": "pytest",
                    "evidence_id": evidence_id,
                },
            )
            assert status == 200
            assert validated["status"] == "validated"

        evidence_url = (
            base
            + "/api/v1/field-evidence?"
            + urllib.parse.urlencode({"tenant_id": "default", "sheet_id": sheet_id})
        )
        status, evidence_page = _request_json(evidence_url, token=token)
        assert status == 200
        assert {item["id"] for item in evidence_page["items"]} == set(evidence_ids)

        status, package = _request_json(
            base + "/api/v1/offline-sync-packages/create",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "sheet_id": sheet_id,
                "idempotency_key": "http-offline-package-0001",
                "ttl_seconds": 86400,
            },
        )
        assert status == 201
        package_id = str(package["id"])
        payload_sha256 = str(package["payload_sha256"])
        assert package["payload"]

        packages_url = (
            base
            + "/api/v1/offline-sync-packages?"
            + urllib.parse.urlencode({"tenant_id": "default", "sheet_id": sheet_id, "limit": "10"})
        )
        status, packages = _request_json(packages_url, token=token)
        assert status == 200
        assert [item["id"] for item in packages["items"]] == [package_id]

        package_url = (
            base
            + "/api/v1/offline-sync-packages/get?"
            + urllib.parse.urlencode(
                {
                    "tenant_id": "default",
                    "package_id": package_id,
                    "include_payload": "false",
                }
            )
        )
        status, package_without_payload = _request_json(package_url, token=token)
        assert status == 200
        assert "payload" not in package_without_payload

        status, synchronized = _request_json(
            base + "/api/v1/offline-sync-packages/synchronize",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "package_id": package_id,
                "payload_sha256": payload_sha256,
            },
        )
        assert status == 200
        assert synchronized["status"] == "synchronized"

        status, completed = _request_json(
            base + "/api/v1/field-operation-sheets/complete",
            token=token,
            payload={"tenant_id": "default", "actor": "pytest", "sheet_id": sheet_id},
        )
        assert status == 200
        assert completed["status"] == "completed"

        status, generated_cancel = _request_json(
            base + "/api/v1/field-operation-sheets/generate",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "target_type": "equipment",
                "target_id": "PAR-SRV-HTTP-FULL",
                "title": "Intervention HTTP annulée",
                "purpose": "Valider la libération explicite et l'annulation.",
                "owner": "ops.owner",
                "operator": "field.operator",
            },
        )
        assert status == 201
        cancel_sheet_id = str(generated_cancel["id"])
        status, cancel_lock = _request_json(
            base + "/api/v1/intervention-locks/acquire",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "sheet_id": cancel_sheet_id,
                "idempotency_key": "http-field-cancel-lock-0001",
                "ttl_seconds": 3600,
            },
        )
        assert status == 201
        status, released = _request_json(
            base + "/api/v1/intervention-locks/release",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "lock_id": cancel_lock["id"],
            },
        )
        assert status == 200
        assert released["active"] is False

        status, cancelled = _request_json(
            base + "/api/v1/field-operation-sheets/cancel",
            token=token,
            payload={
                "tenant_id": "default",
                "actor": "pytest",
                "sheet_id": cancel_sheet_id,
            },
        )
        assert status == 200
        assert cancelled["status"] == "cancelled"
        assert lock["active"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
