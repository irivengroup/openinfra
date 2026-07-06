from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from openinfra.application.ports import (
    AuditRepository,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.audit import AuditEventFilter, AuditEventPage
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    Pagination,
    TenantId,
    ValidationError,
)
from openinfra.domain.security import Permission
from openinfra.domain.resource_taxonomy import ResourceClassification, ResourceTaxonomy
from openinfra.domain.source_governance import (
    SourceConflictStrategy,
    SourceGovernanceEvaluation,
    SourceGovernanceEvaluator,
)
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
    resource_category: str | None = None
    resource_type: str | None = None


@dataclass(frozen=True, slots=True)
class ReconcileSourceObjectCommand:
    tenant_id: str
    actor: str
    admin_token: str
    key: str
    attributes_json: str
    source: str
    display_name: str | None = None
    tags: tuple[str, ...] | None = None
    apply: bool = False
    resource_category: str | None = None
    resource_type: str | None = None


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
    resource_type: str | None = None


@dataclass(frozen=True, slots=True)
class GetSourceObjectVersionCommand:
    tenant_id: str
    admin_token: str
    key: str
    version: int


@dataclass(frozen=True, slots=True)
class GetSourceObjectAsOfCommand:
    tenant_id: str
    admin_token: str
    key: str
    as_of: str | datetime


