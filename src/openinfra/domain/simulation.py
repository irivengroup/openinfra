from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import EntityId, Severity, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceObjectKey


class SimulationChangeKind(StrEnum):
    EQUIPMENT_MOVE = "equipment-move"
    EQUIPMENT_ADD = "equipment-add"
    EQUIPMENT_REMOVE = "equipment-remove"
    EQUIPMENT_OUTAGE = "equipment-outage"
    VLAN_CHANGE = "vlan-change"
    VRF_CHANGE = "vrf-change"
    SUBNET_CHANGE = "subnet-change"
    DNS_CHANGE = "dns-change"
    FIREWALL_CHANGE = "firewall-change"
    PDU_OUTAGE = "pdu-outage"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {
            "move": cls.EQUIPMENT_MOVE.value,
            "add": cls.EQUIPMENT_ADD.value,
            "remove": cls.EQUIPMENT_REMOVE.value,
            "outage": cls.EQUIPMENT_OUTAGE.value,
            "cut": cls.EQUIPMENT_OUTAGE.value,
            "pdu-cut": cls.PDU_OUTAGE.value,
        }
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("simulation change kind is unsupported") from exc


class SimulationScenarioStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationImpactDimension(StrEnum):
    DEPENDENCY = "dependency"
    FLOW = "flow"
    IPAM = "ipam"
    ENERGY = "energy"
    COOLING = "cooling"
    COST = "cost"
    BUSINESS_SERVICE = "business-service"
    DATA_QUALITY = "data-quality"


class ReadinessScopeType(StrEnum):
    SCENARIO = "scenario"
    APPLICATION = "application"
    ASSET = "asset"
    SUBNET = "subnet"
    SITE = "site"


class SimulationValueValidator:
    _MAX_JSON_BYTES = 65_536

    @classmethod
    def text(cls, value: str, label: str, minimum: int = 1, maximum: int = 2000) -> str:
        normalized = " ".join(value.strip().split())
        if not minimum <= len(normalized) <= maximum:
            raise ValidationError(f"{label} must contain {minimum} to {maximum} characters")
        return normalized

    @classmethod
    def optional_token(cls, value: str | None, label: str) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().lower().replace("_", "-")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{0,63}", normalized):
            raise ValidationError(f"{label} must use 1 to 64 safe characters")
        return normalized

    @classmethod
    def idempotency_key(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}", normalized):
            raise ValidationError("simulation idempotency key must use 8 to 128 safe characters")
        return normalized

    @classmethod
    def json_object(cls, value: dict[str, Any], label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValidationError(f"{label} must be a JSON object")
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > cls._MAX_JSON_BYTES:
            raise ValidationError(f"{label} exceeds 64 KiB")
        return dict(value)

    @classmethod
    def assumptions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) > 50:
            raise ValidationError("simulation assumptions cannot exceed 50 entries")
        normalized = tuple(
            sorted({cls.text(value, "simulation assumption", 3, 500) for value in values})
        )
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
class SimulationChange:
    id: EntityId
    kind: SimulationChangeKind
    target_key: str
    before: dict[str, Any]
    after: dict[str, Any]
    assumptions: tuple[str, ...]

    @classmethod
    def create(
        cls,
        kind: str,
        target_key: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        assumptions: tuple[str, ...] = (),
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            kind=kind,
            target_key=target_key,
            before=before or {},
            after=after or {},
            assumptions=assumptions,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        kind: str,
        target_key: str,
        before: dict[str, Any],
        after: dict[str, Any],
        assumptions: tuple[str, ...],
    ) -> Self:
        normalized_kind = SimulationChangeKind.from_value(kind)
        normalized_before = SimulationValueValidator.json_object(before, "simulation before state")
        normalized_after = SimulationValueValidator.json_object(after, "simulation after state")
        cls._validate_kind_payload(normalized_kind, normalized_before, normalized_after)
        return cls(
            id=id,
            kind=normalized_kind,
            target_key=SourceObjectKey.from_value(target_key).value,
            before=normalized_before,
            after=normalized_after,
            assumptions=SimulationValueValidator.assumptions(assumptions),
        )

    @staticmethod
    def _validate_kind_payload(
        kind: SimulationChangeKind,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> None:
        if kind is SimulationChangeKind.EQUIPMENT_MOVE and not any(
            key in after for key in ("site", "building", "room", "rack", "u_position")
        ):
            raise ValidationError("equipment move requires a target physical location")
        required_after = {
            SimulationChangeKind.VLAN_CHANGE: ("vlan", "vlan_id"),
            SimulationChangeKind.VRF_CHANGE: ("vrf", "vrf_name"),
            SimulationChangeKind.SUBNET_CHANGE: ("subnet", "prefix"),
            SimulationChangeKind.DNS_CHANGE: ("dns_name", "resolver", "record"),
            SimulationChangeKind.FIREWALL_CHANGE: ("policy", "action", "rule"),
        }
        candidates = required_after.get(kind)
        if candidates is not None and not any(key in after for key in candidates):
            raise ValidationError(f"{kind.value} requires one of: {', '.join(candidates)}")
        if (
            kind
            in (
                SimulationChangeKind.EQUIPMENT_REMOVE,
                SimulationChangeKind.EQUIPMENT_OUTAGE,
                SimulationChangeKind.PDU_OUTAGE,
            )
            and after
        ):
            raise ValidationError(f"{kind.value} must not define an after state")
        if kind is SimulationChangeKind.EQUIPMENT_ADD and before:
            raise ValidationError("equipment-add must not define a before state")

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "kind": self.kind.value,
            "target_key": self.target_key,
            "before": self.before,
            "after": self.after,
            "assumptions": list(self.assumptions),
        }

    def as_dict(self) -> dict[str, object]:
        return self.fingerprint_payload()


