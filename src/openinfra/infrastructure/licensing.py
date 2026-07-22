from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from openinfra.application.ports import LicenseCryptography
from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.domain.licensing import (
    InstallationIdentity,
    LicenseActivationRequest,
    LicenseEntitlement,
)


class Ed25519LicenseCryptography(LicenseCryptography):
    def create_installation_material(
        self,
        *,
        installation_id: str,
        license_id: str,
        company_name: str,
        edition: str,
        requested_max_hosts: int,
    ) -> tuple[InstallationIdentity, LicenseActivationRequest, bytes]:
        private_key = Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = self._public_pem(private_key.public_key()).decode("ascii")
        identity = InstallationIdentity.create(
            installation_id=installation_id,
            license_id=license_id,
            company_name=company_name,
            edition=edition,
            public_key_pem=public_pem,
        )
        unsigned = LicenseActivationRequest.create_unsigned(identity, requested_max_hosts)
        request = unsigned.with_signature(private_key.sign(unsigned.signing_payload))
        return identity, request, private_pem

    def verify_activation_request(self, request: LicenseActivationRequest) -> None:
        public_key = self._load_public_key(request.installation_public_key_pem.encode("utf-8"))
        try:
            public_key.verify(base64.b64decode(request.signature), request.signing_payload)
        except (InvalidSignature, ValueError) as exc:
            raise ValidationError("activation request signature is invalid") from exc

    def generate_authority_material(self, password: bytes) -> tuple[bytes, bytes, str]:
        if len(password) < 12:
            raise ValidationError("authority private-key password must contain at least 12 bytes")
        private_key = Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(password),
        )
        public_pem = self._public_pem(private_key.public_key())
        return private_pem, public_pem, self.public_key_id(public_pem)

    def issue_entitlement(
        self,
        *,
        request: LicenseActivationRequest,
        authority_private_key_pem: bytes,
        password: bytes,
        max_hosts: int,
        not_before: datetime,
        expires_at: datetime,
        issued_at: datetime | None = None,
    ) -> LicenseEntitlement:
        self.verify_activation_request(request)
        host_limit = int(max_hosts)
        if host_limit > request.requested_max_hosts:
            raise ValidationError("issued host limit cannot exceed the signed requested host limit")
        private_key = self._load_private_key(authority_private_key_pem, password)
        public_pem = self._public_pem(private_key.public_key())
        entitlement = LicenseEntitlement.create_unsigned(
            installation_id=request.installation_id,
            license_id=request.license_id,
            company_name=request.company_name,
            edition=request.edition,
            installation_public_key_fingerprint=hashlib.sha256(
                InstallationIdentity._normalize_pem(request.installation_public_key_pem).encode(
                    "utf-8"
                )
            ).hexdigest(),
            max_hosts=host_limit,
            issued_at=issued_at or datetime.now(UTC),
            not_before=not_before,
            expires_at=expires_at,
            grace_days=30,
            authority_key_id=self.public_key_id(public_pem),
        )
        return entitlement.with_signature(private_key.sign(entitlement.signing_payload))

    def verify_entitlement(
        self,
        entitlement: LicenseEntitlement,
        trust_bundle_pem: bytes,
    ) -> None:
        signature = self._decode_signature(entitlement.signature)
        trusted_keys = self._trusted_public_keys(trust_bundle_pem)
        matching = [
            key
            for key in trusted_keys
            if self.public_key_id(self._public_pem(key)) == entitlement.authority_key_id
        ]
        if not matching:
            raise ValidationError("license authority key is not trusted")
        for public_key in matching:
            try:
                public_key.verify(signature, entitlement.signing_payload)
                return
            except InvalidSignature:
                continue
        raise ValidationError("license authority signature is invalid")

    def public_key_id(self, public_key_pem: bytes) -> str:
        public_key = self._load_public_key(public_key_pem)
        der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(der).hexdigest()[:32]

    def _trusted_public_keys(self, trust_bundle_pem: bytes) -> tuple[Ed25519PublicKey, ...]:
        blocks = re.findall(
            rb"-----BEGIN PUBLIC KEY-----\s+.*?-----END PUBLIC KEY-----",
            trust_bundle_pem.replace(b"\r\n", b"\n"),
            flags=re.DOTALL,
        )
        if not blocks:
            raise ValidationError("license trust bundle does not contain a public key")
        return tuple(self._load_public_key(block + b"\n") for block in blocks)

    def _load_private_key(self, payload: bytes, password: bytes) -> Ed25519PrivateKey:
        try:
            loaded = serialization.load_pem_private_key(payload, password=password)
        except (TypeError, ValueError) as exc:
            raise ValidationError("authority private key or password is invalid") from exc
        if not isinstance(loaded, Ed25519PrivateKey):
            raise ValidationError("authority private key must use Ed25519")
        return loaded

    def _load_public_key(self, payload: bytes) -> Ed25519PublicKey:
        normalized = payload.replace(b"\r\n", b"\n").strip() + b"\n"
        try:
            loaded = serialization.load_pem_public_key(normalized)
        except ValueError as exc:
            raise ValidationError("license public key is invalid") from exc
        if not isinstance(loaded, Ed25519PublicKey):
            raise ValidationError("license public key must use Ed25519")
        return loaded

    def _public_pem(self, public_key: Ed25519PublicKey) -> bytes:
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).replace(b"\r\n", b"\n")

    def _decode_signature(self, value: str) -> bytes:
        try:
            return base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValidationError("license signature encoding is invalid") from exc


