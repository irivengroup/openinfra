from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path

from openinfra.application.container import ApplicationFactory
from openinfra.application.dcim_services import LocateEquipmentCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _request_json(
    url: str,
    method: str,
    payload: Mapping[str, object] | list[object] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers: dict[str, str] = {}
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            return int(response.status), body
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return int(exc.code), body


def test_http_api_error_contracts_cover_all_routes(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    admin_token = "q" * 40
    dcim_token = "r" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "api-admin", ("admin",), admin_token)
    )
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "api-dcim", ("dcim:operator",), dcim_token)
    )
    app.dcim_service.locate_equipment(
        LocateEquipmentCommand(
            tenant_id="default",
            actor="pytest",
            asset_tag="ERR-QR-1",
            equipment_name="Error QR",
            site="PAR1",
            building="BAT-A",
            floor="F01",
            room="MMR1",
            zone=None,
            row="A",
            column="01",
            rack=None,
            u_position=None,
            rack_face=None,
            u_height=None,
            x=None,
            y=None,
            z=None,
        )
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        # GET not found and query validation branches.
        assert _request_json(base + "/api/v1/unknown", "GET")[0] == 404
        for route in (
            "/api/v1/security/tokens",
            "/api/v1/access/rules",
            "/api/v1/audit/events",
            "/api/v1/audit/integrity",
            "/api/v1/rsot/governance-rules",
            "/api/v1/rsot/objects",
            "/api/v1/rsot/object-versions",
            "/api/v1/rsot/relations",
            "/api/v1/identity/effective",
        ):
            code, payload = _request_json(base + route + "?tenant_id=default&limit=bad", "GET")
            assert code in {400, 401}
            assert "error" in payload
        assert _request_json(base + "/api/v1/dcim/rack-capacity?tenant_id=default", "GET")[0] == 400
        assert (
            _request_json(
                base + "/api/v1/dcim/locator-sheet?tenant_id=default", "GET", token=dcim_token
            )[0]
            == 400
        )
        assert (
            _request_json(
                base + "/api/v1/dcim/locator-sheet?tenant_id=default&asset_tag=ERR-QR-1&format=pdf",
                "GET",
                token=dcim_token,
            )[0]
            == 400
        )
        assert (
            _request_json(
                base + "/api/v1/dcim/room-plan?tenant_id=default", "GET", token=dcim_token
            )[0]
            == 400
        )
        assert (
            _request_json(
                base + "/api/v1/dcim/rack-elevation?tenant_id=default", "GET", token=dcim_token
            )[0]
            == 400
        )
        assert (
            _request_json(
                base + "/api/v1/dcim/cable-trace?tenant_id=default", "GET", token=dcim_token
            )[0]
            == 400
        )
        # Authenticated positive locator keeps success path under the same test.
        locator_code, locator = _request_json(
            base + "/api/v1/dcim/locator-sheet?tenant_id=default&asset_tag=ERR-QR-1&format=html",
            "GET",
            token=dcim_token,
        )
        assert locator_code == 200
        assert "OpenInfra fiche localisation" in str(locator["html"])

        # POST not found, content-length and JSON shape validation.
        assert _request_json(base + "/api/v1/not-there", "POST", {})[0] == 404
        request = urllib.request.Request(
            base + "/api/v1/security/whoami",
            data=b"[]",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
        request = urllib.request.Request(
            base + "/api/v1/security/whoami",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        bad_posts: tuple[tuple[str, dict[str, object], str | None], ...] = (
            ("/api/v1/dcim/rooms", {}, dcim_token),
            ("/api/v1/dcim/racks", {}, dcim_token),
            ("/api/v1/dcim/patch-panels", {}, dcim_token),
            ("/api/v1/dcim/ports", {}, dcim_token),
            ("/api/v1/dcim/cables", {"tenant_id": "default", "path_segments": "bad"}, dcim_token),
            (
                "/api/v1/dcim/verify-scan",
                {"tenant_id": "default", "asset_tag": "ERR-QR-1", "payload": "bad"},
                dcim_token,
            ),
            ("/api/v1/rsot/governance-rules", {}, admin_token),
            ("/api/v1/rsot/governance/evaluate", {}, admin_token),
            ("/api/v1/rsot/governance/deactivate-rule", {}, admin_token),
            ("/api/v1/rsot/objects", {"tenant_id": "default", "tags": "bad"}, admin_token),
            ("/api/v1/rsot/relations", {}, admin_token),
            ("/api/v1/audit/export", {"tenant_id": "default", "format": "bad"}, admin_token),
            ("/api/v1/security/whoami", {"tenant_id": "default", "token": "bad"}, admin_token),
            ("/api/v1/security/revoke-token", {}, admin_token),
            (
                "/api/v1/security/rotate-token",
                {"tenant_id": "default", "current_token": admin_token, "roles": "bad"},
                admin_token,
            ),
            ("/api/v1/access/rules", {"tenant_id": "default", "subjects": "bad"}, admin_token),
            ("/api/v1/access/deactivate-rule", {}, admin_token),
            ("/api/v1/access/evaluate", {}, admin_token),
            ("/api/v1/identity/users", {"tenant_id": "default", "roles": "bad"}, admin_token),
            ("/api/v1/identity/groups", {"tenant_id": "default", "roles": "bad"}, admin_token),
            ("/api/v1/identity/group-memberships", {}, admin_token),
            ("/api/v1/identity/user-roles", {}, admin_token),
            ("/api/v1/identity/group-roles", {}, admin_token),
            ("/api/v1/ipam/allocate", {}, admin_token),
        )
        for route, body, token in bad_posts:
            code, response = _request_json(base + route, "POST", body, token=token)
            assert code in {400, 401}
            assert "error" in response
        assert (
            _request_json(
                base + "/api/v1/identity/users",
                "POST",
                {
                    "tenant_id": "default",
                    "username": "x",
                    "display_name": "X",
                    "email": "x@example.org",
                    "roles": ["viewer"],
                },
            )[0]
            == 401
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_api_authenticated_bad_request_branches_and_entrypoint(
    tmp_path: Path, monkeypatch
) -> None:
    import sys
    from argparse import Namespace

    from openinfra.interfaces import http_api
    from openinfra.interfaces.http_api import OpenInfraApiEntrypoint

    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    admin_token = "s" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "api-admin", ("admin",), admin_token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        bad_gets = (
            "/api/v1/security/tokens?tenant_id=default&limit=bad",
            "/api/v1/access/rules?tenant_id=default&limit=bad",
            "/api/v1/audit/events?tenant_id=default&limit=bad",
            "/api/v1/audit/integrity?tenant_id=default&limit=bad",
            "/api/v1/rsot/governance-rules?tenant_id=default&limit=bad",
            "/api/v1/rsot/objects?tenant_id=default&limit=bad",
            "/api/v1/rsot/object-versions?tenant_id=default&key=x&version=bad",
            "/api/v1/rsot/relations?tenant_id=default&limit=bad",
        )
        for route in bad_gets:
            code, payload = _request_json(base + route, "GET", token=admin_token)
            assert code == 400
            assert "error" in payload
        blank = urllib.request.Request(
            base + "/api/v1/security/tokens?tenant_id=default",
            headers={"Authorization": "Bearer   "},
            method="GET",
        )
        try:
            urllib.request.urlopen(blank, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    class FakeServer:
        created: list[tuple[tuple[str, int], object, bool]] = []

        def __init__(self, address, application, auth_required=False):
            self.address = address
            self.application = application
            self.auth_required = auth_required
            self.closed = False
            FakeServer.created.append((address, application, auth_required))

        def serve_forever(self):
            raise KeyboardInterrupt()

        def server_close(self):
            self.closed = True

    monkeypatch.setattr(http_api, "OpenInfraThreadingServer", FakeServer)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "openinfra-api",
            "--backend",
            "json",
            "--data",
            str(tmp_path / "entry.json"),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--auth-required",
        ],
    )
    assert OpenInfraApiEntrypoint.main() == 0
    assert FakeServer.created[0][2] is True

    entrypoint = OpenInfraApiEntrypoint()
    sentinel = object()
    monkeypatch.setattr(
        http_api.ApplicationFactory,
        "create_postgresql_application",
        lambda self, dsn, seed=False: sentinel,
    )
    monkeypatch.setenv("OPENINFRA_DATABASE_DSN", "postgresql://openinfra@db/openinfra")
    assert (
        entrypoint._create_application(
            Namespace(backend="postgresql", data=tmp_path / "ignored.json", postgres_dsn=None)
        )
        is sentinel
    )


def test_http_api_authenticated_external_itsm_and_read_routes_cover_error_branches(
    tmp_path: Path,
) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    admin_token = "t" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "api-admin", ("admin",), admin_token)
    )
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        unauthorized_gets = (
            "/api/v1/editions/policies?tenant_id=default",
            "/api/v1/editions/feature-check?tenant_id=default&edition=enterprise&capability=core_rsot",
            "/api/v1/editions/quota-check?tenant_id=default&edition=enterprise&resource=rsot_objects",
            "/api/v1/search/global?tenant_id=default&query=server",
            "/api/v1/itam/support-profile?tenant_id=default&asset_tag=A-1",
            "/api/v1/itam/support-coverage?tenant_id=default&asset_tag=A-1",
            "/api/v1/itam/software-license?tenant_id=default&license_reference=L-1",
            "/api/v1/itam/software-license/compliance?tenant_id=default&license_reference=L-1",
            "/api/v1/exports/jobs?tenant_id=default&job_id=missing",
            "/api/v1/exports/artifact?tenant_id=default&job_id=missing",
            "/api/v1/exports/artifact-chunk?tenant_id=default&job_id=missing",
            "/api/v1/rsot/governance-rules?tenant_id=default",
        )
        for route in unauthorized_gets:
            code, payload = _request_json(base + route, "GET")
            assert code == 401
            assert "error" in payload

        taxonomy_code, taxonomy = _request_json(
            base + "/api/v1/rsot/resource-taxonomy", "GET", token=admin_token
        )
        assert taxonomy_code == 200
        assert "categories" in taxonomy

        bad_gets = (
            "/api/v1/editions/feature-check?tenant_id=default",
            "/api/v1/editions/quota-check?tenant_id=default",
            "/api/v1/search/global?tenant_id=default",
            "/api/v1/itam/support-profile?tenant_id=default",
            "/api/v1/itam/support-coverage?tenant_id=default",
            "/api/v1/itam/software-license?tenant_id=default",
            "/api/v1/itam/software-license/compliance?tenant_id=default",
            "/api/v1/imports/report?tenant_id=default",
            "/api/v1/imports/bulk-report?tenant_id=default",
            "/api/v1/imports/bulk-checkpoint?tenant_id=default",
            "/api/v1/imports/bulk-progress?tenant_id=default",
            "/api/v1/imports/migration-template",
            "/api/v1/imports/migration-report?tenant_id=default",
            "/api/v1/exports/jobs?tenant_id=default",
            "/api/v1/exports/artifact?tenant_id=default",
            "/api/v1/exports/artifact-chunk?tenant_id=default",
            "/api/v1/rsot/governance-rules?tenant_id=default&limit=bad",
        )
        for route in bad_gets:
            code, payload = _request_json(base + route, "GET", token=admin_token)
            assert code == 400
            assert "error" in payload

        unauthorized_posts: tuple[tuple[str, dict[str, object]], ...] = (
            (
                "/api/v1/integrations/itsm/servicenow/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "https://instance.service-now.com",
                    "table_name": "cmdb_ci",
                    "auth_secret_ref": "vault://openinfra/servicenow/oauth",
                },
            ),
            (
                "/api/v1/integrations/itsm/servicenow/ci-sync-plan",
                {"tenant_id": "default", "resource_key": "SRV-PAR1-001"},
            ),
        )
        for route, body in unauthorized_posts:
            code, payload = _request_json(base + route, "POST", body)
            assert code == 401
            assert "error" in payload

        bad_posts: tuple[tuple[str, dict[str, object]], ...] = (
            (
                "/api/v1/integrations/itsm/servicenow/validate",
                {
                    "tenant_id": "default",
                    "instance_url": "http://snow",
                    "auth_secret_ref": "vault://ok",
                },
            ),
            (
                "/api/v1/integrations/itsm/servicenow/ci-sync-plan",
                {"tenant_id": "default", "resource_key": "SRV-PAR1-001", "mapping": "bad"},
            ),
            (
                "/api/v1/integrations/itsm/servicenow/ci-sync-plan",
                {"tenant_id": "default", "resource_key": "x"},
            ),
        )
        for route, body in bad_posts:
            code, payload = _request_json(base + route, "POST", body, token=admin_token)
            assert code == 400
            assert "error" in payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
