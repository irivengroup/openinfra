from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Self, cast

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError


class EnergyScope(StrEnum):
    SITE = "site"
    ROOM = "room"
    RACK = "rack"
    PDU = "pdu"
    ASSET = "asset"
    APPLICATION = "application"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "equipment": cls.ASSET.value,
            "device": cls.ASSET.value,
            "app": cls.APPLICATION.value,
        }
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("energy scope is unsupported") from exc


class MeasurementKind(StrEnum):
    OBSERVED = "observed"
    ESTIMATED = "estimated"

    @classmethod
    def from_value(cls, value: str) -> Self:
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("measurement kind must be observed or estimated") from exc


class CapacityDimension(StrEnum):
    ENERGY = "energy"
    COOLING = "cooling"
    SPACE = "space"
    WEIGHT = "weight"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"power": cls.ENERGY.value, "thermal": cls.COOLING.value}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("capacity dimension is unsupported") from exc


class ConsolidationAction(StrEnum):
    CONSOLIDATE = "consolidate"
    MOVE = "move"
    RETIRE_REVIEW = "retire-review"
    CAPACITY_REVIEW = "capacity-review"


class GreenOpsValidator:
    _QUANTUM = Decimal("0.000001")
    _PERCENT_QUANTUM = Decimal("0.0001")
    _SENSITIVE_KEY = re.compile(
        r"(?:^|[_\-.])(password|passwd|pwd|secret|token|credential|api[_-]?key|private[_-]?key)(?:$|[_\-.])",
        re.IGNORECASE,
    )

    @classmethod
    def text(cls, value: str, label: str, maximum: int = 512) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain 1 to {maximum} characters")
        return normalized

    @classmethod
    def optional_text(cls, value: str | None, label: str, maximum: int = 512) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.text(value, label, maximum)

    @classmethod
    def token(cls, value: str, label: str, maximum: int = 128) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(rf"[a-z0-9][a-z0-9_.:@/-]{{0,{maximum - 1}}}", normalized):
            raise ValidationError(f"{label} must use 1 to {maximum} safe characters")
        return normalized

    @classmethod
    def idempotency_key(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}", normalized):
            raise ValidationError("greenops idempotency key must use 8 to 192 safe characters")
        return normalized

    @classmethod
    def decimal(
        cls, value: Decimal | str | int | float, label: str, *, positive: bool = False
    ) -> Decimal:
        try:
            normalized = Decimal(str(value)).quantize(cls._QUANTUM, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{label} must be a finite decimal") from exc
        if not normalized.is_finite() or normalized < 0 or (positive and normalized <= 0):
            qualifier = "strictly positive" if positive else "non-negative"
            raise ValidationError(f"{label} must be {qualifier} and finite")
        if normalized > Decimal("999999999999999999.999999"):
            raise ValidationError(f"{label} exceeds the supported range")
        return normalized

    @classmethod
    def percentage(cls, value: Decimal | str | int | float, label: str) -> Decimal:
        normalized = cls.decimal(value, label)
        if normalized > Decimal("100"):
            raise ValidationError(f"{label} must be between 0 and 100")
        return normalized.quantize(cls._PERCENT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def aware_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def time_range(cls, start: datetime, end: datetime) -> tuple[datetime, datetime]:
        normalized_start = cls.aware_datetime(start, "period_start")
        normalized_end = cls.aware_datetime(end, "period_end")
        if normalized_end <= normalized_start:
            raise ValidationError("measurement period_end must be after period_start")
        if (normalized_end - normalized_start).days > 3660:
            raise ValidationError("measurement period cannot exceed ten years")
        return normalized_start, normalized_end

    @staticmethod
    def date_range(start: date, end: date) -> tuple[date, date]:
        if end < start:
            raise ValidationError("period_end must not precede period_start")
        if (end - start).days > 3660:
            raise ValidationError("period cannot exceed ten years")
        return start, end

    @classmethod
    def json_object(cls, value: dict[str, Any], label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        normalized = cast(dict[str, Any], cls._sanitize(value, label, "$"))
        try:
            encoded = json.dumps(
                normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{label} must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > 131_072:
            raise ValidationError(f"{label} exceeds 128 KiB")
        return normalized

    @classmethod
    def _sanitize(cls, value: Any, label: str, path: str) -> Any:
        if isinstance(value, dict):
            result: dict[str, Any] = {}
            for raw_key, item in value.items():
                key = str(raw_key)
                if cls._SENSITIVE_KEY.search(key):
                    raise ValidationError(f"{label} contains a sensitive key at {path}.{key}")
                result[key] = cls._sanitize(item, label, f"{path}.{key}")
            return result
        if isinstance(value, (list, tuple)):
            return [
                cls._sanitize(item, label, f"{path}[{index}]") for index, item in enumerate(value)
            ]
        return value

    @staticmethod
    def digest(payload: object) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class MeasurementSource:
    id: EntityId
    tenant_id: TenantId
    code: str
    name: str
    source_type: str
    owner: str
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        name: str,
        source_type: str,
        owner: str,
        active: bool = True,
    ) -> Self:
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(code, "source code", 64),
            GreenOpsValidator.text(name, "source name", 255),
            GreenOpsValidator.token(source_type, "source type", 64),
            GreenOpsValidator.text(owner, "source owner", 255),
            bool(active),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        code: str,
        name: str,
        source_type: str,
        owner: str,
        active: bool,
        created_at: datetime,
    ) -> Self:
        created = GreenOpsValidator.aware_datetime(created_at, "created_at")
        return cls(
            id,
            tenant_id,
            GreenOpsValidator.token(code, "source code", 64),
            GreenOpsValidator.text(name, "source name", 255),
            GreenOpsValidator.token(source_type, "source type", 64),
            GreenOpsValidator.text(owner, "source owner", 255),
            bool(active),
            created,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "code": self.code,
            "name": self.name,
            "source_type": self.source_type,
            "owner": self.owner,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CarbonFactor:
    id: EntityId
    tenant_id: TenantId
    code: str
    region: str
    grams_co2e_per_kwh: Decimal
    source_name: str
    source_uri: str | None
    period_start: date
    period_end: date
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        region: str,
        grams_co2e_per_kwh: Decimal | str,
        source_name: str,
        period_start: date,
        period_end: date,
        source_uri: str | None = None,
    ) -> Self:
        start, end = GreenOpsValidator.date_range(period_start, period_end)
        uri = GreenOpsValidator.optional_text(source_uri, "carbon factor source URI", 2048)
        if uri is not None and not re.fullmatch(r"https://[^\s]+", uri):
            raise ValidationError("carbon factor source URI must use HTTPS")
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(code, "carbon factor code", 64),
            GreenOpsValidator.token(region, "carbon factor region", 64),
            GreenOpsValidator.decimal(grams_co2e_per_kwh, "grams CO2e per kWh", positive=True),
            GreenOpsValidator.text(source_name, "carbon factor source", 255),
            uri,
            start,
            end,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        code: str,
        region: str,
        grams_co2e_per_kwh: Decimal | str,
        source_name: str,
        source_uri: str | None,
        period_start: date,
        period_end: date,
        created_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            code,
            region,
            grams_co2e_per_kwh,
            source_name,
            period_start,
            period_end,
            source_uri,
        )
        return cls(
            id,
            tenant_id,
            item.code,
            item.region,
            item.grams_co2e_per_kwh,
            item.source_name,
            item.source_uri,
            item.period_start,
            item.period_end,
            GreenOpsValidator.aware_datetime(created_at, "created_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "code": self.code,
            "region": self.region,
            "grams_co2e_per_kwh": str(self.grams_co2e_per_kwh),
            "source_name": self.source_name,
            "source_uri": self.source_uri,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class GreenOpsPolicy:
    id: EntityId
    tenant_id: TenantId
    site_code: str
    default_pue: Decimal
    energy_cost_per_kwh: Decimal
    currency: str
    carbon_factor_code: str
    underutilized_percent: Decimal
    warning_capacity_percent: Decimal
    critical_capacity_percent: Decimal
    minimum_samples: int
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        default_pue: Decimal | str,
        energy_cost_per_kwh: Decimal | str,
        currency: str,
        carbon_factor_code: str,
        underutilized_percent: Decimal | str = "20",
        warning_capacity_percent: Decimal | str = "80",
        critical_capacity_percent: Decimal | str = "90",
        minimum_samples: int = 3,
    ) -> Self:
        pue = GreenOpsValidator.decimal(default_pue, "default PUE", positive=True)
        if pue < Decimal("1") or pue > Decimal("5"):
            raise ValidationError("default PUE must be between 1 and 5")
        warning = GreenOpsValidator.percentage(warning_capacity_percent, "warning capacity percent")
        critical = GreenOpsValidator.percentage(
            critical_capacity_percent, "critical capacity percent"
        )
        if warning >= critical:
            raise ValidationError(
                "warning capacity threshold must be lower than critical threshold"
            )
        normalized_currency = currency.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized_currency):
            raise ValidationError("currency must be a three-letter ISO-4217 code")
        samples = int(minimum_samples)
        if not 2 <= samples <= 120:
            raise ValidationError("minimum_samples must be between 2 and 120")
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(site_code, "site code", 64),
            pue,
            GreenOpsValidator.decimal(energy_cost_per_kwh, "energy cost per kWh"),
            normalized_currency,
            GreenOpsValidator.token(carbon_factor_code, "carbon factor code", 64),
            GreenOpsValidator.percentage(underutilized_percent, "underutilized percent"),
            warning,
            critical,
            samples,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        site_code: str,
        default_pue: Decimal | str,
        energy_cost_per_kwh: Decimal | str,
        currency: str,
        carbon_factor_code: str,
        underutilized_percent: Decimal | str,
        warning_capacity_percent: Decimal | str,
        critical_capacity_percent: Decimal | str,
        minimum_samples: int,
        updated_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            site_code,
            default_pue,
            energy_cost_per_kwh,
            currency,
            carbon_factor_code,
            underutilized_percent,
            warning_capacity_percent,
            critical_capacity_percent,
            minimum_samples,
        )
        return cls(
            id,
            tenant_id,
            item.site_code,
            item.default_pue,
            item.energy_cost_per_kwh,
            item.currency,
            item.carbon_factor_code,
            item.underutilized_percent,
            item.warning_capacity_percent,
            item.critical_capacity_percent,
            item.minimum_samples,
            GreenOpsValidator.aware_datetime(updated_at, "updated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site_code": self.site_code,
            "default_pue": str(self.default_pue),
            "energy_cost_per_kwh": str(self.energy_cost_per_kwh),
            "currency": self.currency,
            "carbon_factor_code": self.carbon_factor_code,
            "underutilized_percent": str(self.underutilized_percent),
            "warning_capacity_percent": str(self.warning_capacity_percent),
            "critical_capacity_percent": str(self.critical_capacity_percent),
            "minimum_samples": self.minimum_samples,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class EnergyMeasurement:
    id: EntityId
    tenant_id: TenantId
    idempotency_key: str
    source_code: str
    kind: MeasurementKind
    scope: EnergyScope
    scope_key: str
    site_code: str
    application_key: str | None
    period_start: datetime
    period_end: datetime
    energy_kwh: Decimal
    it_energy_kwh: Decimal | None
    facility_energy_kwh: Decimal | None
    utilization_percent: Decimal | None
    energy_capacity_percent: Decimal | None
    cooling_capacity_percent: Decimal | None
    space_capacity_percent: Decimal | None
    weight_capacity_percent: Decimal | None
    metadata: dict[str, Any]
    recorded_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        idempotency_key: str,
        source_code: str,
        kind: str,
        scope: str,
        scope_key: str,
        site_code: str,
        period_start: datetime,
        period_end: datetime,
        energy_kwh: Decimal | str,
        *,
        application_key: str | None = None,
        it_energy_kwh: Decimal | str | None = None,
        facility_energy_kwh: Decimal | str | None = None,
        utilization_percent: Decimal | str | None = None,
        energy_capacity_percent: Decimal | str | None = None,
        cooling_capacity_percent: Decimal | str | None = None,
        space_capacity_percent: Decimal | str | None = None,
        weight_capacity_percent: Decimal | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Self:
        start, end = GreenOpsValidator.time_range(period_start, period_end)
        energy = GreenOpsValidator.decimal(energy_kwh, "energy_kwh", positive=True)
        it_energy = (
            None
            if it_energy_kwh is None
            else GreenOpsValidator.decimal(it_energy_kwh, "it_energy_kwh", positive=True)
        )
        facility_energy = (
            None
            if facility_energy_kwh is None
            else GreenOpsValidator.decimal(
                facility_energy_kwh, "facility_energy_kwh", positive=True
            )
        )
        if it_energy is not None and facility_energy is not None and facility_energy < it_energy:
            raise ValidationError("facility energy cannot be lower than IT energy")

        def percent(value: Decimal | str | None, label: str) -> Decimal | None:
            return None if value is None else GreenOpsValidator.percentage(value, label)

        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.idempotency_key(idempotency_key),
            GreenOpsValidator.token(source_code, "source code", 64),
            MeasurementKind.from_value(kind),
            EnergyScope.from_value(scope),
            GreenOpsValidator.token(scope_key, "scope key"),
            GreenOpsValidator.token(site_code, "site code", 64),
            None
            if application_key is None
            else GreenOpsValidator.token(application_key, "application key"),
            start,
            end,
            energy,
            it_energy,
            facility_energy,
            percent(utilization_percent, "utilization percent"),
            percent(energy_capacity_percent, "energy capacity percent"),
            percent(cooling_capacity_percent, "cooling capacity percent"),
            percent(space_capacity_percent, "space capacity percent"),
            percent(weight_capacity_percent, "weight capacity percent"),
            GreenOpsValidator.json_object(metadata or {}, "measurement metadata"),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        idempotency_key: str,
        source_code: str,
        kind: str,
        scope: str,
        scope_key: str,
        site_code: str,
        application_key: str | None,
        period_start: datetime,
        period_end: datetime,
        energy_kwh: Decimal | str,
        it_energy_kwh: Decimal | str | None,
        facility_energy_kwh: Decimal | str | None,
        utilization_percent: Decimal | str | None,
        energy_capacity_percent: Decimal | str | None,
        cooling_capacity_percent: Decimal | str | None,
        space_capacity_percent: Decimal | str | None,
        weight_capacity_percent: Decimal | str | None,
        metadata: dict[str, Any],
        recorded_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            idempotency_key,
            source_code,
            kind,
            scope,
            scope_key,
            site_code,
            period_start,
            period_end,
            energy_kwh,
            application_key=application_key,
            it_energy_kwh=it_energy_kwh,
            facility_energy_kwh=facility_energy_kwh,
            utilization_percent=utilization_percent,
            energy_capacity_percent=energy_capacity_percent,
            cooling_capacity_percent=cooling_capacity_percent,
            space_capacity_percent=space_capacity_percent,
            weight_capacity_percent=weight_capacity_percent,
            metadata=metadata,
        )
        return cls(
            id,
            tenant_id,
            item.idempotency_key,
            item.source_code,
            item.kind,
            item.scope,
            item.scope_key,
            item.site_code,
            item.application_key,
            item.period_start,
            item.period_end,
            item.energy_kwh,
            item.it_energy_kwh,
            item.facility_energy_kwh,
            item.utilization_percent,
            item.energy_capacity_percent,
            item.cooling_capacity_percent,
            item.space_capacity_percent,
            item.weight_capacity_percent,
            item.metadata,
            GreenOpsValidator.aware_datetime(recorded_at, "recorded_at"),
        )

    def input_digest(self) -> str:
        return GreenOpsValidator.digest(self.as_dict())

    def capacity_values(self) -> dict[CapacityDimension, Decimal]:
        pairs = {
            CapacityDimension.ENERGY: self.energy_capacity_percent,
            CapacityDimension.COOLING: self.cooling_capacity_percent,
            CapacityDimension.SPACE: self.space_capacity_percent,
            CapacityDimension.WEIGHT: self.weight_capacity_percent,
        }
        return {dimension: value for dimension, value in pairs.items() if value is not None}

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "idempotency_key": self.idempotency_key,
            "source_code": self.source_code,
            "kind": self.kind.value,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "site_code": self.site_code,
            "application_key": self.application_key,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "energy_kwh": str(self.energy_kwh),
            "it_energy_kwh": None if self.it_energy_kwh is None else str(self.it_energy_kwh),
            "facility_energy_kwh": None
            if self.facility_energy_kwh is None
            else str(self.facility_energy_kwh),
            "utilization_percent": None
            if self.utilization_percent is None
            else str(self.utilization_percent),
            "energy_capacity_percent": None
            if self.energy_capacity_percent is None
            else str(self.energy_capacity_percent),
            "cooling_capacity_percent": None
            if self.cooling_capacity_percent is None
            else str(self.cooling_capacity_percent),
            "space_capacity_percent": None
            if self.space_capacity_percent is None
            else str(self.space_capacity_percent),
            "weight_capacity_percent": None
            if self.weight_capacity_percent is None
            else str(self.weight_capacity_percent),
            "metadata": self.metadata,
            "recorded_at": self.recorded_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CarbonEstimate:
    energy_kwh: Decimal
    kilograms_co2e: Decimal
    factor_code: str
    factor_grams_co2e_per_kwh: Decimal
    factor_source: str
    factor_source_uri: str | None
    factor_period_start: date
    factor_period_end: date
    scope: str

    def as_dict(self) -> dict[str, object]:
        return {
            "energy_kwh": str(self.energy_kwh),
            "kilograms_co2e": str(self.kilograms_co2e),
            "factor_code": self.factor_code,
            "factor_grams_co2e_per_kwh": str(self.factor_grams_co2e_per_kwh),
            "factor_source": self.factor_source,
            "factor_source_uri": self.factor_source_uri,
            "factor_period_start": self.factor_period_start.isoformat(),
            "factor_period_end": self.factor_period_end.isoformat(),
            "scope": self.scope,
        }


@dataclass(frozen=True, slots=True)
class EnergyAnomaly:
    id: EntityId
    tenant_id: TenantId
    site_code: str
    scope: EnergyScope
    scope_key: str
    kind: str
    severity: Severity
    observed_value: Decimal
    baseline_value: Decimal
    description: str
    detected_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        scope: EnergyScope,
        scope_key: str,
        kind: str,
        severity: Severity,
        observed_value: Decimal,
        baseline_value: Decimal,
        description: str,
    ) -> Self:
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(site_code, "site code", 64),
            scope,
            GreenOpsValidator.token(scope_key, "scope key"),
            GreenOpsValidator.token(kind, "anomaly kind", 64),
            severity,
            GreenOpsValidator.decimal(observed_value, "observed value"),
            GreenOpsValidator.decimal(baseline_value, "baseline value"),
            GreenOpsValidator.text(description, "anomaly description", 1024),
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        site_code: str,
        scope: str,
        scope_key: str,
        kind: str,
        severity: str,
        observed_value: Decimal | str,
        baseline_value: Decimal | str,
        description: str,
        detected_at: datetime,
    ) -> Self:
        return cls(
            id,
            tenant_id,
            GreenOpsValidator.token(site_code, "site code", 64),
            EnergyScope.from_value(scope),
            GreenOpsValidator.token(scope_key, "scope key"),
            GreenOpsValidator.token(kind, "anomaly kind", 64),
            Severity(severity),
            GreenOpsValidator.decimal(observed_value, "observed value"),
            GreenOpsValidator.decimal(baseline_value, "baseline value"),
            GreenOpsValidator.text(description, "anomaly description", 1024),
            GreenOpsValidator.aware_datetime(detected_at, "detected_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site_code": self.site_code,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "kind": self.kind,
            "severity": self.severity.value,
            "observed_value": str(self.observed_value),
            "baseline_value": str(self.baseline_value),
            "description": self.description,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CapacityForecast:
    id: EntityId
    tenant_id: TenantId
    site_code: str
    scope: EnergyScope
    scope_key: str
    dimension: CapacityDimension
    current_percent: Decimal
    daily_growth_percent: Decimal
    projected_saturation_at: date | None
    confidence_percent: Decimal
    sample_count: int
    source_digest: str
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        scope: EnergyScope,
        scope_key: str,
        dimension: CapacityDimension,
        current_percent: Decimal,
        daily_growth_percent: Decimal,
        projected_saturation_at: date | None,
        confidence_percent: Decimal,
        sample_count: int,
        source_digest: str,
    ) -> Self:
        digest = source_digest.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValidationError("forecast source digest must be SHA-256")
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(site_code, "site code", 64),
            scope,
            GreenOpsValidator.token(scope_key, "scope key"),
            dimension,
            GreenOpsValidator.percentage(current_percent, "current capacity percent"),
            GreenOpsValidator.decimal(daily_growth_percent, "daily growth percent"),
            projected_saturation_at,
            GreenOpsValidator.percentage(confidence_percent, "confidence percent"),
            int(sample_count),
            digest,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        site_code: str,
        scope: str,
        scope_key: str,
        dimension: str,
        current_percent: Decimal | str,
        daily_growth_percent: Decimal | str,
        projected_saturation_at: date | None,
        confidence_percent: Decimal | str,
        sample_count: int,
        source_digest: str,
        generated_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            site_code,
            EnergyScope.from_value(scope),
            scope_key,
            CapacityDimension.from_value(dimension),
            GreenOpsValidator.percentage(current_percent, "current capacity percent"),
            GreenOpsValidator.decimal(daily_growth_percent, "daily growth percent"),
            projected_saturation_at,
            GreenOpsValidator.percentage(confidence_percent, "confidence percent"),
            sample_count,
            source_digest,
        )
        return cls(
            id,
            tenant_id,
            item.site_code,
            item.scope,
            item.scope_key,
            item.dimension,
            item.current_percent,
            item.daily_growth_percent,
            item.projected_saturation_at,
            item.confidence_percent,
            item.sample_count,
            item.source_digest,
            GreenOpsValidator.aware_datetime(generated_at, "generated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site_code": self.site_code,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "dimension": self.dimension.value,
            "current_percent": str(self.current_percent),
            "daily_growth_percent": str(self.daily_growth_percent),
            "projected_saturation_at": None
            if self.projected_saturation_at is None
            else self.projected_saturation_at.isoformat(),
            "confidence_percent": str(self.confidence_percent),
            "sample_count": self.sample_count,
            "source_digest": self.source_digest,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ConsolidationCandidate:
    id: EntityId
    tenant_id: TenantId
    site_code: str
    scope: EnergyScope
    scope_key: str
    action: ConsolidationAction
    rationale: str
    estimated_annual_energy_saving_kwh: Decimal
    estimated_annual_carbon_saving_kg: Decimal
    risk_level: Severity
    requires_human_approval: bool
    source_digest: str
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        scope: EnergyScope,
        scope_key: str,
        action: ConsolidationAction,
        rationale: str,
        energy_saving: Decimal,
        carbon_saving: Decimal,
        risk_level: Severity,
        source_digest: str,
    ) -> Self:
        digest = source_digest.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValidationError("candidate source digest must be SHA-256")
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(site_code, "site code", 64),
            scope,
            GreenOpsValidator.token(scope_key, "scope key"),
            action,
            GreenOpsValidator.text(rationale, "candidate rationale", 2048),
            GreenOpsValidator.decimal(energy_saving, "energy saving"),
            GreenOpsValidator.decimal(carbon_saving, "carbon saving"),
            risk_level,
            True,
            digest,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        site_code: str,
        scope: str,
        scope_key: str,
        action: str,
        rationale: str,
        estimated_annual_energy_saving_kwh: Decimal | str,
        estimated_annual_carbon_saving_kg: Decimal | str,
        risk_level: str,
        requires_human_approval: bool,
        source_digest: str,
        generated_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            site_code,
            EnergyScope.from_value(scope),
            scope_key,
            ConsolidationAction(action),
            rationale,
            GreenOpsValidator.decimal(estimated_annual_energy_saving_kwh, "energy saving"),
            GreenOpsValidator.decimal(estimated_annual_carbon_saving_kg, "carbon saving"),
            Severity(risk_level),
            source_digest,
        )
        if not requires_human_approval:
            raise ValidationError("GreenOps candidates must require human approval")
        return cls(
            id,
            tenant_id,
            item.site_code,
            item.scope,
            item.scope_key,
            item.action,
            item.rationale,
            item.estimated_annual_energy_saving_kwh,
            item.estimated_annual_carbon_saving_kg,
            item.risk_level,
            True,
            item.source_digest,
            GreenOpsValidator.aware_datetime(generated_at, "generated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site_code": self.site_code,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "action": self.action.value,
            "rationale": self.rationale,
            "estimated_annual_energy_saving_kwh": str(self.estimated_annual_energy_saving_kwh),
            "estimated_annual_carbon_saving_kg": str(self.estimated_annual_carbon_saving_kg),
            "risk_level": self.risk_level.value,
            "requires_human_approval": self.requires_human_approval,
            "source_digest": self.source_digest,
            "generated_at": self.generated_at.isoformat(),
            "production_mutation": False,
        }


@dataclass(frozen=True, slots=True)
class GreenScore:
    id: EntityId
    tenant_id: TenantId
    scope: str
    score: Decimal
    pue_component: Decimal
    capacity_component: Decimal
    data_quality_component: Decimal
    period_start: date
    period_end: date
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        scope: str,
        score: Decimal,
        pue_component: Decimal,
        capacity_component: Decimal,
        data_quality_component: Decimal,
        period_start: date,
        period_end: date,
    ) -> Self:
        start, end = GreenOpsValidator.date_range(period_start, period_end)
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(scope, "score scope"),
            GreenOpsValidator.percentage(score, "green score"),
            GreenOpsValidator.percentage(pue_component, "PUE score"),
            GreenOpsValidator.percentage(capacity_component, "capacity score"),
            GreenOpsValidator.percentage(data_quality_component, "data quality score"),
            start,
            end,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        scope: str,
        score: Decimal | str,
        pue_component: Decimal | str,
        capacity_component: Decimal | str,
        data_quality_component: Decimal | str,
        period_start: date,
        period_end: date,
        generated_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            scope,
            GreenOpsValidator.percentage(score, "green score"),
            GreenOpsValidator.percentage(pue_component, "PUE score"),
            GreenOpsValidator.percentage(capacity_component, "capacity score"),
            GreenOpsValidator.percentage(data_quality_component, "data quality score"),
            period_start,
            period_end,
        )
        return cls(
            id,
            tenant_id,
            item.scope,
            item.score,
            item.pue_component,
            item.capacity_component,
            item.data_quality_component,
            item.period_start,
            item.period_end,
            GreenOpsValidator.aware_datetime(generated_at, "generated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "scope": self.scope,
            "score": str(self.score),
            "pue_component": str(self.pue_component),
            "capacity_component": str(self.capacity_component),
            "data_quality_component": str(self.data_quality_component),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SustainabilityReport:
    id: EntityId
    tenant_id: TenantId
    site_code: str
    scope: str
    period_start: date
    period_end: date
    total_energy_kwh: Decimal
    it_energy_kwh: Decimal
    facility_energy_kwh: Decimal
    pue: Decimal
    pue_source: str
    energy_cost: Decimal
    currency: str
    carbon_estimate: CarbonEstimate
    green_score: GreenScore
    measurement_count: int
    observed_measurement_count: int
    estimated_measurement_count: int
    anomaly_ids: tuple[str, ...]
    forecast_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    input_digest: str
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        site_code: str,
        scope: str,
        period_start: date,
        period_end: date,
        total_energy_kwh: Decimal,
        it_energy_kwh: Decimal,
        facility_energy_kwh: Decimal,
        pue: Decimal,
        pue_source: str,
        energy_cost: Decimal,
        currency: str,
        carbon_estimate: CarbonEstimate,
        green_score: GreenScore,
        measurement_count: int,
        observed_measurement_count: int,
        estimated_measurement_count: int,
        anomaly_ids: tuple[str, ...],
        forecast_ids: tuple[str, ...],
        candidate_ids: tuple[str, ...],
        assumptions: tuple[str, ...],
        input_digest: str,
    ) -> Self:
        start, end = GreenOpsValidator.date_range(period_start, period_end)
        digest = input_digest.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValidationError("report input digest must be SHA-256")
        normalized_currency = currency.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized_currency):
            raise ValidationError("currency must be a three-letter ISO-4217 code")
        return cls(
            EntityId.new(),
            tenant_id,
            GreenOpsValidator.token(site_code, "site code", 64),
            GreenOpsValidator.token(scope, "report scope"),
            start,
            end,
            GreenOpsValidator.decimal(total_energy_kwh, "total energy"),
            GreenOpsValidator.decimal(it_energy_kwh, "IT energy"),
            GreenOpsValidator.decimal(facility_energy_kwh, "facility energy"),
            GreenOpsValidator.decimal(pue, "PUE", positive=True),
            GreenOpsValidator.token(pue_source, "PUE source", 64),
            GreenOpsValidator.decimal(energy_cost, "energy cost"),
            normalized_currency,
            carbon_estimate,
            green_score,
            int(measurement_count),
            int(observed_measurement_count),
            int(estimated_measurement_count),
            anomaly_ids,
            forecast_ids,
            candidate_ids,
            tuple(GreenOpsValidator.text(item, "report assumption", 1024) for item in assumptions),
            digest,
            datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        site_code: str,
        scope: str,
        period_start: date,
        period_end: date,
        total_energy_kwh: Decimal | str,
        it_energy_kwh: Decimal | str,
        facility_energy_kwh: Decimal | str,
        pue: Decimal | str,
        pue_source: str,
        energy_cost: Decimal | str,
        currency: str,
        carbon_estimate: CarbonEstimate,
        green_score: GreenScore,
        measurement_count: int,
        observed_measurement_count: int,
        estimated_measurement_count: int,
        anomaly_ids: tuple[str, ...],
        forecast_ids: tuple[str, ...],
        candidate_ids: tuple[str, ...],
        assumptions: tuple[str, ...],
        input_digest: str,
        generated_at: datetime,
    ) -> Self:
        item = cls.create(
            tenant_id,
            site_code,
            scope,
            period_start,
            period_end,
            GreenOpsValidator.decimal(total_energy_kwh, "total energy"),
            GreenOpsValidator.decimal(it_energy_kwh, "IT energy"),
            GreenOpsValidator.decimal(facility_energy_kwh, "facility energy"),
            GreenOpsValidator.decimal(pue, "PUE", positive=True),
            pue_source,
            GreenOpsValidator.decimal(energy_cost, "energy cost"),
            currency,
            carbon_estimate,
            green_score,
            measurement_count,
            observed_measurement_count,
            estimated_measurement_count,
            anomaly_ids,
            forecast_ids,
            candidate_ids,
            assumptions,
            input_digest,
        )
        return cls(
            id,
            tenant_id,
            item.site_code,
            item.scope,
            item.period_start,
            item.period_end,
            item.total_energy_kwh,
            item.it_energy_kwh,
            item.facility_energy_kwh,
            item.pue,
            item.pue_source,
            item.energy_cost,
            item.currency,
            item.carbon_estimate,
            item.green_score,
            item.measurement_count,
            item.observed_measurement_count,
            item.estimated_measurement_count,
            item.anomaly_ids,
            item.forecast_ids,
            item.candidate_ids,
            item.assumptions,
            item.input_digest,
            GreenOpsValidator.aware_datetime(generated_at, "generated_at"),
        )

    def reproducibility_key(self) -> str:
        return GreenOpsValidator.digest(
            {
                "tenant_id": self.tenant_id.value,
                "site_code": self.site_code,
                "scope": self.scope,
                "period_start": self.period_start.isoformat(),
                "period_end": self.period_end.isoformat(),
                "input_digest": self.input_digest,
            }
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "site_code": self.site_code,
            "scope": self.scope,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_energy_kwh": str(self.total_energy_kwh),
            "it_energy_kwh": str(self.it_energy_kwh),
            "facility_energy_kwh": str(self.facility_energy_kwh),
            "pue": str(self.pue),
            "pue_source": self.pue_source,
            "energy_cost": str(self.energy_cost),
            "currency": self.currency,
            "carbon_estimate": self.carbon_estimate.as_dict(),
            "green_score": self.green_score.as_dict(),
            "measurement_count": self.measurement_count,
            "observed_measurement_count": self.observed_measurement_count,
            "estimated_measurement_count": self.estimated_measurement_count,
            "anomaly_ids": list(self.anomaly_ids),
            "forecast_ids": list(self.forecast_ids),
            "candidate_ids": list(self.candidate_ids),
            "assumptions": list(self.assumptions),
            "input_digest": self.input_digest,
            "reproducibility_key": self.reproducibility_key(),
            "generated_at": self.generated_at.isoformat(),
            "production_mutation": False,
            "native_itsm_ticket_created": False,
        }
