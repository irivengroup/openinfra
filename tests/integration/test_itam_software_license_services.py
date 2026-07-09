from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.itam_services import (
    CreateItamPartnerCommand,
    GetSoftwareLicenseCommand,
    GetSoftwareLicenseComplianceCommand,
    RegisterSoftwareLicenseCommand,
    UpdateSoftwareLicenseAssignmentCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import NotFoundError, ValidationError
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _admin_token(app: object, token: str = "sw_" + "b" * 40) -> str:
    app.security_service.bootstrap_token(  # type: ignore[attr-defined]
        BootstrapTokenCommand(
            tenant_id="default",
            actor="pytest",
            subject="itam-license-admin",
            roles=("admin",),
            token=token,
        )
    )
    return token


def _post_json(url: str, payload: dict[str, object], token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_json_allow_error(
    url: str,
    method: str,
    token: str | None = None,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    headers: dict[str, str] = {}
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _create_software_publisher(app: object, token: str, partner_id: str = "iriven-labs") -> None:
    app.itam_support_service.create_partner(  # type: ignore[attr-defined]
        CreateItamPartnerCommand(
            organization_id="default",
            partner_id=partner_id,
            kind="software_publisher",
            actor="pytest",
            admin_token=token,
            scope_tenant_id="default",
            legal_name="Iriven Labs SAS",
            display_name="Iriven Labs",
            registration_number=f"REG-{partner_id.upper()}",
            tax_identifier=f"TAX-{partner_id.upper()}",
            country_code="FR",
            city="Paris",
            address="1 rue du Test",
            contact_email=f"contact-{partner_id}@example.invalid",
            phone="+33123456789",
            support_contact=f"support-{partner_id}@example.invalid",
        )
    )


def test_software_license_entitlement_and_compliance_report(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    _create_software_publisher(app, token)

    license_ = app.itam_support_service.register_software_license(
        RegisterSoftwareLicenseCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            product_name="OpenInfra Enterprise Connector",
            vendor="Iriven Labs",
            vendor_partner_id="iriven-labs",
            license_reference="lic-001",
            contract_reference="ctr-sw-001",
            metric="device",
            purchased_quantity=100,
            assigned_quantity=70,
            entitlement_start="2026-01-01",
            entitlement_end="2027-01-01",
            version="2026",
            owner="DSI",
            notes="Initial entitlement",
        )
    )
    assert license_.as_dict()["license_reference"] == "LIC-001"
    assert license_.as_dict()["available_quantity"] == 30

    updated = app.itam_support_service.update_software_license_assignment(
        UpdateSoftwareLicenseAssignmentCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            license_reference="lic-001",
            assigned_quantity=110,
            notes="Inventory reconciliation found additional installs",
        )
    )
    assert updated.as_dict()["assigned_quantity"] == 110

    report = app.itam_support_service.get_software_license_compliance(
        GetSoftwareLicenseComplianceCommand("default", token, "LIC-001", as_of="2026-07-08")
    ).as_dict()
    assert report["compliance_state"] == "over_assigned"
    assert report["available_quantity"] == -10
    assert report["utilization_percent"] == 110.0
    assert report["contract_reference"] == "CTR-SW-001"

    reloaded = app.itam_support_service.get_software_license(
        GetSoftwareLicenseCommand("default", token, "lic-001")
    )
    assert reloaded.as_dict() == updated.as_dict()


def test_software_license_validates_dates_quantities_and_unknown_assignment(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app)
    _create_software_publisher(app, token)

    with pytest.raises(NotFoundError, match="software license entitlement not found"):
        app.itam_support_service.update_software_license_assignment(
            UpdateSoftwareLicenseAssignmentCommand("default", "pytest", token, "missing", 1)
        )

    with pytest.raises(ValidationError, match="purchased quantity"):
        app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                product_name="Invalid",
                vendor="Vendor",
                vendor_partner_id="iriven-labs",
                license_reference="lic-invalid",
                metric="device",
                purchased_quantity=0,
                assigned_quantity=0,
                entitlement_start="2026-01-01",
                entitlement_end="2027-01-01",
            )
        )

    with pytest.raises(ValidationError, match="end date"):
        app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                product_name="Invalid",
                vendor="Vendor",
                vendor_partner_id="iriven-labs",
                license_reference="lic-invalid-2",
                metric="device",
                purchased_quantity=10,
                assigned_quantity=0,
                entitlement_start="2027-01-01",
                entitlement_end="2026-01-01",
            )
        )


