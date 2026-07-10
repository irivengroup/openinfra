from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from openinfra.application.certificate_pki_services import (
    AssessCertificatesCommand,
    GetCertificateCommand,
    ImportCertificateBundleCommand,
    ListCertificateEndpointsCommand,
    ListCertificatesCommand,
    ObserveCertificateEndpointCommand,
    RetireCertificateCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import AccessDeniedError, ConflictError, NotFoundError, ValidationError
from openinfra.infrastructure.certificate_parser import CryptographyCertificateParser


def certificate_bundle(*, leaf_days: int = 5) -> str:
    now = datetime.now(UTC)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OpenInfra Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "OpenInfra Root CA"),
        ]
    )
    root = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA256())
    )
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OpenInfra Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "api.example.com"),
        ]
    )
    leaf = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(root_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=leaf_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("api.example.com"),
                    x509.DNSName("*.service.example.com"),
                    x509.IPAddress(__import__("ipaddress").ip_address("192.0.2.10")),
                ]
            ),
            critical=False,
        )
        .sign(root_key, hashes.SHA256())
    )
    return "".join(
        certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")
        for certificate in (leaf, root)
    )


class TestCertificateParser:
    def test_parses_and_verifies_pem_chain(self) -> None:
        materials = CryptographyCertificateParser().parse_pem_bundle(certificate_bundle())

        assert len(materials) == 2
        assert materials[0].common_name == "api.example.com"
        assert materials[0].san_dns == ("api.example.com", "*.service.example.com")
        assert materials[0].is_ca is False
        assert materials[1].is_ca is True
        assert materials[0].issuer_dn == materials[1].subject_dn

    @pytest.mark.parametrize(
        "payload", ["", "not pem", "-----BEGIN CERTIFICATE-----\nbad\n-----END CERTIFICATE-----"]
    )
    def test_rejects_invalid_pem(self, payload: str) -> None:
        with pytest.raises(ValidationError):
            CryptographyCertificateParser().parse_pem_bundle(payload)

    def test_rejects_private_key_material(self) -> None:
        payload = (
            certificate_bundle()
            + "-----BEGIN PRIVATE "
            + "KEY-----\nredacted\n-----END PRIVATE KEY-----"
        )
        with pytest.raises(ValidationError, match="private key"):
            CryptographyCertificateParser().parse_pem_bundle(payload)

    def test_rejects_duplicate_chain_certificate(self) -> None:
        bundle = certificate_bundle()
        root_block = bundle[bundle.rfind("-----BEGIN CERTIFICATE-----") :]
        with pytest.raises(ValidationError, match="duplicate"):
            CryptographyCertificateParser().parse_pem_bundle(bundle + root_block)


