from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.flow_matrix import (
    FlowComplianceStatus,
    FlowDeclaration,
    FlowObservation,
    FlowObservationSource,
    FlowPortRange,
    FlowProtocol,
    FlowSelector,
    FlowSelectorKind,
)

NOW = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def declaration(**overrides: object) -> FlowDeclaration:
    values: dict[str, object] = {
        "tenant_id": TenantId.from_value("default"),
        "code": "APP-WEB-HTTPS",
        "source_selector": "object:application/portal",
        "destination_selector": "cidr:10.20.30.0/24",
        "protocol": "tcp",
        "destination_port_start": 443,
        "destination_port_end": 443,
        "decision": "allow",
        "priority": 100,
        "owner": "network team",
        "justification": "approved application flow",
        "actor": "pytest",
        "valid_from": NOW - timedelta(days=1),
        "valid_to": NOW + timedelta(days=1),
    }
    values.update(overrides)
    return FlowDeclaration.create(**values)  # type: ignore[arg-type]


def observation(**overrides: object) -> FlowObservation:
    values: dict[str, object] = {
        "tenant_id": TenantId.from_value("default"),
        "idempotency_key": "collector-01:000001",
        "source": "netflow",
        "collector": "collector-01",
        "source_ip": "10.10.1.10",
        "destination_ip": "10.20.30.40",
        "source_object_key": "application/portal",
        "destination_object_key": "server/web-01",
        "protocol": "tcp",
        "destination_port": 443,
        "packets": 42,
        "bytes_count": 8192,
        "first_seen": NOW - timedelta(minutes=5),
        "last_seen": NOW,
    }
    values.update(overrides)
    return FlowObservation.create(**values)  # type: ignore[arg-type]


class TestFlowSelector:
    def test_normalizes_any_object_and_cidr_selectors(self) -> None:
        any_selector = FlowSelector.from_value("*")
        object_selector = FlowSelector.from_value("object:application/portal")
        cidr_selector = FlowSelector.from_value("cidr:10.20.30.17/24")

        assert any_selector == FlowSelector(FlowSelectorKind.ANY, "*")
        assert str(object_selector) == "object:application/portal"
        assert str(cidr_selector) == "cidr:10.20.30.0/24"
        assert object_selector.specificity > cidr_selector.specificity > any_selector.specificity
        assert object_selector.matches("192.0.2.1", "application/portal")
        assert not object_selector.matches("192.0.2.1", "application/other")
        assert cidr_selector.matches("10.20.30.254", None)
        assert not cidr_selector.matches("10.20.31.1", None)
        assert cidr_selector.as_dict()["selector"] == "cidr:10.20.30.0/24"

    @pytest.mark.parametrize("value", ["", "object:", "cidr:not-a-network", "host:server/a"])
    def test_rejects_invalid_selectors(self, value: str) -> None:
        with pytest.raises(ValidationError):
            FlowSelector.from_value(value)


class TestFlowPortsAndProtocols:
    def test_protocol_aliases_and_port_ranges(self) -> None:
        assert FlowProtocol.from_value("ICMP-v6") is FlowProtocol.ICMPV6
        assert FlowProtocol.from_value("*") is FlowProtocol.ANY
        port_range = FlowPortRange.from_values(FlowProtocol.TCP, 443, None)
        assert port_range is not None
        assert port_range.contains(443)
        assert not port_range.contains(444)
        assert port_range.width == 0
        assert port_range.as_dict() == {"start": 443, "end": 443}

    @pytest.mark.parametrize(
        ("protocol", "start", "end"),
        [
            (FlowProtocol.TCP, None, None),
            (FlowProtocol.UDP, 0, 53),
            (FlowProtocol.SCTP, 5000, 4999),
            (FlowProtocol.ICMP, 8, 8),
        ],
    )
    def test_rejects_invalid_port_contracts(
        self, protocol: FlowProtocol, start: int | None, end: int | None
    ) -> None:
        with pytest.raises(ValidationError):
            FlowPortRange.from_values(protocol, start, end)


