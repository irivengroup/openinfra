from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import ValidationError
from openinfra.domain.kubernetes_security import KubernetesImageReference, KubernetesSecretReference
from openinfra.domain.kubernetes_topology import KubernetesResource

DOC_ID = "11111111-1111-4111-8111-111111111111"
DIGEST = "sha256:" + "a" * 64
CERT = "b" * 64


def test_image_reference_normalizes_digest_and_document_links() -> None:
    item = KubernetesImageReference.create(
        "registry.example/openinfra/api:1.0",
        "a" * 64,
        (DOC_ID, DOC_ID),
    )
    assert item.digest == DIGEST
    assert item.sbom_document_ids == (DOC_ID,)
    assert KubernetesImageReference.from_dict(item.as_dict()) == item

    embedded = KubernetesImageReference.create(f"registry.example/openinfra/api@{DIGEST.upper()}")
    assert embedded.digest == DIGEST
    assert embedded.reference.endswith(DIGEST)


def test_image_reference_rejects_invalid_or_conflicting_digests() -> None:
    with pytest.raises(ValidationError, match="image reference is invalid"):
        KubernetesImageReference.create("https://registry.example/api:latest")
    with pytest.raises(ValidationError, match="SHA-256"):
        KubernetesImageReference.create("registry.example/api:latest", "sha256:bad")
    with pytest.raises(ValidationError, match="conflicts"):
        KubernetesImageReference.create(f"registry.example/api@{DIGEST}", "sha256:" + "c" * 64)
    with pytest.raises(ValidationError, match="more than 32"):
        KubernetesImageReference.create(
            "registry.example/api:latest",
            sbom_document_ids=tuple(f"00000000-0000-4000-8000-{index:012d}" for index in range(33)),
        )


def test_secret_reference_is_irreversibly_masked_except_kubernetes_object_name() -> None:
    vault = KubernetesSecretReference.create("vault://openinfra/prod/api/password")
    assert vault.provider == "vault"
    assert vault.display_reference == "vault://***"
    assert len(vault.reference_hash) == 64
    assert "password" not in str(vault.as_dict())
    assert KubernetesSecretReference.from_dict(vault.as_dict()) == vault

    native = KubernetesSecretReference.create("kubernetes-secret://production/api-runtime")
    assert native.display_reference == "kubernetes-secret://production/api-runtime"
    assert KubernetesSecretReference.from_dict(native.as_dict()) == native


def test_secret_reference_rejects_cleartext_unsupported_and_tampered_values() -> None:
    with pytest.raises(ValidationError, match="approved external reference scheme"):
        KubernetesSecretReference.create("plain-text-secret")
    with pytest.raises(ValidationError, match="namespace/name"):
        KubernetesSecretReference.create("kubernetes-secret://production")
    persisted = KubernetesSecretReference.create("vault://openinfra/prod/api").as_dict()
    persisted["reference_hash"] = "0" * 64
    # External references are intentionally not reversible; persisted masked form is validated structurally.
    assert KubernetesSecretReference.from_dict(persisted).reference_hash == "0" * 64
    with pytest.raises(ValidationError, match="persisted representation"):
        KubernetesSecretReference.from_dict(
            {
                "provider": "vault",
                "display_reference": "vault://clear/path",
                "reference_hash": "0" * 64,
            }
        )


def test_kubernetes_resource_security_references_round_trip_without_secret_material() -> None:
    resource = KubernetesResource.from_dict(
        {
            "kind": "workload",
            "uid": "deploy-api",
            "name": "api",
            "namespace": "production",
            "images": [
                {
                    "reference": "registry.example/openinfra/api:1.0",
                    "digest": DIGEST,
                    "sbom_document_ids": [DOC_ID],
                }
            ],
            "certificate_fingerprints": [CERT.upper(), CERT],
            "secret_refs": [
                "vault://openinfra/prod/api/password",
                "kubernetes-secret://production/api-runtime",
            ],
        }
    )
    assert len(resource.images) == 1
    assert resource.certificate_fingerprints == (CERT,)
    assert len(resource.secret_refs) == 2
    payload = resource.as_dict()
    assert "openinfra/prod/api/password" not in str(payload)
    assert KubernetesResource.from_dict(payload) == resource


def test_kubernetes_resource_security_reference_kinds_and_limits_are_strict() -> None:
    image = KubernetesImageReference.create("registry.example/api:1")
    secret_reference = KubernetesSecretReference.create("vault://openinfra/prod/api")
    with pytest.raises(ValidationError, match="only valid for workloads and pods"):
        KubernetesResource.create("service", "svc", "api", namespace="prod", images=(image,))
    with pytest.raises(ValidationError, match="certificate references are unsupported"):
        KubernetesResource.create(
            "network-policy",
            "np",
            "default-deny",
            namespace="prod",
            certificate_fingerprints=(CERT,),
        )
    with pytest.raises(ValidationError, match="secret references are unsupported"):
        KubernetesResource.create(
            "volume", "vol", "data", namespace="prod", secret_refs=(secret_reference,)
        )
    with pytest.raises(ValidationError, match="images cannot exceed 64"):
        KubernetesResource.create(
            "workload",
            "deploy",
            "api",
            namespace="prod",
            images=tuple(
                KubernetesImageReference.create(f"registry.example/api:{index}")
                for index in range(65)
            ),
        )


