from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from openinfra.domain.common import EntityId, TenantId, ValidationError
from openinfra.domain.source_of_truth import SourceObjectKey


class FlowProtocol(StrEnum):
    ANY = "any"
    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"
    ICMP = "icmp"
    ICMPV6 = "icmpv6"
    ESP = "esp"
    AH = "ah"
    GRE = "gre"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("-", "")
        aliases = {"*": "any", "icmp6": "icmpv6", "ipv6icmp": "icmpv6"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("flow protocol is unsupported") from exc

    @property
    def supports_ports(self) -> bool:
        return self in {FlowProtocol.TCP, FlowProtocol.UDP, FlowProtocol.SCTP}


class FlowDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class FlowDeclarationStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class FlowObservationSource(StrEnum):
    NETFLOW = "netflow"
    SFLOW = "sflow"
    IPFIX = "ipfix"
    FIREWALL_LOG = "firewall-log"
    APPLICATION_LOG = "application-log"
    IMPORT = "import"
    MANUAL = "manual"

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip().lower().replace("_", "-")
        aliases = {"firewall": "firewall-log", "application": "application-log"}
        try:
            return cls(aliases.get(normalized, normalized))
        except ValueError as exc:
            raise ValidationError("flow observation source is unsupported") from exc


class FlowSelectorKind(StrEnum):
    ANY = "any"
    OBJECT = "object"
    CIDR = "cidr"


class FlowComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    DENIED_OBSERVED = "denied-observed"
    UNDECLARED_OBSERVED = "undeclared-observed"
    DECLARED_UNOBSERVED = "declared-unobserved"


@dataclass(frozen=True, slots=True)
class FlowSelector:
    kind: FlowSelectorKind
    value: str

    @classmethod
    def from_value(cls, value: str) -> Self:
        normalized = value.strip()
        if normalized.lower() in {"*", "any"}:
            return cls(FlowSelectorKind.ANY, "*")
        prefix, separator, raw_value = normalized.partition(":")
        if separator == "" or raw_value.strip() == "":
            raise ValidationError("flow selector must use any, object:<key> or cidr:<network>")
        kind = prefix.strip().lower()
        if kind == FlowSelectorKind.OBJECT.value:
            return cls(FlowSelectorKind.OBJECT, SourceObjectKey.from_value(raw_value).value)
        if kind == FlowSelectorKind.CIDR.value:
            try:
                network = ipaddress.ip_network(raw_value.strip(), strict=False)
            except ValueError as exc:
                raise ValidationError("flow selector CIDR is invalid") from exc
            return cls(FlowSelectorKind.CIDR, str(network))
        raise ValidationError("flow selector must use any, object:<key> or cidr:<network>")

    def matches(self, ip_value: str, object_key: str | None) -> bool:
        if self.kind is FlowSelectorKind.ANY:
            return True
        if self.kind is FlowSelectorKind.OBJECT:
            return (
                object_key is not None
                and SourceObjectKey.from_value(object_key).value == self.value
            )
        try:
            return ipaddress.ip_address(ip_value) in ipaddress.ip_network(self.value, strict=True)
        except ValueError:
            return False

    @property
    def specificity(self) -> int:
        if self.kind is FlowSelectorKind.OBJECT:
            return 10_000
        if self.kind is FlowSelectorKind.CIDR:
            return 100 + ipaddress.ip_network(self.value, strict=True).prefixlen
        return 0

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "value": self.value, "selector": str(self)}

    def __str__(self) -> str:
        if self.kind is FlowSelectorKind.ANY:
            return "any"
        return f"{self.kind.value}:{self.value}"


@dataclass(frozen=True, slots=True)
class FlowPortRange:
    start: int
    end: int

    @classmethod
    def from_values(
        cls,
        protocol: FlowProtocol,
        start: int | None,
        end: int | None,
    ) -> Self | None:
        if not protocol.supports_ports:
            if start is not None or end is not None:
                raise ValidationError("ports are only valid for TCP, UDP or SCTP flows")
            return None
        if start is None:
            raise ValidationError("destination port is mandatory for TCP, UDP or SCTP flows")
        normalized_end = start if end is None else end
        if not 1 <= int(start) <= 65_535 or not 1 <= int(normalized_end) <= 65_535:
            raise ValidationError("flow ports must be between 1 and 65535")
        if int(normalized_end) < int(start):
            raise ValidationError("flow destination port end cannot be before start")
        return cls(int(start), int(normalized_end))

    def contains(self, port: int | None) -> bool:
        return port is not None and self.start <= port <= self.end

    @property
    def width(self) -> int:
        return self.end - self.start

    def as_dict(self) -> dict[str, int]:
        return {"start": self.start, "end": self.end}


