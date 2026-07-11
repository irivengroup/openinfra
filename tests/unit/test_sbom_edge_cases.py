from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.sbom import (
    ExposureContext,
    FindingStatus,
    RiskAssessment,
    RiskFinding,
    RiskPriority,
    SbomComparison,
    SbomComponent,
    SbomDocument,
    SbomFormat,
    SbomValidator,
    VulnerabilityRecord,
)
from openinfra.infrastructure.sbom_mapper import SbomRecordMapper
from openinfra.infrastructure.sbom_parser import SbomPayloadParser

TENANT = TenantId.from_value("default")
NOW = datetime(2026, 7, 11, 12, tzinfo=UTC)


def _component(version: str = "1.0.0", name: str = "package") -> SbomComponent:
    return SbomComponent.create(
        f"pkg:pypi/{name}@{version}", name, version, f"pkg:pypi/{name}@{version}"
    )


def _document(version: str = "1.0.0", release: str = "r1") -> SbomDocument:
    return SbomDocument.create(
        TENANT,
        "app",
        release,
        "production",
        "cyclonedx",
        "1.6",
        "pytest",
        "https://example.invalid/sbom.json",
        SbomValidator.digest({"version": version, "release": release}),
        1,
        (_component(version),),
    )


def _vulnerability(**overrides: object) -> VulnerabilityRecord:
    values: dict[str, object] = {
        "tenant_id": TENANT,
        "cve_id": "CVE-2026-12345",
        "component_name": "package",
        "component_version": "1.0.0",
        "cvss_score": "7.5",
        "component_purl": "pkg:pypi/package@1.0.0",
        "published_at": NOW,
        "modified_at": NOW + timedelta(days=1),
        "references": ("https://example.invalid/CVE-2026-12345",),
    }
    values.update(overrides)
    return VulnerabilityRecord.create(**values)  # type: ignore[arg-type]


def test_sbom_enums_validator_and_uri_error_paths() -> None:
    assert SbomFormat.from_value("Cyclone-DX") is SbomFormat.CYCLONEDX
    assert FindingStatus.from_value("false_positive") is FindingStatus.FALSE_POSITIVE
    assert [RiskPriority.from_score(Decimal(value)) for value in ("3", "4", "7", "9")] == [
        RiskPriority.LOW,
        RiskPriority.MEDIUM,
        RiskPriority.HIGH,
        RiskPriority.CRITICAL,
    ]
    with pytest.raises(ValidationError, match="CycloneDX or SPDX"):
        SbomFormat.from_value("swid")
    with pytest.raises(ValidationError, match="unsupported"):
        FindingStatus.from_value("closed")
    with pytest.raises(ValidationError, match="safe characters"):
        SbomValidator.key("bad key", "key")
    with pytest.raises(ValidationError, match="SHA-256"):
        SbomValidator.sha256("abc")
    with pytest.raises(ValidationError, match="finite decimal"):
        SbomValidator.cvss("invalid")
    for value in ("NaN", "-1", "10.1"):
        with pytest.raises(ValidationError, match="between 0 and 10"):
            SbomValidator.cvss(value)
    assert SbomValidator.optional_text(" ", "optional") is None
    assert SbomValidator.uri(None) is None
    assert SbomValidator.uri("urn:uuid:1234") == "urn:uuid:1234"
    assert SbomValidator.uri("file:///tmp/sbom.json") == "file:///tmp/sbom.json"
    for value, message in (
        ("ftp://example.invalid/a", "must use"),
        ("https:///missing-host", "requires a host"),
        ("file:", "requires a path"),
        ("urn:", "requires a namespace"),
        ("https://example.invalid/white space", "invalid"),
    ):
        with pytest.raises(ValidationError, match=message):
            SbomValidator.uri(value)


def test_json_metadata_bounds_serialization_and_sensitive_keys() -> None:
    assert SbomValidator.json_object({"items": ({"ok": True},)}, "metadata") == {
        "items": [{"ok": True}]
    }
    with pytest.raises(ValidationError, match="JSON object"):
        SbomValidator.json_object([], "metadata")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="serializable"):
        SbomValidator.json_object({"value": object()}, "metadata")
    with pytest.raises(ValidationError, match="exceeds"):
        SbomValidator.json_object({"value": "x" * 128}, "metadata", maximum_bytes=32)
    with pytest.raises(ValidationError, match="sensitive key"):
        SbomValidator.json_object({"nested": [{"private-key": "x"}]}, "metadata")


