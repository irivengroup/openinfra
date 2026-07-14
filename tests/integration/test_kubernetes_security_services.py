from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.kubernetes_topology_services import (
    GetKubernetesTopologyCommand,
    GetLatestKubernetesTopologyCommand,
    ImportKubernetesTopologyCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.certificate_pki import CertificateAsset, CertificateMaterial
from openinfra.domain.common import Pagination, TenantId, ValidationError
from openinfra.domain.sbom import RiskFinding, SbomComponent, SbomDocument, VulnerabilityRecord

KNOWN_CERT = "b" * 64
UNKNOWN_CERT = "c" * 64
IMAGE_DIGEST = "sha256:" + "a" * 64


def _application(path: Path):
    data_path = path if path.suffix == ".json" else path / "state.json"
    app = ApplicationFactory().create_json_application(data_path, seed=False)
    token = "s" * 40
    app.security_service.bootstrap_token(
        BootstrapTokenCommand("default", "pytest", "kubernetes-security", ("admin",), token)
    )
    return app, token


def _seed_sbom(app: object) -> SbomDocument:
    tenant = TenantId.from_value("default")
    component = SbomComponent.create(
        "pkg:api",
        "openinfra-api",
        "1.0.0",
        purl="pkg:pypi/openinfra-api@1.0.0",
    )
    document = SbomDocument.create(
        tenant_id=tenant,
        application="openinfra-api",
        release="1.0.0",
        environment="production",
        format="cyclonedx",
        specification_version="1.6",
        source_name="ci-sbom.json",
        source_uri="https://ci.example/sbom/openinfra-api.json",
        source_hash="d" * 64,
        document_version=1,
        components=(component,),
        metadata={
            "image_reference": "registry.example/openinfra/api:1.0.0",
            "image_digest": IMAGE_DIGEST,
        },
    )
    app.sbom_repository.save_document(document)  # type: ignore[attr-defined]
    vulnerability = VulnerabilityRecord.create(
        tenant,
        "CVE-2026-12345",
        "openinfra-api",
        "1.0.0",
        "9.8",
        component_purl="pkg:pypi/openinfra-api@1.0.0",
        known_exploited=True,
    )
    finding = RiskFinding.create(tenant, document, component, vulnerability, None)
    app.sbom_repository.replace_findings(tenant, document.id.value, (finding,))  # type: ignore[attr-defined]
    return document


def _seed_certificate(app: object, observed_at: datetime) -> None:
    tenant = TenantId.from_value("default")
    material = CertificateMaterial.create(
        fingerprint_sha256=KNOWN_CERT,
        serial_number="A1",
        subject_dn="CN=api.example.net",
        issuer_dn="CN=OpenInfra Test CA",
        common_name="api.example.net",
        san_dns=("api.example.net",),
        san_ip=(),
        san_email=(),
        san_uri=(),
        not_before=observed_at - timedelta(days=10),
        not_after=observed_at + timedelta(days=120),
        public_key_algorithm="rsa",
        public_key_size=2048,
        signature_algorithm="sha256-rsa",
        is_ca=False,
    )
    certificate = CertificateAsset.create(
        tenant_id=tenant,
        material=material,
        chain_fingerprints=(),
        owner="platform-team",
        environment="production",
        source="manual",
        object_key=None,
        actor="pytest",
    )
    app.certificate_inventory_repository.save_certificate(certificate)  # type: ignore[attr-defined]


def _resources(document_id: str) -> tuple[dict[str, object], ...]:
    return (
        {"kind": "namespace", "uid": "ns-prod", "name": "production"},
        {
            "kind": "workload",
            "uid": "deploy-api",
            "name": "api",
            "namespace": "production",
            "images": [
                {
                    "reference": "registry.example/openinfra/api:1.0.0",
                    "digest": IMAGE_DIGEST,
                    "sbom_document_ids": [document_id],
                },
                {"reference": "registry.example/openinfra/sidecar:2.0.0"},
            ],
            "secret_refs": [
                "vault://openinfra/production/api/password",
                "kubernetes-secret://production/api-runtime",
            ],
        },
        {
            "kind": "service",
            "uid": "svc-api",
            "name": "api",
            "namespace": "production",
            "target_uids": ["deploy-api"],
        },
        {
            "kind": "ingress",
            "uid": "ing-api",
            "name": "api",
            "namespace": "production",
            "target_uids": ["svc-api"],
            "certificate_fingerprints": [KNOWN_CERT, UNKNOWN_CERT],
        },
    )


def seeded_security_application(path: Path):
    app, token = _application(path)
    observed_at = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    document = _seed_sbom(app)
    _seed_certificate(app, observed_at)
    snapshot = app.kubernetes_topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            "default",
            token,
            "cluster-par-01",
            "prod-par-01",
            "kubernetes",
            "v1.34.1",
            "pytest",
            observed_at,
            _resources(document.id.value),
            "eu-west",
            "par-01",
            "pytest",
        )
    )
    return app, token, snapshot