class TestCertificatePkiServices:
    def test_inventory_endpoint_assessment_lifecycle_and_restart(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        app, token = self._application(state)
        bundle = certificate_bundle(leaf_days=5)

        imported = app.certificate_pki_service.import_bundle(
            ImportCertificateBundleCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                pem_bundle=bundle,
                owner="Platform team",
                environment="production",
                source="internal-pki",
                object_key="application/api",
            )
        )
        assert len(imported.certificates) == 2
        assert imported.leaf.chain_fingerprints == (imported.certificates[1].fingerprint_sha256,)
        assert imported.certificates[1].material.is_ca

        updated = app.certificate_pki_service.import_bundle(
            ImportCertificateBundleCommand(
                "default",
                "pytest",
                token,
                bundle,
                "Security team",
                "production",
                "discovery",
                "application/api",
            )
        )
        assert updated.leaf.id == imported.leaf.id
        assert updated.leaf.version == 2
        assert updated.leaf.owner == "Security team"

        first = self._observe(
            app,
            token,
            key="scanner-01:api:1",
            fingerprint=updated.leaf.fingerprint_sha256,
            host="api.example.com",
        )
        repeated = self._observe(
            app,
            token,
            key="scanner-01:api:1",
            fingerprint=updated.leaf.fingerprint_sha256,
            host="api.example.com",
        )
        assert repeated.id == first.id
        mismatch = self._observe(
            app,
            token,
            key="scanner-01:api:2",
            fingerprint=updated.leaf.fingerprint_sha256,
            host="wrong.example.com",
        )
        assert mismatch.id != first.id

        with pytest.raises(ConflictError, match="different payload"):
            self._observe(
                app,
                token,
                key="scanner-01:api:1",
                fingerprint=updated.leaf.fingerprint_sha256,
                host="wrong.example.com",
            )

        report = app.certificate_pki_service.assess(
            AssessCertificatesCommand(
                tenant_id="default",
                admin_token=token,
                critical_days=7,
                warning_days=30,
                health="critical",
            )
        )
        assert len(report.items) == 1
        assessment = report.items[0]
        assert assessment.certificate.id == imported.leaf.id
        assert assessment.health.value == "critical"
        assert assessment.endpoint_count == 2
        assert assessment.hostname_mismatch_count == 1
        assert assessment.chain_complete is True
        assert assessment.missing_chain_fingerprints == ()
        assert report.totals["critical"] == 1
        assert report.totals["healthy"] == 1
        assert report.truncated is False

        listed = app.certificate_pki_service.list_certificates(
            ListCertificatesCommand("default", token, limit=1)
        )
        assert len(listed.items) == 1
        assert listed.next_cursor == "1"
        endpoints = app.certificate_pki_service.list_endpoints(
            ListCertificateEndpointsCommand(
                "default", token, certificate_fingerprint=updated.leaf.fingerprint_sha256
            )
        )
        assert len(endpoints.items) == 2

        loaded = app.certificate_pki_service.get_certificate(
            GetCertificateCommand("default", token, updated.leaf.fingerprint_sha256)
        )
        assert loaded.owner == "Security team"

        restarted = ApplicationFactory().create_json_application(state, seed=False)
        reloaded = restarted.certificate_pki_service.get_certificate(
            GetCertificateCommand("default", token, updated.leaf.fingerprint_sha256)
        )
        assert reloaded.material.san_dns == ("api.example.com", "*.service.example.com")
        assert (
            len(
                restarted.certificate_pki_service.list_endpoints(
                    ListCertificateEndpointsCommand("default", token)
                ).items
            )
            == 2
        )

        retired = restarted.certificate_pki_service.retire_certificate(
            RetireCertificateCommand("default", "pytest", token, updated.leaf.fingerprint_sha256)
        )
        assert retired.lifecycle.value == "retired"
        assert (
            restarted.certificate_pki_service.assess(
                AssessCertificatesCommand("default", token, health="retired")
            )
            .items[0]
            .health.value
            == "retired"
        )

    def test_permissions_unknown_certificate_and_input_guards(self, tmp_path: Path) -> None:
        app, admin = self._application(tmp_path / "state.json")
        reader_token = "e" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand(
                "default", "pytest", "certificate-reader", ("certificate:reader",), reader_token
            )
        )

        with pytest.raises(AccessDeniedError):
            app.certificate_pki_service.import_bundle(
                ImportCertificateBundleCommand(
                    "default",
                    "pytest",
                    reader_token,
                    certificate_bundle(),
                    "Platform team",
                    "production",
                    "manual",
                )
            )
        with pytest.raises(NotFoundError):
            self._observe(app, admin, key="scanner:unknown", fingerprint="a" * 64)
        with pytest.raises(NotFoundError):
            app.certificate_pki_service.get_certificate(
                GetCertificateCommand("default", admin, "a" * 64)
            )
        with pytest.raises(ValidationError):
            app.certificate_pki_service.assess(
                AssessCertificatesCommand("default", admin, critical_days=31, warning_days=30)
            )
        with pytest.raises(ValidationError):
            app.certificate_pki_service.assess(
                AssessCertificatesCommand("default", admin, health="unknown")
            )

    @staticmethod
    def _application(state: Path):
        app = ApplicationFactory().create_json_application(state)
        token = "f" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "certificate-admin", ("admin",), token)
        )
        return app, token

    @staticmethod
    def _observe(
        app,
        token: str,
        *,
        key: str,
        fingerprint: str,
        host: str = "api.example.com",
    ):
        return app.certificate_pki_service.observe_endpoint(
            ObserveCertificateEndpointCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                idempotency_key=key,
                protocol="https",
                host=host,
                port=443,
                service="Public API",
                certificate_fingerprint=fingerprint,
                observed_at=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
                source="discovery",
                collector="scanner-01",
                object_key="application/api",
                tls_version="tls1.3",
                cipher="tls_aes_256_gcm_sha384",
            )
        )
