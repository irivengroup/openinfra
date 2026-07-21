from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.licensing_services import BootstrapInstallationIdentityCommand
from openinfra.infrastructure.licensing import Ed25519LicenseCryptography
from openinfra.interfaces.cli import OpenInfraCLI
from openinfra.interfaces.http_api import OpenInfraThreadingServer


def _json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_http_license_enforcement_activation_and_renewal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cryptography = Ed25519LicenseCryptography()
    password = b"correct horse battery staple"
    authority_private, authority_public, _ = cryptography.generate_authority_material(password)
    trust_bundle = tmp_path / "authority-public.pem"
    trust_bundle.write_bytes(authority_public)
    monkeypatch.setenv("OPENINFRA_LICENSE_ENFORCEMENT", "true")
    monkeypatch.setenv("OPENINFRA_LICENSE_TRUST_BUNDLE", str(trust_bundle))

    application = ApplicationFactory().create_json_application(
        tmp_path / "state.json", seed=False, edition="pro"
    )
    identity, request, _ = cryptography.create_installation_material(
        installation_id=str(uuid4()),
        license_id=str(uuid4()),
        company_name="OpenInfra Interface Tests",
        edition="pro",
        requested_max_hosts=25,
    )
    application.license_service.bootstrap_identity(
        BootstrapInstallationIdentityCommand(identity=identity, actor="test-installer")
    )
    now = datetime.now(UTC)
    entitlement = cryptography.issue_entitlement(
        request=request,
        authority_private_key_pem=authority_private,
        password=password,
        max_hosts=20,
        not_before=now,
        expires_at=now + timedelta(days=365),
        issued_at=now,
    )
    renewal = cryptography.issue_entitlement(
        request=request,
        authority_private_key_pem=authority_private,
        password=password,
        max_hosts=20,
        not_before=now,
        expires_at=now + timedelta(days=730),
        issued_at=now + timedelta(minutes=1),
    )

    server = OpenInfraThreadingServer(("127.0.0.1", 0), application)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        status_code, status = _json_request(base_url + "/api/v1/license/status")
        blocked_code, blocked = _json_request(base_url + "/api/v1/editions/policies")
        assert status_code == 200
        assert status["status"] == "missing"
        assert status["runtime_allowed"] is False
        assert blocked_code == 402
        assert blocked["error"] == "runtime_license_required"
        assert blocked["license"]["status"] == "missing"

        activation_code, activation = _json_request(
            base_url + "/api/v1/license/activate",
            method="POST",
            payload={"actor": "http-test", "entitlement": entitlement.as_dict()},
        )
        allowed_code, allowed = _json_request(base_url + "/api/v1/editions/policies")
        assert activation_code == 200
        assert activation["status"] == "active"
        assert activation["max_hosts"] == 20
        assert allowed_code == 200
        assert isinstance(allowed["items"], list)

        renewal_code, renewed = _json_request(
            base_url + "/api/v1/license/renew",
            method="POST",
            payload={"actor": "http-test", "entitlement": renewal.as_dict()},
        )
        assert renewal_code == 200
        assert renewed["status"] == "active"
        assert renewed["expires_at"] == renewal.expires_at.isoformat()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cli_offline_license_lifecycle_and_business_command_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data_path = tmp_path / "state.json"
    material_dir = tmp_path / "installation"
    password_path = tmp_path / "authority-password"
    private_path = tmp_path / "authority-private.pem"
    public_path = tmp_path / "authority-public.pem"
    entitlement_path = tmp_path / "entitlement.json"
    password_path.write_bytes(b"correct horse battery staple\n")

    cli = OpenInfraCLI()
    assert (
        cli.run(
            [
                "license",
                "authority-generate",
                "--password-file",
                str(password_path),
                "--private-key",
                str(private_path),
                "--public-key",
                str(public_path),
            ]
        )
        == 0
    )
    authority = json.loads(capsys.readouterr().out)
    assert authority["authority_key_id"]
    monkeypatch.setenv("OPENINFRA_LICENSE_ENFORCEMENT", "true")
    monkeypatch.setenv("OPENINFRA_LICENSE_TRUST_BUNDLE", str(public_path))
    monkeypatch.setenv("OPENINFRA_EDITION", "pro")

    license_id = str(uuid4())
    assert (
        cli.run(
            [
                "license",
                "bootstrap",
                "--data",
                str(data_path),
                "--edition",
                "pro",
                "--license-id",
                license_id,
                "--company-name",
                "OpenInfra CLI Tests",
                "--requested-max-hosts",
                "12",
                "--material-dir",
                str(material_dir),
            ]
        )
        == 0
    )
    bootstrap = json.loads(capsys.readouterr().out)
    assert bootstrap["identity"]["license_id"] == license_id
    assert Path(bootstrap["files"]["private_key"]).stat().st_mode & 0o777 == 0o600

    blocked_code = cli.run(
        [
            "security",
            "bootstrap-token",
            "--data",
            str(data_path),
            "--tenant",
            "default",
            "--subject",
            "blocked-client",
            "--role",
            "admin",
            "--token",
            "b" * 40,
        ]
    )
    blocked = capsys.readouterr()
    assert blocked_code == 2
    assert "activation is missing" in blocked.err

    now = datetime.now(UTC)
    assert (
        cli.run(
            [
                "license",
                "issue",
                "--request",
                str(material_dir / "activation-request.json"),
                "--authority-private-key",
                str(private_path),
                "--password-file",
                str(password_path),
                "--max-hosts",
                "10",
                "--not-before",
                (now - timedelta(minutes=1)).isoformat(),
                "--expires-at",
                (now + timedelta(days=365)).isoformat(),
                "--output",
                str(entitlement_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli.run(
            [
                "license",
                "activate",
                "--data",
                str(data_path),
                "--edition",
                "pro",
                "--entitlement",
                str(entitlement_path),
            ]
        )
        == 0
    )
    activated = json.loads(capsys.readouterr().out)
    assert activated["status"] == "active"

    assert (
        cli.run(
            [
                "license",
                "status",
                "--data",
                str(data_path),
                "--edition",
                "pro",
            ]
        )
        == 0
    )
    status = json.loads(capsys.readouterr().out)
    assert status["runtime_allowed"] is True
    assert status["max_hosts"] == 10

    allowed_code = cli.run(
        [
            "security",
            "bootstrap-token",
            "--data",
            str(data_path),
            "--tenant",
            "default",
            "--subject",
            "licensed-client",
            "--role",
            "admin",
            "--token",
            "a" * 40,
        ]
    )
    allowed = json.loads(capsys.readouterr().out)
    assert allowed_code == 0
    assert allowed["subject"] == "licensed-client"