@dataclass(frozen=True, slots=True)
class ListSourceObjectAuditCommand:
    tenant_id: str
    admin_token: str
    key: str
    limit: int = 100
    cursor: str | None = None


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
    as_of: str | datetime | None = None


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
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_WRITE)
        )
        attributes = self._attributes_from_json(command.attributes_json)
        classification = self._classify_resource(
            kind=command.kind,
            resource_category=command.resource_category,
            resource_type=command.resource_type,
            attributes=attributes,
        )
        attributes = self._attributes_with_classification(attributes, classification)
        stored_kind = self._stored_kind(command.kind, command.resource_category, classification)
        SourceObjectKind(stored_kind)
        SourceSystem.from_value(command.source)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_object(tenant_id, command.key)
            if existing is None:
                source_object = self._repository.create_object(
                    tenant_id=tenant_id,
                    key=command.key,
                    kind=stored_kind,
                    display_name=command.display_name,
                    attributes=attributes,
                    tags=command.tags,
                    source=command.source,
                    actor=command.actor,
                )
                action = "itrm.object.create"
            else:
                self._enforce_governance(tenant_id, existing, attributes, command.source)
                source_object = existing.revise(
                    display_name=command.display_name,
                    attributes=attributes,
                    tags=command.tags,
                    source=command.source,
                    kind=stored_kind,
                )
                self._repository.upsert_object(source_object, command.actor)
                action = "itrm.object.update"
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
                        "resource_category": source_object.as_dict()["resource_category"],
                        "resource_type": source_object.as_dict()["resource_type"],
                        "tags": [tag.value for tag in source_object.tags],
                        "declared_actor": command.actor,
                    },
                )
            )
            unit_of_work.commit()
        return source_object.as_dict()

    def reconcile_object(self, command: ReconcileSourceObjectCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_WRITE)
        )
        incoming_attributes = self._attributes_from_json(command.attributes_json)
        incoming_source = SourceSystem.from_value(command.source)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_object(tenant_id, command.key)
            if existing is None:
                raise NotFoundError("source object not found: " + command.key)
            classification = self._classify_resource(
                kind=existing.kind.value,
                resource_category=command.resource_category,
                resource_type=command.resource_type,
                attributes=incoming_attributes,
            )
            incoming_attributes = self._attributes_with_classification(
                incoming_attributes, classification
            )
            evaluation = self._evaluate_governance(
                tenant_id,
                existing,
                incoming_attributes,
                incoming_source.value,
            )
            changed_paths = [path.value for path in evaluation.changed_paths]
            stale_rule_names = [name.value for name in evaluation.stale_rule_names]
            conflicts = [conflict.as_dict() for conflict in evaluation.conflicts]
            result: dict[str, object] = {
                "tenant_id": tenant_id.value,
                "key": existing.key.value,
                "kind": existing.kind.value,
                "resource_category": classification.category,
                "resource_type": classification.resource_type,
                "incoming_source": incoming_source.value,
                "accepted": evaluation.accepted,
                "apply_requested": bool(command.apply),
                "applied": False,
                "current_version": existing.version,
                "planned_version": (
                    existing.version + 1 if evaluation.accepted else existing.version
                ),
                "changed_paths": changed_paths,
                "stale_rule_names": stale_rule_names,
                "conflicts": conflicts,
                "result_attributes": (
                    incoming_attributes if evaluation.accepted else existing.attributes
                ),
            }
            action = "itrm.reconciliation.plan"
            if command.apply and evaluation.accepted:
                revised = existing.revise(
                    display_name=command.display_name,
                    attributes=incoming_attributes,
                    tags=command.tags,
                    source=incoming_source.value,
                    kind=(
                        classification.category
                        if command.resource_category
                        else existing.kind.value
                    ),
                )
                self._repository.upsert_object(revised, command.actor)
                result.update(
                    {
                        "applied": True,
                        "version": revised.version,
                        "object": revised.as_dict(),
                    }
                )
                action = "itrm.reconciliation.apply"
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action=action,
                    target_type="source_object",
                    target_id=existing.key.value,
                    metadata={
                        "declared_actor": command.actor,
                        "incoming_source": incoming_source.value,
                        "accepted": evaluation.accepted,
                        "apply_requested": bool(command.apply),
                        "applied": bool(result["applied"]),
                        "changed_paths": changed_paths,
                        "conflict_count": len(conflicts),
                    },
                )
            )
            unit_of_work.commit()
        return result

    def get_object(self, command: GetSourceObjectCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
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
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        kind = SourceObjectKind(str(command.kind).strip().lower()) if command.kind else None
        resource_type = None
        if command.resource_type:
            resource_type = ResourceTaxonomy.normalize_token(command.resource_type, "resource type")
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._repository.list_objects(
                tenant_id=tenant_id,
                pagination=pagination,
                kind=kind.value if kind else None,
                tag=command.tag,
                resource_type=resource_type,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=principal.subject,
                    action="itrm.object.list",
                    target_type="source_object",
                    target_id=tenant_id.value,
                    metadata={
                        "limit": pagination.limit,
                        "kind": kind.value if kind else None,
                        "resource_type": resource_type,
                    },
                )
            )
            unit_of_work.commit()
        return page

    def get_object_version(self, command: GetSourceObjectVersionCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
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

    def get_object_as_of(self, command: GetSourceObjectAsOfCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        as_of = self._datetime_from_value(command.as_of, "as_of")
        with self._transaction_manager.begin() as unit_of_work:
            snapshot = self._repository.find_object_as_of(tenant_id, command.key, as_of)
            if snapshot is None:
                raise NotFoundError("source object snapshot not found at requested date")
            unit_of_work.commit()
        result = dict(snapshot.payload)
        result["as_of"] = as_of.isoformat()
        result["resolved_version"] = snapshot.version
        result["snapshot_changed_at"] = snapshot.changed_at.isoformat()
        return result

    def list_object_audit(self, command: ListSourceObjectAuditCommand) -> AuditEventPage:
        tenant_id = TenantId.from_value(command.tenant_id)
        self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        normalized_key = command.key.strip().lower()
        if not normalized_key:
            raise ValidationError("source object key is mandatory")
        event_filter = AuditEventFilter.create(
            tenant_id=tenant_id,
            pagination=Pagination.from_values(command.limit, command.cursor),
            target_type="source_object",
            target_id=normalized_key,
        )
        with self._transaction_manager.begin() as unit_of_work:
            page = self._audit_repository.list_records(event_filter)
            unit_of_work.commit()
        return page

    def create_relation(self, command: CreateSourceRelationCommand) -> dict[str, object]:
        tenant_id = TenantId.from_value(command.tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_WRITE)
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
                    action="itrm.relation.create",
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
            AuthenticateTokenCommand(tenant_id.value, command.admin_token, Permission.ITRM_READ)
        )
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            page = self._repository.list_relations(
                tenant_id=tenant_id,
                pagination=pagination,
                source_key=command.source_key,
                target_key=command.target_key,
                relation_type=command.relation_type,
                as_of=self._datetime_from_value(command.as_of, "as_of")
                if command.as_of is not None
                else None,
            )
            unit_of_work.commit()
        return page

    def _datetime_from_value(self, value: str | datetime, label: str) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            normalized = value.strip()
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise ValidationError(label + " must be an ISO-8601 datetime") from exc
        if parsed.tzinfo is None:
            raise ValidationError(label + " must be timezone-aware")
        return parsed.astimezone(UTC)

    def _attributes_from_json(self, payload: str) -> dict[str, object]:
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValidationError("attributes must be valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValidationError("attributes must be a JSON object")
        return dict(decoded)

    def _classify_resource(
        self,
        *,
        kind: str | None,
        resource_category: str | None,
        resource_type: str | None,
        attributes: dict[str, object],
    ) -> ResourceClassification:
        return ResourceTaxonomy.classify(
            kind=kind,
            resource_category=resource_category,
            resource_type=resource_type,
            attributes=attributes,
        )

    def _stored_kind(
        self,
        requested_kind: str,
        requested_category: str | None,
        classification: ResourceClassification,
    ) -> str:
        normalized_kind = requested_kind.strip().lower().replace("_", "-")
        if requested_category is None and normalized_kind in ResourceTaxonomy.LEGACY_KIND_MAP:
            return normalized_kind
        return classification.category

    def _attributes_with_classification(
        self, attributes: dict[str, object], classification: ResourceClassification
    ) -> dict[str, object]:
        enriched = dict(attributes)
        enriched["resource_category"] = classification.category
        enriched["resource_type"] = classification.resource_type
        return enriched

    def resource_taxonomy(self) -> dict[str, object]:
        return ResourceTaxonomy.as_dict()

    def _evaluate_governance(
        self,
        tenant_id: TenantId,
        existing: SourceOfTruthObject,
        incoming_attributes: dict[str, object],
        incoming_source: str,
    ) -> SourceGovernanceEvaluation:
        rules = (
            self._governance_repository.find_active_rules_for_kind(tenant_id, existing.kind.value)
            if self._governance_repository is not None
            else ()
        )
        return self._governance_evaluator.evaluate(
            tenant_id=tenant_id,
            object_kind=existing.kind,
            incoming_source=SourceSystem.from_value(incoming_source),
            existing_attributes=existing.attributes,
            incoming_attributes=incoming_attributes,
            rules=rules,
        )

    def _enforce_governance(
        self,
        tenant_id: TenantId,
        existing: SourceOfTruthObject,
        incoming_attributes: dict[str, object],
        incoming_source: str,
    ) -> None:
        evaluation = self._evaluate_governance(
            tenant_id,
            existing,
            incoming_attributes,
            incoming_source,
        )
        blocking = [
            conflict
            for conflict in evaluation.conflicts
            if conflict.strategy == SourceConflictStrategy.REJECT
        ]
        if blocking:
            paths = ", ".join(conflict.attribute_path.value for conflict in blocking)
            raise ConflictError("source governance rejected non-authoritative overwrite: " + paths)