@dataclass(frozen=True, slots=True)
class FlowDeclaration:
    id: EntityId
    tenant_id: TenantId
    code: str
    source_selector: FlowSelector
    destination_selector: FlowSelector
    protocol: FlowProtocol
    destination_ports: FlowPortRange | None
    decision: FlowDecision
    priority: int
    owner: str
    justification: str
    valid_from: datetime
    valid_to: datetime | None
    status: FlowDeclarationStatus
    version: int
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        code: str,
        source_selector: str,
        destination_selector: str,
        protocol: str,
        destination_port_start: int | None,
        destination_port_end: int | None,
        decision: str,
        priority: int,
        owner: str,
        justification: str,
        actor: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> Self:
        now = datetime.now(UTC)
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            code=code,
            source_selector=source_selector,
            destination_selector=destination_selector,
            protocol=protocol,
            destination_port_start=destination_port_start,
            destination_port_end=destination_port_end,
            decision=decision,
            priority=priority,
            owner=owner,
            justification=justification,
            valid_from=valid_from or now,
            valid_to=valid_to,
            status=FlowDeclarationStatus.ACTIVE.value,
            version=1,
            created_by=actor,
            created_at=now,
            updated_by=actor,
            updated_at=now,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        code: str,
        source_selector: str,
        destination_selector: str,
        protocol: str,
        destination_port_start: int | None,
        destination_port_end: int | None,
        decision: str,
        priority: int,
        owner: str,
        justification: str,
        valid_from: datetime,
        valid_to: datetime | None,
        status: str,
        version: int,
        created_by: str,
        created_at: datetime,
        updated_by: str,
        updated_at: datetime,
    ) -> Self:
        normalized_code = code.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{2,63}", normalized_code):
            raise ValidationError(
                "flow declaration code must use 3 to 64 safe uppercase characters"
            )
        normalized_protocol = FlowProtocol.from_value(protocol)
        normalized_priority = int(priority)
        if not 0 <= normalized_priority <= 1000:
            raise ValidationError("flow declaration priority must be between 0 and 1000")
        normalized_owner = " ".join(owner.strip().split())
        if not 2 <= len(normalized_owner) <= 128:
            raise ValidationError("flow declaration owner must contain 2 to 128 characters")
        normalized_justification = " ".join(justification.strip().split())
        if not 5 <= len(normalized_justification) <= 1000:
            raise ValidationError(
                "flow declaration justification must contain 5 to 1000 characters"
            )
        normalized_actor = cls._actor(updated_by)
        normalized_created_by = cls._actor(created_by)
        normalized_valid_from = cls._datetime(valid_from, "valid_from")
        normalized_valid_to = cls._optional_datetime(valid_to, "valid_to")
        if normalized_valid_to is not None and normalized_valid_to <= normalized_valid_from:
            raise ValidationError("flow declaration valid_to must be after valid_from")
        normalized_created_at = cls._datetime(created_at, "created_at")
        normalized_updated_at = cls._datetime(updated_at, "updated_at")
        if normalized_updated_at < normalized_created_at:
            raise ValidationError("flow declaration updated_at cannot be before created_at")
        normalized_version = int(version)
        if normalized_version < 1:
            raise ValidationError("flow declaration version must be positive")
        return cls(
            id=id,
            tenant_id=tenant_id,
            code=normalized_code,
            source_selector=FlowSelector.from_value(source_selector),
            destination_selector=FlowSelector.from_value(destination_selector),
            protocol=normalized_protocol,
            destination_ports=FlowPortRange.from_values(
                normalized_protocol, destination_port_start, destination_port_end
            ),
            decision=FlowDecision(decision.strip().lower()),
            priority=normalized_priority,
            owner=normalized_owner,
            justification=normalized_justification,
            valid_from=normalized_valid_from,
            valid_to=normalized_valid_to,
            status=FlowDeclarationStatus(status.strip().lower()),
            version=normalized_version,
            created_by=normalized_created_by,
            created_at=normalized_created_at,
            updated_by=normalized_actor,
            updated_at=normalized_updated_at,
        )

    def revise(
        self,
        *,
        source_selector: str,
        destination_selector: str,
        protocol: str,
        destination_port_start: int | None,
        destination_port_end: int | None,
        decision: str,
        priority: int,
        owner: str,
        justification: str,
        actor: str,
        valid_from: datetime,
        valid_to: datetime | None,
    ) -> Self:
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            code=self.code,
            source_selector=source_selector,
            destination_selector=destination_selector,
            protocol=protocol,
            destination_port_start=destination_port_start,
            destination_port_end=destination_port_end,
            decision=decision,
            priority=priority,
            owner=owner,
            justification=justification,
            valid_from=valid_from,
            valid_to=valid_to,
            status=FlowDeclarationStatus.ACTIVE.value,
            version=self.version + 1,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def retire(self, actor: str) -> Self:
        if self.status is FlowDeclarationStatus.RETIRED:
            return self
        return self.restore(
            id=self.id,
            tenant_id=self.tenant_id,
            code=self.code,
            source_selector=str(self.source_selector),
            destination_selector=str(self.destination_selector),
            protocol=self.protocol.value,
            destination_port_start=(
                None if self.destination_ports is None else self.destination_ports.start
            ),
            destination_port_end=(
                None if self.destination_ports is None else self.destination_ports.end
            ),
            decision=self.decision.value,
            priority=self.priority,
            owner=self.owner,
            justification=self.justification,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            status=FlowDeclarationStatus.RETIRED.value,
            version=self.version + 1,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_by=actor,
            updated_at=datetime.now(UTC),
        )

    def is_effective_at(self, observed_at: datetime) -> bool:
        return (
            self.status is FlowDeclarationStatus.ACTIVE
            and self.valid_from <= observed_at
            and (self.valid_to is None or observed_at < self.valid_to)
        )

    def matches(self, observation: FlowObservation) -> bool:
        if not self.is_effective_at(observation.last_seen):
            return False
        if not self.source_selector.matches(observation.source_ip, observation.source_object_key):
            return False
        if not self.destination_selector.matches(
            observation.destination_ip, observation.destination_object_key
        ):
            return False
        if self.protocol is not FlowProtocol.ANY and self.protocol is not observation.protocol:
            return False
        return self.destination_ports is None or self.destination_ports.contains(
            observation.destination_port
        )

    @property
    def match_score(self) -> tuple[int, int, int, int, str]:
        protocol_score = 1 if self.protocol is not FlowProtocol.ANY else 0
        port_score = 65_535 - self.destination_ports.width if self.destination_ports else 0
        return (
            self.priority,
            self.source_selector.specificity + self.destination_selector.specificity,
            protocol_score,
            port_score,
            self.code,
        )

    @staticmethod
    def _actor(value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not 1 <= len(normalized) <= 128:
            raise ValidationError("flow declaration actor must contain 1 to 128 characters")
        return normalized

    @staticmethod
    def _datetime(value: datetime, field_name: str) -> datetime:
        if value.tzinfo is None:
            raise ValidationError(field_name + " must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def _optional_datetime(cls, value: datetime | None, field_name: str) -> datetime | None:
        return None if value is None else cls._datetime(value, field_name)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "code": self.code,
            "source_selector": str(self.source_selector),
            "destination_selector": str(self.destination_selector),
            "protocol": self.protocol.value,
            "destination_port_start": (
                None if self.destination_ports is None else self.destination_ports.start
            ),
            "destination_port_end": (
                None if self.destination_ports is None else self.destination_ports.end
            ),
            "decision": self.decision.value,
            "priority": self.priority,
            "owner": self.owner,
            "justification": self.justification,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to is not None else None,
            "status": self.status.value,
            "version": self.version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class FlowObservation:
    id: EntityId
    tenant_id: TenantId
    idempotency_key: str
    source: FlowObservationSource
    collector: str
    source_ip: str
    destination_ip: str
    source_object_key: str | None
    destination_object_key: str | None
    protocol: FlowProtocol
    destination_port: int | None
    packets: int
    bytes_count: int
    first_seen: datetime
    last_seen: datetime
    received_at: datetime
    fingerprint: str

    @classmethod
    def create(
        cls,
        tenant_id: TenantId,
        idempotency_key: str,
        source: str,
        collector: str,
        source_ip: str,
        destination_ip: str,
        source_object_key: str | None,
        destination_object_key: str | None,
        protocol: str,
        destination_port: int | None,
        packets: int,
        bytes_count: int,
        first_seen: datetime,
        last_seen: datetime,
    ) -> Self:
        return cls.restore(
            id=EntityId.new(),
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            source=source,
            collector=collector,
            source_ip=source_ip,
            destination_ip=destination_ip,
            source_object_key=source_object_key,
            destination_object_key=destination_object_key,
            protocol=protocol,
            destination_port=destination_port,
            packets=packets,
            bytes_count=bytes_count,
            first_seen=first_seen,
            last_seen=last_seen,
            received_at=datetime.now(UTC),
        )

    @classmethod
    def restore(
        cls,
        *,
        id: EntityId,
        tenant_id: TenantId,
        idempotency_key: str,
        source: str,
        collector: str,
        source_ip: str,
        destination_ip: str,
        source_object_key: str | None,
        destination_object_key: str | None,
        protocol: str,
        destination_port: int | None,
        packets: int,
        bytes_count: int,
        first_seen: datetime,
        last_seen: datetime,
        received_at: datetime,
        fingerprint: str | None = None,
    ) -> Self:
        normalized_key = idempotency_key.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{7,127}", normalized_key):
            raise ValidationError(
                "flow observation idempotency key must use 8 to 128 safe characters"
            )
        normalized_collector = collector.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{1,127}", normalized_collector):
            raise ValidationError("flow observation collector must use 2 to 128 safe characters")
        normalized_source_ip = cls._ip(source_ip, "source_ip")
        normalized_destination_ip = cls._ip(destination_ip, "destination_ip")
        normalized_source_object = cls._object_key(source_object_key)
        normalized_destination_object = cls._object_key(destination_object_key)
        normalized_protocol = FlowProtocol.from_value(protocol)
        normalized_port = None if destination_port is None else int(destination_port)
        if normalized_protocol.supports_ports:
            if normalized_port is None or not 1 <= normalized_port <= 65_535:
                raise ValidationError(
                    "observed TCP, UDP or SCTP flow requires a valid destination port"
                )
        elif normalized_port is not None:
            raise ValidationError("observed non-port protocol cannot define a destination port")
        normalized_packets = int(packets)
        normalized_bytes = int(bytes_count)
        if normalized_packets < 1:
            raise ValidationError("flow observation packets must be positive")
        if normalized_bytes < 0:
            raise ValidationError("flow observation bytes cannot be negative")
        normalized_first = FlowDeclaration._datetime(first_seen, "first_seen")
        normalized_last = FlowDeclaration._datetime(last_seen, "last_seen")
        normalized_received = FlowDeclaration._datetime(received_at, "received_at")
        if normalized_last < normalized_first:
            raise ValidationError("flow observation last_seen cannot be before first_seen")
        computed_fingerprint = cls._fingerprint(
            tenant_id.value,
            normalized_key,
            FlowObservationSource.from_value(source).value,
            normalized_collector,
            normalized_source_ip,
            normalized_destination_ip,
            normalized_source_object,
            normalized_destination_object,
            normalized_protocol.value,
            normalized_port,
            normalized_packets,
            normalized_bytes,
            normalized_first,
            normalized_last,
        )
        if fingerprint is not None and fingerprint.strip().lower() != computed_fingerprint:
            raise ValidationError("flow observation fingerprint does not match payload")
        return cls(
            id=id,
            tenant_id=tenant_id,
            idempotency_key=normalized_key,
            source=FlowObservationSource.from_value(source),
            collector=normalized_collector,
            source_ip=normalized_source_ip,
            destination_ip=normalized_destination_ip,
            source_object_key=normalized_source_object,
            destination_object_key=normalized_destination_object,
            protocol=normalized_protocol,
            destination_port=normalized_port,
            packets=normalized_packets,
            bytes_count=normalized_bytes,
            first_seen=normalized_first,
            last_seen=normalized_last,
            received_at=normalized_received,
            fingerprint=computed_fingerprint,
        )

    @staticmethod
    def _ip(value: str, field_name: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ValidationError(field_name + " must be a valid IPv4 or IPv6 address") from exc

    @staticmethod
    def _object_key(value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        return SourceObjectKey.from_value(value).value

    @staticmethod
    def _fingerprint(*values: object) -> str:
        normalized = [
            value.isoformat() if isinstance(value, datetime) else value for value in values
        ]
        payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "tenant_id": self.tenant_id.value,
            "idempotency_key": self.idempotency_key,
            "source": self.source.value,
            "collector": self.collector,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "source_object_key": self.source_object_key,
            "destination_object_key": self.destination_object_key,
            "protocol": self.protocol.value,
            "destination_port": self.destination_port,
            "packets": self.packets,
            "bytes": self.bytes_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "received_at": self.received_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class FlowMatrixRow:
    status: FlowComplianceStatus
    observation: FlowObservation | None
    declaration: FlowDeclaration | None
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "declaration": None if self.declaration is None else self.declaration.as_dict(),
            "observation": None if self.observation is None else self.observation.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class FlowMatrixReport:
    window_start: datetime
    window_end: datetime
    rows: tuple[FlowMatrixRow, ...]
    totals: dict[str, int]
    packets: int
    bytes_count: int
    observation_count: int
    declaration_count: int
    next_cursor: str | None
    truncated: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "totals": dict(sorted(self.totals.items())),
            "packets": self.packets,
            "bytes": self.bytes_count,
            "observation_count": self.observation_count,
            "declaration_count": self.declaration_count,
            "row_count": len(self.rows),
            "next_cursor": self.next_cursor,
            "truncated": self.truncated,
            "rows": [row.as_dict() for row in self.rows],
        }
