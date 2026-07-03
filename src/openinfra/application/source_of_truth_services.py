from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from openinfra.application.ports import (
    AuditRepository,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.domain.security import Permission
from openinfra.domain.source_governance import SourceConflictStrategy, SourceGovernanceEvaluator
from openinfra.domain.source_of_truth import (
    SourceObjectKind,
    SourceObjectPage,
    SourceOfTruthObject,
    SourceRelation,
    SourceRelationPage,
    SourceSystem,
)


@dataclass(frozen=True, slots=True)
class UpsertSourceObjectCommand:
    tenant_id: str
    actor: str
    admin_token: str
    key: str
    kind: str
    display_name: str
    attributes_json: str
    tags: tuple[str, ...]
    source: str


@dataclass(frozen=True, slots=True)
class GetSourceObjectCommand:
    tenant_id: str
    admin_token: str
    key: str


@dataclass(frozen=True, slots=True)
class ListSourceObjectsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    kind: str | None = None
    tag: str | None = None


@dataclass(frozen=True, slots=True)
class GetSourceObjectVersionCommand:
    tenant_id: str
    admin_token: str
    key: str
    version: int


@dataclass(frozen=True, slots=True)
class CreateSourceRelationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    relation_type: str
    source_key: str
    target_key: str
    provenance: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None


@dataclass(frozen=True, slots=True)
class ListSourceRelationsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    source_key: str | None = None
    target_key: str | None = None
    relation_type: str | None = None


class SourceOfTruthService:
    def __init__(
        self,
        repository: SourceOfTruthRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        governance_repository: SourceGovernanceRepository | None = None,
        governance_evaluator: SourceGovernanceEvaluator | None = None,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._governance_repository = governance_repository
        self._governance_evaluator = governance_evaluator or SourceGovernanceEvaluator()

    def upsert_object(self, command: UpsertSourceObjectCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_WRITE)
        )
        attributes = self._attributes_from_json(command.attributes_json)
        SourceObjectKind(str(command.kind).strip().lower())
        SourceSystem.from_value(command.source)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_object(tenant_id, command.key)
            if existing is None:
                source_object = self._repository.create_object(
                    tenant_id=tenant_id,
                    key=command.key,
                    kind=command.kind,
                    display_name=command.display_name,
                    attributes=attributes,
                    tags=command.tags,
                    source=command.source,
                    actor=command.actor,
                )
                action = "sot.object.create"
            else:
                self._enforce_governance(tenant_id, existing, attributes, command.source)
                source_object = existing.revise(
                    display_name=command.display_name,
                    attributes=attributes,
                    tags=command.tags,
                    source=command.source,
                )
                self._repository.upsert_object(source_object, command.actor)
                action = "sot.object.update"
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action=action,
                    target_type="source_object",
                    target_id=source_object.key.value,
                    metadata={
                        "version": source_object.version,
                        "kind": source_object.kind.value,
                        "tags": [tag.value for tag in source_object.tags],
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return source_object.as_dict()

    def get_object(self, command: GetSourceObjectCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_READ)
        )
        with self._transaction_manager.begin() as unit_of_work:
            source_object = self._repository.find_object(tenant_id, command.key)
            if source_object is None:
                raise NotFoundError("source object not found: " + command.key)
            unit_of_work.commit()
        return source_object.as_dict()

    def list_objects(self, command: ListSourceObjectsCommand) -> SourceObjectPage:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_READ)
        )
        kind = SourceObjectKind(str(command.kind).strip().lower()) if command.kind else None
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._repository.list_objects(
                tenant_id=tenant_id,
                pagination=pagination,
                kind=kind.value if kind else None,
                tag=command.tag,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="sot.object.list",
                    target_type="source_object",
                    target_id=tenant_id.value,
                    metadata={"limit": pagination.limit, "kind": kind.value if kind else None},
                )
            )
            unit_of_work.commit()
        return page

    def get_object_version(self, command: GetSourceObjectVersionCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_READ)
        )
        if int(command.version) < 1:
            raise ValidationError("source object version must be positive")
        with self._transaction_manager.begin() as unit_of_work:
            snapshot = self._repository.find_object_version(
                tenant_id,
                command.key,
                int(command.version),
            )
            if snapshot is None:
                raise NotFoundError("source object version not found")
            unit_of_work.commit()
        return snapshot.as_dict()

    def create_relation(self, command: CreateSourceRelationCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_WRITE)
        )
        with self._transaction_manager.begin() as unit_of_work:
            if self._repository.find_object(tenant_id, command.source_key) is None:
                raise NotFoundError("relation source object not found: " + command.source_key)
            if self._repository.find_object(tenant_id, command.target_key) is None:
                raise NotFoundError("relation target object not found: " + command.target_key)
            relation = SourceRelation.create(
                tenant_id=tenant_id,
                relation_type=command.relation_type,
                source_key=command.source_key,
                target_key=command.target_key,
                provenance=command.provenance,
                valid_from=command.valid_from,
                valid_to=command.valid_to,
            )
            self._repository.add_relation(relation)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="sot.relation.create",
                    target_type="source_relation",
                    target_id=relation.id.value,
                    metadata={
                        "relation_type": relation.relation_type.value,
                        "source_key": relation.source_key.value,
                        "target_key": relation.target_key.value,
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return relation.as_dict()

    def list_relations(self, command: ListSourceRelationsCommand) -> SourceRelationPage:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.SOT_READ)
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._repository.list_relations(
                tenant_id=tenant_id,
                pagination=pagination,
                source_key=command.source_key,
                target_key=command.target_key,
                relation_type=command.relation_type,
            )
            unit_of_work.commit()
        return page

    def _attributes_from_json(self, payload: str) -> dict[str, object]:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError("attributes must be valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValidationError("attributes must be a JSON object")
        return dict(decoded)

    def _enforce_governance(
        self,
        tenant_id: TenantId,
        existing: SourceOfTruthObject,
        incoming_attributes: dict[str, object],
        incoming_source: str,
    ) -> None:
        if self._governance_repository is None:
            return
        rules = self._governance_repository.find_active_rules_for_kind(
            tenant_id,
            existing.kind.value,
        )
        if not rules:
            return
        evaluation = self._governance_evaluator.evaluate(
            tenant_id=tenant_id,
            object_kind=existing.kind,
            incoming_source=SourceSystem.from_value(incoming_source),
            existing_attributes=existing.attributes,
            incoming_attributes=incoming_attributes,
            rules=rules,
        )
        blocking = [
            conflict for conflict in evaluation.conflicts
            if conflict.strategy == SourceConflictStrategy.REJECT
        ]
        if blocking:
            paths = ", ".join(conflict.attribute_path.value for conflict in blocking)
            raise ConflictError("source governance rejected non-authoritative overwrite: " + paths)

