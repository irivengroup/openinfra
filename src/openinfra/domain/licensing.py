from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import OpenInfraError, ValidationError
from openinfra.domain.editions import OpenInfraEdition


class LicenseAccessDeniedError(OpenInfraError):
    """Raised when the commercial runtime license blocks product access."""

    def __init__(self, report: RuntimeLicenseReport) -> None:
        super().__init__(report.reason)
        self.report = report


class LicenseStateCorruptedError(OpenInfraError):
    """Raised when persisted license state cannot be parsed safely."""


class RuntimeLicenseStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    MISSING = "missing"
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"
    INVALID = "invalid"


class LicenseNotificationLevel(StrEnum):
    NONE = "none"
    INFORMATION = "information"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class InstallationIdentity:
    installation_id: str
    license_id: str
    company_name: str
    edition: OpenInfraEdition
    public_key_pem: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        installation_id: str,
        license_id: str,
        company_name: str,
        edition: str | OpenInfraEdition,
        public_key_pem: str,
        created_at: datetime | None = None,
    ) -> Self:
        normalized_company = " ".join(company_name.strip().split())
        if not 2 <= len(normalized_company) <= 255:
            raise ValidationError("license company name must contain 2 to 255 characters")
        normalized_edition = OpenInfraEdition.from_value(edition)
        if normalized_edition is OpenInfraEdition.LITE:
            raise ValidationError("Lite edition does not use a commercial runtime license")
        normalized_public_key = cls._normalize_pem(public_key_pem)
        if "BEGIN PUBLIC KEY" not in normalized_public_key:
            raise ValidationError("installation public key must be a PEM public key")
        return cls(
            installation_id=cls._uuid(installation_id, "installation id"),
            license_id=cls._uuid(license_id, "license id"),
            company_name=normalized_company,
            edition=normalized_edition,
            public_key_pem=normalized_public_key,
            created_at=cls._aware(created_at or datetime.now(UTC), "identity created_at"),
        )

    @property
    def public_key_fingerprint(self) -> str:
        return hashlib.sha256(self.public_key_pem.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "openinfra.installation-identity/v1",
            "installation_id": self.installation_id,
            "license_id": self.license_id,
            "company_name": self.company_name,
            "edition": self.edition.value,
            "public_key_pem": self.public_key_pem,
            "public_key_fingerprint": self.public_key_fingerprint,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        schema = str(payload.get("schema", "openinfra.installation-identity/v1"))
        if schema != "openinfra.installation-identity/v1":
            raise ValidationError("unsupported installation identity schema")
        return cls.create(
            installation_id=str(payload["installation_id"]),
            license_id=str(payload["license_id"]),
            company_name=str(payload["company_name"]),
            edition=str(payload["edition"]),
            public_key_pem=str(payload["public_key_pem"]),
            created_at=cls._parse_datetime(payload["created_at"], "identity created_at"),
        )

    @staticmethod
    def _uuid(value: str, label: str) -> str:
        try:
            return str(uuid.UUID(value.strip()))
        except (ValueError, AttributeError) as exc:
            raise ValidationError(f"{label} must use UUID format") from exc

    @staticmethod
    def _normalize_pem(value: str) -> str:
        normalized = value.replace("\r\n", "\n").strip()
        return normalized + "\n"

    @staticmethod
    def _aware(value: datetime, label: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def _parse_datetime(cls, value: object, label: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{label} is invalid") from exc
        return cls._aware(parsed, label)


@dataclass(frozen=True, slots=True)
class LicenseActivationRequest:
    installation_id: str
    license_id: str
    company_name: str
    edition: OpenInfraEdition
    installation_public_key_pem: str
    requested_max_hosts: int
    generated_at: datetime
    signature: str

    @classmethod
    def create_unsigned(
        cls,
        identity: InstallationIdentity,
        requested_max_hosts: int,
        generated_at: datetime | None = None,
    ) -> Self:
        host_limit = int(requested_max_hosts)
        if not 1 <= host_limit <= 10_000_000:
            raise ValidationError("requested licensed hosts must be between 1 and 10000000")
        return cls(
            installation_id=identity.installation_id,
            license_id=identity.license_id,
            company_name=identity.company_name,
            edition=identity.edition,
            installation_public_key_pem=identity.public_key_pem,
            requested_max_hosts=host_limit,
            generated_at=InstallationIdentity._aware(
                generated_at or datetime.now(UTC), "activation request generated_at"
            ),
            signature="",
        )

    def with_signature(self, signature: bytes) -> Self:
        if not signature:
            raise ValidationError("activation request signature cannot be empty")
        return replace(self, signature=base64.b64encode(signature).decode("ascii"))

    @property
    def signing_payload(self) -> bytes:
        return self._canonical_json(self.claims_dict())

    def claims_dict(self) -> dict[str, object]:
        return {
            "schema": "openinfra.license-activation-request/v1",
            "installation_id": self.installation_id,
            "license_id": self.license_id,
            "company_name": self.company_name,
            "edition": self.edition.value,
            "installation_public_key_pem": self.installation_public_key_pem,
            "requested_max_hosts": self.requested_max_hosts,
            "generated_at": self.generated_at.isoformat(),
        }

    def as_dict(self) -> dict[str, object]:
        return {**self.claims_dict(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        if str(payload.get("schema", "")) != "openinfra.license-activation-request/v1":
            raise ValidationError("unsupported license activation request schema")
        identity = InstallationIdentity.create(
            installation_id=str(payload["installation_id"]),
            license_id=str(payload["license_id"]),
            company_name=str(payload["company_name"]),
            edition=str(payload["edition"]),
            public_key_pem=str(payload["installation_public_key_pem"]),
            created_at=InstallationIdentity._parse_datetime(
                payload["generated_at"], "activation request generated_at"
            ),
        )
        request = cls.create_unsigned(
            identity,
            int(str(payload["requested_max_hosts"])),
            generated_at=InstallationIdentity._parse_datetime(
                payload["generated_at"], "activation request generated_at"
            ),
        )
        signature = str(payload.get("signature", "")).strip()
        if not signature:
            raise ValidationError("activation request signature is required")
        try:
            base64.b64decode(signature, validate=True)
        except ValueError as exc:
            raise ValidationError("activation request signature is invalid") from exc
        return replace(request, signature=signature)

    @staticmethod
    def _canonical_json(payload: dict[str, object]) -> bytes:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class LicenseEntitlement:
    installation_id: str
    license_id: str
    company_name: str
    edition: OpenInfraEdition
    installation_public_key_fingerprint: str
    max_hosts: int
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    grace_days: int
    authority_key_id: str
    signature: str

    @classmethod
    def create_unsigned(
        cls,
        *,
        installation_id: str,
        license_id: str,
        company_name: str,
        edition: str | OpenInfraEdition,
        installation_public_key_fingerprint: str,
        max_hosts: int,
        issued_at: datetime,
        not_before: datetime,
        expires_at: datetime,
        grace_days: int = 30,
        authority_key_id: str,
    ) -> Self:
        normalized_installation_id = InstallationIdentity._uuid(installation_id, "installation id")
        normalized_license_id = InstallationIdentity._uuid(license_id, "license id")
        normalized_company = " ".join(company_name.strip().split())
        if not 2 <= len(normalized_company) <= 255:
            raise ValidationError("license company name must contain 2 to 255 characters")
        normalized_edition = OpenInfraEdition.from_value(edition)
        if normalized_edition is OpenInfraEdition.LITE:
            raise ValidationError("Lite edition does not use a commercial runtime license")
        fingerprint = installation_public_key_fingerprint.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ValidationError("installation public key fingerprint must be SHA-256 hex")
        host_limit = int(max_hosts)
        if not 1 <= host_limit <= 10_000_000:
            raise ValidationError("licensed hosts must be between 1 and 10000000")
        normalized_issued = InstallationIdentity._aware(issued_at, "license issued_at")
        normalized_not_before = InstallationIdentity._aware(not_before, "license not_before")
        normalized_expires = InstallationIdentity._aware(expires_at, "license expires_at")
        if normalized_not_before < normalized_issued - timedelta(minutes=5):
            raise ValidationError("license not_before cannot materially precede issued_at")
        if normalized_expires <= normalized_not_before:
            raise ValidationError("license expires_at must be after not_before")
        if int(grace_days) != 30:
            raise ValidationError("OpenInfra commercial license grace period must be 30 days")
        key_id = authority_key_id.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{16,64}", key_id):
            raise ValidationError("authority key id is invalid")
        return cls(
            installation_id=normalized_installation_id,
            license_id=normalized_license_id,
            company_name=normalized_company,
            edition=normalized_edition,
            installation_public_key_fingerprint=fingerprint,
            max_hosts=host_limit,
            issued_at=normalized_issued,
            not_before=normalized_not_before,
            expires_at=normalized_expires,
            grace_days=30,
            authority_key_id=key_id,
            signature="",
        )

    @property
    def grace_until(self) -> datetime:
        return self.expires_at + timedelta(days=self.grace_days)

    @property
    def signing_payload(self) -> bytes:
        return LicenseActivationRequest._canonical_json(self.claims_dict())

    def with_signature(self, signature: bytes) -> Self:
        if not signature:
            raise ValidationError("license authority signature cannot be empty")
        return replace(self, signature=base64.b64encode(signature).decode("ascii"))

    def claims_dict(self) -> dict[str, object]:
        return {
            "schema": "openinfra.license-entitlement/v1",
            "installation_id": self.installation_id,
            "license_id": self.license_id,
            "company_name": self.company_name,
            "edition": self.edition.value,
            "installation_public_key_fingerprint": self.installation_public_key_fingerprint,
            "max_hosts": self.max_hosts,
            "issued_at": self.issued_at.isoformat(),
            "not_before": self.not_before.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "grace_days": self.grace_days,
            "authority_key_id": self.authority_key_id,
        }

    def as_dict(self) -> dict[str, object]:
        return {**self.claims_dict(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        if str(payload.get("schema", "")) != "openinfra.license-entitlement/v1":
            raise ValidationError("unsupported license entitlement schema")
        entitlement = cls.create_unsigned(
            installation_id=str(payload["installation_id"]),
            license_id=str(payload["license_id"]),
            company_name=str(payload["company_name"]),
            edition=str(payload["edition"]),
            installation_public_key_fingerprint=str(payload["installation_public_key_fingerprint"]),
            max_hosts=int(str(payload["max_hosts"])),
            issued_at=InstallationIdentity._parse_datetime(
                payload["issued_at"], "license issued_at"
            ),
            not_before=InstallationIdentity._parse_datetime(
                payload["not_before"], "license not_before"
            ),
            expires_at=InstallationIdentity._parse_datetime(
                payload["expires_at"], "license expires_at"
            ),
            grace_days=int(str(payload["grace_days"])),
            authority_key_id=str(payload["authority_key_id"]),
        )
        signature = str(payload.get("signature", "")).strip()
        if not signature:
            raise ValidationError("license authority signature is required")
        try:
            base64.b64decode(signature, validate=True)
        except ValueError as exc:
            raise ValidationError("license authority signature is invalid") from exc
        return replace(entitlement, signature=signature)


@dataclass(frozen=True, slots=True)
class PersistedLicenseState:
    identity: InstallationIdentity
    entitlement: LicenseEntitlement | None
    activated_at: datetime | None
    last_seen_at: datetime | None

    def as_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity.as_dict(),
            "entitlement": self.entitlement.as_dict() if self.entitlement else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        try:
            identity_payload = payload["identity"]
            if not isinstance(identity_payload, dict):
                raise TypeError("identity must be an object")
            entitlement_payload = payload.get("entitlement")
            entitlement = None
            if entitlement_payload is not None:
                if not isinstance(entitlement_payload, dict):
                    raise TypeError("entitlement must be an object")
                entitlement = LicenseEntitlement.from_dict(entitlement_payload)
            activated_at = cls._optional_datetime(payload.get("activated_at"), "activated_at")
            last_seen_at = cls._optional_datetime(payload.get("last_seen_at"), "last_seen_at")
            return cls(
                identity=InstallationIdentity.from_dict(identity_payload),
                entitlement=entitlement,
                activated_at=activated_at,
                last_seen_at=last_seen_at,
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise LicenseStateCorruptedError(
                "persisted runtime license state is corrupted"
            ) from exc

    @staticmethod
    def _optional_datetime(value: object, label: str) -> datetime | None:
        if value is None or str(value).strip() == "":
            return None
        return InstallationIdentity._parse_datetime(value, label)


@dataclass(frozen=True, slots=True)
class RuntimeLicenseReport:
    edition: OpenInfraEdition
    enforcement_enabled: bool
    status: RuntimeLicenseStatus
    runtime_allowed: bool
    reason: str
    notification_level: LicenseNotificationLevel
    checked_at: datetime
    company_name: str | None = None
    installation_id: str | None = None
    license_id: str | None = None
    current_hosts: int = 0
    max_hosts: int | None = None
    expires_at: datetime | None = None
    grace_until: datetime | None = None
    days_until_expiry: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "edition": self.edition.value,
            "enforcement_enabled": self.enforcement_enabled,
            "status": self.status.value,
            "runtime_allowed": self.runtime_allowed,
            "reason": self.reason,
            "notification_level": self.notification_level.value,
            "checked_at": self.checked_at.isoformat(),
            "company_name": self.company_name,
            "installation_id": self.installation_id,
            "license_id": self.license_id,
            "current_hosts": self.current_hosts,
            "max_hosts": self.max_hosts,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "grace_until": self.grace_until.isoformat() if self.grace_until else None,
            "days_until_expiry": self.days_until_expiry,
        }