def test_software_license_http_contract(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _admin_token(app, "c" * 40)
    _create_software_publisher(app, token)
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        created = _post_json(
            base + "/api/v1/itam/software-license",
            {
                "tenant_id": "default",
                "product_name": "OpenInfra Enterprise Connector",
                "vendor": "Iriven Labs",
                "vendor_partner_id": "iriven-labs",
                "license_reference": "lic-http-001",
                "contract_reference": "ctr-http-001",
                "metric": "device",
                "purchased_quantity": 5,
                "assigned_quantity": 4,
                "entitlement_start": "2026-01-01",
                "entitlement_end": "2027-01-01",
            },
            token,
        )
        assigned = _post_json(
            base + "/api/v1/itam/software-license/assignment",
            {
                "tenant_id": "default",
                "license_reference": "lic-http-001",
                "assigned_quantity": 6,
            },
            token,
        )
        loaded = _get_json(
            base + "/api/v1/itam/software-license?tenant_id=default&license_reference=lic-http-001",
            token,
        )
        compliance = _get_json(
            base
            + "/api/v1/itam/software-license/compliance?tenant_id=default&license_reference=lic-http-001&as_of=2026-07-08",
            token,
        )

        assert created["license_reference"] == "LIC-HTTP-001"
        assert assigned["assigned_quantity"] == 6
        assert loaded == assigned
        assert compliance["compliance_state"] == "over_assigned"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_software_license_cli_commands(tmp_path: Path, capsys: object) -> None:
    state = tmp_path / "cli-state.json"
    token = "cli" + "d" * 40
    assert (
        OpenInfraCLI().run(
            [
                "security",
                "bootstrap-token",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--actor",
                "pytest",
                "--subject",
                "itam-license-cli",
                "--role",
                "admin",
                "--token",
                token,
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "partner-create",
                "--data",
                str(state),
                "--organization",
                "default",
                "--partner",
                "iriven-labs",
                "--kind",
                "software_publisher",
                "--admin-token",
                token,
                "--legal-name",
                "Iriven Labs SAS",
                "--display-name",
                "Iriven Labs",
                "--registration-number",
                "REG-IRIVEN",
                "--tax-identifier",
                "TAX-IRIVEN",
                "--country-code",
                "FR",
                "--city",
                "Paris",
                "--address",
                "1 rue du Test",
                "--contact-email",
                "contact-iriven@example.invalid",
                "--phone",
                "+33123456789",
                "--support-contact",
                "support-iriven@example.invalid",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "register-software-license",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--product-name",
                "OpenInfra CLI Connector",
                "--vendor",
                "Iriven Labs",
                "--vendor-partner",
                "iriven-labs",
                "--license-reference",
                "lic-cli-001",
                "--metric",
                "device",
                "--purchased-quantity",
                "2",
                "--assigned-quantity",
                "1",
                "--entitlement-start",
                "2026-01-01",
                "--entitlement-end",
                "2027-01-01",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["available_quantity"] == 1

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "update-license-assignment",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--license-reference",
                "lic-cli-001",
                "--assigned-quantity",
                "3",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        OpenInfraCLI().run(
            [
                "itam",
                "software-license-compliance",
                "--data",
                str(state),
                "--tenant",
                "default",
                "--admin-token",
                token,
                "--license-reference",
                "lic-cli-001",
                "--as-of",
                "2026-07-08",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["compliance_state"] == "over_assigned"


def test_software_license_update_keeps_identity_and_reports_all_states(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app, "state" + "e" * 40)
    _create_software_publisher(app, token)

    first = app.itam_support_service.register_software_license(
        RegisterSoftwareLicenseCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            product_name="OpenInfra Workstation Agent",
            vendor="Iriven Labs",
            vendor_partner_id="iriven-labs",
            license_reference="lic-state-001",
            metric="user",
            purchased_quantity=10,
            assigned_quantity=5,
            entitlement_start="2026-01-01",
            entitlement_end="2026-12-31",
            owner="SAM Team",
            notes="first registration",
        )
    )
    second = app.itam_support_service.register_software_license(
        RegisterSoftwareLicenseCommand(
            tenant_id="default",
            actor="pytest-updater",
            admin_token=token,
            product_name="OpenInfra Workstation Agent",
            vendor="Iriven Labs",
            vendor_partner_id="iriven-labs",
            license_reference="lic-state-001",
            metric="user",
            purchased_quantity=20,
            assigned_quantity=8,
            entitlement_start="2026-01-01",
            entitlement_end="2026-12-31",
            owner="SAM Team",
            notes="renewed quantity",
        )
    )
    assert second.id == first.id
    assert second.created_by == first.created_by
    assert second.updated_by == "pytest-updater"

    compliant = app.itam_support_service.get_software_license_compliance(
        GetSoftwareLicenseComplianceCommand("default", token, "lic-state-001", as_of="2026-07-08")
    ).as_dict()
    assert compliant["compliance_state"] == "compliant"
    assert compliant["available_quantity"] == 12

    default_date_report = app.itam_support_service.get_software_license_compliance(
        GetSoftwareLicenseComplianceCommand("default", token, "lic-state-001")
    ).as_dict()
    assert default_date_report["license_reference"] == "LIC-STATE-001"

    planned = app.itam_support_service.register_software_license(
        RegisterSoftwareLicenseCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            product_name="OpenInfra Future Module",
            vendor="Iriven Labs",
            vendor_partner_id="iriven-labs",
            license_reference="lic-planned-001",
            metric="instance",
            purchased_quantity=3,
            assigned_quantity=0,
            entitlement_start="2027-01-01",
            entitlement_end="2027-12-31",
            status="planned",
        )
    )
    assert planned.version is None
    assert planned.contract_reference is None
    planned_report = app.itam_support_service.get_software_license_compliance(
        GetSoftwareLicenseComplianceCommand("default", token, "lic-planned-001", as_of="2026-07-08")
    ).as_dict()
    assert planned_report["compliance_state"] == "planned"

    expired = app.itam_support_service.register_software_license(
        RegisterSoftwareLicenseCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            product_name="Legacy Connector",
            vendor="Iriven Labs",
            vendor_partner_id="iriven-labs",
            license_reference="lic-expired-001",
            metric="socket",
            purchased_quantity=2,
            assigned_quantity=1,
            entitlement_start="2025-01-01",
            entitlement_end="2025-12-31",
            status="expired",
            contract_reference="   ",
        )
    )
    assert expired.contract_reference is None
    expired_report = app.itam_support_service.get_software_license_compliance(
        GetSoftwareLicenseComplianceCommand("default", token, "lic-expired-001", as_of="2026-07-08")
    ).as_dict()
    assert expired_report["compliance_state"] == "expired"


def test_software_license_rejects_invalid_fields_and_missing_read(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "store.json", seed=True)
    token = _admin_token(app, "invalid" + "f" * 40)
    _create_software_publisher(app, token)

    with pytest.raises(NotFoundError, match="software license entitlement not found"):
        app.itam_support_service.get_software_license(
            GetSoftwareLicenseCommand("default", token, "missing")
        )

    with pytest.raises(NotFoundError, match="software license entitlement not found"):
        app.itam_support_service.get_software_license_compliance(
            GetSoftwareLicenseComplianceCommand("default", token, "missing")
        )

    with pytest.raises(ValidationError, match="assigned quantity"):
        app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                product_name="Invalid",
                vendor="Vendor",
                vendor_partner_id="iriven-labs",
                license_reference="lic-negative",
                metric="device",
                purchased_quantity=10,
                assigned_quantity=-1,
                entitlement_start="2026-01-01",
                entitlement_end="2026-12-31",
            )
        )

    with pytest.raises(ValidationError, match="unsupported software license metric"):
        app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                product_name="Invalid",
                vendor="Vendor",
                vendor_partner_id="iriven-labs",
                license_reference="lic-metric",
                metric="invalid metric",
                purchased_quantity=10,
                assigned_quantity=0,
                entitlement_start="2026-01-01",
                entitlement_end="2026-12-31",
            )
        )

    with pytest.raises(ValidationError, match="unsupported software license status"):
        app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                product_name="Invalid",
                vendor="Vendor",
                vendor_partner_id="iriven-labs",
                license_reference="lic-status",
                metric="device",
                purchased_quantity=10,
                assigned_quantity=0,
                entitlement_start="2026-01-01",
                entitlement_end="2026-12-31",
                status="paused",
            )
        )

    with pytest.raises(ValidationError, match="software contract reference"):
        app.itam_support_service.register_software_license(
            RegisterSoftwareLicenseCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                product_name="Invalid",
                vendor="Vendor",
                vendor_partner_id="iriven-labs",
                license_reference="lic-contract",
                contract_reference="bad reference with spaces",
                metric="device",
                purchased_quantity=10,
                assigned_quantity=0,
                entitlement_start="2026-01-01",
                entitlement_end="2026-12-31",
            )
        )

    valid = app.itam_support_service.register_software_license(
        RegisterSoftwareLicenseCommand(
            tenant_id="default",
            actor="pytest",
            admin_token=token,
            product_name="Valid",
            vendor="Vendor",
            vendor_partner_id="iriven-labs",
            license_reference="lic-valid",
            metric="core",
            purchased_quantity=10,
            assigned_quantity=0,
            entitlement_start="2026-01-01",
            entitlement_end="2026-12-31",
        )
    )
    with pytest.raises(ValidationError, match="assigned quantity"):
        valid.with_assignment(-1, "pytest")


