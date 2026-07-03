from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.audit import (
    AuditEventFilter,
    AuditEventRecord,
    AuditExportFormat,
    AuditIntegrityHasher,
)
from openinfra.domain.common import AuditEvent, Pagination, TenantId, ValidationError


class TestAuditDomain:
    def test_audit_record_hash_chain_verifies(self) -> None:
        tenant = TenantId.from_value("default")
        first = AuditEvent.record(tenant, "pytest", "audit.test.one", "audit", "one")
        first_record = AuditEventRecord.create(first, AuditIntegrityHasher.GENESIS_HASH)
        second = AuditEvent.record(tenant, "pytest", "audit.test.two", "audit", "two")
        second_record = AuditEventRecord.create(second, first_record.record_hash)

        assert first_record.verifies() is True
        assert second_record.previous_hash == first_record.record_hash
        assert second_record.as_dict()["integrity_valid"] is True
        assert len(second_record.record_hash) == 64

    def test_audit_filter_rejects_inverted_dates_and_blank_values(self) -> None:
        tenant = TenantId.from_value("default")
        with pytest.raises(ValidationError):
            AuditEventFilter.create(
                tenant,
                Pagination.from_values(10),
                actor=" ",
            )
        with pytest.raises(ValidationError):
            AuditEventFilter.create(
                tenant,
                Pagination.from_values(10),
                created_from=datetime(2026, 2, 1, tzinfo=UTC),
                created_to=datetime(2026, 1, 1, tzinfo=UTC),
            )
        with pytest.raises(ValidationError):
            AuditEventFilter.create(
                tenant,
                Pagination.from_values(10),
                created_from=datetime(2026, 2, 1),
            )

    def test_audit_hash_and_export_format_validation(self) -> None:
        tenant = TenantId.from_value("default")
        event = AuditEvent.record(tenant, "pytest", "audit.test.hash", "audit", "hash")
        with pytest.raises(ValidationError):
            AuditEventRecord.create(event, "bad")
        with pytest.raises(ValueError):
            AuditExportFormat("csv")
