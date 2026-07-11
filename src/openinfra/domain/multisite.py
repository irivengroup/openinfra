from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from typing import Self

from openinfra.domain.common import Code, EntityId, TenantId, ValidationError


class SiteAccessLevel(IntEnum):
    VIEWER = 10
    OPERATOR = 20
    ADMIN = 30

    @classmethod
    def from_value(cls, value: str | SiteAccessLevel) -> Self:
        if isinstance(value, SiteAccessLevel):
            return cls(value)
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"viewer": cls.VIEWER, "operator": cls.OPERATOR, "admin": cls.ADMIN}
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValidationError("site access level must be viewer, operator or admin") from exc

    @property
    def label(self) -> str:
        return self.name.lower()


class MultisiteValidator:
    _SUBJECT = re.compile(r"[a-z0-9][a-z0-9_.@:-]{1,126}[a-z0-9]")

    @classmethod
    def subject(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not cls._SUBJECT.fullmatch(normalized):
            raise ValidationError("multisite subject must use 3 to 128 safe characters")
        return normalized

    @staticmethod
    def actor(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 128:
            raise ValidationError("multisite actor must contain 1 to 128 characters")
        return normalized

    @staticmethod
    def aware(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class SiteAccessGrant:
    id: EntityId
    tenant_id: TenantId
    subject: str
    site_code: str
    access_level: SiteAccessLevel
    active: bool
    granted_by: str
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        subject: str,
        site_code: str,
        access_level: str | SiteAccessLevel,
        granted_by: str,
        now: datetime | None = None,
    ) -> Self:
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            subject=MultisiteValidator.subject(subject),
            site_code=Code.from_value(site_code, "site code").value,
            access_level=SiteAccessLevel.from_value(access_level),
            active=True,
            granted_by=MultisiteValidator.actor(granted_by),
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        subject: str,
        site_code: str,
        access_level: str | SiteAccessLevel,
        active: bool,
        granted_by: str,
        created_at: datetime,
        updated_at: datetime,
        revoked_at: datetime | None = None,
    ) -> Self:
        normalized_revoked_at = (
            None if revoked_at is None else MultisiteValidator.aware(revoked_at, "revoked_at")
        )
        normalized_active = bool(active)
        if normalized_active and normalized_revoked_at is not None:
            raise ValidationError("active site access grant cannot have a revocation date")
        if not normalized_active and normalized_revoked_at is None:
            raise ValidationError("inactive site access grant requires a revocation date")
        return cls(
            id=id,
            tenant_id=tenant_id,
            subject=MultisiteValidator.subject(subject),
            site_code=Code.from_value(site_code, "site code").value,
            access_level=SiteAccessLevel.from_value(access_level),
            active=normalized_active,
            granted_by=MultisiteValidator.actor(granted_by),
            created_at=MultisiteValidator.aware(created_at, "created_at"),
            updated_at=MultisiteValidator.aware(updated_at, "updated_at"),
            revoked_at=normalized_revoked_at,
        )

    def revise(
        self,
        access_level: str | SiteAccessLevel,
        granted_by: str,
        now: datetime | None = None,
    ) -> Self:
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return replace(
            self,
            access_level=SiteAccessLevel.from_value(access_level),
            active=True,
            granted_by=MultisiteValidator.actor(granted_by),
            updated_at=timestamp,
            revoked_at=None,
        )

    def revoke(self, actor: str, now: datetime | None = None) -> Self:
        if not self.active:
            return self
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return replace(
            self,
            active=False,
            granted_by=MultisiteValidator.actor(actor),
            updated_at=timestamp,
            revoked_at=timestamp,
        )

    def allows(self, required: str | SiteAccessLevel) -> bool:
        return self.active and self.access_level >= SiteAccessLevel.from_value(required)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "subject": self.subject,
            "site_code": self.site_code,
            "access_level": self.access_level.label,
            "active": self.active,
            "granted_by": self.granted_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }


@dataclass(frozen=True, slots=True)
class SitePortfolioEntry:
    site_code: str
    site_name: str
    country: str
    city: str
    status: str
    buildings: int
    floors: int
    rooms: int
    racks: int
    equipment: int

    def as_dict(self) -> dict[str, object]:
        return {
            "site_code": self.site_code,
            "site_name": self.site_name,
            "country": self.country,
            "city": self.city,
            "status": self.status,
            "buildings": self.buildings,
            "floors": self.floors,
            "rooms": self.rooms,
            "racks": self.racks,
            "equipment": self.equipment,
        }


