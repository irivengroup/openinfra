from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.audit_services import (
    ExportAuditEventsCommand,
    ListAuditEventsCommand,
    VerifyAuditIntegrityCommand,
)
from openinfra.application.container import ApplicationFactory
from openinfra.application.ipam_services import AllocateIpCommand
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import AccessDeniedError, ValidationError


class TestAuditTrailServices:
    def test_audit_service_filters_exports_and_detects_tampering(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "k" * 40
        viewer_token = "l" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "audit-admin", ("admin",), admin_token)
        )
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "audit-viewer", ("viewer",), viewer_token)
        )
        app.ipam_service.allocate(
            AllocateIpCommand(
                tenant_id="default",
                actor="operator",
                vrf="default",
                prefix="10.97.0.0/30",
                hostname="audit-filter-srv",
                idempotency_key="audit-filter-1",
            )
        )

        filtered = app.audit_service.list_events(
            ListAuditEventsCommand(
                tenant_id="default",
                admin_token=admin_token,
                limit=10,
                actor="operator",
                action="ipam.address.allocated",
                target_type="ip_reservation",
                severity="info",
                created_from=datetime.now(UTC) - timedelta(minutes=5),
                created_to=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        exported_json = app.audit_service.export_events(
            ExportAuditEventsCommand(
                tenant_id="default",
                admin_token=admin_token,
                format="json",
                limit=10,
                action="ipam.address.allocated",
            )
        )
        exported_jsonl = app.audit_service.export_events(
            ExportAuditEventsCommand(
                tenant_id="default",
                admin_token=admin_token,
                format="jsonl",
                limit=10,
            )
        )

        assert len(filtered.items) == 1
        assert filtered.items[0].event.actor == "operator"
        assert filtered.items[0].verifies() is True
        assert exported_json.content_type == "application/json"
        assert exported_json.payload.startswith("{")
        assert exported_jsonl.content_type == "application/x-ndjson"
        assert exported_jsonl.head_hash
        with pytest.raises(AccessDeniedError):
            app.audit_service.list_events(ListAuditEventsCommand("default", viewer_token, limit=10))
        app.store.data["audit_events"][0]["record_hash"] = "f" * 64
        tampered = app.audit_service.verify_integrity(
            VerifyAuditIntegrityCommand("default", admin_token, limit=100)
        )
        assert tampered.valid is False
        assert tampered.broken_record_id is not None

    def test_audit_service_rejects_invalid_limits_and_formats(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        admin_token = "m" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "audit-admin", ("admin",), admin_token)
        )
        with pytest.raises(ValidationError):
            app.audit_service.list_events(ListAuditEventsCommand("default", admin_token, limit=0))
        with pytest.raises(ValueError):
            app.audit_service.export_events(
                ExportAuditEventsCommand("default", admin_token, format="csv", limit=10)
            )
        with pytest.raises(ValidationError):
            app.audit_service.verify_integrity(
                VerifyAuditIntegrityCommand("default", admin_token, limit=0)
            )

    def test_audit_repository_pagination_and_filters_are_strict(self, tmp_path: Path) -> None:
        from openinfra.domain.audit import AuditEventFilter
        from openinfra.domain.common import AuditEvent, Pagination, Severity, TenantId

        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        tenant = TenantId.from_value("default")
        with app.transaction_manager.begin() as unit_of_work:
            app.audit_repository.append(
                AuditEvent.record(
                    tenant,
                    "filter-actor",
                    "audit.filter.event",
                    "audit_target",
                    "target-1",
                    severity=Severity.WARNING,
                )
            )
            unit_of_work.commit()

        actor_page = app.audit_repository.list_records(
            AuditEventFilter.create(
                tenant,
                Pagination.from_values(10),
                actor="filter-actor",
                target_type="audit_target",
                severity="warning",
            )
        )
        no_actor_page = app.audit_repository.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(10), actor="another-actor")
        )
        no_action_page = app.audit_repository.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(10), action="audit.none")
        )
        no_target_page = app.audit_repository.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(10), target_type="none")
        )
        no_severity_page = app.audit_repository.list_records(
            AuditEventFilter.create(tenant, Pagination.from_values(10), severity="error")
        )

        assert len(actor_page.items) == 1
        assert no_actor_page.items == ()
        assert no_action_page.items == ()
        assert no_target_page.items == ()
        assert no_severity_page.items == ()
        with pytest.raises(ValidationError):
            app.audit_repository.list_records(
                AuditEventFilter.create(tenant, Pagination.from_values(10, "bad"))
            )
        with pytest.raises(ValidationError):
            app.audit_repository.list_records(
                AuditEventFilter.create(tenant, Pagination.from_values(10, "-1"))
            )
