from __future__ import annotations

import json
import stat
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from openinfra.application.licensing_services import (
    ActivateRuntimeLicenseCommand,
    BootstrapInstallationIdentityCommand,
    RuntimeLicenseService,
)
from openinfra.domain.common import ConflictError, OpenInfraError, ValidationError
from openinfra.domain.licensing import (
    InstallationIdentity,
    LicenseAccessDeniedError,
    LicenseActivationRequest,
    LicenseEntitlement,
    LicenseStateCorruptedError,
    PersistedLicenseState,
    RuntimeLicenseStatus,
)
from openinfra.infrastructure import licensing as licensing_module
from openinfra.infrastructure.json_store import (
    JsonAuditRepository,
    JsonDocumentStore,
    JsonLicenseRepository,
    JsonRuntimeUsageRepository,
    JsonTransactionManager,
)
from openinfra.infrastructure.licensing import Ed25519LicenseCryptography, LicenseMaterialStore


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class LicenseScenario:
    def __init__(self, tmp_path: Path, *, edition: str = "pro", enforced: bool = True) -> None:
        self.now = datetime(2026, 7, 20, 20, 0, tzinfo=UTC)
        self.clock = MutableClock(self.now)
        self.crypto = Ed25519LicenseCryptography()
        self.authority_private, self.authority_public, self.authority_key_id = (
            self.crypto.generate_authority_material(b"correct horse battery staple")
        )
        self.identity, self.request, self.installation_private = (
            self.crypto.create_installation_material(
                installation_id=str(uuid.uuid4()),
                license_id=str(uuid.uuid4()),
                company_name="OpenInfra Customer SAS",
                edition=edition,
                requested_max_hosts=25,
            )
        )
        self.store = JsonDocumentStore(tmp_path / "state.json")
        self.repository = JsonLicenseRepository(self.store)
        self.service = RuntimeLicenseService(
            edition=edition,
            repository=self.repository,
            runtime_usage_repository=JsonRuntimeUsageRepository(self.store),
            audit_repository=JsonAuditRepository(self.store),
            transaction_manager=JsonTransactionManager(self.store),
            cryptography=self.crypto,
            trust_bundle_pem=self.authority_public,
            enforcement_enabled=enforced,
            clock=self.clock,
        )

    def bootstrap(self) -> None:
        self.service.bootstrap_identity(BootstrapInstallationIdentityCommand(self.identity))

    def entitlement(
        self,
        *,
        max_hosts: int = 25,
        not_before: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> LicenseEntitlement:
        return self.crypto.issue_entitlement(
            request=self.request,
            authority_private_key_pem=self.authority_private,
            password=b"correct horse battery staple",
            max_hosts=max_hosts,
            issued_at=self.now,
            not_before=not_before or self.now,
            expires_at=expires_at or self.now + timedelta(days=60),
        )

    def activate(self, entitlement: LicenseEntitlement | None = None) -> LicenseEntitlement:
        active = entitlement or self.entitlement()
        self.service.activate(ActivateRuntimeLicenseCommand(active, actor="test-suite"))
        return active


def test_activation_request_survives_json_round_trip_and_pem_newline(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    payload = scenario.request.as_dict()
    serialized = json.loads(json.dumps(payload))
    serialized["installation_public_key_pem"] = str(
        serialized["installation_public_key_pem"]
    ).rstrip("\n")

    restored = LicenseActivationRequest.from_dict(serialized)

    scenario.crypto.verify_activation_request(restored)
    assert restored.installation_public_key_pem.endswith("\n")
    assert restored.signing_payload == scenario.request.signing_payload


def test_activation_request_rejects_tampering(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    tampered = replace(scenario.request, company_name="Other Company")

    with pytest.raises(ValidationError, match="signature is invalid"):
        scenario.crypto.verify_activation_request(tampered)


def test_authority_private_key_is_encrypted_and_password_protected(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)

    assert b"ENCRYPTED PRIVATE KEY" in scenario.authority_private
    assert b"PRIVATE KEY" not in scenario.authority_public
    with pytest.raises(ValidationError, match="private key or password"):
        scenario.crypto.issue_entitlement(
            request=scenario.request,
            authority_private_key_pem=scenario.authority_private,
            password=b"wrong-password-value",
            max_hosts=10,
            issued_at=scenario.now,
            not_before=scenario.now,
            expires_at=scenario.now + timedelta(days=30),
        )


def test_material_store_uses_atomic_strict_permissions(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    material = LicenseMaterialStore()
    paths = material.write_installation_material(
        tmp_path / "license",
        scenario.identity,
        scenario.request,
        scenario.installation_private,
    )
    entitlement_path = tmp_path / "license" / "entitlement.json"
    material.write_entitlement(entitlement_path, scenario.entitlement())

    assert material.load_identity(paths["identity"]) == scenario.identity
    assert material.load_request(paths["request"]) == scenario.request
    assert stat.S_IMODE((tmp_path / "license").stat().st_mode) == 0o700
    assert material.load_entitlement(entitlement_path).license_id == scenario.identity.license_id
    assert stat.S_IMODE(paths["identity"].stat().st_mode) == 0o600
    assert stat.S_IMODE(paths["private_key"].stat().st_mode) == 0o600
    assert stat.S_IMODE(paths["request"].stat().st_mode) == 0o640
    assert stat.S_IMODE(paths["public_key"].stat().st_mode) == 0o644
    assert stat.S_IMODE(entitlement_path.stat().st_mode) == 0o640
    assert not list((tmp_path / "license").glob(".*.tmp"))


def test_material_store_normalizes_existing_sensitive_directory_permissions(
    tmp_path: Path,
) -> None:
    scenario = LicenseScenario(tmp_path)
    material = LicenseMaterialStore()
    root = tmp_path / "inherited-permissions" / "license"
    root.mkdir(parents=True)
    root.chmod(0o2770)

    material.write_installation_material(
        root,
        scenario.identity,
        scenario.request,
        scenario.installation_private,
    )

    assert stat.S_IMODE(root.stat().st_mode) == 0o700


def test_active_warning_grace_and_expired_states(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.bootstrap()
    entitlement = scenario.entitlement(expires_at=scenario.now + timedelta(days=40))
    scenario.activate(entitlement)

    active = scenario.service.status()
    assert active.status is RuntimeLicenseStatus.ACTIVE
    assert active.runtime_allowed is True
    assert active.notification_level.value == "none"

    scenario.clock.value = entitlement.expires_at - timedelta(days=20)
    warning = scenario.service.status()
    assert warning.status is RuntimeLicenseStatus.ACTIVE
    assert warning.notification_level.value == "warning"

    scenario.clock.value = entitlement.expires_at + timedelta(days=10)
    grace = scenario.service.status()
    assert grace.status is RuntimeLicenseStatus.GRACE
    assert grace.runtime_allowed is True
    assert grace.grace_until == entitlement.expires_at + timedelta(days=30)

    scenario.clock.value = entitlement.expires_at + timedelta(days=31)
    expired = scenario.service.status()
    assert expired.status is RuntimeLicenseStatus.EXPIRED
    assert expired.runtime_allowed is False
    with pytest.raises(LicenseAccessDeniedError):
        scenario.service.require_runtime_access()


def test_clock_rollback_fails_closed(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.bootstrap()
    scenario.activate()
    scenario.clock.value = scenario.now - timedelta(minutes=6)

    report = scenario.service.status()

    assert report.status is RuntimeLicenseStatus.INVALID
    assert report.runtime_allowed is False
    assert "clock rollback" in report.reason


def test_company_edition_installation_and_license_are_cryptographically_bound(
    tmp_path: Path,
) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.bootstrap()
    entitlement = scenario.entitlement()

    for changed in (
        replace(entitlement, company_name="Wrong Company"),
        replace(entitlement, installation_id=str(uuid.uuid4())),
        replace(entitlement, license_id=str(uuid.uuid4())),
    ):
        with pytest.raises(ValidationError, match="does not match"):
            scenario.service.activate(ActivateRuntimeLicenseCommand(changed))


def test_host_quota_is_checked_on_activation_and_runtime_capacity(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.bootstrap()
    scenario.store.data["equipment"] = {
        f"default:host-{index}": {"tenant_id": "default"} for index in range(3)
    }
    scenario.store.mark_dirty()

    with pytest.raises(ValidationError, match="current managed host count"):
        scenario.service.activate(ActivateRuntimeLicenseCommand(scenario.entitlement(max_hosts=2)))

    scenario.activate(scenario.entitlement(max_hosts=3))
    with pytest.raises(LicenseAccessDeniedError, match="quota"):
        scenario.service.require_host_capacity(1)
    assert scenario.service.require_host_capacity(0).current_hosts == 3


def test_renewal_requires_same_license_and_extends_expiration(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.bootstrap()
    current = scenario.activate()

    shorter = scenario.entitlement(expires_at=current.expires_at)
    with pytest.raises(ValidationError, match="must extend"):
        scenario.service.renew(ActivateRuntimeLicenseCommand(shorter))

    _other_identity, another_request, _other_private = scenario.crypto.create_installation_material(
        installation_id=scenario.identity.installation_id,
        license_id=str(uuid.uuid4()),
        company_name=scenario.identity.company_name,
        edition=scenario.identity.edition.value,
        requested_max_hosts=20,
    )
    replacement = scenario.crypto.issue_entitlement(
        request=another_request,
        authority_private_key_pem=scenario.authority_private,
        password=b"correct horse battery staple",
        max_hosts=20,
        issued_at=scenario.now,
        not_before=scenario.now,
        expires_at=current.expires_at + timedelta(days=30),
    )
    with pytest.raises(ValidationError, match="does not match"):
        scenario.service.renew(ActivateRuntimeLicenseCommand(replacement))

    renewed = scenario.entitlement(expires_at=current.expires_at + timedelta(days=365))
    report = scenario.service.renew(ActivateRuntimeLicenseCommand(renewed))
    assert report.status is RuntimeLicenseStatus.ACTIVE
    assert report.expires_at == renewed.expires_at


def test_corrupted_persistence_returns_invalid_report_instead_of_500(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.store.data["runtime_license_state"] = {"identity": "not-an-object"}
    scenario.store.mark_dirty()

    report = scenario.service.status()

    assert report.status is RuntimeLicenseStatus.INVALID
    assert report.runtime_allowed is False
    assert "corrupted" in report.reason
    with pytest.raises(LicenseAccessDeniedError, match="corrupted"):
        scenario.service.require_host_capacity(0)


def test_lite_bypasses_license_and_pro_non_enforced_remains_compatible(tmp_path: Path) -> None:
    store = JsonDocumentStore(tmp_path / "lite.json")
    lite = RuntimeLicenseService(
        edition="lite",
        repository=JsonLicenseRepository(store),
        runtime_usage_repository=JsonRuntimeUsageRepository(store),
        audit_repository=JsonAuditRepository(store),
        transaction_manager=JsonTransactionManager(store),
        cryptography=Ed25519LicenseCryptography(),
        trust_bundle_pem=b"",
        enforcement_enabled=True,
    )
    assert lite.status().status is RuntimeLicenseStatus.NOT_REQUIRED
    assert lite.require_runtime_access().runtime_allowed is True
    lite_capacity = lite.require_host_capacity(1000)
    assert lite_capacity.status is RuntimeLicenseStatus.NOT_REQUIRED
    assert lite_capacity.max_hosts is None

    scenario = LicenseScenario(tmp_path / "compat", enforced=False)
    missing = scenario.service.status()
    assert missing.status is RuntimeLicenseStatus.MISSING
    assert missing.runtime_allowed is True


def test_identity_is_immutable_and_state_parser_fails_closed(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    scenario.bootstrap()
    assert (
        scenario.service.bootstrap_identity(BootstrapInstallationIdentityCommand(scenario.identity))
        == scenario.identity
    )

    other = replace(scenario.identity, installation_id=str(uuid.uuid4()))
    with pytest.raises(ConflictError, match="immutable"):
        scenario.service.bootstrap_identity(BootstrapInstallationIdentityCommand(other))

    with pytest.raises(LicenseStateCorruptedError):
        PersistedLicenseState.from_dict({"identity": "invalid"})


def test_domain_rejects_lite_and_invalid_license_contracts(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    with pytest.raises(ValidationError, match="Lite edition"):
        InstallationIdentity.create(
            installation_id=str(uuid.uuid4()),
            license_id=str(uuid.uuid4()),
            company_name="OpenInfra",
            edition="lite",
            public_key_pem=scenario.identity.public_key_pem,
        )
    with pytest.raises(ValidationError, match="cannot exceed"):
        scenario.crypto.issue_entitlement(
            request=scenario.request,
            authority_private_key_pem=scenario.authority_private,
            password=b"correct horse battery staple",
            max_hosts=scenario.request.requested_max_hosts + 1,
            issued_at=scenario.now,
            not_before=scenario.now,
            expires_at=scenario.now + timedelta(days=30),
        )


def test_domain_rejects_malformed_identity_request_and_entitlement_payloads(
    tmp_path: Path,
) -> None:
    scenario = LicenseScenario(tmp_path)
    identity_kwargs = {
        "installation_id": scenario.identity.installation_id,
        "license_id": scenario.identity.license_id,
        "company_name": scenario.identity.company_name,
        "edition": scenario.identity.edition,
        "public_key_pem": scenario.identity.public_key_pem,
        "created_at": scenario.now,
    }
    for overrides, message in (
        ({"company_name": "x"}, "company name"),
        ({"public_key_pem": "not-a-public-key"}, "PEM public key"),
        ({"installation_id": "not-a-uuid"}, "UUID format"),
        ({"created_at": scenario.now.replace(tzinfo=None)}, "timezone-aware"),
    ):
        with pytest.raises(ValidationError, match=message):
            InstallationIdentity.create(**(identity_kwargs | overrides))

    identity_payload = scenario.identity.as_dict()
    with pytest.raises(ValidationError, match="unsupported installation identity schema"):
        InstallationIdentity.from_dict(identity_payload | {"schema": "invalid"})
    with pytest.raises(ValidationError, match="identity created_at is invalid"):
        InstallationIdentity.from_dict(identity_payload | {"created_at": "not-a-date"})

    with pytest.raises(ValidationError, match="requested licensed hosts"):
        LicenseActivationRequest.create_unsigned(scenario.identity, 0)
    with pytest.raises(ValidationError, match="cannot be empty"):
        LicenseActivationRequest.create_unsigned(scenario.identity, 1).with_signature(b"")
    request_payload = scenario.request.as_dict()
    for payload, message in (
        (request_payload | {"schema": "invalid"}, "unsupported license activation"),
        (request_payload | {"signature": ""}, "signature is required"),
        (request_payload | {"signature": "%%%"}, "signature is invalid"),
    ):
        with pytest.raises(ValidationError, match=message):
            LicenseActivationRequest.from_dict(payload)

    entitlement_kwargs = {
        "installation_id": scenario.identity.installation_id,
        "license_id": scenario.identity.license_id,
        "company_name": scenario.identity.company_name,
        "edition": scenario.identity.edition,
        "installation_public_key_fingerprint": scenario.identity.public_key_fingerprint,
        "max_hosts": 10,
        "issued_at": scenario.now,
        "not_before": scenario.now,
        "expires_at": scenario.now + timedelta(days=30),
        "grace_days": 30,
        "authority_key_id": scenario.authority_key_id,
    }
    invalid_entitlements = (
        ({"company_name": "x"}, "company name"),
        ({"edition": "lite"}, "Lite edition"),
        ({"installation_public_key_fingerprint": "not-sha256"}, "fingerprint"),
        ({"max_hosts": 0}, "licensed hosts"),
        ({"not_before": scenario.now - timedelta(minutes=6)}, "cannot materially precede"),
        ({"expires_at": scenario.now}, "must be after"),
        ({"grace_days": 29}, "grace period"),
        ({"authority_key_id": "short"}, "authority key id"),
    )
    for overrides, message in invalid_entitlements:
        with pytest.raises(ValidationError, match=message):
            LicenseEntitlement.create_unsigned(**(entitlement_kwargs | overrides))

    unsigned = LicenseEntitlement.create_unsigned(**entitlement_kwargs)
    with pytest.raises(ValidationError, match="cannot be empty"):
        unsigned.with_signature(b"")
    entitlement_payload = scenario.entitlement().as_dict()
    for payload, message in (
        (entitlement_payload | {"schema": "invalid"}, "unsupported license entitlement"),
        (entitlement_payload | {"signature": ""}, "signature is required"),
        (entitlement_payload | {"signature": "%%%"}, "signature is invalid"),
    ):
        with pytest.raises(ValidationError, match=message):
            LicenseEntitlement.from_dict(payload)
    with pytest.raises(LicenseStateCorruptedError):
        PersistedLicenseState.from_dict(
            {"identity": identity_payload, "entitlement": "not-an-object"}
        )


def test_crypto_rejects_untrusted_invalid_and_non_ed25519_material(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    with pytest.raises(ValidationError, match="at least 12 bytes"):
        scenario.crypto.generate_authority_material(b"too-short")

    entitlement = scenario.entitlement()
    _other_private, other_public, _other_key_id = scenario.crypto.generate_authority_material(
        b"another secure authority password"
    )
    with pytest.raises(ValidationError, match="not trusted"):
        scenario.crypto.verify_entitlement(entitlement, other_public)
    with pytest.raises(ValidationError, match="does not contain"):
        scenario.crypto.verify_entitlement(entitlement, b"")
    with pytest.raises(ValidationError, match="signature encoding"):
        scenario.crypto.verify_entitlement(
            replace(entitlement, signature="%%%"), scenario.authority_public
        )
    tampered = replace(entitlement, max_hosts=entitlement.max_hosts - 1)
    with pytest.raises(ValidationError, match="authority signature is invalid"):
        scenario.crypto.verify_entitlement(tampered, scenario.authority_public)

    rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_private_pem = rsa_private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"rsa-private-password"),
    )
    with pytest.raises(ValidationError, match="private key must use Ed25519"):
        scenario.crypto.issue_entitlement(
            request=scenario.request,
            authority_private_key_pem=rsa_private_pem,
            password=b"rsa-private-password",
            max_hosts=10,
            issued_at=scenario.now,
            not_before=scenario.now,
            expires_at=scenario.now + timedelta(days=30),
        )
    rsa_public_pem = rsa_private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with pytest.raises(ValidationError, match="public key must use Ed25519"):
        scenario.crypto.public_key_id(rsa_public_pem)
    with pytest.raises(ValidationError, match="public key is invalid"):
        scenario.crypto.public_key_id(b"not-a-key")


def test_material_store_rejects_invalid_documents_and_cleans_failed_atomic_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = LicenseScenario(tmp_path)
    material = LicenseMaterialStore()
    private_path = tmp_path / "authority" / "private.pem"
    public_path = tmp_path / "authority" / "public.pem"
    material.write_authority_material(
        private_path,
        public_path,
        scenario.authority_private,
        scenario.authority_public,
    )
    assert private_path.read_bytes() == scenario.authority_private
    assert public_path.read_bytes() == scenario.authority_public

    unreadable = tmp_path / "invalid.json"
    unreadable.write_text("not-json", encoding="utf-8")
    with pytest.raises(OpenInfraError, match="document is unreadable"):
        material.load_identity(unreadable)
    unreadable.write_text("[]", encoding="utf-8")
    with pytest.raises(ValidationError, match="JSON object"):
        material.load_identity(unreadable)

    failed_path = tmp_path / "failed" / "entitlement.json"
    monkeypatch.setattr(
        licensing_module.os,
        "fsync",
        lambda _descriptor: (_ for _ in ()).throw(OSError("disk failure")),
    )
    with pytest.raises(OSError, match="disk failure"):
        material.write_entitlement(failed_path, scenario.entitlement())
    assert not failed_path.exists()
    assert not list(failed_path.parent.glob(".entitlement.json.*"))


def test_service_covers_pre_activation_future_quota_and_clock_edge_cases(tmp_path: Path) -> None:
    scenario = LicenseScenario(tmp_path)
    with pytest.raises(ValidationError, match="persisted before activation"):
        scenario.service.activate(ActivateRuntimeLicenseCommand(scenario.entitlement()))
    with pytest.raises(ValidationError, match="increment cannot be negative"):
        scenario.service.require_host_capacity(-1)

    enterprise_service = RuntimeLicenseService(
        edition="enterprise",
        repository=scenario.repository,
        runtime_usage_repository=JsonRuntimeUsageRepository(scenario.store),
        audit_repository=JsonAuditRepository(scenario.store),
        transaction_manager=JsonTransactionManager(scenario.store),
        cryptography=scenario.crypto,
        trust_bundle_pem=scenario.authority_public,
        enforcement_enabled=True,
        clock=scenario.clock,
    )
    with pytest.raises(ValidationError, match="edition does not match"):
        enterprise_service.bootstrap_identity(
            BootstrapInstallationIdentityCommand(scenario.identity)
        )

    scenario.bootstrap()
    missing = scenario.service.status()
    assert missing.status is RuntimeLicenseStatus.MISSING
    compatible_missing = LicenseScenario(tmp_path / "missing-compatible", enforced=False)
    compatible_missing.bootstrap()
    assert compatible_missing.service.require_host_capacity(0).max_hosts is None
    with pytest.raises(ValidationError, match="activated before renewal"):
        scenario.service.renew(ActivateRuntimeLicenseCommand(scenario.entitlement()))

    future = scenario.entitlement(
        not_before=scenario.now + timedelta(days=1),
        expires_at=scenario.now + timedelta(days=31),
    )
    scenario.activate(future)
    future_report = scenario.service.status()
    assert future_report.status is RuntimeLicenseStatus.INVALID
    assert "not valid yet" in future_report.reason

    scenario.clock.value = scenario.now + timedelta(days=1)
    scenario.store.data["equipment"] = {
        f"default:host-{index}": {"tenant_id": "default"} for index in range(26)
    }
    scenario.store.mark_dirty()
    over_quota = scenario.service.status()
    assert over_quota.status is RuntimeLicenseStatus.INVALID
    assert "exceeds" in over_quota.reason

    compatibility = LicenseScenario(tmp_path / "compatibility", enforced=False)
    compatibility.bootstrap()
    compatibility.activate(compatibility.entitlement(max_hosts=1))
    compatibility.store.data["equipment"] = {"default:host-1": {"tenant_id": "default"}}
    compatibility.store.mark_dirty()
    blocked_but_compatible = compatibility.service.require_host_capacity(1)
    assert blocked_but_compatible.runtime_allowed is True
    assert blocked_but_compatible.status is RuntimeLicenseStatus.INVALID

    naive_clock = LicenseScenario(tmp_path / "naive")
    naive_clock.clock.value = scenario.now.replace(tzinfo=None)
    with pytest.raises(ValidationError, match="clock must be timezone-aware"):
        naive_clock.service.status()


def test_service_rejects_corrupted_persisted_bindings_during_status_and_renewal(
    tmp_path: Path,
) -> None:
    mismatched_edition = LicenseScenario(tmp_path / "edition")
    enterprise_identity, _request, _private = (
        mismatched_edition.crypto.create_installation_material(
            installation_id=str(uuid.uuid4()),
            license_id=str(uuid.uuid4()),
            company_name="Enterprise Customer SAS",
            edition="enterprise",
            requested_max_hosts=10,
        )
    )
    mismatched_edition.store.data["runtime_license_state"] = PersistedLicenseState(
        enterprise_identity,
        None,
        None,
        None,
    ).as_dict()
    mismatched_edition.store.mark_dirty()
    edition_report = mismatched_edition.service.status()
    assert edition_report.status is RuntimeLicenseStatus.INVALID
    assert "edition does not match" in edition_report.reason

    invalid_signature = LicenseScenario(tmp_path / "signature")
    invalid_signature.bootstrap()
    tampered = replace(invalid_signature.entitlement(), max_hosts=24)
    invalid_signature.store.data["runtime_license_state"] = PersistedLicenseState(
        invalid_signature.identity,
        tampered,
        invalid_signature.now,
        invalid_signature.now,
    ).as_dict()
    invalid_signature.store.mark_dirty()
    signature_report = invalid_signature.service.status()
    assert signature_report.status is RuntimeLicenseStatus.INVALID
    assert "signature is invalid" in signature_report.reason

    renewal = LicenseScenario(tmp_path / "renewal")
    renewal.bootstrap()
    active = renewal.entitlement()
    corrupted_active = replace(active, license_id=str(uuid.uuid4()))
    renewal.store.data["runtime_license_state"] = PersistedLicenseState(
        renewal.identity,
        corrupted_active,
        renewal.now,
        renewal.now,
    ).as_dict()
    renewal.store.mark_dirty()
    extended = renewal.entitlement(expires_at=active.expires_at + timedelta(days=30))
    with pytest.raises(ValidationError, match="renewal license id must match"):
        renewal.service.renew(ActivateRuntimeLicenseCommand(extended))