def test_parser_rejects_malformed_oversized_and_invalid_component_payloads() -> None:
    with pytest.raises(ValidationError, match="valid UTF-8 JSON"):
        SbomPayloadParser.parse(b"\xff")
    with pytest.raises(ValidationError, match="valid UTF-8 JSON"):
        SbomPayloadParser.parse("{")
    with pytest.raises(ValidationError, match="root must be"):
        SbomPayloadParser.parse("[]")
    with pytest.raises(ValidationError, match="exceeds 10 MiB"):
        SbomPayloadParser.parse(b"x" * (SbomPayloadParser._MAX_BYTES + 1))
    with pytest.raises(ValidationError, match="unable to detect"):
        SbomPayloadParser.parse({"name": "unknown"})
    with pytest.raises(ValidationError, match="components must be an array"):
        SbomPayloadParser.parse({"bomFormat": "CycloneDX", "components": {}})
    with pytest.raises(ValidationError, match="component 0 must be an object"):
        SbomPayloadParser.parse({"bomFormat": "CycloneDX", "components": ["bad"]})
    with pytest.raises(ValidationError, match="packages must be an array"):
        SbomPayloadParser.parse({"spdxVersion": "SPDX-2.3", "packages": {}})
    with pytest.raises(ValidationError, match="package 0 must be an object"):
        SbomPayloadParser.parse({"spdxVersion": "SPDX-2.3", "packages": ["bad"]})


def test_parser_handles_optional_metadata_suppliers_licenses_hashes_and_fallbacks() -> None:
    parsed = SbomPayloadParser.parse(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "metadata": {"timestamp": "2026-07-11T00:00:00Z", "secret": "discarded"},
                "components": [
                    {
                        "name": "a",
                        "version": "1",
                        "supplier": {"name": "Vendor"},
                        "licenses": [
                            {"license": {"name": "Custom"}},
                            {"expression": "MIT OR Apache-2.0"},
                            "ignored",
                        ],
                        "hashes": [{"alg": "SHA-256", "content": "abc"}, {}],
                    },
                    {"name": "b", "supplier": "Supplier", "purl": "pkg:pypi/b@2"},
                ],
            }
        )
    )
    assert parsed.metadata == {"timestamp": "2026-07-11T00:00:00Z"}
    assert parsed.components[0].supplier == "Vendor"
    assert parsed.components[0].licenses == ("Custom", "MIT OR Apache-2.0")
    assert parsed.components[0].hashes == ("SHA-256:abc",)
    assert parsed.components[1].bom_ref == "pkg:pypi/b@2"
    assert SbomPayloadParser._optional(" ") is None
    assert SbomPayloadParser._metadata([]) == {}
    assert SbomPayloadParser._cyclonedx_licenses({}) == ()
    assert SbomPayloadParser._cyclonedx_hashes({}) == ()

    spdx = SbomPayloadParser.parse(
        {
            "spdxVersion": "SPDX-2.3",
            "documentNamespace": "https://example.invalid/spdx",
            "creationInfo": {"created": "2026-07-11T00:00:00Z", "comment": "discarded"},
            "packages": [
                {
                    "name": "a",
                    "versionInfo": "1",
                    "supplier": "Organization: Vendor",
                    "licenseConcluded": "NOASSERTION",
                    "licenseDeclared": "MIT",
                    "externalRefs": ["ignored", {"referenceType": "other"}],
                    "checksums": [{"algorithm": "SHA256", "checksumValue": "abc"}, {}],
                }
            ],
        }
    )
    assert spdx.serial_number == "https://example.invalid/spdx"
    assert spdx.components[0].purl is None
    assert spdx.components[0].licenses == ("MIT",)
    assert spdx.components[0].hashes == ("SHA256:abc",)
    assert SbomPayloadParser._spdx_purl({}) is None
    assert SbomPayloadParser._spdx_hashes({}) == ()


def test_document_vulnerability_exposure_and_comparison_invariants() -> None:
    component = _component()
    for version, components, message in (
        (0, (component,), "version must be positive"),
        (1, (), "at least one component"),
        (1, (component, component), "references must be unique"),
    ):
        with pytest.raises(ValidationError, match=message):
            SbomDocument.create(
                TENANT,
                "app",
                "r1",
                "prod",
                "cyclonedx",
                "1.6",
                "pytest",
                None,
                "a" * 64,
                version,
                components,
            )
    with pytest.raises(ValidationError, match="cannot precede"):
        _vulnerability(published_at=NOW, modified_at=NOW - timedelta(days=1))
    with pytest.raises(ValidationError, match="reference"):
        _vulnerability(references=("javascript:alert(1)",))
    with pytest.raises(ValidationError, match="business criticality"):
        ExposureContext.create(TENANT, "app", "prod", False, False, 0)

    base = _document("1.0.0", "r1")
    with pytest.raises(ValidationError, match="distinct"):
        SbomComparison.create(TENANT, base, base)
    other_tenant = TenantId.from_value("other")
    other = SbomDocument.create(
        other_tenant,
        "app",
        "r2",
        "prod",
        "cyclonedx",
        "1.6",
        "pytest",
        None,
        "b" * 64,
        1,
        (_component("2.0.0"),),
    )
    with pytest.raises(ValidationError, match="belong to the tenant"):
        SbomComparison.create(TENANT, base, other)