class TestFlowDeclarationAndObservation:
    def test_matches_object_cidr_protocol_and_port_and_serializes(self) -> None:
        item = declaration()
        observed = observation()

        assert item.matches(observed)
        assert item.is_effective_at(NOW)
        assert item.match_score[0] == 100
        assert item.as_dict()["destination_port_start"] == 443
        assert observed.as_dict()["bytes"] == 8192
        assert len(observed.fingerprint) == 64

        assert not item.matches(observation(source_object_key="application/other"))
        assert not item.matches(observation(destination_ip="10.20.31.1"))
        assert not item.matches(observation(protocol="udp", destination_port=443))
        assert not item.matches(observation(destination_port=8443))

    def test_revision_retirement_and_restore_are_compatible(self) -> None:
        original = declaration()
        revised = original.revise(
            source_selector="cidr:10.10.0.0/16",
            destination_selector="cidr:10.20.0.0/16",
            protocol="tcp",
            destination_port_start=443,
            destination_port_end=8443,
            decision="deny",
            priority=200,
            owner="security team",
            justification="temporary containment policy",
            actor="operator",
            valid_from=NOW,
            valid_to=NOW + timedelta(days=2),
        )
        retired = revised.retire("operator")
        restored = FlowDeclaration.restore(
            id=EntityId.from_value(retired.id.value),
            tenant_id=TenantId.from_value("default"),
            code=str(retired.as_dict()["code"]),
            source_selector=str(retired.as_dict()["source_selector"]),
            destination_selector=str(retired.as_dict()["destination_selector"]),
            protocol=str(retired.as_dict()["protocol"]),
            destination_port_start=443,
            destination_port_end=8443,
            decision=str(retired.as_dict()["decision"]),
            priority=int(retired.as_dict()["priority"]),
            owner=str(retired.as_dict()["owner"]),
            justification=str(retired.as_dict()["justification"]),
            valid_from=datetime.fromisoformat(str(retired.as_dict()["valid_from"])),
            valid_to=datetime.fromisoformat(str(retired.as_dict()["valid_to"])),
            status=str(retired.as_dict()["status"]),
            version=int(retired.as_dict()["version"]),
            created_by=str(retired.as_dict()["created_by"]),
            created_at=datetime.fromisoformat(str(retired.as_dict()["created_at"])),
            updated_by=str(retired.as_dict()["updated_by"]),
            updated_at=datetime.fromisoformat(str(retired.as_dict()["updated_at"])),
        )

        assert revised.version == original.version + 1
        assert revised.decision.value == "deny"
        assert retired.status.value == "retired"
        assert not retired.is_effective_at(NOW)
        assert retired.retire("operator") is retired
        assert restored.as_dict() == retired.as_dict()

    def test_observation_fingerprint_detects_tampering(self) -> None:
        item = observation()
        payload = item.as_dict()
        restored = FlowObservation.restore(
            id=EntityId.from_value(str(payload["id"])),
            tenant_id=TenantId.from_value(str(payload["tenant_id"])),
            idempotency_key=str(payload["idempotency_key"]),
            source=str(payload["source"]),
            collector=str(payload["collector"]),
            source_ip=str(payload["source_ip"]),
            destination_ip=str(payload["destination_ip"]),
            source_object_key=str(payload["source_object_key"]),
            destination_object_key=str(payload["destination_object_key"]),
            protocol=str(payload["protocol"]),
            destination_port=int(payload["destination_port"]),
            packets=int(payload["packets"]),
            bytes_count=int(payload["bytes"]),
            first_seen=datetime.fromisoformat(str(payload["first_seen"])),
            last_seen=datetime.fromisoformat(str(payload["last_seen"])),
            received_at=datetime.fromisoformat(str(payload["received_at"])),
            fingerprint=str(payload["fingerprint"]),
        )
        assert restored == item

        with pytest.raises(ValidationError, match="fingerprint"):
            FlowObservation.restore(
                id=item.id,
                tenant_id=item.tenant_id,
                idempotency_key=item.idempotency_key,
                source=item.source.value,
                collector=item.collector,
                source_ip=item.source_ip,
                destination_ip=item.destination_ip,
                source_object_key=item.source_object_key,
                destination_object_key=item.destination_object_key,
                protocol=item.protocol.value,
                destination_port=item.destination_port,
                packets=item.packets + 1,
                bytes_count=item.bytes_count,
                first_seen=item.first_seen,
                last_seen=item.last_seen,
                received_at=item.received_at,
                fingerprint=item.fingerprint,
            )

    @pytest.mark.parametrize(
        "override",
        [
            {"code": "x"},
            {"priority": 1001},
            {"owner": "x"},
            {"justification": "bad"},
            {"valid_from": NOW, "valid_to": NOW},
            {"actor": ""},
        ],
    )
    def test_declaration_validation(self, override: dict[str, object]) -> None:
        with pytest.raises((ValidationError, ValueError)):
            declaration(**override)

    @pytest.mark.parametrize(
        "override",
        [
            {"idempotency_key": "short"},
            {"collector": "X"},
            {"source_ip": "invalid"},
            {"protocol": "tcp", "destination_port": None},
            {"protocol": "icmp", "destination_port": 8},
            {"packets": 0},
            {"bytes_count": -1},
            {"first_seen": NOW, "last_seen": NOW - timedelta(seconds=1)},
        ],
    )
    def test_observation_validation(self, override: dict[str, object]) -> None:
        with pytest.raises(ValidationError):
            observation(**override)


def test_compliance_status_values_are_stable() -> None:
    assert [item.value for item in FlowComplianceStatus] == [
        "compliant",
        "denied-observed",
        "undeclared-observed",
        "declared-unobserved",
    ]


def test_rare_validation_and_non_matching_branches_are_explicit() -> None:
    with pytest.raises(ValidationError, match="protocol"):
        FlowProtocol.from_value("unsupported")
    with pytest.raises(ValidationError, match="source"):
        FlowObservationSource.from_value("unsupported")

    assert not FlowSelector.from_value("cidr:10.0.0.0/8").matches("not-an-ip", None)
    assert FlowPortRange.from_values(FlowProtocol.ICMP, None, None) is None
    assert not declaration(valid_to=NOW - timedelta(minutes=1)).matches(observation())

    with pytest.raises(ValidationError, match="timezone-aware"):
        declaration(valid_from=datetime(2026, 7, 10, 12, 0))

    item = declaration()
    common: dict[str, object] = {
        "id": item.id,
        "tenant_id": item.tenant_id,
        "code": item.code,
        "source_selector": str(item.source_selector),
        "destination_selector": str(item.destination_selector),
        "protocol": item.protocol.value,
        "destination_port_start": item.destination_ports.start if item.destination_ports else None,
        "destination_port_end": item.destination_ports.end if item.destination_ports else None,
        "decision": item.decision.value,
        "priority": item.priority,
        "owner": item.owner,
        "justification": item.justification,
        "valid_from": item.valid_from,
        "valid_to": item.valid_to,
        "status": item.status.value,
        "created_by": item.created_by,
        "created_at": item.created_at,
        "updated_by": item.updated_by,
    }
    with pytest.raises(ValidationError, match="updated_at"):
        FlowDeclaration.restore(
            **common, version=1, updated_at=item.created_at - timedelta(seconds=1)
        )  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="version"):
        FlowDeclaration.restore(**common, version=0, updated_at=item.updated_at)  # type: ignore[arg-type]
