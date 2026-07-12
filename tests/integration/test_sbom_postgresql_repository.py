from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pytest import MonkeyPatch
from tests.integration.test_postgresql_runtime import FakeConnection

from openinfra.domain.common import DomainEvent, EntityId, Pagination, TenantId, ValidationError
from openinfra.domain.sbom import (
    ExposureContext,
    RiskFinding,
    SbomComparison,
    SbomComponent,
    SbomDocument,
    VulnerabilityRecord,
)
from openinfra.infrastructure.postgresql import (
    PostgreSQLConnectionFactory,
    PostgreSQLSbomRepository,
    PostgreSQLSessionRegistry,
)


def _repository() -> PostgreSQLSbomRepository:
    connection = FakeConnection()
    return PostgreSQLSbomRepository(
        PostgreSQLSessionRegistry(
            PostgreSQLConnectionFactory(
                "postgresql://openinfra@db/openinfra",
                connector=lambda _dsn, _profile: connection,
            )
        )
    )


def _objects() -> dict[str, object]:
    tenant = TenantId.from_value("default")
    component = SbomComponent.create(
        "pkg:pypi/requests@2.32.0",
        "requests",
        "2.32.0",
        "pkg:pypi/requests@2.32.0",
        "PSF",
        ("Apache-2.0",),
        ("SHA-256:abc",),
    )
    document = SbomDocument.create(
        tenant,
        "openinfra",
        "0.29.99",
        "production",
        "cyclonedx",
        "1.6",
        "github-actions",
        "https://example.invalid/sbom.json",
        "a" * 64,
        1,
        (component,),
    )
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
        ("waf",),
        ("asset-001",),
        ("service-api",),
    )
    finding = RiskFinding.create(tenant, document, component, vulnerability, exposure)
    target = SbomDocument.create(
        tenant,
        "openinfra",
        "0.30.0",
        "production",
        "cyclonedx",
        "1.6",
        "github-actions",
        None,
        "b" * 64,
        2,
        (
            SbomComponent.create(
                "pkg:pypi/requests@2.33.0",
                "requests",
                "2.33.0",
                "pkg:pypi/requests@2.33.0",
            ),
        ),
    )
    comparison = SbomComparison.create(tenant, document, target)
    event = DomainEvent(
        EntityId.new(),
        tenant,
        document.id,
        "sbom.document.imported",
        {"document_id": document.id.value},
        datetime(2026, 7, 11, 12, tzinfo=UTC),
    )
    return {
        "tenant": tenant,
        "document": document,
        "vulnerability": vulnerability,
        "exposure": exposure,
        "finding": finding,
        "comparison": comparison,
        "event": event,
    }


def _patch_writes(
    monkeypatch: MonkeyPatch, repo: PostgreSQLSbomRepository
) -> list[tuple[str, dict[str, object]]]:
    statements: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(repo, "_ensure_tenant", lambda _tenant: None)
    monkeypatch.setattr(
        repo,
        "_execute_without_result",
        lambda query, params: statements.append((" ".join(query.split()), dict(params))),
    )
    return statements


