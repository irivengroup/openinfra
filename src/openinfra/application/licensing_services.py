from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from openinfra.application.ports import (
    AuditRepository,
    LicenseCryptography,
    LicenseRepository,
    RuntimeUsageRepository,
    TransactionManager,
)
from openinfra.domain.common import AuditEvent, ConflictError, TenantId, ValidationError
from openinfra.domain.editions import OpenInfraEdition, QuotaResource
from openinfra.domain.licensing import (
    InstallationIdentity,
    LicenseAccessDeniedError,
    LicenseEntitlement,
    LicenseNotificationLevel,
    LicenseStateCorruptedError,
    PersistedLicenseState,
    RuntimeLicenseReport,
    RuntimeLicenseStatus,
)


@dataclass(frozen=True, slots=True)
class ActivateRuntimeLicenseCommand:
    entitlement: LicenseEntitlement
    actor: str = "system"


@dataclass(frozen=True, slots=True)
class BootstrapInstallationIdentityCommand:
    identity: InstallationIdentity
    actor: str = "installer"


class RuntimeLicenseService:
    _CLOCK_ROLLBACK_TOLERANCE = timedelta(minutes=5)
    _LAST_SEEN_WRITE_INTERVAL = timedelta(hours=1)
    _EXPIRY_WARNING_WINDOW = timedelta(days=30)

    def __init__(
        self,
        *,
        edition: str | OpenInfraEdition,
        repository: LicenseRepository,
        runtime_usage_repository: RuntimeUsageRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        cryptography: LicenseCryptography,
        trust_bundle_pem: bytes,
        enforcement_enabled: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._edition = OpenInfraEdition.from_value(edition)
        self._repository = repository
        self._runtime_usage_repository = runtime_usage_repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._cryptography = cryptography
        self._trust_bundle_pem = trust_bundle_pem
        self._enforcement_enabled = bool(enforcement_enabled)
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def enforcement_enabled(self) -> bool:
        return self._enforcement_enabled and self._edition is not OpenInfraEdition.LITE

    def bootstrap_identity(
        self, command: BootstrapInstallationIdentityCommand
    ) -> InstallationIdentity:
        identity = command.identity
        if identity.edition is not self._edition:
            raise ValidationError("installation identity edition does not match runtime edition")
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.get_state()
            if existing is not None:
                if existing.identity != identity:
                    raise ConflictError(
                        "an immutable installation identity already exists for this runtime"
                    )
                return existing.identity
            self._repository.save_identity(identity)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=TenantId.from_value("default"),
                    actor=command.actor.strip() or "installer",
                    action="license.installation_identity.created",
                    target_type="runtime_license",
                    target_id=identity.installation_id,
                    metadata={
                        "license_id": identity.license_id,
                        "company_name": identity.company_name,
                        "edition": identity.edition.value,
                        "public_key_fingerprint": identity.public_key_fingerprint,
                    },
                )
            )
            unit_of_work.commit()
        return identity

    def activate(self, command: ActivateRuntimeLicenseCommand) -> RuntimeLicenseReport:
        return self._install_entitlement(command, renewal=False)

    def renew(self, command: ActivateRuntimeLicenseCommand) -> RuntimeLicenseReport:
        return self._install_entitlement(command, renewal=True)

    def status(self) -> RuntimeLicenseReport:
        now = self._now()
        if self._edition is OpenInfraEdition.LITE:
            return self._report(
                now=now,
                status=RuntimeLicenseStatus.NOT_REQUIRED,
                license_allowed=True,
                reason="Lite edition does not require a commercial runtime license",
                notification_level=LicenseNotificationLevel.NONE,
            )
        try:
            with self._transaction_manager.begin() as unit_of_work:
                state = self._repository.get_state()
                report, update_last_seen = self._evaluate_state(state, now)
                if update_last_seen and state is not None:
                    self._repository.update_last_seen(state.identity.installation_id, now)
                    unit_of_work.commit()
                return report
        except LicenseStateCorruptedError:
            return self._report(
                now=now,
                status=RuntimeLicenseStatus.INVALID,
                license_allowed=False,
                reason="persisted runtime license state is corrupted",
                notification_level=LicenseNotificationLevel.CRITICAL,
            )

    def require_runtime_access(self) -> RuntimeLicenseReport:
        report = self.status()
        if not report.runtime_allowed:
            raise LicenseAccessDeniedError(report)
        return report

    def require_host_capacity(self, requested_increment: int) -> RuntimeLicenseReport:
        with self._transaction_manager.begin() as unit_of_work:
            report = self.require_host_capacity_in_current_transaction(requested_increment)
            unit_of_work.commit()
            return report

    def require_host_capacity_in_current_transaction(
        self, requested_increment: int
    ) -> RuntimeLicenseReport:
        if requested_increment < 0:
            raise ValidationError("licensed host increment cannot be negative")
        now = self._now()
        if self._edition is OpenInfraEdition.LITE:
            return self._report(
                now=now,
                status=RuntimeLicenseStatus.NOT_REQUIRED,
                license_allowed=True,
                reason="Lite edition does not require a commercial runtime license",
                notification_level=LicenseNotificationLevel.NONE,
            )
        try:
            state = self._repository.get_state()
            if state is not None:
                self._repository.lock_state(state.identity.installation_id)
            report, update_last_seen = self._evaluate_state(state, now)
            if update_last_seen and state is not None:
                self._repository.update_last_seen(state.identity.installation_id, now)
        except LicenseStateCorruptedError:
            report = self._report(
                now=now,
                status=RuntimeLicenseStatus.INVALID,
                license_allowed=False,
                reason="persisted runtime license state is corrupted",
                notification_level=LicenseNotificationLevel.CRITICAL,
            )
        if not report.runtime_allowed:
            raise LicenseAccessDeniedError(report)
        if report.max_hosts is None:
            return report
        if report.current_hosts + requested_increment <= report.max_hosts:
            return report
        blocked = RuntimeLicenseReport(
            edition=report.edition,
            enforcement_enabled=report.enforcement_enabled,
            status=RuntimeLicenseStatus.INVALID,
            runtime_allowed=not report.enforcement_enabled,
            reason="licensed host quota would be exceeded",
            notification_level=LicenseNotificationLevel.CRITICAL,
            checked_at=report.checked_at,
            company_name=report.company_name,
            installation_id=report.installation_id,
            license_id=report.license_id,
            current_hosts=report.current_hosts,
            max_hosts=report.max_hosts,
            expires_at=report.expires_at,
            grace_until=report.grace_until,
            days_until_expiry=report.days_until_expiry,
        )
        if not blocked.runtime_allowed:
            raise LicenseAccessDeniedError(blocked)
        return blocked

    def _install_entitlement(
        self,
        command: ActivateRuntimeLicenseCommand,
        *,
        renewal: bool,
    ) -> RuntimeLicenseReport:
        now = self._now()
        entitlement = command.entitlement
        with self._transaction_manager.begin() as unit_of_work:
            state = self._repository.get_state()
            if state is None:
                raise ValidationError("installation identity must be persisted before activation")
            identity = state.identity
            self._repository.lock_state(identity.installation_id)
            self._assert_binding(identity, entitlement)
            self._cryptography.verify_entitlement(entitlement, self._trust_bundle_pem)
            current_hosts = self._runtime_usage_repository.count_resource(
                TenantId.from_value("default"), QuotaResource.EQUIPMENT
            )
            if current_hosts > entitlement.max_hosts:
                raise ValidationError(
                    "current managed host count exceeds the issued license host limit"
                )
            if renewal:
                current = state.entitlement
                if current is None:
                    raise ValidationError("runtime license must be activated before renewal")
                if current.license_id != entitlement.license_id:
                    raise ValidationError("renewal license id must match the active license")
                if entitlement.expires_at <= current.expires_at:
                    raise ValidationError("renewal expiration must extend the active license")
            self._repository.save_activation(entitlement, now, now)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=TenantId.from_value("default"),
                    actor=command.actor.strip() or "system",
                    action=("license.runtime.renewed" if renewal else "license.runtime.activated"),
                    target_type="runtime_license",
                    target_id=entitlement.installation_id,
                    metadata={
                        "license_id": entitlement.license_id,
                        "company_name": entitlement.company_name,
                        "edition": entitlement.edition.value,
                        "max_hosts": entitlement.max_hosts,
                        "expires_at": entitlement.expires_at.isoformat(),
                        "grace_until": entitlement.grace_until.isoformat(),
                        "authority_key_id": entitlement.authority_key_id,
                    },
                )
            )
            unit_of_work.commit()
        return self.status()

    def _evaluate_state(
        self,
        state: PersistedLicenseState | None,
        now: datetime,
    ) -> tuple[RuntimeLicenseReport, bool]:
        if state is None:
            return (
                self._report(
                    now=now,
                    status=RuntimeLicenseStatus.MISSING,
                    license_allowed=False,
                    reason="installation identity and runtime license are missing",
                    notification_level=LicenseNotificationLevel.CRITICAL,
                ),
                False,
            )
        identity = state.identity
        entitlement = state.entitlement
        if identity.edition is not self._edition:
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.INVALID,
                False,
                "persisted installation edition does not match runtime edition",
                LicenseNotificationLevel.CRITICAL,
            ), False
        if entitlement is None:
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.MISSING,
                False,
                "runtime license activation is missing",
                LicenseNotificationLevel.CRITICAL,
            ), False
        try:
            self._assert_binding(identity, entitlement)
            self._cryptography.verify_entitlement(entitlement, self._trust_bundle_pem)
        except ValidationError as exc:
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.INVALID,
                False,
                str(exc),
                LicenseNotificationLevel.CRITICAL,
            ), False
        if (
            state.last_seen_at is not None
            and now + self._CLOCK_ROLLBACK_TOLERANCE < state.last_seen_at
        ):
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.INVALID,
                False,
                "system clock rollback detected by runtime license policy",
                LicenseNotificationLevel.CRITICAL,
            ), False
        current_hosts = self._runtime_usage_repository.count_resource(
            TenantId.from_value("default"), QuotaResource.EQUIPMENT
        )
        if current_hosts > entitlement.max_hosts:
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.INVALID,
                False,
                "managed host count exceeds the licensed host quota",
                LicenseNotificationLevel.CRITICAL,
                current_hosts=current_hosts,
            ), self._should_update_last_seen(state, now)
        if now < entitlement.not_before:
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.INVALID,
                False,
                "runtime license is not valid yet",
                LicenseNotificationLevel.CRITICAL,
                current_hosts=current_hosts,
            ), self._should_update_last_seen(state, now)
        if now <= entitlement.expires_at:
            notification = (
                LicenseNotificationLevel.WARNING
                if entitlement.expires_at - now <= self._EXPIRY_WARNING_WINDOW
                else LicenseNotificationLevel.NONE
            )
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.ACTIVE,
                True,
                "runtime license is active",
                notification,
                current_hosts=current_hosts,
            ), self._should_update_last_seen(state, now)
        if now <= entitlement.grace_until:
            return self._bound_report(
                state,
                now,
                RuntimeLicenseStatus.GRACE,
                True,
                "runtime license is expired and operating in the 30-day renewal grace period",
                LicenseNotificationLevel.CRITICAL,
                current_hosts=current_hosts,
            ), self._should_update_last_seen(state, now)
        return self._bound_report(
            state,
            now,
            RuntimeLicenseStatus.EXPIRED,
            False,
            "runtime license and 30-day renewal grace period are expired",
            LicenseNotificationLevel.CRITICAL,
            current_hosts=current_hosts,
        ), self._should_update_last_seen(state, now)

    def _assert_binding(
        self,
        identity: InstallationIdentity,
        entitlement: LicenseEntitlement,
    ) -> None:
        expected = (
            identity.installation_id,
            identity.license_id,
            identity.company_name,
            identity.edition,
            identity.public_key_fingerprint,
        )
        actual = (
            entitlement.installation_id,
            entitlement.license_id,
            entitlement.company_name,
            entitlement.edition,
            entitlement.installation_public_key_fingerprint,
        )
        if actual != expected:
            raise ValidationError(
                "runtime license does not match installation, license UUID, company or edition"
            )

    def _bound_report(
        self,
        state: PersistedLicenseState,
        now: datetime,
        status: RuntimeLicenseStatus,
        license_allowed: bool,
        reason: str,
        notification_level: LicenseNotificationLevel,
        *,
        current_hosts: int = 0,
    ) -> RuntimeLicenseReport:
        entitlement = state.entitlement
        days_until_expiry = None
        if entitlement is not None:
            days_until_expiry = (entitlement.expires_at.date() - now.date()).days
        return self._report(
            now=now,
            status=status,
            license_allowed=license_allowed,
            reason=reason,
            notification_level=notification_level,
            company_name=state.identity.company_name,
            installation_id=state.identity.installation_id,
            license_id=state.identity.license_id,
            current_hosts=current_hosts,
            max_hosts=entitlement.max_hosts if entitlement else None,
            expires_at=entitlement.expires_at if entitlement else None,
            grace_until=entitlement.grace_until if entitlement else None,
            days_until_expiry=days_until_expiry,
        )

    def _report(
        self,
        *,
        now: datetime,
        status: RuntimeLicenseStatus,
        license_allowed: bool,
        reason: str,
        notification_level: LicenseNotificationLevel,
        company_name: str | None = None,
        installation_id: str | None = None,
        license_id: str | None = None,
        current_hosts: int = 0,
        max_hosts: int | None = None,
        expires_at: datetime | None = None,
        grace_until: datetime | None = None,
        days_until_expiry: int | None = None,
    ) -> RuntimeLicenseReport:
        enforced = self.enforcement_enabled
        return RuntimeLicenseReport(
            edition=self._edition,
            enforcement_enabled=enforced,
            status=status,
            runtime_allowed=license_allowed or not enforced,
            reason=reason,
            notification_level=notification_level,
            checked_at=now,
            company_name=company_name,
            installation_id=installation_id,
            license_id=license_id,
            current_hosts=current_hosts,
            max_hosts=max_hosts,
            expires_at=expires_at,
            grace_until=grace_until,
            days_until_expiry=days_until_expiry,
        )

    def _should_update_last_seen(self, state: PersistedLicenseState, now: datetime) -> bool:
        return (
            state.last_seen_at is None or now - state.last_seen_at >= self._LAST_SEEN_WRITE_INTERVAL
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError("runtime license clock must be timezone-aware")
        return value.astimezone(UTC)
