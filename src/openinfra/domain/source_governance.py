from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self

from openinfra.domain.common import EntityId, Pagination, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceObjectKind, SourceSystem


class SourceConflictStrategy(StrEnum):
    REJECT = "reject"
    ACCEPT_WITH_AUDIT = "accept_with_audit"


@dataclass(frozen=True, slots=True)
class GovernanceRuleName:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{1,63}", normalized):
            raise ValidationError("governance rule name must use 2 to 64 safe characters")
        return cls(normalized)


@dataclass(frozen=True, slots=True)
class GovernedAttributePath:
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower()
        if normalized == "*":
            return cls(normalized)
        if not re.fullmatch(r"[a-z0-9][a-z0-9_:-]{0,63}(\.[a-z0-9][a-z0-9_:-]{0,63}){0,7}", normalized):
            raise ValidationError("governed attribute path must be '*' or a safe dotted path")
        return cls(normalized)

    def matches(self, changed_path: str) -> bool:
        normalized = changed_path.strip().lower()
        return self.value == "*" or self.value == normalized or normalized.startswith(self.value + ".")


@dataclass(frozen=True, slots=True)
class SourceGovernanceRule:
    id: EntityId
    tenant_id: TenantId
    name: GovernanceRuleName
    object_kind: SourceObjectKind | None
    attribute_path: GovernedAttributePath
    authoritative_source: SourceSystem
    priority: int
    freshness_seconds: int | None
    conflict_strategy: SourceConflictStrategy
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        name: str,
        object_kind: str | None,
        attribute_path: str,
        authoritative_source: str,
        priority: int,
        freshness_seconds: int | None,
        conflict_strategy: str,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            name=name,
            object_kind=object_kind,
            attribute_path=attribute_path,
            authoritative_source=authoritative_source,
            priority=priority,
            freshness_seconds=freshness_seconds,
            conflict_strategy=conflict_strategy,
            active=True,
            created_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        id: EntityId,
        tenant_id: TenantId,
        name: str,
        object_kind: str | None,
        attribute_path: str,
        authoritative_source: str,
        priority: int,
        freshness_seconds: int | None,
        conflict_strategy: str,
        active: bool,
        created_at: datetime,
    ) -> Self:
        normalized_priority = int(priority)
        if normalized_priority < 0 or normalized_priority > 1_000_000:
            raise ValidationError("governance rule priority must be between 0 and 1000000")
        normalized_freshness = cls._normalize_freshness(freshness_seconds)
        if created_at.tzinfo is None:
            raise ValidationError("governance rule created_at must be timezone-aware")
        kind = cls._normalize_kind(object_kind)
        return cls(
            id=id,
            tenant_id=tenant_id,
            name=GovernanceRuleName.from_value(name),
            object_kind=kind,
            attribute_path=GovernedAttributePath.from_value(attribute_path),
            authoritative_source=SourceSystem.from_value(authoritative_source),
            priority=normalized_priority,
            freshness_seconds=normalized_freshness,
            conflict_strategy=SourceConflictStrategy(str(conflict_strategy).strip().lower()),
            active=bool(active),
            created_at=created_at.astimezone(UTC),
        )

    @classmethod
    def _normalize_kind(cls, value: str | None) -> SourceObjectKind | None:
        if value is None or str(value).strip() in ("", "*"):
            return None
        return SourceObjectKind(str(value).strip().lower())

    @classmethod
    def _normalize_freshness(cls, value: int | None) -> int | None:
        if value is None:
            return None
        normalized = int(value)
        if normalized < 60 or normalized > 366 * 24 * 60 * 60:
            raise ValidationError("governance freshness must be between 60 seconds and 366 days")
        return normalized

    def applies_to(self, object_kind: SourceObjectKind, changed_path: str) -> bool:
        return self.active and (self.object_kind is None or self.object_kind == object_kind) and self.attribute_path.matches(changed_path)

    def is_authoritative(self, source: SourceSystem) -> bool:
        return self.authoritative_source == source

    def is_stale(self, observed_at: datetime | None, now: datetime | None = None) -> bool:
        if self.freshness_seconds is None or observed_at is None:
            return False
        if observed_at.tzinfo is None:
            raise ValidationError("source observed timestamp must be timezone-aware")
        current = (now or datetime.now(UTC)).astimezone(UTC)
        return (current - observed_at.astimezone(UTC)).total_seconds() > self.freshness_seconds

    def disabled(self) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name.value,
            object_kind=self.object_kind.value if self.object_kind else None,
            attribute_path=self.attribute_path.value,
            authoritative_source=self.authoritative_source.value,
            priority=self.priority,
            freshness_seconds=self.freshness_seconds,
            conflict_strategy=self.conflict_strategy.value,
            active=False,
            created_at=self.created_at,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "name": self.name.value,
            "object_kind": self.object_kind.value if self.object_kind else "*",
            "attribute_path": self.attribute_path.value,
            "authoritative_source": self.authoritative_source.value,
            "priority": self.priority,
            "freshness_seconds": self.freshness_seconds,
            "conflict_strategy": self.conflict_strategy.value,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SourceGovernanceConflict:
    attribute_path: GovernedAttributePath
    rule_name: GovernanceRuleName
    authoritative_source: SourceSystem
    incoming_source: SourceSystem
    strategy: SourceConflictStrategy
    existing_value: Any
    incoming_value: Any

    @classmethod
    def create(
        cls,
        attribute_path: str,
        rule: SourceGovernanceRule,
        incoming_source: SourceSystem,
        existing_value: Any,
        incoming_value: Any,
    ) -> Self:
        return cls(
            attribute_path=GovernedAttributePath.from_value(attribute_path),
            rule_name=rule.name,
            authoritative_source=rule.authoritative_source,
            incoming_source=incoming_source,
            strategy=rule.conflict_strategy,
            existing_value=existing_value,
            incoming_value=incoming_value,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "attribute_path": self.attribute_path.value,
            "rule_name": self.rule_name.value,
            "authoritative_source": self.authoritative_source.value,
            "incoming_source": self.incoming_source.value,
            "strategy": self.strategy.value,
            "existing_value": self.existing_value,
            "incoming_value": self.incoming_value,
        }


