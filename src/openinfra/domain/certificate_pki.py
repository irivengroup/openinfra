from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from urllib.parse import urlsplit

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceObjectKey


class CertificateLifecycle(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class CertificateSource(StrEnum):
    MANUAL = "manual"
    DISCOVERY = "discovery"
    IMPORT = "import"
    ACME = "acme"
    INTERNAL_PKI = "internal-pki"
    EXTERNAL_PKI = "external-pki"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"pki": "internal-pki", "external": "external-pki"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("certificate source is unsupported") from exc


class CertificateHealth(StrEnum):
    RETIRED = "retired"
    NOT_YET_VALID = "not-yet-valid"
    EXPIRED = "expired"
    CRITICAL = "critical"
    WARNING = "warning"
    HEALTHY = "healthy"


@dataclass(frozen=True, slots=True)
class CertificateMaterial:
    fingerprint_sha256: str
    serial_number: str
    subject_dn: str
    issuer_dn: str
    common_name: str | None
    san_dns: tuple[str, ...]
    san_ip: tuple[str, ...]
    san_email: tuple[str, ...]
    san_uri: tuple[str, ...]
    not_before: datetime
    not_after: datetime
    public_key_algorithm: str
    public_key_size: int | None
    signature_algorithm: str
    is_ca: bool

    @classmethod
    def create(
        cls,
        *,
        fingerprint_sha256: str,
        serial_number: str,
        subject_dn: str,
        issuer_dn: str,
        common_name: str | None,
        san_dns: tuple[str, ...],
        san_ip: tuple[str, ...],
        san_email: tuple[str, ...],
        san_uri: tuple[str, ...],
        not_before: datetime,
        not_after: datetime,
        public_key_algorithm: str,
        public_key_size: int | None,
        signature_algorithm: str,
        is_ca: bool,
    ) -> Self:
        fingerprint = CertificatePkiRules.fingerprint(fingerprint_sha256)
        serial = serial_number.strip().upper().removeprefix("0X")
        if not re.fullmatch(r"[0-9A-F]{1,128}", serial):
            raise ValidationError("certificate serial number must be hexadecimal")
        subject = CertificatePkiRules.bounded_text(subject_dn, "certificate subject DN", 1, 2_048)
        issuer = CertificatePkiRules.bounded_text(issuer_dn, "certificate issuer DN", 1, 2_048)
        normalized_common_name = CertificatePkiRules.optional_text(
            common_name, "certificate common name", 255
        )
        before = CertificatePkiRules.aware_datetime(not_before, "certificate not_before")
        after = CertificatePkiRules.aware_datetime(not_after, "certificate not_after")
        if after <= before:
            raise ValidationError("certificate not_after must be after not_before")
        algorithm = CertificatePkiRules.safe_token(
            public_key_algorithm, "certificate public key algorithm", 64
        )
        if public_key_size is not None and not 128 <= int(public_key_size) <= 65_536:
            raise ValidationError("certificate public key size must be between 128 and 65536")
        signature = CertificatePkiRules.safe_token(
            signature_algorithm, "certificate signature algorithm", 128
        )
        return cls(
            fingerprint_sha256=fingerprint,
            serial_number=serial,
            subject_dn=subject,
            issuer_dn=issuer,
            common_name=normalized_common_name,
            san_dns=CertificatePkiRules.dns_names(san_dns),
            san_ip=CertificatePkiRules.ip_addresses(san_ip),
            san_email=CertificatePkiRules.emails(san_email),
            san_uri=CertificatePkiRules.uris(san_uri),
            not_before=before,
            not_after=after,
            public_key_algorithm=algorithm,
            public_key_size=None if public_key_size is None else int(public_key_size),
            signature_algorithm=signature,
            is_ca=bool(is_ca),
        )

    def immutable_dict(self) -> dict[str, object]:
        return {
            "fingerprint_sha256": self.fingerprint_sha256,
            "serial_number": self.serial_number,
            "subject_dn": self.subject_dn,
            "issuer_dn": self.issuer_dn,
            "common_name": self.common_name,
            "san_dns": list(self.san_dns),
            "san_ip": list(self.san_ip),
            "san_email": list(self.san_email),
            "san_uri": list(self.san_uri),
            "not_before": self.not_before.isoformat(),
            "not_after": self.not_after.isoformat(),
            "public_key_algorithm": self.public_key_algorithm,
            "public_key_size": self.public_key_size,
            "signature_algorithm": self.signature_algorithm,
            "is_ca": self.is_ca,
        }


@dataclass(frozen=True, slots=True)
class CertificateAsset:
    id: EntityId
    tenant_id: TenantId
    material: CertificateMaterial
    chain_fingerprints: tuple[str, ...]
    owner: str
    environment: str
    source: CertificateSource
    object_key: SourceObjectKey | None
    lifecycle: CertificateLifecycle
    version: int
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        material: CertificateMaterial,
        chain_fingerprints: tuple[str, ...],
        owner: str,
        environment: str,
        source: str,
        object_key: str | None,
        actor: str,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            material=material,
            chain_fingerprints=chain_fingerprints,
            owner=owner,
            environment=environment,
            source=source,
            object_key=object_key,
            lifecycle=CertificateLifecycle.ACTIVE.value,
            version=1,
            created_by=actor,
            created_at=now,
            updated_by=actor,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        material: CertificateMaterial,
        chain_fingerprints: tuple[str, ...],
        owner: str,
        environment: str,
        source: str,
        object_key: str | None,
        lifecycle: str,
        version: int,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
    ) -> Self:
        chain = CertificatePkiRules.chain(chain_fingerprints, material.fingerprint_sha256)
        normalized_owner = CertificatePkiRules.bounded_text(owner, "certificate owner", 2, 255)
        normalized_environment = CertificatePkiRules.safe_token(
            environment, "certificate environment", 64
        )
        normalized_object_key = (
            None if object_key is None else SourceObjectKey.from_value(object_key)
        )
        try:
            normalized_lifecycle = CertificateLifecycle(lifecycle.strip().lower())
        except ValueError as exc:
            raise ValidationError("certificate lifecycle is unsupported") from exc
        if int(version) < 1:
            raise ValidationError("certificate version must be positive")
        return cls(
            id=id,
            tenant_id=tenant_id,
            material=material,
            chain_fingerprints=chain,
            owner=normalized_owner,
            environment=normalized_environment,
            source=CertificateSource.from_value(source),
            object_key=normalized_object_key,
            lifecycle=normalized_lifecycle,
            version=int(version),
            created_by=CertificatePkiRules.actor(created_by),
            created_at=CertificatePkiRules.aware_datetime(created_at, "certificate created_at"),
            updated_by=CertificatePkiRules.actor(updated_by),
            updated_at=CertificatePkiRules.aware_datetime(updated_at, "certificate updated_at"),
        )

    @property
    def fingerprint_sha256(self) -> str:
        return self.material.fingerprint_sha256

    def revise_governance(
        self,
        *,
        chain_fingerprints: tuple[str, ...],
        owner: str,
        environment: str,
        source: str,
        object_key: str | None,
        actor: str,
    ) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            material=self.material,
            chain_fingerprints=chain_fingerprints,
            owner=owner,
            environment=environment,
            source=source,
            object_key=object_key,
            lifecycle=CertificateLifecycle.ACTIVE.value,
            version=self.version + 1,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def retire(self, actor: str) -> Self:
        if self.lifecycle is CertificateLifecycle.RETIRED:
            return self
        return replace(
            self,
            lifecycle=CertificateLifecycle.RETIRED,
            version=self.version + 1,
            updated_by=CertificatePkiRules.actor(actor),
            updated_at=datetime.now(UTC),
        )

    def health(
        self,
        as_of: datetime,
        critical_days: int = 7,
        warning_days: int = 30,
    ) -> CertificateHealth:
        reference = CertificatePkiRules.aware_datetime(as_of, "certificate assessment date")
        if not 0 <= critical_days <= warning_days <= 3_650:
            raise ValidationError("certificate expiry thresholds are invalid")
        if self.lifecycle is CertificateLifecycle.RETIRED:
            return CertificateHealth.RETIRED
        if reference < self.material.not_before:
            return CertificateHealth.NOT_YET_VALID
        if reference >= self.material.not_after:
            return CertificateHealth.EXPIRED
        days = self.days_remaining(reference)
        if days <= critical_days:
            return CertificateHealth.CRITICAL
        if days <= warning_days:
            return CertificateHealth.WARNING
        return CertificateHealth.HEALTHY

    def days_remaining(self, as_of: datetime) -> int:
        reference = CertificatePkiRules.aware_datetime(as_of, "certificate assessment date")
        seconds = (self.material.not_after - reference).total_seconds()
        return int(seconds // 86_400)

    def matches_hostname(self, hostname: str) -> bool:
        normalized = CertificatePkiRules.hostname(hostname)
        try:
            ip = str(ipaddress.ip_address(normalized))
        except ValueError:
            candidates = self.material.san_dns or (
                () if self.material.common_name is None else (self.material.common_name.lower(),)
            )
            return any(
                CertificatePkiRules.dns_match(normalized, candidate) for candidate in candidates
            )
        return ip in self.material.san_ip

    def material_matches(self, material: CertificateMaterial) -> bool:
        return self.material.immutable_dict() == material.immutable_dict()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            **self.material.immutable_dict(),
            "chain_fingerprints": list(self.chain_fingerprints),
            "owner": self.owner,
            "environment": self.environment,
            "source": self.source.value,
            "object_key": None if self.object_key is None else self.object_key.value,
            "lifecycle": self.lifecycle.value,
            "version": self.version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CertificateEndpointObservation:
    id: EntityId
    tenant_id: TenantId
    idempotency_key: str
    protocol: str
    host: str
    port: int
    service: str
    certificate_fingerprint: str
    observed_at: datetime
    source: CertificateSource
    collector: str
    object_key: SourceObjectKey | None
    tls_version: str | None
    cipher: str | None
    received_at: datetime
    payload_fingerprint: str

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        idempotency_key: str,
        protocol: str,
        host: str,
        port: int,
        service: str,
        certificate_fingerprint: str,
        observed_at: datetime,
        source: str,
        collector: str,
        object_key: str | None,
        tls_version: str | None,
        cipher: str | None,
    ) -> Self:
        normalized_idempotency = CertificatePkiRules.safe_identifier(
            idempotency_key, "certificate endpoint idempotency key", 3, 128
        )
        normalized_protocol = CertificatePkiRules.safe_token(
            protocol, "certificate endpoint protocol", 32
        )
        normalized_host = CertificatePkiRules.hostname(host)
        normalized_port = int(port)
        if not 1 <= normalized_port <= 65_535:
            raise ValidationError("certificate endpoint port must be between 1 and 65535")
        normalized_service = CertificatePkiRules.bounded_text(
            service, "certificate endpoint service", 1, 128
        )
        fingerprint = CertificatePkiRules.fingerprint(certificate_fingerprint)
        timestamp = CertificatePkiRules.aware_datetime(
            observed_at, "certificate endpoint observed_at"
        )
        normalized_source = CertificateSource.from_value(source)
        normalized_collector = CertificatePkiRules.safe_identifier(
            collector, "certificate endpoint collector", 2, 128
        )
        normalized_object_key = (
            None if object_key is None else SourceObjectKey.from_value(object_key)
        )
        normalized_tls = CertificatePkiRules.optional_safe_token(tls_version, "TLS version", 32)
        normalized_cipher = CertificatePkiRules.optional_safe_token(cipher, "TLS cipher", 128)
        canonical = {
            "tenant_id": tenant_id.value,
            "idempotency_key": normalized_idempotency,
            "protocol": normalized_protocol,
            "host": normalized_host,
            "port": normalized_port,
            "service": normalized_service,
            "certificate_fingerprint": fingerprint,
            "observed_at": timestamp.isoformat(),
            "source": normalized_source.value,
            "collector": normalized_collector,
            "object_key": None if normalized_object_key is None else normalized_object_key.value,
            "tls_version": normalized_tls,
            "cipher": normalized_cipher,
        }
        digest = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            idempotency_key=normalized_idempotency,
            protocol=normalized_protocol,
            host=normalized_host,
            port=normalized_port,
            service=normalized_service,
            certificate_fingerprint=fingerprint,
            observed_at=timestamp,
            source=normalized_source,
            collector=normalized_collector,
            object_key=normalized_object_key,
            tls_version=normalized_tls,
            cipher=normalized_cipher,
            received_at=datetime.now(UTC),
            payload_fingerprint=digest,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        idempotency_key: str,
        protocol: str,
        host: str,
        port: int,
        service: str,
        certificate_fingerprint: str,
        observed_at: datetime,
        source: str,
        collector: str,
        object_key: str | None,
        tls_version: str | None,
        cipher: str | None,
        received_at: datetime,
        payload_fingerprint: str,
    ) -> Self:
        candidate = cls.create(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            protocol=protocol,
            host=host,
            port=port,
            service=service,
            certificate_fingerprint=certificate_fingerprint,
            observed_at=observed_at,
            source=source,
            collector=collector,
            object_key=object_key,
            tls_version=tls_version,
            cipher=cipher,
        )
        fingerprint = CertificatePkiRules.fingerprint(payload_fingerprint)
        if fingerprint != candidate.payload_fingerprint:
            raise ValidationError("certificate endpoint payload fingerprint is inconsistent")
        return replace(
            candidate,
            id=id,
            received_at=CertificatePkiRules.aware_datetime(
                received_at, "certificate endpoint received_at"
            ),
        )

    @property
    def endpoint(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{self.protocol}://{host}:{self.port}"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "idempotency_key": self.idempotency_key,
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "endpoint": self.endpoint,
            "service": self.service,
            "certificate_fingerprint": self.certificate_fingerprint,
            "observed_at": self.observed_at.isoformat(),
            "source": self.source.value,
            "collector": self.collector,
            "object_key": None if self.object_key is None else self.object_key.value,
            "tls_version": self.tls_version,
            "cipher": self.cipher,
            "received_at": self.received_at.isoformat(),
            "payload_fingerprint": self.payload_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class CertificateAssessment:
    certificate: CertificateAsset
    health: CertificateHealth
    days_remaining: int
    endpoint_count: int
    endpoints: tuple[str, ...]
    hostname_mismatch_count: int
    chain_complete: bool
    missing_chain_fingerprints: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "certificate": self.certificate.as_dict(),
            "health": self.health.value,
            "days_remaining": self.days_remaining,
            "endpoint_count": self.endpoint_count,
            "endpoints": list(self.endpoints),
            "hostname_mismatch_count": self.hostname_mismatch_count,
            "chain_complete": self.chain_complete,
            "missing_chain_fingerprints": list(self.missing_chain_fingerprints),
        }


