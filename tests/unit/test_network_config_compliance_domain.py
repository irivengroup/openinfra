from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openinfra.domain.common import Severity, TenantId, ValidationError
from openinfra.domain.network_config_compliance import (
    NetworkConfigBaseline,
    NetworkConfigComplianceReport,
    NetworkConfigDocumentPolicy,
    NetworkConfigObservation,
)


class TestNetworkConfigComplianceDomain:
    def test_comparison_reports_missing_unexpected_mismatch_and_ignored_paths(self) -> None:
        baseline = self._baseline()
        observation = NetworkConfigObservation.create(
            tenant_id=TenantId.from_value("default"),
            idempotency_key="collector-0001",
            source="netconf",
            collector="collector-paris",
            device_object_key="network-device/core-01",
            platform="ios-xe",
            observed_config={
                "hostname": "core-02",
                "interfaces": {"Gi0/1": {"enabled": True}, "Gi0/2": {"enabled": True}},
                "runtime": {"uptime": 999},
            },
            observed_at=datetime.now(UTC),
        )
        report = NetworkConfigComplianceReport.evaluate(baseline, observation)
        assert report.status.value == "drift"
        by_path = {item.path: item for item in report.drifts}
        assert by_path["/hostname"].kind.value == "mismatch"
        assert by_path["/hostname"].severity is Severity.CRITICAL
        assert by_path["/interfaces/Gi0~11/description"].kind.value == "missing"
        assert by_path["/interfaces/Gi0~12"].kind.value == "unexpected"
        assert "/runtime/uptime" not in by_path

    def test_compliant_missing_observation_platform_mismatch_and_secret_rejection(self) -> None:
        baseline = self._baseline()
        same = NetworkConfigObservation.create(
            tenant_id=baseline.tenant_id,
            idempotency_key="collector-0002",
            source="api",
            collector="collector-paris",
            device_object_key=baseline.device_object_key,
            platform=baseline.platform,
            observed_config=baseline.expected_config,
            observed_at=datetime.now(UTC),
        )
        assert NetworkConfigComplianceReport.evaluate(baseline, same).status.value == "compliant"
        assert (
            NetworkConfigComplianceReport.evaluate(baseline, None).status.value
            == "missing-observation"
        )
        other_platform = NetworkConfigObservation.create(
            tenant_id=baseline.tenant_id,
            idempotency_key="collector-0003",
            source="api",
            collector="collector-paris",
            device_object_key=baseline.device_object_key,
            platform="nx-os",
            observed_config=baseline.expected_config,
            observed_at=datetime.now(UTC),
        )
        report = NetworkConfigComplianceReport.evaluate(baseline, other_platform)
        assert report.drifts[0].path == "/platform"
        assert report.drifts[0].severity is Severity.CRITICAL
        with pytest.raises(ValidationError, match="secrets"):
            NetworkConfigDocumentPolicy().normalize({"snmp_community": "public"})
        with pytest.raises(ValidationError, match="private keys"):
            NetworkConfigDocumentPolicy().normalize(
                {"certificate": "-----BEGIN PRIVATE " + "KEY-----\nredacted"}
            )

    @staticmethod
    def _baseline() -> NetworkConfigBaseline:
        return NetworkConfigBaseline.create(
            tenant_id=TenantId.from_value("default"),
            code="CORE-01-GOLDEN",
            device_object_key="network-device/core-01",
            platform="ios-xe",
            expected_config={
                "hostname": "core-01",
                "interfaces": {"Gi0/1": {"enabled": True, "description": "uplink"}},
                "runtime": {"uptime": 1},
            },
            ignored_paths=("/runtime",),
            critical_paths=("/hostname",),
            owner="Network Team",
            justification="Approved production golden configuration",
            actor="pytest",
        )