@dataclass(frozen=True, slots=True)
class SourceGovernanceEvaluation:
    tenant_id: TenantId
    object_kind: SourceObjectKind
    incoming_source: SourceSystem
    accepted: bool
    changed_paths: tuple[GovernedAttributePath, ...]
    stale_rule_names: tuple[GovernanceRuleName, ...]
    conflicts: tuple[SourceGovernanceConflict, ...]

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        object_kind: SourceObjectKind,
        incoming_source: SourceSystem,
        changed_paths: tuple[str, ...],
        stale_rule_names: tuple[str, ...],
        conflicts: tuple[SourceGovernanceConflict, ...],
    ) -> Self:
        blocking_conflicts = [
            conflict for conflict in conflicts if conflict.strategy == SourceConflictStrategy.REJECT
        ]
        return cls(
            tenant_id=tenant_id,
            object_kind=object_kind,
            incoming_source=incoming_source,
            accepted=not blocking_conflicts,
            changed_paths=tuple(GovernedAttributePath.from_value(path) for path in changed_paths),
            stale_rule_names=tuple(GovernanceRuleName.from_value(name) for name in stale_rule_names),
            conflicts=conflicts,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id.value,
            "object_kind": self.object_kind.value,
            "incoming_source": self.incoming_source.value,
            "accepted": self.accepted,
            "changed_paths": [path.value for path in self.changed_paths],
            "stale_rule_names": [name.value for name in self.stale_rule_names],
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
        }


@dataclass(frozen=True, slots=True)
class SourceGovernanceRulePage:
    items: tuple[SourceGovernanceRule, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


class SourceGovernanceEvaluator:
    def evaluate(
        self,
        tenant_id: TenantId,
        object_kind: SourceObjectKind,
        incoming_source: SourceSystem,
        existing_attributes: dict[str, Any],
        incoming_attributes: dict[str, Any],
        rules: tuple[SourceGovernanceRule, ...],
        observed_at: datetime | None = None,
    ) -> SourceGovernanceEvaluation:
        changed_paths = self.changed_paths(existing_attributes, incoming_attributes)
        conflicts: list[SourceGovernanceConflict] = []
        stale_rule_names: list[str] = []
        for rule in sorted(rules, key=lambda item: item.priority, reverse=True):
            if rule.is_stale(observed_at):
                stale_rule_names.append(rule.name.value)
            for changed_path in changed_paths:
                if not rule.applies_to(object_kind, changed_path):
                    continue
                if rule.is_authoritative(incoming_source):
                    continue
                conflicts.append(
                    SourceGovernanceConflict.create(
                        changed_path,
                        rule,
                        incoming_source,
                        self.value_at(existing_attributes, changed_path),
                        self.value_at(incoming_attributes, changed_path),
                    )
                )
        return SourceGovernanceEvaluation.create(
            tenant_id=tenant_id,
            object_kind=object_kind,
            incoming_source=incoming_source,
            changed_paths=changed_paths,
            stale_rule_names=tuple(sorted(set(stale_rule_names))),
            conflicts=tuple(conflicts),
        )

    def changed_paths(self, existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[str, ...]:
        paths = sorted(set(self._flatten(existing)) | set(self._flatten(incoming)))
        return tuple(path for path in paths if self.value_at(existing, path) != self.value_at(incoming, path))

    def value_at(self, payload: dict[str, Any], path: str) -> Any:
        current: Any = payload
        for segment in path.split("."):
            if not isinstance(current, dict) or segment not in current:
                return None
            current = current[segment]
        return current

    def _flatten(self, payload: dict[str, Any], prefix: str = "") -> tuple[str, ...]:
        paths: list[str] = []
        for key, value in payload.items():
            key_text = str(key).strip().lower()
            current = key_text if not prefix else prefix + "." + key_text
            paths.append(current)
            if isinstance(value, dict):
                paths.extend(self._flatten(value, current))
        return tuple(paths)
