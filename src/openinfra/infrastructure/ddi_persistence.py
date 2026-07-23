from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from openinfra.application.ports import DdiExecutionRepository
from openinfra.domain.common import ConflictError, TenantId, ValidationError
from openinfra.domain.ddi_sync import DdiExecutionJournal
from openinfra.infrastructure.json_store import JsonDocumentStore
from openinfra.infrastructure.postgresql import (
    PostgreSQLRepositoryBase,
    PostgreSQLSessionRegistry,
)


class JsonDdiExecutionRepository(DdiExecutionRepository):
    _COLLECTION = "ipam_ddi_executions"

    def __init__(self, store: JsonDocumentStore) -> None:
        self._store = store

    def acquire_execution_lock(
        self, tenant_id: TenantId, execution_idempotency_key: str
    ) -> None:
        self._key(tenant_id, execution_idempotency_key)
        # JsonUnitOfWork already owns the document-store RLock for the whole transaction.

    def find_by_idempotency_key(
        self, tenant_id: TenantId, execution_idempotency_key: str
    ) -> DdiExecutionJournal | None:
        key = self._key(tenant_id, execution_idempotency_key)
        with self._store.lock:
            payload = self._collection().get(key)
            if payload is None:
                return None
            if not isinstance(payload, dict):
                raise ValidationError("stored DDI execution journal must be a JSON object")
            return DdiExecutionJournal.restore({str(k): v for k, v in payload.items()})

    def save(self, journal: DdiExecutionJournal) -> None:
        key = self._key(journal.tenant_id, journal.execution_idempotency_key)
        with self._store.lock:
            collection = self._collection()
            existing = collection.get(key)
            if existing is not None:
                if not isinstance(existing, dict):
                    raise ValidationError("stored DDI execution journal must be a JSON object")
                restored = DdiExecutionJournal.restore(
                    {str(k): v for k, v in existing.items()}
                )
                if restored.id != journal.id:
                    raise ConflictError("DDI execution idempotency key already exists")
                restored.ensure_same_request(journal.request_fingerprint)
            collection[key] = journal.as_dict()
            self._store.mark_dirty()

    def _collection(self) -> dict[str, Any]:
        value = self._store.data.setdefault(self._COLLECTION, {})
        if not isinstance(value, dict):
            raise ValidationError("DDI execution collection must be an object")
        return value

    @staticmethod
    def _key(tenant_id: TenantId, execution_idempotency_key: str) -> str:
        normalized = execution_idempotency_key.strip()
        if not normalized:
            raise ValidationError("DDI execution idempotency key is mandatory")
        return f"{tenant_id.value}:{normalized}"


class PostgreSQLDdiExecutionRepository(PostgreSQLRepositoryBase, DdiExecutionRepository):
    def __init__(self, registry: PostgreSQLSessionRegistry) -> None:
        super().__init__(registry)

    def acquire_execution_lock(
        self, tenant_id: TenantId, execution_idempotency_key: str
    ) -> None:
        normalized = execution_idempotency_key.strip()
        if not normalized:
            raise ValidationError("DDI execution idempotency key is mandatory")
        self._execute_without_result(
            """
            SELECT pg_advisory_xact_lock(hashtextextended(%(lock_scope)s, 0))
            """,
            {"lock_scope": f"ipam-ddi:{tenant_id.value}:{normalized}"},
        )

    def find_by_idempotency_key(
        self, tenant_id: TenantId, execution_idempotency_key: str
    ) -> DdiExecutionJournal | None:
        row = self._fetch_one(
            """
            SELECT payload
            FROM ipam_ddi_executions
            WHERE tenant_id = %(tenant_id)s
              AND execution_idempotency_key = %(execution_idempotency_key)s
            FOR UPDATE
            """,
            {
                "tenant_id": tenant_id.value,
                "execution_idempotency_key": execution_idempotency_key.strip(),
            },
        )
        if row is None:
            return None
        return DdiExecutionJournal.restore(self._payload(row))

    def save(self, journal: DdiExecutionJournal) -> None:
        self._ensure_tenant(journal.tenant_id)
        payload = json.dumps(journal.as_dict(), sort_keys=True, separators=(",", ":"))
        try:
            self._execute_without_result(
                """
                INSERT INTO ipam_ddi_executions (
                    id,
                    tenant_id,
                    execution_idempotency_key,
                    request_fingerprint,
                    status,
                    reconciliation_required,
                    created_at,
                    updated_at,
                    payload
                ) VALUES (
                    %(id)s,
                    %(tenant_id)s,
                    %(execution_idempotency_key)s,
                    %(request_fingerprint)s,
                    %(status)s,
                    %(reconciliation_required)s,
                    %(created_at)s,
                    %(updated_at)s,
                    %(payload)s::jsonb
                )
                ON CONFLICT (tenant_id, execution_idempotency_key) DO UPDATE SET
                    request_fingerprint = EXCLUDED.request_fingerprint,
                    status = EXCLUDED.status,
                    reconciliation_required = EXCLUDED.reconciliation_required,
                    updated_at = EXCLUDED.updated_at,
                    payload = EXCLUDED.payload
                WHERE ipam_ddi_executions.id = EXCLUDED.id
                  AND ipam_ddi_executions.request_fingerprint = EXCLUDED.request_fingerprint
                """,
                {
                    "id": journal.id.value,
                    "tenant_id": journal.tenant_id.value,
                    "execution_idempotency_key": journal.execution_idempotency_key,
                    "request_fingerprint": journal.request_fingerprint,
                    "status": journal.status.value,
                    "reconciliation_required": journal.reconciliation_required,
                    "created_at": journal.created_at,
                    "updated_at": journal.updated_at,
                    "payload": payload,
                },
            )
        except Exception as exc:
            raise ConflictError(
                "DDI execution idempotency key conflicts with an existing request"
            ) from exc

    @staticmethod
    def _payload(row: Mapping[str, object]) -> dict[str, object]:
        value = row.get("payload")
        if isinstance(value, str):
            decoded = json.loads(value)
        else:
            decoded = value
        if not isinstance(decoded, dict):
            raise ValidationError("postgresql DDI execution payload must be an object")
        return {str(key): item for key, item in decoded.items()}