@dataclass(frozen=True, slots=True)
class CertificateInventoryReport:
    as_of: datetime
    critical_days: int
    warning_days: int
    items: tuple[CertificateAssessment, ...]
    totals: dict[str, int]
    next_cursor: str | None
    truncated: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "as_of": self.as_of.isoformat(),
            "critical_days": self.critical_days,
            "warning_days": self.warning_days,
            "items": [item.as_dict() for item in self.items],
            "totals": dict(self.totals),
            "next_cursor": self.next_cursor,
            "truncated": self.truncated,
        }


class CertificatePkiRules:
    @staticmethod
    def fingerprint(value: str) -> str:
        normalized = value.strip().lower().replace(":", "")
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValidationError("certificate fingerprint must be a SHA-256 hex digest")
        return normalized

    @classmethod
    def chain(cls, values: tuple[str, ...], own_fingerprint: str) -> tuple[str, ...]:
        normalized = tuple(cls.fingerprint(item) for item in values)
        if len(normalized) > 16:
            raise ValidationError("certificate chain cannot exceed 16 certificates")
        if own_fingerprint in normalized:
            raise ValidationError("certificate chain cannot contain the certificate itself")
        if len(set(normalized)) != len(normalized):
            raise ValidationError("certificate chain cannot contain duplicates")
        return normalized

    @staticmethod
    def bounded_text(value: str, label: str, minimum: int, maximum: int) -> str:
        normalized = " ".join(value.strip().split())
        if not minimum <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain {minimum} to {maximum} characters")
        return normalized

    @staticmethod
    def optional_text(value: str | None, label: str, maximum: int) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        if normalized == "":
            return None
        if len(normalized) > maximum:
            raise ValidationError(f"{label} cannot exceed {maximum} characters")
        return normalized

    @staticmethod
    def safe_token(value: str, label: str, maximum: int) -> str:
        normalized = value.strip().lower().replace(" ", "-")
        if not re.fullmatch(rf"[a-z0-9][a-z0-9_.:+/-]{{0,{maximum - 1}}}", normalized):
            raise ValidationError(f"{label} is invalid")
        return normalized

    @classmethod
    def optional_safe_token(cls, value: str | None, label: str, maximum: int) -> str | None:
        if value is None or value.strip() == "":
            return None
        return cls.safe_token(value, label, maximum)

    @staticmethod
    def safe_identifier(value: str, label: str, minimum: int, maximum: int) -> str:
        normalized = value.strip()
        if not re.fullmatch(
            rf"[A-Za-z0-9][A-Za-z0-9_.:@/-]{{{minimum - 1},{maximum - 1}}}", normalized
        ):
            raise ValidationError(f"{label} is invalid")
        return normalized

    @classmethod
    def actor(cls, value: str) -> str:
        return cls.safe_identifier(value, "certificate actor", 2, 128)

    @staticmethod
    def aware_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def dns_names(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for value in values:
            normalized = value.strip().lower().rstrip(".")
            if normalized.startswith("*."):
                cls.hostname(normalized[2:])
            else:
                cls.hostname(normalized)
            if normalized not in result:
                result.append(normalized)
        return tuple(result)

    @staticmethod
    def ip_addresses(values: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for value in values:
            try:
                normalized = str(ipaddress.ip_address(value.strip()))
            except ValueError as exc:
                raise ValidationError("certificate SAN IP address is invalid") from exc
            if normalized not in result:
                result.append(normalized)
        return tuple(result)

    @staticmethod
    def emails(values: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for value in values:
            normalized = value.strip().lower()
            if not re.fullmatch(r"[^@\s]{1,128}@[^@\s]{1,190}", normalized):
                raise ValidationError("certificate SAN email address is invalid")
            if normalized not in result:
                result.append(normalized)
        return tuple(result)

    @staticmethod
    def uris(values: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for value in values:
            normalized = value.strip()
            parsed = urlsplit(normalized)
            if not parsed.scheme or len(normalized) > 2_048:
                raise ValidationError("certificate SAN URI is invalid")
            if normalized not in result:
                result.append(normalized)
        return tuple(result)

    @staticmethod
    def hostname(value: str) -> str:
        normalized = value.strip().lower().rstrip(".")
        try:
            return str(ipaddress.ip_address(normalized))
        except ValueError:
            pass
        try:
            ascii_name = normalized.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValidationError("certificate endpoint hostname is invalid") from exc
        if len(ascii_name) > 253 or not ascii_name:
            raise ValidationError("certificate endpoint hostname is invalid")
        labels = ascii_name.split(".")
        if any(
            not label
            or len(label) > 63
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        ):
            raise ValidationError("certificate endpoint hostname is invalid")
        return ascii_name

    @staticmethod
    def dns_match(hostname: str, pattern: str) -> bool:
        normalized_pattern = pattern.strip().lower().rstrip(".")
        if normalized_pattern.startswith("*."):
            suffix = normalized_pattern[2:]
            host_labels = hostname.split(".")
            suffix_labels = suffix.split(".")
            return len(host_labels) == len(suffix_labels) + 1 and host_labels[1:] == suffix_labels
        return hostname == normalized_pattern