def test_sbom_postgresql_save_methods_and_outbox(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    values = _objects()
    statements = _patch_writes(monkeypatch, repo)

    repo.save_document(values["document"])  # type: ignore[arg-type]
    repo.save_vulnerability(values["vulnerability"])  # type: ignore[arg-type]
    repo.save_exposure(values["exposure"])  # type: ignore[arg-type]
    repo.replace_findings(
        values["tenant"],  # type: ignore[arg-type]
        values["document"].id.value,  # type: ignore[union-attr]
        (values["finding"],),  # type: ignore[arg-type]
    )
    repo.save_comparison(values["comparison"])  # type: ignore[arg-type]
    repo.append_event(values["event"])  # type: ignore[arg-type]

    joined = "\n".join(query for query, _params in statements)
    assert "sbom_documents" in joined
    assert "sbom_vulnerabilities" in joined
    assert "sbom_exposure_contexts" in joined
    assert "DELETE FROM sbom_risk_findings" in joined
    assert "INSERT INTO sbom_risk_findings" in joined
    assert "sbom_comparisons" in joined
    assert "sbom_event_outbox" in joined


def test_sbom_postgresql_read_filters_pagination_and_guards(
    monkeypatch: MonkeyPatch,
) -> None:
    repo = _repository()
    values = _objects()
    tenant = values["tenant"]
    document = values["document"]
    vulnerability = values["vulnerability"]
    exposure = values["exposure"]
    finding = values["finding"]
    comparison = values["comparison"]
    assert isinstance(tenant, TenantId)
    assert isinstance(document, SbomDocument)
    assert isinstance(vulnerability, VulnerabilityRecord)
    assert isinstance(exposure, ExposureContext)
    assert isinstance(finding, RiskFinding)
    assert isinstance(comparison, SbomComparison)

    rows = iter(
        [
            {"payload": json.dumps(document.as_dict())},
            {"payload": json.dumps(document.as_dict())},
            {"version": 4},
            {"payload": json.dumps(vulnerability.as_dict())},
            {"payload": json.dumps(exposure.as_dict())},
            {"payload": json.dumps(comparison.as_dict())},
            {"payload": json.dumps(comparison.as_dict())},
            None,
        ]
    )
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: next(rows))

    assert repo.get_document(tenant, document.id.value) == document
    assert repo.find_document_by_fingerprint(tenant, document.fingerprint) == document
    assert repo.next_document_version(tenant, "OpenInfra", "Production") == 5
    assert repo.find_vulnerability_by_identity(tenant, vulnerability.identity_key) == vulnerability
    assert repo.get_exposure(tenant, "OpenInfra", "Production") == exposure
    assert repo.find_comparison_by_digest(tenant, comparison.input_digest) == comparison
    assert repo.get_comparison(tenant, comparison.id.value) == comparison
    assert repo.get_document(tenant, document.id.value) is None

    page_rows = [
        {"payload": json.dumps(document.as_dict())},
        {"payload": json.dumps(document.as_dict())},
    ]
    captured: list[tuple[str, dict[str, object]]] = []

    def fetch_all(query: str, params: dict[str, object]) -> list[dict[str, object]]:
        captured.append((" ".join(query.split()), dict(params)))
        return page_rows

    monkeypatch.setattr(repo, "_fetch_all", fetch_all)
    page = repo.list_documents(
        tenant,
        Pagination(limit=1),
        application="OpenInfra",
        environment="Production",
        format="Cyclone-DX",
    )
    assert page.items == (document,)
    assert page.next_cursor == "1"
    query, params = captured[-1]
    assert "application = %(application)s" in query
    assert params["format"] == "cyclonedx"

    monkeypatch.setattr(
        repo,
        "_fetch_all",
        lambda _query, _params: [{"payload": json.dumps(vulnerability.as_dict())}],
    )
    assert repo.list_vulnerabilities(
        tenant,
        Pagination(limit=10),
        cve_id="cve-2026-12345",
        component="request",
        known_exploited=True,
    ).items == (vulnerability,)

    monkeypatch.setattr(
        repo,
        "_fetch_all",
        lambda _query, _params: [{"payload": json.dumps(exposure.as_dict())}],
    )
    assert repo.list_exposures(tenant, Pagination(limit=10)).items == (exposure,)

    monkeypatch.setattr(
        repo,
        "_fetch_all",
        lambda _query, _params: [{"payload": json.dumps(finding.as_dict())}],
    )
    assert repo.list_findings(
        tenant,
        Pagination(limit=10),
        document.id.value,
        "critical",
        "false_positive",
    ).items == (finding,)

    monkeypatch.setattr(
        repo,
        "_fetch_all",
        lambda _query, _params: [{"payload": json.dumps(comparison.as_dict())}],
    )
    assert repo.list_comparisons(tenant, Pagination(limit=10)).items == (comparison,)

    with pytest.raises(ValidationError, match="signing secret"):
        repo.list_documents(tenant, Pagination(limit=10, cursor="invalid"))
    with pytest.raises(ValidationError, match="signing secret"):
        repo.list_documents(tenant, Pagination(limit=10, cursor="-1"))
    with pytest.raises(ValueError, match="unsupported"):
        repo._page("not_allowed", tenant, Pagination(limit=10), "", {}, "id")
    with pytest.raises(ValidationError, match="JSON object"):
        repo._json_mapping("[]")


def test_sbom_postgresql_version_defaults_to_one(monkeypatch: MonkeyPatch) -> None:
    repo = _repository()
    tenant = TenantId.from_value("default")
    monkeypatch.setattr(repo, "_fetch_one", lambda _query, _params: None)
    assert repo.next_document_version(tenant, "app", "prod") == 1
    assert repo.find_vulnerability_by_identity(tenant, "missing") is None