@dataclass(frozen=True, slots=True)
class MultisitePortfolioReport:
    id: EntityId
    tenant_id: TenantId
    requested_subject: str
    generated_by: str
    generated_at: datetime
    sites: tuple[SitePortfolioEntry, ...]

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        requested_subject: str,
        generated_by: str,
        sites: tuple[SitePortfolioEntry, ...],
        now: datetime | None = None,
    ) -> Self:
        if not sites:
            raise ValidationError("multisite report requires at least one accessible site")
        if len(sites) > 500:
            raise ValidationError("multisite report cannot contain more than 500 sites")
        codes = [item.site_code for item in sites]
        if len(codes) != len(set(codes)):
            raise ValidationError("multisite report cannot contain duplicate sites")
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            requested_subject=MultisiteValidator.subject(requested_subject),
            generated_by=MultisiteValidator.actor(generated_by),
            generated_at=timestamp,
            sites=tuple(sorted(sites, key=lambda item: item.site_code)),
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        requested_subject: str,
        generated_by: str,
        generated_at: datetime,
        sites: tuple[SitePortfolioEntry, ...],
    ) -> Self:
        restored = cls.create(
            tenant_id,
            requested_subject,
            generated_by,
            sites,
            MultisiteValidator.aware(generated_at, "generated_at"),
        )
        return replace(restored, id=id)

    @property
    def totals(self) -> dict[str, int]:
        return {
            "sites": len(self.sites),
            "buildings": sum(item.buildings for item in self.sites),
            "floors": sum(item.floors for item in self.sites),
            "rooms": sum(item.rooms for item in self.sites),
            "racks": sum(item.racks for item in self.sites),
            "equipment": sum(item.equipment for item in self.sites),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "requested_subject": self.requested_subject,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat(),
            "totals": self.totals,
            "sites": [item.as_dict() for item in self.sites],
        }


@dataclass(frozen=True, slots=True)
class RegionalDiscoveryRoute:
    id: EntityId
    tenant_id: TenantId
    region_code: str
    site_code: str
    vrf_code: str
    collector_id: EntityId
    discovery_scope: str
    active: bool
    configured_by: str
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        region_code: str,
        site_code: str,
        vrf_code: str,
        collector_id: str | EntityId,
        configured_by: str,
        now: datetime | None = None,
    ) -> Self:
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        region = Code.from_value(region_code, "region code").value
        site = Code.from_value(site_code, "site code").value
        vrf = Code.from_value(vrf_code, "VRF code").value
        collector = (
            collector_id
            if isinstance(collector_id, EntityId)
            else EntityId.from_value(collector_id)
        )
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            region_code=region,
            site_code=site,
            vrf_code=vrf,
            collector_id=collector,
            discovery_scope=cls.scope_for(region, site, vrf),
            active=True,
            configured_by=MultisiteValidator.actor(configured_by),
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        region_code: str,
        site_code: str,
        vrf_code: str,
        collector_id: EntityId,
        discovery_scope: str,
        active: bool,
        configured_by: str,
        created_at: datetime,
        updated_at: datetime,
        disabled_at: datetime | None = None,
    ) -> Self:
        region = Code.from_value(region_code, "region code").value
        site = Code.from_value(site_code, "site code").value
        vrf = Code.from_value(vrf_code, "VRF code").value
        expected_scope = cls.scope_for(region, site, vrf)
        if discovery_scope.strip().lower() != expected_scope:
            raise ValidationError("regional discovery route scope is inconsistent")
        normalized_disabled = (
            None if disabled_at is None else MultisiteValidator.aware(disabled_at, "disabled_at")
        )
        if bool(active) == (normalized_disabled is not None):
            raise ValidationError("regional discovery route active state is inconsistent")
        return cls(
            id=id,
            tenant_id=tenant_id,
            region_code=region,
            site_code=site,
            vrf_code=vrf,
            collector_id=collector_id,
            discovery_scope=expected_scope,
            active=bool(active),
            configured_by=MultisiteValidator.actor(configured_by),
            created_at=MultisiteValidator.aware(created_at, "created_at"),
            updated_at=MultisiteValidator.aware(updated_at, "updated_at"),
            disabled_at=normalized_disabled,
        )

    def reassign(
        self,
        collector_id: str | EntityId,
        configured_by: str,
        now: datetime | None = None,
    ) -> Self:
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        collector = (
            collector_id
            if isinstance(collector_id, EntityId)
            else EntityId.from_value(collector_id)
        )
        return replace(
            self,
            collector_id=collector,
            active=True,
            configured_by=MultisiteValidator.actor(configured_by),
            updated_at=timestamp,
            disabled_at=None,
        )

    def disable(self, configured_by: str, now: datetime | None = None) -> Self:
        if not self.active:
            return self
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return replace(
            self,
            active=False,
            configured_by=MultisiteValidator.actor(configured_by),
            updated_at=timestamp,
            disabled_at=timestamp,
        )

    def matches(self, region_code: str, site_code: str, vrf_code: str) -> bool:
        return (
            self.active
            and self.region_code == Code.from_value(region_code, "region code").value
            and self.site_code == Code.from_value(site_code, "site code").value
            and self.vrf_code == Code.from_value(vrf_code, "VRF code").value
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "region_code": self.region_code,
            "site_code": self.site_code,
            "vrf_code": self.vrf_code,
            "collector_id": self.collector_id.value,
            "discovery_scope": self.discovery_scope,
            "active": self.active,
            "configured_by": self.configured_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "disabled_at": self.disabled_at.isoformat() if self.disabled_at else None,
        }

    @staticmethod
    def scope_for(region_code: str, site_code: str, vrf_code: str) -> str:
        region = Code.from_value(region_code, "region code").value.lower()
        site = Code.from_value(site_code, "site code").value.lower()
        vrf = Code.from_value(vrf_code, "VRF code").value.lower()
        return f"region/{region}/site/{site}/vrf/{vrf}"


