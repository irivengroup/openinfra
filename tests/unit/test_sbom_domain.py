from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from openinfra.domain.common import TenantId, ValidationError
from openinfra.domain.sbom import (
    ExposureContext,
    RiskAssessment,
    SbomComponent,
    SbomDocument,
    SbomFormat,
    SbomValidator,
    VulnerabilityRecord,
)
from openinfra.infrastructure.sbom_parser import SbomPayloadParser


def test_cyclonedx_and_spdx_are_parsed_and_normalized() -> None:
    cyclone = SbomPayloadParser.parse(
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "serialNumber": "urn:uuid:test",
            "components": [
                {
                    "bom-ref": "pkg:pypi/requests@2.32.0",
                    "name": "requests",
                    "version": "2.32.0",
                    "purl": "pkg:pypi/requests@2.32.0",
                    "licenses": [{"license": {"id": "Apache-2.0"}}],
                }
            ],
        }
    )
    assert cyclone.format is SbomFormat.CYCLONEDX
    assert cyclone.components[0].licenses == ("Apache-2.0",)
    spdx = SbomPayloadParser.parse(
        {
            "spdxVersion": "SPDX-2.3",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": "openinfra",
            "packages": [
                {
                    "SPDXID": "SPDXRef-Package-requests",
                    "name": "requests",
                    "versionInfo": "2.32.0",
                    "licenseDeclared": "Apache-2.0",
                    "externalRefs": [
                        {
                            "referenceCategory": "PACKAGE-MANAGER",
                            "referenceType": "purl",
                            "referenceLocator": "pkg:pypi/requests@2.32.0",
                        }
                    ],
                }
            ],
        }
    )
    assert spdx.format is SbomFormat.SPDX
    assert spdx.components[0].purl == "pkg:pypi/requests@2.32.0"


def test_sbom_document_and_contextual_risk_are_deterministic() -> None:
    tenant = TenantId.from_value("default")
    component = SbomComponent.create(
        "pkg:pypi/requests@2.32.0",
        "requests",
        "2.32.0",
        "pkg:pypi/requests@2.32.0",
    )
    document = SbomDocument.create(
        tenant,
        "OpenInfra",
        "0.29.99",
        "production",
        "cyclonedx",
        "1.6",
        "ci",
        None,
        "a" * 64,
        1,
        (component,),
    )
    assert document.component_count == 1
    assert len(document.fingerprint) == 64
    vulnerability = VulnerabilityRecord.create(
        tenant,
        "CVE-2026-12345",
        "requests",
        "2.32.0",
        "8.2",
        "pkg:pypi/requests@2.32.0",
        True,
        "weaponized",
    )
    exposure = ExposureContext.create(
        tenant,
        "openinfra",
        "production",
        True,
        True,
        5,
        ("waf", "network-segmentation"),
    )
    score, reasons = RiskAssessment.calculate(vulnerability, exposure)
    assert score == Decimal("10.0")
    assert "internet exposed" in reasons
    assert any("compensating controls" in item for item in reasons)


def test_sbom_validation_rejects_secrets_invalid_identifiers_and_naive_dates() -> None:
    with pytest.raises(ValidationError, match="sensitive key"):
        SbomValidator.json_object({"nested": {"api_token": "x"}}, "metadata")
    with pytest.raises(ValidationError, match="CVE identifier"):
        SbomValidator.cve("GHSA-invalid")
    with pytest.raises(ValidationError, match="package URL"):
        SbomValidator.purl("https://example.invalid/package")
    tenant = TenantId.from_value("default")
    with pytest.raises(ValidationError, match="timezone-aware"):
        VulnerabilityRecord.create(
            tenant,
            "CVE-2026-12345",
            "requests",
            "2.32.0",
            "8.2",
            published_at=datetime(2026, 1, 1),
        )
    assert SbomValidator.aware_datetime(datetime(2026, 1, 1, tzinfo=UTC), "date").tzinfo
