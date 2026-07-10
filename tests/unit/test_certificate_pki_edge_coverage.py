from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa
from cryptography.x509.oid import NameOID
from tests.integration.test_certificate_pki_services import certificate_bundle
from tests.unit.test_certificate_pki_domain import FINGERPRINT, NOW, certificate, material

from openinfra.application.certificate_pki_services import (
    ImportCertificateBundleCommand,
    RetireCertificateCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.ports import CertificateAssetPage, CertificateEndpointPage
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.certificate_pki import (
    CertificateAsset,
    CertificateEndpointObservation,
    CertificatePkiRules,
    CertificateSource,
)
from openinfra.domain.common import EntityId, NotFoundError, TenantId, ValidationError
from openinfra.infrastructure.certificate_parser import CryptographyCertificateParser


class TestCertificatePkiDomainEdges:
    def test_validation_restore_and_idempotent_retirement_edges(self) -> None:
        assert CertificateSource.from_value("pki") is CertificateSource.INTERNAL_PKI
        assert CertificateSource.from_value("external") is CertificateSource.EXTERNAL_PKI
        with pytest.raises(ValidationError, match="source"):
            CertificateSource.from_value("unsupported")

        item = certificate()
        common = {
            "id": item.id,
            "tenant_id": item.tenant_id,
            "material": item.material,
            "chain_fingerprints": item.chain_fingerprints,
            "owner": item.owner,
            "environment": item.environment,
            "source": item.source.value,
            "object_key": item.object_key.value if item.object_key else None,
            "created_by": item.created_by,
            "created_at": item.created_at,
            "updated_by": item.updated_by,
            "updated_at": item.updated_at,
        }
        with pytest.raises(ValidationError, match="lifecycle"):
            CertificateAsset.restore(**common, lifecycle="invalid", version=1)
        with pytest.raises(ValidationError, match="version"):
            CertificateAsset.restore(**common, lifecycle="active", version=0)
        retired = item.retire("operator")
        assert retired.retire("operator") is retired
        with pytest.raises(ValidationError, match="thresholds"):
            item.health(NOW, critical_days=-1, warning_days=30)

    def test_rule_and_endpoint_restore_error_edges(self) -> None:
        with pytest.raises(ValidationError, match="16"):
            CertificatePkiRules.chain(tuple(f"{index:064x}" for index in range(17)), FINGERPRINT)
        with pytest.raises(ValidationError, match="characters"):
            CertificatePkiRules.bounded_text("", "label", 1, 4)
        assert CertificatePkiRules.optional_text(None, "label", 4) is None
        assert CertificatePkiRules.optional_text("  ", "label", 4) is None
        with pytest.raises(ValidationError, match="exceed"):
            CertificatePkiRules.optional_text("abcde", "label", 4)
        with pytest.raises(ValidationError, match="invalid"):
            CertificatePkiRules.safe_token("bad token!", "token", 16)
        assert CertificatePkiRules.optional_safe_token(None, "token", 16) is None
        assert CertificatePkiRules.optional_safe_token("", "token", 16) is None
        with pytest.raises(ValidationError, match="invalid"):
            CertificatePkiRules.safe_identifier("!bad", "identifier", 2, 16)
        with pytest.raises(ValidationError, match="timezone-aware"):
            CertificatePkiRules.aware_datetime(datetime(2026, 7, 10), "date")
        with pytest.raises(ValidationError, match="hostname"):
            CertificatePkiRules.hostname("a" * 254)
        with pytest.raises(ValidationError, match="hostname"):
            CertificatePkiRules.hostname("bad..example")
        with pytest.raises(ValidationError, match="hostname"):
            CertificatePkiRules.hostname("")

        observation = CertificateEndpointObservation.create(
            tenant_id=TenantId.from_value("default"),
            idempotency_key="scanner:ipv6:1",
            protocol="https",
            host="2001:db8::1",
            port=443,
            service="IPv6 endpoint",
            certificate_fingerprint=FINGERPRINT,
            observed_at=NOW,
            source="discovery",
            collector="scanner-01",
            object_key=None,
            tls_version=None,
            cipher=None,
        )
        assert observation.endpoint == "https://[2001:db8::1]:443"
        with pytest.raises(ValidationError, match="inconsistent"):
            CertificateEndpointObservation.restore(
                id=EntityId.new(),
                tenant_id=observation.tenant_id,
                idempotency_key=observation.idempotency_key,
                protocol=observation.protocol,
                host=observation.host,
                port=observation.port,
                service=observation.service,
                certificate_fingerprint=observation.certificate_fingerprint,
                observed_at=observation.observed_at,
                source=observation.source.value,
                collector=observation.collector,
                object_key=None,
                tls_version=None,
                cipher=None,
                received_at=NOW,
                payload_fingerprint="f" * 64,
            )


class TestCertificateParserAlgorithms:
    @pytest.mark.parametrize(
        ("algorithm", "expected"),
        [("ec", "ec-secp256r1"), ("dsa", "dsa"), ("ed25519", "ed25519"), ("ed448", "ed448")],
    )
    def test_verifies_supported_signature_algorithms(self, algorithm: str, expected: str) -> None:
        materials = CryptographyCertificateParser().parse_pem_bundle(
            self._bundle(algorithm=algorithm)
        )
        assert materials[1].public_key_algorithm == expected

    def test_rejects_mismatched_issuer_invalid_signature_and_oversized_bundle(self) -> None:
        parser = CryptographyCertificateParser()
        first = self._bundle(algorithm="rsa", root_common_name="Root A")
        second = self._bundle(algorithm="rsa", root_common_name="Root B")
        leaf = first[: first.find("-----END CERTIFICATE-----") + len("-----END CERTIFICATE-----")]
        root = second[second.rfind("-----BEGIN CERTIFICATE-----") :]
        with pytest.raises(ValidationError, match="issuer and subject"):
            parser.parse_pem_bundle(leaf + root)

        same_name_other_key = self._bundle(algorithm="rsa", root_common_name="Root A")
        other_root = same_name_other_key[same_name_other_key.rfind("-----BEGIN CERTIFICATE-----") :]
        with pytest.raises(ValidationError, match="signature verification"):
            parser.parse_pem_bundle(leaf + other_root)

        one = first[: first.find("-----END CERTIFICATE-----") + len("-----END CERTIFICATE-----")]
        with pytest.raises(ValidationError, match="16"):
            parser.parse_pem_bundle(one * 17)
        with pytest.raises(ValidationError, match="text"):
            parser.parse_pem_bundle(123)  # type: ignore[arg-type]

        class UnknownPublicKey:
            key_size = 999

        assert parser._public_key_description(UnknownPublicKey()) == ("unknownpublickey", 999)

        class UnknownParent:
            @staticmethod
            def public_key() -> UnknownPublicKey:
                return UnknownPublicKey()

        with pytest.raises(ValidationError, match="unsupported"):
            parser._verify_signature(object(), UnknownParent())  # type: ignore[arg-type]

    @staticmethod
    def _bundle(*, algorithm: str, root_common_name: str = "Algorithm Root") -> str:
        now = datetime.now(UTC)
        if algorithm == "rsa":
            root_key: Any = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            leaf_key: Any = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            signing_hash: hashes.HashAlgorithm | None = hashes.SHA256()
        elif algorithm == "ec":
            root_key = ec.generate_private_key(ec.SECP256R1())
            leaf_key = ec.generate_private_key(ec.SECP256R1())
            signing_hash = hashes.SHA256()
        elif algorithm == "dsa":
            root_key = dsa.generate_private_key(key_size=2048)
            leaf_key = dsa.generate_private_key(key_size=2048)
            signing_hash = hashes.SHA256()
        elif algorithm == "ed25519":
            root_key = ed25519.Ed25519PrivateKey.generate()
            leaf_key = ed25519.Ed25519PrivateKey.generate()
            signing_hash = None
        else:
            root_key = ed448.Ed448PrivateKey.generate()
            leaf_key = ed448.Ed448PrivateKey.generate()
            signing_hash = None
        root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, root_common_name)])
        leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "leaf.example.net")])
        root = (
            x509.CertificateBuilder()
            .subject_name(root_name)
            .issuer_name(root_name)
            .public_key(root_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
            .sign(root_key, signing_hash)
        )
        leaf = (
            x509.CertificateBuilder()
            .subject_name(leaf_name)
            .issuer_name(root_name)
            .public_key(leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=30))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(root_key, signing_hash)
        )
        return "".join(
            item.public_bytes(serialization.Encoding.PEM).decode("ascii") for item in (leaf, root)
        )


