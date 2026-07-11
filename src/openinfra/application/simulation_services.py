from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any

from openinfra.application.dependency_graph_services import (
    AnalyzeDependencyImpactCommand,
    DependencyGraphService,
)
from openinfra.application.ports import (
    AuditRepository,
    FlowMatrixRepository,
    SimulationComparisonPage,
    SimulationImpactReportPage,
    SimulationRepository,
    SimulationScenarioPage,
    SourceOfTruthRepository,
    TransactionManager,
)
from openinfra.application.security_services import AuthenticateTokenCommand, SecurityService
from openinfra.domain.common import (
    AuditEvent,
    DomainEvent,
    EntityId,
    NotFoundError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.security import AuthenticatedPrincipal, Permission
from openinfra.domain.simulation import (
    SimulationBlockingDependency,
    SimulationChange,
    SimulationChangeKind,
    SimulationImpactFinding,
    SimulationImpactReport,
    SimulationMigrationWave,
    SimulationMoveGroup,
    SimulationReadinessScore,
    SimulationScenario,
    SimulationScenarioComparison,
    SimulationScenarioStatus,
)
from openinfra.domain.source_of_truth import SourceOfTruthObject


@dataclass(frozen=True, slots=True)
class CreateSimulationScenarioCommand:
    tenant_id: str
    actor: str
    admin_token: str
    name: str
    description: str
    owner: str
    idempotency_key: str
    changes: tuple[dict[str, Any], ...]
    site: str | None = None
    environment: str | None = None
    criticality: str | None = None


@dataclass(frozen=True, slots=True)
class GetSimulationScenarioCommand:
    tenant_id: str
    admin_token: str
    scenario_id: str


@dataclass(frozen=True, slots=True)
class ListSimulationScenariosCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    status: str | None = None
    site: str | None = None


@dataclass(frozen=True, slots=True)
class RunSimulationScenarioCommand:
    tenant_id: str
    actor: str
    admin_token: str
    scenario_id: str
    max_depth: int = 8
    max_nodes: int = 2000


@dataclass(frozen=True, slots=True)
class CancelSimulationScenarioCommand:
    tenant_id: str
    actor: str
    admin_token: str
    scenario_id: str


@dataclass(frozen=True, slots=True)
class GetSimulationReportCommand:
    tenant_id: str
    admin_token: str
    report_id: str


@dataclass(frozen=True, slots=True)
class ListSimulationReportsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None
    scenario_id: str | None = None


@dataclass(frozen=True, slots=True)
class CompareSimulationReportsCommand:
    tenant_id: str
    actor: str
    admin_token: str
    left_report_id: str
    right_report_id: str


@dataclass(frozen=True, slots=True)
class ListSimulationComparisonsCommand:
    tenant_id: str
    admin_token: str
    limit: int = 100
    cursor: str | None = None


@dataclass(slots=True)
class _ImpactAggregate:
    impacted_keys: set[str]
    findings: list[SimulationImpactFinding]
    edges: list[tuple[str, str, str]]
    truncated: bool
    changed_objects: dict[str, SourceOfTruthObject | None]
    flow_codes: set[str]
    capacity_delta: dict[str, float]


class SimulationImpactEngine:
    ENGINE_VERSION = "1.0"

    def __init__(
        self,
        source_repository: SourceOfTruthRepository,
        flow_repository: FlowMatrixRepository,
        graph_service: DependencyGraphService,
    ) -> None:
        self._source_repository = source_repository
        self._flow_repository = flow_repository
        self._graph_service = graph_service

    def evaluate(
        self,
        scenario: SimulationScenario,
        admin_token: str,
        max_depth: int,
        max_nodes: int,
    ) -> SimulationImpactReport:
        aggregate = _ImpactAggregate(set(), [], [], False, {}, set(), {})
        for change in scenario.changes:
            source_object = self._validate_change_target(scenario.tenant_id, change)
            aggregate.changed_objects[change.target_key] = source_object
            self._evaluate_network_input(change, aggregate)
            self._evaluate_capacity(change, source_object, aggregate)
            if change.kind is not SimulationChangeKind.EQUIPMENT_ADD:
                self._evaluate_dependencies(
                    scenario,
                    admin_token,
                    change,
                    aggregate,
                    max_depth,
                    max_nodes,
                )
        self._evaluate_flows(scenario.tenant_id, aggregate)
        groups = self._build_move_groups(scenario, aggregate)
        blockers = self._build_blocking_dependencies(groups, aggregate.edges)
        findings = tuple(self._ordered_findings(aggregate.findings))
        readiness = self._build_readiness(scenario, findings, aggregate.truncated)
        waves = self._build_waves(groups, blockers, readiness[0].score)
        risk_before = self._baseline_risk(scenario, aggregate)
        risk_after = self._projected_risk(findings, aggregate.truncated)
        baseline_summary = self._baseline_summary(scenario, aggregate)
        projected_summary = self._projected_summary(
            scenario,
            aggregate,
            findings,
            groups,
            waves,
            blockers,
        )
        assumptions = tuple(
            sorted({assumption for change in scenario.changes for assumption in change.assumptions})
        )
        return SimulationImpactReport.create(
            tenant_id=scenario.tenant_id,
            scenario_id=scenario.id,
            scenario_version=scenario.version,
            input_sha256=scenario.input_sha256(),
            impacted_keys=tuple(aggregate.impacted_keys),
            findings=findings,
            baseline_summary=baseline_summary,
            projected_summary=projected_summary,
            capacity_delta=aggregate.capacity_delta,
            risk_before=risk_before,
            risk_after=risk_after,
            readiness_scores=readiness,
            move_groups=groups,
            waves=waves,
            blocking_dependencies=blockers,
            assumptions=assumptions,
            truncated=aggregate.truncated,
            engine_version=self.ENGINE_VERSION,
        )

    def _validate_change_target(
        self, tenant_id: TenantId, change: SimulationChange
    ) -> SourceOfTruthObject | None:
        source_object = self._source_repository.find_object(tenant_id, change.target_key)
        if change.kind is SimulationChangeKind.EQUIPMENT_ADD:
            if source_object is not None:
                raise ValidationError("equipment-add target already exists in RSOT")
            return None
        if source_object is None:
            raise NotFoundError(f"simulation target does not exist in RSOT: {change.target_key}")
        if change.before:
            for key, expected in change.before.items():
                current = source_object.attributes.get(key)
                if current != expected:
                    raise ValidationError(
                        f"simulation before state mismatch for {change.target_key}:{key}"
                    )
        return source_object

    def _evaluate_dependencies(
        self,
        scenario: SimulationScenario,
        admin_token: str,
        change: SimulationChange,
        aggregate: _ImpactAggregate,
        max_depth: int,
        max_nodes: int,
    ) -> None:
        report = self._graph_service.impact(
            AnalyzeDependencyImpactCommand(
                tenant_id=scenario.tenant_id.value,
                admin_token=admin_token,
                root_key=change.target_key,
                direction="incoming",
                max_depth=max_depth,
                max_nodes=max_nodes,
            )
        )
        impacted = tuple(node.key for node in report.impacted_nodes)
        aggregate.impacted_keys.update(impacted)
        aggregate.impacted_keys.add(change.target_key)
        aggregate.truncated = aggregate.truncated or report.truncated
        aggregate.edges.extend(
            (edge.source_key, edge.target_key, edge.relation_type) for edge in report.edges
        )
        severity = self._impact_severity(len(impacted), change.kind)
        aggregate.findings.append(
            SimulationImpactFinding.create(
                dimension="dependency",
                severity=severity.value,
                code="DEPENDENCY_IMPACT",
                message=(
                    f"Le changement {change.kind.value} sur {change.target_key} "
                    f"impacte {len(impacted)} objet(s) dépendant(s)."
                ),
                object_key=change.target_key,
                evidence={
                    "impacted_count": len(impacted),
                    "direct_count": report.direct_count,
                    "indirect_count": report.indirect_count,
                    "max_depth_reached": report.max_depth_reached,
                    "truncated": report.truncated,
                },
            )
        )
        business_count = sum(
            1
            for node in report.impacted_nodes
            if node.kind in {"application", "service", "software-service", "database"}
        )
        if business_count:
            aggregate.findings.append(
                SimulationImpactFinding.create(
                    dimension="business-service",
                    severity=("critical" if business_count >= 10 else "error"),
                    code="BUSINESS_SERVICE_IMPACT",
                    message=f"{business_count} service(s) métier sont potentiellement affectés.",
                    object_key=change.target_key,
                    evidence={"business_service_count": business_count},
                )
            )

    def _evaluate_network_input(
        self, change: SimulationChange, aggregate: _ImpactAggregate
    ) -> None:
        if change.kind is SimulationChangeKind.SUBNET_CHANGE:
            raw = change.after.get("subnet", change.after.get("prefix"))
            try:
                network = ipaddress.ip_network(str(raw), strict=False)
            except ValueError as exc:
                raise ValidationError(
                    "simulation subnet change contains an invalid prefix"
                ) from exc
            aggregate.findings.append(
                SimulationImpactFinding.create(
                    dimension="ipam",
                    severity="warning",
                    code="SUBNET_RENUMBERING",
                    message=f"Le préfixe cible {network} requiert une validation IPAM et DDI.",
                    object_key=change.target_key,
                    evidence={"target_prefix": str(network)},
                )
            )
        if change.kind in (
            SimulationChangeKind.VLAN_CHANGE,
            SimulationChangeKind.VRF_CHANGE,
            SimulationChangeKind.DNS_CHANGE,
            SimulationChangeKind.FIREWALL_CHANGE,
        ):
            aggregate.findings.append(
                SimulationImpactFinding.create(
                    dimension=(
                        "flow" if change.kind is SimulationChangeKind.FIREWALL_CHANGE else "ipam"
                    ),
                    severity="warning",
                    code="NETWORK_CONTROL_REQUIRED",
                    message=(
                        f"Le changement {change.kind.value} exige la validation des "
                        "bindings réseau, flux déclarés et dépendances DDI."
                    ),
                    object_key=change.target_key,
                    evidence={"after": change.after},
                )
            )

    def _evaluate_capacity(
        self,
        change: SimulationChange,
        source_object: SourceOfTruthObject | None,
        aggregate: _ImpactAggregate,
    ) -> None:
        before = dict(source_object.attributes) if source_object is not None else {}
        before.update(change.before)
        after = dict(before)
        after.update(change.after)
        if change.kind in (
            SimulationChangeKind.EQUIPMENT_REMOVE,
            SimulationChangeKind.EQUIPMENT_OUTAGE,
            SimulationChangeKind.PDU_OUTAGE,
        ):
            after = {}
        metrics = {
            "power-watts": ("power_watts", "power_draw_watts"),
            "cooling-kw": ("cooling_kw", "cooling_demand_kw"),
            "monthly-cost": ("monthly_cost", "cost_monthly"),
            "rack-u": ("u_height", "rack_units"),
        }
        for output_key, candidates in metrics.items():
            before_value = self._numeric_value(before, candidates)
            after_value = self._numeric_value(after, candidates)
            delta = after_value - before_value
            aggregate.capacity_delta[output_key] = (
                aggregate.capacity_delta.get(output_key, 0.0) + delta
            )
        if change.kind is SimulationChangeKind.PDU_OUTAGE:
            aggregate.findings.extend(
                (
                    SimulationImpactFinding.create(
                        dimension="energy",
                        severity="critical",
                        code="PDU_OUTAGE",
                        message="La coupure PDU supprime un chemin d'alimentation simulé.",
                        object_key=change.target_key,
                        evidence={},
                    ),
                    SimulationImpactFinding.create(
                        dimension="cooling",
                        severity="warning",
                        code="THERMAL_REEVALUATION_REQUIRED",
                        message="La coupure PDU exige une réévaluation thermique de la zone.",
                        object_key=change.target_key,
                        evidence={},
                    ),
                )
            )

    def _evaluate_flows(self, tenant_id: TenantId, aggregate: _ImpactAggregate) -> None:
        cursor: str | None = None
        while True:
            page = self._flow_repository.list_declarations(
                tenant_id,
                Pagination.from_values(500, cursor),
                include_retired=False,
            )
            for declaration in page.items:
                payload = declaration.as_dict()
                selectors = " ".join(
                    (
                        str(payload["source_selector"]),
                        str(payload["destination_selector"]),
                        str(payload["justification"]),
                    )
                ).lower()
                if any(key in selectors for key in aggregate.impacted_keys):
                    aggregate.flow_codes.add(declaration.code)
            cursor = page.next_cursor
            if cursor is None:
                break
        if aggregate.flow_codes:
            aggregate.findings.append(
                SimulationImpactFinding.create(
                    dimension="flow",
                    severity=("error" if len(aggregate.flow_codes) >= 10 else "warning"),
                    code="DECLARED_FLOW_IMPACT",
                    message=(
                        f"{len(aggregate.flow_codes)} déclaration(s) de flux référencent "
                        "des objets impactés."
                    ),
                    evidence={"flow_codes": sorted(aggregate.flow_codes)},
                )
            )

    def _build_move_groups(
        self, scenario: SimulationScenario, aggregate: _ImpactAggregate
    ) -> tuple[SimulationMoveGroup, ...]:
        buckets: dict[str, list[str]] = {}
        reasons: dict[str, set[str]] = {}
        for change in scenario.changes:
            source_object = aggregate.changed_objects[change.target_key]
            attributes = {} if source_object is None else source_object.attributes
            affinity = self._affinity(attributes, scenario.site)
            buckets.setdefault(affinity, []).append(change.target_key)
            reasons.setdefault(affinity, set()).add(f"affinité:{affinity}")
            if source_object is not None:
                reasons[affinity].add(f"type:{source_object.kind.value}")
        groups = []
        for index, affinity in enumerate(sorted(buckets), start=1):
            members = tuple(sorted(buckets[affinity]))
            risk = min(100, 20 + len(members) * 5)
            groups.append(
                SimulationMoveGroup.create(
                    name=f"Groupe {index} — {affinity}",
                    member_keys=members,
                    affinity_reasons=tuple(sorted(reasons[affinity])),
                    risk_score=risk,
                )
            )
        return tuple(groups)

    def _build_blocking_dependencies(
        self,
        groups: tuple[SimulationMoveGroup, ...],
        edges: list[tuple[str, str, str]],
    ) -> tuple[SimulationBlockingDependency, ...]:
        group_by_member = {
            member: group.id.value for group in groups for member in group.member_keys
        }
        blockers: list[SimulationBlockingDependency] = []
        seen: set[tuple[str, str, str]] = set()
        for source_key, target_key, relation_type in edges:
            source_group = group_by_member.get(source_key)
            target_group = group_by_member.get(target_key)
            if source_group is None or target_group is None or source_group == target_group:
                continue
            marker = (source_key, target_key, relation_type)
            if marker in seen:
                continue
            seen.add(marker)
            blockers.append(
                SimulationBlockingDependency.create(
                    source_key,
                    target_key,
                    relation_type,
                    "Dépendance inter-groupe à respecter dans le planning de migration.",
                )
            )
        return tuple(
            sorted(
                blockers,
                key=lambda item: (item.source_key, item.target_key, item.relation_type),
            )
        )

    def _build_readiness(
        self,
        scenario: SimulationScenario,
        findings: tuple[SimulationImpactFinding, ...],
        truncated: bool,
    ) -> tuple[SimulationReadinessScore, ...]:
        blockers = tuple(
            sorted(
                {
                    item.code
                    for item in findings
                    if item.severity in {Severity.CRITICAL, Severity.ERROR}
                }
            )
        )
        warnings = tuple(
            sorted({item.code for item in findings if item.severity is Severity.WARNING})
        )
        missing: list[str] = []
        if not any(change.assumptions for change in scenario.changes):
            missing.append("documented-assumptions")
        if truncated:
            missing.append("complete-impact-graph")
        score = 100 - len(blockers) * 20 - len(warnings) * 5 - len(missing) * 10
        result = [
            SimulationReadinessScore.create(
                "scenario",
                scenario.id.value,
                max(0, score),
                blockers,
                warnings,
                tuple(missing),
            )
        ]
        for change in scenario.changes:
            scoped_blockers = tuple(
                sorted(
                    {
                        item.code
                        for item in findings
                        if item.object_key == change.target_key
                        and item.severity in {Severity.CRITICAL, Severity.ERROR}
                    }
                )
            )
            scoped_warnings = tuple(
                sorted(
                    {
                        item.code
                        for item in findings
                        if item.object_key == change.target_key
                        and item.severity is Severity.WARNING
                    }
                )
            )
            scoped_score = max(0, 100 - len(scoped_blockers) * 25 - len(scoped_warnings) * 5)
            result.append(
                SimulationReadinessScore.create(
                    "asset",
                    change.target_key,
                    scoped_score,
                    scoped_blockers,
                    scoped_warnings,
                    (),
                )
            )
        return tuple(result)

    def _build_waves(
        self,
        groups: tuple[SimulationMoveGroup, ...],
        blockers: tuple[SimulationBlockingDependency, ...],
        readiness_score: int,
    ) -> tuple[SimulationMigrationWave, ...]:
        if not groups:
            return ()
        group_by_member = {member: group.id for group in groups for member in group.member_keys}
        incoming: dict[str, set[str]] = {group.id.value: set() for group in groups}
        outgoing: dict[str, set[str]] = {group.id.value: set() for group in groups}
        for blocker in blockers:
            source = group_by_member[blocker.source_key].value
            target = group_by_member[blocker.target_key].value
            if source == target:
                continue
            outgoing[source].add(target)
            incoming[target].add(source)
        remaining = {group.id.value for group in groups}
        waves: list[SimulationMigrationWave] = []
        number = 1
        while remaining:
            ready = tuple(
                sorted(group_id for group_id in remaining if not incoming[group_id] & remaining)
            )
            cyclic = False
            if not ready:
                ready = tuple(sorted(remaining))
                cyclic = True
            blocked_by = tuple(
                EntityId.from_value(group_id)
                for group_id in sorted(
                    {
                        dependency
                        for group_id in ready
                        for dependency in incoming[group_id]
                        if dependency in remaining and dependency not in ready
                    }
                )
            )
            waves.append(
                SimulationMigrationWave.create(
                    number=number,
                    group_ids=tuple(EntityId.from_value(group_id) for group_id in ready),
                    blocked_by_group_ids=blocked_by,
                    readiness_score=max(0, readiness_score - (20 if cyclic else 0)),
                )
            )
            remaining.difference_update(ready)
            number += 1
        return tuple(waves)

    @staticmethod
    def _impact_severity(count: int, kind: SimulationChangeKind) -> Severity:
        if kind in {SimulationChangeKind.PDU_OUTAGE, SimulationChangeKind.EQUIPMENT_OUTAGE}:
            return Severity.CRITICAL if count else Severity.ERROR
        if count >= 50:
            return Severity.CRITICAL
        if count >= 10:
            return Severity.ERROR
        if count:
            return Severity.WARNING
        return Severity.INFO

    @staticmethod
    def _numeric_value(values: dict[str, Any], candidates: tuple[str, ...]) -> float:
        for key in candidates:
            raw = values.get(key)
            if raw is None:
                continue
            try:
                return float(raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"simulation numeric attribute is invalid: {key}") from exc
        return 0.0

    @staticmethod
    def _affinity(attributes: dict[str, Any], fallback_site: str | None) -> str:
        for key in ("application", "service", "business_service", "site", "vrf", "subnet", "rack"):
            value = attributes.get(key)
            if value not in (None, ""):
                return str(value).strip().lower().replace(" ", "-")[:64]
        return fallback_site or "unclassified"

    @staticmethod
    def _ordered_findings(
        findings: list[SimulationImpactFinding],
    ) -> list[SimulationImpactFinding]:
        priority = {Severity.CRITICAL: 0, Severity.ERROR: 1, Severity.WARNING: 2, Severity.INFO: 3}
        return sorted(
            findings,
            key=lambda item: (
                priority[item.severity],
                item.dimension.value,
                item.code,
                item.object_key or "",
            ),
        )

    @staticmethod
    def _baseline_risk(scenario: SimulationScenario, aggregate: _ImpactAggregate) -> int:
        base = 10 + len(scenario.changes) * 2
        if any(item is None for item in aggregate.changed_objects.values()):
            base += 5
        return min(100, base)

    @staticmethod
    def _projected_risk(findings: tuple[SimulationImpactFinding, ...], truncated: bool) -> int:
        weights = {
            Severity.INFO: 1,
            Severity.WARNING: 5,
            Severity.ERROR: 15,
            Severity.CRITICAL: 25,
        }
        score = sum(weights[item.severity] for item in findings)
        return min(100, score + (20 if truncated else 0))

    @staticmethod
    def _baseline_summary(
        scenario: SimulationScenario, aggregate: _ImpactAggregate
    ) -> dict[str, Any]:
        return {
            "scenario_status": scenario.status.value,
            "change_count": len(scenario.changes),
            "existing_target_count": sum(
                1 for item in aggregate.changed_objects.values() if item is not None
            ),
            "declared_flow_count": len(aggregate.flow_codes),
            "production_snapshot_fingerprint": scenario.input_sha256(),
        }

    @staticmethod
    def _projected_summary(
        scenario: SimulationScenario,
        aggregate: _ImpactAggregate,
        findings: tuple[SimulationImpactFinding, ...],
        groups: tuple[SimulationMoveGroup, ...],
        waves: tuple[SimulationMigrationWave, ...],
        blockers: tuple[SimulationBlockingDependency, ...],
    ) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        by_dimension: dict[str, int] = {}
        for item in findings:
            by_severity[item.severity.value] = by_severity.get(item.severity.value, 0) + 1
            by_dimension[item.dimension.value] = by_dimension.get(item.dimension.value, 0) + 1
        return {
            "scenario_id": scenario.id.value,
            "impacted_count": len(aggregate.impacted_keys),
            "finding_count": len(findings),
            "findings_by_severity": by_severity,
            "findings_by_dimension": by_dimension,
            "move_group_count": len(groups),
            "migration_wave_count": len(waves),
            "blocking_dependency_count": len(blockers),
            "truncated": aggregate.truncated,
            "production_mutation": False,
        }


class SimulationService:
    def __init__(
        self,
        repository: SimulationRepository,
        audit_repository: AuditRepository,
        transaction_manager: TransactionManager,
        security_service: SecurityService,
        impact_engine: SimulationImpactEngine,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._transaction_manager = transaction_manager
        self._security_service = security_service
        self._impact_engine = impact_engine

    def create_scenario(self, command: CreateSimulationScenarioCommand) -> SimulationScenario:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_WRITE
        )
        existing = self._repository.find_scenario_by_idempotency_key(
            tenant_id, command.idempotency_key
        )
        if existing is not None:
            return existing
        changes = tuple(self._change_from_payload(item) for item in command.changes)
        scenario = SimulationScenario.create(
            tenant_id=tenant_id,
            name=command.name,
            description=command.description,
            owner=command.owner,
            idempotency_key=command.idempotency_key,
            changes=changes,
            site=command.site,
            environment=command.environment,
            criticality=command.criticality,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_scenario(scenario)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    scenario.id,
                    "simulation.scenario.created",
                    {"scenario_id": scenario.id.value, "change_count": len(changes)},
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or subject.subject,
                    "simulation.scenario.created",
                    "simulation_scenario",
                    scenario.id.value,
                    metadata={
                        "old_state": None,
                        "new_state": scenario.as_dict(),
                        "correlation": scenario.idempotency_key,
                        "source": "api",
                    },
                )
            )
            unit_of_work.commit()
        return scenario

    def get_scenario(self, command: GetSimulationScenarioCommand) -> SimulationScenario:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_READ
        )
        scenario = self._repository.get_scenario(tenant_id, command.scenario_id)
        if scenario is None:
            raise NotFoundError("simulation scenario does not exist")
        return scenario

    def list_scenarios(self, command: ListSimulationScenariosCommand) -> SimulationScenarioPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_READ
        )
        return self._repository.list_scenarios(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.status,
            command.site,
        )

    def run_scenario(self, command: RunSimulationScenarioCommand) -> SimulationImpactReport:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_EXECUTE
        )
        scenario = self._required_scenario(tenant_id, command.scenario_id)
        latest = self._repository.find_latest_report(tenant_id, scenario.id.value)
        if (
            scenario.status is SimulationScenarioStatus.COMPLETED
            and latest is not None
            and latest.input_sha256 == scenario.input_sha256()
        ):
            return latest
        running = scenario.started()
        self._save_transition(
            scenario,
            running,
            command.actor or subject.subject,
            "simulation.started",
        )
        try:
            report = self._impact_engine.evaluate(
                running,
                command.admin_token,
                command.max_depth,
                command.max_nodes,
            )
        except Exception as exc:
            failed = running.failed(str(exc))
            self._save_transition(
                running,
                failed,
                command.actor or subject.subject,
                "simulation.failed",
                severity=Severity.ERROR,
            )
            raise
        completed = running.completed()
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_report(report)
            self._repository.save_scenario(completed)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    scenario.id,
                    "simulation.completed",
                    {
                        "scenario_id": scenario.id.value,
                        "report_id": report.id.value,
                        "risk_after": report.risk_after,
                        "readiness": report.readiness_scores[0].score,
                    },
                )
            )
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    scenario.id,
                    "impact.report.generated",
                    {
                        "scenario_id": scenario.id.value,
                        "report_id": report.id.value,
                        "impacted_count": len(report.impacted_keys),
                    },
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or subject.subject,
                    "simulation.completed",
                    "simulation_scenario",
                    scenario.id.value,
                    metadata={
                        "old_state": running.as_dict(),
                        "new_state": completed.as_dict(),
                        "report_id": report.id.value,
                        "input_sha256": report.input_sha256,
                        "source": "simulation-engine",
                    },
                )
            )
            unit_of_work.commit()
        return report

    def cancel_scenario(self, command: CancelSimulationScenarioCommand) -> SimulationScenario:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_WRITE
        )
        current = self._required_scenario(tenant_id, command.scenario_id)
        cancelled = current.cancelled()
        self._save_transition(
            current,
            cancelled,
            command.actor or subject.subject,
            "simulation.cancelled",
        )
        return cancelled

    def get_report(self, command: GetSimulationReportCommand) -> SimulationImpactReport:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_READ
        )
        report = self._repository.get_report(tenant_id, command.report_id)
        if report is None:
            raise NotFoundError("simulation impact report does not exist")
        return report

    def list_reports(self, command: ListSimulationReportsCommand) -> SimulationImpactReportPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_READ
        )
        return self._repository.list_reports(
            tenant_id,
            Pagination.from_values(command.limit, command.cursor),
            command.scenario_id,
        )

    def compare_reports(
        self, command: CompareSimulationReportsCommand
    ) -> SimulationScenarioComparison:
        tenant_id, subject = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_WRITE
        )
        left = self._repository.get_report(tenant_id, command.left_report_id)
        right = self._repository.get_report(tenant_id, command.right_report_id)
        if left is None or right is None:
            raise NotFoundError("one or both simulation reports do not exist")
        preferred = self._preferred_report(left, right)
        comparison = SimulationScenarioComparison.create(
            tenant_id,
            left.id,
            right.id,
            summary={
                "risk_delta": right.risk_after - left.risk_after,
                "readiness_delta": (
                    right.readiness_scores[0].score - left.readiness_scores[0].score
                ),
                "impacted_count_delta": len(right.impacted_keys) - len(left.impacted_keys),
                "finding_count_delta": len(right.findings) - len(left.findings),
                "capacity_delta_difference": self._capacity_difference(left, right),
                "left_truncated": left.truncated,
                "right_truncated": right.truncated,
            },
            preferred_report_id=preferred.id if preferred is not None else None,
        )
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_comparison(comparison)
            self._repository.append_event(
                DomainEvent.create(
                    tenant_id,
                    comparison.id,
                    "simulation.comparison.created",
                    comparison.as_dict(),
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    tenant_id,
                    command.actor or subject.subject,
                    "simulation.comparison.created",
                    "simulation_comparison",
                    comparison.id.value,
                    metadata=comparison.as_dict(),
                )
            )
            unit_of_work.commit()
        return comparison

    def list_comparisons(
        self, command: ListSimulationComparisonsCommand
    ) -> SimulationComparisonPage:
        tenant_id, _ = self._authorize(
            command.tenant_id, command.admin_token, Permission.SIMULATION_READ
        )
        return self._repository.list_comparisons(
            tenant_id, Pagination.from_values(command.limit, command.cursor)
        )

    def _save_transition(
        self,
        old: SimulationScenario,
        new: SimulationScenario,
        actor: str,
        event_name: str,
        severity: Severity = Severity.INFO,
    ) -> None:
        with self._transaction_manager.begin() as unit_of_work:
            self._repository.save_scenario(new)
            self._repository.append_event(
                DomainEvent.create(
                    new.tenant_id,
                    new.id,
                    event_name,
                    {"scenario_id": new.id.value, "status": new.status.value},
                )
            )
            self._audit_repository.append(
                AuditEvent.record(
                    new.tenant_id,
                    actor,
                    event_name,
                    "simulation_scenario",
                    new.id.value,
                    metadata={
                        "old_state": old.as_dict(),
                        "new_state": new.as_dict(),
                        "source": "simulation-service",
                    },
                    severity=severity,
                )
            )
            unit_of_work.commit()

    def _required_scenario(self, tenant_id: TenantId, scenario_id: str) -> SimulationScenario:
        scenario = self._repository.get_scenario(tenant_id, scenario_id)
        if scenario is None:
            raise NotFoundError("simulation scenario does not exist")
        return scenario

    def _authorize(
        self, tenant_id: str, token: str, permission: Permission
    ) -> tuple[TenantId, AuthenticatedPrincipal]:
        normalized_tenant = TenantId.from_value(tenant_id)
        principal = self._security_service.authenticate_token(
            AuthenticateTokenCommand(normalized_tenant.value, token, permission)
        )
        return normalized_tenant, principal

    @staticmethod
    def _change_from_payload(payload: dict[str, Any]) -> SimulationChange:
        if not isinstance(payload, dict):
            raise ValidationError("simulation change must be a JSON object")
        return SimulationChange.create(
            kind=str(payload.get("kind", "")),
            target_key=str(payload.get("target_key", "")),
            before=dict(payload.get("before") or {}),
            after=dict(payload.get("after") or {}),
            assumptions=tuple(str(item) for item in payload.get("assumptions", ())),
        )

    @staticmethod
    def _preferred_report(
        left: SimulationImpactReport, right: SimulationImpactReport
    ) -> SimulationImpactReport | None:
        left_key = (
            left.truncated,
            left.risk_after,
            -left.readiness_scores[0].score,
            len(left.impacted_keys),
        )
        right_key = (
            right.truncated,
            right.risk_after,
            -right.readiness_scores[0].score,
            len(right.impacted_keys),
        )
        if left_key == right_key:
            return None
        return left if left_key < right_key else right

    @staticmethod
    def _capacity_difference(
        left: SimulationImpactReport, right: SimulationImpactReport
    ) -> dict[str, float]:
        keys = set(left.capacity_delta) | set(right.capacity_delta)
        return {
            key: right.capacity_delta.get(key, 0.0) - left.capacity_delta.get(key, 0.0)
            for key in sorted(keys)
        }
