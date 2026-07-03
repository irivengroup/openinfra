from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from openinfra.domain.access_policy import AccessPolicyRule
from openinfra.domain.audit import AuditEventFilter, AuditEventPage, AuditIntegrityReport
from openinfra.domain.common import AuditEvent, Pagination, TenantId
from openinfra.domain.dcim import Building, Equipment, Rack, Room, Site
from openinfra.domain.identity import (
    EffectiveIdentity,
    GroupMembership,
    IdentityGroup,
    IdentityUser,
)
from openinfra.domain.ipam import IpReservation, Prefix, Vrf
from openinfra.domain.security import ApiTokenCredential, Permission

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class AccessPolicyRulePage:
    items: tuple[AccessPolicyRule, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class SecurityTokenPage:
    items: tuple[ApiTokenCredential, ...]
    next_cursor: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "items": [item.as_public_dict() for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class ReadinessStatus:
    component: str
    ready: bool
    detail: str

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "component": self.component,
            "ready": self.ready,
            "detail": self.detail,
        }


class ReadinessProbe(ABC):
    @abstractmethod
    def check(self) -> ReadinessStatus:
        raise TypeError("adapter contract invoked directly")


class SchemaStatusProvider(ABC):
    @abstractmethod
    def status_as_dict(self) -> dict[str, object]:
        raise TypeError("adapter contract invoked directly")


class UnitOfWork(ABC):
    @abstractmethod
    def __enter__(self) -> UnitOfWork:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def commit(self) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def rollback(self) -> None:
        raise TypeError("adapter contract invoked directly")


class Repository(Generic[T], ABC):
    @abstractmethod
    def add(self, entity: T) -> None:
        raise TypeError("adapter contract invoked directly")


class DcimRepository(ABC):
    @abstractmethod
    def add_site(self, site: Site) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_building(self, building: Building) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_room(self, room: Room) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_rack(self, rack: Rack) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_equipment(self, equipment: Equipment) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_room(self, tenant_id: TenantId, site: str, building: str, room: str) -> Room | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_rack(
        self,
        tenant_id: TenantId,
        site: str,
        building: str,
        room: str,
        rack: str,
    ) -> Rack | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_equipment(self, tenant_id: TenantId, asset_tag: str) -> Equipment | None:
        raise TypeError("adapter contract invoked directly")


class IpamRepository(ABC):
    @abstractmethod
    def add_vrf(self, vrf: Vrf) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def get_or_create_prefix(self, prefix: Prefix) -> Prefix:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_reservation_by_key(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        idempotency_key: str,
    ) -> IpReservation | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_reservations(
        self,
        tenant_id: TenantId,
        vrf_name: str,
        prefix_cidr: str,
    ) -> tuple[IpReservation, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_reservation(self, reservation: IpReservation) -> None:
        raise TypeError("adapter contract invoked directly")



class IdentityRepository(ABC):
    @abstractmethod
    def upsert_user(self, user: IdentityUser) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def upsert_group(self, group: IdentityGroup) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def add_membership(self, membership: GroupMembership) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def grant_user_role(self, tenant_id: TenantId, username: str, role: str) -> bool:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def grant_group_role(self, tenant_id: TenantId, group_name: str, role: str) -> bool:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def effective_identity_for_subject(
        self,
        tenant_id: TenantId,
        subject: str,
    ) -> EffectiveIdentity:
        raise TypeError("adapter contract invoked directly")

class SecurityRepository(ABC):
    @abstractmethod
    def upsert_token(self, credential: ApiTokenCredential) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_active_token_by_hash(
        self,
        tenant_id: TenantId,
        token_hash: str,
    ) -> ApiTokenCredential | None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def revoke_token(self, tenant_id: TenantId, token_hash: str, actor: str) -> bool:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_tokens(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> SecurityTokenPage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def record_token_used(self, tenant_id: TenantId, token_hash: str) -> None:
        raise TypeError("adapter contract invoked directly")


class AccessPolicyRepository(ABC):
    @abstractmethod
    def upsert_rule(self, rule: AccessPolicyRule) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_rules(
        self,
        tenant_id: TenantId,
        pagination: Pagination,
        include_inactive: bool,
    ) -> AccessPolicyRulePage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def find_active_rules_for_permission(
        self,
        tenant_id: TenantId,
        permission: Permission,
    ) -> tuple[AccessPolicyRule, ...]:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def deactivate_rule(self, tenant_id: TenantId, name: str) -> bool:
        raise TypeError("adapter contract invoked directly")


class AuditRepository(ABC):
    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def list_records(self, event_filter: AuditEventFilter) -> AuditEventPage:
        raise TypeError("adapter contract invoked directly")

    @abstractmethod
    def verify_integrity(self, tenant_id: TenantId, limit: int = 500) -> AuditIntegrityReport:
        raise TypeError("adapter contract invoked directly")


class TransactionManager(ABC):
    @abstractmethod
    def begin(self) -> UnitOfWork:
        raise TypeError("adapter contract invoked directly")