class LicenseMaterialStore:
    def write_installation_material(
        self,
        root: Path,
        identity: InstallationIdentity,
        request: LicenseActivationRequest,
        private_key_pem: bytes,
    ) -> dict[str, Path]:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        paths = {
            "identity": root / "installation-identity.json",
            "request": root / "activation-request.json",
            "private_key": root / "installation-private.pem",
            "public_key": root / "installation-public.pem",
        }
        self._atomic_write(
            paths["identity"],
            self._json_bytes(identity.as_dict()),
            0o600,
        )
        self._atomic_write(paths["request"], self._json_bytes(request.as_dict()), 0o640)
        self._atomic_write(paths["private_key"], private_key_pem, 0o600)
        self._atomic_write(paths["public_key"], identity.public_key_pem.encode("utf-8"), 0o644)
        return paths

    def write_authority_material(
        self,
        private_path: Path,
        public_path: Path,
        private_key_pem: bytes,
        public_key_pem: bytes,
    ) -> None:
        self._atomic_write(private_path, private_key_pem, 0o600)
        self._atomic_write(public_path, public_key_pem, 0o644)

    def write_entitlement(self, path: Path, entitlement: LicenseEntitlement) -> None:
        self._atomic_write(path, self._json_bytes(entitlement.as_dict()), 0o640)

    def load_identity(self, path: Path) -> InstallationIdentity:
        payload = self._load_json(path)
        return InstallationIdentity.from_dict(payload)

    def load_request(self, path: Path) -> LicenseActivationRequest:
        payload = self._load_json(path)
        return LicenseActivationRequest.from_dict(payload)

    def load_entitlement(self, path: Path) -> LicenseEntitlement:
        payload = self._load_json(path)
        return LicenseEntitlement.from_dict(payload)

    def _load_json(self, path: Path) -> dict[str, object]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OpenInfraError("license document is unreadable: " + str(path)) from exc
        if not isinstance(payload, dict):
            raise ValidationError("license document must contain a JSON object")
        return cast(dict[str, object], payload)

    def _atomic_write(self, path: Path, payload: bytes, mode: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(mode)
            temporary.replace(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _json_bytes(self, payload: dict[str, Any]) -> bytes:
        return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
            "utf-8"
        )
