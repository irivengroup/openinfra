from __future__ import annotations

import json
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.sbom_services import (
    AssessSbomRiskCommand,
    CompareSbomsCommand,
    ExportSbomRiskCommand,
    GetExposureCommand,
    GetSbomCommand,
    GetSbomComparisonCommand,
    ImportSbomCommand,
    ImportVulnerabilityCommand,
    ListExposuresCommand,
    ListRiskFindingsCommand,
    ListSbomComparisonsCommand,
    ListSbomsCommand,
    ListVulnerabilitiesCommand,
    UpsertExposureCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import NotFoundError, ValidationError


def _app(tmp_path: Path):
    app = ApplicationFactory().create_json_application(tmp_path / "state.json", seed=False)
    token = "s" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "sbom-admin", ("admin",), token)
    )
    return app, token


def _cyclonedx(version: str, extra: bool = False) -> dict[str, object]:
    components: list[dict[str, object]] = [
        {
            "bom-ref": f"pkg:pypi/requests@{version}",
            "name": "requests",
            "version": version,
            "purl": f"pkg:pypi/requests@{version}",
            "licenses": [{"license": {"id": "Apache-2.0"}}],
        }
    ]
    if extra:
        components.append(
            {
                "bom-ref": "pkg:pypi/urllib3@2.2.2",
                "name": "urllib3",
                "version": "2.2.2",
                "purl": "pkg:pypi/urllib3@2.2.2",
            }
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{version}",
        "components": components,
    }