class TestNetworkConfigComplianceDomainEdges:
    def test_document_policy_rejects_invalid_shape_limits_and_values(self, monkeypatch) -> None:
        policy = NetworkConfigDocumentPolicy()
        with pytest.raises(ValidationError, match="JSON object"):
            policy.normalize([])
        monkeypatch.setattr(policy, "_normalize_value", lambda *_args, **_kwargs: [])
        with pytest.raises(ValidationError, match="root"):
            policy.normalize({})
        monkeypatch.undo()

        oversized = {f"key-{index}": "x" * 16_384 for index in range(64)}
        with pytest.raises(ValidationError, match="1 MiB"):
            policy.normalize(oversized)
        with pytest.raises(ValidationError, match="10000 nodes"):
            policy.normalize({"values": [0] * 10_000})
        nested: object = "leaf"
        for _ in range(34):
            nested = {"next": nested}
        with pytest.raises(ValidationError, match="maximum depth"):
            policy.normalize(nested)
        with pytest.raises(ValidationError, match="keys must be strings"):
            policy.normalize({1: "value"})
        with pytest.raises(ValidationError, match="1 to 128"):
            policy.normalize({"": "value"})
        with pytest.raises(ValidationError, match="scalar"):
            policy.normalize({"banner": "x" * 16_385})
        with pytest.raises(ValidationError, match="unsupported value"):
            policy.normalize({"invalid": object()})

    def test_path_baseline_and_observation_validation_edges(self) -> None:
        from openinfra.domain.common import EntityId
        from openinfra.domain.network_config_compliance import (
            NetworkConfigObservationSource,
            NetworkConfigPathPolicy,
        )

        with pytest.raises(ValidationError, match="unsupported"):
            NetworkConfigObservationSource.from_value("telnet")
        with pytest.raises(ValidationError, match="JSON Pointer"):
            NetworkConfigPathPolicy().normalize_many(("hostname",), "paths")

        baseline = TestNetworkConfigComplianceDomain._baseline()
        baseline_values = {
            "id": baseline.id,
            "tenant_id": baseline.tenant_id,
            "code": baseline.code,
            "device_object_key": baseline.device_object_key,
            "platform": baseline.platform,
            "expected_config": baseline.expected_config,
            "ignored_paths": baseline.ignored_paths,
            "critical_paths": baseline.critical_paths,
            "owner": baseline.owner,
            "justification": baseline.justification,
            "status": baseline.status.value,
            "version": baseline.version,
            "created_by": baseline.created_by,
            "created_at": baseline.created_at,
            "updated_by": baseline.updated_by,
            "updated_at": baseline.updated_at,
        }
        for override, message in (
            ({"code": "bad code"}, "code is invalid"),
            ({"platform": "x"}, "platform"),
            ({"owner": "x"}, "owner"),
            ({"justification": "short"}, "justification"),
            ({"version": 0}, "version"),
            ({"created_at": datetime.now()}, "timezone-aware"),
            ({"updated_by": "x"}, "2 to 255"),
        ):
            with pytest.raises(ValidationError, match=message):
                NetworkConfigBaseline.restore(**(baseline_values | override))
        retired = baseline.retire("pytest")
        assert retired.retire("pytest") is retired

        observation = NetworkConfigObservation.create(
            tenant_id=baseline.tenant_id,
            idempotency_key="collector-edges-0001",
            source="ssh",
            collector="collector-edge",
            device_object_key=baseline.device_object_key,
            platform=baseline.platform,
            observed_config=baseline.expected_config,
            observed_at=datetime.now(UTC),
        )
        observation_values = {
            "id": EntityId.new(),
            "tenant_id": baseline.tenant_id,
            "idempotency_key": observation.idempotency_key,
            "source": observation.source.value,
            "collector": observation.collector,
            "device_object_key": observation.device_object_key,
            "platform": observation.platform,
            "observed_config": observation.observed_config,
            "observed_at": observation.observed_at,
            "received_at": observation.received_at,
            "fingerprint": None,
        }
        for override, message in (
            ({"idempotency_key": "short"}, "idempotency"),
            ({"collector": "x"}, "collector"),
            ({"platform": "x"}, "platform"),
            ({"observed_at": datetime.now()}, "timezone-aware"),
            ({"fingerprint": "0" * 64}, "fingerprint"),
        ):
            with pytest.raises(ValidationError, match=message):
                NetworkConfigObservation.restore(**(observation_values | override))

    def test_report_covers_type_list_device_and_serialization_edges(self) -> None:
        baseline = NetworkConfigBaseline.create(
            tenant_id=TenantId.from_value("default"),
            code="EDGE-GOLDEN",
            device_object_key="network-device/edge-01",
            platform="ios-xe",
            expected_config={"typed": {"a": 1}, "items": [1, 2], "scalar": 1},
            ignored_paths=(),
            critical_paths=("/items",),
            owner="Network Team",
            justification="Approved edge validation configuration",
            actor="pytest",
        )
        observed = NetworkConfigObservation.create(
            tenant_id=baseline.tenant_id,
            idempotency_key="collector-edges-0002",
            source="api",
            collector="collector-edge",
            device_object_key=baseline.device_object_key,
            platform=baseline.platform,
            observed_config={"typed": [], "items": [1, 2, 3], "scalar": "1"},
            observed_at=datetime.now(UTC),
        )
        report = NetworkConfigComplianceReport.evaluate(baseline, observed)
        assert {item.kind.value for item in report.drifts} == {"type-mismatch", "unexpected"}
        assert report.as_dict()["summary"]["total"] == 3

        missing = NetworkConfigObservation.create(
            tenant_id=baseline.tenant_id,
            idempotency_key="collector-edges-0003",
            source="api",
            collector="collector-edge",
            device_object_key=baseline.device_object_key,
            platform=baseline.platform,
            observed_config={"typed": {"a": 1}, "items": [1], "scalar": 1},
            observed_at=datetime.now(UTC),
        )
        assert any(
            item.kind.value == "missing"
            for item in NetworkConfigComplianceReport.evaluate(baseline, missing).drifts
        )
        other_device = NetworkConfigObservation.create(
            tenant_id=baseline.tenant_id,
            idempotency_key="collector-edges-0004",
            source="api",
            collector="collector-edge",
            device_object_key="network-device/other",
            platform=baseline.platform,
            observed_config=baseline.expected_config,
            observed_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError, match="different device"):
            NetworkConfigComplianceReport.evaluate(baseline, other_device)