@dataclass(frozen=True, slots=True)
class SimulationScenario:
    id: EntityId
    tenant_id: TenantId
    name: str
    description: str
    owner: str
    site: str | None
    environment: str | None
    criticality: str | None
    idempotency_key: str
    status: SimulationScenarioStatus
    changes: tuple[SimulationChange, ...]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    version: int

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        description: str,
        owner: str,
        idempotency_key: str,
        changes: tuple[SimulationChange, ...],
        site: str | None = None,
        environment: str | None = None,
        criticality: str | None = None,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=name,
            description=description,
            owner=owner,
            site=site,
            environment=environment,
            criticality=criticality,
            idempotency_key=idempotency_key,
            status=SimulationScenarioStatus.DRAFT.value,
            changes=changes,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
            failure_reason=None,
            version=1,
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        name: str,
        description: str,
        owner: str,
        site: str | None,
        environment: str | None,
        criticality: str | None,
        idempotency_key: str,
        status: str,
        changes: tuple[SimulationChange, ...],
        created_at: datetime,
        updated_at: datetime,
        started_at: datetime | None,
        completed_at: datetime | None,
        failure_reason: str | None,
        version: int,
    ) -> Self:
        if not 1 <= len(changes) <= 100:
            raise ValidationError("simulation scenario requires 1 to 100 changes")
        target_pairs = {(item.kind.value, item.target_key) for item in changes}
        if len(target_pairs) != len(changes):
            raise ValidationError("simulation scenario contains duplicate target changes")
        created = SimulationValueValidator.aware_datetime(created_at, "scenario created_at")
        updated = SimulationValueValidator.aware_datetime(updated_at, "scenario updated_at")
        started = SimulationValueValidator.optional_datetime(started_at, "scenario started_at")
        completed = SimulationValueValidator.optional_datetime(
            completed_at, "scenario completed_at"
        )
        if updated < created:
            raise ValidationError("simulation scenario updated_at cannot precede created_at")
        if started is not None and started < created:
            raise ValidationError("simulation scenario started_at cannot precede created_at")
        if completed is not None and (started is None or completed < started):
            raise ValidationError("simulation scenario completed_at requires a valid started_at")
        normalized_failure = (
            None
            if failure_reason is None
            else SimulationValueValidator.text(failure_reason, "simulation failure reason", 3, 1000)
        )
        normalized_version = int(version)
        if normalized_version < 1:
            raise ValidationError("simulation scenario version must be positive")
        return cls(
            id=id,
            tenant_id=tenant_id,
            name=SimulationValueValidator.text(name, "simulation scenario name", 3, 160),
            description=SimulationValueValidator.text(
                description, "simulation scenario description", 10, 2000
            ),
            owner=SimulationValueValidator.text(owner, "simulation scenario owner", 2, 128),
            site=SimulationValueValidator.optional_token(site, "simulation site"),
            environment=SimulationValueValidator.optional_token(
                environment, "simulation environment"
            ),
            criticality=SimulationValueValidator.optional_token(
                criticality, "simulation criticality"
            ),
            idempotency_key=SimulationValueValidator.idempotency_key(idempotency_key),
            status=SimulationScenarioStatus(status.strip().lower()),
            changes=changes,
            created_at=created,
            updated_at=updated,
            started_at=started,
            completed_at=completed,
            failure_reason=normalized_failure,
            version=normalized_version,
        )

    def queued(self) -> Self:
        if self.status not in (SimulationScenarioStatus.DRAFT, SimulationScenarioStatus.FAILED):
            raise ValidationError("only draft or failed simulations can be queued")
        return replace(
            self,
            status=SimulationScenarioStatus.QUEUED,
            failure_reason=None,
            updated_at=datetime.now(UTC),
            version=self.version + 1,
        )

    def started(self) -> Self:
        if self.status not in (
            SimulationScenarioStatus.DRAFT,
            SimulationScenarioStatus.QUEUED,
            SimulationScenarioStatus.RUNNING,
            SimulationScenarioStatus.FAILED,
        ):
            raise ValidationError("simulation cannot start from its current state")
        now = datetime.now(UTC)
        return replace(
            self,
            status=SimulationScenarioStatus.RUNNING,
            started_at=self.started_at or now,
            completed_at=None,
            failure_reason=None,
            updated_at=now,
            version=self.version + 1,
        )

    def completed(self) -> Self:
        if self.status is not SimulationScenarioStatus.RUNNING:
            raise ValidationError("only running simulations can complete")
        now = datetime.now(UTC)
        return replace(
            self,
            status=SimulationScenarioStatus.COMPLETED,
            completed_at=now,
            updated_at=now,
            version=self.version + 1,
        )

    def failed(self, reason: str) -> Self:
        if self.status is not SimulationScenarioStatus.RUNNING:
            raise ValidationError("only running simulations can fail")
        now = datetime.now(UTC)
        return replace(
            self,
            status=SimulationScenarioStatus.FAILED,
            failure_reason=SimulationValueValidator.text(
                reason, "simulation failure reason", 3, 1000
            ),
            completed_at=now,
            updated_at=now,
            version=self.version + 1,
        )

    def cancelled(self) -> Self:
        if self.status in (
            SimulationScenarioStatus.COMPLETED,
            SimulationScenarioStatus.CANCELLED,
        ):
            raise ValidationError("completed or cancelled simulations cannot be cancelled")
        now = datetime.now(UTC)
        return replace(
            self,
            status=SimulationScenarioStatus.CANCELLED,
            completed_at=now if self.started_at is not None else None,
            updated_at=now,
            version=self.version + 1,
        )

    def input_sha256(self) -> str:
        payload = {
            "scenario_id": self.id.value,
            "changes": [item.fingerprint_payload() for item in self.changes],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "site": self.site,
            "environment": self.environment,
            "criticality": self.criticality,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "changes": [item.as_dict() for item in self.changes],
            "input_sha256": self.input_sha256(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "failure_reason": self.failure_reason,
            "version": self.version,
            "execution_allowed": False,
            "production_mutation": False,
            "itsm_native_change_created": False,
        }


@dataclass(frozen=True, slots=True)
class SimulationImpactFinding:
    dimension: SimulationImpactDimension
    severity: Severity
    code: str
    message: str
    object_key: str | None
    evidence: dict[str, Any]

    @classmethod
    def create(
        cls,
        dimension: str,
        severity: str,
        code: str,
        message: str,
        object_key: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> Self:
        normalized_code = code.strip().upper().replace("-", "_")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", normalized_code):
            raise ValidationError("simulation finding code is invalid")
        normalized_object = (
            None if object_key is None else SourceObjectKey.from_value(object_key).value
        )
        try:
            normalized_severity = Severity(severity.strip().lower())
        except ValueError as exc:
            raise ValidationError("simulation finding severity is invalid") from exc
        return cls(
            dimension=SimulationImpactDimension(dimension.strip().lower()),
            severity=normalized_severity,
            code=normalized_code,
            message=SimulationValueValidator.text(message, "simulation finding message", 5, 1000),
            object_key=normalized_object,
            evidence=SimulationValueValidator.json_object(
                evidence or {}, "simulation finding evidence"
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "object_key": self.object_key,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class SimulationReadinessScore:
    scope_type: ReadinessScopeType
    scope_key: str
    score: int
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    missing_evidence: tuple[str, ...]

    @classmethod
    def create(
        cls,
        scope_type: str,
        scope_key: str,
        score: int,
        blockers: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        missing_evidence: tuple[str, ...] = (),
    ) -> Self:
        normalized_score = int(score)
        if not 0 <= normalized_score <= 100:
            raise ValidationError("simulation readiness score must be between 0 and 100")
        return cls(
            scope_type=ReadinessScopeType(scope_type.strip().lower()),
            scope_key=SimulationValueValidator.text(
                scope_key, "simulation readiness scope key", 1, 256
            ),
            score=normalized_score,
            blockers=SimulationValueValidator.assumptions(blockers),
            warnings=SimulationValueValidator.assumptions(warnings),
            missing_evidence=SimulationValueValidator.assumptions(missing_evidence),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "scope_type": self.scope_type.value,
            "scope_key": self.scope_key,
            "score": self.score,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "missing_evidence": list(self.missing_evidence),
        }


@dataclass(frozen=True, slots=True)
class SimulationMoveGroup:
    id: EntityId
    name: str
    member_keys: tuple[str, ...]
    affinity_reasons: tuple[str, ...]
    risk_score: int

    @classmethod
    def create(
        cls,
        name: str,
        member_keys: tuple[str, ...],
        affinity_reasons: tuple[str, ...],
        risk_score: int,
    ) -> Self:
        members = tuple(sorted({SourceObjectKey.from_value(value).value for value in member_keys}))
        if not members:
            raise ValidationError("simulation move group requires at least one member")
        normalized_risk = int(risk_score)
        if not 0 <= normalized_risk <= 100:
            raise ValidationError("simulation move group risk score must be between 0 and 100")
        return cls(
            id=EntityId.new(),
            name=SimulationValueValidator.text(name, "simulation move group name", 3, 160),
            member_keys=members,
            affinity_reasons=SimulationValueValidator.assumptions(affinity_reasons),
            risk_score=normalized_risk,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "name": self.name,
            "member_keys": list(self.member_keys),
            "affinity_reasons": list(self.affinity_reasons),
            "risk_score": self.risk_score,
        }


@dataclass(frozen=True, slots=True)
class SimulationBlockingDependency:
    source_key: str
    target_key: str
    relation_type: str
    reason: str

    @classmethod
    def create(cls, source_key: str, target_key: str, relation_type: str, reason: str) -> Self:
        relation = relation_type.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", relation):
            raise ValidationError("simulation blocking relation type is invalid")
        return cls(
            source_key=SourceObjectKey.from_value(source_key).value,
            target_key=SourceObjectKey.from_value(target_key).value,
            relation_type=relation,
            reason=SimulationValueValidator.text(
                reason, "simulation blocking dependency reason", 5, 500
            ),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "source_key": self.source_key,
            "target_key": self.target_key,
            "relation_type": self.relation_type,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class SimulationMigrationWave:
    number: int
    group_ids: tuple[EntityId, ...]
    blocked_by_group_ids: tuple[EntityId, ...]
    readiness_score: int

    @classmethod
    def create(
        cls,
        number: int,
        group_ids: tuple[EntityId, ...],
        blocked_by_group_ids: tuple[EntityId, ...],
        readiness_score: int,
    ) -> Self:
        normalized_number = int(number)
        if normalized_number < 1:
            raise ValidationError("migration wave number must be positive")
        if not group_ids:
            raise ValidationError("migration wave requires at least one move group")
        normalized_score = int(readiness_score)
        if not 0 <= normalized_score <= 100:
            raise ValidationError("migration wave readiness score must be between 0 and 100")
        return cls(
            number=normalized_number,
            group_ids=tuple(dict.fromkeys(group_ids)),
            blocked_by_group_ids=tuple(dict.fromkeys(blocked_by_group_ids)),
            readiness_score=normalized_score,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "number": self.number,
            "group_ids": [item.value for item in self.group_ids],
            "blocked_by_group_ids": [item.value for item in self.blocked_by_group_ids],
            "readiness_score": self.readiness_score,
        }


@dataclass(frozen=True, slots=True)
class SimulationImpactReport:
    id: EntityId
    tenant_id: TenantId
    scenario_id: EntityId
    scenario_version: int
    input_sha256: str
    impacted_keys: tuple[str, ...]
    findings: tuple[SimulationImpactFinding, ...]
    baseline_summary: dict[str, Any]
    projected_summary: dict[str, Any]
    capacity_delta: dict[str, float]
    risk_before: int
    risk_after: int
    readiness_scores: tuple[SimulationReadinessScore, ...]
    move_groups: tuple[SimulationMoveGroup, ...]
    waves: tuple[SimulationMigrationWave, ...]
    blocking_dependencies: tuple[SimulationBlockingDependency, ...]
    assumptions: tuple[str, ...]
    generated_at: datetime
    truncated: bool
    engine_version: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        scenario_id: EntityId,
        scenario_version: int,
        input_sha256: str,
        impacted_keys: tuple[str, ...],
        findings: tuple[SimulationImpactFinding, ...],
        baseline_summary: dict[str, Any],
        projected_summary: dict[str, Any],
        capacity_delta: dict[str, float],
        risk_before: int,
        risk_after: int,
        readiness_scores: tuple[SimulationReadinessScore, ...],
        move_groups: tuple[SimulationMoveGroup, ...],
        waves: tuple[SimulationMigrationWave, ...],
        blocking_dependencies: tuple[SimulationBlockingDependency, ...],
        assumptions: tuple[str, ...],
        truncated: bool,
        engine_version: str,
    ) -> Self:
        sha = input_sha256.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValidationError("simulation input fingerprint must be SHA-256")
        before = int(risk_before)
        after = int(risk_after)
        if not 0 <= before <= 100 or not 0 <= after <= 100:
            raise ValidationError("simulation risk scores must be between 0 and 100")
        normalized_capacity: dict[str, float] = {}
        for key, value in capacity_delta.items():
            normalized_key = SimulationValueValidator.optional_token(key, "capacity delta key")
            if normalized_key is None:
                raise ValidationError("capacity delta key cannot be empty")
            normalized_capacity[normalized_key] = float(value)
        version = SimulationValueValidator.text(engine_version, "simulation engine version", 1, 64)
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            scenario_id=scenario_id,
            scenario_version=int(scenario_version),
            input_sha256=sha,
            impacted_keys=tuple(
                sorted({SourceObjectKey.from_value(value).value for value in impacted_keys})
            ),
            findings=findings,
            baseline_summary=SimulationValueValidator.json_object(
                baseline_summary, "simulation baseline summary"
            ),
            projected_summary=SimulationValueValidator.json_object(
                projected_summary, "simulation projected summary"
            ),
            capacity_delta=normalized_capacity,
            risk_before=before,
            risk_after=after,
            readiness_scores=readiness_scores,
            move_groups=move_groups,
            waves=waves,
            blocking_dependencies=blocking_dependencies,
            assumptions=SimulationValueValidator.assumptions(assumptions),
            generated_at=datetime.now(UTC),
            truncated=bool(truncated),
            engine_version=version,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "scenario_id": self.scenario_id.value,
            "scenario_version": self.scenario_version,
            "input_sha256": self.input_sha256,
            "impacted_keys": list(self.impacted_keys),
            "findings": [item.as_dict() for item in self.findings],
            "baseline_summary": self.baseline_summary,
            "projected_summary": self.projected_summary,
            "capacity_delta": self.capacity_delta,
            "risk_before": self.risk_before,
            "risk_after": self.risk_after,
            "risk_delta": self.risk_after - self.risk_before,
            "readiness_scores": [item.as_dict() for item in self.readiness_scores],
            "move_groups": [item.as_dict() for item in self.move_groups],
            "waves": [item.as_dict() for item in self.waves],
            "blocking_dependencies": [item.as_dict() for item in self.blocking_dependencies],
            "assumptions": list(self.assumptions),
            "generated_at": self.generated_at.isoformat(),
            "truncated": self.truncated,
            "engine_version": self.engine_version,
            "production_mutation": False,
            "execution_order": False,
        }


@dataclass(frozen=True, slots=True)
class SimulationScenarioComparison:
    id: EntityId
    tenant_id: TenantId
    left_report_id: EntityId
    right_report_id: EntityId
    summary: dict[str, Any]
    preferred_report_id: EntityId | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        left_report_id: EntityId,
        right_report_id: EntityId,
        summary: dict[str, Any],
        preferred_report_id: EntityId | None,
    ) -> Self:
        if left_report_id == right_report_id:
            raise ValidationError("scenario comparison requires two distinct reports")
        return cls(
            id=EntityId.new(),
            tenant_id=tenant_id,
            left_report_id=left_report_id,
            right_report_id=right_report_id,
            summary=SimulationValueValidator.json_object(summary, "simulation comparison summary"),
            preferred_report_id=preferred_report_id,
            created_at=datetime.now(UTC),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "left_report_id": self.left_report_id.value,
            "right_report_id": self.right_report_id.value,
            "summary": self.summary,
            "preferred_report_id": (
                self.preferred_report_id.value if self.preferred_report_id else None
            ),
            "created_at": self.created_at.isoformat(),
        }
