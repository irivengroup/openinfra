from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openinfra.application.container import ApplicationFactory
from openinfra.application.network_config_compliance_services import (
    AssessNetworkConfigComplianceCommand,
    ListNetworkConfigBaselinesCommand,
    ListNetworkConfigObservationsCommand,
    RetireNetworkConfigBaselineCommand,
    SubmitNetworkConfigObservationCommand,
    UpsertNetworkConfigBaselineCommand,
)
from openinfra.application.security_services import BootstrapTokenCommand
from openinfra.domain.common import AccessDeniedError, ConflictError


class TestNetworkConfigComplianceServices:
    def test_lifecycle_idempotency_persistence_and_compliance(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        app, token = self._app(path)
        assert (
            app.ressources_inventory_quality_service is app.it_resources_management_quality_service
        )
        baseline = app.network_config_compliance_service.upsert_baseline(
            self._baseline_command(token)
        )
        updated = app.network_config_compliance_service.upsert_baseline(
            self._baseline_command(token, expected={"hostname": "core-01", "ntp": ["10.0.0.10"]})
        )
        assert updated.id == baseline.id and updated.version == 2
        observed_at = datetime.now(UTC) - timedelta(minutes=1)
        observation = app.network_config_compliance_service.submit_observation(
            SubmitNetworkConfigObservationCommand(
                "default",
                "pytest",
                token,
                "collector-core-0001",
                "netconf",
                "collector-paris",
                "network-device/core-01",
                "ios-xe",
                {"hostname": "core-02", "ntp": ["10.0.0.10"]},
                observed_at,
            )
        )
        repeated = app.network_config_compliance_service.submit_observation(
            SubmitNetworkConfigObservationCommand(
                "default",
                "pytest",
                token,
                "collector-core-0001",
                "netconf",
                "collector-paris",
                "network-device/core-01",
                "ios-xe",
                {"hostname": "core-02", "ntp": ["10.0.0.10"]},
                observed_at,
            )
        )
        assert repeated == observation
        with pytest.raises(ConflictError):
            app.network_config_compliance_service.submit_observation(
                SubmitNetworkConfigObservationCommand(
                    "default",
                    "pytest",
                    token,
                    "collector-core-0001",
                    "netconf",
                    "collector-paris",
                    "network-device/core-01",
                    "ios-xe",
                    {"hostname": "different"},
                    observed_at,
                )
            )
        report = app.network_config_compliance_service.assess(
            AssessNetworkConfigComplianceCommand("default", token, baseline_code="CORE-01-GOLDEN")
        )
        assert report.items[0].status.value == "drift"
        assert report.items[0].drifts[0].path == "/hostname"
        assert (
            len(
                app.network_config_compliance_service.list_observations(
                    ListNetworkConfigObservationsCommand("default", token)
                ).items
            )
            == 1
        )
        restarted = ApplicationFactory().create_json_application(path, seed=False)
        assert (
            restarted.network_config_compliance_service.list_baselines(
                ListNetworkConfigBaselinesCommand("default", token)
            )
            .items[0]
            .version
            == 2
        )
        retired = restarted.network_config_compliance_service.retire_baseline(
            RetireNetworkConfigBaselineCommand("default", "pytest", token, updated.id.value)
        )
        assert retired.status.value == "retired"

    def test_roles_tenant_isolation_and_missing_observation(self, tmp_path: Path) -> None:
        app = ApplicationFactory().create_json_application(tmp_path / "state.json")
        operator, reader, other = "o" * 40, "r" * 40, "t" * 40
        for tenant, subject, roles, token in (
            ("default", "operator", ("network-config:operator",), operator),
            ("default", "reader", ("network-config:reader",), reader),
            ("other", "reader", ("network-config:reader",), other),
        ):
            app.security_service.bootstrap_token(
                BootstrapTokenCommand(tenant, "pytest", subject, roles, token)
            )
        app.network_config_compliance_service.upsert_baseline(self._baseline_command(operator))
        assert (
            app.network_config_compliance_service.assess(
                AssessNetworkConfigComplianceCommand("default", reader)
            )
            .items[0]
            .status.value
            == "missing-observation"
        )
        assert (
            app.network_config_compliance_service.list_baselines(
                ListNetworkConfigBaselinesCommand("other", other)
            ).items
            == ()
        )
        with pytest.raises(AccessDeniedError):
            app.network_config_compliance_service.upsert_baseline(self._baseline_command(reader))

    @staticmethod
    def _app(path: Path):
        app = ApplicationFactory().create_json_application(path)
        token = "a" * 40
        app.security_service.bootstrap_token(
            BootstrapTokenCommand("default", "pytest", "admin", ("admin",), token)
        )
        return app, token

    @staticmethod
    def _baseline_command(
        token: str, expected: object | None = None
    ) -> UpsertNetworkConfigBaselineCommand:
        return UpsertNetworkConfigBaselineCommand(
            "default",
            "pytest",
            token,
            "CORE-01-GOLDEN",
            "network-device/core-01",
            "ios-xe",
            expected or {"hostname": "core-01"},
            (),
            ("/hostname",),
            "Network Team",
            "Approved production golden configuration",
        )

    def test_validation_conflict_pagination_and_failure_edges(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from openinfra.application.ports import NetworkConfigBaselinePage
        from openinfra.domain.common import ConflictError, NotFoundError, ValidationError

        app, token = self._app(tmp_path / "state-edges.json")
        baseline = app.network_config_compliance_service.upsert_baseline(
            self._baseline_command(token)
        )
        with pytest.raises(ConflictError, match="device cannot be changed"):
            app.network_config_compliance_service.upsert_baseline(
                UpsertNetworkConfigBaselineCommand(
                    "default",
                    "pytest",
                    token,
                    "CORE-01-GOLDEN",
                    "network-device/core-02",
                    "ios-xe",
                    {"hostname": "core-02"},
                    (),
                    (),
                    "Network Team",
                    "Approved production golden configuration",
                )
            )
        with pytest.raises(NotFoundError, match="not found"):
            app.network_config_compliance_service.retire_baseline(
                RetireNetworkConfigBaselineCommand(
                    "default", "pytest", token, "00000000-0000-4000-8000-000000000001"
                )
            )
        with pytest.raises(ValidationError, match="valid JSON"):
            app.network_config_compliance_service.upsert_baseline(
                self._baseline_command(token, expected="{invalid")
            )
        for cursor, message in (("invalid", "numeric"), ("-1", "positive")):
            with pytest.raises(ValidationError, match=message):
                app.network_config_compliance_service.list_baselines(
                    ListNetworkConfigBaselinesCommand("default", token, cursor=cursor)
                )
        with pytest.raises(ValidationError, match="ISO-8601"):
            app.network_config_compliance_service.list_observations(
                ListNetworkConfigObservationsCommand("default", token, observed_before="bad-date")
            )
        with pytest.raises(ValidationError, match="timezone-aware"):
            app.network_config_compliance_service.list_observations(
                ListNetworkConfigObservationsCommand(
                    "default", token, observed_before="2026-07-10T12:00:00"
                )
            )
        with pytest.raises(ValidationError, match="mandatory"):
            app.network_config_compliance_service.submit_observation(
                SubmitNetworkConfigObservationCommand(
                    "default",
                    "pytest",
                    token,
                    "collector-edge-0001",
                    "api",
                    "collector-edge",
                    baseline.device_object_key,
                    baseline.platform,
                    baseline.expected_config,
                    "",
                )
            )
        with pytest.raises(ValidationError, match="unsupported"):
            app.network_config_compliance_service.assess(
                AssessNetworkConfigComplianceCommand("default", token, status="unknown")
            )

        retired = app.network_config_compliance_service.retire_baseline(
            RetireNetworkConfigBaselineCommand("default", "pytest", token, baseline.id.value)
        )
        repository = app.network_config_compliance_repository
        monkeypatch.setattr(
            repository,
            "list_baselines",
            lambda *_args, **_kwargs: NetworkConfigBaselinePage((retired,), None),
        )
        assert (
            app.network_config_compliance_service.assess(
                AssessNetworkConfigComplianceCommand("default", token)
            ).items
            == ()
        )

    def test_observation_persistence_verification_failure(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        app, token = self._app(tmp_path / "state-persistence-failure.json")
        repository = app.network_config_compliance_repository
        monkeypatch.setattr(
            repository,
            "find_observation_by_idempotency_key",
            lambda *_args, **_kwargs: None,
        )
        with pytest.raises(ConflictError, match="could not be persisted"):
            app.network_config_compliance_service.submit_observation(
                SubmitNetworkConfigObservationCommand(
                    "default",
                    "",
                    token,
                    "collector-edge-0002",
                    "api",
                    "collector-edge",
                    "network-device/core-01",
                    "ios-xe",
                    {"hostname": "core-01"},
                    datetime.now(UTC),
                )
            )