def test_software_license_http_errors_are_structured(tmp_path: Path) -> None:
    app = ApplicationFactory().create_json_application(tmp_path / "state.json")
    token = _admin_token(app, "errors" + "a" * 40)
    _create_software_publisher(app, token)
    server = OpenInfraThreadingServer(("127.0.0.1", 0), app, auth_required=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        status, body = _request_json_allow_error(
            base + "/api/v1/itam/software-license?tenant_id=default&license_reference=missing",
            "GET",
        )
        assert status == 401
        assert body["error"] in {"access_denied", "missing bearer token"}

        status, body = _request_json_allow_error(
            base + "/api/v1/itam/software-license?tenant_id=default&license_reference=missing",
            "GET",
            token=token,
        )
        assert status == 400
        assert isinstance(body["error"], str) and body["error"]

        status, body = _request_json_allow_error(
            base
            + "/api/v1/itam/software-license/compliance?tenant_id=default&license_reference=missing",
            "GET",
            token=token,
        )
        assert status == 400
        assert isinstance(body["error"], str) and body["error"]

        valid_payload: dict[str, object] = {
            "tenant_id": "default",
            "product_name": "HTTP Error Coverage",
            "vendor": "Iriven Labs",
            "vendor_partner_id": "iriven-labs",
            "license_reference": "lic-http-errors",
            "metric": "device",
            "purchased_quantity": 4,
            "assigned_quantity": 1,
            "entitlement_start": "2026-01-01",
            "entitlement_end": "2027-01-01",
        }
        status, body = _request_json_allow_error(
            base + "/api/v1/itam/software-license",
            "POST",
            payload=valid_payload,
        )
        assert status == 401
        assert body["error"] in {"access_denied", "missing bearer token"}

        invalid_payload = {**valid_payload, "purchased_quantity": "not-an-int"}
        status, body = _request_json_allow_error(
            base + "/api/v1/itam/software-license",
            "POST",
            token=token,
            payload=invalid_payload,
        )
        assert status == 400
        assert isinstance(body["error"], str) and body["error"]

        status, body = _request_json_allow_error(
            base + "/api/v1/itam/software-license/assignment",
            "POST",
            payload={
                "tenant_id": "default",
                "license_reference": "missing",
                "assigned_quantity": 1,
            },
        )
        assert status == 401
        assert body["error"] in {"access_denied", "missing bearer token"}

        status, body = _request_json_allow_error(
            base + "/api/v1/itam/software-license/assignment",
            "POST",
            token=token,
            payload={
                "tenant_id": "default",
                "license_reference": "missing",
                "assigned_quantity": 1,
            },
        )
        assert status == 400
        assert isinstance(body["error"], str) and body["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