def test_sbom_registry_risk_comparison_and_exports(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    service = app.sbom_service
    first_command = ImportSbomCommand(
        "default",
        token,
        "openinfra",
        "0.29.98",
        "production",
        "github-actions",
        _cyclonedx("2.31.0"),
        "https://example.invalid/sbom/0.29.98.json",
    )
    first = service.import_sbom(first_command)
    assert service.import_sbom(first_command).id == first.id
    second = service.import_sbom(
        ImportSbomCommand(
            "default",
            token,
            "openinfra",
            "0.29.99",
            "production",
            "github-actions",
            _cyclonedx("2.32.0", extra=True),
        )
    )
    assert second.document_version == 2
    assert service.get_sbom(GetSbomCommand("default", token, second.id.value)).id == second.id
    assert len(service.list_sboms(ListSbomsCommand("default", token)).items) == 2

    vulnerability = service.import_vulnerability(
        ImportVulnerabilityCommand(
            "default",
            token,
            "CVE-2026-12345",
            "requests",
            "2.32.0",
            "8.2",
            "pkg:pypi/requests@2.32.0",
            True,
            "weaponized",
            "scanner-x",
        )
    )
    assert (
        service.import_vulnerability(
            ImportVulnerabilityCommand(
                "default",
                token,
                "CVE-2026-12345",
                "requests",
                "2.32.0",
                "8.2",
                "pkg:pypi/requests@2.32.0",
                True,
                "weaponized",
                "scanner-x",
            )
        ).id
        == vulnerability.id
    )
    assert service.list_vulnerabilities(
        ListVulnerabilitiesCommand("default", token, known_exploited=True)
    ).items

    exposure = service.upsert_exposure(
        UpsertExposureCommand(
            "default",
            token,
            "openinfra",
            "production",
            True,
            True,
            5,
            ("waf",),
            ("asset-001",),
            ("service-api",),
        )
    )
    assert (
        service.get_exposure(GetExposureCommand("default", token, "openinfra", "production")).id
        == exposure.id
    )
    assert service.list_exposures(ListExposuresCommand("default", token)).items

    findings = service.assess_risk(AssessSbomRiskCommand("default", token, second.id.value))
    assert len(findings.items) == 1
    assert findings.items[0].priority.value == "critical"
    assert service.list_findings(
        ListRiskFindingsCommand("default", token, document_id=second.id.value)
    ).items

    comparison = service.compare(
        CompareSbomsCommand("default", token, first.id.value, second.id.value)
    )
    assert comparison.changed and comparison.added
    assert (
        service.compare(CompareSbomsCommand("default", token, first.id.value, second.id.value)).id
        == comparison.id
    )
    assert service.list_comparisons(ListSbomComparisonsCommand("default", token)).items

    json_export = service.export_risk(
        ExportSbomRiskCommand("default", token, second.id.value, "json")
    )
    csv_export = service.export_risk(
        ExportSbomRiskCommand("default", token, second.id.value, "csv")
    )
    assert json.loads(json_export.content)["document"]["id"] == second.id.value
    assert b"CVE-2026-12345" in csv_export.content
    assert {value["name"] for value in app.store.data["sbom_event_outbox"].values()} >= {
        "sbom.document.imported",
        "sbom.vulnerability.imported",
        "sbom.exposure.updated",
        "sbom.risk.assessed",
        "sbom.comparison.generated",
    }


def test_sbom_errors_and_tenant_isolation(tmp_path: Path) -> None:
    app, token = _app(tmp_path)
    service = app.sbom_service
    with pytest.raises(ValidationError, match="detect"):
        service.import_sbom(
            ImportSbomCommand("default", token, "app", "1", "prod", "pytest", {"components": []})
        )
    with pytest.raises(NotFoundError):
        service.get_sbom(GetSbomCommand("default", token, "00000000-0000-0000-0000-000000000000"))
    with pytest.raises(ValidationError, match="json or csv"):
        document = service.import_sbom(
            ImportSbomCommand("default", token, "app", "1", "prod", "pytest", _cyclonedx("1.0"))
        )
        service.export_risk(ExportSbomRiskCommand("default", token, document.id.value, "xlsx"))


def test_sbom_service_error_conflict_and_pagination_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, token = _app(tmp_path)
    service = app.sbom_service
    document = service.import_sbom(
        ImportSbomCommand("default", token, "app", "1", "prod", "pytest", _cyclonedx("1.0"))
    )
    first_vulnerability = service.import_vulnerability(
        ImportVulnerabilityCommand("default", token, "CVE-2026-10001", "requests", "1.0", "5.0")
    )
    service.import_vulnerability(
        ImportVulnerabilityCommand("default", token, "CVE-2026-10002", "requests", "1.0", "6.0")
    )
    with pytest.raises(ValidationError, match="another payload"):
        service.import_vulnerability(
            ImportVulnerabilityCommand(
                "default",
                token,
                first_vulnerability.cve_id,
                first_vulnerability.component_name,
                first_vulnerability.component_version,
                "9.0",
            )
        )

    with pytest.raises(NotFoundError, match="exposure"):
        service.get_exposure(GetExposureCommand("default", token, "missing", "prod"))
    with pytest.raises(NotFoundError, match="document"):
        service.assess_risk(
            AssessSbomRiskCommand("default", token, "00000000-0000-0000-0000-000000000000")
        )
    with pytest.raises(NotFoundError, match="base or target"):
        service.compare(
            CompareSbomsCommand(
                "default",
                token,
                document.id.value,
                "00000000-0000-0000-0000-000000000000",
            )
        )
    other_application = service.import_sbom(
        ImportSbomCommand("default", token, "other", "1", "prod", "pytest", _cyclonedx("1.0"))
    )
    with pytest.raises(ValidationError, match="same application"):
        service.compare(
            CompareSbomsCommand("default", token, document.id.value, other_application.id.value)
        )
    with pytest.raises(NotFoundError, match="comparison"):
        service.get_comparison(
            GetSbomComparisonCommand("default", token, "00000000-0000-0000-0000-000000000000")
        )
    with pytest.raises(NotFoundError, match="document"):
        service.export_risk(
            ExportSbomRiskCommand(
                "default",
                token,
                "00000000-0000-0000-0000-000000000000",
                "json",
            )
        )

    monkeypatch.setattr(type(service), "_PAGE_SIZE", 1)
    findings = service.assess_risk(AssessSbomRiskCommand("default", token, document.id.value))
    assert len(findings.items) == 1
    assert len(service.list_findings(ListRiskFindingsCommand("default", token)).items) == 2
    exported = service.export_risk(
        ExportSbomRiskCommand("default", token, document.id.value, "json")
    )
    assert len(json.loads(exported.content)["findings"]) == 2

    monkeypatch.setattr(type(service), "_MAX_VULNERABILITIES", 1)
    with pytest.raises(ValidationError, match="exceeds 100000"):
        service.assess_risk(AssessSbomRiskCommand("default", token, document.id.value))


def test_json_sbom_repository_replacement_and_cursor_guards(tmp_path: Path) -> None:
    from openinfra.domain.common import Pagination, TenantId
    from openinfra.domain.sbom import (
        ExposureContext,
        RiskFinding,
        SbomComponent,
        SbomDocument,
        VulnerabilityRecord,
    )
    from openinfra.infrastructure.json_store import JsonDocumentStore, JsonSbomRepository

    store = JsonDocumentStore(tmp_path / "repository.json")
    repository = JsonSbomRepository(store)
    tenant = TenantId.from_value("default")
    component = SbomComponent.create(
        "pkg:pypi/requests@1.0", "requests", "1.0", "pkg:pypi/requests@1.0"
    )
    document = SbomDocument.create(
        tenant,
        "app",
        "1",
        "prod",
        "cyclonedx",
        "1.6",
        "pytest",
        None,
        "a" * 64,
        1,
        (component,),
    )
    vulnerability = VulnerabilityRecord.create(
        tenant, "CVE-2026-10003", "requests", "1.0", "7.0", component.purl
    )
    first_exposure = ExposureContext.create(tenant, "app", "prod", False, False, 2)
    second_exposure = ExposureContext.create(tenant, "app", "prod", True, True, 5)
    repository.save_exposure(first_exposure)
    repository.save_exposure(second_exposure)
    assert repository.get_exposure(tenant, "app", "prod") == second_exposure

    first_finding = RiskFinding.create(tenant, document, component, vulnerability, first_exposure)
    second_finding = RiskFinding.create(tenant, document, component, vulnerability, second_exposure)
    repository.replace_findings(tenant, document.id.value, (first_finding,))
    repository.replace_findings(tenant, document.id.value, (second_finding,))
    assert repository.list_findings(tenant, Pagination(limit=10)).items == (second_finding,)

    with pytest.raises(ValidationError, match="numeric offset"):
        repository.list_documents(tenant, Pagination(limit=10, cursor="invalid"))
    with pytest.raises(ValidationError, match="positive"):
        repository.list_documents(tenant, Pagination(limit=10, cursor="-1"))
