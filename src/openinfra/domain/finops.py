from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Self, cast

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError


class CostCategory(StrEnum):
    CLOUD = "cloud"
    SAAS = "saas"
    DATACENTER = "datacenter"
    ENERGY = "energy"
    LICENSE = "license"
    SUPPORT = "support"
    CONTRACT = "contract"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "dc": cls.DATACENTER.value,
            "licence": cls.LICENSE.value,
            "licenses": cls.LICENSE.value,
            "licences": cls.LICENSE.value,
        }
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("cost category is unsupported") from exc


class AllocationDimension(StrEnum):
    ASSET = "asset"
    APPLICATION = "application"
    BUSINESS_SERVICE = "business-service"
    TENANT = "tenant"
    OWNER = "owner"
    TAG = "tag"
    COST_CENTER = "cost-center"
    ENVIRONMENT = "environment"
    DEPENDENCY = "dependency"
    UNALLOCATED = "unallocated"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "service": cls.BUSINESS_SERVICE.value,
            "business_service": cls.BUSINESS_SERVICE.value,
            "cost_center": cls.COST_CENTER.value,
        }
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("allocation dimension is unsupported") from exc


class CostQualityStatus(StrEnum):
    ALLOCATED = "allocated"
    PARTIAL = "partial"
    UNALLOCATED = "unallocated"


class FinOpsImportJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FinancialPeriodStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class FinOpsReportKind(StrEnum):
    SHOWBACK = "showback"
    CHARGEBACK = "chargeback"

    @classmethod
    def from_value(cls, value: str) -> Self:
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("finops report kind must be showback or chargeback") from exc


