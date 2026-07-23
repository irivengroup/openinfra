from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.domain.ddi_sync import DdiExecutionJournal
from openinfra.domain.ipam import DdiProvider
from openinfra.infrastructure.ddi_persistence import (
    JsonDdiExecutionRepository,
    PostgreSQLDdiExecutionRepository,
)
from openinfra.infrastructure.json_store import JsonDocumentStore
from openinfra.infrastructure.postgresql import (
    ConnectionProtocol,
    CursorProtocol,
    PostgreSQLClusterProfile,
    PostgreSQLConnectionFactory,
    PostgreSQLSessionRegistry,
    PostgreSQLTransactionManager,
)


class DdiCursor(CursorProtocol):
    def __init__(self, connection: DdiConnection) -> None:
        self._connection = connection
        self._row: Mapping[str, object] | None = None
        self.rowcount = -1

    def execute(
        self,
        query: str,
        params: Mapping[str, object] | Sequence[object] | None = None,
    ) -> object:
        normalized = " ".join(query.split())
        effective = dict(params or {})
        self._connection.statements.append((normalized, effective))
        self._row = None
        if normalized.startswith("SELECT payload FROM ipam_ddi_executions"):
            if self._connection.payload is not None:
                self._row = {"payload": self._connection.payload}
        elif normalized.startswith("INSERT INTO ipam_ddi_executions"):
            self._connection.payload = str(effective["payload"])
        elif normalized.startswith("SELECT pg_advisory_xact_lock"):
            self._connection.lock_scopes.append(str(effective["lock_scope"]))
        elif normalized.startswith("INSERT INTO tenants"):
            pass
        else:
            raise AssertionError(f"unexpected DDI repository SQL: {normalized}")
        return self

    def fetchone(self) -> Mapping[str, object] | None:
        return self._row

    def fetchall(self) -> Sequence[Mapping[str, object]]:
        return () if self._row is None else (self._row,)

    def close(self) -> object:
        return None


class DdiConnection(ConnectionProtocol):
    def __init__(self) -> None:
        self.payload: str | None = None
        self.lock_scopes: list[str] = []
        self.statements: list[tuple[str, dict[str, object]]] = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self) -> CursorProtocol:
        return DdiCursor(self)

    def commit(self) -> object:
        self.commits += 1
        return None

    def rollback(self) -> object:
        self.rollbacks += 1
        return None

    def close(self) -> object:
        return None


class DdiConnector:
    def __init__(self) -> None:
        self.connection = DdiConnection()

    def connect(self, _dsn: str, _profile: PostgreSQLClusterProfile) -> ConnectionProtocol:
        return self.connection


def test_postgresql_ddi_repository_locks_persists_and_restores_journal() -> None:
    connector = DdiConnector()
    registry = PostgreSQLSessionRegistry(
        PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=connector.connect,
        )
    )
    repository = PostgreSQLDdiExecutionRepository(registry)
    transaction_manager = PostgreSQLTransactionManager(registry)
    tenant = TenantId.from_value("tenant-a")
    journal = DdiExecutionJournal.create(
        tenant_id=tenant,
        vrf_name="global",
        reservation_idempotency_key="reservation-1",
        execution_idempotency_key="execution-1",
        request_fingerprint="a" * 64,
        providers=(DdiProvider.BIND, DdiProvider.KEA),
    ).start()

    with transaction_manager.begin() as unit_of_work:
        repository.acquire_execution_lock(tenant, "execution-1")
        assert repository.find_by_idempotency_key(tenant, "execution-1") is None
        repository.save(journal)
        unit_of_work.commit()

    with transaction_manager.begin() as unit_of_work:
        restored = repository.find_by_idempotency_key(tenant, "execution-1")
        unit_of_work.commit()

    assert restored == journal
    assert connector.connection.commits == 2
    assert connector.connection.lock_scopes == ["ipam-ddi:tenant-a:execution-1"]
    assert connector.connection.payload is not None
    assert json.loads(connector.connection.payload)["status"] == "running"
    assert any("FOR UPDATE" in query for query, _params in connector.connection.statements)
    assert any("ON CONFLICT" in query for query, _params in connector.connection.statements)


def test_ddi_repositories_reject_corrupt_state_and_conflicting_idempotency(
    tmp_path: Path,
) -> None:
    tenant = TenantId.from_value("tenant-a")
    store = JsonDocumentStore(tmp_path / "state.json")
    json_repository = JsonDdiExecutionRepository(store)

    with pytest.raises(ValidationError, match="idempotency key is mandatory"):
        json_repository.acquire_execution_lock(tenant, "   ")

    store.data["ipam_ddi_executions"] = []
    with pytest.raises(ValidationError, match="collection must be an object"):
        json_repository.find_by_idempotency_key(tenant, "execution-1")

    store.data["ipam_ddi_executions"] = {"tenant-a:execution-1": []}
    with pytest.raises(ValidationError, match="journal must be a JSON object"):
        json_repository.find_by_idempotency_key(tenant, "execution-1")

    first = DdiExecutionJournal.create(
        tenant_id=tenant,
        vrf_name="global",
        reservation_idempotency_key="reservation-1",
        execution_idempotency_key="execution-1",
        request_fingerprint="a" * 64,
        providers=(DdiProvider.BIND,),
    )
    store.data["ipam_ddi_executions"] = {}
    json_repository.save(first)
    conflicting = DdiExecutionJournal.create(
        tenant_id=tenant,
        vrf_name="global",
        reservation_idempotency_key="reservation-1",
        execution_idempotency_key="execution-1",
        request_fingerprint="a" * 64,
        providers=(DdiProvider.BIND,),
    )
    with pytest.raises(ConflictError, match="idempotency key already exists"):
        json_repository.save(conflicting)

    connector = DdiConnector()
    registry = PostgreSQLSessionRegistry(
        PostgreSQLConnectionFactory(
            "postgresql://openinfra@db/openinfra",
            connector=connector.connect,
        )
    )
    postgresql_repository = PostgreSQLDdiExecutionRepository(registry)
    transaction_manager = PostgreSQLTransactionManager(registry)
    with transaction_manager.begin():
        with pytest.raises(ValidationError, match="idempotency key is mandatory"):
            postgresql_repository.acquire_execution_lock(tenant, " ")

    assert PostgreSQLDdiExecutionRepository._payload(
        {"payload": first.as_dict()}
    ) == first.as_dict()
    with pytest.raises(ValidationError, match="payload must be an object"):
        PostgreSQLDdiExecutionRepository._payload({"payload": "[]"})
    with pytest.raises(ValidationError, match="payload must be an object"):
        PostgreSQLDdiExecutionRepository._payload({"payload": []})

    class FailingPostgreSQLDdiExecutionRepository(PostgreSQLDdiExecutionRepository):
        def _execute_without_result(
            self, query: str, parameters: Mapping[str, object] | None = None
        ) -> None:
            if "INSERT INTO ipam_ddi_executions" in query:
                raise RuntimeError("simulated uniqueness conflict")
            super()._execute_without_result(query, parameters)

    failing_repository = FailingPostgreSQLDdiExecutionRepository(registry)
    with transaction_manager.begin():
        with pytest.raises(ConflictError, match="conflicts with an existing request"):
            failing_repository.save(first)
