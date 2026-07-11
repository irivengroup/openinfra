from __future__ import annotations

import hashlib
import json
from typing import Any

from openinfra.application.ports import SbomPayloadParserPort
from openinfra.domain.common import ValidationError
from openinfra.domain.sbom import ParsedSbom, SbomComponent, SbomFormat, SbomValidator


class SbomPayloadParser(SbomPayloadParserPort):
    _MAX_BYTES = 10 * 1024 * 1024

    @classmethod
    def parse(cls, payload: bytes | str | dict[str, Any]) -> ParsedSbom:
        raw_bytes, document = cls._decode(payload)
        detected = cls._detect_format(document)
        if detected is SbomFormat.CYCLONEDX:
            components = cls._parse_cyclonedx(document)
            spec = str(document.get("specVersion", "unknown"))
            serial = cls._optional(document.get("serialNumber"))
            metadata = cls._metadata(document.get("metadata"))
        else:
            components = cls._parse_spdx(document)
            spec = str(document.get("spdxVersion", "unknown"))
            serial = cls._optional(document.get("documentNamespace"))
            metadata = {
                "name": document.get("name"),
                "data_license": document.get("dataLicense"),
                "creation_info": cls._metadata(document.get("creationInfo")),
            }
        return ParsedSbom(
            detected,
            SbomValidator.text(spec, "specification version", 32),
            serial,
            hashlib.sha256(raw_bytes).hexdigest(),
            components,
            SbomValidator.json_object(metadata, "SBOM metadata"),
        )

    @classmethod
    def _decode(cls, payload: bytes | str | dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
        if isinstance(payload, dict):
            document = {str(key): value for key, value in payload.items()}
            raw = json.dumps(
                document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        else:
            raw = payload.encode("utf-8") if isinstance(payload, str) else payload
            if len(raw) > cls._MAX_BYTES:
                raise ValidationError("SBOM payload exceeds 10 MiB")
            try:
                decoded = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValidationError("SBOM payload must be valid UTF-8 JSON") from exc
            if not isinstance(decoded, dict):
                raise ValidationError("SBOM root must be a JSON object")
            document = {str(key): value for key, value in decoded.items()}
        if len(raw) > cls._MAX_BYTES:
            raise ValidationError("SBOM payload exceeds 10 MiB")
        return raw, document

    @staticmethod
    def _detect_format(document: dict[str, Any]) -> SbomFormat:
        if str(document.get("bomFormat", "")).lower() == "cyclonedx":
            return SbomFormat.CYCLONEDX
        if str(document.get("spdxVersion", "")).upper().startswith("SPDX-"):
            return SbomFormat.SPDX
        raise ValidationError("unable to detect CycloneDX or SPDX format")

    @classmethod
    def _parse_cyclonedx(cls, document: dict[str, Any]) -> tuple[SbomComponent, ...]:
        raw_components = document.get("components")
        if not isinstance(raw_components, list):
            raise ValidationError("CycloneDX components must be an array")
        components: list[SbomComponent] = []
        for index, raw in enumerate(raw_components):
            if not isinstance(raw, dict):
                raise ValidationError(f"CycloneDX component {index} must be an object")
            name = str(raw.get("name", "")).strip()
            version = str(raw.get("version", "unknown"))
            reference = str(raw.get("bom-ref") or raw.get("purl") or f"component-{index}")
            supplier = cls._cyclonedx_supplier(raw.get("supplier"))
            licenses = cls._cyclonedx_licenses(raw.get("licenses"))
            hashes = cls._cyclonedx_hashes(raw.get("hashes"))
            components.append(
                SbomComponent.create(
                    reference,
                    name,
                    version,
                    cls._optional(raw.get("purl")),
                    supplier,
                    licenses,
                    hashes,
                )
            )
        return tuple(components)

    @classmethod
    def _parse_spdx(cls, document: dict[str, Any]) -> tuple[SbomComponent, ...]:
        raw_packages = document.get("packages")
        if not isinstance(raw_packages, list):
            raise ValidationError("SPDX packages must be an array")
        components: list[SbomComponent] = []
        for index, raw in enumerate(raw_packages):
            if not isinstance(raw, dict):
                raise ValidationError(f"SPDX package {index} must be an object")
            purl = cls._spdx_purl(raw.get("externalRefs"))
            licenses = tuple(
                item
                for item in (
                    cls._optional(raw.get("licenseConcluded")),
                    cls._optional(raw.get("licenseDeclared")),
                )
                if item and item not in {"NOASSERTION", "NONE"}
            )
            hashes = cls._spdx_hashes(raw.get("checksums"))
            components.append(
                SbomComponent.create(
                    str(raw.get("SPDXID") or purl or f"SPDXRef-Package-{index}"),
                    str(raw.get("name", "")),
                    str(raw.get("versionInfo", "unknown")),
                    purl,
                    cls._optional(raw.get("supplier")),
                    licenses,
                    hashes,
                )
            )
        return tuple(components)

    @staticmethod
    def _optional(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @classmethod
    def _metadata(cls, value: object) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        allowed = {
            "timestamp",
            "authors",
            "tools",
            "component",
            "name",
            "created",
            "creators",
            "licenseListVersion",
        }
        return {str(key): item for key, item in value.items() if str(key) in allowed}

    @classmethod
    def _cyclonedx_supplier(cls, value: object) -> str | None:
        if isinstance(value, dict):
            return cls._optional(value.get("name"))
        return cls._optional(value)

    @classmethod
    def _cyclonedx_licenses(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        result: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            license_value = item.get("license")
            if isinstance(license_value, dict):
                name = cls._optional(license_value.get("id")) or cls._optional(
                    license_value.get("name")
                )
                if name:
                    result.append(name)
            expression = cls._optional(item.get("expression"))
            if expression:
                result.append(expression)
        return tuple(result)

    @classmethod
    def _cyclonedx_hashes(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(
            f"{item.get('alg')}:{item.get('content')}"
            for item in value
            if isinstance(item, dict) and item.get("alg") and item.get("content")
        )

    @classmethod
    def _spdx_purl(cls, value: object) -> str | None:
        if not isinstance(value, list):
            return None
        for item in value:
            if not isinstance(item, dict):
                continue
            category = str(item.get("referenceCategory", "")).upper()
            reference_type = str(item.get("referenceType", "")).lower()
            locator = cls._optional(item.get("referenceLocator"))
            if category == "PACKAGE-MANAGER" and reference_type == "purl" and locator:
                return locator
        return None

    @staticmethod
    def _spdx_hashes(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(
            f"{item.get('algorithm')}:{item.get('checksumValue')}"
            for item in value
            if isinstance(item, dict) and item.get("algorithm") and item.get("checksumValue")
        )
