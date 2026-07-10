from __future__ import annotations

import re
from contextlib import suppress
from datetime import UTC
from itertools import pairwise

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import (
    dsa,
    ec,
    ed448,
    ed25519,
    padding,
    rsa,
)
from cryptography.x509.oid import ExtensionOID, NameOID

from openinfra.application.ports import CertificateParser
from openinfra.domain.certificate_pki import CertificateMaterial
from openinfra.domain.common import ValidationError


class CryptographyCertificateParser(CertificateParser):
    _PEM_PATTERN = re.compile(
        r"-----BEGIN CERTIFICATE-----\s+.*?-----END CERTIFICATE-----",
        re.DOTALL,
    )
    _PRIVATE_KEY_PATTERN = re.compile(
        r"-----BEGIN (?:ENCRYPTED |RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    )

    def parse_pem_bundle(self, pem_bundle: str) -> tuple[CertificateMaterial, ...]:
        if not isinstance(pem_bundle, str):
            raise ValidationError("certificate PEM bundle must be text")
        if self._PRIVATE_KEY_PATTERN.search(pem_bundle):
            raise ValidationError("certificate PEM bundle must not contain a private key")
        blocks = tuple(self._PEM_PATTERN.findall(pem_bundle.strip()))
        if not blocks:
            raise ValidationError("certificate PEM bundle does not contain a certificate")
        if len(blocks) > 16:
            raise ValidationError("certificate PEM bundle cannot exceed 16 certificates")
        certificates: list[x509.Certificate] = []
        for block in blocks:
            try:
                certificates.append(x509.load_pem_x509_certificate(block.encode("ascii")))
            except (ValueError, UnicodeEncodeError) as exc:
                raise ValidationError("certificate PEM bundle contains invalid data") from exc
        self._validate_adjacent_chain(certificates)
        return tuple(self._material(certificate) for certificate in certificates)

    def _material(self, certificate: x509.Certificate) -> CertificateMaterial:
        san_dns: tuple[str, ...] = ()
        san_ip: tuple[str, ...] = ()
        san_email: tuple[str, ...] = ()
        san_uri: tuple[str, ...] = ()
        try:
            san_extension = certificate.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value
            if not isinstance(san_extension, x509.SubjectAlternativeName):
                raise ValidationError("certificate SAN extension has an invalid type")
            san_dns = tuple(san_extension.get_values_for_type(x509.DNSName))
            san_ip = tuple(
                str(value) for value in san_extension.get_values_for_type(x509.IPAddress)
            )
            san_email = tuple(san_extension.get_values_for_type(x509.RFC822Name))
            san_uri = tuple(san_extension.get_values_for_type(x509.UniformResourceIdentifier))
        except x509.ExtensionNotFound:
            pass

        is_ca = False
        with suppress(x509.ExtensionNotFound):
            basic_constraints = certificate.extensions.get_extension_for_oid(
                ExtensionOID.BASIC_CONSTRAINTS
            ).value
            if not isinstance(basic_constraints, x509.BasicConstraints):
                raise ValidationError("certificate basic constraints extension has an invalid type")
            is_ca = basic_constraints.ca

        common_name: str | None = None
        common_names = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if common_names:
            common_name_value = common_names[0].value
            common_name = (
                common_name_value.decode("utf-8")
                if isinstance(common_name_value, bytes)
                else common_name_value
            )

        public_key = certificate.public_key()
        public_key_algorithm, public_key_size = self._public_key_description(public_key)
        signature_algorithm = (
            certificate.signature_hash_algorithm.name
            if certificate.signature_hash_algorithm is not None
            else certificate.signature_algorithm_oid.dotted_string
        )
        return CertificateMaterial.create(
            fingerprint_sha256=certificate.fingerprint(hashes.SHA256()).hex(),
            serial_number=f"{certificate.serial_number:X}",
            subject_dn=certificate.subject.rfc4514_string(),
            issuer_dn=certificate.issuer.rfc4514_string(),
            common_name=common_name,
            san_dns=san_dns,
            san_ip=san_ip,
            san_email=san_email,
            san_uri=san_uri,
            not_before=certificate.not_valid_before_utc.astimezone(UTC),
            not_after=certificate.not_valid_after_utc.astimezone(UTC),
            public_key_algorithm=public_key_algorithm,
            public_key_size=public_key_size,
            signature_algorithm=signature_algorithm,
            is_ca=is_ca,
        )

    @staticmethod
    def _public_key_description(public_key: object) -> tuple[str, int | None]:
        if isinstance(public_key, rsa.RSAPublicKey):
            return "rsa", public_key.key_size
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            return f"ec-{public_key.curve.name}", public_key.key_size
        if isinstance(public_key, dsa.DSAPublicKey):
            return "dsa", public_key.key_size
        if isinstance(public_key, ed25519.Ed25519PublicKey):
            return "ed25519", 256
        if isinstance(public_key, ed448.Ed448PublicKey):
            return "ed448", 448
        return public_key.__class__.__name__.lower(), getattr(public_key, "key_size", None)

    def _validate_adjacent_chain(self, certificates: list[x509.Certificate]) -> None:
        fingerprints = [certificate.fingerprint(hashes.SHA256()) for certificate in certificates]
        if len(set(fingerprints)) != len(fingerprints):
            raise ValidationError("certificate PEM bundle contains duplicate certificates")
        for child, parent in pairwise(certificates):
            if child.issuer != parent.subject:
                raise ValidationError("certificate chain issuer and subject do not match")
            self._verify_signature(child, parent)

    @staticmethod
    def _verify_signature(child: x509.Certificate, parent: x509.Certificate) -> None:
        public_key = parent.public_key()
        try:
            if isinstance(public_key, rsa.RSAPublicKey):
                hash_algorithm = child.signature_hash_algorithm
                if hash_algorithm is None:
                    raise ValidationError("RSA certificate signature hash is missing")
                algorithm_parameters = child.signature_algorithm_parameters
                rsa_padding = (
                    algorithm_parameters
                    if isinstance(algorithm_parameters, padding.AsymmetricPadding)
                    else padding.PKCS1v15()
                )
                public_key.verify(
                    child.signature,
                    child.tbs_certificate_bytes,
                    rsa_padding,
                    hash_algorithm,
                )
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                hash_algorithm = child.signature_hash_algorithm
                if hash_algorithm is None:
                    raise ValidationError("EC certificate signature hash is missing")
                public_key.verify(
                    child.signature,
                    child.tbs_certificate_bytes,
                    ec.ECDSA(hash_algorithm),
                )
            elif isinstance(public_key, dsa.DSAPublicKey):
                hash_algorithm = child.signature_hash_algorithm
                if hash_algorithm is None:
                    raise ValidationError("DSA certificate signature hash is missing")
                public_key.verify(
                    child.signature,
                    child.tbs_certificate_bytes,
                    hash_algorithm,
                )
            elif isinstance(public_key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
                public_key.verify(child.signature, child.tbs_certificate_bytes)
            else:
                raise ValidationError("certificate chain public key algorithm is unsupported")
        except InvalidSignature as exc:
            raise ValidationError("certificate chain signature verification failed") from exc
