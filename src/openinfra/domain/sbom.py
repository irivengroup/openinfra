from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Self, cast
from urllib.parse import urlparse

from openinfra.domain.common import EntityId, TenantId, ValidationError


class SbomFormat(StrEnum):
    CYCLONEDX = "cyclonedx"
    SPDX = "spdx"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("-", "")
        aliases = {"cyclonedx": cls.CYCLONEDX, "spdx": cls.SPDX}
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValidationError("SBOM format must be CycloneDX or SPDX") from exc


class RiskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: Decimal) -> Self:
        if score >= Decimal("9"):
            return cls.CRITICAL
        if score >= Decimal("7"):
            return cls.HIGH
        if score >= Decimal("4"):
            return cls.MEDIUM
        return cls.LOW


class FindingStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    MITIGATED = "mitigated"
    FALSE_POSITIVE = "false-positive"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValidationError("finding status is unsupported") from exc


class SbomValidator:
    _SAFE_KEY = re.compile(r"[a-z0-9][a-z0-9_.:@/+~-]{0,255}")
    _CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,19}", re.IGNORECASE)
    _SHA256 = re.compile(r"[a-f0-9]{64}")
    _PURL = re.compile(r"pkg:[A-Za-z0-9.+-]+/[A-Za-z0-9._~%:/@+-]+(?:\?[^#\s]+)?(?:#[^\s]+)?")
    _SENSITIVE_KEY = re.compile(
        r"(?:^|[_\-.])(password|passwd|pwd|secret|token|credential|api[_-]?key|private[_-]?key)(?:$|[_\-.])",
        re.IGNORECASE,
    )

    @classmethod
    def text(cls, value: str, label: str, maximum: int = 512) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain 1 to {maximum} characters")
        return normalized

    @classmethod
    def optional_text(cls, value: str | None, label: str, maximum: int = 512) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.text(value, label, maximum)

    @classmethod
    def key(cls, value: str, label: str, maximum: int = 256) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if len(normalized) > maximum or not cls._SAFE_KEY.fullmatch(normalized):
            raise ValidationError(f"{label} must use 1 to {maximum} safe characters")
        return normalized

    @classmethod
    def sha256(cls, value: str, label: str = "sha256") -> str:
        normalized = value.strip().lower()
        if not cls._SHA256.fullmatch(normalized):
            raise ValidationError(f"{label} must be a SHA-256 hexadecimal digest")
        return normalized

    @classmethod
    def cve(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not cls._CVE.fullmatch(normalized):
            raise ValidationError("CVE identifier is invalid")
        return normalized

    @classmethod
    def uri(cls, value: str | None, label: str = "URI") -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if len(normalized) > 2048 or any(char.isspace() for char in normalized):
            raise ValidationError(f"{label} is invalid")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"https", "http", "file", "urn"}:
            raise ValidationError(f"{label} must use https, http, file or urn")
        if parsed.scheme in {"https", "http"} and not parsed.netloc:
            raise ValidationError(f"{label} requires a host")
        if parsed.scheme == "file" and not parsed.path:
            raise ValidationError(f"{label} requires a path")
        if parsed.scheme == "urn" and not parsed.path:
            raise ValidationError(f"{label} requires a namespace")
        return normalized

    @classmethod
    def purl(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if len(normalized) > 1024 or not cls._PURL.fullmatch(normalized):
            raise ValidationError("package URL is invalid")
        return normalized

    @classmethod
    def cvss(cls, value: Decimal | str | int | float) -> Decimal:
        try:
            normalized = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("CVSS score must be a finite decimal") from exc
        if not normalized.is_finite() or normalized < 0 or normalized > 10:
            raise ValidationError("CVSS score must be between 0 and 10")
        return normalized

    @staticmethod
    def aware_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def json_object(
        cls, value: dict[str, Any], label: str, maximum_bytes: int = 262_144
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        normalized = cast(dict[str, Any], cls._sanitize(value, label, "$"))
        try:
            encoded = json.dumps(
                normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{label} must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > maximum_bytes:
            raise ValidationError(f"{label} exceeds {maximum_bytes} bytes")
        return normalized

    @classmethod
    def _sanitize(cls, value: Any, label: str, path: str) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key, item in value.items():
                key = str(raw_key)
                if cls._SENSITIVE_KEY.search(key):
                    raise ValidationError(f"{label} contains a sensitive key at {path}.{key}")
                result[key] = cls._sanitize(item, label, f"{path}.{key}")
            return result
        if isinstance(value, (list, tuple)):
            return [
                cls._sanitize(item, label, f"{path}[{index}]") for index, item in enumerate(value)
            ]
        return value

    @staticmethod
    def digest(payload: object) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SbomComponent:
    bom_ref: str
    name: str
    version: str
    purl: str | None
    supplier: str | None
    licenses: tuple[str, ...]
    hashes: tuple[str, ...]

    @classmethod
    def create(
        cls,
        bom_ref: str,
        name: str,
        version: str,
        purl: str | None = None,
        supplier: str | None = None,
        licenses: tuple[str, ...] = (),
        hashes: tuple[str, ...] = (),
    ) -> Self:
        normalized_licenses = tuple(
            sorted({SbomValidator.text(item, "license", 255) for item in licenses if item.strip()})
        )
        normalized_hashes = tuple(
            sorted(
                {SbomValidator.text(item, "component hash", 255) for item in hashes if item.strip()}
            )
        )
        return cls(
            SbomValidator.text(bom_ref, "component reference", 512),
            SbomValidator.text(name, "component name", 255),
            SbomValidator.text(version or "unknown", "component version", 255),
            SbomValidator.purl(purl),
            SbomValidator.optional_text(supplier, "component supplier", 255),
            normalized_licenses,
            normalized_hashes,
        )

    @property
    def identity_key(self) -> str:
        if self.purl is None:
            return f"name:{self.name.lower()}"
        base = self.purl.split("?", 1)[0].split("#", 1)[0]
        package_path, separator, _version = base.rpartition("@")
        return package_path if separator else base

    def as_dict(self) -> dict[str, object]:
        return {
            "bom_ref": self.bom_ref,
            "name": self.name,
            "version": self.version,
            "purl": self.purl,
            "supplier": self.supplier,
            "licenses": list(self.licenses),
            "hashes": list(self.hashes),
        }


@dataclass(frozen=True, slots=True)
class ParsedSbom:
    format: SbomFormat
    specification_version: str
    serial_number: str | None
    source_hash: str
    components: tuple[SbomComponent, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SbomDocument:
    id: EntityId
    tenant_id: TenantId
    application: str
    release: str
    environment: str
    format: SbomFormat
    specification_version: str
    source_name: str
    source_uri: str | None
    source_hash: str
    document_version: int
    serial_number: str | None
    component_count: int
    components: tuple[SbomComponent, ...]
    metadata: dict[str, Any]
    imported_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        application: str,
        release: str,
        environment: str,
        format: str,
        specification_version: str,
        source_name: str,
        source_uri: str | None,
        source_hash: str,
        document_version: int,
        components: tuple[SbomComponent, ...],
        serial_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Self:
        if not 1 <= document_version <= 2_147_483_647:
            raise ValidationError("SBOM document version must be positive")
        if not components:
            raise ValidationError("SBOM must contain at least one component")
        if len(components) > 100_000:
            raise ValidationError("SBOM cannot exceed 100000 components")
        references = [item.bom_ref for item in components]
        if len(set(references)) != len(references):
            raise ValidationError("SBOM component references must be unique")
        return cls(
            EntityId.new(),
            tenant_id,
            SbomValidator.key(application, "application", 128),
            SbomValidator.text(release, "release", 128),
            SbomValidator.key(environment, "environment", 64),
            SbomFormat.from_value(format),
            SbomValidator.text(specification_version, "specification version", 32),
            SbomValidator.text(source_name, "source name", 255),
            SbomValidator.uri(source_uri, "source URI"),
            SbomValidator.sha256(source_hash, "source hash"),
            document_version,
            SbomValidator.optional_text(serial_number, "serial number", 512),
            len(components),
            components,
            SbomValidator.json_object(metadata or {}, "SBOM metadata"),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        application: str,
        release: str,
        environment: str,
        format: str,
        specification_version: str,
        source_name: str,
        source_uri: str | None,
        source_hash: str,
        document_version: int,
        serial_number: str | None,
        components: tuple[SbomComponent, ...],
        metadata: dict[str, Any],
        imported_at: datetime,
    ) -> Self:
        created = cls.create(
            tenant_id,
            application,
            release,
            environment,
            format,
            specification_version,
            source_name,
            source_uri,
            source_hash,
            document_version,
            components,
            serial_number,
            metadata,
        )
        return cls(
            id,
            created.tenant_id,
            created.application,
            created.release,
            created.environment,
            created.format,
            created.specification_version,
            created.source_name,
            created.source_uri,
            created.source_hash,
            created.document_version,
            created.serial_number,
            created.component_count,
            created.components,
            created.metadata,
            SbomValidator.aware_datetime(imported_at, "imported_at"),
        )

    @property
    def fingerprint(self) -> str:
        return SbomValidator.digest(
            {
                "tenant_id": self.tenant_id.value,
                "application": self.application,
                "release": self.release,
                "environment": self.environment,
                "source_hash": self.source_hash,
            }
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "application": self.application,
            "release": self.release,
            "environment": self.environment,
            "format": self.format.value,
            "specification_version": self.specification_version,
            "source_name": self.source_name,
            "source_uri": self.source_uri,
            "source_hash": self.source_hash,
            "document_version": self.document_version,
            "serial_number": self.serial_number,
            "component_count": self.component_count,
            "components": [item.as_dict() for item in self.components],
            "metadata": self.metadata,
            "fingerprint": self.fingerprint,
            "imported_at": self.imported_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class VulnerabilityRecord:
    id: EntityId
    tenant_id: TenantId
    cve_id: str
    component_purl: str | None
    component_name: str
    component_version: str
    cvss_score: Decimal
    known_exploited: bool
    exploit_maturity: str
    source_name: str
    published_at: datetime | None
    modified_at: datetime | None
    references: tuple[str, ...]
    metadata: dict[str, Any]
    imported_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        cve_id: str,
        component_name: str,
        component_version: str,
        cvss_score: Decimal | str | int | float,
        component_purl: str | None = None,
        known_exploited: bool = False,
        exploit_maturity: str = "unknown",
        source_name: str = "external-scanner",
        published_at: datetime | None = None,
        modified_at: datetime | None = None,
        references: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Self:
        normalized_published = (
            None
            if published_at is None
            else SbomValidator.aware_datetime(published_at, "published_at")
        )
        normalized_modified = (
            None
            if modified_at is None
            else SbomValidator.aware_datetime(modified_at, "modified_at")
        )
        if (
            normalized_published
            and normalized_modified
            and normalized_modified < normalized_published
        ):
            raise ValidationError("vulnerability modified_at cannot precede published_at")
        return cls(
            EntityId.new(),
            tenant_id,
            SbomValidator.cve(cve_id),
            SbomValidator.purl(component_purl),
            SbomValidator.text(component_name, "component name", 255),
            SbomValidator.text(component_version or "unknown", "component version", 255),
            SbomValidator.cvss(cvss_score),
            bool(known_exploited),
            SbomValidator.key(exploit_maturity, "exploit maturity", 64),
            SbomValidator.text(source_name, "vulnerability source", 255),
            normalized_published,
            normalized_modified,
            tuple(
                sorted(
                    normalized
                    for item in references
                    if item.strip()
                    if (normalized := SbomValidator.uri(item, "vulnerability reference"))
                    is not None
                )
            ),
            SbomValidator.json_object(metadata or {}, "vulnerability metadata"),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls, id: EntityId, tenant_id: TenantId, imported_at: datetime, **values: Any
    ) -> Self:
        created = cls.create(tenant_id=tenant_id, **values)
        return cls(
            id,
            created.tenant_id,
            created.cve_id,
            created.component_purl,
            created.component_name,
            created.component_version,
            created.cvss_score,
            created.known_exploited,
            created.exploit_maturity,
            created.source_name,
            created.published_at,
            created.modified_at,
            created.references,
            created.metadata,
            SbomValidator.aware_datetime(imported_at, "imported_at"),
        )

    @property
    def identity_key(self) -> str:
        component = self.component_purl or f"{self.component_name.lower()}@{self.component_version}"
        return f"{self.cve_id}:{component}"

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "cve_id": self.cve_id,
            "component_purl": self.component_purl,
            "component_name": self.component_name,
            "component_version": self.component_version,
            "cvss_score": str(self.cvss_score),
            "known_exploited": self.known_exploited,
            "exploit_maturity": self.exploit_maturity,
            "source_name": self.source_name,
            "published_at": None if self.published_at is None else self.published_at.isoformat(),
            "modified_at": None if self.modified_at is None else self.modified_at.isoformat(),
            "references": list(self.references),
            "metadata": self.metadata,
            "identity_key": self.identity_key,
            "imported_at": self.imported_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ExposureContext:
    id: EntityId
    tenant_id: TenantId
    application: str
    environment: str
    internet_exposed: bool
    flow_exposed: bool
    business_criticality: int
    compensating_controls: tuple[str, ...]
    asset_ids: tuple[str, ...]
    service_ids: tuple[str, ...]
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        application: str,
        environment: str,
        internet_exposed: bool,
        flow_exposed: bool,
        business_criticality: int,
        compensating_controls: tuple[str, ...] = (),
        asset_ids: tuple[str, ...] = (),
        service_ids: tuple[str, ...] = (),
    ) -> Self:
        if not 1 <= business_criticality <= 5:
            raise ValidationError("business criticality must be between 1 and 5")
        return cls(
            EntityId.new(),
            tenant_id,
            SbomValidator.key(application, "application", 128),
            SbomValidator.key(environment, "environment", 64),
            bool(internet_exposed),
            bool(flow_exposed),
            business_criticality,
            tuple(
                sorted(
                    {
                        SbomValidator.text(item, "compensating control", 255)
                        for item in compensating_controls
                        if item.strip()
                    }
                )
            ),
            tuple(
                sorted(
                    {
                        SbomValidator.text(item, "asset id", 255)
                        for item in asset_ids
                        if item.strip()
                    }
                )
            ),
            tuple(
                sorted(
                    {
                        SbomValidator.text(item, "service id", 255)
                        for item in service_ids
                        if item.strip()
                    }
                )
            ),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls, id: EntityId, tenant_id: TenantId, updated_at: datetime, **values: Any
    ) -> Self:
        created = cls.create(tenant_id=tenant_id, **values)
        return cls(
            id,
            created.tenant_id,
            created.application,
            created.environment,
            created.internet_exposed,
            created.flow_exposed,
            created.business_criticality,
            created.compensating_controls,
            created.asset_ids,
            created.service_ids,
            SbomValidator.aware_datetime(updated_at, "updated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "application": self.application,
            "environment": self.environment,
            "internet_exposed": self.internet_exposed,
            "flow_exposed": self.flow_exposed,
            "business_criticality": self.business_criticality,
            "compensating_controls": list(self.compensating_controls),
            "asset_ids": list(self.asset_ids),
            "service_ids": list(self.service_ids),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RiskFinding:
    id: EntityId
    tenant_id: TenantId
    document_id: str
    component_ref: str
    component_name: str
    component_version: str
    component_purl: str | None
    vulnerability_id: str
    cve_id: str
    contextual_score: Decimal
    priority: RiskPriority
    status: FindingStatus
    reasons: tuple[str, ...]
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        document: SbomDocument,
        component: SbomComponent,
        vulnerability: VulnerabilityRecord,
        exposure: ExposureContext | None,
    ) -> Self:
        score, reasons = RiskAssessment.calculate(vulnerability, exposure)
        return cls(
            EntityId.new(),
            tenant_id,
            document.id.value,
            component.bom_ref,
            component.name,
            component.version,
            component.purl,
            vulnerability.id.value,
            vulnerability.cve_id,
            score,
            RiskPriority.from_score(score),
            FindingStatus.OPEN,
            reasons,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        document_id: str,
        component_ref: str,
        component_name: str,
        component_version: str,
        component_purl: str | None,
        vulnerability_id: str,
        cve_id: str,
        contextual_score: Decimal | str,
        priority: str,
        status: str,
        reasons: tuple[str, ...],
        generated_at: datetime,
    ) -> Self:
        score = SbomValidator.cvss(contextual_score)
        try:
            normalized_priority = RiskPriority(priority)
        except ValueError as exc:
            raise ValidationError("risk finding priority is unsupported") from exc
        if normalized_priority is not RiskPriority.from_score(score):
            raise ValidationError("risk finding priority does not match contextual score")
        return cls(
            id,
            tenant_id,
            EntityId.from_value(document_id).value,
            SbomValidator.text(component_ref, "component reference", 512),
            SbomValidator.text(component_name, "component name", 255),
            SbomValidator.text(component_version, "component version", 255),
            SbomValidator.purl(component_purl),
            EntityId.from_value(vulnerability_id).value,
            SbomValidator.cve(cve_id),
            score,
            normalized_priority,
            FindingStatus.from_value(status),
            tuple(SbomValidator.text(item, "risk reason", 512) for item in reasons),
            SbomValidator.aware_datetime(generated_at, "generated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "document_id": self.document_id,
            "component_ref": self.component_ref,
            "component_name": self.component_name,
            "component_version": self.component_version,
            "component_purl": self.component_purl,
            "vulnerability_id": self.vulnerability_id,
            "cve_id": self.cve_id,
            "contextual_score": str(self.contextual_score),
            "priority": self.priority.value,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SbomComparison:
    id: EntityId
    tenant_id: TenantId
    base_document_id: str
    target_document_id: str
    added: tuple[dict[str, str], ...]
    removed: tuple[dict[str, str], ...]
    changed: tuple[dict[str, str], ...]
    input_digest: str
    generated_at: datetime

    @classmethod
    def create(cls, tenant_id: TenantId, base: SbomDocument, target: SbomDocument) -> Self:
        if base.tenant_id != tenant_id or target.tenant_id != tenant_id:
            raise ValidationError("SBOM comparison documents must belong to the tenant")
        if base.id == target.id:
            raise ValidationError("SBOM comparison requires two distinct documents")
        base_items = {item.identity_key: item for item in base.components}
        target_items = {item.identity_key: item for item in target.components}
        added = tuple(
            {"identity": key, "name": target_items[key].name, "version": target_items[key].version}
            for key in sorted(target_items.keys() - base_items.keys())
        )
        removed = tuple(
            {"identity": key, "name": base_items[key].name, "version": base_items[key].version}
            for key in sorted(base_items.keys() - target_items.keys())
        )
        changed = tuple(
            {
                "identity": key,
                "name": target_items[key].name,
                "from_version": base_items[key].version,
                "to_version": target_items[key].version,
            }
            for key in sorted(base_items.keys() & target_items.keys())
            if base_items[key].version != target_items[key].version
        )
        digest = SbomValidator.digest(
            {
                "base_document_id": base.id.value,
                "target_document_id": target.id.value,
                "base_hash": base.source_hash,
                "target_hash": target.source_hash,
            }
        )
        return cls(
            EntityId.new(),
            tenant_id,
            base.id.value,
            target.id.value,
            added,
            removed,
            changed,
            digest,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        base_document_id: str,
        target_document_id: str,
        added: tuple[dict[str, str], ...],
        removed: tuple[dict[str, str], ...],
        changed: tuple[dict[str, str], ...],
        input_digest: str,
        generated_at: datetime,
    ) -> Self:
        normalized_base = EntityId.from_value(base_document_id).value
        normalized_target = EntityId.from_value(target_document_id).value
        if normalized_base == normalized_target:
            raise ValidationError("SBOM comparison requires two distinct documents")
        return cls(
            id,
            tenant_id,
            normalized_base,
            normalized_target,
            tuple(dict(item) for item in added),
            tuple(dict(item) for item in removed),
            tuple(dict(item) for item in changed),
            SbomValidator.sha256(input_digest, "comparison input digest"),
            SbomValidator.aware_datetime(generated_at, "generated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "base_document_id": self.base_document_id,
            "target_document_id": self.target_document_id,
            "added": list(self.added),
            "removed": list(self.removed),
            "changed": list(self.changed),
            "summary": {
                "added": len(self.added),
                "removed": len(self.removed),
                "changed": len(self.changed),
            },
            "input_digest": self.input_digest,
            "generated_at": self.generated_at.isoformat(),
        }


class RiskAssessment:
    @classmethod
    def calculate(
        cls, vulnerability: VulnerabilityRecord, exposure: ExposureContext | None
    ) -> tuple[Decimal, tuple[str, ...]]:
        multiplier = Decimal("1")
        reasons: list[str] = [f"base CVSS {vulnerability.cvss_score}"]
        if vulnerability.known_exploited:
            multiplier *= Decimal("1.20")
            reasons.append("known exploited vulnerability")
        if exposure is None:
            multiplier *= Decimal("0.90")
            reasons.append("no exposure context; conservative internal assumption")
        else:
            if exposure.internet_exposed:
                multiplier *= Decimal("1.30")
                reasons.append("internet exposed")
            elif exposure.flow_exposed:
                multiplier *= Decimal("1.15")
                reasons.append("reachable through declared or observed flows")
            criticality_factor = Decimal("0.8") + Decimal(exposure.business_criticality) * Decimal(
                "0.1"
            )
            multiplier *= criticality_factor
            reasons.append(f"business criticality {exposure.business_criticality}/5")
            if exposure.compensating_controls:
                reduction = min(
                    Decimal("0.30"), Decimal(len(exposure.compensating_controls)) * Decimal("0.05")
                )
                multiplier *= Decimal("1") - reduction
                reasons.append(f"compensating controls reduce score by {reduction * 100}%")
        score = min(Decimal("10.0"), vulnerability.cvss_score * multiplier)
        return score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), tuple(reasons)
