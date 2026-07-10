from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from openinfra.application.ports import (
    AuditRepository,
    FlowDeclarationPage,
    FlowMatrixRepository,
    FlowObservationPage,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    ConflictError,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.flow_matrix import (
    FlowComplianceStatus,
    FlowDecision,
    FlowDeclaration,
    FlowDeclarationStatus,
    FlowMatrixReport,
    FlowMatrixRow,
    FlowObservation,
    FlowObservationSource,
)
from openinfra.domain.security import Permission


@dataclass(frozen=True, slots=True)
class UpsertFlowDeclarationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    code: str
    source_selector: str
    destination_selector: str
    protocol: str
    destination_port_start: int | None
    destination_port_end: int | None
    decision: str
    priority: int
    owner: str
    justification: str
    valid_from: str | datetime | None = None
    valid_to: str | datetime | None = None


@dataclass(frozen=True, slots=True)
class RetireFlowDeclarationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    declaration_id: str


@dataclass(frozen=True, slots=True)
class ListFlowDeclarationsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    include_retired: bool = False


@dataclass(frozen=True, slots=True)
class SubmitFlowObservationCommand:
    tenant_id: str
    actor: str
    admin_token: str
    idempotency_key: str
    source: str
    collector: str
    source_ip: str
    destination_ip: str
    source_object_key: str | None
    destination_object_key: str | None
    protocol: str
    destination_port: int | None
    packets: int
    bytes_count: int
    first_seen: str | datetime
    last_seen: str | datetime


@dataclass(frozen=True, slots=True)
class ListFlowObservationsCommand:
    tenant_id: str
    admin_token: str
    window_start: str | datetime
    window_end: str | datetime
    limit: int = 100
    cursor: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class CompareFlowMatrixCommand:
    tenant_id: str
    admin_token: str
    window_start: str | datetime | None = None
    window_end: str | datetime | None = None
    limit: int = 100
    cursor: str | None = None
    status: str | None = None
    source: str | None = None


class FlowMatrixService:
    _PAGE_SIZE = 500
    _MAX_DECLARATIONS = 5000
    _MAX_OBSERVATIONS = 10_000
    _MAX_WINDOW = timedelta(days=31)

    def __init__(
        self,
        repository: FlowMatrixRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service

    def upsert_declaration(self, command: UpsertFlowDeclarationCommand) -> FlowDeclaration:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.FLOW_WRITE
        )
        actor = self._actor(command.actor, subject)
        valid_from = self._datetime(command.valid_from) or datetime.now(UTC)
        valid_to = self._datetime(command.valid_to)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_declaration_by_code(tenant_id, command.code)
            if existing is None:
                declaration = FlowDeclaration.create(
                    tenant_id=tenant_id,
                    code=command.code,
                    source_selector=command.source_selector,
                    destination_selector=command.destination_selector,
                    protocol=command.protocol,
                    destination_port_start=command.destination_port_start,
                    destination_port_end=command.destination_port_end,
                    decision=command.decision,
                    priority=command.priority,
                    owner=command.owner,
                    justification=command.justification,
                    actor=actor,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
                action = "flow.declaration.create"
            else:
                declaration = existing.revise(
                    source_selector=command.source_selector,
                    destination_selector=command.destination_selector,
                    protocol=command.protocol,
                    destination_port_start=command.destination_port_start,
                    destination_port_end=command.destination_port_end,
                    decision=command.decision,
                    priority=command.priority,
                    owner=command.owner,
                    justification=command.justification,
                    actor=actor,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
                action = "flow.declaration.update"
            self._repository.save_declaration(declaration)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action=action,
                    target_type="flow_declaration",
                    target_id=declaration.id.value,
                    metadata={
                        "code": declaration.code,
                        "decision": declaration.decision.value,
                        "protocol": declaration.protocol.value,
                        "version": declaration.version,
                    },
                )
            )
            unit_of_work.commit()
        return declaration

    def retire_declaration(self, command: RetireFlowDeclarationCommand) -> FlowDeclaration:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.FLOW_WRITE
        )
        actor = self._actor(command.actor, subject)
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.get_declaration(tenant_id, command.declaration_id)
            if existing is None:
                raise NotFoundError("flow declaration not found")
            declaration = existing.retire(actor)
            self._repository.save_declaration(declaration)
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="flow.declaration.retire",
                    target_type="flow_declaration",
                    target_id=declaration.id.value,
                    metadata={"code": declaration.code, "version": declaration.version},
                )
            )
            unit_of_work.commit()
        return declaration

    def list_declarations(self, command: ListFlowDeclarationsCommand) -> FlowDeclarationPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.FLOW_READ)
        return self._repository.list_declarations(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            include_retired=command.include_retired,
        )

    def submit_observation(self, command: SubmitFlowObservationCommand) -> FlowObservation:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.FLOW_WRITE
        )
        actor = self._actor(command.actor, subject)
        observation = FlowObservation.create(
            tenant_id=tenant_id,
            idempotency_key=command.idempotency_key,
            source=command.source,
            collector=command.collector,
            source_ip=command.source_ip,
            destination_ip=command.destination_ip,
            source_object_key=command.source_object_key,
            destination_object_key=command.destination_object_key,
            protocol=command.protocol,
            destination_port=command.destination_port,
            packets=command.packets,
            bytes_count=command.bytes_count,
            first_seen=self._required_datetime(command.first_seen, "first_seen"),
            last_seen=self._required_datetime(command.last_seen, "last_seen"),
        )
        with self._transaction_manager.begin() as unit_of_work:
            existing = self._repository.find_observation_by_idempotency_key(
                tenant_id, observation.idempotency_key
            )
            if existing is not None:
                if existing.fingerprint != observation.fingerprint:
                    raise ConflictError(
                        "flow observation idempotency key already exists with a different payload"
                    )
                unit_of_work.commit()
                return existing
            self._repository.save_observation(observation)
            persisted = self._repository.find_observation_by_idempotency_key(
                tenant_id, observation.idempotency_key
            )
            if persisted is None:
                raise ConflictError("flow observation could not be persisted")
            if persisted.fingerprint != observation.fingerprint:
                raise ConflictError(
                    "flow observation idempotency key already exists with a different payload"
                )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=actor,
                    action="flow.observation.ingest",
                    target_type="flow_observation",
                    target_id=persisted.id.value,
                    metadata={
                        "source": persisted.source.value,
                        "collector": persisted.collector,
                        "protocol": persisted.protocol.value,
                        "packets": persisted.packets,
                        "bytes": persisted.bytes_count,
                    },
                )
            )
            unit_of_work.commit()
        return persisted

    def list_observations(self, command: ListFlowObservationsCommand) -> FlowObservationPage:
        tenant_id, _ = self._authorize(command.tenant_id, command.admin_token, Permission.FLOW_READ)
        start, end = self._window(command.window_start, command.window_end)
        source = self._source(command.source)
        return self._repository.list_observations(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            start,
            end,
            source,
        )

    def compare(self, command: CompareFlowMatrixCommand) -> FlowMatrixReport:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.FLOW_READ
        )
        end = self._datetime(command.window_end) or datetime.now(UTC)
        start = self._datetime(command.window_start) or (end - timedelta(hours=24))
        start, end = self._window(start, end)
        status_filter = self._status(command.status)
        source = self._source(command.source)
        pagination = Pagination.from_values(command.limit, command.cursor)
        with self._transaction_manager.begin() as unit_of_work:
            declarations, declarations_truncated = self._all_declarations(tenant_id)
            observations, observations_truncated = self._all_observations(
                tenant_id, start, end, source
            )
            effective = tuple(
                item
                for item in declarations
                if item.status is FlowDeclarationStatus.ACTIVE
                and item.valid_from < end
                and (item.valid_to is None or item.valid_to > start)
            )
            rows, matched_declarations = self._classify(observations, effective)
            rows.extend(self._orphan_rows(effective, matched_declarations))
            rows.sort(key=self._row_sort_key)
            totals: dict[str, int] = {status.value: 0 for status in FlowComplianceStatus}
            for row in rows:
                totals[row.status.value] += 1
            filtered = (
                rows
                if status_filter is None
                else [row for row in rows if row.status is status_filter]
            )
            offset = self._offset(pagination.cursor)
            selected = tuple(filtered[offset : offset + pagination.limit])
            next_index = offset + len(selected)
            next_cursor = str(next_index) if next_index < len(filtered) else None
            report = FlowMatrixReport(
                window_start=start,
                window_end=end,
                rows=selected,
                totals=totals,
                packets=sum(item.packets for item in observations),
                bytes_count=sum(item.bytes_count for item in observations),
                observation_count=len(observations),
                declaration_count=len(effective),
                next_cursor=next_cursor,
                truncated=declarations_truncated or observations_truncated,
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id=tenant_id,
                    actor=subject,
                    action="flow.matrix.compare",
                    target_type="flow_matrix",
                    target_id=f"{start.isoformat()}..{end.isoformat()}",
                    metadata={
                        "declarations": len(effective),
                        "observations": len(observations),
                        "totals": totals,
                        "status_filter": status_filter.value if status_filter else None,
                        "source_filter": source,
                        "truncated": report.truncated,
                    },
                    severity=(
                        Severity.WARNING
                        if totals[FlowComplianceStatus.DENIED_OBSERVED.value]
                        or totals[FlowComplianceStatus.UNDECLARED_OBSERVED.value]
                        else Severity.INFO
                    ),
                )
            )
            unit_of_work.commit()
        return report

    def _all_declarations(self, tenant_id: TenantId) -> tuple[tuple[FlowDeclaration, ...], bool]:
        items: list[FlowDeclaration] = []
        cursor: str | None = None
        seen: set[str] = set()
        while len(items) < self._MAX_DECLARATIONS:
            page = self._repository.list_declarations(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_DECLARATIONS - len(items)), cursor
                ),
                include_retired=False,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items), False
            if page.next_cursor in seen:
                raise ValidationError("flow declaration repository returned a cyclic cursor")
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        return tuple(items), cursor is not None

    def _all_observations(
        self,
        tenant_id: TenantId,
        start: datetime,
        end: datetime,
        source: str | None,
    ) -> tuple[tuple[FlowObservation, ...], bool]:
        items: list[FlowObservation] = []
        cursor: str | None = None
        seen: set[str] = set()
        while len(items) < self._MAX_OBSERVATIONS:
            page = self._repository.list_observations(
                tenant_id,
                Pagination.from_values(
                    min(self._PAGE_SIZE, self._MAX_OBSERVATIONS - len(items)), cursor
                ),
                start,
                end,
                source,
            )
            items.extend(page.items)
            if page.next_cursor is None:
                return tuple(items), False
            if page.next_cursor in seen:
                raise ValidationError("flow observation repository returned a cyclic cursor")
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        return tuple(items), cursor is not None

    @staticmethod
    def _classify(
        observations: tuple[FlowObservation, ...],
        declarations: tuple[FlowDeclaration, ...],
    ) -> tuple[list[FlowMatrixRow], set[str]]:
        rows: list[FlowMatrixRow] = []
        matched_declarations: set[str] = set()
        for observation in observations:
            candidates = [item for item in declarations if item.matches(observation)]
            candidates.sort(
                key=lambda item: (
                    -item.match_score[0],
                    -item.match_score[1],
                    -item.match_score[2],
                    -item.match_score[3],
                    item.code,
                )
            )
            if not candidates:
                rows.append(
                    FlowMatrixRow(
                        FlowComplianceStatus.UNDECLARED_OBSERVED,
                        observation,
                        None,
                        "no effective declaration matches this observed flow",
                    )
                )
                continue
            declaration = candidates[0]
            matched_declarations.add(declaration.id.value)
            if declaration.decision is FlowDecision.DENY:
                rows.append(
                    FlowMatrixRow(
                        FlowComplianceStatus.DENIED_OBSERVED,
                        observation,
                        declaration,
                        "observed flow matches an explicit deny declaration",
                    )
                )
            else:
                rows.append(
                    FlowMatrixRow(
                        FlowComplianceStatus.COMPLIANT,
                        observation,
                        declaration,
                        "observed flow matches the highest-priority allow declaration",
                    )
                )
        return rows, matched_declarations

    @staticmethod
    def _orphan_rows(
        declarations: tuple[FlowDeclaration, ...], matched_declarations: set[str]
    ) -> list[FlowMatrixRow]:
        return [
            FlowMatrixRow(
                FlowComplianceStatus.DECLARED_UNOBSERVED,
                None,
                declaration,
                "allow declaration has no matching observation in the selected window",
            )
            for declaration in declarations
            if declaration.decision is FlowDecision.ALLOW
            and declaration.id.value not in matched_declarations
        ]

    @staticmethod
    def _row_sort_key(row: FlowMatrixRow) -> tuple[int, str, str]:
        rank = {
            FlowComplianceStatus.DENIED_OBSERVED: 0,
            FlowComplianceStatus.UNDECLARED_OBSERVED: 1,
            FlowComplianceStatus.DECLARED_UNOBSERVED: 2,
            FlowComplianceStatus.COMPLIANT: 3,
        }
        declaration_code = row.declaration.code if row.declaration else ""
        observation_id = row.observation.id.value if row.observation else ""
        return rank[row.status], declaration_code, observation_id

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

    @classmethod
    def _window(
        cls, start_value: str | datetime, end_value: str | datetime
    ) -> tuple[datetime, datetime]:
        start = cls._required_datetime(start_value, "window_start")
        end = cls._required_datetime(end_value, "window_end")
        if end <= start:
            raise ValidationError("flow matrix window_end must be after window_start")
        if end - start > cls._MAX_WINDOW:
            raise ValidationError("flow matrix window cannot exceed 31 days")
        if end > datetime.now(UTC) + timedelta(minutes=5):
            raise ValidationError("flow matrix window_end cannot be in the future")
        return start, end

    @staticmethod
    def _datetime(value: str | datetime | None) -> datetime | None:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError("datetime value must use ISO-8601 syntax") from exc
        if parsed.tzinfo is None:
            raise ValidationError("datetime value must be timezone-aware")
        return parsed.astimezone(UTC)

    @classmethod
    def _required_datetime(cls, value: str | datetime, field_name: str) -> datetime:
        parsed = cls._datetime(value)
        if parsed is None:
            raise ValidationError(field_name + " is mandatory")
        return parsed

    @staticmethod
    def _source(value: str | None) -> str | None:
        return (
            None
            if value is None or value.strip() == ""
            else FlowObservationSource.from_value(value).value
        )

    @staticmethod
    def _status(value: str | None) -> FlowComplianceStatus | None:
        if value is None or value.strip() == "":
            return None
        try:
            return FlowComplianceStatus(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("flow matrix status filter is unsupported") from exc

    @staticmethod
    def _offset(cursor: str | None) -> int:
        try:
            offset = int(cursor or "0")
        except ValueError as exc:
            raise ValidationError("pagination cursor must be a numeric offset") from exc
        if offset < 0:
            raise ValidationError("pagination cursor must be positive")
        return offset