def test_kubernetes_security_correlation_contextualizes_sbom_certificates_and_secret_refs(
    tmp_path: Path,
) -> None:
    app, token, snapshot = seeded_security_application(tmp_path / "state.json")

    report = app.kubernetes_topology_service.latest_security(
        GetLatestKubernetesTopologyCommand("default", token, "cluster-par-01")
    )
    payload = report.as_dict()
    summary = payload["summary"]
    assert report.snapshot_id == snapshot.id.value
    assert summary["image_count"] == 2  # type: ignore[index]
    assert summary["images_without_sbom"] == 1  # type: ignore[index]
    assert summary["active_vulnerability_count"] == 1  # type: ignore[index]
    assert summary["critical_vulnerability_count"] == 1  # type: ignore[index]
    assert summary["certificate_count"] == 2  # type: ignore[index]
    assert summary["unknown_certificate_count"] == 1  # type: ignore[index]
    assert summary["secret_reference_count"] == 2  # type: ignore[index]
    assert "openinfra/production/api/password" not in str(payload)
    assert "vault://***" in str(payload)
    persisted_state = (tmp_path / "state.json").read_text(encoding="utf-8")
    assert "openinfra/production/api/password" not in persisted_state
    assert any(
        image["sbom_documents"]
        for resource in payload["resources"]  # type: ignore[index]
        for image in resource["images"]
    )

    exact = app.kubernetes_topology_service.security(
        GetKubernetesTopologyCommand("default", token, snapshot.id.value)
    )
    assert exact.fingerprint == report.fingerprint


def test_kubernetes_security_correlation_requires_security_repositories(tmp_path: Path) -> None:
    app, token = _application(tmp_path)
    snapshot = app.kubernetes_topology_service.import_snapshot(
        ImportKubernetesTopologyCommand(
            "default",
            token,
            "cluster",
            "cluster",
            "kubernetes",
            "v1.34.1",
            "pytest",
            datetime(2026, 7, 14, tzinfo=UTC),
            (
                {"kind": "namespace", "uid": "ns", "name": "prod"},
                {"kind": "workload", "uid": "deploy", "name": "api", "namespace": "prod"},
            ),
        )
    )
    service = app.kubernetes_topology_service
    service._sbom_repository = None  # type: ignore[attr-defined]
    with pytest.raises(ValidationError, match="repositories are unavailable"):
        service.security(GetKubernetesTopologyCommand("default", token, snapshot.id.value))


def test_kubernetes_security_repository_bounds_only_mark_real_remaining_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    tenant = TenantId.from_value("default")
    app, _token, _snapshot = seeded_security_application(tmp_path / "state.json")
    service = app.kubernetes_topology_service
    document = app.sbom_repository.list_documents(tenant, Pagination.from_values(10, None)).items[0]  # type: ignore[attr-defined]
    finding = app.sbom_repository.list_findings(tenant, Pagination.from_values(10, None)).items[0]  # type: ignore[attr-defined]

    monkeypatch.setattr(service, "_MAX_SBOM_DOCUMENTS", 1)
    monkeypatch.setattr(service, "_MAX_SBOM_FINDINGS", 1)

    monkeypatch.setattr(
        service._sbom_repository,
        "list_documents",
        lambda *_args, **_kwargs: SimpleNamespace(items=(document,), next_cursor=None),
    )
    documents, documents_truncated = service._sbom_documents(tenant)
    assert documents == (document,)
    assert documents_truncated is False

    monkeypatch.setattr(
        service._sbom_repository,
        "list_findings",
        lambda *_args, **_kwargs: SimpleNamespace(items=(finding,), next_cursor=None),
    )
    findings, findings_truncated = service._sbom_findings(tenant)
    assert findings == (finding,)
    assert findings_truncated is False

    monkeypatch.setattr(
        service._sbom_repository,
        "list_documents",
        lambda *_args, **_kwargs: SimpleNamespace(items=(document,), next_cursor="more"),
    )
    assert service._sbom_documents(tenant)[1] is True

    monkeypatch.setattr(
        service._sbom_repository,
        "list_findings",
        lambda *_args, **_kwargs: SimpleNamespace(items=(finding,), next_cursor="more"),
    )
    assert service._sbom_findings(tenant)[1] is True


def test_kubernetes_security_service_rejects_cyclic_sbom_repository_cursors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    tenant = TenantId.from_value("default")
    app, _token, _snapshot = seeded_security_application(tmp_path / "state.json")
    service = app.kubernetes_topology_service

    monkeypatch.setattr(
        service._sbom_repository,
        "list_documents",
        lambda *_args, **_kwargs: SimpleNamespace(items=(), next_cursor="same"),
    )
    with pytest.raises(ValidationError, match="SBOM document repository returned a cyclic cursor"):
        service._sbom_documents(tenant)

    monkeypatch.setattr(
        service._sbom_repository,
        "list_findings",
        lambda *_args, **_kwargs: SimpleNamespace(items=(), next_cursor="same"),
    )
    with pytest.raises(ValidationError, match="SBOM finding repository returned a cyclic cursor"):
        service._sbom_findings(tenant)
