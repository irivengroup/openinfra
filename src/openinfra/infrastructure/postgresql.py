from __future__ import annotations

import hashlib
import importlib
import ipaddress
import json
import os
import re
import secrets
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar, Protocol, Self, cast

from openinfra.application.ports import (
    AccessPolicyRepository,
    AccessPolicyRulePage,
    AsyncJobPage,
    AsyncProcessingRepository,
    AuditRepository,
    CapacityForecastPage,
    CarbonFactorPage,
    CertificateAssetPage,
    CertificateEndpointPage,
    CertificateInventoryRepository,
    ConsolidationCandidatePage,
    CostAllocationRulePage,
    CostAnomalyPage,
    CostImportJobPage,
    CostRecordPage,
    DcimRepository,
    DisasterRecoveryDrillPage,
    DisasterRecoveryPlanPage,
    DiscoveryCollectorPage,
    DiscoveryEvidencePage,
    DiscoveryIntegrationProfilePage,
    DiscoveryJobClaimResult,
    DiscoveryJobPage,
    DiscoveryProtocolProfilePage,
    DiscoveryReconciliationCasePage,
    DiscoveryRepository,
    EnergyAnomalyPage,
    EnergyMeasurementPage,
    ExportRepository,
    ExposureContextPage,
    FieldOperationRepository,
    FieldOperationSheetPage,
    FinancialPeriodPage,
    FinOpsBudgetPage,
    FinOpsForecastPage,
    FinOpsReportPage,
    FinOpsRepository,
    FlowDeclarationPage,
    FlowMatrixRepository,
    FlowObservationPage,
    GreenOpsRepository,
    GreenScorePage,
    IdentityRepository,
    ImportRepository,
    IpamRepository,
    ItamSupportRepository,
    KubernetesGitOpsRepository,
    KubernetesGitOpsStatePage,
    KubernetesTopologyRepository,
    KubernetesTopologySnapshotPage,
    MeasurementSourcePage,
    MultisiteReportPage,
    MultisiteRepository,
    NetworkConfigBaselinePage,
    NetworkConfigComplianceRepository,
    NetworkConfigObservationPage,
    OfflineSyncPackagePage,
    OutboxEventPage,
    RagRepository,
    ReadinessProbe,
    ReadinessStatus,
    RegionalDiscoveryRoutePage,
    RiskFindingPage,
    RuntimeUsageRepository,
    SbomComparisonPage,
    SbomDocumentPage,
    SbomRepository,
    SchemaStatusProvider,
    SecurityRepository,
    SecurityTokenPage,
    SimulationComparisonPage,
    SimulationImpactReportPage,
    SimulationRepository,
    SimulationScenarioPage,
    SiteAccessGrantPage,
    SourceGovernanceRepository,
    SourceOfTruthRepository,
    SustainabilityReportPage,
    TransactionManager,
    UnitOfWork,
    VulnerabilityRecordPage,
)
from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.async_processing import (
    ArtifactReference,
    AsyncJob,
    LeasedWorkState,
    OutboxEvent,
    WorkerSpecialization,
    WorkStatus,
)
from openinfra.domain.audit import (
    AuditEventFilter,
    AuditEventPage,
    AuditEventRecord,
    AuditIntegrityHasher,
    AuditIntegrityReport,
)
from openinfra.domain.certificate_pki import (
    CertificateAsset,
    CertificateEndpointObservation,
    CertificateMaterial,
)
from openinfra.domain.common import (
    AuditEvent,
    Code,
    ConflictError,
    Coordinates3D,
    DomainEvent,
    EntityId,
    Name,
    OpenInfraError,
    Pagination,
    Severity,
    TenantId,
    ValidationError,
)
from openinfra.domain.data_export import ExportJob
from openinfra.domain.data_import import (
    BulkImportCheckpoint,
    BulkImportMetrics,
    BulkImportReport,
    ImportFormat,
    ImportJobStatus,
    ImportMapping,
    ImportReport,
    ImportRowImpact,
    ImportRowIssue,
    LegacyMigrationSource,
    MigrationGap,
    MigrationPlanReport,
    MigrationTemplate,
)
from openinfra.domain.dcim import (
    Building,
    BuildingType,
    CoolingRole,
    CoolingZone,
    DcimCable,
    DcimCableMedium,
    DcimCablePathSegment,
    DcimCableStatus,
    DcimConnectorType,
    DcimLifecycleStatus,
    DcimPort,
    DcimPortEndpoint,
    DcimPortOwnerType,
    Equipment,
    EquipmentLocation,
    Floor,
    FloorNomenclature,
    PatchPanel,
    PowerCircuit,
    PowerDevice,
    PowerDeviceKind,
    PowerFeedSide,
    Rack,
    RackFace,
    RackPowerReservation,
    Room,
    RoomZone,
    Site,
)
from openinfra.domain.discovery import (
    DiscoveryCollector,
    DiscoveryEvidence,
    DiscoveryIntegrationProfile,
    DiscoveryProtocolCredentialProfile,
    DiscoveryReconciliationCase,
    DiscoveryReconciliationStatus,
)
from openinfra.domain.discovery_jobs import DiscoveryJob, DiscoveryJobStatus
from openinfra.domain.editions import QuotaResource
from openinfra.domain.field_operations import (
    FieldEvidence,
    FieldOperationSheet,
    InterventionLock,
    OfflineSyncPackage,
)
from openinfra.domain.finops import (
    CostAllocationRule,
    CostAnomaly,
    CostImportJob,
    CostRecord,
    FinancialPeriod,
    FinOpsBudget,
    FinOpsForecast,
    FinOpsReport,
)
from openinfra.domain.flow_matrix import (
    FlowDeclaration,
    FlowObservation,
)
from openinfra.domain.greenops import (
    CapacityForecast,
    CarbonFactor,
    ConsolidationCandidate,
    EnergyAnomaly,
    EnergyMeasurement,
    GreenOpsPolicy,
    GreenScore,
    MeasurementSource,
    SustainabilityReport,
)
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityGroupName,
    IdentityRoleSet,
    IdentitySubject,
    IdentityUser,
)
from openinfra.domain.ipam import (
    AutonomousSystem,
    BgpAddressFamily,
    BgpPeer,
    IpAddressRecord,
    IpAggregate,
    IpRange,
    IpReservation,
    ObservedDhcpLease,
    ObservedDnsRecord,
    Prefix,
    Vlan,
    VlanGroup,
    Vrf,
    VxlanVni,
)
from openinfra.domain.itam import (
    ItamDateParser,
    ItamOrganization,
    ItamPartner,
    ItamTenant,
    ManufacturerWarranty,
    PhysicalAssetSupportProfile,
    SoftwareLicenseEntitlement,
    ThirdPartySupportContract,
)
from openinfra.domain.kubernetes_gitops import KubernetesGitOpsState
from openinfra.domain.kubernetes_topology import KubernetesTopologySnapshot
from openinfra.domain.multisite import (
    DisasterRecoveryDrillStatus,
    MultisiteDisasterRecoveryDrill,
    MultisiteDisasterRecoveryPlan,
    MultisitePortfolioReport,
    RegionalDiscoveryRoute,
    SiteAccessGrant,
    SitePortfolioEntry,
)
from openinfra.domain.network_config_compliance import (
    NetworkConfigBaseline,
    NetworkConfigObservation,
)
from openinfra.domain.rag import (
    RagAnswer,
    RagAnswerPage,
    RagArtifact,
    RagDocument,
    RagDocumentPage,
    RagJobPage,
    RagSearchCandidate,
    RagSearchResult,
    RagTransferJob,
)
from openinfra.domain.sbom import (
    ExposureContext,
    RiskFinding,
    SbomComparison,
    SbomDocument,
    VulnerabilityRecord,
)
from openinfra.domain.security import ApiTokenCredential, Permission
from openinfra.domain.simulation import (
    SimulationImpactReport,
    SimulationScenario,
    SimulationScenarioComparison,
)
from openinfra.domain.source_governance import SourceGovernanceRule, SourceGovernanceRulePage
from openinfra.domain.source_of_truth import (
    SourceObjectPage,
    SourceObjectSnapshot,
    SourceOfTruthObject,
    SourceRelation,
    SourceRelationPage,
)
from openinfra.infrastructure.cursor_pagination import (
    CursorDirection,
    CursorField,
    CursorTokenCodec,
    CursorValueType,
    PostgreSQLKeysetPage,
)
from openinfra.infrastructure.field_operation_mapper import FieldOperationRecordMapper
from openinfra.infrastructure.finops_mapper import FinOpsRecordMapper
from openinfra.infrastructure.greenops_mapper import GreenOpsRecordMapper
from openinfra.infrastructure.kubernetes_gitops_mapper import KubernetesGitOpsRecordMapper
from openinfra.infrastructure.kubernetes_topology_mapper import KubernetesTopologyRecordMapper
from openinfra.infrastructure.rag_mapper import RagRecordMapper
from openinfra.infrastructure.read_routing import (
    PostgreSQLReadRoutingSettings,
    PostgreSQLReplicaHealth,
    ReadRoute,
    ReadRoutingContext,
)
from openinfra.infrastructure.sbom_mapper import SbomRecordMapper
from openinfra.infrastructure.simulation_mapper import SimulationRecordMapper


class CursorProtocol(Protocol):
    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        raise TypeError("adapter contract invoked directly")

    def fetchone(self) -> Mapping[str, object] | None:
        raise TypeError("adapter contract invoked directly")

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        raise TypeError("adapter contract invoked directly")

    def close(self) -> object:
        raise TypeError("adapter contract invoked directly")


class ConnectionProtocol(Protocol):
    def cursor(self) -> CursorProtocol:
        raise TypeError("adapter contract invoked directly")

    def commit(self) -> object:
        raise TypeError("adapter contract invoked directly")

    def rollback(self) -> object:
        raise TypeError("adapter contract invoked directly")

    def close(self) -> object:
        raise TypeError("adapter contract invoked directly")


@dataclass(frozen=True, slots=True)
class PostgreSQLClusterProfile:
    application_name: str
    statement_timeout_ms: int
    lock_timeout_ms: int
    read_only_replica_allowed: bool

    @classmethod
    def production_default(cls) -> Self:
        return cls(
            application_name="openinfra-api",
            statement_timeout_ms=30_000,
            lock_timeout_ms=5_000,
            read_only_replica_allowed=True,
        )

    def dsn_options(self) -> str:
        return (
            f"application_name={self.application_name} "
            f"statement_timeout={self.statement_timeout_ms} "
            f"lock_timeout={self.lock_timeout_ms}"
        )


class PostgreSQLPartitionConstraintValidator:
    _SQL_IDENTIFIER_RE: ClassVar[str] = r"[a-zA-Z_][a-zA-Z0-9_]*"

    @classmethod
    def validate(cls, sql: str) -> None:
        partitioned_tables: dict[str, tuple[str, ...]] = {}
        for statement in PostgreSQLStatementSplitter.split(sql):
            create_match = re.search(
                rf"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+({cls._SQL_IDENTIFIER_RE})\b",
                statement,
                re.I,
            )
            if create_match is not None and " PARTITION OF " not in statement.upper():
                table_name = create_match.group(1).lower()
                partition_columns = cls._partition_columns(statement)
                if partition_columns:
                    partitioned_tables[table_name] = partition_columns
                    opening_index = statement.find("(", create_match.end())
                    table_body = cls._matching_parenthesized_value(statement, opening_index)
                    for item in cls._split_top_level_csv(table_body):
                        for unique_columns in cls._inline_unique_constraint_columns(item):
                            missing = set(partition_columns) - set(unique_columns)
                            if missing:
                                raise ValidationError(
                                    "partitioned table unique constraint must include "
                                    f"partition columns: {table_name} missing {sorted(missing)}"
                                )
                continue

            index_match = re.search(
                rf"\bCREATE\s+UNIQUE\s+INDEX\b.+?\bON\s+({cls._SQL_IDENTIFIER_RE})\s+(?:USING\s+{cls._SQL_IDENTIFIER_RE}\s+)?\(",
                statement,
                re.I | re.S,
            )
            if index_match is None:
                continue
            table_name = index_match.group(1).lower()
            index_partition_columns = partitioned_tables.get(table_name)
            if not index_partition_columns:
                continue
            opening_index = statement.find("(", index_match.end() - 1)
            index_columns = cls._column_identifiers(
                cls._matching_parenthesized_value(statement, opening_index)
            )
            missing = set(index_partition_columns) - set(index_columns)
            if missing:
                raise ValidationError(
                    "partitioned table unique index must include partition columns: "
                    f"{table_name} missing {sorted(missing)}"
                )

    @classmethod
    def _matching_parenthesized_value(cls, sql: str, opening_index: int) -> str:
        if opening_index < 0 or opening_index >= len(sql) or sql[opening_index] != "(":
            raise ValidationError("invalid SQL parenthesized expression")
        depth = 0
        start = opening_index + 1
        for index, character in enumerate(sql[opening_index:], start=opening_index):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    return sql[start:index]
        raise ValidationError("unbalanced SQL parenthesized expression")

    @classmethod
    def _split_top_level_csv(cls, payload: str) -> tuple[str, ...]:
        parts: list[str] = []
        buffer: list[str] = []
        depth = 0
        for character in payload:
            if character == "(":
                depth += 1
            elif character == ")" and depth > 0:
                depth -= 1
            if character == "," and depth == 0:
                part = "".join(buffer).strip()
                if part:
                    parts.append(part)
                buffer = []
                continue
            buffer.append(character)
        trailing = "".join(buffer).strip()
        if trailing:
            parts.append(trailing)
        return tuple(parts)

    @classmethod
    def _column_identifiers(cls, payload: str) -> tuple[str, ...]:
        columns: list[str] = []
        for expression in cls._split_top_level_csv(payload):
            normalized = re.sub(
                r"\s+(ASC|DESC|NULLS\s+(FIRST|LAST))\b", "", expression, flags=re.I
            ).strip()
            if re.fullmatch(cls._SQL_IDENTIFIER_RE, normalized):
                columns.append(normalized.lower())
        return tuple(columns)

    @classmethod
    def _partition_columns(cls, statement: str) -> tuple[str, ...]:
        match = re.search(r"\bPARTITION\s+BY\s+(?:HASH|RANGE|LIST)\s*\(", statement, re.I)
        if match is None:
            return ()
        opening_index = statement.find("(", match.end() - 1)
        return cls._column_identifiers(cls._matching_parenthesized_value(statement, opening_index))

    @classmethod
    def _inline_unique_constraint_columns(cls, table_item: str) -> tuple[tuple[str, ...], ...]:
        upper = table_item.upper()
        columns: list[tuple[str, ...]] = []
        for marker in ("PRIMARY KEY", "UNIQUE"):
            marker_index = upper.find(marker)
            if marker_index == -1:
                continue
            opening_index = table_item.find("(", marker_index)
            columns.append(
                cls._column_identifiers(
                    cls._matching_parenthesized_value(table_item, opening_index)
                )
            )
        return tuple(columns)


@dataclass(frozen=True, slots=True)
class PostgreSQLMigration:
    name: str
    path: Path
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        if not self.name.endswith(".sql"):
            raise ValidationError("migration name must end with .sql")
        normalized = self.sql.upper()
        has_schema_change = any(
            marker in normalized
            for marker in ("CREATE TABLE", "ALTER TABLE", "CREATE INDEX", "CREATE EXTENSION")
        )
        if not has_schema_change:
            raise ValidationError("migration must contain a controlled schema change")
        if "CREATE TABLE" in normalized and "PARTITION BY" not in normalized:
            raise ValidationError("table-creating migrations must define partitioning")
        if "CREATE INDEX" not in normalized:
            raise ValidationError("migration must create or maintain indexes")
        if "AUDIT_EVENTS" not in normalized:
            raise ValidationError("migration must include audit persistence or audit indexes")
        PostgreSQLPartitionConstraintValidator.validate(self.sql)

    def as_dict(self) -> dict[str, object]:
        return {"version": self.name, "checksum": self.checksum}


class PostgreSQLMigrationCatalog:
    def __init__(self, root: Path) -> None:
        self._root = root

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> Self:
        root = project_root or Path.cwd()
        return cls(root / "installers" / "migrations" / "postgresql")

    def load(self, name: str) -> PostgreSQLMigration:
        safe_name = self._sanitize_name(name)
        path = self._root / safe_name
        if not path.is_file():
            raise ValidationError(f"migration not found: {safe_name}")
        migration = PostgreSQLMigration(
            name=safe_name,
            path=path,
            sql=path.read_text(encoding="utf-8"),
        )
        migration.validate()
        return migration

    def list_names(self) -> tuple[str, ...]:
        return tuple(sorted(path.name for path in self._root.glob("*.sql") if path.is_file()))

    def _sanitize_name(self, name: str) -> str:
        normalized = name.strip()
        if not normalized.endswith(".sql"):
            normalized = f"{normalized}.sql"
        if "/" in normalized or "\\" in normalized or normalized.startswith("."):
            raise ValidationError("unsafe migration name")
        return normalized


@dataclass(frozen=True, slots=True)
class PostgreSQLAppliedMigration:
    version: str
    checksum: str
    applied_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "checksum": self.checksum,
            "applied_at": self.applied_at,
        }


@dataclass(frozen=True, slots=True)
class PostgreSQLSchemaStatus:
    ready: bool
    applied: tuple[PostgreSQLAppliedMigration, ...]
    pending: tuple[PostgreSQLMigration, ...]
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "backend": "postgresql",
            "managed": True,
            "ready": self.ready,
            "detail": self.detail,
            "applied": [item.as_dict() for item in self.applied],
            "pending": [item.as_dict() for item in self.pending],
        }


class PostgreSQLMigrationExecutor(SchemaStatusProvider):
    _HISTORY_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS openinfra_schema_migrations (
        version text PRIMARY KEY,
        checksum text NOT NULL,
        applied_at timestamptz NOT NULL DEFAULT now()
    )
    """

    def __init__(
        self,
        registry: PostgreSQLSessionRegistry,
        catalog: PostgreSQLMigrationCatalog,
    ) -> None:
        self._registry = registry
        self._catalog = catalog

    def status(self) -> PostgreSQLSchemaStatus:
        connection = self._registry.open()
        cursor = connection.cursor()
        try:
            self._ensure_history_table(cursor)
            applied = self._load_applied(cursor)
            pending = self._pending_migrations(applied)
            connection.rollback()
            detail = (
                "postgresql schema is up to date"
                if not pending
                else "postgresql schema has pending migrations"
            )
            return PostgreSQLSchemaStatus(not pending, tuple(applied.values()), pending, detail)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            self._registry.release(connection)

    def status_as_dict(self) -> dict[str, object]:
        return self.status().as_dict()

    def apply_all(self, dry_run: bool = False) -> PostgreSQLSchemaStatus:
        connection = self._registry.open()
        cursor = connection.cursor()
        try:
            self._ensure_history_table(cursor)
            applied = self._load_applied(cursor)
            pending = self._pending_migrations(applied)
            if dry_run:
                connection.rollback()
                detail = "dry run completed; no migration was applied"
                return PostgreSQLSchemaStatus(not pending, tuple(applied.values()), pending, detail)
            for migration in pending:
                for statement in self._transactional_statements(migration):
                    cursor.execute(statement)
                cursor.execute(
                    """
                    INSERT INTO openinfra_schema_migrations (version, checksum)
                    VALUES (%(version)s, %(checksum)s)
                    ON CONFLICT (version) DO UPDATE SET
                        checksum = EXCLUDED.checksum,
                        applied_at = now()
                    """,
                    {"version": migration.name, "checksum": migration.checksum},
                )
            connection.commit()
            refreshed = self._load_applied(cursor)
            detail = (
                "postgresql schema migrations applied"
                if pending
                else "postgresql schema was already up to date"
            )
            return PostgreSQLSchemaStatus(True, tuple(refreshed.values()), (), detail)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            self._registry.release(connection)

    def _transactional_sql(self, migration: PostgreSQLMigration) -> str:
        return "\n".join(self._transactional_statements(migration)).strip() + "\n"

    def _transactional_statements(self, migration: PostgreSQLMigration) -> tuple[str, ...]:
        retained_lines: list[str] = []
        for line in migration.sql.splitlines():
            normalized = line.strip().upper()
            if normalized in {"BEGIN;", "COMMIT;"}:
                continue
            retained_lines.append(line)
        return PostgreSQLStatementSplitter.split("\n".join(retained_lines))

    def _ensure_history_table(self, cursor: CursorProtocol) -> None:
        cursor.execute(self._HISTORY_TABLE_SQL)

    def _load_applied(self, cursor: CursorProtocol) -> dict[str, PostgreSQLAppliedMigration]:
        cursor.execute(
            """
            SELECT version, checksum, applied_at
            FROM openinfra_schema_migrations
            ORDER BY version
            """
        )
        applied: dict[str, PostgreSQLAppliedMigration] = {}
        for row in cursor.fetchall():
            applied[str(row["version"])] = PostgreSQLAppliedMigration(
                version=str(row["version"]),
                checksum=str(row["checksum"]),
                applied_at=str(row["applied_at"]),
            )
        return applied

    def _pending_migrations(
        self,
        applied: Mapping[str, PostgreSQLAppliedMigration],
    ) -> tuple[PostgreSQLMigration, ...]:
        pending: list[PostgreSQLMigration] = []
        for name in self._catalog.list_names():
            migration = self._catalog.load(name)
            applied_migration = applied.get(migration.name)
            if applied_migration is None:
                pending.append(migration)
                continue
            if applied_migration.checksum != migration.checksum:
                raise ValidationError("applied migration checksum mismatch: " + migration.name)
        return tuple(pending)


class PostgreSQLStatementSplitter:
    @classmethod
    def split(cls, sql: str) -> tuple[str, ...]:
        statements: list[str] = []
        buffer: list[str] = []
        index = 0
        single_quoted = False
        double_quoted = False
        line_comment = False
        block_comment_depth = 0
        dollar_quote_tag: str | None = None
        while index < len(sql):
            character = sql[index]
            next_character = sql[index + 1] if index + 1 < len(sql) else ""

            if line_comment:
                buffer.append(character)
                if character == "\n":
                    line_comment = False
                index += 1
                continue

            if block_comment_depth:
                buffer.append(character)
                if character == "/" and next_character == "*":
                    buffer.append(next_character)
                    block_comment_depth += 1
                    index += 2
                    continue
                if character == "*" and next_character == "/":
                    buffer.append(next_character)
                    block_comment_depth -= 1
                    index += 2
                    continue
                index += 1
                continue

            if dollar_quote_tag is not None:
                if sql.startswith(dollar_quote_tag, index):
                    buffer.append(dollar_quote_tag)
                    index += len(dollar_quote_tag)
                    dollar_quote_tag = None
                    continue
                buffer.append(character)
                index += 1
                continue

            if single_quoted:
                buffer.append(character)
                if character == "'":
                    if next_character == "'":
                        buffer.append(next_character)
                        index += 2
                        continue
                    single_quoted = False
                index += 1
                continue

            if double_quoted:
                buffer.append(character)
                if character == '"':
                    if next_character == '"':
                        buffer.append(next_character)
                        index += 2
                        continue
                    double_quoted = False
                index += 1
                continue

            if character == "-" and next_character == "-":
                buffer.append(character)
                buffer.append(next_character)
                line_comment = True
                index += 2
                continue
            if character == "/" and next_character == "*":
                buffer.append(character)
                buffer.append(next_character)
                block_comment_depth = 1
                index += 2
                continue
            if character == "'":
                buffer.append(character)
                single_quoted = True
                index += 1
                continue
            if character == '"':
                buffer.append(character)
                double_quoted = True
                index += 1
                continue
            tag = cls._dollar_quote_tag(sql, index)
            if tag is not None:
                buffer.append(tag)
                dollar_quote_tag = tag
                index += len(tag)
                continue
            if character == ";":
                buffer.append(character)
                statement = "".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
                index += 1
                continue
            buffer.append(character)
            index += 1

        trailing = "".join(buffer).strip()
        if trailing:
            statements.append(trailing)
        return tuple(statements)

    @staticmethod
    def _dollar_quote_tag(sql: str, index: int) -> str | None:
        if sql[index] != "$":
            return None
        closing_index = sql.find("$", index + 1)
        if closing_index == -1:
            return None
        tag_body = sql[index + 1 : closing_index]
        if tag_body and not (tag_body[0].isalpha() or tag_body[0] == "_"):
            return None
        for character in tag_body:
            if not (character.isalnum() or character == "_"):
                return None
        return sql[index : closing_index + 1]


@dataclass(frozen=True, slots=True)
class PostgreSQLConnectionPoolSettings:
    min_size: int
    max_size: int
    timeout_seconds: float
    max_idle_seconds: float
    max_lifetime_seconds: float
    worker_count: int = 1
    connection_budget: int = 120

    def __post_init__(self) -> None:
        if self.min_size < 0:
            raise ValidationError("postgresql pool min_size cannot be negative")
        if self.max_size <= 0:
            raise ValidationError("postgresql pool max_size must be positive")
        if self.min_size > self.max_size:
            raise ValidationError("postgresql pool min_size cannot exceed max_size")
        if self.timeout_seconds <= 0:
            raise ValidationError("postgresql pool timeout must be positive")
        if self.max_idle_seconds <= 0 or self.max_lifetime_seconds <= 0:
            raise ValidationError("postgresql pool lifetime values must be positive")
        if self.worker_count <= 0:
            raise ValidationError("postgresql pool worker_count must be positive")
        if self.connection_budget <= 0:
            raise ValidationError("postgresql connection budget must be positive")
        if self.max_size * self.worker_count > self.connection_budget:
            raise ValidationError(
                "postgresql pool capacity exceeds the configured process connection budget"
            )

    @classmethod
    def from_environment(cls, edition: str, worker_count: int) -> Self:
        normalized = edition.strip().lower()
        defaults = {
            "lite": (1, 4, 20),
            "pro": (1, 8, 80),
            "enterprise": (2, 12, 192),
        }
        if normalized not in defaults:
            raise ValidationError("edition must be lite, pro or enterprise")
        default_min, default_max, default_budget = defaults[normalized]
        return cls(
            min_size=int(os.environ.get("OPENINFRA_DB_POOL_MIN_SIZE", str(default_min))),
            max_size=int(os.environ.get("OPENINFRA_DB_POOL_MAX_SIZE", str(default_max))),
            timeout_seconds=float(os.environ.get("OPENINFRA_DB_POOL_TIMEOUT_SECONDS", "5")),
            max_idle_seconds=float(os.environ.get("OPENINFRA_DB_POOL_MAX_IDLE_SECONDS", "300")),
            max_lifetime_seconds=float(
                os.environ.get("OPENINFRA_DB_POOL_MAX_LIFETIME_SECONDS", "1800")
            ),
            worker_count=worker_count,
            connection_budget=int(
                os.environ.get("OPENINFRA_DB_CONNECTION_BUDGET", str(default_budget))
            ),
        )


class PostgreSQLConnectionPool:
    def __init__(
        self,
        dsn: str,
        profile: PostgreSQLClusterProfile,
        settings: PostgreSQLConnectionPoolSettings,
    ) -> None:
        try:
            pool_module = importlib.import_module("psycopg_pool")
            rows = importlib.import_module("psycopg.rows")
        except ModuleNotFoundError as exc:
            raise OpenInfraError(
                "postgresql pooling requires optional dependency: pip install openinfra[postgresql]"
            ) from exc
        pool_type = pool_module.ConnectionPool
        self._pool: Any = pool_type(
            conninfo=dsn,
            min_size=settings.min_size,
            max_size=settings.max_size,
            timeout=settings.timeout_seconds,
            max_idle=settings.max_idle_seconds,
            max_lifetime=settings.max_lifetime_seconds,
            kwargs={
                "autocommit": False,
                "row_factory": rows.dict_row,
                "prepare_threshold": None,
                "options": "-c " + profile.dsn_options().replace(" ", " -c "),
            },
            open=False,
        )
        self._pool.open(wait=False)

    def getconn(self) -> ConnectionProtocol:
        try:
            return cast(ConnectionProtocol, self._pool.getconn())
        except Exception as exc:  # pragma: no cover - external PostgreSQL runtime
            raise OpenInfraError("postgresql pool acquisition failed: " + str(exc)) from exc

    def putconn(self, connection: ConnectionProtocol) -> None:
        self._pool.putconn(connection)

    def close(self) -> None:
        self._pool.close()

    def statistics(self) -> dict[str, float]:
        getter = getattr(self._pool, "get_stats", None)
        if not callable(getter):
            return {}
        raw = getter()
        allowed = {
            "pool_min",
            "pool_max",
            "pool_size",
            "pool_available",
            "requests_waiting",
            "requests_num",
            "requests_queued",
            "requests_wait_ms",
            "requests_errors",
            "usage_ms",
        }
        result: dict[str, float] = {}
        for name, value in raw.items():
            normalized = str(name)
            if normalized not in allowed or isinstance(value, bool):
                continue
            try:
                result[normalized] = float(value)
            except (TypeError, ValueError):
                continue
        return result


class PostgreSQLDriver:
    def connect(self, dsn: str, profile: PostgreSQLClusterProfile) -> ConnectionProtocol:
        try:
            psycopg = importlib.import_module("psycopg")
            rows = importlib.import_module("psycopg.rows")
        except ModuleNotFoundError as exc:
            raise OpenInfraError(
                "postgresql backend requires optional dependency: pip install openinfra[postgresql]"
            ) from exc
        connect = cast(Callable[..., ConnectionProtocol], psycopg.connect)
        row_factory = rows.dict_row
        try:
            return connect(
                dsn,
                autocommit=False,
                row_factory=row_factory,
                prepare_threshold=None,
                options="-c " + profile.dsn_options().replace(" ", " -c "),
            )
        except Exception as exc:  # pragma: no cover - depends on external PostgreSQL runtime
            raise OpenInfraError("postgresql connection failed: " + str(exc)) from exc


class PostgreSQLConnectionFactory:
    def __init__(
        self,
        dsn: str,
        profile: PostgreSQLClusterProfile | None = None,
        connector: Callable[[str, PostgreSQLClusterProfile], ConnectionProtocol] | None = None,
        pool_settings: PostgreSQLConnectionPoolSettings | None = None,
        pool_factory: Callable[
            [str, PostgreSQLClusterProfile, PostgreSQLConnectionPoolSettings],
            PostgreSQLConnectionPool,
        ]
        | None = None,
    ) -> None:
        normalized = dsn.strip()
        if not normalized:
            raise ValidationError("postgresql dsn is mandatory")
        self._dsn = normalized
        self._profile = profile or PostgreSQLClusterProfile.production_default()
        self._connector = connector or PostgreSQLDriver().connect
        self._pool: PostgreSQLConnectionPool | None = None
        if pool_settings is not None:
            if connector is not None and pool_factory is None:
                raise ValidationError(
                    "postgresql connector and pool settings require an explicit pool_factory"
                )
            factory = pool_factory or PostgreSQLConnectionPool
            self._pool = factory(self._dsn, self._profile, pool_settings)

    @property
    def pooled(self) -> bool:
        return self._pool is not None

    def create(self) -> ConnectionProtocol:
        if self._pool is not None:
            return self._pool.getconn()
        return self._connector(self._dsn, self._profile)

    def release(self, connection: ConnectionProtocol) -> None:
        if self._pool is not None:
            self._pool.putconn(connection)
            return
        connection.close()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()

    def statistics(self) -> dict[str, float]:
        if self._pool is None:
            return {"pooled": 0.0}
        return {"pooled": 1.0, **self._pool.statistics()}


class PostgreSQLReplicaMonitor:
    _probe_sql = """
        SELECT
            pg_is_in_recovery() AS is_replica,
            CASE
                WHEN pg_last_xact_replay_timestamp() IS NULL THEN NULL
                ELSE EXTRACT(EPOCH FROM (clock_timestamp() - pg_last_xact_replay_timestamp()))
            END AS lag_seconds
    """

    def __init__(
        self,
        read_factory: PostgreSQLConnectionFactory,
        settings: PostgreSQLReadRoutingSettings,
        *,
        monotonic_clock: Callable[[], float] = time.monotonic,
        epoch_clock: Callable[[], float] = time.time,
    ) -> None:
        self._read_factory = read_factory
        self._settings = settings
        self._monotonic_clock = monotonic_clock
        self._epoch_clock = epoch_clock
        self._lock = threading.Lock()
        self._last_probe_monotonic = float("-inf")
        self._snapshot = PostgreSQLReplicaHealth.disabled()

    def snapshot(self, *, force: bool = False) -> PostgreSQLReplicaHealth:
        now = self._monotonic_clock()
        with self._lock:
            if (
                not force
                and self._snapshot.checked_at_epoch is not None
                and now - self._last_probe_monotonic < self._settings.probe_interval_seconds
            ):
                return self._snapshot
            self._snapshot = self._probe()
            self._last_probe_monotonic = now
            return self._snapshot

    def _probe(self) -> PostgreSQLReplicaHealth:
        connection = self._read_factory.create()
        cursor = connection.cursor()
        try:
            cursor.execute(self._probe_sql)
            row = cursor.fetchone() or {}
            connection.rollback()
            is_replica = bool(row.get("is_replica", False))
            raw_lag = row.get("lag_seconds")
            lag_seconds = float(str(raw_lag)) if raw_lag is not None else None
            recovery_ok = is_replica or not self._settings.require_recovery
            lag_ok = lag_seconds is not None and lag_seconds <= (
                self._settings.max_replica_lag_seconds
            )
            eligible = recovery_ok and lag_ok
            if not recovery_ok:
                detail = "configured read endpoint is not a PostgreSQL standby"
            elif lag_seconds is None:
                detail = "replica replay timestamp is unavailable"
            elif not lag_ok:
                detail = (
                    "replica lag exceeds threshold: "
                    f"{lag_seconds:.3f}s > {self._settings.max_replica_lag_seconds:.3f}s"
                )
            else:
                detail = f"replica is eligible with {lag_seconds:.3f}s replay lag"
            return PostgreSQLReplicaHealth(
                configured=True,
                eligible=eligible,
                is_replica=is_replica,
                lag_seconds=lag_seconds,
                checked_at_epoch=self._epoch_clock(),
                detail=detail,
            )
        except Exception as exc:
            with suppress(Exception):
                connection.rollback()
            return PostgreSQLReplicaHealth(
                configured=True,
                eligible=False,
                is_replica=False,
                lag_seconds=None,
                checked_at_epoch=self._epoch_clock(),
                detail="replica probe failed: " + str(exc),
            )
        finally:
            cursor.close()
            self._read_factory.release(connection)


class PostgreSQLSessionRegistry:
    def __init__(
        self,
        factory: PostgreSQLConnectionFactory,
        read_factory: PostgreSQLConnectionFactory | None = None,
        read_routing_settings: PostgreSQLReadRoutingSettings | None = None,
        replica_monitor: PostgreSQLReplicaMonitor | None = None,
    ) -> None:
        self._factory = factory
        self._read_factory = read_factory
        self._read_routing_settings = read_routing_settings or PostgreSQLReadRoutingSettings(
            enabled=False,
            max_replica_lag_seconds=0,
            probe_interval_seconds=1,
            fallback_to_primary=True,
        )
        self._replica_monitor = replica_monitor
        if self._read_routing_settings.enabled and self._read_factory is None:
            raise ValidationError("postgresql read routing requires a read connection factory")
        if self._read_factory is not None and self._replica_monitor is None:
            self._replica_monitor = PostgreSQLReplicaMonitor(
                self._read_factory, self._read_routing_settings
            )
        self._local = threading.local()
        self._lease_lock = threading.Lock()
        self._lease_factories: dict[int, PostgreSQLConnectionFactory] = {}
        self._stats_lock = threading.Lock()
        self._primary_acquisitions = 0
        self._replica_acquisitions = 0
        self._replica_fallbacks = 0
        self._acquisition_failures = {"primary": 0, "replica": 0}
        self._acquisition_duration_seconds = {"primary": 0.0, "replica": 0.0}

    def open(self, *, read_only: bool = False) -> ConnectionProtocol:
        factory = self._select_factory(read_only=read_only)
        target = "replica" if factory is self._read_factory else "primary"
        started_at = time.perf_counter()
        try:
            connection = factory.create()
        except Exception:
            with self._stats_lock:
                self._acquisition_failures[target] += 1
            raise
        finally:
            elapsed = max(0.0, time.perf_counter() - started_at)
            with self._stats_lock:
                self._acquisition_duration_seconds[target] += elapsed
        with self._lease_lock:
            self._lease_factories[id(connection)] = factory
        return connection

    def release(self, connection: ConnectionProtocol) -> None:
        with self._lease_lock:
            factory = self._lease_factories.pop(id(connection), self._factory)
        factory.release(connection)

    def close(self) -> None:
        self._factory.close()
        if self._read_factory is not None and self._read_factory is not self._factory:
            self._read_factory.close()

    def bind(self, connection: ConnectionProtocol) -> None:
        self._local.connection = connection

    def unbind(self) -> None:
        if hasattr(self._local, "connection"):
            del self._local.connection

    def has_current(self) -> bool:
        return getattr(self._local, "connection", None) is not None

    def current(self) -> ConnectionProtocol:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            raise OpenInfraError("postgresql operation requires an active unit of work")
        return cast(ConnectionProtocol, connection)

    @contextmanager
    def read_scope(self) -> Iterator[ConnectionProtocol]:
        if self.has_current():
            yield self.current()
            return
        connection = self.open(read_only=True)
        self.bind(connection)
        try:
            yield connection
        finally:
            try:
                connection.rollback()
            finally:
                self.unbind()
                self.release(connection)

    def routing_status_as_dict(self, *, force_probe: bool = False) -> dict[str, object]:
        snapshot = (
            self._replica_monitor.snapshot(force=force_probe)
            if self._replica_monitor is not None
            else PostgreSQLReplicaHealth.disabled()
        )
        with self._stats_lock:
            counters = {
                "primary_acquisitions": self._primary_acquisitions,
                "replica_acquisitions": self._replica_acquisitions,
                "replica_fallbacks": self._replica_fallbacks,
            }
        return {
            "read_routing_enabled": self._read_routing_settings.enabled,
            "fallback_to_primary": self._read_routing_settings.fallback_to_primary,
            "max_replica_lag_seconds": (self._read_routing_settings.max_replica_lag_seconds),
            "replica": snapshot.as_dict(),
            "counters": counters,
        }

    def operational_metrics(self, *, force_probe: bool = False) -> dict[str, object]:
        routing = self.routing_status_as_dict(force_probe=force_probe)
        with self._stats_lock:
            primary_count = self._primary_acquisitions
            replica_count = self._replica_acquisitions
            primary_duration = self._acquisition_duration_seconds["primary"]
            replica_duration = self._acquisition_duration_seconds["replica"]
            primary_failures = self._acquisition_failures["primary"]
            replica_failures = self._acquisition_failures["replica"]
        primary = {
            **self._factory.statistics(),
            "acquisitions": float(primary_count),
            "acquisition_failures": float(primary_failures),
            "acquisition_duration_seconds_sum": primary_duration,
            "acquisition_duration_seconds_count": float(primary_count + primary_failures),
        }
        replica: dict[str, float] = {}
        if self._read_factory is not None:
            replica = {
                **self._read_factory.statistics(),
                "acquisitions": float(replica_count),
                "acquisition_failures": float(replica_failures),
                "acquisition_duration_seconds_sum": replica_duration,
                "acquisition_duration_seconds_count": float(replica_count + replica_failures),
            }
        return {"routing": routing, "pools": {"primary": primary, "replica": replica}}

    def _select_factory(self, *, read_only: bool) -> PostgreSQLConnectionFactory:
        prefer_replica = (
            read_only
            and ReadRoutingContext.current() is ReadRoute.REPLICA
            and self._read_routing_settings.enabled
            and self._read_factory is not None
        )
        if not prefer_replica:
            self._increment("primary")
            return self._factory
        monitor = self._replica_monitor
        snapshot = monitor.snapshot() if monitor is not None else PostgreSQLReplicaHealth.disabled()
        if snapshot.eligible:
            self._increment("replica")
            read_factory = self._read_factory
            if read_factory is None:  # pragma: no cover - guarded by prefer_replica
                raise OpenInfraError("postgresql read factory is unavailable")
            return read_factory
        if self._read_routing_settings.fallback_to_primary:
            self._increment("fallback")
            self._increment("primary")
            return self._factory
        raise OpenInfraError("postgresql read replica is not eligible: " + snapshot.detail)

    def _increment(self, counter: str) -> None:
        with self._stats_lock:
            if counter == "primary":
                self._primary_acquisitions += 1
            elif counter == "replica":
                self._replica_acquisitions += 1
            else:
                self._replica_fallbacks += 1


class PostgreSQLUnitOfWork(UnitOfWork):
    def __init__(self, registry: PostgreSQLSessionRegistry) -> None:
        self._registry = registry
        self._connection: ConnectionProtocol | None = None
        self._committed = False

    def __enter__(self) -> PostgreSQLUnitOfWork:
        connection = self._registry.open()
        self._connection = connection
        self._registry.bind(connection)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        connection = self._require_connection()
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._registry.unbind()
            self._registry.release(connection)
            self._connection = None

    def commit(self) -> None:
        self._require_connection().commit()
        self._committed = True

    def rollback(self) -> None:
        self._require_connection().rollback()
        self._committed = False

    def _require_connection(self) -> ConnectionProtocol:
        if self._connection is None:
            raise OpenInfraError("postgresql unit of work is not active")
        return self._connection


class PostgreSQLReadinessProbe(ReadinessProbe):
    def __init__(
        self,
        registry: PostgreSQLSessionRegistry,
        migration_catalog: PostgreSQLMigrationCatalog | None = None,
    ) -> None:
        self._registry = registry
        self._migration_catalog = migration_catalog

    def check(self) -> ReadinessStatus:
        connection = self._registry.open()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT 1 AS ready")
            row = cursor.fetchone()
            ready_value = row.get("ready") if row else None
            if ready_value != 1:
                connection.rollback()
                return ReadinessStatus("postgresql", False, "unexpected readiness response")
            catalog = self._migration_catalog
            if catalog is not None:
                schema_status = self._check_schema(cursor, catalog)
                connection.rollback()
                if not schema_status.ready:
                    return ReadinessStatus("postgresql", False, schema_status.detail)
                return ReadinessStatus(
                    "postgresql",
                    True,
                    "postgresql connection and schema are ready",
                )
            connection.rollback()
            return ReadinessStatus("postgresql", True, "postgresql primary connection is reachable")
        except Exception as exc:
            connection.rollback()
            return ReadinessStatus("postgresql", False, f"postgresql readiness failed: {exc}")
        finally:
            cursor.close()
            self._registry.release(connection)

    def _check_schema(
        self,
        cursor: CursorProtocol,
        catalog: PostgreSQLMigrationCatalog,
    ) -> PostgreSQLSchemaStatus:
        cursor.execute(
            "SELECT to_regclass('public.openinfra_schema_migrations') AS migration_table"
        )
        row = cursor.fetchone()
        if row is None or row.get("migration_table") is None:
            missing_history_pending = tuple(catalog.load(name) for name in catalog.list_names())
            return PostgreSQLSchemaStatus(
                False,
                (),
                missing_history_pending,
                "postgresql schema history is missing; run openinfra database apply-migrations",
            )
        cursor.execute(
            """
            SELECT version, checksum, applied_at
            FROM openinfra_schema_migrations
            ORDER BY version
            """
        )
        applied: dict[str, PostgreSQLAppliedMigration] = {}
        for item in cursor.fetchall():
            applied[str(item["version"])] = PostgreSQLAppliedMigration(
                version=str(item["version"]),
                checksum=str(item["checksum"]),
                applied_at=str(item["applied_at"]),
            )
        pending: list[PostgreSQLMigration] = []
        for name in catalog.list_names():
            migration = catalog.load(name)
            applied_migration = applied.get(migration.name)
            if applied_migration is None:
                pending.append(migration)
                continue
            if applied_migration.checksum != migration.checksum:
                return PostgreSQLSchemaStatus(
                    False,
                    tuple(applied.values()),
                    (),
                    "postgresql schema checksum mismatch: " + migration.name,
                )
        detail = (
            "postgresql schema is up to date"
            if not pending
            else "postgresql schema has pending migrations"
        )
        return PostgreSQLSchemaStatus(not pending, tuple(applied.values()), tuple(pending), detail)


class PostgreSQLTransactionManager(TransactionManager):
    def __init__(self, registry: PostgreSQLSessionRegistry) -> None:
        self._registry = registry

    def begin(self) -> PostgreSQLUnitOfWork:
        return PostgreSQLUnitOfWork(self._registry)


class PostgreSQLRepositoryBase:
    def __init__(
        self,
        registry: PostgreSQLSessionRegistry,
        cursor_codec: CursorTokenCodec | None = None,
    ) -> None:
        self._registry = registry
        self._cursor_codec = cursor_codec

    def _keyset_page(
        self,
        pagination: Pagination,
        *,
        scope: str,
        tenant_id: TenantId,
        filters: Mapping[str, object],
        fields: Sequence[CursorField],
    ) -> PostgreSQLKeysetPage:
        return PostgreSQLKeysetPage.create(
            pagination,
            scope=scope,
            tenant_id=tenant_id.value,
            filters=filters,
            fields=fields,
            codec=self._cursor_codec,
        )

    def _execute(self, query: str, params: Mapping[str, object] | None = None) -> CursorProtocol:
        cursor = self._registry.current().cursor()
        try:
            cursor.execute(query, params or {})
        except Exception:
            cursor.close()
            raise
        return cursor

    def _fetch_one(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> Mapping[str, object] | None:
        cursor = self._registry.current().cursor()
        try:
            cursor.execute(query, params or {})
            return cursor.fetchone()
        finally:
            cursor.close()

    def _fetch_all(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> Sequence[Mapping[str, object]]:
        cursor = self._registry.current().cursor()
        try:
            cursor.execute(query, params or {})
            return cursor.fetchall()
        finally:
            cursor.close()

    def _execute_without_result(
        self,
        query: str,
        params: Mapping[str, object] | None = None,
    ) -> CursorProtocol:
        cursor = self._execute(query, params)
        cursor.close()
        return cursor

    def _ensure_tenant(self, tenant_id: TenantId) -> None:
        self._execute_without_result(
            """
            INSERT INTO tenants (id, display_name)
            VALUES (%(tenant_id)s, %(display_name)s)
            ON CONFLICT (id) DO NOTHING
            """,
            {"tenant_id": tenant_id.value, "display_name": tenant_id.value},
        )

    def _row_int(self, row: Mapping[str, object], key: str) -> int:
        return int(str(row[key]))

    def _row_int_or_default(self, row: Mapping[str, object], key: str, default: int) -> int:
        value = row.get(key)
        return default if value is None else int(str(value))

    def _row_float(self, row: Mapping[str, object], key: str) -> float:
        return float(str(row[key]))

    def _row_sequence(self, row: Mapping[str, object], key: str) -> Sequence[object]:
        return cast(Sequence[object], row[key])

    def _row_optional_sequence(
        self,
        row: Mapping[str, object],
        key: str,
        default: Sequence[object],
    ) -> Sequence[object]:
        value = row.get(key)
        return default if value is None else cast(Sequence[object], value)


class PostgreSQLRuntimeUsageRepository(PostgreSQLRepositoryBase, RuntimeUsageRepository):
    _COUNT_QUERIES: ClassVar[dict[QuotaResource, tuple[str, ...]]] = {
        QuotaResource.EQUIPMENT: (
            "SELECT COUNT(*) AS total FROM equipment WHERE tenant_id = %(tenant_id)s",
        ),
        QuotaResource.SUBNET_VLAN: (
            "SELECT COUNT(*) AS total FROM prefixes WHERE tenant_id = %(tenant_id)s",
            "SELECT COUNT(*) AS total FROM ipam_vlans WHERE tenant_id = %(tenant_id)s",
        ),
        QuotaResource.IP_DNS_RECORD: (
            "SELECT COUNT(*) AS total FROM ip_reservations WHERE tenant_id = %(tenant_id)s",
            "SELECT COUNT(*) AS total FROM ip_address_records WHERE tenant_id = %(tenant_id)s",
            "SELECT COUNT(*) AS total FROM ipam_dns_observations WHERE tenant_id = %(tenant_id)s",
        ),
        QuotaResource.USER: (
            "SELECT COUNT(*) AS total FROM identity_users WHERE tenant_id = %(tenant_id)s",
        ),
        QuotaResource.DISCOVERY_COLLECTOR: (
            "SELECT COUNT(*) AS total FROM discovery_collectors WHERE tenant_id = %(tenant_id)s",
        ),
    }

    def count_resource(self, tenant_id: TenantId, resource: QuotaResource) -> int:
        try:
            return self._count_with_active_connection(tenant_id, resource)
        except OpenInfraError:
            connection = self._registry.open()
            self._registry.bind(connection)
            try:
                total = self._count_with_active_connection(tenant_id, resource)
                connection.rollback()
                return total
            finally:
                self._registry.unbind()
                self._registry.release(connection)

    def _count_with_active_connection(self, tenant_id: TenantId, resource: QuotaResource) -> int:
        total = 0
        for query in self._COUNT_QUERIES[resource]:
            row = self._fetch_one(query, {"tenant_id": tenant_id.value})
            if row is not None:
                total += self._row_int(row, "total")
        return total


class PostgreSQLDcimRepository(PostgreSQLRepositoryBase, DcimRepository):
    def add_site(self, site: Site) -> None:
        self._ensure_tenant(site.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sites (
                id, tenant_id, code, name, country, city, region,
                street_address, postal_code, contact_email, phone, status
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(name)s, %(country)s,
                %(city)s, %(region)s, %(street_address)s, %(postal_code)s,
                %(contact_email)s, %(phone)s, %(status)s
            )
            ON CONFLICT (tenant_id, code) DO NOTHING
            """,
            {
                "id": site.id.value,
                "tenant_id": site.tenant_id.value,
                "code": site.code.value,
                "name": site.name.value,
                "country": site.country,
                "city": site.city,
                "region": site.region,
                "street_address": site.street_address,
                "postal_code": site.postal_code,
                "contact_email": site.contact_email,
                "phone": site.phone,
                "status": site.status.value,
            },
        )

    def save_site(self, site: Site) -> None:
        self._ensure_tenant(site.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sites (
                id, tenant_id, code, name, country, city, region,
                street_address, postal_code, contact_email, phone, status
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(name)s, %(country)s,
                %(city)s, %(region)s, %(street_address)s, %(postal_code)s,
                %(contact_email)s, %(phone)s, %(status)s
            )
            ON CONFLICT (tenant_id, code) DO UPDATE SET
                organization_id = EXCLUDED.organization_id,
                name = EXCLUDED.name,
                country = EXCLUDED.country,
                city = EXCLUDED.city,
                region = EXCLUDED.region,
                street_address = EXCLUDED.street_address,
                postal_code = EXCLUDED.postal_code,
                contact_email = EXCLUDED.contact_email,
                phone = EXCLUDED.phone,
                status = EXCLUDED.status
            """,
            {
                "id": site.id.value,
                "tenant_id": site.tenant_id.value,
                "code": site.code.value,
                "name": site.name.value,
                "country": site.country,
                "city": site.city,
                "region": site.region,
                "street_address": site.street_address,
                "postal_code": site.postal_code,
                "contact_email": site.contact_email,
                "phone": site.phone,
                "status": site.status.value,
            },
        )

    def add_building(self, building: Building) -> None:
        self._ensure_tenant(building.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO buildings (
                id, tenant_id, site_code, code, name, building_type,
                initial_level, final_level, status
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(code)s, %(name)s,
                %(building_type)s, %(initial_level)s, %(final_level)s, %(status)s
            )
            ON CONFLICT (tenant_id, site_code, code) DO NOTHING
            """,
            {
                "id": building.id.value,
                "tenant_id": building.tenant_id.value,
                "site_code": building.site_code.value,
                "code": building.code.value,
                "name": building.name.value,
                "building_type": building.building_type.value,
                "initial_level": building.initial_level,
                "final_level": building.final_level,
                "status": building.status.value,
            },
        )

    def save_building(self, building: Building) -> None:
        self._execute_without_result(
            """
            UPDATE buildings
            SET name = %(name)s,
                building_type = %(building_type)s,
                initial_level = %(initial_level)s,
                final_level = %(final_level)s,
                status = %(status)s
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s AND code = %(code)s
            """,
            {
                "tenant_id": building.tenant_id.value,
                "site_code": building.site_code.value,
                "code": building.code.value,
                "name": building.name.value,
                "building_type": building.building_type.value,
                "initial_level": building.initial_level,
                "final_level": building.final_level,
                "status": building.status.value,
            },
        )

    def add_floor(self, floor: Floor) -> None:
        self._ensure_tenant(floor.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO floors (
                id, tenant_id, site_code, building_code, code, name, level_index, status
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s,
                %(code)s, %(name)s, %(level_index)s, %(status)s
            )
            ON CONFLICT (tenant_id, site_code, building_code, code) DO NOTHING
            """,
            {
                "id": floor.id.value,
                "tenant_id": floor.tenant_id.value,
                "site_code": floor.site_code.value,
                "building_code": floor.building_code.value,
                "code": floor.code.value,
                "name": floor.name.value,
                "level_index": floor.level_index,
                "status": floor.status.value,
            },
        )

    def save_floor(self, floor: Floor) -> None:
        self._execute_without_result(
            """
            UPDATE floors
            SET name = %(name)s, level_index = %(level_index)s, status = %(status)s
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": floor.tenant_id.value,
                "site_code": floor.site_code.value,
                "building_code": floor.building_code.value,
                "code": floor.code.value,
                "name": floor.name.value,
                "level_index": floor.level_index,
                "status": floor.status.value,
            },
        )

    def add_room(self, room: Room) -> None:
        self._ensure_tenant(room.tenant_id)
        coordinates = room.coordinates
        self._execute_without_result(
            """
            INSERT INTO rooms (
                id, tenant_id, site_code, building_code, floor_code, code, name, rows, columns,
                zone_codes, coordinate_x, coordinate_y, coordinate_z, status
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(floor_code)s,
                %(code)s, %(name)s, %(rows)s, %(columns)s, %(zone_codes)s,
                %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s, %(status)s
            )
            ON CONFLICT (tenant_id, site_code, building_code, code) DO NOTHING
            """,
            {
                "id": room.id.value,
                "tenant_id": room.tenant_id.value,
                "site_code": room.site_code.value,
                "building_code": room.building_code.value,
                "floor_code": room.floor_code.value if room.floor_code else None,
                "code": room.code.value,
                "name": room.name.value,
                "rows": list(room.rows),
                "columns": list(room.columns),
                "zone_codes": [zone.value for zone in room.zone_codes],
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
                "status": room.status.value,
            },
        )

    def save_room(self, room: Room) -> None:
        coordinates = room.coordinates
        self._execute_without_result(
            """
            UPDATE rooms
            SET name = %(name)s, rows = %(rows)s, columns = %(columns)s,
                zone_codes = %(zone_codes)s, coordinate_x = %(coordinate_x)s,
                coordinate_y = %(coordinate_y)s, coordinate_z = %(coordinate_z)s,
                status = %(status)s
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": room.tenant_id.value,
                "site_code": room.site_code.value,
                "building_code": room.building_code.value,
                "code": room.code.value,
                "name": room.name.value,
                "rows": list(room.rows),
                "columns": list(room.columns),
                "zone_codes": [zone.value for zone in room.zone_codes],
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
                "status": room.status.value,
            },
        )

    def add_zone(self, zone: RoomZone) -> None:
        self._ensure_tenant(zone.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO room_zones (
                id, tenant_id, site_code, building_code, floor_code, room_code, code,
                name, rows, columns, status
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(floor_code)s,
                %(room_code)s, %(code)s, %(name)s, %(rows)s, %(columns)s, %(status)s
            )
            ON CONFLICT (tenant_id, site_code, building_code, room_code, code) DO NOTHING
            """,
            {
                "id": zone.id.value,
                "tenant_id": zone.tenant_id.value,
                "site_code": zone.site_code.value,
                "building_code": zone.building_code.value,
                "floor_code": zone.floor_code.value,
                "room_code": zone.room_code.value,
                "code": zone.code.value,
                "name": zone.name.value,
                "rows": list(zone.rows),
                "columns": list(zone.columns),
                "status": zone.status.value,
            },
        )

    def save_zone(self, zone: RoomZone) -> None:
        self._execute_without_result(
            """
            UPDATE room_zones
            SET name = %(name)s, rows = %(rows)s, columns = %(columns)s, status = %(status)s
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": zone.tenant_id.value,
                "site_code": zone.site_code.value,
                "building_code": zone.building_code.value,
                "room_code": zone.room_code.value,
                "code": zone.code.value,
                "name": zone.name.value,
                "rows": list(zone.rows),
                "columns": list(zone.columns),
                "status": zone.status.value,
            },
        )

    def add_rack(self, rack: Rack) -> None:
        self._ensure_tenant(rack.tenant_id)
        coordinates = rack.coordinates
        self._execute_without_result(
            """
            INSERT INTO racks (
                id, tenant_id, site_code, building_code, floor_code, room_code, code,
                row_code, column_code, zone_code, units, coordinate_x, coordinate_y, coordinate_z,
                usable_faces, max_weight_kg, power_capacity_watts, status
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(floor_code)s,
                %(room_code)s, %(code)s, %(row_code)s, %(column_code)s, %(zone_code)s,
                %(units)s, %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s,
                %(usable_faces)s, %(max_weight_kg)s, %(power_capacity_watts)s, %(status)s
            )
            """,
            {
                "id": rack.id.value,
                "tenant_id": rack.tenant_id.value,
                "site_code": rack.site_code.value,
                "building_code": rack.building_code.value,
                "room_code": rack.room_code.value,
                "code": rack.code.value,
                "row_code": rack.row,
                "column_code": rack.column,
                "floor_code": rack.floor_code.value if rack.floor_code else None,
                "zone_code": rack.zone_code.value if rack.zone_code else None,
                "units": rack.units,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
                "usable_faces": [face.value for face in rack.usable_faces],
                "max_weight_kg": rack.max_weight_kg,
                "power_capacity_watts": rack.power_capacity_watts,
                "status": rack.status.value,
            },
        )

    def save_rack(self, rack: Rack) -> None:
        coordinates = rack.coordinates
        self._execute_without_result(
            """
            UPDATE racks
            SET row_code = %(row_code)s, column_code = %(column_code)s, units = %(units)s,
                coordinate_x = %(coordinate_x)s, coordinate_y = %(coordinate_y)s,
                coordinate_z = %(coordinate_z)s, usable_faces = %(usable_faces)s,
                max_weight_kg = %(max_weight_kg)s,
                power_capacity_watts = %(power_capacity_watts)s, status = %(status)s
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": rack.tenant_id.value,
                "site_code": rack.site_code.value,
                "building_code": rack.building_code.value,
                "room_code": rack.room_code.value,
                "code": rack.code.value,
                "row_code": rack.row,
                "column_code": rack.column,
                "units": rack.units,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
                "usable_faces": [face.value for face in rack.usable_faces],
                "max_weight_kg": rack.max_weight_kg,
                "power_capacity_watts": rack.power_capacity_watts,
                "status": rack.status.value,
            },
        )

    def add_patch_panel(self, patch_panel: PatchPanel) -> None:
        self._ensure_tenant(patch_panel.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_patch_panels (
                id, tenant_id, site_code, building_code, room_code, rack_code, code,
                rack_face, u_position, u_height, port_count, connector, medium, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(room_code)s,
                %(rack_code)s, %(code)s, %(rack_face)s, %(u_position)s, %(u_height)s,
                %(port_count)s, %(connector)s, %(medium)s, %(label)s
            )
            """,
            {
                "id": patch_panel.id.value,
                "tenant_id": patch_panel.tenant_id.value,
                "site_code": patch_panel.site_code.value,
                "building_code": patch_panel.building_code.value,
                "room_code": patch_panel.room_code.value,
                "rack_code": patch_panel.rack_code.value,
                "code": patch_panel.code.value,
                "rack_face": patch_panel.rack_face.value,
                "u_position": patch_panel.u_position,
                "u_height": patch_panel.u_height,
                "port_count": patch_panel.port_count,
                "connector": patch_panel.connector.value,
                "medium": patch_panel.medium.value,
                "label": patch_panel.label,
            },
        )

    def add_dcim_port(self, port: DcimPort) -> None:
        self._ensure_tenant(port.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_ports (
                id, tenant_id, owner_type, owner_code, port_name, site_code,
                building_code, room_code, connector, medium, enabled
            ) VALUES (
                %(id)s, %(tenant_id)s, %(owner_type)s, %(owner_code)s, %(port_name)s,
                %(site_code)s, %(building_code)s, %(room_code)s, %(connector)s,
                %(medium)s, %(enabled)s
            )
            """,
            {
                "id": port.id.value,
                "tenant_id": port.tenant_id.value,
                "owner_type": port.endpoint.owner_type.value,
                "owner_code": port.endpoint.owner_code.value,
                "port_name": port.endpoint.port_name.value,
                "site_code": port.site_code.value,
                "building_code": port.building_code.value,
                "room_code": port.room_code.value,
                "connector": port.connector.value,
                "medium": port.medium.value,
                "enabled": port.enabled,
            },
        )

    def add_dcim_cable(self, cable: DcimCable) -> None:
        self._ensure_tenant(cable.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_cables (
                id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                length_m, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(cable_id)s, %(a_owner_type)s, %(a_owner_code)s,
                %(a_port_name)s, %(b_owner_type)s, %(b_owner_code)s, %(b_port_name)s,
                %(medium)s, %(status)s, %(path_segments)s, %(length_m)s, %(label)s
            )
            """,
            {
                "id": cable.id.value,
                "tenant_id": cable.tenant_id.value,
                "cable_id": cable.cable_id.value,
                "a_owner_type": cable.a_endpoint.owner_type.value,
                "a_owner_code": cable.a_endpoint.owner_code.value,
                "a_port_name": cable.a_endpoint.port_name.value,
                "b_owner_type": cable.b_endpoint.owner_type.value,
                "b_owner_code": cable.b_endpoint.owner_code.value,
                "b_port_name": cable.b_endpoint.port_name.value,
                "medium": cable.medium.value,
                "status": cable.status.value,
                "path_segments": json.dumps([segment.as_dict() for segment in cable.path]),
                "length_m": cable.length_m,
                "label": cable.label,
            },
        )

    def add_equipment(self, equipment: Equipment) -> None:
        self._ensure_tenant(equipment.tenant_id)
        location = equipment.location
        coordinates = location.coordinates
        self._execute_without_result(
            """
            INSERT INTO equipment (
                id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                coordinate_x, coordinate_y, coordinate_z
            ) VALUES (
                %(id)s, %(tenant_id)s, %(asset_tag)s, %(name)s, %(site_code)s, %(building_code)s,
                %(floor_code)s, %(room_code)s, %(row_code)s, %(column_code)s, %(zone_code)s,
                %(rack_code)s, %(u_position)s, %(rack_face)s, %(u_height)s,
                %(coordinate_x)s, %(coordinate_y)s, %(coordinate_z)s
            )
            ON CONFLICT (tenant_id, asset_tag) DO UPDATE SET
                organization_id = EXCLUDED.organization_id,
                name = EXCLUDED.name,
                site_code = EXCLUDED.site_code,
                building_code = EXCLUDED.building_code,
                floor_code = EXCLUDED.floor_code,
                room_code = EXCLUDED.room_code,
                row_code = EXCLUDED.row_code,
                column_code = EXCLUDED.column_code,
                zone_code = EXCLUDED.zone_code,
                rack_code = EXCLUDED.rack_code,
                u_position = EXCLUDED.u_position,
                rack_face = EXCLUDED.rack_face,
                u_height = EXCLUDED.u_height,
                coordinate_x = EXCLUDED.coordinate_x,
                coordinate_y = EXCLUDED.coordinate_y,
                coordinate_z = EXCLUDED.coordinate_z,
                version = equipment.version + 1,
                updated_at = now()
            """,
            {
                "id": equipment.id.value,
                "tenant_id": equipment.tenant_id.value,
                "asset_tag": equipment.asset_tag.value,
                "name": equipment.name.value,
                "site_code": location.site_code.value,
                "building_code": location.building_code.value,
                "floor_code": location.floor_code.value if location.floor_code else None,
                "room_code": location.room_code.value,
                "row_code": location.row,
                "column_code": location.column,
                "zone_code": location.zone_code.value if location.zone_code else None,
                "rack_code": location.rack_code.value if location.rack_code else None,
                "u_position": location.u_position,
                "rack_face": location.rack_face.value if location.rack_face else None,
                "u_height": location.u_height,
                "coordinate_x": coordinates.x if coordinates else None,
                "coordinate_y": coordinates.y if coordinates else None,
                "coordinate_z": coordinates.z if coordinates else None,
            },
        )

    def add_power_device(self, power_device: PowerDevice) -> None:
        self._ensure_tenant(power_device.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_power_devices (
                id, tenant_id, code, kind, site_code, building_code, room_code, rack_code,
                side, capacity_watts, derating_percent, input_source, output_voltage, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(kind)s, %(site_code)s, %(building_code)s,
                %(room_code)s, %(rack_code)s, %(side)s, %(capacity_watts)s,
                %(derating_percent)s, %(input_source)s, %(output_voltage)s, %(label)s
            )
            """,
            {
                "id": power_device.id.value,
                "tenant_id": power_device.tenant_id.value,
                "code": power_device.code.value,
                "kind": power_device.kind.value,
                "site_code": power_device.site_code.value,
                "building_code": power_device.building_code.value,
                "room_code": power_device.room_code.value,
                "rack_code": power_device.rack_code.value if power_device.rack_code else None,
                "side": power_device.side.value if power_device.side else None,
                "capacity_watts": power_device.capacity_watts,
                "derating_percent": power_device.derating_percent,
                "input_source": power_device.input_source,
                "output_voltage": power_device.output_voltage,
                "label": power_device.label,
            },
        )

    def add_power_circuit(self, circuit: PowerCircuit) -> None:
        self._ensure_tenant(circuit.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_power_circuits (
                id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                redundancy_group, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(circuit_id)s, %(source_device_code)s,
                %(site_code)s, %(building_code)s, %(room_code)s, %(rack_code)s, %(side)s,
                %(capacity_watts)s, %(breaker_rating_amps)s, %(redundancy_group)s, %(label)s
            )
            """,
            {
                "id": circuit.id.value,
                "tenant_id": circuit.tenant_id.value,
                "circuit_id": circuit.circuit_id.value,
                "source_device_code": circuit.source_device_code.value,
                "site_code": circuit.site_code.value,
                "building_code": circuit.building_code.value,
                "room_code": circuit.room_code.value,
                "rack_code": circuit.rack_code.value,
                "side": circuit.side.value,
                "capacity_watts": circuit.capacity_watts,
                "breaker_rating_amps": circuit.breaker_rating_amps,
                "redundancy_group": circuit.redundancy_group,
                "label": circuit.label,
            },
        )

    def add_cooling_zone(self, cooling_zone: CoolingZone) -> None:
        self._ensure_tenant(cooling_zone.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_cooling_zones (
                id, tenant_id, site_code, building_code, room_code, zone_code, role,
                cooling_capacity_watts, supply_temperature_c, return_temperature_c, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(site_code)s, %(building_code)s, %(room_code)s,
                %(zone_code)s, %(role)s, %(cooling_capacity_watts)s,
                %(supply_temperature_c)s, %(return_temperature_c)s, %(label)s
            )
            """,
            {
                "id": cooling_zone.id.value,
                "tenant_id": cooling_zone.tenant_id.value,
                "site_code": cooling_zone.site_code.value,
                "building_code": cooling_zone.building_code.value,
                "room_code": cooling_zone.room_code.value,
                "zone_code": cooling_zone.zone_code.value,
                "role": cooling_zone.role.value,
                "cooling_capacity_watts": cooling_zone.cooling_capacity_watts,
                "supply_temperature_c": cooling_zone.supply_temperature_c,
                "return_temperature_c": cooling_zone.return_temperature_c,
                "label": cooling_zone.label,
            },
        )

    def add_power_reservation(self, reservation: RackPowerReservation) -> None:
        self._ensure_tenant(reservation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO dcim_power_reservations (
                id, tenant_id, asset_tag, circuit_id, side, site_code, building_code,
                room_code, rack_code, expected_watts, label
            ) VALUES (
                %(id)s, %(tenant_id)s, %(asset_tag)s, %(circuit_id)s, %(side)s,
                %(site_code)s, %(building_code)s, %(room_code)s, %(rack_code)s,
                %(expected_watts)s, %(label)s
            )
            """,
            {
                "id": reservation.id.value,
                "tenant_id": reservation.tenant_id.value,
                "asset_tag": reservation.asset_tag.value,
                "circuit_id": reservation.circuit_id.value,
                "side": reservation.side.value,
                "site_code": reservation.site_code.value,
                "building_code": reservation.building_code.value,
                "room_code": reservation.room_code.value,
                "rack_code": reservation.rack_code.value,
                "expected_watts": reservation.expected_watts,
                "label": reservation.label,
            },
        )

    def list_sites(self, tenant_id: TenantId, include_retired: bool = False) -> tuple[Site, ...]:
        query = """
            SELECT * FROM sites
            WHERE tenant_id = %(tenant_id)s
            ORDER BY code
            """
        if not include_retired:
            query = """
                SELECT * FROM sites
                WHERE tenant_id = %(tenant_id)s AND status = 'active'
                ORDER BY code
                """
        rows = self._fetch_all(query, {"tenant_id": tenant_id.value})
        return tuple(self._site_from_row(row) for row in rows)

    def list_buildings(
        self, tenant_id: TenantId, site: str, include_retired: bool = False
    ) -> tuple[Building, ...]:
        query = """
            SELECT * FROM buildings
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site)s
            ORDER BY code
            """
        if not include_retired:
            query = """
                SELECT * FROM buildings
                WHERE tenant_id = %(tenant_id)s AND site_code = %(site)s AND status = 'active'
                ORDER BY code
                """
        rows = self._fetch_all(
            query,
            {"tenant_id": tenant_id.value, "site": Code.from_value(site, "site code").value},
        )
        return tuple(self._building_from_row(row) for row in rows)

    def list_floors(
        self, tenant_id: TenantId, site: str, building: str, include_retired: bool = False
    ) -> tuple[Floor, ...]:
        query = """
            SELECT * FROM floors
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site)s
              AND building_code = %(building)s
            ORDER BY level_index, code
            """
        if not include_retired:
            query = """
                SELECT * FROM floors
                WHERE tenant_id = %(tenant_id)s
                  AND site_code = %(site)s
                  AND building_code = %(building)s
                  AND status = 'active'
                ORDER BY level_index, code
                """
        rows = self._fetch_all(
            query,
            {
                "tenant_id": tenant_id.value,
                "site": Code.from_value(site, "site code").value,
                "building": Code.from_value(building, "building code").value,
            },
        )
        return tuple(self._floor_from_row(row) for row in rows)

    def list_rooms(
        self, tenant_id: TenantId, site: str, building: str, include_retired: bool = False
    ) -> tuple[Room, ...]:
        query = """
            SELECT * FROM rooms
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site)s
              AND building_code = %(building)s
            ORDER BY code
            """
        if not include_retired:
            query = """
                SELECT * FROM rooms
                WHERE tenant_id = %(tenant_id)s
                  AND site_code = %(site)s
                  AND building_code = %(building)s
                  AND status = 'active'
                ORDER BY code
                """
        rows = self._fetch_all(
            query,
            {
                "tenant_id": tenant_id.value,
                "site": Code.from_value(site, "site code").value,
                "building": Code.from_value(building, "building code").value,
            },
        )
        return tuple(self._room_from_row(row) for row in rows)

    def list_zones(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        include_retired: bool = False,
    ) -> tuple[RoomZone, ...]:
        query = """
            SELECT * FROM room_zones
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site)s
              AND building_code = %(building)s
              AND room_code = %(room)s
            ORDER BY code
            """
        if not include_retired:
            query = """
                SELECT * FROM room_zones
                WHERE tenant_id = %(tenant_id)s
                  AND site_code = %(site)s
                  AND building_code = %(building)s
                  AND room_code = %(room)s
                  AND status = 'active'
                ORDER BY code
                """
        rows = self._fetch_all(
            query,
            {
                "tenant_id": tenant_id.value,
                "site": Code.from_value(site, "site code").value,
                "building": Code.from_value(building, "building code").value,
                "room": Code.from_value(room, "room code").value,
            },
        )
        return tuple(self._zone_from_row(row) for row in rows)

    def find_site(self, tenant_id: TenantId, site: str) -> Site | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, code, name, country, city, region,
                   street_address, postal_code, contact_email, phone, status
            FROM sites
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "code": Code.from_value(site, "site code").value,
            },
        )
        return self._site_from_row(row) if row else None

    def find_building(self, tenant_id: TenantId, site: str, building: str) -> Building | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, code, name, building_type,
                   initial_level, final_level, status
            FROM buildings
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "code": Code.from_value(building, "building code").value,
            },
        )
        return self._building_from_row(row) if row else None

    def find_floor(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        floor: str,
    ) -> Floor | None:
        parameters: dict[str, object] = {
            "tenant_id": tenant_id.value,
            "site_code": Code.from_value(site, "site code").value,
            "building_code": Code.from_value(building, "building code").value,
            "code": Code.from_value(floor, "floor code").value,
        }
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, code, name, level_index, status
            FROM floors
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND code = %(code)s
            """,
            parameters,
        )
        if row is not None:
            return self._floor_from_row(row)
        requested_level = FloorNomenclature.level_from_code(floor)
        if requested_level is None:
            return None
        parameters["level_index"] = requested_level
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, code, name, level_index, status
            FROM floors
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND level_index = %(level_index)s
            """,
            parameters,
        )
        return self._floor_from_row(row) if row else None

    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, floor_code, code, name, rows, columns,
                   zone_codes, coordinate_x, coordinate_y, coordinate_z, status
            FROM rooms
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "code": Code.from_value(room, "room code").value,
            },
        )
        return self._room_from_row(row) if row else None

    def find_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> RoomZone | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   name, rows, columns, status
            FROM room_zones
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "code": Code.from_value(zone, "zone code").value,
            },
        )
        return self._zone_from_row(row) if row else None

    def find_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> Rack | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   row_code, column_code, zone_code, units,
                   coordinate_x, coordinate_y, coordinate_z, usable_faces,
                   max_weight_kg, power_capacity_watts, status
            FROM racks
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "code": Code.from_value(rack, "rack code").value,
            },
        )
        return self._rack_from_row(row) if row else None

    def find_patch_panel(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
        patch_panel: str,
    ) -> PatchPanel | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, rack_code, code,
                   rack_face, u_position, u_height, port_count, connector, medium, label
            FROM dcim_patch_panels
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
                "code": Code.from_value(patch_panel, "patch panel code").value,
            },
        )
        return self._patch_panel_from_row(row) if row else None

    def find_dcim_port(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimPort | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, owner_type, owner_code, port_name, site_code,
                   building_code, room_code, connector, medium, enabled
            FROM dcim_ports
            WHERE tenant_id = %(tenant_id)s AND owner_type = %(owner_type)s
              AND owner_code = %(owner_code)s AND port_name = %(port_name)s
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": endpoint.owner_type.value,
                "owner_code": endpoint.owner_code.value,
                "port_name": endpoint.port_name.value,
            },
        )
        return self._dcim_port_from_row(row) if row else None

    def find_dcim_cable(self, tenant_id: TenantId, cable_id: str) -> DcimCable | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                   b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                   length_m, label
            FROM dcim_cables
            WHERE tenant_id = %(tenant_id)s AND cable_id = %(cable_id)s
            """,
            {"tenant_id": tenant_id.value, "cable_id": Code.from_value(cable_id).value},
        )
        return self._dcim_cable_from_row(row) if row else None

    def find_active_dcim_cable_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> DcimCable | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                   b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                   length_m, label
            FROM dcim_cables
            WHERE tenant_id = %(tenant_id)s AND status IN ('planned', 'installed')
              AND (
                (a_owner_type = %(owner_type)s AND a_owner_code = %(owner_code)s
                 AND a_port_name = %(port_name)s)
                OR (b_owner_type = %(owner_type)s AND b_owner_code = %(owner_code)s
                    AND b_port_name = %(port_name)s)
              )
            ORDER BY cable_id
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": endpoint.owner_type.value,
                "owner_code": endpoint.owner_code.value,
                "port_name": endpoint.port_name.value,
            },
        )
        return self._dcim_cable_from_row(row) if row else None

    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                   row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                   coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s AND asset_tag = %(asset_tag)s
            """,
            {
                "tenant_id": tenant_id.value,
                "asset_tag": Code.from_value(asset_tag, "asset tag").value,
            },
        )
        return self._equipment_from_row(row) if row else None

    def find_power_device(self, tenant_id: TenantId, code: str) -> PowerDevice | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, code, kind, site_code, building_code, room_code,
                   rack_code, side, capacity_watts, derating_percent, input_source,
                   output_voltage, label
            FROM dcim_power_devices
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "code": Code.from_value(code, "power device code").value,
            },
        )
        return self._power_device_from_row(row) if row else None

    def find_power_circuit(self, tenant_id: TenantId, circuit_id: str) -> PowerCircuit | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                   room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                   redundancy_group, label
            FROM dcim_power_circuits
            WHERE tenant_id = %(tenant_id)s AND circuit_id = %(circuit_id)s
            """,
            {
                "tenant_id": tenant_id.value,
                "circuit_id": Code.from_value(circuit_id, "power circuit id").value,
            },
        )
        return self._power_circuit_from_row(row) if row else None

    def find_cooling_zone(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        zone: str,
    ) -> CoolingZone | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, zone_code, role,
                   cooling_capacity_watts, supply_temperature_c, return_temperature_c, label
            FROM dcim_cooling_zones
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND zone_code = %(zone_code)s
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "zone_code": Code.from_value(zone, "zone code").value,
            },
        )
        return self._cooling_zone_from_row(row) if row else None

    def list_equipment_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[Equipment, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                   row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                   coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY rack_face NULLS FIRST, u_position NULLS FIRST, asset_tag
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._equipment_from_row(row) for row in rows)

    def list_racks_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        include_retired: bool = False,
    ) -> tuple[Rack, ...]:
        query = """
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   row_code, column_code, zone_code, units,
                   coordinate_x, coordinate_y, coordinate_z, usable_faces,
                   max_weight_kg, power_capacity_watts, status
            FROM racks
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
            ORDER BY row_code, column_code, code
            """
        params = {
            "tenant_id": tenant_id.value,
            "site_code": Code.from_value(site, "site code").value,
            "building_code": Code.from_value(building, "building code").value,
            "room_code": Code.from_value(room, "room code").value,
        }
        if not include_retired:
            query = """
            SELECT id, tenant_id, site_code, building_code, floor_code, room_code, code,
                   row_code, column_code, zone_code, units,
                   coordinate_x, coordinate_y, coordinate_z, usable_faces,
                   max_weight_kg, power_capacity_watts, status
            FROM racks
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
              AND status = %(status)s
            ORDER BY row_code, column_code, code
            """
            params["status"] = "active"
        rows = self._fetch_all(query, params)
        return tuple(self._rack_from_row(row) for row in rows)

    def list_patch_panels_in_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PatchPanel, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, site_code, building_code, room_code, rack_code, code,
                   rack_face, u_position, u_height, port_count, connector, medium, label
            FROM dcim_patch_panels
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY rack_face, u_position, code
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._patch_panel_from_row(row) for row in rows)

    def list_dcim_ports_by_owner(
        self,
        tenant_id: TenantId,
        owner_type: str,
        owner_code: str,
    ) -> tuple[DcimPort, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, owner_type, owner_code, port_name, site_code,
                   building_code, room_code, connector, medium, enabled
            FROM dcim_ports
            WHERE tenant_id = %(tenant_id)s AND owner_type = %(owner_type)s
              AND owner_code = %(owner_code)s
            ORDER BY port_name
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": DcimPortOwnerType.from_value(owner_type).value,
                "owner_code": Code.from_value(owner_code).value,
            },
        )
        return tuple(self._dcim_port_from_row(row) for row in rows)

    def list_dcim_cables_by_endpoint(
        self,
        tenant_id: TenantId,
        endpoint: DcimPortEndpoint,
    ) -> tuple[DcimCable, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, cable_id, a_owner_type, a_owner_code, a_port_name,
                   b_owner_type, b_owner_code, b_port_name, medium, status, path_segments,
                   length_m, label
            FROM dcim_cables
            WHERE tenant_id = %(tenant_id)s AND (
                (a_owner_type = %(owner_type)s AND a_owner_code = %(owner_code)s
                 AND a_port_name = %(port_name)s)
                OR (b_owner_type = %(owner_type)s AND b_owner_code = %(owner_code)s
                    AND b_port_name = %(port_name)s)
              )
            ORDER BY cable_id
            """,
            {
                "tenant_id": tenant_id.value,
                "owner_type": endpoint.owner_type.value,
                "owner_code": endpoint.owner_code.value,
                "port_name": endpoint.port_name.value,
            },
        )
        return tuple(self._dcim_cable_from_row(row) for row in rows)

    def list_equipment_in_room(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
    ) -> tuple[Equipment, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, name, site_code, building_code, floor_code, room_code,
                   row_code, column_code, zone_code, rack_code, u_position, rack_face, u_height,
                   coordinate_x, coordinate_y, coordinate_z
            FROM equipment
            WHERE tenant_id = %(tenant_id)s
              AND site_code = %(site_code)s
              AND building_code = %(building_code)s
              AND room_code = %(room_code)s
            ORDER BY row_code, column_code, rack_code NULLS FIRST, asset_tag
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
            },
        )
        return tuple(self._equipment_from_row(row) for row in rows)

    def list_power_circuits_by_source(
        self,
        tenant_id: TenantId,
        source_device: str,
    ) -> tuple[PowerCircuit, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                   room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                   redundancy_group, label
            FROM dcim_power_circuits
            WHERE tenant_id = %(tenant_id)s AND source_device_code = %(source_device_code)s
            ORDER BY circuit_id
            """,
            {
                "tenant_id": tenant_id.value,
                "source_device_code": Code.from_value(source_device, "power device code").value,
            },
        )
        return tuple(self._power_circuit_from_row(row) for row in rows)

    def list_power_circuits_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[PowerCircuit, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, circuit_id, source_device_code, site_code, building_code,
                   room_code, rack_code, side, capacity_watts, breaker_rating_amps,
                   redundancy_group, label
            FROM dcim_power_circuits
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY side, circuit_id
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._power_circuit_from_row(row) for row in rows)

    def list_power_reservations_for_circuit(
        self,
        tenant_id: TenantId,
        circuit_id: str,
    ) -> tuple[RackPowerReservation, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, circuit_id, side, site_code, building_code,
                   room_code, rack_code, expected_watts, label
            FROM dcim_power_reservations
            WHERE tenant_id = %(tenant_id)s AND circuit_id = %(circuit_id)s
            ORDER BY asset_tag, side
            """,
            {
                "tenant_id": tenant_id.value,
                "circuit_id": Code.from_value(circuit_id, "power circuit id").value,
            },
        )
        return tuple(self._power_reservation_from_row(row) for row in rows)

    def list_power_reservations_for_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> tuple[RackPowerReservation, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asset_tag, circuit_id, side, site_code, building_code,
                   room_code, rack_code, expected_watts, label
            FROM dcim_power_reservations
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s
              AND building_code = %(building_code)s AND room_code = %(room_code)s
              AND rack_code = %(rack_code)s
            ORDER BY side, asset_tag
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": Code.from_value(site, "site code").value,
                "building_code": Code.from_value(building, "building code").value,
                "room_code": Code.from_value(room, "room code").value,
                "rack_code": Code.from_value(rack, "rack code").value,
            },
        )
        return tuple(self._power_reservation_from_row(row) for row in rows)

    def _site_from_row(self, row: Mapping[str, object]) -> Site:
        return Site(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            code=Code.from_value(str(row["code"]), "site code"),
            name=Name.from_value(str(row["name"]), "site name"),
            country=str(row["country"]),
            city=str(row["city"]),
            region=str(row.get("region") or ""),
            status=DcimLifecycleStatus.from_value(
                str(row.get("status") or "active"), "site status"
            ),
        )

    def _building_from_row(self, row: Mapping[str, object]) -> Building:
        building_type = BuildingType.from_value(str(row.get("building_type") or "simple"))
        return Building(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            code=Code.from_value(str(row["code"]), "building code"),
            name=Name.from_value(str(row["name"]), "building name"),
            building_type=building_type,
            initial_level=int(str(row["initial_level"]))
            if building_type.requires_floor() and row.get("initial_level") is not None
            else None,
            final_level=int(str(row["final_level"]))
            if building_type.requires_floor() and row.get("final_level") is not None
            else None,
            status=DcimLifecycleStatus.from_value(
                str(row.get("status") or "active"), "building status"
            ),
        )

    def _floor_from_row(self, row: Mapping[str, object]) -> Floor:
        return Floor(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            code=Code.from_value(str(row["code"]), "floor code"),
            name=Name.from_value(str(row["name"]), "floor name"),
            level_index=self._row_int(row, "level_index"),
            status=DcimLifecycleStatus.from_value(
                str(row.get("status") or "active"), "floor status"
            ),
        )

    def _room_from_row(self, row: Mapping[str, object]) -> Room:
        coordinates = Coordinates3D.from_values(
            self._float_or_none(row.get("coordinate_x")),
            self._float_or_none(row.get("coordinate_y")),
            self._float_or_none(row.get("coordinate_z")),
        )
        zone_values = self._row_optional_sequence(row, "zone_codes", ())
        return Room(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            code=Code.from_value(str(row["code"]), "room code"),
            name=Name.from_value(str(row["name"]), "room name"),
            rows=tuple(str(value) for value in self._row_sequence(row, "rows")),
            columns=tuple(str(value) for value in self._row_sequence(row, "columns")),
            floor_code=(
                Code.from_value(str(row["floor_code"]), "floor code")
                if row.get("floor_code") is not None
                else None
            ),
            zone_codes=tuple(Code.from_value(str(value), "zone code") for value in zone_values),
            coordinates=coordinates,
            status=DcimLifecycleStatus.from_value(
                str(row.get("status") or "active"), "room status"
            ),
        )

    def _zone_from_row(self, row: Mapping[str, object]) -> RoomZone:
        return RoomZone(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            floor_code=Code.from_value(str(row["floor_code"]), "floor code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            code=Code.from_value(str(row["code"]), "zone code"),
            name=Name.from_value(str(row["name"]), "zone name"),
            rows=tuple(str(value) for value in self._row_sequence(row, "rows")),
            columns=tuple(str(value) for value in self._row_sequence(row, "columns")),
            status=DcimLifecycleStatus.from_value(
                str(row.get("status") or "active"), "zone status"
            ),
        )

    def _rack_from_row(self, row: Mapping[str, object]) -> Rack:
        coordinates = Coordinates3D.from_values(
            self._float_or_none(row["coordinate_x"]),
            self._float_or_none(row["coordinate_y"]),
            self._float_or_none(row["coordinate_z"]),
        )
        return Rack(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            code=Code.from_value(str(row["code"]), "rack code"),
            row=str(row["row_code"]),
            column=str(row["column_code"]),
            units=self._row_int(row, "units"),
            coordinates=coordinates,
            floor_code=(
                Code.from_value(str(row["floor_code"]), "floor code")
                if row.get("floor_code") is not None
                else None
            ),
            zone_code=(
                Code.from_value(str(row["zone_code"]), "zone code")
                if row.get("zone_code") is not None
                else None
            ),
            usable_faces=tuple(
                RackFace.from_value(str(face)) or RackFace.FRONT
                for face in self._row_optional_sequence(row, "usable_faces", ("front",))
            ),
            max_weight_kg=(
                self._float_or_none(row.get("max_weight_kg"))
                if row.get("max_weight_kg") is not None
                else None
            ),
            power_capacity_watts=(
                self._row_int(row, "power_capacity_watts")
                if row.get("power_capacity_watts") is not None
                else None
            ),
            status=DcimLifecycleStatus.from_value(
                str(row.get("status") or "active"), "rack status"
            ),
        )

    def _equipment_from_row(self, row: Mapping[str, object]) -> Equipment:
        coordinates = Coordinates3D.from_values(
            self._float_or_none(row["coordinate_x"]),
            self._float_or_none(row["coordinate_y"]),
            self._float_or_none(row["coordinate_z"]),
        )
        location = EquipmentLocation.create(
            site_code=str(row["site_code"]),
            building_code=str(row["building_code"]),
            room_code=str(row["room_code"]),
            row=str(row["row_code"]),
            column=str(row["column_code"]),
            rack_code=str(row["rack_code"]) if row["rack_code"] is not None else None,
            u_position=self._row_int(row, "u_position") if row["u_position"] is not None else None,
            coordinates=coordinates,
            floor_code=str(row["floor_code"]) if row.get("floor_code") is not None else None,
            zone_code=str(row["zone_code"]) if row.get("zone_code") is not None else None,
            rack_face=str(row["rack_face"]) if row.get("rack_face") is not None else None,
            u_height=self._row_int(row, "u_height") if row.get("u_height") is not None else None,
        )
        return Equipment(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            asset_tag=Code.from_value(str(row["asset_tag"]), "asset tag"),
            name=Name.from_value(str(row["name"]), "equipment name"),
            location=location,
        )

    def _patch_panel_from_row(self, row: Mapping[str, object]) -> PatchPanel:
        rack_face = RackFace.from_value(str(row["rack_face"]))
        if rack_face is None:
            raise ValidationError("postgresql patch panel row has no rack face")
        return PatchPanel(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code"),
            code=Code.from_value(str(row["code"]), "patch panel code"),
            rack_face=rack_face,
            u_position=self._row_int(row, "u_position"),
            u_height=self._row_int(row, "u_height"),
            port_count=self._row_int(row, "port_count"),
            connector=DcimConnectorType.from_value(str(row["connector"])),
            medium=DcimCableMedium.from_value(str(row["medium"])),
            label=str(row.get("label") or ""),
        )

    def _dcim_port_from_row(self, row: Mapping[str, object]) -> DcimPort:
        return DcimPort(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            endpoint=DcimPortEndpoint.create(
                str(row["owner_type"]),
                str(row["owner_code"]),
                str(row["port_name"]),
            ),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            connector=DcimConnectorType.from_value(str(row["connector"])),
            medium=DcimCableMedium.from_value(str(row["medium"])),
            enabled=bool(row["enabled"]),
        )

    def _dcim_cable_from_row(self, row: Mapping[str, object]) -> DcimCable:
        return DcimCable(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            cable_id=Code.from_value(str(row["cable_id"]), "cable id"),
            a_endpoint=DcimPortEndpoint.create(
                str(row["a_owner_type"]),
                str(row["a_owner_code"]),
                str(row["a_port_name"]),
            ),
            b_endpoint=DcimPortEndpoint.create(
                str(row["b_owner_type"]),
                str(row["b_owner_code"]),
                str(row["b_port_name"]),
            ),
            medium=DcimCableMedium.from_value(str(row["medium"])),
            status=DcimCableStatus.from_value(str(row["status"])),
            path=self._dcim_cable_path_from_row(row),
            length_m=self._float_or_none(row.get("length_m")),
            label=str(row.get("label") or ""),
        )

    def _dcim_cable_path_from_row(
        self,
        row: Mapping[str, object],
    ) -> tuple[DcimCablePathSegment, ...]:
        raw_path = row.get("path_segments")
        decoded = json.loads(raw_path) if isinstance(raw_path, str) else raw_path
        path_items = cast(Sequence[Mapping[str, object]], decoded or ())
        return tuple(
            DcimCablePathSegment.create(
                order=self._row_int(item, "order"),
                kind=str(item.get("kind") or "path"),
                label=str(item["label"]),
            )
            for item in path_items
        )

    def _power_device_from_row(self, row: Mapping[str, object]) -> PowerDevice:
        return PowerDevice(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            code=Code.from_value(str(row["code"]), "power device code"),
            kind=PowerDeviceKind.from_value(str(row["kind"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code")
            if row.get("rack_code") is not None
            else None,
            side=PowerFeedSide.from_value(str(row["side"]))
            if row.get("side") is not None
            else None,
            capacity_watts=self._row_int(row, "capacity_watts"),
            derating_percent=self._row_int(row, "derating_percent"),
            input_source=str(row["input_source"]),
            output_voltage=self._row_int(row, "output_voltage"),
            label=str(row.get("label") or ""),
        )

    def _power_circuit_from_row(self, row: Mapping[str, object]) -> PowerCircuit:
        return PowerCircuit(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            circuit_id=Code.from_value(str(row["circuit_id"]), "power circuit id"),
            source_device_code=Code.from_value(str(row["source_device_code"]), "power device code"),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code"),
            side=PowerFeedSide.from_value(str(row["side"])),
            capacity_watts=self._row_int(row, "capacity_watts"),
            breaker_rating_amps=self._row_int(row, "breaker_rating_amps"),
            redundancy_group=str(row["redundancy_group"]),
            label=str(row.get("label") or ""),
        )

    def _cooling_zone_from_row(self, row: Mapping[str, object]) -> CoolingZone:
        return CoolingZone(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            zone_code=Code.from_value(str(row["zone_code"]), "zone code"),
            role=CoolingRole.from_value(str(row["role"])),
            cooling_capacity_watts=self._row_int(row, "cooling_capacity_watts"),
            supply_temperature_c=self._row_float(row, "supply_temperature_c"),
            return_temperature_c=self._row_float(row, "return_temperature_c"),
            label=str(row.get("label") or ""),
        )

    def _power_reservation_from_row(self, row: Mapping[str, object]) -> RackPowerReservation:
        return RackPowerReservation(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            asset_tag=Code.from_value(str(row["asset_tag"]), "asset tag"),
            circuit_id=Code.from_value(str(row["circuit_id"]), "power circuit id"),
            side=PowerFeedSide.from_value(str(row["side"])),
            site_code=Code.from_value(str(row["site_code"]), "site code"),
            building_code=Code.from_value(str(row["building_code"]), "building code"),
            room_code=Code.from_value(str(row["room_code"]), "room code"),
            rack_code=Code.from_value(str(row["rack_code"]), "rack code"),
            expected_watts=self._row_int(row, "expected_watts"),
            label=str(row.get("label") or ""),
        )

    def _float_or_none(self, value: object) -> float | None:
        return None if value is None else float(str(value))


class PostgreSQLIpamRepository(PostgreSQLRepositoryBase, IpamRepository):
    def add_vrf(self, vrf: Vrf) -> None:
        self._ensure_tenant(vrf.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO vrfs (id, tenant_id, name, route_distinguisher)
            VALUES (%(id)s, %(tenant_id)s, %(name)s, %(route_distinguisher)s)
            ON CONFLICT (tenant_id, name) DO NOTHING
            """,
            {
                "id": vrf.id.value,
                "tenant_id": vrf.tenant_id.value,
                "name": vrf.name.value,
                "route_distinguisher": vrf.route_distinguisher,
            },
        )

    def add_or_get_vrf(self, vrf: Vrf) -> Vrf:
        self._ensure_tenant(vrf.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO vrfs (id, tenant_id, name, route_distinguisher)
            VALUES (%(id)s, %(tenant_id)s, %(name)s, %(route_distinguisher)s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET route_distinguisher = COALESCE(
                vrfs.route_distinguisher,
                EXCLUDED.route_distinguisher
            )
            RETURNING id, tenant_id, name, route_distinguisher
            """,
            {
                "id": vrf.id.value,
                "tenant_id": vrf.tenant_id.value,
                "name": vrf.name.value,
                "route_distinguisher": vrf.route_distinguisher,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return vrf after upsert")
        return self._vrf_from_row(row)

    def list_vrfs(self, tenant_id: TenantId) -> tuple[Vrf, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, route_distinguisher
            FROM vrfs
            WHERE tenant_id = %(tenant_id)s
            ORDER BY name
            """,
            {"tenant_id": tenant_id.value},
        )
        return tuple(self._vrf_from_row(row) for row in rows)

    def add_aggregate(self, aggregate: IpAggregate) -> IpAggregate:
        self._ensure_tenant(aggregate.tenant_id)
        self.add_vrf(Vrf.create(aggregate.tenant_id, aggregate.vrf_name.value))
        row = self._fetch_one(
            """
            INSERT INTO ip_aggregates (id, tenant_id, vrf_name, cidr, family, description)
            VALUES (%(id)s, %(tenant_id)s, %(vrf_name)s, %(cidr)s, %(family)s, %(description)s)
            ON CONFLICT (tenant_id, vrf_name, cidr)
            DO UPDATE SET description = ip_aggregates.description
            RETURNING id, tenant_id, vrf_name, cidr, description
            """,
            {
                "id": aggregate.id.value,
                "tenant_id": aggregate.tenant_id.value,
                "vrf_name": aggregate.vrf_name.value,
                "cidr": str(aggregate.network),
                "family": aggregate.network.version,
                "description": aggregate.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return aggregate after upsert")
        return self._aggregate_from_row(row)

    def list_aggregates(self, tenant_id: TenantId, vrf_name: str) -> tuple[IpAggregate, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, cidr, description
            FROM ip_aggregates
            WHERE tenant_id = %(tenant_id)s AND vrf_name = %(vrf_name)s
            ORDER BY cidr
            """,
            {"tenant_id": tenant_id.value, "vrf_name": Name.from_value(vrf_name, "vrf name").value},
        )
        return tuple(self._aggregate_from_row(row) for row in rows)

    def get_or_create_prefix(self, prefix: Prefix) -> Prefix:
        self._ensure_tenant(prefix.tenant_id)
        self.add_vrf(Vrf.create(prefix.tenant_id, prefix.vrf_name.value))
        row = self._fetch_one(
            """
            INSERT INTO prefixes (
                id, tenant_id, vrf_name, cidr, family, first_usable, last_usable, description
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(cidr)s, %(family)s,
                %(first_usable)s, %(last_usable)s, %(description)s
            )
            ON CONFLICT (tenant_id, vrf_name, cidr) DO UPDATE SET description = prefixes.description
            RETURNING id, tenant_id, vrf_name, cidr, description
            """,
            {
                "id": prefix.id.value,
                "tenant_id": prefix.tenant_id.value,
                "vrf_name": prefix.vrf_name.value,
                "cidr": str(prefix.network),
                "family": prefix.network.version,
                "first_usable": str(ipaddress.ip_address(prefix.first_usable_int)),
                "last_usable": str(ipaddress.ip_address(prefix.last_usable_int)),
                "description": prefix.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return prefix after upsert")
        return self._prefix_from_row(row)

    def list_prefixes(self, tenant_id: TenantId, vrf_name: str) -> tuple[Prefix, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, cidr, description
            FROM prefixes
            WHERE tenant_id = %(tenant_id)s AND vrf_name = %(vrf_name)s
            ORDER BY cidr
            """,
            {"tenant_id": tenant_id.value, "vrf_name": Name.from_value(vrf_name, "vrf name").value},
        )
        return tuple(self._prefix_from_row(row) for row in rows)

    def add_range(self, ip_range: IpRange) -> IpRange:
        row = self._fetch_one(
            """
            INSERT INTO ip_ranges (
                id, tenant_id, vrf_name, prefix_cidr, start_address, end_address,
                purpose, description
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(start_address)s,
                %(end_address)s, %(purpose)s, %(description)s
            )
            ON CONFLICT (tenant_id, vrf_name, prefix_cidr, start_address, end_address)
            DO UPDATE SET description = ip_ranges.description
            RETURNING id, tenant_id, vrf_name, prefix_cidr, start_address, end_address,
                purpose, description
            """,
            {
                "id": ip_range.id.value,
                "tenant_id": ip_range.tenant_id.value,
                "vrf_name": ip_range.vrf_name.value,
                "prefix_cidr": ip_range.prefix,
                "start_address": str(ip_range.start),
                "end_address": str(ip_range.end),
                "purpose": ip_range.purpose.value,
                "description": ip_range.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return range after upsert")
        return self._range_from_row(row)

    def list_ranges(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpRange, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, start_address, end_address,
                purpose, description
            FROM ip_ranges
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND prefix_cidr = %(prefix_cidr)s
            ORDER BY start_address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "prefix_cidr": prefix_cidr,
            },
        )
        return tuple(self._range_from_row(row) for row in rows)

    def upsert_address_record(self, record: IpAddressRecord) -> IpAddressRecord:
        row = self._fetch_one(
            """
            INSERT INTO ip_address_records (
                id, tenant_id, vrf_name, prefix_cidr, address, hostname, interface_name, status
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(address)s,
                %(hostname)s, %(interface_name)s, %(status)s
            )
            ON CONFLICT (tenant_id, vrf_name, address)
            DO UPDATE SET
                prefix_cidr = EXCLUDED.prefix_cidr,
                hostname = EXCLUDED.hostname,
                interface_name = EXCLUDED.interface_name,
                status = EXCLUDED.status
            RETURNING id, tenant_id, vrf_name, prefix_cidr, address, hostname,
                interface_name, status
            """,
            {
                "id": record.id.value,
                "tenant_id": record.tenant_id.value,
                "vrf_name": record.vrf_name.value,
                "prefix_cidr": record.prefix,
                "address": str(record.address),
                "hostname": record.hostname,
                "interface_name": record.interface_name.value if record.interface_name else None,
                "status": record.status.value,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return address record after upsert")
        return self._address_record_from_row(row)

    def list_address_records(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpAddressRecord, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, address, hostname, interface_name, status
            FROM ip_address_records
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND prefix_cidr = %(prefix_cidr)s
            ORDER BY address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "prefix_cidr": prefix_cidr,
            },
        )
        return tuple(self._address_record_from_row(row) for row in rows)

    def acquire_allocation_lock(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> None:
        normalized_vrf = Name.from_value(vrf_name, "vrf name").value
        normalized_prefix = str(ipaddress.ip_network(prefix_cidr.strip(), strict=True))
        self._execute_without_result(
            """
            SELECT pg_advisory_xact_lock(
                hashtextextended(%(lock_scope)s, 0)
            )
            """,
            {"lock_scope": f"ipam:{tenant_id.value}:{normalized_vrf}:{normalized_prefix}"},
        )

    def find_reservation_by_key(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        idempotency_key: str,
    ) -> IpReservation | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, address, hostname, idempotency_key
            FROM ip_reservations
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND idempotency_key = %(idempotency_key)s
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "idempotency_key": idempotency_key.strip(),
            },
        )
        return self._reservation_from_row(row) if row else None

    def list_reservations(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpReservation, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, prefix_cidr, address, hostname, idempotency_key
            FROM ip_reservations
            WHERE tenant_id = %(tenant_id)s
              AND vrf_name = %(vrf_name)s
              AND prefix_cidr = %(prefix_cidr)s
            ORDER BY address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value,
                "prefix_cidr": prefix_cidr,
            },
        )
        return tuple(self._reservation_from_row(row) for row in rows)

    def add_reservation(self, reservation: IpReservation) -> None:
        try:
            self._execute_without_result(
                """
                INSERT INTO ip_reservations (
                    id, tenant_id, vrf_name, prefix_cidr, address, hostname, idempotency_key
                ) VALUES (
                    %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(address)s,
                    %(hostname)s, %(idempotency_key)s
                )
                """,
                {
                    "id": reservation.id.value,
                    "tenant_id": reservation.tenant_id.value,
                    "vrf_name": reservation.vrf_name.value,
                    "prefix_cidr": reservation.prefix,
                    "address": str(reservation.address),
                    "hostname": reservation.hostname,
                    "idempotency_key": reservation.idempotency_key,
                },
            )
        except Exception as exc:
            raise ConflictError(
                f"duplicate or invalid ip reservation: {reservation.address}"
            ) from exc

    def add_dns_observation(self, record: ObservedDnsRecord) -> ObservedDnsRecord:
        self._ensure_tenant(record.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_dns_observations (
                id, tenant_id, vrf_name, hostname, address, ptr_hostname, source
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(hostname)s, %(address)s,
                %(ptr_hostname)s, %(source)s
            )
            ON CONFLICT (tenant_id, vrf_name, hostname, address) DO UPDATE SET
                ptr_hostname = EXCLUDED.ptr_hostname,
                source = EXCLUDED.source
            RETURNING id, tenant_id, vrf_name, hostname, address, ptr_hostname, source
            """,
            {
                "id": record.id.value,
                "tenant_id": record.tenant_id.value,
                "vrf_name": record.vrf_name.value,
                "hostname": record.hostname,
                "address": str(record.address),
                "ptr_hostname": record.ptr_hostname,
                "source": record.source,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return DNS observation after upsert")
        return self._dns_observation_from_row(row)

    def list_dns_observations(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[ObservedDnsRecord, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, hostname, address, ptr_hostname, source
            FROM ipam_dns_observations
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY vrf_name, hostname, address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._dns_observation_from_row(row) for row in rows)

    def add_dhcp_lease(self, lease: ObservedDhcpLease) -> ObservedDhcpLease:
        self._ensure_tenant(lease.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_dhcp_leases (
                id, tenant_id, vrf_name, prefix_cidr, address,
                mac_address, hostname, source, active
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(prefix_cidr)s, %(address)s,
                %(mac_address)s, %(hostname)s, %(source)s, %(active)s
            )
            ON CONFLICT (tenant_id, vrf_name, prefix_cidr, address, mac_address) DO UPDATE SET
                hostname = EXCLUDED.hostname,
                source = EXCLUDED.source,
                active = EXCLUDED.active
            RETURNING
                id, tenant_id, vrf_name, prefix_cidr, address,
                mac_address, hostname, source, active
            """,
            {
                "id": lease.id.value,
                "tenant_id": lease.tenant_id.value,
                "vrf_name": lease.vrf_name.value,
                "prefix_cidr": lease.prefix,
                "address": str(lease.address),
                "mac_address": lease.mac_address,
                "hostname": lease.hostname,
                "source": lease.source,
                "active": lease.active,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return DHCP lease after upsert")
        return self._dhcp_lease_from_row(row)

    def list_dhcp_leases(
        self, tenant_id: TenantId, vrf_name: str | None = None, active_only: bool = True
    ) -> tuple[ObservedDhcpLease, ...]:
        rows = self._fetch_all(
            """
            SELECT
                id, tenant_id, vrf_name, prefix_cidr, address,
                mac_address, hostname, source, active
            FROM ipam_dhcp_leases
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
              AND (%(active_only)s = false OR active = true)
            ORDER BY vrf_name, address, mac_address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
                "active_only": active_only,
            },
        )
        return tuple(self._dhcp_lease_from_row(row) for row in rows)

    def add_vlan_group(self, group: VlanGroup) -> VlanGroup:
        self._ensure_tenant(group.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_vlan_groups (id, tenant_id, name, scope, description)
            VALUES (%(id)s, %(tenant_id)s, %(name)s, %(scope)s, %(description)s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET description = ipam_vlan_groups.description
            RETURNING id, tenant_id, name, scope, description
            """,
            {
                "id": group.id.value,
                "tenant_id": group.tenant_id.value,
                "name": group.name.value,
                "scope": group.scope.value if group.scope else None,
                "description": group.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return VLAN group after upsert")
        return self._vlan_group_from_row(row)

    def list_vlan_groups(self, tenant_id: TenantId) -> tuple[VlanGroup, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, scope, description
            FROM ipam_vlan_groups
            WHERE tenant_id = %(tenant_id)s
            ORDER BY name
            """,
            {"tenant_id": tenant_id.value},
        )
        return tuple(self._vlan_group_from_row(row) for row in rows)

    def add_vlan(self, vlan: Vlan) -> Vlan:
        self._ensure_tenant(vlan.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_vlans (
                id, tenant_id, group_name, vlan_id, name, vrf_name, vni, description
            )
            VALUES (
                %(id)s, %(tenant_id)s, %(group_name)s, %(vlan_id)s,
                %(name)s, %(vrf_name)s, %(vni)s, %(description)s
            )
            ON CONFLICT (tenant_id, group_name, vlan_id)
            DO UPDATE SET description = ipam_vlans.description
            RETURNING id, tenant_id, group_name, vlan_id, name, vrf_name, vni, description
            """,
            {
                "id": vlan.id.value,
                "tenant_id": vlan.tenant_id.value,
                "group_name": vlan.group_name.value,
                "vlan_id": vlan.vlan_id,
                "name": vlan.name.value,
                "vrf_name": vlan.vrf_name.value if vlan.vrf_name else None,
                "vni": vlan.vni,
                "description": vlan.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return VLAN after upsert")
        return self._vlan_from_row(row)

    def list_vlans(self, tenant_id: TenantId, vrf_name: str | None = None) -> tuple[Vlan, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, group_name, vlan_id, name, vrf_name, vni, description
            FROM ipam_vlans
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY group_name, vlan_id
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._vlan_from_row(row) for row in rows)

    def add_vxlan_vni(self, vni: VxlanVni) -> VxlanVni:
        self._ensure_tenant(vni.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_vxlan_vnis (
                id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vni)s, %(name)s, %(vrf_name)s,
                %(route_targets_import)s, %(route_targets_export)s, %(description)s
            )
            ON CONFLICT (tenant_id, vni)
            DO UPDATE SET description = ipam_vxlan_vnis.description
            RETURNING id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            """,
            {
                "id": vni.id.value,
                "tenant_id": vni.tenant_id.value,
                "vni": vni.vni,
                "name": vni.name.value,
                "vrf_name": vni.vrf_name.value,
                "route_targets_import": list(vni.route_targets_import),
                "route_targets_export": list(vni.route_targets_export),
                "description": vni.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return VXLAN VNI after upsert")
        return self._vxlan_vni_from_row(row)

    def find_vxlan_vni(self, tenant_id: TenantId, vni: int) -> VxlanVni | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            FROM ipam_vxlan_vnis
            WHERE tenant_id = %(tenant_id)s AND vni = %(vni)s
            """,
            {"tenant_id": tenant_id.value, "vni": vni},
        )
        return self._vxlan_vni_from_row(row) if row else None

    def list_vxlan_vnis(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[VxlanVni, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vni, name, vrf_name, route_targets_import,
                route_targets_export, description
            FROM ipam_vxlan_vnis
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY vni
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._vxlan_vni_from_row(row) for row in rows)

    def add_asn(self, asn: AutonomousSystem) -> AutonomousSystem:
        self._ensure_tenant(asn.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_autonomous_systems (id, tenant_id, asn, name, description)
            VALUES (%(id)s, %(tenant_id)s, %(asn)s, %(name)s, %(description)s)
            ON CONFLICT (tenant_id, asn)
            DO UPDATE SET description = ipam_autonomous_systems.description
            RETURNING id, tenant_id, asn, name, description
            """,
            {
                "id": asn.id.value,
                "tenant_id": asn.tenant_id.value,
                "asn": asn.number,
                "name": asn.name.value,
                "description": asn.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return ASN after upsert")
        return self._asn_from_row(row)

    def find_asn(self, tenant_id: TenantId, number: int) -> AutonomousSystem | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, asn, name, description
            FROM ipam_autonomous_systems
            WHERE tenant_id = %(tenant_id)s AND asn = %(asn)s
            """,
            {"tenant_id": tenant_id.value, "asn": number},
        )
        return self._asn_from_row(row) if row else None

    def list_asns(self, tenant_id: TenantId) -> tuple[AutonomousSystem, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, asn, name, description
            FROM ipam_autonomous_systems
            WHERE tenant_id = %(tenant_id)s
            ORDER BY asn
            """,
            {"tenant_id": tenant_id.value},
        )
        return tuple(self._asn_from_row(row) for row in rows)

    def add_bgp_peer(self, peer: BgpPeer) -> BgpPeer:
        self._ensure_tenant(peer.tenant_id)
        row = self._fetch_one(
            """
            INSERT INTO ipam_bgp_peers (
                id, tenant_id, vrf_name, local_asn, remote_asn, peer_address,
                address_family, route_targets_import, route_targets_export, description
            ) VALUES (
                %(id)s, %(tenant_id)s, %(vrf_name)s, %(local_asn)s, %(remote_asn)s,
                %(peer_address)s, %(address_family)s, %(route_targets_import)s,
                %(route_targets_export)s, %(description)s
            )
            ON CONFLICT (tenant_id, vrf_name, local_asn, peer_address)
            DO UPDATE SET description = ipam_bgp_peers.description
            RETURNING id, tenant_id, vrf_name, local_asn, remote_asn, peer_address,
                address_family, route_targets_import, route_targets_export, description
            """,
            {
                "id": peer.id.value,
                "tenant_id": peer.tenant_id.value,
                "vrf_name": peer.vrf_name.value,
                "local_asn": peer.local_asn,
                "remote_asn": peer.remote_asn,
                "peer_address": str(peer.peer_address),
                "address_family": peer.address_family.value,
                "route_targets_import": list(peer.route_targets_import),
                "route_targets_export": list(peer.route_targets_export),
                "description": peer.description,
            },
        )
        if row is None:
            raise OpenInfraError("postgresql did not return BGP peer after upsert")
        return self._bgp_peer_from_row(row)

    def list_bgp_peers(
        self, tenant_id: TenantId, vrf_name: str | None = None
    ) -> tuple[BgpPeer, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, vrf_name, local_asn, remote_asn, peer_address,
                address_family, route_targets_import, route_targets_export, description
            FROM ipam_bgp_peers
            WHERE tenant_id = %(tenant_id)s
              AND (%(vrf_name)s IS NULL OR vrf_name = %(vrf_name)s)
            ORDER BY vrf_name, local_asn, peer_address
            """,
            {
                "tenant_id": tenant_id.value,
                "vrf_name": Name.from_value(vrf_name, "vrf name").value if vrf_name else None,
            },
        )
        return tuple(self._bgp_peer_from_row(row) for row in rows)

    def _dns_observation_from_row(self, row: Mapping[str, object]) -> ObservedDnsRecord:
        record = ObservedDnsRecord.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["hostname"]),
            str(row["address"]),
            str(row["ptr_hostname"]) if row.get("ptr_hostname") is not None else None,
            str(row.get("source", "postgresql")),
        )
        return ObservedDnsRecord(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=record.tenant_id,
            vrf_name=record.vrf_name,
            hostname=record.hostname,
            address=record.address,
            ptr_hostname=record.ptr_hostname,
            source=record.source,
        )

    def _dhcp_lease_from_row(self, row: Mapping[str, object]) -> ObservedDhcpLease:
        lease = ObservedDhcpLease.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
            str(row["address"]),
            str(row["mac_address"]),
            str(row["hostname"]),
            str(row.get("source", "postgresql")),
            bool(row.get("active", True)),
        )
        return ObservedDhcpLease(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=lease.tenant_id,
            vrf_name=lease.vrf_name,
            prefix=lease.prefix,
            address=lease.address,
            mac_address=lease.mac_address,
            hostname=lease.hostname,
            source=lease.source,
            active=lease.active,
        )

    def _vlan_group_from_row(self, row: Mapping[str, object]) -> VlanGroup:
        return VlanGroup(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=Name.from_value(str(row["name"]), "vlan group name"),
            scope=(
                None
                if row.get("scope") is None
                else Code.from_value(str(row["scope"]), "vlan group scope")
            ),
            description=str(row.get("description") or ""),
        )

    def _vlan_from_row(self, row: Mapping[str, object]) -> Vlan:
        return Vlan(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            group_name=Name.from_value(str(row["group_name"]), "vlan group name"),
            vlan_id=int(str(row["vlan_id"])),
            name=Name.from_value(str(row["name"]), "vlan name"),
            vrf_name=(
                None
                if row.get("vrf_name") is None
                else Name.from_value(str(row["vrf_name"]), "vrf name")
            ),
            vni=None if row.get("vni") is None else int(str(row["vni"])),
            description=str(row.get("description") or ""),
        )

    def _vxlan_vni_from_row(self, row: Mapping[str, object]) -> VxlanVni:
        return VxlanVni(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vni=int(str(row["vni"])),
            name=Name.from_value(str(row["name"]), "vni name"),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            route_targets_import=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_import"])
            ),
            route_targets_export=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_export"])
            ),
            description=str(row.get("description") or ""),
        )

    def _asn_from_row(self, row: Mapping[str, object]) -> AutonomousSystem:
        return AutonomousSystem(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            number=int(str(row["asn"])),
            name=Name.from_value(str(row["name"]), "asn name"),
            description=str(row.get("description") or ""),
        )

    def _bgp_peer_from_row(self, row: Mapping[str, object]) -> BgpPeer:
        return BgpPeer(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            local_asn=int(str(row["local_asn"])),
            remote_asn=int(str(row["remote_asn"])),
            peer_address=ipaddress.ip_address(str(row["peer_address"])),
            address_family=BgpAddressFamily.from_value(str(row["address_family"])),
            route_targets_import=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_import"])
            ),
            route_targets_export=tuple(
                str(value) for value in cast(Sequence[object], row["route_targets_export"])
            ),
            description=str(row.get("description") or ""),
        )

    def _vrf_from_row(self, row: Mapping[str, object]) -> Vrf:
        return Vrf(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=Name.from_value(str(row["name"]), "vrf name"),
            route_distinguisher=(
                None if row.get("route_distinguisher") is None else str(row["route_distinguisher"])
            ),
        )

    def _aggregate_from_row(self, row: Mapping[str, object]) -> IpAggregate:
        return IpAggregate(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            network=ipaddress.ip_network(str(row["cidr"]), strict=True),
            description=str(row["description"] or ""),
        )

    def _prefix_from_row(self, row: Mapping[str, object]) -> Prefix:
        return Prefix(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=Name.from_value(str(row["vrf_name"]), "vrf name"),
            network=ipaddress.ip_network(str(row["cidr"]), strict=True),
            description=str(row["description"] or ""),
        )

    def _range_from_row(self, row: Mapping[str, object]) -> IpRange:
        prefix = Prefix.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
        )
        ip_range = IpRange.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            prefix,
            str(row["start_address"]),
            str(row["end_address"]),
            str(row["purpose"]),
            str(row["description"] or ""),
        )
        return IpRange(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=ip_range.tenant_id,
            vrf_name=ip_range.vrf_name,
            prefix=ip_range.prefix,
            start=ip_range.start,
            end=ip_range.end,
            purpose=ip_range.purpose,
            description=ip_range.description,
        )

    def _address_record_from_row(self, row: Mapping[str, object]) -> IpAddressRecord:
        prefix = Prefix.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
        )
        record = IpAddressRecord.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            prefix,
            str(row["address"]),
            str(row["hostname"]),
            None if row.get("interface_name") is None else str(row["interface_name"]),
            str(row["status"]),
        )
        return IpAddressRecord(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=record.tenant_id,
            vrf_name=record.vrf_name,
            prefix=record.prefix,
            address=record.address,
            hostname=record.hostname,
            interface_name=record.interface_name,
            status=record.status,
        )

    def _reservation_from_row(self, row: Mapping[str, object]) -> IpReservation:
        prefix = Prefix.create(
            TenantId.from_value(str(row["tenant_id"])),
            str(row["vrf_name"]),
            str(row["prefix_cidr"]),
        )
        reservation = IpReservation.create(
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            vrf_name=str(row["vrf_name"]),
            prefix=prefix,
            address=str(row["address"]),
            hostname=str(row["hostname"]),
            idempotency_key=str(row["idempotency_key"]),
        )
        return IpReservation(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=reservation.tenant_id,
            vrf_name=reservation.vrf_name,
            prefix=reservation.prefix,
            address=reservation.address,
            hostname=reservation.hostname,
            idempotency_key=reservation.idempotency_key,
        )


class PostgreSQLDiscoveryRepository(PostgreSQLRepositoryBase, DiscoveryRepository):
    def save_job(self, job: DiscoveryJob) -> None:
        self._ensure_tenant(job.tenant_id)
        current = self.get_job(job.tenant_id, job.id.value)
        parameters = {
            "id": job.id.value,
            "tenant_id": job.tenant_id.value,
            "collector_id": job.collector_id.value,
            "requested_scope": job.requested_scope.value,
            "job_type": job.job_type,
            "target": job.target,
            "idempotency_key": job.idempotency_key,
            "max_attempts": job.max_attempts,
            "attempt_count": job.attempt_count,
            "status": job.status.value,
            "lease_owner": job.lease_owner,
            "lease_token": job.lease_token,
            "leased_until": job.leased_until,
            "next_attempt_at": job.next_attempt_at,
            "last_error": job.last_error,
            "result_hash": job.result_hash,
            "requested_by": job.requested_by,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "completed_at": job.completed_at,
        }
        if current is None:
            row = self._fetch_one(
                """
                INSERT INTO discovery_jobs (
                    id, tenant_id, collector_id, requested_scope, job_type, target,
                    idempotency_key, max_attempts, attempt_count, status, lease_owner,
                    lease_token, leased_until, next_attempt_at, last_error, result_hash,
                    requested_by, created_at, updated_at, completed_at
                ) VALUES (
                    %(id)s, %(tenant_id)s, %(collector_id)s, %(requested_scope)s,
                    %(job_type)s, %(target)s, %(idempotency_key)s, %(max_attempts)s,
                    %(attempt_count)s, %(status)s, %(lease_owner)s, %(lease_token)s,
                    %(leased_until)s, %(next_attempt_at)s, %(last_error)s, %(result_hash)s,
                    %(requested_by)s, %(created_at)s, %(updated_at)s, %(completed_at)s
                )
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                parameters,
            )
            if row is None:
                raise ConflictError("discovery job insert conflicts with persisted idempotency")
            return
        job.assert_persistence_transition_from(current)
        if job == current:
            return
        parameters.update(
            {
                "expected_status": current.status.value,
                "expected_attempt_count": current.attempt_count,
                "expected_lease_token": current.lease_token,
                "expected_lease_owner": current.lease_owner,
                "expected_updated_at": current.updated_at,
            }
        )
        row = self._fetch_one(
            """
            UPDATE discovery_jobs
            SET status = %(status)s,
                attempt_count = %(attempt_count)s,
                lease_owner = %(lease_owner)s,
                lease_token = %(lease_token)s,
                leased_until = %(leased_until)s,
                next_attempt_at = %(next_attempt_at)s,
                last_error = %(last_error)s,
                result_hash = %(result_hash)s,
                updated_at = %(updated_at)s,
                completed_at = %(completed_at)s
            WHERE tenant_id = %(tenant_id)s
              AND id = %(id)s
              AND status = %(expected_status)s
              AND attempt_count = %(expected_attempt_count)s
              AND lease_token = %(expected_lease_token)s
              AND lease_owner IS NOT DISTINCT FROM %(expected_lease_owner)s
              AND updated_at = %(expected_updated_at)s
            RETURNING id
            """,
            parameters,
        )
        if row is None:
            raise ConflictError("discovery job update rejected by optimistic fencing policy")

    def get_job(self, tenant_id: TenantId, job_id: str) -> DiscoveryJob | None:
        row = self._fetch_one(
            self._job_select() + " WHERE tenant_id = %(tenant_id)s AND id = %(id)s",
            {"tenant_id": tenant_id.value, "id": job_id.strip()},
        )
        return self._job_from_row(row) if row else None

    def find_job_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> DiscoveryJob | None:
        row = self._fetch_one(
            self._job_select() + " WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(key)s",
            {"tenant_id": tenant_id.value, "key": idempotency_key.strip()},
        )
        return self._job_from_row(row) if row else None

    def claim_next_job(
        self,
        tenant_id: TenantId,
        collector_id: EntityId,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
    ) -> DiscoveryJobClaimResult:
        exhausted_rows = self._fetch_all(
            """
            UPDATE discovery_jobs
            SET status = 'dead-letter',
                lease_owner = NULL,
                leased_until = NULL,
                next_attempt_at = NULL,
                last_error = 'lease expired after final attempt',
                result_hash = NULL,
                completed_at = NULL,
                updated_at = %(now)s
            WHERE tenant_id = %(tenant_id)s
              AND collector_id = %(collector_id)s
              AND status = 'leased'
              AND leased_until <= %(now)s
              AND attempt_count >= max_attempts
            RETURNING id, tenant_id, collector_id, requested_scope, job_type, target,
                      idempotency_key, max_attempts, attempt_count, status, lease_owner,
                      lease_token, leased_until, next_attempt_at, last_error, result_hash,
                      requested_by, created_at, updated_at, completed_at
            """,
            {
                "tenant_id": tenant_id.value,
                "collector_id": collector_id.value,
                "now": now,
            },
        )
        dead_lettered_jobs = tuple(self._job_from_row(row) for row in exhausted_rows)
        row = self._fetch_one(
            """
            WITH candidate AS (
                SELECT id
                FROM discovery_jobs
                WHERE tenant_id = %(tenant_id)s
                  AND collector_id = %(collector_id)s
                  AND attempt_count < max_attempts
                  AND (
                      status = 'queued'
                      OR (status = 'retry-wait' AND next_attempt_at <= %(now)s)
                      OR (status = 'leased' AND leased_until <= %(now)s)
                  )
                ORDER BY COALESCE(next_attempt_at, leased_until, created_at), created_at, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE discovery_jobs AS job
            SET status = 'leased',
                attempt_count = job.attempt_count + 1,
                lease_owner = %(worker_id)s,
                lease_token = job.lease_token + 1,
                leased_until = %(now)s + make_interval(secs => %(lease_seconds)s),
                next_attempt_at = NULL,
                result_hash = NULL,
                completed_at = NULL,
                updated_at = %(now)s
            FROM candidate
            WHERE job.tenant_id = %(tenant_id)s AND job.id = candidate.id
            RETURNING job.id, job.tenant_id, job.collector_id, job.requested_scope,
                      job.job_type, job.target, job.idempotency_key, job.max_attempts,
                      job.attempt_count, job.status, job.lease_owner, job.lease_token,
                      job.leased_until, job.next_attempt_at, job.last_error, job.result_hash,
                      job.requested_by, job.created_at, job.updated_at, job.completed_at
            """,
            {
                "tenant_id": tenant_id.value,
                "collector_id": collector_id.value,
                "worker_id": worker_id,
                "lease_seconds": lease_seconds,
                "now": now,
            },
        )
        claimed = self._job_from_row(row) if row else None
        return DiscoveryJobClaimResult(
            job=claimed,
            dead_lettered_jobs=dead_lettered_jobs,
        )

    def list_jobs(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: str | None = None,
    ) -> DiscoveryJobPage:
        normalized_status = None if status is None else DiscoveryJobStatus.from_value(status).value
        clauses = ["tenant_id = %(tenant_id)s"]
        params: dict[str, object] = {"tenant_id": tenant_id.value, "limit": pagination.limit}
        if normalized_status is not None:
            clauses.append("status = %(status)s")
            params["status"] = normalized_status
        if pagination.cursor is not None:
            clauses.append("id > %(cursor)s")
            params["cursor"] = pagination.cursor
        rows = self._fetch_all(
            self._job_select()
            + " WHERE "
            + " AND ".join(clauses)
            + " ORDER BY id ASC LIMIT %(limit)s",
            params,
        )
        jobs = tuple(self._job_from_row(row) for row in rows)
        next_cursor = jobs[-1].id.value if len(jobs) == pagination.limit else None
        return DiscoveryJobPage(items=jobs, next_cursor=next_cursor)

    @staticmethod
    def _job_select() -> str:
        return """
            SELECT id, tenant_id, collector_id, requested_scope, job_type, target,
                   idempotency_key, max_attempts, attempt_count, status, lease_owner,
                   lease_token, leased_until, next_attempt_at, last_error, result_hash,
                   requested_by, created_at, updated_at, completed_at
            FROM discovery_jobs
        """

    @staticmethod
    def _job_from_row(row: Mapping[str, object]) -> DiscoveryJob:
        return DiscoveryJob.from_dict(dict(row))

    def save_evidence(self, evidence: DiscoveryEvidence) -> None:
        self._ensure_tenant(evidence.tenant_id)
        payload = evidence.as_dict()
        self._execute_without_result(
            """
            INSERT INTO discovery_evidence (
                id, tenant_id, source, source_ref, scope, external_id, object_key,
                object_kind, confidence, completeness, observed_at, received_at,
                payload_hash, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(source)s, %(source_ref)s, %(scope)s,
                %(external_id)s, %(object_key)s, %(object_kind)s, %(confidence)s,
                %(completeness)s, %(observed_at)s, %(received_at)s, %(payload_hash)s,
                %(payload)s::jsonb
            )
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": payload["id"],
                "tenant_id": payload["tenant_id"],
                "source": payload["source"],
                "source_ref": payload["source_ref"],
                "scope": payload["scope"],
                "external_id": payload["external_id"],
                "object_key": payload["object_key"],
                "object_kind": payload["object_kind"],
                "confidence": payload["confidence"],
                "completeness": payload["completeness"],
                "observed_at": evidence.observed_at,
                "received_at": evidence.received_at,
                "payload_hash": payload["payload_hash"],
                "payload": json.dumps(payload["payload"], sort_keys=True),
            },
        )
        stored = self.get_evidence(evidence.tenant_id, evidence.id.value)
        if stored is None or stored.as_dict() != evidence.as_dict():
            raise ConflictError("discovery evidence is immutable")

    def get_evidence(self, tenant_id: TenantId, evidence_id: str) -> DiscoveryEvidence | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, source, source_ref, scope, external_id, object_key,
                   object_kind, confidence, completeness, observed_at, received_at,
                   payload_hash, payload
            FROM discovery_evidence
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": evidence_id.strip()},
        )
        return self._evidence_from_row(row) if row else None

    def list_evidence(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        object_key: str | None = None,
    ) -> DiscoveryEvidencePage:
        params: dict[str, object] = {"tenant_id": tenant_id.value, "limit": pagination.limit}
        clauses = ["tenant_id = %(tenant_id)s"]
        if object_key:
            params["object_key"] = object_key.strip()
            clauses.append("object_key = %(object_key)s")
        if pagination.cursor:
            params["cursor"] = pagination.cursor
            clauses.append("id > %(cursor)s")
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, source, source_ref, scope, external_id, object_key,
                   object_kind, confidence, completeness, observed_at, received_at,
                   payload_hash, payload
            FROM discovery_evidence
            WHERE {" AND ".join(clauses)}
            ORDER BY id ASC
            LIMIT %(limit)s
            """,  # nosec B608 -- clauses are fixed SQL fragments
            params,
        )
        evidences = tuple(self._evidence_from_row(row) for row in rows)
        next_cursor = evidences[-1].id.value if len(evidences) == pagination.limit else None
        return DiscoveryEvidencePage(items=evidences, next_cursor=next_cursor)

    def save_reconciliation_case(self, case: DiscoveryReconciliationCase) -> None:
        self._ensure_tenant(case.tenant_id)
        payload = case.as_dict()
        self._execute_without_result(
            """
            INSERT INTO discovery_reconciliation_cases (
                id, tenant_id, object_key, object_kind, evidence_ids, source_count,
                confidence_score, freshness_score, completeness_score, overall_score,
                status, conflicts, merged_payload, evaluated_at, evaluated_by,
                signature, resolution, rsot_write_executed, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(object_key)s, %(object_kind)s, %(evidence_ids)s,
                %(source_count)s, %(confidence_score)s, %(freshness_score)s,
                %(completeness_score)s, %(overall_score)s, %(status)s,
                %(conflicts)s::jsonb, %(merged_payload)s::jsonb, %(evaluated_at)s,
                %(evaluated_by)s, %(signature)s, %(resolution)s::jsonb,
                %(rsot_write_executed)s, now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                merged_payload = EXCLUDED.merged_payload,
                resolution = EXCLUDED.resolution,
                updated_at = now()
            WHERE discovery_reconciliation_cases.signature = EXCLUDED.signature
              AND discovery_reconciliation_cases.status <> 'resolved'
            """,
            {
                "id": payload["id"],
                "tenant_id": payload["tenant_id"],
                "object_key": payload["object_key"],
                "object_kind": payload["object_kind"],
                "evidence_ids": payload["evidence_ids"],
                "source_count": payload["source_count"],
                "confidence_score": payload["confidence_score"],
                "freshness_score": payload["freshness_score"],
                "completeness_score": payload["completeness_score"],
                "overall_score": payload["overall_score"],
                "status": payload["status"],
                "conflicts": json.dumps(payload["conflicts"], sort_keys=True),
                "merged_payload": json.dumps(payload["merged_payload"], sort_keys=True),
                "evaluated_at": case.evaluated_at,
                "evaluated_by": payload["evaluated_by"],
                "signature": payload["signature"],
                "resolution": json.dumps(payload["resolution"], sort_keys=True),
                "rsot_write_executed": payload["rsot_write_executed"],
            },
        )
        stored = self.get_reconciliation_case(case.tenant_id, case.id.value)
        if stored is None or stored.as_dict() != case.as_dict():
            raise ConflictError("reconciliation case evidence set is immutable")

    def get_reconciliation_case(
        self, tenant_id: TenantId, case_id: str
    ) -> DiscoveryReconciliationCase | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, object_kind, evidence_ids, source_count,
                   confidence_score, freshness_score, completeness_score, overall_score,
                   status, conflicts, merged_payload, evaluated_at, evaluated_by,
                   signature, resolution, rsot_write_executed
            FROM discovery_reconciliation_cases
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": case_id.strip()},
        )
        return self._reconciliation_case_from_row(row) if row else None

    def find_reconciliation_case_by_signature(
        self, tenant_id: TenantId, signature: str
    ) -> DiscoveryReconciliationCase | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, object_kind, evidence_ids, source_count,
                   confidence_score, freshness_score, completeness_score, overall_score,
                   status, conflicts, merged_payload, evaluated_at, evaluated_by,
                   signature, resolution, rsot_write_executed
            FROM discovery_reconciliation_cases
            WHERE tenant_id = %(tenant_id)s AND signature = %(signature)s
            """,
            {"tenant_id": tenant_id.value, "signature": signature.strip()},
        )
        return self._reconciliation_case_from_row(row) if row else None

    def list_reconciliation_cases(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: str | None = None,
    ) -> DiscoveryReconciliationCasePage:
        params: dict[str, object] = {"tenant_id": tenant_id.value, "limit": pagination.limit}
        clauses = ["tenant_id = %(tenant_id)s"]
        if status:
            normalized_status = DiscoveryReconciliationStatus(status.strip().lower()).value
            params["status"] = normalized_status
            clauses.append("status = %(status)s")
        if pagination.cursor:
            params["cursor"] = pagination.cursor
            clauses.append("id > %(cursor)s")
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, object_key, object_kind, evidence_ids, source_count,
                   confidence_score, freshness_score, completeness_score, overall_score,
                   status, conflicts, merged_payload, evaluated_at, evaluated_by,
                   signature, resolution, rsot_write_executed
            FROM discovery_reconciliation_cases
            WHERE {" AND ".join(clauses)}
            ORDER BY id ASC
            LIMIT %(limit)s
            """,  # nosec B608 -- clauses are fixed SQL fragments
            params,
        )
        cases = tuple(self._reconciliation_case_from_row(row) for row in rows)
        next_cursor = cases[-1].id.value if len(cases) == pagination.limit else None
        return DiscoveryReconciliationCasePage(items=cases, next_cursor=next_cursor)

    def _evidence_from_row(self, row: Mapping[str, object]) -> DiscoveryEvidence:
        return DiscoveryEvidence.from_dict(
            {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "source": row["source"],
                "source_ref": row["source_ref"],
                "scope": row["scope"],
                "external_id": row["external_id"],
                "object_key": row["object_key"],
                "object_kind": row["object_kind"],
                "confidence": row["confidence"],
                "completeness": row["completeness"],
                "observed_at": row["observed_at"],
                "received_at": row["received_at"],
                "payload_hash": row["payload_hash"],
                "payload": self._json_object(row["payload"], "discovery evidence payload"),
            }
        )

    def _reconciliation_case_from_row(
        self, row: Mapping[str, object]
    ) -> DiscoveryReconciliationCase:
        evidence_ids_value = row["evidence_ids"]
        if not isinstance(evidence_ids_value, Sequence) or isinstance(evidence_ids_value, str):
            raise ValidationError("stored reconciliation evidence ids are invalid")
        return DiscoveryReconciliationCase.from_dict(
            {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "object_key": row["object_key"],
                "object_kind": row["object_kind"],
                "evidence_ids": list(evidence_ids_value),
                "source_count": row["source_count"],
                "confidence_score": row["confidence_score"],
                "freshness_score": row["freshness_score"],
                "completeness_score": row["completeness_score"],
                "overall_score": row["overall_score"],
                "status": row["status"],
                "conflicts": self._json_array(row["conflicts"], "reconciliation conflicts"),
                "merged_payload": self._json_object(
                    row["merged_payload"], "reconciliation merged payload"
                ),
                "evaluated_at": row["evaluated_at"],
                "evaluated_by": row["evaluated_by"],
                "signature": row["signature"],
                "resolution": self._json_nullable_object(
                    row.get("resolution"), "reconciliation resolution"
                ),
                "rsot_write_executed": row["rsot_write_executed"],
            }
        )

    @staticmethod
    def _json_object(value: object, label: str) -> dict[str, object]:
        decoded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(decoded, dict):
            raise ValidationError(label + " must be a JSON object")
        return cast(dict[str, object], decoded)

    @staticmethod
    def _json_array(value: object, label: str) -> list[object]:
        decoded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(decoded, list):
            raise ValidationError(label + " must be a JSON array")
        return cast(list[object], decoded)

    @classmethod
    def _json_nullable_object(cls, value: object, label: str) -> dict[str, object] | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValidationError(label + " must contain valid JSON") from exc
            if decoded is None:
                return None
            if not isinstance(decoded, dict):
                raise ValidationError(label + " must be a JSON object")
            return cast(dict[str, object], decoded)
        return cls._json_object(value, label)

    def save_integration_profile(self, profile: DiscoveryIntegrationProfile) -> None:
        self._ensure_tenant(profile.tenant_id)
        payload = profile.as_dict()
        self._execute_without_result(
            """
            INSERT INTO discovery_integration_profiles (
                id, tenant_id, name, kind, scope, endpoint_url, credential_secret_ref,
                verify_tls, inventory_enabled, max_concurrency, rate_limit_per_minute,
                status, created_by, created_at, disabled_reason, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(kind)s, %(scope)s, %(endpoint_url)s,
                %(credential_secret_ref)s, %(verify_tls)s, %(inventory_enabled)s,
                %(max_concurrency)s, %(rate_limit_per_minute)s, %(status)s,
                %(created_by)s, %(created_at)s, %(disabled_reason)s, now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                name = EXCLUDED.name,
                kind = EXCLUDED.kind,
                scope = EXCLUDED.scope,
                endpoint_url = EXCLUDED.endpoint_url,
                credential_secret_ref = EXCLUDED.credential_secret_ref,
                verify_tls = EXCLUDED.verify_tls,
                inventory_enabled = EXCLUDED.inventory_enabled,
                max_concurrency = EXCLUDED.max_concurrency,
                rate_limit_per_minute = EXCLUDED.rate_limit_per_minute,
                status = EXCLUDED.status,
                disabled_reason = EXCLUDED.disabled_reason,
                updated_at = now()
            """,
            {
                "id": payload["id"],
                "tenant_id": payload["tenant_id"],
                "name": payload["name"],
                "kind": payload["kind"],
                "scope": payload["scope"],
                "endpoint_url": payload["endpoint_url"],
                "credential_secret_ref": payload["credential_secret_ref"],
                "verify_tls": payload["verify_tls"],
                "inventory_enabled": payload["inventory_enabled"],
                "max_concurrency": payload["max_concurrency"],
                "rate_limit_per_minute": payload["rate_limit_per_minute"],
                "status": payload["status"],
                "created_by": payload["created_by"],
                "created_at": profile.created_at,
                "disabled_reason": payload["disabled_reason"],
            },
        )

    def get_integration_profile(
        self, tenant_id: TenantId, profile_id: str
    ) -> DiscoveryIntegrationProfile | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, name, kind, scope, endpoint_url, credential_secret_ref,
                   verify_tls, inventory_enabled, max_concurrency, rate_limit_per_minute,
                   status, created_by, created_at, disabled_reason
            FROM discovery_integration_profiles
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": profile_id.strip()},
        )
        return self._integration_profile_from_row(row) if row else None

    def list_integration_profiles(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryIntegrationProfilePage:
        params: dict[str, object] = {"tenant_id": tenant_id.value, "limit": pagination.limit}
        if pagination.cursor:
            params["cursor"] = pagination.cursor
        rows = self._fetch_all(
            self._integration_profile_list_query(include_inactive, pagination.cursor is not None),
            params,
        )
        profiles = tuple(self._integration_profile_from_row(row) for row in rows)
        next_cursor = profiles[-1].id.value if len(profiles) == pagination.limit else None
        return DiscoveryIntegrationProfilePage(items=profiles, next_cursor=next_cursor)

    def _integration_profile_list_query(self, include_inactive: bool, has_cursor: bool) -> str:
        if include_inactive and has_cursor:
            return """
            SELECT id, tenant_id, name, kind, scope, endpoint_url, credential_secret_ref,
                   verify_tls, inventory_enabled, max_concurrency, rate_limit_per_minute,
                   status, created_by, created_at, disabled_reason
            FROM discovery_integration_profiles
            WHERE tenant_id = %(tenant_id)s AND id > %(cursor)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        if include_inactive:
            return """
            SELECT id, tenant_id, name, kind, scope, endpoint_url, credential_secret_ref,
                   verify_tls, inventory_enabled, max_concurrency, rate_limit_per_minute,
                   status, created_by, created_at, disabled_reason
            FROM discovery_integration_profiles
            WHERE tenant_id = %(tenant_id)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        if has_cursor:
            return """
            SELECT id, tenant_id, name, kind, scope, endpoint_url, credential_secret_ref,
                   verify_tls, inventory_enabled, max_concurrency, rate_limit_per_minute,
                   status, created_by, created_at, disabled_reason
            FROM discovery_integration_profiles
            WHERE tenant_id = %(tenant_id)s AND status <> 'disabled' AND id > %(cursor)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        return """
            SELECT id, tenant_id, name, kind, scope, endpoint_url, credential_secret_ref,
                   verify_tls, inventory_enabled, max_concurrency, rate_limit_per_minute,
                   status, created_by, created_at, disabled_reason
            FROM discovery_integration_profiles
            WHERE tenant_id = %(tenant_id)s AND status <> 'disabled'
            ORDER BY id ASC
            LIMIT %(limit)s
            """

    def _integration_profile_from_row(
        self, row: Mapping[str, object]
    ) -> DiscoveryIntegrationProfile:
        return DiscoveryIntegrationProfile.from_dict(
            {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "name": row["name"],
                "kind": row["kind"],
                "scope": row["scope"],
                "endpoint_url": row.get("endpoint_url"),
                "credential_secret_ref": row["credential_secret_ref"],
                "verify_tls": row["verify_tls"],
                "inventory_enabled": row["inventory_enabled"],
                "max_concurrency": row["max_concurrency"],
                "rate_limit_per_minute": row["rate_limit_per_minute"],
                "status": row["status"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "disabled_reason": row.get("disabled_reason"),
            }
        )

    def save_protocol_profile(self, profile: DiscoveryProtocolCredentialProfile) -> None:
        self._ensure_tenant(profile.tenant_id)
        payload = profile.as_dict()
        self._execute_without_result(
            """
            INSERT INTO discovery_protocol_profiles (
                id, tenant_id, name, protocol, scope, credential_secret_ref, port,
                timeout_seconds, max_concurrency, rate_limit_per_minute, retry_count,
                status, created_by, created_at, disabled_reason, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(protocol)s, %(scope)s,
                %(credential_secret_ref)s, %(port)s, %(timeout_seconds)s,
                %(max_concurrency)s, %(rate_limit_per_minute)s, %(retry_count)s,
                %(status)s, %(created_by)s, %(created_at)s, %(disabled_reason)s, now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                name = EXCLUDED.name,
                protocol = EXCLUDED.protocol,
                scope = EXCLUDED.scope,
                credential_secret_ref = EXCLUDED.credential_secret_ref,
                port = EXCLUDED.port,
                timeout_seconds = EXCLUDED.timeout_seconds,
                max_concurrency = EXCLUDED.max_concurrency,
                rate_limit_per_minute = EXCLUDED.rate_limit_per_minute,
                retry_count = EXCLUDED.retry_count,
                status = EXCLUDED.status,
                disabled_reason = EXCLUDED.disabled_reason,
                updated_at = now()
            """,
            {
                "id": payload["id"],
                "tenant_id": payload["tenant_id"],
                "name": payload["name"],
                "protocol": payload["protocol"],
                "scope": payload["scope"],
                "credential_secret_ref": payload["credential_secret_ref"],
                "port": payload["port"],
                "timeout_seconds": payload["timeout_seconds"],
                "max_concurrency": payload["max_concurrency"],
                "rate_limit_per_minute": payload["rate_limit_per_minute"],
                "retry_count": payload["retry_count"],
                "status": payload["status"],
                "created_by": payload["created_by"],
                "created_at": profile.created_at,
                "disabled_reason": payload["disabled_reason"],
            },
        )

    def get_protocol_profile(
        self, tenant_id: TenantId, profile_id: str
    ) -> DiscoveryProtocolCredentialProfile | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, name, protocol, scope, credential_secret_ref, port,
                   timeout_seconds, max_concurrency, rate_limit_per_minute, retry_count,
                   status, created_by, created_at, disabled_reason
            FROM discovery_protocol_profiles
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": profile_id.strip()},
        )
        return self._protocol_profile_from_row(row) if row else None

    def list_protocol_profiles(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryProtocolProfilePage:
        params: dict[str, object] = {"tenant_id": tenant_id.value, "limit": pagination.limit}
        if pagination.cursor:
            params["cursor"] = pagination.cursor
        rows = self._fetch_all(
            self._protocol_profile_list_query(include_inactive, pagination.cursor is not None),
            params,
        )
        profiles = tuple(self._protocol_profile_from_row(row) for row in rows)
        next_cursor = profiles[-1].id.value if len(profiles) == pagination.limit else None
        return DiscoveryProtocolProfilePage(items=profiles, next_cursor=next_cursor)

    def _protocol_profile_list_query(self, include_inactive: bool, has_cursor: bool) -> str:
        if include_inactive and has_cursor:
            return """
            SELECT id, tenant_id, name, protocol, scope, credential_secret_ref, port,
                   timeout_seconds, max_concurrency, rate_limit_per_minute, retry_count,
                   status, created_by, created_at, disabled_reason
            FROM discovery_protocol_profiles
            WHERE tenant_id = %(tenant_id)s AND id > %(cursor)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        if include_inactive:
            return """
            SELECT id, tenant_id, name, protocol, scope, credential_secret_ref, port,
                   timeout_seconds, max_concurrency, rate_limit_per_minute, retry_count,
                   status, created_by, created_at, disabled_reason
            FROM discovery_protocol_profiles
            WHERE tenant_id = %(tenant_id)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        if has_cursor:
            return """
            SELECT id, tenant_id, name, protocol, scope, credential_secret_ref, port,
                   timeout_seconds, max_concurrency, rate_limit_per_minute, retry_count,
                   status, created_by, created_at, disabled_reason
            FROM discovery_protocol_profiles
            WHERE tenant_id = %(tenant_id)s AND status <> 'disabled' AND id > %(cursor)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        return """
            SELECT id, tenant_id, name, protocol, scope, credential_secret_ref, port,
                   timeout_seconds, max_concurrency, rate_limit_per_minute, retry_count,
                   status, created_by, created_at, disabled_reason
            FROM discovery_protocol_profiles
            WHERE tenant_id = %(tenant_id)s AND status <> 'disabled'
            ORDER BY id ASC
            LIMIT %(limit)s
            """

    def _protocol_profile_from_row(
        self, row: Mapping[str, object]
    ) -> DiscoveryProtocolCredentialProfile:
        return DiscoveryProtocolCredentialProfile.from_dict(
            {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "name": row["name"],
                "protocol": row["protocol"],
                "scope": row["scope"],
                "credential_secret_ref": row["credential_secret_ref"],
                "port": row["port"],
                "timeout_seconds": row["timeout_seconds"],
                "max_concurrency": row["max_concurrency"],
                "rate_limit_per_minute": row["rate_limit_per_minute"],
                "retry_count": row["retry_count"],
                "status": row["status"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "disabled_reason": row.get("disabled_reason"),
            }
        )

    def save_collector(self, collector: DiscoveryCollector) -> None:
        self._ensure_tenant(collector.tenant_id)
        payload = collector.as_dict()
        self._execute_without_result(
            """
            INSERT INTO discovery_collectors (
                id, tenant_id, name, kind, certificate_fingerprint, vault_secret_ref,
                scopes, version, endpoint_url, status, registered_by, registered_at,
                last_heartbeat_at, last_heartbeat_status, last_seen_version, disabled_reason,
                updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(kind)s, %(certificate_fingerprint)s,
                %(vault_secret_ref)s, %(scopes)s, %(version)s, %(endpoint_url)s, %(status)s,
                %(registered_by)s, %(registered_at)s, %(last_heartbeat_at)s,
                %(last_heartbeat_status)s, %(last_seen_version)s, %(disabled_reason)s, now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                organization_id = EXCLUDED.organization_id,
                name = EXCLUDED.name,
                kind = EXCLUDED.kind,
                certificate_fingerprint = EXCLUDED.certificate_fingerprint,
                vault_secret_ref = EXCLUDED.vault_secret_ref,
                scopes = EXCLUDED.scopes,
                version = EXCLUDED.version,
                endpoint_url = EXCLUDED.endpoint_url,
                status = EXCLUDED.status,
                last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                last_heartbeat_status = EXCLUDED.last_heartbeat_status,
                last_seen_version = EXCLUDED.last_seen_version,
                disabled_reason = EXCLUDED.disabled_reason,
                updated_at = now()
            """,
            {
                "id": payload["id"],
                "tenant_id": payload["tenant_id"],
                "name": payload["name"],
                "kind": payload["kind"],
                "certificate_fingerprint": payload["certificate_fingerprint"],
                "vault_secret_ref": payload["vault_secret_ref"],
                "scopes": json.dumps(payload["scopes"], sort_keys=True),
                "version": payload["version"],
                "endpoint_url": payload["endpoint_url"],
                "status": payload["status"],
                "registered_by": payload["registered_by"],
                "registered_at": collector.registered_at,
                "last_heartbeat_at": collector.last_heartbeat_at,
                "last_heartbeat_status": payload["last_heartbeat_status"],
                "last_seen_version": payload["last_seen_version"],
                "disabled_reason": payload["disabled_reason"],
            },
        )

    def get_collector(self, tenant_id: TenantId, collector_id: str) -> DiscoveryCollector | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, name, kind, certificate_fingerprint, vault_secret_ref,
                   scopes, version, endpoint_url, status, registered_by, registered_at,
                   last_heartbeat_at, last_heartbeat_status, last_seen_version, disabled_reason
            FROM discovery_collectors
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": collector_id.strip()},
        )
        return self._collector_from_row(row) if row else None

    def list_collectors(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> DiscoveryCollectorPage:
        params: dict[str, object] = {"tenant_id": tenant_id.value, "limit": pagination.limit}
        if pagination.cursor:
            params["cursor"] = pagination.cursor
        rows = self._fetch_all(
            self._collector_list_query(include_inactive, pagination.cursor is not None),
            params,
        )
        collectors = tuple(self._collector_from_row(row) for row in rows)
        next_cursor = collectors[-1].id.value if len(collectors) == pagination.limit else None
        return DiscoveryCollectorPage(items=collectors, next_cursor=next_cursor)

    def _collector_list_query(self, include_inactive: bool, has_cursor: bool) -> str:
        if include_inactive and has_cursor:
            return """
            SELECT id, tenant_id, name, kind, certificate_fingerprint, vault_secret_ref,
                   scopes, version, endpoint_url, status, registered_by, registered_at,
                   last_heartbeat_at, last_heartbeat_status, last_seen_version, disabled_reason
            FROM discovery_collectors
            WHERE tenant_id = %(tenant_id)s AND id > %(cursor)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        if include_inactive:
            return """
            SELECT id, tenant_id, name, kind, certificate_fingerprint, vault_secret_ref,
                   scopes, version, endpoint_url, status, registered_by, registered_at,
                   last_heartbeat_at, last_heartbeat_status, last_seen_version, disabled_reason
            FROM discovery_collectors
            WHERE tenant_id = %(tenant_id)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        if has_cursor:
            return """
            SELECT id, tenant_id, name, kind, certificate_fingerprint, vault_secret_ref,
                   scopes, version, endpoint_url, status, registered_by, registered_at,
                   last_heartbeat_at, last_heartbeat_status, last_seen_version, disabled_reason
            FROM discovery_collectors
            WHERE tenant_id = %(tenant_id)s AND status <> 'disabled' AND id > %(cursor)s
            ORDER BY id ASC
            LIMIT %(limit)s
            """
        return """
            SELECT id, tenant_id, name, kind, certificate_fingerprint, vault_secret_ref,
                   scopes, version, endpoint_url, status, registered_by, registered_at,
                   last_heartbeat_at, last_heartbeat_status, last_seen_version, disabled_reason
            FROM discovery_collectors
            WHERE tenant_id = %(tenant_id)s AND status <> 'disabled'
            ORDER BY id ASC
            LIMIT %(limit)s
            """

    def _collector_from_row(self, row: Mapping[str, object]) -> DiscoveryCollector:
        scopes_value = row["scopes"]
        scopes = scopes_value if isinstance(scopes_value, list) else json.loads(str(scopes_value))
        return DiscoveryCollector.from_dict(
            {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "name": row["name"],
                "kind": row["kind"],
                "certificate_fingerprint": row["certificate_fingerprint"],
                "vault_secret_ref": row.get("vault_secret_ref"),
                "scopes": scopes,
                "version": row["version"],
                "endpoint_url": row.get("endpoint_url"),
                "status": row["status"],
                "registered_by": row["registered_by"],
                "registered_at": row["registered_at"],
                "last_heartbeat_at": row.get("last_heartbeat_at"),
                "last_heartbeat_status": row.get("last_heartbeat_status"),
                "last_seen_version": row.get("last_seen_version"),
                "disabled_reason": row.get("disabled_reason"),
            }
        )


class PostgreSQLExportRepository(PostgreSQLRepositoryBase, ExportRepository):
    def save_export_job(self, job: ExportJob) -> None:
        self._ensure_tenant(job.tenant_id)
        payload = job.as_dict()
        self._execute_without_result(
            """
            INSERT INTO export_jobs (
                id, tenant_id, resource, export_format, status, filter, requested_by,
                total_rows, artifact, error, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(resource)s, %(export_format)s, %(status)s,
                %(filter)s, %(requested_by)s, %(total_rows)s, %(artifact)s, %(error)s,
                %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                total_rows = EXCLUDED.total_rows,
                artifact = EXCLUDED.artifact,
                error = EXCLUDED.error,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "id": job.id.value,
                "tenant_id": job.tenant_id.value,
                "resource": job.resource.value,
                "export_format": job.format.value,
                "status": job.status.value,
                "filter": json.dumps(payload["filter"], sort_keys=True),
                "requested_by": job.requested_by,
                "total_rows": job.total_rows,
                "artifact": json.dumps(payload["artifact"], sort_keys=True),
                "error": job.error,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            },
        )

    def get_export_job(self, tenant_id: TenantId, job_id: str) -> ExportJob | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, resource, export_format, status, filter, requested_by,
                   total_rows, artifact, error, created_at, updated_at
            FROM export_jobs
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": job_id.strip()},
        )
        return self._export_job_from_row(row) if row else None

    def get_next_queued_export_job(self, tenant_id: TenantId) -> ExportJob | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, resource, export_format, status, filter, requested_by,
                   total_rows, artifact, error, created_at, updated_at
            FROM export_jobs
            WHERE tenant_id = %(tenant_id)s AND status = 'queued'
            ORDER BY created_at ASC, id ASC
            LIMIT 1
            """,
            {"tenant_id": tenant_id.value},
        )
        return self._export_job_from_row(row) if row else None

    def save_export_artifact(self, job: ExportJob, content: bytes) -> None:
        self._ensure_tenant(job.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO export_artifacts (job_id, tenant_id, content, created_at)
            VALUES (%(job_id)s, %(tenant_id)s, %(content)s, now())
            ON CONFLICT (tenant_id, job_id) DO UPDATE SET
                content = EXCLUDED.content,
                created_at = EXCLUDED.created_at
            """,
            {"job_id": job.id.value, "tenant_id": job.tenant_id.value, "content": content},
        )

    def get_export_artifact(self, tenant_id: TenantId, job_id: str) -> bytes | None:
        row = self._fetch_one(
            """
            SELECT content
            FROM export_artifacts
            WHERE tenant_id = %(tenant_id)s AND job_id = %(job_id)s
            """,
            {"tenant_id": tenant_id.value, "job_id": job_id.strip()},
        )
        if row is None:
            return None
        value = row["content"]
        if isinstance(value, bytes):
            return value
        if isinstance(value, memoryview):
            return value.tobytes()
        raise ValidationError("stored export artifact content is invalid")

    def get_or_create_export_signing_secret(self) -> bytes:
        row = self._fetch_one("SELECT secret_hex FROM export_signing_keys WHERE id = 'default'")
        if row is not None:
            return bytes.fromhex(str(row["secret_hex"]))
        secret_hex = secrets.token_hex(32)
        self._execute_without_result(
            """
            INSERT INTO export_signing_keys (id, secret_hex, created_at)
            VALUES ('default', %(secret_hex)s, now())
            ON CONFLICT (id) DO NOTHING
            """,
            {"secret_hex": secret_hex},
        )
        row = self._fetch_one("SELECT secret_hex FROM export_signing_keys WHERE id = 'default'")
        if row is None:
            raise ValidationError("export signing key could not be initialized")
        return bytes.fromhex(str(row["secret_hex"]))

    def export_storage_strategy_name(self) -> str:
        return "postgresql-managed-object-storage"

    def _export_job_from_row(self, row: Mapping[str, object]) -> ExportJob:
        artifact_value = row.get("artifact")
        artifact = (
            self._json_object(artifact_value) if artifact_value not in (None, "null") else None
        )
        return ExportJob.from_dict(
            {
                "id": row["id"],
                "tenant_id": row["tenant_id"],
                "resource": row["resource"],
                "format": row["export_format"],
                "status": row["status"],
                "filter": self._json_object(row["filter"]),
                "requested_by": row["requested_by"],
                "total_rows": row["total_rows"],
                "artifact": artifact,
                "error": row.get("error"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def _json_object(self, value: object) -> dict[str, object]:
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        loaded = json.loads(str(value))
        if not isinstance(loaded, dict):
            raise ValidationError("stored export JSON object is invalid")
        return cast(dict[str, object], loaded)


class PostgreSQLImportRepository(PostgreSQLRepositoryBase, ImportRepository):
    def save_import_report(self, report: ImportReport) -> None:
        self._ensure_tenant(report.tenant_id)
        payload = report.as_dict()
        self._execute_without_result(
            """
            INSERT INTO import_jobs (
                id, tenant_id, import_format, dry_run, status, total_rows, valid_rows,
                invalid_rows, mapping, impacts, dlq, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(import_format)s, %(dry_run)s, %(status)s,
                %(total_rows)s, %(valid_rows)s, %(invalid_rows)s, %(mapping)s,
                %(impacts)s, %(dlq)s, now(), now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                dry_run = EXCLUDED.dry_run,
                status = EXCLUDED.status,
                total_rows = EXCLUDED.total_rows,
                valid_rows = EXCLUDED.valid_rows,
                invalid_rows = EXCLUDED.invalid_rows,
                mapping = EXCLUDED.mapping,
                impacts = EXCLUDED.impacts,
                dlq = EXCLUDED.dlq,
                updated_at = now()
            """,
            {
                "id": report.job_id.value,
                "tenant_id": report.tenant_id.value,
                "import_format": report.format.value,
                "dry_run": report.dry_run,
                "status": report.status.value,
                "total_rows": report.total_rows,
                "valid_rows": report.valid_rows,
                "invalid_rows": report.invalid_rows,
                "mapping": json.dumps(payload["mapping"], sort_keys=True),
                "impacts": json.dumps(payload["impacts"], sort_keys=True),
                "dlq": json.dumps(payload["dlq"], sort_keys=True),
            },
        )

    def get_import_report(self, tenant_id: TenantId, job_id: str) -> ImportReport | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, import_format, dry_run, status, total_rows, valid_rows,
                   invalid_rows, mapping, impacts, dlq
            FROM import_jobs
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": job_id.strip()},
        )
        if row is None:
            return None
        return self._report_from_row(row)

    def save_bulk_import_report(self, report: BulkImportReport) -> None:
        self._ensure_tenant(report.tenant_id)
        payload = report.as_dict()
        self._execute_without_result(
            """
            INSERT INTO bulk_import_jobs (
                id, tenant_id, import_format, dry_run, status, total_rows, valid_rows,
                invalid_rows, create_count, update_count, mapping, metrics, checkpoint,
                impact_sample, dlq_sample, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(import_format)s, %(dry_run)s, %(status)s,
                %(total_rows)s, %(valid_rows)s, %(invalid_rows)s, %(create_count)s,
                %(update_count)s, %(mapping)s, %(metrics)s, %(checkpoint)s,
                %(impact_sample)s, %(dlq_sample)s, now(), now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                dry_run = EXCLUDED.dry_run,
                status = EXCLUDED.status,
                total_rows = EXCLUDED.total_rows,
                valid_rows = EXCLUDED.valid_rows,
                invalid_rows = EXCLUDED.invalid_rows,
                create_count = EXCLUDED.create_count,
                update_count = EXCLUDED.update_count,
                mapping = EXCLUDED.mapping,
                metrics = EXCLUDED.metrics,
                checkpoint = EXCLUDED.checkpoint,
                impact_sample = EXCLUDED.impact_sample,
                dlq_sample = EXCLUDED.dlq_sample,
                updated_at = now()
            """,
            {
                "id": report.job_id.value,
                "tenant_id": report.tenant_id.value,
                "import_format": report.format.value,
                "dry_run": report.dry_run,
                "status": report.status.value,
                "total_rows": report.total_rows,
                "valid_rows": report.valid_rows,
                "invalid_rows": report.invalid_rows,
                "create_count": report.create_count,
                "update_count": report.update_count,
                "mapping": json.dumps(payload["mapping"], sort_keys=True),
                "metrics": json.dumps(payload["metrics"], sort_keys=True),
                "checkpoint": json.dumps(payload["checkpoint"], sort_keys=True),
                "impact_sample": json.dumps(payload["impact_sample"], sort_keys=True),
                "dlq_sample": json.dumps(payload["dlq_sample"], sort_keys=True),
            },
        )

    def get_bulk_import_report(self, tenant_id: TenantId, job_id: str) -> BulkImportReport | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, import_format, dry_run, status, total_rows, valid_rows,
                   invalid_rows, create_count, update_count, mapping, metrics, checkpoint,
                   impact_sample, dlq_sample
            FROM bulk_import_jobs
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": job_id.strip()},
        )
        if row is None:
            return None
        return self._bulk_report_from_row(row)

    def save_bulk_import_checkpoint(self, checkpoint: BulkImportCheckpoint) -> None:
        self._ensure_tenant(checkpoint.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO bulk_import_checkpoints (
                job_id, tenant_id, next_row_number, total_rows, valid_rows, invalid_rows,
                create_count, update_count, batches_completed, status, updated_at
            ) VALUES (
                %(job_id)s, %(tenant_id)s, %(next_row_number)s, %(total_rows)s,
                %(valid_rows)s, %(invalid_rows)s, %(create_count)s, %(update_count)s,
                %(batches_completed)s, %(status)s, now()
            )
            ON CONFLICT (tenant_id, job_id) DO UPDATE SET
                next_row_number = EXCLUDED.next_row_number,
                total_rows = EXCLUDED.total_rows,
                valid_rows = EXCLUDED.valid_rows,
                invalid_rows = EXCLUDED.invalid_rows,
                create_count = EXCLUDED.create_count,
                update_count = EXCLUDED.update_count,
                batches_completed = EXCLUDED.batches_completed,
                status = EXCLUDED.status,
                updated_at = now()
            """,
            checkpoint.as_dict(),
        )

    def get_bulk_import_checkpoint(
        self, tenant_id: TenantId, job_id: str
    ) -> BulkImportCheckpoint | None:
        row = self._fetch_one(
            """
            SELECT job_id, tenant_id, next_row_number, total_rows, valid_rows, invalid_rows,
                   create_count, update_count, batches_completed, status
            FROM bulk_import_checkpoints
            WHERE tenant_id = %(tenant_id)s AND job_id = %(job_id)s
            """,
            {"tenant_id": tenant_id.value, "job_id": job_id.strip()},
        )
        if row is None:
            return None
        return self._checkpoint_from_row(row)

    def save_migration_plan_report(self, report: MigrationPlanReport) -> None:
        self._ensure_tenant(report.tenant_id)
        payload = report.as_dict()
        self._execute_without_result(
            """
            INSERT INTO migration_plan_reports (
                id, tenant_id, source, import_format, status, template, total_rows,
                valid_rows, invalid_rows, create_count, update_count, gaps,
                import_report, resume_strategy, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(source)s, %(import_format)s, %(status)s,
                %(template)s, %(total_rows)s, %(valid_rows)s, %(invalid_rows)s,
                %(create_count)s, %(update_count)s, %(gaps)s, %(import_report)s,
                %(resume_strategy)s, now(), now()
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                template = EXCLUDED.template,
                total_rows = EXCLUDED.total_rows,
                valid_rows = EXCLUDED.valid_rows,
                invalid_rows = EXCLUDED.invalid_rows,
                create_count = EXCLUDED.create_count,
                update_count = EXCLUDED.update_count,
                gaps = EXCLUDED.gaps,
                import_report = EXCLUDED.import_report,
                resume_strategy = EXCLUDED.resume_strategy,
                updated_at = now()
            """,
            {
                "id": report.job_id.value,
                "tenant_id": report.tenant_id.value,
                "source": report.source.value,
                "import_format": report.format.value,
                "status": report.status.value,
                "template": json.dumps(payload["template"], sort_keys=True),
                "total_rows": report.total_rows,
                "valid_rows": report.valid_rows,
                "invalid_rows": report.invalid_rows,
                "create_count": report.create_count,
                "update_count": report.update_count,
                "gaps": json.dumps(payload["gaps"], sort_keys=True),
                "import_report": json.dumps(payload["import_report"], sort_keys=True),
                "resume_strategy": report.resume_strategy,
            },
        )

    def get_migration_plan_report(
        self, tenant_id: TenantId, job_id: str
    ) -> MigrationPlanReport | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, source, import_format, status, template, total_rows,
                   valid_rows, invalid_rows, create_count, update_count, gaps,
                   import_report, resume_strategy
            FROM migration_plan_reports
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": job_id.strip()},
        )
        if row is None:
            return None
        return self._migration_plan_from_row(row)

    def bulk_import_strategy_name(self) -> str:
        return "postgresql-bounded-batch-copy-eligible"

    def _migration_plan_from_row(self, row: Mapping[str, object]) -> MigrationPlanReport:
        template_payload = self._json_object(row["template"])
        gaps_payload = self._json_list(row["gaps"])
        import_payload = self._json_object(row["import_report"])
        mapping_payload = template_payload.get("mapping", {})
        if not isinstance(mapping_payload, dict):
            raise ValidationError("stored migration template mapping is invalid")
        source = LegacyMigrationSource.from_value(str(template_payload["source"]))
        required_columns_payload = template_payload.get("required_columns", [])
        recommended_columns_payload = template_payload.get("recommended_columns", [])
        notes_payload = template_payload.get("notes", [])
        if not isinstance(required_columns_payload, list):
            raise ValidationError("stored migration template required columns are invalid")
        if not isinstance(recommended_columns_payload, list) or not isinstance(notes_payload, list):
            raise ValidationError("stored migration template metadata is invalid")
        template = MigrationTemplate.create(
            source=source,
            name=str(template_payload["name"]),
            version=str(template_payload["version"]),
            mapping=ImportMapping.from_dict({str(k): str(v) for k, v in mapping_payload.items()}),
            required_columns=tuple(str(item) for item in required_columns_payload),
            recommended_columns=tuple(str(item) for item in recommended_columns_payload),
            notes=tuple(str(item) for item in notes_payload),
        )
        gaps = tuple(
            MigrationGap.create(
                str(item["category"]),
                str(item["field"]),
                str(item["message"]),
                Severity(str(item["severity"])),
            )
            for item in gaps_payload
            if isinstance(item, dict)
        )
        return MigrationPlanReport.create(
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            source=LegacyMigrationSource.from_value(str(row["source"])),
            import_format=ImportFormat.from_value(str(row["import_format"])),
            template=template,
            gaps=gaps,
            import_report=self._report_from_row(import_payload),
            resume_strategy=str(row["resume_strategy"]),
            job_id=EntityId.from_value(str(row["id"])),
        )

    def _report_from_row(self, row: Mapping[str, object]) -> ImportReport:
        mapping_payload = self._json_object(row["mapping"])
        impacts_payload = self._json_list(row["impacts"])
        dlq_payload = self._json_list(row["dlq"])
        mapping = ImportMapping.from_dict(
            {str(key): str(value) for key, value in mapping_payload.items()}
        )
        impacts = tuple(
            ImportRowImpact.create(
                int(item["row_number"]),
                str(item["action"]),
                str(item["object_key"]),
                str(item["object_kind"]),
            )
            for item in impacts_payload
            if isinstance(item, dict)
        )
        issues = tuple(
            ImportRowIssue.create(
                int(item["row_number"]),
                str(item["field"]),
                str(item["message"]),
                Severity(str(item["severity"])),
            )
            for item in dlq_payload
            if isinstance(item, dict)
        )
        return ImportReport.create(
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            import_format=ImportFormat.from_value(str(row["import_format"])),
            dry_run=bool(row["dry_run"]),
            mapping=mapping,
            total_rows=int(str(row["total_rows"])),
            impacts=impacts,
            dlq=issues,
            status=ImportJobStatus(str(row["status"])),
            job_id=EntityId.from_value(str(row["id"])),
        )

    def _bulk_report_from_row(self, row: Mapping[str, object]) -> BulkImportReport:
        mapping_payload = self._json_object(row["mapping"])
        metrics_payload = self._json_object(row["metrics"])
        checkpoint_payload = self._json_object(row["checkpoint"])
        impacts_payload = self._json_list(row["impact_sample"])
        dlq_payload = self._json_list(row["dlq_sample"])
        mapping = ImportMapping.from_dict(
            {str(key): str(value) for key, value in mapping_payload.items()}
        )
        metrics = BulkImportMetrics.create(
            batch_size=int(str(metrics_payload["batch_size"])),
            checkpoint_interval=int(str(metrics_payload["checkpoint_interval"])),
            batches_completed=int(str(metrics_payload["batches_completed"])),
            copy_strategy=str(metrics_payload["copy_strategy"]),
            resumed_from_row=(
                None
                if metrics_payload.get("resumed_from_row") is None
                else int(str(metrics_payload["resumed_from_row"]))
            ),
        )
        checkpoint = self._checkpoint_from_row(checkpoint_payload)
        impacts = tuple(
            ImportRowImpact.create(
                int(item["row_number"]),
                str(item["action"]),
                str(item["object_key"]),
                str(item["object_kind"]),
            )
            for item in impacts_payload
            if isinstance(item, dict)
        )
        issues = tuple(
            ImportRowIssue.create(
                int(item["row_number"]),
                str(item["field"]),
                str(item["message"]),
                Severity(str(item["severity"])),
            )
            for item in dlq_payload
            if isinstance(item, dict)
        )
        return BulkImportReport.create(
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            import_format=ImportFormat.from_value(str(row["import_format"])),
            dry_run=bool(row["dry_run"]),
            status=ImportJobStatus(str(row["status"])),
            total_rows=int(str(row["total_rows"])),
            valid_rows=int(str(row["valid_rows"])),
            invalid_rows=int(str(row["invalid_rows"])),
            create_count=int(str(row["create_count"])),
            update_count=int(str(row["update_count"])),
            mapping=mapping,
            metrics=metrics,
            checkpoint=checkpoint,
            impact_sample=impacts,
            dlq_sample=issues,
            job_id=EntityId.from_value(str(row["id"])),
        )

    def _checkpoint_from_row(self, row: Mapping[str, object]) -> BulkImportCheckpoint:
        job_value = row.get("job_id", row.get("id"))
        if job_value is None:
            raise ValidationError("stored bulk import checkpoint job id is invalid")
        return BulkImportCheckpoint.create(
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            next_row_number=int(str(row["next_row_number"])),
            total_rows=int(str(row["total_rows"])),
            valid_rows=int(str(row["valid_rows"])),
            invalid_rows=int(str(row["invalid_rows"])),
            create_count=int(str(row["create_count"])),
            update_count=int(str(row["update_count"])),
            batches_completed=int(str(row["batches_completed"])),
            status=ImportJobStatus(str(row["status"])),
            job_id=EntityId.from_value(str(job_value)),
        )

    def _json_object(self, value: object) -> dict[str, object]:
        if isinstance(value, dict):
            return cast(dict[str, object], value)
        loaded = json.loads(str(value))
        if not isinstance(loaded, dict):
            raise ValidationError("stored import JSON object is invalid")
        return cast(dict[str, object], loaded)

    def _json_list(self, value: object) -> list[object]:
        if isinstance(value, list):
            return value
        loaded = json.loads(str(value))
        if not isinstance(loaded, list):
            raise ValidationError("stored import JSON list is invalid")
        return loaded


class PostgreSQLIdentityRepository(PostgreSQLRepositoryBase, IdentityRepository):
    def upsert_user(self, user: IdentityUser) -> None:
        self._ensure_tenant(user.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO identity_users (
                id, tenant_id, username, display_name, email, roles, active
            ) VALUES (
                %(id)s, %(tenant_id)s, %(username)s, %(display_name)s, %(email)s,
                %(roles)s, %(active)s
            )
            ON CONFLICT (tenant_id, username) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                email = EXCLUDED.email,
                roles = EXCLUDED.roles,
                active = EXCLUDED.active,
                updated_at = now()
            """,
            {
                "id": user.id.value,
                "tenant_id": user.tenant_id.value,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "roles": list(user.role_names()),
                "active": user.active,
            },
        )

    def upsert_group(self, group: IdentityGroup) -> None:
        self._ensure_tenant(group.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO identity_groups (
                id, tenant_id, name, display_name, roles, active
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(display_name)s, %(roles)s,
                %(active)s
            )
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                roles = EXCLUDED.roles,
                active = EXCLUDED.active,
                updated_at = now()
            """,
            {
                "id": group.id.value,
                "tenant_id": group.tenant_id.value,
                "name": group.name,
                "display_name": group.display_name,
                "roles": list(group.role_names()),
                "active": group.active,
            },
        )

    def add_membership(self, membership: GroupMembership) -> None:
        self._ensure_tenant(membership.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO identity_group_memberships (tenant_id, username, group_name)
            VALUES (%(tenant_id)s, %(username)s, %(group_name)s)
            ON CONFLICT (tenant_id, username, group_name) DO NOTHING
            """,
            {
                "tenant_id": membership.tenant_id.value,
                "username": membership.username,
                "group_name": membership.group_name,
            },
        )

    def grant_user_role(self, tenant_id: TenantId, username: str, role: str) -> bool:
        normalized_user = IdentitySubject.normalize(username)
        normalized_role = IdentityRoleSet.from_names((role,))[0].name
        row = self._fetch_one(
            """
            SELECT roles
            FROM identity_users
            WHERE tenant_id = %(tenant_id)s AND username = %(username)s
            """,
            {"tenant_id": tenant_id.value, "username": normalized_user},
        )
        if row is None:
            raise ValidationError("identity user must exist before granting a role")
        roles = {str(item) for item in cast(Sequence[object], row.get("roles", []))}
        changed = normalized_role not in roles
        roles.add(normalized_role)
        self._execute_without_result(
            """
            UPDATE identity_users
            SET roles = %(roles)s, updated_at = now()
            WHERE tenant_id = %(tenant_id)s AND username = %(username)s
            """,
            {
                "tenant_id": tenant_id.value,
                "username": normalized_user,
                "roles": sorted(roles),
            },
        )
        return changed

    def grant_group_role(self, tenant_id: TenantId, group_name: str, role: str) -> bool:
        normalized_group = IdentityGroupName.normalize(group_name)
        normalized_role = IdentityRoleSet.from_names((role,))[0].name
        row = self._fetch_one(
            """
            SELECT roles
            FROM identity_groups
            WHERE tenant_id = %(tenant_id)s AND name = %(group_name)s
            """,
            {"tenant_id": tenant_id.value, "group_name": normalized_group},
        )
        if row is None:
            raise ValidationError("identity group must exist before granting a role")
        roles = {str(item) for item in cast(Sequence[object], row.get("roles", []))}
        changed = normalized_role not in roles
        roles.add(normalized_role)
        self._execute_without_result(
            """
            UPDATE identity_groups
            SET roles = %(roles)s, updated_at = now()
            WHERE tenant_id = %(tenant_id)s AND name = %(group_name)s
            """,
            {
                "tenant_id": tenant_id.value,
                "group_name": normalized_group,
                "roles": sorted(roles),
            },
        )
        return changed

    def effective_identity_for_subject(
        self,
        tenant_id: TenantId,
        subject: str,
    ) -> EffectiveIdentity:
        normalized_subject = IdentitySubject.normalize(subject)
        user_row = self._fetch_one(
            """
            SELECT id, tenant_id, username, display_name, email, roles, active, created_at
            FROM identity_users
            WHERE tenant_id = %(tenant_id)s AND username = %(username)s
            """,
            {"tenant_id": tenant_id.value, "username": normalized_subject},
        )
        if user_row is None:
            return EffectiveIdentity.empty(tenant_id, normalized_subject)
        user = self._user_from_row(user_row)
        rows = self._fetch_all(
            """
            SELECT g.name AS group_name, g.roles AS group_roles
            FROM identity_group_memberships m
            JOIN identity_groups g
              ON g.tenant_id = m.tenant_id AND g.name = m.group_name
            WHERE m.tenant_id = %(tenant_id)s
              AND m.username = %(username)s
              AND g.active = true
            ORDER BY g.name ASC
            """,
            {"tenant_id": tenant_id.value, "username": normalized_subject},
        )
        group_names: list[str] = []
        group_roles: list[str] = []
        for row in rows:
            group_names.append(str(row["group_name"]))
            group_roles.extend(str(role) for role in cast(Sequence[object], row["group_roles"]))
        return EffectiveIdentity.from_parts(user, tuple(group_names), tuple(group_roles))

    def _user_from_row(self, row: Mapping[str, object]) -> IdentityUser:
        roles = row["roles"]
        return IdentityUser.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            email=str(row["email"]) if row.get("email") is not None else None,
            roles=tuple(str(role) for role in cast(Sequence[object], roles)),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLSecurityRepository(PostgreSQLRepositoryBase, SecurityRepository):
    def upsert_token(self, credential: ApiTokenCredential) -> None:
        self._ensure_tenant(credential.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO api_tokens (
                id, tenant_id, subject, token_hash, token_prefix, roles, active,
                expires_at, revoked_at, revoked_by, last_used_at, use_count
            ) VALUES (
                %(id)s, %(tenant_id)s, %(subject)s, %(token_hash)s,
                %(token_prefix)s, %(roles)s, %(active)s, %(expires_at)s,
                %(revoked_at)s, %(revoked_by)s, %(last_used_at)s, %(use_count)s
            )
            ON CONFLICT (tenant_id, token_hash) DO UPDATE SET
                subject = EXCLUDED.subject,
                token_prefix = EXCLUDED.token_prefix,
                roles = EXCLUDED.roles,
                active = EXCLUDED.active,
                expires_at = EXCLUDED.expires_at,
                revoked_at = EXCLUDED.revoked_at,
                revoked_by = EXCLUDED.revoked_by,
                last_used_at = COALESCE(api_tokens.last_used_at, EXCLUDED.last_used_at),
                use_count = GREATEST(api_tokens.use_count, EXCLUDED.use_count)
            """,
            {
                "id": credential.id.value,
                "tenant_id": credential.tenant_id.value,
                "subject": credential.subject,
                "token_hash": credential.token_hash,
                "token_prefix": credential.token_prefix,
                "roles": list(credential.role_names()),
                "active": credential.active,
                "expires_at": credential.expires_at,
                "revoked_at": credential.revoked_at,
                "revoked_by": credential.revoked_by,
                "last_used_at": credential.last_used_at,
                "use_count": credential.use_count,
            },
        )

    def find_active_token_by_hash(
        self,
        tenant_id: TenantId,
        token_hash: str,
    ) -> ApiTokenCredential | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, subject, token_hash, token_prefix, roles, active, created_at,
                   expires_at, revoked_at, revoked_by, last_used_at, use_count
            FROM api_tokens
            WHERE tenant_id = %(tenant_id)s
              AND token_hash = %(token_hash)s
              AND active = true
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > now())
            """,
            {"tenant_id": tenant_id.value, "token_hash": token_hash},
        )
        return self._credential_from_row(row) if row else None

    def revoke_token(self, tenant_id: TenantId, token_hash: str, actor: str) -> bool:
        updated = self._execute_without_result(
            """
            UPDATE api_tokens
            SET active = false, revoked_at = now(), revoked_by = %(actor)s
            WHERE tenant_id = %(tenant_id)s
              AND token_hash = %(token_hash)s
              AND active = true
              AND revoked_at IS NULL
            """,
            {"tenant_id": tenant_id.value, "token_hash": token_hash, "actor": actor},
        )
        rowcount = getattr(updated, "rowcount", None)
        return True if rowcount is None else int(rowcount) > 0

    def list_tokens(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> SecurityTokenPage:
        page = self._keyset_page(
            pagination,
            scope="security.api-tokens",
            tenant_id=tenant_id,
            filters={"include_inactive": include_inactive},
            fields=(
                CursorField("created_at", CursorDirection.ASC, CursorValueType.DATETIME),
                CursorField("id"),
            ),
        )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, subject, token_hash, token_prefix, roles, active, created_at,
                   expires_at, revoked_at, revoked_by, last_used_at, use_count
            FROM api_tokens
            WHERE tenant_id = %(tenant_id)s
              AND (
                %(include_inactive)s
                OR (
                    active = true
                    AND revoked_at IS NULL
                    AND (expires_at IS NULL OR expires_at > now())
                )
              )
              {page.where_sql}
            ORDER BY created_at ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {
                "tenant_id": tenant_id.value,
                "include_inactive": include_inactive,
                **page.parameters,
            },
        )
        selected_rows = tuple(rows[: pagination.limit])
        credentials = tuple(self._credential_from_row(row) for row in selected_rows)
        return SecurityTokenPage(credentials, page.next_cursor(rows))

    def record_token_used(self, tenant_id: TenantId, token_hash: str) -> None:
        self._execute_without_result(
            """
            UPDATE api_tokens
            SET last_used_at = now(), use_count = use_count + 1
            WHERE tenant_id = %(tenant_id)s AND token_hash = %(token_hash)s AND active = true
            """,
            {"tenant_id": tenant_id.value, "token_hash": token_hash},
        )

    def _credential_from_row(self, row: Mapping[str, object]) -> ApiTokenCredential:
        roles = row["roles"]
        return ApiTokenCredential.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            subject=str(row["subject"]),
            token_hash=str(row["token_hash"]),
            token_prefix=str(row["token_prefix"]),
            roles=tuple(str(role) for role in cast(Sequence[object], roles)),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
            expires_at=self._row_optional_datetime(row.get("expires_at")),
            revoked_at=self._row_optional_datetime(row.get("revoked_at")),
            revoked_by=str(row["revoked_by"]) if row.get("revoked_by") is not None else None,
            last_used_at=self._row_optional_datetime(row.get("last_used_at")),
            use_count=self._row_int_or_default(row, "use_count", 0),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    def _row_optional_datetime(self, value: object | None) -> datetime | None:
        if value is None:
            return None
        return self._row_datetime(value)


class PostgreSQLAccessPolicyRepository(PostgreSQLRepositoryBase, AccessPolicyRepository):
    def upsert_rule(self, rule: AccessPolicyRule) -> None:
        self._ensure_tenant(rule.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO access_policy_rules (
                id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                environments, active, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(permission)s, %(effect)s,
                %(subjects)s, %(roles)s, %(site_codes)s, %(environments)s,
                %(active)s, %(created_at)s
            )
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                permission = EXCLUDED.permission,
                effect = EXCLUDED.effect,
                subjects = EXCLUDED.subjects,
                roles = EXCLUDED.roles,
                site_codes = EXCLUDED.site_codes,
                environments = EXCLUDED.environments,
                active = EXCLUDED.active,
                updated_at = now()
            """,
            {
                "id": rule.id.value,
                "tenant_id": rule.tenant_id.value,
                "name": rule.name,
                "permission": rule.permission.value,
                "effect": rule.effect.value,
                "subjects": list(rule.subjects),
                "roles": list(rule.role_names()),
                "site_codes": list(rule.site_codes),
                "environments": list(rule.environments),
                "active": rule.active,
                "created_at": rule.created_at,
            },
        )

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> AccessPolicyRulePage:
        page = self._keyset_page(
            pagination,
            scope="security.access-policy-rules",
            tenant_id=tenant_id,
            filters={"include_inactive": include_inactive},
            fields=(CursorField("name"), CursorField("id")),
        )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                   environments, active, created_at
            FROM access_policy_rules
            WHERE tenant_id = %(tenant_id)s
              AND (%(include_inactive)s OR active = true)
              {page.where_sql}
            ORDER BY name ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {
                "tenant_id": tenant_id.value,
                "include_inactive": include_inactive,
                **page.parameters,
            },
        )
        selected_rows = tuple(rows[: pagination.limit])
        return AccessPolicyRulePage(
            tuple(self._rule_from_row(row) for row in selected_rows),
            page.next_cursor(rows),
        )

    def find_active_rules_for_permission(
        self,
        tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[AccessPolicyRule, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, permission, effect, subjects, roles, site_codes,
                   environments, active, created_at
            FROM access_policy_rules
            WHERE tenant_id = %(tenant_id)s
              AND permission = %(permission)s
              AND active = true
            ORDER BY name ASC, id ASC
            """,
            {"tenant_id": tenant_id.value, "permission": permission.value},
        )
        return tuple(self._rule_from_row(row) for row in rows)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        normalized_name = AccessPolicyRule.create(
            tenant_id,
            name,
            Permission.SCHEMA_READ,
            "allow",
        ).name
        cursor = self._execute_without_result(
            """
            UPDATE access_policy_rules
            SET active = false, updated_at = now()
            WHERE tenant_id = %(tenant_id)s AND name = %(name)s AND active = true
            """,
            {"tenant_id": tenant_id.value, "name": normalized_name},
        )
        rowcount = getattr(cursor, "rowcount", None)
        return True if rowcount is None else int(rowcount) > 0

    def _rule_from_row(self, row: Mapping[str, object]) -> AccessPolicyRule:
        return AccessPolicyRule.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=str(row["name"]),
            permission=str(row["permission"]),
            effect=str(row["effect"]),
            subjects=tuple(str(item) for item in cast(Sequence[object], row["subjects"])),
            roles=tuple(str(item) for item in cast(Sequence[object], row["roles"])),
            site_codes=tuple(str(item) for item in cast(Sequence[object], row["site_codes"])),
            environments=tuple(str(item) for item in cast(Sequence[object], row["environments"])),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLSourceGovernanceRepository(PostgreSQLRepositoryBase, SourceGovernanceRepository):
    def upsert_rule(self, rule: SourceGovernanceRule) -> None:
        self._ensure_tenant(rule.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO source_governance_rules (
                id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                priority, freshness_seconds, conflict_strategy, active, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(object_kind)s, %(attribute_path)s,
                %(authoritative_source)s, %(priority)s, %(freshness_seconds)s,
                %(conflict_strategy)s, %(active)s, %(created_at)s
            )
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                object_kind = EXCLUDED.object_kind,
                attribute_path = EXCLUDED.attribute_path,
                authoritative_source = EXCLUDED.authoritative_source,
                priority = EXCLUDED.priority,
                freshness_seconds = EXCLUDED.freshness_seconds,
                conflict_strategy = EXCLUDED.conflict_strategy,
                active = EXCLUDED.active
            """,
            self._rule_params(rule),
        )

    def find_rule(self, tenant_id: TenantId, name: str) -> SourceGovernanceRule | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                   priority, freshness_seconds, conflict_strategy, active, created_at
            FROM source_governance_rules
            WHERE tenant_id = %(tenant_id)s AND name = %(name)s
            """,
            {"tenant_id": tenant_id.value, "name": name.strip().lower()},
        )
        return self._rule_from_row(row) if row else None

    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool = False,
        object_kind: str | None = None,
    ) -> SourceGovernanceRulePage:
        normalized_kind = object_kind.strip().lower() if object_kind is not None else None
        page = self._keyset_page(
            pagination,
            scope="rsot.source-governance-rules",
            tenant_id=tenant_id,
            filters={"include_inactive": include_inactive, "object_kind": normalized_kind},
            fields=(
                CursorField("priority", CursorDirection.DESC, CursorValueType.INTEGER),
                CursorField("name"),
                CursorField("id"),
            ),
        )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                   priority, freshness_seconds, conflict_strategy, active, created_at
            FROM source_governance_rules
            WHERE tenant_id = %(tenant_id)s
              AND (%(include_inactive)s OR active IS TRUE)
              AND (
                %(object_kind)s IS NULL
                OR object_kind IS NULL
                OR object_kind = %(object_kind)s
              )
              {page.where_sql}
            ORDER BY priority DESC, name ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {
                "tenant_id": tenant_id.value,
                "include_inactive": include_inactive,
                "object_kind": normalized_kind,
                **page.parameters,
            },
        )
        selected = tuple(rows[: pagination.limit])
        return SourceGovernanceRulePage(
            tuple(self._rule_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    def find_active_rules_for_kind(
        self,
        tenant_id: TenantId,
        object_kind: str,
    ) -> tuple[SourceGovernanceRule, ...]:
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, name, object_kind, attribute_path, authoritative_source,
                   priority, freshness_seconds, conflict_strategy, active, created_at
            FROM source_governance_rules
            WHERE tenant_id = %(tenant_id)s
              AND active IS TRUE
              AND (object_kind IS NULL OR object_kind = %(object_kind)s)
            ORDER BY priority DESC, name ASC, id ASC
            """,
            {"tenant_id": tenant_id.value, "object_kind": object_kind.strip().lower()},
        )
        return tuple(self._rule_from_row(row) for row in rows)

    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        cursor = self._execute_without_result(
            """
            UPDATE source_governance_rules
            SET active = FALSE
            WHERE tenant_id = %(tenant_id)s AND name = %(name)s AND active IS TRUE
            """,
            {"tenant_id": tenant_id.value, "name": name.strip().lower()},
        )
        rowcount = getattr(cursor, "rowcount", None)
        return True if rowcount is None else int(rowcount) > 0

    def _rule_params(self, rule: SourceGovernanceRule) -> dict[str, object]:
        return {
            "id": rule.id.value,
            "tenant_id": rule.tenant_id.value,
            "name": rule.name.value,
            "object_kind": rule.object_kind.value if rule.object_kind else None,
            "attribute_path": rule.attribute_path.value,
            "authoritative_source": rule.authoritative_source.value,
            "priority": rule.priority,
            "freshness_seconds": rule.freshness_seconds,
            "conflict_strategy": rule.conflict_strategy.value,
            "active": rule.active,
            "created_at": rule.created_at,
        }

    def _rule_from_row(self, row: Mapping[str, object]) -> SourceGovernanceRule:
        return SourceGovernanceRule.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            name=str(row["name"]),
            object_kind=(str(row["object_kind"]) if row.get("object_kind") else None),
            attribute_path=str(row["attribute_path"]),
            authoritative_source=str(row["authoritative_source"]),
            priority=self._row_int(row, "priority"),
            freshness_seconds=(
                self._row_int(row, "freshness_seconds")
                if row.get("freshness_seconds") is not None
                else None
            ),
            conflict_strategy=str(row["conflict_strategy"]),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLSourceOfTruthRepository(PostgreSQLRepositoryBase, SourceOfTruthRepository):
    def create_object(
        self,
        tenant_id: TenantId,
        key: str,
        kind: str,
        display_name: str,
        attributes: dict[str, object],
        tags: tuple[str, ...],
        source: str,
        actor: str,
    ) -> SourceOfTruthObject:
        source_object = SourceOfTruthObject.create(
            tenant_id=tenant_id,
            key=key,
            kind=kind,
            display_name=display_name,
            attributes=attributes,
            tags=tags,
            source=source,
        )
        self.upsert_object(source_object, actor)
        return source_object

    def upsert_object(self, source_object: SourceOfTruthObject, actor: str) -> None:
        self._ensure_tenant(source_object.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO source_objects (
                id, tenant_id, object_key, kind, display_name, attributes, tags, source_system,
                version, status, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(object_key)s, %(kind)s, %(display_name)s,
                %(attributes)s, %(tags)s, %(source_system)s, %(version)s, %(status)s,
                %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, object_key) DO UPDATE SET
                kind = EXCLUDED.kind,
                display_name = EXCLUDED.display_name,
                attributes = EXCLUDED.attributes,
                tags = EXCLUDED.tags,
                source_system = EXCLUDED.source_system,
                version = EXCLUDED.version,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """,
            self._object_params(source_object),
        )
        snapshot = SourceObjectSnapshot.create(source_object, actor)
        self._execute_without_result(
            """
            INSERT INTO source_object_snapshots (
                id, tenant_id, object_key, object_id, version, payload, changed_by, changed_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(object_key)s, %(object_id)s, %(version)s,
                %(payload)s, %(changed_by)s, %(changed_at)s
            )
            ON CONFLICT (tenant_id, object_key, version) DO NOTHING
            """,
            {
                "id": snapshot.id.value,
                "tenant_id": snapshot.tenant_id.value,
                "object_key": snapshot.object_key.value,
                "object_id": snapshot.object_id.value,
                "version": snapshot.version,
                "payload": json.dumps(snapshot.payload, sort_keys=True),
                "changed_by": snapshot.changed_by,
                "changed_at": snapshot.changed_at,
            },
        )

    def find_object(self, tenant_id: TenantId, key: str) -> SourceOfTruthObject | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, kind, display_name, attributes, tags, source_system,
                   version, status, created_at, updated_at
            FROM source_objects
            WHERE tenant_id = %(tenant_id)s AND object_key = %(object_key)s
            """,
            {"tenant_id": tenant_id.value, "object_key": key.strip().lower()},
        )
        return self._object_from_row(row) if row else None

    def list_objects(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        tag: str | None = None,
        resource_type: str | None = None,
    ) -> SourceObjectPage:
        normalized_kind = kind.strip().lower() if kind is not None else None
        normalized_tag = tag.strip().lower() if tag is not None else None
        normalized_resource_type = (
            resource_type.strip().lower() if resource_type is not None else None
        )
        page = self._keyset_page(
            pagination,
            scope="rsot.source-objects",
            tenant_id=tenant_id,
            filters={
                "kind": normalized_kind,
                "tag": normalized_tag,
                "resource_type": normalized_resource_type,
            },
            fields=(CursorField("object_key"),),
        )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, object_key, kind, display_name, attributes, tags, source_system,
                   version, status, created_at, updated_at
            FROM source_objects
            WHERE tenant_id = %(tenant_id)s
              AND (%(kind)s IS NULL OR kind = %(kind)s)
              AND (%(tag)s IS NULL OR tags @> %(tag)s)
              AND (%(resource_type)s IS NULL OR attributes->>'resource_type' = %(resource_type)s)
              {page.where_sql}
            ORDER BY object_key ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {
                "tenant_id": tenant_id.value,
                "kind": normalized_kind,
                "tag": [normalized_tag] if normalized_tag is not None else None,
                "resource_type": normalized_resource_type,
                **page.parameters,
            },
        )
        selected = tuple(rows[: pagination.limit])
        return SourceObjectPage(
            tuple(self._object_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    def find_object_version(
        self,
        tenant_id: TenantId,
        key: str,
        version: int,
    ) -> SourceObjectSnapshot | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, object_id, version,
                   payload, changed_by, changed_at
            FROM source_object_snapshots
            WHERE tenant_id = %(tenant_id)s
              AND object_key = %(object_key)s
              AND version = %(version)s
            """,
            {
                "tenant_id": tenant_id.value,
                "object_key": key.strip().lower(),
                "version": int(version),
            },
        )
        return self._snapshot_from_row(row) if row else None

    def find_object_as_of(
        self,
        tenant_id: TenantId,
        key: str,
        as_of: datetime,
    ) -> SourceObjectSnapshot | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, object_key, object_id, version,
                   payload, changed_by, changed_at
            FROM source_object_snapshots
            WHERE tenant_id = %(tenant_id)s
              AND object_key = %(object_key)s
              AND changed_at <= %(as_of)s
            ORDER BY changed_at DESC, version DESC
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "object_key": key.strip().lower(),
                "as_of": as_of,
            },
        )
        return self._snapshot_from_row(row) if row else None

    def add_relation(self, relation: SourceRelation) -> None:
        self._ensure_tenant(relation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO source_relations (
                id, tenant_id, relation_type, source_key, target_key, provenance,
                valid_from, valid_to, active, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(relation_type)s, %(source_key)s, %(target_key)s,
                %(provenance)s, %(valid_from)s, %(valid_to)s, %(active)s, %(created_at)s
            )
            """,
            {
                "id": relation.id.value,
                "tenant_id": relation.tenant_id.value,
                "relation_type": relation.relation_type.value,
                "source_key": relation.source_key.value,
                "target_key": relation.target_key.value,
                "provenance": relation.provenance.value,
                "valid_from": relation.valid_from,
                "valid_to": relation.valid_to,
                "active": relation.active,
                "created_at": relation.created_at,
            },
        )

    def list_relations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_key: str | None = None,
        target_key: str | None = None,
        relation_type: str | None = None,
        as_of: datetime | None = None,
    ) -> SourceRelationPage:
        normalized_source = source_key.strip().lower() if source_key is not None else None
        normalized_target = target_key.strip().lower() if target_key is not None else None
        normalized_type = relation_type.strip().lower() if relation_type is not None else None
        page = self._keyset_page(
            pagination,
            scope="rsot.source-relations",
            tenant_id=tenant_id,
            filters={
                "source_key": normalized_source,
                "target_key": normalized_target,
                "relation_type": normalized_type,
                "as_of": as_of,
            },
            fields=(
                CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, relation_type, source_key, target_key, provenance,
                   valid_from, valid_to, active, created_at
            FROM source_relations
            WHERE tenant_id = %(tenant_id)s
              AND (%(source_key)s IS NULL OR source_key = %(source_key)s)
              AND (%(target_key)s IS NULL OR target_key = %(target_key)s)
              AND (%(relation_type)s IS NULL OR relation_type = %(relation_type)s)
              AND (%(as_of)s IS NULL OR (active = TRUE AND valid_from <= %(as_of)s
                   AND (valid_to IS NULL OR %(as_of)s < valid_to)))
              {page.where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {
                "tenant_id": tenant_id.value,
                "source_key": normalized_source,
                "target_key": normalized_target,
                "relation_type": normalized_type,
                "as_of": as_of,
                **page.parameters,
            },
        )
        selected = tuple(rows[: pagination.limit])
        return SourceRelationPage(
            tuple(self._relation_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    def _object_params(self, source_object: SourceOfTruthObject) -> dict[str, object]:
        return {
            "id": source_object.id.value,
            "tenant_id": source_object.tenant_id.value,
            "object_key": source_object.key.value,
            "kind": source_object.kind.value,
            "display_name": source_object.display_name,
            "attributes": json.dumps(source_object.attributes, sort_keys=True),
            "tags": [tag.value for tag in source_object.tags],
            "source_system": source_object.source.value,
            "version": source_object.version,
            "status": source_object.status.value,
            "created_at": source_object.created_at,
            "updated_at": source_object.updated_at,
        }

    def _object_from_row(self, row: Mapping[str, object]) -> SourceOfTruthObject:
        attributes = row["attributes"]
        return SourceOfTruthObject.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            key=str(row["object_key"]),
            kind=str(row["kind"]),
            display_name=str(row["display_name"]),
            attributes=(
                json.loads(str(attributes))
                if isinstance(attributes, str)
                else dict(cast(Mapping[str, Any], attributes))
            ),
            tags=tuple(str(item) for item in self._row_sequence(row, "tags")),
            source=str(row["source_system"]),
            version=self._row_int(row, "version"),
            status=str(row["status"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _snapshot_from_row(self, row: Mapping[str, object]) -> SourceObjectSnapshot:
        payload = row["payload"]
        return SourceObjectSnapshot.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            object_key=str(row["object_key"]),
            object_id=EntityId.from_value(str(row["object_id"])),
            version=self._row_int(row, "version"),
            payload=(
                json.loads(str(payload))
                if isinstance(payload, str)
                else dict(cast(Mapping[str, Any], payload))
            ),
            changed_by=str(row["changed_by"]),
            changed_at=self._row_datetime(row["changed_at"]),
        )

    def _relation_from_row(self, row: Mapping[str, object]) -> SourceRelation:
        return SourceRelation.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            relation_type=str(row["relation_type"]),
            source_key=str(row["source_key"]),
            target_key=str(row["target_key"]),
            provenance=str(row["provenance"]),
            valid_from=self._row_datetime(row["valid_from"]),
            valid_to=(self._row_datetime(row["valid_to"]) if row.get("valid_to") else None),
            active=bool(row["active"]),
            created_at=self._row_datetime(row["created_at"]),
        )

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLItamSupportRepository(PostgreSQLRepositoryBase, ItamSupportRepository):
    def save_organization(self, organization: ItamOrganization) -> None:
        self._execute_without_result(
            """
            INSERT INTO itam_organizations (
                organization_id, legal_name, display_name, status,
                registration_number, tax_identifier, country_code, city, postal_code, address,
                contact_email, phone, support_contact, description,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                %(organization_id)s, %(legal_name)s, %(display_name)s, %(status)s,
                %(registration_number)s, %(tax_identifier)s, %(country_code)s, %(city)s,
                %(postal_code)s, %(address)s, %(contact_email)s, %(phone)s,
                %(support_contact)s, %(description)s,
                %(created_by)s, %(created_at)s, %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (organization_id) DO UPDATE SET
                legal_name = EXCLUDED.legal_name,
                display_name = EXCLUDED.display_name,
                status = EXCLUDED.status,
                registration_number = EXCLUDED.registration_number,
                tax_identifier = EXCLUDED.tax_identifier,
                country_code = EXCLUDED.country_code,
                city = EXCLUDED.city,
                postal_code = EXCLUDED.postal_code,
                address = EXCLUDED.address,
                contact_email = EXCLUDED.contact_email,
                phone = EXCLUDED.phone,
                support_contact = EXCLUDED.support_contact,
                description = EXCLUDED.description,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "organization_id": organization.id.value,
                "legal_name": organization.legal_name.value,
                "display_name": organization.display_name.value,
                "status": organization.status.value,
                "registration_number": organization.registration_number,
                "tax_identifier": organization.tax_identifier,
                "country_code": organization.country_code,
                "city": organization.city,
                "postal_code": organization.postal_code,
                "address": organization.address,
                "contact_email": organization.contact_email,
                "phone": organization.phone,
                "support_contact": organization.support_contact,
                "description": organization.description,
                "created_by": organization.created_by,
                "created_at": organization.created_at,
                "updated_by": organization.updated_by,
                "updated_at": organization.updated_at,
            },
        )

    def find_organization(self, organization_id: str) -> ItamOrganization | None:
        row = self._fetch_one(
            """
            SELECT organization_id, legal_name, display_name, status,
                   registration_number, tax_identifier, country_code, city,
                   postal_code, address, contact_email, phone, support_contact, description,
                   created_by, created_at, updated_by, updated_at
            FROM itam_organizations
            WHERE organization_id = %(organization_id)s
            """,
            {"organization_id": TenantId.from_value(organization_id).value},
        )
        return self._organization_from_row(row) if row else None

    def list_organizations(self, include_retired: bool = False) -> tuple[ItamOrganization, ...]:
        if include_retired:
            rows = self._fetch_all(
                """
                SELECT organization_id, legal_name, display_name, status,
                       registration_number, tax_identifier, country_code, city,
                       postal_code, address, contact_email, phone, support_contact, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_organizations
                ORDER BY display_name ASC, organization_id ASC
                """,
                {},
            )
        else:
            rows = self._fetch_all(
                """
                SELECT organization_id, legal_name, display_name, status,
                       registration_number, tax_identifier, country_code, city,
                       postal_code, address, contact_email, phone, support_contact, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_organizations
                WHERE status <> 'retired'
                ORDER BY display_name ASC, organization_id ASC
                """,
                {},
            )
        if rows:
            return tuple(self._organization_from_row(row) for row in rows)
        default = ItamOrganization.create(
            organization_id="default",
            legal_name="Default Organization",
            display_name="Default",
            actor="system",
            registration_number="N/A",
            tax_identifier="N/A",
            country_code="FR",
            city="Non renseigné",
            postal_code="00000",
            address="Non renseigné",
            contact_email="contact@example.invalid",
            phone="+33000000000",
            support_contact="support@example.invalid",
            description="Compatibility organization for single-tenant installations.",
        )
        self.save_organization(default)
        return (default,)

    def _organization_from_row(self, row: Mapping[str, object]) -> ItamOrganization:
        return ItamOrganization.restore(
            organization_id=str(row["organization_id"]),
            legal_name=str(row["legal_name"]),
            display_name=str(row["display_name"]),
            status=str(row["status"]),
            registration_number=str(row["registration_number"]),
            tax_identifier=str(row["tax_identifier"]),
            country_code=str(row["country_code"]),
            city=str(row["city"]),
            postal_code=str(row.get("postal_code") or "00000"),
            address=str(row["address"]),
            contact_email=str(row["contact_email"]),
            phone=str(row.get("phone") or "+33000000000"),
            support_contact=str(row["support_contact"]),
            description=(None if row.get("description") is None else str(row.get("description"))),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def save_partner(self, partner: ItamPartner) -> None:
        self._execute_without_result(
            """
            INSERT INTO itam_partners (
                organization_id, partner_id, kind, legal_name, display_name, status,
                registration_number, tax_identifier, country_code, city, postal_code, address,
                contact_email, phone, support_contact, website, description,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                %(organization_id)s, %(partner_id)s, %(kind)s, %(legal_name)s,
                %(display_name)s, %(status)s, %(registration_number)s, %(tax_identifier)s,
                %(country_code)s, %(city)s, %(postal_code)s, %(address)s, %(contact_email)s,
                %(phone)s, %(support_contact)s, %(website)s, %(description)s, %(created_by)s,
                %(created_at)s, %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (organization_id, partner_id) DO UPDATE SET
                kind = EXCLUDED.kind,
                legal_name = EXCLUDED.legal_name,
                display_name = EXCLUDED.display_name,
                status = EXCLUDED.status,
                registration_number = EXCLUDED.registration_number,
                tax_identifier = EXCLUDED.tax_identifier,
                country_code = EXCLUDED.country_code,
                city = EXCLUDED.city,
                postal_code = EXCLUDED.postal_code,
                address = EXCLUDED.address,
                contact_email = EXCLUDED.contact_email,
                phone = EXCLUDED.phone,
                support_contact = EXCLUDED.support_contact,
                website = EXCLUDED.website,
                description = EXCLUDED.description,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            self._partner_params(partner),
        )

    def find_partner(self, organization_id: str, partner_id: str) -> ItamPartner | None:
        row = self._fetch_one(
            """
            SELECT organization_id, partner_id, kind, legal_name, display_name, status,
                   registration_number, tax_identifier, country_code, city,
                   postal_code, address, contact_email, phone, support_contact,
                   website, description,
                   created_by, created_at, updated_by, updated_at
            FROM itam_partners
            WHERE organization_id = %(organization_id)s AND partner_id = %(partner_id)s
            """,
            {
                "organization_id": TenantId.from_value(organization_id).value,
                "partner_id": TenantId.from_value(partner_id).value,
            },
        )
        return self._partner_from_row(row) if row else None

    def list_partners(
        self, organization_id: str | None = None, include_retired: bool = False
    ) -> tuple[ItamPartner, ...]:
        if organization_id is None and include_retired:
            rows = self._fetch_all(
                """
                SELECT organization_id, partner_id, kind, legal_name, display_name, status,
                       registration_number, tax_identifier, country_code, city,
                       postal_code, address, contact_email, phone, support_contact,
                   website, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_partners
                ORDER BY organization_id ASC, kind ASC, display_name ASC, partner_id ASC
                """,
                {},
            )
        elif organization_id is None:
            rows = self._fetch_all(
                """
                SELECT organization_id, partner_id, kind, legal_name, display_name, status,
                       registration_number, tax_identifier, country_code, city,
                       postal_code, address, contact_email, phone, support_contact,
                   website, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_partners
                WHERE status <> 'retired'
                ORDER BY organization_id ASC, kind ASC, display_name ASC, partner_id ASC
                """,
                {},
            )
        elif include_retired:
            rows = self._fetch_all(
                """
                SELECT organization_id, partner_id, kind, legal_name, display_name, status,
                       registration_number, tax_identifier, country_code, city,
                       postal_code, address, contact_email, phone, support_contact,
                   website, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_partners
                WHERE organization_id = %(organization_id)s
                ORDER BY kind ASC, display_name ASC, partner_id ASC
                """,
                {"organization_id": TenantId.from_value(organization_id).value},
            )
        else:
            rows = self._fetch_all(
                """
                SELECT organization_id, partner_id, kind, legal_name, display_name, status,
                       registration_number, tax_identifier, country_code, city,
                       postal_code, address, contact_email, phone, support_contact,
                   website, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_partners
                WHERE organization_id = %(organization_id)s AND status <> 'retired'
                ORDER BY kind ASC, display_name ASC, partner_id ASC
                """,
                {"organization_id": TenantId.from_value(organization_id).value},
            )
        return tuple(self._partner_from_row(row) for row in rows)

    def _partner_params(self, partner: ItamPartner) -> dict[str, object]:
        return {
            "organization_id": partner.organization_id.value,
            "partner_id": partner.id.value,
            "kind": partner.kind.value,
            "legal_name": partner.legal_name.value,
            "display_name": partner.display_name.value,
            "status": partner.status.value,
            "registration_number": partner.registration_number,
            "tax_identifier": partner.tax_identifier,
            "country_code": partner.country_code,
            "city": partner.city,
            "postal_code": partner.postal_code,
            "address": partner.address,
            "contact_email": partner.contact_email,
            "phone": partner.phone,
            "support_contact": partner.support_contact,
            "website": partner.website,
            "description": partner.description,
            "created_by": partner.created_by,
            "created_at": partner.created_at,
            "updated_by": partner.updated_by,
            "updated_at": partner.updated_at,
        }

    def _partner_from_row(self, row: Mapping[str, object]) -> ItamPartner:
        return ItamPartner.restore(
            partner_id=str(row["partner_id"]),
            organization_id=str(row["organization_id"]),
            kind=str(row["kind"]),
            legal_name=str(row["legal_name"]),
            display_name=str(row["display_name"]),
            status=str(row["status"]),
            registration_number=str(row["registration_number"]),
            tax_identifier=str(row["tax_identifier"]),
            country_code=str(row["country_code"]),
            city=str(row["city"]),
            postal_code=str(row.get("postal_code") or "00000"),
            address=str(row["address"]),
            contact_email=str(row["contact_email"]),
            phone=str(row["phone"]),
            support_contact=str(row["support_contact"]),
            website=(None if row.get("website") is None else str(row.get("website"))),
            description=(None if row.get("description") is None else str(row.get("description"))),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def save_tenant(self, tenant: ItamTenant) -> None:
        if self.find_organization(tenant.organization_id.value) is None:
            self.save_organization(
                ItamOrganization.create(
                    organization_id=tenant.organization_id.value,
                    legal_name=tenant.organization_id.value,
                    display_name=tenant.organization_id.value,
                    actor="system",
                    registration_number="N/A",
                    tax_identifier="N/A",
                    country_code="FR",
                    city="Non renseigné",
                    address="Non renseigné",
                    contact_email="contact@example.invalid",
                    support_contact="support@example.invalid",
                    description=(
                        "Compatibility organization automatically created for tenant attachment."
                    ),
                )
            )
        self._ensure_tenant(tenant.id)
        self._execute_without_result(
            """
            INSERT INTO itam_tenants (
                tenant_id, organization_id, name, status, is_default, description,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                %(tenant_id)s, %(organization_id)s, %(name)s, %(status)s,
                %(is_default)s, %(description)s, %(created_by)s, %(created_at)s,
                %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id) DO UPDATE SET
                organization_id = EXCLUDED.organization_id,
                name = EXCLUDED.name,
                status = EXCLUDED.status,
                is_default = EXCLUDED.is_default,
                description = EXCLUDED.description,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "tenant_id": tenant.id.value,
                "organization_id": tenant.organization_id.value,
                "name": tenant.name.value,
                "status": tenant.status.value,
                "is_default": tenant.is_default,
                "description": tenant.description,
                "created_by": tenant.created_by,
                "created_at": tenant.created_at,
                "updated_by": tenant.updated_by,
                "updated_at": tenant.updated_at,
            },
        )

    def find_tenant(self, tenant_id: TenantId) -> ItamTenant | None:
        row = self._fetch_one(
            """
            SELECT tenant_id, organization_id, name, status, is_default, description,
                   created_by, created_at, updated_by, updated_at
            FROM itam_tenants
            WHERE tenant_id = %(tenant_id)s
            """,
            {"tenant_id": tenant_id.value},
        )
        return self._tenant_from_row(row) if row else None

    def list_tenants(self, include_retired: bool = False) -> tuple[ItamTenant, ...]:
        query = """
            SELECT tenant_id, organization_id, name, status, is_default, description,
                   created_by, created_at, updated_by, updated_at
            FROM itam_tenants
            ORDER BY is_default DESC, name ASC, tenant_id ASC
            """
        if not include_retired:
            query = """
                SELECT tenant_id, organization_id, name, status, is_default, description,
                       created_by, created_at, updated_by, updated_at
                FROM itam_tenants
                WHERE status <> 'retired'
                ORDER BY is_default DESC, name ASC, tenant_id ASC
                """
        rows = self._fetch_all(query, {})
        if rows:
            return tuple(self._tenant_from_row(row) for row in rows)
        default = ItamTenant.create(
            tenant_id="default",
            organization_id="default",
            name="Default",
            actor="system",
            is_default=True,
            description="Default ITAM tenant created for single-tenant installations.",
        )
        self.save_tenant(default)
        return (default,)

    def clear_default_tenant(self, except_tenant_id: TenantId | None = None) -> None:
        if except_tenant_id is None:
            self._execute_without_result(
                "UPDATE itam_tenants SET is_default = false WHERE is_default = true",
                {},
            )
            return
        self._execute_without_result(
            """
            UPDATE itam_tenants
            SET is_default = false
            WHERE is_default = true AND tenant_id <> %(tenant_id)s
            """,
            {"tenant_id": except_tenant_id.value},
        )

    def _tenant_from_row(self, row: Mapping[str, object]) -> ItamTenant:
        return ItamTenant.restore(
            tenant_id=str(row["tenant_id"]),
            organization_id=str(row.get("organization_id", "default")),
            name=str(row["name"]),
            status=str(row["status"]),
            is_default=bool(row["is_default"]),
            description=(None if row.get("description") is None else str(row.get("description"))),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def save_support_profile(self, profile: PhysicalAssetSupportProfile) -> None:
        self._ensure_tenant(profile.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO asset_support_profiles (
                id, tenant_id, asset_tag, manufacturer_warranty, third_party_contracts,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(asset_tag)s, %(manufacturer_warranty)s,
                %(third_party_contracts)s, %(created_by)s, %(created_at)s,
                %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, asset_tag) DO UPDATE SET
                third_party_contracts = EXCLUDED.third_party_contracts,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "id": profile.id.value,
                "tenant_id": profile.tenant_id.value,
                "asset_tag": profile.asset_tag.value,
                "manufacturer_warranty": json.dumps(
                    profile.manufacturer_warranty.as_dict(), sort_keys=True
                ),
                "third_party_contracts": json.dumps(
                    [item.as_dict() for item in profile.third_party_contracts],
                    sort_keys=True,
                ),
                "created_by": profile.created_by,
                "created_at": profile.created_at,
                "updated_by": profile.updated_by,
                "updated_at": profile.updated_at,
            },
        )

    def find_support_profile(
        self, tenant_id: TenantId, asset_tag: str
    ) -> PhysicalAssetSupportProfile | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, asset_tag, manufacturer_warranty, third_party_contracts,
                   created_by, created_at, updated_by, updated_at
            FROM asset_support_profiles
            WHERE tenant_id = %(tenant_id)s AND asset_tag = %(asset_tag)s
            """,
            {
                "tenant_id": tenant_id.value,
                "asset_tag": Code.from_value(asset_tag, "asset tag").value,
            },
        )
        return self._profile_from_row(row) if row else None

    def _profile_from_row(self, row: Mapping[str, object]) -> PhysicalAssetSupportProfile:
        warranty_payload = self._json_mapping(row["manufacturer_warranty"])
        warranty = ManufacturerWarranty.restore(
            manufacturer=str(warranty_payload["manufacturer"]),
            manufacturer_partner_id=(
                None
                if not warranty_payload.get("manufacturer_partner_id")
                else str(warranty_payload.get("manufacturer_partner_id"))
            ),
            warranty_reference=str(warranty_payload["warranty_reference"]),
            warranty_level=str(warranty_payload["warranty_level"]),
            warranty_start=ItamDateParser.parse_date(
                str(warranty_payload["warranty_start"]), "manufacturer warranty start"
            ),
            warranty_end=ItamDateParser.parse_date(
                str(warranty_payload["warranty_end"]), "manufacturer warranty end"
            ),
            support_reference=str(warranty_payload["support_reference"]),
            support_level=str(warranty_payload["support_level"]),
            support_contact=str(warranty_payload["support_contact"]),
        )
        third_party_payload = self._json_sequence(row["third_party_contracts"])
        return PhysicalAssetSupportProfile.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            asset_tag=str(row["asset_tag"]),
            manufacturer_warranty=warranty,
            third_party_contracts=tuple(
                self._third_party_from_mapping(item)
                for item in third_party_payload
                if isinstance(item, Mapping)
            ),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _third_party_from_mapping(self, value: Mapping[str, object]) -> ThirdPartySupportContract:
        return ThirdPartySupportContract.restore(
            id=EntityId.from_value(str(value["id"])),
            provider=str(value["provider"]),
            provider_partner_id=(
                None
                if not value.get("provider_partner_id")
                else str(value.get("provider_partner_id"))
            ),
            contract_reference=str(value["contract_reference"]),
            support_level=str(value["support_level"]),
            support_start=ItamDateParser.parse_date(
                str(value["support_start"]), "third-party support start"
            ),
            support_end=ItamDateParser.parse_date(
                str(value["support_end"]), "third-party support end"
            ),
            support_contact=str(value["support_contact"]),
            status=str(value["status"]),
            notes=(None if value.get("notes") is None else str(value.get("notes"))),
            created_at=self._row_datetime(value["created_at"]),
        )

    def save_software_license(self, license_: SoftwareLicenseEntitlement) -> None:
        self._ensure_tenant(license_.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO software_license_entitlements (
                id, tenant_id, product_name, vendor, vendor_partner_id, version,
                license_reference, contract_reference, metric, purchased_quantity,
                assigned_quantity, entitlement_start, entitlement_end, status, owner, notes,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(product_name)s, %(vendor)s, %(vendor_partner_id)s,
                %(version)s, %(license_reference)s, %(contract_reference)s, %(metric)s,
                %(purchased_quantity)s, %(assigned_quantity)s, %(entitlement_start)s,
                %(entitlement_end)s, %(status)s, %(owner)s, %(notes)s,
                %(created_by)s, %(created_at)s, %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, license_reference) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                vendor = EXCLUDED.vendor,
                vendor_partner_id = EXCLUDED.vendor_partner_id,
                version = EXCLUDED.version,
                contract_reference = EXCLUDED.contract_reference,
                metric = EXCLUDED.metric,
                purchased_quantity = EXCLUDED.purchased_quantity,
                assigned_quantity = EXCLUDED.assigned_quantity,
                entitlement_start = EXCLUDED.entitlement_start,
                entitlement_end = EXCLUDED.entitlement_end,
                status = EXCLUDED.status,
                owner = EXCLUDED.owner,
                notes = EXCLUDED.notes,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "id": license_.id.value,
                "tenant_id": license_.tenant_id.value,
                "product_name": license_.product_name.value,
                "vendor": license_.vendor,
                "vendor_partner_id": license_.vendor_partner_id,
                "version": license_.version,
                "license_reference": license_.license_reference.value,
                "contract_reference": license_.contract_reference,
                "metric": license_.metric.value,
                "purchased_quantity": license_.purchased_quantity,
                "assigned_quantity": license_.assigned_quantity,
                "entitlement_start": license_.entitlement_start,
                "entitlement_end": license_.entitlement_end,
                "status": license_.status.value,
                "owner": license_.owner,
                "notes": license_.notes,
                "created_by": license_.created_by,
                "created_at": license_.created_at,
                "updated_by": license_.updated_by,
                "updated_at": license_.updated_at,
            },
        )

    def find_software_license(
        self, tenant_id: TenantId, license_reference: str
    ) -> SoftwareLicenseEntitlement | None:
        row = self._fetch_one(
            """
            SELECT id, tenant_id, product_name, vendor, vendor_partner_id, version,
                   license_reference, contract_reference, metric, purchased_quantity,
                   assigned_quantity, entitlement_start, entitlement_end, status, owner, notes,
                   created_by, created_at, updated_by, updated_at
            FROM software_license_entitlements
            WHERE tenant_id = %(tenant_id)s AND license_reference = %(license_reference)s
            """,
            {
                "tenant_id": tenant_id.value,
                "license_reference": Code.from_value(
                    license_reference, "software license reference"
                ).value,
            },
        )
        return self._software_license_from_row(row) if row else None

    def _software_license_from_row(self, row: Mapping[str, object]) -> SoftwareLicenseEntitlement:
        return SoftwareLicenseEntitlement.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            product_name=str(row["product_name"]),
            vendor=str(row["vendor"]),
            vendor_partner_id=(
                None if not row.get("vendor_partner_id") else str(row.get("vendor_partner_id"))
            ),
            version=(None if row.get("version") is None else str(row.get("version"))),
            license_reference=str(row["license_reference"]),
            contract_reference=(
                None
                if row.get("contract_reference") is None
                else str(row.get("contract_reference"))
            ),
            metric=str(row["metric"]),
            purchased_quantity=int(str(row["purchased_quantity"])),
            assigned_quantity=int(str(row["assigned_quantity"])),
            entitlement_start=ItamDateParser.parse_date(
                str(row["entitlement_start"]), "software entitlement start"
            ),
            entitlement_end=ItamDateParser.parse_date(
                str(row["entitlement_end"]), "software entitlement end"
            ),
            status=str(row["status"]),
            owner=(None if row.get("owner") is None else str(row.get("owner"))),
            notes=(None if row.get("notes") is None else str(row.get("notes"))),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _json_mapping(self, value: object) -> Mapping[str, object]:
        if isinstance(value, str):
            return cast(Mapping[str, object], json.loads(value))
        return cast(Mapping[str, object], value)

    def _json_sequence(self, value: object) -> Sequence[object]:
        if isinstance(value, str):
            return cast(Sequence[object], json.loads(value))
        return cast(Sequence[object], value)

    def _row_datetime(self, value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLFieldOperationRepository(PostgreSQLRepositoryBase, FieldOperationRepository):
    def save_sheet(self, sheet: FieldOperationSheet) -> None:
        self._ensure_tenant(sheet.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO field_operation_sheets (
                id, tenant_id, target_type, target_id, site_code, status,
                owner, operator_name, version, payload, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(target_type)s, %(target_id)s, %(site_code)s,
                %(status)s, %(owner)s, %(operator_name)s, %(version)s,
                %(payload)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                owner = EXCLUDED.owner,
                operator_name = EXCLUDED.operator_name,
                version = EXCLUDED.version,
                payload = EXCLUDED.payload,
                updated_at = EXCLUDED.updated_at
            """,
            {
                "id": sheet.id.value,
                "tenant_id": sheet.tenant_id.value,
                "target_type": sheet.target_type.value,
                "target_id": sheet.target_id,
                "site_code": sheet.location.site,
                "status": sheet.status.value,
                "owner": sheet.owner,
                "operator_name": sheet.operator,
                "version": sheet.version,
                "payload": json.dumps(sheet.as_dict(), sort_keys=True),
                "created_at": sheet.created_at,
                "updated_at": sheet.updated_at,
            },
        )

    def get_sheet(self, tenant_id: TenantId, sheet_id: str) -> FieldOperationSheet | None:
        row = self._fetch_one(
            """
            SELECT payload FROM field_operation_sheets
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(sheet_id).value},
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.sheet(self._json_mapping(row["payload"]))
        )

    def list_sheets(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: str | None = None,
        target_type: str | None = None,
        site: str | None = None,
    ) -> FieldOperationSheetPage:
        normalized_status = status.strip().lower() if status else None
        normalized_target = target_type.strip().lower().replace("_", "-") if target_type else None
        normalized_site = Code.from_value(site, "site code").value if site else None
        filters = {
            "status": normalized_status,
            "target_type": normalized_target,
            "site_code": normalized_site,
        }
        page = self._keyset_page(
            pagination,
            scope="field-operation.sheets",
            tenant_id=tenant_id,
            filters=filters,
            fields=(
                CursorField("updated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        clauses = ["tenant_id = %(tenant_id)s"]
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_status is not None:
            clauses.append("status = %(status)s")
            params["status"] = normalized_status
        if normalized_target is not None:
            clauses.append("target_type = %(target_type)s")
            params["target_type"] = normalized_target
        if normalized_site is not None:
            clauses.append("site_code = %(site_code)s")
            params["site_code"] = normalized_site
        rows = self._fetch_all(
            f"""
            SELECT payload, updated_at, id FROM field_operation_sheets
            WHERE {" AND ".join(clauses)} {page.where_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- predicates and keyset fields are validated internal values
            params,
        )
        selected = rows[: pagination.limit]
        return FieldOperationSheetPage(
            tuple(
                FieldOperationRecordMapper.sheet(self._json_mapping(row["payload"]))
                for row in selected
            ),
            page.next_cursor(rows),
        )

    def save_evidence(self, evidence: FieldEvidence) -> None:
        self._ensure_tenant(evidence.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO field_evidence (
                id, tenant_id, sheet_id, phase, status, content_sha256,
                size_bytes, payload, attached_at, validated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(sheet_id)s, %(phase)s, %(status)s,
                %(content_sha256)s, %(size_bytes)s, %(payload)s,
                %(attached_at)s, %(validated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                payload = EXCLUDED.payload,
                validated_at = EXCLUDED.validated_at
            """,
            {
                "id": evidence.id.value,
                "tenant_id": evidence.tenant_id.value,
                "sheet_id": evidence.sheet_id.value,
                "phase": evidence.phase.value,
                "status": evidence.status.value,
                "content_sha256": evidence.content_sha256,
                "size_bytes": evidence.size_bytes,
                "payload": json.dumps(evidence.as_dict(include_content=True), sort_keys=True),
                "attached_at": evidence.attached_at,
                "validated_at": evidence.validated_at,
            },
        )

    def get_evidence(self, tenant_id: TenantId, evidence_id: str) -> FieldEvidence | None:
        row = self._fetch_one(
            """
            SELECT payload FROM field_evidence
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(evidence_id).value},
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.evidence(self._json_mapping(row["payload"]))
        )

    def list_evidence(self, tenant_id: TenantId, sheet_id: str) -> tuple[FieldEvidence, ...]:
        rows = self._fetch_all(
            """
            SELECT payload FROM field_evidence
            WHERE tenant_id = %(tenant_id)s AND sheet_id = %(sheet_id)s
            ORDER BY attached_at ASC, id ASC
            """,
            {"tenant_id": tenant_id.value, "sheet_id": EntityId.from_value(sheet_id).value},
        )
        return tuple(
            FieldOperationRecordMapper.evidence(self._json_mapping(row["payload"])) for row in rows
        )

    def save_lock(self, lock: InterventionLock) -> None:
        self._ensure_tenant(lock.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO intervention_locks (
                id, tenant_id, sheet_id, target_type, target_id, idempotency_key,
                owner, status, acquired_at, expires_at, released_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(sheet_id)s, %(target_type)s, %(target_id)s,
                %(idempotency_key)s, %(owner)s, %(status)s, %(acquired_at)s,
                %(expires_at)s, %(released_at)s, %(payload)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                released_at = EXCLUDED.released_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": lock.id.value,
                "tenant_id": lock.tenant_id.value,
                "sheet_id": lock.sheet_id.value,
                "target_type": lock.target_type.value,
                "target_id": lock.target_id,
                "idempotency_key": lock.idempotency_key,
                "owner": lock.owner,
                "status": lock.status.value,
                "acquired_at": lock.acquired_at,
                "expires_at": lock.expires_at,
                "released_at": lock.released_at,
                "payload": json.dumps(lock.as_dict(), sort_keys=True),
            },
        )

    def get_lock(self, tenant_id: TenantId, lock_id: str) -> InterventionLock | None:
        row = self._fetch_one(
            """
            SELECT payload FROM intervention_locks
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(lock_id).value},
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.lock(self._json_mapping(row["payload"]))
        )

    def find_active_lock(
        self, tenant_id: TenantId, target_type: str, target_id: str
    ) -> InterventionLock | None:
        row = self._fetch_one(
            """
            SELECT payload FROM intervention_locks
            WHERE tenant_id = %(tenant_id)s AND target_type = %(target_type)s
              AND target_id = %(target_id)s AND status = 'active'
              AND expires_at > CURRENT_TIMESTAMP
            ORDER BY acquired_at DESC LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "target_type": target_type.strip().lower().replace("_", "-"),
                "target_id": target_id.strip(),
            },
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.lock(self._json_mapping(row["payload"]))
        )

    def find_lock_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> InterventionLock | None:
        row = self._fetch_one(
            """
            SELECT payload FROM intervention_locks
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.lock(self._json_mapping(row["payload"]))
        )

    def save_offline_package(self, package: OfflineSyncPackage) -> None:
        self._ensure_tenant(package.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO offline_sync_packages (
                id, tenant_id, sheet_id, idempotency_key, authorized_site, status,
                payload_sha256, created_at, expires_at, synchronized_at, package_payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(sheet_id)s, %(idempotency_key)s,
                %(authorized_site)s, %(status)s, %(payload_sha256)s, %(created_at)s,
                %(expires_at)s, %(synchronized_at)s, %(payload)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                synchronized_at = EXCLUDED.synchronized_at,
                package_payload = EXCLUDED.package_payload
            """,
            {
                "id": package.id.value,
                "tenant_id": package.tenant_id.value,
                "sheet_id": package.sheet_id.value,
                "idempotency_key": package.idempotency_key,
                "authorized_site": package.authorized_site,
                "status": package.status.value,
                "payload_sha256": package.payload_sha256,
                "created_at": package.created_at,
                "expires_at": package.expires_at,
                "synchronized_at": package.synchronized_at,
                "payload": json.dumps(package.as_dict(include_payload=True), sort_keys=True),
            },
        )

    def get_offline_package(
        self, tenant_id: TenantId, package_id: str
    ) -> OfflineSyncPackage | None:
        row = self._fetch_one(
            """
            SELECT package_payload FROM offline_sync_packages
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(package_id).value},
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.package(self._json_mapping(row["package_payload"]))
        )

    def find_offline_package_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> OfflineSyncPackage | None:
        row = self._fetch_one(
            """
            SELECT package_payload FROM offline_sync_packages
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return (
            None
            if row is None
            else FieldOperationRecordMapper.package(self._json_mapping(row["package_payload"]))
        )

    def list_offline_packages(
        self, tenant_id: TenantId, pagination: Pagination, sheet_id: str | None = None
    ) -> OfflineSyncPackagePage:
        normalized_sheet_id = EntityId.from_value(sheet_id).value if sheet_id is not None else None
        page = self._keyset_page(
            pagination,
            scope="field-operation.offline-packages",
            tenant_id=tenant_id,
            filters={"sheet_id": normalized_sheet_id},
            fields=(
                CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        predicate = "" if normalized_sheet_id is None else "AND sheet_id = %(sheet_id)s"
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_sheet_id is not None:
            params["sheet_id"] = normalized_sheet_id
        rows = self._fetch_all(
            f"""
            SELECT package_payload, created_at, id FROM offline_sync_packages
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- predicate and keyset fields are fixed internal values
            params,
        )
        selected = rows[: pagination.limit]
        return OfflineSyncPackagePage(
            tuple(
                FieldOperationRecordMapper.package(self._json_mapping(row["package_payload"]))
                for row in selected
            ),
            page.next_cursor(rows),
        )

    def append_event(self, event: DomainEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO field_event_outbox (
                id, tenant_id, aggregate_id, event_name, payload, occurred_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(event_name)s,
                %(payload)s, %(occurred_at)s
            )
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "event_name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("field operation payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLSimulationRepository(PostgreSQLRepositoryBase, SimulationRepository):
    def save_scenario(self, scenario: SimulationScenario) -> None:
        self._ensure_tenant(scenario.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO simulation_scenarios (
                id, tenant_id, idempotency_key, site_code, environment, criticality,
                status, owner_name, version, payload, created_at, updated_at,
                started_at, completed_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(idempotency_key)s, %(site_code)s,
                %(environment)s, %(criticality)s, %(status)s, %(owner_name)s,
                %(version)s, %(payload)s, %(created_at)s, %(updated_at)s,
                %(started_at)s, %(completed_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                version = EXCLUDED.version,
                payload = EXCLUDED.payload,
                updated_at = EXCLUDED.updated_at,
                started_at = EXCLUDED.started_at,
                completed_at = EXCLUDED.completed_at
            """,
            {
                "id": scenario.id.value,
                "tenant_id": scenario.tenant_id.value,
                "idempotency_key": scenario.idempotency_key,
                "site_code": scenario.site,
                "environment": scenario.environment,
                "criticality": scenario.criticality,
                "status": scenario.status.value,
                "owner_name": scenario.owner,
                "version": scenario.version,
                "payload": json.dumps(scenario.as_dict(), sort_keys=True),
                "created_at": scenario.created_at,
                "updated_at": scenario.updated_at,
                "started_at": scenario.started_at,
                "completed_at": scenario.completed_at,
            },
        )

    def get_scenario(self, tenant_id: TenantId, scenario_id: str) -> SimulationScenario | None:
        row = self._fetch_one(
            """
            SELECT payload FROM simulation_scenarios
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(scenario_id).value},
        )
        return (
            None
            if row is None
            else SimulationRecordMapper.scenario(self._json_mapping(row["payload"]))
        )

    def find_scenario_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> SimulationScenario | None:
        row = self._fetch_one(
            """
            SELECT payload FROM simulation_scenarios
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return (
            None
            if row is None
            else SimulationRecordMapper.scenario(self._json_mapping(row["payload"]))
        )

    def list_scenarios(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: str | None = None,
        site: str | None = None,
    ) -> SimulationScenarioPage:
        normalized_status = status.strip().lower() if status else None
        normalized_site = site.strip().lower().replace("_", "-") if site else None
        page = self._keyset_page(
            pagination,
            scope="simulation.scenarios",
            tenant_id=tenant_id,
            filters={"status": normalized_status, "site_code": normalized_site},
            fields=(
                CursorField("updated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        clauses = ["tenant_id = %(tenant_id)s"]
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_status is not None:
            clauses.append("status = %(status)s")
            params["status"] = normalized_status
        if normalized_site is not None:
            clauses.append("site_code = %(site_code)s")
            params["site_code"] = normalized_site
        rows = self._fetch_all(
            f"""
            SELECT payload, updated_at, id FROM simulation_scenarios
            WHERE {" AND ".join(clauses)} {page.where_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- predicates and keyset fields are validated internal values
            params,
        )
        selected = rows[: pagination.limit]
        return SimulationScenarioPage(
            tuple(
                SimulationRecordMapper.scenario(self._json_mapping(row["payload"]))
                for row in selected
            ),
            page.next_cursor(rows),
        )

    def save_report(self, report: SimulationImpactReport) -> None:
        self._ensure_tenant(report.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO simulation_impact_reports (
                id, tenant_id, scenario_id, scenario_version, input_sha256,
                risk_before, risk_after, readiness_score, impacted_count,
                truncated, payload, generated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(scenario_id)s, %(scenario_version)s,
                %(input_sha256)s, %(risk_before)s, %(risk_after)s,
                %(readiness_score)s, %(impacted_count)s, %(truncated)s,
                %(payload)s, %(generated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                payload = EXCLUDED.payload,
                risk_after = EXCLUDED.risk_after,
                readiness_score = EXCLUDED.readiness_score,
                impacted_count = EXCLUDED.impacted_count,
                truncated = EXCLUDED.truncated
            """,
            {
                "id": report.id.value,
                "tenant_id": report.tenant_id.value,
                "scenario_id": report.scenario_id.value,
                "scenario_version": report.scenario_version,
                "input_sha256": report.input_sha256,
                "risk_before": report.risk_before,
                "risk_after": report.risk_after,
                "readiness_score": report.readiness_scores[0].score,
                "impacted_count": len(report.impacted_keys),
                "truncated": report.truncated,
                "payload": json.dumps(report.as_dict(), sort_keys=True),
                "generated_at": report.generated_at,
            },
        )

    def get_report(self, tenant_id: TenantId, report_id: str) -> SimulationImpactReport | None:
        row = self._fetch_one(
            """
            SELECT payload FROM simulation_impact_reports
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(report_id).value},
        )
        return (
            None
            if row is None
            else SimulationRecordMapper.report(self._json_mapping(row["payload"]))
        )

    def find_latest_report(
        self, tenant_id: TenantId, scenario_id: str
    ) -> SimulationImpactReport | None:
        row = self._fetch_one(
            """
            SELECT payload FROM simulation_impact_reports
            WHERE tenant_id = %(tenant_id)s AND scenario_id = %(scenario_id)s
            ORDER BY generated_at DESC, id DESC LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "scenario_id": EntityId.from_value(scenario_id).value},
        )
        return (
            None
            if row is None
            else SimulationRecordMapper.report(self._json_mapping(row["payload"]))
        )

    def list_reports(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        scenario_id: str | None = None,
    ) -> SimulationImpactReportPage:
        normalized_scenario_id = (
            EntityId.from_value(scenario_id).value if scenario_id is not None else None
        )
        page = self._keyset_page(
            pagination,
            scope="simulation.reports",
            tenant_id=tenant_id,
            filters={"scenario_id": normalized_scenario_id},
            fields=(
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        predicate = "" if normalized_scenario_id is None else "AND scenario_id = %(scenario_id)s"
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_scenario_id is not None:
            params["scenario_id"] = normalized_scenario_id
        rows = self._fetch_all(
            f"""
            SELECT payload, generated_at, id FROM simulation_impact_reports
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY generated_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- predicate and keyset fields are fixed internal values
            params,
        )
        selected = rows[: pagination.limit]
        return SimulationImpactReportPage(
            tuple(
                SimulationRecordMapper.report(self._json_mapping(row["payload"]))
                for row in selected
            ),
            page.next_cursor(rows),
        )

    def save_comparison(self, comparison: SimulationScenarioComparison) -> None:
        self._ensure_tenant(comparison.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO simulation_scenario_comparisons (
                id, tenant_id, left_report_id, right_report_id,
                preferred_report_id, payload, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(left_report_id)s, %(right_report_id)s,
                %(preferred_report_id)s, %(payload)s, %(created_at)s
            )
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": comparison.id.value,
                "tenant_id": comparison.tenant_id.value,
                "left_report_id": comparison.left_report_id.value,
                "right_report_id": comparison.right_report_id.value,
                "preferred_report_id": (
                    comparison.preferred_report_id.value
                    if comparison.preferred_report_id is not None
                    else None
                ),
                "payload": json.dumps(comparison.as_dict(), sort_keys=True),
                "created_at": comparison.created_at,
            },
        )

    def get_comparison(
        self, tenant_id: TenantId, comparison_id: str
    ) -> SimulationScenarioComparison | None:
        row = self._fetch_one(
            """
            SELECT payload FROM simulation_scenario_comparisons
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(comparison_id).value},
        )
        return (
            None
            if row is None
            else SimulationRecordMapper.comparison(self._json_mapping(row["payload"]))
        )

    def list_comparisons(
        self, tenant_id: TenantId, pagination: Pagination
    ) -> SimulationComparisonPage:
        page = self._keyset_page(
            pagination,
            scope="simulation.comparisons",
            tenant_id=tenant_id,
            filters={},
            fields=(
                CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        rows = self._fetch_all(
            f"""
            SELECT payload, created_at, id FROM simulation_scenario_comparisons
            WHERE tenant_id = %(tenant_id)s {page.where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {"tenant_id": tenant_id.value, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return SimulationComparisonPage(
            tuple(
                SimulationRecordMapper.comparison(self._json_mapping(row["payload"]))
                for row in selected
            ),
            page.next_cursor(rows),
        )

    def append_event(self, event: DomainEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO simulation_event_outbox (
                id, tenant_id, aggregate_id, event_name, payload, occurred_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(event_name)s,
                %(payload)s, %(occurred_at)s
            )
            ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "event_name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("simulation payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLFinOpsRepository(PostgreSQLRepositoryBase, FinOpsRepository):
    def save_allocation_rule(self, rule: CostAllocationRule) -> None:
        self._upsert_payload(
            "finops_allocation_rules",
            rule.tenant_id,
            rule.id.value,
            rule.as_dict(),
            "priority, active, dimension",
            {
                "priority": rule.priority,
                "active": rule.active,
                "dimension": rule.dimension.value,
            },
        )

    def list_allocation_rules(
        self, tenant_id: TenantId, pagination: Pagination, active_only: bool = False
    ) -> CostAllocationRulePage:
        predicate = "AND active = TRUE" if active_only else ""
        rows, next_cursor = self._payload_page(
            "finops_allocation_rules",
            tenant_id,
            pagination,
            predicate,
            {},
            "priority ASC, id ASC",
        )
        return CostAllocationRulePage(
            tuple(FinOpsRecordMapper.allocation_rule(row) for row in rows), next_cursor
        )

    def save_import_job(self, job: CostImportJob) -> None:
        self._upsert_payload(
            "finops_import_jobs",
            job.tenant_id,
            job.id.value,
            job.as_dict(include_records=True),
            "idempotency_key, status, submitted_at",
            {
                "idempotency_key": job.idempotency_key,
                "status": job.status.value,
                "submitted_at": job.submitted_at,
            },
        )

    def get_import_job(self, tenant_id: TenantId, job_id: str) -> CostImportJob | None:
        value = self._get_payload("finops_import_jobs", tenant_id, job_id)
        return FinOpsRecordMapper.import_job(value) if value else None

    def find_import_job_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> CostImportJob | None:
        value = self._find_payload(
            "finops_import_jobs", tenant_id, "idempotency_key", idempotency_key.strip()
        )
        return FinOpsRecordMapper.import_job(value) if value else None

    def list_import_jobs(
        self, tenant_id: TenantId, pagination: Pagination, status: str | None = None
    ) -> CostImportJobPage:
        predicate = "" if status is None else "AND status = %(status)s"
        params: dict[str, object] = {} if status is None else {"status": status.strip().lower()}
        rows, next_cursor = self._payload_page(
            "finops_import_jobs",
            tenant_id,
            pagination,
            predicate,
            params,
            "submitted_at DESC, id DESC",
        )
        return CostImportJobPage(
            tuple(FinOpsRecordMapper.import_job(row) for row in rows), next_cursor
        )

    def save_cost_record(self, record: CostRecord) -> None:
        self._ensure_tenant(record.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO finops_cost_records (
                id, tenant_id, idempotency_key, period_start, period_end,
                currency, category, source, quality_status, amount, payload, created_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(idempotency_key)s, %(period_start)s, %(period_end)s,
                %(currency)s, %(category)s, %(source)s, %(quality_status)s, %(amount)s,
                %(payload)s, %(created_at)s
            )
            ON CONFLICT (tenant_id, period_start, id) DO UPDATE SET
                period_end = EXCLUDED.period_end,
                currency = EXCLUDED.currency,
                category = EXCLUDED.category,
                source = EXCLUDED.source,
                quality_status = EXCLUDED.quality_status,
                amount = EXCLUDED.amount,
                payload = EXCLUDED.payload
            """,
            {
                "id": record.id.value,
                "tenant_id": record.tenant_id.value,
                "idempotency_key": record.idempotency_key,
                "period_start": record.period_start,
                "period_end": record.period_end,
                "currency": record.currency,
                "category": record.category.value,
                "source": record.source,
                "quality_status": record.quality_status.value,
                "amount": record.amount,
                "payload": json.dumps(record.as_dict(), sort_keys=True),
                "created_at": record.imported_at,
            },
        )

    def find_cost_record_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> CostRecord | None:
        row = self._fetch_one(
            """
            SELECT payload FROM finops_cost_records
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            ORDER BY period_start DESC LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return (
            None
            if row is None
            else FinOpsRecordMapper.cost_record(self._json_mapping(row["payload"]))
        )

    def list_cost_records(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        period_start: date | None = None,
        period_end: date | None = None,
        currency: str | None = None,
        category: str | None = None,
        source: str | None = None,
        quality_status: str | None = None,
    ) -> CostRecordPage:
        filters: list[str] = []
        params: dict[str, object] = {}
        candidates = {
            "period_start": period_start,
            "period_end": period_end,
            "currency": currency.strip().upper() if currency else None,
            "category": category.strip().lower() if category else None,
            "source": source.strip().lower().replace("_", "-") if source else None,
            "quality_status": quality_status.strip().lower() if quality_status else None,
        }
        for name, value in candidates.items():
            if value is None:
                continue
            operator = ">=" if name == "period_start" else "<=" if name == "period_end" else "="
            filters.append(f"AND {name} {operator} %({name})s")
            params[name] = value
        rows, next_cursor = self._payload_page(
            "finops_cost_records",
            tenant_id,
            pagination,
            " ".join(filters),
            params,
            "period_start DESC, id DESC",
        )
        return CostRecordPage(
            tuple(FinOpsRecordMapper.cost_record(row) for row in rows), next_cursor
        )

    def save_budget(self, budget: FinOpsBudget) -> None:
        self._upsert_payload(
            "finops_budgets",
            budget.tenant_id,
            budget.id.value,
            budget.as_dict(),
            "dimension, target, period_start, period_end, currency",
            {
                "dimension": budget.dimension.value,
                "target": budget.target,
                "period_start": budget.period_start,
                "period_end": budget.period_end,
                "currency": budget.currency,
            },
        )

    def find_budget(
        self,
        tenant_id: TenantId,
        dimension: str,
        target: str,
        period_start: date,
        period_end: date,
        currency: str,
    ) -> FinOpsBudget | None:
        row = self._fetch_one(
            """
            SELECT payload FROM finops_budgets
            WHERE tenant_id = %(tenant_id)s AND dimension = %(dimension)s
              AND target = %(target)s AND period_start = %(period_start)s
              AND period_end = %(period_end)s AND currency = %(currency)s
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "dimension": dimension.strip().lower().replace("_", "-"),
                "target": target.strip().lower().replace("_", "-"),
                "period_start": period_start,
                "period_end": period_end,
                "currency": currency.strip().upper(),
            },
        )
        return (
            None if row is None else FinOpsRecordMapper.budget(self._json_mapping(row["payload"]))
        )

    def list_budgets(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        dimension: str | None = None,
        target: str | None = None,
        currency: str | None = None,
    ) -> FinOpsBudgetPage:
        predicate, params = self._optional_filters(
            {
                "dimension": dimension.strip().lower().replace("_", "-") if dimension else None,
                "target": target.strip().lower().replace("_", "-") if target else None,
                "currency": currency.strip().upper() if currency else None,
            }
        )
        rows, next_cursor = self._payload_page(
            "finops_budgets", tenant_id, pagination, predicate, params, "period_start DESC, id DESC"
        )
        return FinOpsBudgetPage(tuple(FinOpsRecordMapper.budget(row) for row in rows), next_cursor)

    def save_period(self, period: FinancialPeriod) -> None:
        self._upsert_payload(
            "finops_financial_periods",
            period.tenant_id,
            period.id.value,
            period.as_dict(),
            "period_start, period_end, currency, status",
            {
                "period_start": period.period_start,
                "period_end": period.period_end,
                "currency": period.currency,
                "status": period.status.value,
            },
        )

    def find_period(
        self, tenant_id: TenantId, period_start: date, period_end: date, currency: str
    ) -> FinancialPeriod | None:
        row = self._fetch_one(
            """
            SELECT payload FROM finops_financial_periods
            WHERE tenant_id = %(tenant_id)s AND period_start = %(period_start)s
              AND period_end = %(period_end)s AND currency = %(currency)s LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "period_start": period_start,
                "period_end": period_end,
                "currency": currency.strip().upper(),
            },
        )
        return (
            None if row is None else FinOpsRecordMapper.period(self._json_mapping(row["payload"]))
        )

    def list_periods(
        self, tenant_id: TenantId, pagination: Pagination, status: str | None = None
    ) -> FinancialPeriodPage:
        predicate = "" if status is None else "AND status = %(status)s"
        params: dict[str, object] = {} if status is None else {"status": status.strip().lower()}
        rows, next_cursor = self._payload_page(
            "finops_financial_periods",
            tenant_id,
            pagination,
            predicate,
            params,
            "period_start DESC, id DESC",
        )
        return FinancialPeriodPage(
            tuple(FinOpsRecordMapper.period(row) for row in rows), next_cursor
        )

    def save_anomaly(self, anomaly: CostAnomaly) -> None:
        self._upsert_payload(
            "finops_cost_anomalies",
            anomaly.tenant_id,
            anomaly.id.value,
            anomaly.as_dict(),
            "severity, detected_at",
            {"severity": anomaly.severity.value, "detected_at": anomaly.detected_at},
        )

    def list_anomalies(
        self, tenant_id: TenantId, pagination: Pagination, severity: str | None = None
    ) -> CostAnomalyPage:
        predicate = "" if severity is None else "AND severity = %(severity)s"
        params: dict[str, object] = (
            {} if severity is None else {"severity": severity.strip().lower()}
        )
        rows, next_cursor = self._payload_page(
            "finops_cost_anomalies",
            tenant_id,
            pagination,
            predicate,
            params,
            "detected_at DESC, id DESC",
        )
        return CostAnomalyPage(tuple(FinOpsRecordMapper.anomaly(row) for row in rows), next_cursor)

    def save_forecast(self, forecast: FinOpsForecast) -> None:
        self._upsert_payload(
            "finops_forecasts",
            forecast.tenant_id,
            forecast.id.value,
            forecast.as_dict(),
            "dimension, target, period_start, period_end",
            {
                "dimension": forecast.dimension.value,
                "target": forecast.target,
                "period_start": forecast.period_start,
                "period_end": forecast.period_end,
            },
        )

    def list_forecasts(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        dimension: str | None = None,
        target: str | None = None,
    ) -> FinOpsForecastPage:
        predicate, params = self._optional_filters(
            {
                "dimension": dimension.strip().lower().replace("_", "-") if dimension else None,
                "target": target.strip().lower().replace("_", "-") if target else None,
            }
        )
        rows, next_cursor = self._payload_page(
            "finops_forecasts",
            tenant_id,
            pagination,
            predicate,
            params,
            "period_start DESC, id DESC",
        )
        return FinOpsForecastPage(
            tuple(FinOpsRecordMapper.forecast(row) for row in rows), next_cursor
        )

    def save_report(self, report: FinOpsReport) -> None:
        self._upsert_payload(
            "finops_reports",
            report.tenant_id,
            report.id.value,
            report.as_dict(),
            "kind, currency, reproducibility_key, generated_at",
            {
                "kind": report.kind.value,
                "currency": report.currency,
                "reproducibility_key": report.reproducibility_key(),
                "generated_at": report.generated_at,
            },
        )

    def get_report(self, tenant_id: TenantId, report_id: str) -> FinOpsReport | None:
        value = self._get_payload("finops_reports", tenant_id, report_id)
        return FinOpsRecordMapper.report(value) if value else None

    def find_report_by_reproducibility_key(
        self, tenant_id: TenantId, reproducibility_key: str
    ) -> FinOpsReport | None:
        value = self._find_payload(
            "finops_reports", tenant_id, "reproducibility_key", reproducibility_key.strip().lower()
        )
        return FinOpsRecordMapper.report(value) if value else None

    def list_reports(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        kind: str | None = None,
        currency: str | None = None,
    ) -> FinOpsReportPage:
        predicate, params = self._optional_filters(
            {
                "kind": kind.strip().lower() if kind else None,
                "currency": currency.strip().upper() if currency else None,
            }
        )
        rows, next_cursor = self._payload_page(
            "finops_reports", tenant_id, pagination, predicate, params, "generated_at DESC, id DESC"
        )
        return FinOpsReportPage(tuple(FinOpsRecordMapper.report(row) for row in rows), next_cursor)

    def append_event(self, event: DomainEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO finops_event_outbox (
                id, tenant_id, aggregate_id, event_name, payload, occurred_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(event_name)s,
                %(payload)s, %(occurred_at)s
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "event_name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    def _upsert_payload(
        self,
        table: str,
        tenant_id: TenantId,
        identifier: str,
        payload: dict[str, object],
        column_list: str,
        values: dict[str, object],
    ) -> None:
        self._ensure_tenant(tenant_id)
        columns = [item.strip() for item in column_list.split(",") if item.strip()]
        insert_columns = ", ".join(columns)
        insert_values = ", ".join(f"%({column})s" for column in columns)
        updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in columns)
        query = f"""
            INSERT INTO {table} (id, tenant_id, {insert_columns}, payload)
            VALUES (%(id)s, %(tenant_id)s, {insert_values}, %(payload)s)
            ON CONFLICT (tenant_id, id) DO UPDATE SET {updates}, payload = EXCLUDED.payload
        """  # nosec B608 -- table and columns are fixed internal constants
        params = {
            "id": identifier,
            "tenant_id": tenant_id.value,
            "payload": json.dumps(payload, sort_keys=True),
            **values,
        }
        self._execute_without_result(query, params)

    def _get_payload(
        self, table: str, tenant_id: TenantId, identifier: str
    ) -> dict[str, Any] | None:
        query = f"SELECT payload FROM {table} WHERE tenant_id = %(tenant_id)s AND id = %(id)s"  # nosec B608
        row = self._fetch_one(
            query,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(identifier).value},
        )
        return None if row is None else self._json_mapping(row["payload"])

    def _find_payload(
        self, table: str, tenant_id: TenantId, column: str, value: object
    ) -> dict[str, Any] | None:
        lookup = (table, column)
        if lookup == ("finops_import_jobs", "idempotency_key"):
            query = """
                SELECT payload FROM finops_import_jobs
                WHERE tenant_id = %(tenant_id)s
                  AND idempotency_key = %(value)s
                LIMIT 1
            """
        elif lookup == ("finops_reports", "reproducibility_key"):
            query = """
                SELECT payload FROM finops_reports
                WHERE tenant_id = %(tenant_id)s
                  AND reproducibility_key = %(value)s
                LIMIT 1
            """
        else:
            raise ValueError("unsupported FinOps payload lookup")
        row = self._fetch_one(query, {"tenant_id": tenant_id.value, "value": value})
        return None if row is None else self._json_mapping(row["payload"])

    def _payload_page(
        self,
        table: str,
        tenant_id: TenantId,
        pagination: Pagination,
        predicate: str,
        extra_params: dict[str, object],
        ordering: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        field_catalog: dict[tuple[str, str], tuple[CursorField, ...]] = {
            ("finops_allocation_rules", "priority ASC, id ASC"): (
                CursorField("priority", value_type=CursorValueType.INTEGER),
                CursorField("id"),
            ),
            ("finops_import_jobs", "submitted_at DESC, id DESC"): (
                CursorField("submitted_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("finops_cost_records", "period_start DESC, id DESC"): (
                CursorField("period_start", CursorDirection.DESC, CursorValueType.DATE),
                CursorField("id", CursorDirection.DESC),
            ),
            ("finops_budgets", "period_start DESC, id DESC"): (
                CursorField("period_start", CursorDirection.DESC, CursorValueType.DATE),
                CursorField("id", CursorDirection.DESC),
            ),
            ("finops_financial_periods", "period_start DESC, id DESC"): (
                CursorField("period_start", CursorDirection.DESC, CursorValueType.DATE),
                CursorField("id", CursorDirection.DESC),
            ),
            ("finops_cost_anomalies", "detected_at DESC, id DESC"): (
                CursorField("detected_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("finops_forecasts", "period_start DESC, id DESC"): (
                CursorField("period_start", CursorDirection.DESC, CursorValueType.DATE),
                CursorField("id", CursorDirection.DESC),
            ),
            ("finops_reports", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        }
        fields = field_catalog.get((table, ordering))
        if fields is None:
            raise ValueError("unsupported FinOps pagination query")
        page = self._keyset_page(
            pagination,
            scope="finops." + table.removeprefix("finops_"),
            tenant_id=tenant_id,
            filters=extra_params,
            fields=fields,
        )
        field_names = ", ".join(field.name for field in fields)
        query = f"""
            SELECT payload, {field_names} FROM {table}
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY {ordering}
            LIMIT %(fetch_limit)s{page.offset_sql}
        """  # nosec B608 -- table, ordering and fields come from a closed internal catalog
        rows = self._fetch_all(
            query,
            {"tenant_id": tenant_id.value, **extra_params, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return (
            [self._json_mapping(row["payload"]) for row in selected],
            page.next_cursor(rows),
        )

    @staticmethod
    def _optional_filters(values: dict[str, object | None]) -> tuple[str, dict[str, object]]:
        params = {key: value for key, value in values.items() if value is not None}
        return " ".join(f"AND {key} = %({key})s" for key in params), params

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("finops payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLGreenOpsRepository(PostgreSQLRepositoryBase, GreenOpsRepository):
    def save_source(self, source: MeasurementSource) -> None:
        self._upsert_payload(
            "greenops_measurement_sources",
            source.tenant_id,
            source.id.value,
            source.as_dict(),
            {"code": source.code, "active": source.active, "created_at": source.created_at},
        )

    def find_source(self, tenant_id: TenantId, code: str) -> MeasurementSource | None:
        row = self._fetch_one(
            """
            SELECT payload FROM greenops_measurement_sources
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "code": code.strip().lower().replace("_", "-")},
        )
        return (
            None if row is None else GreenOpsRecordMapper.source(self._json_mapping(row["payload"]))
        )

    def list_sources(
        self, tenant_id: TenantId, pagination: Pagination, active_only: bool = False
    ) -> MeasurementSourcePage:
        predicate = "AND active = TRUE" if active_only else ""
        rows, cursor = self._payload_page(
            "greenops_measurement_sources", tenant_id, pagination, predicate, {}, "code, id"
        )
        return MeasurementSourcePage(
            tuple(GreenOpsRecordMapper.source(row) for row in rows), cursor
        )

    def save_policy(self, policy: GreenOpsPolicy) -> None:
        self._upsert_payload(
            "greenops_policies",
            policy.tenant_id,
            policy.id.value,
            policy.as_dict(),
            {"site_code": policy.site_code, "updated_at": policy.updated_at},
        )

    def get_policy(self, tenant_id: TenantId, site_code: str) -> GreenOpsPolicy | None:
        row = self._fetch_one(
            """
            SELECT payload FROM greenops_policies
            WHERE tenant_id = %(tenant_id)s AND site_code = %(site_code)s LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "site_code": site_code.strip().lower().replace("_", "-"),
            },
        )
        return (
            None if row is None else GreenOpsRecordMapper.policy(self._json_mapping(row["payload"]))
        )

    def save_carbon_factor(self, factor: CarbonFactor) -> None:
        self._upsert_payload(
            "greenops_carbon_factors",
            factor.tenant_id,
            factor.id.value,
            factor.as_dict(),
            {
                "code": factor.code,
                "region": factor.region,
                "period_start": factor.period_start,
                "period_end": factor.period_end,
                "created_at": factor.created_at,
            },
        )

    def list_carbon_factors(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        code: str | None = None,
        region: str | None = None,
    ) -> CarbonFactorPage:
        predicate, params = self._optional_filters(
            {
                "code": code.strip().lower().replace("_", "-") if code else None,
                "region": region.strip().lower().replace("_", "-") if region else None,
            }
        )
        rows, cursor = self._payload_page(
            "greenops_carbon_factors",
            tenant_id,
            pagination,
            predicate,
            params,
            "period_start DESC, created_at DESC, id DESC",
        )
        return CarbonFactorPage(tuple(GreenOpsRecordMapper.factor(row) for row in rows), cursor)

    def save_measurement(self, measurement: EnergyMeasurement) -> None:
        self._ensure_tenant(measurement.tenant_id)
        payload = json.dumps(measurement.as_dict(), sort_keys=True)
        payload_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        registry_row = self._fetch_one(
            """
            INSERT INTO greenops_measurement_idempotency (
                tenant_id, idempotency_key, measurement_id, period_start,
                payload_digest, created_at
            ) VALUES (
                %(tenant_id)s, %(idempotency_key)s, %(id)s, %(period_start)s,
                %(payload_digest)s, %(recorded_at)s
            )
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            RETURNING measurement_id, payload_digest
            """,
            {
                "tenant_id": measurement.tenant_id.value,
                "idempotency_key": measurement.idempotency_key,
                "id": measurement.id.value,
                "period_start": measurement.period_start,
                "payload_digest": payload_digest,
                "recorded_at": measurement.recorded_at,
            },
        )
        if registry_row is None:
            registry_row = self._fetch_one(
                """
                SELECT measurement_id, payload_digest
                FROM greenops_measurement_idempotency
                WHERE tenant_id = %(tenant_id)s
                  AND idempotency_key = %(idempotency_key)s
                LIMIT 1
                """,
                {
                    "tenant_id": measurement.tenant_id.value,
                    "idempotency_key": measurement.idempotency_key,
                },
            )
            if registry_row is None:
                raise OpenInfraError("GreenOps idempotency reservation could not be verified")
            if str(registry_row["payload_digest"]) != payload_digest:
                raise ValidationError(
                    "GreenOps idempotency key is already bound to another payload"
                )
            if str(registry_row["measurement_id"]) != measurement.id.value:
                raise ValidationError(
                    "GreenOps idempotent request is already committed or in progress; retry"
                )
        self._execute_without_result(
            """
            INSERT INTO greenops_energy_measurements (
                id, tenant_id, idempotency_key, source_code, kind, scope, scope_key,
                site_code, period_start, period_end, energy_kwh, recorded_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(idempotency_key)s, %(source_code)s, %(kind)s,
                %(scope)s, %(scope_key)s, %(site_code)s, %(period_start)s, %(period_end)s,
                %(energy_kwh)s, %(recorded_at)s, %(payload)s
            ) ON CONFLICT (tenant_id, period_start, id) DO UPDATE SET
                payload = EXCLUDED.payload,
                period_end = EXCLUDED.period_end,
                energy_kwh = EXCLUDED.energy_kwh
            """,
            {
                "id": measurement.id.value,
                "tenant_id": measurement.tenant_id.value,
                "idempotency_key": measurement.idempotency_key,
                "source_code": measurement.source_code,
                "kind": measurement.kind.value,
                "scope": measurement.scope.value,
                "scope_key": measurement.scope_key,
                "site_code": measurement.site_code,
                "period_start": measurement.period_start,
                "period_end": measurement.period_end,
                "energy_kwh": measurement.energy_kwh,
                "recorded_at": measurement.recorded_at,
                "payload": payload,
            },
        )

    def find_measurement_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> EnergyMeasurement | None:
        row = self._fetch_one(
            """
            SELECT measurement.payload
            FROM greenops_measurement_idempotency AS registry
            JOIN greenops_energy_measurements AS measurement
              ON measurement.tenant_id = registry.tenant_id
             AND measurement.id = registry.measurement_id
             AND measurement.period_start = registry.period_start
            WHERE registry.tenant_id = %(tenant_id)s
              AND registry.idempotency_key = %(idempotency_key)s
            LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return (
            None
            if row is None
            else GreenOpsRecordMapper.measurement(self._json_mapping(row["payload"]))
        )

    def list_measurements(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        site_code: str | None = None,
        scope: str | None = None,
        scope_key: str | None = None,
        kind: str | None = None,
    ) -> EnergyMeasurementPage:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if period_start is not None:
            clauses.append("period_end >= %(period_start)s")
            params["period_start"] = period_start
        if period_end is not None:
            clauses.append("period_start < %(period_end)s")
            params["period_end"] = period_end
        for key, value in {
            "site_code": site_code.strip().lower().replace("_", "-") if site_code else None,
            "scope": scope.strip().lower().replace("_", "-") if scope else None,
            "scope_key": scope_key.strip().lower().replace("_", "-") if scope_key else None,
            "kind": kind.strip().lower() if kind else None,
        }.items():
            if value is not None:
                clauses.append(f"{key} = %({key})s")
                params[key] = value
        predicate = "" if not clauses else "AND " + " AND ".join(clauses)
        rows, cursor = self._payload_page(
            "greenops_energy_measurements",
            tenant_id,
            pagination,
            predicate,
            params,
            "period_start DESC, id DESC",
        )
        return EnergyMeasurementPage(
            tuple(GreenOpsRecordMapper.measurement(row) for row in rows), cursor
        )

    def save_anomaly(self, anomaly: EnergyAnomaly) -> None:
        self._upsert_payload(
            "greenops_anomalies",
            anomaly.tenant_id,
            anomaly.id.value,
            anomaly.as_dict(),
            {
                "site_code": anomaly.site_code,
                "severity": anomaly.severity.value,
                "detected_at": anomaly.detected_at,
            },
        )

    def list_anomalies(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        severity: str | None = None,
        site_code: str | None = None,
    ) -> EnergyAnomalyPage:
        predicate, params = self._optional_filters(
            {
                "severity": severity.strip().lower() if severity else None,
                "site_code": site_code.strip().lower().replace("_", "-") if site_code else None,
            }
        )
        rows, cursor = self._payload_page(
            "greenops_anomalies",
            tenant_id,
            pagination,
            predicate,
            params,
            "detected_at DESC, id DESC",
        )
        return EnergyAnomalyPage(tuple(GreenOpsRecordMapper.anomaly(row) for row in rows), cursor)

    def save_forecast(self, forecast: CapacityForecast) -> None:
        self._upsert_payload(
            "greenops_forecasts",
            forecast.tenant_id,
            forecast.id.value,
            forecast.as_dict(),
            {
                "site_code": forecast.site_code,
                "dimension": forecast.dimension.value,
                "generated_at": forecast.generated_at,
            },
        )

    def list_forecasts(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        site_code: str | None = None,
        dimension: str | None = None,
    ) -> CapacityForecastPage:
        predicate, params = self._optional_filters(
            {
                "site_code": site_code.strip().lower().replace("_", "-") if site_code else None,
                "dimension": dimension.strip().lower().replace("_", "-") if dimension else None,
            }
        )
        rows, cursor = self._payload_page(
            "greenops_forecasts",
            tenant_id,
            pagination,
            predicate,
            params,
            "generated_at DESC, id DESC",
        )
        return CapacityForecastPage(
            tuple(GreenOpsRecordMapper.forecast(row) for row in rows), cursor
        )

    def save_candidate(self, candidate: ConsolidationCandidate) -> None:
        self._upsert_payload(
            "greenops_consolidation_candidates",
            candidate.tenant_id,
            candidate.id.value,
            candidate.as_dict(),
            {
                "site_code": candidate.site_code,
                "risk_level": candidate.risk_level.value,
                "generated_at": candidate.generated_at,
            },
        )

    def list_candidates(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        site_code: str | None = None,
        risk_level: str | None = None,
    ) -> ConsolidationCandidatePage:
        predicate, params = self._optional_filters(
            {
                "site_code": site_code.strip().lower().replace("_", "-") if site_code else None,
                "risk_level": risk_level.strip().lower() if risk_level else None,
            }
        )
        rows, cursor = self._payload_page(
            "greenops_consolidation_candidates",
            tenant_id,
            pagination,
            predicate,
            params,
            "generated_at DESC, id DESC",
        )
        return ConsolidationCandidatePage(
            tuple(GreenOpsRecordMapper.candidate(row) for row in rows), cursor
        )

    def save_score(self, score: GreenScore) -> None:
        self._upsert_payload(
            "greenops_scores",
            score.tenant_id,
            score.id.value,
            score.as_dict(),
            {"scope": score.scope, "generated_at": score.generated_at},
        )

    def list_scores(
        self, tenant_id: TenantId, pagination: Pagination, scope: str | None = None
    ) -> GreenScorePage:
        predicate, params = self._optional_filters(
            {
                "scope": scope.strip().lower().replace("_", "-") if scope else None,
            }
        )
        rows, cursor = self._payload_page(
            "greenops_scores",
            tenant_id,
            pagination,
            predicate,
            params,
            "generated_at DESC, id DESC",
        )
        return GreenScorePage(tuple(GreenOpsRecordMapper.score(row) for row in rows), cursor)

    def save_report(self, report: SustainabilityReport) -> None:
        self._upsert_payload(
            "greenops_reports",
            report.tenant_id,
            report.id.value,
            report.as_dict(),
            {
                "site_code": report.site_code,
                "scope": report.scope,
                "reproducibility_key": report.reproducibility_key(),
                "generated_at": report.generated_at,
            },
        )

    def get_report(self, tenant_id: TenantId, report_id: str) -> SustainabilityReport | None:
        row = self._fetch_one(
            """
            SELECT payload FROM greenops_reports
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(report_id).value},
        )
        return (
            None if row is None else GreenOpsRecordMapper.report(self._json_mapping(row["payload"]))
        )

    def find_report_by_reproducibility_key(
        self, tenant_id: TenantId, reproducibility_key: str
    ) -> SustainabilityReport | None:
        row = self._fetch_one(
            """
            SELECT payload FROM greenops_reports
            WHERE tenant_id = %(tenant_id)s AND reproducibility_key = %(key)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "key": reproducibility_key.strip().lower()},
        )
        return (
            None if row is None else GreenOpsRecordMapper.report(self._json_mapping(row["payload"]))
        )

    def list_reports(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        site_code: str | None = None,
        scope: str | None = None,
    ) -> SustainabilityReportPage:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if site_code:
            clauses.append("site_code = %(site_code)s")
            params["site_code"] = site_code.strip().lower().replace("_", "-")
        if scope:
            clauses.append("scope LIKE %(scope)s")
            params["scope"] = scope.strip().lower().replace("_", "-") + ":%"
        predicate = "" if not clauses else "AND " + " AND ".join(clauses)
        rows, cursor = self._payload_page(
            "greenops_reports",
            tenant_id,
            pagination,
            predicate,
            params,
            "generated_at DESC, id DESC",
        )
        return SustainabilityReportPage(
            tuple(GreenOpsRecordMapper.report(row) for row in rows), cursor
        )

    def append_event(self, event: DomainEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO greenops_event_outbox (
                id, tenant_id, aggregate_id, event_name, payload, occurred_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(event_name)s,
                %(payload)s, %(occurred_at)s
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "event_name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    def _upsert_payload(
        self,
        table: str,
        tenant_id: TenantId,
        identifier: str,
        payload: dict[str, object],
        values: dict[str, object],
    ) -> None:
        allowed = {
            "greenops_measurement_sources": ("code", "active", "created_at"),
            "greenops_policies": ("site_code", "updated_at"),
            "greenops_carbon_factors": (
                "code",
                "region",
                "period_start",
                "period_end",
                "created_at",
            ),
            "greenops_anomalies": ("site_code", "severity", "detected_at"),
            "greenops_forecasts": ("site_code", "dimension", "generated_at"),
            "greenops_consolidation_candidates": ("site_code", "risk_level", "generated_at"),
            "greenops_scores": ("scope", "generated_at"),
            "greenops_reports": ("site_code", "scope", "reproducibility_key", "generated_at"),
        }
        columns = allowed.get(table)
        if columns is None or tuple(values) != columns:
            raise ValueError("unsupported GreenOps payload table or columns")
        self._ensure_tenant(tenant_id)
        insert_columns = ", ".join(columns)
        insert_values = ", ".join(f"%({column})s" for column in columns)
        updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in columns)
        query = f"""
            INSERT INTO {table} (id, tenant_id, {insert_columns}, payload)
            VALUES (%(id)s, %(tenant_id)s, {insert_values}, %(payload)s)
            ON CONFLICT (tenant_id, id) DO UPDATE SET {updates}, payload = EXCLUDED.payload
        """  # nosec B608 -- table and columns are validated against a closed internal whitelist
        self._execute_without_result(
            query,
            {
                "id": identifier,
                "tenant_id": tenant_id.value,
                "payload": json.dumps(payload, sort_keys=True),
                **values,
            },
        )

    def _payload_page(
        self,
        table: str,
        tenant_id: TenantId,
        pagination: Pagination,
        predicate: str,
        params: dict[str, object],
        ordering: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        field_catalog: dict[tuple[str, str], tuple[CursorField, ...]] = {
            ("greenops_measurement_sources", "code, id"): (CursorField("code"), CursorField("id")),
            ("greenops_carbon_factors", "period_start DESC, created_at DESC, id DESC"): (
                CursorField("period_start", CursorDirection.DESC, CursorValueType.DATE),
                CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("greenops_energy_measurements", "period_start DESC, id DESC"): (
                CursorField("period_start", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("greenops_anomalies", "detected_at DESC, id DESC"): (
                CursorField("detected_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("greenops_forecasts", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("greenops_consolidation_candidates", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("greenops_scores", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("greenops_reports", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        }
        fields = field_catalog.get((table, ordering))
        if fields is None:
            raise ValueError("unsupported GreenOps pagination query")
        page = self._keyset_page(
            pagination,
            scope="greenops." + table.removeprefix("greenops_"),
            tenant_id=tenant_id,
            filters=params,
            fields=fields,
        )
        field_names = ", ".join(field.name for field in fields)
        query = f"""
            SELECT payload, {field_names} FROM {table}
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY {ordering}
            LIMIT %(fetch_limit)s{page.offset_sql}
        """  # nosec B608 -- table, ordering and fields come from a closed internal catalog
        rows = self._fetch_all(
            query,
            {"tenant_id": tenant_id.value, **params, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return [self._json_mapping(row["payload"]) for row in selected], page.next_cursor(rows)

    @staticmethod
    def _optional_filters(values: dict[str, object | None]) -> tuple[str, dict[str, object]]:
        params = {key: value for key, value in values.items() if value is not None}
        return " ".join(f"AND {key} = %({key})s" for key in params), params

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("GreenOps payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLKubernetesGitOpsRepository(PostgreSQLRepositoryBase, KubernetesGitOpsRepository):
    def save_state(self, state: KubernetesGitOpsState) -> None:
        self._ensure_tenant(state.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO kubernetes_gitops_states (
                id, tenant_id, cluster_key, environment, owner, revision, captured_at, imported_at,
                fingerprint, resource_count, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(cluster_key)s, %(environment)s, %(owner)s, %(revision)s,
                %(captured_at)s, %(imported_at)s, %(fingerprint)s, %(resource_count)s,
                %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                cluster_key = EXCLUDED.cluster_key,
                environment = EXCLUDED.environment,
                owner = EXCLUDED.owner,
                revision = EXCLUDED.revision,
                captured_at = EXCLUDED.captured_at,
                imported_at = EXCLUDED.imported_at,
                fingerprint = EXCLUDED.fingerprint,
                resource_count = EXCLUDED.resource_count,
                payload = EXCLUDED.payload
            """,
            {
                "id": state.id.value,
                "tenant_id": state.tenant_id.value,
                "cluster_key": state.cluster_key,
                "environment": state.environment,
                "owner": state.owner,
                "revision": state.revision,
                "captured_at": state.captured_at,
                "imported_at": state.imported_at,
                "fingerprint": state.fingerprint,
                "resource_count": len(state.resources),
                "payload": json.dumps(state.as_dict(include_resources=True), sort_keys=True),
            },
        )

    def get_state(self, tenant_id: TenantId, state_id: str) -> KubernetesGitOpsState | None:
        row = self._fetch_one(
            """
            SELECT payload FROM kubernetes_gitops_states
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(state_id).value},
        )
        return (
            None
            if row is None
            else KubernetesGitOpsRecordMapper.state(self._json_mapping(row["payload"]))
        )

    def find_state_by_fingerprint(
        self, tenant_id: TenantId, fingerprint: str
    ) -> KubernetesGitOpsState | None:
        row = self._fetch_one(
            """
            SELECT payload FROM kubernetes_gitops_states
            WHERE tenant_id = %(tenant_id)s AND fingerprint = %(fingerprint)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "fingerprint": fingerprint.strip().lower()},
        )
        return (
            None
            if row is None
            else KubernetesGitOpsRecordMapper.state(self._json_mapping(row["payload"]))
        )

    def find_latest_state(
        self, tenant_id: TenantId, cluster_key: str
    ) -> KubernetesGitOpsState | None:
        row = self._fetch_one(
            """
            SELECT payload FROM kubernetes_gitops_states
            WHERE tenant_id = %(tenant_id)s AND cluster_key = %(cluster_key)s
            ORDER BY captured_at DESC, imported_at DESC, id DESC
            LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "cluster_key": cluster_key.strip().lower()},
        )
        return (
            None
            if row is None
            else KubernetesGitOpsRecordMapper.state(self._json_mapping(row["payload"]))
        )

    def list_states(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        cluster_key: str | None = None,
        environment: str | None = None,
        owner: str | None = None,
    ) -> KubernetesGitOpsStatePage:
        filters = {
            "cluster_key": cluster_key.strip().lower() if cluster_key else None,
            "environment": environment.strip().lower() if environment else None,
            "owner": owner.strip().lower() if owner else None,
        }
        params = {key: value for key, value in filters.items() if value is not None}
        predicate = " ".join(f"AND {key} = %({key})s" for key in params)
        fields = (
            CursorField("captured_at", CursorDirection.DESC, CursorValueType.DATETIME),
            CursorField("imported_at", CursorDirection.DESC, CursorValueType.DATETIME),
            CursorField("id", CursorDirection.DESC),
        )
        page = self._keyset_page(
            pagination,
            scope="kubernetes.gitops.states",
            tenant_id=tenant_id,
            filters=params,
            fields=fields,
        )
        rows = self._fetch_all(
            f"""
            SELECT payload, captured_at, imported_at, id
            FROM kubernetes_gitops_states
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY captured_at DESC, imported_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- predicate and ordering use a closed internal field set
            {"tenant_id": tenant_id.value, **params, **page.parameters},
        )
        selected = rows[: pagination.limit]
        items = tuple(
            KubernetesGitOpsRecordMapper.state(self._json_mapping(row["payload"]))
            for row in selected
        )
        return KubernetesGitOpsStatePage(items, page.next_cursor(rows))

    def append_event(self, event: DomainEvent) -> None:
        self._execute_without_result(
            """
            INSERT INTO kubernetes_gitops_event_outbox (
                id, tenant_id, aggregate_id, name, payload, occurred_at, published_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(name)s, %(payload)s::jsonb,
                %(occurred_at)s, NULL
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("Kubernetes GitOps payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLKubernetesTopologyRepository(
    PostgreSQLRepositoryBase, KubernetesTopologyRepository
):
    def save_snapshot(self, snapshot: KubernetesTopologySnapshot) -> None:
        self._ensure_tenant(snapshot.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO kubernetes_topology_snapshots (
                id, tenant_id, cluster_key, provider, site_code, observed_at, imported_at,
                fingerprint, resource_count, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(cluster_key)s, %(provider)s, %(site_code)s,
                %(observed_at)s, %(imported_at)s, %(fingerprint)s, %(resource_count)s,
                %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                cluster_key = EXCLUDED.cluster_key,
                provider = EXCLUDED.provider,
                site_code = EXCLUDED.site_code,
                observed_at = EXCLUDED.observed_at,
                imported_at = EXCLUDED.imported_at,
                fingerprint = EXCLUDED.fingerprint,
                resource_count = EXCLUDED.resource_count,
                payload = EXCLUDED.payload
            """,
            {
                "id": snapshot.id.value,
                "tenant_id": snapshot.tenant_id.value,
                "cluster_key": snapshot.cluster_key,
                "provider": snapshot.provider,
                "site_code": snapshot.site_code,
                "observed_at": snapshot.observed_at,
                "imported_at": snapshot.imported_at,
                "fingerprint": snapshot.fingerprint,
                "resource_count": len(snapshot.resources),
                "payload": json.dumps(snapshot.as_dict(include_resources=True), sort_keys=True),
            },
        )

    def get_snapshot(
        self, tenant_id: TenantId, snapshot_id: str
    ) -> KubernetesTopologySnapshot | None:
        row = self._fetch_one(
            """
            SELECT payload FROM kubernetes_topology_snapshots
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(snapshot_id).value},
        )
        return (
            None
            if row is None
            else KubernetesTopologyRecordMapper.snapshot(self._json_mapping(row["payload"]))
        )

    def find_snapshot_by_fingerprint(
        self, tenant_id: TenantId, fingerprint: str
    ) -> KubernetesTopologySnapshot | None:
        row = self._fetch_one(
            """
            SELECT payload FROM kubernetes_topology_snapshots
            WHERE tenant_id = %(tenant_id)s AND fingerprint = %(fingerprint)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "fingerprint": fingerprint.strip().lower()},
        )
        return (
            None
            if row is None
            else KubernetesTopologyRecordMapper.snapshot(self._json_mapping(row["payload"]))
        )

    def find_latest_snapshot(
        self, tenant_id: TenantId, cluster_key: str
    ) -> KubernetesTopologySnapshot | None:
        row = self._fetch_one(
            """
            SELECT payload FROM kubernetes_topology_snapshots
            WHERE tenant_id = %(tenant_id)s AND cluster_key = %(cluster_key)s
            ORDER BY observed_at DESC, imported_at DESC, id DESC
            LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "cluster_key": cluster_key.strip().lower()},
        )
        return (
            None
            if row is None
            else KubernetesTopologyRecordMapper.snapshot(self._json_mapping(row["payload"]))
        )

    def list_snapshots(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        cluster_key: str | None = None,
        provider: str | None = None,
        site_code: str | None = None,
    ) -> KubernetesTopologySnapshotPage:
        filters = {
            "cluster_key": cluster_key.strip().lower() if cluster_key else None,
            "provider": provider.strip().lower() if provider else None,
            "site_code": site_code.strip().lower() if site_code else None,
        }
        params = {key: value for key, value in filters.items() if value is not None}
        predicate = " ".join(f"AND {key} = %({key})s" for key in params)
        fields = (
            CursorField("observed_at", CursorDirection.DESC, CursorValueType.DATETIME),
            CursorField("imported_at", CursorDirection.DESC, CursorValueType.DATETIME),
            CursorField("id", CursorDirection.DESC),
        )
        page = self._keyset_page(
            pagination,
            scope="kubernetes.topology.snapshots",
            tenant_id=tenant_id,
            filters=params,
            fields=fields,
        )
        rows = self._fetch_all(
            f"""
            SELECT payload, observed_at, imported_at, id
            FROM kubernetes_topology_snapshots
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY observed_at DESC, imported_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- predicate and ordering use a closed internal field set
            {"tenant_id": tenant_id.value, **params, **page.parameters},
        )
        selected = rows[: pagination.limit]
        items = tuple(
            KubernetesTopologyRecordMapper.snapshot(self._json_mapping(row["payload"]))
            for row in selected
        )
        return KubernetesTopologySnapshotPage(items, page.next_cursor(rows))

    def append_event(self, event: DomainEvent) -> None:
        self._execute_without_result(
            """
            INSERT INTO kubernetes_topology_event_outbox (
                id, tenant_id, aggregate_id, name, payload, occurred_at, published_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(name)s, %(payload)s::jsonb,
                %(occurred_at)s, NULL
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("Kubernetes topology payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLSbomRepository(PostgreSQLRepositoryBase, SbomRepository):
    def save_document(self, document: SbomDocument) -> None:
        self._ensure_tenant(document.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sbom_documents (
                id, tenant_id, application, release, environment, format, source_hash,
                fingerprint, document_version, component_count, imported_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(application)s, %(release)s, %(environment)s,
                %(format)s, %(source_hash)s, %(fingerprint)s, %(document_version)s,
                %(component_count)s, %(imported_at)s, %(payload)s
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                application = EXCLUDED.application, release = EXCLUDED.release,
                environment = EXCLUDED.environment, format = EXCLUDED.format,
                source_hash = EXCLUDED.source_hash, fingerprint = EXCLUDED.fingerprint,
                document_version = EXCLUDED.document_version,
                component_count = EXCLUDED.component_count,
                imported_at = EXCLUDED.imported_at, payload = EXCLUDED.payload
            """,
            {
                "id": document.id.value,
                "tenant_id": document.tenant_id.value,
                "application": document.application,
                "release": document.release,
                "environment": document.environment,
                "format": document.format.value,
                "source_hash": document.source_hash,
                "fingerprint": document.fingerprint,
                "document_version": document.document_version,
                "component_count": document.component_count,
                "imported_at": document.imported_at,
                "payload": json.dumps(document.as_dict(), sort_keys=True),
            },
        )

    def get_document(self, tenant_id: TenantId, document_id: str) -> SbomDocument | None:
        row = self._fetch_one(
            """
            SELECT payload FROM sbom_documents
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(document_id).value},
        )
        return (
            None if row is None else SbomRecordMapper.document(self._json_mapping(row["payload"]))
        )

    def find_document_by_fingerprint(
        self, tenant_id: TenantId, fingerprint: str
    ) -> SbomDocument | None:
        row = self._fetch_one(
            """
            SELECT payload FROM sbom_documents
            WHERE tenant_id = %(tenant_id)s AND fingerprint = %(fingerprint)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "fingerprint": fingerprint.strip().lower()},
        )
        return (
            None if row is None else SbomRecordMapper.document(self._json_mapping(row["payload"]))
        )

    def next_document_version(self, tenant_id: TenantId, application: str, environment: str) -> int:
        row = self._fetch_one(
            """
            SELECT COALESCE(MAX(document_version), 0) AS version
            FROM sbom_documents
            WHERE tenant_id = %(tenant_id)s AND application = %(application)s
              AND environment = %(environment)s
            """,
            {
                "tenant_id": tenant_id.value,
                "application": application.strip().lower().replace("_", "-"),
                "environment": environment.strip().lower().replace("_", "-"),
            },
        )
        raw_version = 0 if row is None else row.get("version", 0)
        try:
            return int(str(raw_version)) + 1
        except ValueError as exc:
            raise ValidationError("SBOM document version aggregate is invalid") from exc

    def list_documents(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        application: str | None = None,
        environment: str | None = None,
        format: str | None = None,
    ) -> SbomDocumentPage:
        predicate, params = self._filters(
            {
                "application": application.strip().lower().replace("_", "-")
                if application
                else None,
                "environment": environment.strip().lower().replace("_", "-")
                if environment
                else None,
                "format": format.strip().lower().replace("-", "") if format else None,
            }
        )
        rows, cursor = self._page(
            "sbom_documents", tenant_id, pagination, predicate, params, "imported_at DESC, id DESC"
        )
        return SbomDocumentPage(tuple(SbomRecordMapper.document(row) for row in rows), cursor)

    def save_vulnerability(self, vulnerability: VulnerabilityRecord) -> None:
        self._ensure_tenant(vulnerability.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sbom_vulnerabilities (
                id, tenant_id, cve_id, identity_key, cvss_score, known_exploited,
                imported_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(cve_id)s, %(identity_key)s, %(cvss_score)s,
                %(known_exploited)s, %(imported_at)s, %(payload)s
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                cve_id = EXCLUDED.cve_id, identity_key = EXCLUDED.identity_key,
                cvss_score = EXCLUDED.cvss_score, known_exploited = EXCLUDED.known_exploited,
                imported_at = EXCLUDED.imported_at, payload = EXCLUDED.payload
            """,
            {
                "id": vulnerability.id.value,
                "tenant_id": vulnerability.tenant_id.value,
                "cve_id": vulnerability.cve_id,
                "identity_key": vulnerability.identity_key,
                "cvss_score": vulnerability.cvss_score,
                "known_exploited": vulnerability.known_exploited,
                "imported_at": vulnerability.imported_at,
                "payload": json.dumps(vulnerability.as_dict(), sort_keys=True),
            },
        )

    def find_vulnerability_by_identity(
        self, tenant_id: TenantId, identity_key: str
    ) -> VulnerabilityRecord | None:
        row = self._fetch_one(
            """
            SELECT payload FROM sbom_vulnerabilities
            WHERE tenant_id = %(tenant_id)s AND identity_key = %(identity_key)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "identity_key": identity_key.strip()},
        )
        return (
            None
            if row is None
            else SbomRecordMapper.vulnerability(self._json_mapping(row["payload"]))
        )

    def list_vulnerabilities(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        cve_id: str | None = None,
        component: str | None = None,
        known_exploited: bool | None = None,
    ) -> VulnerabilityRecordPage:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if cve_id:
            clauses.append("cve_id = %(cve_id)s")
            params["cve_id"] = cve_id.strip().upper()
        if known_exploited is not None:
            clauses.append("known_exploited = %(known_exploited)s")
            params["known_exploited"] = known_exploited
        if component:
            clauses.append(
                "(payload ->> 'component_name' ILIKE %(component)s "
                "OR payload ->> 'component_purl' ILIKE %(component)s)"
            )
            params["component"] = f"%{component.strip()}%"
        predicate = "" if not clauses else "AND " + " AND ".join(clauses)
        rows, cursor = self._page(
            "sbom_vulnerabilities",
            tenant_id,
            pagination,
            predicate,
            params,
            "cvss_score DESC, cve_id, id",
        )
        return VulnerabilityRecordPage(
            tuple(SbomRecordMapper.vulnerability(row) for row in rows), cursor
        )

    def save_exposure(self, exposure: ExposureContext) -> None:
        self._ensure_tenant(exposure.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sbom_exposure_contexts (
                id, tenant_id, application, environment, internet_exposed, flow_exposed,
                business_criticality, updated_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(application)s, %(environment)s, %(internet_exposed)s,
                %(flow_exposed)s, %(business_criticality)s, %(updated_at)s, %(payload)s
            ) ON CONFLICT (tenant_id, application, environment) DO UPDATE SET
                id = EXCLUDED.id, internet_exposed = EXCLUDED.internet_exposed,
                flow_exposed = EXCLUDED.flow_exposed,
                business_criticality = EXCLUDED.business_criticality,
                updated_at = EXCLUDED.updated_at, payload = EXCLUDED.payload
            """,
            {
                "id": exposure.id.value,
                "tenant_id": exposure.tenant_id.value,
                "application": exposure.application,
                "environment": exposure.environment,
                "internet_exposed": exposure.internet_exposed,
                "flow_exposed": exposure.flow_exposed,
                "business_criticality": exposure.business_criticality,
                "updated_at": exposure.updated_at,
                "payload": json.dumps(exposure.as_dict(), sort_keys=True),
            },
        )

    def get_exposure(
        self, tenant_id: TenantId, application: str, environment: str
    ) -> ExposureContext | None:
        row = self._fetch_one(
            """
            SELECT payload FROM sbom_exposure_contexts
            WHERE tenant_id = %(tenant_id)s AND application = %(application)s
              AND environment = %(environment)s LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "application": application.strip().lower().replace("_", "-"),
                "environment": environment.strip().lower().replace("_", "-"),
            },
        )
        return (
            None if row is None else SbomRecordMapper.exposure(self._json_mapping(row["payload"]))
        )

    def list_exposures(self, tenant_id: TenantId, pagination: Pagination) -> ExposureContextPage:
        rows, cursor = self._page(
            "sbom_exposure_contexts", tenant_id, pagination, "", {}, "application, environment, id"
        )
        return ExposureContextPage(tuple(SbomRecordMapper.exposure(row) for row in rows), cursor)

    def replace_findings(
        self, tenant_id: TenantId, document_id: str, findings: tuple[RiskFinding, ...]
    ) -> None:
        normalized_document = EntityId.from_value(document_id).value
        self._execute_without_result(
            """
            DELETE FROM sbom_risk_findings
            WHERE tenant_id = %(tenant_id)s AND document_id = %(document_id)s
            """,
            {"tenant_id": tenant_id.value, "document_id": normalized_document},
        )
        for finding in findings:
            self._execute_without_result(
                """
                INSERT INTO sbom_risk_findings (
                    id, tenant_id, document_id, cve_id, priority, status, contextual_score,
                    generated_at, payload
                ) VALUES (
                    %(id)s, %(tenant_id)s, %(document_id)s, %(cve_id)s, %(priority)s,
                    %(status)s, %(contextual_score)s, %(generated_at)s, %(payload)s
                ) ON CONFLICT (tenant_id, id) DO NOTHING
                """,
                {
                    "id": finding.id.value,
                    "tenant_id": tenant_id.value,
                    "document_id": normalized_document,
                    "cve_id": finding.cve_id,
                    "priority": finding.priority.value,
                    "status": finding.status.value,
                    "contextual_score": finding.contextual_score,
                    "generated_at": finding.generated_at,
                    "payload": json.dumps(finding.as_dict(), sort_keys=True),
                },
            )

    def list_findings(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        document_id: str | None = None,
        priority: str | None = None,
        status: str | None = None,
    ) -> RiskFindingPage:
        predicate, params = self._filters(
            {
                "document_id": EntityId.from_value(document_id).value if document_id else None,
                "priority": priority.strip().lower() if priority else None,
                "status": status.strip().lower().replace("_", "-") if status else None,
            }
        )
        rows, cursor = self._page(
            "sbom_risk_findings",
            tenant_id,
            pagination,
            predicate,
            params,
            "contextual_score DESC, generated_at DESC, id DESC",
        )
        return RiskFindingPage(tuple(SbomRecordMapper.finding(row) for row in rows), cursor)

    def save_comparison(self, comparison: SbomComparison) -> None:
        self._ensure_tenant(comparison.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sbom_comparisons (
                id, tenant_id, base_document_id, target_document_id, input_digest,
                generated_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(base_document_id)s, %(target_document_id)s,
                %(input_digest)s, %(generated_at)s, %(payload)s
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                base_document_id = EXCLUDED.base_document_id,
                target_document_id = EXCLUDED.target_document_id,
                input_digest = EXCLUDED.input_digest, generated_at = EXCLUDED.generated_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": comparison.id.value,
                "tenant_id": comparison.tenant_id.value,
                "base_document_id": comparison.base_document_id,
                "target_document_id": comparison.target_document_id,
                "input_digest": comparison.input_digest,
                "generated_at": comparison.generated_at,
                "payload": json.dumps(comparison.as_dict(), sort_keys=True),
            },
        )

    def find_comparison_by_digest(
        self, tenant_id: TenantId, input_digest: str
    ) -> SbomComparison | None:
        row = self._fetch_one(
            """
            SELECT payload FROM sbom_comparisons
            WHERE tenant_id = %(tenant_id)s AND input_digest = %(input_digest)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "input_digest": input_digest.strip().lower()},
        )
        return (
            None if row is None else SbomRecordMapper.comparison(self._json_mapping(row["payload"]))
        )

    def get_comparison(self, tenant_id: TenantId, comparison_id: str) -> SbomComparison | None:
        row = self._fetch_one(
            """
            SELECT payload FROM sbom_comparisons
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(comparison_id).value},
        )
        return (
            None if row is None else SbomRecordMapper.comparison(self._json_mapping(row["payload"]))
        )

    def list_comparisons(self, tenant_id: TenantId, pagination: Pagination) -> SbomComparisonPage:
        rows, cursor = self._page(
            "sbom_comparisons", tenant_id, pagination, "", {}, "generated_at DESC, id DESC"
        )
        return SbomComparisonPage(tuple(SbomRecordMapper.comparison(row) for row in rows), cursor)

    def append_event(self, event: DomainEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO sbom_event_outbox (
                id, tenant_id, aggregate_id, event_name, payload, occurred_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(event_name)s,
                %(payload)s, %(occurred_at)s
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "event_name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    def _page(
        self,
        table: str,
        tenant_id: TenantId,
        pagination: Pagination,
        predicate: str,
        params: dict[str, object],
        ordering: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        field_catalog: dict[tuple[str, str], tuple[CursorField, ...]] = {
            ("sbom_documents", "imported_at DESC, id DESC"): (
                CursorField("imported_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("sbom_vulnerabilities", "cvss_score DESC, cve_id, id"): (
                CursorField("cvss_score", CursorDirection.DESC, CursorValueType.FLOAT),
                CursorField("cve_id"),
                CursorField("id"),
            ),
            ("sbom_exposure_contexts", "application, environment, id"): (
                CursorField("application"),
                CursorField("environment"),
                CursorField("id"),
            ),
            ("sbom_risk_findings", "contextual_score DESC, generated_at DESC, id DESC"): (
                CursorField("contextual_score", CursorDirection.DESC, CursorValueType.FLOAT),
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("sbom_comparisons", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        }
        fields = field_catalog.get((table, ordering))
        if fields is None:
            raise ValueError("unsupported SBOM pagination query")
        page = self._keyset_page(
            pagination,
            scope="sbom." + table.removeprefix("sbom_"),
            tenant_id=tenant_id,
            filters=params,
            fields=fields,
        )
        field_names = ", ".join(field.name for field in fields)
        query = f"""
            SELECT payload, {field_names} FROM {table}
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY {ordering}
            LIMIT %(fetch_limit)s{page.offset_sql}
        """  # nosec B608 -- table, ordering and fields come from a closed internal catalog
        rows = self._fetch_all(
            query,
            {"tenant_id": tenant_id.value, **params, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return [self._json_mapping(row["payload"]) for row in selected], page.next_cursor(rows)

    @staticmethod
    def _filters(values: dict[str, object | None]) -> tuple[str, dict[str, object]]:
        params = {key: value for key, value in values.items() if value is not None}
        return " ".join(f"AND {key} = %({key})s" for key in params), params

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("SBOM payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLRagRepository(PostgreSQLRepositoryBase, RagRepository):
    def save_document(self, document: RagDocument) -> None:
        self._ensure_tenant(document.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO rag_documents (
                id, tenant_id, source_type, source_ref, version, active, checksum,
                required_permissions, indexed_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(source_type)s, %(source_ref)s, %(version)s,
                %(active)s, %(checksum)s, %(required_permissions)s::jsonb,
                %(indexed_at)s, %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_ref = EXCLUDED.source_ref,
                version = EXCLUDED.version,
                active = EXCLUDED.active,
                checksum = EXCLUDED.checksum,
                required_permissions = EXCLUDED.required_permissions,
                indexed_at = EXCLUDED.indexed_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": document.id.value,
                "tenant_id": document.tenant_id.value,
                "source_type": document.source_type.value,
                "source_ref": document.source_ref,
                "version": document.version,
                "active": document.active,
                "checksum": document.checksum,
                "required_permissions": json.dumps(list(document.required_permissions)),
                "indexed_at": document.indexed_at,
                "payload": json.dumps(document.as_dict(), sort_keys=True),
            },
        )
        self._execute_without_result(
            """
            DELETE FROM rag_chunks
            WHERE tenant_id = %(tenant_id)s AND document_id = %(document_id)s
            """,
            {"tenant_id": document.tenant_id.value, "document_id": document.id.value},
        )
        for chunk in document.chunks:
            self._execute_without_result(
                """
                INSERT INTO rag_chunks (
                    id, tenant_id, document_id, ordinal, title, content,
                    required_permissions, payload
                ) VALUES (
                    %(id)s, %(tenant_id)s, %(document_id)s, %(ordinal)s,
                    %(title)s, %(content)s, %(required_permissions)s::jsonb,
                    %(payload)s::jsonb
                )
                """,
                {
                    "id": chunk.id.value,
                    "tenant_id": document.tenant_id.value,
                    "document_id": document.id.value,
                    "ordinal": chunk.ordinal,
                    "title": document.title,
                    "content": chunk.content,
                    "required_permissions": json.dumps(list(document.required_permissions)),
                    "payload": json.dumps(chunk.as_dict(), sort_keys=True),
                },
            )

    def get_document(self, tenant_id: TenantId, document_id: str) -> RagDocument | None:
        row = self._fetch_one(
            """
            SELECT payload FROM rag_documents
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(document_id).value},
        )
        return None if row is None else RagRecordMapper.document(self._json_mapping(row["payload"]))

    def find_active_document(
        self, tenant_id: TenantId, source_type: str, source_ref: str
    ) -> RagDocument | None:
        row = self._fetch_one(
            """
            SELECT payload FROM rag_documents
            WHERE tenant_id = %(tenant_id)s AND source_type = %(source_type)s
              AND source_ref = %(source_ref)s AND active = TRUE
            ORDER BY version DESC, indexed_at DESC LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "source_type": source_type.strip().lower().replace("_", "-"),
                "source_ref": " ".join(source_ref.strip().split()),
            },
        )
        return None if row is None else RagRecordMapper.document(self._json_mapping(row["payload"]))

    def list_documents(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        source_type: str | None = None,
        active: bool | None = None,
    ) -> RagDocumentPage:
        normalized_source_type = (
            source_type.strip().lower().replace("_", "-") if source_type else None
        )
        page = self._keyset_page(
            pagination,
            scope="rag.documents",
            tenant_id=tenant_id,
            filters={"source_type": normalized_source_type, "active": active},
            fields=(
                CursorField("indexed_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        predicates: list[str] = []
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_source_type is not None:
            predicates.append("source_type = %(source_type)s")
            params["source_type"] = normalized_source_type
        if active is not None:
            predicates.append("active = %(active)s")
            params["active"] = active
        suffix = "" if not predicates else " AND " + " AND ".join(predicates)
        query = f"""
            SELECT payload, indexed_at, id FROM rag_documents
            WHERE tenant_id = %(tenant_id)s {suffix} {page.where_sql}
            ORDER BY indexed_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
        """  # nosec B608 -- suffix contains only closed static predicates and keyset SQL
        rows = self._fetch_all(query, params)
        selected = rows[: pagination.limit]
        items = tuple(
            RagRecordMapper.document(self._json_mapping(row["payload"])) for row in selected
        )
        return RagDocumentPage(items, page.next_cursor(rows))

    def search(
        self,
        tenant_id: TenantId,
        query: str,
        permissions: frozenset[str],
        limit: int,
    ) -> RagSearchResult:
        params: dict[str, object] = {
            "tenant_id": tenant_id.value,
            "query": query,
            "permissions": sorted(permissions),
            "limit": limit,
        }
        rows = self._fetch_all(
            """
            SELECT d.payload AS document_payload, c.payload AS chunk_payload,
                   ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', %(query)s)) AS rank
            FROM rag_chunks c
            JOIN rag_documents d
              ON d.tenant_id = c.tenant_id AND d.id = c.document_id
            WHERE d.tenant_id = %(tenant_id)s
              AND d.active = TRUE
              AND c.search_vector @@ websearch_to_tsquery('simple', %(query)s)
              AND NOT EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(d.required_permissions) AS required(permission)
                  WHERE NOT (required.permission = ANY(%(permissions)s))
              )
            ORDER BY rank DESC, d.indexed_at DESC, c.ordinal ASC, c.id ASC
            LIMIT %(limit)s
            """,
            params,
        )
        filtered_row = self._fetch_one(
            """
            SELECT COUNT(DISTINCT d.id) AS total
            FROM rag_chunks c
            JOIN rag_documents d
              ON d.tenant_id = c.tenant_id AND d.id = c.document_id
            WHERE d.tenant_id = %(tenant_id)s
              AND d.active = TRUE
              AND c.search_vector @@ websearch_to_tsquery('simple', %(query)s)
              AND EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(d.required_permissions) AS required(permission)
                  WHERE NOT (required.permission = ANY(%(permissions)s))
              )
            """,
            params,
        )
        candidates = tuple(
            RagSearchCandidate(
                RagRecordMapper.document(self._json_mapping(row["document_payload"])),
                RagRecordMapper.chunk(self._json_mapping(row["chunk_payload"])),
                Decimal(str(row["rank"])),
            )
            for row in rows
        )
        filtered = 0 if filtered_row is None else int(str(filtered_row["total"]))
        return RagSearchResult(candidates, filtered)

    def save_answer(self, answer: RagAnswer) -> None:
        self._ensure_tenant(answer.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO rag_answers (
                id, tenant_id, question_hash, status, confidence, generated_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(question_hash)s, %(status)s,
                %(confidence)s, %(generated_at)s, %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                question_hash = EXCLUDED.question_hash,
                status = EXCLUDED.status,
                confidence = EXCLUDED.confidence,
                generated_at = EXCLUDED.generated_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": answer.id.value,
                "tenant_id": answer.tenant_id.value,
                "question_hash": answer.question_hash,
                "status": answer.status.value,
                "confidence": answer.confidence,
                "generated_at": answer.generated_at,
                "payload": json.dumps(answer.as_dict(), sort_keys=True),
            },
        )

    def get_answer(self, tenant_id: TenantId, answer_id: str) -> RagAnswer | None:
        row = self._fetch_one(
            """
            SELECT payload FROM rag_answers
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(answer_id).value},
        )
        return None if row is None else RagRecordMapper.answer(self._json_mapping(row["payload"]))

    def list_answers(self, tenant_id: TenantId, pagination: Pagination) -> RagAnswerPage:
        rows, cursor = self._page(
            "rag_answers", tenant_id, pagination, "generated_at DESC, id DESC"
        )
        return RagAnswerPage(tuple(RagRecordMapper.answer(row) for row in rows), cursor)

    def save_job(self, job: RagTransferJob) -> None:
        self._ensure_tenant(job.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO rag_jobs (
                id, tenant_id, kind, status, idempotency_key, input_digest,
                processed_count, total_count, created_at, updated_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(kind)s, %(status)s, %(idempotency_key)s,
                %(input_digest)s, %(processed_count)s, %(total_count)s,
                %(created_at)s, %(updated_at)s, %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                status = EXCLUDED.status,
                processed_count = EXCLUDED.processed_count,
                total_count = EXCLUDED.total_count,
                updated_at = EXCLUDED.updated_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": job.id.value,
                "tenant_id": job.tenant_id.value,
                "kind": job.kind.value,
                "status": job.status.value,
                "idempotency_key": job.idempotency_key,
                "input_digest": job.input_digest,
                "processed_count": job.processed_count,
                "total_count": job.total_count,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "payload": json.dumps(job.as_dict(), sort_keys=True),
            },
        )

    def get_job(self, tenant_id: TenantId, job_id: str) -> RagTransferJob | None:
        row = self._fetch_one(
            """
            SELECT payload FROM rag_jobs
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(job_id).value},
        )
        return None if row is None else RagRecordMapper.job(self._json_mapping(row["payload"]))

    def find_job_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> RagTransferJob | None:
        row = self._fetch_one(
            """
            SELECT payload FROM rag_jobs
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "idempotency_key": idempotency_key.strip().lower().replace("_", "-"),
            },
        )
        return None if row is None else RagRecordMapper.job(self._json_mapping(row["payload"]))

    def list_jobs(self, tenant_id: TenantId, pagination: Pagination) -> RagJobPage:
        rows, cursor = self._page("rag_jobs", tenant_id, pagination, "created_at DESC, id DESC")
        return RagJobPage(tuple(RagRecordMapper.job(row) for row in rows), cursor)

    def save_artifact(self, tenant_id: TenantId, job_id: str, artifact: RagArtifact) -> None:
        self._ensure_tenant(tenant_id)
        self._execute_without_result(
            """
            INSERT INTO rag_artifacts (
                tenant_id, job_id, filename, content_type, content, sha256, created_at
            ) VALUES (
                %(tenant_id)s, %(job_id)s, %(filename)s, %(content_type)s,
                %(content)s, %(sha256)s, NOW()
            ) ON CONFLICT (tenant_id, job_id) DO UPDATE SET
                filename = EXCLUDED.filename,
                content_type = EXCLUDED.content_type,
                content = EXCLUDED.content,
                sha256 = EXCLUDED.sha256,
                created_at = EXCLUDED.created_at
            """,
            {
                "tenant_id": tenant_id.value,
                "job_id": EntityId.from_value(job_id).value,
                "filename": artifact.filename,
                "content_type": artifact.content_type,
                "content": artifact.content,
                "sha256": artifact.sha256,
            },
        )

    def get_artifact(self, tenant_id: TenantId, job_id: str) -> RagArtifact | None:
        row = self._fetch_one(
            """
            SELECT filename, content_type, content, sha256 FROM rag_artifacts
            WHERE tenant_id = %(tenant_id)s AND job_id = %(job_id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "job_id": EntityId.from_value(job_id).value},
        )
        if row is None:
            return None
        raw_content = row["content"]
        if isinstance(raw_content, memoryview):
            content = raw_content.tobytes()
        elif isinstance(raw_content, (bytes, bytearray)):
            content = bytes(raw_content)
        else:
            raise ValidationError("stored RAG artifact content is invalid")
        artifact = RagArtifact.create(str(row["filename"]), str(row["content_type"]), content)
        if artifact.sha256 != str(row["sha256"]):
            raise ValidationError("stored RAG artifact checksum is invalid")
        return artifact

    def append_event(self, event: DomainEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO rag_event_outbox (
                id, tenant_id, aggregate_id, event_name, payload, occurred_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_id)s, %(event_name)s,
                %(payload)s::jsonb, %(occurred_at)s
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "aggregate_id": event.aggregate_id.value,
                "event_name": event.name,
                "payload": json.dumps(event.payload, sort_keys=True),
                "occurred_at": event.occurred_at,
            },
        )

    def _page(
        self,
        table: str,
        tenant_id: TenantId,
        pagination: Pagination,
        ordering: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        field_catalog: dict[tuple[str, str], tuple[CursorField, ...]] = {
            ("rag_answers", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("rag_jobs", "created_at DESC, id DESC"): (
                CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        }
        fields = field_catalog.get((table, ordering))
        if fields is None:
            raise ValueError("unsupported RAG pagination query")
        page = self._keyset_page(
            pagination,
            scope="rag." + table.removeprefix("rag_"),
            tenant_id=tenant_id,
            filters={},
            fields=fields,
        )
        field_names = ", ".join(field.name for field in fields)
        query = f"""
            SELECT payload, {field_names} FROM {table}
            WHERE tenant_id = %(tenant_id)s {page.where_sql}
            ORDER BY {ordering}
            LIMIT %(fetch_limit)s{page.offset_sql}
        """  # nosec B608 -- table, ordering and fields come from a closed internal catalog
        rows = self._fetch_all(query, {"tenant_id": tenant_id.value, **page.parameters})
        selected = rows[: pagination.limit]
        return [self._json_mapping(row["payload"]) for row in selected], page.next_cursor(rows)

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, Mapping):
            raise ValidationError("stored RAG payload must be a JSON object")
        return {str(key): item for key, item in value.items()}


class PostgreSQLMultisiteRepository(PostgreSQLRepositoryBase, MultisiteRepository):
    def save_grant(self, grant: SiteAccessGrant) -> None:
        self._ensure_tenant(grant.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO multisite_site_access_grants (
                id, tenant_id, subject, site_code, access_level, active,
                granted_by, created_at, updated_at, revoked_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(subject)s, %(site_code)s, %(access_level)s,
                %(active)s, %(granted_by)s, %(created_at)s, %(updated_at)s,
                %(revoked_at)s, %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, subject, site_code) DO UPDATE SET
                id = EXCLUDED.id, access_level = EXCLUDED.access_level,
                active = EXCLUDED.active, granted_by = EXCLUDED.granted_by,
                updated_at = EXCLUDED.updated_at, revoked_at = EXCLUDED.revoked_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": grant.id.value,
                "tenant_id": grant.tenant_id.value,
                "subject": grant.subject,
                "site_code": grant.site_code,
                "access_level": grant.access_level.label,
                "active": grant.active,
                "granted_by": grant.granted_by,
                "created_at": grant.created_at,
                "updated_at": grant.updated_at,
                "revoked_at": grant.revoked_at,
                "payload": json.dumps(grant.as_dict(), sort_keys=True),
            },
        )

    def find_grant(
        self, tenant_id: TenantId, subject: str, site_code: str
    ) -> SiteAccessGrant | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_site_access_grants
            WHERE tenant_id = %(tenant_id)s AND subject = %(subject)s
              AND site_code = %(site_code)s LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "subject": subject.strip().lower(),
                "site_code": Code.from_value(site_code, "site code").value,
            },
        )
        return None if row is None else self._grant(self._json_mapping(row["payload"]))

    def list_grants(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        subject: str | None = None,
        site_code: str | None = None,
        active_only: bool = True,
    ) -> SiteAccessGrantPage:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if subject:
            clauses.append("subject = %(subject)s")
            params["subject"] = subject.strip().lower()
        if site_code:
            clauses.append("site_code = %(site_code)s")
            params["site_code"] = Code.from_value(site_code, "site code").value
        if active_only:
            clauses.append("active = TRUE")
        predicate = "" if not clauses else "AND " + " AND ".join(clauses)
        rows, cursor = self._page(
            "multisite_site_access_grants",
            tenant_id,
            pagination,
            predicate,
            params,
            "subject, site_code, id",
        )
        return SiteAccessGrantPage(tuple(self._grant(row) for row in rows), cursor)

    def save_report(self, report: MultisitePortfolioReport) -> None:
        self._ensure_tenant(report.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO multisite_reports (
                id, tenant_id, requested_subject, generated_by, generated_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(requested_subject)s, %(generated_by)s,
                %(generated_at)s, %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO UPDATE SET
                requested_subject = EXCLUDED.requested_subject,
                generated_by = EXCLUDED.generated_by,
                generated_at = EXCLUDED.generated_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": report.id.value,
                "tenant_id": report.tenant_id.value,
                "requested_subject": report.requested_subject,
                "generated_by": report.generated_by,
                "generated_at": report.generated_at,
                "payload": json.dumps(report.as_dict(), sort_keys=True),
            },
        )

    def get_report(self, tenant_id: TenantId, report_id: str) -> MultisitePortfolioReport | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_reports
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(report_id).value},
        )
        return None if row is None else self._report(self._json_mapping(row["payload"]))

    def list_reports(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        requested_subject: str | None = None,
    ) -> MultisiteReportPage:
        predicate = ""
        params: dict[str, object] = {}
        if requested_subject:
            predicate = "AND requested_subject = %(requested_subject)s"
            params["requested_subject"] = requested_subject.strip().lower()
        rows, cursor = self._page(
            "multisite_reports",
            tenant_id,
            pagination,
            predicate,
            params,
            "generated_at DESC, id DESC",
        )
        return MultisiteReportPage(tuple(self._report(row) for row in rows), cursor)

    def save_regional_route(self, route: RegionalDiscoveryRoute) -> None:
        self._ensure_tenant(route.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO multisite_regional_discovery_routes (
                id, tenant_id, region_code, site_code, vrf_code, collector_id,
                discovery_scope, active, configured_by, created_at, updated_at,
                disabled_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(region_code)s, %(site_code)s, %(vrf_code)s,
                %(collector_id)s, %(discovery_scope)s, %(active)s, %(configured_by)s,
                %(created_at)s, %(updated_at)s, %(disabled_at)s, %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, region_code, site_code, vrf_code) DO UPDATE SET
                id = EXCLUDED.id, collector_id = EXCLUDED.collector_id,
                discovery_scope = EXCLUDED.discovery_scope, active = EXCLUDED.active,
                configured_by = EXCLUDED.configured_by, updated_at = EXCLUDED.updated_at,
                disabled_at = EXCLUDED.disabled_at, payload = EXCLUDED.payload
            """,
            {
                "id": route.id.value,
                "tenant_id": route.tenant_id.value,
                "region_code": route.region_code,
                "site_code": route.site_code,
                "vrf_code": route.vrf_code,
                "collector_id": route.collector_id.value,
                "discovery_scope": route.discovery_scope,
                "active": route.active,
                "configured_by": route.configured_by,
                "created_at": route.created_at,
                "updated_at": route.updated_at,
                "disabled_at": route.disabled_at,
                "payload": json.dumps(route.as_dict(), sort_keys=True),
            },
        )

    def get_regional_route(
        self, tenant_id: TenantId, route_id: str
    ) -> RegionalDiscoveryRoute | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_regional_discovery_routes
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(route_id).value},
        )
        return None if row is None else self._regional_route(self._json_mapping(row["payload"]))

    def find_regional_route(
        self, tenant_id: TenantId, region_code: str, site_code: str, vrf_code: str
    ) -> RegionalDiscoveryRoute | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_regional_discovery_routes
            WHERE tenant_id = %(tenant_id)s AND region_code = %(region_code)s
              AND site_code = %(site_code)s AND vrf_code = %(vrf_code)s LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "region_code": Code.from_value(region_code, "region code").value,
                "site_code": Code.from_value(site_code, "site code").value,
                "vrf_code": Code.from_value(vrf_code, "VRF code").value,
            },
        )
        return None if row is None else self._regional_route(self._json_mapping(row["payload"]))

    def list_regional_routes(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        region_code: str | None = None,
        site_code: str | None = None,
        active_only: bool = True,
    ) -> RegionalDiscoveryRoutePage:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if region_code:
            clauses.append("region_code = %(region_code)s")
            params["region_code"] = Code.from_value(region_code, "region code").value
        if site_code:
            clauses.append("site_code = %(site_code)s")
            params["site_code"] = Code.from_value(site_code, "site code").value
        if active_only:
            clauses.append("active = TRUE")
        predicate = "" if not clauses else "AND " + " AND ".join(clauses)
        rows, cursor = self._page(
            "multisite_regional_discovery_routes",
            tenant_id,
            pagination,
            predicate,
            params,
            "region_code, site_code, vrf_code, id",
        )
        return RegionalDiscoveryRoutePage(tuple(self._regional_route(row) for row in rows), cursor)

    def save_dr_plan(self, plan: MultisiteDisasterRecoveryPlan) -> None:
        self._ensure_tenant(plan.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO multisite_dr_plans (
                id, tenant_id, name, primary_site_code, recovery_site_code,
                replication_mode, rpo_seconds, rto_seconds, max_backup_age_seconds,
                active, configured_by, created_at, updated_at, disabled_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(name)s, %(primary_site_code)s,
                %(recovery_site_code)s, %(replication_mode)s, %(rpo_seconds)s,
                %(rto_seconds)s, %(max_backup_age_seconds)s, %(active)s,
                %(configured_by)s, %(created_at)s, %(updated_at)s, %(disabled_at)s,
                %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, primary_site_code, recovery_site_code) DO UPDATE SET
                name = EXCLUDED.name,
                replication_mode = EXCLUDED.replication_mode,
                rpo_seconds = EXCLUDED.rpo_seconds, rto_seconds = EXCLUDED.rto_seconds,
                max_backup_age_seconds = EXCLUDED.max_backup_age_seconds,
                active = EXCLUDED.active, configured_by = EXCLUDED.configured_by,
                updated_at = EXCLUDED.updated_at, disabled_at = EXCLUDED.disabled_at,
                payload = EXCLUDED.payload
            """,
            {
                "id": plan.id.value,
                "tenant_id": plan.tenant_id.value,
                "name": plan.name,
                "primary_site_code": plan.primary_site_code,
                "recovery_site_code": plan.recovery_site_code,
                "replication_mode": plan.replication_mode.value,
                "rpo_seconds": plan.rpo_seconds,
                "rto_seconds": plan.rto_seconds,
                "max_backup_age_seconds": plan.max_backup_age_seconds,
                "active": plan.active,
                "configured_by": plan.configured_by,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
                "disabled_at": plan.disabled_at,
                "payload": json.dumps(plan.as_dict(), sort_keys=True),
            },
        )

    def get_dr_plan(
        self, tenant_id: TenantId, plan_id: str
    ) -> MultisiteDisasterRecoveryPlan | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_dr_plans
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(plan_id).value},
        )
        return None if row is None else self._dr_plan(self._json_mapping(row["payload"]))

    def find_dr_plan_by_sites(
        self, tenant_id: TenantId, primary_site_code: str, recovery_site_code: str
    ) -> MultisiteDisasterRecoveryPlan | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_dr_plans
            WHERE tenant_id = %(tenant_id)s
              AND primary_site_code = %(primary_site_code)s
              AND recovery_site_code = %(recovery_site_code)s
            LIMIT 1
            """,
            {
                "tenant_id": tenant_id.value,
                "primary_site_code": Code.from_value(primary_site_code, "primary site code").value,
                "recovery_site_code": Code.from_value(
                    recovery_site_code, "recovery site code"
                ).value,
            },
        )
        return None if row is None else self._dr_plan(self._json_mapping(row["payload"]))

    def list_dr_plans(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        active_only: bool = True,
    ) -> DisasterRecoveryPlanPage:
        predicate = "AND active = TRUE" if active_only else ""
        rows, cursor = self._page(
            "multisite_dr_plans",
            tenant_id,
            pagination,
            predicate,
            {},
            "primary_site_code, recovery_site_code, id",
        )
        return DisasterRecoveryPlanPage(tuple(self._dr_plan(row) for row in rows), cursor)

    def save_dr_drill(self, drill: MultisiteDisasterRecoveryDrill) -> None:
        self._ensure_tenant(drill.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO multisite_dr_drills (
                id, tenant_id, plan_id, scenario, unavailable_site_code,
                recovery_site_code, status, replication_lag_seconds,
                backup_age_seconds, measured_rto_seconds, restore_verified,
                recovery_available, vip_reachable, operator_confirmed,
                executed_by, executed_at, payload
            ) VALUES (
                %(id)s, %(tenant_id)s, %(plan_id)s, %(scenario)s,
                %(unavailable_site_code)s, %(recovery_site_code)s, %(status)s,
                %(replication_lag_seconds)s, %(backup_age_seconds)s,
                %(measured_rto_seconds)s, %(restore_verified)s,
                %(recovery_available)s, %(vip_reachable)s,
                %(operator_confirmed)s, %(executed_by)s, %(executed_at)s,
                %(payload)s::jsonb
            ) ON CONFLICT (tenant_id, id) DO NOTHING
            """,
            {
                "id": drill.id.value,
                "tenant_id": drill.tenant_id.value,
                "plan_id": drill.plan_id.value,
                "scenario": drill.scenario,
                "unavailable_site_code": drill.unavailable_site_code,
                "recovery_site_code": drill.recovery_site_code,
                "status": drill.status.value,
                "replication_lag_seconds": drill.replication_lag_seconds,
                "backup_age_seconds": drill.backup_age_seconds,
                "measured_rto_seconds": drill.measured_rto_seconds,
                "restore_verified": drill.restore_verified,
                "recovery_available": drill.recovery_available,
                "vip_reachable": drill.vip_reachable,
                "operator_confirmed": drill.operator_confirmed,
                "executed_by": drill.executed_by,
                "executed_at": drill.executed_at,
                "payload": json.dumps(drill.as_dict(), sort_keys=True),
            },
        )

    def get_dr_drill(
        self, tenant_id: TenantId, drill_id: str
    ) -> MultisiteDisasterRecoveryDrill | None:
        row = self._fetch_one(
            """
            SELECT payload FROM multisite_dr_drills
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s LIMIT 1
            """,
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(drill_id).value},
        )
        return None if row is None else self._dr_drill(self._json_mapping(row["payload"]))

    def list_dr_drills(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        plan_id: str | None = None,
        status: str | None = None,
    ) -> DisasterRecoveryDrillPage:
        clauses: list[str] = []
        params: dict[str, object] = {}
        if plan_id:
            clauses.append("plan_id = %(plan_id)s")
            params["plan_id"] = EntityId.from_value(plan_id).value
        if status:
            try:
                normalized_status = DisasterRecoveryDrillStatus(status).value
            except ValueError as exc:
                raise ValidationError("DR drill status must be passed or failed") from exc
            clauses.append("status = %(status)s")
            params["status"] = normalized_status
        predicate = "" if not clauses else "AND " + " AND ".join(clauses)
        rows, cursor = self._page(
            "multisite_dr_drills",
            tenant_id,
            pagination,
            predicate,
            params,
            "executed_at DESC, id DESC",
        )
        return DisasterRecoveryDrillPage(tuple(self._dr_drill(row) for row in rows), cursor)

    def _page(
        self,
        table: str,
        tenant_id: TenantId,
        pagination: Pagination,
        predicate: str,
        params: dict[str, object],
        ordering: str,
    ) -> tuple[list[dict[str, Any]], str | None]:
        field_catalog: dict[tuple[str, str], tuple[CursorField, ...]] = {
            ("multisite_site_access_grants", "subject, site_code, id"): (
                CursorField("subject"),
                CursorField("site_code"),
                CursorField("id"),
            ),
            ("multisite_reports", "generated_at DESC, id DESC"): (
                CursorField("generated_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
            ("multisite_regional_discovery_routes", "region_code, site_code, vrf_code, id"): (
                CursorField("region_code"),
                CursorField("site_code"),
                CursorField("vrf_code"),
                CursorField("id"),
            ),
            ("multisite_dr_plans", "primary_site_code, recovery_site_code, id"): (
                CursorField("primary_site_code"),
                CursorField("recovery_site_code"),
                CursorField("id"),
            ),
            ("multisite_dr_drills", "executed_at DESC, id DESC"): (
                CursorField("executed_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        }
        fields = field_catalog.get((table, ordering))
        if fields is None:
            raise ValueError("unsupported multisite pagination query")
        page = self._keyset_page(
            pagination,
            scope="multisite." + table.removeprefix("multisite_"),
            tenant_id=tenant_id,
            filters=params,
            fields=fields,
        )
        field_names = ", ".join(field.name for field in fields)
        query = f"""
            SELECT payload, {field_names} FROM {table}
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY {ordering}
            LIMIT %(fetch_limit)s{page.offset_sql}
        """  # nosec B608 -- table, ordering and fields come from a closed internal catalog
        rows = self._fetch_all(
            query,
            {"tenant_id": tenant_id.value, **params, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return [self._json_mapping(row["payload"]) for row in selected], page.next_cursor(rows)

    @staticmethod
    def _grant(value: dict[str, Any]) -> SiteAccessGrant:
        revoked_at = value.get("revoked_at")
        return SiteAccessGrant.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            subject=str(value["subject"]),
            site_code=str(value["site_code"]),
            access_level=str(value["access_level"]),
            active=bool(value["active"]),
            granted_by=str(value["granted_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
            revoked_at=None if revoked_at is None else datetime.fromisoformat(str(revoked_at)),
        )

    @staticmethod
    def _regional_route(value: dict[str, Any]) -> RegionalDiscoveryRoute:
        disabled_at = value.get("disabled_at")
        return RegionalDiscoveryRoute.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            region_code=str(value["region_code"]),
            site_code=str(value["site_code"]),
            vrf_code=str(value["vrf_code"]),
            collector_id=EntityId.from_value(str(value["collector_id"])),
            discovery_scope=str(value["discovery_scope"]),
            active=bool(value["active"]),
            configured_by=str(value["configured_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
            disabled_at=None if disabled_at is None else datetime.fromisoformat(str(disabled_at)),
        )

    @staticmethod
    def _dr_plan(value: dict[str, Any]) -> MultisiteDisasterRecoveryPlan:
        disabled_at = value.get("disabled_at")
        return MultisiteDisasterRecoveryPlan.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            name=str(value["name"]),
            primary_site_code=str(value["primary_site_code"]),
            recovery_site_code=str(value["recovery_site_code"]),
            replication_mode=str(value["replication_mode"]),
            rpo_seconds=int(value["rpo_seconds"]),
            rto_seconds=int(value["rto_seconds"]),
            max_backup_age_seconds=int(value["max_backup_age_seconds"]),
            active=bool(value["active"]),
            configured_by=str(value["configured_by"]),
            created_at=datetime.fromisoformat(str(value["created_at"])),
            updated_at=datetime.fromisoformat(str(value["updated_at"])),
            disabled_at=None if disabled_at is None else datetime.fromisoformat(str(disabled_at)),
        )

    @staticmethod
    def _dr_drill(value: dict[str, Any]) -> MultisiteDisasterRecoveryDrill:
        raw_reasons = value.get("failure_reasons", [])
        if not isinstance(raw_reasons, list):
            raise ValidationError("DR drill failure reasons payload must be a list")
        return MultisiteDisasterRecoveryDrill.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            plan_id=EntityId.from_value(str(value["plan_id"])),
            scenario=str(value["scenario"]),
            unavailable_site_code=str(value["unavailable_site_code"]),
            recovery_site_code=str(value["recovery_site_code"]),
            replication_lag_seconds=int(value["replication_lag_seconds"]),
            backup_age_seconds=int(value["backup_age_seconds"]),
            measured_rto_seconds=int(value["measured_rto_seconds"]),
            restore_verified=bool(value["restore_verified"]),
            recovery_available=bool(value["recovery_available"]),
            vip_reachable=bool(value["vip_reachable"]),
            operator_confirmed=bool(value["operator_confirmed"]),
            status=str(value["status"]),
            failure_reasons=tuple(str(item) for item in raw_reasons),
            executed_by=str(value["executed_by"]),
            executed_at=datetime.fromisoformat(str(value["executed_at"])),
        )

    @staticmethod
    def _report(value: dict[str, Any]) -> MultisitePortfolioReport:
        raw_sites = value.get("sites")
        if not isinstance(raw_sites, list):
            raise ValidationError("multisite report sites payload must be a list")
        sites = tuple(
            SitePortfolioEntry(
                site_code=str(item["site_code"]),
                site_name=str(item["site_name"]),
                country=str(item["country"]),
                city=str(item["city"]),
                status=str(item["status"]),
                buildings=int(item["buildings"]),
                floors=int(item["floors"]),
                rooms=int(item["rooms"]),
                racks=int(item["racks"]),
                equipment=int(item["equipment"]),
            )
            for item in raw_sites
            if isinstance(item, Mapping)
        )
        return MultisitePortfolioReport.restore(
            id=EntityId.from_value(str(value["id"])),
            tenant_id=TenantId.from_value(str(value["tenant_id"])),
            requested_subject=str(value["requested_subject"]),
            generated_by=str(value["generated_by"]),
            generated_at=datetime.fromisoformat(str(value["generated_at"])),
            sites=sites,
        )

    @staticmethod
    def _json_mapping(value: object) -> dict[str, Any]:
        loaded = json.loads(value) if isinstance(value, str) else value
        if not isinstance(loaded, Mapping):
            raise ValidationError("multisite payload must be a JSON object")
        return {str(key): item for key, item in loaded.items()}


class PostgreSQLCertificateInventoryRepository(
    PostgreSQLRepositoryBase, CertificateInventoryRepository
):
    _CERTIFICATE_COLUMNS = """
        id, tenant_id, fingerprint_sha256, serial_number, subject_dn, issuer_dn,
        common_name, san_dns, san_ip, san_email, san_uri, not_before, not_after,
        public_key_algorithm, public_key_size, signature_algorithm, is_ca,
        chain_fingerprints, owner, environment, source, object_key, lifecycle,
        version, created_by, created_at, updated_by, updated_at
    """
    _ENDPOINT_COLUMNS = """
        id, tenant_id, idempotency_key, protocol, host, port, service,
        certificate_fingerprint, observed_at, source, collector, object_key,
        tls_version, cipher, received_at, payload_fingerprint
    """

    def save_certificate(self, certificate: CertificateAsset) -> None:
        self._ensure_tenant(certificate.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO certificate_inventory (
                id, tenant_id, fingerprint_sha256, serial_number, subject_dn, issuer_dn,
                common_name, san_dns, san_ip, san_email, san_uri, not_before, not_after,
                public_key_algorithm, public_key_size, signature_algorithm, is_ca,
                chain_fingerprints, owner, environment, source, object_key, lifecycle,
                version, created_by, created_at, updated_by, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(fingerprint_sha256)s, %(serial_number)s,
                %(subject_dn)s, %(issuer_dn)s, %(common_name)s, %(san_dns)s,
                %(san_ip)s, %(san_email)s, %(san_uri)s, %(not_before)s, %(not_after)s,
                %(public_key_algorithm)s, %(public_key_size)s, %(signature_algorithm)s,
                %(is_ca)s, %(chain_fingerprints)s, %(owner)s, %(environment)s,
                %(source)s, %(object_key)s, %(lifecycle)s, %(version)s, %(created_by)s,
                %(created_at)s, %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                chain_fingerprints = EXCLUDED.chain_fingerprints,
                owner = EXCLUDED.owner,
                environment = EXCLUDED.environment,
                source = EXCLUDED.source,
                object_key = EXCLUDED.object_key,
                lifecycle = EXCLUDED.lifecycle,
                version = EXCLUDED.version,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            self._certificate_params(certificate),
        )

    def get_certificate_by_fingerprint(
        self, tenant_id: TenantId, fingerprint: str
    ) -> CertificateAsset | None:
        row = self._fetch_one(
            f"""
            SELECT {self._CERTIFICATE_COLUMNS}
            FROM certificate_inventory
            WHERE tenant_id = %(tenant_id)s AND fingerprint_sha256 = %(fingerprint)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {
                "tenant_id": tenant_id.value,
                "fingerprint": fingerprint.strip().lower().replace(":", ""),
            },
        )
        return self._certificate_from_row(row) if row else None

    def get_certificate(self, tenant_id: TenantId, certificate_id: str) -> CertificateAsset | None:
        row = self._fetch_one(
            f"""
            SELECT {self._CERTIFICATE_COLUMNS}
            FROM certificate_inventory
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(certificate_id).value},
        )
        return self._certificate_from_row(row) if row else None

    def list_certificates(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_retired: bool = False,
    ) -> CertificateAssetPage:
        page = self._keyset_page(
            pagination,
            scope="security.certificate-inventory",
            tenant_id=tenant_id,
            filters={"include_retired": include_retired},
            fields=(
                CursorField("not_after", value_type=CursorValueType.DATETIME),
                CursorField("subject_dn"),
                CursorField("fingerprint_sha256"),
            ),
        )
        lifecycle_filter = "" if include_retired else "AND lifecycle <> 'retired'"
        rows = self._fetch_all(
            f"""
            SELECT {self._CERTIFICATE_COLUMNS}
            FROM certificate_inventory
            WHERE tenant_id = %(tenant_id)s {lifecycle_filter} {page.where_sql}
            ORDER BY not_after ASC, subject_dn ASC, fingerprint_sha256 ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- columns, lifecycle predicate and keyset fields are fixed
            {"tenant_id": tenant_id.value, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return CertificateAssetPage(
            tuple(self._certificate_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    def save_endpoint_observation(self, observation: CertificateEndpointObservation) -> None:
        self._ensure_tenant(observation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO certificate_endpoint_observations (
                id, tenant_id, idempotency_key, protocol, host, port, service,
                certificate_fingerprint, observed_at, source, collector, object_key,
                tls_version, cipher, received_at, payload_fingerprint
            ) VALUES (
                %(id)s, %(tenant_id)s, %(idempotency_key)s, %(protocol)s, %(host)s,
                %(port)s, %(service)s, %(certificate_fingerprint)s, %(observed_at)s,
                %(source)s, %(collector)s, %(object_key)s, %(tls_version)s, %(cipher)s,
                %(received_at)s, %(payload_fingerprint)s
            )
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            """,
            self._endpoint_params(observation),
        )

    def find_endpoint_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> CertificateEndpointObservation | None:
        row = self._fetch_one(
            f"""
            SELECT {self._ENDPOINT_COLUMNS}
            FROM certificate_endpoint_observations
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return self._endpoint_from_row(row) if row else None

    def list_endpoint_observations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        certificate_fingerprint: str | None = None,
    ) -> CertificateEndpointPage:
        normalized_fingerprint = (
            certificate_fingerprint.strip().lower().replace(":", "")
            if certificate_fingerprint is not None
            else None
        )
        page = self._keyset_page(
            pagination,
            scope="security.certificate-endpoints",
            tenant_id=tenant_id,
            filters={"certificate_fingerprint": normalized_fingerprint},
            fields=(
                CursorField("observed_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        fingerprint_filter = (
            ""
            if normalized_fingerprint is None
            else "AND certificate_fingerprint = %(fingerprint)s"
        )
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_fingerprint is not None:
            params["fingerprint"] = normalized_fingerprint
        rows = self._fetch_all(
            f"""
            SELECT {self._ENDPOINT_COLUMNS}
            FROM certificate_endpoint_observations
            WHERE tenant_id = %(tenant_id)s {fingerprint_filter} {page.where_sql}
            ORDER BY observed_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- columns, predicate and keyset fields are fixed
            params,
        )
        selected = rows[: pagination.limit]
        return CertificateEndpointPage(
            tuple(self._endpoint_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    @staticmethod
    def _certificate_params(certificate: CertificateAsset) -> dict[str, object]:
        material = certificate.material
        return {
            "id": certificate.id.value,
            "tenant_id": certificate.tenant_id.value,
            "fingerprint_sha256": material.fingerprint_sha256,
            "serial_number": material.serial_number,
            "subject_dn": material.subject_dn,
            "issuer_dn": material.issuer_dn,
            "common_name": material.common_name,
            "san_dns": json.dumps(material.san_dns),
            "san_ip": json.dumps(material.san_ip),
            "san_email": json.dumps(material.san_email),
            "san_uri": json.dumps(material.san_uri),
            "not_before": material.not_before,
            "not_after": material.not_after,
            "public_key_algorithm": material.public_key_algorithm,
            "public_key_size": material.public_key_size,
            "signature_algorithm": material.signature_algorithm,
            "is_ca": material.is_ca,
            "chain_fingerprints": json.dumps(certificate.chain_fingerprints),
            "owner": certificate.owner,
            "environment": certificate.environment,
            "source": certificate.source.value,
            "object_key": None if certificate.object_key is None else certificate.object_key.value,
            "lifecycle": certificate.lifecycle.value,
            "version": certificate.version,
            "created_by": certificate.created_by,
            "created_at": certificate.created_at,
            "updated_by": certificate.updated_by,
            "updated_at": certificate.updated_at,
        }

    @staticmethod
    def _endpoint_params(observation: CertificateEndpointObservation) -> dict[str, object]:
        return {
            "id": observation.id.value,
            "tenant_id": observation.tenant_id.value,
            "idempotency_key": observation.idempotency_key,
            "protocol": observation.protocol,
            "host": observation.host,
            "port": observation.port,
            "service": observation.service,
            "certificate_fingerprint": observation.certificate_fingerprint,
            "observed_at": observation.observed_at,
            "source": observation.source.value,
            "collector": observation.collector,
            "object_key": None if observation.object_key is None else observation.object_key.value,
            "tls_version": observation.tls_version,
            "cipher": observation.cipher,
            "received_at": observation.received_at,
            "payload_fingerprint": observation.payload_fingerprint,
        }

    def _certificate_from_row(self, row: Mapping[str, object]) -> CertificateAsset:
        material = CertificateMaterial.create(
            fingerprint_sha256=str(row["fingerprint_sha256"]),
            serial_number=str(row["serial_number"]),
            subject_dn=str(row["subject_dn"]),
            issuer_dn=str(row["issuer_dn"]),
            common_name=(None if row.get("common_name") is None else str(row["common_name"])),
            san_dns=tuple(str(item) for item in self._json_sequence(row["san_dns"])),
            san_ip=tuple(str(item) for item in self._json_sequence(row["san_ip"])),
            san_email=tuple(str(item) for item in self._json_sequence(row["san_email"])),
            san_uri=tuple(str(item) for item in self._json_sequence(row["san_uri"])),
            not_before=self._row_datetime(row["not_before"]),
            not_after=self._row_datetime(row["not_after"]),
            public_key_algorithm=str(row["public_key_algorithm"]),
            public_key_size=(
                None if row.get("public_key_size") is None else int(str(row["public_key_size"]))
            ),
            signature_algorithm=str(row["signature_algorithm"]),
            is_ca=bool(row["is_ca"]),
        )
        return CertificateAsset.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            material=material,
            chain_fingerprints=tuple(
                str(item) for item in self._json_sequence(row["chain_fingerprints"])
            ),
            owner=str(row["owner"]),
            environment=str(row["environment"]),
            source=str(row["source"]),
            object_key=(None if row.get("object_key") is None else str(row["object_key"])),
            lifecycle=str(row["lifecycle"]),
            version=int(str(row["version"])),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _endpoint_from_row(self, row: Mapping[str, object]) -> CertificateEndpointObservation:
        return CertificateEndpointObservation.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            idempotency_key=str(row["idempotency_key"]),
            protocol=str(row["protocol"]),
            host=str(row["host"]),
            port=int(str(row["port"])),
            service=str(row["service"]),
            certificate_fingerprint=str(row["certificate_fingerprint"]),
            observed_at=self._row_datetime(row["observed_at"]),
            source=str(row["source"]),
            collector=str(row["collector"]),
            object_key=(None if row.get("object_key") is None else str(row["object_key"])),
            tls_version=(None if row.get("tls_version") is None else str(row["tls_version"])),
            cipher=(None if row.get("cipher") is None else str(row["cipher"])),
            received_at=self._row_datetime(row["received_at"]),
            payload_fingerprint=str(row["payload_fingerprint"]),
        )

    @staticmethod
    def _json_sequence(value: object) -> Sequence[object]:
        if isinstance(value, str):
            return cast(Sequence[object], json.loads(value))
        return cast(Sequence[object], value)

    @staticmethod
    def _row_datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLFlowMatrixRepository(PostgreSQLRepositoryBase, FlowMatrixRepository):
    _DECLARATION_COLUMNS = """
        id, tenant_id, code, source_selector, destination_selector, protocol,
        destination_port_start, destination_port_end, decision, priority, owner,
        justification, valid_from, valid_to, status, version, created_by, created_at,
        updated_by, updated_at
    """
    _OBSERVATION_COLUMNS = """
        id, tenant_id, idempotency_key, source, collector, source_ip, destination_ip,
        source_object_key, destination_object_key, protocol, destination_port,
        packets, bytes_count, first_seen, last_seen, received_at, fingerprint
    """

    def save_declaration(self, declaration: FlowDeclaration) -> None:
        self._ensure_tenant(declaration.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO flow_declarations (
                id, tenant_id, code, source_selector, destination_selector, protocol,
                destination_port_start, destination_port_end, decision, priority, owner,
                justification, valid_from, valid_to, status, version, created_by, created_at,
                updated_by, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(source_selector)s,
                %(destination_selector)s, %(protocol)s, %(destination_port_start)s,
                %(destination_port_end)s, %(decision)s, %(priority)s, %(owner)s,
                %(justification)s, %(valid_from)s, %(valid_to)s, %(status)s, %(version)s,
                %(created_by)s, %(created_at)s, %(updated_by)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                source_selector = EXCLUDED.source_selector,
                destination_selector = EXCLUDED.destination_selector,
                protocol = EXCLUDED.protocol,
                destination_port_start = EXCLUDED.destination_port_start,
                destination_port_end = EXCLUDED.destination_port_end,
                decision = EXCLUDED.decision,
                priority = EXCLUDED.priority,
                owner = EXCLUDED.owner,
                justification = EXCLUDED.justification,
                valid_from = EXCLUDED.valid_from,
                valid_to = EXCLUDED.valid_to,
                status = EXCLUDED.status,
                version = EXCLUDED.version,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at
            """,
            self._declaration_params(declaration),
        )

    def find_declaration_by_code(self, tenant_id: TenantId, code: str) -> FlowDeclaration | None:
        row = self._fetch_one(
            f"""
            SELECT {self._DECLARATION_COLUMNS}
            FROM flow_declarations
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "code": code.strip().upper()},
        )
        return self._declaration_from_row(row) if row else None

    def get_declaration(self, tenant_id: TenantId, declaration_id: str) -> FlowDeclaration | None:
        row = self._fetch_one(
            f"""
            SELECT {self._DECLARATION_COLUMNS}
            FROM flow_declarations
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(declaration_id).value},
        )
        return self._declaration_from_row(row) if row else None

    def list_declarations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_retired: bool = False,
    ) -> FlowDeclarationPage:
        page = self._keyset_page(
            pagination,
            scope="ipam.flow-declarations",
            tenant_id=tenant_id,
            filters={"include_retired": include_retired},
            fields=(CursorField("code"), CursorField("id")),
        )
        status_filter = "" if include_retired else "AND status <> 'retired'"
        rows = self._fetch_all(
            f"""
            SELECT {self._DECLARATION_COLUMNS}
            FROM flow_declarations
            WHERE tenant_id = %(tenant_id)s {status_filter} {page.where_sql}
            ORDER BY code ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- columns, status predicate and keyset fields are fixed
            {"tenant_id": tenant_id.value, **page.parameters},
        )
        selected = rows[: pagination.limit]
        return FlowDeclarationPage(
            tuple(self._declaration_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    def save_observation(self, observation: FlowObservation) -> None:
        self._ensure_tenant(observation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO flow_observations (
                id, tenant_id, idempotency_key, source, collector, source_ip, destination_ip,
                source_object_key, destination_object_key, protocol, destination_port,
                packets, bytes_count, first_seen, last_seen, received_at, fingerprint
            ) VALUES (
                %(id)s, %(tenant_id)s, %(idempotency_key)s, %(source)s, %(collector)s,
                %(source_ip)s, %(destination_ip)s, %(source_object_key)s,
                %(destination_object_key)s, %(protocol)s, %(destination_port)s,
                %(packets)s, %(bytes_count)s, %(first_seen)s, %(last_seen)s,
                %(received_at)s, %(fingerprint)s
            )
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            """,
            self._observation_params(observation),
        )

    def find_observation_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> FlowObservation | None:
        row = self._fetch_one(
            f"""
            SELECT {self._OBSERVATION_COLUMNS}
            FROM flow_observations
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return self._observation_from_row(row) if row else None

    def list_observations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        window_start: datetime,
        window_end: datetime,
        source: str | None = None,
    ) -> FlowObservationPage:
        normalized_source = source.strip().lower().replace("_", "-") if source else None
        page = self._keyset_page(
            pagination,
            scope="ipam.flow-observations",
            tenant_id=tenant_id,
            filters={
                "window_start": window_start,
                "window_end": window_end,
                "source": normalized_source,
            },
            fields=(
                CursorField("last_seen", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        source_filter = "" if normalized_source is None else "AND source = %(source)s"
        params: dict[str, object] = {
            "tenant_id": tenant_id.value,
            "window_start": window_start,
            "window_end": window_end,
            **page.parameters,
        }
        if normalized_source is not None:
            params["source"] = normalized_source
        rows = self._fetch_all(
            f"""
            SELECT {self._OBSERVATION_COLUMNS}
            FROM flow_observations
            WHERE tenant_id = %(tenant_id)s
              AND last_seen >= %(window_start)s
              AND first_seen < %(window_end)s
              {source_filter}
              {page.where_sql}
            ORDER BY last_seen DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- columns, source predicate and keyset fields are fixed
            params,
        )
        selected = rows[: pagination.limit]
        return FlowObservationPage(
            tuple(self._observation_from_row(row) for row in selected),
            page.next_cursor(rows),
        )

    @staticmethod
    def _declaration_params(declaration: FlowDeclaration) -> dict[str, object]:
        return {
            "id": declaration.id.value,
            "tenant_id": declaration.tenant_id.value,
            "code": declaration.code,
            "source_selector": str(declaration.source_selector),
            "destination_selector": str(declaration.destination_selector),
            "protocol": declaration.protocol.value,
            "destination_port_start": (
                None
                if declaration.destination_ports is None
                else declaration.destination_ports.start
            ),
            "destination_port_end": (
                None if declaration.destination_ports is None else declaration.destination_ports.end
            ),
            "decision": declaration.decision.value,
            "priority": declaration.priority,
            "owner": declaration.owner,
            "justification": declaration.justification,
            "valid_from": declaration.valid_from,
            "valid_to": declaration.valid_to,
            "status": declaration.status.value,
            "version": declaration.version,
            "created_by": declaration.created_by,
            "created_at": declaration.created_at,
            "updated_by": declaration.updated_by,
            "updated_at": declaration.updated_at,
        }

    @staticmethod
    def _observation_params(observation: FlowObservation) -> dict[str, object]:
        return {
            "id": observation.id.value,
            "tenant_id": observation.tenant_id.value,
            "idempotency_key": observation.idempotency_key,
            "source": observation.source.value,
            "collector": observation.collector,
            "source_ip": observation.source_ip,
            "destination_ip": observation.destination_ip,
            "source_object_key": observation.source_object_key,
            "destination_object_key": observation.destination_object_key,
            "protocol": observation.protocol.value,
            "destination_port": observation.destination_port,
            "packets": observation.packets,
            "bytes_count": observation.bytes_count,
            "first_seen": observation.first_seen,
            "last_seen": observation.last_seen,
            "received_at": observation.received_at,
            "fingerprint": observation.fingerprint,
        }

    def _declaration_from_row(self, row: Mapping[str, object]) -> FlowDeclaration:
        return FlowDeclaration.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            code=str(row["code"]),
            source_selector=str(row["source_selector"]),
            destination_selector=str(row["destination_selector"]),
            protocol=str(row["protocol"]),
            destination_port_start=(
                None
                if row.get("destination_port_start") is None
                else int(str(row["destination_port_start"]))
            ),
            destination_port_end=(
                None
                if row.get("destination_port_end") is None
                else int(str(row["destination_port_end"]))
            ),
            decision=str(row["decision"]),
            priority=int(str(row["priority"])),
            owner=str(row["owner"]),
            justification=str(row["justification"]),
            valid_from=self._row_datetime(row["valid_from"]),
            valid_to=(None if row.get("valid_to") is None else self._row_datetime(row["valid_to"])),
            status=str(row["status"]),
            version=int(str(row["version"])),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _observation_from_row(self, row: Mapping[str, object]) -> FlowObservation:
        return FlowObservation.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            idempotency_key=str(row["idempotency_key"]),
            source=str(row["source"]),
            collector=str(row["collector"]),
            source_ip=str(row["source_ip"]),
            destination_ip=str(row["destination_ip"]),
            source_object_key=(
                None if row.get("source_object_key") is None else str(row["source_object_key"])
            ),
            destination_object_key=(
                None
                if row.get("destination_object_key") is None
                else str(row["destination_object_key"])
            ),
            protocol=str(row["protocol"]),
            destination_port=(
                None if row.get("destination_port") is None else int(str(row["destination_port"]))
            ),
            packets=int(str(row["packets"])),
            bytes_count=int(str(row["bytes_count"])),
            first_seen=self._row_datetime(row["first_seen"]),
            last_seen=self._row_datetime(row["last_seen"]),
            received_at=self._row_datetime(row["received_at"]),
            fingerprint=str(row["fingerprint"]),
        )

    @staticmethod
    def _row_datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLNetworkConfigComplianceRepository(
    PostgreSQLRepositoryBase, NetworkConfigComplianceRepository
):
    _BASELINE_COLUMNS = """
        id, tenant_id, code, device_object_key, platform, expected_config,
        ignored_paths, critical_paths, owner, justification, status, version,
        created_by, created_at, updated_by, updated_at, fingerprint
    """
    _OBSERVATION_COLUMNS = """
        id, tenant_id, idempotency_key, source, collector, device_object_key,
        platform, observed_config, observed_at, received_at, fingerprint
    """

    def save_baseline(self, baseline: NetworkConfigBaseline) -> None:
        self._ensure_tenant(baseline.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO network_config_baselines (
                id, tenant_id, code, device_object_key, platform, expected_config,
                ignored_paths, critical_paths, owner, justification, status, version,
                created_by, created_at, updated_by, updated_at, fingerprint
            ) VALUES (
                %(id)s, %(tenant_id)s, %(code)s, %(device_object_key)s, %(platform)s,
                %(expected_config)s, %(ignored_paths)s, %(critical_paths)s, %(owner)s,
                %(justification)s, %(status)s, %(version)s, %(created_by)s, %(created_at)s,
                %(updated_by)s, %(updated_at)s, %(fingerprint)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                platform = EXCLUDED.platform,
                expected_config = EXCLUDED.expected_config,
                ignored_paths = EXCLUDED.ignored_paths,
                critical_paths = EXCLUDED.critical_paths,
                owner = EXCLUDED.owner,
                justification = EXCLUDED.justification,
                status = EXCLUDED.status,
                version = EXCLUDED.version,
                updated_by = EXCLUDED.updated_by,
                updated_at = EXCLUDED.updated_at,
                fingerprint = EXCLUDED.fingerprint
            """,
            self._baseline_params(baseline),
        )

    def find_baseline_by_code(self, tenant_id: TenantId, code: str) -> NetworkConfigBaseline | None:
        row = self._fetch_one(
            f"""
            SELECT {self._BASELINE_COLUMNS}
            FROM network_config_baselines
            WHERE tenant_id = %(tenant_id)s AND code = %(code)s
            """,  # nosec B608 -- selected columns are fixed
            {"tenant_id": tenant_id.value, "code": code.strip().upper()},
        )
        return self._baseline_from_row(row) if row else None

    def get_baseline(self, tenant_id: TenantId, baseline_id: str) -> NetworkConfigBaseline | None:
        row = self._fetch_one(
            f"""
            SELECT {self._BASELINE_COLUMNS}
            FROM network_config_baselines
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,  # nosec B608 -- selected columns are fixed
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(baseline_id).value},
        )
        return self._baseline_from_row(row) if row else None

    def list_baselines(
        self, tenant_id: TenantId, pagination: Pagination, include_retired: bool = False
    ) -> NetworkConfigBaselinePage:
        page = self._keyset_page(
            pagination,
            scope="ipam.network-config-baselines",
            tenant_id=tenant_id,
            filters={"include_retired": include_retired},
            fields=(CursorField("code"), CursorField("id")),
        )
        status_filter = "" if include_retired else "AND status <> 'retired'"
        rows = self._fetch_all(
            f"""
            SELECT {self._BASELINE_COLUMNS}
            FROM network_config_baselines
            WHERE tenant_id = %(tenant_id)s {status_filter} {page.where_sql}
            ORDER BY code ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- columns, status predicate and keyset fields are fixed
            {"tenant_id": tenant_id.value, **page.parameters},
        )
        return NetworkConfigBaselinePage(
            tuple(self._baseline_from_row(row) for row in rows[: pagination.limit]),
            page.next_cursor(rows),
        )

    def save_observation(self, observation: NetworkConfigObservation) -> None:
        self._ensure_tenant(observation.tenant_id)
        self._execute_without_result(
            """
            INSERT INTO network_config_observations (
                id, tenant_id, idempotency_key, source, collector, device_object_key,
                platform, observed_config, observed_at, received_at, fingerprint
            ) VALUES (
                %(id)s, %(tenant_id)s, %(idempotency_key)s, %(source)s, %(collector)s,
                %(device_object_key)s, %(platform)s, %(observed_config)s, %(observed_at)s,
                %(received_at)s, %(fingerprint)s
            )
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            """,
            self._observation_params(observation),
        )

    def find_observation_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> NetworkConfigObservation | None:
        row = self._fetch_one(
            f"""
            SELECT {self._OBSERVATION_COLUMNS}
            FROM network_config_observations
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,  # nosec B608 -- selected columns are fixed
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return self._observation_from_row(row) if row else None

    def list_observations(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        device_object_key: str | None = None,
        platform: str | None = None,
        observed_before: datetime | None = None,
    ) -> NetworkConfigObservationPage:
        normalized_device = device_object_key.strip() if device_object_key is not None else None
        normalized_platform = platform.strip().lower() if platform is not None else None
        page = self._keyset_page(
            pagination,
            scope="ipam.network-config-observations",
            tenant_id=tenant_id,
            filters={
                "device_object_key": normalized_device,
                "platform": normalized_platform,
                "observed_before": observed_before,
            },
            fields=(
                CursorField("observed_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("received_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        filters = []
        params: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if normalized_device is not None:
            filters.append("AND device_object_key = %(device_object_key)s")
            params["device_object_key"] = normalized_device
        if normalized_platform is not None:
            filters.append("AND platform = %(platform)s")
            params["platform"] = normalized_platform
        if observed_before is not None:
            filters.append("AND observed_at <= %(observed_before)s")
            params["observed_before"] = observed_before
        rows = self._fetch_all(
            f"""
            SELECT {self._OBSERVATION_COLUMNS}
            FROM network_config_observations
            WHERE tenant_id = %(tenant_id)s {" ".join(filters)} {page.where_sql}
            ORDER BY observed_at DESC, received_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- filters and keyset fields are fixed internal constants
            params,
        )
        return NetworkConfigObservationPage(
            tuple(self._observation_from_row(row) for row in rows[: pagination.limit]),
            page.next_cursor(rows),
        )

    @staticmethod
    def _baseline_params(baseline: NetworkConfigBaseline) -> dict[str, object]:
        return {
            "id": baseline.id.value,
            "tenant_id": baseline.tenant_id.value,
            "code": baseline.code,
            "device_object_key": baseline.device_object_key,
            "platform": baseline.platform,
            "expected_config": json.dumps(baseline.expected_config, sort_keys=True),
            "ignored_paths": json.dumps(baseline.ignored_paths),
            "critical_paths": json.dumps(baseline.critical_paths),
            "owner": baseline.owner,
            "justification": baseline.justification,
            "status": baseline.status.value,
            "version": baseline.version,
            "created_by": baseline.created_by,
            "created_at": baseline.created_at,
            "updated_by": baseline.updated_by,
            "updated_at": baseline.updated_at,
            "fingerprint": baseline.fingerprint,
        }

    @staticmethod
    def _observation_params(observation: NetworkConfigObservation) -> dict[str, object]:
        return {
            "id": observation.id.value,
            "tenant_id": observation.tenant_id.value,
            "idempotency_key": observation.idempotency_key,
            "source": observation.source.value,
            "collector": observation.collector,
            "device_object_key": observation.device_object_key,
            "platform": observation.platform,
            "observed_config": json.dumps(observation.observed_config, sort_keys=True),
            "observed_at": observation.observed_at,
            "received_at": observation.received_at,
            "fingerprint": observation.fingerprint,
        }

    def _baseline_from_row(self, row: Mapping[str, object]) -> NetworkConfigBaseline:
        return NetworkConfigBaseline.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            code=str(row["code"]),
            device_object_key=str(row["device_object_key"]),
            platform=str(row["platform"]),
            expected_config=self._json_mapping(row["expected_config"]),
            ignored_paths=tuple(str(item) for item in self._json_sequence(row["ignored_paths"])),
            critical_paths=tuple(str(item) for item in self._json_sequence(row["critical_paths"])),
            owner=str(row["owner"]),
            justification=str(row["justification"]),
            status=str(row["status"]),
            version=int(str(row["version"])),
            created_by=str(row["created_by"]),
            created_at=self._row_datetime(row["created_at"]),
            updated_by=str(row["updated_by"]),
            updated_at=self._row_datetime(row["updated_at"]),
        )

    def _observation_from_row(self, row: Mapping[str, object]) -> NetworkConfigObservation:
        return NetworkConfigObservation.restore(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            idempotency_key=str(row["idempotency_key"]),
            source=str(row["source"]),
            collector=str(row["collector"]),
            device_object_key=str(row["device_object_key"]),
            platform=str(row["platform"]),
            observed_config=self._json_mapping(row["observed_config"]),
            observed_at=self._row_datetime(row["observed_at"]),
            received_at=self._row_datetime(row["received_at"]),
            fingerprint=str(row["fingerprint"]),
        )

    @staticmethod
    def _json_mapping(value: object) -> Mapping[str, object]:
        return cast(Mapping[str, object], json.loads(value) if isinstance(value, str) else value)

    @staticmethod
    def _json_sequence(value: object) -> Sequence[object]:
        return cast(Sequence[object], json.loads(value) if isinstance(value, str) else value)

    @staticmethod
    def _row_datetime(value: object) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class PostgreSQLAuditRepository(PostgreSQLRepositoryBase, AuditRepository):
    def append(self, event: AuditEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        previous_hash = self._latest_hash(event.tenant_id)
        record = AuditEventRecord.create(event, previous_hash)
        self._execute_without_result(
            """
            INSERT INTO audit_events (
                id, tenant_id, actor, action, target_type, target_id, severity, metadata,
                created_at, previous_hash, record_hash
            ) VALUES (
                %(id)s, %(tenant_id)s, %(actor)s, %(action)s, %(target_type)s, %(target_id)s,
                %(severity)s, %(metadata)s, %(created_at)s, %(previous_hash)s, %(record_hash)s
            )
            """,
            {
                "id": event.id.value,
                "tenant_id": event.tenant_id.value,
                "actor": event.actor,
                "action": event.action,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "severity": event.severity.value,
                "metadata": json.dumps(event.metadata, sort_keys=True),
                "created_at": event.created_at,
                "previous_hash": record.previous_hash,
                "record_hash": record.record_hash,
            },
        )

    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        filter_values = {
            "actor": event_filter.actor,
            "action": event_filter.action,
            "target_type": event_filter.target_type,
            "target_id": event_filter.target_id,
            "severity": event_filter.severity.value if event_filter.severity is not None else None,
            "created_from": event_filter.created_from,
            "created_to": event_filter.created_to,
        }
        page = self._keyset_page(
            event_filter.pagination,
            scope="security.audit-events",
            tenant_id=event_filter.tenant_id,
            filters=filter_values,
            fields=(
                CursorField("created_at", CursorDirection.DESC, CursorValueType.DATETIME),
                CursorField("id", CursorDirection.DESC),
            ),
        )
        rows = self._fetch_all(
            f"""
            SELECT id, tenant_id, actor, action, target_type, target_id, severity,
                   metadata, created_at, previous_hash, record_hash
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
              AND (%(actor)s IS NULL OR actor = %(actor)s)
              AND (%(action)s IS NULL OR action = %(action)s)
              AND (%(target_type)s IS NULL OR target_type = %(target_type)s)
              AND (%(target_id)s IS NULL OR target_id = %(target_id)s)
              AND (%(severity)s IS NULL OR severity = %(severity)s)
              AND (%(created_from)s IS NULL OR created_at >= %(created_from)s)
              AND (%(created_to)s IS NULL OR created_at <= %(created_to)s)
              {page.where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- keyset SQL is generated from validated cursor fields
            {
                "tenant_id": event_filter.tenant_id.value,
                **filter_values,
                **page.parameters,
            },
        )
        records = tuple(self._record_from_row(row) for row in rows[: event_filter.pagination.limit])
        return AuditEventPage(records, page.next_cursor(rows))

    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        if not 1 <= int(limit) <= 10_000:
            raise ValidationError("audit integrity limit must be between 1 and 10000")
        rows = self._fetch_all(
            """
            SELECT id, tenant_id, actor, action, target_type, target_id, severity,
                   metadata, created_at, previous_hash, record_hash
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at ASC, id ASC
            LIMIT %(limit)s
            """,
            {"tenant_id": tenant_id.value, "limit": int(limit)},
        )
        previous_hash = AuditIntegrityHasher.GENESIS_HASH
        checked = 0
        for row in rows:
            record = self._record_from_row(row)
            if record.previous_hash != previous_hash or not record.verifies():
                return AuditIntegrityReport(
                    tenant_id=tenant_id,
                    checked=checked + 1,
                    valid=False,
                    broken_record_id=record.event.id.value,
                    head_hash=previous_hash,
                )
            previous_hash = record.record_hash
            checked += 1
        return AuditIntegrityReport(
            tenant_id=tenant_id,
            checked=checked,
            valid=True,
            broken_record_id=None,
            head_hash=previous_hash,
        )

    def list_events(self, tenant_id: TenantId, limit: int = 100) -> tuple[AuditEvent, ...]:
        if not 1 <= limit <= 500:
            raise ValidationError("audit list limit must be between 1 and 500")
        event_filter = AuditEventFilter.create(
            tenant_id,
            Pagination.from_values(limit),
        )
        return tuple(record.event for record in self.list_records(event_filter).items)

    def _latest_hash(self, tenant_id: TenantId) -> str:
        row = self._fetch_one(
            """
            SELECT record_hash
            FROM audit_events
            WHERE tenant_id = %(tenant_id)s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            {"tenant_id": tenant_id.value},
        )
        if row is None or row.get("record_hash") is None:
            return AuditIntegrityHasher.GENESIS_HASH
        return AuditIntegrityHasher.normalize_hash(str(row["record_hash"]), "record_hash")

    def _record_from_row(self, row: Mapping[str, object]) -> AuditEventRecord:
        event = self._event_from_row(row)
        previous_hash = str(row.get("previous_hash") or AuditIntegrityHasher.GENESIS_HASH)
        record_hash = row.get("record_hash")
        if record_hash is None:
            return AuditEventRecord.create(event, previous_hash)
        return AuditEventRecord.restore(event, previous_hash, str(record_hash))

    def _event_from_row(self, row: Mapping[str, object]) -> AuditEvent:
        metadata = row["metadata"]
        created_at = row["created_at"]
        if not isinstance(created_at, datetime):
            raise ValidationError("audit event created_at must be a datetime")
        return AuditEvent(
            id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            actor=str(row["actor"]),
            action=str(row["action"]),
            target_type=str(row["target_type"]),
            target_id=str(row["target_id"]),
            severity=Severity(str(row["severity"])),
            created_at=(
                created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=UTC)
            ),
            metadata=(
                json.loads(str(metadata))
                if isinstance(metadata, str)
                else dict(cast(Mapping[str, Any], metadata))
            ),
        )


class PostgreSQLAsyncProcessingRepository(PostgreSQLRepositoryBase, AsyncProcessingRepository):
    _JOB_COLUMNS = """
        id, tenant_id, specialization, operation, idempotency_key,
        payload_object_key, payload_sha256, payload_size_bytes, payload_media_type,
        payload_created_at, result_object_key, result_sha256, result_size_bytes,
        result_media_type, result_created_at, requested_by, max_attempts, attempt_count,
        status, lease_owner, lease_token, leased_until, next_attempt_at, last_error,
        completed_at, created_at, updated_at
    """
    _OUTBOX_COLUMNS = """
        id, tenant_id, aggregate_type, aggregate_id, event_name, idempotency_key,
        payload, max_attempts, attempt_count, status, lease_owner, lease_token,
        leased_until, next_attempt_at, last_error, completed_at, created_at, updated_at
    """

    def save_job(self, job: AsyncJob) -> None:
        self._ensure_tenant(job.tenant_id)
        current = self.get_job(job.tenant_id, job.id.value)
        if current is not None:
            job.assert_persistence_transition_from(current)
        self._execute_without_result(
            """
            INSERT INTO async_jobs (
                id, tenant_id, specialization, operation, idempotency_key,
                payload_object_key, payload_sha256, payload_size_bytes, payload_media_type,
                payload_created_at, result_object_key, result_sha256, result_size_bytes,
                result_media_type, result_created_at, requested_by, max_attempts,
                attempt_count, status, lease_owner, lease_token, leased_until,
                next_attempt_at, last_error, completed_at, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(specialization)s, %(operation)s,
                %(idempotency_key)s, %(payload_object_key)s, %(payload_sha256)s,
                %(payload_size_bytes)s, %(payload_media_type)s, %(payload_created_at)s,
                %(result_object_key)s, %(result_sha256)s, %(result_size_bytes)s,
                %(result_media_type)s, %(result_created_at)s, %(requested_by)s,
                %(max_attempts)s, %(attempt_count)s, %(status)s, %(lease_owner)s,
                %(lease_token)s, %(leased_until)s, %(next_attempt_at)s, %(last_error)s,
                %(completed_at)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                result_object_key = EXCLUDED.result_object_key,
                result_sha256 = EXCLUDED.result_sha256,
                result_size_bytes = EXCLUDED.result_size_bytes,
                result_media_type = EXCLUDED.result_media_type,
                result_created_at = EXCLUDED.result_created_at,
                attempt_count = EXCLUDED.attempt_count,
                status = EXCLUDED.status,
                lease_owner = EXCLUDED.lease_owner,
                lease_token = EXCLUDED.lease_token,
                leased_until = EXCLUDED.leased_until,
                next_attempt_at = EXCLUDED.next_attempt_at,
                last_error = EXCLUDED.last_error,
                completed_at = EXCLUDED.completed_at,
                updated_at = EXCLUDED.updated_at
            """,
            self._job_params(job),
        )

    def get_job(self, tenant_id: TenantId, job_id: str) -> AsyncJob | None:
        row = self._fetch_one(
            f"""
            SELECT {self._JOB_COLUMNS}
            FROM async_jobs
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(job_id).value},
        )
        return None if row is None else self._job_from_row(row)

    def find_job_by_idempotency_key(
        self, tenant_id: TenantId, idempotency_key: str
    ) -> AsyncJob | None:
        row = self._fetch_one(
            f"""
            SELECT {self._JOB_COLUMNS}
            FROM async_jobs
            WHERE tenant_id = %(tenant_id)s AND idempotency_key = %(idempotency_key)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "idempotency_key": idempotency_key.strip()},
        )
        return None if row is None else self._job_from_row(row)

    def lock_job_idempotency(self, tenant_id: TenantId, idempotency_key: str) -> None:
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise ValidationError("idempotency key is required")
        self._execute_without_result(
            """
            SELECT pg_advisory_xact_lock(hashtextextended(%(lock_key)s, 0))
            """,
            {"lock_key": f"{tenant_id.value}:{normalized_key}"},
        )

    def claim_next_job(
        self,
        tenant_id: TenantId,
        specialization: WorkerSpecialization,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
    ) -> AsyncJob | None:
        while True:
            row = self._fetch_one(
                f"""
                SELECT {self._JOB_COLUMNS}
                FROM async_jobs
                WHERE tenant_id = %(tenant_id)s
                  AND specialization = %(specialization)s
                  AND (
                    (status IN ('queued', 'retry-wait') AND next_attempt_at <= %(now)s)
                    OR (status = 'leased' AND leased_until <= %(now)s)
                  )
                ORDER BY created_at ASC, id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,  # nosec B608 -- selected columns are a fixed class constant
                {
                    "tenant_id": tenant_id.value,
                    "specialization": specialization.value,
                    "now": now,
                },
            )
            if row is None:
                return None
            job = self._job_from_row(row)
            if (
                job.state.status is WorkStatus.LEASED
                and job.state.attempt_count >= job.state.max_attempts
            ):
                self.save_job(job.expire_final_lease(now))
                continue
            claimed = job.claim(worker_id, lease_seconds, now)
            self.save_job(claimed)
            return claimed

    def list_jobs(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: WorkStatus | None = None,
        specialization: WorkerSpecialization | None = None,
    ) -> AsyncJobPage:
        page = self._keyset_page(
            pagination,
            scope="async.jobs",
            tenant_id=tenant_id,
            filters={
                "status": None if status is None else status.value,
                "specialization": None if specialization is None else specialization.value,
            },
            fields=(
                CursorField("created_at", value_type=CursorValueType.DATETIME),
                CursorField("id"),
            ),
        )
        predicates = ["tenant_id = %(tenant_id)s"]
        parameters: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if status is not None:
            predicates.append("status = %(status)s")
            parameters["status"] = status.value
        if specialization is not None:
            predicates.append("specialization = %(specialization)s")
            parameters["specialization"] = specialization.value
        rows = self._fetch_all(
            f"""
            SELECT {self._JOB_COLUMNS}
            FROM async_jobs
            WHERE {" AND ".join(predicates)} {page.where_sql}
            ORDER BY created_at ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- clauses are fixed and predicates are selected locally
            parameters,
        )
        selected = rows[: pagination.limit]
        return AsyncJobPage(
            tuple(self._job_from_row(row) for row in selected), page.next_cursor(rows)
        )

    def save_outbox_event(self, event: OutboxEvent) -> None:
        self._ensure_tenant(event.tenant_id)
        current = self.get_outbox_event(event.tenant_id, event.id.value)
        if current is not None:
            event.assert_persistence_transition_from(current)
        self._execute_without_result(
            """
            INSERT INTO outbox_events (
                id, tenant_id, aggregate_type, aggregate_id, event_name,
                idempotency_key, payload, max_attempts, attempt_count, status,
                lease_owner, lease_token, leased_until, next_attempt_at, last_error,
                completed_at, created_at, updated_at
            ) VALUES (
                %(id)s, %(tenant_id)s, %(aggregate_type)s, %(aggregate_id)s,
                %(event_name)s, %(idempotency_key)s, %(payload)s::jsonb,
                %(max_attempts)s, %(attempt_count)s, %(status)s, %(lease_owner)s,
                %(lease_token)s, %(leased_until)s, %(next_attempt_at)s, %(last_error)s,
                %(completed_at)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (tenant_id, id) DO UPDATE SET
                attempt_count = EXCLUDED.attempt_count,
                status = EXCLUDED.status,
                lease_owner = EXCLUDED.lease_owner,
                lease_token = EXCLUDED.lease_token,
                leased_until = EXCLUDED.leased_until,
                next_attempt_at = EXCLUDED.next_attempt_at,
                last_error = EXCLUDED.last_error,
                completed_at = EXCLUDED.completed_at,
                updated_at = EXCLUDED.updated_at
            """,
            self._outbox_params(event),
        )

    def get_outbox_event(self, tenant_id: TenantId, event_id: str) -> OutboxEvent | None:
        row = self._fetch_one(
            f"""
            SELECT {self._OUTBOX_COLUMNS}
            FROM outbox_events
            WHERE tenant_id = %(tenant_id)s AND id = %(id)s
            """,  # nosec B608 -- selected columns are a fixed class constant
            {"tenant_id": tenant_id.value, "id": EntityId.from_value(event_id).value},
        )
        return None if row is None else self._outbox_from_row(row)

    def claim_next_outbox_event(
        self,
        tenant_id: TenantId,
        worker_id: str,
        lease_seconds: int,
        now: datetime,
    ) -> OutboxEvent | None:
        while True:
            row = self._fetch_one(
                f"""
                SELECT {self._OUTBOX_COLUMNS}
                FROM outbox_events
                WHERE tenant_id = %(tenant_id)s
                  AND (
                    (status IN ('queued', 'retry-wait') AND next_attempt_at <= %(now)s)
                    OR (status = 'leased' AND leased_until <= %(now)s)
                  )
                ORDER BY created_at ASC, id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,  # nosec B608 -- selected columns are a fixed class constant
                {"tenant_id": tenant_id.value, "now": now},
            )
            if row is None:
                return None
            event = self._outbox_from_row(row)
            if (
                event.state.status is WorkStatus.LEASED
                and event.state.attempt_count >= event.state.max_attempts
            ):
                self.save_outbox_event(event.expire_final_lease(now))
                continue
            claimed = event.claim(worker_id, lease_seconds, now)
            self.save_outbox_event(claimed)
            return claimed

    def list_outbox_events(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        status: WorkStatus | None = None,
    ) -> OutboxEventPage:
        page = self._keyset_page(
            pagination,
            scope="async.outbox",
            tenant_id=tenant_id,
            filters={"status": None if status is None else status.value},
            fields=(
                CursorField("created_at", value_type=CursorValueType.DATETIME),
                CursorField("id"),
            ),
        )
        predicate = ""
        parameters: dict[str, object] = {"tenant_id": tenant_id.value, **page.parameters}
        if status is not None:
            predicate = "AND status = %(status)s"
            parameters["status"] = status.value
        rows = self._fetch_all(
            f"""
            SELECT {self._OUTBOX_COLUMNS}
            FROM outbox_events
            WHERE tenant_id = %(tenant_id)s {predicate} {page.where_sql}
            ORDER BY created_at ASC, id ASC
            LIMIT %(fetch_limit)s{page.offset_sql}
            """,  # nosec B608 -- clauses are fixed and status predicate is selected locally
            parameters,
        )
        selected = rows[: pagination.limit]
        return OutboxEventPage(
            tuple(self._outbox_from_row(row) for row in selected), page.next_cursor(rows)
        )

    def queue_metrics(self, tenant_id: TenantId) -> dict[str, object]:
        job_rows = self._fetch_all(
            """
            SELECT status, COUNT(*) AS total
            FROM async_jobs
            WHERE tenant_id = %(tenant_id)s
            GROUP BY status
            """,
            {"tenant_id": tenant_id.value},
        )
        outbox_rows = self._fetch_all(
            """
            SELECT status, COUNT(*) AS total
            FROM outbox_events
            WHERE tenant_id = %(tenant_id)s
            GROUP BY status
            """,
            {"tenant_id": tenant_id.value},
        )
        jobs = {str(row["status"]): self._row_int(row, "total") for row in job_rows}
        outbox = {str(row["status"]): self._row_int(row, "total") for row in outbox_rows}
        return {
            "tenant_id": tenant_id.value,
            "generated_at": datetime.now(UTC).isoformat(),
            "jobs": {state.value: jobs.get(state.value, 0) for state in WorkStatus},
            "outbox": {state.value: outbox.get(state.value, 0) for state in WorkStatus},
        }

    def operational_metrics(self) -> dict[str, object]:
        job_rows = self._fetch_all(
            """
            SELECT specialization, status, COUNT(*) AS total
            FROM async_jobs
            GROUP BY specialization, status
            """
        )
        outbox_rows = self._fetch_all(
            """
            SELECT status, COUNT(*) AS total
            FROM outbox_events
            GROUP BY status
            """
        )
        age_row = (
            self._fetch_one(
                """
            SELECT
                COALESCE(
                    EXTRACT(EPOCH FROM (
                        clock_timestamp() - MIN(created_at) FILTER (
                            WHERE status IN ('queued', 'retry-wait')
                              AND next_attempt_at <= clock_timestamp()
                        )
                    )),
                    0
                ) AS oldest_ready_job_age_seconds
            FROM async_jobs
            """
            )
            or {}
        )
        outbox_age_row = (
            self._fetch_one(
                """
            SELECT
                COALESCE(
                    EXTRACT(EPOCH FROM (
                        clock_timestamp() - MIN(created_at) FILTER (
                            WHERE status IN ('queued', 'retry-wait')
                              AND next_attempt_at <= clock_timestamp()
                        )
                    )),
                    0
                ) AS oldest_ready_outbox_age_seconds
            FROM outbox_events
            """
            )
            or {}
        )
        jobs = {status.value: 0 for status in WorkStatus}
        by_specialization = {
            specialization.value: {status.value: 0 for status in WorkStatus}
            for specialization in WorkerSpecialization
        }
        for row in job_rows:
            status = str(row["status"])
            specialization = str(row["specialization"])
            total = self._row_int(row, "total")
            jobs[status] = jobs.get(status, 0) + total
            if specialization in by_specialization:
                by_specialization[specialization][status] = total
        outbox = {status.value: 0 for status in WorkStatus}
        for row in outbox_rows:
            outbox[str(row["status"])] = self._row_int(row, "total")
        return {
            "jobs": jobs,
            "outbox": outbox,
            "jobs_by_specialization": by_specialization,
            "oldest_ready_job_age_seconds": float(
                str(age_row.get("oldest_ready_job_age_seconds", 0))
            ),
            "oldest_ready_outbox_age_seconds": float(
                str(outbox_age_row.get("oldest_ready_outbox_age_seconds", 0))
            ),
        }

    @staticmethod
    def _job_params(job: AsyncJob) -> dict[str, object]:
        result = job.result_artifact
        return {
            "id": job.id.value,
            "tenant_id": job.tenant_id.value,
            "specialization": job.specialization.value,
            "operation": job.operation,
            "idempotency_key": job.idempotency_key,
            "payload_object_key": job.payload_artifact.object_key,
            "payload_sha256": job.payload_artifact.sha256,
            "payload_size_bytes": job.payload_artifact.size_bytes,
            "payload_media_type": job.payload_artifact.media_type,
            "payload_created_at": job.payload_artifact.created_at,
            "result_object_key": None if result is None else result.object_key,
            "result_sha256": None if result is None else result.sha256,
            "result_size_bytes": None if result is None else result.size_bytes,
            "result_media_type": None if result is None else result.media_type,
            "result_created_at": None if result is None else result.created_at,
            "requested_by": job.requested_by,
            "max_attempts": job.state.max_attempts,
            "attempt_count": job.state.attempt_count,
            "status": job.state.status.value,
            "lease_owner": job.state.lease_owner,
            "lease_token": job.state.lease_token,
            "leased_until": job.state.leased_until,
            "next_attempt_at": job.state.next_attempt_at,
            "last_error": job.state.last_error,
            "completed_at": job.state.completed_at,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    @staticmethod
    def _outbox_params(event: OutboxEvent) -> dict[str, object]:
        return {
            "id": event.id.value,
            "tenant_id": event.tenant_id.value,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "event_name": event.event_name,
            "idempotency_key": event.idempotency_key,
            "payload": json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
            "max_attempts": event.state.max_attempts,
            "attempt_count": event.state.attempt_count,
            "status": event.state.status.value,
            "lease_owner": event.state.lease_owner,
            "lease_token": event.state.lease_token,
            "leased_until": event.state.leased_until,
            "next_attempt_at": event.state.next_attempt_at,
            "last_error": event.state.last_error,
            "completed_at": event.state.completed_at,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }

    @classmethod
    def _job_from_row(cls, row: Mapping[str, object]) -> AsyncJob:
        result = None
        if row.get("result_object_key") is not None:
            result = ArtifactReference.create(
                object_key=str(row["result_object_key"]),
                sha256=str(row["result_sha256"]),
                size_bytes=int(str(row["result_size_bytes"])),
                media_type=str(row["result_media_type"]),
                created_at=cls._db_datetime(row["result_created_at"]),
            )
        return AsyncJob.restore(
            job_id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            specialization=WorkerSpecialization.from_value(str(row["specialization"])),
            operation=str(row["operation"]),
            idempotency_key=str(row["idempotency_key"]),
            payload_artifact=ArtifactReference.create(
                object_key=str(row["payload_object_key"]),
                sha256=str(row["payload_sha256"]),
                size_bytes=int(str(row["payload_size_bytes"])),
                media_type=str(row["payload_media_type"]),
                created_at=cls._db_datetime(row["payload_created_at"]),
            ),
            result_artifact=result,
            requested_by=str(row["requested_by"]),
            state=cls._state_from_row(row),
            created_at=cls._db_datetime(row["created_at"]),
            updated_at=cls._db_datetime(row["updated_at"]),
        )

    @classmethod
    def _outbox_from_row(cls, row: Mapping[str, object]) -> OutboxEvent:
        payload_value = row["payload"]
        payload = json.loads(payload_value) if isinstance(payload_value, str) else payload_value
        if not isinstance(payload, Mapping):
            raise ValidationError("outbox database payload must be a JSON object")
        return OutboxEvent.restore(
            event_id=EntityId.from_value(str(row["id"])),
            tenant_id=TenantId.from_value(str(row["tenant_id"])),
            aggregate_type=str(row["aggregate_type"]),
            aggregate_id=str(row["aggregate_id"]),
            event_name=str(row["event_name"]),
            idempotency_key=str(row["idempotency_key"]),
            payload={str(key): value for key, value in payload.items()},
            state=cls._state_from_row(row),
            created_at=cls._db_datetime(row["created_at"]),
            updated_at=cls._db_datetime(row["updated_at"]),
        )

    @classmethod
    def _state_from_row(cls, row: Mapping[str, object]) -> LeasedWorkState:
        return LeasedWorkState.restore(
            max_attempts=int(str(row["max_attempts"])),
            attempt_count=int(str(row["attempt_count"])),
            status=WorkStatus.from_value(str(row["status"])),
            lease_owner=None if row.get("lease_owner") is None else str(row["lease_owner"]),
            lease_token=int(str(row["lease_token"])),
            leased_until=cls._db_optional_datetime(row.get("leased_until")),
            next_attempt_at=cls._db_optional_datetime(row.get("next_attempt_at")),
            last_error=None if row.get("last_error") is None else str(row["last_error"]),
            completed_at=cls._db_optional_datetime(row.get("completed_at")),
        )

    @staticmethod
    def _db_datetime(value: object) -> datetime:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @classmethod
    def _db_optional_datetime(cls, value: object | None) -> datetime | None:
        return None if value is None else cls._db_datetime(value)