def test_risk_branches_restore_and_mapper_roundtrips() -> None:
    document = _document()
    component = document.components[0]
    vulnerability = _vulnerability(known_exploited=False, cvss_score="5")
    no_context_score, no_context_reasons = RiskAssessment.calculate(vulnerability, None)
    assert no_context_score == Decimal("4.5")
    assert "no exposure context" in " ".join(no_context_reasons)
    flow = ExposureContext.create(TENANT, "app", "production", False, True, 3)
    flow_score, flow_reasons = RiskAssessment.calculate(vulnerability, flow)
    assert flow_score > Decimal("5") and "reachable through" in " ".join(flow_reasons)
    finding = RiskFinding.create(TENANT, document, component, vulnerability, flow)
    assert SbomRecordMapper.finding(finding.as_dict()).id == finding.id
    with pytest.raises(ValidationError, match="priority does not match"):
        RiskFinding.restore(
            finding.id,
            TENANT,
            document.id.value,
            component.bom_ref,
            component.name,
            component.version,
            component.purl,
            vulnerability.id.value,
            vulnerability.cve_id,
            "9.5",
            "low",
            "open",
            ("reason",),
            NOW,
        )

    restored_document = SbomRecordMapper.document(document.as_dict())
    assert restored_document.id == document.id
    restored_vulnerability = SbomRecordMapper.vulnerability(vulnerability.as_dict())
    assert restored_vulnerability.id == vulnerability.id
    exposure = ExposureContext.create(TENANT, "app", "production", True, False, 5)
    assert SbomRecordMapper.exposure(exposure.as_dict()).id == exposure.id
    target = _document("2.0.0", "r2")
    comparison = SbomComparison.create(TENANT, document, target)
    assert SbomRecordMapper.comparison(comparison.as_dict()).id == comparison.id

    with pytest.raises(ValidationError, match="invalid SBOM datetime"):
        SbomRecordMapper._datetime("bad", "created_at")
    with pytest.raises(ValidationError, match="JSON object"):
        SbomRecordMapper._mapping([], "payload")
    with pytest.raises(ValidationError, match="components must be an array"):
        SbomRecordMapper.document({**document.as_dict(), "components": {}})
    with pytest.raises(ValidationError, match="added must be an array"):
        SbomRecordMapper.comparison({**comparison.as_dict(), "added": {}})


def test_additional_domain_restore_and_size_guards() -> None:
    with pytest.raises(ValidationError, match="must contain"):
        SbomValidator.text(" ", "value")
    component_without_purl = SbomComponent.create("component-ref", "Package", "1", None)
    assert component_without_purl.identity_key == "name:package"
    with pytest.raises(ValidationError, match="cannot exceed"):
        SbomDocument.create(
            TENANT,
            "app",
            "r1",
            "prod",
            "cyclonedx",
            "1.6",
            "pytest",
            None,
            "a" * 64,
            1,
            (component_without_purl,) * 100_001,
        )

    document = _document()
    vulnerability = _vulnerability()
    finding = RiskFinding.create(TENANT, document, document.components[0], vulnerability, None)
    with pytest.raises(ValidationError, match="priority is unsupported"):
        RiskFinding.restore(
            finding.id,
            TENANT,
            finding.document_id,
            finding.component_ref,
            finding.component_name,
            finding.component_version,
            finding.component_purl,
            finding.vulnerability_id,
            finding.cve_id,
            finding.contextual_score,
            "urgent",
            finding.status.value,
            finding.reasons,
            finding.generated_at,
        )
    comparison = SbomComparison.create(TENANT, document, _document("2.0.0", "r2"))
    with pytest.raises(ValidationError, match="distinct"):
        SbomComparison.restore(
            comparison.id,
            TENANT,
            document.id.value,
            document.id.value,
            comparison.added,
            comparison.removed,
            comparison.changed,
            comparison.input_digest,
            comparison.generated_at,
        )

    with pytest.raises(ValidationError, match="exceeds 10 MiB"):
        SbomPayloadParser.parse({"bomFormat": "CycloneDX", "padding": "x" * 10_500_000})
