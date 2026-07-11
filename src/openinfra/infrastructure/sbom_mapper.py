from __future__ import annotations

from datetime import datetime
from typing import Any

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.sbom import (
    ExposureContext,
    RiskFinding,
    SbomComparison,
    SbomComponent,
    SbomDocument,
    VulnerabilityRecord,
)


class SbomRecordMapper:
    @staticmethod
    def _datetime(value: object, field: str) -> datetime:
        try:
            return datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValidationError(f"invalid SBOM datetime: {field}") from exc

    @staticmethod
    def _mapping(value: object, field: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{field} must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @classmethod
    def component(cls, value: dict[str, Any]) -> SbomComponent:
        return SbomComponent.create(
            str(value["bom_ref"]),
            str(value["name"]),
            str(value["version"]),
            None if value.get("purl") is None else str(value["purl"]),
            None if value.get("supplier") is None else str(value["supplier"]),
            tuple(str(item) for item in value.get("licenses", [])),
            tuple(str(item) for item in value.get("hashes", [])),
        )

    @classmethod
    def document(cls, value: dict[str, Any]) -> SbomDocument:
        raw_components = value.get("components")
        if not isinstance(raw_components, list):
            raise ValidationError("SBOM components must be an array")
        components = tuple(
            cls.component(cls._mapping(item, "SBOM component")) for item in raw_components
        )
        return SbomDocument.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["application"]),
            str(value["release"]),
            str(value["environment"]),
            str(value["format"]),
            str(value["specification_version"]),
            str(value["source_name"]),
            None if value.get("source_uri") is None else str(value["source_uri"]),
            str(value["source_hash"]),
            int(value["document_version"]),
            None if value.get("serial_number") is None else str(value["serial_number"]),
            components,
            cls._mapping(value.get("metadata", {}), "SBOM metadata"),
            cls._datetime(value["imported_at"], "imported_at"),
        )

    @classmethod
    def vulnerability(cls, value: dict[str, Any]) -> VulnerabilityRecord:
        published = value.get("published_at")
        modified = value.get("modified_at")
        return VulnerabilityRecord.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            imported_at=cls._datetime(value["imported_at"], "imported_at"),
            cve_id=str(value["cve_id"]),
            component_purl=None
            if value.get("component_purl") is None
            else str(value["component_purl"]),
            component_name=str(value["component_name"]),
            component_version=str(value["component_version"]),
            cvss_score=str(value["cvss_score"]),
            known_exploited=bool(value["known_exploited"]),
            exploit_maturity=str(value["exploit_maturity"]),
            source_name=str(value["source_name"]),
            published_at=None if published is None else cls._datetime(published, "published_at"),
            modified_at=None if modified is None else cls._datetime(modified, "modified_at"),
            references=tuple(str(item) for item in value.get("references", [])),
            metadata=cls._mapping(value.get("metadata", {}), "vulnerability metadata"),
        )

    @classmethod
    def exposure(cls, value: dict[str, Any]) -> ExposureContext:
        return ExposureContext.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            updated_at=cls._datetime(value["updated_at"], "updated_at"),
            application=str(value["application"]),
            environment=str(value["environment"]),
            internet_exposed=bool(value["internet_exposed"]),
            flow_exposed=bool(value["flow_exposed"]),
            business_criticality=int(value["business_criticality"]),
            compensating_controls=tuple(
                str(item) for item in value.get("compensating_controls", [])
            ),
            asset_ids=tuple(str(item) for item in value.get("asset_ids", [])),
            service_ids=tuple(str(item) for item in value.get("service_ids", [])),
        )

    @classmethod
    def finding(cls, value: dict[str, Any]) -> RiskFinding:
        return RiskFinding.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["document_id"]),
            str(value["component_ref"]),
            str(value["component_name"]),
            str(value["component_version"]),
            None if value.get("component_purl") is None else str(value["component_purl"]),
            str(value["vulnerability_id"]),
            str(value["cve_id"]),
            str(value["contextual_score"]),
            str(value["priority"]),
            str(value["status"]),
            tuple(str(item) for item in value.get("reasons", [])),
            cls._datetime(value["generated_at"], "generated_at"),
        )

    @classmethod
    def comparison(cls, value: dict[str, Any]) -> SbomComparison:
        def mappings(key: str) -> tuple[dict[str, str], ...]:
            raw = value.get(key, [])
            if not isinstance(raw, list):
                raise ValidationError(f"SBOM comparison {key} must be an array")
            return tuple(
                {
                    str(item_key): str(item_value)
                    for item_key, item_value in cls._mapping(item, key).items()
                }
                for item in raw
            )

        return SbomComparison.restore(
            EntityId.from_value(str(value["id"])),
            TenantId.from_value(str(value["tenant_id"])),
            str(value["base_document_id"]),
            str(value["target_document_id"]),
            mappings("added"),
            mappings("removed"),
            mappings("changed"),
            str(value["input_digest"]),
            cls._datetime(value["generated_at"], "generated_at"),
        )
