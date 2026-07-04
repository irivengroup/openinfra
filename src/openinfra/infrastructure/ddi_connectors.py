from __future__ import annotations

import ipaddress

from openinfra.application.ports import DdiConnector, DdiPreviewContext
from openinfra.domain.ipam import DdiChange, DdiProvider, DdiRecordKind, IpReservation


class BindDdiConnector(DdiConnector):
    @property
    def provider(self) -> DdiProvider:
        return DdiProvider.BIND

    def build_preview_changes(
        self, reservation: IpReservation, context: DdiPreviewContext
    ) -> tuple[DdiChange, ...]:
        record_type = "AAAA" if reservation.address.version == 6 else "A"
        return (
            DdiChange.create(
                self.provider,
                "upsert",
                DdiRecordKind.DNS_FORWARD,
                context.fqdn,
                str(reservation.address),
                context.ttl,
                {
                    "record_type": record_type,
                    "zone": context.dns_zone or self._parent_zone(context.fqdn),
                    "renderer": "bind-nsupdate",
                },
            ),
            DdiChange.create(
                self.provider,
                "upsert",
                DdiRecordKind.DNS_REVERSE,
                reservation.address.reverse_pointer,
                f"{context.fqdn}.",
                context.ttl,
                {"record_type": "PTR", "renderer": "bind-nsupdate"},
            ),
        )

    def _parent_zone(self, fqdn: str) -> str:
        pieces = fqdn.rstrip(".").split(".")
        return ".".join(pieces[1:]) if len(pieces) > 1 else fqdn


class PowerDnsDdiConnector(DdiConnector):
    @property
    def provider(self) -> DdiProvider:
        return DdiProvider.POWERDNS

    def build_preview_changes(
        self, reservation: IpReservation, context: DdiPreviewContext
    ) -> tuple[DdiChange, ...]:
        record_type = "AAAA" if reservation.address.version == 6 else "A"
        return (
            DdiChange.create(
                self.provider,
                "upsert",
                DdiRecordKind.DNS_FORWARD,
                context.fqdn,
                str(reservation.address),
                context.ttl,
                {
                    "record_type": record_type,
                    "zone": context.dns_zone or self._parent_zone(context.fqdn),
                    "api_method": "PATCH /api/v1/servers/localhost/zones/{zone}",
                },
            ),
            DdiChange.create(
                self.provider,
                "upsert",
                DdiRecordKind.DNS_REVERSE,
                reservation.address.reverse_pointer,
                f"{context.fqdn}.",
                context.ttl,
                {
                    "record_type": "PTR",
                    "api_method": "PATCH /api/v1/servers/localhost/zones/{reverse_zone}",
                },
            ),
        )

    def _parent_zone(self, fqdn: str) -> str:
        pieces = fqdn.rstrip(".").split(".")
        return ".".join(pieces[1:]) if len(pieces) > 1 else fqdn


class KeaDdiConnector(DdiConnector):
    @property
    def provider(self) -> DdiProvider:
        return DdiProvider.KEA

    def build_preview_changes(
        self, reservation: IpReservation, context: DdiPreviewContext
    ) -> tuple[DdiChange, ...]:
        if not context.mac_address:
            return ()
        subnet_id = self._deterministic_subnet_id(reservation.prefix)
        return (
            DdiChange.create(
                self.provider,
                "upsert",
                DdiRecordKind.DHCP_RESERVATION,
                f"kea:{subnet_id}:{context.mac_address}",
                str(reservation.address),
                0,
                {
                    "hostname": context.fqdn,
                    "hw_address": context.mac_address,
                    "prefix": reservation.prefix,
                    "subnet_id": str(subnet_id),
                    "control_agent_command": "reservation-add",
                },
            ),
        )

    def _deterministic_subnet_id(self, prefix: str) -> int:
        network = ipaddress.ip_network(prefix, strict=True)
        return int(network.network_address) % 2_147_483_647 or 1


class DdiConnectorFactory:
    @staticmethod
    def default() -> tuple[DdiConnector, ...]:
        return (BindDdiConnector(), PowerDnsDdiConnector(), KeaDdiConnector())
