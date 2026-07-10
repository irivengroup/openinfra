from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.certificate_pki import (
    CertificateAsset,
    CertificateEndpointObservation,
    CertificateHealth,
    CertificateMaterial,
)
from openinfra.domain.common import TenantId, ValidationError

NOW = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64
ROOT_FINGERPRINT = "b" * 64


def material(**overrides: object) -> CertificateMaterial:
    values: dict[str, object] = {
        "fingerprint_sha256": FINGERPRINT,
        "serial_number": "01AB",
        "subject_dn": "CN=api.example.com,O=OpenInfra",
        "issuer_dn": "CN=OpenInfra Root CA,O=OpenInfra",
        "common_name": "api.example.com",
        "san_dns": ("api.example.com", "*.service.example.com"),
        "san_ip": ("192.0.2.10",),
        "san_email": ("pki@example.com",),
        "san_uri": ("spiffe://example.com/api",),
        "not_before": NOW - timedelta(days=1),
        "not_after": NOW + timedelta(days=90),
        "public_key_algorithm": "rsa",
        "public_key_size": 2048,
        "signature_algorithm": "sha256",
        "is_ca": False,
    }
    values.update(overrides)
    return CertificateMaterial.create(**values)  # type: ignore[arg-type]


def certificate(**overrides: object) -> CertificateAsset:
    values: dict[str, object] = {
        "tenant_id": TenantId.from_value("default"),
        "material": material(),
        "chain_fingerprints": (ROOT_FINGERPRINT,),
        "owner": "Platform team",
        "environment": "production",
        "source": "internal-pki",
        "object_key": "application/api",
        "actor": "pytest",
    }
    values.update(overrides)
    return CertificateAsset.create(**values)  # type: ignore[arg-type]


def test_certificate_material_normalizes_and_serializes() -> None:
    item = material(
        fingerprint_sha256=":".join(["AA"] * 32),
        san_dns=("API.EXAMPLE.COM.", "*.SERVICE.EXAMPLE.COM"),
        san_ip=("2001:0db8::1",),
    )

    assert item.fingerprint_sha256 == "aa" * 32
    assert item.san_dns == ("api.example.com", "*.service.example.com")
    assert item.san_ip == ("2001:db8::1",)
    assert item.immutable_dict()["public_key_size"] == 2048


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fingerprint_sha256", "bad"),
        ("serial_number", "not-hex"),
        ("not_after", NOW - timedelta(days=2)),
        ("public_key_size", 64),
        ("san_dns", ("bad host!",)),
        ("san_ip", ("999.1.1.1",)),
        ("san_email", ("invalid",)),
        ("san_uri", ("relative/path",)),
    ],
)
def test_certificate_material_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        material(**{field: value})


def test_certificate_health_hostname_matching_and_retirement() -> None:
    item = certificate()

    assert item.health(NOW) is CertificateHealth.HEALTHY
    assert item.matches_hostname("api.example.com")
    assert item.matches_hostname("one.service.example.com")
    assert not item.matches_hostname("two.deep.service.example.com")
    assert item.matches_hostname("192.0.2.10")
    assert not item.matches_hostname("192.0.2.11")

    warning = certificate(material=material(not_after=NOW + timedelta(days=20)))
    critical = certificate(material=material(not_after=NOW + timedelta(days=5)))
    expired = certificate(material=material(not_after=NOW - timedelta(seconds=1)))
    future = certificate(material=material(not_before=NOW + timedelta(days=1)))
    assert warning.health(NOW) is CertificateHealth.WARNING
    assert critical.health(NOW) is CertificateHealth.CRITICAL
    assert expired.health(NOW) is CertificateHealth.EXPIRED
    assert future.health(NOW) is CertificateHealth.NOT_YET_VALID
    assert item.retire("operator").health(NOW) is CertificateHealth.RETIRED


def test_certificate_revision_preserves_identity_and_validates_chain() -> None:
    item = certificate()
    revised = item.revise_governance(
        chain_fingerprints=(),
        owner="Security team",
        environment="staging",
        source="discovery",
        object_key=None,
        actor="operator",
    )

    assert revised.id == item.id
    assert revised.material == item.material
    assert revised.version == 2
    assert revised.owner == "Security team"
    assert revised.object_key is None

    with pytest.raises(ValidationError, match="itself"):
        certificate(chain_fingerprints=(FINGERPRINT,))
    with pytest.raises(ValidationError, match="duplicates"):
        certificate(chain_fingerprints=(ROOT_FINGERPRINT, ROOT_FINGERPRINT))


def test_endpoint_observation_is_canonical_idempotent_payload() -> None:
    observation = CertificateEndpointObservation.create(
        tenant_id=TenantId.from_value("default"),
        idempotency_key="scanner-01:000001",
        protocol="HTTPS",
        host="API.EXAMPLE.COM.",
        port=443,
        service="Public API",
        certificate_fingerprint=FINGERPRINT,
        observed_at=NOW,
        source="discovery",
        collector="scanner-01",
        object_key="application/api",
        tls_version="TLS1.3",
        cipher="TLS_AES_256_GCM_SHA384",
    )

    assert observation.host == "api.example.com"
    assert observation.protocol == "https"
    assert observation.endpoint == "https://api.example.com:443"
    assert len(observation.payload_fingerprint) == 64
    assert observation.as_dict()["certificate_fingerprint"] == FINGERPRINT

    with pytest.raises(ValidationError):
        CertificateEndpointObservation.create(
            tenant_id=TenantId.from_value("default"),
            idempotency_key="bad",
            protocol="https",
            host="api.example.com",
            port=0,
            service="API",
            certificate_fingerprint=FINGERPRINT,
            observed_at=NOW,
            source="discovery",
            collector="scanner-01",
            object_key=None,
            tls_version=None,
            cipher=None,
        )