def test_kubernetes_resource_rejects_invalid_security_payload_shapes() -> None:
    base = {"kind": "workload", "uid": "deploy", "name": "api", "namespace": "prod"}
    for field in ("images", "certificate_fingerprints", "secret_refs"):
        payload = {**base, field: {"invalid": True}}
        with pytest.raises(ValidationError, match="JSON array"):
            KubernetesResource.from_dict(payload)
    with pytest.raises(ValidationError, match="image reference must be a JSON object"):
        KubernetesResource.from_dict({**base, "images": ["registry.example/api:1"]})
    with pytest.raises(ValidationError, match="string or JSON object"):
        KubernetesResource.from_dict({**base, "secret_refs": [42]})
    with pytest.raises(ValidationError, match="certificate fingerprint"):
        KubernetesResource.from_dict({**base, "certificate_fingerprints": ["not-a-digest"]})


def test_legacy_snapshot_fingerprint_is_preserved_when_security_references_are_absent() -> None:
    from openinfra.domain.common import TenantId
    from openinfra.domain.kubernetes_topology import KubernetesTopologySnapshot

    resources = (
        KubernetesResource.create("namespace", "ns", "prod"),
        KubernetesResource.create(
            "workload",
            "deploy",
            "api",
            namespace="prod",
            attributes={"image": "registry.example/api:1"},
        ),
    )
    snapshot = KubernetesTopologySnapshot.create(
        TenantId.from_value("default"),
        "cluster",
        "cluster",
        "kubernetes",
        "v1.34.1",
        "pytest",
        datetime(2026, 7, 14, tzinfo=UTC),
        resources,
    )
    assert (
        snapshot.fingerprint == "5b02b17e738e7dbdb29964a6060477dd2093254b0d181c8cdc66185e0c54e64e"
    )
    assert "images" not in resources[1].as_dict()
    assert "certificate_fingerprints" not in resources[1].as_dict()
    assert "secret_refs" not in resources[1].as_dict()


def test_security_reference_edge_validation_and_correlation_keys() -> None:
    with pytest.raises(ValidationError, match="image digest is invalid"):
        KubernetesImageReference.create("registry.example/api@sha256:bad")
    with pytest.raises(ValidationError, match="JSON array"):
        KubernetesImageReference.from_dict(
            {"reference": "registry.example/api:1", "sbom_document_ids": "not-a-list"}
        )
    image = KubernetesImageReference.create("registry.example/api:1")
    assert image.correlation_key == "registry.example/api:1"

    with pytest.raises(ValidationError, match="path is invalid"):
        KubernetesSecretReference.create("vault:///invalid")
    with pytest.raises(ValidationError, match="provider is unsupported"):
        KubernetesSecretReference.from_dict(
            {
                "provider": "unsupported",
                "display_reference": "unsupported://***",
                "reference_hash": "0" * 64,
            }
        )
    native = KubernetesSecretReference.create("kubernetes-secret://prod/api")
    payload = native.as_dict()
    payload["reference_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="hash mismatch"):
        KubernetesSecretReference.from_dict(payload)


def test_security_report_counts_unhealthy_certificates_and_list_metadata() -> None:
    from types import SimpleNamespace

    from openinfra.domain.kubernetes_security import KubernetesSecurityCorrelationReport

    resource = KubernetesResource.create(
        "ingress",
        "ing-api",
        "api",
        namespace="prod",
        certificate_fingerprints=(CERT,),
    )
    observed_at = datetime(2026, 7, 14, tzinfo=UTC)
    snapshot = SimpleNamespace(
        id=SimpleNamespace(value="snapshot-1"),
        cluster_key="cluster-1",
        observed_at=observed_at,
        resources=(resource,),
    )

    class _Certificate:
        lifecycle = SimpleNamespace(value="active")
        owner = "platform"
        environment = "production"

        @staticmethod
        def health(_at: datetime) -> object:
            return SimpleNamespace(value="expired")

        @staticmethod
        def days_remaining(_at: datetime) -> int:
            return -1

    report = KubernetesSecurityCorrelationReport.build(
        snapshot=snapshot,
        sbom_documents=(),
        findings=(),
        certificates={CERT: _Certificate()},  # type: ignore[dict-item]
        correlation_truncated=False,
    )
    assert report.unhealthy_certificate_count == 1
    assert KubernetesSecurityCorrelationReport._metadata_strings(
        {"image_references": [" registry.example/api:1 ", ""]}, "image_references"
    ) == {"registry.example/api:1"}