class TestCertificatePkiServiceEdges:
    def test_date_cursor_chain_and_cyclic_repository_guards(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        service = app.certificate_pki_service
        assert service._actor("  ", "token-subject") == "token-subject"
        assert service._datetime(None) is None
        assert service._datetime("") is None
        assert service._datetime(NOW) == NOW
        with pytest.raises(ValidationError, match="ISO-8601"):
            service._datetime("not-a-date")
        with pytest.raises(ValidationError, match="timezone-aware"):
            service._datetime(datetime(2026, 7, 10))
        with pytest.raises(ValidationError, match="required"):
            service._required_datetime("", "observed_at")
        with pytest.raises(ValidationError, match="numeric"):
            service._offset("bad")
        with pytest.raises(ValidationError, match="positive"):
            service._offset("-1")

        leaf = certificate()
        assert not service._chain_complete(leaf, {}, ("missing",))
        root = certificate(
            material=material(subject_dn="CN=Root", issuer_dn="CN=Root", is_ca=True),
            chain_fingerprints=(),
        )
        assert service._chain_complete(root, {root.fingerprint_sha256: root}, ())

        class CyclicRepository:
            def list_certificates(self, *_args: object, **_kwargs: object) -> CertificateAssetPage:
                return CertificateAssetPage((), "loop")

            def list_endpoint_observations(
                self, *_args: object, **_kwargs: object
            ) -> CertificateEndpointPage:
                return CertificateEndpointPage((), "loop")

        original = service._repository
        service._repository = CyclicRepository()  # type: ignore[assignment]
        try:
            with pytest.raises(ValidationError, match="cyclic cursor"):
                service._all_certificates(TenantId.from_value("default"))
            with pytest.raises(ValidationError, match="cyclic cursor"):
                service._all_endpoints(TenantId.from_value("default"))
        finally:
            service._repository = original

    def test_missing_retirement_and_immutable_collision(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        token = "f" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "certificate-admin", ("admin",), token)
        )
        with pytest.raises(NotFoundError, match="not found"):
            app.certificate_pki_service.retire_certificate(
                RetireCertificateCommand("default", "pytest", token, "a" * 64)
            )

        bundle = certificate_bundle()
        imported = app.certificate_pki_service.import_bundle(
            ImportCertificateBundleCommand(
                "default", "pytest", token, bundle, "Platform", "production", "manual"
            )
        )
        original = app.certificate_pki_service._repository.get_certificate_by_fingerprint

        def inconsistent(tenant_id: TenantId, fingerprint: str) -> CertificateAsset | None:
            found = original(tenant_id, fingerprint)
            if found is None:
                return None
            return CertificateAsset.restore(
                id=found.id,
                tenant_id=found.tenant_id,
                material=material(fingerprint_sha256=fingerprint, serial_number="FF"),
                chain_fingerprints=found.chain_fingerprints,
                owner=found.owner,
                environment=found.environment,
                source=found.source.value,
                object_key=None,
                lifecycle=found.lifecycle.value,
                version=found.version,
                created_by=found.created_by,
                created_at=found.created_at,
                updated_by=found.updated_by,
                updated_at=found.updated_at,
            )

        app.certificate_pki_service._repository.get_certificate_by_fingerprint = inconsistent  # type: ignore[method-assign]
        with pytest.raises(Exception, match="inconsistent immutable material"):
            app.certificate_pki_service.import_bundle(
                ImportCertificateBundleCommand(
                    "default",
                    "pytest",
                    token,
                    bundle,
                    "Platform",
                    "production",
                    "manual",
                )
            )
        assert imported.leaf.fingerprint_sha256
