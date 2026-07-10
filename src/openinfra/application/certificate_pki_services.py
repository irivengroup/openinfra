from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from openinfra.application.ports import (
    AuditRepository,
    CertificateAssetPage,
    CertificateEndpointPage,
    CertificateInventoryRepository,
    CertificateParser,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.certificate_pki import (
    CertificateAssessment,
    CertificateAsset,
    CertificateEndpointObservation,
    CertificateHealth,
    CertificateInventoryReport,
)
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class ImportCertificateBundleCommand:
    tenant_id: str
    actor: str
    admin_token: str
    pem_bundle: str
    owner: str
    environment: str
    source: str
    object_key: str | None = None


@dataclass(frozen=True, slots=True)
class CertificateImportResult:
    leaf: CertificateAsset
    certificates: tuple[CertificateAsset, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "leaf": self.leaf.as_dict(),
            "certificates": [item.as_dict() for item in self.certificates],
            "certificate_count": len(self.certificates),
        }


@dataclass(frozen=True, slots=True)
class GetCertificateCommand:
    tenant_id: str
    admin_token: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ListCertificatesCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class RetireCertificateCommand:
    tenant_id: str
    actor: str
    admin_token: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ObserveCertificateEndpointCommand:
    tenant_id: str
    actor: str
    admin_token: str
    idempotency_key: str
    protocol: str
    host: str
    port: int
    service: str
    certificate_fingerprint: str
    observed_at: str | datetime
    source: str
    collector: str
    object_key: str | None = None
    tls_version: str | None = None
    cipher: str | None = None


@dataclass(frozen=True, slots=True)
class ListCertificateEndpointsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    certificate_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class AssessCertificatesCommand:
    tenant_id: str
    admin_token: str
    as_of: str | datetime | None = None
    critical_days: int = 7
    warning_days: int = 30
    health: str | None = None
    limit: int = 100
    cursor: str | None = None


class CertificatePkiService:
    _PAGE_SIZE = 500
    _MAX_CERTIFICATES = 5_000
    _MAX_ENDPOINTS = 10_000

    def __init__(
        self,
        repository: CertificateInventoryRepository,
        parser: CertificateParser,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def import_bundle(self, command: ImportCertificateBundleCommand) -> CertificateImportResult:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_WRITE
        )
        actor = self._actor(command.actor, subject)
        materials = self._parser.parse_pem_bundle(command.pem_bundle)
        fingerprints = tuple(item.fingerprint_sha256 for item in materials)
        persisted: list[CertificateAsset] = []
        with self._transaction_manager.begin() as unit_of_work:
            for index, material in enumerate(materials):
                chain = fingerprints[index + 1 :]
                existing = self._repository.get_certificate_by_fingerprint(
                    tenant_id, material.fingerprint_sha256
                )
                if existing is not None and not existing.material_matches(material):
                    raise ConflictError(
                        "certificate fingerprint already exists with inconsistent "
                        "immutable material"
                    )
                if existing is None:
                    certificate = CertificateAsset.create(
                        tenant_id=tenant_id,
                        material=material,
                        chain_fingerprints=chain,
                        owner=command.owner,
                        environment=command.environment,
                        source=command.source,
                        object_key=command.object_key if index == 0 else None,
                        actor=actor,
                    )
                    action = "certificate.inventory.create"
                else:
                    certificate = existing.revise_governance(
                        chain_fingerprints=chain,
                        owner=command.owner if index == 0 else existing.owner,
                        environment=command.environment if index == 0 else existing.environment,
                        source=command.source if index == 0 else existing.source.value,
                        object_key=(
                            command.object_key
                            if index == 0
                            else (
                                None if existing.object_key is None else existing.object_key.value
                            )
                        ),
                        actor=actor,
                    )
                    action = "certificate.inventory.update"
                self._repository.save_certificate(certificate)
                persisted.append(certificate)
                self._audit_repository.append(
                    AuditEvent.record(
                        tenant_id=tenant_id,
                        actor=actor,
                        action=action,
                        target_type="certificate",
                        target_id=certificate.fingerprint_sha256,
                        metadata={
                            "subject_dn": certificate.material.subject_dn,
                            "issuer_dn": certificate.material.issuer_dn,
                            "owner": certificate.owner,
                            "environment": certificate.environment,
                            "is_leaf": index == 0,
                            "chain_length": len(chain),
                            "version": certificate.version,
                        },
                    )
                )
            unit_of_work.commit()
        return CertificateImportResult(persisted[0], tuple(persisted))

    def get_certificate(self, command: GetCertificateCommand) -> CertificateAsset:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_READ
        )
        certificate = self._repository.get_certificate_by_fingerprint(
            tenant_id, command.fingerprint
        )
        if certificate is None:
            raise NotFoundError("certificate not found")
        return certificate

    def list_certificates(self, command: ListCertificatesCommand) -> CertificateAssetPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_READ
        )
        return self._repository.list_certificates(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            include_retired=command.include_retired,
        )

    def retire_certificate(self, command: RetireCertificateCommand) -> CertificateAsset:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_WRITE
        )
        actor = self._actor(command.actor, subject)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.get_certificate_by_fingerprint(
                tenant_id, command.fingerprint
            )
            if existing is None:
                raise NotFoundError("certificate not found")
            certificate = existing.retire(actor)
            self._repository.save_certificate(certificate)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="certificate.inventory.retire",
                    target_type="certificate",
                    target_id=certificate.fingerprint_sha256,
                    metadata={"owner": certificate.owner, "version": certificate.version},
                )
            )
            unit_of_work.commit()
        return certificate

    def observe_endpoint(
        self, command: ObserveCertificateEndpointCommand
    ) -> CertificateEndpointObservation:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_WRITE
        )
        actor = self._actor(command.actor, subject)
        observed_at = self._required_datetime(command.observed_at, "observed_at")
        observation = CertificateEndpointObservation.create(
            tenant_id=tenant_id,
            idempotency_key=command.idempotency_key,
            protocol=command.protocol,
            host=command.host,
            port=command.port,
            service=command.service,
            certificate_fingerprint=command.certificate_fingerprint,
            observed_at=observed_at,
            source=command.source,
            collector=command.collector,
            object_key=command.object_key,
            tls_version=command.tls_version,
            cipher=command.cipher,
        )
        with self._transaction_manager.begin() as unit_of_work:
            certificate = self._repository.get_certificate_by_fingerprint(
                tenant_id, observation.certificate_fingerprint
            )
            if certificate is None:
                raise NotFoundError("certificate endpoint references an unknown certificate")
            existing = self._repository.find_endpoint_by_idempotency_key(
                tenant_id, observation.idempotency_key
            )
            if existing is not None:
                if existing.payload_fingerprint != observation.payload_fingerprint:
                    raise ConflictError(
                        "certificate endpoint idempotency key already exists with "
                        "a different payload"
                    )
                unit_of_work.commit()
                return existing
            self._repository.save_endpoint_observation(observation)
            persisted = self._repository.find_endpoint_by_idempotency_key(
                tenant_id, observation.idempotency_key
            )
            if persisted is None:
                raise ConflictError("certificate endpoint observation could not be persisted")
            if persisted.payload_fingerprint != observation.payload_fingerprint:
                raise ConflictError(
                    "certificate endpoint idempotency key already exists with a different payload"
                )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="certificate.endpoint.observe",
                    target_type="certificate_endpoint",
                    target_id=persisted.id.value,
                    metadata={
                        "endpoint": persisted.endpoint,
                        "certificate_fingerprint": persisted.certificate_fingerprint,
                        "hostname_matches": certificate.matches_hostname(persisted.host),
                        "source": persisted.source.value,
                    },
                    severity=(
                        Severity.INFO
                        if certificate.matches_hostname(persisted.host)
                        else Severity.WARNING
                    ),
                )
            )
            unit_of_work.commit()
        return persisted

    def list_endpoints(self, command: ListCertificateEndpointsCommand) -> CertificateEndpointPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_READ
        )
        return self._repository.list_endpoint_observations(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.certificate_fingerprint,
        )

    def assess(self, command: AssessCertificatesCommand) -> CertificateInventoryReport:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.CERTIFICATE_READ
        )
        reference = self._datetime(command.as_of) or datetime.now(UTC)
        if not 0 <= command.critical_days <= command.warning_days <= 3_650:
            raise ValidationError("certificate expiry thresholds are invalid")
        health_filter = self._health(command.health)
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            certificates, certificates_truncated = self._all_certificates(tenant_id)
            endpoints, endpoints_truncated = self._all_endpoints(tenant_id)
            certificate_by_fingerprint = {item.fingerprint_sha256: item for item in certificates}
            endpoint_by_certificate: dict[str, list[CertificateEndpointObservation]] = {}
            for endpoint in endpoints:
                endpoint_by_certificate.setdefault(endpoint.certificate_fingerprint, []).append(
                    endpoint
                )
            assessments: list[CertificateAssessment] = []
            totals = {health.value: 0 for health in CertificateHealth}
            for certificate in certificates:
                health = certificate.health(reference, command.critical_days, command.warning_days)
                totals[health.value] += 1
                related = endpoint_by_certificate.get(certificate.fingerprint_sha256, [])
                endpoint_names = tuple(sorted({item.endpoint for item in related}))
                mismatch_count = sum(
                    1 for item in related if not certificate.matches_hostname(item.host)
                )
                missing = tuple(
                    fingerprint
                    for fingerprint in certificate.chain_fingerprints
                    if fingerprint not in certificate_by_fingerprint
                )
                chain_complete = self._chain_complete(
                    certificate, certificate_by_fingerprint, missing
                )
                assessment = CertificateAssessment(
                    certificate=certificate,
                    health=health,
                    days_remaining=certificate.days_remaining(reference),
                    endpoint_count=len(endpoint_names),
                    endpoints=endpoint_names,
                    hostname_mismatch_count=mismatch_count,
                    chain_complete=chain_complete,
                    missing_chain_fingerprints=missing,
                )
                if health_filter is None or health is health_filter:
                    assessments.append(assessment)
            assessments.sort(
                key=lambda item: (
                    self._health_rank(item.health),
                    item.certificate.material.not_after,
                    item.certificate.fingerprint_sha256,
                )
            )
            offset = self._offset(pagination.cursor)
            selected = tuple(assessments[offset : offset + pagination.limit])
            next_index = offset + len(selected)
            next_cursor = str(next_index) if next_index < len(assessments) else None
            report = CertificateInventoryReport(
                as_of=reference,
                critical_days=command.critical_days,
                warning_days=command.warning_days,
                items=selected,
                totals=totals,
                next_cursor=next_cursor,
                truncated=certificates_truncated or endpoints_truncated,
            )
            risky = sum(
                totals[item.value]
                for item in (
                    CertificateHealth.EXPIRED,
                    CertificateHealth.CRITICAL,
                    CertificateHealth.NOT_YET_VALID,
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="certificate.inventory.assess",
                    target_type="certificate_inventory",
                    target_id=reference.isoformat(),
                    metadata={
                        "totals": totals,
                        "critical_days": command.critical_days,
                        "warning_days": command.warning_days,
                        "health_filter": health_filter.value if health_filter else None,
                        "truncated": report.truncated,
                    },
                    severity=Severity.WARNING if risky else Severity.INFO,
                )
            )
            unit_of_work.commit()
        return report

    def _all_certificates(self, tenant_id: TenantId) -> tuple[tuple[CertificateAsset, ...], bool]:
        items: list[CertificateAsset] = []
        cursor: str | None = None
        seen: set[str] = set()
        while len(items) < self._MAX_CERTIFICATES:
            page = self._repository.list_certificates(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_CERTIFICATES - len(items)), cursor
                ),
                include_retired=True,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items), False
            if page.next_cursor in seen:
                raise ValidationError("certificate repository returned a cyclic cursor")
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        return tuple(items), cursor is not None

    def _all_endpoints(
        self, tenant_id: TenantId
    ) -> tuple[tuple[CertificateEndpointObservation, ...], bool]:
        items: list[CertificateEndpointObservation] = []
        cursor: str | None = None
        seen: set[str] = set()
        while len(items) < self._MAX_ENDPOINTS:
            page = self._repository.list_endpoint_observations(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_ENDPOINTS - len(items)), cursor
                ),
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items), False
            if page.next_cursor in seen:
                raise ValidationError("certificate endpoint repository returned a cyclic cursor")
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        return tuple(items), cursor is not None

    @staticmethod
    def _chain_complete(
        certificate: CertificateAsset,
        inventory: dict[str, CertificateAsset],
        missing: tuple[str, ...],
    ) -> bool:
        if missing:
            return False
        if not certificate.chain_fingerprints:
            return (
                certificate.material.is_ca
                and certificate.material.subject_dn == certificate.material.issuer_dn
            )
        root = inventory[certificate.chain_fingerprints[-1]]
        return root.material.is_ca and root.material.subject_dn == root.material.issuer_dn

    def _authorize(self, tenant: str, token: str, permission: Permission) -> tuple[TenantId, str]:
        tenant_id = TenantId.from_value(tenant)
        authentication = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, token, permission)
        )
        return tenant_id, authentication.subject

    @staticmethod
    def _actor(actor: str, subject: str) -> str:
        normalized = " ".join(actor.strip().split())
        return normalized or subject

    @staticmethod
    def _datetime(value: str | datetime | None) -> datetime | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError("certificate date must use ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ValidationError("certificate date must be timezone-aware")
        return parsed.astimezone(UTC)

    @classmethod
    def _required_datetime(cls, value: str | datetime, label: str) -> datetime:
        parsed = cls._datetime(value)
        if parsed is None:
            raise ValidationError(f"{label} is required")
        return parsed

    @staticmethod
    def _health(value: str | None) -> CertificateHealth | None:
        if value is None or value.strip() == "":
            return None
        try:
            return CertificateHealth(value.strip().lower().replace("_", "-"))
        except ValueError as exc:
            raise ValidationError("certificate health filter is unsupported") from exc

    @staticmethod
    def _offset(cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset

    @staticmethod
    def _health_rank(health: CertificateHealth) -> int:
        return {
            CertificateHealth.EXPIRED: 0,
            CertificateHealth.CRITICAL: 1,
            CertificateHealth.NOT_YET_VALID: 2,
            CertificateHealth.WARNING: 3,
            CertificateHealth.HEALTHY: 4,
            CertificateHealth.RETIRED: 5,
        }[health]