class DisasterRecoveryReplicationMode(StrEnum):
    ASYNCHRONOUS = "asynchronous"
    SYNCHRONOUS = "synchronous"

    @classmethod
    def from_value(cls, value: str | DisasterRecoveryReplicationMode) -> Self:
        if isinstance(value, cls):
            return value
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "async": cls.ASYNCHRONOUS,
            "asynchronous": cls.ASYNCHRONOUS,
            "sync": cls.SYNCHRONOUS,
            "synchronous": cls.SYNCHRONOUS,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValidationError(
                "DR replication mode must be asynchronous or synchronous"
            ) from exc


class DisasterRecoveryDrillStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class MultisiteDisasterRecoveryPlan:
    id: EntityId
    tenant_id: TenantId
    name: str
    primary_site_code: str
    recovery_site_code: str
    replication_mode: DisasterRecoveryReplicationMode
    rpo_seconds: int
    rto_seconds: int
    max_backup_age_seconds: int
    active: bool
    configured_by: str
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        primary_site_code: str,
        recovery_site_code: str,
        replication_mode: str | DisasterRecoveryReplicationMode,
        rpo_seconds: int,
        rto_seconds: int,
        max_backup_age_seconds: int,
        configured_by: str,
        now: datetime | None = None,
    ) -> Self:
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        normalized_name = " ".join(name.strip().split())
        if not 3 <= len(normalized_name) <= 128:
            raise ValidationError("DR plan name must contain 3 to 128 characters")
        primary = Code.from_value(primary_site_code, "primary site code").value
        recovery = Code.from_value(recovery_site_code, "recovery site code").value
        if primary == recovery:
            raise ValidationError("DR primary and recovery sites must be different")
        normalized_rpo = cls._bounded_seconds(rpo_seconds, "RPO", 1, 86_400)
        normalized_rto = cls._bounded_seconds(rto_seconds, "RTO", 1, 604_800)
        backup_age = cls._bounded_seconds(
            max_backup_age_seconds, "maximum backup age", 60, 2_592_000
        )
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=normalized_name,
            primary_site_code=primary,
            recovery_site_code=recovery,
            replication_mode=DisasterRecoveryReplicationMode.from_value(replication_mode),
            rpo_seconds=normalized_rpo,
            rto_seconds=normalized_rto,
            max_backup_age_seconds=backup_age,
            active=True,
            configured_by=MultisiteValidator.actor(configured_by),
            created_at=timestamp,
            updated_at=timestamp,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        name: str,
        primary_site_code: str,
        recovery_site_code: str,
        replication_mode: str | DisasterRecoveryReplicationMode,
        rpo_seconds: int,
        rto_seconds: int,
        max_backup_age_seconds: int,
        active: bool,
        configured_by: str,
        created_at: datetime,
        updated_at: datetime,
        disabled_at: datetime | None = None,
    ) -> Self:
        restored = cls.create(
            tenant_id,
            name,
            primary_site_code,
            recovery_site_code,
            replication_mode,
            rpo_seconds,
            rto_seconds,
            max_backup_age_seconds,
            configured_by,
            MultisiteValidator.aware(created_at, "created_at"),
        )
        normalized_disabled = (
            None if disabled_at is None else MultisiteValidator.aware(disabled_at, "disabled_at")
        )
        if bool(active) == (normalized_disabled is not None):
            raise ValidationError("DR plan active state is inconsistent")
        return replace(
            restored,
            id=id,
            active=bool(active),
            created_at=MultisiteValidator.aware(created_at, "created_at"),
            updated_at=MultisiteValidator.aware(updated_at, "updated_at"),
            disabled_at=normalized_disabled,
        )

    def revise(
        self,
        *,
        name: str,
        replication_mode: str | DisasterRecoveryReplicationMode,
        rpo_seconds: int,
        rto_seconds: int,
        max_backup_age_seconds: int,
        configured_by: str,
        now: datetime | None = None,
    ) -> Self:
        candidate = self.create(
            self.tenant_id,
            name,
            self.primary_site_code,
            self.recovery_site_code,
            replication_mode,
            rpo_seconds,
            rto_seconds,
            max_backup_age_seconds,
            configured_by,
            now,
        )
        return replace(
            candidate,
            id=self.id,
            created_at=self.created_at,
        )

    def disable(self, configured_by: str, now: datetime | None = None) -> Self:
        if not self.active:
            return self
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return replace(
            self,
            active=False,
            configured_by=MultisiteValidator.actor(configured_by),
            updated_at=timestamp,
            disabled_at=timestamp,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "primary_site_code": self.primary_site_code,
            "recovery_site_code": self.recovery_site_code,
            "replication_mode": self.replication_mode.value,
            "rpo_seconds": self.rpo_seconds,
            "rto_seconds": self.rto_seconds,
            "max_backup_age_seconds": self.max_backup_age_seconds,
            "active": self.active,
            "configured_by": self.configured_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "disabled_at": self.disabled_at.isoformat() if self.disabled_at else None,
        }

    @staticmethod
    def _bounded_seconds(value: int, label: str, minimum: int, maximum: int) -> int:
        normalized = int(value)
        if not minimum <= normalized <= maximum:
            raise ValidationError(f"{label} must be between {minimum} and {maximum} seconds")
        return normalized