class FinOpsValueValidator:
    _MONEY_QUANTUM = Decimal("0.000001")
    _PERCENT_QUANTUM = Decimal("0.0001")
    _MAX_RECORD_JSON_BYTES = 131_072
    _MAX_JOB_JSON_BYTES = 10_485_760
    _SENSITIVE_KEY_PATTERN = re.compile(
        r"(?:^|[_\-.])(password|passwd|pwd|secret|token|credential|api[_-]?key|private[_-]?key)(?:$|[_\-.])",
        re.IGNORECASE,
    )
    _ALLOWED_SELECTOR_KEYS = frozenset(
        {
            "asset_key",
            "application_key",
            "service_key",
            "owner",
            "cost_center",
            "environment",
            "dependency_key",
            "tenant",
        }
    )

    @classmethod
    def text(cls, value: str, label: str, minimum: int = 1, maximum: int = 512) -> str:
        normalized = " ".join(value.strip().split())
        if not minimum <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain {minimum} to {maximum} characters")
        return normalized

    @classmethod
    def optional_text(cls, value: str | None, label: str, maximum: int = 512) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.text(value, label, 1, maximum)

    @classmethod
    def token(cls, value: str, label: str, maximum: int = 128) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(rf"[a-z0-9][a-z0-9_.:@/-]{{0,{maximum - 1}}}", normalized):
            raise ValidationError(f"{label} must use 1 to {maximum} safe characters")
        return normalized

    @classmethod
    def optional_token(cls, value: str | None, label: str, maximum: int = 128) -> str | None:
        if value is None or not value.strip():
            return None
        return cls.token(value, label, maximum)

    @classmethod
    def idempotency_key(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{7,191}", normalized):
            raise ValidationError("finops idempotency key must use 8 to 192 safe characters")
        return normalized

    @classmethod
    def currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", normalized):
            raise ValidationError("currency must be a three-letter ISO-4217 code")
        return normalized

    @classmethod
    def amount(cls, value: Decimal | str | int | float, label: str = "amount") -> Decimal:
        try:
            normalized = Decimal(str(value)).quantize(cls._MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{label} must be a finite decimal") from exc
        if not normalized.is_finite() or normalized < 0:
            raise ValidationError(f"{label} cannot be negative or non-finite")
        if normalized > Decimal("999999999999999999.999999"):
            raise ValidationError(f"{label} exceeds the supported financial range")
        return normalized

    @classmethod
    def positive_amount(cls, value: Decimal | str | int | float, label: str = "amount") -> Decimal:
        normalized = cls.amount(value, label)
        if normalized <= 0:
            raise ValidationError(f"{label} must be strictly positive")
        return normalized

    @classmethod
    def percentage(
        cls,
        value: Decimal | str | int | float,
        label: str = "percentage",
        allow_zero: bool = False,
    ) -> Decimal:
        try:
            normalized = Decimal(str(value)).quantize(cls._PERCENT_QUANTUM, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{label} must be a finite decimal") from exc
        lower = Decimal("0") if allow_zero else Decimal("0.0001")
        if not normalized.is_finite() or normalized < lower or normalized > Decimal("100"):
            raise ValidationError(f"{label} must be between {lower} and 100")
        return normalized

    @staticmethod
    def date_range(start: date, end: date, label: str = "financial period") -> tuple[date, date]:
        if end < start:
            raise ValidationError(f"{label} end date must not precede start date")
        if (end - start).days > 3660:
            raise ValidationError(f"{label} cannot exceed ten years")
        return start, end

    @classmethod
    def selector_key(cls, value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        if normalized.startswith("tag:"):
            tag_name = normalized[4:]
            if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,62}", tag_name):
                raise ValidationError("tag selector must contain a safe tag name")
            return normalized
        canonical = normalized.replace("-", "_")
        if canonical not in cls._ALLOWED_SELECTOR_KEYS:
            raise ValidationError("allocation selector key is unsupported")
        return canonical

    @classmethod
    def json_object(cls, value: dict[str, Any], label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        normalized = cast(dict[str, Any], cls._reject_sensitive_keys(value, label))
        try:
            encoded = json.dumps(
                normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{label} must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > cls._MAX_RECORD_JSON_BYTES:
            raise ValidationError(f"{label} exceeds 128 KiB")
        return normalized

    @classmethod
    def _reject_sensitive_keys(cls, value: Any, label: str, path: str = "$") -> Any:
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for raw_key, item in value.items():
                key = str(raw_key)
                if cls._SENSITIVE_KEY_PATTERN.search(key):
                    raise ValidationError(f"{label} contains a sensitive key at {path}.{key}")
                normalized[key] = cls._reject_sensitive_keys(item, label, f"{path}.{key}")
            return normalized
        if isinstance(value, list):
            return [
                cls._reject_sensitive_keys(item, label, f"{path}[{index}]")
                for index, item in enumerate(value)
            ]
        if isinstance(value, tuple):
            return tuple(
                cls._reject_sensitive_keys(item, label, f"{path}[{index}]")
                for index, item in enumerate(value)
            )
        return value

    @classmethod
    def records(cls, values: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        if not values:
            raise ValidationError("finops import job requires at least one cost record")
        if len(values) > 10_000:
            raise ValidationError("finops import job cannot exceed 10000 records")
        normalized = tuple(cls.json_object(value, "finops cost record") for value in values)
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > cls._MAX_JOB_JSON_BYTES:
            raise ValidationError("finops import job payload exceeds 10 MiB")
        return normalized

    @staticmethod
    def aware_datetime(value: datetime, label: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(f"{label} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def optional_datetime(cls, value: datetime | None, label: str) -> datetime | None:
        return None if value is None else cls.aware_datetime(value, label)


@dataclass(frozen=True, slots=True)
class CostAllocationRule:
    id: EntityId
    tenant_id: TenantId
    name: str
    priority: int
    category: CostCategory | None
    source: str | None
    dimension: AllocationDimension
    selector_key: str
    fixed_target: str | None
    percentage: Decimal
    active: bool
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        priority: int,
        dimension: str,
        selector_key: str,
        percentage: Decimal | str | int | float,
        category: str | None = None,
        source: str | None = None,
        fixed_target: str | None = None,
        active: bool = True,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=name,
            priority=priority,
            category=category,
            source=source,
            dimension=dimension,
            selector_key=selector_key,
            fixed_target=fixed_target,
            percentage=percentage,
            active=active,
            created_at=now,
            updated_at=now,
            version=1,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        name: str,
        priority: int,
        category: str | None,
        source: str | None,
        dimension: str,
        selector_key: str,
        fixed_target: str | None,
        percentage: Decimal | str | int | float,
        active: bool,
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        normalized_priority = int(priority)
        if not 1 <= normalized_priority <= 10000:
            raise ValidationError("allocation rule priority must be between 1 and 10000")
        normalized_dimension = AllocationDimension.from_value(dimension)
        if normalized_dimension is AllocationDimension.UNALLOCATED:
            raise ValidationError("allocation rules cannot target the unallocated dimension")
        normalized_selector = FinOpsValueValidator.selector_key(selector_key)
        normalized_fixed_target = FinOpsValueValidator.optional_token(
            fixed_target, "allocation fixed target", 192
        )
        if normalized_fixed_target is None and normalized_selector == "tenant":
            normalized_fixed_target = tenant_id.value
        if int(version) < 1:
            raise ValidationError("allocation rule version must be positive")
        created = FinOpsValueValidator.aware_datetime(created_at, "created_at")
        updated = FinOpsValueValidator.aware_datetime(updated_at, "updated_at")
        if updated < created:
            raise ValidationError("allocation rule updated_at cannot precede created_at")
        return cls(
            id=id,
            tenant_id=tenant_id,
            name=FinOpsValueValidator.text(name, "allocation rule name", 3, 160),
            priority=normalized_priority,
            category=None if category is None else CostCategory.from_value(category),
            source=FinOpsValueValidator.optional_token(source, "cost source", 128),
            dimension=normalized_dimension,
            selector_key=normalized_selector,
            fixed_target=normalized_fixed_target,
            percentage=FinOpsValueValidator.percentage(percentage),
            active=bool(active),
            created_at=created,
            updated_at=updated,
            version=int(version),
        )

    def matches(self, category: CostCategory, source: str) -> bool:
        return (
            self.active
            and (self.category is None or self.category is category)
            and (self.source is None or self.source == source)
        )

    def resolve_target(self, metadata: dict[str, Any], tenant_id: TenantId) -> str | None:
        if self.fixed_target is not None:
            return self.fixed_target
        if self.selector_key == "tenant":
            return tenant_id.value
        if self.selector_key.startswith("tag:"):
            tags = metadata.get("tags")
            if not isinstance(tags, dict):
                return None
            value = tags.get(self.selector_key[4:])
        else:
            value = metadata.get(self.selector_key)
        if value is None or not str(value).strip():
            return None
        return FinOpsValueValidator.token(str(value), "allocation target", 192)

    def revised(
        self,
        name: str,
        priority: int,
        percentage: Decimal | str | int | float,
        active: bool,
    ) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            name=name,
            priority=priority,
            category=None if self.category is None else self.category.value,
            source=self.source,
            dimension=self.dimension.value,
            selector_key=self.selector_key,
            fixed_target=self.fixed_target,
            percentage=percentage,
            active=active,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            version=self.version + 1,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "priority": self.priority,
            "category": None if self.category is None else self.category.value,
            "source": self.source,
            "dimension": self.dimension.value,
            "selector_key": self.selector_key,
            "fixed_target": self.fixed_target,
            "percentage": str(self.percentage),
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class CostAllocation:
    dimension: AllocationDimension
    target: str
    percentage: Decimal
    amount: Decimal
    rule_id: EntityId | None

    @classmethod
    def create(
        cls,
        dimension: str,
        target: str,
        percentage: Decimal | str | int | float,
        amount: Decimal | str | int | float,
        rule_id: EntityId | None = None,
    ) -> Self:
        normalized_dimension = AllocationDimension.from_value(dimension)
        normalized_target = FinOpsValueValidator.token(target, "allocation target", 192)
        if normalized_dimension is AllocationDimension.UNALLOCATED:
            normalized_target = "financial-quality/unallocated"
        return cls(
            dimension=normalized_dimension,
            target=normalized_target,
            percentage=FinOpsValueValidator.percentage(
                percentage, allow_zero=normalized_dimension is AllocationDimension.UNALLOCATED
            ),
            amount=FinOpsValueValidator.amount(amount, "allocated amount"),
            rule_id=rule_id,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension.value,
            "target": self.target,
            "percentage": str(self.percentage),
            "amount": str(self.amount),
            "rule_id": None if self.rule_id is None else self.rule_id.value,
        }


@dataclass(frozen=True, slots=True)
class CostRecord:
    id: EntityId
    tenant_id: TenantId
    external_id: str
    idempotency_key: str
    category: CostCategory
    source: str
    period_start: date
    period_end: date
    currency: str
    amount: Decimal
    owner: str
    allocation_method: str
    metadata: dict[str, Any]
    allocations: tuple[CostAllocation, ...]
    quality_status: CostQualityStatus
    imported_at: datetime
    import_job_id: EntityId

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        external_id: str,
        idempotency_key: str,
        category: str,
        source: str,
        period_start: date,
        period_end: date,
        currency: str,
        amount: Decimal | str | int | float,
        owner: str,
        allocation_method: str,
        metadata: dict[str, Any],
        allocations: tuple[CostAllocation, ...],
        import_job_id: EntityId,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            external_id=external_id,
            idempotency_key=idempotency_key,
            category=category,
            source=source,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            amount=amount,
            owner=owner,
            allocation_method=allocation_method,
            metadata=metadata,
            allocations=allocations,
            imported_at=datetime.now(UTC),
            import_job_id=import_job_id,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        external_id: str,
        idempotency_key: str,
        category: str,
        source: str,
        period_start: date,
        period_end: date,
        currency: str,
        amount: Decimal | str | int | float,
        owner: str,
        allocation_method: str,
        metadata: dict[str, Any],
        allocations: tuple[CostAllocation, ...],
        imported_at: datetime,
        import_job_id: EntityId,
    ) -> Self:
        start, end = FinOpsValueValidator.date_range(period_start, period_end, "cost period")
        normalized_amount = FinOpsValueValidator.positive_amount(amount, "cost amount")
        if not allocations:
            raise ValidationError("cost record requires at least one allocation")
        allocated_total = sum((item.amount for item in allocations), Decimal("0"))
        if allocated_total.quantize(FinOpsValueValidator._MONEY_QUANTUM) != normalized_amount:
            raise ValidationError("cost allocations must exactly equal the cost amount")
        percentage_total = sum((item.percentage for item in allocations), Decimal("0"))
        if percentage_total > Decimal("100.0001"):
            raise ValidationError("cost allocation percentages cannot exceed 100")
        unallocated = sum(
            (
                item.amount
                for item in allocations
                if item.dimension is AllocationDimension.UNALLOCATED
            ),
            Decimal("0"),
        )
        if unallocated == normalized_amount:
            quality_status = CostQualityStatus.UNALLOCATED
        elif unallocated > 0:
            quality_status = CostQualityStatus.PARTIAL
        else:
            quality_status = CostQualityStatus.ALLOCATED
        return cls(
            id=id,
            tenant_id=tenant_id,
            external_id=FinOpsValueValidator.token(external_id, "external cost id", 192),
            idempotency_key=FinOpsValueValidator.idempotency_key(idempotency_key),
            category=CostCategory.from_value(category),
            source=FinOpsValueValidator.token(source, "cost source", 128),
            period_start=start,
            period_end=end,
            currency=FinOpsValueValidator.currency(currency),
            amount=normalized_amount,
            owner=FinOpsValueValidator.text(owner, "cost owner", 2, 160),
            allocation_method=FinOpsValueValidator.token(
                allocation_method, "allocation method", 128
            ),
            metadata=FinOpsValueValidator.json_object(metadata, "cost metadata"),
            allocations=tuple(allocations),
            quality_status=quality_status,
            imported_at=FinOpsValueValidator.aware_datetime(imported_at, "imported_at"),
            import_job_id=import_job_id,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "external_id": self.external_id,
            "idempotency_key": self.idempotency_key,
            "category": self.category.value,
            "source": self.source,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "amount": str(self.amount),
            "owner": self.owner,
            "allocation_method": self.allocation_method,
            "metadata": self.metadata,
            "allocations": [item.as_dict() for item in self.allocations],
            "quality_status": self.quality_status.value,
            "imported_at": self.imported_at.isoformat(),
            "import_job_id": self.import_job_id.value,
        }


@dataclass(frozen=True, slots=True)
class CostImportJob:
    id: EntityId
    tenant_id: TenantId
    idempotency_key: str
    source: str
    records: tuple[dict[str, Any], ...]
    payload_sha256: str
    status: FinOpsImportJobStatus
    submitted_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    imported_count: int
    duplicate_count: int
    anomaly_count: int
    unallocated_count: int
    version: int

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        idempotency_key: str,
        source: str,
        records: tuple[dict[str, Any], ...],
    ) -> Self:
        normalized_records = FinOpsValueValidator.records(records)
        payload_sha256 = hashlib.sha256(
            json.dumps(
                normalized_records,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            source=source,
            records=normalized_records,
            payload_sha256=payload_sha256,
            status=FinOpsImportJobStatus.QUEUED.value,
            submitted_at=datetime.now(UTC),
            started_at=None,
            completed_at=None,
            failure_reason=None,
            imported_count=0,
            duplicate_count=0,
            anomaly_count=0,
            unallocated_count=0,
            version=1,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        idempotency_key: str,
        source: str,
        records: tuple[dict[str, Any], ...],
        payload_sha256: str,
        status: str,
        submitted_at: datetime,
        started_at: datetime | None,
        completed_at: datetime | None,
        failure_reason: str | None,
        imported_count: int,
        duplicate_count: int,
        anomaly_count: int,
        unallocated_count: int,
        version: int,
    ) -> Self:
        normalized_records = FinOpsValueValidator.records(records)
        normalized_digest = payload_sha256.strip().lower()
        expected = hashlib.sha256(
            json.dumps(
                normalized_records,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if normalized_digest != expected:
            raise ValidationError("finops import payload digest does not match records")
        try:
            normalized_status = FinOpsImportJobStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("finops import job status is unsupported") from exc
        counters = tuple(
            int(value)
            for value in (imported_count, duplicate_count, anomaly_count, unallocated_count)
        )
        if any(value < 0 for value in counters):
            raise ValidationError("finops import job counters cannot be negative")
        if int(version) < 1:
            raise ValidationError("finops import job version must be positive")
        submitted = FinOpsValueValidator.aware_datetime(submitted_at, "submitted_at")
        started = FinOpsValueValidator.optional_datetime(started_at, "started_at")
        completed = FinOpsValueValidator.optional_datetime(completed_at, "completed_at")
        if started is not None and started < submitted:
            raise ValidationError("finops import job cannot start before submission")
        if completed is not None and started is not None and completed < started:
            raise ValidationError("finops import job cannot complete before it starts")
        return cls(
            id=id,
            tenant_id=tenant_id,
            idempotency_key=FinOpsValueValidator.idempotency_key(idempotency_key),
            source=FinOpsValueValidator.token(source, "cost source", 128),
            records=normalized_records,
            payload_sha256=normalized_digest,
            status=normalized_status,
            submitted_at=submitted,
            started_at=started,
            completed_at=completed,
            failure_reason=FinOpsValueValidator.optional_text(
                failure_reason, "finops import failure reason", 2000
            ),
            imported_count=counters[0],
            duplicate_count=counters[1],
            anomaly_count=counters[2],
            unallocated_count=counters[3],
            version=int(version),
        )

    def started(self) -> Self:
        if self.status in {FinOpsImportJobStatus.RUNNING, FinOpsImportJobStatus.COMPLETED}:
            return self
        if self.status is FinOpsImportJobStatus.CANCELLED:
            raise ValidationError("cancelled finops import job cannot be started")
        return replace(
            self,
            status=FinOpsImportJobStatus.RUNNING,
            started_at=datetime.now(UTC),
            completed_at=None,
            failure_reason=None,
            version=self.version + 1,
        )

    def completed(
        self,
        imported_count: int,
        duplicate_count: int,
        anomaly_count: int,
        unallocated_count: int,
    ) -> Self:
        if self.status is not FinOpsImportJobStatus.RUNNING:
            raise ValidationError("only a running finops import job can complete")
        return replace(
            self,
            status=FinOpsImportJobStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            failure_reason=None,
            imported_count=int(imported_count),
            duplicate_count=int(duplicate_count),
            anomaly_count=int(anomaly_count),
            unallocated_count=int(unallocated_count),
            version=self.version + 1,
        )

    def failed(self, reason: str) -> Self:
        if self.status is FinOpsImportJobStatus.COMPLETED:
            raise ValidationError("completed finops import job cannot fail")
        return replace(
            self,
            status=FinOpsImportJobStatus.FAILED,
            completed_at=datetime.now(UTC),
            failure_reason=FinOpsValueValidator.text(
                reason, "finops import failure reason", 1, 2000
            ),
            version=self.version + 1,
        )

    def cancelled(self) -> Self:
        if self.status in {FinOpsImportJobStatus.COMPLETED, FinOpsImportJobStatus.CANCELLED}:
            return self
        return replace(
            self,
            status=FinOpsImportJobStatus.CANCELLED,
            completed_at=datetime.now(UTC),
            failure_reason=None,
            version=self.version + 1,
        )

    def as_dict(self, include_records: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "idempotency_key": self.idempotency_key,
            "source": self.source,
            "payload_sha256": self.payload_sha256,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat(),
            "started_at": None if self.started_at is None else self.started_at.isoformat(),
            "completed_at": None if self.completed_at is None else self.completed_at.isoformat(),
            "failure_reason": self.failure_reason,
            "record_count": len(self.records),
            "imported_count": self.imported_count,
            "duplicate_count": self.duplicate_count,
            "anomaly_count": self.anomaly_count,
            "unallocated_count": self.unallocated_count,
            "version": self.version,
        }
        if include_records:
            payload["records"] = list(self.records)
        return payload


@dataclass(frozen=True, slots=True)
class FinancialPeriod:
    id: EntityId
    tenant_id: TenantId
    period_start: date
    period_end: date
    currency: str
    status: FinancialPeriodStatus
    closed_at: datetime | None
    closed_by: str | None
    source_digest: str | None
    created_at: datetime

    @classmethod
    def create(
        cls, tenant_id: TenantId, period_start: date, period_end: date, currency: str
    ) -> Self:
        start, end = FinOpsValueValidator.date_range(period_start, period_end)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            currency=FinOpsValueValidator.currency(currency),
            status=FinancialPeriodStatus.OPEN,
            closed_at=None,
            closed_by=None,
            source_digest=None,
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        period_start: date,
        period_end: date,
        currency: str,
        status: str,
        closed_at: datetime | None,
        closed_by: str | None,
        source_digest: str | None,
        created_at: datetime,
    ) -> Self:
        start, end = FinOpsValueValidator.date_range(period_start, period_end)
        try:
            normalized_status = FinancialPeriodStatus(status.strip().lower())
        except ValueError as exc:
            raise ValidationError("financial period status is unsupported") from exc
        normalized_closed_at = FinOpsValueValidator.optional_datetime(closed_at, "closed_at")
        normalized_closed_by = FinOpsValueValidator.optional_text(
            closed_by, "financial period closing actor", 160
        )
        normalized_digest = source_digest.strip().lower() if source_digest else None
        if normalized_digest is not None and not re.fullmatch(r"[a-f0-9]{64}", normalized_digest):
            raise ValidationError("financial period source digest must be SHA-256")
        if normalized_status is FinancialPeriodStatus.CLOSED and (
            normalized_closed_at is None
            or normalized_closed_by is None
            or normalized_digest is None
        ):
            raise ValidationError("closed financial period requires actor, timestamp and digest")
        return cls(
            id=id,
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            currency=FinOpsValueValidator.currency(currency),
            status=normalized_status,
            closed_at=normalized_closed_at,
            closed_by=normalized_closed_by,
            source_digest=normalized_digest,
            created_at=FinOpsValueValidator.aware_datetime(created_at, "created_at"),
        )

    def closed(self, actor: str, source_digest: str) -> Self:
        if self.status is FinancialPeriodStatus.CLOSED:
            if self.source_digest != source_digest:
                raise ValidationError("closed financial period source digest cannot change")
            return self
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            period_start=self.period_start,
            period_end=self.period_end,
            currency=self.currency,
            status=FinancialPeriodStatus.CLOSED.value,
            closed_at=datetime.now(UTC),
            closed_by=actor,
            source_digest=source_digest,
            created_at=self.created_at,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "status": self.status.value,
            "closed_at": None if self.closed_at is None else self.closed_at.isoformat(),
            "closed_by": self.closed_by,
            "source_digest": self.source_digest,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class FinOpsBudget:
    id: EntityId
    tenant_id: TenantId
    dimension: AllocationDimension
    target: str
    period_start: date
    period_end: date
    currency: str
    amount: Decimal
    warning_threshold_percent: Decimal
    owner: str
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        dimension: str,
        target: str,
        period_start: date,
        period_end: date,
        currency: str,
        amount: Decimal | str | int | float,
        warning_threshold_percent: Decimal | str | int | float,
        owner: str,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            dimension=dimension,
            target=target,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            amount=amount,
            warning_threshold_percent=warning_threshold_percent,
            owner=owner,
            created_at=now,
            updated_at=now,
            version=1,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        dimension: str,
        target: str,
        period_start: date,
        period_end: date,
        currency: str,
        amount: Decimal | str | int | float,
        warning_threshold_percent: Decimal | str | int | float,
        owner: str,
        created_at: datetime,
        updated_at: datetime,
        version: int,
    ) -> Self:
        normalized_dimension = AllocationDimension.from_value(dimension)
        if normalized_dimension is AllocationDimension.UNALLOCATED:
            raise ValidationError("budget cannot target the unallocated bucket")
        start, end = FinOpsValueValidator.date_range(period_start, period_end, "budget period")
        created = FinOpsValueValidator.aware_datetime(created_at, "created_at")
        updated = FinOpsValueValidator.aware_datetime(updated_at, "updated_at")
        if updated < created:
            raise ValidationError("budget updated_at cannot precede created_at")
        if int(version) < 1:
            raise ValidationError("budget version must be positive")
        return cls(
            id=id,
            tenant_id=tenant_id,
            dimension=normalized_dimension,
            target=FinOpsValueValidator.token(target, "budget target", 192),
            period_start=start,
            period_end=end,
            currency=FinOpsValueValidator.currency(currency),
            amount=FinOpsValueValidator.positive_amount(amount, "budget amount"),
            warning_threshold_percent=FinOpsValueValidator.percentage(
                warning_threshold_percent, "budget warning threshold"
            ),
            owner=FinOpsValueValidator.text(owner, "budget owner", 2, 160),
            created_at=created,
            updated_at=updated,
            version=int(version),
        )

    def revised(
        self,
        amount: Decimal | str | int | float,
        warning_threshold_percent: Decimal | str | int | float,
        owner: str,
    ) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            dimension=self.dimension.value,
            target=self.target,
            period_start=self.period_start,
            period_end=self.period_end,
            currency=self.currency,
            amount=amount,
            warning_threshold_percent=warning_threshold_percent,
            owner=owner,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            version=self.version + 1,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "dimension": self.dimension.value,
            "target": self.target,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "amount": str(self.amount),
            "warning_threshold_percent": str(self.warning_threshold_percent),
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class CostAnomaly:
    id: EntityId
    tenant_id: TenantId
    record_id: EntityId
    code: str
    severity: Severity
    message: str
    deviation_percent: Decimal
    detected_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        record_id: EntityId,
        code: str,
        severity: Severity,
        message: str,
        deviation_percent: Decimal | str | int | float,
    ) -> Self:
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            record_id=record_id,
            code=FinOpsValueValidator.token(code, "cost anomaly code", 96),
            severity=severity,
            message=FinOpsValueValidator.text(message, "cost anomaly message", 3, 1000),
            deviation_percent=FinOpsValueValidator.percentage(
                deviation_percent, "cost anomaly deviation", allow_zero=True
            ),
            detected_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        record_id: EntityId,
        code: str,
        severity: str,
        message: str,
        deviation_percent: Decimal | str | int | float,
        detected_at: datetime,
    ) -> Self:
        try:
            normalized_severity = Severity(severity.strip().lower())
        except ValueError as exc:
            raise ValidationError("cost anomaly severity is unsupported") from exc
        return cls(
            id=id,
            tenant_id=tenant_id,
            record_id=record_id,
            code=FinOpsValueValidator.token(code, "cost anomaly code", 96),
            severity=normalized_severity,
            message=FinOpsValueValidator.text(message, "cost anomaly message", 3, 1000),
            deviation_percent=FinOpsValueValidator.percentage(
                deviation_percent, "cost anomaly deviation", allow_zero=True
            ),
            detected_at=FinOpsValueValidator.aware_datetime(detected_at, "detected_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "record_id": self.record_id.value,
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "deviation_percent": str(self.deviation_percent),
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class FinOpsForecast:
    id: EntityId
    tenant_id: TenantId
    dimension: AllocationDimension
    target: str
    period_start: date
    period_end: date
    currency: str
    expected_amount: Decimal
    basis_period_count: int
    confidence_percent: Decimal
    input_digest: str
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        dimension: str,
        target: str,
        period_start: date,
        period_end: date,
        currency: str,
        expected_amount: Decimal | str | int | float,
        basis_period_count: int,
        confidence_percent: Decimal | str | int | float,
        input_digest: str,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            dimension=dimension,
            target=target,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            expected_amount=expected_amount,
            basis_period_count=basis_period_count,
            confidence_percent=confidence_percent,
            input_digest=input_digest,
            generated_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        dimension: str,
        target: str,
        period_start: date,
        period_end: date,
        currency: str,
        expected_amount: Decimal | str | int | float,
        basis_period_count: int,
        confidence_percent: Decimal | str | int | float,
        input_digest: str,
        generated_at: datetime,
    ) -> Self:
        normalized_dimension = AllocationDimension.from_value(dimension)
        start, end = FinOpsValueValidator.date_range(period_start, period_end, "forecast period")
        periods = int(basis_period_count)
        if not 1 <= periods <= 36:
            raise ValidationError("forecast basis period count must be between 1 and 36")
        digest = input_digest.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValidationError("forecast input digest must be SHA-256")
        return cls(
            id=id,
            tenant_id=tenant_id,
            dimension=normalized_dimension,
            target=FinOpsValueValidator.token(target, "forecast target", 192),
            period_start=start,
            period_end=end,
            currency=FinOpsValueValidator.currency(currency),
            expected_amount=FinOpsValueValidator.amount(
                expected_amount, "forecast expected amount"
            ),
            basis_period_count=periods,
            confidence_percent=FinOpsValueValidator.percentage(
                confidence_percent, "forecast confidence", allow_zero=True
            ),
            input_digest=digest,
            generated_at=FinOpsValueValidator.aware_datetime(generated_at, "generated_at"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "dimension": self.dimension.value,
            "target": self.target,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "expected_amount": str(self.expected_amount),
            "basis_period_count": self.basis_period_count,
            "confidence_percent": str(self.confidence_percent),
            "input_digest": self.input_digest,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class FinOpsReportLine:
    target: str
    amount: Decimal
    record_count: int
    budget_amount: Decimal | None
    variance_amount: Decimal | None
    variance_percent: Decimal | None
    forecast_amount: Decimal | None
    anomaly_count: int

    @classmethod
    def create(
        cls,
        target: str,
        amount: Decimal | str | int | float,
        record_count: int,
        budget_amount: Decimal | str | int | float | None,
        forecast_amount: Decimal | str | int | float | None,
        anomaly_count: int,
    ) -> Self:
        normalized_amount = FinOpsValueValidator.amount(amount, "report line amount")
        normalized_budget = (
            None
            if budget_amount is None
            else FinOpsValueValidator.amount(budget_amount, "report line budget amount")
        )
        normalized_forecast = (
            None
            if forecast_amount is None
            else FinOpsValueValidator.amount(forecast_amount, "report line forecast amount")
        )
        variance_amount = None
        variance_percent = None
        if normalized_budget is not None:
            variance_amount = (normalized_amount - normalized_budget).quantize(
                FinOpsValueValidator._MONEY_QUANTUM
            )
            if normalized_budget > 0:
                variance_percent = (variance_amount / normalized_budget * Decimal("100")).quantize(
                    FinOpsValueValidator._PERCENT_QUANTUM
                )
        if int(record_count) < 0 or int(anomaly_count) < 0:
            raise ValidationError("report line counters cannot be negative")
        return cls(
            target=FinOpsValueValidator.token(target, "report target", 192),
            amount=normalized_amount,
            record_count=int(record_count),
            budget_amount=normalized_budget,
            variance_amount=variance_amount,
            variance_percent=variance_percent,
            forecast_amount=normalized_forecast,
            anomaly_count=int(anomaly_count),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "amount": str(self.amount),
            "record_count": self.record_count,
            "budget_amount": None if self.budget_amount is None else str(self.budget_amount),
            "variance_amount": (
                None if self.variance_amount is None else str(self.variance_amount)
            ),
            "variance_percent": (
                None if self.variance_percent is None else str(self.variance_percent)
            ),
            "forecast_amount": (
                None if self.forecast_amount is None else str(self.forecast_amount)
            ),
            "anomaly_count": self.anomaly_count,
        }


@dataclass(frozen=True, slots=True)
class FinOpsReport:
    id: EntityId
    tenant_id: TenantId
    kind: FinOpsReportKind
    period_start: date
    period_end: date
    group_by: AllocationDimension
    currency: str
    total_amount: Decimal
    unallocated_amount: Decimal
    quality_score_percent: Decimal
    chargeback_markup_percent: Decimal
    lines: tuple[FinOpsReportLine, ...]
    input_digest: str
    closed_period: bool
    generated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        kind: str,
        period_start: date,
        period_end: date,
        group_by: str,
        currency: str,
        total_amount: Decimal | str | int | float,
        unallocated_amount: Decimal | str | int | float,
        chargeback_markup_percent: Decimal | str | int | float,
        lines: tuple[FinOpsReportLine, ...],
        input_digest: str,
        closed_period: bool,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            kind=kind,
            period_start=period_start,
            period_end=period_end,
            group_by=group_by,
            currency=currency,
            total_amount=total_amount,
            unallocated_amount=unallocated_amount,
            chargeback_markup_percent=chargeback_markup_percent,
            lines=lines,
            input_digest=input_digest,
            closed_period=closed_period,
            generated_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        kind: str,
        period_start: date,
        period_end: date,
        group_by: str,
        currency: str,
        total_amount: Decimal | str | int | float,
        unallocated_amount: Decimal | str | int | float,
        chargeback_markup_percent: Decimal | str | int | float,
        lines: tuple[FinOpsReportLine, ...],
        input_digest: str,
        closed_period: bool,
        generated_at: datetime,
    ) -> Self:
        start, end = FinOpsValueValidator.date_range(period_start, period_end, "report period")
        normalized_total = FinOpsValueValidator.amount(total_amount, "report total")
        normalized_unallocated = FinOpsValueValidator.amount(
            unallocated_amount, "report unallocated amount"
        )
        if normalized_unallocated > normalized_total:
            raise ValidationError("report unallocated amount cannot exceed total")
        quality = Decimal("100")
        if normalized_total > 0:
            quality = (
                (normalized_total - normalized_unallocated) / normalized_total * Decimal("100")
            ).quantize(FinOpsValueValidator._PERCENT_QUANTUM)
        digest = input_digest.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValidationError("finops report input digest must be SHA-256")
        return cls(
            id=id,
            tenant_id=tenant_id,
            kind=FinOpsReportKind.from_value(kind),
            period_start=start,
            period_end=end,
            group_by=AllocationDimension.from_value(group_by),
            currency=FinOpsValueValidator.currency(currency),
            total_amount=normalized_total,
            unallocated_amount=normalized_unallocated,
            quality_score_percent=quality,
            chargeback_markup_percent=FinOpsValueValidator.percentage(
                chargeback_markup_percent, "chargeback markup", allow_zero=True
            ),
            lines=tuple(lines),
            input_digest=digest,
            closed_period=bool(closed_period),
            generated_at=FinOpsValueValidator.aware_datetime(generated_at, "generated_at"),
        )

    def reproducibility_key(self) -> str:
        payload = {
            "tenant_id": self.tenant_id.value,
            "kind": self.kind.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "group_by": self.group_by.value,
            "currency": self.currency,
            "markup": str(self.chargeback_markup_percent),
            "input_digest": self.input_digest,
            "closed_period": self.closed_period,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "kind": self.kind.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "group_by": self.group_by.value,
            "currency": self.currency,
            "total_amount": str(self.total_amount),
            "unallocated_amount": str(self.unallocated_amount),
            "quality_score_percent": str(self.quality_score_percent),
            "chargeback_markup_percent": str(self.chargeback_markup_percent),
            "lines": [item.as_dict() for item in self.lines],
            "input_digest": self.input_digest,
            "reproducibility_key": self.reproducibility_key(),
            "closed_period": self.closed_period,
            "generated_at": self.generated_at.isoformat(),
            "production_billing_mutation": False,
        }
