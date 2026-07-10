from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.flow_matrix_services import (
    CompareFlowMatrixCommand,
    ListFlowDeclarationsCommand,
    ListFlowObservationsCommand,
    RetireFlowDeclarationCommand,
    SubmitFlowObservationCommand,
    UpsertFlowDeclarationCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import AccessDeniedError, ConflictError, ValidationError


class TestFlowMatrixServices:
    def test_declared_and_observed_flows_produce_all_compliance_states(
        self, tmp_path: Path
    ) -> None:
        app, token = self._application(tmp_path / "state.json")
        end = datetime.now(UTC) - timedelta(minutes=1)
        start = end - timedelta(hours=1)

        allow = self._declare(
            app,
            token,
            code="APP-WEB-HTTPS",
            source_selector="object:application/portal",
            destination_selector="cidr:10.20.30.0/24",
            protocol="tcp",
            port=443,
            decision="allow",
            priority=100,
            valid_from=start - timedelta(days=1),
        )
        deny = self._declare(
            app,
            token,
            code="ADMIN-SSH-DENY",
            source_selector="cidr:10.10.0.0/16",
            destination_selector="cidr:10.20.40.0/24",
            protocol="tcp",
            port=22,
            decision="deny",
            priority=500,
            valid_from=start - timedelta(days=1),
        )
        orphan = self._declare(
            app,
            token,
            code="BACKUP-TLS",
            source_selector="cidr:10.50.0.0/16",
            destination_selector="cidr:10.60.0.0/16",
            protocol="tcp",
            port=443,
            decision="allow",
            priority=50,
            valid_from=start - timedelta(days=1),
        )

        compliant = self._observe(
            app,
            token,
            key="collector-01:compliant",
            source_ip="10.1.1.10",
            destination_ip="10.20.30.40",
            source_object_key="application/portal",
            protocol="tcp",
            port=443,
            first_seen=start + timedelta(minutes=10),
            last_seen=start + timedelta(minutes=11),
        )
        denied = self._observe(
            app,
            token,
            key="collector-01:denied",
            source_ip="10.10.2.20",
            destination_ip="10.20.40.22",
            protocol="tcp",
            port=22,
            first_seen=start + timedelta(minutes=20),
            last_seen=start + timedelta(minutes=21),
        )
        undeclared = self._observe(
            app,
            token,
            key="collector-01:undeclared",
            source_ip="192.0.2.10",
            destination_ip="198.51.100.20",
            protocol="udp",
            port=53,
            first_seen=start + timedelta(minutes=30),
            last_seen=start + timedelta(minutes=31),
        )

        report = app.flow_matrix_service.compare(
            CompareFlowMatrixCommand(
                tenant_id="default",
                admin_token=token,
                window_start=start,
                window_end=end,
                limit=100,
            )
        )

        assert report.totals == {
            "compliant": 1,
            "denied-observed": 1,
            "undeclared-observed": 1,
            "declared-unobserved": 1,
        }
        assert report.observation_count == 3
        assert report.declaration_count == 3
        assert report.packets == 30
        assert report.bytes_count == 3072
        assert report.truncated is False
        by_status = {row.status.value: row for row in report.rows}
        assert by_status["compliant"].observation == compliant
        assert by_status["compliant"].declaration == allow
        assert by_status["denied-observed"].observation == denied
        assert by_status["denied-observed"].declaration == deny
        assert by_status["undeclared-observed"].observation == undeclared
        assert by_status["undeclared-observed"].declaration is None
        assert by_status["declared-unobserved"].declaration == orphan
        assert report.as_dict()["row_count"] == 4

        denied_only = app.flow_matrix_service.compare(
            CompareFlowMatrixCommand(
                "default",
                token,
                start,
                end,
                status="denied-observed",
                source="netflow",
            )
        )
        assert len(denied_only.rows) == 1
        assert denied_only.rows[0].declaration == deny
        assert denied_only.totals == report.totals

    def test_declaration_lifecycle_observation_idempotency_and_json_restart(
        self, tmp_path: Path
    ) -> None:
        data_path = tmp_path / "state.json"
        app, token = self._application(data_path)
        now = datetime.now(UTC) - timedelta(minutes=2)
        created = self._declare(
            app,
            token,
            code="DNS-UDP",
            source_selector="any",
            destination_selector="cidr:10.53.0.0/16",
            protocol="udp",
            port=53,
            decision="allow",
            priority=10,
            valid_from=now - timedelta(days=1),
        )
        updated = self._declare(
            app,
            token,
            code="DNS-UDP",
            source_selector="cidr:10.0.0.0/8",
            destination_selector="cidr:10.53.0.0/16",
            protocol="udp",
            port=53,
            decision="allow",
            priority=20,
            valid_from=now - timedelta(days=1),
        )
        observed = self._observe(
            app,
            token,
            key="dns-collector:000001",
            source_ip="10.1.2.3",
            destination_ip="10.53.0.53",
            protocol="udp",
            port=53,
            first_seen=now - timedelta(minutes=1),
            last_seen=now,
        )
        repeated = self._observe(
            app,
            token,
            key="dns-collector:000001",
            source_ip="10.1.2.3",
            destination_ip="10.53.0.53",
            protocol="udp",
            port=53,
            first_seen=now - timedelta(minutes=1),
            last_seen=now,
        )

        assert updated.id == created.id
        assert updated.version == 2
        assert repeated == observed
        with pytest.raises(ConflictError):
            self._observe(
                app,
                token,
                key="dns-collector:000001",
                source_ip="10.1.2.4",
                destination_ip="10.53.0.53",
                protocol="udp",
                port=53,
                first_seen=now - timedelta(minutes=1),
                last_seen=now,
            )

        retired = app.flow_matrix_service.retire_declaration(
            RetireFlowDeclarationCommand("default", "pytest", token, updated.id.value)
        )
        assert retired.status.value == "retired"
        assert retired.version == 3
        assert (
            app.flow_matrix_service.retire_declaration(
                RetireFlowDeclarationCommand("default", "pytest", token, updated.id.value)
            ).version
            == 3
        )
        assert (
            app.flow_matrix_service.list_declarations(
                ListFlowDeclarationsCommand("default", token)
            ).items
            == ()
        )
        assert (
            len(
                app.flow_matrix_service.list_declarations(
                    ListFlowDeclarationsCommand("default", token, include_retired=True)
                ).items
            )
            == 1
        )

        restarted = ApplicationFactory().create_json_application(data_path, seed=False)
        listed = restarted.flow_matrix_service.list_observations(
            ListFlowObservationsCommand(
                "default", token, now - timedelta(hours=1), now + timedelta(minutes=1)
            )
        )
        assert listed.items == (observed,)
        assert (
            restarted.flow_matrix_repository.find_declaration_by_code(
                retired.tenant_id, retired.code
            )
            == retired
        )

    def test_permissions_tenant_isolation_pagination_and_window_validation(
        self, tmp_path: Path
    ) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        operator = "o" * 40
        reader = "r" * 40
        tenant_reader = "t" * 40
        for tenant, subject, roles, token in (
            ("default", "operator", ("flow:operator",), operator),
            ("default", "reader", ("flow:reader",), reader),
            ("other", "other-reader", ("flow:reader",), tenant_reader),
        ):
            app.security_service.bootstrap_token(
                BootstrapTokenCommand(tenant, "pytest", subject, roles, token)
            )
        now = datetime.now(UTC) - timedelta(minutes=2)
        for index in range(3):
            self._declare(
                app,
                operator,
                code=f"WEB-{index:02d}",
                source_selector="any",
                destination_selector=f"cidr:10.{index}.0.0/16",
                protocol="tcp",
                port=443,
                decision="allow",
                priority=index,
                valid_from=now - timedelta(days=1),
            )

        first = app.flow_matrix_service.list_declarations(
            ListFlowDeclarationsCommand("default", reader, limit=2)
        )
        second = app.flow_matrix_service.list_declarations(
            ListFlowDeclarationsCommand("default", reader, limit=2, cursor=first.next_cursor)
        )
        assert [item.code for item in first.items] == ["WEB-00", "WEB-01"]
        assert [item.code for item in second.items] == ["WEB-02"]
        assert (
            app.flow_matrix_service.list_declarations(
                ListFlowDeclarationsCommand("other", tenant_reader)
            ).items
            == ()
        )

        with pytest.raises(AccessDeniedError):
            self._declare(
                app,
                reader,
                code="DENIED-WRITE",
                source_selector="any",
                destination_selector="any",
                protocol="icmp",
                port=None,
                decision="allow",
                priority=1,
                valid_from=now,
            )
        with pytest.raises(ValidationError, match="31 days"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand(
                    "default",
                    reader,
                    now - timedelta(days=32),
                    now,
                )
            )
        with pytest.raises(ValidationError, match="future"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand(
                    "default",
                    reader,
                    now,
                    datetime.now(UTC) + timedelta(hours=1),
                )
            )
        with pytest.raises(ValidationError, match="unsupported"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand(
                    "default", reader, now - timedelta(hours=1), now, status="bad"
                )
            )
        with pytest.raises(ValidationError, match="numeric"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand(
                    "default", reader, now - timedelta(hours=1), now, cursor="x"
                )
            )
        with pytest.raises(ValidationError, match="after"):
            app.flow_matrix_service.compare(CompareFlowMatrixCommand("default", reader, now, now))
        with pytest.raises(ValidationError, match="ISO-8601"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand("default", reader, "not-a-date", now)
            )
        with pytest.raises(ValidationError, match="timezone-aware"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand("default", reader, datetime(2026, 7, 10, 12, 0), now)
            )
        with pytest.raises(ValidationError, match="positive"):
            app.flow_matrix_service.compare(
                CompareFlowMatrixCommand(
                    "default", reader, now - timedelta(hours=1), now, cursor="-1"
                )
            )

    def _application(self, data_path: Path):
        app = ApplicationFactory().create_json_application(data_path)
        token = "f" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "flow-admin", ("admin",), token)
        )
        return app, token

    def _declare(
        self,
        app,
        token: str,
        *,
        code: str,
        source_selector: str,
        destination_selector: str,
        protocol: str,
        port: int | None,
        decision: str,
        priority: int,
        valid_from: datetime,
    ):
        return app.flow_matrix_service.upsert_declaration(
            UpsertFlowDeclarationCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                code=code,
                source_selector=source_selector,
                destination_selector=destination_selector,
                protocol=protocol,
                destination_port_start=port,
                destination_port_end=port,
                decision=decision,
                priority=priority,
                owner="network team",
                justification="approved by network governance",
                valid_from=valid_from,
            )
        )

    def _observe(
        self,
        app,
        token: str,
        *,
        key: str,
        source_ip: str,
        destination_ip: str,
        protocol: str,
        port: int | None,
        first_seen: datetime,
        last_seen: datetime,
        source_object_key: str | None = None,
    ):
        return app.flow_matrix_service.submit_observation(
            SubmitFlowObservationCommand(
                tenant_id="default",
                actor="pytest",
                admin_token=token,
                idempotency_key=key,
                source="netflow",
                collector="collector-01",
                source_ip=source_ip,
                destination_ip=destination_ip,
                source_object_key=source_object_key,
                destination_object_key=None,
                protocol=protocol,
                destination_port=port,
                packets=10,
                bytes_count=1024,
                first_seen=first_seen,
                last_seen=last_seen,
            )
        )