@dataclass(frozen=True, slots=True)
class MultisiteDisasterRecoveryDrill:
    id: EntityId
    tenant_id: TenantId
    plan_id: EntityId
    scenario: str
    unavailable_site_code: str
    recovery_site_code: str
    replication_lag_seconds: int
    backup_age_seconds: int
    measured_rto_seconds: int
    restore_verified: bool
    recovery_available: bool
    vip_reachable: bool
    operator_confirmed: bool
    status: DisasterRecoveryDrillStatus
    failure_reasons: tuple[str, ...]
    executed_by: str
    executed_at: datetime

    @classmethod
    def execute_site_loss(
        cls,
        plan: MultisiteDisasterRecoveryPlan,
        *,
        replication_lag_seconds: int,
        backup_age_seconds: int,
        measured_rto_seconds: int,
        restore_verified: bool,
        recovery_available: bool,
        vip_reachable: bool,
        operator_confirmed: bool,
        executed_by: str,
        now: datetime | None = None,
    ) -> Self:
        if not plan.active:
            raise ValidationError("DR drill requires an active plan")
        lag = cls._non_negative(replication_lag_seconds, "replication lag")
        backup_age = cls._non_negative(backup_age_seconds, "backup age")
        measured_rto = cls._non_negative(measured_rto_seconds, "measured RTO")
        failures: list[str] = []
        if not operator_confirmed:
            failures.append("operator-confirmation-missing")
        if not recovery_available:
            failures.append("recovery-site-unavailable")
        if not restore_verified:
            failures.append("restore-not-verified")
        if not vip_reachable:
            failures.append("service-endpoint-unreachable")
        if lag > plan.rpo_seconds:
            failures.append("rpo-exceeded")
        if backup_age > plan.max_backup_age_seconds:
            failures.append("backup-too-old")
        if measured_rto > plan.rto_seconds:
            failures.append("rto-exceeded")
        status = (
            DisasterRecoveryDrillStatus.PASSED
            if not failures
            else DisasterRecoveryDrillStatus.FAILED
        )
        timestamp = datetime.now(UTC) if now is None else MultisiteValidator.aware(now, "now")
        return cls(
            id=EntityId.new(),
            tenant_id=plan.tenant_id,
            plan_id=plan.id,
            scenario="primary-site-loss",
            unavailable_site_code=plan.primary_site_code,
            recovery_site_code=plan.recovery_site_code,
            replication_lag_seconds=lag,
            backup_age_seconds=backup_age,
            measured_rto_seconds=measured_rto,
            restore_verified=bool(restore_verified),
            recovery_available=bool(recovery_available),
            vip_reachable=bool(vip_reachable),
            operator_confirmed=bool(operator_confirmed),
            status=status,
            failure_reasons=tuple(failures),
            executed_by=MultisiteValidator.actor(executed_by),
            executed_at=timestamp,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        plan_id: EntityId,
        scenario: str,
        unavailable_site_code: str,
        recovery_site_code: str,
        replication_lag_seconds: int,
        backup_age_seconds: int,
        measured_rto_seconds: int,
        restore_verified: bool,
        recovery_available: bool,
        vip_reachable: bool,
        operator_confirmed: bool,
        status: str | DisasterRecoveryDrillStatus,
        failure_reasons: tuple[str, ...],
        executed_by: str,
        executed_at: datetime,
    ) -> Self:
        normalized_scenario = scenario.strip().lower()
        if normalized_scenario != "primary-site-loss":
            raise ValidationError("unsupported DR drill scenario")
        try:
            normalized_status = (
                status
                if isinstance(status, DisasterRecoveryDrillStatus)
                else DisasterRecoveryDrillStatus(status)
            )
        except ValueError as exc:
            raise ValidationError("DR drill status must be passed or failed") from exc
        normalized_failures = tuple(
            str(item).strip() for item in failure_reasons if str(item).strip()
        )
        if (normalized_status is DisasterRecoveryDrillStatus.PASSED) == bool(normalized_failures):
            raise ValidationError("DR drill status and failure reasons are inconsistent")
        return cls(
            id=id,
            tenant_id=tenant_id,
            plan_id=plan_id,
            scenario=normalized_scenario,
            unavailable_site_code=Code.from_value(
                unavailable_site_code, "unavailable site code"
            ).value,
            recovery_site_code=Code.from_value(recovery_site_code, "recovery site code").value,
            replication_lag_seconds=cls._non_negative(replication_lag_seconds, "replication lag"),
            backup_age_seconds=cls._non_negative(backup_age_seconds, "backup age"),
            measured_rto_seconds=cls._non_negative(measured_rto_seconds, "measured RTO"),
            restore_verified=bool(restore_verified),
            recovery_available=bool(recovery_available),
            vip_reachable=bool(vip_reachable),
            operator_confirmed=bool(operator_confirmed),
            status=normalized_status,
            failure_reasons=normalized_failures,
            executed_by=MultisiteValidator.actor(executed_by),
            executed_at=MultisiteValidator.aware(executed_at, "executed_at"),
        )

    @property
    def measured_rpo_seconds(self) -> int:
        return self.replication_lag_seconds

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "plan_id": self.plan_id.value,
            "scenario": self.scenario,
            "unavailable_site_code": self.unavailable_site_code,
            "recovery_site_code": self.recovery_site_code,
            "replication_lag_seconds": self.replication_lag_seconds,
            "backup_age_seconds": self.backup_age_seconds,
            "measured_rpo_seconds": self.measured_rpo_seconds,
            "measured_rto_seconds": self.measured_rto_seconds,
            "restore_verified": self.restore_verified,
            "recovery_available": self.recovery_available,
            "vip_reachable": self.vip_reachable,
            "operator_confirmed": self.operator_confirmed,
            "status": self.status.value,
            "failure_reasons": list(self.failure_reasons),
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat(),
        }

    @staticmethod
    def _non_negative(value: int, label: str) -> int:
        normalized = int(value)
        if normalized < 0:
            raise ValidationError(f"{label} must be non-negative")
        return normalized
